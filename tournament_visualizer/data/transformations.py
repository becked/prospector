"""Data transformation utilities for handling sparse/delta-encoded history data.

Old World save files (v1.0.81366+, January 2026) use delta encoding for history data,
only recording values when they change. These utilities forward-fill missing turns
to reconstruct complete time series for analysis and visualization.
"""

from typing import Optional

import pandas as pd


def forward_fill_history(
    df: pd.DataFrame,
    turn_col: str = "turn_number",
    player_col: str = "player_id",
    value_cols: Optional[list[str]] = None,
    min_turn: Optional[int] = None,
    max_turn: Optional[int] = None,
    preserve_columns: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Forward-fill sparse player history to complete time series.

    Handles delta-encoded history where values are only recorded when they change.
    For each player, fills missing turns with the last known value.

    Args:
        df: DataFrame with player history data
        turn_col: Column name for turn numbers
        player_col: Column name for player identifier
        value_cols: Column names for values to forward-fill. If None, all numeric
            columns except turn_col and player_col are used.
        min_turn: Minimum turn to fill from (default: df minimum)
        max_turn: Maximum turn to fill to (default: df maximum)
        preserve_columns: Additional columns to preserve (forward-filled with values).
            Useful for player_name, civilization, etc.

    Returns:
        DataFrame with complete turn range for each player, forward-filled values.
        Returns empty DataFrame if input is empty.

    Example:
        >>> # Sparse input: player has data at turns 1, 5, 10
        >>> df = pd.DataFrame({
        ...     'turn_number': [1, 5, 10],
        ...     'player_id': [1, 1, 1],
        ...     'military_power': [100, 150, 200]
        ... })
        >>> filled = forward_fill_history(df, value_cols=['military_power'])
        >>> # Output has turns 1-10 with values [100, 100, 100, 100, 150, 150, ...]
    """
    if df.empty:
        return df.copy()

    # Determine turn range
    if min_turn is None:
        min_turn = int(df[turn_col].min())
    if max_turn is None:
        max_turn = int(df[turn_col].max())

    all_turns = list(range(min_turn, max_turn + 1))

    # Determine value columns to fill
    if value_cols is None:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        value_cols = [c for c in numeric_cols if c not in [turn_col, player_col]]

    # Columns to preserve (forward-fill along with values)
    preserve_cols = preserve_columns or []

    players = df[player_col].unique()
    filled_dfs = []

    for player_id in players:
        player_data = df[df[player_col] == player_id].copy()

        # Get columns to include in output
        cols_to_fill = value_cols + preserve_cols
        subset_cols = [turn_col] + [c for c in cols_to_fill if c in player_data.columns]

        player_subset = player_data[subset_cols].drop_duplicates(subset=[turn_col])
        player_subset = player_subset.set_index(turn_col)

        # Reindex to all turns and forward-fill
        player_filled = player_subset.reindex(all_turns)
        player_filled = player_filled.ffill()

        # Fill any leading NaNs with 0 for numeric columns, first valid for others
        for col in value_cols:
            if col in player_filled.columns:
                player_filled[col] = player_filled[col].fillna(0)

        for col in preserve_cols:
            if col in player_filled.columns:
                player_filled[col] = player_filled[col].bfill().ffill()

        # Reset index and add player_id back
        player_filled = player_filled.reset_index()
        player_filled = player_filled.rename(columns={"index": turn_col})
        player_filled[player_col] = player_id

        filled_dfs.append(player_filled)

    result = pd.concat(filled_dfs, ignore_index=True)

    # Reorder columns to match input pattern
    output_cols = [turn_col, player_col] + [
        c for c in result.columns if c not in [turn_col, player_col]
    ]
    return result[output_cols]


def forward_fill_history_by_category(
    df: pd.DataFrame,
    turn_col: str = "turn_number",
    player_col: str = "player_id",
    category_col: str = "resource_type",
    value_col: str = "amount",
    min_turn: Optional[int] = None,
    max_turn: Optional[int] = None,
    preserve_columns: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Forward-fill sparse history with multiple categories per player.

    Handles data like yield history where each player has multiple resource types,
    each recorded independently with delta encoding. Each (player, category)
    combination is forward-filled independently.

    Args:
        df: DataFrame with categorized player history data
        turn_col: Column name for turn numbers
        player_col: Column name for player identifier
        category_col: Column name for category (e.g., 'resource_type')
        value_col: Column name for the value to forward-fill
        min_turn: Minimum turn to fill from (default: df minimum)
        max_turn: Maximum turn to fill to (default: df maximum)
        preserve_columns: Additional columns to preserve per player
            (e.g., player_name, civilization)

    Returns:
        DataFrame with complete turn range for each (player, category) combination.
        Returns empty DataFrame if input is empty.

    Example:
        >>> # Yield history with sparse YIELD_SCIENCE and YIELD_TRAINING
        >>> df = pd.DataFrame({
        ...     'turn_number': [1, 5, 1, 3],
        ...     'player_id': [1, 1, 1, 1],
        ...     'resource_type': ['YIELD_SCIENCE', 'YIELD_SCIENCE', 'YIELD_TRAINING', 'YIELD_TRAINING'],
        ...     'amount': [10, 15, 20, 25]
        ... })
        >>> filled = forward_fill_history_by_category(df)
        >>> # Each resource_type now has turns 1-5 filled
    """
    if df.empty:
        return df.copy()

    # Determine turn range
    if min_turn is None:
        min_turn = int(df[turn_col].min())
    if max_turn is None:
        max_turn = int(df[turn_col].max())

    all_turns = list(range(min_turn, max_turn + 1))

    # Columns to preserve per player (not per category)
    preserve_cols = preserve_columns or []

    # Get unique (player, category) combinations
    players = df[player_col].unique()
    categories = df[category_col].unique()

    filled_dfs = []

    for player_id in players:
        player_data = df[df[player_col] == player_id]

        # Get preserved values for this player (take first occurrence)
        preserved_values = {}
        for col in preserve_cols:
            if col in player_data.columns:
                preserved_values[col] = player_data[col].iloc[0]

        for category in categories:
            cat_data = player_data[player_data[category_col] == category].copy()

            if cat_data.empty:
                # This player doesn't have this category - skip
                continue

            # Get subset with turn and value
            cat_subset = cat_data[[turn_col, value_col]].drop_duplicates(
                subset=[turn_col]
            )
            cat_subset = cat_subset.set_index(turn_col)

            # Reindex and forward-fill
            cat_filled = cat_subset.reindex(all_turns)
            cat_filled = cat_filled.ffill().fillna(0)
            cat_filled = cat_filled.reset_index()
            cat_filled = cat_filled.rename(columns={"index": turn_col})

            # Add back player_id and category
            cat_filled[player_col] = player_id
            cat_filled[category_col] = category

            # Add preserved columns
            for col, val in preserved_values.items():
                cat_filled[col] = val

            filled_dfs.append(cat_filled)

    if not filled_dfs:
        return df.iloc[:0].copy()  # Return empty DataFrame with same structure

    result = pd.concat(filled_dfs, ignore_index=True)

    # Reorder columns to match input pattern
    base_cols = [turn_col, player_col, category_col, value_col]
    other_cols = [c for c in result.columns if c not in base_cols]
    output_cols = base_cols + other_cols
    return result[[c for c in output_cols if c in result.columns]]


def is_sparse_history(
    df: pd.DataFrame,
    turn_col: str = "turn_number",
    player_col: str = "player_id",
    threshold: float = 0.9,
) -> bool:
    """Check if history data appears to be delta-encoded (sparse).

    Useful for conditional forward-fill as an optimization when processing
    matches with complete data (pre-January 2026).

    Args:
        df: DataFrame with player history data
        turn_col: Column name for turn numbers
        player_col: Column name for player identifier
        threshold: Density threshold below which data is considered sparse
            (default: 0.9 = 90%)

    Returns:
        True if data density is below threshold, indicating delta-encoding.

    Example:
        >>> if is_sparse_history(military_df):
        ...     military_df = forward_fill_history(military_df)
    """
    if df.empty:
        return False

    min_turn = df[turn_col].min()
    max_turn = df[turn_col].max()
    num_players = df[player_col].nunique()

    expected_rows = (max_turn - min_turn + 1) * num_players
    actual_rows = len(df.drop_duplicates(subset=[turn_col, player_col]))

    if expected_rows == 0:
        return False

    density = actual_rows / expected_rows
    return bool(density < threshold)
