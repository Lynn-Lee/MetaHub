"""数据源连接凭证的对称加解密（DEV-TASKS T8.2 / PRD §M10-8）。

采集器连接生产库需要明文密码，但明文绝不落库：录入时用 Fernet 加密成密文存
`data_source.password_cipher`，采集时解密后用于建连。主密钥
`CREDENTIAL_SECRET_KEY` 只从环境变量注入（见 `.env.example` / `core.config`），
绝不入库、不写日志。

与 `core.security` 的口令哈希是两码事：用户登录口令走单向 pbkdf2（不可逆），
数据源密码必须可逆解密才能拿去连库，故用 Fernet 对称加密。
"""

from __future__ import annotations

from cryptography.fernet import Fernet

from app.core.config import get_settings


def _cipher(key: str | None) -> Fernet:
    secret = key or get_settings().CREDENTIAL_SECRET_KEY
    return Fernet(secret.encode())


def encrypt_credential(plaintext: str, *, key: str | None = None) -> str:
    """把明文凭证加密为可落库的密文；`key` 缺省取环境注入的主密钥。"""
    if not plaintext:
        raise ValueError("credential must not be empty")
    return _cipher(key).encrypt(plaintext.encode()).decode()


def decrypt_credential(cipher_text: str, *, key: str | None = None) -> str:
    """还原密文为明文凭证；密钥不匹配或密文损坏抛 `cryptography.fernet.InvalidToken`。"""
    return _cipher(key).decrypt(cipher_text.encode()).decode()
