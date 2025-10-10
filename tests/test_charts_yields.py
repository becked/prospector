"""Tests for yield chart functions."""

import pandas as pd
import pytest
from plotly import graph_objects as go

from tournament_visualizer.components.charts import (
    create_food_yields_chart,
    create_yield_chart,
)


@pytest.fixture
def sample_yield_data() -> pd.DataFrame:
    """Sample yield data for testing (Food yields for 2 players)."""
    return pd.DataFrame(
        {
            "player_id": [1, 1, 1, 2, 2, 2],
            "player_name": ["Alice", "Alice", "Alice", "Bob", "Bob", "Bob"],
            "turn_number": [10, 20, 30, 10, 20, 30],
            "resource_type": [
                "YIELD_FOOD",
                "YIELD_FOOD",
                "YIELD_FOOD",
                "YIELD_FOOD",
                "YIELD_FOOD",
                "YIELD_FOOD",
            ],
            "amount": [50, 75, 100, 40, 70, 95],
        }
    )


@pytest.fixture
def empty_yield_data() -> pd.DataFrame:
    """Empty DataFrame with correct yield schema."""
    return pd.DataFrame(
        columns=[
            "player_id",
            "player_name",
            "turn_number",
            "resource_type",
            "amount",
        ]
    )


@pytest.fixture
def multi_yield_data() -> pd.DataFrame:
    """Sample data with multiple yield types."""
    return pd.DataFrame(
        {
            "player_id": [1, 1, 1, 1, 2, 2, 2, 2],
            "player_name": [
                "Alice",
                "Alice",
                "Alice",
                "Alice",
                "Bob",
                "Bob",
                "Bob",
                "Bob",
            ],
            "turn_number": [10, 20, 10, 20, 10, 20, 10, 20],
            "resource_type": [
                "YIELD_FOOD",
                "YIELD_FOOD",
                "YIELD_SCIENCE",
                "YIELD_SCIENCE",
                "YIELD_FOOD",
                "YIELD_FOOD",
                "YIELD_SCIENCE",
                "YIELD_SCIENCE",
            ],
            "amount": [50, 75, 30, 45, 40, 70, 25, 40],
        }
    )


class TestGenericYieldChart:
    """Tests for create_yield_chart() - the generic yield chart function."""

    def test_returns_figure(self, sample_yield_data: pd.DataFrame) -> None:
        """Should return a Plotly Figure object."""
        fig = create_yield_chart(sample_yield_data)
        assert isinstance(fig, go.Figure)

    def test_uses_line_chart(self, sample_yield_data: pd.DataFrame) -> None:
        """Should use line chart (Scatter with lines)."""
        fig = create_yield_chart(sample_yield_data)

        if len(fig.data) > 0:
            # Should be Scatter traces
            assert isinstance(fig.data[0], go.Scatter)
            # Should have mode including "lines"
            assert "lines" in fig.data[0].mode

    def test_has_trace_per_player(self, sample_yield_data: pd.DataFrame) -> None:
        """Should have one line per player."""
        fig = create_yield_chart(sample_yield_data)

        # Should have 2 traces (one per player in fixture)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        assert len(scatter_traces) == 2

    def test_empty_data_returns_placeholder(self, empty_yield_data: pd.DataFrame) -> None:
        """Should handle empty data gracefully."""
        fig = create_yield_chart(empty_yield_data)

        assert isinstance(fig, go.Figure)
        # Placeholder charts have no data traces
        assert len(fig.data) == 0

    def test_chart_has_title(self, sample_yield_data: pd.DataFrame) -> None:
        """Chart should have a descriptive title."""
        fig = create_yield_chart(sample_yield_data)
        assert fig.layout.title.text is not None

    def test_chart_has_axis_labels(self, sample_yield_data: pd.DataFrame) -> None:
        """Chart should have labeled axes."""
        fig = create_yield_chart(sample_yield_data)
        assert fig.layout.xaxis.title.text is not None
        assert fig.layout.yaxis.title.text is not None

    def test_accepts_yield_type_parameter(self, sample_yield_data: pd.DataFrame) -> None:
        """Should accept yield_type parameter."""
        fig = create_yield_chart(sample_yield_data, yield_type="YIELD_FOOD")
        assert isinstance(fig, go.Figure)

    def test_accepts_display_name_parameter(
        self, sample_yield_data: pd.DataFrame
    ) -> None:
        """Should accept display_name parameter and use it in y-axis label."""
        fig = create_yield_chart(
            sample_yield_data, yield_type="YIELD_FOOD", display_name="Food"
        )
        assert isinstance(fig, go.Figure)
        # Display name should be in y-axis label
        assert "Food" in fig.layout.yaxis.title.text

    def test_derives_display_name_from_yield_type(
        self, sample_yield_data: pd.DataFrame
    ) -> None:
        """Should derive display name from yield_type if not provided."""
        fig = create_yield_chart(sample_yield_data, yield_type="YIELD_SCIENCE")
        assert isinstance(fig, go.Figure)
        # Should contain "Science" (derived from YIELD_SCIENCE) in y-axis label
        assert "Science" in fig.layout.yaxis.title.text

    def test_handles_total_turns_parameter(
        self, sample_yield_data: pd.DataFrame
    ) -> None:
        """Should accept total_turns parameter to extend lines."""
        # Should not crash when total_turns is provided
        fig = create_yield_chart(sample_yield_data, total_turns=50)
        assert isinstance(fig, go.Figure)

    def test_works_with_all_yield_types(self, multi_yield_data: pd.DataFrame) -> None:
        """Should work with any yield type from Old World."""
        yield_types = [
            "YIELD_FOOD",
            "YIELD_GROWTH",
            "YIELD_SCIENCE",
            "YIELD_CULTURE",
            "YIELD_CIVICS",
            "YIELD_TRAINING",
            "YIELD_MONEY",
            "YIELD_ORDERS",
            "YIELD_HAPPINESS",
            "YIELD_DISCONTENT",
            "YIELD_IRON",
            "YIELD_STONE",
            "YIELD_WOOD",
            "YIELD_MAINTENANCE",
        ]

        # Test a few representative ones
        for yield_type in ["YIELD_FOOD", "YIELD_SCIENCE", "YIELD_CULTURE"]:
            df_filtered = multi_yield_data[
                multi_yield_data["resource_type"] == yield_type
            ]
            fig = create_yield_chart(df_filtered, yield_type=yield_type)
            assert isinstance(fig, go.Figure)


class TestFoodYieldsChart:
    """Tests for create_food_yields_chart() - backward compatibility wrapper."""

    def test_returns_figure(self, sample_yield_data: pd.DataFrame) -> None:
        """Should return a Plotly Figure object."""
        fig = create_food_yields_chart(sample_yield_data)
        assert isinstance(fig, go.Figure)

    def test_delegates_to_generic_function(
        self, sample_yield_data: pd.DataFrame
    ) -> None:
        """Should produce same result as calling generic function directly."""
        fig_old = create_food_yields_chart(sample_yield_data)
        fig_new = create_yield_chart(
            sample_yield_data, yield_type="YIELD_FOOD", display_name="Food"
        )

        # Both should be valid figures
        assert isinstance(fig_old, go.Figure)
        assert isinstance(fig_new, go.Figure)

        # Should have same number of traces
        assert len(fig_old.data) == len(fig_new.data)

    def test_accepts_total_turns_parameter(
        self, sample_yield_data: pd.DataFrame
    ) -> None:
        """Should still accept total_turns parameter."""
        fig = create_food_yields_chart(sample_yield_data, total_turns=50)
        assert isinstance(fig, go.Figure)

    def test_empty_data_returns_placeholder(self, empty_yield_data: pd.DataFrame) -> None:
        """Should handle empty data gracefully."""
        fig = create_food_yields_chart(empty_yield_data)

        assert isinstance(fig, go.Figure)
        # Placeholder charts have no data traces
        assert len(fig.data) == 0


class TestYieldChartDataHandling:
    """Tests for edge cases and data validation."""

    def test_handles_single_player(self) -> None:
        """Should work with just one player."""
        df = pd.DataFrame(
            {
                "player_id": [1, 1, 1],
                "player_name": ["Alice", "Alice", "Alice"],
                "turn_number": [10, 20, 30],
                "resource_type": ["YIELD_FOOD", "YIELD_FOOD", "YIELD_FOOD"],
                "amount": [50, 75, 100],
            }
        )

        fig = create_yield_chart(df)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1  # One player = one trace

    def test_handles_many_players(self) -> None:
        """Should work with many players."""
        players = []
        for i in range(1, 11):  # 10 players
            for turn in [10, 20, 30]:
                players.append(
                    {
                        "player_id": i,
                        "player_name": f"Player{i}",
                        "turn_number": turn,
                        "resource_type": "YIELD_FOOD",
                        "amount": 50 + i * 5,
                    }
                )

        df = pd.DataFrame(players)
        fig = create_yield_chart(df)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 10  # Ten players = ten traces

    def test_handles_sparse_data(self) -> None:
        """Should handle players with different numbers of data points."""
        df = pd.DataFrame(
            {
                "player_id": [1, 1, 1, 2],  # Alice has 3 points, Bob has 1
                "player_name": ["Alice", "Alice", "Alice", "Bob"],
                "turn_number": [10, 20, 30, 15],
                "resource_type": ["YIELD_FOOD", "YIELD_FOOD", "YIELD_FOOD", "YIELD_FOOD"],
                "amount": [50, 75, 100, 60],
            }
        )

        fig = create_yield_chart(df)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2  # Should still create both traces

    def test_handles_zero_yields(self) -> None:
        """Should handle zero yield amounts."""
        df = pd.DataFrame(
            {
                "player_id": [1, 1, 1],
                "player_name": ["Alice", "Alice", "Alice"],
                "turn_number": [10, 20, 30],
                "resource_type": ["YIELD_FOOD", "YIELD_FOOD", "YIELD_FOOD"],
                "amount": [0, 0, 0],
            }
        )

        fig = create_yield_chart(df)
        assert isinstance(fig, go.Figure)
        # Should not crash on zero values

    def test_handles_negative_yields(self) -> None:
        """Should handle negative yield amounts (like YIELD_MAINTENANCE)."""
        df = pd.DataFrame(
            {
                "player_id": [1, 1, 1],
                "player_name": ["Alice", "Alice", "Alice"],
                "turn_number": [10, 20, 30],
                "resource_type": [
                    "YIELD_MAINTENANCE",
                    "YIELD_MAINTENANCE",
                    "YIELD_MAINTENANCE",
                ],
                "amount": [-10, -15, -20],
            }
        )

        fig = create_yield_chart(df, yield_type="YIELD_MAINTENANCE")
        assert isinstance(fig, go.Figure)
        # Should not crash on negative values
