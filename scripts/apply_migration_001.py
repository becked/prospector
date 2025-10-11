#!/usr/bin/env python3
"""Apply migration 001: Add LogData events support.

This script adds the idx_events_type_player index to optimize
law and tech progression queries.

Usage:
    uv run python scripts/apply_migration_001.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tournament_visualizer.data.database import TournamentDatabase


def apply_migration() -> bool:
    """Apply migration 001 to add indexes for LogData events.

    Returns:
        True if successful, False otherwise
    """
    print("Applying migration 001: Add LogData events support")
    print("=" * 60)

    # Open database in write mode
    db = TournamentDatabase(db_path="data/tournament_data.duckdb", read_only=False)

    try:
        # Connect to database
        conn = db.connect()

        # Check if index already exists
        print("\nChecking for existing indexes...")
        existing_indexes = conn.execute(
            """
            SELECT index_name
            FROM duckdb_indexes()
            WHERE table_name = 'events'
            AND index_name = 'idx_events_type_player'
        """
        ).fetchall()

        if existing_indexes:
            print("✓ Index idx_events_type_player already exists")
            return True

        # Create the new index
        print("\nCreating index idx_events_type_player...")
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_events_type_player
            ON events(event_type, player_id, turn_number)
        """
        )
        print("✓ Index created successfully")

        # Verify index was created
        print("\nVerifying index creation...")
        indexes = conn.execute(
            """
            SELECT index_name, sql
            FROM duckdb_indexes()
            WHERE table_name = 'events'
            ORDER BY index_name
        """
        ).fetchall()

        print("\nCurrent indexes on events table:")
        for index_name, sql in indexes:
            print(f"  - {index_name}")

        # Mark migration as applied
        print("\nMarking migration as applied...")
        conn.execute(
            """
            INSERT OR IGNORE INTO schema_migrations (version, description)
            VALUES ('1.1.0', 'Add LogData events support and indexes')
        """
        )
        print("✓ Migration marked as applied")

        print("\n" + "=" * 60)
        print("Migration 001 applied successfully!")
        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        return False

    finally:
        db.close()


def main() -> None:
    """Main entry point."""
    success = apply_migration()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
