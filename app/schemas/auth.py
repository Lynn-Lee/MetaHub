"""登录与会话相关 schema（DEV-TASKS T8.4）。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64, examples=["lynn"])
    password: str = Field(min_length=1, max_length=256, examples=["correct-horse"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 - OAuth2 token 类型标识，非密码
    expires_in: int = Field(description="令牌有效期（秒）", examples=[28800])


class CurrentUser(BaseModel):
    id: int
    username: str
    real_name: str | None = None
    email: str | None = None
