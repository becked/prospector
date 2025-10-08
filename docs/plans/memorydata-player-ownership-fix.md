# MemoryData Player Ownership Fix - Implementation Plan

## Problem Statement

Currently, MemoryData events that lack an explicit `<Player>` child element (e.g., MEMORYTRIBE_*, MEMORYFAMILY_*, MEMORYRELIGION_*) are stored in the database with `player_id = NULL`. However, these events ARE stored within a specific Player's `<MemoryList>` in the XML, meaning they belong to that player's perspective/memory.

**Current Behavior:**
- Parser uses `.findall('.//MemoryData')` which searches globally through XML
- Loses parent `<Player ID="...">` context
- Events like MEMORYTRIBE_ATTACKED_ENEMY get `player_id = NULL` in database
- User can't see whose perspective these memories represent

**Expected Behavior:**
- Track which Player[@ID] owns each MemoryData element
- Store correct player_id for ALL memory events
- Events show which player experienced/witnessed them

## XML Structure Overview

```xml
<Root>
  <Player ID="0">  <!-- Fluffbunny, stored as player_id=1 in DB -->
    <MemoryList>
      <MemoryData>
        <Type>MEMORYPLAYER_ATTACKED_CITY</Type>
        <Player>1</Player>  <!-- The OTHER player, not owner -->
        <Turn>63</Turn>
      </MemoryData>
      <MemoryData>
        <Type>MEMORYTRIBE_ATTACKED_UNIT</Type>
        <Tribe>TRIBE_RAIDERS</Tribe>  <!-- NO <Player> child -->
        <Turn>63</Turn>
      </MemoryData>
    </MemoryList>
  </Player>

  <Player ID="1">  <!-- Becked, stored as player_id=2 in DB -->
    <MemoryList>
      <!-- More MemoryData elements -->
    </MemoryList>
  </Player>
</Root>
```

**Key Points:**
1. **Owner Player**: `<Player ID="0">` is the player who owns the MemoryList (viewer/experiencer)
2. **Subject Player**: `<Player>1</Player>` inside MemoryData is the OTHER player (opponent/subject)
3. **No Subject**: MEMORYTRIBE/FAMILY/RELIGION events have NO `<Player>` child, only owner matters
4. **ID Mapping**: XML ID="0" → DB player_id=1, XML ID="1" → DB player_id=2

## Implementation Tasks

### Task 1: Write Failing Test for MEMORYTRIBE Events

**File:** `tests/test_parser_memorydata.py` (create new file)

**Goal:** Verify that MEMORYTRIBE events get assigned to the correct player_id based on their parent Player[@ID].

**Test Design:**
- Use TDD: Write test BEFORE implementing fix
- Test should FAIL initially (currently returns NULL)
- Test both players to ensure we're tracking ownership correctly

**Code:**

```python
"""Tests for MemoryData event parsing with correct player ownership."""

import pytest
from tournament_visualizer.data.parser import SaveFileParser


class TestMemoryDataPlayerOwnership:
    """Test that MemoryData events are assigned to correct player based on parent Player element."""

    def test_memorytribe_events_assigned_to_owner_player(self, sample_save_path):
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
        parser = SaveFileParser(sample_save_path)
        parser.extract_and_parse()
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

    def test_memorytribe_distribution_across_players(self, sample_save_path):
        """MEMORYTRIBE events should be distributed across both players' memories.

        Context:
            - Each player has their own MemoryList
            - Some tribe events belong to Player 0, some to Player 1
            - Distribution should reflect whose perspective stored the memory
        """
        parser = SaveFileParser(sample_save_path)
        parser.extract_and_parse()
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

    def test_memoryplayer_events_still_work(self, sample_save_path):
        """MEMORYPLAYER events should still use their <Player> child for player_id.

        Context:
            - MEMORYPLAYER_* events HAVE a <Player> child element
            - That <Player> is the OTHER player (opponent/subject), NOT owner
            - We need to preserve this existing behavior

        Important:
            - This is a REGRESSION test
            - Ensures our fix doesn't break existing MEMORYPLAYER parsing
        """
        parser = SaveFileParser(sample_save_path)
        parser.extract_and_parse()
        events = parser.extract_events()

        player_events = [e for e in events if e['event_type'].startswith('MEMORYPLAYER_')]

        # Should have some MEMORYPLAYER events
        assert len(player_events) > 0, "Sample file should contain MEMORYPLAYER events"

        # All should have valid player_id from their <Player> child element
        for event in player_events:
            assert event['player_id'] in [1, 2], \
                f"MEMORYPLAYER event has invalid player_id={event['player_id']}"


@pytest.fixture
def sample_save_path():
    """Path to sample save file for testing."""
    return "tests/fixtures/sample_save.xml"
```

**How to Run:**
```bash
# Run just this new test file
uv run pytest tests/test_parser_memorydata.py -v

# Expected: ALL tests should FAIL initially (this is TDD - test first!)
# Example failure message:
#   AssertionError: Found 72 MEMORYTRIBE events with NULL player_id. All should be assigned to their owner Player[@ID]
```

**Validation:**
- Tests should compile without errors
- Tests should FAIL with clear error messages about NULL player_id
- Failure messages should indicate the bug we're fixing

**Commit:** `test: Add failing tests for MemoryData player ownership bug`

---

### Task 2: Refactor Parser to Track Player Ownership

**File:** `tournament_visualizer/data/parser.py`

**Method:** `extract_events()` (lines 281-374)

**Goal:** Change from global `.findall('.//MemoryData')` to iterating through `Player[@ID]` elements first, then their MemoryList children.

**Current Code Structure:**
```python
# BEFORE (loses player ownership)
memory_data_elements = self.root.findall('.//MemoryData')  # Global search!
for mem in memory_data_elements:
    player_elem = mem.find('Player')  # Only finds <Player> child
    raw_player_id = self._safe_int(player_elem.text) if player_elem else None
```

**New Code Structure:**
```python
# AFTER (preserves player ownership)
for player in self.root.findall('.//Player[@ID]'):  # Find all Player elements with ID attribute
    owner_id = self._safe_int(player.get('ID'))  # Get owner's ID from attribute
    memory_list = player.find('MemoryList')
    if memory_list is None:
        continue

    for mem in memory_list.findall('MemoryData'):  # Iterate children
        player_elem = mem.find('Player')  # Subject player (for MEMORYPLAYER_*)
        # Use owner_id as fallback when no subject player
```

**Full Implementation:**

```python
def extract_events(self) -> List[Dict[str, Any]]:
    """Extract game events from MemoryData elements.

    MemoryData contains character and diplomatic memories stored by the game AI.
    This provides limited historical data compared to LogData.

    Player ID Mapping:
        - Owner Player: The Player[@ID] element that contains the MemoryList
          This is whose perspective/memory the event represents.

        - Subject Player: The <Player> child element inside MemoryData
          Only exists for MEMORYPLAYER_* events, represents the OTHER player.

        - For MEMORYPLAYER_*: Use subject player (the <Player> child)
        - For MEMORYTRIBE/FAMILY/RELIGION_*: Use owner player (parent Player[@ID])

        XML uses 0-based IDs, database uses 1-based:
            Example: XML Player[@ID="0"] → database player_id=1
                     XML Player[@ID="1"] → database player_id=2

    Returns:
        List of event dictionaries from memory data, with player IDs mapped
        to 1-based database IDs for consistency with LogData events.
    """
    if self.root is None:
        raise ValueError("XML not parsed. Call extract_and_parse() first.")

    events = []

    # Build lookup tables for resolving IDs to names
    character_lookup = self._build_character_lookup()
    city_lookup = self._build_city_lookup()

    # Iterate through Player elements to preserve ownership context
    for player_element in self.root.findall('.//Player[@ID]'):
        # Get the player ID who OWNS this MemoryList (0-based in XML)
        owner_xml_id = self._safe_int(player_element.get('ID'))
        if owner_xml_id is None:
            continue

        # Convert to 1-based database player_id
        owner_player_id = owner_xml_id + 1

        # Find this player's MemoryList
        memory_list = player_element.find('MemoryList')
        if memory_list is None:
            continue

        # Process all MemoryData elements within this player's list
        for mem in memory_list.findall('MemoryData'):
            # Extract basic memory event data
            turn_elem = mem.find('Turn')
            type_elem = mem.find('Type')

            if turn_elem is None or type_elem is None:
                continue

            event_type = type_elem.text
            turn_number = self._safe_int(turn_elem.text)

            # Determine player_id based on event type:
            # - MEMORYPLAYER_*: Use the <Player> child (subject/opponent)
            # - MEMORYTRIBE/FAMILY/RELIGION_*: Use the owner player (viewer)
            player_elem = mem.find('Player')

            if player_elem is not None:
                # MEMORYPLAYER_* events: <Player> child is the subject (0-based)
                raw_subject_id = self._safe_int(player_elem.text)
                player_id = (raw_subject_id + 1) if raw_subject_id is not None else None
            else:
                # MEMORYTRIBE/FAMILY/RELIGION_* events: use owner
                player_id = owner_player_id

            # Extract additional context fields (note: actual XML uses IDs)
            context_data = {}

            # Fields that are directly available as text
            text_fields = ['Religion', 'Tribe', 'Family', 'Nation']
            for field in text_fields:
                elem = mem.find(field)
                if elem is not None and elem.text:
                    # Format the value to be more readable
                    context_data[field.lower()] = self._format_context_value(elem.text)

            # Fields that are IDs and need lookup
            character_id_elem = mem.find('CharacterID')
            if character_id_elem is not None and character_id_elem.text:
                char_id = self._safe_int(character_id_elem.text)
                if char_id and char_id in character_lookup:
                    context_data['character'] = character_lookup[char_id]
                else:
                    context_data['character_id'] = char_id

            city_id_elem = mem.find('CityID')
            if city_id_elem is not None and city_id_elem.text:
                city_id = self._safe_int(city_id_elem.text)
                if city_id and city_id in city_lookup:
                    context_data['city'] = city_lookup[city_id]
                else:
                    context_data['city_id'] = city_id

            # Only include event_data if there's actual context data
            event_data_json = context_data if context_data else None

            event_data = {
                'turn_number': turn_number,
                'event_type': event_type,
                'player_id': player_id,
                'description': self._format_memory_event(event_type, context_data),
                'x_coordinate': None,
                'y_coordinate': None,
                'event_data': event_data_json
            }

            events.append(event_data)

    return events
```

**Testing:**
```bash
# Run the tests we wrote in Task 1
uv run pytest tests/test_parser_memorydata.py -v

# Expected: Tests should now PASS
```

**Validation Checklist:**
- [ ] Tests pass
- [ ] No regressions in existing tests: `uv run pytest tests/test_parser_logdata.py -v`
- [ ] Code is clean and well-commented
- [ ] No unused variables or imports

**Commit:** `fix: Track player ownership for MemoryData events without <Player> child`

---

### Task 3: Verify Database Schema Supports Fix

**File:** Check database schema (no changes needed, just verification)

**Goal:** Confirm the `events` table can store player_id for all event types.

**Commands:**
```bash
# Check events table schema
uv run duckdb tournament_data.duckdb -readonly -c "DESCRIBE events"

# Should show:
# - player_id: BIGINT, nullable (YES)
# - This is correct - allows NULL for events with no player association
```

**Validation:**
- Confirm `player_id` column exists and accepts integers
- Confirm it's nullable (some global events may have no player)
- No schema changes needed - our fix works with existing schema

**Expected Output:**
```
┌──────────────┬─────────────┬─────────┐
│ column_name  │ column_type │  null   │
├──────────────┼─────────────┼─────────┤
│ player_id    │ BIGINT      │ YES     │  ← This is what we need
└──────────────┴─────────────┴─────────┘
```

**No commit needed** - this is verification only.

---

### Task 4: Re-import Data with Fixed Parser

**Files:** Database file, import script

**Goal:** Re-import tournament data using the fixed parser so existing data gets corrected.

**Important:**
- Backup database first
- Use dry-run to verify changes
- Check before/after counts

**Commands:**
```bash
# 1. Backup existing database
cp tournament_data.duckdb tournament_data.duckdb.backup_$(date +%Y%m%d_%H%M%S)

# 2. Check BEFORE counts (should show many NULL player_ids)
uv run duckdb tournament_data.duckdb -readonly -c "
SELECT
    'MEMORYTRIBE' as event_category,
    COUNT(*) as total_events,
    SUM(CASE WHEN player_id IS NULL THEN 1 ELSE 0 END) as null_player_id,
    SUM(CASE WHEN player_id IS NOT NULL THEN 1 ELSE 0 END) as has_player_id
FROM events
WHERE event_type LIKE 'MEMORYTRIBE_%'
"

# Expected BEFORE:
# - null_player_id: large number (e.g., 72)
# - has_player_id: 0

# 3. Re-import data
uv run python import_tournaments.py --directory saves --force --verbose

# 4. Check AFTER counts (should show NO NULL player_ids)
uv run duckdb tournament_data.duckdb -readonly -c "
SELECT
    'MEMORYTRIBE' as event_category,
    COUNT(*) as total_events,
    SUM(CASE WHEN player_id IS NULL THEN 1 ELSE 0 END) as null_player_id,
    SUM(CASE WHEN player_id IS NOT NULL THEN 1 ELSE 0 END) as has_player_id
FROM events
WHERE event_type LIKE 'MEMORYTRIBE_%'
"

# Expected AFTER:
# - null_player_id: 0
# - has_player_id: large number (e.g., 72)
```

**Validation Checklist:**
- [ ] Backup created successfully
- [ ] Import completed without errors
- [ ] All MEMORYTRIBE events now have player_id
- [ ] No MEMORYPLAYER events lost their player_id (regression check)
- [ ] Event counts match before/after (same total, just reassigned)

**Commit:** `data: Re-import tournaments with fixed MemoryData player ownership`

---

### Task 5: Add Integration Test with Real Data

**File:** `tests/test_parser_memorydata.py` (add to existing file)

**Goal:** Verify fix works with real imported data, not just parser unit tests.

**Code:**

```python
def test_memorytribe_events_in_database_have_player_id():
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


def test_memoryfamily_events_in_database_have_player_id():
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


def test_memoryreligion_events_in_database_have_player_id():
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
```

**How to Run:**
```bash
# Run integration tests (requires database)
uv run pytest tests/test_parser_memorydata.py::test_memorytribe_events_in_database_have_player_id -v

# Run all parser tests
uv run pytest tests/test_parser_memorydata.py -v
```

**Validation:**
- All integration tests pass
- Confirms data was imported correctly
- Provides ongoing regression protection

**Commit:** `test: Add integration tests for MemoryData player ownership`

---

### Task 6: Update Event Timeline Query

**File:** `tournament_visualizer/data/queries.py`

**Method:** `get_event_timeline()` (lines 292-411)

**Goal:** Now that MEMORYTRIBE/FAMILY/RELIGION events have player_id, we can show them with player context in the UI.

**Current State:**
- These events show `player_name = NULL` in UI
- User sees "Memory | NULL | Attacked Unit (Raiders)"

**Desired State:**
- Show which player's perspective: "Memory | Fluffbunny | Attacked Unit (Raiders)"
- Makes it clear whose memory/experience this represents

**Changes Needed:**

The query already has this JOIN:
```python
LEFT JOIN players p ON e.player_id = p.player_id AND e.match_id = p.match_id
```

**This should work automatically!** Once player_id is populated, the JOIN will resolve player_name.

**Verification Query:**
```bash
uv run duckdb tournament_data.duckdb -readonly -c "
SELECT
    turn_number,
    event_type,
    p.player_name,
    description
FROM events e
LEFT JOIN players p ON e.player_id = p.player_id AND e.match_id = p.match_id
WHERE e.match_id = 11
    AND e.event_type LIKE 'MEMORYTRIBE_%'
    AND e.turn_number = 63
ORDER BY turn_number
"
```

**Expected Output:**
```
┌─────────────┬────────────────────────────┬─────────────┬────────────────────────────┐
│ turn_number │         event_type         │ player_name │        description         │
├─────────────┼────────────────────────────┼─────────────┼────────────────────────────┤
│          63 │ MEMORYTRIBE_ATTACKED_ENEMY │ Fluffbunny  │ Attacked Enemy (Scythians) │
│          63 │ MEMORYTRIBE_ATTACKED_UNIT  │ Becked      │ Attacked Unit (Raiders)    │
│          63 │ MEMORYTRIBE_ATTACKED_UNIT  │ Becked      │ Attacked Unit (Raiders)    │
```

**If player_name is still NULL:**
- Check the JOIN clause in get_event_timeline()
- Verify match_id is included in JOIN condition
- Ensure player_id was actually populated in Task 4

**No code changes needed** if JOIN is correct. Just verify it works.

**Commit:** `verify: Event timeline shows player names for MEMORYTRIBE events`

---

### Task 7: Update UI to Show Player Context

**File:** `tournament_visualizer/pages/matches.py`

**Section:** Event Details table (lines 286-298)

**Current Columns:**
- Turn
- Category
- Player  ← This will now show names instead of NULL
- Description

**Goal:** Verify UI displays player names correctly for MEMORYTRIBE/FAMILY/RELIGION events.

**Testing:**
1. Restart the application:
```bash
uv run python manage.py restart
```

2. Navigate to http://localhost:8050/matches

3. Select "Becked vs Fluffbunny" match

4. Go to "Turn Progression" tab

5. Look at Event Details table for turn 63

**Expected Results:**
- MEMORYTRIBE_ATTACKED_ENEMY shows player name (not NULL)
- MEMORYTRIBE_ATTACKED_UNIT shows player name (not NULL)
- Player column indicates whose perspective/memory

**Before Fix:**
```
| 63 | Memory | (empty) | Attacked Unit (Raiders) |
```

**After Fix:**
```
| 63 | Memory | Becked | Attacked Unit (Raiders) |
```

**If Still Broken:**
- Check matches.py callback `update_turns_table()`
- Verify it's using the correct query method
- Check browser console for JavaScript errors
- Verify data actually has player_id (query database directly)

**No code changes expected** - just validation.

**Commit:** `verify: UI displays player names for memory events`

---

### Task 8: Add Validation Script

**File:** `scripts/validate_memorydata_ownership.py` (create new file)

**Goal:** Provide a quick script to verify data integrity after import.

**Code:**

```python
#!/usr/bin/env python3
"""Validate that all MemoryData events have proper player ownership.

This script checks the database to ensure the MemoryData player ownership
fix is working correctly. It should be run after re-importing data.

Usage:
    uv run python scripts/validate_memorydata_ownership.py
"""

import duckdb
import sys
from typing import Tuple


def check_event_type_ownership(conn: duckdb.DuckDBPyConnection, pattern: str) -> Tuple[int, int]:
    """Check how many events matching pattern have NULL vs valid player_id.

    Args:
        conn: Database connection
        pattern: SQL LIKE pattern (e.g., 'MEMORYTRIBE_%')

    Returns:
        Tuple of (total_events, null_count)
    """
    result = conn.execute(f"""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN player_id IS NULL THEN 1 ELSE 0 END) as null_count
        FROM events
        WHERE event_type LIKE '{pattern}'
    """).fetchone()

    return result[0], result[1]


def main():
    """Run validation checks."""
    print("=" * 60)
    print("MemoryData Player Ownership Validation")
    print("=" * 60)
    print()

    # Connect to database
    try:
        conn = duckdb.connect('tournament_data.duckdb', read_only=True)
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        print("   Make sure tournament_data.duckdb exists")
        return 1

    # Check different event type categories
    checks = [
        ('MEMORYTRIBE_%', 'MEMORYTRIBE Events'),
        ('MEMORYFAMILY_%', 'MEMORYFAMILY Events'),
        ('MEMORYRELIGION_%', 'MEMORYRELIGION Events'),
        ('MEMORYCHARACTER_%', 'MEMORYCHARACTER Events'),
        ('MEMORYPLAYER_%', 'MEMORYPLAYER Events (should also work)'),
    ]

    all_passed = True

    for pattern, label in checks:
        total, null_count = check_event_type_ownership(conn, pattern)

        if total == 0:
            print(f"⚠️  {label}: No events found (OK - may not exist in data)")
            continue

        valid_count = total - null_count
        percentage = (valid_count / total * 100) if total > 0 else 0

        if null_count == 0:
            print(f"✅ {label}: {total} events, ALL have player_id ({percentage:.1f}%)")
        else:
            print(f"❌ {label}: {total} events, {null_count} have NULL player_id ({percentage:.1f}% valid)")
            all_passed = False

    print()
    print("=" * 60)

    if all_passed:
        print("✅ All validation checks passed!")
        print()
        print("Player ownership is correctly assigned for all MemoryData events.")
        return 0
    else:
        print("❌ Some validation checks failed!")
        print()
        print("Action required:")
        print("1. Check if parser fix is implemented correctly")
        print("2. Re-import data: uv run python import_tournaments.py --directory saves --force")
        print("3. Run this script again to verify")
        return 1


if __name__ == '__main__':
    sys.exit(main())
```

**Make Executable:**
```bash
chmod +x scripts/validate_memorydata_ownership.py
```

**How to Run:**
```bash
uv run python scripts/validate_memorydata_ownership.py
```

**Expected Output (Success):**
```
============================================================
MemoryData Player Ownership Validation
============================================================

✅ MEMORYTRIBE Events: 72 events, ALL have player_id (100.0%)
✅ MEMORYFAMILY Events: 37 events, ALL have player_id (100.0%)
✅ MEMORYRELIGION Events: 45 events, ALL have player_id (100.0%)
✅ MEMORYCHARACTER Events: 12 events, ALL have player_id (100.0%)
✅ MEMORYPLAYER Events (should also work): 95 events, ALL have player_id (100.0%)

============================================================
✅ All validation checks passed!

Player ownership is correctly assigned for all MemoryData events.
```

**Commit:** `chore: Add validation script for MemoryData player ownership`

---

### Task 9: Update Documentation

**Files:**
- `docs/developer-guide.md` (update)
- `CLAUDE.md` (update)

**Goal:** Document the fix for future developers.

**Changes to CLAUDE.md:**

Add new section under "Old World Save File Structure":

```markdown
### Memory Event Ownership

**Key Concept**: MemoryData events are stored in a player's MemoryList, representing that player's perspective/memory.

**XML Structure:**
```xml
<Player ID="0">  <!-- Owner player -->
  <MemoryList>
    <MemoryData>
      <Type>MEMORYPLAYER_ATTACKED_CITY</Type>
      <Player>1</Player>  <!-- Subject player (opponent) -->
      <Turn>63</Turn>
    </MemoryData>
    <MemoryData>
      <Type>MEMORYTRIBE_ATTACKED_UNIT</Type>
      <Tribe>TRIBE_RAIDERS</Tribe>  <!-- No <Player> child -->
      <Turn>63</Turn>
    </MemoryData>
  </MemoryList>
</Player>
```

**Player ID Assignment:**

1. **MEMORYPLAYER_* events**: Use `<Player>` child element (the opponent/subject)
   - Example: If Becked's memory says "MEMORYPLAYER_ATTACKED_CITY Player=1",
     it means Becked remembers Fluffbunny (Player 1) attacking a city

2. **MEMORYTRIBE/FAMILY/RELIGION_* events**: Use owner `Player[@ID]` (the viewer)
   - Example: If Becked's memory says "MEMORYTRIBE_ATTACKED_UNIT Tribe=Raiders",
     it means Becked witnessed/experienced Raiders attacking units
   - No `<Player>` child element exists for these events

**Database Mapping:**
- XML `Player[@ID="0"]` → Database `player_id=1`
- XML `Player[@ID="1"]` → Database `player_id=2`
- Consistent with LogData event mapping
```

**Changes to docs/developer-guide.md:**

Add new section under "Data Parsing":

```markdown
### Parsing MemoryData Events

When parsing MemoryData events, it's critical to preserve player ownership context:

**DO:**
```python
# Iterate through Player elements first
for player_element in root.findall('.//Player[@ID]'):
    owner_id = player_element.get('ID')
    memory_list = player_element.find('MemoryList')
    for mem in memory_list.findall('MemoryData'):
        # Process with owner_id context
```

**DON'T:**
```python
# Global search loses ownership context!
for mem in root.findall('.//MemoryData'):  # ❌ WRONG
    # Can't tell which player owns this memory
```

**Why:** MemoryData elements without a `<Player>` child (e.g., MEMORYTRIBE_*)
need to inherit their player_id from the parent `Player[@ID]` that owns the MemoryList.

**Validation:**
After any parser changes affecting MemoryData, run:
```bash
uv run python scripts/validate_memorydata_ownership.py
```
```

**Commit:** `docs: Document MemoryData player ownership pattern`

---

### Task 10: Final Testing and Verification

**Goal:** Comprehensive end-to-end test of the entire fix.

**Test Checklist:**

1. **Parser Unit Tests:**
```bash
uv run pytest tests/test_parser_memorydata.py -v
# All tests should pass
```

2. **Integration Tests:**
```bash
uv run pytest -v
# No regressions in any tests
```

3. **Database Validation:**
```bash
uv run python scripts/validate_memorydata_ownership.py
# All checks should pass
```

4. **Manual UI Testing:**
```bash
# Start server
uv run python manage.py start

# Navigate to http://localhost:8050/matches
# Select a match (e.g., Becked vs Fluffbunny)
# View Event Details table
# Verify:
# - MEMORYTRIBE events show player names
# - MEMORYFAMILY events show player names
# - MEMORYRELIGION events show player names
# - No events show NULL in Player column (except global events if any)
```

5. **Data Integrity Check:**
```bash
uv run duckdb tournament_data.duckdb -readonly -c "
-- Should return 0 (no NULL player_ids for memory events)
SELECT COUNT(*)
FROM events
WHERE (event_type LIKE 'MEMORYTRIBE_%'
       OR event_type LIKE 'MEMORYFAMILY_%'
       OR event_type LIKE 'MEMORYRELIGION_%')
  AND player_id IS NULL
"
```

6. **Code Quality:**
```bash
# Format code
uv run black tournament_visualizer/ tests/ scripts/

# Lint
uv run ruff check tournament_visualizer/ tests/ scripts/

# Fix linting issues
uv run ruff check --fix tournament_visualizer/ tests/ scripts/
```

**Expected Results:**
- [ ] All tests pass
- [ ] Validation script passes
- [ ] UI shows player names for all memory events
- [ ] No NULL player_ids in database for MEMORY* events
- [ ] Code is formatted and linted
- [ ] Documentation is updated

**Final Commit:** `chore: Final verification of MemoryData player ownership fix`

---

## Summary

**Total Tasks:** 10
**Estimated Time:** 4-6 hours
**Commits:** 8-9 commits (small, focused commits)

**Key Principles Applied:**
- **TDD**: Write failing tests first (Task 1), then fix (Task 2)
- **DRY**: Reuse existing JOIN logic in queries, no duplication
- **YAGNI**: Only fix what's needed, no over-engineering
- **Frequent Commits**: Each task gets its own commit
- **Good Test Design**: Unit tests, integration tests, and validation scripts

**Success Criteria:**
1. All MEMORYTRIBE/FAMILY/RELIGION events have player_id
2. UI shows which player's perspective for memory events
3. No regressions in existing MEMORYPLAYER event handling
4. Comprehensive test coverage
5. Clear documentation for future developers

**Rollback Plan:**
If something goes wrong:
```bash
# Restore database backup
cp tournament_data.duckdb.backup_YYYYMMDD_HHMMSS tournament_data.duckdb

# Revert code changes
git revert <commit-hash>
```

**Next Steps After Completion:**
- Consider adding player perspective filter to Event Details table
- Analyze memory event patterns by player
- Use player ownership data for more detailed match analysis
