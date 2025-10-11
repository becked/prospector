"""Validate turn-by-turn history data integrity.

This script validates the data loaded into the new history tables:
- player_yield_history
- player_points_history
- player_military_history
- player_legitimacy_history
- family_opinion_history
- religion_opinion_history
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple

import duckdb


def connect_db(db_path: str = "data/tournament_data.duckdb") -> duckdb.DuckDBPyConnection:
    """Connect to the database in read-only mode."""
    return duckdb.connect(db_path, read_only=True)


def check_record_counts(conn: duckdb.DuckDBPyConnection) -> Dict[str, int]:
    """Check record counts for all history tables."""
    tables = [
        "player_yield_history",
        "player_points_history",
        "player_military_history",
        "player_legitimacy_history",
        "family_opinion_history",
        "religion_opinion_history",
    ]

    counts = {}
    for table in tables:
        result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        counts[table] = result[0]

    return counts


def check_foreign_key_integrity(conn: duckdb.DuckDBPyConnection) -> List[str]:
    """Check that all foreign keys reference valid records."""
    issues = []

    # Check player_yield_history
    result = conn.execute("""
        SELECT COUNT(*) FROM player_yield_history yh
        LEFT JOIN matches m ON yh.match_id = m.match_id
        WHERE m.match_id IS NULL
    """).fetchone()[0]
    if result > 0:
        issues.append(f"player_yield_history: {result} orphaned match_id records")

    result = conn.execute("""
        SELECT COUNT(*) FROM player_yield_history yh
        LEFT JOIN players p ON yh.player_id = p.player_id
        WHERE p.player_id IS NULL
    """).fetchone()[0]
    if result > 0:
        issues.append(f"player_yield_history: {result} orphaned player_id records")

    # Check player_points_history
    result = conn.execute("""
        SELECT COUNT(*) FROM player_points_history ph
        LEFT JOIN matches m ON ph.match_id = m.match_id
        WHERE m.match_id IS NULL
    """).fetchone()[0]
    if result > 0:
        issues.append(f"player_points_history: {result} orphaned match_id records")

    result = conn.execute("""
        SELECT COUNT(*) FROM player_points_history ph
        LEFT JOIN players p ON ph.player_id = p.player_id
        WHERE p.player_id IS NULL
    """).fetchone()[0]
    if result > 0:
        issues.append(f"player_points_history: {result} orphaned player_id records")

    # Check player_military_history
    result = conn.execute("""
        SELECT COUNT(*) FROM player_military_history mh
        LEFT JOIN matches m ON mh.match_id = m.match_id
        WHERE m.match_id IS NULL
    """).fetchone()[0]
    if result > 0:
        issues.append(f"player_military_history: {result} orphaned match_id records")

    # Check player_legitimacy_history
    result = conn.execute("""
        SELECT COUNT(*) FROM player_legitimacy_history lh
        LEFT JOIN matches m ON lh.match_id = m.match_id
        WHERE m.match_id IS NULL
    """).fetchone()[0]
    if result > 0:
        issues.append(f"player_legitimacy_history: {result} orphaned match_id records")

    # Check family_opinion_history
    result = conn.execute("""
        SELECT COUNT(*) FROM family_opinion_history fh
        LEFT JOIN matches m ON fh.match_id = m.match_id
        WHERE m.match_id IS NULL
    """).fetchone()[0]
    if result > 0:
        issues.append(f"family_opinion_history: {result} orphaned match_id records")

    # Check religion_opinion_history
    result = conn.execute("""
        SELECT COUNT(*) FROM religion_opinion_history rh
        LEFT JOIN matches m ON rh.match_id = m.match_id
        WHERE m.match_id IS NULL
    """).fetchone()[0]
    if result > 0:
        issues.append(f"religion_opinion_history: {result} orphaned match_id records")

    return issues


def check_data_quality(conn: duckdb.DuckDBPyConnection) -> List[str]:
    """Check for data quality issues."""
    issues = []

    # Check for NULL values where not expected
    tables_and_columns = [
        ("player_yield_history", ["match_id", "player_id", "turn_number", "resource_type", "amount"]),
        ("player_points_history", ["match_id", "player_id", "turn_number", "points"]),
        ("player_military_history", ["match_id", "player_id", "turn_number", "military_power"]),
        ("player_legitimacy_history", ["match_id", "player_id", "turn_number", "legitimacy"]),
        ("family_opinion_history", ["match_id", "player_id", "turn_number", "family_name", "opinion"]),
        ("religion_opinion_history", ["match_id", "player_id", "turn_number", "religion_name", "opinion"]),
    ]

    for table, columns in tables_and_columns:
        for column in columns:
            result = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL").fetchone()[0]
            if result > 0:
                issues.append(f"{table}.{column}: {result} NULL values found")

    # Check for negative turn numbers
    for table in ["player_yield_history", "player_points_history", "player_military_history",
                  "player_legitimacy_history", "family_opinion_history", "religion_opinion_history"]:
        result = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE turn_number < 0").fetchone()[0]
        if result > 0:
            issues.append(f"{table}: {result} records with negative turn_number")

    # Check for negative points (should not happen)
    result = conn.execute("SELECT COUNT(*) FROM player_points_history WHERE points < 0").fetchone()[0]
    if result > 0:
        issues.append(f"player_points_history: {result} records with negative points")

    # Check for negative military power (should not happen)
    result = conn.execute("SELECT COUNT(*) FROM player_military_history WHERE military_power < 0").fetchone()[0]
    if result > 0:
        issues.append(f"player_military_history: {result} records with negative military_power")

    # Check for negative legitimacy (should not happen)
    result = conn.execute("SELECT COUNT(*) FROM player_legitimacy_history WHERE legitimacy < 0").fetchone()[0]
    if result > 0:
        issues.append(f"player_legitimacy_history: {result} records with negative legitimacy")

    return issues


def check_turn_consistency(conn: duckdb.DuckDBPyConnection) -> List[str]:
    """Check for turn-by-turn consistency across history tables."""
    issues = []

    # Check that points, military, and legitimacy have same turn coverage
    result = conn.execute("""
        SELECT COUNT(*) FROM (
            SELECT match_id, player_id, turn_number FROM player_points_history
            EXCEPT
            SELECT match_id, player_id, turn_number FROM player_military_history
        )
    """).fetchone()[0]
    if result > 0:
        issues.append(f"Turn mismatch: {result} records in points_history not in military_history")

    result = conn.execute("""
        SELECT COUNT(*) FROM (
            SELECT match_id, player_id, turn_number FROM player_points_history
            EXCEPT
            SELECT match_id, player_id, turn_number FROM player_legitimacy_history
        )
    """).fetchone()[0]
    if result > 0:
        issues.append(f"Turn mismatch: {result} records in points_history not in legitimacy_history")

    return issues


def get_summary_statistics(conn: duckdb.DuckDBPyConnection) -> Dict[str, Dict[str, any]]:
    """Get summary statistics for each history table."""
    stats = {}

    # Yield history
    result = conn.execute("""
        SELECT
            COUNT(DISTINCT match_id) as match_count,
            COUNT(DISTINCT player_id) as player_count,
            MIN(turn_number) as min_turn,
            MAX(turn_number) as max_turn,
            COUNT(DISTINCT resource_type) as resource_type_count,
            MIN(amount) as min_amount,
            MAX(amount) as max_amount
        FROM player_yield_history
    """).fetchone()
    stats["player_yield_history"] = {
        "matches": result[0],
        "players": result[1],
        "turn_range": f"{result[2]}-{result[3]}",
        "resource_types": result[4],
        "amount_range": f"{result[5]} to {result[6]}",
    }

    # Points history
    result = conn.execute("""
        SELECT
            COUNT(DISTINCT match_id) as match_count,
            COUNT(DISTINCT player_id) as player_count,
            MIN(turn_number) as min_turn,
            MAX(turn_number) as max_turn,
            MIN(points) as min_points,
            MAX(points) as max_points,
            AVG(points) as avg_points
        FROM player_points_history
    """).fetchone()
    stats["player_points_history"] = {
        "matches": result[0],
        "players": result[1],
        "turn_range": f"{result[2]}-{result[3]}",
        "points_range": f"{result[4]} to {result[5]}",
        "avg_points": round(result[6], 2),
    }

    # Military history
    result = conn.execute("""
        SELECT
            COUNT(DISTINCT match_id) as match_count,
            COUNT(DISTINCT player_id) as player_count,
            MIN(military_power) as min_mil,
            MAX(military_power) as max_mil,
            AVG(military_power) as avg_mil
        FROM player_military_history
    """).fetchone()
    stats["player_military_history"] = {
        "matches": result[0],
        "players": result[1],
        "military_range": f"{result[2]} to {result[3]}",
        "avg_military": round(result[4], 2),
    }

    # Legitimacy history
    result = conn.execute("""
        SELECT
            COUNT(DISTINCT match_id) as match_count,
            COUNT(DISTINCT player_id) as player_count,
            MIN(legitimacy) as min_leg,
            MAX(legitimacy) as max_leg,
            AVG(legitimacy) as avg_leg
        FROM player_legitimacy_history
    """).fetchone()
    stats["player_legitimacy_history"] = {
        "matches": result[0],
        "players": result[1],
        "legitimacy_range": f"{result[2]} to {result[3]}",
        "avg_legitimacy": round(result[4], 2),
    }

    # Family opinion history
    result = conn.execute("""
        SELECT
            COUNT(DISTINCT match_id) as match_count,
            COUNT(DISTINCT player_id) as player_count,
            COUNT(DISTINCT family_name) as family_count,
            MIN(opinion) as min_opinion,
            MAX(opinion) as max_opinion
        FROM family_opinion_history
    """).fetchone()
    stats["family_opinion_history"] = {
        "matches": result[0],
        "players": result[1],
        "families": result[2],
        "opinion_range": f"{result[3]} to {result[4]}",
    }

    # Religion opinion history
    result = conn.execute("""
        SELECT
            COUNT(DISTINCT match_id) as match_count,
            COUNT(DISTINCT player_id) as player_count,
            COUNT(DISTINCT religion_name) as religion_count,
            MIN(opinion) as min_opinion,
            MAX(opinion) as max_opinion
        FROM religion_opinion_history
    """).fetchone()
    stats["religion_opinion_history"] = {
        "matches": result[0],
        "players": result[1],
        "religions": result[2],
        "opinion_range": f"{result[3]} to {result[4]}",
    }

    return stats


def main() -> int:
    """Run all validation checks and print report."""
    db_path = Path("data/tournament_data.duckdb")
    if not db_path.exists():
        print(f"ERROR: Database not found at {db_path}")
        return 1

    print("=" * 80)
    print("TURN-BY-TURN HISTORY DATA VALIDATION REPORT")
    print("=" * 80)
    print()

    conn = connect_db(str(db_path))

    # Record counts
    print("1. RECORD COUNTS")
    print("-" * 80)
    counts = check_record_counts(conn)
    total_records = 0
    for table, count in sorted(counts.items()):
        print(f"  {table:35s} {count:>10,} records")
        total_records += count
    print(f"  {'TOTAL':35s} {total_records:>10,} records")
    print()

    # Foreign key integrity
    print("2. FOREIGN KEY INTEGRITY")
    print("-" * 80)
    fk_issues = check_foreign_key_integrity(conn)
    if fk_issues:
        for issue in fk_issues:
            print(f"  ❌ {issue}")
    else:
        print("  ✓ All foreign keys are valid")
    print()

    # Data quality
    print("3. DATA QUALITY")
    print("-" * 80)
    dq_issues = check_data_quality(conn)
    if dq_issues:
        for issue in dq_issues:
            print(f"  ❌ {issue}")
    else:
        print("  ✓ No data quality issues found")
    print()

    # Turn consistency
    print("4. TURN CONSISTENCY")
    print("-" * 80)
    turn_issues = check_turn_consistency(conn)
    if turn_issues:
        for issue in turn_issues:
            print(f"  ❌ {issue}")
    else:
        print("  ✓ Turn-by-turn data is consistent across tables")
    print()

    # Summary statistics
    print("5. SUMMARY STATISTICS")
    print("-" * 80)
    stats = get_summary_statistics(conn)
    for table, table_stats in sorted(stats.items()):
        print(f"  {table}:")
        for key, value in table_stats.items():
            print(f"    {key:20s} {value}")
        print()

    # Overall result
    print("=" * 80)
    all_issues = fk_issues + dq_issues + turn_issues
    if all_issues:
        print(f"VALIDATION FAILED: {len(all_issues)} issues found")
        return 1
    else:
        print("VALIDATION PASSED: All checks successful!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
