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
