# Migration 004: Add City Tables

## Overview
Add support for tracking cities and their production in tournament matches.
Enables analysis of expansion patterns, production strategies, and territorial control.

## Rationale
- Save files contain detailed city data (population, production, ownership)
- Cities are fundamental to Old World gameplay strategy
- Need to track expansion speed (when cities founded)
- Need to track production focus (military vs. economy)
- Need to detect city captures (FirstPlayer vs. LastPlayer)

## Schema Changes

### New Table: `cities`
```sql
CREATE TABLE cities (
    city_id INTEGER NOT NULL,
    match_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,
    city_name VARCHAR NOT NULL,
    tile_id INTEGER NOT NULL,
    founded_turn INTEGER NOT NULL,
    family_name VARCHAR,
    is_capital BOOLEAN DEFAULT FALSE,
    population INTEGER,
    first_player_id BIGINT,
    governor_id INTEGER,
    PRIMARY KEY (match_id, city_id)
);

CREATE INDEX idx_cities_match_id ON cities(match_id);
CREATE INDEX idx_cities_player_id ON cities(match_id, player_id);
CREATE INDEX idx_cities_founded_turn ON cities(match_id, founded_turn);
```

### New Table: `city_unit_production`
```sql
CREATE TABLE city_unit_production (
    production_id INTEGER PRIMARY KEY,
    match_id BIGINT NOT NULL,
    city_id INTEGER NOT NULL,
    unit_type VARCHAR NOT NULL,
    count INTEGER NOT NULL
);

CREATE INDEX idx_city_production_match_city ON city_unit_production(match_id, city_id);
CREATE INDEX idx_city_production_unit_type ON city_unit_production(unit_type);
```

### New Table: `city_projects`
```sql
CREATE TABLE city_projects (
    project_id INTEGER PRIMARY KEY,
    match_id BIGINT NOT NULL,
    city_id INTEGER NOT NULL,
    project_type VARCHAR NOT NULL,
    count INTEGER NOT NULL
);

CREATE INDEX idx_city_projects_match_city ON city_projects(match_id, city_id);
CREATE INDEX idx_city_projects_type ON city_projects(project_type);
```

## Migration Script

See: `scripts/migrate_add_city_tables.py`

Run with:
```bash
# Backup first!
cp data/tournament_data.duckdb data/tournament_data.duckdb.backup_$(date +%Y%m%d_%H%M%S)

# Apply migration
uv run python scripts/migrate_add_city_tables.py

# Verify
uv run python scripts/migrate_add_city_tables.py --verify
```

## Rollback Procedure

To undo this migration:
```bash
uv run python scripts/migrate_add_city_tables.py --rollback
```

Or manually:
```sql
DROP TABLE IF EXISTS city_projects;
DROP TABLE IF EXISTS city_unit_production;
DROP TABLE IF EXISTS cities;
```

## Verification

After migration, verify:
```bash
# Check tables exist
uv run duckdb data/tournament_data.duckdb -readonly -c "SHOW TABLES"

# Should show: cities, city_unit_production, city_projects

# Check schema
uv run duckdb data/tournament_data.duckdb -readonly -c "DESCRIBE cities"
```

## Data Population

After migration, re-import tournament data:
```bash
# Backup database
cp data/tournament_data.duckdb data/tournament_data.duckdb.backup_before_reimport

# Re-import with city data
uv run python scripts/import_attachments.py --directory saves --force --verbose
```

## Related Files
- `tournament_visualizer/data/parser.py`: Parses city data from XML
- `tournament_visualizer/data/database.py`: Inserts city data
- `tournament_visualizer/data/queries.py`: Queries city data
- `scripts/validate_city_data.py`: Validates city data quality

## Impact Assessment

**Data Size**: Expect ~10-15 cities per match
- 27 matches × 12 cities/match ≈ 324 city records
- Each city has ~5 unit types ≈ 1,620 production records
- Low storage impact (< 100 KB total)

**Query Performance**: Indexes on match_id and player_id
- City lookups by match: O(log n) via index
- Production analysis: O(log n) via unit_type index
- No performance concerns for this data size

**Breaking Changes**: None
- Only adds new tables
- Existing queries unaffected
- Requires data re-import to populate
