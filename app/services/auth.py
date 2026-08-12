"""登录与会话服务（DEV-TASKS T8.4）。

职责：核对账号密码后签发 JWT，以及从 JWT 还原当前用户。
账号读写走 web 角色（web 对全表有权限）。密码校验、令牌签发/解码委托
`app.core.security`。RBAC 强制留给 V1.0 T23.1，这里只做认证不做授权。
"""

from __future__ import annotations

from typing import Any, Protocol

import jwt
from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.core.exceptions import UnauthenticatedError
from app.core.security import create_access_token, decode_access_token, verify_password
from app.models.support import SysUser
from app.schemas.auth import CurrentUser, TokenResponse

_INVALID_CREDENTIALS = "用户名或密码错误"
_INVALID_TOKEN = "令牌无效或已过期"  # noqa: S105 - 错误提示文案，非密码


class AuthSession(Protocol):
    async def execute(self, statement: object, parameters: dict[str, Any] | None = None) -> Any: ...


_USER_COLUMNS = (
    SysUser.id,
    SysUser.username,
    SysUser.real_name,
    SysUser.email,
    SysUser.enabled,
    SysUser.password_hash,
)


class AuthService:
    def __init__(self, *, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def login(self, session: AuthSession, *, username: str, password: str) -> TokenResponse:
        row = await self._load_user(session, SysUser.username == username)
        # 用户不存在、被停用、未设本地密码，一律回同一句话，避免泄露账号是否存在。
        if row is None or not row["enabled"] or row["password_hash"] is None:
            raise UnauthenticatedError(_INVALID_CREDENTIALS)
        if not verify_password(password, row["password_hash"]):
            raise UnauthenticatedError(_INVALID_CREDENTIALS)

        token = create_access_token(
            str(row["id"]),
            secret_key=self._settings.JWT_SECRET_KEY,
            expires_minutes=self._settings.JWT_EXPIRE_MINUTES,
            extra_claims={"username": row["username"]},
        )
        return TokenResponse(
            access_token=token,
            expires_in=self._settings.JWT_EXPIRE_MINUTES * 60,
        )

    async def current_user(self, session: AuthSession, *, token: str) -> CurrentUser:
        try:
            payload = decode_access_token(token, secret_key=self._settings.JWT_SECRET_KEY)
            user_id = int(payload["sub"])
        except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
            raise UnauthenticatedError(_INVALID_TOKEN) from exc

        row = await self._load_user(session, SysUser.id == user_id)
        if row is None or not row["enabled"]:
            raise UnauthenticatedError("用户不存在或已停用")
        return CurrentUser(
            id=row["id"],
            username=row["username"],
            real_name=row["real_name"],
            email=row["email"],
        )

    async def _load_user(self, session: AuthSession, condition: Any) -> dict[str, Any] | None:
        result = await session.execute(select(*_USER_COLUMNS).where(condition))
        row = result.mappings().first()
        return dict(row) if row is not None else None
