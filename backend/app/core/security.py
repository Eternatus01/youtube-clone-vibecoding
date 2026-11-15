import time
from datetime import datetime, timedelta, timezone

import argon2
import jwt
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

ph = argon2.PasswordHasher()


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(password: str, hash_str: str) -> bool:
    try:
        return ph.verify(hash_str, password)
    except (VerifyMismatchError, argon2.exceptions.InvalidHashError):
        return False


def create_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def create_refresh_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(days=settings.refresh_token_days),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.refresh_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


def decode_refresh_token(token: str) -> dict:
    return jwt.decode(token, settings.refresh_secret, algorithms=["HS256"])