"""Database migration: Add player statistics tables.

This migration adds support for:
- Technology progress (TechCount)
- Player statistics (YieldStockpile, BonusCount, LawClassChangeCount)
- Match metadata (game settings and configuration)

Version: 1.1.0
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tournament_visualizer.data.database import TournamentDatabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_if_migrated(db: TournamentDatabase) -> bool:
    """Check if this migration has already been applied.

    Args:
        db: Database instance

    Returns:
        True if migration already applied
    """
    result = db.fetch_one(
        "SELECT 1 FROM schema_migrations WHERE version = '1.1.0'"
    )
    return result is not None


def migrate_up(db: TournamentDatabase) -> None:
    """Apply the migration.

    Args:
        db: Database instance
    """
    logger.info("Starting migration 1.1.0: Add player statistics tables")

    with db.get_connection() as conn:
        # Create sequences
        logger.info("Creating sequences...")
        conn.execute("CREATE SEQUENCE IF NOT EXISTS technology_progress_id_seq START 1;")
        conn.execute("CREATE SEQUENCE IF NOT EXISTS player_statistics_id_seq START 1;")

        # Create technology_progress table
        logger.info("Creating technology_progress table...")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS technology_progress (
                tech_progress_id BIGINT PRIMARY KEY,
                match_id BIGINT NOT NULL,
                player_id BIGINT NOT NULL,
                tech_name VARCHAR NOT NULL,
                count INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (match_id) REFERENCES matches(match_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id),
                UNIQUE(match_id, player_id, tech_name)
            )
        """)

        # Create player_statistics table
        logger.info("Creating player_statistics table...")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS player_statistics (
                stat_id BIGINT PRIMARY KEY,
                match_id BIGINT NOT NULL,
                player_id BIGINT NOT NULL,
                stat_category VARCHAR NOT NULL,
                stat_name VARCHAR NOT NULL,
                value INTEGER NOT NULL,
                FOREIGN KEY (match_id) REFERENCES matches(match_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id),
                UNIQUE(match_id, player_id, stat_category, stat_name)
            )
        """)

        # Create match_metadata table
        logger.info("Creating match_metadata table...")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS match_metadata (
                match_id BIGINT PRIMARY KEY,
                difficulty VARCHAR,
                event_level VARCHAR,
                victory_type VARCHAR,
                victory_turn INTEGER,
                game_options JSON,
                dlc_content JSON,
                map_settings JSON,
                FOREIGN KEY (match_id) REFERENCES matches(match_id)
            )
        """)

        # Create indexes
        logger.info("Creating indexes...")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tech_progress_match ON technology_progress(match_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tech_progress_player ON technology_progress(player_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tech_progress_tech ON technology_progress(tech_name);")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_player_stats_match ON player_statistics(match_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_player_stats_player ON player_statistics(player_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_player_stats_category ON player_statistics(stat_category);")

        # Record migration
        logger.info("Recording migration...")
        conn.execute("""
            INSERT INTO schema_migrations (version, description, applied_at)
            VALUES ('1.1.0', 'Add player statistics tables (technology_progress, player_statistics, match_metadata)', CURRENT_TIMESTAMP)
        """)

    logger.info("Migration 1.1.0 completed successfully")


def migrate_down(db: TournamentDatabase) -> None:
    """Rollback the migration.

    Args:
        db: Database instance
    """
    logger.info("Rolling back migration 1.1.0...")

    with db.get_connection() as conn:
        # Drop tables in reverse order
        conn.execute("DROP TABLE IF EXISTS match_metadata;")
        conn.execute("DROP TABLE IF EXISTS player_statistics;")
        conn.execute("DROP TABLE IF EXISTS technology_progress;")

        # Drop sequences
        conn.execute("DROP SEQUENCE IF EXISTS player_statistics_id_seq;")
        conn.execute("DROP SEQUENCE IF EXISTS technology_progress_id_seq;")

        # Remove migration record
        conn.execute("DELETE FROM schema_migrations WHERE version = '1.1.0';")

    logger.info("Migration 1.1.0 rolled back successfully")


def main() -> None:
    """Main migration script entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Apply database migration 1.1.0')
    parser.add_argument('--rollback', action='store_true', help='Rollback the migration')
    parser.add_argument('--db', default='tournament_data.duckdb', help='Database file path')
    args = parser.parse_args()

    # Create database instance in write mode
    db = TournamentDatabase(db_path=args.db, read_only=False)

    try:
        if args.rollback:
            migrate_down(db)
        else:
            if check_if_migrated(db):
                logger.info("Migration 1.1.0 has already been applied. Skipping.")
                return
            migrate_up(db)
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        db.close()


if __name__ == '__main__':
    main()
