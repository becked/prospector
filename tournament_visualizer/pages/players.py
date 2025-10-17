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
        # Participant linking info alert
        dbc.Alert(
            [
                html.Div(
                    [
                        html.I(className="bi bi-info-circle me-2"),
                        html.Span(
                            "Players marked with ⚠️ are not yet linked to tournament participants. "
                            "This may happen when player names in save files don't match Challonge usernames."
                        ),
                    ]
                )
            ],
            color="info",
            className="mb-4",
            dismissable=True,
            id="participant-linking-info",
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
                                                {
                                                    "name": "Player",
                                                    "id": "player_display",
                                                    "presentation": "markdown",
                                                },
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
                                                    "name": "Civilizations",
                                                    "id": "civilizations_display",
                                                    "presentation": "markdown",
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
                                                            placeholder="Select first player first...",
                                                            options=[],
                                                            disabled=True,
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


def _format_civilizations_display(civs_played: str, favorite: str) -> str:
    """Format civilizations for display with favorite highlighted.

    Args:
        civs_played: Comma-separated list of civilizations
        favorite: The most-played civilization

    Returns:
        Markdown-formatted string with favorite bolded

    Examples:
        >>> _format_civilizations_display("Rome, Assyria", "Rome")
        '**Rome**, Assyria'

        >>> _format_civilizations_display("Babylon", "Babylon")
        '**Babylon**'
    """
    if not civs_played or pd.isna(civs_played):
        return "—"

    if not favorite or pd.isna(favorite):
        return civs_played

    # Split, bold the favorite, rejoin
    civs = [civ.strip() for civ in str(civs_played).split(",")]
    formatted = [f"**{civ}**" if civ == favorite else civ for civ in civs]
    return ", ".join(formatted)


@callback(
    Output("player-summary-metrics", "children"),
    Input("refresh-interval", "n_intervals"),
)
def update_player_summary_metrics(n_intervals: int) -> html.Div:
    """Update player summary metrics.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Metrics grid component with participant linking stats
    """
    try:
        queries = get_queries()
        df = queries.get_player_performance()

        if df.empty:
            return create_empty_state("No player data available")

        # Count total players (all)
        total_players = len(df)

        # Count linked vs unlinked
        linked_count = len(df[df["is_unlinked"] == False])
        unlinked_count = len(df[df["is_unlinked"] == True])

        # Calculate linking percentage
        linking_pct = (linked_count / total_players * 100) if total_players > 0 else 0

        metrics = [
            {
                "title": "Total Players",
                "value": total_players,
                "icon": "bi-people",
                "color": "primary",
            },
            {
                "title": "Linked Participants",
                "value": linked_count,
                "icon": "bi-link-45deg",
                "color": "success",
            },
            {
                "title": "Unlinked Players",
                "value": unlinked_count,
                "icon": "bi-exclamation-triangle",
                "color": "warning" if unlinked_count > 0 else "secondary",
            },
            {
                "title": "Linking Coverage",
                "value": f"{linking_pct:.0f}%",
                "icon": "bi-diagram-3",
                "color": "info",
            },
        ]

        return create_metric_grid(metrics)

    except Exception as e:
        return create_empty_state(f"Error loading metrics: {str(e)}")


@callback(
    Output("h2h-player1-selector", "options"),
    Input("refresh-interval", "n_intervals"),
)
def update_h2h_player1_options(n_intervals: int) -> List[Dict[str, str]]:
    """Update Player 1 selector options.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        List of player options sorted by activity
    """
    try:
        queries = get_queries()
        df = queries.get_player_performance()

        if df.empty:
            return []

        # Create player options sorted by activity
        options = []
        for _, player in df.sort_values("total_matches", ascending=False).iterrows():
            label = f"{player['player_name']} ({player['total_matches']} matches)"
            options.append({"label": label, "value": player["player_name"]})

        return options

    except Exception as e:
        logger.error(f"Error updating H2H Player 1 options: {e}")
        return []


@callback(
    [
        Output("h2h-player2-selector", "options"),
        Output("h2h-player2-selector", "value"),
        Output("h2h-player2-selector", "disabled"),
    ],
    Input("h2h-player1-selector", "value"),
)
def update_h2h_player2_options(
    player1: Optional[str],
) -> tuple[List[Dict[str, str]], Optional[str], bool]:
    """Update Player 2 selector options based on Player 1 selection.

    Args:
        player1: Selected Player 1 name

    Returns:
        Tuple of (player2_options, player2_value, disabled)
    """
    if not player1:
        # Player 1 not selected - disable Player 2
        return [], None, True

    try:
        queries = get_queries()
        opponents = queries.get_opponents(player1)

        if not opponents:
            # No opponents found - disable Player 2
            return [], None, True

        # Create opponent options (already sorted alphabetically by query)
        options = [{"label": name, "value": name} for name in opponents]

        # Enable Player 2 dropdown
        return options, None, False

    except Exception as e:
        logger.error(f"Error updating H2H Player 2 options: {e}")
        return [], None, True


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
        List of player ranking data with visual indicators for unlinked players
    """
    try:
        queries = get_queries()
        df = queries.get_player_performance()

        if df.empty:
            return []

        # Sort by win rate and add rank
        df = df.sort_values("win_rate", ascending=False).reset_index(drop=True)
        df["rank"] = range(1, len(df) + 1)

        # Convert win rate to percentage for display (already 0-100, need 0-1 for formatter)
        df["win_rate"] = df["win_rate"] / 100

        # Create display columns with indicators
        df["player_display"] = df.apply(
            lambda row: (
                f"⚠️ {row['player_name']}"  # Warning emoji for unlinked
                if row["is_unlinked"]
                else row["player_name"]
            ),
            axis=1,
        )

        # Format civilizations with favorite highlighted
        df["civilizations_display"] = df.apply(
            lambda row: _format_civilizations_display(
                row["civilizations_played"], row["favorite_civilization"]
            ),
            axis=1,
        )

        return df.to_dict("records")

    except Exception as e:
        logger.error(f"Error updating rankings table: {e}")
        return []
