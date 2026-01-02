# Feature: Board State Comparison Tab

## Status: Approved
**Created**: 2024-12-31
**Updated**: 2025-01-01
**Source**: Discord feedback from Filthy, Siontific, and community

---

## Problem Statement

The current timeline shows **what happened** (events) but not **who was winning** at any given point. If you scroll to turn 35 in the middle of a match, you have no idea which player was ahead.

> "Using Aran vs Nizar, if I scroll to t35 as dead center in my screen: I have no idea who's winning."
> — Filthy

The goal is to tell the **story** of a game through data:

> "I'd like to be able to go, oh, I see, he went early Military Drill, completed steel, added 10 orders from finishing Jebel, and then had a military spike 5 turns later, and a big battle 3 turns after that."
> — Filthy

---

## Proposed Solution

Add a new **"Game State" tab** on the match page that shows relative game state using a 7-column layout with comparison indicators:

| Symbol | Meaning | Color |
|--------|---------|-------|
| `--` | Significantly behind | Red |
| `-` | Slightly behind | Orange |
| `=` | Roughly equal | Gray |
| `+` | Slightly ahead | Light green |
| `++` | Significantly ahead | Bright green |

This mirrors Old World's in-game "stronger/weaker, competent/developing" diplomacy display.

---

## Approved Layout: 7-Column

```
Turn | P1 Icons | P1 Orders | Mil Comp | Sci Comp | P2 Orders | P2 Icons
-----|----------|-----------|----------|----------|-----------|----------
 23  | [events] |    8      |    ++    |     +    |     6     | [events]
 24  | [events] |    8      |    +     |     =    |     7     | [events]
 25  | [events] |    9      |    -     |     =    |     8     | [events]
```

**Columns (left to right):**
1. **Turn #** - Turn number
2. **P1 Icons** - Player 1's events (condensed icon format)
3. **P1 Orders** - Player 1's orders per turn (actual number)
4. **Mil Comparison** - Military power relative comparison (from P1's perspective)
5. **Sci Comparison** - Science rate relative comparison (from P1's perspective)
6. **P2 Orders** - Player 2's orders per turn (actual number)
7. **P2 Icons** - Player 2's events (condensed icon format)

---

## Key Metrics (Approved)

1. **Military Power** - Direct measure of army strength
   - Data source: `player_military_history.military_power`
   - Available: Every turn for both players

2. **Orders** - Action economy / tempo
   - Data source: `player_yield_history` where `resource_type = 'YIELD_ORDERS'`
   - Available: Every turn (divide by 10 for display value)

3. **Science Rate** - Technology investment
   - Data source: `player_yield_history` where `resource_type = 'YIELD_SCIENCE'`
   - Available: Every turn (divide by 10 for display value)

### Future Consideration

- **City Count** - Economic/territorial advantage
- **Legitimacy** - Political stability (affects orders)

---

## Threshold Design (Approved: Percentage-Based)

All metrics use percentage-based thresholds:

```
Ratio = P1_value / P2_value

++  : ratio > 1.30  (30%+ ahead)
+   : ratio > 1.10  (10-30% ahead)
=   : 0.90 <= ratio <= 1.10  (within 10%)
-   : ratio < 0.90  (10-30% behind)
--  : ratio < 0.70  (30%+ behind)
```

---

## Data Availability

### Required Data

| Metric | Table | Field | Per-Turn? | Notes |
|--------|-------|-------|-----------|-------|
| Military Power | `player_military_history` | `military_power` | Yes | Raw value, no scaling needed |
| Orders | `player_yield_history` | `amount` | Yes | Filter `resource_type = 'YIELD_ORDERS'`, divide by 10 |
| Science | `player_yield_history` | `amount` | Yes | Filter `resource_type = 'YIELD_SCIENCE'`, divide by 10 |

### Query Approach

New query `get_match_turn_comparisons(match_id)` returns per-turn metrics with interpolation:

```sql
-- Generate all turns, join metrics, interpolate missing values
WITH all_turns AS (
    SELECT DISTINCT turn_number FROM player_military_history WHERE match_id = ?
),
military AS (
    SELECT turn_number, player_id, military_power
    FROM player_military_history WHERE match_id = ?
),
orders AS (
    SELECT turn_number, player_id, amount / 10.0 as orders
    FROM player_yield_history
    WHERE match_id = ? AND resource_type = 'YIELD_ORDERS'
),
science AS (
    SELECT turn_number, player_id, amount / 10.0 as science
    FROM player_yield_history
    WHERE match_id = ? AND resource_type = 'YIELD_SCIENCE'
)
SELECT
    t.turn_number,
    -- P1 metrics
    COALESCE(m1.military_power, LAG(m1.military_power) OVER (...)) as p1_military,
    COALESCE(o1.orders, LAG(o1.orders) OVER (...)) as p1_orders,
    COALESCE(s1.science, LAG(s1.science) OVER (...)) as p1_science,
    -- P2 metrics (same pattern)
    ...
FROM all_turns t
LEFT JOIN military m1 ON t.turn_number = m1.turn_number AND m1.player_id = ?
-- ... more joins
ORDER BY t.turn_number
```

---

## UI/UX Considerations

### Color Coding

The `--`, `-`, `=`, `+`, `++` indicators should be color-coded:

- `--` : `#ff6b6b` (red) - significantly behind
- `-`  : `#ffa94d` (orange) - slightly behind
- `=`  : `#868e96` (gray) - equal
- `+`  : `#69db7c` (light green) - slightly ahead
- `++` : `#40c057` (bright green) - significantly ahead

### Hover/Tooltip

On hover, show actual values:
> "Military: 450 vs 320 (+40%)"

### Responsive Behavior

- On narrow screens, consider collapsing to icons only
- The inner comparison columns should be narrower than event columns

### Accessibility

- Don't rely on color alone - the symbols (`++`, `+`, etc.) provide meaning
- Consider screen reader text: "Player 1 significantly ahead in military power"

---

## Decisions Made

| Question | Decision |
|----------|----------|
| Layout | 7-column (Option A) |
| Metrics | Military Power, Orders, Science Rate |
| Thresholds | Percentage-based for all metrics |
| Empty turns | Only show turns with events (matches timeline) |
| Early game | Only shown if events occur |
| Tech vs Science | Science rate (per-turn production) |

### Future Consideration

- VPs for later implementation (needs separate tracking)

---

## Implementation Phases

### Phase 1: Data Layer
- [ ] Create query `get_match_turn_comparisons(match_id)` returning per-turn metrics for both players
- [ ] Implement interpolation for missing turns (carry forward last value)
- [ ] Return raw values for display + computed comparison indicators

### Phase 2: Comparison Logic
- [ ] Implement percentage-based threshold calculations
- [ ] Return comparison indicators (`--`, `-`, `=`, `+`, `++`) per metric
- [ ] Handle edge cases (zero values, early game)

### Phase 3: UI Integration
- [ ] Add new "Game State" tab to match page
- [ ] Create 7-column table component with events + comparisons
- [ ] Add color coding and styling for indicators
- [ ] Add hover tooltips with actual values
- [ ] Reuse existing timeline event icons

### Phase 4: Testing
- [ ] Test with various matches (short games, long games, one-sided, close)
- [ ] Verify interpolation works correctly
- [ ] Get community feedback and adjust thresholds if needed

---

## Success Criteria

1. **At-a-glance understanding**: User can scroll to any turn and immediately know who's ahead
2. **Story telling**: User can trace the narrative of how leads changed over time
3. **Doesn't obscure events**: The comparison columns complement, not replace, the event timeline
4. **Performance**: Timeline still renders quickly for 100+ turn games

---

## Related Features

- **Icon Enhancement** (completed): Game icons now used in timeline
- **Drill-down charts**: Clicking on a comparison column could highlight that metric in the existing charts
- **Battle detection refinement**: Current 20% drop threshold may need tuning

---

## References

- Discord feedback thread (Dec 31, 2024)
- Current timeline implementation: `tournament_visualizer/components/timeline.py`
- Turn history queries: `tournament_visualizer/data/queries.py`
- Data tables: `player_military_history`, `player_yield_history`, `player_legitimacy_history`
