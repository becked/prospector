"""Tests for narrative generator module."""

from unittest.mock import MagicMock, patch

import pytest
from tournament_visualizer.data.narrative_generator import (
    NarrativeGenerator,
    serialize_analysis,
)


@pytest.fixture
def sample_analysis() -> dict:
    """Sample analysis dict matching analyze_match() output."""
    return {
        "match_id": 19,
        "total_turns": 64,
        "winner_player_id": 1,
        "winner_name": "Fluffbunny",
        "player_ids": (1, 2),
        "player_names": ("Fluffbunny", "Becked"),
        "civilizations": ("Kush", "Assyria"),
        "archetype_info": {
            "archetype": "Early Military Rush",
            "length_class": "Short",
            "decisive_phase": "early",
            "win_story": "Fluffbunny wins via early aggression",
        },
        "vp_analysis": {
            "max_p1_lead": 42,
            "max_p1_lead_turn": 55,
            "max_p2_lead": 10,
            "max_p2_lead_turn": 20,
            "total_lead_changes": 2,
            "permanent_lead_turn": 45,
        },
        "territory_analysis": {
            "p1_final_cities": 7,
            "p2_final_cities": 5,
            "p1_first_to_5": 28,
            "p2_first_to_5": 35,
            "expansion_class_p1": "Fast",
            "expansion_class_p2": "Balanced",
        },
        "p1_profile": {
            "player_id": 1,
            "player_name": "Fluffbunny",
            "civilization": "Kush",
            "playstyle_tags": {
                "expansion": "Fast",
                "military": "Aggressive",
                "economy": "Training-focused",
                "identity": None,
            },
            "army_composition": {
                "Infantry": 0.4,
                "Ranged": 0.3,
                "Cavalry": 0.2,
                "Siege": 0.1,
                "Naval": 0.0,
                "Support": 0.0,
            },
            "wonders_built": 2,
        },
        "p2_profile": {
            "player_id": 2,
            "player_name": "Becked",
            "civilization": "Assyria",
            "playstyle_tags": {
                "expansion": "Balanced",
                "military": "Defensive",
                "economy": "Science-focused",
                "identity": None,
            },
            "army_composition": {
                "Infantry": 0.5,
                "Ranged": 0.3,
                "Cavalry": 0.1,
                "Siege": 0.1,
                "Naval": 0.0,
                "Support": 0.0,
            },
            "wonders_built": 1,
        },
        "key_events": [
            {
                "turn": 32,
                "player_id": 2,
                "event_type": "city_lost",
                "title": "Lost city",
                "icon": "",
                "priority": 50,
            },
        ],
        "summary": {
            "laws": {
                "Fluffbunny": {"total": 5, "swaps": 0, "style": "Stable"},
                "Becked": {"total": 3, "swaps": 1, "style": "Cycling"},
            },
            "religions": {"Fluffbunny": ["Zoroastrianism"], "Becked": []},
            "wonders": {
                "Fluffbunny": {"count": 2, "list": ["Pyramids", "Colosseum"]},
                "Becked": {"count": 1, "list": ["Hanging Gardens"]},
            },
        },
        "highlights": {
            "mvp_city": {"name": "Meroe", "wonders": 2, "player_id": 1},
            "pivotal_battle": None,
            "signature_tech": None,
        },
        "yield_comparison": {
            "victory_points": {
                "p1_total": 120.0,
                "p2_total": 80.0,
                "display_name": "Victory Points",
            },
            "training": {
                "p1_total": 4520.0,
                "p2_total": 3200.0,
                "display_name": "Training",
            },
        },
        "victory_conditions": "Points, Conquest",
        "avg_turns": 83,
    }


def test_generator_initialization() -> None:
    """Should initialize with API key."""
    generator = NarrativeGenerator(api_key="test-key")
    assert generator is not None


def test_generator_requires_api_key() -> None:
    """Should raise if API key is empty."""
    with pytest.raises(ValueError):
        NarrativeGenerator(api_key="")


def test_serialize_analysis_includes_key_data(sample_analysis: dict) -> None:
    """Serialized analysis should contain all key match data."""
    result = serialize_analysis(sample_analysis)

    assert "Fluffbunny" in result
    assert "Becked" in result
    assert "Kush" in result
    assert "Assyria" in result
    assert "64 turns (average 83)" in result
    assert "Wonders completed: 2" in result
    assert "Victory Points" in result


def test_serialize_analysis_includes_profiles(sample_analysis: dict) -> None:
    """Serialized analysis should include player profile tags."""
    result = serialize_analysis(sample_analysis)

    assert "Expansion: Fast" in result
    assert "Economy: Training-focused" in result
    assert "Army: Infantry 40%" in result


@patch("tournament_visualizer.data.narrative_generator.AnthropicClient")
def test_generate_match_summary(
    mock_client_class: MagicMock,
    sample_analysis: dict,
) -> None:
    """Match summary generation should call LLM once."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.generate_text.return_value = "A short but intense match."

    generator = NarrativeGenerator(api_key="test-key")
    result = generator.generate_match_summary(sample_analysis)

    assert mock_client.generate_text.call_count == 1
    assert result == "A short but intense match."

    # Verify prompt contains analysis data
    call_args = mock_client.generate_text.call_args
    messages = call_args.kwargs["messages"]
    prompt = messages[0]["content"]
    assert "Fluffbunny" in prompt
    assert "Kush" in prompt


@patch("tournament_visualizer.data.narrative_generator.AnthropicClient")
def test_generate_player_narrative(
    mock_client_class: MagicMock,
    sample_analysis: dict,
) -> None:
    """Player narrative generation should call LLM once with player context."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.generate_text.return_value = "Fluffbunny played aggressively."

    generator = NarrativeGenerator(api_key="test-key")
    result = generator.generate_player_narrative(sample_analysis, "p1")

    assert mock_client.generate_text.call_count == 1
    assert result == "Fluffbunny played aggressively."

    # Verify prompt mentions the player specifically
    call_args = mock_client.generate_text.call_args
    messages = call_args.kwargs["messages"]
    prompt = messages[0]["content"]
    assert "Fluffbunny (Kush)" in prompt
    assert "winning" in prompt


@patch("tournament_visualizer.data.narrative_generator.AnthropicClient")
def test_generate_player_narrative_loser(
    mock_client_class: MagicMock,
    sample_analysis: dict,
) -> None:
    """Loser narrative should use 'losing' context."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.generate_text.return_value = "Becked struggled defensively."

    generator = NarrativeGenerator(api_key="test-key")
    result = generator.generate_player_narrative(sample_analysis, "p2")

    call_args = mock_client.generate_text.call_args
    messages = call_args.kwargs["messages"]
    prompt = messages[0]["content"]
    assert "Becked (Assyria)" in prompt
    assert "losing" in prompt
