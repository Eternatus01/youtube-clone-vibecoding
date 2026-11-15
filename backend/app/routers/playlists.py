from fastapi import APIRouter, Depends, status

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

router = APIRouter(prefix="/api/playlists", tags=["playlists"])


@router.post("/", response_model=PlaylistOut, status_code=status.HTTP_201_CREATED)
async def create_playlist(body: PlaylistCreate, current_user=Depends(get_current_user)):
    raise NotImplementedError


@router.get("/{playlist_id}", response_model=PlaylistDetail)
async def get_playlist(playlist_id: str, current_user=Depends(get_current_user_optional)):
    raise NotImplementedError


@router.patch("/{playlist_id}", response_model=PlaylistOut)
async def update_playlist(
    playlist_id: str,
    body: PlaylistUpdate,
    current_user=Depends(get_current_user),
):
    raise NotImplementedError


@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playlist(playlist_id: str, current_user=Depends(get_current_user)):
    raise NotImplementedError


@router.post("/{playlist_id}/items", response_model=PlaylistItemOut, status_code=status.HTTP_201_CREATED)
async def add_item(
    playlist_id: str,
    body: PlaylistItemAdd,
    current_user=Depends(get_current_user),
):
    raise NotImplementedError


@router.delete("/{playlist_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item(playlist_id: str, item_id: str, current_user=Depends(get_current_user)):
    raise NotImplementedError


@router.patch("/{playlist_id}/items/{item_id}/position")
async def move_item(
    playlist_id: str,
    item_id: str,
    body: PlaylistItemMove,
    current_user=Depends(get_current_user),
):
    raise NotImplementedError