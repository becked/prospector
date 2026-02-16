"""Player performance analytics page.

This page provides comprehensive player statistics, skill ratings,
and performance comparisons.
"""

import logging
from typing import Any, Dict, List, Optional

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, callback, dcc, html

from tournament_visualizer.components.charts import (
    create_skill_radar_chart,
)
from tournament_visualizer.components.layouts import (
    create_data_table_card,
    create_empty_state,
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
        # Download component for exports
        dcc.Download(id="skill-rankings-download"),
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
                    "label": "Skill Ratings",
                    "tab_id": "skill-ratings",
                    "content": [
                        # Full-width table
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_data_table_card(
                                            title=None,
                                            table_id="skill-rankings-table",
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
                                                    "name": "Score",
                                                    "id": "skill_score",
                                                    "type": "numeric",
                                                    "format": {"specifier": ".1f"},
                                                },
                                                {
                                                    "name": "Matches",
                                                    "id": "matches_played",
                                                    "type": "numeric",
                                                },
                                                {
                                                    "name": "Civilizations",
                                                    "id": "civilizations_display",
                                                    "presentation": "markdown",
                                                },
                                                {
                                                    "name": "Win",
                                                    "id": "win_component",
                                                    "type": "numeric",
                                                    "format": {"specifier": ".0f"},
                                                },
                                                {
                                                    "name": "Econ",
                                                    "id": "economy_component",
                                                    "type": "numeric",
                                                    "format": {"specifier": ".0f"},
                                                },
                                                {
                                                    "name": "Gov",
                                                    "id": "governance_component",
                                                    "type": "numeric",
                                                    "format": {"specifier": ".0f"},
                                                },
                                                {
                                                    "name": "Mil",
                                                    "id": "military_component",
                                                    "type": "numeric",
                                                    "format": {"specifier": ".0f"},
                                                },
                                            ],
                                        ),
                                    ],
                                    width=12,
                                ),
                            ]
                        ),
                        # Methodology reference
                        dbc.Card(
                            [
                                dbc.CardHeader("Reference"),
                                dbc.CardBody(
                                    [
                                        html.P(
                                            "The skill score combines four components into a single 0-100 rating:",
                                            className="mb-2",
                                        ),
                                        html.Pre(
                                            "Score = (Win + Economy + Governance + Military) × 0.25 each",
                                            className="bg-dark p-2 rounded small",
                                        ),
                                        html.H6("Components", className="mt-4 mb-3"),
                                        html.Div(
                                            [
                                                html.Div(
                                                    [
                                                        html.Strong("Win (25%): "),
                                                        html.Span(
                                                            "Win rate (70%) + Victory point margin (30%)"
                                                        ),
                                                    ],
                                                    className="mb-2",
                                                ),
                                                html.Div(
                                                    [
                                                        html.Strong("Economy (25%): "),
                                                        html.Span(
                                                            "Total productive yields per turn (science, civics, training, culture, money, growth, food, orders)"
                                                        ),
                                                    ],
                                                    className="mb-2",
                                                ),
                                                html.Div(
                                                    [
                                                        html.Strong("Governance (25%): "),
                                                        html.Span(
                                                            "Legitimacy (33%) + Expansion rate (33%) + Law adoption rate (33%)"
                                                        ),
                                                    ],
                                                    className="mb-2",
                                                ),
                                                html.Div(
                                                    [
                                                        html.Strong("Military (25%): "),
                                                        html.Span(
                                                            "Military power (40%) + Army diversity (20%) + Power lead (40%)"
                                                        ),
                                                    ],
                                                    className="mb-2",
                                                ),
                                            ]
                                        ),
                                        html.H6("Normalization", className="mt-4 mb-3"),
                                        html.Ul(
                                            [
                                                html.Li(
                                                    "All metrics are converted to percentiles within the tournament population"
                                                ),
                                                html.Li(
                                                    "Per-game metrics are weighted by game length (longer games count more)"
                                                ),
                                                html.Li(
                                                    "Economy yields are normalized by game length to avoid penalizing quick wins"
                                                ),
                                                html.Li(
                                                    [
                                                        html.Span("Players with "),
                                                        html.Strong("<3 matches"),
                                                        html.Span(
                                                            " have their scores regressed toward the population mean"
                                                        ),
                                                    ]
                                                ),
                                            ],
                                            className="small mb-0",
                                        ),
                                    ]
                                ),
                            ],
                            className="mt-4",
                        ),
                    ],
                },
                {
                    "label": "Skills Comparison",
                    "tab_id": "skills-comparison",
                    "content": [
                        # Radar chart with selector on right
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Card(
                                            dbc.CardBody(
                                                dcc.Graph(
                                                    id="skill-radar-chart",
                                                    config={"displayModeBar": False},
                                                    style={"height": "500px"},
                                                ),
                                            ),
                                        ),
                                    ],
                                    lg=8,
                                    md=12,
                                ),
                                dbc.Col(
                                    [
                                        # Dimensions legend
                                        dbc.Card(
                                            [
                                                dbc.CardHeader("Dimensions"),
                                                dbc.CardBody(
                                                    [
                                                        html.Ul(
                                                            [
                                                                html.Li([
                                                                    html.Strong("Win Rate: "),
                                                                    html.Span("Match win percentage"),
                                                                ]),
                                                                html.Li([
                                                                    html.Strong("Win Margin: "),
                                                                    html.Span("Average victory point lead in wins"),
                                                                ]),
                                                                html.Li([
                                                                    html.Strong("Yields: "),
                                                                    html.Span("Total productive output per turn"),
                                                                ]),
                                                                html.Li([
                                                                    html.Strong("Expansion: "),
                                                                    html.Span("City founding rate"),
                                                                ]),
                                                                html.Li([
                                                                    html.Strong("Legitimacy: "),
                                                                    html.Span("Average governance stability"),
                                                                ]),
                                                                html.Li([
                                                                    html.Strong("Law Rate: "),
                                                                    html.Span("Laws adopted per 100 turns"),
                                                                ]),
                                                                html.Li([
                                                                    html.Strong("Military: "),
                                                                    html.Span("Military power, army diversity, power lead"),
                                                                ]),
                                                            ],
                                                            className="small mb-0",
                                                        ),
                                                    ]
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        # Player selector
                                        dbc.Card(
                                            [
                                                dbc.CardHeader("Select Players"),
                                                dbc.CardBody(
                                                    [
                                                        html.P(
                                                            "Select players to compare",
                                                            className="text-muted small mb-2",
                                                        ),
                                                        dcc.Dropdown(
                                                            id="skill-compare-selector",
                                                            placeholder="Select players...",
                                                            options=[],
                                                            multi=True,
                                                        ),
                                                    ]
                                                ),
                                            ],
                                        ),
                                    ],
                                    lg=4,
                                    md=12,
                                    className="mt-4 mt-lg-0",
                                ),
                            ]
                        ),
                    ],
                },
            ],
            active_tab="skill-ratings",
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


# Skill Ratings tab callbacks
@callback(
    Output("skill-rankings-table", "data"),
    Input("_pages_location", "pathname"),
)
def update_skill_rankings_table(pathname: str) -> List[Dict[str, Any]]:
    """Update skill rankings table.

    Args:
        pathname: Current page path (triggers on page load)

    Returns:
        List of skill ranking data with civilizations
    """
    try:
        queries = get_queries()
        df = queries.get_player_skill_ratings()

        if df.empty:
            return []

        # Get civilization data from player performance
        perf_df = queries.get_player_performance()
        if not perf_df.empty:
            civ_data = perf_df[["player_name", "civilizations_played", "favorite_civilization"]]
            df = df.merge(civ_data, on="player_name", how="left")

            # Format civilizations display
            df["civilizations_display"] = df.apply(
                lambda row: _format_civilizations_display(
                    row.get("civilizations_played", ""),
                    row.get("favorite_civilization", "")
                ),
                axis=1,
            )
        else:
            df["civilizations_display"] = "—"

        # Add rank
        df["rank"] = range(1, len(df) + 1)

        # Use player name directly for display
        df["player_display"] = df["player_name"]

        return df.to_dict("records")

    except Exception as e:
        logger.error(f"Error updating skill rankings table: {e}")
        return []


@callback(
    Output("skill-compare-selector", "options"),
    Input("_pages_location", "pathname"),
)
def update_skill_compare_options(pathname: str) -> List[Dict[str, str]]:
    """Update skill comparison player selector options.

    Args:
        pathname: Current page path (triggers on page load)

    Returns:
        List of player options for radar chart comparison
    """
    try:
        queries = get_queries()
        df = queries.get_player_skill_ratings()

        if df.empty:
            return []

        # Create options sorted by skill score
        options = []
        for _, player in df.iterrows():
            score = player["skill_score"]
            label = f"{player['player_name']} ({score:.0f})"
            options.append({"label": label, "value": player["player_name"]})

        return options

    except Exception as e:
        logger.error(f"Error updating skill compare options: {e}")
        return []


@callback(
    Output("skill-radar-chart", "figure"),
    Input("skill-compare-selector", "value"),
)
def update_skill_radar_chart(selected_players: Optional[List[str]]):
    """Update skill radar chart based on selected players.

    Args:
        selected_players: List of selected player names

    Returns:
        Radar chart figure comparing selected players
    """
    if not selected_players:
        return create_skill_radar_chart([])

    try:
        queries = get_queries()
        df = queries.get_player_skill_ratings()

        if df.empty:
            return create_skill_radar_chart([])

        # Filter to selected players
        selected = df[df["player_name"].isin(selected_players)]

        if selected.empty:
            return create_skill_radar_chart([])

        # Convert to list of dicts for chart function
        players_data = selected.to_dict("records")

        return create_skill_radar_chart(players_data)

    except Exception as e:
        logger.error(f"Error updating skill radar chart: {e}")
        return create_skill_radar_chart([])


@callback(
    Output("skill-rankings-download", "data"),
    Input("skill-rankings-table-export", "n_clicks"),
    prevent_initial_call=True,
)
def export_skill_rankings(n_clicks: int) -> dict:
    """Export skill rankings table to CSV.

    Args:
        n_clicks: Number of export button clicks

    Returns:
        Download data dict for CSV file
    """
    if not n_clicks:
        return dash.no_update

    try:
        queries = get_queries()
        df = queries.get_player_skill_ratings()

        if df.empty:
            return dash.no_update

        # Select columns for export
        export_cols = [
            "player_name",
            "skill_score",
            "matches_played",
            "win_rate",
            "win_component",
            "economy_component",
            "governance_component",
            "military_component",
        ]
        export_df = df[[c for c in export_cols if c in df.columns]]

        return dcc.send_data_frame(export_df.to_csv, "skill_rankings.csv", index=False)

    except Exception as e:
        logger.error(f"Error exporting skill rankings: {e}")
        return dash.no_update
