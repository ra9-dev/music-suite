"""
Playlist routes.

GET /api/playlists             — list all playlists + Liked Songs at the top
GET /api/playlists/{id}/tracks — fetch every track in a playlist or Liked Songs

Liked Songs (id = "liked_songs") is a special case: it lives at /me/tracks
rather than being a real Spotify playlist, so it is injected manually.
"""

import asyncio

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_access_token, get_current_user
from app.services.spotify import LIKED_SONGS_ID, SpotifyService
from app.types import Playlist, SpotifyUser

router = APIRouter(prefix="/api/playlists", tags=["playlists"])


@router.get("", summary="List all user playlists")
async def list_playlists(
    user: SpotifyUser = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
) -> dict:
    """
    Return all playlists the user owns or follows, with Liked Songs prepended.

    Liked Songs uses the sentinel id "liked_songs" and is always shown first
    since it's typically the largest and most-used collection.
    """
    spotify = SpotifyService(access_token)

    # Fetch regular playlists and liked-songs count concurrently
    playlists, liked_count = await asyncio.gather(
        spotify.get_user_playlists(user.id),
        spotify.get_liked_songs_count(),
    )

    liked_songs = Playlist(
        id=LIKED_SONGS_ID,
        name="Liked Songs",
        description=None,
        track_count=liked_count,
        owner_id=user.id,
        owner_name=user.display_name,
        image_url=None,
        is_owner=True,          # user always owns their liked songs
        is_collaborative=False,
    )

    return {"playlists": [liked_songs.model_dump(), *[p.model_dump() for p in playlists]]}


@router.get("/{playlist_id}/tracks", summary="Fetch all tracks in a playlist")
async def get_tracks(
    playlist_id: str,
    user: SpotifyUser = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
) -> dict:
    """
    Return every track in a playlist or in Liked Songs.

    For regular playlists: fetches from /playlists/{id}/tracks (with positions).
    For Liked Songs (id = "liked_songs"): fetches from /me/tracks.
    """
    spotify = SpotifyService(access_token)

    try:
        if playlist_id == LIKED_SONGS_ID:
            tracks = await spotify.get_liked_songs_tracks()
            return {
                "playlist_id": LIKED_SONGS_ID,
                "playlist_name": "Liked Songs",
                "tracks": [t.model_dump() for t in tracks],
            }

        playlist_info, tracks = await asyncio.gather(
            spotify.get_playlist_info(playlist_id),
            spotify.get_playlist_tracks(playlist_id),
        )

        return {
            "playlist_id": playlist_id,
            "playlist_name": playlist_info.get("name", "Unknown Playlist"),
            "tracks": [t.model_dump() for t in tracks],
        }

    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 403:
            raise HTTPException(
                status_code=403,
                detail="Spotify denied access to this playlist. You may not have permission to read it.",
            )
        if status == 404:
            raise HTTPException(status_code=404, detail="Playlist not found on Spotify.")
        raise HTTPException(status_code=502, detail=f"Spotify API error: {status}")
