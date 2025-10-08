#!/usr/bin/env python3
"""Validate that all MemoryData events have proper player ownership.

This script checks the database to ensure the MemoryData player ownership
fix is working correctly. It should be run after re-importing data.

Usage:
    uv run python scripts/validate_memorydata_ownership.py
"""

import sys
from typing import Tuple

import duckdb


def check_event_type_ownership(
    conn: duckdb.DuckDBPyConnection, pattern: str
) -> Tuple[int, int]:
    """Check how many events matching pattern have NULL vs valid player_id.

    Args:
        conn: Database connection
        pattern: SQL LIKE pattern (e.g., 'MEMORYTRIBE_%')

    Returns:
        Tuple of (total_events, null_count)
    """
    result = conn.execute(
        f"""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN player_id IS NULL THEN 1 ELSE 0 END) as null_count
        FROM events
        WHERE event_type LIKE '{pattern}'
    """
    ).fetchone()

    return result[0], result[1]


def main() -> int:
    """Run validation checks."""
    print("=" * 60)
    print("MemoryData Player Ownership Validation")
    print("=" * 60)
    print()

    # Connect to database
    try:
        conn = duckdb.connect("tournament_data.duckdb", read_only=True)
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        print("   Make sure tournament_data.duckdb exists")
        return 1

    # Check different event type categories
    checks = [
        ("MEMORYTRIBE_%", "MEMORYTRIBE Events"),
        ("MEMORYFAMILY_%", "MEMORYFAMILY Events"),
        ("MEMORYRELIGION_%", "MEMORYRELIGION Events"),
        ("MEMORYCHARACTER_%", "MEMORYCHARACTER Events"),
        ("MEMORYPLAYER_%", "MEMORYPLAYER Events (should also work)"),
    ]

    all_passed = True

    for pattern, label in checks:
        total, null_count = check_event_type_ownership(conn, pattern)

        if total == 0:
            print(f"⚠️  {label}: No events found (OK - may not exist in data)")
            continue

        valid_count = total - null_count
        percentage = (valid_count / total * 100) if total > 0 else 0

        if null_count == 0:
            print(f"✅ {label}: {total} events, ALL have player_id ({percentage:.1f}%)")
        else:
            print(
                f"❌ {label}: {total} events, {null_count} have NULL player_id ({percentage:.1f}% valid)"
            )
            all_passed = False

    print()
    print("=" * 60)

    if all_passed:
        print("✅ All validation checks passed!")
        print()
        print("Player ownership is correctly assigned for all MemoryData events.")
        return 0
    else:
        print("❌ Some validation checks failed!")
        print()
        print("Action required:")
        print("1. Check if parser fix is implemented correctly")
        print(
            "2. Re-import data: uv run python scripts/import_tournaments.py --directory saves --force"
        )
        print("3. Run this script again to verify")
        return 1


if __name__ == "__main__":
    sys.exit(main())
