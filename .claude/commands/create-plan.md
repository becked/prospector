$1
I need your help to write out a comprehensive implementation plan

---

## CRITICAL: Pre-Planning Requirements (DO THESE FIRST!)

**Before writing any code examples or implementation tasks, you MUST:**

### 1. Review Project Architecture

**Read `CLAUDE.md` - "Architecture Overview" section** to understand:
- Data layer structure (queries, parser, database, ETL)
- UI layer structure (pages, charts, layouts, callbacks)
- UI conventions (no chart titles, component IDs, empty states, etc.)
- Testing patterns
- Cross-cutting concerns (config, logging, type hints)

This provides the roadmap for where different types of code belong.

### 2. Explore Existing Patterns

Search the codebase for similar functionality and document what you find:

**For Data Features:**
- Query patterns in `tournament_visualizer/data/queries.py`
- Parser patterns in `tournament_visualizer/data/parser.py`
- Database operations in `tournament_visualizer/data/database.py`
- ETL pipeline in `tournament_visualizer/data/etl.py`

**For UI Features:**
- Chart patterns in `tournament_visualizer/charts.py` (60+ examples)
- Layout patterns in `tournament_visualizer/layouts.py` (reusable components)
- Page patterns in `tournament_visualizer/pages/*.py` (callbacks, routing)
- Existing similar charts or pages

**For All Features:**
- Test patterns in `tests/` (mirror package structure)
- Configuration in `tournament_visualizer/config.py`

### 3. Document Findings in Task 0

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

### 4. Follow Existing Patterns (Default Behavior)

**Default**: Match the existing codebase architecture and style.

**Only deviate if you have a compelling reason**
**If deviating**: Add an "Architecture Decision" section explaining:
- What existing pattern you're NOT following
- Why deviation is justified
- What new pattern you're using instead

### 5. Reference Existing Code Explicitly

Show the engineer examples with specific locations:
- ✅ "Follow the pattern from `extract_players()` at parser.py:456"
- ✅ "Use bulk insert like `bulk_insert_events()` at database.py:789"
- ✅ "Add chart to Overview page Performance tab like `create_player_comparison()` at charts.py:234"
- ❌ "Follow existing patterns" (too vague)

### 6. Code Examples Must Match Existing Style

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
