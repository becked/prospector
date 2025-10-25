# New README Structure Design

Date: 2025-10-25
Purpose: Design the skeleton/outline for the overhauled README.md

## Design Principles

1. **Quick Start First**: Get new users running in <5 minutes
2. **Progressive Disclosure**: Basic information → Advanced details via links
3. **Accuracy**: Every command must work as written
4. **Signposting**: Clear pointers to detailed docs for deep dives
5. **Maintenance**: Easy to keep updated (no duplication)
6. **YAGNI**: Only include what users need NOW, not "might be useful"
7. **DRY**: Don't repeat information that's in other docs, link to them

## Target Metrics

- **Length**: < 200 lines (vs 394 current)
- **Quick Start Time**: < 5 minutes to running dashboard
- **Accuracy**: 100% (zero broken commands/links)
- **Feature Coverage**: All major features mentioned
- **Link Depth**: Max 1 click to detailed docs

## Proposed Structure

### 1. Title + One-Line Description

```markdown
# Old World Tournament Visualizer

Interactive Plotly Dash application for analyzing Old World tournament save files with turn-by-turn progression tracking, law/tech analytics, and player performance insights.
```

**Rationale**:
- Clear, specific description
- Mentions key technologies (Plotly Dash, Old World)
- Hints at main features (turn-by-turn, law/tech, performance)
- One sentence - scannable

### 2. Features (Brief, Bullet Points)

```markdown
## Features

### Analytics Dashboard
- **Tournament Overview**: Nation win rates, ruler archetypes, unit popularity, pick order analysis
- **Match Analysis**: Turn-by-turn progression, law/tech timelines, yield tracking (14 types)
- **Player Performance**: Win rates, civilization preferences, head-to-head comparisons
- **Map Analytics**: Territory control, strategic position impact, map-specific performance

### Data Tracking
- **Turn-by-Turn History**: 6 tracked metrics (points, yields, military, legitimacy, orders, opinions)
- **Law Progression**: 6 visualization types analyzing milestone timing and efficiency
- **Tech Research**: Complete tech tree progression and timing analysis
- **Ruler Archetypes**: Character traits, combinations, and matchup analysis
- **Pick Order**: Pick/ban tracking and win rate correlation

### Data Integration
- **Local Import**: Process Old World save files (.zip format)
- **Challonge API**: Sync tournament structure and participants
- **Google Drive**: Alternative save file storage
- **Data Quality**: 4 override systems for manual corrections
```

**Rationale**:
- Organized into 3 logical groups (Dashboard, Tracking, Integration)
- Mentions ALL major features (rulers, participants, pick order, narratives via "tracking")
- Brief but comprehensive
- No detailed explanations (that's for docs)
- Visually scannable with bold headers

### 3. Prerequisites

```markdown
## Prerequisites

- **Python 3.9+** - Required by DuckDB and type hints
- **[uv](https://docs.astral.sh/uv/)** - Modern Python package manager
- **Old World save files** - Tournament matches in `.zip` format

Optional for full features:
- **Challonge API key** - For tournament sync ([get key](https://challonge.com/settings/developer))
- **Google Drive API** - For alternative file storage
```

**Rationale**:
- Clear required vs optional
- Links to external resources
- Explains WHY each is needed
- Correct script name (saves/ not tournament files/)

### 4. Quick Start (3-Step Process)

```markdown
## Quick Start

### 1. Install Dependencies

```bash
uv sync
```

This installs Dash, Plotly, DuckDB, and all required packages.

### 2. Import Tournament Data

Place your Old World save files (`.zip` format) in the `saves/` directory, then:

```bash
uv run python scripts/import_attachments.py --directory saves/
```

**Import options:**
```bash
# Verbose output
uv run python scripts/import_attachments.py --verbose

# Force reimport (removes existing database)
uv run python scripts/import_attachments.py --force

# Dry run (preview without importing)
uv run python scripts/import_attachments.py --dry-run
```

### 3. Launch the Dashboard

```bash
uv run python manage.py start
```

Open your browser to: **http://localhost:8050**

**Server management:**
```bash
uv run python manage.py stop      # Stop server
uv run python manage.py restart   # Restart (useful after code changes)
uv run python manage.py status    # Check if running
uv run python manage.py logs      # View logs
uv run python manage.py logs -f   # Follow logs (tail -f)
```

See [CLAUDE.md § Application Management](CLAUDE.md#application-management) for details.
```

**Rationale**:
- 3 clear steps (1-2-3)
- Uses correct script name (`import_attachments.py`)
- Uses correct launch method (`manage.py start`)
- Includes common options for each step
- Links to CLAUDE.md for advanced usage
- Shows full server management (not just start)

### 5. Documentation Links

```markdown
## Documentation

### Start Here

**New to the project?**
- [Developer Guide](docs/developer-guide.md) - Architecture, database schema, ETL pipeline, testing
- [Deployment Guide](docs/deployment-guide.md) - Deploy to Fly.io with persistent storage
- [CLAUDE.md](CLAUDE.md) - Development conventions, workflows, domain knowledge

### Quick Reference

| I want to... | See this |
|-------------|----------|
| Understand database schema | [Developer Guide § Turn-by-Turn History](docs/developer-guide.md#turn-by-turn-history) |
| Run tests | [CLAUDE.md § Testing](CLAUDE.md#testing--code-quality) |
| Deploy to production | [Deployment Guide](docs/deployment-guide.md) |
| Use query functions | [Developer Guide § Testing Architecture](docs/developer-guide.md#testing-architecture) |
| Understand schema changes | [docs/migrations/](docs/migrations/) |
| Configure the app | [Developer Guide § Architecture](docs/developer-guide.md#architecture-overview) |
| Manage the database | [CLAUDE.md § Database Management](CLAUDE.md#database-management) |
| Learn project conventions | [CLAUDE.md](CLAUDE.md) |
| Use override systems | [Developer Guide § Override Systems](docs/developer-guide.md#override-systems) |
| Sync external data | [Developer Guide § Data Integration](docs/developer-guide.md#data-integration) |

### Additional Resources
- [Documentation Guide](docs/README.md) - How documentation is organized
- [Save File Format](docs/reference/save-file-format.md) - Old World XML structure
- [Active Reports](docs/reports/) - Current analysis and investigations
- [Schema Migrations](docs/migrations/) - Database change history
```

**Rationale**:
- Table format is scannable
- Links to specific sections (not just files)
- Covers common user needs
- Progressive disclosure (start here → quick ref → additional)
- All links verified to exist

### 6. Example Usage (ONE Example)

```markdown
## Example Usage

### Analyzing Law Progression

```python
from tournament_visualizer.data.queries import get_queries

# Initialize query interface
queries = get_queries()

# Get law progression for a specific match
progression = queries.get_law_progression_by_match(match_id=10)
print(progression)
# Output: DataFrame with columns: player_name, turn_to_4_laws, turn_to_7_laws, total_laws

# Get tech timeline
tech_timeline = queries.get_tech_timeline_by_match(match_id=10)
print(tech_timeline)
# Output: DataFrame with columns: player_name, turn_number, tech_name, tech_sequence
```

**See also:**
- [Developer Guide § Testing Architecture](docs/developer-guide.md#testing-architecture) - All 56 query functions
- [Developer Guide § Turn-by-Turn History](docs/developer-guide.md#turn-by-turn-history) - Database schema details
```

**Rationale**:
- Shows ONE real example (law progression - popular feature)
- Includes output format (helps users understand return values)
- Links to complete query documentation
- Demonstrates basic usage pattern
- YAGNI: Most users use dashboard, not programmatic queries

### 7. Common Issues (Top 4 Only)

```markdown
## Common Issues

### Port Already in Use

```bash
# Stop existing server
uv run python manage.py stop

# Or kill manually
lsof -ti:8050 | xargs kill
```

### No Data Showing in Dashboard

```bash
# Verify data was imported
uv run duckdb data/tournament_data.duckdb -readonly -c "SELECT COUNT(*) FROM matches"

# Should show count > 0
# If 0, reimport your data:
uv run python scripts/import_attachments.py --directory saves/ --verbose
```

### Import Errors or Parsing Failures

```bash
# Run with verbose logging
uv run python scripts/import_attachments.py --directory saves/ --verbose

# Check logs
tail -f logs/tournament_import.log

# Validate specific save file
unzip -t saves/your_match.zip
```

### Module Import Errors

```bash
# Ensure all dependencies installed
uv sync

# If still failing, try clean install
rm -rf .venv
uv sync
```

**More troubleshooting:** [Developer Guide § Common Issues](docs/developer-guide.md#common-issues--solutions)
```

**Rationale**:
- Covers actual common issues (based on user experience)
- Provides actionable solutions
- Uses correct commands (manage.py, import_attachments.py)
- Links to developer guide for complex issues
- Top 4 only (YAGNI)

### 8. Contributing

```markdown
## Contributing

We welcome contributions! Please follow these guidelines:

### Development Workflow

1. **Install dev dependencies:**
   ```bash
   uv sync --group dev
   ```

2. **Make changes following our conventions:**
   - [CLAUDE.md § Development Principles](CLAUDE.md#development-principles) - YAGNI, DRY, Atomic Commits
   - [CLAUDE.md § Commit Messages](CLAUDE.md#commit-messages) - Conventional commits format
   - [CLAUDE.md § Code Comments](CLAUDE.md#code-comments) - Explain WHY, not WHAT

3. **Run quality checks:**
   ```bash
   uv run black tournament_visualizer/
   uv run ruff check tournament_visualizer/
   uv run pytest
   ```

4. **Commit and push:**
   ```bash
   git add .
   git commit -m "feat: Add new visualization for X"
   git push origin your-branch
   ```

See [CLAUDE.md](CLAUDE.md) for detailed conventions and [Developer Guide](docs/developer-guide.md) for architecture.
```

**Rationale**:
- Concrete workflow (not vague "follow best practices")
- Links to specific convention sections
- Shows actual commands
- Points to authoritative docs

### 9. License + About

```markdown
## License

This project is licensed under the MIT License - see the LICENSE file for details.

## About Old World

Old World is a historical turn-based strategy game by Mohawk Games. This visualizer analyzes tournament save files in the standard `.zip` format exported from the game.

**More about Old World:** https://www.mohawkgames.com/oldworld/

---

**Note:** This application is not affiliated with or endorsed by Mohawk Games or the Old World development team.
```

**Rationale**:
- Standard license reference
- Clear game attribution
- Disclaimer (legal protection)
- External link to game info

## What We're REMOVING from README

### Content Moving to developer-guide.md
- Detailed project structure (lines 104-126)
- Complete database schema listing (lines 274-284)
- All 57 query examples (keep 1, lines 287-314)
- Configuration details (lines 128-145)
- MemoryData vs LogData deep dive (lines 249-273)
- Data source technical details (parsers, ETL)

### Content Moving to deployment-guide.md
- Step-by-step Fly.io deployment (lines 147-215)
- Volume creation commands
- Secrets management
- Health check configuration
- Cost breakdown details

### Content Moving to CLAUDE.md
- Development tools setup
- Testing workflow details
- Code quality tool configuration

### Content Removing Entirely
- "Dashboard Pages" section (lines 64-103) - Info is outdated, users can explore the UI
- "Performance Tips" (lines 365-370) - Generic advice, not specific to this app
- Environment variable configuration (lines 128-145) - Most users don't need this

## What We're FIXING

### Critical Fixes
- ✅ `import_tournaments.py` → `import_attachments.py` (all occurrences)
- ✅ `docs/deployment/` → `docs/deployment-guide.md`
- ✅ `tournament_visualizer/app.py` → `manage.py start`
- ✅ Missing tables in schema → Link to developer-guide.md
- ✅ Missing features → Add to features list (rulers, participants, pick order, narratives)

### Path Fixes
- ✅ `docs/deployment/flyio-deployment-guide.md` → `docs/deployment-guide.md`
- ✅ `docs/deployment/pre-deployment-checklist.md` → Remove (archived or integrated)
- ✅ `docs/plans/flyio-deployment-implementation-plan.md` → Remove (archived, internal)

### Command Fixes
- ✅ Show `manage.py` commands (not just `app.py`)
- ✅ Verify all bash commands work
- ✅ Verify all Python examples work

## Estimated Line Count

| Section | Lines |
|---------|-------|
| Title + Description | 3 |
| Features | 20 |
| Prerequisites | 8 |
| Quick Start | 35 |
| Documentation | 30 |
| Example Usage | 15 |
| Common Issues | 30 |
| Contributing | 20 |
| License + About | 10 |
| **TOTAL** | **~171 lines** |

**Target**: < 200 lines ✅
**Current README**: 394 lines
**Reduction**: 57% shorter

## Success Criteria

### Accuracy
- [ ] Zero incorrect script names
- [ ] Zero broken documentation links
- [ ] All bash commands tested and working
- [ ] All Python examples tested and working

### Completeness
- [ ] All major features mentioned (rulers, participants, pick order, narratives)
- [ ] Core workflows covered (install, import, launch)
- [ ] Common issues have solutions
- [ ] Links to detailed docs for deep dives

### Usability
- [ ] New user can get running in < 5 minutes
- [ ] Clear signposting to detailed docs
- [ ] Quick reference table for common tasks
- [ ] Progressive disclosure (basic → advanced)

### Maintainability
- [ ] No duplication with other docs (DRY)
- [ ] Easy to update (minimal surface area)
- [ ] All links use stable paths
- [ ] Content is in appropriate doc (README vs guides)

## Next Steps

1. Write Section 1-4 (Title → Quick Start)
2. Write Section 5-9 (Documentation → License)
3. Test every command
4. Validate all links
5. Peer review against audit document
6. Replace old README

## Notes

- Keep it CONCISE - every line must earn its place
- LINK > DUPLICATE - point to detailed docs instead of repeating
- TEST EVERYTHING - every command must work as written
- PROGRESSIVE DISCLOSURE - basic info → links to details
- YAGNI - only what users need now, not "might be useful"
