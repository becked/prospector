# Migration 011: Add Cognomen to Rulers Table

## Overview
Adds a `cognomen` column to the `rulers` table to store each ruler's title (e.g., "the Lion", "the Great").

## Motivation
Cognomens contribute to player legitimacy. Each ruler earns a cognomen based on their achievements, and these provide legitimacy bonuses that decay for previous rulers. This enables displaying a detailed legitimacy breakdown on the match page.

## Schema Changes

### Add Column
```sql
ALTER TABLE rulers ADD COLUMN cognomen VARCHAR;
```

### Updated Table Structure
```sql
CREATE TABLE rulers (
    ruler_id INTEGER NOT NULL,
    match_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,
    character_id INTEGER NOT NULL,
    ruler_name VARCHAR,
    archetype VARCHAR,
    starting_trait VARCHAR,
    cognomen VARCHAR,              -- NEW: e.g., "Lion", "Great", "Wise"
    succession_order INTEGER NOT NULL,
    succession_turn INTEGER NOT NULL
);
```

## Data Population
The cognomen is extracted from the XML Character element:
```xml
<Character ID="2" ...>
    <Cognomen>COGNOMEN_LION</Cognomen>
</Character>
```

The parser strips the `COGNOMEN_` prefix and formats it (e.g., "Lion").

## Rollback
```sql
ALTER TABLE rulers DROP COLUMN cognomen;
```

## Related Changes
- `tournament_visualizer/data/parser.py`: Extract cognomen in `extract_rulers()`
- `tournament_visualizer/data/database.py`: Update `bulk_insert_rulers()`
- `tournament_visualizer/config.py`: Add `COGNOMEN_LEGITIMACY` values

## Testing
After migration and re-import:
```sql
-- Verify cognomens were populated
SELECT cognomen, COUNT(*) as count
FROM rulers
WHERE cognomen IS NOT NULL
GROUP BY cognomen
ORDER BY count DESC;

-- Check rulers with cognomens
SELECT match_id, player_id, ruler_name, cognomen, succession_order
FROM rulers
ORDER BY match_id, player_id, succession_order
LIMIT 20;
```
