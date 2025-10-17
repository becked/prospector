# Migration 004: Add Tournament Participant Tracking

## Overview
Adds tournament participant tracking to link players across multiple matches using Challonge API data.

## Schema Changes

### New Table: `tournament_participants`

```sql
CREATE TABLE tournament_participants (
    participant_id BIGINT PRIMARY KEY,
    display_name VARCHAR NOT NULL,
    display_name_normalized VARCHAR NOT NULL,
    challonge_username VARCHAR,
    challonge_user_id BIGINT,
    seed INTEGER,
    final_rank INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX idx_participants_normalized ON tournament_participants(display_name_normalized);
```

### New Table: `participant_name_overrides`

```sql
CREATE TABLE participant_name_overrides (
    override_id INTEGER PRIMARY KEY,
    match_id BIGINT NOT NULL,
    save_file_player_name VARCHAR NOT NULL,
    participant_id BIGINT NOT NULL,
    reason VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (participant_id) REFERENCES tournament_participants(participant_id),
    UNIQUE(match_id, save_file_player_name)
);
```

### Alter Table: `matches`

```sql
ALTER TABLE matches ADD COLUMN player1_participant_id BIGINT;
ALTER TABLE matches ADD COLUMN player2_participant_id BIGINT;
ALTER TABLE matches ADD COLUMN winner_participant_id BIGINT;
```

Note: Foreign key constraints will be added after participants are populated.

### Alter Table: `players`

```sql
ALTER TABLE players ADD COLUMN participant_id BIGINT;

CREATE INDEX idx_players_participant ON players(participant_id);
```

Note: Foreign key constraint will be added after participants are populated.

## SQL Migration Script

```sql
-- Create tournament_participants table
CREATE TABLE IF NOT EXISTS tournament_participants (
    participant_id BIGINT PRIMARY KEY,
    display_name VARCHAR NOT NULL,
    display_name_normalized VARCHAR NOT NULL,
    challonge_username VARCHAR,
    challonge_user_id BIGINT,
    seed INTEGER,
    final_rank INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_participants_normalized
ON tournament_participants(display_name_normalized);

-- Create participant_name_overrides table
CREATE TABLE IF NOT EXISTS participant_name_overrides (
    override_id INTEGER PRIMARY KEY,
    match_id BIGINT NOT NULL,
    save_file_player_name VARCHAR NOT NULL,
    participant_id BIGINT NOT NULL,
    reason VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (participant_id) REFERENCES tournament_participants(participant_id),
    UNIQUE(match_id, save_file_player_name)
);

-- Add participant tracking to matches table
ALTER TABLE matches ADD COLUMN IF NOT EXISTS player1_participant_id BIGINT;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS player2_participant_id BIGINT;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS winner_participant_id BIGINT;

-- Add participant tracking to players table
ALTER TABLE players ADD COLUMN IF NOT EXISTS participant_id BIGINT;

CREATE INDEX IF NOT EXISTS idx_players_participant ON players(participant_id);

-- Record migration
INSERT INTO schema_migrations (version, description, applied_at)
VALUES ('4', 'Add tournament participant tracking', CURRENT_TIMESTAMP);
```

## Rollback Procedure

```sql
-- Drop indexes
DROP INDEX IF EXISTS idx_players_participant;
DROP INDEX IF EXISTS idx_participants_normalized;

-- Remove columns from players table
ALTER TABLE players DROP COLUMN IF EXISTS participant_id;

-- Remove columns from matches table
ALTER TABLE matches DROP COLUMN IF EXISTS winner_participant_id;
ALTER TABLE matches DROP COLUMN IF EXISTS player2_participant_id;
ALTER TABLE matches DROP COLUMN IF EXISTS player1_participant_id;

-- Drop tables
DROP TABLE IF EXISTS participant_name_overrides;
DROP TABLE IF EXISTS tournament_participants;

-- Remove migration record
DELETE FROM schema_migrations WHERE version = '4';
```

## Verification

After applying migration:

```sql
-- Verify tables exist
SELECT name FROM sqlite_master WHERE type='table'
AND name IN ('tournament_participants', 'participant_name_overrides');

-- Verify columns added
PRAGMA table_info(matches);
PRAGMA table_info(players);

-- Verify indexes
PRAGMA index_list(tournament_participants);
PRAGMA index_list(players);

-- Verify migration recorded
SELECT * FROM schema_migrations WHERE version = '4';
```

## Related Files
- Challonge sync: `scripts/sync_challonge_participants.py` (new)
- Name matching: `tournament_visualizer/data/name_normalizer.py` (new)
- Participant matching: `tournament_visualizer/data/participant_matcher.py` (new)
- Database operations: `tournament_visualizer/data/database.py`
- ETL: `tournament_visualizer/data/etl.py`

## Data Population Order

1. Apply schema migration
2. Import Challonge participants (new script)
3. Update matches with participant IDs (new script)
4. Link players to participants via name matching (new script)
5. Verify all linkages

## Notes

- participant_id is nullable in players table (backward compatible)
- Name matching is fuzzy - manual overrides may be needed
- All queries work without participant data (optional enhancement)
