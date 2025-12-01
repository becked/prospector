# Result Filter Implementation Plan

## Open Questions

None - ready for implementation.

## Task Checklist

### Phase 1: Query Layer
- ☑ Add `ResultFilter` type alias to `queries.py`
- ☑ Add `_get_winner_player_ids()` helper method to `TournamentQueries`
- ☑ Update `_get_filtered_match_ids()` to accept `result_filter` and return `(match_id, player_id)` tuples when filtering by result
- ☑ Add unit tests for result filtering in `tests/test_queries_result_filter.py`

### Phase 2: UI and Callbacks
- ☑ Add Result dropdown component to filter panel in `overview.py`
- ☑ Add Result filter to clear filters callback
- ☑ Add Result filter Input to all chart callbacks (21 callbacks)
- ☑ Pass `result_filter` parameter through to query methods
- ☑ Add warning banner for win-rate charts when result filter is active
- ☑ Update `tests/test_overview_filter_connections.py` to include Result filter

---

## Phase 1: Query Layer

### Affected Files
| File | Changes |
|------|---------|
| `tournament_visualizer/data/queries.py` | Add `ResultFilter` type, `_get_winner_player_ids()`, update `_get_filtered_match_ids()` |
| `tests/test_queries_result_filter.py` | New file with result filter tests |

### Implementation

**1. Add type alias and helper method in `queries.py`:**

```python
from typing import Literal

ResultFilter = Literal["all", "winners", "losers"] | None

class TournamentQueries:
    def _get_winner_player_ids(self, match_ids: list[int] | None = None) -> set[tuple[int, int]]:
        """Returns set of (match_id, player_id) tuples for winners.

        If match_ids provided, filters to only those matches.
        """
        query = """
            SELECT match_id, winner_player_id
            FROM match_winners
            WHERE winner_player_id IS NOT NULL
        """
        if match_ids:
            query += f" AND match_id IN ({','.join(map(str, match_ids))})"

        df = self.db.execute_query(query)
        return set(zip(df["match_id"], df["winner_player_id"]))
```

**2. Update `_get_filtered_match_ids()` signature and return type:**

Current signature:
```python
def _get_filtered_match_ids(
    self,
    tournament_round: Optional[list[int]] = None,
    ...
) -> list[int]:
```

New signature:
```python
def _get_filtered_match_ids(
    self,
    tournament_round: Optional[list[int]] = None,
    bracket: Optional[str] = None,
    min_turns: Optional[int] = None,
    max_turns: Optional[int] = None,
    map_size: Optional[list[str]] = None,
    map_class: Optional[list[str]] = None,
    map_aspect: Optional[list[str]] = None,
    nations: Optional[list[str]] = None,
    players: Optional[list[str]] = None,
    result_filter: ResultFilter = None,
) -> list[int] | list[tuple[int, int]]:
    """Returns filtered match IDs, or (match_id, player_id) tuples if result_filter is set.

    When result_filter is "winners" or "losers", returns tuples to enable
    player-level filtering. When result_filter is None or "all", returns
    just match IDs (existing behavior).
    """
```

**3. Implementation logic in `_get_filtered_match_ids()`:**

At end of existing method, before return:

```python
# Get base match_ids from existing logic
match_ids = [row[0] for row in result]

# If no result filter, return match IDs only (existing behavior)
if result_filter is None or result_filter == "all":
    return match_ids

# Get winner (match_id, player_id) pairs
winner_pairs = self._get_winner_player_ids(match_ids)

if result_filter == "winners":
    return list(winner_pairs)

# For losers: get all players in filtered matches, subtract winners
all_players_query = f"""
    SELECT DISTINCT match_id, player_id
    FROM players
    WHERE match_id IN ({','.join(map(str, match_ids))})
"""
all_players_df = self.db.execute_query(all_players_query)
all_pairs = set(zip(all_players_df["match_id"], all_players_df["player_id"]))
loser_pairs = all_pairs - winner_pairs
return list(loser_pairs)
```

**4. Update query methods to handle tuple results:**

Query methods that use `_get_filtered_match_ids()` need to handle both return types. Example pattern:

```python
def get_nation_popularity(
    self,
    tournament_round: Optional[list[int]] = None,
    # ... other params ...
    result_filter: ResultFilter = None,
) -> pd.DataFrame:
    filtered = self._get_filtered_match_ids(
        tournament_round=tournament_round,
        # ... other params ...
        result_filter=result_filter,
    )

    # Handle both return types
    if result_filter in ("winners", "losers"):
        # filtered is list of (match_id, player_id) tuples
        if not filtered:
            return pd.DataFrame()
        pairs_clause = " OR ".join(
            f"(p.match_id = {m} AND p.player_id = {pid})"
            for m, pid in filtered
        )
        where_clause = f"WHERE ({pairs_clause})"
    else:
        # filtered is list of match_ids
        if not filtered:
            return pd.DataFrame()
        where_clause = f"WHERE p.match_id IN ({','.join(map(str, filtered))})"

    # Rest of query using where_clause...
```

### Unit Tests

**New file: `tests/test_queries_result_filter.py`**

```python
"""Tests for result_filter parameter in TournamentQueries."""

import pytest
from tournament_visualizer.data.queries import TournamentQueries

class TestResultFilter:
    def test_get_filtered_match_ids_no_filter_returns_ints(self, test_db):
        """Without result_filter, returns list of match IDs."""
        queries = TournamentQueries(test_db)
        result = queries._get_filtered_match_ids()
        assert all(isinstance(x, int) for x in result)

    def test_get_filtered_match_ids_winners_returns_tuples(self, test_db):
        """With result_filter='winners', returns (match_id, player_id) tuples."""
        queries = TournamentQueries(test_db)
        result = queries._get_filtered_match_ids(result_filter="winners")
        assert all(isinstance(x, tuple) and len(x) == 2 for x in result)

    def test_get_filtered_match_ids_losers_returns_tuples(self, test_db):
        """With result_filter='losers', returns (match_id, player_id) tuples."""
        queries = TournamentQueries(test_db)
        result = queries._get_filtered_match_ids(result_filter="losers")
        assert all(isinstance(x, tuple) and len(x) == 2 for x in result)

    def test_winners_and_losers_are_disjoint(self, test_db):
        """Winners and losers sets should not overlap."""
        queries = TournamentQueries(test_db)
        winners = set(queries._get_filtered_match_ids(result_filter="winners"))
        losers = set(queries._get_filtered_match_ids(result_filter="losers"))
        assert winners.isdisjoint(losers)

    def test_winners_plus_losers_equals_all_players(self, test_db):
        """Winners + losers should equal all players in matches with winner data."""
        queries = TournamentQueries(test_db)
        winners = set(queries._get_filtered_match_ids(result_filter="winners"))
        losers = set(queries._get_filtered_match_ids(result_filter="losers"))

        # Get all match_ids that have winner data
        match_ids_with_winners = {m for m, _ in winners}

        # All players in those matches
        all_result = queries._get_filtered_match_ids(result_filter="all")
        # Filter to only matches with winner data
        all_players_query = f"""
            SELECT DISTINCT match_id, player_id FROM players
            WHERE match_id IN ({','.join(map(str, match_ids_with_winners))})
        """
        # ... verify winners | losers == all players in those matches

    def test_matches_without_winner_excluded_from_winners_losers(self, test_db):
        """Matches without winner data should not appear in winners/losers results."""
        queries = TournamentQueries(test_db)
        winners = queries._get_filtered_match_ids(result_filter="winners")
        losers = queries._get_filtered_match_ids(result_filter="losers")

        winner_match_ids = {m for m, _ in winners}
        loser_match_ids = {m for m, _ in losers}

        # All returned matches should have winner data
        for match_id in winner_match_ids | loser_match_ids:
            assert queries._get_winner_player_ids([match_id])
```

---

## Phase 2: UI and Callbacks

### Affected Files
| File | Changes |
|------|---------|
| `tournament_visualizer/pages/overview.py` | Add Result dropdown, update all callbacks, add warning logic |
| `tests/test_overview_filter_connections.py` | Add Result filter to `REQUIRED_FILTER_INPUTS` |

### Implementation

**1. Add Result dropdown to filter panel (around line 200 in filter UI section):**

```python
dbc.Col([
    html.Label("Result", className="form-label small text-muted"),
    dcc.Dropdown(
        id="overview-result-dropdown",
        options=[
            {"label": "All Players", "value": "all"},
            {"label": "Winners", "value": "winners"},
            {"label": "Losers", "value": "losers"},
        ],
        value="all",
        clearable=False,
        className="mb-2",
    ),
], md=2),
```

**2. Update clear filters callback (line ~925):**

Add output:
```python
Output("overview-result-dropdown", "value"),
```

Add to return tuple:
```python
return (None, 200, None, None, None, None, None, "all")  # Added "all" for result
```

**3. Add Input to all chart callbacks:**

Add to each callback's Input list:
```python
Input("overview-result-dropdown", "value"),
```

Add parameter to each callback function:
```python
result_filter: Optional[str],
```

**4. Charts requiring warning (6 charts):**

Define constant at top of file:
```python
WARN_ON_RESULT_FILTER = {
    "overview-nation-win-chart",
    "overview-nation-loss-chart",
    "overview-pick-order-win-rate",
    "overview-law-efficiency",
    "overview-ruler-trait-performance-chart",
    "overview-ruler-matchup-matrix-chart",
    "overview-counter-pick-heatmap",
}
```

**5. Add warning banner component:**

Add helper function:
```python
def _add_result_filter_warning(fig: go.Figure, result_filter: str) -> go.Figure:
    """Adds annotation warning that win-rate data is filtered."""
    if result_filter in ("winners", "losers"):
        fig.add_annotation(
            text=f"⚠️ Filtered to {result_filter} only - win rates not meaningful",
            xref="paper", yref="paper",
            x=0.5, y=1.02,
            showarrow=False,
            font=dict(size=12, color="orange"),
            xanchor="center",
        )
    return fig
```

**6. Update affected chart callbacks to add warning:**

For each chart in `WARN_ON_RESULT_FILTER`, add before return:
```python
if chart_id in WARN_ON_RESULT_FILTER:
    fig = _add_result_filter_warning(fig, result_filter)
```

**7. Pass result_filter to query methods:**

Update each callback to pass the parameter:
```python
df = queries.get_nation_popularity(
    tournament_round=round_num,
    # ... other params ...
    result_filter=result_filter,
)
```

### Unit Tests

**Update `tests/test_overview_filter_connections.py`:**

Add to `REQUIRED_FILTER_INPUTS`:
```python
REQUIRED_FILTER_INPUTS = [
    "overview-round-filter-dropdown",
    "overview-turn-length-slider",
    "overview-map-size-dropdown",
    "overview-map-class-dropdown",
    "overview-map-aspect-dropdown",
    "overview-nations-dropdown",
    "overview-players-dropdown",
    "overview-result-dropdown",  # NEW
]
```

Existing tests will automatically verify that all charts receive the new filter input.

**Add test for warning charts constant:**
```python
def test_warn_charts_exist_in_layout():
    """All charts in WARN_ON_RESULT_FILTER should exist in the layout."""
    from tournament_visualizer.pages.overview import WARN_ON_RESULT_FILTER
    # Verify each chart_id in WARN_ON_RESULT_FILTER has a callback
    for chart_id in WARN_ON_RESULT_FILTER:
        assert any(
            chart_id in str(cb.get("output", ""))
            for cb in GLOBAL_CALLBACK_LIST
        ), f"Chart {chart_id} in WARN_ON_RESULT_FILTER but no callback found"
```
