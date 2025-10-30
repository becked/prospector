"""Migration 004: Add city tables for tracking city data.

This migration adds support for tracking cities, unit production, and projects.

Usage:
    # Apply migration
    uv run python scripts/migrate_add_city_tables.py

    # Rollback migration
    uv run python scripts/migrate_add_city_tables.py --rollback

    # Verify migration
    uv run python scripts/migrate_add_city_tables.py --verify

See: docs/migrations/004_add_city_tables.md
"""

import argparse
import logging
from pathlib import Path

import duckdb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "data/tournament_data.duckdb"


def migrate_up(db_path: str = DEFAULT_DB_PATH) -> None:
    """Apply migration: Create city tables.

    Args:
        db_path: Path to DuckDB database
    """
    logger.info(f"Applying migration 004 to {db_path}")

    conn = duckdb.connect(db_path)

    try:
        # Create sequences for auto-increment IDs
        conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS city_unit_production_id_seq
        """)
        conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS city_projects_id_seq
        """)
        logger.info("✓ Created sequences for auto-increment IDs")

        # Create cities table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cities (
                city_id INTEGER NOT NULL,
                match_id BIGINT NOT NULL,
                player_id BIGINT NOT NULL,
                city_name VARCHAR NOT NULL,
                tile_id INTEGER NOT NULL,
                founded_turn INTEGER NOT NULL,
                family_name VARCHAR,
                is_capital BOOLEAN DEFAULT FALSE,
                population INTEGER,
                first_player_id BIGINT,
                governor_id INTEGER,
                PRIMARY KEY (match_id, city_id)
            )
        """)
        logger.info("✓ Created cities table")

        # Create indexes for cities
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cities_match_id
            ON cities(match_id)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cities_player_id
            ON cities(match_id, player_id)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cities_founded_turn
            ON cities(match_id, founded_turn)
        """)
        logger.info("✓ Created indexes for cities")

        # Create city_unit_production table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS city_unit_production (
                production_id INTEGER PRIMARY KEY DEFAULT nextval('city_unit_production_id_seq'),
                match_id BIGINT NOT NULL,
                city_id INTEGER NOT NULL,
                unit_type VARCHAR NOT NULL,
                count INTEGER NOT NULL
            )
        """)
        logger.info("✓ Created city_unit_production table")

        # Create indexes for production
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_city_production_match_city
            ON city_unit_production(match_id, city_id)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_city_production_unit_type
            ON city_unit_production(unit_type)
        """)
        logger.info("✓ Created indexes for city_unit_production")

        # Create city_projects table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS city_projects (
                project_id INTEGER PRIMARY KEY DEFAULT nextval('city_projects_id_seq'),
                match_id BIGINT NOT NULL,
                city_id INTEGER NOT NULL,
                project_type VARCHAR NOT NULL,
                count INTEGER NOT NULL
            )
        """)
        logger.info("✓ Created city_projects table")

        # Create indexes for projects
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_city_projects_match_city
            ON city_projects(match_id, city_id)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_city_projects_type
            ON city_projects(project_type)
        """)
        logger.info("✓ Created indexes for city_projects")

        logger.info("✓ Migration 004 applied successfully")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        conn.close()


def migrate_down(db_path: str = DEFAULT_DB_PATH) -> None:
    """Rollback migration: Drop city tables.

    Args:
        db_path: Path to DuckDB database
    """
    logger.info(f"Rolling back migration 004 from {db_path}")

    conn = duckdb.connect(db_path)

    try:
        # Drop tables in reverse order (respect FKs)
        conn.execute("DROP TABLE IF EXISTS city_projects")
        logger.info("✓ Dropped city_projects table")

        conn.execute("DROP TABLE IF EXISTS city_unit_production")
        logger.info("✓ Dropped city_unit_production table")

        conn.execute("DROP TABLE IF EXISTS cities")
        logger.info("✓ Dropped cities table")

        # Drop sequences
        conn.execute("DROP SEQUENCE IF EXISTS city_projects_id_seq")
        conn.execute("DROP SEQUENCE IF EXISTS city_unit_production_id_seq")
        logger.info("✓ Dropped sequences")

        logger.info("✓ Migration 004 rolled back successfully")

    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        raise
    finally:
        conn.close()


def verify_migration(db_path: str = DEFAULT_DB_PATH) -> None:
    """Verify migration was applied correctly.

    Args:
        db_path: Path to DuckDB database
    """
    conn = duckdb.connect(db_path, read_only=True)

    try:
        # Check tables exist
        tables = conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]

        required_tables = ['cities', 'city_unit_production', 'city_projects']

        for table in required_tables:
            if table in table_names:
                logger.info(f"✓ Table '{table}' exists")

                # Check columns for cities table
                if table == 'cities':
                    columns = conn.execute(f"DESCRIBE {table}").fetchall()
                    column_names = [col[0] for col in columns]

                    expected_columns = [
                        'city_id', 'match_id', 'player_id', 'city_name',
                        'tile_id', 'founded_turn', 'family_name', 'is_capital',
                        'population', 'first_player_id', 'governor_id'
                    ]

                    for col in expected_columns:
                        if col in column_names:
                            logger.info(f"  ✓ Column '{col}' exists")
                        else:
                            logger.error(f"  ✗ Column '{col}' missing")
            else:
                logger.error(f"✗ Table '{table}' does not exist")

    finally:
        conn.close()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Apply or rollback migration 004 (city tables)"
    )
    parser.add_argument(
        '--rollback',
        action='store_true',
        help='Rollback the migration'
    )
    parser.add_argument(
        '--db',
        default=DEFAULT_DB_PATH,
        help='Path to database (default: data/tournament_data.duckdb)'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify migration was applied'
    )

    args = parser.parse_args()

    if args.verify:
        verify_migration(args.db)
    elif args.rollback:
        migrate_down(args.db)
    else:
        migrate_up(args.db)


if __name__ == '__main__':
    main()
