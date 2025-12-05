"""Tests for theme configuration."""

from tournament_visualizer.theme import CHART_THEME, DARK_THEME


def test_dark_theme_has_required_keys() -> None:
    """Verify DARK_THEME has all required color keys."""
    required = ["bg_dark", "bg_medium", "text_primary", "accent_primary", "accent_info"]
    for key in required:
        assert key in DARK_THEME


def test_chart_theme_has_required_keys() -> None:
    """Verify CHART_THEME has all required layout keys."""
    required = [
        "paper_bgcolor",
        "plot_bgcolor",
        "font_color",
        "text_muted",
        "gridcolor",
        "hoverlabel_bgcolor",
        "hoverlabel_font_color",
    ]
    for key in required:
        assert key in CHART_THEME


def test_chart_theme_uses_dark_theme_colors() -> None:
    """Verify CHART_THEME references DARK_THEME colors."""
    assert CHART_THEME["paper_bgcolor"] == DARK_THEME["bg_dark"]
    assert CHART_THEME["font_color"] == DARK_THEME["text_primary"]
