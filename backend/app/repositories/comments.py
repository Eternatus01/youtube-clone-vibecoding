from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Comment


async def get(db: AsyncSession, comment_id: str) -> Comment | None:
    result = await db.execute(
        select(Comment)
        .options(selectinload(Comment.author))
        .where(Comment.id == comment_id)
    )
    return result.scalar_one_or_none()


async def list_for_video(
    db: AsyncSession,
    video_id: str,
    *,
    sort: str,
    offset: int,
    limit: int,
) -> tuple[list[Comment], int]:
    conditions = [Comment.video_id == video_id]
    order = (
        Comment.created_at.desc() if sort == "newest" else Comment.created_at.asc()
    )
    total = await db.scalar(select(func.count(Comment.id)).where(*conditions))
    result = await db.execute(
        select(Comment)
        .options(selectinload(Comment.author))
        .where(*conditions)
        .order_by(order, Comment.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), int(total or 0)


async def reply_counts(db: AsyncSession, comment_ids: list[str]) -> dict[str, int]:
    if not comment_ids:
        return {}
    result = await db.execute(
        select(Comment.parent_id, func.count(Comment.id))
        .where(Comment.parent_id.in_(comment_ids))
        .group_by(Comment.parent_id)
    )
    return {parent_id: int(count) for parent_id, count in result.all()}


async def create(
    db: AsyncSession,
    *,
    video_id: str,
    author_id: str,
    body: str,
    parent_id: str | None,
) -> Comment:
    comment = Comment(
        video_id=video_id,
        author_id=author_id,
        body=body,
        parent_id=parent_id,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return await get(db, comment.id)


async def save(db: AsyncSession, comment: Comment, body: str) -> Comment:
    comment.body = body
    await db.commit()
    return await get(db, comment.id)


async def delete_comment(db: AsyncSession, comment: Comment) -> None:
    await db.delete(comment)
    await db.commit()