#!/usr/bin/env python3
"""Sync Challonge participant data to database.

Downloads tournament participants from Challonge API and stores them
in the tournament_participants table. Also updates matches table with
participant IDs for player1, player2, and winner.

This script should be run:
1. After database schema migration
2. Before importing save files
3. Whenever tournament participants change
"""

import os
import sys
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from chyllonge.api import ChallongeApi
from dotenv import load_dotenv

from tournament_visualizer.config import Config
from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.name_normalizer import normalize_name


def load_config() -> str:
    """Load tournament ID from environment variables.

    Returns:
        Tournament ID string

    Raises:
        ValueError: If required environment variables are missing
    """
    load_dotenv()

    tournament_id = os.getenv("challonge_tournament_id")

    if not tournament_id:
        raise ValueError(
            "challonge_tournament_id not found in environment variables"
        )

    if not os.getenv("CHALLONGE_KEY"):
        raise ValueError("CHALLONGE_KEY not found in environment variables")

    if not os.getenv("CHALLONGE_USER"):
        raise ValueError("CHALLONGE_USER not found in environment variables")

    return tournament_id


def fetch_participants(api: ChallongeApi, tournament_id: str) -> list[dict[str, Any]]:
    """Fetch all participants from Challonge tournament.

    Args:
        api: Challonge API client
        tournament_id: Tournament ID

    Returns:
        List of participant dictionaries
    """
    print(f"Fetching participants for tournament {tournament_id}...")

    try:
        participants = api.participants.get_all(tournament_id)
        print(f"Found {len(participants)} participants")
        return participants
    except Exception as e:
        print(f"Error fetching participants: {e}")
        return []


def fetch_matches(api: ChallongeApi, tournament_id: str) -> list[dict[str, Any]]:
    """Fetch all matches from Challonge tournament.

    Args:
        api: Challonge API client
        tournament_id: Tournament ID

    Returns:
        List of match dictionaries
    """
    print(f"Fetching matches for tournament {tournament_id}...")

    try:
        matches = api.matches.get_all(tournament_id)
        print(f"Found {len(matches)} matches")
        return matches
    except Exception as e:
        print(f"Error fetching matches: {e}")
        return []


def insert_participants(
    db: TournamentDatabase, participants: list[dict[str, Any]]
) -> int:
    """Insert participants into database.

    Args:
        db: Database instance
        participants: List of participant data from Challonge

    Returns:
        Number of participants inserted
    """
    if not participants:
        print("No participants to insert")
        return 0

    print(f"Inserting {len(participants)} participants...")

    with db.get_connection() as conn:
        # Clear existing participants (full refresh)
        conn.execute("DELETE FROM tournament_participants")

        inserted = 0

        for participant in participants:
            try:
                participant_id = participant.get("id")
                display_name = participant.get("display_name") or participant.get("name")

                if not participant_id or not display_name:
                    print(f"Skipping participant with missing ID or name: {participant}")
                    continue

                # Normalize name for matching
                normalized_name = normalize_name(display_name)

                conn.execute(
                    """
                    INSERT INTO tournament_participants (
                        participant_id,
                        display_name,
                        display_name_normalized,
                        challonge_username,
                        challonge_user_id,
                        seed,
                        final_rank,
                        created_at,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        participant_id,
                        display_name,
                        normalized_name,
                        participant.get("challonge_username"),
                        participant.get("challonge_user_id"),
                        participant.get("seed"),
                        participant.get("final_rank"),
                        participant.get("created_at"),
                        participant.get("updated_at"),
                    ],
                )

                inserted += 1

            except Exception as e:
                print(f"Error inserting participant {participant.get('id')}: {e}")
                continue

        print(f"Inserted {inserted} participants")
        return inserted


def update_match_participants(
    db: TournamentDatabase, challonge_matches: list[dict[str, Any]]
) -> tuple[int, int]:
    """Update matches table with participant IDs.

    Links matches to participants by matching challonge_match_id.

    Args:
        db: Database instance
        challonge_matches: List of match data from Challonge

    Returns:
        Tuple of (matches_updated, matches_not_found)
    """
    if not challonge_matches:
        print("No Challonge matches to process")
        return 0, 0

    print(f"Updating {len(challonge_matches)} matches with participant IDs...")

    updated = 0
    not_found = 0

    with db.get_connection() as conn:
        for challonge_match in challonge_matches:
            challonge_match_id = challonge_match.get("id")

            if not challonge_match_id:
                continue

            # Check if this match exists in our database
            result = conn.execute(
                "SELECT match_id FROM matches WHERE challonge_match_id = ?",
                [challonge_match_id],
            ).fetchone()

            if not result:
                not_found += 1
                continue

            match_id = result[0]

            # Update with participant IDs
            player1_participant_id = challonge_match.get("player1_id")
            player2_participant_id = challonge_match.get("player2_id")
            winner_participant_id = challonge_match.get("winner_id")

            conn.execute(
                """
                UPDATE matches
                SET player1_participant_id = ?,
                    player2_participant_id = ?,
                    winner_participant_id = ?
                WHERE match_id = ?
                """,
                [
                    player1_participant_id,
                    player2_participant_id,
                    winner_participant_id,
                    match_id,
                ],
            )

            updated += 1

    print(f"Updated {updated} matches")
    if not_found > 0:
        print(f"Warning: {not_found} Challonge matches not found in database")

    return updated, not_found


def print_summary(db: TournamentDatabase) -> None:
    """Print summary of participant data.

    Args:
        db: Database instance
    """
    print("\n" + "=" * 60)
    print("PARTICIPANT SYNC SUMMARY")
    print("=" * 60)

    with db.get_connection() as conn:
        # Total participants
        total = conn.execute("SELECT COUNT(*) FROM tournament_participants").fetchone()[
            0
        ]

        print(f"\nTotal participants: {total}")

        # Participants with Challonge accounts
        with_accounts = conn.execute(
            "SELECT COUNT(*) FROM tournament_participants WHERE challonge_user_id IS NOT NULL"
        ).fetchone()[0]

        print(f"With Challonge accounts: {with_accounts}")

        # Matches with participant data
        matches_with_participants = conn.execute(
            """
            SELECT COUNT(*)
            FROM matches
            WHERE player1_participant_id IS NOT NULL
            AND player2_participant_id IS NOT NULL
            """
        ).fetchone()[0]

        total_matches = conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]

        print(
            f"\nMatches with participant data: {matches_with_participants}/{total_matches}"
        )

        # Sample participants
        print("\nSample participants:")
        samples = conn.execute(
            """
            SELECT display_name, seed, challonge_username
            FROM tournament_participants
            ORDER BY seed
            LIMIT 10
            """
        ).fetchall()

        for display_name, seed, username in samples:
            username_str = f" (@{username})" if username else ""
            print(f"  Seed {seed}: {display_name}{username_str}")

    print("=" * 60)


def main() -> None:
    """Main function."""
    try:
        # Load configuration
        tournament_id = load_config()

        # Create Challonge API client
        api = ChallongeApi()

        # Fetch data from Challonge
        participants = fetch_participants(api, tournament_id)
        matches = fetch_matches(api, tournament_id)

        if not participants:
            print("No participants found. Exiting.")
            sys.exit(1)

        # Connect to database
        db = TournamentDatabase(Config.DATABASE_PATH, read_only=False)

        # Insert participants
        insert_participants(db, participants)

        # Update matches with participant IDs
        update_match_participants(db, matches)

        # Print summary
        print_summary(db)

        db.close()

        print("\nParticipant sync complete!")

    except ValueError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
