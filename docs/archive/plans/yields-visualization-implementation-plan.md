# Yields Visualization Implementation Plan

> **Status**: Completed and archived (2025-10-25)
>
> Charts implemented and working in app. See CLAUDE.md (Dashboard & Chart Conventions section).

## Overview

**Goal**: Add comprehensive yield tracking visualizations to the Match Details page, displaying all 14 yield types (Food, Growth, Science, Culture, etc.) as line charts showing progression over time.

**Current State**: Only Food yields are displayed (single chart)

**Target State**: All 14 yield types displayed in a scrollable 2-column grid

**Complexity**: Low - straightforward refactoring task

**Estimated Time**: 2-3 hours

---

## Background Context

### What are "Yields" in Old World?

Yields are per-turn production rates for various resources in the game:
- **Population**: Food, Growth
- **Progress**: Science, Culture, Civics, Training
- **Resources**: Iron, Stone, Wood
- **Economy**: Money, Orders, Maintenance
- **Stability**: Happiness, Discontent

Players need to track how these yields change over time to understand their economic development and compare against opponents.

### Current Implementation

**File**: `tournament_visualizer/pages/matches.py`
- Line 461-480: Yields tab definition (only contains Food chart placeholder)
- Line 1413-1451: `update_food_yields_chart()` callback (Food-only implementation)

**File**: `tournament_visualizer/components/charts.py`
- Line 2272-2367: `create_food_yields_chart()` function (Food-specific)

**Database**:
- Table: `player_yield_history`
- Columns: `match_id`, `player_id`, `turn_number`, `resource_type`, `amount`
- 14 yield types: `YIELD_FOOD`, `YIELD_GROWTH`, `YIELD_SCIENCE`, etc.
- ~1,800 rows per yield type across all matches

### Why Simple Implementation Works

**Data Volume Analysis**:
- Worst case: 108 turns × 2 players × 14 yields = 3,024 chart points
- Modern browsers handle 10K+ Plotly points easily
- DuckDB queries 25K rows in < 10ms
- **Conclusion**: No need for lazy loading, pagination, or complex optimizations

---

## Architecture Decisions

### ✅ Approved Approach: Single Query + Multiple Charts

**Pattern**: One database query fetches ALL yield data, then we create 14 separate charts from the same DataFrame.

**Why this approach?**
- **DRY**: Reuse one generic chart function for all 14 yields
- **Performance**: Single query is faster than 14 separate queries
- **Maintainability**: One function to test and update
- **Simple**: Easy to understand and debug

**Rejected alternatives**:
- ❌ 14 separate callbacks: Wasteful queries, hard to maintain
- ❌ Lazy loading with accordions: Over-engineering for small dataset
- ❌ Dropdown selector: Worse UX (users want to see all at once)

---

## Implementation Plan

Follow these tasks **in order**. Commit after completing each task.

---

### Task 1: Create Generic Yield Chart Function

**Objective**: Refactor `create_food_yields_chart()` into a reusable `create_yield_chart()` function that works for any yield type.

**Files to modify**:
- `tournament_visualizer/components/charts.py`

**Steps**:

1. **Read the existing implementation** to understand the pattern:
   ```bash
   # Look at the Food yields implementation
   # File: tournament_visualizer/components/charts.py
   # Lines: 2272-2367
   ```

2. **Create the new generic function** (add after `create_food_yields_chart()`):

```python
def create_yield_chart(
    df: pd.DataFrame,
    total_turns: Optional[int] = None,
    yield_type: str = "YIELD_FOOD",
    display_name: Optional[str] = None
) -> go.Figure:
    """Create a line chart showing yield production over time.

    Generic function that works for any yield type (Food, Science, Culture, etc.).
    Shows yield production per turn for each player, making it easy to compare
    yield economy development throughout the match.

    Args:
        df: DataFrame with columns: player_name, turn_number, amount, resource_type
            (from get_yield_history_by_match() filtered to specific yield type)
        total_turns: Optional total turns in the match to extend lines to the end
        yield_type: The yield type being displayed (e.g., "YIELD_FOOD", "YIELD_SCIENCE")
                   Used for validation and error messages
        display_name: Optional human-readable name for the yield (e.g., "Food", "Science")
                     If not provided, derives from yield_type (removes YIELD_ prefix)

    Returns:
        Plotly figure with line chart

    Example:
        >>> df = queries.get_yield_history_by_match(match_id=1, yield_types=["YIELD_SCIENCE"])
        >>> fig = create_yield_chart(df, total_turns=100, yield_type="YIELD_SCIENCE", display_name="Science")
    """
    # Derive display name if not provided
    if display_name is None:
        display_name = yield_type.replace("YIELD_", "").replace("_", " ").title()

    if df.empty:
        return create_empty_chart_placeholder(
            f"No {display_name} yield data available for this match"
        )

    fig = create_base_figure(
        title="",
        x_title="Turn Number",
        y_title=f"{display_name} Yield",
        height=400,
    )

    # Add a line for each player
    players = df["player_name"].unique()

    for i, player in enumerate(players):
        player_data = df[df["player_name"] == player].sort_values("turn_number")

        # Get turn and yield data
        turns = player_data["turn_number"].tolist()
        yields = player_data["amount"].tolist()

        # Create hover text
        hover_texts = [
            f"<b>{player}</b><br>Turn {turn}: {yield_val} {display_name.lower()}"
            for turn, yield_val in zip(turns, yields)
        ]

        # Extend line to match end if total_turns provided
        if total_turns and turns and turns[-1] < total_turns:
            turns.append(total_turns)
            yields.append(yields[-1])  # Keep final yield value
            hover_texts.append(hover_texts[-1])  # Reuse last hover text

        # Assign last trace to yaxis2 to make right-side labels visible
        yaxis_ref = "y2" if i == len(players) - 1 else "y"

        fig.add_trace(
            go.Scatter(
                x=turns,
                y=yields,
                mode="lines+markers",
                name=player,
                line=dict(
                    color=Config.PRIMARY_COLORS[i % len(Config.PRIMARY_COLORS)],
                    width=4,
                ),
                marker=dict(size=8),
                hoveron='points',  # Only trigger hover on marker points, not lines
                hovertemplate="%{hovertext}<extra></extra>",
                hovertext=hover_texts,
                yaxis=yaxis_ref,
            )
        )

    # Calculate the maximum yield to set appropriate y-axis range
    max_yield = int(df["amount"].max()) if not df.empty else 100
    y_range = [0, max_yield + 20]  # Add some padding at the top

    # Set Y-axis with labels on both left and right sides
    fig.update_layout(
        yaxis=dict(
            range=y_range,
            showgrid=True,
            ticks="outside",
        ),
        yaxis2=dict(
            overlaying="y",
            side="right",
            range=y_range,
            showticklabels=True,
            ticks="outside",
            showgrid=False,
        ),
        hovermode='closest',  # Explicitly set hover mode
        hoverdistance=100,  # Increase hover detection distance (default is 20)
    )

    return fig
```

3. **Update the existing Food chart function** to use the new generic function:

```python
def create_food_yields_chart(
    df: pd.DataFrame, total_turns: Optional[int] = None
) -> go.Figure:
    """Create a line chart showing food yields over time.

    DEPRECATED: Use create_yield_chart() instead. Kept for backward compatibility.

    Args:
        df: DataFrame with columns: player_name, turn_number, amount
            (from get_yield_history_by_match() filtered to YIELD_FOOD)
        total_turns: Optional total turns in the match to extend lines to the end

    Returns:
        Plotly figure with line chart
    """
    return create_yield_chart(df, total_turns, yield_type="YIELD_FOOD", display_name="Food")
```

**Why keep the old function?**
- Backward compatibility - don't break existing code
- Clear deprecation path for future cleanup
- Following YAGNI - only remove when actually needed

**Testing** (manual for now, we'll write unit tests later):

```bash
# Start the dev server
uv run python manage.py restart

# Navigate to: http://localhost:8050/matches
# Select any match
# Go to Yields tab
# Verify Food chart still works correctly
```

**Commit**:
```bash
git add tournament_visualizer/components/charts.py
git commit -m "refactor: Extract generic create_yield_chart function

- Add create_yield_chart() accepting yield_type and display_name params
- Refactor create_food_yields_chart() to use new generic function
- Maintains backward compatibility
- Prepares for adding 13 additional yield charts"
```

---

### Task 2: Update Yields Tab Layout

**Objective**: Modify the Yields tab to display all 14 yield types in a 2-column grid layout.

**Files to modify**:
- `tournament_visualizer/pages/matches.py`

**Steps**:

1. **Define yield types constant** (add near top of file, after imports):

```python
# Add after line 36 (after logger initialization)

# All 14 yield types tracked in Old World
YIELD_TYPES = [
    ("YIELD_FOOD", "Food"),
    ("YIELD_GROWTH", "Growth"),
    ("YIELD_SCIENCE", "Science"),
    ("YIELD_CULTURE", "Culture"),
    ("YIELD_CIVICS", "Civics"),
    ("YIELD_TRAINING", "Training"),
    ("YIELD_MONEY", "Money"),
    ("YIELD_ORDERS", "Orders"),
    ("YIELD_HAPPINESS", "Happiness"),
    ("YIELD_DISCONTENT", "Discontent"),
    ("YIELD_IRON", "Iron"),
    ("YIELD_STONE", "Stone"),
    ("YIELD_WOOD", "Wood"),
    ("YIELD_MAINTENANCE", "Maintenance"),
]
```

**Why this format?**
- Tuple of (database_name, display_name) for each yield
- Order matters: grouped logically (population, progress, resources, economy, stability)
- Makes it easy to iterate and create charts programmatically

2. **Replace the Yields tab content** (find around line 461-480, replace the entire "Yields" tab definition):

```python
{
    "label": "Yields",
    "tab_id": "yields",
    "content": [
        # Generate rows of charts dynamically
        # Each row contains 2 charts side-by-side
        *[
            dbc.Row(
                [
                    dbc.Col(
                        [
                            create_chart_card(
                                title=YIELD_TYPES[i][1],  # Display name
                                chart_id=f"match-{YIELD_TYPES[i][0].lower().replace('_', '-')}-chart",
                                height="400px",
                            )
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            create_chart_card(
                                title=YIELD_TYPES[i + 1][1] if i + 1 < len(YIELD_TYPES) else "",
                                chart_id=f"match-{YIELD_TYPES[i + 1][0].lower().replace('_', '-')}-chart" if i + 1 < len(YIELD_TYPES) else "match-empty-chart",
                                height="400px",
                            )
                        ],
                        width=6,
                    ) if i + 1 < len(YIELD_TYPES) else dbc.Col(width=6),  # Empty column if odd number
                ],
                className="mb-3",
            )
            for i in range(0, len(YIELD_TYPES), 2)  # Step by 2 to create pairs
        ],
    ],
},
```

**Why this layout?**
- **2-column grid**: Efficient use of screen space, easy to compare adjacent yields
- **Dynamic generation**: Use list comprehension to avoid repeating 14 times
- **Responsive**: Bootstrap columns automatically stack on mobile
- **Consistent spacing**: `mb-3` class adds margin between rows

**Understanding the code**:
- `*[...]` unpacks the list directly into the content array
- `range(0, len(YIELD_TYPES), 2)` creates pairs: (0,1), (2,3), (4,5), etc.
- `if i + 1 < len(YIELD_TYPES)` handles odd-numbered totals gracefully
- Chart IDs follow pattern: `match-yield-food-chart`, `match-yield-science-chart`, etc.

**Testing**:
```bash
# Restart server
uv run python manage.py restart

# Navigate to Yields tab
# You should see 14 empty chart placeholders in 2 columns
# They won't have data yet (that's next task)
```

**Commit**:
```bash
git add tournament_visualizer/pages/matches.py
git commit -m "feat: Add layout for all 14 yield charts

- Define YIELD_TYPES constant with all 14 yield types
- Generate 2-column grid layout dynamically
- Create chart placeholders for all yields
- Prepares for callback implementation"
```

---

### Task 3: Implement Single Callback for All Yield Charts

**Objective**: Create one callback that fetches all yield data and populates all 14 charts.

**Files to modify**:
- `tournament_visualizer/pages/matches.py`

**Steps**:

1. **Remove the old Food-only callback** (delete the `update_food_yields_chart` function around line 1413-1451)

2. **Add the new comprehensive callback** (add in the same location):

```python
@callback(
    # Generate outputs for all 14 yield charts dynamically
    [
        Output(f"match-{yield_type.lower().replace('_', '-')}-chart", "figure")
        for yield_type, _ in YIELD_TYPES
    ],
    Input("match-selector", "value"),
)
def update_all_yield_charts(match_id: Optional[int]) -> List[go.Figure]:
    """Update all yield charts when a match is selected.

    Fetches data for all 14 yield types in a single query and creates
    individual charts for each yield type.

    Args:
        match_id: Selected match ID

    Returns:
        List of 14 Plotly figures (one for each yield type)
    """
    # If no match selected, return empty placeholders for all charts
    if not match_id:
        return [
            create_empty_chart_placeholder(f"Select a match to view {display_name} yields")
            for _, display_name in YIELD_TYPES
        ]

    try:
        queries = get_queries()

        # SINGLE query fetches ALL yield data for the match
        all_yields_df = queries.get_yield_history_by_match(match_id)

        if all_yields_df.empty:
            return [
                create_empty_chart_placeholder(f"No {display_name} yield data available")
                for _, display_name in YIELD_TYPES
            ]

        # Get total turns for the match to extend chart lines
        match_df = queries.get_match_summary()
        match_info = match_df[match_df["match_id"] == match_id]
        total_turns = (
            match_info.iloc[0]["total_turns"] if not match_info.empty else None
        )

        # Create all 14 charts from the same DataFrame
        charts = []
        for yield_type, display_name in YIELD_TYPES:
            # Filter to this specific yield type
            df_yield = all_yields_df[all_yields_df["resource_type"] == yield_type]

            # Create chart using generic function
            chart = create_yield_chart(
                df_yield,
                total_turns=total_turns,
                yield_type=yield_type,
                display_name=display_name
            )
            charts.append(chart)

        return charts

    except Exception as e:
        logger.error(f"Error loading yield charts: {e}")
        # Return error charts for all yields
        return [
            create_empty_chart_placeholder(f"Error loading {display_name} yields: {str(e)}")
            for _, display_name in YIELD_TYPES
        ]
```

**Why this approach?**
- **Single query**: Fetch all yields at once (fast, efficient)
- **Dynamic outputs**: Generate output list using list comprehension
- **Error handling**: Gracefully handle missing data or errors
- **Consistent**: Same pattern as other callbacks in the file

**Understanding the callback**:
1. Input: Match selection changes → triggers callback
2. Validation: If no match selected → return 14 empty placeholders
3. Query: Single database call for ALL yields
4. Filter: Loop through yield types, filter DataFrame for each
5. Create: Call generic `create_yield_chart()` for each yield
6. Return: List of 14 figures (Dash matches by position to outputs)

**Testing**:
```bash
# Restart server
uv run python manage.py restart

# Navigate to: http://localhost:8050/matches
# Select any match
# Go to Yields tab
# Verify all 14 charts display with data
# Check hover tooltips work
# Verify player colors are consistent
# Verify lines extend to end of match
```

**Manual test checklist**:
- [ ] All 14 charts render without errors
- [ ] Each chart shows correct yield type in title
- [ ] Player names appear in legend
- [ ] Hover shows correct turn number and yield value
- [ ] Lines extend to final turn of match
- [ ] Y-axis scales appropriately for each yield
- [ ] Charts scroll smoothly on page
- [ ] Selecting different matches updates all charts
- [ ] Empty state shows when no data available

**Commit**:
```bash
git add tournament_visualizer/pages/matches.py
git commit -m "feat: Implement single callback for all yield charts

- Remove old update_food_yields_chart callback
- Add update_all_yield_charts with dynamic outputs
- Single query fetches all yields efficiently
- Creates 14 charts from same DataFrame
- Handles errors and empty states gracefully"
```

---

### Task 4: Update Imports

**Objective**: Ensure all necessary chart functions are imported.

**Files to modify**:
- `tournament_visualizer/pages/matches.py`

**Steps**:

1. **Update the import from charts.py** (find around line 16-23, update to include new function):

```python
from tournament_visualizer.components.charts import (
    create_cumulative_law_count_chart,
    create_cumulative_tech_count_chart,
    create_empty_chart_placeholder,
    create_food_yields_chart,  # Keep for backward compat (currently unused)
    create_yield_chart,  # NEW: Generic yield chart function
    create_statistics_grouped_bar,
    create_statistics_radar_chart,
)
```

**Testing**:
```bash
# Check for import errors
uv run python -c "from tournament_visualizer.pages.matches import *"

# Should complete without errors
```

**Commit**:
```bash
git add tournament_visualizer/pages/matches.py
git commit -m "chore: Update chart imports

- Add create_yield_chart to imports
- Keep create_food_yields_chart for backward compatibility"
```

---

### Task 5: Write Unit Tests

**Objective**: Add automated tests to prevent regressions.

**Files to modify**:
- `tests/test_charts.py` (create if doesn't exist)

**Steps**:

1. **Check if test file exists**:
```bash
ls tests/test_charts.py
# If doesn't exist, create it
```

2. **Create or update test file**:

```python
"""Unit tests for chart generation functions."""

import pandas as pd
import pytest
from plotly.graph_objects import Figure

from tournament_visualizer.components.charts import (
    create_empty_chart_placeholder,
    create_yield_chart,
)


class TestYieldCharts:
    """Tests for yield chart generation."""

    @pytest.fixture
    def sample_yield_data(self) -> pd.DataFrame:
        """Create sample yield data for testing.

        Simulates data from get_yield_history_by_match() with 2 players
        over 10 turns for a single yield type.
        """
        return pd.DataFrame({
            "player_id": [1, 1, 1, 1, 1, 2, 2, 2, 2, 2],
            "player_name": ["Alice", "Alice", "Alice", "Alice", "Alice",
                           "Bob", "Bob", "Bob", "Bob", "Bob"],
            "civilization": ["Rome", "Rome", "Rome", "Rome", "Rome",
                           "Egypt", "Egypt", "Egypt", "Egypt", "Egypt"],
            "turn_number": [1, 2, 3, 4, 5, 1, 2, 3, 4, 5],
            "resource_type": ["YIELD_FOOD"] * 10,
            "amount": [10, 12, 15, 18, 20, 8, 10, 13, 16, 19],
        })

    def test_create_yield_chart_returns_figure(self, sample_yield_data: pd.DataFrame):
        """Test that create_yield_chart returns a Plotly Figure."""
        fig = create_yield_chart(
            sample_yield_data,
            total_turns=5,
            yield_type="YIELD_FOOD",
            display_name="Food"
        )

        assert isinstance(fig, Figure)
        assert fig is not None

    def test_create_yield_chart_with_empty_dataframe(self):
        """Test that empty DataFrame returns placeholder chart."""
        empty_df = pd.DataFrame(columns=["player_name", "turn_number", "amount", "resource_type"])

        fig = create_yield_chart(
            empty_df,
            total_turns=10,
            yield_type="YIELD_SCIENCE",
            display_name="Science"
        )

        assert isinstance(fig, Figure)
        # Placeholder charts have an annotation
        assert len(fig.layout.annotations) > 0
        assert "Science" in fig.layout.annotations[0].text

    def test_create_yield_chart_has_correct_traces(self, sample_yield_data: pd.DataFrame):
        """Test that chart has one trace per player."""
        fig = create_yield_chart(
            sample_yield_data,
            total_turns=5,
            yield_type="YIELD_FOOD",
            display_name="Food"
        )

        # Should have 2 traces (one for Alice, one for Bob)
        assert len(fig.data) == 2

        # Check player names in traces
        trace_names = {trace.name for trace in fig.data}
        assert trace_names == {"Alice", "Bob"}

    def test_create_yield_chart_extends_to_total_turns(self, sample_yield_data: pd.DataFrame):
        """Test that chart lines extend to total_turns when provided."""
        # Data only goes to turn 5, but match goes to turn 10
        fig = create_yield_chart(
            sample_yield_data,
            total_turns=10,  # Extend to turn 10
            yield_type="YIELD_FOOD",
            display_name="Food"
        )

        # Each trace should have data points extending to turn 10
        for trace in fig.data:
            max_turn = max(trace.x)
            assert max_turn == 10, f"Expected max turn 10, got {max_turn}"

    def test_create_yield_chart_derives_display_name(self, sample_yield_data: pd.DataFrame):
        """Test that display name is derived from yield_type if not provided."""
        fig = create_yield_chart(
            sample_yield_data,
            total_turns=5,
            yield_type="YIELD_SCIENCE",
            display_name=None  # Let function derive name
        )

        # Check Y-axis title contains derived name
        assert "Science" in fig.layout.yaxis.title.text

    def test_create_yield_chart_with_all_yield_types(self, sample_yield_data: pd.DataFrame):
        """Test that chart works for all 14 yield types."""
        yield_types = [
            "YIELD_FOOD", "YIELD_GROWTH", "YIELD_SCIENCE", "YIELD_CULTURE",
            "YIELD_CIVICS", "YIELD_TRAINING", "YIELD_MONEY", "YIELD_ORDERS",
            "YIELD_HAPPINESS", "YIELD_DISCONTENT", "YIELD_IRON", "YIELD_STONE",
            "YIELD_WOOD", "YIELD_MAINTENANCE"
        ]

        for yield_type in yield_types:
            # Update resource_type in test data
            test_df = sample_yield_data.copy()
            test_df["resource_type"] = yield_type

            fig = create_yield_chart(
                test_df,
                total_turns=5,
                yield_type=yield_type,
                display_name=None
            )

            assert isinstance(fig, Figure), f"Failed for {yield_type}"
            assert len(fig.data) == 2, f"Wrong trace count for {yield_type}"

    def test_create_yield_chart_y_axis_range(self, sample_yield_data: pd.DataFrame):
        """Test that Y-axis range includes all data with padding."""
        fig = create_yield_chart(
            sample_yield_data,
            total_turns=5,
            yield_type="YIELD_FOOD",
            display_name="Food"
        )

        # Max amount in sample data is 20
        # Y-axis should have range [0, max + 20 padding]
        assert fig.layout.yaxis.range[0] == 0
        assert fig.layout.yaxis.range[1] >= 20  # At least max value
        assert fig.layout.yaxis.range[1] <= 100  # Reasonable upper bound

    def test_create_yield_chart_hover_text(self, sample_yield_data: pd.DataFrame):
        """Test that hover text contains player name and turn info."""
        fig = create_yield_chart(
            sample_yield_data,
            total_turns=5,
            yield_type="YIELD_FOOD",
            display_name="Food"
        )

        # Check first trace (Alice)
        alice_trace = [t for t in fig.data if t.name == "Alice"][0]

        # Hover text should mention player and have turn info
        assert len(alice_trace.hovertext) > 0
        assert "Alice" in alice_trace.hovertext[0]
        assert "Turn" in alice_trace.hovertext[0]


class TestEmptyChartPlaceholder:
    """Tests for empty chart placeholder function."""

    def test_returns_figure(self):
        """Test that placeholder returns a Figure."""
        fig = create_empty_chart_placeholder("Test message")
        assert isinstance(fig, Figure)

    def test_contains_message(self):
        """Test that placeholder contains the provided message."""
        message = "No data available for testing"
        fig = create_empty_chart_placeholder(message)

        # Message should be in annotations
        assert len(fig.layout.annotations) > 0
        assert message in fig.layout.annotations[0].text
```

**Understanding the tests**:

**Test Categories**:
1. **Happy path**: Normal data → chart renders correctly
2. **Edge cases**: Empty data, missing params, extreme values
3. **Integration**: Works with all 14 yield types
4. **UI details**: Hover text, axis ranges, labels

**Fixtures**:
- `sample_yield_data`: Reusable test data (DRY principle)
- Simulates 2 players over 5 turns
- Realistic structure matching database output

**Test design principles**:
- **One assertion per test**: Tests should fail for only one reason
- **Descriptive names**: `test_create_yield_chart_extends_to_total_turns` tells you exactly what it tests
- **Arrange-Act-Assert**: Set up data → call function → verify result
- **Fast**: No database calls, no network requests

3. **Run the tests**:

```bash
# Run just the chart tests
uv run pytest tests/test_charts.py -v

# Run with coverage
uv run pytest tests/test_charts.py --cov=tournament_visualizer.components.charts

# Expected output: All tests pass
```

**If tests fail**:
1. Read the error message carefully
2. Check which assertion failed
3. Use `pytest -v` for verbose output
4. Add `print()` statements in the test to debug
5. Run single test: `pytest tests/test_charts.py::TestYieldCharts::test_name -v`

**Commit**:
```bash
git add tests/test_charts.py
git commit -m "test: Add unit tests for yield chart functions

- Test create_yield_chart with sample data
- Test empty DataFrame handling
- Test all 14 yield types work correctly
- Test Y-axis range calculation
- Test hover text generation
- Test line extension to total_turns"
```

---

### Task 6: Manual Testing & Verification

**Objective**: Thoroughly test the implementation in a real browser.

**Test Plan**:

1. **Start the development server**:
```bash
uv run python manage.py restart
uv run python manage.py logs -f
# Watch for errors in logs
```

2. **Navigate to the application**:
```
http://localhost:8050/matches
```

3. **Test match selection**:
- [ ] Select match with shortest game (Match 6: 30 turns)
- [ ] Select match with longest game (Match 13: 108 turns)
- [ ] Select different matches rapidly - charts should update smoothly
- [ ] Deselect match - charts should show "Select a match" placeholder

4. **Test individual charts** (for one match):
- [ ] Food: Check values are reasonable (should be 10-100 range typically)
- [ ] Growth: Often low single digits
- [ ] Science: Should increase over time
- [ ] Culture: Should increase over time
- [ ] Money: Often highest yield
- [ ] Iron/Stone/Wood: Resource-dependent, may be 0 for some players
- [ ] Happiness: Usually 50-100 range
- [ ] Discontent: Lower is better, 0-30 range

5. **Test chart interactions**:
- [ ] Hover over data points - tooltip shows player, turn, value
- [ ] Hover over legend - highlights corresponding line
- [ ] Click legend item - toggles line visibility
- [ ] Zoom in on chart - works correctly
- [ ] Reset zoom (double-click) - works correctly

6. **Test layout**:
- [ ] Charts are in 2-column grid
- [ ] Charts align properly
- [ ] Page scrolls smoothly with 14 charts
- [ ] No horizontal scrollbar appears
- [ ] Mobile view (resize browser): Charts stack vertically

7. **Test performance**:
- [ ] Tab switch to Yields: < 1 second load time
- [ ] Switching matches: < 1 second update time
- [ ] No visible lag when scrolling
- [ ] Browser developer console: No errors

8. **Test error handling**:
- [ ] Navigate to Yields tab before selecting match - shows placeholder
- [ ] If database is empty: Should show "No data" message

**Performance benchmarking**:

```bash
# Open browser DevTools (F12)
# Go to Network tab
# Select a match and switch to Yields tab
# Check:
# - Number of requests: Should be 1-2 (just the callback)
# - Response time: Should be < 200ms
# - Payload size: Should be < 500KB

# Go to Performance tab
# Record while switching matches
# Check:
# - Frame rate stays > 30 FPS
# - No long tasks (> 50ms)
```

**Document any issues found**:

Create `docs/testing/yields-tab-test-results.md`:
```markdown
# Yields Tab Testing Results

**Date**: [Your date]
**Tester**: [Your name]
**Environment**: [Mac/Windows/Linux, Chrome/Firefox/Safari]

## Test Results

### Match Selection
- ✅ All matches load correctly
- ✅ Charts update when selection changes
- ❌ Issue: [Describe any problem]

### Chart Rendering
- ✅ All 14 charts display
- ✅ Data values look reasonable
- ❌ Issue: [Describe any problem]

### Performance
- Load time: [X] seconds
- Update time: [X] seconds
- Any lag: Yes/No

### Issues Found
1. [Issue description]
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
```

**Commit** (only if everything passes):
```bash
git add docs/testing/yields-tab-test-results.md
git commit -m "docs: Add manual testing results for yields tab

- Tested all 14 charts with multiple matches
- Verified performance meets requirements
- Confirmed no errors in browser console"
```

---

### Task 7: Documentation Updates

**Objective**: Update user-facing and developer documentation.

**Files to create/modify**:

1. **Update main developer guide** (`docs/developer-guide.md`):

Add section about yields visualization (find the "Visualizations" section or create it):

```markdown
### Yields Visualization

**Location**: `/matches` page → Yields tab

**Purpose**: Show turn-by-turn progression of all 14 yield types for each player in a match.

**Yield Types**:
- **Population**: Food, Growth - Drive city expansion
- **Progress**: Science, Culture, Civics, Training - Unlock technologies and civics
- **Resources**: Iron, Stone, Wood - Used for production
- **Economy**: Money, Orders - Finance and command military
- **Stability**: Happiness, Discontent - Affect legitimacy

**Implementation Details**:

- **Query**: Single `get_yield_history_by_match(match_id)` call fetches all yields
- **Callback**: `update_all_yield_charts()` in `pages/matches.py`
- **Chart Function**: `create_yield_chart()` in `components/charts.py` (generic, reusable)
- **Layout**: 2-column grid, 7 rows, scrollable
- **Performance**: ~3,000 data points max, renders in < 1 second

**Data Flow**:
1. User selects match → `match-selector` Input triggers
2. Callback queries `player_yield_history` table (25K rows total)
3. Filters DataFrame 14 times (once per yield type)
4. Creates 14 Plotly figures using `create_yield_chart()`
5. Returns list of figures → Dash updates all 14 chart divs

**Adding New Yield Types** (if game adds more):
1. Add to `YIELD_TYPES` constant in `pages/matches.py`
2. No other code changes needed (dynamic generation handles it)
3. Add test case in `tests/test_charts.py`
```

2. **Create a user guide** (`docs/user-guide.md`):

```markdown
# Tournament Visualizer User Guide

## Viewing Match Details

### Yields Tab

The Yields tab shows how each player's economy developed throughout the match.

**What are Yields?**

Yields are per-turn production rates for various resources:

- **Food** 🍖: Feeds population, enables city growth
- **Growth** 👶: Increases population directly
- **Science** 🔬: Unlocks new technologies
- **Culture** 🎭: Advances culture and unlocks great works
- **Civics** ⚖️: Unlocks new laws
- **Training** ⚔️: Trains military units faster
- **Money** 💰: Finances your empire
- **Orders** 📜: Commands military actions
- **Iron/Stone/Wood** ⛏️: Building materials
- **Happiness** 😊: Keeps population content
- **Discontent** 😠: Represents unrest (lower is better)
- **Maintenance** 💸: Upkeep costs (negative yield)

**How to Read the Charts**:

- **X-axis**: Turn number (1 to end of game)
- **Y-axis**: Yield amount (per turn production rate)
- **Lines**: Each player has a colored line
- **Hover**: See exact value at any turn

**Interpreting Patterns**:

- **Steadily increasing**: Good economic growth (common for Science, Culture)
- **Sudden spikes**: Built a wonder, captured a city, or completed a major project
- **Plateaus**: Economic stagnation, may indicate strategic shift
- **Diverging lines**: One player pulling ahead economically
- **Crossing lines**: Lead changes hands

**Example Analysis**:

If Player A has higher Food but lower Science than Player B:
- Player A focused on expansion (more cities)
- Player B focused on research (fewer but more developed cities)
```

3. **Update changelog** (`CHANGELOG.md` or create it):

```markdown
# Changelog

## [Unreleased]

### Added
- Comprehensive yields visualization with all 14 yield types
- Generic `create_yield_chart()` function for reusable chart generation
- Dynamic 2-column grid layout for yield charts
- Single-query optimization for fetching all yield data

### Changed
- Refactored `create_food_yields_chart()` to use generic `create_yield_chart()`
- Updated Yields tab to display all yield types instead of just Food

### Technical
- Added `YIELD_TYPES` constant for maintaining yield type list
- Implemented single callback pattern for efficiency
- Added comprehensive unit tests for yield chart generation
```

**Commit**:
```bash
git add docs/developer-guide.md docs/user-guide.md CHANGELOG.md
git commit -m "docs: Add documentation for yields visualization

- Add technical details to developer guide
- Add user guide explaining yield types and interpretation
- Update changelog with new features"
```

---

### Task 8: Code Review Self-Checklist

**Objective**: Review your own code before considering it done.

**Checklist**:

**Code Quality**:
- [ ] No hardcoded values (e.g., magic numbers like 14)
- [ ] All functions have docstrings
- [ ] Type hints on all function parameters and returns
- [ ] Variable names are descriptive (`yield_type` not `yt`)
- [ ] No commented-out code
- [ ] No `print()` statements (use `logger` instead)
- [ ] No `TODO` comments without issue numbers

**DRY Principle**:
- [ ] No duplicate code across yield chart implementations
- [ ] Generic function works for all 14 yield types
- [ ] Layout generation uses loops, not copy-paste
- [ ] Test fixtures reused across multiple tests

**YAGNI Principle**:
- [ ] No lazy loading (not needed for current data volume)
- [ ] No caching (premature optimization)
- [ ] No dropdown selectors (users want to see all)
- [ ] No pagination (14 charts fit on one page)

**Error Handling**:
- [ ] Empty DataFrame → placeholder chart
- [ ] No match selected → placeholder chart
- [ ] Database error → error message chart
- [ ] Missing columns → graceful failure with logging

**Testing**:
- [ ] Unit tests pass: `pytest tests/test_charts.py`
- [ ] Manual testing completed and documented
- [ ] All 14 yield types tested
- [ ] Edge cases covered (empty data, long matches, etc.)

**Performance**:
- [ ] Single query fetches all data (not 14 separate queries)
- [ ] Charts render in < 1 second
- [ ] No memory leaks (check browser DevTools Memory tab)
- [ ] No console errors

**Accessibility**:
- [ ] Hover tooltips provide context
- [ ] Color contrast is sufficient (use browser DevTools)
- [ ] Charts have descriptive titles
- [ ] Legend explains what lines mean

**Git Hygiene**:
- [ ] Each commit is atomic (one logical change)
- [ ] Commit messages follow conventional format
- [ ] No merge conflicts
- [ ] No files committed that should be in `.gitignore`

**Run final checks**:

```bash
# Code formatting
uv run black tournament_visualizer/
uv run ruff check tournament_visualizer/

# Type checking (if mypy is set up)
uv run mypy tournament_visualizer/components/charts.py tournament_visualizer/pages/matches.py

# All tests pass
uv run pytest -v

# No obvious performance issues
uv run python manage.py restart
# Load /matches page and test
```

**If any item fails**, fix it before moving to the next task.

---

### Task 9: Final Integration & Deployment Prep

**Objective**: Ensure the feature is production-ready.

**Steps**:

1. **Create a feature summary**:

```bash
# Review all commits for this feature
git log --oneline --grep="yield" --grep="chart" --all-match

# Should see commits from all previous tasks
```

2. **Test in production-like environment**:

```bash
# Stop dev server
uv run python manage.py stop

# Restart fresh
uv run python manage.py start

# Test as a new user would (clear browser cache)
# Open incognito window: http://localhost:8050/matches
```

3. **Performance validation**:

Open browser DevTools and record metrics:

```
Target Performance Metrics:
- Initial page load: < 2 seconds
- Tab switch to Yields: < 1 second
- Match selection update: < 500ms
- Scroll smoothness: 60 FPS
- Memory usage: < 100MB for 14 charts
```

4. **Create a demo script** (`docs/demos/yields-feature-demo.md`):

```markdown
# Yields Feature Demo Script

Use this script to demonstrate the new yields visualization feature.

## Setup
1. Start server: `uv run python manage.py start`
2. Open browser to: http://localhost:8050/matches
3. Select match: "Match 13" (longest game, shows best progression)

## Demo Flow

### 1. Overview (30 seconds)
"We've added comprehensive yield tracking. Instead of just Food, you now see all 14 yield types that Old World tracks turn-by-turn."

### 2. Navigation (15 seconds)
- Click on Yields tab
- Scroll to show all 14 charts
- "Two-column layout makes it easy to compare related yields"

### 3. Specific Examples (2 minutes)

**Economic Comparison**:
- Point to Money chart: "See how Player A dominated economically"
- Point to Orders chart: "But Player B had more military commands"

**Research Race**:
- Point to Science chart: "Player B pulled ahead in research around turn 40"
- Point to Culture chart: "While Player A focused on culture"

**Resource Management**:
- Point to Iron/Stone/Wood: "These show who controlled resource-rich territories"

**Population Growth**:
- Point to Food + Growth: "Player A's superior food production enabled faster expansion"

### 4. Interactivity (30 seconds)
- Hover over a data point: "Tooltips show exact values"
- Click legend: "Toggle players on/off"
- Zoom in on interesting spike: "Investigate anomalies"

### 5. Value Proposition (30 seconds)
"This helps you understand:
- Who had economic advantage and when
- Whether the winner won through economy, military, or strategy
- How yield patterns correlate with victory"

## Questions You Might Get

**Q: Why 2 columns instead of 1?**
A: Efficient use of screen space. Related yields are adjacent for easy comparison.

**Q: Can I filter to just certain yields?**
A: Not yet - with only 14 yields, showing all at once is actually better for analysis. If users request filtering, we can add it (YAGNI principle).

**Q: How fast does it load?**
A: Single query fetches all data in < 100ms. Charts render in < 1 second even for longest games.

**Q: What if I want to compare yields across matches?**
A: That's a future feature! This initial implementation focuses on single-match analysis.
```

5. **Commit the demo script**:
```bash
git add docs/demos/yields-feature-demo.md
git commit -m "docs: Add demo script for yields feature

- Step-by-step walkthrough for demoing feature
- Common questions and answers
- Performance metrics"
```

---

### Task 10: Create Pull Request (Optional)

**Objective**: If using GitHub, create a pull request for code review.

**Steps**:

1. **Push your branch**:
```bash
git push origin feature/yields-visualization
```

2. **Create PR description** (use this template):

```markdown
## Yields Visualization Feature

### Summary
Adds comprehensive yield tracking to the Match Details page, displaying all 14 yield types (Food, Science, Culture, etc.) as time-series charts showing turn-by-turn progression for each player.

### Changes
- ✅ Generic `create_yield_chart()` function for DRY chart generation
- ✅ Single-query optimization (fetch all yields at once)
- ✅ 2-column grid layout displaying all 14 yields
- ✅ Comprehensive unit tests with 95% coverage
- ✅ User and developer documentation

### Testing
- [x] All unit tests pass (`pytest tests/test_charts.py`)
- [x] Manual testing completed on 15 matches
- [x] Performance validated (< 1s render time)
- [x] No errors in browser console
- [x] Tested on Chrome, Firefox, Safari

### Performance
- **Query time**: < 100ms (single query for all yields)
- **Render time**: < 1 second (worst case: 3,000 data points)
- **Memory usage**: < 100MB (14 charts loaded)

### Screenshots
[Add screenshots of the Yields tab showing all 14 charts]

### Review Checklist
- [ ] Code follows DRY principle
- [ ] No premature optimization (YAGNI)
- [ ] Atomic commits with clear messages
- [ ] Documentation updated
- [ ] Tests added and passing

### Related Issues
Closes #[issue-number] (if applicable)
```

3. **Request reviewers**:
- Tag relevant team members
- Link to demo script: `docs/demos/yields-feature-demo.md`
- Link to test results: `docs/testing/yields-tab-test-results.md`

---

## Summary & Maintenance

### What We Built

**Feature**: Comprehensive yields visualization
- **Files changed**: 2 (charts.py, matches.py)
- **Lines added**: ~300
- **Tests added**: 10 unit tests
- **Commits**: 10 atomic commits

**Architecture**:
```
User selects match
    ↓
update_all_yield_charts() callback triggers
    ↓
Single query: get_yield_history_by_match(match_id)
    ↓
Loop through 14 yield types
    ↓
Filter DataFrame for each yield
    ↓
create_yield_chart() for each
    ↓
Return 14 figures
    ↓
Dash updates all charts
```

### Key Principles Applied

**DRY**:
- ✅ One generic `create_yield_chart()` instead of 14 functions
- ✅ Dynamic layout generation (no copy-paste)
- ✅ Reusable test fixtures

**YAGNI**:
- ✅ No lazy loading (not needed yet)
- ✅ No caching (premature optimization)
- ✅ No complex filtering UI (users see all at once)

**TDD**:
- ✅ Tests written alongside code
- ✅ Edge cases covered
- ✅ Regression prevention

### Future Enhancements (Out of Scope)

Only implement these if users request them:

1. **Yield comparison across matches**: Overlay multiple matches on one chart
2. **Filtering UI**: Checkboxes to show/hide specific yields
3. **Export to CSV**: Download yield data
4. **Annotations**: Mark significant events on charts (wars, wonders, etc.)
5. **Correlation analysis**: Show which yields correlate with victory

### Troubleshooting

**Problem**: Charts load slowly (> 2 seconds)

*Diagnosis*:
```bash
# Check database size
uv run duckdb tournament_data.duckdb -readonly -c "SELECT COUNT(*) FROM player_yield_history"

# If > 100K rows, add sampling
```

*Solution*: Add turn sampling in query (every 5th turn for games > 150 turns)

---

**Problem**: Hover tooltips don't work

*Diagnosis*: Check browser console for JavaScript errors

*Solution*:
```python
# Verify hovertext is a list
assert isinstance(hover_texts, list)
assert all(isinstance(h, str) for h in hover_texts)
```

---

**Problem**: Charts show wrong data

*Diagnosis*:
```python
# Add logging to callback
logger.info(f"Filtering for yield_type: {yield_type}")
logger.info(f"Filtered DataFrame shape: {df_yield.shape}")
```

*Solution*: Check `resource_type` column matches exactly (case-sensitive)

---

**Problem**: Memory usage is high

*Diagnosis*: Open browser DevTools → Memory → Take heap snapshot

*Solution*:
- Remove markers: `mode="lines"` instead of `"lines+markers"`
- Simplify data: Sample every Nth turn
- Lazy load: Implement accordions (see rejected Option 1)

---

## Conclusion

You now have a comprehensive, well-tested yields visualization feature that:

- ✅ Follows all code quality principles (DRY, YAGNI, TDD)
- ✅ Has excellent performance (< 1 second render)
- ✅ Is maintainable (generic functions, clear docs)
- ✅ Is tested (unit tests + manual validation)
- ✅ Is documented (user guide + developer guide)

**Total estimated time**: 2-3 hours for an experienced developer, 4-5 hours for someone new to the codebase.

**Commit the final plan document**:
```bash
git add docs/plans/yields-visualization-implementation-plan.md
git commit -m "docs: Add comprehensive implementation plan for yields viz

- Break down into 10 bite-sized tasks
- Include testing strategy and error handling
- Document all files to touch and code to write
- Add troubleshooting guide for common issues"
```

Good luck! 🚀
