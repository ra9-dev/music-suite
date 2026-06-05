"""
Unit tests for the duplicate detection service.

Run with:
    poetry run pytest tests/ -v
"""

import pytest

from app.services.duplicates import detect_duplicates
from app.types import MatchMethod, PlaylistTrack


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_track(
    position: int,
    name: str = "Track Name",
    artists: list[str] | None = None,
    uri: str | None = None,
    isrc: str | None = None,
    album: str = "Album",
) -> PlaylistTrack:
    """Factory for PlaylistTrack test fixtures."""
    return PlaylistTrack(
        position=position,
        uri=uri or f"spotify:track:fakeid{position:03d}",
        id=f"fakeid{position:03d}",
        name=name,
        artists=artists or ["Artist One"],
        album=album,
        duration_ms=200_000,
        isrc=isrc,
    )


# ---------------------------------------------------------------------------
# Pass 1: URI equality
# ---------------------------------------------------------------------------


def test_uri_duplicate_detected():
    tracks = [
        make_track(0, uri="spotify:track:AAA"),
        make_track(1, uri="spotify:track:BBB"),
        make_track(2, uri="spotify:track:AAA"),  # duplicate of position 0
    ]
    groups = detect_duplicates(tracks)
    assert len(groups) == 1
    assert groups[0].match_method == MatchMethod.uri
    assert {t.position for t in groups[0].tracks} == {0, 2}


def test_uri_triple_duplicate():
    tracks = [
        make_track(0, uri="spotify:track:AAA"),
        make_track(1, uri="spotify:track:AAA"),
        make_track(2, uri="spotify:track:AAA"),
    ]
    groups = detect_duplicates(tracks)
    assert len(groups) == 1
    assert len(groups[0].tracks) == 3


def test_no_uri_duplicates():
    # Each track has a unique URI AND a unique name to avoid fuzzy matching
    unique_names = ["Stairway to Heaven", "Bohemian Rhapsody", "Hotel California", "Imagine", "Smells Like Teen Spirit"]
    unique_artists = [["Led Zeppelin"], ["Queen"], ["Eagles"], ["John Lennon"], ["Nirvana"]]
    tracks = [
        make_track(i, name=unique_names[i], artists=unique_artists[i], uri=f"spotify:track:{i:03d}")
        for i in range(5)
    ]
    groups = detect_duplicates(tracks)
    assert groups == []


# ---------------------------------------------------------------------------
# Pass 2: ISRC equality
# ---------------------------------------------------------------------------


def test_isrc_duplicate_detected():
    tracks = [
        make_track(0, isrc="GBARL0000001", uri="spotify:track:A01"),
        make_track(1, isrc="GBARL0000001", uri="spotify:track:A02"),  # same ISRC, different URI
        make_track(2, isrc="GBARL0000002", uri="spotify:track:A03"),  # different ISRC
    ]
    groups = detect_duplicates(tracks)
    assert len(groups) == 1
    assert groups[0].match_method == MatchMethod.isrc
    assert {t.position for t in groups[0].tracks} == {0, 1}


def test_null_isrc_not_grouped():
    """Tracks with no ISRC must not be grouped together (different songs, no ISRC)."""
    tracks = [
        make_track(0, name="Waterloo", artists=["ABBA"], isrc=None, uri="spotify:track:X01"),
        make_track(1, name="Dancing Queen", artists=["ABBA"], isrc=None, uri="spotify:track:X02"),
    ]
    groups = detect_duplicates(tracks)
    assert groups == []


def test_empty_isrc_not_grouped():
    """Empty-string ISRC treated same as None (different songs)."""
    tracks = [
        make_track(0, name="Waterloo", artists=["ABBA"], isrc="", uri="spotify:track:X01"),
        make_track(1, name="Dancing Queen", artists=["ABBA"], isrc="", uri="spotify:track:X02"),
    ]
    groups = detect_duplicates(tracks)
    assert groups == []


def test_uri_duplicate_excluded_from_isrc_pass():
    """A URI duplicate should NOT also appear as an ISRC duplicate."""
    tracks = [
        make_track(0, isrc="SHARED001", uri="spotify:track:SAME"),
        make_track(1, isrc="SHARED001", uri="spotify:track:SAME"),  # URI + ISRC duplicate
    ]
    groups = detect_duplicates(tracks)
    assert len(groups) == 1
    assert groups[0].match_method == MatchMethod.uri  # URI wins


# ---------------------------------------------------------------------------
# Pass 3: Fuzzy matching
# ---------------------------------------------------------------------------


def test_fuzzy_remaster_detected():
    tracks = [
        make_track(0, name="Bohemian Rhapsody", artists=["Queen"], uri="spotify:track:F01"),
        make_track(1, name="Bohemian Rhapsody (2011 Remaster)", artists=["Queen"], uri="spotify:track:F02"),
    ]
    groups = detect_duplicates(tracks)
    assert len(groups) == 1
    assert groups[0].match_method == MatchMethod.fuzzy
    assert groups[0].fuzzy_score is not None
    assert groups[0].fuzzy_score >= 80


def test_fuzzy_live_version_detected():
    tracks = [
        make_track(0, name="Hotel California", artists=["Eagles"], uri="spotify:track:G01"),
        make_track(1, name="Hotel California (Live)", artists=["Eagles"], uri="spotify:track:G02"),
    ]
    groups = detect_duplicates(tracks)
    assert len(groups) == 1
    assert groups[0].match_method == MatchMethod.fuzzy


def test_fuzzy_different_artist_not_grouped():
    """Same title but different artist must NOT be grouped."""
    tracks = [
        make_track(0, name="Run", artists=["Snow Patrol"], uri="spotify:track:H01"),
        make_track(1, name="Run", artists=["Foo Fighters"], uri="spotify:track:H02"),
    ]
    groups = detect_duplicates(tracks)
    assert groups == []


def test_fuzzy_completely_different_songs_not_grouped():
    tracks = [
        make_track(0, name="Stairway to Heaven", artists=["Led Zeppelin"], uri="spotify:track:I01"),
        make_track(1, name="Smoke on the Water", artists=["Deep Purple"], uri="spotify:track:I02"),
    ]
    groups = detect_duplicates(tracks)
    assert groups == []


def test_fuzzy_transitive_grouping():
    """A~B and B~C should produce one group of three, not two overlapping pairs."""
    tracks = [
        make_track(0, name="Imagine", artists=["John Lennon"], uri="spotify:track:J01"),
        make_track(1, name="Imagine (Remastered)", artists=["John Lennon"], uri="spotify:track:J02"),
        make_track(2, name="Imagine (Live)", artists=["John Lennon"], uri="spotify:track:J03"),
    ]
    groups = detect_duplicates(tracks)
    assert len(groups) == 1
    assert len(groups[0].tracks) == 3


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_list():
    assert detect_duplicates([]) == []


def test_single_track():
    tracks = [make_track(0)]
    assert detect_duplicates(tracks) == []


def test_mixed_methods():
    """URI, ISRC, and fuzzy duplicates all present in one playlist."""
    tracks = [
        # URI duplicate
        make_track(0, uri="spotify:track:URI01"),
        make_track(1, uri="spotify:track:URI01"),
        # ISRC duplicate
        make_track(2, isrc="ISRC001", uri="spotify:track:ISO01"),
        make_track(3, isrc="ISRC001", uri="spotify:track:ISO02"),
        # Fuzzy duplicate
        make_track(4, name="Yesterday", artists=["The Beatles"], uri="spotify:track:FUZ01"),
        make_track(5, name="Yesterday (Remaster)", artists=["The Beatles"], uri="spotify:track:FUZ02"),
        # Unique track
        make_track(6, name="Unique Song", artists=["Unique Artist"], uri="spotify:track:UNIQ"),
    ]
    groups = detect_duplicates(tracks)
    methods = {g.match_method for g in groups}
    assert MatchMethod.uri in methods
    assert MatchMethod.isrc in methods
    assert MatchMethod.fuzzy in methods
    assert len(groups) == 3


def test_groups_sorted_by_earliest_position():
    """Groups should be sorted by the earliest track position they contain."""
    tracks = [
        make_track(5, name="Song B", artists=["Artist"], uri="spotify:track:B1"),
        make_track(6, name="Song B", artists=["Artist"], isrc="ISRC_B", uri="spotify:track:B2"),
        make_track(0, uri="spotify:track:A_SAME"),
        make_track(1, uri="spotify:track:A_SAME"),
    ]
    groups = detect_duplicates(tracks)
    # First group should start at position 0 (URI duplicate)
    assert min(t.position for t in groups[0].tracks) == 0
