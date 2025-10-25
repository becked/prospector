"""Participant matching logic.

Links save file players to tournament participants using name matching
and manual overrides.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from tournament_visualizer.config import Config
from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.name_normalizer import (
    normalize_name,
)

logger = logging.getLogger(__name__)


class ParticipantMatcher:
    """Matches save file players to tournament participants."""

    def __init__(
        self,
        db: TournamentDatabase,
        overrides_path: Optional[str] = None,
    ) -> None:
        """Initialize matcher with database connection.

        Args:
            db: Database instance
            overrides_path: Path to participant name overrides JSON file.
                          If None, uses Config.PARTICIPANT_NAME_OVERRIDES_PATH
        """
        self.db = db
        self._participant_lookup: Optional[dict[str, tuple[int, str]]] = None
        self._overrides_path = overrides_path or Config.PARTICIPANT_NAME_OVERRIDES_PATH
        self._overrides: dict[str, dict[str, dict[str, Any]]] = {}
        self._overrides_loaded = False

    def _load_participants(self) -> None:
        """Load participant data and build lookup table.

        Creates mapping: normalized_name -> (participant_id, display_name)
        """
        if self._participant_lookup is not None:
            return  # Already loaded

        logger.info("Loading tournament participants for matching...")

        participants = self.db.fetch_all(
            """
            SELECT participant_id, display_name, display_name_normalized
            FROM tournament_participants
            """
        )

        # Build lookup: normalized_name -> (participant_id, display_name)
        self._participant_lookup = {}

        for participant_id, display_name, normalized_name in participants:
            if normalized_name and normalized_name not in self._participant_lookup:
                self._participant_lookup[normalized_name] = (
                    participant_id,
                    display_name,
                )

        logger.info(f"Loaded {len(self._participant_lookup)} participants for matching")

    def _load_overrides(self) -> None:
        """Load participant name overrides from JSON file.

        The JSON structure is:
        {
            "challonge_match_id": {
                "save_file_name": {
                    "participant_id": 123,
                    "reason": "explanation",
                    "date_added": "YYYY-MM-DD"
                }
            }
        }
        """
        if self._overrides_loaded:
            return

        overrides_path = Path(self._overrides_path)

        if not overrides_path.exists():
            logger.info(
                f"No participant name overrides file found at {self._overrides_path}"
            )
            self._overrides_loaded = True
            return

        try:
            with open(overrides_path) as f:
                data = json.load(f)

            # Build lookup with challonge_match_id keys (kept as strings)
            override_count = 0
            for challonge_match_id_str, players in data.items():
                # Skip metadata entries
                if challonge_match_id_str.startswith("_"):
                    continue

                # Validate it's a valid number (challonge_match_id)
                try:
                    int(challonge_match_id_str)  # Verify it's numeric
                except ValueError:
                    logger.warning(
                        f"Invalid challonge_match_id key in overrides: '{challonge_match_id_str}'"
                    )
                    continue

                # Store with string key (JSON keys must be strings)
                self._overrides[challonge_match_id_str] = players
                override_count += len(players)

            logger.info(
                f"Loaded {override_count} participant name overrides from {self._overrides_path}"
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse overrides file {self._overrides_path}: {e}")
        except Exception as e:
            logger.error(f"Error loading overrides from {self._overrides_path}: {e}")

        self._overrides_loaded = True

    def _get_challonge_match_id(self, match_id: int) -> Optional[int]:
        """Get challonge_match_id for a database match_id.

        Args:
            match_id: Database match ID (internal, unstable)

        Returns:
            Challonge match ID (external, stable), or None if not found
        """
        result = self.db.fetch_one(
            """
            SELECT challonge_match_id
            FROM matches
            WHERE match_id = ?
            """,
            {"1": match_id},
        )

        if result and result[0]:
            return result[0]

        logger.warning(f"No challonge_match_id found for database match_id {match_id}")
        return None

    def match_player(
        self, match_id: int, player_name: str, allow_override: bool = True
    ) -> Optional[int]:
        """Match a save file player name to a participant ID.

        Matching priority:
        1. Manual override (if allow_override=True)
        2. Normalized name match

        Args:
            match_id: Match ID (for override lookup)
            player_name: Player name from save file
            allow_override: Whether to check override file

        Returns:
            Participant ID if match found, None otherwise
        """
        if not player_name:
            return None

        # Ensure participant data is loaded
        self._load_participants()

        # Check override first
        if allow_override:
            # Load overrides if not already loaded
            if not self._overrides_loaded:
                self._load_overrides()

            # Get challonge_match_id for override lookup
            challonge_match_id = self._get_challonge_match_id(match_id)

            if challonge_match_id:
                # Check if this match has overrides
                # Overrides are keyed by challonge_match_id (as string)
                override_key = str(challonge_match_id)

                if override_key in self._overrides:
                    match_overrides = self._overrides[override_key]
                    if player_name in match_overrides:
                        override_data = match_overrides[player_name]
                        participant_id = override_data["participant_id"]
                        logger.debug(
                            f"Using override for match {match_id} (challonge {challonge_match_id}): "
                            f"'{player_name}' -> participant {participant_id} "
                            f"(reason: {override_data.get('reason', 'not specified')})"
                        )
                        return participant_id

        # Try normalized name matching
        normalized_player_name = normalize_name(player_name)

        if normalized_player_name in self._participant_lookup:
            participant_id, display_name = self._participant_lookup[
                normalized_player_name
            ]
            logger.debug(
                f"Matched '{player_name}' -> '{display_name}' "
                f"(participant {participant_id})"
            )
            return participant_id

        # No match found
        logger.warning(
            f"No participant match found for player '{player_name}' in match {match_id}"
        )
        return None

    def link_match_players(self, match_id: int) -> dict[str, Any]:
        """Link all players in a match to participants.

        Updates the players table with participant_id for all players
        in the specified match.

        Args:
            match_id: Match ID to process

        Returns:
            Dictionary with matching statistics:
                - total_players: Total players in match
                - matched: Number of players successfully matched
                - unmatched: Number of players without matches
                - unmatched_names: List of unmatched player names
        """
        logger.info(f"Linking players to participants for match {match_id}")

        # Get all players for this match
        players = self.db.fetch_all(
            """
            SELECT player_id, player_name
            FROM players
            WHERE match_id = ?
            """,
            {"1": match_id},
        )

        if not players:
            logger.warning(f"No players found for match {match_id}")
            return {
                "total_players": 0,
                "matched": 0,
                "unmatched": 0,
                "unmatched_names": [],
            }

        matched = 0
        unmatched_names = []

        for player_id, player_name in players:
            participant_id = self.match_player(match_id, player_name)

            if participant_id:
                # Update player with participant_id
                self.db.execute_query(
                    """
                    UPDATE players
                    SET participant_id = ?
                    WHERE player_id = ?
                    """,
                    {"1": participant_id, "2": player_id},
                )
                matched += 1
            else:
                unmatched_names.append(player_name)

        stats = {
            "total_players": len(players),
            "matched": matched,
            "unmatched": len(unmatched_names),
            "unmatched_names": unmatched_names,
        }

        if matched == len(players):
            logger.info(
                f"Successfully matched all {matched} players in match {match_id}"
            )
        else:
            logger.warning(
                f"Match {match_id}: {matched}/{len(players)} players matched. "
                f"Unmatched: {unmatched_names}"
            )

        return stats

    def link_all_matches(self) -> dict[str, Any]:
        """Link players to participants for all matches in database.

        Returns:
            Dictionary with overall statistics:
                - total_matches: Total matches processed
                - total_players: Total players across all matches
                - matched_players: Total players successfully matched
                - unmatched_players: Total players without matches
                - matches_fully_matched: Matches where all players matched
                - matches_with_unmatched: Matches with some unmatched players
                - unmatched_by_match: Dict of match_id -> list of unmatched names
        """
        logger.info("Linking all players to participants...")

        # DuckDB workaround: Drop index before bulk updates to avoid foreign key issues
        # This is due to a DuckDB limitation with tables that have foreign key references
        logger.info("Dropping idx_players_participant index for bulk updates...")
        self.db.execute_query("DROP INDEX IF EXISTS idx_players_participant")

        try:
            # Get all match IDs
            match_ids = self.db.fetch_all(
                "SELECT match_id FROM matches ORDER BY match_id"
            )

            total_players = 0
            matched_players = 0
            unmatched_players = 0
            matches_fully_matched = 0
            matches_with_unmatched = 0
            unmatched_by_match = {}

            for (match_id,) in match_ids:
                stats = self.link_match_players(match_id)

                total_players += stats["total_players"]
                matched_players += stats["matched"]
                unmatched_players += stats["unmatched"]

                if stats["unmatched"] == 0:
                    matches_fully_matched += 1
                else:
                    matches_with_unmatched += 1
                    unmatched_by_match[match_id] = stats["unmatched_names"]

            summary = {
                "total_matches": len(match_ids),
                "total_players": total_players,
                "matched_players": matched_players,
                "unmatched_players": unmatched_players,
                "matches_fully_matched": matches_fully_matched,
                "matches_with_unmatched": matches_with_unmatched,
                "unmatched_by_match": unmatched_by_match,
            }

            logger.info(
                f"Linking complete: {matched_players}/{total_players} players matched "
                f"across {len(match_ids)} matches"
            )

            return summary

        finally:
            # Always recreate the index, even if there's an error
            logger.info("Recreating idx_players_participant index...")
            self.db.execute_query(
                "CREATE INDEX IF NOT EXISTS idx_players_participant ON players(participant_id)"
            )
