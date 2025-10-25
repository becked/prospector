# Phase 4 Implementation Issues & Required Fixes

> **Status**: Completed and archived (2025-10-25)
>
> Feature complete. See migrations/002_add_history_tables.md.

**Date:** October 9, 2025
**Status:** Incomplete - Critical Gap Identified
**Phase:** 4 - Database Integration

---

## Executive Summary

Phase 4 implementation completed **50% of the required work**. The bulk insert methods were implemented correctly and are well-tested, but **the ETL integration layer that actually calls these methods is completely missing**.

**Current Status:**
- ✅ Bulk insert methods implemented (5/5)
- ✅ Tests written and passing (7/7)
- ❌ ETL integration missing (0/5)
- ❌ Data flow never tested end-to-end

**Impact:** History data is extracted from XML files but **never saved to the database**. The new history tables will remain empty after import.

---

## Table of Contents
- [What Was Completed](#what-was-completed)
- [Critical Gap: ETL Integration Missing](#critical-gap-etl-integration-missing)
- [Understanding the Data Flow](#understanding-the-data-flow)
- [Required Implementation](#required-implementation)
- [Testing & Verification](#testing--verification)
- [Implementation Checklist](#implementation-checklist)

---

## What Was Completed

### ✅ Task 4.2: Database Insertion Methods

**File:** `tournament_visualizer/data/database.py`
**Lines:** 1125-1300

Five bulk insert methods were implemented correctly:

1. `bulk_insert_points_history()` (lines 1125-1157)
2. `bulk_insert_military_history()` (lines 1158-1191)
3. `bulk_insert_legitimacy_history()` (lines 1193-1226)
4. `bulk_insert_family_opinion_history()` (lines 1228-1262)
5. `bulk_insert_religion_opinion_history()` (lines 1264-1298)

**Quality Assessment:** ✅ Excellent
- Follows existing patterns perfectly
- Proper sequence-based ID generation
- Early return for empty data
- Correct connection handling
- Good documentation

### ✅ Test Coverage

**File:** `tests/test_database.py`
**Tests:** 7 comprehensive tests, all passing

```bash
$ uv run pytest tests/test_database.py -v -k "history"
✅ test_bulk_insert_points_history
✅ test_bulk_insert_points_history_empty
✅ test_bulk_insert_military_history
✅ test_bulk_insert_legitimacy_history
✅ test_bulk_insert_family_opinion_history
✅ test_bulk_insert_religion_opinion_history
✅ test_bulk_insert_all_history_types
```

**Quality Assessment:** ✅ Excellent
- Tests verify correct insertion
- Tests verify empty data handling
- Integration test covers all types
- All assertions passing

---

## Critical Gap: ETL Integration Missing

### Severity: 🔴 CRITICAL - Data Loss

### The Problem

The bulk insert methods **are never called** during the ETL (Extract, Transform, Load) process. This means:

1. ✅ Parser extracts history data from XML
2. ✅ Parser returns history data in dictionary
3. ❌ **ETL ignores the history data completely**
4. ❌ History data is never saved to database
5. ❌ New history tables remain empty

### Evidence

**Parser returns this data structure** (verified in `tournament_visualizer/data/parser.py:1601-1611`):

```python
return {
    "match_metadata": match_metadata,
    "players": players,
    "events": events,
    # ... other existing data ...
    "detailed_metadata": detailed_metadata,

    # NEW: Turn-by-turn history data (these are being returned)
    "yield_history": yield_history,              # ✅ IS inserted (via resources)
    "points_history": points_history,            # ❌ NOT inserted
    "military_history": military_history,        # ❌ NOT inserted
    "legitimacy_history": legitimacy_history,    # ❌ NOT inserted
    "family_opinion_history": opinion_histories["family_opinions"],  # ❌ NOT inserted
    "religion_opinion_history": opinion_histories["religion_opinions"], # ❌ NOT inserted
}
```

**ETL processes this data** (`tournament_visualizer/data/etl.py:105-257`):

```python
def _load_tournament_data(self, parsed_data: Dict[str, Any]) -> None:
    # Line 114: Insert match
    match_id = self.db.insert_match(match_metadata)

    # Line 125: Insert players
    for i, player_data in enumerate(players_data):
        player_id = self.db.insert_player(player_data)
        player_id_mapping[original_player_id] = player_id

    # Lines 158-170: Process events
    if events:
        self.db.bulk_insert_events(events)

    # Lines 189-204: Process resources (this is actually yield_history)
    if resources:
        self.db.bulk_insert_yield_history(resources)

    # Lines 206-251: Process tech, stats, units
    # ...

    # Line 254-257: Insert match metadata
    if detailed_metadata:
        self.db.insert_match_metadata(match_id, detailed_metadata)

    # ❌ METHOD ENDS HERE - No history data processing!
    # ❌ points_history, military_history, legitimacy_history,
    # ❌ family_opinion_history, religion_opinion_history
    # ❌ are all ignored!
```

### Why This Happened

Looking at the implementation plan (Phase 4, Task 4.2), the focus was on:
- Writing tests for bulk insert methods ✅
- Implementing the methods themselves ✅

But **Task 4.3 is missing from the plan**: "Integrate bulk insert methods into ETL pipeline"

The implementer likely thought Phase 4 was complete after the methods were written and tested in isolation.

---

## Understanding the Data Flow

### How ETL Works (Simplified)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. USER RUNS: uv run python scripts/import_tournaments.py  │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. ETL: process_tournament_file(save_file.zip)             │
│    → Calls parse_tournament_file(save_file.zip)            │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. PARSER: Extracts all data from XML                      │
│    → Returns dictionary with 15+ keys including:            │
│      - match_metadata, players, events                      │
│      - points_history, military_history, etc.              │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. ETL: _load_tournament_data(parsed_data)                 │
│    ⚠️  THIS IS WHERE THE GAP IS ⚠️                          │
│    → Should process ALL keys in parsed_data                 │
│    → Currently only processes 10 keys, ignores 5 new ones  │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. DATABASE: bulk_insert_*() methods save data             │
│    → These methods exist and work perfectly                 │
│    → But they're never called for history data!            │
└─────────────────────────────────────────────────────────────┘
```

### The Pattern You Need to Follow

**Existing Example** (how resources/yields are processed):

**Lines 189-204** in `tournament_visualizer/data/etl.py`:

```python
# Process resources
resources = parsed_data["resources"]
for resource_data in resources:
    resource_data["match_id"] = match_id
    # Map player_id if present
    if (
        resource_data.get("player_id")
        and resource_data["player_id"] in player_id_mapping
    ):
        resource_data["player_id"] = player_id_mapping[
            resource_data["player_id"]
        ]

if resources:
    self.db.bulk_insert_yield_history(resources)
    logger.info(f"Inserted {len(resources)} resource records")
```

**What this does:**
1. Extract the data list from `parsed_data`
2. Add `match_id` to each record
3. Map `player_id` from temporary IDs to database IDs
4. Call the bulk insert method
5. Log how many records were inserted

**You need to repeat this pattern 5 times** for the missing history data types.

---

## Required Implementation

### Task 4.3: Add ETL Integration for History Data

**File:** `tournament_visualizer/data/etl.py`
**Method:** `_load_tournament_data()`
**Location:** After line 257 (after `self.db.insert_match_metadata(match_id, detailed_metadata)`)

### Code to Add

Add this code block after the match metadata insertion:

```python
        # Process match metadata
        detailed_metadata = parsed_data.get("detailed_metadata", {})
        if detailed_metadata:
            self.db.insert_match_metadata(match_id, detailed_metadata)
            logger.info("Inserted match metadata")

        # ========================================================================
        # NEW: Process turn-by-turn history data
        # ========================================================================

        # Process points history
        points_history = parsed_data.get("points_history", [])
        for point_data in points_history:
            point_data["match_id"] = match_id
            # Map player_id if present
            if (
                point_data.get("player_id")
                and point_data["player_id"] in player_id_mapping
            ):
                point_data["player_id"] = player_id_mapping[point_data["player_id"]]

        if points_history:
            self.db.bulk_insert_points_history(points_history)
            logger.info(f"Inserted {len(points_history)} points history records")

        # Process military history
        military_history = parsed_data.get("military_history", [])
        for military_data in military_history:
            military_data["match_id"] = match_id
            # Map player_id if present
            if (
                military_data.get("player_id")
                and military_data["player_id"] in player_id_mapping
            ):
                military_data["player_id"] = player_id_mapping[
                    military_data["player_id"]
                ]

        if military_history:
            self.db.bulk_insert_military_history(military_history)
            logger.info(f"Inserted {len(military_history)} military history records")

        # Process legitimacy history
        legitimacy_history = parsed_data.get("legitimacy_history", [])
        for legitimacy_data in legitimacy_history:
            legitimacy_data["match_id"] = match_id
            # Map player_id if present
            if (
                legitimacy_data.get("player_id")
                and legitimacy_data["player_id"] in player_id_mapping
            ):
                legitimacy_data["player_id"] = player_id_mapping[
                    legitimacy_data["player_id"]
                ]

        if legitimacy_history:
            self.db.bulk_insert_legitimacy_history(legitimacy_history)
            logger.info(f"Inserted {len(legitimacy_history)} legitimacy history records")

        # Process family opinion history
        family_opinion_history = parsed_data.get("family_opinion_history", [])
        for opinion_data in family_opinion_history:
            opinion_data["match_id"] = match_id
            # Map player_id if present
            if (
                opinion_data.get("player_id")
                and opinion_data["player_id"] in player_id_mapping
            ):
                opinion_data["player_id"] = player_id_mapping[
                    opinion_data["player_id"]
                ]

        if family_opinion_history:
            self.db.bulk_insert_family_opinion_history(family_opinion_history)
            logger.info(
                f"Inserted {len(family_opinion_history)} family opinion history records"
            )

        # Process religion opinion history
        religion_opinion_history = parsed_data.get("religion_opinion_history", [])
        for opinion_data in religion_opinion_history:
            opinion_data["match_id"] = match_id
            # Map player_id if present
            if (
                opinion_data.get("player_id")
                and opinion_data["player_id"] in player_id_mapping
            ):
                opinion_data["player_id"] = player_id_mapping[
                    opinion_data["player_id"]
                ]

        if religion_opinion_history:
            self.db.bulk_insert_religion_opinion_history(religion_opinion_history)
            logger.info(
                f"Inserted {len(religion_opinion_history)} religion opinion history records"
            )
```

### Understanding the Code

**Each block follows the same 4-step pattern:**

1. **Extract data from parsed_data dictionary**
   ```python
   points_history = parsed_data.get("points_history", [])
   ```
   - Uses `.get()` with `[]` default for safety
   - If key doesn't exist, returns empty list (no crash)

2. **Add match_id and map player_id**
   ```python
   for point_data in points_history:
       point_data["match_id"] = match_id
       if point_data.get("player_id") and point_data["player_id"] in player_id_mapping:
           point_data["player_id"] = player_id_mapping[point_data["player_id"]]
   ```
   - Each record needs to know which match it belongs to
   - Player IDs from parser (1, 2) must be mapped to database IDs (could be 47, 48)
   - The `player_id_mapping` dictionary was built earlier (line 120-127)

3. **Call bulk insert if data exists**
   ```python
   if points_history:
       self.db.bulk_insert_points_history(points_history)
   ```
   - Only insert if there's data (don't call with empty list)
   - Calls the method you already implemented in database.py

4. **Log success**
   ```python
   logger.info(f"Inserted {len(points_history)} points history records")
   ```
   - Helpful for debugging and monitoring imports

### Why Player ID Mapping is Critical

**Example scenario:**

```
Game XML has:
  Player ID="0" → Parser converts to player_id=1
  Player ID="1" → Parser converts to player_id=2

Database already has players from previous matches:
  match 1: player_id=1, player_id=2
  match 2: player_id=3, player_id=4
  match 3: player_id=5, player_id=6

When inserting match 4:
  Parser returns player_id=1 and player_id=2
  But database assigns player_id=7 and player_id=8

  Without mapping:
    points_history would reference player_id=1 (wrong player!)

  With mapping:
    player_id_mapping = {1: 7, 2: 8}
    points_history[0]["player_id"] = 1 → mapped to 7 ✅
    points_history[1]["player_id"] = 2 → mapped to 8 ✅
```

---

## Testing & Verification

### Test Plan

After implementing the ETL integration, you must verify the complete data flow.

#### Test 1: Code Verification (Before Running)

**Check that methods are called:**

```bash
# Verify all bulk insert calls exist in ETL
grep -c "bulk_insert_points_history" tournament_visualizer/data/etl.py
# Expected: 1

grep -c "bulk_insert_military_history" tournament_visualizer/data/etl.py
# Expected: 1

grep -c "bulk_insert_legitimacy_history" tournament_visualizer/data/etl.py
# Expected: 1

grep -c "bulk_insert_family_opinion_history" tournament_visualizer/data/etl.py
# Expected: 1

grep -c "bulk_insert_religion_opinion_history" tournament_visualizer/data/etl.py
# Expected: 1
```

#### Test 2: Integration Test (Write a Test)

**Create:** `tests/test_etl_integration.py`

```python
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

    try:
        # Initialize database with schema
        db = TournamentDatabase(db_path=db_path, read_only=False)
        db.create_schema()

        # Create ETL instance
        etl = TournamentETL(database=db)

        # Process a real save file
        # NOTE: Adjust path to an actual test save file
        test_save_file = "saves/match_001.zip"  # Use actual file

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
```

**Run the test:**

```bash
uv run pytest tests/test_etl_integration.py -v -s
```

**Expected output:**

```
tests/test_etl_integration.py::test_history_data_etl_integration
✅ Integration test passed!
   Points records: 138
   Military records: 138
   Legitimacy records: 138
   Family opinion records: 276
   Religion opinion records: 138
PASSED
```

#### Test 3: Real Data Import (Manual)

**Step 1: Backup current database**

```bash
cp tournament_data.duckdb tournament_data.duckdb.backup_before_history_test
```

**Step 2: Clear existing data (optional, for clean test)**

```bash
uv run duckdb tournament_data.duckdb <<SQL
DELETE FROM player_points_history;
DELETE FROM player_military_history;
DELETE FROM player_legitimacy_history;
DELETE FROM family_opinion_history;
DELETE FROM religion_opinion_history;
SQL
```

**Step 3: Import ONE test file**

```bash
uv run python -c "
from tournament_visualizer.data.etl import TournamentETL
from tournament_visualizer.data.database import get_database

etl = TournamentETL(get_database())
success = etl.process_tournament_file('saves/match_001.zip')
print(f'Import success: {success}')
"
```

**Step 4: Verify data was inserted**

```bash
uv run duckdb tournament_data.duckdb -readonly <<SQL
-- Check all history tables
SELECT 'Points History' AS table_name, COUNT(*) AS record_count
FROM player_points_history
UNION ALL
SELECT 'Military History', COUNT(*) FROM player_military_history
UNION ALL
SELECT 'Legitimacy History', COUNT(*) FROM player_legitimacy_history
UNION ALL
SELECT 'Family Opinions', COUNT(*) FROM family_opinion_history
UNION ALL
SELECT 'Religion Opinions', COUNT(*) FROM religion_opinion_history;
SQL
```

**Expected output (example):**

```
┌───────────────────┬──────────────┐
│   table_name      │ record_count │
├───────────────────┼──────────────┤
│ Points History    │           69 │
│ Military History  │           69 │
│ Legitimacy History│           69 │
│ Family Opinions   │          138 │
│ Religion Opinions │           69 │
└───────────────────┴──────────────┘
```

**If you see 0 for all tables → ETL integration is NOT working**

**Step 5: Inspect actual data**

```bash
uv run duckdb tournament_data.duckdb -readonly <<SQL
-- Show sample points history
SELECT
    pph.turn_number,
    p.player_name,
    pph.points
FROM player_points_history pph
JOIN players p ON pph.player_id = p.player_id
ORDER BY pph.turn_number
LIMIT 10;
SQL
```

**Expected output:**

```
┌─────────────┬─────────────┬────────┐
│ turn_number │ player_name │ points │
├─────────────┼─────────────┼────────┤
│           2 │ Becked      │      1 │
│           2 │ Fluffbunny  │      1 │
│           3 │ Becked      │      2 │
│           3 │ Fluffbunny  │      3 │
│           4 │ Becked      │      5 │
│           4 │ Fluffbunny  │      6 │
│           5 │ Becked      │      8 │
│           5 │ Fluffbunny  │     10 │
│           6 │ Becked      │     13 │
│           6 │ Fluffbunny  │     15 │
└─────────────┴─────────────┴────────┘
```

**This shows:**
- Data is properly linked to players (foreign keys working)
- Turn-by-turn progression is captured
- Player names show mapping worked correctly

---

## Common Issues & Troubleshooting

### Issue: "player_id not in player_id_mapping"

**Symptoms:**
```
KeyError: 1
# Or similar error during ETL
```

**Cause:** Player ID mapping is incomplete or incorrect.

**Debug:**
```python
# Add this temporary debug code in _load_tournament_data after player insertion:
print(f"DEBUG: player_id_mapping = {player_id_mapping}")
print(f"DEBUG: points_history player_ids = {[p['player_id'] for p in points_history[:5]]}")
```

**Solution:** Ensure parser returns player_id values that match what's in the mapping (should be 1, 2 for 2-player games).

### Issue: "Sequence does not exist"

**Symptoms:**
```
Catalog Error: Sequence with name "points_history_id_seq" does not exist!
```

**Cause:** Migration wasn't run, or sequences weren't created.

**Solution:**
```bash
# Check if sequences exist
uv run duckdb tournament_data.duckdb -readonly -c "SHOW SEQUENCES" | grep history

# If missing, re-run migration
uv run python scripts/migrations/002_add_history_tables.py
```

### Issue: "Foreign key violation"

**Symptoms:**
```
Constraint Error: Violates foreign key constraint
```

**Cause:** Trying to insert history record with player_id that doesn't exist in players table.

**Solution:** This indicates the player_id mapping is wrong. The player_id in history records must match a real player_id in the players table for that match.

### Issue: No errors but tables are empty

**Symptoms:** Import succeeds, but `SELECT COUNT(*)` shows 0 records.

**Possible causes:**
1. Parser is returning empty lists → Check parser output
2. ETL code has wrong dictionary keys → Check parsed_data keys match
3. Silent failure in bulk insert → Add try/except with logging

**Debug:**
```python
# Add debug logging in _load_tournament_data:
points_history = parsed_data.get("points_history", [])
print(f"DEBUG: Got {len(points_history)} points_history records from parser")

for point_data in points_history:
    point_data["match_id"] = match_id
    # ... mapping code ...

print(f"DEBUG: After mapping, first record: {points_history[0] if points_history else 'NONE'}")

if points_history:
    self.db.bulk_insert_points_history(points_history)
    print(f"DEBUG: Bulk insert completed for points_history")
```

---

## Implementation Checklist

### Code Changes

- [ ] Open `tournament_visualizer/data/etl.py`
- [ ] Find method `_load_tournament_data()` (around line 105)
- [ ] Scroll to the end of the method (around line 257)
- [ ] Add the 5 history processing blocks after match metadata insertion
- [ ] Verify indentation matches surrounding code
- [ ] Save file

### Verification Steps

- [ ] No syntax errors: `uv run python -c "from tournament_visualizer.data import etl"`
- [ ] All bulk insert methods called: Run grep commands from Test 1
- [ ] Create integration test: `tests/test_etl_integration.py`
- [ ] Integration test passes: `uv run pytest tests/test_etl_integration.py -v`
- [ ] Manual import test: Process one save file and check tables
- [ ] Data actually exists: Run verification queries

### Commit

Once all verification passes:

```bash
git add tournament_visualizer/data/etl.py
git add tests/test_etl_integration.py
git commit -m "feat: Add ETL integration for turn-by-turn history data

- Process points_history in _load_tournament_data()
- Process military_history in _load_tournament_data()
- Process legitimacy_history in _load_tournament_data()
- Process family_opinion_history in _load_tournament_data()
- Process religion_opinion_history in _load_tournament_data()
- Add match_id to all history records
- Map player_id using player_id_mapping
- Add comprehensive integration test
- Verify data flows from parser to database

This completes Phase 4 of the turn-by-turn history implementation."
```

---

## What This Fixes

### Before This Fix

```
User runs: import_tournaments.py
           ↓
Parser extracts history data ✅
           ↓
ETL receives history data ✅
           ↓
ETL IGNORES history data ❌
           ↓
Database: Empty history tables ❌
```

### After This Fix

```
User runs: import_tournaments.py
           ↓
Parser extracts history data ✅
           ↓
ETL receives history data ✅
           ↓
ETL processes history data ✅
           ↓
ETL calls bulk insert methods ✅
           ↓
Database: Populated history tables ✅
```

---

## Questions & Support

### If you get stuck:

1. **Check your changes match the pattern**
   - Compare your code to the resources example (lines 189-204)
   - All 5 blocks should be nearly identical except for variable names

2. **Verify the data exists at each step**
   - Add `print()` statements to see data flow
   - Check `parsed_data.keys()` to confirm parser is returning the data
   - Check `len(points_history)` to confirm data was extracted

3. **Run the tests**
   - Unit tests verify methods work in isolation ✅
   - Integration test verifies end-to-end flow
   - If integration test fails, add debug logging

4. **Check the logs**
   - Logger output shows what's happening
   - Look for "Inserted N records" messages
   - Missing messages = that block wasn't executed

---

## Timeline Impact

**Original Phase 4 Estimate:** 2 hours
**Time Spent (incomplete work):** ~1.5 hours
**Time Needed for Fix:** 1 hour
  - Implementation: 30 minutes
  - Testing: 20 minutes
  - Verification: 10 minutes

**New Phase 4 Total:** ~2.5 hours
**Overall Project Impact:** +0.5 hours (minimal)

---

## Next Steps

After completing this fix:

1. ✅ Commit the changes
2. ✅ Verify integration test passes
3. ✅ Verify manual import works
4. → **Proceed to Phase 5:** Migration & Data Import
   - Run full migration on production database
   - Re-import all tournament files
   - Verify history tables are populated across all matches

---

## Appendix: Complete _load_tournament_data() Structure

After your changes, the method should have this structure:

```python
def _load_tournament_data(self, parsed_data: Dict[str, Any]) -> None:
    """Load parsed tournament data into the database."""

    # 1. Insert match
    # 2. Insert players (build player_id_mapping)
    # 3. Insert winner
    # 4. Insert game states
    # 5. Insert events
    # 6. Insert territories
    # 7. Insert resources (yield_history)
    # 8. Insert technology progress
    # 9. Insert player statistics
    # 10. Insert units produced
    # 11. Insert match metadata

    # NEW: 12-16. Insert turn-by-turn history
    # 12. Insert points history
    # 13. Insert military history
    # 14. Insert legitimacy history
    # 15. Insert family opinion history
    # 16. Insert religion opinion history
```

You're adding items 12-16 to complete the data loading pipeline.

---

**Document Version:** 1.0
**Last Updated:** October 9, 2025
**Author:** Code Review Analysis
