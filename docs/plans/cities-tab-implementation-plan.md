# Cities Tab Implementation Plan

## Overview

### Problem
We have rich city data (369 cities across 27 matches) stored in the database including:
- City founding information (name, turn, founder, population)
- Unit production per city (settlers, workers, disciples)
- City projects completed (forums, festivals, walls, etc.)

This data is not currently visualized in the dashboard. Players and analysts need insights into expansion strategies, production priorities, and city development patterns across the tournament.

### Solution
Add a new "Cities" tab to the Overview page showing tournament-wide patterns in city expansion, production, and development. This will help identify:
- Fast vs. slow expansion strategies
- Economic vs. military production focus
- Project priorities (infrastructure vs. wonders)
- Conquest patterns (rare but dramatic)

### Success Criteria
- New "Cities" tab appears on Overview page after "Economy" tab
- 5 charts displaying tournament-wide city analytics
- All charts handle empty data gracefully
- Charts follow UI conventions (no internal titles, proper error handling)
- Unit tests cover query functions and chart creation
- Changes documented and committed atomically

---

## Prerequisites

### Required Knowledge
- **Python 3.11+**: Modern Python with type hints (all functions MUST have type hints)
- **DuckDB**: Analytics database for SQL queries
- **Pandas**: DataFrames are the standard output from queries
- **Plotly**: All charts use `plotly.graph_objects` (imported as `go`)
- **Dash**: Web framework using Bootstrap components (`dash_bootstrap_components` as `dbc`)
- **pytest**: Testing framework with fixtures

### Required Tools
- **uv**: Python package manager (use `uv run` prefix for all commands)
- **git**: Version control (commit after each task)

### Codebase Navigation
Read these files to understand patterns:
1. **Architecture**: `CLAUDE.md` sections:
   - "Architecture Overview" (data/UI layers)
   - "UI Conventions" (CRITICAL - no chart titles!)
   - "City Data Analysis" (domain knowledge)
2. **Schema**: `docs/database-schema.md` (tables: `cities`, `city_unit_production`, `city_projects`)
3. **Example Page**: `tournament_visualizer/pages/overview.py` (tab structure, callbacks)
4. **Existing Queries**: `tournament_visualizer/data/queries.py` (lines 2693-2800 for city queries)
5. **Test Patterns**: `tests/test_queries_cities.py` (how to test city queries)

---

## Architecture Overview

### Data Flow
```
DuckDB (cities, city_unit_production, city_projects tables)
    ↓
tournament_visualizer/data/queries.py (TournamentQueries class)
    ↓ (returns pandas.DataFrame)
tournament_visualizer/components/charts.py (create_*_chart functions)
    ↓ (returns plotly.graph_objects.Figure)
tournament_visualizer/pages/overview.py (Dash callbacks)
    ↓
Browser (rendered chart in tab)
```

### Files to Modify
1. **Queries** (`tournament_visualizer/data/queries.py`)
   - Add 5 new query methods to `TournamentQueries` class
   - All return `pd.DataFrame`

2. **Charts** (`tournament_visualizer/components/charts.py`)
   - Add 5 new chart creation functions
   - All return `go.Figure`

3. **Page** (`tournament_visualizer/pages/overview.py`)
   - Add new tab after "Economy" tab
   - Add 5 chart callbacks

4. **Tests** (create new files)
   - `tests/test_queries_cities_analytics.py` - Query tests
   - `tests/test_charts_cities.py` - Chart tests

---

## Database Schema Reference

### Key Tables

**cities** (369 rows, 27 matches)
```sql
city_id INTEGER
match_id BIGINT (FK to matches)
player_id BIGINT (FK to players)
city_name VARCHAR (e.g., 'CITYNAME_ROMA')
tile_id INTEGER
founded_turn INTEGER (1-112)
family_name VARCHAR
is_capital BOOLEAN
population INTEGER (nullable)
first_player_id BIGINT (original founder, null if same as player_id)
governor_id INTEGER (nullable)
```

**city_unit_production** (500 rows)
```sql
production_id BIGINT (PK)
match_id BIGINT
city_id INTEGER
unit_type VARCHAR (e.g., 'UNIT_SETTLER', 'UNIT_WORKER')
count INTEGER (how many of this unit type)
```

**city_projects** (459 rows)
```sql
project_id BIGINT (PK)
match_id BIGINT
city_id INTEGER
project_type VARCHAR (e.g., 'PROJECT_FESTIVAL', 'PROJECT_FORUM_1')
count INTEGER (how many times completed)
```

### Key Insights from Data
- 369 cities across 27 matches (~13.7 per match avg)
- City founding spans turns 1-112
- Only 9 cities were conquered (`first_player_id != player_id`)
- Workers are most common unit (501 total)
- Festivals are most popular project (61 total)

---

## Implementation Tasks

### TASK 1: Write Query Tests (TDD First!)

**Goal**: Define expected behavior for 5 new tournament-wide city queries.

**File**: `tests/test_queries_cities_analytics.py`

**Why TDD?**: Writing tests first forces you to think about:
- What data do we need?
- What format should it be in?
- What edge cases exist?

**Test Structure Pattern** (from `tests/test_queries_cities.py`):
```python
import pytest
import pandas as pd
from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.queries import TournamentQueries

def test_query_name(test_db_with_city_data):
    """Test description."""
    # Arrange
    queries = TournamentQueries(test_db_with_city_data)

    # Act
    result = queries.get_something()

    # Assert
    assert isinstance(result, pd.DataFrame)
    assert not result.empty
    assert list(result.columns) == ['col1', 'col2', 'col3']
    # More specific assertions...
```

**Tests to Write**:

1. **test_get_tournament_expansion_timeline**
   - Should return: player_name, civilization, founded_turn, cumulative_cities
   - Should have cumulative count growing with each turn
   - Should handle multiple matches
   - Should order by player_name, founded_turn

2. **test_get_tournament_city_founding_distribution**
   - Should return: turn_range (e.g., '1-20'), city_count
   - Should group cities into turn buckets (1-20, 21-40, 41-60, 61-80, 81-100, 101+)
   - Should handle edge cases (cities at turn 1, turn 112)

3. **test_get_tournament_production_strategies**
   - Should return: player_name, civilization, settlers, workers, disciples, total_units
   - Should sum across all cities for each player
   - Should handle players with no production data (0 counts)

4. **test_get_tournament_project_priorities**
   - Should return: player_name, civilization, project_type, project_count
   - Should sum across all cities per player per project type
   - Should order by player_name, project_count DESC

5. **test_get_tournament_conquest_summary**
   - Should return: conqueror_name, conqueror_civ, original_founder_name, original_founder_civ, city_name, founded_turn
   - Should only include cities where first_player_id != player_id
   - Should return empty DataFrame if no conquests
   - Should join to players table twice (for both conqueror and founder names)

**How to Run Tests** (they will FAIL initially - that's expected!):
```bash
uv run pytest tests/test_queries_cities_analytics.py -v
```

**Commit**:
```bash
git add tests/test_queries_cities_analytics.py
git commit -m "test: Add failing tests for city analytics queries"
```

---

### TASK 2: Implement Query Functions

**Goal**: Make the tests pass by implementing the 5 query methods.

**File**: `tournament_visualizer/data/queries.py`

**Location**: Add after existing `get_production_summary()` method (around line 2795)

**Critical Patterns to Follow**:
1. All methods are in `TournamentQueries` class
2. All return `pd.DataFrame`
3. All use `with self.db.get_connection() as conn:` pattern
4. All queries use parameterized queries (even if no params)
5. Use `COALESCE()` for nullable fields
6. Add comprehensive docstrings with Args/Returns

**Implementation**:

```python
    def get_tournament_expansion_timeline(self) -> pd.DataFrame:
        """Get cumulative city count over time for all players across the tournament.

        Analyzes expansion strategies by showing how quickly players founded cities.
        Returns cumulative count at each city founding event.

        Returns:
            DataFrame with columns:
                - player_name: Player name
                - civilization: Player's civilization
                - founded_turn: Turn when city was founded
                - cumulative_cities: Total cities founded up to this turn
                - cities_this_turn: Cities founded on this specific turn
        """
        query = """
        WITH city_foundings AS (
            SELECT
                p.player_name,
                p.civilization,
                c.founded_turn,
                COUNT(*) as cities_this_turn
            FROM cities c
            JOIN players p ON c.match_id = p.match_id AND c.player_id = p.player_id
            GROUP BY p.player_name, p.civilization, c.founded_turn
        )
        SELECT
            player_name,
            civilization,
            founded_turn,
            cities_this_turn,
            SUM(cities_this_turn) OVER (
                PARTITION BY player_name, civilization
                ORDER BY founded_turn
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) as cumulative_cities
        FROM city_foundings
        ORDER BY player_name, civilization, founded_turn
        """

        with self.db.get_connection() as conn:
            return conn.execute(query).df()

    def get_tournament_city_founding_distribution(self) -> pd.DataFrame:
        """Get distribution of city foundings across turn ranges.

        Shows how many cities were founded in early game vs. mid game vs. late game.
        Useful for understanding tournament-wide expansion timing patterns.

        Returns:
            DataFrame with columns:
                - turn_range: Turn range bucket (e.g., '1-20', '21-40')
                - city_count: Number of cities founded in this range
                - percentage: Percentage of all cities founded in this range
        """
        query = """
        WITH turn_buckets AS (
            SELECT
                CASE
                    WHEN founded_turn <= 20 THEN '1-20'
                    WHEN founded_turn <= 40 THEN '21-40'
                    WHEN founded_turn <= 60 THEN '41-60'
                    WHEN founded_turn <= 80 THEN '61-80'
                    WHEN founded_turn <= 100 THEN '81-100'
                    ELSE '101+'
                END as turn_range,
                COUNT(*) as city_count
            FROM cities
            GROUP BY turn_range
        ),
        total AS (
            SELECT COUNT(*) as total_cities FROM cities
        )
        SELECT
            turn_range,
            city_count,
            ROUND(city_count * 100.0 / total_cities, 1) as percentage
        FROM turn_buckets, total
        ORDER BY
            CASE turn_range
                WHEN '1-20' THEN 1
                WHEN '21-40' THEN 2
                WHEN '41-60' THEN 3
                WHEN '61-80' THEN 4
                WHEN '81-100' THEN 5
                ELSE 6
            END
        """

        with self.db.get_connection() as conn:
            return conn.execute(query).df()

    def get_tournament_production_strategies(self) -> pd.DataFrame:
        """Get unit production strategies for all players across the tournament.

        Aggregates production from all cities for each player, showing whether
        they focused on economic units (settlers, workers) or military units.

        Returns:
            DataFrame with columns:
                - player_name: Player name
                - civilization: Player's civilization
                - settlers: Total settler units produced
                - workers: Total worker units produced
                - disciples: Total disciple units produced (all religions)
                - total_units: Total units produced
        """
        query = """
        SELECT
            p.player_name,
            p.civilization,
            COALESCE(SUM(CASE WHEN prod.unit_type = 'UNIT_SETTLER' THEN prod.count ELSE 0 END), 0) as settlers,
            COALESCE(SUM(CASE WHEN prod.unit_type = 'UNIT_WORKER' THEN prod.count ELSE 0 END), 0) as workers,
            COALESCE(SUM(CASE WHEN prod.unit_type LIKE '%_DISCIPLE' THEN prod.count ELSE 0 END), 0) as disciples,
            COALESCE(SUM(prod.count), 0) as total_units
        FROM players p
        LEFT JOIN cities c ON p.match_id = c.match_id AND p.player_id = c.player_id
        LEFT JOIN city_unit_production prod ON c.match_id = prod.match_id AND c.city_id = prod.city_id
        GROUP BY p.player_name, p.civilization
        HAVING COALESCE(SUM(prod.count), 0) > 0
        ORDER BY total_units DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query).df()

    def get_tournament_project_priorities(self) -> pd.DataFrame:
        """Get city project priorities for all players across the tournament.

        Shows which projects players prioritized (forums, treasuries, festivals, etc).

        Returns:
            DataFrame with columns:
                - player_name: Player name
                - civilization: Player's civilization
                - project_type: Project type (e.g., 'PROJECT_FESTIVAL')
                - project_count: Total times this project was completed
        """
        query = """
        SELECT
            p.player_name,
            p.civilization,
            proj.project_type,
            SUM(proj.count) as project_count
        FROM players p
        JOIN cities c ON p.match_id = c.match_id AND p.player_id = c.player_id
        JOIN city_projects proj ON c.match_id = proj.match_id AND c.city_id = proj.city_id
        GROUP BY p.player_name, p.civilization, proj.project_type
        ORDER BY p.player_name, project_count DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query).df()

    def get_tournament_conquest_summary(self) -> pd.DataFrame:
        """Get summary of all city conquests across the tournament.

        Identifies cities that changed ownership (first_player_id != player_id).
        This is rare but strategically significant.

        Returns:
            DataFrame with columns:
                - conqueror_name: Name of player who conquered the city
                - conqueror_civ: Civilization of conqueror
                - original_founder_name: Name of player who founded the city
                - original_founder_civ: Civilization of original founder
                - city_name: Name of conquered city
                - founded_turn: Turn when city was founded
                - match_id: Match where conquest occurred
        """
        query = """
        SELECT
            conqueror.player_name as conqueror_name,
            conqueror.civilization as conqueror_civ,
            founder.player_name as original_founder_name,
            founder.civilization as original_founder_civ,
            c.city_name,
            c.founded_turn,
            c.match_id
        FROM cities c
        JOIN players conqueror ON c.match_id = conqueror.match_id AND c.player_id = conqueror.player_id
        JOIN players founder ON c.match_id = founder.match_id AND c.first_player_id = founder.player_id
        WHERE c.first_player_id IS NOT NULL
          AND c.first_player_id != c.player_id
        ORDER BY c.match_id, c.founded_turn
        """

        with self.db.get_connection() as conn:
            return conn.execute(query).df()
```

**Testing**:
```bash
# Run tests - they should PASS now
uv run pytest tests/test_queries_cities_analytics.py -v

# Run with coverage
uv run pytest tests/test_queries_cities_analytics.py --cov=tournament_visualizer.data.queries -v
```

**Commit**:
```bash
git add tournament_visualizer/data/queries.py tests/test_queries_cities_analytics.py
git commit -m "feat: Add tournament-wide city analytics queries

- get_tournament_expansion_timeline: Cumulative city count over time
- get_tournament_city_founding_distribution: Turn range distribution
- get_tournament_production_strategies: Unit production patterns
- get_tournament_project_priorities: Project completion patterns
- get_tournament_conquest_summary: City conquest events

All queries return DataFrames with comprehensive player/civ context."
```

---

### TASK 3: Write Chart Tests (TDD for Charts)

**Goal**: Define expected behavior for 5 chart creation functions.

**File**: `tests/test_charts_cities.py`

**Chart Test Pattern** (from `tests/test_charts_yields.py`):
```python
import pandas as pd
import plotly.graph_objects as go
from tournament_visualizer.components.charts import create_some_chart

def test_chart_with_valid_data():
    """Test chart creation with valid data."""
    # Arrange
    df = pd.DataFrame({
        'column1': [1, 2, 3],
        'column2': ['a', 'b', 'c']
    })

    # Act
    fig = create_some_chart(df)

    # Assert
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0  # Has traces
    assert fig.layout.showlegend is True  # Or False, depending on chart
    assert fig.layout.title.text == ""  # CRITICAL: No internal title!

def test_chart_with_empty_data():
    """Test chart handles empty DataFrame gracefully."""
    # Arrange
    df = pd.DataFrame()

    # Act
    fig = create_some_chart(df)

    # Assert
    assert isinstance(fig, go.Figure)
    assert "No data available" in fig.layout.annotations[0].text
```

**Tests to Write**:

1. **test_create_tournament_expansion_timeline_chart**
   - Valid data: Should create line chart with one trace per player
   - Empty data: Should show empty state message
   - Check: No title, showlegend=True, x_title="Turn", y_title="Cumulative Cities"

2. **test_create_tournament_founding_distribution_chart**
   - Valid data: Should create bar chart with turn ranges
   - Empty data: Should show empty state
   - Check: No title, showlegend=False, x_title="Turn Range", y_title="Cities Founded"

3. **test_create_tournament_production_strategies_chart**
   - Valid data: Should create stacked bar chart (settlers, workers, disciples)
   - Empty data: Should show empty state
   - Check: No title, showlegend=True, x_title="Player", y_title="Units Produced"

4. **test_create_tournament_project_priorities_chart**
   - Valid data: Should create grouped bar chart or heatmap
   - Empty data: Should show empty state
   - Check: No title, showlegend depends on chart type

5. **test_create_tournament_conquest_summary_chart**
   - Valid data: Should create table or sankey diagram
   - Empty data: Should show "No conquests occurred" message
   - Check: Handles 0 conquests gracefully

**Run Tests** (will FAIL initially):
```bash
uv run pytest tests/test_charts_cities.py -v
```

**Commit**:
```bash
git add tests/test_charts_cities.py
git commit -m "test: Add failing tests for city analytics charts"
```

---

### TASK 4: Implement Chart Functions

**Goal**: Make chart tests pass by implementing 5 chart creation functions.

**File**: `tournament_visualizer/components/charts.py`

**Location**: Add at end of file (after line 4672)

**Critical Patterns**:
1. **NO internal titles**: `create_base_figure()` should have `title=""`
2. Use `create_base_figure()` for consistency
3. Handle empty DataFrames with `create_empty_chart_placeholder()`
4. Wrap in try/except for error handling
5. Use civilization colors where applicable (`get_nation_color()`)
6. Add comprehensive docstrings

**Implementation**:

```python
def create_tournament_expansion_timeline_chart(df: pd.DataFrame) -> go.Figure:
    """Create line chart showing cumulative city expansion over time for all players.

    Shows how quickly players expanded throughout the tournament. Each line represents
    one player's city count growth.

    Args:
        df: DataFrame from get_tournament_expansion_timeline() with columns:
            player_name, civilization, founded_turn, cumulative_cities

    Returns:
        Plotly figure with line chart (one trace per player)
    """
    if df.empty:
        return create_empty_chart_placeholder("No expansion data available")

    try:
        fig = create_base_figure(
            title="",  # Card header provides title
            show_legend=True,
            x_title="Turn",
            y_title="Cumulative Cities",
        )

        # Group by player and create one trace per player
        for (player_name, civ), group in df.groupby(['player_name', 'civilization']):
            # Sort by turn to ensure proper line drawing
            group = group.sort_values('founded_turn')

            # Get civilization color
            color = get_nation_color(civ)

            fig.add_trace(
                go.Scatter(
                    x=group['founded_turn'],
                    y=group['cumulative_cities'],
                    mode='lines+markers',
                    name=f"{player_name} ({civ})",
                    line=dict(color=color, width=2),
                    marker=dict(size=6, color=color),
                    hovertemplate=(
                        f"<b>{player_name}</b><br>"
                        "Turn: %{x}<br>"
                        "Total Cities: %{y}<br>"
                        "<extra></extra>"
                    ),
                )
            )

        # Update layout for better readability
        fig.update_layout(
            hovermode='closest',
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02
            )
        )

        return fig

    except Exception as e:
        logger.error(f"Error creating expansion timeline chart: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


def create_tournament_founding_distribution_chart(df: pd.DataFrame) -> go.Figure:
    """Create bar chart showing distribution of city foundings by turn range.

    Shows when most cities were founded (early, mid, or late game).

    Args:
        df: DataFrame from get_tournament_city_founding_distribution() with columns:
            turn_range, city_count, percentage

    Returns:
        Plotly figure with bar chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No city founding data available")

    try:
        fig = create_base_figure(
            title="",
            show_legend=False,
            x_title="Turn Range",
            y_title="Cities Founded",
        )

        fig.add_trace(
            go.Bar(
                x=df['turn_range'],
                y=df['city_count'],
                text=[f"{count}<br>({pct}%)" for count, pct in zip(df['city_count'], df['percentage'])],
                textposition='outside',
                marker_color=Config.PRIMARY_COLOR,
                hovertemplate=(
                    "Turn Range: %{x}<br>"
                    "Cities: %{y}<br>"
                    "Percentage: %{text}<br>"
                    "<extra></extra>"
                ),
            )
        )

        fig.update_layout(
            xaxis=dict(type='category'),  # Preserve order
            yaxis=dict(rangemode='tozero'),
        )

        return fig

    except Exception as e:
        logger.error(f"Error creating founding distribution chart: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


def create_tournament_production_strategies_chart(df: pd.DataFrame) -> go.Figure:
    """Create stacked bar chart showing unit production strategies.

    Compares how much each player focused on settlers vs workers vs disciples.

    Args:
        df: DataFrame from get_tournament_production_strategies() with columns:
            player_name, civilization, settlers, workers, disciples, total_units

    Returns:
        Plotly figure with stacked bar chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No production data available")

    try:
        fig = create_base_figure(
            title="",
            show_legend=True,
            x_title="Player",
            y_title="Units Produced",
        )

        # Create x-axis labels with civilization
        x_labels = [f"{row['player_name']}<br>({row['civilization']})"
                   for _, row in df.iterrows()]

        # Add traces for each unit type
        fig.add_trace(
            go.Bar(
                x=x_labels,
                y=df['settlers'],
                name='Settlers',
                marker_color='#FF6B6B',
                hovertemplate="Settlers: %{y}<extra></extra>",
            )
        )

        fig.add_trace(
            go.Bar(
                x=x_labels,
                y=df['workers'],
                name='Workers',
                marker_color='#4ECDC4',
                hovertemplate="Workers: %{y}<extra></extra>",
            )
        )

        fig.add_trace(
            go.Bar(
                x=x_labels,
                y=df['disciples'],
                name='Disciples',
                marker_color='#FFE66D',
                hovertemplate="Disciples: %{y}<extra></extra>",
            )
        )

        fig.update_layout(
            barmode='stack',
            xaxis=dict(tickangle=-45),
        )

        return fig

    except Exception as e:
        logger.error(f"Error creating production strategies chart: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


def create_tournament_project_priorities_chart(df: pd.DataFrame) -> go.Figure:
    """Create grouped bar chart showing city project priorities.

    Shows which projects players focused on (forums, festivals, etc).

    Args:
        df: DataFrame from get_tournament_project_priorities() with columns:
            player_name, civilization, project_type, project_count

    Returns:
        Plotly figure with grouped bar chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No project data available")

    try:
        # Get top 5 most common projects across all players
        top_projects = (
            df.groupby('project_type')['project_count']
            .sum()
            .nlargest(5)
            .index
            .tolist()
        )

        # Filter to only top projects
        df_filtered = df[df['project_type'].isin(top_projects)].copy()

        if df_filtered.empty:
            return create_empty_chart_placeholder("No project data available")

        fig = create_base_figure(
            title="",
            show_legend=True,
            x_title="Player",
            y_title="Projects Completed",
        )

        # Create x-axis labels
        players = df_filtered[['player_name', 'civilization']].drop_duplicates()
        x_labels = [f"{row['player_name']}<br>({row['civilization']})"
                   for _, row in players.iterrows()]

        # Add trace for each project type
        for project_type in top_projects:
            project_data = df_filtered[df_filtered['project_type'] == project_type]

            # Merge with all players to show 0 for players who didn't build this
            y_values = []
            for _, player in players.iterrows():
                player_project = project_data[
                    (project_data['player_name'] == player['player_name']) &
                    (project_data['civilization'] == player['civilization'])
                ]
                count = player_project['project_count'].iloc[0] if not player_project.empty else 0
                y_values.append(count)

            # Clean up project name for display
            display_name = project_type.replace('PROJECT_', '').replace('_', ' ').title()

            fig.add_trace(
                go.Bar(
                    x=x_labels,
                    y=y_values,
                    name=display_name,
                    hovertemplate=f"{display_name}: %{{y}}<extra></extra>",
                )
            )

        fig.update_layout(
            barmode='group',
            xaxis=dict(tickangle=-45),
        )

        return fig

    except Exception as e:
        logger.error(f"Error creating project priorities chart: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


def create_tournament_conquest_summary_chart(df: pd.DataFrame) -> go.Figure:
    """Create table showing city conquests.

    Displays rare but dramatic city conquest events.

    Args:
        df: DataFrame from get_tournament_conquest_summary() with columns:
            conqueror_name, conqueror_civ, original_founder_name,
            original_founder_civ, city_name, founded_turn, match_id

    Returns:
        Plotly figure with table
    """
    if df.empty:
        return create_empty_chart_placeholder(
            "No conquests occurred in the tournament.<br>"
            "All cities remained with their original founders!"
        )

    try:
        # Clean up city names
        df = df.copy()
        df['city_name'] = df['city_name'].str.replace('CITYNAME_', '')

        fig = go.Figure(data=[go.Table(
            header=dict(
                values=[
                    'City Conquered',
                    'Original Founder',
                    'Conquered By',
                    'Founded Turn',
                    'Match'
                ],
                fill_color=Config.PRIMARY_COLOR,
                font=dict(color='white', size=12),
                align='left',
            ),
            cells=dict(
                values=[
                    df['city_name'],
                    [f"{name} ({civ})" for name, civ in
                     zip(df['original_founder_name'], df['original_founder_civ'])],
                    [f"{name} ({civ})" for name, civ in
                     zip(df['conqueror_name'], df['conqueror_civ'])],
                    df['founded_turn'],
                    df['match_id'],
                ],
                fill_color='white',
                font=dict(size=11),
                align='left',
                height=30,
            )
        )])

        fig.update_layout(
            title="",
            height=max(200, len(df) * 35 + 50),  # Dynamic height based on rows
        )

        return fig

    except Exception as e:
        logger.error(f"Error creating conquest summary chart: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")
```

**Import Addition**: Add to imports at top of file:
```python
from ..config import Config  # If not already imported
import logging

logger = logging.getLogger(__name__)
```

**Testing**:
```bash
# Run chart tests
uv run pytest tests/test_charts_cities.py -v

# Run all city-related tests
uv run pytest tests/test_queries_cities_analytics.py tests/test_charts_cities.py -v
```

**Commit**:
```bash
git add tournament_visualizer/components/charts.py tests/test_charts_cities.py
git commit -m "feat: Add city analytics chart functions

- Expansion timeline (line chart)
- Founding distribution (bar chart)
- Production strategies (stacked bar)
- Project priorities (grouped bar)
- Conquest summary (table)

All charts follow UI conventions (no internal titles, empty state handling)."
```

---

### TASK 5: Add Cities Tab to Overview Page

**Goal**: Add new tab with 5 charts to the Overview page.

**File**: `tournament_visualizer/pages/overview.py`

**Step 5.1: Add Chart Function Imports**

Find the imports section (lines 14-35) and add new imports:

```python
from tournament_visualizer.components.charts import (
    # ... existing imports ...
    create_tournament_conquest_summary_chart,
    create_tournament_expansion_timeline_chart,
    create_tournament_founding_distribution_chart,
    create_tournament_production_strategies_chart,
    create_tournament_project_priorities_chart,
)
```

**Step 5.2: Add Cities Tab**

Find the closing of the "Economy" tab (around line 363) and add new tab BEFORE the closing `]`:

```python
                ),
                # Tab 5: Cities
                dbc.Tab(
                    label="Cities",
                    tab_id="cities-tab",
                    children=[
                        # Expansion Timeline - full width
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="City Expansion Timeline",
                                            chart_id="overview-expansion-timeline",
                                            height="500px",
                                        )
                                    ],
                                    width=12,
                                ),
                            ],
                            className="mb-4 mt-3",
                        ),
                        # Founding Distribution and Production Strategies
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="City Founding Distribution",
                                            chart_id="overview-founding-distribution",
                                            height="400px",
                                        )
                                    ],
                                    width=6,
                                ),
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Production Strategies",
                                            chart_id="overview-production-strategies",
                                            height="400px",
                                        )
                                    ],
                                    width=6,
                                ),
                            ],
                            className="mb-4",
                        ),
                        # Project Priorities and Conquest Summary
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="City Project Priorities",
                                            chart_id="overview-project-priorities",
                                            height="450px",
                                        )
                                    ],
                                    width=8,
                                ),
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="City Conquests",
                                            chart_id="overview-conquest-summary",
                                            height="450px",
                                        )
                                    ],
                                    width=4,
                                ),
                            ],
                            className="mb-4",
                        ),
                    ],
                ),
            ],
            id="overview-tabs",
            active_tab="summary-tab",
        ),
```

**Step 5.3: Add Chart Callbacks**

Add 5 new callbacks at the end of the file (after the last callback):

```python
# Cities Tab Callbacks


@callback(
    Output("overview-expansion-timeline", "figure"),
    Input("refresh-interval", "n_intervals"),
)
def update_expansion_timeline_chart(n_intervals: int) -> go.Figure:
    """Update the city expansion timeline chart.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with expansion timeline
    """
    try:
        queries = get_queries()
        df = queries.get_tournament_expansion_timeline()
        return create_tournament_expansion_timeline_chart(df)

    except Exception as e:
        logger.error(f"Error updating expansion timeline: {e}")
        return create_empty_chart_placeholder("Error loading expansion data")


@callback(
    Output("overview-founding-distribution", "figure"),
    Input("refresh-interval", "n_intervals"),
)
def update_founding_distribution_chart(n_intervals: int) -> go.Figure:
    """Update the city founding distribution chart.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with founding distribution
    """
    try:
        queries = get_queries()
        df = queries.get_tournament_city_founding_distribution()
        return create_tournament_founding_distribution_chart(df)

    except Exception as e:
        logger.error(f"Error updating founding distribution: {e}")
        return create_empty_chart_placeholder("Error loading founding data")


@callback(
    Output("overview-production-strategies", "figure"),
    Input("refresh-interval", "n_intervals"),
)
def update_production_strategies_chart(n_intervals: int) -> go.Figure:
    """Update the production strategies chart.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with production strategies
    """
    try:
        queries = get_queries()
        df = queries.get_tournament_production_strategies()
        return create_tournament_production_strategies_chart(df)

    except Exception as e:
        logger.error(f"Error updating production strategies: {e}")
        return create_empty_chart_placeholder("Error loading production data")


@callback(
    Output("overview-project-priorities", "figure"),
    Input("refresh-interval", "n_intervals"),
)
def update_project_priorities_chart(n_intervals: int) -> go.Figure:
    """Update the city project priorities chart.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with project priorities
    """
    try:
        queries = get_queries()
        df = queries.get_tournament_project_priorities()
        return create_tournament_project_priorities_chart(df)

    except Exception as e:
        logger.error(f"Error updating project priorities: {e}")
        return create_empty_chart_placeholder("Error loading project data")


@callback(
    Output("overview-conquest-summary", "figure"),
    Input("refresh-interval", "n_intervals"),
)
def update_conquest_summary_chart(n_intervals: int) -> go.Figure:
    """Update the city conquest summary chart.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with conquest summary
    """
    try:
        queries = get_queries()
        df = queries.get_tournament_conquest_summary()
        return create_tournament_conquest_summary_chart(df)

    except Exception as e:
        logger.error(f"Error updating conquest summary: {e}")
        return create_empty_chart_placeholder("Error loading conquest data")
```

**Testing the UI**:
```bash
# Start the dashboard
uv run python manage.py start

# Open browser to http://localhost:8050
# Click "Cities" tab
# Verify all 5 charts load
# Check for any console errors (F12 developer tools)

# Stop the dashboard
uv run python manage.py stop
```

**Manual Testing Checklist**:
- [ ] Cities tab appears after Economy tab
- [ ] Expansion timeline shows lines for all players
- [ ] Founding distribution shows bar chart with turn ranges
- [ ] Production strategies shows stacked bars
- [ ] Project priorities shows grouped bars (top 5 projects)
- [ ] Conquest summary shows table (or empty message if no conquests)
- [ ] No internal chart titles visible
- [ ] Hover tooltips work on all charts
- [ ] Charts resize properly when browser window changes
- [ ] No console errors in browser developer tools

**Commit**:
```bash
git add tournament_visualizer/pages/overview.py
git commit -m "feat: Add Cities tab to Overview page

- New tab with 5 charts showing tournament-wide city patterns
- Expansion timeline (line chart)
- Founding distribution (bar chart)
- Production strategies (stacked bar)
- Project priorities (grouped bar)
- Conquest summary (table)

Callbacks follow standard pattern with error handling."
```

---

### TASK 6: Integration Testing

**Goal**: Verify the entire feature works end-to-end.

**Manual Testing**:
1. Start fresh terminal session
2. Navigate to project directory
3. Run full test suite:
   ```bash
   uv run pytest -v
   ```
4. Start dashboard:
   ```bash
   uv run python manage.py restart
   ```
5. Open http://localhost:8050
6. Click through all tabs
7. Verify Cities tab loads correctly
8. Check browser console for errors (F12)
9. Test edge cases:
   - Refresh page
   - Switch between tabs multiple times
   - Resize browser window

**Automated Integration Test** (optional, advanced):

Create `tests/test_integration_cities_page.py`:

```python
"""Integration tests for Cities tab on Overview page."""

import pytest
from dash.testing.application_runners import import_app


def test_cities_tab_loads(dash_duo):
    """Test that Cities tab loads without errors."""
    # Import and start app
    app = import_app("app")
    dash_duo.start_server(app)

    # Wait for app to load
    dash_duo.wait_for_page(timeout=10)

    # Click Cities tab
    cities_tab = dash_duo.find_element("#cities-tab")
    cities_tab.click()

    # Wait for charts to load
    dash_duo.wait_for_element("#overview-expansion-timeline", timeout=10)
    dash_duo.wait_for_element("#overview-founding-distribution", timeout=10)
    dash_duo.wait_for_element("#overview-production-strategies", timeout=10)
    dash_duo.wait_for_element("#overview-project-priorities", timeout=10)
    dash_duo.wait_for_element("#overview-conquest-summary", timeout=10)

    # Verify no errors in browser console
    assert dash_duo.get_logs() == [], "Browser console has errors"
```

Run integration test:
```bash
uv run pytest tests/test_integration_cities_page.py -v
```

**Expected Results**:
- All tests pass
- Dashboard loads without errors
- Charts display data
- No console errors
- Responsive design works

**If Tests Fail**:
1. Read error messages carefully
2. Check imports are correct
3. Verify function signatures match
4. Check for typos in chart IDs
5. Ensure database has city data (run `uv run python scripts/validate_city_data.py`)

**Commit**:
```bash
# Only if you added integration test
git add tests/test_integration_cities_page.py
git commit -m "test: Add integration test for Cities tab"
```

---

### TASK 7: Code Quality & Documentation

**Goal**: Ensure code quality and update documentation.

**Step 7.1: Run Linter**
```bash
# Check for issues
uv run ruff check tournament_visualizer/ tests/

# Auto-fix simple issues
uv run ruff check --fix tournament_visualizer/ tests/
```

**Step 7.2: Format Code**
```bash
uv run black tournament_visualizer/ tests/
```

**Step 7.3: Run Full Test Suite**
```bash
# All tests
uv run pytest -v

# With coverage
uv run pytest --cov=tournament_visualizer --cov-report=html
```

**Step 7.4: Update CHANGELOG** (if exists)

Add to `CHANGELOG.md`:
```markdown
## [Unreleased]

### Added
- Cities tab on Overview page showing tournament-wide city analytics
  - Expansion timeline chart (cumulative city growth)
  - City founding distribution by turn ranges
  - Unit production strategies comparison
  - City project priorities analysis
  - City conquest summary table
- Five new query methods in `TournamentQueries`:
  - `get_tournament_expansion_timeline()`
  - `get_tournament_city_founding_distribution()`
  - `get_tournament_production_strategies()`
  - `get_tournament_project_priorities()`
  - `get_tournament_conquest_summary()`
- Five new chart functions in `charts.py`:
  - `create_tournament_expansion_timeline_chart()`
  - `create_tournament_founding_distribution_chart()`
  - `create_tournament_production_strategies_chart()`
  - `create_tournament_project_priorities_chart()`
  - `create_tournament_conquest_summary_chart()`
```

**Step 7.5: Update CLAUDE.md** (optional)

If you want to document the new queries for future reference, add to the "Querying City Data" section in `CLAUDE.md`:

```markdown
### Tournament-Wide Analytics

```python
# Expansion timeline
timeline_df = queries.get_tournament_expansion_timeline()
# Returns: player_name, civilization, founded_turn, cumulative_cities

# Founding distribution
distribution_df = queries.get_tournament_city_founding_distribution()
# Returns: turn_range, city_count, percentage

# Production strategies
production_df = queries.get_tournament_production_strategies()
# Returns: player_name, civilization, settlers, workers, disciples, total_units

# Project priorities
projects_df = queries.get_tournament_project_priorities()
# Returns: player_name, civilization, project_type, project_count

# Conquests
conquests_df = queries.get_tournament_conquest_summary()
# Returns: conqueror_name, conqueror_civ, original_founder_name,
#          original_founder_civ, city_name, founded_turn, match_id
```
```

**Commit**:
```bash
git add .
git commit -m "chore: Code quality improvements and documentation

- Run ruff linter and fix issues
- Format code with black
- Update CHANGELOG with new features
- Document new query methods in CLAUDE.md"
```

---

## Testing Guide

### Types of Tests

1. **Unit Tests** (Query Functions)
   - Test SQL logic
   - Test data transformations
   - Test edge cases (empty results, NULL values)

2. **Unit Tests** (Chart Functions)
   - Test chart creation with valid data
   - Test empty data handling
   - Test error handling

3. **Integration Tests** (optional)
   - Test page loads
   - Test tab switching
   - Test chart rendering

### Running Tests

```bash
# Single test file
uv run pytest tests/test_queries_cities_analytics.py -v

# Single test function
uv run pytest tests/test_queries_cities_analytics.py::test_get_tournament_expansion_timeline -v

# All city-related tests
uv run pytest -k "cities" -v

# With coverage
uv run pytest --cov=tournament_visualizer.data.queries --cov=tournament_visualizer.components.charts -v

# Generate HTML coverage report
uv run pytest --cov=tournament_visualizer --cov-report=html
# Open htmlcov/index.html in browser
```

### Test Design Best Practices

1. **Follow AAA Pattern**: Arrange, Act, Assert
2. **Use Descriptive Names**: `test_expansion_timeline_with_multiple_players`
3. **Test One Thing**: Each test should verify one behavior
4. **Use Fixtures**: Reuse test data setup
5. **Test Edge Cases**: Empty data, NULL values, single row, large datasets
6. **Check Types**: Use `isinstance()` to verify return types
7. **Check Structure**: Verify DataFrame columns, Figure traces

### Example Test Patterns

**Good Test**:
```python
def test_get_tournament_expansion_timeline_cumulative_count():
    """Cumulative cities should increase monotonically for each player."""
    queries = TournamentQueries(test_db_with_city_data)

    df = queries.get_tournament_expansion_timeline()

    for (player, civ), group in df.groupby(['player_name', 'civilization']):
        cumulative = group.sort_values('founded_turn')['cumulative_cities'].tolist()
        assert all(cumulative[i] <= cumulative[i+1] for i in range(len(cumulative)-1)), \
            f"{player}'s cumulative cities should never decrease"
```

**Bad Test** (too broad):
```python
def test_expansion_timeline():
    """Test expansion timeline."""
    df = queries.get_tournament_expansion_timeline()
    assert not df.empty
```

---

## Troubleshooting

### Common Issues

**Issue**: Tests fail with "table not found: cities"
**Solution**:
```bash
# Re-run migration
uv run python scripts/run_migration.py 003_add_city_tables

# Or re-import data
uv run python scripts/import_attachments.py --directory saves --force
```

**Issue**: Charts show "No data available"
**Solution**:
```bash
# Verify data exists
uv run duckdb data/tournament_data.duckdb -readonly -c "SELECT COUNT(*) FROM cities"

# Check validation
uv run python scripts/validate_city_data.py
```

**Issue**: Import error: "cannot import name 'create_tournament_expansion_timeline_chart'"
**Solution**: Check spelling and ensure you added the function to `tournament_visualizer/components/charts.py`

**Issue**: Dashboard shows blank page
**Solution**:
```bash
# Check logs
uv run python manage.py logs

# Restart dashboard
uv run python manage.py restart

# Check browser console (F12)
```

**Issue**: Linter errors after implementation
**Solution**:
```bash
# Auto-fix
uv run ruff check --fix tournament_visualizer/

# Format
uv run black tournament_visualizer/
```

**Issue**: Type hint errors
**Solution**: Ensure all functions have type hints:
```python
def my_function(param: str) -> pd.DataFrame:
    """Docstring."""
    pass
```

---

## Verification Checklist

Before marking tasks complete, verify:

### Code Quality
- [ ] All functions have type hints
- [ ] All functions have docstrings (Args, Returns)
- [ ] No linter errors (`uv run ruff check`)
- [ ] Code is formatted (`uv run black`)
- [ ] No hardcoded values (use Config constants)
- [ ] Error handling in place (try/except)

### Testing
- [ ] All query tests pass
- [ ] All chart tests pass
- [ ] Coverage >80% for new code
- [ ] Manual testing completed (dashboard loads)
- [ ] No browser console errors

### Functionality
- [ ] Cities tab appears on Overview page
- [ ] All 5 charts display data
- [ ] Charts have NO internal titles
- [ ] Empty states show helpful messages
- [ ] Hover tooltips work
- [ ] Charts are responsive

### Documentation
- [ ] CHANGELOG updated (if exists)
- [ ] Git commits are atomic (one logical change per commit)
- [ ] Commit messages follow conventional format

---

## Commit History (Expected)

You should have approximately 5-7 commits:

1. `test: Add failing tests for city analytics queries`
2. `feat: Add tournament-wide city analytics queries`
3. `test: Add failing tests for city analytics charts`
4. `feat: Add city analytics chart functions`
5. `feat: Add Cities tab to Overview page`
6. `test: Add integration test for Cities tab` (optional)
7. `chore: Code quality improvements and documentation`

Each commit should be focused and atomic (one logical change).

---

## Success Criteria Summary

✅ **Functionality**:
- Cities tab visible on Overview page
- 5 charts displaying tournament-wide data
- All charts interactive and responsive

✅ **Code Quality**:
- All tests pass
- No linter errors
- Type hints on all functions
- Comprehensive docstrings

✅ **UI/UX**:
- No internal chart titles (card headers provide context)
- Empty states handle missing data gracefully
- Error messages are helpful
- Charts follow existing design patterns

✅ **Documentation**:
- Atomic git commits with clear messages
- Code comments explain WHY, not WHAT
- CHANGELOG updated (if exists)

---

## Time Estimates

| Task | Estimated Time | Why |
|------|---------------|-----|
| Task 1: Query Tests | 45 min | Writing 5 test functions with edge cases |
| Task 2: Query Implementation | 60 min | SQL queries with JOINs and aggregations |
| Task 3: Chart Tests | 30 min | Similar structure to query tests |
| Task 4: Chart Implementation | 90 min | 5 different chart types with styling |
| Task 5: Add Tab to Page | 30 min | Copy-paste pattern, modify IDs |
| Task 6: Integration Testing | 30 min | Manual testing + verification |
| Task 7: Code Quality | 20 min | Linting, formatting, docs |
| **Total** | **5 hours** | Includes breaks and debugging |

**Note**: Times assume familiarity with tools. First-time might take 6-7 hours.

---

## Next Steps (Future Enhancements)

After this feature is complete and merged, consider:

1. **Per-Match City Analysis**: Add city charts to Match detail page
2. **City Map Visualization**: Use tile coordinates to show city locations
3. **Governor Analysis**: Track which governors were assigned to cities
4. **City Specialization**: Analyze production patterns per city
5. **Expansion Speed Metrics**: Calculate cities-per-turn rates

See `docs/plans/` for future implementation plans.

---

## Questions?

If stuck or need clarification:
1. Re-read the "Prerequisites" section
2. Check `CLAUDE.md` for codebase patterns
3. Look at existing code for similar patterns
4. Run validation scripts to check data quality
5. Use `git log` to see commit history for similar features

Remember: **YAGNI**, **DRY**, **TDD**, **Atomic Commits**!
