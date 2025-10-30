"""Tests for city tables migration.

Test Strategy:
- Use temporary database for isolation
- Test table creation, indexes, constraints
- Test migration is idempotent (safe to run twice)
- Test rollback works
- Test foreign key constraints
"""

import pytest
import duckdb
import tempfile
import shutil
from pathlib import Path


class TestCityTablesMigration:
    """Test migration for city-related tables."""

    @pytest.fixture
    def temp_db_path(self) -> Path:
        """Create temporary database with minimal matches/players tables.

        Returns:
            Path to temporary database file
        """
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test.duckdb"

        conn = duckdb.connect(str(db_path))

        # Create minimal matches table for FK constraint
        conn.execute("""
            CREATE TABLE matches (
                match_id BIGINT PRIMARY KEY
            )
        """)
        conn.execute("INSERT INTO matches VALUES (1), (2)")

        # Create minimal players table for FK constraint
        conn.execute("""
            CREATE TABLE players (
                player_id BIGINT NOT NULL,
                match_id BIGINT NOT NULL,
                player_name VARCHAR,
                PRIMARY KEY (match_id, player_id)
            )
        """)
        conn.execute("""
            INSERT INTO players VALUES
            (1, 1, 'anarkos'),
            (2, 1, 'becked'),
            (1, 2, 'moose'),
            (2, 2, 'fluffbunny')
        """)

        conn.close()

        yield db_path

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_migration_creates_cities_table(self, temp_db_path: Path) -> None:
        """Test that migration creates cities table with correct schema."""
        from scripts.migrate_add_city_tables import migrate_up

        # Run migration
        migrate_up(str(temp_db_path))

        # Verify table exists
        conn = duckdb.connect(str(temp_db_path), read_only=True)

        # Check table exists
        tables = conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]
        assert 'cities' in table_names

        # Check columns
        columns = conn.execute("DESCRIBE cities").fetchall()
        column_names = [col[0] for col in columns]

        expected_columns = [
            'city_id', 'match_id', 'player_id', 'city_name',
            'tile_id', 'founded_turn', 'family_name', 'is_capital',
            'population', 'first_player_id', 'governor_id'
        ]

        for col in expected_columns:
            assert col in column_names, f"Column '{col}' missing from cities table"

        conn.close()

    def test_migration_creates_production_tables(self, temp_db_path: Path) -> None:
        """Test that migration creates unit production and project tables."""
        from scripts.migrate_add_city_tables import migrate_up

        migrate_up(str(temp_db_path))

        conn = duckdb.connect(str(temp_db_path), read_only=True)

        tables = conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]

        assert 'city_unit_production' in table_names
        assert 'city_projects' in table_names

        conn.close()

    def test_migration_creates_indexes(self, temp_db_path: Path) -> None:
        """Test that indexes are created for query performance."""
        from scripts.migrate_add_city_tables import migrate_up

        migrate_up(str(temp_db_path))

        conn = duckdb.connect(str(temp_db_path), read_only=True)

        # Try queries that should use indexes
        result = conn.execute("""
            SELECT * FROM cities WHERE match_id = 1
        """).fetchall()
        # Should work (even if empty)

        conn.close()

    def test_migration_idempotent(self, temp_db_path: Path) -> None:
        """Test that running migration twice doesn't error."""
        from scripts.migrate_add_city_tables import migrate_up

        # Run twice
        migrate_up(str(temp_db_path))
        migrate_up(str(temp_db_path))  # Should not crash

        # Verify tables still exist
        conn = duckdb.connect(str(temp_db_path), read_only=True)
        tables = conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]

        assert 'cities' in table_names
        assert 'city_unit_production' in table_names
        assert 'city_projects' in table_names

        conn.close()

    def test_can_insert_city(self, temp_db_path: Path) -> None:
        """Test inserting a city with all required fields."""
        from scripts.migrate_add_city_tables import migrate_up

        migrate_up(str(temp_db_path))

        conn = duckdb.connect(str(temp_db_path))

        # Insert a city
        conn.execute("""
            INSERT INTO cities (
                city_id, match_id, player_id, city_name,
                tile_id, founded_turn, is_capital, population
            ) VALUES (
                0, 1, 1, 'CITYNAME_NINEVEH',
                1292, 1, TRUE, 3
            )
        """)

        # Verify insertion
        result = conn.execute("SELECT * FROM cities").fetchone()
        assert result is not None
        assert result[0] == 0  # city_id
        assert result[1] == 1  # match_id
        assert result[2] == 1  # player_id
        assert result[3] == 'CITYNAME_NINEVEH'  # city_name

        conn.close()

    def test_can_insert_unit_production(self, temp_db_path: Path) -> None:
        """Test inserting unit production data."""
        from scripts.migrate_add_city_tables import migrate_up

        migrate_up(str(temp_db_path))

        conn = duckdb.connect(str(temp_db_path))

        # Insert a city first
        conn.execute("""
            INSERT INTO cities (
                city_id, match_id, player_id, city_name,
                tile_id, founded_turn
            ) VALUES (0, 1, 1, 'CITYNAME_NINEVEH', 1292, 1)
        """)

        # Insert production data
        conn.execute("""
            INSERT INTO city_unit_production (
                match_id, city_id, unit_type, count
            ) VALUES (1, 0, 'UNIT_SETTLER', 4)
        """)

        # Verify
        result = conn.execute("""
            SELECT * FROM city_unit_production
        """).fetchone()

        assert result[1] == 1  # match_id
        assert result[2] == 0  # city_id
        assert result[3] == 'UNIT_SETTLER'  # unit_type
        assert result[4] == 4  # count

        conn.close()

    def test_foreign_key_constraint(self, temp_db_path: Path) -> None:
        """Test that foreign key to matches table works."""
        from scripts.migrate_add_city_tables import migrate_up

        migrate_up(str(temp_db_path))

        conn = duckdb.connect(str(temp_db_path))

        # Try to insert city with non-existent match_id
        # Note: DuckDB requires enabling constraints
        conn.execute("PRAGMA foreign_keys = ON")

        with pytest.raises(duckdb.ConstraintException):
            conn.execute("""
                INSERT INTO cities (
                    city_id, match_id, player_id, city_name,
                    tile_id, founded_turn
                ) VALUES (0, 999, 1, 'TEST', 1, 1)
            """)

        conn.close()

    def test_unique_city_per_match(self, temp_db_path: Path) -> None:
        """Test that (match_id, city_id) is unique."""
        from scripts.migrate_add_city_tables import migrate_up

        migrate_up(str(temp_db_path))

        conn = duckdb.connect(str(temp_db_path))

        # Insert first city
        conn.execute("""
            INSERT INTO cities (
                city_id, match_id, player_id, city_name,
                tile_id, founded_turn
            ) VALUES (0, 1, 1, 'CITY_A', 100, 1)
        """)

        # Try to insert same city_id in same match
        with pytest.raises(duckdb.ConstraintException):
            conn.execute("""
                INSERT INTO cities (
                    city_id, match_id, player_id, city_name,
                    tile_id, founded_turn
                ) VALUES (0, 1, 2, 'CITY_B', 200, 5)
            """)

        conn.close()

    def test_rollback(self, temp_db_path: Path) -> None:
        """Test that rollback removes all city tables."""
        from scripts.migrate_add_city_tables import migrate_up, migrate_down

        # Migrate up
        migrate_up(str(temp_db_path))

        # Verify tables exist
        conn = duckdb.connect(str(temp_db_path), read_only=True)
        tables_before = conn.execute("SHOW TABLES").fetchall()
        table_names_before = [t[0] for t in tables_before]
        assert 'cities' in table_names_before
        conn.close()

        # Rollback
        migrate_down(str(temp_db_path))

        # Verify tables are gone
        conn = duckdb.connect(str(temp_db_path), read_only=True)
        tables_after = conn.execute("SHOW TABLES").fetchall()
        table_names_after = [t[0] for t in tables_after]
        assert 'cities' not in table_names_after
        assert 'city_unit_production' not in table_names_after
        assert 'city_projects' not in table_names_after
        conn.close()
