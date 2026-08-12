from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

_SECRET = "unit_test_secret_key_at_least_32_chars_long"


def test_hash_password_roundtrip() -> None:
    stored = hash_password("s3cret-pw")
    assert stored.startswith("pbkdf2_sha256$")
    assert "s3cret-pw" not in stored
    assert verify_password("s3cret-pw", stored) is True
    assert verify_password("wrong-pw", stored) is False


def test_hash_password_is_salted() -> None:
    assert hash_password("same") != hash_password("same")


def test_verify_password_rejects_malformed_hash() -> None:
    assert verify_password("x", "not-a-valid-hash") is False
    assert verify_password("x", "md5$1$aa$bb") is False


def test_hash_password_rejects_empty() -> None:
    with pytest.raises(ValueError):
        hash_password("")


def test_access_token_roundtrip() -> None:
    token = create_access_token(
        "42", secret_key=_SECRET, expires_minutes=30, extra_claims={"username": "lynn"}
    )
    payload = decode_access_token(token, secret_key=_SECRET)
    assert payload["sub"] == "42"
    assert payload["username"] == "lynn"


def test_expired_token_is_rejected() -> None:
    past = datetime.now(UTC) - timedelta(hours=2)
    token = create_access_token("42", secret_key=_SECRET, expires_minutes=30, now=past)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token, secret_key=_SECRET)


def test_token_signed_with_other_key_is_rejected() -> None:
    token = create_access_token("42", secret_key=_SECRET, expires_minutes=30)
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token, secret_key="another_secret_key_at_least_32_chars_xx")
