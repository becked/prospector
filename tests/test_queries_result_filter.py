"""Tests for result_filter parameter in TournamentQueries.

Test Strategy:
- Test that result_filter=None returns list[int] (existing behavior)
- Test that result_filter="all" returns list[int] (existing behavior)
- Test that result_filter="winners" returns list[tuple[int, int]] with winner pairs
- Test that result_filter="losers" returns list[tuple[int, int]] with loser pairs
- Test that winners and losers are disjoint
- Test that winners + losers covers all players in matches with winner data
- Test that matches without winner data are excluded from winners/losers
"""

import pytest

from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.queries import TournamentQueries


@pytest.fixture
def test_db_with_winners(tmp_path):
    """Create database with match winner test data."""
    db_path = tmp_path / "result_filter_test.duckdb"

    db = TournamentDatabase(str(db_path), read_only=False)
    db.create_schema()

    with db.get_connection() as conn:
        # Insert test matches
        conn.execute("""
            INSERT INTO matches (
                match_id, file_name, file_hash, game_name,
                tournament_round, total_turns, challonge_match_id
            ) VALUES
                (1, 'match1.zip', 'hash1', 'Game 1', 1, 50, 1001),
                (2, 'match2.zip', 'hash2', 'Game 2', 1, 75, 1002),
                (3, 'match3.zip', 'hash3', 'Game 3', 2, 100, 1003),
                (4, 'match4.zip', 'hash4', 'Game 4', -1, 60, NULL)
        """)

        # Insert test players
        conn.execute("""
            INSERT INTO players (
                match_id, player_id, player_name, player_name_normalized, civilization
            ) VALUES
                -- Match 1: Player 1 (winner) vs Player 2
                (1, 1, 'Alice', 'alice', 'Rome'),
                (1, 2, 'Bob', 'bob', 'Carthage'),
                -- Match 2: Player 3 vs Player 4 (winner)
                (2, 3, 'Alice', 'alice', 'Greece'),
                (2, 4, 'Bob', 'bob', 'Egypt'),
                -- Match 3: Player 5 (winner) vs Player 6
                (3, 5, 'Charlie', 'charlie', 'Rome'),
                (3, 6, 'Diana', 'diana', 'Persia'),
                -- Match 4: No winner data (no challonge_match_id)
                (4, 7, 'Eve', 'eve', 'Carthage'),
                (4, 8, 'Frank', 'frank', 'Babylon')
        """)

        # Insert match winners (match 4 has no winner)
        conn.execute("""
            INSERT INTO match_winners (match_id, winner_player_id) VALUES
                (1, 1),  -- Alice wins match 1
                (2, 4),  -- Bob wins match 2
                (3, 5)   -- Charlie wins match 3
        """)

    yield db
    db.close()


@pytest.fixture
def test_queries(test_db_with_winners):
    """Create queries instance with test database."""
    return TournamentQueries(test_db_with_winners)


class TestResultFilterNone:
    """Tests for result_filter=None (default, existing behavior)."""

    def test_returns_list_of_ints(self, test_queries):
        """Without result_filter, returns list of match IDs."""
        result = test_queries._get_filtered_match_ids()
        assert isinstance(result, list)
        assert all(isinstance(x, int) for x in result)

    def test_returns_all_matches(self, test_queries):
        """Returns all matches regardless of winner data."""
        result = test_queries._get_filtered_match_ids()
        assert sorted(result) == [1, 2, 3, 4]


class TestResultFilterAll:
    """Tests for result_filter='all' (same as None)."""

    def test_returns_list_of_ints(self, test_queries):
        """With result_filter='all', returns list of match IDs."""
        result = test_queries._get_filtered_match_ids(result_filter="all")
        assert isinstance(result, list)
        assert all(isinstance(x, int) for x in result)

    def test_returns_all_matches(self, test_queries):
        """Returns all matches regardless of winner data."""
        result = test_queries._get_filtered_match_ids(result_filter="all")
        assert sorted(result) == [1, 2, 3, 4]


class TestResultFilterWinners:
    """Tests for result_filter='winners'."""

    def test_returns_list_of_tuples(self, test_queries):
        """With result_filter='winners', returns (match_id, player_id) tuples."""
        result = test_queries._get_filtered_match_ids(result_filter="winners")
        assert isinstance(result, list)
        assert all(isinstance(x, tuple) and len(x) == 2 for x in result)

    def test_returns_winner_pairs(self, test_queries):
        """Returns correct winner (match_id, player_id) pairs."""
        result = test_queries._get_filtered_match_ids(result_filter="winners")
        result_set = set(result)

        # Expected: (1, 1), (2, 4), (3, 5)
        assert (1, 1) in result_set  # Alice wins match 1
        assert (2, 4) in result_set  # Bob wins match 2
        assert (3, 5) in result_set  # Charlie wins match 3
        assert len(result_set) == 3

    def test_excludes_matches_without_winner_data(self, test_queries):
        """Match 4 has no winner data, should not appear."""
        result = test_queries._get_filtered_match_ids(result_filter="winners")
        match_ids = {m for m, _ in result}
        assert 4 not in match_ids


class TestResultFilterLosers:
    """Tests for result_filter='losers'."""

    def test_returns_list_of_tuples(self, test_queries):
        """With result_filter='losers', returns (match_id, player_id) tuples."""
        result = test_queries._get_filtered_match_ids(result_filter="losers")
        assert isinstance(result, list)
        assert all(isinstance(x, tuple) and len(x) == 2 for x in result)

    def test_returns_loser_pairs(self, test_queries):
        """Returns correct loser (match_id, player_id) pairs."""
        result = test_queries._get_filtered_match_ids(result_filter="losers")
        result_set = set(result)

        # Expected: (1, 2), (2, 3), (3, 6)
        assert (1, 2) in result_set  # Bob loses match 1
        assert (2, 3) in result_set  # Alice loses match 2
        assert (3, 6) in result_set  # Diana loses match 3
        assert len(result_set) == 3

    def test_excludes_matches_without_winner_data(self, test_queries):
        """Match 4 has no winner data, losers also excluded."""
        result = test_queries._get_filtered_match_ids(result_filter="losers")
        match_ids = {m for m, _ in result}
        assert 4 not in match_ids


class TestWinnersAndLosersRelationship:
    """Tests for the relationship between winners and losers."""

    def test_winners_and_losers_are_disjoint(self, test_queries):
        """Winners and losers sets should not overlap."""
        winners = set(test_queries._get_filtered_match_ids(result_filter="winners"))
        losers = set(test_queries._get_filtered_match_ids(result_filter="losers"))
        assert winners.isdisjoint(losers)

    def test_winners_plus_losers_covers_all_players_with_winner_data(
        self, test_queries, test_db_with_winners
    ):
        """Winners + losers should equal all players in matches with winner data."""
        winners = set(test_queries._get_filtered_match_ids(result_filter="winners"))
        losers = set(test_queries._get_filtered_match_ids(result_filter="losers"))
        combined = winners | losers

        # Get all players in matches 1, 2, 3 (matches with winner data)
        with test_db_with_winners.get_connection() as conn:
            df = conn.execute("""
                SELECT DISTINCT match_id, player_id FROM players
                WHERE match_id IN (1, 2, 3)
            """).df()
            expected = set(zip(df["match_id"], df["player_id"]))

        assert combined == expected


class TestResultFilterWithOtherFilters:
    """Tests for result_filter combined with other filters."""

    def test_winners_with_bracket_filter(self, test_queries):
        """Result filter combined with bracket filter."""
        result = test_queries._get_filtered_match_ids(
            bracket="Winners",  # rounds 1, 2 -> matches 1, 2, 3
            result_filter="winners"
        )
        result_set = set(result)

        # Winners bracket has matches 1, 2, 3
        # Winners in those: (1, 1), (2, 4), (3, 5)
        assert len(result_set) == 3
        assert (1, 1) in result_set
        assert (2, 4) in result_set
        assert (3, 5) in result_set

    def test_losers_with_round_filter(self, test_queries):
        """Result filter combined with round filter."""
        result = test_queries._get_filtered_match_ids(
            tournament_round=[1],  # matches 1, 2
            result_filter="losers"
        )
        result_set = set(result)

        # Round 1 has matches 1, 2
        # Losers in those: (1, 2), (2, 3)
        assert len(result_set) == 2
        assert (1, 2) in result_set
        assert (2, 3) in result_set


class TestGetWinnerPlayerIds:
    """Tests for the _get_winner_player_ids helper method."""

    def test_returns_set_of_tuples(self, test_queries):
        """Helper returns set of (match_id, player_id) tuples."""
        result = test_queries._get_winner_player_ids()
        assert isinstance(result, set)
        assert all(isinstance(x, tuple) and len(x) == 2 for x in result)

    def test_returns_all_winners(self, test_queries):
        """Returns all winners when no match_ids filter."""
        result = test_queries._get_winner_player_ids()
        assert result == {(1, 1), (2, 4), (3, 5)}

    def test_filters_by_match_ids(self, test_queries):
        """Filters to specific matches when match_ids provided."""
        result = test_queries._get_winner_player_ids(match_ids=[1, 2])
        assert result == {(1, 1), (2, 4)}

    def test_empty_result_for_match_without_winner(self, test_queries):
        """Returns empty set for match with no winner data."""
        result = test_queries._get_winner_player_ids(match_ids=[4])
        assert result == set()
