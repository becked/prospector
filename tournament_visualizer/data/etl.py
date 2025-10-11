"""ETL (Extract, Transform, Load) pipeline for tournament data.

This module orchestrates the extraction of data from Old World save files,
transformation into the appropriate format, and loading into the DuckDB database.
"""

import hashlib
import logging
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .database import TournamentDatabase, get_database
from .parser import parse_tournament_file

logger = logging.getLogger(__name__)


class TournamentETL:
    """ETL pipeline for processing tournament save files."""

    def __init__(self, database: Optional[TournamentDatabase] = None) -> None:
        """Initialize ETL pipeline.

        Args:
            database: Database instance to use (defaults to global instance)
        """
        self.db = database or get_database()

    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of a file.

        Args:
            file_path: Path to the file

        Returns:
            SHA256 hash as hex string
        """
        sha256_hash = hashlib.sha256()

        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)

        return sha256_hash.hexdigest()

    def is_file_processed(self, file_path: str) -> bool:
        """Check if a file has already been processed.

        Args:
            file_path: Path to the file to check

        Returns:
            True if file already exists in database
        """
        filename = Path(file_path).name
        file_hash = self.calculate_file_hash(file_path)

        return self.db.file_already_processed(filename, file_hash)

    def process_tournament_file(
        self, file_path: str, challonge_match_id: Optional[int] = None
    ) -> bool:
        """Process a single tournament save file.

        Args:
            file_path: Path to the tournament save zip file
            challonge_match_id: Optional Challonge match ID to associate

        Returns:
            True if processing was successful, False otherwise
        """
        try:
            # Check if file already processed
            if self.is_file_processed(file_path):
                logger.info(f"File already processed: {file_path}")
                return True

            logger.info(f"Processing tournament file: {file_path}")

            # Calculate file hash
            file_hash = self.calculate_file_hash(file_path)

            # Parse the file
            parsed_data = parse_tournament_file(file_path)

            # Add file tracking information
            match_metadata = parsed_data["match_metadata"]
            match_metadata["file_hash"] = file_hash
            if challonge_match_id:
                match_metadata["challonge_match_id"] = challonge_match_id

            # Transform and load data
            self._load_tournament_data(parsed_data)

            logger.info(f"Successfully processed: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            logger.error(traceback.format_exc())
            return False

    def _load_tournament_data(self, parsed_data: Dict[str, Any]) -> None:
        """Load parsed tournament data into the database.

        Args:
            parsed_data: Dictionary containing all parsed data
        """
        # Start with match data (without winner_player_id for now)
        match_metadata = parsed_data["match_metadata"].copy()
        original_winner_id = match_metadata.pop("winner_player_id", None)
        match_id = self.db.insert_match(match_metadata)

        logger.info(f"Inserted match with ID: {match_id}")

        # Process players
        players_data = parsed_data["players"]
        player_id_mapping = {}  # Map original index to database ID
        winner_db_id = None

        for i, player_data in enumerate(players_data):
            player_data["match_id"] = match_id
            player_id = self.db.insert_player(player_data)
            original_player_id = i + 1  # Assuming 1-based indexing
            player_id_mapping[original_player_id] = player_id

            # Check if this is the winner
            if original_winner_id and original_player_id == original_winner_id:
                winner_db_id = player_id

        logger.info(f"Inserted {len(players_data)} players")

        # Insert winner information into separate table
        if winner_db_id:
            self.db.insert_match_winner(match_id, winner_db_id, "parser_determined")
            logger.info(f"Recorded winner: player_id {winner_db_id}")

        # Process events
        events = parsed_data["events"]
        for event_data in events:
            event_data["match_id"] = match_id
            # Map player_id if present
            if (
                event_data.get("player_id")
                and event_data["player_id"] in player_id_mapping
            ):
                event_data["player_id"] = player_id_mapping[event_data["player_id"]]

        if events:
            self.db.bulk_insert_events(events)
            logger.info(f"Inserted {len(events)} events")

        # Process territories
        territories = parsed_data["territories"]
        for territory_data in territories:
            territory_data["match_id"] = match_id
            # Map owner_player_id if present
            if (
                territory_data.get("owner_player_id")
                and territory_data["owner_player_id"] in player_id_mapping
            ):
                territory_data["owner_player_id"] = player_id_mapping[
                    territory_data["owner_player_id"]
                ]

        if territories:
            self.db.bulk_insert_territories(territories)
            logger.info(f"Inserted {len(territories)} territory records")

        # Process resources
        resources = parsed_data["resources"]
        for resource_data in resources:
            resource_data["match_id"] = match_id
            # Map player_id if present
            if (
                resource_data.get("player_id")
                and resource_data["player_id"] in player_id_mapping
            ):
                resource_data["player_id"] = player_id_mapping[
                    resource_data["player_id"]
                ]

        if resources:
            self.db.bulk_insert_yield_history(resources)
            logger.info(f"Inserted {len(resources)} resource records")

        # Process technology progress
        technology_progress = parsed_data.get("technology_progress", [])
        for tech_data in technology_progress:
            tech_data["match_id"] = match_id
            # Map player_id if present
            if (
                tech_data.get("player_id")
                and tech_data["player_id"] in player_id_mapping
            ):
                tech_data["player_id"] = player_id_mapping[tech_data["player_id"]]

        if technology_progress:
            self.db.bulk_insert_technology_progress(technology_progress)
            logger.info(
                f"Inserted {len(technology_progress)} technology progress records"
            )

        # Process player statistics
        player_statistics = parsed_data.get("player_statistics", [])
        for stat_data in player_statistics:
            stat_data["match_id"] = match_id
            # Map player_id if present
            if (
                stat_data.get("player_id")
                and stat_data["player_id"] in player_id_mapping
            ):
                stat_data["player_id"] = player_id_mapping[stat_data["player_id"]]

        if player_statistics:
            self.db.bulk_insert_player_statistics(player_statistics)
            logger.info(f"Inserted {len(player_statistics)} player statistics records")

        # Process units produced
        units_produced = parsed_data.get("units_produced", [])
        for unit_data in units_produced:
            unit_data["match_id"] = match_id
            # Map player_id if present
            if (
                unit_data.get("player_id")
                and unit_data["player_id"] in player_id_mapping
            ):
                unit_data["player_id"] = player_id_mapping[unit_data["player_id"]]

        if units_produced:
            self.db.bulk_insert_units_produced(units_produced)
            logger.info(f"Inserted {len(units_produced)} units produced records")

        # Process match metadata
        detailed_metadata = parsed_data.get("detailed_metadata", {})
        if detailed_metadata:
            self.db.insert_match_metadata(match_id, detailed_metadata)
            logger.info("Inserted match metadata")

        # ========================================================================
        # Process turn-by-turn history data
        # ========================================================================

        # Process points history
        points_history = parsed_data.get("points_history", [])
        for point_data in points_history:
            point_data["match_id"] = match_id
            # Map player_id if present
            if (
                point_data.get("player_id")
                and point_data["player_id"] in player_id_mapping
            ):
                point_data["player_id"] = player_id_mapping[point_data["player_id"]]

        if points_history:
            self.db.bulk_insert_points_history(points_history)
            logger.info(f"Inserted {len(points_history)} points history records")

        # Process yield history
        yield_history = parsed_data.get("yield_history", [])
        for yield_data in yield_history:
            yield_data["match_id"] = match_id
            # Map player_id if present
            if (
                yield_data.get("player_id")
                and yield_data["player_id"] in player_id_mapping
            ):
                yield_data["player_id"] = player_id_mapping[yield_data["player_id"]]

        if yield_history:
            self.db.bulk_insert_yield_history(yield_history)
            logger.info(f"Inserted {len(yield_history)} yield history records")

        # Process military history
        military_history = parsed_data.get("military_history", [])
        for military_data in military_history:
            military_data["match_id"] = match_id
            # Map player_id if present
            if (
                military_data.get("player_id")
                and military_data["player_id"] in player_id_mapping
            ):
                military_data["player_id"] = player_id_mapping[
                    military_data["player_id"]
                ]

        if military_history:
            self.db.bulk_insert_military_history(military_history)
            logger.info(f"Inserted {len(military_history)} military history records")

        # Process legitimacy history
        legitimacy_history = parsed_data.get("legitimacy_history", [])
        for legitimacy_data in legitimacy_history:
            legitimacy_data["match_id"] = match_id
            # Map player_id if present
            if (
                legitimacy_data.get("player_id")
                and legitimacy_data["player_id"] in player_id_mapping
            ):
                legitimacy_data["player_id"] = player_id_mapping[
                    legitimacy_data["player_id"]
                ]

        if legitimacy_history:
            self.db.bulk_insert_legitimacy_history(legitimacy_history)
            logger.info(f"Inserted {len(legitimacy_history)} legitimacy history records")

        # Process family opinion history
        family_opinion_history = parsed_data.get("family_opinion_history", [])
        for opinion_data in family_opinion_history:
            opinion_data["match_id"] = match_id
            # Map player_id if present
            if (
                opinion_data.get("player_id")
                and opinion_data["player_id"] in player_id_mapping
            ):
                opinion_data["player_id"] = player_id_mapping[
                    opinion_data["player_id"]
                ]

        if family_opinion_history:
            self.db.bulk_insert_family_opinion_history(family_opinion_history)
            logger.info(
                f"Inserted {len(family_opinion_history)} family opinion history records"
            )

        # Process religion opinion history
        religion_opinion_history = parsed_data.get("religion_opinion_history", [])
        for opinion_data in religion_opinion_history:
            opinion_data["match_id"] = match_id
            # Map player_id if present
            if (
                opinion_data.get("player_id")
                and opinion_data["player_id"] in player_id_mapping
            ):
                opinion_data["player_id"] = player_id_mapping[
                    opinion_data["player_id"]
                ]

        if religion_opinion_history:
            self.db.bulk_insert_religion_opinion_history(religion_opinion_history)
            logger.info(
                f"Inserted {len(religion_opinion_history)} religion opinion history records"
            )

    def process_directory(
        self, directory_path: str, file_pattern: str = "*.zip"
    ) -> Tuple[int, int]:
        """Process all tournament files in a directory.

        Args:
            directory_path: Path to directory containing tournament files
            file_pattern: File pattern to match (default: "*.zip")

        Returns:
            Tuple of (successful_count, total_count)
        """
        directory = Path(directory_path)

        if not directory.exists():
            raise ValueError(f"Directory does not exist: {directory_path}")

        # Find all matching files
        files = list(directory.glob(file_pattern))

        if not files:
            logger.warning(
                f"No files matching pattern '{file_pattern}' found in {directory_path}"
            )
            return 0, 0

        logger.info(f"Found {len(files)} files to process in {directory_path}")

        successful_count = 0

        for file_path in files:
            logger.info(
                f"Processing file {successful_count + 1}/{len(files)}: {file_path.name}"
            )

            if self.process_tournament_file(str(file_path)):
                successful_count += 1
            else:
                logger.error(f"Failed to process: {file_path}")

        logger.info(
            f"Processing complete: {successful_count}/{len(files)} files successful"
        )
        return successful_count, len(files)

    def get_processing_summary(self) -> Dict[str, Any]:
        """Get a summary of processed data.

        Returns:
            Dictionary with processing statistics
        """
        summary = {}

        # Count matches
        result = self.db.fetch_one("SELECT COUNT(*) FROM matches")
        summary["total_matches"] = result[0] if result else 0

        # Count players
        result = self.db.fetch_one("SELECT COUNT(*) FROM players")
        summary["total_players"] = result[0] if result else 0

        # Count unique player names
        result = self.db.fetch_one("SELECT COUNT(DISTINCT player_name) FROM players")
        summary["unique_players"] = result[0] if result else 0

        # Count events
        result = self.db.fetch_one("SELECT COUNT(*) FROM events")
        summary["total_events"] = result[0] if result else 0

        # Count territory records
        result = self.db.fetch_one("SELECT COUNT(*) FROM territories")
        summary["total_territories"] = result[0] if result else 0

        # Count yield history records
        result = self.db.fetch_one("SELECT COUNT(*) FROM player_yield_history")
        summary["total_resources"] = result[0] if result else 0

        # Get date range
        result = self.db.fetch_one(
            "SELECT MIN(save_date), MAX(save_date) FROM matches WHERE save_date IS NOT NULL"
        )
        if result and result[0]:
            summary["date_range"] = {"earliest": result[0], "latest": result[1]}

        # Get most recent processing
        result = self.db.fetch_one("SELECT MAX(processed_date) FROM matches")
        if result and result[0]:
            summary["last_processed"] = result[0]

        return summary

    def cleanup_duplicate_entries(self) -> int:
        """Remove any duplicate entries that might have been created.

        Returns:
            Number of duplicate records removed
        """
        logger.info("Checking for and removing duplicate entries...")

        # Remove duplicate matches (same filename and hash)
        duplicate_query = """
        DELETE FROM matches 
        WHERE match_id NOT IN (
            SELECT MIN(match_id) 
            FROM matches 
            GROUP BY file_name, file_hash
        )
        """

        result = self.db.execute_query(duplicate_query)
        removed_count = result.rowcount if hasattr(result, "rowcount") else 0

        if removed_count > 0:
            logger.info(f"Removed {removed_count} duplicate match records")
        else:
            logger.info("No duplicate entries found")

        return removed_count

    def validate_data_integrity(self) -> Dict[str, Any]:
        """Validate the integrity of loaded data.

        Returns:
            Dictionary with validation results
        """
        logger.info("Validating data integrity...")

        validation_results = {"errors": [], "warnings": [], "statistics": {}}

        # Check for orphaned players
        orphaned_players = self.db.fetch_one(
            """
            SELECT COUNT(*) FROM players p 
            LEFT JOIN matches m ON p.match_id = m.match_id 
            WHERE m.match_id IS NULL
        """
        )

        if orphaned_players and orphaned_players[0] > 0:
            validation_results["errors"].append(
                f"Found {orphaned_players[0]} orphaned player records"
            )

        # Check for matches without players
        empty_matches = self.db.fetch_one(
            """
            SELECT COUNT(*) FROM matches m 
            LEFT JOIN players p ON m.match_id = p.match_id 
            WHERE p.match_id IS NULL
        """
        )

        if empty_matches and empty_matches[0] > 0:
            validation_results["warnings"].append(
                f"Found {empty_matches[0]} matches without players"
            )

        # Check coordinate bounds for territories
        invalid_coordinates = self.db.fetch_one(
            """
            SELECT COUNT(*) FROM territories 
            WHERE x_coordinate < 0 OR x_coordinate > 45 OR y_coordinate < 0 OR y_coordinate > 45
        """
        )

        if invalid_coordinates and invalid_coordinates[0] > 0:
            validation_results["errors"].append(
                f"Found {invalid_coordinates[0]} territories with invalid coordinates"
            )

        # Get statistics
        validation_results["statistics"] = self.get_processing_summary()

        logger.info(
            f"Validation complete: {len(validation_results['errors'])} errors, {len(validation_results['warnings'])} warnings"
        )

        return validation_results


def initialize_database() -> TournamentDatabase:
    """Initialize the database with schema.

    Returns:
        Initialized database instance
    """
    from ..config import Config

    # Create a new database instance with write access for schema creation
    db = TournamentDatabase(db_path=Config.DATABASE_PATH, read_only=False)
    db.create_schema()
    logger.info("Database initialized successfully")
    return db


def process_tournament_directory(
    directory_path: str, challonge_match_mapping: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """Process all tournament files in a directory.

    Args:
        directory_path: Path to directory containing tournament save files
        challonge_match_mapping: Optional mapping of filename to Challonge match ID

    Returns:
        Dictionary with processing results
    """
    # Initialize database if needed
    db = initialize_database()

    # Create ETL instance
    etl = TournamentETL(db)

    # Process all files
    successful_count, total_count = etl.process_directory(directory_path)

    # Cleanup and validate
    duplicates_removed = etl.cleanup_duplicate_entries()
    validation_results = etl.validate_data_integrity()

    # Get final summary
    summary = etl.get_processing_summary()

    return {
        "processing": {
            "successful_files": successful_count,
            "total_files": total_count,
            "success_rate": successful_count / total_count if total_count > 0 else 0,
        },
        "cleanup": {"duplicates_removed": duplicates_removed},
        "validation": validation_results,
        "summary": summary,
    }
