"""
Route-level tests for the API endpoints.

Strategy:
    - Auth dependencies (get_current_user, get_access_token) are overridden
      so no real session/token is needed.
    - SpotifyService methods are patched with AsyncMock to avoid real Spotify
      API calls — tests run offline and never touch real playlists.
    - The dry_run flag is tested to confirm it skips actual Spotify mutations.

Run with:
    poetry run pytest tests/test_routes.py -v
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_access_token, get_current_user
from app.main import app
from app.types import Playlist, PlaylistTrack, SpotifyUser

# ---------------------------------------------------------------------------
# Auth overrides — replaces real session + token validation
# ---------------------------------------------------------------------------

FAKE_USER = SpotifyUser(id="test_user_id", display_name="Test User", image_url=None)
FAKE_TOKEN = "fake_spotify_token"


def _override_user():
    return FAKE_USER


def _override_token():
    return FAKE_TOKEN


app.dependency_overrides[get_current_user] = _override_user
app.dependency_overrides[get_access_token] = _override_token

client = TestClient(app)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_track(
    position: int,
    name: str = "Track Name",
    artists: list[str] | None = None,
    uri: str | None = None,
    isrc: str | None = None,
) -> PlaylistTrack:
    return PlaylistTrack(
        position=position,
        uri=uri or f"spotify:track:fakeid{position:03d}",
        id=f"fakeid{position:03d}",
        name=name,
        artists=artists or ["Artist One"],
        album="Test Album",
        duration_ms=200_000,
        isrc=isrc,
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /api/playlists
# ---------------------------------------------------------------------------


def test_list_playlists_returns_liked_songs_first():
    fake_playlists = [
        Playlist(
            id="pl1",
            name="My Playlist",
            track_count=10,
            owner_id="test_user_id",
            owner_name="Test User",
            image_url=None,
            is_owner=True,
        )
    ]

    with (
        patch(
            "app.routers.playlists.SpotifyService.get_user_playlists",
            new_callable=AsyncMock,
            return_value=fake_playlists,
        ),
        patch(
            "app.routers.playlists.SpotifyService.get_liked_songs_count",
            new_callable=AsyncMock,
            return_value=42,
        ),
    ):
        resp = client.get("/api/playlists")

    assert resp.status_code == 200
    playlists = resp.json()["playlists"]
    assert playlists[0]["id"] == "liked_songs"
    assert playlists[0]["track_count"] == 42
    assert playlists[1]["id"] == "pl1"


# ---------------------------------------------------------------------------
# GET /api/playlists/{id}/tracks
# ---------------------------------------------------------------------------


def test_get_playlist_tracks():
    fake_tracks = [
        make_track(0, name="Song A"),
        make_track(1, name="Song B"),
    ]

    with (
        patch(
            "app.routers.playlists.SpotifyService.get_playlist_info",
            new_callable=AsyncMock,
            return_value={"id": "pl1", "name": "My Playlist"},
        ),
        patch(
            "app.routers.playlists.SpotifyService.get_playlist_tracks",
            new_callable=AsyncMock,
            return_value=fake_tracks,
        ),
    ):
        resp = client.get("/api/playlists/pl1/tracks")

    assert resp.status_code == 200
    data = resp.json()
    assert data["playlist_name"] == "My Playlist"
    assert len(data["tracks"]) == 2


def test_get_liked_songs_tracks():
    fake_tracks = [make_track(0, name="Liked Song")]

    with patch(
        "app.routers.playlists.SpotifyService.get_liked_songs_tracks",
        new_callable=AsyncMock,
        return_value=fake_tracks,
    ):
        resp = client.get("/api/playlists/liked_songs/tracks")

    assert resp.status_code == 200
    data = resp.json()
    assert data["playlist_name"] == "Liked Songs"
    assert data["tracks"][0]["name"] == "Liked Song"


# ---------------------------------------------------------------------------
# POST /api/duplicates/detect
# ---------------------------------------------------------------------------


def test_detect_no_duplicates():
    # Names and artists must be sufficiently different to avoid fuzzy matching
    tracks = [
        make_track(0, name="Stairway to Heaven", artists=["Led Zeppelin"]),
        make_track(1, name="Bohemian Rhapsody", artists=["Queen"]),
    ]
    resp = client.post(
        "/api/duplicates/detect",
        json={"playlist_id": "pl1", "tracks": [t.model_dump() for t in tracks]},
    )
    assert resp.status_code == 200
    assert resp.json()["total_duplicates"] == 0
    assert resp.json()["duplicate_groups"] == []


def test_detect_uri_duplicates():
    tracks = [
        make_track(0, uri="spotify:track:SAME"),
        make_track(1, uri="spotify:track:SAME"),
        make_track(2, uri="spotify:track:OTHER"),
    ]
    resp = client.post(
        "/api/duplicates/detect",
        json={"playlist_id": "pl1", "tracks": [t.model_dump() for t in tracks]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_duplicates"] == 1
    assert len(data["duplicate_groups"]) == 1
    assert data["duplicate_groups"][0]["match_method"] == "uri"


def test_detect_isrc_duplicates():
    tracks = [
        make_track(0, isrc="GB123456789", uri="spotify:track:A"),
        make_track(1, isrc="GB123456789", uri="spotify:track:B"),
    ]
    resp = client.post(
        "/api/duplicates/detect",
        json={"playlist_id": "pl1", "tracks": [t.model_dump() for t in tracks]},
    )
    data = resp.json()
    assert len(data["duplicate_groups"]) == 1
    assert data["duplicate_groups"][0]["match_method"] == "isrc"


# ---------------------------------------------------------------------------
# POST /api/duplicates/remove — dry_run=true (safe, no Spotify calls)
# ---------------------------------------------------------------------------


def test_remove_dry_run_does_not_call_spotify():
    """dry_run=true must return the correct count but never call Spotify."""
    mock_remove = AsyncMock()

    with patch(
        "app.routers.duplicates.SpotifyService.remove_tracks",
        mock_remove,
    ):
        resp = client.post(
            "/api/duplicates/remove?dry_run=true",
            json={
                "playlist_id": "pl1",
                "removals": [{"uri": "spotify:track:AAA", "positions": [3, 7]}],
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["dry_run"] is True
    assert data["removed_count"] == 2
    mock_remove.assert_not_called()  # ← Spotify was NOT touched


def test_remove_dry_run_liked_songs_does_not_call_spotify():
    mock_remove = AsyncMock()

    with patch(
        "app.routers.duplicates.SpotifyService.remove_liked_songs",
        mock_remove,
    ):
        resp = client.post(
            "/api/duplicates/remove?dry_run=true",
            json={
                "playlist_id": "liked_songs",
                "removals": [{"uri": "spotify:track:AAA", "positions": []}],
            },
        )

    assert resp.status_code == 200
    assert resp.json()["dry_run"] is True
    mock_remove.assert_not_called()


# ---------------------------------------------------------------------------
# POST /api/duplicates/remove — real removal (mocked Spotify)
# ---------------------------------------------------------------------------


def test_remove_calls_spotify_when_not_dry_run():
    mock_remove = AsyncMock(return_value="snapshot_abc")

    with patch(
        "app.routers.duplicates.SpotifyService.remove_tracks",
        mock_remove,
    ):
        resp = client.post(
            "/api/duplicates/remove",   # dry_run defaults to false
            json={
                "playlist_id": "pl1",
                "removals": [{"uri": "spotify:track:AAA", "positions": [3]}],
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["dry_run"] is False
    assert data["removed_count"] == 1
    assert data["snapshot_id"] == "snapshot_abc"
    mock_remove.assert_called_once()


def test_remove_liked_songs_calls_correct_api():
    mock_remove = AsyncMock()

    with patch(
        "app.routers.duplicates.SpotifyService.remove_liked_songs",
        mock_remove,
    ):
        resp = client.post(
            "/api/duplicates/remove",
            json={
                "playlist_id": "liked_songs",
                "removals": [{"uri": "spotify:track:4uLU6hMCjMI75M1A2tKUQC", "positions": []}],
            },
        )

    assert resp.status_code == 200
    mock_remove.assert_called_once_with(["4uLU6hMCjMI75M1A2tKUQC"])
