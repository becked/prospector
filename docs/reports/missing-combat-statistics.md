# Missing Combat Statistics Report

**Date:** November 6, 2025
**Status:** Analysis Complete
**Priority:** Medium

## Executive Summary

The Old World save files contain a comprehensive `<Stat>` element with 36+ player statistics covering combat, diplomacy, expansion, and achievement metrics. **None of these statistics are currently extracted or stored in the database.** This represents a significant gap in our tournament analytics capabilities, particularly for combat-focused analysis.

## Current State

### What IS Currently Tracked

| Data Type | XML Location | Database Table | Status |
|-----------|-------------|----------------|--------|
| Military power over time | `<MilitaryPowerHistory>` | `player_military_history` | ✅ Tracked |
| Units produced (totals) | `<UnitsProduced>` | `player_units_produced` | ✅ Tracked |
| City-specific production | `<UnitProductionCounts>` | `city_unit_production` | ✅ Tracked |
| Yield stockpiles | `<YieldStockpile>` | `player_statistics` | ✅ Tracked |
| Bonus counts | `<BonusCount>` | `player_statistics` | ✅ Tracked |
| Law changes | `<LawClassChangeCount>` | `player_statistics` | ✅ Tracked |

### What is NOT Currently Tracked

The `<Stat>` element contains 36+ statistics that are **not extracted**. These are stored per player at the end of each game and represent cumulative game-wide achievements.

## Available Statistics

### Combat Statistics (8 fields)

| Statistic | Description | Use Case |
|-----------|-------------|----------|
| `STAT_UNIT_MILITARY_KILLED` | Enemy military units killed | Combat effectiveness, aggression analysis |
| `STAT_UNIT_MILITARY_KILLED_ANY_GENERAL` | Enemy units killed by generals | General combat performance |
| `STAT_UNIT_MILITARY_KILLED_GENERAL` | Enemy generals killed | Elite combat achievements |
| `STAT_UNIT_LOST` | Total units lost | Combat casualties, attrition |
| `STAT_REGULAR_MILITARY_LOST` | Regular military units lost | Military losses (excludes settlers, workers) |
| `STAT_UNIT_PROMOTED` | Units promoted to higher levels | Military experience, veteran forces |
| `STAT_UNIT_HEALED` | Units healed | Sustain capability, defensive tactics |
| `STAT_UNIT_TRAINED` | Units trained (unclear vs. produced) | Possibly training bonuses/upgrades |

### Territorial Statistics (2 fields)

| Statistic | Description | Use Case |
|-----------|-------------|----------|
| `STAT_CITY_CAPTURED` | Enemy cities captured | Military conquest success |
| `STAT_CITY_LOST` | Cities lost to enemies | Defensive failures, counterplay |
| `STAT_CITY_FOUNDED` | New cities founded | Expansion rate (duplicates city table data) |

### Development Statistics (10 fields)

| Statistic | Description | Use Case |
|-----------|-------------|----------|
| `STAT_IMPROVEMENT_FINISHED` | Improvements built | Infrastructure investment |
| `STAT_IMPROVEMENT_REPAIRED` | Improvements repaired | Maintenance, post-combat recovery |
| `STAT_SPECIALIST_PRODUCED` | Specialists created | Advanced economy analysis |
| `STAT_TECH_DISCOVERED` | Technologies researched | Tech pace, strategy |
| `STAT_TILES_REVEALED` | Map tiles explored | Exploration speed, scouting |
| `STAT_VEGETATION_REMOVED` | Vegetation cleared | Tile development |
| `STAT_TREES_REMOVED` | Trees chopped | Lumber/production focus |
| `STAT_RESOURCE_HARVESTED` | Resources extracted | Resource exploitation |
| `STAT_CULTURE_LEVEL_INCREASED` | Culture level gains | Cultural development |
| `STAT_HAPPINESS_LEVEL_INCREASED` | Happiness level gains | Civic management |

### Diplomacy & Religion Statistics (8 fields)

| Statistic | Description | Use Case |
|-----------|-------------|----------|
| `STAT_TRIBE_CONTACTED` | Barbarian tribes contacted | Early game diplomacy |
| `STAT_TRIBE_DECLARED_WAR` | War declared on tribes | Aggression vs. tribes |
| `STAT_TRIBE_CLEARED` | Barbarian tribes eliminated | Map control |
| `STAT_RELIGION_SPREAD` | Religion spread events | Religious influence |
| `STAT_PAGAN_RELIGION_SPREAD` | Pagan religion spread | Alternative religion tracking |
| `STAT_WORLD_RELIGION_FOUNDED` | World religions founded | Religious founding achievements |
| `STAT_NATION_FOUNDED` | Nation founding events | Political milestones |
| `STAT_LAW_ADOPTED` | Laws adopted | Governance tracking (duplicates law_changes) |
| `STAT_LAW_CHANGED` | Laws changed | Governance flexibility |

### Character & Achievement Statistics (8 fields)

| Statistic | Description | Use Case |
|-----------|-------------|----------|
| `STAT_CHILDREN_COUNT` | Ruler children born | Dynasty building |
| `STAT_YEARS_REIGNED` | Total years ruled | Leadership stability |
| `STAT_COURTIER_ADDED` | Courtiers recruited | Court development |
| `STAT_CLERGY_ADDED` | Clergy appointed | Religious administration |
| `STAT_AMBITION_ACHIEVED` | Ambitions completed | Goal-driven gameplay |
| `STAT_LANDMARK_DISCOVERED` | Landmarks discovered | Exploration achievements |
| `STAT_LANDMARK_NAMED` | Landmarks named | Naming rights, territorial claims |

## XML Structure

```xml
<Player ID="0" OnlineID="...">
  <Stat>
    <!-- Combat -->
    <STAT_UNIT_MILITARY_KILLED>29</STAT_UNIT_MILITARY_KILLED>
    <STAT_UNIT_MILITARY_KILLED_ANY_GENERAL>12</STAT_UNIT_MILITARY_KILLED_ANY_GENERAL>
    <STAT_UNIT_MILITARY_KILLED_GENERAL>6</STAT_UNIT_MILITARY_KILLED_GENERAL>
    <STAT_UNIT_LOST>11</STAT_UNIT_LOST>
    <STAT_REGULAR_MILITARY_LOST>7</STAT_REGULAR_MILITARY_LOST>
    <STAT_UNIT_PROMOTED>11</STAT_UNIT_PROMOTED>
    <STAT_UNIT_HEALED>25</STAT_UNIT_HEALED>
    <STAT_UNIT_TRAINED>37</STAT_UNIT_TRAINED>

    <!-- Territorial -->
    <STAT_CITY_CAPTURED>1</STAT_CITY_CAPTURED>
    <STAT_CITY_LOST>1</STAT_CITY_LOST>
    <STAT_CITY_FOUNDED>6</STAT_CITY_FOUNDED>

    <!-- Development -->
    <STAT_IMPROVEMENT_FINISHED>23</STAT_IMPROVEMENT_FINISHED>
    <STAT_SPECIALIST_PRODUCED>5</STAT_SPECIALIST_PRODUCED>
    <STAT_TECH_DISCOVERED>12</STAT_TECH_DISCOVERED>
    <STAT_TILES_REVEALED>1165</STAT_TILES_REVEALED>
    <STAT_RESOURCE_HARVESTED>3</STAT_RESOURCE_HARVESTED>
    <STAT_VEGETATION_REMOVED>41</STAT_VEGETATION_REMOVED>
    <STAT_TREES_REMOVED>15</STAT_TREES_REMOVED>

    <!-- Diplomacy & Religion -->
    <STAT_TRIBE_CONTACTED>4</STAT_TRIBE_CONTACTED>
    <STAT_TRIBE_CLEARED>2</STAT_TRIBE_CLEARED>
    <STAT_RELIGION_SPREAD>8</STAT_RELIGION_SPREAD>

    <!-- Characters & Achievements -->
    <STAT_CHILDREN_COUNT>5</STAT_CHILDREN_COUNT>
    <STAT_YEARS_REIGNED>85</STAT_YEARS_REIGNED>
    <STAT_AMBITION_ACHIEVED>3</STAT_AMBITION_ACHIEVED>
    <STAT_LANDMARK_DISCOVERED>2</STAT_LANDMARK_DISCOVERED>
  </Stat>
</Player>
```

## High-Value Use Cases

### 1. Combat Effectiveness Dashboard
**Priority: HIGH**

Create a "Combat Performance" tab showing:
- Kill/Death ratio (military_killed / units_lost)
- General effectiveness (kills_by_generals / total_kills)
- Combat efficiency (promotions, healings per unit produced)
- Conquest rate (cities captured vs. cities founded)

**Impact:** Directly answers "who won by military dominance vs. economic superiority"

### 2. Aggression vs. Defense Analysis
**Priority: HIGH**

Compare:
- Offensive players: High `STAT_UNIT_MILITARY_KILLED`, `STAT_CITY_CAPTURED`
- Defensive players: High `STAT_UNIT_HEALED`, low `STAT_CITY_LOST`
- Peaceful players: Low combat stats, high development stats

**Impact:** Identifies playstyle archetypes beyond just unit production

### 3. Military Loss Analysis
**Priority: MEDIUM**

Track unit attrition:
- Units lost vs. enemy kills (was it worth it?)
- Regular military lost vs. total lost (losing workers vs. soldiers)
- Cities lost (catastrophic defeats)

**Impact:** Understand **cost** of victory, not just victory itself

### 4. Development Speed Comparison
**Priority: MEDIUM**

Compare non-combat progress:
- Tech discovery rate
- Improvement completion rate
- Specialist production
- Exploration speed (tiles revealed)

**Impact:** Economic vs. military strategy comparison

### 5. Tribal Interaction Patterns
**Priority: LOW**

Analyze barbarian diplomacy:
- Tribes contacted vs. cleared (peaceful vs. aggressive)
- Early game barbarian pressure

**Impact:** Early game strategy insights

## Implementation Considerations

### Database Schema Addition

Add new table `player_combat_statistics`:

```sql
CREATE TABLE player_combat_statistics (
    match_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    stat_name VARCHAR NOT NULL,
    value INTEGER NOT NULL,
    PRIMARY KEY (match_id, player_id, stat_name),
    FOREIGN KEY (match_id, player_id) REFERENCES players(match_id, player_id)
);
```

**Rationale:**
- Flexible schema accommodates all 36+ statistics
- Future-proof for new stats added by game updates
- Similar to existing `player_statistics` table structure
- Normalized design avoids 36 columns

### Parser Changes

Update `tournament_visualizer/data/parser.py`:

```python
def extract_player_statistics(self) -> List[Dict[str, Any]]:
    # ... existing code for YieldStockpile, BonusCount, LawClassChangeCount ...

    # ADD: Extract Stat
    stat_elem = player_elem.find(".//Stat")
    if stat_elem is not None:
        for stat_child in stat_elem:
            stat_name = stat_child.tag
            value = self._safe_int(stat_child.text, 0)

            if value > 0:  # Only store non-zero values
                statistics.append(
                    {
                        "player_id": player_index,
                        "stat_category": "combat_stats",  # or "player_stats"
                        "stat_name": stat_name,
                        "value": value,
                    }
                )
```

**Effort:** ~15 minutes of coding + testing

### Query Layer

Add queries to `tournament_visualizer/data/queries.py`:

```python
def get_player_combat_stats(self, match_id: int) -> pd.DataFrame:
    """Get combat statistics for all players in a match."""
    query = """
        SELECT
            p.player_name,
            s.stat_name,
            s.value
        FROM player_combat_statistics s
        JOIN players p ON s.match_id = p.match_id AND s.player_id = p.player_id
        WHERE s.match_id = ?
        AND s.stat_name LIKE 'STAT_UNIT_%' OR s.stat_name LIKE 'STAT_CITY_%'
        ORDER BY p.player_name, s.stat_name
    """
    return self.db.query(query, [match_id])

def get_combat_effectiveness(self, match_id: int) -> pd.DataFrame:
    """Calculate kill/death ratios and combat metrics."""
    query = """
        WITH combat AS (
            SELECT
                player_id,
                MAX(CASE WHEN stat_name = 'STAT_UNIT_MILITARY_KILLED' THEN value ELSE 0 END) as kills,
                MAX(CASE WHEN stat_name = 'STAT_UNIT_LOST' THEN value ELSE 0 END) as losses,
                MAX(CASE WHEN stat_name = 'STAT_UNIT_PROMOTED' THEN value ELSE 0 END) as promotions,
                MAX(CASE WHEN stat_name = 'STAT_CITY_CAPTURED' THEN value ELSE 0 END) as cities_captured
            FROM player_combat_statistics
            WHERE match_id = ?
            GROUP BY player_id
        )
        SELECT
            p.player_name,
            c.kills,
            c.losses,
            ROUND(CAST(c.kills AS FLOAT) / NULLIF(c.losses, 0), 2) as kd_ratio,
            c.promotions,
            c.cities_captured
        FROM combat c
        JOIN players p ON p.match_id = ? AND p.player_id = c.player_id
        ORDER BY c.kills DESC
    """
    return self.db.query(query, [match_id, match_id])
```

### UI/Visualization

Add "Combat Analysis" section to Match Details page:

1. **Combat Effectiveness Table**
   - Columns: Player, Kills, Deaths, K/D Ratio, Cities Captured/Lost
   - Sortable by any metric

2. **Military Casualties Chart**
   - Stacked bar: Units lost (red) vs. Units killed (green)
   - Visual comparison of offensive vs. defensive success

3. **Combat Style Radar Chart**
   - Axes: Aggression (kills), Defense (heals), Conquest (cities captured), Attrition (losses)
   - Overlaid radar for each player

4. **Development vs. Combat Scatter**
   - X-axis: Total combat stats (kills + captures)
   - Y-axis: Total development stats (techs + improvements)
   - Each point = one player
   - Quadrants: Pure Military, Pure Economy, Balanced, Struggling

## Data Quality Considerations

### Known Limitations

1. **Cumulative Only:** These are end-of-game totals, not turn-by-turn history
2. **No Opponent Tracking:** Stats don't identify which opponent was killed/captured from
3. **Ambiguous Fields:** `STAT_UNIT_TRAINED` unclear vs. `UnitsProduced`
4. **Zero Values:** Statistics not achieved are omitted from XML (need to handle missing data)

### Testing Requirements

1. Verify player ID mapping (XML 0-based → DB 1-based)
2. Confirm all 36 statistics appear across multiple games
3. Test zero-handling for players with no combat
4. Validate K/D ratio calculation with division by zero protection

## Recommendation

**Implement Tier 1 (Combat Stats) Immediately**

Extract and store these 10 high-value statistics:
- `STAT_UNIT_MILITARY_KILLED`
- `STAT_UNIT_MILITARY_KILLED_GENERAL`
- `STAT_UNIT_LOST`
- `STAT_REGULAR_MILITARY_LOST`
- `STAT_UNIT_PROMOTED`
- `STAT_UNIT_HEALED`
- `STAT_CITY_CAPTURED`
- `STAT_CITY_LOST`
- `STAT_CITY_FOUNDED`
- `STAT_TECH_DISCOVERED`

**Implement Tier 2 (All Stats) Later**

Store all remaining statistics for completeness, but prioritize Tier 1 for visualization.

### Implementation Effort

| Task | Effort | Priority |
|------|--------|----------|
| Schema migration | 30 min | HIGH |
| Parser update | 15 min | HIGH |
| Database insertion | 10 min | HIGH |
| Query layer | 1 hour | HIGH |
| Combat dashboard | 2-3 hours | MEDIUM |
| Testing & validation | 1 hour | HIGH |
| **Total** | **5-6 hours** | - |

## Related Work

- **City Data Extraction** (`docs/migrations/012_add_city_data.md`): Similar approach for city-level data
- **Territory Tiles** (`docs/migrations/013_add_territories.md`): Demonstrates large stat extraction
- **Yield Display Scale** (`docs/reports/yield-display-scale-issue.md`): Precedent for discovering missing transformations

## Next Steps

1. Create migration `docs/migrations/014_add_combat_statistics.md`
2. Implement parser extraction for `<Stat>` element
3. Create `player_combat_statistics` table
4. Add bulk insert to database layer
5. Update ETL pipeline
6. Add query methods
7. Create combat effectiveness dashboard
8. Re-import tournament data with `--force`

## Conclusion

The `<Stat>` element represents a treasure trove of **36+ untapped statistics** that would significantly enhance combat and strategy analysis capabilities. The implementation is straightforward (similar to existing stat extraction) and provides immediate value for understanding tournament dynamics beyond simple "who won" metrics.

**Key Value:** Answers "**HOW did they win?**" (military conquest vs. economic dominance) rather than just "who won?"
