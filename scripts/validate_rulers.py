#!/usr/bin/env python3
"""Validation script for ruler data integrity.

This script checks:
1. All rulers have corresponding players
2. Succession order is sequential for each player
3. Starting rulers are at turn 1
4. Successor rulers have succession_turn > 1
5. Archetype and trait values are valid
6. No duplicate rulers within a player's succession
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tournament_visualizer.config import Config
from tournament_visualizer.data.database import TournamentDatabase


def validate_foreign_keys(db: TournamentDatabase) -> tuple[bool, list[str]]:
    """Validate that all rulers have corresponding players.

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    # Check for orphaned rulers
    with db.get_connection() as conn:
        orphaned = conn.execute(
            """
            SELECT r.ruler_id, r.match_id, r.player_id
            FROM rulers r
            LEFT JOIN players p ON r.player_id = p.player_id AND r.match_id = p.match_id
            WHERE p.player_id IS NULL
            """
        ).fetchall()

    if orphaned:
        errors.append(f"Found {len(orphaned)} rulers without corresponding players:")
        for ruler_id, match_id, player_id in orphaned[:5]:
            errors.append(f"  Ruler {ruler_id}: match={match_id}, player={player_id}")

    return len(errors) == 0, errors


def validate_succession_order(db: TournamentDatabase) -> tuple[bool, list[str]]:
    """Validate that succession order is sequential for each player.

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    # Check for gaps or duplicates in succession order
    with db.get_connection() as conn:
        gaps = conn.execute(
            """
            WITH succession_gaps AS (
                SELECT
                    match_id,
                    player_id,
                    succession_order,
                    LAG(succession_order) OVER (
                        PARTITION BY match_id, player_id
                        ORDER BY succession_order
                    ) as prev_order
                FROM rulers
            )
            SELECT match_id, player_id, succession_order, prev_order
            FROM succession_gaps
            WHERE prev_order IS NOT NULL
            AND succession_order != prev_order + 1
            """
        ).fetchall()

    if gaps:
        errors.append(f"Found {len(gaps)} succession order gaps or duplicates:")
        for match_id, player_id, order, prev_order in gaps[:5]:
            errors.append(
                f"  Match {match_id}, Player {player_id}: "
                f"order {order} after {prev_order}"
            )

    return len(errors) == 0, errors


def validate_succession_turns(db: TournamentDatabase) -> tuple[bool, list[str]]:
    """Validate succession turn constraints.

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    # Starting rulers should be at turn 1
    with db.get_connection() as conn:
        bad_starting_turns = conn.execute(
            """
            SELECT match_id, player_id, ruler_name, succession_turn
            FROM rulers
            WHERE succession_order = 0
            AND succession_turn != 1
            """
        ).fetchall()

    if bad_starting_turns:
        errors.append(
            f"Found {len(bad_starting_turns)} starting rulers not at turn 1:"
        )
        for match_id, player_id, name, turn in bad_starting_turns[:5]:
            errors.append(
                f"  Match {match_id}, Player {player_id}, {name}: turn {turn}"
            )

    # Successor rulers should be after turn 1
    with db.get_connection() as conn:
        bad_successor_turns = conn.execute(
            """
            SELECT match_id, player_id, ruler_name, succession_turn, succession_order
            FROM rulers
            WHERE succession_order > 0
            AND succession_turn <= 1
            """
        ).fetchall()

    if bad_successor_turns:
        errors.append(
            f"Found {len(bad_successor_turns)} successors at/before turn 1:"
        )
        for match_id, player_id, name, turn, order in bad_successor_turns[:5]:
            errors.append(
                f"  Match {match_id}, Player {player_id}, {name} "
                f"(order {order}): turn {turn}"
            )

    return len(errors) == 0, errors


def validate_archetype_values(db: TournamentDatabase) -> tuple[bool, list[str]]:
    """Validate archetype values are from expected set.

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    valid_archetypes = {"Scholar", "Tactician", "Commander", "Schemer", "Builder", "Judge", "Zealot"}

    with db.get_connection() as conn:
        invalid = conn.execute(
            """
            SELECT DISTINCT archetype, COUNT(*) as count
            FROM rulers
            WHERE archetype IS NOT NULL
            AND archetype NOT IN ('Scholar', 'Tactician', 'Commander', 'Schemer', 'Builder', 'Judge', 'Zealot')
            GROUP BY archetype
            """
        ).fetchall()

    if invalid:
        errors.append(f"Found {len(invalid)} invalid archetype values:")
        for archetype, count in invalid:
            errors.append(f"  '{archetype}': {count} occurrences")

    return len(errors) == 0, errors


def validate_duplicate_rulers(db: TournamentDatabase) -> tuple[bool, list[str]]:
    """Validate no duplicate character IDs within a player's succession.

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    with db.get_connection() as conn:
        duplicates = conn.execute(
            """
            SELECT match_id, player_id, character_id, COUNT(*) as count
            FROM rulers
            GROUP BY match_id, player_id, character_id
            HAVING COUNT(*) > 1
            """
        ).fetchall()

    if duplicates:
        errors.append(
            f"Found {len(duplicates)} duplicate character IDs in succession:"
        )
        for match_id, player_id, char_id, count in duplicates[:5]:
            errors.append(
                f"  Match {match_id}, Player {player_id}, "
                f"Character {char_id}: {count} times"
            )

    return len(errors) == 0, errors


def print_summary(db: TournamentDatabase) -> None:
    """Print summary statistics about rulers."""
    print("\n" + "=" * 60)
    print("RULER DATA SUMMARY")
    print("=" * 60)

    # Total counts
    with db.get_connection() as conn:
        total_rulers = conn.execute("SELECT COUNT(*) FROM rulers").fetchone()[0]
        total_players = conn.execute(
            "SELECT COUNT(DISTINCT player_id) FROM rulers"
        ).fetchone()[0]

    print(f"\nTotal rulers: {total_rulers}")
    print(f"Players with rulers: {total_players}")
    print(f"Average rulers per player: {total_rulers / total_players:.2f}")

    # Succession statistics
    with db.get_connection() as conn:
        succession_stats = conn.execute(
            """
            SELECT
                MIN(ruler_count) as min_rulers,
                MAX(ruler_count) as max_rulers,
                AVG(ruler_count) as avg_rulers
            FROM (
                SELECT player_id, COUNT(*) as ruler_count
                FROM rulers
                GROUP BY player_id
            ) subquery
            """
        ).fetchone()

    print(f"\nRulers per player: min={succession_stats[0]}, "
          f"max={succession_stats[1]}, avg={succession_stats[2]:.2f}")

    # Archetype distribution
    print("\nStarting archetype distribution:")
    with db.get_connection() as conn:
        archetypes = conn.execute(
            """
            SELECT
                COALESCE(archetype, 'Unknown') as archetype,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
            FROM rulers
            WHERE succession_order = 0
            GROUP BY archetype
            ORDER BY count DESC
            """
        ).fetchall()

    for archetype, count, pct in archetypes:
        print(f"  {archetype}: {count} ({pct}%)")

    # Starting trait distribution (top 10)
    print("\nTop 10 starting traits:")
    with db.get_connection() as conn:
        traits = conn.execute(
            """
            SELECT
                COALESCE(starting_trait, 'Unknown') as trait,
                COUNT(*) as count
            FROM rulers
            WHERE succession_order = 0
            GROUP BY starting_trait
            ORDER BY count DESC
            LIMIT 10
            """
        ).fetchall()

    for trait, count in traits:
        print(f"  {trait}: {count}")

    print("=" * 60)


def main() -> None:
    """Run all validations."""
    print("Validating ruler data...")

    # Connect to database
    db = TournamentDatabase(Config.DATABASE_PATH)

    # Run validations
    validations = [
        ("Foreign key integrity", validate_foreign_keys),
        ("Succession order", validate_succession_order),
        ("Succession turns", validate_succession_turns),
        ("Archetype values", validate_archetype_values),
        ("Duplicate rulers", validate_duplicate_rulers),
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

    # Print summary
    print_summary(db)

    # Print all errors at the end
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
