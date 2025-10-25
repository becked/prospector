# Streamline CLAUDE.md Implementation Plan

> **Status**: Completed and archived (2025-10-25)
>
> CLAUDE.md has been streamlined from 1,108 lines to 358 lines (67.7% reduction).
> Content moved to appropriate guides:
> - Data Integration sections → docs/developer-guide.md
> - Override Systems → docs/developer-guide.md
> - Data Synchronization → docs/deployment-guide.md
>
> See commit history for details.

## Overview

**Problem**: CLAUDE.md is 1,108 lines (~4,300 words, ~6,000-7,000 tokens), making it:
- Token-heavy (injected into every Claude Code conversation)
- Hard to maintain (duplicate information across docs)
- Low signal-to-noise ratio (critical info buried in details)

**Goal**: Reduce CLAUDE.md to ~400-500 lines of essential conventions and critical domain knowledge, moving detailed documentation to appropriate guides.

**Success Criteria**:
- CLAUDE.md is <600 lines
- No information is lost (moved, not deleted)
- All files referenced are valid
- Documentation is better organized
- Token usage per conversation is reduced by ~70%

**Approach**:
1. Keep: Development principles, critical domain knowledge, quick commands
2. Move: Feature documentation → developer-guide.md
3. Move: Deployment workflows → deployment-guide.md
4. Move: Documentation lifecycle → docs/README.md

**Time Estimate**: 3-4 hours

---

## Task Breakdown

### Phase 1: Preparation (30 min)

#### Task 1.1: Create backup of current CLAUDE.md
**Files**: `CLAUDE.md`

**What to do**:
1. Create a backup copy:
   ```bash
   cp CLAUDE.md CLAUDE.md.backup
   ```

**Why**: Safety net in case we need to reference the original during reorganization.

**Testing**: Verify backup exists:
```bash
ls -la CLAUDE.md.backup
```

**Commit**: Not yet - just a local backup

---

#### Task 1.2: Review current developer-guide.md structure
**Files**: `docs/developer-guide.md`

**What to do**:
1. Read through `docs/developer-guide.md` to understand existing sections
2. Note the current table of contents structure
3. Identify where new sections should be added (keep logical flow)

**Why**: We need to know where to place new content without disrupting existing organization.

**Expected sections** (from current file):
- Architecture Overview
- Turn-by-Turn History
- Query Layer
- Testing
- (We'll add new sections here)

**Testing**: No testing needed - this is a review task

**Commit**: No commit - just gathering information

---

#### Task 1.3: Review current deployment-guide.md structure
**Files**: `docs/deployment-guide.md`

**What to do**:
1. Read through `docs/deployment-guide.md` to understand existing sections
2. Note where deployment-related workflows should be added
3. Verify it doesn't already contain the content we're moving

**Why**: Avoid duplication and maintain logical flow in deployment guide.

**Expected sections** (from current file):
- Prerequisites
- Initial Deployment
- Configuration
- (We'll add operation workflows here)

**Testing**: No testing needed - this is a review task

**Commit**: No commit - just gathering information

---

### Phase 2: Expand Developer Guide (90 min)

#### Task 2.1: Add "Data Integration" section to developer-guide.md
**Files**: `docs/developer-guide.md`

**What to do**:
1. Open `docs/developer-guide.md`
2. Find an appropriate location (after "Query Layer" section, before "Testing")
3. Add a new top-level section: "## Data Integration"
4. Add subsections for:
   - Participant Tracking
   - Google Drive Integration
   - Pick Order Data
   - Match Narrative Summaries

**Content to move from CLAUDE.md** (copy these sections):
- Lines 108-200: Participant Tracking (all subsections)
- Lines 249-364: Google Drive Integration (all subsections)
- Lines 634-790: Pick Order Data Integration (all subsections)
- Lines 791-882: Match Narrative Summaries (all subsections)

**How to structure it**:
```markdown
## Data Integration

This section covers how external data sources are integrated with save file data.

### Participant Tracking

The database links players across matches using Challonge participant data.

#### Key Concepts
- `player_id` is match-scoped (different ID per match)
- `participant_id` is tournament-scoped (same ID across matches)
... [rest of content from CLAUDE.md]

### Google Drive Integration

Tournament save files are stored in two locations...
... [rest of content from CLAUDE.md]

### Pick Order Data Integration

Tournament games have a draft phase...
... [rest of content from CLAUDE.md]

### Match Narrative Summaries

Tournament matches include AI-generated narrative summaries...
... [rest of content from CLAUDE.md]
```

**Why**: These are feature documentation with detailed workflows, not quick reference material. They belong in the comprehensive developer guide.

**Testing**:
1. Verify all links in moved content still work (relative paths may need adjustment)
2. Check that code blocks render correctly
3. Ensure tables display properly
```bash
# Preview in a markdown viewer or push to GitHub to see rendering
```

**Commit**:
```bash
git add docs/developer-guide.md
git commit -m "docs: Add Data Integration section to developer guide

Moved detailed feature documentation from CLAUDE.md:
- Participant Tracking workflows
- Google Drive Integration
- Pick Order Data Integration
- Match Narrative Summaries

This provides comprehensive reference without bloating CLAUDE.md."
```

---

#### Task 2.2: Add "Participant UI Integration" section to developer-guide.md
**Files**: `docs/developer-guide.md`

**What to do**:
1. Within the "Data Integration" section, expand the "Participant Tracking" subsection
2. Add a sub-subsection: "### Participant UI Integration"
3. Move content from CLAUDE.md lines 132-200

**Content structure**:
```markdown
### Participant Tracking

... [existing participant tracking content] ...

#### Participant UI Integration

The web app shows **participants** (real people), not match-scoped player instances.

**Display Strategy:**
... [content from CLAUDE.md lines 132-145]

**Key Queries:**
... [content from CLAUDE.md lines 145-161]

**Visual Indicators:**
... [content from CLAUDE.md lines 163-167]

**Data Quality:**
... [content from CLAUDE.md lines 169-200]
```

**Why**: This is detailed feature documentation showing how participant tracking surfaces in the UI.

**Testing**:
1. Verify code examples are syntax-highlighted correctly
2. Check that SQL examples render properly
3. Ensure bash command blocks display correctly

**Commit**:
```bash
git add docs/developer-guide.md
git commit -m "docs: Add Participant UI Integration details to developer guide

Moved detailed UI integration documentation from CLAUDE.md including:
- Display strategy explanation
- Key query examples
- Visual indicators
- Data quality validation

Provides comprehensive UI context for developers."
```

---

#### Task 2.3: Add "Override Systems" section to developer-guide.md
**Files**: `docs/developer-guide.md`

**What to do**:
1. Add a new top-level section after "Data Integration"
2. Title: "## Override Systems"
3. Move content from CLAUDE.md about specific override systems

**Content to move from CLAUDE.md**:
- Lines 522-602: Match Winner Overrides
- Lines 555-602: Participant Name Overrides
- Lines 604-633: Override Systems Design (keep the table in CLAUDE.md as quick reference)

**Structure**:
```markdown
## Override Systems

The application uses JSON-based override files to handle edge cases where automatic data matching fails.

### Design Principles

All override files follow a consistent design:
1. Use stable external IDs (never auto-incrementing database row IDs)
2. Survive database re-imports
3. JSON format for easy editing
4. Not in git (tournament-specific data)
5. Example templates (`.example` files)

... [rest of override systems design content]

### Match Winner Overrides

**Problem**: Some save files have incorrect winner data...
... [full content from CLAUDE.md lines 522-554]

### Participant Name Overrides

**Problem**: Save file player names often don't match...
... [full content from CLAUDE.md lines 555-602]
```

**Why**: These are detailed operational procedures for handling data quality issues, not quick reference.

**Testing**:
1. Verify JSON examples are properly formatted
2. Check that file paths are correct
3. Ensure bash examples work

**Commit**:
```bash
git add docs/developer-guide.md
git commit -m "docs: Add Override Systems section to developer guide

Moved detailed override system documentation from CLAUDE.md:
- Design principles and rationale
- Match Winner Overrides (complete workflow)
- Participant Name Overrides (complete workflow)

Provides comprehensive reference for handling data quality issues."
```

---

### Phase 3: Expand Deployment Guide (45 min)

#### Task 3.1: Add "Data Synchronization" section to deployment-guide.md
**Files**: `docs/deployment-guide.md`

**What to do**:
1. Find the appropriate location (after "Configuration" or "Secrets")
2. Add new section: "## Data Synchronization"
3. Move content from CLAUDE.md lines 202-248

**Content structure**:
```markdown
## Data Synchronization

### Overview

The server MUST be restarted after database updates!
- The app uses a persistent DuckDB connection that caches data
- Changes to the database file won't be visible until the connection is closed/reopened
- Always restart the server after importing new data

### Production Sync (Fly.io)

Use the sync script from your local machine to update production:
```bash
./scripts/sync_tournament_data.sh [app-name]
# Default app-name is "prospector"
```

This script processes data **locally** (much faster!) and then uploads to Fly.io:
... [full content from CLAUDE.md lines 210-232]

### Local Development Sync

For local development/testing, run the same workflow manually:
... [full content from CLAUDE.md lines 234-248]
```

**Why**: This is deployment/operations content, not development conventions.

**Testing**:
1. Verify bash examples are correct
2. Check that script paths are valid
```bash
# Verify script exists
ls -la scripts/sync_tournament_data.sh
```

**Commit**:
```bash
git add docs/deployment-guide.md
git commit -m "docs: Add Data Synchronization section to deployment guide

Moved production sync workflows from CLAUDE.md:
- Production sync process explanation
- Local development sync workflow
- Server restart requirements

Consolidates deployment operations in deployment guide."
```

---

#### Task 3.2: Expand existing deployment sections
**Files**: `docs/deployment-guide.md`

**What to do**:
1. Find the "Deployment" section (should already exist)
2. If content from CLAUDE.md lines 883-912 provides additional detail, integrate it
3. Check for any duplicates - keep the more detailed version

**Content to review from CLAUDE.md**:
- Lines 883-912: Deployment (Fly.io) section

**Action**:
- If deployment-guide.md is already comprehensive, **skip this task**
- If CLAUDE.md has additional useful details, integrate them
- Remove any redundant content

**Why**: Avoid duplication between CLAUDE.md quick reference and comprehensive deployment guide.

**Testing**:
```bash
# Compare the two files
diff <(grep -A 30 "^## Deployment" CLAUDE.md) <(grep -A 30 "^## " docs/deployment-guide.md)
```

**Commit** (only if changes made):
```bash
git add docs/deployment-guide.md
git commit -m "docs: Consolidate deployment instructions

Merged any additional deployment details from CLAUDE.md into
comprehensive deployment guide to avoid duplication."
```

---

### Phase 4: Update docs/README.md (30 min)

#### Task 4.1: Add "Documentation Lifecycle" section to docs/README.md
**Files**: `docs/README.md`

**What to do**:
1. The section already exists (lines 51-73)!
2. Review CLAUDE.md lines 946-1043 for any additional detail
3. If CLAUDE.md has more comprehensive content, **replace** the README section
4. Otherwise, **skip this task**

**Content to review from CLAUDE.md**:
- Lines 946-1043: Documentation Lifecycle (comprehensive)

**Why**: Documentation lifecycle is about how to maintain docs, not development conventions.

**Testing**:
```bash
# Verify README renders correctly
cat docs/README.md | grep -A 50 "Documentation Lifecycle"
```

**Commit** (only if changes made):
```bash
git add docs/README.md
git commit -m "docs: Enhance Documentation Lifecycle section

Updated from CLAUDE.md to provide more comprehensive guidance on
when to archive documentation and the archival process."
```

---

### Phase 5: Create Streamlined CLAUDE.md (60 min)

#### Task 5.1: Create new streamlined CLAUDE.md
**Files**: `CLAUDE.md` (will overwrite)

**What to do**:
1. Create a new version of CLAUDE.md with only essential content
2. Keep it under 600 lines
3. Focus on conventions, critical domain knowledge, and quick commands

**Content to KEEP in CLAUDE.md**:

```markdown
We are using uv to manage Python

## Development Principles

[KEEP lines 3-42: YAGNI, DRY, Atomic Commits, Code Comments]

## Commit Messages

[KEEP lines 29-42: Conventional format, no Claude Code attribution]

## Application Management

[KEEP lines 44-54: manage.py commands - concise version]

## Database Management

### Quick Commands

[KEEP lines 56-86: Essential backup, inspect, re-import commands]

### Validation Scripts

[KEEP lines 88-106: List of validation scripts to run]

## Critical Domain Knowledge

### Player ID Mapping

[KEEP lines 404-413: XML 0-based vs database 1-based - CRITICAL]

### Yield Value Display Scale

[KEEP lines 415-462: Raw values vs display values - CRITICAL]

### Memory Event Ownership

[KEEP lines 479-515: How MemoryData player IDs work - CRITICAL]

### Override Systems Quick Reference

[KEEP lines 604-633: Table of override systems - QUICK REFERENCE ONLY]

## Testing & Code Quality

[KEEP lines 365-400: Essential test commands, formatting, TDD principles]

## Dashboard & Chart Conventions

[KEEP lines 1044-1072: Chart title conventions]

## Chyllonge Library Notes

[KEEP lines 1073-1109: API response structure, common calls, gotchas]

## Need More Details?

For comprehensive documentation, see:
- **Architecture & Features**: `docs/developer-guide.md`
- **Deployment & Operations**: `docs/deployment-guide.md`
- **Database Changes**: `docs/migrations/`
- **Documentation Guide**: `docs/README.md`
```

**What to REMOVE** (moved to other docs):
- Detailed participant tracking workflows
- Google Drive Integration details
- Pick Order Data Integration details
- Match Narrative Summaries details
- Participant UI Integration details
- Syncing Tournament Data (production details)
- Deployment (Fly.io) comprehensive section
- Documentation Lifecycle comprehensive section
- Documentation Standards detailed guidelines
- XML Structure Notes (keep in developer-guide.md)
- Detailed override system workflows (keep table only)

**Structure of new CLAUDE.md**:
```
[Line 1-2] Tool declaration
[Line 3-42] Development Principles (40 lines)
[Line 43-54] Application Management (12 lines)
[Line 55-106] Database Management (52 lines)
[Line 107-300] Critical Domain Knowledge (~190 lines)
  - Player ID Mapping
  - Yield Display Scale
  - Memory Event Ownership
  - Override Systems Table
  - XML Structure (minimal)
[Line 301-350] Testing & Code Quality (50 lines)
[Line 351-380] Dashboard Conventions (30 lines)
[Line 381-420] Chyllonge Library Notes (40 lines)
[Line 421-440] References to other docs (20 lines)

TOTAL: ~440 lines (target <600 lines)
```

**Why**: This creates a concise, high-signal reference that Claude Code can quickly parse while keeping detailed docs separate.

**Testing**:
1. Count lines: `wc -l CLAUDE.md` (should be <600)
2. Verify all referenced files exist
3. Check that all commands are valid
```bash
# Test line count
wc -l CLAUDE.md

# Verify referenced files
ls -la docs/developer-guide.md docs/deployment-guide.md docs/README.md

# Check key sections exist
grep "## Development Principles" CLAUDE.md
grep "## Critical Domain Knowledge" CLAUDE.md
grep "## Need More Details?" CLAUDE.md
```

**Commit**: Not yet - we'll test first

---

#### Task 5.2: Test streamlined CLAUDE.md references
**Files**: `CLAUDE.md`

**What to do**:
1. Verify all file paths mentioned in CLAUDE.md exist
2. Test that all bash commands are valid syntax
3. Ensure all script references are correct

**Test commands**:
```bash
# Extract all file paths from CLAUDE.md and check they exist
grep -E '\`[a-z_]+\.py\`|\`scripts/[^`]+\`|\`data/[^`]+\`' CLAUDE.md | \
  sed 's/.*`\([^`]*\)`.*/\1/' | \
  while read file; do
    if [[ -f "$file" ]]; then
      echo "✓ $file exists"
    else
      echo "✗ $file NOT FOUND"
    fi
  done

# Verify validation scripts exist
ls -la scripts/validate_*.py

# Check example files exist
ls -la data/*.example

# Verify manage.py exists
ls -la manage.py
```

**Expected output**:
- All referenced files should exist
- No "NOT FOUND" messages

**Why**: Ensure CLAUDE.md doesn't reference non-existent files or scripts.

**Commit**: Not yet - continue to next task

---

#### Task 5.3: Create comparison document
**Files**: `docs/plans/claude-md-comparison.md` (temporary, for review only)

**What to do**:
1. Create a comparison showing what was moved where
2. This helps verify nothing was lost

**Content**:
```markdown
# CLAUDE.md Reorganization - Content Mapping

## Before: 1,108 lines
## After: ~440 lines

### Content Kept in CLAUDE.md
- Development Principles (YAGNI, DRY, etc.)
- Commit Messages format
- Application Management (manage.py commands)
- Database Management (quick commands, validation scripts)
- Critical Domain Knowledge (Player IDs, Yield Scale, Memory Events)
- Override Systems Table (quick reference)
- Testing & Code Quality
- Dashboard Conventions
- Chyllonge Library Notes

### Content Moved to docs/developer-guide.md
- Participant Tracking (detailed workflows) → Data Integration section
- Participant UI Integration → Data Integration section
- Google Drive Integration → Data Integration section
- Pick Order Data Integration → Data Integration section
- Match Narrative Summaries → Data Integration section
- Override Systems (detailed workflows) → Override Systems section

### Content Moved to docs/deployment-guide.md
- Syncing Tournament Data (production) → Data Synchronization section
- Deployment details (if any unique content)

### Content Already in docs/README.md
- Documentation Lifecycle (already present, possibly enhanced)

### Nothing Lost
All content is preserved, just relocated to appropriate comprehensive guides.
```

**Why**: Verification that reorganization is complete and correct.

**Testing**: Manual review of the comparison

**Commit**: Not committed - this is a temporary working document

---

#### Task 5.4: Final review and commit streamlined CLAUDE.md
**Files**: `CLAUDE.md`

**What to do**:
1. Do a final read-through of new CLAUDE.md
2. Verify it's concise and high-signal
3. Check line count is <600
4. Commit the changes

**Review checklist**:
- [ ] Line count <600 lines
- [ ] All file references are valid
- [ ] All commands are correct
- [ ] Critical domain knowledge is present
- [ ] References to other docs are clear
- [ ] No duplicate information from other docs

**Testing**:
```bash
# Final checks
wc -l CLAUDE.md
grep "## Need More Details?" CLAUDE.md
```

**Commit**:
```bash
git add CLAUDE.md
git commit -m "docs: Streamline CLAUDE.md to essential conventions

Reduced from 1,108 lines to ~440 lines by moving detailed
documentation to appropriate guides:

Kept in CLAUDE.md:
- Development principles (YAGNI, DRY, commits, comments)
- Commit message format
- Critical domain knowledge (player IDs, yields, memory events)
- Quick command references
- Testing conventions
- Chart and library conventions

Moved to docs/developer-guide.md:
- Participant tracking (detailed workflows)
- Google Drive integration
- Pick Order data integration
- Match narrative summaries
- Override systems (detailed)

Moved to docs/deployment-guide.md:
- Production sync workflows

This reduces token usage per conversation by ~70% while
preserving all information in appropriate guides."
```

---

### Phase 6: Verification (30 min)

#### Task 6.1: Build verification checklist
**Files**: None (testing only)

**What to do**:
1. Verify nothing was lost in the reorganization
2. Test that all moved content is accessible
3. Ensure all documentation is consistent

**Verification tests**:

```bash
# 1. Check line count reduction
echo "Old CLAUDE.md:" && wc -l CLAUDE.md.backup
echo "New CLAUDE.md:" && wc -l CLAUDE.md

# 2. Verify developer-guide.md has new sections
grep "## Data Integration" docs/developer-guide.md
grep "### Participant Tracking" docs/developer-guide.md
grep "### Google Drive Integration" docs/developer-guide.md
grep "### Pick Order Data Integration" docs/developer-guide.md
grep "### Match Narrative Summaries" docs/developer-guide.md
grep "## Override Systems" docs/developer-guide.md

# 3. Verify deployment-guide.md has new section
grep "## Data Synchronization" docs/deployment-guide.md

# 4. Check all referenced files exist
for script in $(grep -oE 'scripts/[a-z_]+\.py' CLAUDE.md | sort -u); do
  if [[ -f "$script" ]]; then
    echo "✓ $script"
  else
    echo "✗ $script MISSING"
  fi
done

# 5. Verify critical domain knowledge is preserved
grep "Player ID Mapping" CLAUDE.md
grep "Yield Value Display Scale" CLAUDE.md
grep "Memory Event Ownership" CLAUDE.md

# 6. Check for duplicate content
echo "Checking for potential duplicates..."
grep -c "Participant Tracking" CLAUDE.md docs/developer-guide.md
# Should be: 1 (or minimal) in CLAUDE.md, substantial in developer-guide.md
```

**Expected results**:
- CLAUDE.md is <600 lines
- All new sections exist in target docs
- All referenced files exist
- Critical domain knowledge is preserved in CLAUDE.md
- No significant duplication

**Why**: Ensure reorganization is complete and correct before finalizing.

**Commit**: No commit - just verification

---

#### Task 6.2: Test with actual development workflow
**Files**: None (integration testing)

**What to do**:
1. Verify the streamlined docs support common developer tasks
2. Check that essential info is quickly accessible

**Test scenarios**:

**Scenario 1: New developer needs to know commit format**
```bash
# They should find it quickly in CLAUDE.md
grep -A 10 "## Commit Messages" CLAUDE.md
# Should show conventional format clearly
```

**Scenario 2: Developer needs to understand participant tracking**
```bash
# They should be pointed to developer-guide.md
grep -A 5 "participant" CLAUDE.md
# Should reference docs/developer-guide.md

# Comprehensive info should be in developer-guide.md
grep -A 50 "### Participant Tracking" docs/developer-guide.md
```

**Scenario 3: Developer needs to sync production data**
```bash
# Should be pointed to deployment-guide.md
grep -A 3 "sync" CLAUDE.md
# Should reference docs/deployment-guide.md

# Full workflow in deployment guide
grep -A 30 "## Data Synchronization" docs/deployment-guide.md
```

**Scenario 4: Developer needs to understand player ID mapping (critical!)**
```bash
# Should find it immediately in CLAUDE.md (critical domain knowledge)
grep -A 10 "Player ID Mapping" CLAUDE.md
# Should explain 0-based vs 1-based
```

**Why**: Ensure the reorganization improves, not hinders, developer experience.

**Expected outcome**:
- Quick reference info is in CLAUDE.md
- Detailed info is in appropriate guides
- References between docs are clear

**Commit**: No commit - just testing

---

#### Task 6.3: Update documentation references if needed
**Files**: Various documentation files

**What to do**:
1. Check if any other docs reference CLAUDE.md content that moved
2. Update those references to point to new locations
3. Check docs/README.md has correct pointers

**Files to check**:
```bash
# Find any docs that reference CLAUDE.md sections
grep -r "CLAUDE.md" docs/
grep -r "see CLAUDE" docs/
```

**Potential updates needed**:
- Migration docs that reference CLAUDE.md
- README.md navigation
- Any implementation plans that reference specific CLAUDE.md sections

**Why**: Keep documentation cross-references up to date.

**Commit** (if changes made):
```bash
git add docs/
git commit -m "docs: Update cross-references after CLAUDE.md reorganization

Updated documentation references to reflect new locations:
- Detailed feature docs → developer-guide.md
- Deployment workflows → deployment-guide.md

Ensures documentation navigation remains accurate."
```

---

### Phase 7: Cleanup & Finalization (15 min)

#### Task 7.1: Remove backup and temporary files
**Files**: `CLAUDE.md.backup`, `docs/plans/claude-md-comparison.md`

**What to do**:
1. Remove the backup (original is in git history)
2. Remove any temporary comparison documents

```bash
# Remove backup
rm CLAUDE.md.backup

# Remove temporary comparison (if created)
rm -f docs/plans/claude-md-comparison.md

# Verify
git status
# Should show only committed changes, no extra files
```

**Why**: Clean up temporary files now that reorganization is complete.

**Commit**: No commit needed (just cleanup)

---

#### Task 7.2: Archive this implementation plan
**Files**: `docs/plans/streamline-claude-md-implementation-plan.md` → `docs/archive/plans/`

**What to do**:
1. Add archive note to top of this plan
2. Move to archive

```markdown
> **Status**: Completed and archived (YYYY-MM-DD)
>
> CLAUDE.md has been streamlined from 1,108 lines to ~440 lines.
> Content moved to appropriate guides. See commit history for details.
```

```bash
# Add archive note (edit file manually)
# Then move to archive
git mv docs/plans/streamline-claude-md-implementation-plan.md \
      docs/archive/plans/

git add docs/archive/plans/streamline-claude-md-implementation-plan.md
git commit -m "docs: Archive completed CLAUDE.md streamlining plan

Plan complete. CLAUDE.md reduced from 1,108 to ~440 lines.
All content preserved in appropriate guides."
```

**Why**: Follow documentation lifecycle - completed plans should be archived.

**Commit**: See above

---

#### Task 7.3: Create final summary
**Files**: None (status update)

**What to do**:
1. Review all commits made during this plan
2. Verify line count reduction achieved
3. Document final state

**Summary to create**:
```
CLAUDE.md Streamlining - Final Report

Before:
- CLAUDE.md: 1,108 lines
- Token usage: ~6,000-7,000 tokens per conversation

After:
- CLAUDE.md: ~440 lines
- Token usage: ~2,000 tokens per conversation (70% reduction)

Content Moved:
- Developer Guide: +XXX lines (data integration, override systems)
- Deployment Guide: +XX lines (sync workflows)
- docs/README.md: Enhanced documentation lifecycle

Commits:
1. docs: Add Data Integration section to developer guide
2. docs: Add Participant UI Integration details to developer guide
3. docs: Add Override Systems section to developer guide
4. docs: Add Data Synchronization section to deployment guide
5. docs: Streamline CLAUDE.md to essential conventions
6. (optional) docs: Update cross-references after CLAUDE.md reorganization
7. docs: Archive completed CLAUDE.md streamlining plan

Verification:
✓ All content preserved
✓ No broken references
✓ Line count target achieved
✓ Token usage reduced
✓ Documentation better organized
```

**Testing**: Run final checks:
```bash
# Line count
wc -l CLAUDE.md

# Git log
git log --oneline | head -10

# Verify structure
head -50 CLAUDE.md
tail -20 CLAUDE.md
```

**Commit**: No commit - just verification

---

## Testing Strategy

### Unit Testing
Not applicable - this is documentation reorganization.

### Integration Testing
Verify documentation cross-references:
```bash
# Test all file references
./scripts/test_doc_references.sh  # (if such script exists)

# Manual verification
grep -r "CLAUDE.md" docs/ | grep -v "Binary"
```

### Validation Testing
```bash
# Ensure all mentioned scripts exist
for script in $(grep -oE 'scripts/[a-z_]+\.py' CLAUDE.md); do
  test -f "$script" && echo "✓ $script" || echo "✗ $script MISSING"
done

# Ensure all mentioned data files exist
for file in $(grep -oE 'data/[a-z_]+\.json' CLAUDE.md); do
  test -f "${file}.example" && echo "✓ ${file}.example" || echo "✗ ${file}.example MISSING"
done
```

### Manual Testing
1. Read through new CLAUDE.md - should be concise and clear
2. Check developer-guide.md - should have comprehensive feature docs
3. Check deployment-guide.md - should have complete operational procedures
4. Verify docs/README.md - should guide navigation effectively

---

## Common Issues & Solutions

### Issue 1: File references break after moving content
**Symptom**: Relative paths like `../../scripts/foo.py` don't work after moving content

**Solution**:
- CLAUDE.md uses relative paths from project root: `scripts/foo.py`
- developer-guide.md is in `docs/`, so paths stay the same
- Test all paths after moving

**Prevention**: Use project-root-relative paths, not `../` paths

---

### Issue 2: Content duplication between docs
**Symptom**: Same information appears in multiple places

**Solution**:
- Keep principle/convention in CLAUDE.md (concise)
- Keep detailed how-to in developer-guide.md (comprehensive)
- Use cross-references: "See developer-guide.md for details"

**Prevention**: Follow "write once, reference elsewhere" principle

---

### Issue 3: CLAUDE.md still too long after first pass
**Symptom**: After moving content, still >600 lines

**Solution**:
1. Look for example code blocks - can they be shortened?
2. Look for repeated explanations - can they be consolidated?
3. Consider moving more content to developer-guide.md

**Prevention**: Be ruthless about "essential vs nice-to-have"

---

### Issue 4: Critical information buried in comprehensive guides
**Symptom**: Developer can't find essential info quickly

**Solution**:
- Keep truly critical info in CLAUDE.md (player ID mapping, yield scale)
- Use prominent "Need More Details?" section with clear navigation
- Ensure developer-guide.md has good table of contents

**Prevention**: Test with "new developer" scenarios

---

## Success Metrics

After completing this plan:

1. **Line count**: CLAUDE.md is <600 lines ✓
2. **Token usage**: Reduced by ~70% (from ~7,000 to ~2,000 tokens) ✓
3. **Information preservation**: No content lost ✓
4. **Organization**: Clear separation of concerns ✓
5. **Usability**: Essential info quickly accessible ✓
6. **Maintainability**: Less duplication across docs ✓

---

## Time Tracking

Estimated time: 3-4 hours

- Phase 1 (Preparation): 30 min
- Phase 2 (Developer Guide): 90 min
- Phase 3 (Deployment Guide): 45 min
- Phase 4 (docs/README.md): 30 min
- Phase 5 (Streamlined CLAUDE.md): 60 min
- Phase 6 (Verification): 30 min
- Phase 7 (Cleanup): 15 min

Total: 4 hours

---

## References

- **Claude Code Documentation**: https://docs.anthropic.com/claude/docs/claude-code
- **Markdown Best Practices**: https://www.markdownguide.org/basic-syntax/
- **Documentation Lifecycle**: `docs/README.md` (lines 51-107)
- **Current CLAUDE.md**: 1,108 lines, needs streamlining

---

## Notes for Implementation

### Key Principles

1. **Don't lose information** - Move, don't delete
2. **Maintain references** - Update cross-links
3. **Test thoroughly** - Verify file paths work
4. **Commit frequently** - After each phase
5. **Keep git history** - Original CLAUDE.md is in git

### What Makes Good CLAUDE.md Content?

**Include**:
- Conventions (commit format, code style)
- Critical domain knowledge (player IDs, yield scale)
- Quick commands (how to run tests, start server)
- Common gotchas (Chyllonge API quirks)

**Exclude**:
- Step-by-step tutorials (those are guides)
- Comprehensive feature docs (those are in developer-guide.md)
- Deployment procedures (those are in deployment-guide.md)
- Historical context (those are in archive)

### Testing Philosophy

Since this is documentation:
- No unit tests needed
- Manual verification is primary testing
- Check file references programmatically
- Validate with real developer scenarios

### Post-Implementation

After completing this plan:
1. Monitor if developers can find information easily
2. Watch for questions that indicate missing info in CLAUDE.md
3. Adjust as needed based on actual usage
4. Keep CLAUDE.md lean as project evolves
