#!/usr/bin/env python3
"""Sync pick order data from Google Sheets to database.

This script:
1. Fetches GAMEDATA sheet from Google Sheets
2. Parses the multi-column game layout
3. Stores parsed data in pick_order_games table
4. Does NOT match to matches table (separate script handles that)

Usage:
    python scripts/sync_pick_order_data.py [--dry-run] [--verbose]

Examples:
    # Sync pick order data (default)
    python scripts/sync_pick_order_data.py

    # See what would be synced without writing
    python scripts/sync_pick_order_data.py --dry-run

    # Verbose logging
    python scripts/sync_pick_order_data.py --verbose
"""

import argparse
import logging
import sys
from pathlib import Path

import duckdb
from dotenv import load_dotenv

# Load environment variables BEFORE importing Config
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tournament_visualizer.config import Config
from tournament_visualizer.data.gamedata_parser import parse_gamedata_sheet
from tournament_visualizer.data.gsheets_client import GoogleSheetsClient

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def sync_pick_order_data(dry_run: bool = False) -> None:
    """Fetch and sync pick order data from Google Sheets.

    Args:
        dry_run: If True, don't write to database

    Raises:
        ValueError: If configuration is invalid
        Exception: If sync fails
    """
    # Verify configuration
    if not Config.GOOGLE_DRIVE_API_KEY:
        raise ValueError(
            "GOOGLE_DRIVE_API_KEY not set. "
            "Add it to .env file to access Google Sheets."
        )

    if not Config.GOOGLE_SHEETS_SPREADSHEET_ID:
        raise ValueError("GOOGLE_SHEETS_SPREADSHEET_ID not set")

    logger.info("Fetching pick order data from Google Sheets...")
    logger.info(f"  Spreadsheet: {Config.GOOGLE_SHEETS_SPREADSHEET_ID}")
    logger.info(f"  Sheet GID: {Config.GOOGLE_SHEETS_GAMEDATA_GID}")

    # Initialize Google Sheets client
    client = GoogleSheetsClient(api_key=Config.GOOGLE_DRIVE_API_KEY)

    # Fetch sheet data
    # Use a large range to capture all data (adjust if needed)
    range_name = "GAMEDATA!A1:Z200"

    logger.info(f"Fetching range: {range_name}")

    try:
        values = client.get_sheet_values(
            spreadsheet_id=Config.GOOGLE_SHEETS_SPREADSHEET_ID,
            range_name=range_name,
        )
    except Exception as e:
        logger.error(f"Failed to fetch sheet data: {e}")
        raise

    logger.info(f"✓ Fetched {len(values)} rows from sheet")

    # Parse sheet data
    logger.info("Parsing game data...")

    try:
        games = parse_gamedata_sheet(values)
    except Exception as e:
        logger.error(f"Failed to parse sheet: {e}")
        raise

    logger.info(f"✓ Parsed {len(games)} games")

    if not games:
        logger.warning("No games found in sheet - nothing to sync")
        return

    # Show sample of parsed data
    logger.info("\nSample of parsed games:")
    for game in games[:3]:
        logger.info(
            f"  Game {game['game_number']} (Round {game['round_number']}): "
            f"{game['player1_sheet_name']} vs {game['player2_sheet_name']}"
        )
        logger.info(
            f"    First: {game['first_pick_nation']}, "
            f"Second: {game['second_pick_nation']}"
        )

    if dry_run:
        logger.info("\n[DRY RUN] Would sync %d games to database", len(games))
        return

    # Write to database
    logger.info(f"\nWriting {len(games)} games to database...")

    conn = duckdb.connect(Config.DATABASE_PATH)

    try:
        # Clear existing data (full replace)
        conn.execute("DELETE FROM pick_order_games")
        logger.info("✓ Cleared existing pick_order_games data")

        # Insert new data
        insert_sql = """
        INSERT INTO pick_order_games (
            game_number,
            round_number,
            round_label,
            player1_sheet_name,
            player2_sheet_name,
            first_pick_nation,
            second_pick_nation
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """

        for game in games:
            conn.execute(
                insert_sql,
                [
                    game['game_number'],
                    game['round_number'],
                    game['round_label'],
                    game['player1_sheet_name'],
                    game['player2_sheet_name'],
                    game['first_pick_nation'],
                    game['second_pick_nation'],
                ],
            )

        logger.info(f"✓ Inserted {len(games)} games")

        # Show stats
        result = conn.execute("""
            SELECT
                COUNT(*) as total_games,
                COUNT(DISTINCT round_number) as total_rounds,
                MIN(game_number) as min_game,
                MAX(game_number) as max_game
            FROM pick_order_games
        """).fetchone()

        logger.info("\nDatabase statistics:")
        logger.info(f"  Total games: {result[0]}")
        logger.info(f"  Total rounds: {result[1]}")
        logger.info(f"  Game number range: {result[2]}-{result[3]}")

        # Show unmatched games (should be all at this point)
        unmatched = conn.execute("""
            SELECT COUNT(*)
            FROM pick_order_games
            WHERE matched_match_id IS NULL
        """).fetchone()[0]

        logger.info(f"  Unmatched games: {unmatched}")
        logger.info(
            "  (Run match_pick_order_games.py to link to matches table)"
        )

    finally:
        conn.close()

    logger.info("\n✓ Pick order data sync complete")


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Sync pick order data from Google Sheets"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing to database",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    setup_logging(args.verbose)

    try:
        sync_pick_order_data(dry_run=args.dry_run)
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
