"""Chart generation functions for tournament data visualization.

This module provides functions to create various types of charts and visualizations
using Plotly for the tournament dashboard.
"""

from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..config import CIVILIZATION_COLORS, DEFAULT_CHART_LAYOUT, Config
from ..nation_colors import get_nation_color


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
    layout = DEFAULT_CHART_LAYOUT.copy()
    layout.update(
        {
            "title": {"text": title, "x": 0.5, "xanchor": "center"},
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


def create_territory_control_chart(df: pd.DataFrame) -> go.Figure:
    """Create an area chart showing territory control over time.

    Args:
        df: DataFrame with territory control data over time

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

        fig.add_trace(
            go.Scatter(
                x=player_data["turn_number"],
                y=player_data["controlled_territories"],
                mode="lines",
                name=player,
                fill="tonexty" if i > 0 else "tozeroy",
                line=dict(color=Config.PRIMARY_COLORS[i % len(Config.PRIMARY_COLORS)]),
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
        font=dict(size=16, color="gray"),
    )

    fig.update_layout(
        showlegend=False,
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
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

    title = f"Top {top_n} Statistics Comparison (Normalized %)"
    if category_filter:
        title += f" - {category_filter}"

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        title=title,
    )

    return fig


def create_law_progression_chart(df: pd.DataFrame) -> go.Figure:
    """Create a bar chart showing total laws enacted by each player.

    Args:
        df: DataFrame with columns: player_name, civilization, total_laws, total_turns

    Returns:
        Plotly figure with grouped bar chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No law progression data available")

    fig = create_base_figure(
        title="Law Progression by Player",
        x_title="Player",
        y_title="Total Laws Enacted",
        height=400,
    )

    # Sort by total laws descending
    df_sorted = df.sort_values("total_laws", ascending=False)

    # Create hover text with additional info
    hover_text = [
        f"Player: {row['player_name']}<br>"
        + f"Civilization: {row.get('civilization', 'Unknown')}<br>"
        + f"Total Laws: {row['total_laws']}<br>"
        + f"Total Turns: {row.get('total_turns', 'N/A')}"
        for _, row in df_sorted.iterrows()
    ]

    fig.add_trace(
        go.Bar(
            x=df_sorted["player_name"],
            y=df_sorted["total_laws"],
            text=df_sorted["total_laws"],
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
    """Create a pie chart showing nation win percentages.

    Args:
        df: DataFrame with nation, wins columns

    Returns:
        Plotly figure with pie chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No nation data available")

    fig = create_base_figure(title="Nation Win Percentage", show_legend=False)

    # Use nation colors from nation_colors.py
    colors = [get_nation_color(nation) for nation in df["nation"]]

    fig.add_trace(
        go.Pie(
            labels=df["nation"],
            values=df["wins"],
            marker=dict(colors=colors),
            textposition="inside",
            textinfo="label",
            hovertemplate="<b>%{label}</b><br>Wins: %{value}<br>Percentage: %{percent}<extra></extra>",
        )
    )

    fig.update_layout(showlegend=False)

    return fig


def create_nation_loss_percentage_chart(df: pd.DataFrame) -> go.Figure:
    """Create a pie chart showing nation loss percentages.

    Args:
        df: DataFrame with nation, losses columns

    Returns:
        Plotly figure with pie chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No nation data available")

    fig = create_base_figure(title="Nation Loss Percentage", show_legend=False)

    # Use nation colors from nation_colors.py
    colors = [get_nation_color(nation) for nation in df["nation"]]

    fig.add_trace(
        go.Pie(
            labels=df["nation"],
            values=df["losses"],
            marker=dict(colors=colors),
            textposition="inside",
            textinfo="label",
            hovertemplate="<b>%{label}</b><br>Losses: %{value}<br>Percentage: %{percent}<extra></extra>",
        )
    )

    fig.update_layout(showlegend=False)

    return fig


def create_nation_popularity_chart(df: pd.DataFrame) -> go.Figure:
    """Create a pie chart showing nation popularity (matches played).

    Args:
        df: DataFrame with nation, total_matches columns

    Returns:
        Plotly figure with pie chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No nation data available")

    fig = create_base_figure(title="Nation Popularity", show_legend=False)

    # Use nation colors from nation_colors.py
    colors = [get_nation_color(nation) for nation in df["nation"]]

    fig.add_trace(
        go.Pie(
            labels=df["nation"],
            values=df["total_matches"],
            marker=dict(colors=colors),
            textposition="inside",
            textinfo="label",
            hovertemplate="<b>%{label}</b><br>Matches: %{value}<br>Percentage: %{percent}<extra></extra>",
        )
    )

    fig.update_layout(showlegend=False)

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
    """Create a sunburst chart showing unit popularity by category and type.

    Args:
        df: DataFrame with category, role, unit_type, total_count columns

    Returns:
        Plotly figure with sunburst chart
    """
    if df.empty:
        return create_empty_chart_placeholder("No unit data available")

    # Build the sunburst data structure
    # Calculate total for root
    total_units = int(df["total_count"].sum())

    # Level 0: Root with unit count
    labels = [f"{total_units} units"]
    parents = [""]
    values = [total_units]

    # Level 1: Add categories (inner circle: military, civilian, religious)
    category_totals = df.groupby("category")["total_count"].sum().to_dict()
    categories = sorted(category_totals.keys())

    for category in categories:
        labels.append(category)
        parents.append(f"{total_units} units")
        values.append(category_totals[category])

    # Level 2: Add unit types (outer circle)
    for _, row in df.iterrows():
        # Remove "UNIT_" prefix and convert to title case
        unit_name = row["unit_type"].replace("UNIT_", "").replace("_", " ").title()
        labels.append(unit_name)
        parents.append(row["category"])
        values.append(row["total_count"])

    fig = go.Figure(
        go.Sunburst(
            labels=labels,
            parents=parents,
            values=values,
            branchvalues="total",
            textfont=dict(size=10),
            marker=dict(colorscale="RdBu", cmid=50),
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percentParent:.1%} of parent<extra></extra>",
        )
    )

    fig.update_layout(margin=dict(t=0, l=0, r=0, b=0), height=400)

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
            text=pd.to_numeric(df["turn_to_4_laws"], errors="coerce").round(0).astype("Int64"),  # Int64 handles NA
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
            text=pd.to_numeric(df["turn_to_7_laws"], errors="coerce").round(0).astype("Int64"),
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
            milestones.append({
                "turn": row["turn_to_4_laws"],
                "label": "4 laws",
                "symbol": "circle",
            })

        if pd.notna(row["turn_to_7_laws"]):
            milestones.append({
                "turn": row["turn_to_7_laws"],
                "label": "7 laws",
                "symbol": "star",
            })

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
        title="Law Milestone Timing Distribution (All Matches)",
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
                    "<b>4 Laws Milestone</b><br>"
                    "Turn: %{y}<br>"
                    "<extra></extra>"
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
                    "<b>7 Laws Milestone</b><br>"
                    "Turn: %{y}<br>"
                    "<extra></extra>"
                ),
            )
        )

    # Add statistics annotation
    if not df_4_laws.empty:
        median_4 = df_4_laws["turn_to_4_laws"].median()
        mean_4 = df_4_laws["turn_to_4_laws"].mean()
        count_4 = len(df_4_laws)

        stats_text = f"4 Laws: n={count_4}, median={median_4:.0f}, mean={mean_4:.1f}"

        if not df_7_laws.empty:
            median_7 = df_7_laws["turn_to_7_laws"].median()
            mean_7 = df_7_laws["turn_to_7_laws"].mean()
            count_7 = len(df_7_laws)
            stats_text += f" | 7 Laws: n={count_7}, median={median_7:.0f}, mean={mean_7:.1f}"

        fig.add_annotation(
            text=stats_text,
            xref="paper",
            yref="paper",
            x=0.5,
            y=1.1,
            showarrow=False,
            font=dict(size=11),
        )

    return fig
