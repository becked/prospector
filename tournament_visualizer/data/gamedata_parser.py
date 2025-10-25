"""Parser for Google Sheets GAMEDATA tab tournament data.

This module parses the complex multi-column game layout from the
GAMEDATA sheet and extracts pick order information.

The sheet has a complex structure:
- Multiple rounds, each with different row offsets
- Multiple games per round, spanning columns
- Dynamic game column positions
- Row labels like "Nation; First Pick", "Second Pick", etc.

Example usage:
    >>> from tournament_visualizer.data.gsheets_client import GoogleSheetsClient
    >>> from tournament_visualizer.config import Config
    >>>
    >>> client = GoogleSheetsClient(Config.GOOGLE_DRIVE_API_KEY)
    >>> values = client.get_sheet_values(
    ...     Config.GOOGLE_SHEETS_SPREADSHEET_ID,
    ...     "GAMEDATA *SPOILER WARNING*!A1:Z200"
    ... )
    >>>
    >>> games = parse_gamedata_sheet(values)
    >>> print(f"Parsed {len(games)} games")
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def parse_gamedata_sheet(rows: list[list[str]]) -> list[dict[str, Any]]:
    """Parse the GAMEDATA sheet into structured game data.

    Args:
        rows: Raw sheet data (list of rows, each row is list of cells)

    Returns:
        List of game dictionaries with keys:
        - game_number: Game number from sheet
        - round_number: Round number (1, 2, 3, ...)
        - round_label: Full round label text
        - player1_sheet_name: First player name
        - player2_sheet_name: Second player name
        - first_pick_nation: Nation picked first
        - second_pick_nation: Nation picked second

    Raises:
        ValueError: If sheet structure is invalid or parsing fails
    """
    games = []

    # Find all round sections
    round_sections = find_round_sections(rows)

    logger.info(f"Found {len(round_sections)} round sections")

    for round_info in round_sections:
        try:
            round_games = parse_round_section(rows, round_info)
            games.extend(round_games)
            logger.info(f"Parsed {len(round_games)} games from {round_info['label']}")
        except Exception as e:
            logger.error(f"Failed to parse round {round_info['label']}: {e}")
            # Continue with other rounds

    logger.info(f"Parsed total of {len(games)} games from sheet")

    return games


def find_round_sections(rows: list[list[str]]) -> list[dict[str, Any]]:
    """Find all round sections in the sheet.

    Scans column A for "ROUND X" pattern to identify round boundaries.

    Args:
        rows: Raw sheet data

    Returns:
        List of round info dictionaries with keys:
        - round_number: Extracted round number (1, 2, 3, ...)
        - label: Full round label text
        - start_row: Row index where round starts
    """
    rounds = []
    round_pattern = re.compile(r"ROUND\s+(\d+)", re.IGNORECASE)

    for row_idx, row in enumerate(rows):
        if not row:
            continue

        # Check column A for round label
        col_a = row[0] if len(row) > 0 else ""

        match = round_pattern.search(col_a)
        if match:
            round_num = int(match.group(1))
            rounds.append(
                {
                    "round_number": round_num,
                    "label": col_a.strip(),
                    "start_row": row_idx,
                }
            )

    return rounds


def parse_round_section(
    rows: list[list[str]], round_info: dict[str, Any]
) -> list[dict[str, Any]]:
    """Parse games from a single round section.

    Args:
        rows: Raw sheet data
        round_info: Round metadata from find_round_sections()

    Returns:
        List of game dictionaries for this round

    Raises:
        ValueError: If critical rows not found
    """
    start_row = round_info["start_row"]
    round_number = round_info["round_number"]
    round_label = round_info["label"]

    # Find the key rows within this round section
    # Scan the next ~30 rows after round header
    search_range = rows[start_row : start_row + 30]

    game_number_row_idx = find_row_by_label(search_range, "Game Number")
    players_row_idx = find_row_by_label(search_range, "Players")
    first_pick_row_idx = find_row_by_label(search_range, "Nation; First Pick")
    second_pick_row_idx = find_row_by_label(search_range, "Second Pick")

    if game_number_row_idx is None:
        raise ValueError(f"Could not find 'Game Number' row in round {round_number}")

    if first_pick_row_idx is None:
        raise ValueError(
            f"Could not find 'Nation; First Pick' row in round {round_number}"
        )

    if second_pick_row_idx is None:
        raise ValueError(f"Could not find 'Second Pick' row in round {round_number}")

    if players_row_idx is None:
        raise ValueError(f"Could not find 'Players' row in round {round_number}")

    # Convert to absolute row indices
    game_number_row_idx += start_row
    players_row_idx += start_row
    first_pick_row_idx += start_row
    second_pick_row_idx += start_row

    # Get the actual row data
    game_number_row = rows[game_number_row_idx]
    players_row = rows[players_row_idx]
    first_pick_row = rows[first_pick_row_idx]
    second_pick_row = rows[second_pick_row_idx]

    # Find game columns by detecting "Game N" in game_number_row
    game_columns = find_game_columns(game_number_row)

    logger.debug(
        f"Round {round_number}: Found {len(game_columns)} games at columns {game_columns}"
    )

    # Parse each game
    games = []

    for col_info in game_columns:
        try:
            game = parse_game_columns(
                game_number_row=game_number_row,
                players_row=players_row,
                first_pick_row=first_pick_row,
                second_pick_row=second_pick_row,
                game_col_start=col_info["col_start"],
                game_col_end=col_info["col_end"],
                round_number=round_number,
                round_label=round_label,
            )

            if game:
                games.append(game)

        except Exception as e:
            logger.warning(
                f"Failed to parse game at columns {col_info['col_start']}-{col_info['col_end']}: {e}"
            )

    return games


def find_row_by_label(rows: list[list[str]], label: str) -> int | None:
    """Find row index by searching for label in column A.

    Args:
        rows: List of rows to search
        label: Label text to find (case-insensitive)

    Returns:
        Row index (relative to input rows), or None if not found
    """
    label_lower = label.lower()

    for idx, row in enumerate(rows):
        if not row:
            continue

        col_a = row[0] if len(row) > 0 else ""

        if label_lower in col_a.lower():
            return idx

    return None


def find_game_columns(game_number_row: list[str]) -> list[dict[str, int]]:
    """Find column ranges for each game.

    Detects "Game N" in the row and returns the column span for each game.

    Args:
        game_number_row: The row containing "Game 1", "Game 2", etc.

    Returns:
        List of dicts with keys:
        - game_number: Extracted game number
        - col_start: Starting column index
        - col_end: Ending column index (inclusive)

    Example:
        Row: ["", "", "Game 1", "", "Game 2", "", "", "Game 3"]
        Returns: [
            {"game_number": 1, "col_start": 2, "col_end": 3},
            {"game_number": 2, "col_start": 4, "col_end": 6},
            {"game_number": 3, "col_start": 7, "col_end": ...},
        ]
    """
    games = []
    game_pattern = re.compile(r"Game\s+(\d+)", re.IGNORECASE)

    # Find all columns with "Game N"
    game_starts = []

    for col_idx, cell in enumerate(game_number_row):
        if not cell:
            continue

        match = game_pattern.search(cell)
        if match:
            game_num = int(match.group(1))
            game_starts.append(
                {
                    "game_number": game_num,
                    "col_start": col_idx,
                }
            )

    # Determine column end for each game
    # Typically 2-3 columns per game (player columns + possible gap)
    for i, game in enumerate(game_starts):
        if i < len(game_starts) - 1:
            # End is just before next game starts
            game["col_end"] = game_starts[i + 1]["col_start"] - 1
        else:
            # Last game - extend a reasonable amount (3 columns)
            game["col_end"] = game["col_start"] + 3

        games.append(game)

    return games


def parse_game_columns(
    game_number_row: list[str],
    players_row: list[str],
    first_pick_row: list[str],
    second_pick_row: list[str],
    game_col_start: int,
    game_col_end: int,
    round_number: int,
    round_label: str,
) -> dict[str, Any] | None:
    """Parse game data from column range.

    Args:
        game_number_row: Row with "Game N" labels
        players_row: Row with "Players" label and player names
        first_pick_row: Row with "Nation; First Pick" label and nation
        second_pick_row: Row with "Second Pick" label and nation
        game_col_start: Starting column index for this game
        game_col_end: Ending column index for this game
        round_number: Round number
        round_label: Full round label text

    Returns:
        Game dictionary, or None if data is incomplete
    """
    # Extract game number from header
    game_number = None
    game_pattern = re.compile(r"Game\s+(\d+)", re.IGNORECASE)

    for col in range(game_col_start, min(game_col_end + 1, len(game_number_row))):
        cell = game_number_row[col] if col < len(game_number_row) else ""
        match = game_pattern.search(cell)
        if match:
            game_number = int(match.group(1))
            break

    if not game_number:
        logger.debug(f"No game number found in columns {game_col_start}-{game_col_end}")
        return None

    # Extract player names (skip label column)
    players = []
    for col in range(game_col_start, min(game_col_end + 1, len(players_row))):
        cell = players_row[col] if col < len(players_row) else ""

        # Skip label column and empty cells
        if cell and "Players" not in cell:
            players.append(cell.strip())

    if len(players) < 2:
        logger.debug(f"Game {game_number}: Found only {len(players)} players")
        return None

    # Extract nations (skip label column)
    first_pick_nation = None
    second_pick_nation = None

    for col in range(game_col_start, min(game_col_end + 1, len(first_pick_row))):
        cell = first_pick_row[col] if col < len(first_pick_row) else ""

        # Skip label column and empty cells
        if cell and "Nation" not in cell and "First Pick" not in cell:
            first_pick_nation = cell.strip()
            break

    for col in range(game_col_start, min(game_col_end + 1, len(second_pick_row))):
        cell = second_pick_row[col] if col < len(second_pick_row) else ""

        # Skip label column and empty cells
        if cell and "Second Pick" not in cell:
            second_pick_nation = cell.strip()
            break

    if not first_pick_nation or not second_pick_nation:
        logger.debug(
            f"Game {game_number}: Missing nation data "
            f"(first={first_pick_nation}, second={second_pick_nation})"
        )
        return None

    return {
        "game_number": game_number,
        "round_number": round_number,
        "round_label": round_label,
        "player1_sheet_name": players[0],
        "player2_sheet_name": players[1] if len(players) > 1 else "",
        "first_pick_nation": first_pick_nation,
        "second_pick_nation": second_pick_nation,
    }
