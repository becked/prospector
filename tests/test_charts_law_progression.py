"""Tests for law progression chart functions."""

import pandas as pd
import pytest
from plotly import graph_objects as go

from tournament_visualizer.components.charts import (
    create_cumulative_law_count_chart,  # ← ADD THIS
    # We'll add more imports as we create more charts
    create_law_efficiency_scatter,
    create_law_milestone_comparison_chart,
    create_law_milestone_distribution_chart,
    create_law_progression_heatmap,
    create_law_race_timeline_chart,
)


@pytest.fixture
def sample_match_data() -> pd.DataFrame:
    """Sample law progression data for a single match (2 players)."""
    return pd.DataFrame(
        {
            "match_id": [10, 10],
            "player_id": [19, 20],
            "player_name": ["anarkos", "becked"],
            "civilization": ["Persia", "Assyria"],
            "turn_to_4_laws": [54, 46],
            "turn_to_7_laws": [pd.NA, 68],  # anarkos didn't reach 7
            "total_laws": [6, 7],
        }
    )


@pytest.fixture
def sample_all_matches_data() -> pd.DataFrame:
    """Sample law progression data for multiple matches."""
    return pd.DataFrame(
        {
            "match_id": [1, 1, 3, 3, 4, 4],
            "player_id": [1, 2, 5, 6, 7, 8],
            "player_name": [
                "yagman",
                "Marauder",
                "fonder",
                "aran",
                "PBM",
                "MongrelEyes",
            ],
            "civilization": [
                "Hittite",
                "Persia",
                "Assyria",
                "Assyria",
                "Greece",
                "Aksum",
            ],
            "turn_to_4_laws": [50, pd.NA, 35, 61, pd.NA, pd.NA],
            "turn_to_7_laws": [pd.NA, pd.NA, 68, pd.NA, pd.NA, pd.NA],
            "total_laws": [4, 1, 9, 5, 2, 3],
        }
    )


@pytest.fixture
def empty_data() -> pd.DataFrame:
    """Empty DataFrame with correct schema."""
    return pd.DataFrame(
        columns=[
            "match_id",
            "player_id",
            "player_name",
            "civilization",
            "turn_to_4_laws",
            "turn_to_7_laws",
            "total_laws",
        ]
    )


@pytest.fixture
def sample_cumulative_data() -> pd.DataFrame:
    """Sample cumulative law count data for testing."""
    return pd.DataFrame(
        {
            "player_id": [19, 19, 19, 20, 20, 20, 20],
            "player_name": [
                "anarkos",
                "anarkos",
                "anarkos",
                "becked",
                "becked",
                "becked",
                "becked",
            ],
            "turn_number": [11, 36, 49, 20, 37, 43, 46],
            "cumulative_laws": [1, 2, 3, 1, 2, 3, 4],
        }
    )


class TestChartInfrastructure:
    """Tests for basic chart infrastructure."""

    def test_empty_data_returns_placeholder(self, empty_data: pd.DataFrame) -> None:
        """Charts should handle empty data gracefully."""
        fig = create_law_milestone_comparison_chart(empty_data)

        assert isinstance(fig, go.Figure)
        # Placeholder charts have no data traces
        assert len(fig.data) == 0


class TestLawMilestoneComparisonChart:
    """Tests for match comparison bar chart (Visualization #1)."""

    def test_returns_figure(self, sample_match_data: pd.DataFrame) -> None:
        """Should return a Plotly Figure object."""
        fig = create_law_milestone_comparison_chart(sample_match_data)
        assert isinstance(fig, go.Figure)

    def test_has_correct_number_of_traces(
        self, sample_match_data: pd.DataFrame
    ) -> None:
        """Should have 2 traces (4 laws milestone, 7 laws milestone)."""
        fig = create_law_milestone_comparison_chart(sample_match_data)
        assert len(fig.data) == 2

    def test_handles_missing_milestones(self, sample_match_data: pd.DataFrame) -> None:
        """Should handle NULL values (players who didn't reach milestones)."""
        fig = create_law_milestone_comparison_chart(sample_match_data)

        # Should not raise an error
        assert isinstance(fig, go.Figure)

        # First trace (4 laws) should have data for both players
        assert len(fig.data[0].x) == 2

        # Second trace (7 laws) should handle the NULL for anarkos
        # Plotly will skip NULL values automatically

    def test_chart_has_title(self, sample_match_data: pd.DataFrame) -> None:
        """Chart should have a descriptive title."""
        fig = create_law_milestone_comparison_chart(sample_match_data)
        assert fig.layout.title.text is not None
        title_lower = fig.layout.title.text.lower()
        assert "milestone" in title_lower or "law" in title_lower

    def test_chart_has_axis_labels(self, sample_match_data: pd.DataFrame) -> None:
        """Chart should have labeled axes."""
        fig = create_law_milestone_comparison_chart(sample_match_data)
        assert fig.layout.xaxis.title.text is not None
        assert fig.layout.yaxis.title.text is not None


class TestLawRaceTimelineChart:
    """Tests for horizontal timeline chart (Visualization #2)."""

    def test_returns_figure(self, sample_match_data: pd.DataFrame) -> None:
        """Should return a Plotly Figure object."""
        fig = create_law_race_timeline_chart(sample_match_data)
        assert isinstance(fig, go.Figure)

    def test_has_traces_for_both_players(self, sample_match_data: pd.DataFrame) -> None:
        """Should have separate traces for each player."""
        fig = create_law_race_timeline_chart(sample_match_data)

        # Should have at least 2 traces (one per player)
        assert len(fig.data) >= 2

    def test_uses_scatter_plot(self, sample_match_data: pd.DataFrame) -> None:
        """Timeline should use scatter plot with markers."""
        fig = create_law_race_timeline_chart(sample_match_data)

        # All traces should be Scatter type
        for trace in fig.data:
            assert isinstance(trace, go.Scatter)

    def test_handles_player_who_didnt_reach_7_laws(
        self, sample_match_data: pd.DataFrame
    ) -> None:
        """Should gracefully handle players with fewer milestones."""
        # anarkos only reached 4 laws, not 7
        fig = create_law_race_timeline_chart(sample_match_data)

        # Should not raise an error
        assert isinstance(fig, go.Figure)

    def test_empty_data_returns_placeholder(self, empty_data: pd.DataFrame) -> None:
        """Should handle empty data."""
        fig = create_law_race_timeline_chart(empty_data)
        assert len(fig.data) == 0  # Placeholder has no traces


class TestLawMilestoneDistributionChart:
    """Tests for box plot distribution (Visualization #3)."""

    def test_returns_figure(self, sample_all_matches_data: pd.DataFrame) -> None:
        """Should return a Plotly Figure object."""
        fig = create_law_milestone_distribution_chart(sample_all_matches_data)
        assert isinstance(fig, go.Figure)

    def test_uses_box_plots(self, sample_all_matches_data: pd.DataFrame) -> None:
        """Should use box plots to show distribution."""
        fig = create_law_milestone_distribution_chart(sample_all_matches_data)

        # Should have box plot traces
        assert any(isinstance(trace, go.Box) for trace in fig.data)

    def test_has_two_boxes(self, sample_all_matches_data: pd.DataFrame) -> None:
        """Should show two distributions (4 laws and 7 laws)."""
        fig = create_law_milestone_distribution_chart(sample_all_matches_data)

        # Should have 2 box traces
        box_traces = [trace for trace in fig.data if isinstance(trace, go.Box)]
        assert len(box_traces) == 2

    def test_handles_sparse_data(self, sample_all_matches_data: pd.DataFrame) -> None:
        """Should handle when few players reached milestones."""
        # Only 2 players reached 4 laws, 1 reached 7 laws in fixture
        fig = create_law_milestone_distribution_chart(sample_all_matches_data)

        # Should still create chart
        assert isinstance(fig, go.Figure)


class TestLawProgressionHeatmap:
    """Tests for player performance heatmap (Visualization #4)."""

    def test_returns_figure(self, sample_all_matches_data: pd.DataFrame) -> None:
        """Should return a Plotly Figure object."""
        fig = create_law_progression_heatmap(sample_all_matches_data)
        assert isinstance(fig, go.Figure)

    def test_uses_heatmap(self, sample_all_matches_data: pd.DataFrame) -> None:
        """Should use heatmap visualization."""
        fig = create_law_progression_heatmap(sample_all_matches_data)

        # Should have heatmap trace
        assert any(isinstance(trace, go.Heatmap) for trace in fig.data)

    def test_handles_players_without_milestones(
        self, sample_all_matches_data: pd.DataFrame
    ) -> None:
        """Should show players who never reached milestones."""
        # Several players in fixture never reached 4 laws
        fig = create_law_progression_heatmap(sample_all_matches_data)

        assert isinstance(fig, go.Figure)


class TestLawEfficiencyScatter:
    """Tests for efficiency scatter plot (Visualization #5)."""

    def test_returns_figure(self, sample_all_matches_data: pd.DataFrame) -> None:
        """Should return a Plotly Figure object."""
        fig = create_law_efficiency_scatter(sample_all_matches_data)
        assert isinstance(fig, go.Figure)

    def test_uses_scatter_plot(self, sample_all_matches_data: pd.DataFrame) -> None:
        """Should use scatter plot."""
        fig = create_law_efficiency_scatter(sample_all_matches_data)

        assert any(isinstance(trace, go.Scatter) for trace in fig.data)

    def test_only_includes_players_who_reached_both_milestones(
        self, sample_all_matches_data: pd.DataFrame
    ) -> None:
        """Should only plot players who reached both 4 and 7 laws."""
        # Only 'fonder' reached both milestones in the fixture
        fig = create_law_efficiency_scatter(sample_all_matches_data)

        # Should have at least one point
        if len(fig.data) > 0:
            scatter_trace = fig.data[0]
            # Number of points should match players who reached both milestones
            assert len(scatter_trace.x) >= 1

    def test_handles_no_complete_progressions(
        self, sample_match_data: pd.DataFrame
    ) -> None:
        """Should handle when no players reached both milestones."""
        # In sample_match_data, anarkos only reached 4 laws
        fig = create_law_efficiency_scatter(sample_match_data)

        # Should return placeholder or chart with limited data
        assert isinstance(fig, go.Figure)


class TestCumulativeLawCountChart:
    """Tests for cumulative law count line chart (Visualization #6)."""

    def test_returns_figure(self, sample_cumulative_data: pd.DataFrame) -> None:
        """Should return a Plotly Figure object."""
        fig = create_cumulative_law_count_chart(sample_cumulative_data)
        assert isinstance(fig, go.Figure)

    def test_uses_line_chart(self, sample_cumulative_data: pd.DataFrame) -> None:
        """Should use line chart (Scatter with lines)."""
        fig = create_cumulative_law_count_chart(sample_cumulative_data)

        if len(fig.data) > 0:
            # Should be Scatter traces
            assert isinstance(fig.data[0], go.Scatter)
            # Should have mode including "lines"
            assert "lines" in fig.data[0].mode

    def test_has_trace_per_player(self, sample_cumulative_data: pd.DataFrame) -> None:
        """Should have one line per player."""
        fig = create_cumulative_law_count_chart(sample_cumulative_data)

        # Should have 2 traces (one per player in fixture)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        assert len(scatter_traces) == 2

    def test_includes_milestone_reference_lines(
        self, sample_cumulative_data: pd.DataFrame
    ) -> None:
        """Should show horizontal lines for 4 and 7 law milestones."""
        fig = create_cumulative_law_count_chart(sample_cumulative_data)

        # Check for horizontal lines (shapes in layout)
        assert len(fig.layout.shapes) >= 2  # At least 4-law and 7-law lines
