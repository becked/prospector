# Implementation Plan: Add Tile Details to Territories

**Status:** Not Started
**Created:** 2025-10-30
**Approach:** Option A - Extend existing territories table

## Overview

Add specialist assignments, improvements, resources, and roads to the `territories` table to enable richer map visualizations and strategic analysis.

**Current state:** `territories` table only tracks ownership and terrain
**Goal state:** `territories` table includes specialists, improvements, resources, and infrastructure

## Context for New Engineers

### What is Old World?
Old World is a historical 4X strategy game where players build civilizations. Players:
- Expand territory by founding cities
- Build improvements on tiles (farms, mines, quarries)
- Assign specialists to tiles for bonuses (miners, officers, priests)
- Compete in multiplayer tournaments

### Our System
We parse end-of-game save files (XML in ZIP archives) and import data into DuckDB for tournament analytics and visualizations.

### Key Files
- `tournament_visualizer/data/parser.py` - Extracts data from XML save files
- `tournament_visualizer/data/database.py` - DuckDB operations and schema
- `tournament_visualizer/data/etl.py` - Coordinates import pipeline
- `docs/schema.sql` - Database schema documentation
- `scripts/import_attachments.py` - Main import script

### Development Workflow
1. Write failing test first (TDD)
2. Implement minimum code to pass test
3. Refactor
4. Commit when tests pass
5. Run validation scripts after schema changes

### Tools We Use
- **uv** - Python package manager (like npm for Python)
- **DuckDB** - Analytics database (like SQLite but for OLAP)
- **pytest** - Testing framework
- **XML ElementTree** - XML parsing (built into Python)

## Architecture Decision: Why Extend territories?

**Option A (Chosen):** Add columns to `territories` table
- Simpler queries (no joins needed for map views)
- Consistent with existing architecture (turn-by-turn snapshots)
- Most values will be NULL and compress well in DuckDB
- Easy to add incremental columns later

**Option B (Rejected):** Separate normalized tables
- Would require joins for every map query
- More complex to maintain turn-by-turn consistency
- Premature optimization (YAGNI principle)

## Database Schema Changes

### New Columns

```sql
ALTER TABLE territories ADD COLUMN improvement_type VARCHAR;
ALTER TABLE territories ADD COLUMN specialist_type VARCHAR;
ALTER TABLE territories ADD COLUMN resource_type VARCHAR;
ALTER TABLE territories ADD COLUMN has_road BOOLEAN DEFAULT FALSE;
```

**Column details:**
- `improvement_type`: Type constant from XML (e.g., "IMPROVEMENT_MINE", "IMPROVEMENT_FARM")
- `specialist_type`: Specialist constant (e.g., "SPECIALIST_MINER", "SPECIALIST_OFFICER_1")
- `resource_type`: Resource constant (e.g., "RESOURCE_HORSE", "RESOURCE_MARBLE")
- `has_road`: Boolean flag for road network tracking

**Why these specific columns?**
- Improvements: Show infrastructure development strategy
- Specialists: Critical for competitive analysis (where players focus economy)
- Resources: Show resource control and strategic targets
- Roads: Trade network and logistics tracking

### Migration Strategy

We use DuckDB which doesn't support ALTER TABLE ADD COLUMN in all versions, so we'll:
1. Create migration that drops and recreates table with new columns
2. Preserve existing data using temp table pattern
3. Document in `docs/migrations/`

## Implementation Tasks

### Task 1: Create Migration Script

**File:** `docs/migrations/005_add_tile_details_to_territories.md`

**What:** Document the schema change for reference

**Why:** We track all schema changes in migrations/ for rollback and documentation

**Steps:**
1. Create file `docs/migrations/005_add_tile_details_to_territories.md`
2. Document the schema change (see template below)
3. Include rollback procedure
4. List affected queries

**Template:**
```markdown
# Migration 005: Add Tile Details to Territories

**Date:** 2025-10-30
**Status:** Pending

## Summary
Extends territories table with improvement_type, specialist_type, resource_type, and has_road columns.

## Forward Migration
```sql
-- DuckDB doesn't support ALTER ADD COLUMN reliably
-- Use parser changes + re-import instead
-- New territories will be created with new columns automatically
```

## Rollback
Drop new columns if needed:
```sql
ALTER TABLE territories DROP COLUMN improvement_type;
ALTER TABLE territories DROP COLUMN specialist_type;
ALTER TABLE territories DROP COLUMN resource_type;
ALTER TABLE territories DROP COLUMN has_road;
```

## Affected Queries
- None (new columns, backward compatible)

## Testing
Run: `uv run python scripts/validate_territory_data.py` (to be created)

## Data Re-import Required
Yes - full re-import needed to populate new columns
```

**Commit:** `docs: Add migration 005 for tile details`

---

### Task 2: Update Database Schema Documentation

**File:** `docs/schema.sql`

**What:** Add new columns to territories table definition

**Why:** This is our source of truth for schema - must be updated before code changes

**Steps:**
1. Open `docs/schema.sql`
2. Find `CREATE TABLE territories` section
3. Add new columns with comments
4. Run `uv run duckdb data/tournament_data.duckdb -c "DESCRIBE territories"` to verify current schema
5. Update the documentation to match new schema

**Code to add:**
```sql
CREATE TABLE territories (
    territory_id BIGINT PRIMARY KEY,
    match_id BIGINT NOT NULL,
    x_coordinate INTEGER NOT NULL,
    y_coordinate INTEGER NOT NULL,
    turn_number INTEGER NOT NULL,
    terrain_type VARCHAR,
    owner_player_id BIGINT,
    -- NEW COLUMNS:
    improvement_type VARCHAR,      -- e.g., 'IMPROVEMENT_MINE', 'IMPROVEMENT_FARM'
    specialist_type VARCHAR,       -- e.g., 'SPECIALIST_MINER', 'SPECIALIST_OFFICER_1'
    resource_type VARCHAR,         -- e.g., 'RESOURCE_HORSE', 'RESOURCE_MARBLE'
    has_road BOOLEAN DEFAULT FALSE,-- TRUE if tile has a road
    UNIQUE (match_id, x_coordinate, y_coordinate, turn_number)
);
```

**Commit:** `docs: Update schema.sql with tile detail columns`

---

### Task 3: Write Parser Tests (TDD Step 1)

**File:** `tests/test_parser_territories.py` (new file)

**What:** Write failing tests for tile detail extraction

**Why:** TDD - write tests before implementation to define expected behavior

**Steps:**
1. Create `tests/test_parser_territories.py`
2. Write test for specialist extraction
3. Write test for improvement extraction
4. Write test for resource extraction
5. Write test for road extraction
6. Run tests - they should FAIL (code not implemented yet)

**Test Code:**
```python
"""Tests for territory/tile data extraction in parser.py"""

import xml.etree.ElementTree as ET
from tournament_visualizer.data.parser import OldWorldSaveParser


def test_extract_territories_includes_specialists():
    """Test that extract_territories captures specialist assignments."""
    # Create minimal XML with specialist on a tile
    xml_content = """<?xml version="1.0"?>
    <Root MapWidth="10">
        <Player ID="0" OnlineID="12345" Name="TestPlayer" />
        <Tile ID="0">
            <Terrain>TERRAIN_TEMPERATE</Terrain>
            <Specialist>SPECIALIST_MINER</Specialist>
            <OwnerHistory><T1>0</T1></OwnerHistory>
        </Tile>
    </Root>
    """

    parser = OldWorldSaveParser("")
    parser.root = ET.fromstring(xml_content)

    territories = parser.extract_territories(match_id=1, final_turn=1)

    # Find the tile record
    tile_record = next(t for t in territories if t["tile_id"] == 0)

    assert tile_record["specialist_type"] == "SPECIALIST_MINER"
    assert tile_record["x_coordinate"] == 0
    assert tile_record["y_coordinate"] == 0


def test_extract_territories_includes_improvements():
    """Test that extract_territories captures improvement types."""
    xml_content = """<?xml version="1.0"?>
    <Root MapWidth="10">
        <Player ID="0" OnlineID="12345" Name="TestPlayer" />
        <Tile ID="5">
            <Terrain>TERRAIN_TEMPERATE</Terrain>
            <Improvement>IMPROVEMENT_MINE</Improvement>
            <OwnerHistory><T1>0</T1></OwnerHistory>
        </Tile>
    </Root>
    """

    parser = OldWorldSaveParser("")
    parser.root = ET.fromstring(xml_content)

    territories = parser.extract_territories(match_id=1, final_turn=1)

    tile_record = next(t for t in territories if t["tile_id"] == 5)

    assert tile_record["improvement_type"] == "IMPROVEMENT_MINE"


def test_extract_territories_includes_resources():
    """Test that extract_territories captures natural resources."""
    xml_content = """<?xml version="1.0"?>
    <Root MapWidth="10">
        <Player ID="0" OnlineID="12345" Name="TestPlayer" />
        <Tile ID="7">
            <Terrain>TERRAIN_GRASSLAND</Terrain>
            <Resource>RESOURCE_HORSE</Resource>
            <OwnerHistory><T1>0</T1></OwnerHistory>
        </Tile>
    </Root>
    """

    parser = OldWorldSaveParser("")
    parser.root = ET.fromstring(xml_content)

    territories = parser.extract_territories(match_id=1, final_turn=1)

    tile_record = next(t for t in territories if t["tile_id"] == 7)

    assert tile_record["resource_type"] == "RESOURCE_HORSE"


def test_extract_territories_includes_roads():
    """Test that extract_territories captures road network."""
    xml_content = """<?xml version="1.0"?>
    <Root MapWidth="10">
        <Player ID="0" OnlineID="12345" Name="TestPlayer" />
        <Tile ID="3">
            <Terrain>TERRAIN_TEMPERATE</Terrain>
            <Road />
            <OwnerHistory><T1>0</T1></OwnerHistory>
        </Tile>
    </Root>
    """

    parser = OldWorldSaveParser("")
    parser.root = ET.fromstring(xml_content)

    territories = parser.extract_territories(match_id=1, final_turn=1)

    tile_record = next(t for t in territories if t["tile_id"] == 3)

    assert tile_record["has_road"] is True


def test_extract_territories_defaults_to_none_when_missing():
    """Test that tiles without specialists/improvements/resources have None values."""
    xml_content = """<?xml version="1.0"?>
    <Root MapWidth="10">
        <Player ID="0" OnlineID="12345" Name="TestPlayer" />
        <Tile ID="10">
            <Terrain>TERRAIN_WATER</Terrain>
        </Tile>
    </Root>
    """

    parser = OldWorldSaveParser("")
    parser.root = ET.fromstring(xml_content)

    territories = parser.extract_territories(match_id=1, final_turn=1)

    tile_record = next(t for t in territories if t["tile_id"] == 10)

    assert tile_record["specialist_type"] is None
    assert tile_record["improvement_type"] is None
    assert tile_record["resource_type"] is None
    assert tile_record["has_road"] is False


def test_extract_territories_combines_all_attributes():
    """Test that a tile can have multiple attributes simultaneously."""
    xml_content = """<?xml version="1.0"?>
    <Root MapWidth="10">
        <Player ID="0" OnlineID="12345" Name="TestPlayer" />
        <Tile ID="15">
            <Terrain>TERRAIN_TEMPERATE</Terrain>
            <Improvement>IMPROVEMENT_PASTURE</Improvement>
            <Specialist>SPECIALIST_RANCHER</Specialist>
            <Resource>RESOURCE_HORSE</Resource>
            <Road />
            <OwnerHistory><T1>0</T1></OwnerHistory>
        </Tile>
    </Root>
    """

    parser = OldWorldSaveParser("")
    parser.root = ET.fromstring(xml_content)

    territories = parser.extract_territories(match_id=1, final_turn=1)

    tile_record = next(t for t in territories if t["tile_id"] == 15)

    assert tile_record["improvement_type"] == "IMPROVEMENT_PASTURE"
    assert tile_record["specialist_type"] == "SPECIALIST_RANCHER"
    assert tile_record["resource_type"] == "RESOURCE_HORSE"
    assert tile_record["has_road"] is True
    assert tile_record["terrain_type"] == "TERRAIN_TEMPERATE"
```

**Run tests:**
```bash
uv run pytest tests/test_parser_territories.py -v
```

**Expected result:** All tests FAIL (KeyError on new fields)

**Commit:** `test: Add failing tests for tile detail extraction`

---

### Task 4: Implement Parser Changes (TDD Step 2)

**File:** `tournament_visualizer/data/parser.py`

**What:** Modify `extract_territories()` to extract new tile attributes

**Why:** This is the core implementation that makes tests pass

**Steps:**
1. Open `tournament_visualizer/data/parser.py`
2. Find `extract_territories()` method (around line 716)
3. Locate the tile parsing loop (where `tile_data` dict is built)
4. Add extraction logic for new attributes
5. Add new fields to territory records
6. Run tests - they should PASS now

**Code changes:**

Find this section (around line 760-798):
```python
# Build tile data structures
tile_data = {}
for tile_elem in tiles:
    tile_id = int(tile_elem.get("ID"))

    # Calculate coordinates from tile ID
    x_coord = tile_id % map_width
    y_coord = tile_id // map_width

    # Extract terrain (required)
    terrain_elem = tile_elem.find("Terrain")
    terrain = terrain_elem.text if terrain_elem is not None else None

    # Extract ownership history
    # ... existing ownership code ...
```

**Replace with:**
```python
# Build tile data structures
tile_data = {}
for tile_elem in tiles:
    tile_id = int(tile_elem.get("ID"))

    # Calculate coordinates from tile ID
    x_coord = tile_id % map_width
    y_coord = tile_id // map_width

    # Extract terrain (required)
    terrain_elem = tile_elem.find("Terrain")
    terrain = terrain_elem.text if terrain_elem is not None else None

    # Extract improvement (NEW)
    improvement_elem = tile_elem.find("Improvement")
    improvement = improvement_elem.text if improvement_elem is not None else None

    # Extract specialist (NEW)
    specialist_elem = tile_elem.find("Specialist")
    specialist = specialist_elem.text if specialist_elem is not None else None

    # Extract resource (NEW)
    resource_elem = tile_elem.find("Resource")
    resource = resource_elem.text if resource_elem is not None else None

    # Extract road (NEW)
    # Road is an empty element <Road /> so check for existence
    has_road = tile_elem.find("Road") is not None

    # Extract ownership history
    # ... existing ownership code ...
```

Then find where `tile_data[tile_id]` dict is created (around line 793):
```python
tile_data[tile_id] = {
    "x_coord": x_coord,
    "y_coord": y_coord,
    "terrain": terrain,
    "ownership_by_turn": ownership_by_turn,
}
```

**Replace with:**
```python
tile_data[tile_id] = {
    "x_coord": x_coord,
    "y_coord": y_coord,
    "terrain": terrain,
    "improvement": improvement,
    "specialist": specialist,
    "resource": resource,
    "has_road": has_road,
    "ownership_by_turn": ownership_by_turn,
}
```

Finally, find where territory records are created (around line 817):
```python
territories.append(
    {
        "match_id": match_id,
        "tile_id": tile_id,
        "x_coordinate": data["x_coord"],
        "y_coordinate": data["y_coord"],
        "turn_number": turn,
        "terrain_type": data["terrain"],
        "owner_player_id": current_owner,
    }
)
```

**Replace with:**
```python
territories.append(
    {
        "match_id": match_id,
        "tile_id": tile_id,
        "x_coordinate": data["x_coord"],
        "y_coordinate": data["y_coord"],
        "turn_number": turn,
        "terrain_type": data["terrain"],
        "improvement_type": data["improvement"],
        "specialist_type": data["specialist"],
        "resource_type": data["resource"],
        "has_road": data["has_road"],
        "owner_player_id": current_owner,
    }
)
```

**Update docstring** at the top of `extract_territories()` method:

Find (around line 730-737):
```python
Returns:
    List of territory records, each containing:
    - match_id: Foreign key to matches table
    - tile_id: Original tile ID from XML (for debugging)
    - x_coordinate: Tile X position on map grid
    - y_coordinate: Tile Y position on map grid
    - turn_number: Game turn (1 to final_turn)
    - terrain_type: Terrain constant (e.g., "TERRAIN_GRASSLAND")
    - owner_player_id: Database player ID (1-based), or None if unowned
```

**Replace with:**
```python
Returns:
    List of territory records, each containing:
    - match_id: Foreign key to matches table
    - tile_id: Original tile ID from XML (for debugging)
    - x_coordinate: Tile X position on map grid
    - y_coordinate: Tile Y position on map grid
    - turn_number: Game turn (1 to final_turn)
    - terrain_type: Terrain constant (e.g., "TERRAIN_GRASSLAND")
    - improvement_type: Improvement constant or None
    - specialist_type: Specialist constant or None
    - resource_type: Resource constant or None
    - has_road: Boolean, True if tile has road
    - owner_player_id: Database player ID (1-based), or None if unowned
```

**Run tests:**
```bash
uv run pytest tests/test_parser_territories.py -v
```

**Expected result:** All tests PASS

**Commit:** `feat: Extract specialists, improvements, resources, and roads from tiles`

---

### Task 5: Update Database Schema

**File:** `tournament_visualizer/data/database.py`

**What:** Update `create_tables()` method to include new columns

**Why:** Schema must be defined in code for new databases

**Steps:**
1. Open `tournament_visualizer/data/database.py`
2. Find `CREATE TABLE territories` statement
3. Add new columns to the CREATE statement
4. Test by creating a fresh database

**Code changes:**

Find the territories table creation (search for "CREATE TABLE territories"):
```sql
CREATE TABLE IF NOT EXISTS territories (
    territory_id INTEGER PRIMARY KEY,
    match_id INTEGER NOT NULL,
    x_coordinate INTEGER NOT NULL,
    y_coordinate INTEGER NOT NULL,
    turn_number INTEGER NOT NULL,
    terrain_type VARCHAR,
    owner_player_id INTEGER,
    UNIQUE (match_id, x_coordinate, y_coordinate, turn_number)
)
```

**Replace with:**
```sql
CREATE TABLE IF NOT EXISTS territories (
    territory_id INTEGER PRIMARY KEY,
    match_id INTEGER NOT NULL,
    x_coordinate INTEGER NOT NULL,
    y_coordinate INTEGER NOT NULL,
    turn_number INTEGER NOT NULL,
    terrain_type VARCHAR,
    improvement_type VARCHAR,
    specialist_type VARCHAR,
    resource_type VARCHAR,
    has_road BOOLEAN DEFAULT FALSE,
    owner_player_id INTEGER,
    UNIQUE (match_id, x_coordinate, y_coordinate, turn_number)
)
```

**Test:**
```bash
# Create a test database with new schema
uv run python -c "
from tournament_visualizer.data.database import TournamentDatabase
db = TournamentDatabase('test_schema.duckdb')
db.create_tables()
print('Schema created successfully')
"

# Verify columns exist
uv run duckdb test_schema.duckdb -c "DESCRIBE territories"

# Clean up
rm test_schema.duckdb
```

**Expected output:** Should show all columns including the new ones

**Commit:** `feat: Add tile detail columns to territories table schema`

---

### Task 6: Update Bulk Insert Method

**File:** `tournament_visualizer/data/database.py`

**What:** Update `bulk_insert_territories()` to handle new columns

**Why:** The INSERT statement needs to include new column names

**Steps:**
1. Stay in `tournament_visualizer/data/database.py`
2. Find `bulk_insert_territories()` method
3. Add new columns to the INSERT statement
4. No need to test yet (will test in integration)

**Code changes:**

Find `bulk_insert_territories()` method and locate the INSERT statement:
```python
query = """
    INSERT INTO territories (
        match_id, x_coordinate, y_coordinate, turn_number,
        terrain_type, owner_player_id
    ) VALUES (?, ?, ?, ?, ?, ?)
"""
```

**Replace with:**
```python
query = """
    INSERT INTO territories (
        match_id, x_coordinate, y_coordinate, turn_number,
        terrain_type, improvement_type, specialist_type,
        resource_type, has_road, owner_player_id
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""
```

Find the data extraction part:
```python
data = [
    (
        rec["match_id"],
        rec["x_coordinate"],
        rec["y_coordinate"],
        rec["turn_number"],
        rec["terrain_type"],
        rec["owner_player_id"],
    )
    for rec in records
]
```

**Replace with:**
```python
data = [
    (
        rec["match_id"],
        rec["x_coordinate"],
        rec["y_coordinate"],
        rec["turn_number"],
        rec["terrain_type"],
        rec.get("improvement_type"),
        rec.get("specialist_type"),
        rec.get("resource_type"),
        rec.get("has_road", False),
        rec["owner_player_id"],
    )
    for rec in records
]
```

**Note:** We use `.get()` for new fields to handle old data gracefully during transition.

**Commit:** `feat: Update bulk_insert_territories to include tile details`

---

### Task 7: Backup Current Database

**What:** Create a backup before making destructive changes

**Why:** Safety - we can roll back if something goes wrong

**Steps:**
```bash
# Create backup with timestamp
cp data/tournament_data.duckdb "data/tournament_data.duckdb.backup_$(date +%Y%m%d_%H%M%S)"

# Verify backup exists
ls -lh data/*.backup_*
```

**Commit:** Not needed (backup files not in git)

---

### Task 8: Drop and Recreate Territories Table

**What:** Recreate territories table with new schema

**Why:** DuckDB may not support ALTER ADD COLUMN reliably, fresh start is cleanest

**Steps:**
```bash
# Drop existing territories table
uv run duckdb data/tournament_data.duckdb -c "DROP TABLE territories"

# Verify it's gone
uv run duckdb data/tournament_data.duckdb -c "SHOW TABLES" | grep -i territ

# Recreate with new schema
uv run python -c "
from tournament_visualizer.data.database import TournamentDatabase
db = TournamentDatabase('data/tournament_data.duckdb')
# Only create territories table (others already exist)
db.conn.execute('''
CREATE TABLE IF NOT EXISTS territories (
    territory_id INTEGER PRIMARY KEY,
    match_id INTEGER NOT NULL,
    x_coordinate INTEGER NOT NULL,
    y_coordinate INTEGER NOT NULL,
    turn_number INTEGER NOT NULL,
    terrain_type VARCHAR,
    improvement_type VARCHAR,
    specialist_type VARCHAR,
    resource_type VARCHAR,
    has_road BOOLEAN DEFAULT FALSE,
    owner_player_id INTEGER,
    UNIQUE (match_id, x_coordinate, y_coordinate, turn_number)
)
''')
print('Territories table recreated')
"

# Verify new schema
uv run duckdb data/tournament_data.duckdb -c "DESCRIBE territories"
```

**Expected output:** Should show all columns including new ones

**Commit:** `chore: Recreate territories table with tile detail columns`

---

### Task 9: Re-import All Data

**What:** Run full data import to populate new columns

**Why:** Existing territories data is gone, need to rebuild with new parser

**Steps:**
```bash
# Run import with verbose output
uv run python scripts/import_attachments.py --directory saves --force --verbose 2>&1 | tee reimport.log

# Monitor progress (in another terminal if needed)
tail -f reimport.log

# Check for errors
grep -i error reimport.log
grep -i "failed" reimport.log
```

**This will take a while** - importing ~27 matches with full territory data

**When complete, verify:**
```bash
# Check record count (should be ~4.2 million)
uv run duckdb data/tournament_data.duckdb -readonly -c "
  SELECT COUNT(*) as total_records FROM territories
"

# Check new columns have data
uv run duckdb data/tournament_data.duckdb -readonly -c "
  SELECT
    COUNT(*) as total,
    COUNT(specialist_type) as with_specialist,
    COUNT(improvement_type) as with_improvement,
    COUNT(resource_type) as with_resource,
    SUM(CASE WHEN has_road THEN 1 ELSE 0 END) as with_road
  FROM territories
"
```

**Expected output:**
- Total: ~4.2M records
- Specialists: ~few thousand (specialists are rare)
- Improvements: ~tens of thousands (common)
- Resources: ~tens of thousands (natural resources)
- Roads: ~tens of thousands (infrastructure)

**Commit:** Not needed (data not in git)

---

### Task 10: Create Validation Script

**File:** `scripts/validate_territory_data.py` (new file)

**What:** Script to verify tile detail data quality

**Why:** Ensure import worked correctly and data makes sense

**Steps:**
1. Create `scripts/validate_territory_data.py`
2. Add validation checks
3. Run validation
4. Fix any issues found

**Code:**
```python
"""Validate territory tile detail data after import.

Checks:
- Specialist assignments are on valid tiles
- Improvements exist where expected
- Resources match improvement types
- Data consistency across matches
"""

import logging
from tournament_visualizer.data.database import TournamentDatabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_specialist_counts() -> bool:
    """Verify specialist assignments look reasonable."""
    db = TournamentDatabase("data/tournament_data.duckdb")

    query = """
    SELECT
        COUNT(DISTINCT match_id) as matches,
        COUNT(*) as total_tiles_with_specialists,
        COUNT(DISTINCT specialist_type) as unique_specialist_types,
        COUNT(*) * 1.0 / COUNT(DISTINCT match_id) as avg_per_match
    FROM territories
    WHERE specialist_type IS NOT NULL
    """

    result = db.conn.execute(query).fetchone()
    matches, total, unique_types, avg = result

    logger.info(f"Specialist validation:")
    logger.info(f"  Matches with specialists: {matches}")
    logger.info(f"  Total specialist assignments: {total}")
    logger.info(f"  Unique specialist types: {unique_types}")
    logger.info(f"  Average per match: {avg:.1f}")

    # Sanity checks
    if unique_types < 5:
        logger.error(f"Too few specialist types: {unique_types} (expected 10+)")
        return False

    if avg < 10:
        logger.warning(f"Low average specialists per match: {avg:.1f}")

    return True


def validate_improvement_counts() -> bool:
    """Verify improvement distribution looks reasonable."""
    db = TournamentDatabase("data/tournament_data.duckdb")

    query = """
    SELECT
        COUNT(DISTINCT match_id) as matches,
        COUNT(*) as total_tiles_with_improvements,
        COUNT(DISTINCT improvement_type) as unique_improvement_types,
        COUNT(*) * 1.0 / COUNT(DISTINCT match_id) as avg_per_match
    FROM territories
    WHERE improvement_type IS NOT NULL
    """

    result = db.conn.execute(query).fetchone()
    matches, total, unique_types, avg = result

    logger.info(f"\nImprovement validation:")
    logger.info(f"  Matches with improvements: {matches}")
    logger.info(f"  Total improvement tiles: {total}")
    logger.info(f"  Unique improvement types: {unique_types}")
    logger.info(f"  Average per match: {avg:.1f}")

    # Sanity checks
    if unique_types < 10:
        logger.error(f"Too few improvement types: {unique_types} (expected 20+)")
        return False

    if avg < 50:
        logger.warning(f"Low average improvements per match: {avg:.1f}")

    return True


def validate_resource_counts() -> bool:
    """Verify resource distribution looks reasonable."""
    db = TournamentDatabase("data/tournament_data.duckdb")

    query = """
    SELECT
        COUNT(DISTINCT match_id) as matches,
        COUNT(*) as total_tiles_with_resources,
        COUNT(DISTINCT resource_type) as unique_resource_types,
        COUNT(*) * 1.0 / COUNT(DISTINCT match_id) as avg_per_match
    FROM territories
    WHERE resource_type IS NOT NULL
    """

    result = db.conn.execute(query).fetchone()
    matches, total, unique_types, avg = result

    logger.info(f"\nResource validation:")
    logger.info(f"  Matches with resources: {matches}")
    logger.info(f"  Total resource tiles: {total}")
    logger.info(f"  Unique resource types: {unique_types}")
    logger.info(f"  Average per match: {avg:.1f}")

    # Sanity checks
    if unique_types < 10:
        logger.error(f"Too few resource types: {unique_types} (expected 20+)")
        return False

    return True


def validate_road_counts() -> bool:
    """Verify road network data looks reasonable."""
    db = TournamentDatabase("data/tournament_data.duckdb")

    query = """
    SELECT
        COUNT(DISTINCT match_id) as matches,
        SUM(CASE WHEN has_road THEN 1 ELSE 0 END) as total_road_tiles,
        SUM(CASE WHEN has_road THEN 1 ELSE 0 END) * 1.0 / COUNT(DISTINCT match_id) as avg_per_match
    FROM territories
    """

    result = db.conn.execute(query).fetchone()
    matches, total, avg = result

    logger.info(f"\nRoad validation:")
    logger.info(f"  Matches with roads: {matches}")
    logger.info(f"  Total road tiles: {total}")
    logger.info(f"  Average per match: {avg:.1f}")

    if avg < 10:
        logger.warning(f"Low average road tiles per match: {avg:.1f}")

    return True


def validate_specialist_improvement_correlation() -> bool:
    """Check that specialists are on appropriate improvement types."""
    db = TournamentDatabase("data/tournament_data.duckdb")

    query = """
    SELECT
        specialist_type,
        improvement_type,
        COUNT(*) as count
    FROM territories
    WHERE specialist_type IS NOT NULL
    GROUP BY specialist_type, improvement_type
    ORDER BY specialist_type, count DESC
    """

    results = db.conn.execute(query).fetchall()

    logger.info(f"\nSpecialist-Improvement correlation:")
    logger.info(f"  (Checking specialists are on appropriate tiles)")

    for spec_type, imp_type, count in results[:20]:  # Top 20
        logger.info(f"  {spec_type} on {imp_type}: {count}")

    # Look for known good patterns
    expected_patterns = [
        ("SPECIALIST_MINER", "IMPROVEMENT_MINE"),
        ("SPECIALIST_RANCHER", "IMPROVEMENT_PASTURE"),
        ("SPECIALIST_STONECUTTER", "IMPROVEMENT_QUARRY"),
    ]

    found_patterns = {(r[0], r[1]) for r in results}

    for spec, imp in expected_patterns:
        if (spec, imp) in found_patterns:
            logger.info(f"  ✓ Found expected pattern: {spec} on {imp}")
        else:
            logger.warning(f"  ⚠ Missing expected pattern: {spec} on {imp}")

    return True


def validate_sample_match() -> bool:
    """Deep dive into one match to verify data quality."""
    db = TournamentDatabase("data/tournament_data.duckdb")

    # Get first match with specialists
    query = """
    SELECT DISTINCT match_id
    FROM territories
    WHERE specialist_type IS NOT NULL
    LIMIT 1
    """
    match_id = db.conn.execute(query).fetchone()[0]

    logger.info(f"\nSample match deep dive (match_id={match_id}):")

    # Check final turn snapshot
    query = """
    SELECT
        COUNT(*) as total_tiles,
        COUNT(DISTINCT terrain_type) as terrain_types,
        COUNT(improvement_type) as tiles_with_improvements,
        COUNT(specialist_type) as tiles_with_specialists,
        COUNT(resource_type) as tiles_with_resources,
        SUM(CASE WHEN has_road THEN 1 ELSE 0 END) as tiles_with_roads,
        MAX(turn_number) as final_turn
    FROM territories
    WHERE match_id = ?
    GROUP BY turn_number
    ORDER BY turn_number DESC
    LIMIT 1
    """

    result = db.conn.execute(query, [match_id]).fetchone()

    if result:
        tiles, terrains, imps, specs, res, roads, turn = result
        logger.info(f"  Final turn: {turn}")
        logger.info(f"  Total tiles: {tiles}")
        logger.info(f"  Terrain types: {terrains}")
        logger.info(f"  Tiles with improvements: {imps}")
        logger.info(f"  Tiles with specialists: {specs}")
        logger.info(f"  Tiles with resources: {res}")
        logger.info(f"  Tiles with roads: {roads}")

        if specs == 0:
            logger.warning("  No specialists found in sample match")
            return False

    return True


def main():
    """Run all validation checks."""
    logger.info("=" * 60)
    logger.info("Territory Tile Detail Validation")
    logger.info("=" * 60)

    checks = [
        ("Specialist counts", validate_specialist_counts),
        ("Improvement counts", validate_improvement_counts),
        ("Resource counts", validate_resource_counts),
        ("Road counts", validate_road_counts),
        ("Specialist-Improvement correlation", validate_specialist_improvement_correlation),
        ("Sample match", validate_sample_match),
    ]

    results = []
    for name, check_func in checks:
        try:
            passed = check_func()
            results.append((name, passed))
        except Exception as e:
            logger.error(f"Check '{name}' failed with error: {e}")
            results.append((name, False))

    logger.info("\n" + "=" * 60)
    logger.info("Validation Summary")
    logger.info("=" * 60)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{status}: {name}")

    all_passed = all(passed for _, passed in results)

    if all_passed:
        logger.info("\n✓ All validation checks passed!")
        return 0
    else:
        logger.error("\n✗ Some validation checks failed")
        return 1


if __name__ == "__main__":
    exit(main())
```

**Run validation:**
```bash
uv run python scripts/validate_territory_data.py
```

**Expected output:** All checks should pass

**Commit:** `test: Add territory tile detail validation script`

---

### Task 11: Update Schema Export

**What:** Regenerate schema documentation with new columns

**Why:** Keep docs in sync with actual database

**Steps:**
```bash
# Export current schema
uv run python scripts/export_schema.py

# Verify docs/schema.sql was updated
git diff docs/schema.sql

# Should show new columns in territories table
```

**Commit:** `docs: Update exported schema with tile details`

---

### Task 12: Test Query Performance

**What:** Verify queries still perform well with new columns

**Why:** More columns = more data, could slow queries

**Steps:**
```bash
uv run python -c "
from tournament_visualizer.data.database import TournamentDatabase
import time

db = TournamentDatabase('data/tournament_data.duckdb')

# Test basic territory query
start = time.time()
result = db.conn.execute('''
    SELECT * FROM territories
    WHERE match_id = 1 AND turn_number = 50
    LIMIT 100
''').fetchall()
elapsed = time.time() - start
print(f'Basic query: {elapsed:.3f}s ({len(result)} rows)')

# Test specialist query
start = time.time()
result = db.conn.execute('''
    SELECT match_id, COUNT(*) as specialist_count
    FROM territories
    WHERE specialist_type IS NOT NULL
    GROUP BY match_id
''').fetchall()
elapsed = time.time() - start
print(f'Specialist aggregation: {elapsed:.3f}s ({len(result)} rows)')

# Test improvement query
start = time.time()
result = db.conn.execute('''
    SELECT improvement_type, COUNT(*) as count
    FROM territories
    WHERE improvement_type IS NOT NULL
    GROUP BY improvement_type
    ORDER BY count DESC
''').fetchall()
elapsed = time.time() - start
print(f'Improvement aggregation: {elapsed:.3f}s ({len(result)} rows)')
"
```

**Expected:** All queries under 1 second

**Commit:** Not needed (just verification)

---

### Task 13: Write Integration Test

**File:** `tests/test_integration_territory_import.py` (new file)

**What:** End-to-end test of import pipeline with new fields

**Why:** Verify entire system works together

**Code:**
```python
"""Integration test for territory tile detail import."""

import tempfile
import zipfile
from pathlib import Path
from tournament_visualizer.data.parser import OldWorldSaveParser
from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.etl import GameImporter


def test_full_territory_import_with_tile_details():
    """Test complete import pipeline with specialists and improvements."""

    # Create minimal valid save file
    xml_content = """<?xml version="1.0"?>
<Root
    MapWidth="3"
    Turn="2"
    GameName="Test Game"
    Year="100">
    <Player ID="0" OnlineID="12345" Name="TestPlayer" Team="0" />
    <GameState Turn="1" Year="100" />
    <GameState Turn="2" Year="101" />
    <Tile ID="0">
        <Terrain>TERRAIN_GRASSLAND</Terrain>
        <Improvement>IMPROVEMENT_FARM</Improvement>
        <Resource>RESOURCE_WHEAT</Resource>
        <Road />
        <OwnerHistory><T1>0</T1></OwnerHistory>
    </Tile>
    <Tile ID="1">
        <Terrain>TERRAIN_TEMPERATE</Terrain>
        <Improvement>IMPROVEMENT_MINE</Improvement>
        <Specialist>SPECIALIST_MINER</Specialist>
        <Road />
        <OwnerHistory><T1>0</T1></OwnerHistory>
    </Tile>
    <Tile ID="2">
        <Terrain>TERRAIN_WATER</Terrain>
    </Tile>
</Root>
"""

    # Create temporary zip file
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Write XML to zip
        zip_path = tmpdir_path / "test_game.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("test_game.xml", xml_content)

        # Create temporary database
        db_path = tmpdir_path / "test.duckdb"
        db = TournamentDatabase(str(db_path))
        db.create_tables()

        # Import via ETL pipeline
        importer = GameImporter(db)
        match_id = importer.import_game(str(zip_path))

        assert match_id is not None

        # Verify territories were imported with new fields
        territories = db.conn.execute("""
            SELECT
                turn_number,
                x_coordinate,
                y_coordinate,
                terrain_type,
                improvement_type,
                specialist_type,
                resource_type,
                has_road
            FROM territories
            WHERE match_id = ?
            ORDER BY turn_number, x_coordinate, y_coordinate
        """, [match_id]).fetchall()

        # Should have 3 tiles × 2 turns = 6 records
        assert len(territories) == 6

        # Check turn 2, tile 0 (farm with wheat and road)
        t2_tile0 = [t for t in territories if t[0] == 2 and t[1] == 0][0]
        assert t2_tile0[3] == "TERRAIN_GRASSLAND"
        assert t2_tile0[4] == "IMPROVEMENT_FARM"
        assert t2_tile0[5] is None  # No specialist
        assert t2_tile0[6] == "RESOURCE_WHEAT"
        assert t2_tile0[7] is True  # Has road

        # Check turn 2, tile 1 (mine with specialist)
        t2_tile1 = [t for t in territories if t[0] == 2 and t[1] == 1][0]
        assert t2_tile1[3] == "TERRAIN_TEMPERATE"
        assert t2_tile1[4] == "IMPROVEMENT_MINE"
        assert t2_tile1[5] == "SPECIALIST_MINER"
        assert t2_tile1[6] is None  # No resource
        assert t2_tile1[7] is True  # Has road

        # Check turn 2, tile 2 (water, no features)
        t2_tile2 = [t for t in territories if t[0] == 2 and t[1] == 2][0]
        assert t2_tile2[3] == "TERRAIN_WATER"
        assert t2_tile2[4] is None  # No improvement
        assert t2_tile2[5] is None  # No specialist
        assert t2_tile2[6] is None  # No resource
        assert t2_tile2[7] is False  # No road
```

**Run test:**
```bash
uv run pytest tests/test_integration_territory_import.py -v
```

**Expected:** Test passes

**Commit:** `test: Add integration test for territory tile detail import`

---

### Task 14: Update CLAUDE.md Documentation

**File:** `CLAUDE.md`

**What:** Document the new tile detail data in project guide

**Why:** Future developers need to know about this data

**Steps:**
1. Open `CLAUDE.md`
2. Find the "City Data Analysis" section
3. Add new "Territory Tile Details" section after it

**Content to add:**
```markdown
## Territory Tile Detail Analysis

### Overview
The `territories` table tracks turn-by-turn snapshots of every tile on the map, including ownership, terrain, improvements, specialists, resources, and infrastructure.

### What We Track
- **Ownership**: Which player controls each tile each turn
- **Terrain**: Base terrain type (grassland, desert, water, urban, etc.)
- **Improvements**: Buildings on tiles (mines, farms, quarries, barracks, etc.)
- **Specialists**: Expert workers assigned to tiles (miners, ranchers, priests, officers, etc.)
- **Resources**: Natural resources (horses, marble, wheat, etc.)
- **Infrastructure**: Road network

### Database Table
- `territories` - Complete map state per turn

See: `docs/database-schema.md` for complete schema

### Querying Territory Data

```python
from tournament_visualizer.data.queries import TournamentQueries, get_queries

# Get global queries instance
queries = get_queries()

# Get territories for a specific match and turn
territories_df = queries.get_match_territories(match_id=1, turn_number=50)

# Count specialists by type
specialist_counts = queries.get_specialist_counts(match_id=1)

# Get improvement distribution
improvement_stats = queries.get_improvement_distribution(match_id=1)
```

### Common Analyses

**Specialist Usage:**
```sql
-- Which players use the most specialists?
SELECT
    p.player_name,
    COUNT(DISTINCT t.specialist_type) as specialist_types_used,
    COUNT(*) as total_specialists
FROM territories t
JOIN players p ON t.match_id = p.match_id AND t.owner_player_id = p.player_id
WHERE t.specialist_type IS NOT NULL
  AND t.turn_number = (SELECT MAX(turn_number) FROM territories WHERE match_id = t.match_id)
GROUP BY p.player_name
ORDER BY total_specialists DESC;
```

**Infrastructure Investment:**
```sql
-- Track improvement build-out over time
SELECT
    turn_number,
    COUNT(DISTINCT CASE WHEN improvement_type IS NOT NULL THEN concat(x_coordinate, ',', y_coordinate) END) as total_improvements,
    SUM(CASE WHEN has_road THEN 1 ELSE 0 END) as total_roads
FROM territories
WHERE match_id = 1 AND owner_player_id = 1
GROUP BY turn_number
ORDER BY turn_number;
```

**Resource Control:**
```sql
-- Who controls strategic resources?
SELECT
    p.player_name,
    t.resource_type,
    COUNT(*) as tiles_controlled
FROM territories t
JOIN players p ON t.match_id = p.match_id AND t.owner_player_id = p.player_id
WHERE t.resource_type IN ('RESOURCE_IRON', 'RESOURCE_HORSE', 'RESOURCE_MARBLE')
  AND t.turn_number = (SELECT MAX(turn_number) FROM territories WHERE match_id = t.match_id)
GROUP BY p.player_name, t.resource_type
ORDER BY p.player_name, tiles_controlled DESC;
```

### Data Volume

Territory data is **large**:
- ~2000 tiles per map
- ~100+ turns per game
- = ~200,000+ records per match
- Most fields are NULL (compress well)

### Performance Tips

- Always filter by `match_id` and `turn_number`
- Use final turn for end-state analysis: `turn_number = (SELECT MAX(turn_number) FROM territories WHERE match_id = ?)`
- Consider creating indexes if queries are slow
```

**Commit:** `docs: Document territory tile detail data in CLAUDE.md`

---

### Task 15: Clean Up and Final Testing

**What:** Run all tests and validation scripts

**Why:** Ensure nothing broke

**Steps:**
```bash
# Run full test suite
uv run pytest -v

# Run validation scripts
uv run python scripts/validate_territory_data.py
uv run python scripts/validate_city_data.py

# Quick manual check
uv run python -c "
from tournament_visualizer.data.queries import get_queries

queries = get_queries()

# This should work without errors
print('Queries initialized successfully')
print(f'Database connection OK')
"
```

**Expected:** All tests pass, all validations pass

**Commit:** Not needed

---

## Testing Checklist

Before marking this complete, verify:

- [ ] All unit tests pass (`uv run pytest tests/test_parser_territories.py`)
- [ ] Integration test passes (`uv run pytest tests/test_integration_territory_import.py`)
- [ ] Full test suite passes (`uv run pytest`)
- [ ] Validation script passes (`uv run python scripts/validate_territory_data.py`)
- [ ] Database has 4M+ territory records with new columns populated
- [ ] Sample queries return expected data
- [ ] Documentation is updated (schema.sql, CLAUDE.md)
- [ ] Migration is documented (docs/migrations/005_*.md)

## Success Criteria

1. **Data Quality:**
   - Specialist data exists for all matches
   - Improvement types are captured correctly
   - Resources match expected distribution
   - Roads show logical network patterns

2. **Code Quality:**
   - All tests pass
   - No regression in existing functionality
   - Code follows DRY principle (no duplication)
   - Clear docstrings on modified methods

3. **Documentation:**
   - Schema docs updated
   - Migration documented
   - CLAUDE.md has usage examples
   - Validation script in place

## Rollback Plan

If something goes wrong:

```bash
# Restore database backup
rm data/tournament_data.duckdb
cp data/tournament_data.duckdb.backup_YYYYMMDD_HHMMSS data/tournament_data.duckdb

# Revert code changes
git revert HEAD~N  # Where N is number of commits to undo

# Verify old system works
uv run pytest
```

## Future Enhancements

After this is complete and stable, consider:

1. **Map Visualizations:**
   - Specialist density heatmaps
   - Improvement type distribution charts
   - Resource control over time animations

2. **Strategic Analysis:**
   - Economic focus metrics (improvement types)
   - Military vs. economic specialist ratios
   - Infrastructure investment timing

3. **Performance:**
   - Add indexes on (match_id, turn_number) if queries slow
   - Consider materialized views for common aggregations

4. **Additional Tile Data:**
   - Height (hills, mountains)
   - Vegetation (forests)
   - Units (military positions)
   - Cities (urban centers)

## Questions?

If stuck:

1. **Parser errors:** Check XML structure with `unzip -p saves/file.zip | less`
2. **Database errors:** Use `uv run duckdb data/tournament_data.duckdb -c "DESCRIBE territories"` to debug schema
3. **Test failures:** Run with `-vv` flag for verbose output
4. **Import errors:** Check `reimport.log` for detailed error messages

Refer to:
- `docs/developer-guide.md` for architecture
- `docs/database-schema.md` for table relationships
- `CLAUDE.md` for quick reference
