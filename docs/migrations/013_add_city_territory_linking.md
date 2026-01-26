# Migration 013: Add City Territory Linking

**Date:** 2025-01-25
**Status:** Pending Re-import

## Summary
Adds `city_id` column to territories table to link each tile to its controlling city. This enables:
- Counting specialists per city for Sages family bonus calculation
- City-level analysis of infrastructure

## Schema Change

```sql
-- Add city_id column to territories table
ALTER TABLE territories ADD COLUMN city_id INTEGER;

-- Add index for city lookups
CREATE INDEX IF NOT EXISTS idx_territories_city ON territories(match_id, city_id);
```

Note: DuckDB doesn't support ALTER ADD COLUMN reliably. Schema is already updated in `database.py`. Re-import required.

## Parser Change

In `parser.py` `extract_territories()`, now extracts `<CityTerritory>` element:
```python
city_territory_elem = tile_elem.find("CityTerritory")
city_id = (
    int(city_territory_elem.text)
    if city_territory_elem is not None and city_territory_elem.text
    else None
)
```

## Files Modified

| File | Changes |
|------|---------|
| `tournament_visualizer/data/database.py` | Added `city_id INTEGER` column + index to territories schema |
| `tournament_visualizer/data/database.py` | Updated `bulk_insert_territories()` to include city_id |
| `tournament_visualizer/data/parser.py` | Added CityTerritory extraction in `extract_territories()` |

## Rollback

```sql
-- Remove city_id column
ALTER TABLE territories DROP COLUMN city_id;

-- Remove index
DROP INDEX IF EXISTS idx_territories_city;
```

To rollback parser changes, revert the three edits in `parser.py`.

## Data Re-import Required

Yes - full re-import needed to populate city_id for all territories.

```bash
# Backup database first
cp data/tournament_data.duckdb data/tournament_data.duckdb.backup_$(date +%Y%m%d_%H%M%S)

# Re-import all saves
uv run python scripts/import_attachments.py --directory saves --force --verbose
```

## Verification

After re-import:
```bash
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT
    COUNT(*) as total,
    COUNT(city_id) as with_city,
    COUNT(*) - COUNT(city_id) as without_city
FROM territories
WHERE match_id = 1
"
```

Expected: ~30% of tiles should have city_id (city-controlled), ~70% without (water, neutral, etc.)

## Related Features

This migration enables:
1. **Sages Family Bonus**: Count specialists in FAMILY_AMORITE, FAMILY_THUTMOSID, FAMILY_ALCMAEONID cities
2. **City Infrastructure Analysis**: Track improvements/specialists per city over time
