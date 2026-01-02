# CSV Export Implementation Guide

This guide explains how to add CSV download functionality to charts in the tournament visualizer.

## Overview

The CSV export feature allows users to download the raw data behind any chart as a CSV file. The exported data:
- Matches exactly what's displayed in the chart (same filters applied)
- Includes descriptive filenames with filter information and timestamps
- Provides the underlying data, not just aggregated values (configurable)

**Example filename:**
```
science_production_result=losers_round=3_max_turns=100_20251130_143022.csv
```

## Architecture

The CSV export system consists of three components:

1. **Download Utilities** (`tournament_visualizer/downloads.py`)
   - Helper functions for filename generation and data preparation
   - Reusable across all chart types

2. **UI Components** (`tournament_visualizer/components/layouts.py`)
   - Download button and `dcc.Download` component
   - Integrated into `create_chart_card()` via `download_id` parameter

3. **Download Callbacks** (in page files)
   - Mirror chart callbacks but return CSV data instead of figures
   - Use `State` for filter inputs (not `Input`) to avoid triggering on filter changes

## Quick Start

### For Simple Charts Using `create_chart_card()`

If your chart already uses `create_chart_card()`, adding CSV export is a one-liner + callback:

**Step 1: Add `download_id` to layout**

```python
# In your page layout (e.g., pages/overview.py)
create_chart_card(
    title="My Chart",
    chart_id="my-chart",
    download_id="my-chart-download",  # <-- Add this
)
```

**Step 2: Create download callback**

```python
# In your page file, near other callbacks
from tournament_visualizer.downloads import generate_filename

@callback(
    Output("my-chart-download", "data"),
    Input("my-chart-download-btn", "n_clicks"),
    State("filter-1", "value"),
    State("filter-2", "value"),
    # ... same State inputs as chart callback
    prevent_initial_call=True,
)
def download_my_chart_data(
    n_clicks: int,
    filter1: str,
    filter2: str,
) -> dict:
    """Download CSV data for my chart."""
    try:
        # Get data using same query as chart callback
        queries = get_queries()
        df = queries.get_my_data(filter1, filter2)

        if df.empty:
            return dcc.send_data_frame(
                pd.DataFrame({"message": ["No data available"]}).to_csv,
                "no_data.csv",
                index=False,
            )

        # Generate descriptive filename
        filename = generate_filename(
            "my_chart",
            {"filter1": filter1, "filter2": filter2},
        )

        return dcc.send_data_frame(df.to_csv, filename, index=False)

    except Exception as e:
        logger.error(f"Error generating download: {e}")
        return dcc.send_data_frame(
            pd.DataFrame({"error": [str(e)]}).to_csv,
            "error.csv",
            index=False,
        )
```

Done! Your chart now has a CSV download button.

## Detailed Implementation

### 1. Update Layout

#### Option A: Using `create_chart_card()` (Recommended)

```python
from tournament_visualizer.components.layouts import create_chart_card

# In your layout
create_chart_card(
    title="Player Performance",
    chart_id="player-performance-chart",
    height="400px",
    download_id="player-performance-download",  # Enables download button
)
```

This automatically adds:
- Download button with icon in card header
- `dcc.Download` component with ID `player-performance-download`
- Button trigger with ID `player-performance-download-btn`

#### Option B: Custom Layout

For custom layouts (like Science chart with scale toggle):

```python
dbc.Card([
    dbc.CardHeader([
        html.H5("My Chart"),
        html.Div([
            # Your custom controls here
            dbc.Button(
                [html.I(className="bi bi-download me-1"), "CSV"],
                id="my-chart-download-btn",
                size="sm",
                color="secondary",
                outline=True,
            ),
            dcc.Download(id="my-chart-download"),
        ]),
    ]),
    dbc.CardBody([
        dcc.Graph(id="my-chart"),
    ]),
])
```

### 2. Create Download Callback

#### Basic Pattern

```python
from dash import Input, Output, State, callback, dcc
from tournament_visualizer.data.queries import get_queries
from tournament_visualizer.downloads import generate_filename

@callback(
    Output("my-chart-download", "data"),
    Input("my-chart-download-btn", "n_clicks"),
    State("filter-1", "value"),
    State("filter-2", "value"),
    prevent_initial_call=True,
)
def download_chart_data(n_clicks, filter1, filter2):
    queries = get_queries()
    df = queries.get_data(filter1, filter2)

    filename = generate_filename("my_chart", {"filter1": filter1})
    return dcc.send_data_frame(df.to_csv, filename, index=False)
```

#### Key Points

1. **Use `State` not `Input`** for filters
   - Prevents callback from triggering every time filters change
   - Only triggers when user clicks download button

2. **Match chart callback filters**
   - Ensures downloaded data matches displayed chart
   - Copy filter parameters from chart callback

3. **Reuse query logic**
   - Call the same query methods as chart callback
   - Extract to helper functions if needed (DRY principle)

4. **Always set `prevent_initial_call=True`**
   - Prevents download on page load

### 3. Data Preparation

#### Simple Case: Single DataFrame

If your query returns a single DataFrame:

```python
df = queries.get_simple_data(filters)
return dcc.send_data_frame(df.to_csv, filename, index=False)
```

#### Complex Case: Multiple DataFrames

For charts that combine multiple data sources (like yield charts with rate + cumulative):

```python
from tournament_visualizer.downloads import prepare_yield_data_for_csv

# Get data (returns dict with multiple DataFrames)
data = queries.get_yield_with_cumulative(yield_type, **filters)

# Combine into single CSV-ready DataFrame
csv_df = prepare_yield_data_for_csv(
    data["rate"],
    data["cumulative"],
    "Science",
)

return dcc.send_data_frame(csv_df.to_csv, filename, index=False)
```

**Create custom preparation functions for complex charts:**

```python
# In tournament_visualizer/downloads.py

def prepare_my_chart_data_for_csv(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
) -> pd.DataFrame:
    """Combine multiple DataFrames for CSV export.

    Args:
        df1: First data source
        df2: Second data source

    Returns:
        Combined DataFrame ready for CSV export
    """
    result = df1.merge(df2, on="common_column", how="outer")
    # Add any necessary column renaming, formatting
    return result
```

### 4. Filename Generation

Use `generate_filename()` to create descriptive filenames:

```python
from tournament_visualizer.downloads import generate_filename

# Basic usage
filename = generate_filename("player_performance")
# Result: player_performance_20251130_143022.csv

# With filters
filename = generate_filename(
    "player_performance",
    {
        "result": "winners",
        "round": 3,
        "nation": "Rome",
    }
)
# Result: player_performance_result=winners_round=3_nation=Rome_20251130_143022.csv

# Handles lists automatically
filename = generate_filename(
    "yield_analysis",
    {
        "nations": ["Rome", "Egypt"],  # Short list: includes all
        "players": ["Player1", "Player2", "Player3"],  # Long list: shows count
    }
)
# Result: yield_analysis_nations=Rome+Egypt_players=3items_20251130_143022.csv
```

**Filter handling:**
- `None` values are skipped
- `"all"` string is skipped
- Empty lists `[]` are skipped
- Lists with 1-2 items: includes all values joined with `+`
- Lists with 3+ items: shows count as `Nitems`

### 5. Error Handling

Always wrap download callbacks in try/except:

```python
@callback(...)
def download_data(...):
    try:
        # Get and prepare data
        df = queries.get_data(...)

        # Check for empty data
        if df.empty:
            return dcc.send_data_frame(
                pd.DataFrame({"message": ["No data available for selected filters"]}).to_csv,
                "no_data.csv",
                index=False,
            )

        filename = generate_filename(...)
        return dcc.send_data_frame(df.to_csv, filename, index=False)

    except Exception as e:
        logger.error(f"Error generating download: {e}")
        return dcc.send_data_frame(
            pd.DataFrame({"error": [str(e)]}).to_csv,
            "error.csv",
            index=False,
        )
```

## Examples

### Example 1: Simple Single-DataFrame Chart

```python
# Layout
create_chart_card(
    title="Nation Win Rates",
    chart_id="nation-win-rates",
    download_id="nation-win-rates-download",
)

# Callback
@callback(
    Output("nation-win-rates-download", "data"),
    Input("nation-win-rates-download-btn", "n_clicks"),
    State("round-filter", "value"),
    State("bracket-filter", "value"),
    prevent_initial_call=True,
)
def download_nation_win_rates(n_clicks, round_num, bracket):
    queries = get_queries()
    df = queries.get_nation_win_rates(
        tournament_round=round_num,
        bracket=bracket,
    )

    if df.empty:
        return dcc.send_data_frame(
            pd.DataFrame({"message": ["No data"]}).to_csv,
            "no_data.csv",
            index=False,
        )

    filename = generate_filename(
        "nation_win_rates",
        {"round": round_num, "bracket": bracket},
    )

    return dcc.send_data_frame(df.to_csv, filename, index=False)
```

### Example 2: Multiple Charts with Factory Function

For pages with many similar charts (like yield charts):

```python
# Create factory function
def _create_download_callback(chart_type: str, display_name: str):
    download_id = f"overview-{chart_type}-download"

    @callback(
        Output(download_id, "data"),
        Input(f"{download_id}-btn", "n_clicks"),
        State("filter-1", "value"),
        State("filter-2", "value"),
        prevent_initial_call=True,
    )
    def download_data(n_clicks, filter1, filter2):
        queries = get_queries()
        df = queries.get_data(chart_type, filter1, filter2)

        filename = generate_filename(
            f"{display_name.lower()}_production",
            {"filter1": filter1, "filter2": filter2},
        )

        return dcc.send_data_frame(df.to_csv, filename, index=False)

    return download_data

# Register callbacks for multiple charts
CHART_TYPES = [
    ("science", "Science"),
    ("orders", "Orders"),
    ("food", "Food"),
]

for chart_type, display_name in CHART_TYPES:
    _create_download_callback(chart_type, display_name)
```

### Example 3: Custom Data Preparation

For charts with complex aggregations:

```python
# In downloads.py
def prepare_player_stats_for_csv(
    stats_df: pd.DataFrame,
    matches_df: pd.DataFrame,
) -> pd.DataFrame:
    """Combine player stats with match context for CSV export."""
    result = stats_df.merge(
        matches_df[["match_id", "match_name", "tournament_round"]],
        on="match_id",
        how="left",
    )

    # Reorder columns for readability
    cols = ["player_name", "match_name", "tournament_round", "score", "rank"]
    return result[cols]

# In page callback
@callback(...)
def download_player_stats(...):
    stats = queries.get_player_stats(...)
    matches = queries.get_matches(...)

    csv_df = prepare_player_stats_for_csv(stats, matches)

    filename = generate_filename("player_stats", filters)
    return dcc.send_data_frame(csv_df.to_csv, filename, index=False)
```

## Best Practices

### 1. Data Consistency

✅ **DO**: Use the same query and filters as the chart callback

```python
# Chart callback
@callback(Output("chart", "figure"), Input("filter", "value"))
def update_chart(filter_val):
    df = queries.get_data(filter_val)  # Query here
    return create_chart(df)

# Download callback
@callback(Output("download", "data"), State("filter", "value"))
def download_data(n_clicks, filter_val):
    df = queries.get_data(filter_val)  # Same query here
    return dcc.send_data_frame(df.to_csv, filename)
```

❌ **DON'T**: Use different queries or filters

```python
# Chart shows filtered data
df = queries.get_data(filter_val)

# Download returns all data (inconsistent!)
df = queries.get_data()  # Wrong!
```

### 2. Extract Shared Logic (DRY)

✅ **DO**: Extract query logic to shared functions

```python
def get_chart_data(filter1, filter2):
    """Shared data fetching logic for chart and download."""
    queries = get_queries()
    return queries.get_data(filter1, filter2)

@callback(Output("chart", "figure"), Input("filter1", "value"))
def update_chart(filter1, filter2):
    df = get_chart_data(filter1, filter2)
    return create_chart(df)

@callback(Output("download", "data"), State("filter1", "value"))
def download_data(n_clicks, filter1, filter2):
    df = get_chart_data(filter1, filter2)
    return dcc.send_data_frame(df.to_csv, filename)
```

### 3. Descriptive Filenames

✅ **DO**: Include filter information in filenames

```python
filename = generate_filename(
    "player_performance",
    {
        "result": result_filter,
        "round": round_num,
        "nation": nation,
    }
)
# Result: player_performance_result=winners_round=3_nation=Rome_20251130.csv
```

❌ **DON'T**: Use generic filenames

```python
filename = "data.csv"  # Not helpful!
filename = "export.csv"  # Too vague!
```

### 4. Column Naming

✅ **DO**: Use clear, human-readable column names

```python
df.columns = [
    "player_name",
    "total_score",
    "games_played",
    "win_rate_percent",
]
```

❌ **DON'T**: Keep database column names or abbreviations

```python
# Unclear columns
df.columns = ["p_nm", "tot_sc", "cnt", "wr"]
```

### 5. Empty Data Handling

✅ **DO**: Return informative message when no data

```python
if df.empty:
    return dcc.send_data_frame(
        pd.DataFrame({
            "message": ["No data available for selected filters"]
        }).to_csv,
        "no_data.csv",
        index=False,
    )
```

✅ **ALSO OK**: Return empty DataFrame with column headers

```python
if df.empty:
    # Return empty DataFrame with proper columns
    empty_df = pd.DataFrame(columns=["player_name", "score", "rank"])
    return dcc.send_data_frame(empty_df.to_csv, "no_data.csv", index=False)
```

### 6. Performance Considerations

For large datasets (>10k rows):

```python
# Consider adding warnings or limits
if len(df) > 50000:
    logger.warning(f"Large CSV download: {len(df)} rows")
    # Optionally: truncate or sample
    # df = df.head(50000)
```

## Testing Checklist

When adding CSV export to a new chart:

- [ ] Download button appears in chart card header
- [ ] Clicking button triggers download
- [ ] Filename includes chart name and timestamp
- [ ] Filename includes active filters
- [ ] CSV contains same data as displayed in chart
- [ ] CSV has clear column names
- [ ] Empty data returns informative message (not error)
- [ ] Multiple filter combinations work correctly
- [ ] Large datasets download without errors
- [ ] No console errors in browser or server logs

## Troubleshooting

### Button doesn't appear

**Check:** Did you add `download_id` parameter?

```python
create_chart_card(
    title="My Chart",
    chart_id="my-chart",
    download_id="my-chart-download",  # ← Must be present
)
```

### Download doesn't trigger

**Check:** Is callback registered and using correct IDs?

```python
@callback(
    Output("my-chart-download", "data"),  # ← Must match download_id
    Input("my-chart-download-btn", "n_clicks"),  # ← Note -btn suffix
    prevent_initial_call=True,  # ← Must be True
)
```

### Downloaded data doesn't match chart

**Check:** Are filters identical?

```python
# Chart callback filters
Input("filter-1", "value"),
Input("filter-2", "value"),

# Download callback filters (should be State, not Input)
State("filter-1", "value"),  # ← Same filter IDs
State("filter-2", "value"),  # ← Same filter IDs
```

**Check:** Is query called with same parameters?

```python
# Both should call same query with same args
queries.get_data(filter1, filter2)
```

### Filename is always generic

**Check:** Are you passing filters to `generate_filename()`?

```python
# Wrong
filename = generate_filename("my_chart")  # No filters

# Correct
filename = generate_filename("my_chart", {
    "filter1": filter1_value,
    "filter2": filter2_value,
})
```

### Download triggers on page load

**Check:** Is `prevent_initial_call=True` set?

```python
@callback(
    ...,
    prevent_initial_call=True,  # ← Required
)
```

### Error: "callback input/output already registered"

**Check:** Do you have duplicate callback decorators?

- Each download callback should be registered only once
- If using factory functions, ensure they're called only once per chart

## Reference

### Available Utilities

**From `tournament_visualizer/downloads.py`:**

```python
generate_filename(
    chart_name: str,
    filters: Optional[Dict[str, Any]] = None,
    extension: str = "csv",
) -> str

prepare_yield_data_for_csv(
    rate_df: pd.DataFrame,
    cumulative_df: pd.DataFrame,
    yield_name: str,
) -> pd.DataFrame

prepare_generic_chart_data_for_csv(
    df: pd.DataFrame
) -> pd.DataFrame
```

### Component Parameters

**`create_chart_card()`:**

```python
create_chart_card(
    title: str,              # Required: Chart title
    chart_id: str,           # Required: Chart component ID
    height: str = "400px",   # Optional: Chart height
    loading: bool = True,    # Optional: Show loading spinner
    controls: List = None,   # Optional: Custom controls
    download_id: str = None, # Optional: Enables CSV download
) -> dbc.Card
```

### Dash Download API

```python
# Send DataFrame as CSV
dcc.send_data_frame(
    df.to_csv,           # DataFrame conversion method
    filename,            # Filename for download
    index=False,         # Don't include DataFrame index
)

# Send string content
dcc.send_string(
    "csv,data\n1,2",     # CSV string content
    filename,            # Filename for download
)

# Send bytes
dcc.send_bytes(
    bytes_data,          # Bytes content
    filename,            # Filename for download
)
```

## See Also

- [Filter System Reference](filter-system.md) - Understanding filter architecture
- [UI Architecture](../ui-architecture.md) - Chart and layout patterns
- [Dash dcc.Download Documentation](https://dash.plotly.com/dash-core-components/download)
