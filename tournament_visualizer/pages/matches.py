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
    create_cumulative_law_count_chart,
    create_cumulative_tech_count_chart,
    create_empty_chart_placeholder,
    create_statistics_grouped_bar,
    create_statistics_radar_chart,
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
from tournament_visualizer.config import PAGE_CONFIG
from tournament_visualizer.data.queries import get_queries

logger = logging.getLogger(__name__)

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
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dcc.Dropdown(
                                            id="match-selector",
                                            placeholder="Choose a match to analyze...",
                                            options=[],
                                            value=None,
                                        )
                                    ],
                                    width=8,
                                ),
                                dbc.Col(
                                    [
                                        dbc.Button(
                                            [
                                                html.I(
                                                    className="bi bi-arrow-clockwise me-2"
                                                ),
                                                "Refresh",
                                            ],
                                            id="matches-refresh-btn",
                                            color="outline-primary",
                                            className="w-100",
                                        )
                                    ],
                                    width=4,
                                ),
                            ]
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
    Input("matches-refresh-btn", "n_clicks"),
    prevent_initial_call=False,
)
def update_match_options(refresh_clicks: Optional[int]) -> List[Dict[str, Any]]:
    """Update match selector options.

    Args:
        refresh_clicks: Number of refresh button clicks (None on initial load)

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

        # Create match details layout
        details_content = [
            # Match overview cards
            dbc.Row(
                [
                    dbc.Col(
                        [
                            create_metric_card(
                                title="Game Name",
                                value=game_display,
                                icon="bi-controller",
                                color="primary",
                            )
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            create_metric_card(
                                title="Total Turns",
                                value=match_data.get("total_turns", 0),
                                icon="bi-clock",
                                color="info",
                            )
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            create_metric_card(
                                title="Players",
                                value=match_data.get("player_count", 0),
                                icon="bi-people",
                                color="success",
                            )
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            create_metric_card(
                                title="Winner",
                                value=winner_display,
                                icon="bi-trophy",
                                color="warning",
                            )
                        ],
                        width=3,
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
                                                title="Events Timeline (All Event Types)",
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
                        "label": "Technology & Research",
                        "tab_id": "technology",
                        "content": [
                            # Final Laws and Technologies by player
                            html.Div(
                                id="match-final-laws-techs-content", className="mb-3"
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
                        ],
                    },
                    {
                        "label": "Player Statistics",
                        "tab_id": "statistics",
                        "content": [
                            # Grouped Bar Chart
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Card(
                                                [
                                                    dbc.CardHeader(
                                                        [
                                                            dbc.Row(
                                                                [
                                                                    dbc.Col(
                                                                        [
                                                                            html.H5(
                                                                                "Top 10 Statistics - Grouped Comparison",
                                                                                className="mb-0",
                                                                            )
                                                                        ],
                                                                        width=8,
                                                                    ),
                                                                    dbc.Col(
                                                                        [
                                                                            dcc.Dropdown(
                                                                                id="stats-grouped-bar-category-filter",
                                                                                placeholder="All Categories",
                                                                                options=[],
                                                                                value=None,
                                                                                clearable=True,
                                                                                className="mb-0",
                                                                            )
                                                                        ],
                                                                        width=4,
                                                                    ),
                                                                ],
                                                                align="center",
                                                            )
                                                        ]
                                                    ),
                                                    dbc.CardBody(
                                                        [
                                                            dcc.Loading(
                                                                dcc.Graph(
                                                                    id="match-stats-grouped-bar",
                                                                    config={
                                                                        "displayModeBar": False
                                                                    },
                                                                ),
                                                                type="default",
                                                            )
                                                        ],
                                                        style={"height": "500px"},
                                                    ),
                                                ]
                                            )
                                        ],
                                        width=12,
                                    )
                                ],
                                className="mb-3",
                            ),
                            # Radar Chart
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Card(
                                                [
                                                    dbc.CardHeader(
                                                        [
                                                            dbc.Row(
                                                                [
                                                                    dbc.Col(
                                                                        [
                                                                            html.H5(
                                                                                "Statistics Radar Chart",
                                                                                className="mb-0",
                                                                            )
                                                                        ],
                                                                        width=8,
                                                                    ),
                                                                    dbc.Col(
                                                                        [
                                                                            dcc.Dropdown(
                                                                                id="stats-radar-category-filter",
                                                                                placeholder="All Categories",
                                                                                options=[],
                                                                                value=None,
                                                                                clearable=True,
                                                                                className="mb-0",
                                                                            )
                                                                        ],
                                                                        width=4,
                                                                    ),
                                                                ],
                                                                align="center",
                                                            )
                                                        ]
                                                    ),
                                                    dbc.CardBody(
                                                        [
                                                            dcc.Loading(
                                                                dcc.Graph(
                                                                    id="match-stats-radar",
                                                                    config={
                                                                        "displayModeBar": False
                                                                    },
                                                                ),
                                                                type="default",
                                                            )
                                                        ],
                                                        style={"height": "500px"},
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
                                                        [
                                                            dbc.Row(
                                                                [
                                                                    dbc.Col(
                                                                        [
                                                                            html.H5(
                                                                                "Category Totals",
                                                                                className="mb-0",
                                                                            )
                                                                        ],
                                                                        width=8,
                                                                    ),
                                                                    dbc.Col(
                                                                        [
                                                                            dcc.Dropdown(
                                                                                id="stats-comparison-category-filter",
                                                                                placeholder="All Categories",
                                                                                options=[],
                                                                                value=None,
                                                                                clearable=True,
                                                                                className="mb-0",
                                                                            )
                                                                        ],
                                                                        width=4,
                                                                    ),
                                                                ],
                                                                align="center",
                                                            )
                                                        ]
                                                    ),
                                                    dbc.CardBody(
                                                        [
                                                            dcc.Loading(
                                                                dcc.Graph(
                                                                    id="match-stats-comparison",
                                                                    config={
                                                                        "displayModeBar": False
                                                                    },
                                                                ),
                                                                type="default",
                                                            )
                                                        ],
                                                        style={"height": "500px"},
                                                    ),
                                                ]
                                            )
                                        ],
                                        width=6,
                                    ),
                                ]
                            ),
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
    """Update the events timeline chart with all event types.

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

        # Count events per turn by event category
        import plotly.graph_objects as go

        from tournament_visualizer.components.charts import create_base_figure
        from tournament_visualizer.config import Config

        # Group by turn and event category
        events_by_category = (
            df.groupby(["turn_number", "event_category"])
            .size()
            .reset_index(name="event_count")
        )

        # Create stacked bar chart
        fig = create_base_figure(
            title="Events Timeline (Memory + Game Log Events)",
            x_title="Turn Number",
            y_title="Number of Events",
        )

        # Get unique categories
        categories = events_by_category["event_category"].unique()

        # Add a bar trace for each category
        category_colors = {
            "Game Log": Config.PRIMARY_COLORS[0],  # Blue for LogData
            "Memory": Config.PRIMARY_COLORS[2],  # Purple for MemoryData
        }

        for category in categories:
            category_data = events_by_category[
                events_by_category["event_category"] == category
            ]
            fig.add_trace(
                go.Bar(
                    name=category,
                    x=category_data["turn_number"],
                    y=category_data["event_count"],
                    marker_color=category_colors.get(
                        category, Config.PRIMARY_COLORS[3]
                    ),
                )
            )

        # Set barmode to stack
        fig.update_layout(barmode="stack")

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


@callback(
    [
        Output("stats-grouped-bar-category-filter", "options"),
        Output("stats-radar-category-filter", "options"),
        Output("stats-comparison-category-filter", "options"),
    ],
    Input("match-selector", "value"),
)
def update_category_filter_options(
    match_id: Optional[int],
) -> tuple[List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, str]]]:
    """Update category filter options for all three dropdowns.

    Args:
        match_id: Selected match ID

    Returns:
        Tuple of three identical lists of category options for each dropdown
    """
    if not match_id:
        return [], [], []

    try:
        queries = get_queries()
        df = queries.get_player_statistics_by_category(match_id)

        if df.empty or "stat_category" not in df.columns:
            return [], [], []

        categories = sorted(df["stat_category"].unique())
        options = [{"label": cat, "value": cat} for cat in categories]
        return options, options, options

    except Exception as e:
        logger.error(f"Error loading category options: {e}")
        return [], [], []


@callback(
    Output("match-stats-grouped-bar", "figure"),
    Input("match-selector", "value"),
    Input("stats-grouped-bar-category-filter", "value"),
)
def update_stats_grouped_bar(match_id: Optional[int], category_filter: Optional[str]):
    """Update grouped bar chart.

    Args:
        match_id: Selected match ID
        category_filter: Optional category to filter by

    Returns:
        Plotly figure for grouped bar chart
    """
    if not match_id:
        return create_empty_chart_placeholder("Select a match to view statistics")

    try:
        queries = get_queries()
        df = queries.get_player_statistics_by_category(match_id)

        if df.empty:
            return create_empty_chart_placeholder(
                "No statistics data available for this match"
            )

        return create_statistics_grouped_bar(
            df, category_filter=category_filter, top_n=10
        )

    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading statistics: {str(e)}")


@callback(
    Output("match-stats-radar", "figure"),
    Input("match-selector", "value"),
    Input("stats-radar-category-filter", "value"),
)
def update_stats_radar(match_id: Optional[int], category_filter: Optional[str]):
    """Update radar chart.

    Args:
        match_id: Selected match ID
        category_filter: Optional category to filter by

    Returns:
        Plotly figure for radar chart
    """
    if not match_id:
        return create_empty_chart_placeholder("Select a match to view statistics")

    try:
        queries = get_queries()
        df = queries.get_player_statistics_by_category(match_id)

        if df.empty:
            return create_empty_chart_placeholder(
                "No statistics data available for this match"
            )

        return create_statistics_radar_chart(
            df, category_filter=category_filter, top_n=8
        )

    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading statistics: {str(e)}")


@callback(
    Output("match-stats-comparison", "figure"),
    Input("match-selector", "value"),
    Input("stats-comparison-category-filter", "value"),
)
def update_stats_comparison(match_id: Optional[int], category_filter: Optional[str]):
    """Update category totals bar chart.

    Args:
        match_id: Selected match ID
        category_filter: Optional category to filter by

    Returns:
        Plotly figure for category totals
    """
    if not match_id:
        return create_empty_chart_placeholder(
            "Select a match to view statistics comparison"
        )

    try:
        queries = get_queries()
        df = queries.get_player_statistics_by_category(match_id)

        if df.empty:
            return create_empty_chart_placeholder(
                "No statistics data available for this match"
            )

        # If category filter is set, show individual stats from that category
        if category_filter:
            category_df = df[df["stat_category"] == category_filter]
            return create_statistics_grouped_bar(
                category_df, category_filter=None, top_n=15
            )

        # Otherwise, show totals by category
        if "stat_category" not in df.columns:
            return create_empty_chart_placeholder("No category data available")

        # Aggregate by category
        category_totals = (
            df.groupby(["stat_category", "player_name"])["value"].sum().reset_index()
        )

        import plotly.graph_objects as go

        from tournament_visualizer.components.charts import create_base_figure
        from tournament_visualizer.config import Config

        fig = create_base_figure(
            title="Total Statistics by Category",
            x_title="Category",
            y_title="Total Value",
        )

        # Add a bar for each player
        for i, player in enumerate(category_totals["player_name"].unique()):
            player_data = category_totals[category_totals["player_name"] == player]

            fig.add_trace(
                go.Bar(
                    name=player,
                    x=player_data["stat_category"],
                    y=player_data["value"],
                    marker_color=Config.PRIMARY_COLORS[i % len(Config.PRIMARY_COLORS)],
                    text=player_data["value"],
                    textposition="auto",
                )
            )

        fig.update_layout(barmode="group", xaxis_tickangle=-45)

        return fig

    except Exception as e:
        return create_empty_chart_placeholder(
            f"Error loading statistics comparison: {str(e)}"
        )


@callback(
    Output("match-settings-content", "children"), Input("match-selector", "value")
)
def update_settings_content(match_id: Optional[int]):
    """Update game settings display.

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

        if not metadata:
            return create_empty_state(
                "No settings data available for this match",
                icon="bi-exclamation-triangle",
            )

        # Create a card layout for settings
        import json

        settings_cards = []

        # Basic settings
        if (
            metadata.get("difficulty")
            or metadata.get("event_level")
            or metadata.get("victory_type")
        ):
            basic_settings = dbc.Card(
                [
                    dbc.CardHeader("Basic Settings"),
                    dbc.CardBody(
                        [
                            html.Dl(
                                [
                                    html.Dt("Difficulty"),
                                    html.Dd(metadata.get("difficulty", "N/A")),
                                    html.Dt("Event Level"),
                                    html.Dd(metadata.get("event_level", "N/A")),
                                    html.Dt("Victory Type"),
                                    html.Dd(metadata.get("victory_type", "N/A")),
                                    html.Dt("Victory Turn"),
                                    html.Dd(str(metadata.get("victory_turn", "N/A"))),
                                ]
                            )
                        ]
                    ),
                ],
                className="mb-3",
            )
            settings_cards.append(basic_settings)

        # Game options
        if metadata.get("game_options"):
            try:
                options = (
                    json.loads(metadata["game_options"])
                    if isinstance(metadata["game_options"], str)
                    else metadata["game_options"]
                )
                if options:
                    game_options_card = dbc.Card(
                        [
                            dbc.CardHeader("Game Options"),
                            dbc.CardBody(
                                [
                                    html.Pre(
                                        json.dumps(options, indent=2), className="mb-0"
                                    )
                                ]
                            ),
                        ],
                        className="mb-3",
                    )
                    settings_cards.append(game_options_card)
            except:
                pass

        # DLC content
        if metadata.get("dlc_content"):
            try:
                dlc = (
                    json.loads(metadata["dlc_content"])
                    if isinstance(metadata["dlc_content"], str)
                    else metadata["dlc_content"]
                )
                if dlc:
                    dlc_card = dbc.Card(
                        [
                            dbc.CardHeader("DLC Content"),
                            dbc.CardBody(
                                [html.Pre(json.dumps(dlc, indent=2), className="mb-0")]
                            ),
                        ],
                        className="mb-3",
                    )
                    settings_cards.append(dlc_card)
            except:
                pass

        # Map settings
        if metadata.get("map_settings"):
            try:
                map_settings = (
                    json.loads(metadata["map_settings"])
                    if isinstance(metadata["map_settings"], str)
                    else metadata["map_settings"]
                )
                if map_settings:
                    map_card = dbc.Card(
                        [
                            dbc.CardHeader("Map Settings"),
                            dbc.CardBody(
                                [
                                    html.Pre(
                                        json.dumps(map_settings, indent=2),
                                        className="mb-0",
                                    )
                                ]
                            ),
                        ],
                        className="mb-3",
                    )
                    settings_cards.append(map_card)
            except:
                pass

        if not settings_cards:
            return create_empty_state(
                "No detailed settings available", icon="bi-info-circle"
            )

        return html.Div(settings_cards)

    except Exception as e:
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
                    # Remove LAW_ prefix, humanize, and sort
                    player_data[player_id]["laws"] = sorted(
                        [
                            law.replace("LAW_", "").replace("_", " ").title()
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
                    # Remove TECH_ prefix, humanize, and sort
                    player_data[player_id]["techs"] = sorted(
                        [
                            tech.replace("TECH_", "").replace("_", " ").title()
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
                                                className="list-unstyled",
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
                                                className="list-unstyled",
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
