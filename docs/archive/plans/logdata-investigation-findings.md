# LogData Investigation Findings

> **Status**: Completed and archived (2025-10-25)
>
> LogData events are now documented in CLAUDE.md (Data Sources section).
> See migrations/001_add_logdata_events.md for schema changes.

## Investigation Date: 2025-10-08

## Questions Investigated

### 1. Test Fixture Creation - Should we ensure complete XML elements?

**Answer: YES** - We should ensure test fixtures contain complete Player and PermanentLogList sections. Using `head -n 1000` could cut off mid-element.

**Recommendation:** Extract complete Player sections programmatically or manually verify the fixture is well-formed XML.

---

### 2. Player ID Mapping - Do players with ID="0" exist?

**Answer: YES** - Players with ID="0" definitely exist and are valid players.

**Evidence from saves:**
- `match_426504721_anarkos-becked.zip`: Player ID="0" (anarkos), Player ID="1" (becked)
- `match_426504724_moose-mongreleyes.zip`: Player ID="0" (PBM), Player ID="1" (MongrelEyes)

**Current extract_events() behavior:**
```python
# Line 294-295 in parser.py
raw_player_id = self._safe_int(player_elem.text) if player_elem is not None else None
player_id = raw_player_id if raw_player_id and raw_player_id > 0 else None
```
This converts player_id 0 to None, which is INCORRECT for MemoryData events.

**Correct behavior for LogData:**
- XML Player ID="0" should map to database player_id=1
- XML Player ID="1" should map to database player_id=2
- Formula: `database_player_id = xml_player_id + 1`

**Action Required:**
1. LogData extraction should use the formula above
2. Consider reviewing MemoryData extraction logic (separate from this task)

---

### 3. XML Structure - Where is LogData located?

**Answer:** LogData is primarily under `PermanentLogList` elements, which are children of `Player` elements.

**Structure:**
```xml
<Player ID="0" Name="anarkos" OnlineID="...">
  <PermanentLogList>
    <LogData>
      <Type>LAW_ADOPTED</Type>
      <Turn>11</Turn>
      <Data1>LAW_SLAVERY</Data1>
      <Text>Adopted <color=...>Slavery</color></Text>
    </LogData>
    <!-- More LogData elements -->
  </PermanentLogList>
</Player>
```

**LogData Distribution (anarkos vs becked match):**
- PermanentLogList: 131 events (68 for player 0, 63 for player 1)
- TurnLogList: 15 events
- ChatLogList: 17 events
- TurnSummary: 3 events (not the main source!)

**Player-specific counts:**
- Player 0 (anarkos): 68 LogData events
  - LAW_ADOPTED: 6 events (turns 11, 36, 49, 54, 55, 63)
  - TECH_DISCOVERED: 19 events
  - CITY_FOUNDED: 7 events

- Player 1 (becked): 63 LogData events
  - LAW_ADOPTED: 7 events (turns 20, 37, 43, 46, 50, 64, 68)
  - TECH_DISCOVERED: 20 events
  - CITY_FOUNDED: 7 events

**Total:** 13 LAW_ADOPTED events, 39 TECH_DISCOVERED events

**Implementation Note:** Extract LogData from Player/PermanentLogList, NOT from TurnSummary as suggested in the plan.

---

### 4. Event Duplication - Are there duplicates between MemoryData and LogData?

**Answer: NO** - There are ZERO overlapping event types between MemoryData and LogData.

**Evidence (anarkos vs becked match):**
- MemoryData: 109 events with 23 unique types (all start with "MEMORY*")
  - Examples: MEMORYPLAYER_ATTACKED_UNIT, MEMORYFAMILY_FOUNDED_CITY

- LogData: 163 events with 23 unique types (none start with "MEMORY*")
  - Examples: LAW_ADOPTED, TECH_DISCOVERED, CITY_FOUNDED, GOAL_STARTED

- Overlapping types: **0** (confirmed in multiple save files)

**Conclusion:** No deduplication logic needed! The event type namespaces are completely separate.

**Action Required:** Remove Task 3.4 (Handle Duplicate Events) from implementation plan - it's not needed.

---

### 5. Performance Testing - What should the target be?

**Answer:** Can be ignored for now per user request.

**Rationale:** LogData extraction should be similar performance to MemoryData extraction. We're just parsing XML elements - no complex operations.

**Recommendation:** Remove performance tests from critical path. Add them later if performance issues arise.

---

## Updated Implementation Insights

### XPath Queries to Use
```python
# Find all players with game data
players = root.findall('.//Player[@OnlineID]')

# For each player, get their LogData
perm_log_list = player.find('.//PermanentLogList')
if perm_log_list:
    log_data_elements = perm_log_list.findall('.//LogData')
```

### Player ID Conversion
```python
xml_player_id = int(player.get('ID'))  # 0, 1, 2, ...
database_player_id = xml_player_id + 1  # 1, 2, 3, ...
```

### No Deduplication Needed
Since MemoryData and LogData have completely separate event type namespaces, we can simply:
```python
all_events = memory_events + logdata_events
# No deduplication necessary!
```

### Event Type Statistics
From the anarkos vs becked match:
- Expected LAW_ADOPTED: 13 (6 + 7)
- Expected TECH_DISCOVERED: 39 (19 + 20)
- Expected CITY_FOUNDED: 14 (7 + 7)

These numbers can be used for validation tests.

---

## Plan Corrections Required

1. **Task 1.2:** Update XPath to use `Player[@OnlineID]/PermanentLogList/LogData` instead of `Player/TurnSummary/LogData`

2. **Task 2.2-2.3:** Update expected counts:
   - anarkos-becked match: 13 LAW_ADOPTED, 39 TECH_DISCOVERED

3. **Task 3.1:** Update implementation to:
   - Find `Player[@OnlineID]` elements
   - Extract LogData from `PermanentLogList` child
   - Convert player XML ID using `xml_id + 1` formula

4. **Task 3.4:** **REMOVE THIS TASK** - No deduplication needed

5. **Task 6.3:** Make performance tests optional/lower priority

---

## Summary

✅ Players with ID="0" exist and are valid - must map to database player_id=1
✅ LogData is under Player/PermanentLogList, not Player/TurnSummary
✅ NO duplicate events between MemoryData and LogData - no deduplication needed
✅ Expected data: 13 laws, 39 techs in the test match
✅ Performance testing can be deprioritized
