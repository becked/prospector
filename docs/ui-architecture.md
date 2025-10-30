# Tournament Visualizer - UI/Dashboard Architecture Summary

## Overview

The application is built on **Dash** (Flask-based reactive framework) with **Plotly** for visualizations and **Dash Bootstrap Components (dbc)** for styling and layout. The architecture follows a modular, component-driven approach with multi-page support.

---

## 1. Directory Structure

### Core Application Files

```
tournament_visualizer/
├── app.py                    # Main Dash app initialization & global callbacks
├── config.py                 # Configuration, constants, defaults
├── nation_colors.py          # Nation/civilization color mappings
│
├── components/
│   ├── __init__.py
│   ├── charts.py            # 50+ chart creation functions (Plotly)
│   ├── layouts.py           # Reusable layout components (cards, grids, modals)
│   └── filters.py           # Filter components & filter callbacks
│
├── pages/
│   ├── __init__.py
│   ├── overview.py          # Tournament summary dashboard (multi-tab)
│   ├── matches.py           # Individual match analysis (78KB - largest page)
│   ├── players.py           # Player rankings & head-to-head
│   └── maps.py              # Map performance analysis
│
├── assets/
│   └── style.css            # Custom CSS (460 lines, responsive design)
│
└── data/                     # Database & query layer
    ├── queries.py           # TournamentQueries class for all data
    └── ...
```

### File Sizes
- **charts.py**: ~4600 lines (60+ chart functions)
- **matches.py**: ~78KB (complex match detail page)
- **overview.py**: ~35KB (main dashboard with 4+ tabs)
- **layouts.py**: ~570 lines (15+ layout helpers)
- **app.py**: ~466 lines (app setup + 3 global callbacks)

---

## 2. Layout Patterns

### 2.1 Page Structure (Standard Pattern)

All pages follow this consistent structure:

```python
# pages/overview.py
import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, html, dcc

# Register page
dash.register_page(__name__, path="/", name="Overview")

# Static layout definition
layout = html.Div([
    # 1. Page header with title & description
    create_page_header(
        title="Tournament Overview",
        description="High-level tournament statistics",
        icon="bi-bar-chart-fill"
    ),
    
    # 2. Optional alerts/status messages
    html.Div(id="overview-alerts"),
    
    # 3. Main content (tabs, grid, cards)
    dbc.Tabs([...]),
])

# 4. Callbacks to populate content
@callback(...)
def update_metrics(n_intervals):
    ...
```

**Key Pattern**: Layout is static with `html.Div(id="...")` placeholders. Callbacks populate these via `Output`.

### 2.2 Card-Based Grid System

The dashboard uses Bootstrap 12-column grid with dbc.Card components:

```python
# Create metric cards in a grid
dbc.Row([
    dbc.Col([
        create_metric_card(
            title="Total Matches",
            value=42,
            icon="bi-trophy",
            color="primary",
        )
    ], width=3),  # 25% of row
])
```

**Grid Widths**: 
- 4 columns = 33% (3-chart rows)
- 6 columns = 50% (2-chart rows)
- 12 columns = 100% (full width)

### 2.3 Tabbed Layouts

Multi-tab pages for organizing related content:

```python
dbc.Tabs([
    dbc.Tab(label="Summary", tab_id="summary-tab", children=[...]),
    dbc.Tab(label="Nations", tab_id="nations-tab", children=[...]),
    dbc.Tab(label="Rulers", tab_id="rulers-tab", children=[...]),
], id="overview-tabs", active_tab="summary-tab")
```

**Pages with Tabs**:
- Overview: 4 tabs (Summary, Nations, Rulers, Economy)
- Matches: Dynamic tabs per match (Progression, Yields, Laws, Techs, etc.)
- Players: 2 tabs (Rankings, Head-to-Head)

### 2.4 Chart Card Pattern

Standard pattern for chart containers:

```python
create_chart_card(
    title="Nation Win Percentage",      # Card header title
    chart_id="overview-nation-win",     # Unique ID for callback targeting
    height="400px",                     # Card height
    loading=True,                       # Show loading spinner
    controls=[...],                     # Optional filter controls inside card
)
```

**Important**: No internal chart titles - the card header provides context.

---

## 3. Chart/Visualization Patterns

### 3.1 Chart Creation Functions

Located in **components/charts.py** (60+ functions). All follow consistent pattern:

```python
def create_nation_win_percentage_chart(df: pd.DataFrame) -> go.Figure:
    """Create pie chart showing nation win percentages.
    
    Args:
        df: DataFrame with columns: nation, win_rate
    
    Returns:
        Plotly figure with pie chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No nation data available")
    
    fig = create_base_figure(
        title="",  # NO TITLE - card header shows it
        show_legend=True,
    )
    
    fig.add_trace(go.Pie(
        labels=df["nation"],
        values=df["win_rate"],
        marker_colors=[get_nation_color(n) for n in df["nation"]],
    ))
    
    return fig
```

**Key Principles**:
1. **No chart titles** - card titles provide context (per CLAUDE.md convention)
2. **Empty state handling** - check `if df.empty` first
3. **Reuse colors** - use `Config.PRIMARY_COLORS` or civilization colors
4. **Type hints** - always include arg types and return type
5. **Docstrings** - explain what data is expected

### 3.2 Chart Types Used

**Bar/Horizontal Bar**:
```python
fig.add_trace(go.Bar(
    x=df["win_rate"],
    y=df["player_name"],
    orientation="h",
    marker_color=Config.PRIMARY_COLORS[0],
    text=[f"{rate:.1f}%" for rate in df["win_rate"]],
    textposition="auto",
))
fig.update_layout(yaxis={"categoryorder": "total ascending"})
```

**Line/Area**:
```python
fig.add_trace(go.Scatter(
    x=df["turn"],
    y=df["science"],
    mode="lines+markers",  # or just "lines"
    fill="tozeroy",        # for area charts
    name="Science",
))
```

**Pie/Donut**:
```python
fig.add_trace(go.Pie(labels=..., values=..., hole=0.4))  # hole=0.4 for donut
```

**Heatmap**:
```python
fig.add_trace(go.Heatmap(
    z=pivot_data.values,
    x=pivot_data.columns,
    y=pivot_data.index,
    colorscale="RdYlBu",
))
```

**Sunburst** (hierarchical):
```python
fig.add_trace(go.Sunburst(
    labels=df["label"],
    parents=df["parent"],
    values=df["count"],
))
```

**Scatter**:
```python
fig.add_trace(go.Scatter(
    x=df["x_col"],
    y=df["y_col"],
    mode="markers",
    marker=dict(size=8, color=df["color_col"], colorscale="Viridis"),
))
```

### 3.3 Base Figure Setup

All charts use `create_base_figure()` for consistency:

```python
def create_base_figure(
    title: str = "",
    height: int = None,
    show_legend: bool = True,
    x_title: str = "",
    y_title: str = "",
) -> go.Figure:
    """Create a base figure with consistent styling."""
    layout = DEFAULT_CHART_LAYOUT.copy()
    layout.update({
        "title": {"text": title, "x": 0.5, "xanchor": "center"},
        "showlegend": show_legend,
        "xaxis_title": x_title,
        "yaxis_title": y_title,
    })
    if height:
        layout["height"] = height
    return go.Figure(layout=layout)
```

**DEFAULT_CHART_LAYOUT** (from config.py):
```python
DEFAULT_CHART_LAYOUT = {
    "margin": {"l": 50, "r": 50, "t": 50, "b": 50},
    "height": 400,  # Default, overridable
    "showlegend": True,
    "legend": {"x": 0, "y": 1, "bgcolor": "rgba(255,255,255,0.8)"},
    "font": {"size": 12},
    "plot_bgcolor": "rgba(0,0,0,0)",  # Transparent background
    "paper_bgcolor": "rgba(0,0,0,0)",
}
```

### 3.4 Chart in Page Callback

Standard pattern to populate chart in page:

```python
@callback(
    Output("overview-nation-win-chart", "figure"),
    Input("refresh-interval", "n_intervals"),
)
def update_nation_win_chart(n_intervals: int):
    """Update nation win percentage chart."""
    try:
        queries = get_queries()
        df = queries.get_nation_win_stats()
        
        if df.empty:
            return create_empty_chart_placeholder("No nation data")
        
        return create_nation_win_percentage_chart(df)
    
    except Exception as e:
        return create_empty_chart_placeholder(f"Error: {str(e)}")
```

**Pattern**:
1. Get data from `queries` (singleton instance)
2. Check if empty
3. Pass to chart function
4. Handle errors with placeholder

---

## 4. Callback Patterns

### 4.1 Basic Chart Update Callback

```python
@callback(
    Output("chart-id", "figure"),
    Input("refresh-interval", "n_intervals"),
)
def update_chart(n_intervals: int):
    """Update chart with latest data."""
    try:
        queries = get_queries()
        df = queries.get_data()
        if df.empty:
            return create_empty_chart_placeholder("No data")
        return create_chart(df)
    except Exception as e:
        return create_empty_chart_placeholder(f"Error: {str(e)}")
```

### 4.2 Data Table Callback

```python
@callback(
    Output("table-id", "data"),
    Input("refresh-interval", "n_intervals"),
)
def update_table(n_intervals: int) -> List[Dict[str, Any]]:
    """Update data table."""
    try:
        queries = get_queries()
        df = queries.get_data()
        if df.empty:
            return []
        return df.to_dict("records")
    except Exception as e:
        logger.error(f"Error: {e}")
        return []
```

### 4.3 Multiple Outputs (Dynamic Content)

```python
@callback(
    [
        Output("match-details-section", "children"),   # Set content
        Output("match-details-section", "style"),      # Show/hide
        Output("match-empty-state", "style"),          # Show/hide
    ],
    Input("match-selector", "value"),
    prevent_initial_call=False,
)
def update_match_details(match_id: Optional[int]):
    """Show/hide match details based on selection."""
    if not match_id:
        # Show empty state, hide details
        return [], {"display": "none"}, {"display": "block"}
    
    # Build content
    details = dbc.Row([...])
    return details, {"display": "block"}, {"display": "none"}
```

### 4.4 Filter-Based Callbacks

```python
@callback(
    Output("player-selector", "options"),
    Input("date-filter", "value"),
    prevent_initial_call=True,
)
def update_player_options(date_range: int) -> List[Dict[str, str]]:
    """Update player list based on date filter."""
    try:
        queries = get_queries()
        df = queries.get_players(date_range_days=date_range)
        return [
            {"label": f"{row['name']} ({row['matches']} matches)", 
             "value": row['name']}
            for _, row in df.iterrows()
        ]
    except Exception as e:
        logger.error(f"Error: {e}")
        return []
```

### 4.5 Conditional Component Enable/Disable

```python
@callback(
    [
        Output("player2-selector", "options"),
        Output("player2-selector", "value"),
        Output("player2-selector", "disabled"),  # Key: disable when no player1
    ],
    Input("player1-selector", "value"),
)
def update_player2(player1: Optional[str]) -> tuple:
    """Enable Player 2 selector only if Player 1 selected."""
    if not player1:
        return [], None, True  # disabled=True
    
    try:
        queries = get_queries()
        opponents = queries.get_opponents(player1)
        options = [{"label": o, "value": o} for o in opponents]
        return options, None, False  # disabled=False
    except Exception as e:
        return [], None, True
```

### 4.6 URL Synchronization

```python
@callback(
    [Output("selector", "value"), Output("url", "search")],
    [Input("url", "search"), Input("selector", "value")],
    prevent_initial_call=False,
)
def sync_selection(url_search: str, value: Any) -> tuple:
    """Keep URL and selector in sync."""
    ctx = dash.callback_context
    
    if not ctx.triggered:
        # Initial load - parse URL
        from urllib.parse import parse_qs
        params = parse_qs(url_search)
        match_id = params.get("match_id", [None])[0]
        return match_id, url_search
    
    # Triggered by selector change
    return value, f"?match_id={value}" if value else ""
```

### 4.7 Toggle Modal

```python
@callback(
    Output("about-modal", "is_open"),
    [Input("about-open-btn", "n_clicks"), 
     Input("about-close-btn", "n_clicks")],
    prevent_initial_call=True,
)
def toggle_modal(open_clicks: int, close_clicks: int) -> bool:
    """Toggle about modal open/closed."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return False
    
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    return button_id == "about-open-btn"
```

### 4.8 Global App Callbacks (in app.py)

```python
@callback(
    Output("db-status-badge", "children"),
    Output("db-status-badge", "color"),
    Input("refresh-interval", "n_intervals"),
)
def update_database_status(n_intervals: int) -> tuple[str, str]:
    """Update database status indicator."""
    try:
        db = get_database()
        with db.get_connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
        
        if count == 0:
            return "No Data", "warning"
        return f"{count} Matches", "success"
    except Exception:
        return "DB Error", "danger"
```

### Callback Best Practices

1. **Always use type hints** on all parameters and returns
2. **Handle exceptions** - return empty/default or placeholder
3. **Check empty data** - `if df.empty: return create_empty_...`
4. **Use `prevent_initial_call=True`** when callback isn't needed on page load
5. **Log errors** - use `logger.error(f"...")`
6. **Use `dash.no_update`** to not update a specific output
7. **Use `dash.callback_context`** to know which input triggered the callback

---

## 5. Component Patterns

### 5.1 Layout Components (layouts.py)

All return dbc components. Examples:

```python
# Metric Card (single KPI)
create_metric_card(
    title="Total Matches",
    value=42,
    icon="bi-trophy",       # Bootstrap icon class
    color="primary",        # Bootstrap color
    subtitle="This month"   # Optional
)

# Chart Card (with embedded chart)
create_chart_card(
    title="Win Rate Trends",
    chart_id="win-rate-chart",
    height="400px",
    loading=True,
    controls=[dcc.Dropdown(...)]  # Optional controls
)

# Data Table Card
create_data_table_card(
    title="Match Results",
    table_id="results-table",
    columns=[
        {"name": "Date", "id": "date", "type": "datetime"},
        {"name": "Winner", "id": "winner"},
        {"name": "Turns", "id": "turns", "type": "numeric"},
    ],
    export_button=True  # Include export button
)

# Filter Card (collapsible)
create_filter_card(
    title="Filters",
    filters=[dcc.Dropdown(...), dcc.DatePickerRange(...)],
    collapsible=True
)

# Page Header
create_page_header(
    title="Overview",
    description="Tournament summary",
    icon="bi-bar-chart",
    actions=[dbc.Button("Export", ...)]  # Optional action buttons
)

# Grid Layout (metric cards)
create_metric_grid([
    {"title": "Metric 1", "value": 100, "icon": "bi-chart"},
    {"title": "Metric 2", "value": 200, "icon": "bi-people"},
])

# Tab Layout
create_tab_layout([
    {"label": "Tab 1", "tab_id": "tab1", "content": [...], ...},
    {"label": "Tab 2", "tab_id": "tab2", "content": [...], ...},
])

# Two/Three Column Layouts
create_two_column_layout(
    left_content=[...],
    right_content=[...],
    left_width=8, right_width=4
)

# Empty State
create_empty_state(
    title="No Data",
    message="No matches found",
    icon="bi-inbox",
    action_button={"text": "Import", "id": "import-btn", "color": "primary"}
)

# Modal Dialog
create_modal_dialog(
    modal_id="confirm-modal",
    title="Confirm",
    body_content=[html.P("Are you sure?")],
    footer_content=[dbc.Button("Yes", ...), dbc.Button("No", ...)],
    size="lg"  # sm, lg, xl
)

# Breadcrumb Navigation
create_breadcrumb([
    {"label": "Home", "href": "/"},
    {"label": "Matches", "href": "/matches"},
    {"label": "Match 123"},  # Last item has no href (current page)
])
```

### 5.2 Filter Components (filters.py)

Reusable filter UI components:

```python
# Date range filter
create_date_range_filter(
    component_id="date-filter",
    label="Date Range",
    default_range=30  # days, or "all"
)

# Player selector
create_player_filter(
    component_id="player-filter",
    label="Players",
    multi=True  # Multiple selection
)

# Civilization filter
create_civilization_filter(
    component_id="civ-filter",
    label="Civilizations",
    multi=True
)

# Match duration filter
create_match_duration_filter(
    component_id="duration-filter",
    label="Match Duration"
)

# Victory condition filter
create_victory_condition_filter(
    component_id="victory-filter",
    label="Victory Conditions"
)

# Complete filter sidebar
sidebar = create_filter_sidebar([
    "date_range",
    "players",
    "civilizations",
    "match_duration",
    "maps",
    "victory_conditions",
])
```

---

## 6. Styling Patterns

### 6.1 Bootstrap-Based

Using **Dash Bootstrap Components** (dbc) for grid and components:

```python
import dash_bootstrap_components as dbc

# Grid system (12 columns)
dbc.Row([
    dbc.Col([content], width=6),  # 50% width
    dbc.Col([content], width=6),  # 50% width
], className="mb-4")  # margin-bottom

# Spacing utilities
className="mt-3"       # margin-top
className="mb-4"       # margin-bottom
className="px-4"       # padding-x
className="ms-auto"    # margin-start (auto = right)
className="d-flex gap-2"  # flexbox with gap

# Colors
color="primary", color="success", color="warning", color="danger"
className="text-primary", "text-muted", "text-center"
className="bg-light"

# Typography
className="h1", "h2", "h3", "h4", "h5", "h6"
className="fw-bold", "fw-light"
className="fs-1"  # font-size 1

# Visibility
className="d-none"  # display: none
style={"display": "none"}  # Alternative

# Alignment
className="text-center", "text-start", "text-end"
className="align-items-center", "justify-content-between"
```

### 6.2 Custom CSS (style.css)

460 lines of custom CSS for additional styling:

**Key Custom Classes**:
- `.filter-sidebar` - sticky sidebar styling
- `.page-header` - page title section
- `.empty-state` - no-data placeholder
- `.card` - custom card styles with hover effects
- `.metric-card` - KPI display styling
- `.chart-container` - chart wrapper
- `.civilization-badge` - small badge for civs
- `.winner-highlight` - highlight winner row

**CSS Variables**:
```css
:root {
    --primary-color: #0d6efd;
    --secondary-color: #6c757d;
    --success-color: #198754;
    --sidebar-width: 250px;
    --navbar-height: 60px;
    --border-radius: 0.375rem;
    --transition: all 0.15s ease-in-out;
}
```

**Card Hover Effects**:
```css
.card:hover {
    box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
    transform: translateY(-2px);  /* Lift effect */
}
```

**Responsive Design**:
- Tablet (≤768px): Filter sidebar changes from sticky to static
- Mobile (≤576px): Smaller font sizes, reduced padding
- Print media: Hides navbars, buttons; adds borders

**Dark Mode Support**:
```css
@media (prefers-color-scheme: dark) {
    /* Dark theme colors */
}
```

### 6.3 Bootstrap Icons

Using **Bootstrap Icons** (bi) library:

```python
html.I(className="bi bi-bar-chart")         # Chart icon
html.I(className="bi bi-people")            # People icon
html.I(className="bi bi-trophy")            # Trophy icon
html.I(className="bi bi-map")               # Map icon
html.I(className="bi bi-info-circle")       # Info icon
html.I(className="bi bi-check-circle")      # Checkmark icon
html.I(className="bi bi-exclamation-triangle")  # Warning icon
html.I(className="bi bi-funnel")            # Filter icon
html.I(className="bi bi-download")          # Download icon
html.I(className="bi bi-gear")              # Settings icon
html.I(className="bi bi-link")              # Link icon
html.I(className="bi bi-arrow-clockwise")   # Refresh icon
```

---

## 7. Configuration & Styling Defaults

### config.py

```python
# Chart defaults
Config.CHART_HEIGHT = 400
Config.CHART_MARGIN = {"l": 50, "r": 50, "t": 50, "b": 50}
Config.MAX_CHART_POINTS = 1000

# Colors
Config.PRIMARY_COLORS = ["#1f77b4", "#ff7f0e", ...]  # Plotly defaults
Config.CIVILIZATION_COLORS = {
    "Rome": "#dc143c",
    "Egypt": "#ffd700",
    ...
}

# Modebar config (Plotly toolbar)
MODEBAR_CONFIG = {
    "displayModeBar": "hover",  # Show only on hover
    "displaylogo": False,
    "modeBarButtonsToRemove": [
        "pan2d", "select2d", "lasso2d",  # Remove most buttons
        "toImage",  # Don't save as image
    ],
}

# Layout constants
LAYOUT_CONSTANTS = {
    "SIDEBAR_WIDTH": "250px",
    "CONTENT_PADDING": "20px",
    "TABLE_PAGE_SIZE": 20,
}

# Filter options
FILTER_OPTIONS = {
    "date_ranges": [
        {"label": "Last 7 days", "value": 7},
        {"label": "All time", "value": "all"},
    ],
    ...
}

# Page metadata
PAGE_CONFIG = {
    "overview": {"title": "Tournament Overview", "description": "..."},
    "matches": {"title": "Match Analysis", ...},
    ...
}
```

---

## 8. Key Conventions & Best Practices

### Navigation & App Structure

1. **Multi-page with Dash**:
   - `dash.register_page(__name__, path="/", name="Overview")`
   - Auto-discovery of pages/ directory
   - `dash.page_container` in app layout

2. **Page Header**:
   - Always use `create_page_header()` for consistency
   - Includes title, description, optional actions

3. **Breadcrumb Navigation**:
   - Used on match detail pages
   - Shows: Home > Matches > Match ID

### Chart Conventions

1. **No Chart Titles** - Card headers provide context (per CLAUDE.md)
2. **Empty State Handling** - Always check `if df.empty`
3. **Error Handling** - Show `create_empty_chart_placeholder()` on error
4. **Loading Spinners** - Use `dcc.Loading()` wrapper for async data
5. **Color Consistency** - Use config colors, not hardcoded hex values

### Data Flow

```
Page Layout (static HTML)
    ↓
User interaction (dropdown change, button click)
    ↓
Callback triggered (Input)
    ↓
Get data from queries.py (queries = get_queries())
    ↓
Process/filter data
    ↓
Pass to chart/layout function
    ↓
Return to component (Output)
    ↓
Browser renders updated content
```

### Error Handling Pattern

```python
try:
    queries = get_queries()
    df = queries.get_data()
    
    if df.empty:
        return create_empty_chart_placeholder("No data available")
    
    return create_chart(df)

except Exception as e:
    logger.error(f"Error loading chart: {e}")
    return create_empty_chart_placeholder(f"Error: {str(e)}")
```

### Performance Considerations

1. **Lazy Loading**: Use `prevent_initial_call=True` when callback not needed on page load
2. **Pagination**: Data tables use `page_size=20` (configurable)
3. **Caching**: `Config.CACHE_TIMEOUT = 300` (development) or `3600` (production)
4. **Chart Limits**: `MAX_CHART_POINTS = 1000` to avoid performance issues

---

## 9. Special Features

### 9.1 Database Status Badge

Global app callback showing match count and connection status:

```python
@callback(
    Output("db-status-badge", "children"),
    Output("db-status-badge", "color"),
    Input("refresh-interval", "n_intervals"),
)
def update_database_status(n_intervals):
    # Updates every minute
```

### 9.2 Periodic Refresh

```python
dcc.Interval(
    id="refresh-interval",
    interval=60 * 1000,  # 60 seconds
    n_intervals=0,
    disabled=False,
)
```

All chart callbacks listen to `refresh-interval` to auto-update.

### 9.3 URL Query Parameters

Match page supports `?match_id=123` to deep-link specific matches:

```python
dcc.Location(id="match-url", refresh=False)

@callback(
    [Output("selector", "value"), Output("url", "search")],
    [Input("url", "search"), Input("selector", "value")],
)
def sync_selection(url_search, value):
    # Parse ?match_id=123 from URL
    # Keep selector and URL in sync
```

---

## 10. Chart Gallery

**Overview Page Charts** (50+ total):
- Nation Win/Loss/Popularity (pie charts)
- Counter-Pick Effectiveness (heatmap)
- Pick Order Win Rate (grouped bars)
- Ruler Archetype Performance (dual-axis)
- Ruler Trait Performance (dual-axis)
- Archetype Matchup Matrix (heatmap)
- Popular Combinations (horizontal bar)
- Event Category Timeline (stacked area)
- Unit Popularity (sunburst)
- Map Breakdown (sunburst)
- Science Progression (line with percentile band)
- Orders Progression (line with percentile band)
- Military Score Progression (line with percentile band)
- Legitimacy Progression (line with percentile band)
- Law Timing Distribution (box plot)
- Law Progression Efficiency (scatter)

**Match Detail Page Charts**:
- Event Timeline (categorized by type)
- Yield History (multiple line charts)
- Territory Control (stacked area)
- Cumulative City Count (line)
- Cumulative Law Count (line)
- Cumulative Tech Count (line)
- Law Adoption Timeline (timeline)
- Tech Completion Timeline (timeline)
- Ambition Timeline (bar)

**Player & Map Pages**:
- Head-to-Head (pie chart)
- Map Length by Settings (grouped bars)

---

## 11. File Structure Reference

### Import Patterns

```python
# For layouts
from tournament_visualizer.components.layouts import (
    create_chart_card,
    create_metric_card,
    create_page_header,
)

# For charts
from tournament_visualizer.components.charts import (
    create_nation_win_percentage_chart,
    create_empty_chart_placeholder,
)

# For filters
from tournament_visualizer.components.filters import (
    create_player_filter,
    apply_filters_to_dataframe,
)

# For queries
from tournament_visualizer.data.queries import get_queries

# For config
from tournament_visualizer.config import (
    PAGE_CONFIG,
    MODEBAR_CONFIG,
    Config,
)
```

### Component IDs Naming Convention

```
{page}-{component}-{type}
{page}-{component}-{section}

Examples:
"match-selector"           # dropdown on matches page
"overview-nation-win-chart"  # chart on overview
"player1-selector"         # first player selector
"h2h-results-section"      # head-to-head results container
"map-stats-table"          # data table on maps page
```

---

## 12. Future Enhancement Points

1. **Component Library**: Extract more complex components (chart + filter combos)
2. **Theming**: Implement dark mode toggle
3. **Mobile Optimization**: Improve mobile responsiveness
4. **Accessibility**: Add ARIA labels, keyboard navigation
5. **Performance**: Cache more heavily, implement virtual scrolling for large tables
6. **Testing**: Add Dash test callback testing

