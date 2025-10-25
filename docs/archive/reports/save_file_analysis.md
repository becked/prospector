# Old World Save File Analysis

## Summary

The Old World game save files are **single-state snapshots** of the final game state, not turn-by-turn replay files. This means most of the historical/progression visualizations cannot work with this data format.

## What Data IS Available

### 1. Basic Match Metadata
- Game name, map size, turn count (from `<Game>` element)
- Victory type (from `<TeamVictoriesCompleted>`)
- Final turn number

### 2. Player Information (Arrays)
Located in root-level arrays:
- `<Team><PlayerTeam>`: Team IDs for each player
- `<Difficulty><PlayerDifficulty>`: Difficulty levels
- `<Nation><PlayerNation>`: Nation/civilization
- `<Humans><PlayerHuman>`: Whether player is human (0/1)

### 3. Memory Events (Historical)
`<MemoryData>` elements contain event history with:
- `<Type>`: Event type (e.g., MEMORYPLAYER_ATTACKED_CITY)
- `<Player>`: Player ID involved
- `<Turn>`: Turn number when event occurred

This is the ONLY historical/time-series data available.

### 4. Final Game State (Snapshot Only)
- Cities, units, tiles at end of match
- Final resource states
- Final territory ownership

## What Data is NOT Available

### ❌ Turn-by-Turn Progression
The parser expected `<Turn>` elements for each turn, but the file only has a single `<Turn>69</Turn>` value showing the final turn.

###❌ Resource History
No `<PlayerResources>` elements exist. Resources are in `<YieldPrice>` but only for the final state.

### ❌ Territory History
No turn-by-turn tile ownership data. Only final state exists.

### ❌ Detailed Event Log
No `<Battle>`, `<CityFounded>`, `<TechDiscovered>` elements as expected by parser.

## Required Changes

### Parser (`parser.py`)
1. **Simplify player extraction** - read from array structure, not individual `<Player>` elements
2. **Extract memory events** - parse `<MemoryData>` elements for event timeline
3. **Remove** - `extract_resources()`, `extract_territories()`, detailed `extract_events()`
4. **Simplify** - `extract_game_states()` to just return final turn state

### Visualizer (`matches.py`)
1. **Remove tabs**: Resources, Territory Control, Events
2. **Simplify Turn Progression tab**: Show only memory events timeline
3. **Keep**: Match summary cards (game name, turns, players, winner)

### Database
- Keep tables for backwards compatibility, but they'll remain empty
- Focus on populating: `matches`, `players`, `match_winners`, `events` (from MemoryData)

## Player Name Extraction

Player names come from Challonge API match data, NOT from save files. The save files only contain:
- Player indices (0, 1)
- Teams, nations, difficulty
- No actual player names or IDs

This is why the import process must match Challonge participants to save file player indices.
