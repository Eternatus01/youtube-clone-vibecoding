from fastapi import APIRouter, Depends, Response, status

from app.dependencies.auth import get_current_user, get_current_user_optional
from app.schemas.schemas import (
    PasswordChange,
    RefreshRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserUpdate,
    UserOut,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: UserRegister):
    raise NotImplementedError


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin, response: Response):
    raise NotImplementedError


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, response: Response):
    raise NotImplementedError


@router.post("/logout")
async def logout(response: Response):
    raise NotImplementedError


@router.get("/me", response_model=UserOut)
async def me(current_user=Depends(get_current_user)):
    raise NotImplementedError


@router.patch("/me", response_model=UserOut)
async def update_me(body: UserUpdate, current_user=Depends(get_current_user)):
    raise NotImplementedError


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(body: PasswordChange, current_user=Depends(get_current_user)):
    raise NotImplementedError