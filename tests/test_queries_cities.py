"""Tests for city query functions.

Test Strategy:
- Test basic city retrieval
- Test expansion analysis queries
- Test production analysis queries
- Use TournamentDatabase with known data (follows codebase pattern)
"""

import pytest

from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.queries import TournamentQueries


class TestCityQueries:
    """Test query functions for city data."""

    @pytest.fixture
    def city_test_db(self, tmp_path):
        """Create database with sample city data.

        Follows pattern from test_queries_civilization_performance.py fixture.
        """
        db_path = tmp_path / "city_test.duckdb"

        # Create database with schema
        import duckdb
        conn = duckdb.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(20) PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """)
        conn.execute("""
            INSERT INTO schema_migrations (version, description)
            VALUES ('5', 'Add city tracking tables')
        """)
        conn.close()

        db = TournamentDatabase(str(db_path), read_only=False)
        db.create_schema()

        with db.get_connection() as conn:
            # Create city tables (not in base schema yet)
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

            # Create sequence for city_unit_production
            conn.execute("CREATE SEQUENCE IF NOT EXISTS city_unit_production_id_seq START 1")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS city_unit_production (
                    production_id INTEGER PRIMARY KEY DEFAULT nextval('city_unit_production_id_seq'),
                    match_id BIGINT NOT NULL,
                    city_id INTEGER NOT NULL,
                    unit_type VARCHAR NOT NULL,
                    count INTEGER NOT NULL
                )
            """)

            # Insert matches
            conn.execute("""
                INSERT INTO matches (match_id, challonge_match_id, file_name, file_hash, total_turns)
                VALUES
                (1, 100, 'm1.zip', 'h1', 92),
                (2, 101, 'm2.zip', 'h2', 47)
            """)

            # Insert players (player_id must be globally unique)
            conn.execute("""
                INSERT INTO players (player_id, match_id, player_name, player_name_normalized)
                VALUES
                (1, 1, 'anarkos', 'anarkos'),
                (2, 1, 'becked', 'becked'),
                (3, 2, 'moose', 'moose'),
                (4, 2, 'fluffbunny', 'fluffbunny')
            """)

            # Insert cities
            conn.execute("""
                INSERT INTO cities (city_id, match_id, player_id, city_name, tile_id, founded_turn, is_capital)
                VALUES
                (0, 1, 1, 'CITYNAME_NINEVEH', 100, 1, TRUE),
                (1, 1, 2, 'CITYNAME_PERSEPOLIS', 200, 1, TRUE),
                (2, 1, 1, 'CITYNAME_SAREISA', 300, 15, FALSE),
                (3, 1, 2, 'CITYNAME_ARBELA', 400, 22, FALSE),
                (0, 2, 3, 'CITYNAME_CAPITAL1', 500, 1, TRUE),
                (1, 2, 4, 'CITYNAME_CAPITAL2', 600, 1, TRUE)
            """)

            # Insert city unit production
            conn.execute("""
                INSERT INTO city_unit_production (match_id, city_id, unit_type, count)
                VALUES
                (1, 0, 'UNIT_SETTLER', 4),
                (1, 0, 'UNIT_WORKER', 1),
                (1, 0, 'UNIT_SPEARMAN', 3),
                (1, 1, 'UNIT_SETTLER', 3),
                (1, 1, 'UNIT_ARCHER', 5)
            """)

        yield db
        db.close()

    def test_get_match_cities(self, city_test_db: TournamentDatabase) -> None:
        """Test getting all cities for a match."""
        queries = TournamentQueries(city_test_db)

        df = queries.get_match_cities(match_id=1)

        # Should have 4 cities for match 1
        assert len(df) == 4

        # Check first city (Nineveh)
        first_city = df.iloc[0]
        assert first_city['city_name'] == 'CITYNAME_NINEVEH'
        assert first_city['founded_turn'] == 1
        assert first_city['is_capital'] == True

    def test_get_player_expansion_stats(self, city_test_db: TournamentDatabase) -> None:
        """Test expansion statistics for a match."""
        queries = TournamentQueries(city_test_db)

        df = queries.get_player_expansion_stats(match_id=1)

        # Should have stats for 2 players
        assert len(df) == 2

        # Check player 1 (anarkos) - should have 2 cities
        player1 = df[df['player_name'] == 'anarkos'].iloc[0]
        assert player1['total_cities'] == 2
        assert player1['first_city_turn'] == 1
        assert player1['last_city_turn'] == 15

        # Check player 2 (becked) - should have 2 cities
        player2 = df[df['player_name'] == 'becked'].iloc[0]
        assert player2['total_cities'] == 2
        assert player2['last_city_turn'] == 22

    def test_get_production_summary(self, city_test_db: TournamentDatabase) -> None:
        """Test production summary by player."""
        queries = TournamentQueries(city_test_db)

        df = queries.get_production_summary(match_id=1)

        # Should have summary for 2 players
        assert len(df) == 2

        # Check player 1 (anarkos) - produced 4+1+3=8 units
        player1 = df[df['player_id'] == 1].iloc[0]
        assert player1['total_units_produced'] == 8
        assert player1['settlers'] == 4
        assert player1['workers'] == 1

        # Check player 2 (becked) - produced 3+5=8 units
        player2 = df[df['player_id'] == 2].iloc[0]
        assert player2['total_units_produced'] == 8
        assert player2['settlers'] == 3
