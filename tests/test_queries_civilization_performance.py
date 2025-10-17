"""Tests for civilization performance query with participant awareness."""

import pytest

from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.queries import TournamentQueries


@pytest.fixture
def civ_test_db(tmp_path):
    """Create test database with civilization data."""
    db_path = tmp_path / "civ_test.duckdb"

    # Create database with schema - same pattern as other tests
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
        VALUES ('4', 'Add tournament participant tracking')
    """)
    conn.close()

    db = TournamentDatabase(str(db_path), read_only=False)
    db.create_schema()

    with db.get_connection() as conn:
        # Insert participant
        conn.execute("""
            INSERT INTO tournament_participants (
                participant_id, display_name, display_name_normalized
            ) VALUES (4001, 'CivPlayer', 'civplayer')
        """)

        # Insert matches
        conn.execute("""
            INSERT INTO matches (match_id, challonge_match_id, file_name, file_hash, total_turns)
            VALUES
            (400, 426504750, 'm1.zip', 'h1', 50),
            (401, 426504751, 'm2.zip', 'h2', 60)
        """)

        # Same person plays Rome twice (linked)
        conn.execute("""
            INSERT INTO players (
                player_id, match_id, player_name, player_name_normalized,
                participant_id, civilization, final_score
            ) VALUES
            (1, 400, 'CivPlayer', 'civplayer', 4001, 'Rome', 500),
            (2, 401, 'CivPlayer', 'civplayer', 4001, 'Rome', 600)
        """)

        # Different unlinked person also plays Rome
        conn.execute("""
            INSERT INTO players (
                player_id, match_id, player_name, player_name_normalized,
                participant_id, civilization, final_score
            ) VALUES
            (3, 400, 'UnlinkedRome', 'unlinkedrome', NULL, 'Rome', 450)
        """)

    yield db
    db.close()


class TestCivilizationPerformanceParticipantAware:
    """Tests for civilization performance with participant awareness."""

    def test_counts_unique_participants_not_instances(self, civ_test_db):
        """Should count unique people, not player instances."""
        queries = TournamentQueries(civ_test_db)
        df = queries.get_civilization_performance()

        rome_stats = df[df['civilization'] == 'Rome'].iloc[0]

        # 3 player instances total
        assert rome_stats['total_matches'] == 2  # Only 2 matches

        # 2 unique people: 1 linked participant + 1 unlinked player
        assert rome_stats['unique_participants'] == 2
        assert rome_stats['unique_linked_participants'] == 1
        assert rome_stats['unique_unlinked_players'] == 1

    def test_multiple_civs_by_same_participant(self, tmp_path):
        """Participant playing multiple civs should count for each civ."""
        db_path = tmp_path / "multi_civ.duckdb"

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
            VALUES ('4', 'Add tournament participant tracking')
        """)
        conn.close()

        db = TournamentDatabase(str(db_path), read_only=False)
        db.create_schema()

        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO tournament_participants (
                    participant_id, display_name, display_name_normalized
                ) VALUES (5001, 'MultiCivPlayer', 'multicivplayer')
            """)

            conn.execute("""
                INSERT INTO matches (match_id, challonge_match_id, file_name, file_hash, total_turns)
                VALUES
                (500, 426504750, 'm1.zip', 'h1', 50),
                (501, 426504751, 'm2.zip', 'h2', 60)
            """)

            # Same person plays different civs
            conn.execute("""
                INSERT INTO players (
                    player_id, match_id, player_name, player_name_normalized,
                    participant_id, civilization, final_score
                ) VALUES
                (1, 500, 'MultiCivPlayer', 'multicivplayer', 5001, 'Rome', 500),
                (2, 501, 'MultiCivPlayer', 'multicivplayer', 5001, 'Assyria', 600)
            """)

        queries = TournamentQueries(db)
        df = queries.get_civilization_performance()

        # Should appear in both civilizations
        assert len(df) == 2
        assert 'Rome' in df['civilization'].values
        assert 'Assyria' in df['civilization'].values

        # Each civ should count this participant
        for _, row in df.iterrows():
            assert row['unique_participants'] == 1

        db.close()

    def test_returns_expected_columns(self, civ_test_db):
        """Result should have all expected columns."""
        queries = TournamentQueries(civ_test_db)
        df = queries.get_civilization_performance()

        expected_columns = [
            'civilization',
            'total_matches',
            'wins',
            'win_rate',
            'avg_score',
            'unique_participants',
            'unique_linked_participants',
            'unique_unlinked_players',
        ]

        for col in expected_columns:
            assert col in df.columns, f"Missing column: {col}"

    def test_empty_database(self, tmp_path):
        """Query should handle empty database gracefully."""
        db_path = tmp_path / "empty.duckdb"

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
            VALUES ('4', 'Add tournament participant tracking')
        """)
        conn.close()

        db = TournamentDatabase(str(db_path), read_only=False)
        db.create_schema()
        queries = TournamentQueries(db)

        df = queries.get_civilization_performance()
        assert df.empty
        db.close()

    def test_data_quality_columns_sum_correctly(self, civ_test_db):
        """Linked + unlinked should equal total unique participants."""
        queries = TournamentQueries(civ_test_db)
        df = queries.get_civilization_performance()

        for _, row in df.iterrows():
            total = row['unique_linked_participants'] + row['unique_unlinked_players']
            assert total == row['unique_participants'], \
                f"Mismatch for {row['civilization']}: {row['unique_linked_participants']} + " \
                f"{row['unique_unlinked_players']} != {row['unique_participants']}"
