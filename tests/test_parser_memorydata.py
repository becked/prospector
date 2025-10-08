"""Tests for MemoryData event parsing with correct player ownership."""

import pytest
from tournament_visualizer.data.parser import OldWorldSaveParser


class TestMemoryDataPlayerOwnership:
    """Test that MemoryData events are assigned to correct player based on parent Player element."""

    def test_memorytribe_events_assigned_to_owner_player(self, sample_save_path: str) -> None:
        """MEMORYTRIBE events should get player_id from parent Player[@ID], not from <Player> child.

        Context:
            - MemoryData elements are stored inside Player[@ID]/MemoryList
            - MEMORYTRIBE_* events have NO <Player> child element
            - They should inherit player_id from their parent Player[@ID] owner

        Expected:
            - XML: <Player ID="0"> → Database: player_id=1
            - XML: <Player ID="1"> → Database: player_id=2
            - MEMORYTRIBE events should have player_id matching their owner
        """
        parser = OldWorldSaveParser(sample_save_path)
        parser.parse_xml_file(sample_save_path)
        events = parser.extract_events()

        # Filter to MEMORYTRIBE events only
        tribe_events = [e for e in events if e['event_type'].startswith('MEMORYTRIBE_')]

        # Should have some MEMORYTRIBE events
        assert len(tribe_events) > 0, "Sample file should contain MEMORYTRIBE events"

        # NONE should have NULL player_id (currently fails - this is the bug we're fixing)
        null_player_events = [e for e in tribe_events if e['player_id'] is None]
        assert len(null_player_events) == 0, \
            f"Found {len(null_player_events)} MEMORYTRIBE events with NULL player_id. " \
            f"All should be assigned to their owner Player[@ID]"

        # All should have valid player_id (1 or 2 for 2-player match)
        for event in tribe_events:
            assert event['player_id'] in [1, 2], \
                f"MEMORYTRIBE event has invalid player_id={event['player_id']}, expected 1 or 2"

    def test_memorytribe_distribution_across_players(self, sample_save_path: str) -> None:
        """MEMORYTRIBE events should be distributed across both players' memories.

        Context:
            - Each player has their own MemoryList
            - Some tribe events belong to Player 0, some to Player 1
            - Distribution should reflect whose perspective stored the memory
        """
        parser = OldWorldSaveParser(sample_save_path)
        parser.parse_xml_file(sample_save_path)
        events = parser.extract_events()

        tribe_events = [e for e in events if e['event_type'].startswith('MEMORYTRIBE_')]

        # Count by player_id
        player_1_events = [e for e in tribe_events if e['player_id'] == 1]
        player_2_events = [e for e in tribe_events if e['player_id'] == 2]

        # Both players should have some MEMORYTRIBE events
        assert len(player_1_events) > 0, "Player 1 should have some MEMORYTRIBE events"
        assert len(player_2_events) > 0, "Player 2 should have some MEMORYTRIBE events"

        # Total should match
        assert len(player_1_events) + len(player_2_events) == len(tribe_events)

    def test_memoryplayer_events_still_work(self, sample_save_path: str) -> None:
        """MEMORYPLAYER events should still use their <Player> child for player_id.

        Context:
            - MEMORYPLAYER_* events HAVE a <Player> child element
            - That <Player> is the OTHER player (opponent/subject), NOT owner
            - We need to preserve this existing behavior

        Important:
            - This is a REGRESSION test
            - Ensures our fix doesn't break existing MEMORYPLAYER parsing
        """
        parser = OldWorldSaveParser(sample_save_path)
        parser.parse_xml_file(sample_save_path)
        events = parser.extract_events()

        player_events = [e for e in events if e['event_type'].startswith('MEMORYPLAYER_')]

        # Should have some MEMORYPLAYER events
        assert len(player_events) > 0, "Sample file should contain MEMORYPLAYER events"

        # All should have valid player_id from their <Player> child element
        for event in player_events:
            assert event['player_id'] in [1, 2], \
                f"MEMORYPLAYER event has invalid player_id={event['player_id']}"


def test_memorytribe_events_in_database_have_player_id() -> None:
    """Integration test: Verify imported MEMORYTRIBE events have player_id.

    Context:
        - Tests against actual database (tournament_data.duckdb)
        - Verifies the full pipeline: parse → import → query

    Requirement:
        - Database must exist with imported data
        - Run this AFTER Task 4 (re-import data)
    """
    import duckdb

    conn = duckdb.connect('tournament_data.duckdb', read_only=True)

    # Query all MEMORYTRIBE events
    result = conn.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN player_id IS NULL THEN 1 ELSE 0 END) as null_count,
            SUM(CASE WHEN player_id IS NOT NULL THEN 1 ELSE 0 END) as valid_count
        FROM events
        WHERE event_type LIKE 'MEMORYTRIBE_%'
    """).fetchone()

    total, null_count, valid_count = result

    # Should have some events
    assert total > 0, "Database should contain MEMORYTRIBE events"

    # ALL should have player_id
    assert null_count == 0, \
        f"Found {null_count} MEMORYTRIBE events with NULL player_id after import. " \
        f"Parser fix may not be working correctly."

    assert valid_count == total, \
        f"Expected all {total} events to have player_id, but only {valid_count} do"

    conn.close()


def test_memoryfamily_events_in_database_have_player_id() -> None:
    """Verify MEMORYFAMILY events also get player_id (same fix applies)."""
    import duckdb

    conn = duckdb.connect('tournament_data.duckdb', read_only=True)

    result = conn.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN player_id IS NULL THEN 1 ELSE 0 END) as null_count
        FROM events
        WHERE event_type LIKE 'MEMORYFAMILY_%'
    """).fetchone()

    total, null_count = result

    if total > 0:  # Only test if we have these events
        assert null_count == 0, \
            f"Found {null_count} MEMORYFAMILY events with NULL player_id"

    conn.close()


def test_memoryreligion_events_in_database_have_player_id() -> None:
    """Verify MEMORYRELIGION events also get player_id (same fix applies)."""
    import duckdb

    conn = duckdb.connect('tournament_data.duckdb', read_only=True)

    result = conn.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN player_id IS NULL THEN 1 ELSE 0 END) as null_count
        FROM events
        WHERE event_type LIKE 'MEMORYRELIGION_%'
    """).fetchone()

    total, null_count = result

    if total > 0:
        assert null_count == 0, \
            f"Found {null_count} MEMORYRELIGION events with NULL player_id"

    conn.close()


@pytest.fixture
def sample_save_path() -> str:
    """Path to sample save file for testing."""
    return "tests/fixtures/sample_save.xml"
