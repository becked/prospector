# Plan: Match Overview Tab

## Phase 1: Data Layer

### Files Changed

| File | Changes |
|------|---------|
| `tournament_visualizer/data/game_constants.py` | New file. Tech type classification dict, law class mapping dict, timeline icon mapping. |
| `tournament_visualizer/data/queries.py` | Add `get_match_timeline_events()` method returning unified timeline DataFrame. |
| `tests/test_queries_timeline.py` | New file. Unit tests for timeline query. |

### Implementation

#### 1.1 Create `game_constants.py`

```python
# tournament_visualizer/data/game_constants.py

TECH_TYPES: dict[str, str] = {
    # Tech types classified by thematic focus: science, civics, training, growth
    # All 43 non-bonus techs from database:
    "TECH_ADMINISTRATION": "growth",      # Granary, Treasury, Caravansary
    "TECH_ARCHITECTURE": "civics",        # Courthouse, Colosseum
    "TECH_ARISTOCRACY": "civics",         # Council, Chancellor
    "TECH_BALLISTICS": "training",        # Ballista, Siege improvements
    "TECH_BATTLELINE": "training",        # Swordsman, formation combat
    "TECH_BODKIN_ARROW": "training",      # Marksman archer upgrade
    "TECH_CARTOGRAPHY": "growth",         # Harbor, trade routes
    "TECH_CITIZENSHIP": "civics",         # Legal Code law, civic buildings
    "TECH_COHORTS": "training",           # Legion, military organization
    "TECH_COINAGE": "growth",             # Mint, economic buildings
    "TECH_COMPOSITE_BOW": "training",     # Archer unit
    "TECH_DIVINATION": "science",         # Shrine, Oracle, religious knowledge
    "TECH_DOCTRINE": "civics",            # Cathedral, religious civics
    "TECH_DRAMA": "growth",               # Theater, Odeon, culture
    "TECH_ECONOMIC_REFORM": "growth",     # Market, economic improvements
    "TECH_FORESTRY": "growth",            # Lumbermill, resource extraction
    "TECH_HUSBANDRY": "growth",           # Pasture, animal resources
    "TECH_HYDRAULICS": "civics",          # Aqueduct, public works
    "TECH_INFANTRY_SQUARE": "training",   # Spearman formations
    "TECH_IRONWORKING": "training",       # Warrior, basic military
    "TECH_JURISPRUDENCE": "civics",       # Laws, legal system
    "TECH_LABOR_FORCE": "growth",         # Quarry, resource production
    "TECH_LAND_CONSOLIDATION": "growth",  # Farm improvements
    "TECH_MACHINERY": "civics",           # Workshop, engineering
    "TECH_MANOR": "growth",               # Manor house, rural economy
    "TECH_MARTIAL_CODE": "training",      # Military laws and discipline
    "TECH_METAPHYSICS": "science",        # Academy, philosophical knowledge
    "TECH_MILITARY_DRILL": "training",    # Officer, military training
    "TECH_MONASTICISM": "science",        # Monastery, religious scholarship
    "TECH_NAVIGATION": "growth",          # Port, naval trade
    "TECH_PHALANX": "training",           # Spearman unit
    "TECH_POLIS": "civics",               # City governance
    "TECH_PORTCULLIS": "civics",          # Stronghold, defensive civics
    "TECH_RHETORIC": "civics",            # Ambassador, diplomacy
    "TECH_SCHOLARSHIP": "science",        # Library, knowledge buildings
    "TECH_SOVEREIGNTY": "civics",         # Throne, royal authority
    "TECH_SPOKED_WHEEL": "training",      # Chariot unit
    "TECH_STEEL": "training",             # Advanced military equipment
    "TECH_STIRRUPS": "training",          # Horseman improvements
    "TECH_STONECUTTING": "growth",        # Quarry, stone resources
    "TECH_TRAPPING": "training",          # Scout, Hunter units
    "TECH_VAULTING": "civics",            # Basilica, monumental buildings
    "TECH_WINDLASS": "training",          # Crossbowman unit
}

LAW_CLASSES: dict[str, list[str]] = {
    # Derived from LAWCLASS_X_Y naming in player_statistics
    "slavery_freedom": ["LAW_SLAVERY", "LAW_FREEDOM"],
    "centralization_vassalage": ["LAW_CENTRALIZATION", "LAW_VASSALAGE"],
    "colonies_serfdom": ["LAW_COLONIES", "LAW_SERFDOM"],
    "monotheism_polytheism": ["LAW_MONOTHEISM", "LAW_POLYTHEISM"],
    "tyranny_constitution": ["LAW_TYRANNY", "LAW_CONSTITUTION"],
    "epics_exploration": ["LAW_EPICS", "LAW_EXPLORATION"],
    "divine_rule_legal_code": ["LAW_DIVINE_RULE", "LAW_LEGAL_CODE"],
    "guilds_elites": ["LAW_GUILDS", "LAW_ELITES"],
    "iconography_calligraphy": ["LAW_ICONOGRAPHY", "LAW_CALLIGRAPHY"],
    "philosophy_engineering": ["LAW_PHILOSOPHY", "LAW_ENGINEERING"],
    "professional_army_volunteers": ["LAW_PROFESSIONAL_ARMY", "LAW_VOLUNTEERS"],
    "tolerance_orthodoxy": ["LAW_TOLERANCE", "LAW_ORTHODOXY"],
}

# Succession laws to ignore (not shown in timeline)
IGNORED_LAWS: set[str] = {"LAW_PRIMOGENITURE", "LAW_SENIORITY", "LAW_ULTIMOGENITURE"}

# Reverse lookup: law -> class
LAW_TO_CLASS: dict[str, str] = {
    law: class_name
    for class_name, laws in LAW_CLASSES.items()
    for law in laws
}

TIMELINE_ICONS: dict[str, str] = {
    "tech": "🔬",
    "law": "⚖️",
    "law_swap": "⚖️",
    "wonder_start": "🏗️",
    "wonder_complete": "🏛️",
    "city": "🏠",
    "capital": "🏰",
    "ruler": "👑",
    "death": "💀",
    "battle": "⚔️",
    "uu_unlock": "🗡️",
}
```

#### 1.2 Add `get_match_timeline_events()` to queries.py

New method that unions multiple event sources into a single timeline:

```python
def get_match_timeline_events(self, match_id: int) -> pd.DataFrame:
    """
    Get unified timeline of key game events for a match.

    Returns DataFrame with columns:
    - turn: int
    - player_id: int
    - event_type: str (tech, law, law_swap, wonder_start, wonder_complete,
                       city, capital, ruler, death, battle, uu_unlock)
    - title: str (short display text)
    - details: str (hover tooltip)
    - icon: str (emoji)
    - subtype: str | None (tech type, law class, etc.)
    """
```

Query logic:

1. **Tech events** - `events WHERE event_type = 'TECH_DISCOVERED'`
   - Filter out `_BONUS_` variants: `NOT LIKE '%_BONUS_%'`
   - Extract tech name from `json_extract(event_data, '$.tech')`
   - Look up tech type from `TECH_TYPES`

2. **Law events** - `events WHERE event_type = 'LAW_ADOPTED'`
   - Extract law name from `json_extract(event_data, '$.law')`
   - Filter out `IGNORED_LAWS` (succession laws)
   - Use window function to detect swaps: if previous law in same class, mark as swap
   - Track law count per player for UU unlock detection

3. **Wonder events** - `events WHERE event_type = 'WONDER_ACTIVITY'`
   - **Note**: `event_data` is NULL for wonder events; must parse `description` field
   - **Deduplication**: Each wonder event appears twice (once per player observing).
     Extract builder name from description and match to player, OR dedupe by (turn, wonder_name)
     keeping only one row per actual wonder event.
   - Parse description for multi-language patterns:
     - Started (English): `"has begun construction of"` → wonder name follows
     - Started (German): `"begonnen:"` → wonder name follows the colon
     - Started (Russian): `"начинает"` → wonder name in description
     - Completed (English): `"completed by"` → wonder name at start ("The X completed")
     - Completed (German): `"abgeschlossen"` or `"fertiggestellt"`
   - Extract wonder name via language-aware regex:
     - English start: `r"construction of (.+?)[.!]"`
     - English complete: `r"^(.+?) completed"`
     - German start: `r"begonnen: (.+?)[.!]"` (name after colon)
     - German complete: `r"(.+?) (abgeschlossen|fertiggestellt)"`

4. **City founding** - `events WHERE event_type = 'CITY_FOUNDED'`
   - Use `turn_number`, `description` (contains city name)
   - Join with `cities` table for `is_capital` status if needed

5. **Ruler events** - `rulers` table
   - Succession: use `succession_turn`, `ruler_name`, `archetype`
   - **Identify rulers by `succession_order`** (not name, which can repeat)
   - Death: infer from next ruler's `succession_turn - 1` (using `succession_order + 1`)

6. **Battle detection** - `player_military_history` table
   - Calculate turn-over-turn military power drop **relative to previous turn**
   - Flag turns with >= 20% drop compared to previous turn as battles

7. **UU unlock** - Derived from law count
   - 4th LAW_ADOPTED = 1st UU
   - 7th LAW_ADOPTED = 2nd UU

Final query unions all CTEs and orders by `turn, player_id, event_priority`.

### Unit Tests

Create `tests/test_queries_timeline.py`:

```python
# Test fixtures: Create test database with known data

def test_tech_events_returned():
    """Tech discoveries appear in timeline with correct type."""
    # Insert TECH_DISCOVERED event
    # Assert tech event appears with correct title, icon, subtype

def test_tech_bonus_variants_filtered():
    """_BONUS_ tech variants are excluded from timeline."""
    # Insert TECH_ARCHITECTURE and TECH_ARCHITECTURE_BONUS_CIVICS
    # Assert only one tech event appears

def test_law_events_returned():
    """Law adoptions appear in timeline."""
    # Insert LAW_ADOPTED events
    # Assert law events appear with correct title

def test_law_swap_detection():
    """Consecutive laws in same class marked as swap."""
    # Insert LAW_SLAVERY then LAW_FREEDOM for same player
    # Assert second law has event_type='law_swap' and title contains arrow

def test_succession_laws_ignored():
    """Succession laws (primogeniture, seniority, ultimogeniture) excluded."""
    # Insert LAW_PRIMOGENITURE event
    # Assert no law events in timeline

def test_city_founding_events():
    """City founding from CITY_FOUNDED events appears in timeline."""
    # Insert CITY_FOUNDED event
    # Assert city events appear with correct turn, title (city name)

def test_capital_distinct_from_city():
    """Capital uses different event_type than regular city."""
    # Insert CITY_FOUNDED event, join with cities table where is_capital=True
    # Assert event_type='capital'

def test_ruler_succession_events():
    """Ruler successions appear in timeline."""
    # Insert rulers with succession_order 0, 1
    # Assert ruler events appear with archetype

def test_ruler_death_inferred():
    """Ruler death inferred from next succession_turn."""
    # Insert ruler 0 starting turn 1, ruler 1 starting turn 50
    # Assert death event on turn 49 for first ruler

def test_battle_detection_threshold():
    """Military power drops >= 20% flagged as battles."""
    # Insert military history: turn 10 = 100, turn 11 = 75
    # Assert battle event on turn 11 with -25%

def test_no_battle_below_threshold():
    """Military drops < 20% not flagged as battles."""
    # Insert military history: turn 10 = 100, turn 11 = 85
    # Assert no battle event

def test_uu_unlock_on_4th_and_7th_law():
    """UU unlock events generated on 4th and 7th law adoption."""
    # Insert 7 LAW_ADOPTED events for one player
    # Assert uu_unlock events on 4th and 7th law turns

def test_timeline_sorted_by_turn():
    """Timeline events sorted by turn, then player_id."""
    # Insert events on various turns
    # Assert returned DataFrame is sorted correctly

def test_empty_match_returns_empty_dataframe():
    """Match with no events returns empty DataFrame with correct columns."""
    # Query non-existent match_id
    # Assert empty DataFrame with expected column schema

def test_wonder_started_english():
    """English 'begun construction' parsed as wonder_start."""
    # Insert WONDER_ACTIVITY with description "Rome has begun construction of The Pyramids."
    # Assert event_type='wonder_start', title contains "Pyramids"

def test_wonder_completed_english():
    """English 'completed' parsed as wonder_complete."""
    # Insert WONDER_ACTIVITY with description "The Pyramids completed by Rome!"
    # Assert event_type='wonder_complete'

def test_wonder_started_german():
    """German 'begonnen:' parsed as wonder_start with name after colon."""
    # Insert WONDER_ACTIVITY with description "hat mit dem Bau folgender Erweiterung begonnen: Jervan-Aquädukt."
    # Assert event_type='wonder_start', title contains "Jervan-Aquädukt"

def test_wonder_started_russian():
    """Russian 'начинает' parsed as wonder_start."""
    # Insert WONDER_ACTIVITY with description containing "начинает"
    # Assert event_type='wonder_start'

def test_wonder_events_deduplicated():
    """Duplicate wonder events (one per observer) are deduplicated."""
    # Insert two WONDER_ACTIVITY events on same turn for same wonder (different player_id)
    # Assert only one wonder event appears in timeline
```

---

## Phase 2: UI Layer

### Files Changed

| File | Changes |
|------|---------|
| `tournament_visualizer/components/timeline.py` | New file. `create_timeline_component()` function rendering HTML timeline. |
| `tournament_visualizer/pages/matches.py` | Add Overview tab as first/default tab, add filter checkboxes, add callbacks. |
| `tests/test_timeline_component.py` | New file. Unit tests for timeline rendering logic. |

### Implementation

#### 2.1 Create `timeline.py` component

```python
# tournament_visualizer/components/timeline.py

def create_timeline_component(
    events_df: pd.DataFrame,
    player1_name: str,
    player2_name: str,
    player1_color: str,
    player2_color: str,
) -> html.Div:
    """
    Create two-column timeline HTML component.

    Args:
        events_df: DataFrame from get_match_timeline_events()
        player1_name: Display name for player 1 (left column)
        player2_name: Display name for player 2 (right column)
        player1_color: Nation color for player 1
        player2_color: Nation color for player 2

    Returns:
        Dash HTML component with timeline layout
    """
```

Component structure:
- Container div with flexbox layout
- Header row: Player 1 name | Turn | Player 2 name
- For each unique turn with events:
  - Row with three columns (player1 | turn | player2)
  - Events positioned in appropriate column
  - Each event: icon + title, with `title` attribute for hover tooltip

CSS classes for styling:
- `.timeline-container` - scrollable container
- `.timeline-row` - flex row for each turn
- `.timeline-cell-left` / `.timeline-cell-right` - player columns
- `.timeline-cell-center` - turn column
- `.timeline-event` - individual event with hover

Helper function:
```python
def format_event_title(row: pd.Series) -> str:
    """Format event for display (handles law swap arrow, etc.)."""
```

#### 2.2 Update `matches.py`

Add Overview tab as first tab in `create_tab_layout()` call:

```python
{
    "label": "Overview",
    "tab_id": "overview",
    "content": [
        # Filter checkboxes row
        dbc.Row([
            dbc.Col([
                dbc.Checklist(
                    id="match-overview-filters",
                    options=[
                        {"label": "Tech", "value": "tech"},
                        {"label": "Laws", "value": "law"},
                        {"label": "Wonders", "value": "wonder"},
                        {"label": "Cities", "value": "city"},
                        {"label": "Rulers", "value": "ruler"},
                        {"label": "Battles", "value": "battle"},
                    ],
                    value=["tech", "law", "wonder", "city", "ruler", "battle"],
                    inline=True,
                )
            ])
        ]),
        # Timeline container
        dbc.Row([
            dbc.Col([
                html.Div(id="match-overview-timeline")
            ])
        ])
    ],
}
```

Set `active_tab="overview"` in `create_tab_layout()`.

Add callback:
```python
@callback(
    Output("match-overview-timeline", "children"),
    Input("match-details-tabs", "active_tab"),
    Input("match-selector", "value"),
    Input("match-overview-filters", "value"),
)
def update_overview_timeline(
    active_tab: Optional[str],
    match_id: Optional[int],
    filters: list[str],
) -> html.Div:
    if active_tab != "overview":
        raise dash.exceptions.PreventUpdate
    if not match_id:
        return create_empty_state("Select a match", "...")

    # Get timeline data
    queries = get_queries()
    events_df = queries.get_match_timeline_events(match_id)

    # Apply filters
    filter_types = _expand_filter_types(filters)  # e.g., "wonder" -> ["wonder_start", "wonder_complete"]
    events_df = events_df[events_df["event_type"].isin(filter_types)]

    # Get player info and colors
    players_df = queries.get_match_players(match_id)
    # ... get names and colors

    return create_timeline_component(events_df, ...)
```

#### 2.3 Add timeline CSS

Add to `assets/style.css` or inline in component:

```css
.timeline-container {
    max-height: 600px;
    overflow-y: auto;
}

.timeline-row {
    display: flex;
    border-bottom: 1px solid var(--bs-border-color);
    min-height: 28px;
}

.timeline-cell-left,
.timeline-cell-right {
    flex: 1;
    padding: 4px 8px;
}

.timeline-cell-center {
    width: 60px;
    text-align: center;
    font-weight: bold;
    color: var(--bs-secondary);
}

.timeline-event {
    cursor: help;
}
```

### Unit Tests

Create `tests/test_timeline_component.py`:

```python
def test_timeline_empty_df_returns_empty_state():
    """Empty DataFrame renders empty state message."""
    result = create_timeline_component(pd.DataFrame(), ...)
    # Assert contains empty state indicator

def test_timeline_renders_both_players():
    """Events for both players appear in correct columns."""
    # Create df with player_id 1 and 2 events
    result = create_timeline_component(df, ...)
    # Assert player 1 events in left column, player 2 in right

def test_timeline_turn_column_shows_unique_turns():
    """Turn column shows each turn only once."""
    # Create df with multiple events on same turn
    result = create_timeline_component(df, ...)
    # Assert turn number appears once per row

def test_event_icon_in_output():
    """Event icon emoji appears in rendered output."""
    # Create df with tech event
    result = create_timeline_component(df, ...)
    # Assert "🔬" appears in output

def test_hover_tooltip_contains_details():
    """Event hover shows details from details column."""
    # Create df with event where details="Test details"
    result = create_timeline_component(df, ...)
    # Assert title attribute contains "Test details"

def test_law_swap_shows_arrow():
    """Law swap events show old → new format."""
    # Create df with law_swap event
    result = create_timeline_component(df, ...)
    # Assert "→" appears in output

def test_player_colors_applied():
    """Player columns use provided nation colors."""
    result = create_timeline_component(df, ..., player1_color="#ff0000", ...)
    # Assert color style applied to left column
```

---

## Phase 3: Polish and Edge Cases

### Files Changed

| File | Changes |
|------|---------|
| `tournament_visualizer/data/queries.py` | Handle edge cases in timeline query (single ruler, no military history, etc.) |
| `tournament_visualizer/components/timeline.py` | Handle sparse data, long games, visual polish. |
| `tests/test_queries_timeline.py` | Add edge case tests. |

### Implementation

#### 3.1 Query Edge Cases

- **Single ruler (no death)**: Don't generate death event for last ruler
- **No military history**: Skip battle detection if table empty for match
- **Game ends before 7 laws**: Only generate UU unlocks that actually occurred
- **Same turn events**: Maintain stable sort order (event_type priority)

#### 3.2 Component Polish

- **Long games**: Virtualization or pagination for 200+ turn games
- **Sparse data**: Handle matches with few events gracefully
- **Mobile responsive**: Stack columns on narrow screens
- **Keyboard accessibility**: Ensure tooltips work without hover

### Unit Tests

Add to `tests/test_queries_timeline.py`:

```python
def test_single_ruler_no_death_event():
    """Match with only one ruler doesn't generate death event."""
    # Insert single ruler
    # Assert no death events in timeline

def test_no_military_history_no_battles():
    """Match without military history returns no battle events."""
    # Insert match data without player_military_history
    # Assert no battle events

def test_fewer_than_4_laws_no_uu():
    """Player with fewer than 4 laws gets no UU unlock."""
    # Insert 3 LAW_ADOPTED events
    # Assert no uu_unlock events

def test_event_priority_within_turn():
    """Events on same turn sorted by type priority."""
    # Insert city, tech, ruler all on same turn
    # Assert consistent ordering
```
