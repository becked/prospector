"""Integration tests for ETL participant linking flow.

Tests the full flow of:
1. Creating database with participants
2. Importing save files (ETL)
3. Automatic participant linking
4. Verifying linkages
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.etl import import_all_files


@pytest.fixture
def test_db_with_participants(tmp_path):
    """Create a test database with participant data."""
    db_path = tmp_path / "test.duckdb"
    db = TournamentDatabase(str(db_path))

    # Insert test participants
    db.conn.execute("""
        INSERT INTO tournament_participants (
            participant_id, display_name, display_name_normalized
        ) VALUES
        (1001, 'TestPlayer1', 'testplayer1'),
        (1002, 'TestPlayer2', 'testplayer2'),
        (1003, 'TestPlayer3', 'testplayer3')
    """)

    yield db
    db.close()


@pytest.fixture
def mock_save_files(tmp_path):
    """Create mock save file directory."""
    saves_dir = tmp_path / "saves"
    saves_dir.mkdir()

    # Create dummy save files
    (saves_dir / "match1.zip").write_text("dummy")
    (saves_dir / "match2.zip").write_text("dummy")

    return saves_dir


class TestETLParticipantLinking:
    """Tests for ETL participant linking integration."""

    def test_etl_links_participants_when_available(
        self, test_db_with_participants, mock_save_files
    ):
        """Test that ETL automatically links participants when they exist."""
        # Mock the actual save file processing to insert test players
        def mock_process_file(file_path, db):
            # Simulate creating players during save file import
            match_id = 1 if "match1" in str(file_path) else 2
            db.conn.execute("""
                INSERT INTO matches (match_id, challonge_match_id, file_name, file_hash)
                VALUES (?, ?, ?, ?)
            """, (match_id, match_id * 1000, Path(file_path).name, f"hash{match_id}"))

            db.conn.execute("""
                INSERT INTO players (
                    player_id, match_id, player_name, player_name_normalized
                ) VALUES
                (?, ?, 'TestPlayer1', 'testplayer1'),
                (?, ?, 'TestPlayer2', 'testplayer2')
            """, (match_id * 10 + 1, match_id, match_id * 10 + 2, match_id))

        with patch('tournament_visualizer.data.etl.process_tournament_file', side_effect=mock_process_file):
            # Run ETL import
            results = import_all_files(
                str(mock_save_files),
                test_db_with_participants
            )

        # Verify participant linking occurred
        assert results.get('participant_linking') is not None
        link_stats = results['participant_linking']

        # Should have linked 4 players total (2 per match)
        assert link_stats['total_players'] == 4
        assert link_stats['matched_players'] == 4
        assert link_stats['unmatched_players'] == 0

    def test_etl_skips_linking_when_no_participants(
        self, tmp_path, mock_save_files
    ):
        """Test that ETL skips linking when no participants exist."""
        # Create DB without participants
        db_path = tmp_path / "test.duckdb"
        db = TournamentDatabase(str(db_path))

        def mock_process_file(file_path, db):
            match_id = 1
            db.conn.execute("""
                INSERT INTO matches (match_id, challonge_match_id, file_name, file_hash)
                VALUES (?, ?, ?, ?)
            """, (match_id, match_id * 1000, Path(file_path).name, f"hash{match_id}"))

        with patch('tournament_visualizer.data.etl.process_tournament_file', side_effect=mock_process_file):
            results = import_all_files(
                str(mock_save_files),
                db
            )

        # Should skip participant linking
        assert results.get('participant_linking') is None

        db.close()

    def test_etl_handles_partial_matches(
        self, test_db_with_participants, mock_save_files
    ):
        """Test ETL handles cases where some players don't match."""
        def mock_process_file(file_path, db):
            match_id = 1
            db.conn.execute("""
                INSERT INTO matches (match_id, challonge_match_id, file_name, file_hash)
                VALUES (?, ?, ?, ?)
            """, (match_id, match_id * 1000, Path(file_path).name, f"hash{match_id}"))

            # One player matches, one doesn't
            db.conn.execute("""
                INSERT INTO players (
                    player_id, match_id, player_name, player_name_normalized
                ) VALUES
                (1, 1, 'TestPlayer1', 'testplayer1'),
                (2, 1, 'UnknownPlayer', 'unknownplayer')
            """)

        with patch('tournament_visualizer.data.etl.process_tournament_file', side_effect=mock_process_file):
            results = import_all_files(
                str(mock_save_files),
                test_db_with_participants
            )

        # Verify partial matching
        link_stats = results['participant_linking']
        assert link_stats['total_players'] == 2
        assert link_stats['matched_players'] == 1
        assert link_stats['unmatched_players'] == 1
        assert 'UnknownPlayer' in link_stats['unmatched_by_match'].get(1, [])

    def test_etl_linking_uses_overrides(
        self, test_db_with_participants, mock_save_files
    ):
        """Test that ETL participant linking respects manual overrides."""
        # Add an override
        test_db_with_participants.conn.execute("""
            INSERT INTO participant_name_overrides (
                match_id, save_file_player_name, participant_id, reason
            ) VALUES (1, 'WrongName', 1003, 'Test override')
        """)

        def mock_process_file(file_path, db):
            match_id = 1
            db.conn.execute("""
                INSERT INTO matches (match_id, challonge_match_id, file_name, file_hash)
                VALUES (?, ?, ?, ?)
            """, (match_id, match_id * 1000, Path(file_path).name, f"hash{match_id}"))

            db.conn.execute("""
                INSERT INTO players (
                    player_id, match_id, player_name, player_name_normalized
                ) VALUES
                (1, 1, 'WrongName', 'wrongname')
            """)

        with patch('tournament_visualizer.data.etl.process_tournament_file', side_effect=mock_process_file):
            results = import_all_files(
                str(mock_save_files),
                test_db_with_participants
            )

        # Verify override was used
        link_stats = results['participant_linking']
        assert link_stats['matched_players'] == 1

        # Check that player was linked to participant 1003 (from override)
        player_participant = test_db_with_participants.conn.execute("""
            SELECT participant_id
            FROM players
            WHERE player_name = 'WrongName'
        """).fetchone()

        assert player_participant[0] == 1003

    def test_etl_continues_on_linking_error(
        self, test_db_with_participants, mock_save_files
    ):
        """Test that ETL continues if participant linking fails."""
        def mock_process_file(file_path, db):
            match_id = 1
            db.conn.execute("""
                INSERT INTO matches (match_id, challonge_match_id, file_name, file_hash)
                VALUES (?, ?, ?, ?)
            """, (match_id, match_id * 1000, Path(file_path).name, f"hash{match_id}"))

        # Mock participant matcher to raise an error
        with patch('tournament_visualizer.data.etl.process_tournament_file', side_effect=mock_process_file):
            with patch('tournament_visualizer.data.etl.ParticipantMatcher') as mock_matcher:
                mock_matcher.return_value.link_all_matches.side_effect = Exception("Test error")

                # Should not raise, should continue
                results = import_all_files(
                    str(mock_save_files),
                    test_db_with_participants
                )

        # Linking should be None (failed)
        assert results.get('participant_linking') is None

    def test_full_etl_flow_integration(
        self, test_db_with_participants, mock_save_files
    ):
        """Full integration test of ETL flow with participant linking."""
        def mock_process_file(file_path, db):
            match_id = 1 if "match1" in str(file_path) else 2

            # Create match
            db.conn.execute("""
                INSERT INTO matches (
                    match_id,
                    challonge_match_id,
                    file_name,
                    file_hash,
                    player1_participant_id,
                    player2_participant_id
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (match_id, match_id * 1000, Path(file_path).name, f"hash{match_id}", 1001, 1002))

            # Create players
            db.conn.execute("""
                INSERT INTO players (
                    player_id, match_id, player_name, player_name_normalized
                ) VALUES
                (?, ?, 'TestPlayer1', 'testplayer1'),
                (?, ?, 'TestPlayer2', 'testplayer2')
            """, (match_id * 10 + 1, match_id, match_id * 10 + 2, match_id))

        with patch('tournament_visualizer.data.etl.process_tournament_file', side_effect=mock_process_file):
            results = import_all_files(
                str(mock_save_files),
                test_db_with_participants
            )

        # Verify ETL completed successfully
        assert 'participant_linking' in results

        # Verify database state
        total_players = test_db_with_participants.conn.execute(
            "SELECT COUNT(*) FROM players"
        ).fetchone()[0]
        assert total_players == 4

        linked_players = test_db_with_participants.conn.execute(
            "SELECT COUNT(*) FROM players WHERE participant_id IS NOT NULL"
        ).fetchone()[0]
        assert linked_players == 4

        # Verify linkages are correct
        player1_links = test_db_with_participants.conn.execute("""
            SELECT COUNT(DISTINCT participant_id)
            FROM players
            WHERE player_name = 'TestPlayer1'
        """).fetchone()[0]

        # TestPlayer1 appears in 2 matches but should link to same participant
        assert player1_links == 1


class TestETLParticipantLinkingReporting:
    """Tests for ETL participant linking result reporting."""

    def test_import_summary_includes_linking_stats(
        self, test_db_with_participants, mock_save_files, capsys
    ):
        """Test that import summary includes participant linking stats."""
        def mock_process_file(file_path, db):
            match_id = 1
            db.conn.execute("""
                INSERT INTO matches (match_id, challonge_match_id, file_name, file_hash)
                VALUES (?, ?, ?, ?)
            """, (match_id, match_id * 1000, Path(file_path).name, f"hash{match_id}"))

            db.conn.execute("""
                INSERT INTO players (
                    player_id, match_id, player_name, player_name_normalized
                ) VALUES
                (1, 1, 'TestPlayer1', 'testplayer1')
            """)

        with patch('tournament_visualizer.data.etl.process_tournament_file', side_effect=mock_process_file):
            results = import_all_files(
                str(mock_save_files),
                test_db_with_participants
            )

            # Print summary (assuming there's a print_import_summary function)
            from tournament_visualizer.data.etl import print_import_summary
            print_import_summary(results)

        captured = capsys.readouterr()

        # Verify linking stats appear in output
        assert 'Participant Linking' in captured.out or 'participant' in captured.out.lower()
        assert 'matched' in captured.out.lower()
