# Feature Inventory for README

Date: 2025-10-25
Purpose: Document what the application ACTUALLY does (not what README says)

## Data Import Capabilities

### Core Import
- [X] **Import from local .zip files** (`import_attachments.py`)
  - Supports verbose logging
  - Force reimport option
  - Dry-run preview mode
  - Default saves/ directory or custom path

### External Integrations
- [X] **Download from Challonge API** (`download_attachments.py`)
  - Automated match file retrieval
  - API key authentication required

- [X] **Sync tournament participants** (`sync_challonge_participants.py`)
  - Links Challonge participant data to matches
  - Populates `tournament_participants` table

- [X] **Sync pick order data** (`sync_pick_order_data.py`)
  - Imports pick/ban information
  - Populates `pick_order_games` table

- [X] **Generate match narratives** (`generate_match_narratives.py`)
  - AI-generated match summaries
  - Stores in `match_metadata.narrative_summary`

### Data Override Systems
- [X] **Match winner overrides** (`data/match_winner_overrides.json`)
  - Fix corrupted winner data
  - Key: `challonge_match_id`

- [X] **Pick order overrides** (`data/pick_order_overrides.json`)
  - Manually link games to matches
  - Key: `game_number`

- [X] **Google Drive mapping overrides** (`data/gdrive_match_mapping_overrides.json`)
  - Map GDrive files to matches
  - Key: `challonge_match_id`

- [X] **Participant name overrides** (`data/participant_name_overrides.json`)
  - Link mismatched player names
  - Key: `challonge_match_id`

## Dashboard Pages

### 1. Overview (/)
Location: `tournament_visualizer/pages/overview.py`

**Tournament Statistics:**
- Total matches, players, nations played
- Recent activity summary
- Data status indicator

**Nation Analytics:**
- Nation win percentage chart
- Nation loss chart
- Nation popularity (play frequency)

**Unit Analytics:**
- Unit popularity by type
- Unit production statistics

**Map Analytics:**
- Map breakdown and distribution
- Map-specific statistics

**Law Analytics:**
- Law distribution across players
- Law efficiency metrics
- Law progression timing stats

**Ruler Analytics:**
- Archetype performance (win rates by archetype)
- Ruler trait performance
- Archetype matchup matrix (performance in specific matchups)
- Archetype-trait combinations chart

**Pick Order Analytics:**
- Nation counter-pick matrix
- Pick order win rates

**Match Table:**
- Recent matches list
- Sortable columns

### 2. Matches (/matches)
Location: `tournament_visualizer/pages/matches.py`

**Match Selection:**
- Dropdown selector for all matches
- Match metadata display

**Turn-by-Turn Tracking:**
- Points progression (6 tracked metrics)
- Yield tracking (14 yield types, scaled by 10)
- Military history
- Legitimacy history
- Family opinion history
- Religion opinion history

**Law Progression Analysis (6 visualizations):**
1. Law Milestone Timing - When each player reached 4 and 7 laws
2. Law Milestone Timeline - Horizontal timeline showing race
3. Milestone Timing Distribution - Box plots across all matches
4. Player Performance Heatmap - Color-coded performance matrix
5. Law Progression Efficiency - Scatter plot analysis
6. Cumulative Law Count Race - Turn-by-turn progression line chart

**Tech Progression:**
- Technology comparison across players
- Technology detail charts
- Tech timeline visualization
- Techs available at law milestones

**Event Timeline:**
- Aggregated event visualization
- Event type filtering
- Turn-based event display

**Ambitions:**
- Ambition timeline
- Ambition summary statistics

**Player Statistics Comparison:**
- Statistics by category
- Radar charts for multi-metric comparison

### 3. Players (/players)
Location: `tournament_visualizer/pages/players.py`

**Player Performance:**
- Player rankings
- Win rate analysis
- Performance by civilization
- Head-to-head comparisons
- Activity metrics

### 4. Maps (/maps)
Location: `tournament_visualizer/pages/maps.py`

**Map Analysis:**
- Map performance statistics
- Territory control heatmaps
- Strategic position impact
- Game length by map

## Database Schema (21 tables)

### Core Tables
1. **matches** - Match metadata and results
2. **players** - Player information per match
3. **match_winners** - Winner tracking (supports overrides)
4. **match_metadata** - Narrative summaries, GDrive links

### Turn-by-Turn History (6 tables)
5. **player_points_history** - Turn-by-turn point progression
6. **player_yield_history** - Yield production rates (14 types, raw values ÷ 10 for display)
7. **player_military_history** - Military strength over time
8. **player_legitimacy_history** - Legitimacy changes
9. **family_opinion_history** - Family relationship tracking
10. **religion_opinion_history** - Religion opinion tracking

### Event Tracking
11. **events** - MemoryData and LogData events
12. **technology_progress** - Tech research timeline

### Territory & Combat
13. **territories** - Territory control data
14. **units_produced** - Unit production records
15. **unit_classifications** - Unit type categorization

### Tournament Integration
16. **tournament_participants** - Challonge participant data
17. **pick_order_games** - Pick/ban tracking
18. **participant_name_overrides** - Name linking overrides

### Ruler System
19. **rulers** - Ruler archetypes and traits
20. **player_statistics** - End-of-game statistics

### System
21. **schema_migrations** - Database version tracking

## Analytics Queries (56 functions)

Location: `tournament_visualizer/data/queries.py`

### Match Analysis (13 queries)
- get_match_summary
- get_match_metadata
- get_recent_matches
- get_opponents
- get_head_to_head_stats
- get_match_duration_analysis
- get_database_statistics
- get_turn_progression_data
- get_territory_control_summary
- get_victory_condition_analysis
- get_event_timeline
- get_resource_progression
- get_metric_progression_stats

### Player Performance (5 queries)
- get_player_performance
- get_civilization_performance
- get_player_statistics_by_category
- get_stat_categories
- get_player_law_progression_stats

### Technology Tracking (5 queries)
- get_technology_comparison
- get_technology_summary
- get_tech_timeline_by_match
- get_tech_count_by_turn
- get_tech_timeline

### Law Progression (8 queries)
- get_law_progression
- get_total_laws_by_player
- get_law_milestone_timing
- get_law_progression_by_match
- get_cumulative_law_count_by_turn
- get_law_timeline
- get_techs_at_law_milestone
- get_law_progression_comparison (chart function)

### Nation Analytics (3 queries)
- get_nation_win_stats
- get_nation_loss_stats
- get_nation_popularity

### Map Analytics (2 queries)
- get_map_performance_analysis
- get_map_breakdown

### Unit Analytics (1 query)
- get_unit_popularity

### Yield Tracking (5 queries)
- get_yield_history_by_match
- get_yield_types
- get_points_history_by_match
- get_points_history_all_matches
- Note: All yield values are raw (÷ 10 for display)

### History Metrics (4 queries)
- get_military_history_by_match
- get_legitimacy_history_by_match
- get_family_opinion_history_by_match
- get_religion_opinion_history_by_match

### Family & Religion (2 queries)
- get_family_names
- get_religion_names

### Event Analysis (3 queries)
- get_aggregated_event_timeline
- get_ambition_timeline
- get_ambition_summary

### Ruler Analytics (5 queries)
- get_ruler_archetype_win_rates
- get_ruler_trait_win_rates
- get_ruler_succession_impact
- get_ruler_archetype_matchups
- get_ruler_archetype_trait_combinations

### Pick Order (2 queries)
- get_pick_order_win_rates
- get_nation_counter_pick_matrix

## Chart Components (30+ charts)

Location: `tournament_visualizer/components/charts.py`

### General Charts
- Match timeline chart
- Player performance chart
- Civilization performance chart
- Win rate by map chart
- Victory condition chart
- Heatmap chart (generic)
- Head-to-head chart
- Empty placeholder chart

### Resource & Progression
- Resource progression chart
- Territory control chart
- Technology comparison chart
- Technology detail chart

### Statistics
- Player statistics comparison chart
- Statistics radar chart

### Law Progression (6 charts)
- Law progression chart
- Law milestone chart
- Law progression comparison chart
- Player law performance chart
- Law milestone distribution chart
- Law efficiency chart

### Event Timeline
- Event timeline chart

### Nation Analytics
- Nation win percentage chart
- Nation loss percentage chart
- Nation popularity chart

### Ruler Analytics (4 charts)
- Ruler archetype win rates chart
- Ruler trait performance chart
- Ruler archetype matchup matrix
- Ruler archetype trait combinations chart

### Pick Order
- Nation counter-pick matrix chart
- Pick order win rates chart

## Validation Scripts (7 scripts)

1. **validate_history_data.py** - Validate turn-by-turn history tables
2. **validate_logdata.py** - Validate LogData event ingestion
3. **validate_memorydata_ownership.py** - Validate MemoryData player ownership
4. **validate_participant_queries.py** - Test participant query functions
5. **validate_participant_ui_data.py** - Validate participant UI data quality
6. **validate_participants.py** - Validate participant tracking
7. **validate_rulers.py** - Validate ruler archetype data
8. **verify_analytics.py** - Test analytics query functions

## Application Management

Location: `manage.py`

**Server Control:**
- `uv run python manage.py start` - Start server
- `uv run python manage.py stop` - Stop server
- `uv run python manage.py restart` - Restart server
- `uv run python manage.py status` - Check status
- `uv run python manage.py logs` - View logs
- `uv run python manage.py logs -f` - Follow logs (tail -f)

**Default URL:** http://localhost:8050

## Key Technical Details

### Data Sources
1. **Old World save files** (.zip containing XML) - Core game data
2. **Challonge API** - Tournament structure and participants
3. **Google Drive API** (optional) - Alternative file storage
4. **Manual overrides** - Data quality corrections (4 systems)

### Critical Domain Knowledge

**Player ID Mapping:**
- XML uses 0-based IDs, database uses 1-based
- XML `Player[@ID="0"]` → Database `player_id=1`
- Player ID="0" is valid and should NOT be skipped!

**Yield Value Display Scale:**
- All yield values stored as raw integers (10x actual display value)
- Parser stores raw XML values (215, not 21.5)
- Queries MUST divide by 10 for display: `amount / 10.0 AS amount`
- Affects: player_yield_history, all 14 yield types

**Memory Event Ownership:**
- MemoryData events stored in player's MemoryList (owner's perspective)
- MEMORYPLAYER_* events: Use `<Player>` child (subject player)
- MEMORYTRIBE/FAMILY/RELIGION_* events: Use owner Player[@ID]

### Testing Architecture

**Development dependencies:**
- black - Code formatting
- ruff - Linting
- mypy - Type checking (optional)
- pytest - Test framework

**Test coverage:**
- Parser tests (LogData, MemoryData, rulers, yields)
- Integration tests (database, ETL pipeline)
- Chart tests (law progression, ruler analytics)
- Validation scripts (7 automated validators)

## Features NOT in Current README

The following major features are completely missing from README.md:

1. **Ruler Tracking System** - Archetypes, traits, win rates, matchups (5 queries, 4 charts)
2. **Tournament Participants** - Challonge integration, participant linking
3. **Pick Order Tracking** - Pick/ban data, win rate analysis, counter-pick matrix
4. **Match Narratives** - AI-generated summaries in match_metadata
5. **Data Override Systems** - 4 JSON-based override mechanisms
6. **Turn-by-Turn History** - 6 history tables tracking progression
7. **Validation Scripts** - 7 automated data quality validators
8. **Application Management** - manage.py commands for server control
9. **Yield Display Scale** - Critical ÷10 scaling requirement
10. **Player ID Mapping** - 0-based XML to 1-based database conversion

## Summary Statistics

- **4 Dashboard Pages** (overview, matches, players, maps)
- **21 Database Tables** (vs 6 listed in current README)
- **56 Query Functions** (vs 3 examples shown)
- **30+ Chart Components** (law progression suite, ruler analytics, etc.)
- **7 Validation Scripts** (not mentioned in README)
- **4 Data Integration Sources** (saves, Challonge, GDrive, overrides)
- **6 Turn-by-Turn History Tables** (called "game_state" in README)
- **14 Yield Types** (with ÷10 scaling requirement)

## Recommendations for New README

### Must Include
1. All 4 data integration sources (not just save files)
2. Ruler analytics features
3. Pick order tracking
4. Match narratives
5. manage.py server control (not direct app.py)
6. Link to developer-guide.md for 21-table schema (don't list inline)
7. Link to developer-guide.md for 56 query functions (show 1 example)

### Keep Brief
- 1 example query (not 3)
- Point to developer-guide.md for details
- Remove inline project structure (in developer-guide.md)
- Remove inline configuration (in developer-guide.md)
- Simplify deployment (link to deployment-guide.md)

### Quick Start Focus
- 3-step installation: sync → import → start
- Use manage.py start (not app.py)
- Use import_attachments.py (not import_tournaments.py)
- Show common troubleshooting (port in use, no data, import errors)
