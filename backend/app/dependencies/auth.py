import os

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import decode_access_token
from app.models.models import Role, User

MINIO_ROOT_USER = os.environ.get("MINIO_ROOT_USER", "minioadmin")
MINIO_ROOT_PASSWORD = os.environ.get("MINIO_ROOT_PASSWORD", "change_me_minio")


async def _get_token(request: Request) -> str | None:
    access_token = request.cookies.get("access_token")
    if not access_token:
        header = request.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            access_token = header[7:]
    return access_token


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    token = await _get_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    token = await _get_token(request)
    if not token:
        return None
    try:
        payload = decode_access_token(token)
    except Exception:
        return None
    if payload.get("type") != "access":
        return None
    result = await db.execute(select(User).where(User.id == payload.get("sub"), User.is_active == True))
    return result.scalar_one_or_none()


async def require_moderator(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role not in (Role.moderator, Role.admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Moderator only")
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != Role.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return current_user