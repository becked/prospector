# Tournament Visualization Project Plan

## Project Overview

Build a Plotly Dash web application to visualize tournament data from Old World game saves. The application will provide dynamic, interactive visualizations of match data, player performance, and game statistics.

## Data Analysis Summary

**Current Data Structure:**
- 15 tournament matches as zipped XML files
- Each XML file contains ~98K lines with detailed game state
- Rich data including: game settings, turn-by-turn progression, territories, players, events
- File sizes: ~2.6MB per save (uncompressed XML)

**Key Data Elements Found:**
- Game metadata (settings, players, dates, civilizations)
- Turn-by-turn progression data
- Territory and map information (46x46 grid, coordinates)
- Player actions and events
- Resource management data
- Diplomatic and military events

## Architecture Decision: DuckDB + Plotly Dash

### Why DuckDB Over XML?

1. **Performance**: SQL queries vs XML parsing for analytics
2. **Scalability**: Handle large datasets efficiently
3. **Query Flexibility**: Complex aggregations and joins
4. **Integration**: Seamless pandas/Python workflow
5. **Analytics**: Built-in statistical functions

### Data Pipeline Architecture

```
Tournament ZIP Files → Manual Import Script → XML Extraction → Data Parsing → DuckDB Tables → Dash App
                                          ↓
                                    Process new files only
                                    (Skip files already in DB)
```

## Database Schema Design

### Core Tables

#### 1. `matches`
```sql
CREATE TABLE matches (
    match_id INTEGER PRIMARY KEY,
    challonge_match_id INTEGER,
    file_name VARCHAR(255) NOT NULL,
    file_hash CHAR(64) NOT NULL,  -- SHA256 hash
    game_name VARCHAR(255),
    save_date TIMESTAMP,
    processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    game_mode VARCHAR(50),
    map_size VARCHAR(20),
    map_class VARCHAR(50),
    turn_style VARCHAR(50),
    turn_timer INTEGER,  -- seconds
    victory_conditions TEXT,
    total_turns INTEGER,
    winner_player_id INTEGER,

    -- Constraints
    UNIQUE(file_name, file_hash),  -- Duplicate prevention
    CHECK(total_turns >= 0),
    CHECK(turn_timer >= 0)
);

-- Indexes for performance
CREATE INDEX idx_matches_processed_date ON matches(processed_date);
CREATE INDEX idx_matches_challonge_id ON matches(challonge_match_id);
CREATE INDEX idx_matches_save_date ON matches(save_date);
CREATE INDEX idx_matches_winner ON matches(winner_player_id);
```

#### 2. `players`
```sql
CREATE TABLE players (
    player_id INTEGER PRIMARY KEY,
    match_id INTEGER NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    player_name VARCHAR(100) NOT NULL,
    civilization VARCHAR(50),
    team_id INTEGER,
    difficulty_level VARCHAR(20),
    final_score INTEGER DEFAULT 0,
    is_human BOOLEAN DEFAULT TRUE,
    final_turn_active INTEGER,

    -- Constraints
    CHECK(final_score >= 0),
    CHECK(final_turn_active >= 0)
);

-- Indexes for performance
CREATE INDEX idx_players_match_id ON players(match_id);
CREATE INDEX idx_players_name ON players(player_name);
CREATE INDEX idx_players_civilization ON players(civilization);
CREATE INDEX idx_players_match_name ON players(match_id, player_name);
```

#### 3. `game_state`
```sql
CREATE TABLE game_state (
    state_id INTEGER PRIMARY KEY,
    match_id INTEGER NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,
    active_player_id INTEGER REFERENCES players(player_id),
    game_year INTEGER,
    turn_timestamp TIMESTAMP,

    -- Constraints
    CHECK(turn_number >= 0),
    CHECK(game_year >= 0),
    UNIQUE(match_id, turn_number)  -- One state per turn per match
);

-- Indexes for performance
CREATE INDEX idx_game_state_match_turn ON game_state(match_id, turn_number);
CREATE INDEX idx_game_state_player ON game_state(active_player_id);
```

#### 4. `territories`
```sql
CREATE TABLE territories (
    territory_id INTEGER PRIMARY KEY,
    match_id INTEGER NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    x_coordinate INTEGER NOT NULL,
    y_coordinate INTEGER NOT NULL,
    turn_number INTEGER NOT NULL,  -- Track ownership changes over time
    terrain_type VARCHAR(50),
    owner_player_id INTEGER REFERENCES players(player_id),

    -- Constraints
    CHECK(x_coordinate >= 0 AND x_coordinate <= 45),  -- 46x46 grid (0-45)
    CHECK(y_coordinate >= 0 AND y_coordinate <= 45),
    CHECK(turn_number >= 0),
    UNIQUE(match_id, x_coordinate, y_coordinate, turn_number)  -- Unique territory state per turn
);

-- Indexes for spatial-temporal queries
CREATE INDEX idx_territories_spatial ON territories(match_id, x_coordinate, y_coordinate);
CREATE INDEX idx_territories_temporal ON territories(match_id, turn_number);
CREATE INDEX idx_territories_owner ON territories(owner_player_id);
CREATE INDEX idx_territories_spatial_temporal ON territories(match_id, turn_number, x_coordinate, y_coordinate);
```

#### 5. `events`
```sql
CREATE TABLE events (
    event_id INTEGER PRIMARY KEY,
    match_id INTEGER NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    player_id INTEGER REFERENCES players(player_id),
    description TEXT,
    x_coordinate INTEGER,
    y_coordinate INTEGER,
    event_data JSONB,  -- Flexible storage for event-specific data

    -- Constraints
    CHECK(turn_number >= 0),
    CHECK(x_coordinate IS NULL OR (x_coordinate >= 0 AND x_coordinate <= 45)),
    CHECK(y_coordinate IS NULL OR (y_coordinate >= 0 AND y_coordinate <= 45))
);

-- Indexes for performance
CREATE INDEX idx_events_match_turn ON events(match_id, turn_number);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_player ON events(player_id);
CREATE INDEX idx_events_location ON events(x_coordinate, y_coordinate) WHERE x_coordinate IS NOT NULL;
```

#### 6. `resources`
```sql
CREATE TABLE resources (
    resource_id INTEGER PRIMARY KEY,
    match_id INTEGER NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    player_id INTEGER NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    amount INTEGER NOT NULL,

    -- Constraints
    CHECK(turn_number >= 0),
    CHECK(amount >= 0),
    UNIQUE(match_id, player_id, turn_number, resource_type)  -- One value per resource type per turn
);

-- Indexes for performance
CREATE INDEX idx_resources_match_player ON resources(match_id, player_id);
CREATE INDEX idx_resources_turn ON resources(turn_number);
CREATE INDEX idx_resources_type ON resources(resource_type);
CREATE INDEX idx_resources_match_turn_type ON resources(match_id, turn_number, resource_type);
```

### Schema Evolution Support

#### Migration Framework
```sql
-- Schema version tracking
CREATE TABLE schema_migrations (
    version VARCHAR(20) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Insert initial version
INSERT INTO schema_migrations (version, description)
VALUES ('1.0.0', 'Initial database schema with comprehensive constraints and indexes');
```

### Performance Optimization Views

#### Materialized Views for Common Queries
```sql
-- Player performance summary
CREATE VIEW player_performance AS
SELECT
    p.player_id,
    p.player_name,
    p.civilization,
    COUNT(DISTINCT p.match_id) as total_matches,
    COUNT(CASE WHEN m.winner_player_id = p.player_id THEN 1 END) as wins,
    ROUND(
        COUNT(CASE WHEN m.winner_player_id = p.player_id THEN 1 END) * 100.0 /
        COUNT(DISTINCT p.match_id), 2
    ) as win_rate,
    AVG(p.final_score) as avg_score
FROM players p
JOIN matches m ON p.match_id = m.match_id
GROUP BY p.player_id, p.player_name, p.civilization;

-- Match summary statistics
CREATE VIEW match_summary AS
SELECT
    m.match_id,
    m.game_name,
    m.save_date,
    m.total_turns,
    m.map_size,
    m.victory_conditions,
    COUNT(p.player_id) as player_count,
    w.player_name as winner_name,
    w.civilization as winner_civilization
FROM matches m
LEFT JOIN players p ON m.match_id = p.match_id
LEFT JOIN players w ON m.winner_player_id = w.player_id
GROUP BY m.match_id, m.game_name, m.save_date, m.total_turns,
         m.map_size, m.victory_conditions, w.player_name, w.civilization;
```

## Application Structure

```
tournament_visualizer/
├── data/
│   ├── __init__.py
│   ├── parser.py          # XML parsing and data extraction
│   ├── database.py        # DuckDB connection and schema
│   ├── etl.py            # Extract, Transform, Load pipeline
│   └── queries.py         # Reusable SQL queries
├── import_tournaments.py  # Manual import script for new files
├── components/
│   ├── __init__.py
│   ├── filters.py         # Interactive filter components
│   ├── charts.py          # Chart generation functions
│   └── layouts.py         # Page layout components
├── pages/
│   ├── __init__.py
│   ├── overview.py        # Tournament overview dashboard
│   ├── matches.py         # Individual match analysis
│   ├── players.py         # Player performance analytics
│   └── maps.py           # Territory/map visualizations
├── assets/
│   └── style.css         # Custom CSS styling
├── app.py                # Main Dash application
├── config.py             # Configuration settings
└── requirements.txt      # Python dependencies
```

## Planned Visualizations

### 1. Tournament Overview Dashboard
- **Match Timeline**: Chronological view of all matches
- **Player Performance Matrix**: Win/loss records, favorite civilizations
- **Game Duration Distribution**: Histogram of match lengths
- **Map Type Preferences**: Breakdown by map size/type

### 2. Individual Match Analysis
- **Turn Progression**: Game length and pacing
- **Territory Control Timeline**: Area charts showing territorial expansion
- **Resource Accumulation**: Line charts of player resources over time
- **Critical Events**: Timeline of major game events

### 3. Player Analytics
- **Win Rate Analysis**: Success rates by civilization, map type
- **Playing Style Metrics**: Aggression, expansion patterns
- **Head-to-Head Comparisons**: Direct player matchup statistics
- **Performance Trends**: Improvement over time

### 4. Map & Territory Visualizations
- **Territory Heatmaps**: Control patterns across different maps
- **Expansion Animations**: Territory acquisition over time
- **Strategic Position Analysis**: Starting position impact on outcomes
- **Resource Distribution Maps**: Strategic resource locations

### 5. Advanced Analytics
- **Predictive Modeling**: Win probability based on early game state
- **Clustering Analysis**: Player archetype identification
- **Correlation Analysis**: Factor impact on game outcomes
- **Tournament Bracket Visualization**: Interactive tournament tree

## Implementation Phases

### Phase 1: Data Foundation (Week 1)
- [ ] Set up project structure
- [ ] Implement XML parser for game saves
- [ ] Design and create DuckDB schema with file tracking
- [ ] Build ETL pipeline for existing matches
- [ ] Implement incremental processing for new files
- [ ] Create duplicate detection and file integrity checking
- [ ] Create basic data validation and testing

### Phase 2: Core Visualizations (Week 2)
- [ ] Set up Dash application framework
- [ ] Implement tournament overview dashboard
- [ ] Create basic filtering and navigation
- [ ] Build individual match analysis pages
- [ ] Add player performance analytics

### Phase 3: Advanced Features (Week 3)
- [ ] Implement map/territory visualizations
- [ ] Add interactive animations and transitions
- [ ] Create advanced analytics and correlations
- [ ] Implement tournament bracket visualization
- [ ] Add data export capabilities

### Phase 4: Polish & Deployment (Week 4)
- [ ] UI/UX improvements and responsive design
- [ ] Performance optimization
- [ ] Documentation and user guides
- [ ] Testing and bug fixes
- [ ] Deployment preparation

## Technical Requirements

### Dependencies
```python
# Core
dash==2.17.1
plotly==5.17.0
duckdb==0.9.1
pandas==2.1.3

# Data Processing
lxml==4.9.3
python-dateutil==2.8.2

# Development
pytest==7.4.3
black==23.11.0
```

### Development Setup
1. Use `uv` for Python package management
2. Type annotations required for all functions
3. Follow project's existing code style
4. Use DuckDB for data storage and analytics
5. Implement responsive design for multiple screen sizes

## Manual Import Strategy

### Simple Import Workflow
1. **Run import script**: `python import_tournaments.py`
2. **Scan directory**: Check all `.zip` files in `saves/`
3. **Calculate hashes**: SHA256 hash for each file
4. **Check duplicates**: Query database for filename AND hash
5. **Process new files**: Import only files not in database
6. **Update database**: Add new match data with file tracking

### Database Design for Incremental Updates
- **File Tracking**: `matches.file_name` and `matches.file_hash` for duplicate prevention
- **Processing Timestamps**: `matches.processed_date` for audit trail
- **Transaction Safety**: Atomic operations to prevent partial data corruption

### Import Script Logic
```python
def import_new_tournaments():
    """Simple import: process only files not already in database"""
    existing_files = get_processed_files_from_db()  # Returns {(filename, hash), ...}

    for zip_file in scan_tournament_directory():
        file_hash = calculate_sha256(zip_file)
        if (zip_file.name, file_hash) not in existing_files:
            try:
                process_tournament_file(zip_file)
                mark_file_as_processed(zip_file.name, file_hash)
                print(f"Imported: {zip_file.name}")
            except Exception as e:
                print(f"Error processing {zip_file.name}: {e}")
                continue
        else:
            print(f"Skipped: {zip_file.name} (already processed)")
```

## Performance Considerations

### Data Loading Strategy
- **Lazy Loading**: Load match data on-demand
- **Caching**: Cache frequently accessed aggregations
- **Pagination**: Handle large datasets with pagination
- **Incremental Updates**: Support adding new matches without full reload

### Visualization Optimization
- **Data Downsampling**: Reduce data points for large time series
- **Progressive Loading**: Show basic charts first, add details
- **Client-side Filtering**: Use Dash clientside callbacks where possible
- **Memory Management**: Clear unused data from memory

## Future Enhancements

### Data Sources
- Real-time tournament integration via Challonge API
- Support for multiple tournament formats
- Integration with player ranking systems
- Historical tournament data import

### Advanced Analytics
- Machine learning models for outcome prediction
- Statistical significance testing for strategy analysis
- Network analysis of player interactions
- Automated tournament reporting

### User Experience
- Customizable dashboard layouts
- Bookmark and share specific views
- Mobile-responsive design
- Offline viewing capabilities

## Success Metrics

1. **Functionality**: All planned visualizations implemented and working
2. **Performance**: Page load times under 3 seconds
3. **Usability**: Intuitive navigation and clear visual hierarchy
4. **Insights**: Actionable insights discoverable through the interface
5. **Scalability**: Supports adding new tournaments without performance degradation

---

*This plan provides a roadmap for creating a comprehensive tournament visualization platform that transforms raw game data into actionable insights for players and tournament organizers.*
