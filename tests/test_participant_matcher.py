"""Tests for participant matching logic."""

import pytest

from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.participant_matcher import ParticipantMatcher


@pytest.fixture
def test_db(tmp_path) -> TournamentDatabase:
    """Create a temporary test database with participant data."""
    db_path = tmp_path / "test.duckdb"
    # Create database without running migration (schema includes participant tables)
    db = TournamentDatabase.__new__(TournamentDatabase)
    db.db_path = str(db_path)
    db.read_only = False
    db.connection = None
    db._lock = __import__("threading").RLock()

    # Create full schema (includes participant tables)
    db.create_schema()

    # Insert test participants
    with db.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO tournament_participants (
                participant_id, display_name, display_name_normalized
            ) VALUES
            (1001, 'Ninja', 'ninja'),
            (1002, 'FluffybunnyMohawk', 'fluffybunnymohawk'),
            (1003, 'Auro', 'auro')
        """
        )

        # Insert test match
        conn.execute(
            """
            INSERT INTO matches (match_id, challonge_match_id, file_name, file_hash)
            VALUES (100, 426504750, 'test.zip', 'hash123')
        """
        )

        # Insert test players
        conn.execute(
            """
            INSERT INTO players (
                player_id, match_id, player_name, player_name_normalized
            ) VALUES
            (1, 100, 'Ninja', 'ninja'),
            (2, 100, 'FluffybunnyMohawk', 'fluffybunnymohawk')
        """
        )

    yield db
    db.close()


class TestParticipantMatcher:
    """Tests for ParticipantMatcher class."""

    def test_match_player_exact(self, test_db: TournamentDatabase) -> None:
        """Test exact name matching."""
        matcher = ParticipantMatcher(test_db)

        participant_id = matcher.match_player(100, "Ninja")
        assert participant_id == 1001

    def test_match_player_case_insensitive(self, test_db: TournamentDatabase) -> None:
        """Test case-insensitive matching."""
        matcher = ParticipantMatcher(test_db)

        participant_id = matcher.match_player(100, "ninja")
        assert participant_id == 1001

        participant_id = matcher.match_player(100, "NINJA")
        assert participant_id == 1001

    def test_match_player_with_whitespace(self, test_db: TournamentDatabase) -> None:
        """Test matching with whitespace normalization."""
        matcher = ParticipantMatcher(test_db)

        participant_id = matcher.match_player(100, " Ninja ")
        assert participant_id == 1001

    def test_match_player_not_found(self, test_db: TournamentDatabase) -> None:
        """Test matching when participant doesn't exist."""
        matcher = ParticipantMatcher(test_db)

        participant_id = matcher.match_player(100, "UnknownPlayer")
        assert participant_id is None

    def test_match_player_with_override(self, test_db: TournamentDatabase) -> None:
        """Test manual override takes precedence."""
        # Insert override
        with test_db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO participant_name_overrides (
                    override_id, match_id, save_file_player_name, participant_id, reason
                ) VALUES (1, 100, 'WrongName', 1003, 'Test override')
            """
            )

        matcher = ParticipantMatcher(test_db)

        # Should use override despite name not matching
        participant_id = matcher.match_player(100, "WrongName")
        assert participant_id == 1003

    def test_link_match_players(self, test_db: TournamentDatabase) -> None:
        """Test linking all players in a match."""
        matcher = ParticipantMatcher(test_db)

        stats = matcher.link_match_players(100)

        assert stats["total_players"] == 2
        assert stats["matched"] == 2
        assert stats["unmatched"] == 0
        assert stats["unmatched_names"] == []

        # Verify database was updated
        result = test_db.fetch_one(
            """
            SELECT COUNT(*)
            FROM players
            WHERE match_id = 100
            AND participant_id IS NOT NULL
        """
        )

        assert result[0] == 2

    def test_link_match_players_with_unmatched(
        self, test_db: TournamentDatabase
    ) -> None:
        """Test linking when some players don't match."""
        # Add player that won't match
        with test_db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO players (
                    player_id, match_id, player_name, player_name_normalized
                ) VALUES (3, 100, 'UnknownPlayer', 'unknownplayer')
            """
            )

        matcher = ParticipantMatcher(test_db)

        stats = matcher.link_match_players(100)

        assert stats["total_players"] == 3
        assert stats["matched"] == 2
        assert stats["unmatched"] == 1
        assert "UnknownPlayer" in stats["unmatched_names"]
