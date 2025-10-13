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

# For analytics queries
uv run python scripts/verify_analytics.py
```

### Syncing Tournament Data

**IMPORTANT:** The server MUST be restarted after database updates!
- The app uses a persistent DuckDB connection that caches data
- Changes to the database file won't be visible until the connection is closed/reopened
- Always restart the server after importing new data

**Production (Fly.io) - Automated (Recommended):**

Use the sync script from your local machine to update production:
```bash
./scripts/sync_tournament_data.sh [app-name]
# Default app-name is "prospector"
```

This script processes data **locally** (much faster!) and then uploads to Fly.io:
1. Download all attachments from Challonge (to local `saves/` directory)
2. Import save files into DuckDB locally (~10x faster than on Fly.io)
3. Upload new database to temporary location on Fly.io (while app is running)
4. Stop the Fly.io machine (closes database connections)
5. Start the Fly.io machine
6. Replace old database with new one and fix permissions (664, owned by appuser)
7. Restart app to load the new data

**Why local processing?** Fly.io's shared CPUs and network-attached storage make XML parsing and database writes very slow. Processing locally on your machine is significantly faster.

Requires:
- `flyctl` installed locally
- `uv` installed locally (for running Python scripts)
- Environment variables set locally: `CHALLONGE_KEY`, `CHALLONGE_USER`, `challonge_tournament_id`

**Production (Fly.io) - Remote Processing (Legacy):**

For the old workflow that processes on Fly.io (slower but doesn't require local setup):
```bash
./scripts/sync_tournament_data_remote.sh [app-name]
```

This processes data on the Fly.io server itself. Requires only `flyctl` locally, but is much slower due to resource constraints.

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
