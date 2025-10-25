# Territory Visualization Implementation Plan

## Overview

Implement turn-by-turn territory visualization for Old World tournament matches. Users will be able to see a hexagonal map showing which player controlled which tiles at any point in the game, with a slider to scrub through game history.

## Background & Context

### Problem Domain
Old World is a turn-based strategy game played on a hexagonal grid. Players expand by claiming tiles. The game saves include turn-by-turn ownership history for each tile that was ever owned.

### Current State
- Database has empty `territories` table with schema ready
- Parser has stub method `extract_territories()` that returns empty list
- Maps page (`/maps`) has UI components ready but no data
- Save files (ZIP archives with XML) contain the needed data

### What We're Building
- Parse tile ownership from XML save files
- Store full snapshots (all 2024 tiles × all turns) in database
- Display hexagonal map with slider to view any turn
- Color tiles by owner, show terrain for unowned tiles

### Design Decisions Made
1. **Full snapshots**: Store every tile for every turn (not just changes)
2. **God view**: Show all tiles from turn 1, regardless of player revelation
3. **NULL for unowned**: Use SQL NULL for tiles without owners (not -1)
4. **Simple schema**: One table, no city territory for now
5. **In-memory generation**: Build all records in memory before bulk insert

## Prerequisites

### Knowledge Requirements
- **Python 3.11+**: Type hints, dataclasses, ElementTree XML parsing
- **DuckDB**: SQL database, optimized for analytics
- **Pytest**: Unit testing framework
- **Old World game mechanics**: Hexagonal maps, tile ownership, turn-based gameplay

### Tools & Setup
```bash
# Development environment uses uv
uv run python manage.py status  # Check if server is running
uv run pytest -v                # Run tests
uv run python scripts/import_attachments.py --directory saves --verbose  # Re-import data
```

### Key Files to Understand First
1. **`tournament_visualizer/data/parser.py`**: XML parsing logic
2. **`tournament_visualizer/data/database.py`**: Database schema and operations
3. **`tournament_visualizer/data/etl.py`**: Data import pipeline
4. **`CLAUDE.md`**: Project conventions (YAGNI, DRY, commit guidelines)

### Testing Philosophy
- **TDD**: Write failing test first, then implement
- **Test data**: Use real XML snippet from `saves/match_426504721_anarkos-becked.zip`
- **Validation scripts**: Run after implementation to verify data quality

## Database Schema

### Current Schema
```sql
CREATE TABLE IF NOT EXISTS territories (
    territory_id BIGINT PRIMARY KEY DEFAULT nextval('territories_id_seq'),
    match_id BIGINT NOT NULL,
    x_coordinate INTEGER NOT NULL,
    y_coordinate INTEGER NOT NULL,
    turn_number INTEGER NOT NULL,
    terrain_type VARCHAR,
    owner_player_id BIGINT,
    UNIQUE(match_id, x_coordinate, y_coordinate, turn_number),
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (owner_player_id) REFERENCES players(player_id)
);

-- Indexes (already exist)
CREATE INDEX IF NOT EXISTS idx_territories_spatial ON territories(match_id, x_coordinate, y_coordinate);
CREATE INDEX IF NOT EXISTS idx_territories_temporal ON territories(match_id, turn_number);
CREATE INDEX IF NOT EXISTS idx_territories_owner ON territories(owner_player_id);
```

### Data Volume
- **Per match**: 2,024 tiles × ~70 turns = ~142,000 rows
- **Current dataset**: 20 matches = ~2.8 million rows
- **Storage**: ~200-250 MB (database will grow from 99 MB to ~300 MB)

## Implementation Tasks

### Task 1: Add Terrain Type Constants

**File**: `tournament_visualizer/data/parser.py`

**What**: Define constants for terrain types to avoid magic strings.

**Why**: The XML uses values like `TERRAIN_GRASSLAND`, `TERRAIN_WATER`. We need these for lookups and testing.

**Implementation**:

```python
# Add near top of file after imports
class TerrainType:
    """Old World terrain type constants from XML."""
    WATER = "TERRAIN_WATER"
    GRASSLAND = "TERRAIN_GRASSLAND"
    DESERT = "TERRAIN_DESERT"
    ARID = "TERRAIN_ARID"
    SCRUB = "TERRAIN_SCRUB"
    TUNDRA = "TERRAIN_TUNDRA"
    SNOW = "TERRAIN_SNOW"
```

**Test**: No test needed (constants only).

**Commit**: `feat: Add terrain type constants for tile parsing`

---

### Task 2: Write Test for Tile Extraction (TDD)

**File**: `tests/test_parser_territories.py` (new file)

**What**: Create test file with failing test for `extract_territories()`.

**Why**: TDD - write test first to define expected behavior.

**Test Data Setup**:
1. Extract sample XML to use in tests:
   ```bash
   unzip -p saves/match_426504721_anarkos-becked.zip > tests/fixtures/sample_match.xml
   ```

2. Or create minimal XML fixture (better for unit tests):
   ```xml
   <?xml version="1.0" encoding="utf-8"?>
   <Root MapWidth="3" TurnScale="TURNSCALE_YEAR">
     <Tile ID="0">
       <Terrain>TERRAIN_GRASSLAND</Terrain>
       <OwnerHistory>
         <T1>0</T1>
         <T2>0</T2>
       </OwnerHistory>
     </Tile>
     <Tile ID="1">
       <Terrain>TERRAIN_WATER</Terrain>
     </Tile>
     <Tile ID="2">
       <Terrain>TERRAIN_DESERT</Terrain>
       <OwnerHistory>
         <T1>1</T1>
       </OwnerHistory>
     </Tile>
   </Root>
   ```

**Implementation**:

```python
"""Tests for territory extraction from Old World save files."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from tournament_visualizer.data.parser import OldWorldSaveParser


@pytest.fixture
def minimal_xml_tree():
    """Create minimal XML tree for testing territory extraction."""
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
    <Root MapWidth="3" TurnScale="TURNSCALE_YEAR">
      <Tile ID="0">
        <Terrain>TERRAIN_GRASSLAND</Terrain>
        <OwnerHistory>
          <T1>0</T1>
          <T2>0</T2>
        </OwnerHistory>
      </Tile>
      <Tile ID="1">
        <Terrain>TERRAIN_WATER</Terrain>
      </Tile>
      <Tile ID="2">
        <Terrain>TERRAIN_DESERT</Terrain>
        <OwnerHistory>
          <T1>1</T1>
        </OwnerHistory>
      </Tile>
    </Root>
    """
    return ET.ElementTree(ET.fromstring(xml_content))


def test_extract_territories_basic_structure(minimal_xml_tree):
    """Test that extract_territories returns correct structure."""
    parser = OldWorldSaveParser()
    parser.root = minimal_xml_tree.getroot()

    territories = parser.extract_territories(match_id=1, final_turn=2)

    # Should have 3 tiles × 2 turns = 6 records
    assert len(territories) == 6

    # Check first record structure
    first = territories[0]
    assert "match_id" in first
    assert "tile_id" in first
    assert "x_coordinate" in first
    assert "y_coordinate" in first
    assert "turn_number" in first
    assert "terrain_type" in first
    assert "owner_player_id" in first


def test_extract_territories_coordinates(minimal_xml_tree):
    """Test that tile IDs are correctly converted to x,y coordinates."""
    parser = OldWorldSaveParser()
    parser.root = minimal_xml_tree.getroot()

    territories = parser.extract_territories(match_id=1, final_turn=1)

    # Map width is 3, so:
    # Tile 0: x=0, y=0
    # Tile 1: x=1, y=0
    # Tile 2: x=2, y=0

    tile_coords = {t["tile_id"]: (t["x_coordinate"], t["y_coordinate"])
                   for t in territories if t["turn_number"] == 1}

    assert tile_coords[0] == (0, 0)
    assert tile_coords[1] == (1, 0)
    assert tile_coords[2] == (2, 0)


def test_extract_territories_ownership(minimal_xml_tree):
    """Test that ownership is correctly extracted and mapped."""
    parser = OldWorldSaveParser()
    parser.root = minimal_xml_tree.getroot()

    territories = parser.extract_territories(match_id=1, final_turn=2)

    # Tile 0, turn 1: owned by player 0 (XML) -> player_id 1 (DB)
    tile0_turn1 = [t for t in territories
                   if t["tile_id"] == 0 and t["turn_number"] == 1][0]
    assert tile0_turn1["owner_player_id"] == 1  # XML 0 -> DB 1

    # Tile 1, turn 1: no owner -> NULL
    tile1_turn1 = [t for t in territories
                   if t["tile_id"] == 1 and t["turn_number"] == 1][0]
    assert tile1_turn1["owner_player_id"] is None

    # Tile 2, turn 1: owned by player 1 (XML) -> player_id 2 (DB)
    tile2_turn1 = [t for t in territories
                   if t["tile_id"] == 2 and t["turn_number"] == 1][0]
    assert tile2_turn1["owner_player_id"] == 2  # XML 1 -> DB 2


def test_extract_territories_terrain(minimal_xml_tree):
    """Test that terrain types are correctly extracted."""
    parser = OldWorldSaveParser()
    parser.root = minimal_xml_tree.getroot()

    territories = parser.extract_territories(match_id=1, final_turn=1)

    # Check terrain for each tile (turn 1)
    terrains = {t["tile_id"]: t["terrain_type"]
                for t in territories if t["turn_number"] == 1}

    assert terrains[0] == "TERRAIN_GRASSLAND"
    assert terrains[1] == "TERRAIN_WATER"
    assert terrains[2] == "TERRAIN_DESERT"


def test_extract_territories_all_turns(minimal_xml_tree):
    """Test that all turns are generated for all tiles."""
    parser = OldWorldSaveParser()
    parser.root = minimal_xml_tree.getroot()

    territories = parser.extract_territories(match_id=1, final_turn=2)

    # Group by tile and turn
    tiles_by_turn = {}
    for t in territories:
        key = (t["tile_id"], t["turn_number"])
        tiles_by_turn[key] = t

    # Should have records for all combinations
    assert (0, 1) in tiles_by_turn
    assert (0, 2) in tiles_by_turn
    assert (1, 1) in tiles_by_turn
    assert (1, 2) in tiles_by_turn
    assert (2, 1) in tiles_by_turn
    assert (2, 2) in tiles_by_turn

    # Tile 0, turn 2: still owned by player 0
    assert tiles_by_turn[(0, 2)]["owner_player_id"] == 1


def test_extract_territories_ownership_persistence(minimal_xml_tree):
    """Test that ownership persists across turns until changed."""
    parser = OldWorldSaveParser()
    parser.root = minimal_xml_tree.getroot()

    territories = parser.extract_territories(match_id=1, final_turn=2)

    # Tile 2: owned by player 1 at turn 1, no entry for turn 2
    # Should persist ownership to turn 2
    tile2_turn1 = [t for t in territories
                   if t["tile_id"] == 2 and t["turn_number"] == 1][0]
    tile2_turn2 = [t for t in territories
                   if t["tile_id"] == 2 and t["turn_number"] == 2][0]

    assert tile2_turn1["owner_player_id"] == 2
    assert tile2_turn2["owner_player_id"] == 2  # Persisted


def test_extract_territories_empty_xml():
    """Test graceful handling of XML with no tiles."""
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
    <Root MapWidth="10" TurnScale="TURNSCALE_YEAR">
    </Root>
    """
    tree = ET.ElementTree(ET.fromstring(xml_content))

    parser = OldWorldSaveParser()
    parser.root = tree.getroot()

    territories = parser.extract_territories(match_id=1, final_turn=10)

    # Should return empty list, not error
    assert territories == []


def test_extract_territories_no_map_width():
    """Test error handling when MapWidth attribute is missing."""
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
    <Root TurnScale="TURNSCALE_YEAR">
      <Tile ID="0">
        <Terrain>TERRAIN_GRASSLAND</Terrain>
      </Tile>
    </Root>
    """
    tree = ET.ElementTree(ET.fromstring(xml_content))

    parser = OldWorldSaveParser()
    parser.root = tree.getroot()

    with pytest.raises(ValueError, match="MapWidth"):
        parser.extract_territories(match_id=1, final_turn=1)
```

**How to Run**:
```bash
uv run pytest tests/test_parser_territories.py -v
```

**Expected**: All tests should FAIL (method not implemented yet).

**Commit**: `test: Add comprehensive tests for territory extraction`

---

### Task 3: Implement `extract_territories()` Method

**File**: `tournament_visualizer/data/parser.py`

**What**: Replace the stub method with full implementation.

**Why**: Core parsing logic to extract tile data from XML.

**Implementation**:

```python
def extract_territories(
    self, match_id: int, final_turn: int
) -> List[Dict[str, Any]]:
    """Extract territory control information for all tiles across all turns.

    Creates a full snapshot of the map for each turn, storing ownership,
    terrain, and coordinates for every tile. This enables turn-by-turn
    map visualization.

    Args:
        match_id: Database match ID for foreign key reference
        final_turn: Last turn of the game (from game state data)

    Returns:
        List of territory records, each containing:
        - match_id: Foreign key to matches table
        - tile_id: Original tile ID from XML (for debugging)
        - x_coordinate: Tile X position on map grid
        - y_coordinate: Tile Y position on map grid
        - turn_number: Game turn (1 to final_turn)
        - terrain_type: Terrain constant (e.g., "TERRAIN_GRASSLAND")
        - owner_player_id: Database player ID (1-based), or None if unowned

    Raises:
        ValueError: If XML not parsed or MapWidth attribute missing
    """
    if self.root is None:
        raise ValueError("XML not parsed. Call extract_and_parse() first.")

    # Get map dimensions
    map_width = self.root.get("MapWidth")
    if not map_width:
        raise ValueError("MapWidth attribute missing from Root element")

    map_width = int(map_width)

    # Get all tiles from XML
    tiles = self.root.findall(".//Tile[@ID]")

    if not tiles:
        return []

    # Build tile data structures
    tile_data = {}
    for tile_elem in tiles:
        tile_id = int(tile_elem.get("ID"))

        # Calculate coordinates from tile ID
        # Old World uses row-major layout: x = id % width, y = id // width
        x_coord = tile_id % map_width
        y_coord = tile_id // map_width

        # Extract terrain (required)
        terrain_elem = tile_elem.find("Terrain")
        terrain = terrain_elem.text if terrain_elem is not None else None

        # Extract ownership history
        # OwnerHistory contains turn-by-turn ownership changes
        # Example: <OwnerHistory><T45>1</T45><T64>-1</T64></OwnerHistory>
        ownership_by_turn = {}
        owner_hist_elem = tile_elem.find("OwnerHistory")
        if owner_hist_elem is not None:
            for turn_elem in owner_hist_elem:
                # Tag format: "T45" -> turn 45
                turn_num = int(turn_elem.tag[1:])  # Strip 'T' prefix
                owner_xml_id = int(turn_elem.text)

                # Convert XML player ID to database player ID
                # XML uses 0-based, DB uses 1-based
                # XML -1 = unowned/neutral -> None in DB
                if owner_xml_id == -1:
                    owner_db_id = None
                else:
                    owner_db_id = owner_xml_id + 1

                ownership_by_turn[turn_num] = owner_db_id

        tile_data[tile_id] = {
            "x_coord": x_coord,
            "y_coord": y_coord,
            "terrain": terrain,
            "ownership_by_turn": ownership_by_turn,
        }

    # Generate full snapshots for all turns
    # For each turn, create a record for every tile
    territories = []

    for turn in range(1, final_turn + 1):
        for tile_id, data in tile_data.items():
            # Determine owner at this turn
            # Ownership persists until changed
            current_owner = None

            # Find the most recent ownership change <= current turn
            for hist_turn in sorted(data["ownership_by_turn"].keys()):
                if hist_turn <= turn:
                    current_owner = data["ownership_by_turn"][hist_turn]
                else:
                    break  # Future ownership change, stop

            territories.append({
                "match_id": match_id,
                "tile_id": tile_id,
                "x_coordinate": data["x_coord"],
                "y_coordinate": data["y_coord"],
                "turn_number": turn,
                "terrain_type": data["terrain"],
                "owner_player_id": current_owner,
            })

    return territories
```

**Key Logic**:
1. **Coordinate conversion**: `x = tile_id % map_width`, `y = tile_id // map_width`
2. **Player ID mapping**: XML 0 → DB 1, XML -1 → NULL
3. **Ownership persistence**: Find most recent change ≤ current turn
4. **Full snapshots**: Generate record for every tile × every turn

**How to Test**:
```bash
# Run the tests we wrote earlier
uv run pytest tests/test_parser_territories.py -v

# All tests should now PASS
```

**Commit**: `feat: Implement territory extraction from XML save files`

---

### Task 4: Update ETL Pipeline to Extract Territories

**File**: `tournament_visualizer/data/etl.py`

**What**: Modify `extract_from_attachment()` to call `extract_territories()` with correct parameters.

**Why**: Parser method exists, but ETL pipeline doesn't call it yet.

**Current Code** (around line 130):
```python
territories = parser.extract_territories()
```

**Change To**:
```python
# Extract territories (requires match_id and final_turn)
# Get final turn from game states
final_turn = 0
if game_states:
    final_turn = max(gs["turn_number"] for gs in game_states)

territories = parser.extract_territories(
    match_id=match_id,
    final_turn=final_turn
)
```

**Why This Works**:
- `game_states` are already extracted earlier in the function
- Each game state has a `turn_number`
- We need the max turn to know how many snapshots to generate
- `match_id` is passed to the function, just forward it to parser

**Edge Case Handling**:
```python
# Extract territories (requires match_id and final_turn)
final_turn = 0
if game_states:
    final_turn = max(gs["turn_number"] for gs in game_states)

# Only extract territories if we have turn data
if final_turn > 0:
    territories = parser.extract_territories(
        match_id=match_id,
        final_turn=final_turn
    )
else:
    logger.warning(
        f"No game states found for match {match_id}, skipping territory extraction"
    )
    territories = []
```

**Test**:
```bash
# Re-import one match to test the pipeline
uv run python scripts/import_attachments.py --directory saves --dry-run --verbose

# Should see log output like:
# INFO: Extracted 141680 territory records
```

**Commit**: `feat: Integrate territory extraction into ETL pipeline`

---

### Task 5: Update Database Bulk Insert

**File**: `tournament_visualizer/data/database.py`

**What**: Verify `bulk_insert_territories()` method exists and handles NULL values correctly.

**Check Current Implementation** (should be around line 500+):

```python
def bulk_insert_territories(self, territories: List[Dict[str, Any]]) -> None:
    """Bulk insert territory records.

    Args:
        territories: List of territory dictionaries from parser
    """
    if not territories:
        return

    # DuckDB parameterized insert
    query = """
    INSERT INTO territories (
        match_id, x_coordinate, y_coordinate, turn_number,
        terrain_type, owner_player_id
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """

    # Convert to tuple format
    values = [
        (
            t["match_id"],
            t["x_coordinate"],
            t["y_coordinate"],
            t["turn_number"],
            t["terrain_type"],
            t["owner_player_id"],  # Can be None (NULL in DB)
        )
        for t in territories
    ]

    self.executemany(query, values)
```

**If Method Doesn't Exist**, add it to the `TournamentDatabase` class.

**Test**: No unit test needed (tested via integration in Task 6).

**Commit**: `feat: Add bulk insert method for territories (if needed)` OR skip commit if already exists.

---

### Task 6: Integration Test - Re-Import Data

**What**: Re-import tournament data to populate territories table.

**Why**: End-to-end test of the full pipeline.

**Steps**:

1. **Backup current database**:
   ```bash
   cp data/tournament_data.duckdb data/tournament_data.duckdb.backup_$(date +%Y%m%d_%H%M%S)
   ```

2. **Re-import with verbose logging**:
   ```bash
   uv run python scripts/import_attachments.py --directory saves --force --verbose
   ```

3. **Check output** for territory messages:
   ```
   INFO: Processing match 426504721
   INFO: Extracted 141680 territory records
   INFO: Inserted 141680 territory records
   ```

4. **Validate data in database**:
   ```bash
   uv run duckdb data/tournament_data.duckdb -readonly -c "SELECT COUNT(*) FROM territories"
   # Should show ~2.8 million rows (20 matches × ~142k rows/match)

   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT
     match_id,
     COUNT(*) as total_records,
     COUNT(DISTINCT turn_number) as turns,
     COUNT(DISTINCT x_coordinate || ',' || y_coordinate) as tiles
   FROM territories
   GROUP BY match_id
   LIMIT 5
   "
   # Should show ~2024 tiles per match, ~70 turns
   ```

5. **Check for NULL owners**:
   ```bash
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT
     COUNT(*) as total,
     COUNT(owner_player_id) as owned,
     COUNT(*) - COUNT(owner_player_id) as unowned
   FROM territories
   WHERE match_id = (SELECT MIN(match_id) FROM territories)
     AND turn_number = 1
   "
   # Should show mix of owned and unowned tiles at turn 1
   ```

**Expected Results**:
- Import completes without errors
- ~2.8 million territory records inserted
- Each match has ~2024 tiles × ~70 turns
- Mix of NULL and non-NULL `owner_player_id`

**If Import Fails**:
- Check logs for Python errors
- Verify XML parsing (might be malformed data)
- Check database constraints (foreign key violations?)
- Restore backup and fix issue

**Commit**: No commit (data import, not code change).

---

### Task 7: Create Validation Script

**File**: `scripts/validate_territories.py` (new file)

**What**: Script to verify territory data quality after import.

**Why**: Catch data issues early (missing turns, coordinate errors, etc.).

**Implementation**:

```python
#!/usr/bin/env python3
"""Validate territory data quality.

Checks for:
- Missing turns in sequences
- Invalid coordinates
- Orphaned player references
- Data consistency issues
"""

import sys
from typing import List, Tuple

from tournament_visualizer.data.database import get_database


def check_turn_sequences() -> List[str]:
    """Verify no gaps in turn sequences for each match."""
    db = get_database()
    issues = []

    query = """
    SELECT
        match_id,
        MIN(turn_number) as min_turn,
        MAX(turn_number) as max_turn,
        COUNT(DISTINCT turn_number) as unique_turns
    FROM territories
    GROUP BY match_id
    """

    results = db.fetch_all(query)

    for match_id, min_turn, max_turn, unique_turns in results:
        expected_turns = max_turn - min_turn + 1
        if unique_turns != expected_turns:
            issues.append(
                f"Match {match_id}: Expected {expected_turns} turns "
                f"({min_turn}-{max_turn}), found {unique_turns}"
            )

    return issues


def check_coordinate_validity() -> List[str]:
    """Verify coordinates are within valid map bounds."""
    db = get_database()
    issues = []

    query = """
    SELECT DISTINCT match_id, x_coordinate, y_coordinate
    FROM territories
    WHERE x_coordinate < 0 OR y_coordinate < 0
       OR x_coordinate > 100 OR y_coordinate > 100
    """

    results = db.fetch_all(query)

    if results:
        issues.append(f"Found {len(results)} records with invalid coordinates")
        for match_id, x, y in results[:5]:  # Show first 5
            issues.append(f"  Match {match_id}: ({x}, {y})")

    return issues


def check_tile_counts() -> List[str]:
    """Verify each match has consistent tile count across turns."""
    db = get_database()
    issues = []

    query = """
    SELECT
        match_id,
        turn_number,
        COUNT(*) as tile_count
    FROM territories
    GROUP BY match_id, turn_number
    HAVING tile_count != (
        SELECT COUNT(*)
        FROM territories t2
        WHERE t2.match_id = territories.match_id
          AND t2.turn_number = 1
    )
    """

    results = db.fetch_all(query)

    if results:
        issues.append(f"Found {len(results)} turns with inconsistent tile counts")
        for match_id, turn, count in results[:5]:
            issues.append(f"  Match {match_id}, Turn {turn}: {count} tiles")

    return issues


def check_orphaned_players() -> List[str]:
    """Verify all owner_player_id values reference valid players."""
    db = get_database()
    issues = []

    query = """
    SELECT DISTINCT t.owner_player_id, t.match_id
    FROM territories t
    LEFT JOIN players p ON t.owner_player_id = p.player_id
    WHERE t.owner_player_id IS NOT NULL
      AND p.player_id IS NULL
    """

    results = db.fetch_all(query)

    if results:
        issues.append(f"Found {len(results)} orphaned player references")
        for player_id, match_id in results[:5]:
            issues.append(f"  Player {player_id} in Match {match_id}")

    return issues


def check_ownership_sanity() -> List[str]:
    """Verify ownership data makes sense."""
    db = get_database()
    issues = []

    # Check: Most tiles at turn 1 should be unowned
    query = """
    SELECT
        COUNT(*) as total,
        COUNT(owner_player_id) as owned,
        100.0 * COUNT(owner_player_id) / COUNT(*) as pct_owned
    FROM territories
    WHERE turn_number = 1
    """

    result = db.fetch_one(query)
    if result:
        total, owned, pct_owned = result
        if pct_owned > 20:  # More than 20% owned at turn 1 is suspicious
            issues.append(
                f"Turn 1 ownership seems high: {pct_owned:.1f}% "
                f"({owned}/{total} tiles)"
            )

    # Check: Final turn should have more ownership
    query = """
    SELECT
        t.match_id,
        COUNT(*) as total,
        COUNT(owner_player_id) as owned,
        100.0 * COUNT(owner_player_id) / COUNT(*) as pct_owned
    FROM territories t
    INNER JOIN (
        SELECT match_id, MAX(turn_number) as final_turn
        FROM territories
        GROUP BY match_id
    ) final ON t.match_id = final.match_id
           AND t.turn_number = final.final_turn
    GROUP BY t.match_id
    HAVING pct_owned < 10
    """

    results = db.fetch_all(query)
    if results:
        issues.append(
            f"Found {len(results)} matches with low final ownership (< 10%)"
        )

    return issues


def check_terrain_coverage() -> List[str]:
    """Verify terrain data is populated."""
    db = get_database()
    issues = []

    query = """
    SELECT
        COUNT(*) as total,
        COUNT(terrain_type) as with_terrain,
        100.0 * COUNT(terrain_type) / COUNT(*) as pct
    FROM territories
    """

    result = db.fetch_one(query)
    if result:
        total, with_terrain, pct = result
        if pct < 95:  # Expect at least 95% to have terrain
            issues.append(
                f"Terrain coverage low: {pct:.1f}% "
                f"({with_terrain}/{total} records)"
            )

    return issues


def main() -> int:
    """Run all validation checks."""
    print("Validating territory data...\n")

    all_issues = []

    checks = [
        ("Turn sequences", check_turn_sequences),
        ("Coordinate validity", check_coordinate_validity),
        ("Tile counts", check_tile_counts),
        ("Orphaned players", check_orphaned_players),
        ("Ownership sanity", check_ownership_sanity),
        ("Terrain coverage", check_terrain_coverage),
    ]

    for check_name, check_func in checks:
        print(f"Checking {check_name}...", end=" ")
        issues = check_func()

        if issues:
            print(f"❌ {len(issues)} issue(s)")
            all_issues.extend(issues)
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("✓")

    print(f"\n{'='*60}")
    if all_issues:
        print(f"❌ Validation failed with {len(all_issues)} issue(s)")
        return 1
    else:
        print("✓ All validation checks passed")
        return 0


if __name__ == "__main__":
    sys.exit(main())
```

**How to Use**:
```bash
uv run python scripts/validate_territories.py
```

**Expected Output**:
```
Validating territory data...

Checking Turn sequences... ✓
Checking Coordinate validity... ✓
Checking Tile counts... ✓
Checking Orphaned players... ✓
Checking Ownership sanity... ✓
Checking Terrain coverage... ✓

============================================================
✓ All validation checks passed
```

**Commit**: `test: Add territory data validation script`

---

### Task 8: Add Query Method for Territory Data

**File**: `tournament_visualizer/data/queries.py`

**What**: Add method to fetch territory data for a specific match and turn.

**Why**: Maps page needs to query this data for visualization.

**Implementation**:

```python
def get_territory_map(
    self, match_id: int, turn_number: int
) -> pd.DataFrame:
    """Get territory map snapshot for a specific match and turn.

    Returns all tiles with their ownership and terrain for visualization.

    Args:
        match_id: Match to query
        turn_number: Turn number to retrieve

    Returns:
        DataFrame with columns:
        - tile_id: Original XML tile ID
        - x_coordinate: Tile X position
        - y_coordinate: Tile Y position
        - terrain_type: Terrain constant
        - owner_player_id: Player ID or NULL
        - player_name: Player name (NULL if unowned)
        - civilization: Player civilization (NULL if unowned)
    """
    query = """
    SELECT
        t.x_coordinate,
        t.y_coordinate,
        t.terrain_type,
        t.owner_player_id,
        p.player_name,
        p.civilization
    FROM territories t
    LEFT JOIN players p ON t.owner_player_id = p.player_id
    WHERE t.match_id = ?
      AND t.turn_number = ?
    ORDER BY t.y_coordinate, t.x_coordinate
    """

    result = self.db.fetch_all(query, {"1": match_id, "2": turn_number})

    if not result:
        return pd.DataFrame()

    return pd.DataFrame(
        result,
        columns=[
            "x_coordinate",
            "y_coordinate",
            "terrain_type",
            "owner_player_id",
            "player_name",
            "civilization",
        ],
    )


def get_territory_turn_range(self, match_id: int) -> Tuple[int, int]:
    """Get the turn range (min, max) for a match's territory data.

    Args:
        match_id: Match to query

    Returns:
        Tuple of (min_turn, max_turn), or (0, 0) if no data
    """
    query = """
    SELECT
        MIN(turn_number) as min_turn,
        MAX(turn_number) as max_turn
    FROM territories
    WHERE match_id = ?
    """

    result = self.db.fetch_one(query, {"1": match_id})

    if not result or result[0] is None:
        return (0, 0)

    return (result[0], result[1])
```

**Test** (add to `tests/test_queries.py`):

```python
def test_get_territory_map(queries, sample_db):
    """Test territory map query."""
    # Assuming test database has territory data
    df = queries.get_territory_map(match_id=1, turn_number=50)

    # Should have map data
    assert not df.empty

    # Check columns
    expected_cols = [
        "x_coordinate", "y_coordinate", "terrain_type",
        "owner_player_id", "player_name", "civilization"
    ]
    assert list(df.columns) == expected_cols

    # Check coordinate types
    assert df["x_coordinate"].dtype in [int, "int64", "Int64"]
    assert df["y_coordinate"].dtype in [int, "int64", "Int64"]


def test_get_territory_turn_range(queries, sample_db):
    """Test turn range query."""
    min_turn, max_turn = queries.get_territory_turn_range(match_id=1)

    # Should have valid range
    assert min_turn > 0
    assert max_turn >= min_turn

    # Non-existent match
    min_turn, max_turn = queries.get_territory_turn_range(match_id=99999)
    assert min_turn == 0
    assert max_turn == 0
```

**Run Tests**:
```bash
uv run pytest tests/test_queries.py::test_get_territory_map -v
uv run pytest tests/test_queries.py::test_get_territory_turn_range -v
```

**Commit**: `feat: Add territory map query methods`

---

### Task 9: Create Hexagonal Map Visualization Component

**File**: `tournament_visualizer/components/charts.py`

**What**: Add function to create hexagonal map visualization with Plotly.

**Why**: Need specialized chart for hex grid display.

**Implementation**:

```python
def create_hexagonal_map(
    df: pd.DataFrame,
    map_width: int = 46,
) -> go.Figure:
    """Create hexagonal map visualization.

    Displays tiles as hexagons colored by owner, with terrain shown
    for unowned tiles.

    Args:
        df: DataFrame with columns [x_coordinate, y_coordinate, terrain_type,
            owner_player_id, player_name, civilization]
        map_width: Map width for calculating hex positions

    Returns:
        Plotly figure with hexagonal map
    """
    if df.empty:
        return create_empty_chart_placeholder("No map data available")

    # Hex grid constants
    HEX_WIDTH = 1.0
    HEX_HEIGHT = 0.866  # sqrt(3)/2 for regular hexagon

    # Calculate hex positions
    # Offset rows (even rows shifted right by 0.5 hex width)
    df = df.copy()
    df["hex_x"] = df["x_coordinate"] * HEX_WIDTH + (df["y_coordinate"] % 2) * (HEX_WIDTH / 2)
    df["hex_y"] = df["y_coordinate"] * HEX_HEIGHT

    # Create figure
    fig = go.Figure()

    # Define color scheme
    # Owned tiles: use player colors
    # Unowned tiles: use terrain colors
    terrain_colors = {
        "TERRAIN_WATER": "#4A90E2",       # Blue
        "TERRAIN_GRASSLAND": "#7CB342",   # Green
        "TERRAIN_DESERT": "#F4E04D",      # Yellow
        "TERRAIN_ARID": "#D4A574",        # Tan
        "TERRAIN_SCRUB": "#9CCC65",       # Light green
        "TERRAIN_TUNDRA": "#B0BEC5",      # Grey-blue
        "TERRAIN_SNOW": "#ECEFF1",        # White-grey
    }

    # Get unique owners (excluding NULL/unowned)
    owned_tiles = df[df["owner_player_id"].notna()]
    unowned_tiles = df[df["owner_player_id"].isna()]

    # Plot owned tiles by player
    if not owned_tiles.empty:
        for i, (player_id, player_data) in enumerate(owned_tiles.groupby("owner_player_id")):
            player_name = player_data["player_name"].iloc[0]
            color = Config.PRIMARY_COLORS[int(i) % len(Config.PRIMARY_COLORS)]

            fig.add_trace(
                go.Scatter(
                    x=player_data["hex_x"],
                    y=player_data["hex_y"],
                    mode="markers",
                    name=player_name,
                    marker=dict(
                        color=color,
                        size=20,
                        symbol="hexagon",
                        line=dict(color="white", width=1),
                    ),
                    hovertemplate=(
                        f"<b>{player_name}</b><br>"
                        "Position: (%{customdata[0]}, %{customdata[1]})<br>"
                        "Terrain: %{customdata[2]}<br>"
                        "<extra></extra>"
                    ),
                    customdata=player_data[["x_coordinate", "y_coordinate", "terrain_type"]].values,
                )
            )

    # Plot unowned tiles by terrain
    if not unowned_tiles.empty:
        for terrain, terrain_data in unowned_tiles.groupby("terrain_type"):
            color = terrain_colors.get(terrain, "#CCCCCC")  # Default grey

            # Clean up terrain name for display
            terrain_display = terrain.replace("TERRAIN_", "").title() if terrain else "Unknown"

            fig.add_trace(
                go.Scatter(
                    x=terrain_data["hex_x"],
                    y=terrain_data["hex_y"],
                    mode="markers",
                    name=f"Unowned - {terrain_display}",
                    marker=dict(
                        color=color,
                        size=20,
                        symbol="hexagon",
                        opacity=0.5,
                        line=dict(color="white", width=1),
                    ),
                    hovertemplate=(
                        f"<b>Unowned</b><br>"
                        f"Terrain: {terrain_display}<br>"
                        "Position: (%{customdata[0]}, %{customdata[1]})<br>"
                        "<extra></extra>"
                    ),
                    customdata=terrain_data[["x_coordinate", "y_coordinate"]].values,
                )
            )

    # Update layout for hex grid
    fig.update_layout(
        xaxis=dict(
            showgrid=False,
            showticklabels=False,
            zeroline=False,
            scaleanchor="y",
            scaleratio=1,
        ),
        yaxis=dict(
            showgrid=False,
            showticklabels=False,
            zeroline=False,
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hovermode="closest",
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
        ),
        height=700,
    )

    return fig
```

**Test** (manual, in next task):
- Will test via UI integration

**Commit**: `feat: Add hexagonal map visualization component`

---

### Task 10: Update Maps Page with Territory Visualization

**File**: `tournament_visualizer/pages/maps.py`

**What**: Update the territory heatmap callback to use new hexagonal visualization.

**Why**: Connect the UI to the new data and visualization.

**Find**: Callback `update_territory_heatmap()` around line 571.

**Replace With**:

```python
@callback(
    [
        Output("territory-heatmap", "figure"),
        Output("territory-turn-range", "max"),
        Output("territory-turn-range", "value"),
        Output("territory-turn-range", "marks"),
    ],
    Input("territory-match-selector", "value"),
)
def update_territory_controls(match_id: Optional[int]):
    """Update territory heatmap and configure turn slider for selected match.

    Args:
        match_id: Selected match ID

    Returns:
        Tuple of (figure, slider_max, slider_value, slider_marks)
    """
    if not match_id:
        empty_fig = create_empty_chart_placeholder(
            "Select a match to view territory map"
        )
        return empty_fig, 100, [0, 100], {i: str(i) for i in range(0, 101, 25)}

    try:
        queries = get_queries()

        # Get turn range for this match
        min_turn, max_turn = queries.get_territory_turn_range(match_id)

        if max_turn == 0:
            empty_fig = create_empty_chart_placeholder(
                "No territory data available for this match"
            )
            return empty_fig, 100, [0, 100], {i: str(i) for i in range(0, 101, 25)}

        # Get final turn map data (default view)
        df = queries.get_territory_map(match_id, max_turn)

        if df.empty:
            empty_fig = create_empty_chart_placeholder(
                "No territory data available"
            )
            return empty_fig, max_turn, [min_turn, max_turn], {}

        # Create hexagonal map
        from tournament_visualizer.components.charts import create_hexagonal_map
        fig = create_hexagonal_map(df)

        # Configure slider
        # Create marks every ~10 turns, but ensure min and max are included
        mark_step = max(1, max_turn // 10)
        marks = {i: str(i) for i in range(min_turn, max_turn + 1, mark_step)}
        marks[min_turn] = str(min_turn)  # Ensure min is marked
        marks[max_turn] = str(max_turn)  # Ensure max is marked

        return fig, max_turn, [min_turn, max_turn], marks

    except Exception as e:
        logger.error(f"Error updating territory heatmap: {e}")
        empty_fig = create_empty_chart_placeholder(
            f"Error loading territory map: {str(e)}"
        )
        return empty_fig, 100, [0, 100], {i: str(i) for i in range(0, 101, 25)}


@callback(
    Output("territory-heatmap", "figure", allow_duplicate=True),
    [
        Input("territory-match-selector", "value"),
        Input("territory-turn-range", "value"),
    ],
    prevent_initial_call=True,
)
def update_territory_heatmap_turn(
    match_id: Optional[int],
    turn_range: List[int]
) -> go.Figure:
    """Update territory heatmap when turn slider changes.

    Args:
        match_id: Selected match ID
        turn_range: [min_turn, max_turn] from slider

    Returns:
        Plotly figure for territory map at selected turn
    """
    if not match_id or not turn_range:
        return create_empty_chart_placeholder("Select a match")

    try:
        queries = get_queries()

        # Use the max value from range slider (right handle)
        display_turn = turn_range[1]

        # Get map data for selected turn
        df = queries.get_territory_map(match_id, display_turn)

        if df.empty:
            return create_empty_chart_placeholder(
                f"No territory data for turn {display_turn}"
            )

        # Create hexagonal map
        from tournament_visualizer.components.charts import create_hexagonal_map
        return create_hexagonal_map(df)

    except Exception as e:
        logger.error(f"Error updating territory map for turn: {e}")
        return create_empty_chart_placeholder(
            f"Error loading map: {str(e)}"
        )
```

**Changes Made**:
1. Split into two callbacks:
   - `update_territory_controls`: Initializes slider and shows final turn
   - `update_territory_heatmap_turn`: Updates map when slider moves
2. Use new query methods
3. Use new hexagonal visualization
4. Configure slider dynamically based on match data

**Note**: You may need to update the UI layout to add slider outputs. Check the layout around line 158-173 and ensure `territory-turn-range` has these properties exposed.

**Commit**: `feat: Connect territory visualization to Maps page`

---

### Task 11: Manual UI Testing

**What**: Test the complete feature in the browser.

**Steps**:

1. **Start the server**:
   ```bash
   uv run python manage.py restart
   ```

2. **Navigate to Maps page**:
   - Open http://localhost:8050/maps
   - Click "Territory Analysis" tab

3. **Test workflow**:
   - Select a match from dropdown
   - Verify map displays at final turn
   - Drag turn slider left (toward turn 1)
   - Verify map updates to show earlier state
   - Check that:
     - Owned tiles are colored by player
     - Unowned tiles are colored by terrain
     - Hover shows tile info
     - Legend shows all players and terrain types

4. **Check performance**:
   - Slider should respond smoothly
   - Map should update within ~500ms
   - No browser console errors

5. **Test edge cases**:
   - Select match with no territory data (if any exist)
   - Drag slider to turn 1 (should show mostly unowned tiles)
   - Switch between matches

**Expected Behavior**:
- Map displays hexagonal grid
- Colors change as ownership changes
- Slider controls are intuitive
- No errors or crashes

**If Issues Found**:
- Check browser console for JavaScript errors
- Check server logs for Python errors
- Verify data in database (use DuckDB CLI)

**Commit**: No commit (testing only).

---

### Task 12: Performance Testing & Optimization

**What**: Test query performance with large dataset.

**Why**: 2.8M rows might be slow to query, especially for slider.

**Test Query Performance**:

```bash
uv run duckdb data/tournament_data.duckdb -readonly -c "
EXPLAIN ANALYZE
SELECT
    t.x_coordinate,
    t.y_coordinate,
    t.terrain_type,
    t.owner_player_id,
    p.player_name,
    p.civilization
FROM territories t
LEFT JOIN players p ON t.owner_player_id = p.player_id
WHERE t.match_id = 1
  AND t.turn_number = 50
"
```

**Expected**: Query should complete in < 100ms.

**If Slow (> 500ms)**:

1. **Check indexes exist**:
   ```sql
   SELECT * FROM duckdb_indexes() WHERE table_name = 'territories';
   ```

2. **Add covering index** (if needed):
   ```sql
   CREATE INDEX idx_territories_match_turn
   ON territories(match_id, turn_number);
   ```

3. **Test again** - should be faster.

**Commit**: `perf: Add covering index for territory queries (if needed)`

---

### Task 13: Write Documentation

**File**: `docs/features/territory-visualization.md` (new file)

**What**: Document the feature for future developers and users.

**Implementation**:

```markdown
# Territory Visualization

## Overview

The territory visualization feature allows users to view turn-by-turn map control for Old World tournament matches. Users can scrub through game history with a slider to see how territorial control evolved.

## User Guide

### Accessing the Feature

1. Navigate to the **Maps** page
2. Click the **Territory Analysis** tab
3. Select a match from the dropdown
4. Use the turn slider to view different points in the game

### Understanding the Map

- **Hexagonal tiles**: Each hexagon represents one tile on the game map
- **Player colors**: Owned tiles are colored by player (see legend)
- **Terrain colors**: Unowned tiles show terrain type:
  - Blue: Water
  - Green: Grassland
  - Yellow: Desert
  - Tan: Arid
  - Light green: Scrub
  - Grey-blue: Tundra
  - White-grey: Snow
- **Hover info**: Hover over tiles to see owner, terrain, and coordinates

### Controls

- **Match selector**: Choose which game to visualize
- **Turn slider**:
  - Left handle: Minimum turn (not currently used)
  - Right handle: Turn to display
  - Drag right handle to scrub through game history
  - Map updates automatically as you drag

## Technical Details

### Data Model

Territory data is stored as full turn-by-turn snapshots:

```sql
CREATE TABLE territories (
    territory_id BIGINT PRIMARY KEY,
    match_id BIGINT NOT NULL,           -- Which match
    x_coordinate INTEGER NOT NULL,      -- Tile position X (0-45)
    y_coordinate INTEGER NOT NULL,      -- Tile position Y (0-43)
    turn_number INTEGER NOT NULL,       -- Game turn (1-70)
    terrain_type VARCHAR,               -- TERRAIN_GRASSLAND, etc.
    owner_player_id BIGINT,             -- Player ID or NULL (unowned)
    UNIQUE(match_id, x_coordinate, y_coordinate, turn_number)
);
```

**Storage characteristics**:
- ~2,024 tiles per match (46 × 44 grid)
- ~70 turns average per match
- ~142,000 rows per match
- ~2.8 million rows for 20 matches
- ~250 MB database size

### Data Pipeline

1. **XML Parsing** (`parser.py`):
   - Extract `<Tile>` elements from save file XML
   - Parse `<OwnerHistory>` for turn-by-turn ownership
   - Convert tile IDs to x/y coordinates
   - Map XML player IDs (0-based) to database IDs (1-based)

2. **ETL Pipeline** (`etl.py`):
   - Call `parser.extract_territories()` during import
   - Pass `match_id` and `final_turn` parameters
   - Bulk insert territory records

3. **Database Insert** (`database.py`):
   - Bulk insert using parameterized queries
   - Foreign keys ensure referential integrity
   - Indexes optimize query performance

### Visualization

**Hexagonal Grid Rendering** (`charts.py:create_hexagonal_map()`):

The hexagonal map uses Plotly scatter plot with hexagon markers:

```python
# Calculate hex positions
HEX_WIDTH = 1.0
HEX_HEIGHT = 0.866  # sqrt(3)/2
hex_x = x_coordinate * HEX_WIDTH + (y_coordinate % 2) * (HEX_WIDTH / 2)
hex_y = y_coordinate * HEX_HEIGHT
```

**Offset coordinates**: Even rows are shifted right by half a hex width to create proper hexagonal tesselation.

**Color scheme**:
- Owned tiles: Player colors from `Config.PRIMARY_COLORS`
- Unowned tiles: Terrain-specific colors (blue for water, green for grassland, etc.)

### Performance Considerations

**Query optimization**:
- Covering index on `(match_id, turn_number)` enables fast filtering
- Spatial index on `(match_id, x_coordinate, y_coordinate)` for future queries
- LEFT JOIN with players table (not INNER) to include unowned tiles

**UI responsiveness**:
- Slider updates trigger callback with ~100ms debounce
- Query completes in < 100ms (2,024 rows returned)
- Plotly renders 2,024 hexagons in < 200ms
- Total slider response: ~400ms (feels instant)

**Memory usage**:
- Parser generates ~142k records in memory per match
- ~64 bytes per record = ~9 MB per match
- Acceptable for modern systems

## Testing

### Unit Tests

**Parser tests** (`tests/test_parser_territories.py`):
- Coordinate conversion (tile ID → x,y)
- Player ID mapping (XML 0 → DB 1)
- Ownership persistence across turns
- Terrain extraction
- Edge cases (empty XML, missing attributes)

**Query tests** (`tests/test_queries.py`):
- `get_territory_map()` returns correct data
- `get_territory_turn_range()` handles missing data
- Foreign key joins work correctly

### Integration Tests

**Data import** (`scripts/import_attachments.py`):
- Re-import with `--force` flag
- Verify territory count in logs
- Check for errors during parsing

**Validation** (`scripts/validate_territories.py`):
- Turn sequence completeness
- Coordinate validity
- Tile count consistency
- Player reference integrity
- Ownership sanity checks
- Terrain coverage

### Manual Testing

1. Start server: `uv run python manage.py restart`
2. Navigate to Maps → Territory Analysis
3. Select a match
4. Verify map displays at final turn
5. Drag slider to test responsiveness
6. Check hover tooltips
7. Verify legend accuracy

## Future Enhancements

### Potential Features

1. **City territory visualization**: Show which city each tile belongs to
2. **Fog of war**: View map from a specific player's perspective
3. **Territory change highlights**: Highlight tiles that changed hands this turn
4. **Expansion velocity**: Show rate of territorial growth
5. **Contested tiles**: Identify tiles that changed hands multiple times
6. **Resource overlay**: Show strategic resources on tiles
7. **Export to image**: Download map as PNG for analysis

### Schema Extensions

```sql
-- Add city territory (requires cities table)
ALTER TABLE territories ADD COLUMN city_territory_id BIGINT;

-- Add visibility tracking (fog of war)
ALTER TABLE territories ADD COLUMN visible_to_player_id BIGINT;

-- Add resource information
ALTER TABLE territories ADD COLUMN resource_type VARCHAR;
```

### Performance Optimizations

If database grows beyond 10M rows:

1. **Partition by match**: Create separate tables per tournament
2. **Materialize views**: Pre-aggregate common queries
3. **Incremental updates**: Only re-import changed matches
4. **Client-side caching**: Cache map data in browser for slider scrubbing

## Troubleshooting

### No territory data showing

**Check database**:
```bash
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT COUNT(*) FROM territories
"
```

If count is 0:
- Re-import data: `uv run python scripts/import_attachments.py --directory saves --force`
- Check logs for parser errors

### Slider not working

**Check browser console** for JavaScript errors.

**Verify callback outputs** match input IDs in layout.

### Slow performance

**Test query speed**:
```bash
uv run duckdb data/tournament_data.duckdb -readonly -c "
EXPLAIN ANALYZE
SELECT * FROM territories WHERE match_id = 1 AND turn_number = 50
"
```

If > 500ms:
- Verify indexes exist
- Consider adding covering index

### Map looks wrong

**Verify data quality**:
```bash
uv run python scripts/validate_territories.py
```

Fix any reported issues.

## Related Files

- `tournament_visualizer/data/parser.py` - Territory extraction logic
- `tournament_visualizer/data/queries.py` - Territory queries
- `tournament_visualizer/components/charts.py` - Hexagonal visualization
- `tournament_visualizer/pages/maps.py` - UI callbacks
- `tests/test_parser_territories.py` - Parser tests
- `scripts/validate_territories.py` - Data validation

## References

- **Old World save format**: XML schema documentation (unofficial)
- **Hexagonal grids**: [Red Blob Games - Hexagonal Grids](https://www.redblobgames.com/grids/hexagons/)
- **Plotly markers**: [Plotly Scatter Markers](https://plotly.com/python/marker-style/)
```

**Commit**: `docs: Add territory visualization feature documentation`

---

### Task 14: Update Main Documentation

**File**: `docs/developer-guide.md`

**What**: Add territory visualization to the features list.

**Find**: Section on "Turn-by-turn History Tables" (around line 50).

**Add After**:

```markdown
### Territory Visualization

The `territories` table stores full map snapshots for each turn, enabling
turn-by-turn visualization of territorial control:

- **Full snapshots**: Every tile, every turn (not just ownership changes)
- **Hexagonal display**: Tiles rendered as hexagons colored by owner
- **Interactive slider**: Scrub through game history turn-by-turn
- **Terrain overlay**: Unowned tiles show terrain type

**Key implementation details**:
- Tile coordinates derived from tile ID: `x = id % map_width, y = id // map_width`
- Player ID mapping: XML 0-based → Database 1-based
- Unowned tiles stored as `owner_player_id = NULL`
- ~142k rows per match, ~250 MB for current dataset

See `docs/features/territory-visualization.md` for complete documentation.
```

**Commit**: `docs: Add territory visualization to developer guide`

---

## Testing Checklist

Before marking this complete, verify:

### Unit Tests
- [ ] All parser tests pass: `uv run pytest tests/test_parser_territories.py -v`
- [ ] All query tests pass: `uv run pytest tests/test_queries.py -v`
- [ ] Overall test suite passes: `uv run pytest -v`

### Integration Tests
- [ ] Data import completes without errors
- [ ] Validation script passes: `uv run python scripts/validate_territories.py`
- [ ] Database size is reasonable (~300 MB)
- [ ] Territory count matches expectations (~2.8M rows for 20 matches)

### Manual UI Tests
- [ ] Maps page loads without errors
- [ ] Territory Analysis tab displays
- [ ] Match selector populated with matches
- [ ] Map displays at final turn by default
- [ ] Turn slider configured correctly (1 to final_turn)
- [ ] Slider updates map when dragged
- [ ] Map shows hexagonal tiles
- [ ] Owned tiles colored by player
- [ ] Unowned tiles colored by terrain
- [ ] Hover tooltips work
- [ ] Legend shows all players and terrains
- [ ] Performance acceptable (< 500ms for slider)

### Code Quality
- [ ] No linting errors: `uv run ruff check tournament_visualizer/`
- [ ] Code formatted: `uv run black tournament_visualizer/`
- [ ] Type hints present on all new functions
- [ ] Docstrings follow Google style

### Documentation
- [ ] Feature documentation complete
- [ ] Developer guide updated
- [ ] All code comments explain WHY not WHAT

### Git History
- [ ] Commits follow conventional format (feat:, test:, docs:)
- [ ] Each commit is atomic (one logical change)
- [ ] Commit messages are descriptive
- [ ] No Claude Code attribution lines in commits

## Rollback Procedure

If something goes wrong:

1. **Restore database backup**:
   ```bash
   cp data/tournament_data.duckdb.backup_YYYYMMDD_HHMMSS data/tournament_data.duckdb
   ```

2. **Revert code changes**:
   ```bash
   git log --oneline  # Find last good commit
   git revert <commit-sha>  # Revert problematic commits
   ```

3. **Clear territories table**:
   ```bash
   uv run duckdb data/tournament_data.duckdb -c "DELETE FROM territories"
   ```

## Success Criteria

Feature is complete when:

1. ✅ User can select a match and see its territory map
2. ✅ User can drag slider to view any turn in the game
3. ✅ Map displays hexagonal tiles colored appropriately
4. ✅ All tests pass
5. ✅ Validation script passes
6. ✅ Documentation is complete
7. ✅ Code is clean and well-commented
8. ✅ Performance is acceptable (< 500ms slider response)

## Estimated Effort

- **Task 1-3** (Setup & Tests): 1-2 hours
- **Task 4-6** (Parser & Pipeline): 2-3 hours
- **Task 7-8** (Validation & Queries): 1-2 hours
- **Task 9-10** (Visualization & UI): 2-3 hours
- **Task 11-12** (Testing & Performance): 1-2 hours
- **Task 13-14** (Documentation): 1 hour

**Total**: 8-13 hours for experienced developer unfamiliar with codebase.

## Questions?

- **Old World game mechanics**: Check the game's wiki or subreddit
- **DuckDB queries**: [DuckDB documentation](https://duckdb.org/docs/)
- **Plotly hexagons**: [Plotly Python reference](https://plotly.com/python/)
- **Dash callbacks**: [Dash documentation](https://dash.plotly.com/)
- **Project conventions**: See `CLAUDE.md` in project root
