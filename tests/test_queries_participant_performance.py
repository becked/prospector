"""Tests for participant-aware player performance queries."""

import pytest
import pandas as pd
from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.queries import TournamentQueries


@pytest.fixture
def test_db(tmp_path):
    """Create test database with participant and player data."""
    db_path = tmp_path / "test.duckdb"

    # Create database - schema creation will run after migration in read-write mode
    # The migration checks for existing migration in schema_migrations table
    # We create schema first manually by temporarily setting read_only during init
    import duckdb
    conn = duckdb.connect(str(db_path))

    # Create basic schema manually to satisfy migration FK constraints
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(20) PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT
        )
    """)

    # Mark migration as already applied to skip it
    conn.execute("""
        INSERT INTO schema_migrations (version, description)
        VALUES ('4', 'Add tournament participant tracking')
    """)
    conn.close()

    # Now open with TournamentDatabase which will skip migration
    db = TournamentDatabase(str(db_path), read_only=False)
    db.create_schema()

    with db.get_connection() as conn:
        # Insert test participants
        conn.execute("""
            INSERT INTO tournament_participants (
                participant_id, display_name, display_name_normalized
            ) VALUES
            (1001, 'LinkedPlayer1', 'linkedplayer1'),
            (1002, 'LinkedPlayer2', 'linkedplayer2')
        """)

        # Insert test matches
        conn.execute("""
            INSERT INTO matches (match_id, challonge_match_id, file_name, file_hash, total_turns)
            VALUES
            (100, 426504750, 'match1.zip', 'hash1', 50),
            (101, 426504751, 'match2.zip', 'hash2', 75)
        """)

        # Insert test players - mix of linked and unlinked
        conn.execute("""
            INSERT INTO players (
                player_id, match_id, player_name, player_name_normalized,
                participant_id, civilization, final_score
            ) VALUES
            -- Linked player, two matches, two different civs
            (1, 100, 'LinkedPlayer1', 'linkedplayer1', 1001, 'Rome', 500),
            (2, 101, 'LinkedPlayer1', 'linkedplayer1', 1001, 'Assyria', 600),
            -- Linked player, one match
            (3, 100, 'LinkedPlayer2', 'linkedplayer2', 1002, 'Babylon', 450),
            -- Unlinked player (name case variation)
            (4, 101, 'UnlinkedPlayer', 'unlinkedplayer', NULL, 'Egypt', 400),
            (5, 100, 'unlinkedplayer', 'unlinkedplayer', NULL, 'Greece', 350)
        """)

        # Insert match winners
        conn.execute("""
            INSERT INTO match_winners (match_id, winner_player_id)
            VALUES
            (100, 1),  -- LinkedPlayer1 wins match 100
            (101, 2)   -- LinkedPlayer1 wins match 101
        """)

    yield db
    db.close()


class TestPlayerPerformanceParticipantAware:
    """Tests for get_player_performance() with participant tracking."""

    def test_linked_player_appears_once(self, test_db):
        """Linked player should appear as one row despite multiple matches."""
        queries = TournamentQueries(test_db)
        df = queries.get_player_performance()

        # LinkedPlayer1 should appear once, not twice
        linked_players = df[df['player_name'] == 'LinkedPlayer1']
        assert len(linked_players) == 1

        row = linked_players.iloc[0]
        assert row['participant_id'] == 1001
        assert row['total_matches'] == 2
        assert row['wins'] == 2
        assert row['win_rate'] == 100.0
        assert row['is_unlinked'] == False

    def test_linked_player_shows_multiple_civs(self, test_db):
        """Linked player who used multiple civs should list all civs."""
        queries = TournamentQueries(test_db)
        df = queries.get_player_performance()

        linked_players = df[df['player_name'] == 'LinkedPlayer1']
        row = linked_players.iloc[0]

        # Should show both civs (order may vary)
        civs = row['civilizations_played']
        assert 'Rome' in civs
        assert 'Assyria' in civs

        # Favorite should be one of them
        assert row['favorite_civilization'] in ['Rome', 'Assyria']

    def test_unlinked_player_groups_by_normalized_name(self, test_db):
        """Unlinked players with name variations should collapse to one row."""
        queries = TournamentQueries(test_db)
        df = queries.get_player_performance()

        # Should have one row for unlinkedplayer (not two)
        unlinked_players = df[df['player_name'].str.lower() == 'unlinkedplayer']
        assert len(unlinked_players) == 1

        row = unlinked_players.iloc[0]
        assert pd.isna(row['participant_id']) or row['participant_id'] is None
        assert row['is_unlinked'] == True
        assert row['total_matches'] == 2

    def test_unlinked_player_marked_correctly(self, test_db):
        """Unlinked players should have is_unlinked=True."""
        queries = TournamentQueries(test_db)
        df = queries.get_player_performance()

        unlinked = df[df['is_unlinked'] == True]
        assert len(unlinked) >= 1

        # All unlinked should have NULL participant_id
        assert all(pd.isna(unlinked['participant_id']))

    def test_linked_player_marked_correctly(self, test_db):
        """Linked players should have is_unlinked=False."""
        queries = TournamentQueries(test_db)
        df = queries.get_player_performance()

        linked = df[df['is_unlinked'] == False]
        assert len(linked) >= 1

        # All linked should have non-NULL participant_id
        assert all(pd.notna(linked['participant_id']))

    def test_win_rate_calculation(self, test_db):
        """Win rate should calculate correctly across matches."""
        queries = TournamentQueries(test_db)
        df = queries.get_player_performance()

        # LinkedPlayer1: 2 matches, 2 wins = 100%
        lp1 = df[df['player_name'] == 'LinkedPlayer1'].iloc[0]
        assert lp1['win_rate'] == 100.0

        # LinkedPlayer2: 1 match, 0 wins = 0%
        lp2 = df[df['player_name'] == 'LinkedPlayer2'].iloc[0]
        assert lp2['win_rate'] == 0.0

    def test_score_aggregation(self, test_db):
        """Score stats should aggregate correctly."""
        queries = TournamentQueries(test_db)
        df = queries.get_player_performance()

        lp1 = df[df['player_name'] == 'LinkedPlayer1'].iloc[0]
        assert lp1['max_score'] == 600
        assert lp1['min_score'] == 500
        assert lp1['avg_score'] == 550.0  # (500 + 600) / 2

    def test_returns_expected_columns(self, test_db):
        """Result should have all expected columns."""
        queries = TournamentQueries(test_db)
        df = queries.get_player_performance()

        expected_columns = [
            'player_name',
            'participant_id',
            'is_unlinked',
            'total_matches',
            'wins',
            'win_rate',
            'avg_score',
            'max_score',
            'min_score',
            'civilizations_played',
            'favorite_civilization'
        ]

        for col in expected_columns:
            assert col in df.columns, f"Missing column: {col}"

    def test_empty_database(self, tmp_path):
        """Query should handle empty database gracefully."""
        db_path = tmp_path / "empty.duckdb"

        # Same setup as main fixture to avoid migration issues
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

        df = queries.get_player_performance()
        assert df.empty
        db.close()


class TestPlayerPerformanceEdgeCases:
    """Test edge cases and data quality scenarios."""

    def test_player_with_null_civilization(self, test_db):
        """Players with NULL civilization should not break query."""
        # Add player with NULL civ
        with test_db.get_connection() as conn:
            conn.execute("""
                INSERT INTO players (
                    player_id, match_id, player_name, player_name_normalized,
                    participant_id, civilization, final_score
                ) VALUES
                (99, 100, 'NoCivPlayer', 'nocivplayer', 1001, NULL, 300)
            """)

        queries = TournamentQueries(test_db)
        df = queries.get_player_performance()

        # Should not raise error
        assert not df.empty

    def test_sorting_order(self, test_db):
        """Results should be sorted by win_rate DESC, total_matches DESC."""
        queries = TournamentQueries(test_db)
        df = queries.get_player_performance()

        # First row should have highest win_rate
        # If tied, should have most matches
        assert df.iloc[0]['win_rate'] >= df.iloc[1]['win_rate']
