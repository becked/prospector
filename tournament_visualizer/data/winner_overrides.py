"""Match winner override system for corrupted save files.

This module handles loading and applying manual winner overrides for matches
where the save file contains incorrect winner data due to bugs or manual
intervention.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class MatchWinnerOverrides:
    """Manages match winner overrides from JSON configuration."""

    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialize override system.

        Args:
            config_path: Path to override JSON file (default: data/match_winner_overrides.json)
        """
        self.config_path = Path(config_path or "data/match_winner_overrides.json")
        self.overrides: Dict[str, Dict[str, Any]] = {}
        self._load_overrides()

    def _load_overrides(self) -> None:
        """Load overrides from JSON file.

        Validates format and logs warnings for any issues.
        Missing file is not an error - system works without overrides.
        """
        if not self.config_path.exists():
            logger.info(
                f"No override file found at {self.config_path} - using save file winners"
            )
            return

        try:
            with open(self.config_path, encoding="utf-8") as f:
                data = json.load(f)

            # Filter out comment/instruction fields
            self.overrides = {k: v for k, v in data.items() if not k.startswith("_")}

            logger.info(
                f"Loaded {len(self.overrides)} match winner overrides from {self.config_path}"
            )

            # Validate each override
            for match_id, override_data in self.overrides.items():
                self._validate_override(match_id, override_data)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {self.config_path}: {e}")
            self.overrides = {}
        except Exception as e:
            logger.error(f"Error loading overrides from {self.config_path}: {e}")
            self.overrides = {}

    def _validate_override(self, match_id: str, override_data: Dict[str, Any]) -> bool:
        """Validate a single override entry.

        Args:
            match_id: Challonge match ID as string
            override_data: Override configuration dict

        Returns:
            True if valid, False if invalid (logs warning)
        """
        # Check required fields
        if "winner_player_name" not in override_data:
            logger.warning(
                f"Override for match {match_id} missing required field 'winner_player_name'"
            )
            return False

        if "reason" not in override_data:
            logger.warning(
                f"Override for match {match_id} missing required field 'reason'"
            )
            return False

        # Validate types
        if not isinstance(override_data["winner_player_name"], str):
            logger.warning(
                f"Override for match {match_id}: winner_player_name must be string"
            )
            return False

        return True

    def get_override_winner(self, challonge_match_id: Optional[int]) -> Optional[str]:
        """Get override winner player name for a match.

        Args:
            challonge_match_id: Challonge match ID (can be None for local files)

        Returns:
            Winner player name if override exists, None otherwise
        """
        if challonge_match_id is None:
            return None

        # Convert to string for JSON lookup
        match_id_str = str(challonge_match_id)

        if match_id_str in self.overrides:
            override = self.overrides[match_id_str]
            winner_name = override["winner_player_name"]
            reason = override.get("reason", "unknown")

            logger.info(
                f"Applying winner override for match {challonge_match_id}: "
                f"winner={winner_name}, reason={reason}"
            )

            return winner_name

        return None

    def has_override(self, challonge_match_id: Optional[int]) -> bool:
        """Check if an override exists for a match.

        Args:
            challonge_match_id: Challonge match ID

        Returns:
            True if override exists
        """
        if challonge_match_id is None:
            return False
        return str(challonge_match_id) in self.overrides


# Global instance for convenience
_overrides_instance: Optional[MatchWinnerOverrides] = None


def get_overrides() -> MatchWinnerOverrides:
    """Get or create the global overrides instance.

    Returns:
        Global MatchWinnerOverrides instance
    """
    global _overrides_instance
    if _overrides_instance is None:
        _overrides_instance = MatchWinnerOverrides()
    return _overrides_instance
