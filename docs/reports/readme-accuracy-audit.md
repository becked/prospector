# README.md Accuracy Audit

Date: 2025-10-25
Status: Initial audit for README overhaul

## Executive Summary

The current README.md has several critical accuracy issues including incorrect script names, outdated documentation paths, missing features, and an incomplete database schema listing.

## Script Name Issues

### Line 35: Incorrect Script Name
- **Issue**: References `scripts/import_tournaments.py`
- **Actual**: Script is named `scripts/import_attachments.py`
- **Impact**: HIGH - Users following instructions will get "file not found" error
- **Fix**: Replace all occurrences with `import_attachments.py`

### Lines 41, 47, 50, 53: Repeated Script Name Error
- **Issue**: Multiple references to `import_tournaments.py` in examples
- **Actual**: Should all be `import_attachments.py`
- **Impact**: HIGH - Broken examples throughout Quick Start section

## Path Issues

### Line 198: Outdated Deployment Guide Path
- **Issue**: References `docs/deployment/flyio-deployment-guide.md`
- **Actual**: File is at `docs/deployment-guide.md` (root of docs/)
- **Impact**: HIGH - Broken link to critical documentation
- **Fix**: Update to `docs/deployment-guide.md`

### Line 199: Outdated Checklist Path
- **Issue**: References `docs/deployment/pre-deployment-checklist.md`
- **Actual**: No longer exists (archived or integrated into deployment-guide.md)
- **Impact**: MEDIUM - Broken link but not critical path
- **Fix**: Remove reference or update to archived location

### Line 200: Outdated Plan Path
- **Issue**: References `docs/plans/flyio-deployment-implementation-plan.md`
- **Actual**: File is in `docs/archive/plans/flyio-deployment-implementation-plan.md`
- **Impact**: LOW - Link to implementation plan that's been completed and archived
- **Fix**: Remove reference (implementation plans are internal docs)

## Application Launch Issues

### Line 59: Incorrect App Launch Command
- **Issue**: Shows `uv run python tournament_visualizer/app.py`
- **Actual**: Should use `uv run python manage.py start` (per CLAUDE.md conventions)
- **Impact**: MEDIUM - Direct app.py launch works but bypasses management layer
- **Fix**: Replace with `manage.py start` and add server management section

### Missing: Server Management Commands
- **Issue**: No documentation of `manage.py stop`, `manage.py restart`, etc.
- **Actual**: These commands exist and are the standard way to control the app
- **Impact**: MEDIUM - Users miss out on proper server management
- **Fix**: Add Application Management section showing all manage.py commands

## Missing Features

### Major Features Not Documented

1. **Ruler Tracking**
   - **Missing**: No mention of ruler archetype analytics
   - **Exists**: `rulers` table, ruler queries, archetype charts
   - **Migration**: `docs/migrations/003_add_rulers_table.md`
   - **Impact**: HIGH - Major feature completely undocumented

2. **Tournament Participants**
   - **Missing**: No mention of Challonge participant integration
   - **Exists**: `tournament_participants` table, sync scripts, participant linking
   - **Migration**: `docs/migrations/004_add_tournament_participants.md`
   - **Impact**: HIGH - Critical integration feature missing

3. **Pick Order Tracking**
   - **Missing**: No mention of pick/ban data
   - **Exists**: `pick_order_games` table, `sync_pick_order_data.py`, analytics
   - **Migration**: `docs/migrations/008_add_pick_order_tracking.md`
   - **Impact**: HIGH - Tournament-specific feature not mentioned

4. **Match Narratives**
   - **Missing**: No mention of AI-generated match summaries
   - **Exists**: `match_metadata` table with narrative_summary, `generate_match_narratives.py`
   - **Migration**: `docs/migrations/009_add_match_narrative_summary.md`
   - **Impact**: MEDIUM - Value-add feature missing

5. **Data Override Systems**
   - **Missing**: No mention of 4 data quality override systems
   - **Exists**: Match winner overrides, pick order overrides, GDrive mapping, participant name overrides
   - **Documentation**: `docs/developer-guide.md` has complete coverage
   - **Impact**: MEDIUM - Power user features not exposed

6. **Google Drive Integration**
   - **Missing**: No mention of alternative save file storage
   - **Exists**: GDrive download capability, mapping overrides
   - **Scripts**: `download_attachments.py`, `generate_gdrive_mapping.py`
   - **Impact**: MEDIUM - Alternative data source not documented

### Data Sources Incomplete

- **Line 249-273**: Only mentions MemoryData and LogData events
- **Missing**: Challonge API integration, Google Drive API, manual overrides
- **Fix**: Expand Data Sources section to include all 4 integration points

## Incorrect Database Schema

### Line 274-284: Incomplete Schema Listing

**Current (6 tables listed):**
- matches
- players
- game_state (doesn't exist!)
- territories
- events
- resources (doesn't exist!)

**Actual (21 tables):**
- events
- family_opinion_history
- match_metadata
- match_winners
- matches
- participant_name_overrides
- pick_order_games
- player_legitimacy_history
- player_military_history
- player_points_history
- player_statistics
- player_yield_history
- players
- religion_opinion_history
- rulers
- schema_migrations
- technology_progress
- territories
- tournament_participants
- unit_classifications
- units_produced

**Issues:**
- Lists "game_state" which doesn't exist (should be 6 history tables)
- Lists "resources" which doesn't exist (should be player_yield_history)
- Missing 15+ tables including all history tables, rulers, participants, pick order
- Impact: HIGH - Completely misleading schema representation
- Fix: Remove schema listing from README, link to developer-guide.md

## Missing Scripts/Workflows

### Sync Scripts Not Mentioned
- `sync_challonge_participants.py` - Sync tournament participants
- `sync_pick_order_data.py` - Sync pick order data
- `download_attachments.py` - Download from Challonge

### Validation Scripts Not Mentioned
- `validate_logdata.py`
- `validate_memorydata_ownership.py`
- `validate_participants.py`
- `validate_participant_ui_data.py`
- `validate_rulers.py`
- `verify_analytics.py`

**Impact**: MEDIUM - Users don't know these tools exist
**Fix**: Mention in troubleshooting or link to developer guide

## Analytics Queries Section Issues

### Lines 287-314: Limited Query Examples

**Current**: Shows only 3 query examples (law progression, tech timeline, techs at milestone)
**Actual**: 57+ query functions exist across law, tech, yield, participant, ruler, etc.
**Impact**: LOW - Examples are valid but don't represent full capability
**Fix**: Keep 1-2 examples, link to developer-guide.md for complete list

## Troubleshooting Section Issues

### Lines 316-363: Missing Common Issues

**Not Covered:**
- Port already in use (common issue, need `manage.py stop`)
- No data showing in dashboard (how to verify import)
- Module import errors after updates
- How to use validation scripts

**Impact**: MEDIUM - Users won't find solutions to common problems
**Fix**: Expand troubleshooting with top 4-5 actual issues

## Configuration Section Issues

### Lines 128-145: Environment Variables

**Current**: Shows direct app configuration via env vars
**Issue**: Doesn't match actual usage pattern (most users don't need this)
**Impact**: LOW - Adds complexity without clear benefit
**Fix**: Move to developer-guide.md, keep README focused on quick start

## Deployment Section Issues

### Lines 147-215: Too Detailed for README

**Current**: Step-by-step Fly.io deployment instructions
**Issue**: This level of detail belongs in deployment-guide.md
**Impact**: LOW - Useful but makes README too long
**Fix**: Reduce to 3-line example, link to deployment-guide.md for details

## Commands That Don't Work As Written

### Line 59: Direct app.py execution
```bash
uv run python tournament_visualizer/app.py
```
**Status**: Works but not recommended (bypasses manage.py)
**Should be**: `uv run python manage.py start`

### Lines 35-53: All import commands wrong
```bash
uv run python scripts/import_tournaments.py --directory saves/
```
**Status**: File not found error
**Should be**: `uv run python scripts/import_attachments.py --directory saves/`

### Line 357-362: Database statistics query
```python
from tournament_visualizer.data.queries import get_queries
q = get_queries()
stats = q.get_database_statistics()
print(f'Matches: {stats.get("matches_count", 0)}')
```
**Status**: Need to verify if `get_database_statistics()` method exists
**Impact**: MEDIUM - May not work as shown

## Documentation Structure Issues

### Too Many Roles

**Current README tries to be:**
1. Quick start guide
2. Comprehensive reference
3. Deployment guide
4. Development guide
5. API documentation

**Should be**: Focused quick start guide with links to detailed docs

**Impact**: HIGH - README is 394 lines, hard to scan, overwhelming for new users
**Fix**: Reduce to <200 lines, move content to appropriate docs

## Missing Quick Reference Table

**Issue**: No "I want to..." quick reference table
**Impact**: MEDIUM - Users have to read everything to find what they need
**Fix**: Add table mapping common tasks to documentation sections

## Summary Statistics

### Issues by Severity
- **CRITICAL (10)**: Broken script names, paths, missing major features
- **HIGH (5)**: Incomplete schema, missing features documentation
- **MEDIUM (8)**: Missing workflows, incomplete troubleshooting
- **LOW (4)**: Style/organization issues

### Estimated Fix Effort
- Phase 1 (Accuracy fixes): 2-4 hours
- Phase 2 (Content reorganization): 4-6 hours
- Phase 3 (Testing & validation): 2-3 hours
- **Total**: 8-13 hours

### Success Criteria for Fixed README
- [ ] Zero incorrect script names
- [ ] Zero broken documentation links
- [ ] All major features mentioned (rulers, participants, pick order, narratives)
- [ ] Complete but concise (< 200 lines)
- [ ] Clear quick start (works in < 5 minutes)
- [ ] All commands tested and working
- [ ] Links to detailed docs for deep dives

## Recommended Action

**Do NOT patch existing README** - too many systemic issues.

**Instead**: Follow the implementation plan to create new README from scratch using:
- Feature inventory (what actually exists)
- Documentation mapping (where details live)
- Tested commands (verified to work)
- Progressive disclosure (basic → detailed via links)

This audit provides the foundation for Phase 2 content design.
