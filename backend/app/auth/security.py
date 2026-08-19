"""
FairyReport Backend — 密码哈希与 JWT 签发/校验
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from ..config import settings

PBKDF2_ITERATIONS = 600_000


def hash_password(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    """pbkdf2_hmac(SHA-256) 哈希；返回 (哈希 hex, 盐 hex)，未给盐时生成随机盐。"""
    salt_hex = salt_hex or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), PBKDF2_ITERATIONS
    )
    return digest.hex(), salt_hex


def verify_password(password: str, salt_hex: str, expected_hash: str) -> bool:
    """按存储盐重算哈希并做常量时间比较。"""
    digest, _ = hash_password(password, salt_hex)
    return hmac.compare_digest(digest, expected_hash)


def create_access_token(user_id: int, email: str) -> str:
    """签发 JWT（含 sub/exp，过期时间取 settings.jwt_expire_days）。"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_expire_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """校验并解码 JWT；无效或过期抛出 jwt.PyJWTError。"""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
