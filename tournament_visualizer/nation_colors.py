"""
Nation color mappings for consistent chart colors.
Colors extracted from nation logos in Old World.
"""

# Nation name to primary color mapping (hex values)
NATION_COLORS: dict[str, str] = {
    "ASSYRIA": "#E8C547",  # Gold/Yellow
    "BABYLONIA": "#6B9D4D",  # Green
    "CARTHAGE": "#D4D4D4",  # Light Gray/White
    "EGYPT": "#D67E2C",  # Orange
    "GREECE": "#4A8FD4",  # Blue
    "HATTI": "#5DCED8",  # Cyan/Turquoise
    "KUSH": "#E8E09B",  # Pale Yellow
    "PERSIA": "#D47474",  # Red/Coral
    "ROME": "#A84B9E",  # Purple/Magenta
}


def get_nation_color(nation_name: str) -> str:
    """
    Get the color for a nation.

    Args:
        nation_name: The nation name (case-insensitive)

    Returns:
        Hex color code. Returns a default gray if nation not found.
    """
    return NATION_COLORS.get(nation_name.upper(), "#808080")
