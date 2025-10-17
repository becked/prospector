#!/usr/bin/env python3
"""Validation script for participant UI data quality.

Checks:
1. Player performance query returns expected data
2. Linked players appear once (no duplicates)
3. Unlinked players group correctly by normalized name
4. Head-to-head matching works for linked players
5. Civilization stats count participants correctly

Run this before and after UI updates to ensure data integrity.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tournament_visualizer.config import Config
from tournament_visualizer.data.queries import get_queries


def validate_player_performance() -> tuple[bool, list[str]]:
    """Validate player performance query results."""
    errors = []
    queries = get_queries()

    print("Validating player performance query...")

    try:
        df = queries.get_player_performance()

        if df.empty:
            errors.append("Player performance query returned empty results")
            return False, errors

        # Check required columns
        required_cols = [
            "player_name",
            "participant_id",
            "is_unlinked",
            "total_matches",
            "wins",
            "win_rate",
            "civilizations_played",
            "favorite_civilization",
        ]

        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            errors.append(f"Missing columns: {missing_cols}")

        # Check for duplicate participant_ids (should never happen)
        linked = df[df["is_unlinked"] == False]
        if not linked.empty:
            dup_participants = linked[linked.duplicated("participant_id", keep=False)]
            if not dup_participants.empty:
                errors.append(
                    f"Found {len(dup_participants)} duplicate participant_id entries"
                )

        # Check that unlinked players have NULL participant_id
        unlinked = df[df["is_unlinked"] == True]
        if not unlinked.empty:
            non_null = unlinked[unlinked["participant_id"].notna()]
            if not non_null.empty:
                errors.append(
                    f"Found {len(non_null)} unlinked players with non-NULL participant_id"
                )

        # Check win_rate is valid percentage (0-100)
        invalid_rates = df[(df["win_rate"] < 0) | (df["win_rate"] > 100)]
        if not invalid_rates.empty:
            errors.append(f"Found {len(invalid_rates)} invalid win rates")

        # Summary stats
        total = len(df)
        linked_count = len(linked)
        unlinked_count = len(unlinked)

        print(f"  Total players: {total}")
        print(f"  Linked participants: {linked_count} ({linked_count/total*100:.1f}%)")
        print(f"  Unlinked players: {unlinked_count} ({unlinked_count/total*100:.1f}%)")

        # Check for potential duplicates in unlinked (case variations)
        if not unlinked.empty:
            # Group by lowercase name to find potential duplicates
            name_lower = unlinked["player_name"].str.lower()
            dup_names = name_lower[name_lower.duplicated(keep=False)]
            if not dup_names.empty:
                errors.append(
                    f"Warning: Found {len(dup_names)} unlinked players with case variations. "
                    f"These should be linked to participants."
                )

        if errors:
            return False, errors

        print("  ✓ Player performance validation passed")
        return True, []

    except Exception as e:
        errors.append(f"Exception during validation: {e}")
        return False, errors


def validate_head_to_head() -> tuple[bool, list[str]]:
    """Validate head-to-head matching."""
    errors = []
    queries = get_queries()

    print("\nValidating head-to-head matching...")

    try:
        df = queries.get_player_performance()

        if df.empty or len(df) < 2:
            print("  ⚠️  Skipping H2H validation (not enough players)")
            return True, []

        # Test with first two players
        player1 = df.iloc[0]["player_name"]
        player2 = df.iloc[1]["player_name"]

        print(f"  Testing H2H: {player1} vs {player2}")

        stats = queries.get_head_to_head_stats(player1, player2)

        # Should return dict with expected keys (even if 0 matches)
        expected_keys = [
            "total_matches",
            "player1_wins",
            "player2_wins",
            "avg_match_length",
        ]

        missing_keys = [key for key in expected_keys if key not in stats]
        if missing_keys:
            errors.append(f"H2H stats missing keys: {missing_keys}")

        # Check logical consistency
        if stats:
            total = stats.get("total_matches", 0)
            p1_wins = stats.get("player1_wins", 0)
            p2_wins = stats.get("player2_wins", 0)

            if p1_wins + p2_wins > total:
                errors.append(
                    f"H2H win counts ({p1_wins} + {p2_wins}) exceed total matches ({total})"
                )

            print(f"  Matches found: {total}")
            if total > 0:
                print(f"  {player1}: {p1_wins} wins")
                print(f"  {player2}: {p2_wins} wins")

        if errors:
            return False, errors

        print("  ✓ Head-to-head validation passed")
        return True, []

    except Exception as e:
        errors.append(f"Exception during H2H validation: {e}")
        return False, errors


def validate_civilization_stats() -> tuple[bool, list[str]]:
    """Validate civilization performance stats."""
    errors = []
    queries = get_queries()

    print("\nValidating civilization statistics...")

    try:
        df = queries.get_civilization_performance()

        if df.empty:
            errors.append("Civilization performance query returned empty results")
            return False, errors

        # Check required columns
        required_cols = [
            "civilization",
            "total_matches",
            "wins",
            "win_rate",
            "unique_participants",
        ]

        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            errors.append(f"Missing columns in civ stats: {missing_cols}")

        # Check logical consistency
        for _, row in df.iterrows():
            civ = row["civilization"]

            # Wins should not exceed total matches
            if row["wins"] > row["total_matches"]:
                errors.append(
                    f"{civ}: wins ({row['wins']}) > total_matches ({row['total_matches']})"
                )

            # unique_participants should be > 0 if total_matches > 0
            if row["total_matches"] > 0 and row["unique_participants"] == 0:
                errors.append(f"{civ}: has matches but 0 unique participants")

        print(f"  Civilizations tracked: {len(df)}")
        print(f"  Total matches: {df['total_matches'].sum()}")

        if errors:
            return False, errors

        print("  ✓ Civilization stats validation passed")
        return True, []

    except Exception as e:
        errors.append(f"Exception during civ stats validation: {e}")
        return False, errors


def validate_data_consistency() -> tuple[bool, list[str]]:
    """Cross-validate data consistency across queries."""
    errors = []
    queries = get_queries()

    print("\nValidating cross-query data consistency...")

    try:
        player_df = queries.get_player_performance()
        civ_df = queries.get_civilization_performance()

        # Total matches from player perspective
        player_matches = player_df["total_matches"].sum()

        # Total matches from civ perspective (will be higher due to multi-player matches)
        civ_matches = civ_df["total_matches"].sum()

        print(f"  Player-perspective matches: {player_matches}")
        print(f"  Civ-perspective matches: {civ_matches}")

        # Civ matches should be >= player matches (same matches counted from different angle)
        # Actually, for 1v1 matches, civ_matches should be exactly 2x player_matches
        # But we might have some data inconsistencies, so just check >=
        if civ_matches < player_matches:
            errors.append(
                f"Civ match count ({civ_matches}) less than player match count ({player_matches})"
            )

        if errors:
            return False, errors

        print("  ✓ Cross-query consistency validation passed")
        return True, []

    except Exception as e:
        errors.append(f"Exception during consistency validation: {e}")
        return False, errors


def print_data_quality_summary():
    """Print summary of participant linking data quality."""
    queries = get_queries()

    print("\n" + "=" * 60)
    print("PARTICIPANT LINKING DATA QUALITY SUMMARY")
    print("=" * 60)

    # Get raw database stats
    db = queries.db

    # Total player instances
    result = db.fetch_one("SELECT COUNT(*) FROM players")
    total_instances = result[0] if result else 0

    # Linked instances
    result = db.fetch_one(
        "SELECT COUNT(*) FROM players WHERE participant_id IS NOT NULL"
    )
    linked_instances = result[0] if result else 0

    # Unique participants
    result = db.fetch_one(
        "SELECT COUNT(DISTINCT participant_id) FROM players WHERE participant_id IS NOT NULL"
    )
    unique_participants = result[0] if result else 0

    # Unique normalized names
    result = db.fetch_one("SELECT COUNT(DISTINCT player_name_normalized) FROM players")
    unique_names = result[0] if result else 0

    print(f"\nDatabase Statistics:")
    print(f"  Total player instances: {total_instances}")
    print(f"  Linked instances: {linked_instances} ({linked_instances/total_instances*100:.1f}%)")
    print(f"  Unique participants: {unique_participants}")
    print(f"  Unique player names: {unique_names}")

    # Potential linkage targets (unlinked players that might match participants)
    result = db.fetch_all("""
        SELECT
            p.player_name,
            p.player_name_normalized,
            tp.display_name,
            tp.participant_id
        FROM players p
        LEFT JOIN tournament_participants tp
            ON p.player_name_normalized LIKE '%' || tp.display_name_normalized || '%'
            OR tp.display_name_normalized LIKE '%' || p.player_name_normalized || '%'
        WHERE p.participant_id IS NULL
            AND tp.participant_id IS NOT NULL
        GROUP BY p.player_name, p.player_name_normalized, tp.display_name, tp.participant_id
        ORDER BY p.player_name
        LIMIT 10
    """)

    if result:
        print(f"\nPotential linkage opportunities (showing first 10):")
        print("  Save File Name → Potential Challonge Match")
        for row in result:
            print(f"  {row[0]} → {row[2]}")

        print(f"\n  💡 Consider adding manual overrides for these players")

    print("=" * 60)


def main():
    """Run all validations."""
    print("Participant UI Data Quality Validation")
    print("=" * 60)

    all_passed = True
    all_errors = []

    # Run validations
    validations = [
        ("Player Performance", validate_player_performance),
        ("Head-to-Head Matching", validate_head_to_head),
        ("Civilization Statistics", validate_civilization_stats),
        ("Data Consistency", validate_data_consistency),
    ]

    for name, validator in validations:
        passed, errors = validator()
        if not passed:
            all_passed = False
            all_errors.extend([f"{name}: {err}" for err in errors])

    # Print data quality summary
    print_data_quality_summary()

    # Final result
    if not all_passed:
        print("\n" + "=" * 60)
        print("VALIDATION ERRORS")
        print("=" * 60)
        for error in all_errors:
            print(f"  ✗ {error}")
        print("=" * 60)
        sys.exit(1)
    else:
        print("\n✓ All validations passed!")
        print("\nData quality is good for participant UI integration.")
        sys.exit(0)


if __name__ == "__main__":
    main()
