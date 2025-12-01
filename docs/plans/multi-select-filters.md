# Multi-Select Filters Implementation Plan

## Task Checklist

### Phase 1: Query Layer
- ☑ Update `_get_filtered_match_ids()` signature and WHERE clauses
- ☑ Update all query method signatures that pass filter parameters
- ☑ Add unit tests for list-based filtering

### Phase 2: UI Layer
- ☑ Add `multi=True` to 4 dropdown components
- ☑ Update callback type hints for multi-select parameters
- ☑ Update clear filters callback return values (no change needed - None works)
- ☑ Update filter system documentation

---

## Phase 1: Query Layer

**Affected files:**
- `tournament_visualizer/data/queries.py` - Update `_get_filtered_match_ids()` and ~50 method signatures
- `tests/test_queries_filters.py` (new) - Unit tests for list-based filtering

### Changes to `queries.py`

**1. Update `_get_filtered_match_ids()` (line 3865):**

```python
def _get_filtered_match_ids(
    self,
    tournament_round: Optional[list[int]] = None,  # Changed from Optional[int]
    bracket: Optional[str] = None,
    min_turns: Optional[int] = None,
    max_turns: Optional[int] = None,
    map_size: Optional[list[str]] = None,  # Changed from Optional[str]
    map_class: Optional[list[str]] = None,  # Changed from Optional[str]
    map_aspect: Optional[list[str]] = None,  # Changed from Optional[str]
    nations: Optional[list[str]] = None,
    players: Optional[list[str]] = None,
) -> list[int]:
```

**2. Update WHERE clauses (lines 3900-3926):**

Replace single-value checks with list checks:

```python
# Tournament round filter (was: = $tournament_round)
if tournament_round and len(tournament_round) > 0:
    query += " AND m.tournament_round = ANY($tournament_round)"
    params["tournament_round"] = tournament_round

# Map filters (same pattern)
if map_size and len(map_size) > 0:
    query += " AND m.map_size = ANY($map_size)"
    params["map_size"] = map_size
if map_class and len(map_class) > 0:
    query += " AND m.map_class = ANY($map_class)"
    params["map_class"] = map_class
if map_aspect and len(map_aspect) > 0:
    query += " AND m.map_aspect_ratio = ANY($map_aspect)"
    params["map_aspect"] = map_aspect
```

**3. Update all query method signatures:**

Find all methods with these parameter patterns and update:
- `tournament_round: Optional[int]` → `Optional[list[int]]`
- `map_size: Optional[str]` → `Optional[list[str]]`
- `map_class: Optional[str]` → `Optional[list[str]]`
- `map_aspect: Optional[str]` → `Optional[list[str]]`

Methods to update (grep for `tournament_round: Optional[int]`):
- `get_nation_win_stats`
- `get_nation_loss_stats`
- `get_nation_popularity`
- `get_map_breakdown`
- `get_unit_popularity`
- `get_law_progression_by_match`
- `get_matches_by_round`
- `get_archetype_win_rates`
- `get_ruler_trait_win_rates`
- `get_yield_history_aggregate`
- `get_event_timeline_aggregate`
- ... (all others that forward these params)

### Unit Tests: `tests/test_queries_filters.py`

```python
"""Tests for _get_filtered_match_ids with list-based filters."""

import pytest
from tournament_visualizer.data.queries import TournamentQueries

class TestGetFilteredMatchIds:
    def test_single_round_in_list(self, test_db):
        """Single round value in list returns matches for that round."""
        queries = TournamentQueries(test_db)
        result = queries._get_filtered_match_ids(tournament_round=[1])
        # Assert returns match IDs for round 1

    def test_multiple_rounds(self, test_db):
        """Multiple rounds returns matches for all specified rounds."""
        queries = TournamentQueries(test_db)
        result = queries._get_filtered_match_ids(tournament_round=[1, 2])
        # Assert returns match IDs for rounds 1 and 2

    def test_empty_round_list_returns_all(self, test_db):
        """Empty list treated same as None (no filter)."""
        queries = TournamentQueries(test_db)
        result = queries._get_filtered_match_ids(tournament_round=[])
        all_matches = queries._get_filtered_match_ids()
        assert result == all_matches

    def test_multiple_map_sizes(self, test_db):
        """Multiple map sizes returns matches for all sizes."""
        queries = TournamentQueries(test_db)
        result = queries._get_filtered_match_ids(map_size=["Huge", "Giant"])
        # Assert returns matches with either size

    def test_combined_multi_filters(self, test_db):
        """Multiple multi-select filters combine with AND."""
        queries = TournamentQueries(test_db)
        result = queries._get_filtered_match_ids(
            tournament_round=[1, 2],
            map_size=["Huge"],
            map_class=["Continent", "Lakes"]
        )
        # Assert returns intersection of all filters
```

---

## Phase 2: UI Layer

**Affected files:**
- `tournament_visualizer/pages/overview.py` - Add `multi=True`, update callback signatures
- `docs/reference/filter-system.md` - Update filter type documentation

### Changes to `overview.py`

**1. Add `multi=True` to dropdowns (lines 139-182):**

```python
# Tournament Round (line 139)
dcc.Dropdown(
    id="overview-round-filter-dropdown",
    options=[],
    value=None,
    placeholder="All Rounds",
    multi=True,  # Add this
    className="mb-3",
),

# Map Size (line 151)
dcc.Dropdown(
    id="overview-map-size-dropdown",
    options=[],
    value=None,
    placeholder="All Sizes",
    multi=True,  # Add this
    className="mb-3",
),

# Map Class (line 163)
dcc.Dropdown(
    id="overview-map-class-dropdown",
    options=[],
    value=None,
    placeholder="All Classes",
    multi=True,  # Add this
    className="mb-3",
),

# Map Aspect (line 175)
dcc.Dropdown(
    id="overview-map-aspect-dropdown",
    options=[],
    value=None,
    placeholder="All Aspects",
    multi=True,  # Add this
    className="mb-3",
),
```

**2. Update all chart callback type hints:**

Find all callbacks with these patterns and update:
- `round_num: Optional[int]` → `round_nums: Optional[List[int]]`
- `map_size: Optional[str]` → `map_sizes: Optional[List[str]]`
- `map_class: Optional[str]` → `map_classes: Optional[List[str]]`
- `map_aspect: Optional[str]` → `map_aspects: Optional[List[str]]`

Example callback update:

```python
def update_nation_win_chart(
    round_nums: Optional[List[int]],  # Was: round_num: Optional[int]
    turn_length: Optional[int],
    map_sizes: Optional[List[str]],   # Was: map_size: Optional[str]
    map_classes: Optional[List[str]], # Was: map_class: Optional[str]
    map_aspects: Optional[List[str]], # Was: map_aspect: Optional[str]
    nations: Optional[List[str]],
    players: Optional[List[str]],
    n_intervals: int,
):
    min_turns, max_turns = parse_turn_length(turn_length)
    # Pass directly to query methods (already accept lists)
```

**3. Update clear filters callback (line 925):**

```python
def clear_all_filters(n_clicks):
    return (None, 200, None, None, None, None, None)
    # No change needed - None works for multi-select dropdowns
```

**4. Update `docs/reference/filter-system.md`:**

Update the filter table:

```markdown
| Filter | Component ID | Type | Default |
|--------|-------------|------|---------|
| Tournament Round | `overview-round-filter-dropdown` | Multi-select | `None` |
| Turn Length | `overview-turn-length-slider` | Slider | `200` |
| Map Size | `overview-map-size-dropdown` | Multi-select | `None` |
| Map Class | `overview-map-class-dropdown` | Multi-select | `None` |
| Map Aspect | `overview-map-aspect-dropdown` | Multi-select | `None` |
| Nations | `overview-nations-dropdown` | Multi-select | `None` |
| Players | `overview-players-dropdown` | Multi-select | `None` |
```

### Validation

Run existing filter connection tests:
```bash
uv run python -m pytest tests/test_overview_filter_connections.py -v
```

These tests validate that all chart callbacks receive all filter inputs - they should pass without modification since the callback structure hasn't changed.
