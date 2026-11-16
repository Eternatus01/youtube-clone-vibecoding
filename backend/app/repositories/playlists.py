from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Playlist, PlaylistItem, Visibility


async def get(db: AsyncSession, playlist_id: str) -> Playlist | None:
    result = await db.execute(select(Playlist).where(Playlist.id == playlist_id))
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    *,
    owner_id: str,
    title: str,
    description: str | None,
    visibility: Visibility,
) -> Playlist:
    playlist = Playlist(
        owner_id=owner_id,
        title=title,
        description=description,
        visibility=visibility,
    )
    db.add(playlist)
    await db.commit()
    await db.refresh(playlist)
    return playlist


async def save(db: AsyncSession, playlist: Playlist) -> Playlist:
    await db.commit()
    await db.refresh(playlist)
    return playlist


async def delete_playlist(db: AsyncSession, playlist: Playlist) -> None:
    await db.delete(playlist)
    await db.commit()


async def item_counts(db: AsyncSession, playlist_ids: list[str]) -> dict[str, int]:
    if not playlist_ids:
        return {}
    result = await db.execute(
        select(PlaylistItem.playlist_id, func.count(PlaylistItem.id))
        .where(PlaylistItem.playlist_id.in_(playlist_ids))
        .group_by(PlaylistItem.playlist_id)
    )
    return {playlist_id: int(count) for playlist_id, count in result.all()}


async def list_by_owner(
    db: AsyncSession,
    owner_id: str,
    *,
    offset: int,
    limit: int,
) -> tuple[list[Playlist], int]:
    conditions = [
        Playlist.owner_id == owner_id,
        Playlist.visibility == Visibility.public,
    ]
    total = await db.scalar(select(func.count(Playlist.id)).where(*conditions))
    result = await db.execute(
        select(Playlist)
        .where(*conditions)
        .order_by(Playlist.created_at.desc(), Playlist.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), int(total or 0)


async def list_items(db: AsyncSession, playlist_id: str) -> list[PlaylistItem]:
    result = await db.execute(
        select(PlaylistItem)
        .where(PlaylistItem.playlist_id == playlist_id)
        .order_by(PlaylistItem.position.asc(), PlaylistItem.created_at.asc())
    )
    return list(result.scalars().all())


async def get_item(
    db: AsyncSession, playlist_id: str, item_id: str
) -> PlaylistItem | None:
    result = await db.execute(
        select(PlaylistItem).where(
            PlaylistItem.id == item_id, PlaylistItem.playlist_id == playlist_id
        )
    )
    return result.scalar_one_or_none()


async def find_item_by_video(
    db: AsyncSession, playlist_id: str, video_id: str
) -> PlaylistItem | None:
    result = await db.execute(
        select(PlaylistItem).where(
            PlaylistItem.playlist_id == playlist_id,
            PlaylistItem.video_id == video_id,
        )
    )
    return result.scalar_one_or_none()


async def next_position(db: AsyncSession, playlist_id: str) -> int:
    last = await db.scalar(
        select(func.max(PlaylistItem.position)).where(
            PlaylistItem.playlist_id == playlist_id
        )
    )
    return 0 if last is None else int(last) + 1


async def add_item(
    db: AsyncSession,
    *,
    playlist_id: str,
    video_id: str,
    position: int,
) -> PlaylistItem:
    item = PlaylistItem(playlist_id=playlist_id, video_id=video_id, position=position)
    db.add(item)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
    await db.refresh(item)
    return item


async def delete_item(db: AsyncSession, item: PlaylistItem) -> None:
    await db.delete(item)
    await db.commit()


async def reindex(db: AsyncSession, items: list[PlaylistItem]) -> None:
    """Rewrite positions so the list is dense and starts at zero."""
    changed = False
    for index, item in enumerate(items):
        if item.position != index:
            item.position = index
            changed = True
    if changed:
        await db.commit()
    else:
        await db.flush()