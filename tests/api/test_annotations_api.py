from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import annotations
from app.core.exceptions import ErrorCode, register_exception_handlers
from app.db.session import get_web_session


class RejectingSession:
    async def execute(self, statement: object, parameters: object | None = None) -> None:
        del statement, parameters
        raise AssertionError("readonly-field validation should happen before database writes")


async def fake_session() -> AsyncIterator[RejectingSession]:
    yield RejectingSession()


def test_field_annotation_endpoint_rejects_collection_fields_with_400() -> None:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(annotations.router)
    app.dependency_overrides[get_web_session] = fake_session
    client = TestClient(app)

    response = client.put(
        "/annotations/field",
        params={"urn": "mysql:crm:sales:orders:pay_amount"},
        json={
            "business_meaning": "订单支付金额",
            "raw_type": "decimal(12,2)",
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == ErrorCode.ANNOTATION_READONLY_FIELD
    assert response.json()["detail"]["fields"] == ["raw_type"]


def test_table_batch_annotation_endpoint_returns_per_field_errors_without_db_write() -> None:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(annotations.router)
    app.dependency_overrides[get_web_session] = fake_session
    client = TestClient(app)

    response = client.put(
        "/annotations/table/fields",
        params={"table_urn": "mysql:crm:sales:orders"},
        json={
            "items": [
                {
                    "urn": "mysql:crm:sales:orders:pay_amount",
                    "annotation": {"business_meaning": "订单支付金额"},
                },
                {
                    "urn": "mysql:crm:sales:orders:order_status",
                    "annotation": {
                        "business_meaning": "订单状态",
                        "raw_type": "tinyint",
                    },
                },
            ]
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == ErrorCode.ANNOTATION_BATCH_FAILED
    assert response.json()["detail"]["errors"] == [
        {
            "urn": "mysql:crm:sales:orders:order_status",
            "fields": ["raw_type"],
            "message": "标注接口不允许写入采集层字段",
        }
    ]


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_field_annotation_endpoint_rejects_invalid_urn_query_with_422(method: str) -> None:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(annotations.router)
    app.dependency_overrides[get_web_session] = fake_session
    client = TestClient(app)

    response = client.request(
        method.upper(),
        "/annotations/field",
        params={"urn": "mysql:crm:sales:orders/pay_amount"},
        json={"business_meaning": "订单支付金额"} if method == "put" else None,
    )

    assert response.status_code == 422


def test_table_batch_annotation_endpoint_rejects_invalid_table_urn_query_with_422() -> None:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(annotations.router)
    app.dependency_overrides[get_web_session] = fake_session
    client = TestClient(app)

    response = client.put(
        "/annotations/table/fields",
        params={"table_urn": "mysql:crm:sales:orders:pay_amount"},
        json={
            "items": [
                {
                    "urn": "mysql:crm:sales:orders:pay_amount",
                    "annotation": {"business_meaning": "订单支付金额"},
                }
            ]
        },
    )

    assert response.status_code == 422


def test_annotation_routes_keep_urns_out_of_path_parameters() -> None:
    route_paths = {route.path for route in annotations.router.routes}

    assert "/annotations/field/{urn}" not in route_paths
    assert all("{urn}" not in path and "{table_urn}" not in path for path in route_paths)
