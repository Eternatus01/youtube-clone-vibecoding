from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Playlist, Visibility
from app.repositories import playlists as playlists_repo
from app.repositories import users as users_repo
from app.repositories import videos as videos_repo
from app.schemas.schemas import (
    PlaylistCreate,
    PlaylistDetail,
    PlaylistItemOut,
    PlaylistOut,
    PlaylistUpdate,
    UserOut,
    VideoOut,
)
from app.services import videos as videos_service


def _parse_visibility(value: str) -> Visibility:
    try:
        return Visibility(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid visibility"
        )


def ensure_can_view_playlist(playlist: Playlist, user) -> None:
    if playlist.visibility == Visibility.public:
        return
    if playlist.visibility == Visibility.hidden:
        if not videos_service.is_moderator(user):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found"
            )
        return
    if user is None or (
        playlist.owner_id != user.id and not videos_service.is_moderator(user)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )


def ensure_can_edit_playlist(playlist: Playlist, user) -> None:
    if playlist.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )


async def _owners(db: AsyncSession, playlists: list[Playlist]) -> dict[str, UserOut]:
    owner_ids = {p.owner_id for p in playlists}
    owners = await users_repo.get_many(db, list(owner_ids))
    return {owner.id: UserOut.model_validate(owner) for owner in owners}


async def serialize_playlists(
    db: AsyncSession, playlists: list[Playlist]
) -> list[PlaylistOut]:
    counts = await playlists_repo.item_counts(db, [p.id for p in playlists])
    owners = await _owners(db, playlists)
    result: list[PlaylistOut] = []
    for playlist in playlists:
        out = PlaylistOut.model_validate(playlist)
        result.append(
            out.model_copy(
                update={
                    "owner": owners.get(playlist.owner_id),
                    "item_count": counts.get(playlist.id, 0),
                }
            )
        )
    return result


async def serialize_playlist(db: AsyncSession, playlist: Playlist) -> PlaylistOut:
    return (await serialize_playlists(db, [playlist]))[0]


def _item_video_visible(playlist: Playlist, video: VideoOut | None, user) -> bool:
    if video is None:
        return True
    if user is not None and (
        playlist.owner_id == user.id or videos_service.is_moderator(user)
    ):
        return True
    return video.visibility == Visibility.public and video.status == "ready"


async def get_playlist_detail(
    db: AsyncSession, playlist: Playlist, user
) -> PlaylistDetail:
    base = await serialize_playlist(db, playlist)
    items = await playlists_repo.list_items(db, playlist.id)
    videos = await videos_repo.get_many(db, [item.video_id for item in items])
    serialized = await videos_service.serialize_videos(db, videos, user)
    by_id = {video.id: video for video in serialized}

    item_outs: list[PlaylistItemOut] = []
    for item in items:
        video = by_id.get(item.video_id)
        if not _item_video_visible(playlist, video, user):
            continue
        out = PlaylistItemOut.model_validate(item)
        item_outs.append(
            out.model_copy(update={"video": video})
        )
    return PlaylistDetail(**base.model_dump(), items=item_outs)


async def get_playlist(db: AsyncSession, playlist_id: str, user) -> Playlist:
    playlist = await playlists_repo.get(db, playlist_id)
    if playlist is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found"
        )
    ensure_can_view_playlist(playlist, user)
    return playlist


async def list_channel_playlists(
    db: AsyncSession,
    channel_id: str,
    *,
    page: int,
    page_size: int,
) -> tuple[list[PlaylistOut], int, int, int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    playlists, total = await playlists_repo.list_by_owner(
        db, channel_id, offset=(page - 1) * page_size, limit=page_size
    )
    return (
        await serialize_playlists(db, playlists),
        total,
        page,
        page_size,
    )


async def create_playlist(
    db: AsyncSession, body: PlaylistCreate, user
) -> PlaylistOut:
    playlist = await playlists_repo.create(
        db,
        owner_id=user.id,
        title=body.title,
        description=body.description,
        visibility=_parse_visibility(body.visibility),
    )
    return await serialize_playlist(db, playlist)


async def update_playlist(
    db: AsyncSession, playlist_id: str, body: PlaylistUpdate, user
) -> PlaylistOut:
    playlist = await get_playlist(db, playlist_id, user)
    ensure_can_edit_playlist(playlist, user)
    if body.title is not None:
        playlist.title = body.title
    if body.description is not None:
        playlist.description = body.description
    if body.visibility is not None:
        playlist.visibility = _parse_visibility(body.visibility)
    await playlists_repo.save(db, playlist)
    return await serialize_playlist(db, playlist)


async def delete_playlist(db: AsyncSession, playlist_id: str, user) -> None:
    playlist = await get_playlist(db, playlist_id, user)
    ensure_can_edit_playlist(playlist, user)
    await playlists_repo.delete_playlist(db, playlist)


async def add_item(db: AsyncSession, playlist_id: str, video_id: str, user) -> PlaylistItemOut:
    playlist = await get_playlist(db, playlist_id, user)
    ensure_can_edit_playlist(playlist, user)
    video = await videos_repo.get(db, video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Video not found"
        )
    videos_service.ensure_can_view(video, user)

    existing = await playlists_repo.find_item_by_video(db, playlist.id, video.id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Video already in playlist",
        )

    position = await playlists_repo.next_position(db, playlist.id)
    item = await playlists_repo.add_item(
        db, playlist_id=playlist.id, video_id=video.id, position=position
    )
    serialized = (await videos_service.serialize_videos(db, [video], user))[0]
    out = PlaylistItemOut.model_validate(item)
    return out.model_copy(update={"video": serialized})


async def remove_item(
    db: AsyncSession, playlist_id: str, item_id: str, user
) -> None:
    playlist = await get_playlist(db, playlist_id, user)
    ensure_can_edit_playlist(playlist, user)
    item = await playlists_repo.get_item(db, playlist.id, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Playlist item not found"
        )
    await playlists_repo.delete_item(db, item)
    # Keep positions dense after removal.
    await playlists_repo.reindex(db, await playlists_repo.list_items(db, playlist.id))


async def move_item(
    db: AsyncSession, playlist_id: str, item_id: str, position: int, user
) -> PlaylistDetail:
    playlist = await get_playlist(db, playlist_id, user)
    ensure_can_edit_playlist(playlist, user)
    items = await playlists_repo.list_items(db, playlist.id)
    index = next((i for i, item in enumerate(items) if item.id == item_id), None)
    if index is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Playlist item not found"
        )
    moved = items.pop(index)
    target = min(max(position, 0), len(items))
    items.insert(target, moved)
    await playlists_repo.reindex(db, items)
    return await get_playlist_detail(db, playlist, user)