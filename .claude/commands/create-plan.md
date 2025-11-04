$1
I need your help to write out a comprehensive implementation plan

---

## CRITICAL: Pre-Planning Requirements (DO THESE FIRST!)

**Before writing any code examples or implementation tasks, you MUST:**

### 1. Determine Feature Type

**First, identify what type of feature you're planning:**

- **Data Feature**: Adding/modifying data extraction, queries, database schema, ETL
- **UI Feature**: Adding/modifying charts, pages, layouts, dashboards
- **Full-Stack Feature**: Requires both data and UI changes

**The feature type determines which files you need to read in the next steps.**

### 2. Review Project Architecture (Conditional)

Read the Architecture Overview section of `CLAUDE.md`, focusing on relevant sections:

**For Data Features:**
- Data layer structure (queries, parser, database, ETL)
- Testing patterns
- Cross-cutting concerns (config, logging, type hints)

**For UI Features:**
- UI layer structure (pages, charts, layouts, callbacks)
- UI conventions (no chart titles, component IDs, empty states, etc.)
- Testing patterns
- Cross-cutting concerns (config, logging, type hints)

**For Full-Stack Features:**
- Read all sections - you need to understand both data and UI layers

This provides the roadmap for where different types of code belong.

### 3. Explore Existing Patterns (Conditional)

Search the codebase for similar functionality and document what you find.

**For Data Features - READ THESE FILES:**
- `tournament_visualizer/data/queries.py` - Study TournamentQueries class methods, return types (DataFrames)
- `tournament_visualizer/data/parser.py` - Study SaveGameParser methods, XML extraction patterns
- `tournament_visualizer/data/database.py` - Study bulk insert methods, transaction patterns
- `tournament_visualizer/data/etl.py` - Study ETL pipeline orchestration
- `docs/schema.sql` - Understand database schema
- `tests/test_queries.py`, `tests/test_parser.py` - Study test patterns

**For UI Features - READ THESE FILES:**
- `tournament_visualizer/charts.py` - Study 3-5 similar chart examples (CRITICAL: find charts similar to what you're building)
- `tournament_visualizer/layouts.py` - Study reusable component functions
- `tournament_visualizer/pages/page_*.py` - Find and study the most similar page/tab
- `tournament_visualizer/config.py` - Review color schemes and chart settings
- `CLAUDE.md` "UI Conventions" section - Review no-title rule, empty states, component IDs
- `tests/test_charts.py`, `tests/test_layouts.py` - Study test patterns

**For Full-Stack Features:**
- Read files from BOTH sections above

**For All Features:**
- `tests/conftest.py` - Shared test fixtures
- `CLAUDE.md` "Development Principles" - YAGNI, DRY, commit practices

### 4. Document Findings in Task 0

Your plan MUST start with **Task 0: Discovery & Pattern Analysis** that documents what you found:

```markdown
## Task 0: Discovery & Pattern Analysis

[Include sections relevant to your feature type]

### Existing Data Patterns (if applicable)
- **File**: `tournament_visualizer/data/queries.py`
- **Structure**: [Class-based / Standalone functions]
- **Example**: `method_name()` at line XXX
- **Returns**: [DataFrame / dict / list]
- **Database access**: [self.db / direct connection]

### Existing UI Patterns (if applicable)
- **File**: `tournament_visualizer/charts.py`
- **Structure**: [Standalone functions using create_base_figure()]
- **Example**: `create_player_performance_bar()` at line XXX
- **Returns**: [plotly.graph_objects.Figure]
- **Empty handling**: [Returns create_empty_figure() if df.empty]

### Existing Layout Patterns (if applicable)
- **File**: `tournament_visualizer/layouts.py`
- **Example**: `create_chart_card()` at line XXX
- **Pattern**: [Card with header, chart div, optional controls]

### Existing Callback Patterns (if applicable)
- **File**: `tournament_visualizer/pages/page_*.py`
- **Pattern**: [Callbacks with type hints, prevent_initial_call usage]
- **Example**: `update_charts()` at line XXX

### Architecture Decisions
- **Decision**: [Follow existing pattern / Deviate from existing pattern]
- **Rationale**: [Explain why - required if deviating]
- **UI Conventions**: [Confirm following conventions from CLAUDE.md or justify deviation]
```

### 5. Follow Existing Patterns (Default Behavior)

**Default**: Match the existing codebase architecture and style.

**Only deviate if you have a compelling reason**
**If deviating**: Add an "Architecture Decision" section explaining:
- What existing pattern you're NOT following
- Why deviation is justified
- What new pattern you're using instead

### 6. Reference Existing Code Explicitly

Show the engineer examples with specific locations:
- ✅ "Follow the pattern from `extract_players()` at parser.py:456"
- ✅ "Use bulk insert like `bulk_insert_events()` at database.py:789"
- ✅ "Add chart to Overview page Performance tab like `create_player_comparison()` at charts.py:234"
- ❌ "Follow existing patterns" (too vague)

### 7. Code Examples Must Match Existing Style

All code examples in your plan must:
- Use the same architectural patterns (class methods vs functions)
- Use the same naming conventions
- Use the same return types
- Use the same database access patterns
- Follow UI conventions from CLAUDE.md (no chart titles, empty state handling, etc.)

---

## Plan Content Requirements

Assume that the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, what code to write, what tests to create, what docs they might need to check, how to test it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume they are a skilled developer, but know almost nothing about our toolset or problem domain. Assume they don't know good test design very well.

### Required Plan Structure

```markdown
# [Feature Name] Implementation Plan

## Overview
[Brief description of what we're building and why]

## Prerequisites
[What needs to be in place before starting]

## Task 0: Discovery & Pattern Analysis (15-30 min)
[Document all existing patterns as shown above - REQUIRED]

## Task 1: [First Implementation Task]

### Subtask 1.1: [Description]
**File**: `path/to/file.py`

**Why this approach**: [Reference to pattern from Task 0]

**What to do**:
1. Step-by-step instructions
2. With specific line numbers when relevant

**Code to add**:
```python
# Code example that matches existing patterns
```

**Test it**:
```bash
# How to verify this subtask works
```

**Expected output**: [What success looks like]

**Commit Point**: ✓ "commit message here"

[Repeat for each subtask]

## Common Pitfalls
[Things that typically go wrong and how to avoid them]

## Success Criteria
[Clear checklist of what "done" means]
```

### Plan Quality Checklist

Before submitting your plan, verify:

- [ ] Reviewed CLAUDE.md "Architecture Overview" section
- [ ] Task 0 exists and documents existing patterns with file paths and line numbers
- [ ] All code examples match existing architectural patterns (unless deviation is justified)
- [ ] Every deviation from existing patterns has a written justification
- [ ] File paths are specific (not "the parser file" but "tournament_visualizer/data/parser.py")
- [ ] Line numbers or function names are referenced for examples
- [ ] Test patterns match existing test structure
- [ ] Code examples follow project conventions (type hints, docstrings, etc.)
- [ ] UI features follow conventions from CLAUDE.md (no chart titles, empty states, component IDs, etc.)
- [ ] Each task has clear "how to test" instructions
- [ ] Commit messages follow conventional commit format

---

Please write out this plan, in full detail, into docs/plans/
