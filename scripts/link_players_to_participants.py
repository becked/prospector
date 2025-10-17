#!/usr/bin/env python3
"""Link save file players to tournament participants.

Matches player names from save files to Challonge participants using
normalized name matching. Reports unmatched players that may need
manual overrides.

Prerequisites:
- Database must contain player data (from save file import)
- Participants must be synced (run sync_challonge_participants.py first)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tournament_visualizer.config import Config
from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.participant_matcher import ParticipantMatcher


def print_summary(stats: dict) -> None:
    """Print summary of matching results.

    Args:
        stats: Statistics dictionary from ParticipantMatcher.link_all_matches()
    """
    print("\n" + "=" * 60)
    print("PLAYER-PARTICIPANT LINKING SUMMARY")
    print("=" * 60)

    print(f"\nTotal matches processed: {stats['total_matches']}")
    print(f"Total players: {stats['total_players']}")
    print(f"Successfully matched: {stats['matched_players']}")
    print(f"Unmatched: {stats['unmatched_players']}")

    if stats['total_players'] > 0:
        match_rate = (stats['matched_players'] / stats['total_players']) * 100
        print(f"Match rate: {match_rate:.1f}%")

    print(f"\nMatches fully matched: {stats['matches_fully_matched']}")
    print(f"Matches with unmatched players: {stats['matches_with_unmatched']}")

    # Show unmatched players by match
    if stats['unmatched_by_match']:
        print("\nUnmatched players by match:")
        print("-" * 60)

        for match_id, unmatched_names in stats['unmatched_by_match'].items():
            print(f"\nMatch {match_id}:")
            for name in unmatched_names:
                print(f"  - {name}")

        print("\n" + "-" * 60)
        print("\nTo fix unmatched players:")
        print("1. Review the unmatched names above")
        print("2. Find their correct participant IDs in tournament_participants")
        print("3. Add entries to participant_name_overrides table")
        print("4. Re-run this script")

    print("=" * 60)


def verify_prerequisites(db: TournamentDatabase) -> bool:
    """Verify required data exists before linking.

    Args:
        db: Database instance

    Returns:
        True if prerequisites met, False otherwise
    """
    # Check for participants
    participant_count = db.fetch_one("SELECT COUNT(*) FROM tournament_participants")[0]

    if participant_count == 0:
        print("ERROR: No participants found in database")
        print("Run sync_challonge_participants.py first")
        return False

    # Check for players
    player_count = db.fetch_one("SELECT COUNT(*) FROM players")[0]

    if player_count == 0:
        print("ERROR: No players found in database")
        print("Import save files first using import_attachments.py")
        return False

    print(f"Found {participant_count} participants and {player_count} players")
    return True


def main() -> None:
    """Main function."""
    print("Player-Participant Linking Script")
    print("=" * 60)

    try:
        # Connect to database in read-write mode
        db = TournamentDatabase(Config.DATABASE_PATH, read_only=False)

        # Verify prerequisites
        if not verify_prerequisites(db):
            sys.exit(1)

        # Create matcher and link all players
        matcher = ParticipantMatcher(db)
        stats = matcher.link_all_matches()

        # Print summary
        print_summary(stats)

        db.close()

        # Exit with error code if there were unmatched players
        if stats['unmatched_players'] > 0:
            sys.exit(1)
        else:
            print("\nAll players successfully linked!")
            sys.exit(0)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
