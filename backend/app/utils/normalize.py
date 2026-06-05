"""
Text normalization for fuzzy duplicate detection.

The goal is to strip away version-specific suffixes so that
"Bohemian Rhapsody (2011 Remaster)" and "Bohemian Rhapsody" produce
the same normalized key and are correctly identified as duplicates.

Steps applied in order:
    1. Lowercase
    2. Strip parenthetical/bracketed version tags (remaster, live, deluxe, …)
    3. Strip featured-artist annotations (feat. / ft.)
    4. Strip remaining non-alphanumeric characters (punctuation, symbols)
    5. Collapse multiple spaces and trim
"""

import re

# Matches any parenthetical/bracket that CONTAINS a version keyword anywhere inside.
# The keyword can appear at the start, end, or after a year: "(2011 Remaster)", "[Live]",
# "(Deluxe Edition)", "(Radio Edit)", "(Remastered 2023)", "(Official Music Video)" etc.
_VERSION_TAG = re.compile(
    r"\s*[\(\[][^\)\]]*"
    r"(?:remaster(?:ed)?|live|deluxe|edition|edit|version|radio|"
    r"acoustic|demo|instrumental|extended|mono|stereo|anniversary|"
    r"bonus|explicit|clean|single|original|re-?record)"
    r"[^\)\]]*[\)\]]",
    re.IGNORECASE,
)

# Matches "feat. Artist" or "ft. Artist" with optional surrounding brackets.
# Examples: "(feat. Jay-Z)", "ft. Eminem", "[feat. Dua Lipa]"
_FEAT = re.compile(
    r"\s*[\(\[]?\s*(?:feat\.|ft\.)\s+[^\)\]\,]+[\)\]]?",
    re.IGNORECASE,
)

# Anything that isn't a letter, digit, or space
_NON_ALPHANUM = re.compile(r"[^a-z0-9\s]")

# Two or more consecutive spaces
_MULTI_SPACE = re.compile(r"\s{2,}")


def normalize(text: str) -> str:
    """
    Normalize a track name or artist name for fuzzy comparison.

    Returns a lowercase, stripped string suitable for Levenshtein comparison.

    Examples:
        normalize("Bohemian Rhapsody (2011 Remaster)") → "bohemian rhapsody"
        normalize("Shape of You (feat. Ed Sheeran)")   → "shape of you"
        normalize("Mr. Brightside")                    → "mr brightside"
    """
    s = text.lower()
    s = _VERSION_TAG.sub("", s)
    s = _FEAT.sub("", s)
    s = _NON_ALPHANUM.sub("", s)
    s = _MULTI_SPACE.sub(" ", s).strip()
    return s
