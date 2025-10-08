# MemoryData Player ID Mapping Bug

**Status:** ✅ FIXED (2025-10-08)
**Severity:** Medium - Data integrity issue
**Affected Code:** `tournament_visualizer/data/parser.py::extract_events()`
**Fix Commits:** 443de56

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
