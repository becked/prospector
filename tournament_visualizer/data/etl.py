"""ETL (Extract, Transform, Load) pipeline for tournament data.

This module orchestrates the extraction of data from Old World save files,
transformation into the appropriate format, and loading into the DuckDB database.
"""

import hashlib
import logging
import os
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from chyllonge.api import ChallongeApi
from dotenv import load_dotenv

from .database import TournamentDatabase, get_database
from .parser import OldWorldSaveParser, parse_tournament_file

logger = logging.getLogger(__name__)


def fetch_tournament_rounds(tournament_url: str = "owduels2025") -> Dict[int, int]:
    """Fetch tournament round numbers from Challonge API.

    Args:
        tournament_url: Challonge tournament URL identifier

    Returns:
        Dictionary mapping challonge_match_id to round number.
        Returns empty dict if API call fails.

    Note:
        Round numbers are signed integers:
        - Positive (1, 2, 3, ...) = Winners Bracket
        - Negative (-1, -2, -3, ...) = Losers Bracket
    """
    load_dotenv()

    # Check for API credentials
    if not os.getenv("CHALLONGE_KEY"):
        logger.warning(
            "Challonge API credentials not configured. "
            "tournament_round will be NULL for all matches."
        )
        return {}

    try:
        logger.info(f"Fetching tournament structure from Challonge: {tournament_url}")
        api = ChallongeApi()
        matches = api.matches.get_all(tournament_url)

        # Build cache: challonge_match_id -> round_number
        round_cache = {match["id"]: match["round"] for match in matches}

        logger.info(f"Cached {len(round_cache)} match rounds from Challonge")
        return round_cache

    except Exception as e:
        logger.error(f"Failed to fetch Challonge tournament data: {e}")
        logger.warning("Continuing import without round data (will be NULL)")
        return {}


class TournamentETL:
    """ETL pipeline for processing tournament save files."""

    def __init__(
        self,
        database: Optional[TournamentDatabase] = None,
        round_cache: Optional[Dict[int, int]] = None,
    ) -> None:
        """Initialize ETL pipeline.

        Args:
            database: Database instance to use (defaults to global instance)
            round_cache: Optional cache of challonge_match_id -> round_number
        """
        self.db = database or get_database()
        self.round_cache = round_cache or {}

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

                # Add tournament round from cache
                tournament_round = self.round_cache.get(challonge_match_id)
                if tournament_round is not None:
                    match_metadata["tournament_round"] = tournament_round
                else:
                    logger.warning(
                        f"No round data found for challonge_match_id {challonge_match_id}"
                    )

            # Transform and load data
            self._load_tournament_data(parsed_data, file_path)

            logger.info(f"Successfully processed: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            logger.error(traceback.format_exc())
            return False

    def _load_tournament_data(self, parsed_data: Dict[str, Any], file_path: str) -> None:
        """Load parsed tournament data into the database.

        Winner determination priority:
        1. Manual override (from match_winner_overrides.json)
        2. Parser-determined (from save file TeamVictoriesCompleted)
        3. No winner recorded (None)

        Args:
            parsed_data: Dictionary containing all parsed data
            file_path: Path to the tournament file (for re-parsing territories)
        """
        # Start with match data (without winner_player_id for now)
        match_metadata = parsed_data["match_metadata"].copy()
        original_winner_id = match_metadata.pop("winner_player_id", None)
        challonge_match_id = match_metadata.get("challonge_match_id")
        match_id = self.db.insert_match(match_metadata)

        logger.info(f"Inserted match with ID: {match_id}")

        # Check for manual override BEFORE processing players
        from .winner_overrides import get_overrides

        overrides = get_overrides()
        override_winner_name = overrides.get_override_winner(challonge_match_id)

        # Process players
        players_data = parsed_data["players"]
        player_id_mapping = {}  # Map original index to database ID
        player_name_to_db_id = {}  # Map player name to database ID
        winner_db_id = None
        winner_method = "parser_determined"

        for i, player_data in enumerate(players_data):
            player_data["match_id"] = match_id
            player_id = self.db.insert_player(player_data)
            original_player_id = i + 1  # Assuming 1-based indexing
            player_id_mapping[original_player_id] = player_id

            # Track player names for override lookup
            player_name = player_data["player_name"]
            player_name_to_db_id[player_name] = player_id

            # Check if this is the winner (override takes precedence)
            if override_winner_name:
                if player_name == override_winner_name:
                    winner_db_id = player_id
                    winner_method = "manual_override"
            elif original_winner_id and original_player_id == original_winner_id:
                winner_db_id = player_id

        logger.info(f"Inserted {len(players_data)} players")

        # Process rulers (after players, before events due to foreign key dependency)
        rulers = parsed_data.get("rulers", [])
        # Map player_ids from XML-based to database IDs
        for ruler_data in rulers:
            if (
                ruler_data.get("player_id")
                and ruler_data["player_id"] in player_id_mapping
            ):
                ruler_data["player_id"] = player_id_mapping[ruler_data["player_id"]]

        if rulers:
            self.db.bulk_insert_rulers(match_id, rulers)
            logger.info(f"Inserted {len(rulers)} rulers")

        # Validate override was applied if requested
        if override_winner_name and not winner_db_id:
            logger.error(
                f"Override winner '{override_winner_name}' not found in player list "
                f"for match {challonge_match_id}. Available players: {list(player_name_to_db_id.keys())}"
            )
            # Fall back to parser-determined winner
            for i, player_data in enumerate(players_data):
                original_player_id = i + 1
                if original_winner_id and original_player_id == original_winner_id:
                    winner_db_id = player_id_mapping[original_player_id]
                    winner_method = "parser_determined"
                    logger.warning(
                        f"Falling back to parser-determined winner for match {challonge_match_id}"
                    )
                    break

        # Insert winner information into separate table
        if winner_db_id:
            self.db.insert_match_winner(match_id, winner_db_id, winner_method)
            logger.info(
                f"Recorded winner: player_id {winner_db_id} (method: {winner_method})"
            )

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

        # Process territories (requires match_id and final_turn)
        # Extract territories from save file now that we have match_id
        # Get final turn from match metadata
        final_turn = parsed_data["match_metadata"].get("total_turns", 0)

        # Only extract territories if we have turn data
        if final_turn > 0:
            parser = OldWorldSaveParser(file_path)
            parser.extract_and_parse()
            territories = parser.extract_territories(
                match_id=match_id, final_turn=final_turn
            )

            # Note: owner_player_id is already in database format (1-based) from parser
            # No need to remap player IDs as parser handles the conversion

            if territories:
                self.db.bulk_insert_territories(territories)
                logger.info(f"Inserted {len(territories)} territory records")
        else:
            logger.warning(
                f"No game states found for match {match_id}, skipping territory extraction"
            )

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
            logger.info(
                f"Inserted {len(legitimacy_history)} legitimacy history records"
            )

        # Process family opinion history
        family_opinion_history = parsed_data.get("family_opinion_history", [])
        for opinion_data in family_opinion_history:
            opinion_data["match_id"] = match_id
            # Map player_id if present
            if (
                opinion_data.get("player_id")
                and opinion_data["player_id"] in player_id_mapping
            ):
                opinion_data["player_id"] = player_id_mapping[opinion_data["player_id"]]

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
                opinion_data["player_id"] = player_id_mapping[opinion_data["player_id"]]

        if religion_opinion_history:
            self.db.bulk_insert_religion_opinion_history(religion_opinion_history)
            logger.info(
                f"Inserted {len(religion_opinion_history)} religion opinion history records"
            )

        # Process city data
        cities = parsed_data.get("cities", [])
        # Map player_ids from XML-based to database IDs (same as events/rulers)
        for city_data in cities:
            city_data["match_id"] = match_id
            # Remap current owner player_id
            if (
                city_data.get("player_id")
                and city_data["player_id"] in player_id_mapping
            ):
                city_data["player_id"] = player_id_mapping[city_data["player_id"]]
            # Remap first_player_id (original founder) for conquest tracking
            if (
                city_data.get("first_player_id")
                and city_data["first_player_id"] in player_id_mapping
            ):
                city_data["first_player_id"] = player_id_mapping[
                    city_data["first_player_id"]
                ]

        if cities:
            self.db.insert_cities(match_id, cities)
            logger.info(f"Inserted {len(cities)} cities")

        # Process city unit production
        city_unit_production = parsed_data.get("city_unit_production", [])
        # Production data doesn't need player_id mapping - just match_id
        for prod_data in city_unit_production:
            prod_data["match_id"] = match_id

        if city_unit_production:
            self.db.insert_city_unit_production(match_id, city_unit_production)
            logger.info(
                f"Inserted {len(city_unit_production)} city unit production records"
            )

        # Process city projects
        city_projects = parsed_data.get("city_projects", [])
        # Project data doesn't need player_id mapping - just match_id
        for proj_data in city_projects:
            proj_data["match_id"] = match_id

        if city_projects:
            self.db.insert_city_projects(match_id, city_projects)
            logger.info(f"Inserted {len(city_projects)} city project records")

    def extract_lightweight_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract minimal metadata from a file for deduplication.

        Args:
            file_path: Path to the tournament save zip file

        Returns:
            Dictionary with game_name, total_turns, save_date, file_size, has_victory_data, and is_autosave
            Returns None if parsing fails
        """
        try:
            parser = OldWorldSaveParser(file_path)
            parser.extract_and_parse()

            # Get basic metadata
            metadata = parser.extract_basic_metadata()

            # Check if file has victory completion data
            has_victory_data = False
            if parser.root is not None:
                team_victories = parser.root.find(".//TeamVictoriesCompleted")
                has_victory_data = team_victories is not None

            # Check if this is an autosave
            filename = Path(file_path).name
            is_autosave = "Auto" in filename or "auto" in filename

            # Get file size
            file_size = os.path.getsize(file_path)

            return {
                "file_path": file_path,
                "game_name": metadata.get("game_name"),
                "total_turns": metadata.get("total_turns"),
                "save_date": metadata.get("save_date"),
                "file_size": file_size,
                "has_victory_data": has_victory_data,
                "is_autosave": is_autosave,
            }

        except Exception as e:
            logger.warning(f"Could not extract metadata from {file_path}: {e}")
            return None

    def select_best_duplicate(
        self, duplicate_files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Select the best file from a list of duplicates.

        Priority (highest to lowest):
        1. Has TeamVictoriesCompleted data (most reliable winner determination)
        2. Not an autosave (manual saves are usually final state)
        3. Larger file size (likely more complete data)

        Args:
            duplicate_files: List of file metadata dictionaries

        Returns:
            The best file metadata dictionary
        """
        if len(duplicate_files) == 1:
            return duplicate_files[0]

        # Sort by priority
        def priority_key(f: Dict[str, Any]) -> Tuple[bool, bool, int]:
            return (
                f["has_victory_data"],  # True sorts after False, so we negate
                not f["is_autosave"],  # Prefer non-autosaves
                f["file_size"],  # Larger files preferred
            )

        sorted_files = sorted(duplicate_files, key=priority_key, reverse=True)
        return sorted_files[0]

    def find_duplicates(
        self, files: List[Path], deduplicate: bool = True
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Find and filter duplicate files.

        Args:
            files: List of file paths to check
            deduplicate: If True, filter out duplicates keeping only the best

        Returns:
            Tuple of (files_to_process, skipped_files_info)
            - files_to_process: List of file paths to process
            - skipped_files_info: List of dicts with info about skipped files
        """
        if not deduplicate:
            return [str(f) for f in files], []

        logger.info("Scanning files for duplicates...")

        # Extract metadata for all files
        file_metadata = []
        for file_path in files:
            metadata = self.extract_lightweight_metadata(str(file_path))
            if metadata:
                file_metadata.append(metadata)

        # Group files by (game_name, total_turns, save_date)
        from collections import defaultdict

        groups = defaultdict(list)
        for metadata in file_metadata:
            # Create key from game identifiers
            key = (
                metadata["game_name"],
                metadata["total_turns"],
                metadata["save_date"],
            )
            groups[key].append(metadata)

        # Select best file from each group
        files_to_process = []
        skipped_files = []

        for group_key, group_files in groups.items():
            if len(group_files) > 1:
                # Found duplicates
                best_file = self.select_best_duplicate(group_files)
                files_to_process.append(best_file["file_path"])

                # Log skipped files
                for file_metadata in group_files:
                    if file_metadata["file_path"] != best_file["file_path"]:
                        reason_parts = []
                        if not file_metadata["has_victory_data"]:
                            reason_parts.append("missing victory data")
                        if file_metadata["is_autosave"]:
                            reason_parts.append("autosave")
                        if file_metadata["file_size"] < best_file["file_size"]:
                            reason_parts.append(
                                f"smaller ({file_metadata['file_size']} < {best_file['file_size']} bytes)"
                            )

                        reason = (
                            ", ".join(reason_parts)
                            if reason_parts
                            else "lower priority"
                        )

                        skipped_files.append(
                            {
                                "file_path": file_metadata["file_path"],
                                "game_name": group_key[0],
                                "reason": reason,
                                "duplicate_of": best_file["file_path"],
                            }
                        )

                        logger.info(
                            f"Skipping duplicate: {Path(file_metadata['file_path']).name} "
                            f"(reason: {reason})"
                        )
            else:
                # No duplicates, process the only file
                files_to_process.append(group_files[0]["file_path"])

        logger.info(
            f"Deduplication complete: {len(files_to_process)} files to process, "
            f"{len(skipped_files)} duplicates skipped"
        )

        return files_to_process, skipped_files

    def extract_challonge_match_id(self, file_path: str) -> Optional[int]:
        """Extract Challonge match ID from filename.

        Filenames follow the pattern: match_{challonge_match_id}_*.zip
        Example: match_426504724_moose-mongreleyes.zip -> 426504724

        Args:
            file_path: Path to the file

        Returns:
            Challonge match ID if found, None otherwise
        """
        import re

        filename = Path(file_path).name
        # Match pattern: match_{digits}_
        match = re.match(r"match_(\d+)_", filename)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                logger.warning(f"Could not parse match ID from filename: {filename}")
                return None
        return None

    def process_directory(
        self, directory_path: str, file_pattern: str = "*.zip", deduplicate: bool = True
    ) -> Tuple[int, int, List[Dict[str, Any]]]:
        """Process all tournament files in a directory.

        Args:
            directory_path: Path to directory containing tournament files
            file_pattern: File pattern to match (default: "*.zip")
            deduplicate: If True, automatically skip duplicate files (default: True)

        Returns:
            Tuple of (successful_count, total_count, skipped_duplicates)
        """
        directory = Path(directory_path)

        if not directory.exists():
            raise ValueError(f"Directory does not exist: {directory_path}")

        # Find all matching files
        all_files = list(directory.glob(file_pattern))

        if not all_files:
            logger.warning(
                f"No files matching pattern '{file_pattern}' found in {directory_path}"
            )
            return 0, 0, []

        logger.info(f"Found {len(all_files)} files in {directory_path}")

        # Deduplicate files if requested
        files_to_process, skipped_duplicates = self.find_duplicates(
            all_files, deduplicate=deduplicate
        )

        successful_count = 0
        total_files = len(files_to_process)

        for i, file_path in enumerate(files_to_process):
            logger.info(
                f"Processing file {i + 1}/{total_files}: {Path(file_path).name}"
            )

            # Extract challonge_match_id from filename
            challonge_match_id = self.extract_challonge_match_id(file_path)
            if challonge_match_id:
                logger.info(f"Extracted Challonge match ID: {challonge_match_id}")

            if self.process_tournament_file(file_path, challonge_match_id):
                successful_count += 1
            else:
                logger.error(f"Failed to process: {file_path}")

        logger.info(
            f"Processing complete: {successful_count}/{total_files} files successful"
        )
        return successful_count, total_files, skipped_duplicates

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

        # Count rulers
        result = self.db.fetch_one("SELECT COUNT(*) FROM rulers")
        summary["total_rulers"] = result[0] if result else 0

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
    directory_path: str,
    challonge_match_mapping: Optional[Dict[str, int]] = None,
    deduplicate: bool = True,
) -> Dict[str, Any]:
    """Process all tournament files in a directory.

    Args:
        directory_path: Path to directory containing tournament save files
        challonge_match_mapping: Optional mapping of filename to Challonge match ID
        deduplicate: If True, automatically skip duplicate files (default: True)

    Returns:
        Dictionary with processing results
    """
    # Initialize database if needed
    db = initialize_database()

    # Fetch tournament round data once at start
    logger.info("Fetching tournament structure from Challonge API...")
    round_cache = fetch_tournament_rounds()

    # Create ETL instance
    etl = TournamentETL(db, round_cache=round_cache)

    # Process all files
    successful_count, total_count, skipped_duplicates = etl.process_directory(
        directory_path, deduplicate=deduplicate
    )

    # Cleanup and validate
    duplicates_removed = etl.cleanup_duplicate_entries()
    validation_results = etl.validate_data_integrity()

    # Link players to participants (if participants exist)
    participant_linking_stats = None
    try:
        from .participant_matcher import ParticipantMatcher

        # Check if there are participants in the database
        participant_count = db.fetch_one(
            "SELECT COUNT(*) FROM tournament_participants"
        )[0]

        if participant_count > 0:
            logger.info("Linking players to tournament participants...")
            matcher = ParticipantMatcher(db)
            participant_linking_stats = matcher.link_all_matches()

            logger.info(
                f"Linked {participant_linking_stats['matched_players']}/{participant_linking_stats['total_players']} "
                f"players to participants"
            )

            # Warn if there are unmatched players
            if participant_linking_stats["unmatched_players"] > 0:
                logger.warning(
                    f"{participant_linking_stats['unmatched_players']} players could not be matched to participants. "
                    "Run scripts/link_players_to_participants.py for details."
                )
        else:
            logger.info(
                "No participants in database, skipping player-participant linking"
            )

    except Exception as e:
        logger.warning(f"Error linking players to participants: {e}")
        logger.warning(
            "Player-participant linking skipped. You can run scripts/link_players_to_participants.py manually."
        )

    # Get final summary
    summary = etl.get_processing_summary()

    return {
        "processing": {
            "successful_files": successful_count,
            "total_files": total_count,
            "success_rate": successful_count / total_count if total_count > 0 else 0,
            "skipped_duplicates": len(skipped_duplicates),
            "skipped_files": skipped_duplicates,
        },
        "cleanup": {"duplicates_removed": duplicates_removed},
        "validation": validation_results,
        "participant_linking": participant_linking_stats,
        "summary": summary,
    }
