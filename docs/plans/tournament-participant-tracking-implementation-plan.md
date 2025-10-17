# Tournament Participant Tracking Implementation Plan

## Overview

Add a tournament participant tracking system that links players across multiple matches using Challonge API data. This enables cross-match analytics, persistent player identity, and bracket integration.

## Background

### Current Problem

Currently, each save file generates independent player IDs:
- **Match 8**: Ninja (player_id=15) vs Fiddler (player_id=16)
- **Match 9**: Ninja (player_id=17) vs Auro (player_id=18)

The database treats these as four completely separate entities. We cannot:
- Track individual performance across multiple matches
- Calculate per-person win rates or statistics
- Link save file results back to the tournament bracket
- Identify that "Ninja" in two different matches is the same person

### Solution

Create a two-tier identity system:
1. **Match-scoped players** (current): Each save file has independent player_ids
2. **Tournament participants** (new): Persistent identity across all matches

This is accomplished by:
1. Importing Challonge participant and match data
2. Linking save file players to Challonge participants by name matching
3. Enabling cross-match queries via the participant_id foreign key

### Challonge API Data

**Participants endpoint** provides:
```json
{
  "id": 270990513,                    // Unique tournament participant ID
  "name": "FluffybunnyMohawk",        // Display name
  "challonge_username": "FluffybunnyMohawk",
  "challonge_user_id": 6946236,       // Challonge account ID (persistent across tournaments)
  "seed": 1,
  "final_rank": null
}
```

**Matches endpoint** provides:
```json
{
  "id": 426504750,         // Match ID (already stored in matches.challonge_match_id)
  "player1_id": 270990513, // Participant ID for player 1
  "player2_id": 270990514, // Participant ID for player 2
  "winner_id": 270990513
}
```

### Name Matching Strategy

**The Core Challenge**: Link save file player names to Challonge participant names.

**Examples of matching complexity**:
- Exact match: "Ninja" → "Ninja"
- Case differences: "ninja" → "Ninja"
- Whitespace: " Ninja " → "Ninja"
- Clan tags: "Ninja [OW]" → "Ninja"
- Special characters: "Ninja_OW" → "Ninja"

**Approach**: Normalize both sides and match:
1. Strip whitespace
2. Convert to lowercase
3. Remove special characters
4. Store normalized name for fast matching
5. Keep original display name for UI

**Fallback**: Manual override table for edge cases

### Why This Design?

**DRY**: Reuse existing Challonge API integration (chyllonge library)
**YAGNI**: Only implement single-tournament tracking now, not multi-tournament
**Minimal changes**: Add new tables without modifying existing schema
**Backward compatible**: All existing queries still work, participant_id is nullable

## Database Schema

### New Table: `tournament_participants`

```sql
CREATE TABLE tournament_participants (
    participant_id BIGINT PRIMARY KEY,           -- Challonge participant ID
    display_name VARCHAR NOT NULL,               -- "FluffybunnyMohawk"
    display_name_normalized VARCHAR NOT NULL,    -- "fluffybunnymohawk" (for matching)
    challonge_username VARCHAR,                  -- Challonge account username
    challonge_user_id BIGINT,                    -- Challonge account ID
    seed INTEGER,
    final_rank INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX idx_participants_normalized ON tournament_participants(display_name_normalized);
```

### Update Existing Table: `matches`

Add participant ID fields to track which participants played in each match:

```sql
ALTER TABLE matches ADD COLUMN player1_participant_id BIGINT REFERENCES tournament_participants(participant_id);
ALTER TABLE matches ADD COLUMN player2_participant_id BIGINT REFERENCES tournament_participants(participant_id);
ALTER TABLE matches ADD COLUMN winner_participant_id BIGINT REFERENCES tournament_participants(participant_id);
```

### Update Existing Table: `players`

Add foreign key to link save file players to tournament participants:

```sql
ALTER TABLE players ADD COLUMN participant_id BIGINT REFERENCES tournament_participants(participant_id);

CREATE INDEX idx_players_participant ON players(participant_id);
```

### New Table: `participant_name_overrides`

Manual mapping for cases where automatic name matching fails:

```sql
CREATE TABLE participant_name_overrides (
    override_id INTEGER PRIMARY KEY,
    match_id BIGINT NOT NULL,
    save_file_player_name VARCHAR NOT NULL,    -- Name from save file
    participant_id BIGINT NOT NULL,            -- Correct participant ID
    reason VARCHAR,                             -- Why override needed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (participant_id) REFERENCES tournament_participants(participant_id),
    UNIQUE(match_id, save_file_player_name)
);
```

### Example Data

**tournament_participants:**
```
participant_id | display_name      | display_name_normalized | challonge_user_id | seed
---------------|-------------------|-------------------------|-------------------|------
270990513      | FluffybunnyMohawk | fluffybunnymohawk      | 6946236           | 1
270990514      | Ninja             | ninja                  | 7123456           | 2
270990515      | Auro              | auro                   | 8234567           | 3
```

**matches (updated):**
```
match_id | challonge_match_id | player1_participant_id | player2_participant_id | winner_participant_id
---------|--------------------|-----------------------|-----------------------|----------------------
8        | 426504750          | 270990514             | 270990516             | 270990514
9        | 426504723          | 270990514             | 270990515             | 270990515
```

**players (updated):**
```
player_id | match_id | player_name | participant_id
----------|----------|-------------|---------------
15        | 8        | Ninja       | 270990514
16        | 8        | Fiddler     | 270990516
17        | 9        | Ninja       | 270990514  (same participant!)
18        | 9        | Auro        | 270990515
```

## Implementation Tasks

### Task 1: Create Database Migration Document

**Objective**: Document all schema changes in a migration document.

**Files to Create**:
- `docs/migrations/004_add_tournament_participants.md`

**Migration Document Content**:

```markdown
# Migration 004: Add Tournament Participant Tracking

## Overview
Adds tournament participant tracking to link players across multiple matches using Challonge API data.

## Schema Changes

### New Table: `tournament_participants`

```sql
CREATE TABLE tournament_participants (
    participant_id BIGINT PRIMARY KEY,
    display_name VARCHAR NOT NULL,
    display_name_normalized VARCHAR NOT NULL,
    challonge_username VARCHAR,
    challonge_user_id BIGINT,
    seed INTEGER,
    final_rank INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX idx_participants_normalized ON tournament_participants(display_name_normalized);
```

### New Table: `participant_name_overrides`

```sql
CREATE TABLE participant_name_overrides (
    override_id INTEGER PRIMARY KEY,
    match_id BIGINT NOT NULL,
    save_file_player_name VARCHAR NOT NULL,
    participant_id BIGINT NOT NULL,
    reason VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (participant_id) REFERENCES tournament_participants(participant_id),
    UNIQUE(match_id, save_file_player_name)
);
```

### Alter Table: `matches`

```sql
ALTER TABLE matches ADD COLUMN player1_participant_id BIGINT;
ALTER TABLE matches ADD COLUMN player2_participant_id BIGINT;
ALTER TABLE matches ADD COLUMN winner_participant_id BIGINT;
```

Note: Foreign key constraints will be added after participants are populated.

### Alter Table: `players`

```sql
ALTER TABLE players ADD COLUMN participant_id BIGINT;

CREATE INDEX idx_players_participant ON players(participant_id);
```

Note: Foreign key constraint will be added after participants are populated.

## SQL Migration Script

```sql
-- Create tournament_participants table
CREATE TABLE IF NOT EXISTS tournament_participants (
    participant_id BIGINT PRIMARY KEY,
    display_name VARCHAR NOT NULL,
    display_name_normalized VARCHAR NOT NULL,
    challonge_username VARCHAR,
    challonge_user_id BIGINT,
    seed INTEGER,
    final_rank INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_participants_normalized
ON tournament_participants(display_name_normalized);

-- Create participant_name_overrides table
CREATE TABLE IF NOT EXISTS participant_name_overrides (
    override_id INTEGER PRIMARY KEY,
    match_id BIGINT NOT NULL,
    save_file_player_name VARCHAR NOT NULL,
    participant_id BIGINT NOT NULL,
    reason VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (participant_id) REFERENCES tournament_participants(participant_id),
    UNIQUE(match_id, save_file_player_name)
);

-- Add participant tracking to matches table
ALTER TABLE matches ADD COLUMN IF NOT EXISTS player1_participant_id BIGINT;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS player2_participant_id BIGINT;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS winner_participant_id BIGINT;

-- Add participant tracking to players table
ALTER TABLE players ADD COLUMN IF NOT EXISTS participant_id BIGINT;

CREATE INDEX IF NOT EXISTS idx_players_participant ON players(participant_id);

-- Record migration
INSERT INTO schema_migrations (version, description, applied_at)
VALUES (4, 'Add tournament participant tracking', CURRENT_TIMESTAMP);
```

## Rollback Procedure

```sql
-- Drop indexes
DROP INDEX IF EXISTS idx_players_participant;
DROP INDEX IF EXISTS idx_participants_normalized;

-- Remove columns from players table
ALTER TABLE players DROP COLUMN IF EXISTS participant_id;

-- Remove columns from matches table
ALTER TABLE matches DROP COLUMN IF EXISTS winner_participant_id;
ALTER TABLE matches DROP COLUMN IF EXISTS player2_participant_id;
ALTER TABLE matches DROP COLUMN IF EXISTS player1_participant_id;

-- Drop tables
DROP TABLE IF EXISTS participant_name_overrides;
DROP TABLE IF EXISTS tournament_participants;

-- Remove migration record
DELETE FROM schema_migrations WHERE version = 4;
```

## Verification

After applying migration:

```sql
-- Verify tables exist
SELECT name FROM sqlite_master WHERE type='table'
AND name IN ('tournament_participants', 'participant_name_overrides');

-- Verify columns added
PRAGMA table_info(matches);
PRAGMA table_info(players);

-- Verify indexes
PRAGMA index_list(tournament_participants);
PRAGMA index_list(players);

-- Verify migration recorded
SELECT * FROM schema_migrations WHERE version = 4;
```

## Related Files
- Challonge sync: `scripts/sync_challonge_participants.py` (new)
- Name matching: `tournament_visualizer/data/participant_matcher.py` (new)
- Database operations: `tournament_visualizer/data/database.py`
- ETL: `tournament_visualizer/data/etl.py`

## Data Population Order

1. Apply schema migration
2. Import Challonge participants (new script)
3. Update matches with participant IDs (new script)
4. Link players to participants via name matching (new script)
5. Verify all linkages

## Notes

- participant_id is nullable in players table (backward compatible)
- Name matching is fuzzy - manual overrides may be needed
- All queries work without participant data (optional enhancement)
```

**Testing**:
```bash
# Test SQL syntax
uv run duckdb :memory: < migration_sql_file.sql
```

**Commit Message**:
```
docs: Add migration plan for tournament participant tracking

Documents schema changes for linking players across matches using
Challonge participant data, including foreign keys and indexes.
```

---

### Task 2: Update Database Schema Initialization

**Objective**: Add new tables to database initialization code.

**Files to Modify**:
- `tournament_visualizer/data/database.py`

**Location**: Find the `create_tables()` or `initialize_database()` method.

**Code Changes**:

Add after existing table creation code:

```python
# Add this to the create_tables() method:

# Tournament participants table
conn.execute("""
    CREATE TABLE IF NOT EXISTS tournament_participants (
        participant_id BIGINT PRIMARY KEY,
        display_name VARCHAR NOT NULL,
        display_name_normalized VARCHAR NOT NULL,
        challonge_username VARCHAR,
        challonge_user_id BIGINT,
        seed INTEGER,
        final_rank INTEGER,
        created_at TIMESTAMP,
        updated_at TIMESTAMP
    )
""")

conn.execute("""
    CREATE INDEX IF NOT EXISTS idx_participants_normalized
    ON tournament_participants(display_name_normalized)
""")

# Participant name overrides table
conn.execute("""
    CREATE TABLE IF NOT EXISTS participant_name_overrides (
        override_id INTEGER PRIMARY KEY,
        match_id BIGINT NOT NULL,
        save_file_player_name VARCHAR NOT NULL,
        participant_id BIGINT NOT NULL,
        reason VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (match_id) REFERENCES matches(match_id),
        FOREIGN KEY (participant_id) REFERENCES tournament_participants(participant_id),
        UNIQUE(match_id, save_file_player_name)
    )
""")
```

**Testing**:
```bash
# Remove existing database
rm data/tournament_data.duckdb

# Create new database with updated schema
uv run python -c "
from tournament_visualizer.data.database import TournamentDatabase
db = TournamentDatabase()
db.close()
"

# Verify new tables exist
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT name FROM sqlite_master
WHERE type='table'
AND name IN ('tournament_participants', 'participant_name_overrides')
"

# Verify tournament_participants schema
uv run duckdb data/tournament_data.duckdb -readonly -c "DESCRIBE tournament_participants"
```

**Commit Message**:
```
feat: Add tournament participant tables to database schema

Adds tournament_participants and participant_name_overrides tables
for tracking player identity across multiple matches.
```

---

### Task 3: Add Schema Migration for Existing Databases

**Objective**: Add participant columns to existing tables.

**Files to Modify**:
- `tournament_visualizer/data/database.py`

**Add New Method**:

```python
def migrate_to_participant_tracking(self) -> None:
    """Migrate existing database to support participant tracking.

    Adds participant_id columns to matches and players tables.
    This migration is idempotent - safe to run multiple times.

    Should be called after database connection is established,
    typically in __init__ or during ETL pipeline startup.
    """
    logger.info("Checking for participant tracking migration...")

    try:
        # Check if migration already applied
        result = self.conn.execute("""
            SELECT COUNT(*)
            FROM schema_migrations
            WHERE version = 4
        """).fetchone()

        if result[0] > 0:
            logger.info("Participant tracking migration already applied")
            return

        logger.info("Applying participant tracking migration...")

        # Add columns to matches table
        # Note: ALTER TABLE ADD COLUMN IF NOT EXISTS not supported in all DuckDB versions
        # Check if columns exist first
        columns_to_add_matches = [
            "player1_participant_id BIGINT",
            "player2_participant_id BIGINT",
            "winner_participant_id BIGINT"
        ]

        for column_def in columns_to_add_matches:
            column_name = column_def.split()[0]
            # Check if column exists
            existing = self.conn.execute(f"""
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_name = 'matches'
                AND column_name = '{column_name}'
            """).fetchone()

            if existing[0] == 0:
                self.conn.execute(f"ALTER TABLE matches ADD COLUMN {column_def}")
                logger.info(f"Added column {column_name} to matches table")

        # Add participant_id to players table
        existing = self.conn.execute("""
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_name = 'players'
            AND column_name = 'participant_id'
        """).fetchone()

        if existing[0] == 0:
            self.conn.execute("ALTER TABLE players ADD COLUMN participant_id BIGINT")
            logger.info("Added participant_id column to players table")

            # Create index
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_players_participant
                ON players(participant_id)
            """)
            logger.info("Created index on players.participant_id")

        # Record migration
        self.conn.execute("""
            INSERT INTO schema_migrations (version, description, applied_at)
            VALUES (4, 'Add tournament participant tracking', CURRENT_TIMESTAMP)
        """)

        logger.info("Participant tracking migration completed successfully")

    except Exception as e:
        logger.error(f"Error during participant tracking migration: {e}")
        raise
```

**Call Migration in __init__**:

Find the `TournamentDatabase.__init__()` method and add:

```python
def __init__(self, db_path: str = None):
    # ... existing initialization code ...

    # Run migrations
    self.migrate_to_participant_tracking()
```

**Testing**:
```bash
# Test migration on existing database
uv run python -c "
from tournament_visualizer.data.database import TournamentDatabase

# Connect to existing database
db = TournamentDatabase('data/tournament_data.duckdb')

# Migration should run automatically
# Check it worked
result = db.conn.execute('''
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = \"players\"
    AND column_name = \"participant_id\"
''').fetchall()

print(f'Migration successful: {len(result) > 0}')
db.close()
"

# Verify migration recorded
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT * FROM schema_migrations WHERE version = 4
"
```

**Commit Message**:
```
feat: Add automatic schema migration for participant tracking

Implements idempotent migration to add participant_id columns
to existing databases. Runs automatically on database connection.
```

---

### Task 4: Create Name Normalization Utility

**Objective**: Create a utility module for normalizing player names for matching.

**Files to Create**:
- `tournament_visualizer/data/name_normalizer.py`

**Implementation**:

```python
"""Name normalization utilities for participant matching.

Provides functions to normalize player/participant names for fuzzy matching
between save file player names and Challonge participant names.
"""

import re
import unicodedata
from typing import Optional


def normalize_name(name: Optional[str]) -> str:
    """Normalize a player/participant name for matching.

    Normalization steps:
    1. Strip whitespace
    2. Convert to lowercase
    3. Remove Unicode accents/diacritics
    4. Remove special characters (keep only alphanumeric)
    5. Collapse multiple spaces to single space
    6. Strip again

    Args:
        name: Player or participant name to normalize

    Returns:
        Normalized name (lowercase, no special chars, no whitespace)
        Empty string if name is None

    Examples:
        >>> normalize_name("FluffybunnyMohawk")
        'fluffybunnymohawk'

        >>> normalize_name("Ninja [OW]")
        'ninjaow'

        >>> normalize_name("  Player_123  ")
        'player123'

        >>> normalize_name("José García")
        'josegarcia'
    """
    if not name:
        return ""

    # Strip leading/trailing whitespace
    normalized = name.strip()

    # Convert to lowercase
    normalized = normalized.lower()

    # Remove Unicode accents/diacritics
    # Decompose Unicode characters, then filter out combining marks
    normalized = unicodedata.normalize('NFKD', normalized)
    normalized = ''.join(
        char for char in normalized
        if not unicodedata.combining(char)
    )

    # Remove all non-alphanumeric characters
    normalized = re.sub(r'[^a-z0-9\s]', '', normalized)

    # Collapse multiple spaces to single space
    normalized = re.sub(r'\s+', ' ', normalized)

    # Final strip and remove all remaining whitespace
    normalized = normalized.strip().replace(' ', '')

    return normalized


def names_match(name1: Optional[str], name2: Optional[str]) -> bool:
    """Check if two names match after normalization.

    Args:
        name1: First name to compare
        name2: Second name to compare

    Returns:
        True if normalized names are equal, False otherwise

    Examples:
        >>> names_match("Ninja", "ninja")
        True

        >>> names_match("Ninja [OW]", "Ninja")
        True

        >>> names_match("FluffyBunny", "Fluffy Bunny")
        True

        >>> names_match("Ninja", "Auro")
        False
    """
    return normalize_name(name1) == normalize_name(name2)


def find_best_match(
    target_name: str,
    candidate_names: dict[str, str],
    require_exact: bool = False
) -> Optional[str]:
    """Find the best matching name from a set of candidates.

    Args:
        target_name: Name to find a match for
        candidate_names: Dict mapping normalized names to original names
        require_exact: If True, only return exact normalized matches

    Returns:
        Original name of best match, or None if no match found

    Note:
        Currently only supports exact normalized matching.
        Future: Could add fuzzy matching (Levenshtein distance, etc.)
    """
    normalized_target = normalize_name(target_name)

    if not normalized_target:
        return None

    # Exact match on normalized name
    if normalized_target in candidate_names:
        return candidate_names[normalized_target]

    # No match found
    return None


def build_name_lookup(names: list[str]) -> dict[str, str]:
    """Build a lookup dictionary from list of names.

    Maps normalized name → original name for fast matching.
    If multiple names normalize to the same value, keeps the first one.

    Args:
        names: List of original names

    Returns:
        Dictionary mapping normalized_name -> original_name

    Example:
        >>> build_name_lookup(["Ninja", "ninja", "Auro"])
        {'ninja': 'Ninja', 'auro': 'Auro'}
    """
    lookup = {}

    for name in names:
        normalized = normalize_name(name)
        if normalized and normalized not in lookup:
            lookup[normalized] = name

    return lookup
```

**Files to Create**:
- `tests/test_name_normalizer.py`

**Test Implementation**:

```python
"""Tests for name normalization utilities."""

import pytest
from tournament_visualizer.data.name_normalizer import (
    normalize_name,
    names_match,
    find_best_match,
    build_name_lookup,
)


class TestNormalizeName:
    """Tests for normalize_name() function."""

    def test_normalize_basic(self):
        """Test basic normalization."""
        assert normalize_name("Ninja") == "ninja"

    def test_normalize_whitespace(self):
        """Test whitespace handling."""
        assert normalize_name("  Ninja  ") == "ninja"
        assert normalize_name("Fluffy Bunny") == "fluffybunny"
        assert normalize_name("Player   Name") == "playername"

    def test_normalize_special_chars(self):
        """Test special character removal."""
        assert normalize_name("Ninja [OW]") == "ninjaow"
        assert normalize_name("Player_123") == "player123"
        assert normalize_name("Test-Name!") == "testname"

    def test_normalize_unicode(self):
        """Test Unicode character handling."""
        assert normalize_name("José") == "jose"
        assert normalize_name("García") == "garcia"
        assert normalize_name("Müller") == "muller"

    def test_normalize_empty(self):
        """Test empty/None handling."""
        assert normalize_name("") == ""
        assert normalize_name(None) == ""
        assert normalize_name("   ") == ""

    def test_normalize_case(self):
        """Test case insensitivity."""
        assert normalize_name("NINJA") == "ninja"
        assert normalize_name("NiNjA") == "ninja"
        assert normalize_name("ninja") == "ninja"


class TestNamesMatch:
    """Tests for names_match() function."""

    def test_exact_match(self):
        """Test exact name matching."""
        assert names_match("Ninja", "Ninja") is True

    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        assert names_match("Ninja", "ninja") is True
        assert names_match("NINJA", "ninja") is True

    def test_whitespace_match(self):
        """Test whitespace normalization."""
        assert names_match("Ninja", " Ninja ") is True
        assert names_match("Fluffy Bunny", "FluffyBunny") is True

    def test_special_char_match(self):
        """Test special character handling."""
        assert names_match("Ninja [OW]", "Ninja") is True
        assert names_match("Player_123", "Player 123") is True

    def test_no_match(self):
        """Test non-matching names."""
        assert names_match("Ninja", "Auro") is False
        assert names_match("FluffyBunny", "Ninja") is False

    def test_empty_names(self):
        """Test empty name handling."""
        assert names_match("", "") is True
        assert names_match(None, None) is True
        assert names_match("Ninja", None) is False
        assert names_match(None, "Ninja") is False


class TestFindBestMatch:
    """Tests for find_best_match() function."""

    def test_exact_match(self):
        """Test finding exact match."""
        candidates = build_name_lookup(["Ninja", "Auro", "FluffyBunny"])

        result = find_best_match("Ninja", candidates)
        assert result == "Ninja"

    def test_case_insensitive_match(self):
        """Test case-insensitive matching."""
        candidates = build_name_lookup(["Ninja", "Auro"])

        result = find_best_match("ninja", candidates)
        assert result == "Ninja"

    def test_special_char_match(self):
        """Test matching with special characters."""
        candidates = build_name_lookup(["Ninja", "Auro"])

        result = find_best_match("Ninja [OW]", candidates)
        assert result == "Ninja"

    def test_no_match(self):
        """Test when no match exists."""
        candidates = build_name_lookup(["Ninja", "Auro"])

        result = find_best_match("Unknown", candidates)
        assert result is None

    def test_empty_candidates(self):
        """Test with empty candidate list."""
        result = find_best_match("Ninja", {})
        assert result is None


class TestBuildNameLookup:
    """Tests for build_name_lookup() function."""

    def test_basic_lookup(self):
        """Test basic lookup building."""
        names = ["Ninja", "Auro", "FluffyBunny"]
        lookup = build_name_lookup(names)

        assert lookup["ninja"] == "Ninja"
        assert lookup["auro"] == "Auro"
        assert lookup["fluffybunny"] == "FluffyBunny"

    def test_duplicate_normalized(self):
        """Test handling of names that normalize to same value."""
        names = ["Ninja", "ninja", "NINJA"]
        lookup = build_name_lookup(names)

        # Should keep first occurrence
        assert lookup["ninja"] == "Ninja"
        assert len(lookup) == 1

    def test_empty_names(self):
        """Test with empty name list."""
        lookup = build_name_lookup([])
        assert lookup == {}

    def test_ignores_empty_strings(self):
        """Test that empty strings are ignored."""
        names = ["Ninja", "", None, "Auro"]
        lookup = build_name_lookup(names)

        assert len(lookup) == 2
        assert "ninja" in lookup
        assert "auro" in lookup
```

**Testing**:
```bash
# Run tests
uv run pytest tests/test_name_normalizer.py -v

# Check coverage
uv run pytest tests/test_name_normalizer.py --cov=tournament_visualizer.data.name_normalizer --cov-report=term-missing
```

**Commit Messages**:
```
feat: Add name normalization utility for participant matching

Implements robust name normalization for fuzzy matching between
save file players and Challonge participants. Handles case,
whitespace, special characters, and Unicode.
```

```
test: Add comprehensive tests for name normalization

Tests cover basic normalization, Unicode handling, fuzzy matching,
and edge cases like empty names and duplicates.
```

---

### Task 5: Create Challonge Participant Sync Script

**Objective**: Create a script to download and import Challonge participant data.

**Files to Create**:
- `scripts/sync_challonge_participants.py`

**Implementation**:

```python
#!/usr/bin/env python3
"""Sync Challonge participant data to database.

Downloads tournament participants from Challonge API and stores them
in the tournament_participants table. Also updates matches table with
participant IDs for player1, player2, and winner.

This script should be run:
1. After database schema migration
2. Before importing save files
3. Whenever tournament participants change
"""

import os
import sys
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from chyllonge.api import ChallongeApi
from dotenv import load_dotenv

from tournament_visualizer.config import Config
from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.name_normalizer import normalize_name


def load_config() -> str:
    """Load tournament ID from environment variables.

    Returns:
        Tournament ID string

    Raises:
        ValueError: If required environment variables are missing
    """
    load_dotenv()

    tournament_id = os.getenv("challonge_tournament_id")

    if not tournament_id:
        raise ValueError(
            "challonge_tournament_id not found in environment variables"
        )

    if not os.getenv("CHALLONGE_KEY"):
        raise ValueError("CHALLONGE_KEY not found in environment variables")

    if not os.getenv("CHALLONGE_USER"):
        raise ValueError("CHALLONGE_USER not found in environment variables")

    return tournament_id


def fetch_participants(api: ChallongeApi, tournament_id: str) -> list[dict[str, Any]]:
    """Fetch all participants from Challonge tournament.

    Args:
        api: Challonge API client
        tournament_id: Tournament ID

    Returns:
        List of participant dictionaries
    """
    print(f"Fetching participants for tournament {tournament_id}...")

    try:
        participants = api.participants.get_all(tournament_id)
        print(f"Found {len(participants)} participants")
        return participants
    except Exception as e:
        print(f"Error fetching participants: {e}")
        return []


def fetch_matches(api: ChallongeApi, tournament_id: str) -> list[dict[str, Any]]:
    """Fetch all matches from Challonge tournament.

    Args:
        api: Challonge API client
        tournament_id: Tournament ID

    Returns:
        List of match dictionaries
    """
    print(f"Fetching matches for tournament {tournament_id}...")

    try:
        matches = api.matches.get_all(tournament_id)
        print(f"Found {len(matches)} matches")
        return matches
    except Exception as e:
        print(f"Error fetching matches: {e}")
        return []


def insert_participants(
    db: TournamentDatabase,
    participants: list[dict[str, Any]]
) -> int:
    """Insert participants into database.

    Args:
        db: Database instance
        participants: List of participant data from Challonge

    Returns:
        Number of participants inserted
    """
    if not participants:
        print("No participants to insert")
        return 0

    print(f"Inserting {len(participants)} participants...")

    # Clear existing participants (full refresh)
    db.conn.execute("DELETE FROM tournament_participants")

    inserted = 0

    for participant in participants:
        try:
            participant_id = participant.get("id")
            display_name = participant.get("display_name") or participant.get("name")

            if not participant_id or not display_name:
                print(f"Skipping participant with missing ID or name: {participant}")
                continue

            # Normalize name for matching
            normalized_name = normalize_name(display_name)

            db.conn.execute(
                """
                INSERT INTO tournament_participants (
                    participant_id,
                    display_name,
                    display_name_normalized,
                    challonge_username,
                    challonge_user_id,
                    seed,
                    final_rank,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    participant_id,
                    display_name,
                    normalized_name,
                    participant.get("challonge_username"),
                    participant.get("challonge_user_id"),
                    participant.get("seed"),
                    participant.get("final_rank"),
                    participant.get("created_at"),
                    participant.get("updated_at"),
                ),
            )

            inserted += 1

        except Exception as e:
            print(f"Error inserting participant {participant.get('id')}: {e}")
            continue

    print(f"Inserted {inserted} participants")
    return inserted


def update_match_participants(
    db: TournamentDatabase,
    challonge_matches: list[dict[str, Any]]
) -> tuple[int, int]:
    """Update matches table with participant IDs.

    Links matches to participants by matching challonge_match_id.

    Args:
        db: Database instance
        challonge_matches: List of match data from Challonge

    Returns:
        Tuple of (matches_updated, matches_not_found)
    """
    if not challonge_matches:
        print("No Challonge matches to process")
        return 0, 0

    print(f"Updating {len(challonge_matches)} matches with participant IDs...")

    updated = 0
    not_found = 0

    for challonge_match in challonge_matches:
        challonge_match_id = challonge_match.get("id")

        if not challonge_match_id:
            continue

        # Check if this match exists in our database
        result = db.conn.execute(
            "SELECT match_id FROM matches WHERE challonge_match_id = ?",
            (challonge_match_id,)
        ).fetchone()

        if not result:
            not_found += 1
            continue

        match_id = result[0]

        # Update with participant IDs
        player1_participant_id = challonge_match.get("player1_id")
        player2_participant_id = challonge_match.get("player2_id")
        winner_participant_id = challonge_match.get("winner_id")

        db.conn.execute(
            """
            UPDATE matches
            SET player1_participant_id = ?,
                player2_participant_id = ?,
                winner_participant_id = ?
            WHERE match_id = ?
            """,
            (
                player1_participant_id,
                player2_participant_id,
                winner_participant_id,
                match_id,
            ),
        )

        updated += 1

    print(f"Updated {updated} matches")
    if not_found > 0:
        print(f"Warning: {not_found} Challonge matches not found in database")

    return updated, not_found


def print_summary(db: TournamentDatabase) -> None:
    """Print summary of participant data.

    Args:
        db: Database instance
    """
    print("\n" + "=" * 60)
    print("PARTICIPANT SYNC SUMMARY")
    print("=" * 60)

    # Total participants
    total = db.conn.execute(
        "SELECT COUNT(*) FROM tournament_participants"
    ).fetchone()[0]

    print(f"\nTotal participants: {total}")

    # Participants with Challonge accounts
    with_accounts = db.conn.execute(
        "SELECT COUNT(*) FROM tournament_participants WHERE challonge_user_id IS NOT NULL"
    ).fetchone()[0]

    print(f"With Challonge accounts: {with_accounts}")

    # Matches with participant data
    matches_with_participants = db.conn.execute(
        """
        SELECT COUNT(*)
        FROM matches
        WHERE player1_participant_id IS NOT NULL
        AND player2_participant_id IS NOT NULL
        """
    ).fetchone()[0]

    total_matches = db.conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]

    print(f"\nMatches with participant data: {matches_with_participants}/{total_matches}")

    # Sample participants
    print("\nSample participants:")
    samples = db.conn.execute(
        """
        SELECT display_name, seed, challonge_username
        FROM tournament_participants
        ORDER BY seed
        LIMIT 10
        """
    ).fetchall()

    for display_name, seed, username in samples:
        username_str = f" (@{username})" if username else ""
        print(f"  Seed {seed}: {display_name}{username_str}")

    print("=" * 60)


def main() -> None:
    """Main function."""
    try:
        # Load configuration
        tournament_id = load_config()

        # Create Challonge API client
        api = ChallongeApi()

        # Fetch data from Challonge
        participants = fetch_participants(api, tournament_id)
        matches = fetch_matches(api, tournament_id)

        if not participants:
            print("No participants found. Exiting.")
            sys.exit(1)

        # Connect to database
        db = TournamentDatabase(Config.DATABASE_PATH)

        # Insert participants
        insert_participants(db, participants)

        # Update matches with participant IDs
        update_match_participants(db, matches)

        # Print summary
        print_summary(db)

        db.close()

        print("\nParticipant sync complete!")

    except ValueError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Testing**:
```bash
# Run the script
uv run python scripts/sync_challonge_participants.py

# Verify data
uv run duckdb data/tournament_data.duckdb -readonly -c "SELECT COUNT(*) FROM tournament_participants"

# Check sample data
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT display_name, display_name_normalized, seed
FROM tournament_participants
ORDER BY seed
LIMIT 10
"

# Verify matches updated
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT COUNT(*)
FROM matches
WHERE player1_participant_id IS NOT NULL
"
```

**Commit Message**:
```
feat: Add Challonge participant sync script

Downloads tournament participants from Challonge API and populates
tournament_participants table. Updates matches with participant IDs
for bracket integration.
```

---

### Task 6: Create Participant Matching Module

**Objective**: Create a module to link save file players to Challonge participants.

**Files to Create**:
- `tournament_visualizer/data/participant_matcher.py`

**Implementation**:

```python
"""Participant matching logic.

Links save file players to tournament participants using name matching
and manual overrides.
"""

import logging
from typing import Any, Optional

from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.name_normalizer import (
    normalize_name,
    build_name_lookup,
    find_best_match,
)

logger = logging.getLogger(__name__)


class ParticipantMatcher:
    """Matches save file players to tournament participants."""

    def __init__(self, db: TournamentDatabase):
        """Initialize matcher with database connection.

        Args:
            db: Database instance
        """
        self.db = db
        self._participant_lookup: Optional[dict[str, tuple[int, str]]] = None
        self._override_cache: dict[tuple[int, str], int] = {}

    def _load_participants(self) -> None:
        """Load participant data and build lookup table.

        Creates mapping: normalized_name -> (participant_id, display_name)
        """
        if self._participant_lookup is not None:
            return  # Already loaded

        logger.info("Loading tournament participants for matching...")

        participants = self.db.conn.execute(
            """
            SELECT participant_id, display_name, display_name_normalized
            FROM tournament_participants
            """
        ).fetchall()

        # Build lookup: normalized_name -> (participant_id, display_name)
        self._participant_lookup = {}

        for participant_id, display_name, normalized_name in participants:
            if normalized_name and normalized_name not in self._participant_lookup:
                self._participant_lookup[normalized_name] = (participant_id, display_name)

        logger.info(f"Loaded {len(self._participant_lookup)} participants for matching")

    def _load_overrides(self, match_id: int) -> None:
        """Load name overrides for a specific match.

        Args:
            match_id: Match ID to load overrides for
        """
        overrides = self.db.conn.execute(
            """
            SELECT save_file_player_name, participant_id
            FROM participant_name_overrides
            WHERE match_id = ?
            """,
            (match_id,)
        ).fetchall()

        for save_name, participant_id in overrides:
            cache_key = (match_id, save_name)
            self._override_cache[cache_key] = participant_id

        if overrides:
            logger.info(f"Loaded {len(overrides)} name overrides for match {match_id}")

    def match_player(
        self,
        match_id: int,
        player_name: str,
        allow_override: bool = True
    ) -> Optional[int]:
        """Match a save file player name to a participant ID.

        Matching priority:
        1. Manual override (if allow_override=True)
        2. Normalized name match

        Args:
            match_id: Match ID (for override lookup)
            player_name: Player name from save file
            allow_override: Whether to check override table

        Returns:
            Participant ID if match found, None otherwise
        """
        if not player_name:
            return None

        # Ensure participant data is loaded
        self._load_participants()

        # Check override first
        if allow_override:
            # Load overrides for this match if not cached
            cache_key = (match_id, player_name)
            if cache_key not in self._override_cache:
                self._load_overrides(match_id)

            if cache_key in self._override_cache:
                participant_id = self._override_cache[cache_key]
                logger.debug(
                    f"Using override: '{player_name}' -> participant {participant_id}"
                )
                return participant_id

        # Try normalized name matching
        normalized_player_name = normalize_name(player_name)

        if normalized_player_name in self._participant_lookup:
            participant_id, display_name = self._participant_lookup[normalized_player_name]
            logger.debug(
                f"Matched '{player_name}' -> '{display_name}' "
                f"(participant {participant_id})"
            )
            return participant_id

        # No match found
        logger.warning(
            f"No participant match found for player '{player_name}' in match {match_id}"
        )
        return None

    def link_match_players(self, match_id: int) -> dict[str, Any]:
        """Link all players in a match to participants.

        Updates the players table with participant_id for all players
        in the specified match.

        Args:
            match_id: Match ID to process

        Returns:
            Dictionary with matching statistics:
                - total_players: Total players in match
                - matched: Number of players successfully matched
                - unmatched: Number of players without matches
                - unmatched_names: List of unmatched player names
        """
        logger.info(f"Linking players to participants for match {match_id}")

        # Get all players for this match
        players = self.db.conn.execute(
            """
            SELECT player_id, player_name
            FROM players
            WHERE match_id = ?
            """,
            (match_id,)
        ).fetchall()

        if not players:
            logger.warning(f"No players found for match {match_id}")
            return {
                "total_players": 0,
                "matched": 0,
                "unmatched": 0,
                "unmatched_names": []
            }

        matched = 0
        unmatched_names = []

        for player_id, player_name in players:
            participant_id = self.match_player(match_id, player_name)

            if participant_id:
                # Update player with participant_id
                self.db.conn.execute(
                    """
                    UPDATE players
                    SET participant_id = ?
                    WHERE player_id = ?
                    """,
                    (participant_id, player_id)
                )
                matched += 1
            else:
                unmatched_names.append(player_name)

        stats = {
            "total_players": len(players),
            "matched": matched,
            "unmatched": len(unmatched_names),
            "unmatched_names": unmatched_names
        }

        if matched == len(players):
            logger.info(
                f"Successfully matched all {matched} players in match {match_id}"
            )
        else:
            logger.warning(
                f"Match {match_id}: {matched}/{len(players)} players matched. "
                f"Unmatched: {unmatched_names}"
            )

        return stats

    def link_all_matches(self) -> dict[str, Any]:
        """Link players to participants for all matches in database.

        Returns:
            Dictionary with overall statistics:
                - total_matches: Total matches processed
                - total_players: Total players across all matches
                - matched_players: Total players successfully matched
                - unmatched_players: Total players without matches
                - matches_fully_matched: Matches where all players matched
                - matches_with_unmatched: Matches with some unmatched players
                - unmatched_by_match: Dict of match_id -> list of unmatched names
        """
        logger.info("Linking all players to participants...")

        # Get all match IDs
        match_ids = self.db.conn.execute(
            "SELECT match_id FROM matches ORDER BY match_id"
        ).fetchall()

        total_players = 0
        matched_players = 0
        unmatched_players = 0
        matches_fully_matched = 0
        matches_with_unmatched = 0
        unmatched_by_match = {}

        for (match_id,) in match_ids:
            stats = self.link_match_players(match_id)

            total_players += stats["total_players"]
            matched_players += stats["matched"]
            unmatched_players += stats["unmatched"]

            if stats["unmatched"] == 0:
                matches_fully_matched += 1
            else:
                matches_with_unmatched += 1
                unmatched_by_match[match_id] = stats["unmatched_names"]

        summary = {
            "total_matches": len(match_ids),
            "total_players": total_players,
            "matched_players": matched_players,
            "unmatched_players": unmatched_players,
            "matches_fully_matched": matches_fully_matched,
            "matches_with_unmatched": matches_with_unmatched,
            "unmatched_by_match": unmatched_by_match
        }

        logger.info(
            f"Linking complete: {matched_players}/{total_players} players matched "
            f"across {len(match_ids)} matches"
        )

        return summary
```

**Files to Create**:
- `tests/test_participant_matcher.py`

**Test Implementation**:

```python
"""Tests for participant matching logic."""

import pytest
from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.participant_matcher import ParticipantMatcher


@pytest.fixture
def test_db(tmp_path):
    """Create a temporary test database with participant data."""
    db_path = tmp_path / "test.duckdb"
    db = TournamentDatabase(str(db_path))

    # Insert test participants
    db.conn.execute("""
        INSERT INTO tournament_participants (
            participant_id, display_name, display_name_normalized
        ) VALUES
        (1001, 'Ninja', 'ninja'),
        (1002, 'FluffybunnyMohawk', 'fluffybunnymohawk'),
        (1003, 'Auro', 'auro')
    """)

    # Insert test match
    db.conn.execute("""
        INSERT INTO matches (match_id, challonge_match_id, file_name, file_hash)
        VALUES (100, 426504750, 'test.zip', 'hash123')
    """)

    # Insert test players
    db.conn.execute("""
        INSERT INTO players (
            player_id, match_id, player_name, player_name_normalized
        ) VALUES
        (1, 100, 'Ninja', 'ninja'),
        (2, 100, 'FluffybunnyMohawk', 'fluffybunnymohawk')
    """)

    yield db
    db.close()


class TestParticipantMatcher:
    """Tests for ParticipantMatcher class."""

    def test_match_player_exact(self, test_db):
        """Test exact name matching."""
        matcher = ParticipantMatcher(test_db)

        participant_id = matcher.match_player(100, "Ninja")
        assert participant_id == 1001

    def test_match_player_case_insensitive(self, test_db):
        """Test case-insensitive matching."""
        matcher = ParticipantMatcher(test_db)

        participant_id = matcher.match_player(100, "ninja")
        assert participant_id == 1001

        participant_id = matcher.match_player(100, "NINJA")
        assert participant_id == 1001

    def test_match_player_with_whitespace(self, test_db):
        """Test matching with whitespace normalization."""
        matcher = ParticipantMatcher(test_db)

        participant_id = matcher.match_player(100, " Ninja ")
        assert participant_id == 1001

    def test_match_player_not_found(self, test_db):
        """Test matching when participant doesn't exist."""
        matcher = ParticipantMatcher(test_db)

        participant_id = matcher.match_player(100, "UnknownPlayer")
        assert participant_id is None

    def test_match_player_with_override(self, test_db):
        """Test manual override takes precedence."""
        # Insert override
        test_db.conn.execute("""
            INSERT INTO participant_name_overrides (
                match_id, save_file_player_name, participant_id, reason
            ) VALUES (100, 'WrongName', 1003, 'Test override')
        """)

        matcher = ParticipantMatcher(test_db)

        # Should use override despite name not matching
        participant_id = matcher.match_player(100, "WrongName")
        assert participant_id == 1003

    def test_link_match_players(self, test_db):
        """Test linking all players in a match."""
        matcher = ParticipantMatcher(test_db)

        stats = matcher.link_match_players(100)

        assert stats["total_players"] == 2
        assert stats["matched"] == 2
        assert stats["unmatched"] == 0
        assert stats["unmatched_names"] == []

        # Verify database was updated
        result = test_db.conn.execute("""
            SELECT COUNT(*)
            FROM players
            WHERE match_id = 100
            AND participant_id IS NOT NULL
        """).fetchone()

        assert result[0] == 2

    def test_link_match_players_with_unmatched(self, test_db):
        """Test linking when some players don't match."""
        # Add player that won't match
        test_db.conn.execute("""
            INSERT INTO players (
                player_id, match_id, player_name, player_name_normalized
            ) VALUES (3, 100, 'UnknownPlayer', 'unknownplayer')
        """)

        matcher = ParticipantMatcher(test_db)

        stats = matcher.link_match_players(100)

        assert stats["total_players"] == 3
        assert stats["matched"] == 2
        assert stats["unmatched"] == 1
        assert "UnknownPlayer" in stats["unmatched_names"]
```

**Testing**:
```bash
# Run tests
uv run pytest tests/test_participant_matcher.py -v

# Check coverage
uv run pytest tests/test_participant_matcher.py --cov=tournament_visualizer.data.participant_matcher --cov-report=term-missing
```

**Commit Messages**:
```
feat: Add participant matching module

Implements player-to-participant linking using normalized name matching
and manual overrides. Supports batch processing of all matches.
```

```
test: Add tests for participant matching

Tests cover exact matching, case insensitivity, overrides,
and batch processing with unmatched players.
```

---

### Task 7: Create Player-Participant Linking Script

**Objective**: Create a standalone script to link players to participants.

**Files to Create**:
- `scripts/link_players_to_participants.py`

**Implementation**:

```python
#!/usr/bin/env python3
"""Link save file players to tournament participants.

Matches player names from save files to Challonge participants using
normalized name matching. Reports unmatched players that may need
manual overrides.

Prerequisites:
- Database must contain player data (from save file import)
- Participants must be synced (run sync_challonge_participants.py first)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tournament_visualizer.config import Config
from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.participant_matcher import ParticipantMatcher


def print_summary(stats: dict) -> None:
    """Print summary of matching results.

    Args:
        stats: Statistics dictionary from ParticipantMatcher.link_all_matches()
    """
    print("\n" + "=" * 60)
    print("PLAYER-PARTICIPANT LINKING SUMMARY")
    print("=" * 60)

    print(f"\nTotal matches processed: {stats['total_matches']}")
    print(f"Total players: {stats['total_players']}")
    print(f"Successfully matched: {stats['matched_players']}")
    print(f"Unmatched: {stats['unmatched_players']}")

    if stats['total_players'] > 0:
        match_rate = (stats['matched_players'] / stats['total_players']) * 100
        print(f"Match rate: {match_rate:.1f}%")

    print(f"\nMatches fully matched: {stats['matches_fully_matched']}")
    print(f"Matches with unmatched players: {stats['matches_with_unmatched']}")

    # Show unmatched players by match
    if stats['unmatched_by_match']:
        print("\nUnmatched players by match:")
        print("-" * 60)

        for match_id, unmatched_names in stats['unmatched_by_match'].items():
            print(f"\nMatch {match_id}:")
            for name in unmatched_names:
                print(f"  - {name}")

        print("\n" + "-" * 60)
        print("\nTo fix unmatched players:")
        print("1. Review the unmatched names above")
        print("2. Find their correct participant IDs in tournament_participants")
        print("3. Add entries to participant_name_overrides table")
        print("4. Re-run this script")

    print("=" * 60)


def verify_prerequisites(db: TournamentDatabase) -> bool:
    """Verify required data exists before linking.

    Args:
        db: Database instance

    Returns:
        True if prerequisites met, False otherwise
    """
    # Check for participants
    participant_count = db.conn.execute(
        "SELECT COUNT(*) FROM tournament_participants"
    ).fetchone()[0]

    if participant_count == 0:
        print("ERROR: No participants found in database")
        print("Run sync_challonge_participants.py first")
        return False

    # Check for players
    player_count = db.conn.execute(
        "SELECT COUNT(*) FROM players"
    ).fetchone()[0]

    if player_count == 0:
        print("ERROR: No players found in database")
        print("Import save files first using import_attachments.py")
        return False

    print(f"Found {participant_count} participants and {player_count} players")
    return True


def main() -> None:
    """Main function."""
    print("Player-Participant Linking Script")
    print("=" * 60)

    try:
        # Connect to database
        db = TournamentDatabase(Config.DATABASE_PATH)

        # Verify prerequisites
        if not verify_prerequisites(db):
            sys.exit(1)

        # Create matcher and link all players
        matcher = ParticipantMatcher(db)
        stats = matcher.link_all_matches()

        # Print summary
        print_summary(stats)

        db.close()

        # Exit with error code if there were unmatched players
        if stats['unmatched_players'] > 0:
            sys.exit(1)
        else:
            print("\nAll players successfully linked!")
            sys.exit(0)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Testing**:
```bash
# Prerequisites
uv run python scripts/sync_challonge_participants.py

# Run linking script
uv run python scripts/link_players_to_participants.py

# Verify linkages
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN participant_id IS NOT NULL THEN 1 ELSE 0 END) as linked,
    SUM(CASE WHEN participant_id IS NULL THEN 1 ELSE 0 END) as unlinked
FROM players
"
```

**Commit Message**:
```
feat: Add player-participant linking script

Batch links all save file players to tournament participants using
name matching. Reports unmatched players for manual review.
```

---

### Task 8: Update ETL Pipeline

**Objective**: Integrate participant linking into the ETL import pipeline.

**Files to Modify**:
- `tournament_visualizer/data/etl.py`

**Code Changes**:

Add participant linking as a post-processing step after all save files are imported.

**Find the main import function** (likely `import_all_files()` or similar) and add:

```python
def import_all_files(directory: str, db: TournamentDatabase, **kwargs) -> dict:
    """Import all save files from directory.

    Args:
        directory: Directory containing save files
        db: Database instance
        **kwargs: Additional arguments

    Returns:
        Dictionary with import statistics
    """
    # ... existing import code ...

    # Process all save files
    for save_file in save_files:
        process_tournament_file(save_file, db)

    # ... existing code ...

    # NEW: Link players to participants (if participants exist)
    try:
        from tournament_visualizer.data.participant_matcher import ParticipantMatcher

        participant_count = db.conn.execute(
            "SELECT COUNT(*) FROM tournament_participants"
        ).fetchone()[0]

        if participant_count > 0:
            logger.info("Linking players to tournament participants...")
            matcher = ParticipantMatcher(db)
            link_stats = matcher.link_all_matches()

            logger.info(
                f"Linked {link_stats['matched_players']}/{link_stats['total_players']} "
                f"players to participants"
            )

            # Add to results
            results['participant_linking'] = link_stats
        else:
            logger.info("No participants in database, skipping player-participant linking")
            results['participant_linking'] = None

    except Exception as e:
        logger.warning(f"Error linking players to participants: {e}")
        results['participant_linking'] = None

    return results
```

**Update summary output** to include participant linking stats:

```python
def print_import_summary(results: dict) -> None:
    """Print summary of import results."""
    # ... existing summary code ...

    # NEW: Add participant linking summary
    if results.get('participant_linking'):
        link_stats = results['participant_linking']
        print("\nParticipant Linking:")
        print(f"  Players matched: {link_stats['matched_players']}/{link_stats['total_players']}")

        if link_stats['unmatched_players'] > 0:
            print(f"  WARNING: {link_stats['unmatched_players']} players unmatched")
            print("  Run: uv run python scripts/link_players_to_participants.py for details")
```

**Testing**:
```bash
# Run full import
uv run python scripts/import_attachments.py --directory saves --force --verbose

# Should see participant linking in output
```

**Commit Message**:
```
feat: Integrate participant linking into ETL pipeline

Automatically links players to participants after save file import.
Warns if matches are incomplete and suggests manual review.
```

---

### Task 9: Create Validation Script

**Objective**: Create a script to validate participant linking integrity.

**Files to Create**:
- `scripts/validate_participants.py`

**Implementation** (abbreviated for space - follow pattern from `validate_rulers.py`):

```python
#!/usr/bin/env python3
"""Validation script for participant linking integrity.

Checks:
1. All participants have valid data
2. Player-participant links are valid
3. Match participant IDs match player linkages
4. No orphaned links
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tournament_visualizer.config import Config
from tournament_visualizer.data.database import TournamentDatabase


def validate_participant_data(db: TournamentDatabase) -> tuple[bool, list[str]]:
    """Validate participant table data integrity."""
    errors = []

    # Check for NULL display names
    null_names = db.conn.execute("""
        SELECT COUNT(*)
        FROM tournament_participants
        WHERE display_name IS NULL OR display_name = ''
    """).fetchone()[0]

    if null_names > 0:
        errors.append(f"Found {null_names} participants with NULL/empty display names")

    # Check normalized names
    null_normalized = db.conn.execute("""
        SELECT COUNT(*)
        FROM tournament_participants
        WHERE display_name_normalized IS NULL OR display_name_normalized = ''
    """).fetchone()[0]

    if null_normalized > 0:
        errors.append(f"Found {null_normalized} participants with NULL/empty normalized names")

    return len(errors) == 0, errors


def validate_player_participant_links(db: TournamentDatabase) -> tuple[bool, list[str]]:
    """Validate player-participant linkages."""
    errors = []

    # Check for invalid participant_id references
    invalid_refs = db.conn.execute("""
        SELECT COUNT(*)
        FROM players p
        LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
        WHERE p.participant_id IS NOT NULL
        AND tp.participant_id IS NULL
    """).fetchone()[0]

    if invalid_refs > 0:
        errors.append(f"Found {invalid_refs} players with invalid participant_id references")

    return len(errors) == 0, errors


def validate_match_participant_consistency(db: TournamentDatabase) -> tuple[bool, list[str]]:
    """Validate match participant IDs match player linkages."""
    errors = []

    # For each match, check if players' participant_ids match match.player1/2_participant_id
    inconsistent = db.conn.execute("""
        WITH match_players AS (
            SELECT
                m.match_id,
                m.player1_participant_id,
                m.player2_participant_id,
                p.participant_id as player_participant_id
            FROM matches m
            JOIN players p ON m.match_id = p.match_id
            WHERE m.player1_participant_id IS NOT NULL
            AND m.player2_participant_id IS NOT NULL
            AND p.participant_id IS NOT NULL
        )
        SELECT COUNT(DISTINCT match_id)
        FROM match_players
        WHERE player_participant_id NOT IN (player1_participant_id, player2_participant_id)
    """).fetchone()[0]

    if inconsistent > 0:
        errors.append(
            f"Found {inconsistent} matches where player participant IDs don't match "
            "match participant IDs"
        )

    return len(errors) == 0, errors


def print_summary(db: TournamentDatabase) -> None:
    """Print summary statistics."""
    print("\n" + "=" * 60)
    print("PARTICIPANT DATA SUMMARY")
    print("=" * 60)

    total_participants = db.conn.execute(
        "SELECT COUNT(*) FROM tournament_participants"
    ).fetchone()[0]

    total_players = db.conn.execute(
        "SELECT COUNT(*) FROM players"
    ).fetchone()[0]

    linked_players = db.conn.execute(
        "SELECT COUNT(*) FROM players WHERE participant_id IS NOT NULL"
    ).fetchone()[0]

    print(f"\nTotal participants: {total_participants}")
    print(f"Total players: {total_players}")
    print(f"Linked players: {linked_players} ({linked_players/total_players*100:.1f}%)")

    # Unique participants with players
    unique_participants = db.conn.execute("""
        SELECT COUNT(DISTINCT participant_id)
        FROM players
        WHERE participant_id IS NOT NULL
    """).fetchone()[0]

    print(f"Participants with players: {unique_participants}/{total_participants}")

    print("=" * 60)


def main() -> None:
    """Run all validations."""
    print("Validating participant data...")

    db = TournamentDatabase(Config.DATABASE_PATH)

    validations = [
        ("Participant data integrity", validate_participant_data),
        ("Player-participant links", validate_player_participant_links),
        ("Match-participant consistency", validate_match_participant_consistency),
    ]

    all_valid = True
    all_errors = []

    for name, validator in validations:
        print(f"\nChecking {name}...", end=" ")
        is_valid, errors = validator(db)

        if is_valid:
            print("✓ PASS")
        else:
            print("✗ FAIL")
            all_errors.extend([f"\n{name}:"] + errors)
            all_valid = False

    print_summary(db)

    if not all_valid:
        print("\n" + "=" * 60)
        print("VALIDATION ERRORS")
        print("=" * 60)
        for error in all_errors:
            print(error)
        print("=" * 60)
        sys.exit(1)
    else:
        print("\n✓ All validations passed!")
        sys.exit(0)

    db.close()


if __name__ == "__main__":
    main()
```

**Testing**:
```bash
uv run python scripts/validate_participants.py
```

**Commit Message**:
```
feat: Add participant data validation script

Validates participant data integrity, player-participant links,
and consistency between matches and player linkages.
```

---

### Task 10: Create ETL Integration Tests

**Objective**: Test the full ETL participant linking flow.

**Files to Create**:
- `tests/test_etl_participant_linking.py`

**Test Coverage**:

```python
"""Integration tests for ETL participant linking flow."""

class TestETLParticipantLinking:
    def test_etl_links_participants_when_available()
    def test_etl_skips_linking_when_no_participants()
    def test_etl_handles_partial_matches()
    def test_etl_linking_uses_overrides()
    def test_etl_continues_on_linking_error()
    def test_full_etl_flow_integration()

class TestETLParticipantLinkingReporting:
    def test_import_summary_includes_linking_stats()
```

**Testing**:
```bash
# Run ETL integration tests
uv run pytest tests/test_etl_participant_linking.py -v

# Check coverage
uv run pytest tests/test_etl_participant_linking.py --cov=tournament_visualizer.data.etl --cov-report=term-missing
```

**Commit Message**:
```
test: Add ETL participant linking integration tests

Tests full ETL flow including automatic participant linking,
partial matches, override handling, and error recovery.
```

---

### Task 11: Create Validation Script Tests

**Objective**: Test the validation script logic.

**Files to Create**:
- `tests/test_validate_participants.py`

**Test Coverage**:

```python
"""Tests for participant validation script logic."""

class TestParticipantDataValidation:
    def test_valid_participant_data()
    def test_detects_null_display_names()
    def test_detects_empty_display_names()
    def test_detects_null_normalized_names()

class TestPlayerParticipantLinkValidation:
    def test_valid_player_participant_links()
    def test_detects_invalid_participant_references()
    def test_allows_null_participant_references()

class TestMatchParticipantConsistency:
    def test_valid_match_participant_consistency()
    def test_detects_mismatched_participant_ids()
    def test_ignores_null_participant_data()

class TestParticipantSummaryStats:
    def test_participant_count()
    def test_linked_player_count()
    def test_linked_player_percentage()
    def test_unique_participants_with_players()
    def test_matches_with_participant_data()

class TestOrphanedReferences:
    def test_detects_orphaned_match_participant_ids()
    def test_detects_multiple_orphaned_references_in_match()
    def test_detects_unused_participants()

class TestValidationEdgeCases:
    def test_empty_database()
    def test_participants_without_matches()
    def test_players_without_participants()
```

**Testing**:
```bash
# Run validation tests
uv run pytest tests/test_validate_participants.py -v

# Check coverage
uv run pytest tests/test_validate_participants.py --cov-report=term-missing
```

**Commit Message**:
```
test: Add validation script logic tests

Tests all validation checks including data integrity, link validity,
match-participant consistency, orphaned references, and edge cases.
```

---

### Task 12: Update Documentation

**Objective**: Document the participant tracking system.

**Files to Modify**:
- `docs/developer-guide.md`
- `CLAUDE.md`

**Add to developer-guide.md**:

```markdown
## Tournament Participant Tracking

### Overview

The participant tracking system links players across multiple matches using Challonge tournament data. This enables cross-match analytics and persistent player identity.

### Architecture

**Two-tier identity system:**
1. **Match-scoped players** (`players` table): Independent player_ids per save file
2. **Tournament participants** (`tournament_participants` table): Persistent identity

**Data flow:**
1. Import Challonge participants via API
2. Import save files (creates match-scoped players)
3. Link players to participants via name matching
4. Enable cross-match queries using participant_id

### Schema

**tournament_participants table:**
```sql
CREATE TABLE tournament_participants (
    participant_id BIGINT PRIMARY KEY,           -- Challonge participant ID
    display_name VARCHAR NOT NULL,               -- Display name
    display_name_normalized VARCHAR NOT NULL,    -- Normalized for matching
    challonge_username VARCHAR,
    challonge_user_id BIGINT,                    -- Persistent across tournaments
    seed INTEGER,
    final_rank INTEGER
);
```

**Foreign keys:**
- `players.participant_id` → `tournament_participants.participant_id`
- `matches.player1_participant_id` → `tournament_participants.participant_id`
- `matches.player2_participant_id` → `tournament_participants.participant_id`
- `matches.winner_participant_id` → `tournament_participants.participant_id`

### Common Queries

**Player performance across matches:**
```sql
SELECT
    tp.display_name,
    COUNT(DISTINCT p.match_id) as matches_played,
    SUM(CASE WHEN mw.winner_player_id = p.player_id THEN 1 ELSE 0 END) as wins
FROM tournament_participants tp
JOIN players p ON tp.participant_id = p.participant_id
JOIN match_winners mw ON p.match_id = mw.match_id
GROUP BY tp.participant_id, tp.display_name
ORDER BY wins DESC;
```

**Participant civilizations:**
```sql
SELECT
    tp.display_name,
    p.civilization,
    COUNT(*) as times_played
FROM tournament_participants tp
JOIN players p ON tp.participant_id = p.participant_id
WHERE p.civilization IS NOT NULL
GROUP BY tp.participant_id, tp.display_name, p.civilization
ORDER BY tp.display_name, times_played DESC;
```

### Workflow

**Initial setup:**
```bash
# 1. Sync participants from Challonge
uv run python scripts/sync_challonge_participants.py

# 2. Import save files
uv run python scripts/import_attachments.py --directory saves --force

# 3. Link players to participants (automatic in ETL, or manual)
uv run python scripts/link_players_to_participants.py

# 4. Validate
uv run python scripts/validate_participants.py
```

**After tournament updates:**
```bash
# Re-sync participants (handles new/changed participants)
uv run python scripts/sync_challonge_participants.py

# Re-link (if participant names changed)
uv run python scripts/link_players_to_participants.py
```

### Name Matching

**Normalization process:**
1. Strip whitespace
2. Convert to lowercase
3. Remove Unicode accents
4. Remove special characters
5. Remove all remaining whitespace

**Examples:**
- "FluffybunnyMohawk" → "fluffybunnymohawk"
- "Ninja [OW]" → "ninjaow"
- "José García" → "josegarcia"

### Manual Overrides

**When automated matching fails, add manual override:**

```sql
INSERT INTO participant_name_overrides (
    match_id,
    save_file_player_name,
    participant_id,
    reason
) VALUES (
    123,
    'SaveFileName',
    456,
    'Player changed name mid-tournament'
);
```

Then re-run linking:
```bash
uv run python scripts/link_players_to_participants.py
```

### Validation

```bash
uv run python scripts/validate_participants.py
```

Checks:
- Participant data integrity
- Player-participant foreign key validity
- Match participant consistency
- No orphaned links
```

**Add to CLAUDE.md**:

```markdown
## Participant Tracking

The database links players across matches using Challonge participant data.

**Key concepts:**
- `player_id` is match-scoped (different ID per match)
- `participant_id` is tournament-scoped (same ID across matches)
- Name matching uses normalized names (lowercase, no special chars)
- Manual overrides available for edge cases

**Sync workflow:**
```bash
# 1. Import participants from Challonge
uv run python scripts/sync_challonge_participants.py

# 2. Import save files
uv run python scripts/import_attachments.py --directory saves --force

# 3. Participants automatically linked (or run manually)
uv run python scripts/link_players_to_participants.py
```

**Cross-match queries** use `participant_id` to track individuals across multiple matches.
```

**Commit Message**:
```
docs: Add tournament participant tracking documentation

Documents participant system architecture, workflow, name matching,
manual overrides, and common cross-match query patterns.
```

---

## Summary Checklist

Before considering implementation complete:

- [ ] Migration document created
- [ ] Database schema updated with new tables
- [ ] Schema migration for existing databases implemented
- [ ] Name normalization utility created
- [ ] Name normalization tests passing
- [ ] Challonge participant sync script working
- [ ] Participant matcher module implemented
- [ ] Participant matcher tests passing
- [ ] Player-participant linking script working
- [ ] ETL pipeline updated with automatic linking
- [ ] ETL integration tests passing
- [ ] Validation script created and passing
- [ ] Validation script tests passing
- [ ] Developer documentation updated
- [ ] CLAUDE.md updated with workflow
- [ ] All tests passing: `uv run pytest -v`
- [ ] Code formatted: `uv run black tournament_visualizer/`
- [ ] Linting clean: `uv run ruff check tournament_visualizer/`

## Time Estimates

- Task 1: 45 minutes (migration doc)
- Task 2: 30 minutes (database schema)
- Task 3: 1 hour (schema migration)
- Task 4: 2 hours (name normalizer + tests)
- Task 5: 1.5 hours (Challonge sync script)
- Task 6: 2.5 hours (participant matcher + tests)
- Task 7: 1 hour (linking script)
- Task 8: 45 minutes (ETL integration)
- Task 9: 1 hour (validation script)
- Task 10: 1.5 hours (ETL integration tests)
- Task 11: 1.5 hours (validation script tests)
- Task 12: 1 hour (documentation)

**Total: ~15 hours**

## Success Criteria

Implementation successful when:

1. All tests pass
2. Participants sync from Challonge successfully
3. Players link to participants with >95% match rate
4. Validation script passes all checks
5. Can answer: "How many matches has each person played?"
6. Can track individual win rates across matches
7. Manual override system works for edge cases
8. Documentation is complete and accurate

## Rollback Plan

If issues discovered:

```bash
# Restore database backup
cp data/tournament_data.duckdb.backup_TIMESTAMP data/tournament_data.duckdb

# Or remove participant data only
uv run duckdb data/tournament_data.duckdb -c "
DELETE FROM tournament_participants;
DELETE FROM participant_name_overrides;
UPDATE players SET participant_id = NULL;
UPDATE matches SET player1_participant_id = NULL,
                   player2_participant_id = NULL,
                   winner_participant_id = NULL;
"
```

## Future Enhancements (YAGNI - Do NOT Implement Now)

- Multi-tournament tracking via challonge_user_id
- Fuzzy matching (Levenshtein distance)
- Automatic override suggestions
- Participant statistics caching
- Cross-tournament analytics
