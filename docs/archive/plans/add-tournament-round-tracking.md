# Implementation Plan: Add Tournament Round Tracking

**Status:** Not Started
**Created:** 2025-11-04
**Approach:** Store round data in matches table, fetch from Challonge API during import

## Overview

Add tournament round and bracket information from the Challonge API to enable filtering matches by tournament progression (round number and winner/loser bracket).

**Current state:** Match records have no tournament structure metadata
**Goal state:** Every match has `tournament_round` field populated from Challonge API

## Context for New Engineers

### What Problem Are We Solving?

Tournament organizers use Challonge to run double-elimination tournaments. Challonge tracks:
- Which **round** a match belongs to (Round 1, Round 2, etc.)
- Which **bracket** it's in (Winners or Losers)

We need this data in our database so users can filter dashboard views like:
- "Show only Round 1 matches"
- "Show only Winners Bracket finals"
- "Compare Winners vs Losers bracket performance"

### What is Old World?

Old World is a historical 4X strategy game. Players compete in multiplayer tournaments organized via Challonge. We import end-of-game save files and tournament metadata for analytics.

### What is Challonge?

Challonge is a tournament bracket management platform. It provides:
- Tournament bracket visualization
- Match scheduling
- Result tracking
- **REST API** for programmatic access

### How Challonge Represents Round/Bracket

Challonge uses a **signed integer** for rounds:
- **Positive numbers** = Winners Bracket (1, 2, 3, ...)
- **Negative/zero numbers** = Losers Bracket (-1, -2, -3, ...)

Example:
- Round `1` = Winners Round 1
- Round `3` = Winners Round 3 (Semifinals)
- Round `-1` = Losers Round 1
- Round `-5` = Losers Round 5 (Losers Finals)

### Our System Architecture

```
┌─────────────────┐
│  Challonge API  │ ← Fetch round data
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  Save Files     │ ← Parse game data
│  (.zip w/ XML)  │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  ETL Pipeline   │ ← Merge both sources
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  DuckDB         │ ← Query for dashboard
└─────────────────┘
```

### Key Files

**Data Layer:**
- `tournament_visualizer/data/database.py` - Schema and database operations
- `tournament_visualizer/data/etl.py` - Import orchestration
- `tournament_visualizer/data/parser.py` - XML save file parsing
- `scripts/import_attachments.py` - Main import script

**API Integration:**
- `scripts/list_matches_without_saves.py` - Example of Challonge API usage

**Schema:**
- `docs/schema.sql` - Current schema documentation
- `docs/migrations/` - Schema change history

### Development Workflow

Follow **TDD (Test-Driven Development)**:

1. **Red:** Write failing test first
2. **Green:** Implement minimum code to pass
3. **Refactor:** Clean up while keeping tests green
4. **Commit:** Commit when all tests pass

**Commit early, commit often** - one logical change per commit.

### Tools We Use

- **uv** - Python package manager (like npm for JavaScript)
  ```bash
  uv run python script.py   # Run Python with managed dependencies
  uv run pytest             # Run tests
  ```

- **DuckDB** - Analytics database (like SQLite but optimized for analytics)
  ```bash
  uv run duckdb data/tournament_data.duckdb -readonly
  ```

- **pytest** - Testing framework
  ```bash
  uv run pytest -v                     # Run all tests verbosely
  uv run pytest tests/test_file.py -v # Run specific test file
  ```

- **chyllonge** - Challonge API client library
  - Flat response format (no nested 'match' or 'tournament' keys)
  - Access fields directly: `match['id']`, `match['round']`
  - See `scripts/list_matches_without_saves.py` for examples

### Environment Setup

Challonge API requires credentials:

```bash
# .env file (not in git)
CHALLONGE_KEY=your_api_key_here
CHALLONGE_USER=your_username
```

Get API key from: https://challonge.com/settings/developer

## Architecture Decisions

### Decision 1: Single Column vs Two Columns

**Chosen: Option A - Single `tournament_round` column (INTEGER)**

Store Challonge's raw signed integer:
- `1`, `2`, `3` = Winners Bracket Round 1, 2, 3
- `-1`, `-2`, `-3` = Losers Bracket Round 1, 2, 3

**Rationale:**
- DRY: Preserves raw data, derive bracket in queries as needed
- Simple: One column, one source of truth
- Flexible: Can change display logic without schema migration

**Derive bracket in queries:**
```sql
SELECT
  match_id,
  tournament_round,
  CASE
    WHEN tournament_round > 0 THEN 'Winners'
    WHEN tournament_round < 0 THEN 'Losers'
    ELSE 'Unknown'
  END as bracket
FROM matches
```

**Rejected: Option B - Two columns (`tournament_round` INT + `bracket` VARCHAR)**
- Violates DRY (duplicate information)
- Maintenance burden (must keep in sync)
- More storage

### Decision 2: Fetch Strategy

**Chosen: Fetch all matches once at import start, cache in memory**

```python
# Pseudocode
def import_directory(save_files):
    # Fetch ONCE at start
    challonge_matches = fetch_all_tournament_matches()
    match_cache = {m['id']: m for m in challonge_matches}

    for save_file in save_files:
        challonge_id = extract_id_from_filename(save_file)
        round_num = match_cache.get(challonge_id, {}).get('round')
        # Process with round_num
```

**Rationale:**
- Efficient: One API call instead of N calls
- Fast: No network latency during import loop
- Respectful: Avoids rate limiting

**Rejected: Fetch per-file**
- Slow (N API calls)
- Rate limit risk
- Unnecessary network traffic

### Decision 3: Missing challonge_match_id Handling

**Chosen: Log warning, continue with NULL**

Some save files might not have a `challonge_match_id` (test games, manual uploads).

```python
if challonge_match_id is None:
    logger.warning(f"No challonge_match_id for {filename}, tournament_round will be NULL")
    tournament_round = None
else:
    tournament_round = round_cache.get(challonge_match_id)
```

**Rationale:**
- Resilient: Don't block import for missing data
- Informative: Warning helps debug
- Graceful: NULL is semantically correct

**Rejected: Fail import**
- Too strict (YAGNI - might have valid non-tournament matches)
- Bad UX (breaks entire import for one file)

### Decision 4: API Failure Handling

**Chosen: Continue with NULL values, log error**

If Challonge API fails at import start:

```python
try:
    matches = api.matches.get_all(tournament_url)
    round_cache = {m['id']: m['round'] for m in matches}
except Exception as e:
    logger.error(f"Failed to fetch Challonge data: {e}")
    round_cache = {}  # Empty cache, all rounds will be NULL
```

**Rationale:**
- Resilient: Import can proceed without API
- Valuable: Game data more important than round metadata
- Fixable: Can backfill later with separate script

**Rejected: Fail entire import**
- Too fragile (API downtime blocks all imports)
- Unnecessary coupling

## Database Schema Changes

### New Column

```sql
ALTER TABLE matches ADD COLUMN tournament_round INTEGER;
```

**Column Details:**
- **Name:** `tournament_round`
- **Type:** `INTEGER` (nullable)
- **Values:**
  - Positive integers (1, 2, 3, ...) = Winners Bracket
  - Negative integers (-1, -2, -3, ...) = Losers Bracket
  - `NULL` = Unknown (missing challonge_match_id or API failure)

**Index:**
```sql
CREATE INDEX IF NOT EXISTS idx_matches_tournament_round
ON matches(tournament_round);
```

**Why index?**
- Common filter in dashboard queries
- Cheap to maintain (low cardinality)

### Migration Strategy

Since this project uses fresh database rebuilds:
1. Update `_create_matches_table()` in `database.py`
2. No ALTER TABLE needed
3. Document in migrations for reference

## Implementation Tasks

Tasks are ordered to follow TDD principles and minimize risk.

---

### Task 1: Write Challonge API Fetch Test

**File:** `tests/test_challonge_integration.py` (NEW)

**What:** Test that we can fetch and cache tournament round data from Challonge API

**Why:** TDD - test first! Verifies API integration works before modifying production code

**Dependencies:** None (first task)

**Estimated Time:** 20 minutes

**Steps:**

1. **Create test file:**
   ```bash
   touch tests/test_challonge_integration.py
   ```

2. **Write test:**
   ```python
   """Tests for Challonge API integration."""

   import os
   import pytest
   from chyllonge.api import ChallongeApi
   from dotenv import load_dotenv


   # Skip if no API credentials
   @pytest.mark.skipif(
       not os.getenv("CHALLONGE_KEY"),
       reason="Challonge API credentials not configured"
   )
   class TestChallongeIntegration:
       """Test Challonge API data fetching."""

       @pytest.fixture
       def api(self) -> ChallongeApi:
           """Create Challonge API client."""
           load_dotenv()
           return ChallongeApi()

       def test_fetch_tournament_matches(self, api: ChallongeApi) -> None:
           """Test fetching all matches from tournament."""
           # ARRANGE
           tournament_url = "owduels2025"

           # ACT
           matches = api.matches.get_all(tournament_url)

           # ASSERT
           assert len(matches) > 0, "Tournament should have matches"

           # Verify structure
           first_match = matches[0]
           assert "id" in first_match
           assert "round" in first_match
           assert isinstance(first_match["round"], int)

       def test_create_round_cache(self, api: ChallongeApi) -> None:
           """Test creating round number cache from API data."""
           # ARRANGE
           tournament_url = "owduels2025"
           matches = api.matches.get_all(tournament_url)

           # ACT - Create cache like we'll use in ETL
           round_cache = {
               match["id"]: match["round"]
               for match in matches
           }

           # ASSERT
           assert len(round_cache) > 0
           assert all(isinstance(r, int) for r in round_cache.values())

           # Verify we have both positive and negative rounds (both brackets)
           rounds = list(round_cache.values())
           has_positive = any(r > 0 for r in rounds)
           has_negative = any(r < 0 for r in rounds)
           assert has_positive, "Should have winners bracket matches"
           # Note: Might not have losers matches yet depending on tournament state
   ```

3. **Run test (should PASS if API is configured):**
   ```bash
   uv run pytest tests/test_challonge_integration.py -v
   ```

4. **Verify skipping works without credentials:**
   ```bash
   # Temporarily rename .env
   mv .env .env.backup
   uv run pytest tests/test_challonge_integration.py -v
   # Should show: SKIPPED (Challonge API credentials not configured)
   mv .env.backup .env
   ```

**Success Criteria:**
- Test passes with valid credentials
- Test skips gracefully without credentials
- Cache structure matches expected format

**Commit Message:**
```
test: Add Challonge API integration tests

- Test fetching tournament matches
- Test creating round number cache
- Skip tests when API credentials missing
```

---

### Task 2: Update Database Schema

**File:** `tournament_visualizer/data/database.py`

**What:** Add `tournament_round` column to matches table schema

**Why:** Needs to exist before import can populate it

**Dependencies:** Task 1 complete

**Estimated Time:** 15 minutes

**Steps:**

1. **Open `database.py` and find `_create_matches_table()` method** (around line 196)

2. **Add column to CREATE TABLE statement:**

   Find this section:
   ```python
   total_turns INTEGER,
   winner_player_id BIGINT,
   ```

   Add after `total_turns`:
   ```python
   total_turns INTEGER,
   tournament_round INTEGER,  # <-- ADD THIS LINE
   winner_player_id BIGINT,
   ```

3. **Add index for the new column:**

   Find this section:
   ```python
   CREATE INDEX IF NOT EXISTS idx_matches_save_date ON matches(save_date);
   CREATE INDEX IF NOT EXISTS idx_matches_winner ON matches(winner_player_id);
   ```

   Add after those:
   ```python
   CREATE INDEX IF NOT EXISTS idx_matches_tournament_round ON matches(tournament_round);
   ```

4. **Verify schema in DuckDB:**
   ```bash
   # Backup existing DB
   cp data/tournament_data.duckdb data/tournament_data.duckdb.backup_before_round

   # Recreate schema (will wipe data - that's ok for now)
   rm data/tournament_data.duckdb

   # Run import to create schema
   uv run python -c "
   from tournament_visualizer.data.database import TournamentDatabase
   db = TournamentDatabase('data/tournament_data.duckdb', read_only=False)
   db.create_schema()
   db.close()
   print('Schema created')
   "

   # Check column exists
   uv run duckdb data/tournament_data.duckdb -readonly -c "DESCRIBE matches" | grep tournament_round
   ```

   Should show:
   ```
   │ tournament_round │ INTEGER │ YES │ NULL │ NULL │ NULL │
   ```

5. **Check index exists:**
   ```bash
   uv run duckdb data/tournament_data.duckdb -readonly -c "SHOW TABLES" | grep idx_matches_tournament_round
   ```

**Success Criteria:**
- Column appears in schema
- Column type is INTEGER
- Column is nullable
- Index exists

**Commit Message:**
```
feat: Add tournament_round column to matches table

- Add tournament_round INTEGER column (nullable)
- Add index for filtering by round
- Stores Challonge round number (positive=winners, negative=losers)
```

---

### Task 3: Add Round Fetching to ETL

**File:** `tournament_visualizer/data/etl.py`

**What:** Add function to fetch and cache tournament round data from Challonge

**Why:** ETL needs round data to populate database during import

**Dependencies:** Tasks 1-2 complete

**Estimated Time:** 30 minutes

**Steps:**

1. **Add imports at top of `etl.py`:**
   ```python
   import os
   from typing import Any, Dict, List, Optional, Tuple

   from chyllonge.api import ChallongeApi  # ADD THIS
   from dotenv import load_dotenv          # ADD THIS
   ```

2. **Add helper function after imports:**
   ```python
   def fetch_tournament_rounds(tournament_url: str = "owduels2025") -> Dict[int, int]:
       """Fetch tournament round numbers from Challonge API.

       Args:
           tournament_url: Challonge tournament URL identifier

       Returns:
           Dictionary mapping challonge_match_id to round number.
           Returns empty dict if API call fails.

       Note:
           Round numbers are signed integers:
           - Positive (1, 2, 3, ...) = Winners Bracket
           - Negative (-1, -2, -3, ...) = Losers Bracket
       """
       load_dotenv()

       # Check for API credentials
       if not os.getenv("CHALLONGE_KEY"):
           logger.warning(
               "Challonge API credentials not configured. "
               "tournament_round will be NULL for all matches."
           )
           return {}

       try:
           logger.info(f"Fetching tournament structure from Challonge: {tournament_url}")
           api = ChallongeApi()
           matches = api.matches.get_all(tournament_url)

           # Build cache: challonge_match_id -> round_number
           round_cache = {
               match["id"]: match["round"]
               for match in matches
           }

           logger.info(f"Cached {len(round_cache)} match rounds from Challonge")
           return round_cache

       except Exception as e:
           logger.error(f"Failed to fetch Challonge tournament data: {e}")
           logger.warning("Continuing import without round data (will be NULL)")
           return {}
   ```

3. **Find the `process_tournament_directory` function** (around line 300+)

4. **Add round cache to `process_tournament_directory`:**

   Find the function start:
   ```python
   def process_tournament_directory(
       directory: Path,
       force: bool = False,
       verbose: bool = False,
   ) -> Dict[str, Any]:
   ```

   After the docstring, add:
   ```python
       # Fetch tournament round data once at start
       logger.info("Fetching tournament structure from Challonge API...")
       round_cache = fetch_tournament_rounds()
   ```

5. **Pass round_cache to the ETL pipeline:**

   Find where `TournamentETL` is instantiated (search for `etl = TournamentETL`):
   ```python
   etl = TournamentETL(database=db)
   ```

   Update to pass round_cache (we'll add parameter next):
   ```python
   etl = TournamentETL(database=db, round_cache=round_cache)
   ```

6. **Update `TournamentETL.__init__` to accept round_cache:**

   Find the `__init__` method:
   ```python
   def __init__(self, database: Optional[TournamentDatabase] = None) -> None:
   ```

   Update to:
   ```python
   def __init__(
       self,
       database: Optional[TournamentDatabase] = None,
       round_cache: Optional[Dict[int, int]] = None
   ) -> None:
       """Initialize ETL pipeline.

       Args:
           database: Database instance to use (defaults to global instance)
           round_cache: Optional cache of challonge_match_id -> round_number
       """
       self.db = database or get_database()
       self.round_cache = round_cache or {}
   ```

7. **Update `process_tournament_file` to use round_cache:**

   Find where `challonge_match_id` is set (around line 92):
   ```python
   if challonge_match_id:
       match_metadata["challonge_match_id"] = challonge_match_id
   ```

   Add after that:
   ```python
   if challonge_match_id:
       match_metadata["challonge_match_id"] = challonge_match_id

       # Add tournament round from cache
       tournament_round = self.round_cache.get(challonge_match_id)
       if tournament_round is not None:
           match_metadata["tournament_round"] = tournament_round
       else:
           logger.warning(
               f"No round data found for challonge_match_id {challonge_match_id}"
           )
   ```

**Success Criteria:**
- `fetch_tournament_rounds()` function exists and has docstring
- Returns empty dict on error (doesn't crash)
- Logs appropriate warnings
- Round cache passed to ETL pipeline
- Round added to match_metadata before insert

**Commit Message:**
```
feat: Fetch tournament rounds from Challonge during import

- Add fetch_tournament_rounds() to get round data from API
- Cache rounds at import start (one API call)
- Pass round cache through ETL pipeline
- Add tournament_round to match metadata
- Handle API failures gracefully (continue with NULL)
```

---

### Task 4: Write ETL Integration Test

**File:** `tests/test_etl_round_integration.py` (NEW)

**What:** Test that ETL correctly populates tournament_round from cache

**Why:** Verify the ETL changes work end-to-end

**Dependencies:** Tasks 1-3 complete

**Estimated Time:** 25 minutes

**Steps:**

1. **Create test file:**
   ```bash
   touch tests/test_etl_round_integration.py
   ```

2. **Write test:**
   ```python
   """Test ETL integration with tournament round tracking."""

   import tempfile
   from pathlib import Path
   from typing import Dict

   import pytest

   from tournament_visualizer.data.database import TournamentDatabase
   from tournament_visualizer.data.etl import TournamentETL


   @pytest.fixture
   def temp_db() -> TournamentDatabase:
       """Create temporary test database."""
       with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False) as f:
           db_path = f.name

       db = TournamentDatabase(db_path, read_only=False)
       db.create_schema()
       yield db
       db.close()

       # Cleanup
       Path(db_path).unlink(missing_ok=True)


   class TestETLRoundIntegration:
       """Test tournament round integration in ETL pipeline."""

       def test_round_cache_initialization(self, temp_db: TournamentDatabase) -> None:
           """Test ETL accepts round_cache parameter."""
           # ARRANGE
           round_cache = {426504730: 1, 426504731: 2}

           # ACT
           etl = TournamentETL(database=temp_db, round_cache=round_cache)

           # ASSERT
           assert etl.round_cache == round_cache

       def test_round_cache_defaults_empty(self, temp_db: TournamentDatabase) -> None:
           """Test ETL uses empty dict if no cache provided."""
           # ACT
           etl = TournamentETL(database=temp_db)

           # ASSERT
           assert etl.round_cache == {}

       def test_round_added_to_match_metadata(
           self,
           temp_db: TournamentDatabase,
           sample_save_file: Path  # You'll need to add this fixture
       ) -> None:
           """Test that tournament_round is added from cache during import."""
           # ARRANGE
           challonge_id = 426504730
           expected_round = 3
           round_cache = {challonge_id: expected_round}

           etl = TournamentETL(database=temp_db, round_cache=round_cache)

           # ACT
           success = etl.process_tournament_file(
               str(sample_save_file),
               challonge_match_id=challonge_id
           )

           # ASSERT
           assert success

           # Verify round in database
           result = temp_db.fetch_one(
               "SELECT tournament_round FROM matches WHERE challonge_match_id = ?",
               {"challonge_match_id": challonge_id}
           )
           assert result is not None
           assert result[0] == expected_round

       def test_missing_round_in_cache_logs_warning(
           self,
           temp_db: TournamentDatabase,
           sample_save_file: Path,
           caplog
       ) -> None:
           """Test warning logged when challonge_match_id not in cache."""
           # ARRANGE
           challonge_id = 426504730
           round_cache = {999999: 1}  # Different ID

           etl = TournamentETL(database=temp_db, round_cache=round_cache)

           # ACT
           etl.process_tournament_file(
               str(sample_save_file),
               challonge_match_id=challonge_id
           )

           # ASSERT
           assert "No round data found" in caplog.text

           # Verify round is NULL
           result = temp_db.fetch_one(
               "SELECT tournament_round FROM matches WHERE challonge_match_id = ?",
               {"challonge_match_id": challonge_id}
           )
           assert result[0] is None
   ```

3. **Add sample save file fixture if not exists:**

   Check if `conftest.py` has a sample save file fixture. If not, add one:

   ```python
   @pytest.fixture
   def sample_save_file() -> Path:
       """Path to a real save file for testing."""
       # Use an existing save file from saves/
       save_dir = Path("saves")
       save_files = list(save_dir.glob("*.zip"))

       if not save_files:
           pytest.skip("No save files available for testing")

       return save_files[0]
   ```

4. **Run tests:**
   ```bash
   uv run pytest tests/test_etl_round_integration.py -v
   ```

5. **If tests fail, debug:**
   - Check error messages
   - Verify database schema has tournament_round
   - Verify ETL changes from Task 3
   - Use `pytest -v -s` to see print output

**Success Criteria:**
- All tests pass
- Round data correctly flows from cache to database
- NULL handling works correctly
- Warning logged for missing rounds

**Commit Message:**
```
test: Add ETL integration tests for tournament rounds

- Test round cache initialization
- Test round data flows to database
- Test NULL handling for missing rounds
- Test warning logged for cache misses
```

---

### Task 5: Update Schema Documentation

**File:** `docs/schema.sql`

**What:** Document the new column in schema export

**Why:** Keep documentation in sync with actual schema

**Dependencies:** Tasks 1-4 complete

**Estimated Time:** 10 minutes

**Steps:**

1. **Export current schema:**
   ```bash
   uv run python scripts/export_schema.py
   ```

   This will update both `docs/schema.sql` and `docs/database-schema.md`

2. **Verify tournament_round appears in `docs/schema.sql`:**
   ```bash
   grep -A2 "tournament_round" docs/schema.sql
   ```

   Should show:
   ```sql
   tournament_round INTEGER,
   ```

3. **Verify index appears:**
   ```bash
   grep "idx_matches_tournament_round" docs/schema.sql
   ```

4. **Review `docs/database-schema.md` for matches table:**
   ```bash
   # Open in editor and check matches table section
   ```

**Success Criteria:**
- `tournament_round` column documented in schema.sql
- Index documented
- database-schema.md updated

**Commit Message:**
```
docs: Update schema documentation with tournament_round

- Export current schema to docs/
- Document tournament_round column
- Document round index
```

---

### Task 6: Create Migration Documentation

**File:** `docs/migrations/010_add_tournament_round.md` (NEW)

**What:** Document the schema change for future reference

**Why:** We track all schema changes for rollback and understanding history

**Dependencies:** Tasks 1-5 complete

**Estimated Time:** 15 minutes

**Steps:**

1. **Create migration document:**
   ```bash
   touch docs/migrations/010_add_tournament_round.md
   ```

2. **Write documentation:**
   ```markdown
   # Migration 010: Add Tournament Round Tracking

   ## Overview

   Adds tournament round metadata from Challonge API to enable filtering by tournament progression.

   **Date:** 2025-11-04
   **Author:** System
   **Status:** Completed

   ---

   ## Changes

   ### Updated Table: matches

   Adds column to store tournament round number from Challonge.

   ```sql
   ALTER TABLE matches
   ADD COLUMN tournament_round INTEGER;

   CREATE INDEX IF NOT EXISTS idx_matches_tournament_round
   ON matches(tournament_round);
   ```

   **Column Details:**
   - **Type:** INTEGER (nullable)
   - **Values:**
     - Positive (1, 2, 3, ...) = Winners Bracket rounds
     - Negative (-1, -2, -3, ...) = Losers Bracket rounds
     - NULL = Unknown (no challonge_match_id or API error)

   **Derive Bracket in Queries:**
   ```sql
   SELECT
     tournament_round,
     CASE
       WHEN tournament_round > 0 THEN 'Winners'
       WHEN tournament_round < 0 THEN 'Losers'
       ELSE 'Unknown'
     END as bracket
   FROM matches
   ```

   ---

   ## Migration Procedure

   ### Step 1: Backup Database

   ```bash
   cp data/tournament_data.duckdb data/tournament_data.duckdb.backup_$(date +%Y%m%d_%H%M%S)
   ```

   ### Step 2: Fresh Import (Recommended)

   Since this project rebuilds database from source:

   ```bash
   # Remove old database
   rm data/tournament_data.duckdb

   # Re-import with new schema
   uv run python scripts/import_attachments.py --directory saves --force --verbose
   ```

   ### Step 3: Verify Schema

   ```bash
   uv run duckdb data/tournament_data.duckdb -readonly -c "DESCRIBE matches" | grep tournament_round
   ```

   Should show:
   ```
   │ tournament_round │ INTEGER │ YES │ NULL │ NULL │ NULL │
   ```

   ### Step 4: Verify Data

   ```bash
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT
     tournament_round,
     COUNT(*) as match_count,
     CASE
       WHEN tournament_round > 0 THEN 'Winners'
       WHEN tournament_round < 0 THEN 'Losers'
       ELSE 'Unknown'
     END as bracket
   FROM matches
   GROUP BY tournament_round
   ORDER BY tournament_round
   "
   ```

   ---

   ## Rollback Procedure

   ```bash
   # Restore from backup
   cp data/tournament_data.duckdb.backup_YYYYMMDD_HHMMSS data/tournament_data.duckdb
   ```

   No schema rollback needed if using fresh import approach.

   ---

   ## Related Files

   - `tournament_visualizer/data/database.py:196` - Schema definition
   - `tournament_visualizer/data/etl.py` - Round fetching logic
   - `scripts/import_attachments.py` - Import script
   - `tests/test_challonge_integration.py` - API integration tests
   - `tests/test_etl_round_integration.py` - ETL tests

   ---

   ## API Integration Notes

   **Challonge API Setup:**

   Requires environment variables in `.env`:
   ```bash
   CHALLONGE_KEY=your_api_key
   CHALLONGE_USER=your_username
   ```

   Get API key from: https://challonge.com/settings/developer

   **Error Handling:**

   - If API credentials missing: Logs warning, continues with NULL
   - If API call fails: Logs error, continues with NULL
   - If challonge_match_id missing: Logs warning, stores NULL
   - If match not in cache: Logs warning, stores NULL

   **Performance:**

   - Fetches all matches once at import start
   - Caches in memory for O(1) lookup
   - One API call per import, not per file
   ```

3. **Add to migrations README:**
   ```bash
   # Edit docs/migrations/README.md
   # Add line:
   # - [010_add_tournament_round.md](010_add_tournament_round.md) - Add tournament round tracking
   ```

**Success Criteria:**
- Migration document complete and clear
- Includes rollback procedure
- Documents API requirements
- Lists all related files

**Commit Message:**
```
docs: Add migration 010 for tournament round tracking

- Document schema changes
- Include migration and rollback procedures
- Document API integration requirements
- List related code files
```

---

### Task 7: Test Full Import with Real Data

**What:** Run complete import with Challonge API integration

**Why:** Verify everything works end-to-end with production data

**Dependencies:** Tasks 1-6 complete

**Estimated Time:** 15 minutes (plus import time)

**Steps:**

1. **Backup current database:**
   ```bash
   cp data/tournament_data.duckdb data/tournament_data.duckdb.backup_before_round_test
   ```

2. **Verify API credentials:**
   ```bash
   cat .env | grep CHALLONGE
   ```

   Should show:
   ```
   CHALLONGE_KEY=...
   CHALLONGE_USER=...
   ```

3. **Test with a few files first:**
   ```bash
   # Create test directory with 3 files
   mkdir -p test_saves
   cp saves/match_*.zip test_saves/ | head -3

   # Remove DB and run import
   rm data/tournament_data.duckdb
   uv run python scripts/import_attachments.py --directory test_saves --verbose
   ```

4. **Check for Challonge API logs:**
   Look for these log lines:
   - `"Fetching tournament structure from Challonge API..."`
   - `"Cached X match rounds from Challonge"`

5. **Verify round data in database:**
   ```bash
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT
     challonge_match_id,
     tournament_round,
     CASE
       WHEN tournament_round > 0 THEN 'Winners'
       WHEN tournament_round < 0 THEN 'Losers'
       ELSE 'Unknown'
     END as bracket,
     game_name
   FROM matches
   ORDER BY tournament_round
   "
   ```

   **Expect:**
   - tournament_round populated (not all NULL)
   - Mix of positive and negative numbers
   - Reasonable round numbers (1-10, -1 to -10)

6. **Check round distribution:**
   ```bash
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT
     tournament_round,
     COUNT(*) as matches,
     CASE
       WHEN tournament_round > 0 THEN 'Winners'
       WHEN tournament_round < 0 THEN 'Losers'
       ELSE 'Unknown'
     END as bracket
   FROM matches
   GROUP BY tournament_round
   ORDER BY tournament_round
   "
   ```

7. **If successful, run full import:**
   ```bash
   # Clean up test
   rm -rf test_saves

   # Full import
   rm data/tournament_data.duckdb
   uv run python scripts/import_attachments.py --directory saves --force --verbose 2>&1 | tee import_with_rounds.log
   ```

8. **Verify final results:**
   ```bash
   # Check completion
   tail -20 import_with_rounds.log

   # Verify round data
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT
     COUNT(*) as total_matches,
     COUNT(tournament_round) as matches_with_rounds,
     COUNT(*) - COUNT(tournament_round) as null_rounds
   FROM matches
   "
   ```

9. **Test query patterns for filtering:**
   ```bash
   # Winners Round 1 matches
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT COUNT(*) FROM matches WHERE tournament_round = 1
   "

   # All Winners Bracket
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT COUNT(*) FROM matches WHERE tournament_round > 0
   "

   # All Losers Bracket
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT COUNT(*) FROM matches WHERE tournament_round < 0
   "
   ```

**Success Criteria:**
- Import completes without errors
- tournament_round populated for matches with challonge_match_id
- Round numbers are reasonable
- Can filter by round and bracket
- No crashes or API errors

**Troubleshooting:**

**Problem:** All tournament_round are NULL

**Check:**
```bash
grep "Challonge" import_with_rounds.log
```

**Possible causes:**
- API credentials missing → Check .env file
- API call failed → Check network/API status
- Wrong tournament_url → Check hardcoded "owduels2025"

**Problem:** Import crashes with API error

**Solution:**
- API should fail gracefully
- Check error handling in `fetch_tournament_rounds()`
- Verify try/except returns empty dict on error

**Problem:** Wrong round numbers

**Check:**
```bash
# Compare with Challonge directly
uv run python scripts/list_matches_without_saves.py | head -20
```

**Commit Message:**
```
test: Verify full import with tournament round data

- Test import with real save files
- Verify Challonge API integration
- Confirm round data populated correctly
- Document expected round distribution
```

---

### Task 8: Update CLAUDE.md Documentation

**File:** `CLAUDE.md`

**What:** Document the new tournament_round field for future reference

**Why:** Help future developers understand the feature

**Dependencies:** Tasks 1-7 complete

**Estimated Time:** 10 minutes

**Steps:**

1. **Find the "Database Management" section** in CLAUDE.md

2. **Add subsection about tournament rounds:**

   After the "### Yield Value Display Scale" section, add:

   ```markdown
   ### Tournament Round Tracking

   **Tournament rounds are fetched from the Challonge API during import.**

   **Storage Format:**
   - Stored in `matches.tournament_round` as INTEGER
   - Values are signed: positive = Winners Bracket, negative = Losers Bracket
   - NULL = missing challonge_match_id or API failure

   **Examples:**
   - `tournament_round = 1` → Winners Round 1
   - `tournament_round = 3` → Winners Round 3 (Semifinals)
   - `tournament_round = -1` → Losers Round 1
   - `tournament_round = -5` → Losers Round 5
   - `tournament_round = NULL` → Unknown

   **Deriving Bracket in Queries:**
   ```sql
   SELECT
     tournament_round,
     CASE
       WHEN tournament_round > 0 THEN 'Winners'
       WHEN tournament_round < 0 THEN 'Losers'
       ELSE 'Unknown'
     END as bracket
   FROM matches
   ```

   **API Integration:**
   - Requires Challonge API credentials in `.env`
   - Fetches all rounds once at import start (cached in memory)
   - Fails gracefully if API unavailable (stores NULL)

   **See Also:**
   - `docs/migrations/010_add_tournament_round.md` - Implementation details
   - `scripts/list_matches_without_saves.py` - Example Challonge API usage
   ```

3. **Save and review:**
   ```bash
   # Check formatting
   cat CLAUDE.md | grep -A20 "Tournament Round Tracking"
   ```

**Success Criteria:**
- Documentation clear and concise
- Examples provided
- Links to related docs

**Commit Message:**
```
docs: Document tournament round tracking in CLAUDE.md

- Explain signed integer format
- Show bracket derivation query
- Document API integration
- Link to migration docs
```

---

## Testing Strategy

### Unit Tests

**What to test:**
- `fetch_tournament_rounds()` returns correct format
- Empty dict on API failure
- Round cache initialization
- Round lookup logic

**Files:**
- `tests/test_challonge_integration.py`
- `tests/test_etl_round_integration.py`

### Integration Tests

**What to test:**
- Full import with round data
- Database correctly populated
- NULL handling for missing data
- Query filtering by round/bracket

**Method:**
- Task 7 (manual import testing)

### Edge Cases to Test

1. **No API credentials** → Should continue with NULL
2. **API call fails** → Should continue with NULL
3. **Match not in cache** → Should log warning, store NULL
4. **No challonge_match_id** → Should store NULL
5. **Round = 0** → Handle correctly (might be valid)

## Validation Checklist

After completing all tasks, verify:

- [ ] Column exists in schema
- [ ] Index exists
- [ ] Import completes without errors
- [ ] Round data populated where challonge_match_id exists
- [ ] NULL stored when data unavailable
- [ ] Can filter matches by round
- [ ] Can derive bracket from round
- [ ] Documentation complete
- [ ] Tests pass
- [ ] Migration documented

## Common Issues and Solutions

### Issue: API Rate Limiting

**Symptom:** API calls fail after several requests

**Solution:** We fetch once at import start, so this shouldn't happen. If it does:
- Reduce tournament_url to smaller tournament for testing
- Add retry logic with exponential backoff
- Cache API responses to disk

### Issue: Wrong Tournament URL

**Symptom:** No rounds found for any matches

**Solution:**
- Check hardcoded `tournament_url` in `fetch_tournament_rounds()`
- Verify against actual tournament URL on Challonge
- Consider making it configurable

### Issue: Round Numbers Don't Make Sense

**Symptom:** Round 100 or other weird values

**Solution:**
- Check Challonge API response format
- Verify we're reading correct field
- Check if Challonge API changed

### Issue: Database Lock During Import

**Symptom:** Cannot query database during import

**Solution:**
- This is expected (write lock)
- Wait for import to finish
- Or open separate read-only connection

## Performance Considerations

**API Call:** ~500ms per call
- **Impact:** One-time cost at import start
- **Optimization:** Already cached

**Database Insert:** ~1ms per row with new column
- **Impact:** Negligible (same as before)
- **Optimization:** Not needed

**Index Maintenance:** ~10ms per index update
- **Impact:** Minimal, standard DuckDB performance
- **Optimization:** Not needed

**Memory:** Cache size = ~8 bytes × match count
- **Impact:** Negligible (e.g., 100 matches = 800 bytes)
- **Optimization:** Not needed

## Future Enhancements (Out of Scope)

After this implementation, consider:

1. **Backfill script** - Populate existing NULL rounds
2. **Tournament URL configuration** - Make configurable vs hardcoded
3. **Round name display** - "Finals", "Semifinals" instead of numbers
4. **API response caching** - Disk cache for offline imports
5. **Multiple tournaments** - Support importing from multiple tournaments

## Related Documentation

- [Challonge API Docs](https://api.challonge.com/v1)
- [chyllonge Library](https://github.com/fp12/chyllonge)
- [DuckDB ALTER TABLE](https://duckdb.org/docs/sql/statements/alter_table.html)
- [Migration 010](../migrations/010_add_tournament_round.md)

## Glossary

**Challonge:** Tournament bracket management platform with REST API

**Double Elimination:** Tournament format with winners and losers brackets

**Winners Bracket:** Main bracket for teams that haven't lost

**Losers Bracket:** Secondary bracket for teams with one loss

**Round Number:** Integer representing tournament progression (1, 2, 3, ...)

**ETL:** Extract, Transform, Load - data pipeline pattern

**TDD:** Test-Driven Development - write tests before code

**DRY:** Don't Repeat Yourself - avoid duplicate code/data

**YAGNI:** You Ain't Gonna Need It - don't add unused features
