"""数据源凭证对称加解密（DEV-TASKS T8.2）。

验收关键：明文密码经 Fernet 加密后落库、可逆解密拿去连库，密文≠明文、
换密钥无法解密。主密钥经参数注入，测试不依赖环境变量。
"""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet, InvalidToken

from app.core.credentials import decrypt_credential, encrypt_credential

_KEY = Fernet.generate_key().decode()


def test_encrypt_decrypt_roundtrip() -> None:
    cipher = encrypt_credential("s3cret-pw", key=_KEY)
    assert cipher != "s3cret-pw"
    assert decrypt_credential(cipher, key=_KEY) == "s3cret-pw"


def test_ciphertext_does_not_contain_plaintext() -> None:
    plaintext = "P@ssw0rd-明文"
    cipher = encrypt_credential(plaintext, key=_KEY)
    assert plaintext not in cipher


def test_wrong_key_cannot_decrypt() -> None:
    cipher = encrypt_credential("s3cret-pw", key=_KEY)
    other_key = Fernet.generate_key().decode()
    with pytest.raises(InvalidToken):
        decrypt_credential(cipher, key=other_key)


def test_empty_credential_rejected() -> None:
    with pytest.raises(ValueError):
        encrypt_credential("", key=_KEY)
