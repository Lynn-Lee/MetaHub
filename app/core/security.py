"""密码哈希与 JWT 令牌（DEV-TASKS T8.4）。

密码用标准库 `hashlib.pbkdf2_hmac`（sha256 + 每用户随机盐 + 高迭代），
存储格式 `pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>`，校验用
`hmac.compare_digest` 常量时间比较。不引入 passlib/bcrypt——V0.1 的简单
登录只是 SSO/LDAP（PRD M10-1）落地前的过渡，pbkdf2 是标准库里的 NIST KDF，
既不自造哈希原语，又把依赖面压到最小。

JWT 用 PyJWT，密钥与有效期由调用方（AuthService）从 Settings 注入。
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

_ALGORITHM = "HS256"
_PBKDF2_ITERATIONS = 600_000
_SALT_BYTES = 16
_HASH_SCHEME = "pbkdf2_sha256"


def hash_password(password: str, *, iterations: int = _PBKDF2_ITERATIONS) -> str:
    if not password:
        raise ValueError("password must not be empty")
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"{_HASH_SCHEME}${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    parts = stored.split("$")
    if len(parts) != 4 or parts[0] != _HASH_SCHEME:
        return False
    _, iter_str, salt_hex, hash_hex = parts
    try:
        iterations = int(iter_str)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return hmac.compare_digest(digest, expected)


def create_access_token(
    subject: str,
    *,
    secret_key: str,
    expires_minutes: int,
    extra_claims: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> str:
    issued_at = now or datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=expires_minutes),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, secret_key, algorithm=_ALGORITHM)


def decode_access_token(token: str, *, secret_key: str) -> dict[str, Any]:
    """解码并校验签名与有效期；失败抛 `jwt.InvalidTokenError` 家族异常。"""
    return jwt.decode(token, secret_key, algorithms=[_ALGORITHM])
