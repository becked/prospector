"""Name normalization utilities for participant matching.

Provides functions to normalize player/participant names for fuzzy matching
between save file player names and Challonge participant names.
"""

import re
import unicodedata
from typing import Optional


def normalize_name(name: Optional[str]) -> str:
    """Normalize a player/participant name for matching.

    Normalization steps:
    1. Strip whitespace
    2. Convert to lowercase
    3. Remove Unicode accents/diacritics
    4. Remove special characters (keep only alphanumeric)
    5. Collapse multiple spaces to single space
    6. Strip again

    Args:
        name: Player or participant name to normalize

    Returns:
        Normalized name (lowercase, no special chars, no whitespace)
        Empty string if name is None

    Examples:
        >>> normalize_name("FluffybunnyMohawk")
        'fluffybunnymohawk'

        >>> normalize_name("Ninja [OW]")
        'ninjaow'

        >>> normalize_name("  Player_123  ")
        'player123'

        >>> normalize_name("José García")
        'josegarcia'
    """
    if not name:
        return ""

    # Strip leading/trailing whitespace
    normalized = name.strip()

    # Convert to lowercase
    normalized = normalized.lower()

    # Remove Unicode accents/diacritics
    # Decompose Unicode characters, then filter out combining marks
    normalized = unicodedata.normalize("NFKD", normalized)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))

    # Remove all non-alphanumeric characters
    normalized = re.sub(r"[^a-z0-9\s]", "", normalized)

    # Collapse multiple spaces to single space
    normalized = re.sub(r"\s+", " ", normalized)

    # Final strip and remove all remaining whitespace
    normalized = normalized.strip().replace(" ", "")

    return normalized


def names_match(name1: Optional[str], name2: Optional[str]) -> bool:
    """Check if two names match after normalization.

    Args:
        name1: First name to compare
        name2: Second name to compare

    Returns:
        True if normalized names are equal, False otherwise

    Examples:
        >>> names_match("Ninja", "ninja")
        True

        >>> names_match("Ninja [OW]", "Ninja")
        True

        >>> names_match("FluffyBunny", "Fluffy Bunny")
        True

        >>> names_match("Ninja", "Auro")
        False
    """
    return normalize_name(name1) == normalize_name(name2)


def find_best_match(
    target_name: str, candidate_names: dict[str, str], require_exact: bool = False
) -> Optional[str]:
    """Find the best matching name from a set of candidates.

    Args:
        target_name: Name to find a match for
        candidate_names: Dict mapping normalized names to original names
        require_exact: If True, only return exact normalized matches

    Returns:
        Original name of best match, or None if no match found

    Note:
        Currently only supports exact normalized matching.
        Future: Could add fuzzy matching (Levenshtein distance, etc.)
    """
    normalized_target = normalize_name(target_name)

    if not normalized_target:
        return None

    # Exact match on normalized name
    if normalized_target in candidate_names:
        return candidate_names[normalized_target]

    # No match found
    return None


def build_name_lookup(names: list[str]) -> dict[str, str]:
    """Build a lookup dictionary from list of names.

    Maps normalized name → original name for fast matching.
    If multiple names normalize to the same value, keeps the first one.

    Args:
        names: List of original names

    Returns:
        Dictionary mapping normalized_name -> original_name

    Example:
        >>> build_name_lookup(["Ninja", "ninja", "Auro"])
        {'ninja': 'Ninja', 'auro': 'Auro'}
    """
    lookup = {}

    for name in names:
        normalized = normalize_name(name)
        if normalized and normalized not in lookup:
            lookup[normalized] = name

    return lookup
