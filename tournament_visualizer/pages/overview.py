"""Tournament overview dashboard page.

This page provides a high-level overview of tournament statistics,
recent matches, and key performance indicators.
"""

import logging
from typing import Any, Dict, List, Optional

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, callback, dcc, html

from tournament_visualizer.components.charts import (
    create_aggregated_event_category_timeline_chart,
    create_empty_chart_placeholder,
    create_law_efficiency_scatter,
    create_law_milestone_distribution_chart,
    create_legitimacy_progression_chart,
    create_map_breakdown_actual_sunburst_chart,
    create_military_progression_chart,
    create_nation_counter_pick_heatmap,
    create_nation_loss_percentage_chart,
    create_nation_popularity_chart,
    create_nation_win_percentage_chart,
    create_orders_progression_chart,
    create_pick_order_win_rate_chart,
    create_ruler_archetype_matchup_matrix,
    create_ruler_archetype_trait_combinations_chart,
    create_ruler_archetype_win_rates_chart,
    create_ruler_trait_performance_chart,
    create_science_progression_chart,
    create_summary_metrics_cards,
    create_tournament_expansion_timeline_chart,
    create_tournament_production_strategies_chart,
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
        ),
        # Alert area
        html.Div(id="overview-alerts"),
        # Filters (above tabs)
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H5(
                                            "Filters",
                                            className="card-title mb-3",
                                        ),
                                        # Row 1: Tournament filters
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "Tournament Bracket",
                                                            className="fw-bold mb-2",
                                                        ),
                                                        dcc.Dropdown(
                                                            id="overview-bracket-filter-dropdown",
                                                            options=[
                                                                {
                                                                    "label": "All Brackets",
                                                                    "value": "all",
                                                                },
                                                                {
                                                                    "label": "Winners Bracket",
                                                                    "value": "Winners",
                                                                },
                                                                {
                                                                    "label": "Losers Bracket",
                                                                    "value": "Losers",
                                                                },
                                                                {
                                                                    "label": "Unknown",
                                                                    "value": "Unknown",
                                                                },
                                                            ],
                                                            value="all",
                                                            clearable=False,
                                                            className="mb-3",
                                                        ),
                                                    ],
                                                    width=3,
                                                ),
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "Tournament Round",
                                                            className="fw-bold mb-2",
                                                        ),
                                                        dcc.Dropdown(
                                                            id="overview-round-filter-dropdown",
                                                            options=[],
                                                            value=None,
                                                            placeholder="All Rounds",
                                                            clearable=True,
                                                            className="mb-3",
                                                        ),
                                                    ],
                                                    width=3,
                                                ),
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "Min Turns",
                                                            className="fw-bold mb-2",
                                                        ),
                                                        dcc.Input(
                                                            id="overview-min-turns-input",
                                                            type="number",
                                                            placeholder="Min",
                                                            className="form-control mb-3",
                                                        ),
                                                    ],
                                                    width=3,
                                                ),
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "Max Turns",
                                                            className="fw-bold mb-2",
                                                        ),
                                                        dcc.Input(
                                                            id="overview-max-turns-input",
                                                            type="number",
                                                            placeholder="Max",
                                                            className="form-control mb-3",
                                                        ),
                                                    ],
                                                    width=3,
                                                ),
                                            ]
                                        ),
                                        # Row 2: Map filters
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "Map Size",
                                                            className="fw-bold mb-2",
                                                        ),
                                                        dcc.Dropdown(
                                                            id="overview-map-size-dropdown",
                                                            options=[],
                                                            value=None,
                                                            placeholder="All Sizes",
                                                            clearable=True,
                                                            className="mb-3",
                                                        ),
                                                    ],
                                                    width=4,
                                                ),
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "Map Class",
                                                            className="fw-bold mb-2",
                                                        ),
                                                        dcc.Dropdown(
                                                            id="overview-map-class-dropdown",
                                                            options=[],
                                                            value=None,
                                                            placeholder="All Classes",
                                                            clearable=True,
                                                            className="mb-3",
                                                        ),
                                                    ],
                                                    width=4,
                                                ),
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "Map Aspect",
                                                            className="fw-bold mb-2",
                                                        ),
                                                        dcc.Dropdown(
                                                            id="overview-map-aspect-dropdown",
                                                            options=[],
                                                            value=None,
                                                            placeholder="All Aspects",
                                                            clearable=True,
                                                            className="mb-3",
                                                        ),
                                                    ],
                                                    width=4,
                                                ),
                                            ]
                                        ),
                                        # Row 3: Player and Nation filters
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "Nations",
                                                            className="fw-bold mb-2",
                                                        ),
                                                        dcc.Dropdown(
                                                            id="overview-nations-dropdown",
                                                            options=[],
                                                            value=None,
                                                            placeholder="All Nations",
                                                            multi=True,
                                                            className="mb-3",
                                                        ),
                                                    ],
                                                    width=6,
                                                ),
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "Players",
                                                            className="fw-bold mb-2",
                                                        ),
                                                        dcc.Dropdown(
                                                            id="overview-players-dropdown",
                                                            options=[],
                                                            value=None,
                                                            placeholder="All Players",
                                                            multi=True,
                                                            className="mb-3",
                                                        ),
                                                    ],
                                                    width=6,
                                                ),
                                            ]
                                        ),
                                    ]
                                )
                            ]
                        )
                    ],
                    width=12,
                )
            ],
            className="mb-4",
        ),
        # Tabbed interface
        dbc.Tabs(
            [
                # Tab 1: Summary
                dbc.Tab(
                    label="Summary",
                    tab_id="summary-tab",
                    children=[
                        # Summary metrics
                        html.Div(id="overview-metrics", className="mt-3"),
                        # Tournament Round Statistics
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Card(
                                            [
                                                dbc.CardBody(
                                                    [
                                                        html.H5(
                                                            "Tournament Rounds",
                                                            className="card-title",
                                                        ),
                                                        html.Div(
                                                            id="overview-round-stats-content"
                                                        ),
                                                    ]
                                                )
                                            ]
                                        )
                                    ],
                                    width=4,
                                ),
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Event Category Timeline",
                                            chart_id="overview-event-timeline",
                                            height="450px",
                                        )
                                    ],
                                    width=8,
                                ),
                            ],
                            className="mb-4",
                        ),
                        # Unit and Map breakdown charts
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Military Unit Breakdown",
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
                        # Matches table
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_data_table_card(
                                            title="Matches",
                                            table_id="overview-matches-table",
                                            columns=[
                                                {
                                                    "name": "Match",
                                                    "id": "match_link",
                                                    "presentation": "markdown",
                                                },
                                                {
                                                    "name": "Date",
                                                    "id": "save_date",
                                                    "type": "datetime",
                                                },
                                                {
                                                    "name": "Round",
                                                    "id": "round_display",
                                                },
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
                            ],
                            className="mb-4",
                        ),
                    ],
                ),
                # Tab 2: Nations
                dbc.Tab(
                    label="Nations",
                    tab_id="nations-tab",
                    children=[
                        # Nation performance charts - 3 pie charts in a row
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
                            className="mb-4 mt-3",
                        ),
                        # Counter-Pick Analysis - heatmap and win rate chart
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Nation Counter-Pick Effectiveness",
                                            chart_id="overview-counter-pick-heatmap",
                                            height="550px",
                                        )
                                    ],
                                    width=8,
                                ),
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Pick Order Win Rate",
                                            chart_id="overview-pick-order-win-rate",
                                            height="550px",
                                        )
                                    ],
                                    width=4,
                                ),
                            ],
                            className="mb-4",
                        ),
                    ],
                ),
                # Tab 3: Rulers
                dbc.Tab(
                    label="Rulers",
                    tab_id="rulers-tab",
                    children=[
                        # Ruler performance charts
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Archetype Performance",
                                            chart_id="overview-ruler-archetype-chart",
                                            height="400px",
                                        )
                                    ],
                                    width=6,
                                ),
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Trait Performance",
                                            chart_id="overview-ruler-trait-performance-chart",
                                            height="400px",
                                        )
                                    ],
                                    width=6,
                                ),
                            ],
                            className="mb-4 mt-3",
                        ),
                        # Ruler matchups and combinations
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Archetype Matchup Matrix",
                                            chart_id="overview-ruler-matchup-matrix-chart",
                                            height="550px",
                                        )
                                    ],
                                    width=8,
                                ),
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Popular Combinations",
                                            chart_id="overview-ruler-combinations-chart",
                                            height="550px",
                                        )
                                    ],
                                    width=4,
                                ),
                            ],
                            className="mb-4",
                        ),
                    ],
                ),
                # Tab 4: Economy
                dbc.Tab(
                    label="Economy",
                    tab_id="economy-tab",
                    children=[
                        # Economic progression - Science and Orders
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Average Science Per Turn",
                                            chart_id="overview-science-progression",
                                            height="400px",
                                        )
                                    ],
                                    width=6,
                                ),
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Average Orders Per Turn",
                                            chart_id="overview-orders-progression",
                                            height="400px",
                                        )
                                    ],
                                    width=6,
                                ),
                            ],
                            className="mb-4 mt-3",
                        ),
                        # Military and Legitimacy progression
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Average Military Score Per Turn",
                                            chart_id="overview-military-progression",
                                            height="400px",
                                        )
                                    ],
                                    width=6,
                                ),
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Average Legitimacy Per Turn",
                                            chart_id="overview-legitimacy-progression",
                                            height="400px",
                                        )
                                    ],
                                    width=6,
                                ),
                            ],
                            className="mb-4",
                        ),
                        # Law Progression Analysis - 2 charts side by side
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Law Timing Distribution",
                                            chart_id="overview-law-distribution",
                                            height="450px",
                                        )
                                    ],
                                    width=6,
                                ),
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Law Progression Efficiency",
                                            chart_id="overview-law-efficiency",
                                            height="450px",
                                        )
                                    ],
                                    width=6,
                                ),
                            ],
                            className="mb-4",
                        ),
                        # Production Strategies (full width for readability)
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Production Strategies",
                                            chart_id="overview-production-strategies",
                                            height="1600px",  # Tall enough for all players
                                        )
                                    ],
                                    width=12,
                                ),
                            ],
                            className="mb-4",
                        ),
                    ],
                ),
                # Tab 5: Cities
                dbc.Tab(
                    label="Cities",
                    tab_id="cities-tab",
                    children=[
                        # Expansion Timeline - full width
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="City Expansion Timeline",
                                            chart_id="overview-expansion-timeline",
                                            height="500px",
                                        )
                                    ],
                                    width=12,
                                ),
                            ],
                            className="mb-4 mt-3",
                        ),
                    ],
                ),
            ],
            id="overview-tabs",
            active_tab="summary-tab",
        ),
    ]
)


@callback(
    Output("overview-round-filter-dropdown", "options"),
    Input("overview-bracket-filter-dropdown", "value"),
)
def update_round_options(bracket: str) -> List[dict]:
    """Update round dropdown options based on selected bracket.

    Args:
        bracket: Selected bracket ('all', 'Winners', 'Losers', 'Unknown')

    Returns:
        List of options for round dropdown
    """
    from tournament_visualizer.components.layouts import format_round_display

    try:
        queries = get_queries()
        available_rounds = queries.get_available_rounds()

        if available_rounds.empty:
            return []

        # Filter rounds based on bracket selection
        if bracket == "Winners":
            filtered = available_rounds[available_rounds["tournament_round"] > 0]
        elif bracket == "Losers":
            filtered = available_rounds[available_rounds["tournament_round"] < 0]
        elif bracket == "Unknown":
            filtered = available_rounds[available_rounds["tournament_round"].isna()]
        else:  # 'all'
            filtered = available_rounds

        # Create options
        options = [
            {
                "label": f"{format_round_display(row['tournament_round'])} ({int(row['match_count'])} matches)",
                "value": int(row["tournament_round"])
                if pd.notna(row["tournament_round"])
                else None,
            }
            for _, row in filtered.iterrows()
        ]

        return options

    except Exception as e:
        logger.error(f"Error updating round options: {e}")
        return []


@callback(
    Output("overview-map-size-dropdown", "options"),
    Input("refresh-interval", "n_intervals"),
)
def update_map_size_options(n_intervals: int) -> List[dict]:
    """Update map size dropdown options.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        List of options for map size dropdown
    """
    try:
        queries = get_queries()
        sizes = queries.get_available_map_sizes()
        return [{"label": size, "value": size} for size in sizes]
    except Exception as e:
        logger.error(f"Error updating map size options: {e}")
        return []


@callback(
    Output("overview-map-class-dropdown", "options"),
    Input("refresh-interval", "n_intervals"),
)
def update_map_class_options(n_intervals: int) -> List[dict]:
    """Update map class dropdown options.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        List of options for map class dropdown
    """
    try:
        queries = get_queries()
        classes = queries.get_available_map_classes()
        return [{"label": cls, "value": cls} for cls in classes]
    except Exception as e:
        logger.error(f"Error updating map class options: {e}")
        return []


@callback(
    Output("overview-map-aspect-dropdown", "options"),
    Input("refresh-interval", "n_intervals"),
)
def update_map_aspect_options(n_intervals: int) -> List[dict]:
    """Update map aspect dropdown options.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        List of options for map aspect dropdown
    """
    try:
        queries = get_queries()
        aspects = queries.get_available_map_aspects()
        return [{"label": aspect, "value": aspect} for aspect in aspects]
    except Exception as e:
        logger.error(f"Error updating map aspect options: {e}")
        return []


@callback(
    Output("overview-nations-dropdown", "options"),
    Input("refresh-interval", "n_intervals"),
)
def update_nations_options(n_intervals: int) -> List[dict]:
    """Update nations dropdown options.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        List of options for nations dropdown
    """
    try:
        queries = get_queries()
        nations = queries.get_available_nations()
        return [{"label": nation, "value": nation} for nation in nations]
    except Exception as e:
        logger.error(f"Error updating nations options: {e}")
        return []


@callback(
    Output("overview-players-dropdown", "options"),
    Input("refresh-interval", "n_intervals"),
)
def update_players_options(n_intervals: int) -> List[dict]:
    """Update players dropdown options.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        List of options for players dropdown
    """
    try:
        queries = get_queries()
        players = queries.get_available_players()
        return [{"label": player, "value": player} for player in players]
    except Exception as e:
        logger.error(f"Error updating players options: {e}")
        return []


@callback(
    Output("overview-round-stats-content", "children"),
    Input("refresh-interval", "n_intervals"),
)
def update_round_statistics(n_intervals: int) -> List[Any]:
    """Display tournament round distribution statistics.

    Returns:
        List of HTML components showing round stats
    """
    from tournament_visualizer.components.layouts import format_round_display

    try:
        queries = get_queries()
        rounds_df = queries.get_available_rounds()

        if rounds_df.empty:
            return [html.P("No round data available", className="text-muted")]

        # Calculate totals
        total_matches = int(rounds_df["match_count"].sum())
        winners_df = rounds_df[rounds_df["bracket"] == "Winners"]
        losers_df = rounds_df[rounds_df["bracket"] == "Losers"]
        unknown_df = rounds_df[rounds_df["bracket"] == "Unknown"]

        winners_matches = int(winners_df["match_count"].sum()) if not winners_df.empty else 0
        losers_matches = int(losers_df["match_count"].sum()) if not losers_df.empty else 0
        unknown_matches = int(unknown_df["match_count"].sum()) if not unknown_df.empty else 0

        # Create summary
        stats = [
            html.P(
                [html.Strong("Total Matches: "), f"{total_matches}"], className="mb-2"
            ),
            html.P(
                [
                    html.Strong("Winners Bracket: "),
                    html.Span(f"{winners_matches}", className="text-success"),
                ],
                className="mb-2",
            ),
            html.P(
                [
                    html.Strong("Losers Bracket: "),
                    html.Span(f"{losers_matches}", className="text-warning"),
                ],
                className="mb-2",
            ),
        ]

        if unknown_matches > 0:
            stats.append(
                html.P(
                    [
                        html.Strong("Unknown: "),
                        html.Span(f"{unknown_matches}", className="text-muted"),
                    ],
                    className="mb-2",
                )
            )

        # Add horizontal rule
        stats.append(html.Hr())

        # Add breakdown by round
        stats.append(
            html.P(html.Strong("Breakdown by Round:"), className="mb-2")
        )

        for _, row in rounds_df.iterrows():
            round_display = format_round_display(row["tournament_round"])
            match_count = int(row["match_count"])
            stats.append(
                html.P(
                    [
                        f"{round_display}: ",
                        html.Span(
                            f"{match_count} matches", className="text-muted"
                        ),
                    ],
                    className="mb-1 ms-3",
                )
            )

        return stats

    except Exception as e:
        logger.error(f"Error loading round statistics: {e}")
        return [html.P(f"Error: {str(e)}", className="text-danger")]


@callback(
    Output("overview-metrics", "children"), Input("refresh-interval", "n_intervals")
)
def update_overview_metrics(n_intervals: int) -> html.Div:
    """Update the overview metrics cards.

    Args:
        n_intervals: Number of interval triggers

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
    Input("overview-bracket-filter-dropdown", "value"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-min-turns-input", "value"),
    Input("overview-max-turns-input", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_nation_win_chart(
    bracket: str,
    round_num: Optional[int],
    min_turns: Optional[int],
    max_turns: Optional[int],
    map_size: Optional[str],
    map_class: Optional[str],
    map_aspect: Optional[str],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    n_intervals: int,
):
    """Update the nation win percentage chart with filters.

    Args:
        bracket: Selected bracket filter
        round_num: Selected round number
        min_turns: Minimum number of turns
        max_turns: Maximum number of turns
        map_size: Map size filter
        map_class: Map class filter
        map_aspect: Map aspect ratio filter
        nations: List of selected nations
        players: List of selected players
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure for nation win percentage
    """
    try:
        queries = get_queries()
        bracket_param = None if bracket == "all" else bracket

        df = queries.get_nation_win_stats(
            tournament_round=round_num,
            bracket=bracket_param,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
        )

        if df.empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_nation_win_percentage_chart(df)

    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading nation data: {str(e)}")


@callback(
    Output("overview-nation-loss-chart", "figure"),
    Input("overview-bracket-filter-dropdown", "value"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-min-turns-input", "value"),
    Input("overview-max-turns-input", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_nation_loss_chart(
    bracket: str,
    round_num: Optional[int],
    min_turns: Optional[int],
    max_turns: Optional[int],
    map_size: Optional[str],
    map_class: Optional[str],
    map_aspect: Optional[str],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    n_intervals: int,
):
    """Update the nation loss percentage chart with filters.

    Args:
        bracket: Selected bracket filter
        round_num: Selected round number
        min_turns: Minimum number of turns
        max_turns: Maximum number of turns
        map_size: Map size filter
        map_class: Map class filter
        map_aspect: Map aspect ratio filter
        nations: List of selected nations
        players: List of selected players
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure for nation loss percentage
    """
    try:
        queries = get_queries()
        bracket_param = None if bracket == "all" else bracket

        df = queries.get_nation_loss_stats(
            tournament_round=round_num,
            bracket=bracket_param,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
        )

        if df.empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_nation_loss_percentage_chart(df)

    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading nation data: {str(e)}")


@callback(
    Output("overview-nation-popularity-chart", "figure"),
    Input("overview-bracket-filter-dropdown", "value"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-min-turns-input", "value"),
    Input("overview-max-turns-input", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_nation_popularity_chart(
    bracket: str,
    round_num: Optional[int],
    min_turns: Optional[int],
    max_turns: Optional[int],
    map_size: Optional[str],
    map_class: Optional[str],
    map_aspect: Optional[str],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    n_intervals: int,
):
    """Update the nation popularity chart with filters.

    Args:
        bracket: Selected bracket filter
        round_num: Selected round number
        min_turns: Minimum number of turns
        max_turns: Maximum number of turns
        map_size: Map size filter
        map_class: Map class filter
        map_aspect: Map aspect ratio filter
        nations: List of selected nations
        players: List of selected players
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure for nation popularity
    """
    try:
        queries = get_queries()
        bracket_param = None if bracket == "all" else bracket

        df = queries.get_nation_popularity(
            tournament_round=round_num,
            bracket=bracket_param,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
        )

        if df.empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_nation_popularity_chart(df)

    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading nation data: {str(e)}")


@callback(
    Output("overview-units-chart", "figure"), Input("refresh-interval", "n_intervals")
)
def update_units_chart(n_intervals: int):
    """Update the unit popularity sunburst chart.

    Args:
        n_intervals: Number of interval triggers

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
    Output("overview-map-chart", "figure"), Input("refresh-interval", "n_intervals")
)
def update_map_chart(n_intervals: int):
    """Update the map breakdown sunburst chart.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure for map breakdown
    """
    try:
        queries = get_queries()
        df = queries.get_map_breakdown()

        if df.empty:
            return create_empty_chart_placeholder("No map data available")

        return create_map_breakdown_actual_sunburst_chart(df)

    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading map data: {str(e)}")


@callback(
    Output("overview-matches-table", "data"),
    Input("overview-bracket-filter-dropdown", "value"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-min-turns-input", "value"),
    Input("overview-max-turns-input", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_matches_table(
    bracket: str,
    round_num: Optional[int],
    min_turns: Optional[int],
    max_turns: Optional[int],
    map_size: Optional[str],
    map_class: Optional[str],
    map_aspect: Optional[str],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    n_intervals: int,
) -> List[Dict[str, Any]]:
    """Update the matches table based on filters.

    Args:
        bracket: Selected bracket filter
        round_num: Selected round number
        min_turns: Minimum number of turns
        max_turns: Maximum number of turns
        map_size: Map size filter
        map_class: Map class filter
        map_aspect: Map aspect ratio filter
        nations: List of selected nations
        players: List of selected players
        n_intervals: Number of interval triggers

    Returns:
        List of dictionaries for table data
    """
    from tournament_visualizer.components.layouts import format_round_display

    try:
        queries = get_queries()

        # Build bracket parameter for query
        bracket_param = None if bracket == "all" else bracket

        # Get filtered matches
        df = queries.get_matches_by_round(
            tournament_round=round_num,
            bracket=bracket_param,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
        )

        if df.empty:
            return []

        # Format data for table
        table_data = []
        for _, row in df.iterrows():
            match_id = row.get("match_id")
            game_name = row.get("game_name", "Unknown")

            table_data.append(
                {
                    "match_link": f"[{game_name}](/matches?match_id={match_id})",
                    "save_date": (
                        row.get("save_date", "").strftime("%Y-%m-%d")
                        if pd.notna(row.get("save_date"))
                        else ""
                    ),
                    "round_display": format_round_display(
                        row.get("tournament_round")
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
    Output("overview-alerts", "children"), Input("refresh-interval", "n_intervals")
)
def check_data_status(n_intervals: int) -> html.Div:
    """Check data status and show alerts if needed.

    Args:
        n_intervals: Number of interval triggers

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


@callback(
    Output("overview-law-distribution", "figure"),
    Input("overview-bracket-filter-dropdown", "value"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-min-turns-input", "value"),
    Input("overview-max-turns-input", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_law_distribution(
    bracket: str,
    round_num: Optional[int],
    min_turns: Optional[int],
    max_turns: Optional[int],
    map_size: Optional[str],
    map_class: Optional[str],
    map_aspect: Optional[str],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    n_intervals: int,
):
    """Update law milestone distribution chart with filters.

    Args:
        bracket: Selected bracket filter
        round_num: Selected round number
        min_turns: Minimum number of turns
        max_turns: Maximum number of turns
        map_size: Map size filter
        map_class: Map class filter
        map_aspect: Map aspect ratio filter
        nations: List of selected nations
        players: List of selected players
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with box plot distribution
    """
    try:
        queries = get_queries()
        bracket_param = None if bracket == "all" else bracket

        # Get ALL matches data with filters
        df = queries.get_law_progression_by_match(
            match_id=None,
            tournament_round=round_num,
            bracket=bracket_param,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
        )

        if df.empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_law_milestone_distribution_chart(df)

    except Exception as e:
        logger.error(f"Error loading law distribution: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-law-efficiency", "figure"),
    Input("overview-bracket-filter-dropdown", "value"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-min-turns-input", "value"),
    Input("overview-max-turns-input", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_law_efficiency(
    bracket: str,
    round_num: Optional[int],
    min_turns: Optional[int],
    max_turns: Optional[int],
    map_size: Optional[str],
    map_class: Optional[str],
    map_aspect: Optional[str],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    n_intervals: int,
):
    """Update law efficiency scatter plot with filters.

    Args:
        bracket: Selected bracket filter
        round_num: Selected round number
        min_turns: Minimum number of turns
        max_turns: Maximum number of turns
        map_size: Map size filter
        map_class: Map class filter
        map_aspect: Map aspect ratio filter
        nations: List of selected nations
        players: List of selected players
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with scatter plot
    """
    try:
        queries = get_queries()
        bracket_param = None if bracket == "all" else bracket

        df = queries.get_law_progression_by_match(
            match_id=None,
            tournament_round=round_num,
            bracket=bracket_param,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
        )

        if df.empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_law_efficiency_scatter(df)

    except Exception as e:
        logger.error(f"Error loading law efficiency: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-event-timeline", "figure"),
    Input("refresh-interval", "n_intervals"),
)
def update_event_timeline(n_intervals: int):
    """Update aggregated event category timeline chart.

    Shows typical event patterns across ALL matches.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with stacked area chart
    """
    try:
        queries = get_queries()
        df = queries.get_aggregated_event_timeline(max_turn=150)

        if df.empty:
            return create_empty_chart_placeholder("No event timeline data available")

        return create_aggregated_event_category_timeline_chart(df)

    except Exception as e:
        logger.error(f"Error loading event timeline: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-ruler-archetype-chart", "figure"),
    Input("overview-bracket-filter-dropdown", "value"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-min-turns-input", "value"),
    Input("overview-max-turns-input", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_ruler_archetype_chart(
    bracket: str,
    round_num: Optional[int],
    min_turns: Optional[int],
    max_turns: Optional[int],
    map_size: Optional[str],
    map_class: Optional[str],
    map_aspect: Optional[str],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    n_intervals: int,
):
    """Update ruler archetype win rates chart with filters.

    Args:
        bracket: Selected bracket filter
        round_num: Selected round number
        min_turns: Minimum number of turns
        max_turns: Maximum number of turns
        map_size: Map size filter
        map_class: Map class filter
        map_aspect: Map aspect ratio filter
        nations: List of selected nations
        players: List of selected players
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with dual-axis chart
    """
    try:
        queries = get_queries()
        bracket_param = None if bracket == "all" else bracket

        df = queries.get_ruler_archetype_win_rates(
            tournament_round=round_num,
            bracket=bracket_param,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
        )

        if df.empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_ruler_archetype_win_rates_chart(df)

    except Exception as e:
        logger.error(f"Error loading ruler archetype data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-ruler-trait-performance-chart", "figure"),
    Input("overview-bracket-filter-dropdown", "value"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-min-turns-input", "value"),
    Input("overview-max-turns-input", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_ruler_trait_performance_chart(
    bracket: str,
    round_num: Optional[int],
    min_turns: Optional[int],
    max_turns: Optional[int],
    map_size: Optional[str],
    map_class: Optional[str],
    map_aspect: Optional[str],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    n_intervals: int,
):
    """Update ruler trait performance chart with filters.

    Args:
        bracket: Selected bracket filter
        round_num: Selected round number
        min_turns: Minimum number of turns
        max_turns: Maximum number of turns
        map_size: Map size filter
        map_class: Map class filter
        map_aspect: Map aspect ratio filter
        nations: List of selected nations
        players: List of selected players
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with dual-axis chart
    """
    try:
        queries = get_queries()
        bracket_param = None if bracket == "all" else bracket

        df = queries.get_ruler_trait_win_rates(
            min_games=1,
            tournament_round=round_num,
            bracket=bracket_param,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
        )

        if df.empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_ruler_trait_performance_chart(df)

    except Exception as e:
        logger.error(f"Error loading ruler trait data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-ruler-matchup-matrix-chart", "figure"),
    Input("overview-bracket-filter-dropdown", "value"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-min-turns-input", "value"),
    Input("overview-max-turns-input", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_ruler_matchup_matrix_chart(
    bracket: str,
    round_num: Optional[int],
    min_turns: Optional[int],
    max_turns: Optional[int],
    map_size: Optional[str],
    map_class: Optional[str],
    map_aspect: Optional[str],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    n_intervals: int,
):
    """Update ruler archetype matchup matrix chart with filters.

    Args:
        bracket: Selected bracket filter
        round_num: Selected round number
        min_turns: Minimum number of turns
        max_turns: Maximum number of turns
        map_size: Map size filter
        map_class: Map class filter
        map_aspect: Map aspect ratio filter
        nations: List of selected nations
        players: List of selected players
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with heatmap
    """
    try:
        queries = get_queries()
        bracket_param = None if bracket == "all" else bracket

        df = queries.get_ruler_archetype_matchups(
            tournament_round=round_num,
            bracket=bracket_param,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
        )

        if df.empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_ruler_archetype_matchup_matrix(df)

    except Exception as e:
        logger.error(f"Error loading ruler matchup data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-ruler-combinations-chart", "figure"),
    Input("overview-bracket-filter-dropdown", "value"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-min-turns-input", "value"),
    Input("overview-max-turns-input", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_ruler_combinations_chart(
    bracket: str,
    round_num: Optional[int],
    min_turns: Optional[int],
    max_turns: Optional[int],
    map_size: Optional[str],
    map_class: Optional[str],
    map_aspect: Optional[str],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    n_intervals: int,
):
    """Update ruler archetype + trait combinations chart with filters.

    Args:
        bracket: Selected bracket filter
        round_num: Selected round number
        min_turns: Minimum number of turns
        max_turns: Maximum number of turns
        map_size: Map size filter
        map_class: Map class filter
        map_aspect: Map aspect ratio filter
        nations: List of selected nations
        players: List of selected players
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with horizontal bar chart
    """
    try:
        queries = get_queries()
        bracket_param = None if bracket == "all" else bracket

        df = queries.get_ruler_archetype_trait_combinations(
            limit=10,
            tournament_round=round_num,
            bracket=bracket_param,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
        )

        if df.empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_ruler_archetype_trait_combinations_chart(df)

    except Exception as e:
        logger.error(f"Error loading ruler combinations data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-counter-pick-heatmap", "figure"),
    Input("overview-bracket-filter-dropdown", "value"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-min-turns-input", "value"),
    Input("overview-max-turns-input", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_counter_pick_heatmap(
    bracket: str,
    round_num: Optional[int],
    min_turns: Optional[int],
    max_turns: Optional[int],
    map_size: Optional[str],
    map_class: Optional[str],
    map_aspect: Optional[str],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    n_intervals: int,
):
    """Update nation counter-pick effectiveness heatmap with filters.

    Args:
        bracket: Selected bracket filter
        round_num: Selected round number
        min_turns: Minimum number of turns
        max_turns: Maximum number of turns
        map_size: Map size filter
        map_class: Map class filter
        map_aspect: Map aspect ratio filter
        nations: List of selected nations
        players: List of selected players
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with heatmap
    """
    try:
        queries = get_queries()
        bracket_param = None if bracket == "all" else bracket

        df = queries.get_nation_counter_pick_matrix(
            min_games=1,
            tournament_round=round_num,
            bracket=bracket_param,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
        )

        if df.empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_nation_counter_pick_heatmap(df)

    except Exception as e:
        logger.error(f"Error loading counter-pick data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-pick-order-win-rate", "figure"),
    Input("overview-bracket-filter-dropdown", "value"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-min-turns-input", "value"),
    Input("overview-max-turns-input", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_pick_order_win_rate(
    bracket: str,
    round_num: Optional[int],
    min_turns: Optional[int],
    max_turns: Optional[int],
    map_size: Optional[str],
    map_class: Optional[str],
    map_aspect: Optional[str],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    n_intervals: int,
):
    """Update pick order win rate bar chart with filters.

    Args:
        bracket: Selected bracket filter
        round_num: Selected round number
        min_turns: Minimum number of turns
        max_turns: Maximum number of turns
        map_size: Map size filter
        map_class: Map class filter
        map_aspect: Map aspect ratio filter
        nations: List of selected nations
        players: List of selected players
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with grouped bar chart
    """
    try:
        queries = get_queries()
        bracket_param = None if bracket == "all" else bracket

        df = queries.get_pick_order_win_rates(
            tournament_round=round_num,
            bracket=bracket_param,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
        )

        if df.empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_pick_order_win_rate_chart(df)

    except Exception as e:
        logger.error(f"Error loading pick order win rate data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-science-progression", "figure"),
    Input("overview-bracket-filter-dropdown", "value"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-min-turns-input", "value"),
    Input("overview-max-turns-input", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_science_progression(
    bracket: str,
    round_num: Optional[int],
    min_turns: Optional[int],
    max_turns: Optional[int],
    map_size: Optional[str],
    map_class: Optional[str],
    map_aspect: Optional[str],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    n_intervals: int,
):
    """Update science progression chart with filters.

    Args:
        bracket: Selected bracket filter
        round_num: Selected round number
        min_turns: Minimum number of turns
        max_turns: Maximum number of turns
        map_size: Map size filter
        map_class: Map class filter
        map_aspect: Map aspect ratio filter
        nations: List of selected nations
        players: List of selected players
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with line chart
    """
    try:
        queries = get_queries()
        bracket_param = None if bracket == "all" else bracket

        stats = queries.get_metric_progression_stats(
            tournament_round=round_num,
            bracket=bracket_param,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
        )

        if stats["science"].empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_science_progression_chart(stats["science"])

    except Exception as e:
        logger.error(f"Error loading science progression data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-orders-progression", "figure"),
    Input("overview-bracket-filter-dropdown", "value"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-min-turns-input", "value"),
    Input("overview-max-turns-input", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_orders_progression(
    bracket: str,
    round_num: Optional[int],
    min_turns: Optional[int],
    max_turns: Optional[int],
    map_size: Optional[str],
    map_class: Optional[str],
    map_aspect: Optional[str],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    n_intervals: int,
):
    """Update orders progression chart with filters.

    Args:
        bracket: Selected bracket filter
        round_num: Selected round number
        min_turns: Minimum number of turns
        max_turns: Maximum number of turns
        map_size: Map size filter
        map_class: Map class filter
        map_aspect: Map aspect ratio filter
        nations: List of selected nations
        players: List of selected players
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with line chart
    """
    try:
        queries = get_queries()
        bracket_param = None if bracket == "all" else bracket

        stats = queries.get_metric_progression_stats(
            tournament_round=round_num,
            bracket=bracket_param,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
        )

        if stats["orders"].empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_orders_progression_chart(stats["orders"])

    except Exception as e:
        logger.error(f"Error loading orders progression data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-military-progression", "figure"),
    Input("overview-bracket-filter-dropdown", "value"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-min-turns-input", "value"),
    Input("overview-max-turns-input", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_military_progression(
    bracket: str,
    round_num: Optional[int],
    min_turns: Optional[int],
    max_turns: Optional[int],
    map_size: Optional[str],
    map_class: Optional[str],
    map_aspect: Optional[str],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    n_intervals: int,
):
    """Update military progression chart with filters.

    Args:
        bracket: Selected bracket filter
        round_num: Selected round number
        min_turns: Minimum number of turns
        max_turns: Maximum number of turns
        map_size: Map size filter
        map_class: Map class filter
        map_aspect: Map aspect ratio filter
        nations: List of selected nations
        players: List of selected players
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with line chart
    """
    try:
        queries = get_queries()
        bracket_param = None if bracket == "all" else bracket

        stats = queries.get_metric_progression_stats(
            tournament_round=round_num,
            bracket=bracket_param,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
        )

        if stats["military"].empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_military_progression_chart(stats["military"])

    except Exception as e:
        logger.error(f"Error loading military progression data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-legitimacy-progression", "figure"),
    Input("overview-bracket-filter-dropdown", "value"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-min-turns-input", "value"),
    Input("overview-max-turns-input", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_legitimacy_progression(
    bracket: str,
    round_num: Optional[int],
    min_turns: Optional[int],
    max_turns: Optional[int],
    map_size: Optional[str],
    map_class: Optional[str],
    map_aspect: Optional[str],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    n_intervals: int,
):
    """Update legitimacy progression chart with filters.

    Args:
        bracket: Selected bracket filter
        round_num: Selected round number
        min_turns: Minimum number of turns
        max_turns: Maximum number of turns
        map_size: Map size filter
        map_class: Map class filter
        map_aspect: Map aspect ratio filter
        nations: List of selected nations
        players: List of selected players
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with line chart
    """
    try:
        queries = get_queries()
        bracket_param = None if bracket == "all" else bracket

        stats = queries.get_metric_progression_stats(
            tournament_round=round_num,
            bracket=bracket_param,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
        )

        if stats["legitimacy"].empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_legitimacy_progression_chart(stats["legitimacy"])

    except Exception as e:
        logger.error(f"Error loading legitimacy progression data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


# Cities Tab Callbacks


@callback(
    Output("overview-expansion-timeline", "figure"),
    Input("overview-bracket-filter-dropdown", "value"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-min-turns-input", "value"),
    Input("overview-max-turns-input", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_expansion_timeline_chart(
    bracket: str,
    round_num: Optional[int],
    min_turns: Optional[int],
    max_turns: Optional[int],
    map_size: Optional[str],
    map_class: Optional[str],
    map_aspect: Optional[str],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    n_intervals: int,
):
    """Update the city expansion timeline chart with filters.

    Args:
        bracket: Selected bracket filter
        round_num: Selected round number
        min_turns: Minimum number of turns
        max_turns: Maximum number of turns
        map_size: Map size filter
        map_class: Map class filter
        map_aspect: Map aspect ratio filter
        nations: List of selected nations
        players: List of selected players
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with expansion timeline
    """
    try:
        queries = get_queries()
        bracket_param = None if bracket == "all" else bracket

        df = queries.get_tournament_expansion_timeline(
            tournament_round=round_num,
            bracket=bracket_param,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
        )

        if df.empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_tournament_expansion_timeline_chart(df)

    except Exception as e:
        logger.error(f"Error updating expansion timeline: {e}")
        return create_empty_chart_placeholder("Error loading expansion data")


@callback(
    Output("overview-production-strategies", "figure"),
    Input("overview-bracket-filter-dropdown", "value"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-min-turns-input", "value"),
    Input("overview-max-turns-input", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_production_strategies_chart(
    bracket: str,
    round_num: Optional[int],
    min_turns: Optional[int],
    max_turns: Optional[int],
    map_size: Optional[str],
    map_class: Optional[str],
    map_aspect: Optional[str],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    n_intervals: int,
):
    """Update the production strategies chart with filters.

    Args:
        bracket: Selected bracket filter
        round_num: Selected round number
        min_turns: Minimum number of turns
        max_turns: Maximum number of turns
        map_size: Map size filter
        map_class: Map class filter
        map_aspect: Map aspect ratio filter
        nations: List of selected nations
        players: List of selected players
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with production strategies
    """
    try:
        queries = get_queries()
        bracket_param = None if bracket == "all" else bracket

        df = queries.get_tournament_production_strategies(
            tournament_round=round_num,
            bracket=bracket_param,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
        )

        if df.empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_tournament_production_strategies_chart(df)

    except Exception as e:
        logger.error(f"Error updating production strategies: {e}")
        return create_empty_chart_placeholder("Error loading production data")
