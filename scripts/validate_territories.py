#!/usr/bin/env python3
"""Validate territory data quality.

Checks for:
- Missing turns in sequences
- Invalid coordinates
- Orphaned player references
- Data consistency issues
"""

import sys
from typing import List

from tournament_visualizer.data.database import get_database


def check_turn_sequences() -> List[str]:
    """Verify no gaps in turn sequences for each match."""
    db = get_database()
    issues = []

    query = """
    SELECT
        match_id,
        MIN(turn_number) as min_turn,
        MAX(turn_number) as max_turn,
        COUNT(DISTINCT turn_number) as unique_turns
    FROM territories
    GROUP BY match_id
    """

    results = db.fetch_all(query)

    for match_id, min_turn, max_turn, unique_turns in results:
        expected_turns = max_turn - min_turn + 1
        if unique_turns != expected_turns:
            issues.append(
                f"Match {match_id}: Expected {expected_turns} turns "
                f"({min_turn}-{max_turn}), found {unique_turns}"
            )

    return issues


def check_coordinate_validity() -> List[str]:
    """Verify coordinates are within valid map bounds."""
    db = get_database()
    issues = []

    query = """
    SELECT DISTINCT match_id, x_coordinate, y_coordinate
    FROM territories
    WHERE x_coordinate < 0 OR y_coordinate < 0
       OR x_coordinate > 100 OR y_coordinate > 100
    """

    results = db.fetch_all(query)

    if results:
        issues.append(f"Found {len(results)} records with invalid coordinates")
        for match_id, x, y in results[:5]:  # Show first 5
            issues.append(f"  Match {match_id}: ({x}, {y})")

    return issues


def check_tile_counts() -> List[str]:
    """Verify each match has consistent tile count across turns."""
    db = get_database()
    issues = []

    query = """
    SELECT
        match_id,
        turn_number,
        COUNT(*) as tile_count
    FROM territories
    GROUP BY match_id, turn_number
    HAVING tile_count != (
        SELECT COUNT(*)
        FROM territories t2
        WHERE t2.match_id = territories.match_id
          AND t2.turn_number = 1
    )
    """

    results = db.fetch_all(query)

    if results:
        issues.append(f"Found {len(results)} turns with inconsistent tile counts")
        for match_id, turn, count in results[:5]:
            issues.append(f"  Match {match_id}, Turn {turn}: {count} tiles")

    return issues


def check_orphaned_players() -> List[str]:
    """Verify all owner_player_id values reference valid players."""
    db = get_database()
    issues = []

    query = """
    SELECT DISTINCT t.owner_player_id, t.match_id
    FROM territories t
    LEFT JOIN players p ON t.owner_player_id = p.player_id
    WHERE t.owner_player_id IS NOT NULL
      AND p.player_id IS NULL
    """

    results = db.fetch_all(query)

    if results:
        issues.append(f"Found {len(results)} orphaned player references")
        for player_id, match_id in results[:5]:
            issues.append(f"  Player {player_id} in Match {match_id}")

    return issues


def check_ownership_sanity() -> List[str]:
    """Verify ownership data makes sense."""
    db = get_database()
    issues = []

    # Check: Most tiles at turn 1 should be unowned
    query = """
    SELECT
        COUNT(*) as total,
        COUNT(owner_player_id) as owned,
        100.0 * COUNT(owner_player_id) / COUNT(*) as pct_owned
    FROM territories
    WHERE turn_number = 1
    """

    result = db.fetch_one(query)
    if result:
        total, owned, pct_owned = result
        if pct_owned > 20:  # More than 20% owned at turn 1 is suspicious
            issues.append(
                f"Turn 1 ownership seems high: {pct_owned:.1f}% "
                f"({owned}/{total} tiles)"
            )

    # Check: Final turn should have more ownership
    query = """
    SELECT
        t.match_id,
        COUNT(*) as total,
        COUNT(owner_player_id) as owned,
        100.0 * COUNT(owner_player_id) / COUNT(*) as pct_owned
    FROM territories t
    INNER JOIN (
        SELECT match_id, MAX(turn_number) as final_turn
        FROM territories
        GROUP BY match_id
    ) final ON t.match_id = final.match_id
           AND t.turn_number = final.final_turn
    GROUP BY t.match_id
    HAVING pct_owned < 10
    """

    results = db.fetch_all(query)
    if results:
        issues.append(
            f"Found {len(results)} matches with low final ownership (< 10%)"
        )

    return issues


def check_terrain_coverage() -> List[str]:
    """Verify terrain data is populated."""
    db = get_database()
    issues = []

    query = """
    SELECT
        COUNT(*) as total,
        COUNT(terrain_type) as with_terrain,
        100.0 * COUNT(terrain_type) / COUNT(*) as pct
    FROM territories
    """

    result = db.fetch_one(query)
    if result:
        total, with_terrain, pct = result
        if pct < 95:  # Expect at least 95% to have terrain
            issues.append(
                f"Terrain coverage low: {pct:.1f}% "
                f"({with_terrain}/{total} records)"
            )

    return issues


def main() -> int:
    """Run all validation checks."""
    print("Validating territory data...\n")

    all_issues = []

    checks = [
        ("Turn sequences", check_turn_sequences),
        ("Coordinate validity", check_coordinate_validity),
        ("Tile counts", check_tile_counts),
        ("Orphaned players", check_orphaned_players),
        ("Ownership sanity", check_ownership_sanity),
        ("Terrain coverage", check_terrain_coverage),
    ]

    for check_name, check_func in checks:
        print(f"Checking {check_name}...", end=" ")
        issues = check_func()

        if issues:
            print(f"❌ {len(issues)} issue(s)")
            all_issues.extend(issues)
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("✓")

    print(f"\n{'='*60}")
    if all_issues:
        print(f"❌ Validation failed with {len(all_issues)} issue(s)")
        return 1
    else:
        print("✓ All validation checks passed")
        return 0


if __name__ == "__main__":
    sys.exit(main())
