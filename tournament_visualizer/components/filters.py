"""Interactive filter components for the tournament visualizer.

This module provides reusable filter components for date ranges, players,
civilizations, and other tournament data attributes.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, callback, dcc, html

from ..config import APP_CONSTANTS, FILTER_OPTIONS
from ..data.queries import get_queries

logger = logging.getLogger(__name__)


def create_date_range_filter(
    component_id: str, label: str = "Date Range", default_range: Union[int, str] = 30
) -> dbc.Card:
    """Create a date range filter component.

    Args:
        component_id: Unique ID for the component
        label: Display label for the filter
        default_range: Default number of days to include or "all" for all time

    Returns:
        Card component containing date range filter
    """
    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.Label(label, className="form-label fw-bold"),
                    dcc.Dropdown(
                        id=f"{component_id}-dropdown",
                        options=FILTER_OPTIONS["date_ranges"],
                        value=default_range,
                        clearable=False,
                        className="mb-2",
                    ),
                    dcc.DatePickerRange(
                        id=f"{component_id}-picker",
                        display_format="YYYY-MM-DD",
                        className="d-none",  # Hidden by default, shown when "Custom" is selected
                    ),
                ]
            )
        ],
        className="mb-3",
    )


def create_player_filter(
    component_id: str, label: str = "Players", multi: bool = True
) -> dbc.Card:
    """Create a player selection filter component.

    Args:
        component_id: Unique ID for the component
        label: Display label for the filter
        multi: Whether to allow multiple selections

    Returns:
        Card component containing player filter
    """
    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.Label(label, className="form-label fw-bold"),
                    dcc.Dropdown(
                        id=f"{component_id}-dropdown",
                        multi=multi,
                        placeholder=f"Select {label.lower()}...",
                        options=[],  # Will be populated by callback
                        className="mb-2",
                    ),
                    dbc.Button(
                        "Clear All",
                        id=f"{component_id}-clear",
                        color="outline-secondary",
                        size="sm",
                        className="w-100",
                    ),
                ]
            )
        ],
        className="mb-3",
    )


def create_civilization_filter(
    component_id: str, label: str = "Civilizations", multi: bool = True
) -> dbc.Card:
    """Create a civilization selection filter component.

    Args:
        component_id: Unique ID for the component
        label: Display label for the filter
        multi: Whether to allow multiple selections

    Returns:
        Card component containing civilization filter
    """
    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.Label(label, className="form-label fw-bold"),
                    dcc.Dropdown(
                        id=f"{component_id}-dropdown",
                        multi=multi,
                        placeholder=f"Select {label.lower()}...",
                        options=[],  # Will be populated by callback
                        className="mb-2",
                    ),
                    dbc.Button(
                        "Clear All",
                        id=f"{component_id}-clear",
                        color="outline-secondary",
                        size="sm",
                        className="w-100",
                    ),
                ]
            )
        ],
        className="mb-3",
    )


def create_match_duration_filter(
    component_id: str, label: str = "Match Duration"
) -> dbc.Card:
    """Create a match duration filter component.

    Args:
        component_id: Unique ID for the component
        label: Display label for the filter

    Returns:
        Card component containing match duration filter
    """
    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.Label(label, className="form-label fw-bold"),
                    dcc.Dropdown(
                        id=f"{component_id}-dropdown",
                        options=FILTER_OPTIONS["match_durations"],
                        multi=True,
                        placeholder="Select duration ranges...",
                        className="mb-2",
                    ),
                    html.Div(
                        [
                            html.Label("Custom Range:", className="form-label small"),
                            dcc.RangeSlider(
                                id=f"{component_id}-slider",
                                min=0,
                                max=300,
                                step=10,
                                marks={i: str(i) for i in range(0, 301, 50)},
                                tooltip={"placement": "bottom", "always_visible": True},
                            ),
                        ],
                        className="mt-3",
                    ),
                ]
            )
        ],
        className="mb-3",
    )


def create_map_filter(component_id: str, label: str = "Map Settings") -> dbc.Card:
    """Create a map settings filter component.

    Args:
        component_id: Unique ID for the component
        label: Display label for the filter

    Returns:
        Card component containing map filter
    """
    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.Label(label, className="form-label fw-bold"),
                    # Map size filter
                    html.Label("Map Size:", className="form-label small mt-2"),
                    dcc.Dropdown(
                        id=f"{component_id}-size-dropdown",
                        multi=True,
                        placeholder="Select map sizes...",
                        options=[],  # Will be populated by callback
                        className="mb-2",
                    ),
                    # Map class filter
                    html.Label("Map Class:", className="form-label small"),
                    dcc.Dropdown(
                        id=f"{component_id}-class-dropdown",
                        multi=True,
                        placeholder="Select map classes...",
                        options=[
                            {"label": cls, "value": cls}
                            for cls in APP_CONSTANTS["MAP_CLASSES"]
                        ],
                        className="mb-2",
                    ),
                ]
            )
        ],
        className="mb-3",
    )


def create_victory_condition_filter(
    component_id: str, label: str = "Victory Conditions"
) -> dbc.Card:
    """Create a victory conditions filter component.

    Args:
        component_id: Unique ID for the component
        label: Display label for the filter

    Returns:
        Card component containing victory conditions filter
    """
    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.Label(label, className="form-label fw-bold"),
                    dcc.Dropdown(
                        id=f"{component_id}-dropdown",
                        options=[
                            {"label": vc, "value": vc}
                            for vc in APP_CONSTANTS["VICTORY_CONDITIONS"]
                        ],
                        multi=True,
                        placeholder="Select victory conditions...",
                        className="mb-2",
                    ),
                ]
            )
        ],
        className="mb-3",
    )


def create_filter_sidebar(filters: List[str]) -> dbc.Col:
    """Create a complete filter sidebar with specified filters.

    Args:
        filters: List of filter types to include

    Returns:
        Column component containing all requested filters
    """
    filter_components = []

    if "date_range" in filters:
        filter_components.append(create_date_range_filter("sidebar-date"))

    if "players" in filters:
        filter_components.append(create_player_filter("sidebar-players"))

    if "civilizations" in filters:
        filter_components.append(create_civilization_filter("sidebar-civilizations"))

    if "match_duration" in filters:
        filter_components.append(create_match_duration_filter("sidebar-duration"))

    if "maps" in filters:
        filter_components.append(create_map_filter("sidebar-maps"))

    if "victory_conditions" in filters:
        filter_components.append(create_victory_condition_filter("sidebar-victory"))

    # Add reset all button
    filter_components.append(
        dbc.Card(
            [
                dbc.CardBody(
                    [
                        dbc.Button(
                            [
                                html.I(className="bi bi-arrow-clockwise me-2"),
                                "Reset All Filters",
                            ],
                            id="reset-all-filters",
                            color="outline-primary",
                            className="w-100",
                        )
                    ]
                )
            ],
            className="mb-3",
        )
    )

    return dbc.Col(html.Div(filter_components), width=3, className="filter-sidebar")


# Callback functions for populating filter options


@callback(
    Output("sidebar-players-dropdown", "options"),
    Input("sidebar-date-dropdown", "value"),
    prevent_initial_call=True,
)
def update_player_options(date_range: Optional[int]) -> List[Dict[str, str]]:
    """Update player filter options based on date range.

    Args:
        date_range: Selected date range in days

    Returns:
        List of player options
    """
    try:
        queries = get_queries()

        # Get player performance data
        df = queries.get_player_performance()

        if df.empty:
            return []

        # Create options with win rate info
        options = []
        for _, row in df.iterrows():
            label = f"{row['player_name']} ({row['win_rate']:.1f}% win rate)"
            options.append({"label": label, "value": row["player_name"]})

        return options

    except Exception as e:
        logger.error(f"Error updating player options: {e}")
        return []


@callback(
    Output("sidebar-civilizations-dropdown", "options"),
    Input("sidebar-date-dropdown", "value"),
    prevent_initial_call=True,
)
def update_civilization_options(date_range: Optional[int]) -> List[Dict[str, str]]:
    """Update civilization filter options.

    Args:
        date_range: Selected date range in days

    Returns:
        List of civilization options
    """
    try:
        queries = get_queries()

        # Get civilization performance data
        df = queries.get_civilization_performance()

        if df.empty:
            return []

        # Create options with win rate info
        options = []
        for _, row in df.iterrows():
            if pd.notna(row["civilization"]):
                label = f"{row['civilization']} ({row['win_rate']:.1f}% win rate)"
                options.append({"label": label, "value": row["civilization"]})

        return sorted(options, key=lambda x: x["label"])

    except Exception as e:
        logger.error(f"Error updating civilization options: {e}")
        return []


@callback(
    Output("sidebar-maps-size-dropdown", "options"),
    Input("sidebar-date-dropdown", "value"),
    prevent_initial_call=True,
)
def update_map_size_options(date_range: Optional[int]) -> List[Dict[str, str]]:
    """Update map size filter options.

    Args:
        date_range: Selected date range in days

    Returns:
        List of map size options
    """
    try:
        queries = get_queries()

        # Get map performance data
        df = queries.get_map_performance_analysis()

        if df.empty:
            return []

        # Get unique map sizes
        map_sizes = df["map_size"].dropna().unique()

        options = [{"label": size, "value": size} for size in sorted(map_sizes)]
        return options

    except Exception as e:
        logger.error(f"Error updating map size options: {e}")
        return []


# Clear button callbacks


@callback(
    Output("sidebar-players-dropdown", "value"),
    Input("sidebar-players-clear", "n_clicks"),
    prevent_initial_call=True,
)
def clear_player_filter(n_clicks: int) -> List:
    """Clear player filter selections.

    Args:
        n_clicks: Number of clear button clicks

    Returns:
        Empty list to clear selections
    """
    if n_clicks:
        return []
    return dash.no_update


@callback(
    Output("sidebar-civilizations-dropdown", "value"),
    Input("sidebar-civilizations-clear", "n_clicks"),
    prevent_initial_call=True,
)
def clear_civilization_filter(n_clicks: int) -> List:
    """Clear civilization filter selections.

    Args:
        n_clicks: Number of clear button clicks

    Returns:
        Empty list to clear selections
    """
    if n_clicks:
        return []
    return dash.no_update


# Reset all filters callback


@callback(
    [
        Output("sidebar-date-dropdown", "value"),
        Output("sidebar-duration-dropdown", "value"),
        Output("sidebar-maps-size-dropdown", "value"),
        Output("sidebar-maps-class-dropdown", "value"),
        Output("sidebar-victory-dropdown", "value"),
    ],
    Input("reset-all-filters", "n_clicks"),
    prevent_initial_call=True,
)
def reset_all_filters(n_clicks: int) -> tuple:
    """Reset all filter values to defaults.

    Args:
        n_clicks: Number of reset button clicks

    Returns:
        Tuple of default values for all filters
    """
    if n_clicks:
        return (30, [], [], [], [])  # Default values
    return (dash.no_update,) * 5


def get_filter_values(
    date_range: Optional[int] = None,
    players: Optional[List[str]] = None,
    civilizations: Optional[List[str]] = None,
    durations: Optional[List[str]] = None,
    map_sizes: Optional[List[str]] = None,
    map_classes: Optional[List[str]] = None,
    victory_conditions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Combine all filter values into a single dictionary.

    Args:
        date_range: Selected date range in days
        players: Selected players
        civilizations: Selected civilizations
        durations: Selected duration categories
        map_sizes: Selected map sizes
        map_classes: Selected map classes
        victory_conditions: Selected victory conditions

    Returns:
        Dictionary containing all filter values
    """
    return {
        "date_range": date_range,
        "players": players or [],
        "civilizations": civilizations or [],
        "durations": durations or [],
        "map_sizes": map_sizes or [],
        "map_classes": map_classes or [],
        "victory_conditions": victory_conditions or [],
    }


def apply_filters_to_dataframe(
    df: pd.DataFrame, filters: Dict[str, Any], date_column: str = "save_date"
) -> pd.DataFrame:
    """Apply filter values to a DataFrame.

    Args:
        df: DataFrame to filter
        filters: Dictionary of filter values
        date_column: Name of the date column to filter on

    Returns:
        Filtered DataFrame
    """
    filtered_df = df.copy()

    # Apply date range filter
    date_range = filters.get("date_range")
    if date_range and date_range != "all" and date_column in filtered_df.columns:
        cutoff_date = datetime.now() - timedelta(days=date_range)
        filtered_df = filtered_df[
            pd.to_datetime(filtered_df[date_column]) >= cutoff_date
        ]

    # Apply player filter
    if filters.get("players") and "player_name" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["player_name"].isin(filters["players"])]

    # Apply civilization filter
    if filters.get("civilizations") and "civilization" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["civilization"].isin(filters["civilizations"])
        ]

    # Apply map size filter
    if filters.get("map_sizes") and "map_size" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["map_size"].isin(filters["map_sizes"])]

    # Apply map class filter
    if filters.get("map_classes") and "map_class" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["map_class"].isin(filters["map_classes"])]

    return filtered_df
