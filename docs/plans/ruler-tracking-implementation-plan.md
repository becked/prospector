# Ruler Tracking Implementation Plan

## Overview

Add a new `rulers` table to track all rulers (leaders) for each player throughout a match, including their archetype and starting trait chosen at game initialization. This enables analytics on ruler succession, archetype effectiveness, and trait correlations with performance.

## Background

### Old World Game Mechanics

In Old World, players start by choosing:
1. **Nation** (e.g., Persia, Greece, Rome)
2. **Starting Ruler** with:
   - **Archetype**: One of 4 types (Scholar, Tactician, Commander, Schemer)
   - **Starting Trait**: One initial trait (e.g., Educated, Brave, Intelligent)

During gameplay, rulers can:
- Gain additional traits through events
- Die or abdicate
- Be succeeded by heirs

Each player may have multiple rulers throughout a game.

### Data Source

Old World save files (`.zip` containing `.xml`) store:
- **Player/Leaders element**: List of character IDs in succession order
- **Character elements**: Individual character data including:
  - `FirstName` attribute: Ruler's name (e.g., `NAME_YAZDEGERD`)
  - `TraitTurn` child element: Traits mapped to turn acquired
    - Archetype trait: Tagged with `_ARCHETYPE` suffix (e.g., `TRAIT_SCHOLAR_ARCHETYPE`)
    - Regular traits: Each has text content = turn number when acquired
    - Turn 1 traits = initial choices at game start

### XML Structure Example

```xml
<Player ID="0" OnlineID="123" Name="anarkos" Nation="NATION_PERSIA">
  <Leaders>
    <ID>9</ID>   <!-- First ruler (starting) -->
    <ID>20</ID>  <!-- Second ruler (successor) -->
    <ID>64</ID>  <!-- Third ruler (successor) -->
  </Leaders>
  <!-- other player data -->
</Player>

<Character ID="9" FirstName="NAME_YAZDEGERD" BirthTurn="-17">
  <TraitTurn>
    <TRAIT_SCHEMER_ARCHETYPE>1</TRAIT_SCHEMER_ARCHETYPE>  <!-- Archetype chosen at start -->
    <TRAIT_EDUCATED>1</TRAIT_EDUCATED>                     <!-- Starting trait chosen at start -->
    <TRAIT_BESIEGER>15</TRAIT_BESIEGER>                    <!-- Gained later during gameplay -->
    <TRAIT_BRAVE>18</TRAIT_BRAVE>                          <!-- Gained later during gameplay -->
  </TraitTurn>
  <!-- other character data -->
</Character>
```

### Existing Event Data

The database already tracks `CHARACTER_SUCCESSION` events in the `events` table from LogData. These events contain:
- Turn number when succession occurred
- Character ID (in `Data1` field)
- Ruler name (in description text)

However, these events:
- Don't include archetype/trait information
- Don't exist for the starting ruler (who begins at turn 1)
- Are stored as unstructured text descriptions

The new `rulers` table will provide structured, complete ruler data.

### Why a Separate Table?

Following database normalization principles:
1. **Distinct Entity**: Rulers are a separate concept from players (1-to-many relationship)
2. **Reduced Redundancy**: Don't duplicate character data in the `players` table
3. **Query Efficiency**: Direct queries like "how many rulers did this player have?"
4. **Analytics**: Enable ruler-specific analysis (archetype win rates, succession patterns)

## Database Schema

### New Table: `rulers`

```sql
CREATE TABLE rulers (
    ruler_id INTEGER PRIMARY KEY,
    match_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,
    character_id INTEGER NOT NULL,
    ruler_name VARCHAR,
    archetype VARCHAR,
    starting_trait VARCHAR,
    succession_order INTEGER NOT NULL,
    succession_turn INTEGER NOT NULL,
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id)
);
```

### Field Descriptions

- **ruler_id**: Auto-incrementing primary key
- **match_id**: Reference to the match (for joining with match data)
- **player_id**: Reference to the player (1-based, same as `players` table)
- **character_id**: Character ID from XML (for joining with events if needed)
- **ruler_name**: Formatted ruler name (e.g., "Yazdegerd" not "NAME_YAZDEGERD")
- **archetype**: Ruler archetype (e.g., "Schemer", "Scholar", "Tactician", "Commander")
- **starting_trait**: Initial trait chosen at game start (e.g., "Educated", "Brave")
- **succession_order**: 0 for starting ruler, 1 for first successor, 2 for second, etc.
- **succession_turn**: Turn when ruler took power (1 for starting ruler)

### Example Data

```
ruler_id | match_id | player_id | character_id | ruler_name    | archetype | starting_trait | succession_order | succession_turn
---------|----------|-----------|--------------|---------------|-----------|----------------|------------------|----------------
1        | 100      | 1         | 9            | Yazdegerd     | Schemer   | Educated       | 0                | 1
2        | 100      | 1         | 20           | Shapur        | Tactician | Affable        | 1                | 47
3        | 100      | 1         | 64           | Mithridates   | Tactician | Intelligent    | 2                | 65
4        | 100      | 2         | 5            | Naqia         | Schemer   | Intelligent    | 0                | 1
5        | 100      | 2         | 43           | Tiglath       | Tactician | Tough          | 1                | 52
```

## Implementation Tasks

### Task 1: Create Database Migration

**Objective**: Define the schema change in a migration document.

**Files to Create**:
- `docs/migrations/003_add_rulers_table.md`

**Migration Document Template**:

```markdown
# Migration 003: Add Rulers Table

## Overview
Adds a new `rulers` table to track all rulers for each player throughout a match, including archetype and starting trait information.

## Schema Changes

### New Table: `rulers`

```sql
CREATE TABLE rulers (
    ruler_id INTEGER PRIMARY KEY,
    match_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,
    character_id INTEGER NOT NULL,
    ruler_name VARCHAR,
    archetype VARCHAR,
    starting_trait VARCHAR,
    succession_order INTEGER NOT NULL,
    succession_turn INTEGER NOT NULL,
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id)
);
```

## SQL Migration Script

```sql
-- Create the rulers table
CREATE TABLE IF NOT EXISTS rulers (
    ruler_id INTEGER PRIMARY KEY,
    match_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,
    character_id INTEGER NOT NULL,
    ruler_name VARCHAR,
    archetype VARCHAR,
    starting_trait VARCHAR,
    succession_order INTEGER NOT NULL,
    succession_turn INTEGER NOT NULL,
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id)
);

-- Record migration
INSERT INTO schema_migrations (version, description, applied_at)
VALUES (3, 'Add rulers table', CURRENT_TIMESTAMP);
```

## Rollback Procedure

```sql
-- Drop the table
DROP TABLE IF EXISTS rulers;

-- Remove migration record
DELETE FROM schema_migrations WHERE version = 3;
```

## Verification

After applying migration:

```sql
-- Verify table exists
SELECT name FROM sqlite_master WHERE type='table' AND name='rulers';

-- Verify schema
PRAGMA table_info(rulers);

-- Verify migration recorded
SELECT * FROM schema_migrations WHERE version = 3;
```

## Related Files
- Parser: `tournament_visualizer/data/parser.py` (will need `extract_rulers()` method)
- Database: `tournament_visualizer/data/database.py` (will need `insert_rulers()` method)
- ETL: `tournament_visualizer/data/etl.py` (will need to call extraction and insertion)

## Data Population
After migration, re-import all save files to populate the rulers table:
```bash
uv run python scripts/import_attachments.py --directory saves --force --verbose
```
```

**Testing**:
1. Read the migration document to ensure completeness
2. Verify SQL syntax is valid (copy-paste into DuckDB to test)

**Commit Message**:
```
docs: Add migration plan for rulers table

Documents schema changes, rollback procedure, and verification steps
for adding the rulers table to track ruler succession and archetype data.
```

---

### Task 2: Update Database Schema Initialization

**Objective**: Add the `rulers` table creation to the database initialization code.

**Files to Modify**:
- `tournament_visualizer/data/database.py`

**Location**: Find the `initialize_database()` or `create_tables()` method (around line 50-200 depending on current structure).

**Code Changes**:

Look for the section with `CREATE TABLE` statements. Add the rulers table after the `players` table definition:

```python
# In the create_tables() method or similar:

# Existing players table creation...
conn.execute("""
    CREATE TABLE IF NOT EXISTS players (
        player_id BIGINT PRIMARY KEY,
        match_id BIGINT,
        player_name VARCHAR NOT NULL,
        ...
    )
""")

# ADD THIS: Create rulers table
conn.execute("""
    CREATE TABLE IF NOT EXISTS rulers (
        ruler_id INTEGER PRIMARY KEY,
        match_id BIGINT NOT NULL,
        player_id BIGINT NOT NULL,
        character_id INTEGER NOT NULL,
        ruler_name VARCHAR,
        archetype VARCHAR,
        starting_trait VARCHAR,
        succession_order INTEGER NOT NULL,
        succession_turn INTEGER NOT NULL,
        FOREIGN KEY (match_id) REFERENCES matches(match_id),
        FOREIGN KEY (player_id) REFERENCES players(player_id)
    )
""")

# Continue with other tables...
```

**Testing**:
```bash
# Remove existing database
rm data/tournament_data.duckdb

# Run database initialization
uv run python -c "from tournament_visualizer.data.database import TournamentDatabase; db = TournamentDatabase(); db.close()"

# Verify table was created
uv run duckdb data/tournament_data.duckdb -readonly -c "DESCRIBE rulers"

# Should output the table schema with all columns
```

**Commit Message**:
```
feat: Add rulers table to database schema

Adds rulers table creation in database initialization to track
ruler succession, archetypes, and starting traits for each player.
```

---

### Task 3: Add Parser Method to Extract Rulers

**Objective**: Add a method to `OldWorldSaveParser` to extract ruler data from save files.

**Files to Modify**:
- `tournament_visualizer/data/parser.py`

**Reference Code**: Look at existing extraction methods like `extract_players()` (around line 218) or `extract_points_history()` (around line 1259) for patterns.

**Add New Method** (suggested location: after `extract_opinion_histories()`, around line 1588):

```python
def extract_rulers(self) -> List[Dict[str, Any]]:
    """Extract ruler succession data from Player/Leaders elements.

    Parses the complete ruler succession for each player, including archetype
    and starting trait information. The Leaders element contains character IDs
    in chronological order of succession.

    Each ruler's archetype and starting trait are determined by examining their
    Character element's TraitTurn data:
    - Traits with turn_acquired=1 are initial choices at game start
    - One trait will have '_ARCHETYPE' suffix (Scholar, Tactician, Commander, Schemer)
    - One trait will be a regular trait (Educated, Brave, Intelligent, etc.)

    Note on Player IDs:
        XML uses 0-based player IDs (ID="0", ID="1", etc.)
        Database uses 1-based player IDs (player_id=1, player_id=2, etc.)
        Conversion: database_player_id = xml_id + 1

    Returns:
        List of ruler dictionaries with keys:
            - player_id: Database player ID (1-based)
            - character_id: Character ID from XML
            - ruler_name: Formatted ruler name (e.g., "Yazdegerd")
            - archetype: Ruler archetype (e.g., "Schemer", "Scholar")
            - starting_trait: Initial trait chosen (e.g., "Educated")
            - succession_order: 0 for starting ruler, 1+ for successors
            - succession_turn: Turn when ruler took power

    Raises:
        ValueError: If XML not parsed yet (call extract_and_parse() first)
    """
    if self.root is None:
        raise ValueError("XML not parsed. Call extract_and_parse() first.")

    rulers = []

    # Find all player elements with OnlineID (human players only)
    player_elements = self.root.findall(".//Player[@OnlineID]")

    for player_elem in player_elements:
        # Get player's XML ID (0-based)
        player_xml_id = player_elem.get("ID")
        if player_xml_id is None:
            continue

        # Convert to 1-based database player ID
        player_id = int(player_xml_id) + 1

        # Find Leaders element containing succession order
        leaders_elem = player_elem.find("Leaders")
        if leaders_elem is None:
            logger.warning(f"No Leaders element found for player {player_id}")
            continue

        # Extract all leader character IDs in succession order
        leader_id_elements = leaders_elem.findall("ID")

        for succession_order, leader_id_elem in enumerate(leader_id_elements):
            character_id_str = leader_id_elem.text
            if not character_id_str:
                continue

            character_id = self._safe_int(character_id_str)
            if character_id is None:
                continue

            # Look up character data
            char_elem = self.root.find(f".//Character[@ID='{character_id}']")
            if char_elem is None:
                logger.warning(
                    f"Character {character_id} not found for player {player_id}"
                )
                continue

            # Extract ruler name
            first_name = char_elem.get("FirstName")
            ruler_name = self._format_context_value(first_name) if first_name else None

            # Extract archetype and starting trait from TraitTurn
            archetype = None
            starting_trait = None

            trait_turn_elem = char_elem.find(".//TraitTurn")
            if trait_turn_elem is not None:
                for trait_elem in trait_turn_elem:
                    trait_name = trait_elem.tag
                    turn_acquired_str = trait_elem.text
                    turn_acquired = self._safe_int(turn_acquired_str)

                    # Only process turn 1 traits (initial choices)
                    if turn_acquired != 1:
                        continue

                    # Check if this is an archetype trait
                    if "_ARCHETYPE" in trait_name:
                        # Remove TRAIT_ prefix and _ARCHETYPE suffix
                        archetype = (
                            trait_name.replace("TRAIT_", "")
                            .replace("_ARCHETYPE", "")
                            .replace("_", " ")
                            .title()
                        )
                    else:
                        # This is the starting trait
                        starting_trait = (
                            trait_name.replace("TRAIT_", "")
                            .replace("_", " ")
                            .title()
                        )

            # Determine succession turn
            # For starting ruler (succession_order=0), always turn 1
            # For successors, look for CHARACTER_SUCCESSION event
            if succession_order == 0:
                succession_turn = 1
            else:
                # Find the CHARACTER_SUCCESSION event for this character
                succession_turn = self._find_succession_turn(
                    player_elem, character_id
                )
                if succession_turn is None:
                    # Fallback: estimate based on order
                    logger.warning(
                        f"No succession event found for character {character_id}"
                    )
                    succession_turn = 1  # Default fallback

            ruler_data = {
                "player_id": player_id,
                "character_id": character_id,
                "ruler_name": ruler_name,
                "archetype": archetype,
                "starting_trait": starting_trait,
                "succession_order": succession_order,
                "succession_turn": succession_turn,
            }

            rulers.append(ruler_data)

    return rulers


def _find_succession_turn(
    self, player_elem: ET.Element, character_id: int
) -> Optional[int]:
    """Find the turn when a character became ruler from succession events.

    Searches through the player's PermanentLogList for CHARACTER_SUCCESSION
    events that match the given character ID.

    Args:
        player_elem: Player XML element
        character_id: Character ID to search for

    Returns:
        Turn number when succession occurred, or None if not found
    """
    perm_log_list = player_elem.find(".//PermanentLogList")
    if perm_log_list is None:
        return None

    # Search for CHARACTER_SUCCESSION events
    for log_elem in perm_log_list.findall(".//LogData"):
        type_elem = log_elem.find("Type")
        if type_elem is None or type_elem.text != "CHARACTER_SUCCESSION":
            continue

        # Check if Data1 contains our character ID
        data1_elem = log_elem.find("Data1")
        if data1_elem is None:
            continue

        event_char_id = self._safe_int(data1_elem.text)
        if event_char_id == character_id:
            # Found the succession event, extract turn
            turn_elem = log_elem.find("Turn")
            if turn_elem is not None:
                return self._safe_int(turn_elem.text)

    return None
```

**Key Implementation Notes**:
1. **DRY**: Reuse existing helper methods (`_safe_int()`, `_format_context_value()`)
2. **Player ID mapping**: XML uses 0-based (ID="0"), database uses 1-based (player_id=1)
3. **Trait filtering**: Only examine traits where `turn_acquired == 1` (initial choices)
4. **Error handling**: Log warnings but continue processing if data is missing
5. **Succession turn**: Use turn 1 for starting ruler, look up events for successors

**Testing** (create test file after implementation):
```bash
# Create test file: tests/test_parser_rulers.py
# Run parser tests (will create in Task 4)
uv run pytest tests/test_parser_rulers.py -v
```

**Commit Message**:
```
feat: Add extract_rulers() method to parser

Extracts ruler succession data from save files including archetype,
starting trait, and succession order. Handles both starting rulers
and successors with proper turn tracking.
```

---

### Task 4: Write Tests for Parser Method

**Objective**: Create comprehensive tests for the `extract_rulers()` method following TDD principles.

**Files to Create**:
- `tests/test_parser_rulers.py`

**Test File Template**:

```python
"""Tests for ruler extraction from Old World save files."""

import pytest
from tournament_visualizer.data.parser import OldWorldSaveParser


class TestExtractRulers:
    """Tests for the extract_rulers() method."""

    def test_extract_rulers_requires_parsed_xml(self):
        """Test that extract_rulers() raises ValueError if XML not parsed."""
        parser = OldWorldSaveParser("dummy.zip")

        with pytest.raises(ValueError, match="XML not parsed"):
            parser.extract_rulers()

    def test_extract_rulers_basic_structure(self):
        """Test that extract_rulers() returns expected structure."""
        # Use a known save file from the saves/ directory
        parser = OldWorldSaveParser("saves/match_426504721_anarkos-becked.zip")
        parser.extract_and_parse()

        rulers = parser.extract_rulers()

        # Should have rulers for both players
        assert len(rulers) > 0

        # Verify structure of first ruler
        ruler = rulers[0]
        assert "player_id" in ruler
        assert "character_id" in ruler
        assert "ruler_name" in ruler
        assert "archetype" in ruler
        assert "starting_trait" in ruler
        assert "succession_order" in ruler
        assert "succession_turn" in ruler

    def test_extract_rulers_player_id_mapping(self):
        """Test that player IDs are correctly converted from 0-based to 1-based."""
        parser = OldWorldSaveParser("saves/match_426504721_anarkos-becked.zip")
        parser.extract_and_parse()

        rulers = parser.extract_rulers()

        # Player IDs should be 1 and 2 (1-based), not 0 and 1 (0-based XML)
        player_ids = {r["player_id"] for r in rulers}
        assert 1 in player_ids
        assert 2 in player_ids
        assert 0 not in player_ids  # Should not have 0-based IDs

    def test_extract_rulers_starting_ruler_is_turn_1(self):
        """Test that starting rulers (succession_order=0) have succession_turn=1."""
        parser = OldWorldSaveParser("saves/match_426504721_anarkos-becked.zip")
        parser.extract_and_parse()

        rulers = parser.extract_rulers()

        # Find all starting rulers
        starting_rulers = [r for r in rulers if r["succession_order"] == 0]

        assert len(starting_rulers) > 0

        # All starting rulers should have succession_turn = 1
        for ruler in starting_rulers:
            assert ruler["succession_turn"] == 1, (
                f"Starting ruler {ruler['ruler_name']} should have "
                f"succession_turn=1, got {ruler['succession_turn']}"
            )

    def test_extract_rulers_archetype_format(self):
        """Test that archetypes are properly formatted."""
        parser = OldWorldSaveParser("saves/match_426504721_anarkos-becked.zip")
        parser.extract_and_parse()

        rulers = parser.extract_rulers()

        # Get archetypes (filter out None values)
        archetypes = {r["archetype"] for r in rulers if r["archetype"]}

        # Should have readable archetypes (not raw XML constants)
        valid_archetypes = {"Scholar", "Tactician", "Commander", "Schemer"}

        for archetype in archetypes:
            assert archetype in valid_archetypes, (
                f"Invalid archetype: {archetype}. "
                f"Expected one of {valid_archetypes}"
            )

            # Should not contain underscores or TRAIT_ prefix
            assert "_" not in archetype
            assert "TRAIT" not in archetype

    def test_extract_rulers_trait_format(self):
        """Test that starting traits are properly formatted."""
        parser = OldWorldSaveParser("saves/match_426504721_anarkos-becked.zip")
        parser.extract_and_parse()

        rulers = parser.extract_rulers()

        # Get starting traits (filter out None values)
        traits = {r["starting_trait"] for r in rulers if r["starting_trait"]}

        assert len(traits) > 0

        for trait in traits:
            # Should be title case
            assert trait[0].isupper(), f"Trait should be title case: {trait}"

            # Should not contain raw XML prefixes
            assert "TRAIT_" not in trait

            # Multi-word traits should have spaces
            if len(trait.split()) > 1:
                assert " " in trait

    def test_extract_rulers_ruler_name_format(self):
        """Test that ruler names are properly formatted."""
        parser = OldWorldSaveParser("saves/match_426504721_anarkos-becked.zip")
        parser.extract_and_parse()

        rulers = parser.extract_rulers()

        # Get ruler names (filter out None values)
        names = {r["ruler_name"] for r in rulers if r["ruler_name"]}

        assert len(names) > 0

        for name in names:
            # Should not contain NAME_ prefix
            assert "NAME_" not in name, f"Name should not have NAME_ prefix: {name}"

            # Should be title case
            assert name[0].isupper(), f"Name should be title case: {name}"

    def test_extract_rulers_succession_order_is_sequential(self):
        """Test that succession_order values are sequential for each player."""
        parser = OldWorldSaveParser("saves/match_426504721_anarkos-becked.zip")
        parser.extract_and_parse()

        rulers = parser.extract_rulers()

        # Group by player_id
        players = {}
        for ruler in rulers:
            player_id = ruler["player_id"]
            if player_id not in players:
                players[player_id] = []
            players[player_id].append(ruler)

        # Check each player's succession order
        for player_id, player_rulers in players.items():
            # Sort by succession_order
            player_rulers.sort(key=lambda r: r["succession_order"])

            # Verify sequential: 0, 1, 2, ...
            for i, ruler in enumerate(player_rulers):
                assert ruler["succession_order"] == i, (
                    f"Player {player_id} should have sequential succession_order. "
                    f"Expected {i}, got {ruler['succession_order']}"
                )

    def test_extract_rulers_successor_turn_greater_than_1(self):
        """Test that successor rulers (order > 0) have succession_turn > 1."""
        parser = OldWorldSaveParser("saves/match_426504721_anarkos-becked.zip")
        parser.extract_and_parse()

        rulers = parser.extract_rulers()

        # Find all successor rulers
        successors = [r for r in rulers if r["succession_order"] > 0]

        if len(successors) > 0:  # Only test if there are successors
            for ruler in successors:
                assert ruler["succession_turn"] > 1, (
                    f"Successor ruler {ruler['ruler_name']} (order "
                    f"{ruler['succession_order']}) should have succession_turn > 1, "
                    f"got {ruler['succession_turn']}"
                )

    def test_extract_rulers_with_multiple_saves(self):
        """Test extraction works across different save files."""
        import os
        from pathlib import Path

        saves_dir = Path("saves")
        save_files = list(saves_dir.glob("match_*.zip"))[:3]  # Test first 3 files

        for save_file in save_files:
            parser = OldWorldSaveParser(str(save_file))

            try:
                parser.extract_and_parse()
                rulers = parser.extract_rulers()

                # Should have at least 2 rulers (one per player minimum)
                assert len(rulers) >= 2, (
                    f"Save {save_file.name} should have at least 2 rulers"
                )

                # All rulers should have required fields
                for ruler in rulers:
                    assert ruler["player_id"] > 0
                    assert ruler["character_id"] >= 0
                    assert ruler["succession_order"] >= 0
                    assert ruler["succession_turn"] >= 1

            except Exception as e:
                pytest.fail(f"Failed to process {save_file.name}: {e}")


class TestFindSuccessionTurn:
    """Tests for the _find_succession_turn() helper method."""

    def test_find_succession_turn_basic(self):
        """Test that succession turn is found for successor rulers."""
        parser = OldWorldSaveParser("saves/match_426504721_anarkos-becked.zip")
        parser.extract_and_parse()

        rulers = parser.extract_rulers()

        # Find a successor ruler (succession_order > 0)
        successor = next(
            (r for r in rulers if r["succession_order"] > 0),
            None
        )

        if successor:
            # Should have a valid succession turn
            assert successor["succession_turn"] is not None
            assert successor["succession_turn"] > 1
```

**Testing Strategy**:

1. **Run tests before implementation** (TDD):
   ```bash
   uv run pytest tests/test_parser_rulers.py -v
   # Should fail - that's expected!
   ```

2. **After implementing parser method** (Task 3):
   ```bash
   uv run pytest tests/test_parser_rulers.py -v
   # Should pass
   ```

3. **Check coverage**:
   ```bash
   uv run pytest tests/test_parser_rulers.py --cov=tournament_visualizer.data.parser --cov-report=term-missing
   ```

**What These Tests Verify**:
- Correct data structure returned
- Player ID conversion (0-based → 1-based)
- Starting rulers always at turn 1
- Proper formatting of archetypes, traits, names
- Sequential succession order
- Successor turns are after turn 1
- Works across multiple save files
- Error handling for unparsed XML

**Commit Message**:
```
test: Add comprehensive tests for ruler extraction

Tests verify correct parsing of ruler data including archetype, traits,
succession order, and turn tracking. Covers edge cases and formatting.
```

---

### Task 5: Add Database Insert Method

**Objective**: Add a method to `TournamentDatabase` to insert ruler data.

**Files to Modify**:
- `tournament_visualizer/data/database.py`

**Reference Code**: Look at existing insert methods like `insert_players()` or `insert_events()` for patterns.

**Add New Method** (suggested location: after `insert_players()` method):

```python
def insert_rulers(self, match_id: int, rulers: List[Dict[str, Any]]) -> None:
    """Insert ruler data for a match.

    Args:
        match_id: The match ID to associate rulers with
        rulers: List of ruler dictionaries from parser.extract_rulers()

    Raises:
        ValueError: If match_id is invalid or rulers data is malformed
    """
    if not rulers:
        logger.debug(f"No rulers to insert for match {match_id}")
        return

    logger.info(f"Inserting {len(rulers)} rulers for match {match_id}")

    try:
        # Prepare data for batch insert
        insert_data = []

        for ruler in rulers:
            # Validate required fields
            if "player_id" not in ruler or "character_id" not in ruler:
                logger.warning(f"Skipping ruler with missing required fields: {ruler}")
                continue

            # Build insert tuple
            insert_data.append({
                "match_id": match_id,
                "player_id": ruler["player_id"],
                "character_id": ruler["character_id"],
                "ruler_name": ruler.get("ruler_name"),
                "archetype": ruler.get("archetype"),
                "starting_trait": ruler.get("starting_trait"),
                "succession_order": ruler.get("succession_order", 0),
                "succession_turn": ruler.get("succession_turn", 1),
            })

        if not insert_data:
            logger.warning(f"No valid rulers to insert for match {match_id}")
            return

        # Batch insert using DuckDB's efficient bulk insert
        self.conn.executemany(
            """
            INSERT INTO rulers (
                match_id, player_id, character_id, ruler_name,
                archetype, starting_trait, succession_order, succession_turn
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            [
                (
                    d["match_id"],
                    d["player_id"],
                    d["character_id"],
                    d["ruler_name"],
                    d["archetype"],
                    d["starting_trait"],
                    d["succession_order"],
                    d["succession_turn"],
                )
                for d in insert_data
            ],
        )

        logger.info(f"Successfully inserted {len(insert_data)} rulers for match {match_id}")

    except Exception as e:
        logger.error(f"Error inserting rulers for match {match_id}: {e}")
        raise
```

**Key Implementation Notes**:
1. **DRY**: Follow same pattern as other insert methods
2. **Validation**: Check required fields before inserting
3. **Batch insert**: Use `executemany()` for efficiency
4. **Error handling**: Log warnings for bad data, raise on database errors
5. **Logging**: Info for success, warning for skipped data, error for failures

**Testing** (manual verification before unit tests):
```bash
# Test database insert manually
uv run python -c "
from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.parser import OldWorldSaveParser

# Parse a save file
parser = OldWorldSaveParser('saves/match_426504721_anarkos-becked.zip')
parser.extract_and_parse()
rulers = parser.extract_rulers()

# Insert to database
db = TournamentDatabase()
db.insert_rulers(match_id=999, rulers=rulers)
db.close()

print(f'Inserted {len(rulers)} rulers')
"

# Verify data was inserted
uv run duckdb data/tournament_data.duckdb -readonly -c "SELECT * FROM rulers WHERE match_id = 999"
```

**Commit Message**:
```
feat: Add insert_rulers() method to database

Implements batch insertion of ruler data with validation and error
handling. Uses executemany() for efficient bulk inserts.
```

---

### Task 6: Write Tests for Database Insert Method

**Objective**: Create tests for the `insert_rulers()` method.

**Files to Create/Modify**:
- `tests/test_database_rulers.py` (create new file)

**Test File Template**:

```python
"""Tests for ruler database operations."""

import pytest
from pathlib import Path
from tournament_visualizer.data.database import TournamentDatabase


@pytest.fixture
def test_db(tmp_path):
    """Create a temporary test database."""
    db_path = tmp_path / "test.duckdb"
    db = TournamentDatabase(str(db_path))
    yield db
    db.close()


class TestInsertRulers:
    """Tests for insert_rulers() method."""

    def test_insert_rulers_basic(self, test_db):
        """Test basic ruler insertion."""
        rulers = [
            {
                "player_id": 1,
                "character_id": 9,
                "ruler_name": "Yazdegerd",
                "archetype": "Schemer",
                "starting_trait": "Educated",
                "succession_order": 0,
                "succession_turn": 1,
            },
            {
                "player_id": 1,
                "character_id": 20,
                "ruler_name": "Shapur",
                "archetype": "Tactician",
                "starting_trait": "Affable",
                "succession_order": 1,
                "succession_turn": 47,
            },
        ]

        test_db.insert_rulers(match_id=100, rulers=rulers)

        # Verify insertion
        result = test_db.conn.execute(
            "SELECT COUNT(*) FROM rulers WHERE match_id = 100"
        ).fetchone()

        assert result[0] == 2

    def test_insert_rulers_empty_list(self, test_db):
        """Test that empty ruler list is handled gracefully."""
        test_db.insert_rulers(match_id=100, rulers=[])

        # Should not raise error
        result = test_db.conn.execute(
            "SELECT COUNT(*) FROM rulers WHERE match_id = 100"
        ).fetchone()

        assert result[0] == 0

    def test_insert_rulers_validates_required_fields(self, test_db):
        """Test that rulers with missing required fields are skipped."""
        rulers = [
            {
                # Missing player_id - should be skipped
                "character_id": 9,
                "ruler_name": "Yazdegerd",
                "archetype": "Schemer",
                "starting_trait": "Educated",
                "succession_order": 0,
                "succession_turn": 1,
            },
            {
                # Valid ruler - should be inserted
                "player_id": 1,
                "character_id": 20,
                "ruler_name": "Shapur",
                "archetype": "Tactician",
                "starting_trait": "Affable",
                "succession_order": 1,
                "succession_turn": 47,
            },
        ]

        test_db.insert_rulers(match_id=100, rulers=rulers)

        # Only the valid ruler should be inserted
        result = test_db.conn.execute(
            "SELECT COUNT(*) FROM rulers WHERE match_id = 100"
        ).fetchone()

        assert result[0] == 1

    def test_insert_rulers_handles_null_optional_fields(self, test_db):
        """Test that null values in optional fields are handled correctly."""
        rulers = [
            {
                "player_id": 1,
                "character_id": 9,
                "ruler_name": None,  # Optional
                "archetype": None,  # Optional
                "starting_trait": None,  # Optional
                "succession_order": 0,
                "succession_turn": 1,
            },
        ]

        test_db.insert_rulers(match_id=100, rulers=rulers)

        # Should insert successfully
        result = test_db.conn.execute(
            "SELECT * FROM rulers WHERE match_id = 100"
        ).fetchone()

        assert result is not None
        # Verify nulls are preserved
        assert result[4] is None  # ruler_name
        assert result[5] is None  # archetype
        assert result[6] is None  # starting_trait

    def test_insert_rulers_multiple_matches(self, test_db):
        """Test inserting rulers for multiple matches."""
        rulers_match1 = [
            {
                "player_id": 1,
                "character_id": 9,
                "ruler_name": "Yazdegerd",
                "archetype": "Schemer",
                "starting_trait": "Educated",
                "succession_order": 0,
                "succession_turn": 1,
            },
        ]

        rulers_match2 = [
            {
                "player_id": 1,
                "character_id": 5,
                "ruler_name": "Naqia",
                "archetype": "Scholar",
                "starting_trait": "Intelligent",
                "succession_order": 0,
                "succession_turn": 1,
            },
        ]

        test_db.insert_rulers(match_id=100, rulers=rulers_match1)
        test_db.insert_rulers(match_id=101, rulers=rulers_match2)

        # Verify both matches have rulers
        result1 = test_db.conn.execute(
            "SELECT COUNT(*) FROM rulers WHERE match_id = 100"
        ).fetchone()
        result2 = test_db.conn.execute(
            "SELECT COUNT(*) FROM rulers WHERE match_id = 101"
        ).fetchone()

        assert result1[0] == 1
        assert result2[0] == 1

    def test_insert_rulers_preserves_succession_order(self, test_db):
        """Test that succession_order is correctly preserved."""
        rulers = [
            {
                "player_id": 1,
                "character_id": 9,
                "ruler_name": "First",
                "archetype": "Schemer",
                "starting_trait": "Educated",
                "succession_order": 0,
                "succession_turn": 1,
            },
            {
                "player_id": 1,
                "character_id": 20,
                "ruler_name": "Second",
                "archetype": "Tactician",
                "starting_trait": "Brave",
                "succession_order": 1,
                "succession_turn": 30,
            },
            {
                "player_id": 1,
                "character_id": 64,
                "ruler_name": "Third",
                "archetype": "Commander",
                "starting_trait": "Tough",
                "succession_order": 2,
                "succession_turn": 60,
            },
        ]

        test_db.insert_rulers(match_id=100, rulers=rulers)

        # Query in succession order
        results = test_db.conn.execute(
            """
            SELECT ruler_name, succession_order, succession_turn
            FROM rulers
            WHERE match_id = 100
            ORDER BY succession_order
            """
        ).fetchall()

        assert len(results) == 3
        assert results[0][0] == "First"
        assert results[0][1] == 0
        assert results[0][2] == 1
        assert results[1][0] == "Second"
        assert results[1][1] == 1
        assert results[1][2] == 30
        assert results[2][0] == "Third"
        assert results[2][1] == 2
        assert results[2][2] == 60
```

**Testing**:
```bash
# Run the tests
uv run pytest tests/test_database_rulers.py -v

# Check coverage
uv run pytest tests/test_database_rulers.py --cov=tournament_visualizer.data.database --cov-report=term-missing
```

**Commit Message**:
```
test: Add tests for ruler database insertion

Tests verify correct insertion, validation of required fields,
handling of null values, and preservation of succession order.
```

---

### Task 7: Integrate Ruler Extraction into ETL Pipeline

**Objective**: Add ruler extraction and insertion to the ETL (Extract-Transform-Load) process.

**Files to Modify**:
- `tournament_visualizer/data/etl.py`

**Location**: Find the `process_tournament_file()` function (around line 50-150).

**Code Changes**:

Look for the section where other data is extracted and inserted. Add ruler processing after player insertion:

```python
def process_tournament_file(file_path: str, db: TournamentDatabase) -> bool:
    """Process a single tournament file and load into database.

    Args:
        file_path: Path to tournament save file
        db: Database instance

    Returns:
        True if successful, False otherwise
    """
    try:
        # ... existing code for parsing ...

        parser = OldWorldSaveParser(file_path)
        parser.extract_and_parse()

        # ... existing extraction code ...
        match_metadata = parser.extract_basic_metadata()
        players = parser.extract_players()
        # ... other extractions ...

        # ADD THIS: Extract rulers
        rulers = parser.extract_rulers()

        # ... existing database insertion code ...

        # Insert basic data first
        match_id = db.insert_match(match_metadata)
        db.insert_players(match_id, players)

        # ADD THIS: Insert rulers after players
        db.insert_rulers(match_id, rulers)

        # ... rest of insertion code ...
        db.insert_events(match_id, events)
        # etc.

        logger.info(f"Successfully processed {file_path}")
        return True

    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        return False
```

**Key Points**:
1. **Order matters**: Insert rulers AFTER players (foreign key dependency)
2. **Extract before insert**: Call `extract_rulers()` with other extraction calls
3. **Error handling**: Errors are caught by existing try/except
4. **Logging**: Existing logging will track success/failure

**Testing** (manual verification):
```bash
# Test with a single file
uv run python -c "
from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.etl import process_tournament_file

db = TournamentDatabase('data/test_etl.duckdb')
success = process_tournament_file('saves/match_426504721_anarkos-becked.zip', db)
print(f'Success: {success}')

# Check rulers were inserted
result = db.conn.execute('SELECT COUNT(*) FROM rulers').fetchone()
print(f'Rulers inserted: {result[0]}')

db.close()
"

# Clean up test database
rm data/test_etl.duckdb
```

**Commit Message**:
```
feat: Integrate ruler extraction into ETL pipeline

Adds ruler extraction and insertion to the tournament file processing
workflow. Rulers are inserted after players to maintain foreign keys.
```

---

### Task 8: Update ETL Summary to Include Rulers

**Objective**: Add ruler counts to the ETL summary statistics.

**Files to Modify**:
- `tournament_visualizer/data/etl.py`

**Location**: Find the summary generation code (look for `get_database_summary()` or similar around line 200-300).

**Code Changes**:

Add ruler count to the summary query:

```python
def get_database_summary(db: TournamentDatabase) -> Dict[str, Any]:
    """Get summary statistics about database contents.

    Args:
        db: Database instance

    Returns:
        Dictionary with summary statistics
    """
    summary = {}

    # ... existing queries ...

    # Total matches
    result = db.conn.execute("SELECT COUNT(*) FROM matches").fetchone()
    summary["total_matches"] = result[0]

    # Total players
    result = db.conn.execute("SELECT COUNT(*) FROM players").fetchone()
    summary["total_players"] = result[0]

    # ADD THIS: Total rulers
    result = db.conn.execute("SELECT COUNT(*) FROM rulers").fetchone()
    summary["total_rulers"] = result[0]

    # ... existing queries for events, territories, etc. ...

    return summary
```

**Also update the summary printing** (in `print_summary()` or similar):

```python
def print_summary(results: dict) -> None:
    """Print a summary of import results."""
    # ... existing code ...

    summary = results["summary"]
    print("\nDatabase contents:")
    print(f"  Matches: {summary['total_matches']}")
    print(f"  Players: {summary['total_players']} ({summary['unique_players']} unique)")
    print(f"  Rulers: {summary['total_rulers']}")  # ADD THIS LINE
    print(f"  Events: {summary['total_events']}")
    print(f"  Territories: {summary['total_territories']}")
    # ... rest of output ...
```

**Testing**:
```bash
# Run import with verbose output
uv run python scripts/import_attachments.py --directory saves --verbose

# Should see "Rulers: X" in the summary output
```

**Commit Message**:
```
feat: Add ruler count to ETL summary

Displays total number of rulers in import summary statistics
for better visibility of processed data.
```

---

### Task 9: Full Integration Test

**Objective**: Test the complete pipeline from save file to database with real data.

**Files to Create**:
- `tests/test_integration_rulers.py`

**Test File Template**:

```python
"""Integration tests for ruler tracking end-to-end."""

import pytest
from pathlib import Path
from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.etl import process_tournament_file


@pytest.fixture
def integration_db(tmp_path):
    """Create a temporary database for integration tests."""
    db_path = tmp_path / "integration_test.duckdb"
    db = TournamentDatabase(str(db_path))
    yield db
    db.close()


class TestRulerIntegration:
    """Integration tests for complete ruler tracking workflow."""

    def test_full_pipeline_single_file(self, integration_db):
        """Test complete ETL pipeline with ruler tracking."""
        # Use a known save file
        save_file = "saves/match_426504721_anarkos-becked.zip"

        # Process the file
        success = process_tournament_file(save_file, integration_db)
        assert success, "ETL pipeline should succeed"

        # Verify rulers were inserted
        result = integration_db.conn.execute(
            "SELECT COUNT(*) FROM rulers"
        ).fetchone()

        assert result[0] > 0, "Should have inserted rulers"

        # Verify rulers have correct structure
        rulers = integration_db.conn.execute(
            """
            SELECT
                match_id, player_id, character_id, ruler_name,
                archetype, starting_trait, succession_order, succession_turn
            FROM rulers
            ORDER BY player_id, succession_order
            """
        ).fetchall()

        # Should have at least 2 rulers (one per player minimum)
        assert len(rulers) >= 2

        # Verify data types and constraints
        for ruler in rulers:
            match_id, player_id, char_id, name, arch, trait, order, turn = ruler

            # IDs should be positive
            assert match_id > 0
            assert player_id > 0
            assert char_id >= 0

            # Succession order and turn should be valid
            assert order >= 0
            assert turn >= 1

            # Starting ruler should be at turn 1
            if order == 0:
                assert turn == 1

    def test_rulers_match_players(self, integration_db):
        """Test that all rulers have corresponding players."""
        save_file = "saves/match_426504721_anarkos-becked.zip"
        process_tournament_file(save_file, integration_db)

        # Query rulers and players
        result = integration_db.conn.execute(
            """
            SELECT r.player_id, p.player_id
            FROM rulers r
            LEFT JOIN players p ON r.player_id = p.player_id AND r.match_id = p.match_id
            WHERE p.player_id IS NULL
            """
        ).fetchall()

        # Should have no orphaned rulers
        assert len(result) == 0, "All rulers should have corresponding players"

    def test_starting_rulers_have_archetype_and_trait(self, integration_db):
        """Test that starting rulers have archetype and trait populated."""
        save_file = "saves/match_426504721_anarkos-becked.zip"
        process_tournament_file(save_file, integration_db)

        # Query starting rulers
        starting_rulers = integration_db.conn.execute(
            """
            SELECT ruler_name, archetype, starting_trait
            FROM rulers
            WHERE succession_order = 0
            """
        ).fetchall()

        assert len(starting_rulers) > 0, "Should have starting rulers"

        for name, archetype, trait in starting_rulers:
            # Starting rulers should have archetype and trait
            # (Note: Some save files may have null values due to data issues)
            if archetype is not None:
                assert len(archetype) > 0, f"Ruler {name} should have non-empty archetype"
            if trait is not None:
                assert len(trait) > 0, f"Ruler {name} should have non-empty trait"

    def test_succession_count_analytics(self, integration_db):
        """Test that we can answer the question: how many rulers did each player have?"""
        save_file = "saves/match_426504721_anarkos-becked.zip"
        process_tournament_file(save_file, integration_db)

        # Run analytics query
        results = integration_db.conn.execute(
            """
            SELECT
                p.player_name,
                COUNT(r.ruler_id) as ruler_count,
                MAX(r.succession_order) + 1 as succession_count
            FROM players p
            LEFT JOIN rulers r ON p.player_id = r.player_id AND p.match_id = r.match_id
            GROUP BY p.player_name
            ORDER BY p.player_name
            """
        ).fetchall()

        assert len(results) > 0, "Should have player ruler counts"

        for player_name, ruler_count, succession_count in results:
            # Counts should match
            assert ruler_count == succession_count, (
                f"Ruler count ({ruler_count}) should equal succession count ({succession_count})"
            )

            # Should have at least 1 ruler
            assert ruler_count >= 1, f"Player {player_name} should have at least 1 ruler"

    def test_archetype_analytics(self, integration_db):
        """Test that we can analyze starting archetypes."""
        save_file = "saves/match_426504721_anarkos-becked.zip"
        process_tournament_file(save_file, integration_db)

        # Run archetype analytics query
        results = integration_db.conn.execute(
            """
            SELECT
                archetype,
                COUNT(*) as count
            FROM rulers
            WHERE succession_order = 0
            AND archetype IS NOT NULL
            GROUP BY archetype
            ORDER BY count DESC
            """
        ).fetchall()

        # Should have at least one archetype
        assert len(results) > 0, "Should have archetype data"

        # Verify archetypes are valid
        valid_archetypes = {"Scholar", "Tactician", "Commander", "Schemer"}
        for archetype, count in results:
            assert archetype in valid_archetypes, (
                f"Invalid archetype: {archetype}"
            )
            assert count > 0


class TestMultipleFilesIntegration:
    """Test ruler tracking across multiple save files."""

    def test_multiple_files(self, integration_db):
        """Test processing multiple save files."""
        import os

        saves_dir = Path("saves")
        save_files = list(saves_dir.glob("match_*.zip"))[:3]  # Process 3 files

        successful = 0
        for save_file in save_files:
            success = process_tournament_file(str(save_file), integration_db)
            if success:
                successful += 1

        assert successful > 0, "At least one file should process successfully"

        # Verify total ruler count
        result = integration_db.conn.execute(
            "SELECT COUNT(*) FROM rulers"
        ).fetchone()

        # Should have rulers from multiple matches
        assert result[0] >= successful * 2, (
            "Should have at least 2 rulers per successful match"
        )
```

**Testing**:
```bash
# Run integration tests
uv run pytest tests/test_integration_rulers.py -v

# Should see all tests passing
```

**Commit Message**:
```
test: Add integration tests for ruler tracking

Tests verify complete ETL pipeline from save files to database,
including foreign key relationships and analytics queries.
```

---

### Task 10: Run Full Re-import with Real Data

**Objective**: Re-import all save files to populate the rulers table with production data.

**Prerequisites**:
- All previous tasks completed
- All tests passing
- Database backup created

**Steps**:

1. **Backup existing database**:
   ```bash
   cp data/tournament_data.duckdb data/tournament_data.duckdb.backup_$(date +%Y%m%d_%H%M%S)
   ```

2. **Run full re-import**:
   ```bash
   uv run python scripts/import_attachments.py --directory saves --force --verbose
   ```

3. **Verify data**:
   ```bash
   # Check ruler count
   uv run duckdb data/tournament_data.duckdb -readonly -c "SELECT COUNT(*) FROM rulers"

   # Check sample data
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT
       p.player_name,
       r.ruler_name,
       r.archetype,
       r.starting_trait,
       r.succession_order
   FROM rulers r
   JOIN players p ON r.player_id = p.player_id AND r.match_id = p.match_id
   WHERE r.succession_order = 0
   LIMIT 10
   "

   # Verify foreign keys
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT COUNT(*)
   FROM rulers r
   LEFT JOIN players p ON r.player_id = p.player_id AND r.match_id = p.match_id
   WHERE p.player_id IS NULL
   "
   # Should return 0 (no orphaned rulers)
   ```

4. **Run validation queries**:
   ```bash
   # How many rulers per player?
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT
       COUNT(r.ruler_id) as total_rulers,
       COUNT(DISTINCT r.player_id) as players_with_rulers,
       AVG(ruler_count) as avg_rulers_per_player
   FROM (
       SELECT player_id, COUNT(*) as ruler_count
       FROM rulers
       GROUP BY player_id
   ) subquery
   "

   # Archetype distribution
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT
       archetype,
       COUNT(*) as count,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
   FROM rulers
   WHERE succession_order = 0 AND archetype IS NOT NULL
   GROUP BY archetype
   ORDER BY count DESC
   "

   # Starting trait distribution
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT
       starting_trait,
       COUNT(*) as count
   FROM rulers
   WHERE succession_order = 0 AND starting_trait IS NOT NULL
   GROUP BY starting_trait
   ORDER BY count DESC
   LIMIT 15
   "
   ```

**Expected Results**:
- Ruler count should be >= player count (at least 1 ruler per player)
- All rulers should have matching players
- Starting rulers (order=0) should have archetype and trait data
- Archetype distribution should show Scholar, Tactician, Commander, Schemer
- No database errors or warnings in logs

**Troubleshooting**:

If data looks incorrect:
```bash
# Check parser output for a single file
uv run python -c "
from tournament_visualizer.data.parser import OldWorldSaveParser

parser = OldWorldSaveParser('saves/match_426504721_anarkos-becked.zip')
parser.extract_and_parse()
rulers = parser.extract_rulers()

for r in rulers:
    print(f'{r[\"player_id\"]}: {r[\"ruler_name\"]} - {r[\"archetype\"]} / {r[\"starting_trait\"]} (order {r[\"succession_order\"]})')
"
```

If import fails:
```bash
# Check logs
tail -100 logs/tournament_import.log

# Try single file import
uv run python -c "
from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.etl import process_tournament_file

db = TournamentDatabase()
result = process_tournament_file('saves/match_426504721_anarkos-becked.zip', db)
print(f'Result: {result}')
db.close()
"
```

**Commit Message**:
```
feat: Populate rulers table with production data

Re-imported all save files to populate the new rulers table.
Verified data integrity and foreign key relationships.
```

---

### Task 11: Create Validation Script

**Objective**: Create a script to validate ruler data integrity.

**Files to Create**:
- `scripts/validate_rulers.py`

**Script Template**:

```python
#!/usr/bin/env python3
"""Validation script for ruler data integrity.

This script checks:
1. All rulers have corresponding players
2. Succession order is sequential for each player
3. Starting rulers are at turn 1
4. Successor rulers have succession_turn > 1
5. Archetype and trait values are valid
6. No duplicate rulers within a player's succession
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tournament_visualizer.config import Config
from tournament_visualizer.data.database import TournamentDatabase


def validate_foreign_keys(db: TournamentDatabase) -> tuple[bool, list[str]]:
    """Validate that all rulers have corresponding players.

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    # Check for orphaned rulers
    orphaned = db.conn.execute(
        """
        SELECT r.ruler_id, r.match_id, r.player_id
        FROM rulers r
        LEFT JOIN players p ON r.player_id = p.player_id AND r.match_id = p.match_id
        WHERE p.player_id IS NULL
        """
    ).fetchall()

    if orphaned:
        errors.append(f"Found {len(orphaned)} rulers without corresponding players:")
        for ruler_id, match_id, player_id in orphaned[:5]:
            errors.append(f"  Ruler {ruler_id}: match={match_id}, player={player_id}")

    return len(errors) == 0, errors


def validate_succession_order(db: TournamentDatabase) -> tuple[bool, list[str]]:
    """Validate that succession order is sequential for each player.

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    # Check for gaps or duplicates in succession order
    gaps = db.conn.execute(
        """
        WITH succession_gaps AS (
            SELECT
                match_id,
                player_id,
                succession_order,
                LAG(succession_order) OVER (
                    PARTITION BY match_id, player_id
                    ORDER BY succession_order
                ) as prev_order
            FROM rulers
        )
        SELECT match_id, player_id, succession_order, prev_order
        FROM succession_gaps
        WHERE prev_order IS NOT NULL
        AND succession_order != prev_order + 1
        """
    ).fetchall()

    if gaps:
        errors.append(f"Found {len(gaps)} succession order gaps or duplicates:")
        for match_id, player_id, order, prev_order in gaps[:5]:
            errors.append(
                f"  Match {match_id}, Player {player_id}: "
                f"order {order} after {prev_order}"
            )

    return len(errors) == 0, errors


def validate_succession_turns(db: TournamentDatabase) -> tuple[bool, list[str]]:
    """Validate succession turn constraints.

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    # Starting rulers should be at turn 1
    bad_starting_turns = db.conn.execute(
        """
        SELECT match_id, player_id, ruler_name, succession_turn
        FROM rulers
        WHERE succession_order = 0
        AND succession_turn != 1
        """
    ).fetchall()

    if bad_starting_turns:
        errors.append(
            f"Found {len(bad_starting_turns)} starting rulers not at turn 1:"
        )
        for match_id, player_id, name, turn in bad_starting_turns[:5]:
            errors.append(
                f"  Match {match_id}, Player {player_id}, {name}: turn {turn}"
            )

    # Successor rulers should be after turn 1
    bad_successor_turns = db.conn.execute(
        """
        SELECT match_id, player_id, ruler_name, succession_turn, succession_order
        FROM rulers
        WHERE succession_order > 0
        AND succession_turn <= 1
        """
    ).fetchall()

    if bad_successor_turns:
        errors.append(
            f"Found {len(bad_successor_turns)} successors at/before turn 1:"
        )
        for match_id, player_id, name, turn, order in bad_successor_turns[:5]:
            errors.append(
                f"  Match {match_id}, Player {player_id}, {name} "
                f"(order {order}): turn {turn}"
            )

    return len(errors) == 0, errors


def validate_archetype_values(db: TournamentDatabase) -> tuple[bool, list[str]]:
    """Validate archetype values are from expected set.

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    valid_archetypes = {"Scholar", "Tactician", "Commander", "Schemer"}

    invalid = db.conn.execute(
        """
        SELECT DISTINCT archetype, COUNT(*) as count
        FROM rulers
        WHERE archetype IS NOT NULL
        AND archetype NOT IN ('Scholar', 'Tactician', 'Commander', 'Schemer')
        GROUP BY archetype
        """
    ).fetchall()

    if invalid:
        errors.append(f"Found {len(invalid)} invalid archetype values:")
        for archetype, count in invalid:
            errors.append(f"  '{archetype}': {count} occurrences")

    return len(errors) == 0, errors


def validate_duplicate_rulers(db: TournamentDatabase) -> tuple[bool, list[str]]:
    """Validate no duplicate character IDs within a player's succession.

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    duplicates = db.conn.execute(
        """
        SELECT match_id, player_id, character_id, COUNT(*) as count
        FROM rulers
        GROUP BY match_id, player_id, character_id
        HAVING COUNT(*) > 1
        """
    ).fetchall()

    if duplicates:
        errors.append(
            f"Found {len(duplicates)} duplicate character IDs in succession:"
        )
        for match_id, player_id, char_id, count in duplicates[:5]:
            errors.append(
                f"  Match {match_id}, Player {player_id}, "
                f"Character {char_id}: {count} times"
            )

    return len(errors) == 0, errors


def print_summary(db: TournamentDatabase) -> None:
    """Print summary statistics about rulers."""
    print("\n" + "=" * 60)
    print("RULER DATA SUMMARY")
    print("=" * 60)

    # Total counts
    total_rulers = db.conn.execute("SELECT COUNT(*) FROM rulers").fetchone()[0]
    total_players = db.conn.execute(
        "SELECT COUNT(DISTINCT player_id) FROM rulers"
    ).fetchone()[0]

    print(f"\nTotal rulers: {total_rulers}")
    print(f"Players with rulers: {total_players}")
    print(f"Average rulers per player: {total_rulers / total_players:.2f}")

    # Succession statistics
    succession_stats = db.conn.execute(
        """
        SELECT
            MIN(ruler_count) as min_rulers,
            MAX(ruler_count) as max_rulers,
            AVG(ruler_count) as avg_rulers
        FROM (
            SELECT player_id, COUNT(*) as ruler_count
            FROM rulers
            GROUP BY player_id
        ) subquery
        """
    ).fetchone()

    print(f"\nRulers per player: min={succession_stats[0]}, "
          f"max={succession_stats[1]}, avg={succession_stats[2]:.2f}")

    # Archetype distribution
    print("\nStarting archetype distribution:")
    archetypes = db.conn.execute(
        """
        SELECT
            COALESCE(archetype, 'Unknown') as archetype,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
        FROM rulers
        WHERE succession_order = 0
        GROUP BY archetype
        ORDER BY count DESC
        """
    ).fetchall()

    for archetype, count, pct in archetypes:
        print(f"  {archetype}: {count} ({pct}%)")

    # Starting trait distribution (top 10)
    print("\nTop 10 starting traits:")
    traits = db.conn.execute(
        """
        SELECT
            COALESCE(starting_trait, 'Unknown') as trait,
            COUNT(*) as count
        FROM rulers
        WHERE succession_order = 0
        GROUP BY starting_trait
        ORDER BY count DESC
        LIMIT 10
        """
    ).fetchall()

    for trait, count in traits:
        print(f"  {trait}: {count}")

    print("=" * 60)


def main() -> None:
    """Run all validations."""
    print("Validating ruler data...")

    # Connect to database
    db = TournamentDatabase(Config.DATABASE_PATH)

    # Run validations
    validations = [
        ("Foreign key integrity", validate_foreign_keys),
        ("Succession order", validate_succession_order),
        ("Succession turns", validate_succession_turns),
        ("Archetype values", validate_archetype_values),
        ("Duplicate rulers", validate_duplicate_rulers),
    ]

    all_valid = True
    all_errors = []

    for name, validator in validations:
        print(f"\nChecking {name}...", end=" ")
        is_valid, errors = validator(db)

        if is_valid:
            print("✓ PASS")
        else:
            print("✗ FAIL")
            all_errors.extend([f"\n{name}:"] + errors)
            all_valid = False

    # Print summary
    print_summary(db)

    # Print all errors at the end
    if not all_valid:
        print("\n" + "=" * 60)
        print("VALIDATION ERRORS")
        print("=" * 60)
        for error in all_errors:
            print(error)
        print("=" * 60)
        sys.exit(1)
    else:
        print("\n✓ All validations passed!")
        sys.exit(0)

    db.close()


if __name__ == "__main__":
    main()
```

**Testing**:
```bash
# Run validation
uv run python scripts/validate_rulers.py

# Should output validation results and summary statistics
```

**Commit Message**:
```
feat: Add ruler data validation script

Validates foreign keys, succession order, turn constraints,
archetype values, and identifies duplicates. Provides summary
statistics for ruler data quality assessment.
```

---

### Task 12: Update Documentation

**Objective**: Document the new rulers table and its usage.

**Files to Modify**:
- `docs/developer-guide.md`

**Add Section** (suggested location: after Player Data section):

```markdown
## Ruler Data

### Overview

The `rulers` table tracks all rulers (leaders) for each player throughout a match, including the archetype and starting trait chosen at game initialization.

### Schema

```sql
CREATE TABLE rulers (
    ruler_id INTEGER PRIMARY KEY,
    match_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,
    character_id INTEGER NOT NULL,
    ruler_name VARCHAR,
    archetype VARCHAR,
    starting_trait VARCHAR,
    succession_order INTEGER NOT NULL,
    succession_turn INTEGER NOT NULL,
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id)
);
```

### Field Descriptions

- **ruler_id**: Auto-incrementing primary key
- **match_id**: Reference to the match
- **player_id**: Reference to the player (1-based, consistent with `players` table)
- **character_id**: Character ID from XML save file (0-based)
- **ruler_name**: Formatted ruler name (e.g., "Yazdegerd")
- **archetype**: One of: Scholar, Tactician, Commander, Schemer
- **starting_trait**: Initial trait chosen at game start (e.g., "Educated", "Brave")
- **succession_order**: 0 for starting ruler, 1+ for successors
- **succession_turn**: Turn when ruler took power (always 1 for starting ruler)

### Common Queries

**Count rulers per player:**
```sql
SELECT
    p.player_name,
    COUNT(r.ruler_id) as total_rulers
FROM players p
LEFT JOIN rulers r ON p.player_id = r.player_id AND p.match_id = r.match_id
GROUP BY p.player_name
ORDER BY total_rulers DESC;
```

**Get starting ruler for each player:**
```sql
SELECT
    p.player_name,
    r.ruler_name,
    r.archetype,
    r.starting_trait
FROM players p
JOIN rulers r ON p.player_id = r.player_id
    AND p.match_id = r.match_id
    AND r.succession_order = 0;
```

**Archetype win rate:**
```sql
SELECT
    r.archetype,
    COUNT(*) as games,
    SUM(CASE WHEN mw.winner_player_id = r.player_id THEN 1 ELSE 0 END) as wins,
    ROUND(
        SUM(CASE WHEN mw.winner_player_id = r.player_id THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
        2
    ) as win_rate
FROM rulers r
JOIN match_winners mw ON r.match_id = mw.match_id
WHERE r.succession_order = 0
AND r.archetype IS NOT NULL
GROUP BY r.archetype
ORDER BY win_rate DESC;
```

**Players with most successions:**
```sql
SELECT
    p.player_name,
    p.match_id,
    COUNT(r.ruler_id) as ruler_count
FROM players p
JOIN rulers r ON p.player_id = r.player_id AND p.match_id = r.match_id
GROUP BY p.player_name, p.match_id
HAVING COUNT(r.ruler_id) > 2
ORDER BY ruler_count DESC;
```

### Data Source

Ruler data is extracted from Old World save files:
- `Player/Leaders` element contains character IDs in succession order
- `Character` elements contain name, archetype, and trait data
- Succession turns come from `CHARACTER_SUCCESSION` events in LogData

### Validation

Run the validation script to check data integrity:
```bash
uv run python scripts/validate_rulers.py
```

This checks:
- Foreign key relationships
- Succession order sequencing
- Turn constraints
- Valid archetype values
- No duplicate rulers

### Notes

- Starting rulers (succession_order=0) always have succession_turn=1
- Archetype and starting_trait are the values chosen at game start
- Traits gained during gameplay are not tracked in this table
- Character IDs are consistent with event data for cross-referencing
```

**Commit Message**:
```
docs: Document rulers table and common queries

Adds comprehensive documentation for the rulers table including
schema, field descriptions, common queries, and validation procedures.
```

---

### Task 13: Add Analytics Examples

**Objective**: Create example analytics queries demonstrating ruler data usage.

**Files to Create**:
- `scripts/analytics_rulers.py`

**Script Template**:

```python
#!/usr/bin/env python3
"""Example analytics queries using ruler data.

Demonstrates how to analyze ruler archetypes, traits, and succession patterns.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tournament_visualizer.config import Config
from tournament_visualizer.data.database import TournamentDatabase


def archetype_win_rates(db: TournamentDatabase) -> None:
    """Calculate win rates by starting archetype."""
    print("\n" + "=" * 60)
    print("WIN RATES BY STARTING ARCHETYPE")
    print("=" * 60)

    results = db.conn.execute(
        """
        SELECT
            r.archetype,
            COUNT(*) as games,
            SUM(CASE WHEN mw.winner_player_id = r.player_id THEN 1 ELSE 0 END) as wins,
            ROUND(
                SUM(CASE WHEN mw.winner_player_id = r.player_id THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
                2
            ) as win_rate
        FROM rulers r
        JOIN match_winners mw ON r.match_id = mw.match_id
        WHERE r.succession_order = 0
        AND r.archetype IS NOT NULL
        GROUP BY r.archetype
        ORDER BY win_rate DESC
        """
    ).fetchall()

    print(f"\n{'Archetype':<15} {'Games':<8} {'Wins':<8} {'Win Rate':<10}")
    print("-" * 45)

    for archetype, games, wins, win_rate in results:
        print(f"{archetype:<15} {games:<8} {wins:<8} {win_rate}%")


def trait_win_rates(db: TournamentDatabase) -> None:
    """Calculate win rates by starting trait (top 15)."""
    print("\n" + "=" * 60)
    print("WIN RATES BY STARTING TRAIT (Top 15)")
    print("=" * 60)

    results = db.conn.execute(
        """
        SELECT
            r.starting_trait,
            COUNT(*) as games,
            SUM(CASE WHEN mw.winner_player_id = r.player_id THEN 1 ELSE 0 END) as wins,
            ROUND(
                SUM(CASE WHEN mw.winner_player_id = r.player_id THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
                2
            ) as win_rate
        FROM rulers r
        JOIN match_winners mw ON r.match_id = mw.match_id
        WHERE r.succession_order = 0
        AND r.starting_trait IS NOT NULL
        GROUP BY r.starting_trait
        HAVING COUNT(*) >= 3
        ORDER BY win_rate DESC
        LIMIT 15
        """
    ).fetchall()

    print(f"\n{'Trait':<20} {'Games':<8} {'Wins':<8} {'Win Rate':<10}")
    print("-" * 50)

    for trait, games, wins, win_rate in results:
        print(f"{trait:<20} {games:<8} {wins:<8} {win_rate}%")


def succession_impact(db: TournamentDatabase) -> None:
    """Analyze relationship between ruler successions and victory."""
    print("\n" + "=" * 60)
    print("SUCCESSION IMPACT ON VICTORY")
    print("=" * 60)

    results = db.conn.execute(
        """
        WITH player_successions AS (
            SELECT
                r.match_id,
                r.player_id,
                COUNT(*) as ruler_count,
                MAX(CASE WHEN mw.winner_player_id = r.player_id THEN 1 ELSE 0 END) as won
            FROM rulers r
            JOIN match_winners mw ON r.match_id = mw.match_id
            GROUP BY r.match_id, r.player_id
        )
        SELECT
            CASE
                WHEN ruler_count = 1 THEN '1 ruler'
                WHEN ruler_count = 2 THEN '2 rulers'
                WHEN ruler_count = 3 THEN '3 rulers'
                ELSE '4+ rulers'
            END as succession_count,
            COUNT(*) as games,
            SUM(won) as wins,
            ROUND(SUM(won) * 100.0 / COUNT(*), 2) as win_rate
        FROM player_successions
        GROUP BY
            CASE
                WHEN ruler_count = 1 THEN '1 ruler'
                WHEN ruler_count = 2 THEN '2 rulers'
                WHEN ruler_count = 3 THEN '3 rulers'
                ELSE '4+ rulers'
            END
        ORDER BY succession_count
        """
    ).fetchall()

    print(f"\n{'Successions':<15} {'Games':<8} {'Wins':<8} {'Win Rate':<10}")
    print("-" * 45)

    for succession, games, wins, win_rate in results:
        print(f"{succession:<15} {games:<8} {wins:<8} {win_rate}%")


def archetype_trait_combinations(db: TournamentDatabase) -> None:
    """Show most common archetype + trait combinations."""
    print("\n" + "=" * 60)
    print("POPULAR ARCHETYPE + TRAIT COMBINATIONS (Top 10)")
    print("=" * 60)

    results = db.conn.execute(
        """
        SELECT
            r.archetype,
            r.starting_trait,
            COUNT(*) as count
        FROM rulers r
        WHERE r.succession_order = 0
        AND r.archetype IS NOT NULL
        AND r.starting_trait IS NOT NULL
        GROUP BY r.archetype, r.starting_trait
        ORDER BY count DESC
        LIMIT 10
        """
    ).fetchall()

    print(f"\n{'Archetype':<15} {'Trait':<20} {'Count':<8}")
    print("-" * 45)

    for archetype, trait, count in results:
        print(f"{archetype:<15} {trait:<20} {count:<8}")


def archetype_by_nation(db: TournamentDatabase) -> None:
    """Show archetype preferences by nation."""
    print("\n" + "=" * 60)
    print("ARCHETYPE PREFERENCES BY NATION")
    print("=" * 60)

    results = db.conn.execute(
        """
        SELECT
            p.civilization as nation,
            r.archetype,
            COUNT(*) as count
        FROM rulers r
        JOIN players p ON r.player_id = p.player_id AND r.match_id = p.match_id
        WHERE r.succession_order = 0
        AND r.archetype IS NOT NULL
        AND p.civilization IS NOT NULL
        GROUP BY p.civilization, r.archetype
        HAVING COUNT(*) >= 2
        ORDER BY nation, count DESC
        """
    ).fetchall()

    current_nation = None
    for nation, archetype, count in results:
        if nation != current_nation:
            print(f"\n{nation}:")
            current_nation = nation
        print(f"  {archetype}: {count}")


def main() -> None:
    """Run all analytics examples."""
    print("Ruler Analytics Examples")
    print("=" * 60)

    db = TournamentDatabase(Config.DATABASE_PATH)

    # Run analytics
    archetype_win_rates(db)
    trait_win_rates(db)
    succession_impact(db)
    archetype_trait_combinations(db)
    archetype_by_nation(db)

    print("\n" + "=" * 60)
    print("Analytics complete!")
    print("=" * 60)

    db.close()


if __name__ == "__main__":
    main()
```

**Testing**:
```bash
# Run analytics
uv run python scripts/analytics_rulers.py

# Should output various analytics reports
```

**Commit Message**:
```
feat: Add ruler analytics examples

Demonstrates analytics queries for archetype win rates, trait
effectiveness, succession impact, and popular combinations.
```

---

## Summary Checklist

Before considering this implementation complete, verify:

- [ ] Migration document created (`docs/migrations/003_add_rulers_table.md`)
- [ ] Database schema updated (`tournament_visualizer/data/database.py`)
- [ ] Parser method implemented (`tournament_visualizer/data/parser.py`)
- [ ] Parser tests written and passing (`tests/test_parser_rulers.py`)
- [ ] Database insert method implemented (`tournament_visualizer/data/database.py`)
- [ ] Database tests written and passing (`tests/test_database_rulers.py`)
- [ ] ETL integration complete (`tournament_visualizer/data/etl.py`)
- [ ] ETL summary updated to show ruler counts
- [ ] Integration tests written and passing (`tests/test_integration_rulers.py`)
- [ ] Full re-import completed successfully
- [ ] Validation script created and passing (`scripts/validate_rulers.py`)
- [ ] Developer documentation updated (`docs/developer-guide.md`)
- [ ] Analytics examples created (`scripts/analytics_rulers.py`)
- [ ] All tests passing: `uv run pytest -v`
- [ ] Code formatted: `uv run black tournament_visualizer/`
- [ ] Linting clean: `uv run ruff check tournament_visualizer/`

## Time Estimates

- Task 1: 30 minutes (migration doc)
- Task 2: 20 minutes (database schema)
- Task 3: 2 hours (parser method)
- Task 4: 1.5 hours (parser tests)
- Task 5: 45 minutes (database insert)
- Task 6: 1 hour (database tests)
- Task 7: 30 minutes (ETL integration)
- Task 8: 15 minutes (ETL summary)
- Task 9: 1 hour (integration tests)
- Task 10: 30 minutes (re-import + verification)
- Task 11: 1 hour (validation script)
- Task 12: 30 minutes (documentation)
- Task 13: 45 minutes (analytics examples)

**Total: ~11 hours**

## Success Criteria

The implementation is successful when:

1. All tests pass
2. Full re-import completes without errors
3. Validation script passes all checks
4. Can answer the question: "How many rulers did each player have?"
5. Can analyze starting archetype/trait effectiveness
6. Data integrity constraints are maintained
7. Documentation is complete and accurate

## Rollback Plan

If issues are discovered after deployment:

1. Restore database from backup:
   ```bash
   cp data/tournament_data.duckdb.backup_TIMESTAMP data/tournament_data.duckdb
   ```

2. Revert code changes:
   ```bash
   git revert <commit-range>
   ```

3. Drop the rulers table:
   ```sql
   DROP TABLE IF EXISTS rulers;
   DELETE FROM schema_migrations WHERE version = 3;
   ```
