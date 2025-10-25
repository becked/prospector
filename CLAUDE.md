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

# For analytics queries
uv run python scripts/verify_analytics.py
```

### Participant Tracking

The database links players across matches using Challonge participant data.

**Key concepts:**
- `player_id` is match-scoped (different ID per match)
- `participant_id` is tournament-scoped (same ID across matches)
- Name matching uses normalized names (lowercase, no special chars)
- Manual overrides available for edge cases

**Sync workflow:**
```bash
# 1. Import participants from Challonge
uv run python scripts/sync_challonge_participants.py

# 2. Import save files
uv run python scripts/import_attachments.py --directory saves --force

# 3. Participants automatically linked (or run manually)
uv run python scripts/link_players_to_participants.py
```

**Cross-match queries** use `participant_id` to track individuals across multiple matches.

## Participant UI Integration

### Display Strategy

The web app shows **participants** (real people), not match-scoped player instances.

**What this means:**
- Players page: One row per person, even if they played multiple matches
- Stats aggregate across all matches for that person
- Unlinked players (⚠️) grouped by normalized name until linked

### Key Queries

```python
from tournament_visualizer.data.queries import get_queries

queries = get_queries()

# Player performance (one row per person)
df = queries.get_player_performance()
# Columns: player_name, participant_id, is_unlinked, total_matches, wins, win_rate, ...

# Head-to-head (matches by participant_id)
stats = queries.get_head_to_head_stats('Player1', 'Player2')
# Returns: total_matches, player1_wins, player2_wins, avg_match_length, ...

# Civilization stats (counts unique participants)
df = queries.get_civilization_performance()
# Columns: civilization, total_matches, unique_participants, ...
```

### Visual Indicators

- ⚠️ = Unlinked player (needs manual override or better name matching)
- **Bold civ** = Favorite/most-played civilization
- Linking Coverage % = Data quality metric

### Data Quality

Run validation:
```bash
uv run python scripts/validate_participant_ui_data.py
```

Shows linking coverage and potential match opportunities.

### Common Tasks

**Check linking status:**
```bash
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT
    COUNT(*) as total,
    COUNT(participant_id) as linked,
    ROUND(COUNT(participant_id) * 100.0 / COUNT(*), 1) as coverage
FROM players
"
```

**Find unlinked players:**
```bash
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT player_name, COUNT(*) as instances
FROM players
WHERE participant_id IS NULL
GROUP BY player_name_normalized, player_name
ORDER BY instances DESC
"
```

### Syncing Tournament Data

**IMPORTANT:** The server MUST be restarted after database updates!
- The app uses a persistent DuckDB connection that caches data
- Changes to the database file won't be visible until the connection is closed/reopened
- Always restart the server after importing new data

**Production (Fly.io):**

Use the sync script from your local machine to update production:
```bash
./scripts/sync_tournament_data.sh [app-name]
# Default app-name is "prospector"
```

This script processes data **locally** (much faster!) and then uploads to Fly.io:
1. Download all attachments from Challonge (to local `saves/` directory)
2. Import save files into DuckDB locally (~10x faster than on Fly.io)
3. Upload database directly to Fly.io (overwrites existing file)
4. Upload match winner overrides file (if exists)
5. Fix file permissions (664, owned by appuser) and restart app

**Note**: The app stays running during upload. Restart ensures the app picks up the new database cleanly.

**Why local processing?** Fly.io's shared CPUs and network-attached storage make XML parsing and database writes very slow. Processing locally on your machine is significantly faster.

**Requirements:**
- `flyctl` installed locally
- `uv` installed locally (for running Python scripts)
- Environment variables set locally: `CHALLONGE_KEY`, `CHALLONGE_USER`, `challonge_tournament_id`

**Local Development:**

For local development/testing, run the same workflow manually:
```bash
# Download attachments
uv run python scripts/download_attachments.py

# Import to database (processes locally)
uv run python scripts/import_attachments.py --directory saves --verbose

# Restart local server to pick up changes
uv run python manage.py restart
```

This is the same fast local processing that the production sync script uses!

## Google Drive Integration

### Overview

Tournament save files are stored in two locations:
1. **Challonge attachments** - Files under 250KB (most files)
2. **Google Drive** - Files over 250KB (fallback for oversized files)

The download script tries Challonge first, then falls back to Google Drive.

### Manual Overrides

**Problem**: Some Google Drive files can't be automatically matched to Challonge matches:
- Player names in filename don't match Challonge names
- In-game player names differ from both filename and Challonge

**Solution**: Manual override system via JSON configuration

**Location**: `data/gdrive_match_mapping_overrides.json` (not in git)

**Format**:
```json
{
  "challonge_match_id": {
    "gdrive_filename": "XX-player1-player2.zip",
    "reason": "Why this override is needed",
    "date_added": "YYYY-MM-DD"
  }
}
```

**Usage**:
1. Copy `data/gdrive_match_mapping_overrides.json.example` to `data/gdrive_match_mapping_overrides.json`
2. Add override entry for unmatched file
3. Re-run mapping: `uv run python scripts/generate_gdrive_mapping.py`
4. For production: `./scripts/sync_tournament_data.sh` (uploads override file automatically)

**Note**: If the in-game player name also differs, you'll also need to add a participant name override (see Participant Name Overrides section).

### Setup

**Local Development:**

1. Get a Google Drive API key:
   - Visit https://console.cloud.google.com/
   - Create project or use existing
   - Enable "Google Drive API"
   - Create API Key (Credentials → Create → API Key)
   - Optionally restrict to Drive API only

2. Add to `.env`:
   ```bash
   GOOGLE_DRIVE_API_KEY=your_api_key_here
   GOOGLE_DRIVE_FOLDER_ID=1ss8ToApXPY7o2syLV76i_CJdoS-lnHQk
   ```

**Production (Fly.io):**

```bash
fly secrets set GOOGLE_DRIVE_API_KEY="your_key" -a prospector
```

### Workflow

The Google Drive integration is automatic:

```bash
# Generate mapping (run once, or when new files added)
uv run python scripts/generate_gdrive_mapping.py

# Download saves (tries Challonge, falls back to GDrive)
uv run python scripts/download_attachments.py

# Import and sync as usual
uv run python scripts/import_attachments.py --directory saves --force
uv run python scripts/link_players_to_participants.py
```

For production sync:
```bash
# Automatically handles GDrive mapping and download
./scripts/sync_tournament_data.sh
```

### Files

**Data:**
- `data/gdrive_match_mapping.json` - Auto-generated mapping (not in git)
- `data/gdrive_match_mapping_overrides.json` - Manual overrides (not in git)
- `data/gdrive_match_mapping_overrides.json.example` - Override file template

**Scripts:**
- `scripts/generate_gdrive_mapping.py` - Auto-matches GDrive files to Challonge matches
- `scripts/download_attachments.py` - Downloads from Challonge and GDrive

**Modules:**
- `tournament_visualizer/data/gdrive_client.py` - Google Drive API client

### Troubleshooting

**No GDrive files downloaded:**
- Check that `GOOGLE_DRIVE_API_KEY` is set
- Run `generate_gdrive_mapping.py` to create mapping
- Verify mapping file exists: `cat data/gdrive_match_mapping.json`

**Low confidence matches:**
- Review mapping output for confidence scores
- Add manual overrides to `data/gdrive_match_mapping_overrides.json`
- Re-run `generate_gdrive_mapping.py` to apply overrides
- Player name mismatches require both GDrive and participant name overrides

**API quota errors:**
- Google Drive API has rate limits
- Script handles this automatically with retries
- If persistent, wait a few minutes and retry

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

## Old World Save File Structure

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

**Database Storage:**
- `player_yield_history.amount` - INT storing raw values (215, not 21.5)
- `player_statistics.value` - DECIMAL(10,1) for yield_stockpile category

**Important:** Only queries that return data for display should divide by 10.

**Why this approach?**
- Preserves exact XML values in database
- No data loss from premature conversion
- Flexible for future changes (raw data available)
- Simple parser logic

**Reference:** Old World developer documentation on internal yield storage format
**See Also:**
- `docs/reports/yield-display-scale-issue.md` - Full investigation
- `docs/reports/yield-fix-implementation-summary.md` - Implementation guide

### Data Sources

**MemoryData Events** (limited historical data):
- Character/diplomatic memories for AI decision-making
- Event types: `MEMORYPLAYER_*`, `MEMORYFAMILY_*`, etc.
- Location: Various places in XML

**LogData Events** (comprehensive turn-by-turn logs):
- Complete gameplay history
- Event types: `LAW_ADOPTED`, `TECH_DISCOVERED`, `GOAL_STARTED`, etc.
- Location: `Player/PermanentLogList/LogData` elements
- **No overlap with MemoryData** - different event type namespaces

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

### Match Winner Overrides

**Problem**: Some save files have incorrect winner data due to:
- Old World bug preventing access to completed saves
- Manual corruption from TO opening files to reveal maps
- Missing TeamVictoriesCompleted data

**Solution**: Manual override system via JSON configuration

**Location**: `data/match_winner_overrides.json` (not in git)

**Format**:
```json
{
  "challonge_match_id": {
    "winner_player_name": "PlayerName",
    "reason": "Why this override is needed",
    "date_added": "YYYY-MM-DD",
    "notes": "Optional additional context"
  }
}
```

**Usage**:
1. Copy `data/match_winner_overrides.json.example` to `data/match_winner_overrides.json`
2. Add override entry for problematic match
3. Re-import data: `uv run python scripts/import_attachments.py --force`
4. For production: `./scripts/sync_tournament_data.sh` (uploads override file automatically)

**Priority**: Overrides take precedence over save file data
**Logging**: Check logs for "Applying winner override" messages
**Validation**: Errors logged if override player name not found in save file

### Participant Name Overrides

**Problem**: Save file player names often don't match Challonge participant names:
- Save files store short nicknames (e.g., "Ninja", "Fonder")
- Challonge uses full usernames (e.g., "Ninjaa", "FonderCargo348")
- Normalized name matching fails on these differences

**Solution**: Manual override system via JSON configuration

**Location**: `data/participant_name_overrides.json` (not in git)

**Format**:
```json
{
  "challonge_match_id": {
    "SaveFileName": {
      "participant_id": 272470588,
      "reason": "Save file uses 'Ninja' but Challonge name is 'Ninjaa'",
      "date_added": "YYYY-MM-DD"
    }
  }
}
```

**Key Design**:
- Uses **`challonge_match_id`** (from Challonge API) - stable across database re-imports
- NOT `match_id` (database row ID) - that would break on re-import
- Consistent with other override systems (winner, pick order, GDrive mapping)

**Usage**:
1. Copy `data/participant_name_overrides.json.example` to `data/participant_name_overrides.json`
2. Find IDs using SQL:
   ```bash
   # Find challonge_match_id
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT match_id, challonge_match_id, player1_name, player2_name
   FROM matches
   "

   # Find participant_id
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT participant_id, display_name
   FROM tournament_participants
   "
   ```
3. Add override entries for mismatched names
4. Run linking: `uv run python scripts/link_players_to_participants.py`
5. For production: `./scripts/sync_tournament_data.sh` (uploads override file automatically)

### Override Systems Design

All override files in this application follow a consistent design:

| Override File | Purpose | Key Type | Stability |
|--------------|---------|----------|-----------|
| `match_winner_overrides.json` | Fix corrupted winner data | `challonge_match_id` | ✅ Stable |
| `pick_order_overrides.json` | Manually link games to matches | `game_number` | ✅ Stable |
| `gdrive_match_mapping_overrides.json` | Map GDrive files to matches | `challonge_match_id` | ✅ Stable |
| `participant_name_overrides.json` | Link mismatched player names | `challonge_match_id` | ✅ Stable |

**Design Principles**:
1. **Use stable external IDs** - Never use auto-incrementing database row IDs
2. **Survive database re-imports** - Overrides must work after data is reimported
3. **JSON format** - All overrides use JSON for easy editing
4. **Not in git** - Override files contain tournament-specific data
5. **Example templates** - Each has a `.example` file showing format

**Why `challonge_match_id` is stable**:
- Assigned by Challonge API when match is created
- Never changes for the lifetime of the match
- Same value across all database imports
- Globally unique within the tournament

**Why database `match_id` is NOT stable**:
- Auto-incrementing row ID assigned during import
- Changes based on import order (file system, API response order)
- Different value after each database re-import
- Only unique within that specific database instance

## Pick Order Data Integration

### Overview

Tournament games have a draft phase where one player picks their nation first, then the other player picks second. Save files don't capture this information (both nations show as chosen on turn 1), so we integrate pick order data from a Google Sheet maintained by the tournament organizer.

**Data Sources:**
1. **Save files** - Contain nations played and game outcomes
2. **Google Sheet (GAMEDATA tab)** - Contains pick order information

**Use Cases:**
- Does picking first or second affect win rate?
- Which nations are picked first most often?
- Counter-pick analysis (what beats what?)
- Player pick order preferences

### Database Schema

**`pick_order_games` table** - Stores parsed sheet data:
- Game number, round, player names from sheet
- First/second pick nations
- Matching metadata (match_id, confidence, etc.)

**`matches` table additions:**
- `first_picker_participant_id` - Who picked first
- `second_picker_participant_id` - Who picked second

### Workflow

The pick order integration is automatic during full sync:

```bash
# Full sync (includes pick order)
./scripts/sync_tournament_data.sh
```

Or run manually:

```bash
# 1. Fetch and parse sheet data
uv run python scripts/sync_pick_order_data.py

# 2. Match games to database
uv run python scripts/match_pick_order_games.py
```

### Configuration

**.env variables:**
```bash
# Same API key used for Google Drive
GOOGLE_DRIVE_API_KEY=your_api_key_here

# Spreadsheet ID (from sheet URL)
GOOGLE_SHEETS_SPREADSHEET_ID=19t5AbJtQr5kZ62pw8FJ-r2b9LVkz01zl2GUNWkIrhAc

# Sheet GID (optional, has default)
GOOGLE_SHEETS_GAMEDATA_GID=1663493966
```

**For production (Fly.io):**
```bash
# API key is already set for GDrive
# Just add spreadsheet ID if different
fly secrets set GOOGLE_SHEETS_SPREADSHEET_ID="id" -a prospector
```

### Manual Overrides

Some games may fail to auto-match (name mismatches, nation mismatches). Create manual overrides:

1. Copy example file:
   ```bash
   cp data/pick_order_overrides.json.example data/pick_order_overrides.json
   ```

2. Add override entries for failing games:
   ```json
   {
     "game_1": {
       "challonge_match_id": 426504734,
       "reason": "Player name mismatch: sheet has 'Ninja', save has 'Ninjaa'",
       "date_added": "2025-10-17"
     }
   }
   ```

3. Re-run matching:
   ```bash
   uv run python scripts/match_pick_order_games.py
   ```

### Analytics

Example queries available in `scripts/pick_order_analytics_examples.sql`:

```bash
# Run all examples
uv run duckdb data/tournament_data.duckdb -readonly < scripts/pick_order_analytics_examples.sql
```

**Query examples:**
- Overall pick order win rate
- Nation performance by pick position
- Counter-pick patterns
- Player pick preferences
- Data quality checks

### Troubleshooting

**No pick order data synced:**
- Check `GOOGLE_DRIVE_API_KEY` is set
- Verify `GOOGLE_SHEETS_SPREADSHEET_ID` is correct
- Check sheet is publicly readable

**Low match rate:**
- Check player names in sheet vs save files (use `validate_participants.py`)
- Add overrides to `data/pick_order_overrides.json`
- Run matching with `--verbose` flag to see why matches fail

**Nation mismatches:**
- Verify nations in sheet match civilization names exactly:
  - Correct: "Assyria", "Egypt", "Persia"
  - Incorrect: "ASSYRIA", "egyptian", "Persians"
- Check if player changed nation after draft (needs override)

**Check data quality:**
```bash
# See how many games have pick order data
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT
    COUNT(*) as total_matches,
    COUNT(first_picker_participant_id) as with_pick_order,
    ROUND(COUNT(first_picker_participant_id) * 100.0 / COUNT(*), 1) as coverage_pct
FROM matches
"
```

### Files

**Data:**
- `data/pick_order_overrides.json` - Manual match overrides (not in git)
- `data/pick_order_overrides.json.example` - Override file template

**Scripts:**
- `scripts/sync_pick_order_data.py` - Fetch and parse sheet
- `scripts/match_pick_order_games.py` - Match to database
- `scripts/pick_order_analytics_examples.sql` - Example queries

**Modules:**
- `tournament_visualizer/data/gsheets_client.py` - Google Sheets API client
- `tournament_visualizer/data/gamedata_parser.py` - Sheet parser

**Documentation:**
- `docs/migrations/008_add_pick_order_tracking.md` - Schema migration docs
- `docs/plans/pick-order-integration-implementation-plan.md` - Full implementation plan

## Match Narrative Summaries

### Overview

Tournament matches include AI-generated narrative summaries on match detail pages.

**How it works:**
- Analyzes all match events (techs, laws, combat, cities, etc.)
- Uses Claude API with two-pass approach:
  1. Extract structured timeline from events
  2. Generate 2-3 paragraph narrative from timeline
- Stored in `matches.narrative_summary` column

### Generation

**Local Development:**

Generate narratives for matches without summaries:
```bash
uv run python scripts/generate_match_narratives.py
```

Regenerate specific match:
```bash
uv run python scripts/generate_match_narratives.py --match-id 19 --force
```

Regenerate all narratives:
```bash
uv run python scripts/generate_match_narratives.py --force
```

**Production Sync:**

Narratives are automatically generated during sync:
```bash
./scripts/sync_tournament_data.sh
```

This generates narratives locally before uploading database to Fly.io.

### Requirements

**API Key:**
- `ANTHROPIC_API_KEY` must be set in `.env`
- Get key from https://console.anthropic.com/

**For production (Fly.io):**
```bash
fly secrets set ANTHROPIC_API_KEY="your_key" -a prospector
```

### Database Schema

```sql
-- Narratives stored in matches table
ALTER TABLE matches ADD COLUMN narrative_summary TEXT;
```

See `docs/migrations/009_add_match_narrative_summary.md` for details.

### Implementation

**Modules:**
- `tournament_visualizer/data/anthropic_client.py` - API client with retry logic
- `tournament_visualizer/data/event_formatter.py` - Format events for LLM
- `tournament_visualizer/data/narrative_generator.py` - Two-pass generation

**Scripts:**
- `scripts/generate_match_narratives.py` - Generate narratives

**Tests:**
- `tests/test_event_formatter.py`
- `tests/test_narrative_generator.py`

### Troubleshooting

**No narratives generated:**
- Check `ANTHROPIC_API_KEY` is set
- Run with `--verbose` flag to see errors
- Check API quota/billing at https://console.anthropic.com/

**API errors:**
- Rate limits handled with exponential backoff
- Transient errors retried automatically
- Persistent errors logged and skipped

**Narrative quality issues:**
- Regenerate specific match with `--force`
- Check event data quality in database
- Review prompts in `narrative_generator.py`

## Deployment (Fly.io)

### Quick Reference

**First time deployment:**
```bash
fly launch                    # Create app (say NO to database and deploy)
fly volumes create tournament_data --size 1 --region sjc -a prospector
fly secrets set CHALLONGE_KEY="key" CHALLONGE_USER="user" challonge_tournament_id="id" -a prospector
fly deploy                    # Deploy the app
./scripts/sync_tournament_data.sh  # Sync tournament data
```

**Update code:**
```bash
fly deploy
```

**Update tournament data:**
```bash
./scripts/sync_tournament_data.sh
```

**View logs:**
```bash
fly logs -a prospector
```

**Full deployment guide:** See `docs/deployment-guide.md` for complete instructions, troubleshooting, and advanced topics.

## Documentation Standards

### Documentation Structure

```
docs/
├── developer-guide.md      # Architecture and how-to guides
├── deployment-guide.md     # Fly.io deployment instructions
├── migrations/             # Database schema changes
│   └── 001_*.md           # Numbered migration docs
└── plans/                  # Implementation plans and investigations
    └── feature-name-implementation-plan.md
```

### Migration Documentation

Every schema change needs a migration doc in `docs/migrations/`:
- **Overview**: What and why
- **Schema Changes**: Specific SQL changes
- **Rollback Procedure**: How to undo
- **Verification**: How to test it worked
- **Related Files**: What code changed

### Implementation Plans

For complex features, create an implementation plan in `docs/plans/`:
- Task breakdown with time estimates
- Testing strategy
- Success metrics
- Commit checkpoints

See `docs/plans/logdata-ingestion-implementation-plan.md` as an example.

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
