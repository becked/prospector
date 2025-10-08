"""Integration tests for LogData ingestion pipeline."""

import pytest
from pathlib import Path
import tempfile
import shutil
from tournament_visualizer.data.etl import TournamentETL
from tournament_visualizer.data.database import TournamentDatabase


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_tournament.duckdb"

    yield db_path

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_save_dir(tmp_path):
    """Create temp directory with one save file."""
    save_dir = tmp_path / "saves"
    save_dir.mkdir()

    # Copy one save file for testing
    source = Path("saves/match_426504721_anarkos-becked.zip")
    if source.exists():
        shutil.copy(source, save_dir / source.name)

    return save_dir


def test_full_pipeline_with_logdata(temp_db, sample_save_dir):
    """Test complete ETL pipeline including LogData extraction."""
    # Initialize database
    db = TournamentDatabase(db_path=str(temp_db), read_only=False)
    db.create_schema()

    # Process the save file
    etl = TournamentETL(database=db)

    # Process each file in the directory
    save_files = list(sample_save_dir.glob("*.zip"))
    assert len(save_files) == 1, "Should have one save file for testing"

    success = etl.process_tournament_file(str(save_files[0]))
    assert success, "Processing should succeed"

    # Check that law events were captured
    with db.get_connection() as conn:
        law_events = conn.execute("""
            SELECT COUNT(*) as count
            FROM events
            WHERE event_type = 'LAW_ADOPTED'
        """).df()

    assert law_events['count'].iloc[0] >= 13, "Should find 13 law adoptions"

    # Check that tech events were captured
    with db.get_connection() as conn:
        tech_events = conn.execute("""
            SELECT COUNT(*) as count
            FROM events
            WHERE event_type = 'TECH_DISCOVERED'
        """).df()

    assert tech_events['count'].iloc[0] >= 39, "Should find 39 tech discoveries"


def test_law_milestone_calculation(temp_db, sample_save_dir):
    """Test that law milestones are correctly calculated."""
    # Initialize database
    db = TournamentDatabase(db_path=str(temp_db), read_only=False)
    db.create_schema()

    # Process the save file
    etl = TournamentETL(database=db)

    # Process each file in the directory
    save_files = list(sample_save_dir.glob("*.zip"))
    assert len(save_files) == 1, "Should have one save file for testing"

    success = etl.process_tournament_file(str(save_files[0]))
    assert success, "Processing should succeed"

    # Query law milestones
    from tournament_visualizer.data.queries import TournamentQueries

    with db.get_connection() as conn:
        matches = conn.execute("SELECT match_id FROM matches LIMIT 1").df()
    match_id = int(matches['match_id'].iloc[0])

    queries = TournamentQueries(database=db)
    progression = queries.get_law_progression_by_match(match_id)

    # Verify both players have data
    assert len(progression) == 2, "Should have data for both players"

    # Verify milestone columns exist and have reasonable values
    assert 'turn_to_4_laws' in progression.columns
    assert 'turn_to_7_laws' in progression.columns

    # At least one player should reach 4 laws
    assert progression['turn_to_4_laws'].notna().any()
