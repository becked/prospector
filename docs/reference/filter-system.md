# Filter System Reference

## Overview Page Filters

The overview page (`tournament_visualizer/pages/overview.py`) provides 7 filter inputs:

| Filter | Component ID | Type | Default |
|--------|-------------|------|---------|
| Tournament Round | `overview-round-filter-dropdown` | Multi-select | `None` |
| Turn Length | `overview-turn-length-slider` | Slider | `200` |
| Map Size | `overview-map-size-dropdown` | Multi-select | `None` |
| Map Class | `overview-map-class-dropdown` | Multi-select | `None` |
| Map Aspect | `overview-map-aspect-dropdown` | Multi-select | `None` |
| Nations | `overview-nations-dropdown` | Multi-select | `None` |
| Players | `overview-players-dropdown` | Multi-select | `None` |

## Component ID Convention

Pattern: `{page}-{filter-name}-{component-type}`

Examples:
- `overview-round-filter-dropdown`
- `overview-turn-length-slider`
- `overview-nations-dropdown`

## Filter UI Layout

Defined in `overview.py` lines 105-287. The filter panel is collapsible via:
- Toggle button: `overview-filter-toggle`
- Collapse container: `overview-filter-collapse`
- Clear all button: `overview-clear-filters-btn`

## Callback Structure

### Filter Population Callbacks

Each dropdown's options are populated dynamically from the database:

```python
@callback(
    Output("overview-round-filter-dropdown", "options"),
    Input("refresh-interval", "n_intervals"),
)
def update_round_options(n_intervals: int) -> List[dict]:
    queries = get_queries()
    return queries.get_available_rounds()
```

Population callbacks (lines 755-904):
- `update_round_options()` - Fetches distinct rounds
- `update_map_size_options()` - Fetches distinct map sizes
- `update_map_class_options()` - Fetches distinct map classes
- `update_map_aspect_options()` - Fetches distinct map aspects
- `update_nations_options()` - Fetches distinct civilizations
- `update_players_options()` - Fetches distinct player names

### Chart Update Callbacks

Every chart callback receives all 7 filter inputs plus the refresh interval:

```python
@callback(
    Output("overview-nation-win-chart", "figure"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-turn-length-slider", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_nation_win_chart(
    round_num: Optional[list[int]],
    turn_length: Optional[int],
    map_size: Optional[list[str]],
    map_class: Optional[list[str]],
    map_aspect: Optional[list[str]],
    nations: Optional[list[str]],
    players: Optional[list[str]],
    n_intervals: int,
):
```

### Clear Filters Callback

Resets all filters to defaults (line 925-953):

```python
@callback(
    Output("overview-round-filter-dropdown", "value"),
    Output("overview-turn-length-slider", "value"),
    Output("overview-map-size-dropdown", "value"),
    Output("overview-map-class-dropdown", "value"),
    Output("overview-map-aspect-dropdown", "value"),
    Output("overview-nations-dropdown", "value"),
    Output("overview-players-dropdown", "value"),
    Input("overview-clear-filters-btn", "n_clicks"),
    prevent_initial_call=True,
)
def clear_all_filters(n_clicks):
    return (None, 200, None, None, None, None, None)
```

## Query Layer Integration

### Filter Helper Method

`TournamentQueries._get_filtered_match_ids()` in `queries.py` (line 3865) centralizes filter logic:

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
) -> list[int]:
```

Returns a list of `match_id` integers matching all provided filters. Query methods use this to filter their results.

### Turn Length Conversion

The slider value is converted to min/max turns via `parse_turn_length()` (line 55-66):

```python
def parse_turn_length(turn_length: Optional[int]) -> tuple[Optional[int], Optional[int]]:
    if turn_length is None:
        return (None, None)
    return (None, turn_length)  # Returns (min_turns=None, max_turns=slider_value)
```

## Adding a New Filter

1. **Add UI component** in the filter panel layout (around line 105)

2. **Add population callback** if the filter needs dynamic options:
   ```python
   @callback(
       Output("overview-new-filter-dropdown", "options"),
       Input("refresh-interval", "n_intervals"),
   )
   def update_new_filter_options(n_intervals: int) -> List[dict]:
       queries = get_queries()
       return queries.get_available_new_filter_values()
   ```

3. **Add to clear callback** outputs and return tuple (line 925)

4. **Add Input to all chart callbacks** - Each chart callback must include the new filter as an Input

5. **Update query methods** to accept and apply the new filter parameter

6. **Update `_get_filtered_match_ids()`** to handle the new filter in the WHERE clause

7. **Update tests** in `tests/test_overview_filter_connections.py`:
   - Add to `REQUIRED_FILTER_INPUTS` list
   - Tests will automatically verify all charts receive the new filter

## Adding a New Chart

1. **Add chart component** in layout using `create_chart_card()`:
   ```python
   create_chart_card(
       title="New Chart Title",
       chart_id="overview-new-chart",
       height="400px",
   )
   ```

2. **Create callback** with all filter inputs:
   ```python
   @callback(
       Output("overview-new-chart", "figure"),
       Input("overview-round-filter-dropdown", "value"),
       Input("overview-turn-length-slider", "value"),
       Input("overview-map-size-dropdown", "value"),
       Input("overview-map-class-dropdown", "value"),
       Input("overview-map-aspect-dropdown", "value"),
       Input("overview-nations-dropdown", "value"),
       Input("overview-players-dropdown", "value"),
       Input("refresh-interval", "n_intervals"),
   )
   def update_new_chart(...):
   ```

3. **Run tests** to verify filter connections:
   ```bash
   uv run python -m pytest tests/test_overview_filter_connections.py -v
   ```

## Factory Pattern for Similar Charts

For groups of similar charts, use the factory pattern (see yield charts, line 2010-2081):

```python
def _create_yield_callback(yield_type: str, display_name: str, ...):
    chart_id = f"overview-yield-{yield_type.lower()}"

    @callback(
        Output(chart_id, "figure"),
        Input("overview-round-filter-dropdown", "value"),
        # ... all filter inputs
    )
    def update_yield_chart(...):
        # Implementation using yield_type parameter
        pass

    return update_yield_chart

# Register callbacks
for yield_type, display_name, ... in YIELD_CHARTS:
    _create_yield_callback(yield_type, display_name, ...)
```

## Dash Callback Registry

Callbacks are stored in `dash._callback.GLOBAL_CALLBACK_LIST` after page import. Each entry is a dict:

```python
{
    'output': 'overview-nation-win-chart.figure',
    'inputs': [
        {'id': 'overview-round-filter-dropdown', 'property': 'value'},
        {'id': 'overview-turn-length-slider', 'property': 'value'},
        # ...
    ],
    'state': [],
    'prevent_initial_call': False,
    # ...
}
```

Access via:
```python
from tournament_visualizer.app import app  # Must import app first
from tournament_visualizer.pages import overview  # Registers callbacks
from dash._callback import GLOBAL_CALLBACK_LIST
```

## Testing

`tests/test_overview_filter_connections.py` validates:

- All chart IDs in layout have corresponding callbacks
- All chart callbacks receive all required filter inputs
- Filter dropdown population callbacks exist
- Each filter is used by at least one chart

Run with:
```bash
uv run python -m pytest tests/test_overview_filter_connections.py -v
```
