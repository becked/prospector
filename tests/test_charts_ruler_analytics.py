"""Tests for ruler analytics chart functions."""

import pandas as pd
import plotly.graph_objects as go
import pytest

from tournament_visualizer.components.charts import (
    create_ruler_archetype_trait_combinations_chart,
    create_ruler_archetype_win_rates_chart,
    create_ruler_succession_impact_chart,
    create_ruler_trait_win_rates_chart,
)


class TestRulerArchetypeWinRatesChart:
    """Tests for create_ruler_archetype_win_rates_chart."""

    def test_empty_dataframe(self) -> None:
        """Should handle empty DataFrame gracefully."""
        df = pd.DataFrame(columns=["archetype", "games", "wins", "win_rate"])
        fig = create_ruler_archetype_win_rates_chart(df)

        assert isinstance(fig, go.Figure)
        assert "No ruler data available" in str(fig.to_dict())

    def test_valid_data(self) -> None:
        """Should create dual-axis chart with valid data."""
        df = pd.DataFrame(
            {
                "archetype": ["Schemer", "Builder", "Tactician"],
                "games": [10, 8, 6],
                "wins": [6, 5, 2],
                "win_rate": [60.0, 62.5, 33.33],
            }
        )

        fig = create_ruler_archetype_win_rates_chart(df)

        assert isinstance(fig, go.Figure)
        # Should have 2 traces: bars and line
        assert len(fig.data) == 2
        # First trace should be bars (games played)
        assert isinstance(fig.data[0], go.Bar)
        # Second trace should be scatter (win rate)
        assert isinstance(fig.data[1], go.Scatter)

    def test_sorting_by_win_rate(self) -> None:
        """Should sort archetypes by win rate."""
        df = pd.DataFrame(
            {
                "archetype": ["Scholar", "Zealot", "Builder"],
                "games": [5, 3, 8],
                "wins": [2, 3, 5],
                "win_rate": [40.0, 100.0, 62.5],
            }
        )

        fig = create_ruler_archetype_win_rates_chart(df)

        # Check that data is sorted (lowest win rate first for horizontal display)
        y_values = fig.data[0].y
        assert y_values[0] == "Scholar"  # 40% win rate
        assert y_values[-1] == "Zealot"  # 100% win rate


class TestRulerSuccessionImpactChart:
    """Tests for create_ruler_succession_impact_chart."""

    def test_empty_dataframe(self) -> None:
        """Should handle empty DataFrame gracefully."""
        df = pd.DataFrame(
            columns=["succession_category", "games", "wins", "win_rate"]
        )
        fig = create_ruler_succession_impact_chart(df)

        assert isinstance(fig, go.Figure)
        assert "No ruler data available" in str(fig.to_dict())

    def test_valid_data(self) -> None:
        """Should create line chart with valid data."""
        df = pd.DataFrame(
            {
                "succession_category": [
                    "1 ruler",
                    "2 rulers",
                    "3 rulers",
                    "4+ rulers",
                ],
                "games": [6, 13, 8, 3],
                "wins": [2, 10, 1, 2],
                "win_rate": [33.33, 76.92, 12.5, 66.67],
            }
        )

        fig = create_ruler_succession_impact_chart(df)

        assert isinstance(fig, go.Figure)
        # Should have 1 trace: line with markers
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Scatter)
        assert fig.data[0].mode == "lines+markers"

    def test_category_ordering(self) -> None:
        """Should maintain proper category ordering."""
        df = pd.DataFrame(
            {
                "succession_category": ["3 rulers", "1 ruler", "4+ rulers", "2 rulers"],
                "games": [8, 6, 3, 13],
                "wins": [1, 2, 2, 10],
                "win_rate": [12.5, 33.33, 66.67, 76.92],
            }
        )

        fig = create_ruler_succession_impact_chart(df)

        # Check that x-axis maintains proper order
        x_values = list(fig.data[0].x)
        assert x_values == ["1 ruler", "2 rulers", "3 rulers", "4+ rulers"]

    def test_y_axis_range(self) -> None:
        """Should set y-axis range to 0-100."""
        df = pd.DataFrame(
            {
                "succession_category": ["1 ruler"],
                "games": [10],
                "wins": [3],
                "win_rate": [30.0],
            }
        )

        fig = create_ruler_succession_impact_chart(df)

        # Check that y-axis has correct range
        assert fig.layout.yaxis["range"] == (0, 100)


class TestRulerTraitWinRatesChart:
    """Tests for create_ruler_trait_win_rates_chart."""

    def test_empty_dataframe(self) -> None:
        """Should handle empty DataFrame gracefully."""
        df = pd.DataFrame(columns=["starting_trait", "games", "wins", "win_rate"])
        fig = create_ruler_trait_win_rates_chart(df)

        assert isinstance(fig, go.Figure)
        assert "No ruler data available" in str(fig.to_dict())

    def test_valid_data(self) -> None:
        """Should create horizontal bar chart with valid data."""
        df = pd.DataFrame(
            {
                "starting_trait": ["Intelligent", "Educated", "Affable"],
                "games": [10, 4, 3],
                "wins": [5, 2, 1],
                "win_rate": [50.0, 50.0, 33.33],
            }
        )

        fig = create_ruler_trait_win_rates_chart(df)

        assert isinstance(fig, go.Figure)
        # Should have 1 trace: horizontal bars
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Bar)
        assert fig.data[0].orientation == "h"

    def test_top_n_limiting(self) -> None:
        """Should limit to top N traits."""
        df = pd.DataFrame(
            {
                "starting_trait": [f"Trait{i}" for i in range(20)],
                "games": [10] * 20,
                "wins": [5] * 20,
                "win_rate": [50.0] * 20,
            }
        )

        fig = create_ruler_trait_win_rates_chart(df, top_n=5)

        # Should only show top 5
        assert len(fig.data[0].y) == 5

    def test_color_gradient(self) -> None:
        """Should apply color gradient based on win rate."""
        df = pd.DataFrame(
            {
                "starting_trait": ["High", "Low"],
                "games": [10, 10],
                "wins": [9, 1],
                "win_rate": [90.0, 10.0],
            }
        )

        fig = create_ruler_trait_win_rates_chart(df)

        # Both bars should have color, but different
        colors = fig.data[0].marker.color
        assert len(colors) == 2
        assert colors[0] != colors[1]


class TestRulerArchetypeTraitCombinationsChart:
    """Tests for create_ruler_archetype_trait_combinations_chart."""

    def test_empty_dataframe(self) -> None:
        """Should handle empty DataFrame gracefully."""
        df = pd.DataFrame(columns=["archetype", "starting_trait", "count"])
        fig = create_ruler_archetype_trait_combinations_chart(df)

        assert isinstance(fig, go.Figure)
        assert "No ruler data available" in str(fig.to_dict())

    def test_valid_data(self) -> None:
        """Should create horizontal bar chart with combinations."""
        df = pd.DataFrame(
            {
                "archetype": ["Builder", "Schemer", "Schemer"],
                "starting_trait": ["Intelligent", "Intelligent", "Educated"],
                "count": [4, 3, 3],
            }
        )

        fig = create_ruler_archetype_trait_combinations_chart(df)

        assert isinstance(fig, go.Figure)
        # Should have 1 trace: horizontal bars
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Bar)
        assert fig.data[0].orientation == "h"

    def test_combination_labels(self) -> None:
        """Should create combined labels."""
        df = pd.DataFrame(
            {
                "archetype": ["Builder", "Schemer"],
                "starting_trait": ["Intelligent", "Educated"],
                "count": [4, 3],
            }
        )

        fig = create_ruler_archetype_trait_combinations_chart(df)

        y_values = list(fig.data[0].y)
        assert "Builder + Intelligent" in y_values
        assert "Schemer + Educated" in y_values

    def test_sorting_by_count(self) -> None:
        """Should sort by count ascending."""
        df = pd.DataFrame(
            {
                "archetype": ["A", "B", "C"],
                "starting_trait": ["X", "Y", "Z"],
                "count": [10, 5, 20],
            }
        )

        fig = create_ruler_archetype_trait_combinations_chart(df)

        # Should be sorted ascending (lowest first for horizontal bars)
        x_values = list(fig.data[0].x)
        assert x_values[0] == 5  # B+Y
        assert x_values[-1] == 20  # C+Z

    def test_archetype_coloring(self) -> None:
        """Should color by archetype."""
        df = pd.DataFrame(
            {
                "archetype": ["Scholar", "Tactician"],
                "starting_trait": ["Intelligent", "Brave"],
                "count": [3, 4],
            }
        )

        fig = create_ruler_archetype_trait_combinations_chart(df)

        # Should have colors assigned
        colors = fig.data[0].marker.color
        assert len(colors) == 2
        # Different archetypes should have different colors
        assert colors[0] != colors[1]


class TestIntegrationScenarios:
    """Integration tests for typical usage scenarios."""

    def test_realistic_archetype_data(self) -> None:
        """Should handle realistic archetype distribution."""
        df = pd.DataFrame(
            {
                "archetype": [
                    "Zealot",
                    "Builder",
                    "Schemer",
                    "Scholar",
                    "Tactician",
                    "Judge",
                ],
                "games": [2, 8, 9, 2, 6, 1],
                "wins": [2, 5, 5, 1, 1, 0],
                "win_rate": [100.0, 62.5, 55.56, 50.0, 16.67, 0.0],
            }
        )

        fig = create_ruler_archetype_win_rates_chart(df)

        assert isinstance(fig, go.Figure)
        # Should handle varying win rates gracefully
        assert len(fig.data[0].x) == 6  # All 6 archetypes shown

    def test_realistic_succession_data(self) -> None:
        """Should handle realistic succession distribution."""
        df = pd.DataFrame(
            {
                "succession_category": [
                    "1 ruler",
                    "2 rulers",
                    "3 rulers",
                    "4+ rulers",
                ],
                "games": [6, 13, 8, 3],
                "wins": [2, 10, 1, 2],
                "win_rate": [33.33, 76.92, 12.5, 66.67],
            }
        )

        fig = create_ruler_succession_impact_chart(df)

        assert isinstance(fig, go.Figure)
        # Should show the peak at 2 rulers clearly
        win_rates = list(fig.data[0].y)
        assert win_rates[1] == 76.92  # 2 rulers has highest win rate

    def test_realistic_trait_data_with_ties(self) -> None:
        """Should handle traits with identical win rates."""
        df = pd.DataFrame(
            {
                "starting_trait": ["Intelligent", "Educated", "Steadfast"],
                "games": [10, 4, 2],
                "wins": [5, 2, 1],
                "win_rate": [50.0, 50.0, 50.0],
            }
        )

        fig = create_ruler_trait_win_rates_chart(df)

        assert isinstance(fig, go.Figure)
        # Should handle tie-breaking gracefully
        assert len(fig.data[0].y) == 3

    def test_realistic_combinations_data(self) -> None:
        """Should handle realistic combination data."""
        df = pd.DataFrame(
            {
                "archetype": [
                    "Builder",
                    "Schemer",
                    "Schemer",
                    "Builder",
                    "Tactician",
                ],
                "starting_trait": [
                    "Intelligent",
                    "Intelligent",
                    "Educated",
                    "Gay",
                    "Intelligent",
                ],
                "count": [4, 3, 3, 2, 2],
            }
        )

        fig = create_ruler_archetype_trait_combinations_chart(df)

        assert isinstance(fig, go.Figure)
        # Should show all 5 combinations
        assert len(fig.data[0].y) == 5
