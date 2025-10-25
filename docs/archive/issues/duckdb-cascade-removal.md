# DuckDB CASCADE Foreign Key Constraint Removal

## Issue Summary
DuckDB does not support CASCADE operations (`ON DELETE CASCADE`, `ON UPDATE CASCADE`) in foreign key constraints. The original database schema included these constraints which caused schema creation to fail.

## Problem
```
Parser Error: FOREIGN KEY constraints cannot use CASCADE, SET NULL or SET DEFAULT
```

## Solution Applied
Removed all CASCADE operations from foreign key constraints in the following tables:
- `players` table: `REFERENCES matches(match_id) ON DELETE CASCADE` → `REFERENCES matches(match_id)`
- `game_state` table: `REFERENCES matches(match_id) ON DELETE CASCADE` → `REFERENCES matches(match_id)`
- `territories` table: `REFERENCES matches(match_id) ON DELETE CASCADE` → `REFERENCES matches(match_id)`
- `events` table: `REFERENCES matches(match_id) ON DELETE CASCADE` → `REFERENCES matches(match_id)`
- `resources` table: Both `REFERENCES matches(match_id) ON DELETE CASCADE` and `REFERENCES players(player_id) ON DELETE CASCADE` → removed CASCADE

## Impact on Application

### Positive Effects
- **Data Safety**: Prevents accidental data loss from cascading deletes
- **Explicit Control**: Forces intentional deletion patterns
- **DuckDB Compatibility**: Resolves schema creation errors

### Considerations
- **Manual Cleanup Required**: When deleting parent records, child records must be deleted manually first
- **Application Code Changes**: Deletion logic needs to handle proper cleanup order:
  ```python
  # Required deletion order for matches:
  1. Delete resources for all players in match
  2. Delete events for match
  3. Delete territories for match
  4. Delete players for match
  5. Delete match
  ```

### Recommended Deletion Order
```python
def delete_match_completely(match_id):
    # Delete in reverse dependency order
    delete_resources_for_match(match_id)
    delete_events_for_match(match_id) 
    delete_territories_for_match(match_id)
    delete_players_for_match(match_id)
    delete_match(match_id)
```

## Future Considerations
- Consider implementing application-level cascade deletion functions
- Add transaction wrapping for multi-table deletions to ensure consistency
- Document deletion patterns for future developers

## Files Modified
- `tournament_visualizer/data/database.py`: Removed CASCADE from all foreign key constraints

## Status
🔄 **SUPERSEDED** - This approach was replaced by a better architectural solution

## Summary of Resolution

This issue described removing CASCADE operations from foreign key constraints and implementing manual deletion patterns. However, during the implementation of the database schema changes (see `database-schema-changes-impact-summary.md`), a different and better solution was adopted:

### Actual Solution Implemented
Instead of working around DuckDB's CASCADE limitations, the problem was solved by **restructuring the data model**:

- Created a separate `match_winners` table to handle winner information
- This eliminated the foreign key constraint conflicts that originally caused the CASCADE issues
- No manual deletion order is required with the current architecture

### Why This Approach Was Superseded
1. **Cleaner Architecture**: The `match_winners` table approach provides better separation of concerns
2. **No Manual Cleanup**: Eliminates the need for complex deletion patterns described in this document
3. **Better DuckDB Compatibility**: Works within DuckDB's constraints without workarounds

### Current State
- The deletion order code examples in this document are **no longer needed**
- The schema now uses a structure that naturally works with DuckDB's foreign key limitations
- See `database-schema-changes-impact-summary.md` for the complete details of the implemented solution

**Reference**: See [Database Schema Changes Impact Summary](database-schema-changes-impact-summary.md) for the actual resolution approach.