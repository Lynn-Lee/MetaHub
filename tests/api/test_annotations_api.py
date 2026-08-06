from collections.abc import AsyncIterator

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
