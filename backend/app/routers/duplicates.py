"""
Duplicate detection and removal routes.

POST /api/duplicates/detect  — analyse a track list and return duplicate groups
POST /api/duplicates/remove  — remove specific track positions from a playlist

Design decision:
    The frontend fetches the track list from /api/playlists/{id}/tracks and then
    passes it to /detect. This avoids a redundant Spotify API round-trip, since
    the frontend already has the data and detection is a pure computation.
"""

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_access_token, get_current_user
from app.services.duplicates import detect_duplicates
from app.services.spotify import LIKED_SONGS_ID, SpotifyService
from app.types import DetectDuplicatesRequest, RemoveDuplicatesRequest, SpotifyUser

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/duplicates", tags=["duplicates"])


@router.post("/detect", summary="Detect duplicate tracks in a playlist")
async def detect(
    body: DetectDuplicatesRequest,
    user: SpotifyUser = Depends(get_current_user),
    _: str = Depends(get_access_token),   # validates session / refreshes token
) -> dict:
    """
    Run duplicate detection on the provided track list.

    Three passes are run in priority order:
        1. URI equality    — same track added twice
        2. ISRC equality   — same recording, different edition
        3. Fuzzy matching  — similar title + artist (remasters, live versions, etc.)

    Each group in the response includes a `match_method` and, for fuzzy matches,
    a `fuzzy_score` (0–100) so the frontend can show confidence to the user.

    Request body:
        { "playlist_id": "...", "tracks": [ PlaylistTrack, ... ] }

    Response:
        {
            "playlist_id": "...",
            "duplicate_groups": [ DuplicateGroup, ... ],
            "total_duplicates": 3   // total number of tracks that are duplicates
        }
    """
    groups = detect_duplicates(body.tracks)
    total_duplicates = sum(len(g.tracks) - 1 for g in groups)

    return {
        "playlist_id": body.playlist_id,
        "duplicate_groups": [g.model_dump() for g in groups],
        "total_duplicates": total_duplicates,
    }


@router.post("/remove", summary="Remove selected duplicate tracks from a playlist")
async def remove(
    body: RemoveDuplicatesRequest,
    dry_run: bool = Query(
        default=False,
        description=(
            "When true, calculate what WOULD be removed but do not call Spotify. "
            "Use this for testing to avoid mutating real playlists."
        ),
    ),
    user: SpotifyUser = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
) -> dict:
    """
    Remove specific track positions from a Spotify playlist.

    Pass ?dry_run=true to simulate the removal without touching Spotify —
    the response shows exactly what would have been removed.

    Request body:
        {
            "playlist_id": "...",
            "removals": [{ "uri": "spotify:track:...", "positions": [17, 31] }]
        }

    Response:
        { "ok": true, "dry_run": false, "removed_count": 2, "playlist_id": "...", "snapshot_id": "..." }
    """
    # Liked Songs: DELETE /me/tracks with track IDs (no positions)
    if body.playlist_id == LIKED_SONGS_ID:
        track_uris = [r.uri for r in body.removals if r.uri]
        if not dry_run:
            spotify = SpotifyService(access_token)
            try:
                await spotify.remove_liked_songs(track_uris)
            except httpx.HTTPStatusError as e:
                log.error(
                    "remove_liked_songs: Spotify %s — %s",
                    e.response.status_code,
                    e.response.text,
                )
                if e.response.status_code == 403:
                    raise HTTPException(
                        status_code=403,
                        detail="Missing user-library-modify scope. Log out and log in again to re-authorize.",
                    )
                raise
        return {
            "ok": True,
            "dry_run": dry_run,
            "removed_count": len(track_uris),
            "playlist_id": body.playlist_id,
            "snapshot_id": "",
        }

    # Regular playlists: sort positions descending to prevent index drift
    sorted_removals = [
        {"uri": r.uri, "positions": sorted(r.positions, reverse=True)}
        for r in body.removals
    ]
    sorted_removals.sort(
        key=lambda r: max(r["positions"]) if r["positions"] else 0,
        reverse=True,
    )
    removed_count = sum(len(r["positions"]) for r in sorted_removals)

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "removed_count": removed_count,
            "playlist_id": body.playlist_id,
            "snapshot_id": "",
        }

    spotify = SpotifyService(access_token)
    snapshot_id = await spotify.remove_tracks(body.playlist_id, sorted_removals)

    return {
        "ok": True,
        "dry_run": False,
        "removed_count": removed_count,
        "playlist_id": body.playlist_id,
        "snapshot_id": snapshot_id,
    }
