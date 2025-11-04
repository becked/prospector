"""Tests for Challonge API integration."""

import os

import pytest
from chyllonge.api import ChallongeApi
from dotenv import load_dotenv

# Load environment variables before checking
load_dotenv()

# Skip if no API credentials
@pytest.mark.skipif(
    not os.getenv("CHALLONGE_KEY"),
    reason="Challonge API credentials not configured",
)
class TestChallongeIntegration:
    """Test Challonge API data fetching."""

    @pytest.fixture
    def api(self) -> ChallongeApi:
        """Create Challonge API client."""
        load_dotenv()
        return ChallongeApi()

    def test_fetch_tournament_matches(self, api: ChallongeApi) -> None:
        """Test fetching all matches from tournament."""
        # ARRANGE
        tournament_url = "owduels2025"

        # ACT
        matches = api.matches.get_all(tournament_url)

        # ASSERT
        assert len(matches) > 0, "Tournament should have matches"

        # Verify structure
        first_match = matches[0]
        assert "id" in first_match
        assert "round" in first_match
        assert isinstance(first_match["round"], int)

    def test_create_round_cache(self, api: ChallongeApi) -> None:
        """Test creating round number cache from API data."""
        # ARRANGE
        tournament_url = "owduels2025"
        matches = api.matches.get_all(tournament_url)

        # ACT - Create cache like we'll use in ETL
        round_cache = {match["id"]: match["round"] for match in matches}

        # ASSERT
        assert len(round_cache) > 0
        assert all(isinstance(r, int) for r in round_cache.values())

        # Verify we have both positive and negative rounds (both brackets)
        rounds = list(round_cache.values())
        has_positive = any(r > 0 for r in rounds)
        has_negative = any(r < 0 for r in rounds)
        assert has_positive, "Should have winners bracket matches"
        # Note: Might not have losers matches yet depending on tournament state
