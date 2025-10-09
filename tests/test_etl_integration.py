"""Integration test for history data ETL pipeline."""

import tempfile
from pathlib import Path
import pytest
from tournament_visualizer.data.etl import TournamentETL
from tournament_visualizer.data.database import TournamentDatabase


def test_history_data_etl_integration():
    """Test that history data flows from parser through ETL to database."""

    # Create temporary test database
    with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False) as tmp_db:
        db_path = tmp_db.name

    # Remove the temp file so DuckDB can create a fresh database
    Path(db_path).unlink()

    try:
        # Initialize database with schema
        db = TournamentDatabase(db_path=db_path, read_only=False)
        db.create_schema()

        # Create ETL instance
        etl = TournamentETL(database=db)

        # Process a real save file
        test_save_file = "saves/match_426504721_anarkos-becked.zip"

        if not Path(test_save_file).exists():
            pytest.skip(f"Test save file not found: {test_save_file}")

        # Process the file
        success = etl.process_tournament_file(test_save_file)
        assert success, "File processing should succeed"

        # Verify history data was inserted
        with db.get_connection() as conn:
            # Check points history
            points_count = conn.execute(
                "SELECT COUNT(*) FROM player_points_history"
            ).fetchone()[0]
            assert points_count > 0, "Points history should have records"

            # Check military history
            military_count = conn.execute(
                "SELECT COUNT(*) FROM player_military_history"
            ).fetchone()[0]
            assert military_count > 0, "Military history should have records"

            # Check legitimacy history
            legitimacy_count = conn.execute(
                "SELECT COUNT(*) FROM player_legitimacy_history"
            ).fetchone()[0]
            assert legitimacy_count > 0, "Legitimacy history should have records"

            # Check family opinions
            family_count = conn.execute(
                "SELECT COUNT(*) FROM family_opinion_history"
            ).fetchone()[0]
            assert family_count > 0, "Family opinion history should have records"

            # Check religion opinions
            religion_count = conn.execute(
                "SELECT COUNT(*) FROM religion_opinion_history"
            ).fetchone()[0]
            assert religion_count > 0, "Religion opinion history should have records"

            print(f"\n✅ Integration test passed!")
            print(f"   Points records: {points_count}")
            print(f"   Military records: {military_count}")
            print(f"   Legitimacy records: {legitimacy_count}")
            print(f"   Family opinion records: {family_count}")
            print(f"   Religion opinion records: {religion_count}")

    finally:
        # Cleanup
        Path(db_path).unlink(missing_ok=True)


if __name__ == "__main__":
    test_history_data_etl_integration()
