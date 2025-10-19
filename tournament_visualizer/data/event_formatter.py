"""Format match events into human-readable text for LLM consumption.

This module converts database event rows into grouped, readable text
that provides context to LLMs for narrative generation.

Example:
    >>> formatter = EventFormatter()
    >>> events = get_events_from_db(match_id=19)
    >>> text = formatter.format_events(events)
    >>> print(text)
    Turn 1:
      - Fluffbunny (Kush) founded Meroe
      - Fluffbunny (Kush) discovered Trapping
      - Becked (Assyria) founded Nineveh
    Turn 5:
      - Becked (Assyria) discovered Ironworking
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class EventFormatter:
    """Formats match events into human-readable grouped text.

    Groups events by turn and formats each with player context
    and event details.
    """

    def format_events(self, events: list[dict[str, Any]]) -> str:
        """Format events into grouped human-readable text.

        Args:
            events: List of event dicts from database with fields:
                - turn_number: int
                - event_type: str
                - player_name: str
                - civilization: str | None
                - description: str | None
                - event_data: dict | None

        Returns:
            Formatted text with events grouped by turn

        Example:
            >>> events = [
            ...     {"turn_number": 1, "event_type": "CITY_FOUNDED",
            ...      "player_name": "Alice", "civilization": "Rome",
            ...      "description": "Founded Rome", "event_data": None}
            ... ]
            >>> formatter.format_events(events)
            'Turn 1:\\n  - Alice (Rome) founded Rome\\n'
        """
        if not events:
            return ""

        # Group events by turn
        events_by_turn: dict[int, list[dict[str, Any]]] = {}
        for event in events:
            turn = event["turn_number"]
            if turn not in events_by_turn:
                events_by_turn[turn] = []
            events_by_turn[turn].append(event)

        # Format each turn
        lines: list[str] = []
        for turn in sorted(events_by_turn.keys()):
            lines.append(f"Turn {turn}:")
            for event in events_by_turn[turn]:
                formatted = self._format_single_event(event)
                if formatted:
                    lines.append(f"  - {formatted}")

        return "\n".join(lines)

    def _format_single_event(self, event: dict[str, Any]) -> str:
        """Format a single event into readable text.

        Args:
            event: Event dict from database

        Returns:
            Formatted event string (without turn prefix)
        """
        player = event.get("player_name", "Unknown")
        civ = event.get("civilization")
        event_type = event.get("event_type", "UNKNOWN")
        description = event.get("description")
        event_data = event.get("event_data")

        # Build player context
        player_ctx = player
        if civ:
            player_ctx = f"{player} ({civ})"

        # Try to get description from various sources
        detail = self._extract_event_detail(event_type, description, event_data)

        if detail:
            return f"{player_ctx} {detail}"
        else:
            # Fallback: just show event type
            return f"{player_ctx} - {event_type}"

    def _extract_event_detail(
        self,
        event_type: str,
        description: str | None,
        event_data: dict[str, Any] | None,
    ) -> str:
        """Extract human-readable detail from event.

        Args:
            event_type: Type of event (e.g., "TECH_DISCOVERED")
            description: Description field from database
            event_data: JSON event data

        Returns:
            Human-readable event detail
        """
        # Use description if available
        if description:
            return description

        # Extract from event_data JSON
        if event_data:
            # Tech discovered
            if event_type == "TECH_DISCOVERED" and "tech" in event_data:
                tech = event_data["tech"]
                # Clean up tech name (remove TECH_ prefix)
                if tech.startswith("TECH_"):
                    tech = tech[5:]
                # Convert to title case and replace underscores
                tech = tech.replace("_", " ").title()
                return f"discovered {tech}"

            # Law adopted
            if event_type == "LAW_ADOPTED" and "law" in event_data:
                law = event_data["law"]
                # Clean up law name (remove LAW_ prefix)
                if law.startswith("LAW_"):
                    law = law[4:]
                # Convert to title case and replace underscores
                law = law.replace("_", " ").title()
                return f"adopted {law}"

        # Map common event types to readable verbs
        event_type_map = {
            "CITY_FOUNDED": "founded a city",
            "CITY_BREACHED": "had a city breached",
            "TEAM_DIPLOMACY": "diplomatic action",
            "GOAL_STARTED": "started a goal",
            "GOAL_FINISHED": "finished a goal",
            "GOAL_FAILED": "failed a goal",
            "MEMORYPLAYER_ATTACKED_CITY": "attacked enemy city",
            "MEMORYPLAYER_ATTACKED_UNIT": "attacked enemy unit",
            "MEMORYPLAYER_CAPTURED_CITY": "captured enemy city",
        }

        if event_type in event_type_map:
            return event_type_map[event_type]

        # Return empty string for unmapped types
        # (caller will use fallback)
        return ""
