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
- `tournament_visualizer/data/database.py:1286` - insert_match method
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
