from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import metadata_queries
from app.core.exceptions import register_exception_handlers
from app.db.session import get_web_session
from app.schemas.metadata_queries import (
    ColumnOut,
    DataSourceOut,
    FieldSearchGroupOut,
    MetadataPage,
    SearchOut,
    TableDdlOut,
    TableOut,
)


class FakeSession:
    pass


async def fake_session() -> AsyncIterator[FakeSession]:
    yield FakeSession()


class FakeMetadataQueryService:
    async def list_data_sources(
        self,
        session: object,
        *,
        page: int,
        page_size: int,
    ) -> MetadataPage[DataSourceOut]:
        del session
        return MetadataPage(
            total=2,
            page=page,
            page_size=page_size,
            items=[
                DataSourceOut(
                    id=1,
                    code="crm-prod",
                    name="CRM 生产库",
                    db_type="mysql",
                    env="prod",
                    host="crm-db.internal",
                    port=3306,
                    default_db="sales",
                    group_name="CRM",
                    enabled=True,
                )
            ],
        )

    async def list_tables(
        self,
        session: object,
        *,
        urn: str | None,
        source_id: int | None,
        db_name: str | None,
        keyword: str | None,
        include_deleted: bool,
        page: int,
        page_size: int,
    ) -> MetadataPage[TableOut]:
        del session, source_id, db_name, keyword, include_deleted
        table_urn = urn or "mysql:crm:sales:orders"
        return MetadataPage(
            total=1,
            page=page,
            page_size=page_size,
            items=[
                TableOut(
                    urn=table_urn,
                    source_id=1,
                    db_name="sales",
                    table_name="orders",
                    table_type="TABLE",
                    table_comment="订单表",
                    row_count=1200,
                    data_size=4096,
                    dw_layer=None,
                    is_deleted=False,
                )
            ],
        )

    async def list_columns(
        self,
        session: object,
        *,
        urn: str | None,
        table_urn: str | None,
        keyword: str | None,
        include_deleted: bool,
        page: int,
        page_size: int,
    ) -> MetadataPage[ColumnOut]:
        del session, table_urn, keyword, include_deleted
        column_urn = urn or "mysql:crm:sales:orders:pay_amount"
        return MetadataPage(
            total=1,
            page=page,
            page_size=page_size,
            items=[
                ColumnOut(
                    urn=column_urn,
                    table_urn="mysql:crm:sales:orders",
                    column_name="pay_amount",
                    ordinal=3,
                    raw_type="decimal(12,2)",
                    logical_type="decimal",
                    raw_comment="支付金额",
                    is_nullable=False,
                    is_primary_key=False,
                    is_deleted=False,
                    business_meaning="订单支付金额",
                    effective_type="decimal",
                    effective_domain_id=10,
                    domain_name="交易域",
                )
            ],
        )

    async def get_table_ddl(self, session: object, *, urn: str) -> TableDdlOut:
        del session
        return TableDdlOut(
            urn=urn,
            ddl='CREATE TABLE "orders" (\n  "pay_amount" decimal(12,2) NOT NULL\n);',
            total=1,
        )

    async def search(
        self,
        session: object,
        *,
        query: str,
        page: int,
        page_size: int,
    ) -> SearchOut:
        del session
        return SearchOut(
            query=query,
            total=2,
            page=page,
            page_size=page_size,
            tables=[],
            field_groups=[
                FieldSearchGroupOut(
                    table_urn="mysql:crm:sales:orders",
                    source_id=1,
                    db_name="sales",
                    table_name="orders",
                    max_score=0.91,
                    columns=[
                        ColumnOut(
                            urn="mysql:crm:sales:orders:pay_amount",
                            table_urn="mysql:crm:sales:orders",
                            column_name="pay_amount",
                            ordinal=3,
                            raw_type="decimal(12,2)",
                            logical_type="decimal",
                            raw_comment="支付金额",
                            is_nullable=False,
                            is_primary_key=False,
                            is_deleted=False,
                            business_meaning="订单支付金额",
                            effective_type="decimal",
                            effective_domain_id=10,
                            domain_name="交易域",
                        )
                    ],
                )
            ],
        )


def _client() -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(metadata_queries.router)
    app.dependency_overrides[get_web_session] = fake_session
    app.dependency_overrides[metadata_queries.get_metadata_query_service] = lambda: (
        FakeMetadataQueryService()
    )
    return TestClient(app)


def test_datasources_endpoint_returns_paginated_total() -> None:
    response = _client().get("/datasources", params={"page": 2, "page_size": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["page"] == 2
    assert body["page_size"] == 1
    assert body["items"][0]["code"] == "crm-prod"


def test_tables_endpoint_accepts_table_urn_query_for_detail() -> None:
    response = _client().get("/tables", params={"urn": "mysql:crm:sales:orders"})

    assert response.status_code == 200
    assert response.json()["items"][0]["urn"] == "mysql:crm:sales:orders"


def test_columns_endpoint_accepts_column_urn_query_for_detail() -> None:
    response = _client().get(
        "/columns",
        params={"urn": "mysql:crm:sales:orders:pay_amount"},
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["urn"] == "mysql:crm:sales:orders:pay_amount"


def test_table_ddl_endpoint_uses_query_urn_and_returns_total() -> None:
    response = _client().get("/tables/ddl", params={"urn": "mysql:crm:sales:orders"})

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert 'CREATE TABLE "orders"' in response.json()["ddl"]


def test_search_endpoint_keeps_grouped_results_and_total() -> None:
    response = _client().get("/search", params={"q": "订单", "page_size": 10})

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "订单"
    assert body["total"] == 2
    assert body["field_groups"][0]["columns"][0]["business_meaning"] == "订单支付金额"


def test_metadata_routes_keep_urns_out_of_path_parameters() -> None:
    route_paths = {route.path for route in metadata_queries.router.routes}

    assert "/tables/{urn}" not in route_paths
    assert "/columns/{urn}" not in route_paths
    assert all("{urn}" not in path and "{table_urn}" not in path for path in route_paths)
