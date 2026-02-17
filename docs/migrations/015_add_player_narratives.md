# Migration 015: Add Per-Player Narrative Columns

## Overview

Adds per-player LLM-generated narrative columns to the matches table. The existing `narrative_summary` column stores the overall match narrative; the new columns store player-specific empire narratives.

**Date:** 2026-02-16
**Schema Version:** 6

---

## Changes

### Updated Table: matches

```sql
ALTER TABLE matches ADD COLUMN p1_narrative TEXT;
ALTER TABLE matches ADD COLUMN p2_narrative TEXT;
```

---

## Migration Procedure

Migration is applied automatically when `TournamentDatabase` is initialized with `read_only=False` (e.g., during import or narrative generation).

### Manual Application

```bash
uv run duckdb data/tournament_data.duckdb -c "ALTER TABLE matches ADD COLUMN p1_narrative TEXT"
uv run duckdb data/tournament_data.duckdb -c "ALTER TABLE matches ADD COLUMN p2_narrative TEXT"
```

### Verify

```bash
uv run duckdb data/tournament_data.duckdb -readonly -c "DESCRIBE matches" | grep narrative
```

Should show:
```
narrative_summary  VARCHAR  YES  NULL  NULL  NULL
p1_narrative       VARCHAR  YES  NULL  NULL  NULL
p2_narrative       VARCHAR  YES  NULL  NULL  NULL
```

---

## Rollback Procedure

```bash
uv run duckdb data/tournament_data.duckdb -c "ALTER TABLE matches DROP COLUMN p1_narrative"
uv run duckdb data/tournament_data.duckdb -c "ALTER TABLE matches DROP COLUMN p2_narrative"
uv run duckdb data/tournament_data.duckdb -c "DELETE FROM schema_migrations WHERE version = '6'"
```

---

## Related Files

- `tournament_visualizer/data/database.py` - Schema definition and migration
- `tournament_visualizer/data/narrative_generator.py` - Narrative generation logic
- `scripts/generate_match_narratives.py` - Script to populate narratives
