"""Tests for turn-by-turn history extraction from Old World save files."""

from pathlib import Path
from typing import Dict, Any

import pytest

from tournament_visualizer.data.parser import OldWorldSaveParser


@pytest.fixture
def sample_history_path() -> Path:
    """Path to sample history XML fixture."""
    return Path(__file__).parent / "fixtures" / "sample_history.xml"


def test_sample_history_fixture_exists(sample_history_path: Path) -> None:
    """Verify test fixture exists."""
    assert sample_history_path.exists(), f"Test fixture not found: {sample_history_path}"


class TestPointsHistoryExtraction:
    """Tests for extracting victory points history."""

    def test_extract_points_history(self, sample_history_path: Path) -> None:
        """Test extraction of victory points history."""
        # Setup: Create parser with test fixture
        parser = OldWorldSaveParser(str(sample_history_path))
        parser.parse_xml_file(str(sample_history_path))

        # Execute: Extract points history
        points_history = parser.extract_points_history()

        # Verify: Check we got the right data
        assert len(points_history) > 0, "Should extract at least some points data"

        # Should have 2 players × 4 turns = 8 records
        assert len(points_history) == 8, f"Expected 8 records, got {len(points_history)}"

        # Check structure of first record
        first_record = points_history[0]
        assert "player_id" in first_record
        assert "turn_number" in first_record
        assert "points" in first_record

        # Verify player ID mapping (XML ID=0 → DB player_id=1)
        player_1_records = [r for r in points_history if r["player_id"] == 1]
        assert len(player_1_records) == 4, "Player 1 should have 4 turn records"

        # Verify actual values from fixture
        # Player 1 (XML ID=0), Turn 2: 1 point
        turn_2_player_1 = next(
            r
            for r in points_history
            if r["player_id"] == 1 and r["turn_number"] == 2
        )
        assert turn_2_player_1["points"] == 1

        # Player 1, Turn 5: 8 points
        turn_5_player_1 = next(
            r
            for r in points_history
            if r["player_id"] == 1 and r["turn_number"] == 5
        )
        assert turn_5_player_1["points"] == 8

        # Player 2 (XML ID=1 → DB player_id=2), Turn 5: 10 points
        turn_5_player_2 = next(
            r
            for r in points_history
            if r["player_id"] == 2 and r["turn_number"] == 5
        )
        assert turn_5_player_2["points"] == 10

    def test_extract_points_history_missing_history(
        self, sample_history_path: Path
    ) -> None:
        """Test points extraction when PointsHistory element is missing."""
        xml_without_history = """<?xml version="1.0" encoding="utf-8"?>
        <Root>
            <Player ID="0" OnlineID="123" Name="Test">
                <!-- No PointsHistory element -->
            </Player>
        </Root>"""

        parser = OldWorldSaveParser(str(sample_history_path))
        # Parse the string directly
        import xml.etree.ElementTree as ET

        parser.root = ET.fromstring(xml_without_history)

        points_history = parser.extract_points_history()

        # Should return empty list, not crash
        assert points_history == []

    def test_extract_points_history_invalid_turn_tags(
        self, sample_history_path: Path
    ) -> None:
        """Test points extraction handles non-turn tags gracefully."""
        xml_with_invalid = """<?xml version="1.0" encoding="utf-8"?>
        <Root>
            <Player ID="0" OnlineID="123" Name="Test">
                <PointsHistory>
                    <T2>5</T2>
                    <InvalidTag>999</InvalidTag>
                    <T3>10</T3>
                </PointsHistory>
            </Player>
        </Root>"""

        parser = OldWorldSaveParser(str(sample_history_path))
        import xml.etree.ElementTree as ET

        parser.root = ET.fromstring(xml_with_invalid)

        points_history = parser.extract_points_history()

        # Should have exactly 2 records (T2 and T3), skipping InvalidTag
        assert len(points_history) == 2
        assert all(r["turn_number"] in [2, 3] for r in points_history)
