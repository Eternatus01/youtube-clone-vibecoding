from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.rate_limit import check_rate_limit
from app.dependencies.auth import get_current_user
from app.schemas.schemas import (
    PasswordChange,
    RefreshRequest,
    TokenResponse,
    UserLogin,
    UserOut,
    UserRegister,
    UserUpdate,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _token_response(user, access_token: str, refresh_token: str) -> TokenResponse:
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: UserRegister,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    user = await auth_service.register_user(db, body)
    access_token, refresh_token = auth_service.issue_tokens(user)
    auth_service.set_auth_cookies(response, access_token, refresh_token)
    return _token_response(user, access_token, refresh_token)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: UserLogin,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    client_host = request.client.host if request.client else "unknown"
    check_rate_limit(f"login:{client_host}:{body.login.lower()}", limit=10, window_seconds=60)
    user = await auth_service.authenticate(db, body.login, body.password)
    access_token, refresh_token = auth_service.issue_tokens(user)
    auth_service.set_auth_cookies(response, access_token, refresh_token)
    return _token_response(user, access_token, refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    token = request.cookies.get("refresh_token") or body.refresh_token
    user = await auth_service.user_from_refresh_token(db, token)
    access_token, refresh_token = auth_service.issue_tokens(user)
    auth_service.set_auth_cookies(response, access_token, refresh_token)
    return _token_response(user, access_token, refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    auth_service.clear_auth_cookies(response)


@router.get("/me", response_model=UserOut)
async def me(current_user=Depends(get_current_user)):
    return UserOut.model_validate(current_user)


@router.patch("/me", response_model=UserOut)
async def update_me(
    body: UserUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await auth_service.update_profile(db, current_user, body)
    return UserOut.model_validate(user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: PasswordChange,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await auth_service.change_password(
        db, current_user, body.old_password, body.new_password
    )