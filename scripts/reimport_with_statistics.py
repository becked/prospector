"""Reimport all tournament files to populate new statistics tables."""

import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.etl import TournamentETL
from tournament_visualizer.data.parser import parse_tournament_file

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def reimport_all() -> None:
    """Reimport all files to populate statistics tables."""

    saves_dir = Path("saves")
    db = TournamentDatabase(read_only=False)
    etl = TournamentETL(db)

    try:
        # Get all existing match file hashes
        existing_matches = db.fetch_all(
            "SELECT match_id, file_name, file_hash FROM matches ORDER BY match_id"
        )

        logger.info(f"Found {len(existing_matches)} existing matches to update")

        for match_id, file_name, file_hash in existing_matches:
            file_path = saves_dir / file_name

            if not file_path.exists():
                logger.warning(f"File not found: {file_path}, skipping...")
                continue

            logger.info(f"\nProcessing match {match_id}: {file_name}")

            try:
                # Parse the file
                parsed_data = parse_tournament_file(str(file_path))

                # Get player ID mapping
                players = db.fetch_all(
                    "SELECT player_id FROM players WHERE match_id = ? ORDER BY player_id",
                    {"1": match_id},
                )
                player_id_mapping = {i + 1: pid[0] for i, pid in enumerate(players)}

                # Process technology progress
                technology_progress = parsed_data.get("technology_progress", [])
                for tech_data in technology_progress:
                    tech_data["match_id"] = match_id
                    if tech_data.get("player_id") in player_id_mapping:
                        tech_data["player_id"] = player_id_mapping[
                            tech_data["player_id"]
                        ]

                if technology_progress:
                    db.bulk_insert_technology_progress(technology_progress)
                    logger.info(
                        f"  ✓ Inserted {len(technology_progress)} technology records"
                    )

                # Process player statistics
                player_statistics = parsed_data.get("player_statistics", [])
                for stat_data in player_statistics:
                    stat_data["match_id"] = match_id
                    if stat_data.get("player_id") in player_id_mapping:
                        stat_data["player_id"] = player_id_mapping[
                            stat_data["player_id"]
                        ]

                if player_statistics:
                    db.bulk_insert_player_statistics(player_statistics)
                    logger.info(
                        f"  ✓ Inserted {len(player_statistics)} statistics records"
                    )

                # Process match metadata
                detailed_metadata = parsed_data.get("detailed_metadata", {})
                if detailed_metadata:
                    db.insert_match_metadata(match_id, detailed_metadata)
                    logger.info("  ✓ Inserted match metadata")

            except Exception as e:
                logger.error(f"  ✗ Error processing {file_name}: {e}")
                continue

        logger.info("\n=== Reimport complete! ===")

        # Show summary statistics
        tech_total = db.fetch_one("SELECT COUNT(*) FROM technology_progress")[0]
        stats_total = db.fetch_one("SELECT COUNT(*) FROM player_statistics")[0]
        metadata_total = db.fetch_one("SELECT COUNT(*) FROM match_metadata")[0]

        logger.info("\nTotal records inserted:")
        logger.info(f"  Technology progress: {tech_total}")
        logger.info(f"  Player statistics: {stats_total}")
        logger.info(f"  Match metadata: {metadata_total}")

    finally:
        db.close()


if __name__ == "__main__":
    reimport_all()
