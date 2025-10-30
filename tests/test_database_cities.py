"""Tests for city database operations.

Test Strategy:
- Test bulk insert of cities
- Test bulk insert of production/projects
- Test foreign key constraints
- Test duplicate handling
- Use temporary database
"""

import pytest
import duckdb
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any


class TestCityDatabaseOperations:
    """Test database operations for city data."""

    @pytest.fixture
    def temp_db_with_schema(self) -> Path:
        """Create temporary database with city tables.

        Returns:
            Path to temporary database
        """
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test.duckdb"

        # Run migration to create schema
        from scripts.migrate_add_city_tables import migrate_up
        migrate_up(str(db_path))

        # Create matches table
        conn = duckdb.connect(str(db_path))
        conn.execute("""
            CREATE TABLE matches (
                match_id BIGINT PRIMARY KEY
            )
        """)
        conn.execute("INSERT INTO matches VALUES (1), (2)")

        # Create players table
        conn.execute("""
            CREATE TABLE players (
                player_id BIGINT,
                match_id BIGINT,
                player_name VARCHAR,
                PRIMARY KEY (match_id, player_id)
            )
        """)
        conn.execute("""
            INSERT INTO players VALUES
            (1, 1, 'anarkos'),
            (2, 1, 'becked')
        """)

        conn.close()

        yield db_path

        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_cities(self) -> List[Dict[str, Any]]:
        """Sample city data for testing."""
        return [
            {
                'city_id': 0,
                'city_name': 'CITYNAME_NINEVEH',
                'tile_id': 1292,
                'player_id': 2,
                'founded_turn': 1,
                'family_name': 'FAMILY_TUDIYA',
                'is_capital': True,
                'population': 3,
                'governor_id': 72,
                'first_player_id': 2
            },
            {
                'city_id': 1,
                'city_name': 'CITYNAME_PERSEPOLIS',
                'tile_id': 1375,
                'player_id': 1,
                'founded_turn': 1,
                'family_name': 'FAMILY_ACHAEMENID',
                'is_capital': True,
                'population': 5,
                'governor_id': 61,
                'first_player_id': 1
            }
        ]

    @pytest.fixture
    def sample_production(self) -> List[Dict[str, Any]]:
        """Sample production data for testing."""
        return [
            {'city_id': 0, 'unit_type': 'UNIT_SETTLER', 'count': 4},
            {'city_id': 0, 'unit_type': 'UNIT_WORKER', 'count': 1},
            {'city_id': 1, 'unit_type': 'UNIT_SETTLER', 'count': 4},
        ]

    @pytest.fixture
    def sample_projects(self) -> List[Dict[str, Any]]:
        """Sample project data for testing."""
        return [
            {'city_id': 0, 'project_type': 'PROJECT_FORUM_2', 'count': 1},
            {'city_id': 1, 'project_type': 'PROJECT_GRAIN_DOLE', 'count': 1},
        ]

    def test_insert_cities(
        self,
        temp_db_with_schema: Path,
        sample_cities: List[Dict[str, Any]]
    ) -> None:
        """Test inserting cities into database."""
        from tournament_visualizer.data.database import TournamentDatabase

        db_path = str(temp_db_with_schema)
        db = TournamentDatabase(db_path, read_only=False)

        # Insert cities for match 1
        db.insert_cities(match_id=1, cities=sample_cities)

        # Verify insertion
        conn = duckdb.connect(db_path, read_only=True)
        cities = conn.execute("""
            SELECT city_id, city_name, player_id, is_capital
            FROM cities
            WHERE match_id = 1
            ORDER BY city_id
        """).fetchall()
        conn.close()

        assert len(cities) == 2
        assert cities[0][0] == 0  # city_id
        assert cities[0][1] == 'CITYNAME_NINEVEH'  # city_name
        assert cities[0][2] == 2  # player_id
        assert cities[0][3] is True  # is_capital

    def test_insert_unit_production(
        self,
        temp_db_with_schema: Path,
        sample_cities: List[Dict[str, Any]],
        sample_production: List[Dict[str, Any]]
    ) -> None:
        """Test inserting unit production data."""
        from tournament_visualizer.data.database import TournamentDatabase

        db_path = str(temp_db_with_schema)
        db = TournamentDatabase(db_path, read_only=False)

        # Insert cities first (required for FK)
        db.insert_cities(match_id=1, cities=sample_cities)

        # Insert production
        db.insert_city_unit_production(match_id=1, production=sample_production)

        # Verify insertion
        conn = duckdb.connect(db_path, read_only=True)
        production = conn.execute("""
            SELECT city_id, unit_type, count
            FROM city_unit_production
            WHERE match_id = 1
            ORDER BY city_id, unit_type
        """).fetchall()
        conn.close()

        assert len(production) == 3
        assert production[0][1] == 'UNIT_SETTLER'
        assert production[0][2] == 4

    def test_insert_city_projects(
        self,
        temp_db_with_schema: Path,
        sample_cities: List[Dict[str, Any]],
        sample_projects: List[Dict[str, Any]]
    ) -> None:
        """Test inserting city project data."""
        from tournament_visualizer.data.database import TournamentDatabase

        db_path = str(temp_db_with_schema)
        db = TournamentDatabase(db_path, read_only=False)

        # Insert cities first
        db.insert_cities(match_id=1, cities=sample_cities)

        # Insert projects
        db.insert_city_projects(match_id=1, projects=sample_projects)

        # Verify insertion
        conn = duckdb.connect(db_path, read_only=True)
        projects = conn.execute("""
            SELECT city_id, project_type, count
            FROM city_projects
            WHERE match_id = 1
            ORDER BY city_id
        """).fetchall()
        conn.close()

        assert len(projects) == 2
        assert projects[0][1] == 'PROJECT_FORUM_2'

    def test_insert_empty_lists(self, temp_db_with_schema: Path) -> None:
        """Test that inserting empty lists doesn't error."""
        from tournament_visualizer.data.database import TournamentDatabase

        db = TournamentDatabase(str(temp_db_with_schema), read_only=False)

        # Should not raise errors
        db.insert_cities(match_id=1, cities=[])
        db.insert_city_unit_production(match_id=1, production=[])
        db.insert_city_projects(match_id=1, projects=[])

        # Verify no data inserted
        conn = duckdb.connect(str(temp_db_with_schema), read_only=True)
        count = conn.execute("SELECT COUNT(*) FROM cities").fetchone()[0]
        assert count == 0
        conn.close()

    def test_duplicate_city_handling(
        self,
        temp_db_with_schema: Path,
        sample_cities: List[Dict[str, Any]]
    ) -> None:
        """Test that duplicate cities are handled.

        Primary key prevents duplicates (raises error).
        """
        from tournament_visualizer.data.database import TournamentDatabase

        db = TournamentDatabase(str(temp_db_with_schema), read_only=False)

        # Insert once
        db.insert_cities(match_id=1, cities=sample_cities)

        # Try to insert again (should error)
        with pytest.raises(Exception):  # DuckDB will raise constraint error
            db.insert_cities(match_id=1, cities=sample_cities)
