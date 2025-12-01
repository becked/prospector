"""Tests for tournament round filtering queries.

Test Strategy:
- Test filtering by specific round number
- Test filtering by bracket (Winners/Losers/Unknown)
- Test combining round and bracket filters
- Test empty result handling
"""

import pytest

from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.queries import TournamentQueries


class TestRoundFiltering:
    """Test tournament round filtering queries."""

    @pytest.fixture
    def test_db_with_rounds(self, tmp_path):
        """Create database with round data."""
        db_path = tmp_path / "round_test.duckdb"

        # Create database with schema
        db = TournamentDatabase(str(db_path), read_only=False)
        db.create_schema()

        with db.get_connection() as conn:
            # Insert test matches with various rounds
            conn.execute("""
                INSERT INTO matches (
                    match_id, file_name, file_hash, game_name,
                    tournament_round, total_turns, challonge_match_id
                ) VALUES
                    (1, 'match1.zip', 'hash1', 'Game 1', 1, 50, 1001),      -- Winners R1
                    (2, 'match2.zip', 'hash2', 'Game 2', 1, 60, 1002),      -- Winners R1
                    (3, 'match3.zip', 'hash3', 'Game 3', 2, 70, 1003),      -- Winners R2
                    (4, 'match4.zip', 'hash4', 'Game 4', -1, 80, 1004),     -- Losers R1
                    (5, 'match5.zip', 'hash5', 'Game 5', -2, 90, 1005),     -- Losers R2
                    (6, 'match6.zip', 'hash6', 'Game 6', NULL, 100, NULL)   -- Unknown
            """)

        yield db
        db.close()

    def test_get_matches_by_round_specific(
        self, test_db_with_rounds: TournamentDatabase
    ) -> None:
        """Test filtering by specific round number."""
        # ARRANGE
        queries = TournamentQueries(test_db_with_rounds)

        # ACT
        result = queries.get_matches_by_round(tournament_round=[1])

        # ASSERT
        assert len(result) == 2, "Should return 2 matches from Winners Round 1"
        assert all(result["tournament_round"] == 1), "All rounds should be 1"
        assert all(result["bracket"] == "Winners"), "All should be Winners bracket"

    def test_get_matches_by_bracket_winners(
        self, test_db_with_rounds: TournamentDatabase
    ) -> None:
        """Test filtering by Winners bracket."""
        # ARRANGE
        queries = TournamentQueries(test_db_with_rounds)

        # ACT
        result = queries.get_matches_by_round(bracket="Winners")

        # ASSERT
        assert len(result) == 3, "Should return 3 Winners bracket matches"
        assert all(result["tournament_round"] > 0), "All rounds should be positive"
        assert all(result["bracket"] == "Winners"), "All should be Winners"

    def test_get_matches_by_bracket_losers(
        self, test_db_with_rounds: TournamentDatabase
    ) -> None:
        """Test filtering by Losers bracket."""
        # ARRANGE
        queries = TournamentQueries(test_db_with_rounds)

        # ACT
        result = queries.get_matches_by_round(bracket="Losers")

        # ASSERT
        assert len(result) == 2, "Should return 2 Losers bracket matches"
        assert all(result["tournament_round"] < 0), "All rounds should be negative"
        assert all(result["bracket"] == "Losers"), "All should be Losers"

    def test_get_matches_by_bracket_unknown(
        self, test_db_with_rounds: TournamentDatabase
    ) -> None:
        """Test filtering by Unknown bracket (NULL rounds)."""
        # ARRANGE
        queries = TournamentQueries(test_db_with_rounds)

        # ACT
        result = queries.get_matches_by_round(bracket="Unknown")

        # ASSERT
        assert len(result) == 1, "Should return 1 Unknown bracket match"
        assert result["tournament_round"].isna().all(), "Round should be NULL"
        assert all(result["bracket"] == "Unknown"), "All should be Unknown"

    def test_get_matches_all_no_filter(
        self, test_db_with_rounds: TournamentDatabase
    ) -> None:
        """Test getting all matches without filter."""
        # ARRANGE
        queries = TournamentQueries(test_db_with_rounds)

        # ACT
        result = queries.get_matches_by_round()

        # ASSERT
        assert len(result) == 6, "Should return all 6 matches"

    def test_get_matches_combine_round_and_bracket(
        self, test_db_with_rounds: TournamentDatabase
    ) -> None:
        """Test combining round and bracket filters."""
        # ARRANGE
        queries = TournamentQueries(test_db_with_rounds)

        # ACT
        result = queries.get_matches_by_round(tournament_round=[1], bracket="Winners")

        # ASSERT
        assert len(result) == 2, "Should return 2 Winners Round 1 matches"
        assert all(result["tournament_round"] == 1)
        assert all(result["bracket"] == "Winners")

    def test_get_available_rounds(
        self, test_db_with_rounds: TournamentDatabase
    ) -> None:
        """Test getting list of available rounds."""
        # ARRANGE
        queries = TournamentQueries(test_db_with_rounds)

        # ACT
        result = queries.get_available_rounds()

        # ASSERT
        assert len(result) == 5, "Should have 5 distinct round groups (NULL values group)"

        # Check specific rounds exist
        rounds = result["tournament_round"].dropna().tolist()
        assert 1 in rounds, "Should have Winners Round 1"
        assert 2 in rounds, "Should have Winners Round 2"
        assert -1 in rounds, "Should have Losers Round 1"
        assert -2 in rounds, "Should have Losers Round 2"

        # Check for Unknown bracket
        unknown_rows = result[result["bracket"] == "Unknown"]
        assert len(unknown_rows) == 1, "Should have 1 Unknown bracket row"

        # Check match counts
        round_1_count = result[result["tournament_round"] == 1]["match_count"].iloc[0]
        assert round_1_count == 2, "Winners Round 1 should have 2 matches"

    def test_empty_result_when_no_matches(
        self, test_db_with_rounds: TournamentDatabase
    ) -> None:
        """Test that empty DataFrame returned when no matches found."""
        # ARRANGE
        queries = TournamentQueries(test_db_with_rounds)

        # ACT
        result = queries.get_matches_by_round(tournament_round=[99])

        # ASSERT
        assert len(result) == 0, "Should return empty DataFrame"
        import pandas as pd

        assert isinstance(result, pd.DataFrame), "Should still be DataFrame"
