# Implementation Plan: Dual Law Metrics Tracking

**Status**: Not Started
**Created**: 2025-01-09
**Estimated Effort**: 4-6 hours
**Priority**: Medium

## Problem Statement

Currently, law metrics count every law change/switch as a separate law, which inflates numbers. For example:
- Player adopts Serfdom (turn 58)
- Player switches to Colonies (turn 63)
- Player switches back to Serfdom (turn 71)
- **Current**: Shows "3 laws"
- **Expected**: Shows "1 law pair adopted"

However, the switching behavior itself is strategically interesting and worth tracking separately.

## Solution: Track Three Metrics

1. **`unique_law_pairs`** - Number of different law categories adopted (e.g., 8)
2. **`total_laws_adopted`** - Total law adoption events from event log (e.g., 12)
3. **`law_switch_count`** - Derived metric: `total_laws_adopted - unique_law_pairs` (e.g., 4)

**Data Sources**:
- `unique_law_pairs`: COUNT from `player_statistics` WHERE `stat_category='law_changes'`
- `total_laws_adopted`: COUNT from `events` WHERE `event_type='LAW_ADOPTED'` (source of truth)
- Switching behavior: Calculated from above

**No database changes or re-import needed** - all data already exists.

## Design Principles

### YAGNI (You Ain't Gonna Need It)

**What we're NOT doing**:
- ❌ Adding metric selection dropdowns in UI (can add later if users request)
- ❌ Creating all possible chart variations (unique vs total vs switches)
- ❌ Building a law timeline heatmap showing every switch
- ❌ Adding new database columns or tables
- ❌ Changing existing chart APIs (avoid breaking changes)

**What we ARE doing**:
- ✅ Fix the immediate counting issue (use events table)
- ✅ Preserve switching data in queries (make it available)
- ✅ Update only the 4 queries that calculate `total_laws`
- ✅ Keep chart interfaces the same (backwards compatible)

### DRY (Don't Repeat Yourself)

**Shared Query Pattern**:

All law queries will use a common CTE pattern:

```sql
WITH law_metrics AS (
    -- SINGLE source of truth for law counts
    SELECT
        e.match_id,
        e.player_id,
        COUNT(*) as total_laws_adopted,
        -- Could add unique pairs here later if needed
    FROM events e
    WHERE e.event_type = 'LAW_ADOPTED'
    GROUP BY e.match_id, e.player_id
)
-- Rest of query uses law_metrics
```

**Don't duplicate this logic** - if we need unique pairs later, add it to this one CTE.

## Implementation Steps

### Step 1: Update Core Query Method (30 min)

**File**: `tournament_visualizer/data/queries.py`

**Current code** (line 1006):
```python
def get_total_laws_by_player(self, match_id: Optional[int] = None) -> pd.DataFrame:
    """Get total law counts by player, optionally filtered by match."""
    base_query = """
    SELECT
        p.player_name,
        p.civilization,
        m.match_id,
        m.game_name,
        m.total_turns,
        SUM(ps.value) as total_laws  -- ← PROBLEM: Counts switches
    FROM player_statistics ps
    JOIN players p ON ps.player_id = p.player_id
    JOIN matches m ON ps.match_id = m.match_id
    WHERE ps.stat_category = 'law_changes'
    """
```

**New code**:
```python
def get_total_laws_by_player(self, match_id: Optional[int] = None) -> pd.DataFrame:
    """Get law counts by player, optionally filtered by match.

    Returns:
        DataFrame with columns:
            - player_name: Player display name
            - civilization: Civilization played
            - match_id: Match ID
            - game_name: Match name
            - total_turns: Total turns in match
            - total_laws_adopted: Total law adoptions (from events - includes switches)
            - unique_law_pairs: Unique law categories adopted (from statistics)
            - law_switches: Number of times player switched laws (derived)
    """
    base_query = """
    WITH law_events AS (
        -- Count actual law adoptions from event log (source of truth)
        SELECT
            match_id,
            player_id,
            COUNT(*) as total_laws_adopted
        FROM events
        WHERE event_type = 'LAW_ADOPTED'
        GROUP BY match_id, player_id
    ),
    law_pairs AS (
        -- Count unique law pairs adopted
        SELECT
            match_id,
            player_id,
            COUNT(*) as unique_law_pairs
        FROM player_statistics
        WHERE stat_category = 'law_changes'
        GROUP BY match_id, player_id
    )
    SELECT
        p.player_name,
        p.civilization,
        m.match_id,
        m.game_name,
        m.total_turns,
        le.total_laws_adopted,
        lp.unique_law_pairs,
        (le.total_laws_adopted - lp.unique_law_pairs) as law_switches
    FROM players p
    JOIN matches m ON p.match_id = m.match_id
    LEFT JOIN law_events le ON p.match_id = le.match_id AND p.player_id = le.player_id
    LEFT JOIN law_pairs lp ON p.match_id = lp.match_id AND p.player_id = lp.player_id
    WHERE le.total_laws_adopted IS NOT NULL  -- Only players who adopted laws
    """

    params: List[Any] = []

    if match_id:
        base_query += " AND p.match_id = ?"
        params.append(match_id)

    base_query += """
    ORDER BY le.total_laws_adopted DESC
    """

    with self.db.get_connection() as conn:
        return conn.execute(base_query, params).df()
```

**Why this approach**:
- Uses `events` table as source of truth (most accurate)
- Provides all three metrics for flexibility
- Backwards compatible: returns superset of old columns
- Single CTE pattern can be reused

---

### Step 2: Update `get_law_progression()` (20 min)

**File**: `tournament_visualizer/data/queries.py:980`

**Current**: Returns `law_count` from `player_statistics` (inflated)

**Change**: Replace with event-based count

```python
def get_law_progression(self, match_id: int) -> pd.DataFrame:
    """Get law progression data for a specific match.

    Args:
        match_id: ID of the match

    Returns:
        DataFrame with law change counts by player and law type
    """
    query = """
    WITH law_counts AS (
        -- Count actual adoptions per law pair from events
        SELECT
            e.match_id,
            e.player_id,
            json_extract(e.event_data, '$.law') as law_name,
            COUNT(*) as adoption_count
        FROM events e
        WHERE e.event_type = 'LAW_ADOPTED'
            AND e.match_id = ?
        GROUP BY e.match_id, e.player_id, law_name
    ),
    law_pair_mapping AS (
        -- Map individual laws to their pairs
        SELECT
            lc.*,
            CASE
                WHEN law_name IN ('LAW_SERFDOM', 'LAW_COLONIES') THEN 'LAWCLASS_COLONIES_SERFDOM'
                WHEN law_name IN ('LAW_SLAVERY', 'LAW_FREEDOM') THEN 'LAWCLASS_SLAVERY_FREEDOM'
                WHEN law_name IN ('LAW_CENTRALIZATION', 'LAW_VASSALAGE') THEN 'LAWCLASS_CENTRALIZATION_VASSALAGE'
                WHEN law_name IN ('LAW_MONOTHEISM', 'LAW_POLYTHEISM') THEN 'LAWCLASS_MONOTHEISM_POLYTHEISM'
                WHEN law_name IN ('LAW_TYRANNY', 'LAW_CONSTITUTION') THEN 'LAWCLASS_TYRANNY_CONSTITUTION'
                WHEN law_name IN ('LAW_EPICS', 'LAW_EXPLORATION') THEN 'LAWCLASS_EPICS_EXPLORATION'
                -- Add remaining law pairs...
                ELSE 'LAWCLASS_UNKNOWN'
            END as law_pair_class
        FROM law_counts lc
    )
    SELECT
        p.player_name,
        p.civilization,
        lpm.law_pair_class as law_type,
        SUM(lpm.adoption_count) as law_count
    FROM law_pair_mapping lpm
    JOIN players p ON lpm.player_id = p.player_id AND lpm.match_id = p.match_id
    GROUP BY p.player_name, p.civilization, lpm.law_pair_class
    ORDER BY p.player_name, lpm.law_pair_class
    """

    with self.db.get_connection() as conn:
        return conn.execute(query, [match_id]).df()
```

**YAGNI Decision**: We actually DON'T need to implement this right now. The current implementation using `player_statistics` works fine for showing which law categories were adopted. The bar chart doesn't care about switches.

**Action**: SKIP this change unless a specific chart is broken.

---

### Step 3: Update `get_law_milestone_timing()` (30 min)

**File**: `tournament_visualizer/data/queries.py:1043`

**Change**: Use event-based count for milestone calculations

```python
def get_law_milestone_timing(self) -> pd.DataFrame:
    """Get timing analysis for law milestones across all matches.

    Calculates when players reach 4 laws and 7 laws based on
    actual law adoption events.

    Returns:
        DataFrame with estimated milestone timing
    """
    query = """
    WITH law_totals AS (
        -- Count actual law adoptions from events
        SELECT
            e.match_id,
            e.player_id,
            COUNT(*) as total_laws_adopted
        FROM events e
        WHERE e.event_type = 'LAW_ADOPTED'
        GROUP BY e.match_id, e.player_id
    )
    SELECT
        p.player_name,
        p.civilization,
        m.game_name,
        m.total_turns,
        lt.total_laws_adopted as total_laws,
        CAST(m.total_turns AS FLOAT) / lt.total_laws_adopted as turns_per_law,
        CASE
            WHEN lt.total_laws_adopted >= 4
                THEN CAST((4.0 * m.total_turns / lt.total_laws_adopted) AS INTEGER)
            ELSE NULL
        END as estimated_turn_to_4_laws,
        CASE
            WHEN lt.total_laws_adopted >= 7
                THEN CAST((7.0 * m.total_turns / lt.total_laws_adopted) AS INTEGER)
            ELSE NULL
        END as estimated_turn_to_7_laws
    FROM law_totals lt
    JOIN players p ON lt.player_id = p.player_id AND lt.match_id = p.match_id
    JOIN matches m ON lt.match_id = m.match_id
    WHERE lt.total_laws_adopted > 0
    ORDER BY turns_per_law ASC
    """

    with self.db.get_connection() as conn:
        return conn.execute(query).df()
```

**Key change**: `total_laws_adopted` instead of `SUM(ps.value)`

---

### Step 4: Update `get_player_law_progression_stats()` (30 min)

**File**: `tournament_visualizer/data/queries.py:1095`

**Change**: Use event-based counts in aggregations

Find the line:
```python
SUM(ps.value) as total_laws
```

Replace with:
```sql
WITH law_event_counts AS (
    SELECT
        match_id,
        player_id,
        COUNT(*) as total_laws_adopted
    FROM events
    WHERE event_type = 'LAW_ADOPTED'
    GROUP BY match_id, player_id
)
-- Then use total_laws_adopted in aggregations
```

---

### Step 5: Update `get_law_progression_by_match()` (ALREADY CORRECT!)

**File**: `tournament_visualizer/data/queries.py:1489`

**Current implementation** (lines 1553-1573):
```sql
WITH law_events AS (
    SELECT
        e.match_id,
        e.player_id,
        e.turn_number,
        ROW_NUMBER() OVER (
            PARTITION BY e.match_id, e.player_id
            ORDER BY e.turn_number
        ) as law_number
    FROM events e
    WHERE e.event_type = 'LAW_ADOPTED'
        AND e.player_id IS NOT NULL
```

✅ **No changes needed** - this already uses the events table correctly!

---

### Step 6: Update Charts (15 min each)

**Principle**: Keep chart APIs unchanged, just pass correct data

**Chart**: `create_law_progression_chart()` (line 957)

**Current signature**: `def create_law_progression_chart(df: pd.DataFrame) -> go.Figure:`

**No signature change needed**, but update internal column reference:

```python
def create_law_progression_chart(df: pd.DataFrame) -> go.Figure:
    """Create a bar chart showing total laws enacted by each player.

    Args:
        df: DataFrame with columns: player_name, civilization,
            total_laws_adopted (or legacy 'total_laws'), total_turns

    Returns:
        Plotly figure with grouped bar chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No law progression data available")

    # Support both old and new column names
    laws_col = 'total_laws_adopted' if 'total_laws_adopted' in df.columns else 'total_laws'

    fig = create_base_figure(
        title="Law Progression by Player",
        x_title="Player",
        y_title="Total Laws Adopted",  # ← Updated title
        height=400,
    )

    # Sort by laws descending
    df_sorted = df.sort_values(laws_col, ascending=False)

    # Create hover text with additional info
    hover_text = [
        f"Player: {row['player_name']}<br>"
        + f"Civilization: {row.get('civilization', 'Unknown')}<br>"
        + f"Laws Adopted: {row[laws_col]}<br>"
        + f"Total Turns: {row.get('total_turns', 'N/A')}"
        for _, row in df_sorted.iterrows()
    ]

    fig.add_trace(
        go.Bar(
            x=df_sorted["player_name"],
            y=df_sorted[laws_col],
            text=df_sorted[laws_col],
            textposition="auto",
            hovertext=hover_text,
            hoverinfo="text",
            marker_color=Config.PRIMARY_COLORS[0],
        )
    )

    fig.update_layout(showlegend=False)
    fig.update_xaxes(tickangle=-45)

    return fig
```

**Other charts**: Apply same pattern - support both column names for backwards compatibility.

---

### Step 7: Add Law Switching Analysis Chart (OPTIONAL - Phase 2)

**YAGNI**: Only implement if users ask for it.

**If needed**, add this chart:

```python
def create_law_switching_behavior_chart(df: pd.DataFrame) -> go.Figure:
    """Show which players switch laws most frequently.

    Args:
        df: DataFrame with columns: player_name, total_laws_adopted, unique_law_pairs

    Returns:
        Bar chart showing law switching rate
    """
    if df.empty:
        return create_empty_chart_placeholder("No law switching data available")

    # Calculate switching metrics
    df = df.copy()
    df['law_switches'] = df['total_laws_adopted'] - df['unique_law_pairs']
    df['switch_rate'] = df['law_switches'] / df['total_laws_adopted']

    # Only show players who switched at least once
    df = df[df['law_switches'] > 0].sort_values('law_switches', ascending=False)

    fig = create_base_figure(
        title="Law Switching Behavior",
        x_title="Player",
        y_title="Law Switches",
        height=400,
    )

    fig.add_trace(
        go.Bar(
            x=df["player_name"],
            y=df["law_switches"],
            text=df["law_switches"],
            textposition="auto",
            marker_color=Config.PRIMARY_COLORS[2],
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Law Switches: %{y}<br>"
                "Switch Rate: %{customdata:.1%}<extra></extra>"
            ),
            customdata=df["switch_rate"],
        )
    )

    fig.update_layout(showlegend=False)
    fig.update_xaxes(tickangle=-45)

    return fig
```

---

## Testing Strategy

### Unit Tests

**File**: `tests/test_queries_law_metrics.py` (new file)

```python
"""Tests for law metrics queries."""

import pandas as pd
import pytest
from tournament_visualizer.data.queries import TournamentQueries


class TestLawMetricsQueries:
    """Test law counting logic."""

    def test_get_total_laws_returns_event_based_count(self, test_db, sample_match):
        """Should count laws from events table, not statistics."""
        queries = TournamentQueries(test_db)

        df = queries.get_total_laws_by_player(match_id=sample_match.id)

        assert 'total_laws_adopted' in df.columns
        assert 'unique_law_pairs' in df.columns
        assert 'law_switches' in df.columns

    def test_law_switches_calculated_correctly(self, test_db, sample_match):
        """Law switches should be total_laws - unique_pairs."""
        queries = TournamentQueries(test_db)

        df = queries.get_total_laws_by_player(match_id=sample_match.id)

        for _, row in df.iterrows():
            expected = row['total_laws_adopted'] - row['unique_law_pairs']
            assert row['law_switches'] == expected

    def test_handles_players_with_no_switches(self, test_db, sample_match):
        """Players who never switched should have law_switches=0."""
        queries = TournamentQueries(test_db)

        df = queries.get_total_laws_by_player(match_id=sample_match.id)

        # At least one player should have no switches in test data
        assert (df['law_switches'] == 0).any()
```

### Integration Tests

**File**: `tests/test_integration_law_charts.py`

```python
"""Test law charts with real data."""

def test_law_progression_chart_with_new_metrics(queries):
    """Chart should work with new column names."""
    df = queries.get_total_laws_by_player(match_id=33)

    fig = create_law_progression_chart(df)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0
    assert fig.layout.yaxis.title.text == "Total Laws Adopted"
```

### Data Validation

**Script**: `scripts/validate_law_metrics.py` (new)

```python
"""Validate law metrics across all matches."""

from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.queries import TournamentQueries

def validate_law_metrics():
    """Check that law metrics make sense."""
    db = TournamentDatabase("data/tournament_data.duckdb")
    queries = TournamentQueries(db)

    df = queries.get_total_laws_by_player()

    # Validation checks
    issues = []

    # 1. Total laws should always be >= unique pairs
    invalid = df[df['total_laws_adopted'] < df['unique_law_pairs']]
    if not invalid.empty:
        issues.append(f"Found {len(invalid)} players with total_laws < unique_pairs")
        print(invalid[['player_name', 'match_id', 'total_laws_adopted', 'unique_law_pairs']])

    # 2. Law switches should be non-negative
    invalid = df[df['law_switches'] < 0]
    if not invalid.empty:
        issues.append(f"Found {len(invalid)} players with negative law_switches")

    # 3. Report summary stats
    print(f"\nLaw Metrics Summary:")
    print(f"  Total players: {len(df)}")
    print(f"  Players who switched: {(df['law_switches'] > 0).sum()}")
    print(f"  Avg switches per player: {df['law_switches'].mean():.2f}")
    print(f"  Max switches: {df['law_switches'].max()}")

    if issues:
        raise ValueError(f"Validation failed:\n" + "\n".join(issues))

    print("\n✅ All validations passed!")

if __name__ == "__main__":
    validate_law_metrics()
```

**Run after implementation**:
```bash
uv run python scripts/validate_law_metrics.py
```

---

## Rollout Plan

### Phase 1: Core Queries (1-2 hours)
1. Update `get_total_laws_by_player()` - use events table
2. Update `get_law_milestone_timing()` - use events table
3. Update `get_player_law_progression_stats()` - use events table
4. Write unit tests
5. Run validation script

### Phase 2: Charts (1-2 hours)
1. Update `create_law_progression_chart()` - support new columns
2. Update `create_law_milestone_chart()` - support new columns
3. Update any other charts that use `total_laws`
4. Test with real match data (match 33)

### Phase 3: Validation (1 hour)
1. Run full test suite
2. Manually verify Match 33 shows correct counts
3. Check a few other matches for sanity
4. Update documentation

### Phase 4 (Optional): Advanced Charts
- Only if users request law switching analysis
- Add `create_law_switching_behavior_chart()`
- Add to matches page

---

## Backwards Compatibility

**For external consumers** (if dashboard is used by others):

Old queries will continue to work because:
- New columns are added, old ones not removed
- Charts accept both `total_laws` and `total_laws_adopted`
- Milestone calculations more accurate but similar results

**Deprecation path** (if needed later):
1. Log warning when `total_laws` column accessed
2. After 2 months, remove `total_laws` column entirely

---

## Success Criteria

✅ Match 33 screenshot shows:
- alcaras: 9 laws (not counting Serfdom/Colonies switches separately)
- Nizar: 9 laws

✅ All existing tests pass

✅ Validation script reports no issues

✅ Charts render without errors

✅ Law switching data preserved for future analysis

---

## Related Files

**Queries**:
- `tournament_visualizer/data/queries.py:980` - `get_law_progression()`
- `tournament_visualizer/data/queries.py:1006` - `get_total_laws_by_player()`
- `tournament_visualizer/data/queries.py:1043` - `get_law_milestone_timing()`
- `tournament_visualizer/data/queries.py:1095` - `get_player_law_progression_stats()`
- `tournament_visualizer/data/queries.py:1489` - `get_law_progression_by_match()` ✅ Already correct

**Charts**:
- `tournament_visualizer/components/charts.py:957` - `create_law_progression_chart()`
- `tournament_visualizer/components/charts.py:1006` - `create_law_milestone_chart()`
- `tournament_visualizer/components/charts.py:1643` - `create_law_milestone_comparison_chart()`
- `tournament_visualizer/components/charts.py:1806` - `create_law_milestone_distribution_chart()`
- `tournament_visualizer/components/charts.py:1872` - `create_law_progression_heatmap()`
- `tournament_visualizer/components/charts.py:1975` - `create_law_efficiency_scatter()`

**Tests**:
- `tests/test_charts_law_progression.py` - Existing tests
- `tests/test_queries_law_metrics.py` - New tests (create this)

**Validation**:
- `scripts/validate_law_metrics.py` - New script (create this)

---

## DRY/YAGNI Decision Log

### What We Avoided (YAGNI)

❌ **UI dropdowns for metric selection** - No evidence users need this
❌ **Separate charts for each metric** - Can add later if needed
❌ **Database schema changes** - Data already exists in events table
❌ **New API endpoints** - Just update existing queries
❌ **Complex law pair mapping logic** - Only needed if we migrate away from player_statistics

### What We Reused (DRY)

✅ **Common CTE pattern** - `law_events AS (SELECT FROM events WHERE event_type='LAW_ADOPTED')`
✅ **Existing chart infrastructure** - No new chart types, just data changes
✅ **Existing test patterns** - Follow `test_charts_law_progression.py` style
✅ **Column name compatibility** - Support both old and new names in one place

### Future Refactoring Opportunities

If this pattern works well:
1. Consider creating a `QueryCTELibrary` class with reusable CTEs
2. Add a `get_law_metrics()` helper that all queries call
3. Create a `LawMetrics` dataclass for type safety

But **don't do these now** - wait until we have 3+ places using the same pattern.

---

## Questions & Answers

**Q**: Should we add a `law_switches_per_turn` metric?
**A**: No (YAGNI). Wait for user request.

**Q**: Should we cache law metrics in a materialized view?
**A**: No. Player count is small (~65), queries are fast.

**Q**: Should we update the parser to store correct counts?
**A**: No. Events table is already correct; parser can stay as-is.

**Q**: What if events and statistics disagree?
**A**: Events table is source of truth. Statistics table remains for law pair classification.

---

## Sign-off

Before merging:
- [ ] All tests pass (`uv run pytest -v`)
- [ ] Validation script runs clean
- [ ] Match 33 displays correctly in UI
- [ ] Code review completed
- [ ] Documentation updated (this file marked as "Completed")
