# Yield Display Scale Issue - Investigation Report

**Date:** 2025-10-24
**Investigator:** Claude Code
**Status:** Issue Confirmed

## Executive Summary

All yield-related values (science, civics, culture, etc.) displayed in the application are **10x too high** due to the game's internal storage format. Old World stores yields in units of 0.1 internally, requiring division by 10 for correct display to users.

**Impact:** HIGH - All yield visualizations show incorrect values
**Severity:** Data Display Issue (data is intact, only display is incorrect)

## Background

During investigation of science per turn data, we discovered that Old World uses a specific storage convention:

> "Yield numbers should be divided by 10 for display. The game internally stores stockpiles, and yield rate history, in units of 0.1"
> — Old World Developer

This means:
- XML value of `215` should display as `21.5 science/turn`
- XML value of `2500` should display as `250.0 stone`

## Investigation Findings

### 1. Database Schema

The `player_yield_history` table stores yield production rates:

```sql
┌───────────────┬─────────────┐
│  column_name  │ column_type │
├───────────────┼─────────────┤
│ resource_id   │ BIGINT      │
│ match_id      │ BIGINT      │
│ player_id     │ BIGINT      │
│ turn_number   │ INTEGER     │
│ resource_type │ VARCHAR     │
│ amount        │ INTEGER     │  -- Stores RAW values (not divided by 10)
└───────────────┴─────────────┘
```

**Sample Data:**
```
turn 2: 215 (should display as 21.5)
turn 30: 399 (should display as 39.9)
turn 57: 707 (should display as 70.7)
```

The `player_statistics` table stores yield stockpiles with same issue:

```
YIELD_CIVICS: 2284 (should display as 228.4)
YIELD_TRAINING: 13563 (should display as 1356.3)
```

### 2. Parser Code

**File:** `tournament_visualizer/data/parser.py`

**YieldRateHistory Parsing** (lines 1325-1399):
```python
def extract_yield_history(self) -> List[Dict[str, Any]]:
    # ...
    amount = self._safe_int(turn_elem.text)  # Line 1385
    # ...
    yield_data.append({
        "amount": amount,  # Line 1395 - Raw value stored as-is
    })
```

**YieldStockpile Parsing** (lines 798-812):
```python
yield_stockpile = player_elem.find(".//YieldStockpile")
if yield_stockpile is not None:
    for yield_elem in yield_stockpile:
        value = self._safe_int(yield_elem.text, 0)  # Line 803
        statistics.append({
            "value": value,  # Line 810 - Raw value stored as-is
        })
```

**Finding:** Parser stores raw XML values without transformation.

### 3. Query Code

**File:** `tournament_visualizer/data/queries.py`

**Yield History Query** (lines 1608-1631):
```python
def get_yield_history_by_match(self, match_id: int, ...):
    base_query = """
    SELECT
        yh.amount  -- Line 1615 - Raw value returned
    FROM player_yield_history yh
    ...
    """
```

**Finding:** Queries return raw values without division by 10.

### 4. Visualization Code

**File:** `tournament_visualizer/components/charts.py`

**Yield Chart Creation** (lines 2363-2448):
```python
def create_yield_chart(df: pd.DataFrame, ...):
    # ...
    yields = player_data["amount"].tolist()  # Line 2415 - Raw values

    hover_texts = [
        f"Turn {turn}: {yield_val} {display_name.lower()}"  # Line 2419
        # Shows raw value like "215" instead of "21.5"
        for turn, yield_val in zip(turns, yields)
    ]
```

**File:** `tournament_visualizer/pages/matches.py`

**Chart Display** (lines 1350-1361):
```python
for yield_type, display_name in YIELD_TYPES:
    df_yield = all_yields_df[all_yields_df["resource_type"] == yield_type]
    chart = create_yield_chart(
        df_yield,  # Contains raw "amount" values
        # No transformation applied
    )
```

**Finding:** Charts display raw values directly to users.

### 5. Affected Yield Types

All 14 yield types tracked in Old World are affected:

1. `YIELD_FOOD` - Food production
2. `YIELD_GROWTH` - Population growth
3. `YIELD_SCIENCE` - Science/research ⚠️
4. `YIELD_CULTURE` - Culture points
5. `YIELD_CIVICS` - Civics points
6. `YIELD_TRAINING` - Military training
7. `YIELD_MONEY` - Gold/treasury
8. `YIELD_ORDERS` - Orders (actions)
9. `YIELD_IRON` - Iron resource
10. `YIELD_STONE` - Stone resource
11. `YIELD_WOOD` - Wood resource
12. `YIELD_HAPPINESS` - Happiness/contentment
13. `YIELD_DISCONTENT` - Discontent/unhappiness
14. `YIELD_MAINTENANCE` - Maintenance costs

### 6. Verification

**Expected vs. Actual Values:**

| Turn | Expected Science/Turn | Actual Display | Status |
|------|----------------------|----------------|--------|
| 2-8  | 20.5-21.5           | 205-215        | ❌ 10x too high |
| 30   | 25-40               | 250-400        | ❌ 10x too high |
| 50+  | 50-70               | 500-700        | ❌ 10x too high |

**Database Verification:**
```sql
-- Raw values in database
SELECT turn_number, amount
FROM player_yield_history
WHERE resource_type = 'YIELD_SCIENCE'
  AND match_id = 1
  AND player_id = 1
LIMIT 5;

-- Results:
turn 2: 215  (should display: 21.5)
turn 3: 215  (should display: 21.5)
turn 7: 234  (should display: 23.4)
```

## Impact Analysis

### User-Facing Impact

**HIGH** - All yield visualizations show incorrect values:

1. **Match Detail Page** - 14 yield charts (Food, Science, Culture, etc.)
   - Each chart shows values 10x too high
   - Hover tooltips show incorrect numbers
   - Y-axis scales are 10x inflated

2. **Statistics Display** - Yield stockpile values
   - End-game resource amounts shown incorrectly

3. **Analytics** - Any analysis based on yield data
   - Comparisons still valid (ratios preserved)
   - Absolute numbers misleading

### Data Integrity Impact

**NONE** - Data is correctly stored:
- Database contains accurate raw values from save files
- All historical data preserved
- Queries and aggregations work correctly
- Only the **display layer** is affected

### User Experience Impact

**MEDIUM** - Confusing but not breaking:
- Users familiar with Old World will notice incorrect scale
- Charts still show relative trends correctly
- Comparisons between players still valid
- Tournament analysis conclusions still sound

## Root Cause

The issue stems from a **missing display transformation**:

1. **Old World Game Design:** Stores yields in units of 0.1 for precision
2. **Our Parser:** Correctly extracts raw values from XML
3. **Our Database:** Correctly stores raw values
4. **Missing Step:** No division by 10 in visualization layer

## Recommendations

### Option 1: Transform in Database (Recommended)

**Approach:** Store display-ready values in database

**Pros:**
- Single source of truth for display values
- Queries return correct values automatically
- Simplest for chart/UI code
- No risk of inconsistent divisions

**Cons:**
- Requires database migration
- Must re-import all data
- Loses precision (decimal values or must use FLOAT)

**Implementation:**
```python
# In parser.py extract_yield_history()
amount = self._safe_int(turn_elem.text)
display_amount = amount / 10.0  # Convert to display value

yield_data.append({
    "amount": display_amount,  # Store display-ready value
})
```

**Migration:**
```sql
-- Option 1a: Use DECIMAL for precision
ALTER TABLE player_yield_history
  ALTER COLUMN amount TYPE DECIMAL(10, 1);

UPDATE player_yield_history
  SET amount = amount / 10.0;

-- Option 1b: Keep INTEGER, accept rounding
UPDATE player_yield_history
  SET amount = CAST(amount / 10.0 AS INTEGER);
-- Note: Loses decimal precision (21.5 → 21)
```

### Option 2: Transform in Queries

**Approach:** Divide by 10 in SQL queries

**Pros:**
- Preserves raw data in database
- No migration needed
- Can still access raw values if needed

**Cons:**
- Must remember to divide in every query
- Risk of inconsistency
- More complex query code

**Implementation:**
```python
# In queries.py
def get_yield_history_by_match(self, ...):
    base_query = """
    SELECT
        yh.amount / 10.0 as amount,  -- Transform in query
    FROM player_yield_history yh
    ...
    """
```

### Option 3: Transform in Visualization

**Approach:** Divide by 10 in chart creation code

**Pros:**
- Preserves raw data throughout
- No database changes
- No query changes

**Cons:**
- Must transform in multiple places
- Highest risk of inconsistency
- Couples display logic to raw values

**Implementation:**
```python
# In charts.py create_yield_chart()
yields = player_data["amount"].tolist()
yields = [y / 10.0 for y in yields]  # Transform for display

hover_texts = [
    f"Turn {turn}: {yield_val:.1f} {display_name.lower()}"
    for turn, yield_val in zip(turns, yields)
]
```

### Recommended Approach

**Option 1a: Transform in Database using DECIMAL**

**Rationale:**
1. **Correctness:** Display values from single source of truth
2. **Simplicity:** Chart code just displays what it gets
3. **Maintainability:** No risk of forgetting to divide
4. **Precision:** DECIMAL(10,1) preserves one decimal place (21.5)
5. **Consistency:** Matches how users think about yields

**Implementation Plan:**

1. **Create Migration Script** (`scripts/migrations/XXX_fix_yield_scale.py`):
   ```python
   def upgrade(conn):
       # Convert amount column to DECIMAL
       conn.execute("""
           ALTER TABLE player_yield_history
           ALTER COLUMN amount TYPE DECIMAL(10, 1)
       """)

       # Divide all existing values by 10
       conn.execute("""
           UPDATE player_yield_history
           SET amount = amount / 10.0
       """)

       # Same for player_statistics yield stockpile values
       conn.execute("""
           UPDATE player_statistics
           SET value = value / 10.0
           WHERE stat_category = 'yield_stockpile'
       """)
   ```

2. **Update Parser** (`tournament_visualizer/data/parser.py`):
   ```python
   # In extract_yield_history()
   amount = self._safe_int(turn_elem.text)
   display_amount = amount / 10.0  # Line 1385

   yield_data.append({
       "amount": display_amount,  # Store display value
   })

   # In extract_player_statistics()
   value = self._safe_int(yield_elem.text, 0)
   display_value = value / 10.0  # Line 803
   ```

3. **Update Chart Formatting** (`tournament_visualizer/components/charts.py`):
   ```python
   # Format as decimal in hover text
   f"Turn {turn}: {yield_val:.1f} {display_name.lower()}"
   # Shows "21.5" instead of "21.5000" or "21"
   ```

4. **Testing:**
   - Verify values after migration match expected ranges
   - Check all 14 yield type charts display correctly
   - Validate hover tooltips show proper decimals
   - Test stockpile displays

## Documentation Updates Needed

### CLAUDE.md

Add section under "Old World Save File Structure":

```markdown
### Yield Value Display Scale

**CRITICAL:** Old World stores all yield values in units of 0.1 internally.

**Storage Convention:**
- XML values must be **divided by 10** for display to users
- Examples:
  - XML: `<YIELD_SCIENCE>215</YIELD_SCIENCE>` → Display: `21.5 science/turn`
  - XML: `<YIELD_CIVICS>2500</YIELD_CIVICS>` → Display: `250.0 civics`

**Affected Data:**
- `YieldRateHistory` - Turn-by-turn yield production rates
- `YieldStockpile` - Current resource stockpiles
- All 14 yield types (SCIENCE, CIVICS, TRAINING, etc.)

**Implementation:**
- Parser divides by 10 during extraction
- Database stores display-ready values as DECIMAL(10,1)
- Charts display values directly without transformation

**Reference:** Old World game developer documentation
```

### docs/reference/save-file-format.md

Update yield sections to note the scale:

```markdown
#### YieldRateHistory - Production rates per turn

**IMPORTANT:** All yield values are stored in units of 0.1 and must be divided by 10 for display.

Example:
```xml
<YIELD_SCIENCE>
  <T2>215</T2>  <!-- Display as 21.5 science/turn -->
  <T3>234</T3>  <!-- Display as 23.4 science/turn -->
</YIELD_SCIENCE>
```
```

## Testing Checklist

After implementing fix:

- [ ] Database migration runs successfully
- [ ] All yield values reduced by factor of 10
- [ ] Science chart shows ~20-30 in early game (not 200-300)
- [ ] Hover tooltips show decimal values (21.5, not 215)
- [ ] All 14 yield type charts display correctly
- [ ] Stockpile values show proper scale
- [ ] No queries return 10x values
- [ ] Documentation updated in CLAUDE.md
- [ ] Save file format docs updated

## Related Files

**Parser:**
- `tournament_visualizer/data/parser.py:1325-1399` (extract_yield_history)
- `tournament_visualizer/data/parser.py:798-812` (extract YieldStockpile)

**Database:**
- `tournament_visualizer/data/database.py` (schema)
- `scripts/migrations/002_add_history_tables.py` (original migration)

**Queries:**
- `tournament_visualizer/data/queries.py:1590-1631` (get_yield_history_by_match)

**Visualization:**
- `tournament_visualizer/components/charts.py:2363-2448` (create_yield_chart)
- `tournament_visualizer/pages/matches.py:45-56` (YIELD_TYPES list)
- `tournament_visualizer/pages/matches.py:1350-1361` (chart creation)

**Documentation:**
- `docs/reference/save-file-format.md`
- `CLAUDE.md`

## Implementation Guide: Transform in Queries (RECOMMENDED APPROACH)

After further analysis, **transforming in queries** is the recommended approach over storing display values in the database.

### Rationale for Query Transformation

**Pros:**
- ✅ Database preserves exact XML values (data fidelity)
- ✅ Easier to validate parser correctness (DB == XML)
- ✅ Flexible - can change display rules without migration
- ✅ Simple parser - no game logic knowledge needed
- ✅ Can access both raw and display values

**Cons:**
- ❌ Must remember to transform in every query
- ❌ Slightly more complex queries
- ❌ Risk of forgetting transformation in new code

### Critical Implementation Details

#### 1. **Affected Tables**

Two tables store raw yield values that need transformation:

```sql
-- Turn-by-turn yield production rates
SELECT resource_type, amount FROM player_yield_history;
-- amount is RAW (215 = 21.5 displayed)

-- End-game yield stockpiles
SELECT stat_name, value FROM player_statistics
WHERE stat_category = 'yield_stockpile';
-- value is RAW (2500 = 250.0 displayed)
```

#### 2. **Query Pattern**

**Standard transformation:**
```python
def get_yield_history_by_match(self, match_id: int, ...):
    query = """
    SELECT
        yh.player_id,
        p.player_name,
        yh.turn_number,
        yh.resource_type,
        yh.amount / 10.0 AS amount  -- Transform here!
    FROM player_yield_history yh
    JOIN players p ON yh.player_id = p.player_id
    WHERE yh.match_id = ?
    ORDER BY yh.turn_number, yh.player_id
    """
```

**Important:** Use `/ 10.0` (not `/ 10`) to ensure float division:
```sql
-- WRONG: Integer division in some SQL dialects
amount / 10    -- 215 / 10 = 21 (truncated!)

-- CORRECT: Float division
amount / 10.0  -- 215 / 10.0 = 21.5
```

#### 3. **All Locations Requiring Changes**

**File: `tournament_visualizer/data/queries.py`**

```python
# Line ~1615: get_yield_history_by_match
yh.amount / 10.0 AS amount  # ADD THIS

# NEW HELPER METHOD: Get yield stockpile values
def get_yield_stockpiles(self, match_id: int):
    """Get end-game yield stockpile values (display format)."""
    query = """
    SELECT
        ps.player_id,
        p.player_name,
        ps.stat_name,
        ps.value / 10.0 AS value  -- ADD THIS
    FROM player_statistics ps
    JOIN players p ON ps.player_id = p.player_id
    WHERE ps.match_id = ?
      AND ps.stat_category = 'yield_stockpile'
    """
```

**Other files using yield data:**
- `tournament_visualizer/components/charts.py` - No changes (uses query results)
- `tournament_visualizer/pages/matches.py` - No changes (uses charts)

#### 4. **Chart Display Format**

Update hover text to show one decimal place:

```python
# File: tournament_visualizer/components/charts.py
# Line ~2419

# BEFORE:
f"Turn {turn}: {yield_val} {display_name.lower()}"

# AFTER:
f"Turn {turn}: {yield_val:.1f} {display_name.lower()}"
# Shows "21.5" instead of "21.5000000"
```

#### 5. **Code Review Checklist**

When reviewing yield-related code, verify:

- [ ] All queries on `player_yield_history` use `amount / 10.0`
- [ ] All queries on `player_statistics` (yield_stockpile) use `value / 10.0`
- [ ] Float formatting uses `.1f` for one decimal place
- [ ] No direct table queries without transformation
- [ ] Comments explain the /10 transformation

#### 6. **Common Pitfalls to Avoid**

**❌ Pitfall 1: Forgetting transformation**
```python
# WRONG - Raw values
df = conn.execute("""
    SELECT amount FROM player_yield_history
""").df()
# Returns 215 instead of 21.5!

# CORRECT
df = conn.execute("""
    SELECT amount / 10.0 AS amount FROM player_yield_history
""").df()
```

**❌ Pitfall 2: Integer division**
```sql
-- WRONG in some SQL dialects (PostgreSQL in integer mode)
amount / 10    -- 215 / 10 = 21

-- CORRECT
amount / 10.0  -- 215 / 10.0 = 21.5
```

**❌ Pitfall 3: Transforming twice**
```python
# WRONG - Query already transformed
df = queries.get_yield_history_by_match(match_id)
df['amount'] = df['amount'] / 10.0  # Now it's 2.15!

# CORRECT - Query handles transformation
df = queries.get_yield_history_by_match(match_id)
# Use df['amount'] directly
```

**❌ Pitfall 4: Inconsistent decimal formatting**
```python
# INCONSISTENT - Sometimes shows 21.5, sometimes 21.500000
f"Science: {value}"  # 21.5 or 21.500000 depending on value

# CONSISTENT
f"Science: {value:.1f}"  # Always 21.5
```

#### 7. **Testing Strategy**

**Unit Tests:**
```python
def test_yield_history_displays_correct_scale():
    """Verify yield values are divided by 10."""
    # Raw XML has: <YIELD_SCIENCE>215</YIELD_SCIENCE>
    df = queries.get_yield_history_by_match(match_id=1)

    science = df[df['resource_type'] == 'YIELD_SCIENCE']['amount'].iloc[0]

    # Should be display value, not raw
    assert science == 21.5, f"Expected 21.5, got {science}"
    assert science != 215, "Value should be divided by 10!"
```

**Integration Tests:**
```python
def test_charts_show_correct_scale():
    """Verify charts display reasonable values."""
    fig = create_yield_chart(df, yield_type="YIELD_SCIENCE")

    # Early game science should be 10-30, not 100-300
    y_values = fig.data[0].y
    early_game_avg = sum(y_values[:5]) / 5

    assert 10 <= early_game_avg <= 50, \
        f"Early game science {early_game_avg} out of expected range"
```

**Visual Regression:**
```python
# Before fix: Science chart shows 200-700 range
# After fix: Science chart shows 20-70 range

# Check Y-axis range
assert max(y_values) < 100, "Science values still 10x too high!"
```

#### 8. **Documentation Requirements**

**Code Comments:**
```python
def get_yield_history_by_match(self, match_id: int, ...):
    """Get yield production progression for all players in a match.

    NOTE: Old World stores yields in units of 0.1 internally.
    This query divides by 10 to return display-ready values.

    Example: XML value of 215 returns as 21.5 science/turn

    See: docs/reports/yield-display-scale-issue.md
    """
```

**Query Comments:**
```sql
SELECT
    yh.resource_type,
    yh.amount / 10.0 AS amount  -- Old World stores in 0.1 units
FROM player_yield_history yh
```

#### 9. **Future Maintenance**

**New Queries Checklist:**

When adding new queries that touch yield data:

1. Check if table contains yield values (`player_yield_history`, `player_statistics`)
2. Apply `/10.0` transformation to amount/value columns
3. Add comment explaining transformation
4. Test with known values (215 → 21.5)
5. Verify chart/display shows reasonable ranges

**Developer Onboarding:**

Add to developer documentation:

> **IMPORTANT:** Yield values are stored as raw integers from XML.
> All display queries must divide by 10.0 to show correct values.
> See CLAUDE.md "Yield Value Display Scale" section.

#### 10. **Performance Considerations**

**Query Performance:**
- Division by constant (10.0) is negligible performance impact
- Modern databases optimize this well
- No indexing changes needed

**Aggregation Queries:**
```sql
-- Aggregations work correctly with transformation
SELECT
    AVG(amount / 10.0) AS avg_science,  -- Correct
    MAX(amount / 10.0) AS max_science   -- Correct
FROM player_yield_history
WHERE resource_type = 'YIELD_SCIENCE'
```

**Computed Columns (Optional Optimization):**

If performance becomes an issue (unlikely):
```sql
-- Add computed column (DuckDB syntax)
ALTER TABLE player_yield_history
ADD COLUMN amount_display AS (amount / 10.0);

-- Then queries can use it directly
SELECT amount_display FROM player_yield_history;
```

#### 11. **Verification After Implementation**

**Step-by-step verification:**

```bash
# 1. Check sample raw values (should be 200-700 range)
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT turn_number, amount
FROM player_yield_history
WHERE resource_type = 'YIELD_SCIENCE'
  AND match_id = 1
  AND player_id = 1
LIMIT 5
"

# 2. Check transformed values via query (should be 20-70 range)
# Run this after implementing the fix in queries.py
uv run python -c "
from tournament_visualizer.data.queries import get_queries
df = get_queries().get_yield_history_by_match(1, ['YIELD_SCIENCE'])
print(df[['turn_number', 'amount']].head())
"

# 3. View chart in browser
uv run python manage.py restart
# Navigate to match detail page, check Science chart Y-axis
# Should show 20-70 range, not 200-700

# 4. Verify hover tooltips
# Hover over data points - should show "21.5", not "215"
```

**Expected Results:**

| Check | Before Fix | After Fix | Status |
|-------|-----------|-----------|--------|
| Raw DB values | 215 | 215 | ✅ Unchanged |
| Query results | 215 | 21.5 | ✅ Transformed |
| Chart Y-axis | 0-700 | 0-70 | ✅ Correct scale |
| Hover text | "215" | "21.5" | ✅ With decimal |

### Migration Plan: None Required!

**Advantage of query transformation:** No database migration needed!

- ✅ Existing data stays unchanged
- ✅ No downtime required
- ✅ No risk of data corruption
- ✅ Can rollback by reverting code changes

**Deployment steps:**
1. Update `queries.py` with transformations
2. Update `charts.py` with `.1f` formatting
3. Add tests to verify correct scale
4. Deploy code changes
5. Verify charts show correct values
6. Update documentation

**Rollback plan:**
- Simply revert the code changes
- No database state to restore

## Conclusion

The yield display scale issue is a **high-impact but low-risk** problem:

✅ **Good News:**
- Data is intact and correct
- Issue is purely in display layer
- Fix is straightforward

⚠️ **Action Required:**
- Implement database migration to fix scale
- Update parser to divide by 10
- Update documentation
- Verify all charts display correctly

**Estimated Effort:** 2-3 hours
**Priority:** HIGH (affects all yield visualizations)
**Risk:** LOW (data migration with backup)

---

*This report was generated through systematic investigation of the codebase, database, and Old World save file format.*
