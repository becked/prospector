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

## Turn-by-Turn History

The system tracks turn-by-turn gameplay progression through six specialized history tables:

### History Tables Overview

| Table | Purpose | Data Per Turn |
|-------|---------|---------------|
| `player_points_history` | Victory points | points |
| `player_yield_history` | Resource production | 14 yield types × amount |
| `player_military_history` | Military strength | military_power |
| `player_legitimacy_history` | Legitimacy score | legitimacy |
| `family_opinion_history` | Family relations | 40 families × opinion |
| `religion_opinion_history` | Religious standing | 15 religions × opinion |

**Key Characteristics:**
- All tables share `(match_id, player_id, turn_number)` structure
- Data is extracted from `Player/TurnList/TurnData` elements in XML
- Yields can be **negative** (no CHECK constraint on amount)
- Opinion values range from very negative to very positive

### Extracting History Data (Parser)

The parser extracts history data from `TurnData` elements:

```python
# In parser.py
def extract_points_history(self) -> List[Dict[str, Any]]:
    """Extract points history from TurnData elements."""
    points_history = []

    for player in self.root.findall('.//Player[@ID]'):
        player_id = int(player.get('ID')) + 1  # 1-based for database

        turn_list = player.find('TurnList')
        if turn_list is not None:
            for turn_data in turn_list.findall('TurnData'):
                turn_number = int(turn_data.get('Turn', 0))
                points = int(turn_data.get('Points', 0))

                points_history.append({
                    'player_id': player_id,
                    'turn_number': turn_number,
                    'points': points,
                })

    return points_history
```

**Important Details:**
- **Negative values**: Yields can be negative (e.g., debt, unhappiness)
- **All turns**: Extract data for every turn, even turn 0 or 1
- **No filtering**: Don't skip turns with zero or negative values
- **Player ID**: Always convert XML 0-based to database 1-based

### Loading History Data (ETL)

The ETL maps player IDs and bulk inserts history data:

```python
# In etl.py
def _load_tournament_data(self, parsed_data: Dict[str, Any]) -> None:
    # ... insert match and players first ...

    # Process points history
    points_history = parsed_data.get("points_history", [])
    for point_data in points_history:
        point_data["match_id"] = match_id
        # Map player_id from XML to database
        if (
            point_data.get("player_id")
            and point_data["player_id"] in player_id_mapping
        ):
            point_data["player_id"] = player_id_mapping[point_data["player_id"]]

    if points_history:
        self.db.bulk_insert_points_history(points_history)
        logger.info(f"Inserted {len(points_history)} points history records")
```

**Pattern for all history tables:**
1. Get history data from parsed_data
2. Add match_id to each record
3. Map player_id using player_id_mapping
4. Bulk insert using appropriate database method

### Querying History Data

Use window functions for turn-by-turn analysis:

```python
# In queries.py
def get_points_progression(self, match_id: int) -> pd.DataFrame:
    """Get victory points progression for a match."""
    query = """
    SELECT
        p.player_name,
        ph.turn_number,
        ph.points,
        -- Calculate change from previous turn
        ph.points - LAG(ph.points) OVER (
            PARTITION BY ph.player_id
            ORDER BY ph.turn_number
        ) as points_gained
    FROM player_points_history ph
    JOIN players p ON ph.player_id = p.player_id
    WHERE ph.match_id = ?
    ORDER BY ph.turn_number, p.player_name
    """

    with self.db.get_connection() as conn:
        return conn.execute(query, [match_id]).df()
```

**SQL Tips:**
- Use `LAG()` to compare with previous turns
- Use `LEAD()` to compare with future turns
- `PARTITION BY player_id` for per-player analysis
- Always filter by `match_id` for performance

### Database Schema

History tables use sequences for auto-increment IDs:

```sql
-- Sequences (shared across related tables)
CREATE SEQUENCE IF NOT EXISTS resources_id_seq START 1;
CREATE SEQUENCE IF NOT EXISTS points_history_id_seq START 1;

-- Example: player_yield_history
CREATE TABLE player_yield_history (
    resource_id BIGINT PRIMARY KEY,
    match_id BIGINT NOT NULL REFERENCES matches(match_id),
    player_id BIGINT NOT NULL REFERENCES players(player_id),
    turn_number INTEGER NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    amount INTEGER NOT NULL,  -- Can be negative!

    CHECK (turn_number >= 0),
    UNIQUE (match_id, player_id, turn_number, resource_type)
);

-- Indexes for fast queries
CREATE INDEX idx_yield_history_match_player
ON player_yield_history(match_id, player_id);

CREATE INDEX idx_yield_history_turn
ON player_yield_history(turn_number);
```

**Schema Design Notes:**
- No CHECK constraint on `amount` (yields can be negative)
- UNIQUE constraint prevents duplicate turn records
- Foreign keys enforce referential integrity
- Indexes optimize common query patterns

### Adding New History Tables

To add a new history table (e.g., `player_culture_history`):

#### 1. Update Database Schema

Add table creation in `database.py`:

```python
def _create_player_culture_history_table(self) -> None:
    """Create the player_culture_history table."""
    query = """
    CREATE TABLE IF NOT EXISTS player_culture_history (
        culture_history_id BIGINT PRIMARY KEY,
        match_id BIGINT NOT NULL REFERENCES matches(match_id),
        player_id BIGINT NOT NULL REFERENCES players(player_id),
        turn_number INTEGER NOT NULL,
        culture_type VARCHAR(50) NOT NULL,
        culture_level INTEGER NOT NULL,

        CHECK (turn_number >= 0),
        UNIQUE (match_id, player_id, turn_number, culture_type)
    );

    CREATE INDEX idx_culture_history_match_player
    ON player_culture_history(match_id, player_id);
    """
    with self.get_connection() as conn:
        conn.execute(query)
```

#### 2. Add Parser Method

Extract data in `parser.py`:

```python
def extract_culture_history(self) -> List[Dict[str, Any]]:
    """Extract culture history from TurnData elements."""
    culture_history = []

    for player in self.root.findall('.//Player[@ID]'):
        player_id = int(player.get('ID')) + 1
        turn_list = player.find('TurnList')

        if turn_list is not None:
            for turn_data in turn_list.findall('TurnData'):
                turn_number = int(turn_data.get('Turn', 0))

                # Extract culture-related attributes
                culture_type = turn_data.get('CultureType')
                culture_level = int(turn_data.get('CultureLevel', 0))

                if culture_type:
                    culture_history.append({
                        'player_id': player_id,
                        'turn_number': turn_number,
                        'culture_type': culture_type,
                        'culture_level': culture_level,
                    })

    return culture_history
```

#### 3. Add Bulk Insert Method

Add database method in `database.py`:

```python
def bulk_insert_culture_history(
    self, culture_data: List[Dict[str, Any]]
) -> None:
    """Bulk insert culture history records."""
    if not culture_data:
        return

    with self.get_connection() as conn:
        query = """
        INSERT INTO player_culture_history (
            culture_history_id, match_id, player_id,
            turn_number, culture_type, culture_level
        ) VALUES (?, ?, ?, ?, ?, ?)
        """

        values = []
        for culture in culture_data:
            culture_id = conn.execute(
                "SELECT nextval('culture_history_id_seq')"
            ).fetchone()[0]
            values.append([
                culture_id,
                culture["match_id"],
                culture["player_id"],
                culture["turn_number"],
                culture["culture_type"],
                culture["culture_level"],
            ])

        conn.executemany(query, values)
```

#### 4. Update ETL Pipeline

Add to ETL processing in `etl.py`:

```python
# In _load_tournament_data method
culture_history = parsed_data.get("culture_history", [])
for culture_data in culture_history:
    culture_data["match_id"] = match_id
    if culture_data.get("player_id") in player_id_mapping:
        culture_data["player_id"] = player_id_mapping[culture_data["player_id"]]

if culture_history:
    self.db.bulk_insert_culture_history(culture_history)
    logger.info(f"Inserted {len(culture_history)} culture history records")
```

#### 5. Write Tests

Test extraction in `tests/test_parser.py`:

```python
def test_extract_culture_history():
    parser = OldWorldSaveParser("test_data.zip")
    parser.extract_and_parse()

    culture_history = parser.extract_culture_history()

    assert len(culture_history) > 0
    assert all('player_id' in record for record in culture_history)
    assert all('turn_number' in record for record in culture_history)
```

### Validation

After adding history data, run validation:

```bash
# Validate history data integrity
uv run python scripts/validate_history_data.py
```

The validation script checks:
- Record counts
- Foreign key integrity
- Data quality (NULLs, negative values)
- Turn consistency across tables

### Analytics Examples

See comprehensive analytics examples in:
- `docs/turn-by-turn-history-analytics.md`

Quick examples:

```sql
-- Victory points progression
SELECT
    p.player_name,
    ph.turn_number,
    ph.points
FROM player_points_history ph
JOIN players p ON ph.player_id = p.player_id
WHERE ph.match_id = 1
ORDER BY ph.turn_number;

-- Economic power (average yields)
SELECT
    p.player_name,
    AVG(CASE WHEN yh.resource_type = 'YIELD_MONEY' THEN yh.amount END) as avg_money,
    AVG(CASE WHEN yh.resource_type = 'YIELD_SCIENCE' THEN yh.amount END) as avg_science
FROM player_yield_history yh
JOIN players p ON yh.player_id = p.player_id
WHERE yh.match_id = 1
GROUP BY p.player_name;

-- Military advantage over time
SELECT
    p.player_name,
    mh.turn_number,
    mh.military_power,
    mh.military_power - AVG(mh.military_power) OVER (
        PARTITION BY mh.turn_number
    ) as military_advantage
FROM player_military_history mh
JOIN players p ON mh.player_id = p.player_id
WHERE mh.match_id = 1;
```

### Migration Management

History tables were added via migration 002:

```bash
# Run migration
uv run python scripts/migrations/002_add_history_tables.py

# Rollback if needed
uv run python scripts/migrations/002_add_history_tables.py --rollback
```

**Migration Details:**
- Drops broken `game_state` table
- Renames `resources` → `player_yield_history`
- Creates 5 new history tables
- See: `docs/migrations/002_add_history_tables.md`

## Data Parsing

### Parsing MemoryData Events

When parsing MemoryData events, it's critical to preserve player ownership context:

**DO:**
```python
# Iterate through Player elements first
for player_element in root.findall('.//Player[@ID]'):
    owner_id = player_element.get('ID')
    memory_list = player_element.find('MemoryList')
    for mem in memory_list.findall('MemoryData'):
        # Process with owner_id context
```

**DON'T:**
```python
# Global search loses ownership context!
for mem in root.findall('.//MemoryData'):  # ❌ WRONG
    # Can't tell which player owns this memory
```

**Why:** MemoryData elements without a `<Player>` child (e.g., MEMORYTRIBE_*)
need to inherit their player_id from the parent `Player[@ID]` that owns the MemoryList.

**Validation:**
After any parser changes affecting MemoryData, run:
```bash
uv run python scripts/validate_memorydata_ownership.py
```

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
uv run python scripts/import_tournaments.py --directory saves --force --verbose
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
# LogData validation
uv run python scripts/validate_logdata.py

# MemoryData validation
uv run python scripts/validate_memorydata_ownership.py

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

**Last Updated:** 2025-10-09

**Contributors:** Initial implementation following TDD and YAGNI principles. Turn-by-turn history feature added in October 2025.
