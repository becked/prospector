"""Individual match analysis page.

This page provides detailed analysis of specific tournament matches including
turn progression, resource development, and event timelines.
"""

import logging
from typing import Any, Dict, List, Optional

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import dash_cytoscape as cyto
from dash import Input, Output, State, callback, dcc, html
from plotly import graph_objects as go

from tournament_visualizer.components.charts import (
    create_ambition_summary_table,
    create_ambition_timeline_chart,
    create_base_figure,
    create_city_founding_scatter_jitter_chart,
    create_cumulative_city_count_chart,
    create_cumulative_law_count_chart,
    create_cumulative_tech_count_chart,
    create_empty_chart_placeholder,
    create_improvement_butterfly_chart,
    create_law_adoption_timeline_chart,
    create_match_legitimacy_chart,
    create_military_power_chart,
    create_science_breakdown_chart,
    create_science_infrastructure_timeline,
    create_science_sources_detail_chart,
    create_specialist_butterfly_chart,
    create_tech_completion_timeline_chart,
    create_territory_control_chart,
    create_match_yield_stacked_chart,
    create_units_stacked_bar_chart,
    create_units_grouped_bar_chart,
    create_units_waffle_chart,
    create_units_treemap_chart,
    create_units_icon_grid,
    create_units_army_portrait,
    create_units_marimekko_chart,
)
from tournament_visualizer.components.layouts import (
    create_breadcrumb,
    create_chart_card,
    create_data_table_card,
    create_empty_state,
    create_metric_card,
    create_page_header,
    create_tab_layout,
)
from tournament_visualizer.config import (
    COGNOMEN_DISPLAY_NAMES,
    COGNOMEN_LEGITIMACY,
    MODEBAR_CONFIG,
    PAGE_CONFIG,
    Config,
    format_event_type_display,
    format_family_display_name,
    get_cognomen_decay_rate,
    get_family_class,
)
from tournament_visualizer.data.queries import get_queries
from tournament_visualizer.nation_colors import get_match_player_colors
from tournament_visualizer.utils.event_categories import (
    get_category_color_map,
    get_event_category,
)
from tournament_visualizer.components.tech_tree import (
    build_cytoscape_elements,
    get_techs_at_turn,
    TECH_TREE_STYLESHEET,
)
from tournament_visualizer.components.game_state import create_game_state_component
from tournament_visualizer.components.match_card import analyze_match
from tournament_visualizer.components.match_card_layouts import create_match_card_layout
from tournament_visualizer.tech_tree import TECHS

logger = logging.getLogger(__name__)


def get_player_colors_from_df(df: pd.DataFrame) -> Dict[str, str]:
    """Extract player colors based on their civilizations from a DataFrame.

    Args:
        df: DataFrame with 'player_name' and 'civilization' columns

    Returns:
        Dict mapping player names to hex color codes
    """
    if df.empty or "civilization" not in df.columns:
        return {}

    # Get unique player-civilization pairs
    player_civs = df.groupby("player_name")["civilization"].first().to_dict()
    players = list(player_civs.keys())

    if len(players) < 2:
        # Single player, just use their nation color
        from tournament_visualizer.nation_colors import get_nation_color

        return {p: get_nation_color(player_civs[p]) for p in players}

    # Two players - use get_match_player_colors for same-nation handling
    color1, color2 = get_match_player_colors(
        player_civs.get(players[0]), player_civs.get(players[1])
    )
    return {players[0]: color1, players[1]: color2}


def get_player_colors_for_match(match_id: int) -> Dict[str, str]:
    """Get player colors for a match by fetching player civilization data.

    Args:
        match_id: The match ID to get player colors for

    Returns:
        Dict mapping player names to hex color codes
    """
    try:
        queries = get_queries()
        # Use yield history which has civilization data
        df = queries.get_yield_history_by_match(match_id)
        if not df.empty and "civilization" in df.columns:
            return get_player_colors_from_df(df)
    except Exception:
        pass
    return {}


# All 14 yield types tracked in Old World
YIELD_TYPES = [
    ("YIELD_FOOD", "Food"),
    ("YIELD_GROWTH", "Growth"),
    ("YIELD_SCIENCE", "Science"),
    ("YIELD_CULTURE", "Culture"),
    ("YIELD_CIVICS", "Civics"),
    ("YIELD_TRAINING", "Training"),
    ("YIELD_MONEY", "Money"),
    ("YIELD_ORDERS", "Orders"),
    ("YIELD_HAPPINESS", "Happiness"),
    ("YIELD_DISCONTENT", "Discontent"),
    ("YIELD_IRON", "Iron"),
    ("YIELD_STONE", "Stone"),
    ("YIELD_WOOD", "Wood"),
    ("YIELD_MAINTENANCE", "Maintenance"),
]

# Register this page
dash.register_page(__name__, path="/matches", name="Matches")

# Page layout
layout = html.Div(
    [
        # URL tracking
        dcc.Location(id="match-url", refresh=False),
        # Persistent storage for show text toggle (localStorage)
        dcc.Store(id="show-event-text-store", storage_type="local", data=False),
        # Persistent storage for event filter preferences (localStorage)
        # Default: all categories enabled
        dcc.Store(
            id="event-filter-store",
            storage_type="local",
            data={
                "Ambitions": True,
                "Battles": True,
                "Cities": True,
                "Laws": True,
                "Religion": True,
                "Rulers": True,
                "Techs": True,
                "Wonders": True,
            },
        ),
        # Track which tabs have been loaded for the current match
        # This prevents re-fetching data when switching back to already-loaded tabs
        dcc.Store(
            id="match-tabs-loaded-store",
            storage_type="memory",
            data={"match_id": None, "loaded_tabs": []},
        ),
        # Page header
        create_page_header(
            title=PAGE_CONFIG["matches"]["title"],
            description=PAGE_CONFIG["matches"]["description"],
            icon="bi-target",
        ),
        # Breadcrumb navigation
        html.Div(id="match-breadcrumb"),
        # Match selection
        dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.H5("Select Match", className="card-title"),
                        dcc.Dropdown(
                            id="match-selector",
                            placeholder="Choose a match to analyze...",
                            options=[],
                            value=None,
                        ),
                    ]
                )
            ],
            className="mb-4",
            style={"position": "relative", "zIndex": 100},
        ),
        # Match details section (shown when match is selected)
        html.Div(id="match-details-section", style={"display": "none"}),
        # Default empty state
        html.Div(
            id="match-empty-state",
            children=[
                create_empty_state(
                    title="Select a Match",
                    message="Choose a match from the dropdown above to view detailed analysis.",
                    icon="bi-search",
                )
            ],
        ),
    ]
)


# =============================================================================
# Tab Loading State Management
# =============================================================================
# This callback manages which tabs have been loaded for the current match.
# Tab callbacks use the store State to skip re-fetching data when returning
# to an already-loaded tab. The store resets when the match changes.


@callback(
    Output("match-tabs-loaded-store", "data"),
    Input("match-details-tabs", "active_tab"),
    Input("match-selector", "value"),
    State("match-tabs-loaded-store", "data"),
    prevent_initial_call=True,
)
def update_tab_loaded_state(
    active_tab: Optional[str],
    match_id: Optional[int],
    current_state: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Track which tabs have been loaded for the current match.

    When a tab is visited, it's added to the loaded_tabs list.
    When the match changes, the list is reset.

    Args:
        active_tab: Currently active tab ID
        match_id: Currently selected match ID
        current_state: Current state from the store

    Returns:
        Updated state dict with match_id and loaded_tabs list
    """
    if current_state is None:
        current_state = {"match_id": None, "loaded_tabs": []}

    # If match changed, reset loaded tabs
    if current_state.get("match_id") != match_id:
        return {"match_id": match_id, "loaded_tabs": [active_tab] if active_tab else []}

    # Add current tab to loaded list if not already there
    loaded_tabs = current_state.get("loaded_tabs", [])
    if active_tab and active_tab not in loaded_tabs:
        loaded_tabs = loaded_tabs + [active_tab]

    return {"match_id": match_id, "loaded_tabs": loaded_tabs}


@callback(
    [
        Output("match-selector", "value"),
        Output("match-url", "search"),
        Output("match-url", "hash"),  # Clear any hash that might appear
    ],
    [
        Input("match-url", "search"),
        Input("match-url", "hash"),  # Watch for hash changes
        Input("match-selector", "value"),
        Input("match-selector", "options"),
    ],
    prevent_initial_call=False,
)
def sync_match_selection(
    url_search: str,
    url_hash: str,
    selector_value: Optional[int],
    options: List[Dict[str, Any]],
) -> tuple:
    """Synchronize match selection between URL and dropdown.

    This callback handles bidirectional sync without creating a circular dependency
    by checking which input triggered the callback. It also waits for dropdown options
    to be loaded before setting a value from the URL to avoid race conditions.

    Args:
        url_search: URL query string (e.g., "?match_id=123")
        selector_value: Currently selected match ID from dropdown
        options: Available match options in dropdown

    Returns:
        Tuple of (selector_value, url_search, url_hash)
    """
    ctx = dash.callback_context

    # On initial load (no trigger), check URL for match_id
    if not ctx.triggered:
        from urllib.parse import parse_qs

        if url_search and options:
            params = parse_qs(url_search.lstrip("?"))
            match_id = params.get("match_id", [None])[0]
            if match_id:
                match_id_int = int(match_id)
                # Only set value if it exists in options
                if any(opt["value"] == match_id_int for opt in options):
                    return match_id_int, url_search, ""
        return None, "", ""

    # Check which input triggered this callback
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    # If URL changed (user navigated), update selector to match
    if trigger_id == "match-url":
        from urllib.parse import parse_qs

        if url_search and options:
            params = parse_qs(url_search.lstrip("?"))
            match_id = params.get("match_id", [None])[0]
            if match_id:
                match_id_int = int(match_id)
                # Only set value if it exists in options
                if any(opt["value"] == match_id_int for opt in options):
                    return match_id_int, url_search, ""
        return None, "", ""

    # If selector changed (user picked from dropdown), update URL to match
    elif trigger_id == "match-selector":
        if selector_value:
            new_url = f"?match_id={selector_value}"
            return selector_value, new_url, ""
        return None, "", ""

    # If options changed and we have a URL parameter, try to set it
    elif trigger_id == "match-selector" and url_search and options:
        from urllib.parse import parse_qs

        params = parse_qs(url_search.lstrip("?"))
        match_id = params.get("match_id", [None])[0]
        if match_id:
            match_id_int = int(match_id)
            # Only set value if it exists in options and not already set
            if selector_value != match_id_int and any(
                opt["value"] == match_id_int for opt in options
            ):
                return match_id_int, url_search, ""

    # Fallback (shouldn't reach here)
    return dash.no_update, dash.no_update, dash.no_update


@callback(
    Output("match-selector", "options"),
    Input("_pages_location", "pathname"),
)
def update_match_options(pathname: str) -> List[Dict[str, Any]]:
    """Update match selector options.

    Args:
        pathname: Current page path (triggers on page load)

    Returns:
        List of match options for dropdown
    """
    try:
        queries = get_queries()
        df = queries.get_match_summary()

        if df.empty:
            return []

        # Create options with match info
        options = []
        for _, row in df.iterrows():
            # Format display label
            game_name = row.get("game_name", "Unknown")
            save_date = row.get("save_date", "")
            total_turns = row.get("total_turns", 0)
            winner = row.get("winner_name", "Unknown")
            winner_civ = row.get("winner_civilization", "Unknown")
            players_with_nations = row.get("players_with_nations", "")

            if pd.notna(save_date):
                date_str = pd.to_datetime(save_date).strftime("%Y-%m-%d")
            else:
                date_str = "Unknown Date"

            # Include nation with winner name
            winner_display = (
                f"{winner} ({winner_civ})" if winner_civ != "Unknown" else winner
            )

            # Use players_with_nations if available, otherwise show game name
            if players_with_nations:
                label = f"{players_with_nations} ({date_str}) - {total_turns} turns - Winner: {winner_display}"
            else:
                label = f"{game_name} ({date_str}) - {total_turns} turns - Winner: {winner_display}"

            options.append({"label": label, "value": row["match_id"]})

        return sorted(options, key=lambda x: x["label"])

    except Exception as e:
        logger.error(f"Error updating match options: {e}")
        return []


@callback(
    [
        Output("match-details-section", "children"),
        Output("match-details-section", "style"),
        Output("match-empty-state", "style"),
    ],
    Input("match-selector", "value"),
    State("match-url", "search"),
)
def update_match_details(match_id: Optional[int], url_search: Optional[str]) -> tuple:
    """Update match details when a match is selected.

    Args:
        match_id: Selected match ID
        url_search: URL query string (e.g., "?beta=true")

    Returns:
        Tuple of (details_content, details_style, empty_state_style)
    """
    # Check if beta features should be shown
    show_beta = url_search and "beta=true" in url_search
    if not match_id:
        return html.Div(), {"display": "none"}, {"display": "block"}

    try:
        queries = get_queries()

        # Get match info
        match_df = queries.get_match_summary()
        match_info = match_df[match_df["match_id"] == match_id]

        if match_info.empty:
            return (
                create_empty_state(
                    title="Match Not Found",
                    message="The selected match could not be found.",
                    icon="bi-exclamation-triangle",
                ),
                {"display": "block"},
                {"display": "none"},
            )

        match_data = match_info.iloc[0]

        # Format display values with nations
        players_with_nations = match_data.get("players_with_nations", "")
        game_display = (
            players_with_nations
            if players_with_nations
            else match_data.get("game_name", "Unknown")
        )

        winner_name = match_data.get("winner_name", "Unknown")
        winner_civ = match_data.get("winner_civilization", "Unknown")
        winner_display = (
            f"{winner_name} ({winner_civ})" if winner_civ != "Unknown" else winner_name
        )

        # Get first picker info
        first_picker_name = match_data.get("first_picker_name", "Unknown")
        first_picker_display = (
            first_picker_name if first_picker_name != "Unknown" else "No data"
        )

        # Create match details layout
        details_content = [
            # Game name header
            html.Div(
                [
                    html.H1(
                        [
                            html.I(className="bi bi-controller me-3"),
                            game_display,
                        ],
                        className="mb-4",
                    )
                ],
            ),
            # Match info and winner boxes
            dbc.Row(
                [
                    # Combined match info box
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            # First line: turns and players
                                            html.Div(
                                                [
                                                    html.Div(
                                                        [
                                                            html.I(
                                                                className="bi bi-clock me-2 text-info"
                                                            ),
                                                            html.Span(
                                                                f"{match_data.get('total_turns', 0)} ",
                                                                className="fw-bold",
                                                            ),
                                                            html.Span(
                                                                "Turns",
                                                                className="text-muted",
                                                            ),
                                                        ],
                                                        className="d-inline-block me-4",
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.I(
                                                                className="bi bi-people me-2 text-success"
                                                            ),
                                                            html.Span(
                                                                f"{match_data.get('player_count', 0)} ",
                                                                className="fw-bold",
                                                            ),
                                                            html.Span(
                                                                "Players",
                                                                className="text-muted",
                                                            ),
                                                        ],
                                                        className="d-inline-block",
                                                    ),
                                                ],
                                                className="mb-2",
                                            ),
                                            # Second line: first pick
                                            html.Div(
                                                [
                                                    html.I(
                                                        className="bi bi-1-circle me-2 text-primary"
                                                    ),
                                                    html.Span(
                                                        (
                                                            f"{first_picker_display} had first pick"
                                                            if first_picker_name
                                                            != "Unknown"
                                                            else "First pick data not available"
                                                        ),
                                                        className="mb-0",
                                                    ),
                                                ],
                                            ),
                                        ]
                                    )
                                ],
                                className="h-100",
                            )
                        ],
                        width=8,
                    ),
                    # Winner box
                    dbc.Col(
                        [
                            create_metric_card(
                                title="Winner",
                                value=winner_display,
                                icon="bi-trophy",
                                color="warning",
                            )
                        ],
                        width=4,
                    ),
                ],
                className="mb-4",
            ),
            # Tabbed analysis sections
            create_tab_layout(
                [
                    {
                        "label": "Overview",
                        "tab_id": "overview",
                        "content": [
                            html.Div(
                                id="match-overview-content",
                                className="mt-3",
                            )
                        ],
                    },
                    {
                        "label": "Timeline",
                        "tab_id": "timeline",
                        "content": [
                            # Toggle for showing/hiding event text and filter
                            dbc.Row(
                                [
                                    dbc.Col(
                                        html.Div(
                                            [
                                                dbc.Checklist(
                                                    id="event-filter-checklist",
                                                    options=[
                                                        {"label": cat, "value": cat}
                                                        for cat in [
                                                            "Ambitions",
                                                            "Battles",
                                                            "Cities",
                                                            "Laws",
                                                            "Religion",
                                                            "Rulers",
                                                            "Techs",
                                                            "Wonders",
                                                            "Metrics",
                                                        ]
                                                    ],
                                                    value=[
                                                        "Ambitions",
                                                        "Battles",
                                                        "Cities",
                                                        "Laws",
                                                        "Religion",
                                                        "Rulers",
                                                        "Techs",
                                                        "Wonders",
                                                        "Metrics",
                                                    ],
                                                    inline=True,
                                                    className="event-filter-checklist d-inline-flex",
                                                    switch=True,
                                                ),
                                            ],
                                            className="py-1 px-2 d-flex align-items-center",
                                            style={
                                                "backgroundColor": "rgba(255,255,255,0.05)",
                                                "border": "1px solid rgba(255,255,255,0.1)",
                                                "borderRadius": "0.375rem",
                                            },
                                        ),
                                        width="auto",
                                    ),
                                    dbc.Col(
                                        html.Div(
                                            dbc.Switch(
                                                id="show-event-text-toggle",
                                                label="Display text",
                                                value=False,
                                                className="mb-0",
                                            ),
                                            className="py-1 px-2 d-flex align-items-center",
                                            style={
                                                "backgroundColor": "rgba(255,255,255,0.05)",
                                                "border": "1px solid rgba(255,255,255,0.1)",
                                                "borderRadius": "0.375rem",
                                            },
                                        ),
                                        width="auto",
                                        className="ms-auto",
                                    ),
                                ],
                                className="mt-2 mb-2 align-items-center g-3",
                            ),
                            # Game state comparison table
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Card(
                                                [
                                                    dbc.CardBody(
                                                        [
                                                            html.Div(
                                                                id="match-overview-table",
                                                                className="game-state-container",
                                                            )
                                                        ]
                                                    )
                                                ]
                                            )
                                        ],
                                        width=12,
                                    )
                                ],
                            ),
                        ],
                    },
                    {
                        "label": "Events",
                        "tab_id": "events",
                        "content": [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            create_chart_card(
                                                title="Events Timeline by Category",
                                                chart_id="match-progression-chart",
                                                height="400px",
                                            )
                                        ],
                                        width=12,
                                    )
                                ],
                                className="mt-3 mb-3",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            create_data_table_card(
                                                title="Events",
                                                table_id="match-turns-table",
                                                columns=[
                                                    {
                                                        "name": "Turn",
                                                        "id": "turn_number",
                                                        "type": "numeric",
                                                    },
                                                    {
                                                        "name": "Category",
                                                        "id": "event_category",
                                                    },
                                                    {
                                                        "name": "Player",
                                                        "id": "player_name",
                                                    },
                                                    {
                                                        "name": "Description",
                                                        "id": "description",
                                                    },
                                                ],
                                            )
                                        ],
                                        width=12,
                                    )
                                ]
                            ),
                        ],
                    },
                    {
                        "label": "Laws",
                        "tab_id": "laws",
                        "content": [
                            # Law Tempo chart
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            create_chart_card(
                                                title="Law Tempo",
                                                chart_id="match-law-cumulative",
                                                height="400px",
                                            )
                                        ],
                                        width=12,
                                    ),
                                ],
                                className="mt-3 mb-3",
                            ),
                            # Law Adoption Timeline - height auto to fit dynamic law count
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            create_chart_card(
                                                title="Law Adoption Timeline",
                                                chart_id="match-law-timeline",
                                                height="auto",
                                            )
                                        ],
                                        width=12,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Final Laws by player
                            html.Div(id="match-final-laws-content", className="mb-3"),
                        ],
                    },
                    {
                        "label": "Techs",
                        "tab_id": "technology",
                        "content": [
                            # Tech Tree Visualization
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H5(
                                                "Tech Tree Progression",
                                                className="card-title",
                                            ),
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            html.Label(
                                                                "Turn:",
                                                                className="form-label",
                                                            ),
                                                            dcc.Slider(
                                                                id="match-tech-tree-turn-slider",
                                                                min=0,
                                                                max=100,
                                                                step=1,
                                                                value=100,
                                                                marks={
                                                                    i: str(i)
                                                                    for i in range(
                                                                        0, 101, 25
                                                                    )
                                                                },
                                                                tooltip={
                                                                    "placement": "bottom",
                                                                    "always_visible": True,
                                                                },
                                                            ),
                                                        ],
                                                        width=12,
                                                    ),
                                                ]
                                            ),
                                        ]
                                    )
                                ],
                                className="mt-3 mb-3",
                            ),
                            # Tech trees side by side
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Card(
                                                [
                                                    dbc.CardHeader(
                                                        id="match-tech-tree-player1-header"
                                                    ),
                                                    dbc.CardBody(
                                                        [
                                                            cyto.Cytoscape(
                                                                id="match-tech-tree-player1",
                                                                elements=[],
                                                                stylesheet=TECH_TREE_STYLESHEET,
                                                                layout={
                                                                    "name": "preset"
                                                                },
                                                                style={
                                                                    "width": "100%",
                                                                    "height": "420px",
                                                                },
                                                                userZoomingEnabled=False,
                                                                userPanningEnabled=False,
                                                                boxSelectionEnabled=False,
                                                            )
                                                        ],
                                                        style={"padding": "0.5rem"},
                                                    ),
                                                ]
                                            )
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Card(
                                                [
                                                    dbc.CardHeader(
                                                        id="match-tech-tree-player2-header"
                                                    ),
                                                    dbc.CardBody(
                                                        [
                                                            cyto.Cytoscape(
                                                                id="match-tech-tree-player2",
                                                                elements=[],
                                                                stylesheet=TECH_TREE_STYLESHEET,
                                                                layout={
                                                                    "name": "preset"
                                                                },
                                                                style={
                                                                    "width": "100%",
                                                                    "height": "420px",
                                                                },
                                                                userZoomingEnabled=False,
                                                                userPanningEnabled=False,
                                                                boxSelectionEnabled=False,
                                                            )
                                                        ],
                                                        style={"padding": "0.5rem"},
                                                    ),
                                                ]
                                            )
                                        ],
                                        width=6,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Technology Tempo chart
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            create_chart_card(
                                                title="Technology Tempo",
                                                chart_id="match-technology-chart",
                                                height="400px",
                                            )
                                        ],
                                        width=12,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Technology Discovery Timeline
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            create_chart_card(
                                                title="Technology Discovery Timeline",
                                                chart_id="match-tech-timeline",
                                                height="1200px",
                                            )
                                        ],
                                        width=12,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Final Technologies by player
                            html.Div(id="match-final-techs-content", className="mb-3"),
                        ],
                    },
                    {
                        "label": "Yields",
                        "tab_id": "yields",
                        "content": [
                            # Generate rows of charts dynamically
                            # Each row contains 2 charts side-by-side
                            *[
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            [
                                                create_chart_card(
                                                    title=YIELD_TYPES[i][
                                                        1
                                                    ],  # Display name
                                                    chart_id=f"match-{YIELD_TYPES[i][0].lower().replace('_', '-')}-chart",
                                                    height="520px",
                                                )
                                            ],
                                            width=6,
                                        ),
                                        (
                                            dbc.Col(
                                                [
                                                    create_chart_card(
                                                        title=(
                                                            YIELD_TYPES[i + 1][1]
                                                            if i + 1 < len(YIELD_TYPES)
                                                            else ""
                                                        ),
                                                        chart_id=(
                                                            f"match-{YIELD_TYPES[i + 1][0].lower().replace('_', '-')}-chart"
                                                            if i + 1 < len(YIELD_TYPES)
                                                            else "match-empty-chart"
                                                        ),
                                                        height="520px",
                                                    )
                                                ],
                                                width=6,
                                            )
                                            if i + 1 < len(YIELD_TYPES)
                                            else dbc.Col(width=6)
                                        ),  # Empty column if odd number
                                    ],
                                    className="mt-3 mb-3" if i == 0 else "mb-3",
                                )
                                for i in range(
                                    0, len(YIELD_TYPES), 2
                                )  # Step by 2 to create pairs
                            ],
                        ],
                    },
                    # Science tab (beta) - only shown when ?beta=true in URL
                    *(
                        [
                            {
                                "label": "Science ᴮᵉᵗᵃ",
                                "tab_id": "science",
                                "content": [
                                    # Row 1: Science Breakdown (full width)
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    create_chart_card(
                                                        title="Science from Infrastructure",
                                                        chart_id="match-science-breakdown",
                                                        height="280px",
                                                    )
                                                ],
                                                width=12,
                                            ),
                                        ],
                                        className="mt-3 mb-3",
                                    ),
                                    # Row 2: Direct Science Sources (full width)
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    create_chart_card(
                                                        title="Direct Science Sources",
                                                        chart_id="match-science-sources",
                                                        height="400px",
                                                    )
                                                ],
                                                width=12,
                                            ),
                                        ],
                                        className="mb-3",
                                    ),
                                    # Row 3: Timeline (full width)
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    create_chart_card(
                                                        title="Science Infrastructure Timeline",
                                                        chart_id="match-science-timeline",
                                                        height="400px",
                                                    )
                                                ],
                                                width=12,
                                            ),
                                        ],
                                        className="mb-3",
                                    ),
                                ],
                            }
                        ]
                        if show_beta
                        else []
                    ),
                    {
                        "label": "Ambitions",
                        "tab_id": "ambitions",
                        "content": [
                            # Legitimacy Progression Chart
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            create_chart_card(
                                                title="Legitimacy Progression",
                                                chart_id="match-legitimacy-progression",
                                                height="400px",
                                            )
                                        ],
                                        width=12,
                                    ),
                                ],
                                className="mt-3 mb-3",
                            ),
                            # Ambition Summary (moved from Ambitions tab)
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            create_chart_card(
                                                title="Ambition Summary",
                                                chart_id="match-ambition-summary",
                                                height="auto",
                                            )
                                        ],
                                        width=12,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Legitimacy Breakdown (populated by callback)
                            html.Div(id="match-legitimacy-breakdown-container"),
                            # Ambition Timeline Charts (dynamically generated per player)
                            html.Div(id="match-ambition-timelines-container"),
                        ],
                    },
                    {
                        "label": "Cities",
                        "tab_id": "cities",
                        "content": [
                            # Territory Control Charts
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            create_chart_card(
                                                title="Territory Control Over Time",
                                                chart_id="match-territory-timeline-chart",
                                                height="400px",
                                            )
                                        ],
                                        width=8,
                                    ),
                                    dbc.Col(
                                        [
                                            create_chart_card(
                                                title="Final Territory Distribution",
                                                chart_id="match-territory-distribution-chart",
                                                height="400px",
                                            )
                                        ],
                                        width=4,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Family City Distribution
                            html.Div(id="match-family-city-panels", className="mb-3"),
                            # Cumulative City Count
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            create_chart_card(
                                                title="Cumulative City Count",
                                                chart_id="match-cumulative-city-count",
                                                height="400px",
                                            )
                                        ],
                                        width=12,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # City Founding Timeline
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            create_chart_card(
                                                title="City Founding Timeline",
                                                chart_id="match-city-founding-scatter",
                                                height="400px",
                                            )
                                        ],
                                        width=12,
                                    ),
                                ],
                                className="mb-3",
                            ),
                        ],
                    },
                    {
                        "label": "Map",
                        "tab_id": "map",
                        "content": [
                            # Pixi.js Map Viewer in iframe
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.Iframe(
                                                id="match-pixi-map-iframe",
                                                src="",
                                                style={
                                                    "width": "100%",
                                                    "height": "700px",
                                                    "border": "none",
                                                    "borderRadius": "6px",
                                                },
                                            ),
                                        ],
                                        className="p-2",
                                    ),
                                ],
                                className="mb-3",
                            ),
                        ],
                    },
                    {
                        "label": "Improvements",
                        "tab_id": "improvements",
                        "content": [
                            # Improvements section - side-by-side player lists
                            html.Div(
                                id="match-improvements-section", className="mt-3 mb-3"
                            ),
                            # Specialists section - side-by-side player lists
                            html.Div(id="match-specialists-section", className="mb-3"),
                        ],
                    },
                    {
                        "label": "Military",
                        "tab_id": "military",
                        "content": [
                            # Military Power Progression
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            create_chart_card(
                                                title="Military Power",
                                                chart_id="match-military-power",
                                                height="400px",
                                            )
                                        ],
                                        width=12,
                                    ),
                                ],
                                className="mt-3 mb-3",
                            ),
                            # Unit listing by player
                            html.Div(
                                id="match-units-list-content", className="mt-3 mb-3"
                            ),
                            # Row 1: Stacked Bar and Grouped Bar
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            create_chart_card(
                                                title="Army Composition (Stacked)",
                                                chart_id="match-units-stacked-bar",
                                                height="400px",
                                            )
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            create_chart_card(
                                                title="Unit Comparison (Grouped)",
                                                chart_id="match-units-grouped-bar",
                                                height="400px",
                                            )
                                        ],
                                        width=6,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Row 2: Waffle Chart
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            create_chart_card(
                                                title="Unit Grid (Waffle)",
                                                chart_id="match-units-waffle",
                                                height="450px",
                                            )
                                        ],
                                        width=12,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Row 3: Treemap
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            create_chart_card(
                                                title="Unit Hierarchy (Treemap)",
                                                chart_id="match-units-treemap",
                                                height="550px",
                                            )
                                        ],
                                        width=12,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Row 4: Icon Grid
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            create_chart_card(
                                                title="Army Formation (Icons)",
                                                chart_id="match-units-icon-grid",
                                                height="450px",
                                            )
                                        ],
                                        width=12,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Row 5: Army Portrait
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            create_chart_card(
                                                title="Army Portrait",
                                                chart_id="match-units-portrait",
                                                height="400px",
                                            )
                                        ],
                                        width=12,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Row 6: Marimekko Chart
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            create_chart_card(
                                                title="Army Size & Composition (Marimekko)",
                                                chart_id="match-units-marimekko",
                                                height="500px",
                                            )
                                        ],
                                        width=12,
                                    ),
                                ],
                                className="mb-3",
                            ),
                        ],
                    },
                    {
                        "label": "Settings",
                        "tab_id": "settings",
                        "content": [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [html.Div(id="match-settings-content")],
                                        width=12,
                                    )
                                ],
                                className="mt-3",
                            )
                        ],
                    },
                ],
                active_tab="overview",
                tabs_id="match-details-tabs",
            ),
        ]

        return details_content, {"display": "block"}, {"display": "none"}

    except Exception as e:
        error_content = create_empty_state(
            title="Error Loading Match",
            message=f"Unable to load match details: {str(e)}",
            icon="bi-exclamation-triangle",
        )
        return error_content, {"display": "block"}, {"display": "none"}


@callback(
    Output("show-event-text-toggle", "value"),
    Input("show-event-text-store", "modified_timestamp"),
    State("show-event-text-store", "data"),
    prevent_initial_call=False,
)
def sync_toggle_from_store(
    modified_ts: Optional[int], store_value: Optional[bool]
) -> bool:
    """Initialize toggle from localStorage on page load."""
    return store_value if store_value is not None else False


@callback(
    Output("show-event-text-store", "data"),
    Input("show-event-text-toggle", "value"),
    prevent_initial_call=True,
)
def sync_store_from_toggle(toggle_value: bool) -> bool:
    """Save toggle state to localStorage when user changes toggle."""
    return toggle_value


# Event filter callbacks
@callback(
    Output("event-filter-checklist", "value"),
    Input("event-filter-store", "modified_timestamp"),
    State("event-filter-store", "data"),
    prevent_initial_call=False,
)
def sync_filter_from_store(
    modified_ts: Optional[int], store_data: Optional[dict]
) -> list[str]:
    """Initialize filter checklist from localStorage on page load."""
    if store_data is None:
        # Default: all enabled
        return [
            "Ambitions",
            "Battles",
            "Cities",
            "Laws",
            "Religion",
            "Rulers",
            "Techs",
            "Wonders",
        ]
    # Return list of enabled categories
    return [cat for cat, enabled in store_data.items() if enabled]


@callback(
    Output("event-filter-store", "data"),
    Input("event-filter-checklist", "value"),
    prevent_initial_call=True,
)
def sync_store_from_filter(selected_categories: list[str]) -> dict:
    """Save filter state to localStorage when user changes selection."""
    all_categories = [
        "Ambitions",
        "Battles",
        "Cities",
        "Laws",
        "Religion",
        "Rulers",
        "Techs",
        "Wonders",
        "Metrics",
    ]
    return {cat: (cat in selected_categories) for cat in all_categories}


@callback(
    Output("match-overview-table", "children"),
    Input("match-details-tabs", "active_tab"),
    Input("match-selector", "value"),
    Input("show-event-text-toggle", "value"),
    Input("event-filter-checklist", "value"),
)
def update_overview_table(
    active_tab: Optional[str],
    match_id: Optional[int],
    show_text: bool,
    enabled_categories: Optional[list[str]],
) -> html.Div:
    """Update the overview comparison table.

    Args:
        active_tab: Currently active tab ID
        match_id: Selected match ID
        show_text: Whether to show event text labels
        enabled_categories: List of enabled filter categories (includes "Metrics")

    Returns:
        Overview comparison component HTML
    """
    # Extract Metrics toggle from the checklist
    show_metrics = "Metrics" in (enabled_categories or [])
    # Lazy loading - only update when Timeline tab is active
    if active_tab != "timeline":
        raise dash.exceptions.PreventUpdate

    if not match_id:
        return create_empty_state(
            title="Select a Match",
            message="Choose a match from the dropdown to view match overview.",
            icon="bi-bar-chart",
        )

    try:
        queries = get_queries()

        # Get timeline events for the icons column
        events_df = queries.get_match_timeline_events(match_id)

        # Get player IDs from events or match summary
        if not events_df.empty:
            player_ids = events_df["player_id"].dropna().unique()
            if len(player_ids) >= 2:
                player1_id = int(min(player_ids))
                player2_id = int(max(player_ids))
            else:
                # Fall back to match summary
                players_df = queries.get_match_summary()
                match_info = players_df[players_df["match_id"] == match_id]
                if not match_info.empty:
                    player1_id = int(match_info.iloc[0]["player1_id"])
                    player2_id = int(match_info.iloc[0]["player2_id"])
                else:
                    return create_empty_state(
                        title="No Player Data",
                        message="Unable to determine players for this match.",
                        icon="bi-people",
                    )
        else:
            # Get player IDs from match summary
            players_df = queries.get_match_summary()
            match_info = players_df[players_df["match_id"] == match_id]
            if not match_info.empty:
                player1_id = int(match_info.iloc[0]["player1_id"])
                player2_id = int(match_info.iloc[0]["player2_id"])
            else:
                return create_empty_state(
                    title="No Match Data",
                    message="Unable to load match data.",
                    icon="bi-exclamation-circle",
                )

        # Get comparison data
        comparison_df = queries.get_match_turn_comparisons(
            match_id, player1_id, player2_id
        )

        if comparison_df.empty:
            return create_empty_state(
                title="No Comparison Data",
                message="No turn-by-turn data available for this match.",
                icon="bi-bar-chart",
            )

        # Filter to only turns with events (no interpolation)
        if not events_df.empty:
            event_turns = events_df["turn"].unique()
            comparison_df = comparison_df[
                comparison_df["turn_number"].isin(event_turns)
            ]

        # Get player names
        player1_name = "Player 1"
        player2_name = "Player 2"

        if not events_df.empty:
            player_names = events_df[["player_id", "player_name"]].drop_duplicates()
            for _, row in player_names.iterrows():
                if row["player_id"] == player1_id:
                    player1_name = row["player_name"] or "Player 1"
                elif row["player_id"] == player2_id:
                    player2_name = row["player_name"] or "Player 2"

        # Get nation colors and civilizations from yield history
        player1_color = "#4dabf7"
        player2_color = "#ff6b6b"
        player1_civilization = ""
        player2_civilization = ""
        try:
            yield_df = queries.get_yield_history_by_match(match_id)
            if not yield_df.empty and "civilization" in yield_df.columns:
                colors = get_player_colors_from_df(yield_df)
                player1_color = colors.get(player1_name, "#4dabf7")
                player2_color = colors.get(player2_name, "#ff6b6b")
                # Extract civilizations
                civ_by_name = (
                    yield_df.groupby("player_name")["civilization"].first().to_dict()
                )
                player1_civilization = civ_by_name.get(player1_name, "")
                player2_civilization = civ_by_name.get(player2_name, "")
        except Exception:
            pass

        return create_game_state_component(
            comparison_df=comparison_df,
            events_df=events_df,
            player1_name=player1_name,
            player2_name=player2_name,
            player1_id=player1_id,
            player2_id=player2_id,
            player1_color=player1_color,
            player2_color=player2_color,
            player1_civilization=player1_civilization,
            player2_civilization=player2_civilization,
            show_text=show_text,
            show_metrics=show_metrics,
            enabled_categories=enabled_categories,
        )

    except Exception as e:
        logger.error(f"Error updating game state table: {e}")
        return create_empty_state(
            title="Error Loading Game State",
            message=f"Unable to load game state: {str(e)}",
            icon="bi-exclamation-triangle",
        )


@callback(Output("match-progression-chart", "figure"), Input("match-selector", "value"))
def update_progression_chart(match_id: Optional[int]):
    """Update the events timeline chart categorized by gameplay type.

    Args:
        match_id: Selected match ID

    Returns:
        Plotly figure for events timeline as stacked bar chart
    """
    if not match_id:
        return create_empty_chart_placeholder("Select a match to view events")

    try:
        queries = get_queries()
        # Get event timeline (includes both MemoryData and LogData events)
        df = queries.get_event_timeline(match_id, None)

        if df.empty:
            return create_empty_chart_placeholder("No event data available")

        # Add gameplay category to each event
        df["gameplay_category"] = df["event_type"].apply(get_event_category)

        # Count events per turn by gameplay category
        import plotly.graph_objects as go

        from tournament_visualizer.components.charts import create_base_figure

        # Group by turn and gameplay category
        events_by_category = (
            df.groupby(["turn_number", "gameplay_category"])
            .size()
            .reset_index(name="event_count")
        )

        # Create stacked bar chart
        fig = create_base_figure(
            title="Events Timeline by Category",
            x_title="Turn Number",
            y_title="Number of Events",
        )

        # Get category colors
        category_colors = get_category_color_map()

        # Get unique categories and sort for consistent legend order
        categories = sorted(events_by_category["gameplay_category"].unique())

        # Add a bar trace for each category
        for category in categories:
            category_data = events_by_category[
                events_by_category["gameplay_category"] == category
            ]
            fig.add_trace(
                go.Bar(
                    name=category,
                    x=category_data["turn_number"],
                    y=category_data["event_count"],
                    marker_color=category_colors.get(category, "#6c757d"),
                )
            )

        # Set barmode to stack
        fig.update_layout(
            barmode="stack",
            legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        )

        return fig

    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading events: {str(e)}")


@callback(Output("match-turns-table", "data"), Input("match-selector", "value"))
def update_turns_table(match_id: Optional[int]) -> List[Dict[str, Any]]:
    """Update the event details table with both MemoryData and LogData events.

    Args:
        match_id: Selected match ID

    Returns:
        List of event data for table
    """
    if not match_id:
        return []

    try:
        queries = get_queries()
        # Get event timeline data (includes both MemoryData and LogData events)
        df = queries.get_event_timeline(match_id, None)

        if df.empty:
            return []

        # Add gameplay category to each event
        df["gameplay_category"] = df["event_type"].apply(get_event_category)

        # Replace the old event_category with the new gameplay_category
        df["event_category"] = df["gameplay_category"]

        # Limit to 500 most recent events for display (increased from 100 to show more LogData events)
        return df.head(500).to_dict("records")

    except Exception as e:
        logger.error(f"Error updating events table: {e}")
        return []


@callback(Output("match-breadcrumb", "children"), Input("match-selector", "value"))
def update_breadcrumb(match_id: Optional[int]) -> html.Div:
    """Update breadcrumb navigation.

    Args:
        match_id: Selected match ID

    Returns:
        Breadcrumb component
    """
    items = [{"label": "Home", "href": "/"}, {"label": "Matches", "href": "/matches"}]

    if match_id:
        # Get match name for breadcrumb
        try:
            queries = get_queries()
            match_df = queries.get_match_summary()
            match_info = match_df[match_df["match_id"] == match_id]

            if not match_info.empty:
                players_with_nations = match_info.iloc[0].get(
                    "players_with_nations", ""
                )
                game_name = match_info.iloc[0].get("game_name", f"Match {match_id}")
                # Use players with nations if available, otherwise use game name
                display_name = (
                    players_with_nations if players_with_nations else game_name
                )
                items.append({"label": display_name})
            else:
                items.append({"label": f"Match {match_id}"})
        except Exception as e:
            # Log the error but don't crash
            logger.error(f"Error getting match name for breadcrumb: {e}")
            items.append({"label": f"Match {match_id}"})

    return create_breadcrumb(items)


@callback(
    Output("match-technology-chart", "figure"),
    Input("match-details-tabs", "active_tab"),
    Input("match-selector", "value"),
    State("match-tabs-loaded-store", "data"),
    prevent_initial_call=True,
)
def update_technology_chart(
    active_tab: Optional[str],
    match_id: Optional[int],
    loaded_state: Optional[Dict[str, Any]],
) -> go.Figure:
    """Update cumulative technology count chart.

    Args:
        active_tab: Currently active tab
        match_id: Selected match ID
        loaded_state: Tab loading state from store

    Returns:
        Plotly figure for cumulative technology count
    """
    # Lazy loading: skip rendering if tab is not active
    if active_tab != "technology":
        raise dash.exceptions.PreventUpdate

    # Skip re-fetching if tab was already loaded for this match
    if loaded_state and loaded_state.get("match_id") == match_id:
        if "technology" in loaded_state.get("loaded_tabs", []):
            raise dash.exceptions.PreventUpdate

    if not match_id:
        return create_empty_chart_placeholder("Select a match to view technology data")

    try:
        queries = get_queries()
        df = queries.get_tech_count_by_turn(match_id)

        if df.empty:
            return create_empty_chart_placeholder(
                "No technology data available for this match"
            )

        # Get total turns for the match to extend lines to the end
        match_df = queries.get_match_summary()
        match_info = match_df[match_df["match_id"] == match_id]
        total_turns = (
            match_info.iloc[0]["total_turns"] if not match_info.empty else None
        )

        # Get player colors based on their civilizations
        player_colors = get_player_colors_for_match(match_id)

        return create_cumulative_tech_count_chart(df, total_turns, player_colors)

    except Exception as e:
        logger.error(f"Error loading cumulative tech count: {e}")
        return create_empty_chart_placeholder(
            f"Error loading technology data: {str(e)}"
        )


@callback(Output("match-tech-timeline", "figure"), Input("match-selector", "value"))
def update_tech_timeline(match_id: Optional[int]) -> go.Figure:
    """Update technology completion timeline chart.

    Args:
        match_id: Selected match ID

    Returns:
        Plotly figure showing when each player discovered each technology
    """
    if not match_id:
        return create_empty_chart_placeholder(
            "Select a match to view technology timeline"
        )

    try:
        queries = get_queries()
        df = queries.get_tech_timeline(match_id)

        if df.empty:
            return create_empty_chart_placeholder(
                "No technology timeline data available for this match"
            )

        # Get player colors based on their civilizations
        player_colors = get_player_colors_for_match(match_id)

        return create_tech_completion_timeline_chart(df, player_colors)

    except Exception as e:
        logger.error(f"Error loading tech completion timeline: {e}")
        return create_empty_chart_placeholder(
            f"Error loading technology timeline: {str(e)}"
        )


@callback(
    Output("match-law-timeline", "figure"),
    Input("match-details-tabs", "active_tab"),
    Input("match-selector", "value"),
    State("match-tabs-loaded-store", "data"),
    prevent_initial_call=True,
)
def update_law_timeline(
    active_tab: Optional[str],
    match_id: Optional[int],
    loaded_state: Optional[Dict[str, Any]],
) -> go.Figure:
    """Update law adoption timeline chart.

    Args:
        active_tab: Currently active tab
        match_id: Selected match ID
        loaded_state: Tab loading state from store

    Returns:
        Plotly figure showing when each player adopted each law
    """
    # Lazy loading: skip rendering if tab is not active
    if active_tab != "laws":
        raise dash.exceptions.PreventUpdate
    # Skip re-fetching if tab was already loaded for this match
    if loaded_state and loaded_state.get("match_id") == match_id:
        if "laws" in loaded_state.get("loaded_tabs", []):
            raise dash.exceptions.PreventUpdate
    # Skip re-fetching if tab was already loaded for this match
    if loaded_state and loaded_state.get("match_id") == match_id:
        if "laws" in loaded_state.get("loaded_tabs", []):
            raise dash.exceptions.PreventUpdate

    # Skip re-fetching if tab was already loaded for this match
    if loaded_state and loaded_state.get("match_id") == match_id:
        if "laws" in loaded_state.get("loaded_tabs", []):
            raise dash.exceptions.PreventUpdate

    if not match_id:
        return create_empty_chart_placeholder("Select a match to view law timeline")

    try:
        queries = get_queries()
        df = queries.get_law_timeline(match_id)

        if df.empty:
            return create_empty_chart_placeholder(
                "No law timeline data available for this match"
            )

        # Get player colors based on their civilizations
        player_colors = get_player_colors_for_match(match_id)

        return create_law_adoption_timeline_chart(df, player_colors)

    except Exception as e:
        logger.error(f"Error loading law adoption timeline: {e}")
        return create_empty_chart_placeholder(f"Error loading law timeline: {str(e)}")


@callback(
    Output("match-settings-content", "children"), Input("match-selector", "value")
)
def update_settings_content(match_id: Optional[int]):
    """Update game settings display with comprehensive formatting.

    Args:
        match_id: Selected match ID

    Returns:
        HTML content with game settings
    """
    if not match_id:
        return create_empty_state(
            "Select a match to view game settings", icon="bi-gear"
        )

    try:
        queries = get_queries()
        metadata = queries.get_match_metadata(match_id)

        # Get map info and game mode from match summary
        match_df = queries.get_match_summary()
        match_info = match_df[match_df["match_id"] == match_id]

        if not match_info.empty:
            map_size = match_info.iloc[0].get("map_size", "Unknown")
            map_class = match_info.iloc[0].get("map_class", "Unknown")
            map_aspect_ratio = match_info.iloc[0].get("map_aspect_ratio", "Unknown")
            game_mode = match_info.iloc[0].get("game_mode", "Unknown")
            turn_style = match_info.iloc[0].get("turn_style", "Unknown")
            turn_timer = match_info.iloc[0].get("turn_timer", "Unknown")
        else:
            map_size = map_class = map_aspect_ratio = "Unknown"
            game_mode = turn_style = turn_timer = "Unknown"

        if not metadata:
            return create_empty_state(
                "No settings data available for this match",
                icon="bi-exclamation-triangle",
            )

        import json

        settings_cards = []

        # Row 1: Basic Settings and Map Settings (side by side)
        settings_row1 = dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader("Basic Settings"),
                                dbc.CardBody(
                                    [
                                        html.Dl(
                                            [
                                                html.Dt("Difficulty"),
                                                html.Dd(
                                                    metadata.get("difficulty", "N/A")
                                                ),
                                                html.Dt("Event Level"),
                                                html.Dd(
                                                    metadata.get("event_level", "N/A")
                                                ),
                                                html.Dt("Victory Type"),
                                                html.Dd(
                                                    metadata.get("victory_type", "N/A")
                                                ),
                                                html.Dt("Victory Turn"),
                                                html.Dd(
                                                    str(
                                                        metadata.get(
                                                            "victory_turn", "None"
                                                        )
                                                    )
                                                ),
                                            ]
                                        )
                                    ]
                                ),
                            ],
                        )
                    ],
                    width=6,
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader("Map Settings"),
                                dbc.CardBody(
                                    [
                                        html.Dl(
                                            [
                                                html.Dt("Class"),
                                                html.Dd(map_class),
                                                html.Dt("Size"),
                                                html.Dd(map_size),
                                                html.Dt("Aspect Ratio"),
                                                html.Dd(map_aspect_ratio),
                                            ]
                                        )
                                    ]
                                ),
                            ],
                        )
                    ],
                    width=6,
                ),
            ],
            className="mb-3",
        )
        settings_cards.append(settings_row1)

        # Row 2: Turn Settings and Gameplay Modifiers (side by side)
        settings_row2 = dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader("Turn Settings"),
                                dbc.CardBody(
                                    [
                                        html.Dl(
                                            [
                                                html.Dt("Game Mode"),
                                                html.Dd(game_mode),
                                                html.Dt("Turn Style"),
                                                html.Dd(turn_style),
                                                html.Dt("Turn Timer"),
                                                html.Dd(turn_timer),
                                            ]
                                        )
                                    ]
                                ),
                            ],
                        )
                    ],
                    width=6,
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader("Gameplay Modifiers"),
                                dbc.CardBody(
                                    [
                                        html.Dl(
                                            [
                                                html.Dt("Opponent Level"),
                                                html.Dd(
                                                    metadata.get(
                                                        "opponent_level", "N/A"
                                                    )
                                                ),
                                                html.Dt("Tribe Level"),
                                                html.Dd(
                                                    metadata.get("tribe_level", "N/A")
                                                ),
                                                html.Dt("Development"),
                                                html.Dd(
                                                    metadata.get("development", "N/A")
                                                ),
                                            ]
                                        )
                                    ]
                                ),
                            ],
                        )
                    ],
                    width=6,
                ),
            ],
            className="mb-3",
        )
        settings_cards.append(settings_row2)

        # Row 3: Advanced Modifiers
        settings_row3 = dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader("Advanced Settings"),
                                dbc.CardBody(
                                    [
                                        html.Dl(
                                            [
                                                html.Dt("Advantage"),
                                                html.Dd(
                                                    metadata.get("advantage", "N/A")
                                                ),
                                                html.Dt("Succession Gender"),
                                                html.Dd(
                                                    metadata.get(
                                                        "succession_gender", "N/A"
                                                    )
                                                ),
                                                html.Dt("Succession Order"),
                                                html.Dd(
                                                    metadata.get(
                                                        "succession_order", "N/A"
                                                    )
                                                ),
                                                html.Dt("Mortality"),
                                                html.Dd(
                                                    metadata.get("mortality", "N/A")
                                                ),
                                                html.Dt("Victory Point Modifier"),
                                                html.Dd(
                                                    metadata.get(
                                                        "victory_point_modifier", "N/A"
                                                    )
                                                ),
                                            ]
                                        )
                                    ]
                                ),
                            ],
                        )
                    ],
                    width=12,
                ),
            ],
            className="mb-3",
        )
        settings_cards.append(settings_row3)

        # Game Options - formatted as readable list
        if metadata.get("game_options"):
            try:
                options = (
                    json.loads(metadata["game_options"])
                    if isinstance(metadata["game_options"], str)
                    else metadata["game_options"]
                )
                if options:
                    # Format option names to be readable
                    option_items = []
                    for opt_key, opt_value in options.items():
                        # Clean up the option name
                        clean_name = (
                            opt_key.replace("GAMEOPTION_", "").replace("_", " ").title()
                        )
                        # If value exists, show it; otherwise just show the option name
                        if opt_value and opt_value != "":
                            option_items.append(f"{clean_name}: {opt_value}")
                        else:
                            option_items.append(clean_name)

                    game_options_card = dbc.Card(
                        [
                            dbc.CardHeader("Game Options"),
                            dbc.CardBody(
                                [
                                    html.Ul(
                                        [html.Li(opt) for opt in option_items],
                                        style={"fontSize": "0.95rem"},
                                    )
                                ]
                            ),
                        ],
                        className="mb-3",
                    )
                    settings_cards.append(game_options_card)
            except Exception as e:
                logger.warning(f"Error formatting game options: {e}")

        # DLC Content - formatted as readable list
        if metadata.get("dlc_content"):
            try:
                dlc = (
                    json.loads(metadata["dlc_content"])
                    if isinstance(metadata["dlc_content"], str)
                    else metadata["dlc_content"]
                )
                if dlc:
                    # Format DLC names to be readable
                    dlc_items = []
                    for dlc_key in dlc.keys():
                        # Clean up the DLC name
                        clean_name = (
                            dlc_key.replace("DLC_", "").replace("_", " ").title()
                        )
                        dlc_items.append(clean_name)

                    dlc_card = dbc.Card(
                        [
                            dbc.CardHeader("DLC Content"),
                            dbc.CardBody(
                                [
                                    html.Ul(
                                        [html.Li(dlc) for dlc in sorted(dlc_items)],
                                        style={"fontSize": "0.95rem"},
                                    )
                                ]
                            ),
                        ],
                        className="mb-3",
                    )
                    settings_cards.append(dlc_card)
            except Exception as e:
                logger.warning(f"Error formatting DLC content: {e}")

        return html.Div(settings_cards)

    except Exception as e:
        logger.error(f"Error loading settings: {e}")
        return create_empty_state(
            f"Error loading settings: {str(e)}", icon="bi-exclamation-triangle"
        )


@callback(
    Output("match-final-laws-content", "children"),
    Input("match-details-tabs", "active_tab"),
    Input("match-selector", "value"),
    State("match-tabs-loaded-store", "data"),
    prevent_initial_call=True,
)
def update_final_laws(
    active_tab: Optional[str],
    match_id: Optional[int],
    loaded_state: Optional[Dict[str, Any]],
) -> html.Div:
    """Update final laws display by player.

    Args:
        active_tab: Currently active tab
        match_id: Selected match ID

    Returns:
        HTML content with player boxes containing laws
    """
    # Lazy loading: skip rendering if tab is not active
    if active_tab != "laws":
        raise dash.exceptions.PreventUpdate

    if not match_id:
        return html.Div("Select a match to view final laws", className="text-muted")

    try:
        queries = get_queries()

        # Get laws data
        laws_df = queries.get_cumulative_law_count_by_turn(match_id)

        if laws_df.empty:
            return html.Div("No law data available", className="text-muted")

        # Get final turn data for each player
        player_data = {}

        final_laws = laws_df.loc[laws_df.groupby("player_id")["turn_number"].idxmax()]
        for _, row in final_laws.iterrows():
            player_id = row["player_id"]
            player_data[player_id] = {
                "name": row["player_name"],
                "laws": [],
            }
            law_list_str = row.get("law_list", "")
            if law_list_str and pd.notna(law_list_str):
                laws = [law.strip() for law in str(law_list_str).split(",")]
                # Remove LAW_ prefix, quotes, humanize, deduplicate, and sort
                player_data[player_id]["laws"] = sorted(
                    set(
                        [
                            law.replace("LAW_", "")
                            .replace("_", " ")
                            .strip('"')
                            .strip("'")
                            .title()
                            for law in laws
                        ]
                    )
                )

        # Create player boxes
        player_cols = []
        for player_id in sorted(player_data.keys()):
            data = player_data[player_id]

            laws_items = (
                [html.Li(law, className="mb-1") for law in data["laws"]]
                if data["laws"]
                else [html.Span("No laws", className="text-muted")]
            )

            player_card = dbc.Card(
                [
                    dbc.CardHeader(html.H5(data["name"], className="mb-0")),
                    dbc.CardBody(
                        [
                            html.H6(
                                [
                                    "Laws ",
                                    dbc.Badge(
                                        len(data["laws"]),
                                        color="primary",
                                        pill=True,
                                    ),
                                ],
                                className="mb-2",
                            ),
                            html.Ul(
                                laws_items,
                                style={"fontSize": "0.9rem"},
                            ),
                        ]
                    ),
                ]
            )
            player_cols.append(dbc.Col(player_card, width=12 // len(player_data)))

        return dbc.Row(player_cols)

    except Exception as e:
        logger.error(f"Error loading final laws: {e}")
        return html.Div(f"Error loading data: {str(e)}", className="text-danger")


@callback(
    Output("match-final-techs-content", "children"),
    Input("match-selector", "value"),
)
def update_final_techs(match_id: Optional[int]) -> html.Div:
    """Update final technologies display by player.

    Args:
        match_id: Selected match ID

    Returns:
        HTML content with player boxes containing technologies
    """
    if not match_id:
        return html.Div(
            "Select a match to view final technologies", className="text-muted"
        )

    try:
        queries = get_queries()

        # Get techs data
        techs_df = queries.get_tech_count_by_turn(match_id)

        if techs_df.empty:
            return html.Div("No technology data available", className="text-muted")

        # Get final turn data for each player
        player_data = {}

        final_techs = techs_df.loc[
            techs_df.groupby("player_id")["turn_number"].idxmax()
        ]
        for _, row in final_techs.iterrows():
            player_id = row["player_id"]
            player_data[player_id] = {
                "name": row["player_name"],
                "techs": [],
            }
            tech_list_str = row.get("tech_list", "")
            if tech_list_str and pd.notna(tech_list_str):
                techs = [tech.strip() for tech in str(tech_list_str).split(",")]
                # Remove TECH_ prefix, quotes, humanize, and sort
                player_data[player_id]["techs"] = sorted(
                    [
                        tech.replace("TECH_", "")
                        .replace("_", " ")
                        .strip('"')
                        .strip("'")
                        .title()
                        for tech in techs
                    ]
                )

        # Create player boxes
        player_cols = []
        for player_id in sorted(player_data.keys()):
            data = player_data[player_id]

            techs_items = (
                [html.Li(tech, className="mb-1") for tech in data["techs"]]
                if data["techs"]
                else [html.Span("No technologies", className="text-muted")]
            )

            player_card = dbc.Card(
                [
                    dbc.CardHeader(html.H5(data["name"], className="mb-0")),
                    dbc.CardBody(
                        [
                            html.H6(
                                [
                                    "Technologies ",
                                    dbc.Badge(
                                        len(data["techs"]),
                                        color="success",
                                        pill=True,
                                    ),
                                ],
                                className="mb-2",
                            ),
                            html.Ul(
                                techs_items,
                                style={"fontSize": "0.9rem"},
                            ),
                        ]
                    ),
                ]
            )
            player_cols.append(dbc.Col(player_card, width=12 // len(player_data)))

        return dbc.Row(player_cols)

    except Exception as e:
        logger.error(f"Error loading final technologies: {e}")
        return html.Div(f"Error loading data: {str(e)}", className="text-danger")


@callback(
    Output("match-law-cumulative", "figure"),
    Input("match-details-tabs", "active_tab"),
    Input("match-selector", "value"),
    State("match-tabs-loaded-store", "data"),
    prevent_initial_call=True,
)
def update_law_cumulative(
    active_tab: Optional[str],
    match_id: Optional[int],
    loaded_state: Optional[Dict[str, Any]],
) -> go.Figure:
    """Update cumulative law count chart.

    Args:
        active_tab: Currently active tab
        match_id: Selected match ID

    Returns:
        Plotly figure with cumulative line chart
    """
    # Lazy loading: skip rendering if tab is not active
    if active_tab != "laws":
        raise dash.exceptions.PreventUpdate

    if not match_id:
        return create_empty_chart_placeholder("Select a match")

    try:
        queries = get_queries()
        df = queries.get_cumulative_law_count_by_turn(match_id)

        if df.empty:
            return create_empty_chart_placeholder("No law data for this match")

        # Get total turns for the match to extend lines to the end
        match_df = queries.get_match_summary()
        match_info = match_df[match_df["match_id"] == match_id]
        total_turns = (
            match_info.iloc[0]["total_turns"] if not match_info.empty else None
        )

        # Get player colors based on their civilizations
        player_colors = get_player_colors_for_match(match_id)

        return create_cumulative_law_count_chart(df, total_turns, player_colors)

    except Exception as e:
        logger.error(f"Error loading cumulative law count: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    # Generate outputs for all 14 yield charts dynamically
    [
        Output(f"match-{yield_type.lower().replace('_', '-')}-chart", "figure")
        for yield_type, _ in YIELD_TYPES
    ],
    Input("match-details-tabs", "active_tab"),
    Input("match-selector", "value"),
    State("match-tabs-loaded-store", "data"),
    prevent_initial_call=True,
)
def update_all_yield_charts(
    active_tab: Optional[str],
    match_id: Optional[int],
    loaded_state: Optional[Dict[str, Any]],
) -> List[go.Figure]:
    """Update all yield charts when a match is selected.

    Fetches data for all 14 yield types in a single query and creates
    individual charts for each yield type.

    Args:
        active_tab: Currently active tab
        match_id: Selected match ID
        loaded_state: Tab loading state from store

    Returns:
        List of 14 Plotly figures (one for each yield type)
    """
    # Lazy loading: skip rendering if tab is not active
    if active_tab != "yields":
        raise dash.exceptions.PreventUpdate

    # Skip re-fetching if tab was already loaded for this match
    if loaded_state and loaded_state.get("match_id") == match_id:
        if "yields" in loaded_state.get("loaded_tabs", []):
            raise dash.exceptions.PreventUpdate

    # If no match selected, return empty placeholders for all charts
    if not match_id:
        return [
            create_empty_chart_placeholder(
                f"Select a match to view {display_name} yields"
            )
            for _, display_name in YIELD_TYPES
        ]

    try:
        queries = get_queries()

        # SINGLE query fetches ALL yield data for the match
        all_yields_df = queries.get_yield_history_by_match(match_id)

        if all_yields_df.empty:
            return [
                create_empty_chart_placeholder(
                    f"No {display_name} yield data available"
                )
                for _, display_name in YIELD_TYPES
            ]

        # Check for actual cumulative totals (v1.0.81366+ saves)
        # These are ~30% more accurate because they include events, bonuses, etc.
        yield_total_df = None
        if queries.has_yield_total_history(match_id):
            yield_total_df = queries.get_yield_total_history_by_match(match_id)

        # Get total turns for the match to extend chart lines
        match_df = queries.get_match_summary()
        match_info = match_df[match_df["match_id"] == match_id]
        total_turns = (
            match_info.iloc[0]["total_turns"] if not match_info.empty else None
        )

        # Get player colors based on their civilizations
        player_colors = get_player_colors_from_df(all_yields_df)

        # Create all 14 charts from the same DataFrame
        charts = []
        for yield_type, display_name in YIELD_TYPES:
            # Filter to this specific yield type
            df_yield = all_yields_df[all_yields_df["resource_type"] == yield_type]

            # Filter cumulative totals for this yield type if available
            cumulative_df = None
            if yield_total_df is not None and not yield_total_df.empty:
                cumulative_df = yield_total_df[
                    yield_total_df["resource_type"] == yield_type
                ]

            # Create stacked chart with rate + cumulative (using nation colors)
            chart = create_match_yield_stacked_chart(
                df_yield,
                total_turns=total_turns,
                yield_type=yield_type,
                display_name=display_name,
                player_colors=player_colors,
                cumulative_df=cumulative_df,
            )
            charts.append(chart)

        return charts

    except Exception as e:
        logger.error(f"Error loading yield charts: {e}")
        # Return error charts for all yields
        return [
            create_empty_chart_placeholder(
                f"Error loading {display_name} yields: {str(e)}"
            )
            for _, display_name in YIELD_TYPES
        ]


# =============================================================================
# Science Tab Callbacks
# =============================================================================


@callback(
    Output("match-science-breakdown", "figure"),
    Input("match-details-tabs", "active_tab"),
    Input("match-selector", "value"),
    State("match-tabs-loaded-store", "data"),
    prevent_initial_call=True,
)
def update_science_breakdown_chart(
    active_tab: Optional[str],
    match_id: Optional[int],
    loaded_state: Optional[Dict[str, Any]],
) -> go.Figure:
    """Update science breakdown chart showing all sources.

    Args:
        active_tab: Currently active tab
        match_id: Selected match ID
        loaded_state: Tab loading state from store

    Returns:
        Plotly figure with stacked horizontal bar chart
    """
    if active_tab != "science":
        raise dash.exceptions.PreventUpdate

    if loaded_state and loaded_state.get("match_id") == match_id:
        if "science" in loaded_state.get("loaded_tabs", []):
            raise dash.exceptions.PreventUpdate

    if not match_id:
        return create_empty_chart_placeholder("Select a match to view science breakdown")

    try:
        queries = get_queries()
        breakdown_df = queries.get_science_breakdown_for_chart(match_id)

        if breakdown_df.empty:
            return create_empty_chart_placeholder("No science data available")

        player_colors = get_player_colors_for_match(match_id)
        return create_science_breakdown_chart(breakdown_df, player_colors)

    except Exception as e:
        logger.error(f"Error loading science breakdown: {e}")
        return create_empty_chart_placeholder("Error loading breakdown data")


@callback(
    Output("match-science-sources", "figure"),
    Input("match-details-tabs", "active_tab"),
    Input("match-selector", "value"),
    State("match-tabs-loaded-store", "data"),
    prevent_initial_call=True,
)
def update_science_sources_chart(
    active_tab: Optional[str],
    match_id: Optional[int],
    loaded_state: Optional[Dict[str, Any]],
) -> go.Figure:
    """Update detailed science sources chart.

    Args:
        active_tab: Currently active tab
        match_id: Selected match ID
        loaded_state: Tab loading state from store

    Returns:
        Plotly figure with grouped bar chart
    """
    if active_tab != "science":
        raise dash.exceptions.PreventUpdate

    if loaded_state and loaded_state.get("match_id") == match_id:
        if "science" in loaded_state.get("loaded_tabs", []):
            raise dash.exceptions.PreventUpdate

    if not match_id:
        return create_empty_chart_placeholder("Select a match to view science sources")

    try:
        queries = get_queries()
        infra_df = queries.get_science_infrastructure_summary(match_id)

        if infra_df.empty:
            return create_empty_chart_placeholder("No science infrastructure data")

        player_colors = get_player_colors_for_match(match_id)
        return create_science_sources_detail_chart(infra_df, player_colors)

    except Exception as e:
        logger.error(f"Error loading science sources: {e}")
        return create_empty_chart_placeholder("Error loading sources data")


@callback(
    Output("match-science-timeline", "figure"),
    Input("match-details-tabs", "active_tab"),
    Input("match-selector", "value"),
    State("match-tabs-loaded-store", "data"),
    prevent_initial_call=True,
)
def update_science_timeline_chart(
    active_tab: Optional[str],
    match_id: Optional[int],
    loaded_state: Optional[Dict[str, Any]],
) -> go.Figure:
    """Update stacked area chart for science infrastructure timeline.

    Args:
        active_tab: Currently active tab
        match_id: Selected match ID
        loaded_state: Tab loading state from store

    Returns:
        Plotly figure with stacked area chart
    """
    if active_tab != "science":
        raise dash.exceptions.PreventUpdate

    if loaded_state and loaded_state.get("match_id") == match_id:
        if "science" in loaded_state.get("loaded_tabs", []):
            raise dash.exceptions.PreventUpdate

    if not match_id:
        return create_empty_chart_placeholder("Select a match to view science timeline")

    try:
        queries = get_queries()
        df = queries.get_science_infrastructure_timeline(match_id)

        if df.empty:
            return create_empty_chart_placeholder("No science timeline data")

        player_colors = get_player_colors_for_match(match_id)
        return create_science_infrastructure_timeline(df, player_colors)

    except Exception as e:
        logger.error(f"Error loading science timeline: {e}")
        return create_empty_chart_placeholder("Error loading timeline data")


@callback(
    Output("match-legitimacy-progression", "figure"),
    Input("match-details-tabs", "active_tab"),
    Input("match-selector", "value"),
    State("match-tabs-loaded-store", "data"),
    prevent_initial_call=True,
)
def update_legitimacy_chart(
    active_tab: Optional[str],
    match_id: Optional[int],
    loaded_state: Optional[Dict[str, Any]],
) -> go.Figure:
    """Update legitimacy progression chart.

    Args:
        active_tab: Currently active tab
        match_id: Selected match ID

    Returns:
        Plotly figure with legitimacy progression
    """
    # Lazy loading: skip rendering if tab is not active
    if active_tab != "ambitions":
        raise dash.exceptions.PreventUpdate
    # Skip re-fetching if tab was already loaded for this match
    if loaded_state and loaded_state.get("match_id") == match_id:
        if "ambitions" in loaded_state.get("loaded_tabs", []):
            raise dash.exceptions.PreventUpdate
    # Skip re-fetching if tab was already loaded for this match
    if loaded_state and loaded_state.get("match_id") == match_id:
        if "ambitions" in loaded_state.get("loaded_tabs", []):
            raise dash.exceptions.PreventUpdate
    # Skip re-fetching if tab was already loaded for this match
    if loaded_state and loaded_state.get("match_id") == match_id:
        if "ambitions" in loaded_state.get("loaded_tabs", []):
            raise dash.exceptions.PreventUpdate
    # Skip re-fetching if tab was already loaded for this match
    if loaded_state and loaded_state.get("match_id") == match_id:
        if "ambitions" in loaded_state.get("loaded_tabs", []):
            raise dash.exceptions.PreventUpdate

    if not match_id:
        return create_empty_chart_placeholder("Select a match to view legitimacy")

    try:
        queries = get_queries()
        df = queries.get_legitimacy_history_by_match(match_id)

        if df.empty:
            return create_empty_chart_placeholder(
                "No legitimacy data available for this match"
            )

        return create_match_legitimacy_chart(df)

    except Exception as e:
        logger.error(f"Error loading legitimacy chart: {e}")
        return create_empty_chart_placeholder(f"Error loading legitimacy: {str(e)}")


@callback(
    Output("match-legitimacy-breakdown-container", "children"),
    Input("match-details-tabs", "active_tab"),
    Input("match-selector", "value"),
    State("match-tabs-loaded-store", "data"),
    prevent_initial_call=True,
)
def update_legitimacy_breakdown(
    active_tab: Optional[str],
    match_id: Optional[int],
    loaded_state: Optional[Dict[str, Any]],
) -> html.Div:
    """Update legitimacy breakdown showing cognomen contributions per ruler.

    Displays each player's legitimacy sources with events grouped under
    each ruler based on when they occurred during that ruler's reign.

    Args:
        active_tab: Currently active tab
        match_id: Selected match ID

    Returns:
        HTML Div containing breakdown cards for each player
    """
    # Lazy loading: skip rendering if tab is not active
    if active_tab != "ambitions":
        raise dash.exceptions.PreventUpdate

    if not match_id:
        return html.Div()

    try:
        queries = get_queries()

        # Get ruler data with cognomens
        rulers_df = queries.get_ruler_legitimacy_breakdown(match_id)

        # Get ambitions completed
        ambitions_df = queries.get_ambitions_completed_by_match(match_id)

        # Get legitimacy-related events with turn numbers
        events_df = queries.get_legitimacy_events_by_match(match_id)

        # Get legacies completed
        legacies_df = queries.get_legacies_completed_by_match(match_id)

        if rulers_df.empty:
            return html.Div(
                "No ruler data available for this match",
                className="text-muted text-center mt-3",
            )

        # Get unique player names and IDs
        players = rulers_df[["player_id", "player_name"]].drop_duplicates()

        # Create a card for each player
        player_cards = []
        for _, player_row in players.iterrows():
            player_id = player_row["player_id"]
            player_name = player_row["player_name"]

            # Get rulers for this player sorted by succession_order ASC (oldest first)
            player_rulers = rulers_df[rulers_df["player_id"] == player_id].sort_values(
                "succession_order", ascending=True
            )

            # Get events for this player, excluding legacy events
            player_events = events_df[events_df["player_id"] == player_id]
            player_events = player_events[
                ~player_events["event_type"].isin(
                    ["MEMORYFAMILY_OUR_LEGACY", "MEMORYRELIGION_OUR_LEGACY"]
                )
            ]

            # Build turn ranges for each ruler
            ruler_list = player_rulers.to_dict("records")
            for i, ruler in enumerate(ruler_list):
                ruler["start_turn"] = ruler["succession_turn"]
                if i + 1 < len(ruler_list):
                    ruler["end_turn"] = ruler_list[i + 1]["succession_turn"] - 1
                else:
                    ruler["end_turn"] = 9999  # Current ruler - no end

            # Pre-calculate ambitions and legacies for total
            player_ambitions = ambitions_df[ambitions_df["player_id"] == player_id]
            ambitions_count = 0
            if not player_ambitions.empty:
                ambitions_count = player_ambitions.iloc[0]["ambitions_completed"]
            legitimacy_per_ambition = 10
            ambitions_legitimacy = ambitions_count * legitimacy_per_ambition

            player_legacies = legacies_df[legacies_df["player_id"] == player_id]
            legacies_count = 0
            if not player_legacies.empty:
                legacies_count = player_legacies.iloc[0]["legacies_completed"]
            legitimacy_per_legacy = 5
            legacies_legitimacy = legacies_count * legitimacy_per_legacy

            # Calculate total from cognomens first
            total_from_cognomens = 0
            for ruler in ruler_list:
                cognomen = ruler["cognomen"]
                base_value = COGNOMEN_LEGITIMACY.get(cognomen, 0) if cognomen else 0
                decay_rate = get_cognomen_decay_rate(ruler["generations_ago"])
                total_from_cognomens += int(base_value * decay_rate)

            total_legitimacy = (
                total_from_cognomens + ambitions_legitimacy + legacies_legitimacy
            )

            # Build breakdown items with total at top
            breakdown_items = [
                html.Div(
                    html.Strong(f"Calculated Total: {total_legitimacy}"),
                    className="mb-2",
                ),
            ]

            # Add ambitions display right after total
            if ambitions_count > 0:
                breakdown_items.append(
                    html.Div(
                        [
                            html.Span(
                                f"+{ambitions_legitimacy}: ",
                                className="text-info fw-bold",
                            ),
                            html.Span(f"Ambitions Finished (x{ambitions_count})"),
                        ],
                        className="mb-1",
                    )
                )

            # Add legacies display
            if legacies_count > 0:
                breakdown_items.append(
                    html.Div(
                        [
                            html.Span(
                                f"+{legacies_legitimacy}: ",
                                className="text-info fw-bold",
                            ),
                            html.Span(f"Legacies Finished (x{legacies_count})"),
                        ],
                        className="mb-1",
                    )
                )

            # Separator before ruler breakdown
            breakdown_items.append(html.Hr(className="my-2"))

            # Process rulers in reverse order (current ruler first for display)
            for ruler in reversed(ruler_list):
                cognomen = ruler["cognomen"]
                ruler_name = ruler["ruler_name"]
                generations_ago = ruler["generations_ago"]
                start_turn = ruler["start_turn"]
                end_turn = ruler["end_turn"]

                # Get base legitimacy value for this cognomen
                base_value = COGNOMEN_LEGITIMACY.get(cognomen, 0) if cognomen else 0

                # Calculate decayed value
                decay_rate = get_cognomen_decay_rate(generations_ago)
                decayed_value = int(base_value * decay_rate)
                total_from_cognomens += decayed_value

                # Format display name (e.g., "King Kurigalzu the Great")
                display_cognomen = (
                    COGNOMEN_DISPLAY_NAMES.get(cognomen, f"the {cognomen}")
                    if cognomen
                    else ""
                )
                ruler_display = (
                    f"{ruler_name} {display_cognomen}".strip()
                    if display_cognomen
                    else ruler_name
                )

                # Add decay indicator for previous rulers
                decay_note = " (decayed)" if generations_ago > 0 else ""

                # Create ruler header with cognomen value
                value_color = "text-info" if decayed_value >= 0 else "text-danger"
                value_prefix = "+" if decayed_value >= 0 else ""

                breakdown_items.append(
                    html.Div(
                        [
                            html.Span(
                                f"{value_prefix}{decayed_value}: ",
                                className=f"{value_color} fw-bold",
                            ),
                            html.Span(f"{ruler_display}"),
                            html.Span(
                                decay_note,
                                className="text-muted small",
                            ),
                        ],
                        className="mb-1",
                    )
                )

                # Get events during this ruler's reign
                ruler_events = player_events[
                    (player_events["turn_number"] >= start_turn)
                    & (player_events["turn_number"] <= end_turn)
                ]

                if not ruler_events.empty:
                    # Aggregate events by type for this ruler
                    event_counts = (
                        ruler_events.groupby("event_type")["count"].sum().reset_index()
                    )
                    event_counts = event_counts.sort_values("count", ascending=False)

                    for _, event_row in event_counts.iterrows():
                        event_type = event_row["event_type"]
                        count = event_row["count"]
                        display_name = format_event_type_display(event_type)

                        count_str = f" (x{count})" if count > 1 else ""
                        breakdown_items.append(
                            html.Div(
                                f"• {display_name}{count_str}",
                                className="text-muted small ms-3",
                            )
                        )

            # Create card for this player
            player_cards.append(
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                html.H6(player_name, className="mb-0"),
                            ),
                            dbc.CardBody(
                                breakdown_items,
                                className="small",
                            ),
                        ],
                        className="h-100",
                    ),
                    md=6,
                    className="mb-3",
                )
            )

        return dbc.Row(
            player_cards,
            className="mt-3",
        )

    except Exception as e:
        logger.error(f"Error loading legitimacy breakdown: {e}")
        return html.Div(
            f"Error loading legitimacy breakdown: {str(e)}",
            className="text-danger text-center mt-3",
        )


@callback(
    Output("match-ambition-timelines-container", "children"),
    Input("match-details-tabs", "active_tab"),
    Input("match-selector", "value"),
    State("match-tabs-loaded-store", "data"),
    prevent_initial_call=True,
)
def update_ambition_timelines(
    active_tab: Optional[str],
    match_id: Optional[int],
    loaded_state: Optional[Dict[str, Any]],
):
    """Update ambition timeline charts - one per player.

    Args:
        active_tab: Currently active tab
        match_id: Selected match ID

    Returns:
        HTML Div containing separate chart cards for each player
    """
    # Lazy loading: skip rendering if tab is not active
    if active_tab != "ambitions":
        raise dash.exceptions.PreventUpdate

    if not match_id:
        return html.Div(
            "Select a match to view ambition timelines", className="text-muted"
        )

    try:
        queries = get_queries()
        df = queries.get_ambition_timeline(match_id)

        if df.empty:
            return html.Div(
                "No ambition data available for this match", className="text-muted"
            )

        # Get unique players
        players = df["player_name"].unique()

        # Create a separate chart for each player
        chart_rows = []
        for player in players:
            player_df = df[df["player_name"] == player]
            fig = create_ambition_timeline_chart(player_df)

            chart_row = dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        html.H5(
                                            f"{player} - Ambitions", className="mb-0"
                                        )
                                    ),
                                    dbc.CardBody(
                                        [dcc.Graph(figure=fig, config=MODEBAR_CONFIG)]
                                    ),
                                ],
                                className="mb-3",
                            )
                        ],
                        width=12,
                    )
                ],
                className="mb-3",
            )
            chart_rows.append(chart_row)

        return html.Div(chart_rows)

    except Exception as e:
        logger.error(f"Error loading ambition timelines: {e}")
        return html.Div(
            f"Error loading ambition timelines: {str(e)}", className="text-danger"
        )


@callback(
    Output("match-ambition-summary", "figure"),
    Input("match-details-tabs", "active_tab"),
    Input("match-selector", "value"),
    State("match-tabs-loaded-store", "data"),
    prevent_initial_call=True,
)
def update_ambition_summary(
    active_tab: Optional[str],
    match_id: Optional[int],
    loaded_state: Optional[Dict[str, Any]],
) -> go.Figure:
    """Update ambition summary table.

    Args:
        active_tab: Currently active tab
        match_id: Selected match ID

    Returns:
        Plotly figure for ambition summary table
    """
    # Lazy loading: skip rendering if tab is not active
    if active_tab != "ambitions":
        raise dash.exceptions.PreventUpdate

    if not match_id:
        return create_empty_chart_placeholder("Select a match to view ambition summary")

    try:
        queries = get_queries()
        df = queries.get_ambition_summary(match_id)

        if df.empty:
            return create_empty_chart_placeholder(
                "No ambition data available for this match"
            )

        return create_ambition_summary_table(df)

    except Exception as e:
        logger.error(f"Error loading ambition summary: {e}")
        return create_empty_chart_placeholder(
            f"Error loading ambition summary: {str(e)}"
        )


@callback(
    Output("match-family-city-panels", "children"),
    Input("match-selector", "value"),
)
def update_family_city_panels(match_id: Optional[int]) -> dbc.Row:
    """Update family city distribution panels for each player.

    Shows which families each player has and how many cities per family.

    Args:
        match_id: Selected match ID

    Returns:
        Row with player panels showing family city counts
    """
    if not match_id:
        return html.Div()

    try:
        queries = get_queries()
        df = queries.get_family_city_counts(match_id)

        if df.empty:
            return html.Div()

        # Get player names in order
        players = df["player_name"].unique()

        player_cols = []
        for player in sorted(players):
            player_data = df[df["player_name"] == player]

            # Build family list with class and count
            family_items = []
            total_cities = 0
            for _, row in player_data.iterrows():
                family_display = format_family_display_name(row["family_name"])
                family_class = get_family_class(row["family_name"])
                city_count = int(row["city_count"])
                total_cities += city_count
                family_items.append(
                    html.Li(
                        f"{family_display} ({family_class}): {city_count}",
                        className="mb-1",
                    )
                )

            player_card = dbc.Card(
                [
                    dbc.CardHeader(
                        html.H6(
                            [
                                f"{player} - Families ",
                                dbc.Badge(
                                    f"{total_cities} cities",
                                    color="info",
                                    pill=True,
                                ),
                            ],
                            className="mb-0",
                        )
                    ),
                    dbc.CardBody(
                        html.Ul(
                            (
                                family_items
                                if family_items
                                else [
                                    html.Span("No family data", className="text-muted")
                                ]
                            ),
                            style={"fontSize": "0.9rem", "marginBottom": "0"},
                            className="ps-3",
                        ),
                        className="py-2",
                    ),
                ],
                className="h-100",
            )
            player_cols.append(dbc.Col(player_card, width=12 // len(players)))

        return dbc.Row(player_cols)

    except Exception as e:
        logger.error(f"Error loading family city panels: {e}")
        return html.Div(f"Error loading data: {str(e)}", className="text-danger")


@callback(
    Output("match-cumulative-city-count", "figure"),
    Input("match-selector", "value"),
)
def update_cumulative_city_count(match_id: Optional[int]) -> go.Figure:
    """Update cumulative city count chart.

    Args:
        match_id: Selected match ID

    Returns:
        Plotly figure with cumulative city count
    """
    if not match_id:
        return create_empty_chart_placeholder(
            "Select a match to view cumulative city count"
        )

    try:
        queries = get_queries()
        df = queries.get_city_founding_timeline(match_id)

        if df.empty:
            return create_empty_chart_placeholder(
                "No city founding data available for this match"
            )

        # Get total turns for the match to extend lines to the end
        match_df = queries.get_match_summary()
        match_info = match_df[match_df["match_id"] == match_id]
        total_turns = (
            match_info.iloc[0]["total_turns"] if not match_info.empty else None
        )

        # Get player colors based on their civilizations
        player_colors = get_player_colors_for_match(match_id)

        return create_cumulative_city_count_chart(df, total_turns, player_colors)

    except Exception as e:
        logger.error(f"Error loading cumulative city count: {e}")
        return create_empty_chart_placeholder(
            f"Error loading cumulative city count: {str(e)}"
        )


@callback(
    Output("match-city-founding-scatter", "figure"),
    Input("match-selector", "value"),
)
def update_city_founding_scatter(match_id: Optional[int]) -> go.Figure:
    """Update city founding scatter plot with jitter.

    Args:
        match_id: Selected match ID

    Returns:
        Plotly figure with city founding scatter plot
    """
    if not match_id:
        return create_empty_chart_placeholder(
            "Select a match to view city founding detail"
        )

    try:
        queries = get_queries()
        df = queries.get_city_founding_timeline(match_id)

        if df.empty:
            return create_empty_chart_placeholder(
                "No city founding data available for this match"
            )

        # Get player colors based on their civilizations
        player_colors = get_player_colors_for_match(match_id)

        return create_city_founding_scatter_jitter_chart(df, player_colors)

    except Exception as e:
        logger.error(f"Error loading city founding scatter: {e}")
        return create_empty_chart_placeholder(
            f"Error loading city founding detail: {str(e)}"
        )


@callback(
    Output("match-pixi-map-iframe", "src"),
    Input("match-details-tabs", "active_tab"),
    Input("match-selector", "value"),
    prevent_initial_call=True,
)
def update_pixi_map_iframe(
    active_tab: Optional[str],
    match_id: Optional[int],
) -> str:
    """Update Pixi.js map iframe src when Map tab is selected.

    Args:
        active_tab: Currently active tab
        match_id: Selected match ID

    Returns:
        URL for the Pixi.js map viewer iframe
    """
    # Only load when Map tab is active
    if active_tab != "map":
        raise dash.exceptions.PreventUpdate

    if not match_id:
        return ""

    # Return URL to Flask map viewer route
    return f"/map/viewer/{match_id}"


@callback(
    Output("match-territory-timeline-chart", "figure"),
    Input("match-details-tabs", "active_tab"),
    Input("match-selector", "value"),
    State("match-tabs-loaded-store", "data"),
    prevent_initial_call=True,
)
def update_match_territory_timeline_chart(
    active_tab: Optional[str],
    match_id: Optional[int],
    loaded_state: Optional[Dict[str, Any]],
):
    """Update territory timeline chart.

    Args:
        active_tab: Currently active tab
        match_id: Selected match ID

    Returns:
        Plotly figure for territory timeline
    """
    # Lazy loading: skip rendering if tab is not active
    if active_tab != "cities":
        raise dash.exceptions.PreventUpdate

    if not match_id:
        return create_empty_chart_placeholder(
            "Select a match to view territory control"
        )

    try:
        queries = get_queries()
        df = queries.get_territory_control_summary(match_id)

        if df.empty:
            return create_empty_chart_placeholder(
                "No territory data available for this match"
            )

        # Get player colors based on their civilizations
        player_colors = get_player_colors_for_match(match_id)

        return create_territory_control_chart(df, player_colors)

    except Exception as e:
        logger.error(f"Error loading territory timeline: {e}")
        return create_empty_chart_placeholder(
            f"Error loading territory timeline: {str(e)}"
        )


@callback(
    Output("match-territory-distribution-chart", "figure"),
    Input("match-details-tabs", "active_tab"),
    Input("match-selector", "value"),
    State("match-tabs-loaded-store", "data"),
    prevent_initial_call=True,
)
def update_match_territory_distribution_chart(
    active_tab: Optional[str],
    match_id: Optional[int],
    loaded_state: Optional[Dict[str, Any]],
):
    """Update territory distribution chart.

    Args:
        active_tab: Currently active tab
        match_id: Selected match ID

    Returns:
        Plotly figure for territory distribution
    """
    # Lazy loading: skip rendering if tab is not active
    if active_tab != "cities":
        raise dash.exceptions.PreventUpdate

    if not match_id:
        return create_empty_chart_placeholder("Select a match")

    try:
        queries = get_queries()
        df = queries.get_territory_control_summary(match_id)

        if df.empty:
            return create_empty_chart_placeholder("No territory data available")

        # Get final turn data, excluding unowned territories (NULL player names)
        final_turn = df["turn_number"].max()
        final_data = df[(df["turn_number"] == final_turn) & (df["player_name"].notna())]

        # Get nation colors for players
        player_colors = get_player_colors_for_match(match_id)
        colors = [
            player_colors.get(
                name, Config.PRIMARY_COLORS[i % len(Config.PRIMARY_COLORS)]
            )
            for i, name in enumerate(final_data["player_name"])
        ]

        fig = create_base_figure(show_legend=False)

        fig.add_trace(
            go.Pie(
                labels=final_data["player_name"],
                values=final_data["controlled_territories"],
                hole=0.3,
                marker_colors=colors,
            )
        )

        return fig

    except Exception as e:
        logger.error(f"Error loading territory distribution: {e}")
        return create_empty_chart_placeholder(
            f"Error loading territory distribution: {str(e)}"
        )


@callback(
    Output("match-improvements-section", "children"),
    Input("match-details-tabs", "active_tab"),
    Input("match-selector", "value"),
    State("match-tabs-loaded-store", "data"),
    prevent_initial_call=True,
)
def update_match_improvements_section(
    active_tab: Optional[str],
    match_id: Optional[int],
    loaded_state: Optional[Dict[str, Any]],
) -> html.Div:
    """Update improvements section showing improvement counts per player.

    Args:
        active_tab: Currently active tab
        match_id: Selected match ID

    Returns:
        HTML div with butterfly chart comparing improvement counts
    """
    # Lazy loading: skip rendering if tab is not active
    if active_tab != "improvements":
        raise dash.exceptions.PreventUpdate

    if not match_id:
        return html.Div()

    try:
        queries = get_queries()
        df = queries.get_improvement_counts_by_player(match_id)

        # Get player colors for styling
        player_colors = get_player_colors_for_match(match_id)

        # Create butterfly chart
        fig = create_improvement_butterfly_chart(df, player_colors)

        return html.Div(
            [
                html.H5("Improvements", className="mb-3"),
                dcc.Graph(
                    figure=fig,
                    config={"displayModeBar": False},
                    style={"width": "100%"},
                ),
            ]
        )

    except Exception as e:
        logger.error(f"Error loading improvements section: {e}")
        return dbc.Card(
            dbc.CardBody(
                html.P(
                    f"Error loading improvements: {str(e)}",
                    className="text-danger text-center mb-0",
                )
            ),
            className="mt-3",
        )


@callback(
    Output("match-specialists-section", "children"),
    Input("match-details-tabs", "active_tab"),
    Input("match-selector", "value"),
    State("match-tabs-loaded-store", "data"),
    prevent_initial_call=True,
)
def update_match_specialists_section(
    active_tab: Optional[str],
    match_id: Optional[int],
    loaded_state: Optional[Dict[str, Any]],
) -> html.Div:
    """Update specialists section showing specialist counts per player.

    Args:
        active_tab: Currently active tab
        match_id: Selected match ID

    Returns:
        HTML div with butterfly chart comparing specialist counts
    """
    # Lazy loading: skip rendering if tab is not active
    if active_tab != "improvements":
        raise dash.exceptions.PreventUpdate

    if not match_id:
        return html.Div()

    try:
        queries = get_queries()
        df = queries.get_specialist_counts_by_player(match_id)

        # Get player colors for styling
        player_colors = get_player_colors_for_match(match_id)

        # Create butterfly chart
        fig = create_specialist_butterfly_chart(df, player_colors)

        return html.Div(
            [
                html.H5("Specialists", className="mb-3"),
                dcc.Graph(
                    figure=fig,
                    config={"displayModeBar": False},
                    style={"width": "100%"},
                ),
            ]
        )

    except Exception as e:
        logger.error(f"Error loading specialists section: {e}")
        return dbc.Card(
            dbc.CardBody(
                html.P(
                    f"Error loading specialists: {str(e)}",
                    className="text-danger text-center mb-0",
                )
            ),
            className="mt-3",
        )


# =============================================================================
# Unit Composition Callbacks
# =============================================================================


@callback(
    Output("match-military-power", "figure"),
    Input("match-details-tabs", "active_tab"),
    Input("match-selector", "value"),
    State("match-tabs-loaded-store", "data"),
    prevent_initial_call=True,
)
def update_military_power_chart(
    active_tab: Optional[str],
    match_id: Optional[int],
    loaded_state: Optional[Dict[str, Any]],
) -> go.Figure:
    """Update military power progression chart.

    Args:
        active_tab: Currently active tab
        match_id: Selected match ID

    Returns:
        Plotly figure with military power line chart
    """
    # Lazy loading: skip rendering if tab is not active
    if active_tab != "military":
        raise dash.exceptions.PreventUpdate
    # Skip re-fetching if tab was already loaded for this match
    if loaded_state and loaded_state.get("match_id") == match_id:
        if "military" in loaded_state.get("loaded_tabs", []):
            raise dash.exceptions.PreventUpdate

    if not match_id:
        return create_empty_chart_placeholder("Select a match to view military power")

    try:
        queries = get_queries()
        df = queries.get_military_history_by_match(match_id)

        if df.empty:
            return create_empty_chart_placeholder(
                "No military power data available for this match"
            )

        return create_military_power_chart(df)

    except Exception as e:
        logger.error(f"Error loading military power chart: {e}")
        return create_empty_chart_placeholder(f"Error loading military power: {str(e)}")


@callback(
    [
        Output("match-units-stacked-bar", "figure"),
        Output("match-units-grouped-bar", "figure"),
        Output("match-units-waffle", "figure"),
        Output("match-units-treemap", "figure"),
        Output("match-units-icon-grid", "figure"),
        Output("match-units-portrait", "figure"),
        Output("match-units-marimekko", "figure"),
    ],
    Input("match-details-tabs", "active_tab"),
    Input("match-selector", "value"),
    State("match-tabs-loaded-store", "data"),
    prevent_initial_call=True,
)
def update_all_unit_charts(
    active_tab: Optional[str],
    match_id: Optional[int],
    loaded_state: Optional[Dict[str, Any]],
) -> List[go.Figure]:
    """Update all unit composition charts when a match is selected.

    Fetches unit data once and creates all 7 chart types.

    Args:
        active_tab: Currently active tab
        match_id: Selected match ID
        loaded_state: Tab loading state from store

    Returns:
        List of 7 Plotly figures for unit charts
    """
    # Lazy loading: skip rendering if tab is not active
    if active_tab != "military":
        raise dash.exceptions.PreventUpdate

    # Skip re-fetching if tab was already loaded for this match
    if loaded_state and loaded_state.get("match_id") == match_id:
        if "military" in loaded_state.get("loaded_tabs", []):
            raise dash.exceptions.PreventUpdate

    empty_placeholder = create_empty_chart_placeholder(
        "Select a match to view unit data"
    )

    if not match_id:
        return [empty_placeholder] * 7

    try:
        queries = get_queries()
        df = queries.get_match_units_produced(match_id)

        if df.empty:
            no_data = create_empty_chart_placeholder(
                "No unit data available for this match"
            )
            return [no_data] * 7

        # Get player colors for nation-based coloring
        player_colors = get_player_colors_for_match(match_id)

        # Create all 7 charts from the same DataFrame
        return [
            create_units_stacked_bar_chart(df),
            create_units_grouped_bar_chart(df, player_colors),
            create_units_waffle_chart(df),
            create_units_treemap_chart(df),
            create_units_icon_grid(df),
            create_units_army_portrait(df),
            create_units_marimekko_chart(df),
        ]

    except Exception as e:
        logger.error(f"Error loading unit charts: {e}")
        error_fig = create_empty_chart_placeholder(f"Error loading unit data: {str(e)}")
        return [error_fig] * 7


@callback(
    Output("match-units-list-content", "children"),
    Input("match-selector", "value"),
)
def update_units_list(match_id: Optional[int]) -> html.Div:
    """Update unit listing by player, split into Military and Non-Military.

    Args:
        match_id: Selected match ID

    Returns:
        HTML content with player boxes containing unit lists
    """
    if not match_id:
        return html.Div("Select a match to view unit details", className="text-muted")

    try:
        queries = get_queries()
        df = queries.get_match_units_produced(match_id)

        if df.empty:
            return html.Div("No unit data available", className="text-muted")

        # Group by player
        players = df["player_name"].unique()

        player_cols = []
        for player in sorted(players):
            player_data = df[df["player_name"] == player]

            # Split into military and non-military
            military_data = player_data[player_data["category"] == "military"]
            non_military_data = player_data[player_data["category"] != "military"]

            # Build military list with counts
            military_items = []
            for _, row in military_data.sort_values("unit_name").iterrows():
                unit_display = row["unit_name"].title()
                military_items.append(
                    html.Li(f"{unit_display} ({row['count']})", className="mb-1")
                )

            # Build non-military list with counts
            non_military_items = []
            for _, row in non_military_data.sort_values("unit_name").iterrows():
                unit_display = row["unit_name"].title()
                non_military_items.append(
                    html.Li(f"{unit_display} ({row['count']})", className="mb-1")
                )

            # Calculate totals
            military_total = int(military_data["count"].sum())
            non_military_total = int(non_military_data["count"].sum())

            player_card = dbc.Card(
                [
                    dbc.CardHeader(html.H5(player, className="mb-0")),
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.H6(
                                                [
                                                    "Military ",
                                                    dbc.Badge(
                                                        military_total,
                                                        color="danger",
                                                        pill=True,
                                                    ),
                                                ],
                                                className="mb-2",
                                            ),
                                            html.Ul(
                                                (
                                                    military_items
                                                    if military_items
                                                    else [
                                                        html.Span(
                                                            "No military units",
                                                            className="text-muted",
                                                        )
                                                    ]
                                                ),
                                                style={"fontSize": "0.9rem"},
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            html.H6(
                                                [
                                                    "Non-Military ",
                                                    dbc.Badge(
                                                        non_military_total,
                                                        color="success",
                                                        pill=True,
                                                    ),
                                                ],
                                                className="mb-2",
                                            ),
                                            html.Ul(
                                                (
                                                    non_military_items
                                                    if non_military_items
                                                    else [
                                                        html.Span(
                                                            "No non-military units",
                                                            className="text-muted",
                                                        )
                                                    ]
                                                ),
                                                style={"fontSize": "0.9rem"},
                                            ),
                                        ],
                                        width=6,
                                    ),
                                ]
                            )
                        ]
                    ),
                ]
            )
            player_cols.append(dbc.Col(player_card, width=12 // len(players)))

        return dbc.Row(player_cols)

    except Exception as e:
        logger.error(f"Error loading unit list: {e}")
        return html.Div(f"Error loading data: {str(e)}", className="text-danger")


# ============================================================================
# Tech Tree Callbacks
# ============================================================================


@callback(
    [
        Output("match-tech-tree-player1", "elements"),
        Output("match-tech-tree-player2", "elements"),
        Output("match-tech-tree-player1-header", "children"),
        Output("match-tech-tree-player2-header", "children"),
        Output("match-tech-tree-turn-slider", "max"),
        Output("match-tech-tree-turn-slider", "value"),
        Output("match-tech-tree-turn-slider", "marks"),
    ],
    Input("match-selector", "value"),
)
def update_tech_tree_controls(match_id: Optional[int]):
    """Initialize tech trees and configure turn slider for selected match.

    Args:
        match_id: Selected match ID

    Returns:
        Tuple of (player1_elements, player2_elements, player1_header,
                  player2_header, slider_max, slider_value, slider_marks)
    """
    empty_elements: List[Dict[str, Any]] = []
    default_marks = {i: str(i) for i in range(0, 101, 25)}

    if not match_id:
        return (
            empty_elements,
            empty_elements,
            "Player 1",
            "Player 2",
            100,
            100,
            default_marks,
        )

    try:
        queries = get_queries()

        # Get tech timeline for this match
        tech_df = queries.get_tech_timeline(match_id)

        if tech_df.empty:
            return (
                empty_elements,
                empty_elements,
                "No tech data",
                "No tech data",
                100,
                100,
                default_marks,
            )

        # Get player info
        players = (
            tech_df[["player_id", "player_name"]].drop_duplicates().values.tolist()
        )
        if len(players) < 2:
            # Pad with empty player if only one found
            players.append((None, "Player 2"))

        player1_id, player1_name = players[0]
        player2_id, player2_name = (
            players[1] if len(players) > 1 else (None, "Player 2")
        )

        # Get max turn from tech discoveries
        max_turn = int(tech_df["turn_number"].max())
        min_turn = int(tech_df["turn_number"].min())

        # Get techs at final turn for initial view
        player1_techs = get_techs_at_turn(tech_df, player1_id, max_turn)
        player2_techs = (
            get_techs_at_turn(tech_df, player2_id, max_turn) if player2_id else set()
        )

        # Build elements
        player1_elements = build_cytoscape_elements(player1_techs)
        player2_elements = build_cytoscape_elements(player2_techs)

        # Build headers with tech counts
        total_techs = len(TECHS)
        player1_header = f"{player1_name} ({len(player1_techs)}/{total_techs} techs)"
        player2_header = f"{player2_name} ({len(player2_techs)}/{total_techs} techs)"

        # Configure slider marks
        mark_step = max(1, max_turn // 10)
        marks = {i: str(i) for i in range(min_turn, max_turn + 1, mark_step)}
        marks[min_turn] = str(min_turn)
        marks[max_turn] = str(max_turn)

        return (
            player1_elements,
            player2_elements,
            player1_header,
            player2_header,
            max_turn,
            max_turn,
            marks,
        )

    except Exception as e:
        logger.error(f"Error initializing tech trees: {e}")
        return (
            empty_elements,
            empty_elements,
            "Error",
            "Error",
            100,
            100,
            default_marks,
        )


@callback(
    [
        Output("match-tech-tree-player1", "elements", allow_duplicate=True),
        Output("match-tech-tree-player2", "elements", allow_duplicate=True),
        Output("match-tech-tree-player1-header", "children", allow_duplicate=True),
        Output("match-tech-tree-player2-header", "children", allow_duplicate=True),
    ],
    [
        Input("match-selector", "value"),
        Input("match-tech-tree-turn-slider", "value"),
    ],
    prevent_initial_call=True,
)
def update_tech_trees_for_turn(
    match_id: Optional[int],
    turn_number: int,
) -> tuple:
    """Update tech trees when turn slider changes.

    Args:
        match_id: Selected match ID
        turn_number: Turn number from slider

    Returns:
        Tuple of (player1_elements, player2_elements, player1_header, player2_header)
    """
    empty_elements: List[Dict[str, Any]] = []

    if not match_id or turn_number is None:
        return empty_elements, empty_elements, "Player 1", "Player 2"

    try:
        queries = get_queries()

        # Get tech timeline for this match
        tech_df = queries.get_tech_timeline(match_id)

        if tech_df.empty:
            return empty_elements, empty_elements, "No data", "No data"

        # Get player info
        players = (
            tech_df[["player_id", "player_name"]].drop_duplicates().values.tolist()
        )
        if len(players) < 2:
            players.append((None, "Player 2"))

        player1_id, player1_name = players[0]
        player2_id, player2_name = (
            players[1] if len(players) > 1 else (None, "Player 2")
        )

        # Get techs at specified turn
        player1_techs = get_techs_at_turn(tech_df, player1_id, turn_number)
        player2_techs = (
            get_techs_at_turn(tech_df, player2_id, turn_number) if player2_id else set()
        )

        # Build elements
        player1_elements = build_cytoscape_elements(player1_techs)
        player2_elements = build_cytoscape_elements(player2_techs)

        # Build headers with tech counts
        total_techs = len(TECHS)
        player1_header = f"{player1_name} ({len(player1_techs)}/{total_techs} techs)"
        player2_header = f"{player2_name} ({len(player2_techs)}/{total_techs} techs)"

        return player1_elements, player2_elements, player1_header, player2_header

    except Exception as e:
        logger.error(f"Error updating tech trees for turn: {e}")
        return empty_elements, empty_elements, "Error", "Error"


# =============================================================================
# Overview (Beta) - Match Card Callback
# =============================================================================


@callback(
    Output("match-overview-content", "children"),
    Input("match-details-tabs", "active_tab"),
    Input("match-selector", "value"),
)
def update_overview_beta(
    active_tab: Optional[str],
    match_id: Optional[int],
) -> html.Div:
    """Update the Overview (Beta) Match Card content.

    Args:
        active_tab: Currently active tab ID
        match_id: Selected match ID

    Returns:
        Match Card layout component
    """
    # Lazy loading - only update when Overview (Beta) tab is active
    if active_tab != "overview":
        raise dash.exceptions.PreventUpdate

    if not match_id:
        return create_empty_state(
            title="Select a Match",
            message="Choose a match from the dropdown to view the match card.",
            icon="bi-card-heading",
        )

    try:
        queries = get_queries()

        # Fetch all required data
        points_df = queries.get_points_history_by_match(match_id)
        military_df = queries.get_military_history_by_match(match_id)
        events_df = queries.get_match_timeline_events(match_id)
        yield_df = queries.get_yield_history_by_match(match_id)
        cities_df = queries.get_match_cities(match_id)
        expansion_df = queries.get_player_expansion_stats(match_id)
        units_df = queries.get_match_units_produced(match_id)
        law_df = queries.get_law_timeline(match_id)

        # Get actual cumulative totals if available (v1.0.81366+ saves)
        # These are ~30% more accurate because they include events, bonuses, etc.
        yield_total_df = None
        if queries.has_yield_total_history(match_id):
            yield_total_df = queries.get_yield_total_history_by_match(match_id)

        # Get match summary for metadata
        match_summary_df = queries.get_match_summary()
        match_info = match_summary_df[match_summary_df["match_id"] == match_id]

        if match_info.empty:
            return create_empty_state(
                title="Match Not Found",
                message="Unable to load match metadata.",
                icon="bi-exclamation-circle",
            )

        match_row = match_info.iloc[0]
        total_turns = int(match_row.get("total_turns", 0))
        winner_name_from_summary = str(match_row.get("winner_name", "Unknown"))

        # Get player info from yield_df which has player_id, player_name, civilization
        player1_id = 0
        player2_id = 0
        player1_name = "Player 1"
        player2_name = "Player 2"
        player1_civ = "Unknown"
        player2_civ = "Unknown"

        if not yield_df.empty and "player_id" in yield_df.columns:
            player_info = (
                yield_df[["player_id", "player_name", "civilization"]]
                .drop_duplicates()
                .sort_values("player_id")
            )
            if len(player_info) >= 1:
                p1 = player_info.iloc[0]
                player1_id = int(p1["player_id"])
                player1_name = str(p1["player_name"] or "Player 1")
                player1_civ = str(p1["civilization"] or "Unknown")
            if len(player_info) >= 2:
                p2 = player_info.iloc[1]
                player2_id = int(p2["player_id"])
                player2_name = str(p2["player_name"] or "Player 2")
                player2_civ = str(p2["civilization"] or "Unknown")
        elif not events_df.empty and "player_id" in events_df.columns:
            # Fall back to events_df
            player_ids = sorted(events_df["player_id"].dropna().unique())
            if len(player_ids) >= 1:
                player1_id = int(player_ids[0])
            if len(player_ids) >= 2:
                player2_id = int(player_ids[1])

            # Try to get names from events
            if "player_name" in events_df.columns:
                for _, row in events_df[["player_id", "player_name"]].drop_duplicates().iterrows():
                    if row["player_id"] == player1_id:
                        player1_name = str(row["player_name"] or "Player 1")
                    elif row["player_id"] == player2_id:
                        player2_name = str(row["player_name"] or "Player 2")

        # Determine winner
        winner_player_id = None
        winner_name = winner_name_from_summary

        # Match winner name to player ID
        if winner_name_from_summary and winner_name_from_summary != "Unknown":
            if winner_name_from_summary == player1_name:
                winner_player_id = player1_id
            elif winner_name_from_summary == player2_name:
                winner_player_id = player2_id

        # Run the analysis
        analysis = analyze_match(
            match_id=match_id,
            points_df=points_df,
            military_df=military_df,
            events_df=events_df,
            yield_df=yield_df,
            cities_df=cities_df,
            expansion_df=expansion_df,
            units_df=units_df,
            law_df=law_df,
            total_turns=total_turns,
            winner_player_id=winner_player_id,
            winner_name=winner_name,
            player_ids=(player1_id, player2_id),
            player_names=(player1_name, player2_name),
            civilizations=(player1_civ, player2_civ),
            yield_total_df=yield_total_df,
        )

        # Create and return the layout
        return create_match_card_layout(analysis)

    except Exception as e:
        logger.error(f"Error creating match card: {e}")
        return create_empty_state(
            title="Error Loading Match Card",
            message=f"An error occurred: {str(e)}",
            icon="bi-exclamation-triangle",
        )
