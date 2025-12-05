"""
Nation color mappings for consistent chart colors.
Colors from docs/reference/color-scheme.md

With the dark theme, Carthage uses off-white/beige for visibility on dark backgrounds.
"""

from typing import Optional

# Nation name to primary color mapping (hex values)
# Source: docs/reference/color-scheme.md
# Note: Carthage uses off-white for visibility on dark backgrounds
NATION_COLORS: dict[str, str] = {
    "AKSUM": "#F8A3B4",     # Pink/Rose
    "ASSYRIA": "#FADC3B",   # Yellow
    "BABYLONIA": "#82C83E", # Green
    "CARTHAGE": "#F6EFE1",  # Off-white/Beige (visible on dark background)
    "EGYPT": "#BC6304",     # Dark Orange/Brown
    "GREECE": "#2360BC",    # Dark Blue
    "HATTI": "#80E3E8",     # Cyan
    "HITTITE": "#80E3E8",   # Cyan (alias for HATTI)
    "KUSH": "#FFFFB6",      # Light Yellow
    "PERSIA": "#C04E4A",    # Red
    "ROME": "#880D56",      # Purple/Burgundy
}

# Backwards compatibility - now identical to NATION_COLORS
NATION_MAP_COLORS = NATION_COLORS

# Fallback color for player 2 when both players use same nation
SAME_NATION_FALLBACK_COLOR = "#228B22"  # Forest Green


def get_nation_color(nation_name: str) -> str:
    """
    Get the color for a nation.

    Args:
        nation_name: The nation name (case-insensitive)

    Returns:
        Hex color code. Returns a default gray if nation not found.
    """
    return NATION_COLORS.get(nation_name.upper(), "#808080")


def get_nation_map_color(nation_name: str) -> str:
    """
    Get the map color for a nation.

    Now identical to get_nation_color() - kept for backwards compatibility.

    Args:
        nation_name: The nation name (case-insensitive)

    Returns:
        Hex color code. Returns a default gray if nation not found.
    """
    return NATION_COLORS.get(nation_name.upper(), "#808080")


def get_match_player_colors(
    player1_nation: Optional[str],
    player2_nation: Optional[str],
) -> tuple[str, str]:
    """
    Get colors for two players in a match, handling same-nation cases.

    Args:
        player1_nation: Nation name for player 1 (can be None)
        player2_nation: Nation name for player 2 (can be None)

    Returns:
        Tuple of (player1_color, player2_color)
    """
    # Get nation colors (or default gray if not found)
    color1 = get_nation_color(player1_nation) if player1_nation else "#808080"
    color2 = get_nation_color(player2_nation) if player2_nation else "#808080"

    # If same nation, player 2 gets fallback green
    if (
        player1_nation
        and player2_nation
        and player1_nation.upper() == player2_nation.upper()
    ):
        color2 = SAME_NATION_FALLBACK_COLOR

    return color1, color2
