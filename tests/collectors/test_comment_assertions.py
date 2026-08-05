from collections.abc import AsyncIterator
from typing import Any

import pytest

from app.collectors import DataSourceConfig, get_collector

_MYSQL_ROWS: list[dict[str, Any]] = []
_POSTGRESQL_ROWS: list[dict[str, Any]] = []


class FakeMySQLCursor:
    def __enter__(self) -> "FakeMySQLCursor":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def execute(self, _sql: str, _params: tuple[Any, ...] = ()) -> None:
        return None

    def fetchall(self) -> list[dict[str, Any]]:
        return _MYSQL_ROWS


class FakeMySQLConnection:
    def __enter__(self) -> "FakeMySQLConnection":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def cursor(self) -> FakeMySQLCursor:
        return FakeMySQLCursor()


class FakePostgreSQLConnection:
    async def fetch(self, _sql: str, *_params: Any) -> list[dict[str, Any]]:
        return _POSTGRESQL_ROWS

    async def close(self) -> None:
        return None


@pytest.fixture(params=["mysql", "postgresql"])
async def fixture_source(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[DataSourceConfig]:
    db_type = str(request.param)
    if db_type == "mysql":
        _MYSQL_ROWS[:] = [
            {
                "db_name": "meta_test_db",
                "table_name": "orders",
                "column_name": "pay_amount",
                "ordinal": 1,
                "raw_type": "decimal(12,2)",
                "data_length": 12,
                "num_precision": 12,
                "num_scale": 2,
                "is_nullable": "NO",
                "default_value": None,
                "raw_comment": "支付金额",
                "column_key": "",
                "extra": "",
            }
        ]
        monkeypatch.setattr(
            "app.collectors.mysql.pymysql.connect",
            lambda **_kwargs: FakeMySQLConnection(),
        )
        port = 3306
    else:
        _POSTGRESQL_ROWS[:] = [
            {
                "db_name": "public",
                "table_name": "orders",
                "column_name": "pay_amount",
                "ordinal": 1,
                "raw_type": "numeric(12,2)",
                "data_length": None,
                "num_precision": 12,
                "num_scale": 2,
                "is_nullable": False,
                "default_value": None,
                "raw_comment": "支付金额",
                "is_primary_key": False,
                "is_unique": False,
            }
        ]

        async def fake_connect(**_kwargs: Any) -> FakePostgreSQLConnection:
            return FakePostgreSQLConnection()

        monkeypatch.setattr("app.collectors.postgresql.asyncpg.connect", fake_connect)
        port = 5432

    yield DataSourceConfig(
        source_id=1,
        code=f"{db_type}_fixture",
        db_type=db_type,
        host="127.0.0.1",
        port=port,
        username="readonly",
        password="secret",
        default_db="meta_test_db",
    )
    _MYSQL_ROWS.clear()
    _POSTGRESQL_ROWS.clear()


@pytest.mark.gate
async def test_comment_not_all_empty(fixture_source: DataSourceConfig) -> None:
    """带中文注释的 fixture 采集结果不能全空，不允许 skip。"""
    collector = get_collector(fixture_source.db_type, fixture_source)
    db_name = "public" if fixture_source.db_type == "postgresql" else "meta_test_db"

    columns = await collector.list_columns(db_name)

    assert len(columns) > 0, "未采集到任何字段"
    with_comment = [
        column for column in columns if column.raw_comment and column.raw_comment.strip()
    ]
    assert len(with_comment) > 0, f"{fixture_source.db_type} 注释采集全空，实现有误"

    zh = [
        column
        for column in with_comment
        if any("\u4e00" <= char <= "\u9fff" for char in column.raw_comment or "")
    ]
    assert len(zh) > 0, f"{fixture_source.db_type} 中文注释解码异常"
