"""Tests for LogData extraction from Old World save files.

Current extract_events() behavior:
- Returns: List[Dict[str, Any]] with keys: turn_number, event_type, player_id, description, x_coordinate, y_coordinate, event_data
- Player ID mapping: XML Player="0" becomes None (BUG!), Player="1+" becomes player_id
  - Line 295: player_id = raw_player_id if raw_player_id and raw_player_id > 0 else None
  - This incorrectly converts player_id 0 to None
- Extracts from: MemoryData elements only (not LogData)
- Used by: etl.py process_save_file() to insert into events table

For LogData extraction, we'll use correct mapping:
- XML Player[@ID="0"] → database player_id = 1
- XML Player[@ID="1"] → database player_id = 2
- Formula: database_player_id = int(xml_id) + 1
"""

import pytest
from pathlib import Path
from tournament_visualizer.data.parser import OldWorldSaveParser


@pytest.fixture
def sample_xml_path() -> Path:
    """Path to sample XML fixture."""
    return Path(__file__).parent / "fixtures" / "sample_save.xml"


def test_sample_fixture_exists(sample_xml_path: Path) -> None:
    """Verify test fixture exists."""
    assert sample_xml_path.exists(), f"Test fixture not found: {sample_xml_path}"
