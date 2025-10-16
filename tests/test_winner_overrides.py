"""Tests for match winner override system."""

import json
import tempfile
from pathlib import Path

import pytest

from tournament_visualizer.data.winner_overrides import MatchWinnerOverrides


class TestMatchWinnerOverrides:
    """Tests for MatchWinnerOverrides class."""

    def test_load_valid_overrides(self, tmp_path: Path) -> None:
        """Test loading valid override file."""
        override_file = tmp_path / "overrides.json"
        override_file.write_text(
            json.dumps(
                {
                    "12345": {
                        "winner_player_name": "PlayerOne",
                        "reason": "Test reason",
                        "date_added": "2025-10-16",
                    }
                }
            )
        )

        overrides = MatchWinnerOverrides(str(override_file))

        assert overrides.has_override(12345)
        assert overrides.get_override_winner(12345) == "PlayerOne"
        assert not overrides.has_override(99999)

    def test_missing_file_not_error(self, tmp_path: Path) -> None:
        """Test that missing override file doesn't raise error."""
        missing_file = tmp_path / "does_not_exist.json"

        overrides = MatchWinnerOverrides(str(missing_file))

        assert not overrides.has_override(12345)
        assert overrides.get_override_winner(12345) is None

    def test_invalid_json_handled(self, tmp_path: Path) -> None:
        """Test that invalid JSON is handled gracefully."""
        override_file = tmp_path / "invalid.json"
        override_file.write_text("{ invalid json content }")

        overrides = MatchWinnerOverrides(str(override_file))

        # Should not crash, just log error and have no overrides
        assert not overrides.has_override(12345)

    def test_missing_required_fields(self, tmp_path: Path) -> None:
        """Test validation of required fields."""
        override_file = tmp_path / "missing_fields.json"
        override_file.write_text(
            json.dumps(
                {
                    "12345": {
                        "winner_player_name": "PlayerOne"
                        # Missing 'reason' field
                    },
                    "67890": {
                        "reason": "Test reason"
                        # Missing 'winner_player_name' field
                    },
                }
            )
        )

        overrides = MatchWinnerOverrides(str(override_file))

        # Both should be loaded but validation warnings logged
        # (validation is informational, doesn't block loading)
        assert len(overrides.overrides) == 2

    def test_comment_fields_ignored(self, tmp_path: Path) -> None:
        """Test that _comment and _instructions fields are filtered out."""
        override_file = tmp_path / "with_comments.json"
        override_file.write_text(
            json.dumps(
                {
                    "_comment": "This is a comment",
                    "_instructions": ["Do this", "Do that"],
                    "12345": {
                        "winner_player_name": "PlayerOne",
                        "reason": "Test",
                    },
                }
            )
        )

        overrides = MatchWinnerOverrides(str(override_file))

        # Only the actual override should be loaded
        assert len(overrides.overrides) == 1
        assert overrides.has_override(12345)

    def test_none_match_id_returns_none(self, tmp_path: Path) -> None:
        """Test that None match ID returns None (local files)."""
        override_file = tmp_path / "overrides.json"
        override_file.write_text(
            json.dumps(
                {
                    "12345": {
                        "winner_player_name": "PlayerOne",
                        "reason": "Test",
                    }
                }
            )
        )

        overrides = MatchWinnerOverrides(str(override_file))

        assert not overrides.has_override(None)
        assert overrides.get_override_winner(None) is None

    def test_multiple_overrides(self, tmp_path: Path) -> None:
        """Test loading multiple overrides."""
        override_file = tmp_path / "overrides.json"
        override_file.write_text(
            json.dumps(
                {
                    "12345": {
                        "winner_player_name": "PlayerOne",
                        "reason": "Test 1",
                    },
                    "67890": {
                        "winner_player_name": "PlayerTwo",
                        "reason": "Test 2",
                    },
                }
            )
        )

        overrides = MatchWinnerOverrides(str(override_file))

        assert len(overrides.overrides) == 2
        assert overrides.get_override_winner(12345) == "PlayerOne"
        assert overrides.get_override_winner(67890) == "PlayerTwo"

    def test_optional_fields(self, tmp_path: Path) -> None:
        """Test that optional fields are accepted."""
        override_file = tmp_path / "overrides.json"
        override_file.write_text(
            json.dumps(
                {
                    "12345": {
                        "winner_player_name": "PlayerOne",
                        "reason": "Test",
                        "date_added": "2025-10-16",
                        "notes": "Additional notes",
                    }
                }
            )
        )

        overrides = MatchWinnerOverrides(str(override_file))

        assert overrides.has_override(12345)
        assert overrides.get_override_winner(12345) == "PlayerOne"


class TestETLIntegration:
    """Integration tests for override system in ETL pipeline."""

    def test_extract_challonge_match_id_from_filename(self) -> None:
        """Test extraction of Challonge match ID from filename."""
        from tournament_visualizer.data.etl import TournamentETL

        etl = TournamentETL()

        # Test valid filenames
        assert etl.extract_challonge_match_id("match_426504724_moose-mongreleyes.zip") == 426504724
        assert etl.extract_challonge_match_id("match_12345_some-file.zip") == 12345
        assert (
            etl.extract_challonge_match_id(
                "match_426504724_OW-Save-Auto-Game270134180-7-Player2.zip"
            )
            == 426504724
        )

        # Test invalid filenames (no match ID)
        assert etl.extract_challonge_match_id("some_file.zip") is None
        assert etl.extract_challonge_match_id("matchfile.zip") is None
        assert etl.extract_challonge_match_id("OW-Save-Auto.zip") is None

        # Test edge cases
        assert etl.extract_challonge_match_id("match_abc_file.zip") is None  # Non-numeric
        assert etl.extract_challonge_match_id("match__file.zip") is None  # Empty ID

    def test_override_applied_in_etl(self) -> None:
        """Test that overrides are applied during ETL import.

        This test requires:
        1. A test save file with incorrect winner
        2. An override file with correct winner
        3. Verification that override winner is stored in database
        """
        # TODO: Implement integration test
        # This requires setting up a test database and test save file
        # Left as skeleton for developer to complete
        pass
