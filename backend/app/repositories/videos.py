from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Comment, Like, Video, VideoStatus, Visibility


async def get(db: AsyncSession, video_id: str) -> Video | None:
    result = await db.execute(
        select(Video).options(selectinload(Video.owner)).where(Video.id == video_id)
    )
    return result.scalar_one_or_none()


async def get_feed(
    db: AsyncSession,
    *,
    search: str | None,
    offset: int,
    limit: int,
) -> tuple[list[Video], int]:
    conditions = [
        Video.status == VideoStatus.ready,
        Video.visibility == Visibility.public,
    ]
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        conditions.append(Video.title.ilike(f"%{escaped}%", escape="\\"))

    total = await db.scalar(select(func.count(Video.id)).where(*conditions))
    result = await db.execute(
        select(Video)
        .options(selectinload(Video.owner))
        .where(*conditions)
        .order_by(Video.created_at.desc(), Video.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), int(total or 0)


async def like_counts(db: AsyncSession, video_ids: list[str]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    if not video_ids:
        return counts
    result = await db.execute(
        select(Like.video_id, Like.is_like, func.count(Like.id))
        .where(Like.video_id.in_(video_ids))
        .group_by(Like.video_id, Like.is_like)
    )
    for video_id, is_like, count in result.all():
        bucket = counts.setdefault(video_id, {"like": 0, "dislike": 0})
        bucket["like" if is_like else "dislike"] = int(count)
    return counts


async def comment_counts(db: AsyncSession, video_ids: list[str]) -> dict[str, int]:
    if not video_ids:
        return {}
    result = await db.execute(
        select(Comment.video_id, func.count(Comment.id))
        .where(Comment.video_id.in_(video_ids))
        .group_by(Comment.video_id)
    )
    return {video_id: int(count) for video_id, count in result.all()}


async def user_likes(
    db: AsyncSession, user_id: str, video_ids: list[str]
) -> dict[str, bool]:
    if not video_ids or not user_id:
        return {}
    result = await db.execute(
        select(Like.video_id, Like.is_like).where(
            Like.user_id == user_id, Like.video_id.in_(video_ids)
        )
    )
    return {video_id: bool(is_like) for video_id, is_like in result.all()}


async def get_many(db: AsyncSession, video_ids: list[str]) -> list[Video]:
    if not video_ids:
        return []
    result = await db.execute(
        select(Video)
        .options(selectinload(Video.owner))
        .where(Video.id.in_(video_ids))
    )
    return list(result.scalars().all())


async def list_by_owner(
    db: AsyncSession,
    owner_id: str,
    *,
    offset: int,
    limit: int,
) -> tuple[list[Video], int]:
    conditions = [
        Video.owner_id == owner_id,
        Video.status == VideoStatus.ready,
        Video.visibility == Visibility.public,
    ]
    total = await db.scalar(select(func.count(Video.id)).where(*conditions))
    result = await db.execute(
        select(Video)
        .options(selectinload(Video.owner))
        .where(*conditions)
        .order_by(Video.created_at.desc(), Video.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), int(total or 0)


async def list_related(
    db: AsyncSession,
    *,
    video_id: str,
    owner_id: str,
    offset: int,
    limit: int,
) -> tuple[list[Video], int]:
    conditions = [
        Video.id != video_id,
        Video.status == VideoStatus.ready,
        Video.visibility == Visibility.public,
    ]
    total = await db.scalar(select(func.count(Video.id)).where(*conditions))
    same_owner_first = case((Video.owner_id == owner_id, 0), else_=1)
    result = await db.execute(
        select(Video)
        .options(selectinload(Video.owner))
        .where(*conditions)
        .order_by(same_owner_first, Video.created_at.desc(), Video.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), int(total or 0)


async def increment_views(db: AsyncSession, video_id: str) -> None:
    await db.execute(
        update(Video).where(Video.id == video_id).values(views=Video.views + 1)
    )
    await db.commit()


async def save(db: AsyncSession, video: Video) -> Video:
    await db.commit()
    await db.refresh(video)
    return video