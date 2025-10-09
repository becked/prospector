"""Database connection and schema management for tournament data.

This module handles DuckDB connection, schema creation, and database operations
for the tournament visualization application.
"""

import logging
import threading
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

import duckdb

logger = logging.getLogger(__name__)


class TournamentDatabase:
    """Manages database connection and schema for tournament data."""

    def __init__(
        self, db_path: str = "tournament_data.duckdb", read_only: bool = True
    ) -> None:
        """Initialize database connection.

        Args:
            db_path: Path to the DuckDB database file
            read_only: Whether to open in read-only mode (default True for safety)
        """
        self.db_path = db_path
        self.read_only = read_only
        self.connection: Optional[duckdb.DuckDBPyConnection] = None
        self._lock = threading.RLock()  # Use reentrant lock to avoid deadlocks

    @contextmanager
    def get_connection(self):
        """Context manager for database connections with proper locking.

        Uses the shared connection to prevent multiple connections.

        Yields:
            DuckDB connection object
        """
        with self._lock:
            # Ensure the shared connection is established
            conn = self.connect()
            yield conn

    def connect(self) -> duckdb.DuckDBPyConnection:
        """Establish database connection.

        Uses double-checked locking pattern for thread safety.

        Returns:
            DuckDB connection object
        """
        # First check without lock for performance
        if self.connection is None:
            # Second check with lock for thread safety
            with self._lock:
                if self.connection is None:
                    # Connect based on read_only setting
                    self.connection = duckdb.connect(
                        self.db_path, read_only=self.read_only
                    )
                    mode = "read-only" if self.read_only else "read-write"
                    logger.info(
                        f"Connected to database: {self.db_path} ({mode} mode, single shared connection)"
                    )
        return self.connection

    def close(self) -> None:
        """Close database connection."""
        with self._lock:
            if self.connection:
                self.connection.close()
                self.connection = None
                logger.info("Shared database connection closed")

    def execute_query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> None:
        """Execute a SQL query (for INSERT/UPDATE/DELETE operations).

        Args:
            query: SQL query string
            parameters: Query parameters
        """
        with self.get_connection() as conn:
            conn.execute(query, parameters or {})

    def fetch_all(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple]:
        """Execute query and fetch all results.

        Args:
            query: SQL query string
            parameters: Query parameters

        Returns:
            List of result tuples
        """
        with self.get_connection() as conn:
            result = conn.execute(query, parameters or {})
            return result.fetchall()

    def fetch_one(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> Optional[Tuple]:
        """Execute query and fetch one result.

        Args:
            query: SQL query string
            parameters: Query parameters

        Returns:
            Single result tuple or None
        """
        with self.get_connection() as conn:
            result = conn.execute(query, parameters or {})
            return result.fetchone()

    def create_schema(self) -> None:
        """Create the complete database schema."""
        logger.info("Creating database schema...")

        # Create sequences for auto-increment
        self._create_sequences()

        # Create tables in dependency order
        self._create_matches_table()
        self._create_players_table()
        self._create_match_winners_table()
        self._create_match_metadata_table()
        self._create_game_state_table()
        self._create_territories_table()
        self._create_events_table()
        self._create_resources_table()
        self._create_technology_progress_table()
        self._create_player_statistics_table()
        self._create_units_produced_table()
        self._create_unit_classifications_table()
        self._create_player_points_history_table()
        self._create_player_military_history_table()
        self._create_player_legitimacy_history_table()
        self._create_family_opinion_history_table()
        self._create_religion_opinion_history_table()
        self._create_schema_migrations_table()
        self._create_views()

        # Mark initial schema version
        self._mark_schema_version(
            "1.0.0",
            "Initial database schema with comprehensive constraints and indexes",
        )

        logger.info("Database schema created successfully")

    def _create_sequences(self) -> None:
        """Create sequences for auto-increment primary keys."""
        sequences = [
            "CREATE SEQUENCE IF NOT EXISTS matches_id_seq START 1;",
            "CREATE SEQUENCE IF NOT EXISTS players_id_seq START 1;",
            "CREATE SEQUENCE IF NOT EXISTS game_state_id_seq START 1;",
            "CREATE SEQUENCE IF NOT EXISTS territories_id_seq START 1;",
            "CREATE SEQUENCE IF NOT EXISTS events_id_seq START 1;",
            "CREATE SEQUENCE IF NOT EXISTS resources_id_seq START 1;",
            "CREATE SEQUENCE IF NOT EXISTS technology_progress_id_seq START 1;",
            "CREATE SEQUENCE IF NOT EXISTS player_statistics_id_seq START 1;",
            "CREATE SEQUENCE IF NOT EXISTS units_produced_id_seq START 1;",
            "CREATE SEQUENCE IF NOT EXISTS points_history_id_seq START 1;",
            "CREATE SEQUENCE IF NOT EXISTS military_history_id_seq START 1;",
            "CREATE SEQUENCE IF NOT EXISTS legitimacy_history_id_seq START 1;",
            "CREATE SEQUENCE IF NOT EXISTS family_opinion_id_seq START 1;",
            "CREATE SEQUENCE IF NOT EXISTS religion_opinion_id_seq START 1;",
        ]

        with self.get_connection() as conn:
            for seq_query in sequences:
                conn.execute(seq_query)

    def _create_matches_table(self) -> None:
        """Create the matches table."""
        query = """
        CREATE TABLE IF NOT EXISTS matches (
            match_id BIGINT PRIMARY KEY,
            challonge_match_id INTEGER,
            file_name VARCHAR(255) NOT NULL,
            file_hash CHAR(64) NOT NULL,
            game_name VARCHAR(255),
            save_date TIMESTAMP,
            processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            game_mode VARCHAR(50),
            map_size VARCHAR(20),
            map_class VARCHAR(50),
            map_aspect_ratio VARCHAR(20),
            turn_style VARCHAR(50),
            turn_timer VARCHAR(20),
            victory_conditions TEXT,
            total_turns INTEGER,
            winner_player_id BIGINT,

            CONSTRAINT unique_file UNIQUE(file_name, file_hash),
            CONSTRAINT check_total_turns CHECK(total_turns >= 0)
        );
        
        CREATE INDEX IF NOT EXISTS idx_matches_processed_date ON matches(processed_date);
        CREATE INDEX IF NOT EXISTS idx_matches_challonge_id ON matches(challonge_match_id);
        CREATE INDEX IF NOT EXISTS idx_matches_save_date ON matches(save_date);
        CREATE INDEX IF NOT EXISTS idx_matches_winner ON matches(winner_player_id);
        """
        with self.get_connection() as conn:
            conn.execute(query)

    def _create_players_table(self) -> None:
        """Create the players table."""
        query = """
        CREATE TABLE IF NOT EXISTS players (
            player_id BIGINT PRIMARY KEY,
            match_id BIGINT NOT NULL REFERENCES matches(match_id),
            player_name VARCHAR(100) NOT NULL,
            player_name_normalized VARCHAR(100) NOT NULL,
            civilization VARCHAR(50),
            team_id INTEGER,
            difficulty_level VARCHAR(20),
            final_score INTEGER DEFAULT 0,
            is_human BOOLEAN DEFAULT TRUE,
            final_turn_active INTEGER,

            CONSTRAINT check_final_score CHECK(final_score >= 0),
            CONSTRAINT check_final_turn_active CHECK(final_turn_active >= 0)
        );

        CREATE INDEX IF NOT EXISTS idx_players_match_id ON players(match_id);
        CREATE INDEX IF NOT EXISTS idx_players_name ON players(player_name);
        CREATE INDEX IF NOT EXISTS idx_players_name_normalized ON players(player_name_normalized);
        CREATE INDEX IF NOT EXISTS idx_players_civilization ON players(civilization);
        CREATE INDEX IF NOT EXISTS idx_players_match_name ON players(match_id, player_name_normalized);
        """
        with self.get_connection() as conn:
            conn.execute(query)

    def _create_match_winners_table(self) -> None:
        """Create the match_winners table for tracking winners separately."""
        query = """
        CREATE TABLE IF NOT EXISTS match_winners (
            match_id BIGINT PRIMARY KEY REFERENCES matches(match_id),
            winner_player_id BIGINT NOT NULL REFERENCES players(player_id),
            winner_determination_method VARCHAR(50) DEFAULT 'automatic',
            determined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_match_winners_player ON match_winners(winner_player_id);
        """
        with self.get_connection() as conn:
            conn.execute(query)

    def _create_game_state_table(self) -> None:
        """Create the game_state table."""
        query = """
        CREATE TABLE IF NOT EXISTS game_state (
            state_id BIGINT PRIMARY KEY,
            match_id BIGINT NOT NULL REFERENCES matches(match_id),
            turn_number INTEGER NOT NULL,
            active_player_id BIGINT REFERENCES players(player_id),
            game_year INTEGER,
            turn_timestamp TIMESTAMP,

            CONSTRAINT check_turn_number CHECK(turn_number >= 0),
            CONSTRAINT check_game_year CHECK(game_year >= 0)
        );
        
        CREATE INDEX IF NOT EXISTS idx_game_state_match_turn ON game_state(match_id, turn_number);
        CREATE INDEX IF NOT EXISTS idx_game_state_player ON game_state(active_player_id);
        """
        with self.get_connection() as conn:
            conn.execute(query)

    def _create_territories_table(self) -> None:
        """Create the territories table."""
        query = """
        CREATE TABLE IF NOT EXISTS territories (
            territory_id BIGINT PRIMARY KEY,
            match_id BIGINT NOT NULL REFERENCES matches(match_id),
            x_coordinate INTEGER NOT NULL,
            y_coordinate INTEGER NOT NULL,
            turn_number INTEGER NOT NULL,
            terrain_type VARCHAR(50),
            owner_player_id BIGINT REFERENCES players(player_id),

            CONSTRAINT check_x_coordinate CHECK(x_coordinate >= 0 AND x_coordinate <= 45),
            CONSTRAINT check_y_coordinate CHECK(y_coordinate >= 0 AND y_coordinate <= 45),
            CONSTRAINT check_turn_number CHECK(turn_number >= 0),
            CONSTRAINT unique_territory_turn UNIQUE(match_id, x_coordinate, y_coordinate, turn_number)
        );
        
        CREATE INDEX IF NOT EXISTS idx_territories_spatial ON territories(match_id, x_coordinate, y_coordinate);
        CREATE INDEX IF NOT EXISTS idx_territories_temporal ON territories(match_id, turn_number);
        CREATE INDEX IF NOT EXISTS idx_territories_owner ON territories(owner_player_id);
        CREATE INDEX IF NOT EXISTS idx_territories_spatial_temporal ON territories(match_id, turn_number, x_coordinate, y_coordinate);
        """
        with self.get_connection() as conn:
            conn.execute(query)

    def _create_events_table(self) -> None:
        """Create the events table."""
        query = """
        CREATE TABLE IF NOT EXISTS events (
            event_id BIGINT PRIMARY KEY,
            match_id BIGINT NOT NULL REFERENCES matches(match_id),
            turn_number INTEGER NOT NULL,
            event_type VARCHAR(100) NOT NULL,
            player_id BIGINT REFERENCES players(player_id),
            description TEXT,
            x_coordinate INTEGER,
            y_coordinate INTEGER,
            event_data JSON,

            CONSTRAINT check_turn_number CHECK(turn_number >= 0),
            CONSTRAINT check_x_coordinate CHECK(x_coordinate IS NULL OR (x_coordinate >= 0 AND x_coordinate <= 45)),
            CONSTRAINT check_y_coordinate CHECK(y_coordinate IS NULL OR (y_coordinate >= 0 AND y_coordinate <= 45))
        );
        
        CREATE INDEX IF NOT EXISTS idx_events_match_turn ON events(match_id, turn_number);
        CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
        CREATE INDEX IF NOT EXISTS idx_events_player ON events(player_id);
        CREATE INDEX IF NOT EXISTS idx_events_location ON events(x_coordinate, y_coordinate);
        CREATE INDEX IF NOT EXISTS idx_events_type_player ON events(event_type, player_id, turn_number);
        """
        with self.get_connection() as conn:
            conn.execute(query)

    def _create_resources_table(self) -> None:
        """Create the resources table."""
        query = """
        CREATE TABLE IF NOT EXISTS resources (
            resource_id BIGINT PRIMARY KEY,
            match_id BIGINT NOT NULL REFERENCES matches(match_id),
            player_id BIGINT NOT NULL REFERENCES players(player_id),
            turn_number INTEGER NOT NULL,
            resource_type VARCHAR(50) NOT NULL,
            amount INTEGER NOT NULL,

            CONSTRAINT check_turn_number CHECK(turn_number >= 0),
            CONSTRAINT check_amount CHECK(amount >= 0),
            CONSTRAINT unique_resource_turn UNIQUE(match_id, player_id, turn_number, resource_type)
        );
        
        CREATE INDEX IF NOT EXISTS idx_resources_match_player ON resources(match_id, player_id);
        CREATE INDEX IF NOT EXISTS idx_resources_turn ON resources(turn_number);
        CREATE INDEX IF NOT EXISTS idx_resources_type ON resources(resource_type);
        CREATE INDEX IF NOT EXISTS idx_resources_match_turn_type ON resources(match_id, turn_number, resource_type);
        """
        with self.get_connection() as conn:
            conn.execute(query)

    def _create_match_metadata_table(self) -> None:
        """Create the match_metadata table for detailed game settings."""
        query = """
        CREATE TABLE IF NOT EXISTS match_metadata (
            match_id BIGINT PRIMARY KEY REFERENCES matches(match_id),
            difficulty VARCHAR(50),
            event_level VARCHAR(50),
            victory_type VARCHAR(100),
            victory_turn INTEGER,
            game_options TEXT,
            dlc_content TEXT,
            map_settings TEXT,

            CONSTRAINT check_victory_turn CHECK(victory_turn IS NULL OR victory_turn >= 0)
        );

        CREATE INDEX IF NOT EXISTS idx_match_metadata_difficulty ON match_metadata(difficulty);
        CREATE INDEX IF NOT EXISTS idx_match_metadata_victory_type ON match_metadata(victory_type);
        """
        with self.get_connection() as conn:
            conn.execute(query)

    def _create_technology_progress_table(self) -> None:
        """Create the technology_progress table for tracking tech research."""
        query = """
        CREATE TABLE IF NOT EXISTS technology_progress (
            tech_progress_id BIGINT PRIMARY KEY,
            match_id BIGINT NOT NULL REFERENCES matches(match_id),
            player_id BIGINT NOT NULL REFERENCES players(player_id),
            tech_name VARCHAR(100) NOT NULL,
            count INTEGER NOT NULL,

            CONSTRAINT check_tech_count CHECK(count >= 0),
            CONSTRAINT unique_tech_per_player UNIQUE(match_id, player_id, tech_name)
        );

        CREATE INDEX IF NOT EXISTS idx_tech_progress_match_player ON technology_progress(match_id, player_id);
        CREATE INDEX IF NOT EXISTS idx_tech_progress_tech_name ON technology_progress(tech_name);
        """
        with self.get_connection() as conn:
            conn.execute(query)

    def _create_player_statistics_table(self) -> None:
        """Create the player_statistics table for tracking various player stats including law progression."""
        query = """
        CREATE TABLE IF NOT EXISTS player_statistics (
            stat_id BIGINT PRIMARY KEY,
            match_id BIGINT NOT NULL REFERENCES matches(match_id),
            player_id BIGINT NOT NULL REFERENCES players(player_id),
            stat_category VARCHAR(100) NOT NULL,
            stat_name VARCHAR(100) NOT NULL,
            value INTEGER NOT NULL,

            CONSTRAINT unique_stat_per_player UNIQUE(match_id, player_id, stat_category, stat_name)
        );

        CREATE INDEX IF NOT EXISTS idx_player_stats_match_player ON player_statistics(match_id, player_id);
        CREATE INDEX IF NOT EXISTS idx_player_stats_category ON player_statistics(stat_category);
        CREATE INDEX IF NOT EXISTS idx_player_stats_name ON player_statistics(stat_name);
        """
        with self.get_connection() as conn:
            conn.execute(query)

    def _create_units_produced_table(self) -> None:
        """Create the units_produced table for tracking unit production by players."""
        query = """
        CREATE TABLE IF NOT EXISTS units_produced (
            unit_produced_id BIGINT PRIMARY KEY,
            match_id BIGINT NOT NULL REFERENCES matches(match_id),
            player_id BIGINT NOT NULL REFERENCES players(player_id),
            unit_type VARCHAR(100) NOT NULL,
            count INTEGER NOT NULL,

            CONSTRAINT check_unit_count CHECK(count >= 0),
            CONSTRAINT unique_unit_per_player UNIQUE(match_id, player_id, unit_type)
        );

        CREATE INDEX IF NOT EXISTS idx_units_produced_match_player ON units_produced(match_id, player_id);
        CREATE INDEX IF NOT EXISTS idx_units_produced_unit_type ON units_produced(unit_type);
        CREATE INDEX IF NOT EXISTS idx_units_produced_match_unit ON units_produced(match_id, unit_type);
        """
        with self.get_connection() as conn:
            conn.execute(query)

    def _create_unit_classifications_table(self) -> None:
        """Create the unit_classifications table for categorizing unit types."""
        query = """
        CREATE TABLE IF NOT EXISTS unit_classifications (
            unit_type VARCHAR(100) PRIMARY KEY,
            category VARCHAR(50) NOT NULL,
            role VARCHAR(50) NOT NULL,
            description TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_unit_classifications_category ON unit_classifications(category);
        CREATE INDEX IF NOT EXISTS idx_unit_classifications_role ON unit_classifications(role);
        """
        with self.get_connection() as conn:
            conn.execute(query)

            # Populate with initial unit classifications
            classifications = [
                # Civilian units
                (
                    "UNIT_WORKER",
                    "civilian",
                    "worker",
                    "Worker unit for improving tiles",
                ),
                (
                    "UNIT_SETTLER",
                    "civilian",
                    "settler",
                    "Settler unit for founding cities",
                ),
                # Religious units
                (
                    "UNIT_JUDAISM_DISCIPLE",
                    "religious",
                    "religious",
                    "Religious unit for spreading Judaism",
                ),
                (
                    "UNIT_ZOROASTRIANISM_DISCIPLE",
                    "religious",
                    "religious",
                    "Religious unit for spreading Zoroastrianism",
                ),
                # Military - Scout
                (
                    "UNIT_SCOUT",
                    "military",
                    "scout",
                    "Scout unit for exploration and reconnaissance",
                ),
                # Military - Infantry
                ("UNIT_WARRIOR", "military", "infantry", "Basic melee infantry unit"),
                ("UNIT_SPEARMAN", "military", "infantry", "Anti-cavalry infantry unit"),
                ("UNIT_HASTATUS", "military", "infantry", "Roman infantry unit"),
                (
                    "UNIT_LEGIONARY",
                    "military",
                    "infantry",
                    "Advanced Roman infantry unit",
                ),
                (
                    "UNIT_MILITIA",
                    "military",
                    "infantry",
                    "Basic defensive infantry unit",
                ),
                ("UNIT_AXEMAN", "military", "infantry", "Melee infantry unit with axe"),
                ("UNIT_MACEMAN", "military", "infantry", "Heavy melee infantry unit"),
                ("UNIT_DMT_WARRIOR", "military", "infantry", "Special infantry unit"),
                ("UNIT_HOPLITE", "military", "infantry", "Greek heavy infantry unit"),
                # Military - Ranged
                ("UNIT_ARCHER", "military", "ranged", "Basic ranged unit"),
                ("UNIT_SLINGER", "military", "ranged", "Early ranged unit"),
                ("UNIT_CROSSBOWMAN", "military", "ranged", "Advanced ranged unit"),
                # Military - Cavalry
                ("UNIT_CHARIOT", "military", "cavalry", "Chariot unit"),
                ("UNIT_LIGHT_CHARIOT", "military", "cavalry", "Fast chariot unit"),
                (
                    "UNIT_HITTITE_CHARIOT_1",
                    "military",
                    "cavalry",
                    "Hittite unique chariot unit",
                ),
                ("UNIT_PALTON_CAVALRY", "military", "cavalry", "Cavalry unit"),
                (
                    "UNIT_AFRICAN_ELEPHANT",
                    "military",
                    "cavalry",
                    "Elephant cavalry unit",
                ),
                (
                    "UNIT_WAR_ELEPHANT",
                    "military",
                    "cavalry",
                    "War elephant cavalry unit",
                ),
                (
                    "UNIT_TURRETED_ELEPHANT",
                    "military",
                    "cavalry",
                    "Advanced elephant cavalry unit",
                ),
                # Military - Siege
                ("UNIT_ONAGER", "military", "siege", "Stone-throwing siege weapon"),
                ("UNIT_BALLISTA", "military", "siege", "Bolt-throwing siege weapon"),
                (
                    "UNIT_BATTERING_RAM",
                    "military",
                    "siege",
                    "Siege weapon for attacking cities",
                ),
                # Military - Naval
                ("UNIT_BIREME", "military", "naval", "Ancient warship"),
            ]

            insert_query = """
            INSERT INTO unit_classifications (unit_type, category, role, description)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (unit_type) DO NOTHING
            """

            conn.executemany(insert_query, classifications)

    def _create_player_points_history_table(self) -> None:
        """Create the player_points_history table."""
        query = """
        CREATE TABLE IF NOT EXISTS player_points_history (
            points_history_id BIGINT PRIMARY KEY,
            match_id BIGINT NOT NULL REFERENCES matches(match_id),
            player_id BIGINT NOT NULL REFERENCES players(player_id),
            turn_number INTEGER NOT NULL,
            points INTEGER NOT NULL,

            CONSTRAINT check_turn_number CHECK(turn_number >= 0),
            CONSTRAINT check_points CHECK(points >= 0),
            CONSTRAINT unique_points_turn UNIQUE(match_id, player_id, turn_number)
        );

        CREATE INDEX IF NOT EXISTS idx_points_history_match_player
        ON player_points_history(match_id, player_id);

        CREATE INDEX IF NOT EXISTS idx_points_history_turn
        ON player_points_history(turn_number);
        """
        with self.get_connection() as conn:
            conn.execute(query)

    def _create_player_military_history_table(self) -> None:
        """Create the player_military_history table."""
        query = """
        CREATE TABLE IF NOT EXISTS player_military_history (
            military_history_id BIGINT PRIMARY KEY,
            match_id BIGINT NOT NULL REFERENCES matches(match_id),
            player_id BIGINT NOT NULL REFERENCES players(player_id),
            turn_number INTEGER NOT NULL,
            military_power INTEGER NOT NULL,

            CONSTRAINT check_turn_number CHECK(turn_number >= 0),
            CONSTRAINT check_military_power CHECK(military_power >= 0),
            CONSTRAINT unique_military_turn UNIQUE(match_id, player_id, turn_number)
        );

        CREATE INDEX IF NOT EXISTS idx_military_history_match_player
        ON player_military_history(match_id, player_id);

        CREATE INDEX IF NOT EXISTS idx_military_history_turn
        ON player_military_history(turn_number);
        """
        with self.get_connection() as conn:
            conn.execute(query)

    def _create_player_legitimacy_history_table(self) -> None:
        """Create the player_legitimacy_history table."""
        query = """
        CREATE TABLE IF NOT EXISTS player_legitimacy_history (
            legitimacy_history_id BIGINT PRIMARY KEY,
            match_id BIGINT NOT NULL REFERENCES matches(match_id),
            player_id BIGINT NOT NULL REFERENCES players(player_id),
            turn_number INTEGER NOT NULL,
            legitimacy INTEGER NOT NULL,

            CONSTRAINT check_turn_number CHECK(turn_number >= 0),
            CONSTRAINT check_legitimacy CHECK(legitimacy >= 0 AND legitimacy <= 100),
            CONSTRAINT unique_legitimacy_turn UNIQUE(match_id, player_id, turn_number)
        );

        CREATE INDEX IF NOT EXISTS idx_legitimacy_history_match_player
        ON player_legitimacy_history(match_id, player_id);

        CREATE INDEX IF NOT EXISTS idx_legitimacy_history_turn
        ON player_legitimacy_history(turn_number);
        """
        with self.get_connection() as conn:
            conn.execute(query)

    def _create_family_opinion_history_table(self) -> None:
        """Create the family_opinion_history table."""
        query = """
        CREATE TABLE IF NOT EXISTS family_opinion_history (
            family_opinion_id BIGINT PRIMARY KEY,
            match_id BIGINT NOT NULL REFERENCES matches(match_id),
            player_id BIGINT NOT NULL REFERENCES players(player_id),
            turn_number INTEGER NOT NULL,
            family_name VARCHAR NOT NULL,
            opinion INTEGER NOT NULL,

            CONSTRAINT check_turn_number CHECK(turn_number >= 0),
            CONSTRAINT check_opinion CHECK(opinion >= 0 AND opinion <= 100),
            CONSTRAINT unique_family_opinion_turn UNIQUE(match_id, player_id, turn_number, family_name)
        );

        CREATE INDEX IF NOT EXISTS idx_family_opinion_match_player
        ON family_opinion_history(match_id, player_id);

        CREATE INDEX IF NOT EXISTS idx_family_opinion_family
        ON family_opinion_history(family_name);
        """
        with self.get_connection() as conn:
            conn.execute(query)

    def _create_religion_opinion_history_table(self) -> None:
        """Create the religion_opinion_history table."""
        query = """
        CREATE TABLE IF NOT EXISTS religion_opinion_history (
            religion_opinion_id BIGINT PRIMARY KEY,
            match_id BIGINT NOT NULL REFERENCES matches(match_id),
            player_id BIGINT NOT NULL REFERENCES players(player_id),
            turn_number INTEGER NOT NULL,
            religion_name VARCHAR NOT NULL,
            opinion INTEGER NOT NULL,

            CONSTRAINT check_turn_number CHECK(turn_number >= 0),
            CONSTRAINT check_opinion CHECK(opinion >= 0 AND opinion <= 100),
            CONSTRAINT unique_religion_opinion_turn UNIQUE(match_id, player_id, turn_number, religion_name)
        );

        CREATE INDEX IF NOT EXISTS idx_religion_opinion_match_player
        ON religion_opinion_history(match_id, player_id);

        CREATE INDEX IF NOT EXISTS idx_religion_opinion_religion
        ON religion_opinion_history(religion_name);
        """
        with self.get_connection() as conn:
            conn.execute(query)

    def _create_schema_migrations_table(self) -> None:
        """Create the schema migrations tracking table."""
        query = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(20) PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT
        );
        """
        with self.get_connection() as conn:
            conn.execute(query)

    def _create_views(self) -> None:
        """Create performance optimization views."""
        # Player performance summary view
        player_performance_query = """
        CREATE OR REPLACE VIEW player_performance AS
        SELECT
            p.player_id,
            p.player_name,
            p.civilization,
            COUNT(DISTINCT p.match_id) as total_matches,
            COUNT(CASE WHEN mw.winner_player_id = p.player_id THEN 1 END) as wins,
            ROUND(
                COUNT(CASE WHEN mw.winner_player_id = p.player_id THEN 1 END) * 100.0 /
                COUNT(DISTINCT p.match_id), 2
            ) as win_rate,
            AVG(p.final_score) as avg_score
        FROM players p
        JOIN matches m ON p.match_id = m.match_id
        LEFT JOIN match_winners mw ON p.match_id = mw.match_id
        GROUP BY p.player_id, p.player_name, p.civilization;
        """

        # Match summary statistics view
        match_summary_query = """
        CREATE OR REPLACE VIEW match_summary AS
        SELECT
            m.match_id,
            m.game_name,
            m.save_date,
            m.total_turns,
            m.map_size,
            m.victory_conditions,
            COUNT(p.player_id) as player_count,
            w.player_name as winner_name,
            w.civilization as winner_civilization
        FROM matches m
        LEFT JOIN players p ON m.match_id = p.match_id
        LEFT JOIN match_winners mw ON m.match_id = mw.match_id
        LEFT JOIN players w ON mw.winner_player_id = w.player_id
        GROUP BY m.match_id, m.game_name, m.save_date, m.total_turns,
                 m.map_size, m.victory_conditions, w.player_name, w.civilization;
        """

        with self.get_connection() as conn:
            conn.execute(player_performance_query)
            conn.execute(match_summary_query)

    def _mark_schema_version(self, version: str, description: str) -> None:
        """Mark a schema version as applied.

        Args:
            version: Version string
            description: Description of changes
        """
        query = """
        INSERT OR IGNORE INTO schema_migrations (version, description)
        VALUES (?, ?)
        """
        with self.get_connection() as conn:
            conn.execute(query, {"1": version, "2": description})

    def get_processed_files(self) -> List[Tuple[str, str]]:
        """Get list of already processed files with their hashes.

        Returns:
            List of (filename, hash) tuples
        """
        query = "SELECT file_name, file_hash FROM matches"
        return self.fetch_all(query)

    def file_already_processed(self, filename: str, file_hash: str) -> bool:
        """Check if a file has already been processed.

        Args:
            filename: Name of the file
            file_hash: SHA256 hash of the file

        Returns:
            True if file already exists in database
        """
        query = "SELECT 1 FROM matches WHERE file_name = ? AND file_hash = ?"
        result = self.fetch_one(query, {"1": filename, "2": file_hash})
        return result is not None

    def insert_match(self, match_data: Dict[str, Any]) -> int:
        """Insert a new match record.

        Args:
            match_data: Dictionary with match information

        Returns:
            ID of the inserted match
        """
        with self.get_connection() as conn:
            # Get the next sequence value for match_id
            match_id = conn.execute("SELECT nextval('matches_id_seq')").fetchone()[0]

            query = """
            INSERT INTO matches (
                match_id, challonge_match_id, file_name, file_hash, game_name, save_date,
                game_mode, map_size, map_class, map_aspect_ratio, turn_style, turn_timer,
                victory_conditions, total_turns, winner_player_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            conn.execute(
                query,
                [
                    match_id,
                    match_data.get("challonge_match_id"),
                    match_data["file_name"],
                    match_data["file_hash"],
                    match_data.get("game_name"),
                    match_data.get("save_date"),
                    match_data.get("game_mode"),
                    match_data.get("map_size"),
                    match_data.get("map_class"),
                    match_data.get("map_aspect_ratio"),
                    match_data.get("turn_style"),
                    match_data.get("turn_timer"),
                    match_data.get("victory_conditions"),
                    match_data.get("total_turns"),
                    match_data.get("winner_player_id"),
                ],
            )

            return match_id

    def insert_player(self, player_data: Dict[str, Any]) -> int:
        """Insert a new player record.

        Args:
            player_data: Dictionary with player information

        Returns:
            ID of the inserted player
        """
        with self.get_connection() as conn:
            # Get the next sequence value for player_id
            player_id = conn.execute("SELECT nextval('players_id_seq')").fetchone()[0]

            query = """
            INSERT INTO players (
                player_id, match_id, player_name, player_name_normalized, civilization, team_id, difficulty_level,
                final_score, is_human, final_turn_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            conn.execute(
                query,
                [
                    player_id,
                    player_data["match_id"],
                    player_data["player_name"],
                    player_data["player_name_normalized"],
                    player_data.get("civilization"),
                    player_data.get("team_id"),
                    player_data.get("difficulty_level"),
                    player_data.get("final_score", 0),
                    player_data.get("is_human", True),
                    player_data.get("final_turn_active"),
                ],
            )

            return player_id

    def insert_match_winner(
        self, match_id: int, winner_player_id: int, method: str = "automatic"
    ) -> None:
        """Insert a match winner record.

        Args:
            match_id: ID of the match
            winner_player_id: ID of the winning player
            method: Method used to determine winner
        """
        query = """
        INSERT INTO match_winners (match_id, winner_player_id, winner_determination_method)
        VALUES (?, ?, ?)
        """
        with self.get_connection() as conn:
            conn.execute(query, [match_id, winner_player_id, method])

    def bulk_insert_events(self, events_data: List[Dict[str, Any]]) -> None:
        """Bulk insert event records for better performance.

        Args:
            events_data: List of event dictionaries
        """
        if not events_data:
            return

        with self.get_connection() as conn:
            query = """
            INSERT INTO events (
                event_id, match_id, turn_number, event_type, player_id, description,
                x_coordinate, y_coordinate, event_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            # Prepare data for bulk insert with sequence values
            values = []
            for event in events_data:
                event_id = conn.execute("SELECT nextval('events_id_seq')").fetchone()[0]
                values.append(
                    [
                        event_id,
                        event["match_id"],
                        event["turn_number"],
                        event["event_type"],
                        event.get("player_id"),
                        event.get("description"),
                        event.get("x_coordinate"),
                        event.get("y_coordinate"),
                        event.get("event_data"),
                    ]
                )

            conn.executemany(query, values)

    def bulk_insert_territories(self, territories_data: List[Dict[str, Any]]) -> None:
        """Bulk insert territory records for better performance.

        Args:
            territories_data: List of territory dictionaries
        """
        if not territories_data:
            return

        with self.get_connection() as conn:
            query = """
            INSERT INTO territories (
                territory_id, match_id, x_coordinate, y_coordinate, turn_number,
                terrain_type, owner_player_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """

            values = []
            for territory in territories_data:
                territory_id = conn.execute(
                    "SELECT nextval('territories_id_seq')"
                ).fetchone()[0]
                values.append(
                    [
                        territory_id,
                        territory["match_id"],
                        territory["x_coordinate"],
                        territory["y_coordinate"],
                        territory["turn_number"],
                        territory.get("terrain_type"),
                        territory.get("owner_player_id"),
                    ]
                )

            conn.executemany(query, values)

    def bulk_insert_yield_history(self, yield_data: List[Dict[str, Any]]) -> None:
        """Bulk insert yield rate history records.

        Args:
            yield_data: List of yield history dictionaries
        """
        if not yield_data:
            return

        with self.get_connection() as conn:
            query = """
            INSERT INTO player_yield_history (
                resource_id, match_id, player_id, turn_number, resource_type, amount
            ) VALUES (?, ?, ?, ?, ?, ?)
            """

            values = []
            for resource in yield_data:
                resource_id = conn.execute(
                    "SELECT nextval('resources_id_seq')"
                ).fetchone()[0]
                values.append(
                    [
                        resource_id,
                        resource["match_id"],
                        resource["player_id"],
                        resource["turn_number"],
                        resource["resource_type"],
                        resource["amount"],
                    ]
                )

            conn.executemany(query, values)

    def bulk_insert_technology_progress(
        self, tech_progress_data: List[Dict[str, Any]]
    ) -> None:
        """Bulk insert technology progress records.

        Args:
            tech_progress_data: List of technology progress dictionaries
        """
        if not tech_progress_data:
            return

        with self.get_connection() as conn:
            query = """
            INSERT INTO technology_progress (
                tech_progress_id, match_id, player_id, tech_name, count
            ) VALUES (?, ?, ?, ?, ?)
            """

            values = []
            for tech in tech_progress_data:
                tech_id = conn.execute(
                    "SELECT nextval('technology_progress_id_seq')"
                ).fetchone()[0]
                values.append(
                    [
                        tech_id,
                        tech["match_id"],
                        tech["player_id"],
                        tech["tech_name"],
                        tech["count"],
                    ]
                )

            conn.executemany(query, values)

    def bulk_insert_player_statistics(
        self, statistics_data: List[Dict[str, Any]]
    ) -> None:
        """Bulk insert player statistics records.

        Args:
            statistics_data: List of player statistics dictionaries
        """
        if not statistics_data:
            return

        with self.get_connection() as conn:
            query = """
            INSERT INTO player_statistics (
                stat_id, match_id, player_id, stat_category, stat_name, value
            ) VALUES (?, ?, ?, ?, ?, ?)
            """

            values = []
            for stat in statistics_data:
                stat_id = conn.execute(
                    "SELECT nextval('player_statistics_id_seq')"
                ).fetchone()[0]
                values.append(
                    [
                        stat_id,
                        stat["match_id"],
                        stat["player_id"],
                        stat["stat_category"],
                        stat["stat_name"],
                        stat["value"],
                    ]
                )

            conn.executemany(query, values)

    def bulk_insert_units_produced(self, units_data: List[Dict[str, Any]]) -> None:
        """Bulk insert units produced records.

        Args:
            units_data: List of units produced dictionaries
        """
        if not units_data:
            return

        with self.get_connection() as conn:
            query = """
            INSERT INTO units_produced (
                unit_produced_id, match_id, player_id, unit_type, count
            ) VALUES (?, ?, ?, ?, ?)
            """

            values = []
            for unit in units_data:
                unit_id = conn.execute(
                    "SELECT nextval('units_produced_id_seq')"
                ).fetchone()[0]
                values.append(
                    [
                        unit_id,
                        unit["match_id"],
                        unit["player_id"],
                        unit["unit_type"],
                        unit["count"],
                    ]
                )

            conn.executemany(query, values)

    def insert_match_metadata(self, match_id: int, metadata: Dict[str, Any]) -> None:
        """Insert match metadata record.

        Args:
            match_id: ID of the match
            metadata: Dictionary with match metadata
        """
        if not metadata:
            return

        with self.get_connection() as conn:
            query = """
            INSERT INTO match_metadata (
                match_id, difficulty, event_level, victory_type, victory_turn,
                game_options, dlc_content, map_settings
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """

            conn.execute(
                query,
                [
                    match_id,
                    metadata.get("difficulty"),
                    metadata.get("event_level"),
                    metadata.get("victory_type"),
                    metadata.get("victory_turn"),
                    metadata.get("game_options"),
                    metadata.get("dlc_content"),
                    metadata.get("map_settings"),
                ],
            )

    def bulk_insert_points_history(self, points_data: List[Dict[str, Any]]) -> None:
        """Bulk insert points history records.

        Args:
            points_data: List of points history dictionaries
        """
        if not points_data:
            return

        with self.get_connection() as conn:
            query = """
            INSERT INTO player_points_history (
                points_history_id, match_id, player_id, turn_number, points
            ) VALUES (?, ?, ?, ?, ?)
            """

            values = []
            for point in points_data:
                points_id = conn.execute(
                    "SELECT nextval('points_history_id_seq')"
                ).fetchone()[0]
                values.append(
                    [
                        points_id,
                        point["match_id"],
                        point["player_id"],
                        point["turn_number"],
                        point["points"],
                    ]
                )

            conn.executemany(query, values)

    def bulk_insert_military_history(
        self, military_data: List[Dict[str, Any]]
    ) -> None:
        """Bulk insert military power history records.

        Args:
            military_data: List of military history dictionaries
        """
        if not military_data:
            return

        with self.get_connection() as conn:
            query = """
            INSERT INTO player_military_history (
                military_history_id, match_id, player_id, turn_number, military_power
            ) VALUES (?, ?, ?, ?, ?)
            """

            values = []
            for military in military_data:
                military_id = conn.execute(
                    "SELECT nextval('military_history_id_seq')"
                ).fetchone()[0]
                values.append(
                    [
                        military_id,
                        military["match_id"],
                        military["player_id"],
                        military["turn_number"],
                        military["military_power"],
                    ]
                )

            conn.executemany(query, values)

    def bulk_insert_legitimacy_history(
        self, legitimacy_data: List[Dict[str, Any]]
    ) -> None:
        """Bulk insert legitimacy history records.

        Args:
            legitimacy_data: List of legitimacy history dictionaries
        """
        if not legitimacy_data:
            return

        with self.get_connection() as conn:
            query = """
            INSERT INTO player_legitimacy_history (
                legitimacy_history_id, match_id, player_id, turn_number, legitimacy
            ) VALUES (?, ?, ?, ?, ?)
            """

            values = []
            for legitimacy in legitimacy_data:
                legitimacy_id = conn.execute(
                    "SELECT nextval('legitimacy_history_id_seq')"
                ).fetchone()[0]
                values.append(
                    [
                        legitimacy_id,
                        legitimacy["match_id"],
                        legitimacy["player_id"],
                        legitimacy["turn_number"],
                        legitimacy["legitimacy"],
                    ]
                )

            conn.executemany(query, values)

    def bulk_insert_family_opinion_history(
        self, family_data: List[Dict[str, Any]]
    ) -> None:
        """Bulk insert family opinion history records.

        Args:
            family_data: List of family opinion history dictionaries
        """
        if not family_data:
            return

        with self.get_connection() as conn:
            query = """
            INSERT INTO family_opinion_history (
                family_opinion_id, match_id, player_id, turn_number, family_name, opinion
            ) VALUES (?, ?, ?, ?, ?, ?)
            """

            values = []
            for family in family_data:
                family_id = conn.execute(
                    "SELECT nextval('family_opinion_id_seq')"
                ).fetchone()[0]
                values.append(
                    [
                        family_id,
                        family["match_id"],
                        family["player_id"],
                        family["turn_number"],
                        family["family_name"],
                        family["opinion"],
                    ]
                )

            conn.executemany(query, values)

    def bulk_insert_religion_opinion_history(
        self, religion_data: List[Dict[str, Any]]
    ) -> None:
        """Bulk insert religion opinion history records.

        Args:
            religion_data: List of religion opinion history dictionaries
        """
        if not religion_data:
            return

        with self.get_connection() as conn:
            query = """
            INSERT INTO religion_opinion_history (
                religion_opinion_id, match_id, player_id, turn_number, religion_name, opinion
            ) VALUES (?, ?, ?, ?, ?, ?)
            """

            values = []
            for religion in religion_data:
                religion_id = conn.execute(
                    "SELECT nextval('religion_opinion_id_seq')"
                ).fetchone()[0]
                values.append(
                    [
                        religion_id,
                        religion["match_id"],
                        religion["player_id"],
                        religion["turn_number"],
                        religion["religion_name"],
                        religion["opinion"],
                    ]
                )

            conn.executemany(query, values)


# Global database instance
db = TournamentDatabase()


def get_database() -> TournamentDatabase:
    """Get the global database instance.

    Returns:
        TournamentDatabase instance
    """
    return db
