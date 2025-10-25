# Plotly Modebar Hover Implementation Plan

> **Status**: Completed and archived (2025-10-25)
>
> Charts implemented and working in app. See CLAUDE.md (Dashboard & Chart Conventions section).

## Overview

Update all Plotly modebars across the application to:
1. Display only on hover (instead of always visible)
2. Show only two buttons: zoom in and zoom out

**Estimated Total Time:** 2-3 hours

## Background

### What is a Plotly Modebar?

The modebar is the toolbar that appears on Plotly charts with interactive buttons. Currently, it's always visible (`displayModeBar: True`) and shows various buttons. We want to:
- Make it appear only when hovering over charts
- Simplify it to show only zoom in/out buttons

### Current State

The modebar configuration exists in two places:

1. **`tournament_visualizer/components/layouts.py:87-100`**
   - Function: `create_chart_card()`
   - Current config:
     ```python
     config={
         "displayModeBar": True,
         "displaylogo": False,
         "modeBarButtonsToRemove": [
             "pan2d",
             "lasso2d",
             "select2d",
             "autoScale2d",
             "resetScale2d",
         ],
     }
     ```

2. **`tournament_visualizer/pages/matches.py:1376`**
   - Direct usage: `dcc.Graph(figure=fig)`
   - No config specified (uses Plotly defaults)

### Plotly Modebar Configuration

**displayModeBar options:**
- `True` - Always show
- `False` - Never show
- `'hover'` - Show only on hover

**Available buttons** (we want to keep ONLY these two):
- `zoomIn2d` - Zoom in button
- `zoomOut2d` - Zoom out button

**All other buttons to remove:**
- `pan2d` - Pan
- `zoom2d` - Box zoom
- `select2d` - Box select
- `lasso2d` - Lasso select
- `zoomIn2d` - ✅ Keep this
- `zoomOut2d` - ✅ Keep this
- `autoScale2d` - Autoscale
- `resetScale2d` - Reset axes
- `hoverClosestCartesian` - Hover mode
- `hoverCompareCartesian` - Compare hover
- `toggleSpikelines` - Toggle spike lines
- `toggleHover` - Toggle hover

## Implementation Tasks

### Task 1: Add Modebar Configuration Constant to Config (DRY Principle)

**File:** `tournament_visualizer/config.py`

**Why:** Following DRY principle - define the configuration once and reuse it everywhere.

**Changes:**

Add this constant after line 274 (after `DEFAULT_CHART_LAYOUT`):

```python
# Plotly modebar configuration
# Show modebar only on hover with just zoom in/out buttons
MODEBAR_CONFIG = {
    "displayModeBar": "hover",  # Show only on hover
    "displaylogo": False,  # Hide Plotly logo
    "modeBarButtonsToRemove": [
        # Remove ALL buttons except zoomIn2d and zoomOut2d
        "pan2d",
        "zoom2d",
        "select2d",
        "lasso2d",
        "autoScale2d",
        "resetScale2d",
        "hoverClosestCartesian",
        "hoverCompareCartesian",
        "toggleSpikelines",
        "toggleHover",
    ],
}
```

**Testing:**
- Verify the constant is importable: `from tournament_visualizer.config import MODEBAR_CONFIG`
- Verify it's a dictionary with the correct keys

**Commit message:**
```
feat: Add centralized modebar configuration constant

Add MODEBAR_CONFIG to config.py to define standard modebar behavior:
- Display only on hover
- Show only zoom in/out buttons
```

---

### Task 2: Update create_chart_card Function

**File:** `tournament_visualizer/components/layouts.py`

**Why:** This function is used by most charts in the application. Updating it here fixes ~90% of the modebars.

**Changes:**

1. Add import at the top (around line 12):

```python
from ..config import LAYOUT_CONSTANTS, MODEBAR_CONFIG
```

2. Replace lines 87-100 with:

```python
    chart_component = dcc.Graph(
        id=chart_id,
        style={"height": height},
        config=MODEBAR_CONFIG,
    )
```

**Before:**
```python
    chart_component = dcc.Graph(
        id=chart_id,
        style={"height": height},
        config={
            "displayModeBar": True,
            "displaylogo": False,
            "modeBarButtonsToRemove": [
                "pan2d",
                "lasso2d",
                "select2d",
                "autoScale2d",
                "resetScale2d",
            ],
        },
    )
```

**After:**
```python
    chart_component = dcc.Graph(
        id=chart_id,
        style={"height": height},
        config=MODEBAR_CONFIG,
    )
```

**Testing:**
- Run the app: `uv run python manage.py restart`
- Navigate to any match and check charts:
  - Modebar should NOT be visible by default
  - Modebar should appear when hovering over chart
  - Only zoom in/out buttons should be visible
- Test on multiple tabs: Turn Progression, Technology & Research, Yields, Player Statistics

**Commit message:**
```
feat: Update create_chart_card to use hover modebar

Replace inline config with MODEBAR_CONFIG constant.
Modebar now shows only on hover with zoom in/out buttons.
```

---

### Task 3: Update Ambition Timeline Charts

**File:** `tournament_visualizer/pages/matches.py`

**Why:** This is the only place where `dcc.Graph` is created directly without using `create_chart_card`.

**Changes:**

1. Add import at the top (around line 10):

```python
from tournament_visualizer.config import PAGE_CONFIG, MODEBAR_CONFIG
```

2. Replace line 1376:

**Before:**
```python
                                    dbc.CardBody([dcc.Graph(figure=fig)]),
```

**After:**
```python
                                    dbc.CardBody([dcc.Graph(figure=fig, config=MODEBAR_CONFIG)]),
```

**Full context (lines 1373-1377):**
```python
                            dbc.Card(
                                [
                                    dbc.CardHeader(html.H5(f"{player} - Ambitions", className="mb-0")),
                                    dbc.CardBody([dcc.Graph(figure=fig, config=MODEBAR_CONFIG)]),
                                ],
                                className="mb-3"
                            )
```

**Testing:**
- Run the app: `uv run python manage.py restart`
- Navigate to a match → Player Statistics tab
- Scroll down to Ambition Timeline charts
- Verify:
  - Modebar appears only on hover
  - Only zoom in/out buttons visible

**Commit message:**
```
feat: Add hover modebar to ambition timeline charts

Apply MODEBAR_CONFIG to directly created Graph component
in ambition timeline visualization.
```

---

### Task 4: Search for Any Other Direct dcc.Graph Usage

**Why:** Ensure we haven't missed any charts (belt-and-suspenders approach).

**Commands to run:**

```bash
# Search for any dcc.Graph usage
uv run rg "dcc\.Graph\(" tournament_visualizer/

# Search for any config= usage in Graph components
uv run rg "dcc\.Graph.*config" tournament_visualizer/
```

**Expected result:** Should only find the files we already updated.

**If new instances found:**
- Update them following the same pattern as Task 3
- Add tests
- Create a commit

**Testing:**
- Review search results
- Verify no additional instances need updating

**Commit message (if changes needed):**
```
feat: Apply hover modebar to remaining Graph components

Ensure all dcc.Graph instances use MODEBAR_CONFIG.
```

---

### Task 5: Comprehensive Visual Testing

**Why:** Plotly charts are visual components - automated tests can't fully verify the user experience.

**Testing Checklist:**

1. **Overview Page** (`/`)
   - [ ] Match Timeline chart - modebar on hover only
   - [ ] Player Performance chart - modebar on hover only
   - [ ] All other charts - modebar on hover only

2. **Matches Page** (`/matches`)
   - Select a match with complete data
   - **Turn Progression tab:**
     - [ ] Events Timeline chart - modebar on hover
     - [ ] Only zoom in/out buttons visible
   - **Technology & Research tab:**
     - [ ] Technology Tempo chart - modebar on hover
     - [ ] Law Tempo chart - modebar on hover
   - **Yields tab:**
     - [ ] All 14 yield charts - modebar on hover
     - [ ] Test at least 3 different yield types
   - **Player Statistics tab:**
     - [ ] Yields Comparison radar chart - modebar on hover
     - [ ] Ambition Summary table (not a chart, skip)
     - [ ] Ambition Timeline charts - modebar on hover

3. **Players Page** (`/players`)
   - [ ] All charts - modebar on hover

4. **Maps Page** (`/maps`)
   - [ ] All charts - modebar on hover

**Test in different browsers (if possible):**
- [ ] Chrome
- [ ] Firefox
- [ ] Safari

**Interaction testing:**
- [ ] Hover works smoothly (no flickering)
- [ ] Zoom in button works correctly
- [ ] Zoom out button works correctly
- [ ] Modebar disappears when mouse leaves chart
- [ ] No other buttons are visible

**Commit message:**
```
test: Complete visual testing of modebar changes

Verified all charts across all pages show modebar on hover
with only zoom in/out buttons.
```

---

### Task 6: Write Unit Tests for Config

**Why:** Ensure the configuration constant is correct and doesn't break in future changes.

**File:** `tests/test_config.py`

**Add these tests at the end of the file:**

```python
def test_modebar_config_structure() -> None:
    """MODEBAR_CONFIG should have correct structure and values."""
    from tournament_visualizer.config import MODEBAR_CONFIG

    # Verify it's a dictionary
    assert isinstance(MODEBAR_CONFIG, dict)

    # Verify required keys exist
    assert "displayModeBar" in MODEBAR_CONFIG
    assert "displaylogo" in MODEBAR_CONFIG
    assert "modeBarButtonsToRemove" in MODEBAR_CONFIG

    # Verify correct values
    assert MODEBAR_CONFIG["displayModeBar"] == "hover"
    assert MODEBAR_CONFIG["displaylogo"] is False
    assert isinstance(MODEBAR_CONFIG["modeBarButtonsToRemove"], list)


def test_modebar_removes_correct_buttons() -> None:
    """MODEBAR_CONFIG should remove all buttons except zoom in/out."""
    from tournament_visualizer.config import MODEBAR_CONFIG

    removed_buttons = MODEBAR_CONFIG["modeBarButtonsToRemove"]

    # These buttons MUST be removed (we don't want them)
    expected_removed = [
        "pan2d",
        "zoom2d",
        "select2d",
        "lasso2d",
        "autoScale2d",
        "resetScale2d",
        "hoverClosestCartesian",
        "hoverCompareCartesian",
        "toggleSpikelines",
        "toggleHover",
    ]

    for button in expected_removed:
        assert button in removed_buttons, f"{button} should be removed"

    # These buttons MUST NOT be removed (we want to keep them)
    # Note: If a button isn't in modeBarButtonsToRemove, it will be shown
    assert "zoomIn2d" not in removed_buttons
    assert "zoomOut2d" not in removed_buttons
```

**Run tests:**

```bash
# Run just the new tests
uv run pytest tests/test_config.py::test_modebar_config_structure -v
uv run pytest tests/test_config.py::test_modebar_removes_correct_buttons -v

# Run all config tests
uv run pytest tests/test_config.py -v
```

**Expected output:**
```
tests/test_config.py::test_modebar_config_structure PASSED
tests/test_config.py::test_modebar_removes_correct_buttons PASSED
```

**Commit message:**
```
test: Add unit tests for MODEBAR_CONFIG

Verify modebar configuration has correct structure and
removes all buttons except zoom in/out.
```

---

### Task 7: Update Documentation

**Why:** Help future developers understand the modebar configuration.

**File:** `docs/developer-guide.md`

**Add this section** (find an appropriate place, maybe after chart configuration section):

```markdown
### Plotly Modebar Configuration

All Plotly charts in the application use a standardized modebar configuration defined in `tournament_visualizer/config.py`:

```python
MODEBAR_CONFIG = {
    "displayModeBar": "hover",  # Show only on hover
    "displaylogo": False,       # Hide Plotly logo
    "modeBarButtonsToRemove": [...],  # Remove all except zoom in/out
}
```

**Usage:**

1. **For charts using `create_chart_card()`** (preferred):
   ```python
   from tournament_visualizer.components.layouts import create_chart_card

   create_chart_card(
       title="My Chart",
       chart_id="my-chart",
       height="400px",
   )
   # Config is automatically applied
   ```

2. **For direct `dcc.Graph` usage** (when `create_chart_card` isn't suitable):
   ```python
   from dash import dcc
   from tournament_visualizer.config import MODEBAR_CONFIG

   dcc.Graph(
       figure=fig,
       config=MODEBAR_CONFIG,
   )
   ```

**Available Buttons:**
- `zoomIn2d` - Zoom in (✅ shown)
- `zoomOut2d` - Zoom out (✅ shown)
- All others removed

**Why hover-only?**
- Cleaner UI - toolbar doesn't clutter the chart
- Still accessible when needed
- Consistent with modern web app design patterns
```

**Commit message:**
```
docs: Document Plotly modebar configuration

Add section explaining MODEBAR_CONFIG usage and design decisions.
```

---

## Testing Strategy

### Unit Tests
- ✅ Config structure tests (Task 6)
- ✅ Button removal verification (Task 6)

### Integration Tests
- Visual testing with running application (Task 5)
- Cross-browser testing (Task 5)

### Regression Testing
```bash
# Run ALL existing tests to ensure nothing broke
uv run pytest -v

# Run with coverage to check we didn't miss anything
uv run pytest --cov=tournament_visualizer --cov-report=term-missing
```

**Expected:** All existing tests should pass.

---

## Rollback Procedure

If issues are discovered after deployment:

### Quick Rollback (revert all commits)

```bash
# Find the commits
git log --oneline -n 7

# Revert them in reverse order
git revert <commit-7-hash>  # Task 7 docs
git revert <commit-6-hash>  # Task 6 tests
git revert <commit-5-hash>  # Task 5 visual testing
git revert <commit-4-hash>  # Task 4 search
git revert <commit-3-hash>  # Task 3 matches.py
git revert <commit-2-hash>  # Task 2 layouts.py
git revert <commit-1-hash>  # Task 1 config.py
```

### Partial Rollback (keep some changes)

If the issue is specific to one file:
```bash
# Revert just that task's commit
git revert <specific-commit-hash>
```

### Emergency Hotfix

If you need to restore the old behavior immediately:

1. Edit `tournament_visualizer/config.py`:
```python
MODEBAR_CONFIG = {
    "displayModeBar": True,  # Change back to True
    "displaylogo": False,
    "modeBarButtonsToRemove": [
        "pan2d",
        "lasso2d",
        "select2d",
        "autoScale2d",
        "resetScale2d",
    ],
}
```

2. Restart the app:
```bash
uv run python manage.py restart
```

---

## Success Criteria

- [ ] All modebars display only on hover
- [ ] All modebars show only zoom in and zoom out buttons
- [ ] No modebar appears by default (when not hovering)
- [ ] All existing tests pass
- [ ] New unit tests pass
- [ ] Visual testing complete on all pages
- [ ] Documentation updated
- [ ] All commits follow conventional commit format
- [ ] No code duplication (DRY principle followed)

---

## Common Pitfalls & Troubleshooting

### Pitfall 1: Modebar still always visible
**Symptom:** Modebar shows even without hovering

**Cause:** Using old config or typo in `displayModeBar` value

**Solution:**
- Verify `displayModeBar: "hover"` (with quotes)
- Check import: `from tournament_visualizer.config import MODEBAR_CONFIG`
- Restart the app: `uv run python manage.py restart`

### Pitfall 2: Wrong buttons showing
**Symptom:** Pan, select, or other buttons still visible

**Cause:** Missing buttons in `modeBarButtonsToRemove` list

**Solution:**
- Cross-reference with the full button list in Task 1
- Ensure all buttons except `zoomIn2d` and `zoomOut2d` are in the remove list

### Pitfall 3: Buttons disappear entirely
**Symptom:** No buttons show up, even on hover

**Cause:** Accidentally removed `zoomIn2d` or `zoomOut2d`

**Solution:**
- Check `modeBarButtonsToRemove` does NOT include these buttons
- They should be the ONLY buttons NOT in the remove list

### Pitfall 4: Config not applying to all charts
**Symptom:** Some charts still have old config

**Cause:** Missed a direct `dcc.Graph` usage

**Solution:**
- Run Task 4 search commands
- Update any missed instances

### Pitfall 5: Tests failing after changes
**Symptom:** Existing tests break

**Cause:** Tests might be checking for specific modebar config

**Solution:**
- Check test output for specific failures
- Update test expectations if they were testing modebar behavior
- If tests are unrelated, investigate for unintended side effects

---

## Task Execution Order

**MUST follow this exact order:**

1. ✅ Task 1: Add config constant (foundation)
2. ✅ Task 2: Update `create_chart_card` (covers most charts)
3. ✅ Task 3: Update ambition timelines (edge case)
4. ✅ Task 4: Search for other instances (safety check)
5. ✅ Task 5: Visual testing (verification)
6. ✅ Task 6: Unit tests (automated verification)
7. ✅ Task 7: Documentation (knowledge sharing)

**Why this order?**
- Foundation first (config constant)
- High-impact changes next (most charts)
- Edge cases after main changes
- Verification before documentation
- Tests ensure changes work
- Docs help future developers

---

## Time Estimates

| Task | Estimated Time | Complexity |
|------|---------------|------------|
| Task 1: Config constant | 10 minutes | Low |
| Task 2: Update create_chart_card | 15 minutes | Low |
| Task 3: Update ambition charts | 10 minutes | Low |
| Task 4: Search for others | 15 minutes | Low |
| Task 5: Visual testing | 45 minutes | Medium |
| Task 6: Unit tests | 30 minutes | Medium |
| Task 7: Documentation | 25 minutes | Low |
| **Total** | **2.5 hours** | - |

Add 30 minutes buffer for unexpected issues = **3 hours total**

---

## Related Files Reference

### Files to Modify
- ✅ `tournament_visualizer/config.py` - Add MODEBAR_CONFIG
- ✅ `tournament_visualizer/components/layouts.py` - Update create_chart_card
- ✅ `tournament_visualizer/pages/matches.py` - Update ambition timelines
- ✅ `tests/test_config.py` - Add unit tests
- ✅ `docs/developer-guide.md` - Add documentation

### Files to Review (No Changes Expected)
- `tournament_visualizer/components/charts.py` - Chart creation functions
- `tournament_visualizer/pages/overview.py` - Uses create_chart_card
- `tournament_visualizer/pages/players.py` - Uses create_chart_card
- `tournament_visualizer/pages/maps.py` - Uses create_chart_card

### Test Files to Verify
- `tests/test_charts_yields.py` - Yield chart tests
- `tests/test_charts_law_progression.py` - Law chart tests
- All other test files should pass unchanged

---

## Pre-Implementation Checklist

Before starting, verify:
- [ ] Development environment is set up: `uv` is installed
- [ ] App runs successfully: `uv run python manage.py start`
- [ ] Tests pass: `uv run pytest -v`
- [ ] You can access the app at http://localhost:8050
- [ ] You have test data loaded (matches visible in dropdown)
- [ ] Git status is clean or changes are committed

---

## Post-Implementation Checklist

After completing all tasks:
- [ ] All unit tests pass: `uv run pytest -v`
- [ ] App starts without errors: `uv run python manage.py restart`
- [ ] Visual testing complete on all pages
- [ ] Documentation updated
- [ ] All commits follow conventional commit format
- [ ] No merge conflicts
- [ ] Ready for PR/review

---

## Notes for Code Reviewers

**What to look for:**

1. **Consistency:** All `dcc.Graph` components should use `MODEBAR_CONFIG`
2. **DRY Principle:** No duplicated config definitions
3. **Completeness:** No charts left with old config
4. **Testing:** Both unit tests and visual testing completed
5. **Documentation:** Clear explanation of the change

**Quick verification:**
```bash
# Should find ONLY the constant definition
rg "displayModeBar.*True" tournament_visualizer/

# Should find uses of MODEBAR_CONFIG
rg "MODEBAR_CONFIG" tournament_visualizer/

# Should find the new tests
rg "test_modebar" tests/
```
