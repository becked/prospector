"""Tests for law progression chart functions."""

from typing import Any, Dict, List

import pandas as pd
import pytest
from plotly import graph_objects as go

from tournament_visualizer.components.charts import (
    create_empty_chart_placeholder,
    create_law_milestone_comparison_chart,
    # We'll add more imports as we create more charts
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
            "player_name": ["yagman", "Marauder", "fonder", "aran", "PBM", "MongrelEyes"],
            "civilization": ["Hittite", "Persia", "Assyria", "Assyria", "Greece", "Aksum"],
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

    def test_has_correct_number_of_traces(self, sample_match_data: pd.DataFrame) -> None:
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
        assert "milestone" in fig.layout.title.text.lower() or "law" in fig.layout.title.text.lower()

    def test_chart_has_axis_labels(self, sample_match_data: pd.DataFrame) -> None:
        """Chart should have labeled axes."""
        fig = create_law_milestone_comparison_chart(sample_match_data)
        assert fig.layout.xaxis.title.text is not None
        assert fig.layout.yaxis.title.text is not None
