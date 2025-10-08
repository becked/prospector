"""Tournament overview dashboard page.

This page provides a high-level overview of tournament statistics,
recent matches, and key performance indicators.
"""

import logging
from typing import Any, Dict, List

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, callback, html

from tournament_visualizer.components.charts import (
    create_empty_chart_placeholder,
    create_map_breakdown_sunburst_chart,
    create_nation_loss_percentage_chart,
    create_nation_popularity_chart,
    create_nation_win_percentage_chart,
    create_summary_metrics_cards,
    create_unit_popularity_sunburst_chart,
)
from tournament_visualizer.components.layouts import (
    create_chart_card,
    create_data_table_card,
    create_empty_state,
    create_metric_grid,
    create_page_header,
)
from tournament_visualizer.config import PAGE_CONFIG
from tournament_visualizer.data.queries import get_queries

logger = logging.getLogger(__name__)

# Register this page
dash.register_page(__name__, path="/", name="Overview")

# Page layout
layout = html.Div(
    [
        # Page header
        create_page_header(
            title=PAGE_CONFIG["overview"]["title"],
            description=PAGE_CONFIG["overview"]["description"],
            icon="bi-bar-chart-fill",
            actions=[
                dbc.Button(
                    [html.I(className="bi bi-arrow-clockwise me-2"), "Refresh"],
                    id="overview-refresh-btn",
                    color="outline-primary",
                    size="sm",
                )
            ],
        ),
        # Alert area
        html.Div(id="overview-alerts"),
        # Summary metrics
        html.Div(id="overview-metrics"),
        # Main charts section - 3 pie charts in a row
        dbc.Row(
            [
                dbc.Col(
                    [
                        create_chart_card(
                            title="Nation Win Percentage",
                            chart_id="overview-nation-win-chart",
                            height="400px",
                        )
                    ],
                    width=4,
                ),
                dbc.Col(
                    [
                        create_chart_card(
                            title="Nation Loss Percentage",
                            chart_id="overview-nation-loss-chart",
                            height="400px",
                        )
                    ],
                    width=4,
                ),
                dbc.Col(
                    [
                        create_chart_card(
                            title="Nation Popularity",
                            chart_id="overview-nation-popularity-chart",
                            height="400px",
                        )
                    ],
                    width=4,
                ),
            ],
            className="mb-4",
        ),
        # Unit breakdown and Map breakdown section - 2 charts side by side
        dbc.Row(
            [
                dbc.Col(
                    [
                        create_chart_card(
                            title="Unit Breakdown",
                            chart_id="overview-units-chart",
                            height="400px",
                        )
                    ],
                    width=6,
                ),
                dbc.Col(
                    [
                        create_chart_card(
                            title="Map Breakdown",
                            chart_id="overview-map-chart",
                            height="400px",
                        )
                    ],
                    width=6,
                ),
            ],
            className="mb-4",
        ),
        # Recent matches table
        dbc.Row(
            [
                dbc.Col(
                    [
                        create_data_table_card(
                            title="Recent Matches",
                            table_id="overview-matches-table",
                            columns=[
                                {
                                    "name": "Match",
                                    "id": "match_link",
                                    "presentation": "markdown",
                                },
                                {"name": "Date", "id": "save_date", "type": "datetime"},
                                {
                                    "name": "Turns",
                                    "id": "total_turns",
                                    "type": "numeric",
                                },
                                {"name": "Winner", "id": "winner_name"},
                                {"name": "Map", "id": "map_info"},
                            ],
                        )
                    ],
                    width=12,
                )
            ]
        ),
    ]
)


@callback(
    Output("overview-metrics", "children"), Input("overview-refresh-btn", "n_clicks")
)
def update_overview_metrics(refresh_clicks: int) -> html.Div:
    """Update the overview metrics cards.

    Args:
        refresh_clicks: Number of refresh button clicks

    Returns:
        Metrics grid component
    """
    try:
        queries = get_queries()
        stats = queries.get_database_statistics()

        # Create metric cards
        metrics = create_summary_metrics_cards(stats)

        return create_metric_grid(metrics)

    except Exception as e:
        return create_empty_state(
            title="Error Loading Metrics",
            message=f"Unable to load overview metrics: {str(e)}",
            icon="bi-exclamation-triangle",
        )


@callback(
    Output("overview-nation-win-chart", "figure"),
    Input("overview-refresh-btn", "n_clicks"),
)
def update_nation_win_chart(refresh_clicks: int):
    """Update the nation win percentage chart.

    Args:
        refresh_clicks: Number of refresh button clicks

    Returns:
        Plotly figure for nation win percentage
    """
    try:
        queries = get_queries()
        df = queries.get_nation_win_stats()

        if df.empty:
            return create_empty_chart_placeholder("No nation data available")

        return create_nation_win_percentage_chart(df)

    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading nation data: {str(e)}")


@callback(
    Output("overview-nation-loss-chart", "figure"),
    Input("overview-refresh-btn", "n_clicks"),
)
def update_nation_loss_chart(refresh_clicks: int):
    """Update the nation loss percentage chart.

    Args:
        refresh_clicks: Number of refresh button clicks

    Returns:
        Plotly figure for nation loss percentage
    """
    try:
        queries = get_queries()
        df = queries.get_nation_loss_stats()

        if df.empty:
            return create_empty_chart_placeholder("No nation data available")

        return create_nation_loss_percentage_chart(df)

    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading nation data: {str(e)}")


@callback(
    Output("overview-nation-popularity-chart", "figure"),
    Input("overview-refresh-btn", "n_clicks"),
)
def update_nation_popularity_chart(refresh_clicks: int):
    """Update the nation popularity chart.

    Args:
        refresh_clicks: Number of refresh button clicks

    Returns:
        Plotly figure for nation popularity
    """
    try:
        queries = get_queries()
        df = queries.get_nation_popularity()

        if df.empty:
            return create_empty_chart_placeholder("No nation data available")

        return create_nation_popularity_chart(df)

    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading nation data: {str(e)}")


@callback(
    Output("overview-units-chart", "figure"), Input("overview-refresh-btn", "n_clicks")
)
def update_units_chart(refresh_clicks: int):
    """Update the unit popularity sunburst chart.

    Args:
        refresh_clicks: Number of refresh button clicks

    Returns:
        Plotly figure for unit popularity
    """
    try:
        queries = get_queries()
        df = queries.get_unit_popularity()

        if df.empty:
            return create_empty_chart_placeholder("No unit data available")

        return create_unit_popularity_sunburst_chart(df)

    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading unit data: {str(e)}")


@callback(
    Output("overview-map-chart", "figure"), Input("overview-refresh-btn", "n_clicks")
)
def update_map_chart(refresh_clicks: int):
    """Update the map breakdown sunburst chart.

    Args:
        refresh_clicks: Number of refresh button clicks

    Returns:
        Plotly figure for map breakdown
    """
    try:
        queries = get_queries()
        df = queries.get_map_breakdown()

        if df.empty:
            return create_empty_chart_placeholder("No map data available")

        return create_map_breakdown_sunburst_chart(df)

    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading map data: {str(e)}")


@callback(
    Output("overview-matches-table", "data"), Input("overview-refresh-btn", "n_clicks")
)
def update_matches_table(refresh_clicks: int) -> List[Dict[str, Any]]:
    """Update the recent matches table.

    Args:
        refresh_clicks: Number of refresh button clicks

    Returns:
        List of dictionaries for table data
    """
    try:
        queries = get_queries()
        df = queries.get_recent_matches(limit=20)

        if df.empty:
            return []

        # Format data for table
        table_data = []
        for _, row in df.iterrows():
            match_id = row.get("match_id")
            players = (
                f"{row.get('player1', 'Unknown')} vs {row.get('player2', 'Unknown')}"
            )
            table_data.append(
                {
                    "match_link": f"[{players}](/matches?match_id={match_id})",
                    "save_date": (
                        row.get("save_date", "").strftime("%Y-%m-%d")
                        if pd.notna(row.get("save_date"))
                        else ""
                    ),
                    "total_turns": row.get("total_turns", 0),
                    "winner_name": row.get("winner_name", "Unknown"),
                    "map_info": row.get("map_info", "Unknown").strip(),
                }
            )

        return table_data

    except Exception as e:
        logger.error(f"Error updating matches table: {e}")
        return []


@callback(
    Output("overview-alerts", "children"), Input("overview-refresh-btn", "n_clicks")
)
def check_data_status(refresh_clicks: int) -> html.Div:
    """Check data status and show alerts if needed.

    Args:
        refresh_clicks: Number of refresh button clicks

    Returns:
        Alert components if needed
    """
    try:
        queries = get_queries()
        stats = queries.get_database_statistics()

        alerts = []

        # Check if there's no data
        if stats.get("matches_count", 0) == 0:
            alerts.append(
                dbc.Alert(
                    [
                        html.H4("No Tournament Data", className="alert-heading"),
                        html.P(
                            [
                                "No tournament matches have been imported yet. ",
                                "Use the import script to process your tournament save files.",
                            ]
                        ),
                        html.Hr(),
                        dbc.Button("Learn More", color="info", outline=True, size="sm"),
                    ],
                    color="info",
                    dismissable=True,
                )
            )

        # Check for recent data
        elif "last_processed" in stats:
            from datetime import datetime, timedelta

            last_processed = pd.to_datetime(stats["last_processed"])
            if datetime.now() - last_processed > timedelta(days=7):
                alerts.append(
                    dbc.Alert(
                        [
                            html.H4("Data May Be Outdated", className="alert-heading"),
                            html.P(
                                [
                                    f"Last import was {(datetime.now() - last_processed).days} days ago. ",
                                    "Consider importing new tournament data.",
                                ]
                            ),
                        ],
                        color="warning",
                        dismissable=True,
                    )
                )

        return html.Div(alerts) if alerts else html.Div()

    except Exception as e:
        return dbc.Alert(
            f"Error checking data status: {str(e)}", color="danger", dismissable=True
        )
