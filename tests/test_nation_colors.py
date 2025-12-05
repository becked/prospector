"""Tests for nation color configuration."""

from tournament_visualizer.nation_colors import (
    NATION_COLORS,
    NATION_MAP_COLORS,
    get_nation_color,
    get_nation_map_color,
    get_match_player_colors,
    SAME_NATION_FALLBACK_COLOR,
)


def test_carthage_uses_offwhite() -> None:
    """Verify Carthage uses off-white for dark theme visibility."""
    assert NATION_COLORS["CARTHAGE"] == "#F6EFE1"


def test_nation_map_colors_is_nation_colors() -> None:
    """Verify NATION_MAP_COLORS is now the same as NATION_COLORS."""
    assert NATION_MAP_COLORS is NATION_COLORS


def test_get_nation_color_case_insensitive() -> None:
    """Verify get_nation_color is case-insensitive."""
    assert get_nation_color("rome") == get_nation_color("ROME")
    assert get_nation_color("Rome") == get_nation_color("ROME")


def test_get_nation_color_returns_default_for_unknown() -> None:
    """Verify get_nation_color returns gray for unknown nations."""
    assert get_nation_color("UNKNOWN_NATION") == "#808080"


def test_get_nation_map_color_matches_get_nation_color() -> None:
    """Verify get_nation_map_color returns same result as get_nation_color."""
    for nation in NATION_COLORS:
        assert get_nation_map_color(nation) == get_nation_color(nation)


def test_get_match_player_colors_different_nations() -> None:
    """Verify get_match_player_colors returns nation colors for different nations."""
    color1, color2 = get_match_player_colors("ROME", "GREECE")
    assert color1 == NATION_COLORS["ROME"]
    assert color2 == NATION_COLORS["GREECE"]


def test_get_match_player_colors_same_nation() -> None:
    """Verify get_match_player_colors uses fallback for same nation."""
    color1, color2 = get_match_player_colors("ROME", "ROME")
    assert color1 == NATION_COLORS["ROME"]
    assert color2 == SAME_NATION_FALLBACK_COLOR


def test_get_match_player_colors_handles_none() -> None:
    """Verify get_match_player_colors handles None nations."""
    color1, color2 = get_match_player_colors(None, "ROME")
    assert color1 == "#808080"  # Default gray
    assert color2 == NATION_COLORS["ROME"]

    color1, color2 = get_match_player_colors("ROME", None)
    assert color1 == NATION_COLORS["ROME"]
    assert color2 == "#808080"  # Default gray
