# Migration 005: Add Tile Details to Territories

**Date:** 2025-10-30
**Status:** Pending

## Summary
Extends territories table with improvement_type, specialist_type, resource_type, and has_road columns.

## Forward Migration
```sql
-- DuckDB doesn't support ALTER ADD COLUMN reliably
-- Use parser changes + re-import instead
-- New territories will be created with new columns automatically
```

## Rollback
Drop new columns if needed:
```sql
ALTER TABLE territories DROP COLUMN improvement_type;
ALTER TABLE territories DROP COLUMN specialist_type;
ALTER TABLE territories DROP COLUMN resource_type;
ALTER TABLE territories DROP COLUMN has_road;
```

## Affected Queries
- None (new columns, backward compatible)

## Testing
Run: `uv run python scripts/validate_territory_data.py` (to be created)

## Data Re-import Required
Yes - full re-import needed to populate new columns
