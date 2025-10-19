#!/usr/bin/env python3
"""Generate AI-powered narrative summaries for tournament matches.

This script generates narrative summaries using Claude API and stores them
in the matches.narrative_summary column.

Usage:
    # Generate for matches without narratives
    uv run python scripts/generate_match_narratives.py

    # Force regenerate all narratives
    uv run python scripts/generate_match_narratives.py --force

    # Generate for specific match
    uv run python scripts/generate_match_narratives.py --match-id 19

    # Verbose logging
    uv run python scripts/generate_match_narratives.py --verbose
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import duckdb

from tournament_visualizer.config import Config
from tournament_visualizer.data.event_formatter import EventFormatter
from tournament_visualizer.data.narrative_generator import NarrativeGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_matches_to_process(
    conn: duckdb.DuckDBPyConnection,
    force: bool = False,
    match_id: int | None = None,
) -> list[int]:
    """Get list of match IDs to process.

    Args:
        conn: Database connection
        force: If True, process all matches regardless of existing narratives
        match_id: If provided, only process this specific match

    Returns:
        List of match IDs to process
    """
    if match_id:
        # Verify match exists
        result = conn.execute(
            "SELECT match_id FROM matches WHERE match_id = ?", [match_id]
        ).fetchone()
        if not result:
            logger.error(f"Match {match_id} not found")
            return []
        return [match_id]

    if force:
        # All matches
        query = "SELECT match_id FROM matches ORDER BY match_id"
    else:
        # Only matches without narratives
        query = """
            SELECT match_id
            FROM matches
            WHERE narrative_summary IS NULL
            ORDER BY match_id
        """

    results = conn.execute(query).fetchall()
    return [row[0] for row in results]


def get_match_metadata(
    conn: duckdb.DuckDBPyConnection, match_id: int
) -> dict[str, Any] | None:
    """Get metadata for a match.

    Args:
        conn: Database connection
        match_id: Match ID to fetch

    Returns:
        Match metadata dict or None if not found
    """
    query = """
        SELECT
            m.match_id,
            p1.player_name as player1_name,
            p1.civilization as player1_civ,
            p2.player_name as player2_name,
            p2.civilization as player2_civ,
            pw.player_name as winner_name,
            m.total_turns
        FROM matches m
        LEFT JOIN players p1 ON m.match_id = p1.match_id
            AND m.player1_participant_id = p1.participant_id
        LEFT JOIN players p2 ON m.match_id = p2.match_id
            AND m.player2_participant_id = p2.participant_id
        LEFT JOIN players pw ON m.match_id = pw.match_id
            AND m.winner_participant_id = pw.participant_id
        WHERE m.match_id = ?
    """

    result = conn.execute(query, [match_id]).fetchone()
    if not result:
        return None

    return {
        "match_id": result[0],
        "player1_name": result[1],
        "player1_civ": result[2],
        "player2_name": result[3],
        "player2_civ": result[4],
        "winner_name": result[5],
        "total_turns": result[6],
    }


def get_match_events(
    conn: duckdb.DuckDBPyConnection, match_id: int
) -> list[dict[str, Any]]:
    """Get all events for a match.

    Args:
        conn: Database connection
        match_id: Match ID to fetch events for

    Returns:
        List of event dicts
    """
    query = """
        SELECT
            e.turn_number,
            e.event_type,
            p.player_name,
            p.civilization,
            e.description,
            e.event_data
        FROM events e
        JOIN players p ON e.player_id = p.player_id
        WHERE e.match_id = ?
        ORDER BY e.turn_number, e.event_id
    """

    results = conn.execute(query, [match_id]).fetchall()

    return [
        {
            "turn_number": row[0],
            "event_type": row[1],
            "player_name": row[2],
            "civilization": row[3],
            "description": row[4],
            "event_data": row[5],
        }
        for row in results
    ]


def save_narrative(
    conn: duckdb.DuckDBPyConnection, match_id: int, narrative: str
) -> None:
    """Save narrative to database.

    Args:
        conn: Database connection
        match_id: Match ID to update
        narrative: Narrative text to save
    """
    conn.execute(
        "UPDATE matches SET narrative_summary = ? WHERE match_id = ?",
        [narrative, match_id],
    )
    conn.commit()


def process_match(
    conn: duckdb.DuckDBPyConnection,
    match_id: int,
    generator: NarrativeGenerator,
    formatter: EventFormatter,
) -> bool:
    """Process a single match to generate narrative.

    Args:
        conn: Database connection
        match_id: Match ID to process
        generator: Narrative generator instance
        formatter: Event formatter instance

    Returns:
        True if successful, False if error occurred
    """
    try:
        logger.info(f"Processing match {match_id}")

        # Get match metadata
        metadata = get_match_metadata(conn, match_id)
        if not metadata:
            logger.error(f"Match {match_id} metadata not found")
            return False

        # Get events
        events = get_match_events(conn, match_id)
        if not events:
            logger.warning(f"Match {match_id} has no events, skipping")
            return False

        logger.info(
            f"Match {match_id}: {metadata['player1_name']} ({metadata['player1_civ']}) "
            f"vs {metadata['player2_name']} ({metadata['player2_civ']}) - "
            f"{len(events)} events"
        )

        # Format events
        formatted_events = formatter.format_events(events)

        # Generate narrative
        narrative = generator.generate_narrative(
            formatted_events=formatted_events,
            match_metadata=metadata,
        )

        # Save to database
        save_narrative(conn, match_id, narrative)

        logger.info(f"Match {match_id}: Generated narrative ({len(narrative)} chars)")
        return True

    except Exception as e:
        logger.error(f"Match {match_id}: Error - {e}", exc_info=True)
        return False


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        description="Generate narrative summaries for tournament matches"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate narratives for all matches (overwrite existing)",
    )
    parser.add_argument(
        "--match-id",
        type=int,
        help="Generate narrative for specific match ID only",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Check API key
    if not Config.ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY not found in environment")
        logger.error("Set it in .env file or environment variables")
        return 1

    # Initialize generator and formatter
    generator = NarrativeGenerator(api_key=Config.ANTHROPIC_API_KEY)
    formatter = EventFormatter()

    # Connect to database
    logger.info(f"Connecting to database: {Config.DATABASE_PATH}")
    conn = duckdb.connect(Config.DATABASE_PATH)

    try:
        # Get matches to process
        match_ids = get_matches_to_process(
            conn, force=args.force, match_id=args.match_id
        )

        if not match_ids:
            if args.force or args.match_id:
                logger.error("No matches found to process")
                return 1
            else:
                logger.info("No matches need narratives (all up to date)")
                return 0

        logger.info(f"Processing {len(match_ids)} matches")

        # Process each match
        success_count = 0
        error_count = 0

        for match_id in match_ids:
            if process_match(conn, match_id, generator, formatter):
                success_count += 1
            else:
                error_count += 1

        # Summary
        logger.info("=" * 60)
        logger.info(f"Processed {len(match_ids)} matches")
        logger.info(f"  Success: {success_count}")
        logger.info(f"  Errors:  {error_count}")

        return 0 if error_count == 0 else 1

    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
