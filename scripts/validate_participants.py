#!/usr/bin/env python3
"""Validation script for participant linking integrity.

Checks:
1. All participants have valid data
2. Player-participant links are valid
3. Match participant IDs match player linkages
4. No orphaned links
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tournament_visualizer.config import Config
from tournament_visualizer.data.database import TournamentDatabase


def validate_participant_data(db: TournamentDatabase) -> tuple[bool, list[str]]:
    """Validate participant table data integrity.

    Args:
        db: Database instance

    Returns:
        Tuple of (is_valid, errors)
    """
    errors = []

    # Check for NULL display names
    null_names = db.fetch_one(
        """
        SELECT COUNT(*)
        FROM tournament_participants
        WHERE display_name IS NULL OR display_name = ''
        """
    )[0]

    if null_names > 0:
        errors.append(f"Found {null_names} participants with NULL/empty display names")

    # Check normalized names
    null_normalized = db.fetch_one(
        """
        SELECT COUNT(*)
        FROM tournament_participants
        WHERE display_name_normalized IS NULL OR display_name_normalized = ''
        """
    )[0]

    if null_normalized > 0:
        errors.append(
            f"Found {null_normalized} participants with NULL/empty normalized names"
        )

    return len(errors) == 0, errors


def validate_player_participant_links(db: TournamentDatabase) -> tuple[bool, list[str]]:
    """Validate player-participant linkages.

    Args:
        db: Database instance

    Returns:
        Tuple of (is_valid, errors)
    """
    errors = []

    # Check for invalid participant_id references
    invalid_refs = db.fetch_one(
        """
        SELECT COUNT(*)
        FROM players p
        LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
        WHERE p.participant_id IS NOT NULL
        AND tp.participant_id IS NULL
        """
    )[0]

    if invalid_refs > 0:
        errors.append(
            f"Found {invalid_refs} players with invalid participant_id references"
        )

    return len(errors) == 0, errors


def validate_match_participant_consistency(
    db: TournamentDatabase,
) -> tuple[bool, list[str]]:
    """Validate match participant IDs match player linkages.

    Args:
        db: Database instance

    Returns:
        Tuple of (is_valid, errors)
    """
    errors = []

    # For each match, check if players' participant_ids match match.player1/2_participant_id
    inconsistent = db.fetch_one(
        """
        WITH match_players AS (
            SELECT
                m.match_id,
                m.player1_participant_id,
                m.player2_participant_id,
                p.participant_id as player_participant_id
            FROM matches m
            JOIN players p ON m.match_id = p.match_id
            WHERE m.player1_participant_id IS NOT NULL
            AND m.player2_participant_id IS NOT NULL
            AND p.participant_id IS NOT NULL
        )
        SELECT COUNT(DISTINCT match_id)
        FROM match_players
        WHERE player_participant_id NOT IN (player1_participant_id, player2_participant_id)
        """
    )[0]

    if inconsistent > 0:
        errors.append(
            f"Found {inconsistent} matches where player participant IDs don't match "
            "match participant IDs"
        )

    return len(errors) == 0, errors


def print_summary(db: TournamentDatabase) -> None:
    """Print summary statistics.

    Args:
        db: Database instance
    """
    print("\n" + "=" * 60)
    print("PARTICIPANT DATA SUMMARY")
    print("=" * 60)

    total_participants = db.fetch_one("SELECT COUNT(*) FROM tournament_participants")[0]

    total_players = db.fetch_one("SELECT COUNT(*) FROM players")[0]

    linked_players = db.fetch_one(
        "SELECT COUNT(*) FROM players WHERE participant_id IS NOT NULL"
    )[0]

    print(f"\nTotal participants: {total_participants}")
    print(f"Total players: {total_players}")

    if total_players > 0:
        link_percentage = (linked_players / total_players) * 100
        print(f"Linked players: {linked_players} ({link_percentage:.1f}%)")
    else:
        print("Linked players: 0")

    # Unique participants with players
    unique_participants = db.fetch_one(
        """
        SELECT COUNT(DISTINCT participant_id)
        FROM players
        WHERE participant_id IS NOT NULL
        """
    )[0]

    if total_participants > 0:
        print(
            f"Participants with players: {unique_participants}/{total_participants}"
        )

    print("=" * 60)


def main() -> None:
    """Run all validations."""
    print("Validating participant data...")

    db = TournamentDatabase(Config.DATABASE_PATH, read_only=True)

    validations = [
        ("Participant data integrity", validate_participant_data),
        ("Player-participant links", validate_player_participant_links),
        ("Match-participant consistency", validate_match_participant_consistency),
    ]

    all_valid = True
    all_errors = []

    for name, validator in validations:
        print(f"\nChecking {name}...", end=" ")
        is_valid, errors = validator(db)

        if is_valid:
            print("✓ PASS")
        else:
            print("✗ FAIL")
            all_errors.extend([f"\n{name}:"] + errors)
            all_valid = False

    print_summary(db)

    if not all_valid:
        print("\n" + "=" * 60)
        print("VALIDATION ERRORS")
        print("=" * 60)
        for error in all_errors:
            print(error)
        print("=" * 60)
        sys.exit(1)
    else:
        print("\n✓ All validations passed!")
        sys.exit(0)

    db.close()


if __name__ == "__main__":
    main()
