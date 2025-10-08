"""Fix turn counts in the matches table by re-parsing save files."""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.parser import OldWorldSaveParser

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def fix_turn_counts() -> None:
    """Fix turn counts in matches table by re-parsing save files."""

    saves_dir = Path("saves")
    db = TournamentDatabase(read_only=False)

    try:
        # Get all existing matches
        existing_matches = db.fetch_all(
            "SELECT match_id, file_name, total_turns FROM matches ORDER BY match_id"
        )

        logger.info(f"Found {len(existing_matches)} matches to update")

        for match_id, file_name, old_turns in existing_matches:
            file_path = saves_dir / file_name

            if not file_path.exists():
                logger.warning(f"File not found: {file_path}, skipping...")
                continue

            try:
                # Parse the file to get correct turn count
                parser = OldWorldSaveParser(str(file_path))
                parser.extract_and_parse()
                metadata = parser.extract_basic_metadata()
                new_turns = metadata.get('total_turns', 0)

                # Update the database
                db.execute_query(
                    "UPDATE matches SET total_turns = ? WHERE match_id = ?",
                    {"1": new_turns, "2": match_id}
                )

                logger.info(f"Match {match_id} ({file_name}): {old_turns} → {new_turns} turns")

            except Exception as e:
                logger.error(f"Error processing {file_name}: {e}")
                continue

        logger.info("\n=== Turn count fix complete! ===")

        # Show updated statistics
        stats = db.fetch_one(
            "SELECT AVG(total_turns)::INT as avg_turns, MIN(total_turns) as min_turns, "
            "MAX(total_turns) as max_turns FROM matches"
        )
        logger.info(f"\nUpdated statistics:")
        logger.info(f"  Average turns: {stats[0]}")
        logger.info(f"  Min turns: {stats[1]}")
        logger.info(f"  Max turns: {stats[2]}")

    finally:
        db.close()


if __name__ == '__main__':
    fix_turn_counts()
