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
from typing import Any, Dict, List
from tournament_visualizer.data.parser import OldWorldSaveParser


@pytest.fixture
def sample_xml_path() -> Path:
    """Path to sample XML fixture."""
    return Path(__file__).parent / "fixtures" / "sample_save.xml"


def test_sample_fixture_exists(sample_xml_path: Path) -> None:
    """Verify test fixture exists."""
    assert sample_xml_path.exists(), f"Test fixture not found: {sample_xml_path}"


class TestLawAdoptionExtraction:
    """Tests for extracting LAW_ADOPTED events from LogData."""

    def test_extract_logdata_events_returns_list(self, sample_xml_path: Path) -> None:
        """extract_logdata_events() should return a list."""
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.parse_xml_file(str(sample_xml_path))

        # This method doesn't exist yet - we'll create it
        events = parser.extract_logdata_events()

        assert isinstance(events, list)

    def test_extract_law_adoptions_finds_all_laws(self, sample_xml_path: Path) -> None:
        """Should find all LAW_ADOPTED events in the file."""
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.parse_xml_file(str(sample_xml_path))

        events = parser.extract_logdata_events()
        law_events = [e for e in events if e['event_type'] == 'LAW_ADOPTED']

        # For anarkos-becked match, there are 13 total law adoptions
        # (6 for anarkos, 7 for becked)
        assert len(law_events) > 0, "Should find at least one law adoption"

    def test_law_adoption_event_structure(self, sample_xml_path: Path) -> None:
        """Law adoption events should have correct structure."""
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.parse_xml_file(str(sample_xml_path))

        events = parser.extract_logdata_events()
        law_events = [e for e in events if e['event_type'] == 'LAW_ADOPTED']

        if law_events:
            event = law_events[0]

            # Required fields
            assert 'turn_number' in event
            assert 'event_type' in event
            assert 'player_id' in event
            assert 'description' in event

            # Type checks
            assert isinstance(event['turn_number'], int)
            assert event['event_type'] == 'LAW_ADOPTED'
            assert isinstance(event['player_id'], int)
            assert isinstance(event['description'], str)

    def test_law_adoption_extracts_law_name(self, sample_xml_path: Path) -> None:
        """Should extract the specific law from Data1."""
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.parse_xml_file(str(sample_xml_path))

        events = parser.extract_logdata_events()
        law_events = [e for e in events if e['event_type'] == 'LAW_ADOPTED']

        if law_events:
            event = law_events[0]

            # event_data should contain the law name
            assert event.get('event_data') is not None
            assert 'law' in event['event_data']
            assert event['event_data']['law'].startswith('LAW_')

    def test_law_adoption_correct_player_mapping(self, sample_xml_path: Path) -> None:
        """Should correctly map player IDs from XML to database."""
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.parse_xml_file(str(sample_xml_path))

        events = parser.extract_logdata_events()
        law_events = [e for e in events if e['event_type'] == 'LAW_ADOPTED']

        # Player IDs should be 1-based (matching players table)
        player_ids = [e['player_id'] for e in law_events]
        assert all(pid >= 1 for pid in player_ids), "Player IDs should be 1-based"


class TestTechDiscoveryExtraction:
    """Tests for extracting TECH_DISCOVERED events from LogData."""

    def test_extract_tech_discoveries_finds_techs(self, sample_xml_path: Path) -> None:
        """Should find TECH_DISCOVERED events in the file."""
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.parse_xml_file(str(sample_xml_path))

        events = parser.extract_logdata_events()
        tech_events = [e for e in events if e['event_type'] == 'TECH_DISCOVERED']

        # anarkos-becked match has 39 tech discoveries (19 + 20)
        assert len(tech_events) > 0, "Should find at least one tech discovery"

    def test_tech_discovery_event_structure(self, sample_xml_path: Path) -> None:
        """Tech discovery events should have correct structure."""
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.parse_xml_file(str(sample_xml_path))

        events = parser.extract_logdata_events()
        tech_events = [e for e in events if e['event_type'] == 'TECH_DISCOVERED']

        if tech_events:
            event = tech_events[0]

            # Required fields
            assert 'turn_number' in event
            assert 'event_type' in event
            assert 'player_id' in event

            # Type checks
            assert isinstance(event['turn_number'], int)
            assert event['event_type'] == 'TECH_DISCOVERED'
            assert isinstance(event['player_id'], int)

    def test_tech_discovery_extracts_tech_name(self, sample_xml_path: Path) -> None:
        """Should extract the specific tech from Data1."""
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.parse_xml_file(str(sample_xml_path))

        events = parser.extract_logdata_events()
        tech_events = [e for e in events if e['event_type'] == 'TECH_DISCOVERED']

        if tech_events:
            event = tech_events[0]

            # event_data should contain the tech name
            assert event.get('event_data') is not None
            assert 'tech' in event['event_data']
            assert event['event_data']['tech'].startswith('TECH_')

    def test_tech_discoveries_ordered_by_turn(self, sample_xml_path: Path) -> None:
        """Tech discoveries should be extractable in turn order."""
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.parse_xml_file(str(sample_xml_path))

        events = parser.extract_logdata_events()
        tech_events = [e for e in events if e['event_type'] == 'TECH_DISCOVERED']

        # Check that we can order by turn
        turns = [e['turn_number'] for e in tech_events]
        assert turns == sorted(turns), "Should preserve turn order"
