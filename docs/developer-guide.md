# Developer Guide

> **Purpose:** This guide explains the architecture, design patterns, and technical implementation of the Old World Tournament Visualizer. For workflows, commands, and operational procedures, see `CLAUDE.md`.

## Architecture Overview

### Data Flow

The tournament visualizer follows a multi-stage ETL pipeline:

1. **Data Extraction**: XML save files (`.zip`) → Parser → Structured dictionaries
2. **Data Transformation**: Events → ETL pipeline → Normalized data structures
3. **Data Loading**: Transformed data → DuckDB tables (relational storage)
4. **Analytics Layer**: DuckDB → Query abstraction → Pandas DataFrames
5. **Presentation Layer**: DataFrames → Dash/Plotly components → Interactive web UI

**Key Design Decisions:**
- **DuckDB over SQLite**: OLAP optimization, better DataFrame integration, superior SQL analytics
- **Single-pass parsing**: Memory-efficient extraction from potentially large XML files
- **Event-based storage**: Flexible schema accommodates diverse event types via JSON
- **Query separation**: Business logic isolated in query layer, not scattered in UI code

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

### Adding New History Tables - Architectural Pattern

**Consistent structure across all history tables:**

```python
# Schema pattern
CREATE TABLE player_<category>_history (
    <category>_history_id BIGINT PRIMARY KEY,        # Auto-generated from sequence
    match_id BIGINT NOT NULL REFERENCES matches,      # Which match
    player_id BIGINT NOT NULL REFERENCES players,     # Which player
    turn_number INTEGER NOT NULL,                     # When (temporal dimension)
    <category>_specific_fields...,                    # What (data payload)

    CHECK (turn_number >= 0),                         # Basic validation
    UNIQUE (match_id, player_id, turn_number, ...)   # Prevent duplicates
);
```

**Data flow pattern:**
1. **Parser** extracts from `TurnData` elements → Returns `List[Dict[str, Any]]`
2. **ETL** maps player IDs and adds match_id → Enriches dictionaries
3. **Database** bulk inserts via sequence-generated IDs → Transactional commit
4. **Queries** join with players/matches → Returns DataFrames for analytics

**Key architectural decisions:**
- **No CHECK constraint on amounts**: Yields/values can be negative (debt, unhappiness)
- **UNIQUE constraint prevents duplicates**: At turn granularity per player
- **Sequences for IDs**: DuckDB sequences provide auto-increment behavior
- **Bulk inserts**: Performance optimization vs. row-by-row inserts

### Analytics Examples

See comprehensive analytics examples in:
- `docs/archive/reports/turn-by-turn-history-analytics.md`

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

### Schema Evolution Strategy

**Migration approach:**
- Versioned migration scripts in `scripts/migrations/`
- Each migration documented in `docs/migrations/`
- Always include rollback procedures
- Backup creation before destructive changes

**Example: Migration 002 (History Tables)**
- Removed `game_state` table (design flaw: all rows had turn_number=0)
- Renamed `resources` → `player_yield_history` (semantic clarity)
- Added 5 specialized history tables (separation of concerns)
- See: `docs/migrations/002_add_history_tables.md` for details

## Yields Visualization

The Match Details page includes comprehensive yield tracking showing all 14 yield types from Old World over time.

### Architecture

**Components:**
- **Generic chart function**: `create_yield_chart()` in `components/charts.py`
- **Backward-compatible wrapper**: `create_food_yields_chart()` delegates to generic function
- **Dynamic layout**: 2-column grid generated programmatically in `pages/matches.py`
- **Single callback**: `update_all_yield_charts()` handles all 14 yield types with one query

**Data Flow:**
1. User selects match → `match-selector` Input triggers callback
2. Single query fetches all yields: `get_yield_history_by_match(match_id)`
3. Callback filters DataFrame 14 times (once per yield type)
4. Creates 14 Plotly figures using `create_yield_chart()`
5. Returns list of figures → Dash updates all 14 chart divs

### The 14 Yield Types

```python
YIELD_TYPES = [
    ("YIELD_FOOD", "Food"),
    ("YIELD_GROWTH", "Growth"),
    ("YIELD_SCIENCE", "Science"),
    ("YIELD_CULTURE", "Culture"),
    ("YIELD_CIVICS", "Civics"),
    ("YIELD_TRAINING", "Training"),
    ("YIELD_MONEY", "Money"),
    ("YIELD_ORDERS", "Orders"),
    ("YIELD_HAPPINESS", "Happiness"),
    ("YIELD_DISCONTENT", "Discontent"),
    ("YIELD_IRON", "Iron"),
    ("YIELD_STONE", "Stone"),
    ("YIELD_WOOD", "Wood"),
    ("YIELD_MAINTENANCE", "Maintenance"),
]
```

### Creating Yield Charts

The generic `create_yield_chart()` function accepts any yield type:

```python
from tournament_visualizer.components.charts import create_yield_chart

# Basic usage
df = queries.get_yield_history_by_match(match_id=1)
df_food = df[df["resource_type"] == "YIELD_FOOD"]
fig = create_yield_chart(df_food, yield_type="YIELD_FOOD")

# With optional parameters
fig = create_yield_chart(
    df_food,
    total_turns=100,          # Extends lines to match end
    yield_type="YIELD_FOOD",  # For validation/error messages
    display_name="Food"       # Human-readable name (overrides derived name)
)

# Display name auto-derived from yield_type if not provided
fig = create_yield_chart(df_science, yield_type="YIELD_SCIENCE")
# Y-axis label will be "Science Yield" (derived from "YIELD_SCIENCE")
```

**Function Signature:**
```python
def create_yield_chart(
    df: pd.DataFrame,
    total_turns: Optional[int] = None,
    yield_type: str = "YIELD_FOOD",
    display_name: Optional[str] = None
) -> go.Figure:
    """Create a line chart showing yield production over time.

    Args:
        df: DataFrame with columns: player_name, turn_number, amount, resource_type
        total_turns: Optional total turns in match to extend lines to the end
        yield_type: The yield type being displayed (e.g., "YIELD_FOOD")
        display_name: Optional human-readable name (e.g., "Food")

    Returns:
        Plotly figure with line chart
    """
```

### DataFrame Schema

The query returns data in this format:

```python
# get_yield_history_by_match() returns:
{
    "player_id": [1, 1, 1, 2, 2, 2, ...],
    "player_name": ["Alice", "Alice", "Alice", "Bob", "Bob", "Bob", ...],
    "turn_number": [10, 20, 30, 10, 20, 30, ...],
    "resource_type": ["YIELD_FOOD", "YIELD_FOOD", "YIELD_FOOD", ...],
    "amount": [50, 75, 100, 40, 70, 95, ...]  # Can be negative!
}
```

**Important:** The `amount` column can be negative for yields like YIELD_MAINTENANCE and YIELD_DISCONTENT.

### Adding New Yield Types

If Old World adds new yield types in future updates:

1. **Update YIELD_TYPES constant** in `pages/matches.py`:
```python
YIELD_TYPES = [
    # ... existing yields ...
    ("YIELD_NEW_RESOURCE", "New Resource"),  # Add new yield
]
```

2. **That's it!** The dynamic generation handles everything else automatically:
   - Layout adjusts to new yield count
   - Callback generates outputs dynamically
   - Charts render without code changes

3. **Write test** in `tests/test_charts_yields.py`:
```python
def test_new_yield_type(multi_yield_data: pd.DataFrame) -> None:
    """Should work with new yield type."""
    df = multi_yield_data[multi_yield_data["resource_type"] == "YIELD_NEW_RESOURCE"]
    fig = create_yield_chart(df, yield_type="YIELD_NEW_RESOURCE")
    assert isinstance(fig, go.Figure)
```

### Performance Characteristics

**Query Performance:**
- Single query fetches ~2,000-3,000 rows per match
- Query time: < 100ms for typical matches
- Uses index on `(match_id, player_id)`

**Rendering Performance:**
- 14 charts with ~200 points each = ~2,800 total points
- Render time: < 1 second in browser
- Dash efficiently updates all charts in parallel

**Memory Usage:**
- DataFrame size: ~200 KB per match
- 14 figures in memory: ~2 MB total
- No performance issues with typical match counts

### Design Principles Applied

**DRY (Don't Repeat Yourself):**
- ✅ One `create_yield_chart()` instead of 14 separate functions
- ✅ Dynamic layout generation (no copy-paste HTML)
- ✅ Single callback handles all yield types

**YAGNI (You Aren't Gonna Need It):**
- ✅ No premature optimization (filtering is fast enough)
- ✅ No caching layer (query is already fast)
- ✅ No yield-specific customization (all use same chart style)

**Testing:**
- ✅ 20 unit tests covering generic function, backward compatibility, edge cases
- ✅ Tests validate empty data, single/many players, sparse data
- ✅ Tests confirm negative yields work correctly

### Design Considerations

**Chart rendering performance:**
- 14 charts × ~200 points each = ~2,800 total render points
- Plotly handles this efficiently with WebGL acceleration
- No virtualization needed until 10,000+ points
- Browser rendering is the bottleneck, not data fetching

**Query optimization:**
- Single query fetches all yields (14 types × all turns)
- Client-side filtering by yield type (fast enough)
- Alternative considered: 14 separate queries (rejected - too many round trips)
- Trade-off: Slightly more data transfer for simpler code and fewer queries

**Code maintainability:**
- Generic chart function reduces duplication (DRY principle)
- Adding 15th yield type requires only constant update
- No yield-specific logic scattered through codebase
- Easy to test (one function, many test cases)

## Plotly Modebar Configuration

All Plotly charts in the application use a standardized modebar configuration defined in `tournament_visualizer/config.py`:

```python
MODEBAR_CONFIG = {
    "displayModeBar": "hover",  # Show only on hover
    "displaylogo": False,       # Hide Plotly logo
    "modeBarButtonsToRemove": [...],  # Remove all except zoom in/out
}
```

**Usage:**

1. **For charts using `create_chart_card()`** (preferred):
   ```python
   from tournament_visualizer.components.layouts import create_chart_card

   create_chart_card(
       title="My Chart",
       chart_id="my-chart",
       height="400px",
   )
   # Config is automatically applied
   ```

2. **For direct `dcc.Graph` usage** (when `create_chart_card` isn't suitable):
   ```python
   from dash import dcc
   from tournament_visualizer.config import MODEBAR_CONFIG

   dcc.Graph(
       figure=fig,
       config=MODEBAR_CONFIG,
   )
   ```

**Available Buttons:**
- `zoomIn2d` - Zoom in (✅ shown)
- `zoomOut2d` - Zoom out (✅ shown)
- All others removed

**Why hover-only?**
- Cleaner UI - toolbar doesn't clutter the chart
- Still accessible when needed
- Consistent with modern web app design patterns

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

## Event System Architecture

### Event Storage Pattern

**Schema design:**

```sql
CREATE TABLE events (
    event_id BIGINT PRIMARY KEY,
    match_id BIGINT REFERENCES matches,
    player_id BIGINT REFERENCES players,
    turn_number INTEGER,
    event_type VARCHAR(100),      -- Enum-like: "LAW_ADOPTED", "TECH_DISCOVERED"
    event_data JSON,               -- Flexible payload for event-specific data
    description TEXT,              -- Human-readable summary
    timestamp TIMESTAMP
);
```

**Design rationale:**
- **JSON event_data field**: Accommodates diverse event types without schema changes
- **No event-specific tables**: YAGNI - JSON provides enough flexibility
- **Indexed on (event_type, player_id, turn_number)**: Optimizes common query patterns
- **Description field**: Pre-computed readable text avoids parsing JSON in UI

### Event Type Namespaces

**Two separate event sources with distinct namespaces:**

1. **MemoryData events**: `MEMORYPLAYER_*`, `MEMORYFAMILY_*`, `MEMORYTRIBE_*`
   - AI decision-making context
   - Limited historical scope
   - Parsed from `Player/MemoryList` elements

2. **LogData events**: `LAW_ADOPTED`, `TECH_DISCOVERED`, `GOAL_*`, etc.
   - Complete turn-by-turn gameplay history
   - Comprehensive event coverage
   - Parsed from `Player/PermanentLogList` elements

**No overlap**: Event types are mutually exclusive → Simple concatenation, no deduplication needed

### Adding New Event Types

**Parser extensibility pattern:**

```python
# In parser.py - _build_logdata_event_data()
def _build_logdata_event_data(self, event_type, data1, data2, data3):
    """Build event-specific data dictionary from XML attributes."""
    if event_type == 'LAW_ADOPTED' and data1:
        return {'law': data1}  # Extract relevant data
    # ... more event types ...
    return {}  # Unknown events get empty dict
```

**Benefits:**
- New event types require only parser changes
- Database schema unchanged (JSON handles structure)
- Queries filter by event_type string
- UI gets pre-formatted description

## Testing Architecture

### Test Pyramid Strategy

**Three testing layers with different purposes:**

```
        /\
       /UI\          Integration tests (slow, comprehensive)
      /----\
     /Unit  \        Unit tests (fast, isolated)
    /--------\
   /Validation\      Validation scripts (production data)
  /____________\
```

1. **Unit tests** (base layer - most tests):
   - Test individual functions in isolation
   - Mock external dependencies (database, file system)
   - Fast execution (< 1 second suite)
   - Example: Parser extracts correct player IDs from XML

2. **Integration tests** (middle layer):
   - Test component interactions
   - Real database, real file I/O
   - Moderate execution time (< 30 seconds)
   - Example: Full ETL pipeline from save file to database

3. **Validation scripts** (top layer - production):
   - Test real-world data quality
   - Run after imports, not in CI
   - Catch anomalies tests miss
   - Example: Check for unlinked players, data integrity

**Trade-offs:**
- Unit tests catch logic errors quickly but miss integration issues
- Integration tests catch schema mismatches but are slower
- Validation scripts catch real-world edge cases but can't run in CI

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

## Development Practices

### Test-Driven Development

**Three-layer testing strategy:**

1. **Unit tests** (`tests/test_*.py`):
   - Fast feedback (< 1 second)
   - Isolated component testing
   - Mock external dependencies

2. **Integration tests** (`tests/test_integration_*.py`):
   - End-to-end pipeline validation
   - Real database interactions
   - Catch inter-component issues

3. **Validation scripts** (`scripts/validate_*.py`):
   - Post-import data quality checks
   - Production data verification
   - Business rule enforcement

**Why three layers?** Unit tests catch logic errors quickly. Integration tests catch schema mismatches. Validation scripts catch real-world data anomalies that tests might miss.

### Code Quality Standards

**Type annotations required:**
- All public functions must have complete type hints
- Enables static analysis (mypy)
- Self-documenting code
- IDE autocomplete support

**Docstring conventions:**
- Google style docstrings
- Document Args, Returns, Raises
- Include usage examples for complex functions
- Explain "why" in comments, "what" in docstrings

**Formatting:**
- Black for consistent code style (no debates)
- Ruff for linting and import organization
- Pre-commit hooks enforce standards

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

## Architecture Principles

### YAGNI (You Aren't Gonna Need It)

**Applied throughout:**
- No premature abstraction layers
- Features implemented when needed, not "just in case"
- Example: Single query for all yields instead of separate query per yield type
- Example: No caching layer until performance actually becomes an issue

### DRY (Don't Repeat Yourself)

**Pattern reuse:**
- Generic `create_yield_chart()` function handles all 14 yield types
- Shared name normalization logic across all player/participant matching
- Centralized modebar configuration in `config.py`
- Query abstraction layer prevents SQL duplication

### Separation of Concerns

**Clear boundaries:**
- Parser: XML → Dictionaries (no database knowledge)
- ETL: Dictionaries → Database (no XML knowledge)
- Queries: Database → DataFrames (no UI knowledge)
- UI: DataFrames → Components (no SQL knowledge)

**Benefits:**
- Components testable in isolation
- Easy to swap implementations
- Clear responsibility boundaries
- Reduced cognitive load

## References

### Documentation Structure

- **This file (`developer-guide.md`)**: Architecture, design patterns, technical concepts
- **`CLAUDE.md`**: Workflows, commands, operational procedures
- **`docs/migrations/`**: Schema changes with rationale
- **`docs/archive/`**: Historical implementation plans and reports

### External Resources

- [DuckDB Documentation](https://duckdb.org/docs/) - OLAP database
- [Plotly Dash Documentation](https://dash.plotly.com/) - Web framework
- [Old World Wiki](https://oldworld.fandom.com/) - Game mechanics reference

---

**Last Updated:** 2025-10-16

**Contributors:** Initial implementation following TDD and YAGNI principles. Turn-by-turn history feature added in October 2025. Comprehensive yields visualization added in October 2025.

## Ruler Tracking

The `rulers` table tracks ruler succession data for each player in a match, including archetype and starting trait information.

### Database Schema

```sql
CREATE TABLE rulers (
    ruler_id INTEGER PRIMARY KEY,
    match_id BIGINT NOT NULL REFERENCES matches(match_id),
    player_id BIGINT NOT NULL REFERENCES players(player_id),
    character_id INTEGER NOT NULL,
    ruler_name VARCHAR,
    archetype VARCHAR,             -- Scholar, Tactician, Commander, Schemer, Builder, Judge, Zealot
    starting_trait VARCHAR,        -- Initial trait chosen at game start
    succession_order INTEGER NOT NULL,  -- 0 for starting ruler, 1+ for successors
    succession_turn INTEGER NOT NULL,   -- Turn when ruler took power (1 for starting)
);
```

### Common Queries

```sql
-- Get all rulers for a match
SELECT p.player_name, r.ruler_name, r.archetype, r.starting_trait, r.succession_order
FROM rulers r
JOIN players p ON r.player_id = p.player_id AND r.match_id = p.match_id
WHERE r.match_id = ?
ORDER BY p.player_name, r.succession_order;

-- Count ruler successions per player
SELECT p.player_name, COUNT(*) as ruler_count
FROM rulers r
JOIN players p ON r.player_id = p.player_id
WHERE r.match_id = ?
GROUP BY p.player_name;

-- Archetype win rates
SELECT r.archetype, COUNT(*) as games,
       SUM(CASE WHEN mw.winner_player_id = r.player_id THEN 1 ELSE 0 END) as wins
FROM rulers r
JOIN match_winners mw ON r.match_id = mw.match_id
WHERE r.succession_order = 0
GROUP BY r.archetype;
```

### Validation

Run validation to check ruler data integrity:

```bash
uv run python scripts/validate_rulers.py
```

Validates:
- Foreign key relationships
- Sequential succession order
- Correct succession turns
- Valid archetype values
- No duplicate rulers

## Tournament Participant Tracking

The participant tracking system links players across multiple matches using Challonge tournament data. This enables cross-match analytics, persistent player identity, and bracket integration.

### Architecture

**Two-tier identity system:**
1. **Match-scoped players** (`players` table): Independent player_ids per save file
2. **Tournament participants** (`tournament_participants` table): Persistent identity

**Data flow:**
1. Import Challonge participants via API
2. Import save files (creates match-scoped players)
3. Link players to participants via name matching
4. Enable cross-match queries using participant_id

### Schema

**tournament_participants table:**
```sql
CREATE TABLE tournament_participants (
    participant_id BIGINT PRIMARY KEY,           -- Challonge participant ID
    display_name VARCHAR NOT NULL,               -- Display name
    display_name_normalized VARCHAR NOT NULL,    -- Normalized for matching
    challonge_username VARCHAR,
    challonge_user_id BIGINT,                    -- Persistent across tournaments
    seed INTEGER,
    final_rank INTEGER
);
```

**Foreign keys:**
- `players.participant_id` → `tournament_participants.participant_id`
- `matches.player1_participant_id` → `tournament_participants.participant_id`
- `matches.player2_participant_id` → `tournament_participants.participant_id`
- `matches.winner_participant_id` → `tournament_participants.participant_id`

### Common Queries

**Player performance across matches:**
```sql
SELECT
    tp.display_name,
    COUNT(DISTINCT p.match_id) as matches_played,
    SUM(CASE WHEN mw.winner_player_id = p.player_id THEN 1 ELSE 0 END) as wins
FROM tournament_participants tp
JOIN players p ON tp.participant_id = p.participant_id
JOIN match_winners mw ON p.match_id = mw.match_id
GROUP BY tp.participant_id, tp.display_name
ORDER BY wins DESC;
```

**Participant civilizations:**
```sql
SELECT
    tp.display_name,
    p.civilization,
    COUNT(*) as times_played
FROM tournament_participants tp
JOIN players p ON tp.participant_id = p.participant_id
WHERE p.civilization IS NOT NULL
GROUP BY tp.participant_id, tp.display_name, p.civilization
ORDER BY tp.display_name, times_played DESC;
```

### Linking Architecture

**Two-phase linking process:**

1. **Automated matching** (90%+ success rate):
   - Normalize both save file names and Challonge names
   - Match on exact normalized string equality
   - Handles most common variations (whitespace, case, accents)

2. **Manual override system** (edge cases):
   - JSON configuration file: `data/participant_name_overrides.json`
   - Uses stable `challonge_match_id` (survives re-imports)
   - Per-match overrides allow handling name changes mid-tournament

**Design trade-off**: Chose exact matching over fuzzy matching to avoid false positives. Manual overrides handle edge cases without complexity of Levenshtein distance or ML-based matching.

### Name Matching

**Normalization process:**
1. Strip whitespace
2. Convert to lowercase
3. Remove Unicode accents
4. Remove special characters
5. Remove all remaining whitespace

**Examples:**
- "FluffybunnyMohawk" → "fluffybunnymohawk"
- "Ninja [OW]" → "ninjaow"
- "José García" → "josegarcia"

### Manual Overrides

**When automated matching fails, add manual override:**

```sql
INSERT INTO participant_name_overrides (
    match_id,
    save_file_player_name,
    participant_id,
    reason
) VALUES (
    123,
    'SaveFileName',
    456,
    'Player changed name mid-tournament'
);
```

Then re-run linking:
```bash
uv run python scripts/link_players_to_participants.py
```

### Data Integrity Constraints

**Foreign key enforcement:**
- `players.participant_id` → `tournament_participants.participant_id`
- `matches.player1_participant_id` → `tournament_participants.participant_id`
- `matches.winner_participant_id` → `tournament_participants.participant_id`

**Validation strategy:**
- Pre-commit validation scripts prevent corrupt data
- Post-import validation ensures referential integrity
- Unlinked players allowed (graceful degradation)

### DuckDB Workaround

Due to a DuckDB limitation with updating tables that have foreign key references TO them, the participant linking process must drop and recreate the `idx_players_participant` index during bulk updates. This is handled automatically by the `ParticipantMatcher.link_all_matches()` method.

## Participant UI Integration

### Overview

The web application displays **tournament participants** (real people) rather than match-scoped player instances. This provides accurate cross-match analytics and persistent player identity.

### Display Strategy: Show All with Fallback

The UI uses a "participant-first, fallback to name" strategy:

- **Linked players**: Grouped by `participant_id`, show participant display name
- **Unlinked players**: Grouped by `player_name_normalized`, show player name with ⚠️ indicator
- **Visual feedback**: Unlinked players marked for data quality awareness

This ensures:
✅ All match data visible to users
✅ Graceful degradation when linking incomplete
✅ Works during active tournaments (new players not yet in Challonge)
✅ Incentivizes data quality through visual indicators

### Key Queries

#### Player Performance (`get_player_performance()`)

Returns one row per person, grouping by participant when available:

```sql
-- Smart grouping key: participant_id if linked, else normalized name
COALESCE(
    CAST(tp.participant_id AS VARCHAR),
    'unlinked_' || p.player_name_normalized
) as grouping_key
```

**Columns returned:**
- `player_name`: Display name (participant or player)
- `participant_id`: Participant ID (NULL for unlinked)
- `is_unlinked`: Boolean flag for UI indicators
- `total_matches`, `wins`, `win_rate`: Standard stats
- `civilizations_played`: All civs used (comma-separated)
- `favorite_civilization`: Most-played civ

**Use cases:**
- Players page rankings table
- Player performance metrics
- Head-to-head comparisons

#### Head-to-Head Stats (`get_head_to_head_stats()`)

Matches players by `participant_id` first, falls back to name matching:

```python
stats = queries.get_head_to_head_stats('Ninja', 'Fiddler')
# Uses participant_id if both are linked
# Falls back to name matching for unlinked
```

**Returns:**
```python
{
    'total_matches': 5,
    'player1_wins': 3,
    'player2_wins': 2,
    'avg_match_length': 87.4,
    'first_match': '2025-01-01',
    'last_match': '2025-02-15'
}
```

#### Civilization Performance (`get_civilization_performance()`)

Counts unique **participants**, not unique names:

```sql
-- Counts distinct people who played this civ
COUNT(DISTINCT COALESCE(
    CAST(p.participant_id AS VARCHAR),
    'unlinked_' || p.player_name_normalized
)) as unique_participants
```

**Columns returned:**
- `unique_participants`: Total unique people
- `unique_linked_participants`: Count of linked only
- `unique_unlinked_players`: Count of unlinked only

Data quality columns help track linking coverage.

### UI Components

#### Players Page (`pages/players.py`)

**Rankings Table:**
- One row per person (not per match instance)
- Player column uses markdown with ⚠️ for unlinked
- Civilizations column shows all civs played (favorite bolded)

**Summary Metrics:**
- Total Players
- Linked Participants
- Unlinked Players
- Linking Coverage %

**Head-to-Head:**
- Dropdowns populated with participant names
- Matching by participant_id ensures accuracy

### Data Quality Indicators

#### Visual Indicators

| Indicator | Meaning | Action |
|-----------|---------|--------|
| ⚠️ | Player not linked to participant | Consider adding manual override |
| **Bold civ** | Most-played civilization | User info |
| Linking Coverage % | Percentage of players linked | Data quality metric |

#### Validation

Run validation script to check data quality:

```bash
uv run python scripts/validate_participant_ui_data.py
```

Checks:
- Query correctness
- Data consistency
- Linking coverage
- Potential linking opportunities

### Common Queries

**Find unlinked players:**
```sql
SELECT
    player_name,
    COUNT(DISTINCT match_id) as matches_played
FROM players
WHERE participant_id IS NULL
GROUP BY player_name_normalized, player_name
ORDER BY matches_played DESC;
```

**Check participant linking coverage:**
```sql
SELECT
    COUNT(*) as total_instances,
    COUNT(participant_id) as linked,
    COUNT(*) - COUNT(participant_id) as unlinked,
    ROUND(COUNT(participant_id) * 100.0 / COUNT(*), 1) as coverage_pct
FROM players;
```

**Find participants with multiple civs:**
```sql
SELECT
    tp.display_name,
    STRING_AGG(DISTINCT p.civilization, ', ') as civs,
    COUNT(DISTINCT p.civilization) as civ_count
FROM tournament_participants tp
JOIN players p ON tp.participant_id = p.participant_id
GROUP BY tp.participant_id, tp.display_name
HAVING COUNT(DISTINCT p.civilization) > 1
ORDER BY civ_count DESC;
```

### Query Design Patterns

**Smart grouping key pattern:**

```sql
-- Group by participant when available, fallback to normalized name
COALESCE(
    CAST(tp.participant_id AS VARCHAR),
    'unlinked_' || p.player_name_normalized
) as grouping_key
```

**Why this works:**
- Linked players: Group by participant_id → Correct cross-match aggregation
- Unlinked players: Group by normalized name → Best-effort fallback
- String prefix prevents ID collision with actual participant IDs
- Graceful degradation when linking incomplete

**Alternative approaches considered:**

1. **Filter out unlinked players**: Rejected - loses data visibility
2. **Show all player instances**: Rejected - confusing for users
3. **Fuzzy name matching**: Rejected - risk of false positives
4. **This approach**: Accepted - balances data quality with usability

### Performance Considerations

#### Query Optimization

Participant queries use CTEs and appropriate indexes:

```sql
-- Indexes used:
-- - players.participant_id (for JOIN)
-- - players.player_name_normalized (for fallback grouping)
-- - tournament_participants.participant_id (PRIMARY KEY)
```

For large datasets (>1000 matches):
- Queries typically execute in <100ms
- No additional optimization needed
- DuckDB handles aggregations efficiently

#### Caching

Dash app does NOT cache query results by default. Each page visit executes queries fresh.

For production with high traffic, consider:
- Add `dcc.Interval` component for periodic refresh
- Cache results in Redis/Memcached
- Pre-compute aggregations in background job

### Future Enhancements

**Multi-tournament support** (YAGNI - not implemented):
- Currently tracks single tournament via `participant_id`
- Could extend using `challonge_user_id` for cross-tournament
- Would require additional grouping level

**Fuzzy name matching** (YAGNI - not implemented):
- Current matching is exact normalized string match
- Could add Levenshtein distance for "Ninja" vs "Ninjaa"
- Manual overrides cover edge cases for now

**Participant detail page**:
- Dedicated `/participants/<id>` page
- Match history, opponent analysis, trends
- See Task 3 in implementation plan

