# Law Progression Visualizations Implementation Plan

> **Status**: Completed and archived (2025-10-25)
>
> Charts implemented and working in app. See CLAUDE.md (Dashboard & Chart Conventions section).

> **Created:** 2025-10-08
> **Target:** Add 6 law progression visualizations to the Technology & Research tab on the Matches page

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Domain Knowledge](#domain-knowledge)
4. [Architecture Overview](#architecture-overview)
5. [Implementation Phases](#implementation-phases)
6. [Testing Strategy](#testing-strategy)
7. [Success Criteria](#success-criteria)

---

## Overview

### Goal

Add 6 new law progression visualizations to the **Technology & Research** tab of the Matches page. These visualizations will help users understand:
- When players reached law milestones (4 laws, 7 laws)
- Comparative progression between players
- Statistical distributions across matches
- Efficiency of law progression strategies

### What We're Building

The 6 visualizations are:

1. **Match Comparison** - Side-by-side bar chart showing both players' milestone timing
2. **Race Timeline** - Horizontal timeline showing law progression over game turns
3. **Distribution Analysis** - Box plot showing milestone timing distributions across all matches
4. **Player Performance Heatmap** - Matrix showing player performance with color coding
5. **Efficiency Scatter Plot** - X/Y plot analyzing speed to 4 laws vs speed to 7 laws
6. **Cumulative Law Count** - Line chart showing laws over time (like a race)

### Where in the Codebase

**Files to modify:**
- `tournament_visualizer/pages/matches.py` - Add charts to Technology & Research tab
- `tournament_visualizer/components/charts.py` - Create chart generation functions
- `tests/test_charts_law_progression.py` - Tests for new chart functions (NEW FILE)

**Files to reference:**
- `tournament_visualizer/data/queries.py` - Already has `get_law_progression_by_match()`
- `docs/plans/logdata-ingestion-implementation-plan.md` - Context on law milestone calculation

---

## Prerequisites

### Required Knowledge

**Old World Game Mechanics:**
- Laws are game rules that players adopt to gain bonuses
- Reaching 4 laws and 7 laws are important strategic milestones
- Players adopt laws throughout the game (turn-by-turn)
- Some players may never reach 4 or 7 laws in a match

**Database Structure:**
- `events` table contains `LAW_ADOPTED` events with `turn_number` and `player_id`
- `players` table has `player_name`, `civilization`, and `match_id`
- Player IDs are 1-based (player_id 1, 2, 3...)

**Data Structure from Query:**

The `get_law_progression_by_match()` query returns this DataFrame:

```python
# Sample data structure:
   match_id  player_id  player_name  civilization  turn_to_4_laws  turn_to_7_laws  total_laws
0        10         19      anarkos        Persia              54            <NA>           6
1        10         20       becked       Assyria              46              68           7

# NULL values (<NA>) mean the player never reached that milestone
# Average turn to 4 laws: ~45 turns (range 34-63)
# Average turn to 7 laws: ~71 turns (range 47-92)
# Only 64% of players reach 4 laws, 29% reach 7 laws
```

### Development Environment

**Tools:**
- Python 3.13 (managed by `uv`)
- Plotly (already installed) - For creating interactive charts
- Dash (already installed) - Web framework for the app
- pytest (already installed) - Testing framework
- DuckDB (already installed) - Database

**Project Principles:**
- **DRY (Don't Repeat Yourself)** - Reuse existing chart patterns
- **YAGNI (You Ain't Gonna Need It)** - Only implement what's specified
- **TDD (Test-Driven Development)** - Write tests before code
- **Atomic Commits** - One logical change per commit

**How to Run Tests:**
```bash
# All tests
uv run pytest -v

# Specific test file
uv run pytest tests/test_charts_law_progression.py -v

# With coverage
uv run pytest --cov=tournament_visualizer tests/test_charts_law_progression.py
```

**How to Run the App:**
```bash
# Start server
uv run python manage.py start

# View at http://localhost:8050
# Navigate to Matches page > Select a match > Technology & Research tab
```

**How to Format Code:**
```bash
# Format
uv run black tournament_visualizer/

# Lint
uv run ruff check tournament_visualizer/

# Auto-fix linting issues
uv run ruff check --fix tournament_visualizer/
```

---

## Domain Knowledge

### Law Milestone Calculation

The calculation uses SQL window functions to number laws sequentially for each player:

```sql
-- Step 1: Number each law adoption event (1st, 2nd, 3rd, 4th...)
ROW_NUMBER() OVER (
    PARTITION BY match_id, player_id
    ORDER BY turn_number
) as law_number

-- Step 2: Extract the turn number where the 4th law was adopted
MAX(CASE WHEN law_number = 4 THEN turn_number END) as turn_to_4_laws

-- Step 3: Extract the turn number where the 7th law was adopted
MAX(CASE WHEN law_number = 7 THEN turn_number END) as turn_to_7_laws
```

**Key Insight:** This gives us the EXACT turn number when a player reached each milestone, not an estimate.

### Existing Chart Patterns

All charts in the app follow these patterns:

**1. Chart Function Signature:**
```python
def create_my_chart(df: pd.DataFrame, **kwargs) -> go.Figure:
    """Create a chart description.

    Args:
        df: DataFrame with required columns
        kwargs: Optional parameters

    Returns:
        Plotly figure
    """
```

**2. Empty Data Handling:**
```python
if df.empty:
    return create_empty_chart_placeholder("No data available")
```

**3. Use Base Figure:**
```python
fig = create_base_figure(
    title="Chart Title",
    x_title="X Axis Label",
    y_title="Y Axis Label",
    height=400,  # Optional
)
```

**4. Add Traces:**
```python
fig.add_trace(
    go.Bar(  # or go.Scatter, go.Box, etc.
        x=data,
        y=values,
        marker_color=Config.PRIMARY_COLORS[0],
        name="Series Name",
    )
)
```

**5. Update Layout (if needed):**
```python
fig.update_layout(
    barmode="group",  # or "stack"
    xaxis_tickangle=-45,
)
```

### Plotly Chart Types Reference

**Bar Chart (go.Bar):**
```python
go.Bar(
    x=[1, 2, 3],
    y=[10, 20, 30],
    name="Series Name",
    orientation="v",  # or "h" for horizontal
    marker_color="#FF0000",
    text=[10, 20, 30],  # Values to display on bars
    textposition="auto",  # or "inside", "outside"
)
```

**Scatter Plot (go.Scatter):**
```python
go.Scatter(
    x=[1, 2, 3],
    y=[10, 20, 30],
    mode="lines",  # or "markers", "lines+markers"
    name="Player 1",
    line=dict(color="#FF0000", width=2),
    fill="tonexty",  # Fill area to next trace
)
```

**Box Plot (go.Box):**
```python
go.Box(
    y=[34, 37, 43, 46, 50],
    name="Turn to 4 Laws",
    marker_color="#FF0000",
    boxmean="sd",  # Show mean and standard deviation
)
```

**Heatmap (go.Heatmap):**
```python
go.Heatmap(
    z=[[1, 2], [3, 4]],  # 2D array of values
    x=["Player 1", "Player 2"],
    y=["Match 1", "Match 2"],
    colorscale="RdYlGn",  # Red-Yellow-Green
    reversescale=True,
)
```

---

## Architecture Overview

### Current Match Page Structure

```
matches.py
├── layout (Dash layout)
│   ├── match-selector (dropdown)
│   ├── match-details-section
│   │   ├── Metric cards (game info)
│   │   └── Tabs
│   │       ├── Turn Progression (tab)
│   │       ├── Technology & Research (tab) ← WE ADD HERE
│   │       ├── Player Statistics (tab)
│   │       └── Game Settings (tab)
│   └── match-empty-state
└── callbacks (reactive updates)
    ├── update_match_details()
    ├── update_technology_chart()
    └── ... (one callback per chart)
```

### How Dash Callbacks Work

**Concept:** Callbacks are functions that run when inputs change, updating outputs.

```python
@callback(
    Output("chart-id", "figure"),  # What to update
    Input("match-selector", "value"),  # What triggers the update
)
def update_chart(match_id: Optional[int]) -> go.Figure:
    """This runs every time match_id changes."""
    if not match_id:
        return create_empty_chart_placeholder("Select a match")

    # Fetch data
    queries = get_queries()
    df = queries.get_law_progression_by_match(match_id)

    # Create chart
    return create_my_chart(df)
```

**Key Points:**
- One callback per chart
- Callback IDs must match the `id` in the layout
- Always handle the "no data" case
- Return a Plotly `go.Figure` object

### File Organization

```
tournament_visualizer/
├── components/
│   └── charts.py           # Chart creation functions
├── data/
│   └── queries.py          # SQL queries (already has get_law_progression_by_match)
├── pages/
│   └── matches.py          # Page layout and callbacks
tests/
└── test_charts_law_progression.py  # Tests for new charts
```

---

## Implementation Phases

### Phase 1: Setup & First Visualization (3-4 hours)

This phase sets up the testing infrastructure and implements the first (simplest) visualization.

---

#### Task 1.1: Create Test File with Fixtures

**Goal:** Set up pytest infrastructure with sample data

**File to create:** `tests/test_charts_law_progression.py`

**Code to write:**

```python
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
```

**How to test this (it will fail initially):**
```bash
uv run pytest tests/test_charts_law_progression.py -v
```

**Expected output:** Tests fail with "ImportError: cannot import name 'create_law_milestone_comparison_chart'"

**Why this is correct:** We're doing TDD - write tests first, then implement.

**Commit:**
```bash
git add tests/test_charts_law_progression.py
git commit -m "test: Add test infrastructure for law progression charts

- Create test file with pytest fixtures
- Add sample data fixtures (single match, multiple matches, empty)
- Add failing tests for match comparison chart
- Tests define expected behavior before implementation"
```

---

#### Task 1.2: Implement Match Comparison Chart (Visualization #1)

**Goal:** Create a grouped bar chart showing milestone timing for players in a match

**File to modify:** `tournament_visualizer/components/charts.py`

**What this chart looks like:**
```
Turn to Milestone
70 |           ╔═══╗
60 |           ║   ║  ╔═══╗
50 |    ╔═══╗  ║   ║  ║   ║
40 |    ║   ║  ║   ║  ║   ║
30 |    ║ 4 ║  ║ 7 ║  ║ 4 ║
   +------------------------------------
       anarkos      becked

Legend: ■ 4 Laws   ■ 7 Laws
```

**Code to add at end of `charts.py`:**

```python
def create_law_milestone_comparison_chart(df: pd.DataFrame) -> go.Figure:
    """Create a grouped bar chart comparing law milestone timing between players.

    Shows when each player in a match reached the 4-law and 7-law milestones.
    Useful for head-to-head comparison in a single match.

    Args:
        df: DataFrame with columns: player_name, turn_to_4_laws, turn_to_7_laws
            (typically from get_law_progression_by_match() for one match)

    Returns:
        Plotly figure with grouped bar chart

    Example:
        >>> queries = get_queries()
        >>> df = queries.get_law_progression_by_match(match_id=10)
        >>> fig = create_law_milestone_comparison_chart(df)
    """
    if df.empty:
        return create_empty_chart_placeholder("No law progression data for this match")

    fig = create_base_figure(
        title="Law Milestone Timing Comparison",
        x_title="Player",
        y_title="Turn Number",
        height=400,
    )

    # Add trace for 4 laws milestone
    fig.add_trace(
        go.Bar(
            name="4 Laws",
            x=df["player_name"],
            y=df["turn_to_4_laws"],
            marker_color=Config.PRIMARY_COLORS[0],
            text=df["turn_to_4_laws"].round(0).astype("Int64"),  # Int64 handles NA
            textposition="auto",
            hovertemplate="<b>%{x}</b><br>4th Law: Turn %{y}<extra></extra>",
        )
    )

    # Add trace for 7 laws milestone
    fig.add_trace(
        go.Bar(
            name="7 Laws",
            x=df["player_name"],
            y=df["turn_to_7_laws"],
            marker_color=Config.PRIMARY_COLORS[1],
            text=df["turn_to_7_laws"].round(0).astype("Int64"),
            textposition="auto",
            hovertemplate="<b>%{x}</b><br>7th Law: Turn %{y}<extra></extra>",
        )
    )

    # Group bars side-by-side
    fig.update_layout(barmode="group")

    # Add annotation explaining NULL values
    fig.add_annotation(
        text="Missing bars indicate milestone not reached",
        xref="paper",
        yref="paper",
        x=0.5,
        y=-0.15,
        showarrow=False,
        font=dict(size=10, color="gray"),
    )

    return fig
```

**How to test:**
```bash
uv run pytest tests/test_charts_law_progression.py::TestLawMilestoneComparisonChart -v
```

**Expected output:** All tests pass ✅

**Commit:**
```bash
git add tournament_visualizer/components/charts.py
git commit -m "feat: Add law milestone comparison chart

- Create grouped bar chart showing 4-law and 7-law timing
- Handle NULL values for players who didn't reach milestones
- Add hover tooltips with turn numbers
- Include annotation explaining missing bars"
```

---

#### Task 1.3: Add Chart to Matches Page

**Goal:** Integrate the new chart into the Technology & Research tab

**File to modify:** `tournament_visualizer/pages/matches.py`

**Step 1: Update imports** (add to existing imports at top of file)

```python
from tournament_visualizer.components.charts import (
    create_empty_chart_placeholder,
    create_statistics_grouped_bar,
    create_statistics_radar_chart,
    create_technology_comparison_chart,
    create_technology_detail_chart,
    create_law_milestone_comparison_chart,  # ← ADD THIS
)
```

**Step 2: Find the Technology & Research tab in layout**

Search for `"Technology & Research"` in the file. You'll find it around line 368.

**Step 3: Add the new chart to the tab's content**

Replace the existing Technology & Research tab content with this:

```python
{
    "label": "Technology & Research",
    "tab_id": "technology",
    "content": [
        # Existing technology charts
        dbc.Row(
            [
                dbc.Col(
                    [
                        create_chart_card(
                            title="Technology Research Comparison",
                            chart_id="match-technology-chart",
                            height="400px",
                        )
                    ],
                    width=6,
                ),
                dbc.Col(
                    [
                        create_chart_card(
                            title="Top 10 Technologies",
                            chart_id="match-technology-detail-chart",
                            height="400px",
                        )
                    ],
                    width=6,
                ),
            ],
            className="mb-3",
        ),
        # NEW: Law Progression Section
        html.Hr(),  # Visual separator
        html.H4("Law Progression Analysis", className="mt-4 mb-3"),
        # Visualization #1: Match Comparison
        dbc.Row(
            [
                dbc.Col(
                    [
                        create_chart_card(
                            title="Law Milestone Timing (This Match)",
                            chart_id="match-law-milestone-comparison",
                            height="400px",
                        )
                    ],
                    width=12,
                ),
            ],
            className="mb-3",
        ),
    ],
},
```

**Step 4: Add callback to populate the chart**

Add this callback at the end of the file (before the final settings callback):

```python
@callback(
    Output("match-law-milestone-comparison", "figure"),
    Input("match-selector", "value"),
)
def update_law_milestone_comparison(match_id: Optional[int]) -> go.Figure:
    """Update law milestone comparison chart.

    Args:
        match_id: Selected match ID

    Returns:
        Plotly figure with law milestone comparison
    """
    if not match_id:
        return create_empty_chart_placeholder(
            "Select a match to view law progression"
        )

    try:
        queries = get_queries()
        df = queries.get_law_progression_by_match(match_id)

        if df.empty:
            return create_empty_chart_placeholder(
                "No law progression data available for this match"
            )

        return create_law_milestone_comparison_chart(df)

    except Exception as e:
        logger.error(f"Error loading law milestone comparison: {e}")
        return create_empty_chart_placeholder(
            f"Error loading data: {str(e)}"
        )
```

**How to test manually:**
```bash
# Start the server
uv run python manage.py start

# Open browser to http://localhost:8050
# Navigate to: Matches page > Select any match > Technology & Research tab
# Scroll down to see "Law Milestone Timing (This Match)" chart
```

**Expected result:** Chart displays showing both players' milestone timing

**Commit:**
```bash
git add tournament_visualizer/pages/matches.py
git commit -m "feat: Add law milestone comparison to Technology tab

- Add new section 'Law Progression Analysis' to Tech tab
- Create callback to populate law milestone chart
- Handle empty data and error states
- Position chart below existing technology charts"
```

---

### Phase 2: Timeline Visualization (2-3 hours)

This phase implements the horizontal timeline chart showing law progression over game turns.

---

#### Task 2.1: Add Tests for Race Timeline Chart

**Goal:** Define expected behavior for timeline visualization

**File to modify:** `tests/test_charts_law_progression.py`

**Code to add:**

```python
# Add this import at the top
from tournament_visualizer.components.charts import (
    create_empty_chart_placeholder,
    create_law_milestone_comparison_chart,
    create_law_race_timeline_chart,  # ← ADD THIS
)


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

    def test_handles_player_who_didnt_reach_7_laws(self, sample_match_data: pd.DataFrame) -> None:
        """Should gracefully handle players with fewer milestones."""
        # anarkos only reached 4 laws, not 7
        fig = create_law_race_timeline_chart(sample_match_data)

        # Should not raise an error
        assert isinstance(fig, go.Figure)

    def test_empty_data_returns_placeholder(self, empty_data: pd.DataFrame) -> None:
        """Should handle empty data."""
        fig = create_law_race_timeline_chart(empty_data)
        assert len(fig.data) == 0  # Placeholder has no traces
```

**Run tests (they'll fail):**
```bash
uv run pytest tests/test_charts_law_progression.py::TestLawRaceTimelineChart -v
```

**Commit:**
```bash
git add tests/test_charts_law_progression.py
git commit -m "test: Add tests for law race timeline chart

- Define expected behavior for horizontal timeline
- Test scatter plot structure
- Test handling of incomplete progressions
- Tests will fail until implementation is added"
```

---

#### Task 2.2: Implement Race Timeline Chart

**Goal:** Create a horizontal timeline showing when each player reached milestones

**File to modify:** `tournament_visualizer/components/charts.py`

**What this chart looks like:**
```
Turn:  0----10----20----30----40----50----60----70----80
       |
P1:    |                                ●(54)
       |                                4 laws
P2:    |                         ●(46)          ●(68)
       |                         4 laws         7 laws
```

**Code to add:**

```python
def create_law_race_timeline_chart(df: pd.DataFrame) -> go.Figure:
    """Create a horizontal timeline showing law milestone progression.

    Displays milestones as markers on a timeline, making it easy to see
    who reached each milestone first and the gap between players.

    Args:
        df: DataFrame with columns: player_name, turn_to_4_laws, turn_to_7_laws

    Returns:
        Plotly figure with scatter plot timeline
    """
    if df.empty:
        return create_empty_chart_placeholder("No law progression data available")

    fig = create_base_figure(
        title="Law Milestone Race Timeline",
        x_title="Turn Number",
        y_title="Player",
        height=300,
    )

    # Create Y positions for each player (0, 1, 2, ...)
    player_positions = {name: i for i, name in enumerate(df["player_name"])}

    # For each player, add markers for their milestones
    for _, row in df.iterrows():
        player_name = row["player_name"]
        y_pos = player_positions[player_name]

        # Prepare milestone data (only include milestones that were reached)
        milestones = []

        if pd.notna(row["turn_to_4_laws"]):
            milestones.append({
                "turn": row["turn_to_4_laws"],
                "label": "4 laws",
                "symbol": "circle",
            })

        if pd.notna(row["turn_to_7_laws"]):
            milestones.append({
                "turn": row["turn_to_7_laws"],
                "label": "7 laws",
                "symbol": "star",
            })

        # Add a line connecting the milestones for this player
        if milestones:
            turns = [m["turn"] for m in milestones]

            fig.add_trace(
                go.Scatter(
                    x=turns,
                    y=[y_pos] * len(turns),
                    mode="lines+markers+text",
                    name=player_name,
                    line=dict(
                        color=Config.PRIMARY_COLORS[y_pos % len(Config.PRIMARY_COLORS)],
                        width=2,
                    ),
                    marker=dict(
                        size=12,
                        symbol=[m["symbol"] for m in milestones],
                    ),
                    text=[f"{m['label']}<br>Turn {int(m['turn'])}" for m in milestones],
                    textposition="top center",
                    hovertemplate="<b>%{fullData.name}</b><br>%{text}<extra></extra>",
                )
            )

    # Update Y-axis to show player names
    fig.update_yaxes(
        tickmode="array",
        tickvals=list(player_positions.values()),
        ticktext=list(player_positions.keys()),
    )

    # Add vertical grid lines for easier reading
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="rgba(128,128,128,0.2)")

    return fig
```

**Test:**
```bash
uv run pytest tests/test_charts_law_progression.py::TestLawRaceTimelineChart -v
```

**Commit:**
```bash
git add tournament_visualizer/components/charts.py
git commit -m "feat: Add law race timeline chart

- Create horizontal timeline with milestone markers
- Use circles for 4-law milestone, stars for 7-law
- Connect milestones with lines for each player
- Add text labels showing milestone and turn number"
```

---

#### Task 2.3: Add Timeline Chart to Page

**File to modify:** `tournament_visualizer/pages/matches.py`

**Step 1: Update imports**
```python
from tournament_visualizer.components.charts import (
    # ... existing imports ...
    create_law_milestone_comparison_chart,
    create_law_race_timeline_chart,  # ← ADD THIS
)
```

**Step 2: Add chart to layout** (in Technology & Research tab content)

Add this after the milestone comparison chart:

```python
# Visualization #2: Race Timeline
dbc.Row(
    [
        dbc.Col(
            [
                create_chart_card(
                    title="Law Milestone Timeline",
                    chart_id="match-law-race-timeline",
                    height="300px",
                )
            ],
            width=12,
        ),
    ],
    className="mb-3",
),
```

**Step 3: Add callback**

```python
@callback(
    Output("match-law-race-timeline", "figure"),
    Input("match-selector", "value"),
)
def update_law_race_timeline(match_id: Optional[int]) -> go.Figure:
    """Update law race timeline chart.

    Args:
        match_id: Selected match ID

    Returns:
        Plotly figure with timeline
    """
    if not match_id:
        return create_empty_chart_placeholder("Select a match")

    try:
        queries = get_queries()
        df = queries.get_law_progression_by_match(match_id)

        if df.empty:
            return create_empty_chart_placeholder("No data available")

        return create_law_race_timeline_chart(df)

    except Exception as e:
        logger.error(f"Error loading law race timeline: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")
```

**Test manually** in browser, then commit:

```bash
git add tournament_visualizer/pages/matches.py
git commit -m "feat: Add law race timeline to Technology tab

- Add timeline chart below milestone comparison
- Create callback to populate timeline chart
- Set appropriate height (300px) for horizontal layout"
```

---

### Phase 3: Distribution & Heatmap Visualizations (3-4 hours)

This phase adds statistical visualizations showing data across ALL matches.

---

#### Task 3.1: Add Tests for Distribution Chart

**File to modify:** `tests/test_charts_law_progression.py`

**Important:** This chart uses data from ALL matches, not just one.

```python
# Update import
from tournament_visualizer.components.charts import (
    create_empty_chart_placeholder,
    create_law_milestone_comparison_chart,
    create_law_race_timeline_chart,
    create_law_milestone_distribution_chart,  # ← ADD THIS
)


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
```

**Commit:**
```bash
git add tests/test_charts_law_progression.py
git commit -m "test: Add tests for law milestone distribution chart

- Test box plot structure
- Test handling of sparse milestone data
- Define expected behavior for statistical distribution"
```

---

#### Task 3.2: Implement Distribution Chart

**File to modify:** `tournament_visualizer/components/charts.py`

**What this chart looks like:**
```
Turn
80 |                    ○ (outlier)
70 |              ┌─────┴─────┐
60 |              │     │     │
50 |   ┌──────────┤─────┼─────┤
40 |   │     │    │     │     │
30 |   │     │    └─────┴─────┘
   +---------------------------
      4 Laws      7 Laws

Box shows: min, Q1, median, Q3, max
```

**Code to add:**

```python
def create_law_milestone_distribution_chart(df: pd.DataFrame) -> go.Figure:
    """Create a box plot showing distribution of milestone timing across all matches.

    Box plot displays:
    - Median (middle line)
    - Quartiles (box boundaries)
    - Min/max (whiskers)
    - Outliers (individual points)

    Args:
        df: DataFrame with turn_to_4_laws and turn_to_7_laws columns
            (typically from get_law_progression_by_match() for ALL matches)

    Returns:
        Plotly figure with box plots
    """
    if df.empty:
        return create_empty_chart_placeholder("No law progression data available")

    # Filter out players who didn't reach milestones
    df_4_laws = df[df["turn_to_4_laws"].notna()]
    df_7_laws = df[df["turn_to_7_laws"].notna()]

    if df_4_laws.empty and df_7_laws.empty:
        return create_empty_chart_placeholder(
            "No players reached law milestones in the dataset"
        )

    fig = create_base_figure(
        title="Law Milestone Timing Distribution (All Matches)",
        x_title="Milestone",
        y_title="Turn Number",
        height=450,
    )

    # Add box plot for 4 laws
    if not df_4_laws.empty:
        fig.add_trace(
            go.Box(
                y=df_4_laws["turn_to_4_laws"],
                name="4 Laws",
                marker_color=Config.PRIMARY_COLORS[0],
                boxmean="sd",  # Show mean and standard deviation
                hovertemplate=(
                    "<b>4 Laws Milestone</b><br>"
                    "Turn: %{y}<br>"
                    "<extra></extra>"
                ),
            )
        )

    # Add box plot for 7 laws
    if not df_7_laws.empty:
        fig.add_trace(
            go.Box(
                y=df_7_laws["turn_to_7_laws"],
                name="7 Laws",
                marker_color=Config.PRIMARY_COLORS[1],
                boxmean="sd",
                hovertemplate=(
                    "<b>7 Laws Milestone</b><br>"
                    "Turn: %{y}<br>"
                    "<extra></extra>"
                ),
            )
        )

    # Add statistics annotation
    if not df_4_laws.empty:
        median_4 = df_4_laws["turn_to_4_laws"].median()
        mean_4 = df_4_laws["turn_to_4_laws"].mean()
        count_4 = len(df_4_laws)

        stats_text = f"4 Laws: n={count_4}, median={median_4:.0f}, mean={mean_4:.1f}"

        if not df_7_laws.empty:
            median_7 = df_7_laws["turn_to_7_laws"].median()
            mean_7 = df_7_laws["turn_to_7_laws"].mean()
            count_7 = len(df_7_laws)
            stats_text += f" | 7 Laws: n={count_7}, median={median_7:.0f}, mean={mean_7:.1f}"

        fig.add_annotation(
            text=stats_text,
            xref="paper",
            yref="paper",
            x=0.5,
            y=1.1,
            showarrow=False,
            font=dict(size=11),
        )

    return fig
```

**Test:**
```bash
uv run pytest tests/test_charts_law_progression.py::TestLawMilestoneDistributionChart -v
```

**Commit:**
```bash
git add tournament_visualizer/components/charts.py
git commit -m "feat: Add law milestone distribution chart

- Create box plots showing timing distribution
- Display mean and standard deviation
- Add statistics annotation with n, median, mean
- Handle sparse data (few players reaching milestones)"
```

---

#### Task 3.3: Add Tests for Heatmap Chart

**File to modify:** `tests/test_charts_law_progression.py`

```python
# Update import
from tournament_visualizer.components.charts import (
    # ... existing ...
    create_law_progression_heatmap,  # ← ADD THIS
)


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

    def test_handles_players_without_milestones(self, sample_all_matches_data: pd.DataFrame) -> None:
        """Should show players who never reached milestones."""
        # Several players in fixture never reached 4 laws
        fig = create_law_progression_heatmap(sample_all_matches_data)

        assert isinstance(fig, go.Figure)
```

**Commit:**
```bash
git add tests/test_charts_law_progression.py
git commit -m "test: Add tests for law progression heatmap

- Test heatmap structure
- Test handling of incomplete progression data
- Define expected visualization behavior"
```

---

#### Task 3.4: Implement Heatmap Chart

**File to modify:** `tournament_visualizer/components/charts.py`

**What this chart looks like:**
```
              Match 1  Match 3  Match 4
yagman          🟢       -       -
Marauder        🔴       -       -
fonder           -      🟢       -
aran             -      🟡       -
PBM              -       -      🔴
MongrelEyes      -       -      🔴

Legend: 🟢 Reached 7 laws  🟡 Reached 4 laws  🔴 < 4 laws
```

**Code to add:**

```python
def create_law_progression_heatmap(df: pd.DataFrame) -> go.Figure:
    """Create a heatmap showing player law progression performance.

    Color coding:
    - Green: Reached 7 laws (strong performance)
    - Yellow: Reached 4 laws (moderate performance)
    - Red: < 4 laws (weak performance)
    - Gray: No data

    Args:
        df: DataFrame with player_name, match_id, turn_to_4_laws, turn_to_7_laws

    Returns:
        Plotly figure with heatmap
    """
    if df.empty:
        return create_empty_chart_placeholder("No law progression data available")

    # Create a performance score:
    # 3 = reached 7 laws
    # 2 = reached 4 laws (but not 7)
    # 1 = < 4 laws
    # 0 = no data (shouldn't happen in valid data)
    def calculate_performance_score(row: pd.Series) -> int:
        """Calculate performance score based on milestones reached."""
        if pd.notna(row["turn_to_7_laws"]):
            return 3  # Reached 7 laws
        elif pd.notna(row["turn_to_4_laws"]):
            return 2  # Reached 4 laws
        else:
            return 1  # Didn't reach 4 laws

    df["performance_score"] = df.apply(calculate_performance_score, axis=1)

    # Pivot table: rows = players, columns = matches, values = performance score
    pivot_data = df.pivot_table(
        index="player_name",
        columns="match_id",
        values="performance_score",
        aggfunc="first",  # One entry per player per match
    )

    if pivot_data.empty:
        return create_empty_chart_placeholder("Insufficient data for heatmap")

    # Create custom colorscale
    # 1 = red, 2 = yellow, 3 = green
    colorscale = [
        [0.0, "#EF5350"],   # Red (poor)
        [0.33, "#EF5350"],  # Red
        [0.34, "#FFA726"],  # Yellow (moderate)
        [0.66, "#FFA726"],  # Yellow
        [0.67, "#66BB6A"],  # Green (excellent)
        [1.0, "#66BB6A"],   # Green
    ]

    fig = create_base_figure(
        title="Player Law Progression Performance (All Matches)",
        show_legend=False,
        height=400 + (len(pivot_data) * 20),  # Scale height with player count
    )

    # Create hover text
    hover_text = []
    for player in pivot_data.index:
        row_text = []
        for match_id in pivot_data.columns:
            score = pivot_data.loc[player, match_id]
            if pd.notna(score):
                if score == 3:
                    text = f"Match {match_id}<br>{player}<br>Reached 7 laws"
                elif score == 2:
                    text = f"Match {match_id}<br>{player}<br>Reached 4 laws"
                else:
                    text = f"Match {match_id}<br>{player}<br>< 4 laws"
            else:
                text = f"Match {match_id}<br>{player}<br>No data"
            row_text.append(text)
        hover_text.append(row_text)

    fig.add_trace(
        go.Heatmap(
            z=pivot_data.values,
            x=[f"Match {mid}" for mid in pivot_data.columns],
            y=pivot_data.index,
            colorscale=colorscale,
            hovertext=hover_text,
            hoverinfo="text",
            showscale=True,
            colorbar=dict(
                title="Performance",
                tickvals=[1, 2, 3],
                ticktext=["< 4 laws", "4 laws", "7 laws"],
            ),
        )
    )

    fig.update_xaxes(title="Match", side="bottom")
    fig.update_yaxes(title="Player")

    return fig
```

**Test:**
```bash
uv run pytest tests/test_charts_law_progression.py::TestLawProgressionHeatmap -v
```

**Commit:**
```bash
git add tournament_visualizer/components/charts.py
git commit -m "feat: Add law progression performance heatmap

- Create heatmap with color-coded performance levels
- Green = 7 laws, Yellow = 4 laws, Red = < 4 laws
- Pivot data by player and match
- Scale chart height based on player count
- Add custom colorscale and hover tooltips"
```

---

#### Task 3.5: Add Distribution and Heatmap to Page

**File to modify:** `tournament_visualizer/pages/matches.py`

**Important:** These charts use data from ALL matches, so they should display the same data regardless of which match is selected.

**Step 1: Update imports**
```python
from tournament_visualizer.components.charts import (
    # ... existing ...
    create_law_milestone_distribution_chart,
    create_law_progression_heatmap,
)
```

**Step 2: Add charts to layout**

Add after the timeline chart:

```python
# Visualization #3: Distribution
dbc.Row(
    [
        dbc.Col(
            [
                create_chart_card(
                    title="Milestone Timing Distribution (All Matches)",
                    chart_id="match-law-distribution",
                    height="450px",
                )
            ],
            width=6,
        ),
        # Visualization #4: Heatmap
        dbc.Col(
            [
                create_chart_card(
                    title="Player Performance Heatmap",
                    chart_id="match-law-heatmap",
                    height="450px",
                )
            ],
            width=6,
        ),
    ],
    className="mb-3",
),
```

**Step 3: Add callbacks**

```python
@callback(
    Output("match-law-distribution", "figure"),
    Input("match-selector", "value"),
)
def update_law_distribution(match_id: Optional[int]) -> go.Figure:
    """Update law milestone distribution chart.

    Note: This chart shows data from ALL matches, not just the selected one.

    Args:
        match_id: Selected match ID (used to trigger update, but chart shows all data)

    Returns:
        Plotly figure with box plot distribution
    """
    try:
        queries = get_queries()
        # Get ALL matches data (pass None to get_law_progression_by_match)
        df = queries.get_law_progression_by_match(match_id=None)

        if df.empty:
            return create_empty_chart_placeholder("No law progression data available")

        return create_law_milestone_distribution_chart(df)

    except Exception as e:
        logger.error(f"Error loading law distribution: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("match-law-heatmap", "figure"),
    Input("match-selector", "value"),
)
def update_law_heatmap(match_id: Optional[int]) -> go.Figure:
    """Update law progression heatmap.

    Note: This chart shows data from ALL matches.

    Args:
        match_id: Selected match ID (used to trigger update, but chart shows all data)

    Returns:
        Plotly figure with heatmap
    """
    try:
        queries = get_queries()
        df = queries.get_law_progression_by_match(match_id=None)

        if df.empty:
            return create_empty_chart_placeholder("No law progression data available")

        return create_law_progression_heatmap(df)

    except Exception as e:
        logger.error(f"Error loading law heatmap: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")
```

**Test manually**, then commit:

```bash
git add tournament_visualizer/pages/matches.py
git commit -m "feat: Add distribution and heatmap to Technology tab

- Add box plot showing milestone timing distribution
- Add heatmap showing player performance across matches
- Both charts show all matches data (not filtered by selection)
- Position charts side-by-side in same row"
```

---

### Phase 4: Scatter Plot & Cumulative Charts (3-4 hours)

Final two visualizations: efficiency analysis and cumulative progression.

---

#### Task 4.1: Add Tests for Scatter Plot

**File to modify:** `tests/test_charts_law_progression.py`

```python
# Update import
from tournament_visualizer.components.charts import (
    # ... existing ...
    create_law_efficiency_scatter,  # ← ADD THIS
)


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

    def test_handles_no_complete_progressions(self, sample_match_data: pd.DataFrame) -> None:
        """Should handle when no players reached both milestones."""
        # In sample_match_data, anarkos only reached 4 laws
        fig = create_law_efficiency_scatter(sample_match_data)

        # Should return placeholder or chart with limited data
        assert isinstance(fig, go.Figure)
```

**Commit:**
```bash
git add tests/test_charts_law_progression.py
git commit -m "test: Add tests for law efficiency scatter plot

- Test scatter plot structure
- Test filtering to complete progressions only
- Test handling of incomplete data"
```

---

#### Task 4.2: Implement Scatter Plot

**File to modify:** `tournament_visualizer/components/charts.py`

**What this chart looks like:**
```
Turn to 7 Laws
90 |                  ● (slow)
80 |          ●
70 |      ●       ● (efficient)
60 |  ●
   +---------------------------
   30   40   50   60
      Turn to 4 Laws

Lower-left = fastest progression
Upper-right = slowest progression
```

**Code to add:**

```python
def create_law_efficiency_scatter(df: pd.DataFrame) -> go.Figure:
    """Create a scatter plot analyzing law progression efficiency.

    X-axis: Turn to reach 4 laws
    Y-axis: Turn to reach 7 laws

    Players in the lower-left corner are most efficient (reached milestones quickly).
    Players in the upper-right are slower.

    Args:
        df: DataFrame with player_name, civilization, turn_to_4_laws, turn_to_7_laws

    Returns:
        Plotly figure with scatter plot
    """
    if df.empty:
        return create_empty_chart_placeholder("No law progression data available")

    # Filter to only players who reached BOTH milestones
    df_complete = df[
        df["turn_to_4_laws"].notna() & df["turn_to_7_laws"].notna()
    ].copy()

    if df_complete.empty:
        return create_empty_chart_placeholder(
            "No players reached both 4 and 7 law milestones"
        )

    fig = create_base_figure(
        title="Law Progression Efficiency Analysis",
        x_title="Turn to Reach 4 Laws (lower = faster)",
        y_title="Turn to Reach 7 Laws (lower = faster)",
        height=500,
    )

    # Calculate time between milestones
    df_complete["time_between"] = (
        df_complete["turn_to_7_laws"] - df_complete["turn_to_4_laws"]
    )

    # Color by civilization
    unique_civs = df_complete["civilization"].unique()
    civ_colors = {
        civ: CIVILIZATION_COLORS.get(civ, Config.PRIMARY_COLORS[i % len(Config.PRIMARY_COLORS)])
        for i, civ in enumerate(unique_civs)
    }

    # Group by civilization for separate traces
    for civ in unique_civs:
        civ_data = df_complete[df_complete["civilization"] == civ]

        fig.add_trace(
            go.Scatter(
                x=civ_data["turn_to_4_laws"],
                y=civ_data["turn_to_7_laws"],
                mode="markers+text",
                name=civ,
                marker=dict(
                    size=12,
                    color=civ_colors[civ],
                    line=dict(width=1, color="white"),
                ),
                text=civ_data["player_name"],
                textposition="top center",
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    f"{civ}<br>"
                    "4 Laws: Turn %{x}<br>"
                    "7 Laws: Turn %{y}<br>"
                    "<extra></extra>"
                ),
            )
        )

    # Add diagonal line showing typical progression ratio
    if not df_complete.empty:
        x_range = [df_complete["turn_to_4_laws"].min(), df_complete["turn_to_4_laws"].max()]
        # Typical ratio: if 4 laws at turn X, 7 laws around turn 1.5*X
        y_trend = [x * 1.5 for x in x_range]

        fig.add_trace(
            go.Scatter(
                x=x_range,
                y=y_trend,
                mode="lines",
                name="Typical Pace",
                line=dict(dash="dash", color="gray", width=1),
                showlegend=True,
                hoverinfo="skip",
            )
        )

    # Add quadrant annotations
    fig.add_annotation(
        text="Fast & Efficient",
        x=0.2,
        y=0.2,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(size=10, color="green"),
    )

    fig.add_annotation(
        text="Slow",
        x=0.8,
        y=0.8,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(size=10, color="red"),
    )

    return fig
```

**Test:**
```bash
uv run pytest tests/test_charts_law_progression.py::TestLawEfficiencyScatter -v
```

**Commit:**
```bash
git add tournament_visualizer/components/charts.py
git commit -m "feat: Add law efficiency scatter plot

- Plot turn-to-4-laws vs turn-to-7-laws
- Color code by civilization
- Add typical pace trendline
- Add quadrant annotations (fast/slow)
- Only include players who reached both milestones"
```

---

#### Task 4.3: Add Tests for Cumulative Chart

**File to modify:** `tests/test_charts_law_progression.py`

**Important:** This chart requires a new query that we don't have yet. We'll need to create it.

```python
# Update import
from tournament_visualizer.components.charts import (
    # ... existing ...
    create_cumulative_law_count_chart,  # ← ADD THIS
)


class TestCumulativeLawCountChart:
    """Tests for cumulative law count line chart (Visualization #6)."""

    def test_returns_figure(self, sample_match_data: pd.DataFrame) -> None:
        """Should return a Plotly Figure object."""
        # Note: This will need different data structure (turn-by-turn cumulative)
        # For now, we'll test with what we have
        fig = create_cumulative_law_count_chart(sample_match_data)
        assert isinstance(fig, go.Figure)

    def test_uses_line_chart(self, sample_match_data: pd.DataFrame) -> None:
        """Should use line chart (Scatter with lines)."""
        fig = create_cumulative_law_count_chart(sample_match_data)

        if len(fig.data) > 0:
            # Should be Scatter traces
            assert isinstance(fig.data[0], go.Scatter)

    def test_has_trace_per_player(self, sample_match_data: pd.DataFrame) -> None:
        """Should have one line per player."""
        fig = create_cumulative_law_count_chart(sample_match_data)

        # Should have 2 traces (one per player in fixture)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        assert len(scatter_traces) == 2
```

**Commit:**
```bash
git add tests/test_charts_law_progression.py
git commit -m "test: Add tests for cumulative law count chart

- Test line chart structure
- Test one trace per player
- Note: Will need new query for turn-by-turn data"
```

---

#### Task 4.4: Create Query for Cumulative Law Count

**Goal:** Add a query that returns cumulative law counts by turn

**File to modify:** `tournament_visualizer/data/queries.py`

**Add this method to the `TournamentQueries` class:**

```python
def get_cumulative_law_count_by_turn(self, match_id: int) -> pd.DataFrame:
    """Get cumulative law count by turn for each player.

    Similar to get_tech_count_by_turn, but for laws.

    Args:
        match_id: Match ID to analyze

    Returns:
        DataFrame with columns: player_id, player_name, turn_number, cumulative_laws
    """
    query = """
    WITH law_events AS (
        SELECT
            e.player_id,
            p.player_name,
            e.turn_number,
            ROW_NUMBER() OVER (
                PARTITION BY e.player_id
                ORDER BY e.turn_number
            ) as cumulative_laws
        FROM events e
        JOIN players p ON e.match_id = p.match_id AND e.player_id = p.player_id
        WHERE e.event_type = 'LAW_ADOPTED'
            AND e.match_id = ?
    )
    SELECT DISTINCT
        player_id,
        player_name,
        turn_number,
        cumulative_laws
    FROM law_events
    ORDER BY player_id, turn_number
    """

    with self.db.get_connection() as conn:
        return conn.execute(query, [match_id]).df()
```

**Test the query:**
```bash
uv run python -c "
from tournament_visualizer.data.database import get_database
from tournament_visualizer.data.queries import TournamentQueries

db = get_database()
queries = TournamentQueries(db)
df = queries.get_cumulative_law_count_by_turn(match_id=10)
print(df.to_string())
"
```

**Expected output:**
```
   player_id player_name  turn_number  cumulative_laws
0         19     anarkos           11                1
1         19     anarkos           36                2
2         19     anarkos           49                3
...
```

**Commit:**
```bash
git add tournament_visualizer/data/queries.py
git commit -m "feat: Add query for cumulative law count by turn

- Create get_cumulative_law_count_by_turn() method
- Use ROW_NUMBER window function to calculate cumulative count
- Return turn-by-turn progression for each player
- Pattern matches existing get_tech_count_by_turn()"
```

---

#### Task 4.5: Implement Cumulative Chart

**File to modify:** `tournament_visualizer/components/charts.py`

**What this chart looks like:**
```
Laws
 7 |                    ___becked
 6 |                ___/
 5 |               /
 4 |     ____anarkos
 3 |    /
 2 |   /
 1 |  /
   +---------------------------
     10   30   50   70   Turns
```

**Code to add:**

```python
def create_cumulative_law_count_chart(df: pd.DataFrame) -> go.Figure:
    """Create a line chart showing cumulative law count over time.

    Displays a "racing" view of law progression, making it easy to see
    who was ahead at any point in the match.

    Args:
        df: DataFrame with columns: player_name, turn_number, cumulative_laws
            (from get_cumulative_law_count_by_turn())

    Returns:
        Plotly figure with line chart
    """
    if df.empty:
        return create_empty_chart_placeholder(
            "No law progression data available for this match"
        )

    fig = create_base_figure(
        title="Cumulative Law Count Race",
        x_title="Turn Number",
        y_title="Laws Adopted",
        height=400,
    )

    # Add a line for each player
    players = df["player_name"].unique()

    for i, player in enumerate(players):
        player_data = df[df["player_name"] == player]

        # Add a point at turn 0 with 0 laws for cleaner visualization
        turns = [0] + player_data["turn_number"].tolist()
        laws = [0] + player_data["cumulative_laws"].tolist()

        fig.add_trace(
            go.Scatter(
                x=turns,
                y=laws,
                mode="lines+markers",
                name=player,
                line=dict(
                    color=Config.PRIMARY_COLORS[i % len(Config.PRIMARY_COLORS)],
                    width=3,
                ),
                marker=dict(size=6),
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "Turn %{x}: %{y} laws<br>"
                    "<extra></extra>"
                ),
            )
        )

    # Add reference lines for milestones
    fig.add_hline(
        y=4,
        line_dash="dash",
        line_color="rgba(128,128,128,0.5)",
        annotation_text="4 Laws",
        annotation_position="right",
    )

    fig.add_hline(
        y=7,
        line_dash="dash",
        line_color="rgba(128,128,128,0.5)",
        annotation_text="7 Laws",
        annotation_position="right",
    )

    # Set Y-axis to start at 0 and use integer ticks
    fig.update_yaxes(
        rangemode="tozero",
        dtick=1,  # Tick every 1 law
    )

    return fig
```

**Update test fixture in test file:**

The test needs the cumulative data structure. Update `sample_match_data` fixture:

```python
@pytest.fixture
def sample_cumulative_data() -> pd.DataFrame:
    """Sample cumulative law count data for testing."""
    return pd.DataFrame(
        {
            "player_id": [19, 19, 19, 20, 20, 20, 20],
            "player_name": ["anarkos", "anarkos", "anarkos", "becked", "becked", "becked", "becked"],
            "turn_number": [11, 36, 49, 20, 37, 43, 46],
            "cumulative_laws": [1, 2, 3, 1, 2, 3, 4],
        }
    )
```

**Update tests to use new fixture:**

```python
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

    def test_includes_milestone_reference_lines(self, sample_cumulative_data: pd.DataFrame) -> None:
        """Should show horizontal lines for 4 and 7 law milestones."""
        fig = create_cumulative_law_count_chart(sample_cumulative_data)

        # Check for horizontal lines (shapes in layout)
        assert len(fig.layout.shapes) >= 2  # At least 4-law and 7-law lines
```

**Test:**
```bash
uv run pytest tests/test_charts_law_progression.py::TestCumulativeLawCountChart -v
```

**Commit:**
```bash
git add tournament_visualizer/components/charts.py tests/test_charts_law_progression.py
git commit -m "feat: Add cumulative law count race chart

- Create line chart showing law progression over time
- Add point at turn 0 for cleaner visualization
- Add reference lines for 4 and 7 law milestones
- Use integer Y-axis ticks
- Update tests with cumulative data fixture"
```

---

#### Task 4.6: Add Scatter and Cumulative to Page

**File to modify:** `tournament_visualizer/pages/matches.py`

**Step 1: Update imports**
```python
from tournament_visualizer.components.charts import (
    # ... existing ...
    create_law_efficiency_scatter,
    create_cumulative_law_count_chart,
)
```

**Step 2: Add charts to layout**

Add after the distribution/heatmap row:

```python
# Visualization #5: Efficiency Scatter
dbc.Row(
    [
        dbc.Col(
            [
                create_chart_card(
                    title="Law Progression Efficiency (All Matches)",
                    chart_id="match-law-efficiency",
                    height="500px",
                )
            ],
            width=6,
        ),
        # Visualization #6: Cumulative Count
        dbc.Col(
            [
                create_chart_card(
                    title="Cumulative Law Count (This Match)",
                    chart_id="match-law-cumulative",
                    height="400px",
                )
            ],
            width=6,
        ),
    ],
    className="mb-3",
),
```

**Step 3: Add callbacks**

```python
@callback(
    Output("match-law-efficiency", "figure"),
    Input("match-selector", "value"),
)
def update_law_efficiency(match_id: Optional[int]) -> go.Figure:
    """Update law efficiency scatter plot.

    Note: Shows data from ALL matches.

    Args:
        match_id: Selected match ID

    Returns:
        Plotly figure with scatter plot
    """
    try:
        queries = get_queries()
        df = queries.get_law_progression_by_match(match_id=None)

        if df.empty:
            return create_empty_chart_placeholder("No data available")

        return create_law_efficiency_scatter(df)

    except Exception as e:
        logger.error(f"Error loading law efficiency: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("match-law-cumulative", "figure"),
    Input("match-selector", "value"),
)
def update_law_cumulative(match_id: Optional[int]) -> go.Figure:
    """Update cumulative law count chart.

    Args:
        match_id: Selected match ID

    Returns:
        Plotly figure with cumulative line chart
    """
    if not match_id:
        return create_empty_chart_placeholder("Select a match")

    try:
        queries = get_queries()
        df = queries.get_cumulative_law_count_by_turn(match_id)

        if df.empty:
            return create_empty_chart_placeholder("No law data for this match")

        return create_cumulative_law_count_chart(df)

    except Exception as e:
        logger.error(f"Error loading cumulative law count: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")
```

**Test manually**, then commit:

```bash
git add tournament_visualizer/pages/matches.py
git commit -m "feat: Add efficiency scatter and cumulative count to Technology tab

- Add efficiency scatter showing all matches data
- Add cumulative count showing current match progression
- Position charts side-by-side
- Complete all 6 law progression visualizations"
```

---

### Phase 5: Testing & Polish (2-3 hours)

Final testing, documentation, and cleanup.

---

#### Task 5.1: Run Full Test Suite

**Goal:** Ensure all tests pass

```bash
# Run all tests
uv run pytest -v

# Run only law progression tests
uv run pytest tests/test_charts_law_progression.py -v

# Run with coverage
uv run pytest --cov=tournament_visualizer tests/test_charts_law_progression.py
```

**Expected output:** All tests pass ✅

**If tests fail:**
1. Read the error message carefully
2. Check the specific test that failed
3. Debug the implementation
4. Re-run tests

**Commit any fixes:**
```bash
git add <fixed-files>
git commit -m "fix: <description of what was fixed>"
```

---

#### Task 5.2: Code Formatting and Linting

**Goal:** Ensure code follows project standards

```bash
# Format code
uv run black tournament_visualizer/ tests/

# Check linting
uv run ruff check tournament_visualizer/ tests/

# Auto-fix linting issues
uv run ruff check --fix tournament_visualizer/ tests/
```

**Commit if changes were made:**
```bash
git add tournament_visualizer/ tests/
git commit -m "chore: Format code with black and fix linting issues"
```

---

#### Task 5.3: Manual Testing Checklist

**Goal:** Verify all visualizations work correctly in the browser

**Test procedure:**

1. Start the server: `uv run python manage.py start`
2. Open browser to http://localhost:8050
3. Navigate to **Matches** page
4. Select a match from the dropdown
5. Click **Technology & Research** tab
6. Scroll down to **Law Progression Analysis** section

**For each visualization, check:**

- [ ] **Match Comparison**
  - [ ] Chart displays with correct data
  - [ ] Bars show for both players
  - [ ] Missing bars when player didn't reach milestone
  - [ ] Hover tooltips work
  - [ ] Annotation about missing bars is visible

- [ ] **Race Timeline**
  - [ ] Timeline displays with correct turn range
  - [ ] Markers show at correct turns
  - [ ] Different symbols for 4-law (circle) and 7-law (star)
  - [ ] Lines connect milestones
  - [ ] Player names on Y-axis

- [ ] **Distribution (All Matches)**
  - [ ] Box plots display
  - [ ] Statistics annotation shows
  - [ ] Whiskers and boxes render correctly
  - [ ] Same data regardless of selected match

- [ ] **Heatmap (All Matches)**
  - [ ] Heatmap renders with color coding
  - [ ] Players on Y-axis, matches on X-axis
  - [ ] Color legend shows (< 4 laws, 4 laws, 7 laws)
  - [ ] Hover shows match and player details

- [ ] **Efficiency Scatter (All Matches)**
  - [ ] Scatter points display
  - [ ] Player names visible
  - [ ] Trendline shows
  - [ ] Quadrant annotations visible
  - [ ] Colored by civilization

- [ ] **Cumulative Count (This Match)**
  - [ ] Lines show progression over time
  - [ ] Reference lines at 4 and 7 laws
  - [ ] Starts at turn 0 with 0 laws
  - [ ] Markers on line
  - [ ] Legend shows player names

**Test edge cases:**

- [ ] Select a match with only 1 player reaching milestones
- [ ] Select a match where no one reached 4 laws
- [ ] Try all different matches in dropdown
- [ ] Check that page doesn't crash with any selection

**Record any bugs found:**

If you find bugs, create a checklist:
```
Bugs found:
- [ ] Chart X doesn't handle NULL values correctly (fix in ...)
- [ ] Chart Y has wrong colors (fix in ...)
```

---

#### Task 5.4: Update Documentation

**Goal:** Document the new features

**File to update:** `README.md`

**Add this section** (find the appropriate place in the README):

```markdown
### Law Progression Visualizations

The **Technology & Research** tab on the Matches page includes comprehensive law progression analysis:

1. **Law Milestone Timing** - Compare when each player reached 4 and 7 law milestones
2. **Law Milestone Timeline** - Horizontal timeline showing progression race
3. **Milestone Timing Distribution** - Box plots showing typical timing across all matches
4. **Player Performance Heatmap** - Color-coded matrix showing performance by player and match
5. **Law Progression Efficiency** - Scatter plot analyzing speed to milestones
6. **Cumulative Law Count Race** - Line chart showing turn-by-turn progression

**Key Insights:**
- Only ~64% of players reach 4 laws
- Only ~29% of players reach 7 laws
- Average turn to 4 laws: ~45 turns
- Average turn to 7 laws: ~71 turns
```

**Commit:**
```bash
git add README.md
git commit -m "docs: Document law progression visualizations

- Add section describing all 6 visualizations
- Include key statistics about law progression
- Explain where to find the visualizations in the UI"
```

---

#### Task 5.5: Create Implementation Summary

**Goal:** Document what was done for future reference

**File to create:** `docs/plans/law-progression-visualizations-summary.md`

```markdown
# Law Progression Visualizations - Implementation Summary

**Completed:** 2025-10-08

## What Was Built

Added 6 law progression visualizations to the Technology & Research tab:

1. Match Comparison (grouped bar chart)
2. Race Timeline (horizontal scatter plot)
3. Distribution Analysis (box plots)
4. Player Performance Heatmap (heatmap)
5. Efficiency Scatter (scatter plot with trendline)
6. Cumulative Law Count (line chart)

## Files Modified

- `tournament_visualizer/components/charts.py` - Added 6 chart creation functions
- `tournament_visualizer/pages/matches.py` - Added charts to Technology tab and callbacks
- `tournament_visualizer/data/queries.py` - Added `get_cumulative_law_count_by_turn()`
- `tests/test_charts_law_progression.py` - Added comprehensive tests (NEW FILE)
- `README.md` - Documented new features

## Commits

Total commits: ~18
- Setup and infrastructure: 3
- Visualization #1 (Match Comparison): 3
- Visualization #2 (Timeline): 3
- Visualizations #3-4 (Distribution & Heatmap): 4
- Visualizations #5-6 (Scatter & Cumulative): 5
- Testing and polish: 3

## Testing

- 25+ unit tests covering all chart functions
- Manual testing completed for all edge cases
- Code formatted and linted

## Key Learnings

- Using `ROW_NUMBER()` window function for milestone calculation
- Handling NULL values in Plotly (use `pd.NA` and `astype("Int64")`)
- Creating color-coded heatmaps with custom colorscales
- Adding reference lines and annotations for context

## Success Metrics

✅ All 6 visualizations implemented
✅ All tests passing
✅ Code formatted and linted
✅ Documentation updated
✅ Manual testing completed
```

**Commit:**
```bash
git add docs/plans/law-progression-visualizations-summary.md
git commit -m "docs: Add implementation summary

- Document all files modified
- List all visualizations created
- Record commit count and testing status
- Note key learnings for future reference"
```

---

## Testing Strategy

### Test Structure

All tests follow this pattern:

```python
class TestChartName:
    """Tests for specific chart."""

    def test_returns_figure(self, fixture):
        """Most basic test - does it return a Figure?"""

    def test_handles_empty_data(self, empty_fixture):
        """Does it handle empty DataFrames?"""

    def test_chart_structure(self, fixture):
        """Does it have the right trace types?"""

    def test_edge_case(self, fixture):
        """Does it handle unusual data?"""
```

### Test Data Strategy

**Use fixtures for reusability:**
```python
@pytest.fixture
def sample_data() -> pd.DataFrame:
    """Realistic sample data."""
    return pd.DataFrame({...})
```

**Fixtures we need:**
- `sample_match_data` - Single match, 2 players
- `sample_all_matches_data` - Multiple matches
- `sample_cumulative_data` - Turn-by-turn progression
- `empty_data` - Empty DataFrame with correct schema

### What to Test

**✅ DO test:**
- Function returns correct type (`go.Figure`)
- Chart handles empty data
- Chart has expected number of traces
- Chart has title and axis labels
- Chart handles NULL values

**❌ DON'T test:**
- Exact pixel positions
- Specific color hex codes (test that colors exist)
- Plotly internals
- Database queries (tested separately)

---

## Success Criteria

### Definition of Done

All of these must be true:

- [ ] All 6 visualizations are implemented
- [ ] All visualizations appear in the Technology & Research tab
- [ ] All tests pass (`uv run pytest -v`)
- [ ] Code is formatted (`uv run black ...`)
- [ ] Code is linted (`uv run ruff check ...`)
- [ ] Manual testing completed (checklist in Task 5.3)
- [ ] Documentation updated (README.md)
- [ ] Implementation summary created

### Quality Metrics

- **Test Coverage:** >90% for new chart functions
- **Commits:** ~18 atomic commits following guidelines
- **Code Quality:** No linting errors or warnings
- **Performance:** All charts render in <2 seconds

### User Acceptance

When complete, a user should be able to:
1. Select any match from the dropdown
2. Navigate to Technology & Research tab
3. See all 6 law progression visualizations
4. Interact with charts (hover, zoom, etc.)
5. Understand when players reached law milestones
6. Compare performance across matches

---

## Troubleshooting

### Common Issues

**Issue: "ImportError: cannot import name 'create_..._chart'"**
- **Cause:** Function not yet implemented
- **Fix:** Implement the function in `charts.py` first

**Issue: "KeyError: 'turn_to_4_laws'"**
- **Cause:** DataFrame doesn't have expected columns
- **Fix:** Check query returns correct columns

**Issue: Chart shows "No data available"**
- **Cause:** Empty DataFrame or all NULL values
- **Fix:** Check query logic, verify events table has `LAW_ADOPTED` events

**Issue: Tests fail with "AssertionError: expected X, got Y"**
- **Cause:** Implementation doesn't match test expectations
- **Fix:** Read test carefully, update implementation

**Issue: Callback not triggering**
- **Cause:** Callback ID doesn't match layout ID
- **Fix:** Ensure `Output("chart-id", ...)` matches `id="chart-id"` in layout

### Debugging Tips

**Print data in callback:**
```python
@callback(...)
def update_chart(match_id):
    df = queries.get_law_progression_by_match(match_id)
    print(f"Data shape: {df.shape}")
    print(df.head())
    return create_chart(df)
```

**Test chart function independently:**
```python
# In Python REPL
from tournament_visualizer.data.database import get_database
from tournament_visualizer.data.queries import TournamentQueries
from tournament_visualizer.components.charts import create_law_milestone_comparison_chart

queries = TournamentQueries(get_database())
df = queries.get_law_progression_by_match(10)
fig = create_law_milestone_comparison_chart(df)
fig.show()  # Opens in browser
```

**Check browser console:**
- Open browser DevTools (F12)
- Look for JavaScript errors
- Check Network tab for failed requests

---

## Glossary

**Terms used in this plan:**

- **Milestone:** Reaching 4 or 7 laws (important strategic thresholds)
- **Turn:** A game turn (one unit of game time)
- **Fixture:** Test data (pytest terminology)
- **Trace:** A data series in a Plotly chart (e.g., one line, one bar group)
- **Callback:** Dash function that updates UI when inputs change
- **Layout:** Dash UI structure (HTML/components)
- **ROW_NUMBER():** SQL window function that numbers rows sequentially
- **NULL/NA:** Missing data (player didn't reach that milestone)

---

## Next Steps After Completion

Once all 6 visualizations are complete:

1. **User Feedback:** Share with users, collect feedback
2. **Iteration:** Based on feedback, consider:
   - Adding filters (by civilization, map type, etc.)
   - Adding more visualizations (law types, law timing vs win rate, etc.)
   - Exporting data to CSV
3. **Performance:** If charts are slow with large datasets:
   - Add caching
   - Pre-compute statistics
   - Limit data shown

---

## Questions?

If you get stuck:

1. **Re-read this plan** - The answer is probably here
2. **Check existing code** - Look at how other charts are implemented
3. **Read test error messages** - They often tell you exactly what's wrong
4. **Test in isolation** - Use Python REPL to test chart functions directly
5. **Check browser console** - Look for JavaScript errors

Remember:
- **TDD:** Write tests first
- **DRY:** Copy patterns from existing charts
- **YAGNI:** Only implement what's specified
- **Commit often:** Every 30-60 minutes of work
