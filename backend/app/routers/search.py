from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user_optional
from app.schemas.schemas import SearchResult

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/", response_model=SearchResult)
async def search(
    q: str,
    page: int = 1,
    page_size: int = 20,
    current_user=Depends(get_current_user_optional),
):
    raise NotImplementedError