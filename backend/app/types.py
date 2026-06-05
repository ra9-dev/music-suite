"""
Shared Pydantic models used across routers, services, and tests.

These models define the shape of data flowing through the API.
The frontend TypeScript types in frontend/src/types/index.ts mirror these exactly.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Spotify entities
# ---------------------------------------------------------------------------


class SpotifyUser(BaseModel):
    id: str
    display_name: str
    image_url: Optional[str] = None


class Playlist(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    track_count: int
    owner_id: str
    owner_name: str
    image_url: Optional[str] = None
    # True if the authenticated user owns this playlist
    is_owner: bool
    # True if the playlist is collaborative (non-owners can edit)
    is_collaborative: bool = False


class PlaylistTrack(BaseModel):
    # 0-based index of this track in the playlist (including episodes/local files)
    # Critical for the Spotify DELETE API — must be exact
    position: int
    uri: str            # e.g. "spotify:track:4uLU6hMCjMI75M1A2tKUQC"
    id: str
    name: str
    artists: list[str]  # ordered list of artist names
    album: str
    image_url: Optional[str] = None  # album cover art from Spotify
    duration_ms: int
    # International Standard Recording Code — uniquely identifies a recording
    # May be None for older or non-commercial tracks
    isrc: Optional[str] = None
    added_at: Optional[str] = None   # ISO 8601 datetime string
    added_by: Optional[str] = None   # Spotify user ID who added the track


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------


class MatchMethod(str, Enum):
    """How a duplicate group was detected."""
    uri = "uri"       # Identical Spotify track URI added twice
    isrc = "isrc"     # Same recording via different album editions (same ISRC)
    fuzzy = "fuzzy"   # Similar title + artist (catches remasters, live versions, etc.)


class DuplicateGroup(BaseModel):
    group_id: str                    # UUID, stable within a detection run
    match_method: MatchMethod
    fuzzy_score: Optional[int] = None  # 0–100, only set for fuzzy matches
    tracks: list[PlaylistTrack]      # 2 or more tracks that are considered duplicates


# ---------------------------------------------------------------------------
# API request / response bodies
# ---------------------------------------------------------------------------


class DetectDuplicatesRequest(BaseModel):
    playlist_id: str
    # The frontend passes back the full track list it fetched.
    # This avoids a redundant Spotify API call in the detect endpoint.
    tracks: list[PlaylistTrack]


class RemovalItem(BaseModel):
    uri: str
    # Exact playlist positions to remove.
    # MUST be included — omitting positions causes Spotify to remove ALL occurrences.
    positions: list[int]


class RemoveDuplicatesRequest(BaseModel):
    playlist_id: str
    removals: list[RemovalItem]
