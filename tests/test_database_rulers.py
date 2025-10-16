"""Tests for ruler database operations."""

import pytest
from pathlib import Path
from tournament_visualizer.data.database import TournamentDatabase


@pytest.fixture
def test_db(tmp_path: Path) -> TournamentDatabase:
    """Create a temporary test database with schema.

    Args:
        tmp_path: Pytest temporary directory fixture

    Yields:
        TournamentDatabase instance with schema created
    """
    db_path = tmp_path / "test.duckdb"
    db = TournamentDatabase(db_path=str(db_path), read_only=False)

    # Create schema
    db.create_schema()

    # Insert test matches and players
    with db.get_connection() as conn:
        conn.execute("""INSERT INTO matches VALUES
            (1, NULL, 'test.zip', 'hash123', 'Test Match 1', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, NULL)
        """)
        conn.execute("""INSERT INTO matches VALUES
            (100, NULL, 'test2.zip', 'hash456', 'Test Match 100', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, NULL)
        """)
        conn.execute("""INSERT INTO matches VALUES
            (101, NULL, 'test3.zip', 'hash789', 'Test Match 101', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, NULL)
        """)
        conn.execute("INSERT INTO players VALUES (1, 1, 'Player1', 'player1', 'CIVILIZATION_ROME', NULL, NULL, 0, TRUE, NULL)")
        conn.execute("INSERT INTO players VALUES (2, 1, 'Player2', 'player2', 'CIVILIZATION_CARTHAGE', NULL, NULL, 0, TRUE, NULL)")

    yield db

    db.close()


class TestBulkInsertRulers:
    """Tests for bulk_insert_rulers() method."""

    def test_bulk_insert_rulers_basic(self, test_db: TournamentDatabase) -> None:
        """Test basic ruler insertion."""
        rulers = [
            {
                "player_id": 1,
                "character_id": 9,
                "ruler_name": "Yazdegerd",
                "archetype": "Schemer",
                "starting_trait": "Educated",
                "succession_order": 0,
                "succession_turn": 1,
            },
            {
                "player_id": 1,
                "character_id": 20,
                "ruler_name": "Shapur",
                "archetype": "Tactician",
                "starting_trait": "Affable",
                "succession_order": 1,
                "succession_turn": 47,
            },
        ]

        test_db.bulk_insert_rulers(match_id=1, rulers=rulers)

        # Verify insertion
        with test_db.get_connection() as conn:
            result = conn.execute(
                "SELECT COUNT(*) FROM rulers WHERE match_id = 1"
            ).fetchone()

        assert result[0] == 2

    def test_bulk_insert_rulers_empty_list(self, test_db: TournamentDatabase) -> None:
        """Test that empty ruler list is handled gracefully."""
        test_db.bulk_insert_rulers(match_id=1, rulers=[])

        # Should not raise error
        with test_db.get_connection() as conn:
            result = conn.execute(
                "SELECT COUNT(*) FROM rulers WHERE match_id = 1"
            ).fetchone()

        assert result[0] == 0

    def test_bulk_insert_rulers_validates_required_fields(
        self, test_db: TournamentDatabase
    ) -> None:
        """Test that rulers with missing required fields are skipped."""
        rulers = [
            {
                # Missing player_id - should be skipped
                "character_id": 9,
                "ruler_name": "Yazdegerd",
                "archetype": "Schemer",
                "starting_trait": "Educated",
                "succession_order": 0,
                "succession_turn": 1,
            },
            {
                # Valid ruler - should be inserted
                "player_id": 1,
                "character_id": 20,
                "ruler_name": "Shapur",
                "archetype": "Tactician",
                "starting_trait": "Affable",
                "succession_order": 1,
                "succession_turn": 47,
            },
        ]

        test_db.bulk_insert_rulers(match_id=1, rulers=rulers)

        # Only the valid ruler should be inserted
        with test_db.get_connection() as conn:
            result = conn.execute(
                "SELECT COUNT(*) FROM rulers WHERE match_id = 1"
            ).fetchone()

        assert result[0] == 1

    def test_bulk_insert_rulers_handles_null_optional_fields(
        self, test_db: TournamentDatabase
    ) -> None:
        """Test that null values in optional fields are handled correctly."""
        rulers = [
            {
                "player_id": 1,
                "character_id": 9,
                "ruler_name": None,  # Optional
                "archetype": None,  # Optional
                "starting_trait": None,  # Optional
                "succession_order": 0,
                "succession_turn": 1,
            },
        ]

        test_db.bulk_insert_rulers(match_id=1, rulers=rulers)

        # Should insert successfully
        with test_db.get_connection() as conn:
            result = conn.execute(
                "SELECT * FROM rulers WHERE match_id = 1"
            ).fetchone()

        assert result is not None
        # Verify nulls are preserved
        assert result[4] is None  # ruler_name
        assert result[5] is None  # archetype
        assert result[6] is None  # starting_trait

    def test_bulk_insert_rulers_multiple_matches(
        self, test_db: TournamentDatabase
    ) -> None:
        """Test inserting rulers for multiple matches."""
        rulers_match1 = [
            {
                "player_id": 1,
                "character_id": 9,
                "ruler_name": "Yazdegerd",
                "archetype": "Schemer",
                "starting_trait": "Educated",
                "succession_order": 0,
                "succession_turn": 1,
            },
        ]

        rulers_match2 = [
            {
                "player_id": 1,
                "character_id": 5,
                "ruler_name": "Naqia",
                "archetype": "Scholar",
                "starting_trait": "Intelligent",
                "succession_order": 0,
                "succession_turn": 1,
            },
        ]

        test_db.bulk_insert_rulers(match_id=100, rulers=rulers_match1)
        test_db.bulk_insert_rulers(match_id=101, rulers=rulers_match2)

        # Verify both matches have rulers
        with test_db.get_connection() as conn:
            result1 = conn.execute(
                "SELECT COUNT(*) FROM rulers WHERE match_id = 100"
            ).fetchone()
            result2 = conn.execute(
                "SELECT COUNT(*) FROM rulers WHERE match_id = 101"
            ).fetchone()

        assert result1[0] == 1
        assert result2[0] == 1

    def test_bulk_insert_rulers_preserves_succession_order(
        self, test_db: TournamentDatabase
    ) -> None:
        """Test that succession_order is correctly preserved."""
        rulers = [
            {
                "player_id": 1,
                "character_id": 9,
                "ruler_name": "First",
                "archetype": "Schemer",
                "starting_trait": "Educated",
                "succession_order": 0,
                "succession_turn": 1,
            },
            {
                "player_id": 1,
                "character_id": 20,
                "ruler_name": "Second",
                "archetype": "Tactician",
                "starting_trait": "Brave",
                "succession_order": 1,
                "succession_turn": 30,
            },
            {
                "player_id": 1,
                "character_id": 64,
                "ruler_name": "Third",
                "archetype": "Commander",
                "starting_trait": "Tough",
                "succession_order": 2,
                "succession_turn": 60,
            },
        ]

        test_db.bulk_insert_rulers(match_id=1, rulers=rulers)

        # Query in succession order
        with test_db.get_connection() as conn:
            results = conn.execute(
                """
                SELECT ruler_name, succession_order, succession_turn
                FROM rulers
                WHERE match_id = 1
                ORDER BY succession_order
                """
            ).fetchall()

        assert len(results) == 3
        assert results[0][0] == "First"
        assert results[0][1] == 0
        assert results[0][2] == 1
        assert results[1][0] == "Second"
        assert results[1][1] == 1
        assert results[1][2] == 30
        assert results[2][0] == "Third"
        assert results[2][1] == 2
        assert results[2][2] == 60
