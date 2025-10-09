# Fix Application After Turn-by-Turn History Database Changes

**Date:** October 9, 2025
**Status:** Ready for Implementation
**Estimated Time:** 4-6 hours
**Related Plan:** [turn-by-turn-history-implementation-plan.md](turn-by-turn-history-implementation-plan.md)

---

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Issues Found](#issues-found)
- [Implementation Tasks](#implementation-tasks)
  - [Phase 1: Fix Circular Dependency](#phase-1-fix-circular-dependency)
  - [Phase 2: Update Query References](#phase-2-update-query-references)
  - [Phase 3: Add History Query Functions](#phase-3-add-history-query-functions)
  - [Phase 4: Testing & Verification](#phase-4-testing--verification)
- [Testing Strategy](#testing-strategy)
- [Success Criteria](#success-criteria)

---

## Overview

### The Problem
After implementing turn-by-turn history tables (as detailed in `turn-by-turn-history-implementation-plan.md`), the web application has several issues:

1. **Circular dependency error** in the Matches page preventing proper navigation
2. **References to dropped/renamed tables** causing query failures
3. **Missing query functions** for the new history data preventing visualizations

### What Changed in the Database

According to migration `002_add_history_tables`:
- **Dropped:** `game_state` table (was broken - all rows had turn_number=0)
- **Renamed:** `resources` → `player_yield_history`
- **Added:** 5 new history tables:
  - `player_points_history` - Victory points per turn
  - `player_military_history` - Military power per turn
  - `player_legitimacy_history` - Legitimacy per turn
  - `family_opinion_history` - Family opinions per turn
  - `religion_opinion_history` - Religion opinions per turn

### Current State
- ✅ Database migration completed successfully
- ✅ ETL/parser code is working (data is being loaded)
- ❌ Query layer has broken references
- ❌ Matches page has circular dependency
- ❌ No query functions for new history tables

---

## Prerequisites

### Required Knowledge
- **Python**: Type annotations, dictionaries, list operations
- **Dash**: Callback patterns, Input/Output dependencies
- **SQL**: Basic SELECT queries, JOINs
- **Testing**: pytest basics, test structure

### Tools You'll Use
- `uv run pytest` - Run tests
- `uv run python manage.py restart` - Restart the web app
- Browser - View the running application
- `uv run duckdb tournament_data.duckdb -readonly` - Query the database

### Files You'll Touch
```
tournament_visualizer/
├── pages/
│   └── matches.py              # Fix circular dependency
├── data/
│   └── queries.py              # Update table references, add new functions
tests/
└── test_queries.py             # Add tests for new queries
```

---

## Issues Found

### Issue 1: Circular Dependency in Matches Page

**File:** `tournament_visualizer/pages/matches.py`
**Lines:** 118-152

**Problem:**
Two callbacks create a circular dependency:
```python
# Callback 1: Lines 118-135
@callback(Output("match-selector", "value"), Input("match-url", "search"))
def set_match_from_url(search: str) -> Optional[int]:
    # Reads URL query, writes to match-selector
    ...

# Callback 2: Lines 138-152
@callback(Output("match-url", "search"), Input("match-selector", "value"))
def update_url_from_match(match_id: Optional[int]) -> str:
    # Reads match-selector, writes to URL query
    ...
```

This creates a cycle: `match-selector.value → match-url.search → match-selector.value`

**Browser Error:**
```
Dependency Cycle Found: match-selector.value -> match-url.search -> match-selector.value
```

**Impact:** Matches page doesn't work, users can't select matches.

---

### Issue 2: References to Dropped/Renamed Tables

**File:** `tournament_visualizer/data/queries.py`

**Problems:**

1. **Line 233-259: `get_turn_progression_data()` references `game_state`**
   ```python
   query = """
   SELECT
       gs.turn_number,
       gs.game_year,
       ...
   FROM game_state gs  # ← BROKEN: table was dropped
   ```
   **Impact:** Any code calling this function will fail.

2. **Line 260-292: `get_resource_progression()` references `resources`**
   ```python
   query = """
   SELECT
       r.turn_number,
       ...
   FROM resources r  # ← BROKEN: table renamed to player_yield_history
   ```
   **Impact:** Resource progression queries fail.

3. **Line 485-528: `get_database_statistics()` references both**
   ```python
   tables = [
       "matches",
       "players",
       "game_state",  # ← BROKEN: dropped table
       "events",
       "territories",
       "resources",   # ← BROKEN: renamed table
   ]
   ```
   **Impact:** Statistics page fails to load.

---

### Issue 3: Missing Query Functions for New History Tables

**File:** `tournament_visualizer/data/queries.py`

**Problem:**
No functions exist to query the 5 new history tables:
- `player_points_history` (✅ has 1,842 rows - data exists!)
- `player_military_history`
- `player_legitimacy_history`
- `family_opinion_history`
- `religion_opinion_history`

**Impact:** Cannot create visualizations for turn-by-turn history data that was just added.

---

## Implementation Tasks

### Phase 1: Fix Circular Dependency

**Goal:** Remove circular dependency from Matches page so it loads properly.

**Strategy:** Use Dash's `prevent_initial_call` and state management to break the cycle.

#### Task 1.1: Refactor URL/Selector Synchronization

**Time:** 30 minutes
**File:** `tournament_visualizer/pages/matches.py`

**The Problem Explained:**

Dash callbacks fire when their Input changes. The current setup causes an infinite loop:
1. URL changes → triggers `set_match_from_url()` → updates `match-selector`
2. `match-selector` changes → triggers `update_url_from_match()` → updates URL
3. Go to step 1 (infinite loop!)

**The Solution:**

Use `dash.callback_context` to detect which input triggered the callback, and only update if needed.

**Steps:**

1. **Read the current code carefully:**
   ```bash
   # Look at lines 118-152
   uv run python -c "
   with open('tournament_visualizer/pages/matches.py') as f:
       lines = f.readlines()
       print(''.join(lines[117:153]))
   "
   ```

2. **Replace both callbacks with a single multi-output callback:**

   Delete lines 118-152 and replace with:
   ```python
   @callback(
       [
           Output("match-selector", "value"),
           Output("match-url", "search"),
       ],
       [
           Input("match-url", "search"),
           Input("match-selector", "value"),
       ],
       prevent_initial_call=False,
   )
   def sync_match_selection(url_search: str, selector_value: Optional[int]) -> tuple:
       """Synchronize match selection between URL and dropdown.

       This callback handles bidirectional sync without creating a circular dependency
       by checking which input triggered the callback.

       Args:
           url_search: URL query string (e.g., "?match_id=123")
           selector_value: Currently selected match ID from dropdown

       Returns:
           Tuple of (selector_value, url_search)
       """
       ctx = dash.callback_context

       # On initial load (no trigger), check URL for match_id
       if not ctx.triggered:
           from urllib.parse import parse_qs

           if url_search:
               params = parse_qs(url_search.lstrip("?"))
               match_id = params.get("match_id", [None])[0]
               if match_id:
                   return int(match_id), url_search
           return None, ""

       # Check which input triggered this callback
       trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

       # If URL changed (user navigated), update selector to match
       if trigger_id == "match-url":
           from urllib.parse import parse_qs

           if url_search:
               params = parse_qs(url_search.lstrip("?"))
               match_id = params.get("match_id", [None])[0]
               if match_id:
                   return int(match_id), url_search
           return None, ""

       # If selector changed (user picked from dropdown), update URL to match
       elif trigger_id == "match-selector":
           if selector_value:
               new_url = f"?match_id={selector_value}"
               return selector_value, new_url
           return None, ""

       # Fallback (shouldn't reach here)
       return dash.no_update, dash.no_update
   ```

3. **Understanding the fix:**

   **Why this works:**
   - `prevent_initial_call=False` allows it to run on page load
   - `callback_context` tells us WHICH input changed
   - We only update the OTHER output (break the cycle)
   - If URL changed → update selector
   - If selector changed → update URL
   - Never update both at once!

**Testing:**
```bash
# Restart the app
uv run python manage.py restart

# Visit in browser
open http://localhost:8050/matches

# Test scenarios:
# 1. Navigate to /matches?match_id=10 - selector should auto-select match 10
# 2. Change dropdown - URL should update
# 3. Browser back/forward - selector should follow URL
```

**Expected:** No more "Circular Dependencies" error in browser console.

**Commit:**
```bash
git add tournament_visualizer/pages/matches.py
git commit -m "fix: Resolve circular dependency in matches page URL/selector sync

- Replace two circular callbacks with single bidirectional sync callback
- Use callback_context to detect which input triggered the callback
- Only update the opposite output to break the cycle
- Fixes browser error: Dependency Cycle Found"
```

---

### Phase 2: Update Query References

**Goal:** Fix queries that reference dropped/renamed tables.

#### Task 2.1: Fix get_turn_progression_data()

**Time:** 30 minutes
**File:** `tournament_visualizer/data/queries.py`
**Lines:** 233-259

**The Issue:**
This function queries the `game_state` table which was dropped. The migration removed it because all rows had `turn_number=0` (broken data).

**Decision:** Since game_state data was broken anyway, we should either:
1. Remove this function entirely (if it's not used)
2. Return empty data with a comment explaining why

**Steps:**

1. **Check if the function is actually used:**
   ```bash
   grep -rn "get_turn_progression_data" tournament_visualizer/pages/ --include="*.py"
   ```

   **Expected:** Should show if any page calls this function.

2. **If NOT used anywhere (likely):**

   Comment out the entire function and add a deprecation note:
   ```python
   # DEPRECATED: This function queried the game_state table which was removed
   # in migration 002. The game_state table had broken data (all turn_number=0).
   #
   # def get_turn_progression_data(self, match_id: int) -> pd.DataFrame:
   #     """Get turn-by-turn progression data for a specific match.
   #
   #     DEPRECATED: game_state table was removed. This data was broken anyway.
   #     Use get_event_timeline() for turn-by-turn event data instead.
   #     """
   #     pass

   def get_turn_progression_data(self, match_id: int) -> pd.DataFrame:
       """Get turn-by-turn progression data for a specific match.

       DEPRECATED: The game_state table was removed in migration 002 because
       all rows had turn_number=0 (broken data). Use get_event_timeline() or
       the new history tables instead.

       Returns:
           Empty DataFrame with expected columns
       """
       import pandas as pd
       return pd.DataFrame(columns=[
           "turn_number",
           "game_year",
           "active_player",
           "civilization",
           "events_count"
       ])
   ```

3. **If IS used somewhere:**

   You'll need to rewrite it to use alternative data sources. Come back to this after understanding how it's used.

**Testing:**
```bash
# Quick Python test
uv run python -c "
from tournament_visualizer.data.queries import get_queries
queries = get_queries()
df = queries.get_turn_progression_data(1)
print(f'Result: {len(df)} rows')
print(f'Columns: {list(df.columns)}')
"
```

**Expected:** Should return empty DataFrame without error.

---

#### Task 2.2: Fix get_resource_progression()

**Time:** 30 minutes
**File:** `tournament_visualizer/data/queries.py`
**Lines:** 260-292

**The Issue:**
Queries `resources` table which was renamed to `player_yield_history`.

**The Fix:**
Simply rename the table in the query. The renamed table has the same structure:
- `resource_id` → still exists (wasn't renamed)
- `resource_type` → still exists (wasn't renamed to yield_type)
- `amount` → still exists

**Steps:**

1. **Update the query:**

   Find this line (around line 272):
   ```python
   base_query = """
   SELECT
       r.turn_number,
       p.player_name,
       r.resource_type,
       r.amount
   FROM resources r
   ```

   Replace with:
   ```python
   base_query = """
   SELECT
       r.turn_number,
       p.player_name,
       r.resource_type,
       r.amount
   FROM player_yield_history r
   ```

2. **That's it!** The rest of the function is fine.

**Testing:**
```bash
# Test with a real match
uv run python -c "
from tournament_visualizer.data.queries import get_queries
queries = get_queries()
df = queries.get_resource_progression(1)  # Match ID 1
print(f'Results: {len(df)} rows')
if not df.empty:
    print(df.head())
"
```

**Expected:** Should return yield history data for match 1.

**Commit:**
```bash
git add tournament_visualizer/data/queries.py
git commit -m "fix: Update get_resource_progression to use renamed table

- Query player_yield_history instead of resources
- Table was renamed in migration 002
- Function logic unchanged, just table name update"
```

---

#### Task 2.3: Fix get_database_statistics()

**Time:** 15 minutes
**File:** `tournament_visualizer/data/queries.py`
**Lines:** 485-528

**The Issue:**
Tries to count rows in `game_state` and `resources` which no longer exist.

**The Fix:**
Update the tables list and adjust count reporting.

**Steps:**

1. **Find the tables array (around line 493):**
   ```python
   tables = [
       "matches",
       "players",
       "game_state",    # ← REMOVE THIS
       "events",
       "territories",
       "resources",     # ← CHANGE THIS
   ]
   ```

2. **Replace with:**
   ```python
   tables = [
       "matches",
       "players",
       "events",
       "territories",
       "player_yield_history",  # Renamed from resources
       # Note: game_state was removed in migration 002 (had broken data)
   ]
   ```

3. **Update the summary key name (optional):**

   Around line 502, you might see:
   ```python
   stats[f"{table}_count"] = result[0] if result else 0
   ```

   This will now create `player_yield_history_count` which is verbose. Optionally update:
   ```python
   # Make the key names cleaner
   for table in tables:
       result = self.db.fetch_one(f"SELECT COUNT(*) FROM {table}")
       # Use friendly name for yield history
       key_name = "yield_history" if table == "player_yield_history" else table
       stats[f"{key_name}_count"] = result[0] if result else 0
   ```

**Testing:**
```bash
uv run python -c "
from tournament_visualizer.data.queries import get_queries
queries = get_queries()
stats = queries.get_database_statistics()
print('Statistics:', stats)
"
```

**Expected:** Should return stats without errors. Check that `yield_history_count` is present.

**Commit:**
```bash
git add tournament_visualizer/data/queries.py
git commit -m "fix: Update get_database_statistics for renamed/removed tables

- Remove game_state from tables list (dropped in migration 002)
- Replace resources with player_yield_history (renamed)
- Add comment explaining changes"
```

---

### Phase 3: Add History Query Functions

**Goal:** Add query functions for the 5 new history tables so we can visualize turn-by-turn data.

#### Task 3.1: Add get_points_history_by_match()

**Time:** 30 minutes
**File:** `tournament_visualizer/data/queries.py`

**Context:** The `player_points_history` table contains turn-by-turn victory points for each player in each match. This is perfect for creating racing line charts showing point progression.

**Steps:**

1. **Add the query function after `get_cumulative_law_count_by_turn()` (around line 1108):**

   ```python
   def get_points_history_by_match(self, match_id: int) -> pd.DataFrame:
       """Get victory points progression for all players in a match.

       Returns data from the player_points_history table which tracks
       turn-by-turn victory point totals for each player.

       Args:
           match_id: Match ID to query

       Returns:
           DataFrame with columns:
           - player_id: Database player ID
           - player_name: Player name
           - turn_number: Turn number
           - points: Victory points at that turn

       Example usage:
           df = queries.get_points_history_by_match(1)
           # Create a line chart with turn_number on x-axis, points on y-axis,
           # with separate lines for each player_name
       """
       query = """
       SELECT
           ph.player_id,
           p.player_name,
           p.civilization,
           ph.turn_number,
           ph.points
       FROM player_points_history ph
       JOIN players p ON ph.player_id = p.player_id AND ph.match_id = p.match_id
       WHERE ph.match_id = ?
       ORDER BY ph.turn_number, ph.player_id
       """

       with self.db.get_connection() as conn:
           return conn.execute(query, [match_id]).df()
   ```

2. **Add a companion function for ALL matches:**

   ```python
   def get_points_history_all_matches(self) -> pd.DataFrame:
       """Get victory points progression across all matches.

       Useful for aggregate analysis like "how do points typically progress?"

       Returns:
           DataFrame with match_id, player_id, player_name, turn_number, points
       """
       query = """
       SELECT
           ph.match_id,
           ph.player_id,
           p.player_name,
           p.civilization,
           ph.turn_number,
           ph.points
       FROM player_points_history ph
       JOIN players p ON ph.player_id = p.player_id AND ph.match_id = p.match_id
       ORDER BY ph.match_id, ph.turn_number, ph.player_id
       """

       with self.db.get_connection() as conn:
           return conn.execute(query).df()
   ```

**Testing:**
```bash
uv run python -c "
from tournament_visualizer.data.queries import get_queries
queries = get_queries()

# Test single match
df = queries.get_points_history_by_match(1)
print(f'Match 1 points history: {len(df)} rows')
if not df.empty:
    print(df.head(10))
    print(f'Columns: {list(df.columns)}')

# Test all matches
df_all = queries.get_points_history_all_matches()
print(f'All matches points history: {len(df_all)} rows')
"
```

**Expected:** Should return data matching the 1,842 rows we saw earlier in player_points_history.

---

#### Task 3.2: Add get_yield_history_by_match()

**Time:** 30 minutes
**File:** `tournament_visualizer/data/queries.py`

**Context:** This replaces/enhances the `get_resource_progression()` function. The `player_yield_history` table has per-turn yield production for each yield type.

**Steps:**

1. **Add after the points history functions:**

   ```python
   def get_yield_history_by_match(
       self,
       match_id: int,
       yield_types: Optional[List[str]] = None
   ) -> pd.DataFrame:
       """Get yield production progression for all players in a match.

       Returns data from player_yield_history showing turn-by-turn
       yield production rates (YIELD_GROWTH, YIELD_CIVICS, etc.)

       Args:
           match_id: Match ID to query
           yield_types: Optional list of yield types to filter
                       (e.g., ['YIELD_GROWTH', 'YIELD_SCIENCE'])
                       If None, returns all yield types.

       Returns:
           DataFrame with columns:
           - player_id, player_name, civilization
           - turn_number
           - resource_type: The yield type (YIELD_GROWTH, etc.)
           - amount: Production rate for that yield on that turn
       """
       base_query = """
       SELECT
           yh.player_id,
           p.player_name,
           p.civilization,
           yh.turn_number,
           yh.resource_type,
           yh.amount
       FROM player_yield_history yh
       JOIN players p ON yh.player_id = p.player_id AND yh.match_id = p.match_id
       WHERE yh.match_id = ?
       """

       params = [match_id]

       if yield_types:
           placeholders = ", ".join(["?" for _ in yield_types])
           base_query += f" AND yh.resource_type IN ({placeholders})"
           params.extend(yield_types)

       base_query += " ORDER BY yh.turn_number, yh.player_id, yh.resource_type"

       with self.db.get_connection() as conn:
           return conn.execute(base_query, params).df()
   ```

2. **Add a helper to get available yield types:**

   ```python
   def get_yield_types(self, match_id: Optional[int] = None) -> List[str]:
       """Get list of available yield types.

       Args:
           match_id: Optional match ID to filter by. If None, returns all yield types
                    across all matches.

       Returns:
           List of yield type names (e.g., ['YIELD_GROWTH', 'YIELD_CIVICS', ...])
       """
       if match_id:
           query = """
           SELECT DISTINCT resource_type
           FROM player_yield_history
           WHERE match_id = ?
           ORDER BY resource_type
           """
           params = [match_id]
       else:
           query = """
           SELECT DISTINCT resource_type
           FROM player_yield_history
           ORDER BY resource_type
           """
           params = []

       with self.db.get_connection() as conn:
           df = conn.execute(query, params).df()
           return df["resource_type"].tolist() if not df.empty else []
   ```

**Testing:**
```bash
uv run python -c "
from tournament_visualizer.data.queries import get_queries
queries = get_queries()

# Get available yield types
types = queries.get_yield_types()
print(f'Available yield types: {types}')

# Test single match, all yields
df = queries.get_yield_history_by_match(1)
print(f'Match 1 yield history (all types): {len(df)} rows')

# Test single match, filtered yields
df_filtered = queries.get_yield_history_by_match(1, ['YIELD_GROWTH', 'YIELD_SCIENCE'])
print(f'Match 1 yield history (filtered): {len(df_filtered)} rows')
"
```

---

#### Task 3.3: Add get_military_history_by_match()

**Time:** 20 minutes
**File:** `tournament_visualizer/data/queries.py`

**Steps:**

```python
def get_military_history_by_match(self, match_id: int) -> pd.DataFrame:
    """Get military power progression for all players in a match.

    Returns data from player_military_history showing turn-by-turn
    military strength values.

    Args:
        match_id: Match ID to query

    Returns:
        DataFrame with columns:
        - player_id, player_name, civilization
        - turn_number
        - military_power: Military strength value for that turn
    """
    query = """
    SELECT
        mh.player_id,
        p.player_name,
        p.civilization,
        mh.turn_number,
        mh.military_power
    FROM player_military_history mh
    JOIN players p ON mh.player_id = p.player_id AND mh.match_id = p.match_id
    WHERE mh.match_id = ?
    ORDER BY mh.turn_number, mh.player_id
    """

    with self.db.get_connection() as conn:
        return conn.execute(query, [match_id]).df()
```

**Testing:**
```bash
uv run python -c "
from tournament_visualizer.data.queries import get_queries
queries = get_queries()
df = queries.get_military_history_by_match(1)
print(f'Military history: {len(df)} rows')
if not df.empty:
    print(df.head())
"
```

---

#### Task 3.4: Add get_legitimacy_history_by_match()

**Time:** 20 minutes
**File:** `tournament_visualizer/data/queries.py`

**Steps:**

```python
def get_legitimacy_history_by_match(self, match_id: int) -> pd.DataFrame:
    """Get legitimacy progression for all players in a match.

    Returns data from player_legitimacy_history showing turn-by-turn
    legitimacy values (governance stability, 0-100).

    Args:
        match_id: Match ID to query

    Returns:
        DataFrame with columns:
        - player_id, player_name, civilization
        - turn_number
        - legitimacy: Legitimacy value (0-100) for that turn
    """
    query = """
    SELECT
        lh.player_id,
        p.player_name,
        p.civilization,
        lh.turn_number,
        lh.legitimacy
    FROM player_legitimacy_history lh
    JOIN players p ON lh.player_id = p.player_id AND lh.match_id = p.match_id
    WHERE lh.match_id = ?
    ORDER BY lh.turn_number, lh.player_id
    """

    with self.db.get_connection() as conn:
        return conn.execute(query, [match_id]).df()
```

---

#### Task 3.5: Add get_family_opinion_history_by_match()

**Time:** 25 minutes
**File:** `tournament_visualizer/data/queries.py`

**Context:** Family opinion is nested - each player has opinions from multiple families, tracked per turn.

**Steps:**

```python
def get_family_opinion_history_by_match(
    self,
    match_id: int,
    family_names: Optional[List[str]] = None
) -> pd.DataFrame:
    """Get family opinion progression for all players in a match.

    Returns data from family_opinion_history showing turn-by-turn
    family opinion values (0-100) for each family.

    Args:
        match_id: Match ID to query
        family_names: Optional list of family names to filter
                     (e.g., ['FAMILY_JULII', 'FAMILY_BRUTII'])

    Returns:
        DataFrame with columns:
        - player_id, player_name, civilization
        - turn_number
        - family_name: Name of the family (e.g., 'FAMILY_JULII')
        - opinion: Opinion value (0-100) for that family on that turn
    """
    base_query = """
    SELECT
        fh.player_id,
        p.player_name,
        p.civilization,
        fh.turn_number,
        fh.family_name,
        fh.opinion
    FROM family_opinion_history fh
    JOIN players p ON fh.player_id = p.player_id AND fh.match_id = p.match_id
    WHERE fh.match_id = ?
    """

    params = [match_id]

    if family_names:
        placeholders = ", ".join(["?" for _ in family_names])
        base_query += f" AND fh.family_name IN ({placeholders})"
        params.extend(family_names)

    base_query += " ORDER BY fh.turn_number, fh.player_id, fh.family_name"

    with self.db.get_connection() as conn:
        return conn.execute(base_query, params).df()

def get_family_names(self, match_id: Optional[int] = None) -> List[str]:
    """Get list of family names that appear in the data.

    Args:
        match_id: Optional match ID to filter by

    Returns:
        List of family names (e.g., ['FAMILY_JULII', 'FAMILY_BRUTII', ...])
    """
    if match_id:
        query = """
        SELECT DISTINCT family_name
        FROM family_opinion_history
        WHERE match_id = ?
        ORDER BY family_name
        """
        params = [match_id]
    else:
        query = """
        SELECT DISTINCT family_name
        FROM family_opinion_history
        ORDER BY family_name
        """
        params = []

    with self.db.get_connection() as conn:
        df = conn.execute(query, params).df()
        return df["family_name"].tolist() if not df.empty else []
```

---

#### Task 3.6: Add get_religion_opinion_history_by_match()

**Time:** 25 minutes
**File:** `tournament_visualizer/data/queries.py`

**Steps:**

```python
def get_religion_opinion_history_by_match(
    self,
    match_id: int,
    religion_names: Optional[List[str]] = None
) -> pd.DataFrame:
    """Get religion opinion progression for all players in a match.

    Returns data from religion_opinion_history showing turn-by-turn
    religion opinion values (0-100) for each religion.

    Args:
        match_id: Match ID to query
        religion_names: Optional list of religion names to filter
                       (e.g., ['RELIGION_JUPITER', 'RELIGION_BAAL'])

    Returns:
        DataFrame with columns:
        - player_id, player_name, civilization
        - turn_number
        - religion_name: Name of the religion
        - opinion: Opinion value (0-100) for that religion on that turn
    """
    base_query = """
    SELECT
        rh.player_id,
        p.player_name,
        p.civilization,
        rh.turn_number,
        rh.religion_name,
        rh.opinion
    FROM religion_opinion_history rh
    JOIN players p ON rh.player_id = p.player_id AND rh.match_id = p.match_id
    WHERE rh.match_id = ?
    """

    params = [match_id]

    if religion_names:
        placeholders = ", ".join(["?" for _ in religion_names])
        base_query += f" AND rh.religion_name IN ({placeholders})"
        params.extend(religion_names)

    base_query += " ORDER BY rh.turn_number, rh.player_id, rh.religion_name"

    with self.db.get_connection() as conn:
        return conn.execute(base_query, params).df()

def get_religion_names(self, match_id: Optional[int] = None) -> List[str]:
    """Get list of religion names that appear in the data.

    Args:
        match_id: Optional match ID to filter by

    Returns:
        List of religion names (e.g., ['RELIGION_JUPITER', 'RELIGION_BAAL', ...])
    """
    if match_id:
        query = """
        SELECT DISTINCT religion_name
        FROM religion_opinion_history
        WHERE match_id = ?
        ORDER BY religion_name
        """
        params = [match_id]
    else:
        query = """
        SELECT DISTINCT religion_name
        FROM religion_opinion_history
        ORDER BY religion_name
        """
        params = []

    with self.db.get_connection() as conn:
        df = conn.execute(query, params).df()
        return df["religion_name"].tolist() if not df.empty else []
```

**Testing All New Functions:**
```bash
uv run python -c "
from tournament_visualizer.data.queries import get_queries
queries = get_queries()

# Test all new history query functions
match_id = 1

print('Points history:', len(queries.get_points_history_by_match(match_id)))
print('Yield history:', len(queries.get_yield_history_by_match(match_id)))
print('Military history:', len(queries.get_military_history_by_match(match_id)))
print('Legitimacy history:', len(queries.get_legitimacy_history_by_match(match_id)))
print('Family opinions:', len(queries.get_family_opinion_history_by_match(match_id)))
print('Religion opinions:', len(queries.get_religion_opinion_history_by_match(match_id)))

print('\nYield types:', queries.get_yield_types(match_id))
print('Families:', queries.get_family_names(match_id))
print('Religions:', queries.get_religion_names(match_id))
"
```

**Commit:**
```bash
git add tournament_visualizer/data/queries.py
git commit -m "feat: Add query functions for turn-by-turn history tables

- get_points_history_by_match(): Victory points progression
- get_yield_history_by_match(): Yield production rates over time
- get_military_history_by_match(): Military power progression
- get_legitimacy_history_by_match(): Legitimacy values over time
- get_family_opinion_history_by_match(): Family opinion tracking
- get_religion_opinion_history_by_match(): Religion opinion tracking
- Helper functions: get_yield_types(), get_family_names(), get_religion_names()

These functions query the 5 new history tables added in migration 002."
```

---

### Phase 4: Testing & Verification

**Goal:** Verify all fixes work and app runs without errors.

#### Task 4.1: Manual Testing

**Time:** 30 minutes

**Steps:**

1. **Restart the application:**
   ```bash
   uv run python manage.py restart
   ```

2. **Test Overview Page:**
   ```bash
   open http://localhost:8050/
   ```

   **Check:**
   - ✅ Page loads without errors
   - ✅ Statistics cards show data
   - ✅ Charts render properly
   - ✅ No console errors

3. **Test Matches Page:**
   ```bash
   open http://localhost:8050/matches
   ```

   **Check:**
   - ✅ Page loads without circular dependency error
   - ✅ Dropdown populates with matches
   - ✅ Selecting a match updates URL
   - ✅ URL with ?match_id=X auto-selects match
   - ✅ Match details display
   - ✅ All tabs work (Turn Progression, Technology & Research, Player Statistics, Game Settings)

4. **Test Players Page:**
   ```bash
   open http://localhost:8050/players
   ```

   **Check:**
   - ✅ Page loads
   - ✅ Player rankings display
   - ✅ Charts render

5. **Test Maps Page:**
   ```bash
   open http://localhost:8050/maps
   ```

   **Check:**
   - ✅ Page loads
   - ✅ Map data displays

6. **Check Browser Console:**

   Open browser DevTools (F12), check Console tab:
   - ✅ No "Circular Dependencies" errors
   - ✅ No "table not found" errors
   - ✅ No 500 server errors

7. **Check Server Logs:**
   ```bash
   uv run python manage.py logs
   ```

   **Look for:**
   - ❌ Any error messages
   - ❌ SQL errors
   - ❌ Missing table errors

---

#### Task 4.2: Automated Testing

**Time:** 1 hour

**File:** `tests/test_queries.py` (create if doesn't exist)

**Steps:**

1. **Create test file if it doesn't exist:**
   ```bash
   touch tests/test_queries.py
   ```

2. **Add tests for fixed functions:**

   ```python
   """Tests for query functions, focusing on recent fixes."""

   import pytest
   from tournament_visualizer.data.queries import TournamentQueries
   from tournament_visualizer.data.database import get_database


   @pytest.fixture
   def queries():
       """Get queries instance with real database."""
       return TournamentQueries()


   class TestFixedQueries:
       """Test queries that were fixed for table rename/removal."""

       def test_get_resource_progression_uses_correct_table(self, queries):
           """Test that get_resource_progression queries player_yield_history."""
           # This should not raise an error about missing 'resources' table
           try:
               df = queries.get_resource_progression(1)
               # May be empty if no data, but should not error
               assert df is not None
           except Exception as e:
               # Should not mention 'resources' table
               assert "resources" not in str(e).lower()

       def test_get_database_statistics_excludes_dropped_tables(self, queries):
           """Test that get_database_statistics doesn't query dropped tables."""
           stats = queries.get_database_statistics()

           # Should not have game_state in results
           assert "game_state_count" not in stats

           # Should have player_yield_history or yield_history
           assert "yield_history_count" in stats or "player_yield_history_count" in stats

       def test_get_turn_progression_data_returns_empty(self, queries):
           """Test that deprecated get_turn_progression_data returns empty data."""
           df = queries.get_turn_progression_data(1)

           # Should return DataFrame (not error)
           assert df is not None
           # Should be empty (table was dropped)
           assert len(df) == 0


   class TestNewHistoryQueries:
       """Test new query functions for history tables."""

       def test_get_points_history_by_match(self, queries):
           """Test points history query."""
           df = queries.get_points_history_by_match(1)

           assert df is not None
           # Check columns exist
           if not df.empty:
               assert "player_id" in df.columns
               assert "player_name" in df.columns
               assert "turn_number" in df.columns
               assert "points" in df.columns

       def test_get_yield_history_by_match(self, queries):
           """Test yield history query."""
           df = queries.get_yield_history_by_match(1)

           assert df is not None
           if not df.empty:
               assert "player_id" in df.columns
               assert "turn_number" in df.columns
               assert "resource_type" in df.columns
               assert "amount" in df.columns

       def test_get_yield_history_with_filter(self, queries):
           """Test yield history with type filter."""
           df = queries.get_yield_history_by_match(1, ["YIELD_GROWTH"])

           assert df is not None
           if not df.empty:
               # All rows should be YIELD_GROWTH
               assert all(df["resource_type"] == "YIELD_GROWTH")

       def test_get_military_history_by_match(self, queries):
           """Test military history query."""
           df = queries.get_military_history_by_match(1)

           assert df is not None
           if not df.empty:
               assert "military_power" in df.columns

       def test_get_legitimacy_history_by_match(self, queries):
           """Test legitimacy history query."""
           df = queries.get_legitimacy_history_by_match(1)

           assert df is not None
           if not df.empty:
               assert "legitimacy" in df.columns
               # Legitimacy should be 0-100
               assert all((df["legitimacy"] >= 0) & (df["legitimacy"] <= 100))

       def test_get_family_opinion_history_by_match(self, queries):
           """Test family opinion history query."""
           df = queries.get_family_opinion_history_by_match(1)

           assert df is not None
           if not df.empty:
               assert "family_name" in df.columns
               assert "opinion" in df.columns

       def test_get_religion_opinion_history_by_match(self, queries):
           """Test religion opinion history query."""
           df = queries.get_religion_opinion_history_by_match(1)

           assert df is not None
           if not df.empty:
               assert "religion_name" in df.columns
               assert "opinion" in df.columns

       def test_get_yield_types(self, queries):
           """Test getting available yield types."""
           types = queries.get_yield_types()

           assert isinstance(types, list)
           # Common yield types should be present if data exists
           if types:
               # Just check it returns a list of strings
               assert all(isinstance(t, str) for t in types)

       def test_get_family_names(self, queries):
           """Test getting family names."""
           families = queries.get_family_names()

           assert isinstance(families, list)

       def test_get_religion_names(self, queries):
           """Test getting religion names."""
           religions = queries.get_religion_names()

           assert isinstance(religions, list)
   ```

3. **Run the tests:**
   ```bash
   uv run pytest tests/test_queries.py -v
   ```

4. **Expected Results:**
   - All tests should pass ✅
   - No "table not found" errors
   - No circular dependency errors

**Commit:**
```bash
git add tests/test_queries.py
git commit -m "test: Add tests for fixed and new query functions

- Test fixed queries use correct table names
- Test deprecated functions return empty data gracefully
- Test all 6 new history query functions
- Test helper functions for types/names
- Verify no errors with dropped/renamed tables"
```

---

## Testing Strategy

### Unit Testing
- Query functions return correct data types
- Empty DataFrames when no data exists
- Filters work correctly
- No SQL errors

### Integration Testing
- Dash app starts without errors
- All pages load successfully
- Callbacks fire without circular dependencies
- Charts render with real data

### Manual Testing
- Browser console shows no errors
- URL sync works bidirectionally on Matches page
- All visualizations display properly
- Navigation works between pages

---

## Success Criteria

### Must Have ✅
1. ✅ No circular dependency error in browser console
2. ✅ Matches page loads and allows match selection
3. ✅ Overview page displays statistics
4. ✅ No "table not found" SQL errors
5. ✅ All 6 new history query functions work

### Nice to Have 🎯
1. 🎯 Tests for all new functions pass
2. 🎯 Server logs show no warnings
3. 🎯 All pages fully functional
4. 🎯 Code comments explain changes

---

## Common Pitfalls to Avoid

### ❌ Don't Do This:
1. **Don't update both outputs in the circular dependency fix**
   - Only update the opposite output based on which input triggered

2. **Don't forget about player_id mappings**
   - The history tables use database player_ids (already mapped by ETL)

3. **Don't query game_state anywhere**
   - It was dropped because data was broken

4. **Don't call the table "resources" anymore**
   - It's "player_yield_history" now

### ✅ Do This Instead:
1. **Use callback_context to detect trigger**
   - Prevents infinite loops

2. **Trust the data already in history tables**
   - ETL already handles player_id mapping

3. **Return empty DataFrames for deprecated functions**
   - Better than crashing

4. **Use correct table names in all queries**
   - player_yield_history, not resources

---

## Rollback Procedure

If something goes wrong:

1. **Revert code changes:**
   ```bash
   git revert HEAD~3  # Revert last 3 commits
   ```

2. **Restart app:**
   ```bash
   uv run python manage.py restart
   ```

3. **Check logs:**
   ```bash
   uv run python manage.py logs
   ```

The database is unchanged - we only fixed the query layer.

---

## Related Files

### Modified Files
- `tournament_visualizer/pages/matches.py` - Fixed circular dependency
- `tournament_visualizer/data/queries.py` - Updated table references, added history queries

### Created Files
- `tests/test_queries.py` - Tests for fixes and new functions
- `docs/plans/fix-app-after-history-tables-implementation-plan.md` - This document

### Reference Files
- `docs/plans/turn-by-turn-history-implementation-plan.md` - Original implementation plan
- `docs/migrations/002_add_history_tables.md` - Migration documentation

---

## Next Steps After This Plan

Once this plan is complete, you can:

1. **Create visualizations using the new history data:**
   - Line charts for points progression
   - Area charts for yield production over time
   - Comparison charts for military buildup
   - Heatmaps for family/religion opinion tracking

2. **Add new pages/tabs:**
   - "Turn-by-Turn Analysis" page
   - Enhanced match details with history charts

3. **Optimize queries:**
   - Add indexes if queries are slow
   - Cache frequently accessed data

---

## Questions?

If you get stuck:

1. **Check the logs:**
   ```bash
   uv run python manage.py logs -f
   ```

2. **Test queries directly:**
   ```bash
   uv run duckdb tournament_data.duckdb -readonly
   ```

3. **Look at existing code:**
   - See how other query functions are structured
   - Copy patterns from working code

4. **Run tests to pinpoint issues:**
   ```bash
   uv run pytest tests/test_queries.py -v -s
   ```
