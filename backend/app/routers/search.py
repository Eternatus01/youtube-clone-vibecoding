from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.dependencies.auth import get_current_user_optional
from app.schemas.schemas import SearchResult
from app.services import search as search_service

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/", response_model=SearchResult)
async def search(
    q: str,
    page: int = 1,
    page_size: int = 20,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    return await search_service.search(
        db, q=q, page=page, page_size=page_size
    )