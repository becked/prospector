# Database Schema Changes Impact Analysis

**Issue ID**: `DB-001`
**Severity**: `HIGH`
**Created**: 2025-10-06
**Status**: `OPEN`

## Overview

Recent changes to fix DuckDB compatibility issues have introduced breaking changes to the database schema that significantly impact the tournament visualization application functionality.

## Summary of Schema Changes

### 1. Primary Key Type Changes
- **Changed**: All primary keys from `INTEGER PRIMARY KEY` to `BIGINT PRIMARY KEY`
- **Reason**: DuckDB auto-increment compatibility
- **Files**: `tournament_visualizer/data/database.py`

### 2. Foreign Key Type Updates
- **Changed**: All foreign key references updated from `INTEGER` to `BIGINT`
- **Reason**: Type consistency with new primary keys
- **Files**: `tournament_visualizer/data/database.py`

### 3. Winner Player ID Handling Removed
- **Changed**: ETL no longer sets `winner_player_id` in matches table
- **Reason**: DuckDB foreign key constraint restrictions
- **Files**: `tournament_visualizer/data/etl.py` (lines 110-135)

### 4. Game State Unique Constraint Removed
- **Changed**: Removed `CONSTRAINT unique_match_turn UNIQUE(match_id, turn_number)`
- **Reason**: Data contains legitimate duplicate turn numbers
- **Files**: `tournament_visualizer/data/database.py` (line 190)

### 5. Sequence-Based ID Generation
- **Added**: Custom sequences for auto-increment behavior
- **Reason**: DuckDB doesn't support `SERIAL` or auto-increment like SQLite
- **Files**: `tournament_visualizer/data/database.py`, `tournament_visualizer/data/etl.py`

## Critical Impact Analysis

### 🔴 HIGH SEVERITY ISSUES

#### 1. Winner Information Completely Broken
**Impact**: All winner-related functionality is non-functional
**Root Cause**: `winner_player_id` is always `NULL` in matches table

**Affected Components**:
- `queries.py`: Lines 66, 94, 159, 163, 167, 276, 292, 314, 385
- Database views: `player_performance`, `match_summary`
- Dashboard pages: Overview, Players, Matches
- Statistics: Win rates, player rankings, victory analysis

**Affected Queries**:
```sql
-- These all return NULL/0 for winner data
COUNT(CASE WHEN m.winner_player_id = p.player_id THEN 1 END) as wins
w.player_name as winner_name
w.civilization as winner_civilization
```

#### 2. Database Views Broken
**Impact**: Pre-computed views return incorrect data
**Root Cause**: Views depend on `winner_player_id` which is always NULL

**Affected Views**:
- `player_performance`: Win rates always 0%
- `match_summary`: Winner names always NULL

### 🟡 MEDIUM SEVERITY ISSUES

#### 3. Data Type Assumptions
**Impact**: Potential issues with ID size assumptions
**Risk**: Application code assuming 32-bit integers

**Potential Issues**:
- JavaScript number precision limits
- API serialization issues
- Memory usage increases
- Index performance changes

#### 4. Data Integrity Concerns
**Impact**: Duplicate game states allowed
**Risk**: Analytical queries may return incorrect aggregations

**Affected Areas**:
- Turn progression analysis
- Resource tracking over time
- Event timeline accuracy

### 🟢 LOW SEVERITY ISSUES

#### 5. Sequence Management
**Impact**: New ID generation pattern
**Risk**: Maintenance complexity, potential gaps in sequences

## Immediate Actions Required

### 1. Fix Winner Player ID Logic
**Priority**: CRITICAL
**Effort**: High

**Required Changes**:
1. Create new `match_winners` table
2. Restructure ETL flow to avoid FK constraint violations
3. Update all queries to JOIN with `match_winners` table
4. Update database views to use new winner table
5. Re-import existing data with correct winner information

### 2. Update Database Views
**Priority**: HIGH
**Effort**: Low

Update views to handle NULL winner_player_id gracefully or remove winner-dependent columns.

### 3. Validate Data Type Compatibility
**Priority**: MEDIUM
**Effort**: Low

Test all ID operations for BIGINT compatibility across the application stack.

### 4. Review Query Performance
**Priority**: MEDIUM
**Effort**: Medium

Benchmark queries with BIGINT keys vs INTEGER keys for performance impact.

## Proposed Solutions

### Solution 1: Restructure ETL Flow (Recommended)
**Issue**: Parser determines winner, but ETL can't set it due to DuckDB FK constraints.
**Root Cause**: DuckDB doesn't allow UPDATE on tables referenced by foreign keys.

**Approach**: Restructure the ETL flow to avoid UPDATE operations:

```python
def _load_tournament_data(self, parsed_data: Dict[str, Any]) -> None:
    """Load tournament data - restructured to handle winner properly."""

    # Step 1: Insert match WITHOUT winner (to get match_id)
    match_metadata = parsed_data['match_metadata'].copy()
    original_winner_id = match_metadata.pop('winner_player_id', None)
    match_id = self.db.insert_match(match_metadata)

    # Step 2: Insert players and build ID mapping
    players_data = parsed_data['players']
    player_id_mapping = {}
    for i, player_data in enumerate(players_data):
        player_data['match_id'] = match_id
        player_id = self.db.insert_player(player_data)
        player_id_mapping[i + 1] = player_id

    # Step 3: Use a separate winner tracking table (no FK constraints)
    if original_winner_id and original_winner_id in player_id_mapping:
        winner_db_id = player_id_mapping[original_winner_id]
        self.db.execute_query("""
            INSERT INTO match_winners (match_id, winner_player_id)
            VALUES (?, ?)
        """, [match_id, winner_db_id])
```

**Requires**: New `match_winners` table (see Solution 2)

### Solution 2: Winner Summary Table
```sql
CREATE TABLE match_winners (
    match_id BIGINT PRIMARY KEY REFERENCES matches(match_id),
    winner_player_id BIGINT REFERENCES players(player_id),
    winner_determination_method VARCHAR(50),
    determined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Solution 3: ETL Restructure
Modify ETL to:
1. Parse all match data first
2. Determine winner from game data
3. Insert match with winner_player_id populated from start

## Testing Requirements

1. **Unit Tests**: All queries involving winner_player_id
2. **Integration Tests**: Dashboard functionality with winner display
3. **Performance Tests**: BIGINT vs INTEGER key performance
4. **Data Validation**: Ensure no duplicate game states cause issues

## Timeline

- **Immediate (Day 1)**: Document broken functionality
- **Short-term (Week 1)**: Implement winner determination logic
- **Medium-term (Week 2)**: Update all affected queries and views
- **Long-term (Month 1)**: Performance validation and optimization

## Files Requiring Updates

### High Priority
- `tournament_visualizer/data/queries.py` - Update all winner-dependent queries
- `tournament_visualizer/data/database.py` - Update database views
- `tournament_visualizer/data/etl.py` - Add winner determination logic

### Medium Priority
- `tournament_visualizer/pages/overview.py` - Handle NULL winner data
- `tournament_visualizer/pages/players.py` - Update player performance metrics
- `tournament_visualizer/pages/matches.py` - Update match displays
- `tournament_visualizer/components/charts.py` - Handle missing winner data

### Testing
- Add comprehensive tests for winner determination logic
- Add tests for BIGINT key compatibility
- Add data integrity tests for duplicate game states

## Risk Mitigation

1. **Backward Compatibility**: Maintain old query signatures where possible
2. **Graceful Degradation**: Display "Unknown" instead of crashing on NULL winners
3. **Data Validation**: Add checks for data consistency issues
4. **Performance Monitoring**: Track query performance after BIGINT migration

## Current Status

As of 2025-10-06, the database schema changes have been successfully applied and tournament import is working (15/15 files imported successfully). However, **all winner-related functionality is completely broken** because the ETL now sets `winner_player_id` to NULL for all matches.

### Immediate Impact
- ✅ Tournament data import: **WORKING**
- ❌ Player win rates: **BROKEN** (all showing 0%)
- ❌ Match winners: **BROKEN** (all showing NULL)
- ❌ Victory analysis: **BROKEN** (no winner data)
- ❌ Player rankings: **BROKEN** (based on wins)

### Next Steps
1. **DO NOT** attempt to fix by reverting schema changes - this will break import functionality
2. Implement Solution 1 (match_winners table) + restructured ETL
3. Re-import all tournament data to populate winner information
4. Update application queries to use new winner table

## Notes

This issue affects core functionality of the tournament visualization application. The winner information is central to player rankings, match analysis, and performance metrics. Immediate action is required to restore full functionality.

Consider this a breaking change that requires coordinated updates across multiple components of the application.

**Priority**: This should be the #1 development priority as the application's core value proposition (tournament analysis) is severely compromised without winner information.