from collections.abc import AsyncIterator
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import auth
from app.core.exceptions import ErrorCode, register_exception_handlers
from app.core.security import hash_password
from app.db.session import get_web_session

_USER = {
    "id": 7,
    "username": "lynn",
    "real_name": "Lynn",
    "email": "lynn@example.com",
    "enabled": True,
    "password_hash": hash_password("correct-horse"),
}


class FakeResult:
    def __init__(self, row: dict[str, Any] | None) -> None:
        self._row = row

    def mappings(self) -> "FakeResult":
        return self

    def first(self) -> dict[str, Any] | None:
        return self._row


class FakeSession:
    async def execute(self, statement: object, parameters: object | None = None) -> FakeResult:
        del statement, parameters
        return FakeResult(_USER)


async def fake_session() -> AsyncIterator[FakeSession]:
    yield FakeSession()


def _client() -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(auth.router)
    app.dependency_overrides[get_web_session] = fake_session
    return TestClient(app)


def test_login_success_returns_bearer_token() -> None:
    client = _client()
    response = client.post("/auth/login", json={"username": "lynn", "password": "correct-horse"})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password_returns_401() -> None:
    client = _client()
    response = client.post("/auth/login", json={"username": "lynn", "password": "wrong"})
    assert response.status_code == 401
    assert response.json()["code"] == ErrorCode.UNAUTHENTICATED


def test_me_with_valid_token_returns_profile() -> None:
    client = _client()
    token = client.post(
        "/auth/login", json={"username": "lynn", "password": "correct-horse"}
    ).json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "lynn"
    assert body["id"] == 7


def test_me_without_token_returns_401() -> None:
    client = _client()
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.json()["code"] == ErrorCode.UNAUTHENTICATED
