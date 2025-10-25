"""Map and territory visualization page.

This page provides territorial control analysis, map-based visualizations,
and strategic position analytics.
"""

import logging
from typing import Any, Dict, List, Optional

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html

from tournament_visualizer.components.charts import (
    create_base_figure,
    create_empty_chart_placeholder,
    create_territory_control_chart,
)
from tournament_visualizer.components.layouts import (
    create_chart_card,
    create_data_table_card,
    create_empty_state,
    create_metric_grid,
    create_page_header,
    create_tab_layout,
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
        # Tabbed analysis sections
        create_tab_layout(
            [
                {
                    "label": "Map Performance",
                    "tab_id": "map-performance",
                    "content": [
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
                    ],
                },
                {
                    "label": "Territory Analysis",
                    "tab_id": "territory-analysis",
                    "content": [
                        # Match selection for territory analysis
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H5(
                                            "Territory Analysis", className="card-title"
                                        ),
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "Select Match:",
                                                            className="form-label",
                                                        ),
                                                        dcc.Dropdown(
                                                            id="territory-match-selector",
                                                            placeholder="Choose a match to analyze territories...",
                                                            options=[],
                                                        ),
                                                    ],
                                                    width=8,
                                                ),
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "Turn Range:",
                                                            className="form-label",
                                                        ),
                                                        dcc.RangeSlider(
                                                            id="territory-turn-range",
                                                            min=0,
                                                            max=100,
                                                            value=[0, 100],
                                                            marks={
                                                                i: str(i)
                                                                for i in range(
                                                                    0, 101, 25
                                                                )
                                                            },
                                                            tooltip={
                                                                "placement": "bottom",
                                                                "always_visible": True,
                                                            },
                                                        ),
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
                        # Territory visualizations
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Territory Control Over Time",
                                            chart_id="territory-timeline-chart",
                                            height="500px",
                                        )
                                    ],
                                    width=8,
                                ),
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Final Territory Distribution",
                                            chart_id="territory-distribution-chart",
                                            height="500px",
                                        )
                                    ],
                                    width=4,
                                ),
                            ],
                            className="mb-4",
                        ),
                        # Territory heatmap
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Territory Control Heatmap",
                                            chart_id="territory-heatmap",
                                            height="600px",
                                        )
                                    ],
                                    width=12,
                                )
                            ]
                        ),
                    ],
                },
                {
                    "label": "Strategic Analysis",
                    "tab_id": "strategic-analysis",
                    "content": [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Starting Position Impact",
                                            chart_id="starting-position-chart",
                                            height="400px",
                                        )
                                    ],
                                    width=6,
                                ),
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Map Class Performance",
                                            chart_id="map-class-performance-chart",
                                            height="400px",
                                        )
                                    ],
                                    width=6,
                                ),
                            ],
                            className="mb-4",
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        create_chart_card(
                                            title="Territory Expansion Patterns",
                                            chart_id="expansion-patterns-chart",
                                            height="500px",
                                        )
                                    ],
                                    width=12,
                                )
                            ]
                        ),
                    ],
                },
            ],
            active_tab="map-performance",
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
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
            ),
        )

        return fig

    except Exception as e:
        return create_empty_chart_placeholder(
            f"Error loading map length data: {str(e)}"
        )


@callback(
    Output("territory-match-selector", "options"),
    Input("refresh-interval", "n_intervals"),
)
def update_territory_match_options(n_intervals: int) -> List[Dict[str, Any]]:
    """Update territory match selector options.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        List of match options for territory analysis
    """
    try:
        queries = get_queries()
        df = queries.get_match_summary()

        if df.empty:
            return []

        # Filter to matches that likely have territory data
        # (we can't easily check without querying each match)
        options = []
        for _, row in df.head(20).iterrows():  # Limit to recent 20 matches
            game_name = row.get("game_name", "Unknown")
            save_date = row.get("save_date", "")
            total_turns = row.get("total_turns", 0)

            if pd.notna(save_date):
                date_str = pd.to_datetime(save_date).strftime("%Y-%m-%d")
            else:
                date_str = "Unknown Date"

            label = f"{game_name} ({date_str}) - {total_turns} turns"

            options.append({"label": label, "value": row["match_id"]})

        return options

    except Exception as e:
        logger.error(f"Error updating territory match options: {e}")
        return []


@callback(
    Output("territory-timeline-chart", "figure"),
    [
        Input("territory-match-selector", "value"),
        Input("territory-turn-range", "value"),
    ],
)
def update_territory_timeline_chart(match_id: Optional[int], turn_range: List[int]):
    """Update territory timeline chart.

    Args:
        match_id: Selected match ID
        turn_range: Selected turn range

    Returns:
        Plotly figure for territory timeline
    """
    if not match_id:
        return create_empty_chart_placeholder(
            "Select a match to view territory control"
        )

    try:
        queries = get_queries()
        df = queries.get_territory_control_summary(match_id)

        if df.empty:
            return create_empty_chart_placeholder(
                "No territory data available for this match"
            )

        # Filter by turn range
        df = df[
            (df["turn_number"] >= turn_range[0]) & (df["turn_number"] <= turn_range[1])
        ]

        if df.empty:
            return create_empty_chart_placeholder(
                "No territory data in selected turn range"
            )

        return create_territory_control_chart(df)

    except Exception as e:
        return create_empty_chart_placeholder(
            f"Error loading territory timeline: {str(e)}"
        )


@callback(
    Output("territory-distribution-chart", "figure"),
    Input("territory-match-selector", "value"),
)
def update_territory_distribution_chart(match_id: Optional[int]):
    """Update territory distribution chart.

    Args:
        match_id: Selected match ID

    Returns:
        Plotly figure for territory distribution
    """
    if not match_id:
        return create_empty_chart_placeholder("Select a match")

    try:
        queries = get_queries()
        df = queries.get_territory_control_summary(match_id)

        if df.empty:
            return create_empty_chart_placeholder("No territory data available")

        # Get final turn data
        final_turn = df["turn_number"].max()
        final_data = df[df["turn_number"] == final_turn]

        fig = create_base_figure(
            title="Final Territory Distribution", show_legend=False
        )

        fig.add_trace(
            go.Pie(
                labels=final_data["player_name"],
                values=final_data["controlled_territories"],
                hole=0.3,
                marker_colors=Config.PRIMARY_COLORS[: len(final_data)],
            )
        )

        return fig

    except Exception as e:
        return create_empty_chart_placeholder(
            f"Error loading territory distribution: {str(e)}"
        )


@callback(
    [
        Output("territory-heatmap", "figure"),
        Output("territory-turn-range", "max"),
        Output("territory-turn-range", "value"),
        Output("territory-turn-range", "marks"),
    ],
    Input("territory-match-selector", "value"),
)
def update_territory_controls(match_id: Optional[int]):
    """Update territory heatmap and configure turn slider for selected match.

    Args:
        match_id: Selected match ID

    Returns:
        Tuple of (figure, slider_max, slider_value, slider_marks)
    """
    if not match_id:
        empty_fig = create_empty_chart_placeholder(
            "Select a match to view territory map"
        )
        return empty_fig, 100, [0, 100], {i: str(i) for i in range(0, 101, 25)}

    try:
        queries = get_queries()

        # Get turn range for this match
        min_turn, max_turn = queries.get_territory_turn_range(match_id)

        if max_turn == 0:
            empty_fig = create_empty_chart_placeholder(
                "No territory data available for this match"
            )
            return empty_fig, 100, [0, 100], {i: str(i) for i in range(0, 101, 25)}

        # Get final turn map data (default view)
        df = queries.get_territory_map(match_id, max_turn)

        if df.empty:
            empty_fig = create_empty_chart_placeholder(
                "No territory data available"
            )
            return empty_fig, max_turn, [min_turn, max_turn], {}

        # Create hexagonal map
        from tournament_visualizer.components.charts import create_hexagonal_map
        fig = create_hexagonal_map(df)

        # Configure slider
        # Create marks every ~10 turns, but ensure min and max are included
        mark_step = max(1, max_turn // 10)
        marks = {i: str(i) for i in range(min_turn, max_turn + 1, mark_step)}
        marks[min_turn] = str(min_turn)  # Ensure min is marked
        marks[max_turn] = str(max_turn)  # Ensure max is marked

        return fig, max_turn, [min_turn, max_turn], marks

    except Exception as e:
        logger.error(f"Error updating territory heatmap: {e}")
        empty_fig = create_empty_chart_placeholder(
            f"Error loading territory map: {str(e)}"
        )
        return empty_fig, 100, [0, 100], {i: str(i) for i in range(0, 101, 25)}


@callback(
    Output("territory-heatmap", "figure", allow_duplicate=True),
    [
        Input("territory-match-selector", "value"),
        Input("territory-turn-range", "value"),
    ],
    prevent_initial_call=True,
)
def update_territory_heatmap_turn(
    match_id: Optional[int],
    turn_range: List[int]
) -> go.Figure:
    """Update territory heatmap when turn slider changes.

    Args:
        match_id: Selected match ID
        turn_range: [min_turn, max_turn] from slider

    Returns:
        Plotly figure for territory map at selected turn
    """
    if not match_id or not turn_range:
        return create_empty_chart_placeholder("Select a match")

    try:
        queries = get_queries()

        # Use the max value from range slider (right handle)
        display_turn = turn_range[1]

        # Get map data for selected turn
        df = queries.get_territory_map(match_id, display_turn)

        if df.empty:
            return create_empty_chart_placeholder(
                f"No territory data for turn {display_turn}"
            )

        # Create hexagonal map
        from tournament_visualizer.components.charts import create_hexagonal_map
        return create_hexagonal_map(df)

    except Exception as e:
        logger.error(f"Error updating territory map for turn: {e}")
        return create_empty_chart_placeholder(
            f"Error loading map: {str(e)}"
        )


@callback(
    Output("map-stats-table", "data"),
    Input("refresh-interval", "n_intervals"),
)
def update_map_stats_table(n_intervals: int) -> List[Dict[str, Any]]:
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


# Additional charts for strategic analysis tab
@callback(
    Output("starting-position-chart", "figure"),
    Input("refresh-interval", "n_intervals"),
)
def update_starting_position_chart(n_intervals: int):
    """Update starting position impact chart.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure for starting position analysis
    """
    # This would require more complex analysis of starting positions
    # For now, return a placeholder
    return create_empty_chart_placeholder(
        "Starting position analysis not yet implemented"
    )


@callback(
    Output("map-class-performance-chart", "figure"),
    Input("refresh-interval", "n_intervals"),
)
def update_map_class_performance_chart(n_intervals: int):
    """Update map class performance chart.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure for map class performance
    """
    try:
        queries = get_queries()
        df = queries.get_map_performance_analysis()

        if df.empty:
            return create_empty_chart_placeholder("No map class data available")

        # Group by map class
        class_performance = (
            df.groupby("map_class")
            .agg({"total_matches": "sum", "avg_turns": "mean"})
            .reset_index()
        )

        fig = create_base_figure(
            title="Map Class Performance", x_title="Map Class", y_title="Average Turns"
        )

        fig.add_trace(
            go.Bar(
                x=class_performance["map_class"],
                y=class_performance["avg_turns"],
                marker_color=Config.PRIMARY_COLORS[2],
                text=[f"{turns:.0f}" for turns in class_performance["avg_turns"]],
                textposition="auto",
            )
        )

        fig.update_layout(xaxis_tickangle=-45)

        return fig

    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading map class data: {str(e)}")


@callback(
    Output("expansion-patterns-chart", "figure"),
    Input("refresh-interval", "n_intervals"),
)
def update_expansion_patterns_chart(n_intervals: int):
    """Update expansion patterns chart.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Plotly figure for expansion patterns
    """
    # This would require complex analysis of territory expansion over time
    # For now, return a placeholder
    return create_empty_chart_placeholder(
        "Expansion pattern analysis not yet implemented"
    )
