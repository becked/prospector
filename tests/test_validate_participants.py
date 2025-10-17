"""Tests for participant validation script logic.

Tests validation checks for:
- Participant data integrity
- Player-participant link validity
- Match-participant consistency
- Orphaned references
"""

import pytest
from tournament_visualizer.data.database import TournamentDatabase


@pytest.fixture
def test_db(tmp_path):
    """Create a test database with complete participant setup."""
    db_path = tmp_path / "test.duckdb"
    db = TournamentDatabase(str(db_path))

    # Insert test participants
    db.conn.execute("""
        INSERT INTO tournament_participants (
            participant_id, display_name, display_name_normalized,
            challonge_username, challonge_user_id, seed
        ) VALUES
        (1001, 'TestPlayer1', 'testplayer1', 'player1', 111, 1),
        (1002, 'TestPlayer2', 'testplayer2', 'player2', 222, 2),
        (1003, 'TestPlayer3', 'testplayer3', 'player3', 333, 3)
    """)

    # Insert test matches
    db.conn.execute("""
        INSERT INTO matches (
            match_id, challonge_match_id, file_name, file_hash,
            player1_participant_id, player2_participant_id, winner_participant_id
        ) VALUES
        (100, 1000, 'match1.zip', 'hash1', 1001, 1002, 1001),
        (101, 1001, 'match2.zip', 'hash2', 1002, 1003, 1003)
    """)

    # Insert test players (correctly linked)
    db.conn.execute("""
        INSERT INTO players (
            player_id, match_id, player_name, player_name_normalized, participant_id
        ) VALUES
        (1, 100, 'TestPlayer1', 'testplayer1', 1001),
        (2, 100, 'TestPlayer2', 'testplayer2', 1002),
        (3, 101, 'TestPlayer2', 'testplayer2', 1002),
        (4, 101, 'TestPlayer3', 'testplayer3', 1003)
    """)

    yield db
    db.close()


class TestParticipantDataValidation:
    """Tests for participant data integrity validation."""

    def test_valid_participant_data(self, test_db):
        """Test validation passes with valid participant data."""
        # Check for NULL display names
        null_names = test_db.conn.execute("""
            SELECT COUNT(*)
            FROM tournament_participants
            WHERE display_name IS NULL OR display_name = ''
        """).fetchone()[0]

        assert null_names == 0

        # Check normalized names
        null_normalized = test_db.conn.execute("""
            SELECT COUNT(*)
            FROM tournament_participants
            WHERE display_name_normalized IS NULL OR display_name_normalized = ''
        """).fetchone()[0]

        assert null_normalized == 0

    def test_detects_null_display_names(self, test_db):
        """Test detection of NULL display names."""
        # Insert participant with NULL display name
        test_db.conn.execute("""
            INSERT INTO tournament_participants (
                participant_id, display_name, display_name_normalized
            ) VALUES (9999, NULL, 'test')
        """)

        null_names = test_db.conn.execute("""
            SELECT COUNT(*)
            FROM tournament_participants
            WHERE display_name IS NULL OR display_name = ''
        """).fetchone()[0]

        assert null_names == 1

    def test_detects_empty_display_names(self, test_db):
        """Test detection of empty display names."""
        test_db.conn.execute("""
            INSERT INTO tournament_participants (
                participant_id, display_name, display_name_normalized
            ) VALUES (9998, '', 'test')
        """)

        empty_names = test_db.conn.execute("""
            SELECT COUNT(*)
            FROM tournament_participants
            WHERE display_name IS NULL OR display_name = ''
        """).fetchone()[0]

        assert empty_names == 1

    def test_detects_null_normalized_names(self, test_db):
        """Test detection of NULL normalized names."""
        test_db.conn.execute("""
            INSERT INTO tournament_participants (
                participant_id, display_name, display_name_normalized
            ) VALUES (9997, 'Test', NULL)
        """)

        null_normalized = test_db.conn.execute("""
            SELECT COUNT(*)
            FROM tournament_participants
            WHERE display_name_normalized IS NULL OR display_name_normalized = ''
        """).fetchone()[0]

        assert null_normalized == 1


class TestPlayerParticipantLinkValidation:
    """Tests for player-participant link validation."""

    def test_valid_player_participant_links(self, test_db):
        """Test validation passes with valid links."""
        # Check for invalid participant_id references
        invalid_refs = test_db.conn.execute("""
            SELECT COUNT(*)
            FROM players p
            LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
            WHERE p.participant_id IS NOT NULL
            AND tp.participant_id IS NULL
        """).fetchone()[0]

        assert invalid_refs == 0

    def test_detects_invalid_participant_references(self, test_db):
        """Test detection of invalid participant_id references."""
        # Insert player with invalid participant_id
        test_db.conn.execute("""
            INSERT INTO players (
                player_id, match_id, player_name, player_name_normalized, participant_id
            ) VALUES (999, 100, 'Invalid', 'invalid', 9999)
        """)

        invalid_refs = test_db.conn.execute("""
            SELECT COUNT(*)
            FROM players p
            LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
            WHERE p.participant_id IS NOT NULL
            AND tp.participant_id IS NULL
        """).fetchone()[0]

        assert invalid_refs == 1

    def test_allows_null_participant_references(self, test_db):
        """Test that NULL participant_id is valid (unlinked players)."""
        # Insert player without participant link
        test_db.conn.execute("""
            INSERT INTO players (
                player_id, match_id, player_name, player_name_normalized, participant_id
            ) VALUES (998, 100, 'Unlinked', 'unlinked', NULL)
        """)

        # Should not count as invalid
        invalid_refs = test_db.conn.execute("""
            SELECT COUNT(*)
            FROM players p
            LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
            WHERE p.participant_id IS NOT NULL
            AND tp.participant_id IS NULL
        """).fetchone()[0]

        assert invalid_refs == 0


class TestMatchParticipantConsistency:
    """Tests for match-participant consistency validation."""

    def test_valid_match_participant_consistency(self, test_db):
        """Test validation passes with consistent data."""
        # For each match, check if players' participant_ids match
        inconsistent = test_db.conn.execute("""
            WITH match_players AS (
                SELECT
                    m.match_id,
                    m.player1_participant_id,
                    m.player2_participant_id,
                    p.participant_id as player_participant_id
                FROM matches m
                JOIN players p ON m.match_id = p.match_id
                WHERE m.player1_participant_id IS NOT NULL
                AND m.player2_participant_id IS NOT NULL
                AND p.participant_id IS NOT NULL
            )
            SELECT COUNT(DISTINCT match_id)
            FROM match_players
            WHERE player_participant_id NOT IN (player1_participant_id, player2_participant_id)
        """).fetchone()[0]

        assert inconsistent == 0

    def test_detects_mismatched_participant_ids(self, test_db):
        """Test detection of mismatched participant IDs."""
        # Insert player with wrong participant_id
        test_db.conn.execute("""
            INSERT INTO players (
                player_id, match_id, player_name, player_name_normalized, participant_id
            ) VALUES (997, 100, 'Mismatched', 'mismatched', 1003)
        """)

        # This player has participant 1003, but match 100 only has 1001 and 1002
        inconsistent = test_db.conn.execute("""
            WITH match_players AS (
                SELECT
                    m.match_id,
                    m.player1_participant_id,
                    m.player2_participant_id,
                    p.participant_id as player_participant_id
                FROM matches m
                JOIN players p ON m.match_id = p.match_id
                WHERE m.player1_participant_id IS NOT NULL
                AND m.player2_participant_id IS NOT NULL
                AND p.participant_id IS NOT NULL
            )
            SELECT COUNT(DISTINCT match_id)
            FROM match_players
            WHERE player_participant_id NOT IN (player1_participant_id, player2_participant_id)
        """).fetchone()[0]

        assert inconsistent == 1

    def test_ignores_null_participant_data(self, test_db):
        """Test that matches/players with NULL participants don't fail validation."""
        # Insert match without participant data
        test_db.conn.execute("""
            INSERT INTO matches (
                match_id, challonge_match_id, file_name, file_hash,
                player1_participant_id, player2_participant_id
            ) VALUES (199, 1999, 'match99.zip', 'hash99', NULL, NULL)
        """)

        # Insert players without participant data
        test_db.conn.execute("""
            INSERT INTO players (
                player_id, match_id, player_name, player_name_normalized, participant_id
            ) VALUES
            (991, 199, 'Player1', 'player1', NULL),
            (992, 199, 'Player2', 'player2', NULL)
        """)

        # Should not count as inconsistent (NULL data is allowed)
        inconsistent = test_db.conn.execute("""
            WITH match_players AS (
                SELECT
                    m.match_id,
                    m.player1_participant_id,
                    m.player2_participant_id,
                    p.participant_id as player_participant_id
                FROM matches m
                JOIN players p ON m.match_id = p.match_id
                WHERE m.player1_participant_id IS NOT NULL
                AND m.player2_participant_id IS NOT NULL
                AND p.participant_id IS NOT NULL
            )
            SELECT COUNT(DISTINCT match_id)
            FROM match_players
            WHERE player_participant_id NOT IN (player1_participant_id, player2_participant_id)
        """).fetchone()[0]

        assert inconsistent == 0


class TestParticipantSummaryStats:
    """Tests for validation summary statistics."""

    def test_participant_count(self, test_db):
        """Test participant count calculation."""
        total = test_db.conn.execute(
            "SELECT COUNT(*) FROM tournament_participants"
        ).fetchone()[0]

        assert total == 3

    def test_linked_player_count(self, test_db):
        """Test linked player count calculation."""
        total_players = test_db.conn.execute(
            "SELECT COUNT(*) FROM players"
        ).fetchone()[0]

        linked_players = test_db.conn.execute(
            "SELECT COUNT(*) FROM players WHERE participant_id IS NOT NULL"
        ).fetchone()[0]

        assert total_players == 4
        assert linked_players == 4

    def test_linked_player_percentage(self, test_db):
        """Test linked player percentage calculation."""
        total_players = test_db.conn.execute(
            "SELECT COUNT(*) FROM players"
        ).fetchone()[0]

        linked_players = test_db.conn.execute(
            "SELECT COUNT(*) FROM players WHERE participant_id IS NOT NULL"
        ).fetchone()[0]

        percentage = (linked_players / total_players) * 100
        assert percentage == 100.0

    def test_unique_participants_with_players(self, test_db):
        """Test count of unique participants that have players."""
        unique_participants = test_db.conn.execute("""
            SELECT COUNT(DISTINCT participant_id)
            FROM players
            WHERE participant_id IS NOT NULL
        """).fetchone()[0]

        assert unique_participants == 3

    def test_matches_with_participant_data(self, test_db):
        """Test count of matches with participant data."""
        matches_with_participants = test_db.conn.execute("""
            SELECT COUNT(*)
            FROM matches
            WHERE player1_participant_id IS NOT NULL
            AND player2_participant_id IS NOT NULL
        """).fetchone()[0]

        total_matches = test_db.conn.execute(
            "SELECT COUNT(*) FROM matches"
        ).fetchone()[0]

        assert matches_with_participants == 2
        assert total_matches == 2


class TestOrphanedReferences:
    """Tests for orphaned reference detection."""

    def test_detects_orphaned_match_participant_ids(self, test_db):
        """Test detection of match participant IDs with no matching participant."""
        # Update match to reference non-existent participant
        test_db.conn.execute("""
            UPDATE matches
            SET winner_participant_id = 9999
            WHERE match_id = 100
        """)

        # Check for orphaned winner references
        orphaned = test_db.conn.execute("""
            SELECT COUNT(*)
            FROM matches m
            LEFT JOIN tournament_participants tp ON m.winner_participant_id = tp.participant_id
            WHERE m.winner_participant_id IS NOT NULL
            AND tp.participant_id IS NULL
        """).fetchone()[0]

        assert orphaned == 1

    def test_detects_multiple_orphaned_references_in_match(self, test_db):
        """Test detection of multiple orphaned participant references in one match."""
        # Update match with multiple invalid references
        test_db.conn.execute("""
            UPDATE matches
            SET player1_participant_id = 8888,
                player2_participant_id = 9999
            WHERE match_id = 100
        """)

        # Check player1
        orphaned_p1 = test_db.conn.execute("""
            SELECT COUNT(*)
            FROM matches m
            LEFT JOIN tournament_participants tp ON m.player1_participant_id = tp.participant_id
            WHERE m.player1_participant_id IS NOT NULL
            AND tp.participant_id IS NULL
        """).fetchone()[0]

        # Check player2
        orphaned_p2 = test_db.conn.execute("""
            SELECT COUNT(*)
            FROM matches m
            LEFT JOIN tournament_participants tp ON m.player2_participant_id = tp.participant_id
            WHERE m.player2_participant_id IS NOT NULL
            AND tp.participant_id IS NULL
        """).fetchone()[0]

        assert orphaned_p1 == 1
        assert orphaned_p2 == 1

    def test_detects_unused_participants(self, test_db):
        """Test detection of participants with no players."""
        # Insert participant with no players
        test_db.conn.execute("""
            INSERT INTO tournament_participants (
                participant_id, display_name, display_name_normalized
            ) VALUES (9996, 'Unused', 'unused')
        """)

        # Find participants without players
        unused = test_db.conn.execute("""
            SELECT COUNT(*)
            FROM tournament_participants tp
            LEFT JOIN players p ON tp.participant_id = p.participant_id
            WHERE p.participant_id IS NULL
        """).fetchone()[0]

        assert unused == 1


class TestValidationEdgeCases:
    """Tests for validation edge cases."""

    def test_empty_database(self, tmp_path):
        """Test validation with empty database."""
        db_path = tmp_path / "empty.duckdb"
        db = TournamentDatabase(str(db_path))

        # Should not crash with empty tables
        total_participants = db.conn.execute(
            "SELECT COUNT(*) FROM tournament_participants"
        ).fetchone()[0]

        assert total_participants == 0
        db.close()

    def test_participants_without_matches(self, tmp_path):
        """Test validation when participants exist but no matches."""
        db_path = tmp_path / "test.duckdb"
        db = TournamentDatabase(str(db_path))

        # Add participants
        db.conn.execute("""
            INSERT INTO tournament_participants (
                participant_id, display_name, display_name_normalized
            ) VALUES (1001, 'Test', 'test')
        """)

        # No matches or players
        total_participants = db.conn.execute(
            "SELECT COUNT(*) FROM tournament_participants"
        ).fetchone()[0]

        total_matches = db.conn.execute(
            "SELECT COUNT(*) FROM matches"
        ).fetchone()[0]

        assert total_participants == 1
        assert total_matches == 0
        db.close()

    def test_players_without_participants(self, tmp_path):
        """Test validation when players exist but no participants."""
        db_path = tmp_path / "test.duckdb"
        db = TournamentDatabase(str(db_path))

        # Add match and players without participants
        db.conn.execute("""
            INSERT INTO matches (match_id, challonge_match_id, file_name, file_hash)
            VALUES (100, 1000, 'match.zip', 'hash')
        """)

        db.conn.execute("""
            INSERT INTO players (
                player_id, match_id, player_name, player_name_normalized
            ) VALUES (1, 100, 'Test', 'test')
        """)

        total_players = db.conn.execute(
            "SELECT COUNT(*) FROM players"
        ).fetchone()[0]

        linked_players = db.conn.execute(
            "SELECT COUNT(*) FROM players WHERE participant_id IS NOT NULL"
        ).fetchone()[0]

        assert total_players == 1
        assert linked_players == 0
        db.close()
