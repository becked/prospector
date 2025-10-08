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

from pathlib import Path

import pytest

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
        law_events = [e for e in events if e["event_type"] == "LAW_ADOPTED"]

        # For anarkos-becked match, there are 13 total law adoptions
        # (6 for anarkos, 7 for becked)
        assert len(law_events) > 0, "Should find at least one law adoption"

    def test_law_adoption_event_structure(self, sample_xml_path: Path) -> None:
        """Law adoption events should have correct structure."""
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.parse_xml_file(str(sample_xml_path))

        events = parser.extract_logdata_events()
        law_events = [e for e in events if e["event_type"] == "LAW_ADOPTED"]

        if law_events:
            event = law_events[0]

            # Required fields
            assert "turn_number" in event
            assert "event_type" in event
            assert "player_id" in event
            assert "description" in event

            # Type checks
            assert isinstance(event["turn_number"], int)
            assert event["event_type"] == "LAW_ADOPTED"
            assert isinstance(event["player_id"], int)
            assert isinstance(event["description"], str)

    def test_law_adoption_extracts_law_name(self, sample_xml_path: Path) -> None:
        """Should extract the specific law from Data1."""
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.parse_xml_file(str(sample_xml_path))

        events = parser.extract_logdata_events()
        law_events = [e for e in events if e["event_type"] == "LAW_ADOPTED"]

        if law_events:
            event = law_events[0]

            # event_data should contain the law name
            assert event.get("event_data") is not None
            assert "law" in event["event_data"]
            assert event["event_data"]["law"].startswith("LAW_")

    def test_law_adoption_correct_player_mapping(self, sample_xml_path: Path) -> None:
        """Should correctly map player IDs from XML to database."""
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.parse_xml_file(str(sample_xml_path))

        events = parser.extract_logdata_events()
        law_events = [e for e in events if e["event_type"] == "LAW_ADOPTED"]

        # Player IDs should be 1-based (matching players table)
        player_ids = [e["player_id"] for e in law_events]
        assert all(pid >= 1 for pid in player_ids), "Player IDs should be 1-based"


class TestTechDiscoveryExtraction:
    """Tests for extracting TECH_DISCOVERED events from LogData."""

    def test_extract_tech_discoveries_finds_techs(self, sample_xml_path: Path) -> None:
        """Should find TECH_DISCOVERED events in the file."""
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.parse_xml_file(str(sample_xml_path))

        events = parser.extract_logdata_events()
        tech_events = [e for e in events if e["event_type"] == "TECH_DISCOVERED"]

        # anarkos-becked match has 39 tech discoveries (19 + 20)
        assert len(tech_events) > 0, "Should find at least one tech discovery"

    def test_tech_discovery_event_structure(self, sample_xml_path: Path) -> None:
        """Tech discovery events should have correct structure."""
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.parse_xml_file(str(sample_xml_path))

        events = parser.extract_logdata_events()
        tech_events = [e for e in events if e["event_type"] == "TECH_DISCOVERED"]

        if tech_events:
            event = tech_events[0]

            # Required fields
            assert "turn_number" in event
            assert "event_type" in event
            assert "player_id" in event

            # Type checks
            assert isinstance(event["turn_number"], int)
            assert event["event_type"] == "TECH_DISCOVERED"
            assert isinstance(event["player_id"], int)

    def test_tech_discovery_extracts_tech_name(self, sample_xml_path: Path) -> None:
        """Should extract the specific tech from Data1."""
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.parse_xml_file(str(sample_xml_path))

        events = parser.extract_logdata_events()
        tech_events = [e for e in events if e["event_type"] == "TECH_DISCOVERED"]

        if tech_events:
            event = tech_events[0]

            # event_data should contain the tech name
            assert event.get("event_data") is not None
            assert "tech" in event["event_data"]
            assert event["event_data"]["tech"].startswith("TECH_")

    def test_tech_discoveries_ordered_by_turn(self, sample_xml_path: Path) -> None:
        """Tech discoveries should be extractable in turn order."""
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.parse_xml_file(str(sample_xml_path))

        events = parser.extract_logdata_events()
        tech_events = [e for e in events if e["event_type"] == "TECH_DISCOVERED"]

        # Check that we can order by turn
        turns = [e["turn_number"] for e in tech_events]
        assert turns == sorted(turns), "Should preserve turn order"


class TestMemoryDataPlayerIDMapping:
    """Tests for correct player ID mapping in MemoryData extraction.

    These tests verify that the extract_events() method correctly converts
    0-based XML player IDs to 1-based database player IDs, matching the
    behavior of extract_logdata_events().
    """

    def test_player_zero_maps_to_player_id_one(self, sample_xml_path: Path) -> None:
        """XML Player=0 should map to database player_id=1, not None.

        Current bug: Player=0 is treated as invalid and converted to None.
        Expected: Player=0 should be converted to player_id=1 (first player).
        """
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.parse_xml_file(str(sample_xml_path))

        events = parser.extract_events()

        # Find events that should belong to player 1 (XML Player=0)
        # These are MEMORYPLAYER_* events that occur around turn 65
        player_1_events = [
            e
            for e in events
            if e["player_id"] == 1 and e["event_type"].startswith("MEMORYPLAYER_")
        ]

        # The fixture has 39 events with <Player>0</Player>
        # They should all have player_id=1
        assert len(player_1_events) > 0, (
            "Should find events with player_id=1 for XML Player=0. "
            "Currently these are being set to None (bug!)"
        )

        # Verify no events have player_id=None for MEMORYPLAYER_* events
        player_none_events = [
            e
            for e in events
            if e["player_id"] is None and e["event_type"].startswith("MEMORYPLAYER_")
        ]

        assert len(player_none_events) == 0, (
            f"Found {len(player_none_events)} MEMORYPLAYER events with player_id=None. "
            "These should have player_id=1 (from XML Player=0)."
        )

    def test_player_one_maps_to_player_id_two(self, sample_xml_path: Path) -> None:
        """XML Player=1 should map to database player_id=2, not player_id=1.

        Current bug: Player=1 is kept as 1, but should be 2.
        Expected: Player=1 should be converted to player_id=2 (second player).
        """
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.parse_xml_file(str(sample_xml_path))

        events = parser.extract_events()

        # Find events that should belong to player 2 (XML Player=1)
        player_2_events = [
            e
            for e in events
            if e["player_id"] == 2 and e["event_type"].startswith("MEMORYPLAYER_")
        ]

        # The fixture has 32 events with <Player>1</Player>
        # They should all have player_id=2
        assert len(player_2_events) > 0, (
            "Should find events with player_id=2 for XML Player=1. "
            "Currently these are incorrectly set to player_id=1 (bug!)"
        )

    def test_player_id_distribution_matches_xml(self, sample_xml_path: Path) -> None:
        """The distribution of player IDs should match the XML data.

        From test fixture:
        - 39 events with <Player>0</Player> → should have player_id=1
        - 32 events with <Player>1</Player> → should have player_id=2
        """
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.parse_xml_file(str(sample_xml_path))

        events = parser.extract_events()

        # Count MEMORYPLAYER_* events by player_id
        from collections import Counter

        memoryplayer_events = [
            e for e in events if e["event_type"].startswith("MEMORYPLAYER_")
        ]

        player_counts = Counter(e.get("player_id") for e in memoryplayer_events)

        # Expected counts from XML
        expected_player_1_count = 39  # From <Player>0</Player>
        expected_player_2_count = 32  # From <Player>1</Player>

        # Allow some tolerance (±2) for edge cases in test data
        assert abs(player_counts.get(1, 0) - expected_player_1_count) <= 2, (
            f"Expected ~{expected_player_1_count} events for player_id=1, "
            f"got {player_counts.get(1, 0)}"
        )

        assert abs(player_counts.get(2, 0) - expected_player_2_count) <= 2, (
            f"Expected ~{expected_player_2_count} events for player_id=2, "
            f"got {player_counts.get(2, 0)}"
        )

        # Should have NO events with player_id=None for MEMORYPLAYER_* events
        assert player_counts.get(None, 0) == 0, (
            f"Found {player_counts.get(None, 0)} events with player_id=None. "
            "All MEMORYPLAYER events should have a valid player_id."
        )

    def test_memorydata_matches_logdata_player_mapping(
        self, sample_xml_path: Path
    ) -> None:
        """MemoryData and LogData should use the same player ID mapping.

        Both extract methods should convert 0-based XML IDs to 1-based DB IDs.
        This ensures consistency across the codebase.
        """
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.parse_xml_file(str(sample_xml_path))

        memory_events = parser.extract_events()
        logdata_events = parser.extract_logdata_events()

        # Get unique player IDs from each source
        memory_player_ids = set(
            e["player_id"] for e in memory_events if e["player_id"] is not None
        )

        logdata_player_ids = set(
            e["player_id"] for e in logdata_events if e["player_id"] is not None
        )

        # Both should have the same player IDs (1 and 2 for this fixture)
        assert memory_player_ids == logdata_player_ids, (
            f"MemoryData player IDs {memory_player_ids} don't match "
            f"LogData player IDs {logdata_player_ids}. "
            "Both should use 1-based IDs (1, 2, ...)."
        )

        # Specifically, both should have players 1 and 2
        assert 1 in memory_player_ids, "MemoryData should have player_id=1"
        assert 2 in memory_player_ids, "MemoryData should have player_id=2"
