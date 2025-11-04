# Implementation Plan: Apply Filters to All Overview Charts

## Overview

**Goal**: Make the filter section on the overview page apply to ALL charts and visualizations across all tabs (Summary, Nations, Rulers, Economy, Cities), not just the Matches table.

**Current State**: Filters exist on the overview page but only affect the Matches table on the Summary tab.

**Target State**: All charts on all tabs respect the selected filters, allowing users to analyze subsets of tournament data (e.g., "show me nation win rates for Winners Bracket matches only" or "show me economic progression for games with Fluffbunny").

**Files to Touch**:
- `tournament_visualizer/data/queries.py` - Add filtering to query methods
- `tournament_visualizer/pages/overview.py` - Update callbacks to use filters
- `tests/test_queries.py` - Add tests for filtered queries (create if doesn't exist)
- `tests/test_overview_integration.py` - Add integration tests (create if doesn't exist)

## Prerequisites

**Read These First**:
1. `CLAUDE.md` - Development principles (YAGNI, DRY, TDD, atomic commits)
2. `docs/database-schema.md` - Understand the schema
3. `docs/ui-architecture.md` - UI patterns and conventions

**Key Concepts**:
- **YAGNI**: Only add filters where they make sense. Don't add filtering to every single query.
- **DRY**: Create a reusable helper for building WHERE clauses with common filters
- **Atomic Commits**: Commit after each task below
- **TDD**: Write tests first, then implement

**Tooling**:
- Python 3.11+ with type hints
- DuckDB for database
- Dash/Plotly for UI
- pytest for testing
- `uv` for package management

## Architecture Strategy

### Filter Application Pattern

We need to filter at the **match level** (which matches to include) rather than at the event/player level. This means:

1. First filter matches based on criteria (bracket, turns, map properties, etc.)
2. Then compute statistics only from those matches
3. Pass filtered match IDs to downstream queries

### Common Filter Parameters

All filtered queries will accept these optional parameters:
```python
tournament_round: Optional[int] = None
bracket: Optional[str] = None  # 'Winners', 'Losers', 'Unknown'
min_turns: Optional[int] = None
max_turns: Optional[int] = None
map_size: Optional[str] = None
map_class: Optional[str] = None
map_aspect: Optional[str] = None
nations: Optional[list[str]] = None
players: Optional[list[str]] = None
```

## Task Breakdown

---

## Task 1: Create Helper Function for Match Filtering

**Goal**: Create a reusable helper that builds a filtered match ID list.

**Why**: Avoid duplicating the filtering logic across 20+ query methods.

**File**: `tournament_visualizer/data/queries.py`

**Implementation**:

```python
def _get_filtered_match_ids(
    self,
    tournament_round: Optional[int] = None,
    bracket: Optional[str] = None,
    min_turns: Optional[int] = None,
    max_turns: Optional[int] = None,
    map_size: Optional[str] = None,
    map_class: Optional[str] = None,
    map_aspect: Optional[str] = None,
    nations: Optional[list[str]] = None,
    players: Optional[list[str]] = None,
) -> list[int]:
    """Get list of match IDs that match the given filters.

    This is a helper method to avoid duplicating filter logic across queries.
    Returns all match IDs if no filters are provided.

    Args:
        tournament_round: Specific round number
        bracket: Bracket filter
        min_turns: Minimum turns
        max_turns: Maximum turns
        map_size: Map size filter
        map_class: Map class filter
        map_aspect: Map aspect ratio filter
        nations: List of civilizations
        players: List of player names

    Returns:
        List of match_id integers
    """
    query = "SELECT DISTINCT m.match_id FROM matches m WHERE 1=1"
    params = {}

    # Apply filters (reuse logic from get_matches_by_round)
    if tournament_round is not None:
        query += " AND m.tournament_round = $tournament_round"
        params["tournament_round"] = tournament_round

    if bracket == "Winners":
        query += " AND m.tournament_round > 0"
    elif bracket == "Losers":
        query += " AND m.tournament_round < 0"
    elif bracket == "Unknown":
        query += " AND m.tournament_round IS NULL"

    if min_turns is not None:
        query += " AND m.total_turns >= $min_turns"
        params["min_turns"] = min_turns
    if max_turns is not None:
        query += " AND m.total_turns <= $max_turns"
        params["max_turns"] = max_turns

    if map_size:
        query += " AND m.map_size = $map_size"
        params["map_size"] = map_size
    if map_class:
        query += " AND m.map_class = $map_class"
        params["map_class"] = map_class
    if map_aspect:
        query += " AND m.map_aspect_ratio = $map_aspect"
        params["map_aspect"] = map_aspect

    if nations and len(nations) > 0:
        query += """ AND EXISTS (
            SELECT 1 FROM players p
            WHERE p.match_id = m.match_id
            AND p.civilization = ANY($nations)
        )"""
        params["nations"] = nations

    if players and len(players) > 0:
        query += """ AND EXISTS (
            SELECT 1 FROM players p
            WHERE p.match_id = m.match_id
            AND p.player_name = ANY($players)
        )"""
        params["players"] = players

    with self.db.get_connection() as conn:
        df = conn.execute(query, params).df()
        return df["match_id"].tolist() if not df.empty else []
```

**Location**: Add this as a **private method** inside the `TournamentQueries` class (around line 3000, before `get_matches_by_round`).

**Test**: Create `tests/test_queries_filter_helper.py`:

```python
"""Tests for the match filtering helper method."""

import pytest
from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.queries import TournamentQueries


@pytest.fixture
def test_queries(test_db_path):
    """Create queries instance with test database."""
    db = TournamentDatabase(test_db_path)
    return TournamentQueries(db)


def test_get_filtered_match_ids_no_filters(test_queries):
    """Test that no filters returns all match IDs."""
    match_ids = test_queries._get_filtered_match_ids()
    assert len(match_ids) > 0
    assert isinstance(match_ids, list)
    assert all(isinstance(mid, int) for mid in match_ids)


def test_get_filtered_match_ids_by_bracket(test_queries):
    """Test filtering by Winners bracket."""
    all_matches = test_queries._get_filtered_match_ids()
    winners_matches = test_queries._get_filtered_match_ids(bracket="Winners")

    assert len(winners_matches) <= len(all_matches)
    # Verify all returned matches are actually in Winners bracket
    # (Add verification query if needed)


def test_get_filtered_match_ids_by_turns(test_queries):
    """Test filtering by turn range."""
    matches = test_queries._get_filtered_match_ids(min_turns=50, max_turns=100)

    # Verify all returned matches have turns in range
    assert isinstance(matches, list)


def test_get_filtered_match_ids_by_nation(test_queries):
    """Test filtering by civilization."""
    matches = test_queries._get_filtered_match_ids(nations=["Rome"])

    # Should only return matches where Rome was played
    assert isinstance(matches, list)


def test_get_filtered_match_ids_by_player(test_queries):
    """Test filtering by player name."""
    matches = test_queries._get_filtered_match_ids(players=["Fluffbunny"])

    # Should only return matches where Fluffbunny played
    assert isinstance(matches, list)


def test_get_filtered_match_ids_combined_filters(test_queries):
    """Test multiple filters combined."""
    matches = test_queries._get_filtered_match_ids(
        bracket="Winners",
        min_turns=50,
        nations=["Rome"]
    )

    # Result should be subset of each individual filter
    assert isinstance(matches, list)


def test_get_filtered_match_ids_no_matches(test_queries):
    """Test that impossible filters return empty list."""
    matches = test_queries._get_filtered_match_ids(
        nations=["NonexistentCivilization"]
    )

    assert matches == []
```

**How to Test**:
```bash
# Run just this test file
uv run pytest tests/test_queries_filter_helper.py -v

# Run with coverage
uv run pytest tests/test_queries_filter_helper.py --cov=tournament_visualizer.data.queries
```

**Commit Message**:
```
feat: Add helper method for filtering matches by criteria

- Add _get_filtered_match_ids() to TournamentQueries class
- Supports filtering by bracket, turns, map properties, nations, players
- Returns list of match IDs matching all criteria
- Add comprehensive tests for filter combinations
```

---

## Task 2: Update Nation Statistics Queries

**Goal**: Make nation-related queries respect filters.

**Why**: Allow users to see nation performance in specific contexts (e.g., Winners Bracket only).

**File**: `tournament_visualizer/data/queries.py`

**Queries to Update**:
1. `get_nation_win_stats()` - Around line 850
2. `get_nation_loss_stats()` - Around line 900
3. `get_nation_popularity()` - Around line 950
4. `get_nation_counter_pick_matrix()` - Around line 2800
5. `get_pick_order_win_rates()` - Around line 2900

**Pattern for Each Query**:

```python
# BEFORE
def get_nation_win_stats(self) -> pd.DataFrame:
    query = """
    SELECT ...
    FROM players p
    JOIN matches m ON p.match_id = m.match_id
    WHERE ...
    """

# AFTER
def get_nation_win_stats(
    self,
    tournament_round: Optional[int] = None,
    bracket: Optional[str] = None,
    min_turns: Optional[int] = None,
    max_turns: Optional[int] = None,
    map_size: Optional[str] = None,
    map_class: Optional[str] = None,
    map_aspect: Optional[str] = None,
    nations: Optional[list[str]] = None,
    players: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Get nation win statistics, optionally filtered.

    Args:
        [Add all filter args]

    Returns:
        DataFrame with nation win stats from filtered matches
    """
    # Get filtered match IDs
    match_ids = self._get_filtered_match_ids(
        tournament_round=tournament_round,
        bracket=bracket,
        min_turns=min_turns,
        max_turns=max_turns,
        map_size=map_size,
        map_class=map_class,
        map_aspect=map_aspect,
        nations=nations,
        players=players,
    )

    # If no matches, return empty DataFrame
    if not match_ids:
        return pd.DataFrame()

    # Add WHERE clause to filter by match IDs
    query = """
    SELECT ...
    FROM players p
    JOIN matches m ON p.match_id = m.match_id
    WHERE m.match_id = ANY($match_ids)
      AND ...
    """

    params = {"match_ids": match_ids}

    with self.db.get_connection() as conn:
        return conn.execute(query, params).df()
```

**Implementation Order**:
1. Update `get_nation_win_stats()` first
2. Write tests for it
3. Commit
4. Repeat for each nation query

**Test File**: `tests/test_queries_nation_filters.py`

```python
"""Tests for filtered nation statistics queries."""

import pytest
from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.queries import TournamentQueries


@pytest.fixture
def test_queries(test_db_path):
    """Create queries instance with test database."""
    db = TournamentDatabase(test_db_path)
    return TournamentQueries(db)


def test_get_nation_win_stats_no_filters(test_queries):
    """Test nation win stats with no filters returns all data."""
    df = test_queries.get_nation_win_stats()
    assert not df.empty
    assert "civilization" in df.columns
    assert "win_count" in df.columns


def test_get_nation_win_stats_filtered_by_bracket(test_queries):
    """Test nation win stats filtered by Winners bracket."""
    all_stats = test_queries.get_nation_win_stats()
    winners_stats = test_queries.get_nation_win_stats(bracket="Winners")

    # Winners bracket should have fewer or equal total games
    assert winners_stats["win_count"].sum() <= all_stats["win_count"].sum()


def test_get_nation_win_stats_filtered_by_turns(test_queries):
    """Test nation win stats filtered by turn range."""
    stats = test_queries.get_nation_win_stats(min_turns=50, max_turns=100)

    # Should return valid DataFrame
    assert isinstance(stats, pd.DataFrame)


def test_get_nation_win_stats_no_matches(test_queries):
    """Test that impossible filters return empty DataFrame."""
    stats = test_queries.get_nation_win_stats(
        nations=["NonexistentCivilization"]
    )

    assert stats.empty


# Repeat similar tests for:
# - test_get_nation_loss_stats_*
# - test_get_nation_popularity_*
# - test_get_nation_counter_pick_matrix_*
# - test_get_pick_order_win_rates_*
```

**How to Test**:
```bash
uv run pytest tests/test_queries_nation_filters.py -v
```

**Commit Messages** (one per query):
```
feat: Add filtering to get_nation_win_stats query

- Accept standard filter parameters
- Use _get_filtered_match_ids helper
- Add tests for filtered nation win stats
```

---

## Task 3: Update Ruler Statistics Queries

**Goal**: Make ruler-related queries respect filters.

**File**: `tournament_visualizer/data/queries.py`

**Queries to Update**:
1. `get_ruler_archetype_win_rates()` - Around line 1500
2. `get_ruler_trait_win_rates()` - Around line 1600
3. `get_ruler_archetype_matchups()` - Around line 1700
4. `get_ruler_archetype_trait_combinations()` - Around line 1800

**Pattern**: Same as Task 2 - add filter parameters, use helper, add WHERE clause.

**Test File**: `tests/test_queries_ruler_filters.py`

```python
"""Tests for filtered ruler statistics queries."""

# Similar structure to nation tests
# Test each query method with:
# - No filters (baseline)
# - Bracket filter
# - Turn range filter
# - Combined filters
# - No matches case
```

**Commit Messages** (one per query):
```
feat: Add filtering to get_ruler_archetype_win_rates query

- Accept standard filter parameters
- Use _get_filtered_match_ids helper
- Add tests for filtered ruler statistics
```

---

## Task 4: Update Economy/Progression Queries

**Goal**: Make economy-related queries respect filters.

**File**: `tournament_visualizer/data/queries.py`

**Queries to Update**:
1. `get_metric_progression_stats()` - Around line 1200 (returns dict with science/orders/military/legitimacy)
2. `get_law_progression_by_match()` - Around line 2100
3. `get_tournament_production_strategies()` - Around line 2500

**Special Consideration**: `get_metric_progression_stats()` returns a **dict** of DataFrames, not a single DataFrame. Need to filter all of them.

**Implementation**:

```python
def get_metric_progression_stats(
    self,
    tournament_round: Optional[int] = None,
    bracket: Optional[str] = None,
    # ... all other filter params
) -> dict[str, pd.DataFrame]:
    """Get aggregated metric progression stats, optionally filtered."""

    match_ids = self._get_filtered_match_ids(
        tournament_round=tournament_round,
        bracket=bracket,
        # ... pass all params
    )

    if not match_ids:
        return {
            "science": pd.DataFrame(),
            "orders": pd.DataFrame(),
            "military": pd.DataFrame(),
            "legitimacy": pd.DataFrame(),
        }

    # Update each query to filter by match_ids
    # ... existing query logic with WHERE m.match_id = ANY($match_ids)
```

**Test File**: `tests/test_queries_economy_filters.py`

**Commit Messages**:
```
feat: Add filtering to get_metric_progression_stats query

- Accept standard filter parameters
- Filter all progression metrics (science, orders, military, legitimacy)
- Add tests for filtered economy statistics
```

---

## Task 5: Update City/Expansion Queries

**Goal**: Make city-related queries respect filters.

**File**: `tournament_visualizer/data/queries.py`

**Queries to Update**:
1. `get_tournament_expansion_timeline()` - Around line 2600

**Test File**: `tests/test_queries_city_filters.py`

**Commit Message**:
```
feat: Add filtering to city expansion queries

- Accept standard filter parameters
- Add tests for filtered city statistics
```

---

## Task 6: Update Summary Tab Charts

**Goal**: Make Summary tab charts use filters.

**File**: `tournament_visualizer/pages/overview.py`

**Callbacks to Update**:
1. `update_units_chart()` - Line ~890
2. `update_map_chart()` - Line ~910
3. `update_event_timeline()` - Line ~1130

**Pattern**:

```python
# BEFORE
@callback(
    Output("overview-units-chart", "figure"),
    Input("refresh-interval", "n_intervals"),
)
def update_units_chart(n_intervals: int):
    queries = get_queries()
    df = queries.get_unit_popularity()
    return create_unit_popularity_sunburst_chart(df)

# AFTER
@callback(
    Output("overview-units-chart", "figure"),
    Input("overview-bracket-filter-dropdown", "value"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-min-turns-input", "value"),
    Input("overview-max-turns-input", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_units_chart(
    bracket: str,
    round_num: Optional[int],
    min_turns: Optional[int],
    max_turns: Optional[int],
    map_size: Optional[str],
    map_class: Optional[str],
    map_aspect: Optional[str],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    n_intervals: int,
):
    """Update unit popularity chart with filters."""
    queries = get_queries()
    bracket_param = None if bracket == "all" else bracket

    df = queries.get_unit_popularity(
        tournament_round=round_num,
        bracket=bracket_param,
        min_turns=min_turns,
        max_turns=max_turns,
        map_size=map_size,
        map_class=map_class,
        map_aspect=map_aspect,
        nations=nations if nations else None,
        players=players if players else None,
    )

    if df.empty:
        return create_empty_chart_placeholder("No data for selected filters")

    return create_unit_popularity_sunburst_chart(df)
```

**Important**: Check if `get_unit_popularity()` exists. If not, you may need to create it or update a related query.

**Test**: Manual testing in browser (integration tests in Task 9).

**Commit Messages** (one per chart):
```
feat: Apply filters to unit popularity chart

- Add filter inputs to callback
- Pass filters to query method
- Show empty state when no matches
```

---

## Task 7: Update Nations Tab Charts

**Goal**: Make Nations tab charts use filters.

**File**: `tournament_visualizer/pages/overview.py`

**Callbacks to Update**:
1. `update_nation_win_chart()` - Line ~810
2. `update_nation_loss_chart()` - Line ~830
3. `update_nation_popularity_chart()` - Line ~850
4. `update_counter_pick_heatmap()` - Line ~1270
5. `update_pick_order_win_rate()` - Line ~1300

**Pattern**: Same as Task 6 - add all filter inputs, pass to query.

**Commit Messages** (one per chart):
```
feat: Apply filters to nation win percentage chart

- Add filter inputs to callback
- Pass filters to get_nation_win_stats
- Handle empty data gracefully
```

---

## Task 8: Update Rulers, Economy, Cities Tab Charts

**Goal**: Make remaining tab charts use filters.

**File**: `tournament_visualizer/pages/overview.py`

**Rulers Tab Callbacks**:
1. `update_ruler_archetype_chart()` - Line ~1150
2. `update_ruler_trait_performance_chart()` - Line ~1180
3. `update_ruler_matchup_matrix_chart()` - Line ~1210
4. `update_ruler_combinations_chart()` - Line ~1240

**Economy Tab Callbacks**:
1. `update_science_progression()` - Line ~1330
2. `update_orders_progression()` - Line ~1360
3. `update_military_progression()` - Line ~1390
4. `update_legitimacy_progression()` - Line ~1420
5. `update_law_distribution()` - Line ~1060
6. `update_law_efficiency()` - Line ~1090
7. `update_production_strategies_chart()` - Line ~1480

**Cities Tab Callbacks**:
1. `update_expansion_timeline_chart()` - Line ~1450

**Pattern**: Same as previous tasks.

**Commit Messages** (one per chart):
```
feat: Apply filters to [chart name]

- Add filter inputs to callback
- Pass filters to query method
- Handle empty data gracefully
```

---

## Task 9: Integration Testing

**Goal**: Ensure filters work end-to-end across all tabs.

**File**: `tests/test_overview_integration.py` (create new)

```python
"""Integration tests for overview page filters."""

import pytest
from dash.testing.application_runners import import_app


def test_filter_by_bracket_updates_all_charts(dash_duo):
    """Test that changing bracket filter updates all charts."""
    app = import_app("app")
    dash_duo.start_server(app)

    # Navigate to overview page
    dash_duo.wait_for_page(timeout=10)

    # Change bracket filter
    bracket_dropdown = dash_duo.find_element("#overview-bracket-filter-dropdown")
    bracket_dropdown.select_by_value("Winners")

    # Wait for charts to update
    dash_duo.wait_for_element("#overview-nation-win-chart", timeout=5)

    # Verify charts have content
    assert dash_duo.find_element("#overview-nation-win-chart")
    assert dash_duo.find_element("#overview-ruler-archetype-chart")

    # Take screenshot for visual verification
    dash_duo.take_snapshot("filtered-by-bracket")


def test_filter_by_nation_updates_charts(dash_duo):
    """Test that selecting a specific nation filters data."""
    # Similar to above but select nation
    pass


def test_combined_filters(dash_duo):
    """Test that multiple filters work together."""
    # Apply bracket + nation + turn range filters
    pass


def test_no_matches_shows_empty_state(dash_duo):
    """Test that impossible filters show empty state."""
    # Set filters that match no games
    # Verify empty state is shown
    pass
```

**How to Test**:
```bash
# Run integration tests
uv run pytest tests/test_overview_integration.py -v

# Run with browser visible (for debugging)
uv run pytest tests/test_overview_integration.py -v --headed
```

**Note**: Integration tests require Selenium. If not set up:
```bash
uv add --dev pytest-dash selenium
```

**Commit Message**:
```
test: Add integration tests for overview page filters

- Test bracket filter updates all charts
- Test nation filter works across tabs
- Test combined filters
- Test empty state handling
```

---

## Task 10: Manual Testing Checklist

**Goal**: Verify everything works in the running application.

**Prerequisites**:
```bash
# Ensure database has data
uv run duckdb data/tournament_data.duckdb -readonly -c "SELECT COUNT(*) FROM matches"

# Start the app
uv run python manage.py restart

# Open browser to http://localhost:8050
```

**Test Cases**:

### Summary Tab
- [ ] Select "Winners Bracket" - verify matches table filters
- [ ] Select "Losers Bracket" - verify matches table filters
- [ ] Select specific round - verify matches table updates
- [ ] Set turn range (e.g., 50-100) - verify only matches in range
- [ ] Unit chart should update with filters
- [ ] Map chart should update with filters
- [ ] Event timeline should update with filters
- [ ] Round statistics card should still show all rounds (not filtered)

### Nations Tab
- [ ] Apply Winners Bracket filter - nation win % changes
- [ ] Apply Losers Bracket filter - nation win % changes
- [ ] Select specific nation - charts update
- [ ] Counter-pick heatmap updates with filters
- [ ] Pick order win rate updates with filters

### Rulers Tab
- [ ] Apply filters - archetype win rates update
- [ ] Apply filters - trait performance updates
- [ ] Apply filters - matchup matrix updates
- [ ] Apply filters - popular combinations update

### Economy Tab
- [ ] Apply filters - science progression updates
- [ ] Apply filters - orders progression updates
- [ ] Apply filters - military progression updates
- [ ] Apply filters - legitimacy progression updates
- [ ] Apply filters - law distribution updates
- [ ] Apply filters - law efficiency scatter updates
- [ ] Apply filters - production strategies update

### Cities Tab
- [ ] Apply filters - expansion timeline updates

### Edge Cases
- [ ] Select filters that match NO games - all charts show empty state
- [ ] Select then clear filters - charts return to showing all data
- [ ] Switch tabs with filters applied - filters persist
- [ ] Refresh page - filters reset to defaults

### Performance
- [ ] Filtering is reasonably fast (< 2 seconds per chart)
- [ ] No console errors
- [ ] No visible UI glitches

**Bugs Found**: Document any issues in GitHub issues, not inline here.

---

## Task 11: Documentation Updates

**Goal**: Document the new filtering behavior.

**Files to Update**:

### 1. `CLAUDE.md` (if needed)

Add note about filter pattern if not already documented:

```markdown
### Filter Pattern for Overview Page

All chart callbacks on the overview page accept standard filter inputs:
- Tournament bracket and round
- Turn range (min/max)
- Map properties (size, class, aspect)
- Nations and players (multi-select)

Queries use `_get_filtered_match_ids()` helper to build filtered match lists,
then apply `WHERE match_id = ANY($match_ids)` to their queries.
```

### 2. `docs/ui-architecture.md`

Add section on filtering:

```markdown
## Filtering Pattern

### Overview Page Filters

The overview page has a global filter section that affects all charts.

**UI Components** (overview.py lines 65-267):
- Bracket and round dropdowns
- Turn range inputs
- Map property dropdowns
- Nation and player multi-selects

**Data Flow**:
1. User changes filter → callback triggered
2. Callback gets filter values from inputs
3. Callback passes filters to query method
4. Query uses `_get_filtered_match_ids()` to get matching matches
5. Query returns filtered data
6. Callback creates chart from filtered data

**Adding Filters to New Charts**:

```python
@callback(
    Output("my-new-chart", "figure"),
    # Add these 9 inputs for filters:
    Input("overview-bracket-filter-dropdown", "value"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-min-turns-input", "value"),
    Input("overview-max-turns-input", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_my_chart(
    bracket: str,
    round_num: Optional[int],
    min_turns: Optional[int],
    max_turns: Optional[int],
    map_size: Optional[str],
    map_class: Optional[str],
    map_aspect: Optional[str],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    n_intervals: int,
):
    queries = get_queries()
    bracket_param = None if bracket == "all" else bracket

    df = queries.my_query_method(
        tournament_round=round_num,
        bracket=bracket_param,
        min_turns=min_turns,
        max_turns=max_turns,
        map_size=map_size,
        map_class=map_class,
        map_aspect=map_aspect,
        nations=nations if nations else None,
        players=players if players else None,
    )

    if df.empty:
        return create_empty_chart_placeholder("No data for selected filters")

    return create_my_chart(df)
```
```

### 3. Create `docs/features/overview-filters.md` (new file)

```markdown
# Overview Page Filters

## Overview

The overview page provides a comprehensive filter section that allows users to analyze specific subsets of tournament data.

## Available Filters

### Tournament Filters
- **Bracket**: Winners, Losers, Unknown, or All
- **Round**: Specific tournament round or all rounds
- **Turn Range**: Minimum and maximum game length

### Map Filters
- **Map Size**: Small, Medium, Large, etc.
- **Map Class**: Inland, Coastal, Islands, etc.
- **Map Aspect**: Standard, Wide, Tall, etc.

### Player/Nation Filters
- **Nations**: Multi-select civilizations
- **Players**: Multi-select player names

## What Gets Filtered

**All charts across all tabs** respect the filters:

- **Summary Tab**: Unit breakdown, map breakdown, event timeline, matches table
- **Nations Tab**: Win %, loss %, popularity, counter-picks, pick order
- **Rulers Tab**: Archetype performance, trait performance, matchups, combinations
- **Economy Tab**: Science, orders, military, legitimacy, laws, production
- **Cities Tab**: Expansion timeline

**Exception**: The "Tournament Rounds" statistics card shows all rounds regardless of filters.

## Use Cases

### Analyze Winners Bracket Performance
1. Set Bracket filter to "Winners"
2. View nation win rates in Winners Bracket only
3. Compare to Losers Bracket performance

### Study Specific Matchups
1. Set Nations filter to ["Rome", "Carthage"]
2. View only games where Rome or Carthage were played
3. Analyze their performance and counters

### Analyze Long Games
1. Set Min Turns to 100
2. View economy progression in marathon games
3. Compare to shorter games

### Player Analysis
1. Set Players filter to specific player
2. View their nation preferences
3. View their ruler choices
4. Analyze their expansion patterns

## Implementation Details

See `docs/ui-architecture.md` for technical implementation details.
```

**Commit Message**:
```
docs: Document overview page filtering behavior

- Add filter pattern to CLAUDE.md
- Add filtering section to ui-architecture.md
- Create overview-filters.md feature documentation
```

---

## Task 12: Performance Optimization (Optional)

**Goal**: Ensure filtering performs well with large datasets.

**Check Performance**:

```python
# Add to queries.py for profiling
import time
import logging

logger = logging.getLogger(__name__)

def _get_filtered_match_ids(self, ...):
    start = time.time()
    # ... existing code ...
    elapsed = time.time() - start
    logger.debug(f"Filter query took {elapsed:.3f}s, returned {len(match_ids)} matches")
    return match_ids
```

**Profile**:
```bash
# Run app with debug logging
LOG_LEVEL=DEBUG uv run python manage.py start

# Apply various filters and watch logs
# Target: < 100ms for filter query
```

**Optimization Strategies** (only if needed):

1. **Add Indexes** (if queries are slow):
```sql
-- Run these in DuckDB if filtering is slow
CREATE INDEX IF NOT EXISTS idx_matches_tournament_round ON matches(tournament_round);
CREATE INDEX IF NOT EXISTS idx_matches_total_turns ON matches(total_turns);
CREATE INDEX IF NOT EXISTS idx_matches_map_size ON matches(map_size);
CREATE INDEX IF NOT EXISTS idx_players_civilization ON players(civilization);
CREATE INDEX IF NOT EXISTS idx_players_name ON players(player_name);
```

2. **Cache Filter Results** (if calling multiple times):
```python
from functools import lru_cache

# Only do this if profiling shows it's needed
@lru_cache(maxsize=128)
def _get_filtered_match_ids_cached(self, ...):
    # Convert lists to tuples for hashing
    # ... implementation
```

**Commit Message** (only if optimization needed):
```
perf: Optimize match filtering performance

- Add database indexes for filter columns
- Add caching for repeated filter queries
- Reduces filter query time from Xms to Yms
```

---

## Task 13: Final Commit and Summary

**Goal**: Clean up and document the complete implementation.

**Final Checklist**:
- [ ] All tests pass: `uv run pytest -v`
- [ ] No linting errors: `uv run ruff check tournament_visualizer/`
- [ ] No type errors: `uv run mypy tournament_visualizer/` (if using mypy)
- [ ] Manual testing complete (Task 10)
- [ ] Documentation updated (Task 11)
- [ ] All commits are atomic with good messages

**Create Summary Commit**:

If you made many small commits, consider a summary commit:

```bash
git log --oneline | head -20  # Review recent commits

# Optional: Create annotated tag
git tag -a v1.0-overview-filters -m "Complete overview page filtering feature"
```

**Update CHANGELOG** (if project has one):

```markdown
## [Unreleased]

### Added
- Global filters on overview page now apply to all charts across all tabs
- Users can filter by tournament bracket, round, turn range, map properties, nations, and players
- Helper method `_get_filtered_match_ids()` for reusable filtering logic

### Changed
- All overview page chart callbacks now accept filter parameters
- All statistics queries now support optional filtering

### Testing
- Added comprehensive unit tests for filtered queries
- Added integration tests for overview page filtering
```

---

## Testing Strategy Summary

### Unit Tests (Per Task)
- Test each query method with no filters (baseline)
- Test with individual filters (bracket, turns, nations, etc.)
- Test with combined filters
- Test with no matches (empty result)
- Test with invalid inputs

### Integration Tests (Task 9)
- Test that UI filter changes update all charts
- Test that filters persist across tab switches
- Test empty states
- Visual regression testing (screenshots)

### Manual Tests (Task 10)
- Walk through entire UI with various filter combinations
- Verify empty states
- Check for console errors
- Verify performance is acceptable

---

## Common Pitfalls

### 1. Forgetting to Convert "all" to None
```python
# WRONG
bracket_param = bracket  # Passes "all" to query

# RIGHT
bracket_param = None if bracket == "all" else bracket
```

### 2. Not Handling Empty Results
```python
# WRONG
df = queries.get_nation_win_stats(filters...)
return create_chart(df)  # Crashes if df is empty

# RIGHT
df = queries.get_nation_win_stats(filters...)
if df.empty:
    return create_empty_chart_placeholder("No data for selected filters")
return create_chart(df)
```

### 3. Empty Lists vs None
```python
# WRONG
nations=nations  # Passes empty list [], which may cause issues

# RIGHT
nations=nations if nations else None  # Converts empty list to None
```

### 4. Not Filtering Correctly
```python
# WRONG - Filters players first, then aggregates all matches
SELECT ... FROM players WHERE player_name = 'X'

# RIGHT - Filters matches first, then looks at players in those matches
SELECT ... FROM players
WHERE match_id = ANY($filtered_match_ids)
```

### 5. Breaking Existing Callers
When adding filter parameters, make them all **optional with defaults**:

```python
# WRONG - Breaks existing code
def get_nation_win_stats(self, bracket: str):  # Required parameter

# RIGHT - Backwards compatible
def get_nation_win_stats(self, bracket: Optional[str] = None):  # Optional
```

---

## Rollback Plan

If something goes wrong:

1. **Find the last working commit**:
```bash
git log --oneline
# Identify commit before filtering work started
```

2. **Revert changes**:
```bash
# Soft reset (keeps changes, allows fixing)
git reset --soft <commit-hash>

# Hard reset (discards changes, nuclear option)
git reset --hard <commit-hash>
```

3. **Partial rollback** (just one file):
```bash
git checkout <commit-hash> -- tournament_visualizer/pages/overview.py
```

4. **Create hotfix branch**:
```bash
git checkout -b hotfix/revert-filters
git revert <bad-commit-hash>
git push origin hotfix/revert-filters
```

---

## Questions?

**Read these first**:
- `CLAUDE.md` - Development principles
- `docs/database-schema.md` - Database structure
- `docs/ui-architecture.md` - UI patterns

**Still stuck?**
- Check existing similar queries for patterns
- Run tests to verify assumptions
- Use `logger.debug()` to trace execution
- Check DuckDB docs for SQL syntax

---

## Success Criteria

You're done when:

1. ✅ All tests pass
2. ✅ Manual testing checklist complete
3. ✅ All charts respect filters
4. ✅ Empty states work correctly
5. ✅ Performance is acceptable (< 2s per chart)
6. ✅ Documentation updated
7. ✅ All commits are atomic with good messages
8. ✅ No console errors in browser

**Verification Command**:
```bash
# Run all tests
uv run pytest -v

# Check code quality
uv run ruff check tournament_visualizer/

# Start app and test manually
uv run python manage.py restart
```
