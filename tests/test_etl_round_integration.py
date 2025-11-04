"""Test ETL integration with tournament round tracking."""

import tempfile
from pathlib import Path
from typing import Dict

import pytest

from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.etl import TournamentETL


class TestETLRoundIntegration:
    """Test tournament round integration in ETL pipeline."""

    @pytest.fixture
    def temp_db(self) -> TournamentDatabase:
        """Create temporary test database."""
        with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False) as f:
            db_path = f.name

        # Remove file so DuckDB can create fresh database
        Path(db_path).unlink()

        db = TournamentDatabase(db_path, read_only=False)
        db.create_schema()
        yield db
        db.close()

        # Cleanup
        Path(db_path).unlink(missing_ok=True)

    @pytest.fixture
    def sample_save_file(self) -> Path:
        """Path to a real save file for testing."""
        # Use an existing save file from saves/
        save_file = Path("saves/match_426504721_anarkos-becked.zip")

        if not save_file.exists():
            pytest.skip("No save files available for testing")

        return save_file

    def test_round_cache_initialization(self, temp_db: TournamentDatabase) -> None:
        """Test ETL accepts round_cache parameter."""
        # ARRANGE
        round_cache = {426504730: 1, 426504731: 2}

        # ACT
        etl = TournamentETL(database=temp_db, round_cache=round_cache)

        # ASSERT
        assert etl.round_cache == round_cache

    def test_round_cache_defaults_empty(self, temp_db: TournamentDatabase) -> None:
        """Test ETL uses empty dict if no cache provided."""
        # ACT
        etl = TournamentETL(database=temp_db)

        # ASSERT
        assert etl.round_cache == {}

    def test_round_added_to_match_metadata(
        self, temp_db: TournamentDatabase, sample_save_file: Path
    ) -> None:
        """Test that tournament_round is added from cache during import."""
        # ARRANGE
        challonge_id = 426504721
        expected_round = 3
        round_cache = {challonge_id: expected_round}

        etl = TournamentETL(database=temp_db, round_cache=round_cache)

        # ACT
        success = etl.process_tournament_file(
            str(sample_save_file), challonge_match_id=challonge_id
        )

        # ASSERT
        assert success

        # Verify round in database
        with temp_db.get_connection() as conn:
            result = conn.execute(
                "SELECT tournament_round FROM matches WHERE challonge_match_id = ?",
                [challonge_id],
            ).fetchone()
            assert result is not None
            assert result[0] == expected_round

    def test_missing_round_in_cache_logs_warning(
        self, temp_db: TournamentDatabase, sample_save_file: Path, caplog
    ) -> None:
        """Test warning logged when challonge_match_id not in cache."""
        # ARRANGE
        challonge_id = 426504721
        round_cache = {999999: 1}  # Different ID

        etl = TournamentETL(database=temp_db, round_cache=round_cache)

        # ACT
        etl.process_tournament_file(
            str(sample_save_file), challonge_match_id=challonge_id
        )

        # ASSERT
        assert "No round data found" in caplog.text

        # Verify round is NULL
        with temp_db.get_connection() as conn:
            result = conn.execute(
                "SELECT tournament_round FROM matches WHERE challonge_match_id = ?",
                [challonge_id],
            ).fetchone()
            assert result is not None
            assert result[0] is None
