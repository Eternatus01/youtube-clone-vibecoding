from fastapi import HTTPException, Response, status

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.models.models import User
from app.repositories import users as users_repo


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.access_token_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.refresh_token_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    for key in ("access_token", "refresh_token"):
        response.delete_cookie(
            key=key,
            path="/",
            secure=settings.cookie_secure,
            httponly=True,
            samesite="lax",
        )


def issue_tokens(user: User) -> tuple[str, str]:
    return create_access_token(user.id), create_refresh_token(user.id)


async def register_user(db, body) -> User:
    if await users_repo.get_by_username(db, body.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username already taken"
        )
    if await users_repo.get_by_email(db, body.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
    return await users_repo.create(
        db,
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
    )


async def authenticate(db, login: str, password: str) -> User:
    user = await users_repo.get_by_login(db, login)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled"
        )
    return user


async def user_from_refresh_token(db, token: str) -> User:
    try:
        payload = decode_refresh_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
        )
    user = await users_repo.get_by_id(db, str(payload.get("sub")))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


async def update_profile(db, user: User, body) -> User:
    if body.username is not None and body.username != user.username:
        existing = await users_repo.get_by_username(db, body.username)
        if existing and existing.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Username already taken"
            )
        user.username = body.username
    if body.avatar_url is not None:
        if len(body.avatar_url) > 512:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="avatar_url too long",
            )
        user.avatar_url = body.avatar_url
    await db.commit()
    await db.refresh(user)
    return user


async def change_password(db, user: User, old_password: str, new_password: str) -> None:
    if not verify_password(old_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Old password is incorrect"
        )
    user.password_hash = hash_password(new_password)
    await db.commit()