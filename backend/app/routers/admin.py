from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.dependencies.auth import require_admin
from app.schemas.schemas import AdminRoleChange, AdminUsersOut, UserOut
from app.services import admin as admin_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=AdminUsersOut)
async def list_users(
    page: int = 1,
    page_size: int = 20,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.list_users(db, page=page, page_size=page_size)


@router.patch("/users/role", response_model=UserOut)
async def change_role(
    body: AdminRoleChange,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.change_role(db, body, admin)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: str,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await admin_service.deactivate_user(db, user_id, admin)
    return None