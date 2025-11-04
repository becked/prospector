"""Tests for round formatting helper functions.

Test Strategy:
- Test formatting for Winners bracket rounds
- Test formatting for Losers bracket rounds
- Test formatting for unknown rounds
- Test badge color selection
"""

from tournament_visualizer.components.layouts import (
    format_round_display,
    get_round_badge_color,
)


class TestRoundFormatting:
    """Test round formatting utilities."""

    def test_format_round_display_winners(self) -> None:
        """Test formatting Winners bracket rounds."""
        assert format_round_display(1) == "Winners Round 1"
        assert format_round_display(5) == "Winners Round 5"

    def test_format_round_display_losers(self) -> None:
        """Test formatting Losers bracket rounds."""
        assert format_round_display(-1) == "Losers Round 1"
        assert format_round_display(-5) == "Losers Round 5"

    def test_format_round_display_unknown(self) -> None:
        """Test formatting unknown rounds."""
        assert format_round_display(None) == "Unknown"
        assert format_round_display(0) == "Unknown"

    def test_get_round_badge_color(self) -> None:
        """Test badge color selection."""
        assert get_round_badge_color(1) == "success"
        assert get_round_badge_color(-1) == "warning"
        assert get_round_badge_color(None) == "secondary"
