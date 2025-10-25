# Old World Tournament Visualizer

Interactive Plotly Dash application for analyzing Old World tournament save files with turn-by-turn progression tracking, law/tech analytics, and player performance insights.

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

## Prerequisites

- **Python 3.9+** - Required by DuckDB and type hints
- **[uv](https://docs.astral.sh/uv/)** - Modern Python package manager
- **Old World save files** - Tournament matches in `.zip` format

Optional for full features:
- **Challonge API key** - For tournament sync ([get key](https://challonge.com/settings/developer))
- **Google Drive API** - For alternative file storage

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
uv run python manage.py logs -f   # Follow logs (tail -f)
```

See [CLAUDE.md § Application Management](CLAUDE.md#application-management) for details.

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

# Check logs (if they exist)
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

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## About Old World

Old World is a historical turn-based strategy game by Mohawk Games. This visualizer analyzes tournament save files in the standard `.zip` format exported from the game.

**More about Old World:** https://www.mohawkgames.com/oldworld/

---

**Note:** This application is not affiliated with or endorsed by Mohawk Games or the Old World development team.
