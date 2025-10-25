# Yield Display Fix - Implementation Plan

> **Status**: Completed and archived (2025-10-25)
>
> Fix implemented. See CLAUDE.md (Yield Value Display Scale section).

## Context

### The Problem

All yield charts in the tournament visualizer show values 10x too high (e.g., 215 science/turn instead of 21.5). This happens because Old World's game engine stores yield values in units of 0.1 internally (for fixed-point arithmetic), but we're displaying the raw values instead of dividing by 10.

**Visual Impact:**
- Science chart shows 0-700 range instead of 0-70
- Hover tooltips show "215 science" instead of "21.5 science"
- All 14 yield types affected (Food, Growth, Science, Culture, Civics, Training, Money, Orders, Iron, Stone, Wood, Happiness, Discontent, Maintenance)

### Why Old World Does This

Old World uses fixed-point arithmetic (storing decimals as integers × 10) to ensure deterministic calculations across multiplayer games. Floating-point math can produce slightly different results on different CPUs, causing multiplayer desyncs. By storing 21.5 as 215, they can use integer math while preserving one decimal place.

### Our Current Data Flow

```
XML Save File          Parser              Database            Query                UI
<YIELD_SCIENCE>   →   amount = 215    →   amount = 215    →   amount = 215    →   "215 science"
  215                  (raw int)           (raw int)           (raw int)           (WRONG!)
</YIELD_SCIENCE>
```

### Target Data Flow

```
XML Save File          Parser              Database            Query                   UI
<YIELD_SCIENCE>   →   amount = 215    →   amount = 215    →   amount / 10.0 = 21.5  →  "21.5 science"
  215                  (raw int)           (raw int)           (display value)          (CORRECT!)
</YIELD_SCIENCE>
```

### Design Decision: Query Transformation vs Parser Transformation

We chose **query transformation** (divide in SQL) over **parser transformation** (divide during import):

✅ **Advantages:**
- Preserves exact XML values in database (data integrity)
- No data loss from premature conversion
- Simple parser logic (fewer places to modify)
- Flexible for future changes (can add raw-value queries if needed)
- Easy rollback (just revert code changes, no database migration)

❌ **Disadvantage:**
- Must remember to divide by 10 in future yield queries (low risk - we only have 2 yield queries)

## Prerequisites

### Required Knowledge

**Python:**
- Type annotations
- f-strings and string formatting
- List comprehensions
- Context managers (`with` statements)

**SQL:**
- SELECT statements
- Column aliases (`AS`)
- Float division vs integer division

**Testing:**
- pytest basics
- Assertions
- Test isolation principles
- Mocking/patching (for database tests)

**Tools:**
- `uv` - Python package manager (like `pip` but faster)
- `duckdb` - Analytical database (like SQLite but for analytics)
- `pytest` - Testing framework
- `black` - Code formatter
- `ruff` - Code linter

### Files You'll Work With

```
tournament_visualizer/
├── data/
│   ├── queries.py              # SQL queries (MODIFY)
│   └── parser.py               # XML parsing (READ ONLY - for context)
└── components/
    └── charts.py               # Plotly charts (MODIFY)

tests/
└── test_yield_display.py       # New test file (CREATE)

docs/
└── reports/
    ├── yield-display-scale-issue.md              # Investigation (READ)
    ├── yield-display-scale-issue-addendum.md     # Background (READ)
    └── yield-fix-implementation-summary.md        # Quick reference (READ)

CLAUDE.md                       # Project conventions (READ)
```

### Environment Setup

```bash
# Verify uv is installed
uv --version

# Verify database exists
ls -lh data/tournament_data.duckdb

# Start the dev server (we'll need this for testing)
uv run python manage.py start

# Verify it's running
curl http://localhost:8050
```

## Implementation Tasks

### Task 1: Understand Current State (15 min)

**Goal:** Verify the bug exists and understand the data flow.

**Steps:**

1. **Check raw database values:**
   ```bash
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT turn_number, amount
   FROM player_yield_history
   WHERE resource_type = 'YIELD_SCIENCE' AND match_id = 1 AND player_id = 1
   LIMIT 5
   "
   ```

   **Expected output:** `amount` should be around 200-300 (raw values)

2. **Navigate to any match detail page:**
   - Open http://localhost:8050
   - Click on any match
   - Scroll to "Science" chart

3. **Observe the bug:**
   - Y-axis shows 0-700 range (should be 0-70)
   - Hover over a data point - shows "215 science" (should be "21.5 science")

4. **Read the parser code** to understand how values are stored:
   ```bash
   # Open parser.py and find extract_yield_history method
   uv run python -c "
   import inspect
   from tournament_visualizer.data.parser import SaveFileParser
   print(inspect.getsource(SaveFileParser.extract_yield_history))
   "
   ```

   **Key observation:** Line with `amount = self._safe_int(turn_elem.text)` stores raw value

5. **Read the query code** to see current implementation:
   ```bash
   # Find the yield history query
   grep -n "def get_yield_history_by_match" tournament_visualizer/data/queries.py
   ```

**Verification:**
- [ ] Confirmed database has raw values (200-300 range)
- [ ] Confirmed UI shows wrong values (200-300 instead of 20-30)
- [ ] Located parser code (stores raw values)
- [ ] Located query code (no division)

**Time estimate:** 15 minutes

**Commit:** No commit for this task (investigation only)

---

### Task 2: Write Failing Tests (TDD) (20 min)

**Goal:** Create tests that will fail now, but pass after we implement the fix.

**Why TDD?** Writing tests first helps us:
- Define exactly what "correct" looks like
- Catch regressions if we break something
- Document expected behavior

**Create:** `tests/test_yield_display.py`

**Code:**

```python
"""Tests for yield value display scale (divide by 10 for display)."""

import pytest
from tournament_visualizer.data.queries import get_queries


class TestYieldDisplayScale:
    """Test that yield values are correctly scaled for display."""

    @pytest.fixture
    def queries(self):
        """Get queries instance."""
        return get_queries()

    def test_yield_values_are_divided_by_10(self, queries):
        """Yield query should return display-ready values (raw / 10).

        Old World stores yields in 0.1 units (21.5 stored as 215).
        The query must divide by 10 to return display-ready values.

        Example: If XML has <YIELD_SCIENCE>215</YIELD_SCIENCE>,
        database stores 215, and query should return 21.5.
        """
        # Get science yield data for match 1
        df = queries.get_yield_history_by_match(
            match_id=1,
            yield_types=["YIELD_SCIENCE"]
        )

        # Should have data
        assert len(df) > 0, "No yield data found for match 1"

        # Values should be in reasonable display range (10-100)
        # NOT in raw range (100-1000)
        avg_value = df["amount"].mean()
        max_value = df["amount"].max()

        # Early game science is typically 10-50, not 100-500
        assert avg_value < 100, (
            f"Average science {avg_value:.1f} suggests raw values "
            f"(expected <100 for display values)"
        )
        assert max_value < 200, (
            f"Max science {max_value:.1f} suggests raw values "
            f"(expected <200 for display values)"
        )

    def test_yield_values_have_decimal_precision(self, queries):
        """Yield values should support one decimal place.

        The division by 10.0 (float) should preserve decimal precision.
        For example: 215 / 10.0 = 21.5 (not 21).
        """
        df = queries.get_yield_history_by_match(
            match_id=1,
            yield_types=["YIELD_SCIENCE"]
        )

        # Check if any values have decimal places
        # (not all will, but many should: 21.5, 23.4, etc.)
        has_decimals = any(df["amount"] % 1 != 0)
        assert has_decimals, (
            "No decimal values found - suggests integer division was used "
            "instead of float division (use / 10.0 not / 10)"
        )

    def test_all_yield_types_are_scaled(self, queries):
        """All 14 yield types should be scaled correctly.

        This ensures we didn't miss any yield type in the query.
        """
        # Get all yield types for match 1
        df = queries.get_yield_history_by_match(match_id=1)

        # Should have data for multiple yield types
        yield_types = df["resource_type"].unique()
        assert len(yield_types) > 5, "Expected data for multiple yield types"

        # All values should be in display range
        for yield_type in yield_types:
            yield_data = df[df["resource_type"] == yield_type]
            max_value = yield_data["amount"].max()

            # Most yields stay under 200 (except maybe late-game money)
            # But raw values would be 2000+
            assert max_value < 500, (
                f"{yield_type} max value {max_value:.1f} suggests raw values "
                f"(expected <500 for display values)"
            )

    def test_database_still_has_raw_values(self):
        """Database should still contain raw values (we transform in query).

        This verifies our design decision: we divide in the query,
        not during parsing/import.
        """
        import duckdb

        # Query database directly (bypass our query layer)
        conn = duckdb.connect("data/tournament_data.duckdb", read_only=True)
        result = conn.execute("""
            SELECT amount
            FROM player_yield_history
            WHERE resource_type = 'YIELD_SCIENCE'
              AND match_id = 1
              AND player_id = 1
            LIMIT 1
        """).fetchone()
        conn.close()

        raw_value = result[0]

        # Database should have raw values (100-1000), not display values (10-100)
        assert raw_value > 100, (
            f"Database value {raw_value} is too low - expected raw values "
            f"(100-1000 range), not display values (10-100 range)"
        )
```

**Test Design Notes:**

1. **Test one thing at a time:** Each test has a clear, single purpose
2. **Good assertions:** Include helpful messages explaining what went wrong
3. **No magic numbers:** Comments explain why we expect certain ranges
4. **Test the boundaries:** Verify both that transformation happens AND uses float division
5. **Test the design:** Verify database still has raw values (our architectural decision)

**Run the tests (they should FAIL):**

```bash
uv run pytest tests/test_yield_display.py -v
```

**Expected output:**
```
FAILED test_yield_values_are_divided_by_10 - AssertionError: Average science 215.3 suggests raw values
FAILED test_yield_values_have_decimal_precision - AssertionError: No decimal values found
FAILED test_all_yield_types_are_scaled - AssertionError: YIELD_CIVICS max value 2500.0 suggests raw values
PASSED test_database_still_has_raw_values
```

**Verification:**
- [ ] Test file created with 4 tests
- [ ] 3 tests fail (as expected)
- [ ] 1 test passes (database has raw values)
- [ ] Error messages are clear and helpful

**Commit:**
```bash
git add tests/test_yield_display.py
git commit -m "test: Add failing tests for yield display scale issue

Tests verify that yield values are divided by 10 for display.
Currently failing - values show as 215 instead of 21.5.

Related to yield-display-scale-issue.md investigation."
```

**Time estimate:** 20 minutes

---

### Task 3: Fix the Query (10 min)

**Goal:** Update the SQL query to divide yield values by 10.

**File:** `tournament_visualizer/data/queries.py`

**Steps:**

1. **Find the method:**
   ```bash
   grep -n "def get_yield_history_by_match" tournament_visualizer/data/queries.py
   ```

   Should show line number ~1595

2. **Read the current implementation:**

   Look for the SELECT statement around line 1615. You'll see:
   ```sql
   SELECT
       yh.player_id,
       p.player_name,
       p.civilization,
       yh.turn_number,
       yh.resource_type,
       yh.amount           -- Current: returns raw value
   FROM player_yield_history yh
   ```

3. **Make the change:**

   **Find this line (~1615):**
   ```python
   yh.amount
   ```

   **Replace with:**
   ```python
   yh.amount / 10.0 AS amount  -- Old World stores in 0.1 units
   ```

4. **Add documentation to the method:**

   Find the docstring at the start of `get_yield_history_by_match` (around line 1595).

   **Add this note at the end of the docstring:**
   ```python
   """Get yield production progression for all players in a match.

   [existing docstring content...]

   Note:
       Old World stores yields in units of 0.1 internally (for fixed-point
       arithmetic in multiplayer). This query divides by 10 to return
       display-ready values.

       Example: XML value of 215 returns as 21.5 science/turn

       See: docs/reports/yield-display-scale-issue.md
   """
   ```

**Important SQL Details:**

- **Use `10.0` not `10`** - Float division preserves decimals (215 / 10.0 = 21.5)
- **Integer division would truncate** - 215 / 10 = 21 (loses the .5)
- **Column alias required** - `AS amount` keeps the column name consistent

**Full context of the change:**

```python
base_query = """
SELECT
    yh.player_id,
    p.player_name,
    p.civilization,
    yh.turn_number,
    yh.resource_type,
    yh.amount / 10.0 AS amount  -- Old World stores in 0.1 units
FROM player_yield_history yh
JOIN players p ON yh.player_id = p.player_id AND yh.match_id = p.match_id
WHERE yh.match_id = ?
"""
```

**Verification:**

```bash
# Test the query directly
uv run python -c "
from tournament_visualizer.data.queries import get_queries
df = get_queries().get_yield_history_by_match(1, ['YIELD_SCIENCE'])
print(df[['turn_number', 'amount']].head())
print(f'\nAverage: {df[\"amount\"].mean():.1f}')
print(f'Max: {df[\"amount\"].max():.1f}')
"
```

**Expected output:**
```
   turn_number  amount
0            2    21.5
1            3    21.5
2            4    21.5
3            5    21.5
4            6    21.5

Average: 24.3
Max: 58.0
```

**Verification checklist:**
- [ ] Values are now 10x smaller (21.5 instead of 215)
- [ ] Decimal places preserved (.5, .4, etc.)
- [ ] Column still named "amount" (alias works)
- [ ] Docstring updated with explanation

**Commit:**
```bash
git add tournament_visualizer/data/queries.py
git commit -m "fix: Apply /10 scale to yield values in query

Old World stores yields in 0.1 units (21.5 stored as 215).
Query now divides by 10.0 to return display-ready values.

- Use float division (10.0) to preserve decimals
- Add inline SQL comment explaining transformation
- Update docstring with rationale and reference

Fixes 3 of 4 failing tests in test_yield_display.py"
```

**Time estimate:** 10 minutes

---

### Task 4: Fix Chart Formatting (5 min)

**Goal:** Update hover tooltips to show one decimal place (21.5 instead of 21.500000).

**File:** `tournament_visualizer/components/charts.py`

**Why this matters:** Even though our query now returns 21.5, Python's default f-string formatting might show it as "21.5" or "21.500000" depending on the value. We want consistent one-decimal formatting.

**Steps:**

1. **Find the method:**
   ```bash
   grep -n "def create_yield_chart" tournament_visualizer/components/charts.py
   ```

   Should show line number ~2370

2. **Find the hover text generation** (around line 2419):

   **Current code:**
   ```python
   hover_texts = [
       f"<b>{player}</b><br>Turn {turn}: {yield_val} {display_name.lower()}"
       for turn, yield_val in zip(turns, yields)
   ]
   ```

   **Change to:**
   ```python
   hover_texts = [
       f"<b>{player}</b><br>Turn {turn}: {yield_val:.1f} {display_name.lower()}"
       for turn, yield_val in zip(turns, yields)
   ]
   ```

   **What changed:** Added `:.1f` format specifier
   - `:` - Start format specification
   - `.1` - One decimal place
   - `f` - Fixed-point notation (not scientific)

3. **Format specifier examples:**
   ```python
   value = 21.5
   f"{value}"      # "21.5" (default, variable decimals)
   f"{value:.1f}"  # "21.5" (always 1 decimal)
   f"{value:.2f}"  # "21.50" (always 2 decimals)
   f"{value:.0f}"  # "22" (no decimals, rounds)

   value = 21.567
   f"{value:.1f}"  # "21.6" (rounds to 1 decimal)
   ```

**Verification:**

```bash
# Restart server to pick up changes
uv run python manage.py restart

# Wait for server to start
sleep 3

# Open browser and check
echo "Visit http://localhost:8050 and check a match's science chart"
echo "Hover over data points - should show '21.5 science' format"
```

**Visual check:**
- [ ] Navigate to a match detail page
- [ ] Hover over science chart data point
- [ ] Tooltip shows "21.5 science" (one decimal, consistent)

**Verification checklist:**
- [ ] Added `.1f` format specifier
- [ ] Tooltip shows one decimal place
- [ ] Y-axis range is now 0-70 instead of 0-700

**Commit:**
```bash
git add tournament_visualizer/components/charts.py
git commit -m "fix: Format yield tooltips with one decimal place

Show yields as '21.5' instead of '21.500000' in hover text.
Uses .1f format specifier for consistent decimal display.

Completes yield display fix - all values now show correctly."
```

**Time estimate:** 5 minutes

---

### Task 5: Verify Tests Pass (5 min)

**Goal:** Confirm all tests now pass with our changes.

**Run tests:**

```bash
uv run pytest tests/test_yield_display.py -v
```

**Expected output:**
```
tests/test_yield_display.py::TestYieldDisplayScale::test_yield_values_are_divided_by_10 PASSED
tests/test_yield_display.py::TestYieldDisplayScale::test_yield_values_have_decimal_precision PASSED
tests/test_yield_display.py::TestYieldDisplayScale::test_all_yield_types_are_scaled PASSED
tests/test_yield_display.py::TestYieldDisplayScale::test_database_still_has_raw_values PASSED

===================== 4 passed in 0.52s =====================
```

**If any tests fail:**

1. **Read the assertion message** - it will tell you what's wrong
2. **Common issues:**
   - Used `/10` instead of `/10.0` → No decimals (test 2 fails)
   - Forgot `AS amount` → Column name changed (test 1 fails)
   - Changed wrong query → Still returns raw values (tests 1, 2, 3 fail)

**Run full test suite** to ensure we didn't break anything:

```bash
uv run pytest -v
```

**Expected:** All tests pass (including pre-existing tests)

**Verification checklist:**
- [ ] All 4 yield display tests pass
- [ ] All other tests still pass
- [ ] No new warnings or errors

**Time estimate:** 5 minutes

**No commit** (tests passing is verification, not a change)

---

### Task 6: Manual End-to-End Testing (10 min)

**Goal:** Verify the fix works in the actual UI for all yield types.

**Why manual testing?** Our automated tests verify the query returns correct values, but we should also verify the full user experience (charts render correctly, tooltips work, etc.).

**Testing checklist:**

1. **Start the server** (if not already running):
   ```bash
   uv run python manage.py restart
   ```

2. **Navigate to match detail page:**
   - Open http://localhost:8050
   - Click on any match from the list
   - Scroll to the yield charts section

3. **Test Science chart:**
   - [ ] Y-axis shows reasonable range (0-70, not 0-700)
   - [ ] Hover over a data point → tooltip shows "21.5 science" format
   - [ ] Values match expectations (early game: 10-30, late game: 40-80)

4. **Test other yield types** (spot check a few):
   - [ ] Civics chart shows 0-50 range (not 0-500)
   - [ ] Training chart shows 0-40 range (not 0-400)
   - [ ] Money chart shows 0-100 range (not 0-1000)
   - [ ] All tooltips show one decimal place

5. **Test multiple matches:**
   - [ ] Navigate to 2-3 different matches
   - [ ] Verify yield charts look correct in all of them

6. **Verify database unchanged:**
   ```bash
   # Raw values should still be in database (not transformed)
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT turn_number, amount
   FROM player_yield_history
   WHERE resource_type = 'YIELD_SCIENCE' AND match_id = 1 AND player_id = 1
   LIMIT 3
   "
   ```

   **Expected:** Values are still ~200-300 (raw), not 20-30 (transformed)

**What "correct" looks like:**

| Yield Type | Early Game Range | Late Game Range | Notes |
|-----------|------------------|-----------------|-------|
| Science | 10-30 | 40-80 | Most consistent |
| Civics | 5-20 | 30-60 | Lower than science |
| Training | 10-25 | 30-50 | Military focus |
| Money | 20-50 | 60-150 | Highest values |
| Food | 10-30 | 30-60 | Per-city |
| Growth | 5-15 | 15-40 | Population |

**Before vs After comparison:**

```
BEFORE:
- Science Y-axis: 0 to 700
- Hover: "215 science"
- Visual: Looks artificially inflated

AFTER:
- Science Y-axis: 0 to 70
- Hover: "21.5 science"
- Visual: Realistic progression
```

**Verification checklist:**
- [ ] All 14 yield types show correct scales
- [ ] Tooltips consistently show 1 decimal place
- [ ] Y-axis ranges are 10x smaller than before
- [ ] Database still has raw values (transformation in query only)
- [ ] Charts render without errors

**Time estimate:** 10 minutes

**No commit** (manual testing is verification)

---

### Task 7: Update Future Query (Optional - YAGNI) (5 min)

**Goal:** Decide whether to update the unused `get_resource_progression()` query.

**Context:** There's a second query that accesses `player_yield_history`, but it's currently not used anywhere in the codebase.

**Find it:**

```bash
grep -n "def get_resource_progression" tournament_visualizer/data/queries.py
```

Should be around line 535.

**Check if it's used:**

```bash
# Search for calls to this method
grep -r "get_resource_progression" tournament_visualizer/ --exclude-dir=__pycache__
```

**Expected:** Only finds the method definition, no calls.

**Decision:**

Following **YAGNI** (You Ain't Gonna Need It):
- ✅ **Do NOT modify it now** - it's not used
- ✅ **Do add a TODO comment** - document for future

**Add this comment** above the method definition (around line 535):

```python
def get_resource_progression(self, match_id: int, ...) -> pd.DataFrame:
    """Get resource stockpile progression for a match.

    WARNING: This query is currently unused. If you activate it in the future,
    remember to apply the yield scale transformation (/ 10.0) to any yield
    values returned from player_yield_history table.

    See: docs/reports/yield-fix-implementation-summary.md
    TODO: Apply /10.0 transformation if this query is activated

    [rest of existing docstring...]
    """
```

**Why this approach?**
- We don't modify unused code (YAGNI)
- We document the gotcha for future developers
- Clear reference to our implementation docs
- Easy to find with `grep TODO`

**Verification:**
- [ ] Added warning comment to unused query
- [ ] Did NOT modify the SQL (it's unused)

**Commit:**
```bash
git add tournament_visualizer/data/queries.py
git commit -m "docs: Add TODO for unused yield query

get_resource_progression() is not currently used but accesses
player_yield_history. Added warning comment about applying
/10 scale transformation if this query is activated later.

YAGNI: Not modifying unused code, just documenting the gotcha."
```

**Time estimate:** 5 minutes

---

### Task 8: Code Quality & Formatting (5 min)

**Goal:** Ensure code follows project standards.

**Steps:**

1. **Format code with Black:**
   ```bash
   uv run black tournament_visualizer/
   ```

   **Expected:** "All done! ✨ 🍰 ✨" or "X files reformatted"

2. **Lint code with Ruff:**
   ```bash
   uv run ruff check tournament_visualizer/
   ```

   **Expected:** No errors (or only warnings you can ignore)

3. **Fix auto-fixable issues:**
   ```bash
   uv run ruff check --fix tournament_visualizer/
   ```

4. **Run tests one more time:**
   ```bash
   uv run pytest tests/test_yield_display.py -v
   ```

   **Expected:** All 4 tests pass

**Common Black changes:**
- Adjusts line length (max 88 characters)
- Fixes quote style (uses double quotes)
- Adjusts whitespace around operators

**Common Ruff warnings you can ignore:**
- Line too long (if it's a long SQL query, that's fine)
- Unused imports in __init__.py files

**Verification checklist:**
- [ ] Black ran successfully
- [ ] Ruff shows no errors
- [ ] Tests still pass after formatting
- [ ] No unintended changes (review git diff)

**Commit if Black made changes:**
```bash
# Only if Black reformatted files
git add tournament_visualizer/
git commit -m "style: Apply Black formatting to modified files"
```

**Time estimate:** 5 minutes

---

### Task 9: Documentation (10 min)

**Goal:** Update project documentation to reflect the changes.

**Files to update:**

1. **CLAUDE.md** - Already updated with correct implementation details

   **Verify the section** "Yield Value Display Scale (Critical!)" shows:
   - Parser stores raw values
   - Database stores raw values
   - Queries divide by 10 for display

   ```bash
   grep -A 20 "Yield Value Display Scale" CLAUDE.md
   ```

2. **No migration doc needed** - This is a code fix, not a schema change

**What NOT to document:**
- Don't create a new migration doc (no schema change)
- Don't create README updates (already have 3 detailed reports)
- Don't create changelog entry (we're not releasing yet)

**Verification:**
- [ ] CLAUDE.md has correct implementation details
- [ ] CLAUDE.md references both investigation docs
- [ ] No unnecessary docs created

**Time estimate:** 10 minutes

**No commit** (CLAUDE.md already updated in earlier work)

---

### Task 10: Final Verification & Summary (10 min)

**Goal:** Confirm everything works end-to-end and summarize changes.

**Final checks:**

1. **Run full test suite:**
   ```bash
   uv run pytest -v
   ```

   **Expected:** All tests pass

2. **Verify database unchanged:**
   ```bash
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT
       MIN(amount) as min_amount,
       MAX(amount) as max_amount,
       AVG(amount) as avg_amount
   FROM player_yield_history
   WHERE resource_type = 'YIELD_SCIENCE'
   "
   ```

   **Expected:** Values still in 100-1000 range (raw values preserved)

3. **Verify query transformation works:**
   ```bash
   uv run python -c "
   from tournament_visualizer.data.queries import get_queries
   df = get_queries().get_yield_history_by_match(1, ['YIELD_SCIENCE'])
   print(f'Query min: {df[\"amount\"].min():.1f}')
   print(f'Query max: {df[\"amount\"].max():.1f}')
   print(f'Query avg: {df[\"amount\"].mean():.1f}')
   "
   ```

   **Expected:** Values in 10-100 range (transformed for display)

4. **Visual verification in UI:**
   - [ ] Science chart shows 0-70 range
   - [ ] Hover shows "21.5 science" format
   - [ ] Multiple yield types all look correct

5. **Review all commits:**
   ```bash
   git log --oneline -10
   ```

   **Expected commits:**
   - test: Add failing tests for yield display scale issue
   - fix: Apply /10 scale to yield values in query
   - fix: Format yield tooltips with one decimal place
   - docs: Add TODO for unused yield query
   - style: Apply Black formatting (if applicable)

**Changes summary:**

```
Files modified: 2 (3 if counting style changes)
Files created: 1 (test file)
Database migrations: 0 (no schema changes)
Lines changed: ~15 lines of actual logic
```

**Verification checklist:**
- [ ] All tests pass
- [ ] Database has raw values (not transformed)
- [ ] Query returns display values (transformed)
- [ ] UI shows correct values and formatting
- [ ] All commits have clear messages
- [ ] No unnecessary files modified

**Time estimate:** 10 minutes

**No commit** (final verification)

---

## Post-Implementation

### Testing in Production (Optional)

If you have a production deployment:

1. **Deploy the changes:**
   ```bash
   # For Fly.io (see CLAUDE.md)
   fly deploy
   ```

2. **Verify production:**
   - Navigate to production URL
   - Check yield charts look correct
   - Verify tooltips show one decimal

3. **Monitor logs:**
   ```bash
   fly logs -a prospector
   ```

   Look for any errors related to yield queries

### Rollback Procedure

If something goes wrong:

1. **Revert code changes:**
   ```bash
   git log --oneline -10  # Find commit before your changes
   git revert <commit-hash>  # Or reset if not pushed
   ```

2. **Restart server:**
   ```bash
   uv run python manage.py restart
   ```

3. **No database rollback needed** - we didn't change the database!

### Future Queries

If you add new queries that use `player_yield_history`:

```python
# Remember to divide by 10 for display
SELECT
    yh.amount / 10.0 AS amount  -- Old World stores in 0.1 units
FROM player_yield_history yh
```

## Common Pitfalls & Solutions

### Pitfall 1: Integer Division

**Problem:** Using `/10` instead of `/10.0`

```python
# WRONG - loses decimal places
yh.amount / 10  # 215 / 10 = 21 (truncated)

# CORRECT - preserves decimal places
yh.amount / 10.0  # 215 / 10.0 = 21.5
```

**How to detect:** Test `test_yield_values_have_decimal_precision` will fail

### Pitfall 2: Missing Column Alias

**Problem:** Forgetting `AS amount`

```python
# WRONG - column name becomes "yh.amount / 10.0"
SELECT yh.amount / 10.0

# CORRECT - column keeps name "amount"
SELECT yh.amount / 10.0 AS amount
```

**How to detect:** Test will fail with "KeyError: 'amount'"

### Pitfall 3: Modifying Database

**Problem:** Trying to update values in database

```python
# DON'T DO THIS - we transform in query, not database
UPDATE player_yield_history
SET amount = amount / 10.0
```

**Why wrong:**
- Loses precision (can't get back to exact XML values)
- Requires database migration
- Harder to rollback
- Violates our design decision

### Pitfall 4: Transforming Twice

**Problem:** Dividing by 10 in both parser and query

```python
# In parser - WRONG if we also divide in query
amount = self._safe_int(turn_elem.text) / 10.0

# In query - WRONG if we also divided in parser
SELECT amount / 10.0  # Now values are 100x too small!
```

**How to detect:** Test will fail with "AssertionError: values too small"

### Pitfall 5: Applying to Wrong Columns

**Problem:** Dividing non-yield columns

```python
# WRONG - turn_number should NOT be divided
SELECT
    turn_number / 10.0,  # Don't do this!
    amount / 10.0
```

**Only divide:** `amount` column from `player_yield_history` table

## Time Estimates Summary

| Task | Estimated Time | Cumulative |
|------|---------------|------------|
| 1. Understand Current State | 15 min | 15 min |
| 2. Write Failing Tests (TDD) | 20 min | 35 min |
| 3. Fix the Query | 10 min | 45 min |
| 4. Fix Chart Formatting | 5 min | 50 min |
| 5. Verify Tests Pass | 5 min | 55 min |
| 6. Manual E2E Testing | 10 min | 65 min |
| 7. Update Future Query (Optional) | 5 min | 70 min |
| 8. Code Quality & Formatting | 5 min | 75 min |
| 9. Documentation | 10 min | 85 min |
| 10. Final Verification | 10 min | 95 min |

**Total: ~1.5 hours** for a competent developer new to the codebase

## Success Criteria

✅ **Code:**
- Query divides by 10.0 (float division)
- Chart tooltips format with .1f
- All changes committed with clear messages

✅ **Tests:**
- All 4 new tests pass
- All existing tests still pass
- No warnings or errors

✅ **Data:**
- Database still has raw values (215)
- Query returns display values (21.5)
- UI shows correct scales and formatting

✅ **Process:**
- Followed TDD (tests first)
- Followed DRY (single transformation point)
- Followed YAGNI (didn't modify unused code)
- Frequent commits (one per task)

## Resources

**Investigation docs:**
- `docs/reports/yield-display-scale-issue.md` - Full investigation
- `docs/reports/yield-display-scale-issue-addendum.md` - Why Old World uses this format
- `docs/reports/yield-fix-implementation-summary.md` - Quick reference guide

**Project docs:**
- `CLAUDE.md` - Project conventions (read the "Yield Value Display Scale" section)

**Code references:**
- `tournament_visualizer/data/parser.py:1325` - `extract_yield_history()` method
- `tournament_visualizer/data/queries.py:1595` - `get_yield_history_by_match()` method
- `tournament_visualizer/components/charts.py:2370` - `create_yield_chart()` method

**Testing:**
- Run tests: `uv run pytest tests/test_yield_display.py -v`
- Start server: `uv run python manage.py start`
- View UI: http://localhost:8050

## Questions?

**Q: Why divide in query instead of parser?**
A: Preserves exact XML values in database, simpler parser, easy rollback, flexible for future changes. See "Design Decision" section above.

**Q: Why `/10.0` not `/10`?**
A: Float division preserves decimals. Integer division truncates (215/10 = 21, loses the .5).

**Q: Do I need to update other queries?**
A: Only one query is currently used (`get_yield_history_by_match`). The other query (`get_resource_progression`) is unused - we added a TODO comment only.

**Q: What if I see values like 21.500000?**
A: Add `.1f` format specifier to the f-string: `f"{value:.1f}"` → "21.5"

**Q: Will this affect performance?**
A: No. Division by a constant is negligible (microseconds). DuckDB is extremely fast.

**Q: What if I need raw values later?**
A: Query the database directly without the `/10.0` transformation, or create a separate query method.
