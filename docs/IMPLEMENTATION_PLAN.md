# Implementation Plan for Fixing Data Extraction

## Overview
The visualizer was built expecting turn-by-turn historical data, but Old World save files only contain final-state snapshots. This document outlines the changes needed to make the visualizer work with available data.

## Changes Required

### 1. Parser Simplification (`tournament_visualizer/data/parser.py`)

#### Keep & Fix:
- `extract_match_metadata()` - Works mostly, just needs minor fixes
- `extract_players()` - **NEEDS REWRITE** to read from array format:
  ```python
  # Current: Looks for <Player> elements with OnlineID
  # Needed: Read from <Team><PlayerTeam>, <Humans><PlayerHuman>, <Nation><PlayerNation> arrays
  ```
- `determine_winner()` - Already works correctly with `<TeamVictoriesCompleted>`

#### Add:
- `extract_memory_events()` - NEW method to parse `<MemoryData>` elements:
  ```python
  def extract_memory_events(self) -> List[Dict[str, Any]]:
      """Extract memory events which provide historical timeline."""
      events = []
      memory_data_elements = self.root.findall('.//MemoryData')
      for mem in memory_data_elements:
          events.append({
              'turn_number': self._safe_int(mem.find('Turn').text),
              'event_type': mem.find('Type').text,
              'player_id': self._safe_int(mem.find('Player').text) if mem.find('Player') is not None else None,
              'description': self._format_memory_event(mem.find('Type').text)
          })
      return events
  ```

#### Remove/Stub Out:
- `extract_game_states()` - Return empty list or single final state only
- `extract_resources()` - Return empty list
- `extract_territories()` - Return empty list
- `extract_events()` - Return empty list (replaced by `extract_memory_events()`)

### 2. Visualizer Simplification (`tournament_visualizer/pages/matches.py`)

#### Line 242-316: Remove Three Tabs
Delete these tab definitions:
- Lines 242-266: "Resources" tab
- Lines 267-281: "Territory Control" tab
- Lines 282-316: "Events" tab

Keep only the "Turn Progression" tab (lines 213-241).

#### Line 213-241: Simplify Turn Progression Tab
Current content:
- Game Progression chart (showing events per turn)
- Turn Details table (showing turn number, year, active player, events)

**Change "Events Per Turn" chart to "Memory Events Timeline"**:
- X-axis: Turn number
- Y-axis: Count of memory events
- Source: `events` table populated from `<MemoryData>`

**Simplify Turn Details table**:
- Keep: Turn, Events count
- Remove: Year, Active Player (not available in data)

### 3. Remove Unused Callbacks

Delete callbacks that handle the removed tabs:
- `update_resource_chart()` - Around line 450-500
- `update_territory_chart()` - Around line 500-550
- `update_events_chart()` - Around line 550-600
- `update_resource_player_options()` - Dropdown for Resources tab
- `update_event_type_options()` - Dropdown for Events tab

Keep only:
- `update_match_options()` - Populates match selector
- `update_match_details()` - Shows match summary cards
- `update_turn_progression()` - Shows memory events timeline

### 4. Database - No Changes Needed

The existing schema can remain. Tables will just be empty:
- `resources` - 0 rows
- `territories` - 0 rows
- `game_state` - May have 1 row for final state
- `events` - Will be populated from `<MemoryData>`

### 5. Import Process - Minor Changes

In `scripts/import_tournaments.py` or wherever save files are processed:
- Ensure `extract_memory_events()` is called
- Ensure memory events are inserted into `events` table
- Player names still come from Challonge API (not save files)

## Testing Plan

1. **Backup database**: `cp tournament_data.duckdb tournament_data.duckdb.backup`
2. **Clear existing data**: Delete and recreate database
3. **Re-import with new parser**:
   ```bash
   uv run python scripts/import_tournaments.py
   ```
4. **Verify data**:
   ```sql
   SELECT COUNT(*) FROM events;  -- Should be > 0 now
   SELECT * FROM events LIMIT 10;  -- Check memory event data
   ```
5. **Test visualizer**:
   - Navigate to /matches
   - Select a match
   - Verify only "Turn Progression" tab shows
   - Verify memory events display in chart/table

## Estimated Effort

- Parser changes: 2-3 hours
- Visualizer UI changes: 1-2 hours
- Testing & debugging: 1-2 hours
- **Total**: 4-7 hours

## Alternative: Minimal Fix

If full rewrite is too much, a minimal fix:
1. **Just hide the broken tabs** with CSS or by adding `style={'display': 'none'}`
2. **Show helpful message** in Turn Progression tab explaining data limitations
3. **Keep existing parser** - it's not breaking anything, just not extracting much data

This takes < 30 minutes but provides poor user experience.
