"""Player performance analytics page.

This page provides comprehensive player statistics, head-to-head comparisons,
and performance trends analysis.
"""

import logging
from typing import Any, Dict, List, Optional

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, callback, dcc, html

from tournament_visualizer.components.charts import (
    create_base_figure,
    create_civilization_performance_chart,
    create_empty_chart_placeholder,
    create_head_to_head_chart,
    create_player_performance_chart,
)
from tournament_visualizer.components.filters import (
    create_civilization_filter,
    create_date_range_filter,
)
from tournament_visualizer.components.layouts import (
    create_chart_card,
    create_data_table_card,
    create_empty_state,
    create_filter_card,
    create_metric_grid,
    create_page_header,
    create_tab_layout,
)
from tournament_visualizer.config import PAGE_CONFIG
from tournament_visualizer.data.queries import get_queries

logger = logging.getLogger(__name__)

# Register this page
dash.register_page(__name__, path="/players", name="Players")

# Page layout
layout = html.Div(
    [
        # Page header
        create_page_header(
            title=PAGE_CONFIG["players"]["title"],
            description=PAGE_CONFIG["players"]["description"],
            icon="bi-people-fill",
        ),
        # Tabbed analytics sections
        create_tab_layout(
            [
                {
                    "label": "Player Rankings",
                    "tab_id": "rankings",
                    "content": [
                        # Summary metrics
                        html.Div(id="player-summary-metrics", className="mb-4"),
                        # Detailed rankings table
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_data_table_card(
                                            title="Player Performance Rankings",
                                            table_id="players-rankings-table",
                                            columns=[
                                                {
                                                    "name": "Rank",
                                                    "id": "rank",
                                                    "type": "numeric",
                                                },
                                                {"name": "Player", "id": "player_name"},
                                                {
                                                    "name": "Matches",
                                                    "id": "total_matches",
                                                    "type": "numeric",
                                                },
                                                {
                                                    "name": "Wins",
                                                    "id": "wins",
                                                    "type": "numeric",
                                                },
                                                {
                                                    "name": "Win Rate",
                                                    "id": "win_rate",
                                                    "type": "numeric",
                                                    "format": {"specifier": ".1%"},
                                                },
                                                {
                                                    "name": "Avg Score",
                                                    "id": "avg_score",
                                                    "type": "numeric",
                                                    "format": {"specifier": ".1f"},
                                                },
                                                {
                                                    "name": "Favorite Civ",
                                                    "id": "favorite_civilization",
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
                    "label": "Head-to-Head",
                    "tab_id": "head-to-head",
                    "content": [
                        # Player selection
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H5(
                                            "Head-to-Head Comparison",
                                            className="card-title",
                                        ),
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "Player 1:",
                                                            className="form-label",
                                                        ),
                                                        dcc.Dropdown(
                                                            id="h2h-player1-selector",
                                                            placeholder="Select first player...",
                                                            options=[],
                                                        ),
                                                    ],
                                                    width=5,
                                                ),
                                                dbc.Col(
                                                    [
                                                        html.Div(
                                                            "vs",
                                                            className="text-center mt-4",
                                                        ),
                                                    ],
                                                    width=2,
                                                ),
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "Player 2:",
                                                            className="form-label",
                                                        ),
                                                        dcc.Dropdown(
                                                            id="h2h-player2-selector",
                                                            placeholder="Select second player...",
                                                            options=[],
                                                        ),
                                                    ],
                                                    width=5,
                                                ),
                                            ]
                                        ),
                                    ]
                                )
                            ],
                            className="mb-4",
                        ),
                        # Head-to-head results
                        html.Div(id="h2h-results-section"),
                    ],
                },
            ],
            active_tab="rankings",
        ),
    ]
)


@callback(
    Output("player-summary-metrics", "children"),
    Input("refresh-interval", "n_intervals"),
)
def update_player_summary_metrics(n_intervals: int) -> html.Div:
    """Update player summary metrics.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Metrics grid component
    """
    try:
        queries = get_queries()
        df = queries.get_player_performance()

        if df.empty:
            return create_empty_state("No player data available")

        # Count unique players
        total_players = df["player_name"].nunique()

        metrics = [
            {
                "title": "Active Players",
                "value": total_players,
                "icon": "bi-people",
                "color": "primary",
            },
        ]

        return create_metric_grid(metrics)

    except Exception as e:
        return create_empty_state(f"Error loading metrics: {str(e)}")


@callback(
    [
        Output("h2h-player1-selector", "options"),
        Output("h2h-player2-selector", "options"),
    ],
    Input("refresh-interval", "n_intervals"),
)
def update_h2h_player_options(n_intervals: int) -> tuple:
    """Update head-to-head player selector options.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Tuple of (player1_options, player2_options)
    """
    try:
        queries = get_queries()
        df = queries.get_player_performance()

        if df.empty:
            return [], []

        # Create player options sorted by activity
        options = []
        for _, player in df.sort_values("total_matches", ascending=False).iterrows():
            label = f"{player['player_name']} ({player['total_matches']} matches)"
            options.append({"label": label, "value": player["player_name"]})

        return options, options

    except Exception as e:
        logger.error(f"Error updating H2H options: {e}")
        return [], []


@callback(
    Output("h2h-results-section", "children"),
    [Input("h2h-player1-selector", "value"), Input("h2h-player2-selector", "value")],
)
def update_h2h_results(player1: Optional[str], player2: Optional[str]) -> html.Div:
    """Update head-to-head results section.

    Args:
        player1: First player name
        player2: Second player name

    Returns:
        Head-to-head results component
    """
    if not player1 or not player2:
        return create_empty_state(
            title="Select Two Players",
            message="Choose two players from the dropdowns above to compare their head-to-head record.",
            icon="bi-people",
        )

    if player1 == player2:
        return create_empty_state(
            title="Different Players Required",
            message="Please select two different players for comparison.",
            icon="bi-exclamation-circle",
        )

    try:
        queries = get_queries()
        stats = queries.get_head_to_head_stats(player1, player2)

        if not stats or stats.get("total_matches", 0) == 0:
            return create_empty_state(
                title="No Head-to-Head Matches",
                message=f"{player1} and {player2} have not played against each other.",
                icon="bi-question-circle",
            )

        # Create results layout
        results = [
            # Summary metrics
            create_metric_grid(
                [
                    {
                        "title": "Total Matches",
                        "value": stats["total_matches"],
                        "icon": "bi-trophy",
                        "color": "primary",
                    },
                    {
                        "title": f"{player1} Wins",
                        "value": stats["player1_wins"],
                        "icon": "bi-check-circle",
                        "color": "success",
                    },
                    {
                        "title": f"{player2} Wins",
                        "value": stats["player2_wins"],
                        "icon": "bi-check-circle",
                        "color": "info",
                    },
                    {
                        "title": "Avg Match Length",
                        "value": (
                            f"{stats['avg_match_length']:.0f} turns"
                            if stats["avg_match_length"]
                            else "N/A"
                        ),
                        "icon": "bi-clock",
                        "color": "warning",
                    },
                ]
            ),
            # Head-to-head chart
            dbc.Row(
                [
                    dbc.Col(
                        [
                            create_chart_card(
                                title=f"{player1} vs {player2}",
                                chart_id="h2h-chart",
                                height="400px",
                            )
                        ],
                        width=12,
                    )
                ],
                className="mt-4",
            ),
        ]

        return html.Div(results)

    except Exception as e:
        return create_empty_state(
            title="Error Loading Head-to-Head",
            message=f"Unable to load comparison: {str(e)}",
            icon="bi-exclamation-triangle",
        )


@callback(
    Output("h2h-chart", "figure"),
    [Input("h2h-player1-selector", "value"), Input("h2h-player2-selector", "value")],
)
def update_h2h_chart(player1: Optional[str], player2: Optional[str]):
    """Update head-to-head comparison chart.

    Args:
        player1: First player name
        player2: Second player name

    Returns:
        Plotly figure for head-to-head comparison
    """
    if not player1 or not player2 or player1 == player2:
        return create_empty_chart_placeholder("Select two different players")

    try:
        queries = get_queries()
        stats = queries.get_head_to_head_stats(player1, player2)

        return create_head_to_head_chart(stats, player1, player2)

    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading H2H chart: {str(e)}")


# Data table callbacks
@callback(
    Output("players-rankings-table", "data"),
    Input("refresh-interval", "n_intervals"),
)
def update_rankings_table(n_intervals: int) -> List[Dict[str, Any]]:
    """Update player rankings table.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        List of player ranking data
    """
    try:
        queries = get_queries()
        df = queries.get_player_performance()

        if df.empty:
            return []

        # Sort by win rate and add rank
        df = df.sort_values("win_rate", ascending=False).reset_index(drop=True)
        df["rank"] = range(1, len(df) + 1)

        # Convert win rate to percentage for display
        df["win_rate"] = df["win_rate"] / 100

        return df.to_dict("records")

    except Exception as e:
        logger.error(f"Error updating rankings table: {e}")
        return []
