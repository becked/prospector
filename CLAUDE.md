We are using uv to manage Python

## Development Principles

### YAGNI (You Ain't Gonna Need It)
- Only implement features/fixes that are needed NOW
- Don't add abstractions or features that "might be useful later"
- Example: "Only fix the player ID mapping, don't refactor other things"
- Example: "Only implement law and tech events now, not all 79 event types"

### DRY (Don't Repeat Yourself)
- Reuse existing code patterns and logic
- If the same logic exists elsewhere (e.g., LogData player ID mapping), use the same approach
- Don't duplicate code - extract to shared functions if needed
- Example: MemoryData and LogData should use identical player ID conversion: `database_player_id = xml_player_id + 1`

### Atomic Commits
- Each commit should represent ONE logical change
- Commit frequently (after each task/subtask completion)
- Commit messages should clearly describe what changed and why
- Don't batch multiple unrelated changes into one commit

### Code Comments
- Comments should explain **WHY**, not **WHAT**
- The code itself should be clear enough to show what it does
- Document edge cases, business rules, and non-obvious decisions
- Example: Good comment explains XML ID mapping rationale, not just the formula

## Commit Messages

Do NOT include these lines in commit messages:
- `🤖 Generated with [Claude Code](https://claude.com/claude-code)`
- `Co-Authored-By: Claude <noreply@anthropic.com>`

Use conventional commit format:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation
- `test:` for tests
- `refactor:` for code changes that don't add features or fix bugs
- `perf:` for performance improvements
- `chore:` for maintenance tasks

## Application Management

Use `manage.py` to control the Dash web application:
- `uv run python manage.py start` - Start the server
- `uv run python manage.py stop` - Stop the server
- `uv run python manage.py restart` - Restart the server (useful after code changes)
- `uv run python manage.py status` - Check server status
- `uv run python manage.py logs` - Show server logs
- `uv run python manage.py logs -f` - Follow server logs (like tail -f)

The server runs on http://localhost:8050 by default.

## Database Management

### DuckDB Operations

The project uses DuckDB (`data/tournament_data.duckdb`) for analytics.

**Always backup before major changes:**
```bash
cp data/tournament_data.duckdb data/tournament_data.duckdb.backup_$(date +%Y%m%d_%H%M%S)
```

**Inspect database:**
```bash
# Read-only mode (safe)
uv run duckdb data/tournament_data.duckdb -readonly

# Check schema
uv run duckdb data/tournament_data.duckdb -readonly -c "DESCRIBE events"

# Query data
uv run duckdb data/tournament_data.duckdb -readonly -c "SELECT COUNT(*) FROM events"
```

**Re-import data:**
```bash
# Test first (dry-run)
uv run python scripts/import_attachments.py --directory saves --dry-run

# Full re-import (removes existing data)
uv run python scripts/import_attachments.py --directory saves --force --verbose
```

### Validation After Changes

Always run validation scripts after database changes:
```bash
# For LogData-related changes
uv run python scripts/validate_logdata.py

# For MemoryData-related changes
uv run python scripts/validate_memorydata_ownership.py

# For participant tracking changes
uv run python scripts/validate_participants.py

# For participant UI data quality
uv run python scripts/validate_participant_ui_data.py

# For city data
uv run python scripts/validate_city_data.py

# For analytics queries
uv run python scripts/verify_analytics.py
```

### Database Schema

**Always reference the schema documentation before writing queries:**
- `docs/schema.sql` - Exact DDL with types and constraints
- `docs/database-schema.md` - Table descriptions and relationships

**After schema changes, update documentation:**
```bash
uv run python scripts/export_schema.py
git add docs/schema.sql docs/database-schema.md
```

## Critical Domain Knowledge

### Player ID Mapping (Critical!)

**XML uses 0-based IDs, database uses 1-based:**
```python
# XML: <Player ID="0">
# Database: player_id = 1
database_player_id = int(xml_id) + 1
```

**Important:** Player ID="0" is valid and should NOT be skipped!

### Yield Value Display Scale (Critical!)

**Old World stores all yield values in units of 0.1 internally.**

**Current Implementation:**
- Parser stores **raw XML values** (215, not 21.5)
- Database stores **raw values** as-is from parser
- Queries **must divide by 10** to get display-ready values
- Examples:
  - XML: `<YIELD_SCIENCE>215</YIELD_SCIENCE>`
  - Database: `player_yield_history.amount = 215` (raw)
  - Query: `SELECT amount / 10.0 AS amount` → Display: `21.5 science/turn`

**Affected Data:**
- `YieldRateHistory` - Turn-by-turn yield production rates (all turns, all yields)
- `YieldStockpile` - Current resource stockpiles (end-of-game balances)
- All 14 yield types: SCIENCE, CIVICS, TRAINING, CULTURE, MONEY, FOOD, GROWTH, etc.

**Parser Implementation:**
```python
# In parser.py extract_yield_history()
amount = self._safe_int(turn_elem.text)  # Stores raw value (215)
```

**Query Implementation:**
```python
# In queries.py get_yield_history_by_match()
SELECT
    yh.amount / 10.0 AS amount  -- Divide by 10 for display
FROM player_yield_history yh
```

**Important:** Only queries that return data for display should divide by 10.

**Why this approach?**
- Preserves exact XML values in database
- No data loss from premature conversion
- Flexible for future changes (raw data available)
- Simple parser logic

**See Also:**
- `docs/archive/reports/yield-display-scale-issue.md` - Full investigation
- `docs/archive/reports/yield-fix-implementation-summary.md` - Implementation guide

### Memory Event Ownership

**Key Concept**: MemoryData events are stored in a player's MemoryList, representing that player's perspective/memory.

**XML Structure:**
```xml
<Player ID="0">  <!-- Owner player -->
  <MemoryList>
    <MemoryData>
      <Type>MEMORYPLAYER_ATTACKED_CITY</Type>
      <Player>1</Player>  <!-- Subject player (opponent) -->
      <Turn>63</Turn>
    </MemoryData>
    <MemoryData>
      <Type>MEMORYTRIBE_ATTACKED_UNIT</Type>
      <Tribe>TRIBE_RAIDERS</Tribe>  <!-- NO <Player> child -->
      <Turn>63</Turn>
    </MemoryData>
  </MemoryList>
</Player>
```

**Player ID Assignment:**

1. **MEMORYPLAYER_* events**: Use `<Player>` child element (the opponent/subject)
   - Example: If Becked's memory says "MEMORYPLAYER_ATTACKED_CITY Player=1",
     it means Becked remembers Fluffbunny (Player 1) attacking a city

2. **MEMORYTRIBE/FAMILY/RELIGION_* events**: Use owner `Player[@ID]` (the viewer)
   - Example: If Becked's memory says "MEMORYTRIBE_ATTACKED_UNIT Tribe=Raiders",
     it means Becked witnessed/experienced Raiders attacking units
   - No `<Player>` child element exists for these events

**Database Mapping:**
- XML `Player[@ID="0"]` → Database `player_id=1`
- XML `Player[@ID="1"]` → Database `player_id=2`
- Consistent with LogData event mapping

### XML Structure Notes

- Save files are `.zip` archives containing a single `.xml` file
- Extract for inspection: `unzip -p saves/match_*.zip | head -n 1000`
- Root element contains match metadata as attributes
- Player elements contain turn-by-turn data

## City Data Analysis

### Overview
City data tracks expansion patterns, production strategies, and territorial control for each tournament match.

### What We Track
- **Cities**: Name, owner, location, founding turn, population
- **Production**: Units built per city (settlers, military, workers)
- **Projects**: City projects completed (forums, temples, wonders)
- **Ownership**: Original founder vs. current owner (conquest tracking)

### Database Tables
- `cities` - Core city attributes
- `city_unit_production` - Units built per city
- `city_projects` - Projects completed per city

See: `docs/database-schema.md` for complete schema

### Querying City Data

```python
from tournament_visualizer.data.queries import (
    get_match_cities,
    get_player_expansion_stats,
    get_production_summary
)

# Get all cities in a match
cities = get_match_cities(match_id=1)
for city in cities:
    print(f"{city['city_name']} founded turn {city['founded_turn']}")

# Get expansion statistics
stats = get_player_expansion_stats(match_id=1)
for player in stats:
    print(f"{player['player_name']}: {player['total_cities']} cities")

# Get production summary
summary = get_production_summary(match_id=1)
for player in summary:
    print(f"{player['player_name']}: {player['settlers']} settlers")
```

### Validation

After re-importing data, validate city data:
```bash
uv run python scripts/validate_city_data.py
```

### Common Queries

```sql
-- Top expanders (most cities)
SELECT
    p.player_name,
    COUNT(c.city_id) as total_cities
FROM cities c
JOIN players p ON c.match_id = p.match_id AND c.player_id = p.player_id
GROUP BY p.player_name
ORDER BY total_cities DESC
LIMIT 10;

-- Expansion speed (cities per turn)
SELECT
    p.player_name,
    COUNT(c.city_id) as cities,
    MAX(c.founded_turn) as last_city_turn,
    CAST(COUNT(c.city_id) AS FLOAT) / MAX(c.founded_turn) as expansion_rate
FROM cities c
JOIN players p ON c.match_id = p.match_id AND c.player_id = p.player_id
GROUP BY p.player_name
ORDER BY expansion_rate DESC;

-- Military vs. economic production
SELECT
    p.player_name,
    SUM(CASE WHEN prod.unit_type IN ('UNIT_SPEARMAN', 'UNIT_ARCHER', 'UNIT_HORSEMAN')
        THEN prod.count ELSE 0 END) as military_units,
    SUM(CASE WHEN prod.unit_type IN ('UNIT_SETTLER', 'UNIT_WORKER')
        THEN prod.count ELSE 0 END) as economic_units
FROM city_unit_production prod
JOIN cities c ON prod.match_id = c.match_id AND prod.city_id = c.city_id
JOIN players p ON c.match_id = p.match_id AND c.player_id = p.player_id
GROUP BY p.player_name;

-- Captured cities
SELECT
    p.player_name,
    COUNT(*) as cities_captured
FROM cities c
JOIN players p ON c.match_id = p.match_id AND c.player_id = p.player_id
WHERE c.first_player_id != c.player_id
GROUP BY p.player_name
ORDER BY cities_captured DESC;
```

### Troubleshooting

**No cities in database:**
- Run validation: `uv run python scripts/validate_city_data.py`
- Check migration applied: `uv run duckdb data/tournament_data.duckdb -c "SHOW TABLES"`
- Re-import data: `uv run python scripts/import_attachments.py --directory saves --force`

**Incorrect player IDs:**
- Verify player ID conversion: XML uses 0-based, DB uses 1-based
- Check validation script output for errors

**Missing production data:**
- Some cities may have no production (newly founded)
- Check if `<UnitProductionCounts>` is empty in XML

### Override Systems Quick Reference

All override files follow a consistent design for data quality management:

| Override File | Purpose | Key Type | Location |
|--------------|---------|----------|----------|
| `match_winner_overrides.json` | Fix corrupted winner data | `challonge_match_id` | `data/` |
| `pick_order_overrides.json` | Manually link games to matches | `game_number` | `data/` |
| `gdrive_match_mapping_overrides.json` | Map GDrive files to matches | `challonge_match_id` | `data/` |
| `participant_name_overrides.json` | Link mismatched player names | `challonge_match_id` | `data/` |

**Design Principles:**
- Use stable external IDs (never database row IDs)
- Survive database re-imports
- JSON format with `.example` templates
- Not in git (tournament-specific data)

**See:** `docs/developer-guide.md` for complete override workflows

## Testing & Code Quality

### Running Tests

```bash
# All tests
uv run pytest -v

# With coverage report
uv run pytest --cov=tournament_visualizer

# Specific test file
uv run pytest tests/test_parser_logdata.py -v
```

### Code Formatting & Linting

**Before committing, always run:**
```bash
# Format code
uv run black tournament_visualizer/

# Lint code
uv run ruff check tournament_visualizer/

# Auto-fix linting issues
uv run ruff check --fix tournament_visualizer/
```

### Test-Driven Development

Follow TDD principles for new features:
1. Write failing test first
2. Implement minimum code to pass
3. Refactor while keeping tests green
4. Commit when all tests pass

## Dashboard & Chart Conventions

### Chart Titles

**Do NOT add internal chart titles** - the card header provides the title.

**Pattern:**
```python
# ❌ WRONG - Redundant title
fig.update_layout(
    title_text="Archetype Performance",  # Don't do this
    height=400,
)

# ✅ CORRECT - No title, card header shows it
fig.update_layout(
    height=400,
    showlegend=True,
)
```

**Why:** We follow the standard dashboard pattern where one card = one chart:
- Card header provides context in the UI
- Internal chart title would be redundant
- Cleaner, more modern appearance
- Follows industry standards (Grafana, Tableau, etc.)

**Exception:** Only add chart titles if multiple charts appear in a single card (rare).

## Chyllonge Library Notes

When working with the chyllonge library (Challonge API client):

### Setup
- Requires environment variables:
  - `CHALLONGE_KEY`: API key from https://challonge.com/settings/developer
  - `CHALLONGE_USER`: Challonge username
- Initialize client: `api = ChallongeAPI()`

### API Response Structure
- The library returns **flat dictionaries**, not nested under keys like 'tournament' or 'match'
- Access fields directly: `match['id']`, `tournament['name']`
- No need to check for nested structures like `match['match']` or `tournament['tournament']`

### Common API Calls
```python
# Get all matches
matches = api.matches.get_all(tournament_id)

# Get all attachments for a match
attachments = api.attachments.get_all(tournament_id, match_id)
```

### Attachments
- Available fields:
  - `asset_url`: Download URL (missing protocol prefix, prepend 'https:')
  - `asset_file_name`: Original filename
  - `asset_file_size`: File size in bytes
  - `asset_content_type`: MIME type
- URLs come as `//s3.amazonaws.com/...` - add `https:` prefix for downloads

### Common Gotchas
- `attachment_count` can be `None`, always check `if attachment_count and attachment_count > 0:`
- All responses are flat dictionaries, consistent API design
- Supports Python 3.8-3.11

## Need More Details?

For comprehensive documentation, see:

### Development
- **Architecture & Features**: `docs/developer-guide.md`
  - Turn-by-turn history tables
  - Data integration (participants, Google Drive, pick order, narratives)
  - Override systems (detailed workflows)
  - Event system architecture
  - Testing architecture

### Deployment & Operations
- **Deployment Guide**: `docs/deployment-guide.md`
  - Initial Fly.io deployment
  - Data synchronization workflows
  - Troubleshooting

### Database
- **Schema Changes**: `docs/migrations/`
  - Numbered migration docs with rollback procedures

### Documentation
- **Documentation Guide**: `docs/README.md`
  - Documentation structure and lifecycle
  - Finding information
  - Contributing guidelines
