"""Map and territory visualization page.

This page provides territorial control analysis, map-based visualizations,
and strategic position analytics.
"""

import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, Any, List, Optional
import logging
import numpy as np

from tournament_visualizer.components.layouts import (
    create_page_header, create_chart_card, create_two_column_layout,
    create_data_table_card, create_tab_layout, create_metric_card,
    create_empty_state, create_filter_card, create_metric_grid
)
from tournament_visualizer.components.charts import (
    create_territory_control_chart, create_heatmap_chart,
    create_empty_chart_placeholder, create_base_figure
)
from tournament_visualizer.components.filters import (
    create_date_range_filter, create_map_filter,
    get_filter_values, apply_filters_to_dataframe
)
from tournament_visualizer.data.queries import get_queries
from tournament_visualizer.config import PAGE_CONFIG, Config

logger = logging.getLogger(__name__)

# Register this page
dash.register_page(__name__, path="/maps", name="Maps")

# Page layout
layout = html.Div([
    # Page header
    create_page_header(
        title=PAGE_CONFIG["maps"]["title"],
        description=PAGE_CONFIG["maps"]["description"],
        icon="bi-map-fill",
        actions=[
            dbc.Button(
                [html.I(className="bi bi-arrow-clockwise me-2"), "Refresh"],
                id="maps-refresh-btn",
                color="outline-primary",
                size="sm"
            )
        ]
    ),
    
    # Filters section
    create_filter_card(
        title="Filters",
        filters=[
            dbc.Row([
                dbc.Col([
                    create_date_range_filter("maps-date", default_range="all")
                ], width=4),
                dbc.Col([
                    create_map_filter("maps-settings")
                ], width=4),
                dbc.Col([
                    html.Label("Analysis Type:", className="form-label fw-bold"),
                    dcc.Dropdown(
                        id="maps-analysis-type",
                        options=[
                            {"label": "Territory Control", "value": "territory"},
                            {"label": "Starting Positions", "value": "starting"},
                            {"label": "Resource Distribution", "value": "resources"}
                        ],
                        value="territory",
                        clearable=False
                    )
                ], width=4)
            ])
        ]
    ),
    
    # Tabbed analysis sections
    create_tab_layout([
        {
            "label": "Map Performance",
            "tab_id": "map-performance",
            "content": [
                # Summary metrics
                html.Div(id="map-summary-metrics", className="mb-4"),
                
                # Performance charts
                dbc.Row([
                    dbc.Col([
                        create_chart_card(
                            title="Game Length by Map Size",
                            chart_id="map-length-chart",
                            height="400px"
                        )
                    ], width=6),
                    dbc.Col([
                        create_chart_card(
                            title="Map Popularity",
                            chart_id="map-popularity-chart",
                            height="400px"
                        )
                    ], width=6)
                ], className="mb-4"),
                
                # Map statistics table
                dbc.Row([
                    dbc.Col([
                        create_data_table_card(
                            title="Map Statistics",
                            table_id="map-stats-table",
                            columns=[
                                {"name": "Map Size", "id": "map_size"},
                                {"name": "Map Class", "id": "map_class"},
                                {"name": "Matches", "id": "total_matches", "type": "numeric"},
                                {"name": "Avg Turns", "id": "avg_turns", "type": "numeric", "format": {"specifier": ".1f"}},
                                {"name": "Min Turns", "id": "min_turns", "type": "numeric"},
                                {"name": "Max Turns", "id": "max_turns", "type": "numeric"},
                                {"name": "Players", "id": "unique_players", "type": "numeric"}
                            ]
                        )
                    ], width=12)
                ])
            ]
        },
        {
            "label": "Territory Analysis",
            "tab_id": "territory-analysis",
            "content": [
                # Match selection for territory analysis
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Territory Analysis", className="card-title"),
                        dbc.Row([
                            dbc.Col([
                                html.Label("Select Match:", className="form-label"),
                                dcc.Dropdown(
                                    id="territory-match-selector",
                                    placeholder="Choose a match to analyze territories...",
                                    options=[]
                                )
                            ], width=8),
                            dbc.Col([
                                html.Label("Turn Range:", className="form-label"),
                                dcc.RangeSlider(
                                    id="territory-turn-range",
                                    min=0,
                                    max=100,
                                    value=[0, 100],
                                    marks={i: str(i) for i in range(0, 101, 25)},
                                    tooltip={"placement": "bottom", "always_visible": True}
                                )
                            ], width=4)
                        ])
                    ])
                ], className="mb-4"),
                
                # Territory visualizations
                dbc.Row([
                    dbc.Col([
                        create_chart_card(
                            title="Territory Control Over Time",
                            chart_id="territory-timeline-chart",
                            height="500px"
                        )
                    ], width=8),
                    dbc.Col([
                        create_chart_card(
                            title="Final Territory Distribution",
                            chart_id="territory-distribution-chart",
                            height="500px"
                        )
                    ], width=4)
                ], className="mb-4"),
                
                # Territory heatmap
                dbc.Row([
                    dbc.Col([
                        create_chart_card(
                            title="Territory Control Heatmap",
                            chart_id="territory-heatmap",
                            height="600px"
                        )
                    ], width=12)
                ])
            ]
        },
        {
            "label": "Strategic Analysis",
            "tab_id": "strategic-analysis",
            "content": [
                dbc.Row([
                    dbc.Col([
                        create_chart_card(
                            title="Starting Position Impact",
                            chart_id="starting-position-chart",
                            height="400px"
                        )
                    ], width=6),
                    dbc.Col([
                        create_chart_card(
                            title="Map Class Performance",
                            chart_id="map-class-performance-chart",
                            height="400px"
                        )
                    ], width=6)
                ], className="mb-4"),
                
                dbc.Row([
                    dbc.Col([
                        create_chart_card(
                            title="Territory Expansion Patterns",
                            chart_id="expansion-patterns-chart",
                            height="500px"
                        )
                    ], width=12)
                ])
            ]
        }
    ], active_tab="map-performance")
])


@callback(
    Output("map-summary-metrics", "children"),
    [
        Input("maps-date-dropdown", "value"),
        Input("maps-settings-size-dropdown", "value"),
        Input("maps-settings-class-dropdown", "value"),
        Input("maps-refresh-btn", "n_clicks")
    ]
)
def update_map_summary_metrics(
    date_range: Optional[int],
    map_sizes: Optional[List[str]],
    map_classes: Optional[List[str]],
    refresh_clicks: int
) -> html.Div:
    """Update map summary metrics.
    
    Args:
        date_range: Selected date range in days
        map_sizes: Selected map sizes filter
        map_classes: Selected map classes filter
        refresh_clicks: Number of refresh button clicks
        
    Returns:
        Metrics grid component
    """
    try:
        queries = get_queries()
        df = queries.get_map_performance_analysis()
        
        if df.empty:
            return create_empty_state("No map data available")
        
        # Apply filters
        if map_sizes:
            df = df[df['map_size'].isin(map_sizes)]
        if map_classes:
            df = df[df['map_class'].isin(map_classes)]
        
        # Calculate summary metrics
        total_map_types = len(df)
        avg_game_length = df['avg_turns'].mean()
        most_popular_size = df.loc[df['total_matches'].idxmax()]['map_size'] if not df.empty else None
        longest_avg_game = df.loc[df['avg_turns'].idxmax()] if not df.empty else None
        
        metrics = [
            {
                "title": "Map Types",
                "value": total_map_types,
                "icon": "bi-map",
                "color": "primary"
            },
            {
                "title": "Avg Game Length",
                "value": f"{avg_game_length:.0f} turns" if pd.notna(avg_game_length) else "N/A",
                "icon": "bi-clock",
                "color": "info"
            },
            {
                "title": "Most Popular Size",
                "value": most_popular_size or "N/A",
                "icon": "bi-grid",
                "color": "success"
            },
            {
                "title": "Longest Games",
                "value": longest_avg_game['map_size'] if longest_avg_game is not None else "N/A",
                "subtitle": f"{longest_avg_game['avg_turns']:.0f} turns avg" if longest_avg_game is not None else "",
                "icon": "bi-arrow-up",
                "color": "warning"
            }
        ]
        
        return create_metric_grid(metrics)
        
    except Exception as e:
        return create_empty_state(f"Error loading metrics: {str(e)}")


@callback(
    Output("map-length-chart", "figure"),
    [
        Input("maps-date-dropdown", "value"),
        Input("maps-settings-size-dropdown", "value"),
        Input("maps-settings-class-dropdown", "value"),
        Input("maps-refresh-btn", "n_clicks")
    ]
)
def update_map_length_chart(
    date_range: Optional[int],
    map_sizes: Optional[List[str]],
    map_classes: Optional[List[str]],
    refresh_clicks: int
):
    """Update map length chart.
    
    Args:
        date_range: Selected date range in days
        map_sizes: Selected map sizes filter
        map_classes: Selected map classes filter
        refresh_clicks: Number of refresh button clicks
        
    Returns:
        Plotly figure for map length analysis
    """
    try:
        queries = get_queries()
        df = queries.get_map_performance_analysis()
        
        if df.empty:
            return create_empty_chart_placeholder("No map data available")
        
        # Apply filters
        if map_sizes:
            df = df[df['map_size'].isin(map_sizes)]
        if map_classes:
            df = df[df['map_class'].isin(map_classes)]
        
        if df.empty:
            return create_empty_chart_placeholder("No maps match the selected criteria")
        
        fig = create_base_figure(
            title="Average Game Length by Map Size",
            x_title="Map Size",
            y_title="Average Turns"
        )
        
        fig.add_trace(go.Bar(
            x=df['map_size'],
            y=df['avg_turns'],
            marker_color=Config.PRIMARY_COLORS[0],
            text=[f"{turns:.0f}" for turns in df['avg_turns']],
            textposition='auto'
        ))
        
        return fig
        
    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading map length data: {str(e)}")


@callback(
    Output("map-popularity-chart", "figure"),
    [
        Input("maps-date-dropdown", "value"),
        Input("maps-settings-size-dropdown", "value"),
        Input("maps-settings-class-dropdown", "value"),
        Input("maps-refresh-btn", "n_clicks")
    ]
)
def update_map_popularity_chart(
    date_range: Optional[int],
    map_sizes: Optional[List[str]],
    map_classes: Optional[List[str]],
    refresh_clicks: int
):
    """Update map popularity chart.
    
    Args:
        date_range: Selected date range in days
        map_sizes: Selected map sizes filter
        map_classes: Selected map classes filter
        refresh_clicks: Number of refresh button clicks
        
    Returns:
        Plotly figure for map popularity
    """
    try:
        queries = get_queries()
        df = queries.get_map_performance_analysis()
        
        if df.empty:
            return create_empty_chart_placeholder("No map data available")
        
        # Apply filters
        if map_sizes:
            df = df[df['map_size'].isin(map_sizes)]
        if map_classes:
            df = df[df['map_class'].isin(map_classes)]
        
        if df.empty:
            return create_empty_chart_placeholder("No maps match the selected criteria")
        
        fig = create_base_figure(title="Map Size Popularity", show_legend=False)
        
        # Group by map size and sum matches
        size_popularity = df.groupby('map_size')['total_matches'].sum().reset_index()
        
        fig.add_trace(go.Pie(
            labels=size_popularity['map_size'],
            values=size_popularity['total_matches'],
            hole=0.3,
            marker_colors=Config.PRIMARY_COLORS[:len(size_popularity)]
        ))
        
        return fig
        
    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading popularity data: {str(e)}")


@callback(
    Output("territory-match-selector", "options"),
    Input("maps-refresh-btn", "n_clicks")
)
def update_territory_match_options(refresh_clicks: int) -> List[Dict[str, Any]]:
    """Update territory match selector options.
    
    Args:
        refresh_clicks: Number of refresh button clicks
        
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
            game_name = row.get('game_name', 'Unknown')
            save_date = row.get('save_date', '')
            total_turns = row.get('total_turns', 0)
            
            if pd.notna(save_date):
                date_str = pd.to_datetime(save_date).strftime('%Y-%m-%d')
            else:
                date_str = 'Unknown Date'
            
            label = f"{game_name} ({date_str}) - {total_turns} turns"
            
            options.append({
                "label": label,
                "value": row['match_id']
            })
        
        return options
        
    except Exception as e:
        logger.error(f"Error updating territory match options: {e}")
        return []


@callback(
    Output("territory-timeline-chart", "figure"),
    [
        Input("territory-match-selector", "value"),
        Input("territory-turn-range", "value")
    ]
)
def update_territory_timeline_chart(
    match_id: Optional[int],
    turn_range: List[int]
):
    """Update territory timeline chart.
    
    Args:
        match_id: Selected match ID
        turn_range: Selected turn range
        
    Returns:
        Plotly figure for territory timeline
    """
    if not match_id:
        return create_empty_chart_placeholder("Select a match to view territory control")
    
    try:
        queries = get_queries()
        df = queries.get_territory_control_summary(match_id)
        
        if df.empty:
            return create_empty_chart_placeholder("No territory data available for this match")
        
        # Filter by turn range
        df = df[(df['turn_number'] >= turn_range[0]) & (df['turn_number'] <= turn_range[1])]
        
        if df.empty:
            return create_empty_chart_placeholder("No territory data in selected turn range")
        
        return create_territory_control_chart(df)
        
    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading territory timeline: {str(e)}")


@callback(
    Output("territory-distribution-chart", "figure"),
    Input("territory-match-selector", "value")
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
        final_turn = df['turn_number'].max()
        final_data = df[df['turn_number'] == final_turn]
        
        fig = create_base_figure(title="Final Territory Distribution", show_legend=False)
        
        fig.add_trace(go.Pie(
            labels=final_data['player_name'],
            values=final_data['controlled_territories'],
            hole=0.3,
            marker_colors=Config.PRIMARY_COLORS[:len(final_data)]
        ))
        
        return fig
        
    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading territory distribution: {str(e)}")


@callback(
    Output("territory-heatmap", "figure"),
    Input("territory-match-selector", "value")
)
def update_territory_heatmap(match_id: Optional[int]):
    """Update territory heatmap visualization.
    
    Args:
        match_id: Selected match ID
        
    Returns:
        Plotly figure for territory heatmap
    """
    if not match_id:
        return create_empty_chart_placeholder("Select a match to view territory heatmap")
    
    try:
        from tournament_visualizer.data.database import get_database
        db = get_database()
        
        # Get territory data for the match
        query = """
        SELECT x_coordinate, y_coordinate, turn_number, 
               p.player_name, p.civilization
        FROM territories t
        LEFT JOIN players p ON t.owner_player_id = p.player_id
        WHERE t.match_id = ?
        ORDER BY turn_number DESC
        LIMIT 1000
        """
        
        result = db.fetch_all(query, {"1": match_id})
        
        if not result:
            return create_empty_chart_placeholder("No territory data available for this match")
        
        # Convert to DataFrame
        df = pd.DataFrame(result, columns=['x', 'y', 'turn', 'player', 'civilization'])
        
        # Create a simple scatter plot showing territory control
        fig = create_base_figure(
            title="Territory Control Map",
            x_title="X Coordinate",
            y_title="Y Coordinate"
        )
        
        # Get latest turn for each territory
        latest_territories = df.groupby(['x', 'y']).last().reset_index()
        
        # Color by player
        unique_players = latest_territories['player'].dropna().unique()
        color_map = {player: Config.PRIMARY_COLORS[i % len(Config.PRIMARY_COLORS)] 
                    for i, player in enumerate(unique_players)}
        
        for player in unique_players:
            player_data = latest_territories[latest_territories['player'] == player]
            
            fig.add_trace(go.Scatter(
                x=player_data['x'],
                y=player_data['y'],
                mode='markers',
                name=player,
                marker=dict(
                    color=color_map[player],
                    size=8,
                    opacity=0.7
                )
            ))
        
        fig.update_layout(
            xaxis=dict(constrain='domain'),
            yaxis=dict(scaleanchor='x', scaleratio=1)
        )
        
        return fig
        
    except Exception as e:
        return create_empty_chart_placeholder(f"Error creating territory heatmap: {str(e)}")


@callback(
    Output("map-stats-table", "data"),
    [
        Input("maps-date-dropdown", "value"),
        Input("maps-settings-size-dropdown", "value"),
        Input("maps-settings-class-dropdown", "value"),
        Input("maps-refresh-btn", "n_clicks")
    ]
)
def update_map_stats_table(
    date_range: Optional[int],
    map_sizes: Optional[List[str]],
    map_classes: Optional[List[str]],
    refresh_clicks: int
) -> List[Dict[str, Any]]:
    """Update map statistics table.
    
    Args:
        date_range: Selected date range in days
        map_sizes: Selected map sizes filter
        map_classes: Selected map classes filter
        refresh_clicks: Number of refresh button clicks
        
    Returns:
        List of map statistics data
    """
    try:
        queries = get_queries()
        df = queries.get_map_performance_analysis()
        
        if df.empty:
            return []
        
        # Apply filters
        if map_sizes:
            df = df[df['map_size'].isin(map_sizes)]
        if map_classes:
            df = df[df['map_class'].isin(map_classes)]
        
        return df.sort_values('total_matches', ascending=False).to_dict('records')
        
    except Exception as e:
        logger.error(f"Error updating map stats table: {e}")
        return []


# Additional charts for strategic analysis tab
@callback(
    Output("starting-position-chart", "figure"),
    Input("maps-refresh-btn", "n_clicks")
)
def update_starting_position_chart(refresh_clicks: int):
    """Update starting position impact chart.
    
    Args:
        refresh_clicks: Number of refresh button clicks
        
    Returns:
        Plotly figure for starting position analysis
    """
    # This would require more complex analysis of starting positions
    # For now, return a placeholder
    return create_empty_chart_placeholder("Starting position analysis not yet implemented")


@callback(
    Output("map-class-performance-chart", "figure"),
    Input("maps-refresh-btn", "n_clicks")
)
def update_map_class_performance_chart(refresh_clicks: int):
    """Update map class performance chart.
    
    Args:
        refresh_clicks: Number of refresh button clicks
        
    Returns:
        Plotly figure for map class performance
    """
    try:
        queries = get_queries()
        df = queries.get_map_performance_analysis()
        
        if df.empty:
            return create_empty_chart_placeholder("No map class data available")
        
        # Group by map class
        class_performance = df.groupby('map_class').agg({
            'total_matches': 'sum',
            'avg_turns': 'mean'
        }).reset_index()
        
        fig = create_base_figure(
            title="Map Class Performance",
            x_title="Map Class",
            y_title="Average Turns"
        )
        
        fig.add_trace(go.Bar(
            x=class_performance['map_class'],
            y=class_performance['avg_turns'],
            marker_color=Config.PRIMARY_COLORS[2],
            text=[f"{turns:.0f}" for turns in class_performance['avg_turns']],
            textposition='auto'
        ))
        
        fig.update_layout(xaxis_tickangle=-45)
        
        return fig
        
    except Exception as e:
        return create_empty_chart_placeholder(f"Error loading map class data: {str(e)}")


@callback(
    Output("expansion-patterns-chart", "figure"),
    Input("maps-refresh-btn", "n_clicks")
)
def update_expansion_patterns_chart(refresh_clicks: int):
    """Update expansion patterns chart.
    
    Args:
        refresh_clicks: Number of refresh button clicks
        
    Returns:
        Plotly figure for expansion patterns
    """
    # This would require complex analysis of territory expansion over time
    # For now, return a placeholder
    return create_empty_chart_placeholder("Expansion pattern analysis not yet implemented")