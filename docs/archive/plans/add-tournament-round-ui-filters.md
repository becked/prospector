# Implementation Plan: Add Tournament Round UI Filters

**Status:** Not Started
**Created:** 2025-11-04
**Depends On:** Tournament round tracking data layer (completed)
**Approach:** Add filters and visualizations to dashboard for tournament round/bracket filtering

## Overview

Add user-facing UI components to filter and visualize matches by tournament round and bracket (Winners/Losers).

**Current state:** Tournament round data exists in database but no UI to use it
**Goal state:** Users can filter matches by round/bracket on overview page, see round indicators on match cards, and view round-based statistics

## Context for New Engineers

### What Problem Are We Solving?

The backend now tracks which round each match belongs to (Round 1, Round 2, etc.) and which bracket (Winners or Losers). Users need to:
- Filter the match list by specific rounds ("Show only Round 1 matches")
- Filter by bracket type ("Show only Winners Bracket")
- See round information on match cards
- Compare performance across rounds/brackets

### Prerequisites

The data layer is already complete:
- Database has `tournament_round` column (INTEGER, nullable)
- Positive values = Winners Bracket (1, 2, 3, ...)
- Negative values = Losers Bracket (-1, -2, -3, ...)
- NULL = Unknown/no data

### Dashboard Architecture

Our dashboard uses:
- **Dash** - Python web framework (like Flask but for dashboards)
- **Plotly** - Charting library
- **Bootstrap** - CSS framework for layout
- **DuckDB** - Analytics database

Key concepts:
- **Callbacks** - Functions that run when user interacts with UI
- **Components** - Reusable UI elements (dropdowns, cards, charts)
- **Queries** - Functions that fetch data from database

### File Structure

```
tournament_visualizer/
├── pages/
│   └── overview.py          # Main dashboard page (WILL MODIFY)
├── components/
│   ├── filters.py           # Filter UI components (WILL MODIFY)
│   ├── layouts.py           # Reusable layout helpers (MAY USE)
│   └── charts.py            # Chart creation functions (MAY USE)
├── data/
│   └── queries.py           # Database query functions (WILL MODIFY)
└── config.py                # App configuration (MAY USE)

tests/
├── test_queries_round_filters.py    # NEW - Query tests
└── test_overview_round_filters.py   # NEW - UI/callback tests
```

### Development Workflow

Follow **TDD (Test-Driven Development)**:

1. **Red:** Write failing test first
2. **Green:** Implement minimum code to pass
3. **Refactor:** Clean up while keeping tests green
4. **Commit:** Commit when all tests pass

**Commit early, commit often** - one logical change per commit.

### Tools We Use

- **uv** - Python package manager
  ```bash
  uv run python app.py              # Run dashboard locally
  uv run pytest                     # Run tests
  uv run pytest -v                  # Verbose test output
  ```

- **DuckDB** - Query database directly
  ```bash
  uv run duckdb data/tournament_data.duckdb -readonly
  ```

- **Dash DevTools** - Browser developer tools
  - Open dashboard: http://localhost:8050
  - Check console for JavaScript errors
  - Inspect HTML structure

### Dash Fundamentals

**Components** - UI elements with IDs:
```python
dcc.Dropdown(
    id='round-filter',           # IMPORTANT: Unique ID for callbacks
    options=[...],
    value=None                   # Initial value
)
```

**Callbacks** - Functions triggered by user interaction:
```python
@callback(
    Output('match-list', 'children'),    # What to update
    Input('round-filter', 'value')       # What triggers update
)
def update_match_list(selected_round):
    # This runs when dropdown value changes
    return new_match_list
```

**Component IDs** - Follow pattern: `{page}-{component}-{type}`
- Example: `overview-round-filter-dropdown`

### Testing Strategy

**Query Tests** - Test database functions:
```python
def test_filter_by_round():
    # ARRANGE - Set up test database
    # ACT - Call query function
    # ASSERT - Check results
```

**UI Tests** - Test callbacks:
```python
def test_round_filter_callback():
    # ARRANGE - Set up app with test data
    # ACT - Simulate user selecting round
    # ASSERT - Check updated output
```

Run tests:
```bash
uv run pytest tests/test_queries_round_filters.py -v
uv run pytest tests/test_overview_round_filters.py -v
```

### UI Conventions

**Critical conventions to follow:**

1. **No Internal Chart Titles** - Card headers provide context
   ```python
   # ✅ CORRECT
   fig.update_layout(height=400, showlegend=True)

   # ❌ WRONG
   fig.update_layout(title_text="Round Stats", height=400)
   ```

2. **Bootstrap Grid** - Use 12-column layout
   ```python
   dbc.Row([
       dbc.Col([...], width=4),  # 1/3 width
       dbc.Col([...], width=8),  # 2/3 width
   ])
   ```

3. **Filter Placement** - Filters go in collapsible sidebar
   - See existing filters in `overview.py` for pattern

4. **Type Hints** - Always use type annotations
   ```python
   from typing import Optional, List, Dict, Any
   import pandas as pd

   def get_matches_by_round(round_num: Optional[int]) -> pd.DataFrame:
       ...
   ```

5. **Error Handling** - Always handle empty data
   ```python
   if df.empty:
       return html.Div("No matches found for this round")
   ```

## Architecture Decisions

### Decision 1: Filter Location

**Chosen: Add to existing filter sidebar in overview page**

**Rationale:**
- Consistent with existing UI patterns
- Users already familiar with filter location
- Collapsible sidebar saves space
- Easy to combine with other filters

**Rejected: Separate round filter panel**
- Would clutter UI
- Inconsistent with existing design
- Users might miss it

### Decision 2: Round Display Format

**Chosen: Human-readable format ("Winners Round 1", "Losers Round 2")**

**Rationale:**
- More intuitive than raw numbers (1, -2)
- Clear which bracket at a glance
- Better UX

**Implementation:**
```python
def format_round_display(round_num: Optional[int]) -> str:
    """Convert round number to human-readable format."""
    if round_num is None:
        return "Unknown"
    if round_num > 0:
        return f"Winners Round {round_num}"
    elif round_num < 0:
        return f"Losers Round {abs(round_num)}"
    else:
        return "Unknown"
```

**Rejected: Show raw numbers**
- Confusing for users
- Need to explain negative numbers

### Decision 3: Filter Options

**Chosen: Multi-level filter - Bracket first, then Round**

Two separate dropdowns:
1. **Bracket Filter**: All / Winners / Losers
2. **Round Filter**: Populated based on bracket selection

**Rationale:**
- Clearer user flow
- Easier to implement
- Avoids cluttered dropdown with many options

**Rejected: Single dropdown with all rounds**
- Would have ~20+ options (Winners 1-10, Losers 1-10)
- Hard to scan visually
- Confusing mix of positive/negative

### Decision 4: Query Strategy

**Chosen: Add optional parameters to existing query functions**

```python
def get_match_statistics(
    match_ids: Optional[List[int]] = None,
    tournament_round: Optional[int] = None,  # NEW
    bracket: Optional[str] = None             # NEW
) -> pd.DataFrame:
    ...
```

**Rationale:**
- DRY - Don't duplicate query logic
- Backward compatible - existing code still works
- Flexible - can combine filters

**Rejected: Create new separate query functions**
- WET - Would duplicate logic
- More maintenance burden
- Risk of inconsistency

### Decision 5: NULL Handling

**Chosen: Treat NULL as "Unknown" category, show in separate filter option**

**Rationale:**
- Users should know some matches lack data
- Transparent about data quality
- Users can choose to include/exclude

**Implementation:**
- Filter option: "Unknown Round"
- Badge color: Gray
- Include in "All" by default

**Rejected: Hide NULL matches**
- Loss of data visibility
- Users might wonder where matches went

## Implementation Tasks

Tasks are ordered to follow TDD principles and minimize risk.

---

### Task 1: Add Query Functions for Round Filtering

**File:** `tournament_visualizer/data/queries.py`

**What:** Add helper functions to filter match data by tournament round and bracket

**Why:** Need database layer before building UI (TDD - data layer first)

**Dependencies:** None (first task)

**Estimated Time:** 30 minutes

**Steps:**

1. **Open `queries.py` and find the `TournamentQueries` class**

2. **Add helper method for round filtering:**

   Find a good location (after `get_match_statistics` or similar), add:

   ```python
   def get_matches_by_round(
       self,
       tournament_round: Optional[int] = None,
       bracket: Optional[str] = None
   ) -> pd.DataFrame:
       """Get matches filtered by tournament round and/or bracket.

       Args:
           tournament_round: Specific round number (positive for Winners, negative for Losers)
           bracket: 'Winners', 'Losers', or None for all

       Returns:
           DataFrame with match_id, game_name, tournament_round, bracket
       """
       query = """
       SELECT
           m.match_id,
           m.game_name,
           m.save_date,
           m.tournament_round,
           m.total_turns,
           m.challonge_match_id,
           CASE
               WHEN m.tournament_round > 0 THEN 'Winners'
               WHEN m.tournament_round < 0 THEN 'Losers'
               ELSE 'Unknown'
           END as bracket
       FROM matches m
       WHERE 1=1
       """

       params = {}

       # Filter by specific round
       if tournament_round is not None:
           query += " AND m.tournament_round = $tournament_round"
           params['tournament_round'] = tournament_round

       # Filter by bracket
       if bracket == 'Winners':
           query += " AND m.tournament_round > 0"
       elif bracket == 'Losers':
           query += " AND m.tournament_round < 0"
       elif bracket == 'Unknown':
           query += " AND m.tournament_round IS NULL"
       # If bracket is None, don't filter

       query += " ORDER BY m.save_date DESC"

       return self.db.fetch_df(query, params)
   ```

3. **Add helper method to get available rounds:**

   ```python
   def get_available_rounds(self) -> pd.DataFrame:
       """Get list of tournament rounds that have matches.

       Returns:
           DataFrame with tournament_round, bracket, match_count
       """
       query = """
       SELECT
           tournament_round,
           CASE
               WHEN tournament_round > 0 THEN 'Winners'
               WHEN tournament_round < 0 THEN 'Losers'
               ELSE 'Unknown'
           END as bracket,
           COUNT(*) as match_count
       FROM matches
       GROUP BY tournament_round
       ORDER BY tournament_round
       """

       return self.db.fetch_df(query)
   ```

4. **Update `get_match_statistics` to support round filtering:**

   Find `get_match_statistics` method (around line 150-200), locate the WHERE clause:

   ```python
   # Find this section:
   WHERE 1=1
   """

   params = {}

   if match_ids:
       query += " AND m.match_id IN (SELECT unnest($match_ids))"
       params['match_ids'] = match_ids
   ```

   Add after the `match_ids` filter:

   ```python
   if tournament_round is not None:
       query += " AND m.tournament_round = $tournament_round"
       params['tournament_round'] = tournament_round

   if bracket == 'Winners':
       query += " AND m.tournament_round > 0"
   elif bracket == 'Losers':
       query += " AND m.tournament_round < 0"
   elif bracket == 'Unknown':
       query += " AND m.tournament_round IS NULL"
   ```

   Also update the function signature:

   ```python
   def get_match_statistics(
       self,
       match_ids: Optional[List[int]] = None,
       tournament_round: Optional[int] = None,    # ADD THIS
       bracket: Optional[str] = None              # ADD THIS
   ) -> pd.DataFrame:
   ```

5. **Test manually in DuckDB console:**

   ```bash
   uv run duckdb data/tournament_data.duckdb -readonly
   ```

   Run queries:
   ```sql
   -- Check round distribution
   SELECT
       tournament_round,
       CASE
           WHEN tournament_round > 0 THEN 'Winners'
           WHEN tournament_round < 0 THEN 'Losers'
           ELSE 'Unknown'
       END as bracket,
       COUNT(*) as matches
   FROM matches
   GROUP BY tournament_round
   ORDER BY tournament_round;

   -- Test specific round
   SELECT match_id, game_name, tournament_round
   FROM matches
   WHERE tournament_round = 1
   LIMIT 5;

   -- Test bracket filter
   SELECT match_id, game_name, tournament_round
   FROM matches
   WHERE tournament_round > 0
   LIMIT 5;
   ```

**Success Criteria:**
- Two new methods added to `TournamentQueries` class
- `get_match_statistics` updated with optional parameters
- Type hints on all parameters and return values
- Docstrings explain parameters clearly
- Manual SQL queries return expected data

**Commit Message:**
```
feat: Add query functions for tournament round filtering

- Add get_matches_by_round() to filter by round/bracket
- Add get_available_rounds() to list rounds with matches
- Update get_match_statistics() to support round filtering
- Support Winners/Losers/Unknown bracket filtering
```

---

### Task 2: Write Query Function Tests

**File:** `tests/test_queries_round_filters.py` (NEW)

**What:** Test the query functions we just added

**Why:** TDD - verify data layer works before building UI

**Dependencies:** Task 1 complete

**Estimated Time:** 45 minutes

**Steps:**

1. **Create test file:**
   ```bash
   touch tests/test_queries_round_filters.py
   ```

2. **Write comprehensive tests:**

   ```python
   """Tests for tournament round filtering queries."""

   import tempfile
   from pathlib import Path
   from typing import List

   import pytest
   import pandas as pd

   from tournament_visualizer.data.database import TournamentDatabase
   from tournament_visualizer.data.queries import TournamentQueries


   @pytest.fixture
   def test_db_with_rounds() -> TournamentDatabase:
       """Create test database with round data."""
       with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False) as f:
           db_path = f.name

       # Remove file so DuckDB can create fresh
       Path(db_path).unlink()

       db = TournamentDatabase(db_path, read_only=False)
       db.create_schema()

       # Insert test matches with various rounds
       with db.get_connection() as conn:
           conn.execute("""
               INSERT INTO matches (
                   match_id, file_name, file_hash, game_name,
                   tournament_round, total_turns
               ) VALUES
                   (1, 'match1.zip', 'hash1', 'Game 1', 1, 50),      -- Winners R1
                   (2, 'match2.zip', 'hash2', 'Game 2', 1, 60),      -- Winners R1
                   (3, 'match3.zip', 'hash3', 'Game 3', 2, 70),      -- Winners R2
                   (4, 'match4.zip', 'hash4', 'Game 4', -1, 80),     -- Losers R1
                   (5, 'match5.zip', 'hash5', 'Game 5', -2, 90),     -- Losers R2
                   (6, 'match6.zip', 'hash6', 'Game 6', NULL, 100)   -- Unknown
           """)

       yield db
       db.close()
       Path(db_path).unlink(missing_ok=True)


   class TestRoundFiltering:
       """Test tournament round filtering queries."""

       def test_get_matches_by_round_specific(
           self, test_db_with_rounds: TournamentDatabase
       ) -> None:
           """Test filtering by specific round number."""
           # ARRANGE
           queries = TournamentQueries(test_db_with_rounds)

           # ACT
           result = queries.get_matches_by_round(tournament_round=1)

           # ASSERT
           assert len(result) == 2, "Should return 2 matches from Winners Round 1"
           assert all(result['tournament_round'] == 1), "All rounds should be 1"
           assert all(result['bracket'] == 'Winners'), "All should be Winners bracket"

       def test_get_matches_by_bracket_winners(
           self, test_db_with_rounds: TournamentDatabase
       ) -> None:
           """Test filtering by Winners bracket."""
           # ARRANGE
           queries = TournamentQueries(test_db_with_rounds)

           # ACT
           result = queries.get_matches_by_round(bracket='Winners')

           # ASSERT
           assert len(result) == 3, "Should return 3 Winners bracket matches"
           assert all(result['tournament_round'] > 0), "All rounds should be positive"
           assert all(result['bracket'] == 'Winners'), "All should be Winners"

       def test_get_matches_by_bracket_losers(
           self, test_db_with_rounds: TournamentDatabase
       ) -> None:
           """Test filtering by Losers bracket."""
           # ARRANGE
           queries = TournamentQueries(test_db_with_rounds)

           # ACT
           result = queries.get_matches_by_round(bracket='Losers')

           # ASSERT
           assert len(result) == 2, "Should return 2 Losers bracket matches"
           assert all(result['tournament_round'] < 0), "All rounds should be negative"
           assert all(result['bracket'] == 'Losers'), "All should be Losers"

       def test_get_matches_by_bracket_unknown(
           self, test_db_with_rounds: TournamentDatabase
       ) -> None:
           """Test filtering by Unknown bracket (NULL rounds)."""
           # ARRANGE
           queries = TournamentQueries(test_db_with_rounds)

           # ACT
           result = queries.get_matches_by_round(bracket='Unknown')

           # ASSERT
           assert len(result) == 1, "Should return 1 Unknown bracket match"
           assert result['tournament_round'].isna().all(), "Round should be NULL"
           assert all(result['bracket'] == 'Unknown'), "All should be Unknown"

       def test_get_matches_all_no_filter(
           self, test_db_with_rounds: TournamentDatabase
       ) -> None:
           """Test getting all matches without filter."""
           # ARRANGE
           queries = TournamentQueries(test_db_with_rounds)

           # ACT
           result = queries.get_matches_by_round()

           # ASSERT
           assert len(result) == 6, "Should return all 6 matches"

       def test_get_matches_combine_round_and_bracket(
           self, test_db_with_rounds: TournamentDatabase
       ) -> None:
           """Test combining round and bracket filters."""
           # ARRANGE
           queries = TournamentQueries(test_db_with_rounds)

           # ACT
           result = queries.get_matches_by_round(
               tournament_round=1,
               bracket='Winners'
           )

           # ASSERT
           assert len(result) == 2, "Should return 2 Winners Round 1 matches"
           assert all(result['tournament_round'] == 1)
           assert all(result['bracket'] == 'Winners')

       def test_get_available_rounds(
           self, test_db_with_rounds: TournamentDatabase
       ) -> None:
           """Test getting list of available rounds."""
           # ARRANGE
           queries = TournamentQueries(test_db_with_rounds)

           # ACT
           result = queries.get_available_rounds()

           # ASSERT
           assert len(result) == 6, "Should have 6 distinct rounds"

           # Check specific rounds exist
           rounds = result['tournament_round'].tolist()
           assert 1 in rounds, "Should have Winners Round 1"
           assert 2 in rounds, "Should have Winners Round 2"
           assert -1 in rounds, "Should have Losers Round 1"
           assert -2 in rounds, "Should have Losers Round 2"

           # Check match counts
           round_1_count = result[result['tournament_round'] == 1]['match_count'].iloc[0]
           assert round_1_count == 2, "Winners Round 1 should have 2 matches"

       def test_get_match_statistics_with_round_filter(
           self, test_db_with_rounds: TournamentDatabase
       ) -> None:
           """Test that get_match_statistics respects round filter."""
           # ARRANGE
           queries = TournamentQueries(test_db_with_rounds)

           # ACT
           result = queries.get_match_statistics(tournament_round=1)

           # ASSERT
           # Should only return stats for Winners Round 1 matches
           assert len(result) > 0, "Should have statistics"
           # Verify only round 1 data included (exact assertion depends on stats structure)

       def test_empty_result_when_no_matches(
           self, test_db_with_rounds: TournamentDatabase
       ) -> None:
           """Test that empty DataFrame returned when no matches found."""
           # ARRANGE
           queries = TournamentQueries(test_db_with_rounds)

           # ACT
           result = queries.get_matches_by_round(tournament_round=99)

           # ASSERT
           assert len(result) == 0, "Should return empty DataFrame"
           assert isinstance(result, pd.DataFrame), "Should still be DataFrame"
   ```

3. **Run tests:**
   ```bash
   uv run pytest tests/test_queries_round_filters.py -v
   ```

4. **Fix any failures:**
   - If tests fail, debug query functions in Task 1
   - Use `pytest -v -s` to see print output
   - Check test database setup is correct

5. **Verify coverage:**
   ```bash
   uv run pytest tests/test_queries_round_filters.py --cov=tournament_visualizer.data.queries -v
   ```

**Success Criteria:**
- All tests pass
- Tests cover: specific round, bracket filtering, combined filters, empty results
- Tests use proper ARRANGE/ACT/ASSERT structure
- Type hints on all test functions
- Descriptive test names explain what they test

**Commit Message:**
```
test: Add comprehensive tests for round filtering queries

- Test filtering by specific round number
- Test filtering by bracket (Winners/Losers/Unknown)
- Test combining round and bracket filters
- Test get_available_rounds() returns correct data
- Test empty result handling
```

---

### Task 3: Add Round Formatting Helper Functions

**File:** `tournament_visualizer/components/layouts.py`

**What:** Add utility functions to format round numbers for display

**Why:** DRY - Need consistent formatting across UI components

**Dependencies:** Tasks 1-2 complete

**Estimated Time:** 20 minutes

**Steps:**

1. **Open `layouts.py` and add formatting functions at the top of the file** (after imports):

   ```python
   from typing import Optional, List, Tuple


   def format_round_display(round_num: Optional[int]) -> str:
       """Convert tournament round number to human-readable format.

       Args:
           round_num: Round number (positive=Winners, negative=Losers, None=Unknown)

       Returns:
           Formatted string like "Winners Round 1" or "Unknown"

       Examples:
           >>> format_round_display(1)
           'Winners Round 1'
           >>> format_round_display(-2)
           'Losers Round 2'
           >>> format_round_display(None)
           'Unknown'
       """
       if round_num is None:
           return "Unknown"
       elif round_num > 0:
           return f"Winners Round {round_num}"
       elif round_num < 0:
           return f"Losers Round {abs(round_num)}"
       else:
           return "Unknown"


   def get_round_badge_color(round_num: Optional[int]) -> str:
       """Get Bootstrap color class for round badge.

       Args:
           round_num: Round number

       Returns:
           Bootstrap color class name

       Examples:
           >>> get_round_badge_color(1)
           'success'
           >>> get_round_badge_color(-1)
           'warning'
           >>> get_round_badge_color(None)
           'secondary'
       """
       if round_num is None:
           return "secondary"  # Gray for unknown
       elif round_num > 0:
           return "success"    # Green for winners
       else:
           return "warning"    # Yellow for losers


   def create_round_badge(round_num: Optional[int]) -> html.Span:
       """Create a Bootstrap badge showing tournament round.

       Args:
           round_num: Round number

       Returns:
           Dash HTML component for badge

       Example:
           badge = create_round_badge(1)
           # Returns: <span class="badge bg-success">Winners Round 1</span>
       """
       return html.Span(
           format_round_display(round_num),
           className=f"badge bg-{get_round_badge_color(round_num)}",
           style={"marginLeft": "8px", "fontSize": "0.9em"}
       )


   def get_round_options_for_bracket(bracket: Optional[str]) -> List[dict]:
       """Get dropdown options for rounds in specified bracket.

       Args:
           bracket: 'Winners', 'Losers', 'Unknown', or None for all

       Returns:
           List of dicts with 'label' and 'value' keys for dcc.Dropdown

       Note:
           This generates options based on common tournament sizes.
           Actual available rounds should be fetched from database.
       """
       if bracket == 'Winners':
           # Winners bracket typically has 1-5 rounds for 32-team bracket
           return [
               {'label': f'Winners Round {i}', 'value': i}
               for i in range(1, 6)
           ]
       elif bracket == 'Losers':
           # Losers bracket can have up to 2x rounds
           return [
               {'label': f'Losers Round {i}', 'value': -i}
               for i in range(1, 11)
           ]
       elif bracket == 'Unknown':
           return [{'label': 'Unknown', 'value': None}]
       else:
           # All rounds
           return (
               [{'label': f'Winners Round {i}', 'value': i} for i in range(1, 6)]
               + [{'label': f'Losers Round {i}', 'value': -i} for i in range(1, 11)]
               + [{'label': 'Unknown', 'value': None}]
           )
   ```

2. **Add imports at top if not present:**

   ```python
   from typing import Optional, List, Tuple
   from dash import html
   ```

3. **Write simple tests for formatting functions:**

   Create `tests/test_layouts_round_formatting.py`:

   ```python
   """Tests for round formatting helper functions."""

   from tournament_visualizer.components.layouts import (
       format_round_display,
       get_round_badge_color,
       get_round_options_for_bracket,
   )


   class TestRoundFormatting:
       """Test round formatting utilities."""

       def test_format_round_display_winners(self) -> None:
           """Test formatting Winners bracket rounds."""
           assert format_round_display(1) == "Winners Round 1"
           assert format_round_display(5) == "Winners Round 5"

       def test_format_round_display_losers(self) -> None:
           """Test formatting Losers bracket rounds."""
           assert format_round_display(-1) == "Losers Round 1"
           assert format_round_display(-5) == "Losers Round 5"

       def test_format_round_display_unknown(self) -> None:
           """Test formatting unknown rounds."""
           assert format_round_display(None) == "Unknown"
           assert format_round_display(0) == "Unknown"

       def test_get_round_badge_color(self) -> None:
           """Test badge color selection."""
           assert get_round_badge_color(1) == "success"
           assert get_round_badge_color(-1) == "warning"
           assert get_round_badge_color(None) == "secondary"

       def test_get_round_options_winners(self) -> None:
           """Test generating Winners bracket options."""
           options = get_round_options_for_bracket('Winners')
           assert len(options) == 5
           assert options[0]['label'] == 'Winners Round 1'
           assert options[0]['value'] == 1

       def test_get_round_options_losers(self) -> None:
           """Test generating Losers bracket options."""
           options = get_round_options_for_bracket('Losers')
           assert len(options) == 10
           assert options[0]['label'] == 'Losers Round 1'
           assert options[0]['value'] == -1

       def test_get_round_options_all(self) -> None:
           """Test generating all bracket options."""
           options = get_round_options_for_bracket(None)
           assert len(options) == 16  # 5 Winners + 10 Losers + 1 Unknown
   ```

4. **Run tests:**
   ```bash
   uv run pytest tests/test_layouts_round_formatting.py -v
   ```

**Success Criteria:**
- Three formatting functions added to `layouts.py`
- Functions have docstrings with examples
- All tests pass
- Type hints on all functions

**Commit Message:**
```
feat: Add round formatting helper functions

- Add format_round_display() for human-readable labels
- Add get_round_badge_color() for Bootstrap badge colors
- Add create_round_badge() to create badge components
- Add get_round_options_for_bracket() for dropdown options
- Test coverage for all formatting functions
```

---

### Task 4: Add Round Filters to Overview Page

**File:** `tournament_visualizer/pages/overview.py`

**What:** Add bracket and round filter dropdowns to the overview page sidebar

**Why:** Users need UI controls to filter matches

**Dependencies:** Tasks 1-3 complete

**Estimated Time:** 45 minutes

**Steps:**

1. **Open `overview.py` and locate the filter sidebar**

   Search for `create_filter_card` or similar - this is where existing filters are defined.

2. **Add new filter components in the filters section:**

   Find the section that creates filter controls (probably around line 50-150), add:

   ```python
   # Bracket Filter
   html.Label("Tournament Bracket", className="fw-bold mb-2"),
   dcc.Dropdown(
       id='overview-bracket-filter-dropdown',
       options=[
           {'label': 'All Brackets', 'value': 'all'},
           {'label': 'Winners Bracket', 'value': 'Winners'},
           {'label': 'Losers Bracket', 'value': 'Losers'},
           {'label': 'Unknown', 'value': 'Unknown'},
       ],
       value='all',
       clearable=False,
       className="mb-3"
   ),

   # Round Filter
   html.Label("Tournament Round", className="fw-bold mb-2"),
   dcc.Dropdown(
       id='overview-round-filter-dropdown',
       options=[],  # Will be populated by callback based on bracket
       value=None,
       placeholder="All Rounds",
       clearable=True,
       className="mb-3"
   ),
   ```

3. **Add callback to populate round dropdown based on bracket:**

   Add after the filter components, before other callbacks:

   ```python
   @callback(
       Output('overview-round-filter-dropdown', 'options'),
       Input('overview-bracket-filter-dropdown', 'value')
   )
   def update_round_options(bracket: str) -> List[dict]:
       """Update round dropdown options based on selected bracket.

       Args:
           bracket: Selected bracket ('all', 'Winners', 'Losers', 'Unknown')

       Returns:
           List of options for round dropdown
       """
       from tournament_visualizer.data.queries import get_queries
       from tournament_visualizer.components.layouts import format_round_display

       queries = get_queries()

       # Get actual available rounds from database
       available_rounds = queries.get_available_rounds()

       if available_rounds.empty:
           return []

       # Filter rounds based on bracket selection
       if bracket == 'Winners':
           filtered = available_rounds[available_rounds['tournament_round'] > 0]
       elif bracket == 'Losers':
           filtered = available_rounds[available_rounds['tournament_round'] < 0]
       elif bracket == 'Unknown':
           filtered = available_rounds[available_rounds['tournament_round'].isna()]
       else:  # 'all'
           filtered = available_rounds

       # Create options
       options = [
           {
               'label': f"{format_round_display(row['tournament_round'])} ({row['match_count']} matches)",
               'value': row['tournament_round']
           }
           for _, row in filtered.iterrows()
       ]

       return options
   ```

4. **Update the main content callback to use filters:**

   Find the main callback that generates match list (search for `@callback` with Output to match list).

   Add inputs for the new filters:

   ```python
   @callback(
       Output('overview-match-list', 'children'),  # Or whatever the output is
       Input('overview-bracket-filter-dropdown', 'value'),  # ADD
       Input('overview-round-filter-dropdown', 'value'),    # ADD
       # ... existing inputs ...
   )
   def update_match_list(
       bracket: str,           # ADD
       round_num: Optional[int],  # ADD
       # ... existing parameters ...
   ) -> List[Any]:
       """Update match list based on filters."""
       from tournament_visualizer.data.queries import get_queries

       queries = get_queries()

       # Build bracket parameter for query
       bracket_param = None if bracket == 'all' else bracket

       # Get filtered matches
       matches_df = queries.get_matches_by_round(
           tournament_round=round_num,
           bracket=bracket_param
       )

       if matches_df.empty:
           return [html.Div(
               "No matches found for selected filters",
               className="text-muted text-center p-4"
           )]

       # Create match cards (adapt existing code)
       match_cards = []
       for _, match in matches_df.iterrows():
           # Create match card with round badge
           from tournament_visualizer.components.layouts import create_round_badge

           card = dbc.Card([
               dbc.CardBody([
                   html.H5([
                       match['game_name'],
                       create_round_badge(match['tournament_round'])
                   ]),
                   # ... rest of card content ...
               ])
           ])
           match_cards.append(card)

       return match_cards
   ```

5. **Test manually in browser:**

   ```bash
   # Start the dashboard
   uv run python app.py
   ```

   Open http://localhost:8050 and verify:
   - [ ] Bracket dropdown shows 4 options
   - [ ] Selecting bracket updates round dropdown
   - [ ] Round dropdown shows correct rounds with match counts
   - [ ] Selecting filters updates match list
   - [ ] Match cards show round badges
   - [ ] "All Brackets" + no round shows all matches
   - [ ] Clearing round filter shows all matches in bracket

6. **Check browser console for errors:**

   Open browser DevTools (F12), check Console tab for JavaScript errors.

**Success Criteria:**
- Two new dropdowns added to overview page
- Round dropdown updates based on bracket selection
- Match list filters correctly based on selections
- Match cards show round badges
- No JavaScript errors in console
- UI responsive and fast (<1 second to update)

**Commit Message:**
```
feat: Add tournament round filters to overview page

- Add bracket filter dropdown (All/Winners/Losers/Unknown)
- Add round filter dropdown (populated based on bracket)
- Update match list callback to respect round filters
- Add round badges to match cards
- Round dropdown shows match counts
```

---

### Task 5: Write UI Callback Tests

**File:** `tests/test_overview_round_filters.py` (NEW)

**What:** Test the UI callbacks for round filtering

**Why:** Ensure callbacks work correctly and handle edge cases

**Dependencies:** Task 4 complete

**Estimated Time:** 45 minutes

**Steps:**

1. **Create test file:**
   ```bash
   touch tests/test_overview_round_filters.py
   ```

2. **Write callback tests using Dash testing framework:**

   ```python
   """Tests for overview page round filtering UI."""

   import tempfile
   from pathlib import Path

   import pytest
   from dash.testing.application_runners import import_app

   from tournament_visualizer.data.database import TournamentDatabase
   from tournament_visualizer.data.database import get_database


   @pytest.fixture
   def test_app_with_rounds(monkeypatch):
       """Create test app with round data."""
       # Create test database
       with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False) as f:
           db_path = f.name

       Path(db_path).unlink()
       test_db = TournamentDatabase(db_path, read_only=False)
       test_db.create_schema()

       # Insert test data
       with test_db.get_connection() as conn:
           conn.execute("""
               INSERT INTO matches (
                   match_id, file_name, file_hash, game_name,
                   tournament_round, total_turns
               ) VALUES
                   (1, 'match1.zip', 'hash1', 'Winners R1 Game 1', 1, 50),
                   (2, 'match2.zip', 'hash2', 'Winners R1 Game 2', 1, 60),
                   (3, 'match3.zip', 'hash3', 'Winners R2 Game', 2, 70),
                   (4, 'match4.zip', 'hash4', 'Losers R1 Game', -1, 80)
           """)

       # Mock get_database to return test DB
       monkeypatch.setattr(
           'tournament_visualizer.data.queries.get_database',
           lambda: test_db
       )

       # Import app (will use mocked database)
       from tournament_visualizer import app

       yield app.app

       test_db.close()
       Path(db_path).unlink(missing_ok=True)


   class TestOverviewRoundFilters:
       """Test round filtering UI on overview page."""

       def test_bracket_filter_exists(self, dash_duo, test_app_with_rounds) -> None:
           """Test that bracket filter dropdown exists."""
           # ARRANGE
           dash_duo.start_server(test_app_with_rounds)

           # ACT
           dash_duo.wait_for_element("#overview-bracket-filter-dropdown", timeout=4)

           # ASSERT
           bracket_dropdown = dash_duo.find_element("#overview-bracket-filter-dropdown")
           assert bracket_dropdown is not None

       def test_round_filter_exists(self, dash_duo, test_app_with_rounds) -> None:
           """Test that round filter dropdown exists."""
           # ARRANGE
           dash_duo.start_server(test_app_with_rounds)

           # ACT
           dash_duo.wait_for_element("#overview-round-filter-dropdown", timeout=4)

           # ASSERT
           round_dropdown = dash_duo.find_element("#overview-round-filter-dropdown")
           assert round_dropdown is not None

       def test_selecting_winners_updates_round_options(
           self, dash_duo, test_app_with_rounds
       ) -> None:
           """Test selecting Winners bracket updates round dropdown."""
           # ARRANGE
           dash_duo.start_server(test_app_with_rounds)
           dash_duo.wait_for_element("#overview-bracket-filter-dropdown", timeout=4)

           # ACT - Select Winners bracket
           bracket_dropdown = dash_duo.find_element("#overview-bracket-filter-dropdown")
           # Dash dropdown selection (use appropriate selector)
           dash_duo.select_dcc_dropdown("#overview-bracket-filter-dropdown", "Winners")

           # Wait for round options to update
           dash_duo.wait_for_text_to_equal(
               "#overview-round-filter-dropdown .Select-placeholder",
               "All Rounds",
               timeout=2
           )

           # ASSERT - Round dropdown should have Winners rounds only
           # Check options contain "Winners Round" (exact assertion depends on implementation)

       def test_selecting_round_filters_matches(
           self, dash_duo, test_app_with_rounds
       ) -> None:
           """Test selecting specific round filters match list."""
           # ARRANGE
           dash_duo.start_server(test_app_with_rounds)
           dash_duo.wait_for_element("#overview-bracket-filter-dropdown", timeout=4)

           # ACT - Select Winners Round 1
           dash_duo.select_dcc_dropdown("#overview-bracket-filter-dropdown", "Winners")
           dash_duo.wait_for_element("#overview-round-filter-dropdown", timeout=2)
           # Select round 1 from dropdown (value depends on actual options)

           # ASSERT - Should see only 2 matches (Winners R1 has 2 matches)
           # Count match cards (adjust selector to actual card class)
           match_cards = dash_duo.find_elements(".match-card")
           assert len(match_cards) == 2, "Should show 2 Winners Round 1 matches"

       def test_all_brackets_shows_all_matches(
           self, dash_duo, test_app_with_rounds
       ) -> None:
           """Test 'All Brackets' shows all matches."""
           # ARRANGE
           dash_duo.start_server(test_app_with_rounds)
           dash_duo.wait_for_element("#overview-bracket-filter-dropdown", timeout=4)

           # ACT - Ensure 'All' is selected (default)

           # ASSERT - Should see all 4 matches
           match_cards = dash_duo.find_elements(".match-card")
           assert len(match_cards) == 4, "Should show all 4 matches"

       def test_clearing_round_filter_shows_all_in_bracket(
           self, dash_duo, test_app_with_rounds
       ) -> None:
           """Test clearing round filter shows all matches in bracket."""
           # ARRANGE
           dash_duo.start_server(test_app_with_rounds)
           dash_duo.wait_for_element("#overview-bracket-filter-dropdown", timeout=4)

           # Select Winners bracket and specific round
           dash_duo.select_dcc_dropdown("#overview-bracket-filter-dropdown", "Winners")
           # Select round 1 (implementation-specific)

           # ACT - Clear round filter
           # Click clear button on round dropdown

           # ASSERT - Should see all 3 Winners matches (R1 x2 + R2 x1)
           match_cards = dash_duo.find_elements(".match-card")
           assert len(match_cards) == 3

       def test_match_cards_show_round_badges(
           self, dash_duo, test_app_with_rounds
       ) -> None:
           """Test that match cards display round badges."""
           # ARRANGE
           dash_duo.start_server(test_app_with_rounds)
           dash_duo.wait_for_element("#overview-bracket-filter-dropdown", timeout=4)

           # ACT - Select Winners Round 1
           dash_duo.select_dcc_dropdown("#overview-bracket-filter-dropdown", "Winners")

           # ASSERT - Match cards should have badges
           badges = dash_duo.find_elements(".badge")
           assert len(badges) > 0, "Match cards should have round badges"

           # Check badge text
           badge_text = badges[0].text
           assert "Winners Round" in badge_text, "Badge should show round info"
   ```

3. **Note about Dash testing:**

   Dash UI tests can be tricky. If you encounter issues:

   - Use `dash_duo.wait_for_element()` to ensure elements load
   - Check browser console in test output for errors
   - Use `dash_duo.take_screenshot("debug.png")` to debug visually
   - Simplify tests if necessary - it's okay to test just the basics

4. **Run tests:**
   ```bash
   uv run pytest tests/test_overview_round_filters.py -v
   ```

5. **If tests fail or are too complex:**

   Simplify by testing just the callback functions directly:

   ```python
   def test_update_round_options_callback() -> None:
       """Test round options callback directly (without browser)."""
       from tournament_visualizer.pages.overview import update_round_options

       # Test Winners bracket
       options = update_round_options('Winners')
       assert len(options) > 0
       assert all('Winners' in opt['label'] for opt in options)

       # Test Losers bracket
       options = update_round_options('Losers')
       assert len(options) > 0
       assert all('Losers' in opt['label'] for opt in options)
   ```

**Success Criteria:**
- Tests verify filter components exist
- Tests verify selecting filters updates UI
- Tests verify match counts are correct
- Tests pass (or at least core callback logic tested)

**Note:** Dash UI testing is complex - it's acceptable to have simpler tests that focus on callback logic rather than full browser interaction.

**Commit Message:**
```
test: Add UI tests for tournament round filters

- Test bracket and round filter components exist
- Test round dropdown updates based on bracket
- Test match list filters correctly
- Test round badges appear on match cards
- Test clearing filters shows all matches
```

---

### Task 6: Add Round Statistics to Overview Page

**File:** `tournament_visualizer/pages/overview.py`

**What:** Add a statistics card showing match distribution by round/bracket

**Why:** Give users overview of tournament progression

**Dependencies:** Tasks 1-5 complete

**Estimated Time:** 30 minutes

**Steps:**

1. **Find the statistics section in `overview.py`**

   Look for existing statistic cards (KPIs, summary metrics) - probably near the top of the page layout.

2. **Add a new statistics card for round distribution:**

   ```python
   # Add to the overview page layout, in an appropriate row
   dbc.Col([
       dbc.Card([
           dbc.CardBody([
               html.H5("Tournament Rounds", className="card-title"),
               html.Div(id='overview-round-stats-content')
           ])
       ])
   ], width=4),
   ```

3. **Add callback to populate round statistics:**

   ```python
   @callback(
       Output('overview-round-stats-content', 'children')
   )
   def update_round_statistics() -> List[Any]:
       """Display tournament round distribution statistics.

       Returns:
           List of HTML components showing round stats
       """
       from tournament_visualizer.data.queries import get_queries
       from tournament_visualizer.components.layouts import format_round_display

       queries = get_queries()
       rounds_df = queries.get_available_rounds()

       if rounds_df.empty:
           return [html.P("No round data available", className="text-muted")]

       # Calculate totals
       total_matches = rounds_df['match_count'].sum()
       winners_matches = rounds_df[rounds_df['bracket'] == 'Winners']['match_count'].sum()
       losers_matches = rounds_df[rounds_df['bracket'] == 'Losers']['match_count'].sum()
       unknown_matches = rounds_df[rounds_df['bracket'] == 'Unknown']['match_count'].sum()

       # Create summary
       stats = [
           html.P([
               html.Strong("Total Matches: "),
               f"{total_matches}"
           ], className="mb-2"),
           html.P([
               html.Strong("Winners Bracket: "),
               html.Span(f"{winners_matches}", className="text-success")
           ], className="mb-2"),
           html.P([
               html.Strong("Losers Bracket: "),
               html.Span(f"{losers_matches}", className="text-warning")
           ], className="mb-2"),
       ]

       if unknown_matches > 0:
           stats.append(html.P([
               html.Strong("Unknown: "),
               html.Span(f"{unknown_matches}", className="text-muted")
           ], className="mb-2"))

       # Add horizontal rule
       stats.append(html.Hr())

       # Add breakdown by round
       stats.append(html.P(html.Strong("Breakdown by Round:"), className="mb-2"))

       for _, row in rounds_df.iterrows():
           round_display = format_round_display(row['tournament_round'])
           stats.append(
               html.P([
                   f"{round_display}: ",
                   html.Span(
                       f"{row['match_count']} matches",
                       className="text-muted"
                   )
               ], className="mb-1 ms-3")
           )

       return stats
   ```

4. **Optional: Add a simple bar chart visualization:**

   If you want a visual chart instead of text stats:

   ```python
   @callback(
       Output('overview-round-stats-chart', 'figure')
   )
   def update_round_chart() -> go.Figure:
       """Create bar chart of matches by round.

       Returns:
           Plotly figure showing match distribution
       """
       from tournament_visualizer.data.queries import get_queries
       from tournament_visualizer.components.layouts import format_round_display
       from tournament_visualizer.components.charts import create_base_figure
       import plotly.graph_objects as go

       queries = get_queries()
       rounds_df = queries.get_available_rounds()

       if rounds_df.empty:
           from tournament_visualizer.components.charts import create_empty_figure
           return create_empty_figure("No round data available")

       # Format labels
       rounds_df['label'] = rounds_df['tournament_round'].apply(format_round_display)

       # Create bar chart
       fig = create_base_figure()

       # Separate Winners and Losers for different colors
       winners_df = rounds_df[rounds_df['bracket'] == 'Winners']
       losers_df = rounds_df[rounds_df['bracket'] == 'Losers']

       fig.add_trace(go.Bar(
           x=winners_df['label'],
           y=winners_df['match_count'],
           name='Winners Bracket',
           marker_color='#28a745'
       ))

       fig.add_trace(go.Bar(
           x=losers_df['label'],
           y=losers_df['match_count'],
           name='Losers Bracket',
           marker_color='#ffc107'
       ))

       fig.update_layout(
           xaxis_title="Round",
           yaxis_title="Match Count",
           height=300,
           showlegend=True,
           barmode='group'
       )

       return fig
   ```

   And add the chart component to layout:

   ```python
   dcc.Graph(
       id='overview-round-stats-chart',
       config={'displayModeBar': False}
   )
   ```

5. **Test manually:**

   ```bash
   uv run python app.py
   ```

   Verify:
   - [ ] Round statistics card appears
   - [ ] Shows correct total match counts
   - [ ] Shows breakdown by bracket
   - [ ] Shows individual round counts
   - [ ] Chart displays correctly (if added)

**Success Criteria:**
- Round statistics card added to overview page
- Shows total matches by bracket
- Shows breakdown by individual rounds
- Numbers match database query results
- Optional: Chart visualization displays correctly

**Commit Message:**
```
feat: Add tournament round statistics to overview page

- Add statistics card showing match distribution
- Display total matches by bracket (Winners/Losers)
- Show breakdown by individual rounds
- Add color coding for brackets (green/yellow)
- Optional: Add bar chart visualization
```

---

### Task 7: Update Documentation

**File:** `CLAUDE.md`

**What:** Document the new UI features for future developers

**Why:** Help future developers understand how to use/modify round filters

**Dependencies:** Tasks 1-6 complete

**Estimated Time:** 20 minutes

**Steps:**

1. **Open `CLAUDE.md` and find the "Dashboard & Chart Conventions" section**

2. **Add a subsection about tournament round filtering:**

   After the "Chart Titles" section, add:

   ```markdown
   ### Tournament Round Filtering

   **Overview page includes filters for tournament rounds and brackets.**

   **UI Components:**
   - Bracket filter dropdown: Filter by Winners/Losers/Unknown bracket
   - Round filter dropdown: Filter by specific round number (updates based on bracket)
   - Round badges: Display on match cards showing which round

   **Implementation Pattern:**

   The round filtering follows this pattern:

   1. **Bracket dropdown** - User selects bracket type
   2. **Round dropdown callback** - Updates options based on bracket
   3. **Match list callback** - Filters matches based on both selections
   4. **Round badges** - Visual indicators on match cards

   **Example callback structure:**
   ```python
   @callback(
       Output('overview-round-filter-dropdown', 'options'),
       Input('overview-bracket-filter-dropdown', 'value')
   )
   def update_round_options(bracket: str) -> List[dict]:
       """Populate round dropdown based on selected bracket."""
       queries = get_queries()
       available_rounds = queries.get_available_rounds()
       # Filter and format options
       return options

   @callback(
       Output('overview-match-list', 'children'),
       Input('overview-bracket-filter-dropdown', 'value'),
       Input('overview-round-filter-dropdown', 'value')
   )
   def update_match_list(bracket: str, round_num: Optional[int]):
       """Update match list based on round filters."""
       queries = get_queries()
       matches = queries.get_matches_by_round(
           tournament_round=round_num,
           bracket=None if bracket == 'all' else bracket
       )
       # Create match cards with round badges
       return match_cards
   ```

   **Query Functions:**
   - `get_matches_by_round(tournament_round, bracket)` - Filter matches
   - `get_available_rounds()` - Get list of rounds with match counts
   - `get_match_statistics(tournament_round, bracket)` - Get stats for filtered matches

   **Helper Functions:**
   - `format_round_display(round_num)` - Convert round number to display text
   - `get_round_badge_color(round_num)` - Get Bootstrap color for badge
   - `create_round_badge(round_num)` - Create round badge component

   **Round Number Format:**
   - Positive integers (1, 2, 3, ...) = Winners Bracket
   - Negative integers (-1, -2, -3, ...) = Losers Bracket
   - NULL/None = Unknown

   **Files:**
   - `tournament_visualizer/pages/overview.py` - Filter UI and callbacks
   - `tournament_visualizer/data/queries.py` - Filter query functions
   - `tournament_visualizer/components/layouts.py` - Helper formatting functions

   **See Also:**
   - Tournament round data layer: `docs/migrations/010_add_tournament_round.md`
   ```

3. **Update the "UI Conventions" section if needed:**

   Add a bullet about round badges:

   ```markdown
   6. **Round Badges**: Match cards should display tournament round
      ```python
      from tournament_visualizer.components.layouts import create_round_badge

      card_header = html.H5([
          match['game_name'],
          create_round_badge(match['tournament_round'])
      ])
      ```
   ```

4. **Save and review:**
   ```bash
   cat CLAUDE.md | grep -A30 "Tournament Round Filtering"
   ```

**Success Criteria:**
- New section added to CLAUDE.md
- Explains filter UI pattern
- Documents key functions and files
- Includes code examples
- Links to related documentation

**Commit Message:**
```
docs: Document tournament round filtering UI features

- Add "Tournament Round Filtering" section to CLAUDE.md
- Document filter UI components and callbacks
- List query functions and helper utilities
- Include code examples for common patterns
- Link to related documentation
```

---

### Task 8: Manual End-to-End Testing

**What:** Comprehensive manual testing of all round filtering features

**Why:** Ensure everything works together in real usage

**Dependencies:** Tasks 1-7 complete

**Estimated Time:** 30 minutes

**Steps:**

1. **Start the dashboard:**
   ```bash
   uv run python app.py
   ```

2. **Test basic filtering:**

   - [ ] Load overview page - verify filters appear in sidebar
   - [ ] Bracket dropdown has 4 options: All, Winners, Losers, Unknown
   - [ ] Round dropdown initially shows placeholder "All Rounds"
   - [ ] Match list shows all matches initially

3. **Test Winners bracket filtering:**

   - [ ] Select "Winners Bracket" from bracket dropdown
   - [ ] Verify round dropdown updates to show only Winners rounds
   - [ ] Round options show match counts (e.g., "Winners Round 1 (13 matches)")
   - [ ] Select "Winners Round 1"
   - [ ] Verify match list shows only Winners Round 1 matches
   - [ ] Count matches - should match the count shown in dropdown
   - [ ] Verify all match cards show green "Winners Round 1" badge

4. **Test Losers bracket filtering:**

   - [ ] Select "Losers Bracket" from bracket dropdown
   - [ ] Verify round dropdown shows only Losers rounds (negative numbers)
   - [ ] Select "Losers Round 1"
   - [ ] Verify match list shows only Losers Round 1 matches
   - [ ] Verify match cards show yellow "Losers Round 1" badge

5. **Test Unknown bracket:**

   - [ ] Select "Unknown" from bracket dropdown
   - [ ] Verify round dropdown shows "Unknown" option (or is empty if no unknown matches)
   - [ ] If unknown matches exist, select "Unknown"
   - [ ] Verify match cards show gray "Unknown" badge

6. **Test filter combinations:**

   - [ ] Select "Winners Bracket" then "Winners Round 2"
   - [ ] Verify correct matches shown
   - [ ] Change to "Winners Round 1" without changing bracket
   - [ ] Verify matches update correctly

7. **Test clearing filters:**

   - [ ] With filters applied, clear the round dropdown (click X)
   - [ ] Verify all matches in selected bracket are shown
   - [ ] Select "All Brackets"
   - [ ] Verify all matches shown (all brackets and rounds)

8. **Test statistics card:**

   - [ ] Verify round statistics card appears
   - [ ] Numbers match filtered results
   - [ ] Breakdown shows all rounds with correct counts
   - [ ] If chart added, verify it displays correctly

9. **Test edge cases:**

   - [ ] Select a round that has 0 matches (if possible)
   - [ ] Verify "No matches found" message appears
   - [ ] Test with no filters - should see all matches
   - [ ] Verify match counts in statistics match database

10. **Test performance:**

    - [ ] Filter changes apply quickly (<1 second)
    - [ ] No JavaScript errors in browser console (F12)
    - [ ] Page remains responsive with filters applied
    - [ ] Check network tab - no excessive API calls

11. **Test on different browsers** (if possible):

    - [ ] Chrome
    - [ ] Firefox
    - [ ] Safari (Mac only)

12. **Document any issues found:**

    Create a checklist of bugs/issues:
    ```
    - [ ] Issue 1: Description
    - [ ] Issue 2: Description
    ```

    Fix issues before final commit.

**Success Criteria:**
- All filter combinations work correctly
- Match counts are accurate
- Badges display with correct colors
- No JavaScript errors
- Performance is acceptable
- UI is intuitive and responsive

**Notes:**
If you find issues during testing:
1. Note the specific steps to reproduce
2. Check browser console for errors
3. Fix the issue
4. Re-test the specific scenario
5. Run full test suite again

**After Testing:**

Create a summary comment in the plan file:

```markdown
## Manual Testing Results

**Date:** [Date]
**Tested By:** [Your name]

**Results:**
- ✅ All basic filtering scenarios work
- ✅ Filter combinations work correctly
- ✅ Statistics accurate
- ✅ Performance acceptable
- ✅ No console errors

**Issues Found:**
1. [Issue description] - Fixed in commit [hash]
2. [Issue description] - Fixed in commit [hash]

**Browser Compatibility:**
- ✅ Chrome
- ✅ Firefox
- ⚠️ Safari: [Any issues noted]
```

---

### Task 9: Run Full Test Suite

**What:** Run all tests to ensure nothing broke

**Why:** Verify no regressions introduced by new features

**Dependencies:** Tasks 1-8 complete

**Estimated Time:** 10 minutes

**Steps:**

1. **Run all tests:**
   ```bash
   uv run pytest -v
   ```

2. **Check coverage:**
   ```bash
   uv run pytest --cov=tournament_visualizer --cov-report=html
   ```

   Open `htmlcov/index.html` in browser to see detailed coverage report.

3. **Verify new code is tested:**

   Check coverage for:
   - `tournament_visualizer/data/queries.py` - Should have good coverage for new functions
   - `tournament_visualizer/components/layouts.py` - Helper functions covered
   - `tournament_visualizer/pages/overview.py` - Callbacks covered (or manually tested)

4. **If any tests fail:**

   - Read failure output carefully
   - Fix the issue
   - Re-run tests
   - Don't commit until all tests pass

5. **Run integration test with real database:**

   ```bash
   # Test with actual production database
   uv run python -c "
   from tournament_visualizer.data.queries import get_queries

   queries = get_queries()

   # Test get_matches_by_round
   winners_r1 = queries.get_matches_by_round(tournament_round=1)
   print(f'Winners Round 1: {len(winners_r1)} matches')

   losers_r1 = queries.get_matches_by_round(tournament_round=-1)
   print(f'Losers Round 1: {len(losers_r1)} matches')

   # Test get_available_rounds
   rounds = queries.get_available_rounds()
   print(f'Available rounds: {len(rounds)}')
   print(rounds)
   "
   ```

**Success Criteria:**
- All existing tests still pass
- All new tests pass
- Coverage for new code is >80%
- Integration test with real database works

**Commit Message:**
```
test: Verify all tests pass with round filtering features

- All existing tests pass (no regressions)
- New round filtering tests pass
- Coverage for new code meets threshold
- Integration test with production database successful
```

---

### Task 10: Update Plan Status and Final Documentation

**What:** Mark plan as complete and update documentation

**Why:** Track implementation completion and help future developers

**Dependencies:** Tasks 1-9 complete

**Estimated Time:** 15 minutes

**Steps:**

1. **Update plan status:**

   At the top of this file (`docs/plans/add-tournament-round-ui-filters.md`), change:

   ```markdown
   **Status:** Not Started
   ```

   To:

   ```markdown
   **Status:** ✅ Completed
   **Completed:** [Date]
   ```

2. **Add implementation summary:**

   At the end of this file, add:

   ```markdown
   ## Implementation Summary

   ### Completed Features

   **UI Components:**
   - ✅ Bracket filter dropdown (All/Winners/Losers/Unknown)
   - ✅ Round filter dropdown (dynamically populated)
   - ✅ Match list filtering by round and bracket
   - ✅ Round badges on match cards
   - ✅ Round statistics card with breakdown
   - ✅ Optional: Round distribution chart

   **Backend:**
   - ✅ `get_matches_by_round()` query function
   - ✅ `get_available_rounds()` query function
   - ✅ Extended `get_match_statistics()` with round filters

   **Utilities:**
   - ✅ `format_round_display()` formatting helper
   - ✅ `get_round_badge_color()` color helper
   - ✅ `create_round_badge()` component helper

   **Testing:**
   - ✅ Query function tests (comprehensive)
   - ✅ Helper function tests
   - ✅ UI callback tests (basic)
   - ✅ Manual end-to-end testing

   **Documentation:**
   - ✅ CLAUDE.md updated with UI patterns
   - ✅ Implementation plan complete

   ### Commits

   [List commit hashes and messages]

   ### Known Limitations

   [Any limitations or future enhancements noted during implementation]

   ### Next Steps

   Potential future enhancements:
   - Tournament bracket visualization
   - Round progression timeline
   - Head-to-head round comparisons
   - Export filtered match lists
   ```

3. **Take screenshots for documentation:**

   - Take screenshot of overview page with filters
   - Take screenshot of filtered match list
   - Save to `docs/screenshots/` (create directory if needed)

4. **Update README if needed:**

   If the main README mentions features, add a bullet about round filtering.

5. **Create a final summary commit:**

   Review all changes:
   ```bash
   git log --oneline -20
   git status
   ```

   If any loose files, commit them:
   ```bash
   git add docs/plans/add-tournament-round-ui-filters.md
   git commit -m "docs: Mark tournament round UI implementation complete"
   ```

**Success Criteria:**
- Plan status marked as complete
- Implementation summary added
- All commits have clear messages
- Screenshots captured (optional but helpful)
- No uncommitted changes

**Final Commit Message:**
```
docs: Mark tournament round UI implementation complete

- Update plan status to completed
- Add implementation summary
- Document all features delivered
- List known limitations and future enhancements
```

---

## Validation Checklist

After completing all tasks, verify:

**Data Layer:**
- [ ] Query functions filter correctly by round
- [ ] Query functions filter correctly by bracket
- [ ] Query functions handle NULL values
- [ ] Query tests all pass

**UI Layer:**
- [ ] Bracket filter dropdown works
- [ ] Round filter dropdown updates based on bracket
- [ ] Match list filters correctly
- [ ] Round badges display on match cards
- [ ] Statistics card shows accurate counts
- [ ] No JavaScript errors in console

**Testing:**
- [ ] All query tests pass
- [ ] All helper function tests pass
- [ ] Manual testing completed successfully
- [ ] No regressions in existing features

**Documentation:**
- [ ] CLAUDE.md updated
- [ ] Plan marked as complete
- [ ] Code has docstrings and type hints

**Performance:**
- [ ] Filters respond in <1 second
- [ ] No excessive database queries
- [ ] Page remains responsive

**Code Quality:**
- [ ] Follows DRY principle
- [ ] Follows YAGNI principle
- [ ] Uses type hints
- [ ] Has clear commit messages

## Common Issues and Solutions

### Issue: Round dropdown doesn't update when bracket changes

**Cause:** Callback not registered or incorrect Input/Output IDs

**Solution:**
- Verify callback decorator has correct IDs:
  ```python
  @callback(
      Output('overview-round-filter-dropdown', 'options'),
      Input('overview-bracket-filter-dropdown', 'value')
  )
  ```
- Check IDs match component IDs exactly
- Check for JavaScript errors in console

### Issue: Match list shows wrong matches

**Cause:** Filter parameters not passed correctly to query

**Solution:**
- Add debug logging to callback:
  ```python
  print(f"Filter: bracket={bracket}, round={round_num}")
  ```
- Verify query function receives correct parameters
- Check SQL query logic in `get_matches_by_round()`

### Issue: Round badges don't show correct colors

**Cause:** Badge color logic incorrect

**Solution:**
- Test `get_round_badge_color()` directly:
  ```python
  assert get_round_badge_color(1) == "success"
  assert get_round_badge_color(-1) == "warning"
  ```
- Check Bootstrap color classes are correct
- Verify CSS classes applied in `create_round_badge()`

### Issue: Tests fail with "No module named X"

**Cause:** Import paths incorrect

**Solution:**
- Check import statements use correct module paths
- Verify `tournament_visualizer` package structure
- Run `uv run pytest` not just `pytest`

### Issue: Dash callback tests fail

**Cause:** Dash testing framework is complex and sensitive

**Solution:**
- Simplify tests to focus on callback logic
- Test callbacks directly instead of through browser
- Use `dash_duo.take_screenshot()` to debug
- It's okay to have simpler tests than full UI automation

## Performance Considerations

**Query Performance:**
- Index on `tournament_round` already exists (from data layer task)
- Queries should be fast (<100ms) for typical dataset sizes
- If slow, check EXPLAIN QUERY PLAN in DuckDB

**UI Performance:**
- Callbacks should respond in <1 second
- Minimize database queries in callbacks
- Use caching if needed (advanced)

**Memory:**
- Round dropdown options cached in browser
- Match list rendered on-demand
- Statistics calculated per page load (acceptable)

## Future Enhancements (Out of Scope)

After this implementation, consider:

1. **Tournament Bracket Visualization**
   - Visual tree showing tournament progression
   - Click on rounds to filter
   - Show matchup connections

2. **Round Progression Timeline**
   - Chart showing rounds played over time
   - Filter by date range + round

3. **Head-to-Head Round Comparisons**
   - Compare player performance across rounds
   - "How did players do in Round 1 vs Round 2?"

4. **Advanced Filtering**
   - Combine round filters with existing filters
   - Save filter presets
   - URL parameter support for sharable filtered views

5. **Export Functionality**
   - Export filtered match list to CSV
   - Download round statistics

## Related Documentation

- [Tournament Round Data Layer](./add-tournament-round-tracking.md) - Backend implementation
- [Dash Documentation](https://dash.plotly.com/) - Dash framework
- [Plotly Documentation](https://plotly.com/python/) - Charting library
- [Bootstrap Documentation](https://getbootstrap.com/) - CSS framework
- [DuckDB Documentation](https://duckdb.org/docs/) - Database

## Glossary

**Callback** - Dash function that runs when user interacts with UI

**Component ID** - Unique identifier for UI elements (e.g., `overview-round-filter-dropdown`)

**DataFrame** - Pandas data structure (like a spreadsheet in Python)

**Dropdown** - UI component for selecting from a list of options (`dcc.Dropdown`)

**Winners Bracket** - Main tournament bracket (no losses yet)

**Losers Bracket** - Secondary bracket for teams with one loss

**Round Number** - Tournament progression indicator (1, 2, 3, ...)

**Badge** - Small colored label showing additional info

**DRY** - Don't Repeat Yourself - avoid duplicate code

**YAGNI** - You Ain't Gonna Need It - don't add unused features

**TDD** - Test-Driven Development - write tests before code
