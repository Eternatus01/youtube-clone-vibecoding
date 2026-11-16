from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.dependencies.auth import get_current_user, get_current_user_optional
from app.schemas.schemas import (
    LikeInfo,
    PaginatedResponse,
    VideoOut,
    VideoShareCreate,
    VideoShareOut,
    VideoUpdate,
)
from app.services import likes as likes_service
from app.services import shares as shares_service
from app.services import videos as videos_service

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.get("/", response_model=PaginatedResponse)
async def list_videos(
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    return await videos_service.list_feed(
        db, page=page, page_size=page_size, search=search, user=current_user
    )


@router.get("/mine", response_model=PaginatedResponse)
async def my_videos(
    page: int = 1,
    page_size: int = 20,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await videos_service.list_mine(
        db, page=page, page_size=page_size, user=current_user
    )


@router.get("/{video_id}", response_model=VideoOut)
async def get_video(
    video_id: str,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    video = await videos_service.get_video(db, video_id, current_user)
    await videos_service.register_view(db, video, current_user)
    return await videos_service.serialize_video(db, video, current_user)


@router.patch("/{video_id}", response_model=VideoOut)
async def update_video(
    video_id: str,
    body: VideoUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    video = await videos_service.get_video(db, video_id, current_user)
    return await videos_service.update_video(db, video, body, current_user)


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    video_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    video = await videos_service.get_video(db, video_id, current_user)
    await videos_service.delete_video(db, video, current_user)


@router.get("/{video_id}/shares", response_model=list[VideoShareOut])
async def list_shares(
    video_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    video = await videos_service.get_video(db, video_id, current_user)
    return await shares_service.list_shares(db, video, current_user)


@router.post("/{video_id}/shares", response_model=VideoShareOut, status_code=status.HTTP_201_CREATED)
async def add_share(
    video_id: str,
    body: VideoShareCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    video = await videos_service.get_video(db, video_id, current_user)
    return await shares_service.add_share(db, video, body, current_user)


@router.delete("/{video_id}/shares/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_share(
    video_id: str,
    user_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    video = await videos_service.get_video(db, video_id, current_user)
    await shares_service.remove_share(db, video, user_id, current_user)


def _iter_body(body, chunk_size: int = 64 * 1024):
    if hasattr(body, "iter_chunks"):
        yield from body.iter_chunks(chunk_size)
        return
    while True:
        chunk = body.read(chunk_size)
        if not chunk:
            break
        yield chunk


def _media_response(obj, default_media_type: str) -> StreamingResponse:
    content_range = obj.get("ContentRange")
    headers = {"Accept-Ranges": "bytes"}
    if content_range:
        headers["Content-Range"] = content_range
    if obj.get("ContentLength") is not None:
        headers["Content-Length"] = str(obj["ContentLength"])
    return StreamingResponse(
        _iter_body(obj["Body"]),
        status_code=206 if content_range else 200,
        media_type=obj.get("ContentType") or default_media_type,
        headers=headers,
    )


@router.get("/{video_id}/stream")
async def stream_video(
    video_id: str,
    request: Request,
    quality: str | None = None,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Proxies a range request to SeaweedFS for the video asset."""
    video = await videos_service.get_video(db, video_id, current_user)
    assets = await videos_service.get_assets(db, video.id)
    asset = videos_service.choose_stream_asset(assets, quality)
    obj = await videos_service.open_media(asset.object_key, request.headers.get("range"))
    return _media_response(obj, asset.content_type or "video/mp4")


@router.get("/{video_id}/poster")
async def get_poster(
    video_id: str,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Proxies the video poster/thumbnail image. Same authz as get_video."""
    video = await videos_service.get_video(db, video_id, current_user)
    assets = await videos_service.get_assets(db, video.id)
    asset = videos_service.choose_poster_asset(assets)
    obj = await videos_service.open_media(asset.object_key, None)
    return _media_response(obj, "image/jpeg")


@router.post("/{video_id}/like", response_model=LikeInfo)
async def like_video(
    video_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await likes_service.like_video(db, video_id, current_user)


@router.delete("/{video_id}/like", response_model=LikeInfo)
async def unlike_video(
    video_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await likes_service.unlike_video(db, video_id, current_user)


@router.get("/{video_id}/related", response_model=PaginatedResponse)
async def related_videos(
    video_id: str,
    page: int = 1,
    page_size: int = 10,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    video = await videos_service.get_video(db, video_id, current_user)
    return await videos_service.list_related(
        db, video, page=page, page_size=page_size, user=current_user
    )