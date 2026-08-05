import pytest

from app.collectors import (
    BaseCollector,
    ColumnInfo,
    DatabaseInfo,
    DataSourceConfig,
    IndexInfo,
    TableInfo,
    get_collector,
    normalize_column_type,
    register_collector,
)


class DummyCollector(BaseCollector):
    async def test_connection(self) -> bool:
        return True

    async def list_databases(self) -> list[DatabaseInfo]:
        return [DatabaseInfo(name="meta_test_db")]

    async def list_tables(self, db_name: str) -> list[TableInfo]:
        return [
            TableInfo(
                db_name=db_name,
                table_name="orders",
                table_type="TABLE",
                table_comment="订单表",
            )
        ]

    async def list_columns(self, db_name: str) -> list[ColumnInfo]:
        return [
            ColumnInfo(
                db_name=db_name,
                table_name="orders",
                column_name="pay_amount",
                ordinal=1,
                raw_type="decimal(12,2)",
                logical_type=self.normalize_type("decimal(12,2)"),
                is_nullable=False,
                raw_comment="支付金额",
            )
        ]

    async def list_indexes(self, db_name: str) -> list[IndexInfo]:
        return [
            IndexInfo(
                db_name=db_name,
                table_name="orders",
                index_name="idx_orders_pay_amount",
                columns=["pay_amount"],
            )
        ]


def test_registry_instantiates_registered_collector() -> None:
    register_collector("dummy", DummyCollector)

    config = DataSourceConfig(
        source_id=1,
        code="dummy_source",
        db_type="DUMMY",
        host="127.0.0.1",
        port=3306,
        username="readonly",
        password="secret",
    )

    collector = get_collector("DUMMY", config)

    assert isinstance(collector, DummyCollector)
    assert collector.config is config


def test_base_collector_normalizes_type_from_config_db_type() -> None:
    config = DataSourceConfig(
        source_id=1,
        code="mysql_source",
        db_type="mysql",
        host="127.0.0.1",
        port=3306,
        username="readonly",
        password="secret",
    )

    collector = DummyCollector(config)

    assert collector.normalize_type("decimal(12,2)") == "DECIMAL"


@pytest.mark.parametrize(
    ("db_type", "raw_type", "expected"),
    [
        ("mysql", "varchar(255)", "STRING"),
        ("mysql", "tinyint(1)", "BOOL"),
        ("mysql", "tinyint(4)", "INT"),
        ("postgresql", "timestamp with time zone", "DATETIME"),
        ("postgresql", "timestamp without time zone", "DATETIME"),
        ("postgresql", "jsonb", "JSON"),
        ("oracle", "NUMBER(12,0)", "INT"),
        ("oracle", "NUMBER(12,2)", "DECIMAL"),
        ("oracle", "NUMBER(1)", "BOOL"),
        ("sqlserver", "nvarchar(128)", "STRING"),
        ("sqlserver", "bit", "BOOL"),
    ],
)
def test_type_mapper_normalizes_prd_examples(db_type: str, raw_type: str, expected: str) -> None:
    assert normalize_column_type(db_type, raw_type) == expected


def test_unknown_collector_type_is_rejected() -> None:
    config = DataSourceConfig(
        source_id=1,
        code="missing_source",
        db_type="missing",
        host="127.0.0.1",
        port=3306,
        username="readonly",
        password="secret",
    )

    with pytest.raises(KeyError, match="未注册采集器"):
        get_collector("missing", config)
