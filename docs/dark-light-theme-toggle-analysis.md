# Dark/Light Theme Toggle Implementation Analysis

## Executive Summary

This document provides a precise implementation plan for adding a theme toggle between the current dark theme and a new light theme. The approach uses CSS custom properties with a page refresh model for chart updates, avoiding complex real-time re-rendering.

**Scope**: ~9 files, ~15 hours estimated effort

---

## Dark Theme Implementation History

The current dark theme was implemented across three commits:

| Commit | Description | Scope |
|--------|-------------|-------|
| `45bffa6` | feat: Add dark blue theme to dashboard | 10 files, +978/-315 |
| `e79ab4c` | test: Add unit tests for dark theme components | 4 files, +262 |
| `eebdf22` | docs: Add color scheme reference and theme conversion plan | 2 files, +501 |

These commits represent the baseline dark theme that this toggle implementation will build upon. The light theme toggle will restore the ability to use a light color scheme similar to the pre-`45bffa6` state while maintaining all architectural improvements made in the dark theme work.

**Reference**: To view the original light theme state, use `git show 45bffa6^:tournament_visualizer/` to see files before the dark theme conversion.

---

## Current State Inventory

### Files Modified for Dark Theme

| File | Purpose | Theme-Relevant Changes |
|------|---------|------------------------|
| `tournament_visualizer/theme.py` | Theme constants | `DARK_THEME`, `CHART_THEME` dicts |
| `tournament_visualizer/config.py` | App config | `PRIMARY_COLORS`, `DEFAULT_CHART_LAYOUT` |
| `tournament_visualizer/app.py` | Dash app | `index_string` CSS overrides, `data-bs-theme="dark"` |
| `tournament_visualizer/assets/style.css` | Main CSS | CSS variables, component styles |
| `tournament_visualizer/components/charts.py` | Chart creation | `apply_dark_theme()`, `CHART_THEME` usage |
| `tournament_visualizer/components/layouts.py` | UI components | DataTable inline styles |
| `tournament_visualizer/nation_colors.py` | Nation colors | Carthage color for dark bg |
| `tournament_visualizer/pages/matches.py` | Match page | Nation colors for charts |
| `tournament_visualizer/pages/overview.py` | Overview page | Filter button text class |

---

## Color Palette Specification

### Dark Theme (Current)

```
Background Hierarchy:
  bg-darkest:   #0e1b2e  (body background)
  bg-dark:      #364c6b  (cards, containers, chart backgrounds)
  bg-medium:    #3a5a7e  (inputs, headers, card caps)
  bg-light:     #45678e  (hover states, filter inputs)
  bg-highlight: #507498  (active states)

Text Hierarchy:
  text-primary:   #edf2f7  (main text, headings)
  text-secondary: #c8d4e3  (secondary text, links)
  text-muted:     #9db0c9  (placeholder, disabled)

Accents:
  accent-primary: #64b5f6  (primary actions, focus rings)
  accent-info:    #4dd0e1  (info elements)
  accent-success: #4aba6e  (success, positive)
  accent-warning: #ffb74d  (warnings)
  accent-danger:  #ef5350  (errors, destructive)

Borders:
  border-subtle:  rgba(255, 255, 255, 0.12)
  border-default: rgba(255, 255, 255, 0.18)

Shadows:
  shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.2)
  shadow-md: 0 4px 8px rgba(0, 0, 0, 0.3)
```

### Light Theme (Proposed)

```
Background Hierarchy:
  bg-darkest:   #f8f9fa  (body background - Bootstrap light gray)
  bg-dark:      #ffffff  (cards, containers, chart backgrounds)
  bg-medium:    #e9ecef  (inputs, headers, card caps)
  bg-light:     #dee2e6  (hover states, filter inputs)
  bg-highlight: #ced4da  (active states)

Text Hierarchy:
  text-primary:   #212529  (main text, headings - Bootstrap dark)
  text-secondary: #495057  (secondary text)
  text-muted:     #6c757d  (placeholder, disabled - Bootstrap muted)

Accents:
  accent-primary: #0d6efd  (Bootstrap primary blue)
  accent-info:    #0dcaf0  (Bootstrap info cyan)
  accent-success: #198754  (Bootstrap success green)
  accent-warning: #ffc107  (Bootstrap warning yellow)
  accent-danger:  #dc3545  (Bootstrap danger red)

Borders:
  border-subtle:  rgba(0, 0, 0, 0.08)
  border-default: rgba(0, 0, 0, 0.125)

Shadows:
  shadow-sm: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075)
  shadow-md: 0 0.5rem 1rem rgba(0, 0, 0, 0.15)
```

### Chart-Specific Colors

| Property | Dark Theme | Light Theme |
|----------|------------|-------------|
| `paper_bgcolor` | `#364c6b` | `#ffffff` |
| `plot_bgcolor` | `#364c6b` | `#ffffff` |
| `font_color` | `#edf2f7` | `#212529` |
| `text_muted` | `#9db0c9` | `#6c757d` |
| `gridcolor` | `rgba(255,255,255,0.1)` | `rgba(0,0,0,0.1)` |
| `legend_bgcolor` | `rgba(58,90,126,0.9)` | `rgba(255,255,255,0.9)` |
| `legend_bordercolor` | `rgba(255,255,255,0.1)` | `rgba(0,0,0,0.1)` |
| `hoverlabel_bgcolor` | `#3a5a7e` | `#ffffff` |
| `hoverlabel_bordercolor` | `#45678e` | `#dee2e6` |
| `hoverlabel_font_color` | `#edf2f7` | `#212529` |

### PRIMARY_COLORS by Theme

| Index | Dark Theme | Light Theme | Purpose |
|-------|------------|-------------|---------|
| 0 | `#4aba6e` (green) | `#1f77b4` (blue) | Primary series |
| 1 | `#ff7f0e` (orange) | `#ff7f0e` (orange) | Secondary series |
| 2 | `#64b5f6` (light blue) | `#2ca02c` (green) | Tertiary series |
| 3 | `#d62728` (red) | `#d62728` (red) | Quaternary series |
| 4-9 | (unchanged) | (unchanged) | Additional series |

**Rationale**: Dark theme uses green first to avoid blue-on-blue clash with dark blue backgrounds. Light theme reverts to traditional blue-first (Plotly default).

### Nation Colors

| Nation | Dark Theme | Light Theme | Notes |
|--------|------------|-------------|-------|
| Carthage | `#F6EFE1` (off-white) | `#1a1a1a` (near-black) | Visibility on backgrounds |
| All others | (unchanged) | (unchanged) | Work on both backgrounds |

---

## Architecture Design

### Theme State Management

```
┌─────────────────────────────────────────────────────────────┐
│                      Browser Storage                         │
│  localStorage.setItem('theme', 'dark' | 'light')            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    dcc.Store (Dash)                          │
│  id="theme-store", data={'theme': 'dark' | 'light'}         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Theme Resolution                          │
│  1. Check dcc.Store (session state)                         │
│  2. Fallback to localStorage (persistence)                   │
│  3. Fallback to 'dark' (default)                            │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────────┐
│      CSS Layer          │     │      Python Layer           │
│  data-bs-theme attr     │     │  get_current_theme()        │
│  CSS custom properties  │     │  CHART_THEME selection      │
└─────────────────────────┘     └─────────────────────────────┘
```

### Theme Toggle Flow

1. User clicks theme toggle button in navbar
2. Clientside callback updates `dcc.Store` and `localStorage`
3. Clientside callback sets `document.documentElement.dataset.bsTheme`
4. Page refreshes (or navigation triggers re-render)
5. Server reads theme from cookie/store, generates charts with correct theme
6. CSS applies based on `data-bs-theme` attribute

---

## Implementation Details by File

### 1. `tournament_visualizer/theme.py`

**Current State**: Single `DARK_THEME` and `CHART_THEME` dict.

**Required Changes**:

```python
# Add LIGHT_THEME dict
LIGHT_THEME: ThemeColors = {
    "bg_darkest": "#f8f9fa",
    "bg_dark": "#ffffff",
    "bg_medium": "#e9ecef",
    "bg_light": "#dee2e6",
    "text_primary": "#212529",
    "text_secondary": "#495057",
    "text_muted": "#6c757d",
    "accent_primary": "#0d6efd",
    "accent_info": "#0dcaf0",
    "accent_success": "#198754",
    "accent_warning": "#ffc107",
    "accent_danger": "#dc3545",
}

LIGHT_CHART_THEME = {
    "paper_bgcolor": "#ffffff",
    "plot_bgcolor": "#ffffff",
    "font_color": "#212529",
    "text_muted": "#6c757d",
    "gridcolor": "rgba(0, 0, 0, 0.1)",
    "legend_bgcolor": "rgba(255, 255, 255, 0.9)",
    "legend_bordercolor": "rgba(0, 0, 0, 0.1)",
    "hoverlabel_bgcolor": "#ffffff",
    "hoverlabel_bordercolor": "#dee2e6",
    "hoverlabel_font_color": "#212529",
}

# Theme accessor functions
_current_theme = "dark"  # Module-level state

def set_current_theme(theme: str) -> None:
    global _current_theme
    _current_theme = theme

def get_current_theme() -> str:
    return _current_theme

def get_theme_colors() -> ThemeColors:
    return DARK_THEME if _current_theme == "dark" else LIGHT_THEME

def get_chart_theme() -> dict:
    return CHART_THEME if _current_theme == "dark" else LIGHT_CHART_THEME
```

**Critical**: All existing `CHART_THEME` references must be updated to `get_chart_theme()` calls.

---

### 2. `tournament_visualizer/config.py`

**Current State**: `PRIMARY_COLORS` is hardcoded, `DEFAULT_CHART_LAYOUT` imports from theme.

**Required Changes**:

```python
# Replace static PRIMARY_COLORS with theme-aware function
def get_primary_colors() -> list[str]:
    from tournament_visualizer.theme import get_current_theme
    if get_current_theme() == "dark":
        return [
            "#4aba6e",  # Green first for dark theme
            "#ff7f0e", "#64b5f6", "#d62728", "#9467bd",
            "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#4dd0e1",
        ]
    else:
        return [
            "#1f77b4",  # Blue first for light theme (Plotly default)
            "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
            "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
        ]

# DEFAULT_CHART_LAYOUT must become a function
def get_default_chart_layout() -> dict:
    from tournament_visualizer.theme import get_chart_theme
    chart_theme = get_chart_theme()
    return {
        "margin": Config.CHART_MARGIN,
        "height": Config.CHART_HEIGHT,
        "showlegend": True,
        "legend": {
            "x": 0, "y": 1,
            "bgcolor": chart_theme["legend_bgcolor"],
            "bordercolor": chart_theme["legend_bordercolor"],
            "borderwidth": 1,
            "font": {"color": chart_theme["font_color"]},
        },
        "font": {"size": 12, "color": chart_theme["font_color"]},
        "plot_bgcolor": chart_theme["plot_bgcolor"],
        "paper_bgcolor": chart_theme["paper_bgcolor"],
        "hoverlabel": {
            "bgcolor": chart_theme["hoverlabel_bgcolor"],
            "bordercolor": chart_theme["hoverlabel_bordercolor"],
            "font": {"color": chart_theme["hoverlabel_font_color"]},
        },
        "xaxis": {
            "gridcolor": chart_theme["gridcolor"],
            "tickfont": {"color": chart_theme["font_color"]},
            "title_font": {"color": chart_theme["font_color"]},
        },
        "yaxis": {
            "gridcolor": chart_theme["gridcolor"],
            "tickfont": {"color": chart_theme["font_color"]},
            "title_font": {"color": chart_theme["font_color"]},
        },
    }
```

**Breaking Change**: All imports of `DEFAULT_CHART_LAYOUT` and `PRIMARY_COLORS` must change to function calls.

---

### 3. `tournament_visualizer/app.py`

**Current State**:
- `data-bs-theme="dark"` hardcoded in `index_string`
- CSS overrides in `<style>` block target dark theme only

**Required Changes**:

#### 3.1 Dynamic `index_string`

The `index_string` cannot be dynamically generated per-request in Dash. Instead:

1. Keep `data-bs-theme="dark"` as default
2. Add clientside JavaScript to read theme from localStorage and apply immediately
3. Add CSS for both themes

```python
app.index_string = """<!DOCTYPE html>
<html data-bs-theme="dark">
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <script>
            // Apply theme immediately to prevent flash
            (function() {
                var theme = localStorage.getItem('theme') || 'dark';
                document.documentElement.setAttribute('data-bs-theme', theme);
            })();
        </script>
        <style>
            /* ===== DARK THEME ===== */
            [data-bs-theme=dark] {
                --bs-body-bg: #0e1b2e;
                --bs-body-color: #edf2f7;
                --bs-secondary-bg: #364c6b;
                --bs-tertiary-bg: #3a5a7e;
                --bs-card-bg: #364c6b;
                --bs-card-cap-bg: #3a5a7e;
                --bs-modal-bg: #364c6b;
                --bs-dropdown-bg: #3a5a7e;
                --bs-border-color: rgba(255, 255, 255, 0.18);
                --bs-link-color: #c8d4e3;
                --bs-link-hover-color: #ffffff;
            }
            [data-bs-theme=dark] body {
                background-color: #0e1b2e !important;
            }
            [data-bs-theme=dark] .navbar {
                background-color: #3b4c69 !important;
            }
            /* ... rest of dark theme overrides ... */

            /* ===== LIGHT THEME ===== */
            [data-bs-theme=light] {
                --bs-body-bg: #f8f9fa;
                --bs-body-color: #212529;
                --bs-secondary-bg: #ffffff;
                --bs-tertiary-bg: #e9ecef;
                --bs-card-bg: #ffffff;
                --bs-card-cap-bg: #e9ecef;
                --bs-modal-bg: #ffffff;
                --bs-dropdown-bg: #ffffff;
                --bs-border-color: rgba(0, 0, 0, 0.125);
                --bs-link-color: #0d6efd;
                --bs-link-hover-color: #0a58ca;
            }
            [data-bs-theme=light] body {
                background-color: #f8f9fa !important;
            }
            [data-bs-theme=light] .navbar {
                background-color: #e9ecef !important;
            }
            /* ... rest of light theme overrides ... */
        </style>
    </head>
    ...
</html>"""
```

#### 3.2 Theme Toggle UI Component

Add to navbar in `app.layout`:

```python
dbc.NavItem(
    dbc.Button(
        html.I(id="theme-toggle-icon", className="bi bi-moon-fill"),
        id="theme-toggle-btn",
        color="link",
        className="nav-link",
    )
),
```

#### 3.3 Theme Store and Callbacks

```python
# Add to layout
dcc.Store(id="theme-store", storage_type="local"),

# Clientside callback for instant theme switching
app.clientside_callback(
    """
    function(n_clicks, current_theme) {
        if (n_clicks === undefined) {
            // Initial load - read from localStorage
            var stored = localStorage.getItem('theme') || 'dark';
            document.documentElement.setAttribute('data-bs-theme', stored);
            return stored;
        }
        // Toggle theme
        var new_theme = current_theme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-bs-theme', new_theme);
        localStorage.setItem('theme', new_theme);
        // Refresh page to re-render charts with new theme
        window.location.reload();
        return new_theme;
    }
    """,
    Output("theme-store", "data"),
    Input("theme-toggle-btn", "n_clicks"),
    State("theme-store", "data"),
    prevent_initial_call=False,
)

# Update icon based on theme
app.clientside_callback(
    """
    function(theme) {
        return theme === 'dark' ? 'bi bi-moon-fill' : 'bi bi-sun-fill';
    }
    """,
    Output("theme-toggle-icon", "className"),
    Input("theme-store", "data"),
)
```

#### 3.4 Server-Side Theme Detection

Add early in `app.py` (before chart generation):

```python
from flask import request

def get_theme_from_request() -> str:
    """Get theme from cookie or default to dark."""
    # localStorage isn't accessible server-side, use cookie set by JS
    return request.cookies.get('theme', 'dark')

# Hook into request handling to set theme
@app.server.before_request
def set_theme_for_request():
    from tournament_visualizer.theme import set_current_theme
    theme = get_theme_from_request()
    set_current_theme(theme)
```

Update clientside callback to also set cookie:

```javascript
document.cookie = 'theme=' + new_theme + ';path=/;max-age=31536000';
```

---

### 4. `tournament_visualizer/assets/style.css`

**Current State**: CSS variables defined for dark theme only, many hardcoded colors.

**Required Changes**:

The CSS should be restructured to use theme-agnostic variable names that are defined differently per theme:

```css
/* Theme-agnostic variables (values set by data-bs-theme) */
:root {
    /* These are overridden by [data-bs-theme] selectors in app.py */
    --tv-bg-body: var(--bs-body-bg);
    --tv-bg-card: var(--bs-card-bg);
    --tv-bg-input: var(--bs-tertiary-bg);
    --tv-text-primary: var(--bs-body-color);
    --tv-text-muted: var(--bs-secondary-color);
    --tv-border-color: var(--bs-border-color);
    --tv-shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.1);
}

/* Component styles use theme-agnostic variables */
.card {
    background-color: var(--tv-bg-card);
    border-color: var(--tv-border-color);
    color: var(--tv-text-primary);
}

.form-control, .form-select {
    background-color: var(--tv-bg-input);
    border-color: var(--tv-border-color);
    color: var(--tv-text-primary);
}
```

**Full audit required**: Every color value in `style.css` must be checked and converted to use variables.

---

### 5. `tournament_visualizer/components/charts.py`

**Current State**:
- Imports `CHART_THEME` directly
- `apply_dark_theme()` function uses `CHART_THEME`
- `create_base_figure()` uses `DEFAULT_CHART_LAYOUT`
- Multiple chart functions reference `CHART_THEME` directly

**Required Changes**:

#### 5.1 Update Imports

```python
# OLD
from ..theme import CHART_THEME

# NEW
from ..theme import get_chart_theme
```

#### 5.2 Update All CHART_THEME References

Search and replace pattern (with function call at usage site):

```python
# OLD
fig.update_layout(paper_bgcolor=CHART_THEME["paper_bgcolor"])

# NEW
chart_theme = get_chart_theme()
fig.update_layout(paper_bgcolor=chart_theme["paper_bgcolor"])
```

#### 5.3 Audit of CHART_THEME Usage Locations

Based on git diff, these functions reference `CHART_THEME`:

| Function | Line (approx) | Usage |
|----------|---------------|-------|
| `apply_dark_theme()` | 25 | 8 references |
| `create_base_figure()` | 71 | Via DEFAULT_CHART_LAYOUT |
| `create_empty_chart_placeholder()` | 666 | 3 references |
| `create_statistics_radar_chart()` | 1002 | 2 references |
| `create_unit_popularity_sunburst_chart()` | 1641-1702 | 2 references |
| `create_match_yield_stacked_chart()` | 2995-3068 | 2 references |
| `create_map_breakdown_actual_sunburst_chart()` | 3224 | 2 references |
| `create_map_breakdown_parallel_categories_chart()` | 3279 | 2 references |
| `create_ambition_timeline_chart()` | 3385-3515 | 3 references |
| `create_ambition_summary_table()` | 3560-3586 | 6 references |

**Total**: ~30 direct `CHART_THEME` references to update.

#### 5.4 Rename `apply_dark_theme()` to `apply_chart_theme()`

The function should be theme-agnostic:

```python
def apply_chart_theme(fig: go.Figure) -> go.Figure:
    """Apply current theme to any figure (especially subplots)."""
    chart_theme = get_chart_theme()
    fig.update_layout(
        paper_bgcolor=chart_theme["paper_bgcolor"],
        plot_bgcolor=chart_theme["plot_bgcolor"],
        font=dict(color=chart_theme["font_color"]),
        hoverlabel=dict(
            bgcolor=chart_theme["hoverlabel_bgcolor"],
            bordercolor=chart_theme["hoverlabel_bordercolor"],
            font=dict(color=chart_theme["hoverlabel_font_color"]),
        ),
    )
    fig.update_xaxes(
        gridcolor=chart_theme["gridcolor"],
        tickfont=dict(color=chart_theme["font_color"]),
        title_font=dict(color=chart_theme["font_color"]),
    )
    fig.update_yaxes(
        gridcolor=chart_theme["gridcolor"],
        tickfont=dict(color=chart_theme["font_color"]),
        title_font=dict(color=chart_theme["font_color"]),
    )
    return fig
```

---

### 6. `tournament_visualizer/components/layouts.py`

**Current State**: DataTable styles use `DARK_THEME` dict directly.

**Required Changes**:

```python
# OLD
from ..theme import DARK_THEME

# NEW
from ..theme import get_theme_colors

def create_data_table_card(...):
    theme = get_theme_colors()
    return dbc.Card([
        ...
        dash_table.DataTable(
            style_cell={
                "backgroundColor": theme["bg_dark"],
                "color": theme["text_primary"],
                "border": f"1px solid {theme['bg_light']}",
            },
            style_header={
                "backgroundColor": theme["bg_medium"],
                "color": theme["text_primary"],
            },
            style_data_conditional=[
                {
                    "if": {"row_index": "odd"},
                    "backgroundColor": theme["bg_medium"],
                },
            ],
            style_filter={
                "backgroundColor": theme["bg_light"],
                "color": theme["text_primary"],
            },
        ),
    ])
```

---

### 7. `tournament_visualizer/nation_colors.py`

**Current State**: Carthage is `#F6EFE1` (off-white) for dark background visibility.

**Required Changes**:

```python
def get_nation_color(nation_name: str) -> str:
    """Get the color for a nation, adjusted for current theme."""
    from tournament_visualizer.theme import get_current_theme

    name_upper = nation_name.upper()

    # Carthage needs different colors for visibility
    if name_upper == "CARTHAGE":
        return "#F6EFE1" if get_current_theme() == "dark" else "#1a1a1a"

    return NATION_COLORS.get(name_upper, "#808080")
```

---

### 8. `tournament_visualizer/pages/overview.py`

**Current State**: Filter toggle button has `text-light` class.

**Required Changes**:

The button should adapt to theme. Options:

**Option A**: Use Bootstrap's theme-aware classes
```python
className="text-decoration-none text-body fw-bold w-100 text-start p-0"
```
(`text-body` adapts to theme automatically)

**Option B**: Use custom CSS class
```python
className="text-decoration-none filter-toggle-text fw-bold w-100 text-start p-0"
```
```css
[data-bs-theme=dark] .filter-toggle-text { color: #edf2f7; }
[data-bs-theme=light] .filter-toggle-text { color: #212529; }
```

---

### 9. `tournament_visualizer/pages/matches.py`

**Current State**: Uses `get_player_colors_for_match()` which calls `get_nation_color()`.

**Required Changes**: None directly, but depends on `nation_colors.py` changes propagating correctly.

---

## CSS Override Audit

The following CSS overrides in `app.py` `index_string` need light theme equivalents:

| Selector | Dark Value | Light Value |
|----------|------------|-------------|
| `body` background | `#0e1b2e` | `#f8f9fa` |
| `.navbar` background | `#3b4c69` | `#e9ecef` |
| `.dash-table-container a` color | `#c8d4e3` | `#0d6efd` |
| `.dash-table-container a:hover` color | `#ffffff` | `#0a58ca` |
| `th.dash-filter input --bs-body-bg` | `#41597b` | `#ffffff` |
| `th.dash-filter input` background | `#41597b` | `#ffffff` |
| `th.dash-filter input` color | `#edf2f7` | `#212529` |
| `th.dash-filter input::placeholder` color | `#c8d4e3` | `#6c757d` |
| `.column-header--sort` color | `#edf2f7` | `#212529` |
| `.btn-outline-primary` border/color | `#c8d4e3` | `#0d6efd` |
| `.btn-outline-primary:hover` background | `#c8d4e3` | `#0d6efd` |
| `.btn-outline-primary:hover` color | `#0e1b2e` | `#ffffff` |
| `.modebar-btn path` fill | `#c8d4e3` | `#6c757d` |
| `.modebar-btn:hover path` fill | `#ffffff` | `#212529` |

---

## Implementation Order

### Phase 1: Theme Infrastructure (2-3 hours)

1. Update `theme.py` with `LIGHT_THEME`, `LIGHT_CHART_THEME`, accessor functions
2. Update `config.py` with `get_primary_colors()`, `get_default_chart_layout()`
3. Add theme store and toggle UI to `app.py`
4. Add server-side theme detection via cookie

### Phase 2: Chart System Updates (4-5 hours)

1. Update all `CHART_THEME` imports in `charts.py` to use `get_chart_theme()`
2. Rename `apply_dark_theme()` to `apply_chart_theme()`
3. Update `layouts.py` DataTable styles to use `get_theme_colors()`
4. Update `nation_colors.py` for Carthage theme awareness
5. Test all chart types render correctly in both themes

### Phase 3: CSS Dual-Theme Support (4-5 hours)

1. Restructure `style.css` to use theme-agnostic variable names
2. Add `[data-bs-theme=light]` equivalents for all dark theme overrides in `app.py`
3. Update `overview.py` filter button to use theme-aware class
4. Full visual audit of all pages in both themes

### Phase 4: Polish & Testing (2-3 hours)

1. Test theme persistence across page navigation
2. Test theme persistence across browser sessions
3. Verify no flash of wrong theme on page load
4. Test all interactive elements (dropdowns, modals, tooltips)
5. Test all chart types for readability

---

## Testing Checklist

### Pages to Test

- [ ] Overview (all 4 tabs)
- [ ] Matches (all tabs: Info, Progression, Timeline, Territory, Units)
- [ ] Players
- [ ] Maps

### Components to Test

- [ ] Navbar (background, text, dropdown)
- [ ] Cards (background, headers, borders)
- [ ] DataTables (headers, rows, filters, sort indicators, links)
- [ ] Dropdowns (background, text, options, selected state)
- [ ] Buttons (primary, outline, link)
- [ ] Modals (background, text, buttons)
- [ ] Alerts
- [ ] Badges
- [ ] Tabs

### Charts to Test

- [ ] Bar charts (horizontal, vertical, stacked, grouped)
- [ ] Line charts (single, multi-series)
- [ ] Pie/Donut charts
- [ ] Scatter plots
- [ ] Heatmaps
- [ ] Radar charts
- [ ] Sunburst charts
- [ ] Treemaps
- [ ] Timeline charts
- [ ] Tables (Plotly go.Table)

### Chart Elements to Verify

- [ ] Background colors (paper, plot)
- [ ] Text colors (titles, labels, tick marks)
- [ ] Grid lines
- [ ] Legend (background, border, text)
- [ ] Hover tooltips (background, border, text)
- [ ] Modebar icons (zoom in/out buttons)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Missed hardcoded color | High | Medium | Grep for hex codes, visual testing |
| Flash of wrong theme | Medium | Low | Inline JS in `<head>` before CSS |
| Chart theme mismatch | Medium | High | Centralize all theme access through functions |
| Cookie/localStorage desync | Low | Low | Single source of truth (localStorage), cookie mirrors |
| Performance impact | Low | Low | Theme functions called once per request |

---

## Files Modified Summary

| File | Type of Change |
|------|---------------|
| `theme.py` | Add light theme, accessor functions |
| `config.py` | Convert constants to functions |
| `app.py` | Dual-theme CSS, toggle UI, theme detection |
| `style.css` | Theme-agnostic variables |
| `charts.py` | ~30 function call updates |
| `layouts.py` | Dynamic theme colors |
| `nation_colors.py` | Theme-aware Carthage |
| `overview.py` | Theme-aware button class |

---

## Appendix: Grep Commands for Audit

```bash
# Find all CHART_THEME references
grep -n "CHART_THEME" tournament_visualizer/**/*.py

# Find all DARK_THEME references
grep -n "DARK_THEME" tournament_visualizer/**/*.py

# Find all hardcoded hex colors in Python
grep -rn "#[0-9a-fA-F]\{6\}" tournament_visualizer/**/*.py

# Find all hardcoded hex colors in CSS
grep -n "#[0-9a-fA-F]\{6\}" tournament_visualizer/assets/style.css

# Find all rgba colors
grep -rn "rgba(" tournament_visualizer/

# Find PRIMARY_COLORS usage
grep -rn "PRIMARY_COLORS" tournament_visualizer/

# Find DEFAULT_CHART_LAYOUT usage
grep -rn "DEFAULT_CHART_LAYOUT" tournament_visualizer/
```
