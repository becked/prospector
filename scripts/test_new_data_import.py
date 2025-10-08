"""Test script to verify new statistics data import."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.etl import TournamentETL

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def test_import() -> None:
    """Test importing a single file with new statistics."""

    # Pick a sample file
    test_file = "saves/match_426504722_OW-Greece-Year92-2025-09-20-16-12-58.zip"

    logger.info(f"Testing import of: {test_file}")

    # Create database and ETL instances
    db = TournamentDatabase(read_only=False)
    etl = TournamentETL(db)

    try:
        # Process the file
        success = etl.process_tournament_file(test_file)

        if success:
            logger.info("✓ File import successful!")

            # Query to check the data
            logger.info("\nChecking imported data...")

            # Get the match_id for this file
            result = db.fetch_one(
                "SELECT match_id FROM matches WHERE file_name = ? ORDER BY processed_date DESC LIMIT 1",
                {"1": Path(test_file).name},
            )

            if result:
                match_id = result[0]
                logger.info(f"Match ID: {match_id}")

                # Check technology progress
                tech_count = db.fetch_one(
                    "SELECT COUNT(*) FROM technology_progress WHERE match_id = ?",
                    {"1": match_id},
                )
                logger.info(
                    f"  Technology progress records: {tech_count[0] if tech_count else 0}"
                )

                # Check player statistics
                stats_count = db.fetch_one(
                    "SELECT COUNT(*) FROM player_statistics WHERE match_id = ?",
                    {"1": match_id},
                )
                logger.info(
                    f"  Player statistics records: {stats_count[0] if stats_count else 0}"
                )

                # Check match metadata
                metadata = db.fetch_one(
                    "SELECT difficulty, victory_type FROM match_metadata WHERE match_id = ?",
                    {"1": match_id},
                )
                if metadata:
                    logger.info(
                        f"  Match metadata: Difficulty={metadata[0]}, Victory={metadata[1]}"
                    )

                # Show some sample tech data
                logger.info("\nSample technology data:")
                techs = db.fetch_all(
                    """
                    SELECT p.player_name, tp.tech_name, tp.count
                    FROM technology_progress tp
                    JOIN players p ON tp.player_id = p.player_id
                    WHERE tp.match_id = ?
                    LIMIT 5
                    """,
                    {"1": match_id},
                )
                for player_name, tech_name, count in techs:
                    logger.info(f"    {player_name}: {tech_name} x{count}")

                # Show some sample statistics
                logger.info("\nSample player statistics:")
                stats = db.fetch_all(
                    """
                    SELECT p.player_name, ps.stat_category, ps.stat_name, ps.value
                    FROM player_statistics ps
                    JOIN players p ON ps.player_id = p.player_id
                    WHERE ps.match_id = ? AND ps.stat_category = 'yield_stockpile'
                    LIMIT 5
                    """,
                    {"1": match_id},
                )
                for player_name, cat, name, value in stats:
                    logger.info(f"    {player_name} {cat}/{name}: {value}")

            else:
                logger.error("Could not find match record!")
        else:
            logger.error("✗ File import failed!")

    except Exception as e:
        logger.error(f"Error during import: {e}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    test_import()
