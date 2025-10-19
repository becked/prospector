"""Generate AI-powered narrative summaries for tournament matches.

This module implements a two-pass approach:
1. Extract structured timeline from event stream (using tool calling)
2. Generate narrative prose from timeline

Example:
    >>> from tournament_visualizer.config import Config
    >>> generator = NarrativeGenerator(api_key=Config.ANTHROPIC_API_KEY)
    >>> narrative = generator.generate_narrative(
    ...     formatted_events=event_text,
    ...     match_metadata={"player1_name": "Alice", ...}
    ... )
    >>> print(narrative)
    Alice (Rome) defeated Bob (Carthage) via military conquest...
"""

import json
import logging
from typing import Any, TypedDict

from anthropic.types import MessageParam, ToolParam

from tournament_visualizer.data.anthropic_client import AnthropicClient

logger = logging.getLogger(__name__)


class MatchTimeline(TypedDict):
    """Structured timeline extracted from match events."""

    outcome: str
    key_events: list[dict[str, Any]]
    player_stats: dict[str, dict[str, Any]]


class NarrativeGenerator:
    """Generate narrative summaries using two-pass LLM approach.

    Pass 1: Extract structured timeline from events
    Pass 2: Write narrative prose from timeline

    Attributes:
        client: AnthropicClient instance
        model: Model name to use (default: Claude 3.5 Haiku)
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-haiku-20241022",
    ) -> None:
        """Initialize narrative generator.

        Args:
            api_key: Anthropic API key
            model: Model name to use

        Raises:
            ValueError: If api_key is empty
        """
        if not api_key:
            raise ValueError("API key is required")

        self.client = AnthropicClient(api_key=api_key)
        self.model = model

    def generate_narrative(
        self,
        formatted_events: str,
        match_metadata: dict[str, Any],
    ) -> str:
        """Generate narrative summary for a match.

        Args:
            formatted_events: Human-readable event text grouped by turn
            match_metadata: Match info (player names, civs, winner, turns)

        Returns:
            2-3 paragraph narrative summary

        Raises:
            anthropic.APIError: On API call failures
        """
        logger.info(
            f"Generating narrative for match {match_metadata.get('match_id')}"
        )

        # Pass 1: Extract timeline
        timeline = self._extract_timeline(formatted_events, match_metadata)
        logger.debug(f"Extracted timeline: {json.dumps(timeline, indent=2)}")

        # Pass 2: Generate narrative
        narrative = self._generate_narrative_text(timeline, match_metadata)
        logger.info(f"Generated narrative ({len(narrative)} chars)")

        return narrative

    def _extract_timeline(
        self,
        formatted_events: str,
        match_metadata: dict[str, Any],
    ) -> MatchTimeline:
        """Pass 1: Extract structured timeline from events.

        Args:
            formatted_events: Human-readable event text
            match_metadata: Match info

        Returns:
            Structured timeline with outcome, key events, stats
        """
        # Define timeline extraction tool
        timeline_tool: ToolParam = {
            "name": "extract_timeline",
            "description": "Extract a structured timeline from match events",
            "input_schema": {
                "type": "object",
                "properties": {
                    "outcome": {
                        "type": "string",
                        "description": "Brief outcome (who won and how, e.g. 'Fluffbunny (Kush) defeated Becked (Assyria) via military conquest after Becked surrendered')",
                    },
                    "key_events": {
                        "type": "array",
                        "description": "List of key turning points in chronological order",
                        "items": {
                            "type": "object",
                            "properties": {
                                "turn": {
                                    "type": "integer",
                                    "description": "Turn number when event occurred",
                                },
                                "description": {
                                    "type": "string",
                                    "description": "What happened (e.g., 'War declared', 'Tushpa captured')",
                                },
                            },
                            "required": ["turn", "description"],
                        },
                    },
                    "player_stats": {
                        "type": "object",
                        "description": "Summary statistics per player (cities founded, techs discovered, etc.)",
                        "additionalProperties": {
                            "type": "object",
                            "properties": {
                                "cities": {"type": "integer"},
                                "techs": {"type": "integer"},
                                "laws": {"type": "integer"},
                                "goals": {"type": "integer"},
                            },
                        },
                    },
                },
                "required": ["outcome", "key_events", "player_stats"],
            },
        }

        # Build prompt
        prompt = f"""You are analyzing a tournament match from the strategy game Old World.

Players:
- {match_metadata.get('player1_name')} ({match_metadata.get('player1_civ')})
- {match_metadata.get('player2_name')} ({match_metadata.get('player2_civ')})

Winner: {match_metadata.get('winner_name')}
Total Turns: {match_metadata.get('total_turns')}

Here are all the events that occurred during the match, grouped by turn:

{formatted_events}

Analyze these events and extract a structured timeline. Identify:
1. The outcome (who won and how)
2. Key turning points (war declarations, city captures, major strategic decisions)
3. Summary statistics for each player

Focus on events that shaped the match outcome. Ignore routine events like character births or minor diplomatic actions with tribes."""

        # Call API with tool
        messages: list[MessageParam] = [{"role": "user", "content": prompt}]
        response = self.client.generate_with_tools(
            messages=messages,
            tools=[timeline_tool],
            model=self.model,
        )

        # Extract tool use from response
        for block in response.content:
            if hasattr(block, "type") and block.type == "tool_use":
                return block.input  # type: ignore

        raise ValueError("No timeline extracted from LLM response")

    def _generate_narrative_text(
        self,
        timeline: MatchTimeline,
        match_metadata: dict[str, Any],
    ) -> str:
        """Pass 2: Generate narrative prose from timeline.

        Args:
            timeline: Structured timeline from Pass 1
            match_metadata: Match info

        Returns:
            2-3 paragraph narrative summary
        """
        # Build prompt with timeline
        timeline_json = json.dumps(timeline, indent=2)

        prompt = f"""You are writing a narrative summary for a tournament match from Old World.

Players:
- {match_metadata.get('player1_name')} ({match_metadata.get('player1_civ')})
- {match_metadata.get('player2_name')} ({match_metadata.get('player2_civ')})

Here is the structured timeline of key events:

{timeline_json}

Write a concise 2-3 paragraph narrative summary of this match. Focus on:
- The outcome and how it was achieved
- Key strategic decisions or turning points
- The overall story arc (peaceful development, economic advantage, military conflict, etc.)

Write in past tense. Be specific about turns and events. Make it engaging but factual.

DO NOT include section headers or labels. Just write the narrative prose."""

        messages: list[MessageParam] = [{"role": "user", "content": prompt}]
        narrative = self.client.generate_text(
            messages=messages,
            model=self.model,
        )

        return narrative.strip()
