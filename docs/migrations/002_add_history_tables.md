# Migration 002: Add Turn-by-Turn History Tables

**Date:** October 9, 2025
**Status:** Ready to Apply

## Overview

This migration adds support for turn-by-turn historical data from Old World save files.

### Changes

1. **Drops:** `game_state` table (broken - all rows have turn_number=0)
2. **Renames:** `resources` → `player_yield_history` (was empty, now used for YieldRateHistory)
3. **Creates:** 5 new history tables
   - `player_points_history` - Victory points per turn
   - `player_military_history` - Military power per turn
   - `player_legitimacy_history` - Legitimacy per turn
   - `family_opinion_history` - Family opinions per turn
   - `religion_opinion_history` - Religion opinions per turn

## Running the Migration

```bash
# Backup is created automatically
uv run python scripts/migrations/002_add_history_tables.py
```

## Verification

```bash
# Check new tables exist
uv run duckdb tournament_data.duckdb -readonly -c "SHOW TABLES"

# Should see:
# - player_yield_history (renamed from resources)
# - player_points_history (new)
# - player_military_history (new)
# - player_legitimacy_history (new)
# - family_opinion_history (new)
# - religion_opinion_history (new)

# Should NOT see:
# - game_state (dropped)
# - resources (renamed)
```

## Rollback Procedure

```bash
uv run python scripts/migrations/002_add_history_tables.py --rollback
```

This restores the database from the automatic backup created before migration.

## Related Changes

- Parser: `tournament_visualizer/parser/parser.py` - New extraction methods
- Database: `tournament_visualizer/data/database.py` - New table creation methods AND method rename
  - `bulk_insert_resources()` → `bulk_insert_yield_history()` (renamed for clarity)
  - Table reference updated: `resources` → `player_yield_history`
- ETL: `tournament_visualizer/data/etl.py` - Update calls to use new method name
- Tests: `tests/test_parser.py` - Tests for new extraction methods
