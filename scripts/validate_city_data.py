"""Validate city data quality in database.

This script checks:
- Data integrity (all cities have required fields)
- Referential integrity (FKs are valid)
- Business rules (player IDs, founded turns)
- Data quality (reasonable values)

Usage:
    uv run python scripts/validate_city_data.py
    uv run python scripts/validate_city_data.py --match 1
"""

import argparse
import logging
from typing import Dict, Any, List

import duckdb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "data/tournament_data.duckdb"


def validate_city_data(db_path: str = DEFAULT_DB_PATH, match_id: int | None = None) -> Dict[str, Any]:
    """Validate city data in database.

    Args:
        db_path: Path to DuckDB database
        match_id: Optional specific match to validate

    Returns:
        Dictionary with validation results
    """
    conn = duckdb.connect(db_path, read_only=True)

    results = {
        'errors': [],
        'warnings': [],
        'stats': {}
    }

    try:
        # Check 1: Tables exist
        logger.info("Checking tables exist...")
        tables = conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]

        required_tables = ['cities', 'city_unit_production', 'city_projects']
        for table in required_tables:
            if table not in table_names:
                results['errors'].append(f"Table '{table}' does not exist")

        if results['errors']:
            logger.error(f"Missing tables: {results['errors']}")
            return results

        # Check 2: Count records
        logger.info("Counting records...")
        where_clause = f"WHERE match_id = {match_id}" if match_id else ""

        city_count = conn.execute(f"SELECT COUNT(*) FROM cities {where_clause}").fetchone()[0]
        prod_count = conn.execute(f"SELECT COUNT(*) FROM city_unit_production {where_clause}").fetchone()[0]
        proj_count = conn.execute(f"SELECT COUNT(*) FROM city_projects {where_clause}").fetchone()[0]

        results['stats']['total_cities'] = city_count
        results['stats']['total_production_records'] = prod_count
        results['stats']['total_project_records'] = proj_count

        logger.info(f"  Cities: {city_count}")
        logger.info(f"  Production records: {prod_count}")
        logger.info(f"  Project records: {proj_count}")

        if city_count == 0:
            results['warnings'].append("No cities found in database")
            return results

        # Check 3: Required fields populated
        logger.info("Checking required fields...")
        null_checks = [
            ("cities", "city_name"),
            ("cities", "player_id"),
            ("cities", "founded_turn"),
            ("cities", "tile_id")
        ]

        for table, column in null_checks:
            where_condition = f"{where_clause} AND {column} IS NULL" if where_clause else f"WHERE {column} IS NULL"
            count = conn.execute(f"""
                SELECT COUNT(*) FROM {table} {where_condition}
            """).fetchone()[0]

            if count > 0:
                results['errors'].append(f"{count} rows in {table} have NULL {column}")

        # Check 4: Foreign key integrity
        logger.info("Checking foreign key integrity...")

        # Cities with invalid match_id
        and_clause = f"AND c.match_id = {match_id}" if match_id else ""
        invalid_match = conn.execute(f"""
            SELECT COUNT(*)
            FROM cities c
            WHERE NOT EXISTS (SELECT 1 FROM matches m WHERE m.match_id = c.match_id)
            {and_clause}
        """).fetchone()[0]

        if invalid_match > 0:
            results['errors'].append(f"{invalid_match} cities have invalid match_id")

        # Cities with invalid player_id
        invalid_player = conn.execute(f"""
            SELECT COUNT(*)
            FROM cities c
            WHERE NOT EXISTS (
                SELECT 1 FROM players p
                WHERE p.match_id = c.match_id AND p.player_id = c.player_id
            )
            {and_clause}
        """).fetchone()[0]

        if invalid_player > 0:
            results['errors'].append(f"{invalid_player} cities have invalid player_id")

        # Check 5: Business rules
        logger.info("Checking business rules...")

        # Player IDs should be >= 1 (database uses 1-based)
        where_condition = f"{where_clause} OR player_id < 1" if where_clause else "WHERE player_id < 1"
        invalid_ids = conn.execute(f"""
            SELECT COUNT(*)
            FROM cities
            {where_condition}
        """).fetchone()[0]

        if invalid_ids > 0:
            results['errors'].append(f"{invalid_ids} cities have invalid player_id < 1")

        # Founded turn should be >= 1
        where_condition = f"{where_clause} OR founded_turn < 1" if where_clause else "WHERE founded_turn < 1"
        invalid_turns = conn.execute(f"""
            SELECT COUNT(*)
            FROM cities
            {where_condition}
        """).fetchone()[0]

        if invalid_turns > 0:
            results['warnings'].append(f"{invalid_turns} cities have invalid founded_turn < 1")

        # Check 6: Data quality
        logger.info("Checking data quality...")

        # Check for duplicate (match_id, city_id)
        duplicates = conn.execute(f"""
            SELECT match_id, city_id, COUNT(*) as count
            FROM cities
            {where_clause}
            GROUP BY match_id, city_id
            HAVING COUNT(*) > 1
        """).fetchall()

        if duplicates:
            results['errors'].append(f"{len(duplicates)} duplicate (match_id, city_id) pairs")
            for dup in duplicates[:5]:  # Show first 5
                results['errors'].append(f"  - Match {dup[0]}, City {dup[1]}: {dup[2]} copies")

        # Check 7: Statistics
        logger.info("Gathering statistics...")

        # Average cities per match
        avg_cities = conn.execute(f"""
            SELECT AVG(city_count)
            FROM (
                SELECT match_id, COUNT(*) as city_count
                FROM cities
                {where_clause}
                GROUP BY match_id
            )
        """).fetchone()[0]

        results['stats']['avg_cities_per_match'] = round(avg_cities, 1) if avg_cities else 0

        # Cities by player
        cities_by_player = conn.execute(f"""
            SELECT p.player_name, COUNT(c.city_id) as city_count
            FROM cities c
            JOIN players p ON c.match_id = p.match_id AND c.player_id = p.player_id
            {where_clause}
            GROUP BY p.player_name
            ORDER BY city_count DESC
            LIMIT 5
        """).fetchall()

        results['stats']['top_expanders'] = [
            {'player': row[0], 'cities': row[1]}
            for row in cities_by_player
        ]

    finally:
        conn.close()

    return results


def print_results(results: Dict[str, Any]) -> None:
    """Print validation results.

    Args:
        results: Validation results dictionary
    """
    print("\n" + "=" * 60)
    print("CITY DATA VALIDATION RESULTS")
    print("=" * 60)

    # Errors
    if results['errors']:
        print(f"\n❌ ERRORS ({len(results['errors'])})")
        for error in results['errors']:
            print(f"  - {error}")
    else:
        print("\n✅ No errors found")

    # Warnings
    if results['warnings']:
        print(f"\n⚠️  WARNINGS ({len(results['warnings'])})")
        for warning in results['warnings']:
            print(f"  - {warning}")

    # Statistics
    if results['stats']:
        print("\n📊 STATISTICS")
        stats = results['stats']
        print(f"  Total cities: {stats.get('total_cities', 0)}")
        print(f"  Production records: {stats.get('total_production_records', 0)}")
        print(f"  Project records: {stats.get('total_project_records', 0)}")
        print(f"  Avg cities per match: {stats.get('avg_cities_per_match', 0)}")

        if 'top_expanders' in stats and stats['top_expanders']:
            print("\n  Top 5 Expanders:")
            for player in stats['top_expanders']:
                print(f"    - {player['player']}: {player['cities']} cities")

    print("=" * 60 + "\n")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate city data quality in database"
    )
    parser.add_argument(
        '--db',
        default=DEFAULT_DB_PATH,
        help='Path to database (default: data/tournament_data.duckdb)'
    )
    parser.add_argument(
        '--match',
        type=int,
        help='Validate specific match only'
    )

    args = parser.parse_args()

    results = validate_city_data(db_path=args.db, match_id=args.match)
    print_results(results)

    # Exit code based on errors
    if results['errors']:
        exit(1)
    else:
        exit(0)


if __name__ == '__main__':
    main()
