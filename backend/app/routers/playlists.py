from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.dependencies.auth import get_current_user, get_current_user_optional
from app.schemas.schemas import (
    PaginatedResponse,
    PlaylistCreate,
    PlaylistDetail,
    PlaylistItemAdd,
    PlaylistItemMove,
    PlaylistItemOut,
    PlaylistOut,
    PlaylistUpdate,
)
from app.services import playlists as playlists_service

router = APIRouter(prefix="/api/playlists", tags=["playlists"])


@router.post("/", response_model=PlaylistOut, status_code=status.HTTP_201_CREATED)
async def create_playlist(
    body: PlaylistCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await playlists_service.create_playlist(db, body, current_user)


@router.get("/{playlist_id}", response_model=PlaylistDetail)
async def get_playlist(
    playlist_id: str,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    playlist = await playlists_service.get_playlist(db, playlist_id, current_user)
    return await playlists_service.get_playlist_detail(db, playlist, current_user)


@router.patch("/{playlist_id}", response_model=PlaylistOut)
async def update_playlist(
    playlist_id: str,
    body: PlaylistUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await playlists_service.update_playlist(
        db, playlist_id, body, current_user
    )


@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playlist(
    playlist_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await playlists_service.delete_playlist(db, playlist_id, current_user)


@router.post("/{playlist_id}/items", response_model=PlaylistItemOut, status_code=status.HTTP_201_CREATED)
async def add_item(
    playlist_id: str,
    body: PlaylistItemAdd,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await playlists_service.add_item(
        db, playlist_id, body.video_id, current_user
    )


@router.delete("/{playlist_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item(
    playlist_id: str,
    item_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await playlists_service.remove_item(db, playlist_id, item_id, current_user)


@router.patch("/{playlist_id}/items/{item_id}/position")
async def move_item(
    playlist_id: str,
    item_id: str,
    body: PlaylistItemMove,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await playlists_service.move_item(
        db, playlist_id, item_id, body.position, current_user
    )