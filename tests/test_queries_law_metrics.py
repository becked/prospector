"""Tests for law metrics queries.

Test Strategy:
- Test event-based law counting (source of truth)
- Test unique law pairs counting
- Test law switching calculation
- Test milestone timing calculations
- Use TournamentDatabase with known data
"""

import pytest

from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.queries import TournamentQueries


class TestLawMetricsQueries:
    """Test law counting logic."""

    @pytest.fixture
    def law_test_db(self, tmp_path):
        """Create database with sample law data.

        Scenario:
        - Match 1 with 2 players
        - Player 1: Adopts 3 laws, switches 1 (total 4 events, 3 unique)
        - Player 2: Adopts 2 laws, no switches (total 2 events, 2 unique)
        """
        db_path = tmp_path / "law_test.duckdb"

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
            VALUES ('1', 'Initial schema')
        """)
        conn.close()

        db = TournamentDatabase(str(db_path), read_only=False)
        db.create_schema()

        with db.get_connection() as conn:
            # Insert test match
            conn.execute("""
                INSERT INTO matches (match_id, file_name, file_hash, game_name, total_turns)
                VALUES (1, 'test_match.zip', 'test_hash_123', 'Test Match', 100)
            """)

            # Insert test players
            conn.execute("""
                INSERT INTO players (player_id, match_id, player_name, player_name_normalized, civilization)
                VALUES
                    (1, 1, 'Player1', 'player1', 'Rome'),
                    (2, 1, 'Player2', 'player2', 'Greece')
            """)

            # Insert law adoption events
            # Player 1: Adopts Serfdom (turn 20), Slavery (turn 30),
            #           Switches to Colonies (turn 40), Adopts Monotheism (turn 50)
            # Total: 4 events, 3 unique law pairs
            conn.execute("""
                INSERT INTO events (event_id, match_id, player_id, turn_number, event_type, event_data)
                VALUES
                    (1, 1, 1, 20, 'LAW_ADOPTED', '{"law": "LAW_SERFDOM"}'),
                    (2, 1, 1, 30, 'LAW_ADOPTED', '{"law": "LAW_SLAVERY"}'),
                    (3, 1, 1, 40, 'LAW_ADOPTED', '{"law": "LAW_COLONIES"}'),
                    (4, 1, 1, 50, 'LAW_ADOPTED', '{"law": "LAW_MONOTHEISM"}'),
                    (5, 1, 2, 25, 'LAW_ADOPTED', '{"law": "LAW_TYRANNY"}'),
                    (6, 1, 2, 35, 'LAW_ADOPTED', '{"law": "LAW_EPICS"}')
            """)

            # Insert player_statistics (unique law pairs)
            # Player 1: 3 unique law pairs (Colonies/Serfdom counted once)
            # Player 2: 2 unique law pairs
            conn.execute("""
                INSERT INTO player_statistics (stat_id, match_id, player_id, stat_category, stat_name, value)
                VALUES
                    (1, 1, 1, 'law_changes', 'LAWCLASS_COLONIES_SERFDOM', 1),
                    (2, 1, 1, 'law_changes', 'LAWCLASS_SLAVERY_FREEDOM', 1),
                    (3, 1, 1, 'law_changes', 'LAWCLASS_MONOTHEISM_POLYTHEISM', 1),
                    (4, 1, 2, 'law_changes', 'LAWCLASS_TYRANNY_CONSTITUTION', 1),
                    (5, 1, 2, 'law_changes', 'LAWCLASS_EPICS_EXPLORATION', 1)
            """)

        return db

    def test_get_total_laws_returns_event_based_count(self, law_test_db: TournamentDatabase) -> None:
        """Should count laws from events table, not statistics."""
        queries = TournamentQueries(law_test_db)

        df = queries.get_total_laws_by_player(match_id=1)

        assert 'total_laws_adopted' in df.columns
        assert 'unique_law_pairs' in df.columns
        assert 'law_switches' in df.columns
        assert len(df) == 2  # Two players

    def test_law_switches_calculated_correctly(self, law_test_db: TournamentDatabase) -> None:
        """Law switches should be total_laws - unique_pairs."""
        queries = TournamentQueries(law_test_db)

        df = queries.get_total_laws_by_player(match_id=1)

        # Player 1: 4 events - 3 unique = 1 switch
        player1 = df[df['player_name'] == 'Player1'].iloc[0]
        assert player1['total_laws_adopted'] == 4
        assert player1['unique_law_pairs'] == 3
        assert player1['law_switches'] == 1

        # Player 2: 2 events - 2 unique = 0 switches
        player2 = df[df['player_name'] == 'Player2'].iloc[0]
        assert player2['total_laws_adopted'] == 2
        assert player2['unique_law_pairs'] == 2
        assert player2['law_switches'] == 0

    def test_handles_players_with_no_switches(self, law_test_db: TournamentDatabase) -> None:
        """Players who never switched should have law_switches=0."""
        queries = TournamentQueries(law_test_db)

        df = queries.get_total_laws_by_player(match_id=1)

        # At least one player should have no switches
        assert (df['law_switches'] == 0).any()

    def test_get_law_milestone_timing_uses_events(self, law_test_db: TournamentDatabase) -> None:
        """Milestone timing should use event-based counts."""
        queries = TournamentQueries(law_test_db)

        df = queries.get_law_milestone_timing()

        assert not df.empty
        assert 'total_laws' in df.columns
        assert 'turns_per_law' in df.columns

        # Player 1: 4 laws, so can estimate milestone for 4 laws
        player1 = df[df['player_name'] == 'Player1'].iloc[0]
        assert player1['total_laws'] == 4
        assert player1['estimated_turn_to_4_laws'] is not None

        # Player 2: 2 laws, cannot estimate 4 laws milestone
        player2 = df[df['player_name'] == 'Player2'].iloc[0]
        assert player2['total_laws'] == 2
        # estimated_turn_to_4_laws should be NULL for player with < 4 laws
        # Check for None, NaN, or pandas <NA>
        import pandas as pd
        assert pd.isna(player2['estimated_turn_to_4_laws'])

    def test_get_player_law_progression_stats_uses_events(self, law_test_db: TournamentDatabase) -> None:
        """Player progression stats should use event-based counts."""
        queries = TournamentQueries(law_test_db)

        df = queries.get_player_law_progression_stats()

        assert not df.empty
        assert 'avg_laws_per_game' in df.columns
        assert 'max_laws' in df.columns
        assert 'min_laws' in df.columns

        # Player 1 should show 4 laws
        player1 = df[df['player_name'] == 'Player1'].iloc[0]
        assert player1['max_laws'] == 4
        assert player1['avg_laws_per_game'] == 4.0

        # Player 2 should show 2 laws
        player2 = df[df['player_name'] == 'Player2'].iloc[0]
        assert player2['max_laws'] == 2
        assert player2['avg_laws_per_game'] == 2.0

    def test_query_filters_players_with_no_laws(self, law_test_db: TournamentDatabase) -> None:
        """Queries should only return players who adopted at least one law."""
        queries = TournamentQueries(law_test_db)

        with law_test_db.get_connection() as conn:
            # Add a player with no law events
            conn.execute("""
                INSERT INTO players (player_id, match_id, player_name, player_name_normalized, civilization)
                VALUES (3, 1, 'Player3', 'player3', 'Egypt')
            """)

        df = queries.get_total_laws_by_player(match_id=1)

        # Should only return players with laws
        assert len(df) == 2
        assert 'Player3' not in df['player_name'].values
