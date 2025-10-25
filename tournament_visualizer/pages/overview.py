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
                        # Event Category Timeline - full width
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
                    ],
                ),
            ],
            id="overview-tabs",
            active_tab="summary-tab",
        ),
    ]
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
    Input("refresh-interval", "n_intervals"),
)
def update_nation_win_chart(n_intervals: int):
    """Update the nation win percentage chart.

    Args:
        n_intervals: Number of interval triggers

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
    Input("refresh-interval", "n_intervals"),
)
def update_nation_loss_chart(n_intervals: int):
    """Update the nation loss percentage chart.

    Args:
        n_intervals: Number of interval triggers

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
    Input("refresh-interval", "n_intervals"),
)
def update_nation_popularity_chart(n_intervals: int):
    """Update the nation popularity chart.

    Args:
        n_intervals: Number of interval triggers

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
    Output("overview-matches-table", "data"), Input("refresh-interval", "n_intervals")
)
def update_matches_table(n_intervals: int) -> List[Dict[str, Any]]:
    """Update the matches table.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        List of dictionaries for table data
    """
    try:
        queries = get_queries()
        df = queries.get_recent_matches(limit=None)

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
    Input("refresh-interval", "n_intervals"),
)
def update_law_distribution(n_intervals: int):
    """Update law milestone distribution chart.

    Shows data from ALL matches.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with box plot distribution
    """
    try:
        queries = get_queries()
        # Get ALL matches data
        df = queries.get_law_progression_by_match(match_id=None)

        if df.empty:
            return create_empty_chart_placeholder("No law progression data available")

        return create_law_milestone_distribution_chart(df)

    except Exception as e:
        logger.error(f"Error loading law distribution: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-law-efficiency", "figure"),
    Input("refresh-interval", "n_intervals"),
)
def update_law_efficiency(n_intervals: int):
    """Update law efficiency scatter plot.

    Shows data from ALL matches.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with scatter plot
    """
    try:
        queries = get_queries()
        df = queries.get_law_progression_by_match(match_id=None)

        if df.empty:
            return create_empty_chart_placeholder("No law progression data available")

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
    Input("refresh-interval", "n_intervals"),
)
def update_ruler_archetype_chart(n_intervals: int):
    """Update ruler archetype win rates chart.

    Shows win rates and games played for each starting archetype.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with dual-axis chart
    """
    try:
        queries = get_queries()
        df = queries.get_ruler_archetype_win_rates()

        if df.empty:
            return create_empty_chart_placeholder("No ruler data available")

        return create_ruler_archetype_win_rates_chart(df)

    except Exception as e:
        logger.error(f"Error loading ruler archetype data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-ruler-trait-performance-chart", "figure"),
    Input("refresh-interval", "n_intervals"),
)
def update_ruler_trait_performance_chart(n_intervals: int):
    """Update ruler trait performance chart.

    Shows win rates and games played for each starting trait.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with dual-axis chart
    """
    try:
        queries = get_queries()
        df = queries.get_ruler_trait_win_rates(min_games=1)

        if df.empty:
            return create_empty_chart_placeholder("No ruler data available")

        return create_ruler_trait_performance_chart(df)

    except Exception as e:
        logger.error(f"Error loading ruler trait data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-ruler-matchup-matrix-chart", "figure"),
    Input("refresh-interval", "n_intervals"),
)
def update_ruler_matchup_matrix_chart(n_intervals: int):
    """Update ruler archetype matchup matrix chart.

    Shows win rates for each archetype vs archetype matchup.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with heatmap
    """
    try:
        queries = get_queries()
        df = queries.get_ruler_archetype_matchups()

        if df.empty:
            return create_empty_chart_placeholder("No archetype matchup data available")

        return create_ruler_archetype_matchup_matrix(df)

    except Exception as e:
        logger.error(f"Error loading ruler matchup data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-ruler-combinations-chart", "figure"),
    Input("refresh-interval", "n_intervals"),
)
def update_ruler_combinations_chart(n_intervals: int):
    """Update ruler archetype + trait combinations chart.

    Shows most popular starting ruler combinations.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with horizontal bar chart
    """
    try:
        queries = get_queries()
        df = queries.get_ruler_archetype_trait_combinations(limit=10)

        if df.empty:
            return create_empty_chart_placeholder("No ruler data available")

        return create_ruler_archetype_trait_combinations_chart(df)

    except Exception as e:
        logger.error(f"Error loading ruler combinations data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-counter-pick-heatmap", "figure"),
    Input("refresh-interval", "n_intervals"),
)
def update_counter_pick_heatmap(n_intervals: int):
    """Update nation counter-pick effectiveness heatmap.

    Shows which nations are effective counters when picked second.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with heatmap
    """
    try:
        queries = get_queries()
        df = queries.get_nation_counter_pick_matrix(min_games=1)

        if df.empty:
            return create_empty_chart_placeholder(
                "No counter-pick data available. Pick order data needs to be synced."
            )

        return create_nation_counter_pick_heatmap(df)

    except Exception as e:
        logger.error(f"Error loading counter-pick data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-pick-order-win-rate", "figure"),
    Input("refresh-interval", "n_intervals"),
)
def update_pick_order_win_rate(n_intervals: int):
    """Update pick order win rate bar chart.

    Shows overall first pick vs second pick win rates with confidence intervals
    and statistical significance annotation.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with grouped bar chart
    """
    try:
        queries = get_queries()
        df = queries.get_pick_order_win_rates()

        if df.empty:
            return create_empty_chart_placeholder(
                "No pick order data available. Pick order data needs to be synced."
            )

        return create_pick_order_win_rate_chart(df)

    except Exception as e:
        logger.error(f"Error loading pick order win rate data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-science-progression", "figure"),
    Input("refresh-interval", "n_intervals"),
)
def update_science_progression(n_intervals: int):
    """Update science progression chart.

    Shows median science per turn with 25th-75th percentile band across all matches.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with line chart
    """
    try:
        queries = get_queries()
        stats = queries.get_metric_progression_stats()

        if stats["science"].empty:
            return create_empty_chart_placeholder("No science data available")

        return create_science_progression_chart(stats["science"])

    except Exception as e:
        logger.error(f"Error loading science progression data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-orders-progression", "figure"),
    Input("refresh-interval", "n_intervals"),
)
def update_orders_progression(n_intervals: int):
    """Update orders progression chart.

    Shows median orders per turn with 25th-75th percentile band across all matches.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with line chart
    """
    try:
        queries = get_queries()
        stats = queries.get_metric_progression_stats()

        if stats["orders"].empty:
            return create_empty_chart_placeholder("No orders data available")

        return create_orders_progression_chart(stats["orders"])

    except Exception as e:
        logger.error(f"Error loading orders progression data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-military-progression", "figure"),
    Input("refresh-interval", "n_intervals"),
)
def update_military_progression(n_intervals: int):
    """Update military progression chart.

    Shows median military score per turn with 25th-75th percentile band across all matches.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with line chart
    """
    try:
        queries = get_queries()
        stats = queries.get_metric_progression_stats()

        if stats["military"].empty:
            return create_empty_chart_placeholder("No military data available")

        return create_military_progression_chart(stats["military"])

    except Exception as e:
        logger.error(f"Error loading military progression data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")


@callback(
    Output("overview-legitimacy-progression", "figure"),
    Input("refresh-interval", "n_intervals"),
)
def update_legitimacy_progression(n_intervals: int):
    """Update legitimacy progression chart.

    Shows median legitimacy per turn with 25th-75th percentile band across all matches.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure with line chart
    """
    try:
        queries = get_queries()
        stats = queries.get_metric_progression_stats()

        if stats["legitimacy"].empty:
            return create_empty_chart_placeholder("No legitimacy data available")

        return create_legitimacy_progression_chart(stats["legitimacy"])

    except Exception as e:
        logger.error(f"Error loading legitimacy progression data: {e}")
        return create_empty_chart_placeholder(f"Error: {str(e)}")
