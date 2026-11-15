from fastapi import APIRouter, Depends, status

from app.dependencies.auth import require_admin
from app.schemas.schemas import AdminRoleChange, AdminUsersOut, PaginatedResponse, UserOut

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=AdminUsersOut)
async def list_users(
    page: int = 1,
    page_size: int = 20,
    admin=Depends(require_admin),
):
    raise NotImplementedError


@router.patch("/users/role", response_model=UserOut)
async def change_role(body: AdminRoleChange, admin=Depends(require_admin)):
    raise NotImplementedError


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(user_id: str, admin=Depends(require_admin)):
    raise NotImplementedError