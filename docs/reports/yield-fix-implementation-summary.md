# Yield Display Fix - Implementation Summary

**Quick Reference Guide for Developer**

## TL;DR

All yield charts show values **10x too high** (215 instead of 21.5). Fix by adding `/ 10.0` to one query in `queries.py` and updating one format string in `charts.py`.

**Estimated Time:** 15-30 minutes
**Files to Change:** 2 files, ~3 lines of code
**Testing Time:** 10 minutes
**No database migration required!**

## The Fix

### 1. Update Query (queries.py)

**File:** `tournament_visualizer/data/queries.py`
**Line:** ~1615

```python
# FIND THIS:
SELECT
    yh.player_id,
    p.player_name,
    p.civilization,
    yh.turn_number,
    yh.resource_type,
    yh.amount           # <-- Current line
FROM player_yield_history yh

# CHANGE TO:
SELECT
    yh.player_id,
    p.player_name,
    p.civilization,
    yh.turn_number,
    yh.resource_type,
    yh.amount / 10.0 AS amount  # <-- Add / 10.0
FROM player_yield_history yh
```

**Why:** Old World stores yields in units of 0.1. Database has raw values (215), we need display values (21.5).

### 2. Update Chart Format (charts.py)

**File:** `tournament_visualizer/components/charts.py`
**Line:** ~2419

```python
# FIND THIS:
hover_texts = [
    f"<b>{player}</b><br>Turn {turn}: {yield_val} {display_name.lower()}"
    for turn, yield_val in zip(turns, yields)
]

# CHANGE TO:
hover_texts = [
    f"<b>{player}</b><br>Turn {turn}: {yield_val:.1f} {display_name.lower()}"
    #                                              ^^^^ Add .1f for one decimal place
    for turn, yield_val in zip(turns, yields)
]
```

**Why:** Show "21.5" instead of "21.500000" in hover tooltips.

### 3. Add Documentation Comments

**In queries.py, add docstring note:**
```python
def get_yield_history_by_match(self, match_id: int, ...):
    """Get yield production progression for all players in a match.

    NOTE: Old World stores yields in units of 0.1 internally.
    This query divides by 10 to return display-ready values.
    Example: XML value of 215 returns as 21.5 science/turn

    See: docs/reports/yield-display-scale-issue.md
    """
```

**In SQL query, add inline comment:**
```sql
SELECT
    yh.amount / 10.0 AS amount  -- Old World stores in 0.1 units
FROM player_yield_history yh
```

## Testing

### Before Running Tests

Start the server:
```bash
uv run python manage.py restart
```

### 1. Quick Visual Test

1. Navigate to any match detail page
2. Scroll to "Science" chart
3. **Before fix:** Y-axis shows 0-700 range, hover shows "215"
4. **After fix:** Y-axis shows 0-70 range, hover shows "21.5"

### 2. Database Verification

```bash
# Raw values should still be untouched
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT turn_number, amount
FROM player_yield_history
WHERE resource_type = 'YIELD_SCIENCE' AND match_id = 1 AND player_id = 1
LIMIT 5
"
# Expected: 215, 215, 234, etc. (NOT changed)
```

### 3. Query Test

```bash
# After fix, query should return transformed values
uv run python -c "
from tournament_visualizer.data.queries import get_queries
df = get_queries().get_yield_history_by_match(1, ['YIELD_SCIENCE'])
print(df[['turn_number', 'amount']].head())
"
# Expected: 21.5, 21.5, 23.4, etc. (divided by 10)
```

### 4. All Yield Types

Check all 14 yield charts on match page:
- Food, Growth, Science, Culture, Civics, Training, Money, Orders
- Iron, Stone, Wood, Happiness, Discontent, Maintenance

**All should show reasonable ranges:**
- Early game: 10-50 range (not 100-500)
- Late game: 50-150 range (not 500-1500)

## Expected Results

| Metric | Before | After | ✓ |
|--------|--------|-------|---|
| Raw DB value | 215 | 215 | Same |
| Query result | 215 | 21.5 | ÷10 |
| Chart Y-axis | 0-700 | 0-70 | Scaled |
| Hover tooltip | "215 science" | "21.5 science" | Decimal |
| Early game avg | ~210 | ~21 | Realistic |

## Common Mistakes to Avoid

### ❌ Don't Transform Twice
```python
# WRONG!
df = queries.get_yield_history_by_match(match_id)
df['amount'] = df['amount'] / 10.0  # Already divided in query!
```

### ❌ Don't Use Integer Division
```sql
-- WRONG - may truncate decimals
amount / 10

-- CORRECT - preserves decimals
amount / 10.0
```

### ❌ Don't Modify Raw Data
```python
# WRONG - Don't divide in parser
amount = int(xml_value) / 10.0

# CORRECT - Keep raw in parser
amount = int(xml_value)  # Store 215
```

## Rollback

If something goes wrong:

```bash
# Just revert the code changes
git checkout tournament_visualizer/data/queries.py
git checkout tournament_visualizer/components/charts.py

# Restart server
uv run python manage.py restart
```

No database changes to undo!

## Additional Queries That May Need Fixing (Future)

**Note:** There's one more query that accesses `player_yield_history` but is **not currently used**:

**File:** `tournament_visualizer/data/queries.py:535`
**Method:** `get_resource_progression()`

```python
# Currently returns raw values (line 552)
r.amount

# If this gets used in the future, change to:
r.amount / 10.0 AS amount
```

**Action:** No immediate fix needed (not used), but document for future reference.

## Files Reference

**Changed:**
1. `tournament_visualizer/data/queries.py` - Add `/10.0` to query (line ~1615)
2. `tournament_visualizer/components/charts.py` - Add `.1f` format (line ~2419)

**Note for Future:**
3. `tournament_visualizer/data/queries.py` - `get_resource_progression()` (line ~552) - not used yet

**Documentation:**
- `docs/reports/yield-display-scale-issue.md` - Full investigation
- `docs/reports/yield-display-scale-issue-addendum.md` - Why Old World uses this format
- `CLAUDE.md` - Developer reference (section: "Yield Value Display Scale")

## Why This Approach?

**Query transformation** (not database transformation):

✅ No database migration
✅ Preserves exact XML values
✅ Easy rollback
✅ Flexible for future changes
✅ Simple parser

The only downside: must remember `/10.0` in future yield queries. But we only have one yield query currently, so low risk.

## Questions?

**Q: Why does Old World do this?**
A: Fixed-point arithmetic for multiplayer determinism. See `yield-display-scale-issue-addendum.md`

**Q: Are there other fields with this issue?**
A: Only yields. Other values (unit counts, city counts, etc.) display as-is.

**Q: What if I need raw values later?**
A: Create separate query method without division, or query the table directly.

**Q: Will this affect performance?**
A: No. Division by constant is negligible (microseconds).

**Q: Do I need to update tests?**
A: Only if you have tests that check exact yield values. Update expected values from 215 → 21.5.

## Deployment Checklist

- [ ] Update `queries.py` with `/10.0` transformation
- [ ] Update `charts.py` with `.1f` formatting
- [ ] Add docstring to `get_yield_history_by_match()`
- [ ] Test on local: science chart shows 20-70 range
- [ ] Test on local: hover shows "21.5" format
- [ ] Check all 14 yield charts look reasonable
- [ ] Commit with message: "fix: Apply /10 scale to yield display values"
- [ ] Deploy to production
- [ ] Verify production charts show correct scale

---

**Total Implementation Time:** ~30 minutes
**Risk Level:** LOW (no database changes, easy rollback)
**Impact:** HIGH (fixes all yield visualizations)
