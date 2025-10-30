"""Tests for city query functions.

Test Strategy:
- Test basic city retrieval
- Test expansion analysis queries
- Test production analysis queries
- Use temporary database with known data
"""

import pytest
import duckdb
import tempfile
import shutil
from pathlib import Path


class TestCityQueries:
    """Test query functions for city data."""

    @pytest.fixture
    def temp_db_with_city_data(self) -> Path:
        """Create database with sample city data."""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test.duckdb"

        conn = duckdb.connect(str(db_path))

        # Create schema
        conn.execute("""
            CREATE TABLE matches (
                match_id BIGINT PRIMARY KEY,
                total_turns INTEGER
            )
        """)
        conn.execute("INSERT INTO matches VALUES (1, 92), (2, 47)")

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
            (2, 1, 'becked'),
            (1, 2, 'moose'),
            (2, 2, 'fluffbunny')
        """)

        conn.execute("""
            CREATE TABLE cities (
                city_id INTEGER,
                match_id BIGINT,
                player_id BIGINT,
                city_name VARCHAR,
                tile_id INTEGER,
                founded_turn INTEGER,
                is_capital BOOLEAN,
                PRIMARY KEY (match_id, city_id)
            )
        """)
        conn.execute("""
            INSERT INTO cities VALUES
            (0, 1, 1, 'CITYNAME_NINEVEH', 100, 1, TRUE),
            (1, 1, 2, 'CITYNAME_PERSEPOLIS', 200, 1, TRUE),
            (2, 1, 1, 'CITYNAME_SAREISA', 300, 15, FALSE),
            (3, 1, 2, 'CITYNAME_ARBELA', 400, 22, FALSE),
            (0, 2, 1, 'CITYNAME_CAPITAL1', 500, 1, TRUE),
            (1, 2, 2, 'CITYNAME_CAPITAL2', 600, 1, TRUE)
        """)

        conn.execute("""
            CREATE TABLE city_unit_production (
                production_id INTEGER PRIMARY KEY,
                match_id BIGINT,
                city_id INTEGER,
                unit_type VARCHAR,
                count INTEGER
            )
        """)
        conn.execute("""
            INSERT INTO city_unit_production VALUES
            (1, 1, 0, 'UNIT_SETTLER', 4),
            (2, 1, 0, 'UNIT_WORKER', 1),
            (3, 1, 0, 'UNIT_SPEARMAN', 3),
            (4, 1, 1, 'UNIT_SETTLER', 3),
            (5, 1, 1, 'UNIT_ARCHER', 5)
        """)

        conn.close()

        yield db_path

        shutil.rmtree(temp_dir)

    def test_get_match_cities(self, temp_db_with_city_data: Path) -> None:
        """Test getting all cities for a match."""
        from tournament_visualizer.data.queries import get_match_cities

        cities = get_match_cities(match_id=1, db_path=str(temp_db_with_city_data))

        assert len(cities) == 4
        assert cities[0]['city_name'] == 'CITYNAME_NINEVEH'
        assert cities[0]['founded_turn'] == 1

    def test_get_player_expansion_stats(self, temp_db_with_city_data: Path) -> None:
        """Test expansion statistics for a match."""
        from tournament_visualizer.data.queries import get_player_expansion_stats

        stats = get_player_expansion_stats(match_id=1, db_path=str(temp_db_with_city_data))

        # Should have stats for 2 players
        assert len(stats) == 2

        # Check player 1 (anarkos)
        player1 = [s for s in stats if s['player_name'] == 'anarkos'][0]
        assert player1['total_cities'] == 2
        assert player1['first_city_turn'] == 1
        assert player1['last_city_turn'] == 15

        # Check player 2 (becked)
        player2 = [s for s in stats if s['player_name'] == 'becked'][0]
        assert player2['total_cities'] == 2
        assert player2['last_city_turn'] == 22

    def test_get_production_summary(self, temp_db_with_city_data: Path) -> None:
        """Test production summary by player."""
        from tournament_visualizer.data.queries import get_production_summary

        summary = get_production_summary(match_id=1, db_path=str(temp_db_with_city_data))

        # Should have summary for 2 players
        assert len(summary) == 2

        # Check player with Nineveh (city_id=0, player_id=1)
        player1 = [s for s in summary if s['player_id'] == 1][0]

        # Player 1's cities produced: 4 settlers, 1 worker, 3 spearmen = 8 units
        assert player1['total_units_produced'] == 8

        # Check unit breakdown exists
        assert 'unit_breakdown' in player1 or 'settlers' in player1
