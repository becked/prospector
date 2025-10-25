# Documentation Organization Implementation Plan

**Status**: Active
**Created**: 2025-10-25
**Approach**: Option C - Hybrid (Pragmatic archival with navigation guide)

## Overview

This plan organizes the project's documentation to help new developers quickly understand the current state of the application without being confused by outdated or completed implementation plans.

**Goals**:
1. Archive completed implementation plans and dated reports
2. Create clear navigation for new developers
3. Preserve historical context without cluttering active docs
4. Establish documentation lifecycle guidelines

**Non-Goals** (YAGNI):
- Complex status tracking systems
- Automated validation scripts (do manually first)
- Restructuring the entire docs/ tree
- Adding frontmatter to all files

## Current State

```
docs/
├── 58 markdown files (mix of active and completed)
├── plans/ (29 files, many completed)
├── migrations/ (6 files, all relevant)
├── reports/ (5 analysis reports)
├── deployment/ (3 guides)
├── issues/ (5 issue docs)
├── old/ (2 archived files - already exists)
├── bugs/ (1 bug report)
└── reference/ (1 reference doc)
```

**Problem**: New developers can't tell what's current vs. historical.

## Implementation Phases

### Phase 1: Create Archive Structure & Quick Wins

**Goal**: Archive obvious candidates and create navigation guide.

**Estimated Time**: 1-2 hours

---

#### Task 1.1: Create archive directory structure

**What**: Set up the archive/ directory tree.

**Files to create**:
```bash
docs/archive/plans/
docs/archive/reports/
docs/archive/issues/
docs/archive/code-reviews/
docs/archive/deployment/
```

**Commands**:
```bash
cd /Users/jeff/Projects/Old\ World/miner
mkdir -p docs/archive/{plans,reports,issues,code-reviews,deployment}
```

**Test**: Verify directories exist:
```bash
ls -la docs/archive/
```

**Commit**:
```
chore: Create archive directory structure for documentation
```

---

#### Task 1.2: Archive dated code review reports

**What**: Move code review reports from October 7, 2025 to archive.

**Why**: These are point-in-time snapshots, not living documents.

**Files to move**:
- `docs/20251007-code_review_report.md`
- `docs/20251007-code_review_report-summary.md`
- `docs/20251007-code_review_report-action_items.md`

**Commands**:
```bash
git mv docs/20251007-code_review_report.md docs/archive/code-reviews/
git mv docs/20251007-code_review_report-summary.md docs/archive/code-reviews/
git mv docs/20251007-code_review_report-action_items.md docs/archive/code-reviews/
```

**Test**: Verify files moved:
```bash
ls docs/archive/code-reviews/
# Should show 3 files
ls docs/20251007-* 2>/dev/null
# Should show "No such file or directory"
```

**Commit**:
```
chore: Archive dated code review reports from 2025-10-07
```

---

#### Task 1.3: Archive root-level analysis docs

**What**: Move miscellaneous analysis docs to appropriate archive locations.

**Files to move**:

1. **To archive/reports/**:
   - `docs/save_file_analysis.md` (early analysis, superseded by reference/save-file-format.md)
   - `docs/militia_analysis.md` (specific analysis, likely superseded)
   - `docs/match_page_enhancements.md` (completed feature plan)
   - `docs/turn-by-turn-history-analytics.md` (analysis that led to implementation)
   - `docs/pick-order-data-visualization-ideas.md` (brainstorming, not implementation plan)

2. **To archive/plans/**:
   - `docs/initial-project-plan.md` (superseded by current state)
   - `docs/initial-project-plan-implementation-summary.md` (completed)
   - `docs/fixing-data-extraction-implementation-plan.md` (completed)

**Commands**:
```bash
# Move to archive/reports/
git mv docs/save_file_analysis.md docs/archive/reports/
git mv docs/militia_analysis.md docs/archive/reports/
git mv docs/match_page_enhancements.md docs/archive/reports/
git mv docs/turn-by-turn-history-analytics.md docs/archive/reports/
git mv docs/pick-order-data-visualization-ideas.md docs/archive/reports/

# Move to archive/plans/
git mv docs/initial-project-plan.md docs/archive/plans/
git mv docs/initial-project-plan-implementation-summary.md docs/archive/plans/
git mv docs/fixing-data-extraction-implementation-plan.md docs/archive/plans/
```

**Test**: Verify root docs/ is cleaner:
```bash
ls docs/*.md
# Should only show developer-guide.md and deployment-guide.md
```

**Commit**:
```
chore: Archive completed analysis and planning docs
```

---

#### Task 1.4: Archive completed issues

**What**: Move resolved issue documentation to archive.

**How to validate**: Read each issue doc and check if:
1. Issue is described in past tense or marked as resolved
2. Related code is implemented (check git log, codebase)
3. Issue is documented in CLAUDE.md as working feature

**Files in docs/issues/**:
- `database-schema-changes-impact.md`
- `database-schema-changes-impact-summary.md`
- `duckdb-cascade-removal.md`
- `missing-turn-by-turn-history.md`
- `ui-issues-report.md`

**Process for each file**:
1. Read the issue doc
2. Check git log for related commits: `git log --all --grep="<issue-keyword>"`
3. Check if feature works in current app
4. If resolved: move to archive/issues/

**Commands** (after validation):
```bash
# Example for each resolved issue:
git mv docs/issues/database-schema-changes-impact.md docs/archive/issues/
git mv docs/issues/database-schema-changes-impact-summary.md docs/archive/issues/
# ... repeat for others that are resolved
```

**Test**:
```bash
# Check remaining issues
ls docs/issues/
# Should only show unresolved issues (if any)
```

**Manual validation required**:
- Read each issue doc
- Verify resolution in codebase
- Keep any active/ongoing issues

**Commit** (one commit per issue or batch related ones):
```
chore: Archive resolved database schema issues

These issues were resolved in migrations 001-004.
```

---

#### Task 1.5: Create docs/README.md navigation guide

**What**: Create a README that helps new developers navigate documentation.

**Why**: New devs need a "start here" guide to avoid confusion.

**File to create**: `docs/README.md`

**Content structure**:
1. **Start Here** section - where to begin
2. **Active Documentation** - what's current
3. **Reference Documentation** - specs and schemas
4. **Historical Context** - when to look at archive/
5. **Documentation Lifecycle** - how we manage docs

**Implementation**:

Create `docs/README.md`:

```markdown
# Documentation Guide

Welcome! This guide helps you navigate the tournament visualizer documentation.

## Start Here

**New to the project?** Read these in order:

1. **[Developer Guide](developer-guide.md)** - Architecture, development workflow, database operations
2. **[Deployment Guide](deployment-guide.md)** - How to deploy to Fly.io
3. **[CLAUDE.md](../CLAUDE.md)** - Project conventions and feature documentation

## Active Documentation

### Essential Guides
- **[developer-guide.md](developer-guide.md)** - Core development reference (architecture, database, testing)
- **[deployment-guide.md](deployment-guide.md)** - Production deployment on Fly.io

### Schema & Structure
- **[migrations/](migrations/)** - Database schema changes (historical record, all relevant)
  - Numbered sequentially (001, 002, etc.)
  - Each documents a specific schema change
  - Read these to understand database evolution
- **[reference/](reference/)** - Technical specifications
  - `save-file-format.md` - Old World save file XML structure

### Unresolved Items
- **[issues/](issues/)** - Active issues requiring attention
- **[bugs/](bugs/)** - Known bugs under investigation

## Historical Context (Archive)

The `archive/` directory contains **completed** work and **historical** snapshots.

**When to look here:**
- Understanding why a decision was made
- Learning how a feature was implemented
- Historical context for current architecture

**What's archived:**
- **[archive/plans/](archive/plans/)** - Completed implementation plans
- **[archive/reports/](archive/reports/)** - Analysis and investigation reports
- **[archive/issues/](archive/issues/)** - Resolved issues
- **[archive/code-reviews/](archive/code-reviews/)** - Point-in-time code reviews
- **[archive/deployment/](archive/deployment/)** - Old deployment docs

**Note:** If a feature is working and documented in CLAUDE.md, its implementation plan is likely archived.

## Documentation Lifecycle

We follow this lifecycle to keep docs current:

### Active Documentation
- Living documents that reflect current state
- Updated as code changes
- Examples: developer-guide.md, CLAUDE.md, migrations/

### Planning Documents
- Implementation plans live in `plans/` during development
- Once feature is complete and documented in CLAUDE.md, move to `archive/plans/`
- Include pointer to relevant CLAUDE.md section

### Issue Tracking
- Issues live in `issues/` while unresolved
- Once resolved, move to `archive/issues/` with resolution notes

### Reports & Analysis
- Point-in-time investigations and analysis
- Usually archived after decisions are implemented
- Preserved for historical context

## Finding Information

**"How do I develop this app?"**
→ Read [developer-guide.md](developer-guide.md)

**"How do I deploy?"**
→ Read [deployment-guide.md](deployment-guide.md)

**"What are the project conventions?"**
→ Read [../CLAUDE.md](../CLAUDE.md)

**"How does feature X work?"**
→ Check [../CLAUDE.md](../CLAUDE.md) first, then [developer-guide.md](developer-guide.md)

**"Why was this designed this way?"**
→ Check [archive/plans/](archive/plans/) or [archive/reports/](archive/reports/)

**"What changed in the database?"**
→ Read [migrations/](migrations/) in order

**"Where's the save file format?"**
→ [reference/save-file-format.md](reference/save-file-format.md)

## Contributing to Documentation

When working on features:

1. **Create implementation plan** in `plans/` during development
2. **Document in CLAUDE.md** when feature is complete
3. **Archive implementation plan** to `archive/plans/`
4. **Update developer-guide.md** if architecture changes
5. **Create migration doc** if schema changes

See [../CLAUDE.md](../CLAUDE.md) for commit message conventions and development principles.
```

**Commands**:
```bash
# Create the file (use Write tool)
# Content shown above
```

**Test**:
```bash
# Verify file exists and renders properly
cat docs/README.md

# Check markdown rendering (if you have a markdown viewer)
# or just open in your editor/IDE
```

**Commit**:
```
docs: Add navigation guide for documentation structure

Helps new developers understand what's active vs. archived.
```

---

### Phase 2: Validate and Archive Implementation Plans

**Goal**: Systematically review each implementation plan and archive completed ones.

**Estimated Time**: 2-3 hours

**Process**: For each plan, validate if it's completed by checking:
1. Feature documented in CLAUDE.md
2. Related code exists in codebase
3. Related tests exist
4. Migration docs created (if schema changes)

---

#### Task 2.1: Create validation checklist template

**What**: Create a simple checklist to validate each implementation plan.

**Why**: Ensures consistent validation process, less likely to miss something.

**File to create**: `docs/plans/VALIDATION_CHECKLIST.md` (temporary file)

**Content**:

```markdown
# Implementation Plan Validation Checklist

Use this checklist to determine if an implementation plan should be archived.

## For Each Plan

Plan file: `_______________________________`

### Completion Checks

- [ ] Feature is documented in CLAUDE.md (section: _____________)
- [ ] Code exists in codebase (files: _____________)
- [ ] Tests exist (files: _____________)
- [ ] Migration doc created (if applicable): migrations/_____.md
- [ ] Feature works in current app (manual test: _____________)

### Decision

- [ ] **Archive** - All checks pass, feature is complete
- [ ] **Keep Active** - Work is ongoing or planned
- [ ] **Delete** - Obsolete/superseded by different approach

### Archive Notes

If archiving, add brief note at top of plan:

```markdown
> **Status**: Completed and archived (YYYY-MM-DD)
>
> This feature is now documented in CLAUDE.md (section: <name>).
> See migrations/XXX.md for schema changes.
```

**Commands**:
```bash
# Create validation checklist (use Write tool)
# This is a temporary file for the validation process
```

**Test**: Read the checklist to ensure it makes sense.

**Commit**:
```
docs: Add validation checklist for implementation plans

Temporary file to guide Phase 2 validation process.
```

---

#### Task 2.2: Validate and archive LogData/MemoryData plans

**What**: Review and archive plans related to event data ingestion.

**Files to validate**:
- `plans/logdata-ingestion-implementation-plan.md`
- `plans/logdata-investigation-findings.md`
- `plans/fix-memorydata-player-id-bug.md`
- `plans/memorydata-player-ownership-fix.md`

**Validation process**:

For each file:
1. Open the plan
2. Check CLAUDE.md for related feature documentation
3. Check codebase for implementation:
   ```bash
   # Look for LogData parsing code
   grep -r "LogData" tournament_visualizer/

   # Look for MemoryData parsing code
   grep -r "MemoryData" tournament_visualizer/
   ```
4. Check migration docs: `ls docs/migrations/001*`
5. Verify in current app (run app, check if events show up)

**Expected result**: These features are implemented:
- CLAUDE.md documents LogData events (see "Data Sources" section)
- Code exists in `tournament_visualizer/data/parser.py`
- Migration 001 created events table
- Events visible in app

**Actions**:

1. Add archive note to each plan:
```markdown
> **Status**: Completed and archived (2025-10-25)
>
> LogData events are now documented in CLAUDE.md (Data Sources section).
> See migrations/001_add_logdata_events.md for schema changes.
```

2. Move to archive:
```bash
git mv docs/plans/logdata-ingestion-implementation-plan.md docs/archive/plans/
git mv docs/plans/logdata-investigation-findings.md docs/archive/plans/
git mv docs/plans/fix-memorydata-player-id-bug.md docs/archive/plans/
git mv docs/plans/memorydata-player-ownership-fix.md docs/archive/plans/
```

**Test**:
```bash
# Verify files moved
ls docs/archive/plans/logdata* docs/archive/plans/*memorydata* docs/archive/plans/fix-memorydata*

# Verify originals gone
ls docs/plans/logdata* 2>/dev/null
# Should error
```

**Commit**:
```
docs: Archive completed LogData/MemoryData implementation plans

These features are complete and documented in CLAUDE.md.
See migrations/001_add_logdata_events.md.
```

---

#### Task 2.3: Validate and archive history tables plans

**What**: Review and archive plans related to turn-by-turn history implementation.

**Files to validate**:
- `plans/turn-by-turn-history-implementation-plan.md`
- `plans/turn-by-turn-history-implementation-plan-phase2-issues.md`
- `plans/turn-by-turn-history-implementation-plan-phase4-issues.md`
- `plans/turn-by-turn-history-implementation-plan-phase4-validation.md`
- `plans/fix-app-after-history-tables-implementation-plan.md`

**Validation process**:

1. Check CLAUDE.md for turn-by-turn history documentation
2. Check codebase:
   ```bash
   # Look for history table queries
   grep -r "player_yield_history" tournament_visualizer/
   grep -r "player_city_history" tournament_visualizer/
   ```
3. Check migration docs: `ls docs/migrations/002*`
4. Check if history charts exist in app:
   ```bash
   # Look for yield visualizations
   grep -r "get_yield_history" tournament_visualizer/
   ```

**Expected result**:
- CLAUDE.md documents yield display scale (see "Yield Value Display Scale" section)
- Code exists for history tables
- Migration 002 created history tables
- Yield charts visible in app

**Actions**:

1. Add archive note to each plan
2. Move to archive:
```bash
git mv docs/plans/turn-by-turn-history-implementation-plan.md docs/archive/plans/
git mv docs/plans/turn-by-turn-history-implementation-plan-phase2-issues.md docs/archive/plans/
git mv docs/plans/turn-by-turn-history-implementation-plan-phase4-issues.md docs/archive/plans/
git mv docs/plans/turn-by-turn-history-implementation-plan-phase4-validation.md docs/archive/plans/
git mv docs/plans/fix-app-after-history-tables-implementation-plan.md docs/archive/plans/
```

**Test**:
```bash
ls docs/archive/plans/turn-by-turn* docs/archive/plans/fix-app-after*
```

**Commit**:
```
docs: Archive completed turn-by-turn history plans

Feature complete. See migrations/002_add_history_tables.md.
```

---

#### Task 2.4: Validate and archive visualization plans

**What**: Review and archive plans for completed visualizations.

**Files to validate**:
- `plans/law-progression-visualizations-implementation-plan.md`
- `plans/law-progression-visualizations-summary.md`
- `plans/yields-visualization-implementation-plan.md`
- `plans/yield-display-fix-implementation-plan.md`
- `plans/plotly-modebar-hover-implementation-plan.md`

**Validation process**:

1. Check if visualizations exist in app:
   ```bash
   uv run python manage.py status
   # If not running:
   uv run python manage.py start
   # Open http://localhost:8050 and check for:
   # - Law progression charts
   # - Yield charts
   # - Interactive hover tooltips
   ```
2. Check CLAUDE.md for chart conventions
3. Check codebase for visualization code:
   ```bash
   grep -r "law_progression" tournament_visualizer/
   grep -r "yield_history" tournament_visualizer/
   ```

**Expected result**:
- Charts exist and work in app
- CLAUDE.md documents chart conventions (see "Dashboard & Chart Conventions")
- Code exists in `tournament_visualizer/ui/` modules

**Actions**:

1. Add archive notes
2. Move to archive:
```bash
git mv docs/plans/law-progression-visualizations-implementation-plan.md docs/archive/plans/
git mv docs/plans/law-progression-visualizations-summary.md docs/archive/plans/
git mv docs/plans/yields-visualization-implementation-plan.md docs/archive/plans/
git mv docs/plans/yield-display-fix-implementation-plan.md docs/archive/plans/
git mv docs/plans/plotly-modebar-hover-implementation-plan.md docs/archive/plans/
```

**Test**: Verify files moved and originals gone.

**Commit**:
```
docs: Archive completed visualization implementation plans

Charts implemented and working in app.
```

---

#### Task 2.5: Validate and archive participant tracking plans

**What**: Review and archive participant tracking feature plans.

**Files to validate**:
- `plans/tournament-participant-tracking-implementation-plan.md`
- `plans/participant-ui-integration-plan.md`
- `plans/participant-linking-queries-implementation-plan.md`

**Validation process**:

1. Check CLAUDE.md "Participant Tracking" section
2. Check migration docs: `ls docs/migrations/004*`
3. Check if participant linking works:
   ```bash
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT COUNT(*) as linked_players
   FROM players
   WHERE participant_id IS NOT NULL
   "
   ```
4. Check if participants show in app UI

**Expected result**:
- CLAUDE.md documents participant tracking extensively
- Migration 004 added tournament_participants table
- Participants linked in database
- UI shows participants correctly

**Actions**:

1. Add archive notes
2. Move to archive:
```bash
git mv docs/plans/tournament-participant-tracking-implementation-plan.md docs/archive/plans/
git mv docs/plans/participant-ui-integration-plan.md docs/archive/plans/
git mv docs/plans/participant-linking-queries-implementation-plan.md docs/archive/plans/
```

**Commit**:
```
docs: Archive completed participant tracking plans

Feature complete. See migrations/004_add_tournament_participants.md.
```

---

#### Task 2.6: Validate and archive ruler tracking plan

**What**: Review and archive ruler tracking feature plan.

**File to validate**:
- `plans/ruler-tracking-implementation-plan.md`

**Validation process**:

1. Check migration docs: `ls docs/migrations/003*`
2. Check if rulers table exists:
   ```bash
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   DESCRIBE rulers
   "
   ```
3. Check for ruler data:
   ```bash
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT COUNT(*) FROM rulers
   "
   ```

**Expected result**:
- Migration 003 added rulers table
- Rulers data exists in database

**Actions**:

1. Add archive note
2. Move to archive:
```bash
git mv docs/plans/ruler-tracking-implementation-plan.md docs/archive/plans/
```

**Commit**:
```
docs: Archive completed ruler tracking plan

Feature complete. See migrations/003_add_rulers_table.md.
```

---

#### Task 2.7: Validate and archive Google Drive plans

**What**: Review and archive Google Drive integration plans.

**Files to validate**:
- `plans/google-drive-integration-implementation-plan.md`
- `plans/google-drive-findings-and-recommendations.md`
- `plans/google-drive-migration-analysis.md`

**Validation process**:

1. Check CLAUDE.md "Google Drive Integration" section
2. Check if GDrive client exists:
   ```bash
   ls tournament_visualizer/data/gdrive_client.py
   ```
3. Check if mapping file exists:
   ```bash
   ls data/gdrive_match_mapping.json 2>/dev/null
   # May not exist if not generated yet, that's OK
   ```
4. Check if scripts exist:
   ```bash
   ls scripts/generate_gdrive_mapping.py
   ls scripts/download_attachments.py
   ```

**Expected result**:
- CLAUDE.md extensively documents GDrive integration
- Code exists for GDrive client
- Scripts exist for mapping and downloading

**Actions**:

1. Add archive notes
2. Move to archive:
```bash
git mv docs/plans/google-drive-integration-implementation-plan.md docs/archive/plans/
git mv docs/plans/google-drive-findings-and-recommendations.md docs/archive/plans/
git mv docs/plans/google-drive-migration-analysis.md docs/archive/plans/
```

**Commit**:
```
docs: Archive completed Google Drive integration plans

Feature complete and documented in CLAUDE.md.
```

---

#### Task 2.8: Validate and archive pick order plans

**What**: Review and archive pick order tracking feature plan.

**File to validate**:
- `plans/pick-order-integration-implementation-plan.md`

**Validation process**:

1. Check CLAUDE.md "Pick Order Data Integration" section
2. Check migration docs: `ls docs/migrations/008*`
3. Check if pick order data exists:
   ```bash
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT COUNT(*) FROM pick_order_games
   "
   ```
4. Check if pick order fields exist in matches:
   ```bash
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   DESCRIBE matches
   " | grep picker
   ```

**Expected result**:
- CLAUDE.md documents pick order extensively
- Migration 008 added pick order tracking
- Pick order data exists in database

**Actions**:

1. Add archive note
2. Move to archive:
```bash
git mv docs/plans/pick-order-integration-implementation-plan.md docs/archive/plans/
```

**Commit**:
```
docs: Archive completed pick order integration plan

Feature complete. See migrations/008_add_pick_order_tracking.md.
```

---

#### Task 2.9: Validate and archive override system plans

**What**: Review and archive plans for override systems (winner, pick order, participant names, GDrive mapping).

**Files to validate**:
- `plans/match-winner-override-implementation-plan.md`
- `plans/standardize-override-systems-implementation-plan.md`

**Validation process**:

1. Check CLAUDE.md for override system documentation:
   - "Match Winner Overrides" section
   - "Participant Name Overrides" section
   - "Override Systems Design" section
2. Check if override files exist:
   ```bash
   ls data/*.json.example | grep override
   ```
3. Check if override loading code exists:
   ```bash
   grep -r "override" tournament_visualizer/data/parser.py
   ```

**Expected result**:
- CLAUDE.md documents all override systems
- Example override files exist
- Code loads and applies overrides

**Actions**:

1. Add archive notes
2. Move to archive:
```bash
git mv docs/plans/match-winner-override-implementation-plan.md docs/archive/plans/
git mv docs/plans/standardize-override-systems-implementation-plan.md docs/archive/plans/
```

**Commit**:
```
docs: Archive completed override system plans

Override systems complete and documented in CLAUDE.md.
```

---

#### Task 2.10: Validate and archive narrative generation plan

**What**: Review and archive match narrative generation plan.

**File to validate**:
- `plans/match-narrative-generation-implementation-plan.md`

**Validation process**:

1. Check CLAUDE.md "Match Narrative Summaries" section
2. Check migration docs: `ls docs/migrations/009*`
3. Check if narrative code exists:
   ```bash
   ls tournament_visualizer/data/narrative_generator.py
   ls tournament_visualizer/data/anthropic_client.py
   ```
4. Check if narratives exist:
   ```bash
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT COUNT(*)
   FROM matches
   WHERE narrative_summary IS NOT NULL
   "
   ```

**Expected result**:
- CLAUDE.md documents narrative generation
- Migration 009 added narrative_summary column
- Code exists for generation
- Some matches have narratives

**Actions**:

1. Add archive note
2. Move to archive:
```bash
git mv docs/plans/match-narrative-generation-implementation-plan.md docs/archive/plans/
```

**Commit**:
```
docs: Archive completed narrative generation plan

Feature complete. See migrations/009_add_match_narrative_summary.md.
```

---

#### Task 2.11: Validate and archive deployment plans

**What**: Review and archive Fly.io deployment plans.

**File to validate**:
- `plans/flyio-deployment-implementation-plan.md`

**Validation process**:

1. Check if app is deployed:
   ```bash
   fly status -a prospector
   # Should show running app (if you have access)
   ```
2. Check CLAUDE.md "Deployment (Fly.io)" section
3. Check deployment-guide.md exists and is comprehensive

**Expected result**:
- App is deployed to Fly.io
- CLAUDE.md documents deployment
- deployment-guide.md is comprehensive

**Actions**:

1. Add archive note
2. Move to archive:
```bash
git mv docs/plans/flyio-deployment-implementation-plan.md docs/archive/plans/
```

**Commit**:
```
docs: Archive completed Fly.io deployment plan

Deployment complete. See deployment-guide.md.
```

---

#### Task 2.12: Archive deployment/ subdirectory

**What**: Archive old deployment docs that are superseded by deployment-guide.md.

**Files to move**:
- `deployment/flyio-deployment-guide.md` (superseded by root deployment-guide.md)
- `deployment/implementation-review.md` (post-implementation review)
- `deployment/pre-deployment-checklist.md` (one-time checklist)

**Validation**:
1. Read root `deployment-guide.md`
2. Verify it's comprehensive and current
3. Check if deployment/ files are redundant or historical

**Commands**:
```bash
git mv docs/deployment/flyio-deployment-guide.md docs/archive/deployment/
git mv docs/deployment/implementation-review.md docs/archive/deployment/
git mv docs/deployment/pre-deployment-checklist.md docs/archive/deployment/

# Remove empty directory
rmdir docs/deployment/
```

**Test**:
```bash
ls docs/deployment/ 2>/dev/null
# Should show "No such file or directory"

ls docs/archive/deployment/
# Should show 3 files
```

**Commit**:
```
docs: Archive old deployment docs

Superseded by deployment-guide.md at root level.
```

---

#### Task 2.13: Validate remaining plans/ files

**What**: Check if any remaining plans should be archived or kept active.

**Files to check**:
```bash
ls docs/plans/
```

**For each remaining file**:
1. Read the plan
2. Use validation checklist (Task 2.1)
3. Determine: Archive, Keep Active, or Delete

**Likely candidates to keep active**:
- Any plans marked "Status: Active" or "Status: In Progress"
- Plans for features not yet documented in CLAUDE.md
- Plans that reference future work

**Likely candidates to archive**:
- Plans marked "Status: Complete"
- Plans for features documented in CLAUDE.md
- Plans with "implementation-summary" equivalents

**Process**:
```bash
# For each plan to archive:
# 1. Add archive note at top of file
# 2. Move to archive
git mv docs/plans/<plan-name>.md docs/archive/plans/
```

**Test**: Review remaining plans/ directory:
```bash
ls docs/plans/
# Should only show active/ongoing plans
```

**Commit** (one per batch or file):
```
docs: Archive completed <feature-name> plan

Feature complete and documented in CLAUDE.md.
```

---

#### Task 2.14: Remove validation checklist

**What**: Delete the temporary validation checklist.

**Why**: It was only needed for Phase 2 validation process.

**Commands**:
```bash
git rm docs/plans/VALIDATION_CHECKLIST.md
```

**Commit**:
```
docs: Remove temporary validation checklist

Validation process complete.
```

---

### Phase 3: Establish Documentation Lifecycle Guidelines

**Goal**: Add guidelines to CLAUDE.md so future work follows the same pattern.

**Estimated Time**: 30 minutes

---

#### Task 3.1: Add documentation lifecycle to CLAUDE.md

**What**: Add a new section to CLAUDE.md explaining documentation management.

**File to edit**: `CLAUDE.md`

**Location**: Add after "Documentation Standards" section (around line 500)

**Content to add**:

```markdown
## Documentation Lifecycle

We keep documentation current by archiving completed work. This helps new developers focus on what's active.

### When to Archive Documentation

**Archive immediately after completion:**

1. **Implementation plans** (`docs/plans/*.md`)
   - When feature is complete and tested
   - After feature is documented in CLAUDE.md
   - Add archive note pointing to CLAUDE.md section

2. **Issue reports** (`docs/issues/*.md`)
   - When issue is resolved
   - After fix is committed and tested
   - Add note explaining resolution

3. **Analysis reports** (`docs/reports/*.md`)
   - When analysis leads to implementation
   - After decisions are made and documented
   - Keep for historical context

4. **Code reviews** (dated reports at root)
   - Always archive (they're point-in-time snapshots)
   - Move immediately after review

### Archive Process

1. **Add archive note** at top of document:
   ```markdown
   > **Status**: Completed and archived (YYYY-MM-DD)
   >
   > This feature is now documented in CLAUDE.md (section: <name>).
   > See migrations/XXX.md for schema changes (if applicable).
   ```

2. **Move to appropriate archive location**:
   ```bash
   git mv docs/plans/<name>.md docs/archive/plans/
   ```

3. **Commit with clear message**:
   ```bash
   git commit -m "docs: Archive completed <feature> plan

   Feature complete. See CLAUDE.md section '<section-name>'.
   See migrations/XXX.md for schema details."
   ```

### What Stays Active

**Never archive these:**

- `developer-guide.md` - Living architecture doc
- `deployment-guide.md` - Living deployment doc
- `CLAUDE.md` - Living conventions doc
- `migrations/*.md` - Historical record (all relevant)
- `reference/*.md` - Technical specifications
- Active implementation plans for ongoing work
- Unresolved issues

### Archive Structure

```
docs/archive/
├── plans/          # Completed implementation plans
├── reports/        # Historical analysis reports
├── issues/         # Resolved issues
├── code-reviews/   # Point-in-time reviews
└── deployment/     # Old deployment docs
```

### Finding Archived Information

New developers should read `docs/README.md` to understand the archive structure.

**Common scenarios:**

- "Why was this designed this way?" → Check `archive/plans/`
- "How was this feature built?" → Check `archive/plans/`
- "What was this bug?" → Check `archive/issues/`

### Documentation for New Features

When implementing a feature:

1. **Create implementation plan** in `docs/plans/` (optional, for complex features)
2. **Work on feature** following the plan
3. **Create migration doc** if schema changes (required)
4. **Document in CLAUDE.md** when feature is complete (required)
5. **Update developer-guide.md** if architecture changes (if needed)
6. **Archive implementation plan** to `docs/archive/plans/` (required)

**Commit messages:**
- Creating plan: `docs: Add implementation plan for <feature>`
- Archiving plan: `docs: Archive completed <feature> plan`
```

**Commands**:
```bash
# Edit CLAUDE.md (use Edit tool to insert content)
# Location: After "Documentation Standards" section
```

**Test**:
1. Read the new section
2. Verify it's clear and actionable
3. Check that it aligns with our practices

**Commit**:
```
docs: Add documentation lifecycle guidelines to CLAUDE.md

Establishes when and how to archive completed documentation.
```

---

#### Task 3.2: Update docs/README.md with final structure

**What**: Update the README to reflect the final state after archival.

**File to edit**: `docs/README.md`

**Changes needed**:
1. Update file counts in "What's archived" section
2. Add any new patterns discovered during Phase 2
3. Verify all links work

**Commands**:
```bash
# Count archived plans
ls docs/archive/plans/*.md | wc -l

# Count active plans (if any remain)
ls docs/plans/*.md 2>/dev/null | wc -l

# Update README with actual counts (use Edit tool)
```

**Test**:
1. Click through all links in README
2. Verify structure matches actual directories
3. Check that examples are accurate

**Commit**:
```
docs: Update README with final archive structure

Reflects completed archival of implementation plans.
```

---

### Phase 4: Final Validation

**Goal**: Ensure everything is organized correctly and docs are navigable.

**Estimated Time**: 30 minutes

---

#### Task 4.1: Validate directory structure

**What**: Verify the final docs/ structure is clean and logical.

**Commands**:
```bash
# Show final structure
tree docs/ -L 2

# Or without tree command:
find docs -type f -name "*.md" | sort | head -20
```

**Expected structure**:
```
docs/
├── README.md                    # Navigation guide (NEW)
├── developer-guide.md           # Active
├── deployment-guide.md          # Active
├── archive/                     # NEW
│   ├── plans/                   # ~20-25 completed plans
│   ├── reports/                 # ~5-10 reports
│   ├── issues/                  # ~5 resolved issues
│   ├── code-reviews/            # ~3 reviews
│   └── deployment/              # ~3 old guides
├── migrations/                  # 6 migration docs (active record)
├── reference/                   # 1 reference doc
├── plans/                       # 0-3 active plans (if any)
├── issues/                      # 0-2 unresolved issues (if any)
├── reports/                     # 0 files (all archived)
└── bugs/                        # 0-1 active bugs (if any)
```

**Validation**:
- [ ] Root docs/ only has README, developer-guide, deployment-guide
- [ ] archive/ subdirectories contain completed work
- [ ] migrations/ untouched (all still relevant)
- [ ] reference/ contains active reference material
- [ ] plans/ only has active plans (if any)
- [ ] No dated files at root level
- [ ] No empty directories

**Test**:
```bash
# Check for empty directories
find docs -type d -empty

# Check for dated files at root
ls docs/2025* 2>/dev/null
# Should error (no files)
```

**Fix any issues**: Move misplaced files or remove empty dirs.

**No commit needed** (just validation).

---

#### Task 4.2: Validate all archive notes were added

**What**: Ensure all archived files have status notes at the top.

**Commands**:
```bash
# Check first 5 lines of each archived plan
for f in docs/archive/plans/*.md; do
  echo "=== $f ==="
  head -5 "$f"
  echo
done | less
```

**Expected**: Each file should start with:
```markdown
> **Status**: Completed and archived (YYYY-MM-DD)
>
> <Brief note about where to find current info>
```

**Fix any missing notes**:
1. Add the archive note to the file
2. Commit:
   ```bash
   git add docs/archive/plans/<file>.md
   git commit -m "docs: Add archive note to <file>"
   ```

---

#### Task 4.3: Test navigation for new developers

**What**: Walk through the docs as if you're a new developer.

**Process**:

1. **Start at root README**: `cat docs/README.md`
   - [ ] Clear "Start Here" section?
   - [ ] Easy to find developer-guide.md?
   - [ ] Archive explanation clear?

2. **Check developer-guide**: `cat docs/developer-guide.md | head -100`
   - [ ] Comprehensive for daily development?
   - [ ] Links to CLAUDE.md?
   - [ ] References migrations/ correctly?

3. **Check CLAUDE.md**: `cat CLAUDE.md | grep -A 20 "Documentation Lifecycle"`
   - [ ] Lifecycle guidelines clear?
   - [ ] Archive process documented?
   - [ ] Aligns with actual practice?

4. **Try finding information**:
   - "How do I deploy?" → Should find deployment-guide.md quickly
   - "How does LogData work?" → Should find CLAUDE.md, then archive/plans/ for details
   - "What changed in database?" → Should find migrations/

**If anything is confusing**: Update the relevant doc to clarify.

**Commit any fixes**:
```
docs: Clarify <aspect> in <file>

Makes it easier for new developers to find <info>.
```

---

#### Task 4.4: Run final checks

**What**: Automated checks to catch any issues.

**Commands**:

```bash
# 1. Check for broken internal links (manual check)
grep -r "docs/" docs/*.md | grep -v "archive" | grep ".md"
# Verify all non-archive links are valid

# 2. Check for TODO markers in archived files
grep -r "TODO" docs/archive/
# Should be empty or expected TODOs

# 3. Check for files in old/ directory
ls docs/old/
# Consider if these should be in archive/ instead

# 4. Verify no duplicate files
find docs -type f -name "*.md" | xargs -I {} basename {} | sort | uniq -d
# Should be empty (no duplicates)

# 5. Check git status
git status
# Should show all changes staged and committed
```

**Fix any issues found**.

---

#### Task 4.5: Create summary of changes

**What**: Document what was archived for future reference.

**File to create**: `docs/archive/ARCHIVE_LOG.md`

**Content**:

```markdown
# Documentation Archive Log

This file tracks major archival events for the documentation.

## 2025-10-25: Initial Archive Organization

**Context**: Organized docs/ to help new developers distinguish active from completed documentation.

**Approach**: Hybrid (Option C) - Archive completed plans and reports while keeping active docs current.

**Changes**:

### Created Archive Structure
- `archive/plans/` - Completed implementation plans
- `archive/reports/` - Historical analysis reports
- `archive/issues/` - Resolved issues
- `archive/code-reviews/` - Point-in-time reviews
- `archive/deployment/` - Old deployment docs

### Archived Files

**Plans** (~20-25 files):
- LogData/MemoryData ingestion plans
- Turn-by-turn history implementation plans
- Visualization implementation plans
- Participant tracking plans
- Google Drive integration plans
- Pick order tracking plans
- Override system plans
- Deployment plans
- Ruler tracking plan
- Narrative generation plan

**Reports** (~5-10 files):
- Early save file analysis
- Militia analysis
- Match page enhancements
- Turn-by-turn history analytics
- Pick order visualization ideas

**Issues** (~5 files):
- Database schema change impact reports
- DuckDB cascade removal
- Missing turn-by-turn history
- UI issues report
- MemoryData player ID mapping bug

**Code Reviews** (3 files):
- 2025-10-07 code review and action items

**Deployment** (3 files):
- Old Fly.io deployment guide (superseded)
- Implementation review
- Pre-deployment checklist

### Active Documentation Retained

- `developer-guide.md` - Architecture and workflows
- `deployment-guide.md` - Deployment procedures
- `migrations/*.md` - All 6 migration docs (historical record)
- `reference/save-file-format.md` - Save file specification
- `README.md` - Navigation guide (NEW)

### Guidelines Added

- Added "Documentation Lifecycle" section to CLAUDE.md
- Created `docs/README.md` for new developer onboarding
- Established archive process for future work

**Result**: New developers can easily find active documentation without confusion from completed work.

---

## Future Archive Events

Add entries here when archiving significant documentation in the future.

### YYYY-MM-DD: Archive Event Name

**Context**: Why archiving occurred

**Archived**: List of files/categories archived

**Reason**: Brief explanation
```

**Commands**:
```bash
# Create archive log (use Write tool)
```

**Commit**:
```
docs: Add archive log documenting initial organization

Records what was archived and why for future reference.
```

---

#### Task 4.6: Final commit and wrap-up

**What**: Ensure all changes are committed and working tree is clean.

**Commands**:

```bash
# 1. Check git status
git status

# 2. Review all commits made
git log --oneline -20

# 3. Verify working tree is clean
git status
# Should show: "nothing to commit, working tree clean"

# 4. Push changes (if appropriate)
# git push origin main
```

**Expected commits** (should have ~20-30 commits from this plan):
- Initial archive structure creation
- Individual archival commits for each category
- Documentation updates (README, CLAUDE.md)
- Archive log creation
- Any fixes/clarifications

**Validation**:
- [ ] All changes committed
- [ ] Working tree clean
- [ ] Commit messages follow conventions
- [ ] No uncommitted files

**Final Test**:
Ask someone unfamiliar with the project to:
1. Read `docs/README.md`
2. Find how to deploy the app
3. Find how the yield display scale works

If they succeed quickly, the organization is effective.

---

## Success Criteria

### Primary Goals
- [x] New developers can quickly find active documentation
- [x] Completed work is preserved but not in the way
- [x] Clear navigation guide exists (docs/README.md)
- [x] Documentation lifecycle is documented

### Metrics
- **Active docs at root**: 3 files (README, developer-guide, deployment-guide)
- **Active plans**: 0-3 files (only ongoing work)
- **Archived plans**: 20-25 files (completed features)
- **Migrations unchanged**: 6 files (all still relevant)
- **Time to find info**: < 2 minutes for common questions

### Validation Questions

**Can a new developer answer these quickly?**
1. "How do I set up the dev environment?" → developer-guide.md
2. "How do I deploy?" → deployment-guide.md
3. "What are the project conventions?" → CLAUDE.md
4. "Why was LogData designed this way?" → archive/plans/logdata-ingestion-implementation-plan.md
5. "What changed in the database?" → migrations/

**Time estimate**: 2-3 minutes per question max.

---

## Rollback Plan

If organization causes confusion or breaks something:

### Rollback Phase 1-2 (Archive structure and moves)

```bash
# 1. Find the commit before archival started
git log --oneline | grep -B 1 "Create archive directory"

# 2. Reset to before changes
git reset --hard <commit-hash>

# 3. All archived files are back in original locations
```

### Rollback Phase 3 (Documentation updates)

```bash
# If only CLAUDE.md/README updates are problematic:
git revert <commit-hash-of-documentation-update>
```

### Selective Rollback

```bash
# Restore specific archived file to active location:
git show <commit>:docs/archive/plans/file.md > docs/plans/file.md
git add docs/plans/file.md
git commit -m "docs: Restore <file> to active plans"
```

---

## Notes for Future Maintenance

### When Completing New Features

1. Document feature in CLAUDE.md
2. Create migration doc if schema changed
3. Archive implementation plan:
   ```bash
   # Add archive note
   # Move file
   git mv docs/plans/<name>.md docs/archive/plans/
   git commit -m "docs: Archive completed <name> plan"
   ```

### When Starting New Features

1. Create implementation plan in `docs/plans/`
2. Keep it there while work is ongoing
3. Reference it in commits: `part of docs/plans/<name>.md`

### Quarterly Review

Every 3 months, review:
- Are there plans in `plans/` that should be archived?
- Are there issues in `issues/` that are resolved?
- Is docs/README.md still accurate?
- Do archive/ subdirectories need reorganization?

---

## Testing Strategy

### Manual Tests

**Test 1: New Developer Onboarding**
1. Have someone unfamiliar read docs/README.md
2. Ask them to find how to deploy
3. Time: Should take < 2 minutes

**Test 2: Feature Research**
1. Ask: "How does participant tracking work?"
2. Should find: CLAUDE.md → migrations/004 → archive/plans/ for details
3. Time: Should take < 5 minutes

**Test 3: Troubleshooting**
1. Ask: "I'm getting a participant linking error, where do I look?"
2. Should find: developer-guide.md → validation scripts → CLAUDE.md troubleshooting
3. Time: Should take < 3 minutes

### Automated Checks (Optional, YAGNI for now)

Could create a script later to:
- Check all internal links are valid
- Verify all archived files have status notes
- Ensure no empty directories
- Validate consistent structure

**Don't build this now** - do it manually first, automate if needed.

---

## Related Files

### Created/Modified
- `docs/README.md` (NEW)
- `docs/archive/*` (NEW structure)
- `docs/archive/ARCHIVE_LOG.md` (NEW)
- `CLAUDE.md` (added Documentation Lifecycle section)

### Moved (20-30 files)
- `docs/plans/*.md` → `docs/archive/plans/`
- `docs/reports/*.md` → `docs/archive/reports/`
- `docs/issues/*.md` → `docs/archive/issues/`
- `docs/20251007-*.md` → `docs/archive/code-reviews/`
- `docs/deployment/*.md` → `docs/archive/deployment/`

### Unchanged (kept active)
- `docs/developer-guide.md`
- `docs/deployment-guide.md`
- `docs/migrations/*.md` (all 6 files)
- `docs/reference/save-file-format.md`
- `CLAUDE.md`

---

## Time Estimates

- **Phase 1**: 1-2 hours (structure + obvious archival)
- **Phase 2**: 2-3 hours (systematic plan validation)
- **Phase 3**: 30 minutes (guidelines)
- **Phase 4**: 30 minutes (validation)

**Total**: 4-6 hours

**Can be done in chunks** - each task is independently committable.

---

## Questions & Decisions

### Archive vs. Delete?

**Decision**: Archive everything, don't delete.

**Rationale**:
- Preserve historical context
- Disk space is cheap
- Might need to reference later
- Git history preserves anyway

### When to Archive vs. Keep Active?

**Decision**: Archive when feature is complete and documented in CLAUDE.md.

**Edge Cases**:
- Feature complete but poorly documented → Document first, then archive
- Feature partially complete → Keep active
- Feature abandoned → Archive with note explaining why

### How Much Detail in Archive Notes?

**Decision**: Brief note with pointer to current docs.

**Format**:
```markdown
> **Status**: Completed and archived (YYYY-MM-DD)
>
> Feature documented in CLAUDE.md (section: <name>).
> See migrations/XXX.md for schema changes.
```

**Don't include**:
- Full feature description (redundant)
- Implementation details (already in the plan)
- Commit hashes (use git log)

---

## Appendix: Validation Queries

### Check for Completed Features

```bash
# Does feature exist in CLAUDE.md?
grep -i "<feature-name>" CLAUDE.md

# Does migration exist?
ls docs/migrations/ | grep -i "<feature-keyword>"

# Does code exist?
find tournament_visualizer -name "*.py" -exec grep -l "<feature-keyword>" {} \;

# Do tests exist?
find tests -name "*.py" -exec grep -l "<feature-keyword>" {} \;
```

### Check Archive Completeness

```bash
# All archived plans have status notes
for f in docs/archive/plans/*.md; do
  if ! head -5 "$f" | grep -q "Status.*archived"; then
    echo "Missing status note: $f"
  fi
done

# No empty archive directories
find docs/archive -type d -empty
```

### Check Active Docs Quality

```bash
# Developer guide mentions key concepts
grep -i "duckdb\|migrations\|participants\|logdata" docs/developer-guide.md

# README has navigation sections
grep -i "start here\|active\|archive" docs/README.md

# CLAUDE.md has lifecycle section
grep -i "documentation lifecycle" CLAUDE.md
```

---

## References

- Original discussion: "Option C (Hybrid Approach)"
- CLAUDE.md conventions
- Git workflow guidelines
- Documentation Standards section
