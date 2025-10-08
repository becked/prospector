# LogData Ingestion Implementation Plan

## Overview

Currently, the parser only extracts `MemoryData` events from Old World save files, which provides limited historical data (e.g., only 1 law event out of 13 actual law adoptions). The `LogData` sections within `TurnSummary` elements contain comprehensive turn-by-turn historical data including:

- **LAW_ADOPTED**: Which laws were adopted and when (13 events vs 1 memory event)
- **TECH_DISCOVERED**: Which techs were researched and when (44 events vs 0 memory events)
- **GOAL_STARTED/GOAL_FINISHED**: Ambition tracking (e.g., "Enact Four Laws")
- **Other gameplay events**: City founding, character births/deaths, etc. (~79 unique event types)

This plan will guide you through adding LogData parsing to capture law adoption and tech discovery timelines.

---

## Prerequisites

### Domain Knowledge

**Old World Save File Structure:**
- Save files are `.zip` archives containing a single `.xml` file
- Each save represents the end state of a match
- XML structure:
  ```xml
  <Root>
    <Player ID="0" Name="anarkos">
      <TurnSummary>
        <LogData>
          <Text>Human-readable description</Text>
          <Type>EVENT_TYPE</Type>
          <Data1>Primary data (e.g., LAW_SLAVERY)</Data1>
          <Data2>Secondary data</Data2>
          <Data3>Tertiary data</Data3>
          <Turn>11</Turn>
          <TeamTurn>0</TeamTurn>
        </LogData>
        <!-- More LogData entries -->
      </TurnSummary>
    </Player>
  </Root>
  ```

**Player ID Mapping:**
- XML uses `Player ID="0"` and `ID="1"`
- Database uses 1-based sequential player_id
- Help links in Text contain player index: `HELP_LAW,LAW_SLAVERY,0` (0=first player, 1=second player)

**Current Architecture:**
```
tournament_visualizer/data/
├── parser.py          # OldWorldSaveParser class - extracts data from XML
├── etl.py            # Orchestrates parsing and loading into database
├── database.py       # Database connection and operations
└── queries.py        # SQL queries for analytics
```

### Tools & Libraries

- **Python 3.13** (managed by `uv`)
- **DuckDB** - embedded database for analytics
- **xml.etree.ElementTree** - XML parsing
- **pytest** - testing framework (you'll need to set this up)

### Key Principles

1. **DRY (Don't Repeat Yourself)**: Reuse the existing event extraction pattern
2. **YAGNI (You Ain't Gonna Need It)**: Only implement law and tech events now, not all 79 types
3. **TDD (Test-Driven Development)**: Write tests before implementation
4. **Frequent commits**: Commit after each task completion

---

## Task Breakdown

### Phase 1: Setup & Understanding (2-3 hours)

#### Task 1.1: Environment Setup
**Goal**: Get the codebase running and understand the current flow

**Files to read:**
- `README.md` - Project overview
- `CLAUDE.md` - Project-specific instructions
- `import_tournaments.py` - Entry point for data import
- `tournament_visualizer/data/parser.py` - Current parser implementation

**Steps:**
1. Clone/pull the repository
2. Run `uv sync` to install dependencies
3. Verify Python version: `uv run python --version` (should be 3.13.x)
4. List existing save files: `ls -la saves/`
5. Check database structure:
   ```bash
   uv run duckdb tournament_data.duckdb -readonly -c "DESCRIBE events"
   ```

**Expected output:** You should see the events table with columns: event_id, match_id, turn_number, event_type, player_id, description, x_coordinate, y_coordinate, event_data

**Commit checkpoint**: None (just familiarization)

---

#### Task 1.2: Extract Sample XML for Testing
**Goal**: Create a small test XML file with known law/tech events

**Files to create:**
- `tests/fixtures/sample_save.xml` (new file)

**Steps:**
1. Create test fixtures directory:
   ```bash
   mkdir -p tests/fixtures
   ```

2. Extract one save file to examine:
   ```bash
   unzip -q saves/match_426504721_anarkos-becked.zip -d tmp/
   ```

3. Create a minimal test XML with the essential structure:
   ```bash
   # Extract just the relevant sections (first ~1000 lines should include player data)
   head -n 1000 tmp/OW-*.xml > tests/fixtures/sample_save.xml
   ```

4. Manually verify the test file contains:
   - At least one `<Player>` element
   - At least one `<TurnSummary>` section
   - At least one `<LogData>` with `LAW_ADOPTED`
   - At least one `<LogData>` with `TECH_DISCOVERED`

**Verification:**
```bash
grep -c "LAW_ADOPTED" tests/fixtures/sample_save.xml  # Should be > 0
grep -c "TECH_DISCOVERED" tests/fixtures/sample_save.xml  # Should be > 0
```

**Commit**: `test: Add sample XML fixture for LogData parsing tests`

---

#### Task 1.3: Understand Current Event Extraction
**Goal**: Read and understand how MemoryData events are currently extracted

**Files to read:**
- `tournament_visualizer/data/parser.py` - Lines 263-340 (`extract_events` method)

**Questions to answer:**
1. What does `extract_events()` return? (List of dict with what keys?)
2. How does it map player IDs? (See line 294-295)
3. What lookup tables does it build? (Lines 277-278)
4. How are events stored in the database? (Check `etl.py` for usage)

**Deliverable**: Write a comment block at the top of your test file explaining:
```python
"""
Current extract_events() behavior:
- Returns: List[Dict[str, Any]] with keys: turn_number, event_type, player_id, description, x_coordinate, y_coordinate, event_data
- Player ID mapping: XML Player="0" becomes None, Player="1+" becomes player_id
- Extracts from: MemoryData elements only (not LogData)
- Used by: etl.py process_save_file() to insert into events table
"""
```

**Commit**: `docs: Add notes on current event extraction behavior`

---

### Phase 2: Test-Driven Development Setup (2-3 hours)

#### Task 2.1: Set Up Testing Infrastructure
**Goal**: Create pytest configuration and first test file

**Files to create:**
- `pyproject.toml` - Update with pytest configuration
- `tests/__init__.py` - Empty file to make tests a package
- `tests/test_parser_logdata.py` - Test file for new functionality

**Steps:**

1. Check if pytest is in dependencies:
   ```bash
   grep pytest pyproject.toml
   ```

2. If not present, add it:
   ```bash
   uv add --dev pytest
   ```

3. Create test file structure:
   ```bash
   mkdir -p tests
   touch tests/__init__.py
   ```

4. Create initial test file (`tests/test_parser_logdata.py`):
   ```python
   """Tests for LogData extraction from Old World save files."""

   import pytest
   from pathlib import Path
   from tournament_visualizer.data.parser import OldWorldSaveParser


   @pytest.fixture
   def sample_xml_path():
       """Path to sample XML fixture."""
       return Path(__file__).parent / "fixtures" / "sample_save.xml"


   def test_sample_fixture_exists(sample_xml_path):
       """Verify test fixture exists."""
       assert sample_xml_path.exists(), f"Test fixture not found: {sample_xml_path}"
   ```

5. Run the test to verify setup:
   ```bash
   uv run pytest tests/test_parser_logdata.py -v
   ```

**Expected output**: 1 test should pass

**Commit**: `test: Set up pytest infrastructure and initial test file`

---

#### Task 2.2: Write Tests for Law Adoption Extraction
**Goal**: Write failing tests that define the expected behavior

**Files to modify:**
- `tests/test_parser_logdata.py`

**Add these test cases:**

```python
class TestLawAdoptionExtraction:
    """Tests for extracting LAW_ADOPTED events from LogData."""

    def test_extract_logdata_events_returns_list(self, sample_xml_path):
        """extract_logdata_events() should return a list."""
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.extract_and_parse()

        # This method doesn't exist yet - we'll create it
        events = parser.extract_logdata_events()

        assert isinstance(events, list)

    def test_extract_law_adoptions_finds_all_laws(self, sample_xml_path):
        """Should find all LAW_ADOPTED events in the file."""
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.extract_and_parse()

        events = parser.extract_logdata_events()
        law_events = [e for e in events if e['event_type'] == 'LAW_ADOPTED']

        # Count expected law adoptions in fixture
        # You'll need to manually count these in your fixture
        # For anarkos-becked match, there should be 13 total
        assert len(law_events) > 0, "Should find at least one law adoption"

    def test_law_adoption_event_structure(self, sample_xml_path):
        """Law adoption events should have correct structure."""
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.extract_and_parse()

        events = parser.extract_logdata_events()
        law_events = [e for e in events if e['event_type'] == 'LAW_ADOPTED']

        if law_events:
            event = law_events[0]

            # Required fields
            assert 'turn_number' in event
            assert 'event_type' in event
            assert 'player_id' in event
            assert 'description' in event

            # Type checks
            assert isinstance(event['turn_number'], int)
            assert event['event_type'] == 'LAW_ADOPTED'
            assert isinstance(event['player_id'], int)
            assert isinstance(event['description'], str)

    def test_law_adoption_extracts_law_name(self, sample_xml_path):
        """Should extract the specific law from Data1."""
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.extract_and_parse()

        events = parser.extract_logdata_events()
        law_events = [e for e in events if e['event_type'] == 'LAW_ADOPTED']

        if law_events:
            event = law_events[0]

            # event_data should contain the law name
            assert event.get('event_data') is not None
            assert 'law' in event['event_data']
            assert event['event_data']['law'].startswith('LAW_')

    def test_law_adoption_correct_player_mapping(self, sample_xml_path):
        """Should correctly map player IDs from XML to database."""
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.extract_and_parse()

        events = parser.extract_logdata_events()
        law_events = [e for e in events if e['event_type'] == 'LAW_ADOPTED']

        # Player IDs should be 1-based (matching players table)
        player_ids = [e['player_id'] for e in law_events]
        assert all(pid >= 1 for pid in player_ids), "Player IDs should be 1-based"
```

**Run tests (they should fail):**
```bash
uv run pytest tests/test_parser_logdata.py -v
```

**Expected output**: All tests should fail with "AttributeError: 'OldWorldSaveParser' object has no attribute 'extract_logdata_events'"

**Commit**: `test: Add failing tests for LAW_ADOPTED LogData extraction`

---

#### Task 2.3: Write Tests for Tech Discovery Extraction
**Goal**: Write tests for TECH_DISCOVERED events

**Files to modify:**
- `tests/test_parser_logdata.py`

**Add these test cases:**

```python
class TestTechDiscoveryExtraction:
    """Tests for extracting TECH_DISCOVERED events from LogData."""

    def test_extract_tech_discoveries_finds_techs(self, sample_xml_path):
        """Should find TECH_DISCOVERED events in the file."""
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.extract_and_parse()

        events = parser.extract_logdata_events()
        tech_events = [e for e in events if e['event_type'] == 'TECH_DISCOVERED']

        # anarkos-becked match has 44 tech discoveries
        assert len(tech_events) > 0, "Should find at least one tech discovery"

    def test_tech_discovery_event_structure(self, sample_xml_path):
        """Tech discovery events should have correct structure."""
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.extract_and_parse()

        events = parser.extract_logdata_events()
        tech_events = [e for e in events if e['event_type'] == 'TECH_DISCOVERED']

        if tech_events:
            event = tech_events[0]

            # Required fields
            assert 'turn_number' in event
            assert 'event_type' in event
            assert 'player_id' in event

            # Type checks
            assert isinstance(event['turn_number'], int)
            assert event['event_type'] == 'TECH_DISCOVERED'
            assert isinstance(event['player_id'], int)

    def test_tech_discovery_extracts_tech_name(self, sample_xml_path):
        """Should extract the specific tech from Data1."""
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.extract_and_parse()

        events = parser.extract_logdata_events()
        tech_events = [e for e in events if e['event_type'] == 'TECH_DISCOVERED']

        if tech_events:
            event = tech_events[0]

            # event_data should contain the tech name
            assert event.get('event_data') is not None
            assert 'tech' in event['event_data']
            assert event['event_data']['tech'].startswith('TECH_')

    def test_tech_discoveries_ordered_by_turn(self, sample_xml_path):
        """Tech discoveries should be extractable in turn order."""
        parser = OldWorldSaveParser(str(sample_xml_path))
        parser.extract_and_parse()

        events = parser.extract_logdata_events()
        tech_events = [e for e in events if e['event_type'] == 'TECH_DISCOVERED']

        # Check that we can order by turn
        turns = [e['turn_number'] for e in tech_events]
        assert turns == sorted(turns), "Should preserve turn order"
```

**Run tests:**
```bash
uv run pytest tests/test_parser_logdata.py::TestTechDiscoveryExtraction -v
```

**Expected output**: All tests should fail

**Commit**: `test: Add failing tests for TECH_DISCOVERED LogData extraction`

---

### Phase 3: Implementation (4-6 hours)

#### Task 3.1: Implement LogData Extraction Method
**Goal**: Add new method to parser to extract LogData events

**Files to modify:**
- `tournament_visualizer/data/parser.py`

**Steps:**

1. Open `parser.py` and find the `extract_events()` method (around line 263)

2. After the `extract_events()` method, add a new method:

```python
def extract_logdata_events(self) -> List[Dict[str, Any]]:
    """Extract game events from LogData elements in TurnSummary sections.

    LogData contains more detailed historical information than MemoryData,
    including law adoptions, tech discoveries, and goal tracking.

    Returns:
        List of event dictionaries from LogData
    """
    if self.root is None:
        raise ValueError("XML not parsed. Call extract_and_parse() first.")

    events = []

    # Find all Player elements
    player_elements = self.root.findall('.//Player')

    for player_elem in player_elements:
        # Get player's XML ID (0-based in XML)
        player_xml_id = player_elem.get('ID')
        if player_xml_id is None:
            continue

        # Convert to 1-based player_id for database
        # XML ID="0" is player 1, ID="1" is player 2
        player_id = int(player_xml_id) + 1

        # Find TurnSummary for this player
        turn_summary = player_elem.find('.//TurnSummary')
        if turn_summary is None:
            continue

        # Extract all LogData elements
        log_data_elements = turn_summary.findall('.//LogData')

        for log_elem in log_data_elements:
            event = self._extract_single_logdata_event(log_elem, player_id)
            if event:
                events.append(event)

    return events


def _extract_single_logdata_event(self, log_elem: ET.Element, player_id: int) -> Optional[Dict[str, Any]]:
    """Extract a single LogData event.

    Args:
        log_elem: LogData XML element
        player_id: Database player ID (1-based)

    Returns:
        Event dictionary or None if event should be skipped
    """
    # Extract basic fields
    type_elem = log_elem.find('Type')
    turn_elem = log_elem.find('Turn')

    if type_elem is None or turn_elem is None:
        return None

    event_type = type_elem.text
    turn_number = self._safe_int(turn_elem.text)

    if turn_number is None:
        return None

    # Extract data fields
    data1_elem = log_elem.find('Data1')
    data2_elem = log_elem.find('Data2')
    data3_elem = log_elem.find('Data3')

    data1 = data1_elem.text if data1_elem is not None else None
    data2 = data2_elem.text if data2_elem is not None else None
    data3 = data3_elem.text if data3_elem is not None else None

    # Extract human-readable text
    text_elem = log_elem.find('Text')
    text = text_elem.text if text_elem is not None else None

    # Build event_data based on event type
    event_data = self._build_logdata_event_data(event_type, data1, data2, data3)

    # Build description
    description = self._format_logdata_event(event_type, event_data, text)

    return {
        'turn_number': turn_number,
        'event_type': event_type,
        'player_id': player_id,
        'description': description,
        'x_coordinate': None,
        'y_coordinate': None,
        'event_data': event_data if event_data else None
    }


def _build_logdata_event_data(self, event_type: str, data1: Optional[str],
                               data2: Optional[str], data3: Optional[str]) -> Optional[Dict[str, Any]]:
    """Build event_data dict based on event type.

    Args:
        event_type: Type of LogData event
        data1: Primary data field
        data2: Secondary data field
        data3: Tertiary data field

    Returns:
        Dictionary of event data or None
    """
    if event_type == 'LAW_ADOPTED' and data1:
        return {'law': data1}

    if event_type == 'TECH_DISCOVERED' and data1:
        return {'tech': data1}

    # Add more event types as needed (YAGNI - only implement what we need now)

    return None


def _format_logdata_event(self, event_type: str, event_data: Optional[Dict[str, Any]],
                          text: Optional[str]) -> str:
    """Format a LogData event into a readable description.

    Args:
        event_type: Type of event
        event_data: Event data dictionary
        text: Human-readable text from XML (may contain HTML tags)

    Returns:
        Human-readable description
    """
    if event_type == 'LAW_ADOPTED' and event_data and 'law' in event_data:
        law_name = event_data['law'].replace('LAW_', '').replace('_', ' ').title()
        return f"Adopted {law_name}"

    if event_type == 'TECH_DISCOVERED' and event_data and 'tech' in event_data:
        tech_name = event_data['tech'].replace('TECH_', '').replace('_', ' ').title()
        return f"Discovered {tech_name}"

    # Fallback: use event type or text
    if text:
        # Strip HTML tags for database storage
        import re
        clean_text = re.sub(r'<[^>]+>', '', text)
        return clean_text[:200]  # Limit length

    # Final fallback
    return event_type.replace('_', ' ').title()
```

3. Run tests to see if implementation works:
```bash
uv run pytest tests/test_parser_logdata.py -v
```

**Expected output**: Most tests should pass. Debug any failures.

**Commit**: `feat: Add extract_logdata_events method to parser`

---

#### Task 3.2: Fix Player ID Mapping Issues
**Goal**: Ensure player IDs map correctly between XML and database

**Context**: The XML uses `Player ID="0"` for the first player, but our database uses 1-based IDs. The help links in the Text field also use 0-based indexing.

**Files to modify:**
- `tournament_visualizer/data/parser.py` (the method you just added)

**Debug process:**

1. Add a test to verify player mapping:
```python
def test_law_adoptions_match_known_players(sample_xml_path):
    """Law adoptions should map to correct players (anarkos=player 1, becked=player 2)."""
    parser = OldWorldSaveParser(str(sample_xml_path))
    parser.extract_and_parse()

    events = parser.extract_logdata_events()
    law_events = [e for e in events if e['event_type'] == 'LAW_ADOPTED']

    # For anarkos-becked match:
    # anarkos (XML ID="0") adopted laws on turns: 11, 36, 49, 54, 55, 63
    # becked (XML ID="1") adopted laws on turns: 20, 37, 43, 46, 50, 64, 68

    player_1_laws = [e for e in law_events if e['player_id'] == 1]
    player_2_laws = [e for e in law_events if e['player_id'] == 2]

    assert len(player_1_laws) > 0, "Player 1 should have law adoptions"
    assert len(player_2_laws) > 0, "Player 2 should have law adoptions"

    # Verify some known turn numbers
    player_1_turns = [e['turn_number'] for e in player_1_laws]
    assert 11 in player_1_turns, "Player 1 should adopt law on turn 11"
```

2. Run this test and fix any mapping issues in your implementation

3. Verify the mapping is correct by comparing with the actual player names in the XML

**Commit**: `fix: Correct player ID mapping in LogData extraction`

---

#### Task 3.3: Integrate LogData Extraction into ETL Pipeline
**Goal**: Merge LogData events with MemoryData events in the ETL process

**Files to modify:**
- `tournament_visualizer/data/etl.py`

**Steps:**

1. Find the `process_save_file()` function in `etl.py`

2. Look for where `extract_events()` is called (search for `parser.extract_events()`)

3. After that line, add LogData extraction and merge the results:

```python
# Existing code:
memory_events = parser.extract_events()

# Add this:
logdata_events = parser.extract_logdata_events()

# Merge both event sources
all_events = memory_events + logdata_events

# Update the rest of the function to use all_events instead of memory_events
```

4. Make sure the variable name is updated everywhere it's used in that function

**Verification:**
```bash
# Test the full ETL process on one file
uv run python import_tournaments.py --directory saves --dry-run
```

**Expected output**: Should show the file would be processed without errors

**Commit**: `feat: Integrate LogData events into ETL pipeline`

---

#### Task 3.4: Handle Duplicate Events
**Goal**: Prevent duplicate events if same match is imported multiple times

**Context**: Some events exist in both MemoryData and LogData. We need to deduplicate.

**Files to modify:**
- `tournament_visualizer/data/etl.py`

**Steps:**

1. After merging events, add deduplication logic:

```python
# Merge both event sources
all_events = memory_events + logdata_events

# Deduplicate based on (turn_number, event_type, player_id)
# Keep LogData version if both exist (more detailed)
seen = set()
deduplicated_events = []

# Sort to process LogData events first (prefer them)
all_events.sort(key=lambda e: (
    e['turn_number'],
    e['event_type'],
    e['player_id'] or 0,
    0 if 'law' in str(e.get('event_data', '')) else 1  # Prefer events with more data
))

for event in all_events:
    key = (event['turn_number'], event['event_type'], event.get('player_id'))
    if key not in seen:
        seen.add(key)
        deduplicated_events.append(event)

# Use deduplicated_events for database insertion
```

2. Test with a real import to verify no duplicate errors

**Commit**: `fix: Deduplicate events from MemoryData and LogData sources`

---

### Phase 4: Database Schema Updates (1-2 hours)

#### Task 4.1: Add Database Migration for Event Data
**Goal**: Ensure event_data column can store the new JSON structure

**Files to check:**
- `tournament_visualizer/data/database.py` - Look for schema definitions

**Steps:**

1. Check current events table schema:
```bash
uv run duckdb tournament_data.duckdb -c "DESCRIBE events"
```

2. Verify the `event_data` column is JSON type

3. If changes are needed, document the migration in a new file:
   - Create `docs/migrations/001_add_logdata_events.md`
   - Document the schema changes
   - Provide rollback steps

**For DuckDB, schema changes are usually automatic**, but document them for clarity.

**Commit**: `docs: Document event_data schema for LogData events`

---

#### Task 4.2: Create Database Indexes for Performance
**Goal**: Add indexes for common law/tech queries

**Files to modify:**
- `tournament_visualizer/data/database.py`

**Steps:**

1. Find the table creation SQL in `database.py`

2. After the events table creation, add indexes:

```sql
-- Add these after CREATE TABLE events
CREATE INDEX IF NOT EXISTS idx_events_type_player
ON events(event_type, player_id, turn_number);

CREATE INDEX IF NOT EXISTS idx_events_match_turn
ON events(match_id, turn_number);
```

3. Test index creation:
```bash
uv run python -c "
from tournament_visualizer.data.database import get_database
db = get_database()
# Indexes should be created automatically
"
```

**Commit**: `perf: Add indexes for law and tech event queries`

---

### Phase 5: Analytics & Queries (2-3 hours)

#### Task 5.1: Create Law Progression Query
**Goal**: Add query to calculate law milestones (4 laws, 7 laws)

**Files to modify:**
- `tournament_visualizer/data/queries.py`

**Add this query function:**

```python
def get_law_progression_by_match(db, match_id: Optional[int] = None) -> pd.DataFrame:
    """Get law progression for players, showing when they reached 4 and 7 laws.

    Args:
        db: Database connection
        match_id: Optional match_id to filter (None for all matches)

    Returns:
        DataFrame with columns: match_id, player_id, player_name, civilization,
                                turn_to_4_laws, turn_to_7_laws, total_laws
    """
    query = """
    WITH law_events AS (
        SELECT
            e.match_id,
            e.player_id,
            e.turn_number,
            ROW_NUMBER() OVER (
                PARTITION BY e.match_id, e.player_id
                ORDER BY e.turn_number
            ) as law_number
        FROM events e
        WHERE e.event_type = 'LAW_ADOPTED'
            AND e.player_id IS NOT NULL
            {match_filter}
    ),
    milestones AS (
        SELECT
            match_id,
            player_id,
            MAX(CASE WHEN law_number = 4 THEN turn_number END) as turn_to_4_laws,
            MAX(CASE WHEN law_number = 7 THEN turn_number END) as turn_to_7_laws,
            MAX(law_number) as total_laws
        FROM law_events
        GROUP BY match_id, player_id
    )
    SELECT
        m.match_id,
        m.player_id,
        p.player_name,
        p.civilization,
        m.turn_to_4_laws,
        m.turn_to_7_laws,
        m.total_laws
    FROM milestones m
    JOIN players p ON m.match_id = p.match_id AND m.player_id = p.player_id
    ORDER BY m.match_id, m.player_id
    """

    match_filter = f"AND e.match_id = {match_id}" if match_id else ""
    query = query.format(match_filter=match_filter)

    return db.execute_query(query)
```

**Test the query:**
```python
# In a test file or interactive session
from tournament_visualizer.data.database import get_database
from tournament_visualizer.data.queries import get_law_progression_by_match

db = get_database()
result = get_law_progression_by_match(db, match_id=10)  # anarkos vs becked
print(result)
```

**Expected output:** DataFrame showing anarkos reached 4 laws on turn 54, becked reached 4 on turn 46 and 7 on turn 68

**Commit**: `feat: Add law progression analytics query`

---

#### Task 5.2: Create Tech Progression Query
**Goal**: Add query to show tech discovery timeline per player

**Files to modify:**
- `tournament_visualizer/data/queries.py`

**Add this query function:**

```python
def get_tech_timeline_by_match(db, match_id: int) -> pd.DataFrame:
    """Get chronological tech discoveries for a match.

    Args:
        db: Database connection
        match_id: Match ID to analyze

    Returns:
        DataFrame with columns: match_id, player_id, player_name, turn_number,
                                tech_name, tech_sequence
    """
    query = """
    SELECT
        e.match_id,
        e.player_id,
        p.player_name,
        e.turn_number,
        json_extract(e.event_data, '$.tech') as tech_name,
        ROW_NUMBER() OVER (
            PARTITION BY e.match_id, e.player_id
            ORDER BY e.turn_number
        ) as tech_sequence
    FROM events e
    JOIN players p ON e.match_id = p.match_id AND e.player_id = p.player_id
    WHERE e.event_type = 'TECH_DISCOVERED'
        AND e.match_id = ?
    ORDER BY e.player_id, e.turn_number
    """

    return db.execute_query(query, [match_id])


def get_tech_count_by_turn(db, match_id: int) -> pd.DataFrame:
    """Get cumulative tech count by turn for each player.

    Useful for racing line charts showing tech progression over time.

    Args:
        db: Database connection
        match_id: Match ID to analyze

    Returns:
        DataFrame with columns: player_id, player_name, turn_number, cumulative_techs
    """
    query = """
    WITH tech_events AS (
        SELECT
            e.player_id,
            p.player_name,
            e.turn_number,
            COUNT(*) OVER (
                PARTITION BY e.player_id
                ORDER BY e.turn_number
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) as cumulative_techs
        FROM events e
        JOIN players p ON e.match_id = p.match_id AND e.player_id = p.player_id
        WHERE e.event_type = 'TECH_DISCOVERED'
            AND e.match_id = ?
    )
    SELECT DISTINCT
        player_id,
        player_name,
        turn_number,
        cumulative_techs
    FROM tech_events
    ORDER BY player_id, turn_number
    """

    return db.execute_query(query, [match_id])
```

**Commit**: `feat: Add tech progression analytics queries`

---

#### Task 5.3: Create Combined Law + Tech Analysis
**Goal**: Show which techs players had when they reached law milestones

**Files to modify:**
- `tournament_visualizer/data/queries.py`

**Add this query function:**

```python
def get_techs_at_law_milestone(db, match_id: int, milestone: int = 4) -> pd.DataFrame:
    """Get list of techs each player had when reaching a law milestone.

    Args:
        db: Database connection
        match_id: Match ID to analyze
        milestone: Law milestone (4 or 7)

    Returns:
        DataFrame with columns: player_id, player_name, milestone_turn,
                                tech_count, tech_list
    """
    query = """
    WITH law_milestones AS (
        SELECT
            e.match_id,
            e.player_id,
            p.player_name,
            e.turn_number as milestone_turn,
            ROW_NUMBER() OVER (
                PARTITION BY e.match_id, e.player_id
                ORDER BY e.turn_number
            ) as law_number
        FROM events e
        JOIN players p ON e.match_id = p.match_id AND e.player_id = p.player_id
        WHERE e.event_type = 'LAW_ADOPTED'
            AND e.match_id = ?
    ),
    milestone_turns AS (
        SELECT
            match_id,
            player_id,
            player_name,
            milestone_turn
        FROM law_milestones
        WHERE law_number = ?
    ),
    techs_at_milestone AS (
        SELECT
            mt.player_id,
            mt.player_name,
            mt.milestone_turn,
            json_extract(e.event_data, '$.tech') as tech_name
        FROM milestone_turns mt
        JOIN events e ON e.match_id = mt.match_id
            AND e.player_id = mt.player_id
            AND e.turn_number <= mt.milestone_turn
        WHERE e.event_type = 'TECH_DISCOVERED'
    )
    SELECT
        player_id,
        player_name,
        milestone_turn,
        COUNT(*) as tech_count,
        string_agg(tech_name, ', ') as tech_list
    FROM techs_at_milestone
    GROUP BY player_id, player_name, milestone_turn
    ORDER BY player_id
    """

    return db.execute_query(query, [match_id, milestone])
```

**Commit**: `feat: Add combined law/tech milestone analysis query`

---

### Phase 6: Testing & Validation (2-3 hours)

#### Task 6.1: Integration Test with Real Data
**Goal**: Test the full pipeline with actual save files

**Files to create:**
- `tests/test_integration_logdata.py`

**Create integration test:**

```python
"""Integration tests for LogData ingestion pipeline."""

import pytest
from pathlib import Path
import tempfile
import shutil
from tournament_visualizer.data.etl import process_tournament_directory, initialize_database


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_tournament.duckdb"

    yield db_path

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_save_dir(tmp_path):
    """Create temp directory with one save file."""
    save_dir = tmp_path / "saves"
    save_dir.mkdir()

    # Copy one save file for testing
    source = Path("saves/match_426504721_anarkos-becked.zip")
    if source.exists():
        shutil.copy(source, save_dir / source.name)

    return save_dir


def test_full_pipeline_with_logdata(temp_db, sample_save_dir):
    """Test complete ETL pipeline including LogData extraction."""
    # Initialize database
    db = initialize_database(str(temp_db))

    # Process the save file
    results = process_tournament_directory(str(sample_save_dir))

    # Verify processing succeeded
    assert results['processing']['successful_files'] == 1
    assert results['processing']['success_rate'] == 1.0

    # Check that law events were captured
    law_events = db.execute_query("""
        SELECT COUNT(*) as count
        FROM events
        WHERE event_type = 'LAW_ADOPTED'
    """)

    assert law_events['count'].iloc[0] > 10, "Should find 13 law adoptions"

    # Check that tech events were captured
    tech_events = db.execute_query("""
        SELECT COUNT(*) as count
        FROM events
        WHERE event_type = 'TECH_DISCOVERED'
    """)

    assert tech_events['count'].iloc[0] > 40, "Should find 44 tech discoveries"


def test_law_milestone_calculation(temp_db, sample_save_dir):
    """Test that law milestones are correctly calculated."""
    db = initialize_database(str(temp_db))
    process_tournament_directory(str(sample_save_dir))

    # Query law milestones
    from tournament_visualizer.data.queries import get_law_progression_by_match

    matches = db.execute_query("SELECT match_id FROM matches LIMIT 1")
    match_id = matches['match_id'].iloc[0]

    progression = get_law_progression_by_match(db, match_id)

    # Verify both players have data
    assert len(progression) == 2, "Should have data for both players"

    # Verify milestone columns exist and have reasonable values
    assert 'turn_to_4_laws' in progression.columns
    assert 'turn_to_7_laws' in progression.columns

    # At least one player should reach 4 laws
    assert progression['turn_to_4_laws'].notna().any()
```

**Run integration tests:**
```bash
uv run pytest tests/test_integration_logdata.py -v -s
```

**Commit**: `test: Add integration tests for LogData pipeline`

---

#### Task 6.2: Data Quality Validation
**Goal**: Verify imported data matches expected values

**Files to create:**
- `scripts/validate_logdata.py`

**Create validation script:**

```python
#!/usr/bin/env python3
"""Validate LogData import quality by comparing against known values."""

from tournament_visualizer.data.database import get_database
from tournament_visualizer.data.queries import get_law_progression_by_match


def validate_anarkos_becked_match():
    """Validate the anarkos vs becked match has correct law data."""
    db = get_database()

    # Find the anarkos vs becked match
    match_query = """
    SELECT m.match_id
    FROM matches m
    WHERE m.game_name LIKE '%anarkos%becked%'
    """
    matches = db.execute_query(match_query)

    if matches.empty:
        print("❌ Could not find anarkos vs becked match")
        return False

    match_id = matches['match_id'].iloc[0]

    # Get law progression
    progression = get_law_progression_by_match(db, match_id)

    # Expected values from manual analysis
    expected = {
        'anarkos': {
            'turn_to_4_laws': 54,
            'turn_to_7_laws': None,  # Never reached 7
            'total_laws': 6
        },
        'becked': {
            'turn_to_4_laws': 46,
            'turn_to_7_laws': 68,
            'total_laws': 7
        }
    }

    passed = True
    for _, row in progression.iterrows():
        player = row['player_name']
        if player not in expected:
            continue

        exp = expected[player]

        # Check turn to 4 laws
        if row['turn_to_4_laws'] != exp['turn_to_4_laws']:
            print(f"❌ {player} turn_to_4_laws: expected {exp['turn_to_4_laws']}, got {row['turn_to_4_laws']}")
            passed = False

        # Check turn to 7 laws
        if pd.isna(row['turn_to_7_laws']) and exp['turn_to_7_laws'] is not None:
            print(f"❌ {player} turn_to_7_laws: expected {exp['turn_to_7_laws']}, got None")
            passed = False
        elif not pd.isna(row['turn_to_7_laws']) and row['turn_to_7_laws'] != exp['turn_to_7_laws']:
            print(f"❌ {player} turn_to_7_laws: expected {exp['turn_to_7_laws']}, got {row['turn_to_7_laws']}")
            passed = False

        # Check total laws
        if row['total_laws'] != exp['total_laws']:
            print(f"❌ {player} total_laws: expected {exp['total_laws']}, got {row['total_laws']}")
            passed = False

        if passed:
            print(f"✅ {player} law progression validated")

    return passed


if __name__ == '__main__':
    import pandas as pd

    print("Validating LogData import quality...\n")

    if validate_anarkos_becked_match():
        print("\n✅ All validations passed!")
        exit(0)
    else:
        print("\n❌ Validation failed!")
        exit(1)
```

**Run validation:**
```bash
chmod +x scripts/validate_logdata.py
uv run python scripts/validate_logdata.py
```

**Commit**: `test: Add data quality validation script`

---

#### Task 6.3: Performance Testing
**Goal**: Ensure LogData extraction doesn't significantly slow down import

**Files to create:**
- `tests/test_performance_logdata.py`

**Create performance test:**

```python
"""Performance tests for LogData extraction."""

import pytest
import time
from pathlib import Path
from tournament_visualizer.data.parser import OldWorldSaveParser


def test_logdata_extraction_performance():
    """LogData extraction should complete in reasonable time."""
    save_file = Path("saves/match_426504721_anarkos-becked.zip")

    if not save_file.exists():
        pytest.skip("Save file not available")

    parser = OldWorldSaveParser(str(save_file))
    parser.extract_and_parse()

    # Time the extraction
    start = time.time()
    events = parser.extract_logdata_events()
    elapsed = time.time() - start

    print(f"\nExtracted {len(events)} events in {elapsed:.3f}s")

    # Should complete in under 1 second for a typical match
    assert elapsed < 1.0, f"LogData extraction too slow: {elapsed:.3f}s"

    # Should find a reasonable number of events
    assert len(events) > 50, "Should find at least 50 LogData events"


def test_full_import_performance():
    """Full import with LogData should not be significantly slower."""
    # This is a baseline - you may need to adjust thresholds
    # Run import and measure time
    import subprocess

    start = time.time()
    result = subprocess.run(
        ["uv", "run", "python", "import_tournaments.py",
         "--directory", "saves", "--dry-run"],
        capture_output=True,
        text=True
    )
    elapsed = time.time() - start

    assert result.returncode == 0, "Import should succeed"
    print(f"\nDry run completed in {elapsed:.2f}s")

    # Adjust this threshold based on your machine and data size
    assert elapsed < 10.0, "Import taking too long"
```

**Run performance tests:**
```bash
uv run pytest tests/test_performance_logdata.py -v -s
```

**Commit**: `test: Add performance tests for LogData extraction`

---

### Phase 7: Documentation & Cleanup (1-2 hours)

#### Task 7.1: Update README with New Features
**Goal**: Document the new LogData capabilities

**Files to modify:**
- `README.md`

**Add section:**

```markdown
## Data Sources

The tournament analyzer extracts data from Old World save files (`.zip` archives containing XML). Two types of historical data are captured:

### MemoryData Events
Character and diplomatic memories stored by the game AI (limited historical data):
- Character events (promotions, marriages, deaths)
- Tribal interactions
- Family events
- ~145 event types

### LogData Events (NEW)
Comprehensive turn-by-turn gameplay logs:
- **Law Adoptions**: Which laws were adopted and when (`LAW_ADOPTED`)
- **Tech Discoveries**: Complete tech tree progression (`TECH_DISCOVERED`)
- **Goal Tracking**: Ambition start/completion events
- **City Events**: Founding, production, breaches
- ~79 event types

This enables analysis of:
- Time to reach 4 laws / 7 laws
- Tech progression paths
- Tech availability at law milestones
- Comparative player progression

## Analytics Queries

### Law Progression
```python
from tournament_visualizer.data.database import get_database
from tournament_visualizer.data.queries import get_law_progression_by_match

db = get_database()
progression = get_law_progression_by_match(db, match_id=10)
# Returns: player_name, turn_to_4_laws, turn_to_7_laws, total_laws
```

### Tech Timeline
```python
from tournament_visualizer.data.queries import get_tech_timeline_by_match

timeline = get_tech_timeline_by_match(db, match_id=10)
# Returns: player_name, turn_number, tech_name, tech_sequence
```

### Techs at Law Milestone
```python
from tournament_visualizer.data.queries import get_techs_at_law_milestone

techs = get_techs_at_law_milestone(db, match_id=10, milestone=4)
# Returns: player_name, milestone_turn, tech_count, tech_list
```
```

**Commit**: `docs: Update README with LogData features and examples`

---

#### Task 7.2: Add Code Comments and Docstrings
**Goal**: Ensure all new code is well-documented

**Files to review and update:**
- `tournament_visualizer/data/parser.py`
- `tournament_visualizer/data/queries.py`
- `tournament_visualizer/data/etl.py`

**Checklist:**
- [ ] All public methods have docstrings with Args/Returns
- [ ] Complex logic has inline comments explaining "why"
- [ ] Type hints are present for all function parameters
- [ ] Edge cases are documented

**Example review comment:**
```python
def _extract_single_logdata_event(self, log_elem: ET.Element, player_id: int) -> Optional[Dict[str, Any]]:
    """Extract a single LogData event.

    LogData elements contain turn-by-turn gameplay logs. Each element has:
    - Type: Event type (LAW_ADOPTED, TECH_DISCOVERED, etc.)
    - Turn: Game turn number when event occurred
    - Data1/2/3: Event-specific data (e.g., law name, tech name)
    - Text: Human-readable description with HTML tags

    Args:
        log_elem: LogData XML element from TurnSummary
        player_id: Database player ID (1-based, not XML ID)

    Returns:
        Event dictionary with standardized structure, or None if invalid

    Note:
        Player IDs in XML are 0-based (ID="0", ID="1")
        Database player IDs are 1-based (player_id 1, 2, 3...)
        This method receives the already-converted database ID.
    """
```

**Commit**: `docs: Add comprehensive docstrings and comments`

---

#### Task 7.3: Write Developer Guide
**Goal**: Document the architecture for future developers

**Files to create:**
- `docs/developer-guide.md`

**Content outline:**
```markdown
# Developer Guide

## Architecture Overview

### Data Flow
1. Save files (`.zip`) → Parser → Events (dicts)
2. Events → ETL → DuckDB tables
3. DuckDB → Queries → Analytics DataFrames
4. DataFrames → Dash components → Web UI

### Key Components

#### Parser (`parser.py`)
- `OldWorldSaveParser`: Extracts data from XML
- `extract_events()`: MemoryData events (legacy)
- `extract_logdata_events()`: LogData events (NEW)
- `extract_players()`: Player metadata
- `extract_tech_progress()`: Final tech state

#### ETL (`etl.py`)
- `process_save_file()`: Orchestrates parsing and loading
- `initialize_database()`: Sets up schema
- Handles deduplication of events

#### Database (`database.py`)
- DuckDB embedded database
- Events table stores all historical data
- Indexes on (event_type, player_id, turn_number)

#### Queries (`queries.py`)
- `get_law_progression_by_match()`: Law milestones
- `get_tech_timeline_by_match()`: Tech progression
- `get_techs_at_law_milestone()`: Combined analysis

## Adding New Event Types

To add support for a new LogData event type:

1. **Update Parser**:
   ```python
   def _build_logdata_event_data(self, event_type, data1, data2, data3):
       if event_type == 'YOUR_NEW_TYPE' and data1:
           return {'your_field': data1}
   ```

2. **Add Description Formatting**:
   ```python
   def _format_logdata_event(self, event_type, event_data, text):
       if event_type == 'YOUR_NEW_TYPE':
           return f"Your description: {event_data['your_field']}"
   ```

3. **Write Tests**:
   ```python
   def test_extract_your_new_type():
       # Test extraction logic
   ```

4. **Add Query** (if needed):
   ```python
   def get_your_analysis(db, match_id):
       query = "SELECT ... WHERE event_type = 'YOUR_NEW_TYPE'"
   ```

## Testing Strategy

### Unit Tests
- Test individual parsing methods
- Use small XML fixtures
- Fast feedback loop

### Integration Tests
- Test full ETL pipeline
- Use temporary databases
- Verify data quality

### Performance Tests
- Ensure extraction scales
- Monitor import times
- Catch regressions

## Common Issues

### Player ID Mapping
- XML uses 0-based IDs: `<Player ID="0">`
- Database uses 1-based: `player_id = 1`
- Convert when extracting: `player_id = int(xml_id) + 1`

### Duplicate Events
- Some events appear in both MemoryData and LogData
- Deduplication key: `(turn_number, event_type, player_id)`
- Prefer LogData (more detailed)

### HTML in Text Fields
- LogData Text contains HTML tags
- Strip before storing: `re.sub(r'<[^>]+>', '', text)`
- Limit length to prevent database bloat
```

**Commit**: `docs: Add comprehensive developer guide`

---

#### Task 7.4: Clean Up and Final Review
**Goal**: Remove debug code, unused imports, ensure code quality

**Checklist:**
- [ ] Remove all `print()` debug statements
- [ ] Remove unused imports
- [ ] Run code formatter: `uv run black tournament_visualizer/`
- [ ] Run linter: `uv run ruff check tournament_visualizer/`
- [ ] Verify all tests pass: `uv run pytest -v`
- [ ] Check test coverage: `uv run pytest --cov=tournament_visualizer`

**Commit**: `refactor: Clean up code and run formatters`

---

### Phase 8: Deployment & Re-import (1 hour)

#### Task 8.1: Backup Existing Database
**Goal**: Preserve current data before re-import

```bash
# Create timestamped backup
cp tournament_data.duckdb tournament_data.duckdb.backup_before_logdata_$(date +%Y%m%d_%H%M%S)
```

**Commit**: `chore: Backup database before LogData re-import`

---

#### Task 8.2: Re-import All Data
**Goal**: Re-process all save files with LogData extraction

```bash
# Force re-import
uv run python import_tournaments.py --directory saves --force --verbose
```

**Expected output:**
- All 15 matches should import successfully
- Should see significantly more events (13 law events vs 1 per match)
- Should see tech discoveries (44 per match)

**Verify import quality:**
```bash
uv run python scripts/validate_logdata.py
```

**Commit**: `data: Re-import tournament data with LogData events`

---

#### Task 8.3: Verify Analytics Queries
**Goal**: Test new queries against full dataset

**Create verification script** (`scripts/verify_analytics.py`):

```python
#!/usr/bin/env python3
"""Verify analytics queries work on full dataset."""

from tournament_visualizer.data.database import get_database
from tournament_visualizer.data.queries import (
    get_law_progression_by_match,
    get_tech_timeline_by_match,
    get_techs_at_law_milestone
)


def main():
    db = get_database()

    # Get all matches
    matches = db.execute_query("SELECT match_id, game_name FROM matches")

    print(f"Testing analytics on {len(matches)} matches...\n")

    for _, match in matches.iterrows():
        match_id = match['match_id']
        game_name = match['game_name']

        print(f"Match {match_id}: {game_name}")

        # Test law progression
        try:
            law_prog = get_law_progression_by_match(db, match_id)
            print(f"  ✅ Law progression: {len(law_prog)} players")
        except Exception as e:
            print(f"  ❌ Law progression failed: {e}")

        # Test tech timeline
        try:
            tech_time = get_tech_timeline_by_match(db, match_id)
            print(f"  ✅ Tech timeline: {len(tech_time)} discoveries")
        except Exception as e:
            print(f"  ❌ Tech timeline failed: {e}")

        # Test techs at milestone
        try:
            techs_at_4 = get_techs_at_law_milestone(db, match_id, 4)
            print(f"  ✅ Techs at 4 laws: {len(techs_at_4)} players reached milestone")
        except Exception as e:
            print(f"  ❌ Techs at milestone failed: {e}")

        print()


if __name__ == '__main__':
    main()
```

**Run verification:**
```bash
uv run python scripts/verify_analytics.py
```

**Commit**: `test: Verify analytics queries on full dataset`

---

## Summary Checklist

Before marking this complete, verify:

### Code Quality
- [ ] All tests pass (`uv run pytest`)
- [ ] Code is formatted (`black`, `ruff`)
- [ ] No debug print statements
- [ ] Type hints on all functions
- [ ] Docstrings on all public methods

### Functionality
- [ ] LogData events are extracted
- [ ] Law adoptions tracked with turn numbers
- [ ] Tech discoveries tracked with turn numbers
- [ ] Player ID mapping is correct
- [ ] No duplicate events in database
- [ ] Events table has proper indexes

### Testing
- [ ] Unit tests for parser methods
- [ ] Integration tests for full pipeline
- [ ] Performance tests pass
- [ ] Data quality validation passes
- [ ] All matches import successfully

### Documentation
- [ ] README updated with examples
- [ ] Developer guide complete
- [ ] Code comments explain complex logic
- [ ] Migration documented (if needed)
- [ ] Analytics query examples provided

### Data
- [ ] Database backed up
- [ ] All matches re-imported
- [ ] Analytics queries work on full dataset
- [ ] Known matches validate correctly

## Estimated Timeline

- Phase 1 (Setup): 2-3 hours
- Phase 2 (TDD Setup): 2-3 hours
- Phase 3 (Implementation): 4-6 hours
- Phase 4 (Database): 1-2 hours
- Phase 5 (Analytics): 2-3 hours
- Phase 6 (Testing): 2-3 hours
- Phase 7 (Documentation): 1-2 hours
- Phase 8 (Deployment): 1 hour

**Total: 15-23 hours** (2-3 full work days)

## Success Metrics

You'll know you're done when:

1. You can answer: "How many turns did it take anarkos to reach 4 laws?" (Answer: 54)
2. You can answer: "What techs did becked have when reaching 4 laws?" (Should see specific list)
3. All 15 matches have 10+ law events (vs 0-1 currently)
4. All 15 matches have 40+ tech events (vs 0 currently)
5. Analytics queries run in < 1 second
6. A new developer can read the docs and understand the system

## Getting Help

If you get stuck:

1. **Check XML structure**: `unzip -p saves/<file.zip> | head -n 500`
2. **Check database**: `uv run duckdb tournament_data.duckdb -readonly`
3. **Run validation**: `uv run python scripts/validate_logdata.py`
4. **Check test output**: `uv run pytest -v -s`
5. **Review this plan's examples**: All code samples should work as-is

Good luck! Remember: TDD, frequent commits, and DRY. 🚀
