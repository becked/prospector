"""Tests for database insertion methods."""

import pytest
from pathlib import Path
from tournament_visualizer.data.database import TournamentDatabase


@pytest.fixture
def test_db(tmp_path: Path) -> TournamentDatabase:
    """Create temporary test database with schema.

    Args:
        tmp_path: Pytest temporary directory fixture

    Yields:
        TournamentDatabase instance with schema created
    """
    db_path = tmp_path / "test_history.duckdb"
    db = TournamentDatabase(db_path=str(db_path), read_only=False)

    # Create schema
    db.create_schema()

    # Insert test match and players
    with db.get_connection() as conn:
        # matches table: match_id, challonge_match_id, file_name, file_hash, game_name, save_date,
        #                processed_date, game_mode, map_size, map_class, map_aspect_ratio, turn_style,
        #                turn_timer, victory_conditions, total_turns, winner_player_id
        conn.execute("""INSERT INTO matches VALUES
            (1, NULL, 'test.zip', 'hash123', 'Test Match', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, NULL)
        """)
        # players table: player_id, match_id, player_name, player_name_normalized, civilization,
        #                team_id, difficulty_level, final_score, is_human, final_turn_active
        conn.execute("INSERT INTO players VALUES (1, 1, 'Player1', 'player1', 'CIVILIZATION_ROME', NULL, NULL, 0, TRUE, NULL)")
        conn.execute("INSERT INTO players VALUES (2, 1, 'Player2', 'player2', 'CIVILIZATION_CARTHAGE', NULL, NULL, 0, TRUE, NULL)")

    yield db

    db.close()


def test_bulk_insert_points_history(test_db: TournamentDatabase) -> None:
    """Test inserting points history data."""
    # Sample data
    points_data = [
        {"match_id": 1, "player_id": 1, "turn_number": 2, "points": 5},
        {"match_id": 1, "player_id": 1, "turn_number": 3, "points": 10},
        {"match_id": 1, "player_id": 1, "turn_number": 4, "points": 15},
    ]

    # Insert data
    test_db.bulk_insert_points_history(points_data)

    # Verify insertion
    with test_db.get_connection() as conn:
        result = conn.execute("""
            SELECT turn_number, points
            FROM player_points_history
            WHERE match_id = ? AND player_id = ?
            ORDER BY turn_number
        """, [1, 1]).fetchall()

    assert len(result) == 3
    assert result[0] == (2, 5)
    assert result[1] == (3, 10)
    assert result[2] == (4, 15)


def test_bulk_insert_points_history_empty(test_db: TournamentDatabase) -> None:
    """Test that empty data is handled gracefully."""
    test_db.bulk_insert_points_history([])

    # Should not crash, and no data should be inserted
    with test_db.get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM player_points_history").fetchone()[0]

    assert count == 0


def test_bulk_insert_military_history(test_db: TournamentDatabase) -> None:
    """Test inserting military power history data."""
    military_data = [
        {"match_id": 1, "player_id": 1, "turn_number": 2, "military_power": 0},
        {"match_id": 1, "player_id": 1, "turn_number": 3, "military_power": 10},
        {"match_id": 1, "player_id": 2, "turn_number": 2, "military_power": 5},
    ]

    test_db.bulk_insert_military_history(military_data)

    # Verify insertion
    with test_db.get_connection() as conn:
        result = conn.execute("""
            SELECT player_id, turn_number, military_power
            FROM player_military_history
            WHERE match_id = ?
            ORDER BY player_id, turn_number
        """, [1]).fetchall()

    assert len(result) == 3
    assert result[0] == (1, 2, 0)
    assert result[1] == (1, 3, 10)
    assert result[2] == (2, 2, 5)


def test_bulk_insert_legitimacy_history(test_db: TournamentDatabase) -> None:
    """Test inserting legitimacy history data."""
    legitimacy_data = [
        {"match_id": 1, "player_id": 1, "turn_number": 2, "legitimacy": 100},
        {"match_id": 1, "player_id": 1, "turn_number": 3, "legitimacy": 95},
        {"match_id": 1, "player_id": 1, "turn_number": 4, "legitimacy": 90},
    ]

    test_db.bulk_insert_legitimacy_history(legitimacy_data)

    # Verify insertion
    with test_db.get_connection() as conn:
        result = conn.execute("""
            SELECT turn_number, legitimacy
            FROM player_legitimacy_history
            WHERE match_id = ? AND player_id = ?
            ORDER BY turn_number
        """, [1, 1]).fetchall()

    assert len(result) == 3
    assert result[0] == (2, 100)
    assert result[1] == (3, 95)
    assert result[2] == (4, 90)


def test_bulk_insert_family_opinion_history(test_db: TournamentDatabase) -> None:
    """Test inserting family opinion history data."""
    family_data = [
        {"match_id": 1, "player_id": 1, "turn_number": 2, "family_name": "FAMILY_JULII", "opinion": 100},
        {"match_id": 1, "player_id": 1, "turn_number": 3, "family_name": "FAMILY_JULII", "opinion": 95},
        {"match_id": 1, "player_id": 1, "turn_number": 2, "family_name": "FAMILY_BRUTII", "opinion": 80},
    ]

    test_db.bulk_insert_family_opinion_history(family_data)

    # Verify insertion
    with test_db.get_connection() as conn:
        result = conn.execute("""
            SELECT turn_number, family_name, opinion
            FROM family_opinion_history
            WHERE match_id = ? AND player_id = ?
            ORDER BY family_name, turn_number
        """, [1, 1]).fetchall()

    assert len(result) == 3
    assert result[0] == (2, "FAMILY_BRUTII", 80)
    assert result[1] == (2, "FAMILY_JULII", 100)
    assert result[2] == (3, "FAMILY_JULII", 95)


def test_bulk_insert_religion_opinion_history(test_db: TournamentDatabase) -> None:
    """Test inserting religion opinion history data."""
    religion_data = [
        {"match_id": 1, "player_id": 1, "turn_number": 2, "religion_name": "RELIGION_JUPITER", "opinion": 100},
        {"match_id": 1, "player_id": 1, "turn_number": 3, "religion_name": "RELIGION_JUPITER", "opinion": 100},
        {"match_id": 1, "player_id": 2, "turn_number": 2, "religion_name": "RELIGION_BAAL", "opinion": 100},
    ]

    test_db.bulk_insert_religion_opinion_history(religion_data)

    # Verify insertion
    with test_db.get_connection() as conn:
        result = conn.execute("""
            SELECT player_id, turn_number, religion_name, opinion
            FROM religion_opinion_history
            WHERE match_id = ?
            ORDER BY player_id, turn_number
        """, [1]).fetchall()

    assert len(result) == 3
    assert result[0] == (1, 2, "RELIGION_JUPITER", 100)
    assert result[1] == (1, 3, "RELIGION_JUPITER", 100)
    assert result[2] == (2, 2, "RELIGION_BAAL", 100)


def test_bulk_insert_all_history_types(test_db: TournamentDatabase) -> None:
    """Test inserting all history types together for a complete match."""
    # Points
    test_db.bulk_insert_points_history([
        {"match_id": 1, "player_id": 1, "turn_number": 2, "points": 5},
        {"match_id": 1, "player_id": 2, "turn_number": 2, "points": 3},
    ])

    # Military
    test_db.bulk_insert_military_history([
        {"match_id": 1, "player_id": 1, "turn_number": 2, "military_power": 10},
        {"match_id": 1, "player_id": 2, "turn_number": 2, "military_power": 8},
    ])

    # Legitimacy
    test_db.bulk_insert_legitimacy_history([
        {"match_id": 1, "player_id": 1, "turn_number": 2, "legitimacy": 100},
        {"match_id": 1, "player_id": 2, "turn_number": 2, "legitimacy": 95},
    ])

    # Family opinions
    test_db.bulk_insert_family_opinion_history([
        {"match_id": 1, "player_id": 1, "turn_number": 2, "family_name": "FAMILY_JULII", "opinion": 90},
    ])

    # Religion opinions
    test_db.bulk_insert_religion_opinion_history([
        {"match_id": 1, "player_id": 1, "turn_number": 2, "religion_name": "RELIGION_JUPITER", "opinion": 85},
    ])

    # Verify all data was inserted
    with test_db.get_connection() as conn:
        points_count = conn.execute("SELECT COUNT(*) FROM player_points_history").fetchone()[0]
        military_count = conn.execute("SELECT COUNT(*) FROM player_military_history").fetchone()[0]
        legitimacy_count = conn.execute("SELECT COUNT(*) FROM player_legitimacy_history").fetchone()[0]
        family_count = conn.execute("SELECT COUNT(*) FROM family_opinion_history").fetchone()[0]
        religion_count = conn.execute("SELECT COUNT(*) FROM religion_opinion_history").fetchone()[0]

    assert points_count == 2
    assert military_count == 2
    assert legitimacy_count == 2
    assert family_count == 1
    assert religion_count == 1
