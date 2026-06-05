"""
Spotify API service.

Wraps all Spotify Web API calls behind a clean async interface.
Each public method is self-contained: it opens an httpx client,
makes the necessary (paginated) requests, and returns typed results.

Token refresh is handled externally by the `get_access_token` dependency
in dependencies.py before this service is constructed.

Spotify API reference: https://developer.spotify.com/documentation/web-api
"""

import asyncio

import httpx

from app.types import Playlist, PlaylistTrack, SpotifyUser
from app.utils.paginate import paginate_spotify

SPOTIFY_API_BASE = "https://api.spotify.com/v1"

# Sentinel ID used throughout the app to represent the Liked Songs collection.
# Liked Songs is not a real playlist — it lives at /me/tracks and uses a
# different removal API (DELETE /me/tracks with track IDs, not positions).
LIKED_SONGS_ID = "liked_songs"


class SpotifyService:
    """
    Lightweight wrapper around the Spotify Web API.

    Construct with a valid access token; the token is attached to every request.
    """

    def __init__(self, access_token: str) -> None:
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # User
    # ------------------------------------------------------------------

    async def get_current_user(self) -> SpotifyUser:
        """Fetch the authenticated user's profile."""
        async with httpx.AsyncClient() as client:
            resp = await self._get(client, f"{SPOTIFY_API_BASE}/me")
            data = resp.json()
            image_url = data["images"][0]["url"] if data.get("images") else None
            return SpotifyUser(
                id=data["id"],
                display_name=data.get("display_name") or data["id"],
                image_url=image_url,
            )

    # ------------------------------------------------------------------
    # Playlists
    # ------------------------------------------------------------------

    async def get_user_playlists(self, user_id: str) -> list[Playlist]:
        """
        Fetch all playlists the authenticated user owns or follows.

        Paginates automatically (Spotify max 50 per page).
        Sets `is_owner` by comparing each playlist's owner ID to `user_id`.
        """
        async with httpx.AsyncClient() as client:
            playlists: list[Playlist] = []
            async for item in paginate_spotify(
                client,
                f"{SPOTIFY_API_BASE}/me/playlists",
                self._headers,
                limit=50,
            ):
                # Spotify can return None items or non-playlist types (e.g. podcast shows)
                if not item or not item.get("id"):
                    continue
                image_url = item["images"][0]["url"] if item.get("images") else None
                playlists.append(
                    Playlist(
                        id=item["id"],
                        name=item.get("name", "Unnamed Playlist"),
                        description=item.get("description") or None,
                        # "tracks" may be absent on non-music collections
                        track_count=item.get("tracks", {}).get("total", 0),
                        owner_id=item["owner"]["id"],
                        owner_name=item["owner"].get("display_name") or item["owner"]["id"],
                        image_url=image_url,
                        is_owner=item["owner"]["id"] == user_id,
                        is_collaborative=item.get("collaborative", False),
                    )
                )
        return playlists

    async def get_liked_songs_count(self) -> int:
        """Return the total number of tracks in the user's Liked Songs."""
        async with httpx.AsyncClient() as client:
            resp = await self._get(
                client,
                f"{SPOTIFY_API_BASE}/me/tracks",
                params={"limit": 1},
            )
            return resp.json().get("total", 0)

    async def get_liked_songs_tracks(self) -> list[PlaylistTrack]:
        """
        Fetch every track from the user's Liked Songs (GET /me/tracks).

        Liked Songs is a set — the same track cannot be added twice — so URI
        duplicates won't exist here. Only ISRC and fuzzy duplicates are possible.
        Positions are assigned sequentially for display purposes; they are NOT
        used for removal (removal uses track IDs via DELETE /me/tracks).
        """
        async with httpx.AsyncClient() as client:
            tracks: list[PlaylistTrack] = []
            position = 0

            async for item in paginate_spotify(
                client,
                f"{SPOTIFY_API_BASE}/me/tracks",
                self._headers,
                limit=50,
            ):
                track = item.get("track") if item else None
                if not track or track.get("type") != "track":
                    position += 1
                    continue

                isrc = track.get("external_ids", {}).get("isrc") or None
                artists = [a["name"] for a in track.get("artists", [])]
                album = track.get("album", {})
                images = album.get("images") or []
                image_url = images[0]["url"] if images else None

                tracks.append(
                    PlaylistTrack(
                        position=position,
                        uri=track["uri"],
                        id=track["id"],
                        name=track["name"],
                        artists=artists,
                        album=album.get("name", ""),
                        image_url=image_url,
                        duration_ms=track.get("duration_ms", 0),
                        isrc=isrc,
                        added_at=item.get("added_at"),
                        added_by=None,  # Liked Songs has no added_by
                    )
                )
                position += 1

        return tracks

    async def remove_liked_songs(self, track_uris: list[str]) -> None:
        """
        Remove tracks from Liked Songs via DELETE /me/library.

        Uses Spotify URIs (e.g. spotify:track:xxx) passed as the `uris` query
        param. Max 40 URIs per request.
        """
        async with httpx.AsyncClient() as client:
            for i in range(0, max(len(track_uris), 1), 40):
                batch = track_uris[i : i + 40]
                resp = await client.request(
                    "DELETE",
                    f"{SPOTIFY_API_BASE}/me/library",
                    headers=self._headers,
                    params={"uris": ",".join(batch)},
                )
                if resp.status_code == 429:
                    await asyncio.sleep(int(resp.headers.get("Retry-After", 1)))
                    resp = await client.request(
                        "DELETE",
                        f"{SPOTIFY_API_BASE}/me/library",
                        headers=self._headers,
                        params={"uris": ",".join(batch)},
                    )
                resp.raise_for_status()

    async def get_playlist_info(self, playlist_id: str) -> dict:
        """Fetch basic playlist metadata (id, name)."""
        async with httpx.AsyncClient() as client:
            resp = await self._get(
                client,
                f"{SPOTIFY_API_BASE}/playlists/{playlist_id}",
                params={"fields": "id,name"},
            )
            return resp.json()

    async def get_playlist_tracks(self, playlist_id: str) -> list[PlaylistTrack]:
        """
        Fetch every track in a playlist, preserving their exact positions.

        Position is the 0-based index in the playlist and is required for
        the Spotify DELETE API to remove the correct copy of a duplicate.

        Non-track items (podcast episodes, local files, deleted entries)
        are skipped but their positions are still counted so that remaining
        track positions remain accurate.
        """
        async with httpx.AsyncClient() as client:
            tracks: list[PlaylistTrack] = []
            position = 0

            # No `fields` filter — Spotify returns 403 on certain playlist types
            # (collaborative, followed-but-not-owned, etc.) when fields are specified.
            # Fetching the full response is slightly heavier but universally compatible.
            async for item in paginate_spotify(
                client,
                f"{SPOTIFY_API_BASE}/playlists/{playlist_id}/items",
                self._headers,
                limit=50,
            ):
                # /items endpoint uses "item" field; fall back to "track" for compat
                track = (item.get("item") or item.get("track")) if item else None

                # Skip deleted tracks (track is None) and non-track types
                if not track or track.get("type") != "track":
                    position += 1
                    continue

                isrc = track.get("external_ids", {}).get("isrc") or None
                artists = [a["name"] for a in track.get("artists", [])]
                album = track.get("album", {})
                images = album.get("images") or []
                image_url = images[0]["url"] if images else None
                added_by_data = item.get("added_by")

                tracks.append(
                    PlaylistTrack(
                        position=position,
                        uri=track["uri"],
                        id=track["id"],
                        name=track["name"],
                        artists=artists,
                        album=album.get("name", ""),
                        image_url=image_url,
                        duration_ms=track.get("duration_ms", 0),
                        isrc=isrc,
                        added_at=item.get("added_at"),
                        added_by=added_by_data.get("id") if added_by_data else None,
                    )
                )
                position += 1

        return tracks

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    async def remove_tracks(
        self,
        playlist_id: str,
        removals: list[dict],
    ) -> str:
        """
        Remove specific track positions from a playlist.

        Args:
            playlist_id: Spotify playlist ID.
            removals: List of {"uri": "spotify:track:...", "positions": [n, m, ...]}.
                      Positions MUST be included to avoid removing unintended copies.

        Returns:
            The new snapshot_id from Spotify (represents the playlist's state).

        Notes:
            - Spotify allows max 100 tracks per DELETE request; this method batches.
            - Sort positions descending before calling to avoid index drift in
              multi-batch operations (highest positions are removed first).
        """
        async with httpx.AsyncClient() as client:
            snapshot_id = ""
            # Batch into groups of 100 (Spotify's per-request limit)
            for i in range(0, max(len(removals), 1), 100):
                batch = removals[i : i + 100]
                resp = await self._delete_tracks(client, playlist_id, batch)
                snapshot_id = resp.json().get("snapshot_id", "")
            return snapshot_id

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: dict | None = None,
    ) -> httpx.Response:
        """GET with automatic 429 retry."""
        resp = await client.get(url, headers=self._headers, params=params)
        if resp.status_code == 429:
            await asyncio.sleep(int(resp.headers.get("Retry-After", 1)))
            resp = await client.get(url, headers=self._headers, params=params)
        resp.raise_for_status()
        return resp

    async def _delete_tracks(
        self,
        client: httpx.AsyncClient,
        playlist_id: str,
        batch: list[dict],
    ) -> httpx.Response:
        """DELETE playlist tracks with 429 retry."""
        resp = await client.request(
            "DELETE",
            f"{SPOTIFY_API_BASE}/playlists/{playlist_id}/items",
            headers=self._headers,
            json={"tracks": batch},  # "tracks" key still accepted by /items endpoint
        )
        if resp.status_code == 429:
            await asyncio.sleep(int(resp.headers.get("Retry-After", 1)))
            resp = await client.request(
                "DELETE",
                f"{SPOTIFY_API_BASE}/playlists/{playlist_id}/items",
                headers=self._headers,
                json={"tracks": batch},
            )
        resp.raise_for_status()
        return resp
