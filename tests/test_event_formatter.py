"""Tests for event formatter module."""

import pytest
from tournament_visualizer.data.event_formatter import EventFormatter


@pytest.fixture
def sample_events() -> list[dict]:
    """Sample event data from database."""
    return [
        {
            "turn_number": 1,
            "event_type": "CITY_FOUNDED",
            "player_name": "Fluffbunny",
            "civilization": "Kush",
            "description": "Founded Meroe",
            "event_data": None,
        },
        {
            "turn_number": 1,
            "event_type": "TECH_DISCOVERED",
            "player_name": "Fluffbunny",
            "civilization": "Kush",
            "description": None,
            "event_data": {"tech": "TECH_TRAPPING"},
        },
        {
            "turn_number": 1,
            "event_type": "CITY_FOUNDED",
            "player_name": "Becked",
            "civilization": "Assyria",
            "description": "Founded Nineveh",
            "event_data": None,
        },
        {
            "turn_number": 5,
            "event_type": "TECH_DISCOVERED",
            "player_name": "Becked",
            "civilization": "Assyria",
            "description": None,
            "event_data": {"tech": "TECH_IRONWORKING"},
        },
    ]


def test_format_events_groups_by_turn(sample_events: list[dict]) -> None:
    """Events should be grouped by turn number."""
    formatter = EventFormatter()
    result = formatter.format_events(sample_events)

    # Should have turn headers
    assert "Turn 1:" in result
    assert "Turn 5:" in result

    # Turn 1 events should appear before Turn 5
    turn1_pos = result.index("Turn 1:")
    turn5_pos = result.index("Turn 5:")
    assert turn1_pos < turn5_pos


def test_format_events_includes_player_names(sample_events: list[dict]) -> None:
    """Event descriptions should include player names."""
    formatter = EventFormatter()
    result = formatter.format_events(sample_events)

    assert "Fluffbunny" in result
    assert "Becked" in result


def test_format_events_includes_descriptions(sample_events: list[dict]) -> None:
    """Event descriptions from database should be included."""
    formatter = EventFormatter()
    result = formatter.format_events(sample_events)

    assert "Founded Meroe" in result
    assert "Founded Nineveh" in result


def test_format_events_extracts_tech_names(sample_events: list[dict]) -> None:
    """Tech names should be extracted from event_data JSON."""
    formatter = EventFormatter()
    result = formatter.format_events(sample_events)

    # Should show cleaned tech names (without TECH_ prefix)
    assert "Trapping" in result or "TECH_TRAPPING" in result
    assert "Ironworking" in result or "TECH_IRONWORKING" in result


def test_format_events_handles_empty_list() -> None:
    """Should handle empty event list gracefully."""
    formatter = EventFormatter()
    result = formatter.format_events([])

    assert result == "" or result.strip() == ""


def test_format_events_handles_missing_fields() -> None:
    """Should handle events with missing optional fields."""
    events = [
        {
            "turn_number": 1,
            "event_type": "UNKNOWN_EVENT",
            "player_name": "Player",
            "civilization": None,
            "description": None,
            "event_data": None,
        }
    ]

    formatter = EventFormatter()
    result = formatter.format_events(events)

    # Should not crash, should include turn and player
    assert "Turn 1:" in result
    assert "Player" in result
