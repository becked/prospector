# Match Page Enhancement Plan

## Overview
This document outlines the plan to enhance the tournament visualizer's match analysis page with comprehensive turn-by-turn data visualization from Old World save files.

## Current State
- **Currently Displayed**: Memory events timeline only
- **Database Tables**: events, game_state, player_performance, resources, territories, matches, players
- **Available XML Data**: Rich turn-by-turn history for multiple metrics (see below)

## Available Data from Save XML

### High-Value Historical Data (Turn-by-Turn)

#### 1. YieldRateHistory
Turn-by-turn values (T2 through T{final_turn}) for:
- **Economic**: Growth, Money, Science
- **Political**: Civics, Legitimacy, Culture
- **Military**: Training, Orders
- **Resources**: Food, Iron, Stone, Wood
- **Social**: Happiness

#### 2. LegitimacyHistory
- Turn-by-turn legitimacy scores
- Key indicator of political stability
- Shows crisis points and recovery

#### 3. TechCount & Technology Progression
- List of all technologies researched
- Can derive timing from events or create tech timeline

### Cumulative/Final State Data

#### 4. YieldStockpile
Final resource stockpiles at game end:
- Civics, Training, Orders
- Food, Iron, Stone, Wood
- Culture, Science, Money

#### 5. LawClassChangeCount
Number of changes per law category:
- Slavery/Freedom
- Centralization/Vassalage
- Tyranny/Constitution
- Colonies/Serfdom
- Epics/Exploration

#### 6. GoalStartedCount & Goals
- Ambitions pursued
- Ambitions completed vs failed
- Strategic objectives chosen

#### 7. BonusCount (140+ categories)
Detailed event statistics:
- Character development (XP, archetype changes, traits)
- Diplomatic actions (marriages, ambassadors, influence)
- Resource gains/losses
- Event choices made
- Military actions

#### 8. ResourceRevealed
Resources discovered on map with counts

#### 9. Victory Information
- Victory type achieved
- Victory conditions enabled
- Turn of victory completion

### Game Configuration
- Map settings (class, size, aspect ratio)
- Difficulty level
- Turn style and timer
- Event level
- DLC content enabled
- Game options/rules

## Enhancement Plan

### Phase 1: Database Schema Updates

#### 1.1 Create yield_history table
```sql
CREATE TABLE yield_history (
    yield_history_id BIGINT PRIMARY KEY,
    match_id BIGINT REFERENCES matches(match_id),
    player_id BIGINT REFERENCES players(player_id),
    turn_number INTEGER,
    yield_type VARCHAR,  -- 'GROWTH', 'CIVICS', 'TRAINING', etc.
    value INTEGER,
    UNIQUE(match_id, player_id, turn_number, yield_type)
);
```

#### 1.2 Create legitimacy_history table
```sql
CREATE TABLE legitimacy_history (
    legitimacy_history_id BIGINT PRIMARY KEY,
    match_id BIGINT REFERENCES matches(match_id),
    player_id BIGINT REFERENCES players(player_id),
    turn_number INTEGER,
    legitimacy INTEGER,
    UNIQUE(match_id, player_id, turn_number)
);
```

#### 1.3 Create technology_progress table
```sql
CREATE TABLE technology_progress (
    tech_progress_id BIGINT PRIMARY KEY,
    match_id BIGINT REFERENCES matches(match_id),
    player_id BIGINT REFERENCES players(player_id),
    tech_name VARCHAR,
    count INTEGER,  -- Usually 1, but some techs can be researched multiple times
    UNIQUE(match_id, player_id, tech_name)
);
```

#### 1.4 Create player_statistics table
```sql
CREATE TABLE player_statistics (
    stat_id BIGINT PRIMARY KEY,
    match_id BIGINT REFERENCES matches(match_id),
    player_id BIGINT REFERENCES players(player_id),
    stat_category VARCHAR,  -- 'yield_stockpile', 'law_changes', 'goals', 'bonuses'
    stat_name VARCHAR,
    value INTEGER,
    UNIQUE(match_id, player_id, stat_category, stat_name)
);
```

#### 1.5 Extend match_metadata table
```sql
CREATE TABLE match_metadata (
    match_id BIGINT PRIMARY KEY REFERENCES matches(match_id),
    map_class VARCHAR,
    map_size VARCHAR,
    map_aspect_ratio VARCHAR,
    turn_style VARCHAR,
    turn_timer VARCHAR,
    difficulty VARCHAR,
    event_level VARCHAR,
    victory_type VARCHAR,
    victory_turn INTEGER,
    game_options JSON,  -- Store GameOptions as JSON
    dlc_content JSON,   -- Store enabled DLC as JSON
    map_settings JSON   -- Store MapMultiOptions and MapSingleOptions as JSON
);
```

### Phase 2: Data Import Enhancement

#### 2.1 Update XML parser (main.py or import script)
- Extract YieldRateHistory from each Player element
- Extract LegitimacyHistory from each Player element
- Extract TechCount from each Player element
- Extract YieldStockpile, LawClassChangeCount, GoalStartedCount, BonusCount
- Extract game configuration from Root element
- Extract victory information from Game element

#### 2.2 Create data transformation functions
- `parse_yield_history(player_elem) -> List[Dict]`
- `parse_legitimacy_history(player_elem) -> List[Dict]`
- `parse_tech_progress(player_elem) -> List[Dict]`
- `parse_player_statistics(player_elem) -> List[Dict]`
- `parse_match_metadata(root_elem) -> Dict`

#### 2.3 Implement database insertion
- Batch insert yield history records
- Batch insert legitimacy history records
- Insert technology progress records
- Insert player statistics records
- Insert match metadata

### Phase 3: Query Layer Updates

#### 3.1 Add queries to tournament_visualizer/data/queries.py

```python
def get_yield_history(match_id: int, player_id: Optional[int] = None) -> pd.DataFrame:
    """Get yield progression over time for a match."""

def get_legitimacy_history(match_id: int) -> pd.DataFrame:
    """Get legitimacy progression for all players in a match."""

def get_tech_comparison(match_id: int) -> pd.DataFrame:
    """Get technology research comparison between players."""

def get_yield_stockpile_comparison(match_id: int) -> pd.DataFrame:
    """Get final resource stockpile comparison."""

def get_player_statistics(match_id: int, category: Optional[str] = None) -> pd.DataFrame:
    """Get player statistics by category."""

def get_match_metadata(match_id: int) -> pd.DataFrame:
    """Get match configuration and settings."""
```

### Phase 4: Visualization Components

#### 4.1 Create new chart functions in tournament_visualizer/components/charts.py

```python
def create_yield_progression_chart(df: pd.DataFrame, yield_types: List[str]) -> go.Figure:
    """Multi-line chart showing yield progression over time.

    Args:
        df: DataFrame with columns: turn_number, player_name, yield_type, value
        yield_types: List of yield types to display
    """

def create_legitimacy_comparison_chart(df: pd.DataFrame) -> go.Figure:
    """Line chart comparing legitimacy between players over time."""

def create_tech_comparison_chart(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar chart comparing technology counts between players."""

def create_stockpile_comparison_chart(df: pd.DataFrame) -> go.Figure:
    """Grouped bar chart comparing final resource stockpiles."""

def create_player_statistics_chart(df: pd.DataFrame, category: str) -> go.Figure:
    """Bar chart for various player statistics categories."""
```

#### 4.2 Create layout components in tournament_visualizer/components/layouts.py

```python
def create_yield_selector(yield_types: List[str]) -> dcc.Dropdown:
    """Dropdown for selecting which yields to display."""

def create_statistics_category_tabs() -> dbc.Tabs:
    """Tab layout for different statistics categories."""
```

### Phase 5: Match Page UI Updates

#### 5.1 Add new tabs to match details section (matches.py)

Update the `create_tab_layout` call to include:

1. **Economic Development** tab
   - Yield progression chart (multi-select dropdown for yield types)
   - Final stockpile comparison bar chart
   - Table with turn-by-turn values

2. **Political & Military** tab
   - Legitimacy comparison line chart
   - Law changes comparison
   - Military statistics (Training yield, unit bonuses)

3. **Technology & Research** tab
   - Technology comparison bar chart
   - Tech tree visualization (if feasible)
   - Science yield progression

4. **Strategic Decisions** tab
   - Goals/Ambitions pursued
   - Event choices (from BonusCount)
   - Governance style (law changes)

5. **Game Settings** tab
   - Match configuration card
   - Map settings
   - Victory conditions
   - DLC content

#### 5.2 Update existing "Turn Progression" tab
- Keep memory events timeline
- Add option to overlay yield/legitimacy data
- Enhance event details table with filters

#### 5.3 Add new metric cards to overview
- Final legitimacy scores
- Total technologies researched
- Resource stockpile summary
- Ambitions completed

### Phase 6: Implementation Order

#### Sprint 1: Core Infrastructure
1. Create database schema updates
2. Write migration script
3. Implement data extraction functions
4. Test data import with sample files

#### Sprint 2: Economic Visualization
1. Implement yield_history queries
2. Create yield progression chart component
3. Create stockpile comparison chart
4. Add Economic Development tab to UI
5. Test with multiple matches

#### Sprint 3: Political & Military
1. Implement legitimacy_history queries
2. Create legitimacy comparison chart
3. Implement player_statistics queries
4. Add Political & Military tab
5. Create statistics visualization components

#### Sprint 4: Technology & Strategy
1. Implement technology_progress queries
2. Create tech comparison visualizations
3. Add Technology & Research tab
4. Add Strategic Decisions tab
5. Implement category-based statistics views

#### Sprint 5: Polish & Settings
1. Add match metadata extraction
2. Create Game Settings tab
3. Enhance metric cards in overview
4. Add filtering and interactivity
5. Performance optimization
6. Documentation and testing

## Technical Considerations

### Performance
- Yield history can be 90+ turns × 14 yield types × 2 players = ~2,500 records per match
- Use efficient batch inserts
- Consider indexing on (match_id, player_id, turn_number)
- Implement pagination for large tables

### Data Quality
- Handle missing data gracefully (early turns, incomplete games)
- Validate turn numbers match between players
- Handle edge cases (surrendered games, different turn counts)

### UI/UX
- Progressive disclosure: show key metrics first, details on demand
- Color-code players consistently across all charts
- Provide tooltips explaining game concepts
- Add export functionality for charts and data

### Testing
- Unit tests for data extraction functions
- Integration tests for database operations
- Visual regression tests for charts
- Performance tests with large datasets

## Future Enhancements

### Phase 7+: Advanced Features
1. **Comparative Analytics**
   - Compare player vs tournament average
   - Identify play style patterns
   - Strategic decision clustering

2. **Predictive Insights**
   - Key moment identification (legitimacy drops, resource spikes)
   - Win probability over time
   - Critical decision points

3. **Character & Family Analysis**
   - Character lineage visualization
   - Family relationships
   - Leader trait progression

4. **Military Detailed Analysis**
   - Unit composition over time
   - Battle outcomes
   - Territory control heatmaps

5. **Interactive Timeline**
   - Integrated timeline showing all events
   - Filterable by category
   - Click to see detailed state

## Success Metrics

- All historical data successfully imported from save files
- 4+ new visualization tabs on match page
- Sub-second load times for match visualizations
- Positive user feedback on insights gained
- Code coverage >80% for new functionality

## References

- Save file location: `/Users/jeff/Projects/Old World/miner/saves/`
- Current match page: `tournament_visualizer/pages/matches.py`
- Database queries: `tournament_visualizer/data/queries.py`
- Chart components: `tournament_visualizer/components/charts.py`
