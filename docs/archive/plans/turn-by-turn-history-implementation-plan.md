# Turn-by-Turn History Implementation Plan

> **Status**: Completed and archived (2025-10-25)
>
> Turn-by-turn history feature is now documented in CLAUDE.md (Yield Value Display Scale section).
> See migrations/002_add_history_tables.md for schema changes.

**Date:** October 8, 2025
**Status:** Ready for Implementation
**Estimated Time:** 12-15 hours
**Related Issue:** [docs/issues/missing-turn-by-turn-history.md](../issues/missing-turn-by-turn-history.md)

---

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Architecture Overview](#architecture-overview)
- [Implementation Tasks](#implementation-tasks)
  - [Phase 1: Setup & Understanding](#phase-1-setup--understanding)
  - [Phase 2: Schema Design & Migration](#phase-2-schema-design--migration)
  - [Phase 3: Parser Implementation (TDD)](#phase-3-parser-implementation-tdd)
  - [Phase 4: Database Integration](#phase-4-database-integration)
  - [Phase 5: Migration & Data Import](#phase-5-migration--data-import)
  - [Phase 6: Validation & Documentation](#phase-6-validation--documentation)
- [Testing Strategy](#testing-strategy)
- [Rollback Procedure](#rollback-procedure)

---

## Overview

### The Problem
The DuckDB database currently only captures final state data from Old World save files. Critical turn-by-turn historical data exists in the XML but is not being extracted. This prevents analytics like:
- Victory point progression curves
- Economic growth analysis over time
- Military buildup patterns
- Internal politics tracking (family/religion opinions)

### The Solution
Implement extraction and storage of turn-by-turn historical data from XML elements like:
- `PointsHistory` - Victory points per turn
- `YieldRateHistory` - Resource production per turn
- `MilitaryPowerHistory` - Military strength per turn
- `LegitimacyHistory` - Governance stability per turn
- `FamilyOpinionHistory` - Family relations per turn
- `ReligionOpinionHistory` - Religious relations per turn

### What You'll Be Doing
1. Drop a broken table (`game_state`)
2. Repurpose an empty table (`resources` → `player_yield_history`)
3. Add 5 new history tables
4. Write parser methods to extract XML history data
5. Update database ingestion logic
6. Create and run migration script
7. Re-import all tournament data
8. Write comprehensive tests for everything

---

## Prerequisites

### Required Knowledge
- **Python**: Type annotations, list comprehensions, dictionaries
- **XML**: XPath basics, lxml library
- **SQL**: CREATE TABLE, ALTER TABLE, INSERT, foreign keys
- **Testing**: pytest basics (we'll teach you the patterns)
- **Git**: Committing changes frequently

### Domain Concepts You Need to Know

#### Old World Save File Structure
- Save files are `.zip` archives containing a single `.xml` file
- The XML has a root element with match metadata
- Inside are `<Player>` elements with turn-by-turn data

#### Turn-by-Turn History XML Format
Historical data uses this pattern:
```xml
<PointsHistory>
  <T2>1</T2>      <!-- Turn 2: 1 point -->
  <T3>1</T3>      <!-- Turn 3: 1 point -->
  <T4>3</T4>      <!-- Turn 4: 3 points -->
  ...
  <T69>157</T69>  <!-- Turn 69: 157 points -->
</PointsHistory>
```

**Key Points:**
- Each `<TN>` tag is a turn number (T2 = turn 2, T69 = turn 69)
- The text content is the value for that turn
- Games typically run 60-80 turns
- Both players have their own history sections

#### Player ID Mapping (CRITICAL!)
**XML uses 0-based player IDs, database uses 1-based:**
```python
# XML has <Player ID="0"> and <Player ID="1">
# Database uses player_id=1 and player_id=2
database_player_id = int(xml_player_id) + 1
```

**Why?** Database convention - auto-increment primary keys start at 1.

#### YieldRateHistory Special Case
Unlike other histories (single value per turn), yields have multiple types per turn:
```xml
<YieldRateHistory>
  <YIELD_GROWTH>
    <T2>100</T2>
    <T3>100</T3>
    ...
  </YIELD_GROWTH>
  <YIELD_CIVICS>
    <T2>190</T2>
    <T3>195</T3>
    ...
  </YIELD_CIVICS>
  <YIELD_TRAINING>...</YIELD_TRAINING>
  <YIELD_SCIENCE>...</YIELD_SCIENCE>
</YieldRateHistory>
```

**Storage:** One row per (player, turn, yield_type) combination.

### Tools You'll Use
- **uv**: Python package manager (like npm for Python)
- **DuckDB**: Analytics database (like SQLite but faster for analytics)
- **pytest**: Testing framework
- **lxml**: XML parsing library

### File Structure You'll Touch
```
tournament_visualizer/
├── parser/
│   ├── parser.py           # Main XML parser - YOU'LL MODIFY THIS
│   └── utils.py            # Helper functions
├── data/
│   └── database.py         # Database schema AND operations - YOU'LL MODIFY THIS
tests/
├── test_parser.py          # Parser tests - YOU'LL ADD TESTS HERE
├── test_database.py        # Database tests - YOU'LL ADD TESTS HERE
└── fixtures/               # Test data
scripts/
├── import_tournaments.py   # Data import script
└── migrations/             # YOU'LL CREATE NEW MIGRATION HERE
docs/
├── plans/                  # This file is here
└── migrations/             # YOU'LL DOCUMENT MIGRATION HERE
```

---

## Architecture Overview

### Data Flow
```
Old World Save File (.zip)
    ↓
  Extract XML
    ↓
  Parse with lxml (parser.py)
    ↓
  Extract history data (new methods)
    ↓
  Insert into DuckDB (database.py)
    ↓
  Query for analytics (Dash app)
```

### Existing Parser Pattern (You'll Follow This)
The parser already extracts data using this pattern:

**File:** `tournament_visualizer/parser/parser.py`
```python
class OldWorldSaveParser:
    def extract_something(self) -> List[Dict[str, Any]]:
        """Extract something from XML."""
        if self.root is None:
            raise ValueError("XML not parsed. Call extract_and_parse() first.")

        results = []

        # Find player elements (only human players have OnlineID)
        player_elements = self.root.findall(".//Player[@OnlineID]")

        for player_elem in player_elements:
            # Get 0-based XML player ID
            player_xml_id = player_elem.get("ID")
            if player_xml_id is None:
                continue

            # Convert to 1-based database ID
            player_id = int(player_xml_id) + 1

            # Extract data...
            # Append to results...

        return results
```

You'll write methods following this exact pattern.

---

## Implementation Tasks

### Phase 1: Setup & Understanding

#### Task 1.1: Environment Setup & Verification
**Time:** 30 minutes
**Files:** None (just running commands)

**Objective:** Ensure your development environment works.

**Steps:**
1. **Verify Python environment:**
   ```bash
   uv run python --version  # Should be Python 3.11+
   ```

2. **Run existing tests to ensure they pass:**
   ```bash
   uv run pytest -v
   ```
   **Expected:** All tests should pass. If any fail, stop and ask for help.

3. **Check database exists:**
   ```bash
   ls -lh tournament_data.duckdb
   ```
   **Expected:** File should exist (probably 5-20 MB).

4. **Inspect current database schema:**
   ```bash
   uv run duckdb tournament_data.duckdb -readonly -c "SHOW TABLES"
   ```
   **Expected:** You should see tables like `matches`, `players`, `events`, `resources`, `game_state`.

5. **Check for empty/broken tables:**
   ```bash
   uv run duckdb tournament_data.duckdb -readonly -c "SELECT COUNT(*) FROM resources"
   uv run duckdb tournament_data.duckdb -readonly -c "SELECT COUNT(*) FROM game_state"
   ```
   **Expected:**
   - `resources`: 0 rows (empty, we'll repurpose this)
   - `game_state`: Many rows but all have `turn_number=0` (broken, we'll delete this)

**Commit:** Not needed (no code changes).

---

#### Task 1.2: Examine Real XML Data
**Time:** 30 minutes
**Files:** None (just exploration)

**Objective:** Understand the XML structure you'll be parsing.

**Steps:**
1. **List available save files:**
   ```bash
   ls -lh saves/*.zip
   ```

2. **Extract and view a sample save file:**
   ```bash
   # Pick any save file, e.g., the first one alphabetically
   SAMPLE_FILE=$(ls saves/*.zip | head -n 1)
   echo "Examining: $SAMPLE_FILE"

   # Extract and view first 2000 lines
   unzip -p "$SAMPLE_FILE" | head -n 2000 > /tmp/sample_save.xml
   ```

3. **Open `/tmp/sample_save.xml` in a text editor and find these sections:**
   - Search for `<Player ID="0"` - this is the first player
   - Inside that player, find `<PointsHistory>` - note the T2, T3, T4 pattern
   - Find `<YieldRateHistory>` - note the nested structure (YIELD_GROWTH, YIELD_CIVICS, etc.)
   - Find `<MilitaryPowerHistory>` - same TN pattern
   - Find `<LegitimacyHistory>` - same TN pattern
   - Find `<FamilyOpinionHistory>` - note it has family names as tags (FAMILY_ACHAEMENID, etc.)
   - Find `<ReligionOpinionHistory>` - note religion names as tags

4. **Count how many turns this game had:**
   ```bash
   # Last turn is usually T65-T75
   grep -o '<T[0-9]*>' /tmp/sample_save.xml | sort -u | tail -n 5
   ```
   **Note:** This shows you the range of turns (e.g., T65, T66, T67, T68, T69).

**Understanding Check:**
- Do you see the `<TN>value</TN>` pattern clearly?
- Can you see how YieldRateHistory is different (nested by yield type)?
- Can you identify both Player ID="0" and Player ID="1" sections?

**Commit:** Not needed (no code changes).

---

### Phase 2: Schema Design & Migration

#### Task 2.1: Add Schema Definitions to Database Class
**Time:** 1 hour
**Files:** `tournament_visualizer/data/database.py`

**Objective:** Add new table creation methods following the existing pattern.

**Background:** This project keeps all schema definitions in `database.py` inside the `TournamentDatabase` class. Each table has a `_create_TABLENAME_table()` method.

**Steps:**

1. **Read the existing pattern:**
   ```bash
   # Look at how existing tables are created
   grep -A 20 "_create_events_table" tournament_visualizer/data/database.py
   ```
   **Notice:** Each method creates a table with `CREATE TABLE IF NOT EXISTS`, adds indexes, and executes via `self.get_connection()`.

2. **Add sequences for new tables** to `_create_sequences()` method:

   Find the `_create_sequences()` method (around line 154) and add:
   ```python
   def _create_sequences(self) -> None:
       """Create sequences for auto-increment primary keys."""
       sequences = [
           "CREATE SEQUENCE IF NOT EXISTS matches_id_seq START 1;",
           "CREATE SEQUENCE IF NOT EXISTS players_id_seq START 1;",
           "CREATE SEQUENCE IF NOT EXISTS game_state_id_seq START 1;",
           "CREATE SEQUENCE IF NOT EXISTS territories_id_seq START 1;",
           "CREATE SEQUENCE IF NOT EXISTS events_id_seq START 1;",
           "CREATE SEQUENCE IF NOT EXISTS resources_id_seq START 1;",
           "CREATE SEQUENCE IF NOT EXISTS technology_progress_id_seq START 1;",
           "CREATE SEQUENCE IF NOT EXISTS player_statistics_id_seq START 1;",
           "CREATE SEQUENCE IF NOT EXISTS units_produced_id_seq START 1;",
           # NEW: Add these sequences
           "CREATE SEQUENCE IF NOT EXISTS points_history_id_seq START 1;",
           "CREATE SEQUENCE IF NOT EXISTS military_history_id_seq START 1;",
           "CREATE SEQUENCE IF NOT EXISTS legitimacy_history_id_seq START 1;",
           "CREATE SEQUENCE IF NOT EXISTS family_opinion_id_seq START 1;",
           "CREATE SEQUENCE IF NOT EXISTS religion_opinion_id_seq START 1;",
       ]
       # ... rest of method
   ```

3. **Add new table creation methods** after existing ones (around line 430, after `_create_units_produced_table()`):

   ```python
   def _create_player_points_history_table(self) -> None:
       """Create the player_points_history table."""
       query = """
       CREATE TABLE IF NOT EXISTS player_points_history (
           points_history_id BIGINT PRIMARY KEY,
           match_id BIGINT NOT NULL REFERENCES matches(match_id),
           player_id BIGINT NOT NULL REFERENCES players(player_id),
           turn_number INTEGER NOT NULL,
           points INTEGER NOT NULL,

           CONSTRAINT check_turn_number CHECK(turn_number >= 0),
           CONSTRAINT check_points CHECK(points >= 0),
           CONSTRAINT unique_points_turn UNIQUE(match_id, player_id, turn_number)
       );

       CREATE INDEX IF NOT EXISTS idx_points_history_match_player
       ON player_points_history(match_id, player_id);

       CREATE INDEX IF NOT EXISTS idx_points_history_turn
       ON player_points_history(turn_number);
       """
       with self.get_connection() as conn:
           conn.execute(query)

   def _create_player_military_history_table(self) -> None:
       """Create the player_military_history table."""
       query = """
       CREATE TABLE IF NOT EXISTS player_military_history (
           military_history_id BIGINT PRIMARY KEY,
           match_id BIGINT NOT NULL REFERENCES matches(match_id),
           player_id BIGINT NOT NULL REFERENCES players(player_id),
           turn_number INTEGER NOT NULL,
           military_power INTEGER NOT NULL,

           CONSTRAINT check_turn_number CHECK(turn_number >= 0),
           CONSTRAINT check_military_power CHECK(military_power >= 0),
           CONSTRAINT unique_military_turn UNIQUE(match_id, player_id, turn_number)
       );

       CREATE INDEX IF NOT EXISTS idx_military_history_match_player
       ON player_military_history(match_id, player_id);

       CREATE INDEX IF NOT EXISTS idx_military_history_turn
       ON player_military_history(turn_number);
       """
       with self.get_connection() as conn:
           conn.execute(query)

   def _create_player_legitimacy_history_table(self) -> None:
       """Create the player_legitimacy_history table."""
       query = """
       CREATE TABLE IF NOT EXISTS player_legitimacy_history (
           legitimacy_history_id BIGINT PRIMARY KEY,
           match_id BIGINT NOT NULL REFERENCES matches(match_id),
           player_id BIGINT NOT NULL REFERENCES players(player_id),
           turn_number INTEGER NOT NULL,
           legitimacy INTEGER NOT NULL,

           CONSTRAINT check_turn_number CHECK(turn_number >= 0),
           CONSTRAINT check_legitimacy CHECK(legitimacy >= 0 AND legitimacy <= 100),
           CONSTRAINT unique_legitimacy_turn UNIQUE(match_id, player_id, turn_number)
       );

       CREATE INDEX IF NOT EXISTS idx_legitimacy_history_match_player
       ON player_legitimacy_history(match_id, player_id);

       CREATE INDEX IF NOT EXISTS idx_legitimacy_history_turn
       ON player_legitimacy_history(turn_number);
       """
       with self.get_connection() as conn:
           conn.execute(query)

   def _create_family_opinion_history_table(self) -> None:
       """Create the family_opinion_history table."""
       query = """
       CREATE TABLE IF NOT EXISTS family_opinion_history (
           family_opinion_id BIGINT PRIMARY KEY,
           match_id BIGINT NOT NULL REFERENCES matches(match_id),
           player_id BIGINT NOT NULL REFERENCES players(player_id),
           turn_number INTEGER NOT NULL,
           family_name VARCHAR NOT NULL,
           opinion INTEGER NOT NULL,

           CONSTRAINT check_turn_number CHECK(turn_number >= 0),
           CONSTRAINT check_opinion CHECK(opinion >= 0 AND opinion <= 100),
           CONSTRAINT unique_family_opinion_turn UNIQUE(match_id, player_id, turn_number, family_name)
       );

       CREATE INDEX IF NOT EXISTS idx_family_opinion_match_player
       ON family_opinion_history(match_id, player_id);

       CREATE INDEX IF NOT EXISTS idx_family_opinion_family
       ON family_opinion_history(family_name);
       """
       with self.get_connection() as conn:
           conn.execute(query)

   def _create_religion_opinion_history_table(self) -> None:
       """Create the religion_opinion_history table."""
       query = """
       CREATE TABLE IF NOT EXISTS religion_opinion_history (
           religion_opinion_id BIGINT PRIMARY KEY,
           match_id BIGINT NOT NULL REFERENCES matches(match_id),
           player_id BIGINT NOT NULL REFERENCES players(player_id),
           turn_number INTEGER NOT NULL,
           religion_name VARCHAR NOT NULL,
           opinion INTEGER NOT NULL,

           CONSTRAINT check_turn_number CHECK(turn_number >= 0),
           CONSTRAINT check_opinion CHECK(opinion >= 0 AND opinion <= 100),
           CONSTRAINT unique_religion_opinion_turn UNIQUE(match_id, player_id, turn_number, religion_name)
       );

       CREATE INDEX IF NOT EXISTS idx_religion_opinion_match_player
       ON religion_opinion_history(match_id, player_id);

       CREATE INDEX IF NOT EXISTS idx_religion_opinion_religion
       ON religion_opinion_history(religion_name);
       """
       with self.get_connection() as conn:
           conn.execute(query)
   ```

4. **Call new methods from `create_schema()`**:

   Find the `create_schema()` method (around line 123) and add calls to new methods:
   ```python
   def create_schema(self) -> None:
       """Create the complete database schema."""
       logger.info("Creating database schema...")

       # Create sequences for auto-increment
       self._create_sequences()

       # Create tables in dependency order
       self._create_matches_table()
       self._create_players_table()
       self._create_match_winners_table()
       self._create_match_metadata_table()
       self._create_game_state_table()
       self._create_territories_table()
       self._create_events_table()
       self._create_resources_table()
       self._create_technology_progress_table()
       self._create_player_statistics_table()
       self._create_units_produced_table()
       self._create_unit_classifications_table()
       # NEW: Add these calls
       self._create_player_points_history_table()
       self._create_player_military_history_table()
       self._create_player_legitimacy_history_table()
       self._create_family_opinion_history_table()
       self._create_religion_opinion_history_table()
       # END NEW
       self._create_schema_migrations_table()
       self._create_views()
       # ... rest of method
   ```

5. **Understanding the schema:**
   - **Primary Keys:** Each table has a unique ID (e.g., `points_history_id`)
   - **Foreign Keys:** `REFERENCES matches(match_id)` ensures referential integrity
   - **UNIQUE Constraints:** Prevent duplicate entries (e.g., can't have two point values for same player/turn)
   - **CHECK Constraints:** Validate data (e.g., legitimacy must be 0-100)
   - **Indexes:** Speed up common queries (by match/player, by turn)
   - **Sequences:** DuckDB uses sequences for auto-incrementing IDs

**Testing:**
Not applicable yet - these methods will be tested when migration runs.

**Commit:**
```bash
git add tournament_visualizer/data/database.py
git commit -m "feat: Add table creation methods for turn-by-turn history

- Add 5 new sequences for history tables
- Create _create_player_points_history_table()
- Create _create_player_military_history_table()
- Create _create_player_legitimacy_history_table()
- Create _create_family_opinion_history_table()
- Create _create_religion_opinion_history_table()
- Add calls to create_schema() method"
```

---

#### Task 2.2: Create Migration Script
**Time:** 1 hour
**Files:**
- `scripts/migrations/002_add_history_tables.py` (new)
- `docs/migrations/002_add_history_tables.md` (new)

**Objective:** Create a script that migrates the existing database to the new schema.

**Steps:**

1. **Check if migration infrastructure exists:**
   ```bash
   ls -la scripts/migrations/
   ```

   If the directory doesn't exist, create it:
   ```bash
   mkdir -p scripts/migrations
   ```

2. **Create migration script:**

   **File:** `scripts/migrations/002_add_history_tables.py`
   ```python
   """Migration 002: Add turn-by-turn history tables.

   This migration:
   1. Drops the broken game_state table (all rows have turn_number=0)
   2. Renames resources table to player_yield_history
   3. Creates new history tables for points, military, legitimacy, opinions

   Rollback: See docs/migrations/002_add_history_tables.md
   """

   import duckdb
   from pathlib import Path
   from typing import Optional


   def migrate(db_path: Path, backup: bool = True) -> None:
       """Run migration to add history tables.

       Args:
           db_path: Path to the DuckDB database file
           backup: If True, create a backup before migrating
       """
       if backup:
           backup_path = db_path.with_suffix(f".duckdb.backup_002")
           print(f"Creating backup: {backup_path}")
           import shutil
           shutil.copy2(db_path, backup_path)

       print(f"Migrating database: {db_path}")
       conn = duckdb.connect(str(db_path))

       try:
           # 1. Drop broken game_state table
           print("  - Dropping game_state table...")
           conn.execute("DROP TABLE IF EXISTS game_state")

           # 2. Rename resources to player_yield_history
           print("  - Renaming resources to player_yield_history...")
           # Check if table exists and is empty before renaming
           count = conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
           if count > 0:
               print(f"    WARNING: resources table has {count} rows! Skipping rename.")
           else:
               conn.execute("ALTER TABLE resources RENAME TO player_yield_history")

           # 3. Create player_points_history table
           print("  - Creating player_points_history table...")
           conn.execute("""
               CREATE TABLE IF NOT EXISTS player_points_history (
                   points_history_id BIGINT PRIMARY KEY,
                   match_id BIGINT NOT NULL,
                   player_id BIGINT NOT NULL,
                   turn_number INTEGER NOT NULL,
                   points INTEGER NOT NULL,
                   FOREIGN KEY (match_id) REFERENCES matches(match_id),
                   FOREIGN KEY (player_id) REFERENCES players(player_id),
                   CHECK (turn_number >= 0),
                   CHECK (points >= 0),
                   UNIQUE (match_id, player_id, turn_number)
               )
           """)
           conn.execute("""
               CREATE INDEX idx_points_history_match_player
               ON player_points_history(match_id, player_id)
           """)
           conn.execute("""
               CREATE INDEX idx_points_history_turn
               ON player_points_history(turn_number)
           """)

           # 4. Create player_military_history table
           print("  - Creating player_military_history table...")
           conn.execute("""
               CREATE TABLE IF NOT EXISTS player_military_history (
                   military_history_id BIGINT PRIMARY KEY,
                   match_id BIGINT NOT NULL,
                   player_id BIGINT NOT NULL,
                   turn_number INTEGER NOT NULL,
                   military_power INTEGER NOT NULL,
                   FOREIGN KEY (match_id) REFERENCES matches(match_id),
                   FOREIGN KEY (player_id) REFERENCES players(player_id),
                   CHECK (turn_number >= 0),
                   CHECK (military_power >= 0),
                   UNIQUE (match_id, player_id, turn_number)
               )
           """)
           conn.execute("""
               CREATE INDEX idx_military_history_match_player
               ON player_military_history(match_id, player_id)
           """)
           conn.execute("""
               CREATE INDEX idx_military_history_turn
               ON player_military_history(turn_number)
           """)

           # 5. Create player_legitimacy_history table
           print("  - Creating player_legitimacy_history table...")
           conn.execute("""
               CREATE TABLE IF NOT EXISTS player_legitimacy_history (
                   legitimacy_history_id BIGINT PRIMARY KEY,
                   match_id BIGINT NOT NULL,
                   player_id BIGINT NOT NULL,
                   turn_number INTEGER NOT NULL,
                   legitimacy INTEGER NOT NULL,
                   FOREIGN KEY (match_id) REFERENCES matches(match_id),
                   FOREIGN KEY (player_id) REFERENCES players(player_id),
                   CHECK (turn_number >= 0),
                   CHECK (legitimacy >= 0 AND legitimacy <= 100),
                   UNIQUE (match_id, player_id, turn_number)
               )
           """)
           conn.execute("""
               CREATE INDEX idx_legitimacy_history_match_player
               ON player_legitimacy_history(match_id, player_id)
           """)
           conn.execute("""
               CREATE INDEX idx_legitimacy_history_turn
               ON player_legitimacy_history(turn_number)
           """)

           # 6. Create family_opinion_history table
           print("  - Creating family_opinion_history table...")
           conn.execute("""
               CREATE TABLE IF NOT EXISTS family_opinion_history (
                   family_opinion_id BIGINT PRIMARY KEY,
                   match_id BIGINT NOT NULL,
                   player_id BIGINT NOT NULL,
                   turn_number INTEGER NOT NULL,
                   family_name VARCHAR NOT NULL,
                   opinion INTEGER NOT NULL,
                   FOREIGN KEY (match_id) REFERENCES matches(match_id),
                   FOREIGN KEY (player_id) REFERENCES players(player_id),
                   CHECK (turn_number >= 0),
                   CHECK (opinion >= 0 AND opinion <= 100),
                   UNIQUE (match_id, player_id, turn_number, family_name)
               )
           """)
           conn.execute("""
               CREATE INDEX idx_family_opinion_match_player
               ON family_opinion_history(match_id, player_id)
           """)
           conn.execute("""
               CREATE INDEX idx_family_opinion_family
               ON family_opinion_history(family_name)
           """)

           # 7. Create religion_opinion_history table
           print("  - Creating religion_opinion_history table...")
           conn.execute("""
               CREATE TABLE IF NOT EXISTS religion_opinion_history (
                   religion_opinion_id BIGINT PRIMARY KEY,
                   match_id BIGINT NOT NULL,
                   player_id BIGINT NOT NULL,
                   turn_number INTEGER NOT NULL,
                   religion_name VARCHAR NOT NULL,
                   opinion INTEGER NOT NULL,
                   FOREIGN KEY (match_id) REFERENCES matches(match_id),
                   FOREIGN KEY (player_id) REFERENCES players(player_id),
                   CHECK (turn_number >= 0),
                   CHECK (opinion >= 0 AND opinion <= 100),
                   UNIQUE (match_id, player_id, turn_number, religion_name)
               )
           """)
           conn.execute("""
               CREATE INDEX idx_religion_opinion_match_player
               ON religion_opinion_history(match_id, player_id)
           """)
           conn.execute("""
               CREATE INDEX idx_religion_opinion_religion
               ON religion_opinion_history(religion_name)
           """)

           conn.commit()
           print("Migration completed successfully!")

       except Exception as e:
           print(f"Migration failed: {e}")
           conn.rollback()
           raise
       finally:
           conn.close()


   def rollback(db_path: Path) -> None:
       """Rollback migration by restoring from backup.

       Args:
           db_path: Path to the DuckDB database file
       """
       backup_path = db_path.with_suffix(".duckdb.backup_002")
       if not backup_path.exists():
           raise FileNotFoundError(f"Backup not found: {backup_path}")

       print(f"Rolling back by restoring from: {backup_path}")
       import shutil
       shutil.copy2(backup_path, db_path)
       print("Rollback completed!")


   if __name__ == "__main__":
       import sys

       db_path = Path("tournament_data.duckdb")

       if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
           rollback(db_path)
       else:
           migrate(db_path, backup=True)
   ```

3. **Create migration documentation:**

   **File:** `docs/migrations/002_add_history_tables.md`
   ```markdown
   # Migration 002: Add Turn-by-Turn History Tables

   **Date:** October 8, 2025
   **Status:** Ready to Apply

   ## Overview

   This migration adds support for turn-by-turn historical data from Old World save files.

   ### Changes

   1. **Drops:** `game_state` table (broken - all rows have turn_number=0)
   2. **Renames:** `resources` → `player_yield_history` (was empty, now used for YieldRateHistory)
   3. **Creates:** 5 new history tables
      - `player_points_history` - Victory points per turn
      - `player_military_history` - Military power per turn
      - `player_legitimacy_history` - Legitimacy per turn
      - `family_opinion_history` - Family opinions per turn
      - `religion_opinion_history` - Religion opinions per turn

   ## Running the Migration

   ```bash
   # Backup is created automatically
   uv run python scripts/migrations/002_add_history_tables.py
   ```

   ## Verification

   ```bash
   # Check new tables exist
   uv run duckdb tournament_data.duckdb -readonly -c "SHOW TABLES"

   # Should see:
   # - player_yield_history (renamed from resources)
   # - player_points_history (new)
   # - player_military_history (new)
   # - player_legitimacy_history (new)
   # - family_opinion_history (new)
   # - religion_opinion_history (new)

   # Should NOT see:
   # - game_state (dropped)
   # - resources (renamed)
   ```

   ## Rollback Procedure

   ```bash
   uv run python scripts/migrations/002_add_history_tables.py --rollback
   ```

   This restores the database from the automatic backup created before migration.

   ## Related Changes

   - Parser: `tournament_visualizer/parser/parser.py` - New extraction methods
   - Database: `tournament_visualizer/data/database.py` - New insertion methods
   - Schema: `tournament_visualizer/data/schema.py` - New table definitions
   - Tests: `tests/test_parser.py` - Tests for new extraction methods
   ```

**Testing:**
You'll test this in Phase 5 when you actually run it.

**Commit:**
```bash
git add scripts/migrations/002_add_history_tables.py
git add docs/migrations/002_add_history_tables.md
git commit -m "feat: Create migration script for history tables

- Drops broken game_state table
- Renames resources to player_yield_history
- Adds 5 new history tables with indexes
- Includes rollback capability"
```

---

### Phase 3: Parser Implementation (TDD)

**Note:** We'll use Test-Driven Development - write tests FIRST, then implementation.

#### Task 3.1: Setup Test Fixtures
**Time:** 30 minutes
**Files:**
- `tests/fixtures/sample_history.xml` (new)

**Objective:** Create a minimal XML fixture for testing history extraction.

**Steps:**

1. **Check existing test fixtures:**
   ```bash
   ls -la tests/fixtures/
   ```

   If directory doesn't exist:
   ```bash
   mkdir -p tests/fixtures
   ```

2. **Create a minimal test fixture:**

   **File:** `tests/fixtures/sample_history.xml`
   ```xml
   <?xml version="1.0" encoding="utf-8"?>
   <Root TurnCount="5" MapWidth="100" MapHeight="100">
       <Player ID="0" OnlineID="12345" Name="TestPlayer1" Civilization="CIVILIZATION_ROME">
           <PointsHistory>
               <T2>1</T2>
               <T3>2</T3>
               <T4>5</T4>
               <T5>8</T5>
           </PointsHistory>
           <YieldRateHistory>
               <YIELD_GROWTH>
                   <T2>100</T2>
                   <T3>120</T3>
                   <T4>150</T4>
                   <T5>180</T5>
               </YIELD_GROWTH>
               <YIELD_CIVICS>
                   <T2>50</T2>
                   <T3>55</T3>
                   <T4>60</T4>
                   <T5>65</T5>
               </YIELD_CIVICS>
           </YieldRateHistory>
           <MilitaryPowerHistory>
               <T2>0</T2>
               <T3>10</T3>
               <T4>25</T4>
               <T5>40</T5>
           </MilitaryPowerHistory>
           <LegitimacyHistory>
               <T2>100</T2>
               <T3>100</T3>
               <T4>95</T4>
               <T5>90</T5>
           </LegitimacyHistory>
           <FamilyOpinionHistory>
               <FAMILY_JULII>
                   <T2>100</T2>
                   <T3>95</T3>
                   <T4>90</T4>
                   <T5>85</T5>
               </FAMILY_JULII>
               <FAMILY_BRUTII>
                   <T2>80</T2>
                   <T3>75</T3>
                   <T4>70</T4>
                   <T5>65</T5>
               </FAMILY_BRUTII>
           </FamilyOpinionHistory>
           <ReligionOpinionHistory>
               <RELIGION_JUPITER>
                   <T2>100</T2>
                   <T3>100</T3>
                   <T4>95</T4>
                   <T5>95</T5>
               </RELIGION_JUPITER>
           </ReligionOpinionHistory>
       </Player>
       <Player ID="1" OnlineID="67890" Name="TestPlayer2" Civilization="CIVILIZATION_CARTHAGE">
           <PointsHistory>
               <T2>1</T2>
               <T3>3</T3>
               <T4>6</T4>
               <T5>10</T5>
           </PointsHistory>
           <YieldRateHistory>
               <YIELD_GROWTH>
                   <T2>90</T2>
                   <T3>100</T3>
                   <T4>110</T4>
                   <T5>120</T5>
               </YIELD_GROWTH>
           </YieldRateHistory>
           <MilitaryPowerHistory>
               <T2>0</T2>
               <T3>5</T3>
               <T4>15</T4>
               <T5>30</T5>
           </MilitaryPowerHistory>
           <LegitimacyHistory>
               <T2>100</T2>
               <T3>100</T3>
               <T4>100</T4>
               <T5>100</T5>
           </LegitimacyHistory>
           <FamilyOpinionHistory>
               <FAMILY_BARCIDS>
                   <T2>100</T2>
                   <T3>100</T3>
                   <T4>100</T4>
                   <T5>100</T5>
               </FAMILY_BARCIDS>
           </FamilyOpinionHistory>
           <ReligionOpinionHistory>
               <RELIGION_BAAL>
                   <T2>100</T2>
                   <T3>100</T3>
                   <T4>100</T4>
                   <T5>100</T5>
               </RELIGION_BAAL>
           </ReligionOpinionHistory>
       </Player>
   </Root>
   ```

3. **Understanding the fixture:**
   - 2 players (ID=0 and ID=1) with OnlineID (human players)
   - 4 turns of data each (T2 through T5)
   - All 6 history types present
   - Different values so we can verify correct extraction

**Commit:**
```bash
git add tests/fixtures/sample_history.xml
git commit -m "test: Add XML fixture for history extraction tests"
```

---

#### Task 3.2: Test for extract_points_history()
**Time:** 45 minutes
**Files:** `tests/test_parser.py`

**Objective:** Write a failing test, then implement the parser method.

**Steps:**

1. **Examine existing parser tests:**
   ```bash
   cat tests/test_parser.py | head -n 100
   ```

   Look for:
   - How are tests structured?
   - Is there a pytest fixture for loading the parser?
   - What assertion patterns are used?

2. **Add test for points history extraction:**

   Add this to `tests/test_parser.py`:
   ```python
   def test_extract_points_history():
       """Test extraction of victory points history."""
       # Setup: Create parser with test fixture
       from tournament_visualizer.parser.parser import OldWorldSaveParser
       from pathlib import Path

       # Note: You may need to create a mock zip file or adjust based on existing patterns
       fixture_path = Path("tests/fixtures/sample_history.xml")

       # If parser requires zip files, you'll need to adapt this
       # For now, assume we can directly parse XML for testing
       parser = OldWorldSaveParser()
       with open(fixture_path) as f:
           parser.root = parser._parse_xml_string(f.read())  # Adjust based on actual API

       # Execute: Extract points history
       points_history = parser.extract_points_history()

       # Verify: Check we got the right data
       assert len(points_history) > 0, "Should extract at least some points data"

       # Should have 2 players × 4 turns = 8 records
       assert len(points_history) == 8, f"Expected 8 records, got {len(points_history)}"

       # Check structure of first record
       first_record = points_history[0]
       assert "player_id" in first_record
       assert "turn_number" in first_record
       assert "points" in first_record

       # Verify player ID mapping (XML ID=0 → DB player_id=1)
       player_1_records = [r for r in points_history if r["player_id"] == 1]
       assert len(player_1_records) == 4, "Player 1 should have 4 turn records"

       # Verify actual values from fixture
       # Player 1 (XML ID=0), Turn 2: 1 point
       turn_2_player_1 = next(r for r in points_history
                               if r["player_id"] == 1 and r["turn_number"] == 2)
       assert turn_2_player_1["points"] == 1

       # Player 1, Turn 5: 8 points
       turn_5_player_1 = next(r for r in points_history
                               if r["player_id"] == 1 and r["turn_number"] == 5)
       assert turn_5_player_1["points"] == 8

       # Player 2 (XML ID=1 → DB player_id=2), Turn 5: 10 points
       turn_5_player_2 = next(r for r in points_history
                               if r["player_id"] == 2 and r["turn_number"] == 5)
       assert turn_5_player_2["points"] == 10
   ```

3. **Run the test (it should fail):**
   ```bash
   uv run pytest tests/test_parser.py::test_extract_points_history -v
   ```

   **Expected:** Test fails because `extract_points_history()` doesn't exist yet.

4. **Implement the parser method:**

   **File:** `tournament_visualizer/parser/parser.py`

   Add this method to the `OldWorldSaveParser` class:
   ```python
   def extract_points_history(self) -> List[Dict[str, Any]]:
       """Extract victory points progression from PointsHistory.

       Parses Player/PointsHistory elements which contain turn-by-turn
       victory point totals.

       Returns:
           List of points history dictionaries with:
           - player_id: Database player ID (1-based, converted from 0-based XML ID)
           - turn_number: Game turn number (extracted from TN tags)
           - points: Victory points for that turn

       Example XML:
           <Player ID="0" OnlineID="123">
               <PointsHistory>
                   <T2>1</T2>
                   <T3>2</T3>
                   <T4>5</T4>
               </PointsHistory>
           </Player>
       """
       if self.root is None:
           raise ValueError("XML not parsed. Call extract_and_parse() first.")

       points_data = []

       # Find all player elements with OnlineID (human players only)
       player_elements = self.root.findall(".//Player[@OnlineID]")

       for player_elem in player_elements:
           # Get player's XML ID (0-based)
           player_xml_id = player_elem.get("ID")
           if player_xml_id is None:
               continue

           # Convert to 1-based database player ID
           player_id = int(player_xml_id) + 1

           # Find PointsHistory element for this player
           points_history = player_elem.find(".//PointsHistory")
           if points_history is None:
               continue

           # Process each turn element (T2, T3, T4, ...)
           for turn_elem in points_history:
               turn_tag = turn_elem.tag  # e.g., "T2"

               # Skip if not a turn tag
               if not turn_tag.startswith('T'):
                   continue

               # Extract turn number from tag (T2 → 2)
               turn_number = self._safe_int(turn_tag[1:])
               points = self._safe_int(turn_elem.text)

               if turn_number is None or points is None:
                   continue

               points_data.append({
                   "player_id": player_id,
                   "turn_number": turn_number,
                   "points": points
               })

       return points_data
   ```

5. **Run the test again (it should pass):**
   ```bash
   uv run pytest tests/test_parser.py::test_extract_points_history -v
   ```

   **Expected:** Test passes! ✅

6. **Add edge case tests:**

   Add to `tests/test_parser.py`:
   ```python
   def test_extract_points_history_missing_history():
       """Test points extraction when PointsHistory element is missing."""
       from tournament_visualizer.parser.parser import OldWorldSaveParser

       xml_without_history = """<?xml version="1.0" encoding="utf-8"?>
       <Root>
           <Player ID="0" OnlineID="123" Name="Test">
               <!-- No PointsHistory element -->
           </Player>
       </Root>"""

       parser = OldWorldSaveParser()
       parser.root = parser._parse_xml_string(xml_without_history)

       points_history = parser.extract_points_history()

       # Should return empty list, not crash
       assert points_history == []


   def test_extract_points_history_invalid_turn_tags():
       """Test points extraction handles non-turn tags gracefully."""
       from tournament_visualizer.parser.parser import OldWorldSaveParser

       xml_with_invalid = """<?xml version="1.0" encoding="utf-8"?>
       <Root>
           <Player ID="0" OnlineID="123" Name="Test">
               <PointsHistory>
                   <T2>5</T2>
                   <InvalidTag>999</InvalidTag>  <!-- Should be skipped -->
                   <T3>10</T3>
               </PointsHistory>
           </Player>
       </Root>"""

       parser = OldWorldSaveParser()
       parser.root = parser._parse_xml_string(xml_with_invalid)

       points_history = parser.extract_points_history()

       # Should have exactly 2 records (T2 and T3), skipping InvalidTag
       assert len(points_history) == 2
       assert all(r["turn_number"] in [2, 3] for r in points_history)
   ```

7. **Run all tests:**
   ```bash
   uv run pytest tests/test_parser.py -v
   ```

**Commit:**
```bash
git add tests/test_parser.py tournament_visualizer/parser/parser.py
git commit -m "feat: Implement extract_points_history() with tests

- Extracts victory points per turn from PointsHistory XML
- Converts XML player ID (0-based) to database ID (1-based)
- Handles missing data and invalid tags gracefully
- Includes comprehensive test coverage"
```

---

#### Task 3.3: Implement extract_yield_history()
**Time:** 1 hour
**Files:** `tests/test_parser.py`, `tournament_visualizer/parser/parser.py`

**Objective:** Test and implement yield history extraction (nested structure).

**Steps:**

1. **Write the test first:**

   Add to `tests/test_parser.py`:
   ```python
   def test_extract_yield_history():
       """Test extraction of yield rate history."""
       from tournament_visualizer.parser.parser import OldWorldSaveParser
       from pathlib import Path

       fixture_path = Path("tests/fixtures/sample_history.xml")
       parser = OldWorldSaveParser()
       with open(fixture_path) as f:
           parser.root = parser._parse_xml_string(f.read())

       yield_history = parser.extract_yield_history()

       # Player 1 has 2 yield types (GROWTH, CIVICS) × 4 turns = 8 records
       # Player 2 has 1 yield type (GROWTH) × 4 turns = 4 records
       # Total: 12 records
       assert len(yield_history) == 12, f"Expected 12 records, got {len(yield_history)}"

       # Check structure
       first_record = yield_history[0]
       assert "player_id" in first_record
       assert "turn_number" in first_record
       assert "yield_type" in first_record
       assert "amount" in first_record

       # Verify specific values
       # Player 1, Turn 2, YIELD_GROWTH: 100
       player_1_t2_growth = next(r for r in yield_history
                                  if r["player_id"] == 1
                                  and r["turn_number"] == 2
                                  and r["yield_type"] == "YIELD_GROWTH")
       assert player_1_t2_growth["amount"] == 100

       # Player 1, Turn 5, YIELD_CIVICS: 65
       player_1_t5_civics = next(r for r in yield_history
                                  if r["player_id"] == 1
                                  and r["turn_number"] == 5
                                  and r["yield_type"] == "YIELD_CIVICS")
       assert player_1_t5_civics["amount"] == 65

       # Player 2, Turn 3, YIELD_GROWTH: 100
       player_2_t3_growth = next(r for r in yield_history
                                  if r["player_id"] == 2
                                  and r["turn_number"] == 3
                                  and r["yield_type"] == "YIELD_GROWTH")
       assert player_2_t3_growth["amount"] == 100
   ```

2. **Run test (should fail):**
   ```bash
   uv run pytest tests/test_parser.py::test_extract_yield_history -v
   ```

3. **Implement the method:**

   Add to `tournament_visualizer/parser/parser.py`:
   ```python
   def extract_yield_history(self) -> List[Dict[str, Any]]:
       """Extract yield production rates over time from YieldRateHistory.

       Parses Player/YieldRateHistory elements which contain turn-by-turn
       yield production rates for all yield types (GROWTH, CIVICS, TRAINING, etc.).

       Unlike other history types, yields are nested by type:
       <YieldRateHistory>
           <YIELD_GROWTH>
               <T2>100</T2>
               <T3>120</T3>
           </YIELD_GROWTH>
           <YIELD_CIVICS>
               <T2>50</T2>
               <T3>55</T3>
           </YIELD_CIVICS>
       </YieldRateHistory>

       Returns:
           List of yield history dictionaries with:
           - player_id: Database player ID (1-based)
           - turn_number: Game turn number
           - yield_type: Type of yield (YIELD_GROWTH, YIELD_CIVICS, etc.)
           - amount: Production rate for that yield on that turn
       """
       if self.root is None:
           raise ValueError("XML not parsed. Call extract_and_parse() first.")

       yield_data = []

       # Find all player elements with OnlineID (human players)
       player_elements = self.root.findall(".//Player[@OnlineID]")

       for player_elem in player_elements:
           # Get player's XML ID (0-based)
           player_xml_id = player_elem.get("ID")
           if player_xml_id is None:
               continue

           # Convert to 1-based player_id for database
           player_id = int(player_xml_id) + 1

           # Find YieldRateHistory for this player
           yield_history = player_elem.find(".//YieldRateHistory")
           if yield_history is None:
               continue

           # Process each yield type (YIELD_GROWTH, YIELD_CIVICS, etc.)
           for yield_type_elem in yield_history:
               yield_type = yield_type_elem.tag  # e.g., "YIELD_GROWTH"

               # Process each turn within this yield type (T2, T3, ...)
               for turn_elem in yield_type_elem:
                   turn_tag = turn_elem.tag  # e.g., "T2"

                   # Extract turn number from tag (T2 → 2)
                   if not turn_tag.startswith('T'):
                       continue

                   turn_number = self._safe_int(turn_tag[1:])
                   amount = self._safe_int(turn_elem.text)

                   if turn_number is None or amount is None:
                       continue

                   yield_data.append({
                       "player_id": player_id,
                       "turn_number": turn_number,
                       "yield_type": yield_type,
                       "amount": amount
                   })

       return yield_data
   ```

4. **Run test (should pass):**
   ```bash
   uv run pytest tests/test_parser.py::test_extract_yield_history -v
   ```

**Commit:**
```bash
git add tests/test_parser.py tournament_visualizer/parser/parser.py
git commit -m "feat: Implement extract_yield_history() with tests

- Handles nested yield type structure
- Extracts all yield types per turn per player
- Follows same ID mapping pattern as other extractors"
```

---

#### Task 3.4: Implement Remaining History Extractors
**Time:** 2 hours
**Files:** Same as above

**Objective:** Implement and test the remaining 3 simple extractors (military, legitimacy, opinions).

**Strategy:** These follow the same pattern as `extract_points_history()`, so we can reuse the structure.

**Steps:**

1. **Write tests for all three methods at once:**

   Add to `tests/test_parser.py`:
   ```python
   def test_extract_military_history():
       """Test extraction of military power history."""
       from tournament_visualizer.parser.parser import OldWorldSaveParser
       from pathlib import Path

       fixture_path = Path("tests/fixtures/sample_history.xml")
       parser = OldWorldSaveParser()
       with open(fixture_path) as f:
           parser.root = parser._parse_xml_string(f.read())

       military_history = parser.extract_military_history()

       # 2 players × 4 turns = 8 records
       assert len(military_history) == 8

       # Player 1, Turn 5: 40 military power
       player_1_t5 = next(r for r in military_history
                          if r["player_id"] == 1 and r["turn_number"] == 5)
       assert player_1_t5["military_power"] == 40


   def test_extract_legitimacy_history():
       """Test extraction of legitimacy history."""
       from tournament_visualizer.parser.parser import OldWorldSaveParser
       from pathlib import Path

       fixture_path = Path("tests/fixtures/sample_history.xml")
       parser = OldWorldSaveParser()
       with open(fixture_path) as f:
           parser.root = parser._parse_xml_string(f.read())

       legitimacy_history = parser.extract_legitimacy_history()

       # 2 players × 4 turns = 8 records
       assert len(legitimacy_history) == 8

       # Player 1, Turn 5: 90 legitimacy
       player_1_t5 = next(r for r in legitimacy_history
                          if r["player_id"] == 1 and r["turn_number"] == 5)
       assert player_1_t5["legitimacy"] == 90

       # Player 2 maintains 100 legitimacy
       player_2_t5 = next(r for r in legitimacy_history
                          if r["player_id"] == 2 and r["turn_number"] == 5)
       assert player_2_t5["legitimacy"] == 100


   def test_extract_opinion_histories():
       """Test extraction of family and religion opinions."""
       from tournament_visualizer.parser.parser import OldWorldSaveParser
       from pathlib import Path

       fixture_path = Path("tests/fixtures/sample_history.xml")
       parser = OldWorldSaveParser()
       with open(fixture_path) as f:
           parser.root = parser._parse_xml_string(f.read())

       opinion_histories = parser.extract_opinion_histories()

       # Should return dict with two keys
       assert "family_opinions" in opinion_histories
       assert "religion_opinions" in opinion_histories

       family_opinions = opinion_histories["family_opinions"]
       religion_opinions = opinion_histories["religion_opinions"]

       # Player 1: 2 families × 4 turns = 8 records
       # Player 2: 1 family × 4 turns = 4 records
       # Total: 12 family opinion records
       assert len(family_opinions) == 12

       # Player 1: 1 religion × 4 turns = 4 records
       # Player 2: 1 religion × 4 turns = 4 records
       # Total: 8 religion opinion records
       assert len(religion_opinions) == 8

       # Check structure
       first_family = family_opinions[0]
       assert "player_id" in first_family
       assert "turn_number" in first_family
       assert "family_name" in first_family
       assert "opinion" in first_family

       # Verify specific value
       # Player 1, Turn 5, FAMILY_JULII: 85
       player_1_julii_t5 = next(r for r in family_opinions
                                 if r["player_id"] == 1
                                 and r["turn_number"] == 5
                                 and r["family_name"] == "FAMILY_JULII")
       assert player_1_julii_t5["opinion"] == 85

       # Player 2, Turn 2, RELIGION_BAAL: 100
       player_2_baal_t2 = next(r for r in religion_opinions
                                if r["player_id"] == 2
                                and r["turn_number"] == 2
                                and r["religion_name"] == "RELIGION_BAAL")
       assert player_2_baal_t2["opinion"] == 100
   ```

2. **Run tests (should fail):**
   ```bash
   uv run pytest tests/test_parser.py::test_extract_military_history -v
   uv run pytest tests/test_parser.py::test_extract_legitimacy_history -v
   uv run pytest tests/test_parser.py::test_extract_opinion_histories -v
   ```

3. **Implement all three methods:**

   Add to `tournament_visualizer/parser/parser.py`:
   ```python
   def extract_military_history(self) -> List[Dict[str, Any]]:
       """Extract military power progression from MilitaryPowerHistory.

       Returns:
           List of military history dictionaries with:
           - player_id: Database player ID (1-based)
           - turn_number: Game turn number
           - military_power: Military strength for that turn
       """
       if self.root is None:
           raise ValueError("XML not parsed. Call extract_and_parse() first.")

       military_data = []

       player_elements = self.root.findall(".//Player[@OnlineID]")

       for player_elem in player_elements:
           player_xml_id = player_elem.get("ID")
           if player_xml_id is None:
               continue

           player_id = int(player_xml_id) + 1

           military_history = player_elem.find(".//MilitaryPowerHistory")
           if military_history is None:
               continue

           for turn_elem in military_history:
               turn_tag = turn_elem.tag
               if not turn_tag.startswith('T'):
                   continue

               turn_number = self._safe_int(turn_tag[1:])
               military_power = self._safe_int(turn_elem.text)

               if turn_number is None or military_power is None:
                   continue

               military_data.append({
                   "player_id": player_id,
                   "turn_number": turn_number,
                   "military_power": military_power
               })

       return military_data


   def extract_legitimacy_history(self) -> List[Dict[str, Any]]:
       """Extract legitimacy progression from LegitimacyHistory.

       Returns:
           List of legitimacy history dictionaries with:
           - player_id: Database player ID (1-based)
           - turn_number: Game turn number
           - legitimacy: Legitimacy value (0-100) for that turn
       """
       if self.root is None:
           raise ValueError("XML not parsed. Call extract_and_parse() first.")

       legitimacy_data = []

       player_elements = self.root.findall(".//Player[@OnlineID]")

       for player_elem in player_elements:
           player_xml_id = player_elem.get("ID")
           if player_xml_id is None:
               continue

           player_id = int(player_xml_id) + 1

           legitimacy_history = player_elem.find(".//LegitimacyHistory")
           if legitimacy_history is None:
               continue

           for turn_elem in legitimacy_history:
               turn_tag = turn_elem.tag
               if not turn_tag.startswith('T'):
                   continue

               turn_number = self._safe_int(turn_tag[1:])
               legitimacy = self._safe_int(turn_elem.text)

               if turn_number is None or legitimacy is None:
                   continue

               legitimacy_data.append({
                   "player_id": player_id,
                   "turn_number": turn_number,
                   "legitimacy": legitimacy
               })

       return legitimacy_data


   def extract_opinion_histories(self) -> Dict[str, List[Dict[str, Any]]]:
       """Extract family and religion opinion histories.

       Both follow the same nested pattern:
       <FamilyOpinionHistory>
           <FAMILY_NAME>
               <T2>100</T2>
               <T3>95</T3>
           </FAMILY_NAME>
       </FamilyOpinionHistory>

       Returns:
           Dictionary with two keys:
           - 'family_opinions': List of family opinion records
           - 'religion_opinions': List of religion opinion records

           Each record contains:
           - player_id: Database player ID (1-based)
           - turn_number: Game turn number
           - family_name/religion_name: Name of the family/religion
           - opinion: Opinion value (0-100) for that turn
       """
       if self.root is None:
           raise ValueError("XML not parsed. Call extract_and_parse() first.")

       family_opinions = []
       religion_opinions = []

       player_elements = self.root.findall(".//Player[@OnlineID]")

       for player_elem in player_elements:
           player_xml_id = player_elem.get("ID")
           if player_xml_id is None:
               continue

           player_id = int(player_xml_id) + 1

           # Extract family opinions
           family_history = player_elem.find(".//FamilyOpinionHistory")
           if family_history is not None:
               for family_elem in family_history:
                   family_name = family_elem.tag  # e.g., "FAMILY_JULII"

                   for turn_elem in family_elem:
                       turn_tag = turn_elem.tag
                       if not turn_tag.startswith('T'):
                           continue

                       turn_number = self._safe_int(turn_tag[1:])
                       opinion = self._safe_int(turn_elem.text)

                       if turn_number is None or opinion is None:
                           continue

                       family_opinions.append({
                           "player_id": player_id,
                           "turn_number": turn_number,
                           "family_name": family_name,
                           "opinion": opinion
                       })

           # Extract religion opinions (same pattern)
           religion_history = player_elem.find(".//ReligionOpinionHistory")
           if religion_history is not None:
               for religion_elem in religion_history:
                   religion_name = religion_elem.tag  # e.g., "RELIGION_JUPITER"

                   for turn_elem in religion_elem:
                       turn_tag = turn_elem.tag
                       if not turn_tag.startswith('T'):
                           continue

                       turn_number = self._safe_int(turn_tag[1:])
                       opinion = self._safe_int(turn_elem.text)

                       if turn_number is None or opinion is None:
                           continue

                       religion_opinions.append({
                           "player_id": player_id,
                           "turn_number": turn_number,
                           "religion_name": religion_name,
                           "opinion": opinion
                       })

       return {
           "family_opinions": family_opinions,
           "religion_opinions": religion_opinions
       }
   ```

4. **Run tests (should all pass):**
   ```bash
   uv run pytest tests/test_parser.py -v
   ```

**Commit:**
```bash
git add tests/test_parser.py tournament_visualizer/parser/parser.py
git commit -m "feat: Implement military, legitimacy, and opinion extractors

- extract_military_history(): Military power per turn
- extract_legitimacy_history(): Legitimacy per turn
- extract_opinion_histories(): Family and religion opinions
- All include comprehensive tests
- Follow DRY pattern from points/yield extractors"
```

---

#### Task 3.5: Integrate History Extraction into Main Parser
**Time:** 30 minutes
**Files:** `tournament_visualizer/parser/parser.py`, `tests/test_parser.py`

**Objective:** Update the main parse function to call all new extractors.

**Steps:**

1. **Find the main parsing orchestration function:**
   ```bash
   grep -n "def parse_tournament_file" tournament_visualizer/parser/parser.py
   ```

   Or look for a function that calls all the `extract_*` methods.

2. **Update it to include history extraction:**

   Example (adapt to actual code):
   ```python
   def parse_tournament_file(zip_file_path: str) -> Dict[str, Any]:
       """Parse a tournament save file and extract all data.

       Args:
           zip_file_path: Path to the .zip save file

       Returns:
           Dictionary containing all extracted data
       """
       parser = OldWorldSaveParser(zip_file_path)
       parser.extract_and_parse()

       # Extract all data components
       match_metadata = parser.extract_basic_metadata()
       players = parser.extract_players()

       # Extract events (both MemoryData and LogData)
       memory_events = parser.extract_events()
       logdata_events = parser.extract_logdata_events()
       events = memory_events + logdata_events

       # Extract statistics
       technology_progress = parser.extract_technology_progress()
       player_statistics = parser.extract_player_statistics()
       units_produced = parser.extract_units_produced()
       detailed_metadata = parser.extract_match_metadata()

       # NEW: Extract history data
       yield_history = parser.extract_yield_history()
       points_history = parser.extract_points_history()
       military_history = parser.extract_military_history()
       legitimacy_history = parser.extract_legitimacy_history()
       opinion_histories = parser.extract_opinion_histories()

       # Determine winner
       winner_player_id = parser.determine_winner(players)
       match_metadata["winner_player_id"] = winner_player_id

       return {
           "match_metadata": match_metadata,
           "players": players,
           "events": events,
           "technology_progress": technology_progress,
           "player_statistics": player_statistics,
           "units_produced": units_produced,
           "detailed_metadata": detailed_metadata,
           # NEW: History data
           "yield_history": yield_history,
           "points_history": points_history,
           "military_history": military_history,
           "legitimacy_history": legitimacy_history,
           "family_opinion_history": opinion_histories["family_opinions"],
           "religion_opinion_history": opinion_histories["religion_opinions"],
       }
   ```

3. **Write integration test:**

   Add to `tests/test_parser.py`:
   ```python
   def test_parse_tournament_file_includes_history():
       """Test that main parse function includes all history data."""
       from tournament_visualizer.parser.parser import parse_tournament_file

       # This test requires a real zip file
       # Adapt based on existing test setup
       # For now, just test the structure

       # Mock or use actual test file
       # result = parse_tournament_file("tests/fixtures/test_save.zip")

       # assert "yield_history" in result
       # assert "points_history" in result
       # assert "military_history" in result
       # assert "legitimacy_history" in result
       # assert "family_opinion_history" in result
       # assert "religion_opinion_history" in result

       # Skip for now if no test zip available
       pass
   ```

4. **Run all parser tests:**
   ```bash
   uv run pytest tests/test_parser.py -v
   ```

**Commit:**
```bash
git add tournament_visualizer/parser/parser.py tests/test_parser.py
git commit -m "feat: Integrate history extraction into main parser

- parse_tournament_file() now calls all history extractors
- Returns 6 new history data collections
- Maintains backward compatibility with existing data"
```

---

### Phase 4: Database Integration

#### Task 4.1: Prepare for Insertion Methods
**Time:** 15 minutes
**Files:** `tournament_visualizer/data/database.py`

**Objective:** Understand the existing insertion pattern before implementing new methods.

**Steps:**

1. **Examine existing bulk insertion methods:**
   ```bash
   # Look at how existing bulk inserts work
   grep -A 30 "def bulk_insert_events" tournament_visualizer/data/database.py
   ```

   **Notice the pattern:**
   - Methods are on the `TournamentDatabase` class
   - They use `with self.get_connection() as conn:`
   - IDs are generated using `conn.execute("SELECT nextval('seq_name')").fetchone()[0]`
   - They use `conn.executemany()` for bulk operations
   - They return early if data is empty

2. **Note the ID generation pattern:**

   This project uses **DuckDB sequences**, NOT global counters:
   ```python
   # ID generation via sequence (existing pattern)
   event_id = conn.execute("SELECT nextval('events_id_seq')").fetchone()[0]
   ```

   You'll use:
   - `nextval('points_history_id_seq')` for points history
   - `nextval('military_history_id_seq')` for military history
   - `nextval('legitimacy_history_id_seq')` for legitimacy history
   - `nextval('family_opinion_id_seq')` for family opinions
   - `nextval('religion_opinion_id_seq')` for religion opinions

3. **Understand the bulk insert pattern:**

   All bulk inserts follow this structure:
   ```python
   def bulk_insert_something(self, data: List[Dict[str, Any]]) -> None:
       """Bulk insert something records."""
       if not data:  # Early return if empty
           return

       with self.get_connection() as conn:
           query = """INSERT INTO table (...) VALUES (?, ?, ...)"""

           values = []
           for item in data:
               item_id = conn.execute("SELECT nextval('seq')").fetchone()[0]
               values.append([item_id, item["field1"], item["field2"], ...])

           conn.executemany(query, values)
   ```

**Commit:**
Not needed - this is just exploration.

---

#### Task 4.2: Implement Database Insertion Methods (TDD)
**Time:** 2 hours
**Files:** `tests/test_database.py`, `tournament_visualizer/data/database.py`

**Objective:** Write tests then implement insertion logic for history data.

**Steps:**

1. **Write test for points history insertion:**

   Add to `tests/test_database.py`:
   ```python
   import pytest
   import duckdb
   from pathlib import Path


   @pytest.fixture
   def test_db():
       """Create temporary test database."""
       db_path = Path("/tmp/test_history.duckdb")
       if db_path.exists():
           db_path.unlink()

       conn = duckdb.connect(str(db_path))

       # Create minimal schema for testing
       conn.execute("""
           CREATE TABLE matches (
               match_id BIGINT PRIMARY KEY,
               game_name VARCHAR
           )
       """)
       conn.execute("""
           CREATE TABLE players (
               player_id BIGINT PRIMARY KEY,
               match_id BIGINT,
               player_name VARCHAR
           )
       """)
       conn.execute("""
           CREATE TABLE player_points_history (
               points_history_id BIGINT PRIMARY KEY,
               match_id BIGINT NOT NULL,
               player_id BIGINT NOT NULL,
               turn_number INTEGER NOT NULL,
               points INTEGER NOT NULL,
               UNIQUE (match_id, player_id, turn_number)
           )
       """)

       # Insert test match and player
       conn.execute("INSERT INTO matches VALUES (1, 'Test Match')")
       conn.execute("INSERT INTO players VALUES (1, 1, 'TestPlayer')")

       conn.commit()
       yield conn

       conn.close()
       db_path.unlink()


   def test_insert_points_history(test_db):
       """Test inserting points history data."""
       from tournament_visualizer.data.database import insert_points_history

       # Sample data
       points_data = [
           {"player_id": 1, "turn_number": 2, "points": 5},
           {"player_id": 1, "turn_number": 3, "points": 10},
           {"player_id": 1, "turn_number": 4, "points": 15},
       ]

       match_id = 1

       # Insert data
       insert_points_history(test_db, match_id, points_data)

       # Verify insertion
       result = test_db.execute("""
           SELECT turn_number, points
           FROM player_points_history
           WHERE match_id = ? AND player_id = ?
           ORDER BY turn_number
       """, [match_id, 1]).fetchall()

       assert len(result) == 3
       assert result[0] == (2, 5)
       assert result[1] == (3, 10)
       assert result[2] == (4, 15)


   def test_insert_points_history_duplicate_prevention(test_db):
       """Test that duplicate turn entries are rejected."""
       from tournament_visualizer.data.database import insert_points_history

       points_data = [
           {"player_id": 1, "turn_number": 2, "points": 5},
       ]

       match_id = 1

       # First insertion should succeed
       insert_points_history(test_db, match_id, points_data)

       # Second insertion of same turn should fail or be ignored
       # Behavior depends on your implementation - adjust accordingly
       with pytest.raises(Exception):  # DuckDB constraint violation
           insert_points_history(test_db, match_id, points_data)
   ```

2. **Run test (should fail):**
   ```bash
   uv run pytest tests/test_database.py::test_insert_points_history -v
   ```

3. **Implement insertion method:**

   Add to the `TournamentDatabase` class in `tournament_visualizer/data/database.py`:
   ```python
   def bulk_insert_points_history(self, points_data: List[Dict[str, Any]]) -> None:
       """Bulk insert victory points history records.

       Args:
           points_data: List of points history dictionaries from parser
       """
       if not points_data:
           return

       with self.get_connection() as conn:
           query = """
           INSERT INTO player_points_history (
               points_history_id, match_id, player_id, turn_number, points
           ) VALUES (?, ?, ?, ?, ?)
           """

           values = []
           for data in points_data:
               points_id = conn.execute(
                   "SELECT nextval('points_history_id_seq')"
               ).fetchone()[0]
               values.append([
                   points_id,
                   data["match_id"],
                   data["player_id"],
                   data["turn_number"],
                   data["points"]
               ])

           conn.executemany(query, values)
   ```

4. **Run test (should pass):**
   ```bash
   uv run pytest tests/test_database.py::test_insert_points_history -v
   ```

5. **Implement remaining insertion methods** (similar pattern):

   Add to the `TournamentDatabase` class in `tournament_visualizer/data/database.py`:
   ```python
   def bulk_insert_yield_history(self, yield_data: List[Dict[str, Any]]) -> None:
       """Bulk insert yield rate history records."""
       if not yield_data:
           return

       with self.get_connection() as conn:
           query = """
           INSERT INTO resources (
               resource_id, match_id, player_id, turn_number, resource_type, amount
           ) VALUES (?, ?, ?, ?, ?, ?)
           """

           values = []
           for data in yield_data:
               resource_id = conn.execute(
                   "SELECT nextval('resources_id_seq')"
               ).fetchone()[0]
               values.append([
                   resource_id,
                   data["match_id"],
                   data["player_id"],
                   data["turn_number"],
                   data["yield_type"],
                   data["amount"]
               ])

           conn.executemany(query, values)

   def bulk_insert_military_history(self, military_data: List[Dict[str, Any]]) -> None:
       """Bulk insert military power history records."""
       if not military_data:
           return

       with self.get_connection() as conn:
           query = """
           INSERT INTO player_military_history (
               military_history_id, match_id, player_id, turn_number, military_power
           ) VALUES (?, ?, ?, ?, ?)
           """

           values = []
           for data in military_data:
               military_id = conn.execute(
                   "SELECT nextval('military_history_id_seq')"
               ).fetchone()[0]
               values.append([
                   military_id,
                   data["match_id"],
                   data["player_id"],
                   data["turn_number"],
                   data["military_power"]
               ])

           conn.executemany(query, values)

   def bulk_insert_legitimacy_history(self, legitimacy_data: List[Dict[str, Any]]) -> None:
       """Bulk insert legitimacy history records."""
       if not legitimacy_data:
           return

       with self.get_connection() as conn:
           query = """
           INSERT INTO player_legitimacy_history (
               legitimacy_history_id, match_id, player_id, turn_number, legitimacy
           ) VALUES (?, ?, ?, ?, ?)
           """

           values = []
           for data in legitimacy_data:
               legitimacy_id = conn.execute(
                   "SELECT nextval('legitimacy_history_id_seq')"
               ).fetchone()[0]
               values.append([
                   legitimacy_id,
                   data["match_id"],
                   data["player_id"],
                   data["turn_number"],
                   data["legitimacy"]
               ])

           conn.executemany(query, values)

   def bulk_insert_opinion_histories(
       self,
       family_data: List[Dict[str, Any]],
       religion_data: List[Dict[str, Any]]
   ) -> None:
       """Bulk insert family and religion opinion history records."""
       # Insert family opinions
       if family_data:
           with self.get_connection() as conn:
               query = """
               INSERT INTO family_opinion_history (
                   family_opinion_id, match_id, player_id, turn_number, family_name, opinion
               ) VALUES (?, ?, ?, ?, ?, ?)
               """

               values = []
               for data in family_data:
                   family_id = conn.execute(
                       "SELECT nextval('family_opinion_id_seq')"
                   ).fetchone()[0]
                   values.append([
                       family_id,
                       data["match_id"],
                       data["player_id"],
                       data["turn_number"],
                       data["family_name"],
                       data["opinion"]
                   ])

               conn.executemany(query, values)

       # Insert religion opinions
       if religion_data:
           with self.get_connection() as conn:
               query = """
               INSERT INTO religion_opinion_history (
                   religion_opinion_id, match_id, player_id, turn_number, religion_name, opinion
               ) VALUES (?, ?, ?, ?, ?, ?)
               """

               values = []
               for data in religion_data:
                   religion_id = conn.execute(
                       "SELECT nextval('religion_opinion_id_seq')"
                   ).fetchone()[0]
                   values.append([
                       religion_id,
                       data["match_id"],
                       data["player_id"],
                       data["turn_number"],
                       data["religion_name"],
                       data["opinion"]
                   ])

               conn.executemany(query, values)
   ```

6. **Write tests for all insertion methods:**

   Add similar tests to `tests/test_database.py` for each method (follow the pattern from `test_insert_points_history`).

7. **Run all database tests:**
   ```bash
   uv run pytest tests/test_database.py -v
   ```

**Commit:**
```bash
git add tournament_visualizer/data/database.py tests/test_database.py
git commit -m "feat: Implement database insertion methods for history tables

- bulk_insert_points_history(): Victory points
- bulk_insert_yield_history(): Yield rates (uses resources table)
- bulk_insert_military_history(): Military power
- bulk_insert_legitimacy_history(): Legitimacy
- bulk_insert_opinion_histories(): Family and religion opinions
- Follow existing bulk insert pattern with sequences
- Include comprehensive tests with duplicate prevention"
```

---

#### Task 4.3: Update Import Script
**Time:** 1 hour
**Files:** `scripts/import_tournaments.py`

**Objective:** Update the import script to insert history data.

**Steps:**

1. **Find where data is inserted:**
   ```bash
   grep -n "bulk_insert" scripts/import_tournaments.py
   ```

2. **Examine the existing pattern:**

   The script likely uses a `TournamentDatabase` instance. Look for patterns like:
   ```python
   db = TournamentDatabase(db_path, read_only=False)
   # ... later ...
   db.bulk_insert_events(events_data)
   ```

3. **Add history insertion after existing inserts:**

   Find where existing bulk inserts happen (after events, technology, stats, etc.) and add:
   ```python
   # Insert history data (new)
   # Add match_id to each history record
   for record in parsed_data["yield_history"]:
       record["match_id"] = match_id
   for record in parsed_data["points_history"]:
       record["match_id"] = match_id
   for record in parsed_data["military_history"]:
       record["match_id"] = match_id
   for record in parsed_data["legitimacy_history"]:
       record["match_id"] = match_id
   for record in parsed_data["family_opinion_history"]:
       record["match_id"] = match_id
   for record in parsed_data["religion_opinion_history"]:
       record["match_id"] = match_id

   # Bulk insert history data
   db.bulk_insert_yield_history(parsed_data["yield_history"])
   db.bulk_insert_points_history(parsed_data["points_history"])
   db.bulk_insert_military_history(parsed_data["military_history"])
   db.bulk_insert_legitimacy_history(parsed_data["legitimacy_history"])
   db.bulk_insert_opinion_histories(
       parsed_data["family_opinion_history"],
       parsed_data["religion_opinion_history"]
   )
   ```

   **Note:** The parser returns records WITHOUT match_id, so we need to add it before insertion.

4. **Test the import script** (dry run):
   ```bash
   # This won't actually run yet because schema isn't migrated
   # But check for syntax errors
   uv run python scripts/import_tournaments.py --help
   ```

   **Expected:** No import errors or syntax errors.

**Commit:**
```bash
git add scripts/import_tournaments.py
git commit -m "feat: Update import script for history data

- Call bulk_insert methods for all history tables
- Add match_id to history records before insertion
- Insert after existing data (events, tech, stats)
- Prepare for re-import after migration"
```

---

### Phase 5: Migration & Data Import

#### Task 5.1: Backup Current Database
**Time:** 5 minutes
**Files:** None

**Objective:** Create a safety backup before migration.

**Steps:**

1. **Create timestamped backup:**
   ```bash
   cp tournament_data.duckdb tournament_data.duckdb.backup_$(date +%Y%m%d_%H%M%S)
   ```

2. **Verify backup:**
   ```bash
   ls -lh tournament_data.duckdb*
   ```

   You should see both the original and backup file.

**Commit:** Not needed.

---

#### Task 5.2: Run Migration
**Time:** 10 minutes
**Files:** Database

**Objective:** Execute migration script to add new tables.

**Steps:**

1. **Run migration script:**
   ```bash
   uv run python scripts/migrations/002_add_history_tables.py
   ```

   **Expected output:**
   ```
   Creating backup: tournament_data.duckdb.backup_002
   Migrating database: tournament_data.duckdb
     - Dropping game_state table...
     - Renaming resources to player_yield_history...
     - Creating player_points_history table...
     - Creating player_military_history table...
     - Creating player_legitimacy_history table...
     - Creating family_opinion_history table...
     - Creating religion_opinion_history table...
   Migration completed successfully!
   ```

2. **Verify migration:**
   ```bash
   uv run duckdb tournament_data.duckdb -readonly -c "SHOW TABLES"
   ```

   **Should see:**
   - `player_yield_history` (renamed from resources)
   - `player_points_history` (new)
   - `player_military_history` (new)
   - `player_legitimacy_history` (new)
   - `family_opinion_history` (new)
   - `religion_opinion_history` (new)

   **Should NOT see:**
   - `game_state` (dropped)
   - `resources` (renamed)

3. **Check tables are empty:**
   ```bash
   uv run duckdb tournament_data.duckdb -readonly -c "
   SELECT
       'points' as table_name, COUNT(*) as count FROM player_points_history
   UNION ALL
   SELECT 'yield', COUNT(*) FROM player_yield_history
   UNION ALL
   SELECT 'military', COUNT(*) FROM player_military_history
   UNION ALL
   SELECT 'legitimacy', COUNT(*) FROM player_legitimacy_history
   UNION ALL
   SELECT 'family', COUNT(*) FROM family_opinion_history
   UNION ALL
   SELECT 'religion', COUNT(*) FROM religion_opinion_history
   "
   ```

   All should show 0 count (ready for import).

**Commit:** Not needed (database change, not code).

---

#### Task 5.3: Test Import with Single File
**Time:** 30 minutes
**Files:** None

**Objective:** Verify import works with one save file before full re-import.

**Steps:**

1. **Pick one save file for testing:**
   ```bash
   TEST_FILE=$(ls saves/*.zip | head -n 1)
   echo "Testing with: $TEST_FILE"
   ```

2. **Test import (if there's a single-file import option):**
   ```bash
   # Check if import script has a single-file option
   uv run python scripts/import_tournaments.py --help

   # If it does, use it:
   # uv run python scripts/import_tournaments.py --file "$TEST_FILE" --verbose

   # If not, import just one file's directory:
   mkdir -p /tmp/single_test
   cp "$TEST_FILE" /tmp/single_test/
   uv run python scripts/import_tournaments.py --directory /tmp/single_test --verbose
   ```

3. **Check for errors in output:**
   - Look for Python exceptions
   - Look for SQL errors
   - Verify import completed

4. **Verify data was inserted:**
   ```bash
   uv run duckdb tournament_data.duckdb -readonly -c "
   SELECT
       'points' as table_name, COUNT(*) as count FROM player_points_history
   UNION ALL
   SELECT 'yield', COUNT(*) FROM player_yield_history
   UNION ALL
   SELECT 'military', COUNT(*) FROM player_military_history
   UNION ALL
   SELECT 'legitimacy', COUNT(*) FROM player_legitimacy_history
   UNION ALL
   SELECT 'family', COUNT(*) FROM family_opinion_history
   UNION ALL
   SELECT 'religion', COUNT(*) FROM religion_opinion_history
   "
   ```

   **Expected:** All tables should have some data now!

5. **Verify data quality - sample query:**
   ```bash
   uv run duckdb tournament_data.duckdb -readonly -c "
   SELECT
       p.player_name,
       ph.turn_number,
       ph.points
   FROM player_points_history ph
   JOIN players p ON ph.player_id = p.player_id
   ORDER BY p.player_name, ph.turn_number
   LIMIT 20
   "
   ```

   **Check:**
   - Player names look correct
   - Turn numbers are sequential
   - Points increase over time (usually)

**Commit:** Not needed (testing only).

---

#### Task 5.4: Full Data Re-import
**Time:** 30 minutes (mostly waiting)
**Files:** None

**Objective:** Import all tournament data with new history extraction.

**Steps:**

1. **Clear database and start fresh:**
   ```bash
   # Restore from pre-migration backup to start clean
   cp tournament_data.duckdb.backup_$(date +%Y%m%d_%H%M%S | cut -c1-8)* tournament_data.duckdb.pre_reimport

   # Re-run migration on fresh database
   uv run python scripts/migrations/002_add_history_tables.py
   ```

2. **Run full import:**
   ```bash
   uv run python scripts/import_tournaments.py --directory saves --force --verbose
   ```

   **This may take several minutes** for 15 matches.

   Watch for:
   - Any error messages
   - Progress indicators
   - Final success message

3. **Verify import completed:**
   ```bash
   # Check match count
   uv run duckdb tournament_data.duckdb -readonly -c "SELECT COUNT(*) FROM matches"
   # Should be 15

   # Check player count
   uv run duckdb tournament_data.duckdb -readonly -c "SELECT COUNT(*) FROM players"
   # Should be 30 (15 matches × 2 players)
   ```

4. **Verify history data:**
   ```bash
   uv run duckdb tournament_data.duckdb -readonly -c "
   SELECT
       'points' as table_name, COUNT(*) as count FROM player_points_history
   UNION ALL
   SELECT 'yield', COUNT(*) FROM player_yield_history
   UNION ALL
   SELECT 'military', COUNT(*) FROM player_military_history
   UNION ALL
   SELECT 'legitimacy', COUNT(*) FROM player_legitimacy_history
   UNION ALL
   SELECT 'family', COUNT(*) FROM family_opinion_history
   UNION ALL
   SELECT 'religion', COUNT(*) FROM religion_opinion_history
   "
   ```

   **Expected (approximate):**
   - Points: ~2,100 rows (15 matches × 2 players × ~70 turns)
   - Yield: ~21,000 rows (15 × 2 × 70 × 10 yield types)
   - Military: ~2,100 rows
   - Legitimacy: ~2,100 rows
   - Family: ~6,300 rows (varies by number of families)
   - Religion: ~6,300 rows (varies by religions)

**Commit:** Not needed (data import, not code).

---

### Phase 6: Validation & Documentation

#### Task 6.1: Data Validation Queries
**Time:** 1 hour
**Files:** `scripts/validate_history_data.py` (new)

**Objective:** Create comprehensive validation script.

**Steps:**

1. **Create validation script:**

   **File:** `scripts/validate_history_data.py`
   ```python
   """Validate turn-by-turn history data integrity.

   This script performs comprehensive validation checks on the newly imported
   history data to ensure quality and consistency.
   """

   import duckdb
   from pathlib import Path


   def validate_turn_coverage(conn: duckdb.DuckDBPyConnection) -> None:
       """Verify turn coverage is continuous."""
       print("\n=== Validating Turn Coverage ===")

       # Check for gaps in turn sequences
       result = conn.execute("""
           SELECT
               match_id,
               player_id,
               MIN(turn_number) as min_turn,
               MAX(turn_number) as max_turn,
               COUNT(DISTINCT turn_number) as turn_count,
               MAX(turn_number) - MIN(turn_number) + 1 as expected_count
           FROM player_points_history
           GROUP BY match_id, player_id
           HAVING turn_count != expected_count
       """).fetchall()

       if result:
           print(f"  ⚠️  WARNING: Found {len(result)} players with gaps in turn coverage")
           for row in result[:5]:
               print(f"    Match {row[0]}, Player {row[1]}: {row[4]} turns, expected {row[5]}")
       else:
           print("  ✅ All players have continuous turn coverage")


   def validate_player_ids(conn: duckdb.DuckDBPyConnection) -> None:
       """Verify no orphaned player IDs."""
       print("\n=== Validating Player IDs ===")

       # Check for orphaned records in history tables
       orphaned_points = conn.execute("""
           SELECT COUNT(*)
           FROM player_points_history h
           LEFT JOIN players p ON h.player_id = p.player_id
           WHERE p.player_id IS NULL
       """).fetchone()[0]

       if orphaned_points > 0:
           print(f"  ❌ ERROR: Found {orphaned_points} orphaned records in points history")
       else:
           print("  ✅ No orphaned player IDs in points history")

       # Similar checks for other tables...
       orphaned_yield = conn.execute("""
           SELECT COUNT(*)
           FROM player_yield_history h
           LEFT JOIN players p ON h.player_id = p.player_id
           WHERE p.player_id IS NULL
       """).fetchone()[0]

       if orphaned_yield > 0:
           print(f"  ❌ ERROR: Found {orphaned_yield} orphaned records in yield history")
       else:
           print("  ✅ No orphaned player IDs in yield history")


   def validate_duplicates(conn: duckdb.DuckDBPyConnection) -> None:
       """Check for duplicate turn entries."""
       print("\n=== Validating Uniqueness ===")

       # Check for duplicate turns in points history
       duplicates = conn.execute("""
           SELECT match_id, player_id, turn_number, COUNT(*) as count
           FROM player_points_history
           GROUP BY match_id, player_id, turn_number
           HAVING COUNT(*) > 1
       """).fetchall()

       if duplicates:
           print(f"  ❌ ERROR: Found {len(duplicates)} duplicate turn entries in points history")
           for row in duplicates[:5]:
               print(f"    Match {row[0]}, Player {row[1]}, Turn {row[2]}: {row[3]} entries")
       else:
           print("  ✅ No duplicate turn entries in points history")

       # Similar for yield history
       yield_duplicates = conn.execute("""
           SELECT match_id, player_id, turn_number, resource_type, COUNT(*) as count
           FROM player_yield_history
           GROUP BY match_id, player_id, turn_number, resource_type
           HAVING COUNT(*) > 1
       """).fetchall()

       if yield_duplicates:
           print(f"  ❌ ERROR: Found {len(yield_duplicates)} duplicate entries in yield history")
       else:
           print("  ✅ No duplicate entries in yield history")


   def validate_value_ranges(conn: duckdb.DuckDBPyConnection) -> None:
       """Verify values are within expected ranges."""
       print("\n=== Validating Value Ranges ===")

       # Check legitimacy is 0-100
       invalid_legitimacy = conn.execute("""
           SELECT COUNT(*)
           FROM player_legitimacy_history
           WHERE legitimacy < 0 OR legitimacy > 100
       """).fetchone()[0]

       if invalid_legitimacy > 0:
           print(f"  ❌ ERROR: Found {invalid_legitimacy} legitimacy values outside 0-100")
       else:
           print("  ✅ All legitimacy values in valid range (0-100)")

       # Check opinions are 0-100
       invalid_family = conn.execute("""
           SELECT COUNT(*)
           FROM family_opinion_history
           WHERE opinion < 0 OR opinion > 100
       """).fetchone()[0]

       if invalid_family > 0:
           print(f"  ❌ ERROR: Found {invalid_family} family opinions outside 0-100")
       else:
           print("  ✅ All family opinions in valid range (0-100)")

       # Check military power is non-negative
       invalid_military = conn.execute("""
           SELECT COUNT(*)
           FROM player_military_history
           WHERE military_power < 0
       """).fetchone()[0]

       if invalid_military > 0:
           print(f"  ❌ ERROR: Found {invalid_military} negative military power values")
       else:
           print("  ✅ All military power values non-negative")


   def print_summary_statistics(conn: duckdb.DuckDBPyConnection) -> None:
       """Print summary statistics."""
       print("\n=== Summary Statistics ===")

       stats = conn.execute("""
           SELECT
               'points' as table_name, COUNT(*) as total_rows, COUNT(DISTINCT match_id) as matches
           FROM player_points_history
           UNION ALL
           SELECT 'yield', COUNT(*), COUNT(DISTINCT match_id)
           FROM player_yield_history
           UNION ALL
           SELECT 'military', COUNT(*), COUNT(DISTINCT match_id)
           FROM player_military_history
           UNION ALL
           SELECT 'legitimacy', COUNT(*), COUNT(DISTINCT match_id)
           FROM player_legitimacy_history
           UNION ALL
           SELECT 'family_opinion', COUNT(*), COUNT(DISTINCT match_id)
           FROM family_opinion_history
           UNION ALL
           SELECT 'religion_opinion', COUNT(*), COUNT(DISTINCT match_id)
           FROM religion_opinion_history
       """).fetchall()

       for row in stats:
           print(f"  {row[0]:20s}: {row[1]:8,d} rows across {row[2]:2d} matches")


   def main():
       """Run all validation checks."""
       db_path = Path("tournament_data.duckdb")

       if not db_path.exists():
           print(f"Error: Database not found at {db_path}")
           return

       print(f"Validating history data in: {db_path}")

       conn = duckdb.connect(str(db_path), read_only=True)

       try:
           validate_turn_coverage(conn)
           validate_player_ids(conn)
           validate_duplicates(conn)
           validate_value_ranges(conn)
           print_summary_statistics(conn)

           print("\n✅ Validation complete!")

       finally:
           conn.close()


   if __name__ == "__main__":
       main()
   ```

2. **Run validation:**
   ```bash
   uv run python scripts/validate_history_data.py
   ```

   **Review output carefully** - all checks should pass!

**Commit:**
```bash
git add scripts/validate_history_data.py
git commit -m "test: Add comprehensive history data validation script

- Validates turn coverage continuity
- Checks for orphaned player IDs
- Detects duplicate entries
- Verifies value ranges
- Prints summary statistics"
```

---

#### Task 6.2: Sample Analytics Queries
**Time:** 30 minutes
**Files:** `docs/analytics_examples.md` (new)

**Objective:** Document useful queries for the new data.

**Steps:**

1. **Create analytics examples document:**

   **File:** `docs/analytics_examples.md`
   ```markdown
   # Analytics Examples: Turn-by-Turn History Data

   This document provides example queries for analyzing turn-by-turn historical data.

   ## Victory Points Progression

   ### View VP progression for a specific match

   ```sql
   SELECT
       p.player_name,
       ph.turn_number,
       ph.points
   FROM player_points_history ph
   JOIN players p ON ph.player_id = p.player_id
   WHERE ph.match_id = 1
   ORDER BY ph.turn_number, p.player_name;
   ```

   ### Identify when the leader changed

   ```sql
   WITH ranked AS (
       SELECT
           turn_number,
           player_id,
           points,
           RANK() OVER (PARTITION BY turn_number ORDER BY points DESC) as rank
       FROM player_points_history
       WHERE match_id = 1
   )
   SELECT
       r.turn_number,
       p.player_name,
       r.points
   FROM ranked r
   JOIN players p ON r.player_id = p.player_id
   WHERE r.rank = 1
   ORDER BY r.turn_number;
   ```

   ## Economic Analysis

   ### Science production over time

   ```sql
   SELECT
       p.player_name,
       yh.turn_number,
       yh.amount as science_rate
   FROM player_yield_history yh
   JOIN players p ON yh.player_id = p.player_id
   WHERE yh.match_id = 1
     AND yh.resource_type = 'YIELD_SCIENCE'
   ORDER BY yh.turn_number, p.player_name;
   ```

   ### Compare military vs civic investment

   ```sql
   SELECT
       p.player_name,
       yh.turn_number,
       SUM(CASE WHEN yh.resource_type = 'YIELD_TRAINING' THEN yh.amount ELSE 0 END) as military,
       SUM(CASE WHEN yh.resource_type = 'YIELD_CIVICS' THEN yh.amount ELSE 0 END) as civics,
       SUM(CASE WHEN yh.resource_type = 'YIELD_TRAINING' THEN yh.amount ELSE 0 END) * 1.0 /
       NULLIF(SUM(CASE WHEN yh.resource_type = 'YIELD_CIVICS' THEN yh.amount ELSE 0 END), 0) as mil_civ_ratio
   FROM player_yield_history yh
   JOIN players p ON yh.player_id = p.player_id
   WHERE yh.match_id = 1
   GROUP BY p.player_name, yh.turn_number
   ORDER BY yh.turn_number, p.player_name;
   ```

   ## Military Analysis

   ### Military buildup timeline

   ```sql
   SELECT
       p.player_name,
       mh.turn_number,
       mh.military_power,
       mh.military_power - LAG(mh.military_power) OVER (
           PARTITION BY mh.player_id ORDER BY mh.turn_number
       ) as power_change
   FROM player_military_history mh
   JOIN players p ON mh.player_id = p.player_id
   WHERE mh.match_id = 1
   ORDER BY mh.turn_number, p.player_name;
   ```

   ### Detect arms race periods

   ```sql
   WITH military_growth AS (
       SELECT
           player_id,
           turn_number,
           military_power,
           military_power - LAG(military_power) OVER (
               PARTITION BY player_id ORDER BY turn_number
           ) as growth
       FROM player_military_history
       WHERE match_id = 1
   )
   SELECT
       turn_number,
       SUM(growth) as total_growth,
       COUNT(*) as players_building
   FROM military_growth
   WHERE growth > 0
   GROUP BY turn_number
   HAVING COUNT(*) >= 2  -- Both players building
   ORDER BY turn_number;
   ```

   ## Internal Politics

   ### Family opinion stability analysis

   ```sql
   SELECT
       p.player_name,
       fh.family_name,
       AVG(fh.opinion) as avg_opinion,
       MIN(fh.opinion) as min_opinion,
       MAX(fh.opinion) as max_opinion,
       STDDEV(fh.opinion) as volatility
   FROM family_opinion_history fh
   JOIN players p ON fh.player_id = p.player_id
   WHERE fh.match_id = 1
   GROUP BY p.player_name, fh.family_name
   ORDER BY p.player_name, volatility DESC;
   ```

   ### Identify legitimacy crises

   ```sql
   SELECT
       p.player_name,
       lh.turn_number,
       lh.legitimacy,
       LAG(lh.legitimacy) OVER (
           PARTITION BY lh.player_id ORDER BY lh.turn_number
       ) as previous_legitimacy
   FROM player_legitimacy_history lh
   JOIN players p ON lh.player_id = p.player_id
   WHERE lh.match_id = 1
     AND lh.legitimacy < 80  -- Low legitimacy threshold
   ORDER BY lh.player_id, lh.turn_number;
   ```

   ## Cross-Metric Analysis

   ### Correlate economic growth with VP gains

   ```sql
   WITH economy AS (
       SELECT
           player_id,
           turn_number,
           SUM(amount) as total_yield
       FROM player_yield_history
       WHERE match_id = 1
       GROUP BY player_id, turn_number
   )
   SELECT
       p.player_name,
       ph.turn_number,
       ph.points,
       e.total_yield,
       ph.points - LAG(ph.points) OVER (
           PARTITION BY ph.player_id ORDER BY ph.turn_number
       ) as vp_gain,
       e.total_yield - LAG(e.total_yield) OVER (
           PARTITION BY e.player_id ORDER BY e.turn_number
       ) as economy_growth
   FROM player_points_history ph
   JOIN economy e ON ph.player_id = e.player_id AND ph.turn_number = e.turn_number
   JOIN players p ON ph.player_id = p.player_id
   WHERE ph.match_id = 1
   ORDER BY ph.turn_number, p.player_name;
   ```
   ```

2. **Test a few queries:**
   ```bash
   # Try the VP progression query
   uv run duckdb tournament_data.duckdb -readonly -c "
   SELECT
       p.player_name,
       ph.turn_number,
       ph.points
   FROM player_points_history ph
   JOIN players p ON ph.player_id = p.player_id
   WHERE ph.match_id = 1
   ORDER BY ph.turn_number, p.player_name
   LIMIT 20;
   "
   ```

**Commit:**
```bash
git add docs/analytics_examples.md
git commit -m "docs: Add analytics query examples for history data

- Victory points progression queries
- Economic analysis examples
- Military buildup queries
- Internal politics analysis
- Cross-metric correlations"
```

---

#### Task 6.3: Update Developer Guide
**Time:** 30 minutes
**Files:** `docs/developer-guide.md`

**Objective:** Document the new tables and extraction process.

**Steps:**

1. **Add section about history tables:**

   Add to `docs/developer-guide.md`:
   ```markdown
   ## Turn-by-Turn History Data

   ### Overview

   As of Migration 002, the database captures turn-by-turn historical data from Old World save files. This enables time-series analytics of player progression.

   ### History Tables

   #### player_points_history
   Victory points per turn for each player.

   **Schema:**
   - `points_history_id`: Primary key
   - `match_id`: Foreign key to matches
   - `player_id`: Foreign key to players
   - `turn_number`: Game turn (2-80 typically)
   - `points`: Victory points at that turn

   **Source XML:** `Player/PointsHistory`

   #### player_yield_history
   Resource production rates per turn per yield type.

   **Schema:**
   - `resource_id`: Primary key
   - `match_id`: Foreign key to matches
   - `player_id`: Foreign key to players
   - `turn_number`: Game turn
   - `resource_type`: Yield type (YIELD_GROWTH, YIELD_CIVICS, etc.)
   - `amount`: Production rate

   **Source XML:** `Player/YieldRateHistory`

   **Note:** Originally named `resources` but was empty. Renamed and repurposed in Migration 002.

   #### player_military_history
   Military power per turn.

   **Schema:**
   - `military_history_id`: Primary key
   - `match_id`, `player_id`, `turn_number`: As above
   - `military_power`: Military strength value

   **Source XML:** `Player/MilitaryPowerHistory`

   #### player_legitimacy_history
   Governance legitimacy per turn (0-100).

   **Schema:**
   - `legitimacy_history_id`: Primary key
   - `match_id`, `player_id`, `turn_number`: As above
   - `legitimacy`: Legitimacy value (0-100)

   **Source XML:** `Player/LegitimacyHistory`

   #### family_opinion_history
   Family opinion ratings per turn.

   **Schema:**
   - `family_opinion_id`: Primary key
   - `match_id`, `player_id`, `turn_number`: As above
   - `family_name`: Family identifier (e.g., FAMILY_JULII)
   - `opinion`: Opinion value (0-100)

   **Source XML:** `Player/FamilyOpinionHistory`

   #### religion_opinion_history
   Religion opinion ratings per turn.

   **Schema:**
   - `religion_opinion_id`: Primary key
   - `match_id`, `player_id`, `turn_number`: As above
   - `religion_name`: Religion identifier (e.g., RELIGION_JUPITER)
   - `opinion`: Opinion value (0-100)

   **Source XML:** `Player/ReligionOpinionHistory`

   ### Parser Methods

   The `OldWorldSaveParser` class (`tournament_visualizer/parser/parser.py`) provides extraction methods:

   - `extract_points_history()` → List[Dict]
   - `extract_yield_history()` → List[Dict]
   - `extract_military_history()` → List[Dict]
   - `extract_legitimacy_history()` → List[Dict]
   - `extract_opinion_histories()` → Dict[str, List[Dict]]

   All methods:
   1. Find `Player[@OnlineID]` elements (human players only)
   2. Convert XML player ID (0-based) to database ID (1-based)
   3. Parse `<TN>` tags to extract turn numbers
   4. Return list of dictionaries for database insertion

   ### Database Insertion

   The `database.py` module provides insertion functions:

   - `insert_points_history(conn, match_id, points_data)`
   - `insert_yield_history(conn, match_id, yield_data)`
   - `insert_military_history(conn, match_id, military_data)`
   - `insert_legitimacy_history(conn, match_id, legitimacy_data)`
   - `insert_opinion_histories(conn, match_id, family_data, religion_data)`

   These are called automatically during import by `scripts/import_tournaments.py`.

   ### Analytics Examples

   See [analytics_examples.md](analytics_examples.md) for sample queries using this data.
   ```

**Commit:**
```bash
git add docs/developer-guide.md
git commit -m "docs: Document turn-by-turn history tables

- Add schema descriptions for all 6 history tables
- Document parser extraction methods
- Explain database insertion process
- Link to analytics examples"
```

---

#### Task 6.4: Final Testing & Verification
**Time:** 30 minutes
**Files:** None

**Objective:** Comprehensive end-to-end verification.

**Steps:**

1. **Run all tests:**
   ```bash
   uv run pytest -v
   ```

   **All tests should pass!**

2. **Run validation script:**
   ```bash
   uv run python scripts/validate_history_data.py
   ```

   **All checks should pass!**

3. **Run code formatting:**
   ```bash
   uv run black tournament_visualizer/ scripts/ tests/
   uv run ruff check --fix tournament_visualizer/ scripts/ tests/
   ```

4. **Test a few analytics queries manually:**
   ```bash
   # VP progression for match 1
   uv run duckdb tournament_data.duckdb -readonly -c "
   SELECT p.player_name, ph.turn_number, ph.points
   FROM player_points_history ph
   JOIN players p ON ph.player_id = p.player_id
   WHERE ph.match_id = 1
   ORDER BY ph.turn_number, p.player_name
   LIMIT 10;
   "

   # Total history data
   uv run duckdb tournament_data.duckdb -readonly -c "
   SELECT COUNT(*) as total_history_records
   FROM (
       SELECT 1 FROM player_points_history
       UNION ALL SELECT 1 FROM player_yield_history
       UNION ALL SELECT 1 FROM player_military_history
       UNION ALL SELECT 1 FROM player_legitimacy_history
       UNION ALL SELECT 1 FROM family_opinion_history
       UNION ALL SELECT 1 FROM religion_opinion_history
   ) sub;
   "
   ```

5. **Check database size:**
   ```bash
   ls -lh tournament_data.duckdb
   ```

   Should be larger than before but still reasonable (< 100MB for 15 matches).

**Commit:**
```bash
git add -A
git commit -m "chore: Format code and finalize implementation

- Run black formatter
- Fix linting issues
- All tests passing
- All validation checks passing"
```

---

## Testing Strategy

### Unit Tests
- ✅ **Parser Tests**: Each extraction method has dedicated tests
  - Test with sample XML fixtures
  - Test edge cases (missing data, invalid tags)
  - Verify player ID mapping (0-based → 1-based)
  - Verify turn number extraction

- ✅ **Database Tests**: Each insertion method has tests
  - Test successful insertion
  - Test duplicate prevention
  - Test foreign key constraints
  - Test with empty data

### Integration Tests
- ✅ **Full Parse Test**: Test complete file parsing with all extractors
- ✅ **Import Test**: Test single-file import end-to-end
- ✅ **Validation Script**: Comprehensive data quality checks

### Manual Testing
- ✅ **Sample Queries**: Run analytics queries to verify data makes sense
- ✅ **Performance**: Check query speed and database size
- ✅ **Visualization**: If Dash app exists, test new charts

### Test Data
- **Fixtures**: Minimal XML samples for unit tests
- **Real Data**: One actual save file for integration testing
- **Full Dataset**: All 15 matches for final validation

---

## Rollback Procedure

### If Migration Fails

```bash
# Restore from automatic migration backup
uv run python scripts/migrations/002_add_history_tables.py --rollback
```

### If Data is Corrupted

```bash
# Restore from timestamped backup
cp tournament_data.duckdb.backup_YYYYMMDD_HHMMSS tournament_data.duckdb
```

### If Code is Broken

```bash
# Revert commits
git log --oneline  # Find commit before changes
git revert <commit-hash>..HEAD

# Or hard reset (destructive)
git reset --hard <commit-hash>
```

---

## Success Metrics

### Data Completeness
- ✅ All 15 matches have history data
- ✅ All players have continuous turn coverage (no gaps)
- ✅ All 6 history tables populated
- ✅ Row counts match expectations (~40K total rows)

### Data Quality
- ✅ No orphaned player IDs
- ✅ No duplicate turn entries
- ✅ All values within expected ranges
- ✅ Turn sequences are continuous

### Code Quality
- ✅ All tests passing
- ✅ Code formatted (black)
- ✅ No linting errors (ruff)
- ✅ Type annotations present

### Documentation
- ✅ Migration documented
- ✅ Schema documented in developer guide
- ✅ Analytics examples provided
- ✅ Commit messages clear and descriptive

### Performance
- ✅ Queries complete in < 1 second
- ✅ Database size reasonable (< 100MB)
- ✅ Import time acceptable (< 5 minutes for 15 matches)

---

## Estimated Timeline

| Phase | Tasks | Time |
|-------|-------|------|
| Phase 1: Setup | 2 tasks | 1 hour |
| Phase 2: Schema | 2 tasks | 2 hours |
| Phase 3: Parser (TDD) | 5 tasks | 5 hours |
| Phase 4: Database | 3 tasks | 3.5 hours |
| Phase 5: Migration | 4 tasks | 1.5 hours |
| Phase 6: Validation | 4 tasks | 2.5 hours |
| **TOTAL** | **20 tasks** | **15.5 hours** |

Add buffer for debugging: **~18 hours total**

---

## Common Issues & Solutions

### Issue: "XML not parsed" error
**Solution:** Ensure you call `parser.extract_and_parse()` or load the XML fixture before calling extraction methods.

### Issue: Player ID mismatch
**Solution:** Remember XML uses 0-based IDs, database uses 1-based. Always add 1 when converting.

### Issue: No data extracted
**Solution:** Check if XML has `OnlineID` attribute on Player elements. Only human players are extracted.

### Issue: Duplicate key violations
**Solution:** Check UNIQUE constraints in schema. Ensure match_id is different for each import.

### Issue: Foreign key violations
**Solution:** Ensure matches and players are inserted before history data. Check insertion order.

### Issue: Tests fail with "parser has no attribute _parse_xml_string"
**Solution:** Adjust test code to match actual parser API. May need to create temp zip files instead of parsing XML strings directly.

---

## Next Steps After Implementation

1. **Update Dash Visualizations**
   - Add VP progression line charts
   - Add economic growth visualizations
   - Add military timeline charts

2. **Performance Optimization**
   - Add materialized views for common queries
   - Consider partitioning if dataset grows large

3. **Additional Analytics**
   - Calculate VP per turn averages
   - Identify critical turning points automatically
   - Correlation analysis between metrics

4. **Documentation**
   - Add visualization guide
   - Create user guide for analytics
   - Document common analysis patterns

---

## Questions to Ask If Stuck

1. **Parser**: How are other extraction methods implemented? (Copy the pattern!)
2. **Database**: How do existing insertion methods work? (Follow the same structure!)
3. **Tests**: What do existing tests look like? (Mimic the style!)
4. **XML**: Where is this element in the actual save file? (Use `grep` or text editor search!)
5. **Schema**: What do similar tables look like? (Check existing table definitions!)

---

## Congratulations!

When you complete this plan, you will have:
- ✅ Migrated the database schema
- ✅ Added 40,000+ rows of historical data
- ✅ Written comprehensive tests
- ✅ Created validation tools
- ✅ Documented everything
- ✅ Unlocked powerful time-series analytics

**This is a major feature addition. Take your time, commit frequently, and test thoroughly!**
