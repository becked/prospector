#!/usr/bin/env python3
"""Generate AI-powered narrative summaries for tournament matches.

Uses the match card analysis engine to produce structured data, then
generates three narratives per match via parallel LLM calls:
1. Match summary (stored in matches.narrative_summary)
2. Player 1 narrative (stored in matches.p1_narrative)
3. Player 2 narrative (stored in matches.p2_narrative)

Usage:
    # Generate for matches missing any narrative
    uv run python scripts/generate_match_narratives.py

    # Force regenerate all narratives
    uv run python scripts/generate_match_narratives.py --force

    # Generate for specific match
    uv run python scripts/generate_match_narratives.py --match-id 19

    # Dry run - print serialized analysis without calling LLM
    uv run python scripts/generate_match_narratives.py --match-id 19 --dry-run

    # Verbose logging
    uv run python scripts/generate_match_narratives.py --verbose
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import anthropic
import duckdb

from tournament_visualizer.components.match_card import analyze_match, fetch_match_card_data
from tournament_visualizer.config import Config
from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.narrative_generator import (
    build_match_summary_prompt,
    build_player_narrative_prompt,
    serialize_analysis,
)
from tournament_visualizer.data.queries import TournamentQueries

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-opus-4-20250514"


def get_matches_to_process(
    conn: duckdb.DuckDBPyConnection,
    force: bool = False,
    match_id: int | None = None,
) -> list[int]:
    """Get list of match IDs that need narrative generation.

    Args:
        conn: Database connection
        force: If True, process all matches regardless of existing narratives
        match_id: If provided, only process this specific match

    Returns:
        List of match IDs to process
    """
    if match_id:
        result = conn.execute(
            "SELECT match_id FROM matches WHERE match_id = ?", [match_id]
        ).fetchone()
        if not result:
            logger.error(f"Match {match_id} not found")
            return []
        return [match_id]

    if force:
        query = "SELECT match_id FROM matches ORDER BY match_id"
    else:
        # Process matches missing any of the three narratives
        query = """
            SELECT match_id
            FROM matches
            WHERE narrative_summary IS NULL
               OR p1_narrative IS NULL
               OR p2_narrative IS NULL
            ORDER BY match_id
        """

    results = conn.execute(query).fetchall()
    return [row[0] for row in results]


def save_narratives(
    conn: duckdb.DuckDBPyConnection,
    match_id: int,
    match_summary: str,
    p1_narrative: str,
    p2_narrative: str,
) -> None:
    """Save all three narratives to database.

    Args:
        conn: Database connection
        match_id: Match ID to update
        match_summary: Overall match narrative
        p1_narrative: Player 1 empire narrative
        p2_narrative: Player 2 empire narrative
    """
    conn.execute(
        """UPDATE matches
        SET narrative_summary = ?,
            p1_narrative = ?,
            p2_narrative = ?
        WHERE match_id = ?""",
        [match_summary, p1_narrative, p2_narrative, match_id],
    )
    conn.commit()


async def async_generate(
    client: anthropic.AsyncAnthropic,
    model: str,
    prompt: str,
) -> str:
    """Make a single async LLM API call.

    Args:
        client: AsyncAnthropic client
        model: Model name
        prompt: User prompt

    Returns:
        Generated text response
    """
    response = await client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


async def process_match(
    match_id: int,
    queries: TournamentQueries,
    write_conn: duckdb.DuckDBPyConnection | None,
    client: anthropic.AsyncAnthropic | None,
    dry_run: bool = False,
    preview: bool = False,
) -> bool:
    """Process a single match to generate narratives.

    The 3 LLM calls per match run concurrently via asyncio.gather().

    Args:
        match_id: Match ID to process
        queries: TournamentQueries instance for data fetching
        write_conn: Writable database connection for saving results
        client: AsyncAnthropic client (None if dry_run)
        dry_run: If True, print analysis without calling LLM
        preview: If True, generate and print narratives without saving

    Returns:
        True if successful, False if error occurred
    """
    try:
        logger.info(f"Processing match {match_id}")

        # Fetch data and run analysis
        data = fetch_match_card_data(match_id, queries)
        if data is None:
            logger.error(f"Match {match_id}: no data found")
            return False

        analysis = analyze_match(**data)

        p1_name = analysis.get("player_names", ("?", "?"))[0]
        p2_name = analysis.get("player_names", ("?", "?"))[1]
        p1_civ = analysis.get("civilizations", ("?", "?"))[0]
        p2_civ = analysis.get("civilizations", ("?", "?"))[1]
        logger.info(
            f"Match {match_id}: {p1_name} ({p1_civ}) vs {p2_name} ({p2_civ})"
        )

        if dry_run:
            serialized = serialize_analysis(analysis)
            print(f"\n{'='*60}")
            print(f"Match {match_id}: {p1_name} ({p1_civ}) vs {p2_name} ({p2_civ})")
            print(f"{'='*60}")
            print(serialized)
            print()
            return True

        assert client is not None

        # Build prompts
        summary_prompt = build_match_summary_prompt(analysis)
        p1_prompt = build_player_narrative_prompt(analysis, "p1")
        p2_prompt = build_player_narrative_prompt(analysis, "p2")

        # Generate all three narratives in parallel
        match_summary, p1_narrative, p2_narrative = await asyncio.gather(
            async_generate(client, DEFAULT_MODEL, summary_prompt),
            async_generate(client, DEFAULT_MODEL, p1_prompt),
            async_generate(client, DEFAULT_MODEL, p2_prompt),
        )

        if preview:
            print(f"\n{'='*60}")
            print(f"Match {match_id}: {p1_name} ({p1_civ}) vs {p2_name} ({p2_civ})")
            print(f"{'='*60}")
            print(f"\n--- Match Summary ---\n{match_summary}")
            print(f"\n--- {p1_name} ({p1_civ}) ---\n{p1_narrative}")
            print(f"\n--- {p2_name} ({p2_civ}) ---\n{p2_narrative}")
            print()
            return True

        # Save to database
        save_narratives(write_conn, match_id, match_summary, p1_narrative, p2_narrative)

        logger.info(
            f"Match {match_id}: Saved narratives "
            f"(summary: {len(match_summary)} chars, "
            f"p1: {len(p1_narrative)} chars, "
            f"p2: {len(p2_narrative)} chars)"
        )
        return True

    except Exception as e:
        logger.error(f"Match {match_id}: Error - {e}", exc_info=True)
        return False


async def async_main(args: argparse.Namespace) -> int:
    """Async main entry point.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Check API key (unless dry-run)
    if not args.dry_run and not Config.ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY not found in environment")
        logger.error("Set it in .env file or environment variables")
        return 1

    # Initialize async client (unless dry-run)
    client: anthropic.AsyncAnthropic | None = None
    if not args.dry_run:
        client = anthropic.AsyncAnthropic(api_key=Config.ANTHROPIC_API_KEY)

    # Connect to database
    logger.info(f"Connecting to database: {Config.DATABASE_PATH}")
    needs_write = not args.dry_run and not args.preview
    db = TournamentDatabase(Config.DATABASE_PATH, read_only=not needs_write)
    queries = TournamentQueries(db)

    # Separate writable connection for UPDATE/SELECT statements
    write_conn: duckdb.DuckDBPyConnection | None = None
    if needs_write:
        write_conn = duckdb.connect(Config.DATABASE_PATH)

    try:
        # Get matches to process - use write_conn if available, otherwise read-only
        query_conn = write_conn if write_conn else db.connect()
        match_ids = get_matches_to_process(
            query_conn, force=args.force, match_id=args.match_id
        )

        if not match_ids:
            if args.force or args.match_id:
                logger.error("No matches found to process")
                return 1
            else:
                logger.info("No matches need narratives (all up to date)")
                return 0

        logger.info(f"Processing {len(match_ids)} matches")

        # Process each match sequentially (3 LLM calls per match run in parallel)
        success_count = 0
        error_count = 0

        for mid in match_ids:
            if await process_match(mid, queries, write_conn, client, args.dry_run, args.preview):
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
        if write_conn:
            write_conn.close()


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
        "--dry-run",
        action="store_true",
        help="Print serialized analysis without calling LLM",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Generate and print narratives without saving to database",
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

    return asyncio.run(async_main(args))


if __name__ == "__main__":
    sys.exit(main())
