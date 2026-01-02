"""CSV download utilities for chart data export.

This module provides helper functions for generating CSV downloads
from chart data with proper formatting and descriptive filenames.
"""

from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd


def generate_filename(
    chart_name: str,
    filters: Optional[Dict[str, Any]] = None,
    extension: str = "csv",
) -> str:
    """Generate descriptive filename with filters and timestamp.

    Args:
        chart_name: Name of the chart/data being exported
        filters: Dictionary of active filters (keys are filter names, values are selections)
        extension: File extension (default: 'csv')

    Returns:
        Formatted filename string

    Example:
        >>> generate_filename("science_production", {"result": "winners", "round": 3})
        'science_production_result=winners_round=3_20250130_143022.csv'
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Base filename with chart name
    parts = [chart_name.lower().replace(" ", "_")]

    # Add non-empty filters
    if filters:
        for key, value in filters.items():
            if value is not None and value != "all" and value != [] and value != "":
                # Handle list values
                if isinstance(value, list):
                    if len(value) > 0:
                        # Truncate long lists
                        if len(value) <= 2:
                            value_str = "+".join(str(v) for v in value)
                        else:
                            value_str = f"{len(value)}items"
                        parts.append(f"{key}={value_str}")
                else:
                    parts.append(f"{key}={value}")

    # Add timestamp
    parts.append(timestamp)

    return f"{'_'.join(parts)}.{extension}"


def prepare_yield_data_for_csv(
    rate_df: pd.DataFrame,
    cumulative_df: pd.DataFrame,
    yield_name: str,
) -> pd.DataFrame:
    """Prepare yield chart data for CSV export.

    Combines per-turn rate and cumulative dataframes into a single
    CSV-ready dataframe with clear column naming.

    Args:
        rate_df: DataFrame with per-turn yield statistics (median, percentiles, sample_size)
        cumulative_df: DataFrame with cumulative yield statistics
        yield_name: Display name of the yield (e.g., "Science", "Orders")

    Returns:
        Combined DataFrame ready for CSV export with columns:
        - turn_number
        - {yield}_per_turn_median
        - {yield}_per_turn_p25
        - {yield}_per_turn_p75
        - {yield}_cumulative_median
        - {yield}_cumulative_p25
        - {yield}_cumulative_p75
        - games_count
    """
    if rate_df.empty and cumulative_df.empty:
        return pd.DataFrame()

    # Start with turn numbers from whichever dataset is not empty
    base_df = rate_df if not rate_df.empty else cumulative_df
    result = pd.DataFrame({"turn_number": base_df["turn_number"]})

    # Add rate columns if available
    if not rate_df.empty:
        result[f"{yield_name.lower()}_per_turn_median"] = rate_df["median"]
        result[f"{yield_name.lower()}_per_turn_p25"] = rate_df["percentile_25"]
        result[f"{yield_name.lower()}_per_turn_p75"] = rate_df["percentile_75"]
        result["games_count"] = rate_df["sample_size"]

    # Add cumulative columns if available
    if not cumulative_df.empty:
        # If we didn't get games_count from rate, get it from cumulative
        if "games_count" not in result.columns:
            result["games_count"] = cumulative_df["sample_size"]

        result[f"{yield_name.lower()}_cumulative_median"] = cumulative_df["median"]
        result[f"{yield_name.lower()}_cumulative_p25"] = cumulative_df["percentile_25"]
        result[f"{yield_name.lower()}_cumulative_p75"] = cumulative_df["percentile_75"]

    return result


def prepare_generic_chart_data_for_csv(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare generic chart data for CSV export.

    This is a pass-through function for now, but provides a hook
    for future data formatting/cleaning logic.

    Args:
        df: Source DataFrame from query

    Returns:
        DataFrame ready for CSV export
    """
    return df.copy()
