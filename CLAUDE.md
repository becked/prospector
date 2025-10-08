We are using uv to manage Python

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

The project uses DuckDB (`tournament_data.duckdb`) for analytics.

**Always backup before major changes:**
```bash
cp tournament_data.duckdb tournament_data.duckdb.backup_$(date +%Y%m%d_%H%M%S)
```

**Inspect database:**
```bash
# Read-only mode (safe)
uv run duckdb tournament_data.duckdb -readonly

# Check schema
uv run duckdb tournament_data.duckdb -readonly -c "DESCRIBE events"

# Query data
uv run duckdb tournament_data.duckdb -readonly -c "SELECT COUNT(*) FROM events"
```

**Re-import data:**
```bash
# Test first (dry-run)
uv run python import_tournaments.py --directory saves --dry-run

# Full re-import (removes existing data)
uv run python import_tournaments.py --directory saves --force --verbose
```

### Validation After Changes

Always run validation scripts after database changes:
```bash
# For LogData-related changes
uv run python scripts/validate_logdata.py

# For analytics queries
uv run python scripts/verify_analytics.py
```

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

### XML Structure Notes

- Save files are `.zip` archives containing a single `.xml` file
- Extract for inspection: `unzip -p saves/match_*.zip | head -n 1000`
- Root element contains match metadata as attributes
- Player elements contain turn-by-turn data

## Documentation Standards

### Documentation Structure

```
docs/
├── developer-guide.md      # Architecture and how-to guides
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

## PyChallonge Library Notes

When working with the pychallonge library:

### API Response Structure
- The library returns **flat dictionaries**, not nested under keys like 'tournament' or 'match'
- Always handle both flat and nested structures for compatibility:
  ```python
  # Handle both nested and flat structure
  if 'match' in match:
      match_data = match['match']
  else:
      match_data = match
  ```

### Attachments
- Use `challonge.attachments.index(tournament_id, match_id)` (NOT `challonge.match_attachments`)
- Available fields:
  - `asset_url`: Download URL (missing protocol prefix, prepend 'https:')
  - `asset_file_name`: Original filename
  - `asset_file_size`: File size in bytes
  - `asset_content_type`: MIME type
- URLs come as `//s3.amazonaws.com/...` - add `https:` prefix for downloads

### Common Gotchas
- `attachment_count` can be `None`, always check `if attachment_count and attachment_count > 0:`
- Tournament data structure is flat, access directly: `tournament['name']` not `tournament['tournament']['name']`
- Match data structure is also flat: `match['id']` not `match['match']['id']`
