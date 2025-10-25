"""Individual match analysis page.

This page provides detailed analysis of specific tournament matches including
turn progression, resource development, and event timelines.
"""

import logging
from typing import Any, Dict, List, Optional

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, callback, dcc, html
from plotly import graph_objects as go

from tournament_visualizer.components.charts import (
    create_ambition_summary_table,
    create_ambition_timeline_chart,
    create_cumulative_law_count_chart,
    create_cumulative_tech_count_chart,
    create_empty_chart_placeholder,
    create_law_adoption_timeline_chart,
    create_tech_completion_timeline_chart,
    create_yield_chart,  # NEW: Generic yield chart function
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
from tournament_visualizer.config import MODEBAR_CONFIG, PAGE_CONFIG
from tournament_visualizer.data.queries import get_queries
from tournament_visualizer.utils.event_categories import (
    get_category_color_map,
    get_event_category,
)

logger = logging.getLogger(__name__)

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


@callback(
    [
        Output("match-selector", "value"),
        Output("match-url", "search"),
    ],
    [
        Input("match-url", "search"),
        Input("match-selector", "value"),
        Input("match-selector", "options"),
    ],
    prevent_initial_call=False,
)
def sync_match_selection(
    url_search: str, selector_value: Optional[int], options: List[Dict[str, Any]]
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
        Tuple of (selector_value, url_search)
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
                    return match_id_int, url_search
        return None, ""

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
                    return match_id_int, url_search
        return None, ""

    # If selector changed (user picked from dropdown), update URL to match
    elif trigger_id == "match-selector":
        if selector_value:
            new_url = f"?match_id={selector_value}"
            return selector_value, new_url
        return None, ""

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
                return match_id_int, url_search

    # Fallback (shouldn't reach here)
    return dash.no_update, dash.no_update


@callback(
    Output("match-selector", "options"),
    Input("refresh-interval", "n_intervals"),
    prevent_initial_call=False,
)
def update_match_options(n_intervals: int) -> List[Dict[str, Any]]:
    """Update match selector options.

    Args:
        n_intervals: Number of interval triggers

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
)
def update_match_details(match_id: Optional[int]) -> tuple:
    """Update match details when a match is selected.

    Args:
        match_id: Selected match ID

    Returns:
        Tuple of (details_content, details_style, empty_state_style)
    """
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
                        "label": "Turn Progression",
                        "tab_id": "turn-progression",
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
                                className="mb-3",
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
                        "label": "Laws & Technology",
                        "tab_id": "technology",
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
                            # Law Adoption Timeline
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            create_chart_card(
                                                title="Law Adoption Timeline",
                                                chart_id="match-law-timeline",
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
                            # Final Laws and Technologies by player
                            html.Div(
                                id="match-final-laws-techs-content", className="mb-3"
                            ),
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
                                                    height="400px",
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
                                                        height="400px",
                                                    )
                                                ],
                                                width=6,
                                            )
                                            if i + 1 < len(YIELD_TYPES)
                                            else dbc.Col(width=6)
                                        ),  # Empty column if odd number
                                    ],
                                    className="mb-3",
                                )
                                for i in range(
                                    0, len(YIELD_TYPES), 2
                                )  # Step by 2 to create pairs
                            ],
                        ],
                    },
                    {
                        "label": "Ambitions",
                        "tab_id": "statistics",
                        "content": [
                            # Ambition Summary
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
                            # Ambition Timeline Charts (dynamically generated per player)
                            html.Div(id="match-ambition-timelines-container"),
                        ],
                    },
                    {
                        "label": "Game Settings",
                        "tab_id": "settings",
                        "content": [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [html.Div(id="match-settings-content")],
                                        width=12,
                                    )
                                ]
                            )
                        ],
                    },
                ],
                active_tab="turn-progression",
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


@callback(Output("match-technology-chart", "figure"), Input("match-selector", "value"))
def update_technology_chart(match_id: Optional[int]) -> go.Figure:
    """Update cumulative technology count chart.

    Args:
        match_id: Selected match ID

    Returns:
        Plotly figure for cumulative technology count
    """
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

        return create_cumulative_tech_count_chart(df, total_turns)

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

        return create_tech_completion_timeline_chart(df)

    except Exception as e:
        logger.error(f"Error loading tech completion timeline: {e}")
        return create_empty_chart_placeholder(
            f"Error loading technology timeline: {str(e)}"
        )


@callback(Output("match-law-timeline", "figure"), Input("match-selector", "value"))
def update_law_timeline(match_id: Optional[int]) -> go.Figure:
    """Update law adoption timeline chart.

    Args:
        match_id: Selected match ID

    Returns:
        Plotly figure showing when each player adopted each law
    """
    if not match_id:
        return create_empty_chart_placeholder(
            "Select a match to view law timeline"
        )

    try:
        queries = get_queries()
        df = queries.get_law_timeline(match_id)

        if df.empty:
            return create_empty_chart_placeholder(
                "No law timeline data available for this match"
            )

        return create_law_adoption_timeline_chart(df)

    except Exception as e:
        logger.error(f"Error loading law adoption timeline: {e}")
        return create_empty_chart_placeholder(
            f"Error loading law timeline: {str(e)}"
        )


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
    Output("match-final-laws-techs-content", "children"),
    Input("match-selector", "value"),
)
def update_final_laws_techs(match_id: Optional[int]) -> html.Div:
    """Update final laws and technologies display by player.

    Args:
        match_id: Selected match ID

    Returns:
        HTML content with player boxes containing laws and techs
    """
    if not match_id:
        return html.Div(
            "Select a match to view final laws and technologies", className="text-muted"
        )

    try:
        queries = get_queries()

        # Get laws data
        laws_df = queries.get_cumulative_law_count_by_turn(match_id)
        # Get techs data
        techs_df = queries.get_tech_count_by_turn(match_id)

        if laws_df.empty and techs_df.empty:
            return html.Div("No data available", className="text-muted")

        # Get final turn data for each player
        player_data = {}

        if not laws_df.empty:
            final_laws = laws_df.loc[
                laws_df.groupby("player_id")["turn_number"].idxmax()
            ]
            for _, row in final_laws.iterrows():
                player_id = row["player_id"]
                player_data[player_id] = {
                    "name": row["player_name"],
                    "laws": [],
                    "techs": [],
                }
                law_list_str = row.get("law_list", "")
                if law_list_str and pd.notna(law_list_str):
                    laws = [law.strip() for law in str(law_list_str).split(",")]
                    # Remove LAW_ prefix, quotes, humanize, and sort
                    player_data[player_id]["laws"] = sorted(
                        [
                            law.replace("LAW_", "")
                            .replace("_", " ")
                            .strip('"')
                            .strip("'")
                            .title()
                            for law in laws
                        ]
                    )

        if not techs_df.empty:
            final_techs = techs_df.loc[
                techs_df.groupby("player_id")["turn_number"].idxmax()
            ]
            for _, row in final_techs.iterrows():
                player_id = row["player_id"]
                if player_id not in player_data:
                    player_data[player_id] = {
                        "name": row["player_name"],
                        "laws": [],
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

            # Create laws list
            laws_items = (
                [html.Li(law, className="mb-1") for law in data["laws"]]
                if data["laws"]
                else [html.Span("No laws", className="text-muted")]
            )

            # Create techs list
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
                            dbc.Row(
                                [
                                    dbc.Col(
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
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
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
                                        ],
                                        width=6,
                                    ),
                                ]
                            )
                        ]
                    ),
                ]
            )
            player_cols.append(dbc.Col(player_card, width=12 // len(player_data)))

        return dbc.Row(player_cols)

    except Exception as e:
        logger.error(f"Error loading final laws and technologies: {e}")
        return html.Div(f"Error loading data: {str(e)}", className="text-danger")


@callback(
    Output("match-law-cumulative", "figure"),
    Input("match-selector", "value"),
)
def update_law_cumulative(match_id: Optional[int]) -> go.Figure:
    """Update cumulative law count chart.

    Args:
        match_id: Selected match ID

    Returns:
        Plotly figure with cumulative line chart
    """
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

        return create_cumulative_law_count_chart(df, total_turns)

    except Exception as e:
        logger.error(f"Error loading cumulative law count: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    # Generate outputs for all 14 yield charts dynamically
    [
        Output(f"match-{yield_type.lower().replace('_', '-')}-chart", "figure")
        for yield_type, _ in YIELD_TYPES
    ],
    Input("match-selector", "value"),
)
def update_all_yield_charts(match_id: Optional[int]) -> List[go.Figure]:
    """Update all yield charts when a match is selected.

    Fetches data for all 14 yield types in a single query and creates
    individual charts for each yield type.

    Args:
        match_id: Selected match ID

    Returns:
        List of 14 Plotly figures (one for each yield type)
    """
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

        # Get total turns for the match to extend chart lines
        match_df = queries.get_match_summary()
        match_info = match_df[match_df["match_id"] == match_id]
        total_turns = (
            match_info.iloc[0]["total_turns"] if not match_info.empty else None
        )

        # Create all 14 charts from the same DataFrame
        charts = []
        for yield_type, display_name in YIELD_TYPES:
            # Filter to this specific yield type
            df_yield = all_yields_df[all_yields_df["resource_type"] == yield_type]

            # Create chart using generic function
            chart = create_yield_chart(
                df_yield,
                total_turns=total_turns,
                yield_type=yield_type,
                display_name=display_name,
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


@callback(
    Output("match-ambition-timelines-container", "children"),
    Input("match-selector", "value"),
)
def update_ambition_timelines(match_id: Optional[int]):
    """Update ambition timeline charts - one per player.

    Args:
        match_id: Selected match ID

    Returns:
        HTML Div containing separate chart cards for each player
    """
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
    Input("match-selector", "value"),
)
def update_ambition_summary(match_id: Optional[int]) -> go.Figure:
    """Update ambition summary table.

    Args:
        match_id: Selected match ID

    Returns:
        Plotly figure for ambition summary table
    """
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
