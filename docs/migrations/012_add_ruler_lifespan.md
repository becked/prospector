# Migration 012: Add Ruler Lifespan Columns

## Overview
Adds `birth_turn` and `death_turn` columns to the `rulers` table to enable calculating ruler age at death and other lifespan analytics.

## Motivation
Tracking ruler lifespan enables analysis of:
- Age at death (earliest ruler deaths in tournament)
- Age when taking power (succession_turn - birth_turn)
- Ruler longevity patterns across matches

## Schema Changes

### Add Columns
```sql
ALTER TABLE rulers ADD COLUMN birth_turn INTEGER;
ALTER TABLE rulers ADD COLUMN death_turn INTEGER;
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
    cognomen VARCHAR,
    birth_turn INTEGER,     -- NEW: can be negative (born before game start)
    death_turn INTEGER,     -- NEW: NULL if ruler still alive at game end
    succession_order INTEGER NOT NULL,
    succession_turn INTEGER NOT NULL
);
```

## Data Population
The birth and death turns are extracted from the XML Character element:
```xml
<Character ID="2" BirthTurn="-20" ...>
    <DeathTurn>43</DeathTurn>
</Character>
```

- `BirthTurn` is an attribute (can be negative for characters born before game start)
- `DeathTurn` is a child element (only present if character has died)

Age at death = death_turn - birth_turn

## Rollback
```sql
ALTER TABLE rulers DROP COLUMN birth_turn;
ALTER TABLE rulers DROP COLUMN death_turn;
```

## Related Changes
- `tournament_visualizer/data/parser.py`: Extract birth_turn and death_turn in `extract_rulers()`
- `tournament_visualizer/data/database.py`: Update `_create_rulers_table()` and `bulk_insert_rulers()`

## Testing
After migration and re-import:
```sql
-- Verify birth_turn distribution
SELECT
    CASE
        WHEN birth_turn < 0 THEN 'Pre-game'
        WHEN birth_turn <= 10 THEN 'Early game'
        ELSE 'Mid-late game'
    END as birth_period,
    COUNT(*) as count
FROM rulers
GROUP BY 1;

-- Check death_turn population (alive vs deceased)
SELECT
    CASE
        WHEN death_turn IS NULL THEN 'Alive'
        ELSE 'Deceased'
    END as status,
    COUNT(*) as count
FROM rulers
GROUP BY 1;

-- Calculate ruler lifespans
SELECT
    r.ruler_name,
    r.birth_turn,
    r.death_turn,
    r.death_turn - r.birth_turn as age_at_death,
    p.player_name
FROM rulers r
JOIN players p ON r.match_id = p.match_id AND r.player_id = p.player_id
WHERE r.death_turn IS NOT NULL
ORDER BY age_at_death ASC
LIMIT 20;
```
