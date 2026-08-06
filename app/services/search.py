"""关键词检索服务（DEV-TASKS T4.1）。"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Any, Protocol, cast

from sqlalchemy import (
    BigInteger,
    Boolean,
    Float,
    Select,
    String,
    column,
    func,
    literal,
    select,
    table,
    union_all,
)

from app.db.session import web_session
from app.models.knowledge import AssetAnnotation
from app.models.metadata import ColumnMeta


class SearchSession(Protocol):
    async def execute(self, statement: object, parameters: dict[str, Any] | None = None) -> Any: ...


SessionFactory = Callable[[], AbstractAsyncContextManager[SearchSession]]


v_column_effective = table(
    "v_column_effective",
    column("urn", String),
    column("table_urn", String),
    column("source_id", BigInteger),
    column("db_name", String),
    column("table_name", String),
    column("column_name", String),
    column("raw_type", String),
    column("logical_type", String),
    column("raw_comment", String),
    column("is_deleted", Boolean),
    column("business_meaning", String),
    column("effective_type", String),
    column("effective_domain_id", BigInteger),
    column("domain_name", String),
)


@dataclass(frozen=True, slots=True)
class ColumnSearchResult:
    urn: str
    table_urn: str
    source_id: int
    db_name: str
    table_name: str
    column_name: str
    raw_type: str
    logical_type: str
    raw_comment: str | None
    business_meaning: str | None
    effective_type: str | None
    effective_domain_id: int | None
    domain_name: str | None
    score: float


class ColumnSearchService:
    def __init__(self, *, session_factory: SessionFactory | None = None) -> None:
        self._session_factory = session_factory or cast(SessionFactory, web_session)

    async def search_columns(
        self,
        query: str,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ColumnSearchResult]:
        statement = build_column_search_statement(query, limit=limit, offset=offset)
        async with self._session_factory() as session:
            result = await session.execute(statement)
            rows = result.mappings().all()
        return [_column_result(row) for row in rows]


def build_column_search_statement(query: str, *, limit: int, offset: int) -> Select[Any]:
    keyword = query.strip()
    if not keyword:
        raise ValueError("query must not be empty")

    collection_score = func.similarity(ColumnMeta.search_text, keyword).cast(Float)
    annotation_score = func.similarity(AssetAnnotation.search_text, keyword).cast(Float) * literal(
        1.2
    )
    collection_hits = (
        select(
            ColumnMeta.urn.label("urn"),
            collection_score.label("score"),
        )
        .where(
            ColumnMeta.search_text.op("%")(keyword),
            ColumnMeta.is_deleted.is_(False),
        )
        .subquery()
    )
    annotation_hits = (
        select(
            AssetAnnotation.urn.label("urn"),
            annotation_score.label("score"),
        )
        .where(
            AssetAnnotation.search_text.op("%")(keyword),
            AssetAnnotation.asset_type == "COLUMN",
        )
        .subquery()
    )
    hits = union_all(select(collection_hits), select(annotation_hits)).cte("hits")
    result_columns = [
        v_column_effective.c.urn,
        v_column_effective.c.table_urn,
        v_column_effective.c.source_id,
        v_column_effective.c.db_name,
        v_column_effective.c.table_name,
        v_column_effective.c.column_name,
        v_column_effective.c.raw_type,
        v_column_effective.c.logical_type,
        v_column_effective.c.raw_comment,
        v_column_effective.c.business_meaning,
        v_column_effective.c.effective_type,
        v_column_effective.c.effective_domain_id,
        v_column_effective.c.domain_name,
    ]
    score = func.max(hits.c.score).label("score")
    return (
        select(*result_columns, score)
        .select_from(v_column_effective.join(hits, hits.c.urn == v_column_effective.c.urn))
        .where(v_column_effective.c.is_deleted.is_(False))
        .group_by(*result_columns)
        .order_by(score.desc(), v_column_effective.c.urn.asc())
        .limit(max(1, limit))
        .offset(max(0, offset))
    )


def _column_result(row: dict[str, Any]) -> ColumnSearchResult:
    return ColumnSearchResult(
        urn=str(row["urn"]),
        table_urn=str(row["table_urn"]),
        source_id=int(row["source_id"]),
        db_name=str(row["db_name"]),
        table_name=str(row["table_name"]),
        column_name=str(row["column_name"]),
        raw_type=str(row["raw_type"]),
        logical_type=str(row["logical_type"]),
        raw_comment=cast(str | None, row["raw_comment"]),
        business_meaning=cast(str | None, row["business_meaning"]),
        effective_type=cast(str | None, row["effective_type"]),
        effective_domain_id=(
            int(row["effective_domain_id"]) if row["effective_domain_id"] is not None else None
        ),
        domain_name=cast(str | None, row["domain_name"]),
        score=float(row["score"]),
    )
