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

**Plans** (29 files):
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

**Reports** (5 files):
- Early save file analysis
- Militia analysis
- Match page enhancements
- Turn-by-turn history analytics
- Pick order visualization ideas

**Issues** (5 files):
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
