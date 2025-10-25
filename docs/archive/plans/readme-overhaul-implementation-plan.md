# README.md Overhaul Implementation Plan

> **Status:** ✅ COMPLETED on 2025-10-25
>
> **Outcome:** README refactored from 394-line comprehensive reference to 233-line quick start guide (41% reduction)
>
> **Result:** All 27 identified issues fixed. See final README.md and archived work documents in docs/archive/reports/readme-*.md
>
> **Key Achievements:**
> - Fixed all script names, paths, and commands
> - Added 10 missing major features
> - Created validation scripts (test_readme_commands.sh, validate_readme_links.py)
> - Tested all 17 commands - 100% working
> - Validated all 28 links - 100% working
> - Implemented progressive disclosure via documentation links

---

## Overview

### Problem
The current README.md has accumulated technical debt and inaccuracies:
- References non-existent script `import_tournaments.py` (should be `import_attachments.py`)
- Contains outdated deployment documentation paths
- Missing documentation of major features (participants, pick order, rulers, narratives)
- Incomplete database schema (missing 12+ tables)
- Trying to be both quick start guide AND comprehensive reference (succeeding at neither)

### Solution
Refactor README.md to be a focused **quick start guide** that gets new users running in <5 minutes, while pointing to comprehensive documentation in `docs/` for details.

### Success Criteria
- All script names and paths are correct
- README can be followed by someone with zero context and they can run the app
- Features section accurately reflects current capabilities
- Clear signposting to detailed docs for deeper information
- Passes validation (all commands work, all paths exist)

---

## Prerequisites

### Required Knowledge
- **Markdown**: Formatting for documentation
- **Python 3.9+**: Understanding imports and script execution
- **Command line basics**: Running bash commands, setting environment variables
- **Old World game**: Basic understanding helps but not required

### Required Setup
1. **Local development environment**
   ```bash
   # Ensure you can run the app
   uv sync
   uv run python manage.py start
   ```

2. **Access to test data**
   ```bash
   # Verify you have save files
   ls saves/*.zip | head -5

   # Verify database exists
   ls -lh data/tournament_data.duckdb
   ```

3. **Review existing documentation**
   ```bash
   # Read these first to understand current structure
   cat docs/README.md
   cat docs/developer-guide.md | head -100
   cat CLAUDE.md | grep -A 5 "Need More Details"
   ```

---

## Current System Architecture

### Documentation Structure
```
README.md                    # Quick start + comprehensive reference (PROBLEM)
├── CLAUDE.md               # Developer conventions + domain knowledge
├── docs/
│   ├── README.md           # Documentation guide
│   ├── developer-guide.md  # Architecture + technical details
│   ├── deployment-guide.md # Fly.io deployment
│   ├── migrations/         # Schema changes (8 files)
│   ├── reference/          # Technical specs
│   ├── reports/            # Analysis reports (active)
│   ├── plans/              # Implementation plans (active)
│   └── archive/            # Historical context
```

### Application Architecture
```
Old World Save Files (.zip containing .xml)
    ↓
Parser (tournament_visualizer/data/parser.py)
    ↓
ETL Pipeline (tournament_visualizer/data/etl.py)
    ↓
DuckDB Database (data/tournament_data.duckdb)
    ↓ 21 tables including:
    ├── matches, players, events
    ├── tournament_participants (Challonge API)
    ├── pick_order_games (pick/ban tracking)
    ├── rulers (character archetypes)
    ├── 6 history tables (turn-by-turn)
    └── match_metadata (narratives, GDrive links)
    ↓
Query Layer (tournament_visualizer/data/queries.py - 57 functions)
    ↓
Dash Application (4 pages: overview, matches, players, maps)
    ↓
Interactive Web Dashboard (http://localhost:8050)
```

### Key Components

**Data Sources:**
1. **Old World save files** (.zip) - Core game data
2. **Challonge API** - Tournament structure and participants
3. **Google Drive API** - Alternative file storage
4. **Manual overrides** - Data quality corrections (4 systems)

**Features Implemented:**
- Tournament overview analytics (nation win rates, archetypes, unit popularity)
- Individual match analysis (turn-by-turn progression, law/tech timelines)
- Player performance tracking (win rates, civilization preferences)
- Map analytics (territory control, performance by map)
- Law progression analysis (6 visualization types)
- Ruler archetype tracking (traits, combinations, matchups)
- Pick order analysis (pick/ban tracking)
- Match narratives (AI-generated summaries)

---

## Implementation Tasks

### Phase 1: Discovery and Validation (DO THIS FIRST!)

#### Task 1.1: Audit Current README for Accuracy Issues
**Objective:** Create a comprehensive list of every inaccuracy in README.md

**Files to check:**
- `README.md` (the file we're fixing)
- `scripts/` directory listing
- `docs/` directory structure
- `tournament_visualizer/` directory structure

**Commands to run:**
```bash
# Verify every script name mentioned in README exists
grep "scripts/" README.md | grep -oE "scripts/[a-z_]+\.py" | sort -u > /tmp/readme_scripts.txt
ls scripts/*.py | xargs -n1 basename | sort > /tmp/actual_scripts.txt
diff /tmp/readme_scripts.txt /tmp/actual_scripts.txt

# Verify every doc path mentioned exists
grep "docs/" README.md | grep -oE "docs/[a-z/-]+\.md" | sort -u > /tmp/readme_docs.txt
find docs -name "*.md" -type f | sort > /tmp/actual_docs.txt

# Verify all database tables in current schema
uv run duckdb data/tournament_data.duckdb -readonly -c "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name" > /tmp/actual_tables.txt
grep -A 50 "Database Schema" README.md | grep "^- \*\*" | sed 's/- \*\*//' | sed 's/\*\*:.*//' > /tmp/readme_tables.txt
diff /tmp/readme_tables.txt /tmp/actual_tables.txt
```

**What to document:**
Create a markdown file `docs/reports/readme-accuracy-audit.md`:
```markdown
# README.md Accuracy Audit

## Script Name Issues
- Line X: References `import_tournaments.py` → Should be `import_attachments.py`
- [List all]

## Path Issues
- Line Y: References `docs/deployment/` → Should be `docs/archive/deployment/`
- [List all]

## Missing Features
- No mention of ruler tracking
- [List all]

## Incorrect Schema
- Missing tables: X, Y, Z
- [List all]
```

**Testing:**
```bash
# Every command in README should work
# Extract and test each code block
grep -A 20 "^```bash" README.md > /tmp/readme_commands.txt
# Manually verify each command runs without error (or document why it shouldn't)
```

**Success criteria:**
- [ ] Audit document created
- [ ] Every script name verified against filesystem
- [ ] Every path verified to exist
- [ ] Every database table verified against schema
- [ ] Every bash command tested (or marked as example-only)

**Time estimate:** 1-2 hours

**Commit:**
```bash
git add docs/reports/readme-accuracy-audit.md
git commit -m "docs: Audit README.md for accuracy issues"
```

---

#### Task 1.2: Inventory Current Features from Code
**Objective:** Document what the application ACTUALLY does (not what README says)

**Files to analyze:**
```bash
# Find all dashboard pages
ls tournament_visualizer/pages/*.py

# Find all chart types
grep "^def create_.*_chart" tournament_visualizer/components/charts.py

# Find all query functions
grep "^    def get_" tournament_visualizer/data/queries.py

# Find all database tables
uv run duckdb data/tournament_data.duckdb -readonly -c "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"

# Find all validation scripts
ls scripts/validate_*.py

# Find all sync/import scripts
ls scripts/{sync,import,download}*.py 2>/dev/null
```

**What to document:**
Create `docs/reports/readme-feature-inventory.md`:
```markdown
# Feature Inventory for README

## Data Import Capabilities
- [X] Import from local .zip files (import_attachments.py)
- [X] Download from Challonge API (download_attachments.py)
- [X] Sync tournament data (sync_tournament_data.sh)
- [X] Sync participants (sync_challonge_participants.py)
- [X] Sync pick order (sync_pick_order_data.py)

## Dashboard Pages
1. **Overview** (/)
   - Nation win/loss/popularity charts
   - Ruler archetype analytics
   - Unit popularity
   - Pick order win rates
   - [List all features]

2. **Matches** (/matches)
   - Match selector
   - Turn-by-turn progression
   - Law progression (6 chart types)
   - Tech progression
   - Yield tracking (14 types)
   - [List all]

3. **Players** (/players)
   - [Document from pages/players.py]

4. **Maps** (/maps)
   - [Document from pages/maps.py]

## Database Schema (21 tables)
[List all with brief description]

## Analytics Queries (57 functions)
[Group by category: law, tech, yield, participant, ruler, etc.]

## Validation Scripts (6 scripts)
[List each with purpose]
```

**Testing:**
```bash
# Launch app and manually verify each page works
uv run python manage.py restart
open http://localhost:8050

# Navigate to each page
# - Overview: Note all sections and charts
# - Matches: Select a match, note all tabs and charts
# - Players: Note all charts
# - Maps: Note all charts

# Stop app
uv run python manage.py stop
```

**Success criteria:**
- [ ] Feature inventory created
- [ ] All 4 pages documented with feature lists
- [ ] All 21 tables documented
- [ ] All major script categories documented
- [ ] Verified by actually using the application

**Time estimate:** 2-3 hours

**Commit:**
```bash
git add docs/reports/readme-feature-inventory.md
git commit -m "docs: Inventory current features for README update"
```

---

#### Task 1.3: Map Documentation Cross-References
**Objective:** Understand where detailed docs live so README can point to them

**Files to review:**
```bash
# Read the docs guide
cat docs/README.md

# Check what's in developer guide
cat docs/developer-guide.md | grep "^## " | head -20

# Check what's in deployment guide
cat docs/deployment-guide.md | grep "^## " | head -20

# Check CLAUDE.md structure
cat CLAUDE.md | grep "^## " | head -20

# List active plans
ls docs/plans/

# List active reports
ls docs/reports/
```

**What to document:**
Create `docs/reports/readme-doc-mapping.md`:
```markdown
# Documentation Mapping for README

## Quick Start Topics → Where Details Live

### "How do I install dependencies?"
- README: Brief `uv sync` command
- Details: CLAUDE.md "Application Management"
- Also: developer-guide.md "Development Setup"

### "How do I import data?"
- README: One example with import_attachments.py
- Details: CLAUDE.md "Database Management"
- Also: developer-guide.md "ETL Pipeline"

### "What database tables exist?"
- README: Brief mention of core tables
- Details: developer-guide.md "Database Schema"
- Also: docs/migrations/*.md

### "How do I deploy?"
- README: Brief mention + link
- Details: docs/deployment-guide.md (complete guide)

### "What are the project conventions?"
- README: Not covered
- Details: CLAUDE.md (definitive source)

[Continue for all major topics...]

## Features → Where Implementation Details Live

### Law Progression Analysis
- Code: pages/matches.py, components/charts.py
- Docs: docs/archive/plans/law-progression-visualizations-implementation-plan.md
- Tests: tests/test_charts_law_progression.py

### Ruler Tracking
- Code: data/parser.py (extract_rulers), pages/overview.py
- Docs: docs/migrations/003_add_rulers_table.md
- Tests: tests/test_parser_rulers.py, tests/test_integration_rulers.py

[Continue for all features...]
```

**Success criteria:**
- [ ] Mapping document created
- [ ] Every major README topic mapped to detailed docs
- [ ] Every feature mapped to implementation docs
- [ ] Clear understanding of what README should/shouldn't cover

**Time estimate:** 1 hour

**Commit:**
```bash
git add docs/reports/readme-doc-mapping.md
git commit -m "docs: Map README topics to detailed documentation"
```

---

### Phase 2: Content Design

#### Task 2.1: Design New README Structure
**Objective:** Create the skeleton/outline for the new README

**Reference examples:**
Look at popular Python projects for inspiration:
- FastAPI: https://github.com/tiangolo/fastapi (great quick start)
- Plotly Dash: https://github.com/plotly/dash (similar stack)
- DuckDB Python: https://github.com/duckdb/duckdb (database focus)

**Files to create:**
Create `docs/reports/readme-new-structure.md`:
```markdown
# New README Structure Design

## Principles
1. **Quick Start First**: Get running in <5 minutes
2. **Progressive Disclosure**: Basic → Advanced via links
3. **Accuracy**: Every command must work
4. **Signposting**: Clear pointers to detailed docs
5. **Maintenance**: Easy to keep updated

## Proposed Structure

### 1. Title + One-Line Description
```
# Old World Tournament Visualizer

Interactive Plotly Dash application for analyzing Old World tournament save files.
```

### 2. Features (Brief, Bullet Points)
- 🏆 Tournament Overview Dashboard
- 📊 Match-by-Match Analysis
- 👥 Player Performance Tracking
- 🗺️ Map Analytics
- 📈 Turn-by-Turn History (6 tracked metrics)
- ⚖️ Law & Tech Progression
- 👑 Ruler Archetype Analysis
- 🎯 Pick Order Tracking

[Keep concise - just feature names, not explanations]

### 3. Prerequisites
- Python 3.9+
- [uv](https://docs.astral.sh/uv/) package manager
- Tournament save files (.zip format)

### 4. Quick Start (3-Step Process)
```bash
# 1. Install dependencies
uv sync

# 2. Import your tournament data
uv run python scripts/import_attachments.py --directory saves/

# 3. Launch the dashboard
uv run python manage.py start
```

Then open: http://localhost:8050

### 5. Documentation Links
**New to the project?** Start here:
- 📘 [Developer Guide](docs/developer-guide.md) - Architecture, database, testing
- 🚀 [Deployment Guide](docs/deployment-guide.md) - Deploy to Fly.io
- 🛠️ [CLAUDE.md](CLAUDE.md) - Project conventions and workflows

**Need help with:**
- Database operations → [CLAUDE.md § Database Management](CLAUDE.md#database-management)
- Application management → [CLAUDE.md § Application Management](CLAUDE.md#application-management)
- Schema changes → [docs/migrations/](docs/migrations/)
- Testing → [Developer Guide § Testing](docs/developer-guide.md#testing-architecture)

### 6. Example Usage (Keep ONE good example)
**Law Progression Analysis**
```python
from tournament_visualizer.data.queries import get_queries

queries = get_queries()
progression = queries.get_law_progression_by_match(match_id=10)
print(progression)
# Output: player_name, turn_to_4_laws, turn_to_7_laws, total_laws
```

See [Developer Guide § Analytics Queries](docs/developer-guide.md#analytics-queries) for all 57 query functions.

### 7. Common Issues (Top 3 Only)
**Port already in use:**
```bash
uv run python manage.py stop  # Stop existing server
uv run python manage.py start
```

**No data showing:**
```bash
# Verify import worked
uv run duckdb data/tournament_data.duckdb -readonly -c "SELECT COUNT(*) FROM matches"
```

**Import errors:**
```bash
# Run with verbose logging
uv run python scripts/import_attachments.py --directory saves/ --verbose
```

For more troubleshooting → [Developer Guide § Troubleshooting](docs/developer-guide.md#troubleshooting)

### 8. Contributing
See [CLAUDE.md](CLAUDE.md) for:
- Development principles (YAGNI, DRY, TDD)
- Commit message conventions
- Code quality standards
- Testing requirements

### 9. License + Game Info
- License: MIT
- About Old World: https://www.mohawkgames.com/oldworld/
- Not affiliated with Mohawk Games

---

## What We're REMOVING from README
- Detailed project structure (→ developer-guide.md)
- Complete database schema (→ developer-guide.md)
- All 57 query examples (keep 1, link to docs)
- Deployment step-by-step (→ deployment-guide.md)
- Configuration details (→ developer-guide.md)
- Development tools setup (→ CLAUDE.md)
- MemoryData vs LogData explanation (→ developer-guide.md)

## What We're FIXING
- ✅ `import_tournaments.py` → `import_attachments.py`
- ✅ `docs/deployment/` → `docs/deployment-guide.md`
- ✅ Direct `app.py` → `manage.py start`
- ✅ Missing tables in schema → Link to developer-guide.md
- ✅ Missing features → Add to features list
```

**Success criteria:**
- [ ] Structure document created
- [ ] Clear principles defined
- [ ] Section-by-section outline complete
- [ ] Removal list documented
- [ ] Fix list documented

**Time estimate:** 1-2 hours

**Commit:**
```bash
git add docs/reports/readme-new-structure.md
git commit -m "docs: Design new README structure"
```

---

#### Task 2.2: Write First Draft Sections (Part 1)
**Objective:** Write title through Quick Start sections

**Files to edit:**
- Create `README.new.md` (work-in-progress, don't replace README.md yet)

**Writing guidelines (from CLAUDE.md):**
- Comments explain WHY, not WHAT
- Code should be self-documenting
- DRY: Don't repeat information that's in other docs, link to them
- YAGNI: Only include what users need NOW, not "might be useful"

**Section 1: Title + Description**
```markdown
# Old World Tournament Visualizer

Interactive Plotly Dash application for analyzing Old World tournament save files with turn-by-turn progression tracking, law/tech analytics, and player performance insights.

[Screenshot or demo GIF if available in assets/]
```

**Section 2: Features**
```markdown
## Features

### 📊 Analytics Dashboard
- **Tournament Overview**: Nation win rates, ruler archetypes, unit popularity, pick order analysis
- **Match Analysis**: Turn-by-turn progression, law/tech timelines, yield tracking (14 types)
- **Player Performance**: Win rates, civilization preferences, head-to-head comparisons
- **Map Analytics**: Territory control, strategic position impact, map-specific performance

### 📈 Data Tracking
- **Turn-by-Turn History**: 6 tracked metrics (points, yields, military, legitimacy, orders, opinions)
- **Law Progression**: 6 visualization types analyzing milestone timing and efficiency
- **Tech Research**: Complete tech tree progression and timing analysis
- **Ruler Archetypes**: Character traits, combinations, and matchup analysis
- **Pick Order**: Pick/ban tracking and win rate correlation

### 🔄 Data Integration
- **Local Import**: Process Old World save files (.zip format)
- **Challonge API**: Sync tournament structure and participants
- **Google Drive**: Alternative save file storage
- **Data Quality**: 4 override systems for manual corrections
```

**Why these features?**
- Pulled from feature inventory (Task 1.2)
- Grouped logically (Dashboard, Tracking, Integration)
- Brief but comprehensive
- Uses emojis for visual scanning

**Section 3: Prerequisites**
```markdown
## Prerequisites

- **Python 3.9+** - Required by DuckDB and type hints
- **[uv](https://docs.astral.sh/uv/)** - Modern Python package manager
- **Old World save files** - Tournament matches in `.zip` format

Optional for full features:
- **Challonge API key** - For tournament sync ([get key](https://challonge.com/settings/developer))
- **Google Drive API** - For alternative file storage
```

**Section 4: Quick Start**
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
# Verbose output (see what's being processed)
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
uv run python manage.py logs -f   # Follow logs (like tail -f)
```

See [CLAUDE.md § Application Management](CLAUDE.md#application-management) for details.
```

**Testing this section:**
```bash
# Follow your own quick start instructions on a fresh clone
cd /tmp
git clone <repo> test-readme
cd test-readme

# Follow every command in the Quick Start section
# Document any issues
```

**Success criteria:**
- [ ] New file `README.new.md` created
- [ ] Sections 1-4 written
- [ ] All script names verified correct
- [ ] All paths verified correct
- [ ] Tested on fresh clone (or document why not possible)

**Time estimate:** 2 hours

**Commit:**
```bash
git add README.new.md
git commit -m "docs: Write README draft part 1 (title through quick start)"
```

---

#### Task 2.3: Write First Draft Sections (Part 2)
**Objective:** Write Documentation Links through end

**Files to edit:**
- `README.new.md` (continue from Task 2.2)

**Section 5: Documentation Links**
```markdown
## Documentation

### 📚 Start Here

**New to the project?**
- [Developer Guide](docs/developer-guide.md) - Architecture, database schema, ETL pipeline, testing
- [Deployment Guide](docs/deployment-guide.md) - Deploy to Fly.io with persistent storage
- [CLAUDE.md](CLAUDE.md) - Development conventions, workflows, domain knowledge

### 🔍 Quick References

| I want to... | See this |
|-------------|----------|
| Understand database schema | [Developer Guide § Database Schema](docs/developer-guide.md#database-schema) |
| Run tests | [CLAUDE.md § Testing](CLAUDE.md#testing--code-quality) |
| Deploy to production | [Deployment Guide](docs/deployment-guide.md) |
| Use query functions | [Developer Guide § Analytics Queries](docs/developer-guide.md#analytics-queries) |
| Understand schema changes | [docs/migrations/](docs/migrations/) |
| Configure the app | [Developer Guide § Configuration](docs/developer-guide.md#configuration) |
| Manage the database | [CLAUDE.md § Database Management](CLAUDE.md#database-management) |
| Learn project conventions | [CLAUDE.md](CLAUDE.md) |

### 📖 Additional Resources
- [Documentation Guide](docs/README.md) - How documentation is organized
- [Save File Format](docs/reference/save-file-format.md) - Old World XML structure
- [Active Reports](docs/reports/) - Current analysis and investigations
- [Schema Migrations](docs/migrations/) - Database change history
```

**Why this format?**
- Table is scannable (users find what they need quickly)
- Progressive disclosure (links to specific sections, not just files)
- Covers common tasks from feature inventory

**Section 6: Example Usage**
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

# Get techs available at law milestone
techs_at_milestone = queries.get_techs_at_law_milestone(match_id=10, milestone=4)
print(techs_at_milestone)
# Output: DataFrame with columns: player_name, milestone_turn, tech_count, tech_list
```

### Database Queries

```python
from tournament_visualizer.data.database import get_database

db = get_database()

# Direct SQL query
with db.get_connection() as conn:
    result = conn.execute("""
        SELECT player_name, COUNT(*) as matches_played
        FROM players
        GROUP BY player_name
        ORDER BY matches_played DESC
    """).fetchdf()
    print(result)
```

**See also:**
- [Developer Guide § Analytics Layer](docs/developer-guide.md#analytics-layer) - All 57 query functions
- [Developer Guide § Database](docs/developer-guide.md#database) - Schema and operations
```

**Why one example, not many?**
- YAGNI: Most users won't programmatically query, they'll use the dashboard
- DRY: Detailed examples live in developer-guide.md
- Shows enough to get started, link for more

**Section 7: Common Issues**
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
# Run with verbose logging to see details
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

**More troubleshooting:** [Developer Guide § Troubleshooting](docs/developer-guide.md#troubleshooting)

**Known issues:** [docs/bugs/](docs/bugs/)
```

**Why these 4 issues?**
- Based on common support questions (hypothetical, but realistic)
- Each has actionable solution
- Points to detailed docs for complex issues

**Section 8: Contributing**
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

**Section 9: License and About**
```markdown
## License

This project is licensed under the MIT License - see the LICENSE file for details.

## About Old World

Old World is a historical turn-based strategy game by Mohawk Games. This visualizer analyzes tournament save files in the standard `.zip` format exported from the game.

**More about Old World:** https://www.mohawkgames.com/oldworld/

---

**Note:** This application is not affiliated with or endorsed by Mohawk Games or the Old World development team.
```

**Testing this section:**
```bash
# Verify all links work
grep -oE '\[.*\]\([^)]+\)' README.new.md | sed 's/.*(\([^)]*\)).*/\1/' | while read link; do
    if [[ $link == http* ]]; then
        echo "External: $link"  # Test manually
    else
        if [[ -f $link ]] || [[ -d $link ]]; then
            echo "✓ $link"
        else
            echo "✗ MISSING: $link"
        fi
    fi
done
```

**Success criteria:**
- [ ] Sections 5-9 written in README.new.md
- [ ] All links verified (internal files exist)
- [ ] Table of quick references accurate
- [ ] Example code tested (runs without error)
- [ ] Common issues are actually common and solutions work

**Time estimate:** 2-3 hours

**Commit:**
```bash
git add README.new.md
git commit -m "docs: Write README draft part 2 (documentation through end)"
```

---

### Phase 3: Validation and Testing

#### Task 3.1: Test Every Command in New README
**Objective:** Ensure every code block actually works

**Testing approach:**
Create `scripts/test_readme_commands.sh`:
```bash
#!/bin/bash
# Test script for README.md commands
# Tests each command block to ensure it works

set -e  # Exit on first error

echo "Testing README.md commands..."

# Test 1: uv sync
echo "Test 1: uv sync"
uv sync
echo "✓ uv sync works"

# Test 2: import_attachments.py exists and runs
echo "Test 2: import_attachments.py"
if [[ ! -f scripts/import_attachments.py ]]; then
    echo "✗ scripts/import_attachments.py not found"
    exit 1
fi
uv run python scripts/import_attachments.py --help > /dev/null
echo "✓ import_attachments.py exists and shows help"

# Test 3: manage.py commands
echo "Test 3: manage.py commands"
uv run python manage.py status
echo "✓ manage.py status works"

# Test 4: Database query
echo "Test 4: Database query"
uv run duckdb data/tournament_data.duckdb -readonly -c "SELECT COUNT(*) FROM matches" > /dev/null
echo "✓ Database query works"

# Test 5: Python example imports
echo "Test 5: Python imports"
uv run python -c "from tournament_visualizer.data.queries import get_queries; print('✓ Imports work')"

# Test 6: Test commands
echo "Test 6: Development tools"
uv run black --check tournament_visualizer/ > /dev/null
uv run ruff check tournament_visualizer/ > /dev/null
echo "✓ Development tools work"

echo ""
echo "All README commands validated!"
```

**Files to test:**
```bash
# Extract all bash code blocks from README
awk '/^```bash$/,/^```$/' README.new.md > /tmp/readme_bash_blocks.txt

# Extract all python code blocks
awk '/^```python$/,/^```$/' README.new.md > /tmp/readme_python_blocks.txt

# Manually review each block and test
```

**Testing steps:**
```bash
# Make script executable
chmod +x scripts/test_readme_commands.sh

# Run tests
./scripts/test_readme_commands.sh

# Test on fresh environment (if possible)
docker run -it --rm -v $(pwd):/app python:3.11 bash
cd /app
# Install uv, then follow README from scratch
```

**Success criteria:**
- [ ] Test script created
- [ ] All bash commands pass
- [ ] All python imports work
- [ ] All paths are correct
- [ ] Help text works for all scripts
- [ ] No false assumptions (like files existing that don't)

**Time estimate:** 2 hours

**Commit:**
```bash
git add scripts/test_readme_commands.sh
chmod +x scripts/test_readme_commands.sh
git commit -m "test: Add README command validation script"
```

---

#### Task 3.2: Validate All Links and References
**Objective:** Ensure no broken links in README

**Create validation script:**
`scripts/validate_readme_links.py`:
```python
#!/usr/bin/env python3
"""Validate all links in README.md"""

import re
import sys
from pathlib import Path


def extract_markdown_links(content: str) -> list[tuple[str, str]]:
    """Extract all [text](link) patterns from markdown."""
    pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    return re.findall(pattern, content)


def validate_links(readme_path: Path) -> int:
    """Validate all links in README.

    Returns:
        Number of broken links found
    """
    content = readme_path.read_text()
    links = extract_markdown_links(content)

    errors = 0
    for text, link in links:
        # Skip external URLs (test manually)
        if link.startswith(('http://', 'https://')):
            print(f"⚠️  External (test manually): {link}")
            continue

        # Skip anchors within same doc
        if link.startswith('#'):
            print(f"ℹ️  Anchor (test manually): {link}")
            continue

        # Handle anchors to other docs
        if '#' in link:
            link_path, anchor = link.split('#', 1)
            target = Path(link_path)
            if not target.exists():
                print(f"✗ BROKEN: {link} (file not found)")
                errors += 1
            else:
                # Check anchor exists in target file
                target_content = target.read_text()
                # Convert anchor to heading format
                heading = anchor.replace('-', ' ').title()
                if heading not in target_content:
                    print(f"⚠️  Anchor may not exist: {link}")
                else:
                    print(f"✓ {link}")
        else:
            # Check file/directory exists
            target = Path(link)
            if target.exists():
                print(f"✓ {link}")
            else:
                print(f"✗ BROKEN: {link}")
                errors += 1

    return errors


def main() -> int:
    readme = Path("README.new.md")
    if not readme.exists():
        print(f"Error: {readme} not found")
        return 1

    print(f"Validating links in {readme}...\n")
    errors = validate_links(readme)

    print(f"\n{'='*50}")
    if errors > 0:
        print(f"❌ Found {errors} broken links")
        return 1
    else:
        print("✅ All links valid")
        return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Run validation:**
```bash
# Make executable
chmod +x scripts/validate_readme_links.py

# Run validation
uv run python scripts/validate_readme_links.py

# Fix any broken links found
```

**Manual checks needed:**
```bash
# Check external URLs (can't automate)
grep -oE 'https?://[^)]+' README.new.md | sort -u > /tmp/external_urls.txt
cat /tmp/external_urls.txt
# Visit each URL manually

# Check section anchors within README
grep -E '\[.*\]\(#' README.new.md
# Verify each #anchor corresponds to a ## heading
```

**Success criteria:**
- [ ] Validation script created and runs
- [ ] All internal file links work
- [ ] All section anchors verified
- [ ] External URLs manually tested
- [ ] No broken links

**Time estimate:** 1 hour

**Commit:**
```bash
git add scripts/validate_readme_links.py
chmod +x scripts/validate_readme_links.py
git commit -m "test: Add README link validation script"
```

---

#### Task 3.3: Peer Review Against Audit Document
**Objective:** Systematically verify every issue from Task 1.1 is fixed

**Review process:**
```bash
# Open both documents side by side
code docs/reports/readme-accuracy-audit.md README.new.md
```

**Create checklist:**
Create `docs/reports/readme-fix-verification.md`:
```markdown
# README Fix Verification

Reference: `readme-accuracy-audit.md` from Task 1.1

## Script Name Issues
- [ ] Line X: `import_tournaments.py` → Fixed to `import_attachments.py`
- [ ] Line Y: ... (every issue from audit)

## Path Issues
- [ ] Line Z: `docs/deployment/` → Fixed to `docs/deployment-guide.md`
- [ ] ... (every path issue)

## Missing Features
- [ ] Ruler tracking → Added to features section
- [ ] Pick order → Added to features section
- [ ] ... (every missing feature)

## Incorrect Schema
- [ ] Tables missing → Removed schema section, linked to developer-guide.md
- [ ] ... (every schema issue)

## Missing Scripts/Workflows
- [ ] manage.py → Added to Quick Start section
- [ ] Validation scripts → Mentioned in troubleshooting
- [ ] ... (every missing item)

## Commands That Don't Work
- [ ] Command X → Fixed/Removed/Documented why it shouldn't run
- [ ] ... (every broken command)

---

## Sign-Off

All issues from accuracy audit have been addressed:
- [ ] All script names correct
- [ ] All paths verified
- [ ] All features documented
- [ ] All commands tested
- [ ] No inaccuracies remain

Verified by: [Your Name]
Date: [Date]
```

**Testing:**
```bash
# For each item in audit, grep README.new.md to verify fix
# Example:
grep "import_tournaments" README.new.md
# Should return nothing

grep "import_attachments" README.new.md
# Should return correct usage
```

**Success criteria:**
- [ ] Verification checklist created
- [ ] Every audit item checked off
- [ ] All script names verified correct
- [ ] All paths verified exist
- [ ] All features verified documented
- [ ] Sign-off completed

**Time estimate:** 1-2 hours

**Commit:**
```bash
git add docs/reports/readme-fix-verification.md
git commit -m "docs: Verify all README accuracy issues resolved"
```

---

### Phase 4: Migration and Cleanup

#### Task 4.1: Replace Old README with New Version
**Objective:** Deploy the new README

**Safety first:**
```bash
# Backup old README
cp README.md README.old.md
git add README.old.md
git commit -m "docs: Backup old README before replacement"

# Copy new README
cp README.new.md README.md
git add README.md
```

**Update developer-guide.md if needed:**
```bash
# If we moved content TO developer-guide.md, ensure it's there
code docs/developer-guide.md

# Check table of contents is accurate
grep "^## " docs/developer-guide.md
```

**Update CLAUDE.md if needed:**
```bash
# Verify CLAUDE.md "Need More Details" section points to correct docs
grep -A 20 "Need More Details" CLAUDE.md
```

**Success criteria:**
- [ ] Old README backed up
- [ ] New README in place
- [ ] Related docs updated if content moved
- [ ] No broken references

**Time estimate:** 30 minutes

**Commit:**
```bash
git commit -m "docs: Replace README with overhauled version

- Fix incorrect script name (import_tournaments.py → import_attachments.py)
- Fix outdated paths (docs/deployment/ → docs/deployment-guide.md)
- Add missing features (rulers, pick order, participants, narratives)
- Simplify to quick start guide, link to detailed docs
- Remove redundant content (schema, project structure, deployment details)
- Test all commands work
- Validate all links

Closes #XXX (if there's an issue for this)
"
```

---

#### Task 4.2: Clean Up Work Documents
**Objective:** Archive the work documents created during this refactor

**Files to handle:**
```bash
# List all work documents
ls docs/reports/readme-*.md

# These were created during implementation:
# - readme-accuracy-audit.md
# - readme-feature-inventory.md
# - readme-doc-mapping.md
# - readme-new-structure.md
# - readme-fix-verification.md
```

**Decision: Archive or Delete?**

**Archive (recommended):**
```bash
# Move to archive with context
git mv docs/reports/readme-accuracy-audit.md docs/archive/reports/
git mv docs/reports/readme-feature-inventory.md docs/archive/reports/
git mv docs/reports/readme-doc-mapping.md docs/archive/reports/
git mv docs/reports/readme-new-structure.md docs/archive/reports/
git mv docs/reports/readme-fix-verification.md docs/archive/reports/
```

**Why archive?**
- Shows our work process
- Useful if we need to do similar refactor
- Documents what features existed at this point in time

**Update archive log:**
```bash
# Add entry to docs/archive/ARCHIVE_LOG.md
cat >> docs/archive/ARCHIVE_LOG.md << EOF

## $(date +%Y-%m-%d) - README Overhaul Work Documents

**Context:** README.md overhaul implementation plan (Task 4.2)

**Archived:**
- \`reports/readme-accuracy-audit.md\` - Documented inaccuracies in old README
- \`reports/readme-feature-inventory.md\` - Inventoried actual features from code
- \`reports/readme-doc-mapping.md\` - Mapped README topics to detailed docs
- \`reports/readme-new-structure.md\` - Designed new README structure
- \`reports/readme-fix-verification.md\` - Verified all issues resolved

**Why archived:** Implementation artifacts for README refactor, useful as process template for future doc refactors.

**Related:** README overhaul completed, new README focuses on quick start with links to detailed docs.
EOF

git add docs/archive/ARCHIVE_LOG.md
```

**Clean up temporary files:**
```bash
# Remove the working draft (now in README.md)
rm README.new.md

# Remove backup (it's in git history)
rm README.old.md

# Remove temp files from validation
rm -f /tmp/readme_*.txt
```

**Success criteria:**
- [ ] Work documents archived
- [ ] Archive log updated
- [ ] Temporary files cleaned up
- [ ] README.new.md removed (no longer needed)

**Time estimate:** 30 minutes

**Commit:**
```bash
git add docs/archive/
git commit -m "docs: Archive README overhaul work documents

Archive implementation artifacts to preserve process and context."
```

---

#### Task 4.3: Update Implementation Plan Status
**Objective:** Mark this plan as completed and archived

**Update this plan's header:**
Edit `docs/plans/readme-overhaul-implementation-plan.md`:
```markdown
# README.md Overhaul Implementation Plan

> **Status:** ✅ COMPLETED on [DATE]
> **Outcome:** README refactored from comprehensive reference to quick start guide
> **Result:** See final README.md and archived work documents in docs/archive/reports/readme-*.md

[Rest of plan content...]
```

**Archive this plan:**
```bash
# Move to archive
git mv docs/plans/readme-overhaul-implementation-plan.md docs/archive/plans/

# Update archive log
cat >> docs/archive/ARCHIVE_LOG.md << EOF

## $(date +%Y-%m-%d) - README Overhaul Implementation Plan

**Context:** README.md refactor project

**Archived:**
- \`plans/readme-overhaul-implementation-plan.md\` - Complete implementation plan for README overhaul

**Why archived:** Plan completed successfully. README is now a focused quick start guide.

**Related commits:**
- Backup old README
- Write new README
- Archive work documents
- Update references in related docs
EOF

git add docs/archive/ARCHIVE_LOG.md
```

**Success criteria:**
- [ ] Plan marked as completed
- [ ] Plan archived
- [ ] Archive log updated
- [ ] All work documents accounted for

**Time estimate:** 15 minutes

**Commit:**
```bash
git add docs/archive/
git commit -m "docs: Archive README overhaul implementation plan

Plan completed successfully. README now focuses on quick start with links to detailed documentation."
```

---

### Phase 5: Validation and Sign-Off

#### Task 5.1: Full End-to-End Test
**Objective:** One final test that the README works for new users

**Test scenario: New Developer Experience**
```bash
# Simulate fresh clone (use temp directory)
cd /tmp
git clone [repo_url] test-readme-final
cd test-readme-final

# Follow README.md exactly as written
# Document any friction points

# 1. Check prerequisites
python3 --version  # Should be 3.9+
which uv || echo "uv not installed"

# 2. Follow Quick Start Step 1
uv sync
# Did it work? Any errors?

# 3. Check if saves/ directory exists
ls saves/ || echo "No saves directory"

# 4. Follow Quick Start Step 2 (if have data)
uv run python scripts/import_attachments.py --directory saves/
# Did it work? Clear error messages?

# 5. Follow Quick Start Step 3
uv run python manage.py start
# Does it start? Visit http://localhost:8050

# 6. Stop server
uv run python manage.py stop

# 7. Try example code
uv run python << EOF
from tournament_visualizer.data.queries import get_queries
queries = get_queries()
print("✓ Example imports work")
EOF

# 8. Try a documentation link
ls docs/developer-guide.md
ls docs/deployment-guide.md
ls CLAUDE.md
```

**Document results:**
Create `docs/reports/readme-final-test-results.md`:
```markdown
# README Final Test Results

## Test Environment
- OS: [macOS/Linux/Windows]
- Python version: [X.Y.Z]
- uv installed: [Yes/No]
- Fresh clone: [Yes/No]
- Data available: [Yes/No]

## Quick Start Test Results

### Step 1: Install Dependencies
- Command: `uv sync`
- Result: [✓ Success / ✗ Failed]
- Time taken: [X seconds]
- Issues: [None / List issues]

### Step 2: Import Data
- Command: `uv run python scripts/import_attachments.py --directory saves/`
- Result: [✓ Success / ✗ Failed / ⊘ Skipped (no data)]
- Issues: [None / List issues]

### Step 3: Launch Dashboard
- Command: `uv run python manage.py start`
- Result: [✓ Success / ✗ Failed]
- Browser loads: [✓ Yes / ✗ No]
- Issues: [None / List issues]

## Example Code Test
- Python imports: [✓ Success / ✗ Failed]
- Query execution: [✓ Success / ✗ Failed / ⊘ Skipped (no data)]

## Documentation Links Test
- All internal links: [✓ Valid / ✗ Some broken]
- Broken links: [List any broken links]

## User Experience Assessment
- Clarity: [1-5 rating, 5 = very clear]
- Completeness: [1-5 rating]
- Accuracy: [1-5 rating]
- Would a new user succeed: [Yes / No / Maybe]

## Issues Found
1. [Issue description]
2. [Issue description]

## Recommended Changes
- [Change 1]
- [Change 2]

---

**Tester:** [Name]
**Date:** [Date]
**Sign-off:** [✓ Approved for merge / ✗ Needs fixes]
```

**Success criteria:**
- [ ] Test completed on fresh environment
- [ ] Test results documented
- [ ] All quick start steps successful
- [ ] No major issues found
- [ ] Sign-off given

**Time estimate:** 1 hour

**Commit:**
```bash
git add docs/reports/readme-final-test-results.md
git commit -m "docs: Final end-to-end test of new README"
```

---

#### Task 5.2: Code Review Checklist
**Objective:** Final quality check before merge

**Review checklist:**
Create `docs/reports/readme-overhaul-review-checklist.md`:
```markdown
# README Overhaul Review Checklist

## Content Accuracy
- [ ] All script names are correct (no import_tournaments.py)
- [ ] All file paths exist (verified with ls/test -f)
- [ ] All documentation links work
- [ ] All bash commands tested
- [ ] All python code examples tested
- [ ] Features list matches current capabilities
- [ ] Prerequisites are accurate

## Content Quality
- [ ] Language is clear and concise
- [ ] Follows YAGNI (no speculative content)
- [ ] Follows DRY (no duplication with other docs)
- [ ] Structure is logical (title → features → quick start → docs)
- [ ] Quick start is actually quick (<5 min)
- [ ] Troubleshooting covers common issues
- [ ] Links provide progressive disclosure

## Code Quality
- [ ] Validation scripts added (test_readme_commands.sh, validate_readme_links.py)
- [ ] Scripts are executable (chmod +x)
- [ ] Scripts have proper shebangs
- [ ] Type hints used in Python validation script

## Documentation
- [ ] Work documents archived
- [ ] Archive log updated
- [ ] This implementation plan archived
- [ ] Related docs updated (CLAUDE.md, developer-guide.md)
- [ ] No orphaned references to old content

## Testing
- [ ] Commands tested on actual environment
- [ ] Links validated programmatically
- [ ] Examples run without error
- [ ] Fresh clone test completed
- [ ] Test results documented

## Git Hygiene
- [ ] Commits are atomic (one logical change each)
- [ ] Commit messages follow conventional format
- [ ] No Claude attribution in commit messages
- [ ] Clean git history (no "fix typo" commits, squash if needed)

## Sign-Off
- [ ] All checklist items passed
- [ ] Ready for merge

**Reviewer:** [Name]
**Date:** [Date]
**Approved:** [Yes / No / With conditions]
```

**Review process:**
```bash
# View all commits for this work
git log --oneline origin/main..HEAD

# Review each commit
git show [commit-hash]

# Check for issues
git diff origin/main README.md

# Run all validation
./scripts/test_readme_commands.sh
uv run python scripts/validate_readme_links.py
```

**Success criteria:**
- [ ] Review checklist completed
- [ ] All items checked off
- [ ] Any issues fixed
- [ ] Approved for merge

**Time estimate:** 1 hour

**Commit:**
```bash
git add docs/reports/readme-overhaul-review-checklist.md
git commit -m "docs: Add review checklist for README overhaul"
```

---

#### Task 5.3: Merge and Celebrate
**Objective:** Complete the README overhaul

**Final checks:**
```bash
# Ensure on feature branch
git branch --show-current

# Rebase on latest main
git fetch origin
git rebase origin/main

# Run full test suite
uv run pytest

# Check code quality
uv run black tournament_visualizer/
uv run ruff check tournament_visualizer/

# Final README validation
./scripts/test_readme_commands.sh
uv run python scripts/validate_readme_links.py
```

**Create PR or merge directly:**
```bash
# If using PRs:
git push origin readme-overhaul
# Create PR on GitHub/GitLab

# If merging directly:
git checkout main
git merge readme-overhaul
git push origin main
```

**Archive work branch:**
```bash
# After merge, delete feature branch
git branch -d readme-overhaul
git push origin --delete readme-overhaul
```

**Success criteria:**
- [ ] All tests pass
- [ ] Code quality checks pass
- [ ] Merged to main
- [ ] Work branch cleaned up

**Time estimate:** 30 minutes

---

## Summary

### Time Estimates by Phase
- **Phase 1 (Discovery):** 4-6 hours
- **Phase 2 (Content Design):** 5-7 hours
- **Phase 3 (Validation):** 4-5 hours
- **Phase 4 (Migration):** 1-2 hours
- **Phase 5 (Sign-off):** 2-3 hours

**Total:** 16-23 hours (2-3 days)

### Key Deliverables
1. ✅ Accurate README.md (quick start guide)
2. ✅ README validation scripts
3. ✅ Work documents (archived)
4. ✅ Test results
5. ✅ Review checklist

### Success Metrics
- [ ] Zero incorrect script names
- [ ] Zero broken links
- [ ] Zero failed commands
- [ ] New user can run app in <5 minutes
- [ ] README is <500 lines (focused)
- [ ] All detailed content moved to proper docs

---

## Post-Implementation

### Maintenance
- Update README when adding major features
- Run validation scripts before merging README changes
- Keep sync with CLAUDE.md conventions
- Archive old versions when making major updates

### Future Improvements
- Add screenshots/GIFs of dashboard
- Add "Why use this?" section with comparison to alternatives
- Add FAQ section if common questions emerge
- Consider video walkthrough for YouTube

---

## References

### Files to Read Before Starting
- `README.md` (current version)
- `docs/README.md` (documentation guide)
- `docs/developer-guide.md` (architecture)
- `CLAUDE.md` (conventions)

### Related Plans
- `docs/plans/documentation-organization-implementation-plan.md` - How docs are organized
- `docs/archive/plans/` - Examples of completed plans

### Testing Resources
- `tests/` - Test structure examples
- `scripts/validate_*.py` - Validation script examples

---

## Notes for Implementer

### Common Pitfalls
1. **Don't start writing without discovery phase** - You'll miss issues
2. **Don't skip validation** - Commands that look right may not work
3. **Don't preserve everything** - Old README has too much, less is more
4. **Don't forget links** - Every removed section should link to new location
5. **Don't skip testing** - Follow your own instructions on fresh clone

### When in Doubt
- Ask: "Does a new user need this RIGHT NOW?"
- If no → Move to detailed docs
- If yes → Keep but make concise
- Always prefer links over duplication

### Getting Help
- Read CLAUDE.md first
- Check developer-guide.md for architecture
- Look at archived plans for examples
- Ask questions before making assumptions

Good luck! 🚀
