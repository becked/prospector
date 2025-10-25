"""Map performance analysis page.

This page provides analysis of map characteristics and their impact on game length.
"""

import logging
from typing import Any

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, callback, html

from tournament_visualizer.components.charts import (
    create_base_figure,
    create_empty_chart_placeholder,
)
from tournament_visualizer.components.layouts import (
    create_chart_card,
    create_data_table_card,
    create_empty_state,
    create_metric_grid,
    create_page_header,
)
from tournament_visualizer.config import PAGE_CONFIG, Config
from tournament_visualizer.data.queries import get_queries

logger = logging.getLogger(__name__)

# Register this page
dash.register_page(__name__, path="/maps", name="Maps")

# Page layout
layout = html.Div(
    [
        # Page header
        create_page_header(
            title=PAGE_CONFIG["maps"]["title"],
            description=PAGE_CONFIG["maps"]["description"],
            icon="bi-map-fill",
        ),
        # Summary metrics
        html.Div(id="map-summary-metrics", className="mb-4"),
        # Performance charts
        dbc.Row(
            [
                dbc.Col(
                    [
                        create_chart_card(
                            title="Average Game Length by Map Settings",
                            chart_id="map-length-chart",
                            height="400px",
                        )
                    ],
                    width=12,
                ),
            ],
            className="mb-4",
        ),
        # Map statistics table
        dbc.Row(
            [
                dbc.Col(
                    [
                        create_data_table_card(
                            title="Map Statistics",
                            table_id="map-stats-table",
                            columns=[
                                {"name": "Map Size", "id": "map_size"},
                                {
                                    "name": "Map Class",
                                    "id": "map_class",
                                },
                                {
                                    "name": "Aspect Ratio",
                                    "id": "map_aspect_ratio",
                                },
                                {
                                    "name": "Matches",
                                    "id": "total_matches",
                                    "type": "numeric",
                                },
                                {
                                    "name": "Avg Turns",
                                    "id": "avg_turns",
                                    "type": "numeric",
                                    "format": {"specifier": ".1f"},
                                },
                                {
                                    "name": "Min Turns",
                                    "id": "min_turns",
                                    "type": "numeric",
                                },
                                {
                                    "name": "Max Turns",
                                    "id": "max_turns",
                                    "type": "numeric",
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
    ]
)


@callback(
    Output("map-summary-metrics", "children"),
    Input("refresh-interval", "n_intervals"),
)
def update_map_summary_metrics(n_intervals: int) -> html.Div:
    """Update map summary metrics.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Metrics grid component
    """
    try:
        queries = get_queries()
        df = queries.get_map_performance_analysis()

        if df.empty:
            return create_empty_state("No map data available")

        # Calculate summary metrics
        total_map_types = len(df)
        avg_game_length = df["avg_turns"].mean()
        most_popular_size = (
            df.loc[df["total_matches"].idxmax()]["map_size"] if not df.empty else None
        )
        longest_avg_game = df.loc[df["avg_turns"].idxmax()] if not df.empty else None

        metrics = [
            {
                "title": "Map Types",
                "value": total_map_types,
                "icon": "bi-map",
                "color": "primary",
            },
            {
                "title": "Avg Game Length",
                "value": (
                    f"{avg_game_length:.0f} turns"
                    if pd.notna(avg_game_length)
                    else "N/A"
                ),
                "icon": "bi-clock",
                "color": "info",
            },
            {
                "title": "Most Popular Size",
                "value": most_popular_size or "N/A",
                "icon": "bi-grid",
                "color": "success",
            },
            {
                "title": "Longest Games",
                "value": (
                    longest_avg_game["map_size"]
                    if longest_avg_game is not None
                    else "N/A"
                ),
                "subtitle": (
                    f"{longest_avg_game['avg_turns']:.0f} turns avg"
                    if longest_avg_game is not None
                    else ""
                ),
                "icon": "bi-arrow-up",
                "color": "warning",
            },
        ]

        return create_metric_grid(metrics)

    except Exception as e:
        return create_empty_state(f"Error loading metrics: {str(e)}")


@callback(
    Output("map-length-chart", "figure"),
    Input("refresh-interval", "n_intervals"),
)
def update_map_length_chart(n_intervals: int):
    """Update map length chart with grouped bars by size and class.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure for map length analysis
    """
    try:
        queries = get_queries()
        df = queries.get_map_performance_analysis()

        if df.empty:
            return create_empty_chart_placeholder("No map data available")

        # Aggregate across aspect ratios - weighted average by number of matches
        size_class_df = (
            df.groupby(["map_size", "map_class"])
            .apply(
                lambda x: pd.Series(
                    {
                        "avg_turns": (x["avg_turns"] * x["total_matches"]).sum()
                        / x["total_matches"].sum(),
                        "total_matches": x["total_matches"].sum(),
                    }
                )
            )
            .reset_index()
        )

        fig = create_base_figure(
            x_title="Map Size",
            y_title="Average Turns",
        )

        # Add grouped bars for each map class
        map_classes = size_class_df["map_class"].unique()
        for i, map_class in enumerate(map_classes):
            class_data = size_class_df[size_class_df["map_class"] == map_class]
            fig.add_trace(
                go.Bar(
                    name=map_class,
                    x=class_data["map_size"],
                    y=class_data["avg_turns"],
                    marker_color=Config.PRIMARY_COLORS[i % len(Config.PRIMARY_COLORS)],
                    text=[f"{turns:.0f}" for turns in class_data["avg_turns"]],
                    textposition="auto",
                )
            )

        fig.update_layout(
            barmode="group",
            legend={
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "xanchor": "right",
                "x": 1,
            },
        )

        return fig

    except Exception as e:
        return create_empty_chart_placeholder(
            f"Error loading map length data: {str(e)}"
        )


@callback(
    Output("map-stats-table", "data"),
    Input("refresh-interval", "n_intervals"),
)
def update_map_stats_table(n_intervals: int) -> list[dict[str, Any]]:
    """Update map statistics table.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        List of map statistics data
    """
    try:
        queries = get_queries()
        df = queries.get_map_performance_analysis()

        if df.empty:
            return []

        return df.sort_values("total_matches", ascending=False).to_dict("records")

    except Exception as e:
        logger.error(f"Error updating map stats table: {e}")
        return []
