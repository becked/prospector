# Old World Tournament Visualizer

A comprehensive Plotly Dash web application that transforms Old World game save files into interactive tournament analytics and visualizations.

## 🏆 Features

- **Tournament Overview**: High-level statistics, match timeline, and key performance indicators
- **Match Analysis**: Detailed turn-by-turn progression, resource development, and event timelines
- **Player Performance**: Rankings, win rates, civilization preferences, and head-to-head comparisons
- **Map & Territory**: Territory control visualization, map performance analysis, and strategic insights
- **Interactive Filters**: Date ranges, players, civilizations, maps, and match duration
- **Data Export**: Exportable tables and charts for further analysis

## 📋 Prerequisites

- Python 3.9 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- Old World tournament save files (`.zip` format)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
uv sync
```

This will install all required dependencies including Dash, Plotly, DuckDB, and data processing libraries.

### 2. Import Tournament Data

Place your Old World tournament save files (`.zip` format) in a directory (default: `saves/`) and run:

```bash
uv run python import_tournaments.py --directory saves/
```

**Import Options:**
```bash
# Import from default saves/ directory
uv run python import_tournaments.py

# Import from custom directory
uv run python import_tournaments.py --directory /path/to/tournament/files

# Verbose logging
uv run python import_tournaments.py --verbose

# Force reimport (removes existing database)
uv run python import_tournaments.py --force

# Dry run (see what would be imported)
uv run python import_tournaments.py --dry-run
```

### 3. Launch the Dashboard

```bash
uv run python tournament_visualizer/app.py
```

The application will start and be available at: **http://localhost:8050**

## 📊 Dashboard Pages

### Overview
- Tournament statistics and key metrics
- Match timeline visualization
- Recent activity summary
- Player and civilization performance highlights

### Matches
- Individual match selection and analysis
- Turn progression tracking
- Resource development charts
- Event timeline visualization
- Territory control over time

### Players
- Player performance rankings
- Win rate analysis by civilization
- Head-to-head comparisons
- Activity and engagement metrics

### Maps
- Map performance analysis
- Territory control heatmaps
- Strategic position impact
- Game length by map characteristics

## 🗂️ Project Structure

```
tournament_visualizer/
├── data/                   # Database and data processing
│   ├── database.py        # DuckDB schema and connections
│   ├── parser.py          # XML save file parser
│   ├── etl.py            # Extract, Transform, Load pipeline
│   └── queries.py        # Reusable SQL queries
├── components/            # Reusable UI components
│   ├── filters.py        # Interactive filter components
│   ├── charts.py         # Chart generation functions
│   └── layouts.py        # Page layout components
├── pages/                 # Dashboard pages
│   ├── overview.py       # Tournament overview
│   ├── matches.py        # Match analysis
│   ├── players.py        # Player performance
│   └── maps.py          # Map visualizations
├── assets/               # Static assets
│   └── style.css        # Custom CSS styling
├── config.py            # Configuration settings
└── app.py              # Main Dash application
```

## ⚙️ Configuration

The application can be configured via environment variables:

```bash
# Database path
export TOURNAMENT_DB_PATH="custom_tournament_data.duckdb"

# Application host and port
export DASH_HOST="0.0.0.0"
export DASH_PORT="8080"

# Debug mode
export DASH_DEBUG="False"

# Tournament saves directory
export SAVES_DIRECTORY="path/to/saves"
```

## 🔧 Development

### Install Development Dependencies

```bash
uv sync --group dev
```

### Code Quality Tools

```bash
# Format code
uv run black tournament_visualizer/

# Lint code
uv run ruff check tournament_visualizer/

# Type checking
uv run mypy tournament_visualizer/

# Run tests
uv run pytest
```

### Development Mode

Run the application in development mode with auto-reload:

```bash
export DASH_DEBUG="True"
uv run python tournament_visualizer/app.py
```

## 📊 Data Sources

The tournament analyzer extracts data from Old World save files (`.zip` archives containing XML). Two types of historical data are captured:

### MemoryData Events
Character and diplomatic memories stored by the game AI (limited historical data):
- Character events (promotions, marriages, deaths)
- Tribal interactions
- Family events
- ~145 event types

### LogData Events
Comprehensive turn-by-turn gameplay logs:
- **Law Adoptions**: Which laws were adopted and when (`LAW_ADOPTED`)
- **Tech Discoveries**: Complete tech tree progression (`TECH_DISCOVERED`)
- **Goal Tracking**: Ambition start/completion events
- **City Events**: Founding, production, breaches
- ~79 event types

This enables analysis of:
- Time to reach 4 laws / 7 laws
- Tech progression paths
- Tech availability at law milestones
- Comparative player progression

## 📄 Database Schema

The application uses DuckDB with the following core tables:

- **matches**: Tournament match metadata and results
- **players**: Player information and performance stats
- **game_state**: Turn-by-turn game progression
- **territories**: Territory control over time
- **events**: Game events and timeline data (MemoryData + LogData)
- **resources**: Player resource progression

## 📈 Analytics Queries

### Law Progression
```python
from tournament_visualizer.data.database import get_database
from tournament_visualizer.data.queries import get_queries

db = get_database()
queries = get_queries()
progression = queries.get_law_progression_by_match(match_id=10)
# Returns: player_name, turn_to_4_laws, turn_to_7_laws, total_laws
```

### Tech Timeline
```python
from tournament_visualizer.data.queries import get_queries

queries = get_queries()
timeline = queries.get_tech_timeline_by_match(match_id=10)
# Returns: player_name, turn_number, tech_name, tech_sequence
```

### Techs at Law Milestone
```python
from tournament_visualizer.data.queries import get_queries

queries = get_queries()
techs = queries.get_techs_at_law_milestone(match_id=10, milestone=4)
# Returns: player_name, milestone_turn, tech_count, tech_list
```

## 🔍 Troubleshooting

### Import Issues

**No tournament files found:**
```bash
# Check directory exists and contains .zip files
ls saves/*.zip
```

**Database errors:**
```bash
# Remove existing database to start fresh
rm tournament_data.duckdb
uv run python import_tournaments.py --force
```

**Parsing errors:**
```bash
# Run with verbose logging to see detailed errors
uv run python import_tournaments.py --verbose
```

### Application Issues

**Port already in use:**
```bash
# Use a different port
export DASH_PORT="8051"
uv run python tournament_visualizer/app.py
```

**Module import errors:**
```bash
# Ensure dependencies are installed
uv sync
```

**No data showing:**
```bash
# Verify data was imported successfully
uv run python -c "
from tournament_visualizer.data.queries import get_queries
q = get_queries()
stats = q.get_database_statistics()
print(f'Matches: {stats.get(\"matches_count\", 0)}')
"
```

## 📈 Performance Tips

1. **Large Datasets**: For tournaments with many matches, consider using date filters to improve performance
2. **Database Size**: The DuckDB file grows with data - monitor disk space for large tournaments
3. **Memory Usage**: Close unused browser tabs when running resource-intensive visualizations
4. **Network**: For remote deployment, ensure adequate bandwidth for chart rendering

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and add tests
4. Run quality checks: `uv run black . && uv run ruff check . && uv run pytest`
5. Commit changes: `git commit -m "Add feature"`
6. Push to branch: `git push origin feature-name`
7. Create a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🎮 About Old World

Old World is a historical turn-based strategy game. This visualizer supports tournament save files in the standard `.zip` format exported from the game.

For more information about Old World: https://www.mohawkgames.com/oldworld/

---

**Note**: This application is not affiliated with or endorsed by Mohawk Games or the Old World development team.