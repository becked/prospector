# Militia Unit Analysis: Built vs Converted

## Overview

In Old World, militia units can be created in two ways:
1. **Built** - Produced from cities like other military units
2. **Converted** - Created by converting worker units into militia

This document explains how to distinguish between these two sources using save file data.

## Methodology

### Data Sources

The save file XML contains:
- `<Unit Type="UNIT_MILITIA">` - Currently alive militia units
- `<UnitsProduced><UNIT_MILITIA>` - Cumulative count of militia built from cities (per player)

**Key insight**: `UnitsProduced` only tracks city-built units. Worker-to-militia conversions do NOT increment this counter.

### Conversion Detection Formula

```python
militia_conversions = max(0, militia_alive - militia_built)
```

Where:
- `militia_alive` = Count of active `<Unit Type="UNIT_MILITIA">` for the player
- `militia_built` = Value in `<UnitsProduced><UNIT_MILITIA>` (0 if absent)

### How It Works

Three scenarios:

1. **Positive difference** (`militia_alive > militia_built`):
   - Clear evidence of conversions
   - Example: Built=0, Alive=3 → **3 conversions** (exact)

2. **Zero difference** (`militia_alive == militia_built`):
   - No net conversions detected
   - Could mean: 0 conversions, OR conversions+deaths that cancel out
   - Example: Built=2, Alive=2 → **0 conversions** (conservative)

3. **Negative difference** (`militia_alive < militia_built`):
   - Militia died in combat
   - Cannot determine if conversions also occurred
   - Example: Built=6, Alive=3 → **0 conversions reported** (unknown actual)

## Accuracy and Limitations

### Tested Accuracy

Analysis of tournament save files (30 player-games):
- ✅ **86%** clear conversion data (positive difference)
- ⚠️ **14%** indeterminate (negative difference due to combat losses)

### Key Limitation

**The formula provides a minimum count.** When militia die in combat (negative difference), actual conversions could be higher than reported.

**Example of the problem:**
```
Built: 6 militia from cities
Converted: 2 workers to militia
Died: 5 militia in combat
Alive: 3 militia

Formula result: max(0, 3-6) = 0 conversions
Actual conversions: 2 (missed!)
```

### Why Alternative Approaches Don't Work

Investigation showed these data sources are **not available** in save files:
- ❌ Per-unit-type death counters (only aggregate `STAT_UNIT_LOST`)
- ❌ Historical CITY_PRODUCTION logs (only recent turn)
- ❌ Direct conversion tracking or events
- ❌ Individual unit death records

Workers can die in combat (non-rare), making worker deficit unreliable for inferring conversions.

## Handling Indeterminate Cases

For the 14% of cases with negative differences, three options exist:

### Option A: Report 0 (Conservative)

**Implementation:**
```python
conversions = max(0, alive - built)  # Always return a number
```

**Pros:**
- Simple to implement
- No false positives
- Provides lower bound estimate
- Works in all queries/aggregations

**Cons:**
- Underestimates when both conversions AND losses occurred
- Silent about data quality issue
- Could bias analysis toward non-combat scenarios

**Use when:** You need complete data coverage and prefer conservative estimates

---

### Option B: Flag as Unknown

**Implementation:**
```python
if alive >= built:
    conversions = alive - built
    confidence = "high"
elif alive == built:
    conversions = 0
    confidence = "medium"  # Could be hidden deaths+conversions
else:
    conversions = None  # or -1, or special sentinel
    confidence = "unknown"
```

**Pros:**
- Honest about data limitations
- Enables quality-aware analysis
- Users can filter/weight by confidence
- No misleading zeros

**Cons:**
- More complex to handle in queries
- Requires null/special value handling in database
- Users must decide how to treat unknowns

**Use when:** Data quality matters more than coverage

---

### Option C: Exclude from Dataset

**Implementation:**
```python
# Only process/store cases where alive >= built
if alive >= built:
    conversions = alive - built
    store_result(...)
# else: skip this player-game entirely
```

**Pros:**
- Clean dataset of only verified conversions
- Simple to explain: "detected conversions"
- No ambiguous values

**Cons:**
- Loses 14% of data points
- Could bias results (excludes combat-heavy games)
- Incomplete tournament coverage

**Use when:** You're specifically studying conversion strategies, not overall militia usage

---

### Recommendation

**Start with Option B** (flag as unknown) for maximum flexibility. Database schema:

```sql
militia_conversions INT,           -- NULL when indeterminate
militia_conversions_confidence TEXT -- 'high', 'medium', 'unknown'
```

This allows analysts to:
- Use conservative counts: `COALESCE(conversions, 0)`
- Study only verified cases: `WHERE confidence = 'high'`
- Analyze by confidence level

## Python Implementation

### Per-Player Analysis

```python
import xml.etree.ElementTree as ET

tree = ET.parse('save_file.xml')
root = tree.getroot()

for player_elem in root.findall('.//Player[@ID]'):
    player_id = int(player_elem.get('ID'))

    # Count alive militia for this player
    militia_alive = sum(1 for unit in root.findall('.//Unit[@Type="UNIT_MILITIA"]')
                        if unit.get('Player') == player_elem.get('ID'))

    # Get built count from UnitsProduced
    militia_built = 0
    units_prod = player_elem.find('.//UnitsProduced')
    if units_prod is not None:
        militia_elem = units_prod.find('UNIT_MILITIA')
        if militia_elem is not None:
            militia_built = int(militia_elem.text)

    # Calculate conversions with confidence
    diff = militia_alive - militia_built

    if diff > 0:
        conversions = diff
        confidence = "high"
    elif diff == 0:
        conversions = 0
        confidence = "medium"
    else:  # diff < 0
        conversions = None  # or 0 for conservative approach
        confidence = "unknown"

    print(f"Player {player_id + 1}:")  # Database uses 1-based IDs
    print(f"  Built: {militia_built}, Alive: {militia_alive}")
    print(f"  Conversions: {conversions}, Confidence: {confidence}")
```

### Conservative Approach (Option A)

```python
# Simple version that always returns a number
conversions = max(0, militia_alive - militia_built)
```

## Example Analysis

From tournament save `match_426504721_anarkos-becked.zip` (Persia vs Assyria, Year 69):

```xml
<!-- Player 0 (Anarkos) -->
<UnitsProduced>
  <UNIT_MILITIA>6</UNIT_MILITIA>
</UnitsProduced>
<!-- 3 militia alive -->

<!-- Player 1 (Becked) -->
<UnitsProduced>
  <!-- No UNIT_MILITIA entry -->
</UnitsProduced>
<!-- 3 militia alive -->
```

**Results:**

| Player | Built | Alive | Conversions | Confidence |
|--------|-------|-------|-------------|------------|
| Anarkos (P0) | 6 | 3 | 0 or Unknown | Low - combat losses |
| Becked (P1) | 0 | 3 | 3 | High - verified |

Player 1 (Becked) clearly converted 3 workers to militia. Player 0's conversions are indeterminate due to losses.

## Database Integration

### Recommended Schema Addition

```sql
-- Add to events table or create militia_analysis table
ALTER TABLE events ADD COLUMN militia_built INT;
ALTER TABLE events ADD COLUMN militia_alive INT;
ALTER TABLE events ADD COLUMN militia_converted INT;  -- NULL when unknown
ALTER TABLE events ADD COLUMN militia_conversion_confidence TEXT;
```

### Sample Query

```sql
-- Get average conversions (conservative, treating unknowns as 0)
SELECT
    player_id,
    AVG(COALESCE(militia_converted, 0)) as avg_conversions
FROM events
WHERE event_type = 'GAME_END'
GROUP BY player_id;

-- Get average conversions (high confidence only)
SELECT
    player_id,
    AVG(militia_converted) as avg_conversions
FROM events
WHERE event_type = 'GAME_END'
  AND militia_conversion_confidence = 'high'
GROUP BY player_id;
```

## Related Data

The save file also tracks:
- `STAT_UNIT_TRAINED` - Total units trained (all types combined)
- `STAT_UNIT_LOST` - Total units lost (all types combined, no per-unit breakdown)
- `UnitsProducedTurn` - Turn numbers when units were produced
- `CreateTurn` - Individual unit's creation turn (in `<Unit>` element)

### Unit Fields

Each militia unit contains:
- `Type` - Always "UNIT_MILITIA"
- `Player` - Current owner (0-based in XML, convert to 1-based for DB)
- `CreateTurn` - Turn when created
- `OriginalPlayer` - Original owner (for captured units)
- `Damage` - Current damage taken
- **No field distinguishing converted vs built militia**

## Notes

- `UnitsProduced` is a **cumulative lifetime counter**, not current count
- Worker-to-militia conversion does **not** increment `UnitsProduced`
- Workers can die in combat (non-rare), so worker deficit ≠ conversions
- Disbanded militia may still count in `UnitsProduced`
- This methodology works for any unit type, not just militia
- Player IDs in XML are 0-based; database uses 1-based (add 1 when importing)
