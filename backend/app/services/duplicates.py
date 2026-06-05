"""
Duplicate detection service.

Runs three passes over a playlist's track list, each using a
different method to identify duplicates. Passes run in priority order —
a track claimed by an earlier pass is excluded from later passes.

Pass 1 — URI equality
    Catches the same track literally added twice.
    Uses pandas groupby on the Spotify track URI.

Pass 2 — ISRC equality
    Catches the same recording added via different album releases
    (e.g. "original album" vs. "greatest hits" vs. "anniversary edition").
    Uses pandas groupby on the ISRC field.

Pass 3 — Fuzzy title + artist similarity
    Catches versions that share no URI/ISRC but are clearly the same song:
    remasters, live recordings, deluxe editions, radio edits, etc.
    Uses rapidfuzz for fast Levenshtein scoring.
    Title AND artist similarity must both clear their thresholds.
    Union-Find merges transitive matches (A~B and B~C → one group).
"""

import uuid

import pandas as pd
from rapidfuzz import fuzz

from app.types import DuplicateGroup, MatchMethod, PlaylistTrack
from app.utils.normalize import normalize

# Minimum title similarity (0–100) to consider two tracks duplicates
FUZZY_TITLE_THRESHOLD = 80

# Minimum first-artist similarity (0–100) as a guard against short-title false positives
# e.g. "Run" by two completely different artists should NOT match
FUZZY_ARTIST_THRESHOLD = 70

# PlaylistTrack field names — used to filter extra DataFrame columns before reconstruction
_TRACK_FIELDS = set(PlaylistTrack.model_fields.keys())


def detect_duplicates(tracks: list[PlaylistTrack]) -> list[DuplicateGroup]:
    """
    Run all three detection passes and return a list of duplicate groups.

    Each group contains 2+ tracks that are considered duplicates of each other.
    Within a group, the user chooses which copy to keep.

    Args:
        tracks: Full track list of a single playlist (positions must be accurate).

    Returns:
        List of DuplicateGroup objects, sorted by position of the first track
        in each group for a predictable display order.
    """
    if len(tracks) < 2:
        return []

    df = pd.DataFrame([t.model_dump() for t in tracks])
    claimed: set[int] = set()   # positions already assigned to a group
    groups: list[DuplicateGroup] = []

    # ------------------------------------------------------------------
    # Pass 1: URI equality
    # ------------------------------------------------------------------
    for uri, grp in df.groupby("uri"):
        if len(grp) < 2:
            continue
        group_tracks = _rows_to_tracks(grp.to_dict("records"))
        groups.append(
            DuplicateGroup(
                group_id=str(uuid.uuid4()),
                match_method=MatchMethod.uri,
                fuzzy_score=None,
                tracks=group_tracks,
            )
        )
        claimed.update(grp["position"].tolist())

    # ------------------------------------------------------------------
    # Pass 2: ISRC equality
    # ------------------------------------------------------------------
    remaining = df[~df["position"].isin(claimed)].copy()
    # Only consider rows that actually have a non-empty ISRC
    with_isrc = remaining[remaining["isrc"].notna() & (remaining["isrc"] != "")]

    for isrc, grp in with_isrc.groupby("isrc"):
        if len(grp) < 2:
            continue
        group_tracks = _rows_to_tracks(grp.to_dict("records"))
        groups.append(
            DuplicateGroup(
                group_id=str(uuid.uuid4()),
                match_method=MatchMethod.isrc,
                fuzzy_score=None,
                tracks=group_tracks,
            )
        )
        claimed.update(grp["position"].tolist())

    # ------------------------------------------------------------------
    # Pass 3: Fuzzy name + artist similarity
    # ------------------------------------------------------------------
    remaining = df[~df["position"].isin(claimed)].copy()
    if len(remaining) < 2:
        return _sort_groups(groups)

    # Pre-compute normalized keys to avoid repeating normalization in the O(n²) loop
    remaining["norm_title"] = remaining["name"].apply(normalize)
    remaining["norm_artist"] = remaining["artists"].apply(
        lambda a: normalize(a[0]) if isinstance(a, list) and a else ""
    )

    rows = remaining.to_dict("records")

    # Union-Find structure for merging transitive matches
    # (if A matches B and B matches C, they form one group of three)
    parent: dict[int, int] = {r["position"]: r["position"] for r in rows}

    def find(x: int) -> int:
        # Path compression
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        parent[find(x)] = find(y)

    # best_score[(pos_a, pos_b)] = highest title similarity seen for this pair
    best_score: dict[tuple[int, int], int] = {}

    # O(n²) comparison — acceptable because Pass 1 and 2 have already removed
    # most exact duplicates, leaving a much smaller set here
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            a, b = rows[i], rows[j]

            title_score = fuzz.ratio(a["norm_title"], b["norm_title"])
            if title_score < FUZZY_TITLE_THRESHOLD:
                continue

            artist_score = fuzz.ratio(a["norm_artist"], b["norm_artist"])
            if artist_score < FUZZY_ARTIST_THRESHOLD:
                continue

            union(a["position"], b["position"])
            key = (
                min(a["position"], b["position"]),
                max(a["position"], b["position"]),
            )
            best_score[key] = max(best_score.get(key, 0), title_score)

    # Collect groups by their union-find root
    root_to_positions: dict[int, list[int]] = {}
    for r in rows:
        root = find(r["position"])
        root_to_positions.setdefault(root, []).append(r["position"])

    pos_to_row: dict[int, dict] = {r["position"]: r for r in rows}

    for positions in root_to_positions.values():
        if len(positions) < 2:
            continue

        # Find the highest similarity score within this group for display
        max_score = 0
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                key = (min(positions[i], positions[j]), max(positions[i], positions[j]))
                max_score = max(max_score, best_score.get(key, 0))

        group_tracks = _rows_to_tracks(
            [pos_to_row[p] for p in sorted(positions)]
        )
        groups.append(
            DuplicateGroup(
                group_id=str(uuid.uuid4()),
                match_method=MatchMethod.fuzzy,
                fuzzy_score=round(max_score),  # fuzz.ratio() returns float
                tracks=group_tracks,
            )
        )

    return _sort_groups(groups)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rows_to_tracks(rows: list[dict]) -> list[PlaylistTrack]:
    """
    Convert a list of raw DataFrame row dicts back to PlaylistTrack objects.

    Filters out any extra columns added during processing (e.g. norm_title).
    """
    return [PlaylistTrack(**{k: v for k, v in row.items() if k in _TRACK_FIELDS}) for row in rows]


def _sort_groups(groups: list[DuplicateGroup]) -> list[DuplicateGroup]:
    """Sort groups by the position of their earliest track for stable display order."""
    return sorted(groups, key=lambda g: min(t.position for t in g.tracks))
