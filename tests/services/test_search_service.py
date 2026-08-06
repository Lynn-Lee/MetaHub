from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Any

from sqlalchemy.dialects.postgresql import asyncpg

from app.services.search import ColumnSearchService, build_column_search_statement


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
