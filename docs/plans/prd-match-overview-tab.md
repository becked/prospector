# PRD: Match Overview Tab

## Overview

Add a new "Overview" tab to the Match page that displays a turn-by-turn visual timeline comparing both players' key game events side-by-side. This becomes the default tab when viewing a match, providing an at-a-glance summary of how the game unfolded.

## User Stories

1. As a tournament viewer, I want to quickly see when each player hit key milestones (techs, laws, wonders) so I can understand who was ahead at different points.
2. As a player reviewing my match, I want to compare my progression against my opponent's to identify where I fell behind or pulled ahead.
3. As a caster/commentator, I want a visual timeline I can reference to narrate the flow of the game.

## Feature Scope

### Events Included

| Event Type | Visual Indicator | Hover Details | Data Source |
|------------|------------------|---------------|-------------|
| Tech completed | Tech icon + type indicator (science/training/law/order) | Tech name, turn | `events` (TECH_DISCOVERED) |
| Law enacted | Law icon | Law name, turn; for swaps: "Slavery → Freedom" | `events` (LAW_ADOPTED) + law class mapping |
| Wonder started | Construction icon | Wonder name, turn | `events` (WONDER_ACTIVITY) - parse "begun construction" |
| Wonder completed | Wonder icon | Wonder name, turn | `events` (WONDER_ACTIVITY) - parse "completed" |
| City founded | City icon (capital gets distinct icon) | City name, family, turn | `cities` table |
| Ruler succession | Archetype icon | Ruler name, archetype, turn | `rulers` table |
| Ruler death | Death indicator (red X overlay on previous ruler) | Ruler name, turn of death | `rulers` table (inferred from next succession_turn) |
| Battle | Battle icon | Turn, military strength lost (%) | `player_military_history` (20%+ drop between turns) |
| UU unlocked | Generic unit icon | "1st Unique Unit" or "2nd Unique Unit", turn | Derived from 4th/7th LAW_ADOPTED event |

### Tech Type Classification

Techs are categorized by their primary benefit for the type indicator:

- **Science**: Centralization, Architecture, Monasticism, Land Consolidation, Portcullis, Scholarship, Cartography, Metaphysics, Hydraulics
- **Training**: Military Drill, Composite Bow, Sovereignty
- **Law**: Rhetoric, Labor Force, Aristocracy, Navigation, Citizenship, Doctrine, Manor, Vaulting, Martial Code, Jurisprudence, Lateen Sail, Fiscal Policy
- **Order**: Navigation, Jurisprudence, Citizenship, Monasticism, Doctrine

Note: Some techs appear in multiple categories; use primary benefit.

### Law Class Mapping (for Swap Detection)

Laws within the same class are mutually exclusive. Adopting one after another indicates a swap:

| Law Class | Laws |
|-----------|------|
| Slavery/Freedom | LAW_SLAVERY, LAW_FREEDOM |
| Centralization/Vassalage | LAW_CENTRALIZATION, LAW_VASSALAGE |
| Colonies/Serfdom | LAW_COLONIES, LAW_SERFDOM |
| Monotheism/Polytheism | LAW_MONOTHEISM, LAW_POLYTHEISM |
| Tyranny/Constitution | LAW_TYRANNY, LAW_CONSTITUTION |
| Epics/Exploration | LAW_EPICS, LAW_EXPLORATION |
| Divine Rule/Legal Code | LAW_DIVINE_RULE, LAW_LEGAL_CODE |

## UI/UX Specification

### Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  [Filter: ☑Tech ☑Laws ☑Wonders ☑Cities ☑Rulers ☑Battles]       │
├─────────────────────────────────────────────────────────────────┤
│  Player 1 (Rome)              Turn        Player 2 (Persia)     │
│  ══════════════════════════════════════════════════════════════ │
│                                 5                               │
│  🏠 Rome founded (Julii)                                        │
│                                 8          🏠 Persepolis (Acham)│
│  🔬 Writing                    12                               │
│                                15          🔬 Ironworking       │
│  🏗️ Pyramids started          18                               │
│  ⚖️ Slavery                   21          ⚖️ Freedom           │
│                                25          👑 Scholar           │
│  🏛️ Pyramids complete         28                               │
│  ⚔️ Battle (-23%)             32          ⚔️ Battle (-31%)     │
│  ⚖️ Slavery → Freedom         35                               │
│  🗡️ 1st Unique Unit           38                               │
│  💀 Ruler died                 41                               │
│  👑 Tactician                  41                               │
│                                ...                              │
└─────────────────────────────────────────────────────────────────┘
```

### Visual Design

- **Player columns**: Use nation colors for visual differentiation
- **Turn column**: Center-aligned, only shows turns where at least one player has an event
- **Icons**: Unicode/emoji placeholders initially; can be replaced with custom icons later
- **Sparse rows**: Only turns with events are displayed (no empty rows)

### Interactivity

- **Hover tooltips**: Show full details for each event (name, description, exact turn)
- **Filter toggles**: Checkbox filters at top to show/hide event categories
  - Tech, Laws, Wonders, Cities, Rulers, Battles
  - All enabled by default
- **Scrollable**: Timeline scrolls vertically for long games

### Tab Behavior

- Tab name: "Overview"
- Position: First tab (leftmost)
- Default: This tab is selected by default when viewing a match

## Data Requirements

### Queries Needed

1. **Tech events**: `SELECT * FROM events WHERE event_type = 'TECH_DISCOVERED' AND match_id = ?`

2. **Law events**: `SELECT * FROM events WHERE event_type = 'LAW_ADOPTED' AND match_id = ?`
   - Parse `event_data->>'law'` for law name
   - Apply law class mapping to detect swaps

3. **Wonder events**: `SELECT * FROM events WHERE event_type = 'WONDER_ACTIVITY' AND match_id = ?`
   - Parse `description` for "begun construction" vs "completed"
   - Extract wonder name from description

4. **City founding**: `SELECT city_name, family_name, founded_turn, is_capital, player_id FROM cities WHERE match_id = ?`

5. **Ruler data**: `SELECT * FROM rulers WHERE match_id = ? ORDER BY player_id, succession_order`
   - Death turn = next ruler's succession_turn (or game end if last ruler)

6. **Battle detection**:
   ```sql
   SELECT
     turn_number,
     player_id,
     military_power,
     LAG(military_power) OVER (PARTITION BY player_id ORDER BY turn_number) as prev_power
   FROM player_military_history
   WHERE match_id = ?
   ```
   - Battle = `(prev_power - military_power) / prev_power >= 0.20`

7. **UU unlock**: Derived from counting LAW_ADOPTED events per player
   - 4th law = 1st UU
   - 7th law = 2nd UU

### Data Transformations

All events merged into a single timeline structure:

```python
@dataclass
class TimelineEvent:
    turn: int
    player_id: int
    event_type: str  # tech, law, wonder_start, wonder_complete, city, ruler, death, battle, uu_unlock
    title: str       # Short display text
    details: str     # Hover tooltip text
    icon: str        # Unicode/emoji icon
    subtype: str     # Optional: tech type, law class, etc.
```

## Technical Approach

### Implementation Steps

1. **Create timeline data query** (`queries.py`)
   - New method `get_match_timeline_events(match_id)` that unions all event sources
   - Returns DataFrame with columns: turn, player_id, event_type, title, details, icon, subtype

2. **Add Overview tab layout** (`matches.py`)
   - Add new tab as first tab
   - Create filter checkboxes component
   - Create two-column timeline component with center turn column

3. **Create timeline rendering** (`charts.py` or new `timeline.py`)
   - Function to render timeline as Dash HTML components (not Plotly chart)
   - Apply nation colors to player columns
   - Generate hover tooltips

4. **Add callbacks** (`matches.py`)
   - Callback to populate timeline when match selected
   - Callback to filter events based on checkbox state

5. **Update default tab** (`matches.py`)
   - Set Overview as active tab on page load

### File Changes

| File | Changes |
|------|---------|
| `tournament_visualizer/data/queries.py` | Add `get_match_timeline_events()` |
| `tournament_visualizer/pages/matches.py` | Add Overview tab, layout, callbacks |
| `tournament_visualizer/layouts.py` | Add timeline component helpers (if needed) |
| `tournament_visualizer/theme.py` | Ensure nation colors are available |

### Static Data Needed

- Tech type classification (science/training/law/order) - can be a dict in queries.py or config.py
- Law class mapping - can be a dict in queries.py or config.py

## Success Criteria

1. Overview tab displays as default when viewing any match
2. All 8 event types render correctly with appropriate icons
3. Two-column layout clearly shows both players' events aligned by turn
4. Only turns with events are displayed (no empty rows)
5. Hover tooltips show full event details
6. Filter checkboxes successfully hide/show event categories
7. Law swaps display as "OldLaw → NewLaw" format
8. Nation colors correctly applied to player columns
9. Timeline is scrollable for long games (100+ turns)
10. No performance issues with typical match data (~200 events)
