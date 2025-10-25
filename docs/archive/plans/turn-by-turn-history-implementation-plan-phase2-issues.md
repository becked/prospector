# Phase 2 Implementation Issues & Fixes

> **Status**: Completed and archived (2025-10-25)
>
> Feature complete. See migrations/002_add_history_tables.md.

**Date:** October 9, 2025
**Status:** Issues Identified - Fixes Required
**Phase:** 2 - Schema Design & Migration

---

## Overview

Phase 2 implementation is **nearly complete** but has **2 critical issues** that must be fixed before proceeding to Phase 3.

### Status Summary
- ✅ **Task 2.1:** Schema definitions added to `database.py`
- ⚠️ **Task 2.2:** Migration script missing sequences and table rename needs code updates

---

## Issue #1: Migration Script Missing Sequences

### Severity: 🔴 CRITICAL

### Problem
The migration script `scripts/migrations/002_add_history_tables.py` creates the new history tables but **does not create the corresponding DuckDB sequences**.

When insertion methods try to generate IDs using `nextval('points_history_id_seq')`, they will fail with:
```
Error: Catalog Error: Sequence with name "points_history_id_seq" does not exist!
```

### Root Cause
The `create_schema()` method in `database.py` creates sequences (lines 166-170), but the migration script operates on an existing database and only creates tables, not sequences.

### Impact
- Data import will fail completely
- All bulk insertion methods for history tables will crash
- Unable to proceed to Phase 3 testing

### Fix Required

**File:** `scripts/migrations/002_add_history_tables.py`
**Location:** After line 44 (after renaming resources table)

Add this code:

```python
# 2.5. Create sequences for new tables
print("  - Creating sequences for new tables...")
conn.execute("CREATE SEQUENCE IF NOT EXISTS points_history_id_seq START 1")
conn.execute("CREATE SEQUENCE IF NOT EXISTS military_history_id_seq START 1")
conn.execute("CREATE SEQUENCE IF NOT EXISTS legitimacy_history_id_seq START 1")
conn.execute("CREATE SEQUENCE IF NOT EXISTS family_opinion_id_seq START 1")
conn.execute("CREATE SEQUENCE IF NOT EXISTS religion_opinion_id_seq START 1")
```

### Updated Migration Script (lines 37-52)

```python
# 2. Rename resources to player_yield_history
print("  - Renaming resources to player_yield_history...")
# Check if table exists and is empty before renaming
count = conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
if count > 0:
    print(f"    WARNING: resources table has {count} rows! Skipping rename.")
else:
    conn.execute("ALTER TABLE resources RENAME TO player_yield_history")

# 2.5. Create sequences for new tables
print("  - Creating sequences for new tables...")
conn.execute("CREATE SEQUENCE IF NOT EXISTS points_history_id_seq START 1")
conn.execute("CREATE SEQUENCE IF NOT EXISTS military_history_id_seq START 1")
conn.execute("CREATE SEQUENCE IF NOT EXISTS legitimacy_history_id_seq START 1")
conn.execute("CREATE SEQUENCE IF NOT EXISTS family_opinion_id_seq START 1")
conn.execute("CREATE SEQUENCE IF NOT EXISTS religion_opinion_id_seq START 1")

# 3. Create player_points_history table
print("  - Creating player_points_history table...")
```

---

## Issue #2: Resources Table Rename Breaks Existing Code

### Severity: 🟡 HIGH

### Problem
The migration renames `resources` → `player_yield_history`, but the existing `bulk_insert_resources()` method in `database.py` still references the old table name.

**Current code (lines 833-865):**
```python
def bulk_insert_resources(self, resources_data: List[Dict[str, Any]]) -> None:
    """Bulk insert resource records for better performance.

    Args:
        resources_data: List of resource dictionaries
    """
    if not resources_data:
        return

    with self.get_connection() as conn:
        query = """
        INSERT INTO resources (  # ← OLD TABLE NAME
            resource_id, match_id, player_id, turn_number, resource_type, amount
        ) VALUES (?, ?, ?, ?, ?, ?)
        """
        # ... rest of method
```

After migration, this table won't exist, causing insertion to fail.

### Root Cause
Migration changes database schema but code still references old table name.

### Impact
- If any existing code calls `bulk_insert_resources()`, it will fail
- Import scripts may break if they reference the old method
- Inconsistency between database schema and code

### User Decision
**Option B Selected:** Rename table in migration AND update all code references.

---

## Fix for Issue #2

### Changes Required

#### Change 1: Update `bulk_insert_resources()` Method Name and Table Reference

**File:** `tournament_visualizer/data/database.py`
**Lines:** 833-865

**Option A - Rename method to match new purpose:**
```python
def bulk_insert_yield_history(self, yield_data: List[Dict[str, Any]]) -> None:
    """Bulk insert yield rate history records.

    Args:
        yield_data: List of yield history dictionaries
    """
    if not yield_data:
        return

    with self.get_connection() as conn:
        query = """
        INSERT INTO player_yield_history (
            resource_id, match_id, player_id, turn_number, resource_type, amount
        ) VALUES (?, ?, ?, ?, ?, ?)
        """

        values = []
        for resource in yield_data:
            resource_id = conn.execute(
                "SELECT nextval('resources_id_seq')"
            ).fetchone()[0]
            values.append([
                resource_id,
                resource["match_id"],
                resource["player_id"],
                resource["turn_number"],
                resource["resource_type"],
                resource["amount"],
            ])

        conn.executemany(query, values)
```

**Option B - Keep method name but update table:**
```python
def bulk_insert_resources(self, resources_data: List[Dict[str, Any]]) -> None:
    """Bulk insert resource/yield history records.

    Note: 'resources' table was renamed to 'player_yield_history' for clarity,
    but this method maintains backwards compatibility.

    Args:
        resources_data: List of resource dictionaries
    """
    if not resources_data:
        return

    with self.get_connection() as conn:
        query = """
        INSERT INTO player_yield_history (
            resource_id, match_id, player_id, turn_number, resource_type, amount
        ) VALUES (?, ?, ?, ?, ?, ?)
        """
        # ... rest unchanged
```

**Recommendation:** Use **Option A** (rename method) for clarity and consistency with other history methods (`bulk_insert_points_history`, etc.). This follows the principle that the code should reflect the domain clearly.

#### Change 2: Search and Update All References

Run these commands to find all references:
```bash
# Find all references to bulk_insert_resources
grep -rn "bulk_insert_resources" tournament_visualizer/ scripts/

# Find all references to the resources table (excluding schema definitions)
grep -rn '"resources"' tournament_visualizer/ scripts/ | grep -v "CREATE TABLE"
```

Likely locations to update:
- `scripts/import_tournaments.py` - May call `bulk_insert_resources()`
- Any test files - May test the old method
- Any analytics scripts - May query the old table name

#### Change 3: Update Migration Documentation

**File:** `docs/migrations/002_add_history_tables.md`
**Section:** Related Changes

Add note about method rename:
```markdown
## Related Changes

- Parser: `tournament_visualizer/parser/parser.py` - New extraction methods
- Database: `tournament_visualizer/data/database.py` - New table creation methods AND method rename
  - `bulk_insert_resources()` → `bulk_insert_yield_history()` (renamed for clarity)
  - Table reference updated: `resources` → `player_yield_history`
- Scripts: `scripts/import_tournaments.py` - Update calls to use new method name
- Tests: `tests/test_parser.py` - Tests for new extraction methods
```

---

## Implementation Checklist

### Issue #1 Fix
- [ ] Add sequence creation to migration script (lines 45-50)
- [ ] Test migration script on backup database
- [ ] Verify sequences exist after migration
- [ ] Commit: `fix: Add sequence creation to history tables migration`

### Issue #2 Fix
- [ ] Rename `bulk_insert_resources()` → `bulk_insert_yield_history()` in `database.py`
- [ ] Update method docstring to reflect new purpose
- [ ] Search for all references to `bulk_insert_resources()` and update
- [ ] Update migration documentation with method rename note
- [ ] Test that no code references old method name
- [ ] Commit: `refactor: Rename bulk_insert_resources to bulk_insert_yield_history`

### Verification
- [ ] Run migration script: `uv run python scripts/migrations/002_add_history_tables.py`
- [ ] Check tables exist: `uv run duckdb tournament_data.duckdb -readonly -c "SHOW TABLES"`
- [ ] Check sequences exist: `uv run duckdb tournament_data.duckdb -readonly -c "SHOW SEQUENCES"`
- [ ] Verify no Python import errors: `uv run python -c "from tournament_visualizer.data.database import TournamentDatabase"`
- [ ] Rollback test: `uv run python scripts/migrations/002_add_history_tables.py --rollback`

---

## Testing After Fixes

### Test 1: Migration Runs Successfully
```bash
# Backup current database
cp tournament_data.duckdb tournament_data.duckdb.test_backup

# Run migration
uv run python scripts/migrations/002_add_history_tables.py

# Expected output:
# Creating backup: tournament_data.duckdb.backup_002
# Migrating database: tournament_data.duckdb
#   - Dropping game_state table...
#   - Renaming resources to player_yield_history...
#   - Creating sequences for new tables...
#   - Creating player_points_history table...
#   - Creating player_military_history table...
#   - Creating player_legitimacy_history table...
#   - Creating family_opinion_history table...
#   - Creating religion_opinion_history table...
# Migration completed successfully!
```

### Test 2: Sequences Exist
```bash
uv run duckdb tournament_data.duckdb -readonly -c "
SELECT sequence_name
FROM duckdb_sequences()
WHERE sequence_name LIKE '%history%'
ORDER BY sequence_name
"

# Expected output:
# family_opinion_id_seq
# legitimacy_history_id_seq
# military_history_id_seq
# points_history_id_seq
```

### Test 3: Table Renamed
```bash
uv run duckdb tournament_data.duckdb -readonly -c "SHOW TABLES" | grep -E "(resources|yield_history)"

# Expected output:
# player_yield_history  (not resources)
```

### Test 4: No Import Errors
```bash
uv run python -c "
from tournament_visualizer.data.database import TournamentDatabase
db = TournamentDatabase()
print('✓ Imports successful')
print('✓ Method exists:', hasattr(db, 'bulk_insert_yield_history'))
"

# Expected output:
# ✓ Imports successful
# ✓ Method exists: True
```

---

## Timeline Impact

**Original Phase 2 estimate:** 2 hours
**Time spent:** ~1.5 hours (good progress!)
**Fix time needed:** 30-45 minutes
**New Phase 2 total:** ~2.5 hours

**Overall project impact:** Minimal - still on track for 14-15 hour total.

---

## Next Steps After Fixes

Once both issues are fixed and verified:

1. **Commit all changes** with proper messages
2. **Proceed to Phase 3** - Parser Implementation (TDD)
3. Continue following the implementation plan

---

## Questions?

If you encounter any issues while implementing these fixes:
1. Check the verification commands above
2. Review error messages carefully
3. Ensure database backup exists before retrying migration
4. Use rollback if needed: `uv run python scripts/migrations/002_add_history_tables.py --rollback`
