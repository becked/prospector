#!/usr/bin/env python3
"""Manual import script for tournament save files.

This script processes Old World tournament save files from the saves/ directory
and imports them into the DuckDB database for visualization.

Usage:
    python import_tournaments.py [--directory DIRECTORY] [--verbose] [--force]
    python import_tournaments.py --match-id 426504724  # Reimport single match
"""

import argparse
import glob
import logging
import os
import re
import sys
from pathlib import Path

# Add the tournament_visualizer package to the path
sys.path.insert(0, str(Path(__file__).parent))

from tournament_visualizer.config import Config
from tournament_visualizer.data.etl import (
    TournamentETL,
    fetch_tournament_rounds,
    initialize_database,
    process_tournament_directory,
)


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration.

    Args:
        verbose: Enable verbose logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Ensure logs directory exists
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=level,
        format=format_string,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "tournament_import.log"),
        ],
    )


def validate_directory(directory_path: str) -> Path:
    """Validate that the directory exists and contains tournament files.

    Args:
        directory_path: Path to the directory

    Returns:
        Validated Path object

    Raises:
        ValueError: If directory is invalid
    """
    directory = Path(directory_path)

    if not directory.exists():
        raise ValueError(f"Directory does not exist: {directory_path}")

    if not directory.is_dir():
        raise ValueError(f"Path is not a directory: {directory_path}")

    # Check for tournament files
    zip_files = list(directory.glob("*.zip"))
    if not zip_files:
        raise ValueError(f"No .zip files found in directory: {directory_path}")

    print(f"Found {len(zip_files)} tournament files in {directory}")
    return directory


def print_summary(results: dict) -> None:
    """Print a summary of the import results.

    Args:
        results: Results dictionary from process_tournament_directory
    """
    print("\n" + "=" * 60)
    print("IMPORT SUMMARY")
    print("=" * 60)

    # Processing results
    processing = results["processing"]
    print(
        f"Files processed: {processing['successful_files']}/{processing['total_files']}"
    )
    print(f"Success rate: {processing['success_rate']:.1%}")

    # Deduplication results
    if processing.get("skipped_duplicates", 0) > 0:
        print(f"\nDuplicate files skipped: {processing['skipped_duplicates']}")
        if processing.get("skipped_files"):
            print("  Skipped files:")
            for skipped in processing["skipped_files"]:
                filename = Path(skipped["file_path"]).name
                print(f"    - {filename}")
                print(f"      Reason: {skipped['reason']}")

    # Cleanup results
    cleanup = results["cleanup"]
    if cleanup["duplicates_removed"] > 0:
        print(f"\nDuplicate records removed: {cleanup['duplicates_removed']}")

    # Validation results
    validation = results["validation"]
    if validation["errors"]:
        print(f"\nErrors found: {len(validation['errors'])}")
        for error in validation["errors"]:
            print(f"  - {error}")

    if validation["warnings"]:
        print(f"\nWarnings: {len(validation['warnings'])}")
        for warning in validation["warnings"]:
            print(f"  - {warning}")

    # Database summary
    summary = results["summary"]
    print("\nDatabase contents:")
    print(f"  Matches: {summary['total_matches']}")
    print(f"  Players: {summary['total_players']} ({summary['unique_players']} unique)")
    print(f"  Rulers: {summary['total_rulers']}")
    print(f"  Events: {summary['total_events']}")
    print(f"  Territories: {summary['total_territories']}")
    print(f"  Resources: {summary['total_resources']}")

    if "date_range" in summary:
        date_range = summary["date_range"]
        print(f"  Date range: {date_range['earliest']} to {date_range['latest']}")

    print("=" * 60)


def find_match_file(challonge_match_id: int, directory: str) -> Path | None:
    """Find the save file for a given Challonge match ID.

    Filenames follow the pattern: match_{challonge_match_id}_*.zip
    Example: match_426504724_moose-mongreleyes.zip

    Args:
        challonge_match_id: The Challonge match ID to find
        directory: Directory to search in

    Returns:
        Path to the file, or None if not found
    """
    pattern = f"match_{challonge_match_id}_*.zip"
    matches = list(Path(directory).glob(pattern))

    if not matches:
        return None
    if len(matches) > 1:
        print(f"Warning: Found multiple files for match {challonge_match_id}:")
        for m in matches:
            print(f"  - {m.name}")
        print(f"Using: {matches[0].name}")

    return matches[0]


def reimport_single_match(
    challonge_match_id: int, directory: str, verbose: bool = False
) -> None:
    """Reimport a single match by its Challonge match ID.

    This deletes all existing data for the match and reimports it from
    the save file.

    Args:
        challonge_match_id: The Challonge match ID to reimport
        directory: Directory containing save files
        verbose: Enable verbose logging
    """
    setup_logging(verbose)
    logger = logging.getLogger(__name__)

    print(f"\n{'='*60}")
    print(f"SINGLE MATCH REIMPORT: {challonge_match_id}")
    print(f"{'='*60}")

    # Find the save file
    save_file = find_match_file(challonge_match_id, directory)
    if not save_file:
        print(f"\n❌ No save file found for match {challonge_match_id}")
        print(f"   Expected pattern: match_{challonge_match_id}_*.zip")
        print(f"   Searched in: {directory}")
        sys.exit(1)

    print(f"\nFound save file: {save_file.name}")

    # Initialize database
    print("Initializing database...")
    db = initialize_database()

    # Check if match exists in database
    existing_match_id = db.get_match_id_by_challonge_id(challonge_match_id)

    if existing_match_id:
        print(f"Found existing match in database (match_id: {existing_match_id})")
        print("Deleting existing data...")

        if db.delete_match(existing_match_id):
            print(f"✓ Deleted match {existing_match_id} and all associated data")
        else:
            print(f"⚠ Match {existing_match_id} not found (may have been deleted)")
    else:
        print("No existing match found in database (new import)")

    # Fetch Challonge round data
    print("\nFetching tournament round data from Challonge...")
    round_cache = fetch_tournament_rounds()
    if round_cache:
        round_num = round_cache.get(challonge_match_id)
        if round_num:
            bracket = "Winners" if round_num > 0 else "Losers"
            print(f"✓ Match is in {bracket} Bracket, Round {abs(round_num)}")
        else:
            print("⚠ Round data not found for this match")
    else:
        print("⚠ Could not fetch round data (API unavailable)")

    # Process the file
    print(f"\nImporting: {save_file.name}")
    print("-" * 60)

    etl = TournamentETL(database=db, round_cache=round_cache)
    success = etl.process_tournament_file(str(save_file), challonge_match_id)

    if success:
        # Get the new match_id
        new_match_id = db.get_match_id_by_challonge_id(challonge_match_id)
        print(f"\n{'='*60}")
        print(f"✅ Successfully reimported match!")
        print(f"   Challonge ID: {challonge_match_id}")
        print(f"   Database ID:  {new_match_id}")
        print(f"{'='*60}")
    else:
        print(f"\n❌ Failed to import match {challonge_match_id}")
        print("Check the log file 'tournament_import.log' for details.")
        sys.exit(1)

    db.close()


def main() -> None:
    """Main import function."""
    parser = argparse.ArgumentParser(
        description="Import Old World tournament save files into database"
    )

    parser.add_argument(
        "--directory",
        "-d",
        default=os.getenv("SAVES_DIRECTORY", "saves"),
        help="Directory containing tournament save files (default: $SAVES_DIRECTORY or 'saves')",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force reimport of all files (removes database first)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be imported without actually importing",
    )

    parser.add_argument(
        "--keep-duplicates",
        action="store_true",
        help="Keep duplicate files instead of automatically skipping them",
    )

    parser.add_argument(
        "--match-id",
        "-m",
        type=int,
        help="Reimport a single match by its Challonge match ID (e.g., 426504724)",
    )

    args = parser.parse_args()

    # Set up logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    try:
        # Handle single-match reimport
        if args.match_id:
            reimport_single_match(args.match_id, args.directory, args.verbose)
            return

        # Validate directory
        directory = validate_directory(args.directory)

        # Handle force option
        if args.force:
            db_path = Path(Config.DATABASE_PATH)
            if db_path.exists():
                print(f"Removing existing database: {db_path}")
                db_path.unlink()

        # Handle dry run
        if args.dry_run:
            zip_files = list(directory.glob("*.zip"))
            print(f"\nDry run mode - would process {len(zip_files)} files:")
            for zip_file in zip_files:
                print(f"  - {zip_file.name}")
            print("\nUse without --dry-run to actually import the files.")
            return

        # Initialize database
        print("Initializing database...")
        db = initialize_database()

        # Check for existing data
        existing_files = db.get_processed_files()
        if existing_files and not args.force:
            print(
                f"Found {len(existing_files)} previously processed files in database."
            )
            print("Only new files will be imported.")
            print("Use --force to reimport all files.")

        print(f"\nStarting import from directory: {directory}")
        print("-" * 60)

        # Show deduplication status
        if not args.keep_duplicates:
            print("Deduplication: ENABLED (use --keep-duplicates to disable)")
        else:
            print("Deduplication: DISABLED (all files will be processed)")

        # Process all files
        results = process_tournament_directory(
            str(directory), deduplicate=not args.keep_duplicates
        )

        # Print summary
        print_summary(results)

        # Success
        if results["processing"]["success_rate"] == 1.0:
            print("\n✅ All files imported successfully!")
        else:
            print(
                f"\n⚠️  Import completed with {results['processing']['total_files'] - results['processing']['successful_files']} failures"
            )
            print("Check the log file 'tournament_import.log' for details.")

        # Close database connection
        db.close()

    except Exception as e:
        logger.error(f"Import failed: {e}")
        print(f"\n❌ Import failed: {e}", file=sys.stderr)

        # Import traceback for detailed error output
        import traceback
        traceback.print_exc()

        sys.exit(1)


if __name__ == "__main__":
    main()
