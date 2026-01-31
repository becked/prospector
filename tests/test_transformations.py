"""Tests for data transformation utilities."""

import pandas as pd
import pytest

from tournament_visualizer.data.transformations import (
    forward_fill_history,
    forward_fill_history_by_category,
    is_sparse_history,
)


class TestForwardFillHistory:
    """Tests for forward_fill_history function."""

    def test_empty_dataframe(self) -> None:
        """Empty DataFrame returns empty DataFrame."""
        df = pd.DataFrame(columns=["turn_number", "player_id", "military_power"])
        result = forward_fill_history(df, value_cols=["military_power"])
        assert result.empty

    def test_complete_data_unchanged(self) -> None:
        """Complete data (no gaps) passes through with same values."""
        df = pd.DataFrame(
            {
                "turn_number": [1, 2, 3, 1, 2, 3],
                "player_id": [1, 1, 1, 2, 2, 2],
                "military_power": [100, 110, 120, 200, 210, 220],
            }
        )
        result = forward_fill_history(df, value_cols=["military_power"])

        # Should have same number of rows
        assert len(result) == 6

        # Values should match
        p1_data = result[result["player_id"] == 1].sort_values("turn_number")
        assert p1_data["military_power"].tolist() == [100, 110, 120]

    def test_sparse_data_fills_gaps(self) -> None:
        """Sparse data gets gaps filled with last known value."""
        df = pd.DataFrame(
            {
                "turn_number": [1, 5, 10],
                "player_id": [1, 1, 1],
                "military_power": [100, 150, 200],
            }
        )
        result = forward_fill_history(df, value_cols=["military_power"])

        # Should have turns 1-10
        assert len(result) == 10
        assert result["turn_number"].tolist() == list(range(1, 11))

        # Check forward-fill values
        expected = [100, 100, 100, 100, 150, 150, 150, 150, 150, 200]
        assert result["military_power"].tolist() == expected

    def test_multiple_players_independent_fill(self) -> None:
        """Each player is forward-filled independently."""
        df = pd.DataFrame(
            {
                "turn_number": [1, 5, 2, 4],
                "player_id": [1, 1, 2, 2],
                "military_power": [100, 200, 50, 100],
            }
        )
        result = forward_fill_history(df, value_cols=["military_power"])

        # Both players should have turns 1-5
        p1 = result[result["player_id"] == 1].sort_values("turn_number")
        p2 = result[result["player_id"] == 2].sort_values("turn_number")

        assert len(p1) == 5
        assert len(p2) == 5

        # Player 1: 100 at t1, fill to t4, then 200 at t5
        assert p1["military_power"].tolist() == [100, 100, 100, 100, 200]

        # Player 2: 0 at t1 (no data), 50 at t2, fill to t3, 100 at t4, fill to t5
        assert p2["military_power"].tolist() == [0, 50, 50, 100, 100]

    def test_custom_turn_range(self) -> None:
        """Custom min/max turn range is respected."""
        df = pd.DataFrame(
            {
                "turn_number": [5, 10],
                "player_id": [1, 1],
                "military_power": [100, 200],
            }
        )
        result = forward_fill_history(
            df, value_cols=["military_power"], min_turn=1, max_turn=15
        )

        # Should have turns 1-15
        assert len(result) == 15
        assert result["turn_number"].min() == 1
        assert result["turn_number"].max() == 15

        # Turns 1-4 should be 0 (before first data), 5-9 should be 100, 10-15 should be 200
        values = result.sort_values("turn_number")["military_power"].tolist()
        assert values[:4] == [0, 0, 0, 0]  # Before first data
        assert values[4:9] == [100, 100, 100, 100, 100]  # t5-t9
        assert values[9:] == [200, 200, 200, 200, 200, 200]  # t10-t15

    def test_preserves_additional_columns(self) -> None:
        """Preserved columns are forward-filled along with values."""
        df = pd.DataFrame(
            {
                "turn_number": [1, 5],
                "player_id": [1, 1],
                "player_name": ["Alice", "Alice"],
                "civilization": ["Rome", "Rome"],
                "military_power": [100, 200],
            }
        )
        result = forward_fill_history(
            df,
            value_cols=["military_power"],
            preserve_columns=["player_name", "civilization"],
        )

        assert len(result) == 5
        assert all(result["player_name"] == "Alice")
        assert all(result["civilization"] == "Rome")

    def test_single_turn(self) -> None:
        """Single turn data returns single row."""
        df = pd.DataFrame(
            {
                "turn_number": [5],
                "player_id": [1],
                "military_power": [100],
            }
        )
        result = forward_fill_history(df, value_cols=["military_power"])

        assert len(result) == 1
        assert result["turn_number"].iloc[0] == 5
        assert result["military_power"].iloc[0] == 100


class TestForwardFillHistoryByCategory:
    """Tests for forward_fill_history_by_category function."""

    def test_empty_dataframe(self) -> None:
        """Empty DataFrame returns empty DataFrame."""
        df = pd.DataFrame(
            columns=["turn_number", "player_id", "resource_type", "amount"]
        )
        result = forward_fill_history_by_category(df)
        assert result.empty

    def test_single_category_fills(self) -> None:
        """Single category with gaps gets filled."""
        df = pd.DataFrame(
            {
                "turn_number": [1, 5],
                "player_id": [1, 1],
                "resource_type": ["YIELD_SCIENCE", "YIELD_SCIENCE"],
                "amount": [10.0, 15.0],
            }
        )
        result = forward_fill_history_by_category(df)

        assert len(result) == 5
        expected = [10.0, 10.0, 10.0, 10.0, 15.0]
        assert result.sort_values("turn_number")["amount"].tolist() == expected

    def test_multiple_categories_independent(self) -> None:
        """Each category is filled independently."""
        df = pd.DataFrame(
            {
                "turn_number": [1, 5, 2, 4],
                "player_id": [1, 1, 1, 1],
                "resource_type": [
                    "YIELD_SCIENCE",
                    "YIELD_SCIENCE",
                    "YIELD_TRAINING",
                    "YIELD_TRAINING",
                ],
                "amount": [10.0, 20.0, 100.0, 150.0],
            }
        )
        result = forward_fill_history_by_category(df)

        # Should have 5 turns x 2 categories = 10 rows
        assert len(result) == 10

        science = result[result["resource_type"] == "YIELD_SCIENCE"].sort_values(
            "turn_number"
        )
        training = result[result["resource_type"] == "YIELD_TRAINING"].sort_values(
            "turn_number"
        )

        # Science: 10 at t1, fill to t4, 20 at t5
        assert science["amount"].tolist() == [10.0, 10.0, 10.0, 10.0, 20.0]

        # Training: 0 at t1, 100 at t2, fill to t3, 150 at t4, fill to t5
        assert training["amount"].tolist() == [0.0, 100.0, 100.0, 150.0, 150.0]

    def test_multiple_players_multiple_categories(self) -> None:
        """Multiple players with multiple categories all fill correctly."""
        df = pd.DataFrame(
            {
                "turn_number": [1, 3, 1, 3],
                "player_id": [1, 1, 2, 2],
                "resource_type": [
                    "YIELD_SCIENCE",
                    "YIELD_SCIENCE",
                    "YIELD_SCIENCE",
                    "YIELD_SCIENCE",
                ],
                "amount": [10.0, 30.0, 20.0, 40.0],
            }
        )
        result = forward_fill_history_by_category(df)

        # 2 players x 3 turns x 1 category = 6 rows
        assert len(result) == 6

        p1 = result[result["player_id"] == 1].sort_values("turn_number")
        p2 = result[result["player_id"] == 2].sort_values("turn_number")

        assert p1["amount"].tolist() == [10.0, 10.0, 30.0]
        assert p2["amount"].tolist() == [20.0, 20.0, 40.0]

    def test_preserves_player_columns(self) -> None:
        """Player-level columns are preserved."""
        df = pd.DataFrame(
            {
                "turn_number": [1, 3],
                "player_id": [1, 1],
                "player_name": ["Alice", "Alice"],
                "resource_type": ["YIELD_SCIENCE", "YIELD_SCIENCE"],
                "amount": [10.0, 30.0],
            }
        )
        result = forward_fill_history_by_category(
            df, preserve_columns=["player_name"]
        )

        assert len(result) == 3
        assert all(result["player_name"] == "Alice")


class TestIsSparseHistory:
    """Tests for is_sparse_history function."""

    def test_empty_dataframe(self) -> None:
        """Empty DataFrame returns False."""
        df = pd.DataFrame(columns=["turn_number", "player_id"])
        assert is_sparse_history(df) is False

    def test_complete_data_not_sparse(self) -> None:
        """Complete data (100% density) is not sparse."""
        df = pd.DataFrame(
            {
                "turn_number": [1, 2, 3, 1, 2, 3],
                "player_id": [1, 1, 1, 2, 2, 2],
            }
        )
        # 100% density should not be sparse at 90% threshold
        assert is_sparse_history(df, threshold=0.9) is False

    def test_sparse_data_detected(self) -> None:
        """Sparse data (below threshold) is detected."""
        df = pd.DataFrame(
            {
                "turn_number": [1, 5, 10],
                "player_id": [1, 1, 1],
            }
        )
        # 3 rows out of 10 expected = 30% density
        assert is_sparse_history(df, threshold=0.5) is True
        assert is_sparse_history(df, threshold=0.9) is True

    def test_threshold_boundary(self) -> None:
        """Threshold boundary is respected."""
        df = pd.DataFrame(
            {
                "turn_number": [1, 2, 3, 4, 5],
                "player_id": [1, 1, 1, 1, 1],
            }
        )
        # 5 rows out of 5 expected = 100% density
        assert is_sparse_history(df, threshold=0.99) is False
        assert is_sparse_history(df, threshold=1.0) is False

        # Remove turn 3: 4/5 = 80% density (turns 1,2,4,5 but range is 1-5)
        df_sparse = pd.DataFrame(
            {
                "turn_number": [1, 2, 4, 5],
                "player_id": [1, 1, 1, 1],
            }
        )
        assert is_sparse_history(df_sparse, threshold=0.9) is True
        assert is_sparse_history(df_sparse, threshold=0.7) is False
