# Migration 003: Add Rulers Table

## Overview
Adds a new `rulers` table to track all rulers for each player throughout a match, including archetype and starting trait information.

## Schema Changes

### New Table: `rulers`

```sql
CREATE TABLE rulers (
    ruler_id INTEGER PRIMARY KEY,
    match_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,
    character_id INTEGER NOT NULL,
    ruler_name VARCHAR,
    archetype VARCHAR,
    starting_trait VARCHAR,
    succession_order INTEGER NOT NULL,
    succession_turn INTEGER NOT NULL,
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id)
);
```

## SQL Migration Script

```sql
-- Create the rulers table
CREATE TABLE IF NOT EXISTS rulers (
    ruler_id INTEGER PRIMARY KEY,
    match_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,
    character_id INTEGER NOT NULL,
    ruler_name VARCHAR,
    archetype VARCHAR,
    starting_trait VARCHAR,
    succession_order INTEGER NOT NULL,
    succession_turn INTEGER NOT NULL,
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id)
);

-- Record migration
INSERT INTO schema_migrations (version, description, applied_at)
VALUES (3, 'Add rulers table', CURRENT_TIMESTAMP);
```

## Rollback Procedure

```sql
-- Drop the table
DROP TABLE IF EXISTS rulers;

-- Remove migration record
DELETE FROM schema_migrations WHERE version = 3;
```

## Verification

After applying migration:

```sql
-- Verify table exists
SELECT name FROM sqlite_master WHERE type='table' AND name='rulers';

-- Verify schema
PRAGMA table_info(rulers);

-- Verify migration recorded
SELECT * FROM schema_migrations WHERE version = 3;
```

## Related Files
- Parser: `tournament_visualizer/data/parser.py` (will need `extract_rulers()` method)
- Database: `tournament_visualizer/data/database.py` (will need `insert_rulers()` method)
- ETL: `tournament_visualizer/data/etl.py` (will need to call extraction and insertion)

## Data Population
After migration, re-import all save files to populate the rulers table:
```bash
uv run python scripts/import_attachments.py --directory saves --force --verbose
```
