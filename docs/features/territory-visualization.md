# Territory Visualization

## Overview

The territory visualization feature allows users to view turn-by-turn map control for Old World tournament matches. Users can scrub through game history with a slider to see how territorial control evolved, displayed on an interactive hexagonal map.

## User Guide

### Accessing the Feature

1. Navigate to the **Matches** page (`/matches`)
2. Select a match from the dropdown
3. Click the **Map** tab
4. Use the turn slider to view different points in the game

### Understanding the Map

**Territory Control Hexagonal Map** displays the game state at any turn:

- **Hexagonal tiles**: Each hexagon represents one tile on the game map
- **Player colors**: Owned tiles are colored by player's civilization (see legend)
- **Terrain colors**: Unowned tiles show terrain type with reduced opacity:
  - Blue: Water
  - Green: Grassland
  - Yellow: Desert
  - Tan: Arid
  - Light green: Scrub
  - Grey-blue: Tundra
  - White-grey: Snow
- **Hover info**: Hover over tiles to see owner, terrain, and coordinates

### Additional Charts

The Map tab also includes:

- **Territory Control Over Time**: Line chart showing tile count per player across all turns
- **Final Territory Distribution**: Pie chart showing final territorial breakdown
- **Cumulative City Count**: Track city founding over time

### Controls

- **Match selector**: Choose which game to visualize (in main dropdown at top of page)
- **Turn slider**:
  - Drag the slider to scrub through game history
  - Map updates automatically as you drag
  - Slider range adjusts to match the selected game's turn count
  - Tooltip shows current turn number

## Technical Details

### Data Model

Territory data is stored as full turn-by-turn snapshots:

```sql
CREATE TABLE territories (
    territory_id BIGINT PRIMARY KEY,
    match_id BIGINT NOT NULL,           -- Which match
    x_coordinate INTEGER NOT NULL,      -- Tile position X
    y_coordinate INTEGER NOT NULL,      -- Tile position Y
    turn_number INTEGER NOT NULL,       -- Game turn (1 to final_turn)
    terrain_type VARCHAR,               -- TERRAIN_GRASSLAND, etc.
    owner_player_id BIGINT,             -- Player match order (1, 2, etc.) or NULL (unowned)
    UNIQUE(match_id, x_coordinate, y_coordinate, turn_number)
);
```

**Storage characteristics**:
- Map sizes vary by match (typically 1,972 to 3,364 tiles)
- ~70-165 turns per match (varies widely)
- ~150,000-300,000 rows per match
- ~4.1 million rows for current dataset (25 matches)
- ~508 MB database size (includes all tournament data)

**Key design decision**: Store every tile for every turn (full snapshots), not just ownership changes. This simplifies queries and visualization at the cost of storage space.

### Player ID Mapping

**Critical**: The `owner_player_id` field stores the player's **match order** (1, 2, etc.), not their global player ID.

This enables consistent color assignment:
- First player in match → `owner_player_id = 1` → First color in palette
- Second player in match → `owner_player_id = 2` → Second color in palette

The query layer joins with a `player_order` CTE to map back to player names and civilizations.

### Data Pipeline

1. **XML Parsing** (`parser.py:extract_territories()`):
   - Extract `<Tile>` elements from save file XML
   - Parse `<OwnerHistory>` for turn-by-turn ownership changes
   - Convert tile IDs to x/y coordinates: `x = id % map_width`, `y = id // map_width`
   - Map XML player IDs to match order (XML uses 0-based indexing)
   - Persist ownership across turns (if tile owned at turn 45, still owned at 46 unless changed)

2. **ETL Pipeline** (`etl.py:extract_from_attachment()`):
   - Call `parser.extract_territories()` during import
   - Pass `match_id` and `final_turn` (max turn from game states)
   - Build all records in memory before bulk insert

3. **Database Insert** (`database.py:bulk_insert_territories()`):
   - Bulk insert using parameterized queries
   - Foreign keys ensure referential integrity
   - Indexes optimize query performance

### Visualization

**Hexagonal Grid Rendering** (`charts.py:create_hexagonal_map()`):

The hexagonal map uses Plotly scatter plot with hexagon markers:

```python
# Calculate hex positions
HEX_WIDTH = 1.0
HEX_HEIGHT = 0.866  # sqrt(3)/2 for regular hexagon

# Offset rows (even rows shifted right by 0.5 hex width)
hex_x = x_coordinate * HEX_WIDTH + (y_coordinate % 2) * (HEX_WIDTH / 2)
hex_y = y_coordinate * HEX_HEIGHT
```

**Offset coordinates**: Even rows are shifted right by half a hex width to create proper hexagonal tessellation.

**Color scheme**:
- Owned tiles: Civilization-specific colors via `get_nation_color()` function
- Unowned tiles: Terrain-specific colors with 50% opacity

**Layout**:
- Fixed aspect ratio (scaleanchor) to prevent distortion
- No axis labels (just x/y coordinates)
- Legend on right side showing players and terrain types
- 700px height for optimal visibility

### Query Layer

**`queries.py:get_territory_map(match_id, turn_number)`**:

Returns all tiles for a specific match and turn with ownership information:

```python
WITH player_order AS (
    SELECT
        match_id,
        player_id,
        player_name,
        civilization,
        ROW_NUMBER() OVER (PARTITION BY match_id ORDER BY player_id) as match_player_order
    FROM players
)
SELECT
    t.x_coordinate,
    t.y_coordinate,
    t.terrain_type,
    t.owner_player_id,
    p.player_name,
    p.civilization
FROM territories t
LEFT JOIN player_order p ON t.match_id = p.match_id
                         AND t.owner_player_id = p.match_player_order
WHERE t.match_id = ? AND t.turn_number = ?
```

**Key points**:
- Uses LEFT JOIN to include unowned tiles (owner_player_id IS NULL)
- Returns ~1,972-3,364 rows per query (one per tile)
- Executes in < 100ms with proper indexes

**`queries.py:get_territory_turn_range(match_id)`**:

Returns (min_turn, max_turn) for slider configuration.

**`queries.py:get_territory_control_summary(match_id)`**:

Returns territory counts per player per turn for timeline chart.

### Performance Considerations

**Query optimization**:
- Covering index on `(match_id, turn_number)` enables fast filtering
- Spatial index on `(match_id, x_coordinate, y_coordinate)` for future queries
- LEFT JOIN with players table (not INNER) to include unowned tiles

**UI responsiveness**:
- Slider updates trigger callback immediately (no debounce)
- Query completes in < 100ms (~2,000-3,400 rows returned)
- Plotly renders hexagons in < 200ms
- Total slider response: ~300ms (feels instant)

**Memory usage**:
- Parser generates all records in memory per match (150k-300k records)
- ~64 bytes per record = ~10-20 MB per match during import
- Acceptable for modern systems

**Database size**:
- ~4.1M rows currently (25 matches)
- ~200 MB for territories table alone
- Database will grow linearly with match count (~8 MB per match)

## Testing

### Unit Tests

**Parser tests** (`tests/test_parser_territories.py`):
- Coordinate conversion (tile ID → x,y)
- Player ID mapping (XML 0-based → match order 1-based)
- Ownership persistence across turns
- Terrain extraction
- Edge cases (empty XML, missing attributes)

**Query tests** (`tests/test_queries.py`):
- `get_territory_map()` returns correct data structure
- `get_territory_turn_range()` handles missing data
- Foreign key joins work correctly

### Integration Tests

**Data import** (`scripts/import_attachments.py`):
- Re-import with `--force` flag
- Verify territory count in logs
- Check for errors during parsing

**Validation** (`scripts/validate_territories.py`):
- Turn sequence completeness (no gaps)
- Coordinate validity (within bounds)
- Tile count consistency (same tiles per turn)
- Player reference integrity (no orphaned IDs)
- Ownership sanity checks (reasonable % owned)
- Terrain coverage (all tiles have terrain)

### Manual Testing

1. Start server: `uv run python manage.py restart`
2. Navigate to `/matches`
3. Select a match from dropdown
4. Click "Map" tab
5. Verify hexagonal map displays at final turn
6. Drag slider to test responsiveness
7. Check hover tooltips
8. Verify legend accuracy
9. Test with different matches (different map sizes)

## Implementation Files

### Core Implementation
- `tournament_visualizer/data/parser.py:extract_territories()` - Territory extraction from XML
- `tournament_visualizer/data/database.py:bulk_insert_territories()` - Database insertion
- `tournament_visualizer/data/etl.py:extract_from_attachment()` - Pipeline integration
- `tournament_visualizer/data/queries.py` - Query methods:
  - `get_territory_map()`
  - `get_territory_turn_range()`
  - `get_territory_control_summary()`

### Visualization
- `tournament_visualizer/components/charts.py:create_hexagonal_map()` - Hex map visualization
- `tournament_visualizer/components/charts.py:create_territory_control_chart()` - Timeline chart
- `tournament_visualizer/pages/matches.py` - UI layout and callbacks (Map tab)

### Testing & Validation
- `tests/test_parser_territories.py` - Parser unit tests
- `tests/test_queries.py` - Query unit tests
- `scripts/validate_territories.py` - Data validation script

### Schema
- `tournament_visualizer/data/database.py` - Table creation with indexes

## Future Enhancements

### Potential Features

1. **Animation mode**: Auto-advance slider to show game progression
2. **City territory visualization**: Show which city each tile belongs to (requires cities table)
3. **Fog of war**: View map from a specific player's perspective
4. **Territory change highlights**: Highlight tiles that changed hands this turn
5. **Expansion velocity**: Color tiles by how recently they were captured
6. **Contested tiles**: Identify tiles that changed hands multiple times
7. **Resource overlay**: Show strategic resources on tiles (requires parsing resource data)
8. **Export to image**: Download map as PNG for analysis
9. **Side-by-side comparison**: Compare two turns simultaneously
10. **Minimap overview**: Small always-visible map showing full territory

### Schema Extensions

```sql
-- Add city territory (requires cities table first)
ALTER TABLE territories ADD COLUMN city_territory_id BIGINT;

-- Add visibility tracking (fog of war)
CREATE TABLE tile_visibility (
    match_id BIGINT NOT NULL,
    x_coordinate INTEGER NOT NULL,
    y_coordinate INTEGER NOT NULL,
    turn_number INTEGER NOT NULL,
    player_id BIGINT NOT NULL,
    is_visible BOOLEAN NOT NULL,
    PRIMARY KEY (match_id, x_coordinate, y_coordinate, turn_number, player_id)
);

-- Add resource information
ALTER TABLE territories ADD COLUMN resource_type VARCHAR;
```

### Performance Optimizations

If database grows beyond 10M rows:

1. **Partition by tournament**: Create separate tables per tournament
2. **Materialize common views**: Pre-aggregate territory counts by turn
3. **Incremental updates**: Only re-import changed matches
4. **Client-side caching**: Cache map data in browser for smoother slider scrubbing
5. **Compressed storage**: Use DuckDB compression for older tournaments

## Troubleshooting

### No territory data showing

**Check database**:
```bash
uv run duckdb data/tournament_data.duckdb -readonly -c "SELECT COUNT(*) FROM territories"
```

If count is 0:
- Re-import data: `uv run python scripts/import_attachments.py --directory saves --force --verbose`
- Check logs for parser errors
- Verify XML files contain `<Tile>` elements with `<OwnerHistory>`

### Slider not working

**Check browser console** for JavaScript errors.

**Verify callback outputs** match component IDs:
- `match-territory-heatmap` (figure output)
- `match-territory-turn-slider` (slider component)

**Check that match has territory data**:
```bash
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT match_id, COUNT(*) as tiles
FROM territories
WHERE match_id = YOUR_MATCH_ID
GROUP BY match_id
"
```

### Slow performance

**Test query speed**:
```bash
uv run duckdb data/tournament_data.duckdb -readonly -c "
EXPLAIN ANALYZE
SELECT * FROM territories
WHERE match_id = 1 AND turn_number = 50
"
```

If > 500ms:
- Verify indexes exist: `SELECT * FROM duckdb_indexes() WHERE table_name = 'territories'`
- Check database file integrity
- Consider VACUUM to reclaim space

### Map looks distorted

**Check aspect ratio**: Hexagons should look regular (not stretched).

If distorted:
- Verify `scaleanchor="y"` and `scaleratio=1` in chart layout
- Check browser zoom level (100% recommended)
- Try resizing browser window

### Wrong colors or missing players

**Verify player order mapping**:
```bash
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT
    p.player_id,
    p.player_name,
    p.civilization,
    ROW_NUMBER() OVER (PARTITION BY p.match_id ORDER BY p.player_id) as match_player_order
FROM players p
WHERE match_id = YOUR_MATCH_ID
ORDER BY player_id
"
```

The `match_player_order` should match `owner_player_id` values in territories table.

### Data quality issues

**Run validation script**:
```bash
uv run python scripts/validate_territories.py
```

Fix any reported issues before investigating further.

**Check specific match**:
```bash
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT
    turn_number,
    COUNT(*) as total_tiles,
    COUNT(owner_player_id) as owned_tiles,
    COUNT(DISTINCT owner_player_id) as unique_owners
FROM territories
WHERE match_id = YOUR_MATCH_ID
GROUP BY turn_number
ORDER BY turn_number
LIMIT 10
"
```

Should show increasing ownership over time.

## Known Limitations

1. **God view only**: Shows all tiles from turn 1, regardless of player revelation (fog of war)
2. **Territory only**: Does not show city ownership or city territory boundaries
3. **No resources**: Strategic resources are not displayed on tiles
4. **No units**: Unit positions are not shown
5. **Memory intensive**: Large matches (>150 turns, >3,000 tiles) can be slow to parse
6. **Storage intensive**: Full snapshots require ~8 MB per match in database

## References

- **Old World game mechanics**: Hexagonal grid, tile ownership, terrain types
- **Hexagonal grids**: [Red Blob Games - Hexagonal Grids](https://www.redblobgames.com/grids/hexagons/)
- **Plotly scatter**: [Plotly Scatter Markers](https://plotly.com/python/marker-style/)
- **DuckDB**: [DuckDB Documentation](https://duckdb.org/docs/)
- **Dash callbacks**: [Dash Documentation](https://dash.plotly.com/basic-callbacks)

## Related Documentation

- `docs/developer-guide.md` - Project architecture and conventions
- `docs/plans/territory-visualization.md` - Original implementation plan
- `CLAUDE.md` - Project conventions (YAGNI, DRY, commit guidelines)
