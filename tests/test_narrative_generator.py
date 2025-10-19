"""Tests for narrative generator module."""

import json
from unittest.mock import MagicMock, patch

import pytest
from tournament_visualizer.data.narrative_generator import (
    NarrativeGenerator,
    MatchTimeline,
)


@pytest.fixture
def sample_formatted_events() -> str:
    """Sample formatted events text."""
    return """Turn 1:
  - Fluffbunny (Kush) founded Meroe
  - Becked (Assyria) founded Nineveh

Turn 51:
  - Fluffbunny (Kush) Declared War on Assyria (Becked)

Turn 57:
  - Becked (Assyria) Tushpa breached by Kush (Fluffbunny)

Turn 64:
  - Becked (Assyria) Qatna breached by Kush (Fluffbunny)"""


@pytest.fixture
def sample_match_metadata() -> dict:
    """Sample match metadata."""
    return {
        "match_id": 19,
        "player1_name": "Fluffbunny",
        "player1_civ": "Kush",
        "player2_name": "Becked",
        "player2_civ": "Assyria",
        "winner_name": "Fluffbunny",
        "total_turns": 64,
    }


def test_generator_initialization() -> None:
    """Should initialize with API key."""
    generator = NarrativeGenerator(api_key="test-key")
    assert generator is not None


def test_generator_requires_api_key() -> None:
    """Should raise if API key is empty."""
    with pytest.raises(ValueError):
        NarrativeGenerator(api_key="")


@patch("tournament_visualizer.data.narrative_generator.AnthropicClient")
def test_generate_narrative_calls_llm_twice(
    mock_client_class: MagicMock,
    sample_formatted_events: str,
    sample_match_metadata: dict,
) -> None:
    """Should make two LLM calls: extraction then narrative."""
    # Mock the client
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    # Mock Pass 1 response (timeline extraction)
    mock_timeline_response = MagicMock()
    mock_timeline_response.content = [
        MagicMock(
            type="tool_use",
            input={
                "outcome": "Fluffbunny won",
                "key_events": [
                    {"turn": 51, "description": "War declared"}
                ],
                "player_stats": {
                    "Fluffbunny": {"cities": 7},
                    "Becked": {"cities": 5}
                }
            }
        )
    ]

    # Mock Pass 2 response (narrative generation)
    mock_narrative_response = "Fluffbunny defeated Becked via conquest."

    mock_client.generate_with_tools.return_value = mock_timeline_response
    mock_client.generate_text.return_value = mock_narrative_response

    # Run generation
    generator = NarrativeGenerator(api_key="test-key")
    result = generator.generate_narrative(
        formatted_events=sample_formatted_events,
        match_metadata=sample_match_metadata,
    )

    # Should have called LLM twice
    assert mock_client.generate_with_tools.call_count == 1
    assert mock_client.generate_text.call_count == 1

    # Should return narrative
    assert result == mock_narrative_response


@patch("tournament_visualizer.data.narrative_generator.AnthropicClient")
def test_generate_narrative_passes_events_to_extraction(
    mock_client_class: MagicMock,
    sample_formatted_events: str,
    sample_match_metadata: dict,
) -> None:
    """Pass 1 should receive formatted events."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_timeline_response = MagicMock()
    mock_timeline_response.content = [
        MagicMock(type="tool_use", input={"outcome": "Test"})
    ]
    mock_client.generate_with_tools.return_value = mock_timeline_response
    mock_client.generate_text.return_value = "Narrative"

    generator = NarrativeGenerator(api_key="test-key")
    generator.generate_narrative(
        formatted_events=sample_formatted_events,
        match_metadata=sample_match_metadata,
    )

    # Check that events were in the prompt
    call_args = mock_client.generate_with_tools.call_args
    messages = call_args.kwargs["messages"]
    prompt_text = messages[0]["content"]

    assert "Turn 1:" in prompt_text
    assert "Turn 51:" in prompt_text


@patch("tournament_visualizer.data.narrative_generator.AnthropicClient")
def test_generate_narrative_passes_timeline_to_writing(
    mock_client_class: MagicMock,
    sample_formatted_events: str,
    sample_match_metadata: dict,
) -> None:
    """Pass 2 should receive extracted timeline."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_timeline_response = MagicMock()
    mock_timeline_response.content = [
        MagicMock(
            type="tool_use",
            input={
                "outcome": "Fluffbunny won via conquest",
                "key_events": [],
                "player_stats": {}
            }
        )
    ]
    mock_client.generate_with_tools.return_value = mock_timeline_response
    mock_client.generate_text.return_value = "Narrative"

    generator = NarrativeGenerator(api_key="test-key")
    generator.generate_narrative(
        formatted_events=sample_formatted_events,
        match_metadata=sample_match_metadata,
    )

    # Check that timeline was in Pass 2 prompt
    call_args = mock_client.generate_text.call_args
    messages = call_args.kwargs["messages"]
    prompt_text = messages[0]["content"]

    assert "Fluffbunny won via conquest" in prompt_text
