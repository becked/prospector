# Migration 009: Add Match Narrative Summary

## Overview

Adds AI-generated narrative summaries to matches table.

**Date:** 2025-10-19
**Author:** System
**Status:** Pending

---

## Changes

### Updated Table: matches

Adds column to store AI-generated narrative summary.

```sql
ALTER TABLE matches
ADD COLUMN narrative_summary TEXT;
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
uv run duckdb data/tournament_data.duckdb -readonly -c "DESCRIBE matches" | grep narrative
```

Should show:
```
│ narrative_summary │ VARCHAR │ YES │ NULL │ NULL │ NULL │
```

---

## Rollback Procedure

```bash
# Restore from backup
cp data/tournament_data.duckdb.backup_YYYYMMDD_HHMMSS data/tournament_data.duckdb

# Or drop column (DuckDB supports this)
uv run duckdb data/tournament_data.duckdb -c "ALTER TABLE matches DROP COLUMN narrative_summary"
```

---

## Related Files

- `tournament_visualizer/data/schema.py` - Schema definition
- `scripts/generate_match_narratives.py` - Script to populate narratives (Task 3+)
