#!/usr/bin/env python3
"""
Script to clear existing data and re-import all tournament files with correct winner information.
This addresses the database schema changes that broke winner tracking.
"""

import logging
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tournament_visualizer.data.database import get_database
from tournament_visualizer.data.etl import process_tournament_directory

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def clear_all_data():
    """Clear all existing data from the database."""
    logger.info("Clearing all existing data...")

    db = get_database()
    db.connect()

    # Delete in reverse dependency order
    tables_to_clear = [
        "match_winners",
        "resources",
        "events",
        "territories",
        "game_state",
        "players",
        "matches",
    ]

    for table in tables_to_clear:
        try:
            result = db.execute_query(f"DELETE FROM {table}")
            logger.info(f"Cleared {table}")
        except Exception as e:
            logger.warning(f"Failed to clear {table}: {e}")

    # Reset sequences
    sequences = [
        "matches_id_seq",
        "players_id_seq",
        "game_state_id_seq",
        "territories_id_seq",
        "events_id_seq",
        "resources_id_seq",
    ]

    for seq in sequences:
        try:
            db.execute_query(f"ALTER SEQUENCE {seq} RESTART WITH 1")
            logger.info(f"Reset {seq}")
        except Exception as e:
            logger.warning(f"Failed to reset {seq}: {e}")


def main():
    """Main function to clear and re-import data."""
    logger.info("Starting data re-import process...")

    # Check if saves directory exists
    saves_dir = Path("saves")
    if not saves_dir.exists():
        logger.error(f"Saves directory not found: {saves_dir}")
        return 1

    # Clear existing data
    clear_all_data()

    # Re-import all tournament files
    logger.info("Re-importing tournament files...")
    results = process_tournament_directory(str(saves_dir))

    # Report results
    processing = results["processing"]
    logger.info("Re-import complete!")
    logger.info(
        f"Files processed: {processing['successful_files']}/{processing['total_files']}"
    )
    logger.info(f"Success rate: {processing['success_rate']:.1%}")

    # Show final data summary
    summary = results["summary"]
    logger.info("Final data counts:")
    logger.info(f"  Matches: {summary['total_matches']}")
    logger.info(f"  Players: {summary['total_players']}")
    logger.info(f"  Unique players: {summary['unique_players']}")
    logger.info(f"  Game states: {summary.get('total_game_states', 0)}")

    # Check winner data
    from tournament_visualizer.data.database import get_database

    db = get_database()
    db.connect()

    # Count matches with winners
    result = db.fetch_one("SELECT COUNT(*) FROM match_winners")
    winners_count = result[0] if result else 0

    logger.info(f"  Matches with winners: {winners_count}")

    if winners_count > 0:
        logger.info("✅ Winner data successfully restored!")
    else:
        logger.error("❌ No winner data found - there may be an issue with the parser")

    return 0 if processing["success_rate"] > 0.8 else 1


if __name__ == "__main__":
    sys.exit(main())
