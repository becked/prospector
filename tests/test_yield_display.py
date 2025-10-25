"""Tests for yield value display scale (divide by 10 for display)."""

import pytest
from tournament_visualizer.data.queries import get_queries


class TestYieldDisplayScale:
    """Test that yield values are correctly scaled for display."""

    @pytest.fixture
    def queries(self):
        """Get queries instance."""
        return get_queries()

    def test_yield_values_are_divided_by_10(self, queries):
        """Yield query should return display-ready values (raw / 10).

        Old World stores yields in 0.1 units (21.5 stored as 215).
        The query must divide by 10 to return display-ready values.

        Example: If XML has <YIELD_SCIENCE>215</YIELD_SCIENCE>,
        database stores 215, and query should return 21.5.
        """
        # Get science yield data for match 1
        df = queries.get_yield_history_by_match(
            match_id=1,
            yield_types=["YIELD_SCIENCE"]
        )

        # Should have data
        assert len(df) > 0, "No yield data found for match 1"

        # Values should be in reasonable display range (10-100)
        # NOT in raw range (100-1000)
        avg_value = df["amount"].mean()
        max_value = df["amount"].max()

        # Early game science is typically 10-50, not 100-500
        assert avg_value < 100, (
            f"Average science {avg_value:.1f} suggests raw values "
            f"(expected <100 for display values)"
        )
        assert max_value < 200, (
            f"Max science {max_value:.1f} suggests raw values "
            f"(expected <200 for display values)"
        )

    def test_yield_values_have_decimal_precision(self, queries):
        """Yield values should support one decimal place.

        The division by 10.0 (float) should preserve decimal precision.
        For example: 215 / 10.0 = 21.5 (not 21).
        """
        df = queries.get_yield_history_by_match(
            match_id=1,
            yield_types=["YIELD_SCIENCE"]
        )

        # Check if any values have decimal places
        # (not all will, but many should: 21.5, 23.4, etc.)
        has_decimals = any(df["amount"] % 1 != 0)
        assert has_decimals, (
            "No decimal values found - suggests integer division was used "
            "instead of float division (use / 10.0 not / 10)"
        )

    def test_all_yield_types_are_scaled(self, queries):
        """All 14 yield types should be scaled correctly.

        This ensures we didn't miss any yield type in the query.
        """
        # Get all yield types for match 1
        df = queries.get_yield_history_by_match(match_id=1)

        # Should have data for multiple yield types
        yield_types = df["resource_type"].unique()
        assert len(yield_types) > 5, "Expected data for multiple yield types"

        # All values should be in display range
        for yield_type in yield_types:
            yield_data = df[df["resource_type"] == yield_type]
            max_value = yield_data["amount"].max()

            # Most yields stay under 200 (except maybe late-game money)
            # But raw values would be 2000+
            assert max_value < 500, (
                f"{yield_type} max value {max_value:.1f} suggests raw values "
                f"(expected <500 for display values)"
            )

    def test_database_still_has_raw_values(self):
        """Database should still contain raw values (we transform in query).

        This verifies our design decision: we divide in the query,
        not during parsing/import.
        """
        import duckdb

        # Query database directly (bypass our query layer)
        conn = duckdb.connect("data/tournament_data.duckdb", read_only=True)
        result = conn.execute("""
            SELECT amount
            FROM player_yield_history
            WHERE resource_type = 'YIELD_SCIENCE'
              AND match_id = 1
              AND player_id = 1
            LIMIT 1
        """).fetchone()
        conn.close()

        raw_value = result[0]

        # Database should have raw values (100-1000), not display values (10-100)
        assert raw_value > 100, (
            f"Database value {raw_value} is too low - expected raw values "
            f"(100-1000 range), not display values (10-100 range)"
        )
