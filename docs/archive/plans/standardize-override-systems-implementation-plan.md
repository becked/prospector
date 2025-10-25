# Standardize Override Systems Implementation Plan

> **Status**: Completed and archived (2025-10-25)
>
> Override systems complete and documented in CLAUDE.md (Override Systems Design section).

## Executive Summary

**Problem**: The `participant_name_overrides.json` file uses unstable database `match_id` values as keys. Every time the database is re-imported, match IDs change (they're auto-incrementing row IDs), breaking all the overrides and requiring manual remapping.

**Solution**: Migrate to use stable `challonge_match_id` values (from Challonge API) instead, making the system consistent with other override files and immune to database re-imports.

**Impact**:
- Eliminates need for `remap_participant_overrides.py` workaround script
- Makes system consistent with 3 other override systems
- Prevents data corruption on database re-imports
- Simplifies maintenance and debugging

## Current State Analysis

### Override Systems Inventory

| Override File | Key Type | Stability | Status |
|--------------|----------|-----------|--------|
| `match_winner_overrides.json` | `challonge_match_id` (string) | ✅ Stable | Good |
| `pick_order_overrides.json` | `game_number` (from sheet) | ✅ Stable | Good |
| `gdrive_match_mapping_overrides.json` | `challonge_match_id` (string) | ✅ Stable | Good |
| `participant_name_overrides.json` | `match_id` (DB row ID) | ❌ UNSTABLE | **BROKEN** |

### Why `match_id` Is Unstable

```sql
-- Match IDs are assigned during import based on INSERT order
-- Import order can change based on:
-- 1. File system iteration order
-- 2. Challonge API response order
-- 3. Threading/async execution order

-- Example: First import
INSERT INTO matches (...) VALUES (...);  -- match_id = 1
INSERT INTO matches (...) VALUES (...);  -- match_id = 2

-- After re-import (different order!)
INSERT INTO matches (...) VALUES (...);  -- match_id = 1 (DIFFERENT MATCH!)
INSERT INTO matches (...) VALUES (...);  -- match_id = 2 (DIFFERENT MATCH!)
```

### Why `challonge_match_id` Is Stable

- Assigned by Challonge API when match is created
- Never changes for the lifetime of the match
- Globally unique within the tournament
- Same value across all database imports
- Already present in `matches` table

## Architecture

### Data Flow

```
Challonge API
    ↓
matches table (challonge_match_id + match_id)
    ↓
Override file (keyed by challonge_match_id)
    ↓
ParticipantMatcher (lookup by challonge_match_id)
    ↓
Update players table (link player → participant)
```

### File Format Comparison

**BEFORE (Broken)**:
```json
{
  "_comment": "Participant name overrides",
  "1": {                    // ❌ Database match_id (unstable!)
    "Ninja": {
      "participant_id": 272470588,
      "reason": "Save uses 'Ninja' but Challonge is 'Ninjaa'",
      "date_added": "2025-10-17"
    }
  },
  "14": {                   // ❌ Database match_id (unstable!)
    "Fiddler": {
      "participant_id": 272452137,
      "reason": "Save uses 'Fiddler' but Challonge is 'fiddlers25'",
      "date_added": "2025-10-17"
    }
  }
}
```

**AFTER (Fixed)**:
```json
{
  "_comment": "Participant name overrides",
  "426504734": {            // ✅ Challonge match_id (stable!)
    "Ninja": {
      "participant_id": 272470588,
      "reason": "Save uses 'Ninja' but Challonge is 'Ninjaa'",
      "date_added": "2025-10-17"
    }
  },
  "426504756": {            // ✅ Challonge match_id (stable!)
    "Fiddler": {
      "participant_id": 272452137,
      "reason": "Save uses 'Fiddler' but Challonge is 'fiddlers25'",
      "date_added": "2025-10-17"
    }
  }
}
```

## Implementation Tasks

### Prerequisites

**Required Knowledge:**
- Basic Python (dicts, file I/O, type hints)
- JSON format and encoding
- SQL queries (SELECT with WHERE clause)
- Git version control

**Tools:**
- `uv` - Python package manager
- `duckdb` - SQL database CLI
- Your text editor

**Files You'll Touch:**
- `tournament_visualizer/data/participant_matcher.py` - Matching logic
- `data/participant_name_overrides.json` - Override file
- `data/participant_name_overrides.json.example` - Template
- `scripts/migrate_participant_overrides.py` - NEW: Migration script
- `scripts/remap_participant_overrides.py` - DELETE: No longer needed
- `CLAUDE.md` - Documentation update

### Task 1: Create Migration Script

**Goal**: Write a one-time script to convert existing override file from `match_id` keys to `challonge_match_id` keys.

**Files**: Create `scripts/migrate_participant_overrides.py`

**Why**: Automate the conversion to avoid manual errors.

**Code**:

```python
#!/usr/bin/env python3
"""Migrate participant_name_overrides.json to use challonge_match_id keys.

This is a ONE-TIME migration script to convert from unstable database match_id
keys to stable challonge_match_id keys.

Usage:
    # Dry run (preview changes)
    python scripts/migrate_participant_overrides.py --dry-run

    # Apply migration
    python scripts/migrate_participant_overrides.py
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).parent.parent))

from tournament_visualizer.config import Config


def load_match_id_mapping(db_path: str) -> dict[int, int]:
    """Load mapping from database match_id to challonge_match_id.

    Args:
        db_path: Path to DuckDB database

    Returns:
        Dict mapping: database match_id → challonge_match_id
    """
    conn = duckdb.connect(db_path, read_only=True)

    try:
        results = conn.execute("""
            SELECT match_id, challonge_match_id
            FROM matches
            WHERE challonge_match_id IS NOT NULL
            ORDER BY match_id
        """).fetchall()

        # Build mapping
        mapping = {match_id: challonge_id for match_id, challonge_id in results}

        print(f"Loaded mapping for {len(mapping)} matches from database")
        return mapping

    finally:
        conn.close()


def migrate_overrides(
    old_overrides: dict,
    match_mapping: dict[int, int],
    dry_run: bool = False
) -> dict:
    """Migrate override keys from match_id to challonge_match_id.

    Args:
        old_overrides: Original overrides dict with match_id keys
        match_mapping: Dict mapping match_id → challonge_match_id
        dry_run: If True, don't write changes

    Returns:
        New overrides dict with challonge_match_id keys
    """
    new_overrides = {}
    migrated_count = 0
    not_found_count = 0

    print("\nMigrating override entries...")
    print("=" * 70)

    # Copy metadata entries (start with underscore)
    for key, value in old_overrides.items():
        if key.startswith("_"):
            new_overrides[key] = value

    # Migrate data entries
    for old_key, players_dict in old_overrides.items():
        if old_key.startswith("_"):
            continue  # Skip metadata

        try:
            # Convert old key (string) to int for lookup
            db_match_id = int(old_key)

            # Look up challonge_match_id
            if db_match_id in match_mapping:
                challonge_match_id = match_mapping[db_match_id]
                new_key = str(challonge_match_id)

                # Copy entry with new key
                new_overrides[new_key] = players_dict

                player_names = list(players_dict.keys())
                print(
                    f"✓ match_id {old_key:>3} → challonge_match_id {new_key:>9}  "
                    f"({len(player_names)} players: {', '.join(player_names)})"
                )
                migrated_count += 1
            else:
                print(
                    f"✗ match_id {old_key:>3} → NOT FOUND in database "
                    f"(match may have been deleted)"
                )
                not_found_count += 1

        except (ValueError, KeyError) as e:
            print(f"✗ Invalid entry '{old_key}': {e}")
            not_found_count += 1

    print("=" * 70)
    print(f"\nMigration summary:")
    print(f"  Successfully migrated: {migrated_count}")
    print(f"  Not found in database: {not_found_count}")
    print(f"  Total entries: {migrated_count + not_found_count}")

    return new_overrides


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Migrate participant overrides to use challonge_match_id"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files"
    )
    args = parser.parse_args()

    overrides_path = Path(Config.PARTICIPANT_NAME_OVERRIDES_PATH)

    if not overrides_path.exists():
        print(f"ERROR: Override file not found: {overrides_path}")
        print("Nothing to migrate.")
        sys.exit(0)

    # Load current overrides
    print(f"Loading overrides from: {overrides_path}")
    with open(overrides_path, "r", encoding="utf-8") as f:
        old_overrides = json.load(f)

    # Load match ID mapping from database
    match_mapping = load_match_id_mapping(Config.DATABASE_PATH)

    # Migrate
    new_overrides = migrate_overrides(old_overrides, match_mapping, args.dry_run)

    if args.dry_run:
        print("\n[DRY RUN] Would write migrated overrides to:", overrides_path)
        print("\nMigrated overrides preview (first 500 chars):")
        preview = json.dumps(new_overrides, indent=2)[:500]
        print(preview + "...")
    else:
        # Backup old file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = overrides_path.with_suffix(f".json.backup_{timestamp}")
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(old_overrides, f, indent=2)
        print(f"\n✓ Backed up old overrides to: {backup_path}")

        # Write new overrides
        with open(overrides_path, "w", encoding="utf-8") as f:
            json.dump(new_overrides, f, indent=2)
        print(f"✓ Wrote migrated overrides to: {overrides_path}")

        print("\nNext steps:")
        print("1. Run: uv run python scripts/link_players_to_participants.py")
        print("2. Verify linking worked correctly")
        print("3. Delete: scripts/remap_participant_overrides.py (no longer needed)")
        print("4. Commit the migrated override file")


if __name__ == "__main__":
    main()
```

**Testing**:

1. **Dry run first**:
   ```bash
   uv run python scripts/migrate_participant_overrides.py --dry-run
   ```
   - Should show preview of changes
   - Should NOT modify any files
   - Verify output looks correct

2. **Apply migration**:
   ```bash
   uv run python scripts/migrate_participant_overrides.py
   ```
   - Should create backup file
   - Should write new override file
   - Check `data/participant_name_overrides.json` manually

3. **Verify migration**:
   ```bash
   # Check all keys are now 9-digit numbers (challonge_match_id format)
   cat data/participant_name_overrides.json | grep -E '^\s*"[0-9]{9}"'

   # Should see lines like:
   #   "426504734": {
   #   "426504756": {
   ```

**Expected Output**:
```
Loading overrides from: data/participant_name_overrides.json
Loaded mapping for 24 matches from database

Migrating override entries...
======================================================================
✓ match_id   1 → challonge_match_id 426504730  (2 players: Blaj, Fonder)
✓ match_id   2 → challonge_match_id 426504734  (1 players: Marauder)
✓ match_id   3 → challonge_match_id 426504732  (1 players: Michael)
...
======================================================================

Migration summary:
  Successfully migrated: 17
  Not found in database: 0
  Total entries: 17

✓ Backed up old overrides to: data/participant_name_overrides.json.backup_20251019_143052
✓ Wrote migrated overrides to: data/participant_name_overrides.json
```

**Commit After This Task**:
```bash
git add scripts/migrate_participant_overrides.py
git commit -m "feat: Add migration script for participant override keys

Add one-time migration script to convert participant_name_overrides.json
from using unstable database match_id keys to stable challonge_match_id keys.

This prepares for the standardization of all override systems to use
stable external IDs."
```

---

### Task 2: Update ParticipantMatcher to Use challonge_match_id

**Goal**: Modify the participant matching logic to look up overrides by `challonge_match_id` instead of database `match_id`.

**Files**:
- `tournament_visualizer/data/participant_matcher.py`

**Why**: This is the core logic that reads the override file. We need to change what key it uses for lookups.

**Current Behavior**:
- `match_player()` receives database `match_id`
- Looks up overrides using `match_id` directly
- Problem: `match_id` changes on re-import

**New Behavior**:
- `match_player()` receives database `match_id`
- Queries database to get `challonge_match_id` for that `match_id`
- Looks up overrides using `challonge_match_id`
- Benefit: Overrides survive database re-imports

**Code Changes**:

**Step 2.1**: Add challonge_match_id lookup method

Add this new method to `ParticipantMatcher` class after the `_load_overrides()` method:

```python
def _get_challonge_match_id(self, match_id: int) -> Optional[int]:
    """Get challonge_match_id for a database match_id.

    Args:
        match_id: Database match ID (internal, unstable)

    Returns:
        Challonge match ID (external, stable), or None if not found
    """
    result = self.db.fetch_one(
        """
        SELECT challonge_match_id
        FROM matches
        WHERE match_id = ?
        """,
        {"1": match_id}
    )

    if result and result[0]:
        return result[0]

    logger.warning(
        f"No challonge_match_id found for database match_id {match_id}"
    )
    return None
```

**Why**: We need to convert from the database's internal `match_id` to the stable `challonge_match_id` before looking up overrides.

**Step 2.2**: Update override key format in `_load_overrides()`

Find the `_load_overrides()` method (around line 71-121) and update the docstring:

```python
def _load_overrides(self) -> None:
    """Load participant name overrides from JSON file.

    The JSON structure is:
    {
        "challonge_match_id": {    # ← CHANGED: was "match_id"
            "save_file_name": {
                "participant_id": 123,
                "reason": "explanation",
                "date_added": "YYYY-MM-DD"
            }
        }
    }
    """
```

**Why**: Documentation should reflect the new format.

**Step 2.3**: Update `match_player()` to use challonge_match_id

Find the `match_player()` method (around line 123-181) and replace the override lookup section:

**BEFORE** (around lines 146-162):
```python
# Check override first
if allow_override:
    # Load overrides if not already loaded
    if not self._overrides_loaded:
        self._load_overrides()

    # Check if this match has overrides
    if match_id in self._overrides:
        match_overrides = self._overrides[match_id]
        if player_name in match_overrides:
            override_data = match_overrides[player_name]
            participant_id = override_data["participant_id"]
            logger.debug(
                f"Using override: '{player_name}' -> participant {participant_id} "
                f"(reason: {override_data.get('reason', 'not specified')})"
            )
            return participant_id
```

**AFTER**:
```python
# Check override first
if allow_override:
    # Load overrides if not already loaded
    if not self._overrides_loaded:
        self._load_overrides()

    # Get challonge_match_id for override lookup
    challonge_match_id = self._get_challonge_match_id(match_id)

    if challonge_match_id:
        # Check if this match has overrides
        # Overrides are keyed by challonge_match_id (as string)
        override_key = str(challonge_match_id)

        if override_key in self._overrides:
            match_overrides = self._overrides[override_key]
            if player_name in match_overrides:
                override_data = match_overrides[player_name]
                participant_id = override_data["participant_id"]
                logger.debug(
                    f"Using override for match {match_id} (challonge {challonge_match_id}): "
                    f"'{player_name}' -> participant {participant_id} "
                    f"(reason: {override_data.get('reason', 'not specified')})"
                )
                return participant_id
```

**Why**:
- Now looks up challonge_match_id first
- Uses that stable ID to find overrides
- Adds better logging showing both IDs for debugging

**Step 2.4**: Update override storage dict type annotation

Find the class attribute `_overrides` declaration (around line 39):

**BEFORE**:
```python
self._overrides: dict[int, dict[str, dict[str, Any]]] = {}
```

**AFTER**:
```python
self._overrides: dict[str, dict[str, dict[str, Any]]] = {}
```

**Why**: Override keys are now strings (challonge_match_id converted to str for JSON), not ints.

**Step 2.5**: Update override loading logic

Find the override loading loop in `_load_overrides()` (around lines 101-110):

**BEFORE**:
```python
# Convert match IDs from strings to ints and build lookup
override_count = 0
for match_id_str, players in data.items():
    # Skip metadata entries
    if match_id_str.startswith("_"):
        continue

    match_id = int(match_id_str)
    self._overrides[match_id] = players
    override_count += len(players)
```

**AFTER**:
```python
# Build lookup with challonge_match_id keys (kept as strings)
override_count = 0
for challonge_match_id_str, players in data.items():
    # Skip metadata entries
    if challonge_match_id_str.startswith("_"):
        continue

    # Validate it's a valid number (challonge_match_id)
    try:
        int(challonge_match_id_str)  # Verify it's numeric
    except ValueError:
        logger.warning(
            f"Invalid challonge_match_id key in overrides: '{challonge_match_id_str}'"
        )
        continue

    # Store with string key (JSON keys must be strings)
    self._overrides[challonge_match_id_str] = players
    override_count += len(players)
```

**Why**:
- Keys are now challonge_match_id (as strings)
- Added validation to catch invalid keys
- Clearer variable naming

**Testing**:

1. **Write a test** in `tests/test_participant_matcher.py`:

```python
def test_override_lookup_uses_challonge_match_id(db_fixture):
    """Verify overrides use challonge_match_id, not match_id."""
    import tempfile
    import json
    from pathlib import Path

    # Create test override file with challonge_match_id keys
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.json',
        delete=False
    ) as f:
        test_overrides = {
            "426504730": {  # Challonge match ID
                "TestPlayer": {
                    "participant_id": 999999,
                    "reason": "Test override",
                    "date_added": "2025-10-19"
                }
            }
        }
        json.dump(test_overrides, f)
        override_path = f.name

    try:
        # Create matcher with test override file
        matcher = ParticipantMatcher(db_fixture, overrides_path=override_path)

        # Get database match_id for challonge match 426504730
        result = db_fixture.fetch_one(
            "SELECT match_id FROM matches WHERE challonge_match_id = 426504730"
        )
        assert result, "Test match not found in database"
        db_match_id = result[0]

        # Should find override using database match_id
        # (internally converts to challonge_match_id)
        participant_id = matcher.match_player(db_match_id, "TestPlayer")

        assert participant_id == 999999, "Override should be found via challonge_match_id"

    finally:
        # Clean up
        Path(override_path).unlink()
```

2. **Run the test**:
   ```bash
   uv run pytest tests/test_participant_matcher.py::test_override_lookup_uses_challonge_match_id -v
   ```
   - Should pass ✅
   - If it fails, debug the lookup logic

3. **Integration test** - Run actual linking:
   ```bash
   # Stop server first
   uv run python manage.py stop

   # Run linking with migrated overrides
   uv run python scripts/link_players_to_participants.py
   ```
   - Should show "Using override" messages in output
   - Should achieve 100% linking rate
   - Check logs for errors

4. **Verify in database**:
   ```bash
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT
       COUNT(*) as total,
       COUNT(participant_id) as linked,
       ROUND(COUNT(participant_id) * 100.0 / COUNT(*), 1) as pct
   FROM players
   "
   ```
   - Should show 100% linked

**Commit After This Task**:
```bash
git add tournament_visualizer/data/participant_matcher.py
git commit -m "refactor: Use challonge_match_id for participant overrides

Change ParticipantMatcher to look up overrides by stable challonge_match_id
instead of unstable database match_id.

- Add _get_challonge_match_id() method to convert match IDs
- Update match_player() to use challonge_match_id for override lookups
- Update type annotations to reflect string keys
- Add validation for override keys
- Improve logging to show both match_id and challonge_match_id

This makes participant overrides survive database re-imports without
requiring remapping."
```

---

### Task 3: Update Override File Example Template

**Goal**: Update the example template to show the new format with `challonge_match_id` keys.

**Files**: `data/participant_name_overrides.json.example`

**Why**: Developers copying this template need to see the correct format.

**Code**:

Replace the entire file with:

```json
{
  "_comment": "Participant name overrides for save file player names that don't match Challonge names",
  "_instructions": [
    "1. Copy this file to participant_name_overrides.json (not in git)",
    "2. Add entries for players that can't auto-match by name",
    "3. Run: uv run python scripts/link_players_to_participants.py",
    "4. For production: ./scripts/sync_tournament_data.sh"
  ],
  "_format": {
    "challonge_match_id": {
      "save_file_name": {
        "participant_id": "The tournament participant ID to link to",
        "reason": "Why this override is needed (for documentation)",
        "date_added": "YYYY-MM-DD (when override was added)"
      }
    }
  },
  "_how_to_find_ids": {
    "challonge_match_id": "Get from matches table: SELECT match_id, challonge_match_id FROM matches",
    "participant_id": "Get from tournament_participants table: SELECT participant_id, display_name FROM tournament_participants",
    "save_file_name": "Exact player name as it appears in the save file XML"
  },
  "_examples": {
    "426504734": {
      "Ninja": {
        "participant_id": 272470588,
        "reason": "Save file uses 'Ninja' but Challonge name is 'Ninjaa'",
        "date_added": "2025-10-17"
      }
    },
    "426504756": {
      "Fiddler": {
        "participant_id": 272452137,
        "reason": "Save file uses 'Fiddler' but Challonge name is 'fiddlers25'",
        "date_added": "2025-10-17"
      },
      "Ninja": {
        "participant_id": 272470588,
        "reason": "Save file uses 'Ninja' but Challonge name is 'Ninjaa'",
        "date_added": "2025-10-17"
      }
    }
  }
}
```

**Key Changes**:
- Keys are now `challonge_match_id` (9-digit numbers as strings)
- Added `_how_to_find_ids` section with SQL queries
- Updated examples to use real challonge_match_id values
- Clarified instructions

**Testing**:
1. Open the file and verify it's valid JSON:
   ```bash
   cat data/participant_name_overrides.json.example | python -m json.tool > /dev/null
   ```
   - Should produce no errors ✅

2. Verify it matches the new format:
   ```bash
   # Should see 9-digit numbers as keys
   grep -E '^\s*"[0-9]{9}"' data/participant_name_overrides.json.example
   ```

**Commit After This Task**:
```bash
git add data/participant_name_overrides.json.example
git commit -m "docs: Update participant override example to use challonge_match_id

Update example template to show new stable key format using challonge_match_id
instead of database match_id.

- Change keys from match_id to challonge_match_id
- Add _how_to_find_ids section with helpful SQL queries
- Update examples with realistic challonge_match_id values
- Clarify that keys must be strings (JSON requirement)"
```

---

### Task 4: Update Documentation

**Goal**: Update CLAUDE.md to reflect the new override system and remove references to the old remap workaround.

**Files**: `CLAUDE.md`

**Why**: Developers need accurate documentation about how the system works.

**Changes**:

**Step 4.1**: Find the "Participant Name Overrides" section (around line 300+)

Replace this section:

**BEFORE**:
```markdown
### Participant Name Overrides

**Problem**: Save file player names often don't match Challonge participant names:
- Save files store short nicknames (e.g., "Ninja", "Fonder")
- Challonge uses full usernames (e.g., "Ninjaa", "FonderCargo348")
- Normalized name matching fails on these differences

**Solution**: Manual override system via JSON configuration

**Location**: `data/participant_name_overrides.json` (not in git)

**Format**:
```json
{
  "match_id": {
    "SaveFileName": {
      "participant_id": 272470588,
      "reason": "Save file uses 'Ninja' but Challonge name is 'Ninjaa'",
      "date_added": "YYYY-MM-DD"
    }
  }
}
```

**Usage**:
1. Copy `data/participant_name_overrides.json.example` to `data/participant_name_overrides.json`
2. Add override entries for mismatched names
3. Run linking: `uv run python scripts/link_players_to_participants.py`
4. For production: `./scripts/sync_tournament_data.sh` (uploads override file automatically)
```

**AFTER**:
```markdown
### Participant Name Overrides

**Problem**: Save file player names often don't match Challonge participant names:
- Save files store short nicknames (e.g., "Ninja", "Fonder")
- Challonge uses full usernames (e.g., "Ninjaa", "FonderCargo348")
- Normalized name matching fails on these differences

**Solution**: Manual override system via JSON configuration

**Location**: `data/participant_name_overrides.json` (not in git)

**Format**:
```json
{
  "challonge_match_id": {
    "SaveFileName": {
      "participant_id": 272470588,
      "reason": "Save file uses 'Ninja' but Challonge name is 'Ninjaa'",
      "date_added": "YYYY-MM-DD"
    }
  }
}
```

**Key Design**:
- Uses **`challonge_match_id`** (from Challonge API) - stable across database re-imports
- NOT `match_id` (database row ID) - that would break on re-import
- Consistent with other override systems (winner, pick order, GDrive mapping)

**Usage**:
1. Copy `data/participant_name_overrides.json.example` to `data/participant_name_overrides.json`
2. Find IDs using SQL:
   ```bash
   # Find challonge_match_id
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT match_id, challonge_match_id, player1_name, player2_name
   FROM matches
   "

   # Find participant_id
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT participant_id, display_name
   FROM tournament_participants
   "
   ```
3. Add override entries for mismatched names
4. Run linking: `uv run python scripts/link_players_to_participants.py`
5. For production: `./scripts/sync_tournament_data.sh` (uploads override file automatically)
```

**Step 4.2**: Add a new "Override Systems Design" section

Add this new section after the "Participant Name Overrides" section:

```markdown
### Override Systems Design

All override files in this application follow a consistent design:

| Override File | Purpose | Key Type | Stability |
|--------------|---------|----------|-----------|
| `match_winner_overrides.json` | Fix corrupted winner data | `challonge_match_id` | ✅ Stable |
| `pick_order_overrides.json` | Manually link games to matches | `game_number` | ✅ Stable |
| `gdrive_match_mapping_overrides.json` | Map GDrive files to matches | `challonge_match_id` | ✅ Stable |
| `participant_name_overrides.json` | Link mismatched player names | `challonge_match_id` | ✅ Stable |

**Design Principles**:
1. **Use stable external IDs** - Never use auto-incrementing database row IDs
2. **Survive database re-imports** - Overrides must work after data is reimported
3. **JSON format** - All overrides use JSON for easy editing
4. **Not in git** - Override files contain tournament-specific data
5. **Example templates** - Each has a `.example` file showing format

**Why `challonge_match_id` is stable**:
- Assigned by Challonge API when match is created
- Never changes for the lifetime of the match
- Same value across all database imports
- Globally unique within the tournament

**Why database `match_id` is NOT stable**:
- Auto-incrementing row ID assigned during import
- Changes based on import order (file system, API response order)
- Different value after each database re-import
- Only unique within that specific database instance
```

**Step 4.3**: Remove references to `remap_participant_overrides.py`

Search for `remap_participant_overrides` in CLAUDE.md and delete those sections.

**Testing**:
1. Build documentation preview:
   ```bash
   # Verify markdown is valid
   cat CLAUDE.md | python -m markdown > /tmp/claude.html
   ```

2. Read through the sections you changed and verify they make sense

**Commit After This Task**:
```bash
git add CLAUDE.md
git commit -m "docs: Update override system documentation

Update CLAUDE.md to reflect new stable override key design:
- Document use of challonge_match_id instead of match_id
- Add SQL queries for finding IDs
- Add new 'Override Systems Design' section explaining principles
- Remove references to remap_participant_overrides.py workaround

All override systems now use stable external IDs."
```

---

### Task 5: Delete Obsolete Remap Script

**Goal**: Remove the `remap_participant_overrides.py` script that's no longer needed.

**Files**: `scripts/remap_participant_overrides.py`

**Why**:
- Script only existed to work around unstable match_id keys
- Now that we use stable challonge_match_id, remapping is never needed
- Keeping dead code is confusing and causes maintenance burden

**Code**:

```bash
# Delete the file
rm scripts/remap_participant_overrides.py
```

**Verification**:
```bash
# File should not exist
ls scripts/remap_participant_overrides.py
# Should output: No such file or directory
```

**Testing**:
1. Verify no other files reference this script:
   ```bash
   grep -r "remap_participant_overrides" . --exclude-dir=.git --exclude-dir=docs
   ```
   - Should show no results (we already updated CLAUDE.md)

2. Verify git knows it's deleted:
   ```bash
   git status
   # Should show: deleted: scripts/remap_participant_overrides.py
   ```

**Commit After This Task**:
```bash
git add scripts/remap_participant_overrides.py
git commit -m "chore: Remove obsolete remap_participant_overrides.py script

This workaround script is no longer needed now that participant overrides
use stable challonge_match_id keys instead of unstable database match_id.

Overrides now survive database re-imports without requiring remapping."
```

---

### Task 6: End-to-End Integration Test

**Goal**: Verify the entire system works with real data and survives a database re-import.

**Files**: None (testing only)

**Why**: Ensure all the pieces work together correctly in a realistic scenario.

**Test Plan**:

**Test 6.1: Verify current state**

```bash
# Stop server
uv run python manage.py stop

# Check current participant linking
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT
    COUNT(*) as total_players,
    COUNT(participant_id) as linked_players,
    ROUND(COUNT(participant_id) * 100.0 / COUNT(*), 1) as link_rate_pct
FROM players
"
```

Expected: Should show 100% link rate (48/48 players linked)

**Test 6.2: Backup current database**

```bash
cp data/tournament_data.duckdb data/tournament_data.duckdb.backup_test
```

**Test 6.3: Re-import database** (simulates what would break old system)

```bash
# Re-import all data
uv run python scripts/import_attachments.py --directory saves --force --verbose
```

- Should import all 24 files
- match_id values will likely change
- challonge_match_id values will stay the same

**Test 6.4: Verify match IDs changed but challonge IDs stayed same**

```bash
# Check if match IDs changed
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT
    match_id,
    challonge_match_id,
    player1_name,
    player2_name
FROM matches
ORDER BY match_id
LIMIT 5
"
```

Compare to backup:
```bash
uv run duckdb data/tournament_data.duckdb.backup_test -readonly -c "
SELECT
    match_id,
    challonge_match_id,
    player1_name,
    player2_name
FROM matches
ORDER BY match_id
LIMIT 5
"
```

Expected:
- `match_id` values may differ ❓
- `challonge_match_id` values should be IDENTICAL ✅
- Player names should match ✅

**Test 6.5: Run participant linking with unchanged override file**

```bash
# Run linking (override file was NOT modified!)
uv run python scripts/link_players_to_participants.py
```

Expected:
- Should see "Using override" messages
- Should achieve 100% linking (48/48 players)
- Should show NO "unmatched players" messages
- Exit code should be 0 (success)

**Test 6.6: Verify linking survived re-import**

```bash
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT
    COUNT(*) as total_players,
    COUNT(participant_id) as linked_players,
    ROUND(COUNT(participant_id) * 100.0 / COUNT(*), 1) as link_rate_pct
FROM players
"
```

Expected: 100% link rate ✅

**Test 6.7: Verify override file was NOT modified**

```bash
# Check override file modification time
ls -la data/participant_name_overrides.json

# Check git status
git status data/participant_name_overrides.json
```

Expected:
- File should show NO modifications ✅
- `git status` should show "nothing to commit" ✅

**Test 6.8: Verify pick order data still works**

```bash
uv run python scripts/match_pick_order_games.py --verbose
```

Expected:
- Should match 9 games to database ✅
- Should see "Using override" messages
- Should achieve high match rate

**Test 6.9: Start server and verify UI**

```bash
# Start server
uv run python manage.py start

# Check logs
uv run python manage.py logs
```

Open browser to http://localhost:8050 and check:
- Overview page loads ✅
- Pick Order charts show data ✅
- Players page shows 100% linking ✅
- No error messages ✅

**Success Criteria**:
- ✅ All tests pass
- ✅ Override file UNCHANGED after re-import
- ✅ 100% participant linking maintained
- ✅ Pick order matching works
- ✅ UI displays correctly

**If Any Test Fails**:
1. Stop server: `uv run python manage.py stop`
2. Restore backup: `cp data/tournament_data.duckdb.backup_test data/tournament_data.duckdb`
3. Review error messages
4. Debug the failing component
5. Fix the issue
6. Restart from Test 6.3

**Commit After This Task**:
```bash
# Document the test in git
git add -A
git commit -m "test: Verify override system survives database re-import

Ran end-to-end integration test confirming:
- Participant overrides use stable challonge_match_id keys
- Override file survives database re-import unchanged
- Participant linking maintains 100% coverage after re-import
- Pick order matching continues to work
- UI displays correctly

All override systems now immune to database re-import changes."
```

---

### Task 7: Production Migration

**Goal**: Deploy the changes to production (Fly.io) safely.

**Files**: None (deployment only)

**Why**: Production has the same data and same issues. We need to migrate production without breaking anything.

**Prerequisites**:
- All previous tasks completed ✅
- All commits pushed to git ✅
- Local testing passed ✅

**Deployment Steps**:

**Step 7.1: Backup production database**

```bash
# Download current production database
flyctl sftp get /data/tournament_data.duckdb data/tournament_data.duckdb.prod_backup -a prospector

# Verify download
ls -lh data/tournament_data.duckdb.prod_backup
```

**Step 7.2: Download production override file**

```bash
# Get current production overrides
flyctl sftp get /data/participant_name_overrides.json data/participant_name_overrides.json.prod_backup -a prospector

# Verify download
cat data/participant_name_overrides.json.prod_backup | python -m json.tool | head -20
```

**Step 7.3: Migrate production override file locally**

```bash
# Copy production override file to local for migration
cp data/participant_name_overrides.json.prod_backup data/participant_name_overrides.json.prod_to_migrate

# Run migration script against production data
uv run python scripts/migrate_participant_overrides.py \
  --override-file data/participant_name_overrides.json.prod_to_migrate \
  --database data/tournament_data.duckdb.prod_backup

# Verify migration output
cat data/participant_name_overrides.json.prod_to_migrate | python -m json.tool | head -20
```

Expected: Should see challonge_match_id keys instead of match_id

**Step 7.4: Deploy new code**

```bash
# Deploy application with updated code
fly deploy -a prospector
```

Wait for deployment to complete (usually 2-3 minutes)

**Step 7.5: Upload migrated override file**

```bash
# Upload migrated override file to production
flyctl sftp shell -a prospector

# In SFTP shell:
put data/participant_name_overrides.json.prod_to_migrate /data/participant_name_overrides.json
chmod 664 /data/participant_name_overrides.json
exit
```

**Step 7.6: Restart app to pick up new override file**

```bash
fly apps restart prospector
```

**Step 7.7: Verify production deployment**

```bash
# Check app logs
fly logs -a prospector

# Look for:
# - "Loaded N participant name overrides" (should see this)
# - No error messages about overrides
# - Application started successfully
```

**Step 7.8: Test production UI**

Open https://prospector.fly.dev and verify:
- Overview page loads ✅
- Players page shows high linking rate ✅
- Pick order charts display data ✅
- No error messages in browser console ✅

**Step 7.9: Run production sync to verify robustness**

```bash
# Run full sync (downloads, imports, links)
./scripts/sync_tournament_data.sh prospector
```

Expected:
- Should complete successfully ✅
- Should show high participant linking rate ✅
- Override file should NOT need remapping ✅

**Rollback Plan** (if something goes wrong):

```bash
# 1. Restore backup database
flyctl sftp shell -a prospector
put data/tournament_data.duckdb.prod_backup /data/tournament_data.duckdb
exit

# 2. Restore backup override file
flyctl sftp shell -a prospector
put data/participant_name_overrides.json.prod_backup /data/participant_name_overrides.json
exit

# 3. Restart app
fly apps restart prospector

# 4. Verify app is working
fly logs -a prospector
```

**Success Criteria**:
- ✅ New code deployed
- ✅ Override file migrated
- ✅ App starts without errors
- ✅ UI displays correctly
- ✅ Full sync completes successfully
- ✅ No remapping needed

**Commit After This Task**:
```bash
git add -A
git commit -m "chore: Migrated production to use stable override keys

Successfully deployed override system changes to production:
- Deployed updated ParticipantMatcher code
- Migrated production participant_name_overrides.json to use challonge_match_id
- Verified production app functionality
- Confirmed overrides survive database re-import

Production now uses stable override keys across all override systems."
```

---

## Testing Strategy

### Unit Tests

**Location**: `tests/test_participant_matcher.py`

**Coverage**:
1. Override lookup uses challonge_match_id ✅ (Task 2)
2. Override format validation ✅
3. Challonge match ID conversion ✅
4. Missing challonge_match_id handling ✅
5. Invalid override keys rejected ✅

**Run Tests**:
```bash
uv run pytest tests/test_participant_matcher.py -v
```

### Integration Tests

**Manual Test Checklist**:
- [ ] Migration script converts all overrides correctly
- [ ] Participant linking works with migrated overrides
- [ ] Database re-import doesn't break overrides
- [ ] Pick order matching still works
- [ ] UI displays participant data correctly
- [ ] Override file survives sync operations
- [ ] Production deployment succeeds

### Regression Tests

**Verify we didn't break**:
1. Normal participant linking (without overrides)
2. Other override systems (winner, pick order, GDrive)
3. Match import from save files
4. Challonge participant sync
5. Web UI functionality

**Run Validation**:
```bash
# Check participant linking
uv run python scripts/link_players_to_participants.py

# Check pick order
uv run python scripts/match_pick_order_games.py

# Start UI and test manually
uv run python manage.py restart
```

---

## Migration Checklist

Use this checklist when performing the migration:

### Pre-Migration
- [ ] Read entire implementation plan
- [ ] Backup local database
- [ ] Backup production database
- [ ] Backup production override file
- [ ] Stop local server
- [ ] Ensure git working directory is clean

### Task Execution
- [ ] Task 1: Migration script created and tested
- [ ] Task 2: ParticipantMatcher updated and tested
- [ ] Task 3: Example template updated
- [ ] Task 4: Documentation updated
- [ ] Task 5: Obsolete script deleted
- [ ] Task 6: Integration tests pass
- [ ] Task 7: Production deployed successfully

### Verification
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Local override file unchanged after re-import
- [ ] Production override file unchanged after sync
- [ ] 100% participant linking maintained
- [ ] No error messages in logs
- [ ] UI displays correctly
- [ ] All git commits made with clear messages

### Cleanup
- [ ] Delete backup files (or move to archive)
- [ ] Delete migration script (one-time use)
- [ ] Update team documentation
- [ ] Close related issues/tickets

---

## Commit Strategy

### Atomic Commits

Each task should result in ONE commit:
1. ✅ feat: Add migration script
2. ✅ refactor: Use challonge_match_id for overrides
3. ✅ docs: Update override example template
4. ✅ docs: Update CLAUDE.md documentation
5. ✅ chore: Remove obsolete remap script
6. ✅ test: Verify re-import stability
7. ✅ chore: Production migration

### Commit Message Format

```
<type>: <short description>

<longer description explaining what and why>

<bullet points with specific changes>
```

**Types**:
- `feat:` - New feature or capability
- `fix:` - Bug fix
- `refactor:` - Code change that doesn't add features or fix bugs
- `docs:` - Documentation update
- `test:` - Test additions or changes
- `chore:` - Maintenance tasks (deployment, cleanup)

---

## Success Metrics

### Before Migration
- ❌ Override file breaks on database re-import
- ❌ Manual remapping required after each re-import
- ❌ Inconsistent override key types across systems
- ❌ Confusing for new developers

### After Migration
- ✅ Override file survives database re-import unchanged
- ✅ No remapping ever needed
- ✅ All override systems use stable external IDs
- ✅ Clear documentation with examples
- ✅ Simpler system (one less script)

---

## Troubleshooting Guide

### Migration Script Fails

**Symptom**: `migrate_participant_overrides.py` shows errors

**Possible Causes**:
1. Database doesn't have challonge_match_id column
   - Fix: Re-import data with latest schema
2. Override file has invalid JSON
   - Fix: Validate with `python -m json.tool`
3. Match IDs in override file don't exist in database
   - Fix: Check if matches were deleted from tournament

### Participant Linking Fails After Migration

**Symptom**: `link_players_to_participants.py` shows low match rate

**Debug Steps**:
1. Check override file format:
   ```bash
   cat data/participant_name_overrides.json | python -m json.tool
   ```
2. Check logs for "Using override" messages
3. Verify challonge_match_id values exist in database:
   ```bash
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT challonge_match_id FROM matches
   "
   ```
4. Check if any overrides reference deleted matches

### Production Deployment Issues

**Symptom**: Production app fails to start after deployment

**Debug Steps**:
1. Check Fly.io logs:
   ```bash
   fly logs -a prospector
   ```
2. Verify override file uploaded correctly:
   ```bash
   flyctl sftp shell -a prospector
   ls -la /data/participant_name_overrides.json
   cat /data/participant_name_overrides.json
   ```
3. Roll back if needed (see Task 7 rollback plan)

---

## Appendix

### Why Database match_id Is Unstable

Database `match_id` is an auto-incrementing primary key assigned during INSERT:

```sql
CREATE TABLE matches (
    match_id INTEGER PRIMARY KEY,  -- Auto-increment
    challonge_match_id INTEGER,
    ...
);

-- First import
INSERT INTO matches (...) VALUES (...);  -- Gets match_id=1
INSERT INTO matches (...) VALUES (...);  -- Gets match_id=2

-- After DROP TABLE and re-import (different order!)
INSERT INTO matches (...) VALUES (...);  -- Gets match_id=1 (DIFFERENT MATCH!)
INSERT INTO matches (...) VALUES (...);  -- Gets match_id=2 (DIFFERENT MATCH!)
```

Import order varies based on:
- File system directory iteration (undefined order)
- Challonge API response order (can vary)
- Multi-threaded processing order (non-deterministic)
- Network timing variations

### Why challonge_match_id Is Stable

`challonge_match_id` is assigned by Challonge's servers when the match is created:

```
Tournament bracket created → Challonge assigns match IDs (426504730, 426504734, ...)
                           ↓
                    Never changes
                           ↓
            Retrieved via API every sync
                           ↓
            Stored in database as-is
```

Properties:
- Globally unique within tournament
- Assigned once, never changes
- Independent of import order
- Same across all systems

### Override System Comparison Table

| System | File | Key | Stability | Re-import Safe? | Uses External ID? |
|--------|------|-----|-----------|----------------|-------------------|
| Winner | `match_winner_overrides.json` | `challonge_match_id` | ✅ Stable | ✅ Yes | ✅ Yes |
| Pick Order | `pick_order_overrides.json` | `game_number` | ✅ Stable | ✅ Yes | ✅ Yes (sheet) |
| GDrive | `gdrive_match_mapping_overrides.json` | `challonge_match_id` | ✅ Stable | ✅ Yes | ✅ Yes |
| Participant (BEFORE) | `participant_name_overrides.json` | `match_id` | ❌ UNSTABLE | ❌ NO | ❌ NO |
| Participant (AFTER) | `participant_name_overrides.json` | `challonge_match_id` | ✅ Stable | ✅ Yes | ✅ Yes |

### SQL Queries Reference

**Find challonge_match_id for a match**:
```sql
SELECT match_id, challonge_match_id, player1_name, player2_name
FROM matches
WHERE player1_name LIKE '%PlayerName%'
   OR player2_name LIKE '%PlayerName%';
```

**Find participant_id for a player**:
```sql
SELECT participant_id, display_name, display_name_normalized
FROM tournament_participants
WHERE display_name LIKE '%PlayerName%';
```

**Check participant linking coverage**:
```sql
SELECT
    COUNT(*) as total_players,
    COUNT(participant_id) as linked_players,
    ROUND(COUNT(participant_id) * 100.0 / COUNT(*), 1) as coverage_pct
FROM players;
```

**List all overrides with match details**:
```sql
-- Note: Run this query after loading overrides into temp table
-- This is just an example of what you might want to check
SELECT
    m.match_id,
    m.challonge_match_id,
    m.player1_name,
    m.player2_name,
    p.player_name,
    p.participant_id
FROM matches m
JOIN players p ON m.match_id = p.match_id
WHERE m.challonge_match_id IN (426504734, 426504756, ...)  -- Your override match IDs
ORDER BY m.challonge_match_id, p.player_id;
```

---

## Time Estimates

| Task | Estimated Time | Notes |
|------|---------------|-------|
| Task 1: Migration script | 45 min | Writing + testing |
| Task 2: Update ParticipantMatcher | 60 min | Code + tests |
| Task 3: Update template | 10 min | Simple edit |
| Task 4: Update docs | 20 min | Documentation |
| Task 5: Delete script | 5 min | Quick cleanup |
| Task 6: Integration test | 30 min | Thorough testing |
| Task 7: Production deploy | 45 min | Careful deployment |
| **TOTAL** | **~3.5 hours** | For experienced dev |

Add 50-100% time buffer for:
- Debugging issues
- Unexpected edge cases
- Code review feedback
- Documentation review

**Recommended approach**:
- Do tasks 1-5 in one session (2 hours)
- Do task 6 in separate session after break (0.5 hours)
- Do task 7 during low-traffic period (1 hour)

---

## Related Documentation

- `docs/plans/pick-order-integration-implementation-plan.md` - Pick order system design
- `docs/plans/match-winner-override-implementation-plan.md` - Winner override system
- `docs/migrations/008_add_pick_order_tracking.md` - Pick order schema
- `CLAUDE.md` - Main project documentation

---

## Questions & Answers

**Q: Why not just use match_id if we have a remap script?**
A: The remap script is a workaround that adds complexity, can fail, and requires manual intervention. Using stable IDs eliminates the problem entirely.

**Q: What if challonge_match_id is NULL for some matches?**
A: This would indicate a local-only match (not from Challonge). For now, our system only handles Challonge matches. We log a warning and skip override lookup for such matches.

**Q: Can we migrate gradually instead of all at once?**
A: No. The override file format must be consistent. You can't have some keys as match_id and others as challonge_match_id. Do the migration in one go.

**Q: What if I find a bug during migration?**
A: Stop immediately, restore backups, fix the bug, test thoroughly, then restart the migration from the beginning.

**Q: Do I need to update existing participant_name_overrides.json in production?**
A: Yes, Task 7 handles this. The migration script will convert it automatically.

---

## Sign-Off

After completing all tasks:

- [ ] All tasks completed successfully
- [ ] All tests passing
- [ ] Local system working correctly
- [ ] Production deployed and verified
- [ ] Documentation updated
- [ ] Team notified of changes

**Completed by**: ___________________
**Date**: ___________________
**Verified by**: ___________________
**Date**: ___________________
