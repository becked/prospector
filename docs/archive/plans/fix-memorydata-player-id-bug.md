# Fix MemoryData Player ID Mapping Bug - Implementation Plan

> **Created: 2025-10-08**
> **Priority: Medium** - Data integrity issue affecting existing MemoryData events
> **Estimated Time: 3-5 hours**

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [The Bug Explained](#the-bug-explained)
- [Task Breakdown](#task-breakdown)
- [Success Criteria](#success-criteria)
- [Rollback Plan](#rollback-plan)

---

## Overview

### What's Broken?

The `extract_events()` method in `parser.py` incorrectly handles player IDs from MemoryData XML elements. It treats player ID `0` as invalid and converts it to `None`, when `0` is actually the first player in the match.

### Impact

**Severity: Medium**
- ~37 events per match are stored with `player_id=None` (can't be queried by player)
- ~31 events per match are misattributed to the wrong player
- Analytics queries filtered by player return incorrect results for MemoryData events
- LogData events are NOT affected (they use correct mapping)

### Why Now?

- The LogData implementation (recently completed) uses the **correct** player ID mapping
- We now have two inconsistent player ID mappings in the same codebase
- Before importing more data, we should fix this to avoid having to re-import later

### What You'll Do

1. Write failing tests that demonstrate the bug
2. Fix the player ID mapping in `extract_events()`
3. Verify all tests pass
4. Document the fix
5. Plan for database migration (data cleanup will be a separate task)

---

## Prerequisites

### Domain Knowledge

#### Old World Save File Structure

Old World save files are `.zip` archives containing XML. The XML has two places where player IDs appear:

**1. Player Element (Top-level)**
```xml
<Root>
  <Player ID="0" Name="anarkos" OnlineID="...">
    <!-- Player data -->
  </Player>
  <Player ID="1" Name="becked" OnlineID="...">
    <!-- Player data -->
  </Player>
</Root>
```

**2. MemoryData Element (Nested)**
```xml
<MemoryData>
  <Type>MEMORYPLAYER_ATTACKED_UNIT</Type>
  <Player>0</Player>  <!-- This is a child element, not an attribute -->
  <Turn>65</Turn>
</MemoryData>
```

**Key Fact:** Both use **0-based indexing** in the XML:
- Player ID `0` = First player (e.g., anarkos)
- Player ID `1` = Second player (e.g., becked)

#### Database Player ID Convention

The database uses **1-based sequential player IDs**:
- `player_id = 1` = First player in match
- `player_id = 2` = Second player in match
- `player_id = 3` = Third player in match (if FFA)

**Conversion Formula:**
```python
database_player_id = xml_player_id + 1
```

Examples:
- XML `Player ID="0"` → Database `player_id=1`
- XML `Player ID="1"` → Database `player_id=2`
- XML `Player ID="2"` → Database `player_id=3`

#### Current Architecture

```
tournament_visualizer/data/
├── parser.py          # Contains the bug in extract_events() method
├── etl.py            # Uses parser to load data into database
├── database.py       # Database schema and operations
└── queries.py        # SQL queries for analytics (not affected by this bug)
```

**Key Files:**
- `parser.py` - Lines 281-358: `extract_events()` method (contains bug at line 313)
- `tests/test_parser_logdata.py` - Existing test file (we'll add to this)
- `tests/fixtures/sample_save.xml` - Test fixture with known data

### Tools & Libraries

- **Python 3.13** (managed by `uv`)
- **pytest** - Testing framework (already set up)
- **xml.etree.ElementTree** - XML parsing (already used in parser.py)
- **DuckDB** - Database (not needed for this fix, but used for validation later)

### Key Principles

1. **TDD (Test-Driven Development)**: Write failing tests first, then fix the code
2. **DRY (Don't Repeat Yourself)**: Reuse the same mapping logic that LogData uses
3. **YAGNI (You Ain't Gonna Need It)**: Only fix the player ID mapping, don't refactor other things
4. **Frequent commits**: Commit after each task completion

---

## The Bug Explained

### Current (Broken) Code

**Location:** `tournament_visualizer/data/parser.py`, lines 311-313

```python
def extract_events(self) -> List[Dict[str, Any]]:
    """Extract game events from MemoryData elements."""
    # ... setup code ...

    for mem in memory_data_elements:
        # ... extract turn and type ...

        # BUG IS HERE:
        # Get player ID, but convert 0 to None (0 is not a valid player ID)
        raw_player_id = self._safe_int(player_elem.text) if player_elem is not None else None
        player_id = raw_player_id if raw_player_id and raw_player_id > 0 else None
        #                                              ^^^^^^^^^^^^^^
        #                                              This condition is WRONG!
```

**Problem:** The condition `raw_player_id > 0` treats `0` as invalid:
- `raw_player_id = 0` → condition is `False` → `player_id = None` ❌
- `raw_player_id = 1` → condition is `True` → `player_id = 1` (but should be 2!) ❌

### Correct Code (Already Used in LogData)

**Location:** `tournament_visualizer/data/parser.py`, lines 378-385

```python
def extract_logdata_events(self) -> List[Dict[str, Any]]:
    """Extract game events from LogData elements."""
    # ... setup code ...

    for player_elem in player_elements:
        # Get player's XML ID (0-based in XML)
        player_xml_id = player_elem.get('ID')
        if player_xml_id is None:
            continue

        # Convert to 1-based player_id for database
        # XML ID="0" is player 1, ID="1" is player 2
        player_id = int(player_xml_id) + 1  # ✅ CORRECT!
```

**Why This Works:**
- Reads 0-based ID from XML
- Adds 1 to convert to 1-based database ID
- Handles `None` separately (skips the player)

### Test Data (From `tests/fixtures/sample_save.xml`)

Your test fixture contains:
- **39 MemoryData events** with `<Player>0</Player>` (should map to player_id=1)
- **32 MemoryData events** with `<Player>1</Player>` (should map to player_id=2)

Current behavior (WRONG):
- 39 events → `player_id=None`
- 32 events → `player_id=1`

Expected behavior (CORRECT):
- 39 events → `player_id=1`
- 32 events → `player_id=2`

---

## Task Breakdown

### Phase 1: Write Failing Tests (1 hour)

#### Task 1.1: Understand the Existing Test Structure

**Goal:** Familiarize yourself with the test file and fixture

**Files to read:**
- `tests/test_parser_logdata.py` - Existing test file with good examples
- `tests/fixtures/sample_save.xml` - Test data

**What to look for:**
1. How are fixtures loaded? (Line 24-26: `@pytest.fixture` decorator)
2. How is the parser instantiated? (Line 39-40: `OldWorldSaveParser` + `parse_xml_file`)
3. What does `extract_events()` return? (List of dictionaries with event data)
4. How are tests structured? (Classes for grouping, descriptive method names)

**Expected understanding:**
- Tests use pytest fixtures for setup
- Parser has a `parse_xml_file()` method for testing with XML files
- Events are dictionaries with keys: `turn_number`, `event_type`, `player_id`, `description`, etc.

**Deliverable:** You understand how to write a test. No commit yet.

---

#### Task 1.2: Count Expected Events in Test Fixture

**Goal:** Verify the test fixture has the data we need

**Steps:**

1. Run this command to count MemoryData events with player IDs:
   ```bash
   grep -c "<Player>0</Player>" tests/fixtures/sample_save.xml
   grep -c "<Player>1</Player>" tests/fixtures/sample_save.xml
   ```

   Expected output:
   ```
   39    # Events with Player=0 (should become player_id=1)
   32    # Events with Player=1 (should become player_id=2)
   ```

2. Find a specific event to use in tests:
   ```bash
   grep -B1 -A3 "<Player>0</Player>" tests/fixtures/sample_save.xml | head -10
   ```

   Look for output like:
   ```xml
   <MemoryData>
     <Type>MEMORYPLAYER_ATTACKED_UNIT</Type>
     <Player>0</Player>
     <Turn>65</Turn>
   </MemoryData>
   ```

**Deliverable:** You know:
- How many events have `<Player>0</Player>` (should be 39)
- How many events have `<Player>1</Player>` (should be 32)
- What a MemoryData event looks like in XML

**Commit:** None (just investigation)

---

#### Task 1.3: Write Failing Test for Player ID Mapping

**Goal:** Write tests that demonstrate the bug

**Files to modify:**
- `tests/test_parser_logdata.py`

**Add this test class** at the end of the file (after `TestTechDiscoveryExtraction`):

```python
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
            e for e in events
            if e['player_id'] == 1 and e['event_type'].startswith('MEMORYPLAYER_')
        ]

        # The fixture has 39 events with <Player>0</Player>
        # They should all have player_id=1
        assert len(player_1_events) > 0, (
            "Should find events with player_id=1 for XML Player=0. "
            "Currently these are being set to None (bug!)"
        )

        # Verify no events have player_id=None for MEMORYPLAYER_* events
        player_none_events = [
            e for e in events
            if e['player_id'] is None and e['event_type'].startswith('MEMORYPLAYER_')
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
            e for e in events
            if e['player_id'] == 2 and e['event_type'].startswith('MEMORYPLAYER_')
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
            e for e in events if e['event_type'].startswith('MEMORYPLAYER_')
        ]

        player_counts = Counter(e.get('player_id') for e in memoryplayer_events)

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

    def test_memorydata_matches_logdata_player_mapping(self, sample_xml_path: Path) -> None:
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
            e['player_id'] for e in memory_events
            if e['player_id'] is not None
        )

        logdata_player_ids = set(
            e['player_id'] for e in logdata_events
            if e['player_id'] is not None
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
```

**Run the tests** to verify they fail:
```bash
uv run pytest tests/test_parser_logdata.py::TestMemoryDataPlayerIDMapping -v
```

**Expected output:** All 4 tests should **FAIL** with messages about:
- Not finding player_id=1 (because they're None)
- Not finding player_id=2 (because they're 1)
- Finding unexpected player_id=None values

**Commit:** `test: Add failing tests for MemoryData player ID mapping bug`

---

### Phase 2: Fix the Bug (30 minutes)

#### Task 2.1: Fix the Player ID Mapping Logic

**Goal:** Change the player ID mapping to match LogData's correct implementation

**Files to modify:**
- `tournament_visualizer/data/parser.py`

**Steps:**

1. **Find the bug** (line 311-313):
   ```bash
   grep -n "Get player ID, but convert 0 to None" tournament_visualizer/data/parser.py
   ```

2. **Understand the context** - The code currently reads:
   ```python
   # Get player ID, but convert 0 to None (0 is not a valid player ID)
   raw_player_id = self._safe_int(player_elem.text) if player_elem is not None else None
   player_id = raw_player_id if raw_player_id and raw_player_id > 0 else None
   ```

3. **Replace those 3 lines** with this correct implementation:
   ```python
   # Get player ID from MemoryData (0-based in XML, like LogData)
   # Convert to 1-based database player_id to match database schema
   raw_player_id = self._safe_int(player_elem.text) if player_elem is not None else None

   # Convert 0-based XML player ID to 1-based database player_id
   # XML Player=0 → database player_id=1
   # XML Player=1 → database player_id=2
   # This matches the LogData mapping in extract_logdata_events()
   player_id = (raw_player_id + 1) if raw_player_id is not None else None
   ```

**Explanation of the fix:**
- `raw_player_id + 1` converts 0→1, 1→2, 2→3, etc.
- We only do this if `raw_player_id is not None` (preserves None for events without player data)
- We removed the `raw_player_id > 0` check that was causing the bug

**Visual diff:**
```diff
- # Get player ID, but convert 0 to None (0 is not a valid player ID)
+ # Get player ID from MemoryData (0-based in XML, like LogData)
+ # Convert to 1-based database player_id to match database schema
  raw_player_id = self._safe_int(player_elem.text) if player_elem is not None else None
- player_id = raw_player_id if raw_player_id and raw_player_id > 0 else None
+
+ # Convert 0-based XML player ID to 1-based database player_id
+ # XML Player=0 → database player_id=1
+ # XML Player=1 → database player_id=2
+ # This matches the LogData mapping in extract_logdata_events()
+ player_id = (raw_player_id + 1) if raw_player_id is not None else None
```

**Commit:** `fix: Correct MemoryData player ID mapping to match LogData`

---

#### Task 2.2: Verify Tests Now Pass

**Goal:** Confirm the fix works

**Steps:**

1. **Run the new tests:**
   ```bash
   uv run pytest tests/test_parser_logdata.py::TestMemoryDataPlayerIDMapping -v
   ```

   **Expected output:** All 4 tests should **PASS** ✅

2. **Run ALL tests** to make sure you didn't break anything:
   ```bash
   uv run pytest tests/test_parser_logdata.py -v
   ```

   **Expected output:** All 14 tests should pass (10 original + 4 new)

3. **If any tests fail:**
   - Read the error message carefully
   - Check your line numbers (did you edit the right place?)
   - Verify the indentation matches the original code
   - Compare your change to the LogData code (lines 378-385)

**Deliverable:** All tests pass

**Commit:** None (tests passing is verification, not a change)

---

### Phase 3: Manual Verification (30 minutes)

#### Task 3.1: Test with Real Save File

**Goal:** Verify the fix works with actual game data, not just the test fixture

**Steps:**

1. **Find a real save file:**
   ```bash
   ls -lh saves/*.zip | head -1
   ```

2. **Create a verification script** (`scripts/verify_player_id_fix.py`):
   ```python
   #!/usr/bin/env python3
   """Verify that MemoryData player ID mapping is fixed."""

   from pathlib import Path
   from collections import Counter
   from tournament_visualizer.data.parser import OldWorldSaveParser


   def verify_player_id_mapping(save_file: Path) -> None:
       """Verify player ID mapping for a save file."""
       print(f"Testing: {save_file.name}")
       print("=" * 60)

       parser = OldWorldSaveParser(str(save_file))
       parser.extract_and_parse()

       # Extract both event types
       memory_events = parser.extract_events()
       logdata_events = parser.extract_logdata_events()

       # Count player IDs in MemoryData
       memory_player_counts = Counter(
           e.get('player_id') for e in memory_events
           if e['event_type'].startswith('MEMORYPLAYER_')
       )

       # Count player IDs in LogData
       logdata_player_counts = Counter(
           e.get('player_id') for e in logdata_events
       )

       print("\nMemoryData Player Distribution:")
       for player_id in sorted(memory_player_counts.keys(), key=lambda x: (x is None, x)):
           count = memory_player_counts[player_id]
           print(f"  player_id={player_id}: {count} events")

       print("\nLogData Player Distribution:")
       for player_id in sorted(logdata_player_counts.keys(), key=lambda x: (x is None, x)):
           count = logdata_player_counts[player_id]
           print(f"  player_id={player_id}: {count} events")

       # Validation checks
       print("\nValidation:")

       # Check 1: No player_id=None for MEMORYPLAYER events
       if memory_player_counts.get(None, 0) == 0:
           print("  ✅ No MEMORYPLAYER events with player_id=None")
       else:
           print(f"  ❌ Found {memory_player_counts.get(None, 0)} MEMORYPLAYER events with player_id=None")

       # Check 2: MemoryData and LogData have same player IDs
       memory_ids = set(k for k in memory_player_counts.keys() if k is not None)
       logdata_ids = set(k for k in logdata_player_counts.keys() if k is not None)

       if memory_ids == logdata_ids:
           print(f"  ✅ MemoryData and LogData have same player IDs: {sorted(memory_ids)}")
       else:
           print(f"  ❌ MemoryData IDs {memory_ids} != LogData IDs {logdata_ids}")

       # Check 3: All player IDs are 1-based (1, 2, 3, ...)
       all_ids = memory_ids | logdata_ids
       if all_ids and min(all_ids) >= 1:
           print(f"  ✅ All player IDs are 1-based (min={min(all_ids)})")
       else:
           print(f"  ❌ Player IDs are not 1-based: {sorted(all_ids)}")

       print()


   if __name__ == '__main__':
       # Test with all save files in saves/
       saves_dir = Path('saves')
       save_files = list(saves_dir.glob('*.zip'))

       if not save_files:
           print("No save files found in saves/")
           exit(1)

       print(f"Found {len(save_files)} save files to test\n")

       # Test first 3 files (don't need to test all for verification)
       for save_file in save_files[:3]:
           try:
               verify_player_id_mapping(save_file)
           except Exception as e:
               print(f"❌ Error processing {save_file.name}: {e}\n")

       print("Verification complete!")
   ```

3. **Run the verification script:**
   ```bash
   chmod +x scripts/verify_player_id_fix.py
   uv run python scripts/verify_player_id_fix.py
   ```

4. **Expected output** for each save file:
   ```
   Testing: match_123_player1-player2.zip
   ============================================================

   MemoryData Player Distribution:
     player_id=1: 45 events
     player_id=2: 38 events

   LogData Player Distribution:
     player_id=1: 68 events
     player_id=2: 63 events

   Validation:
     ✅ No MEMORYPLAYER events with player_id=None
     ✅ MemoryData and LogData have same player IDs: [1, 2]
     ✅ All player IDs are 1-based (min=1)
   ```

**What to look for:**
- ✅ No `player_id=None` for MEMORYPLAYER events
- ✅ MemoryData and LogData have the same player IDs
- ✅ All player IDs start at 1 (not 0)

**If you see any ❌:**
- Double-check your fix in parser.py
- Make sure you're adding 1 to the raw_player_id
- Verify you didn't accidentally change LogData extraction

**Commit:** `test: Add verification script for player ID mapping`

---

### Phase 4: Documentation (45 minutes)

#### Task 4.1: Add Code Comments Explaining the Fix

**Goal:** Help future developers understand why this mapping exists

**Files to modify:**
- `tournament_visualizer/data/parser.py`

**Step 1:** Update the docstring for `extract_events()` (around line 281)

**Find this:**
```python
def extract_events(self) -> List[Dict[str, Any]]:
    """Extract game events from MemoryData elements.

    This is the only historical data available in Old World save files.

    Returns:
        List of event dictionaries from memory data
    """
```

**Replace with:**
```python
def extract_events(self) -> List[Dict[str, Any]]:
    """Extract game events from MemoryData elements.

    MemoryData contains character and diplomatic memories stored by the game AI.
    This provides limited historical data compared to LogData.

    Player ID Mapping:
        MemoryData uses 0-based player IDs in XML (Player=0, Player=1, ...).
        These are converted to 1-based database player IDs (player_id=1, 2, ...).
        This matches the mapping used in extract_logdata_events().

        Example: XML <Player>0</Player> → database player_id=1
                 XML <Player>1</Player> → database player_id=2

    Returns:
        List of event dictionaries from memory data, with player IDs mapped
        to 1-based database IDs for consistency with LogData events.
    """
```

**Step 2:** Verify the inline comments you added earlier are clear

The comments you added in Task 2.1 should already explain:
- Why we're doing the conversion (0-based XML → 1-based database)
- The mapping formula (raw_player_id + 1)
- That this matches LogData behavior

**Commit:** `docs: Add player ID mapping documentation to extract_events()`

---

#### Task 4.2: Update the Implementation Plan Document

**Goal:** Document that this bug has been fixed

**Files to modify:**
- `docs/plans/logdata-ingestion-implementation-plan.md`

**Steps:**

1. Find the section about the MemoryData player ID bug (around line 156)

2. Add a note that it's been fixed:

**Find this section:**
```markdown
**Questions to answer:**
1. What does `extract_events()` return? (List of dict with what keys?)
2. How does it map player IDs? (See line 294-295 - NOTE: This has a bug for player_id 0!)
3. What lookup tables does it build? (Lines 277-278)
4. How are events stored in the database? (Check `etl.py` for usage)
```

**Update to:**
```markdown
**Questions to answer:**
1. What does `extract_events()` return? (List of dict with what keys?)
2. How does it map player IDs? (See line ~311-318 - FIXED: Now correctly maps 0→1, 1→2)
3. What lookup tables does it build? (Lines 277-278)
4. How are events stored in the database? (Check `etl.py` for usage)
```

3. Add a note at the top of the document:

**Find this section (near the top):**
```markdown
> **Updated: 2025-10-08** - Plan corrected based on investigation of actual save file structure.
> See `docs/plans/logdata-investigation-findings.md` for detailed findings.
> Key changes: LogData is in `PermanentLogList` (not `TurnSummary`), no deduplication needed.
```

**Add after it:**
```markdown
> **Bug Fix (2025-10-08):** MemoryData player ID mapping bug has been fixed.
> Previously, XML Player=0 was incorrectly converted to None instead of player_id=1.
> See `docs/plans/fix-memorydata-player-id-bug.md` for details.
```

**Commit:** `docs: Update LogData plan to reflect MemoryData player ID fix`

---

#### Task 4.3: Create a Bug Report Document

**Goal:** Document what was wrong and how it was fixed for future reference

**Files to create:**
- `docs/bugs/memorydata-player-id-mapping.md`

**Create the file:**
```bash
mkdir -p docs/bugs
```

**Content:**
```markdown
# MemoryData Player ID Mapping Bug

**Status:** ✅ FIXED (2025-10-08)
**Severity:** Medium - Data integrity issue
**Affected Code:** `tournament_visualizer/data/parser.py::extract_events()`
**Fix Commit:** [commit hash from your fix]

## Summary

The `extract_events()` method incorrectly treated XML `Player=0` as invalid, converting it to `None` instead of mapping it to database `player_id=1`. This caused:
- ~37 events per match to be lost (stored with `player_id=None`)
- ~31 events per match to be misattributed to the wrong player

## Root Cause

**Incorrect assumption:** The code comment claimed "0 is not a valid player ID", but this was wrong. Player ID 0 is the first player in Old World XML files.

**Buggy code (lines 311-313):**
```python
# Get player ID, but convert 0 to None (0 is not a valid player ID)
raw_player_id = self._safe_int(player_elem.text) if player_elem is not None else None
player_id = raw_player_id if raw_player_id and raw_player_id > 0 else None
#                                              ^^^^^^^^^^^^^^
#                                              BUG: treats 0 as invalid
```

**Behavior:**
- XML `<Player>0</Player>` → `player_id = None` ❌
- XML `<Player>1</Player>` → `player_id = 1` ❌ (should be 2)

## The Fix

**Correct code:**
```python
# Get player ID from MemoryData (0-based in XML, like LogData)
# Convert to 1-based database player_id to match database schema
raw_player_id = self._safe_int(player_elem.text) if player_elem is not None else None

# Convert 0-based XML player ID to 1-based database player_id
# XML Player=0 → database player_id=1
# XML Player=1 → database player_id=2
# This matches the LogData mapping in extract_logdata_events()
player_id = (raw_player_id + 1) if raw_player_id is not None else None
```

**New behavior:**
- XML `<Player>0</Player>` → `player_id = 1` ✅
- XML `<Player>1</Player>` → `player_id = 2` ✅

## Impact

**Before fix:**
- Test fixture: 37 events with `player_id=None`, 31 with `player_id=1`
- Real save files: ~40% of MEMORYPLAYER events had `player_id=None`
- Analytics queries filtered by player returned incomplete/incorrect results

**After fix:**
- Test fixture: 39 events with `player_id=1`, 32 with `player_id=2`
- All MEMORYPLAYER events have valid player IDs
- Consistent with LogData player ID mapping

## Why It Wasn't Caught Earlier

1. **MemoryData has limited historical value** - LogData provides much richer data
2. **No existing tests for player ID mapping** - Tests were added as part of this fix
3. **LogData worked correctly** - The bug only affected MemoryData extraction

## Related Files

- `tournament_visualizer/data/parser.py` - Contains the fix
- `tests/test_parser_logdata.py` - Tests added to prevent regression
- `scripts/verify_player_id_fix.py` - Verification script
- `docs/plans/fix-memorydata-player-id-bug.md` - Implementation plan

## Data Migration

**Note:** This fix only affects **newly imported** data. Existing database records from before the fix will still have incorrect player IDs for MemoryData events.

**To fix existing data:**
1. Backup the database
2. Delete all matches (will cascade to events)
3. Re-import all save files with the fixed parser

See Phase 5 of the implementation plan for migration steps.

## Prevention

**Tests added:**
- `TestMemoryDataPlayerIDMapping::test_player_zero_maps_to_player_id_one`
- `TestMemoryDataPlayerIDMapping::test_player_one_maps_to_player_id_two`
- `TestMemoryDataPlayerIDMapping::test_player_id_distribution_matches_xml`
- `TestMemoryDataPlayerIDMapping::test_memorydata_matches_logdata_player_mapping`

These tests will fail if the bug is reintroduced.
```

**Commit:** `docs: Add bug report for MemoryData player ID mapping issue`

---

### Phase 5: Database Migration Planning (Optional - 1 hour)

**Note:** This phase is **OPTIONAL** if you don't have existing data in the database. If the database is empty or you're okay with deleting and re-importing, skip to Phase 6.

#### Task 5.1: Check If Database Has Data

**Goal:** Determine if we need to migrate existing data

**Steps:**

1. **Check if database exists:**
   ```bash
   ls -lh tournament_data.duckdb
   ```

2. **If it exists, count events:**
   ```bash
   uv run duckdb tournament_data.duckdb -c "
   SELECT
     COUNT(*) as total_events,
     SUM(CASE WHEN player_id IS NULL THEN 1 ELSE 0 END) as events_with_null_player,
     SUM(CASE WHEN event_type LIKE 'MEMORYPLAYER_%' THEN 1 ELSE 0 END) as memoryplayer_events
   FROM events;
   "
   ```

3. **Decide on migration strategy:**

   **Option A: Database is empty or has no events**
   - Skip migration
   - Just re-import save files (will use fixed parser)

   **Option B: Database has events but you're okay losing them**
   - Delete the database: `rm tournament_data.duckdb`
   - Re-import save files (will use fixed parser)

   **Option C: Database has important data that must be preserved**
   - Follow the migration steps below

**Deliverable:** You know which option to follow

---

#### Task 5.2: Create Database Backup (Option C only)

**Goal:** Protect existing data before migration

**Steps:**

1. **Create backup:**
   ```bash
   timestamp=$(date +%Y%m%d_%H%M%S)
   cp tournament_data.duckdb "tournament_data.duckdb.backup_before_player_id_fix_${timestamp}"
   ```

2. **Verify backup:**
   ```bash
   ls -lh tournament_data.duckdb*
   ```

   You should see two files:
   - `tournament_data.duckdb` (original)
   - `tournament_data.duckdb.backup_before_player_id_fix_20251008_143022` (backup)

**Commit:** `chore: Backup database before player ID migration`

---

#### Task 5.3: Create Migration Script (Option C only)

**Goal:** Update existing MemoryData events with correct player IDs

**Note:** This is complex because we need to:
1. Find which match each event belongs to
2. Look up the original XML to get the raw player ID
3. Update the event with the corrected player_id

**Simpler approach:** Just delete and re-import:

```bash
# Delete all matches (cascades to events)
uv run duckdb tournament_data.duckdb -c "DELETE FROM matches;"

# Re-import all save files
uv run python import_tournaments.py --directory saves
```

**Why this is simpler:**
- MemoryData events don't contain unique data (LogData has better info)
- Re-importing takes ~1 minute for 15 matches
- No risk of migration script bugs

**Commit:** None (this is a manual operation)

---

### Phase 6: Final Validation (30 minutes)

#### Task 6.1: Run Full Test Suite

**Goal:** Ensure nothing is broken

**Steps:**

1. **Run all tests:**
   ```bash
   uv run pytest -v
   ```

   **Expected:** All tests pass

2. **Check test coverage** (optional but recommended):
   ```bash
   uv run pytest --cov=tournament_visualizer.data.parser --cov-report=term-missing
   ```

   Look for the `extract_events` method - it should have high coverage now.

**Deliverable:** All tests pass ✅

**Commit:** None (just verification)

---

#### Task 6.2: Test Full ETL Pipeline

**Goal:** Verify the fix works end-to-end with database import

**Steps:**

1. **Import one save file:**
   ```bash
   # If database exists, delete it for clean test
   rm -f tournament_data.duckdb

   # Import one save file
   uv run python scripts/import_tournaments.py --directory saves
   ```

2. **Query the database to verify player IDs:**
   ```bash
   uv run duckdb tournament_data.duckdb -c "
   SELECT
     event_type,
     player_id,
     COUNT(*) as count
   FROM events
   WHERE event_type LIKE 'MEMORYPLAYER_%'
   GROUP BY event_type, player_id
   ORDER BY event_type, player_id;
   "
   ```

3. **Expected output:**
   ```
   event_type                    player_id  count
   ─────────────────────────────────────────────
   MEMORYPLAYER_ATTACKED_UNIT    1          20
   MEMORYPLAYER_ATTACKED_UNIT    2          15
   MEMORYPLAYER_KILLED_UNIT      1          5
   MEMORYPLAYER_KILLED_UNIT      2          3
   ```

4. **Check for NULL player IDs:**
   ```bash
   uv run duckdb tournament_data.duckdb -c "
   SELECT COUNT(*) as events_with_null_player
   FROM events
   WHERE event_type LIKE 'MEMORYPLAYER_%' AND player_id IS NULL;
   "
   ```

   **Expected output:**
   ```
   events_with_null_player
   ─────────────────────
   0
   ```

**What to look for:**
- ✅ MEMORYPLAYER events have `player_id` values (not NULL)
- ✅ Player IDs are 1 and 2 (not 0)
- ✅ No events have `player_id = NULL` for MEMORYPLAYER types

**If you see problems:**
- Check that the fix is actually in parser.py
- Verify you deleted the old database before re-importing
- Make sure scripts/import_tournaments.py is using the updated parser

**Deliverable:** Database has correct player IDs

**Commit:** None (just verification)

---

#### Task 6.3: Compare MemoryData and LogData Player IDs

**Goal:** Verify consistency between MemoryData and LogData

**Steps:**

1. **Query both event sources:**
   ```bash
   uv run duckdb tournament_data.duckdb -c "
   WITH event_source AS (
     SELECT
       CASE
         WHEN event_type LIKE 'MEMORY%' THEN 'MemoryData'
         ELSE 'LogData'
       END as source,
       player_id,
       COUNT(*) as count
     FROM events
     WHERE player_id IS NOT NULL
     GROUP BY source, player_id
   )
   SELECT * FROM event_source ORDER BY source, player_id;
   "
   ```

2. **Expected output:**
   ```
   source        player_id  count
   ─────────────────────────────
   LogData       1          68
   LogData       2          63
   MemoryData    1          45
   MemoryData    2          38
   ```

**What to verify:**
- ✅ Both MemoryData and LogData have the same player_id values (1, 2)
- ✅ No 0-based IDs (like player_id=0)
- ✅ Counts are reasonable (MemoryData has fewer events, which is expected)

**Deliverable:** MemoryData and LogData use consistent player ID mapping

**Commit:** None (just verification)

---

## Success Criteria

You're done when ALL of these are true:

### Code Quality ✅
- [ ] Bug fix is implemented in `parser.py`
- [ ] Code follows the same pattern as LogData extraction
- [ ] Comments explain the 0→1, 1→2 mapping
- [ ] Docstring updated with player ID mapping explanation

### Testing ✅
- [ ] 4 new tests added to `TestMemoryDataPlayerIDMapping`
- [ ] All 14 tests in `test_parser_logdata.py` pass
- [ ] Verification script confirms fix with real save files
- [ ] No MEMORYPLAYER events have `player_id=None`

### Database ✅
- [ ] Full ETL pipeline works (import completes without errors)
- [ ] Database events table has correct player IDs
- [ ] MemoryData and LogData have same player_id values (1, 2, ...)
- [ ] Zero events with `player_id=NULL` for MEMORYPLAYER events

### Documentation ✅
- [ ] `extract_events()` docstring updated
- [ ] Inline comments explain the fix
- [ ] Bug report created in `docs/bugs/`
- [ ] Implementation plan updated to note fix

### Git History ✅
- [ ] Commits follow the plan's sequence
- [ ] Commit messages are clear and descriptive
- [ ] Each commit is atomic (one logical change)

---

## Rollback Plan

If something goes wrong, you can rollback:

### Rollback Code Changes
```bash
# If you haven't committed yet
git checkout tournament_visualizer/data/parser.py
git checkout tests/test_parser_logdata.py

# If you've committed but want to undo
git revert <commit-hash-of-fix>
```

### Restore Database Backup
```bash
# If you created a backup
cp tournament_data.duckdb.backup_before_player_id_fix_* tournament_data.duckdb
```

### Re-import with Old Code
```bash
# Checkout old parser
git checkout HEAD~1 tournament_visualizer/data/parser.py

# Delete database
rm tournament_data.duckdb

# Re-import (will use old buggy parser)
uv run python scripts/import_tournaments.py --directory saves

# Then fix the bug again...
```

---

## Common Issues and Solutions

### Issue 1: Tests still fail after fix

**Symptom:**
```
AssertionError: Should find events with player_id=1 for XML Player=0
```

**Solution:**
1. Check that you edited the RIGHT line in parser.py (line ~313)
2. Verify you're adding 1: `player_id = (raw_player_id + 1)`
3. Make sure you didn't accidentally edit LogData code
4. Check indentation (Python is whitespace-sensitive)

**Debug command:**
```bash
grep -A5 "raw_player_id = self._safe_int(player_elem.text)" tournament_visualizer/data/parser.py
```

You should see your new code, not the old `raw_player_id > 0` check.

---

### Issue 2: Import fails with "division by zero" or similar error

**Symptom:**
```
ZeroDivisionError: division by zero
```

**Solution:**
This might happen if you broke something else while editing. Check:
1. Did you only change lines 311-318?
2. Is the indentation correct?
3. Did you accidentally delete something?

**Debug:**
```bash
git diff tournament_visualizer/data/parser.py
```

Compare your changes to the expected diff in Task 2.1.

---

### Issue 3: Database import shows NULL player IDs

**Symptom:**
```sql
SELECT COUNT(*) FROM events WHERE player_id IS NULL
-- Returns > 0 for MEMORYPLAYER events
```

**Solution:**
1. Delete the database: `rm tournament_data.duckdb`
2. Verify your code fix is correct
3. Re-import: `uv run python scripts/import_tournaments.py --directory saves`

The old database might have been imported before your fix.

---

### Issue 4: Different player IDs in MemoryData vs LogData

**Symptom:**
```
MemoryData has player_ids: {1, 2}
LogData has player_ids: {2, 3}
```

**Solution:**
This shouldn't happen if you followed the fix. But if it does:
1. Check you're testing the RIGHT file (same save file for both)
2. Verify you didn't break LogData extraction
3. Check the ETL player ID mapping in `etl.py` (lines 123-156)

The ETL might be applying an additional transformation.

---

## Estimated Timeline

- **Phase 1** (Write Tests): 1 hour
  - Task 1.1: 15 min (understand tests)
  - Task 1.2: 15 min (count events)
  - Task 1.3: 30 min (write tests)

- **Phase 2** (Fix Bug): 30 minutes
  - Task 2.1: 20 min (fix code)
  - Task 2.2: 10 min (verify tests pass)

- **Phase 3** (Manual Verification): 30 minutes
  - Task 3.1: 30 min (test with real data)

- **Phase 4** (Documentation): 45 minutes
  - Task 4.1: 15 min (code comments)
  - Task 4.2: 10 min (update plan doc)
  - Task 4.3: 20 min (bug report)

- **Phase 5** (Migration - OPTIONAL): 1 hour
  - Task 5.1: 10 min (check database)
  - Task 5.2: 10 min (backup)
  - Task 5.3: 40 min (re-import)

- **Phase 6** (Final Validation): 30 minutes
  - Task 6.1: 10 min (run tests)
  - Task 6.2: 10 min (test ETL)
  - Task 6.3: 10 min (compare sources)

**Total: 3-5 hours** (depending on whether database migration is needed)

---

## Key Learnings

After completing this fix, you should understand:

1. **Player ID Mapping Patterns**
   - XML uses 0-based indexing for arrays/lists
   - Databases typically use 1-based indexing for IDs
   - Conversion formula: `db_id = xml_id + 1`

2. **Test-Driven Development**
   - Write failing tests first (shows the bug exists)
   - Fix the code
   - Verify tests pass (proves the bug is fixed)
   - Tests prevent regression (bug won't come back)

3. **Code Consistency**
   - LogData and MemoryData should use the same mapping logic
   - DRY: Don't Repeat Yourself (same logic, same implementation)
   - Document WHY the mapping exists (future developers will thank you)

4. **Data Integrity**
   - Bugs in ETL code affect ALL imported data
   - Always verify fixes with real data, not just unit tests
   - Database migrations can be complex - sometimes re-import is simpler

---

## Getting Help

If you get stuck:

1. **Read the error message carefully** - It usually tells you what's wrong
2. **Check the git diff** - Make sure you edited the right lines
3. **Compare to LogData code** - It has the correct implementation (lines 378-385)
4. **Run the verification script** - It shows what's actually happening
5. **Check the test output** - Tests have helpful assertion messages

**Debug commands:**
```bash
# See what you changed
git diff tournament_visualizer/data/parser.py

# Run one specific test with verbose output
uv run pytest tests/test_parser_logdata.py::TestMemoryDataPlayerIDMapping::test_player_zero_maps_to_player_id_one -vv

# Check database state
uv run duckdb tournament_data.duckdb -c "SELECT event_type, player_id, COUNT(*) FROM events GROUP BY event_type, player_id LIMIT 20;"
```

---

## Next Steps After This Fix

Once this bug is fixed, consider:

1. **Add similar tests for other player ID mappings** (e.g., `extract_players()`)
2. **Review other extraction methods** for similar 0-based vs 1-based issues
3. **Document XML → Database mapping conventions** in a central location
4. **Add pre-commit hooks** to run tests automatically

This bug fix also validates the LogData implementation - it used the **correct** mapping from the start! ✅

Good luck! 🚀
