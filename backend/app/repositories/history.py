from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Video, Visibility, WatchHistory


def _base_query():
    return (
        select(WatchHistory)
        .join(Video, Video.id == WatchHistory.video_id)
        .options(
            selectinload(WatchHistory.video).selectinload(Video.owner),
            selectinload(WatchHistory.video).selectinload(Video.shares),
        )
    )


def _visible_condition():
    # Hidden (moderation-removed) videos never show up in history.
    return WatchHistory.video.has(Video.visibility != Visibility.hidden)


async def get_user_history(
    db: AsyncSession, user_id: str, offset: int, limit: int
) -> tuple[list[WatchHistory], int]:
    conditions = (WatchHistory.user_id == user_id, _visible_condition())

    total = await db.scalar(
        select(func.count(WatchHistory.id)).where(*conditions)
    )

    result = await db.execute(
        _base_query()
        .where(*conditions)
        .order_by(WatchHistory.last_watched_at.desc(), WatchHistory.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), int(total or 0)


async def _get(db: AsyncSession, user_id: str, video_id: str) -> WatchHistory | None:
    result = await db.execute(
        select(WatchHistory).where(
            WatchHistory.user_id == user_id, WatchHistory.video_id == video_id
        )
    )
    return result.scalar_one_or_none()


async def upsert_history(
    db: AsyncSession, user_id: str, video_id: str, progress_seconds: int | None
) -> WatchHistory:
    existing = await _get(db, user_id, video_id)
    if existing is not None:
        if progress_seconds is not None:
            existing.progress_seconds = progress_seconds
        existing.last_watched_at = func.now()
        await db.commit()
        await db.refresh(existing)
        return existing

    entry = WatchHistory(
        user_id=user_id, video_id=video_id, progress_seconds=progress_seconds
    )
    db.add(entry)
    try:
        await db.commit()
    except IntegrityError:
        # Concurrent insert won the unique constraint; update that row instead.
        await db.rollback()
        existing = await _get(db, user_id, video_id)
        if existing is None:
            raise
        if progress_seconds is not None:
            existing.progress_seconds = progress_seconds
        existing.last_watched_at = func.now()
        await db.commit()
        await db.refresh(existing)
        return existing
    await db.refresh(entry)
    return entry


async def delete_history_item(db: AsyncSession, user_id: str, video_id: str) -> None:
    await db.execute(
        delete(WatchHistory).where(
            WatchHistory.user_id == user_id, WatchHistory.video_id == video_id
        )
    )
    await db.commit()


async def delete_all_history(db: AsyncSession, user_id: str) -> None:
    await db.execute(delete(WatchHistory).where(WatchHistory.user_id == user_id))
    await db.commit()
