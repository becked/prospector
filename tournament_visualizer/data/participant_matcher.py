"""Participant matching logic.

Links save file players to tournament participants using name matching
and manual overrides.
"""

import logging
from typing import Any, Optional

from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.name_normalizer import (
    normalize_name,
)

logger = logging.getLogger(__name__)


class ParticipantMatcher:
    """Matches save file players to tournament participants."""

    def __init__(self, db: TournamentDatabase) -> None:
        """Initialize matcher with database connection.

        Args:
            db: Database instance
        """
        self.db = db
        self._participant_lookup: Optional[dict[str, tuple[int, str]]] = None
        self._override_cache: dict[tuple[int, str], int] = {}

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

    def _load_overrides(self, match_id: int) -> None:
        """Load name overrides for a specific match.

        Args:
            match_id: Match ID to load overrides for
        """
        overrides = self.db.fetch_all(
            """
            SELECT save_file_player_name, participant_id
            FROM participant_name_overrides
            WHERE match_id = ?
            """,
            {"1": match_id},
        )

        for save_name, participant_id in overrides:
            cache_key = (match_id, save_name)
            self._override_cache[cache_key] = participant_id

        if overrides:
            logger.info(f"Loaded {len(overrides)} name overrides for match {match_id}")

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
            allow_override: Whether to check override table

        Returns:
            Participant ID if match found, None otherwise
        """
        if not player_name:
            return None

        # Ensure participant data is loaded
        self._load_participants()

        # Check override first
        if allow_override:
            # Load overrides for this match if not cached
            cache_key = (match_id, player_name)
            if cache_key not in self._override_cache:
                self._load_overrides(match_id)

            if cache_key in self._override_cache:
                participant_id = self._override_cache[cache_key]
                logger.debug(
                    f"Using override: '{player_name}' -> participant {participant_id}"
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
            match_ids = self.db.fetch_all("SELECT match_id FROM matches ORDER BY match_id")

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
