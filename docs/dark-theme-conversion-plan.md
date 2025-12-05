# Dark Theme Conversion Plan

## Environment

- **Dash**: 3.2.0
- **dash-bootstrap-components**: 2.0.4
- **Bootstrap**: 5.3.6 (via `dbc.themes.BOOTSTRAP`)
- **React-Select**: Uses old `.Select-*` class names (not `.Select__*`)
- **dash-bootstrap-templates**: Required for styling dcc components

The `data-bs-theme="dark"` attribute is fully supported.

---

## Lessons Learned (Phase 1)

### Bootstrap CSS Override Strategy

**Problem:** CSS in `assets/` folder loads BEFORE Bootstrap's CSS, so CSS variable overrides don't take effect.

**Solution:** Use `app.index_string` with a `<style>` block placed AFTER `{%css%}`:

```python
app.index_string = """<!DOCTYPE html>
<html data-bs-theme="dark">
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            /* Override Bootstrap dark theme - loads AFTER Bootstrap */
            [data-bs-theme=dark] {
                --bs-body-bg: #26405e;
                --bs-card-bg: #2f4d6e;
                /* ... other overrides ... */
            }
            body {
                background-color: #26405e !important;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>"""
```

**Key points:**
- Set `data-bs-theme="dark"` on `<html>` element (not a wrapper div)
- Place `<style>` block AFTER `{%css%}` to ensure it loads after Bootstrap
- Use `[data-bs-theme=dark]` selector to override Bootstrap's CSS variables
- Body needs `!important` as a fallback

### Dash Core Component Styling

**Problem:** `dcc.Dropdown` and other Dash core components don't use Bootstrap styling.

**Solution:** Add `dash-bootstrap-templates` CSS and `className="dbc"`:

```python
DBC_CSS = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP, DBC_CSS],
    ...
)

app.layout = dbc.Container(
    [...],
    className="dbc px-4",  # "dbc" class enables dash-bootstrap-templates styling
)
```

---

## Color Scheme

### Dark Blue Palette (Current)

```python
DARK_THEME: ThemeColors = {
    "bg_darkest": "#26405e",  # Body background
    "bg_dark": "#2f4d6e",     # Cards, containers
    "bg_medium": "#3a5a7e",   # Inputs, headers
    "bg_light": "#45678e",    # Hover states
    "text_primary": "#edf2f7",
    "text_secondary": "#c8d4e3",
    "text_muted": "#9db0c9",
    "accent_primary": "#64b5f6",
    "accent_info": "#4dd0e1",
    "accent_success": "#4aba6e",
    "accent_warning": "#ffb74d",
    "accent_danger": "#ef5350",
}
```

---

## Phase 1: Theme Foundation and CSS [COMPLETED]

**Status:** COMPLETED

**Files Changed:**
| File | Status |
|------|--------|
| `tournament_visualizer/theme.py` | Created with dark blue palette |
| `tournament_visualizer/assets/style.css` | Updated with CSS variables and component styles |
| `tournament_visualizer/app.py` | Added `index_string`, DBC_CSS, navbar styling |
| `tests/test_theme.py` | Created with theme tests |

### What Was Implemented

1. **Created `theme.py`** with `DARK_THEME` and `CHART_THEME` dictionaries
2. **Updated `style.css`** with:
   - CSS variables for the dark blue palette
   - Bootstrap override block (backup, main override is in index_string)
   - Comprehensive component styling (cards, forms, dropdowns, modals, etc.)
3. **Updated `app.py`** with:
   - Custom `index_string` with `data-bs-theme="dark"` on `<html>`
   - Style block after `{%css%}` for Bootstrap overrides
   - `dash-bootstrap-templates` CSS from CDN
   - `className="dbc"` on container
   - Navbar with custom background color

---

## Phase 2: Chart Theming [COMPLETED]

**Status:** COMPLETED

**Affected Files:**
| File | Changes |
|------|---------|
| `tournament_visualizer/config.py` | Update `DEFAULT_CHART_LAYOUT` to use `CHART_THEME` with hoverlabel |
| `tournament_visualizer/charts.py` | Add `apply_dark_theme()`, update `create_base_figure`, `create_empty_figure`, and `make_subplots` usages |
| `tournament_visualizer/nation_colors.py` | Consolidate to single dict with off-white Carthage |

### 2.1 Update `config.py` `DEFAULT_CHART_LAYOUT`

```python
from tournament_visualizer.theme import CHART_THEME

DEFAULT_CHART_LAYOUT = {
    "margin": Config.CHART_MARGIN,
    "height": Config.CHART_HEIGHT,
    "showlegend": True,
    "legend": {
        "x": 0,
        "y": 1,
        "bgcolor": CHART_THEME["legend_bgcolor"],
        "bordercolor": CHART_THEME["legend_bordercolor"],
        "borderwidth": 1,
        "font": {"color": CHART_THEME["font_color"]},
    },
    "font": {"size": 12, "color": CHART_THEME["font_color"]},
    "plot_bgcolor": CHART_THEME["plot_bgcolor"],
    "paper_bgcolor": CHART_THEME["paper_bgcolor"],
    # Hover tooltip styling (critical - cannot be done via CSS)
    "hoverlabel": {
        "bgcolor": CHART_THEME["hoverlabel_bgcolor"],
        "bordercolor": CHART_THEME["hoverlabel_bordercolor"],
        "font": {"color": CHART_THEME["hoverlabel_font_color"]},
    },
    "xaxis": {
        "gridcolor": CHART_THEME["gridcolor"],
        "tickfont": {"color": CHART_THEME["font_color"]},
        "title_font": {"color": CHART_THEME["font_color"]},
    },
    "yaxis": {
        "gridcolor": CHART_THEME["gridcolor"],
        "tickfont": {"color": CHART_THEME["font_color"]},
        "title_font": {"color": CHART_THEME["font_color"]},
    },
}
```

### 2.2 Add `apply_dark_theme()` helper for subplots

Charts using `make_subplots()` bypass `create_base_figure()` and get white backgrounds. Add this helper in `charts.py`:

```python
from .theme import CHART_THEME

def apply_dark_theme(fig: go.Figure) -> go.Figure:
    """Apply dark theme to any figure (especially subplots).

    Use this for figures created with make_subplots() which don't go through
    create_base_figure().
    """
    fig.update_layout(
        paper_bgcolor=CHART_THEME["paper_bgcolor"],
        plot_bgcolor=CHART_THEME["plot_bgcolor"],
        font=dict(color=CHART_THEME["font_color"]),
        hoverlabel=dict(
            bgcolor=CHART_THEME["hoverlabel_bgcolor"],
            bordercolor=CHART_THEME["hoverlabel_bordercolor"],
            font=dict(color=CHART_THEME["hoverlabel_font_color"]),
        ),
    )
    # Update all axes (subplots create xaxis, xaxis2, xaxis3, etc.)
    fig.update_xaxes(
        gridcolor=CHART_THEME["gridcolor"],
        tickfont=dict(color=CHART_THEME["font_color"]),
        title_font=dict(color=CHART_THEME["font_color"]),
    )
    fig.update_yaxes(
        gridcolor=CHART_THEME["gridcolor"],
        tickfont=dict(color=CHART_THEME["font_color"]),
        title_font=dict(color=CHART_THEME["font_color"]),
    )
    return fig
```

### 2.3 Update all `make_subplots()` usages

Apply `apply_dark_theme()` after each `make_subplots()` call. Search for all usages:

```bash
grep -n "make_subplots" tournament_visualizer/charts.py
```

Example pattern:
```python
fig = make_subplots(rows=2, cols=1, ...)
fig = apply_dark_theme(fig)  # Add this line
```

### 2.4 Update `create_base_figure`

Add deep copy for nested dicts to avoid mutation:

```python
from .theme import CHART_THEME

def create_base_figure(
    title: str = "",
    height: int = None,
    show_legend: bool = True,
    x_title: str = "",
    y_title: str = "",
) -> go.Figure:
    layout = DEFAULT_CHART_LAYOUT.copy()
    # Deep copy nested dicts to avoid mutation
    layout["legend"] = DEFAULT_CHART_LAYOUT["legend"].copy()
    layout["xaxis"] = DEFAULT_CHART_LAYOUT["xaxis"].copy()
    layout["yaxis"] = DEFAULT_CHART_LAYOUT["yaxis"].copy()
    layout["hoverlabel"] = DEFAULT_CHART_LAYOUT["hoverlabel"].copy()

    layout.update({
        "title": {
            "text": title,
            "x": 0.5,
            "xanchor": "center",
            "font": {"color": CHART_THEME["font_color"]},
        },
        "showlegend": show_legend,
        "xaxis_title": x_title,
        "yaxis_title": y_title,
    })

    if height:
        layout["height"] = height

    return go.Figure(layout=layout)
```

### 2.5 Update `create_empty_figure`

```python
def create_empty_figure(message: str = "No data available") -> go.Figure:
    """Create a placeholder chart when no data is available."""
    fig = go.Figure()

    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        xanchor="center",
        yanchor="middle",
        showarrow=False,
        font=dict(size=16, color=CHART_THEME["text_muted"]),
    )

    fig.update_layout(
        paper_bgcolor=CHART_THEME["paper_bgcolor"],
        plot_bgcolor=CHART_THEME["plot_bgcolor"],
        showlegend=False,
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
    )

    return fig
```

### 2.6 Update `nation_colors.py`

Consolidate to single dict with off-white Carthage (visible on dark background):

```python
"""
Nation color mappings for consistent chart colors.
Colors from docs/reference/color-scheme.md
"""

from typing import Optional

NATION_COLORS: dict[str, str] = {
    "AKSUM": "#F8A3B4",     # Pink/Rose
    "ASSYRIA": "#FADC3B",   # Yellow
    "BABYLONIA": "#82C83E", # Green
    "CARTHAGE": "#F6EFE1",  # Off-white/Beige (visible on dark background)
    "EGYPT": "#BC6304",     # Dark Orange/Brown
    "GREECE": "#2360BC",    # Dark Blue
    "HATTI": "#80E3E8",     # Cyan
    "HITTITE": "#80E3E8",   # Cyan (alias for HATTI)
    "KUSH": "#FFFFB6",      # Light Yellow
    "PERSIA": "#C04E4A",    # Red
    "ROME": "#880D56",      # Purple/Burgundy
}

# Backwards compatibility
NATION_MAP_COLORS = NATION_COLORS
SAME_NATION_FALLBACK_COLOR = "#228B22"  # Forest Green
```

### Unit Tests

```python
# tests/test_charts.py
from tournament_visualizer.charts import (
    create_base_figure,
    create_empty_figure,
    apply_dark_theme,
)
from tournament_visualizer.theme import CHART_THEME


def test_create_base_figure_uses_dark_background():
    fig = create_base_figure()
    assert fig.layout.paper_bgcolor == CHART_THEME["paper_bgcolor"]
    assert fig.layout.plot_bgcolor == CHART_THEME["plot_bgcolor"]


def test_create_base_figure_uses_light_text():
    fig = create_base_figure()
    assert fig.layout.font.color == CHART_THEME["font_color"]


def test_create_empty_figure_uses_dark_theme():
    fig = create_empty_figure("Test message")
    assert fig.layout.paper_bgcolor == CHART_THEME["paper_bgcolor"]


def test_apply_dark_theme_to_subplots():
    from plotly.subplots import make_subplots

    fig = make_subplots(rows=2, cols=1)
    fig = apply_dark_theme(fig)
    assert fig.layout.paper_bgcolor == CHART_THEME["paper_bgcolor"]
    assert fig.layout.hoverlabel.bgcolor == CHART_THEME["hoverlabel_bgcolor"]
```

---

## Phase 3: DataTable and Component Styling

**Status:** COMPLETED

**Affected Files:**
| File | Changes |
|------|---------|
| `tournament_visualizer/layouts.py` | Update `create_data_table_card` with dark styles |

### 3.1 Update `layouts.py` `create_data_table_card`

```python
from tournament_visualizer.theme import DARK_THEME

def create_data_table_card(
    title: str, table_id: str, columns: List[Dict[str, str]], export_button: bool = True
) -> dbc.Card:
    # ... header_controls unchanged ...

    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.Div(
                        header_controls,
                        className="d-flex justify-content-between align-items-center mb-3",
                    ),
                    dash_table.DataTable(
                        id=table_id,
                        columns=columns,
                        data=[],
                        sort_action="native",
                        filter_action="native",
                        filter_options={"case": "insensitive"},
                        page_action="native",
                        page_size=LAYOUT_CONSTANTS["TABLE_PAGE_SIZE"],
                        style_table={
                            "backgroundColor": DARK_THEME["bg_dark"],
                        },
                        style_cell={
                            "textAlign": "left",
                            "padding": "10px",
                            "fontFamily": "inherit",
                            "backgroundColor": DARK_THEME["bg_dark"],
                            "color": DARK_THEME["text_primary"],
                            "border": f"1px solid {DARK_THEME['bg_light']}",
                        },
                        style_header={
                            "backgroundColor": DARK_THEME["bg_medium"],
                            "fontWeight": "bold",
                            "color": DARK_THEME["text_primary"],
                            "border": f"1px solid {DARK_THEME['bg_light']}",
                        },
                        style_data_conditional=[
                            {
                                "if": {"row_index": "odd"},
                                "backgroundColor": DARK_THEME["bg_medium"],
                            },
                            {
                                "if": {"state": "active"},
                                "backgroundColor": DARK_THEME["bg_light"],
                                "border": f"1px solid {DARK_THEME['accent_primary']}",
                            },
                        ],
                        style_filter={
                            "backgroundColor": DARK_THEME["bg_medium"],
                            "color": DARK_THEME["text_primary"],
                        },
                    ),
                ]
            )
        ],
        className="h-100",
    )
```

### Unit Tests

```python
# tests/test_layouts.py
from tournament_visualizer.layouts import create_data_table_card
from tournament_visualizer.theme import DARK_THEME


def test_data_table_card_uses_dark_colors():
    card = create_data_table_card(
        title="Test",
        table_id="test-table",
        columns=[{"name": "Col", "id": "col"}],
    )
    # Extract DataTable from card structure
    card_body = card.children[0]
    data_table = card_body.children[-1]

    assert data_table.style_cell["backgroundColor"] == DARK_THEME["bg_dark"]
    assert data_table.style_header["backgroundColor"] == DARK_THEME["bg_medium"]
```

---

## Summary

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Theme Foundation and CSS | COMPLETED |
| 2 | Chart Theming | COMPLETED |
| 3 | DataTable and Component Styling | COMPLETED |

**Key Implementation Notes:**
- Bootstrap overrides MUST be in `app.index_string` style block, not `assets/style.css`
- Use `dash-bootstrap-templates` CSS + `className="dbc"` for dcc component styling
- Chart hover labels require inline Plotly styling (cannot be done via CSS)
- `make_subplots()` figures need explicit `apply_dark_theme()` call
