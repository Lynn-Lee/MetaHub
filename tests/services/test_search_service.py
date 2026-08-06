from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Any

from sqlalchemy.dialects.postgresql import asyncpg

from app.services.search import (
    ColumnSearchService,
    SearchService,
    build_column_search_statement,
    build_table_search_statement,
)


class MappingRows:
    def __init__(self, rows: list[dict[str, Any]]):
        self._rows = rows

    def all(self) -> list[dict[str, Any]]:
        return self._rows


class QueryResult:
    def __init__(self, rows: list[dict[str, Any]]):
        self._rows = rows

    def mappings(self) -> MappingRows:
        return MappingRows(self._rows)


class RecordingSession:
    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows
        self.statements: list[str] = []

    async def execute(
        self,
        statement: object,
        parameters: dict[str, Any] | None = None,
    ) -> QueryResult:
        del parameters
        self.statements.append(str(statement.compile(dialect=asyncpg.dialect())).replace("\n", " "))
        return QueryResult(self.rows)


@asynccontextmanager
async def _session_factory(session: RecordingSession) -> AsyncIterator[RecordingSession]:
    yield session


def test_column_search_statement_uses_two_core_paths_and_sql_dedupe() -> None:
    statement = build_column_search_statement("订单", limit=20, offset=0)

    sql = str(statement.compile(dialect=asyncpg.dialect())).replace("\n", " ")

    assert "UNION ALL" in sql
    assert "FROM column_meta" in sql
    assert "FROM asset_annotation" in sql
    assert "similarity(column_meta.search_text" in sql
    assert "similarity(asset_annotation.search_text" in sql
    assert " * " in sql
    assert "JOIN v_column_effective" in sql or "JOIN hits" in sql
    assert "JOIN asset_annotation" not in sql
    assert "max(hits.score)" in sql
    assert "GROUP BY" in sql
    assert "%%" not in sql


def test_table_search_statement_uses_table_and_annotation_paths() -> None:
    statement = build_table_search_statement("订单", limit=10, offset=0)

    compiled = statement.compile(dialect=asyncpg.dialect())
    sql = str(compiled).replace("\n", " ")

    assert "UNION ALL" in sql
    assert "FROM table_meta" in sql
    assert "FROM asset_annotation" in sql
    assert "similarity(table_meta.search_text" in sql
    assert "similarity(asset_annotation.search_text" in sql
    assert "asset_annotation.asset_type" in sql
    assert "TABLE" in {str(value) for value in compiled.params.values()}
    assert "max(hits.score)" in sql
    assert "GROUP BY" in sql
    assert "%%" not in sql


async def test_column_search_service_maps_ranked_column_results() -> None:
    session = RecordingSession(
        [
            {
                "urn": "mysql:crm:sales:orders:pay_amount",
                "table_urn": "mysql:crm:sales:orders",
                "source_id": 7,
                "db_name": "sales",
                "table_name": "orders",
                "column_name": "pay_amount",
                "raw_type": "decimal(12,2)",
                "logical_type": "DECIMAL",
                "raw_comment": "支付金额",
                "business_meaning": "订单支付金额",
                "effective_type": "DECIMAL",
                "effective_domain_id": 3,
                "domain_name": "交易域",
                "score": Decimal("1.20"),
            }
        ]
    )
    service = ColumnSearchService(session_factory=lambda: _session_factory(session))

    results = await service.search_columns("订单", limit=10, offset=0)

    assert len(results) == 1
    assert results[0].urn == "mysql:crm:sales:orders:pay_amount"
    assert results[0].table_name == "orders"
    assert results[0].column_name == "pay_amount"
    assert results[0].business_meaning == "订单支付金额"
    assert results[0].score == 1.2
    assert "LIMIT" in session.statements[0]


async def test_search_service_maps_tables_and_groups_columns_by_table() -> None:
    table_session = RecordingSession(
        [
            {
                "urn": "mysql:crm:sales:orders",
                "source_id": 7,
                "db_name": "sales",
                "table_name": "orders",
                "table_type": "TABLE",
                "table_comment": "订单主表",
                "score": Decimal("0.95"),
            }
        ]
    )
    column_session = RecordingSession(
        [
            {
                "urn": "mysql:crm:sales:orders:pay_amount",
                "table_urn": "mysql:crm:sales:orders",
                "source_id": 7,
                "db_name": "sales",
                "table_name": "orders",
                "column_name": "pay_amount",
                "raw_type": "decimal(12,2)",
                "logical_type": "DECIMAL",
                "raw_comment": "支付金额",
                "business_meaning": "订单支付金额",
                "effective_type": "DECIMAL",
                "effective_domain_id": 3,
                "domain_name": "交易域",
                "score": Decimal("1.20"),
            },
            {
                "urn": "mysql:crm:sales:orders:order_status",
                "table_urn": "mysql:crm:sales:orders",
                "source_id": 7,
                "db_name": "sales",
                "table_name": "orders",
                "column_name": "order_status",
                "raw_type": "tinyint",
                "logical_type": "INT",
                "raw_comment": "订单状态",
                "business_meaning": "订单履约状态",
                "effective_type": "INT",
                "effective_domain_id": 3,
                "domain_name": "交易域",
                "score": Decimal("0.86"),
            },
        ]
    )
    sessions = iter([table_session, column_session])
    service = SearchService(session_factory=lambda: _session_factory(next(sessions)))

    result = await service.search_grouped("订单", table_limit=5, column_limit=20)

    assert [table.urn for table in result.tables] == ["mysql:crm:sales:orders"]
    assert len(result.field_groups) == 1
    assert result.field_groups[0].table_urn == "mysql:crm:sales:orders"
    assert result.field_groups[0].table_name == "orders"
    assert [column.column_name for column in result.field_groups[0].columns] == [
        "pay_amount",
        "order_status",
    ]
    assert result.field_groups[0].max_score == 1.2
    assert "FROM table_meta" in table_session.statements[0]
    assert "v_column_effective" in column_session.statements[0]
    assert "JOIN hits" in column_session.statements[0]
