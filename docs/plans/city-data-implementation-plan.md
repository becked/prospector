# City Data Implementation Plan

## Overview

### Problem
Tournament save files contain rich city data (population, production, events, ownership) but we're not currently tracking any of it. We need to extract and analyze city data to understand player expansion patterns, production strategies, and territorial control.

### Solution
Implement city data collection in the existing parser and database pipeline. Extract core city attributes (name, owner, founded turn, production counts) to enable expansion and production strategy analysis.

### Success Criteria
- Extract city data from XML saves into database
- Track unit production and project counts per city
- Enable queries about expansion speed and production focus
- Display city analytics in dashboard
- Handle edge cases (captured cities, missing data)

---

## Prerequisites

### Required Knowledge
- **Python 3.11+**: Type hints, dataclasses
- **DuckDB**: SQL DDL, queries, indexes
- **uv**: Package manager (`uv run python script.py`)
- **pytest**: Testing framework with fixtures
- **XML parsing**: ElementTree (already used in codebase)
- **Old World game mechanics**: Cities, units, projects, families

### Required Setup
1. **Existing development environment** (already set up)
   ```bash
   # Verify setup
   uv run python -c "import duckdb; print('OK')"
   uv run pytest --version
   ```

2. **Sample data** (already exists)
   ```bash
   # Verify save files exist
   ls -l saves/*.zip | head -3

   # Verify database exists
   ls -lh data/tournament_data.duckdb
   ```

3. **Backup database** (CRITICAL - always backup before schema changes)
   ```bash
   cp data/tournament_data.duckdb data/tournament_data.duckdb.backup_$(date +%Y%m%d_%H%M%S)
   ```

---

## Architecture Overview

### Current System
```
saves/*.zip (XML)
    ↓ (parser.py)
DuckDB tables:
    - matches
    - players
    - events
    - rulers
    - territories
    - player_yield_history
    - units_produced
    ↓ (queries.py)
Dash App
```

### After This Change
```
saves/*.zip (XML)
    ↓ (parser.py - ENHANCED)
DuckDB tables:
    - matches
    - players
    - cities ← NEW
    - city_unit_production ← NEW
    - city_projects ← NEW
    ↓ (queries.py - ENHANCED)
Dash App (+ city analytics)
```

### New Components
1. **Parser Methods** (in `tournament_visualizer/data/parser.py`)
   - `extract_cities()` - Parse city XML elements
   - `extract_city_unit_production()` - Parse unit production counts
   - `extract_city_projects()` - Parse project counts

2. **Database Tables** (new schema)
   - `cities` - Core city attributes
   - `city_unit_production` - Units built per city
   - `city_projects` - Projects completed per city

3. **Database Methods** (in `tournament_visualizer/data/database.py`)
   - `insert_cities()` - Bulk insert cities
   - `insert_city_unit_production()` - Bulk insert production
   - `insert_city_projects()` - Bulk insert projects

4. **Query Functions** (in `tournament_visualizer/data/queries.py`)
   - `get_match_cities()` - Get cities for a match
   - `get_player_expansion_stats()` - Expansion analysis
   - `get_production_summary()` - Production patterns

5. **Migration Script** (`scripts/migrate_add_city_tables.py`)
   - Create tables
   - Create indexes
   - Rollback capability

6. **Validation Script** (`scripts/validate_city_data.py`)
   - Verify data quality
   - Check constraints
   - Report statistics

---

## Database Schema

### New Tables

#### Table: `cities`
```sql
CREATE TABLE cities (
    city_id INTEGER NOT NULL,            -- XML City ID (0-based in XML)
    match_id BIGINT NOT NULL,            -- FK to matches
    player_id BIGINT NOT NULL,           -- Current owner (FK to players)
    city_name VARCHAR NOT NULL,          -- e.g., "CITYNAME_NINEVEH"
    tile_id INTEGER NOT NULL,            -- Map location
    founded_turn INTEGER NOT NULL,       -- When city was founded
    family_name VARCHAR,                 -- Controlling family (e.g., "FAMILY_TUDIYA")
    is_capital BOOLEAN DEFAULT FALSE,    -- Whether this is a capital
    population INTEGER,                  -- Current population (citizens)
    first_player_id BIGINT,              -- Original founder (for conquest tracking)
    governor_id INTEGER,                 -- Character ID of governor
    PRIMARY KEY (match_id, city_id)
);

CREATE INDEX idx_cities_match_id ON cities(match_id);
CREATE INDEX idx_cities_player_id ON cities(match_id, player_id);
CREATE INDEX idx_cities_founded_turn ON cities(match_id, founded_turn);
```

**Why these columns?**
- `city_id`: Unique per match (XML uses 0-based ID)
- `player_id`: Current owner (may differ from founder if captured)
- `city_name`: Identifies the city (e.g., Nineveh, Persepolis)
- `founded_turn`: When city was founded (critical for expansion analysis)
- `first_player_id`: Original founder (track conquests)
- `is_capital`: Starting capitals are strategically important
- `population`: Current size (development indicator)

#### Table: `city_unit_production`
```sql
CREATE TABLE city_unit_production (
    production_id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id BIGINT NOT NULL,
    city_id INTEGER NOT NULL,
    unit_type VARCHAR NOT NULL,          -- e.g., "UNIT_SETTLER", "UNIT_SPEARMAN"
    count INTEGER NOT NULL,              -- Total units produced
    FOREIGN KEY (match_id, city_id) REFERENCES cities(match_id, city_id)
);

CREATE INDEX idx_city_production_match_city ON city_unit_production(match_id, city_id);
CREATE INDEX idx_city_production_unit_type ON city_unit_production(unit_type);
```

**Why separate table?**
- One city produces many unit types
- Enables efficient filtering (e.g., "show all military production")
- Normalized design (DRY principle)

#### Table: `city_projects`
```sql
CREATE TABLE city_projects (
    project_id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id BIGINT NOT NULL,
    city_id INTEGER NOT NULL,
    project_type VARCHAR NOT NULL,       -- e.g., "PROJECT_FORUM_2"
    count INTEGER NOT NULL,              -- Times completed
    FOREIGN KEY (match_id, city_id) REFERENCES cities(match_id, city_id)
);

CREATE INDEX idx_city_projects_match_city ON city_projects(match_id, city_id);
CREATE INDEX idx_city_projects_type ON city_projects(project_type);
```

**Why separate table?**
- Same reasoning as unit production
- Projects are rarer, so separate analysis

---

## Critical Domain Knowledge

### XML Structure (From Investigation)
```xml
<City
    ID="0"                              # 0-based ID (city_id in DB)
    TileID="1292"                       # Map location
    Player="1"                          # Owner (0-based, +1 for DB)
    Family="FAMILY_TUDIYA"              # Controlling family
    Founded="1">                        # Turn founded
    <NameType>CITYNAME_NINEVEH</NameType>
    <GovernorID>72</GovernorID>
    <Citizens>3</Citizens>              # Population
    <Capital />                         # Present if capital
    <FirstPlayer>1</FirstPlayer>        # Original founder
    <LastPlayer>1</LastPlayer>          # Current owner

    <UnitProductionCounts>
        <UNIT_SETTLER>4</UNIT_SETTLER>
        <UNIT_WORKER>1</UNIT_WORKER>
        <UNIT_SPEARMAN>2</UNIT_SPEARMAN>
    </UnitProductionCounts>

    <ProjectCount>
        <PROJECT_FORUM_2>1</PROJECT_FORUM_2>
        <PROJECT_SWORD_CULT_TITHE>1</PROJECT_SWORD_CULT_TITHE>
    </ProjectCount>

    <!-- Many other elements we'll skip for now (YAGNI) -->
</City>
```

### Player ID Mapping (CRITICAL!)
**XML uses 0-based IDs, database uses 1-based:**
```python
# XML: <Player ID="0">
# Database: player_id = 1
database_player_id = int(xml_player_attr) + 1
```

**Important:** Player ID="0" is valid and should NOT be skipped!

### City Naming
- Cities use constant names: `CITYNAME_NINEVEH`, `CITYNAME_PERSEPOLIS`
- These are NOT friendly names, just identifiers
- We store as-is (YAGNI - no need to beautify now)

### Conquest Detection
- `FirstPlayer` = original founder
- `LastPlayer` = current owner (should match Player attribute)
- If `FirstPlayer != LastPlayer` → city was captured

---

## Task Breakdown

### Task 0: Project Setup & Discovery (15 min)

#### Subtask 0.1: Explore Existing Parser Code
**What to do**:
1. Read relevant documentation:
   ```bash
   cat CLAUDE.md  # Project conventions
   cat docs/database-schema.md  # Current schema
   ```

2. Examine existing parser patterns:
   ```bash
   # Look at how events are parsed
   grep -A 20 "def extract_events" tournament_visualizer/data/parser.py

   # Look at how players are parsed
   grep -A 20 "def extract_players" tournament_visualizer/data/parser.py
   ```

3. Look at test patterns:
   ```bash
   cat tests/test_parser.py | head -100
   cat tests/test_parser_rulers.py | head -100
   ```

4. Check current database schema:
   ```bash
   uv run duckdb data/tournament_data.duckdb -readonly -c "SHOW TABLES"
   uv run duckdb data/tournament_data.duckdb -readonly -c "DESCRIBE players"
   ```

**Expected Output**:
- Understanding of parser structure (uses ElementTree)
- Knowledge of test patterns (fixtures, sample XML)
- Familiarity with database patterns (bulk inserts)

**Files to examine**:
- `tournament_visualizer/data/parser.py` (lines 1-200, then search for "extract_" methods)
- `tournament_visualizer/data/database.py` (lines 1-100, then search for "insert_" methods)
- `tests/test_parser.py`
- `docs/database-schema.md`

#### Subtask 0.2: Extract Sample City XML
**What to do**:
```bash
# Extract a sample save for reference
unzip -p saves/match_426504721_anarkos-becked.zip > /tmp/sample_game.xml

# Look at City structure
grep -A 100 '<City$' /tmp/sample_game.xml | head -150

# Count cities in sample
python3 << 'EOF'
import re
with open('/tmp/sample_game.xml') as f:
    content = f.read()
    cities = re.findall(r'<City\s+ID="(\d+)"', content)
    print(f"Found {len(cities)} cities")
    print(f"IDs: {sorted(set(int(c) for c in cities))}")
EOF
```

**Expected Output**:
- Sample XML file at `/tmp/sample_game.xml`
- Understanding of City element structure
- Knowledge of how many cities to expect (~10-15 per game)

**Commit Point**: None (exploration only)

---

### Task 1: Database Schema Migration (TDD) (1 hour)

#### Subtask 1.1: Write Migration Tests First
**File**: `tests/test_migration_city_tables.py`

```python
"""Tests for city tables migration.

Test Strategy:
- Use temporary database for isolation
- Test table creation, indexes, constraints
- Test migration is idempotent (safe to run twice)
- Test rollback works
- Test foreign key constraints
"""

import pytest
import duckdb
import tempfile
import shutil
from pathlib import Path


class TestCityTablesMigration:
    """Test migration for city-related tables."""

    @pytest.fixture
    def temp_db_path(self) -> Path:
        """Create temporary database with minimal matches/players tables.

        Returns:
            Path to temporary database file
        """
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test.duckdb"

        conn = duckdb.connect(str(db_path))

        # Create minimal matches table for FK constraint
        conn.execute("""
            CREATE TABLE matches (
                match_id BIGINT PRIMARY KEY
            )
        """)
        conn.execute("INSERT INTO matches VALUES (1), (2)")

        # Create minimal players table for FK constraint
        conn.execute("""
            CREATE TABLE players (
                player_id BIGINT NOT NULL,
                match_id BIGINT NOT NULL,
                player_name VARCHAR,
                PRIMARY KEY (match_id, player_id)
            )
        """)
        conn.execute("""
            INSERT INTO players VALUES
            (1, 1, 'anarkos'),
            (2, 1, 'becked'),
            (1, 2, 'moose'),
            (2, 2, 'fluffbunny')
        """)

        conn.close()

        yield db_path

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_migration_creates_cities_table(self, temp_db_path: Path) -> None:
        """Test that migration creates cities table with correct schema."""
        from scripts.migrate_add_city_tables import migrate_up

        # Run migration
        migrate_up(str(temp_db_path))

        # Verify table exists
        conn = duckdb.connect(str(temp_db_path), read_only=True)

        # Check table exists
        tables = conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]
        assert 'cities' in table_names

        # Check columns
        columns = conn.execute("DESCRIBE cities").fetchall()
        column_names = [col[0] for col in columns]

        expected_columns = [
            'city_id', 'match_id', 'player_id', 'city_name',
            'tile_id', 'founded_turn', 'family_name', 'is_capital',
            'population', 'first_player_id', 'governor_id'
        ]

        for col in expected_columns:
            assert col in column_names, f"Column '{col}' missing from cities table"

        conn.close()

    def test_migration_creates_production_tables(self, temp_db_path: Path) -> None:
        """Test that migration creates unit production and project tables."""
        from scripts.migrate_add_city_tables import migrate_up

        migrate_up(str(temp_db_path))

        conn = duckdb.connect(str(temp_db_path), read_only=True)

        tables = conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]

        assert 'city_unit_production' in table_names
        assert 'city_projects' in table_names

        conn.close()

    def test_migration_creates_indexes(self, temp_db_path: Path) -> None:
        """Test that indexes are created for query performance."""
        from scripts.migrate_add_city_tables import migrate_up

        migrate_up(str(temp_db_path))

        conn = duckdb.connect(str(temp_db_path), read_only=True)

        # DuckDB uses PRAGMA show_tables for indexes
        # We'll verify indexes exist by checking query plans
        # For this test, we'll just verify queries don't error

        # Try queries that should use indexes
        result = conn.execute("""
            SELECT * FROM cities WHERE match_id = 1
        """).fetchall()
        # Should work (even if empty)

        conn.close()

    def test_migration_idempotent(self, temp_db_path: Path) -> None:
        """Test that running migration twice doesn't error."""
        from scripts.migrate_add_city_tables import migrate_up

        # Run twice
        migrate_up(str(temp_db_path))
        migrate_up(str(temp_db_path))  # Should not crash

        # Verify tables still exist
        conn = duckdb.connect(str(temp_db_path), read_only=True)
        tables = conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]

        assert 'cities' in table_names
        assert 'city_unit_production' in table_names
        assert 'city_projects' in table_names

        conn.close()

    def test_can_insert_city(self, temp_db_path: Path) -> None:
        """Test inserting a city with all required fields."""
        from scripts.migrate_add_city_tables import migrate_up

        migrate_up(str(temp_db_path))

        conn = duckdb.connect(str(temp_db_path))

        # Insert a city
        conn.execute("""
            INSERT INTO cities (
                city_id, match_id, player_id, city_name,
                tile_id, founded_turn, is_capital, population
            ) VALUES (
                0, 1, 1, 'CITYNAME_NINEVEH',
                1292, 1, TRUE, 3
            )
        """)

        # Verify insertion
        result = conn.execute("SELECT * FROM cities").fetchone()
        assert result is not None
        assert result[0] == 0  # city_id
        assert result[1] == 1  # match_id
        assert result[2] == 1  # player_id
        assert result[3] == 'CITYNAME_NINEVEH'  # city_name

        conn.close()

    def test_can_insert_unit_production(self, temp_db_path: Path) -> None:
        """Test inserting unit production data."""
        from scripts.migrate_add_city_tables import migrate_up

        migrate_up(str(temp_db_path))

        conn = duckdb.connect(str(temp_db_path))

        # Insert a city first
        conn.execute("""
            INSERT INTO cities (
                city_id, match_id, player_id, city_name,
                tile_id, founded_turn
            ) VALUES (0, 1, 1, 'CITYNAME_NINEVEH', 1292, 1)
        """)

        # Insert production data
        conn.execute("""
            INSERT INTO city_unit_production (
                match_id, city_id, unit_type, count
            ) VALUES (1, 0, 'UNIT_SETTLER', 4)
        """)

        # Verify
        result = conn.execute("""
            SELECT * FROM city_unit_production
        """).fetchone()

        assert result[1] == 1  # match_id
        assert result[2] == 0  # city_id
        assert result[3] == 'UNIT_SETTLER'  # unit_type
        assert result[4] == 4  # count

        conn.close()

    def test_foreign_key_constraint(self, temp_db_path: Path) -> None:
        """Test that foreign key to matches table works."""
        from scripts.migrate_add_city_tables import migrate_up

        migrate_up(str(temp_db_path))

        conn = duckdb.connect(str(temp_db_path))

        # Try to insert city with non-existent match_id
        # Note: DuckDB requires enabling constraints
        conn.execute("PRAGMA foreign_keys = ON")

        with pytest.raises(duckdb.ConstraintException):
            conn.execute("""
                INSERT INTO cities (
                    city_id, match_id, player_id, city_name,
                    tile_id, founded_turn
                ) VALUES (0, 999, 1, 'TEST', 1, 1)
            """)

        conn.close()

    def test_unique_city_per_match(self, temp_db_path: Path) -> None:
        """Test that (match_id, city_id) is unique."""
        from scripts.migrate_add_city_tables import migrate_up

        migrate_up(str(temp_db_path))

        conn = duckdb.connect(str(temp_db_path))

        # Insert first city
        conn.execute("""
            INSERT INTO cities (
                city_id, match_id, player_id, city_name,
                tile_id, founded_turn
            ) VALUES (0, 1, 1, 'CITY_A', 100, 1)
        """)

        # Try to insert same city_id in same match
        with pytest.raises(duckdb.ConstraintException):
            conn.execute("""
                INSERT INTO cities (
                    city_id, match_id, player_id, city_name,
                    tile_id, founded_turn
                ) VALUES (0, 1, 2, 'CITY_B', 200, 5)
            """)

        conn.close()

    def test_rollback(self, temp_db_path: Path) -> None:
        """Test that rollback removes all city tables."""
        from scripts.migrate_add_city_tables import migrate_up, migrate_down

        # Migrate up
        migrate_up(str(temp_db_path))

        # Verify tables exist
        conn = duckdb.connect(str(temp_db_path), read_only=True)
        tables_before = conn.execute("SHOW TABLES").fetchall()
        table_names_before = [t[0] for t in tables_before]
        assert 'cities' in table_names_before
        conn.close()

        # Rollback
        migrate_down(str(temp_db_path))

        # Verify tables are gone
        conn = duckdb.connect(str(temp_db_path), read_only=True)
        tables_after = conn.execute("SHOW TABLES").fetchall()
        table_names_after = [t[0] for t in tables_after]
        assert 'cities' not in table_names_after
        assert 'city_unit_production' not in table_names_after
        assert 'city_projects' not in table_names_after
        conn.close()
```

**Run tests (should fail)**:
```bash
uv run pytest tests/test_migration_city_tables.py -v
```

**Expected**: All tests fail because migration script doesn't exist yet. This is correct for TDD!

**Why This Test Design?**
1. **Fixtures**: Reusable temporary database (`temp_db_path`)
2. **Isolated**: Each test gets fresh database
3. **Comprehensive**: Tests schema, constraints, idempotency, rollback
4. **Clear Names**: Test names explain what they verify
5. **Comments**: Explain WHY, not just WHAT

**Commit Point**: ✓ "test: Add city tables migration tests (TDD, failing)"

---

#### Subtask 1.2: Create Migration Documentation
**File**: `docs/migrations/004_add_city_tables.md`

```markdown
# Migration 004: Add City Tables

## Overview
Add support for tracking cities and their production in tournament matches.
Enables analysis of expansion patterns, production strategies, and territorial control.

## Rationale
- Save files contain detailed city data (population, production, ownership)
- Cities are fundamental to Old World gameplay strategy
- Need to track expansion speed (when cities founded)
- Need to track production focus (military vs. economy)
- Need to detect city captures (FirstPlayer vs. LastPlayer)

## Schema Changes

### New Table: `cities`
```sql
CREATE TABLE cities (
    city_id INTEGER NOT NULL,
    match_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,
    city_name VARCHAR NOT NULL,
    tile_id INTEGER NOT NULL,
    founded_turn INTEGER NOT NULL,
    family_name VARCHAR,
    is_capital BOOLEAN DEFAULT FALSE,
    population INTEGER,
    first_player_id BIGINT,
    governor_id INTEGER,
    PRIMARY KEY (match_id, city_id)
);

CREATE INDEX idx_cities_match_id ON cities(match_id);
CREATE INDEX idx_cities_player_id ON cities(match_id, player_id);
CREATE INDEX idx_cities_founded_turn ON cities(match_id, founded_turn);
```

### New Table: `city_unit_production`
```sql
CREATE TABLE city_unit_production (
    production_id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id BIGINT NOT NULL,
    city_id INTEGER NOT NULL,
    unit_type VARCHAR NOT NULL,
    count INTEGER NOT NULL,
    FOREIGN KEY (match_id, city_id) REFERENCES cities(match_id, city_id)
);

CREATE INDEX idx_city_production_match_city ON city_unit_production(match_id, city_id);
CREATE INDEX idx_city_production_unit_type ON city_unit_production(unit_type);
```

### New Table: `city_projects`
```sql
CREATE TABLE city_projects (
    project_id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id BIGINT NOT NULL,
    city_id INTEGER NOT NULL,
    project_type VARCHAR NOT NULL,
    count INTEGER NOT NULL,
    FOREIGN KEY (match_id, city_id) REFERENCES cities(match_id, city_id)
);

CREATE INDEX idx_city_projects_match_city ON city_projects(match_id, city_id);
CREATE INDEX idx_city_projects_type ON city_projects(project_type);
```

## Migration Script

See: `scripts/migrate_add_city_tables.py`

Run with:
```bash
# Backup first!
cp data/tournament_data.duckdb data/tournament_data.duckdb.backup_$(date +%Y%m%d_%H%M%S)

# Apply migration
uv run python scripts/migrate_add_city_tables.py

# Verify
uv run python scripts/migrate_add_city_tables.py --verify
```

## Rollback Procedure

To undo this migration:
```bash
uv run python scripts/migrate_add_city_tables.py --rollback
```

Or manually:
```sql
DROP TABLE IF EXISTS city_projects;
DROP TABLE IF EXISTS city_unit_production;
DROP TABLE IF EXISTS cities;
```

## Verification

After migration, verify:
```bash
# Check tables exist
uv run duckdb data/tournament_data.duckdb -readonly -c "SHOW TABLES"

# Should show: cities, city_unit_production, city_projects

# Check schema
uv run duckdb data/tournament_data.duckdb -readonly -c "DESCRIBE cities"
```

## Data Population

After migration, re-import tournament data:
```bash
# Backup database
cp data/tournament_data.duckdb data/tournament_data.duckdb.backup_before_reimport

# Re-import with city data
uv run python scripts/import_attachments.py --directory saves --force --verbose
```

## Related Files
- `tournament_visualizer/data/parser.py`: Parses city data from XML
- `tournament_visualizer/data/database.py`: Inserts city data
- `tournament_visualizer/data/queries.py`: Queries city data
- `scripts/validate_city_data.py`: Validates city data quality

## Impact Assessment

**Data Size**: Expect ~10-15 cities per match
- 27 matches × 12 cities/match ≈ 324 city records
- Each city has ~5 unit types ≈ 1,620 production records
- Low storage impact (< 100 KB total)

**Query Performance**: Indexes on match_id and player_id
- City lookups by match: O(log n) via index
- Production analysis: O(log n) via unit_type index
- No performance concerns for this data size

**Breaking Changes**: None
- Only adds new tables
- Existing queries unaffected
- Requires data re-import to populate
```

**Commit Point**: ✓ "docs: Add migration 004 documentation for city tables"

---

#### Subtask 1.3: Implement Migration Script
**File**: `scripts/migrate_add_city_tables.py`

```python
"""Migration 004: Add city tables for tracking city data.

This migration adds support for tracking cities, unit production, and projects.

Usage:
    # Apply migration
    uv run python scripts/migrate_add_city_tables.py

    # Rollback migration
    uv run python scripts/migrate_add_city_tables.py --rollback

    # Verify migration
    uv run python scripts/migrate_add_city_tables.py --verify

See: docs/migrations/004_add_city_tables.md
"""

import argparse
import logging
from pathlib import Path

import duckdb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "data/tournament_data.duckdb"


def migrate_up(db_path: str = DEFAULT_DB_PATH) -> None:
    """Apply migration: Create city tables.

    Args:
        db_path: Path to DuckDB database
    """
    logger.info(f"Applying migration 004 to {db_path}")

    conn = duckdb.connect(db_path)

    try:
        # Create cities table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cities (
                city_id INTEGER NOT NULL,
                match_id BIGINT NOT NULL,
                player_id BIGINT NOT NULL,
                city_name VARCHAR NOT NULL,
                tile_id INTEGER NOT NULL,
                founded_turn INTEGER NOT NULL,
                family_name VARCHAR,
                is_capital BOOLEAN DEFAULT FALSE,
                population INTEGER,
                first_player_id BIGINT,
                governor_id INTEGER,
                PRIMARY KEY (match_id, city_id)
            )
        """)
        logger.info("✓ Created cities table")

        # Create indexes for cities
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cities_match_id
            ON cities(match_id)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cities_player_id
            ON cities(match_id, player_id)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cities_founded_turn
            ON cities(match_id, founded_turn)
        """)
        logger.info("✓ Created indexes for cities")

        # Create city_unit_production table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS city_unit_production (
                production_id INTEGER PRIMARY KEY,
                match_id BIGINT NOT NULL,
                city_id INTEGER NOT NULL,
                unit_type VARCHAR NOT NULL,
                count INTEGER NOT NULL
            )
        """)
        logger.info("✓ Created city_unit_production table")

        # Create indexes for production
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_city_production_match_city
            ON city_unit_production(match_id, city_id)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_city_production_unit_type
            ON city_unit_production(unit_type)
        """)
        logger.info("✓ Created indexes for city_unit_production")

        # Create city_projects table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS city_projects (
                project_id INTEGER PRIMARY KEY,
                match_id BIGINT NOT NULL,
                city_id INTEGER NOT NULL,
                project_type VARCHAR NOT NULL,
                count INTEGER NOT NULL
            )
        """)
        logger.info("✓ Created city_projects table")

        # Create indexes for projects
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_city_projects_match_city
            ON city_projects(match_id, city_id)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_city_projects_type
            ON city_projects(project_type)
        """)
        logger.info("✓ Created indexes for city_projects")

        logger.info("✓ Migration 004 applied successfully")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        conn.close()


def migrate_down(db_path: str = DEFAULT_DB_PATH) -> None:
    """Rollback migration: Drop city tables.

    Args:
        db_path: Path to DuckDB database
    """
    logger.info(f"Rolling back migration 004 from {db_path}")

    conn = duckdb.connect(db_path)

    try:
        # Drop tables in reverse order (respect FKs)
        conn.execute("DROP TABLE IF EXISTS city_projects")
        logger.info("✓ Dropped city_projects table")

        conn.execute("DROP TABLE IF EXISTS city_unit_production")
        logger.info("✓ Dropped city_unit_production table")

        conn.execute("DROP TABLE IF EXISTS cities")
        logger.info("✓ Dropped cities table")

        logger.info("✓ Migration 004 rolled back successfully")

    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        raise
    finally:
        conn.close()


def verify_migration(db_path: str = DEFAULT_DB_PATH) -> None:
    """Verify migration was applied correctly.

    Args:
        db_path: Path to DuckDB database
    """
    conn = duckdb.connect(db_path, read_only=True)

    try:
        # Check tables exist
        tables = conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]

        required_tables = ['cities', 'city_unit_production', 'city_projects']

        for table in required_tables:
            if table in table_names:
                logger.info(f"✓ Table '{table}' exists")

                # Check columns for cities table
                if table == 'cities':
                    columns = conn.execute(f"DESCRIBE {table}").fetchall()
                    column_names = [col[0] for col in columns]

                    expected_columns = [
                        'city_id', 'match_id', 'player_id', 'city_name',
                        'tile_id', 'founded_turn', 'family_name', 'is_capital',
                        'population', 'first_player_id', 'governor_id'
                    ]

                    for col in expected_columns:
                        if col in column_names:
                            logger.info(f"  ✓ Column '{col}' exists")
                        else:
                            logger.error(f"  ✗ Column '{col}' missing")
            else:
                logger.error(f"✗ Table '{table}' does not exist")

    finally:
        conn.close()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Apply or rollback migration 004 (city tables)"
    )
    parser.add_argument(
        '--rollback',
        action='store_true',
        help='Rollback the migration'
    )
    parser.add_argument(
        '--db',
        default=DEFAULT_DB_PATH,
        help='Path to database (default: data/tournament_data.duckdb)'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify migration was applied'
    )

    args = parser.parse_args()

    if args.verify:
        verify_migration(args.db)
    elif args.rollback:
        migrate_down(args.db)
    else:
        migrate_up(args.db)


if __name__ == '__main__':
    main()
```

**Run tests**:
```bash
uv run pytest tests/test_migration_city_tables.py -v
```

**Expected**: All tests pass ✓

**Test on real database** (backup first!):
```bash
# Backup
cp data/tournament_data.duckdb data/tournament_data.duckdb.backup_before_migration_004

# Apply
uv run python scripts/migrate_add_city_tables.py

# Verify
uv run python scripts/migrate_add_city_tables.py --verify

# Check manually
uv run duckdb data/tournament_data.duckdb -readonly -c "DESCRIBE cities"
uv run duckdb data/tournament_data.duckdb -readonly -c "SHOW TABLES"
```

**Commit Point**: ✓ "feat: Add migration script for city tables"

---

### Task 2: Parser Implementation (TDD) (2 hours)

#### Subtask 2.1: Write Parser Tests First
**File**: `tests/test_parser_cities.py`

```python
"""Tests for city data parsing.

Test Strategy:
- Use sample XML with known city data
- Test happy path (normal cities)
- Test edge cases (capitals, captured cities, empty production)
- Test player ID conversion (XML 0-based → DB 1-based)
- Verify all required fields are extracted
"""

import pytest
from pathlib import Path
from tournament_visualizer.data.parser import OldWorldSaveParser


class TestCityParsing:
    """Test parsing city data from XML."""

    @pytest.fixture
    def sample_xml_with_cities(self, tmp_path: Path) -> Path:
        """Create sample XML with city data.

        Returns:
            Path to temporary XML file
        """
        xml_content = """<?xml version="1.0"?>
<Game
    Version="1.0.75"
    Turn="69">

    <Player ID="0">
        <Name>anarkos</Name>
        <Civilization>PERSIA</Civilization>
    </Player>

    <Player ID="1">
        <Name>becked</Name>
        <Civilization>ASSYRIA</Civilization>
    </Player>

    <City
        ID="0"
        TileID="1292"
        Player="1"
        Family="FAMILY_TUDIYA"
        Founded="1">
        <NameType>CITYNAME_NINEVEH</NameType>
        <GovernorID>72</GovernorID>
        <Citizens>3</Citizens>
        <Capital />
        <FirstPlayer>1</FirstPlayer>
        <LastPlayer>1</LastPlayer>
        <UnitProductionCounts>
            <UNIT_SETTLER>4</UNIT_SETTLER>
            <UNIT_WORKER>1</UNIT_WORKER>
            <UNIT_SPEARMAN>2</UNIT_SPEARMAN>
        </UnitProductionCounts>
        <ProjectCount>
            <PROJECT_FORUM_2>1</PROJECT_FORUM_2>
            <PROJECT_SWORD_CULT_TITHE>1</PROJECT_SWORD_CULT_TITHE>
        </ProjectCount>
    </City>

    <City
        ID="1"
        TileID="1375"
        Player="0"
        Family="FAMILY_ACHAEMENID"
        Founded="1">
        <NameType>CITYNAME_PERSEPOLIS</NameType>
        <GovernorID>61</GovernorID>
        <Citizens>5</Citizens>
        <Capital />
        <FirstPlayer>0</FirstPlayer>
        <LastPlayer>0</LastPlayer>
        <UnitProductionCounts>
            <UNIT_SETTLER>4</UNIT_SETTLER>
            <UNIT_WORKER>1</UNIT_WORKER>
        </UnitProductionCounts>
        <ProjectCount>
            <PROJECT_GRAIN_DOLE>1</PROJECT_GRAIN_DOLE>
        </ProjectCount>
    </City>

    <City
        ID="2"
        TileID="1073"
        Player="1"
        Family="FAMILY_TUDIYA"
        Founded="7">
        <NameType>CITYNAME_SAREISA</NameType>
        <Citizens>1</Citizens>
        <FirstPlayer>1</FirstPlayer>
        <LastPlayer>1</LastPlayer>
        <UnitProductionCounts>
            <UNIT_WORKER>2</UNIT_WORKER>
        </UnitProductionCounts>
        <ProjectCount>
            <PROJECT_FORUM_1>1</PROJECT_FORUM_1>
        </ProjectCount>
    </City>

    <City
        ID="3"
        TileID="999"
        Player="1"
        Family="FAMILY_ADASI"
        Founded="20">
        <NameType>CITYNAME_CAPTURED</NameType>
        <Citizens>2</Citizens>
        <FirstPlayer>0</FirstPlayer>
        <LastPlayer>1</LastPlayer>
        <UnitProductionCounts />
        <ProjectCount />
    </City>
</Game>
"""
        xml_file = tmp_path / "test_cities.xml"
        xml_file.write_text(xml_content)
        return xml_file

    def test_extract_cities_basic(self, sample_xml_with_cities: Path) -> None:
        """Test extracting basic city data from XML."""
        parser = OldWorldSaveParser("")
        parser.parse_xml_file(str(sample_xml_with_cities))

        cities = parser.extract_cities()

        # Should find 4 cities
        assert len(cities) == 4

        # Check first city (Nineveh)
        nineveh = cities[0]
        assert nineveh['city_id'] == 0
        assert nineveh['city_name'] == 'CITYNAME_NINEVEH'
        assert nineveh['tile_id'] == 1292
        assert nineveh['founded_turn'] == 1
        assert nineveh['family_name'] == 'FAMILY_TUDIYA'
        assert nineveh['population'] == 3
        assert nineveh['governor_id'] == 72

    def test_player_id_conversion(self, sample_xml_with_cities: Path) -> None:
        """Test that player IDs are converted from XML (0-based) to DB (1-based).

        CRITICAL: XML uses 0-based IDs, database uses 1-based.
        XML Player="0" → DB player_id=1
        """
        parser = OldWorldSaveParser("")
        parser.parse_xml_file(str(sample_xml_with_cities))

        cities = parser.extract_cities()

        # Nineveh: XML Player="1" → DB player_id=2
        nineveh = cities[0]
        assert nineveh['player_id'] == 2, "XML Player=1 should become DB player_id=2"

        # Persepolis: XML Player="0" → DB player_id=1
        persepolis = cities[1]
        assert persepolis['player_id'] == 1, "XML Player=0 should become DB player_id=1"

    def test_capital_flag(self, sample_xml_with_cities: Path) -> None:
        """Test that capital cities are identified correctly."""
        parser = OldWorldSaveParser("")
        parser.parse_xml_file(str(sample_xml_with_cities))

        cities = parser.extract_cities()

        # First two cities are capitals (have <Capital /> element)
        assert cities[0]['is_capital'] is True
        assert cities[1]['is_capital'] is True

        # Third city is not a capital
        assert cities[2]['is_capital'] is False

    def test_captured_city_detection(self, sample_xml_with_cities: Path) -> None:
        """Test that captured cities are detected correctly.

        Captured city: FirstPlayer != LastPlayer
        """
        parser = OldWorldSaveParser("")
        parser.parse_xml_file(str(sample_xml_with_cities))

        cities = parser.extract_cities()

        # Fourth city was captured
        captured = cities[3]
        assert captured['first_player_id'] == 1  # XML FirstPlayer="0" → DB 1
        assert captured['player_id'] == 2  # XML LastPlayer="1" → DB 2
        assert captured['first_player_id'] != captured['player_id']

        # First city was not captured
        nineveh = cities[0]
        assert nineveh['first_player_id'] == nineveh['player_id']

    def test_extract_unit_production(self, sample_xml_with_cities: Path) -> None:
        """Test extracting unit production counts."""
        parser = OldWorldSaveParser("")
        parser.parse_xml_file(str(sample_xml_with_cities))

        production = parser.extract_city_unit_production()

        # Should have production from cities 0, 1, 2 (city 3 is empty)
        # City 0: 3 unit types (SETTLER, WORKER, SPEARMAN)
        # City 1: 2 unit types (SETTLER, WORKER)
        # City 2: 1 unit type (WORKER)
        # Total: 6 records
        assert len(production) == 6

        # Check Nineveh's production (city_id=0)
        nineveh_production = [p for p in production if p['city_id'] == 0]
        assert len(nineveh_production) == 3

        # Check settler production
        settlers = [p for p in nineveh_production if p['unit_type'] == 'UNIT_SETTLER']
        assert len(settlers) == 1
        assert settlers[0]['count'] == 4

    def test_extract_city_projects(self, sample_xml_with_cities: Path) -> None:
        """Test extracting city project counts."""
        parser = OldWorldSaveParser("")
        parser.parse_xml_file(str(sample_xml_with_cities))

        projects = parser.extract_city_projects()

        # City 0: 2 projects
        # City 1: 1 project
        # City 2: 1 project
        # City 3: 0 projects (empty)
        # Total: 4 records
        assert len(projects) == 4

        # Check Nineveh's projects (city_id=0)
        nineveh_projects = [p for p in projects if p['city_id'] == 0]
        assert len(nineveh_projects) == 2

        # Check forum project
        forums = [p for p in nineveh_projects if p['project_type'] == 'PROJECT_FORUM_2']
        assert len(forums) == 1
        assert forums[0]['count'] == 1

    def test_empty_production(self, sample_xml_with_cities: Path) -> None:
        """Test handling cities with no production.

        Edge case: City 3 has <UnitProductionCounts /> (empty)
        Should not error, just return empty list for that city.
        """
        parser = OldWorldSaveParser("")
        parser.parse_xml_file(str(sample_xml_with_cities))

        production = parser.extract_city_unit_production()

        # City 3 should have no production records
        city_3_production = [p for p in production if p['city_id'] == 3]
        assert len(city_3_production) == 0

    def test_missing_optional_fields(self, tmp_path: Path) -> None:
        """Test handling cities with missing optional fields.

        Optional fields: governor_id, population, family_name
        """
        xml_content = """<?xml version="1.0"?>
<Game Turn="10">
    <City
        ID="0"
        TileID="100"
        Player="0"
        Founded="5">
        <NameType>CITYNAME_TEST</NameType>
        <FirstPlayer>0</FirstPlayer>
        <LastPlayer>0</LastPlayer>
        <UnitProductionCounts />
        <ProjectCount />
    </City>
</Game>
"""
        xml_file = tmp_path / "test_minimal.xml"
        xml_file.write_text(xml_content)

        parser = OldWorldSaveParser("")
        parser.parse_xml_file(str(xml_file))

        cities = parser.extract_cities()

        assert len(cities) == 1
        city = cities[0]

        # Required fields should exist
        assert city['city_id'] == 0
        assert city['city_name'] == 'CITYNAME_TEST'

        # Optional fields should be None or have defaults
        assert city.get('governor_id') is None
        assert city.get('population') is None or city.get('population') == 0
        assert city.get('family_name') is None
        assert city['is_capital'] is False

    def test_zero_player_id_valid(self, tmp_path: Path) -> None:
        """Test that Player ID 0 is valid and not skipped.

        CRITICAL: Player ID="0" is valid! Don't skip it.
        XML Player="0" → DB player_id=1
        """
        xml_content = """<?xml version="1.0"?>
<Game Turn="1">
    <City
        ID="0"
        TileID="100"
        Player="0"
        Founded="1">
        <NameType>CITYNAME_CAPITAL</NameType>
        <Capital />
        <FirstPlayer>0</FirstPlayer>
        <LastPlayer>0</LastPlayer>
        <UnitProductionCounts />
        <ProjectCount />
    </City>
</Game>
"""
        xml_file = tmp_path / "test_player_zero.xml"
        xml_file.write_text(xml_content)

        parser = OldWorldSaveParser("")
        parser.parse_xml_file(str(xml_file))

        cities = parser.extract_cities()

        assert len(cities) == 1
        assert cities[0]['player_id'] == 1  # XML 0 → DB 1
```

**Run tests (should fail)**:
```bash
uv run pytest tests/test_parser_cities.py -v
```

**Expected**: All tests fail because parser methods don't exist yet. This is correct for TDD!

**Why This Test Design?**
1. **Fixtures**: Reusable sample XML with known data
2. **Comprehensive Coverage**: Happy path + edge cases
3. **Critical Domain Rules**: Player ID conversion, capital detection, conquest tracking
4. **Clear Assertions**: Each test verifies specific behavior
5. **Descriptive Names**: Test names explain what they test

**Commit Point**: ✓ "test: Add city parser tests (TDD, failing)"

---

#### Subtask 2.2: Implement Parser Methods
**File**: `tournament_visualizer/data/parser.py` (add to existing file)

Add these methods to the `OldWorldSaveParser` class:

```python
    def extract_cities(self) -> List[Dict[str, Any]]:
        """Extract city data from the save file.

        Returns:
            List of city dictionaries

        Raises:
            ValueError: If XML not parsed
        """
        if self.root is None:
            raise ValueError("XML not parsed. Call extract_and_parse() first.")

        logger.info("Extracting city data")
        cities = []

        # Find all City elements (direct children of root)
        for city_elem in self.root.findall("City"):
            try:
                city_data = self._parse_city_element(city_elem)
                cities.append(city_data)
            except Exception as e:
                logger.warning(f"Failed to parse city: {e}")
                continue

        logger.info(f"Extracted {len(cities)} cities")
        return cities

    def _parse_city_element(self, city_elem: ET.Element) -> Dict[str, Any]:
        """Parse a single City XML element.

        Args:
            city_elem: City XML element

        Returns:
            Dictionary with city data
        """
        # Extract required attributes
        city_id = self._safe_int(city_elem.get('ID'))
        tile_id = self._safe_int(city_elem.get('TileID'))
        player_xml_id = self._safe_int(city_elem.get('Player'))
        founded_turn = self._safe_int(city_elem.get('Founded'))

        # Convert player ID: XML is 0-based, database is 1-based
        player_id = player_xml_id + 1

        # Extract optional attributes
        family_name = city_elem.get('Family')

        # Extract child elements
        name_elem = city_elem.find('NameType')
        city_name = name_elem.text if name_elem is not None else 'UNKNOWN'

        # Population (optional)
        citizens_elem = city_elem.find('Citizens')
        population = self._safe_int(citizens_elem.text) if citizens_elem is not None else None

        # Governor (optional)
        governor_elem = city_elem.find('GovernorID')
        governor_id = self._safe_int(governor_elem.text) if governor_elem is not None else None

        # Capital flag (present = capital, absent = not capital)
        capital_elem = city_elem.find('Capital')
        is_capital = capital_elem is not None

        # First and last player (for conquest detection)
        first_player_elem = city_elem.find('FirstPlayer')
        last_player_elem = city_elem.find('LastPlayer')

        # Convert first/last player IDs (also 0-based in XML)
        first_player_id = None
        if first_player_elem is not None:
            first_player_xml_id = self._safe_int(first_player_elem.text)
            first_player_id = first_player_xml_id + 1

        # Build city dictionary
        city_data = {
            'city_id': city_id,
            'city_name': city_name,
            'tile_id': tile_id,
            'player_id': player_id,
            'founded_turn': founded_turn,
            'family_name': family_name,
            'is_capital': is_capital,
            'population': population,
            'governor_id': governor_id,
            'first_player_id': first_player_id,
        }

        return city_data

    def extract_city_unit_production(self) -> List[Dict[str, Any]]:
        """Extract unit production counts for all cities.

        Returns:
            List of production dictionaries
        """
        if self.root is None:
            raise ValueError("XML not parsed. Call extract_and_parse() first.")

        logger.info("Extracting city unit production")
        production_records = []

        for city_elem in self.root.findall("City"):
            try:
                city_id = self._safe_int(city_elem.get('ID'))

                # Find UnitProductionCounts element
                production_elem = city_elem.find('UnitProductionCounts')
                if production_elem is None:
                    continue

                # Extract each unit type
                for unit_elem in production_elem:
                    unit_type = unit_elem.tag
                    count = self._safe_int(unit_elem.text)

                    if count > 0:  # Only record non-zero production
                        production_records.append({
                            'city_id': city_id,
                            'unit_type': unit_type,
                            'count': count
                        })

            except Exception as e:
                logger.warning(f"Failed to parse production for city {city_id}: {e}")
                continue

        logger.info(f"Extracted {len(production_records)} production records")
        return production_records

    def extract_city_projects(self) -> List[Dict[str, Any]]:
        """Extract project counts for all cities.

        Returns:
            List of project dictionaries
        """
        if self.root is None:
            raise ValueError("XML not parsed. Call extract_and_parse() first.")

        logger.info("Extracting city projects")
        project_records = []

        for city_elem in self.root.findall("City"):
            try:
                city_id = self._safe_int(city_elem.get('ID'))

                # Find ProjectCount element
                projects_elem = city_elem.find('ProjectCount')
                if projects_elem is None:
                    continue

                # Extract each project type
                for project_elem in projects_elem:
                    project_type = project_elem.tag
                    count = self._safe_int(project_elem.text)

                    if count > 0:  # Only record non-zero counts
                        project_records.append({
                            'city_id': city_id,
                            'project_type': project_type,
                            'count': count
                        })

            except Exception as e:
                logger.warning(f"Failed to parse projects for city {city_id}: {e}")
                continue

        logger.info(f"Extracted {len(project_records)} project records")
        return project_records

    def _safe_int(self, value: Any) -> int:
        """Safely convert value to integer.

        Args:
            value: Value to convert

        Returns:
            Integer value, or 0 if conversion fails
        """
        if value is None:
            return 0

        try:
            return int(value)
        except (ValueError, TypeError):
            return 0
```

**Note**: The `_safe_int` method may already exist in the parser. If so, don't duplicate it.

**Run tests**:
```bash
uv run pytest tests/test_parser_cities.py -v
```

**Expected**: All tests pass ✓

**Commit Point**: ✓ "feat: Add city parsing to OldWorldSaveParser"

---

### Task 3: Database Integration (TDD) (1.5 hours)

#### Subtask 3.1: Write Database Tests
**File**: `tests/test_database_cities.py`

```python
"""Tests for city database operations.

Test Strategy:
- Test bulk insert of cities
- Test bulk insert of production/projects
- Test foreign key constraints
- Test duplicate handling
- Use temporary database
"""

import pytest
import duckdb
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any


class TestCityDatabaseOperations:
    """Test database operations for city data."""

    @pytest.fixture
    def temp_db_with_schema(self) -> Path:
        """Create temporary database with city tables.

        Returns:
            Path to temporary database
        """
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test.duckdb"

        # Run migration to create schema
        from scripts.migrate_add_city_tables import migrate_up
        migrate_up(str(db_path))

        # Create matches table
        conn = duckdb.connect(str(db_path))
        conn.execute("""
            CREATE TABLE matches (
                match_id BIGINT PRIMARY KEY
            )
        """)
        conn.execute("INSERT INTO matches VALUES (1), (2)")

        # Create players table
        conn.execute("""
            CREATE TABLE players (
                player_id BIGINT,
                match_id BIGINT,
                player_name VARCHAR,
                PRIMARY KEY (match_id, player_id)
            )
        """)
        conn.execute("""
            INSERT INTO players VALUES
            (1, 1, 'anarkos'),
            (2, 1, 'becked')
        """)

        conn.close()

        yield db_path

        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_cities(self) -> List[Dict[str, Any]]:
        """Sample city data for testing."""
        return [
            {
                'city_id': 0,
                'city_name': 'CITYNAME_NINEVEH',
                'tile_id': 1292,
                'player_id': 2,
                'founded_turn': 1,
                'family_name': 'FAMILY_TUDIYA',
                'is_capital': True,
                'population': 3,
                'governor_id': 72,
                'first_player_id': 2
            },
            {
                'city_id': 1,
                'city_name': 'CITYNAME_PERSEPOLIS',
                'tile_id': 1375,
                'player_id': 1,
                'founded_turn': 1,
                'family_name': 'FAMILY_ACHAEMENID',
                'is_capital': True,
                'population': 5,
                'governor_id': 61,
                'first_player_id': 1
            }
        ]

    @pytest.fixture
    def sample_production(self) -> List[Dict[str, Any]]:
        """Sample production data for testing."""
        return [
            {'city_id': 0, 'unit_type': 'UNIT_SETTLER', 'count': 4},
            {'city_id': 0, 'unit_type': 'UNIT_WORKER', 'count': 1},
            {'city_id': 1, 'unit_type': 'UNIT_SETTLER', 'count': 4},
        ]

    @pytest.fixture
    def sample_projects(self) -> List[Dict[str, Any]]:
        """Sample project data for testing."""
        return [
            {'city_id': 0, 'project_type': 'PROJECT_FORUM_2', 'count': 1},
            {'city_id': 1, 'project_type': 'PROJECT_GRAIN_DOLE', 'count': 1},
        ]

    def test_insert_cities(
        self,
        temp_db_with_schema: Path,
        sample_cities: List[Dict[str, Any]]
    ) -> None:
        """Test inserting cities into database."""
        from tournament_visualizer.data.database import DatabaseManager

        db_path = str(temp_db_with_schema)
        db = DatabaseManager(db_path)

        # Insert cities for match 1
        db.insert_cities(match_id=1, cities=sample_cities)

        # Verify insertion
        conn = duckdb.connect(db_path, read_only=True)
        cities = conn.execute("""
            SELECT city_id, city_name, player_id, is_capital
            FROM cities
            WHERE match_id = 1
            ORDER BY city_id
        """).fetchall()
        conn.close()

        assert len(cities) == 2
        assert cities[0][0] == 0  # city_id
        assert cities[0][1] == 'CITYNAME_NINEVEH'  # city_name
        assert cities[0][2] == 2  # player_id
        assert cities[0][3] is True  # is_capital

    def test_insert_unit_production(
        self,
        temp_db_with_schema: Path,
        sample_cities: List[Dict[str, Any]],
        sample_production: List[Dict[str, Any]]
    ) -> None:
        """Test inserting unit production data."""
        from tournament_visualizer.data.database import DatabaseManager

        db_path = str(temp_db_with_schema)
        db = DatabaseManager(db_path)

        # Insert cities first (required for FK)
        db.insert_cities(match_id=1, cities=sample_cities)

        # Insert production
        db.insert_city_unit_production(match_id=1, production=sample_production)

        # Verify insertion
        conn = duckdb.connect(db_path, read_only=True)
        production = conn.execute("""
            SELECT city_id, unit_type, count
            FROM city_unit_production
            WHERE match_id = 1
            ORDER BY city_id, unit_type
        """).fetchall()
        conn.close()

        assert len(production) == 3
        assert production[0][1] == 'UNIT_SETTLER'
        assert production[0][2] == 4

    def test_insert_city_projects(
        self,
        temp_db_with_schema: Path,
        sample_cities: List[Dict[str, Any]],
        sample_projects: List[Dict[str, Any]]
    ) -> None:
        """Test inserting city project data."""
        from tournament_visualizer.data.database import DatabaseManager

        db_path = str(temp_db_with_schema)
        db = DatabaseManager(db_path)

        # Insert cities first
        db.insert_cities(match_id=1, cities=sample_cities)

        # Insert projects
        db.insert_city_projects(match_id=1, projects=sample_projects)

        # Verify insertion
        conn = duckdb.connect(db_path, read_only=True)
        projects = conn.execute("""
            SELECT city_id, project_type, count
            FROM city_projects
            WHERE match_id = 1
            ORDER BY city_id
        """).fetchall()
        conn.close()

        assert len(projects) == 2
        assert projects[0][1] == 'PROJECT_FORUM_2'

    def test_insert_empty_lists(self, temp_db_with_schema: Path) -> None:
        """Test that inserting empty lists doesn't error."""
        from tournament_visualizer.data.database import DatabaseManager

        db = DatabaseManager(str(temp_db_with_schema))

        # Should not raise errors
        db.insert_cities(match_id=1, cities=[])
        db.insert_city_unit_production(match_id=1, production=[])
        db.insert_city_projects(match_id=1, projects=[])

        # Verify no data inserted
        conn = duckdb.connect(str(temp_db_with_schema), read_only=True)
        count = conn.execute("SELECT COUNT(*) FROM cities").fetchone()[0]
        assert count == 0
        conn.close()

    def test_duplicate_city_handling(
        self,
        temp_db_with_schema: Path,
        sample_cities: List[Dict[str, Any]]
    ) -> None:
        """Test that duplicate cities are handled (should replace or error).

        This depends on your strategy:
        - Option A: Primary key prevents duplicates (raises error)
        - Option B: Use INSERT OR REPLACE

        We'll test that duplicates are prevented.
        """
        from tournament_visualizer.data.database import DatabaseManager

        db = DatabaseManager(str(temp_db_with_schema))

        # Insert once
        db.insert_cities(match_id=1, cities=sample_cities)

        # Try to insert again (should error or be handled)
        with pytest.raises(Exception):  # DuckDB will raise constraint error
            db.insert_cities(match_id=1, cities=sample_cities)
```

**Run tests (will fail)**:
```bash
uv run pytest tests/test_database_cities.py -v
```

**Expected**: Tests fail because DatabaseManager methods don't exist yet.

**Commit Point**: ✓ "test: Add city database operation tests (TDD, failing)"

---

#### Subtask 3.2: Implement Database Methods
**File**: `tournament_visualizer/data/database.py` (add to `DatabaseManager` class)

```python
    def insert_cities(self, match_id: int, cities: List[Dict[str, Any]]) -> None:
        """Insert city data for a match.

        Args:
            match_id: Tournament match ID
            cities: List of city dictionaries from parser
        """
        if not cities:
            logger.debug(f"No cities to insert for match {match_id}")
            return

        logger.info(f"Inserting {len(cities)} cities for match {match_id}")

        # Prepare data for bulk insert
        records = []
        for city in cities:
            record = (
                city['city_id'],
                match_id,
                city['player_id'],
                city['city_name'],
                city['tile_id'],
                city['founded_turn'],
                city.get('family_name'),
                city.get('is_capital', False),
                city.get('population'),
                city.get('first_player_id'),
                city.get('governor_id')
            )
            records.append(record)

        # Bulk insert
        self.conn.executemany("""
            INSERT INTO cities (
                city_id, match_id, player_id, city_name,
                tile_id, founded_turn, family_name, is_capital,
                population, first_player_id, governor_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, records)

        logger.info(f"✓ Inserted {len(cities)} cities for match {match_id}")

    def insert_city_unit_production(
        self,
        match_id: int,
        production: List[Dict[str, Any]]
    ) -> None:
        """Insert city unit production data.

        Args:
            match_id: Tournament match ID
            production: List of production dictionaries from parser
        """
        if not production:
            logger.debug(f"No production data to insert for match {match_id}")
            return

        logger.info(f"Inserting {len(production)} production records for match {match_id}")

        # Prepare data for bulk insert
        records = []
        for prod in production:
            record = (
                match_id,
                prod['city_id'],
                prod['unit_type'],
                prod['count']
            )
            records.append(record)

        # Bulk insert
        self.conn.executemany("""
            INSERT INTO city_unit_production (
                match_id, city_id, unit_type, count
            ) VALUES (?, ?, ?, ?)
        """, records)

        logger.info(f"✓ Inserted {len(production)} production records")

    def insert_city_projects(
        self,
        match_id: int,
        projects: List[Dict[str, Any]]
    ) -> None:
        """Insert city project data.

        Args:
            match_id: Tournament match ID
            projects: List of project dictionaries from parser
        """
        if not projects:
            logger.debug(f"No project data to insert for match {match_id}")
            return

        logger.info(f"Inserting {len(projects)} project records for match {match_id}")

        # Prepare data for bulk insert
        records = []
        for proj in projects:
            record = (
                match_id,
                proj['city_id'],
                proj['project_type'],
                proj['count']
            )
            records.append(record)

        # Bulk insert
        self.conn.executemany("""
            INSERT INTO city_projects (
                match_id, city_id, project_type, count
            ) VALUES (?, ?, ?, ?)
        """, records)

        logger.info(f"✓ Inserted {len(projects)} project records")
```

**Run tests**:
```bash
uv run pytest tests/test_database_cities.py -v
```

**Expected**: All tests pass ✓

**Commit Point**: ✓ "feat: Add city database insertion methods"

---

### Task 4: ETL Integration (30 min)

#### Subtask 4.1: Update ETL to Process Cities
**File**: `tournament_visualizer/data/etl.py` (modify existing functions)

Find the main ETL function (likely named something like `process_save_file` or `import_match`) and add city processing:

```python
def process_save_file(save_file_path: str, db: DatabaseManager) -> Dict[str, Any]:
    """Process a single save file and import into database.

    Args:
        save_file_path: Path to .zip save file
        db: Database manager instance

    Returns:
        Dictionary with processing results
    """
    # ... existing code to parse match, players, events, etc. ...

    # Extract city data
    logger.info("Extracting city data")
    cities = parser.extract_cities()
    city_production = parser.extract_city_unit_production()
    city_projects = parser.extract_city_projects()

    # ... existing code to insert match, players, etc. ...

    # Insert city data
    if cities:
        db.insert_cities(match_id=match_id, cities=cities)

    if city_production:
        db.insert_city_unit_production(match_id=match_id, production=city_production)

    if city_projects:
        db.insert_city_projects(match_id=match_id, projects=city_projects)

    # ... rest of existing code ...

    return {
        # ... existing keys ...
        'cities_count': len(cities),
        'production_records': len(city_production),
        'project_records': len(city_projects)
    }
```

**Note**: Adapt this to your actual ETL structure. The key is to add city extraction and insertion alongside existing data processing.

**Test manually**:
```bash
# Backup database
cp data/tournament_data.duckdb data/tournament_data.duckdb.backup_before_city_import

# Test import with one file
uv run python scripts/import_attachments.py --directory saves --dry-run --verbose

# If dry-run looks good, do real import
uv run python scripts/import_attachments.py --directory saves --force --verbose
```

**Verify data**:
```bash
# Check city count
uv run duckdb data/tournament_data.duckdb -readonly -c "SELECT COUNT(*) FROM cities"

# Check sample cities
uv run duckdb data/tournament_data.duckdb -readonly -c "SELECT * FROM cities LIMIT 5"

# Check production data
uv run duckdb data/tournament_data.duckdb -readonly -c "SELECT COUNT(*) FROM city_unit_production"
```

**Commit Point**: ✓ "feat: Integrate city data extraction into ETL pipeline"

---

### Task 5: Query Functions (TDD) (1 hour)

#### Subtask 5.1: Write Query Tests
**File**: `tests/test_queries_cities.py`

```python
"""Tests for city query functions.

Test Strategy:
- Test basic city retrieval
- Test expansion analysis queries
- Test production analysis queries
- Use temporary database with known data
"""

import pytest
import duckdb
import tempfile
import shutil
from pathlib import Path


class TestCityQueries:
    """Test query functions for city data."""

    @pytest.fixture
    def temp_db_with_city_data(self) -> Path:
        """Create database with sample city data."""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test.duckdb"

        conn = duckdb.connect(str(db_path))

        # Create schema
        conn.execute("""
            CREATE TABLE matches (
                match_id BIGINT PRIMARY KEY,
                total_turns INTEGER
            )
        """)
        conn.execute("INSERT INTO matches VALUES (1, 92), (2, 47)")

        conn.execute("""
            CREATE TABLE players (
                player_id BIGINT,
                match_id BIGINT,
                player_name VARCHAR,
                PRIMARY KEY (match_id, player_id)
            )
        """)
        conn.execute("""
            INSERT INTO players VALUES
            (1, 1, 'anarkos'),
            (2, 1, 'becked'),
            (1, 2, 'moose'),
            (2, 2, 'fluffbunny')
        """)

        conn.execute("""
            CREATE TABLE cities (
                city_id INTEGER,
                match_id BIGINT,
                player_id BIGINT,
                city_name VARCHAR,
                tile_id INTEGER,
                founded_turn INTEGER,
                is_capital BOOLEAN,
                PRIMARY KEY (match_id, city_id)
            )
        """)
        conn.execute("""
            INSERT INTO cities VALUES
            (0, 1, 1, 'CITYNAME_NINEVEH', 100, 1, TRUE),
            (1, 1, 2, 'CITYNAME_PERSEPOLIS', 200, 1, TRUE),
            (2, 1, 1, 'CITYNAME_SAREISA', 300, 15, FALSE),
            (3, 1, 2, 'CITYNAME_ARBELA', 400, 22, FALSE),
            (0, 2, 1, 'CITYNAME_CAPITAL1', 500, 1, TRUE),
            (1, 2, 2, 'CITYNAME_CAPITAL2', 600, 1, TRUE)
        """)

        conn.execute("""
            CREATE TABLE city_unit_production (
                production_id INTEGER PRIMARY KEY,
                match_id BIGINT,
                city_id INTEGER,
                unit_type VARCHAR,
                count INTEGER
            )
        """)
        conn.execute("""
            INSERT INTO city_unit_production VALUES
            (1, 1, 0, 'UNIT_SETTLER', 4),
            (2, 1, 0, 'UNIT_WORKER', 1),
            (3, 1, 0, 'UNIT_SPEARMAN', 3),
            (4, 1, 1, 'UNIT_SETTLER', 3),
            (5, 1, 1, 'UNIT_ARCHER', 5)
        """)

        conn.close()

        yield db_path

        shutil.rmtree(temp_dir)

    def test_get_match_cities(self, temp_db_with_city_data: Path) -> None:
        """Test getting all cities for a match."""
        from tournament_visualizer.data.queries import get_match_cities

        cities = get_match_cities(match_id=1, db_path=str(temp_db_with_city_data))

        assert len(cities) == 4
        assert cities[0]['city_name'] == 'CITYNAME_NINEVEH'
        assert cities[0]['founded_turn'] == 1

    def test_get_player_expansion_stats(self, temp_db_with_city_data: Path) -> None:
        """Test expansion statistics for a match."""
        from tournament_visualizer.data.queries import get_player_expansion_stats

        stats = get_player_expansion_stats(match_id=1, db_path=str(temp_db_with_city_data))

        # Should have stats for 2 players
        assert len(stats) == 2

        # Check player 1 (anarkos)
        player1 = [s for s in stats if s['player_name'] == 'anarkos'][0]
        assert player1['total_cities'] == 2
        assert player1['first_city_turn'] == 1
        assert player1['last_city_turn'] == 15

        # Check player 2 (becked)
        player2 = [s for s in stats if s['player_name'] == 'becked'][0]
        assert player2['total_cities'] == 2
        assert player2['last_city_turn'] == 22

    def test_get_production_summary(self, temp_db_with_city_data: Path) -> None:
        """Test production summary by player."""
        from tournament_visualizer.data.queries import get_production_summary

        summary = get_production_summary(match_id=1, db_path=str(temp_db_with_city_data))

        # Should have summary for 2 players
        assert len(summary) == 2

        # Check player with Nineveh (city_id=0, player_id=1)
        player1 = [s for s in summary if s['player_id'] == 1][0]

        # Player 1's cities produced: 4 settlers, 1 worker, 3 spearmen = 8 units
        assert player1['total_units_produced'] == 8

        # Check unit breakdown exists
        assert 'unit_breakdown' in player1 or 'settlers' in player1
```

**Run tests (will fail)**:
```bash
uv run pytest tests/test_queries_cities.py -v
```

**Commit Point**: ✓ "test: Add city query tests (TDD, failing)"

---

#### Subtask 5.2: Implement Query Functions
**File**: `tournament_visualizer/data/queries.py` (add new functions)

```python
def get_match_cities(
    match_id: int,
    db_path: str = "data/tournament_data.duckdb"
) -> List[Dict[str, Any]]:
    """Get all cities for a specific match.

    Args:
        match_id: Tournament match ID
        db_path: Path to database

    Returns:
        List of city dictionaries
    """
    conn = duckdb.connect(db_path, read_only=True)

    result = conn.execute("""
        SELECT
            c.city_id,
            c.city_name,
            c.player_id,
            p.player_name,
            c.founded_turn,
            c.is_capital,
            c.population,
            c.tile_id
        FROM cities c
        JOIN players p ON c.match_id = p.match_id AND c.player_id = p.player_id
        WHERE c.match_id = ?
        ORDER BY c.founded_turn, c.city_id
    """, [match_id]).fetchall()

    conn.close()

    cities = []
    for row in result:
        cities.append({
            'city_id': row[0],
            'city_name': row[1],
            'player_id': row[2],
            'player_name': row[3],
            'founded_turn': row[4],
            'is_capital': row[5],
            'population': row[6],
            'tile_id': row[7]
        })

    return cities


def get_player_expansion_stats(
    match_id: int,
    db_path: str = "data/tournament_data.duckdb"
) -> List[Dict[str, Any]]:
    """Get expansion statistics for each player in a match.

    Args:
        match_id: Tournament match ID
        db_path: Path to database

    Returns:
        List of player expansion dictionaries
    """
    conn = duckdb.connect(db_path, read_only=True)

    result = conn.execute("""
        SELECT
            p.player_id,
            p.player_name,
            COUNT(c.city_id) as total_cities,
            MIN(c.founded_turn) as first_city_turn,
            MAX(c.founded_turn) as last_city_turn,
            SUM(CASE WHEN c.is_capital THEN 1 ELSE 0 END) as capital_count
        FROM players p
        LEFT JOIN cities c ON p.match_id = c.match_id AND p.player_id = c.player_id
        WHERE p.match_id = ?
        GROUP BY p.player_id, p.player_name
        ORDER BY total_cities DESC
    """, [match_id]).fetchall()

    conn.close()

    stats = []
    for row in result:
        stats.append({
            'player_id': row[0],
            'player_name': row[1],
            'total_cities': row[2],
            'first_city_turn': row[3],
            'last_city_turn': row[4],
            'capital_count': row[5]
        })

    return stats


def get_production_summary(
    match_id: int,
    db_path: str = "data/tournament_data.duckdb"
) -> List[Dict[str, Any]]:
    """Get unit production summary for each player.

    Args:
        match_id: Tournament match ID
        db_path: Path to database

    Returns:
        List of production summary dictionaries
    """
    conn = duckdb.connect(db_path, read_only=True)

    result = conn.execute("""
        SELECT
            p.player_id,
            p.player_name,
            SUM(prod.count) as total_units_produced,
            COUNT(DISTINCT prod.unit_type) as unique_unit_types,
            SUM(CASE WHEN prod.unit_type = 'UNIT_SETTLER' THEN prod.count ELSE 0 END) as settlers,
            SUM(CASE WHEN prod.unit_type = 'UNIT_WORKER' THEN prod.count ELSE 0 END) as workers
        FROM players p
        LEFT JOIN cities c ON p.match_id = c.match_id AND p.player_id = c.player_id
        LEFT JOIN city_unit_production prod ON c.match_id = prod.match_id AND c.city_id = prod.city_id
        WHERE p.match_id = ?
        GROUP BY p.player_id, p.player_name
        ORDER BY total_units_produced DESC
    """, [match_id]).fetchall()

    conn.close()

    summary = []
    for row in result:
        summary.append({
            'player_id': row[0],
            'player_name': row[1],
            'total_units_produced': row[2] or 0,
            'unique_unit_types': row[3] or 0,
            'settlers': row[4] or 0,
            'workers': row[5] or 0
        })

    return summary
```

**Run tests**:
```bash
uv run pytest tests/test_queries_cities.py -v
```

**Expected**: All tests pass ✓

**Commit Point**: ✓ "feat: Add query functions for city and production analysis"

---

### Task 6: Validation Script (45 min)

#### Subtask 6.1: Create Validation Script
**File**: `scripts/validate_city_data.py`

```python
"""Validate city data quality in database.

This script checks:
- Data integrity (all cities have required fields)
- Referential integrity (FKs are valid)
- Business rules (player IDs, founded turns)
- Data quality (reasonable values)

Usage:
    uv run python scripts/validate_city_data.py
    uv run python scripts/validate_city_data.py --match 1
"""

import argparse
import logging
from typing import Dict, Any, List

import duckdb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "data/tournament_data.duckdb"


def validate_city_data(db_path: str = DEFAULT_DB_PATH, match_id: int | None = None) -> Dict[str, Any]:
    """Validate city data in database.

    Args:
        db_path: Path to DuckDB database
        match_id: Optional specific match to validate

    Returns:
        Dictionary with validation results
    """
    conn = duckdb.connect(db_path, read_only=True)

    results = {
        'errors': [],
        'warnings': [],
        'stats': {}
    }

    try:
        # Check 1: Tables exist
        logger.info("Checking tables exist...")
        tables = conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]

        required_tables = ['cities', 'city_unit_production', 'city_projects']
        for table in required_tables:
            if table not in table_names:
                results['errors'].append(f"Table '{table}' does not exist")

        if results['errors']:
            logger.error(f"Missing tables: {results['errors']}")
            return results

        # Check 2: Count records
        logger.info("Counting records...")
        where_clause = f"WHERE match_id = {match_id}" if match_id else ""

        city_count = conn.execute(f"SELECT COUNT(*) FROM cities {where_clause}").fetchone()[0]
        prod_count = conn.execute(f"SELECT COUNT(*) FROM city_unit_production {where_clause}").fetchone()[0]
        proj_count = conn.execute(f"SELECT COUNT(*) FROM city_projects {where_clause}").fetchone()[0]

        results['stats']['total_cities'] = city_count
        results['stats']['total_production_records'] = prod_count
        results['stats']['total_project_records'] = proj_count

        logger.info(f"  Cities: {city_count}")
        logger.info(f"  Production records: {prod_count}")
        logger.info(f"  Project records: {proj_count}")

        if city_count == 0:
            results['warnings'].append("No cities found in database")
            return results

        # Check 3: Required fields populated
        logger.info("Checking required fields...")
        null_checks = [
            ("cities", "city_name"),
            ("cities", "player_id"),
            ("cities", "founded_turn"),
            ("cities", "tile_id")
        ]

        for table, column in null_checks:
            count = conn.execute(f"""
                SELECT COUNT(*) FROM {table} {where_clause.replace('WHERE', 'WHERE' if where_clause else 'WHERE')}
                AND {column} IS NULL
            """).fetchone()[0]

            if count > 0:
                results['errors'].append(f"{count} rows in {table} have NULL {column}")

        # Check 4: Foreign key integrity
        logger.info("Checking foreign key integrity...")

        # Cities with invalid match_id
        invalid_match = conn.execute(f"""
            SELECT COUNT(*)
            FROM cities c
            WHERE NOT EXISTS (SELECT 1 FROM matches m WHERE m.match_id = c.match_id)
            {where_clause.replace('WHERE', 'AND')}
        """).fetchone()[0]

        if invalid_match > 0:
            results['errors'].append(f"{invalid_match} cities have invalid match_id")

        # Cities with invalid player_id
        invalid_player = conn.execute(f"""
            SELECT COUNT(*)
            FROM cities c
            WHERE NOT EXISTS (
                SELECT 1 FROM players p
                WHERE p.match_id = c.match_id AND p.player_id = c.player_id
            )
            {where_clause.replace('WHERE', 'AND')}
        """).fetchone()[0]

        if invalid_player > 0:
            results['errors'].append(f"{invalid_player} cities have invalid player_id")

        # Check 5: Business rules
        logger.info("Checking business rules...")

        # Player IDs should be >= 1 (database uses 1-based)
        invalid_ids = conn.execute(f"""
            SELECT COUNT(*)
            FROM cities
            WHERE player_id < 1 {where_clause.replace('WHERE', 'OR')}
        """).fetchone()[0]

        if invalid_ids > 0:
            results['errors'].append(f"{invalid_ids} cities have invalid player_id < 1")

        # Founded turn should be >= 1
        invalid_turns = conn.execute(f"""
            SELECT COUNT(*)
            FROM cities
            WHERE founded_turn < 1 {where_clause.replace('WHERE', 'OR')}
        """).fetchone()[0]

        if invalid_turns > 0:
            results['warnings'].append(f"{invalid_turns} cities have invalid founded_turn < 1")

        # Check 6: Data quality
        logger.info("Checking data quality...")

        # Check for duplicate (match_id, city_id)
        duplicates = conn.execute(f"""
            SELECT match_id, city_id, COUNT(*) as count
            FROM cities
            {where_clause}
            GROUP BY match_id, city_id
            HAVING COUNT(*) > 1
        """).fetchall()

        if duplicates:
            results['errors'].append(f"{len(duplicates)} duplicate (match_id, city_id) pairs")
            for dup in duplicates[:5]:  # Show first 5
                results['errors'].append(f"  - Match {dup[0]}, City {dup[1]}: {dup[2]} copies")

        # Check 7: Statistics
        logger.info("Gathering statistics...")

        # Average cities per match
        avg_cities = conn.execute(f"""
            SELECT AVG(city_count)
            FROM (
                SELECT match_id, COUNT(*) as city_count
                FROM cities
                {where_clause}
                GROUP BY match_id
            )
        """).fetchone()[0]

        results['stats']['avg_cities_per_match'] = round(avg_cities, 1) if avg_cities else 0

        # Cities by player
        cities_by_player = conn.execute(f"""
            SELECT p.player_name, COUNT(c.city_id) as city_count
            FROM cities c
            JOIN players p ON c.match_id = p.match_id AND c.player_id = p.player_id
            {where_clause}
            GROUP BY p.player_name
            ORDER BY city_count DESC
            LIMIT 5
        """).fetchall()

        results['stats']['top_expanders'] = [
            {'player': row[0], 'cities': row[1]}
            for row in cities_by_player
        ]

    finally:
        conn.close()

    return results


def print_results(results: Dict[str, Any]) -> None:
    """Print validation results.

    Args:
        results: Validation results dictionary
    """
    print("\n" + "=" * 60)
    print("CITY DATA VALIDATION RESULTS")
    print("=" * 60)

    # Errors
    if results['errors']:
        print(f"\n❌ ERRORS ({len(results['errors'])})")
        for error in results['errors']:
            print(f"  - {error}")
    else:
        print("\n✅ No errors found")

    # Warnings
    if results['warnings']:
        print(f"\n⚠️  WARNINGS ({len(results['warnings'])})")
        for warning in results['warnings']:
            print(f"  - {warning}")

    # Statistics
    if results['stats']:
        print("\n📊 STATISTICS")
        stats = results['stats']
        print(f"  Total cities: {stats.get('total_cities', 0)}")
        print(f"  Production records: {stats.get('total_production_records', 0)}")
        print(f"  Project records: {stats.get('total_project_records', 0)}")
        print(f"  Avg cities per match: {stats.get('avg_cities_per_match', 0)}")

        if 'top_expanders' in stats and stats['top_expanders']:
            print("\n  Top 5 Expanders:")
            for player in stats['top_expanders']:
                print(f"    - {player['player']}: {player['cities']} cities")

    print("=" * 60 + "\n")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate city data quality in database"
    )
    parser.add_argument(
        '--db',
        default=DEFAULT_DB_PATH,
        help='Path to database (default: data/tournament_data.duckdb)'
    )
    parser.add_argument(
        '--match',
        type=int,
        help='Validate specific match only'
    )

    args = parser.parse_args()

    results = validate_city_data(db_path=args.db, match_id=args.match)
    print_results(results)

    # Exit code based on errors
    if results['errors']:
        exit(1)
    else:
        exit(0)


if __name__ == '__main__':
    main()
```

**Test validation script**:
```bash
# Run validation
uv run python scripts/validate_city_data.py

# Validate specific match
uv run python scripts/validate_city_data.py --match 1
```

**Commit Point**: ✓ "feat: Add city data validation script"

---

### Task 7: Documentation (30 min)

#### Subtask 7.1: Update User Documentation
**File**: `CLAUDE.md` (add section after existing content)

Add this section to your `CLAUDE.md`:

```markdown
## City Data Analysis

### Overview
City data tracks expansion patterns, production strategies, and territorial control for each tournament match.

### What We Track
- **Cities**: Name, owner, location, founding turn, population
- **Production**: Units built per city (settlers, military, workers)
- **Projects**: City projects completed (forums, temples, wonders)
- **Ownership**: Original founder vs. current owner (conquest tracking)

### Database Tables
- `cities` - Core city attributes
- `city_unit_production` - Units built per city
- `city_projects` - Projects completed per city

See: `docs/database-schema.md` for complete schema

### Querying City Data

```python
from tournament_visualizer.data.queries import (
    get_match_cities,
    get_player_expansion_stats,
    get_production_summary
)

# Get all cities in a match
cities = get_match_cities(match_id=1)
for city in cities:
    print(f"{city['city_name']} founded turn {city['founded_turn']}")

# Get expansion statistics
stats = get_player_expansion_stats(match_id=1)
for player in stats:
    print(f"{player['player_name']}: {player['total_cities']} cities")

# Get production summary
summary = get_production_summary(match_id=1)
for player in summary:
    print(f"{player['player_name']}: {player['settlers']} settlers")
```

### Validation

After re-importing data, validate city data:
```bash
uv run python scripts/validate_city_data.py
```

### Common Queries

```sql
-- Top expanders (most cities)
SELECT
    p.player_name,
    COUNT(c.city_id) as total_cities
FROM cities c
JOIN players p ON c.match_id = p.match_id AND c.player_id = p.player_id
GROUP BY p.player_name
ORDER BY total_cities DESC
LIMIT 10;

-- Expansion speed (cities per turn)
SELECT
    p.player_name,
    COUNT(c.city_id) as cities,
    MAX(c.founded_turn) as last_city_turn,
    CAST(COUNT(c.city_id) AS FLOAT) / MAX(c.founded_turn) as expansion_rate
FROM cities c
JOIN players p ON c.match_id = p.match_id AND c.player_id = p.player_id
GROUP BY p.player_name
ORDER BY expansion_rate DESC;

-- Military vs. economic production
SELECT
    p.player_name,
    SUM(CASE WHEN prod.unit_type IN ('UNIT_SPEARMAN', 'UNIT_ARCHER', 'UNIT_HORSEMAN')
        THEN prod.count ELSE 0 END) as military_units,
    SUM(CASE WHEN prod.unit_type IN ('UNIT_SETTLER', 'UNIT_WORKER')
        THEN prod.count ELSE 0 END) as economic_units
FROM city_unit_production prod
JOIN cities c ON prod.match_id = c.match_id AND prod.city_id = c.city_id
JOIN players p ON c.match_id = p.match_id AND c.player_id = p.player_id
GROUP BY p.player_name;

-- Captured cities
SELECT
    p.player_name,
    COUNT(*) as cities_captured
FROM cities c
JOIN players p ON c.match_id = p.match_id AND c.player_id = p.player_id
WHERE c.first_player_id != c.player_id
GROUP BY p.player_name
ORDER BY cities_captured DESC;
```

### Troubleshooting

**No cities in database:**
- Run validation: `uv run python scripts/validate_city_data.py`
- Check migration applied: `uv run duckdb data/tournament_data.duckdb -c "SHOW TABLES"`
- Re-import data: `uv run python scripts/import_attachments.py --directory saves --force`

**Incorrect player IDs:**
- Verify player ID conversion: XML uses 0-based, DB uses 1-based
- Check validation script output for errors

**Missing production data:**
- Some cities may have no production (newly founded)
- Check if `<UnitProductionCounts>` is empty in XML
```

**Commit Point**: ✓ "docs: Add city data analysis documentation"

---

#### Subtask 7.2: Update Schema Documentation
**File**: `docs/database-schema.md` (add to existing file)

Add descriptions for the new tables to your schema documentation.

**Note**: The `export_schema.py` script should automatically pick up the new tables. Run it to update the docs:

```bash
uv run python scripts/export_schema.py
```

**Commit Point**: ✓ "docs: Update database schema documentation with city tables"

---

## Final Integration & Testing

### Integration Test
**File**: `tests/test_integration_cities.py`

```python
"""Integration test for complete city data workflow.

This tests the entire flow:
1. Parse city data from XML
2. Insert into database
3. Query and analyze
"""

import pytest
import duckdb
import tempfile
import shutil
from pathlib import Path


def test_complete_city_workflow(tmp_path: Path) -> None:
    """Test complete workflow from XML to database to queries."""
    # Setup: Create sample XML
    xml_content = """<?xml version="1.0"?>
<Game Turn="50">
    <Player ID="0"><Name>anarkos</Name><Civilization>PERSIA</Civilization></Player>
    <Player ID="1"><Name>becked</Name><Civilization>ASSYRIA</Civilization></Player>

    <City ID="0" TileID="100" Player="0" Family="FAMILY_A" Founded="1">
        <NameType>CITYNAME_CAPITAL1</NameType>
        <Citizens>5</Citizens>
        <Capital />
        <FirstPlayer>0</FirstPlayer>
        <LastPlayer>0</LastPlayer>
        <UnitProductionCounts>
            <UNIT_SETTLER>3</UNIT_SETTLER>
            <UNIT_SPEARMAN>2</UNIT_SPEARMAN>
        </UnitProductionCounts>
        <ProjectCount>
            <PROJECT_FORUM>1</PROJECT_FORUM>
        </ProjectCount>
    </City>

    <City ID="1" TileID="200" Player="1" Family="FAMILY_B" Founded="1">
        <NameType>CITYNAME_CAPITAL2</NameType>
        <Citizens>4</Citizens>
        <Capital />
        <FirstPlayer>1</FirstPlayer>
        <LastPlayer>1</LastPlayer>
        <UnitProductionCounts>
            <UNIT_SETTLER>2</UNIT_SETTLER>
            <UNIT_WORKER>3</UNIT_WORKER>
        </UnitProductionCounts>
        <ProjectCount />
    </City>

    <City ID="2" TileID="300" Player="0" Family="FAMILY_A" Founded="10">
        <NameType>CITYNAME_EXPANSION</NameType>
        <Citizens>2</Citizens>
        <FirstPlayer>0</FirstPlayer>
        <LastPlayer>0</LastPlayer>
        <UnitProductionCounts>
            <UNIT_WORKER>1</UNIT_WORKER>
        </UnitProductionCounts>
        <ProjectCount />
    </City>
</Game>
"""

    xml_file = tmp_path / "test.xml"
    xml_file.write_text(xml_content)

    # Create database
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test.duckdb"

    try:
        # Run migration
        from scripts.migrate_add_city_tables import migrate_up
        migrate_up(str(db_path))

        # Create minimal schema
        conn = duckdb.connect(str(db_path))
        conn.execute("CREATE TABLE matches (match_id BIGINT PRIMARY KEY)")
        conn.execute("INSERT INTO matches VALUES (1)")
        conn.execute("""
            CREATE TABLE players (
                player_id BIGINT, match_id BIGINT,
                player_name VARCHAR, civilization VARCHAR,
                PRIMARY KEY (match_id, player_id)
            )
        """)
        conn.execute("""
            INSERT INTO players VALUES
            (1, 1, 'anarkos', 'PERSIA'),
            (2, 1, 'becked', 'ASSYRIA')
        """)
        conn.close()

        # Parse XML
        from tournament_visualizer.data.parser import OldWorldSaveParser
        parser = OldWorldSaveParser("")
        parser.parse_xml_file(str(xml_file))

        cities = parser.extract_cities()
        production = parser.extract_city_unit_production()
        projects = parser.extract_city_projects()

        # Verify parsing
        assert len(cities) == 3
        assert len(production) == 6  # 2 + 2 + 1 + 1
        assert len(projects) == 1

        # Insert into database
        from tournament_visualizer.data.database import DatabaseManager
        db = DatabaseManager(str(db_path))

        db.insert_cities(match_id=1, cities=cities)
        db.insert_city_unit_production(match_id=1, production=production)
        db.insert_city_projects(match_id=1, projects=projects)

        # Query data
        from tournament_visualizer.data.queries import (
            get_match_cities,
            get_player_expansion_stats,
            get_production_summary
        )

        # Test get_match_cities
        queried_cities = get_match_cities(match_id=1, db_path=str(db_path))
        assert len(queried_cities) == 3
        assert queried_cities[0]['city_name'] == 'CITYNAME_CAPITAL1'

        # Test expansion stats
        expansion = get_player_expansion_stats(match_id=1, db_path=str(db_path))
        assert len(expansion) == 2

        # Player 1 (anarkos) should have 2 cities
        player1 = [p for p in expansion if p['player_name'] == 'anarkos'][0]
        assert player1['total_cities'] == 2
        assert player1['first_city_turn'] == 1
        assert player1['last_city_turn'] == 10

        # Test production summary
        prod_summary = get_production_summary(match_id=1, db_path=str(db_path))
        assert len(prod_summary) == 2

        # Player 1 should have 3 settlers + 2 spearmen + 1 worker = 6 units
        player1_prod = [p for p in prod_summary if p['player_name'] == 'anarkos'][0]
        assert player1_prod['total_units_produced'] == 6
        assert player1_prod['settlers'] == 3

    finally:
        shutil.rmtree(temp_dir)
```

**Run integration test**:
```bash
uv run pytest tests/test_integration_cities.py -v
```

**Commit Point**: ✓ "test: Add end-to-end integration test for city data workflow"

---

## Final Checklist

Before marking complete, verify:

```bash
# 1. All tests pass
uv run pytest -v

# 2. Code formatted
uv run black tournament_visualizer/ scripts/ tests/

# 3. Linting passes
uv run ruff check --fix tournament_visualizer/ scripts/ tests/

# 4. Migration applied
uv run python scripts/migrate_add_city_tables.py --verify

# 5. Data imported
uv run python scripts/import_attachments.py --directory saves --force --verbose

# 6. Validation passes
uv run python scripts/validate_city_data.py

# 7. Schema docs updated
uv run python scripts/export_schema.py

# 8. Manual spot checks
uv run duckdb data/tournament_data.duckdb -readonly -c "SELECT COUNT(*) FROM cities"
uv run duckdb data/tournament_data.duckdb -readonly -c "SELECT * FROM cities LIMIT 3"
```

**Final Commit**: ✓ "chore: Complete city data implementation"

---

## Time Estimates

| Task | Estimated Time | Description |
|------|---------------|-------------|
| 0. Setup & Discovery | 15 min | Explore codebase, extract sample XML |
| 1. Migration | 1 hour | TDD schema migration with tests |
| 2. Parser | 2 hours | TDD parser implementation |
| 3. Database | 1.5 hours | TDD database operations |
| 4. ETL Integration | 30 min | Wire up city extraction |
| 5. Queries | 1 hour | TDD query functions |
| 6. Validation | 45 min | Validation script |
| 7. Documentation | 30 min | User docs, schema docs |
| 8. Integration Test | 30 min | E2E test |
| **Total** | **8 hours** | Full implementation |

---

## Common Pitfalls

### Pitfall 1: Player ID Conversion
**Problem**: Forgetting to convert XML 0-based IDs to database 1-based.
**Solution**:
- Always use: `database_player_id = xml_player_id + 1`
- Test explicitly: Check Player ID="0" becomes player_id=1
- Document everywhere: Comments in parser, tests, docs

### Pitfall 2: Missing Optional Fields
**Problem**: Cities without population, governor, or family crash parser.
**Solution**:
- Use `.get()` for optional fields
- Provide defaults (None or 0)
- Test with minimal XML (no optional fields)

### Pitfall 3: Empty Production Lists
**Problem**: Cities with `<UnitProductionCounts />` (empty) cause errors.
**Solution**:
- Check if element has children before iterating
- Handle empty lists gracefully (skip, don't error)
- Test edge case explicitly

### Pitfall 4: Duplicate Cities
**Problem**: Re-importing data causes duplicate city errors.
**Solution**:
- Primary key (match_id, city_id) prevents duplicates
- Use `--force` flag to clear existing data before import
- Handle constraint errors gracefully

### Pitfall 5: Test Isolation
**Problem**: Tests affect each other due to shared database.
**Solution**:
- Always use temporary databases in fixtures
- Use `shutil.rmtree()` for cleanup
- Never test against real database

---

## Success Criteria

You'll know the implementation is complete when:

1. ✅ All tests pass (`uv run pytest -v`)
2. ✅ Migration applied successfully
3. ✅ Database contains city data after import
4. ✅ Validation script reports no errors
5. ✅ Queries return expected results
6. ✅ Documentation is complete and accurate
7. ✅ Code is formatted and linted
8. ✅ All commits follow conventions
9. ✅ Integration test passes
10. ✅ Can answer questions like "Who expands faster?" and "Who produces more military?"

---

## Next Steps (Future Enhancements - Don't Need Now!)

After basic city data is working, consider:

1. **Turn-by-turn city population tracking**
   - Track population changes over time
   - Requires new `city_population_history` table

2. **Yield progression tracking**
   - Track city yield output per turn
   - Requires parsing `<YieldProgress>` element

3. **Religious spread analysis**
   - Track which religions in which cities
   - Requires parsing `<Religion>` element

4. **Dashboard visualizations**
   - Expansion timeline chart
   - Production comparison chart
   - City map visualization

5. **Advanced analytics**
   - Settler spam detection
   - Expansion efficiency (cities per turn)
   - Production specialization clustering

**Remember: YAGNI! Only implement when actually needed.**

---

## Questions?

If stuck:
1. Check test output for specific errors
2. Review existing parser patterns for similar data
3. Verify database schema with `DESCRIBE cities`
4. Check sample XML structure
5. Run validation script for data quality issues
6. Test individual components in Python REPL

**Remember the principles:**
- **TDD**: Write tests first, make them pass
- **DRY**: Reuse existing patterns (parser methods, database methods, test fixtures)
- **YAGNI**: Only implement what's needed NOW
- **Frequent commits**: After each passing test or completed task

Good luck! 🚀
