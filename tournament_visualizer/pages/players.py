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
            actions=[
                dbc.Button(
                    [html.I(className="bi bi-arrow-clockwise me-2"), "Refresh"],
                    id="players-refresh-btn",
                    color="outline-primary",
                    size="sm",
                )
            ],
        ),
        # Filters section
        create_filter_card(
            title="Filters",
            filters=[
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                create_date_range_filter(
                                    "players-date", default_range="all"
                                )
                            ],
                            width=4,
                        ),
                        dbc.Col(
                            [create_civilization_filter("players-civilizations")],
                            width=4,
                        ),
                        dbc.Col(
                            [
                                html.Label(
                                    "Minimum Matches:", className="form-label fw-bold"
                                ),
                                dcc.Slider(
                                    id="min-matches-slider",
                                    min=1,
                                    max=20,
                                    step=1,
                                    value=1,
                                    marks={i: str(i) for i in range(1, 21, 2)},
                                    tooltip={
                                        "placement": "bottom",
                                        "always_visible": True,
                                    },
                                ),
                            ],
                            width=4,
                        ),
                    ]
                )
            ],
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
                        # Performance charts
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Top Players by Win Rate",
                                            chart_id="players-winrate-chart",
                                            height="500px",
                                        )
                                    ],
                                    width=6,
                                ),
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Player Activity (Total Matches)",
                                            chart_id="players-activity-chart",
                                            height="500px",
                                        )
                                    ],
                                    width=6,
                                ),
                            ],
                            className="mb-4",
                        ),
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
                    "label": "Civilization Analysis",
                    "tab_id": "civilizations",
                    "content": [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Civilization Win Rates",
                                            chart_id="civilization-performance-chart",
                                            height="400px",
                                        )
                                    ],
                                    width=8,
                                ),
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Civilization Popularity",
                                            chart_id="civilization-popularity-chart",
                                            height="400px",
                                        )
                                    ],
                                    width=4,
                                ),
                            ],
                            className="mb-4",
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_data_table_card(
                                            title="Civilization Statistics",
                                            table_id="civilization-stats-table",
                                            columns=[
                                                {
                                                    "name": "Civilization",
                                                    "id": "civilization",
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
                                                    "name": "Players",
                                                    "id": "unique_players",
                                                    "type": "numeric",
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
                {
                    "label": "Performance Trends",
                    "tab_id": "trends",
                    "content": [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Player vs Civilization Matrix",
                                            chart_id="player-civ-heatmap",
                                            height="600px",
                                        )
                                    ],
                                    width=12,
                                )
                            ],
                            className="mb-4",
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Performance Over Time",
                                            chart_id="performance-timeline",
                                            height="400px",
                                        )
                                    ],
                                    width=12,
                                )
                            ]
                        ),
                    ],
                },
            ],
            active_tab="rankings",
        ),
    ]
)


@callback(
    Output("player-summary-metrics", "children"),
    [
        Input("players-date-dropdown", "value"),
        Input("players-civilizations-dropdown", "value"),
        Input("min-matches-slider", "value"),
        Input("players-refresh-btn", "n_clicks"),
    ],
)
def update_player_summary_metrics(
    date_range: Optional[int],
    civilizations: Optional[List[str]],
    min_matches: int,
    refresh_clicks: int,
) -> html.Div:
    """Update player summary metrics.

    Args:
        date_range: Selected date range in days
        civilizations: Selected civilizations filter
        min_matches: Minimum matches threshold
        refresh_clicks: Number of refresh button clicks

    Returns:
        Metrics grid component
    """
    try:
        queries = get_queries()
        df = queries.get_player_performance()

        if df.empty:
            return create_empty_state("No player data available")

        # Apply filters
        filtered_df = df[df["total_matches"] >= min_matches]

        if civilizations:
            filtered_df = filtered_df[filtered_df["civilization"].isin(civilizations)]

        # Calculate summary metrics
        total_players = len(filtered_df)
        avg_win_rate = filtered_df["win_rate"].mean()
        most_active = (
            filtered_df.loc[filtered_df["total_matches"].idxmax()]
            if not filtered_df.empty
            else None
        )
        top_performer = (
            filtered_df.loc[filtered_df["win_rate"].idxmax()]
            if not filtered_df.empty
            else None
        )

        metrics = [
            {
                "title": "Active Players",
                "value": total_players,
                "icon": "bi-people",
                "color": "primary",
            },
            {
                "title": "Average Win Rate",
                "value": f"{avg_win_rate:.1f}%" if pd.notna(avg_win_rate) else "N/A",
                "icon": "bi-percent",
                "color": "info",
            },
            {
                "title": "Most Active",
                "value": (
                    most_active["player_name"] if most_active is not None else "N/A"
                ),
                "subtitle": (
                    f"{most_active['total_matches']} matches"
                    if most_active is not None
                    else ""
                ),
                "icon": "bi-activity",
                "color": "success",
            },
            {
                "title": "Top Performer",
                "value": (
                    top_performer["player_name"] if top_performer is not None else "N/A"
                ),
                "subtitle": (
                    f"{top_performer['win_rate']:.1f}% win rate"
                    if top_performer is not None
                    else ""
                ),
                "icon": "bi-trophy",
                "color": "warning",
            },
        ]

        return create_metric_grid(metrics)

    except Exception as e:
        return create_empty_state(f"Error loading metrics: {str(e)}")


@callback(
    Output("players-winrate-chart", "figure"),
    [
        Input("players-date-dropdown", "value"),
        Input("players-civilizations-dropdown", "value"),
        Input("min-matches-slider", "value"),
        Input("players-refresh-btn", "n_clicks"),
    ],
)
def update_winrate_chart(
    date_range: Optional[int],
    civilizations: Optional[List[str]],
    min_matches: int,
    refresh_clicks: int,
):
    """Update player win rate chart.

    Args:
        date_range: Selected date range in days
        civilizations: Selected civilizations filter
        min_matches: Minimum matches threshold
        refresh_clicks: Number of refresh button clicks

    Returns:
        Plotly figure for win rate chart
    """
    try:
        queries = get_queries()
        df = queries.get_player_performance()

        if df.empty:
            return create_empty_chart_placeholder("No player data available")

        # Apply filters
        filtered_df = df[df["total_matches"] >= min_matches]

        if civilizations:
            filtered_df = filtered_df[filtered_df["civilization"].isin(civilizations)]

        if filtered_df.empty:
            return create_empty_chart_placeholder(
                "No players match the selected criteria"
            )

        return create_player_performance_chart(filtered_df.head(15))

    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading win rate data: {str(e)}")


@callback(
    Output("players-activity-chart", "figure"),
    [
        Input("players-date-dropdown", "value"),
        Input("players-civilizations-dropdown", "value"),
        Input("min-matches-slider", "value"),
        Input("players-refresh-btn", "n_clicks"),
    ],
)
def update_activity_chart(
    date_range: Optional[int],
    civilizations: Optional[List[str]],
    min_matches: int,
    refresh_clicks: int,
):
    """Update player activity chart.

    Args:
        date_range: Selected date range in days
        civilizations: Selected civilizations filter
        min_matches: Minimum matches threshold
        refresh_clicks: Number of refresh button clicks

    Returns:
        Plotly figure for activity chart
    """
    try:
        queries = get_queries()
        df = queries.get_player_performance()

        if df.empty:
            return create_empty_chart_placeholder("No player data available")

        # Apply filters
        filtered_df = df[df["total_matches"] >= min_matches]

        if civilizations:
            filtered_df = filtered_df[filtered_df["civilization"].isin(civilizations)]

        if filtered_df.empty:
            return create_empty_chart_placeholder(
                "No players match the selected criteria"
            )

        # Sort by total matches and take top 15
        top_active = filtered_df.sort_values("total_matches", ascending=True).tail(15)

        import plotly.graph_objects as go

        fig = create_base_figure(
            title="Most Active Players", x_title="Total Matches", y_title="Player"
        )

        fig.add_trace(
            go.Bar(
                x=top_active["total_matches"],
                y=top_active["player_name"],
                orientation="h",
                marker_color="lightgreen",
                text=top_active["total_matches"],
                textposition="auto",
            )
        )

        return fig

    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading activity data: {str(e)}")


@callback(
    Output("civilization-performance-chart", "figure"),
    [
        Input("players-date-dropdown", "value"),
        Input("players-civilizations-dropdown", "value"),
        Input("players-refresh-btn", "n_clicks"),
    ],
)
def update_civilization_performance_chart(
    date_range: Optional[int], civilizations: Optional[List[str]], refresh_clicks: int
):
    """Update civilization performance chart.

    Args:
        date_range: Selected date range in days
        civilizations: Selected civilizations filter
        refresh_clicks: Number of refresh button clicks

    Returns:
        Plotly figure for civilization performance
    """
    try:
        queries = get_queries()
        df = queries.get_civilization_performance()

        if df.empty:
            return create_empty_chart_placeholder("No civilization data available")

        # Apply civilization filter
        if civilizations:
            df = df[df["civilization"].isin(civilizations)]

        return create_civilization_performance_chart(df)

    except Exception as e:
        return create_empty_chart_placeholder(
            f"Error loading civilization data: {str(e)}"
        )


@callback(
    Output("civilization-popularity-chart", "figure"),
    [
        Input("players-date-dropdown", "value"),
        Input("players-civilizations-dropdown", "value"),
        Input("players-refresh-btn", "n_clicks"),
    ],
)
def update_civilization_popularity_chart(
    date_range: Optional[int], civilizations: Optional[List[str]], refresh_clicks: int
):
    """Update civilization popularity chart.

    Args:
        date_range: Selected date range in days
        civilizations: Selected civilizations filter
        refresh_clicks: Number of refresh button clicks

    Returns:
        Plotly figure for civilization popularity
    """
    try:
        queries = get_queries()
        df = queries.get_civilization_performance()

        if df.empty:
            return create_empty_chart_placeholder("No civilization data available")

        # Apply civilization filter
        if civilizations:
            df = df[df["civilization"].isin(civilizations)]

        import plotly.graph_objects as go

        fig = create_base_figure(title="Civilization Popularity", show_legend=False)

        fig.add_trace(
            go.Pie(labels=df["civilization"], values=df["total_matches"], hole=0.3)
        )

        return fig

    except Exception as e:
        return create_empty_chart_placeholder(
            f"Error loading popularity data: {str(e)}"
        )


@callback(
    [
        Output("h2h-player1-selector", "options"),
        Output("h2h-player2-selector", "options"),
    ],
    Input("players-refresh-btn", "n_clicks"),
)
def update_h2h_player_options(refresh_clicks: int) -> tuple:
    """Update head-to-head player selector options.

    Args:
        refresh_clicks: Number of refresh button clicks

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
    [
        Input("players-date-dropdown", "value"),
        Input("players-civilizations-dropdown", "value"),
        Input("min-matches-slider", "value"),
        Input("players-refresh-btn", "n_clicks"),
    ],
)
def update_rankings_table(
    date_range: Optional[int],
    civilizations: Optional[List[str]],
    min_matches: int,
    refresh_clicks: int,
) -> List[Dict[str, Any]]:
    """Update player rankings table.

    Args:
        date_range: Selected date range in days
        civilizations: Selected civilizations filter
        min_matches: Minimum matches threshold
        refresh_clicks: Number of refresh button clicks

    Returns:
        List of player ranking data
    """
    try:
        queries = get_queries()
        df = queries.get_player_performance()

        if df.empty:
            return []

        # Apply filters
        filtered_df = df[df["total_matches"] >= min_matches]

        if civilizations:
            filtered_df = filtered_df[filtered_df["civilization"].isin(civilizations)]

        # Sort by win rate and add rank
        filtered_df = filtered_df.sort_values("win_rate", ascending=False).reset_index(
            drop=True
        )
        filtered_df["rank"] = range(1, len(filtered_df) + 1)

        # Convert win rate to percentage for display
        filtered_df["win_rate"] = filtered_df["win_rate"] / 100

        return filtered_df.to_dict("records")

    except Exception as e:
        logger.error(f"Error updating rankings table: {e}")
        return []


@callback(
    Output("civilization-stats-table", "data"),
    [
        Input("players-date-dropdown", "value"),
        Input("players-civilizations-dropdown", "value"),
        Input("players-refresh-btn", "n_clicks"),
    ],
)
def update_civilization_stats_table(
    date_range: Optional[int], civilizations: Optional[List[str]], refresh_clicks: int
) -> List[Dict[str, Any]]:
    """Update civilization statistics table.

    Args:
        date_range: Selected date range in days
        civilizations: Selected civilizations filter
        refresh_clicks: Number of refresh button clicks

    Returns:
        List of civilization statistics data
    """
    try:
        queries = get_queries()
        df = queries.get_civilization_performance()

        if df.empty:
            return []

        # Apply civilization filter
        if civilizations:
            df = df[df["civilization"].isin(civilizations)]

        # Convert win rate to percentage for display
        df["win_rate"] = df["win_rate"] / 100

        return df.sort_values("win_rate", ascending=False).to_dict("records")

    except Exception as e:
        logger.error(f"Error updating civilization stats table: {e}")
        return []


@callback(
    Output("player-civ-heatmap", "figure"),
    [
        Input("players-date-dropdown", "value"),
        Input("players-civilizations-dropdown", "value"),
        Input("min-matches-slider", "value"),
        Input("players-refresh-btn", "n_clicks"),
    ],
)
def update_player_civ_heatmap(
    date_range: Optional[int],
    civilizations: Optional[List[str]],
    min_matches: int,
    refresh_clicks: int,
):
    """Update player vs civilization heatmap.

    Args:
        date_range: Selected date range in days
        civilizations: Selected civilizations filter
        min_matches: Minimum matches threshold
        refresh_clicks: Number of refresh button clicks

    Returns:
        Plotly figure for player-civ heatmap
    """
    try:
        queries = get_queries()
        df = queries.get_player_performance()

        if df.empty:
            return create_empty_chart_placeholder("No player data available")

        # Apply filters
        filtered_df = df[df["total_matches"] >= min_matches]

        if civilizations:
            filtered_df = filtered_df[filtered_df["civilization"].isin(civilizations)]

        if filtered_df.empty:
            return create_empty_chart_placeholder(
                "No players match the selected criteria"
            )

        # Create pivot table for heatmap
        # Group by player and civilization, sum wins
        pivot_data = (
            filtered_df.groupby(["player_name", "civilization"])
            .agg({"wins": "sum", "total_matches": "sum"})
            .reset_index()
        )

        # Calculate win rate
        pivot_data["win_rate"] = (
            pivot_data["wins"] / pivot_data["total_matches"] * 100
        ).fillna(0)

        # Pivot to create matrix
        heatmap_data = pivot_data.pivot_table(
            index="player_name", columns="civilization", values="win_rate", fill_value=0
        )

        if heatmap_data.empty:
            return create_empty_chart_placeholder("Insufficient data for heatmap")

        import plotly.graph_objects as go

        fig = create_base_figure(
            title="Player Performance by Civilization",
            x_title="Civilization",
            y_title="Player",
        )

        fig.add_trace(
            go.Heatmap(
                z=heatmap_data.values,
                x=heatmap_data.columns,
                y=heatmap_data.index,
                colorscale="RdYlGn",
                text=heatmap_data.values.round(1),
                texttemplate="%{text}%",
                textfont={"size": 10},
                colorbar=dict(title="Win Rate %"),
            )
        )

        fig.update_layout(
            xaxis_tickangle=-45,
            height=max(400, len(heatmap_data) * 30),  # Dynamic height based on players
        )

        return fig

    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading heatmap: {str(e)}")


@callback(
    Output("performance-timeline", "figure"),
    [
        Input("players-date-dropdown", "value"),
        Input("players-civilizations-dropdown", "value"),
        Input("min-matches-slider", "value"),
        Input("players-refresh-btn", "n_clicks"),
    ],
)
def update_performance_timeline(
    date_range: Optional[int],
    civilizations: Optional[List[str]],
    min_matches: int,
    refresh_clicks: int,
):
    """Update performance over time chart.

    Args:
        date_range: Selected date range in days
        civilizations: Selected civilizations filter
        min_matches: Minimum matches threshold
        refresh_clicks: Number of refresh button clicks

    Returns:
        Plotly figure for performance timeline
    """
    try:
        from tournament_visualizer.data.database import get_database

        db = get_database()

        # Get match results with dates
        query = """
        SELECT
            m.save_date,
            p.player_name,
            p.civilization,
            CASE WHEN m.winner_player_id = p.player_id THEN 1 ELSE 0 END as won
        FROM matches m
        JOIN players p ON m.match_id = p.match_id
        WHERE m.save_date IS NOT NULL
        ORDER BY m.save_date
        """

        result = db.fetch_all(query, {})

        if not result:
            return create_empty_chart_placeholder("No match history data available")

        df = pd.DataFrame(
            result, columns=["save_date", "player_name", "civilization", "won"]
        )
        df["save_date"] = pd.to_datetime(df["save_date"])

        # Apply filters
        if civilizations:
            df = df[df["civilization"].isin(civilizations)]

        # Get players with enough matches
        player_match_counts = df.groupby("player_name").size()
        qualified_players = player_match_counts[
            player_match_counts >= min_matches
        ].index
        df = df[df["player_name"].isin(qualified_players)]

        if df.empty:
            return create_empty_chart_placeholder(
                "No players match the selected criteria"
            )

        # Calculate cumulative win rate over time for top players
        top_players = df.groupby("player_name").size().nlargest(10).index
        df_top = df[df["player_name"].isin(top_players)]

        import plotly.graph_objects as go

        fig = create_base_figure(
            title="Player Performance Over Time",
            x_title="Date",
            y_title="Cumulative Win Rate %",
        )

        for player in top_players:
            player_data = df_top[df_top["player_name"] == player].sort_values(
                "save_date"
            )
            player_data["cumulative_wins"] = player_data["won"].cumsum()
            player_data["match_number"] = range(1, len(player_data) + 1)
            player_data["cumulative_win_rate"] = (
                player_data["cumulative_wins"] / player_data["match_number"] * 100
            )

            fig.add_trace(
                go.Scatter(
                    x=player_data["save_date"],
                    y=player_data["cumulative_win_rate"],
                    mode="lines+markers",
                    name=player,
                    line=dict(width=2),
                    marker=dict(size=6),
                )
            )

        return fig

    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading timeline: {str(e)}")
