# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- Comprehensive yields visualization on Match Details page
  - All 14 yield types displayed in scrollable 2-column grid
  - Food, Growth, Science, Culture, Civics, Training, Money, Orders, Happiness, Discontent, Iron, Stone, Wood, Maintenance
  - Generic `create_yield_chart()` function for DRY code
  - Single database query for all yields (performance optimization)
  - 20 comprehensive unit tests covering edge cases
- Updated developer guide with yields visualization section

### Changed
- Refactored food yields chart to use generic function
- Improved code reusability for future yield additions

## [2025-10-09]

### Added
- Turn-by-turn history tracking for all matches
  - Player points history
  - Player yield history (14 yield types)
  - Player military history
  - Player legitimacy history
  - Family opinion history
  - Religion opinion history
- Comprehensive history analytics queries
- History data validation scripts

### Changed
- Renamed `resources` table to `player_yield_history` for clarity
- Improved database schema with proper indexes

### Fixed
- Removed broken `game_state` table

## [2025-10-08]

### Added
- LogData event ingestion (comprehensive turn-by-turn logs)
  - Law adoption events
  - Technology discovery events
  - Goal tracking events
- Law and technology progression charts
- Final laws and technologies display by player
- MemoryData event support
- Player statistics visualization (radar charts, grouped bar charts)

### Changed
- Improved player ID mapping (1-based database IDs)
- Enhanced event parsing with HTML cleanup

## [Initial Release]

### Added
- Tournament data import from Old World save files
- Match summary and player statistics
- DuckDB embedded database
- Dash web interface
- Basic analytics and visualizations
