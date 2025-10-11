#!/usr/bin/env python3
"""Manual import script for tournament save files.

This script processes Old World tournament save files from the saves/ directory
and imports them into the DuckDB database for visualization.

Usage:
    python import_tournaments.py [--directory DIRECTORY] [--verbose] [--force]
"""

import argparse
import logging
import sys
from pathlib import Path

# Add the tournament_visualizer package to the path
sys.path.insert(0, str(Path(__file__).parent))

from tournament_visualizer.data.etl import (
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

    # Cleanup results
    cleanup = results["cleanup"]
    if cleanup["duplicates_removed"] > 0:
        print(f"Duplicate records removed: {cleanup['duplicates_removed']}")

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
    print(f"  Events: {summary['total_events']}")
    print(f"  Territories: {summary['total_territories']}")
    print(f"  Resources: {summary['total_resources']}")

    if "date_range" in summary:
        date_range = summary["date_range"]
        print(f"  Date range: {date_range['earliest']} to {date_range['latest']}")

    print("=" * 60)


def main() -> None:
    """Main import function."""
    parser = argparse.ArgumentParser(
        description="Import Old World tournament save files into database"
    )

    parser.add_argument(
        "--directory",
        "-d",
        default="saves",
        help="Directory containing tournament save files (default: saves)",
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

    args = parser.parse_args()

    # Set up logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    try:
        # Validate directory
        directory = validate_directory(args.directory)

        # Handle force option
        if args.force:
            db_path = Path("data/tournament_data.duckdb")
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

        # Process all files
        results = process_tournament_directory(str(directory))

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
        print(f"\n❌ Import failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
