"""Tests for the match filtering helper method.

Test Strategy:
- Test that no filters returns all match IDs
- Test filtering by bracket (Winners/Losers/Unknown)
- Test filtering by turn range
- Test filtering by map properties
- Test filtering by nations (civilizations)
- Test filtering by players
- Test combining multiple filters
- Test impossible filters return empty list
"""

import pytest

from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.queries import TournamentQueries


@pytest.fixture
def test_db_with_filters(tmp_path):
    """Create database with comprehensive filter test data."""
    db_path = tmp_path / "filter_test.duckdb"

    # Create database with schema
    db = TournamentDatabase(str(db_path), read_only=False)
    db.create_schema()

    with db.get_connection() as conn:
        # Insert test matches with various properties
        conn.execute("""
            INSERT INTO matches (
                match_id, file_name, file_hash, game_name,
                tournament_round, total_turns, challonge_match_id,
                map_size, map_class, map_aspect_ratio
            ) VALUES
                (1, 'match1.zip', 'hash1', 'Game 1', 1, 50, 1001, 'Medium', 'Inland', 'Standard'),
                (2, 'match2.zip', 'hash2', 'Game 2', 1, 75, 1002, 'Large', 'Coastal', 'Wide'),
                (3, 'match3.zip', 'hash3', 'Game 3', 2, 100, 1003, 'Medium', 'Inland', 'Standard'),
                (4, 'match4.zip', 'hash4', 'Game 4', -1, 60, 1004, 'Small', 'Islands', 'Tall'),
                (5, 'match5.zip', 'hash5', 'Game 5', -2, 120, 1005, 'Large', 'Coastal', 'Wide'),
                (6, 'match6.zip', 'hash6', 'Game 6', NULL, 80, NULL, 'Medium', 'Inland', 'Standard')
        """)

        # Insert test players with civilizations
        # Note: player_id must be globally unique (primary key)
        conn.execute("""
            INSERT INTO players (
                match_id, player_id, player_name, player_name_normalized, civilization
            ) VALUES
                -- Match 1: Rome vs Carthage
                (1, 1, 'Fluffbunny', 'fluffbunny', 'Rome'),
                (1, 2, 'Becked', 'becked', 'Carthage'),
                -- Match 2: Greece vs Egypt
                (2, 3, 'Becked', 'becked', 'Greece'),
                (2, 4, 'Alice', 'alice', 'Egypt'),
                -- Match 3: Rome vs Persia
                (3, 5, 'Fluffbunny', 'fluffbunny', 'Rome'),
                (3, 6, 'Bob', 'bob', 'Persia'),
                -- Match 4: Carthage vs Babylon
                (4, 7, 'Alice', 'alice', 'Carthage'),
                (4, 8, 'Bob', 'bob', 'Babylon'),
                -- Match 5: Rome vs Greece
                (5, 9, 'Fluffbunny', 'fluffbunny', 'Rome'),
                (5, 10, 'Becked', 'becked', 'Greece'),
                -- Match 6: Egypt vs Persia
                (6, 11, 'Alice', 'alice', 'Egypt'),
                (6, 12, 'Bob', 'bob', 'Persia')
        """)

    yield db
    db.close()


@pytest.fixture
def test_queries(test_db_with_filters):
    """Create queries instance with test database."""
    return TournamentQueries(test_db_with_filters)


def test_get_filtered_match_ids_no_filters(test_queries):
    """Test that no filters returns all match IDs."""
    match_ids = test_queries._get_filtered_match_ids()
    assert len(match_ids) == 6
    assert isinstance(match_ids, list)
    assert all(isinstance(mid, int) for mid in match_ids)
    assert sorted(match_ids) == [1, 2, 3, 4, 5, 6]


def test_get_filtered_match_ids_by_bracket_winners(test_queries):
    """Test filtering by Winners bracket."""
    all_matches = test_queries._get_filtered_match_ids()
    winners_matches = test_queries._get_filtered_match_ids(bracket="Winners")

    assert len(winners_matches) == 3  # Matches 1, 2, 3
    assert len(winners_matches) < len(all_matches)
    assert sorted(winners_matches) == [1, 2, 3]


def test_get_filtered_match_ids_by_bracket_losers(test_queries):
    """Test filtering by Losers bracket."""
    losers_matches = test_queries._get_filtered_match_ids(bracket="Losers")

    assert len(losers_matches) == 2  # Matches 4, 5
    assert sorted(losers_matches) == [4, 5]


def test_get_filtered_match_ids_by_bracket_unknown(test_queries):
    """Test filtering by Unknown bracket."""
    unknown_matches = test_queries._get_filtered_match_ids(bracket="Unknown")

    assert len(unknown_matches) == 1  # Match 6
    assert unknown_matches == [6]


def test_get_filtered_match_ids_by_specific_round(test_queries):
    """Test filtering by specific round number."""
    round_1_matches = test_queries._get_filtered_match_ids(tournament_round=1)

    assert len(round_1_matches) == 2  # Matches 1, 2
    assert sorted(round_1_matches) == [1, 2]


def test_get_filtered_match_ids_by_min_turns(test_queries):
    """Test filtering by minimum turns."""
    matches = test_queries._get_filtered_match_ids(min_turns=80)

    # Matches with >= 80 turns: 3 (100), 5 (120), 6 (80)
    assert len(matches) == 3
    assert sorted(matches) == [3, 5, 6]


def test_get_filtered_match_ids_by_max_turns(test_queries):
    """Test filtering by maximum turns."""
    matches = test_queries._get_filtered_match_ids(max_turns=75)

    # Matches with <= 75 turns: 1 (50), 2 (75), 4 (60)
    assert len(matches) == 3
    assert sorted(matches) == [1, 2, 4]


def test_get_filtered_match_ids_by_turn_range(test_queries):
    """Test filtering by turn range."""
    matches = test_queries._get_filtered_match_ids(min_turns=60, max_turns=100)

    # Matches with 60-100 turns: 2 (75), 3 (100), 4 (60), 6 (80)
    assert len(matches) == 4
    assert sorted(matches) == [2, 3, 4, 6]


def test_get_filtered_match_ids_by_map_size(test_queries):
    """Test filtering by map size."""
    matches = test_queries._get_filtered_match_ids(map_size="Large")

    # Matches with Large map: 2, 5
    assert len(matches) == 2
    assert sorted(matches) == [2, 5]


def test_get_filtered_match_ids_by_map_class(test_queries):
    """Test filtering by map class."""
    matches = test_queries._get_filtered_match_ids(map_class="Coastal")

    # Matches with Coastal map: 2, 5
    assert len(matches) == 2
    assert sorted(matches) == [2, 5]


def test_get_filtered_match_ids_by_map_aspect(test_queries):
    """Test filtering by map aspect ratio."""
    matches = test_queries._get_filtered_match_ids(map_aspect="Wide")

    # Matches with Wide aspect: 2, 5
    assert len(matches) == 2
    assert sorted(matches) == [2, 5]


def test_get_filtered_match_ids_by_nation(test_queries):
    """Test filtering by civilization."""
    matches = test_queries._get_filtered_match_ids(nations=["Rome"])

    # Matches where Rome was played: 1, 3, 5
    assert len(matches) == 3
    assert sorted(matches) == [1, 3, 5]


def test_get_filtered_match_ids_by_multiple_nations(test_queries):
    """Test filtering by multiple civilizations."""
    matches = test_queries._get_filtered_match_ids(nations=["Rome", "Greece"])

    # Matches where Rome OR Greece was played: 1, 2, 3, 5
    assert len(matches) == 4
    assert sorted(matches) == [1, 2, 3, 5]


def test_get_filtered_match_ids_by_player(test_queries):
    """Test filtering by player name."""
    matches = test_queries._get_filtered_match_ids(players=["Fluffbunny"])

    # Matches where Fluffbunny played: 1, 3, 5
    assert len(matches) == 3
    assert sorted(matches) == [1, 3, 5]


def test_get_filtered_match_ids_by_multiple_players(test_queries):
    """Test filtering by multiple players."""
    matches = test_queries._get_filtered_match_ids(players=["Fluffbunny", "Alice"])

    # Matches where Fluffbunny OR Alice played: 1, 2, 3, 4, 5, 6
    assert len(matches) == 6
    assert sorted(matches) == [1, 2, 3, 4, 5, 6]


def test_get_filtered_match_ids_combined_filters(test_queries):
    """Test multiple filters combined."""
    matches = test_queries._get_filtered_match_ids(
        bracket="Winners",
        min_turns=50,
        nations=["Rome"]
    )

    # Winners bracket + min 50 turns + Rome: 1, 3
    assert len(matches) == 2
    assert sorted(matches) == [1, 3]


def test_get_filtered_match_ids_complex_combination(test_queries):
    """Test complex filter combination."""
    matches = test_queries._get_filtered_match_ids(
        bracket="Winners",
        map_size="Medium",
        nations=["Rome"],
        players=["Fluffbunny"]
    )

    # Winners + Medium + Rome + Fluffbunny: 1, 3
    assert len(matches) == 2
    assert sorted(matches) == [1, 3]


def test_get_filtered_match_ids_no_matches(test_queries):
    """Test that impossible filters return empty list."""
    matches = test_queries._get_filtered_match_ids(
        nations=["NonexistentCivilization"]
    )

    assert matches == []


def test_get_filtered_match_ids_empty_lists(test_queries):
    """Test that empty lists are handled correctly."""
    # Empty nation list should return all matches
    matches = test_queries._get_filtered_match_ids(nations=[])

    assert len(matches) == 6

    # Empty player list should return all matches
    matches = test_queries._get_filtered_match_ids(players=[])

    assert len(matches) == 6


def test_get_filtered_match_ids_none_values(test_queries):
    """Test that None values don't filter."""
    matches = test_queries._get_filtered_match_ids(
        tournament_round=None,
        bracket=None,
        min_turns=None,
        max_turns=None,
        map_size=None,
        map_class=None,
        map_aspect=None,
        nations=None,
        players=None,
    )

    # All None should return all matches
    assert len(matches) == 6
