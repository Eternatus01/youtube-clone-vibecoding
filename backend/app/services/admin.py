from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Role
from app.repositories import admin as admin_repo
from app.schemas.schemas import AdminUsersOut, UserOut

VALID_ROLES = tuple(role.value for role in Role)


def _valid_id(value: str) -> bool:
    try:
        UUID(value)
    except (ValueError, AttributeError, TypeError):
        return False
    return True


async def list_users(
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
) -> AdminUsersOut:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    users, total = await admin_repo.list_users(
        db, offset=(page - 1) * page_size, limit=page_size
    )
    return AdminUsersOut(
        users=[UserOut.model_validate(user) for user in users], total=total
    )


async def change_role(db: AsyncSession, body, admin) -> UserOut:
    if body.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role"
        )
    if body.user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role",
        )
    if not _valid_id(body.user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    user = await admin_repo.get(db, body.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    user.role = Role(body.role)
    await admin_repo.save(db, user)
    return UserOut.model_validate(user)


async def deactivate_user(db: AsyncSession, user_id: str, admin) -> None:
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself",
        )
    if not _valid_id(user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    user = await admin_repo.get(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    user.is_active = False
    await admin_repo.save(db, user)