# Developer Guide

## Architecture Overview

### Data Flow

The tournament visualizer follows a clear data pipeline:

1. **Save files (`.zip`)** → **Parser** → **Events (dicts)**
2. **Events** → **ETL** → **DuckDB tables**
3. **DuckDB** → **Queries** → **Analytics DataFrames**
4. **DataFrames** → **Dash components** → **Web UI**

### Key Components

#### Parser (`tournament_visualizer/data/parser.py`)

The `OldWorldSaveParser` class extracts data from Old World save files (XML format):

- **`extract_events()`**: MemoryData events (legacy)
  - Character and diplomatic memories
  - Limited historical data
  - Event types: `MEMORYPLAYER_*`, `MEMORYFAMILY_*`, etc.

- **`extract_logdata_events()`**: LogData events (NEW)
  - Comprehensive turn-by-turn gameplay logs
  - Law adoptions (`LAW_ADOPTED`)
  - Tech discoveries (`TECH_DISCOVERED`)
  - Goal tracking, city events, etc.

- **`extract_players()`**: Player metadata
  - Player names, civilizations, scores
  - Uses 1-based player IDs for database consistency

- **`extract_tech_progress()`**: Final tech state
  - Tech research counts at end of match

- **`extract_player_statistics()`**: Detailed player stats
  - Production, improvements, units, etc.

#### ETL (`tournament_visualizer/data/etl.py`)

Orchestrates the data loading process:

- **`process_save_file()`**: Main ETL pipeline
  - Parses save file
  - Inserts into database
  - Maps player IDs
  - Handles transactions

- **`initialize_database()`**: Sets up schema
  - Creates tables if not exists
  - Applies indexes for performance

**Event Merging:**
```python
# Extract both event types
memory_events = parser.extract_events()
logdata_events = parser.extract_logdata_events()

# Merge - no deduplication needed!
# MemoryData and LogData have separate event type namespaces
events = memory_events + logdata_events
```

#### Database (`tournament_visualizer/data/database.py`)

DuckDB embedded database with optimized schema:

- **Events table**: Stores all historical data
- **Indexes**: `(event_type, player_id, turn_number)` for fast filtering
- **JSON support**: `event_data` column stores event-specific details

#### Queries (`tournament_visualizer/data/queries.py`)

Pre-built SQL queries for analytics:

- **`get_law_progression_by_match()`**: Law milestones (4 laws, 7 laws)
- **`get_tech_timeline_by_match()`**: Tech progression timeline
- **`get_tech_count_by_turn()`**: Cumulative tech counts (for racing charts)
- **`get_techs_at_law_milestone()`**: Combined law/tech analysis

## Adding New Event Types

To add support for a new LogData event type:

### 1. Update Parser

Add event data extraction in `_build_logdata_event_data()`:

```python
def _build_logdata_event_data(self, event_type, data1, data2, data3):
    if event_type == 'YOUR_NEW_TYPE' and data1:
        return {'your_field': data1}

    # Existing code...
```

### 2. Add Description Formatting

Add human-readable formatting in `_format_logdata_event()`:

```python
def _format_logdata_event(self, event_type, event_data, text):
    if event_type == 'YOUR_NEW_TYPE' and event_data:
        field_value = event_data['your_field']
        return f"Your description: {field_value}"

    # Existing code...
```

### 3. Write Tests

Add test cases in `tests/test_parser_logdata.py`:

```python
def test_extract_your_new_type(sample_xml_path):
    parser = OldWorldSaveParser(str(sample_xml_path))
    parser.extract_and_parse()

    events = parser.extract_logdata_events()
    new_type_events = [e for e in events if e['event_type'] == 'YOUR_NEW_TYPE']

    assert len(new_type_events) > 0
    assert 'your_field' in new_type_events[0]['event_data']
```

### 4. Add Query (if needed)

Create analytics query in `queries.py`:

```python
def get_your_analysis(self, match_id: int) -> pd.DataFrame:
    """Get analysis for your new event type.

    Args:
        match_id: Match ID to analyze

    Returns:
        DataFrame with analysis results
    """
    query = """
    SELECT
        e.player_id,
        p.player_name,
        COUNT(*) as event_count
    FROM events e
    JOIN players p ON e.match_id = p.match_id AND e.player_id = p.player_id
    WHERE e.event_type = 'YOUR_NEW_TYPE'
        AND e.match_id = ?
    GROUP BY e.player_id, p.player_name
    """

    with self.db.get_connection() as conn:
        return conn.execute(query, [match_id]).df()
```

## Testing Strategy

### Unit Tests

Test individual parsing methods with small XML fixtures:

```bash
uv run pytest tests/test_parser_logdata.py -v
```

**Benefits:**
- Fast feedback loop
- Isolated testing
- Easy to debug

### Integration Tests

Test full ETL pipeline with real save files:

```bash
uv run pytest tests/test_integration_logdata.py -v
```

**Benefits:**
- Verify end-to-end functionality
- Catch database issues
- Validate data quality

### Performance Tests (Optional)

Monitor extraction performance:

```bash
uv run pytest tests/test_performance.py -v
```

**Benefits:**
- Catch performance regressions
- Ensure scalability
- Monitor import times

## Common Issues & Solutions

### Player ID Mapping

**Problem:** XML uses 0-based IDs, database uses 1-based

**Solution:**
```python
# XML: <Player ID="0">
# Database: player_id = 1
player_id = int(xml_id) + 1
```

**Important:** Player ID="0" exists and is valid - don't skip it!

### Duplicate Events

**Status:** NOT AN ISSUE ✅

MemoryData and LogData have completely separate event type namespaces:
- MemoryData: `MEMORYPLAYER_*`, `MEMORYFAMILY_*`, etc.
- LogData: `LAW_ADOPTED`, `TECH_DISCOVERED`, etc.

No deduplication needed - just concatenate!

### HTML in Text Fields

**Problem:** LogData `Text` elements contain HTML markup

**Solution:**
```python
import re
clean_text = re.sub(r'<[^>]+>', '', text)
clean_text = clean_text[:200]  # Limit length
```

**Example:**
```xml
<Text>You have adopted <link help="0,0,LAW_SLAVERY">Slavery</link>!</Text>
```
Becomes: "You have adopted Slavery!"

### Event Data JSON Structure

**Storage:** Events are stored with `event_data` as JSON

**Access in queries:**
```sql
-- Extract law name from JSON
json_extract(event_data, '$.law')

-- Extract tech name from JSON
json_extract(event_data, '$.tech')
```

## Code Quality Standards

### Type Hints

All functions must have type annotations:

```python
def extract_logdata_events(self) -> List[Dict[str, Any]]:
    """Extract LogData events."""
    # Implementation...
```

### Docstrings

All public methods need docstrings with Args/Returns:

```python
def get_law_progression_by_match(self, match_id: Optional[int] = None) -> pd.DataFrame:
    """Get law progression for players.

    Args:
        match_id: Optional match_id to filter (None for all matches)

    Returns:
        DataFrame with columns: match_id, player_id, player_name, civilization,
                                turn_to_4_laws, turn_to_7_laws, total_laws
    """
```

### Comments

Complex logic needs inline comments explaining "why":

```python
# Convert to 1-based player_id for database
# XML ID="0" is player 1, ID="1" is player 2
player_id = int(player_xml_id) + 1
```

## Development Workflow

### 1. Make Changes

Edit code following TDD principles:
1. Write failing test
2. Implement feature
3. Run tests until passing

### 2. Run Quality Checks

```bash
# Format code
uv run black tournament_visualizer/

# Lint code
uv run ruff check tournament_visualizer/

# Run tests
uv run pytest -v

# Check coverage
uv run pytest --cov=tournament_visualizer
```

### 3. Commit Changes

Follow conventional commit format:

```bash
git commit -m "feat: Add support for GOAL_STARTED events"
git commit -m "fix: Correct player ID mapping for LogData"
git commit -m "docs: Update developer guide with examples"
```

### 4. Test with Real Data

Re-import tournament data to verify:

```bash
# Backup database first
cp tournament_data.duckdb tournament_data.duckdb.backup

# Force re-import
uv run python import_tournaments.py --directory saves --force --verbose
```

## Debugging Tips

### 1. Inspect XML Structure

```bash
# Extract save file
unzip -p saves/match_*.zip | head -n 500

# Search for specific elements
unzip -p saves/match_*.zip | grep -A 5 "LAW_ADOPTED"
```

### 2. Check Database Contents

```bash
# Open DuckDB
uv run duckdb tournament_data.duckdb -readonly

# Inspect events
SELECT event_type, COUNT(*) as count
FROM events
GROUP BY event_type
ORDER BY count DESC;

# Check specific match
SELECT * FROM events
WHERE match_id = 10 AND event_type = 'LAW_ADOPTED';
```

### 3. Run Validation Scripts

```bash
# Data quality validation
uv run python scripts/validate_logdata.py

# Analytics verification
uv run python scripts/verify_analytics.py
```

### 4. Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance Optimization

### Database Indexes

Indexes are automatically created for common queries:

```sql
CREATE INDEX idx_events_type_player
ON events(event_type, player_id, turn_number);

CREATE INDEX idx_events_match_turn
ON events(match_id, turn_number);
```

### Query Optimization

Use CTEs for complex queries:

```sql
WITH law_events AS (
    SELECT * FROM events WHERE event_type = 'LAW_ADOPTED'
)
SELECT player_id, COUNT(*) FROM law_events GROUP BY player_id;
```

### Batch Operations

Use bulk inserts for performance:

```python
# Good: Bulk insert
db.bulk_insert_events(events)

# Bad: Individual inserts
for event in events:
    db.insert_event(event)
```

## Resources

### Project Files

- `README.md`: User documentation
- `CLAUDE.md`: Project-specific instructions
- `docs/plans/`: Implementation plans and investigation notes
- `tests/`: Test files and fixtures

### External Resources

- [Old World Game](https://www.mohawkgames.com/oldworld/)
- [DuckDB Documentation](https://duckdb.org/docs/)
- [Plotly Dash Documentation](https://dash.plotly.com/)

## Getting Help

If you get stuck:

1. Check this developer guide
2. Review test files for examples
3. Inspect the implementation plan: `docs/plans/logdata-ingestion-implementation-plan.md`
4. Check investigation notes: `docs/plans/logdata-investigation-findings.md`
5. Run validation scripts to identify issues
6. Check git history for similar changes

---

**Last Updated:** 2025-01-08

**Contributors:** Initial implementation following TDD and YAGNI principles
