# Migration 008: Add Pick Order Tracking

## Overview

Adds support for tracking nation pick order (first pick vs second pick) from Google Sheets data.

**Date:** 2025-10-17
**Author:** System
**Status:** Pending

---

## Changes

### New Table: pick_order_games

Stores parsed pick order data from Google Sheets before matching to database.

```sql
CREATE TABLE pick_order_games (
    game_number INTEGER PRIMARY KEY,
    round_number INTEGER NOT NULL,
    round_label VARCHAR,

    player1_sheet_name VARCHAR NOT NULL,
    player2_sheet_name VARCHAR NOT NULL,

    first_pick_nation VARCHAR NOT NULL,
    second_pick_nation VARCHAR NOT NULL,

    first_picker_sheet_name VARCHAR,
    second_picker_sheet_name VARCHAR,

    matched_match_id BIGINT,
    first_picker_participant_id BIGINT,
    second_picker_participant_id BIGINT,
    match_confidence VARCHAR,
    match_reason VARCHAR,

    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    matched_at TIMESTAMP,

    FOREIGN KEY (matched_match_id) REFERENCES matches(match_id),
    FOREIGN KEY (first_picker_participant_id) REFERENCES tournament_participants(participant_id),
    FOREIGN KEY (second_picker_participant_id) REFERENCES tournament_participants(participant_id)
);
```

### Updated Table: matches

Adds columns to track pick order for matched games.

```sql
ALTER TABLE matches
ADD COLUMN first_picker_participant_id BIGINT,
ADD COLUMN second_picker_participant_id BIGINT;

ALTER TABLE matches
ADD FOREIGN KEY (first_picker_participant_id)
    REFERENCES tournament_participants(participant_id);

ALTER TABLE matches
ADD FOREIGN KEY (second_picker_participant_id)
    REFERENCES tournament_participants(participant_id);
```

---

## Migration Procedure

### Step 1: Backup Database

```bash
cp data/tournament_data.duckdb data/tournament_data.duckdb.backup_$(date +%Y%m%d_%H%M%S)
```

### Step 2: Apply Schema Changes

Schema changes are applied automatically on next import:

```bash
uv run python scripts/import_attachments.py --directory saves
```

Or run schema initialization directly:

```bash
uv run python -c "
from tournament_visualizer.data.schema import initialize_schema
from tournament_visualizer.config import Config
import duckdb

conn = duckdb.connect(Config.DUCKDB_PATH)
initialize_schema(conn)
conn.close()
print('Schema updated')
"
```

### Step 3: Verify Schema

```bash
uv run duckdb data/tournament_data.duckdb -readonly -c "DESCRIBE pick_order_games"
uv run duckdb data/tournament_data.duckdb -readonly -c "DESCRIBE matches" | grep picker
```

Should show the new columns.

---

## Rollback Procedure

### Rollback SQL

```sql
-- Remove columns from matches table
ALTER TABLE matches DROP COLUMN first_picker_participant_id;
ALTER TABLE matches DROP COLUMN second_picker_participant_id;

-- Drop pick_order_games table
DROP TABLE IF EXISTS pick_order_games;
```

### Rollback Steps

```bash
uv run duckdb data/tournament_data.duckdb << 'EOF'
ALTER TABLE matches DROP COLUMN IF EXISTS first_picker_participant_id;
ALTER TABLE matches DROP COLUMN IF EXISTS second_picker_participant_id;
DROP TABLE IF EXISTS pick_order_games;
EOF
```

Or restore from backup:
```bash
cp data/tournament_data.duckdb.backup_YYYYMMDD_HHMMSS data/tournament_data.duckdb
```

---

## Verification

```bash
# Check table exists
uv run duckdb data/tournament_data.duckdb -readonly -c "SELECT COUNT(*) FROM pick_order_games"

# Check matches columns exist
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT
    first_picker_participant_id,
    second_picker_participant_id
FROM matches
LIMIT 1
"
```

---

## Related Files

**Schema:**
- `tournament_visualizer/data/schema.py` - Table definitions

**Scripts:**
- `scripts/sync_pick_order_data.py` - Fetches and parses sheet data
- `scripts/match_pick_order_games.py` - Matches games to database

**Documentation:**
- `docs/plans/pick-order-integration-implementation-plan.md` - Full implementation plan
- `CLAUDE.md` - Usage documentation

---

## Impact

**Breaking Changes:** None
**Data Loss Risk:** None (new tables/columns only)
**Requires Re-import:** No
**Affects Queries:** Adds new analytics capabilities

---

## Notes

- Schema changes are idempotent (safe to run multiple times)
- Foreign keys ensure referential integrity
- NULL values in matches table columns indicate pick order data not available
- pick_order_games table may have unmatched entries (matched_match_id NULL)
