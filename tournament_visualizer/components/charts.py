"""Chart generation functions for tournament data visualization.

This module provides functions to create various types of charts and visualizations
using Plotly for the tournament dashboard.
"""

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..config import CIVILIZATION_COLORS, DEFAULT_CHART_LAYOUT, Config
from ..nation_colors import get_nation_color
from ..theme import CHART_THEME


def apply_dark_theme(fig: go.Figure) -> go.Figure:
    """Apply dark theme to any figure (especially subplots).

    Use this for figures created with make_subplots() which don't go through
    create_base_figure().

    Args:
        fig: Plotly figure to apply dark theme to

    Returns:
        The same figure with dark theme applied
    """
    fig.update_layout(
        paper_bgcolor=CHART_THEME["paper_bgcolor"],
        plot_bgcolor=CHART_THEME["plot_bgcolor"],
        font=dict(color=CHART_THEME["font_color"]),
        hoverlabel=dict(
            bgcolor=CHART_THEME["hoverlabel_bgcolor"],
            bordercolor=CHART_THEME["hoverlabel_bordercolor"],
            font=dict(color=CHART_THEME["hoverlabel_font_color"]),
        ),
    )
    # Update all axes (subplots create xaxis, xaxis2, xaxis3, etc.)
    fig.update_xaxes(
        gridcolor=CHART_THEME["gridcolor"],
        tickfont=dict(color=CHART_THEME["font_color"]),
        title_font=dict(color=CHART_THEME["font_color"]),
    )
    fig.update_yaxes(
        gridcolor=CHART_THEME["gridcolor"],
        tickfont=dict(color=CHART_THEME["font_color"]),
        title_font=dict(color=CHART_THEME["font_color"]),
    )
    return fig


def create_base_figure(
    title: str = "",
    height: int = None,
    show_legend: bool = True,
    x_title: str = "",
    y_title: str = "",
) -> go.Figure:
    """Create a base figure with consistent styling.

    Args:
        title: Chart title
        height: Chart height in pixels
        show_legend: Whether to show the legend
        x_title: X-axis title
        y_title: Y-axis title

    Returns:
        Configured Plotly figure
    """
    import copy

    # Deep copy to avoid mutating the default layout
    layout = copy.deepcopy(DEFAULT_CHART_LAYOUT)
    layout.update(
        {
            "title": {
                "text": title,
                "x": 0.5,
                "xanchor": "center",
                "font": {"color": CHART_THEME["font_color"]},
            },
            "showlegend": show_legend,
            "xaxis_title": x_title,
            "yaxis_title": y_title,
        }
    )

    if height:
        layout["height"] = height

    fig = go.Figure(layout=layout)
    return fig


def create_match_timeline_chart(df: pd.DataFrame) -> go.Figure:
    """Create a timeline chart showing matches over time with civilization breakdown.

    Args:
        df: DataFrame with match data including save_date and winner_civilization

    Returns:
        Plotly figure with stacked bar chart timeline
    """
    if df.empty:
        return create_base_figure("No match data available")

    # Ensure save_date is datetime
    df = df.copy()
    df["save_date"] = pd.to_datetime(df["save_date"])

    # Group by date and civilization
    df["date"] = df["save_date"].dt.date
    daily_civ_matches = (
        df.groupby(["date", "winner_civilization"]).size().reset_index(name="count")
    )

    # Pivot to get civilizations as columns
    pivot_data = daily_civ_matches.pivot(
        index="date", columns="winner_civilization", values="count"
    ).fillna(0)

    fig = create_base_figure(
        title="Match Timeline", x_title="Date", y_title="Number of Matches"
    )

    # Add a bar trace for each civilization
    for i, civ in enumerate(pivot_data.columns):
        color = CIVILIZATION_COLORS.get(
            civ, Config.PRIMARY_COLORS[i % len(Config.PRIMARY_COLORS)]
        )
        fig.add_trace(
            go.Bar(name=civ, x=pivot_data.index, y=pivot_data[civ], marker_color=color)
        )

    # Configure as stacked bar chart
    fig.update_layout(barmode="stack", xaxis_tickangle=-45)

    # Fix date formatting to show proper format
    fig.update_xaxes(tickformat="%b %e, %Y")

    return fig


def create_player_performance_chart(df: pd.DataFrame) -> go.Figure:
    """Create a bar chart showing player performance statistics.

    Args:
        df: DataFrame with player performance data

    Returns:
        Plotly figure with player performance bars
    """
    if df.empty:
        return create_base_figure("No player data available")

    # Sort by win rate and take top 10
    df_sorted = df.sort_values("win_rate", ascending=False).head(10)

    fig = create_base_figure(
        title="Top 10 Player Performance", x_title="Win Rate (%)", y_title="Player"
    )

    fig.add_trace(
        go.Bar(
            x=df_sorted["win_rate"],
            y=df_sorted["player_name"],
            orientation="h",
            marker_color=Config.PRIMARY_COLORS[1],
            text=[f"{rate:.1f}%" for rate in df_sorted["win_rate"]],
            textposition="auto",
        )
    )

    fig.update_layout(yaxis={"categoryorder": "total ascending"})

    return fig


def create_civilization_performance_chart(df: pd.DataFrame) -> go.Figure:
    """Create a chart showing civilization performance.

    Args:
        df: DataFrame with civilization performance data

    Returns:
        Plotly figure with civilization performance
    """
    if df.empty:
        return create_base_figure("No civilization data available")

    # Sort by win rate
    df_sorted = df.sort_values("win_rate", ascending=True)

    # Create colors based on civilization names
    colors = [
        CIVILIZATION_COLORS.get(
            civ, Config.PRIMARY_COLORS[i % len(Config.PRIMARY_COLORS)]
        )
        for i, civ in enumerate(df_sorted["civilization"])
    ]

    fig = create_base_figure(
        title="Civilization Performance", x_title="Win Rate (%)", y_title="Civilization"
    )

    fig.add_trace(
        go.Bar(
            x=df_sorted["win_rate"],
            y=df_sorted["civilization"],
            orientation="h",
            marker_color=colors,
            text=[f"{rate:.1f}%" for rate in df_sorted["win_rate"]],
            textposition="auto",
        )
    )

    fig.update_layout(yaxis={"categoryorder": "total ascending"})

    return fig


def create_match_duration_distribution(df: pd.DataFrame) -> go.Figure:
    """Create a box plot showing match duration distribution grouped by player count.

    Improved to show distribution shape and account for different game modes.

    Args:
        df: DataFrame with match duration data (should include player_count column)

    Returns:
        Plotly figure with grouped box plots
    """
    if df.empty:
        return create_base_figure("No match duration data available")

    # Check if player_count column exists
    if "player_count" not in df.columns:
        # Fallback to simple histogram if player_count not available
        fig = create_base_figure(
            title="Match Duration Distribution",
            x_title="Number of Turns",
            y_title="Number of Matches",
        )

        fig.add_trace(
            go.Histogram(
                x=df["total_turns"],
                nbinsx=20,
                marker_color=Config.PRIMARY_COLORS[2],
                opacity=0.7,
            )
        )

        avg_turns = df["total_turns"].mean()
        fig.add_vline(
            x=avg_turns,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Avg: {avg_turns:.1f} turns",
        )

        return fig

    # Create box plot grouped by player count
    fig = create_base_figure(
        title="Match Duration Distribution by Player Count",
        x_title="Number of Players",
        y_title="Match Duration (Turns)",
        height=450,
    )

    # Get unique player counts and sort them
    player_counts = sorted(df["player_count"].unique())

    for i, count in enumerate(player_counts):
        df_subset = df[df["player_count"] == count]

        fig.add_trace(
            go.Box(
                y=df_subset["total_turns"],
                name=f"{count} Players",
                marker_color=Config.PRIMARY_COLORS[i % len(Config.PRIMARY_COLORS)],
                boxmean="sd",  # Show mean and standard deviation
            )
        )

    # Add overall statistics annotation
    avg_turns = df["total_turns"].mean()
    median_turns = df["total_turns"].median()

    fig.add_annotation(
        text=f"Overall - Mean: {avg_turns:.1f} turns, Median: {median_turns:.1f} turns",
        xref="paper",
        yref="paper",
        x=0.5,
        y=1.1,
        showarrow=False,
        font=dict(size=11),
    )

    return fig


def create_resource_progression_chart(df: pd.DataFrame, player_name: str) -> go.Figure:
    """Create a line chart showing resource progression over time.

    Args:
        df: DataFrame with resource progression data
        player_name: Name of the player to show

    Returns:
        Plotly figure with resource progression
    """
    if df.empty:
        return create_base_figure(f"No resource data available for {player_name}")

    # Filter for specific player
    player_data = df[df["player_name"] == player_name]

    if player_data.empty:
        return create_base_figure(f"No resource data available for {player_name}")

    fig = create_base_figure(
        title=f"Resource Progression - {player_name}",
        x_title="Turn Number",
        y_title="Resource Amount",
    )

    # Add a line for each resource type
    resource_types = player_data["resource_type"].unique()

    for i, resource_type in enumerate(resource_types):
        resource_data = player_data[player_data["resource_type"] == resource_type]

        fig.add_trace(
            go.Scatter(
                x=resource_data["turn_number"],
                y=resource_data["amount"],
                mode="lines+markers",
                name=resource_type,
                line=dict(color=Config.PRIMARY_COLORS[i % len(Config.PRIMARY_COLORS)]),
                marker=dict(size=4),
            )
        )

    return fig


def create_territory_control_chart(
    df: pd.DataFrame,
    player_colors: Optional[Dict[str, str]] = None,
) -> go.Figure:
    """Create an area chart showing territory control over time.

    Args:
        df: DataFrame with territory control data over time
        player_colors: Optional dict mapping player names to hex colors

    Returns:
        Plotly figure with territory control
    """
    if df.empty:
        return create_base_figure("No territory control data available")

    fig = create_base_figure(
        title="Territory Control Over Time",
        x_title="Turn Number",
        y_title="Controlled Territories",
    )

    # Get unique players
    players = df["player_name"].dropna().unique()

    for i, player in enumerate(players):
        player_data = df[df["player_name"] == player]

        # Use nation-based color if provided
        if player_colors and player in player_colors:
            color = player_colors[player]
        else:
            color = Config.PRIMARY_COLORS[i % len(Config.PRIMARY_COLORS)]

        fig.add_trace(
            go.Scatter(
                x=player_data["turn_number"],
                y=player_data["controlled_territories"],
                mode="lines",
                name=player,
                fill="tonexty" if i > 0 else "tozeroy",
                line=dict(color=color),
            )
        )

    return fig


def create_event_timeline_chart(df: pd.DataFrame) -> go.Figure:
    """Create a timeline chart showing game events.

    Args:
        df: DataFrame with event timeline data

    Returns:
        Plotly figure with event timeline
    """
    if df.empty:
        return create_base_figure("No event data available")

    fig = create_base_figure(
        title="Game Events Timeline", x_title="Turn Number", y_title="Event Type"
    )

    # Create scatter plot with events
    event_types = df["event_type"].unique()
    y_positions = {event: i for i, event in enumerate(event_types)}

    for event_type in event_types:
        event_data = df[df["event_type"] == event_type]

        fig.add_trace(
            go.Scatter(
                x=event_data["turn_number"],
                y=[y_positions[event_type]] * len(event_data),
                mode="markers",
                name=event_type,
                marker=dict(
                    size=8,
                    color=Config.PRIMARY_COLORS[
                        y_positions[event_type] % len(Config.PRIMARY_COLORS)
                    ],
                ),
                text=event_data["description"],
                hovertemplate="<b>%{fullData.name}</b><br>Turn: %{x}<br>%{text}<extra></extra>",
            )
        )

    fig.update_layout(
        yaxis=dict(
            tickmode="array",
            tickvals=list(y_positions.values()),
            ticktext=list(y_positions.keys()),
        )
    )

    return fig


def create_win_rate_by_map_chart(df: pd.DataFrame) -> go.Figure:
    """Create a chart showing win rates by map type.

    Args:
        df: DataFrame with map performance data

    Returns:
        Plotly figure with map win rates
    """
    if df.empty:
        return create_base_figure("No map data available")

    fig = create_base_figure(
        title="Average Game Length by Map", x_title="Map Type", y_title="Average Turns"
    )

    # Create a grouped bar chart for map size and class
    if "map_size" in df.columns and "avg_turns" in df.columns:
        fig.add_trace(
            go.Bar(
                x=df["map_size"],
                y=df["avg_turns"],
                name="Map Size",
                marker_color=Config.PRIMARY_COLORS[0],
                text=[f"{turns:.0f}" for turns in df["avg_turns"]],
                textposition="auto",
            )
        )

    return fig


def create_head_to_head_chart(
    stats: Dict[str, Any], player1: str, player2: str
) -> go.Figure:
    """Create a head-to-head comparison chart.

    Args:
        stats: Dictionary with head-to-head statistics
        player1: Name of first player
        player2: Name of second player

    Returns:
        Plotly figure with head-to-head comparison
    """
    if not stats or stats.get("total_matches", 0) == 0:
        return create_base_figure(f"No head-to-head data for {player1} vs {player2}")

    fig = create_base_figure(
        title=f"Head-to-Head: {player1} vs {player2}", show_legend=False
    )

    # Create pie chart for wins
    labels = [player1, player2, "Other/Draw"]
    values = [
        stats.get("player1_wins", 0),
        stats.get("player2_wins", 0),
        stats.get("total_matches", 0)
        - stats.get("player1_wins", 0)
        - stats.get("player2_wins", 0),
    ]

    # Filter out zero values
    filtered_data = [
        (label, value) for label, value in zip(labels, values) if value > 0
    ]
    if filtered_data:
        labels, values = zip(*filtered_data)

    fig.add_trace(
        go.Pie(
            labels=labels,
            values=values,
            marker_colors=Config.PRIMARY_COLORS[: len(labels)],
        )
    )

    return fig


def create_victory_condition_chart(df: pd.DataFrame) -> go.Figure:
    """Create a chart showing victory condition analysis.

    Args:
        df: DataFrame with victory condition data

    Returns:
        Plotly figure with victory conditions
    """
    if df.empty:
        return create_base_figure("No victory condition data available")

    fig = create_base_figure(
        title="Victory Conditions Analysis",
        x_title="Victory Condition",
        y_title="Average Game Length (Turns)",
    )

    fig.add_trace(
        go.Bar(
            x=df["victory_conditions"],
            y=df["avg_turns"],
            marker_color=Config.PRIMARY_COLORS[3],
            text=[f"{turns:.0f}" for turns in df["avg_turns"]],
            textposition="auto",
        )
    )

    fig.update_layout(xaxis_tickangle=-45)

    return fig


def create_heatmap_chart(
    data: pd.DataFrame, x_col: str, y_col: str, value_col: str, title: str = "Heatmap"
) -> go.Figure:
    """Create a generic heatmap chart.

    Args:
        data: DataFrame with heatmap data
        x_col: Column name for x-axis
        y_col: Column name for y-axis
        value_col: Column name for values
        title: Chart title

    Returns:
        Plotly figure with heatmap
    """
    if data.empty:
        return create_base_figure(f"No data available for {title}")

    # Pivot the data for heatmap
    pivot_data = data.pivot_table(
        index=y_col, columns=x_col, values=value_col, aggfunc="mean"
    )

    fig = create_base_figure(title=title, show_legend=False)

    fig.add_trace(
        go.Heatmap(
            z=pivot_data.values,
            x=pivot_data.columns,
            y=pivot_data.index,
            colorscale="RdYlBu",
            reversescale=True,
        )
    )

    return fig


def create_summary_metrics_cards(stats: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Create summary metric cards for dashboard.

    Args:
        stats: Dictionary with database statistics

    Returns:
        List of metric card configurations
    """
    cards = []

    # Total matches card
    cards.append(
        {
            "title": "Total Matches",
            "value": stats.get("matches_count", 0),
            "icon": "bi-trophy",
            "color": "primary",
        }
    )

    # Unique players card
    cards.append(
        {
            "title": "Unique Players",
            "value": stats.get("unique_players", 0),
            "icon": "bi-people",
            "color": "info",
        }
    )

    # Average game length card
    turn_stats = stats.get("turn_stats", {})
    avg_turns = turn_stats.get("avg", 0)
    cards.append(
        {
            "title": "Avg Game Length",
            "value": f"{avg_turns:.0f} turns" if avg_turns else "N/A",
            "icon": "bi-clock",
            "color": "success",
        }
    )

    return cards


def create_empty_chart_placeholder(message: str = "No data available") -> go.Figure:
    """Create a placeholder chart when no data is available.

    Args:
        message: Message to display

    Returns:
        Plotly figure with placeholder message
    """
    fig = go.Figure()

    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        xanchor="center",
        yanchor="middle",
        showarrow=False,
        font=dict(size=16, color=CHART_THEME["text_muted"]),
    )

    fig.update_layout(
        showlegend=False,
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        plot_bgcolor=CHART_THEME["plot_bgcolor"],
        paper_bgcolor=CHART_THEME["paper_bgcolor"],
    )

    return fig


def apply_chart_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    """Apply filters to chart data.

    Args:
        df: DataFrame to filter
        filters: Dictionary of filter values

    Returns:
        Filtered DataFrame
    """
    from .filters import apply_filters_to_dataframe

    return apply_filters_to_dataframe(df, filters)


def create_technology_comparison_chart(df: pd.DataFrame) -> go.Figure:
    """Create a bar chart comparing technology research across players.

    Args:
        df: DataFrame with technology progress data (player_name, civilization, tech_name, count)

    Returns:
        Plotly figure with technology comparison
    """
    if df.empty:
        return create_base_figure("No technology data available")

    # Aggregate by player to show total tech counts
    player_tech_counts = (
        df.groupby(["player_name", "civilization"])["count"].sum().reset_index()
    )
    player_tech_counts = player_tech_counts.sort_values("count", ascending=True)

    # Create colors based on civilization
    colors = [
        CIVILIZATION_COLORS.get(
            civ, Config.PRIMARY_COLORS[i % len(Config.PRIMARY_COLORS)]
        )
        for i, civ in enumerate(player_tech_counts["civilization"])
    ]

    # Build data arrays in the same order
    x_values = []
    y_labels = []
    hover_texts = []
    text_values = []

    for _, row in player_tech_counts.iterrows():
        player_name = row["player_name"]
        civilization = row["civilization"]
        total_count = row["count"]

        # Get list of technologies for this player
        techs = df[df["player_name"] == player_name]["tech_name"].tolist()
        tech_list = "<br>".join(techs)

        # Build the hover text
        hover_text = f"<b>{player_name} ({civilization})</b><br>Total: {total_count}<br><br>Technologies:<br>{tech_list}"

        x_values.append(total_count)
        y_labels.append(f"{player_name} ({civilization})")
        hover_texts.append(hover_text)
        text_values.append(total_count)

    fig = create_base_figure(
        title="Technology Research Comparison",
        x_title="Total Technologies Researched",
        y_title="Player",
        show_legend=False,
    )

    fig.add_trace(
        go.Bar(
            x=x_values,
            y=y_labels,
            orientation="h",
            marker_color=colors,
            text=text_values,
            textposition="auto",
            hovertemplate="%{hovertext}<extra></extra>",
            hovertext=hover_texts,
            showlegend=False,
        )
    )

    # Don't use categoryorder to avoid Plotly reordering without updating hover data
    # Data is already sorted in ascending order above
    fig.update_layout(yaxis={"categoryorder": "array", "categoryarray": y_labels})

    return fig


def create_technology_detail_chart(df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    """Create a grouped bar chart showing specific technology research by player.

    Args:
        df: DataFrame with technology progress data
        top_n: Number of top technologies to display

    Returns:
        Plotly figure with detailed technology comparison
    """
    if df.empty:
        return create_base_figure("No technology data available")

    # Get top N most researched technologies
    top_techs = df.groupby("tech_name")["count"].sum().nlargest(top_n).index.tolist()
    df_filtered = df[df["tech_name"].isin(top_techs)]

    fig = create_base_figure(
        title=f"Top {top_n} Technologies by Player",
        x_title="Technology",
        y_title="Count",
    )

    # Create a grouped bar chart
    players = df_filtered["player_name"].unique()

    for i, player in enumerate(players):
        player_data = df_filtered[df_filtered["player_name"] == player]

        fig.add_trace(
            go.Bar(
                name=player,
                x=player_data["tech_name"],
                y=player_data["count"],
                marker_color=Config.PRIMARY_COLORS[i % len(Config.PRIMARY_COLORS)],
            )
        )

    fig.update_layout(barmode="group", xaxis_tickangle=-45)

    return fig


def create_player_statistics_comparison_chart(
    df: pd.DataFrame, stat_names: Optional[List[str]] = None
) -> go.Figure:
    """Create a grouped bar chart comparing player statistics.

    Args:
        df: DataFrame with player statistics (player_name, stat_name, value)
        stat_names: Optional list of specific stat names to display

    Returns:
        Plotly figure with statistics comparison
    """
    if df.empty:
        return create_base_figure("No statistics data available")

    # Filter to specific stats if provided
    if stat_names:
        df = df[df["stat_name"].isin(stat_names)]

    if df.empty:
        return create_base_figure("No data for selected statistics")

    fig = create_base_figure(
        title="Player Statistics Comparison", x_title="Statistic", y_title="Value"
    )

    # Create grouped bars by player
    players = df["player_name"].unique()

    for i, player in enumerate(players):
        player_data = df[df["player_name"] == player]

        fig.add_trace(
            go.Bar(
                name=player,
                x=player_data["stat_name"],
                y=player_data["value"],
                marker_color=Config.PRIMARY_COLORS[i % len(Config.PRIMARY_COLORS)],
                text=player_data["value"],
                textposition="auto",
            )
        )

    fig.update_layout(barmode="group", xaxis_tickangle=-45)

    return fig


def create_statistics_grouped_bar(
    df: pd.DataFrame, category_filter: Optional[str] = None, top_n: int = 10
) -> go.Figure:
    """Create a grouped bar chart showing top N player statistics.

    Args:
        df: DataFrame with player statistics (must have stat_name, player_name, value columns)
        category_filter: Optional category to filter by
        top_n: Number of top statistics to show

    Returns:
        Plotly figure with grouped bar chart
    """
    if df.empty:
        return create_base_figure("No statistics data available")

    # Filter by category if specified
    if category_filter and "stat_category" in df.columns:
        df = df[df["stat_category"] == category_filter]

    if df.empty:
        return create_base_figure(
            f"No statistics available for category: {category_filter}"
        )

    # Calculate total value per stat across all players
    stat_totals = df.groupby("stat_name")["value"].sum().sort_values(ascending=False)
    top_stats = stat_totals.head(top_n).index.tolist()

    # Filter to top stats
    df_filtered = df[df["stat_name"].isin(top_stats)]

    fig = create_base_figure(
        title=f"Top {top_n} Statistics Comparison"
        + (f" - {category_filter}" if category_filter else ""),
        x_title="Statistic",
        y_title="Value",
    )

    # Add a bar for each player
    for i, player in enumerate(df_filtered["player_name"].unique()):
        player_data = df_filtered[df_filtered["player_name"] == player]

        # Ensure we have values for all top stats (fill missing with 0)
        stat_values = []
        for stat in top_stats:
            value = player_data[player_data["stat_name"] == stat]["value"].values
            stat_values.append(value[0] if len(value) > 0 else 0)

        fig.add_trace(
            go.Bar(
                name=player,
                x=top_stats,
                y=stat_values,
                marker_color=Config.PRIMARY_COLORS[i % len(Config.PRIMARY_COLORS)],
                text=stat_values,
                textposition="auto",
            )
        )

    fig.update_layout(barmode="group", xaxis_tickangle=-45)

    return fig


def create_statistics_radar_chart(
    df: pd.DataFrame, category_filter: Optional[str] = None, top_n: int = 8
) -> go.Figure:
    """Create a radar chart comparing player statistics across top N stats.

    Args:
        df: DataFrame with player statistics
        category_filter: Optional category to filter by
        top_n: Number of top statistics to show on radar

    Returns:
        Plotly figure with radar chart
    """
    if df.empty:
        return create_base_figure("No statistics data available")

    # Filter by category if specified
    if category_filter and "stat_category" in df.columns:
        df = df[df["stat_category"] == category_filter]

    if df.empty:
        return create_base_figure(f"No data for category: {category_filter}")

    # Get top N stats by total value
    stat_totals = df.groupby("stat_name")["value"].sum().sort_values(ascending=False)
    top_stats = stat_totals.head(top_n).index.tolist()

    # Filter to top stats
    df_filtered = df[df["stat_name"].isin(top_stats)]

    fig = go.Figure()

    # Get unique players
    player_names = df_filtered["player_name"].unique()

    for i, player in enumerate(player_names):
        player_data = df_filtered[df_filtered["player_name"] == player]

        # Normalize values to 0-100 range for each stat
        values = []
        for stat in top_stats:
            stat_data = df_filtered[df_filtered["stat_name"] == stat]
            max_val = stat_data["value"].max()
            player_val = player_data[player_data["stat_name"] == stat]["value"].values
            normalized = (
                (player_val[0] / max_val * 100)
                if len(player_val) > 0 and max_val > 0
                else 0
            )
            values.append(normalized)

        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=top_stats,
                fill="toself",
                name=player,
                line_color=Config.PRIMARY_COLORS[i % len(Config.PRIMARY_COLORS)],
            )
        )

    # Create a better title based on the category
    if category_filter == "yield_stockpile":
        title = "Yield Stockpiles Comparison (Normalized %)"
    elif category_filter == "bonus_count":
        title = f"Top {top_n} Bonus Events Comparison (Normalized %)"
    elif category_filter == "law_changes":
        title = "Law Changes Comparison (Normalized %)"
    else:
        title = f"Top {top_n} Statistics Comparison (Normalized %)"
        if category_filter:
            title += f" - {category_filter}"

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100]),
            bgcolor=CHART_THEME["plot_bgcolor"],
        ),
        showlegend=True,
        title=title,
        paper_bgcolor=CHART_THEME["paper_bgcolor"],
        font=dict(color=CHART_THEME["font_color"]),
    )

    return fig


def create_law_progression_chart(df: pd.DataFrame) -> go.Figure:
    """Create a bar chart showing total laws enacted by each player.

    Args:
        df: DataFrame with columns: player_name, civilization,
            total_laws_adopted (or legacy 'total_laws'), total_turns

    Returns:
        Plotly figure with grouped bar chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No law progression data available")

    # Support both old and new column names for backwards compatibility
    laws_col = 'total_laws_adopted' if 'total_laws_adopted' in df.columns else 'total_laws'

    fig = create_base_figure(
        title="Law Progression by Player",
        x_title="Player",
        y_title="Total Laws Adopted",
        height=400,
    )

    # Sort by total laws descending
    df_sorted = df.sort_values(laws_col, ascending=False)

    # Create hover text with additional info
    hover_text = [
        f"Player: {row['player_name']}<br>"
        + f"Civilization: {row.get('civilization', 'Unknown')}<br>"
        + f"Laws Adopted: {row[laws_col]}<br>"
        + f"Total Turns: {row.get('total_turns', 'N/A')}"
        for _, row in df_sorted.iterrows()
    ]

    fig.add_trace(
        go.Bar(
            x=df_sorted["player_name"],
            y=df_sorted[laws_col],
            text=df_sorted[laws_col],
            textposition="auto",
            hovertext=hover_text,
            hoverinfo="text",
            marker_color=Config.PRIMARY_COLORS[0],
        )
    )

    fig.update_layout(showlegend=False)
    fig.update_xaxes(tickangle=-45)

    return fig


def create_law_milestone_chart(df: pd.DataFrame) -> go.Figure:
    """Create a chart showing estimated turns to reach law milestones (4 laws, 7 laws).

    Args:
        df: DataFrame with columns: player_name, estimated_turn_to_4_laws, estimated_turn_to_7_laws

    Returns:
        Plotly figure with grouped bar chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No law milestone data available")

    # Filter out rows where both milestones are null
    df_filtered = df[
        df["estimated_turn_to_4_laws"].notna() | df["estimated_turn_to_7_laws"].notna()
    ].copy()

    if df_filtered.empty:
        return create_empty_chart_placeholder("No players reached law milestones")

    fig = create_base_figure(
        title="Estimated Turns to Law Milestones",
        x_title="Player",
        y_title="Estimated Turn Number",
        height=450,
    )

    # Add trace for 4 laws milestone
    if "estimated_turn_to_4_laws" in df_filtered.columns:
        fig.add_trace(
            go.Bar(
                name="4 Laws",
                x=df_filtered["player_name"],
                y=df_filtered["estimated_turn_to_4_laws"],
                text=df_filtered["estimated_turn_to_4_laws"].round(0).astype("Int64"),
                textposition="auto",
                marker_color=Config.PRIMARY_COLORS[0],
            )
        )

    # Add trace for 7 laws milestone
    if "estimated_turn_to_7_laws" in df_filtered.columns:
        fig.add_trace(
            go.Bar(
                name="7 Laws",
                x=df_filtered["player_name"],
                y=df_filtered["estimated_turn_to_7_laws"],
                text=df_filtered["estimated_turn_to_7_laws"].round(0).astype("Int64"),
                textposition="auto",
                marker_color=Config.PRIMARY_COLORS[1],
            )
        )

    fig.update_layout(barmode="group")
    fig.update_xaxes(tickangle=-45)

    return fig


def create_law_progression_comparison_chart(df: pd.DataFrame) -> go.Figure:
    """Create a box plot comparing law progression across players.

    Args:
        df: DataFrame with columns: player_name, avg_laws_per_game, avg_turn_to_4_laws, avg_turn_to_7_laws

    Returns:
        Plotly figure with box plot
    """
    if df.empty:
        return create_empty_chart_placeholder("No law progression data available")

    # Only include players with multiple matches
    df_filtered = df[df["matches_played"] >= 2].copy()

    if df_filtered.empty:
        return create_empty_chart_placeholder(
            "Not enough data for comparison (need players with 2+ matches)"
        )

    fig = make_subplots(
        rows=1,
        cols=3,
        subplot_titles=(
            "Average Laws per Game",
            "Avg Turn to 4 Laws",
            "Avg Turn to 7 Laws",
        ),
        horizontal_spacing=0.12,
    )
    fig = apply_dark_theme(fig)

    # Average laws per game
    fig.add_trace(
        go.Box(
            y=df_filtered["avg_laws_per_game"],
            name="Avg Laws",
            marker_color=Config.PRIMARY_COLORS[0],
            showlegend=False,
        ),
        row=1,
        col=1,
    )

    # Average turn to 4 laws
    valid_4_laws = df_filtered[df_filtered["avg_turn_to_4_laws"].notna()]
    if not valid_4_laws.empty:
        fig.add_trace(
            go.Box(
                y=valid_4_laws["avg_turn_to_4_laws"],
                name="4 Laws",
                marker_color=Config.PRIMARY_COLORS[1],
                showlegend=False,
            ),
            row=1,
            col=2,
        )

    # Average turn to 7 laws
    valid_7_laws = df_filtered[df_filtered["avg_turn_to_7_laws"].notna()]
    if not valid_7_laws.empty:
        fig.add_trace(
            go.Box(
                y=valid_7_laws["avg_turn_to_7_laws"],
                name="7 Laws",
                marker_color=Config.PRIMARY_COLORS[2],
                showlegend=False,
            ),
            row=1,
            col=3,
        )

    fig.update_layout(title_text="Law Progression Statistics Comparison", height=400)

    fig.update_yaxes(title_text="Laws", row=1, col=1)
    fig.update_yaxes(title_text="Turns", row=1, col=2)
    fig.update_yaxes(title_text="Turns", row=1, col=3)

    return fig


def create_player_law_performance_chart(df: pd.DataFrame) -> go.Figure:
    """Create a scatter plot showing law performance metrics.

    Args:
        df: DataFrame with player law progression statistics

    Returns:
        Plotly figure with scatter plot
    """
    if df.empty:
        return create_empty_chart_placeholder("No law progression data available")

    # Filter to players with milestone data
    df_filtered = df[
        (df["avg_turn_to_4_laws"].notna()) & (df["matches_played"] >= 2)
    ].copy()

    if df_filtered.empty:
        return create_empty_chart_placeholder(
            "Not enough data for performance analysis"
        )

    fig = create_base_figure(
        title="Law Progression Performance: Speed vs Quantity",
        x_title="Average Laws per Game",
        y_title="Average Turns per Law (lower is faster)",
        height=500,
    )

    # Create bubble chart with size based on number of matches
    fig.add_trace(
        go.Scatter(
            x=df_filtered["avg_laws_per_game"],
            y=df_filtered["avg_turns_per_law"],
            mode="markers+text",
            text=df_filtered["player_name"],
            textposition="top center",
            marker=dict(
                size=df_filtered["matches_played"] * 3,  # Scale by matches played
                color=df_filtered["avg_laws_per_game"],
                colorscale="Viridis",
                showscale=True,
                colorbar=dict(title="Avg Laws"),
                line=dict(width=1, color="white"),
            ),
            hovertemplate=(
                "<b>%{text}</b><br>"
                + "Avg Laws: %{x:.1f}<br>"
                + "Avg Turns/Law: %{y:.1f}<br>"
                + "<extra></extra>"
            ),
        )
    )

    # Add annotation explaining bubble size
    fig.add_annotation(
        text="Bubble size = matches played",
        xref="paper",
        yref="paper",
        x=1.0,
        y=-0.15,
        showarrow=False,
        font=dict(size=10, color="gray"),
    )

    return fig


def create_nation_win_percentage_chart(df: pd.DataFrame) -> go.Figure:
    """Create a horizontal bar chart showing nation win rates.

    Args:
        df: DataFrame with nation, wins, total_matches, win_percentage columns

    Returns:
        Plotly figure with horizontal bar chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No nation data available")

    # Sort by win percentage descending
    df_sorted = df.sort_values("win_percentage", ascending=True)

    fig = create_base_figure(
        title="Nation Win Rate",
        x_title="Win Rate (%)",
        y_title="Nation",
        show_legend=False,
    )

    # Use nation colors from nation_colors.py
    colors = [get_nation_color(nation) for nation in df_sorted["nation"]]

    # Create hover text with detailed stats
    hover_text = [
        f"<b>{row['nation']}</b><br>"
        f"Win Rate: {row['win_percentage']:.1f}%<br>"
        f"Wins: {row['wins']}<br>"
        f"Games Played: {row['total_matches']}"
        for _, row in df_sorted.iterrows()
    ]

    fig.add_trace(
        go.Bar(
            x=df_sorted["win_percentage"],
            y=df_sorted["nation"],
            orientation="h",
            marker=dict(color=colors),
            text=[f"{pct:.1f}%" for pct in df_sorted["win_percentage"]],
            textposition="auto",
            hovertemplate="%{hovertext}<extra></extra>",
            hovertext=hover_text,
        )
    )

    fig.update_layout(
        yaxis={"categoryorder": "total ascending"},
        xaxis={"range": [0, 100]},
    )

    return fig


def create_nation_loss_percentage_chart(df: pd.DataFrame) -> go.Figure:
    """Create a horizontal bar chart showing nation loss rates.

    Args:
        df: DataFrame with nation, losses, total_matches, loss_percentage columns

    Returns:
        Plotly figure with horizontal bar chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No nation data available")

    # Sort by loss percentage ascending (so lowest loss rate is at top)
    df_sorted = df.sort_values("loss_percentage", ascending=False)

    fig = create_base_figure(
        title="Nation Loss Rate",
        x_title="Loss Rate (%)",
        y_title="Nation",
        show_legend=False,
    )

    # Use nation colors from nation_colors.py
    colors = [get_nation_color(nation) for nation in df_sorted["nation"]]

    # Create hover text with detailed stats
    hover_text = [
        f"<b>{row['nation']}</b><br>"
        f"Loss Rate: {row['loss_percentage']:.1f}%<br>"
        f"Losses: {row['losses']}<br>"
        f"Games Played: {row['total_matches']}"
        for _, row in df_sorted.iterrows()
    ]

    fig.add_trace(
        go.Bar(
            x=df_sorted["loss_percentage"],
            y=df_sorted["nation"],
            orientation="h",
            marker=dict(color=colors),
            text=[f"{pct:.1f}%" for pct in df_sorted["loss_percentage"]],
            textposition="auto",
            hovertemplate="%{hovertext}<extra></extra>",
            hovertext=hover_text,
        )
    )

    fig.update_layout(
        yaxis={"categoryorder": "total ascending"},
        xaxis={"range": [0, 100]},
    )

    return fig


def create_nation_popularity_chart(df: pd.DataFrame) -> go.Figure:
    """Create a horizontal bar chart showing nation popularity (matches played).

    Args:
        df: DataFrame with nation, total_matches columns

    Returns:
        Plotly figure with horizontal bar chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No nation data available")

    # Sort by total matches descending
    df_sorted = df.sort_values("total_matches", ascending=True)

    fig = create_base_figure(
        title="Nation Popularity",
        x_title="Games Played",
        y_title="Nation",
        show_legend=False,
    )

    # Use nation colors from nation_colors.py
    colors = [get_nation_color(nation) for nation in df_sorted["nation"]]

    # Create hover text with detailed stats
    hover_text = [
        f"<b>{row['nation']}</b><br>" f"Games Played: {row['total_matches']}"
        for _, row in df_sorted.iterrows()
    ]

    fig.add_trace(
        go.Bar(
            x=df_sorted["total_matches"],
            y=df_sorted["nation"],
            orientation="h",
            marker=dict(color=colors),
            text=df_sorted["total_matches"],
            textposition="auto",
            hovertemplate="%{hovertext}<extra></extra>",
            hovertext=hover_text,
        )
    )

    fig.update_layout(yaxis={"categoryorder": "total ascending"})

    return fig


def create_map_breakdown_sunburst_chart(df: pd.DataFrame) -> go.Figure:
    """Create a stacked bar chart showing map breakdown by size, class, and aspect ratio.

    Args:
        df: DataFrame with map_class, map_aspect_ratio, map_size, count columns

    Returns:
        Plotly figure with stacked bar chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No map data available")

    # Create a stacked bar chart with:
    # X-axis: map_size (Duel, Tiny)
    # Y-axis: count
    # Stacks: combination of map_class and aspect_ratio

    fig = create_base_figure(title="Map Breakdown", show_legend=True)

    # Create a combined label for each unique combination
    df["combination"] = df["map_class"] + " - " + df["map_aspect_ratio"]

    # Get unique combinations to create consistent colors
    combinations = df["combination"].unique()

    # Color palette - using different shades of green and blue
    color_map = {
        "Continent - Square": "#2E7D32",
        "Continent - Wide": "#43A047",
        "Continent - Ultrawide": "#66BB6A",
        "Continent - Dynamic": "#81C784",
        "Coastal Rain Basin - Square": "#1565C0",
        "Coastal Rain Basin - Wide": "#1976D2",
        "Coastal Rain Basin - Ultrawide": "#42A5F5",
        "Coastal Rain Basin - Dynamic": "#64B5F6",
        "Inland Sea - Square": "#6A1B9A",
        "Inland Sea - Wide": "#8E24AA",
        "Inland Sea - Ultrawide": "#AB47BC",
        "Inland Sea - Dynamic": "#BA68C8",
    }

    # Group by size and combination for stacking
    for combination in sorted(combinations):
        subset = df[df["combination"] == combination]

        # Get counts for each size
        size_counts = {}
        for size in ["Duel", "Tiny"]:
            size_data = subset[subset["map_size"] == size]
            size_counts[size] = (
                int(size_data["count"].sum()) if not size_data.empty else 0
            )

        fig.add_trace(
            go.Bar(
                name=combination,
                x=list(size_counts.keys()),
                y=list(size_counts.values()),
                marker_color=color_map.get(combination, "#808080"),
                hovertemplate="<b>%{fullData.name}</b><br>Count: %{y}<extra></extra>",
            )
        )

    fig.update_layout(
        barmode="stack",
        xaxis_title="Map Size",
        yaxis_title="Number of Maps",
        legend=dict(
            title="Map Type",
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
        ),
        margin=dict(t=40, l=50, r=150, b=50),
    )

    return fig


def create_map_breakdown_pie_charts(df: pd.DataFrame) -> go.Figure:
    """Create two pie charts showing map breakdown by size (Duel and Tiny).

    Args:
        df: DataFrame with map_class, map_aspect_ratio, map_size, count columns

    Returns:
        Plotly figure with two pie charts side by side
    """
    if df.empty:
        return create_empty_chart_placeholder("No map data available")

    # Create subplots for two pie charts
    from plotly.subplots import make_subplots

    # Create a combined label for each unique combination
    df["combination"] = df["map_class"] + " - " + df["map_aspect_ratio"]

    # Color palette - consistent with stacked bar
    color_map = {
        "Continent - Square": "#2E7D32",
        "Continent - Wide": "#43A047",
        "Continent - Ultrawide": "#66BB6A",
        "Continent - Dynamic": "#81C784",
        "Coastal Rain Basin - Square": "#1565C0",
        "Coastal Rain Basin - Wide": "#1976D2",
        "Coastal Rain Basin - Ultrawide": "#42A5F5",
        "Coastal Rain Basin - Dynamic": "#64B5F6",
        "Inland Sea - Square": "#6A1B9A",
        "Inland Sea - Wide": "#8E24AA",
        "Inland Sea - Ultrawide": "#AB47BC",
        "Inland Sea - Dynamic": "#BA68C8",
    }

    # Create subplots with 1 row, 2 columns
    fig = make_subplots(
        rows=1,
        cols=2,
        specs=[[{"type": "pie"}, {"type": "pie"}]],
        subplot_titles=("Duel Maps", "Tiny Maps"),
    )
    fig = apply_dark_theme(fig)

    # Duel maps (left pie chart)
    duel_df = df[df["map_size"] == "Duel"]
    if not duel_df.empty:
        colors = [color_map.get(comb, "#808080") for comb in duel_df["combination"]]
        fig.add_trace(
            go.Pie(
                labels=duel_df["combination"],
                values=duel_df["count"],
                marker=dict(colors=colors),
                textposition="inside",
                textinfo="label+value",
                hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
            ),
            row=1,
            col=1,
        )

    # Tiny maps (right pie chart)
    tiny_df = df[df["map_size"] == "Tiny"]
    if not tiny_df.empty:
        colors = [color_map.get(comb, "#808080") for comb in tiny_df["combination"]]
        fig.add_trace(
            go.Pie(
                labels=tiny_df["combination"],
                values=tiny_df["count"],
                marker=dict(colors=colors),
                textposition="inside",
                textinfo="label+value",
                hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
            ),
            row=1,
            col=2,
        )

    fig.update_layout(
        title_text="Map Breakdown by Size",
        showlegend=False,
        margin=dict(t=60, l=20, r=20, b=20),
    )

    return fig


def create_unit_popularity_sunburst_chart(df: pd.DataFrame) -> go.Figure:
    """Create a sunburst chart showing military unit popularity by role and type.

    Args:
        df: DataFrame with category, role, unit_type, total_count columns

    Returns:
        Plotly figure with sunburst chart showing only military units
    """
    if df.empty:
        return create_empty_chart_placeholder("No unit data available")

    # Filter to only military units
    military_df = df[df["category"] == "military"].copy()

    if military_df.empty:
        return create_empty_chart_placeholder("No military unit data available")

    # Build the sunburst data structure
    # Calculate total for root
    total_units = int(military_df["total_count"].sum())

    # Level 0: Root with unit count
    labels = [f"{total_units} units"]
    parents = [""]
    values = [total_units]

    # Define base colors for each military role
    role_colors = {
        "cavalry": "#8B4513",  # Brown - horses/chariots
        "infantry": "#DC143C",  # Crimson - foot soldiers
        "ranged": "#4169E1",  # Royal Blue - archers
        "siege": "#696969",  # Dim Gray - siege engines
        "naval": "#1E90FF",  # Dodger Blue - water
    }

    # Level 1: Add roles (cavalry, infantry, ranged, siege, naval)
    role_totals = military_df.groupby("role")["total_count"].sum().to_dict()
    roles = sorted(role_totals.keys())
    colors = [CHART_THEME["paper_bgcolor"]]  # Root color (matches background)

    for role in roles:
        labels.append(role)
        parents.append(f"{total_units} units")
        values.append(role_totals[role])
        colors.append(
            role_colors.get(role, "#808080")
        )  # Default to gray if role not found

    # Level 2: Add individual unit types with shaded colors
    # Group units by role to calculate shades
    for role in roles:
        role_units = military_df[military_df["role"] == role].copy()
        num_units = len(role_units)
        base_color = role_colors.get(role, "#808080")

        # Create shades from light to dark (or use base color if only one unit)
        if num_units == 1:
            shades = [base_color]
        else:
            # Parse the hex color to RGB
            r = int(base_color[1:3], 16)
            g = int(base_color[3:5], 16)
            b = int(base_color[5:7], 16)

            shades = []
            for i in range(num_units):
                # Create shades by blending with white (lighter) or black (darker)
                # Use a range from 70% lightness to 100% darkness
                factor = 0.7 + (0.3 * i / max(num_units - 1, 1))
                shade_r = int(r * factor)
                shade_g = int(g * factor)
                shade_b = int(b * factor)
                shades.append(f"#{shade_r:02x}{shade_g:02x}{shade_b:02x}")

        for idx, (_, row) in enumerate(role_units.iterrows()):
            # Remove "UNIT_" prefix and convert to title case
            unit_name = row["unit_type"].replace("UNIT_", "").replace("_", " ").title()
            labels.append(unit_name)
            parents.append(row["role"])
            values.append(row["total_count"])
            colors.append(shades[idx])

    # Use labels directly as display text since we no longer have naming conflicts
    custom_text = labels

    fig = go.Figure(
        go.Sunburst(
            labels=labels,
            parents=parents,
            values=values,
            text=custom_text,
            branchvalues="total",
            textfont=dict(size=10),
            marker=dict(colors=colors, line=dict(color="white", width=2)),
            texttemplate="%{text}",  # Only show the custom text, not both label and text
            hovertemplate="<b>%{text}</b><br>Count: %{value}<br>%{percentParent:.1%} of parent<extra></extra>",
        )
    )

    fig.update_layout(
        margin=dict(t=0, l=0, r=0, b=0),
        height=400,
        paper_bgcolor=CHART_THEME["paper_bgcolor"],
        font=dict(color=CHART_THEME["font_color"]),
    )

    return fig


def create_law_milestone_comparison_chart(df: pd.DataFrame) -> go.Figure:
    """Create a grouped bar chart comparing law milestone timing between players.

    Shows when each player in a match reached the 4-law and 7-law milestones.
    Useful for head-to-head comparison in a single match.

    Args:
        df: DataFrame with columns: player_name, turn_to_4_laws, turn_to_7_laws
            (typically from get_law_progression_by_match() for one match)

    Returns:
        Plotly figure with grouped bar chart

    Example:
        >>> queries = get_queries()
        >>> df = queries.get_law_progression_by_match(match_id=10)
        >>> fig = create_law_milestone_comparison_chart(df)
    """
    if df.empty:
        return create_empty_chart_placeholder("No law progression data for this match")

    fig = create_base_figure(
        title="Law Milestone Timing Comparison",
        x_title="Player",
        y_title="Turn Number",
        height=400,
    )

    # Add trace for 4 laws milestone
    fig.add_trace(
        go.Bar(
            name="4 Laws",
            x=df["player_name"],
            y=df["turn_to_4_laws"],
            marker_color=Config.PRIMARY_COLORS[0],
            text=pd.to_numeric(df["turn_to_4_laws"], errors="coerce")
            .round(0)
            .astype("Int64"),  # Int64 handles NA
            textposition="auto",
            hovertemplate="<b>%{x}</b><br>4th Law: Turn %{y}<extra></extra>",
        )
    )

    # Add trace for 7 laws milestone
    fig.add_trace(
        go.Bar(
            name="7 Laws",
            x=df["player_name"],
            y=df["turn_to_7_laws"],
            marker_color=Config.PRIMARY_COLORS[1],
            text=pd.to_numeric(df["turn_to_7_laws"], errors="coerce")
            .round(0)
            .astype("Int64"),
            textposition="auto",
            hovertemplate="<b>%{x}</b><br>7th Law: Turn %{y}<extra></extra>",
        )
    )

    # Group bars side-by-side
    fig.update_layout(barmode="group")

    # Add annotation explaining NULL values
    fig.add_annotation(
        text="Missing bars indicate milestone not reached",
        xref="paper",
        yref="paper",
        x=0.5,
        y=-0.15,
        showarrow=False,
        font=dict(size=10, color="gray"),
    )

    return fig


def create_law_race_timeline_chart(df: pd.DataFrame) -> go.Figure:
    """Create a horizontal timeline showing law milestone progression.

    Displays milestones as markers on a timeline, making it easy to see
    who reached each milestone first and the gap between players.

    Args:
        df: DataFrame with columns: player_name, turn_to_4_laws, turn_to_7_laws

    Returns:
        Plotly figure with scatter plot timeline
    """
    if df.empty:
        return create_empty_chart_placeholder("No law progression data available")

    fig = create_base_figure(
        title="Law Milestone Race Timeline",
        x_title="Turn Number",
        y_title="Player",
        height=300,
    )

    # Create Y positions for each player (0, 1, 2, ...)
    player_positions = {name: i for i, name in enumerate(df["player_name"])}

    # For each player, add markers for their milestones
    for _, row in df.iterrows():
        player_name = row["player_name"]
        y_pos = player_positions[player_name]

        # Prepare milestone data (only include milestones that were reached)
        milestones = []

        if pd.notna(row["turn_to_4_laws"]):
            milestones.append(
                {
                    "turn": row["turn_to_4_laws"],
                    "label": "4 laws",
                    "symbol": "circle",
                }
            )

        if pd.notna(row["turn_to_7_laws"]):
            milestones.append(
                {
                    "turn": row["turn_to_7_laws"],
                    "label": "7 laws",
                    "symbol": "star",
                }
            )

        # Add a line connecting the milestones for this player
        if milestones:
            turns = [m["turn"] for m in milestones]

            fig.add_trace(
                go.Scatter(
                    x=turns,
                    y=[y_pos] * len(turns),
                    mode="lines+markers+text",
                    name=player_name,
                    line=dict(
                        color=Config.PRIMARY_COLORS[y_pos % len(Config.PRIMARY_COLORS)],
                        width=2,
                    ),
                    marker=dict(
                        size=12,
                        symbol=[m["symbol"] for m in milestones],
                    ),
                    text=[f"{m['label']}<br>Turn {int(m['turn'])}" for m in milestones],
                    textposition="top center",
                    hovertemplate="<b>%{fullData.name}</b><br>%{text}<extra></extra>",
                )
            )

    # Update Y-axis to show player names
    fig.update_yaxes(
        tickmode="array",
        tickvals=list(player_positions.values()),
        ticktext=list(player_positions.keys()),
    )

    # Add vertical grid lines for easier reading
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="rgba(128,128,128,0.2)")

    return fig


def create_law_milestone_distribution_chart(df: pd.DataFrame) -> go.Figure:
    """Create a box plot showing distribution of milestone timing across all matches.

    Box plot displays:
    - Median (middle line)
    - Quartiles (box boundaries)
    - Min/max (whiskers)
    - Outliers (individual points)

    Args:
        df: DataFrame with turn_to_4_laws and turn_to_7_laws columns
            (typically from get_law_progression_by_match() for ALL matches)

    Returns:
        Plotly figure with box plots
    """
    if df.empty:
        return create_empty_chart_placeholder("No law progression data available")

    # Filter out players who didn't reach milestones
    df_4_laws = df[df["turn_to_4_laws"].notna()]
    df_7_laws = df[df["turn_to_7_laws"].notna()]

    if df_4_laws.empty and df_7_laws.empty:
        return create_empty_chart_placeholder(
            "No players reached law milestones in the dataset"
        )

    fig = create_base_figure(
        title="",
        x_title="Milestone",
        y_title="Turn Number",
        height=450,
    )

    # Add box plot for 4 laws
    if not df_4_laws.empty:
        fig.add_trace(
            go.Box(
                y=df_4_laws["turn_to_4_laws"],
                name="4 Laws",
                marker_color=Config.PRIMARY_COLORS[0],
                boxmean="sd",  # Show mean and standard deviation
                hovertemplate=(
                    "<b>4 Laws Milestone</b><br>" "Turn: %{y}<br>" "<extra></extra>"
                ),
            )
        )

    # Add box plot for 7 laws
    if not df_7_laws.empty:
        fig.add_trace(
            go.Box(
                y=df_7_laws["turn_to_7_laws"],
                name="7 Laws",
                marker_color=Config.PRIMARY_COLORS[1],
                boxmean="sd",
                hovertemplate=(
                    "<b>7 Laws Milestone</b><br>" "Turn: %{y}<br>" "<extra></extra>"
                ),
            )
        )

    return fig


def create_law_progression_heatmap(df: pd.DataFrame) -> go.Figure:
    """Create a heatmap showing player law progression performance.

    Color coding:
    - Green: Reached 7 laws (strong performance)
    - Yellow: Reached 4 laws (moderate performance)
    - Red: < 4 laws (weak performance)
    - Gray: No data

    Args:
        df: DataFrame with player_name, match_id, turn_to_4_laws, turn_to_7_laws

    Returns:
        Plotly figure with heatmap
    """
    if df.empty:
        return create_empty_chart_placeholder("No law progression data available")

    # Create a performance score:
    # 3 = reached 7 laws
    # 2 = reached 4 laws (but not 7)
    # 1 = < 4 laws
    # 0 = no data (shouldn't happen in valid data)
    def calculate_performance_score(row: pd.Series) -> int:
        """Calculate performance score based on milestones reached."""
        if pd.notna(row["turn_to_7_laws"]):
            return 3  # Reached 7 laws
        elif pd.notna(row["turn_to_4_laws"]):
            return 2  # Reached 4 laws
        else:
            return 1  # Didn't reach 4 laws

    df["performance_score"] = df.apply(calculate_performance_score, axis=1)

    # Pivot table: rows = players, columns = matches, values = performance score
    pivot_data = df.pivot_table(
        index="player_name",
        columns="match_id",
        values="performance_score",
        aggfunc="first",  # One entry per player per match
    )

    if pivot_data.empty:
        return create_empty_chart_placeholder("Insufficient data for heatmap")

    # Create custom colorscale
    # 1 = red, 2 = yellow, 3 = green
    colorscale = [
        [0.0, "#EF5350"],  # Red (poor)
        [0.33, "#EF5350"],  # Red
        [0.34, "#FFA726"],  # Yellow (moderate)
        [0.66, "#FFA726"],  # Yellow
        [0.67, "#66BB6A"],  # Green (excellent)
        [1.0, "#66BB6A"],  # Green
    ]

    fig = create_base_figure(
        title="Player Law Progression Performance (All Matches)",
        show_legend=False,
        height=400 + (len(pivot_data) * 20),  # Scale height with player count
    )

    # Create hover text
    hover_text = []
    for player in pivot_data.index:
        row_text = []
        for match_id in pivot_data.columns:
            score = pivot_data.loc[player, match_id]
            if pd.notna(score):
                if score == 3:
                    text = f"Match {match_id}<br>{player}<br>Reached 7 laws"
                elif score == 2:
                    text = f"Match {match_id}<br>{player}<br>Reached 4 laws"
                else:
                    text = f"Match {match_id}<br>{player}<br>< 4 laws"
            else:
                text = f"Match {match_id}<br>{player}<br>No data"
            row_text.append(text)
        hover_text.append(row_text)

    fig.add_trace(
        go.Heatmap(
            z=pivot_data.values,
            x=[f"Match {mid}" for mid in pivot_data.columns],
            y=pivot_data.index,
            colorscale=colorscale,
            hovertext=hover_text,
            hoverinfo="text",
            showscale=True,
            colorbar=dict(
                title="Performance",
                tickvals=[1, 2, 3],
                ticktext=["< 4 laws", "4 laws", "7 laws"],
            ),
        )
    )

    fig.update_xaxes(title="Match", side="bottom")
    fig.update_yaxes(title="Player")

    return fig


def create_law_efficiency_scatter(df: pd.DataFrame) -> go.Figure:
    """Create a scatter plot analyzing law progression efficiency.

    X-axis: Turn to reach 4 laws
    Y-axis: Turn to reach 7 laws

    Shows one point per match-player instance. Players in the lower-left corner
    are most efficient (reached milestones quickly). Players in the upper-right
    are slower. Color-coded by participant.

    Args:
        df: DataFrame with player_name, civilization, match_id, turn_to_4_laws, turn_to_7_laws

    Returns:
        Plotly figure with scatter plot
    """
    if df.empty:
        return create_empty_chart_placeholder("No law progression data available")

    # Filter to only players who reached BOTH milestones
    df_complete = df[df["turn_to_4_laws"].notna() & df["turn_to_7_laws"].notna()].copy()

    if df_complete.empty:
        return create_empty_chart_placeholder(
            "No players reached both 4 and 7 law milestones"
        )

    fig = create_base_figure(
        title="",
        x_title="Turn to Reach 4 Laws (lower = faster)",
        y_title="Turn to Reach 7 Laws (lower = faster)",
        height=500,
        show_legend=False,
    )

    # Calculate time between milestones
    df_complete["time_between"] = (
        df_complete["turn_to_7_laws"] - df_complete["turn_to_4_laws"]
    )

    # Color by participant (not civilization)
    unique_participants = df_complete["player_name"].unique()
    participant_colors = {
        name: Config.PRIMARY_COLORS[i % len(Config.PRIMARY_COLORS)]
        for i, name in enumerate(unique_participants)
    }

    # Group by participant - all their games get the same color
    for participant in unique_participants:
        participant_data = df_complete[df_complete["player_name"] == participant]

        fig.add_trace(
            go.Scatter(
                x=participant_data["turn_to_4_laws"],
                y=participant_data["turn_to_7_laws"],
                mode="markers+text",
                name=participant,
                marker=dict(
                    size=12,
                    color=participant_colors[participant],
                    line=dict(width=1, color="white"),
                ),
                text=participant_data["player_name"],
                textposition="top center",
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Civilization: %{customdata[0]}<br>"
                    "Match ID: %{customdata[1]}<br>"
                    "4 Laws: Turn %{x}<br>"
                    "7 Laws: Turn %{y}<br>"
                    "<extra></extra>"
                ),
                customdata=participant_data[["civilization", "match_id"]].values,
            )
        )

    # Add diagonal line showing typical progression ratio
    if not df_complete.empty:
        x_range = [
            df_complete["turn_to_4_laws"].min(),
            df_complete["turn_to_4_laws"].max(),
        ]
        # Typical ratio: if 4 laws at turn X, 7 laws around turn 1.5*X
        y_trend = [x * 1.5 for x in x_range]

        fig.add_trace(
            go.Scatter(
                x=x_range,
                y=y_trend,
                mode="lines",
                name="Typical Pace",
                line=dict(dash="dash", color="gray", width=1),
                showlegend=True,
                hoverinfo="skip",
            )
        )

    return fig


def create_cumulative_law_count_chart(
    df: pd.DataFrame,
    total_turns: Optional[int] = None,
    player_colors: Optional[Dict[str, str]] = None,
) -> go.Figure:
    """Create a line chart showing cumulative law count over time.

    Displays a "racing" view of law progression, making it easy to see
    who was ahead at any point in the match.

    Args:
        df: DataFrame with columns: player_name, turn_number, cumulative_laws
            (from get_cumulative_law_count_by_turn())
        total_turns: Optional total turns in the match to extend lines to the end
        player_colors: Optional dict mapping player names to hex colors

    Returns:
        Plotly figure with line chart
    """
    if df.empty:
        return create_empty_chart_placeholder(
            "No law progression data available for this match"
        )

    fig = create_base_figure(
        title="",
        x_title="Turn Number",
        y_title="Laws Adopted",
        height=400,
    )

    # Add a line for each player
    players = df["player_name"].unique()

    for i, player in enumerate(players):
        player_data = df[df["player_name"] == player]

        # Use nation-based color if provided, otherwise fall back to default
        if player_colors and player in player_colors:
            color = player_colors[player]
        else:
            color = Config.PRIMARY_COLORS[i % len(Config.PRIMARY_COLORS)]

        # Add a point at turn 0 with 0 laws for cleaner visualization
        turns = [0] + player_data["turn_number"].tolist()
        laws = [0] + player_data["cumulative_laws"].tolist()

        # Build law list for hover (empty string for turn 0)
        law_lists = [""] + player_data["law_list"].fillna("").tolist()
        new_law_lists = [""] + player_data["new_laws"].fillna("").tolist()

        # Create custom hover text - only show new laws added this turn
        hover_texts = []
        for turn, law_count, law_list, new_laws in zip(
            turns, laws, law_lists, new_law_lists
        ):
            if law_count == 0:
                hover_texts.append(f"<b>{player}</b><br>Turn {turn}: 0 laws")
            else:
                # Only show new laws added this turn
                if new_laws:
                    new_laws_array = [
                        law.strip()
                        .replace('"', "")
                        .replace("LAW_", "")
                        .replace("_", " ")
                        .title()
                        for law in new_laws.split(",")
                    ]
                    new_laws_array.sort()

                    hover_parts = [
                        f"<b>{player}</b><br>Turn {turn}: {law_count} laws total"
                    ]
                    hover_parts.append("<br><br>")
                    hover_parts.append(
                        "<br>".join([f"• {law}" for law in new_laws_array])
                    )
                    hover_texts.append("".join(hover_parts))
                else:
                    # No new laws this turn
                    hover_texts.append(
                        f"<b>{player}</b><br>Turn {turn}: {law_count} laws total"
                    )

        # Extend line to match end if total_turns provided
        if total_turns and turns[-1] < total_turns:
            turns.append(total_turns)
            laws.append(laws[-1])  # Keep final law count
            hover_texts.append(hover_texts[-1])  # Reuse last hover text

        # Assign last trace to yaxis2 to make right-side labels visible
        yaxis_ref = "y2" if i == len(players) - 1 else "y"

        fig.add_trace(
            go.Scatter(
                x=turns,
                y=laws,
                mode="lines+markers",
                name=player,
                line=dict(
                    color=color,
                    width=4,
                ),
                marker=dict(size=10),
                hoveron="points",  # Only trigger hover on marker points, not lines
                hovertemplate="%{hovertext}<extra></extra>",
                hovertext=hover_texts,
                yaxis=yaxis_ref,
            )
        )

    # Add reference lines for milestones
    fig.add_hline(
        y=4,
        line_dash="dash",
        line_color="rgba(128,128,128,0.5)",
        annotation_text="4 Laws",
        annotation_position="right",
    )

    fig.add_hline(
        y=7,
        line_dash="dash",
        line_color="rgba(128,128,128,0.5)",
        annotation_text="7 Laws",
        annotation_position="right",
    )

    # Calculate the maximum law count to set consistent y-axis range
    max_laws = int(df["cumulative_laws"].max()) if not df.empty else 7
    y_range = [0, max_laws + 1]

    # Set Y-axis with labels on both left and right sides
    # Also increase hoverdistance to make hover targets easier to hit
    fig.update_layout(
        yaxis=dict(
            range=y_range,
            dtick=1,
            showgrid=True,
            ticks="outside",
            tickmode="linear",
        ),
        yaxis2=dict(
            overlaying="y",
            side="right",
            range=y_range,
            dtick=1,
            showticklabels=True,
            ticks="outside",
            showgrid=False,
            tickmode="linear",
        ),
        hovermode="closest",  # Explicitly set hover mode
        hoverdistance=100,  # Increase hover detection distance (default is 20)
    )

    return fig


def create_cumulative_tech_count_chart(
    df: pd.DataFrame,
    total_turns: Optional[int] = None,
    player_colors: Optional[Dict[str, str]] = None,
) -> go.Figure:
    """Create a line chart showing cumulative technology count over time.

    Displays a "racing" view of technology progression, making it easy to see
    who was ahead at any point in the match.

    Args:
        df: DataFrame with columns: player_name, turn_number, cumulative_techs
            (from get_tech_count_by_turn())
        total_turns: Optional total turns in the match to extend lines to the end
        player_colors: Optional dict mapping player names to hex colors

    Returns:
        Plotly figure with line chart
    """
    if df.empty:
        return create_empty_chart_placeholder(
            "No technology progression data available for this match"
        )

    fig = create_base_figure(
        title="",
        x_title="Turn Number",
        y_title="Technologies Discovered",
        height=400,
    )

    # Add a line for each player
    players = df["player_name"].unique()

    for i, player in enumerate(players):
        player_data = df[df["player_name"] == player]

        # Use nation-based color if provided, otherwise fall back to default
        if player_colors and player in player_colors:
            color = player_colors[player]
        else:
            color = Config.PRIMARY_COLORS[i % len(Config.PRIMARY_COLORS)]

        # Add a point at turn 0 with 0 techs for cleaner visualization
        turns = [0] + player_data["turn_number"].tolist()
        techs = [0] + player_data["cumulative_techs"].tolist()

        # Build tech list for hover (empty string for turn 0)
        tech_lists = [""] + player_data["tech_list"].fillna("").tolist()
        new_tech_lists = [""] + player_data["new_techs"].fillna("").tolist()

        # Create custom hover text - only show new techs added this turn
        hover_texts = []
        for turn, tech_count, tech_list, new_techs in zip(
            turns, techs, tech_lists, new_tech_lists
        ):
            if tech_count == 0:
                hover_texts.append(f"<b>{player}</b><br>Turn {turn}: 0 techs")
            else:
                # Only show new techs added this turn
                if new_techs:
                    new_techs_array = [
                        tech.strip()
                        .replace('"', "")
                        .replace("TECH_", "")
                        .replace("_", " ")
                        .title()
                        for tech in new_techs.split(",")
                    ]
                    new_techs_array.sort()

                    hover_parts = [
                        f"<b>{player}</b><br>Turn {turn}: {tech_count} techs total"
                    ]
                    hover_parts.append("<br><br>")
                    hover_parts.append(
                        "<br>".join([f"• {tech}" for tech in new_techs_array])
                    )
                    hover_texts.append("".join(hover_parts))
                else:
                    # No new techs this turn
                    hover_texts.append(
                        f"<b>{player}</b><br>Turn {turn}: {tech_count} techs total"
                    )

        # Extend line to match end if total_turns provided
        if total_turns and turns[-1] < total_turns:
            turns.append(total_turns)
            techs.append(techs[-1])  # Keep final tech count
            hover_texts.append(hover_texts[-1])  # Reuse last hover text

        # Assign last trace to yaxis2 to make right-side labels visible
        yaxis_ref = "y2" if i == len(players) - 1 else "y"

        fig.add_trace(
            go.Scatter(
                x=turns,
                y=techs,
                mode="lines+markers",
                name=player,
                line=dict(
                    color=color,
                    width=4,
                ),
                marker=dict(size=10),
                hoveron="points",  # Only trigger hover on marker points, not lines
                hovertemplate="%{hovertext}<extra></extra>",
                hovertext=hover_texts,
                yaxis=yaxis_ref,
            )
        )

    # Calculate the maximum tech count to set consistent y-axis range
    max_techs = int(df["cumulative_techs"].max()) if not df.empty else 16
    y_range = [0, max_techs + 1]

    # Add horizontal dashed lines at every 5 tickets
    for y_value in range(5, max_techs + 1, 5):
        fig.add_hline(
            y=y_value,
            line_dash="dash",
            line_color="rgba(128, 128, 128, 0.5)",
            line_width=1.5,
        )

    # Set Y-axis with labels on both left and right sides
    # Also increase hoverdistance to make hover targets easier to hit
    fig.update_layout(
        yaxis=dict(
            range=y_range,
            dtick=5,
            showgrid=True,
            ticks="outside",
            tickmode="linear",
        ),
        yaxis2=dict(
            overlaying="y",
            side="right",
            range=y_range,
            dtick=5,
            showticklabels=True,
            ticks="outside",
            showgrid=False,
            tickmode="linear",
        ),
        hovermode="closest",  # Explicitly set hover mode
        hoverdistance=100,  # Increase hover detection distance (default is 20)
    )

    return fig


def create_tech_comparison_bar_chart(df: pd.DataFrame) -> go.Figure:
    """Create a grouped bar chart comparing tech acquisition turns between players.

    Displays side-by-side bars for each technology showing which turn each player
    acquired it. Makes it easy to see who got each tech first and by how much.

    Args:
        df: DataFrame with columns: player_name, turn_number, tech_name
            (from get_tech_timeline())

    Returns:
        Plotly figure with grouped bar chart
    """
    if df.empty:
        return create_empty_chart_placeholder(
            "No technology comparison data available for this match"
        )

    # Format tech names: remove TECH_ prefix, quotes, replace underscores, title case
    df = df.copy()
    df["tech_display"] = (
        df["tech_name"]
        .str.replace('"', "", regex=False)  # Remove quotes from JSON extraction
        .str.replace("TECH_", "", regex=False)
        .str.replace("_", " ")
        .str.title()
    )

    # Get unique technologies sorted alphabetically
    all_techs = sorted(df["tech_display"].unique())

    # Create base figure
    fig = create_base_figure(
        title="",
        x_title="Technology",
        y_title="Turn Number",
        height=500,
    )

    # Add a bar trace for each player
    players = df["player_name"].unique()

    for i, player in enumerate(players):
        player_data = df[df["player_name"] == player]

        # Create a mapping of tech to turn for this player
        tech_to_turn = dict(
            zip(player_data["tech_display"], player_data["turn_number"])
        )

        # Create lists aligned with all_techs
        turns = [tech_to_turn.get(tech, None) for tech in all_techs]

        # Create hover text
        hover_texts = [
            f"<b>{player}</b><br>{tech}<br>Turn {turn}" if turn is not None else ""
            for tech, turn in zip(all_techs, turns)
        ]

        fig.add_trace(
            go.Bar(
                x=all_techs,
                y=turns,
                name=player,
                marker_color=Config.PRIMARY_COLORS[i % len(Config.PRIMARY_COLORS)],
                hovertemplate="%{hovertext}<extra></extra>",
                hovertext=hover_texts,
            )
        )

    # Configure layout
    fig.update_layout(
        barmode="group",
        xaxis=dict(
            tickangle=-45,
            showgrid=False,
        ),
        yaxis=dict(
            showgrid=True,
            dtick=5,  # Show tick marks every 5 turns
        ),
        hovermode="closest",
    )

    return fig


def create_tech_completion_timeline_chart(
    df: pd.DataFrame,
    player_colors: Optional[Dict[str, str]] = None,
) -> go.Figure:
    """Create a timeline chart showing when each player completed each technology.

    Each technology gets its own row, with colored markers showing when
    each player discovered it. Makes it easy to compare timing between players.

    Args:
        df: DataFrame with columns: player_name, turn_number, tech_name
            (from get_tech_timeline())
        player_colors: Optional dict mapping player names to hex colors

    Returns:
        Plotly figure with technology completion timeline
    """
    if df.empty:
        return create_empty_chart_placeholder(
            "No technology timeline data available for this match"
        )

    # Format tech names: remove TECH_ prefix, quotes, replace underscores, title case
    df = df.copy()
    df["tech_display"] = (
        df["tech_name"]
        .str.replace('"', "", regex=False)  # Remove quotes from JSON extraction
        .str.replace("TECH_", "", regex=False)
        .str.replace("_", " ")
        .str.title()
    )

    # Get unique technologies, ordered by earliest discovery turn
    tech_order = (
        df.groupby("tech_display")["turn_number"].min().sort_values().index.tolist()
    )

    # Assign y-position (row) to each tech
    tech_y_positions = {tech: idx for idx, tech in enumerate(tech_order)}

    # Calculate figure height based on number of techs
    num_techs = len(tech_order)
    fig_height = max(400, num_techs * 60 + 100)  # 60px per tech for better spacing

    # Create base figure
    fig = create_base_figure(
        title="",
        x_title="Turn Number",
        y_title="",
        height=fig_height,
    )

    # Get unique players for color assignment
    players = df["player_name"].unique()

    # Add traces for each technology
    for tech in tech_order:
        y_pos = tech_y_positions[tech]
        tech_data = df[df["tech_display"] == tech].sort_values("turn_number")

        # If multiple players discovered this tech, draw a connecting line
        if len(tech_data) > 1:
            turns = tech_data["turn_number"].tolist()
            fig.add_trace(
                go.Scatter(
                    x=turns,
                    y=[y_pos] * len(turns),
                    mode="lines",
                    line=dict(
                        color="rgba(128, 128, 128, 0.3)",
                        width=2,
                    ),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

        # Add a marker for each discovery (sorted chronologically)
        for idx, row in tech_data.iterrows():
            player = row["player_name"]
            turn = row["turn_number"]

            # Get player color - use nation colors if provided
            if player_colors and player in player_colors:
                color = player_colors[player]
            else:
                player_idx = list(players).index(player)
                color = Config.PRIMARY_COLORS[player_idx % len(Config.PRIMARY_COLORS)]

            fig.add_trace(
                go.Scatter(
                    x=[turn],
                    y=[y_pos],
                    mode="markers",
                    name=player,
                    marker=dict(
                        symbol="circle",
                        color=color,
                        size=14,
                        line=dict(width=2, color="white"),
                    ),
                    showlegend=(
                        tech == tech_order[0]
                    ),  # Only show legend for first tech
                    legendgroup=player,
                    hovertemplate=f"<b>{tech}</b><br>{player}<br>Turn {turn}<extra></extra>",
                )
            )

    # Update layout
    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        height=fig_height,
    )

    # Update x-axis - remove grid
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
    )

    # Update y-axis - show tech names as labels
    fig.update_yaxes(
        showticklabels=True,
        tickmode="array",
        tickvals=list(range(len(tech_order))),
        ticktext=tech_order,
        showgrid=False,
        zeroline=False,
    )

    return fig


def create_law_adoption_timeline_chart(
    df: pd.DataFrame,
    player_colors: Optional[Dict[str, str]] = None,
) -> go.Figure:
    """Create a timeline chart showing when each player adopted each law.

    Each law gets its own row, with colored markers showing when
    each player adopted it. Makes it easy to compare timing between players.

    Args:
        df: DataFrame with columns: player_name, turn_number, law_name
            (from get_law_timeline())
        player_colors: Optional dict mapping player names to hex colors

    Returns:
        Plotly figure with law adoption timeline
    """
    if df.empty:
        return create_empty_chart_placeholder(
            "No law timeline data available for this match"
        )

    # Format law names: remove LAW_ prefix, quotes, replace underscores, title case
    df = df.copy()
    df["law_display"] = (
        df["law_name"]
        .str.replace('"', "", regex=False)  # Remove quotes from JSON extraction
        .str.replace("LAW_", "", regex=False)
        .str.replace("_", " ")
        .str.title()
    )

    # Get unique laws, ordered by earliest adoption turn
    law_order = (
        df.groupby("law_display")["turn_number"].min().sort_values().index.tolist()
    )

    # Assign y-position (row) to each law
    law_y_positions = {law: idx for idx, law in enumerate(law_order)}

    # Calculate figure height based on number of laws
    num_laws = len(law_order)
    fig_height = max(300, num_laws * 40 + 100)

    # Create base figure
    fig = create_base_figure(
        title="",
        x_title="Turn Number",
        y_title="",
        height=fig_height,
    )

    # Get unique players for color assignment
    players = df["player_name"].unique()

    # Add traces for each law
    for law in law_order:
        y_pos = law_y_positions[law]
        law_data = df[df["law_display"] == law].sort_values("turn_number")

        # If multiple players adopted this law, draw a connecting line
        if len(law_data) > 1:
            turns = law_data["turn_number"].tolist()
            fig.add_trace(
                go.Scatter(
                    x=turns,
                    y=[y_pos] * len(turns),
                    mode="lines",
                    line=dict(
                        color="rgba(128, 128, 128, 0.3)",
                        width=2,
                    ),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

        # Add a marker for each adoption (sorted chronologically)
        for idx, row in law_data.iterrows():
            player = row["player_name"]
            turn = row["turn_number"]

            # Get player color - use nation colors if provided
            if player_colors and player in player_colors:
                color = player_colors[player]
            else:
                player_idx = list(players).index(player)
                color = Config.PRIMARY_COLORS[player_idx % len(Config.PRIMARY_COLORS)]

            fig.add_trace(
                go.Scatter(
                    x=[turn],
                    y=[y_pos],
                    mode="markers",
                    name=player,
                    marker=dict(
                        symbol="circle",
                        color=color,
                        size=14,
                        line=dict(width=2, color="white"),
                    ),
                    showlegend=(law == law_order[0]),  # Only show legend for first law
                    legendgroup=player,
                    hovertemplate=f"<b>{law}</b><br>{player}<br>Turn {turn}<extra></extra>",
                )
            )

    # Update layout
    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        height=fig_height,
    )

    # Update x-axis - remove grid
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
    )

    # Update y-axis - show law names as labels
    fig.update_yaxes(
        showticklabels=True,
        tickmode="array",
        tickvals=list(range(len(law_order))),
        ticktext=law_order,
        showgrid=False,
        zeroline=False,
    )

    return fig


def create_food_yields_chart(
    df: pd.DataFrame, total_turns: Optional[int] = None
) -> go.Figure:
    """Create a line chart showing food yields over time.

    DEPRECATED: Use create_yield_chart() instead. Kept for backward compatibility.

    Args:
        df: DataFrame with columns: player_name, turn_number, amount
            (from get_yield_history_by_match() filtered to YIELD_FOOD)
        total_turns: Optional total turns in the match to extend lines to the end

    Returns:
        Plotly figure with line chart
    """
    return create_yield_chart(
        df, total_turns, yield_type="YIELD_FOOD", display_name="Food"
    )


def create_yield_chart(
    df: pd.DataFrame,
    total_turns: Optional[int] = None,
    yield_type: str = "YIELD_FOOD",
    display_name: Optional[str] = None,
) -> go.Figure:
    """Create a line chart showing yield production over time.

    Generic function that works for any yield type (Food, Science, Culture, etc.).
    Shows yield production per turn for each player, making it easy to compare
    yield economy development throughout the match.

    Args:
        df: DataFrame with columns: player_name, turn_number, amount, resource_type
            (from get_yield_history_by_match() filtered to specific yield type)
        total_turns: Optional total turns in the match to extend lines to the end
        yield_type: The yield type being displayed (e.g., "YIELD_FOOD", "YIELD_SCIENCE")
                   Used for validation and error messages
        display_name: Optional human-readable name for the yield (e.g., "Food", "Science")
                     If not provided, derives from yield_type (removes YIELD_ prefix)

    Returns:
        Plotly figure with line chart

    Example:
        >>> df = queries.get_yield_history_by_match(match_id=1, yield_types=["YIELD_SCIENCE"])
        >>> fig = create_yield_chart(df, total_turns=100, yield_type="YIELD_SCIENCE", display_name="Science")
    """
    # Derive display name if not provided
    if display_name is None:
        display_name = yield_type.replace("YIELD_", "").replace("_", " ").title()

    if df.empty:
        return create_empty_chart_placeholder(
            f"No {display_name} yield data available for this match"
        )

    fig = create_base_figure(
        title="",
        x_title="Turn Number",
        y_title=f"{display_name} Yield",
        height=400,
    )

    # Add a line for each player
    players = df["player_name"].unique()

    for i, player in enumerate(players):
        player_data = df[df["player_name"] == player].sort_values("turn_number")

        # Get turn and yield data
        turns = player_data["turn_number"].tolist()
        yields = player_data["amount"].tolist()

        # Create hover text
        hover_texts = [
            f"<b>{player}</b><br>Turn {turn}: {yield_val:.1f} {display_name.lower()}"
            for turn, yield_val in zip(turns, yields)
        ]

        # Extend line to match end if total_turns provided
        if total_turns and turns and turns[-1] < total_turns:
            turns.append(total_turns)
            yields.append(yields[-1])  # Keep final yield value
            hover_texts.append(hover_texts[-1])  # Reuse last hover text

        # Assign last trace to yaxis2 to make right-side labels visible
        yaxis_ref = "y2" if i == len(players) - 1 else "y"

        fig.add_trace(
            go.Scatter(
                x=turns,
                y=yields,
                mode="lines+markers",
                name=player,
                line=dict(
                    color=Config.PRIMARY_COLORS[i % len(Config.PRIMARY_COLORS)],
                    width=4,
                ),
                marker=dict(size=8),
                hoveron="points",  # Only trigger hover on marker points, not lines
                hovertemplate="%{hovertext}<extra></extra>",
                hovertext=hover_texts,
                yaxis=yaxis_ref,
            )
        )

    # Calculate the maximum yield to set appropriate y-axis range
    max_yield = int(df["amount"].max()) if not df.empty else 100
    y_range = [0, max_yield + 20]  # Add some padding at the top

    # Set Y-axis with labels on both left and right sides
    fig.update_layout(
        yaxis=dict(
            range=y_range,
            showgrid=True,
            ticks="outside",
        ),
        yaxis2=dict(
            overlaying="y",
            side="right",
            range=y_range,
            showticklabels=True,
            ticks="outside",
            showgrid=False,
        ),
        hovermode="closest",  # Explicitly set hover mode
        hoverdistance=100,  # Increase hover detection distance (default is 20)
    )

    return fig


def create_match_yield_stacked_chart(
    df: pd.DataFrame,
    total_turns: Optional[int] = None,
    yield_type: str = "YIELD_FOOD",
    display_name: Optional[str] = None,
    player_colors: Optional[Dict[str, str]] = None,
) -> go.Figure:
    """Create stacked subplots showing per-player yield rate and cumulative.

    Top chart shows yield per turn for each player, bottom shows cumulative total.
    Both share the x-axis for synchronized zoom/pan.

    Args:
        df: DataFrame with columns: player_name, turn_number, amount, resource_type
            (from get_yield_history_by_match() filtered to specific yield type)
        total_turns: Optional total turns in the match to extend lines to the end
        yield_type: The yield type being displayed (e.g., "YIELD_FOOD")
        display_name: Optional human-readable name (e.g., "Food")
        player_colors: Optional dict mapping player names to hex colors

    Returns:
        Plotly figure with two vertically stacked subplots
    """
    if display_name is None:
        display_name = yield_type.replace("YIELD_", "").replace("_", " ").title()

    if df.empty:
        return create_empty_chart_placeholder(
            f"No {display_name} yield data available for this match"
        )

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.5, 0.5],
        subplot_titles=("Per Turn", "Cumulative Total"),
    )
    fig = apply_dark_theme(fig)

    players = df["player_name"].unique()

    for i, player in enumerate(players):
        player_data = df[df["player_name"] == player].sort_values("turn_number")
        # Use nation-based color if provided, otherwise fall back to default
        if player_colors and player in player_colors:
            color = player_colors[player]
        else:
            color = Config.PRIMARY_COLORS[i % len(Config.PRIMARY_COLORS)]

        turns = player_data["turn_number"].tolist()
        yields = player_data["amount"].tolist()

        # Calculate cumulative yields
        cumulative = []
        running_total = 0.0
        for y in yields:
            running_total += y
            cumulative.append(running_total)

        # Extend lines to match end if total_turns provided
        if total_turns and turns and turns[-1] < total_turns:
            turns = turns + [total_turns]
            yields = yields + [yields[-1]]
            cumulative = cumulative + [cumulative[-1]]

        # Rate chart (top)
        fig.add_trace(
            go.Scatter(
                x=turns,
                y=yields,
                mode="lines+markers",
                name=player,
                line=dict(color=color, width=2),
                marker=dict(size=6),
                hovertemplate=f"<b>{player}</b><br>Turn %{{x}}: %{{y:.1f}}/turn<extra></extra>",
                legendgroup=player,
            ),
            row=1,
            col=1,
        )

        # Cumulative chart (bottom)
        fig.add_trace(
            go.Scatter(
                x=turns,
                y=cumulative,
                mode="lines+markers",
                name=player,
                line=dict(color=color, width=2),
                marker=dict(size=6),
                hovertemplate=f"<b>{player}</b><br>Turn %{{x}}: %{{y:,.0f}} total<extra></extra>",
                legendgroup=player,
                showlegend=False,
            ),
            row=2,
            col=1,
        )

    fig.update_layout(
        height=500,
        margin=dict(t=30, b=40, l=60, r=20),
        hovermode="closest",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
        ),
        template=None,
    )

    for annotation in fig["layout"]["annotations"]:
        annotation["font"] = dict(size=11, color=CHART_THEME["text_muted"])

    fig.update_xaxes(title_text="Turn Number", row=2, col=1)
    fig.update_yaxes(title_text=f"{display_name}/Turn", row=1, col=1)
    fig.update_yaxes(title_text=f"Total {display_name}", row=2, col=1)

    return fig


def create_map_breakdown_actual_sunburst_chart(df: pd.DataFrame) -> go.Figure:
    """Create an actual sunburst chart showing map breakdown by Size → Class → Aspect.

    Hierarchical structure:
    - Center: Total maps
    - Inner ring: Map sizes (Duel, Tiny)
    - Middle ring: Map classes (Continent, Inland Sea, etc.)
    - Outer ring: Aspect ratios (Square, Wide, etc.)

    Color scheme:
    - Continent: Shades of green
    - Inland Sea: Shades of blue
    - Coastal Rain Basin: Shades of red

    Args:
        df: DataFrame with map_class, map_aspect_ratio, map_size, count columns

    Returns:
        Plotly figure with sunburst chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No map data available")

    # Define color mapping for map classes and their aspect ratios
    # Green shades for Continent (darkest to lightest)
    # Blue shades for Inland Sea (darkest to lightest)
    # Red shades for Coastal Rain Basin (darkest to lightest)
    color_map = {
        # Root node - neutral gray
        "All Maps": "#808080",
        # Size level - light neutral colors
        "Duel": "#A0A0A0",
        "Tiny": "#B0B0B0",
        # Continent - Green shades (middle ring and outer ring)
        "Duel - Continent": "#2E7D32",  # Dark green
        "Tiny - Continent": "#388E3C",  # Medium-dark green
        "Duel - Continent - Square": "#1B5E20",  # Darkest green
        "Duel - Continent - Wide": "#2E7D32",  # Dark green
        "Duel - Continent - Ultrawide": "#43A047",  # Medium green
        "Duel - Continent - Dynamic": "#66BB6A",  # Light green
        "Tiny - Continent - Square": "#2E7D32",  # Dark green
        "Tiny - Continent - Wide": "#43A047",  # Medium green
        "Tiny - Continent - Ultrawide": "#66BB6A",  # Light green
        "Tiny - Continent - Dynamic": "#81C784",  # Lightest green
        # Inland Sea - Blue shades (middle ring and outer ring)
        "Duel - Inland Sea": "#1565C0",  # Dark blue
        "Tiny - Inland Sea": "#1976D2",  # Medium-dark blue
        "Duel - Inland Sea - Square": "#0D47A1",  # Darkest blue
        "Duel - Inland Sea - Wide": "#1565C0",  # Dark blue
        "Duel - Inland Sea - Ultrawide": "#1976D2",  # Medium blue
        "Duel - Inland Sea - Dynamic": "#42A5F5",  # Light blue
        "Tiny - Inland Sea - Square": "#1565C0",  # Dark blue
        "Tiny - Inland Sea - Wide": "#1976D2",  # Medium blue
        "Tiny - Inland Sea - Ultrawide": "#42A5F5",  # Light blue
        "Tiny - Inland Sea - Dynamic": "#64B5F6",  # Lightest blue
        # Coastal Rain Basin - Red shades (middle ring and outer ring)
        "Duel - Coastal Rain Basin": "#C62828",  # Dark red
        "Tiny - Coastal Rain Basin": "#D32F2F",  # Medium-dark red
        "Duel - Coastal Rain Basin - Square": "#B71C1C",  # Darkest red
        "Duel - Coastal Rain Basin - Wide": "#C62828",  # Dark red
        "Duel - Coastal Rain Basin - Ultrawide": "#D32F2F",  # Medium red
        "Duel - Coastal Rain Basin - Dynamic": "#E57373",  # Light red
        "Tiny - Coastal Rain Basin - Square": "#C62828",  # Dark red
        "Tiny - Coastal Rain Basin - Wide": "#D32F2F",  # Medium red
        "Tiny - Coastal Rain Basin - Ultrawide": "#E57373",  # Light red
        "Tiny - Coastal Rain Basin - Dynamic": "#EF5350",  # Lightest red
    }

    # Build hierarchical data for sunburst
    labels = []
    parents = []
    values = []
    colors = []
    hover_texts = []

    # Root node
    total_maps = int(df["count"].sum())
    labels.append("All Maps")
    parents.append("")
    values.append(total_maps)
    colors.append(color_map.get("All Maps", "#808080"))
    hover_texts.append(f"<b>All Maps</b><br>Count: {total_maps}")

    # Level 1: Map sizes
    size_totals = df.groupby("map_size")["count"].sum()
    for size in size_totals.index:
        labels.append(size)
        parents.append("All Maps")
        values.append(int(size_totals[size]))
        colors.append(color_map.get(size, "#A0A0A0"))
        hover_texts.append(f"<b>{size}</b><br>Count: {int(size_totals[size])}")

    # Level 2: Map classes within each size
    class_by_size = df.groupby(["map_size", "map_class"])["count"].sum()
    for (size, map_class), count in class_by_size.items():
        # Use full label for internal reference but display only class name
        full_label = f"{size} - {map_class}"
        labels.append(full_label)
        parents.append(size)
        values.append(int(count))
        colors.append(color_map.get(full_label, "#808080"))
        hover_texts.append(f"<b>{map_class}</b><br>Size: {size}<br>Count: {int(count)}")

    # Level 3: Aspect ratios within each class
    for _, row in df.iterrows():
        size = row["map_size"]
        map_class = row["map_class"]
        aspect = row["map_aspect_ratio"]
        count = int(row["count"])

        parent_label = f"{size} - {map_class}"
        full_label = f"{size} - {map_class} - {aspect}"

        labels.append(full_label)
        parents.append(parent_label)
        values.append(count)
        colors.append(color_map.get(full_label, "#808080"))
        hover_texts.append(
            f"<b>{aspect}</b><br>Class: {map_class}<br>Size: {size}<br>Count: {count}"
        )

    # Create display labels (only the last part of each label)
    display_labels = [label.split(" - ")[-1] for label in labels]

    fig = go.Figure(
        go.Sunburst(
            labels=labels,  # Keep full labels for internal hierarchy
            parents=parents,
            values=values,
            branchvalues="total",
            marker=dict(
                colors=colors,
                line=dict(color="white", width=2),
            ),
            text=display_labels,  # Display only the last part
            textinfo="text",  # Show only the custom text, not the label
            hovertext=hover_texts,
            hovertemplate="%{hovertext}<extra></extra>",
        )
    )

    fig.update_layout(
        margin=dict(t=0, l=0, r=0, b=0),
        height=400,
        paper_bgcolor=CHART_THEME["paper_bgcolor"],
        font=dict(color=CHART_THEME["font_color"]),
    )

    return fig


def create_map_breakdown_parallel_categories_chart(df: pd.DataFrame) -> go.Figure:
    """Create a parallel categories (Sankey-style) chart showing map dimension relationships.

    Shows flow from Size → Class → Aspect with ribbon widths proportional to count.

    Args:
        df: DataFrame with map_class, map_aspect_ratio, map_size, count columns

    Returns:
        Plotly figure with parallel categories chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No map data available")

    # Use Plotly's Parcats (parallel categories) trace
    fig = go.Figure(
        go.Parcats(
            dimensions=[
                {
                    "label": "Size",
                    "values": df["map_size"],
                },
                {
                    "label": "Class",
                    "values": df["map_class"],
                },
                {
                    "label": "Aspect",
                    "values": df["map_aspect_ratio"],
                },
            ],
            counts=df["count"],
            line=dict(
                color=df["count"],
                colorscale="Viridis",
                showscale=True,
                cmin=df["count"].min(),
                cmax=df["count"].max(),
            ),
            hoveron="dimension",
            hovertemplate="<b>%{label}</b><br>Count: %{count}<extra></extra>",
        )
    )

    fig.update_layout(
        title="Map Breakdown (Parallel Categories)",
        margin=dict(t=60, l=80, r=80, b=20),
        height=400,
        paper_bgcolor=CHART_THEME["paper_bgcolor"],
        font=dict(color=CHART_THEME["font_color"]),
    )

    return fig


def create_aggregated_event_category_timeline_chart(df: pd.DataFrame) -> go.Figure:
    """Create a stacked area chart showing event categories over time across all matches.

    Shows the typical pattern of game events throughout a match by aggregating
    event data across all matches and categorizing into gameplay categories.

    Args:
        df: DataFrame with columns: turn_number, event_type, avg_event_count
            (from get_aggregated_event_timeline())

    Returns:
        Plotly figure with stacked area chart
    """
    from ..utils.event_categories import get_category_color_map, get_event_category

    if df.empty:
        return create_empty_chart_placeholder("No event timeline data available")

    # Apply event categorization
    df = df.copy()
    df["gameplay_category"] = df["event_type"].apply(get_event_category)

    # Aggregate by turn and category
    category_timeline = (
        df.groupby(["turn_number", "gameplay_category"])["avg_event_count"]
        .sum()
        .reset_index()
    )

    # Get category colors
    category_colors = get_category_color_map()

    fig = create_base_figure(
        title="",
        x_title="Turn Number",
        y_title="Average Events per Turn",
        height=450,
    )

    # Get all categories sorted for consistent ordering
    categories = sorted(category_timeline["gameplay_category"].unique())

    # Add stacked area traces for each category
    for category in categories:
        category_data = category_timeline[
            category_timeline["gameplay_category"] == category
        ].sort_values("turn_number")

        fig.add_trace(
            go.Scatter(
                x=category_data["turn_number"],
                y=category_data["avg_event_count"],
                name=category,
                mode="lines",
                stackgroup="one",  # This creates the stacked area effect
                fillcolor=category_colors.get(category, "#6c757d"),
                line=dict(width=0.5, color=category_colors.get(category, "#6c757d")),
                hovertemplate=(
                    f"<b>{category}</b><br>"
                    "Turn: %{x}<br>"
                    "Avg Events: %{y:.2f}<br>"
                    "<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        hovermode="x unified",
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
        ),
        margin=dict(t=40, l=50, r=150, b=50),
    )

    return fig


def create_ambition_timeline_chart(df: pd.DataFrame) -> go.Figure:
    """Create a timeline chart showing ambition/goal events for a single player.

    Each ambition gets its own row to prevent overlapping labels.

    Args:
        df: DataFrame with columns: player_name, turn_number, status, description
            (from get_ambition_timeline(), filtered to single player)

    Returns:
        Plotly figure with scatter plot timeline
    """
    if df.empty:
        return create_empty_chart_placeholder("No ambition data available")

    # Should only have one player at this point
    player_name = df["player_name"].iloc[0] if not df.empty else "Player"

    # Define marker properties for each status (semantic colors)
    status_markers = {
        "Started": {
            "symbol": "circle-open",
            "color": Config.PRIMARY_COLORS[0],  # Green - new beginning
            "size": 10,
        },
        "Completed": {
            "symbol": "circle",
            "color": Config.PRIMARY_COLORS[1],  # Orange - achievement
            "size": 12,
        },
        "Failed": {"symbol": "x", "color": Config.PRIMARY_COLORS[3], "size": 12},  # Red - failure
    }

    # Helper function to extract ambition name from description
    def extract_ambition_name(description: str) -> str:
        """Extract ambition name from event description."""
        for link_type in ["link(CONCEPT_AMBITION):", "link(CONCEPT_LEGACY):"]:
            if link_type in description:
                text_after = description.split(link_type)[-1]
                if "Failed a" in text_after:
                    text_after = text_after.split("Failed a")[0]
                return text_after.strip()
        return description

    # Extract ambition names and assign each unique ambition to a row
    df_copy = df.copy()
    df_copy["ambition_name"] = df_copy["description"].apply(extract_ambition_name)

    # Get unique ambitions (ordered by first appearance)
    started_ambitions = df_copy[df_copy["status"] == "Started"].sort_values(
        "turn_number"
    )
    unique_ambitions = started_ambitions["ambition_name"].unique()

    # Assign y-position (row) to each ambition
    ambition_y_positions = {
        ambition: idx for idx, ambition in enumerate(unique_ambitions)
    }

    # Calculate figure height based on number of ambitions (more space per row)
    num_ambitions = len(unique_ambitions)
    fig_height = max(300, num_ambitions * 60 + 100)

    # Create base figure
    fig = create_base_figure(
        title="",
        x_title="Turn Number",
        y_title="",
        height=fig_height,
    )

    # Add traces for each ambition
    for ambition in unique_ambitions:
        y_pos = ambition_y_positions[ambition]
        ambition_data = df_copy[df_copy["ambition_name"] == ambition]

        # Add marker traces for each status
        for status in ["Started", "Completed", "Failed"]:
            status_data = ambition_data[ambition_data["status"] == status]
            if not status_data.empty:
                marker_props = status_markers[status]

                # Only show labels for "Started" status
                if status == "Started":
                    label_texts = [f"Started {ambition}"]
                    mode = "markers+text"
                else:
                    label_texts = None
                    mode = "markers"

                fig.add_trace(
                    go.Scatter(
                        x=status_data["turn_number"],
                        y=[y_pos] * len(status_data),
                        mode=mode,
                        name=f"{status}",
                        marker=dict(
                            symbol=marker_props["symbol"],
                            color=marker_props["color"],
                            size=marker_props["size"],
                            line=dict(width=1, color="white"),
                        ),
                        text=label_texts if label_texts else None,
                        textposition="middle left" if label_texts else None,
                        textfont=dict(size=10) if label_texts else None,
                        showlegend=False,
                        hovertemplate=f"<b>{ambition}</b><br>{status}<br>Turn %{{x}}<extra></extra>",
                    )
                )

        # Add connecting line from start to end
        started = ambition_data[ambition_data["status"] == "Started"]
        if not started.empty:
            start_turn = started.iloc[0]["turn_number"]

            ended = ambition_data[
                ambition_data["status"].isin(["Completed", "Failed"])
                & (ambition_data["turn_number"] > start_turn)
            ]

            if not ended.empty:
                end_turn = ended.iloc[0]["turn_number"]

                fig.add_trace(
                    go.Scatter(
                        x=[start_turn, end_turn],
                        y=[y_pos, y_pos],
                        mode="lines",
                        line=dict(
                            color="rgba(128, 128, 128, 0.3)",
                            width=2,
                            dash="dot",
                        ),
                        showlegend=False,
                        hoverinfo="skip",
                    )
                )

    # Update layout
    fig.update_layout(
        showlegend=False,
        height=fig_height,
    )

    # Update x-axis
    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor=CHART_THEME["gridcolor"],
    )

    # Hide y-axis (ambition names are in labels)
    fig.update_yaxes(visible=False)

    return fig


def create_ambition_summary_table(df: pd.DataFrame) -> go.Figure:
    """Create a summary table showing ambition statistics by player.

    Displays a table with columns for player name, civilization, ambitions started,
    completed, failed, and completion rate percentage.

    Args:
        df: DataFrame with columns: player_name, civilization, started, completed,
            failed, completion_rate (from get_ambition_summary())

    Returns:
        Plotly figure with table visualization
    """
    if df.empty:
        return create_empty_chart_placeholder(
            "No ambition data available for this match"
        )

    # Format completion rate with % symbol
    df_display = df.copy()
    df_display["completion_rate"] = df_display["completion_rate"].apply(
        lambda x: f"{x}%"
    )

    fig = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=[
                        "<b>Player</b>",
                        "<b>Civilization</b>",
                        "<b>Started</b>",
                        "<b>Completed</b>",
                        "<b>Failed</b>",
                        "<b>Completion Rate</b>",
                    ],
                    fill_color=CHART_THEME["hoverlabel_bgcolor"],
                    align="left",
                    font=dict(color=CHART_THEME["font_color"], size=12),
                ),
                cells=dict(
                    values=[
                        df_display["player_name"],
                        df_display["civilization"],
                        df_display["started"],
                        df_display["completed"],
                        df_display["failed"],
                        df_display["completion_rate"],
                    ],
                    fill_color=[
                        [CHART_THEME["paper_bgcolor"], CHART_THEME["plot_bgcolor"]] * len(df_display)
                    ],  # Alternating row colors
                    align="left",
                    font=dict(color=CHART_THEME["font_color"], size=11),
                    height=30,
                ),
            )
        ]
    )

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor=CHART_THEME["paper_bgcolor"],
        height=max(150, len(df) * 35 + 50),  # Dynamic height based on number of players
    )

    return fig


def create_ruler_archetype_win_rates_chart(df: pd.DataFrame) -> go.Figure:
    """Create a dual-axis chart showing archetype win rates and games played.

    Displays both the number of games played (bars) and win rate percentage (line)
    for each ruler archetype, allowing easy comparison of popularity vs effectiveness.

    Args:
        df: DataFrame with columns: archetype, games, wins, win_rate

    Returns:
        Plotly figure with dual-axis bar/line chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No ruler data available")

    # Sort by win rate descending
    df_sorted = df.sort_values("win_rate", ascending=True)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig = apply_dark_theme(fig)

    # Add bars for games played
    fig.add_trace(
        go.Bar(
            y=df_sorted["archetype"],
            x=df_sorted["games"],
            name="Games Played",
            marker_color="lightblue",
            orientation="h",
            hovertemplate="<b>%{y}</b><br>Games: %{x}<extra></extra>",
        ),
        secondary_y=False,
    )

    # Add line for win rate
    fig.add_trace(
        go.Scatter(
            y=df_sorted["archetype"],
            x=df_sorted["win_rate"],
            name="Win Rate",
            mode="lines+markers",
            marker=dict(size=10, color="red"),
            line=dict(color="red", width=2),
            hovertemplate="<b>%{y}</b><br>Win Rate: %{x:.1f}%<extra></extra>",
        ),
        secondary_y=True,
    )

    # Update axes labels
    fig.update_layout(
        height=400,
        showlegend=True,
        legend=dict(x=0.5, y=-0.15, xanchor="center", orientation="h"),
        hovermode="closest",
        yaxis=dict(title="Archetype"),
        xaxis=dict(title="Games Played"),
        xaxis2=dict(title="Win Rate (%)", overlaying="x", side="top", range=[0, 100]),
    )

    return fig


def create_ruler_trait_performance_chart(df: pd.DataFrame) -> go.Figure:
    """Create a dual-axis chart showing trait win rates and games played.

    Displays both the number of games played (bars) and win rate percentage (line)
    for each starting ruler trait, allowing easy comparison of popularity vs effectiveness.

    Args:
        df: DataFrame with columns: starting_trait, games, wins, win_rate

    Returns:
        Plotly figure with dual-axis bar/line chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No ruler data available")

    # Sort by win rate descending
    df_sorted = df.sort_values("win_rate", ascending=True)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig = apply_dark_theme(fig)

    # Add bars for games played
    fig.add_trace(
        go.Bar(
            y=df_sorted["starting_trait"],
            x=df_sorted["games"],
            name="Games Played",
            marker_color="lightblue",
            orientation="h",
            hovertemplate="<b>%{y}</b><br>Games: %{x}<extra></extra>",
        ),
        secondary_y=False,
    )

    # Add line for win rate
    fig.add_trace(
        go.Scatter(
            y=df_sorted["starting_trait"],
            x=df_sorted["win_rate"],
            name="Win Rate",
            mode="lines+markers",
            marker=dict(size=10, color="red"),
            line=dict(color="red", width=2),
            hovertemplate="<b>%{y}</b><br>Win Rate: %{x:.1f}%<extra></extra>",
        ),
        secondary_y=True,
    )

    # Update axes labels
    fig.update_layout(
        height=400,
        showlegend=True,
        legend=dict(x=0.5, y=-0.15, xanchor="center", orientation="h"),
        hovermode="closest",
        yaxis=dict(title="Trait"),
        xaxis=dict(title="Games Played"),
        xaxis2=dict(title="Win Rate (%)", overlaying="x", side="top", range=[0, 100]),
    )

    return fig


def create_ruler_archetype_matchup_matrix(df: pd.DataFrame) -> go.Figure:
    """Create a heatmap showing archetype vs archetype win rates.

    Displays win rates for each archetype matchup, showing which archetypes
    perform well against which opponents.

    Args:
        df: DataFrame with columns: archetype, opponent_archetype, games, wins, win_rate

    Returns:
        Plotly figure with heatmap showing matchup win rates
    """
    if df.empty:
        return create_empty_chart_placeholder("No archetype matchup data available")

    # Pivot the data for heatmap
    pivot_data = df.pivot_table(
        index="archetype",
        columns="opponent_archetype",
        values="win_rate",
        aggfunc="first",
    )

    # Get games count for hover text
    games_pivot = df.pivot_table(
        index="archetype", columns="opponent_archetype", values="games", aggfunc="first"
    )

    # Create hover text with win rates and game counts
    hover_text = []
    for i, row_archetype in enumerate(pivot_data.index):
        hover_row = []
        for j, col_archetype in enumerate(pivot_data.columns):
            win_rate = pivot_data.iloc[i, j]
            games = games_pivot.iloc[i, j]
            if pd.notna(win_rate) and pd.notna(games):
                hover_row.append(
                    f"<b>{row_archetype} vs {col_archetype}</b><br>"
                    f"Win Rate: {win_rate:.1f}%<br>"
                    f"Games: {int(games)}"
                )
            else:
                hover_row.append(
                    f"<b>{row_archetype} vs {col_archetype}</b><br>No data"
                )
        hover_text.append(hover_row)

    fig = create_base_figure(
        show_legend=False,
        height=500,
    )

    # Create color scale: red (0%) -> yellow (50%) -> green (100%)
    colorscale = [
        [0.0, "#EF5350"],  # Red (0% win rate)
        [0.5, "#FFF59D"],  # Yellow (50% win rate)
        [1.0, "#66BB6A"],  # Green (100% win rate)
    ]

    fig.add_trace(
        go.Heatmap(
            z=pivot_data.values,
            x=pivot_data.columns,
            y=pivot_data.index,
            colorscale=colorscale,
            zmin=0,
            zmax=100,
            hovertext=hover_text,
            hoverinfo="text",
            showscale=True,
            colorbar=dict(
                title="Win Rate (%)",
                ticksuffix="%",
            ),
            text=[
                [f"{val:.0f}%" if pd.notna(val) else "N/A" for val in row]
                for row in pivot_data.values
            ],
            texttemplate="%{text}",
            textfont={"size": 10},
        )
    )

    fig.update_xaxes(title="Opponent Archetype", side="bottom")
    fig.update_yaxes(title="Your Archetype")

    return fig


def create_nation_counter_pick_heatmap(
    df: pd.DataFrame, min_games: int = 1
) -> go.Figure:
    """Create a heatmap showing nation counter-pick effectiveness.

    Displays win rates for second picker by matchup (first_pick vs second_pick),
    showing which nations are effective counters when picked second.

    Args:
        df: DataFrame with columns: first_pick_nation, second_pick_nation,
            games, second_picker_wins, second_picker_win_rate
        min_games: Minimum games to display (for hover text filtering)

    Returns:
        Plotly figure with heatmap showing counter-pick win rates
    """
    if df.empty:
        return create_empty_chart_placeholder(
            "No counter-pick data available. Pick order data needs to be synced."
        )

    # Pivot the data for heatmap
    pivot_data = df.pivot_table(
        index="first_pick_nation",
        columns="second_pick_nation",
        values="second_picker_win_rate",
        aggfunc="first",
    )

    # Get games count for hover text
    games_pivot = df.pivot_table(
        index="first_pick_nation",
        columns="second_pick_nation",
        values="games",
        aggfunc="first",
    )

    # Create hover text with win rates and game counts
    hover_text = []
    for i, first_pick in enumerate(pivot_data.index):
        hover_row = []
        for j, second_pick in enumerate(pivot_data.columns):
            win_rate = pivot_data.iloc[i, j]
            games = games_pivot.iloc[i, j]
            if pd.notna(win_rate) and pd.notna(games):
                # Show from second picker's perspective
                hover_row.append(
                    f"<b>{first_pick} (1st) vs {second_pick} (2nd)</b><br>"
                    f"{second_pick} Win Rate: {win_rate:.1f}%<br>"
                    f"Games: {int(games)}<br>"
                    f"<i>{'Strong counter!' if win_rate >= 60 else 'Weak counter' if win_rate <= 40 else 'Even matchup'}</i>"
                )
            else:
                hover_row.append(f"<b>{first_pick} vs {second_pick}</b><br>No data")
        hover_text.append(hover_row)

    fig = create_base_figure(
        show_legend=False,
        height=500,
    )

    # Create color scale: red (bad counter, low WR) -> yellow (even) -> green (good counter, high WR)
    # Red = second picker loses often, Green = second picker wins often
    colorscale = [
        [0.0, "#EF5350"],  # Red (0% - terrible counter)
        [0.5, "#FFF59D"],  # Yellow (50% - even matchup)
        [1.0, "#66BB6A"],  # Green (100% - perfect counter)
    ]

    fig.add_trace(
        go.Heatmap(
            z=pivot_data.values,
            x=pivot_data.columns,
            y=pivot_data.index,
            colorscale=colorscale,
            zmin=0,
            zmax=100,
            hovertext=hover_text,
            hoverinfo="text",
            showscale=True,
            colorbar=dict(
                title=dict(
                    text="Counter<br>Effectiveness",
                    side="right",
                ),
                ticksuffix="%",
                tickvals=[0, 25, 50, 75, 100],
                ticktext=[
                    "0%<br>(Bad)",
                    "25%",
                    "50%<br>(Even)",
                    "75%",
                    "100%<br>(Good)",
                ],
                len=0.75,
                thickness=15,
                x=1.02,
            ),
            text=[
                [f"{val:.0f}%" if pd.notna(val) else "-" for val in row]
                for row in pivot_data.values
            ],
            texttemplate="%{text}",
            textfont={"size": 10},
        )
    )

    fig.update_xaxes(title="Counter-Pick (2nd)", side="bottom")
    fig.update_yaxes(title="First Pick")

    # Add more right margin to prevent colorbar overlap
    # Add bottom margin to show annotation
    fig.update_layout(margin=dict(r=120, b=80))

    # Add annotation explaining the heatmap
    fig.add_annotation(
        text="Higher % = Better counter when picked second",
        xref="paper",
        yref="paper",
        x=0.5,
        y=-0.15,
        showarrow=False,
        font=dict(size=10, color="gray"),
        xanchor="center",
    )

    return fig


def create_pick_order_win_rate_chart(df: pd.DataFrame) -> go.Figure:
    """Create a grouped bar chart showing win rates by pick order.

    Displays first pick vs second pick win rates with error bars for confidence
    intervals and statistical significance annotation.

    Args:
        df: DataFrame with columns: pick_position, games, wins, win_rate,
            ci_lower, ci_upper, standard_error

    Returns:
        Plotly figure with grouped bar chart showing pick order win rates
    """
    if df.empty:
        return create_empty_chart_placeholder(
            "No pick order data available. Pick order data needs to be synced."
        )

    fig = create_base_figure(
        x_title="Pick Position",
        y_title="Win Rate (%)",
        show_legend=False,
    )

    # Create hover text
    hover_text = []
    for _, row in df.iterrows():
        hover_text.append(
            f"<b>{row['pick_position']}</b><br>"
            f"Win Rate: {row['win_rate']:.1f}%<br>"
            f"95% CI: [{row['ci_lower']:.1f}%, {row['ci_upper']:.1f}%]<br>"
            f"Games: {int(row['games'])}<br>"
            f"Wins: {int(row['wins'])}"
        )

    # Add bars with error bars
    fig.add_trace(
        go.Bar(
            x=df["pick_position"],
            y=df["win_rate"],
            error_y=dict(
                type="data",
                symmetric=False,
                array=df["ci_upper"] - df["win_rate"],
                arrayminus=df["win_rate"] - df["ci_lower"],
                color="rgba(0,0,0,0.3)",
                thickness=1.5,
                width=4,
            ),
            marker=dict(
                color=[Config.PRIMARY_COLORS[0], Config.PRIMARY_COLORS[1]],
                line=dict(color="white", width=1),
            ),
            hovertemplate="%{hovertext}<extra></extra>",
            hovertext=hover_text,
        )
    )

    # Add 50% reference line
    fig.add_hline(
        y=50,
        line_dash="dash",
        line_color="gray",
        opacity=0.5,
        annotation_text="Even (50%)",
        annotation_position="right",
    )

    # Check if difference is statistically significant
    # If confidence intervals don't overlap, the difference is significant
    if len(df) == 2:
        first_pick = df[df["pick_position"] == "First Pick"].iloc[0]
        second_pick = df[df["pick_position"] == "Second Pick"].iloc[0]

        # Check for overlap: if first_ci_lower > second_ci_upper or second_ci_lower > first_ci_upper
        no_overlap = (
            first_pick["ci_lower"] > second_pick["ci_upper"]
            or second_pick["ci_lower"] > first_pick["ci_upper"]
        )

        if no_overlap:
            # Add significance annotation
            higher = (
                first_pick
                if first_pick["win_rate"] > second_pick["win_rate"]
                else second_pick
            )
            fig.add_annotation(
                text="★ Statistically significant difference (p < 0.05)",
                xref="paper",
                yref="paper",
                x=0.5,
                y=1.05,
                showarrow=False,
                font=dict(size=11, color=Config.PRIMARY_COLORS[0]),
                xanchor="center",
            )

    # Set y-axis range to make differences more visible
    fig.update_yaxes(range=[0, 100])

    return fig


def create_ruler_succession_impact_chart(df: pd.DataFrame) -> go.Figure:
    """Create a line chart showing succession impact on victory.

    Displays the relationship between number of ruler successions and win rate,
    revealing patterns about succession stability and effectiveness.

    Args:
        df: DataFrame with columns: succession_category, games, wins, win_rate

    Returns:
        Plotly figure with line chart showing succession impact
    """
    if df.empty:
        return create_empty_chart_placeholder("No ruler data available")

    # Define order for categories
    category_order = ["1 ruler", "2 rulers", "3 rulers", "4+ rulers"]
    df_sorted = (
        df.set_index("succession_category").reindex(category_order).reset_index()
    )

    fig = create_base_figure(
        title="Succession Impact on Victory",
        x_title="Number of Rulers",
        y_title="Win Rate (%)",
        show_legend=False,
    )

    # Create hover text
    hover_text = []
    for _, row in df_sorted.iterrows():
        if pd.isna(row["games"]):
            hover_text.append(f"<b>{row['succession_category']}</b><br>No data")
        else:
            hover_text.append(
                f"<b>{row['succession_category']}</b><br>"
                f"Win Rate: {row['win_rate']:.1f}%<br>"
                f"Games: {int(row['games'])}<br>"
                f"Wins: {int(row['wins'])}"
            )

    fig.add_trace(
        go.Scatter(
            x=df_sorted["succession_category"],
            y=df_sorted["win_rate"],
            mode="lines+markers",
            line=dict(color=Config.PRIMARY_COLORS[0], width=3),
            marker=dict(size=12, color=Config.PRIMARY_COLORS[0]),
            fill="tozeroy",
            fillcolor=f"rgba({int(Config.PRIMARY_COLORS[0][1:3], 16)}, {int(Config.PRIMARY_COLORS[0][3:5], 16)}, {int(Config.PRIMARY_COLORS[0][5:7], 16)}, 0.2)",
            hovertemplate="%{hovertext}<extra></extra>",
            hovertext=hover_text,
        )
    )

    fig.update_layout(
        yaxis={"range": [0, 100]},
        height=400,
    )

    return fig


def create_ruler_trait_win_rates_chart(df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    """Create a horizontal bar chart showing trait win rates.

    Displays win rates for starting ruler traits, limited to most common traits.

    Args:
        df: DataFrame with columns: starting_trait, games, wins, win_rate
        top_n: Number of top traits to display (default 10)

    Returns:
        Plotly figure with horizontal bar chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No ruler data available")

    # Limit to top N and sort by win rate
    df_top = df.head(top_n).sort_values("win_rate", ascending=True)

    fig = create_base_figure(
        title=f"Top {top_n} Starting Trait Win Rates",
        x_title="Win Rate (%)",
        y_title="Trait",
        show_legend=False,
    )

    # Create hover text
    hover_text = [
        f"<b>{row['starting_trait']}</b><br>"
        f"Win Rate: {row['win_rate']:.1f}%<br>"
        f"Games: {int(row['games'])}<br>"
        f"Wins: {int(row['wins'])}"
        for _, row in df_top.iterrows()
    ]

    # Color bars based on win rate (green for high, red for low)
    colors = [
        f"rgb({int(255 * (1 - rate/100))}, {int(200 * rate/100)}, 50)"
        for rate in df_top["win_rate"]
    ]

    fig.add_trace(
        go.Bar(
            x=df_top["win_rate"],
            y=df_top["starting_trait"],
            orientation="h",
            marker=dict(color=colors),
            text=[f"{rate:.1f}%" for rate in df_top["win_rate"]],
            textposition="auto",
            hovertemplate="%{hovertext}<extra></extra>",
            hovertext=hover_text,
        )
    )

    fig.update_layout(
        xaxis={"range": [0, 100]},
        height=400,
    )

    return fig


def create_ruler_archetype_trait_combinations_chart(df: pd.DataFrame) -> go.Figure:
    """Create a horizontal bar chart showing popular archetype + trait combos.

    Displays the most frequently chosen starting ruler combinations.

    Args:
        df: DataFrame with columns: archetype, starting_trait, count

    Returns:
        Plotly figure with horizontal bar chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No ruler data available")

    # Create combined label
    df = df.copy()
    df["combo"] = df["archetype"] + " + " + df["starting_trait"]

    # Sort by count ascending (for horizontal bar display)
    df_sorted = df.sort_values("count", ascending=True)

    fig = create_base_figure(
        x_title="Times Chosen",
        y_title="Combination",
        show_legend=False,
    )

    # Color by archetype
    archetype_colors = {
        "Scholar": "#1f77b4",
        "Tactician": "#ff7f0e",
        "Commander": "#2ca02c",
        "Schemer": "#d62728",
        "Builder": "#9467bd",
        "Judge": "#8c564b",
        "Zealot": "#e377c2",
    }
    colors = [
        archetype_colors.get(row["archetype"], "#7f7f7f")
        for _, row in df_sorted.iterrows()
    ]

    # Create hover text
    hover_text = [
        f"<b>{row['combo']}</b><br>" f"Times Chosen: {int(row['count'])}"
        for _, row in df_sorted.iterrows()
    ]

    fig.add_trace(
        go.Bar(
            x=df_sorted["count"],
            y=df_sorted["combo"],
            orientation="h",
            marker=dict(color=colors),
            text=df_sorted["count"].astype(int),
            textposition="auto",
            hovertemplate="%{hovertext}<extra></extra>",
            hovertext=hover_text,
        )
    )

    fig.update_layout(height=400)

    return fig


def create_science_progression_chart(df: pd.DataFrame) -> go.Figure:
    """Create a line chart showing average science per turn across all matches.

    Shows median with shaded 25th-75th percentile band.

    Args:
        df: DataFrame with columns: turn_number, median, percentile_25, percentile_75

    Returns:
        Plotly figure with line chart and percentile band
    """
    if df.empty:
        return create_empty_chart_placeholder("No science data available")

    fig = create_base_figure(
        x_title="Turn Number",
        y_title="Science Per Turn",
        show_legend=False,
    )

    # Add shaded band (75th percentile upper bound)
    fig.add_trace(
        go.Scatter(
            x=df["turn_number"],
            y=df["percentile_75"],
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # Add shaded band (25th percentile lower bound with fill)
    fig.add_trace(
        go.Scatter(
            x=df["turn_number"],
            y=df["percentile_25"],
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(31, 119, 180, 0.2)",
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # Add median line
    fig.add_trace(
        go.Scatter(
            x=df["turn_number"],
            y=df["median"],
            mode="lines",
            line=dict(color="#1f77b4", width=2),
            name="Median",
            hovertemplate=(
                "<b>Turn %{x}</b><br>" "Median: %{y:.1f}<br>" "<extra></extra>"
            ),
        )
    )

    fig.update_layout(height=400)

    return fig


def create_yield_stacked_chart(
    rate_df: pd.DataFrame,
    cumulative_df: pd.DataFrame,
    yield_name: str,
    rate_color: str,
    cumulative_color: str,
    cumulative_log_scale: bool = False,
) -> go.Figure:
    """Create stacked subplots showing yield rate and cumulative production.

    Top chart shows yield per turn (rate), bottom shows cumulative total.
    Both share the x-axis for synchronized zoom/pan.

    Args:
        rate_df: DataFrame with columns: turn_number, median, percentile_25, percentile_75
        cumulative_df: DataFrame with same columns for cumulative data
        yield_name: Display name for the yield (e.g., "Science", "Food")
        rate_color: Hex color for rate line (e.g., "#1f77b4")
        cumulative_color: Hex color for cumulative line (e.g., "#2ca02c")
        cumulative_log_scale: If True, use log scale for the cumulative (bottom) chart

    Returns:
        Plotly figure with two vertically stacked subplots
    """
    if rate_df.empty and cumulative_df.empty:
        return create_empty_chart_placeholder(f"No {yield_name.lower()} data available")

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.5, 0.5],
        subplot_titles=("Per Turn", "Cumulative Total"),
        specs=[[{"secondary_y": True}], [{"secondary_y": True}]],
    )
    fig = apply_dark_theme(fig)

    # Convert hex to rgba for fill
    def hex_to_rgba(hex_color: str, alpha: float) -> str:
        hex_color = hex_color.lstrip("#")
        r, g, b = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
        return f"rgba({r}, {g}, {b}, {alpha})"

    # --- Top subplot: Rate ---
    if not rate_df.empty:
        fig.add_trace(
            go.Scatter(
                x=rate_df["turn_number"],
                y=rate_df["percentile_75"],
                mode="lines",
                line=dict(width=0),
                showlegend=False,
                hoverinfo="skip",
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=rate_df["turn_number"],
                y=rate_df["percentile_25"],
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                fillcolor=hex_to_rgba(rate_color, 0.2),
                showlegend=False,
                hoverinfo="skip",
            ),
            row=1,
            col=1,
        )
        # Build customdata for rich tooltips
        rate_customdata = list(zip(
            rate_df["percentile_25"],
            rate_df["percentile_75"],
            rate_df.get("min_value", [None] * len(rate_df)),
            rate_df.get("max_value", [None] * len(rate_df)),
            rate_df.get("avg_value", [None] * len(rate_df)),
            rate_df.get("std_dev", [None] * len(rate_df)),
            rate_df.get("sample_size", [None] * len(rate_df)),
        ))
        fig.add_trace(
            go.Scatter(
                x=rate_df["turn_number"],
                y=rate_df["median"],
                mode="lines",
                line=dict(color=rate_color, width=2),
                name="Per Turn",
                customdata=rate_customdata,
                hovertemplate=(
                    "<b>Turn %{x}</b><br>"
                    "Median: %{y:.1f}/turn<br>"
                    "IQR: %{customdata[0]:.1f} - %{customdata[1]:.1f}<br>"
                    "Range: %{customdata[2]:.1f} - %{customdata[3]:.1f}<br>"
                    "Mean: %{customdata[4]:.1f} (±%{customdata[5]:.1f})<br>"
                    "Games: %{customdata[6]}"
                    "<extra></extra>"
                ),
            ),
            row=1,
            col=1,
        )

        # Add sample size dashed line on secondary y-axis
        if "sample_size" in rate_df.columns:
            # Filter out early turns with incomplete data
            sample_df = rate_df[rate_df["turn_number"] >= 2].copy()
            fig.add_trace(
                go.Scatter(
                    x=sample_df["turn_number"],
                    y=sample_df["sample_size"],
                    mode="lines",
                    name="Sample Size",
                    line=dict(color="rgba(128, 128, 128, 0.5)", width=1, dash="dot"),
                    hovertemplate="Turn %{x}<br>Games: %{y}<extra></extra>",
                ),
                row=1,
                col=1,
                secondary_y=True,
            )

    # --- Bottom subplot: Cumulative ---
    if not cumulative_df.empty:
        fig.add_trace(
            go.Scatter(
                x=cumulative_df["turn_number"],
                y=cumulative_df["percentile_75"],
                mode="lines",
                line=dict(width=0),
                showlegend=False,
                hoverinfo="skip",
            ),
            row=2,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=cumulative_df["turn_number"],
                y=cumulative_df["percentile_25"],
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                fillcolor=hex_to_rgba(cumulative_color, 0.2),
                showlegend=False,
                hoverinfo="skip",
            ),
            row=2,
            col=1,
        )
        # Build customdata for rich tooltips
        cumulative_customdata = list(zip(
            cumulative_df["percentile_25"],
            cumulative_df["percentile_75"],
            cumulative_df.get("min_value", [None] * len(cumulative_df)),
            cumulative_df.get("max_value", [None] * len(cumulative_df)),
            cumulative_df.get("avg_value", [None] * len(cumulative_df)),
            cumulative_df.get("std_dev", [None] * len(cumulative_df)),
            cumulative_df.get("sample_size", [None] * len(cumulative_df)),
        ))
        fig.add_trace(
            go.Scatter(
                x=cumulative_df["turn_number"],
                y=cumulative_df["median"],
                mode="lines",
                line=dict(color=cumulative_color, width=2),
                name="Cumulative",
                customdata=cumulative_customdata,
                hovertemplate=(
                    "<b>Turn %{x}</b><br>"
                    "Median: %{y:,.0f}<br>"
                    "IQR: %{customdata[0]:,.0f} - %{customdata[1]:,.0f}<br>"
                    "Range: %{customdata[2]:,.0f} - %{customdata[3]:,.0f}<br>"
                    "Mean: %{customdata[4]:,.0f} (±%{customdata[5]:,.0f})<br>"
                    "Games: %{customdata[6]}"
                    "<extra></extra>"
                ),
            ),
            row=2,
            col=1,
        )

        # Add sample size dashed line on secondary y-axis
        if "sample_size" in cumulative_df.columns:
            sample_df = cumulative_df[cumulative_df["turn_number"] >= 2].copy()
            fig.add_trace(
                go.Scatter(
                    x=sample_df["turn_number"],
                    y=sample_df["sample_size"],
                    mode="lines",
                    name="Sample Size",
                    line=dict(color="rgba(128, 128, 128, 0.5)", width=1, dash="dot"),
                    hovertemplate="Turn %{x}<br>Games: %{y}<extra></extra>",
                ),
                row=2,
                col=1,
                secondary_y=True,
            )

    fig.update_layout(
        height=500,
        showlegend=False,
        margin=dict(t=30, b=40, l=60, r=60),
    )

    for annotation in fig["layout"]["annotations"]:
        annotation["font"] = dict(size=11, color="#666")

    fig.update_xaxes(title_text="Turn Number", row=2, col=1)
    fig.update_yaxes(title_text=f"{yield_name}/Turn", row=1, col=1)

    # Apply log scale to cumulative chart if requested (primary y-axis only)
    if cumulative_log_scale:
        fig.update_yaxes(
            title_text=f"Total {yield_name} (log)",
            type="log",
            row=2,
            col=1,
            secondary_y=False,
        )
    else:
        fig.update_yaxes(title_text=f"Total {yield_name}", row=2, col=1, secondary_y=False)

    # Configure secondary y-axes for sample size (both subplots use same scale)
    max_sample = 0
    if not rate_df.empty and "sample_size" in rate_df.columns:
        max_sample = max(max_sample, rate_df["sample_size"].max())
    if not cumulative_df.empty and "sample_size" in cumulative_df.columns:
        max_sample = max(max_sample, cumulative_df["sample_size"].max())

    if max_sample > 0:
        fig.update_yaxes(
            title_text="Games",
            showgrid=False,
            range=[0, max_sample * 1.1],
            row=1,
            col=1,
            secondary_y=True,
        )
        fig.update_yaxes(
            title_text="Games",
            showgrid=False,
            range=[0, max_sample * 1.1],
            row=2,
            col=1,
            secondary_y=True,
        )

    return fig


def create_orders_progression_chart(df: pd.DataFrame) -> go.Figure:
    """Create a line chart showing average orders per turn across all matches.

    Shows median with shaded 25th-75th percentile band.

    Args:
        df: DataFrame with columns: turn_number, median, percentile_25, percentile_75

    Returns:
        Plotly figure with line chart and percentile band
    """
    if df.empty:
        return create_empty_chart_placeholder("No orders data available")

    fig = create_base_figure(
        x_title="Turn Number",
        y_title="Orders Per Turn",
        show_legend=False,
    )

    # Add shaded band (75th percentile upper bound)
    fig.add_trace(
        go.Scatter(
            x=df["turn_number"],
            y=df["percentile_75"],
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # Add shaded band (25th percentile lower bound with fill)
    fig.add_trace(
        go.Scatter(
            x=df["turn_number"],
            y=df["percentile_25"],
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(255, 127, 14, 0.2)",
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # Add median line
    fig.add_trace(
        go.Scatter(
            x=df["turn_number"],
            y=df["median"],
            mode="lines",
            line=dict(color="#ff7f0e", width=2),
            name="Median",
            hovertemplate=(
                "<b>Turn %{x}</b><br>" "Median: %{y:.1f}<br>" "<extra></extra>"
            ),
        )
    )

    fig.update_layout(height=400)

    return fig


def create_military_progression_chart(df: pd.DataFrame) -> go.Figure:
    """Create a line chart showing average military score per turn across all matches.

    Shows median with shaded 25th-75th percentile band.

    Args:
        df: DataFrame with columns: turn_number, median, percentile_25, percentile_75

    Returns:
        Plotly figure with line chart and percentile band
    """
    if df.empty:
        return create_empty_chart_placeholder("No military data available")

    fig = create_base_figure(
        x_title="Turn Number",
        y_title="Military Score Per Turn",
        show_legend=False,
    )

    # Add shaded band (75th percentile upper bound)
    fig.add_trace(
        go.Scatter(
            x=df["turn_number"],
            y=df["percentile_75"],
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # Add shaded band (25th percentile lower bound with fill)
    fig.add_trace(
        go.Scatter(
            x=df["turn_number"],
            y=df["percentile_25"],
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(44, 160, 44, 0.2)",
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # Add median line
    fig.add_trace(
        go.Scatter(
            x=df["turn_number"],
            y=df["median"],
            mode="lines",
            line=dict(color="#2ca02c", width=2),
            name="Median",
            hovertemplate=(
                "<b>Turn %{x}</b><br>" "Median: %{y:.0f}<br>" "<extra></extra>"
            ),
        )
    )

    fig.update_layout(height=400)

    return fig


def create_legitimacy_progression_chart(df: pd.DataFrame) -> go.Figure:
    """Create a line chart showing average legitimacy per turn across all matches.

    Shows median with shaded 25th-75th percentile band.

    Args:
        df: DataFrame with columns: turn_number, median, percentile_25, percentile_75

    Returns:
        Plotly figure with line chart and percentile band
    """
    if df.empty:
        return create_empty_chart_placeholder("No legitimacy data available")

    fig = create_base_figure(
        x_title="Turn Number",
        y_title="Legitimacy Per Turn",
        show_legend=False,
    )

    # Add shaded band (75th percentile upper bound)
    fig.add_trace(
        go.Scatter(
            x=df["turn_number"],
            y=df["percentile_75"],
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # Add shaded band (25th percentile lower bound with fill)
    fig.add_trace(
        go.Scatter(
            x=df["turn_number"],
            y=df["percentile_25"],
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(214, 39, 40, 0.2)",
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # Add median line
    fig.add_trace(
        go.Scatter(
            x=df["turn_number"],
            y=df["median"],
            mode="lines",
            line=dict(color="#d62728", width=2),
            name="Median",
            hovertemplate=(
                "<b>Turn %{x}</b><br>" "Median: %{y:.0f}<br>" "<extra></extra>"
            ),
        )
    )

    fig.update_layout(height=400)

    return fig


def create_city_founding_timeline_chart(df: pd.DataFrame) -> go.Figure:
    """Create a timeline chart showing city founding events.

    Shows when each player founded cities, with markers on a timeline
    for easy comparison of expansion timing.

    Args:
        df: DataFrame with columns: player_name, civilization, turn_number, city_name
            (from get_city_founding_timeline())

    Returns:
        Plotly figure with scatter plot timeline
    """
    if df.empty:
        return create_empty_chart_placeholder(
            "No city founding data available for this match"
        )

    # Create base figure
    fig = create_base_figure(
        title="",
        x_title="Turn Number",
        y_title="Player",
        height=400,
    )

    # Get unique players for y-axis positioning
    players = df["player_name"].unique()
    player_y_positions = {player: idx for idx, player in enumerate(players)}

    # Add trace for each player
    for player in players:
        player_data = df[df["player_name"] == player]
        y_pos = player_y_positions[player]

        # Get color based on civilization
        civ = player_data["civilization"].iloc[0] if not player_data.empty else None
        color = get_nation_color(civ) if civ else Config.PRIMARY_COLORS[y_pos]

        fig.add_trace(
            go.Scatter(
                x=player_data["turn_number"],
                y=[y_pos] * len(player_data),
                mode="markers",
                name=player,
                marker=dict(
                    symbol="circle",
                    color=color,
                    size=12,
                    line=dict(width=1, color="white"),
                ),
                text=player_data["city_name"],
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "Turn %{x}<br>"
                    "City: %{text}<br>"
                    "<extra></extra>"
                ),
            )
        )

    # Configure y-axis to show player names
    fig.update_layout(
        yaxis=dict(
            tickmode="array",
            tickvals=list(player_y_positions.values()),
            ticktext=list(player_y_positions.keys()),
        ),
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
        ),
    )

    return fig


def create_cumulative_city_count_chart(
    df: pd.DataFrame,
    total_turns: Optional[int] = None,
    player_colors: Optional[Dict[str, str]] = None,
) -> go.Figure:
    """Create a cumulative city count line chart.

    Shows two lines comparing cumulative city count over time,
    making it easy to see who's ahead at any point.

    Args:
        df: DataFrame with columns: player_name, civilization, turn_number, city_name
            (from get_city_founding_timeline())
        total_turns: Total turns in the match (to extend lines to end)
        player_colors: Optional dict mapping player names to hex colors

    Returns:
        Plotly figure with cumulative line chart
    """
    if df.empty:
        return create_empty_chart_placeholder(
            "No city founding data available for this match"
        )

    # Create base figure
    fig = create_base_figure(
        title="",
        x_title="Turn Number",
        y_title="Cumulative Cities",
        height=400,
    )

    # Calculate cumulative counts for each player
    players = df["player_name"].unique()

    for player in players:
        player_data = df[df["player_name"] == player].copy()
        player_data = player_data.sort_values("turn_number")

        # Create cumulative count
        player_data["cumulative_count"] = range(1, len(player_data) + 1)

        # Use player_colors if provided, otherwise fall back to nation color
        if player_colors and player in player_colors:
            color = player_colors[player]
        else:
            civ = player_data["civilization"].iloc[0] if not player_data.empty else None
            color = get_nation_color(civ) if civ else Config.PRIMARY_COLORS[0]

        # Extend line to total_turns if provided
        if total_turns and player_data["turn_number"].iloc[-1] < total_turns:
            # Add a point at the end of the game with the same count
            final_count = player_data["cumulative_count"].iloc[-1]
            extension_df = pd.DataFrame(
                {
                    "turn_number": [total_turns],
                    "cumulative_count": [final_count],
                }
            )
            player_data = pd.concat([player_data, extension_df], ignore_index=True)

        fig.add_trace(
            go.Scatter(
                x=player_data["turn_number"],
                y=player_data["cumulative_count"],
                mode="lines+markers",
                name=player,
                line=dict(color=color, width=2),
                marker=dict(size=8, color=color),
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "Turn %{x}<br>"
                    "Cities: %{y}<br>"
                    "<extra></extra>"
                ),
            )
        )

    # Configure layout
    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
        ),
    )

    return fig


def create_city_founding_scatter_jitter_chart(
    df: pd.DataFrame,
    player_colors: Optional[Dict[str, str]] = None,
) -> go.Figure:
    """Create a scatter plot with jitter showing city founding events.

    Shows individual cities as points with slight vertical offset (jitter)
    to prevent overlapping. Includes city names on hover.

    Args:
        df: DataFrame with columns: player_name, civilization, turn_number, city_name
            (from get_city_founding_timeline())
        player_colors: Optional dict mapping player names to hex colors

    Returns:
        Plotly figure with scatter plot
    """
    if df.empty:
        return create_empty_chart_placeholder(
            "No city founding data available for this match"
        )

    # Create base figure
    fig = create_base_figure(
        title="",
        x_title="Turn Number",
        y_title="Player",
        height=400,
    )

    # Get unique players for y-axis positioning
    players = df["player_name"].unique()
    player_y_positions = {player: idx for idx, player in enumerate(players)}

    # Add trace for each player
    for player in players:
        player_data = df[df["player_name"] == player].copy()
        y_pos = player_y_positions[player]

        # Use player_colors if provided, otherwise fall back to nation color
        if player_colors and player in player_colors:
            color = player_colors[player]
        else:
            civ = player_data["civilization"].iloc[0] if not player_data.empty else None
            color = get_nation_color(civ) if civ else Config.PRIMARY_COLORS[y_pos]

        # Add jitter: small random offset to prevent exact overlap
        import numpy as np

        np.random.seed(42)  # For consistent jitter
        jitter = np.random.uniform(-0.15, 0.15, len(player_data))
        y_values = [y_pos + j for j in jitter]

        fig.add_trace(
            go.Scatter(
                x=player_data["turn_number"],
                y=y_values,
                mode="markers+text",
                name=player,
                marker=dict(
                    symbol="circle",
                    color=color,
                    size=10,
                    line=dict(width=1, color="white"),
                ),
                text=player_data["city_name"],
                textposition="middle right",
                textfont=dict(size=9),
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "Turn %{x}<br>"
                    "City: %{text}<br>"
                    "<extra></extra>"
                ),
            )
        )

    # Add vertical lines every 10 turns
    max_turn = df["turn_number"].max()
    for turn in range(10, int(max_turn) + 1, 10):
        fig.add_vline(
            x=turn,
            line_dash="dash",
            line_color="rgba(128, 128, 128, 0.3)",
            line_width=1,
        )

    # Configure y-axis to show player names
    fig.update_layout(
        yaxis=dict(
            tickmode="array",
            tickvals=list(player_y_positions.values()),
            ticktext=list(player_y_positions.keys()),
            range=[-0.5, len(players) - 0.5],  # Add padding
            showgrid=True,
            gridcolor=CHART_THEME["gridcolor"],
            zeroline=False,  # Hide the prominent zero line
        ),
        xaxis=dict(
            zeroline=False,  # Hide x-axis zero line as well
        ),
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
        ),
    )

    return fig


def create_hexagonal_map(
    df: pd.DataFrame,
    map_width: int = 46,
) -> go.Figure:
    """Create hexagonal map visualization.

    Displays tiles as hexagons colored by owner, with terrain shown
    for unowned tiles.

    Args:
        df: DataFrame with columns [x_coordinate, y_coordinate, terrain_type,
            owner_player_id, player_name, civilization]
        map_width: Map width for calculating hex positions

    Returns:
        Plotly figure with hexagonal map
    """
    if df.empty:
        return create_empty_chart_placeholder("No map data available")

    # Hex grid constants
    HEX_WIDTH = 1.0
    HEX_HEIGHT = 0.866  # sqrt(3)/2 for regular hexagon

    # Calculate hex positions
    # Offset rows (even rows shifted right by 0.5 hex width)
    df = df.copy()
    df["hex_x"] = df["x_coordinate"] * HEX_WIDTH + (df["y_coordinate"] % 2) * (
        HEX_WIDTH / 2
    )
    df["hex_y"] = df["y_coordinate"] * HEX_HEIGHT

    # Create figure
    fig = go.Figure()

    # Define color scheme
    # Owned tiles: use player colors
    # Unowned tiles: use terrain colors
    terrain_colors = {
        "TERRAIN_WATER": "#4A90E2",  # Blue
        "TERRAIN_GRASSLAND": "#7CB342",  # Green
        "TERRAIN_DESERT": "#F4E04D",  # Yellow
        "TERRAIN_ARID": "#D4A574",  # Tan
        "TERRAIN_SCRUB": "#9CCC65",  # Light green
        "TERRAIN_TUNDRA": "#B0BEC5",  # Grey-blue
        "TERRAIN_SNOW": "#ECEFF1",  # White-grey
    }

    # Get unique owners (excluding NULL/unowned)
    owned_tiles = df[df["owner_player_id"].notna()]
    unowned_tiles = df[df["owner_player_id"].isna()]

    # Plot owned tiles by player
    if not owned_tiles.empty:
        # Build player colors dict based on civilizations (for same-nation handling)
        player_civs = (
            owned_tiles.groupby("player_name")["civilization"].first().to_dict()
        )
        players = list(player_civs.keys())

        # Get colors using map colors (original game colors, beige Carthage not black)
        from tournament_visualizer.nation_colors import get_nation_map_color

        player_colors: Dict[str, str] = {}
        if len(players) >= 2:
            # Check if same nation - if so, player 2 gets a different color
            civ1 = player_civs.get(players[0])
            civ2 = player_civs.get(players[1])
            player_colors[players[0]] = (
                get_nation_map_color(civ1) if civ1 else "#808080"
            )
            if civ1 and civ2 and civ1.upper() == civ2.upper():
                # Same nation - use green for player 2
                player_colors[players[1]] = "#228B22"
            else:
                player_colors[players[1]] = (
                    get_nation_map_color(civ2) if civ2 else "#808080"
                )
        elif len(players) == 1:
            civ = player_civs.get(players[0])
            player_colors[players[0]] = (
                get_nation_map_color(civ) if civ else "#808080"
            )

        for i, (player_id, player_data) in enumerate(
            owned_tiles.groupby("owner_player_id")
        ):
            player_name = player_data["player_name"].iloc[0]
            color = player_colors.get(
                player_name, Config.PRIMARY_COLORS[int(i) % len(Config.PRIMARY_COLORS)]
            )

            fig.add_trace(
                go.Scatter(
                    x=player_data["hex_x"],
                    y=player_data["hex_y"],
                    mode="markers",
                    name=player_name,
                    marker=dict(
                        color=color,
                        size=20,
                        symbol="hexagon",
                        line=dict(color="white", width=1),
                    ),
                    hovertemplate=(
                        f"<b>{player_name}</b><br>"
                        "Position: (%{customdata[0]}, %{customdata[1]})<br>"
                        "Terrain: %{customdata[2]}<br>"
                        "<extra></extra>"
                    ),
                    customdata=player_data[
                        ["x_coordinate", "y_coordinate", "terrain_type"]
                    ].values,
                )
            )

    # Plot unowned tiles by terrain
    if not unowned_tiles.empty:
        for terrain, terrain_data in unowned_tiles.groupby("terrain_type"):
            color = terrain_colors.get(terrain, "#CCCCCC")  # Default grey

            # Clean up terrain name for display
            terrain_display = (
                terrain.replace("TERRAIN_", "").title() if terrain else "Unknown"
            )

            fig.add_trace(
                go.Scatter(
                    x=terrain_data["hex_x"],
                    y=terrain_data["hex_y"],
                    mode="markers",
                    name=f"Unowned - {terrain_display}",
                    marker=dict(
                        color=color,
                        size=20,
                        symbol="hexagon",
                        opacity=0.5,
                        line=dict(color="white", width=1),
                    ),
                    hovertemplate=(
                        f"<b>Unowned</b><br>"
                        f"Terrain: {terrain_display}<br>"
                        "Position: (%{customdata[0]}, %{customdata[1]})<br>"
                        "<extra></extra>"
                    ),
                    customdata=terrain_data[["x_coordinate", "y_coordinate"]].values,
                )
            )

    # Update layout for hex grid
    fig.update_layout(
        xaxis=dict(
            showgrid=False,
            showticklabels=False,
            zeroline=False,
            scaleanchor="y",
            scaleratio=1,
        ),
        yaxis=dict(
            showgrid=False,
            showticklabels=False,
            zeroline=False,
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=CHART_THEME["font_color"]),
        hovermode="closest",
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            font=dict(color=CHART_THEME["font_color"]),
        ),
        hoverlabel=dict(
            bgcolor=CHART_THEME["hoverlabel_bgcolor"],
            bordercolor=CHART_THEME["hoverlabel_bordercolor"],
            font=dict(color=CHART_THEME["hoverlabel_font_color"]),
        ),
        height=700,
    )

    return fig


def create_tournament_expansion_timeline_chart(df: pd.DataFrame) -> go.Figure:
    """Create line chart showing cumulative city expansion over time for all players.

    Shows how quickly players expanded throughout the tournament. Each line represents
    one player's city count growth.

    Args:
        df: DataFrame from get_tournament_expansion_timeline() with columns:
            player_name, civilization, founded_turn, cumulative_cities

    Returns:
        Plotly figure with line chart (one trace per player)
    """
    if df.empty:
        return create_empty_chart_placeholder("No expansion data available")

    fig = create_base_figure(
        title="",  # Card header provides title
        show_legend=True,
        x_title="Turn",
        y_title="Cumulative Cities",
    )

    # Group by player and create one trace per player
    for (player_name, civ), group in df.groupby(["player_name", "civilization"]):
        # Sort by turn to ensure proper line drawing
        group = group.sort_values("founded_turn")

        # Get civilization color
        color = get_nation_color(civ)

        fig.add_trace(
            go.Scatter(
                x=group["founded_turn"],
                y=group["cumulative_cities"],
                mode="lines+markers",
                name=f"{player_name} ({civ})",
                line=dict(color=color, width=2),
                marker=dict(size=6, color=color),
                hovertemplate=(
                    f"<b>{player_name}</b><br>"
                    "Turn: %{x}<br>"
                    "Total Cities: %{y}<br>"
                    "<extra></extra>"
                ),
            )
        )

    # Update layout for better readability
    fig.update_layout(
        hovermode="closest",
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
    )

    return fig


def create_tournament_founding_distribution_chart(df: pd.DataFrame) -> go.Figure:
    """Create bar chart showing distribution of city foundings by turn range.

    Shows when most cities were founded (early, mid, or late game).

    Args:
        df: DataFrame from get_tournament_city_founding_distribution() with columns:
            turn_range, city_count, percentage

    Returns:
        Plotly figure with bar chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No city founding data available")

    fig = create_base_figure(
        title="",
        show_legend=False,
        x_title="Turn Range",
        y_title="Cities Founded",
    )

    fig.add_trace(
        go.Bar(
            x=df["turn_range"],
            y=df["city_count"],
            text=[
                f"{count}<br>({pct}%)"
                for count, pct in zip(df["city_count"], df["percentage"])
            ],
            textposition="outside",
            marker_color=Config.PRIMARY_COLORS[0],
            hovertemplate=("Turn Range: %{x}<br>" "Cities: %{y}<br>" "<extra></extra>"),
        )
    )

    fig.update_layout(
        xaxis=dict(type="category"),  # Preserve order
        yaxis=dict(rangemode="tozero"),
    )

    return fig


def create_tournament_production_strategies_chart(df: pd.DataFrame) -> go.Figure:
    """Create horizontal stacked bar chart showing production strategies.

    Shows unit production (settlers, workers, disciples, military) and city projects.

    Args:
        df: DataFrame from get_tournament_production_strategies() with columns:
            player_name, civilization, settlers, workers, disciples, military, projects, total_production

    Returns:
        Plotly figure with horizontal stacked bar chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No production data available")

    # Sort by total production descending (biggest producers at top)
    df = df.sort_values("total_production", ascending=True)  # ascending=True for horizontal bars

    fig = create_base_figure(
        title="",
        show_legend=True,
        x_title="Production Count",
        y_title="Player",
    )

    # Create y-axis labels with civilization
    y_labels = [
        f"{row['player_name']} ({row['civilization']})" for _, row in df.iterrows()
    ]

    # Add traces for each production category (horizontal bars)
    fig.add_trace(
        go.Bar(
            y=y_labels,
            x=df["settlers"],
            name="Settlers",
            orientation="h",
            marker_color="#FF6B6B",
            hovertemplate="Settlers: %{x}<extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            y=y_labels,
            x=df["workers"],
            name="Workers",
            orientation="h",
            marker_color="#4ECDC4",
            hovertemplate="Workers: %{x}<extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            y=y_labels,
            x=df["disciples"],
            name="Disciples",
            orientation="h",
            marker_color="#FFE66D",
            hovertemplate="Disciples: %{x}<extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            y=y_labels,
            x=df["military"],
            name="Military",
            orientation="h",
            marker_color="#E74C3C",
            hovertemplate="Military: %{x}<extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            y=y_labels,
            x=df["projects"],
            name="Projects",
            orientation="h",
            marker_color="#95E1D3",
            hovertemplate="Projects: %{x}<extra></extra>",
        )
    )

    # Calculate dynamic height based on number of players (40px per player for readability)
    num_players = len(df)
    chart_height = max(800, num_players * 40)

    fig.update_layout(
        barmode="stack",
        height=chart_height,
        yaxis=dict(
            tickmode="linear",
            automargin=True,
        ),
        margin=dict(l=200, r=50, t=50, b=50),  # Extra left margin for player names
        legend=dict(
            orientation="h",
            yanchor="top",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )

    return fig


def create_tournament_project_priorities_chart(df: pd.DataFrame) -> go.Figure:
    """Create grouped bar chart showing city project priorities.

    Shows which projects players focused on (forums, festivals, etc).

    Args:
        df: DataFrame from get_tournament_project_priorities() with columns:
            player_name, civilization, project_type, project_count

    Returns:
        Plotly figure with grouped bar chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No project data available")

    # Get top 5 most common projects across all players
    top_projects = (
        df.groupby("project_type")["project_count"].sum().nlargest(5).index.tolist()
    )

    # Filter to only top projects
    df_filtered = df[df["project_type"].isin(top_projects)].copy()

    if df_filtered.empty:
        return create_empty_chart_placeholder("No project data available")

    fig = create_base_figure(
        title="",
        show_legend=True,
        x_title="Player",
        y_title="Projects Completed",
    )

    # Create x-axis labels
    players = df_filtered[["player_name", "civilization"]].drop_duplicates()
    x_labels = [
        f"{row['player_name']}<br>({row['civilization']})"
        for _, row in players.iterrows()
    ]

    # Add trace for each project type
    for project_type in top_projects:
        project_data = df_filtered[df_filtered["project_type"] == project_type]

        # Merge with all players to show 0 for players who didn't build this
        y_values = []
        for _, player in players.iterrows():
            player_project = project_data[
                (project_data["player_name"] == player["player_name"])
                & (project_data["civilization"] == player["civilization"])
            ]
            count = (
                player_project["project_count"].iloc[0]
                if not player_project.empty
                else 0
            )
            y_values.append(count)

        # Clean up project name for display
        display_name = project_type.replace("PROJECT_", "").replace("_", " ").title()

        fig.add_trace(
            go.Bar(
                x=x_labels,
                y=y_values,
                name=display_name,
                hovertemplate=f"{display_name}: %{{y}}<extra></extra>",
            )
        )

    fig.update_layout(
        barmode="group",
        xaxis=dict(tickangle=-45),
    )

    return fig


def create_tournament_conquest_summary_chart(df: pd.DataFrame) -> go.Figure:
    """Create table showing city conquests.

    Displays rare but dramatic city conquest events.

    Args:
        df: DataFrame from get_tournament_conquest_summary() with columns:
            conqueror_name, conqueror_civ, original_founder_name,
            original_founder_civ, city_name, founded_turn, match_id

    Returns:
        Plotly figure with table
    """
    if df.empty:
        return create_empty_chart_placeholder(
            "No conquests occurred in the tournament.<br>"
            "All cities remained with their original founders!"
        )

    # Clean up city names
    df = df.copy()
    df["city_name"] = df["city_name"].str.replace("CITYNAME_", "")

    fig = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=[
                        "City Conquered",
                        "Original Founder",
                        "Conquered By",
                        "Founded Turn",
                        "Match",
                    ],
                    fill_color=CHART_THEME["hoverlabel_bgcolor"],
                    font=dict(color=CHART_THEME["font_color"], size=12),
                    align="left",
                ),
                cells=dict(
                    values=[
                        df["city_name"],
                        [
                            f"{name} ({civ})"
                            for name, civ in zip(
                                df["original_founder_name"], df["original_founder_civ"]
                            )
                        ],
                        [
                            f"{name} ({civ})"
                            for name, civ in zip(
                                df["conqueror_name"], df["conqueror_civ"]
                            )
                        ],
                        df["founded_turn"],
                        df["match_id"],
                    ],
                    fill_color=CHART_THEME["paper_bgcolor"],
                    font=dict(color=CHART_THEME["font_color"], size=11),
                    align="left",
                    height=30,
                ),
            )
        ]
    )

    fig.update_layout(
        paper_bgcolor=CHART_THEME["paper_bgcolor"],
        height=max(200, len(df) * 35 + 50),  # Dynamic height based on rows
    )

    return fig


def _create_science_progression_line_chart(
    df: pd.DataFrame, result_filter: Optional[str] = None
) -> go.Figure:
    """Create line chart showing science progression for winners vs losers.

    Args:
        df: DataFrame with turn-by-turn science data (from get_science_win_correlation)
            Expected columns: turn_number, avg_science_winners, avg_science_losers,
                            p25_winners, p75_winners, p25_losers, p75_losers,
                            winner_count, loser_count
        result_filter: Filter to show only 'winners' or 'losers' line, or both if None/'all'

    Returns:
        Plotly figure with lines and shaded percentile bands
    """
    if df.empty:
        return create_empty_chart_placeholder("No science data available")

    # Determine which lines to show
    show_winners = result_filter in (None, "all", "winners")
    show_losers = result_filter in (None, "all", "losers")

    # Create base figure with secondary y-axis
    fig = create_base_figure(
        x_title="Turn Number",
        y_title="Average Science Per Turn",
        height=400,
        show_legend=True,
    )

    # Add shaded band for losers (25th-75th percentile)
    if show_losers:
        fig.add_trace(
            go.Scatter(
                x=df["turn_number"],
                y=df["p75_losers"],
                mode="lines",
                line=dict(width=0),
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["turn_number"],
                y=df["p25_losers"],
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                fillcolor="rgba(214, 39, 40, 0.2)",  # Red with transparency
                showlegend=False,
                hoverinfo="skip",
            )
        )

    # Add shaded band for winners (25th-75th percentile)
    if show_winners:
        fig.add_trace(
            go.Scatter(
                x=df["turn_number"],
                y=df["p75_winners"],
                mode="lines",
                line=dict(width=0),
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["turn_number"],
                y=df["p25_winners"],
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                fillcolor="rgba(44, 160, 44, 0.2)",  # Green with transparency
                showlegend=False,
                hoverinfo="skip",
            )
        )

    # Add line for losers (on top of shaded band)
    if show_losers:
        fig.add_trace(
            go.Scatter(
                x=df["turn_number"],
                y=df["avg_science_losers"],
                mode="lines",
                name="Losers (avg)",
                line=dict(color="#d62728", width=2),
                hovertemplate="Turn %{x}<br>Avg Science: %{y:.1f}<extra></extra>",
            )
        )

    # Add line for winners (on top of shaded band)
    if show_winners:
        fig.add_trace(
            go.Scatter(
                x=df["turn_number"],
                y=df["avg_science_winners"],
                mode="lines",
                name="Winners (avg)",
                line=dict(color="#2ca02c", width=2),
                hovertemplate="Turn %{x}<br>Avg Science: %{y:.1f}<extra></extra>",
            )
        )

    # Add sample size line on secondary y-axis
    # Filter out turn 1 which often has incomplete data
    sample_df = df[df["turn_number"] >= 2].copy()
    if show_winners and show_losers:
        sample_size = sample_df[["winner_count", "loser_count"]].max(axis=1)
    elif show_winners:
        sample_size = sample_df["winner_count"]
    else:
        sample_size = sample_df["loser_count"]
    fig.add_trace(
        go.Scatter(
            x=sample_df["turn_number"],
            y=sample_size,
            mode="lines",
            name="Sample Size",
            line=dict(color="rgba(128, 128, 128, 0.5)", width=1, dash="dot"),
            yaxis="y2",
            hovertemplate="Turn %{x}<br>Games: %{y}<extra></extra>",
        )
    )

    # Add secondary y-axis for sample size with explicit range
    max_sample = max(df["winner_count"].max(), df["loser_count"].max())
    fig.update_layout(
        yaxis2=dict(
            title="Number of Games",
            overlaying="y",
            side="right",
            showgrid=False,
            range=[0, max_sample * 1.1],  # Add 10% padding at top
        ),
        legend=dict(
            x=1.0,
            y=1.4,
            xanchor="right",
            yanchor="top",
            bgcolor=CHART_THEME["legend_bgcolor"],
            bordercolor=CHART_THEME["legend_bordercolor"],
            borderwidth=1,
        ),
    )

    return fig


def create_science_per_turn_correlation_chart(
    df: pd.DataFrame, result_filter: Optional[str] = None
) -> go.Figure:
    """Create line chart showing science progression for winners vs losers over turns.

    Args:
        df: DataFrame from get_science_win_correlation()
        result_filter: Filter to show only 'winners' or 'losers' line, or both if None/'all'

    Returns:
        Plotly figure with turn-by-turn science progression
    """
    return _create_science_progression_line_chart(df, result_filter)


# =============================================================================
# Unit Composition Charts
# =============================================================================

# Define role colors for consistent visualization across all unit charts
ROLE_COLORS = {
    "infantry": "#4a90d9",    # Blue
    "ranged": "#d94a4a",      # Red
    "cavalry": "#d9a54a",     # Gold
    "siege": "#8b4513",       # Brown
    "naval": "#20b2aa",       # Teal
    "settler": "#228b22",     # Forest green
    "worker": "#daa520",      # Goldenrod
    "scout": "#9370db",       # Purple
    "religious": "#ff69b4",   # Pink
    "unknown": "#808080",     # Gray
}


def create_units_stacked_bar_chart(df: pd.DataFrame) -> go.Figure:
    """Create stacked bar chart showing army composition by role.

    Each player is a bar with segments colored by unit role (infantry, ranged, etc.).

    Args:
        df: DataFrame from get_match_units_produced()

    Returns:
        Plotly figure with stacked bar chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No unit data available")

    # Aggregate by player and role
    role_totals = df.groupby(["player_name", "role"])["count"].sum().reset_index()

    # Pivot to get roles as columns
    pivot_data = role_totals.pivot(
        index="player_name", columns="role", values="count"
    ).fillna(0)

    fig = create_base_figure(x_title="Player", y_title="Units Produced")

    # Add a bar trace for each role
    for role in pivot_data.columns:
        fig.add_trace(
            go.Bar(
                name=role.title(),
                x=pivot_data.index,
                y=pivot_data[role],
                marker_color=ROLE_COLORS.get(role, "#808080"),
            )
        )

    fig.update_layout(
        barmode="stack",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )

    return fig


def create_units_grouped_bar_chart(
    df: pd.DataFrame,
    player_colors: Optional[Dict[str, str]] = None,
) -> go.Figure:
    """Create grouped bar chart comparing unit types across players.

    Unit types on x-axis, bars grouped by player.

    Args:
        df: DataFrame from get_match_units_produced()
        player_colors: Optional dict mapping player names to hex colors

    Returns:
        Plotly figure with grouped bar chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No unit data available")

    # Get top 10 most-produced unit types across all players
    top_units = df.groupby("unit_name")["count"].sum().nlargest(10).index.tolist()
    df_filtered = df[df["unit_name"].isin(top_units)]

    fig = create_base_figure(x_title="Unit Type", y_title="Units Produced")

    players = df_filtered["player_name"].unique()
    for i, player in enumerate(players):
        player_data = df_filtered[df_filtered["player_name"] == player]
        # Ensure all unit types are represented
        unit_counts = {
            unit: player_data[player_data["unit_name"] == unit]["count"].sum()
            for unit in top_units
        }

        # Use player_colors if provided, otherwise fall back to PRIMARY_COLORS
        if player_colors and player in player_colors:
            color = player_colors[player]
        else:
            color = Config.PRIMARY_COLORS[i % len(Config.PRIMARY_COLORS)]

        fig.add_trace(
            go.Bar(
                name=player,
                x=list(unit_counts.keys()),
                y=list(unit_counts.values()),
                marker_color=color,
            )
        )

    fig.update_layout(
        barmode="group",
        xaxis_tickangle=-45,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )

    return fig


def create_units_waffle_chart(df: pd.DataFrame) -> go.Figure:
    """Create waffle chart showing unit composition as colored grid.

    Each square represents one unit, colored by role.

    Args:
        df: DataFrame from get_match_units_produced()

    Returns:
        Plotly figure with waffle chart (using heatmap)
    """
    if df.empty:
        return create_empty_chart_placeholder("No unit data available")

    # Create a subplot for each player
    players = df["player_name"].unique()
    n_players = len(players)

    fig = make_subplots(
        rows=1,
        cols=n_players,
        subplot_titles=[p for p in players],
        horizontal_spacing=0.05,
    )
    fig = apply_dark_theme(fig)

    # Map roles to numeric values for coloring
    role_to_num = {role: i for i, role in enumerate(ROLE_COLORS.keys())}

    for col_idx, player in enumerate(players, 1):
        player_data = df[df["player_name"] == player]

        # Create flat list of units with their roles
        units = []
        for _, row in player_data.iterrows():
            units.extend([row["role"]] * row["count"])

        if not units:
            continue

        # Arrange into grid (10 columns)
        grid_cols = 10
        grid_rows = (len(units) + grid_cols - 1) // grid_cols

        # Pad to fill grid
        while len(units) < grid_rows * grid_cols:
            units.append(None)

        # Create grid
        z = []
        text = []
        for row in range(grid_rows):
            z_row = []
            text_row = []
            for c in range(grid_cols):
                idx = row * grid_cols + c
                if idx < len(units) and units[idx]:
                    z_row.append(role_to_num.get(units[idx], -1))
                    text_row.append(units[idx].title())
                else:
                    z_row.append(-1)
                    text_row.append("")
            z.append(z_row)
            text.append(text_row)

        # Create colorscale from ROLE_COLORS
        colorscale = []
        for i, (role, color) in enumerate(ROLE_COLORS.items()):
            norm_val = i / (len(ROLE_COLORS) - 1)
            colorscale.append([norm_val, color])

        fig.add_trace(
            go.Heatmap(
                z=z,
                text=text,
                hovertemplate="%{text}<extra></extra>",
                colorscale=colorscale,
                showscale=False,
                xgap=2,
                ygap=2,
            ),
            row=1,
            col=col_idx,
        )

        # Hide axis labels
        fig.update_xaxes(showticklabels=False, showgrid=False, row=1, col=col_idx)
        fig.update_yaxes(showticklabels=False, showgrid=False, row=1, col=col_idx)

    # Add legend manually using scatter traces
    for role, color in ROLE_COLORS.items():
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=15, color=color, symbol="square"),
                name=role.title(),
                showlegend=True,
            )
        )

    fig.update_layout(
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
    )

    return fig


def create_units_treemap_chart(df: pd.DataFrame) -> go.Figure:
    """Create treemap showing hierarchical unit composition.

    Hierarchy: Player > Role > Unit Type

    Args:
        df: DataFrame from get_match_units_produced()

    Returns:
        Plotly figure with treemap
    """
    if df.empty:
        return create_empty_chart_placeholder("No unit data available")

    # Build hierarchical data with unique IDs to avoid duplicate label issues
    ids = ["Army"]
    labels = ["Army"]
    parents = [""]
    values = [0]
    colors = ["#f0f0f0"]

    # Add player level
    players = df["player_name"].unique()
    for player in players:
        ids.append(f"player-{player}")
        labels.append(player)
        parents.append("Army")
        values.append(0)
        colors.append("#e0e0e0")

    # Add role level (under each player)
    for player in players:
        player_data = df[df["player_name"] == player]
        roles = player_data["role"].unique()
        for role in roles:
            role_id = f"{player}-{role}"
            ids.append(role_id)
            labels.append(role.title())
            parents.append(f"player-{player}")
            values.append(0)
            colors.append(ROLE_COLORS.get(role, "#808080"))

            # Add unit types under each role
            role_data = player_data[player_data["role"] == role]
            for _, row in role_data.iterrows():
                unit_id = f"{role_id}-{row['unit_name']}"
                ids.append(unit_id)
                labels.append(row["unit_name"].title())
                parents.append(role_id)
                values.append(row["count"])
                colors.append(ROLE_COLORS.get(role, "#808080"))

    fig = go.Figure(
        go.Treemap(
            ids=ids,
            labels=labels,
            parents=parents,
            values=values,
            marker=dict(colors=colors),
            textinfo="label+value",
            hovertemplate="<b>%{label}</b><br>Count: %{value}<extra></extra>",
            branchvalues="remainder",
        )
    )

    fig.update_layout(
        height=500,
        margin=dict(t=30, l=10, r=10, b=10),
        paper_bgcolor=CHART_THEME["paper_bgcolor"],
        font=dict(color=CHART_THEME["font_color"]),
    )

    return fig


def create_units_icon_grid(df: pd.DataFrame) -> go.Figure:
    """Create unit icon grid showing army composition visually.

    Displays units in formation-like grid using emoji/text icons.

    Args:
        df: DataFrame from get_match_units_produced()

    Returns:
        Plotly figure with icon grid
    """
    if df.empty:
        return create_empty_chart_placeholder("No unit data available")

    # Role to icon mapping (using Unicode symbols)
    role_icons = {
        "infantry": "⚔️",
        "ranged": "🏹",
        "cavalry": "🐴",
        "siege": "🪨",
        "naval": "⚓",
        "settler": "🏠",
        "worker": "⛏️",
        "scout": "👁️",
        "religious": "✝️",
        "unknown": "❓",
    }

    players = df["player_name"].unique()
    n_players = len(players)

    fig = make_subplots(
        rows=1,
        cols=n_players,
        subplot_titles=[p for p in players],
        horizontal_spacing=0.05,
    )
    fig = apply_dark_theme(fig)

    for col_idx, player in enumerate(players, 1):
        player_data = df[df["player_name"] == player]

        # Build unit list organized by role for formation effect
        role_order = ["infantry", "ranged", "cavalry", "siege", "naval", "settler", "worker", "scout", "religious"]
        units = []
        for role in role_order:
            role_data = player_data[player_data["role"] == role]
            for _, row in role_data.iterrows():
                icon = role_icons.get(role, "❓")
                units.extend([(icon, row["unit_name"], role)] * row["count"])

        if not units:
            continue

        # Arrange into grid
        grid_cols = 8
        grid_rows = (len(units) + grid_cols - 1) // grid_cols

        x_coords = []
        y_coords = []
        icons = []
        hover_texts = []

        for i, (icon, name, role) in enumerate(units):
            row = i // grid_cols
            col = i % grid_cols
            x_coords.append(col)
            y_coords.append(grid_rows - row - 1)  # Flip y so row 0 is at top
            icons.append(icon)
            hover_texts.append(f"{name.title()} ({role.title()})")

        fig.add_trace(
            go.Scatter(
                x=x_coords,
                y=y_coords,
                mode="text",
                text=icons,
                textfont=dict(size=16),
                hovertext=hover_texts,
                hoverinfo="text",
                showlegend=False,
            ),
            row=1,
            col=col_idx,
        )

        fig.update_xaxes(
            showticklabels=False,
            showgrid=False,
            zeroline=False,
            range=[-0.5, grid_cols - 0.5],
            row=1,
            col=col_idx,
        )
        fig.update_yaxes(
            showticklabels=False,
            showgrid=False,
            zeroline=False,
            range=[-0.5, grid_rows - 0.5],
            row=1,
            col=col_idx,
        )

    # Add legend
    for role, icon in role_icons.items():
        if role != "unknown":
            fig.add_trace(
                go.Scatter(
                    x=[None],
                    y=[None],
                    mode="markers+text",
                    text=[icon],
                    textposition="middle right",
                    marker=dict(size=1, color=ROLE_COLORS.get(role, "#808080")),
                    name=f"{icon} {role.title()}",
                    showlegend=True,
                )
            )

    fig.update_layout(
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
    )

    return fig


def create_units_army_portrait(df: pd.DataFrame) -> go.Figure:
    """Create army portrait showing scaled composition summary.

    Shows each player's army as a summary with role proportions.

    Args:
        df: DataFrame from get_match_units_produced()

    Returns:
        Plotly figure with army portrait visualization
    """
    if df.empty:
        return create_empty_chart_placeholder("No unit data available")

    players = df["player_name"].unique()
    n_players = len(players)

    fig = make_subplots(
        rows=1,
        cols=n_players,
        subplot_titles=[p for p in players],
        specs=[[{"type": "domain"}] * n_players],
        horizontal_spacing=0.02,
    )
    fig = apply_dark_theme(fig)

    for col_idx, player in enumerate(players, 1):
        player_data = df[df["player_name"] == player]
        role_totals = player_data.groupby("role")["count"].sum()

        fig.add_trace(
            go.Pie(
                labels=[r.title() for r in role_totals.index],
                values=role_totals.values,
                hole=0.4,
                marker=dict(
                    colors=[ROLE_COLORS.get(r, "#808080") for r in role_totals.index]
                ),
                textinfo="percent",
                hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
                showlegend=(col_idx == 1),  # Only show legend for first chart
            ),
            row=1,
            col=col_idx,
        )

        # Add total count in center
        total = role_totals.sum()
        fig.add_annotation(
            text=f"<b>{total}</b><br>units",
            x=0.5 / n_players + (col_idx - 1) / n_players,
            y=0.5,
            font=dict(size=14),
            showarrow=False,
            xref="paper",
            yref="paper",
        )

    fig.update_layout(
        height=350,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
    )

    return fig


def create_units_marimekko_chart(df: pd.DataFrame) -> go.Figure:
    """Create Marimekko chart showing army size and composition.

    Width represents total army size, height segments show role proportions.

    Args:
        df: DataFrame from get_match_units_produced()

    Returns:
        Plotly figure with Marimekko chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No unit data available")

    # Calculate totals per player
    player_totals = df.groupby("player_name")["count"].sum()
    total_all = player_totals.sum()

    # Calculate widths as proportion of total
    widths = {player: total / total_all for player, total in player_totals.items()}

    # Get all roles that exist
    all_roles = df["role"].unique()

    fig = go.Figure()

    # Track x position for each player column
    x_pos = 0

    for player in player_totals.index:
        width = widths[player]
        player_data = df[df["player_name"] == player]
        role_totals = player_data.groupby("role")["count"].sum()
        player_total = role_totals.sum()

        # Stack roles vertically
        y_pos = 0
        for role in all_roles:
            count = role_totals.get(role, 0)
            if count == 0:
                continue

            height = count / player_total  # Normalized height

            fig.add_trace(
                go.Bar(
                    x=[x_pos + width / 2],
                    y=[height],
                    width=width * 0.95,  # Slight gap between bars
                    base=y_pos,
                    name=role.title(),
                    marker_color=ROLE_COLORS.get(role, "#808080"),
                    hovertemplate=(
                        f"<b>{player}</b><br>"
                        f"{role.title()}: {count}<br>"
                        f"<extra></extra>"
                    ),
                    showlegend=bool(x_pos == 0),  # Only show legend for first player
                    legendgroup=role,
                )
            )

            y_pos += height

        x_pos += width

    # Add player labels
    x_pos = 0
    for player, width in widths.items():
        total = player_totals[player]
        fig.add_annotation(
            x=x_pos + width / 2,
            y=-0.08,
            text=f"<b>{player}</b><br>({total} units)",
            showarrow=False,
            font=dict(size=11, color=CHART_THEME["font_color"]),
            xref="x",
            yref="paper",
        )
        x_pos += width

    fig.update_layout(
        barmode="stack",
        xaxis=dict(
            showticklabels=False,
            showgrid=False,
            zeroline=False,
            range=[0, 1],
        ),
        yaxis=dict(
            title="Proportion",
            showgrid=True,
            gridcolor=CHART_THEME["gridcolor"],
            range=[0, 1],
            tickformat=".0%",
            tickfont=dict(color=CHART_THEME["font_color"]),
            title_font=dict(color=CHART_THEME["font_color"]),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(color=CHART_THEME["font_color"]),
        ),
        height=450,
        margin=dict(b=80),
        paper_bgcolor=CHART_THEME["paper_bgcolor"],
        plot_bgcolor=CHART_THEME["plot_bgcolor"],
        font=dict(color=CHART_THEME["font_color"]),
        hoverlabel=dict(
            bgcolor=CHART_THEME["hoverlabel_bgcolor"],
            bordercolor=CHART_THEME["hoverlabel_bordercolor"],
            font=dict(color=CHART_THEME["hoverlabel_font_color"]),
        ),
    )

    return fig
