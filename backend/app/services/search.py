from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import search as search_repo
from app.schemas.schemas import (
    SearchChannelOut,
    SearchResult,
    SearchVideoOut,
    UserOut,
)


def _like_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


async def search(
    db: AsyncSession,
    *,
    q: str,
    page: int,
    page_size: int,
) -> SearchResult:
    query = (q or "").strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query must not be empty",
        )
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    offset = (page - 1) * page_size
    pattern = _like_pattern(query)

    videos = await search_repo.search_videos(
        db, pattern, offset=offset, limit=page_size
    )
    channels = await search_repo.search_channels(
        db, pattern, offset=offset, limit=page_size
    )
    counts = await search_repo.subscriber_counts(db, [c.id for c in channels])

    return SearchResult(
        query=query,
        videos=[
            SearchVideoOut.model_validate(video).model_copy(
                update={
                    "owner": (
                        UserOut.model_validate(video.owner)
                        if video.owner is not None
                        else None
                    )
                }
            )
            for video in videos
        ],
        channels=[
            SearchChannelOut.model_validate(channel).model_copy(
                update={"subscriber_count": counts.get(channel.id, 0)}
            )
            for channel in channels
        ],
    )