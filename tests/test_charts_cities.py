"""Tests for city analytics chart functions.

Test Strategy:
- Test chart creation with valid data
- Test empty data handling
- Verify chart structure (no internal titles, proper traces)
- Follow UI conventions from codebase
"""

import pandas as pd
import plotly.graph_objects as go
import pytest

from tournament_visualizer.components.charts import (
    create_tournament_expansion_timeline_chart,
    create_tournament_founding_distribution_chart,
    create_tournament_production_strategies_chart,
    create_tournament_project_priorities_chart,
    create_tournament_conquest_summary_chart,
)


class TestCityAnalyticsCharts:
    """Test chart creation functions for city analytics."""

    def test_create_tournament_expansion_timeline_chart_with_data(self):
        """Test expansion timeline chart with valid data."""
        # Arrange
        df = pd.DataFrame(
            {
                "player_name": ["Alice", "Alice", "Bob", "Bob"],
                "civilization": ["Rome", "Rome", "Carthage", "Carthage"],
                "founded_turn": [1, 10, 5, 15],
                "cities_this_turn": [1, 1, 1, 1],
                "cumulative_cities": [1, 2, 1, 2],
            }
        )

        # Act
        fig = create_tournament_expansion_timeline_chart(df)

        # Assert
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2  # Two players = two traces
        assert fig.layout.showlegend is True
        assert fig.layout.title.text == ""  # CRITICAL: No internal title
        assert fig.layout.xaxis.title.text == "Turn"
        assert fig.layout.yaxis.title.text == "Cumulative Cities"

    def test_create_tournament_expansion_timeline_chart_empty(self):
        """Test expansion timeline chart with empty DataFrame."""
        # Arrange
        df = pd.DataFrame()

        # Act
        fig = create_tournament_expansion_timeline_chart(df)

        # Assert
        assert isinstance(fig, go.Figure)
        # Should have empty state message
        assert len(fig.layout.annotations) > 0
        assert "No expansion data available" in fig.layout.annotations[0].text

    def test_create_tournament_founding_distribution_chart_with_data(self):
        """Test founding distribution chart with valid data."""
        # Arrange
        df = pd.DataFrame(
            {
                "turn_range": ["1-20", "21-40", "41-60"],
                "city_count": [10, 5, 2],
                "percentage": [58.8, 29.4, 11.8],
            }
        )

        # Act
        fig = create_tournament_founding_distribution_chart(df)

        # Assert
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1  # Single bar chart trace
        assert fig.layout.showlegend is False
        assert fig.layout.title.text == ""  # No internal title
        assert fig.layout.xaxis.title.text == "Turn Range"
        assert fig.layout.yaxis.title.text == "Cities Founded"

    def test_create_tournament_founding_distribution_chart_empty(self):
        """Test founding distribution chart with empty DataFrame."""
        # Arrange
        df = pd.DataFrame()

        # Act
        fig = create_tournament_founding_distribution_chart(df)

        # Assert
        assert isinstance(fig, go.Figure)
        assert len(fig.layout.annotations) > 0
        assert "No city founding data available" in fig.layout.annotations[0].text

    def test_create_tournament_production_strategies_chart_with_data(self):
        """Test production strategies chart with valid data."""
        # Arrange
        df = pd.DataFrame(
            {
                "player_name": ["Alice", "Bob"],
                "civilization": ["Rome", "Carthage"],
                "settlers": [5, 2],
                "workers": [8, 4],
                "disciples": [0, 3],
                "total_units": [13, 9],
            }
        )

        # Act
        fig = create_tournament_production_strategies_chart(df)

        # Assert
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 3  # Settlers, workers, disciples
        assert fig.layout.showlegend is True
        assert fig.layout.title.text == ""
        assert fig.layout.xaxis.title.text == "Player"
        assert fig.layout.yaxis.title.text == "Units Produced"
        assert fig.layout.barmode == "stack"

    def test_create_tournament_production_strategies_chart_empty(self):
        """Test production strategies chart with empty DataFrame."""
        # Arrange
        df = pd.DataFrame()

        # Act
        fig = create_tournament_production_strategies_chart(df)

        # Assert
        assert isinstance(fig, go.Figure)
        assert len(fig.layout.annotations) > 0
        assert "No production data available" in fig.layout.annotations[0].text

    def test_create_tournament_project_priorities_chart_with_data(self):
        """Test project priorities chart with valid data."""
        # Arrange
        df = pd.DataFrame(
            {
                "player_name": ["Alice", "Alice", "Bob", "Bob"],
                "civilization": ["Rome", "Rome", "Carthage", "Carthage"],
                "project_type": [
                    "PROJECT_FORUM_1",
                    "PROJECT_FESTIVAL",
                    "PROJECT_TREASURY_1",
                    "PROJECT_WALLS",
                ],
                "project_count": [2, 3, 1, 1],
            }
        )

        # Act
        fig = create_tournament_project_priorities_chart(df)

        # Assert
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0  # Should have traces for projects
        assert fig.layout.showlegend is True
        assert fig.layout.title.text == ""
        assert fig.layout.xaxis.title.text == "Player"
        assert fig.layout.yaxis.title.text == "Projects Completed"

    def test_create_tournament_project_priorities_chart_empty(self):
        """Test project priorities chart with empty DataFrame."""
        # Arrange
        df = pd.DataFrame()

        # Act
        fig = create_tournament_project_priorities_chart(df)

        # Assert
        assert isinstance(fig, go.Figure)
        assert len(fig.layout.annotations) > 0
        assert "No project data available" in fig.layout.annotations[0].text

    def test_create_tournament_conquest_summary_chart_with_data(self):
        """Test conquest summary chart with valid data."""
        # Arrange
        df = pd.DataFrame(
            {
                "city_name": ["CITYNAME_SYRACUSE"],
                "conqueror_name": ["Bob"],
                "conqueror_civ": ["Carthage"],
                "original_founder_name": ["Alice"],
                "original_founder_civ": ["Rome"],
                "founded_turn": [15],
                "match_id": [1],
            }
        )

        # Act
        fig = create_tournament_conquest_summary_chart(df)

        # Assert
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1  # Should be a table
        assert isinstance(fig.data[0], go.Table)
        assert fig.layout.title.text == ""

    def test_create_tournament_conquest_summary_chart_empty(self):
        """Test conquest summary chart with empty DataFrame."""
        # Arrange
        df = pd.DataFrame()

        # Act
        fig = create_tournament_conquest_summary_chart(df)

        # Assert
        assert isinstance(fig, go.Figure)
        assert len(fig.layout.annotations) > 0
        # Should have message about no conquests
        annotation_text = fig.layout.annotations[0].text
        assert "No conquests occurred" in annotation_text
