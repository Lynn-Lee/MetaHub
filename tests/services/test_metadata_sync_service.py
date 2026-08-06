from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy.dialects import postgresql

from app.collectors import (
    BaseCollector,
    ColumnInfo,
    DatabaseInfo,
    DataSourceConfig,
    IndexInfo,
    TableInfo,
)
from app.models.metadata import DataSource
from app.services.metadata_sync import (
    InMemorySourceLock,
    MetadataSyncService,
    RedisPostgresSourceLock,
    SQLAlchemyMetadataWriter,
)


class FakeCollector(BaseCollector):
    def __init__(
        self,
        config: DataSourceConfig,
        *,
        started: list[str],
    ):
        super().__init__(config)
        self._started = started

    async def test_connection(self) -> bool:
        return True

    async def list_databases(self) -> list[DatabaseInfo]:
        self._started.append(self.config.password)
        return [
            DatabaseInfo(name="sales"),
            DatabaseInfo(name="tmp_db"),
        ]

    async def list_tables(self, db_name: str) -> list[TableInfo]:
        return [
            TableInfo(
                db_name=db_name,
                table_name="orders",
                table_type="TABLE",
                table_comment="订单表",
                row_count=10,
            ),
            TableInfo(
                db_name=db_name,
                table_name="orders_bak",
                table_type="TABLE",
                table_comment="备份表",
            ),
        ]

    async def list_columns(self, db_name: str) -> list[ColumnInfo]:
        return [
            ColumnInfo(
                db_name=db_name,
                table_name="orders",
                column_name="pay_amount",
                ordinal=1,
                raw_type="decimal(12,2)",
                logical_type="DECIMAL",
                is_nullable=False,
                raw_comment="支付金额",
            ),
            ColumnInfo(
                db_name=db_name,
                table_name="orders_bak",
                column_name="pay_amount",
                ordinal=1,
                raw_type="decimal(12,2)",
                logical_type="DECIMAL",
                is_nullable=False,
                raw_comment="备份金额",
            ),
        ]

    async def list_indexes(self, db_name: str) -> list[IndexInfo]:
        return [
            IndexInfo(
                db_name=db_name,
                table_name="orders",
                index_name="idx_orders_pay_amount",
                columns=["pay_amount"],
                index_type="BTREE",
            )
        ]


class RecordingWriter:
    def __init__(self) -> None:
        self.table_urns: list[str] = []
        self.column_urns: list[str] = []
        self.index_names: list[str] = []

    async def write_snapshot(
        self,
        session: object,
        *,
        tables: list[dict[str, Any]],
        columns: list[dict[str, Any]],
        indexes: list[dict[str, Any]],
    ) -> None:
        self.table_urns.extend(str(row["urn"]) for row in tables)
        self.column_urns.extend(str(row["urn"]) for row in columns)
        self.index_names.extend(str(row["index_name"]) for row in indexes)


class FakeSession:
    def __init__(self, source: DataSource):
        self._source = source
        self.commits = 0
        self.rollbacks = 0

    async def get(self, model: object, source_id: int) -> DataSource | None:
        assert model is DataSource
        if source_id == self._source.id:
            return self._source
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class RecordingSQLSession:
    def __init__(self) -> None:
        self.statements: list[str] = []
        self.commits = 0

    async def execute(
        self,
        statement: object,
        parameters: dict[str, Any] | None = None,
    ) -> None:
        del parameters
        self.statements.append(
            str(statement.compile(dialect=postgresql.dialect())).replace("\n", " ")
        )

    async def commit(self) -> None:
        self.commits += 1

    async def scalar(self, statement: object, parameters: dict[str, Any] | None = None) -> bool:
        self.statements.append(
            str(statement.compile(dialect=postgresql.dialect())).replace("\n", " ")
        )
        assert parameters is not None
        assert "lock_key" in parameters
        return True


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def set(self, name: str, value: str, *, ex: int, nx: bool) -> bool:
        assert ex == 60
        assert nx is True
        if name in self.values:
            return False
        self.values[name] = value
        return True

    async def get(self, name: str) -> str | None:
        return self.values.get(name)

    async def delete(self, name: str) -> None:
        self.values.pop(name, None)


@asynccontextmanager
async def _session_factory(session: FakeSession) -> AsyncIterator[FakeSession]:
    yield session


def _source(**overrides: Any) -> DataSource:
    values = {
        "id": 7,
        "code": "crm",
        "name": "CRM",
        "db_type": "mysql",
        "env": "prod",
        "host": "127.0.0.1",
        "port": 3306,
        "default_db": None,
        "username": "readonly",
        "password_cipher": "cipher-text",
        "include_rules": [{"db": "sales"}],
        "exclude_rules": [{"db": "tmp_*"}, {"table": "*_bak"}],
        "enabled": True,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    values.update(overrides)
    return DataSource(**values)


async def test_sync_source_filters_scope_decrypts_credentials_and_upserts_snapshot() -> None:
    source = _source()
    session = FakeSession(source)
    writer = RecordingWriter()
    started_passwords: list[str] = []
    service = MetadataSyncService(
        session_factory=lambda: _session_factory(session),
        collector_factory=lambda db_type, config: FakeCollector(config, started=started_passwords),
        credential_decrypter=lambda cipher: f"plain:{cipher}",
        lock=InMemorySourceLock(),
        writer=writer,
        batch_size=1,
    )

    result = await service.sync_source(source.id)

    assert result.status == "SUCCESS"
    assert result.scanned_databases == 1
    assert result.scanned_tables == 1
    assert started_passwords == ["plain:cipher-text"]
    assert writer.table_urns == ["mysql:crm:sales:orders"]
    assert writer.column_urns == ["mysql:crm:sales:orders:pay_amount"]
    assert writer.index_names == ["idx_orders_pay_amount"]
    assert session.commits == 1


async def test_sync_source_returns_locked_without_running_collector_when_lock_is_busy() -> None:
    source = _source()
    session = FakeSession(source)
    writer = RecordingWriter()
    lock = InMemorySourceLock()
    assert await lock.acquire(session, source.id) is True
    service = MetadataSyncService(
        session_factory=lambda: _session_factory(session),
        collector_factory=lambda db_type, config: pytest.fail("collector must not start"),
        credential_decrypter=lambda cipher: cipher,
        lock=lock,
        writer=writer,
    )

    result = await service.sync_source(source.id)

    assert result.status == "SKIPPED_LOCKED"
    assert writer.table_urns == []
    assert session.commits == 0


async def test_sync_source_keeps_databases_when_include_rule_is_table_only() -> None:
    source = _source(include_rules=[{"table": "orders"}], exclude_rules=[])
    session = FakeSession(source)
    writer = RecordingWriter()
    service = MetadataSyncService(
        session_factory=lambda: _session_factory(session),
        collector_factory=lambda db_type, config: FakeCollector(config, started=[]),
        credential_decrypter=lambda cipher: cipher,
        lock=InMemorySourceLock(),
        writer=writer,
    )

    result = await service.sync_source(source.id)

    assert result.scanned_databases == 2
    assert writer.table_urns == [
        "mysql:crm:sales:orders",
        "mysql:crm:tmp_db:orders",
    ]


async def test_sqlalchemy_writer_uses_batched_postgresql_on_conflict_upserts() -> None:
    session = RecordingSQLSession()
    writer = SQLAlchemyMetadataWriter(batch_size=1)
    now = datetime.now(UTC)

    await writer.write_snapshot(
        session,
        tables=[
            {
                "urn": "mysql:crm:sales:orders",
                "source_id": 7,
                "db_name": "sales",
                "table_name": "orders",
                "table_type": "TABLE",
                "table_comment": "订单表",
                "engine": None,
                "row_count": 10,
                "data_size": None,
                "db_created_at": None,
                "is_deleted": False,
                "deleted_at": None,
                "synced_at": now,
            },
            {
                "urn": "mysql:crm:sales:payments",
                "source_id": 7,
                "db_name": "sales",
                "table_name": "payments",
                "table_type": "TABLE",
                "table_comment": "支付表",
                "engine": None,
                "row_count": 8,
                "data_size": None,
                "db_created_at": None,
                "is_deleted": False,
                "deleted_at": None,
                "synced_at": now,
            },
        ],
        columns=[
            {
                "urn": "mysql:crm:sales:orders:pay_amount",
                "table_urn": "mysql:crm:sales:orders",
                "column_name": "pay_amount",
                "ordinal": 1,
                "raw_type": "decimal(12,2)",
                "logical_type": "DECIMAL",
                "data_length": None,
                "num_precision": 12,
                "num_scale": 2,
                "is_nullable": False,
                "default_value": None,
                "raw_comment": "支付金额",
                "is_primary_key": False,
                "is_auto_incr": False,
                "is_unique": False,
                "is_partition_key": False,
                "is_deleted": False,
                "deleted_at": None,
                "synced_at": now,
            }
        ],
        indexes=[
            {
                "table_urn": "mysql:crm:sales:orders",
                "index_name": "idx_orders_pay_amount",
                "index_type": "BTREE",
                "columns": [{"name": "pay_amount", "ordinal": 1}],
                "synced_at": now,
            }
        ],
    )

    assert len(session.statements) == 4
    assert session.statements[0].count("ON CONFLICT (urn) DO UPDATE") == 1
    assert session.statements[1].count("ON CONFLICT (urn) DO UPDATE") == 1
    assert session.statements[2].count("ON CONFLICT (urn) DO UPDATE") == 1
    assert "ON CONFLICT (table_urn, index_name) DO UPDATE" in session.statements[3]


async def test_redis_postgres_lock_uses_redis_nx_and_pg_advisory_lock() -> None:
    session = RecordingSQLSession()
    redis = FakeRedis()
    lock = RedisPostgresSourceLock(redis_client=redis, ttl_seconds=60)

    acquired = await lock.acquire(session, 7)
    await lock.release(session, 7)

    assert acquired is True
    assert redis.values == {}
    assert any("pg_try_advisory_lock" in statement for statement in session.statements)
    assert any("pg_advisory_unlock" in statement for statement in session.statements)
