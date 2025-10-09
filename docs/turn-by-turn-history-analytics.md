# Turn-by-Turn History Analytics Examples

This document provides SQL query examples for analyzing turn-by-turn history data from Old World tournament matches.

## Table of Contents

- [Available History Tables](#available-history-tables)
- [Basic Queries](#basic-queries)
- [Player Performance Over Time](#player-performance-over-time)
- [Economic Analysis](#economic-analysis)
- [Military Analysis](#military-analysis)
- [Diplomatic Analysis](#diplomatic-analysis)
- [Comparative Analysis](#comparative-analysis)
- [Advanced Analytics](#advanced-analytics)

## Available History Tables

The database includes six turn-by-turn history tables:

| Table | Tracks | Granularity |
|-------|--------|-------------|
| `player_points_history` | Victory points | Per turn, per player |
| `player_yield_history` | Resource yields (14 types) | Per turn, per player, per resource |
| `player_military_history` | Military power | Per turn, per player |
| `player_legitimacy_history` | Legitimacy score | Per turn, per player |
| `family_opinion_history` | Family opinions | Per turn, per player, per family |
| `religion_opinion_history` | Religion opinions | Per turn, per player, per religion |

## Basic Queries

### Check Available Data

```sql
-- See how many matches have history data
SELECT COUNT(DISTINCT match_id) as match_count
FROM player_points_history;

-- Check turn coverage for a specific match
SELECT
    MIN(turn_number) as first_turn,
    MAX(turn_number) as last_turn,
    COUNT(DISTINCT turn_number) as turn_count
FROM player_points_history
WHERE match_id = 1;
```

### Get Player History for a Match

```sql
-- Get complete history for all players in a match
SELECT
    p.player_name,
    ph.turn_number,
    ph.points,
    mh.military_power,
    lh.legitimacy
FROM player_points_history ph
JOIN players p ON ph.player_id = p.player_id
JOIN player_military_history mh
    ON ph.match_id = mh.match_id
    AND ph.player_id = mh.player_id
    AND ph.turn_number = mh.turn_number
JOIN player_legitimacy_history lh
    ON ph.match_id = lh.match_id
    AND ph.player_id = lh.player_id
    AND ph.turn_number = lh.turn_number
WHERE ph.match_id = 1
ORDER BY ph.turn_number, p.player_name;
```

## Player Performance Over Time

### Victory Points Progression

```sql
-- Track victory points over time for all players in a match
SELECT
    p.player_name,
    ph.turn_number,
    ph.points,
    -- Calculate points gained since previous turn
    ph.points - LAG(ph.points) OVER (
        PARTITION BY ph.player_id
        ORDER BY ph.turn_number
    ) as points_gained
FROM player_points_history ph
JOIN players p ON ph.player_id = p.player_id
WHERE ph.match_id = 1
ORDER BY ph.turn_number, p.player_name;
```

### Identify Momentum Shifts

```sql
-- Find turns where a player overtook another in points
WITH ranked_turns AS (
    SELECT
        p.player_name,
        ph.turn_number,
        ph.points,
        RANK() OVER (
            PARTITION BY ph.turn_number
            ORDER BY ph.points DESC
        ) as rank_current,
        LAG(RANK() OVER (
            PARTITION BY ph.turn_number
            ORDER BY ph.points DESC
        )) OVER (
            PARTITION BY ph.player_id
            ORDER BY ph.turn_number
        ) as rank_previous
    FROM player_points_history ph
    JOIN players p ON ph.player_id = p.player_id
    WHERE ph.match_id = 1
)
SELECT *
FROM ranked_turns
WHERE rank_current != rank_previous
ORDER BY turn_number;
```

## Economic Analysis

### Resource Yields Over Time

```sql
-- Track economic yields (money, civics, science) over time
SELECT
    p.player_name,
    yh.turn_number,
    MAX(CASE WHEN yh.resource_type = 'YIELD_MONEY' THEN yh.amount END) as money,
    MAX(CASE WHEN yh.resource_type = 'YIELD_CIVICS' THEN yh.amount END) as civics,
    MAX(CASE WHEN yh.resource_type = 'YIELD_SCIENCE' THEN yh.amount END) as science
FROM player_yield_history yh
JOIN players p ON yh.player_id = p.player_id
WHERE yh.match_id = 1
  AND yh.resource_type IN ('YIELD_MONEY', 'YIELD_CIVICS', 'YIELD_SCIENCE')
GROUP BY p.player_name, yh.turn_number
ORDER BY yh.turn_number, p.player_name;
```

### Economic Efficiency

```sql
-- Calculate average yields per turn for each player
SELECT
    p.player_name,
    yh.resource_type,
    ROUND(AVG(yh.amount), 2) as avg_yield,
    MIN(yh.amount) as min_yield,
    MAX(yh.amount) as max_yield
FROM player_yield_history yh
JOIN players p ON yh.player_id = p.player_id
WHERE yh.match_id = 1
GROUP BY p.player_name, yh.resource_type
ORDER BY p.player_name, yh.resource_type;
```

### Identify Economic Crises

```sql
-- Find turns where players had negative yields
SELECT
    p.player_name,
    yh.turn_number,
    yh.resource_type,
    yh.amount
FROM player_yield_history yh
JOIN players p ON yh.player_id = p.player_id
WHERE yh.match_id = 1
  AND yh.amount < 0
ORDER BY yh.turn_number, p.player_name, yh.resource_type;
```

## Military Analysis

### Military Power Growth

```sql
-- Track military power growth over time
SELECT
    p.player_name,
    mh.turn_number,
    mh.military_power,
    -- Calculate growth rate
    ROUND((mh.military_power - LAG(mh.military_power) OVER (
        PARTITION BY mh.player_id
        ORDER BY mh.turn_number
    )) * 100.0 / NULLIF(LAG(mh.military_power) OVER (
        PARTITION BY mh.player_id
        ORDER BY mh.turn_number
    ), 0), 2) as growth_rate_pct
FROM player_military_history mh
JOIN players p ON mh.player_id = p.player_id
WHERE mh.match_id = 1
ORDER BY mh.turn_number, p.player_name;
```

### Military Advantages

```sql
-- Calculate military advantage/disadvantage between players at each turn
WITH military_by_turn AS (
    SELECT
        mh.turn_number,
        mh.player_id,
        p.player_name,
        mh.military_power,
        AVG(mh.military_power) OVER (
            PARTITION BY mh.turn_number
        ) as avg_military
    FROM player_military_history mh
    JOIN players p ON mh.player_id = p.player_id
    WHERE mh.match_id = 1
)
SELECT
    turn_number,
    player_name,
    military_power,
    ROUND(avg_military, 2) as avg_opponent_military,
    ROUND(military_power - avg_military, 2) as military_advantage
FROM military_by_turn
ORDER BY turn_number, player_name;
```

## Diplomatic Analysis

### Family Opinion Trends

```sql
-- Track family opinion changes over time
SELECT
    p.player_name,
    fh.family_name,
    fh.turn_number,
    fh.opinion,
    fh.opinion - LAG(fh.opinion) OVER (
        PARTITION BY fh.player_id, fh.family_name
        ORDER BY fh.turn_number
    ) as opinion_change
FROM family_opinion_history fh
JOIN players p ON fh.player_id = p.player_id
WHERE fh.match_id = 1
  AND fh.family_name = 'FAMILY_ARGEAD'  -- Example: Argead family
ORDER BY fh.turn_number, p.player_name;
```

### Identify Diplomatic Crises

```sql
-- Find turns where family opinion dropped significantly
WITH opinion_changes AS (
    SELECT
        p.player_name,
        fh.family_name,
        fh.turn_number,
        fh.opinion,
        fh.opinion - LAG(fh.opinion) OVER (
            PARTITION BY fh.player_id, fh.family_name
            ORDER BY fh.turn_number
        ) as opinion_change
    FROM family_opinion_history fh
    JOIN players p ON fh.player_id = p.player_id
    WHERE fh.match_id = 1
)
SELECT *
FROM opinion_changes
WHERE opinion_change < -50  -- Significant opinion drop
ORDER BY opinion_change ASC;
```

### Average Family Support

```sql
-- Calculate average family opinion for each player
SELECT
    p.player_name,
    fh.turn_number,
    ROUND(AVG(fh.opinion), 2) as avg_family_opinion,
    COUNT(CASE WHEN fh.opinion > 0 THEN 1 END) as families_positive,
    COUNT(CASE WHEN fh.opinion < 0 THEN 1 END) as families_negative
FROM family_opinion_history fh
JOIN players p ON fh.player_id = p.player_id
WHERE fh.match_id = 1
GROUP BY p.player_name, fh.turn_number
ORDER BY fh.turn_number, p.player_name;
```

## Comparative Analysis

### Head-to-Head Player Comparison

```sql
-- Compare two players across all metrics over time
SELECT
    ph1.turn_number,
    p1.player_name as player1,
    ph1.points as player1_points,
    mh1.military_power as player1_military,
    lh1.legitimacy as player1_legitimacy,
    p2.player_name as player2,
    ph2.points as player2_points,
    mh2.military_power as player2_military,
    lh2.legitimacy as player2_legitimacy
FROM player_points_history ph1
JOIN players p1 ON ph1.player_id = p1.player_id
JOIN player_military_history mh1
    ON ph1.match_id = mh1.match_id
    AND ph1.player_id = mh1.player_id
    AND ph1.turn_number = mh1.turn_number
JOIN player_legitimacy_history lh1
    ON ph1.match_id = lh1.match_id
    AND ph1.player_id = lh1.player_id
    AND ph1.turn_number = lh1.turn_number
JOIN player_points_history ph2
    ON ph1.match_id = ph2.match_id
    AND ph1.turn_number = ph2.turn_number
JOIN players p2 ON ph2.player_id = p2.player_id
JOIN player_military_history mh2
    ON ph2.match_id = mh2.match_id
    AND ph2.player_id = mh2.player_id
    AND ph2.turn_number = mh2.turn_number
JOIN player_legitimacy_history lh2
    ON ph2.match_id = lh2.match_id
    AND ph2.player_id = lh2.player_id
    AND ph2.turn_number = lh2.turn_number
WHERE ph1.match_id = 1
  AND p1.player_name = 'yagman'
  AND p2.player_name = 'Marauder'
ORDER BY ph1.turn_number;
```

### Match Statistics Summary

```sql
-- Generate comprehensive match statistics
SELECT
    m.match_id,
    m.game_name,
    m.total_turns,
    w.player_name as winner,
    -- Points statistics
    (SELECT ROUND(AVG(points), 2)
     FROM player_points_history
     WHERE match_id = m.match_id) as avg_points,
    (SELECT MAX(points)
     FROM player_points_history
     WHERE match_id = m.match_id) as max_points,
    -- Military statistics
    (SELECT ROUND(AVG(military_power), 2)
     FROM player_military_history
     WHERE match_id = m.match_id) as avg_military,
    (SELECT MAX(military_power)
     FROM player_military_history
     WHERE match_id = m.match_id) as max_military,
    -- Economic statistics
    (SELECT COUNT(*)
     FROM player_yield_history
     WHERE match_id = m.match_id
     AND amount < 0) as negative_yield_occurrences
FROM matches m
LEFT JOIN match_winners mw ON m.match_id = mw.match_id
LEFT JOIN players w ON mw.winner_player_id = w.player_id
WHERE m.match_id = 1;
```

## Advanced Analytics

### Calculate "Power Score"

```sql
-- Create composite power score from multiple metrics
SELECT
    p.player_name,
    ph.turn_number,
    ph.points,
    mh.military_power,
    lh.legitimacy,
    -- Composite power score (weighted average)
    ROUND(
        (ph.points * 10.0 +
         mh.military_power * 0.1 +
         lh.legitimacy * 0.5), 2
    ) as power_score
FROM player_points_history ph
JOIN players p ON ph.player_id = p.player_id
JOIN player_military_history mh
    ON ph.match_id = mh.match_id
    AND ph.player_id = mh.player_id
    AND ph.turn_number = mh.turn_number
JOIN player_legitimacy_history lh
    ON ph.match_id = lh.match_id
    AND ph.player_id = lh.player_id
    AND ph.turn_number = lh.turn_number
WHERE ph.match_id = 1
ORDER BY ph.turn_number, power_score DESC;
```

### Predict Match Outcome

```sql
-- Analyze early game metrics to see if they correlate with final outcome
WITH early_game AS (
    SELECT
        ph.player_id,
        p.player_name,
        AVG(ph.points) as avg_early_points,
        AVG(mh.military_power) as avg_early_military,
        AVG(lh.legitimacy) as avg_early_legitimacy
    FROM player_points_history ph
    JOIN players p ON ph.player_id = p.player_id
    JOIN player_military_history mh
        ON ph.match_id = mh.match_id
        AND ph.player_id = mh.player_id
        AND ph.turn_number = mh.turn_number
    JOIN player_legitimacy_history lh
        ON ph.match_id = lh.match_id
        AND ph.player_id = lh.player_id
        AND ph.turn_number = lh.turn_number
    WHERE ph.match_id = 1
      AND ph.turn_number <= 20  -- First 20 turns
    GROUP BY ph.player_id, p.player_name
)
SELECT
    eg.*,
    CASE WHEN mw.winner_player_id = eg.player_id THEN 'Winner' ELSE 'Loser' END as outcome
FROM early_game eg
JOIN matches m ON TRUE
LEFT JOIN match_winners mw ON m.match_id = mw.match_id
WHERE m.match_id = 1
ORDER BY avg_early_points DESC;
```

### Resource Bottleneck Analysis

```sql
-- Identify which resources were most often negative (bottlenecks)
SELECT
    p.player_name,
    yh.resource_type,
    COUNT(*) as times_negative,
    ROUND(AVG(yh.amount), 2) as avg_when_negative,
    MIN(yh.amount) as most_negative
FROM player_yield_history yh
JOIN players p ON yh.player_id = p.player_id
WHERE yh.match_id = 1
  AND yh.amount < 0
GROUP BY p.player_name, yh.resource_type
ORDER BY p.player_name, times_negative DESC;
```

### Turning Point Analysis

```sql
-- Find critical turns where the game momentum shifted
WITH point_differences AS (
    SELECT
        ph1.turn_number,
        ABS(ph1.points - ph2.points) as point_diff
    FROM player_points_history ph1
    JOIN player_points_history ph2
        ON ph1.match_id = ph2.match_id
        AND ph1.turn_number = ph2.turn_number
        AND ph1.player_id != ph2.player_id
    WHERE ph1.match_id = 1
),
diff_changes AS (
    SELECT
        turn_number,
        point_diff,
        point_diff - LAG(point_diff) OVER (ORDER BY turn_number) as diff_change
    FROM point_differences
)
SELECT
    turn_number,
    point_diff,
    diff_change,
    -- Events that happened on this turn
    (SELECT COUNT(*) FROM events WHERE match_id = 1 AND turn_number = dc.turn_number) as events_count
FROM diff_changes dc
WHERE ABS(diff_change) > 5  -- Significant momentum shift
ORDER BY ABS(diff_change) DESC
LIMIT 10;
```

## Using in Python

Example Python code to query history data:

```python
import duckdb

# Connect to database
conn = duckdb.connect('tournament_data.duckdb', read_only=True)

# Query player progression
query = """
SELECT
    p.player_name,
    ph.turn_number,
    ph.points
FROM player_points_history ph
JOIN players p ON ph.player_id = p.player_id
WHERE ph.match_id = ?
ORDER BY ph.turn_number, p.player_name
"""

result = conn.execute(query, [1]).fetchdf()

# Now you can use pandas for visualization
import matplotlib.pyplot as plt

for player in result['player_name'].unique():
    player_data = result[result['player_name'] == player]
    plt.plot(player_data['turn_number'], player_data['points'], label=player)

plt.xlabel('Turn Number')
plt.ylabel('Victory Points')
plt.title('Victory Points Over Time')
plt.legend()
plt.show()
```

## Tips

1. **Performance**: Add `match_id` to your WHERE clause to improve query performance
2. **Null Handling**: Use `NULLIF()` to avoid division by zero in calculations
3. **Window Functions**: Use `LAG()` and `LEAD()` to compare turn-by-turn changes
4. **Aggregations**: Use `PARTITION BY` with window functions to analyze per-player
5. **Joins**: Always join history tables on `(match_id, player_id, turn_number)` for consistency

## Related Documentation

- [Turn-by-Turn History Implementation Plan](../docs/plans/turn-by-turn-history-implementation-plan.md)
- [Database Schema](../docs/database-schema.md)
- [Developer Guide](../docs/developer-guide.md)
