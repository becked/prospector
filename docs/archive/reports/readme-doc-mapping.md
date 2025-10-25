# Documentation Mapping for README

Date: 2025-10-25
Purpose: Map README topics to detailed documentation locations

## Quick Start Topics → Where Details Live

### "How do I install dependencies?"
- **README**: Brief `uv sync` command
- **Details**: CLAUDE.md § Application Management
- **Also**: developer-guide.md § Development Practices

### "How do I import data?"
- **README**: One example with `import_attachments.py`
- **Details**: CLAUDE.md § Database Management ("Re-import data" section)
- **Also**: developer-guide.md § Data Parsing

### "How do I start the application?"
- **README**: `uv run python manage.py start`
- **Details**: CLAUDE.md § Application Management (complete manage.py command reference)

### "What database tables exist?"
- **README**: Brief mention of core tables (matches, players, events, territories)
- **Details**: developer-guide.md § Turn-by-Turn History (complete 21-table listing)
- **Also**: docs/migrations/*.md (individual schema changes)

### "How do I deploy?"
- **README**: 3-line quick deployment example
- **Details**: docs/deployment-guide.md (complete step-by-step guide)

### "What are the project conventions?"
- **README**: Not covered
- **Details**: CLAUDE.md (definitive source for all conventions)

### "How do I run tests?"
- **README**: Brief mention in development section
- **Details**: CLAUDE.md § Testing & Code Quality (complete test workflow)
- **Also**: developer-guide.md § Testing Architecture

### "What configuration options exist?"
- **README**: Not covered (too detailed)
- **Details**: developer-guide.md § Architecture Overview (config.py)
- **Also**: deployment-guide.md § Configuration Management

### "How do the override systems work?"
- **README**: Not covered (power user feature)
- **Details**: developer-guide.md § Override Systems (complete workflows for all 4)
- **Examples**: developer-guide.md § Data Integration

### "What scripts are available?"
- **README**: Import script only
- **Details**: CLAUDE.md § Database Management (validation scripts)
- **Also**: developer-guide.md § Data Integration (sync scripts)

## Features → Where Implementation Details Live

### Law Progression Analysis
- **Code**: `pages/matches.py`, `components/charts.py`, `data/queries.py`
- **Docs**: `docs/archive/plans/law-progression-visualizations-implementation-plan.md`
- **Tests**: `tests/test_charts_law_progression.py`
- **README**: Should mention 6 visualization types

### Ruler Tracking
- **Code**: `data/parser.py` (extract_rulers), `pages/overview.py`, `data/queries.py`
- **Docs**: `docs/migrations/003_add_rulers_table.md`, `developer-guide.md § Ruler Tracking`
- **Plan**: `docs/archive/plans/ruler-tracking-implementation-plan.md`
- **Tests**: `tests/test_parser_rulers.py`, `tests/test_integration_rulers.py`
- **README**: Missing! Should mention archetype analytics

### Tournament Participants
- **Code**: `data/etl.py`, `data/queries.py`
- **Docs**: `docs/migrations/004_add_tournament_participants.md`, `developer-guide.md § Tournament Participant Tracking`
- **Plan**: `docs/archive/plans/tournament-participant-tracking-implementation-plan.md`
- **Scripts**: `scripts/sync_challonge_participants.py`
- **Tests**: `tests/test_participant_*.py`
- **README**: Missing! Should mention Challonge integration

### Pick Order Tracking
- **Code**: `data/etl.py`, `pages/overview.py`
- **Docs**: `docs/migrations/008_add_pick_order_tracking.md`, `developer-guide.md § Data Integration`
- **Plan**: `docs/archive/plans/pick-order-integration-implementation-plan.md`
- **Scripts**: `scripts/sync_pick_order_data.py`
- **README**: Missing! Should mention pick/ban analytics

### Match Narratives
- **Code**: `data/database.py` (match_metadata table)
- **Docs**: `docs/migrations/009_add_match_narrative_summary.md`
- **Plan**: `docs/archive/plans/match-narrative-generation-implementation-plan.md`
- **Scripts**: `scripts/generate_match_narratives.py`
- **README**: Missing! Should mention AI summaries

### Turn-by-Turn History
- **Code**: `data/parser.py`, `data/etl.py`, 6 history tables
- **Docs**: `docs/migrations/002_add_history_tables.md`, `developer-guide.md § Turn-by-Turn History`
- **Plan**: `docs/archive/plans/turn-by-turn-history-implementation-plan.md`
- **Tests**: `tests/test_parser_history.py`, `scripts/validate_history_data.py`
- **README**: Called "game_state" (wrong!) - should link to developer guide

### Yield Display Scaling
- **Code**: All queries that return yield values
- **Docs**: `docs/archive/reports/yield-display-scale-issue.md`, `CLAUDE.md § Yield Value Display Scale`
- **Critical**: Divide by 10 for display
- **README**: Not mentioned (too technical for quick start)

### LogData Events
- **Code**: `data/parser.py` (extract_logdata_events)
- **Docs**: `docs/migrations/001_add_logdata_events.md`, `developer-guide.md § Event System Architecture`
- **Plan**: `docs/archive/plans/logdata-ingestion-implementation-plan.md`
- **Tests**: `scripts/validate_logdata.py`
- **README**: Mentions briefly, should link to developer guide

### MemoryData Events
- **Code**: `data/parser.py` (extract_memorydata_events)
- **Docs**: `CLAUDE.md § Memory Event Ownership`, `developer-guide.md § Event System Architecture`
- **Critical**: Player ownership rules
- **Tests**: `scripts/validate_memorydata_ownership.py`
- **README**: Mentions briefly, should link to developer guide

### Override Systems
- **Match Winner Overrides**: `docs/developer-guide.md § Override Systems`
- **Pick Order Overrides**: `docs/developer-guide.md § Override Systems`
- **GDrive Mapping Overrides**: `docs/developer-guide.md § Override Systems`
- **Participant Name Overrides**: `docs/developer-guide.md § Override Systems`
- **Plan**: `docs/archive/plans/standardize-override-systems-implementation-plan.md`
- **README**: Not mentioned (power user feature)

## README Content Strategy

### What README Should Cover (Brief)

**Prerequisites:**
- Python 3.9+
- uv package manager
- Save files

**Quick Start:**
- `uv sync` - Install
- `import_attachments.py` - Import data
- `manage.py start` - Launch app

**Features (High-Level Only):**
- Tournament Overview Dashboard
- Match-by-Match Analysis
- Player Performance Tracking
- Map Analytics
- Turn-by-Turn History
- Law & Tech Progression
- Ruler Archetype Analysis
- Pick Order Tracking

**Documentation Links (Progressive Disclosure):**
- New to project? → developer-guide.md
- Deploying? → deployment-guide.md
- Development? → CLAUDE.md
- Quick reference table for common tasks

**Example Usage (ONE Example):**
- Law progression query example
- Link to developer-guide.md for all 56 queries

**Common Issues (Top 4 Only):**
- Port already in use → `manage.py stop`
- No data showing → verify import
- Import errors → run with --verbose
- Module errors → `uv sync`

**Contributing:**
- Brief workflow
- Link to CLAUDE.md for conventions

### What README Should NOT Cover (Detailed Docs Only)

**Move to developer-guide.md:**
- Complete database schema (21 tables)
- All 56 query function examples
- Project structure details
- Configuration options
- Event system architecture
- Parser implementation details
- Override system workflows
- Testing architecture

**Move to deployment-guide.md:**
- Step-by-step Fly.io setup
- Volume creation
- Secrets management
- Health checks
- Monitoring
- Cost breakdowns

**Keep in CLAUDE.md:**
- Development principles (YAGNI, DRY, Atomic Commits)
- Commit message format
- Code quality standards
- Application management commands
- Database operations
- Critical domain knowledge (Player IDs, Yield scaling)
- Chart conventions

## Documentation Cross-Reference Table

For the new README, include this quick reference:

| I want to... | See this |
|-------------|----------|
| Understand architecture | [Developer Guide § Architecture](docs/developer-guide.md#architecture-overview) |
| See database schema | [Developer Guide § Turn-by-Turn History](docs/developer-guide.md#turn-by-turn-history) |
| Deploy to production | [Deployment Guide](docs/deployment-guide.md) |
| Run tests | [CLAUDE.md § Testing](CLAUDE.md#testing--code-quality) |
| Use query functions | [Developer Guide § Testing Architecture](docs/developer-guide.md#testing-architecture) |
| Understand schema changes | [docs/migrations/](docs/migrations/) |
| Configure the app | [Developer Guide § Architecture](docs/developer-guide.md#architecture-overview) |
| Manage the database | [CLAUDE.md § Database Management](CLAUDE.md#database-management) |
| Learn conventions | [CLAUDE.md](CLAUDE.md) |
| Use override systems | [Developer Guide § Override Systems](docs/developer-guide.md#override-systems) |
| Sync external data | [Developer Guide § Data Integration](docs/developer-guide.md#data-integration) |
| Understand event system | [Developer Guide § Event System](docs/developer-guide.md#event-system-architecture) |

## Verification Checklist

### All Links in New README Must Point To:

**Existing Docs:**
- [X] docs/developer-guide.md (not docs/development/)
- [X] docs/deployment-guide.md (not docs/deployment/)
- [X] CLAUDE.md (root level)
- [X] docs/migrations/ (directory exists)
- [X] docs/README.md (documentation guide)

**Archived Docs (Don't Link From README):**
- [X] docs/archive/plans/* - Implementation plans (internal)
- [X] docs/archive/deployment/* - Old deployment docs (obsolete)

**Non-Existent Paths (Avoid):**
- [X] docs/deployment/ - Directory doesn't exist
- [X] docs/deployment/pre-deployment-checklist.md - Archived or deleted
- [X] docs/plans/flyio-deployment-implementation-plan.md - In archive

## README Structure Alignment

### README (Quick Start Guide)
- Title + Description (1-2 sentences)
- Features (bullet points, no details)
- Prerequisites (3 items)
- Quick Start (3 steps)
- Documentation Links (table + brief sections)
- Example Usage (1 example)
- Common Issues (top 4)
- Contributing (brief)
- License + About

### CLAUDE.md (Developer Conventions)
- Development principles
- Commit messages
- Application management
- Database management
- Critical domain knowledge
- Testing & quality
- Chart conventions
- "Need More Details?" → Points to other docs

### developer-guide.md (Technical Reference)
- Architecture overview
- Turn-by-turn history (complete schema)
- Event system architecture
- Ruler tracking
- Tournament participants
- Data integration
- Override systems
- Testing architecture
- Code quality standards

### deployment-guide.md (Operations)
- Prerequisites
- Initial deployment
- Subsequent deployments
- Configuration
- Data synchronization
- Troubleshooting
- Monitoring
- Costs

## Summary

**README Focus**: Get new users running in <5 minutes, then point to detailed docs

**Documentation Hierarchy**:
1. README.md - Quick start (< 200 lines)
2. CLAUDE.md - Conventions and domain knowledge
3. developer-guide.md - Technical reference
4. deployment-guide.md - Operations guide
5. docs/migrations/ - Schema change history
6. docs/archive/ - Historical context

**Key Principle**: DRY - Don't duplicate content, link to authoritative source
