# Participant Linking for Cross-Match Queries - Implementation Plan

## Context

This tournament visualizer tracks Old World game matches from a Challonge tournament. Players participate in multiple matches over time, but their in-game names can vary between matches. We've built a participant linking system that connects match-scoped `players` records to tournament-scoped `tournament_participants` records.

**Problem:** Several queries that aggregate data across multiple matches are still using match-scoped player names instead of tournament participants. This causes the same person to be counted multiple times if their in-game name varies.

**Solution:** Update these queries to use participant linking, following the established pattern from `get_player_performance()` and `get_civilization_performance()`.

---

## Database Schema Overview

### Key Tables

```sql
-- Match-scoped player instances (one per match)
CREATE TABLE players (
    player_id INTEGER PRIMARY KEY,
    match_id INTEGER NOT NULL,
    player_name TEXT NOT NULL,              -- Name from save file (can vary)
    player_name_normalized TEXT NOT NULL,   -- Lowercase, no special chars
    civilization TEXT,
    final_score INTEGER,
    participant_id INTEGER,                 -- FK to tournament_participants (nullable)
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (participant_id) REFERENCES tournament_participants(participant_id)
);

-- Tournament-wide participant records (one per person)
CREATE TABLE tournament_participants (
    participant_id INTEGER PRIMARY KEY,     -- From Challonge API
    display_name TEXT NOT NULL,             -- Canonical name from Challonge
    challonge_username TEXT,
    seed INTEGER
);

-- Law adoption events
CREATE TABLE events (
    event_id INTEGER PRIMARY KEY,
    match_id INTEGER NOT NULL,
    player_id INTEGER,                      -- FK to players.player_id
    turn_number INTEGER NOT NULL,
    event_type TEXT NOT NULL,               -- e.g., 'LAW_ADOPTED', 'TECH_DISCOVERED'
    description TEXT,
    event_data TEXT,                        -- JSON with details
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (player_id) REFERENCES players.player_id
);
```

### Participant Linking Strategy

**Established Pattern (from `get_player_performance`):**

1. **Create a grouping key:** Use `participant_id` if available, else fall back to `'unlinked_' || player_name_normalized`
2. **Join to participants:** `LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id`
3. **Prefer participant names:** `COALESCE(tp.display_name, p.player_name)`
4. **Track linkage status:** Add `is_unlinked` boolean flag
5. **Group by the key:** Aggregate across matches using the grouping key

---

## Queries That Need Updates

### 1. `get_law_progression_by_match()` - Line 1126
- **File:** `tournament_visualizer/data/queries.py`
- **Current behavior:** Returns law milestone timing with match-scoped `player_name`
- **Used by:**
  - `tournament_visualizer/pages/overview.py:535` - Law Timing Distribution chart
  - `tournament_visualizer/pages/overview.py:564` - Law Progression Efficiency chart
- **Impact:** When called with `match_id=None` (all matches), shows duplicate entries for same person

### 2. `get_cumulative_law_count_by_turn()` - Line 1286
- **File:** `tournament_visualizer/data/queries.py`
- **Current behavior:** Returns cumulative law counts with match-scoped `player_name`
- **Used by:**
  - `tournament_visualizer/pages/matches.py:1084` - Match detail law progression chart
  - `tournament_visualizer/pages/matches.py:1246` - Law timeline racing chart
- **Impact:** Shows save file names instead of participant names on match detail page

### 3. `get_map_performance_analysis()` - Line 378
- **File:** `tournament_visualizer/data/queries.py`
- **Current behavior:** Uses `COUNT(DISTINCT p.player_name)` for unique players
- **Used by:**
  - `tournament_visualizer/pages/maps.py` (exact usage TBD - need to check file)
- **Impact:** Inflates unique player count when same person plays on multiple map types

### 4. `get_player_law_progression_stats()` - Line 967
- **File:** `tournament_visualizer/data/queries.py`
- **Current behavior:** Groups by `player_name_normalized` without participant join
- **Used by:** Need to search codebase to confirm usage
- **Impact:** Relies solely on name normalization, which can fail for name variations

---

## Implementation Tasks

### Task 1: Update `get_law_progression_by_match()` (30 min)

**Goal:** Add participant linking so law milestone timing aggregates by person, not player name.

**Context:** This query is called with `match_id=None` to show ALL matches on the overview page. When aggregating across matches, we need to track people, not player instances.

**Design Decision:** Since this returns per-match-instance data but is aggregated in charts, we need to add participant info but keep the row-per-match structure.

**Files to modify:**
- `tournament_visualizer/data/queries.py` (lines 1126-1181)

**Implementation:**

```python
def get_law_progression_by_match(
    self, match_id: Optional[int] = None
) -> pd.DataFrame:
    """Get law progression for players, showing when they reached 4 and 7 laws.

    Groups by tournament participant when available. When called without match_id,
    aggregates across all matches to show how people (not player instances)
    progress through laws.

    Args:
        match_id: Optional match_id to filter (None for all matches)

    Returns:
        DataFrame with columns:
            - match_id: Match ID
            - player_id: Database player ID (match-scoped)
            - player_name: Display name (participant name if linked, else player name)
            - participant_id: Participant ID (NULL if unlinked)
            - is_unlinked: Boolean, TRUE if not linked to participant
            - civilization: Civilization played
            - turn_to_4_laws: Turn number when 4th law adopted (NULL if <4 laws)
            - turn_to_7_laws: Turn number when 7th law adopted (NULL if <7 laws)
            - total_laws: Total laws adopted in this match
    """
    match_filter = "AND e.match_id = ?" if match_id else ""

    query = f"""
    WITH law_events AS (
        SELECT
            e.match_id,
            e.player_id,
            e.turn_number,
            ROW_NUMBER() OVER (
                PARTITION BY e.match_id, e.player_id
                ORDER BY e.turn_number
            ) as law_number
        FROM events e
        WHERE e.event_type = 'LAW_ADOPTED'
            AND e.player_id IS NOT NULL
            {match_filter}
    ),
    milestones AS (
        SELECT
            match_id,
            player_id,
            MAX(CASE WHEN law_number = 4 THEN turn_number END) as turn_to_4_laws,
            MAX(CASE WHEN law_number = 7 THEN turn_number END) as turn_to_7_laws,
            MAX(law_number) as total_laws
        FROM law_events
        GROUP BY match_id, player_id
    )
    SELECT
        m.match_id,
        m.player_id,
        -- Prefer participant name over player name
        COALESCE(tp.display_name, p.player_name) as player_name,
        p.participant_id,
        CASE WHEN p.participant_id IS NULL THEN TRUE ELSE FALSE END as is_unlinked,
        p.civilization,
        m.turn_to_4_laws,
        m.turn_to_7_laws,
        m.total_laws
    FROM milestones m
    JOIN players p ON m.match_id = p.match_id AND m.player_id = p.player_id
    LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
    ORDER BY m.match_id, m.player_id
    """

    params = [match_id] if match_id else []

    with self.db.get_connection() as conn:
        return conn.execute(query, params).df()
```

**Testing approach:**
1. **Unit test:** Verify participant name used when available
2. **Integration test:** Call with `match_id=None`, verify same person appears with one name
3. **UI test:** Check overview page charts show participant names

**Files to check/test:**
- `tournament_visualizer/pages/overview.py:535, 564` - Verify charts work
- `tournament_visualizer/components/charts.py` - Check chart functions handle new columns

**Validation:**
```bash
# After changes, run this to verify
uv run python -c "
from tournament_visualizer.data.queries import get_queries
q = get_queries()
df = q.get_law_progression_by_match(match_id=None)
print('Columns:', df.columns.tolist())
print('Sample rows:')
print(df.head())
print('Unlinked count:', df['is_unlinked'].sum())
print('Linked count:', (~df['is_unlinked']).sum())
"
```

**Commit message:**
```
feat: Add participant linking to get_law_progression_by_match()

- Join to tournament_participants table
- Prefer participant display name over player name
- Add participant_id and is_unlinked columns
- Ensures law progression charts show consistent names across matches

Addresses participant tracking consistency issue.
```

---

### Task 2: Update `get_cumulative_law_count_by_turn()` (25 min)

**Goal:** Use participant names in match-specific law progression chart.

**Context:** This query is match-specific (requires `match_id`), so it doesn't aggregate across matches. However, it should still show participant names for consistency.

**Design Decision:** Simpler than Task 1 - just swap player names for participant names in the output.

**Files to modify:**
- `tournament_visualizer/data/queries.py` (lines 1286-1354)

**Implementation:**

```python
def get_cumulative_law_count_by_turn(self, match_id: int) -> pd.DataFrame:
    """Get cumulative law count by turn for each player.

    Similar to get_tech_count_by_turn, but for laws. Shows participant names
    when available for consistency with other UI elements.

    Args:
        match_id: Match ID to analyze

    Returns:
        DataFrame with columns:
            - player_id: Database player ID
            - player_name: Display name (participant if linked, else player name)
            - participant_id: Participant ID (NULL if unlinked)
            - turn_number: Turn when law was adopted
            - cumulative_laws: Total laws up to this turn
            - law_list: Comma-separated list of all laws adopted
            - new_laws: Comma-separated list of laws adopted this turn
    """
    query = """
    WITH law_events AS (
        SELECT
            e.player_id,
            -- Prefer participant name from join
            COALESCE(tp.display_name, p.player_name) as player_name,
            p.participant_id,
            e.turn_number,
            e.event_id,
            json_extract(e.event_data, '$.law') as law_name,
            ROW_NUMBER() OVER (
                PARTITION BY e.player_id
                ORDER BY e.turn_number, e.event_id
            ) as cumulative_laws
        FROM events e
        JOIN players p ON e.match_id = p.match_id AND e.player_id = p.player_id
        LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
        WHERE e.event_type = 'LAW_ADOPTED'
            AND e.match_id = ?
    ),
    laws_up_to_turn AS (
        SELECT
            le1.player_id,
            le1.player_name,
            le1.participant_id,
            le1.turn_number,
            le1.cumulative_laws,
            le1.event_id,
            string_agg(le2.law_name, ', ') FILTER (WHERE le2.law_name IS NOT NULL) as law_list
        FROM law_events le1
        LEFT JOIN law_events le2 ON le1.player_id = le2.player_id
            AND le2.event_id <= le1.event_id
        GROUP BY le1.player_id, le1.player_name, le1.participant_id, le1.turn_number, le1.cumulative_laws, le1.event_id
    ),
    new_laws_this_turn AS (
        SELECT
            le1.player_id,
            le1.turn_number,
            le1.event_id,
            string_agg(le2.law_name, ', ') FILTER (WHERE le2.law_name IS NOT NULL) as new_laws
        FROM law_events le1
        LEFT JOIN law_events le2 ON le1.player_id = le2.player_id
            AND le2.turn_number = le1.turn_number
            AND le2.event_id <= le1.event_id
        GROUP BY le1.player_id, le1.turn_number, le1.event_id
    )
    SELECT DISTINCT
        lut.player_id,
        lut.player_name,
        lut.participant_id,
        lut.turn_number,
        lut.cumulative_laws,
        lut.law_list,
        nlt.new_laws
    FROM laws_up_to_turn lut
    LEFT JOIN new_laws_this_turn nlt ON lut.player_id = nlt.player_id
        AND lut.turn_number = nlt.turn_number
        AND lut.event_id = nlt.event_id
    ORDER BY lut.player_id, lut.turn_number, lut.cumulative_laws
    """

    with self.db.get_connection() as conn:
        return conn.execute(query, [match_id]).df()
```

**Testing approach:**
1. **Unit test:** Pick a known match, verify participant names appear
2. **UI test:** Load match detail page, verify chart shows participant names

**Files to check/test:**
- `tournament_visualizer/pages/matches.py:1084, 1246` - Verify charts work
- Check if charts need updates to handle new column

**Validation:**
```bash
# Use a known match_id from your database
uv run python -c "
from tournament_visualizer.data.queries import get_queries
q = get_queries()
df = q.get_cumulative_law_count_by_turn(match_id=1)  # Replace with real ID
print('Columns:', df.columns.tolist())
print('Sample:')
print(df[['player_name', 'participant_id', 'turn_number', 'cumulative_laws']].head(10))
"
```

**Commit message:**
```
feat: Add participant names to get_cumulative_law_count_by_turn()

- Join to tournament_participants table
- Use participant display name instead of save file name
- Add participant_id column for reference
- Improves consistency in match detail page

Part of participant tracking improvements.
```

---

### Task 3: Update `get_map_performance_analysis()` (30 min)

**Goal:** Count unique participants (people) instead of unique player names.

**Context:** This query aggregates map performance stats across ALL matches. The `unique_players` column should count how many different PEOPLE played on each map type, not how many different player name strings exist.

**Design Decision:** Use the person_key pattern from `get_civilization_performance()`.

**Files to modify:**
- `tournament_visualizer/data/queries.py` (lines 378-401)

**Implementation:**

```python
def get_map_performance_analysis(self) -> pd.DataFrame:
    """Get performance analysis by map characteristics.

    Counts unique participants (people) rather than player name strings
    to accurately reflect how many different people have played on each
    map configuration.

    Returns:
        DataFrame with map performance data including aspect ratio and participant counts:
            - map_size: Map size (e.g., 'SMALL', 'MEDIUM', 'LARGE')
            - map_class: Map class (e.g., 'INLAND', 'LAKES')
            - map_aspect_ratio: Aspect ratio (e.g., 'STANDARD', 'WIDE')
            - total_matches: Number of matches with this configuration
            - avg_turns: Average match length in turns
            - min_turns: Shortest match
            - max_turns: Longest match
            - unique_participants: Count of unique people (linked + unlinked proxy)
            - unique_linked_participants: Count of properly linked only
            - unique_unlinked_players: Count of unlinked only (data quality metric)
    """
    query = """
    WITH player_identity AS (
        SELECT
            m.match_id,
            p.player_id,
            m.map_size,
            m.map_class,
            m.map_aspect_ratio,
            m.total_turns,
            -- Create person key: participant_id if available, else normalized name
            COALESCE(
                CAST(p.participant_id AS VARCHAR),
                'unlinked_' || p.player_name_normalized
            ) as person_key,
            CASE WHEN p.participant_id IS NOT NULL THEN TRUE ELSE FALSE END as is_linked
        FROM matches m
        LEFT JOIN players p ON m.match_id = p.match_id
    )
    SELECT
        COALESCE(pi.map_size, 'Unknown') as map_size,
        COALESCE(pi.map_class, 'Unknown') as map_class,
        COALESCE(pi.map_aspect_ratio, 'Unknown') as map_aspect_ratio,
        COUNT(DISTINCT pi.match_id) as total_matches,
        AVG(pi.total_turns) as avg_turns,
        MIN(pi.total_turns) as min_turns,
        MAX(pi.total_turns) as max_turns,
        -- Count unique people (participants + unlinked player proxies)
        COUNT(DISTINCT pi.person_key) as unique_participants,
        -- Count only linked participants for data quality insight
        COUNT(DISTINCT CASE WHEN pi.is_linked THEN pi.person_key END) as unique_linked_participants,
        -- Count unlinked for data quality insight
        COUNT(DISTINCT CASE WHEN NOT pi.is_linked THEN pi.person_key END) as unique_unlinked_players
    FROM player_identity pi
    GROUP BY
        COALESCE(pi.map_size, 'Unknown'),
        COALESCE(pi.map_class, 'Unknown'),
        COALESCE(pi.map_aspect_ratio, 'Unknown')
    ORDER BY total_matches DESC
    """

    with self.db.get_connection() as conn:
        return conn.execute(query).df()
```

**Testing approach:**
1. **Manual verification:** Count known participants who played on multiple maps
2. **Data quality check:** Verify `unique_linked_participants + unique_unlinked_players = unique_participants`
3. **Before/after comparison:** Run old query and new query, verify participant count is lower (more accurate)

**Files to check:**
- `tournament_visualizer/pages/maps.py` - Find where this is used and update if needed
- May need to update charts/UI to show the new columns

**Validation:**
```bash
uv run python -c "
from tournament_visualizer.data.queries import get_queries
q = get_queries()
df = q.get_map_performance_analysis()
print('Columns:', df.columns.tolist())
print('Sample:')
print(df[['map_size', 'map_class', 'total_matches', 'unique_participants', 'unique_linked_participants', 'unique_unlinked_players']].head())
# Verify the sum matches
print('\nData quality check:')
print('linked + unlinked == total:',
      (df['unique_linked_participants'] + df['unique_unlinked_players'] == df['unique_participants']).all())
"
```

**Commit message:**
```
feat: Count unique participants in get_map_performance_analysis()

- Use participant_id when available, normalized name as fallback
- Add unique_participants, unique_linked_participants, unique_unlinked_players columns
- Replaces old unique_players count that inflated numbers
- Provides data quality metrics via linked/unlinked breakdown

Fixes inaccurate player count on map performance page.
```

---

### Task 4: Update `get_player_law_progression_stats()` (35 min)

**Goal:** Use participant linking instead of relying solely on name normalization.

**Context:** This query aggregates law progression statistics PER PERSON across all their matches. Currently groups by `player_name_normalized`, which can fail if the same person has name variations that normalize differently.

**Design Decision:** Follow the full participant grouping pattern from `get_player_performance()`.

**Files to modify:**
- `tournament_visualizer/data/queries.py` (lines 967-1012)

**Implementation:**

```python
def get_player_law_progression_stats(self) -> pd.DataFrame:
    """Get aggregate law progression statistics per player.

    Groups by tournament participant when available, ensuring consistent
    aggregation across matches even if in-game names vary.

    Returns:
        DataFrame with average law counts and milestone estimates per person:
            - player_name: Display name (participant name if linked, else player name)
            - participant_id: Participant ID (NULL if unlinked)
            - is_unlinked: Boolean, TRUE if not linked to participant
            - matches_played: Number of matches played
            - avg_laws_per_game: Average laws adopted per match
            - max_laws: Most laws in any single match
            - min_laws: Fewest laws in any single match
            - avg_turns_per_law: Average turns between law adoptions
            - avg_turn_to_4_laws: Average turn when 4th law reached
            - avg_turn_to_7_laws: Average turn when 7th law reached
    """
    query = """
    WITH player_grouping AS (
        -- Create smart grouping key: participant_id if linked, else normalized name
        SELECT
            ps.match_id,
            p.player_id,
            p.player_name,
            tp.participant_id,
            tp.display_name as participant_display_name,
            m.total_turns,
            SUM(ps.value) as total_laws,
            -- Grouping key: use participant_id if available, else normalized name
            COALESCE(
                CAST(tp.participant_id AS VARCHAR),
                'unlinked_' || p.player_name_normalized
            ) as grouping_key,
            -- Display name: prefer participant, fallback to player
            COALESCE(tp.display_name, p.player_name) as display_name,
            -- Flag for unlinked players
            CASE WHEN tp.participant_id IS NULL THEN TRUE ELSE FALSE END as is_unlinked
        FROM player_statistics ps
        JOIN players p ON ps.player_id = p.player_id
        LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
        JOIN matches m ON ps.match_id = m.match_id
        WHERE ps.stat_category = 'law_changes'
        GROUP BY ps.match_id, p.player_id, p.player_name, p.player_name_normalized,
                 tp.participant_id, tp.display_name, m.total_turns
        HAVING SUM(ps.value) > 0
    )
    SELECT
        MAX(display_name) as player_name,
        MAX(participant_id) as participant_id,
        MAX(is_unlinked) as is_unlinked,
        COUNT(DISTINCT match_id) as matches_played,
        AVG(total_laws) as avg_laws_per_game,
        MAX(total_laws) as max_laws,
        MIN(total_laws) as min_laws,
        AVG(CAST(total_turns AS FLOAT) / total_laws) as avg_turns_per_law,
        AVG(CASE
            WHEN total_laws >= 4
                THEN CAST((4.0 * total_turns / total_laws) AS INTEGER)
            ELSE NULL
        END) as avg_turn_to_4_laws,
        AVG(CASE
            WHEN total_laws >= 7
                THEN CAST((7.0 * total_turns / total_laws) AS INTEGER)
            ELSE NULL
        END) as avg_turn_to_7_laws
    FROM player_grouping
    GROUP BY grouping_key
    HAVING COUNT(DISTINCT match_id) > 0
    ORDER BY avg_laws_per_game DESC
    """

    with self.db.get_connection() as conn:
        return conn.execute(query).df()
```

**Testing approach:**
1. **Find usage:** Search codebase to see where this is called
2. **Before/after comparison:** Verify participants who played multiple matches are now one row
3. **Manual check:** Pick known participant, verify their stats aggregate correctly

**Files to check:**
- Search for usage: `grep -r "get_player_law_progression_stats" tournament_visualizer/`
- Update any pages/components that call this

**Validation:**
```bash
uv run python -c "
from tournament_visualizer.data.queries import get_queries
q = get_queries()
df = q.get_player_law_progression_stats()
print('Columns:', df.columns.tolist())
print('Total rows:', len(df))
print('Sample:')
print(df[['player_name', 'participant_id', 'is_unlinked', 'matches_played', 'avg_laws_per_game']].head(10))
print('\nData quality:')
print('Linked players:', (~df['is_unlinked']).sum())
print('Unlinked players:', df['is_unlinked'].sum())
"
```

**Commit message:**
```
feat: Add participant grouping to get_player_law_progression_stats()

- Use participant_id for grouping instead of just name normalization
- Join to tournament_participants table
- Add participant_id and is_unlinked columns
- Ensures accurate cross-match aggregation for law progression stats

Completes participant tracking for law-related queries.
```

---

### Task 5: Integration Testing & Documentation (45 min)

**Goal:** Verify all changes work together and update documentation.

**Sub-tasks:**

#### 5a. Run all existing tests (10 min)

```bash
# Run test suite
uv run pytest -v

# Run specific test files if they exist
uv run pytest tests/test_queries.py -v
uv run pytest tests/test_integration_logdata.py -v
```

**Expected result:** All tests pass. If any fail, fix them before proceeding.

#### 5b. Manual UI testing (15 min)

**Test checklist:**

1. **Overview Page - Law Charts**
   ```bash
   uv run python manage.py start
   # Open http://localhost:8050
   ```
   - Navigate to Overview page
   - Check "Law Timing Distribution" chart - verify participant names shown
   - Check "Law Progression Efficiency" scatter - verify participant names shown
   - Verify no duplicate entries for same person across matches
   - Check tooltip shows participant info correctly

2. **Match Detail Page - Law Progression**
   - Navigate to Matches page
   - Click on a specific match
   - Check law progression chart shows participant names (not save file names)
   - Verify chart legend matches participant names

3. **Maps Page** (if it exists)
   - Navigate to Maps page (if applicable)
   - Verify unique participants count is displayed
   - Check that number makes sense (should be lower than old player name count)

#### 5c. Data quality validation (10 min)

Create a validation script to check participant linking coverage:

**File:** `scripts/validate_participant_queries.py`

```python
"""Validate participant linking in cross-match queries."""

from tournament_visualizer.data.queries import get_queries


def main():
    queries = get_queries()

    print("=" * 60)
    print("Participant Linking Validation Report")
    print("=" * 60)

    # Test 1: Law progression by match
    print("\n1. Law Progression by Match (all matches)")
    df = queries.get_law_progression_by_match(match_id=None)
    total_rows = len(df)
    linked = (~df['is_unlinked']).sum()
    unlinked = df['is_unlinked'].sum()
    print(f"   Total match-player instances: {total_rows}")
    print(f"   Linked to participants: {linked} ({linked/total_rows*100:.1f}%)")
    print(f"   Unlinked: {unlinked} ({unlinked/total_rows*100:.1f}%)")

    # Test 2: Map performance analysis
    print("\n2. Map Performance Analysis")
    df = queries.get_map_performance_analysis()
    print(f"   Total map configurations: {len(df)}")
    print(f"   Total unique participants: {df['unique_participants'].sum()}")
    print(f"   Linked: {df['unique_linked_participants'].sum()}")
    print(f"   Unlinked: {df['unique_unlinked_players'].sum()}")

    # Verify sum property
    sum_check = (
        df['unique_linked_participants'] + df['unique_unlinked_players']
        == df['unique_participants']
    ).all()
    print(f"   Sum check (linked + unlinked = total): {'✓ PASS' if sum_check else '✗ FAIL'}")

    # Test 3: Player law progression stats
    print("\n3. Player Law Progression Stats")
    df = queries.get_player_law_progression_stats()
    total_players = len(df)
    linked = (~df['is_unlinked']).sum()
    unlinked = df['is_unlinked'].sum()
    print(f"   Total unique players: {total_players}")
    print(f"   Linked to participants: {linked} ({linked/total_players*100:.1f}%)")
    print(f"   Unlinked: {unlinked} ({unlinked/total_players*100:.1f}%)")

    print("\n" + "=" * 60)
    print("Validation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
```

**Run validation:**
```bash
uv run python scripts/validate_participant_queries.py
```

#### 5d. Update documentation (10 min)

**File:** `docs/developer-guide.md`

Find the "Participant Tracking" section and add:

```markdown
### Queries Using Participant Linking

The following queries properly use participant linking for cross-match aggregation:

**Player-centric:**
- `get_player_performance()` - Player stats across all matches
- `get_opponents()` - Find who a player has faced
- `get_head_to_head_stats()` - Head-to-head matchup stats

**Civilization-centric:**
- `get_civilization_performance()` - Counts unique participants per civ

**Law progression:**
- `get_law_progression_by_match()` - Law milestone timing (cross-match)
- `get_cumulative_law_count_by_turn()` - Turn-by-turn law adoption (match-specific)
- `get_player_law_progression_stats()` - Average law stats per person

**Map analysis:**
- `get_map_performance_analysis()` - Unique participants per map type

### Pattern for Adding Participant Linking

When creating new queries that aggregate across matches:

1. **Join to participants table:**
   ```sql
   LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
   ```

2. **Create grouping key:**
   ```sql
   COALESCE(
       CAST(tp.participant_id AS VARCHAR),
       'unlinked_' || p.player_name_normalized
   ) as grouping_key
   ```

3. **Prefer participant name:**
   ```sql
   COALESCE(tp.display_name, p.player_name) as player_name
   ```

4. **Add linkage flag:**
   ```sql
   CASE WHEN tp.participant_id IS NULL THEN TRUE ELSE FALSE END as is_unlinked
   ```

5. **Group by the key:**
   ```sql
   GROUP BY grouping_key
   ```

See `get_player_performance()` for the canonical implementation pattern.
```

**Commit message:**
```
docs: Document participant linking in queries

- Add list of queries using participant linking
- Document the standard pattern for adding participant links
- Reference canonical implementation in get_player_performance()

Part of participant tracking improvements.
```

---

## Testing Guidelines

### Unit Test Structure

For each updated query, add a test in `tests/test_queries.py`:

```python
def test_get_law_progression_by_match_uses_participants(tournament_db, sample_data):
    """Test that law progression query uses participant names."""
    queries = TournamentQueries(tournament_db)

    # Get all matches
    df = queries.get_law_progression_by_match(match_id=None)

    # Verify columns exist
    assert 'participant_id' in df.columns
    assert 'is_unlinked' in df.columns
    assert 'player_name' in df.columns

    # Verify at least some rows are linked (if test data has linked participants)
    if sample_data.has_linked_participants:
        assert (~df['is_unlinked']).any(), "Expected some linked participants"

        # Verify participant names are used
        linked_rows = df[~df['is_unlinked']]
        assert linked_rows['player_name'].notna().all()


def test_get_cumulative_law_count_by_turn_shows_participant_names(tournament_db, sample_match):
    """Test that cumulative law count uses participant names."""
    queries = TournamentQueries(tournament_db)

    df = queries.get_cumulative_law_count_by_turn(match_id=sample_match.match_id)

    # Verify participant_id column exists
    assert 'participant_id' in df.columns

    # If match has linked participants, verify names match
    if sample_match.has_linked_participants:
        participant_names = df[df['participant_id'].notna()]['player_name'].unique()
        assert len(participant_names) > 0, "Expected participant names in output"


def test_get_map_performance_counts_participants_not_names(tournament_db):
    """Test that map performance counts unique people, not name strings."""
    queries = TournamentQueries(tournament_db)

    df = queries.get_map_performance_analysis()

    # Verify new columns exist
    assert 'unique_participants' in df.columns
    assert 'unique_linked_participants' in df.columns
    assert 'unique_unlinked_players' in df.columns

    # Verify sum property: linked + unlinked = total
    sum_check = (
        df['unique_linked_participants'] + df['unique_unlinked_players']
        == df['unique_participants']
    ).all()
    assert sum_check, "linked + unlinked should equal total participants"
```

### Integration Test Checklist

- [ ] Overview page loads without errors
- [ ] Law Timing Distribution chart displays
- [ ] Law Progression Efficiency chart displays
- [ ] Match detail page loads without errors
- [ ] Match law progression chart displays
- [ ] Participant names shown instead of save file names
- [ ] No duplicate entries for same person across matches
- [ ] Unlinked players show warning indicator (⚠️) if UI has this feature

---

## Rollback Plan

If issues arise after deployment:

### Immediate Rollback
```bash
git revert HEAD~4..HEAD  # Revert last 4 commits
uv run python manage.py restart
```

### Identify Issues
- Check application logs: `uv run python manage.py logs`
- Look for SQL errors or KeyErrors in query results
- Verify charts are rendering

### Common Issues & Fixes

**Issue:** Charts show "No data available"
- **Cause:** Column name mismatch between query and chart
- **Fix:** Check chart code for old column names, update to match new schema

**Issue:** Duplicate entries still appearing
- **Cause:** Chart grouping by wrong column
- **Fix:** Update chart to group by `grouping_key` or `participant_id`

**Issue:** SQL errors about missing columns
- **Cause:** Old code referencing removed columns
- **Fix:** Search codebase for references to old column names, update them

---

## Deployment Checklist

### Local Development
- [ ] All 4 query updates committed separately
- [ ] Tests pass: `uv run pytest -v`
- [ ] Manual UI testing completed
- [ ] Validation script run successfully
- [ ] Documentation updated
- [ ] Code formatted: `uv run black tournament_visualizer/`
- [ ] Lint passed: `uv run ruff check tournament_visualizer/`

### Production (Fly.io)
- [ ] Backup current database:
  ```bash
  cp data/tournament_data.duckdb data/tournament_data.duckdb.backup_$(date +%Y%m%d_%H%M%S)
  ```
- [ ] Deploy code: `fly deploy`
- [ ] Sync data if needed: `./scripts/sync_tournament_data.sh`
- [ ] Verify application starts: `fly logs -a prospector`
- [ ] Smoke test production UI
- [ ] Monitor for errors for 15 minutes

---

## Timeline Estimate

| Task | Estimated Time | Cumulative |
|------|----------------|------------|
| Task 1: `get_law_progression_by_match()` | 30 min | 30 min |
| Task 2: `get_cumulative_law_count_by_turn()` | 25 min | 55 min |
| Task 3: `get_map_performance_analysis()` | 30 min | 85 min |
| Task 4: `get_player_law_progression_stats()` | 35 min | 120 min |
| Task 5: Testing & Documentation | 45 min | 165 min |
| **Total** | **~2.75 hours** | |

## Success Metrics

✅ **Objective measures:**
1. All 4 queries return `participant_id` and/or `is_unlinked` columns
2. Participant names shown in UI instead of save file names
3. No duplicate entries for same person in cross-match aggregations
4. All tests pass
5. Validation script shows >80% participant linking coverage

✅ **Subjective validation:**
1. Overview page law charts show consistent player names
2. Match detail page shows Challonge participant names
3. Map performance page shows accurate unique player counts
4. No visual regressions in existing charts

---

## References

**Key files:**
- `tournament_visualizer/data/queries.py` - All query implementations
- `tournament_visualizer/pages/overview.py` - Overview page (uses Tasks 1)
- `tournament_visualizer/pages/matches.py` - Match detail page (uses Task 2)
- `tournament_visualizer/pages/maps.py` - Maps page (uses Task 3, if exists)

**Database schema:**
- `players` table - Match-scoped player records
- `tournament_participants` table - Tournament-wide participant records
- `events` table - Law adoption and other events

**Existing participant queries (reference implementations):**
- `get_player_performance()` (lines 71-157) - Canonical participant grouping pattern
- `get_civilization_performance()` (lines 159-214) - Person key pattern for counts
- `get_opponents()` (lines 246-309) - Participant matching logic
- `get_head_to_head_stats()` (lines 311-446) - Advanced participant matching

**Documentation:**
- `CLAUDE.md` - Project development principles
- `docs/developer-guide.md` - Architecture and patterns
- `scripts/link_players_to_participants.py` - How linking works

---

## Notes for Future Work

### Potential Improvements (Not in Scope)
1. **Auto-linking improvements** - Machine learning for name matching
2. **Bulk participant override UI** - Web interface for fixing unlinked players
3. **Participant merge tool** - Handle duplicate participant records
4. **Historical name tracking** - Track name changes over time

### Related Work
- Participant linking was added in previous migration (see `docs/migrations/`)
- This task completes the participant rollout to all cross-match queries
- Future queries should use participant pattern from day one

---

## Questions & Assumptions

**Assumptions:**
1. The `tournament_participants` table is already populated (via sync script)
2. Most players are already linked (>70% coverage expected)
3. Unlinked players are acceptable (shown with ⚠️ indicator)
4. Charts can handle new columns without breaking

**Questions to resolve:**
1. Does maps page exist? Need to check `tournament_visualizer/pages/maps.py`
2. Are there unit tests for queries? Check `tests/test_queries.py`
3. Should we add ⚠️ indicator to charts for unlinked players?
4. Do we need to update any chart components to handle new columns?

**Decision: Check these during implementation and adjust plan as needed.**
