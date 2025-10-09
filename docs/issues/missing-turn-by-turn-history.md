# Missing Turn-by-Turn Historical Data in Database

**Date:** October 8, 2025
**Status:** Identified - Awaiting Implementation
**Priority:** High
**Impact:** Major analytics capabilities missing

---

## Executive Summary

The DuckDB database successfully captures **snapshot/final state data** but is **missing critical turn-by-turn historical data** that exists in the Old World save file XML. This prevents key analytics like:
- Victory point progression curves
- Economic growth analysis
- Military buildup patterns
- Territorial expansion visualization
- Resource efficiency calculations

**Verification:** YieldRateHistory and other *History elements in the XML **DO contain accurate turn-by-turn data** (not just final state). The reference documentation is correct.

**Recommendation:** Implement **Option C (Hybrid Approach)** - repurpose existing broken tables where possible, add new history tables for high-value analytics.

---

## Data Verification: YieldRateHistory Contains Real History

### XML Evidence

Examining `match_426504721_anarkos-becked.zip`, the YieldRateHistory section shows clear turn-by-turn progression:

```xml
<YieldRateHistory>
  <YIELD_GROWTH>
    <T2>100</T2>
    <T3>100</T3>
    <T4>100</T4>
    <T5>100</T5>
    <T6>100</T6>
    <T7>120</T7>    <!-- Growth increase -->
    <T8>120</T8>
    <T9>218</T9>    <!-- Major jump -->
    <T10>240</T10>
    ...
    <T55>945</T55>
    <T56>1077</T56>
    <T57>1101</T57>
    ...
    <T69>858</T69>  <!-- Final turn -->
  </YIELD_GROWTH>
  <YIELD_CIVICS>
    <T2>190</T2>
    <T3>190</T3>
    <T4>190</T4>
    ...
  </YIELD_CIVICS>
  ...
</YieldRateHistory>
```

**Key Observations:**
- Each `<TN>` tag represents a distinct turn number (T2 = turn 2, T69 = turn 69)
- Values change over time (100 → 120 → 218 → ... → 858)
- Multiple yield types tracked (GROWTH, CIVICS, TRAINING, SCIENCE, etc.)
- Both players have separate YieldRateHistory sections

**Conclusion:** This is genuine turn-by-turn historical data, not a single snapshot. The reference document is accurate.

### Other History Elements Verified

Similar turn-by-turn patterns found in:
- `PointsHistory` - Victory points per turn (T2, T3, ..., T69)
- `MilitaryPowerHistory` - Military strength per turn
- `LegitimacyHistory` - Governance stability per turn
- `FamilyOpinionHistory` - Family relations per turn
- `ReligionOpinionHistory` - Religious relations per turn

All follow the same `<TN>value</TN>` structure with values changing over time.

---

## Current Database State

### ✅ What's Working Well

#### 1. Match & Player Fundamentals
- **Tables:** `matches`, `players`, `match_winners`, `match_metadata`
- **Status:** ✅ Fully functional
- **Data Quality:** Good (15 matches, 30 players)
- **Coverage:** Complete metadata, game settings, player info, final scores

#### 2. Events System
- **Table:** `events`
- **Status:** ✅ Functional with both MemoryData and LogData
- **Data Quality:** 3,622 events across 15 matches
- **Event Types:**
  - TECH_DISCOVERED: 533 events
  - LAW_ADOPTED: 143 events
  - CITY_FOUNDED: 193 events
  - MEMORYPLAYER_ATTACKED_UNIT: 484 events
  - MEMORYTRIBE_ATTACKED_UNIT: 439 events
  - And 20+ more types
- **Player ID Mapping:** ✅ Correctly converts 0-based XML to 1-based DB

#### 3. Final State Snapshots
- **Tables:** `technology_progress`, `player_statistics`, `units_produced`
- **Status:** ✅ Fully functional
- **Coverage:**
  - Technology: 533 entries, 59 unique techs
  - Statistics: 1,126+ entries (yields, bonuses, law changes)
  - Units: Comprehensive production counts per player

#### 4. Schema Design
- ✅ Good foreign key relationships
- ✅ Appropriate indexes for common queries
- ✅ JSON fields for flexible event data
- ✅ Useful views (`match_summary`, `player_performance`)

### ❌ Critical Gaps - Missing Historical Data

#### 1. Victory Points History ❌
**XML Source:** `Player/PointsHistory`
```xml
<PointsHistory>
  <T2>1</T2>
  <T3>1</T3>
  <T4>1</T4>
  ...
  <T69>157</T69>
</PointsHistory>
```

**Current DB:** Only `players.final_score` (single value)

**Impact:**
- Cannot analyze VP accumulation curves
- Cannot identify critical turning points or momentum shifts
- Cannot detect catch-up periods or runaway victories
- Cannot compare player progression side-by-side over time

**Analytics Lost:**
- "Show me VP progression for both players"
- "When did Player A pull ahead?"
- "How many VPs were gained per turn on average?"
- "Identify periods of rapid VP growth"

#### 2. Resource/Yield Production History ❌
**XML Source:** `Player/YieldRateHistory`
```xml
<YieldRateHistory>
  <YIELD_GROWTH>
    <T2>100</T2>
    <T3>100</T3>
    ...
    <T69>858</T69>
  </YIELD_GROWTH>
  <YIELD_CIVICS>
    <T2>190</T2>
    ...
  </YIELD_CIVICS>
  <YIELD_TRAINING>...</YIELD_TRAINING>
  <YIELD_SCIENCE>...</YIELD_SCIENCE>
  <YIELD_ORDERS>...</YIELD_ORDERS>
  ...
</YieldRateHistory>
```

**Current DB:** Empty `resources` table (0 rows)

**Impact:**
- Cannot analyze economic growth patterns
- Cannot measure production efficiency
- Cannot identify resource bottlenecks
- Cannot compare economic strategies

**Analytics Lost:**
- "Show me science production over time"
- "Compare military (TRAINING) vs economy (CIVICS) investment"
- "When did Player A's economy overtake Player B's?"
- "Calculate resource efficiency per city"
- "Identify periods of economic crisis or boom"

#### 3. Military Power History ❌
**XML Source:** `Player/MilitaryPowerHistory`
```xml
<MilitaryPowerHistory>
  <T2>0</T2>
  <T3>0</T3>
  <T4>18</T4>
  ...
  <T69>142</T69>
</MilitaryPowerHistory>
```

**Current DB:** Not captured anywhere

**Impact:**
- Cannot analyze military buildup patterns
- Cannot detect arms races between players
- Cannot correlate military investment with outcomes
- Cannot identify aggressive vs defensive strategies

**Analytics Lost:**
- "Show military power over time for both players"
- "Detect arms race periods"
- "When did players invest in military?"
- "Correlate military strength with victory"

#### 4. Legitimacy History ❌
**XML Source:** `Player/LegitimacyHistory`
```xml
<LegitimacyHistory>
  <T2>100</T2>
  <T3>100</T3>
  <T4>100</T4>
  ...
  <T69>100</T69>
</LegitimacyHistory>
```

**Current DB:** Not captured

**Impact:**
- Cannot analyze governance stability
- Cannot identify legitimacy crises
- Cannot correlate legitimacy with player decisions

**Analytics Lost:**
- "Show legitimacy stability over time"
- "Identify legitimacy crisis periods"
- "Correlate low legitimacy with events"

#### 5. Family Opinion History ❌
**XML Source:** `Player/FamilyOpinionHistory`
```xml
<FamilyOpinionHistory>
  <FAMILY_ACHAEMENID>
    <T2>100</T2>
    <T3>100</T3>
    ...
  </FAMILY_ACHAEMENID>
  <FAMILY_ARSACID>
    <T2>0</T2>
    <T3>0</T3>
    ...
  </FAMILY_ARSACID>
</FamilyOpinionHistory>
```

**Current DB:** Not captured

**Impact:**
- Cannot analyze internal politics
- Cannot measure family management skill
- Cannot detect family crises or revolts

#### 6. Religion Opinion History ❌
**XML Source:** `Player/ReligionOpinionHistory`
```xml
<ReligionOpinionHistory>
  <RELIGION_PAGAN_PERSIA>
    <T14>100</T14>
    <T15>100</T15>
    ...
  </RELIGION_PAGAN_PERSIA>
</ReligionOpinionHistory>
```

**Current DB:** Not captured

**Impact:**
- Cannot analyze religious dynamics
- Cannot measure religious management
- Cannot detect religious conflicts

### ⚠️ Broken/Empty Tables

#### 1. `game_state` Table - Broken Data
**Current State:**
```sql
SELECT * FROM game_state LIMIT 5;
-- All 3,911 rows have:
--   turn_number: 0
--   active_player_id: NULL
--   game_year: NULL
--   turn_timestamp: NULL
```

**Root Cause:** Parser's `extract_game_states()` looks for `<Turn>` elements that don't exist in the expected format.

**Assessment:** This table was designed for real-time game state tracking (active player, current year), not post-game analytics. It's not useful for our purposes.

**Recommendation:** Investigate further, but likely **delete** this table as it serves a different use case.

#### 2. `resources` Table - Empty by Design
**Current State:** 0 rows

**Root Cause:** Parser method `extract_resources()` literally returns an empty list:
```python
def extract_resources(self) -> List[Dict[str, Any]]:
    """Extract player resource information over time.

    Note: Old World save files only contain final state, not turn-by-turn history.
    This method returns an empty list as historical resource data is unavailable.
    """
    # No turn-by-turn resource data available in save files
    return []
```

**Assessment:** This comment is **incorrect** - YieldRateHistory DOES contain turn-by-turn data! This was a mistaken design decision.

**Recommendation:** **Repurpose** this table to store YieldRateHistory data (see schema below).

#### 3. `territories` Table - Empty by Design
**Current State:** 0 rows

**Root Cause:** Same as resources - parser returns empty list with comment about no historical data.

**Assessment:** Tile-level data would be massive (2,024 tiles × 70 turns × 15 matches = 2.1M rows). User confirmed not needed.

**Recommendation:** **Keep empty** - not needed for player-level analytics.

---

## Recommended Solution: Option C (Hybrid Approach)

### Strategy

1. **Fix What's Salvageable:** Repurpose the existing `resources` table for YieldRateHistory
2. **Delete What's Broken:** Remove or archive `game_state` table
3. **Add High-Value Tables:** Create new history tables for points, military, legitimacy, opinions
4. **Clean and Focused:** End result is a coherent schema optimized for analytics

### Performance Analysis

**Data Volume Estimate:**
- 15 matches × 2 players × ~70 turns × 10 yield types = **~21,000 rows** for yield history
- 15 matches × 2 players × ~70 turns = **~2,100 rows** for points history
- 15 matches × 2 players × ~70 turns = **~2,100 rows** for military history
- 15 matches × 2 players × ~70 turns = **~2,100 rows** for legitimacy history
- 15 matches × 2 players × ~3 families × ~70 turns = **~6,300 rows** for family opinions
- 15 matches × 2 players × ~3 religions × ~70 turns = **~6,300 rows** for religion opinions

**Total:** ~40,000 new rows across all history tables

**Assessment:** ✅ Totally acceptable for DuckDB - this is a small dataset.

---

## Implementation Plan

### Phase 1: Schema Changes (Migration Required)

#### 1.1. Delete/Archive `game_state` Table
```sql
-- Option A: Drop entirely
DROP TABLE game_state;

-- Option B: Rename for investigation
ALTER TABLE game_state RENAME TO game_state_deprecated;
```

#### 1.2. Modify `resources` Table for YieldRateHistory

**Current Schema:**
```sql
CREATE TABLE resources(
    resource_id BIGINT PRIMARY KEY,
    match_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,
    turn_number INTEGER NOT NULL,
    resource_type VARCHAR NOT NULL,  -- Unclear what this was for
    amount INTEGER NOT NULL,
    UNIQUE(match_id, player_id, turn_number, resource_type)
);
```

**New Schema:**
```sql
-- Rename for clarity
ALTER TABLE resources RENAME TO player_yield_history;

-- Schema is actually already correct! Just needs:
-- - resource_type → stores yield type (YIELD_GROWTH, YIELD_CIVICS, etc.)
-- - amount → stores the yield rate value for that turn
-- - Already has match_id, player_id, turn_number

-- Just need to populate it with YieldRateHistory data
```

#### 1.3. Create New History Tables

```sql
-- Victory points progression
CREATE TABLE player_points_history (
    points_history_id BIGINT PRIMARY KEY,
    match_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,
    turn_number INTEGER NOT NULL,
    points INTEGER NOT NULL,
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    CHECK (turn_number >= 0),
    CHECK (points >= 0),
    UNIQUE (match_id, player_id, turn_number)
);
CREATE INDEX idx_points_history_match_player ON player_points_history(match_id, player_id);
CREATE INDEX idx_points_history_turn ON player_points_history(turn_number);

-- Military power progression
CREATE TABLE player_military_history (
    military_history_id BIGINT PRIMARY KEY,
    match_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,
    turn_number INTEGER NOT NULL,
    military_power INTEGER NOT NULL,
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    CHECK (turn_number >= 0),
    CHECK (military_power >= 0),
    UNIQUE (match_id, player_id, turn_number)
);
CREATE INDEX idx_military_history_match_player ON player_military_history(match_id, player_id);
CREATE INDEX idx_military_history_turn ON player_military_history(turn_number);

-- Legitimacy tracking
CREATE TABLE player_legitimacy_history (
    legitimacy_history_id BIGINT PRIMARY KEY,
    match_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,
    turn_number INTEGER NOT NULL,
    legitimacy INTEGER NOT NULL,
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    CHECK (turn_number >= 0),
    CHECK (legitimacy >= 0 AND legitimacy <= 100),
    UNIQUE (match_id, player_id, turn_number)
);
CREATE INDEX idx_legitimacy_history_match_player ON player_legitimacy_history(match_id, player_id);
CREATE INDEX idx_legitimacy_history_turn ON player_legitimacy_history(turn_number);

-- Family opinion tracking
CREATE TABLE family_opinion_history (
    family_opinion_id BIGINT PRIMARY KEY,
    match_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,
    turn_number INTEGER NOT NULL,
    family_name VARCHAR NOT NULL,
    opinion INTEGER NOT NULL,
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    CHECK (turn_number >= 0),
    CHECK (opinion >= 0 AND opinion <= 100),
    UNIQUE (match_id, player_id, turn_number, family_name)
);
CREATE INDEX idx_family_opinion_match_player ON family_opinion_history(match_id, player_id);
CREATE INDEX idx_family_opinion_family ON family_opinion_history(family_name);

-- Religion opinion tracking
CREATE TABLE religion_opinion_history (
    religion_opinion_id BIGINT PRIMARY KEY,
    match_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,
    turn_number INTEGER NOT NULL,
    religion_name VARCHAR NOT NULL,
    opinion INTEGER NOT NULL,
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    CHECK (turn_number >= 0),
    CHECK (opinion >= 0 AND opinion <= 100),
    UNIQUE (match_id, player_id, turn_number, religion_name)
);
CREATE INDEX idx_religion_opinion_match_player ON religion_opinion_history(match_id, player_id);
CREATE INDEX idx_religion_opinion_religion ON religion_opinion_history(religion_name);
```

### Phase 2: Parser Changes

#### 2.1. Rename Table in Parser
```python
# In parser.py and database.py
# Change references from "resources" to "player_yield_history"
```

#### 2.2. Implement `extract_yield_history()`

**Current (broken):**
```python
def extract_resources(self) -> List[Dict[str, Any]]:
    # No turn-by-turn resource data available in save files
    return []
```

**New implementation:**
```python
def extract_yield_history(self) -> List[Dict[str, Any]]:
    """Extract yield production rates over time from YieldRateHistory.

    Parses Player/YieldRateHistory elements which contain turn-by-turn
    yield production rates for all yield types (GROWTH, CIVICS, TRAINING, etc.).

    Returns:
        List of yield history dictionaries with:
        - player_id: Database player ID (1-based)
        - turn_number: Game turn
        - yield_type: Type of yield (YIELD_GROWTH, YIELD_CIVICS, etc.)
        - amount: Production rate for that yield on that turn
    """
    if self.root is None:
        raise ValueError("XML not parsed. Call extract_and_parse() first.")

    yield_data = []

    # Find all player elements with OnlineID (human players)
    player_elements = self.root.findall(".//Player[@OnlineID]")

    for player_elem in player_elements:
        # Get player's XML ID (0-based)
        player_xml_id = player_elem.get("ID")
        if player_xml_id is None:
            continue

        # Convert to 1-based player_id for database
        player_id = int(player_xml_id) + 1

        # Find YieldRateHistory for this player
        yield_history = player_elem.find(".//YieldRateHistory")
        if yield_history is None:
            continue

        # Process each yield type (YIELD_GROWTH, YIELD_CIVICS, etc.)
        for yield_type_elem in yield_history:
            yield_type = yield_type_elem.tag  # e.g., "YIELD_GROWTH"

            # Process each turn (T2, T3, ..., T69)
            for turn_elem in yield_type_elem:
                turn_tag = turn_elem.tag  # e.g., "T2"

                # Extract turn number from tag (T2 -> 2)
                if not turn_tag.startswith('T'):
                    continue

                turn_number = self._safe_int(turn_tag[1:])
                amount = self._safe_int(turn_elem.text)

                if turn_number is None or amount is None:
                    continue

                yield_data.append({
                    "player_id": player_id,
                    "turn_number": turn_number,
                    "yield_type": yield_type,
                    "amount": amount
                })

    return yield_data
```

#### 2.3. Implement `extract_points_history()`

```python
def extract_points_history(self) -> List[Dict[str, Any]]:
    """Extract victory points progression from PointsHistory.

    Returns:
        List of points history dictionaries
    """
    if self.root is None:
        raise ValueError("XML not parsed. Call extract_and_parse() first.")

    points_data = []

    player_elements = self.root.findall(".//Player[@OnlineID]")

    for player_elem in player_elements:
        player_xml_id = player_elem.get("ID")
        if player_xml_id is None:
            continue

        player_id = int(player_xml_id) + 1

        points_history = player_elem.find(".//PointsHistory")
        if points_history is None:
            continue

        for turn_elem in points_history:
            turn_tag = turn_elem.tag
            if not turn_tag.startswith('T'):
                continue

            turn_number = self._safe_int(turn_tag[1:])
            points = self._safe_int(turn_elem.text)

            if turn_number is None or points is None:
                continue

            points_data.append({
                "player_id": player_id,
                "turn_number": turn_number,
                "points": points
            })

    return points_data
```

#### 2.4. Implement `extract_military_history()`

```python
def extract_military_history(self) -> List[Dict[str, Any]]:
    """Extract military power progression from MilitaryPowerHistory.

    Returns:
        List of military history dictionaries
    """
    if self.root is None:
        raise ValueError("XML not parsed. Call extract_and_parse() first.")

    military_data = []

    player_elements = self.root.findall(".//Player[@OnlineID]")

    for player_elem in player_elements:
        player_xml_id = player_elem.get("ID")
        if player_xml_id is None:
            continue

        player_id = int(player_xml_id) + 1

        military_history = player_elem.find(".//MilitaryPowerHistory")
        if military_history is None:
            continue

        for turn_elem in military_history:
            turn_tag = turn_elem.tag
            if not turn_tag.startswith('T'):
                continue

            turn_number = self._safe_int(turn_tag[1:])
            military_power = self._safe_int(turn_elem.text)

            if turn_number is None or military_power is None:
                continue

            military_data.append({
                "player_id": player_id,
                "turn_number": turn_number,
                "military_power": military_power
            })

    return military_data
```

#### 2.5. Implement `extract_legitimacy_history()`

```python
def extract_legitimacy_history(self) -> List[Dict[str, Any]]:
    """Extract legitimacy progression from LegitimacyHistory.

    Returns:
        List of legitimacy history dictionaries
    """
    if self.root is None:
        raise ValueError("XML not parsed. Call extract_and_parse() first.")

    legitimacy_data = []

    player_elements = self.root.findall(".//Player[@OnlineID]")

    for player_elem in player_elements:
        player_xml_id = player_elem.get("ID")
        if player_xml_id is None:
            continue

        player_id = int(player_xml_id) + 1

        legitimacy_history = player_elem.find(".//LegitimacyHistory")
        if legitimacy_history is None:
            continue

        for turn_elem in legitimacy_history:
            turn_tag = turn_elem.tag
            if not turn_tag.startswith('T'):
                continue

            turn_number = self._safe_int(turn_tag[1:])
            legitimacy = self._safe_int(turn_elem.text)

            if turn_number is None or legitimacy is None:
                continue

            legitimacy_data.append({
                "player_id": player_id,
                "turn_number": turn_number,
                "legitimacy": legitimacy
            })

    return legitimacy_data
```

#### 2.6. Implement `extract_opinion_histories()`

```python
def extract_opinion_histories(self) -> Dict[str, List[Dict[str, Any]]]:
    """Extract family and religion opinion histories.

    Returns:
        Dictionary with 'family_opinions' and 'religion_opinions' lists
    """
    if self.root is None:
        raise ValueError("XML not parsed. Call extract_and_parse() first.")

    family_opinions = []
    religion_opinions = []

    player_elements = self.root.findall(".//Player[@OnlineID]")

    for player_elem in player_elements:
        player_xml_id = player_elem.get("ID")
        if player_xml_id is None:
            continue

        player_id = int(player_xml_id) + 1

        # Extract family opinions
        family_history = player_elem.find(".//FamilyOpinionHistory")
        if family_history is not None:
            for family_elem in family_history:
                family_name = family_elem.tag  # e.g., "FAMILY_ACHAEMENID"

                for turn_elem in family_elem:
                    turn_tag = turn_elem.tag
                    if not turn_tag.startswith('T'):
                        continue

                    turn_number = self._safe_int(turn_tag[1:])
                    opinion = self._safe_int(turn_elem.text)

                    if turn_number is None or opinion is None:
                        continue

                    family_opinions.append({
                        "player_id": player_id,
                        "turn_number": turn_number,
                        "family_name": family_name,
                        "opinion": opinion
                    })

        # Extract religion opinions
        religion_history = player_elem.find(".//ReligionOpinionHistory")
        if religion_history is not None:
            for religion_elem in religion_history:
                religion_name = religion_elem.tag  # e.g., "RELIGION_PAGAN_PERSIA"

                for turn_elem in religion_elem:
                    turn_tag = turn_elem.tag
                    if not turn_tag.startswith('T'):
                        continue

                    turn_number = self._safe_int(turn_tag[1:])
                    opinion = self._safe_int(turn_elem.text)

                    if turn_number is None or opinion is None:
                        continue

                    religion_opinions.append({
                        "player_id": player_id,
                        "turn_number": turn_number,
                        "religion_name": religion_name,
                        "opinion": opinion
                    })

    return {
        "family_opinions": family_opinions,
        "religion_opinions": religion_opinions
    }
```

#### 2.7. Update `parse_tournament_file()`

```python
def parse_tournament_file(zip_file_path: str) -> Dict[str, Any]:
    """Parse a tournament save file and extract all data."""
    parser = OldWorldSaveParser(zip_file_path)
    parser.extract_and_parse()

    # Extract all data components
    match_metadata = parser.extract_basic_metadata()
    players = parser.extract_players()

    # Extract events (both MemoryData and LogData)
    memory_events = parser.extract_events()
    logdata_events = parser.extract_logdata_events()
    events = memory_events + logdata_events

    # Extract statistics
    technology_progress = parser.extract_technology_progress()
    player_statistics = parser.extract_player_statistics()
    units_produced = parser.extract_units_produced()
    detailed_metadata = parser.extract_match_metadata()

    # Extract NEW history data
    yield_history = parser.extract_yield_history()
    points_history = parser.extract_points_history()
    military_history = parser.extract_military_history()
    legitimacy_history = parser.extract_legitimacy_history()
    opinion_histories = parser.extract_opinion_histories()

    # Determine winner
    winner_player_id = parser.determine_winner(players)
    match_metadata["winner_player_id"] = winner_player_id

    return {
        "match_metadata": match_metadata,
        "players": players,
        "events": events,
        "technology_progress": technology_progress,
        "player_statistics": player_statistics,
        "units_produced": units_produced,
        "detailed_metadata": detailed_metadata,
        # NEW: History data
        "yield_history": yield_history,
        "points_history": points_history,
        "military_history": military_history,
        "legitimacy_history": legitimacy_history,
        "family_opinion_history": opinion_histories["family_opinions"],
        "religion_opinion_history": opinion_histories["religion_opinions"],
    }
```

### Phase 3: Database Ingestion Updates

Update `tournament_visualizer/data/database.py` to:
1. Rename `resources` to `player_yield_history` in schema
2. Add new history table schemas
3. Update insertion methods to handle history data
4. Add appropriate ID generation for new tables

### Phase 4: Migration Script

Create `scripts/migrate_add_history_tables.py`:
```python
"""Migration: Add turn-by-turn history tables."""

import duckdb
from pathlib import Path

def migrate(db_path: Path):
    """Run migration to add history tables."""

    conn = duckdb.connect(str(db_path))

    # 1. Drop broken game_state table
    conn.execute("DROP TABLE IF EXISTS game_state")

    # 2. Rename resources to player_yield_history
    conn.execute("""
        ALTER TABLE resources
        RENAME TO player_yield_history
    """)

    # 3. Create new history tables
    # (Include all CREATE TABLE statements from Phase 1.3)

    # 4. Add migration record
    conn.execute("""
        INSERT INTO schema_migrations (version, description)
        VALUES ('002_add_history_tables', 'Add turn-by-turn history tables for analytics')
    """)

    conn.commit()
    conn.close()
```

### Phase 5: Re-import Data

```bash
# Backup database
cp tournament_data.duckdb tournament_data.duckdb.backup_$(date +%Y%m%d_%H%M%S)

# Run migration
uv run python scripts/migrate_add_history_tables.py

# Re-import all matches to populate new tables
uv run python scripts/import_tournaments.py --directory saves --force --verbose
```

---

## Analytics Unlocked

Once implemented, the following analytics become possible:

### Victory Point Analysis
```sql
-- VP progression comparison
SELECT
    p.player_name,
    h.turn_number,
    h.points
FROM player_points_history h
JOIN players p ON h.player_id = p.player_id
WHERE h.match_id = 1
ORDER BY h.turn_number, p.player_name;

-- Identify turning points (when leader changed)
WITH ranked AS (
    SELECT
        turn_number,
        player_id,
        points,
        RANK() OVER (PARTITION BY turn_number ORDER BY points DESC) as rank
    FROM player_points_history
    WHERE match_id = 1
)
SELECT * FROM ranked WHERE rank = 1 ORDER BY turn_number;
```

### Economic Analysis
```sql
-- Science production over time
SELECT
    p.player_name,
    h.turn_number,
    h.amount as science_rate
FROM player_yield_history h
JOIN players p ON h.player_id = p.player_id
WHERE h.match_id = 1
  AND h.yield_type = 'YIELD_SCIENCE'
ORDER BY h.turn_number, p.player_name;

-- Compare military vs civic investment
SELECT
    p.player_name,
    h.turn_number,
    SUM(CASE WHEN h.yield_type = 'YIELD_TRAINING' THEN h.amount ELSE 0 END) as military,
    SUM(CASE WHEN h.yield_type = 'YIELD_CIVICS' THEN h.amount ELSE 0 END) as civics
FROM player_yield_history h
JOIN players p ON h.player_id = p.player_id
WHERE h.match_id = 1
GROUP BY p.player_name, h.turn_number
ORDER BY h.turn_number, p.player_name;
```

### Military Analysis
```sql
-- Military buildup comparison
SELECT
    p.player_name,
    h.turn_number,
    h.military_power
FROM player_military_history h
JOIN players p ON h.player_id = p.player_id
WHERE h.match_id = 1
ORDER BY h.turn_number, p.player_name;

-- Detect arms race periods (both players building military)
WITH military_growth AS (
    SELECT
        player_id,
        turn_number,
        military_power,
        military_power - LAG(military_power) OVER (PARTITION BY player_id ORDER BY turn_number) as growth
    FROM player_military_history
    WHERE match_id = 1
)
SELECT turn_number
FROM military_growth
GROUP BY turn_number
HAVING MIN(growth) > 10  -- Both players growing significantly
ORDER BY turn_number;
```

### Internal Politics Analysis
```sql
-- Family opinion stability
SELECT
    p.player_name,
    f.family_name,
    AVG(f.opinion) as avg_opinion,
    MIN(f.opinion) as min_opinion,
    MAX(f.opinion) as max_opinion,
    STDDEV(f.opinion) as volatility
FROM family_opinion_history f
JOIN players p ON f.player_id = p.player_id
WHERE f.match_id = 1
GROUP BY p.player_name, f.family_name;
```

---

## Testing Strategy

### 1. Unit Tests
- Test each new extraction method with sample XML
- Verify player ID mapping (0-based → 1-based)
- Validate turn number extraction from `<TN>` tags
- Test edge cases (missing data, malformed XML)

### 2. Integration Tests
- Parse a full save file
- Verify all history tables populated
- Check data consistency (turn ranges, player IDs)
- Validate foreign key relationships

### 3. Data Validation Queries
```sql
-- Check turn coverage (should be continuous)
SELECT
    match_id,
    player_id,
    MIN(turn_number) as min_turn,
    MAX(turn_number) as max_turn,
    COUNT(DISTINCT turn_number) as turn_count,
    MAX(turn_number) - MIN(turn_number) + 1 as expected_count
FROM player_points_history
GROUP BY match_id, player_id;

-- Verify no orphaned records
SELECT COUNT(*)
FROM player_yield_history h
LEFT JOIN players p ON h.player_id = p.player_id
WHERE p.player_id IS NULL;

-- Check for duplicate turns (should be 0)
SELECT match_id, player_id, turn_number, COUNT(*)
FROM player_points_history
GROUP BY match_id, player_id, turn_number
HAVING COUNT(*) > 1;
```

---

## Risk Assessment

### Low Risk
- ✅ Data volume is manageable (~40K new rows)
- ✅ Schema changes are additive (no data loss)
- ✅ Parser changes follow existing patterns
- ✅ Can run migration on backup database first

### Medium Risk
- ⚠️ Renaming `resources` table may require code changes in multiple files
- ⚠️ Re-importing 15 matches may take significant time
- ⚠️ Need to verify all visualization code still works

### Mitigation
1. Always backup database before migration
2. Test migration on single match first
3. Run validation queries after import
4. Keep deprecated tables for rollback if needed

---

## Success Metrics

### Data Completeness
- ✅ All matches have points history (15 matches × 2 players × ~70 turns)
- ✅ All matches have yield history (15 × 2 × ~70 × ~10 yield types)
- ✅ All matches have military/legitimacy history
- ✅ No missing turns (continuous T2 → final turn)

### Analytics Capability
- ✅ Can generate VP progression charts
- ✅ Can compare economic strategies
- ✅ Can analyze military buildups
- ✅ Can identify critical turns/events

### Performance
- ✅ Queries complete in < 1 second
- ✅ Database size remains manageable (< 100MB)
- ✅ Dash app loads quickly

---

## Timeline Estimate

- **Phase 1 (Schema):** 1-2 hours
- **Phase 2 (Parser):** 3-4 hours
- **Phase 3 (Database):** 1-2 hours
- **Phase 4 (Migration):** 1 hour
- **Phase 5 (Re-import):** 1 hour
- **Testing & Validation:** 2-3 hours

**Total:** 9-13 hours of development work

---

## Next Steps

1. **Review & Approval:** Confirm this approach makes sense
2. **Create Migration Script:** Write the schema migration
3. **Implement Parsers:** Add extraction methods for all history types
4. **Test on Single Match:** Validate with one save file first
5. **Full Re-import:** Process all 15 matches
6. **Update Visualizations:** Add new charts for historical data
7. **Documentation:** Update developer guide with new tables

---

## Appendix: Example Queries for Dash App

### VP Progression Chart
```sql
SELECT
    m.game_name,
    p.player_name,
    p.civilization,
    h.turn_number,
    h.points
FROM player_points_history h
JOIN players p ON h.player_id = p.player_id
JOIN matches m ON h.match_id = m.match_id
WHERE h.match_id = ?
ORDER BY h.turn_number, p.player_name;
```

### Economic Comparison
```sql
SELECT
    p.player_name,
    h.turn_number,
    h.yield_type,
    h.amount
FROM player_yield_history h
JOIN players p ON h.player_id = p.player_id
WHERE h.match_id = ?
  AND h.yield_type IN ('YIELD_CIVICS', 'YIELD_TRAINING', 'YIELD_SCIENCE')
ORDER BY h.turn_number, p.player_name, h.yield_type;
```

### Military Arms Race Detection
```sql
WITH military_changes AS (
    SELECT
        player_id,
        turn_number,
        military_power,
        military_power - LAG(military_power) OVER (PARTITION BY player_id ORDER BY turn_number) as power_change
    FROM player_military_history
    WHERE match_id = ?
)
SELECT
    p.player_name,
    m.turn_number,
    m.military_power,
    m.power_change
FROM military_changes m
JOIN players p ON m.player_id = p.player_id
WHERE m.power_change > 0
ORDER BY m.turn_number, p.player_name;
```
