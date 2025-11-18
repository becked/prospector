# Issue: Missing Turn 1 Science Data in player_yield_history

**Status:** Open
**Severity:** Medium
**Component:** Parser (`tournament_visualizer/data/parser.py`)
**Table Affected:** `player_yield_history`
**Discovered:** 2025-01-18

## Summary

Only 6 out of 34 matches have science yield data for turn 1 in the `player_yield_history` table, while all 34 matches have complete data starting from turn 2. This results in incomplete historical data for the earliest game turns.

## Impact

- **Science progression charts** start with incomplete sample sizes (6 games instead of 34)
- **Turn-by-turn analysis** cannot accurately represent turn 1 science production
- **Data quality** metrics are skewed for early-game analysis
- **Workaround implemented:** Filter turn 1 from sample size indicators on charts

## Data Evidence

### Turn-by-Turn Data Availability

```sql
SELECT
    turn_number,
    COUNT(DISTINCT yh.match_id) as unique_matches,
    COUNT(*) as total_players
FROM player_yield_history yh
WHERE yh.resource_type = 'YIELD_SCIENCE'
  AND yh.turn_number IN (1, 2, 3)
GROUP BY turn_number
ORDER BY turn_number;
```

**Results:**
| Turn | Unique Matches | Total Players |
|------|----------------|---------------|
| 1    | 6              | 6             |
| 2    | 34             | 68            |
| 3    | 34             | 68            |

**Expected:** All 34 matches should have data for turn 1

### Turn 1 Sample Data

```sql
SELECT
    yh.match_id,
    yh.player_id,
    p.player_name,
    yh.amount / 10.0 as science
FROM player_yield_history yh
JOIN players p ON yh.match_id = p.match_id AND yh.player_id = p.player_id
WHERE yh.resource_type = 'YIELD_SCIENCE'
  AND yh.turn_number = 1
ORDER BY yh.match_id;
```

**Results:** Only 6 matches have turn 1 data:
- Match 2 (Marauder): 10.0 science
- Match 4 (Cliff): 11.0 science
- Match 15 (Fiddler): 14.1 science
- Match 20 (Fluffybunny): 12.8 science
- Match 24 (Rincewind): 10.0 science
- Match 25 (mojo): 9.3 science

**Missing:** Matches 1, 3, 5-14, 16-19, 21-23, 26-34 (28 matches total)

## Possible Root Causes

### 1. Parser Logic Issue
The parser may skip turn 1 science data under certain conditions:
- **Zero-value filtering:** If turn 1 science is 0, parser might skip it
- **Turn number logic:** Parser might start collecting from turn 2
- **XML structure variation:** Some save files might structure turn 1 differently

### 2. Game Mechanics
Turn 1 science production might genuinely be 0 for most players:
- Players start with no science-producing improvements
- Science production begins after turn 1 infrastructure is built
- **However:** 6 games DO have non-zero turn 1 science (10-14 range), suggesting this isn't universally true

### 3. Save File Differences
The 6 games with turn 1 data might have different characteristics:
- Different game settings
- Different civilizations with starting science bonuses
- Different map types or scenarios

## Investigation Steps

### 1. Examine Parser Code

**File:** `tournament_visualizer/data/parser.py`

Look for the `extract_yield_history()` method or similar yield parsing logic:

```python
# Check for conditions that might skip turn 1:
- Minimum turn number checks (e.g., if turn_number < 2: skip)
- Zero-value filtering (e.g., if amount == 0: skip)
- Turn iteration logic (does it start at 0, 1, or 2?)
```

### 2. Inspect Raw XML Files

Compare a save file that HAS turn 1 data vs one that DOESN'T:

```bash
# Extract and examine save files
unzip -p saves/match_2.zip | grep -A 20 "YIELD_SCIENCE"  # Has turn 1 data
unzip -p saves/match_1.zip | grep -A 20 "YIELD_SCIENCE"  # Missing turn 1 data
```

Questions to answer:
- Is turn 1 science data present in the XML for matches 1, 3, 5, etc.?
- If yes, why isn't it being parsed?
- If no, why do only some games have it?

### 3. Check for Zero Values

Query the database to see if zero values are being stored for other resources:

```sql
SELECT
    resource_type,
    COUNT(*) as zero_value_count
FROM player_yield_history
WHERE turn_number = 1
  AND amount = 0
GROUP BY resource_type;
```

If no zeros exist, the parser is likely filtering them out.

### 4. Test Re-Import

Re-import a save file that's missing turn 1 data with verbose logging:

```bash
# Enable debug logging and re-import a specific match
# Check parser output for turn 1 handling
```

## Expected Fix

After investigation, one of these fixes will likely be needed:

### Option A: Parser is incorrectly filtering turn 1
```python
# BEFORE (incorrect)
for turn_data in yield_history:
    if turn_number < 2:  # Skips turn 1
        continue

# AFTER (correct)
for turn_data in yield_history:
    # Process all turns including turn 1
```

### Option B: Parser is skipping zero values
```python
# BEFORE (incorrect)
if amount == 0:
    continue  # Skips zero science production

# AFTER (correct)
# Store zero values for complete historical data
# OR document that zeros are intentionally excluded
```

### Option C: XML parsing logic issue
```python
# Check for off-by-one errors in turn number extraction
# Verify that turn 1 XML nodes are being read correctly
```

## Validation After Fix

After implementing a fix, validate with these queries:

```sql
-- Should return 34 matches for all early turns
SELECT
    turn_number,
    COUNT(DISTINCT match_id) as match_count
FROM player_yield_history
WHERE resource_type = 'YIELD_SCIENCE'
  AND turn_number BETWEEN 1 AND 5
GROUP BY turn_number
ORDER BY turn_number;

-- All should show 34 matches
```

## Workaround (Currently Implemented)

In `tournament_visualizer/components/charts.py`, the sample size line filters out turn 1:

```python
# Filter out turn 1 which often has incomplete data
sample_df = df[df["turn_number"] >= 2].copy()
```

This prevents the chart from showing misleading sample sizes, but **does not fix the underlying data issue**.

## Related Files

- **Parser:** `tournament_visualizer/data/parser.py`
- **Database Schema:** `docs/schema.sql` (table: `player_yield_history`)
- **Chart Workaround:** `tournament_visualizer/components/charts.py:5147`
- **Query Method:** `tournament_visualizer/data/queries.py:4018` (`get_science_win_correlation`)

## References

- Yield display scale documentation: `docs/archive/reports/yield-display-scale-issue.md`
- Database schema: `docs/database-schema.md`

## Next Steps

1. Examine `parser.py` for turn 1 filtering logic
2. Inspect raw XML from affected save files
3. Determine if missing data is a parser bug or game mechanics
4. Implement fix in parser
5. Re-import affected games
6. Remove chart workaround once data is complete
