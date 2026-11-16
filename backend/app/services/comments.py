import math

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Comment, User
from app.repositories import comments as comments_repo
from app.schemas.schemas import (
    CommentCreate,
    CommentOut,
    CommentUpdate,
    PaginatedResponse,
    UserOut,
)
from app.services import videos as videos_service

SORTS = ("newest", "oldest")


async def _serialize(
    db: AsyncSession, comments: list[Comment]
) -> list[CommentOut]:
    reply_counts = await comments_repo.reply_counts(db, [c.id for c in comments])
    items: list[CommentOut] = []
    for comment in comments:
        out = CommentOut.model_validate(comment)
        items.append(
            out.model_copy(
                update={
                    "author": (
                        UserOut.model_validate(comment.author)
                        if comment.author is not None
                        else None
                    ),
                    "reply_count": reply_counts.get(comment.id, 0),
                }
            )
        )
    return items


async def _get_comment(
    db: AsyncSession, video_id: str, comment_id: str
) -> Comment:
    comment = await comments_repo.get(db, comment_id)
    if comment is None or comment.video_id != video_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found"
        )
    return comment


async def list_comments(
    db: AsyncSession,
    video_id: str,
    *,
    page: int,
    page_size: int,
    sort: str,
    user,
) -> PaginatedResponse:
    await videos_service.get_video(db, video_id, user)
    if sort not in SORTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid sort, expected newest or oldest",
        )
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    comments, total = await comments_repo.list_for_video(
        db,
        video_id,
        sort=sort,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return PaginatedResponse(
        items=await _serialize(db, comments),
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


async def create_comment(
    db: AsyncSession, video_id: str, body: CommentCreate, user: User
) -> CommentOut:
    await videos_service.get_video(db, video_id, user)
    if body.parent_id is not None:
        await _get_comment(db, video_id, body.parent_id)
    comment = await comments_repo.create(
        db,
        video_id=video_id,
        author_id=user.id,
        body=body.body,
        parent_id=body.parent_id,
    )
    return (await _serialize(db, [comment]))[0]


async def update_comment(
    db: AsyncSession, video_id: str, comment_id: str, body: CommentUpdate, user
) -> CommentOut:
    await videos_service.get_video(db, video_id, user)
    comment = await _get_comment(db, video_id, comment_id)
    if comment.author_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )
    comment = await comments_repo.save(db, comment, body.body)
    return (await _serialize(db, [comment]))[0]


async def delete_comment(
    db: AsyncSession, video_id: str, comment_id: str, user
) -> None:
    await videos_service.get_video(db, video_id, user)
    comment = await _get_comment(db, video_id, comment_id)
    if comment.author_id != user.id and not videos_service.is_moderator(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )
    await comments_repo.delete_comment(db, comment)