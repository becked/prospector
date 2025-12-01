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
from plotly import graph_objects as go

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
    create_science_per_turn_correlation_chart,
    create_science_progression_chart,
    create_yield_stacked_chart,
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
from tournament_visualizer.config import MODEBAR_CONFIG, PAGE_CONFIG
from tournament_visualizer.data.queries import get_queries

logger = logging.getLogger(__name__)


def parse_turn_length(turn_length: Optional[int]) -> tuple[Optional[int], Optional[int]]:
    """Parse turn length slider value into min and max turns.

    Args:
        turn_length: Maximum turn number cutoff (None means no filter)

    Returns:
        Tuple of (min_turns, max_turns)
    """
    if turn_length is None:
        return (None, None)
    return (None, turn_length)


# Yield chart configuration: (yield_type, display_name, rate_color, cumulative_color)
YIELD_CHARTS = [
    ("YIELD_SCIENCE", "Science", "#1f77b4", "#2ca02c"),
    ("YIELD_ORDERS", "Orders", "#ff7f0e", "#9467bd"),
    ("YIELD_FOOD", "Food", "#8c564b", "#e377c2"),
    ("YIELD_GROWTH", "Growth", "#7f7f7f", "#bcbd22"),
    ("YIELD_CULTURE", "Culture", "#17becf", "#1f77b4"),
    ("YIELD_CIVICS", "Civics", "#d62728", "#ff7f0e"),
    ("YIELD_TRAINING", "Training", "#2ca02c", "#d62728"),
    ("YIELD_MONEY", "Money", "#ffbb00", "#8c564b"),
    ("YIELD_HAPPINESS", "Happiness", "#98df8a", "#aec7e8"),
    ("YIELD_DISCONTENT", "Discontent", "#ff9896", "#c49c94"),
    ("YIELD_IRON", "Iron", "#636363", "#969696"),
    ("YIELD_STONE", "Stone", "#bdbdbd", "#d9d9d9"),
    ("YIELD_WOOD", "Wood", "#8c6d31", "#bd9e39"),
    ("YIELD_MAINTENANCE", "Maintenance", "#843c39", "#ad494a"),
]

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
        # Summary metrics (above filters)
        html.Div(id="overview-metrics", className="mb-4"),
        # Filters (above tabs) - Collapsible
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    dbc.Button(
                                        [
                                            html.I(
                                                id="overview-filter-toggle-icon",
                                                className="bi bi-chevron-right me-2",
                                            ),
                                            "Filters",
                                        ],
                                        id="overview-filter-toggle",
                                        color="link",
                                        className="text-decoration-none text-dark fw-bold w-100 text-start p-0",
                                    ),
                                    className="py-2",
                                ),
                                dbc.Collapse(
                                    dbc.CardBody(
                                        [
                                            # Two column layout
                                            dbc.Row(
                                                [
                                                    # Column 1: Tournament Round + Map Filters
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
                                                                multi=True,
                                                                className="mb-3",
                                                            ),
                                                            html.Label(
                                                                "Map Size",
                                                                className="fw-bold mb-2",
                                                            ),
                                                            dcc.Dropdown(
                                                                id="overview-map-size-dropdown",
                                                                options=[],
                                                                value=None,
                                                                placeholder="All Sizes",
                                                                multi=True,
                                                                className="mb-3",
                                                            ),
                                                            html.Label(
                                                                "Map Class",
                                                                className="fw-bold mb-2",
                                                            ),
                                                            dcc.Dropdown(
                                                                id="overview-map-class-dropdown",
                                                                options=[],
                                                                value=None,
                                                                placeholder="All Classes",
                                                                multi=True,
                                                                className="mb-3",
                                                            ),
                                                            html.Label(
                                                                "Map Aspect",
                                                                className="fw-bold mb-2",
                                                            ),
                                                            dcc.Dropdown(
                                                                id="overview-map-aspect-dropdown",
                                                                options=[],
                                                                value=None,
                                                                placeholder="All Aspects",
                                                                multi=True,
                                                                className="mb-3",
                                                            ),
                                                        ],
                                                        width=6,
                                                    ),
                                                    # Column 2: Game Length + Nations + Players
                                                    dbc.Col(
                                                        [
                                                            html.Label(
                                                                "Game Length (Max Turns)",
                                                                className="fw-bold mb-2",
                                                            ),
                                                            html.Div(
                                                                [
                                                                    dcc.Slider(
                                                                        id="overview-turn-length-slider",
                                                                        min=10,
                                                                        max=200,
                                                                        step=5,
                                                                        value=200,
                                                                        marks={
                                                                            10: "10",
                                                                            50: "50",
                                                                            100: "100",
                                                                            150: "150",
                                                                            200: "200",
                                                                        },
                                                                        tooltip={
                                                                            "placement": "bottom",
                                                                            "always_visible": False,
                                                                        },
                                                                        className="mb-1",
                                                                    ),
                                                                    html.Div(
                                                                        id="overview-turn-length-label",
                                                                        className="text-center text-muted small",
                                                                        children="Max 200 turns",
                                                                    ),
                                                                ],
                                                                className="mb-3",
                                                            ),
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
                                                            html.Label(
                                                                "Result",
                                                                className="fw-bold mb-2",
                                                            ),
                                                            dcc.Dropdown(
                                                                id="overview-result-dropdown",
                                                                options=[
                                                                    {
                                                                        "label": "All Players",
                                                                        "value": "all",
                                                                    },
                                                                    {
                                                                        "label": "Winners Only",
                                                                        "value": "winners",
                                                                    },
                                                                    {
                                                                        "label": "Losers Only",
                                                                        "value": "losers",
                                                                    },
                                                                ],
                                                                value="all",
                                                                clearable=False,
                                                                className="mb-3",
                                                            ),
                                                        ],
                                                        width=6,
                                                    ),
                                                ]
                                            ),
                                            # Clear Filters Button Row
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            dbc.Button(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-arrow-counterclockwise me-2"
                                                                    ),
                                                                    "Clear All Filters",
                                                                ],
                                                                id="overview-clear-filters-btn",
                                                                color="secondary",
                                                                outline=True,
                                                                size="sm",
                                                                className="mt-2",
                                                            ),
                                                        ],
                                                        width=12,
                                                        className="text-end",
                                                    ),
                                                ]
                                            ),
                                        ]
                                    ),
                                    id="overview-filter-collapse",
                                    is_open=False,
                                ),
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
                        # Event Category Timeline
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Event Category Timeline",
                                            chart_id="overview-event-timeline",
                                            height="450px",
                                        )
                                    ],
                                    width=12,
                                ),
                            ],
                            className="mb-4 mt-3",
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
                        # Science correlation chart
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Average Science Per Turn vs Win Rate",
                                            chart_id="overview-science-per-turn-correlation",
                                            height="400px",
                                        )
                                    ],
                                    width=12,
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
                # Tab 4: Yields
                dbc.Tab(
                    label="Yields",
                    tab_id="yields-tab",
                    children=[
                        # First row: Science (with scale toggle) and Orders
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Card(
                                            [
                                                dbc.CardHeader(
                                                    [
                                                        html.Span(
                                                            "Science Production",
                                                            className="fw-bold",
                                                        ),
                                                        html.Span(
                                                            [
                                                                html.Small("Cumulative:", className="text-muted me-3"),
                                                                dbc.RadioItems(
                                                                    id="overview-science-scale-toggle",
                                                                    options=[
                                                                        {"label": "Linear", "value": "linear"},
                                                                        {"label": "Log", "value": "log"},
                                                                    ],
                                                                    value="linear",
                                                                    inline=True,
                                                                    inputClassName="me-1",
                                                                    labelClassName="small",
                                                                    style={"gap": "0.25rem"},
                                                                ),
                                                            ],
                                                            className="d-flex align-items-center",
                                                        ),
                                                    ],
                                                    className="d-flex justify-content-between align-items-center",
                                                ),
                                                dbc.CardBody(
                                                    [
                                                        dcc.Graph(
                                                            id="overview-yield-science",
                                                            config=MODEBAR_CONFIG,
                                                            style={"height": "500px"},
                                                        )
                                                    ],
                                                    style={"height": "520px"},
                                                ),
                                            ]
                                        )
                                    ],
                                    width=6,
                                ),
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Orders Production",
                                            chart_id="overview-yield-orders",
                                            height="520px",
                                        )
                                    ],
                                    width=6,
                                ),
                            ],
                            className="mb-4 mt-3",
                        ),
                        # Remaining yield chart rows (skip Science and Orders, start at index 2)
                        *[
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            create_chart_card(
                                                title=f"{YIELD_CHARTS[i][1]} Production",
                                                chart_id=f"overview-yield-{YIELD_CHARTS[i][0].lower().replace('yield_', '')}",
                                                height="520px",
                                            )
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            create_chart_card(
                                                title=f"{YIELD_CHARTS[i + 1][1]} Production",
                                                chart_id=f"overview-yield-{YIELD_CHARTS[i + 1][0].lower().replace('yield_', '')}",
                                                height="520px",
                                            )
                                        ],
                                        width=6,
                                    ),
                                ],
                                className="mb-4",
                            )
                            for i in range(2, len(YIELD_CHARTS), 2)
                        ],
                        # Military and Legitimacy progression (not yield types)
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
                    ],
                ),
                # Tab 5: Laws
                dbc.Tab(
                    label="Laws",
                    tab_id="laws-tab",
                    children=[
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
                                    width=12,
                                ),
                            ],
                            className="mb-4 mt-3",
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Law Progression Efficiency",
                                            chart_id="overview-law-efficiency",
                                            height="450px",
                                        )
                                    ],
                                    width=12,
                                ),
                            ],
                            className="mb-4",
                        ),
                    ],
                ),
                # Tab 6: Cities
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
                        # Production Strategies (full width for readability)
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Production Strategies",
                                            chart_id="overview-production-strategies",
                                            height="1600px",
                                        )
                                    ],
                                    width=12,
                                ),
                            ],
                            className="mb-4",
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
    Output("overview-filter-collapse", "is_open"),
    Output("overview-filter-toggle-icon", "className"),
    Input("overview-filter-toggle", "n_clicks"),
    prevent_initial_call=True,
)
def toggle_filter_collapse(n_clicks: Optional[int]) -> tuple[bool, str]:
    """Toggle the filter section collapse state.

    Args:
        n_clicks: Number of times the toggle button has been clicked

    Returns:
        Tuple of (is_open, icon_class)
    """
    # Get current state from callback context
    from dash import callback_context

    # Toggle state based on clicks
    is_open = n_clicks % 2 == 1 if n_clicks else False
    icon_class = "bi bi-chevron-down me-2" if is_open else "bi bi-chevron-right me-2"

    return is_open, icon_class


@callback(
    Output("overview-round-filter-dropdown", "options"),
    Input("refresh-interval", "n_intervals"),
)
def update_round_options(n_intervals: int) -> List[dict]:
    """Update round dropdown options.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        List of options for round dropdown
    """
    from tournament_visualizer.components.layouts import format_round_display

    try:
        queries = get_queries()
        available_rounds = queries.get_available_rounds()

        if available_rounds.empty:
            return []

        # Create options for all rounds
        options = [
            {
                "label": f"{format_round_display(row['tournament_round'])} ({int(row['match_count'])} matches)",
                "value": (
                    int(row["tournament_round"])
                    if pd.notna(row["tournament_round"])
                    else None
                ),
            }
            for _, row in available_rounds.iterrows()
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
    Output("overview-turn-length-label", "children"),
    Input("overview-turn-length-slider", "value"),
)
def update_turn_length_label(turn_length: Optional[int]) -> str:
    """Update the label below the slider to show current value.

    Args:
        turn_length: Current slider value

    Returns:
        Label text
    """
    if turn_length is None:
        return "All Lengths"
    return f"Max {turn_length} turns"


@callback(
    Output("overview-round-filter-dropdown", "value"),
    Output("overview-turn-length-slider", "value"),
    Output("overview-map-size-dropdown", "value"),
    Output("overview-map-class-dropdown", "value"),
    Output("overview-map-aspect-dropdown", "value"),
    Output("overview-nations-dropdown", "value"),
    Output("overview-players-dropdown", "value"),
    Output("overview-result-dropdown", "value"),
    Input("overview-clear-filters-btn", "n_clicks"),
    prevent_initial_call=True,
)
def clear_all_filters(n_clicks: Optional[int]) -> tuple:
    """Clear all filter selections and reset to defaults.

    Args:
        n_clicks: Number of times the button has been clicked

    Returns:
        Tuple of default values for all filter dropdowns
    """
    return (
        None,  # round
        200,  # turn_length (slider) - reset to max
        None,  # map_size
        None,  # map_class
        None,  # map_aspect
        None,  # nations
        None,  # players
        "all",  # result
    )


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
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-turn-length-slider", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("overview-result-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_nation_win_chart(
    round_num: Optional[list[int]],
    turn_length: Optional[int],
    map_size: Optional[list[str]],
    map_class: Optional[list[str]],
    map_aspect: Optional[list[str]],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    result_filter: Optional[str],
    n_intervals: int,
):
    """Update the nation win percentage chart with filters.

    Args:
        round_num: Selected round number
        turn_length: Maximum turn number cutoff (None means no filter)
        map_size: Map size filter
        map_class: Map class filter
        map_aspect: Map aspect ratio filter
        nations: List of selected nations
        players: List of selected players
        result_filter: Filter by match result (winners/losers/all)
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure for nation win percentage
    """
    try:
        queries = get_queries()
        min_turns, max_turns = parse_turn_length(turn_length)

        df = queries.get_nation_win_stats(
            tournament_round=round_num,
            bracket=None,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
            result_filter=result_filter if result_filter != "all" else None,
        )

        if df.empty:
            return create_empty_chart_placeholder("No data for selected filters")

        fig = create_nation_win_percentage_chart(df)
        return fig

    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading nation data: {str(e)}")


@callback(
    Output("overview-nation-loss-chart", "figure"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-turn-length-slider", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("overview-result-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_nation_loss_chart(
    round_num: Optional[list[int]],
    turn_length: Optional[int],
    map_size: Optional[list[str]],
    map_class: Optional[list[str]],
    map_aspect: Optional[list[str]],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    result_filter: Optional[str],
    n_intervals: int,
):
    """Update the nation loss percentage chart with filters.

    Args:
        round_num: Selected round number
        turn_length: Maximum turn number cutoff (None means no filter)
        map_size: Map size filter
        map_class: Map class filter
        map_aspect: Map aspect ratio filter
        nations: List of selected nations
        players: List of selected players
        result_filter: Filter by match result (winners/losers/all)
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure for nation loss percentage
    """
    try:
        queries = get_queries()
        min_turns, max_turns = parse_turn_length(turn_length)

        df = queries.get_nation_loss_stats(
            tournament_round=round_num,
            bracket=None,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
            result_filter=result_filter if result_filter != "all" else None,
        )

        if df.empty:
            return create_empty_chart_placeholder("No data for selected filters")

        fig = create_nation_loss_percentage_chart(df)
        return fig

    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading nation data: {str(e)}")


@callback(
    Output("overview-nation-popularity-chart", "figure"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-turn-length-slider", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("overview-result-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_nation_popularity_chart(
    round_num: Optional[list[int]],
    turn_length: Optional[int],
    map_size: Optional[list[str]],
    map_class: Optional[list[str]],
    map_aspect: Optional[list[str]],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    result_filter: Optional[str],
    n_intervals: int,
):
    """Update the nation popularity chart with filters.

    Args:
        round_num: Selected round number
        turn_length: Maximum turn number cutoff (None means no filter)
        map_size: Map size filter
        map_class: Map class filter
        map_aspect: Map aspect ratio filter
        nations: List of selected nations
        players: List of selected players
        result_filter: Filter by match result (winners/losers/all)
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure for nation popularity
    """
    try:
        queries = get_queries()
        min_turns, max_turns = parse_turn_length(turn_length)

        df = queries.get_nation_popularity(
            tournament_round=round_num,
            bracket=None,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
            result_filter=result_filter if result_filter != "all" else None,
        )

        if df.empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_nation_popularity_chart(df)

    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading nation data: {str(e)}")


@callback(
    Output("overview-units-chart", "figure"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-turn-length-slider", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("overview-result-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_units_chart(
    round_num: Optional[list[int]],
    turn_length: Optional[int],
    map_size: Optional[list[str]],
    map_class: Optional[list[str]],
    map_aspect: Optional[list[str]],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    result_filter: Optional[str],
    n_intervals: int,
):
    """Update the unit popularity sunburst chart with filters.

    Args:
        round_num: Selected round number
        turn_length: Maximum turn number cutoff (None means no filter)
        map_size: Map size filter
        map_class: Map class filter
        map_aspect: Map aspect ratio filter
        nations: List of selected nations
        players: List of selected players
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure for unit popularity
    """
    try:
        queries = get_queries()
        min_turns, max_turns = parse_turn_length(turn_length)

        df = queries.get_unit_popularity(
            tournament_round=round_num,
            bracket=None,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
            result_filter=result_filter if result_filter != "all" else None,
        )

        if df.empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_unit_popularity_sunburst_chart(df)

    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading unit data: {str(e)}")


@callback(
    Output("overview-map-chart", "figure"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-turn-length-slider", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("overview-result-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_map_chart(
    round_num: Optional[list[int]],
    turn_length: Optional[int],
    map_size: Optional[list[str]],
    map_class: Optional[list[str]],
    map_aspect: Optional[list[str]],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    result_filter: Optional[str],
    n_intervals: int,
):
    """Update the map breakdown sunburst chart with filters.

    Args:
        round_num: Selected round number
        turn_length: Maximum turn number cutoff (None means no filter)
        map_size: Map size filter
        map_class: Map class filter
        map_aspect: Map aspect ratio filter
        nations: List of selected nations
        players: List of selected players
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure for map breakdown
    """
    try:
        queries = get_queries()
        min_turns, max_turns = parse_turn_length(turn_length)

        df = queries.get_map_breakdown(
            tournament_round=round_num,
            bracket=None,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
            result_filter=result_filter if result_filter != "all" else None,
        )

        if df.empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_map_breakdown_actual_sunburst_chart(df)

    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading map data: {str(e)}")


@callback(
    Output("overview-matches-table", "data"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-turn-length-slider", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("overview-result-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_matches_table(
    round_num: Optional[list[int]],
    turn_length: Optional[int],
    map_size: Optional[list[str]],
    map_class: Optional[list[str]],
    map_aspect: Optional[list[str]],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    result_filter: Optional[str],
    n_intervals: int,
) -> List[Dict[str, Any]]:
    """Update the matches table based on filters.

    Args:
        round_num: Selected round number
        turn_length: Maximum turn number cutoff (None means no filter)
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

        # Parse turn length filter
        min_turns, max_turns = parse_turn_length(turn_length)

        # Get filtered matches
        df = queries.get_matches_by_round(
            tournament_round=round_num,
            bracket=None,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
            result_filter=result_filter if result_filter != "all" else None,
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
                    "round_display": format_round_display(row.get("tournament_round")),
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
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-turn-length-slider", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("overview-result-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_law_distribution(
    round_num: Optional[list[int]],
    turn_length: Optional[int],
    map_size: Optional[list[str]],
    map_class: Optional[list[str]],
    map_aspect: Optional[list[str]],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    result_filter: Optional[str],
    n_intervals: int,
):
    """Update law milestone distribution chart with filters.

    Args:
        round_num: Selected round number
        turn_length: Maximum turn number cutoff (None means no filter)
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
        min_turns, max_turns = parse_turn_length(turn_length)

        # Get ALL matches data with filters
        df = queries.get_law_progression_by_match(
            match_id=None,
            tournament_round=round_num,
            bracket=None,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
            result_filter=result_filter if result_filter != "all" else None,
        )

        if df.empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_law_milestone_distribution_chart(df)

    except Exception as e:
        logger.error(f"Error loading law distribution: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-law-efficiency", "figure"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-turn-length-slider", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("overview-result-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_law_efficiency(
    round_num: Optional[list[int]],
    turn_length: Optional[int],
    map_size: Optional[list[str]],
    map_class: Optional[list[str]],
    map_aspect: Optional[list[str]],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    result_filter: Optional[str],
    n_intervals: int,
):
    """Update law efficiency scatter plot with filters.

    Args:
        round_num: Selected round number
        turn_length: Maximum turn number cutoff (None means no filter)
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
        min_turns, max_turns = parse_turn_length(turn_length)

        df = queries.get_law_progression_by_match(
            match_id=None,
            tournament_round=round_num,
            bracket=None,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
            result_filter=result_filter if result_filter != "all" else None,
        )

        if df.empty:
            return create_empty_chart_placeholder("No data for selected filters")

        fig = create_law_efficiency_scatter(df)
        return fig

    except Exception as e:
        logger.error(f"Error loading law efficiency: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-event-timeline", "figure"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-turn-length-slider", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("overview-result-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_event_timeline(
    round_num: Optional[list[int]],
    turn_length: Optional[int],
    map_size: Optional[list[str]],
    map_class: Optional[list[str]],
    map_aspect: Optional[list[str]],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    result_filter: Optional[str],
    n_intervals: int,
):
    """Update aggregated event category timeline chart with filters.

    Shows typical event patterns across filtered matches.

    Args:
        round_num: Selected round number
        turn_length: Maximum turn number cutoff (None means no filter)
        map_size: Map size filter
        map_class: Map class filter
        map_aspect: Map aspect ratio filter
        nations: List of selected nations
        players: List of selected players
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with stacked area chart
    """
    try:
        queries = get_queries()
        min_turns, max_turns = parse_turn_length(turn_length)

        df = queries.get_aggregated_event_timeline(
            max_turn=150,
            tournament_round=round_num,
            bracket=None,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
            result_filter=result_filter if result_filter != "all" else None,
        )

        if df.empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_aggregated_event_category_timeline_chart(df)

    except Exception as e:
        logger.error(f"Error loading event timeline: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-ruler-archetype-chart", "figure"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-turn-length-slider", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("overview-result-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_ruler_archetype_chart(
    round_num: Optional[list[int]],
    turn_length: Optional[int],
    map_size: Optional[list[str]],
    map_class: Optional[list[str]],
    map_aspect: Optional[list[str]],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    result_filter: Optional[str],
    n_intervals: int,
):
    """Update ruler archetype win rates chart with filters.

    Args:
        round_num: Selected round number
        turn_length: Maximum turn number cutoff (None means no filter)
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
        min_turns, max_turns = parse_turn_length(turn_length)

        df = queries.get_ruler_archetype_win_rates(
            tournament_round=round_num,
            bracket=None,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
            result_filter=result_filter if result_filter != "all" else None,
        )

        if df.empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_ruler_archetype_win_rates_chart(df)

    except Exception as e:
        logger.error(f"Error loading ruler archetype data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-ruler-trait-performance-chart", "figure"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-turn-length-slider", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("overview-result-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_ruler_trait_performance_chart(
    round_num: Optional[list[int]],
    turn_length: Optional[int],
    map_size: Optional[list[str]],
    map_class: Optional[list[str]],
    map_aspect: Optional[list[str]],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    result_filter: Optional[str],
    n_intervals: int,
):
    """Update ruler trait performance chart with filters.

    Args:
        round_num: Selected round number
        turn_length: Maximum turn number cutoff (None means no filter)
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
        min_turns, max_turns = parse_turn_length(turn_length)

        df = queries.get_ruler_trait_win_rates(
            min_games=1,
            tournament_round=round_num,
            bracket=None,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
            result_filter=result_filter if result_filter != "all" else None,
        )

        if df.empty:
            return create_empty_chart_placeholder("No data for selected filters")

        fig = create_ruler_trait_performance_chart(df)
        return fig

    except Exception as e:
        logger.error(f"Error loading ruler trait data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-ruler-matchup-matrix-chart", "figure"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-turn-length-slider", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("overview-result-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_ruler_matchup_matrix_chart(
    round_num: Optional[list[int]],
    turn_length: Optional[int],
    map_size: Optional[list[str]],
    map_class: Optional[list[str]],
    map_aspect: Optional[list[str]],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    result_filter: Optional[str],
    n_intervals: int,
):
    """Update ruler archetype matchup matrix chart with filters.

    Args:
        round_num: Selected round number
        turn_length: Maximum turn number cutoff (None means no filter)
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
        min_turns, max_turns = parse_turn_length(turn_length)

        df = queries.get_ruler_archetype_matchups(
            tournament_round=round_num,
            bracket=None,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
            result_filter=result_filter if result_filter != "all" else None,
        )

        if df.empty:
            return create_empty_chart_placeholder("No data for selected filters")

        fig = create_ruler_archetype_matchup_matrix(df)
        return fig

    except Exception as e:
        logger.error(f"Error loading ruler matchup data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-ruler-combinations-chart", "figure"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-turn-length-slider", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("overview-result-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_ruler_combinations_chart(
    round_num: Optional[list[int]],
    turn_length: Optional[int],
    map_size: Optional[list[str]],
    map_class: Optional[list[str]],
    map_aspect: Optional[list[str]],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    result_filter: Optional[str],
    n_intervals: int,
):
    """Update ruler archetype + trait combinations chart with filters.

    Args:
        round_num: Selected round number
        turn_length: Maximum turn number cutoff (None means no filter)
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
        min_turns, max_turns = parse_turn_length(turn_length)

        df = queries.get_ruler_archetype_trait_combinations(
            limit=10,
            tournament_round=round_num,
            bracket=None,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
            result_filter=result_filter if result_filter != "all" else None,
        )

        if df.empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_ruler_archetype_trait_combinations_chart(df)

    except Exception as e:
        logger.error(f"Error loading ruler combinations data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-counter-pick-heatmap", "figure"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-turn-length-slider", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("overview-result-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_counter_pick_heatmap(
    round_num: Optional[list[int]],
    turn_length: Optional[int],
    map_size: Optional[list[str]],
    map_class: Optional[list[str]],
    map_aspect: Optional[list[str]],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    result_filter: Optional[str],
    n_intervals: int,
):
    """Update nation counter-pick effectiveness heatmap with filters.

    Args:
        round_num: Selected round number
        turn_length: Maximum turn number cutoff (None means no filter)
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
        min_turns, max_turns = parse_turn_length(turn_length)

        df = queries.get_nation_counter_pick_matrix(
            min_games=1,
            tournament_round=round_num,
            bracket=None,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
            result_filter=result_filter if result_filter != "all" else None,
        )

        # Let the chart function handle empty data with a proper message
        fig = create_nation_counter_pick_heatmap(df)
        return fig

    except Exception as e:
        logger.error(f"Error loading counter-pick data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-pick-order-win-rate", "figure"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-turn-length-slider", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("overview-result-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_pick_order_win_rate(
    round_num: Optional[list[int]],
    turn_length: Optional[int],
    map_size: Optional[list[str]],
    map_class: Optional[list[str]],
    map_aspect: Optional[list[str]],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    result_filter: Optional[str],
    n_intervals: int,
):
    """Update pick order win rate bar chart with filters.

    Args:
        round_num: Selected round number
        turn_length: Maximum turn number cutoff (None means no filter)
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
        min_turns, max_turns = parse_turn_length(turn_length)

        df = queries.get_pick_order_win_rates(
            tournament_round=round_num,
            bracket=None,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
            result_filter=result_filter if result_filter != "all" else None,
        )

        # Let the chart function handle empty data with a proper message
        fig = create_pick_order_win_rate_chart(df)
        return fig

    except Exception as e:
        logger.error(f"Error loading pick order win rate data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


# Generate callbacks for all yield charts
def _create_yield_callback(
    yield_type: str,
    display_name: str,
    rate_color: str,
    cumulative_color: str,
    cumulative_log_scale: bool = False,
):
    """Factory function to create a callback for a specific yield type."""
    chart_id = f"overview-yield-{yield_type.lower().replace('yield_', '')}"

    @callback(
        Output(chart_id, "figure"),
        Input("overview-round-filter-dropdown", "value"),
        Input("overview-turn-length-slider", "value"),
        Input("overview-map-size-dropdown", "value"),
        Input("overview-map-class-dropdown", "value"),
        Input("overview-map-aspect-dropdown", "value"),
        Input("overview-nations-dropdown", "value"),
        Input("overview-players-dropdown", "value"),
        Input("overview-result-dropdown", "value"),
        Input("refresh-interval", "n_intervals"),
    )
    def update_yield_chart(
        round_num: Optional[list[int]],
        turn_length: Optional[int],
        map_size: Optional[list[str]],
        map_class: Optional[list[str]],
        map_aspect: Optional[list[str]],
        nations: Optional[List[str]],
        players: Optional[List[str]],
        result_filter: Optional[str],
        n_intervals: int,
    ):
        try:
            queries = get_queries()
            min_turns, max_turns = parse_turn_length(turn_length)

            data = queries.get_yield_with_cumulative(
                yield_type=yield_type,
                tournament_round=round_num,
                bracket=None,
                min_turns=min_turns,
                max_turns=max_turns,
                map_size=map_size,
                map_class=map_class,
                map_aspect=map_aspect,
                nations=nations if nations else None,
                players=players if players else None,
                result_filter=result_filter if result_filter != "all" else None,
            )

            if data["rate"].empty and data["cumulative"].empty:
                return create_empty_chart_placeholder("No data for selected filters")

            return create_yield_stacked_chart(
                data["rate"],
                data["cumulative"],
                display_name,
                rate_color,
                cumulative_color,
                cumulative_log_scale=cumulative_log_scale,
            )

        except Exception as e:
            logger.error(f"Error loading {display_name.lower()} data: {e}")
            return create_empty_chart_placeholder(f"Error: {str(e)}")

    return update_yield_chart


# Register callbacks for all yields except Science (which has its own callback with toggle)
for yield_type, display_name, rate_color, cumulative_color in YIELD_CHARTS:
    if yield_type == "YIELD_SCIENCE":
        continue  # Science has a separate callback with scale toggle
    _create_yield_callback(yield_type, display_name, rate_color, cumulative_color)


# Science callback with scale toggle
@callback(
    Output("overview-yield-science", "figure"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-turn-length-slider", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("overview-result-dropdown", "value"),
    Input("overview-science-scale-toggle", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_science_chart(
    round_num: Optional[list[int]],
    turn_length: Optional[int],
    map_size: Optional[list[str]],
    map_class: Optional[list[str]],
    map_aspect: Optional[list[str]],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    result_filter: Optional[str],
    scale_type: str,
    n_intervals: int,
) -> go.Figure:
    """Update Science chart with scale toggle support."""
    try:
        queries = get_queries()
        min_turns, max_turns = parse_turn_length(turn_length)

        data = queries.get_yield_with_cumulative(
            yield_type="YIELD_SCIENCE",
            tournament_round=round_num,
            bracket=None,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
            result_filter=result_filter if result_filter != "all" else None,
        )

        if data["rate"].empty and data["cumulative"].empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_yield_stacked_chart(
            data["rate"],
            data["cumulative"],
            "Science",
            "#1f77b4",
            "#2ca02c",
            cumulative_log_scale=(scale_type == "log"),
        )

    except Exception as e:
        logger.error(f"Error loading science data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-military-progression", "figure"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-turn-length-slider", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("overview-result-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_military_progression(
    round_num: Optional[list[int]],
    turn_length: Optional[int],
    map_size: Optional[list[str]],
    map_class: Optional[list[str]],
    map_aspect: Optional[list[str]],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    result_filter: Optional[str],
    n_intervals: int,
):
    """Update military progression chart with filters.

    Args:
        round_num: Selected round number
        turn_length: Maximum turn number cutoff (None means no filter)
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
        min_turns, max_turns = parse_turn_length(turn_length)

        stats = queries.get_metric_progression_stats(
            tournament_round=round_num,
            bracket=None,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
            result_filter=result_filter if result_filter != "all" else None,
        )

        if stats["military"].empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_military_progression_chart(stats["military"])

    except Exception as e:
        logger.error(f"Error loading military progression data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-legitimacy-progression", "figure"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-turn-length-slider", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("overview-result-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_legitimacy_progression(
    round_num: Optional[list[int]],
    turn_length: Optional[int],
    map_size: Optional[list[str]],
    map_class: Optional[list[str]],
    map_aspect: Optional[list[str]],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    result_filter: Optional[str],
    n_intervals: int,
):
    """Update legitimacy progression chart with filters.

    Args:
        round_num: Selected round number
        turn_length: Maximum turn number cutoff (None means no filter)
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
        min_turns, max_turns = parse_turn_length(turn_length)

        stats = queries.get_metric_progression_stats(
            tournament_round=round_num,
            bracket=None,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
            result_filter=result_filter if result_filter != "all" else None,
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
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-turn-length-slider", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("overview-result-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_expansion_timeline_chart(
    round_num: Optional[list[int]],
    turn_length: Optional[int],
    map_size: Optional[list[str]],
    map_class: Optional[list[str]],
    map_aspect: Optional[list[str]],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    result_filter: Optional[str],
    n_intervals: int,
):
    """Update the city expansion timeline chart with filters.

    Args:
        round_num: Selected round number
        turn_length: Maximum turn number cutoff (None means no filter)
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
        min_turns, max_turns = parse_turn_length(turn_length)

        df = queries.get_tournament_expansion_timeline(
            tournament_round=round_num,
            bracket=None,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
            result_filter=result_filter if result_filter != "all" else None,
        )

        if df.empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_tournament_expansion_timeline_chart(df)

    except Exception as e:
        logger.error(f"Error updating expansion timeline: {e}")
        return create_empty_chart_placeholder("Error loading expansion data")


@callback(
    Output("overview-production-strategies", "figure"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-turn-length-slider", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("overview-result-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_production_strategies_chart(
    round_num: Optional[list[int]],
    turn_length: Optional[int],
    map_size: Optional[list[str]],
    map_class: Optional[list[str]],
    map_aspect: Optional[list[str]],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    result_filter: Optional[str],
    n_intervals: int,
):
    """Update the production strategies chart with filters.

    Args:
        round_num: Selected round number
        turn_length: Maximum turn number cutoff (None means no filter)
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
        min_turns, max_turns = parse_turn_length(turn_length)

        df = queries.get_tournament_production_strategies(
            tournament_round=round_num,
            bracket=None,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations if nations else None,
            players=players if players else None,
            result_filter=result_filter if result_filter != "all" else None,
        )

        if df.empty:
            return create_empty_chart_placeholder("No data for selected filters")

        return create_tournament_production_strategies_chart(df)

    except Exception as e:
        logger.error(f"Error updating production strategies: {e}")
        return create_empty_chart_placeholder("Error loading production data")


@callback(
    Output("overview-science-per-turn-correlation", "figure"),
    Input("overview-round-filter-dropdown", "value"),
    Input("overview-turn-length-slider", "value"),
    Input("overview-map-size-dropdown", "value"),
    Input("overview-map-class-dropdown", "value"),
    Input("overview-map-aspect-dropdown", "value"),
    Input("overview-nations-dropdown", "value"),
    Input("overview-players-dropdown", "value"),
    Input("overview-result-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_science_correlation_chart(
    round_num: Optional[list[int]],
    turn_length: Optional[int],
    map_size: Optional[list[str]],
    map_class: Optional[list[str]],
    map_aspect: Optional[list[str]],
    nations: Optional[List[str]],
    players: Optional[List[str]],
    result_filter: Optional[str],
    n_intervals: int,
):
    """Update the science per turn correlation chart with filters.

    Args:
        round_num: Selected round number
        turn_length: Maximum turn number cutoff (None means no filter)
        map_size: Map size filter
        map_class: Map class filter
        map_aspect: Map aspect ratio filter
        nations: List of selected nations
        players: List of selected players
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure for science per turn vs win rate
    """
    try:
        queries = get_queries()
        min_turns, max_turns = parse_turn_length(turn_length)

        df = queries.get_science_win_correlation(
            tournament_round=round_num,
            bracket=None,
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

        # Pass result_filter to chart to show only the relevant line(s)
        return create_science_per_turn_correlation_chart(df, result_filter)

    except Exception as e:
        logger.error(f"Error creating science correlation chart: {e}")
        return create_empty_chart_placeholder("Error loading correlation data")
