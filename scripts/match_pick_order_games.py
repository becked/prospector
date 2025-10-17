#!/usr/bin/env python3
"""Match pick_order_games to matches table and update picker columns.

This script:
1. Reads games from pick_order_games table
2. Matches each game to matches table using:
   - Player names (normalized) + round number
   - OR manual overrides from pick_order_overrides.json
3. Determines which player picked first by comparing nations to save file civs
4. Updates pick_order_games with match info
5. Updates matches table with picker participant IDs

Usage:
    python scripts/match_pick_order_games.py [--dry-run] [--verbose]

Examples:
    # Match pick order games
    python scripts/match_pick_order_games.py

    # Preview matches without writing
    python scripts/match_pick_order_games.py --dry-run

    # Verbose logging
    python scripts/match_pick_order_games.py --verbose
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import duckdb
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tournament_visualizer.config import Config

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def load_pick_order_overrides(
    override_path: Path = Path("data/pick_order_overrides.json")
) -> dict:
    """Load manual pick order match overrides.

    Args:
        override_path: Path to overrides JSON file

    Returns:
        Dictionary mapping game_number (str) to match_id (int)
    """
    if not override_path.exists():
        logger.debug(f"No overrides file found at {override_path}")
        return {}

    try:
        with open(override_path) as f:
            data = json.load(f)

        # Convert game_number keys to int
        overrides = {}
        for game_str, info in data.items():
            try:
                game_num = int(game_str.replace("game_", ""))
                match_id = info.get("challonge_match_id")
                if match_id:
                    overrides[game_num] = match_id
                    logger.debug(
                        f"Override: game {game_num} → match {match_id}"
                    )
            except (ValueError, KeyError) as e:
                logger.warning(f"Invalid override entry '{game_str}': {e}")

        logger.info(f"Loaded {len(overrides)} pick order overrides")
        return overrides

    except Exception as e:
        logger.error(f"Failed to load overrides: {e}")
        return {}


def match_games_to_matches(dry_run: bool = False) -> None:
    """Match pick order games to matches table.

    Args:
        dry_run: If True, don't write to database

    Raises:
        Exception: If matching fails
    """
    logger.info("Matching pick order games to matches...")

    # Load overrides
    overrides = load_pick_order_overrides()

    conn = duckdb.connect(Config.DATABASE_PATH)

    try:
        # Get all unmatched pick order games
        games = conn.execute("""
            SELECT
                game_number,
                round_number,
                player1_sheet_name,
                player2_sheet_name,
                first_pick_nation,
                second_pick_nation
            FROM pick_order_games
            WHERE matched_match_id IS NULL
            ORDER BY game_number
        """).fetchall()

        logger.info(f"Found {len(games)} unmatched games")

        if not games:
            logger.info("No games to match")
            return

        matched = 0
        failed = 0

        for game in games:
            game_num, round_num, p1_name, p2_name, first_nation, second_nation = game

            logger.debug(f"\nMatching game {game_num}: {p1_name} vs {p2_name}")

            # Check for manual override
            if game_num in overrides:
                match_id = overrides[game_num]
                logger.info(
                    f"  Using override: game {game_num} → match {match_id}"
                )

                # Get players from the match (need to get both from the match_id)
                match_players = conn.execute("""
                    SELECT player_id, player_name, civilization, participant_id
                    FROM players
                    WHERE match_id = ?
                    ORDER BY player_id
                """, [match_id]).fetchall()

                if len(match_players) != 2:
                    logger.warning(
                        f"  ❌ Override match {match_id} has {len(match_players)} players (expected 2)"
                    )
                    failed += 1
                    continue

                # Construct match_result tuple in the expected format
                p1 = match_players[0]
                p2 = match_players[1]
                match_result = (
                    match_id,
                    p1[0], p1[1], p1[2], p1[3],  # p1 data
                    p2[0], p2[1], p2[2], p2[3],  # p2 data
                )

                if not match_result:
                    logger.warning(
                        f"  ❌ Override match {match_id} not found in database"
                    )
                    failed += 1
                    continue

                confidence = "manual_override"
                reason = f"Manual override to match {match_id}"

            else:
                # Match by player names (normalized)
                # NOTE: Database uses simple .lower() normalization, not normalize_name()
                p1_norm = p1_name.lower()
                p2_norm = p2_name.lower()

                logger.debug(f"  Normalized: '{p1_norm}' vs '{p2_norm}'")

                # Find match with both players (in any order)
                # First, find all matches that have player 1
                candidate_matches = conn.execute("""
                    SELECT DISTINCT match_id
                    FROM players
                    WHERE player_name_normalized = ?
                """, [p1_norm]).fetchall()

                match_result = None
                for (candidate_match_id,) in candidate_matches:
                    # Check if this match also has player 2
                    has_p2 = conn.execute("""
                        SELECT COUNT(*)
                        FROM players
                        WHERE match_id = ? AND player_name_normalized = ?
                    """, [candidate_match_id, p2_norm]).fetchone()[0]

                    if has_p2 > 0:
                        # Found a match! Get the player details
                        match_players = conn.execute("""
                            SELECT player_id, player_name, civilization, participant_id
                            FROM players
                            WHERE match_id = ?
                            ORDER BY player_id
                        """, [candidate_match_id]).fetchall()

                        if len(match_players) == 2:
                            # Construct match_result tuple
                            p1_data = match_players[0]
                            p2_data = match_players[1]
                            match_result = (
                                candidate_match_id,
                                p1_data[0], p1_data[1], p1_data[2], p1_data[3],
                                p2_data[0], p2_data[1], p2_data[2], p2_data[3],
                            )
                            break

                if not match_result:
                    logger.warning(
                        f"  ❌ No match found for '{p1_name}' vs '{p2_name}'"
                    )
                    failed += 1
                    continue

                confidence = "normalized"
                reason = f"Matched by normalized names"

            # Extract match data
            (
                match_id,
                db_p1_id, db_p1_name, db_p1_civ, db_p1_participant,
                db_p2_id, db_p2_name, db_p2_civ, db_p2_participant
            ) = match_result

            logger.debug(
                f"  Found match {match_id}: {db_p1_name} ({db_p1_civ}) vs "
                f"{db_p2_name} ({db_p2_civ})"
            )

            # Determine which player picked first by matching nations
            # Compare first_pick_nation to player civilizations
            first_picker_participant = None
            second_picker_participant = None
            first_picker_sheet_name = None
            second_picker_sheet_name = None

            if db_p1_civ == first_nation:
                # Player 1 picked first
                first_picker_participant = db_p1_participant
                second_picker_participant = db_p2_participant
                first_picker_sheet_name = p1_name
                second_picker_sheet_name = p2_name
                logger.debug(
                    f"  → {db_p1_name} picked {first_nation} first, "
                    f"{db_p2_name} picked {second_nation} second"
                )
            elif db_p2_civ == first_nation:
                # Player 2 picked first
                first_picker_participant = db_p2_participant
                second_picker_participant = db_p1_participant
                first_picker_sheet_name = p2_name
                second_picker_sheet_name = p1_name
                logger.debug(
                    f"  → {db_p2_name} picked {first_nation} first, "
                    f"{db_p1_name} picked {second_nation} second"
                )
            else:
                logger.warning(
                    f"  ⚠️  Nation mismatch: first_pick={first_nation}, "
                    f"but players are {db_p1_civ}/{db_p2_civ}"
                )
                failed += 1
                continue

            # Verify second pick nation also matches
            if db_p1_civ == second_nation or db_p2_civ == second_nation:
                # Good - second nation matches
                pass
            else:
                logger.warning(
                    f"  ⚠️  Second pick nation mismatch: {second_nation}, "
                    f"but players are {db_p1_civ}/{db_p2_civ}"
                )
                failed += 1
                continue

            if dry_run:
                logger.info(
                    f"  ✓ [DRY RUN] Would match game {game_num} to match {match_id}"
                )
                matched += 1
                continue

            # Update pick_order_games table
            conn.execute("""
                UPDATE pick_order_games
                SET
                    matched_match_id = ?,
                    first_picker_participant_id = ?,
                    second_picker_participant_id = ?,
                    first_picker_sheet_name = ?,
                    second_picker_sheet_name = ?,
                    match_confidence = ?,
                    match_reason = ?,
                    matched_at = CURRENT_TIMESTAMP
                WHERE game_number = ?
            """, [
                match_id,
                first_picker_participant,
                second_picker_participant,
                first_picker_sheet_name,
                second_picker_sheet_name,
                confidence,
                reason,
                game_num,
            ])

            # Update matches table
            conn.execute("""
                UPDATE matches
                SET
                    first_picker_participant_id = ?,
                    second_picker_participant_id = ?
                WHERE match_id = ?
            """, [
                first_picker_participant,
                second_picker_participant,
                match_id,
            ])

            logger.info(f"  ✓ Matched game {game_num} to match {match_id}")
            matched += 1

        # Summary
        logger.info(f"\n{'='*60}")
        logger.info(f"Matching complete:")
        logger.info(f"  Matched: {matched}")
        logger.info(f"  Failed: {failed}")
        logger.info(f"  Total: {len(games)}")

        if not dry_run:
            # Show match statistics
            stats = conn.execute("""
                SELECT
                    COUNT(*) as total_games,
                    COUNT(matched_match_id) as matched_games,
                    COUNT(matched_match_id) * 100.0 / COUNT(*) as match_rate
                FROM pick_order_games
            """).fetchone()

            logger.info(f"\nDatabase statistics:")
            logger.info(f"  Total games in sheet: {stats[0]}")
            logger.info(f"  Matched to database: {stats[1]}")
            logger.info(f"  Match rate: {stats[2]:.1f}%")

            # Show matches table update count
            matches_updated = conn.execute("""
                SELECT COUNT(*)
                FROM matches
                WHERE first_picker_participant_id IS NOT NULL
            """).fetchone()[0]

            logger.info(f"  Matches with pick order: {matches_updated}")

    finally:
        conn.close()


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Match pick order games to matches table"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview matches without writing to database",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    setup_logging(args.verbose)

    try:
        match_games_to_matches(dry_run=args.dry_run)
    except Exception as e:
        logger.error(f"Matching failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
