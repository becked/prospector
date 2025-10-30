"""Tests for tournament-wide city analytics queries.

Test Strategy:
- Test tournament-wide aggregation queries
- Test cumulative calculations
- Test edge cases (empty data, no conquests)
- Use TournamentDatabase with known data (follows codebase pattern)
"""

import pytest
import pandas as pd

from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.queries import TournamentQueries


class TestTournamentCityAnalytics:
    """Test tournament-wide city analytics query functions."""

    @pytest.fixture
    def test_db_with_city_data(self, tmp_path):
        """Create database with sample tournament-wide city data.

        Creates realistic test data across multiple matches with:
        - 3 players across 2 matches
        - Various city founding turns
        - Mix of unit production
        - Different project types
        - One conquest event
        """
        db_path = tmp_path / "city_analytics_test.duckdb"

        # Create database with schema
        import duckdb

        conn = duckdb.connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(20) PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """
        )
        conn.execute(
            """
            INSERT INTO schema_migrations (version, description)
            VALUES ('5', 'Add city tracking tables')
        """
        )
        conn.close()

        db = TournamentDatabase(str(db_path), read_only=False)
        db.create_schema()

        with db.get_connection() as conn:
            # Create city tables
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cities (
                    city_id INTEGER NOT NULL,
                    match_id BIGINT NOT NULL,
                    player_id BIGINT NOT NULL,
                    city_name VARCHAR NOT NULL,
                    tile_id INTEGER,
                    founded_turn INTEGER NOT NULL,
                    family_name VARCHAR,
                    is_capital BOOLEAN,
                    population INTEGER,
                    first_player_id BIGINT,
                    governor_id INTEGER,
                    PRIMARY KEY (match_id, city_id)
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS city_unit_production (
                    production_id BIGINT PRIMARY KEY,
                    match_id BIGINT NOT NULL,
                    city_id INTEGER NOT NULL,
                    unit_type VARCHAR NOT NULL,
                    count INTEGER NOT NULL
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS city_projects (
                    project_id BIGINT PRIMARY KEY,
                    match_id BIGINT NOT NULL,
                    city_id INTEGER NOT NULL,
                    project_type VARCHAR NOT NULL,
                    count INTEGER NOT NULL
                )
            """
            )

            # Insert test matches
            conn.execute(
                """
                INSERT INTO matches (match_id, challonge_match_id, file_name, file_hash)
                VALUES
                    (1, 101, 'match1.zip', 'hash1'),
                    (2, 102, 'match2.zip', 'hash2')
            """
            )

            # Insert test players (3 players across 2 matches)
            conn.execute(
                """
                INSERT INTO players (player_id, match_id, player_name, player_name_normalized, civilization)
                VALUES
                    (1, 1, 'Alice', 'alice', 'Rome'),
                    (2, 1, 'Bob', 'bob', 'Carthage'),
                    (3, 2, 'Charlie', 'charlie', 'Greece')
            """
            )

            # Insert cities with staggered founding turns
            # Alice: 3 cities (turns 1, 10, 20)
            # Bob: 2 cities (turns 5, 15), one is conquered from Alice
            # Charlie: 4 cities (turns 1, 8, 16, 40)
            conn.execute(
                """
                INSERT INTO cities (city_id, match_id, player_id, city_name, tile_id, founded_turn, is_capital, first_player_id)
                VALUES
                    -- Match 1: Alice's cities
                    (1, 1, 1, 'CITYNAME_ROMA', 100, 1, TRUE, NULL),
                    (2, 1, 1, 'CITYNAME_OSTIA', 101, 10, FALSE, NULL),
                    (3, 1, 1, 'CITYNAME_VEII', 102, 20, FALSE, NULL),
                    -- Match 1: Bob's cities (city 5 is conquered from Alice)
                    (4, 1, 2, 'CITYNAME_CARTHAGE', 200, 5, TRUE, NULL),
                    (5, 1, 2, 'CITYNAME_SYRACUSE', 201, 15, FALSE, 1),
                    -- Match 2: Charlie's cities
                    (6, 2, 3, 'CITYNAME_ATHENS', 300, 1, TRUE, NULL),
                    (7, 2, 3, 'CITYNAME_SPARTA', 301, 8, FALSE, NULL),
                    (8, 2, 3, 'CITYNAME_CORINTH', 302, 16, FALSE, NULL),
                    (9, 2, 3, 'CITYNAME_THEBES', 303, 40, FALSE, NULL)
            """
            )

            # Insert unit production
            conn.execute(
                """
                INSERT INTO city_unit_production (production_id, match_id, city_id, unit_type, count)
                VALUES
                    -- Alice: heavy on settlers and workers
                    (1, 1, 1, 'UNIT_SETTLER', 3),
                    (2, 1, 1, 'UNIT_WORKER', 5),
                    (3, 1, 2, 'UNIT_SETTLER', 2),
                    (4, 1, 2, 'UNIT_WORKER', 3),
                    -- Bob: balanced
                    (5, 1, 4, 'UNIT_SETTLER', 1),
                    (6, 1, 4, 'UNIT_WORKER', 2),
                    (7, 1, 4, 'UNIT_JUDAISM_DISCIPLE', 1),
                    -- Charlie: heavy on disciples
                    (8, 2, 6, 'UNIT_SETTLER', 1),
                    (9, 2, 6, 'UNIT_WORKER', 2),
                    (10, 2, 7, 'UNIT_CHRISTIANITY_DISCIPLE', 3),
                    (11, 2, 8, 'UNIT_ZOROASTRIANISM_DISCIPLE', 2)
            """
            )

            # Insert city projects
            conn.execute(
                """
                INSERT INTO city_projects (project_id, match_id, city_id, project_type, count)
                VALUES
                    -- Alice: forums and festivals
                    (1, 1, 1, 'PROJECT_FORUM_1', 1),
                    (2, 1, 1, 'PROJECT_FESTIVAL', 2),
                    (3, 1, 2, 'PROJECT_FORUM_1', 1),
                    -- Bob: treasuries
                    (4, 1, 4, 'PROJECT_TREASURY_1', 1),
                    (5, 1, 4, 'PROJECT_FESTIVAL', 1),
                    -- Charlie: mixed projects
                    (6, 2, 6, 'PROJECT_FORUM_1', 2),
                    (7, 2, 6, 'PROJECT_FESTIVAL', 3),
                    (8, 2, 7, 'PROJECT_TREASURY_1', 1),
                    (9, 2, 8, 'PROJECT_WALLS', 1)
            """
            )

        return db

    def test_get_tournament_expansion_timeline(self, test_db_with_city_data):
        """Test expansion timeline returns cumulative city counts."""
        # Arrange
        queries = TournamentQueries(test_db_with_city_data)

        # Act
        result = queries.get_tournament_expansion_timeline()

        # Assert
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert list(result.columns) == [
            "player_name",
            "civilization",
            "founded_turn",
            "cities_this_turn",
            "cumulative_cities",
        ]

        # Check cumulative count is monotonically increasing per player
        for (player, civ), group in result.groupby(["player_name", "civilization"]):
            cumulative = group.sort_values("founded_turn")[
                "cumulative_cities"
            ].tolist()
            assert all(
                cumulative[i] <= cumulative[i + 1] for i in range(len(cumulative) - 1)
            ), f"{player}'s cumulative cities should never decrease"

        # Verify specific data points
        alice_data = result[result["player_name"] == "Alice"].sort_values(
            "founded_turn"
        )
        assert len(alice_data) == 3
        assert alice_data.iloc[0]["cumulative_cities"] == 1  # Turn 1
        assert alice_data.iloc[1]["cumulative_cities"] == 2  # Turn 10
        assert alice_data.iloc[2]["cumulative_cities"] == 3  # Turn 20

    def test_get_tournament_city_founding_distribution(self, test_db_with_city_data):
        """Test founding distribution groups cities into turn ranges."""
        # Arrange
        queries = TournamentQueries(test_db_with_city_data)

        # Act
        result = queries.get_tournament_city_founding_distribution()

        # Assert
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert list(result.columns) == ["turn_range", "city_count", "percentage"]

        # Check turn ranges are present (we have cities in multiple ranges)
        turn_ranges = result["turn_range"].tolist()
        assert "1-20" in turn_ranges
        assert "21-40" in turn_ranges

        # Check percentages sum to ~100
        total_percentage = result["percentage"].sum()
        assert 99.0 <= total_percentage <= 101.0

        # Check specific counts
        early_game = result[result["turn_range"] == "1-20"]
        assert len(early_game) == 1
        assert (
            early_game.iloc[0]["city_count"] == 8
        )  # 8 cities founded in turns 1-20

    def test_get_tournament_production_strategies(self, test_db_with_city_data):
        """Test production strategies aggregates unit production per player."""
        # Arrange
        queries = TournamentQueries(test_db_with_city_data)

        # Act
        result = queries.get_tournament_production_strategies()

        # Assert
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert list(result.columns) == [
            "player_name",
            "civilization",
            "settlers",
            "workers",
            "disciples",
            "total_units",
        ]

        # Verify specific player data
        alice_data = result[result["player_name"] == "Alice"]
        assert len(alice_data) == 1
        assert alice_data.iloc[0]["settlers"] == 5  # 3 + 2
        assert alice_data.iloc[0]["workers"] == 8  # 5 + 3
        assert alice_data.iloc[0]["disciples"] == 0
        assert alice_data.iloc[0]["total_units"] == 13

        charlie_data = result[result["player_name"] == "Charlie"]
        assert len(charlie_data) == 1
        assert charlie_data.iloc[0]["settlers"] == 1
        assert charlie_data.iloc[0]["workers"] == 2
        assert charlie_data.iloc[0]["disciples"] == 5  # 3 + 2
        assert charlie_data.iloc[0]["total_units"] == 8

    def test_get_tournament_project_priorities(self, test_db_with_city_data):
        """Test project priorities aggregates projects per player."""
        # Arrange
        queries = TournamentQueries(test_db_with_city_data)

        # Act
        result = queries.get_tournament_project_priorities()

        # Assert
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert list(result.columns) == [
            "player_name",
            "civilization",
            "project_type",
            "project_count",
        ]

        # Check ordering (should be by player_name, project_count DESC)
        alice_data = result[result["player_name"] == "Alice"]
        assert len(alice_data) == 2  # forums and festivals
        assert alice_data.iloc[0]["project_type"] == "PROJECT_FORUM_1"
        assert alice_data.iloc[0]["project_count"] == 2
        assert alice_data.iloc[1]["project_type"] == "PROJECT_FESTIVAL"
        assert alice_data.iloc[1]["project_count"] == 2

        # Verify Charlie's projects
        charlie_data = result[result["player_name"] == "Charlie"]
        assert len(charlie_data) == 4

    def test_get_tournament_conquest_summary(self, test_db_with_city_data):
        """Test conquest summary identifies conquered cities."""
        # Arrange
        queries = TournamentQueries(test_db_with_city_data)

        # Act
        result = queries.get_tournament_conquest_summary()

        # Assert
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert list(result.columns) == [
            "conqueror_name",
            "conqueror_civ",
            "original_founder_name",
            "original_founder_civ",
            "city_name",
            "founded_turn",
            "match_id",
        ]

        # We have exactly 1 conquest (Bob conquered city 5 from Alice)
        assert len(result) == 1
        conquest = result.iloc[0]
        assert conquest["conqueror_name"] == "Bob"
        assert conquest["conqueror_civ"] == "Carthage"
        assert conquest["original_founder_name"] == "Alice"
        assert conquest["original_founder_civ"] == "Rome"
        assert conquest["city_name"] == "CITYNAME_SYRACUSE"
        assert conquest["founded_turn"] == 15
        assert conquest["match_id"] == 1

    def test_get_tournament_conquest_summary_empty(self, tmp_path):
        """Test conquest summary returns empty DataFrame when no conquests."""
        # Arrange: Create database with cities but no conquests
        db_path = tmp_path / "no_conquests.duckdb"

        import duckdb

        conn = duckdb.connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(20) PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """
        )
        conn.execute(
            """
            INSERT INTO schema_migrations (version, description)
            VALUES ('5', 'Add city tracking tables')
        """
        )
        conn.close()

        db = TournamentDatabase(str(db_path), read_only=False)
        db.create_schema()

        with db.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cities (
                    city_id INTEGER NOT NULL,
                    match_id BIGINT NOT NULL,
                    player_id BIGINT NOT NULL,
                    city_name VARCHAR NOT NULL,
                    tile_id INTEGER,
                    founded_turn INTEGER NOT NULL,
                    family_name VARCHAR,
                    is_capital BOOLEAN,
                    population INTEGER,
                    first_player_id BIGINT,
                    governor_id INTEGER,
                    PRIMARY KEY (match_id, city_id)
                )
            """
            )

            conn.execute(
                """
                INSERT INTO matches (match_id, challonge_match_id, file_name, file_hash)
                VALUES (1, 101, 'match1.zip', 'hash1')
            """
            )

            conn.execute(
                """
                INSERT INTO players (player_id, match_id, player_name, player_name_normalized, civilization)
                VALUES (1, 1, 'Alice', 'alice', 'Rome')
            """
            )

            # Insert city with no conquest (first_player_id is NULL)
            conn.execute(
                """
                INSERT INTO cities (city_id, match_id, player_id, city_name, tile_id, founded_turn, is_capital, first_player_id)
                VALUES (1, 1, 1, 'CITYNAME_ROMA', 100, 1, TRUE, NULL)
            """
            )

        queries = TournamentQueries(db)

        # Act
        result = queries.get_tournament_conquest_summary()

        # Assert
        assert isinstance(result, pd.DataFrame)
        assert result.empty
