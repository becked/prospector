"""Migration 002: Add turn-by-turn history tables.

This migration:
1. Drops the broken game_state table (all rows have turn_number=0)
2. Renames resources table to player_yield_history
3. Creates new history tables for points, military, legitimacy, opinions

Rollback: See docs/migrations/002_add_history_tables.md
"""

import duckdb
from pathlib import Path
from typing import Optional


def migrate(db_path: Path, backup: bool = True) -> None:
    """Run migration to add history tables.

    Args:
        db_path: Path to the DuckDB database file
        backup: If True, create a backup before migrating
    """
    if backup:
        backup_path = db_path.with_suffix(f".duckdb.backup_002")
        print(f"Creating backup: {backup_path}")
        import shutil
        shutil.copy2(db_path, backup_path)

    print(f"Migrating database: {db_path}")
    conn = duckdb.connect(str(db_path))

    try:
        # 1. Drop broken game_state table
        print("  - Dropping game_state table...")
        conn.execute("DROP TABLE IF EXISTS game_state")

        # 2. Rename resources to player_yield_history
        print("  - Renaming resources to player_yield_history...")
        # Check if table exists and is empty before renaming
        count = conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
        if count > 0:
            print(f"    WARNING: resources table has {count} rows! Skipping rename.")
        else:
            # Drop existing indexes first
            print("    - Dropping existing indexes...")
            conn.execute("DROP INDEX IF EXISTS idx_resources_match_player")
            conn.execute("DROP INDEX IF EXISTS idx_resources_match_turn_type")
            conn.execute("DROP INDEX IF EXISTS idx_resources_turn")
            conn.execute("DROP INDEX IF EXISTS idx_resources_type")
            # Now rename the table
            conn.execute("ALTER TABLE resources RENAME TO player_yield_history")
            # Recreate indexes with new table name
            print("    - Creating indexes on player_yield_history...")
            conn.execute("CREATE INDEX idx_yield_history_match_player ON player_yield_history(match_id, player_id)")
            conn.execute("CREATE INDEX idx_yield_history_match_turn_type ON player_yield_history(match_id, turn_number, resource_type)")
            conn.execute("CREATE INDEX idx_yield_history_turn ON player_yield_history(turn_number)")
            conn.execute("CREATE INDEX idx_yield_history_type ON player_yield_history(resource_type)")

        # 2.5. Create sequences for new tables
        print("  - Creating sequences for new tables...")
        conn.execute("CREATE SEQUENCE IF NOT EXISTS points_history_id_seq START 1")
        conn.execute("CREATE SEQUENCE IF NOT EXISTS military_history_id_seq START 1")
        conn.execute("CREATE SEQUENCE IF NOT EXISTS legitimacy_history_id_seq START 1")
        conn.execute("CREATE SEQUENCE IF NOT EXISTS family_opinion_id_seq START 1")
        conn.execute("CREATE SEQUENCE IF NOT EXISTS religion_opinion_id_seq START 1")

        # 3. Create player_points_history table
        print("  - Creating player_points_history table...")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS player_points_history (
                points_history_id BIGINT PRIMARY KEY,
                match_id BIGINT NOT NULL,
                player_id BIGINT NOT NULL,
                turn_number INTEGER NOT NULL,
                points INTEGER NOT NULL,
                FOREIGN KEY (match_id) REFERENCES matches(match_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id),
                CHECK (turn_number >= 0),
                CHECK (points >= 0),
                UNIQUE (match_id, player_id, turn_number)
            )
        """)
        conn.execute("""
            CREATE INDEX idx_points_history_match_player
            ON player_points_history(match_id, player_id)
        """)
        conn.execute("""
            CREATE INDEX idx_points_history_turn
            ON player_points_history(turn_number)
        """)

        # 4. Create player_military_history table
        print("  - Creating player_military_history table...")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS player_military_history (
                military_history_id BIGINT PRIMARY KEY,
                match_id BIGINT NOT NULL,
                player_id BIGINT NOT NULL,
                turn_number INTEGER NOT NULL,
                military_power INTEGER NOT NULL,
                FOREIGN KEY (match_id) REFERENCES matches(match_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id),
                CHECK (turn_number >= 0),
                CHECK (military_power >= 0),
                UNIQUE (match_id, player_id, turn_number)
            )
        """)
        conn.execute("""
            CREATE INDEX idx_military_history_match_player
            ON player_military_history(match_id, player_id)
        """)
        conn.execute("""
            CREATE INDEX idx_military_history_turn
            ON player_military_history(turn_number)
        """)

        # 5. Create player_legitimacy_history table
        print("  - Creating player_legitimacy_history table...")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS player_legitimacy_history (
                legitimacy_history_id BIGINT PRIMARY KEY,
                match_id BIGINT NOT NULL,
                player_id BIGINT NOT NULL,
                turn_number INTEGER NOT NULL,
                legitimacy INTEGER NOT NULL,
                FOREIGN KEY (match_id) REFERENCES matches(match_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id),
                CHECK (turn_number >= 0),
                CHECK (legitimacy >= 0),
                UNIQUE (match_id, player_id, turn_number)
            )
        """)
        conn.execute("""
            CREATE INDEX idx_legitimacy_history_match_player
            ON player_legitimacy_history(match_id, player_id)
        """)
        conn.execute("""
            CREATE INDEX idx_legitimacy_history_turn
            ON player_legitimacy_history(turn_number)
        """)

        # 6. Create family_opinion_history table
        print("  - Creating family_opinion_history table...")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS family_opinion_history (
                family_opinion_id BIGINT PRIMARY KEY,
                match_id BIGINT NOT NULL,
                player_id BIGINT NOT NULL,
                turn_number INTEGER NOT NULL,
                family_name VARCHAR NOT NULL,
                opinion INTEGER NOT NULL,
                FOREIGN KEY (match_id) REFERENCES matches(match_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id),
                CHECK (turn_number >= 0),
                UNIQUE (match_id, player_id, turn_number, family_name)
            )
        """)
        conn.execute("""
            CREATE INDEX idx_family_opinion_match_player
            ON family_opinion_history(match_id, player_id)
        """)
        conn.execute("""
            CREATE INDEX idx_family_opinion_family
            ON family_opinion_history(family_name)
        """)

        # 7. Create religion_opinion_history table
        print("  - Creating religion_opinion_history table...")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS religion_opinion_history (
                religion_opinion_id BIGINT PRIMARY KEY,
                match_id BIGINT NOT NULL,
                player_id BIGINT NOT NULL,
                turn_number INTEGER NOT NULL,
                religion_name VARCHAR NOT NULL,
                opinion INTEGER NOT NULL,
                FOREIGN KEY (match_id) REFERENCES matches(match_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id),
                CHECK (turn_number >= 0),
                UNIQUE (match_id, player_id, turn_number, religion_name)
            )
        """)
        conn.execute("""
            CREATE INDEX idx_religion_opinion_match_player
            ON religion_opinion_history(match_id, player_id)
        """)
        conn.execute("""
            CREATE INDEX idx_religion_opinion_religion
            ON religion_opinion_history(religion_name)
        """)

        conn.commit()
        print("Migration completed successfully!")

    except Exception as e:
        print(f"Migration failed: {e}")
        # Don't call rollback as DuckDB uses auto-commit by default
        raise
    finally:
        conn.close()


def rollback(db_path: Path) -> None:
    """Rollback migration by restoring from backup.

    Args:
        db_path: Path to the DuckDB database file
    """
    backup_path = db_path.with_suffix(".duckdb.backup_002")
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found: {backup_path}")

    print(f"Rolling back by restoring from: {backup_path}")
    import shutil
    shutil.copy2(backup_path, db_path)
    print("Rollback completed!")


if __name__ == "__main__":
    import sys

    db_path = Path("data/tournament_data.duckdb")

    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        rollback(db_path)
    else:
        migrate(db_path, backup=True)
