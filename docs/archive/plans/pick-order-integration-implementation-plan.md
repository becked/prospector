# Pick Order Data Integration Implementation Plan

> **Status**: Completed and archived (2025-10-25)
>
> Feature complete and documented in CLAUDE.md (Pick Order Data Integration section).
> See migrations/008_add_pick_order_tracking.md for schema changes.

## Overview

**Goal:** Integrate nation pick order data from a Google Spreadsheet into the tournament database to enable analysis of whether picking first or second affects game outcomes.

**Context:**
- In tournament games, one player picks their nation first, the other picks second
- Save files don't capture pick order (both show nations chosen on turn 1)
- Tournament organizer maintains pick order data in a Google Sheet (GAMEDATA tab)
- We need this data to analyze pick order impact on win rates, nation preferences, counter-picks, etc.

**Approach:**
- Use Google Sheets API with API key (same as GDrive integration)
- Parse the multi-column game layout from the sheet
- Store parsed data in intermediate table (`pick_order_games`)
- Match games to database matches using player names + round
- Update matches table with first/second picker participant IDs
- Enable pick order analytics queries

**Estimated Total Time:** 6-8 hours

---

## Prerequisites

### Environment Setup
- Python 3.11+ with `uv` package manager
- DuckDB database at `data/tournament_data.duckdb`
- Environment variables set in `.env`:
  - `CHALLONGE_KEY` - Challonge API key
  - `CHALLONGE_USER` - Challonge username
  - `challonge_tournament_id` - Tournament ID
  - `GOOGLE_DRIVE_API_KEY` - Google API key (already configured for GDrive)
  - `GOOGLE_SHEETS_SPREADSHEET_ID` - **NEW** - Spreadsheet ID
  - `GOOGLE_SHEETS_GAMEDATA_GID` - **NEW** - GAMEDATA sheet GID

### Key Files to Understand

**Configuration:**
- `tournament_visualizer/config.py` - Configuration constants
- `.env` - Environment variables (not in git)

**Data Pipeline:**
- `scripts/download_attachments.py` - Downloads save files
- `scripts/import_attachments.py` - Parses saves to database
- `scripts/link_players_to_participants.py` - Links players to participants
- `scripts/sync_tournament_data.sh` - Complete sync workflow

**Existing Integrations:**
- `tournament_visualizer/data/gdrive_client.py` - Google Drive client (reuse pattern)
- `tournament_visualizer/data/name_normalizer.py` - Name normalization (reuse for matching)

**Database Schema:**
- `tournament_visualizer/data/schema.py` - Table definitions
- `matches` table - Match metadata
- `players` table - Per-match player data
- `tournament_participants` table - Cross-match participant tracking

**Codebase Patterns:**
- Uses `logging` for all output (not print statements)
- Type hints required on all functions
- Follows DRY principle - extract shared logic
- Follows YAGNI - only implement what's needed now

---

## Design Decisions

### Key Architectural Choices

**1. Intermediate Storage (pick_order_games table)**
- Store raw sheet data separately before matching to matches
- Enables audit trail and debugging
- Can re-run matching logic without re-fetching sheet
- Shows which games didn't match

**2. Matching Strategy: Player Names + Round**
- Sheet doesn't have Challonge match IDs
- Match by normalized player names within same round
- Use existing participant name override system for mismatches
- Validate by checking both players match

**3. Row Number Detection: Dynamic**
- Don't hardcode row offsets (fragile if sheet changes)
- Find "Nation; First Pick" text in column A for each round
- Detect round boundaries by "ROUND X" pattern
- Parse game columns by finding "Game Number" row

**4. Nation Matching: Direct from Row Values**
- Row 8/37/etc contains "Nation; First Pick" and the nation name
- Row 9/38/etc contains "Second Pick" and the nation name
- Match nation to player by comparing to save file civilization data
- No column position assumptions needed

**5. Error Handling: Log and Skip**
- If game can't be matched, log warning and continue
- Don't halt entire import on single failure
- Collect statistics on match success rate
- Provide clear error messages for debugging

**6. Google Sheets API: Same Key as GDrive**
- Reuse existing GOOGLE_DRIVE_API_KEY (works for Sheets too)
- No new authentication setup required
- Add spreadsheet ID and sheet GID to config

---

## Implementation Tasks

### Task 1: Add Google Sheets Configuration

**Time Estimate:** 15 minutes

**Objective:** Add spreadsheet ID and sheet GID to configuration system.

**Why:** Configuration should be centralized, not hardcoded.

**Files to Modify:**
- `tournament_visualizer/config.py`
- `.env.example`

**Code Changes:**

1. Open `tournament_visualizer/config.py`

2. Add after the existing Google Drive configuration:
```python
# Google Sheets configuration (for pick order data)
GOOGLE_SHEETS_SPREADSHEET_ID = os.getenv(
    "GOOGLE_SHEETS_SPREADSHEET_ID",
    "19t5AbJtQr5kZ62pw8FJ-r2b9LVkz01zl2GUNWkIrhAc"  # Default: OWT 25 Stats sheet
)
GOOGLE_SHEETS_GAMEDATA_GID = os.getenv(
    "GOOGLE_SHEETS_GAMEDATA_GID",
    "1663493966"  # Default: GAMEDATA *SPOILER WARNING* tab
)
```

3. Update `.env.example`:
```bash
# Add to the end of .env.example
# Google Sheets API (for pick order data)
GOOGLE_SHEETS_SPREADSHEET_ID=19t5AbJtQr5kZ62pw8FJ-r2b9LVkz01zl2GUNWkIrhAc
GOOGLE_SHEETS_GAMEDATA_GID=1663493966
```

**Testing:**
```bash
# Verify config loads
uv run python -c "from tournament_visualizer.config import Config; print(Config.GOOGLE_SHEETS_SPREADSHEET_ID); print(Config.GOOGLE_SHEETS_GAMEDATA_GID)"
```

Should print the spreadsheet ID and sheet GID.

**Commit Message:**
```
feat: Add Google Sheets configuration for pick order data

Adds GOOGLE_SHEETS_SPREADSHEET_ID and GOOGLE_SHEETS_GAMEDATA_GID to
centralized configuration. Defaults to OWT 25 Stats GAMEDATA tab.
```

---

### Task 2: Install Google Sheets API Dependency

**Time Estimate:** 5 minutes

**Objective:** Add Google Sheets API client library to project dependencies.

**Why:** We need the official Google API client to interact with Google Sheets. Note that this is the SAME library we already have for Google Drive - both use `google-api-python-client`.

**Files to Check:**
- `pyproject.toml`

**Steps:**

1. Check if already installed (likely yes from GDrive integration):
```bash
uv pip list | grep google-api-python-client
```

2. If not installed, add it:
```bash
uv add google-api-python-client
```

3. Verify installation:
```bash
uv run python -c "from googleapiclient.discovery import build; print('OK')"
```

**Commit Message:**
```
chore: Verify google-api-python-client dependency

Confirms google-api-python-client is installed (shared with GDrive
integration). Both Sheets and Drive APIs use the same library.
```

**Note:** If already installed, skip the commit - nothing changed.

---

### Task 3: Create Database Schema for pick_order_games Table

**Time Estimate:** 30 minutes

**Objective:** Add intermediate storage table for parsed sheet data before matching.

**Why:** Storing raw sheet data separately enables:
- Audit trail of what came from the sheet
- Debugging match failures
- Re-running matching logic without re-fetching
- Seeing which games didn't match to database

**Files to Modify:**
- `tournament_visualizer/data/schema.py`

**Files to Create:**
- `docs/migrations/008_add_pick_order_tracking.md` (assuming previous migrations are 001-007)

**Schema Design:**

The `pick_order_games` table stores the parsed Google Sheets data:

```sql
CREATE TABLE pick_order_games (
    game_number INTEGER PRIMARY KEY,
    round_number INTEGER NOT NULL,
    round_label VARCHAR,  -- "ROUND 1", "UPPER BRACKET ROUND 2, G21-G28"

    -- Players as they appear in the sheet
    player1_sheet_name VARCHAR NOT NULL,
    player2_sheet_name VARCHAR NOT NULL,

    -- Nations picked (first/second)
    first_pick_nation VARCHAR NOT NULL,
    second_pick_nation VARCHAR NOT NULL,

    -- Derived: which player picked which nation
    first_picker_sheet_name VARCHAR,  -- player1 or player2
    second_picker_sheet_name VARCHAR, -- player1 or player2

    -- Matching results
    matched_match_id BIGINT,  -- NULL if no match found
    first_picker_participant_id BIGINT,  -- After matching
    second_picker_participant_id BIGINT, -- After matching
    match_confidence VARCHAR,  -- 'exact', 'normalized', 'manual_override'
    match_reason VARCHAR,  -- Human-readable explanation

    -- Metadata
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    matched_at TIMESTAMP,

    FOREIGN KEY (matched_match_id) REFERENCES matches(match_id),
    FOREIGN KEY (first_picker_participant_id) REFERENCES tournament_participants(participant_id),
    FOREIGN KEY (second_picker_participant_id) REFERENCES tournament_participants(participant_id)
);
```

**Implementation:**

1. Add to `tournament_visualizer/data/schema.py`:

```python
# Add after existing table definitions

PICK_ORDER_GAMES_SCHEMA = """
CREATE TABLE IF NOT EXISTS pick_order_games (
    game_number INTEGER PRIMARY KEY,
    round_number INTEGER NOT NULL,
    round_label VARCHAR,

    player1_sheet_name VARCHAR NOT NULL,
    player2_sheet_name VARCHAR NOT NULL,

    first_pick_nation VARCHAR NOT NULL,
    second_pick_nation VARCHAR NOT NULL,

    first_picker_sheet_name VARCHAR,
    second_picker_sheet_name VARCHAR,

    matched_match_id BIGINT,
    first_picker_participant_id BIGINT,
    second_picker_participant_id BIGINT,
    match_confidence VARCHAR,
    match_reason VARCHAR,

    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    matched_at TIMESTAMP,

    FOREIGN KEY (matched_match_id) REFERENCES matches(match_id),
    FOREIGN KEY (first_picker_participant_id) REFERENCES tournament_participants(participant_id),
    FOREIGN KEY (second_picker_participant_id) REFERENCES tournament_participants(participant_id)
);
"""

# Add to SCHEMAS list
SCHEMAS = [
    # ... existing schemas ...
    PICK_ORDER_GAMES_SCHEMA,
]
```

2. Create migration documentation in `docs/migrations/008_add_pick_order_tracking.md`:

```markdown
# Migration 008: Add Pick Order Tracking

## Overview

Adds support for tracking nation pick order (first pick vs second pick) from Google Sheets data.

**Date:** 2025-10-17
**Author:** System
**Status:** Pending

---

## Changes

### New Table: pick_order_games

Stores parsed pick order data from Google Sheets before matching to database.

```sql
CREATE TABLE pick_order_games (
    game_number INTEGER PRIMARY KEY,
    round_number INTEGER NOT NULL,
    round_label VARCHAR,

    player1_sheet_name VARCHAR NOT NULL,
    player2_sheet_name VARCHAR NOT NULL,

    first_pick_nation VARCHAR NOT NULL,
    second_pick_nation VARCHAR NOT NULL,

    first_picker_sheet_name VARCHAR,
    second_picker_sheet_name VARCHAR,

    matched_match_id BIGINT,
    first_picker_participant_id BIGINT,
    second_picker_participant_id BIGINT,
    match_confidence VARCHAR,
    match_reason VARCHAR,

    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    matched_at TIMESTAMP,

    FOREIGN KEY (matched_match_id) REFERENCES matches(match_id),
    FOREIGN KEY (first_picker_participant_id) REFERENCES tournament_participants(participant_id),
    FOREIGN KEY (second_picker_participant_id) REFERENCES tournament_participants(participant_id)
);
```

### Updated Table: matches

Adds columns to track pick order for matched games.

```sql
ALTER TABLE matches
ADD COLUMN first_picker_participant_id BIGINT,
ADD COLUMN second_picker_participant_id BIGINT;

ALTER TABLE matches
ADD FOREIGN KEY (first_picker_participant_id)
    REFERENCES tournament_participants(participant_id);

ALTER TABLE matches
ADD FOREIGN KEY (second_picker_participant_id)
    REFERENCES tournament_participants(participant_id);
```

---

## Migration Procedure

### Step 1: Backup Database

```bash
cp data/tournament_data.duckdb data/tournament_data.duckdb.backup_$(date +%Y%m%d_%H%M%S)
```

### Step 2: Apply Schema Changes

Schema changes are applied automatically on next import:

```bash
uv run python scripts/import_attachments.py --directory saves
```

Or run schema initialization directly:

```bash
uv run python -c "
from tournament_visualizer.data.schema import initialize_schema
from tournament_visualizer.config import Config
import duckdb

conn = duckdb.connect(Config.DUCKDB_PATH)
initialize_schema(conn)
conn.close()
print('Schema updated')
"
```

### Step 3: Verify Schema

```bash
uv run duckdb data/tournament_data.duckdb -readonly -c "DESCRIBE pick_order_games"
uv run duckdb data/tournament_data.duckdb -readonly -c "DESCRIBE matches" | grep picker
```

Should show the new columns.

---

## Rollback Procedure

### Rollback SQL

```sql
-- Remove columns from matches table
ALTER TABLE matches DROP COLUMN first_picker_participant_id;
ALTER TABLE matches DROP COLUMN second_picker_participant_id;

-- Drop pick_order_games table
DROP TABLE IF EXISTS pick_order_games;
```

### Rollback Steps

```bash
uv run duckdb data/tournament_data.duckdb << 'EOF'
ALTER TABLE matches DROP COLUMN IF EXISTS first_picker_participant_id;
ALTER TABLE matches DROP COLUMN IF EXISTS second_picker_participant_id;
DROP TABLE IF EXISTS pick_order_games;
EOF
```

Or restore from backup:
```bash
cp data/tournament_data.duckdb.backup_YYYYMMDD_HHMMSS data/tournament_data.duckdb
```

---

## Verification

```bash
# Check table exists
uv run duckdb data/tournament_data.duckdb -readonly -c "SELECT COUNT(*) FROM pick_order_games"

# Check matches columns exist
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT
    first_picker_participant_id,
    second_picker_participant_id
FROM matches
LIMIT 1
"
```

---

## Related Files

**Schema:**
- `tournament_visualizer/data/schema.py` - Table definitions

**Scripts:**
- `scripts/sync_pick_order_data.py` - Fetches and parses sheet data
- `scripts/match_pick_order_games.py` - Matches games to database

**Documentation:**
- `docs/plans/pick-order-integration-implementation-plan.md` - Full implementation plan
- `CLAUDE.md` - Usage documentation

---

## Impact

**Breaking Changes:** None
**Data Loss Risk:** None (new tables/columns only)
**Requires Re-import:** No
**Affects Queries:** Adds new analytics capabilities

---

## Notes

- Schema changes are idempotent (safe to run multiple times)
- Foreign keys ensure referential integrity
- NULL values in matches table columns indicate pick order data not available
- pick_order_games table may have unmatched entries (matched_match_id NULL)
```

3. Update the schema initialization to create the table:

The table will be automatically created by the schema initialization code that already exists.

**Testing:**

```bash
# Apply schema changes
uv run python -c "
from tournament_visualizer.data.schema import initialize_schema
from tournament_visualizer.config import Config
import duckdb

conn = duckdb.connect(Config.DUCKDB_PATH)
initialize_schema(conn)
conn.close()
print('✓ Schema updated')
"

# Verify table exists
uv run duckdb data/tournament_data.duckdb -readonly -c "DESCRIBE pick_order_games"

# Verify matches columns exist
uv run duckdb data/tournament_data.duckdb -readonly -c "DESCRIBE matches" | grep picker
```

**Commit Message:**
```
feat: Add pick_order_games table and matches picker columns

Adds intermediate storage for Google Sheets pick order data and
columns to track first/second picker on matches table.

Includes migration documentation and rollback procedure.
```

---

### Task 4: Create Google Sheets Client Module

**Time Estimate:** 45 minutes

**Objective:** Create a module to fetch data from Google Sheets using the Sheets API.

**Why:** Encapsulate Google Sheets API logic in reusable module (DRY principle). Similar to existing `gdrive_client.py`.

**Files to Create:**
- `tournament_visualizer/data/gsheets_client.py`

**Files to Reference:**
- `tournament_visualizer/data/gdrive_client.py` - Similar API pattern

**Implementation:**

Create `tournament_visualizer/data/gsheets_client.py`:

```python
"""Google Sheets client for accessing tournament data spreadsheets.

This module provides a simple interface to the Google Sheets API for
reading tournament data (e.g., pick order information). Uses API key
authentication since spreadsheets are publicly accessible.

Example:
    >>> from tournament_visualizer.config import Config
    >>> client = GoogleSheetsClient(api_key=Config.GOOGLE_DRIVE_API_KEY)
    >>> data = client.get_sheet_values(
    ...     spreadsheet_id=Config.GOOGLE_SHEETS_SPREADSHEET_ID,
    ...     range_name="GAMEDATA *SPOILER WARNING*!A1:Z200"
    ... )
    >>> print(f"Got {len(data)} rows")
"""

import logging
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GoogleSheetsClient:
    """Client for reading data from Google Sheets.

    Uses API key authentication to access publicly shared spreadsheets.
    No OAuth required.

    Attributes:
        api_key: Google API key with Sheets API enabled
    """

    def __init__(self, api_key: str) -> None:
        """Initialize Google Sheets client.

        Args:
            api_key: Google API key with Sheets API enabled

        Raises:
            ValueError: If api_key is empty
        """
        if not api_key:
            raise ValueError("API key is required")

        self.api_key = api_key
        self._service = None

    def _get_service(self) -> Any:
        """Get or create Sheets API service instance.

        Lazy initialization - only creates service when needed.

        Returns:
            Google Sheets API service instance
        """
        if self._service is None:
            self._service = build('sheets', 'v4', developerKey=self.api_key)
        return self._service

    def get_sheet_values(
        self,
        spreadsheet_id: str,
        range_name: str,
    ) -> list[list[str]]:
        """Get cell values from a spreadsheet range.

        Args:
            spreadsheet_id: The spreadsheet ID (from the URL)
            range_name: The A1 notation range (e.g., "Sheet1!A1:D10")

        Returns:
            List of rows, where each row is a list of cell values.
            Empty cells return as empty strings.
            Rows may have different lengths if trailing cells are empty.

        Raises:
            HttpError: If API request fails (e.g., 404 not found, 403 forbidden)

        Example:
            >>> values = client.get_sheet_values(
            ...     "19t5AbJtQr5kZ62pw8FJ-r2b9LVkz01zl2GUNWkIrhAc",
            ...     "GAMEDATA *SPOILER WARNING*!A1:K100"
            ... )
            >>> print(f"First cell: {values[0][0]}")
        """
        try:
            service = self._get_service()

            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name,
            ).execute()

            values = result.get('values', [])
            logger.info(
                f"Fetched {len(values)} rows from sheet "
                f"(range: {range_name})"
            )

            return values

        except HttpError as e:
            logger.error(
                f"Failed to fetch sheet data: {e.status_code} {e.reason}"
            )
            raise

    def get_sheet_metadata(self, spreadsheet_id: str) -> dict[str, Any]:
        """Get metadata about a spreadsheet.

        Args:
            spreadsheet_id: The spreadsheet ID

        Returns:
            Dictionary with spreadsheet metadata including:
            - properties: Title, locale, timezone
            - sheets: List of sheet metadata (title, gridProperties, etc.)

        Raises:
            HttpError: If API request fails
        """
        try:
            service = self._get_service()

            result = service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()

            logger.info(
                f"Fetched metadata for spreadsheet: {result.get('properties', {}).get('title')}"
            )

            return result

        except HttpError as e:
            logger.error(
                f"Failed to fetch sheet metadata: {e.status_code} {e.reason}"
            )
            raise
```

**Testing:**

Test with real API (manual test):

```bash
# Test fetching sheet data
uv run python -c "
from tournament_visualizer.config import Config
from tournament_visualizer.data.gsheets_client import GoogleSheetsClient

client = GoogleSheetsClient(api_key=Config.GOOGLE_DRIVE_API_KEY)

# Fetch a small range
values = client.get_sheet_values(
    Config.GOOGLE_SHEETS_SPREADSHEET_ID,
    'GAMEDATA *SPOILER WARNING*!A1:K10'
)

print(f'✓ Fetched {len(values)} rows')
for i, row in enumerate(values[:3], 1):
    print(f'  Row {i}: {row[:3]}...')
"
```

Expected output:
```
✓ Fetched 10 rows
  Row 1: ['', '', '']...
  Row 2: ['ROUND 1', '', '']...
  Row 3: ['', '', '']...
```

**Commit Message:**
```
feat: Add GoogleSheetsClient for accessing spreadsheet data

Implements API key-based client for reading data from public Google
Sheets. Uses lazy service initialization and proper error handling.

Similar to gdrive_client.py pattern - reusable for any sheet access.
```

---

### Task 5: Create Sheet Parser Module

**Time Estimate:** 2 hours

**Objective:** Parse the multi-column game layout from the GAMEDATA sheet into structured data.

**Why:** The sheet has a complex layout with multiple games per row, varying row numbers per round, and no fixed column positions. Need robust parsing logic.

**Challenge:** This is the most complex part:
- Round sections have different row offsets
- Game columns are dynamic (not fixed)
- Need to detect "Nation; First Pick" and "Second Pick" rows per round
- Must handle missing data gracefully

**Files to Create:**
- `tournament_visualizer/data/gamedata_parser.py`

**Files to Reference:**
- Screenshots/sheet structure we analyzed earlier

**Implementation Strategy:**

1. **Find round boundaries** by scanning for "ROUND X" pattern in column A
2. **For each round section:**
   - Find the "Nation; First Pick" row
   - Find the "Second Pick" row (next row)
   - Find the "Players" row (above pick rows)
   - Find the "Game Number" row (above players)
3. **For each game column set within the round:**
   - Detect columns by finding values in the "Game Number" row
   - Extract player names from "Players" row
   - Extract first pick nation from "Nation; First Pick" row
   - Extract second pick nation from "Second Pick" row
4. **Determine which player picked which:**
   - Need civilization data from database (compare nations to player civs)
   - OR: assume column position (left player = player1, right = player2)

**Implementation:**

Create `tournament_visualizer/data/gamedata_parser.py`:

```python
"""Parser for Google Sheets GAMEDATA tab tournament data.

This module parses the complex multi-column game layout from the
GAMEDATA sheet and extracts pick order information.

The sheet has a complex structure:
- Multiple rounds, each with different row offsets
- Multiple games per round, spanning columns
- Dynamic game column positions
- Row labels like "Nation; First Pick", "Second Pick", etc.

Example usage:
    >>> from tournament_visualizer.data.gsheets_client import GoogleSheetsClient
    >>> from tournament_visualizer.config import Config
    >>>
    >>> client = GoogleSheetsClient(Config.GOOGLE_DRIVE_API_KEY)
    >>> values = client.get_sheet_values(
    ...     Config.GOOGLE_SHEETS_SPREADSHEET_ID,
    ...     "GAMEDATA *SPOILER WARNING*!A1:Z200"
    ... )
    >>>
    >>> games = parse_gamedata_sheet(values)
    >>> print(f"Parsed {len(games)} games")
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def parse_gamedata_sheet(rows: list[list[str]]) -> list[dict[str, Any]]:
    """Parse the GAMEDATA sheet into structured game data.

    Args:
        rows: Raw sheet data (list of rows, each row is list of cells)

    Returns:
        List of game dictionaries with keys:
        - game_number: Game number from sheet
        - round_number: Round number (1, 2, 3, ...)
        - round_label: Full round label text
        - player1_sheet_name: First player name
        - player2_sheet_name: Second player name
        - first_pick_nation: Nation picked first
        - second_pick_nation: Nation picked second

    Raises:
        ValueError: If sheet structure is invalid or parsing fails
    """
    games = []

    # Find all round sections
    round_sections = find_round_sections(rows)

    logger.info(f"Found {len(round_sections)} round sections")

    for round_info in round_sections:
        try:
            round_games = parse_round_section(rows, round_info)
            games.extend(round_games)
            logger.info(
                f"Parsed {len(round_games)} games from {round_info['label']}"
            )
        except Exception as e:
            logger.error(
                f"Failed to parse round {round_info['label']}: {e}"
            )
            # Continue with other rounds

    logger.info(f"Parsed total of {len(games)} games from sheet")

    return games


def find_round_sections(rows: list[list[str]]) -> list[dict[str, Any]]:
    """Find all round sections in the sheet.

    Scans column A for "ROUND X" pattern to identify round boundaries.

    Args:
        rows: Raw sheet data

    Returns:
        List of round info dictionaries with keys:
        - round_number: Extracted round number (1, 2, 3, ...)
        - label: Full round label text
        - start_row: Row index where round starts
    """
    rounds = []
    round_pattern = re.compile(r'ROUND\s+(\d+)', re.IGNORECASE)

    for row_idx, row in enumerate(rows):
        if not row:
            continue

        # Check column A for round label
        col_a = row[0] if len(row) > 0 else ""

        match = round_pattern.search(col_a)
        if match:
            round_num = int(match.group(1))
            rounds.append({
                "round_number": round_num,
                "label": col_a.strip(),
                "start_row": row_idx,
            })

    return rounds


def parse_round_section(
    rows: list[list[str]],
    round_info: dict[str, Any]
) -> list[dict[str, Any]]:
    """Parse games from a single round section.

    Args:
        rows: Raw sheet data
        round_info: Round metadata from find_round_sections()

    Returns:
        List of game dictionaries for this round

    Raises:
        ValueError: If critical rows not found
    """
    start_row = round_info['start_row']
    round_number = round_info['round_number']
    round_label = round_info['label']

    # Find the key rows within this round section
    # Scan the next ~30 rows after round header
    search_range = rows[start_row:start_row + 30]

    game_number_row_idx = find_row_by_label(search_range, "Game Number")
    players_row_idx = find_row_by_label(search_range, "Players")
    first_pick_row_idx = find_row_by_label(search_range, "Nation; First Pick")
    second_pick_row_idx = find_row_by_label(search_range, "Second Pick")

    if game_number_row_idx is None:
        raise ValueError(f"Could not find 'Game Number' row in round {round_number}")

    if first_pick_row_idx is None:
        raise ValueError(f"Could not find 'Nation; First Pick' row in round {round_number}")

    if second_pick_row_idx is None:
        raise ValueError(f"Could not find 'Second Pick' row in round {round_number}")

    if players_row_idx is None:
        raise ValueError(f"Could not find 'Players' row in round {round_number}")

    # Convert to absolute row indices
    game_number_row_idx += start_row
    players_row_idx += start_row
    first_pick_row_idx += start_row
    second_pick_row_idx += start_row

    # Get the actual row data
    game_number_row = rows[game_number_row_idx]
    players_row = rows[players_row_idx]
    first_pick_row = rows[first_pick_row_idx]
    second_pick_row = rows[second_pick_row_idx]

    # Find game columns by detecting "Game N" in game_number_row
    game_columns = find_game_columns(game_number_row)

    logger.debug(
        f"Round {round_number}: Found {len(game_columns)} games at columns {game_columns}"
    )

    # Parse each game
    games = []

    for col_info in game_columns:
        try:
            game = parse_game_columns(
                game_number_row=game_number_row,
                players_row=players_row,
                first_pick_row=first_pick_row,
                second_pick_row=second_pick_row,
                game_col_start=col_info['col_start'],
                game_col_end=col_info['col_end'],
                round_number=round_number,
                round_label=round_label,
            )

            if game:
                games.append(game)

        except Exception as e:
            logger.warning(
                f"Failed to parse game at columns {col_info['col_start']}-{col_info['col_end']}: {e}"
            )

    return games


def find_row_by_label(
    rows: list[list[str]],
    label: str
) -> int | None:
    """Find row index by searching for label in column A.

    Args:
        rows: List of rows to search
        label: Label text to find (case-insensitive)

    Returns:
        Row index (relative to input rows), or None if not found
    """
    label_lower = label.lower()

    for idx, row in enumerate(rows):
        if not row:
            continue

        col_a = row[0] if len(row) > 0 else ""

        if label_lower in col_a.lower():
            return idx

    return None


def find_game_columns(game_number_row: list[str]) -> list[dict[str, int]]:
    """Find column ranges for each game.

    Detects "Game N" in the row and returns the column span for each game.

    Args:
        game_number_row: The row containing "Game 1", "Game 2", etc.

    Returns:
        List of dicts with keys:
        - game_number: Extracted game number
        - col_start: Starting column index
        - col_end: Ending column index (inclusive)

    Example:
        Row: ["", "", "Game 1", "", "Game 2", "", "", "Game 3"]
        Returns: [
            {"game_number": 1, "col_start": 2, "col_end": 3},
            {"game_number": 2, "col_start": 4, "col_end": 6},
            {"game_number": 3, "col_start": 7, "col_end": ...},
        ]
    """
    games = []
    game_pattern = re.compile(r'Game\s+(\d+)', re.IGNORECASE)

    # Find all columns with "Game N"
    game_starts = []

    for col_idx, cell in enumerate(game_number_row):
        if not cell:
            continue

        match = game_pattern.search(cell)
        if match:
            game_num = int(match.group(1))
            game_starts.append({
                "game_number": game_num,
                "col_start": col_idx,
            })

    # Determine column end for each game
    # Typically 2-3 columns per game (player columns + possible gap)
    for i, game in enumerate(game_starts):
        if i < len(game_starts) - 1:
            # End is just before next game starts
            game['col_end'] = game_starts[i + 1]['col_start'] - 1
        else:
            # Last game - extend a reasonable amount (3 columns)
            game['col_end'] = game['col_start'] + 3

        games.append(game)

    return games


def parse_game_columns(
    game_number_row: list[str],
    players_row: list[str],
    first_pick_row: list[str],
    second_pick_row: list[str],
    game_col_start: int,
    game_col_end: int,
    round_number: int,
    round_label: str,
) -> dict[str, Any] | None:
    """Parse game data from column range.

    Args:
        game_number_row: Row with "Game N" labels
        players_row: Row with "Players" label and player names
        first_pick_row: Row with "Nation; First Pick" label and nation
        second_pick_row: Row with "Second Pick" label and nation
        game_col_start: Starting column index for this game
        game_col_end: Ending column index for this game
        round_number: Round number
        round_label: Full round label text

    Returns:
        Game dictionary, or None if data is incomplete
    """
    # Extract game number from header
    game_number = None
    game_pattern = re.compile(r'Game\s+(\d+)', re.IGNORECASE)

    for col in range(game_col_start, min(game_col_end + 1, len(game_number_row))):
        cell = game_number_row[col] if col < len(game_number_row) else ""
        match = game_pattern.search(cell)
        if match:
            game_number = int(match.group(1))
            break

    if not game_number:
        logger.debug(f"No game number found in columns {game_col_start}-{game_col_end}")
        return None

    # Extract player names (skip label column)
    players = []
    for col in range(game_col_start, min(game_col_end + 1, len(players_row))):
        cell = players_row[col] if col < len(players_row) else ""

        # Skip label column and empty cells
        if cell and "Players" not in cell:
            players.append(cell.strip())

    if len(players) < 2:
        logger.debug(f"Game {game_number}: Found only {len(players)} players")
        return None

    # Extract nations (skip label column)
    first_pick_nation = None
    second_pick_nation = None

    for col in range(game_col_start, min(game_col_end + 1, len(first_pick_row))):
        cell = first_pick_row[col] if col < len(first_pick_row) else ""

        # Skip label column and empty cells
        if cell and "Nation" not in cell and "First Pick" not in cell:
            first_pick_nation = cell.strip()
            break

    for col in range(game_col_start, min(game_col_end + 1, len(second_pick_row))):
        cell = second_pick_row[col] if col < len(second_pick_row) else ""

        # Skip label column and empty cells
        if cell and "Second Pick" not in cell:
            second_pick_nation = cell.strip()
            break

    if not first_pick_nation or not second_pick_nation:
        logger.debug(
            f"Game {game_number}: Missing nation data "
            f"(first={first_pick_nation}, second={second_pick_nation})"
        )
        return None

    return {
        "game_number": game_number,
        "round_number": round_number,
        "round_label": round_label,
        "player1_sheet_name": players[0],
        "player2_sheet_name": players[1] if len(players) > 1 else "",
        "first_pick_nation": first_pick_nation,
        "second_pick_nation": second_pick_nation,
    }
```

**Testing:**

Create a test file `tests/test_gamedata_parser.py`:

```python
"""Tests for GAMEDATA sheet parser."""

import pytest

from tournament_visualizer.data.gamedata_parser import (
    find_game_columns,
    find_row_by_label,
    find_round_sections,
    parse_game_columns,
)


class TestFindRoundSections:
    """Test round section detection."""

    def test_finds_round_1(self) -> None:
        """Finds ROUND 1 header."""
        rows = [
            [""],
            ["ROUND 1"],
            [""],
        ]

        rounds = find_round_sections(rows)

        assert len(rounds) == 1
        assert rounds[0]["round_number"] == 1
        assert rounds[0]["label"] == "ROUND 1"
        assert rounds[0]["start_row"] == 1

    def test_finds_multiple_rounds(self) -> None:
        """Finds multiple round headers."""
        rows = [
            ["ROUND 1"],
            ["", "", ""],
            ["", "", ""],
            ["ROUND 2", "UPPER BRACKET ROUND 2, G21-G28"],
            ["", "", ""],
        ]

        rounds = find_round_sections(rows)

        assert len(rounds) == 2
        assert rounds[0]["round_number"] == 1
        assert rounds[1]["round_number"] == 2
        assert rounds[1]["label"] == "ROUND 2"

    def test_handles_empty_sheet(self) -> None:
        """Returns empty list for empty sheet."""
        rounds = find_round_sections([])
        assert rounds == []


class TestFindRowByLabel:
    """Test row label detection."""

    def test_finds_exact_match(self) -> None:
        """Finds row with exact label match."""
        rows = [
            [""],
            ["Game Number"],
            ["Players"],
        ]

        idx = find_row_by_label(rows, "Game Number")
        assert idx == 1

    def test_finds_case_insensitive(self) -> None:
        """Finds row case-insensitively."""
        rows = [
            ["GAME NUMBER"],
            ["players"],
        ]

        idx = find_row_by_label(rows, "game number")
        assert idx == 0

    def test_finds_partial_match(self) -> None:
        """Finds row with label as substring."""
        rows = [
            ["Nation; First Pick"],
        ]

        idx = find_row_by_label(rows, "First Pick")
        assert idx == 0

    def test_returns_none_if_not_found(self) -> None:
        """Returns None if label not found."""
        rows = [[""], ["Other"], [""]]

        idx = find_row_by_label(rows, "Game Number")
        assert idx is None


class TestFindGameColumns:
    """Test game column detection."""

    def test_finds_single_game(self) -> None:
        """Finds columns for single game."""
        row = ["", "", "Game 1", ""]

        games = find_game_columns(row)

        assert len(games) == 1
        assert games[0]["game_number"] == 1
        assert games[0]["col_start"] == 2

    def test_finds_multiple_games(self) -> None:
        """Finds columns for multiple games."""
        row = ["", "", "Game 1", "", "", "Game 2", ""]

        games = find_game_columns(row)

        assert len(games) == 2
        assert games[0]["game_number"] == 1
        assert games[0]["col_start"] == 2
        assert games[1]["game_number"] == 2
        assert games[1]["col_start"] == 5

    def test_handles_empty_row(self) -> None:
        """Returns empty list for empty row."""
        games = find_game_columns([])
        assert games == []


class TestParseGameColumns:
    """Test game data extraction."""

    def test_parses_complete_game(self) -> None:
        """Parses game with all required data."""
        game_number_row = ["", "", "Game 1", ""]
        players_row = ["Players", "", "Becked", "Anarkos"]
        first_pick_row = ["Nation; First Pick", "", "Assyria", ""]
        second_pick_row = ["Second Pick", "", "", "Persia"]

        game = parse_game_columns(
            game_number_row=game_number_row,
            players_row=players_row,
            first_pick_row=first_pick_row,
            second_pick_row=second_pick_row,
            game_col_start=2,
            game_col_end=4,
            round_number=1,
            round_label="ROUND 1",
        )

        assert game is not None
        assert game["game_number"] == 1
        assert game["round_number"] == 1
        assert game["player1_sheet_name"] == "Becked"
        assert game["player2_sheet_name"] == "Anarkos"
        assert game["first_pick_nation"] == "Assyria"
        assert game["second_pick_nation"] == "Persia"

    def test_returns_none_if_missing_players(self) -> None:
        """Returns None if players missing."""
        game_number_row = ["", "", "Game 1"]
        players_row = ["Players", "", ""]  # Missing players
        first_pick_row = ["Nation; First Pick", "", "Assyria"]
        second_pick_row = ["Second Pick", "", "Persia"]

        game = parse_game_columns(
            game_number_row=game_number_row,
            players_row=players_row,
            first_pick_row=first_pick_row,
            second_pick_row=second_pick_row,
            game_col_start=2,
            game_col_end=3,
            round_number=1,
            round_label="ROUND 1",
        )

        assert game is None

    def test_returns_none_if_missing_nations(self) -> None:
        """Returns None if nations missing."""
        game_number_row = ["", "", "Game 1"]
        players_row = ["Players", "", "Player1", "Player2"]
        first_pick_row = ["Nation; First Pick", "", ""]  # Missing
        second_pick_row = ["Second Pick", "", ""]  # Missing

        game = parse_game_columns(
            game_number_row=game_number_row,
            players_row=players_row,
            first_pick_row=first_pick_row,
            second_pick_row=second_pick_row,
            game_col_start=2,
            game_col_end=4,
            round_number=1,
            round_label="ROUND 1",
        )

        assert game is None
```

Run tests:

```bash
uv run pytest tests/test_gamedata_parser.py -v
```

Should show all tests passing.

**Testing with Real Data:**

```bash
# Test with actual sheet data
uv run python -c "
from tournament_visualizer.config import Config
from tournament_visualizer.data.gsheets_client import GoogleSheetsClient
from tournament_visualizer.data.gamedata_parser import parse_gamedata_sheet

client = GoogleSheetsClient(Config.GOOGLE_DRIVE_API_KEY)

values = client.get_sheet_values(
    Config.GOOGLE_SHEETS_SPREADSHEET_ID,
    'GAMEDATA *SPOILER WARNING*!A1:Z200'
)

games = parse_gamedata_sheet(values)

print(f'✓ Parsed {len(games)} games')
for game in games[:3]:
    print(f\"  Game {game['game_number']}: {game['player1_sheet_name']} vs {game['player2_sheet_name']}\")
    print(f\"    First pick: {game['first_pick_nation']}, Second pick: {game['second_pick_nation']}\")
"
```

Expected output:
```
✓ Parsed 40+ games
  Game 1: Becked vs Anarkos
    First pick: Assyria, Second pick: Persia
  Game 2: Mojo vs Fiddlers25
    First pick: Egypt, Second pick: Greece
  ...
```

**Commit Message:**
```
feat: Add GAMEDATA sheet parser

Parses multi-column game layout from Google Sheets to extract:
- Game numbers and round information
- Player names
- First/second pick nations

Handles dynamic row offsets and column positions. Includes
comprehensive test coverage for edge cases.
```

---

### Task 6: Create Pick Order Sync Script

**Time Estimate:** 1 hour 30 minutes

**Objective:** Create script to fetch sheet data, parse it, and store in `pick_order_games` table.

**Why:** This is the main entry point for syncing pick order data from the sheet.

**Files to Create:**
- `scripts/sync_pick_order_data.py`

**Files to Reference:**
- `scripts/sync_challonge_participants.py` - Similar sync pattern
- `scripts/download_attachments.py` - Similar error handling

**Implementation:**

Create `scripts/sync_pick_order_data.py`:

```python
#!/usr/bin/env python3
"""Sync pick order data from Google Sheets to database.

This script:
1. Fetches GAMEDATA sheet from Google Sheets
2. Parses the multi-column game layout
3. Stores parsed data in pick_order_games table
4. Does NOT match to matches table (separate script handles that)

Usage:
    python scripts/sync_pick_order_data.py [--dry-run] [--verbose]

Examples:
    # Sync pick order data (default)
    python scripts/sync_pick_order_data.py

    # See what would be synced without writing
    python scripts/sync_pick_order_data.py --dry-run

    # Verbose logging
    python scripts/sync_pick_order_data.py --verbose
"""

import argparse
import logging
import sys
from pathlib import Path

import duckdb
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tournament_visualizer.config import Config
from tournament_visualizer.data.gamedata_parser import parse_gamedata_sheet
from tournament_visualizer.data.gsheets_client import GoogleSheetsClient

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def sync_pick_order_data(dry_run: bool = False) -> None:
    """Fetch and sync pick order data from Google Sheets.

    Args:
        dry_run: If True, don't write to database

    Raises:
        ValueError: If configuration is invalid
        Exception: If sync fails
    """
    # Verify configuration
    if not Config.GOOGLE_DRIVE_API_KEY:
        raise ValueError(
            "GOOGLE_DRIVE_API_KEY not set. "
            "Add it to .env file to access Google Sheets."
        )

    if not Config.GOOGLE_SHEETS_SPREADSHEET_ID:
        raise ValueError("GOOGLE_SHEETS_SPREADSHEET_ID not set")

    logger.info("Fetching pick order data from Google Sheets...")
    logger.info(f"  Spreadsheet: {Config.GOOGLE_SHEETS_SPREADSHEET_ID}")
    logger.info(f"  Sheet GID: {Config.GOOGLE_SHEETS_GAMEDATA_GID}")

    # Initialize Google Sheets client
    client = GoogleSheetsClient(api_key=Config.GOOGLE_DRIVE_API_KEY)

    # Fetch sheet data
    # Use a large range to capture all data (adjust if needed)
    range_name = f"GAMEDATA *SPOILER WARNING*!A1:Z200"

    logger.info(f"Fetching range: {range_name}")

    try:
        values = client.get_sheet_values(
            spreadsheet_id=Config.GOOGLE_SHEETS_SPREADSHEET_ID,
            range_name=range_name,
        )
    except Exception as e:
        logger.error(f"Failed to fetch sheet data: {e}")
        raise

    logger.info(f"✓ Fetched {len(values)} rows from sheet")

    # Parse sheet data
    logger.info("Parsing game data...")

    try:
        games = parse_gamedata_sheet(values)
    except Exception as e:
        logger.error(f"Failed to parse sheet: {e}")
        raise

    logger.info(f"✓ Parsed {len(games)} games")

    if not games:
        logger.warning("No games found in sheet - nothing to sync")
        return

    # Show sample of parsed data
    logger.info("\nSample of parsed games:")
    for game in games[:3]:
        logger.info(
            f"  Game {game['game_number']} (Round {game['round_number']}): "
            f"{game['player1_sheet_name']} vs {game['player2_sheet_name']}"
        )
        logger.info(
            f"    First: {game['first_pick_nation']}, "
            f"Second: {game['second_pick_nation']}"
        )

    if dry_run:
        logger.info("\n[DRY RUN] Would sync %d games to database", len(games))
        return

    # Write to database
    logger.info(f"\nWriting {len(games)} games to database...")

    conn = duckdb.connect(Config.DUCKDB_PATH)

    try:
        # Clear existing data (full replace)
        conn.execute("DELETE FROM pick_order_games")
        logger.info("✓ Cleared existing pick_order_games data")

        # Insert new data
        insert_sql = """
        INSERT INTO pick_order_games (
            game_number,
            round_number,
            round_label,
            player1_sheet_name,
            player2_sheet_name,
            first_pick_nation,
            second_pick_nation
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """

        for game in games:
            conn.execute(
                insert_sql,
                [
                    game['game_number'],
                    game['round_number'],
                    game['round_label'],
                    game['player1_sheet_name'],
                    game['player2_sheet_name'],
                    game['first_pick_nation'],
                    game['second_pick_nation'],
                ],
            )

        logger.info(f"✓ Inserted {len(games)} games")

        # Show stats
        result = conn.execute("""
            SELECT
                COUNT(*) as total_games,
                COUNT(DISTINCT round_number) as total_rounds,
                MIN(game_number) as min_game,
                MAX(game_number) as max_game
            FROM pick_order_games
        """).fetchone()

        logger.info("\nDatabase statistics:")
        logger.info(f"  Total games: {result[0]}")
        logger.info(f"  Total rounds: {result[1]}")
        logger.info(f"  Game number range: {result[2]}-{result[3]}")

        # Show unmatched games (should be all at this point)
        unmatched = conn.execute("""
            SELECT COUNT(*)
            FROM pick_order_games
            WHERE matched_match_id IS NULL
        """).fetchone()[0]

        logger.info(f"  Unmatched games: {unmatched}")
        logger.info(
            "  (Run match_pick_order_games.py to link to matches table)"
        )

    finally:
        conn.close()

    logger.info("\n✓ Pick order data sync complete")


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Sync pick order data from Google Sheets"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing to database",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    setup_logging(args.verbose)

    try:
        sync_pick_order_data(dry_run=args.dry_run)
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Testing:**

```bash
# Test with dry run
uv run python scripts/sync_pick_order_data.py --dry-run --verbose

# Should show:
# - Fetched N rows
# - Parsed M games
# - Sample games
# - "[DRY RUN] Would sync M games"

# Actual sync
uv run python scripts/sync_pick_order_data.py --verbose

# Verify data
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT
    game_number,
    round_number,
    player1_sheet_name,
    player2_sheet_name,
    first_pick_nation,
    second_pick_nation
FROM pick_order_games
ORDER BY game_number
LIMIT 10
"
```

Expected: Games successfully synced to database.

**Commit Message:**
```
feat: Add pick order data sync script

Fetches GAMEDATA sheet from Google Sheets, parses game data, and
stores in pick_order_games table. Does not match to matches table
(separate step).

Includes dry-run mode for safe testing.
```

---

### Task 7: Create Pick Order Matching Script

**Time Estimate:** 1 hour 30 minutes

**Objective:** Match games from `pick_order_games` to `matches` table using player names and determine which player picked first.

**Why:** This is the critical matching logic that links sheet data to database matches.

**Challenge:**
- Must match by player names (no match IDs in sheet)
- Player names may not match exactly (use normalized names)
- Must determine which player picked which nation (compare to save file civilizations)
- Handle unmatched games gracefully

**Files to Create:**
- `scripts/match_pick_order_games.py`

**Files to Reference:**
- `scripts/link_players_to_participants.py` - Similar matching pattern
- `tournament_visualizer/data/name_normalizer.py` - Name normalization

**Implementation:**

Create `scripts/match_pick_order_games.py`:

```python
#!/usr/bin/env python3
"""Match pick_order_games to matches table and update picker columns.

This script:
1. Reads games from pick_order_games table
2. Matches each game to matches table using:
   - Player names (normalized) + round number
   - OR manual overrides from pick_order_overrides.json
3. Determines which player picked first by comparing nations to save file civs
4. Updates pick_order_games with match info
5. Updates matches table with picker participant IDs

Usage:
    python scripts/match_pick_order_games.py [--dry-run] [--verbose]

Examples:
    # Match pick order games
    python scripts/match_pick_order_games.py

    # Preview matches without writing
    python scripts/match_pick_order_games.py --dry-run

    # Verbose logging
    python scripts/match_pick_order_games.py --verbose
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import duckdb
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tournament_visualizer.config import Config
from tournament_visualizer.data.name_normalizer import normalize_name

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def load_pick_order_overrides(
    override_path: Path = Path("data/pick_order_overrides.json")
) -> dict:
    """Load manual pick order match overrides.

    Args:
        override_path: Path to overrides JSON file

    Returns:
        Dictionary mapping game_number (str) to match_id (int)
    """
    if not override_path.exists():
        logger.debug(f"No overrides file found at {override_path}")
        return {}

    try:
        with open(override_path) as f:
            data = json.load(f)

        # Convert game_number keys to int
        overrides = {}
        for game_str, info in data.items():
            try:
                game_num = int(game_str.replace("game_", ""))
                match_id = info.get("challonge_match_id")
                if match_id:
                    overrides[game_num] = match_id
                    logger.debug(
                        f"Override: game {game_num} → match {match_id}"
                    )
            except (ValueError, KeyError) as e:
                logger.warning(f"Invalid override entry '{game_str}': {e}")

        logger.info(f"Loaded {len(overrides)} pick order overrides")
        return overrides

    except Exception as e:
        logger.error(f"Failed to load overrides: {e}")
        return {}


def match_games_to_matches(dry_run: bool = False) -> None:
    """Match pick order games to matches table.

    Args:
        dry_run: If True, don't write to database

    Raises:
        Exception: If matching fails
    """
    logger.info("Matching pick order games to matches...")

    # Load overrides
    overrides = load_pick_order_overrides()

    conn = duckdb.connect(Config.DUCKDB_PATH)

    try:
        # Get all unmatched pick order games
        games = conn.execute("""
            SELECT
                game_number,
                round_number,
                player1_sheet_name,
                player2_sheet_name,
                first_pick_nation,
                second_pick_nation
            FROM pick_order_games
            WHERE matched_match_id IS NULL
            ORDER BY game_number
        """).fetchall()

        logger.info(f"Found {len(games)} unmatched games")

        if not games:
            logger.info("No games to match")
            return

        matched = 0
        failed = 0

        for game in games:
            game_num, round_num, p1_name, p2_name, first_nation, second_nation = game

            logger.debug(f"\nMatching game {game_num}: {p1_name} vs {p2_name}")

            # Check for manual override
            if game_num in overrides:
                match_id = overrides[game_num]
                logger.info(
                    f"  Using override: game {game_num} → match {match_id}"
                )

                match_result = conn.execute("""
                    SELECT
                        m.match_id,
                        p1.player_id as p1_id,
                        p1.player_name as p1_name,
                        p1.civilization as p1_civ,
                        p1.participant_id as p1_participant,
                        p2.player_id as p2_id,
                        p2.player_name as p2_name,
                        p2.civilization as p2_civ,
                        p2.participant_id as p2_participant
                    FROM matches m
                    JOIN players p1 ON m.match_id = p1.match_id AND p1.player_id = 1
                    JOIN players p2 ON m.match_id = p2.match_id AND p2.player_id = 2
                    WHERE m.match_id = ?
                """, [match_id]).fetchone()

                if not match_result:
                    logger.warning(
                        f"  ❌ Override match {match_id} not found in database"
                    )
                    failed += 1
                    continue

                confidence = "manual_override"
                reason = f"Manual override to match {match_id}"

            else:
                # Match by player names (normalized)
                p1_norm = normalize_name(p1_name)
                p2_norm = normalize_name(p2_name)

                logger.debug(f"  Normalized: '{p1_norm}' vs '{p2_norm}'")

                # Try both orderings (player1/player2 may be swapped)
                match_result = conn.execute("""
                    SELECT
                        m.match_id,
                        p1.player_id as p1_id,
                        p1.player_name as p1_name,
                        p1.civilization as p1_civ,
                        p1.participant_id as p1_participant,
                        p2.player_id as p2_id,
                        p2.player_name as p2_name,
                        p2.civilization as p2_civ,
                        p2.participant_id as p2_participant
                    FROM matches m
                    JOIN players p1 ON m.match_id = p1.match_id AND p1.player_id = 1
                    JOIN players p2 ON m.match_id = p2.match_id AND p2.player_id = 2
                    WHERE (
                        (p1.player_name_normalized = ? AND p2.player_name_normalized = ?)
                        OR
                        (p1.player_name_normalized = ? AND p2.player_name_normalized = ?)
                    )
                """, [p1_norm, p2_norm, p2_norm, p1_norm]).fetchone()

                if not match_result:
                    logger.warning(
                        f"  ❌ No match found for '{p1_name}' vs '{p2_name}'"
                    )
                    failed += 1
                    continue

                confidence = "normalized"
                reason = f"Matched by normalized names"

            # Extract match data
            (
                match_id,
                db_p1_id, db_p1_name, db_p1_civ, db_p1_participant,
                db_p2_id, db_p2_name, db_p2_civ, db_p2_participant
            ) = match_result

            logger.debug(
                f"  Found match {match_id}: {db_p1_name} ({db_p1_civ}) vs "
                f"{db_p2_name} ({db_p2_civ})"
            )

            # Determine which player picked first by matching nations
            # Compare first_pick_nation to player civilizations
            first_picker_participant = None
            second_picker_participant = None
            first_picker_sheet_name = None
            second_picker_sheet_name = None

            if db_p1_civ == first_nation:
                # Player 1 picked first
                first_picker_participant = db_p1_participant
                second_picker_participant = db_p2_participant
                first_picker_sheet_name = p1_name
                second_picker_sheet_name = p2_name
                logger.debug(
                    f"  → {db_p1_name} picked {first_nation} first, "
                    f"{db_p2_name} picked {second_nation} second"
                )
            elif db_p2_civ == first_nation:
                # Player 2 picked first
                first_picker_participant = db_p2_participant
                second_picker_participant = db_p1_participant
                first_picker_sheet_name = p2_name
                second_picker_sheet_name = p1_name
                logger.debug(
                    f"  → {db_p2_name} picked {first_nation} first, "
                    f"{db_p1_name} picked {second_nation} second"
                )
            else:
                logger.warning(
                    f"  ⚠️  Nation mismatch: first_pick={first_nation}, "
                    f"but players are {db_p1_civ}/{db_p2_civ}"
                )
                failed += 1
                continue

            # Validate second picker nation matches
            if db_p1_civ == second_nation or db_p2_civ == second_nation:
                pass  # OK
            else:
                logger.warning(
                    f"  ⚠️  Second pick nation '{second_nation}' doesn't "
                    f"match either player"
                )

            if not first_picker_participant or not second_picker_participant:
                logger.warning(
                    f"  ⚠️  Players not linked to participants "
                    f"(run link_players_to_participants.py first)"
                )
                failed += 1
                continue

            # Update database
            if not dry_run:
                # Update pick_order_games
                conn.execute("""
                    UPDATE pick_order_games
                    SET
                        matched_match_id = ?,
                        first_picker_sheet_name = ?,
                        second_picker_sheet_name = ?,
                        first_picker_participant_id = ?,
                        second_picker_participant_id = ?,
                        match_confidence = ?,
                        match_reason = ?,
                        matched_at = ?
                    WHERE game_number = ?
                """, [
                    match_id,
                    first_picker_sheet_name,
                    second_picker_sheet_name,
                    first_picker_participant,
                    second_picker_participant,
                    confidence,
                    reason,
                    datetime.now(),
                    game_num,
                ])

                # Update matches
                conn.execute("""
                    UPDATE matches
                    SET
                        first_picker_participant_id = ?,
                        second_picker_participant_id = ?
                    WHERE match_id = ?
                """, [
                    first_picker_participant,
                    second_picker_participant,
                    match_id,
                ])

            logger.info(
                f"  ✓ Matched game {game_num} → match {match_id} "
                f"(first picker: participant {first_picker_participant})"
            )
            matched += 1

        logger.info("\n" + "=" * 70)
        logger.info(f"Matching complete:")
        logger.info(f"  Total games: {len(games)}")
        logger.info(f"  Successfully matched: {matched}")
        logger.info(f"  Failed to match: {failed}")

        if failed > 0:
            logger.info(
                "\nTip: Add failed games to data/pick_order_overrides.json"
            )

        if dry_run:
            logger.info("\n[DRY RUN] No changes written to database")

    finally:
        conn.close()


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Match pick order games to matches table"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview matches without writing to database",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    setup_logging(args.verbose)

    try:
        load_dotenv()
        match_games_to_matches(dry_run=args.dry_run)
    except Exception as e:
        logger.error(f"Matching failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Testing:**

```bash
# Prerequisites: Must have players linked to participants
uv run python scripts/link_players_to_participants.py

# Test with dry run
uv run python scripts/match_pick_order_games.py --dry-run --verbose

# Should show:
# - Found N unmatched games
# - Matching attempts for each
# - Match success/failure
# - "[DRY RUN] No changes written"

# Actual matching
uv run python scripts/match_pick_order_games.py --verbose

# Verify matches
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT
    pog.game_number,
    pog.matched_match_id,
    pog.match_confidence,
    pog.first_picker_sheet_name,
    pog.second_picker_sheet_name
FROM pick_order_games pog
WHERE matched_match_id IS NOT NULL
ORDER BY game_number
LIMIT 10
"

# Check matches table updated
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT
    match_id,
    first_picker_participant_id,
    second_picker_participant_id
FROM matches
WHERE first_picker_participant_id IS NOT NULL
LIMIT 10
"
```

Expected: Most/all games successfully matched.

**Commit Message:**
```
feat: Add pick order game matching script

Matches pick_order_games to matches table using normalized player
names. Determines which player picked first by comparing nations to
save file civilizations. Updates both tables with match results.

Supports manual overrides via pick_order_overrides.json.
```

---

### Task 8: Integrate into Sync Workflow

**Time Estimate:** 30 minutes

**Objective:** Add pick order sync and matching to the production sync script.

**Why:** Production deployments should automatically sync pick order data without manual intervention.

**Files to Modify:**
- `scripts/sync_tournament_data.sh`

**Changes:**

Add after participant linking (around line 120):

```bash
# Step 4.5: Sync pick order data from Google Sheets (if configured)
if [ -n "${GOOGLE_DRIVE_API_KEY}" ] && [ -n "${GOOGLE_SHEETS_SPREADSHEET_ID}" ]; then
    echo -e "${YELLOW}[4.5/6] Syncing pick order data from Google Sheets...${NC}"
    if uv run python scripts/sync_pick_order_data.py; then
        echo -e "${GREEN}✓ Pick order data synced${NC}"

        echo -e "${YELLOW}[4.6/6] Matching pick order games to matches...${NC}"
        if uv run python scripts/match_pick_order_games.py; then
            echo -e "${GREEN}✓ Pick order games matched${NC}"
        else
            echo -e "${YELLOW}⚠ Pick order matching failed (non-critical)${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ Pick order sync failed (will skip)${NC}"
    fi
    echo ""
else
    echo -e "${BLUE}[4.5/6] Skipping pick order sync (API key or spreadsheet ID not configured)${NC}"
    echo ""
fi
```

**Testing:**

```bash
# Test locally first (don't deploy)
./scripts/sync_tournament_data.sh --dry-run

# Then test actual sync (be careful - this deploys!)
# Only run if you're confident it's working
```

**Commit Message:**
```
feat: Add pick order sync to production workflow

Production sync now:
1. Syncs pick order data from Google Sheets (if configured)
2. Matches games to database matches automatically
3. Falls back gracefully if not configured

Ensures production always has latest pick order data without
manual intervention.
```

---

### Task 9: Create Override File Examples

**Time Estimate:** 15 minutes

**Objective:** Create example override file for games that can't auto-match.

**Why:** Some games will fail to match (name mismatches, nation mismatches). Need manual override system.

**Files to Create:**
- `data/pick_order_overrides.json.example`

**Implementation:**

Create `data/pick_order_overrides.json.example`:

```json
{
  "_comment": "Manual overrides for pick order games that can't auto-match",
  "_instructions": [
    "1. Copy this file to pick_order_overrides.json (not in git)",
    "2. Add entries for games that failed to match",
    "3. Re-run: uv run python scripts/match_pick_order_games.py",
    "4. For production: ./scripts/sync_tournament_data.sh"
  ],
  "_format": {
    "game_NUMBER": {
      "challonge_match_id": "The database match_id to link to",
      "reason": "Why this override is needed",
      "date_added": "YYYY-MM-DD",
      "notes": "Optional additional context"
    }
  },
  "_examples": {
    "game_1": {
      "challonge_match_id": 426504734,
      "reason": "Player name mismatch: sheet has 'Ninja', save has 'Ninjaa'",
      "date_added": "2025-10-17",
      "notes": "Verified with TO that this is correct match"
    },
    "game_15": {
      "challonge_match_id": 426504999,
      "reason": "Nation mismatch: player changed civ after draft",
      "date_added": "2025-10-17"
    }
  }
}
```

Add to `.gitignore`:

```bash
# Pick order override files (contain manual corrections)
data/pick_order_overrides.json
```

**Testing:**

```bash
# Create test override file
cp data/pick_order_overrides.json.example data/pick_order_overrides.json

# Edit to add actual failing games
# Then test
uv run python scripts/match_pick_order_games.py --verbose

# Should see "Using override" messages
```

**Commit Message:**
```
feat: Add pick order override file example

Provides template for manual overrides when games can't auto-match.
Includes format documentation and usage examples.

Override file is gitignored - each deployment maintains its own.
```

---

### Task 10: Add Pick Order Analytics Queries

**Time Estimate:** 1 hour

**Objective:** Create example analytics queries for pick order analysis.

**Why:** The whole point is to enable analysis - provide starting point queries.

**Files to Create:**
- `scripts/pick_order_analytics_examples.sql`

**Implementation:**

Create `scripts/pick_order_analytics_examples.sql`:

```sql
-- Pick Order Analytics Example Queries
--
-- Run these queries to analyze pick order impact on game outcomes.
-- Use with: uv run duckdb data/tournament_data.duckdb -readonly < scripts/pick_order_analytics_examples.sql

-- ==============================================================================
-- Query 1: Overall Pick Order Win Rate
-- ==============================================================================
-- Does first picker win more often than second picker?

SELECT
    CASE
        WHEN m.winner_participant_id = m.first_picker_participant_id
        THEN 'First Pick'
        ELSE 'Second Pick'
    END as pick_position,
    COUNT(*) as games_won,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM matches WHERE first_picker_participant_id IS NOT NULL AND winner_participant_id IS NOT NULL), 1) as win_rate_pct
FROM matches m
WHERE
    m.first_picker_participant_id IS NOT NULL
    AND m.winner_participant_id IS NOT NULL
GROUP BY pick_position
ORDER BY win_rate_pct DESC;

-- ==============================================================================
-- Query 2: Pick Order Win Rate by Nation
-- ==============================================================================
-- Which nations perform better when picked first vs second?

WITH game_outcomes AS (
    SELECT
        p.civilization,
        CASE
            WHEN p.participant_id = m.first_picker_participant_id
            THEN 'First'
            ELSE 'Second'
        END as pick_position,
        CASE
            WHEN m.winner_participant_id = p.participant_id
            THEN 1
            ELSE 0
        END as won
    FROM matches m
    JOIN players p ON m.match_id = p.match_id
    WHERE
        m.first_picker_participant_id IS NOT NULL
        AND m.winner_participant_id IS NOT NULL
        AND p.participant_id IN (m.first_picker_participant_id, m.second_picker_participant_id)
)
SELECT
    civilization,
    pick_position,
    COUNT(*) as times_picked,
    SUM(won) as wins,
    ROUND(SUM(won) * 100.0 / COUNT(*), 1) as win_rate_pct
FROM game_outcomes
GROUP BY civilization, pick_position
HAVING COUNT(*) >= 3  -- Only show nations picked 3+ times in that position
ORDER BY civilization, pick_position;

-- ==============================================================================
-- Query 3: First Pick Nation Frequency
-- ==============================================================================
-- Which nations are picked first most often?

SELECT
    pog.first_pick_nation as nation,
    COUNT(*) as times_picked_first,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM pick_order_games WHERE matched_match_id IS NOT NULL), 1) as pick_rate_pct
FROM pick_order_games pog
WHERE pog.matched_match_id IS NOT NULL
GROUP BY pog.first_pick_nation
ORDER BY times_picked_first DESC;

-- ==============================================================================
-- Query 4: Counter-Pick Analysis
-- ==============================================================================
-- When nation X is picked first, what's picked second most often?

SELECT
    pog.first_pick_nation,
    pog.second_pick_nation,
    COUNT(*) as times_paired,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY pog.first_pick_nation), 1) as pct_of_first_pick
FROM pick_order_games pog
WHERE pog.matched_match_id IS NOT NULL
GROUP BY pog.first_pick_nation, pog.second_pick_nation
HAVING COUNT(*) >= 2  -- Show pairings that happened 2+ times
ORDER BY pog.first_pick_nation, times_paired DESC;

-- ==============================================================================
-- Query 5: Counter-Pick Success Rate
-- ==============================================================================
-- Do certain second picks beat certain first picks more often?

WITH matchups AS (
    SELECT
        pog.first_pick_nation,
        pog.second_pick_nation,
        CASE
            WHEN m.winner_participant_id = m.second_picker_participant_id
            THEN 1
            ELSE 0
        END as second_won
    FROM pick_order_games pog
    JOIN matches m ON pog.matched_match_id = m.match_id
    WHERE
        pog.matched_match_id IS NOT NULL
        AND m.winner_participant_id IS NOT NULL
)
SELECT
    first_pick_nation,
    second_pick_nation,
    COUNT(*) as games,
    SUM(second_won) as second_wins,
    ROUND(SUM(second_won) * 100.0 / COUNT(*), 1) as second_win_rate_pct
FROM matchups
GROUP BY first_pick_nation, second_pick_nation
HAVING COUNT(*) >= 3  -- Only show matchups with 3+ games
ORDER BY second_win_rate_pct DESC;

-- ==============================================================================
-- Query 6: Player Pick Order Preferences
-- ==============================================================================
-- How often do players get first pick vs second pick?

WITH pick_counts AS (
    SELECT
        tp.display_name as player,
        COUNT(CASE WHEN m.first_picker_participant_id = tp.participant_id THEN 1 END) as times_first,
        COUNT(CASE WHEN m.second_picker_participant_id = tp.participant_id THEN 1 END) as times_second,
        COUNT(*) as total_games
    FROM tournament_participants tp
    JOIN matches m ON
        tp.participant_id IN (m.first_picker_participant_id, m.second_picker_participant_id)
    WHERE m.first_picker_participant_id IS NOT NULL
    GROUP BY tp.participant_id, tp.display_name
)
SELECT
    player,
    total_games,
    times_first,
    times_second,
    ROUND(times_first * 100.0 / total_games, 1) as first_pick_rate_pct
FROM pick_counts
WHERE total_games >= 3  -- Only show players with 3+ games
ORDER BY total_games DESC, first_pick_rate_pct DESC;

-- ==============================================================================
-- Query 7: Player Win Rate by Pick Position
-- ==============================================================================
-- Do certain players perform better with first vs second pick?

WITH player_picks AS (
    SELECT
        tp.display_name as player,
        CASE
            WHEN m.first_picker_participant_id = tp.participant_id
            THEN 'First'
            ELSE 'Second'
        END as pick_position,
        CASE
            WHEN m.winner_participant_id = tp.participant_id
            THEN 1
            ELSE 0
        END as won
    FROM tournament_participants tp
    JOIN matches m ON
        tp.participant_id IN (m.first_picker_participant_id, m.second_picker_participant_id)
    WHERE
        m.first_picker_participant_id IS NOT NULL
        AND m.winner_participant_id IS NOT NULL
)
SELECT
    player,
    pick_position,
    COUNT(*) as games,
    SUM(won) as wins,
    ROUND(SUM(won) * 100.0 / COUNT(*), 1) as win_rate_pct
FROM player_picks
GROUP BY player, pick_position
HAVING COUNT(*) >= 2  -- Only show if they picked in that position 2+ times
ORDER BY player, pick_position;

-- ==============================================================================
-- Query 8: Average Game Length by Pick Order
-- ==============================================================================
-- Do games end faster when first picker wins vs second picker wins?

SELECT
    CASE
        WHEN m.winner_participant_id = m.first_picker_participant_id
        THEN 'First Pick Won'
        ELSE 'Second Pick Won'
    END as outcome,
    COUNT(*) as games,
    ROUND(AVG(m.total_turns), 1) as avg_turns,
    MIN(m.total_turns) as min_turns,
    MAX(m.total_turns) as max_turns
FROM matches m
WHERE
    m.first_picker_participant_id IS NOT NULL
    AND m.winner_participant_id IS NOT NULL
    AND m.total_turns IS NOT NULL
GROUP BY outcome;

-- ==============================================================================
-- Query 9: Data Quality Check
-- ==============================================================================
-- How many games have pick order data vs don't?

SELECT
    'Total Matches' as metric,
    COUNT(*) as count
FROM matches
UNION ALL
SELECT
    'Matches with Pick Order Data' as metric,
    COUNT(*) as count
FROM matches
WHERE first_picker_participant_id IS NOT NULL
UNION ALL
SELECT
    'Pick Order Coverage %' as metric,
    ROUND(
        (SELECT COUNT(*) FROM matches WHERE first_picker_participant_id IS NOT NULL) * 100.0 /
        (SELECT COUNT(*) FROM matches),
        1
    ) as count;

-- ==============================================================================
-- Query 10: Unmatched Games Report
-- ==============================================================================
-- Which games from the sheet didn't match to database?

SELECT
    pog.game_number,
    pog.round_label,
    pog.player1_sheet_name,
    pog.player2_sheet_name,
    pog.first_pick_nation,
    pog.second_pick_nation
FROM pick_order_games pog
WHERE pog.matched_match_id IS NULL
ORDER BY pog.game_number;
```

**Testing:**

```bash
# Run all queries
uv run duckdb data/tournament_data.duckdb -readonly < scripts/pick_order_analytics_examples.sql

# Run specific query
uv run duckdb data/tournament_data.duckdb -readonly -c "
-- Query 1 copied here
"
```

**Commit Message:**
```
docs: Add pick order analytics example queries

Provides 10 example SQL queries for analyzing pick order impact:
- Overall win rates by pick position
- Nation performance by pick order
- Counter-pick patterns and success rates
- Player preferences and performance
- Data quality checks

Ready to use for tournament analysis.
```

---

### Task 11: Update Documentation

**Time Estimate:** 45 minutes

**Objective:** Document the pick order integration in CLAUDE.md for future developers and users.

**Files to Modify:**
- `CLAUDE.md`

**Changes:**

Add new section after "Participant Name Overrides":

```markdown
## Pick Order Data Integration

### Overview

Tournament games have a draft phase where one player picks their nation first, then the other player picks second. Save files don't capture this information (both nations show as chosen on turn 1), so we integrate pick order data from a Google Sheet maintained by the tournament organizer.

**Data Sources:**
1. **Save files** - Contain nations played and game outcomes
2. **Google Sheet (GAMEDATA tab)** - Contains pick order information

**Use Cases:**
- Does picking first or second affect win rate?
- Which nations are picked first most often?
- Counter-pick analysis (what beats what?)
- Player pick order preferences

### Database Schema

**`pick_order_games` table** - Stores parsed sheet data:
- Game number, round, player names from sheet
- First/second pick nations
- Matching metadata (match_id, confidence, etc.)

**`matches` table additions:**
- `first_picker_participant_id` - Who picked first
- `second_picker_participant_id` - Who picked second

### Workflow

The pick order integration is automatic during full sync:

```bash
# Full sync (includes pick order)
./scripts/sync_tournament_data.sh
```

Or run manually:

```bash
# 1. Fetch and parse sheet data
uv run python scripts/sync_pick_order_data.py

# 2. Match games to database
uv run python scripts/match_pick_order_games.py
```

### Configuration

**.env variables:**
```bash
# Same API key used for Google Drive
GOOGLE_DRIVE_API_KEY=your_api_key_here

# Spreadsheet ID (from sheet URL)
GOOGLE_SHEETS_SPREADSHEET_ID=19t5AbJtQr5kZ62pw8FJ-r2b9LVkz01zl2GUNWkIrhAc

# Sheet GID (optional, has default)
GOOGLE_SHEETS_GAMEDATA_GID=1663493966
```

**For production (Fly.io):**
```bash
# API key is already set for GDrive
# Just add spreadsheet ID if different
fly secrets set GOOGLE_SHEETS_SPREADSHEET_ID="id" -a prospector
```

### Manual Overrides

Some games may fail to auto-match (name mismatches, nation mismatches). Create manual overrides:

1. Copy example file:
   ```bash
   cp data/pick_order_overrides.json.example data/pick_order_overrides.json
   ```

2. Add override entries for failing games:
   ```json
   {
     "game_1": {
       "challonge_match_id": 426504734,
       "reason": "Player name mismatch: sheet has 'Ninja', save has 'Ninjaa'",
       "date_added": "2025-10-17"
     }
   }
   ```

3. Re-run matching:
   ```bash
   uv run python scripts/match_pick_order_games.py
   ```

### Analytics

Example queries available in `scripts/pick_order_analytics_examples.sql`:

```bash
# Run all examples
uv run duckdb data/tournament_data.duckdb -readonly < scripts/pick_order_analytics_examples.sql
```

**Query examples:**
- Overall pick order win rate
- Nation performance by pick position
- Counter-pick patterns
- Player pick preferences
- Data quality checks

### Troubleshooting

**No pick order data synced:**
- Check `GOOGLE_DRIVE_API_KEY` is set
- Verify `GOOGLE_SHEETS_SPREADSHEET_ID` is correct
- Check sheet is publicly readable

**Low match rate:**
- Check player names in sheet vs save files (use `validate_participants.py`)
- Add overrides to `data/pick_order_overrides.json`
- Run matching with `--verbose` flag to see why matches fail

**Nation mismatches:**
- Verify nations in sheet match civilization names exactly:
  - Correct: "Assyria", "Egypt", "Persia"
  - Incorrect: "ASSYRIA", "egyptian", "Persians"
- Check if player changed nation after draft (needs override)

**Check data quality:**
```bash
# See how many games have pick order data
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT
    COUNT(*) as total_matches,
    COUNT(first_picker_participant_id) as with_pick_order,
    ROUND(COUNT(first_picker_participant_id) * 100.0 / COUNT(*), 1) as coverage_pct
FROM matches
"
```

### Files

**Data:**
- `data/pick_order_overrides.json` - Manual match overrides (not in git)
- `data/pick_order_overrides.json.example` - Override file template

**Scripts:**
- `scripts/sync_pick_order_data.py` - Fetch and parse sheet
- `scripts/match_pick_order_games.py` - Match to database
- `scripts/pick_order_analytics_examples.sql` - Example queries

**Modules:**
- `tournament_visualizer/data/gsheets_client.py` - Google Sheets API client
- `tournament_visualizer/data/gamedata_parser.py` - Sheet parser

**Documentation:**
- `docs/migrations/008_add_pick_order_tracking.md` - Schema migration docs
- `docs/plans/pick-order-integration-implementation-plan.md` - Full implementation plan
```

**Commit Message:**
```
docs: Add pick order integration guide to CLAUDE.md

Documents setup, workflow, analytics, and troubleshooting for pick
order integration. Includes both local development and production
deployment instructions.

Provides clear guidance for future developers and users.
```

---

### Task 12: Testing & Validation

**Time Estimate:** 1 hour

**Objective:** Comprehensive end-to-end testing before production deployment.

**Testing Checklist:**

#### 12.1 Test Configuration

```bash
# Verify config loads
uv run python -c "
from tournament_visualizer.config import Config
print(f'Spreadsheet ID: {Config.GOOGLE_SHEETS_SPREADSHEET_ID}')
print(f'Sheet GID: {Config.GOOGLE_SHEETS_GAMEDATA_GID}')
print(f'API Key set: {bool(Config.GOOGLE_DRIVE_API_KEY)}')
"
```

Expected: All values present.

#### 12.2 Test Schema Creation

```bash
# Apply schema
uv run python -c "
from tournament_visualizer.data.schema import initialize_schema
from tournament_visualizer.config import Config
import duckdb

conn = duckdb.connect(Config.DUCKDB_PATH)
initialize_schema(conn)
conn.close()
print('✓ Schema initialized')
"

# Verify tables exist
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'main'
AND table_name LIKE '%pick%'
"
```

Expected: Shows `pick_order_games` table.

#### 12.3 Test Sheet Client

```bash
# Test API access
uv run python -c "
from tournament_visualizer.config import Config
from tournament_visualizer.data.gsheets_client import GoogleSheetsClient

client = GoogleSheetsClient(Config.GOOGLE_DRIVE_API_KEY)
values = client.get_sheet_values(
    Config.GOOGLE_SHEETS_SPREADSHEET_ID,
    'GAMEDATA *SPOILER WARNING*!A1:A10'
)
print(f'✓ Fetched {len(values)} rows')
"
```

Expected: Successfully fetches data.

#### 12.4 Test Parser

```bash
# Test parsing
uv run python -c "
from tournament_visualizer.config import Config
from tournament_visualizer.data.gsheets_client import GoogleSheetsClient
from tournament_visualizer.data.gamedata_parser import parse_gamedata_sheet

client = GoogleSheetsClient(Config.GOOGLE_DRIVE_API_KEY)
values = client.get_sheet_values(
    Config.GOOGLE_SHEETS_SPREADSHEET_ID,
    'GAMEDATA *SPOILER WARNING*!A1:Z200'
)
games = parse_gamedata_sheet(values)
print(f'✓ Parsed {len(games)} games')
print(f'  First game: {games[0][\"game_number\"]} - {games[0][\"player1_sheet_name\"]} vs {games[0][\"player2_sheet_name\"]}')
"
```

Expected: Parses 40+ games successfully.

#### 12.5 Test Sync Script

```bash
# Dry run
uv run python scripts/sync_pick_order_data.py --dry-run --verbose

# Actual sync
uv run python scripts/sync_pick_order_data.py --verbose

# Verify data in database
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT COUNT(*) as game_count,
       COUNT(DISTINCT round_number) as round_count
FROM pick_order_games
"
```

Expected: All games synced to database.

#### 12.6 Test Matching Script

```bash
# Prerequisites
uv run python scripts/link_players_to_participants.py

# Dry run
uv run python scripts/match_pick_order_games.py --dry-run --verbose

# Actual match
uv run python scripts/match_pick_order_games.py --verbose

# Check match rate
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT
    COUNT(*) as total_games,
    COUNT(matched_match_id) as matched,
    ROUND(COUNT(matched_match_id) * 100.0 / COUNT(*), 1) as match_rate_pct
FROM pick_order_games
"
```

Expected: High match rate (>90%).

#### 12.7 Test Analytics Queries

```bash
# Run all example queries
uv run duckdb data/tournament_data.duckdb -readonly < scripts/pick_order_analytics_examples.sql

# Should complete without errors and show meaningful results
```

Expected: All queries run successfully.

#### 12.8 Test Override System

```bash
# Create test override
echo '{
  "game_999": {
    "challonge_match_id": 1,
    "reason": "Test override",
    "date_added": "2025-10-17"
  }
}' > data/pick_order_overrides.json

# Test loading
uv run python scripts/match_pick_order_games.py --dry-run --verbose

# Should see "Loaded 1 pick order overrides"

# Clean up
rm data/pick_order_overrides.json
```

Expected: Override file loads successfully.

#### 12.9 Test Full Sync Workflow

```bash
# Run complete workflow locally
./scripts/sync_tournament_data.sh

# Should include pick order steps
# Check logs for:
# - "Syncing pick order data from Google Sheets..."
# - "Matching pick order games to matches..."
```

Expected: Full sync completes with pick order data.

#### 12.10 Test Error Conditions

```bash
# Test with missing API key
unset GOOGLE_DRIVE_API_KEY
uv run python scripts/sync_pick_order_data.py
# Should show clear error message

# Test with invalid spreadsheet ID
export GOOGLE_SHEETS_SPREADSHEET_ID="invalid"
uv run python scripts/sync_pick_order_data.py
# Should show API error

# Restore environment
source .env
```

Expected: Graceful error handling with clear messages.

---

### Task 13: Production Deployment

**Time Estimate:** 30 minutes

**Objective:** Deploy to production and verify everything works.

**Pre-Deployment Checklist:**

- [ ] All tests passing locally (Task 12)
- [ ] Configuration added to Fly.io (API key already there from GDrive)
- [ ] Override file ready if needed
- [ ] Documentation updated
- [ ] Code committed and pushed to git

**Deployment Steps:**

```bash
# 1. Deploy code changes
fly deploy -a prospector

# 2. Verify deployment
fly logs -a prospector

# 3. Run full sync (processes data locally, uploads to Fly)
./scripts/sync_tournament_data.sh

# 4. Monitor logs for pick order steps
fly logs -a prospector -f

# 5. Verify app is running
curl https://prospector.fly.dev/health
# Or visit in browser
```

**Post-Deployment Verification:**

```bash
# Check that pick order data is in production database
fly ssh console -a prospector -C "
cd /app &&
uv run duckdb /data/tournament_data.duckdb -readonly -c '
SELECT
    COUNT(*) as total_matches,
    COUNT(first_picker_participant_id) as with_pick_order,
    ROUND(COUNT(first_picker_participant_id) * 100.0 / COUNT(*), 1) as coverage_pct
FROM matches
'
"

# Should show pick order coverage %
```

**Rollback Plan (if something goes wrong):**

```bash
# Option 1: Disable pick order sync (no code changes)
# Remove from sync script temporarily, or set env var:
export SKIP_PICK_ORDER_SYNC=1
./scripts/sync_tournament_data.sh

# Option 2: Revert to previous deployment
fly releases -a prospector
fly releases rollback <previous-version> -a prospector

# Option 3: Restore database from backup
# (Database changes are additive - no data loss)
```

**Commit Message:**
```
chore: Deploy pick order integration to production

Deploys complete pick order integration:
- Google Sheets sync and parsing
- Automatic matching to database
- Analytics queries ready
- Full documentation

All tests passing. Monitoring for issues.
```

---

## Testing Strategy

### Unit Tests

**Files with tests:**
- `tests/test_gamedata_parser.py` - Parser logic
- Future: `tests/test_gsheets_client.py` (if needed)

**Run tests:**
```bash
uv run pytest tests/test_gamedata_parser.py -v
```

### Integration Tests

**Manual integration testing (Task 12):**
1. Sheet client fetches data
2. Parser extracts games
3. Sync writes to database
4. Matching links to matches
5. Analytics queries work
6. Full workflow succeeds

### End-to-End Testing

**Full workflow test:**
```bash
# Complete sync from scratch
rm -rf saves/*.zip
rm data/tournament_data.duckdb
./scripts/sync_tournament_data.sh

# Verify pick order data present
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT COUNT(*) FROM pick_order_games WHERE matched_match_id IS NOT NULL
"
```

---

## Validation Checklist

Before considering this complete, verify:

- [ ] All unit tests pass
- [ ] Integration tests pass (Task 12 checklist)
- [ ] Documentation updated (CLAUDE.md, migration docs)
- [ ] Google Sheets configuration works
- [ ] Sheet parser handles all rounds
- [ ] Sync script stores data correctly
- [ ] Matching script achieves high match rate (>90%)
- [ ] Manual overrides work
- [ ] Analytics queries return meaningful results
- [ ] Full sync workflow includes pick order
- [ ] Production deployment successful
- [ ] Pick order data visible in production

---

## Rollback Plan

If issues occur in production:

### Immediate Rollback (No Code Changes)

The pick order feature is **additive only** - no existing functionality is changed. To disable:

1. **Skip in sync workflow:**
   ```bash
   # Comment out pick order steps in sync_tournament_data.sh temporarily
   ```

2. **Or unset config:**
   ```bash
   fly secrets unset GOOGLE_SHEETS_SPREADSHEET_ID -a prospector
   ```

This disables pick order sync without affecting other features.

### Code Rollback

```bash
# Find previous good version
fly releases -a prospector

# Rollback
fly releases rollback <version> -a prospector
```

### Data Rollback

Pick order data is in separate tables - no risk to existing data:
- `pick_order_games` table is standalone
- `matches` table only gains nullable columns

To remove if needed:
```bash
fly ssh console -a prospector
cd /app
uv run duckdb /data/tournament_data.duckdb -c "
ALTER TABLE matches DROP COLUMN IF EXISTS first_picker_participant_id;
ALTER TABLE matches DROP COLUMN IF EXISTS second_picker_participant_id;
DROP TABLE IF EXISTS pick_order_games;
"
```

---

## Known Limitations

1. **Manual sheet updates required:**
   - Sheet is updated manually by TO
   - No automatic sync on new games
   - Must run sync script to get latest data

2. **Player name matching:**
   - Depends on name consistency between sheet and save files
   - May require manual overrides for mismatches
   - Normalized matching helps but isn't perfect

3. **Nation name exact match:**
   - Requires exact civilization name spelling
   - "Assyria" works, "ASSYRIA" or "assyrian" doesn't
   - No fuzzy matching currently

4. **Sheet structure assumptions:**
   - Parser expects specific row labels ("Nation; First Pick", etc.)
   - Column detection is dynamic but may fail on major layout changes
   - Robust to row offset changes within rounds

5. **No historical validation:**
   - Doesn't validate pick order makes sense historically
   - Trusts sheet data is accurate
   - No cross-validation with other sources

---

## Future Enhancements

**Not in scope for this implementation, but could be added later:**

1. **Sheet change detection:**
   - Monitor sheet for updates
   - Auto-trigger sync when changes detected
   - Notification when new games added

2. **Fuzzy name matching:**
   - Use similarity algorithms for player names
   - Suggest possible matches with confidence scores
   - Reduce manual override needs

3. **Nation name normalization:**
   - Handle case variations
   - Map common misspellings
   - Provide feedback on invalid nation names

4. **Pick order validation:**
   - Cross-check with tournament bracket
   - Verify first picker rotates appropriately
   - Flag suspicious data

5. **Web UI for overrides:**
   - Visual interface for adding overrides
   - Show unmatched games with suggestions
   - Reduce need to edit JSON manually

6. **Dashboard integration:**
   - Pick order visualizations in web app
   - Interactive filters and charts
   - Export analysis results

---

## Troubleshooting Guide

### Problem: "API key is required" error

**Cause:** GOOGLE_DRIVE_API_KEY not set

**Solution:**
```bash
# Check .env file
cat .env | grep GOOGLE_DRIVE_API_KEY

# If missing, add it
echo "GOOGLE_DRIVE_API_KEY=your_key_here" >> .env
```

### Problem: "Failed to fetch sheet data"

**Cause:** Invalid API key, API not enabled, or sheet not accessible

**Solution:**
1. Verify API key: https://console.cloud.google.com/apis/credentials
2. Enable Sheets API: https://console.cloud.google.com/apis/library/sheets.googleapis.com
3. Check sheet is public or API key has access
4. Verify spreadsheet ID is correct

### Problem: Low match rate (<50%)

**Cause:** Player names in sheet don't match save files

**Solution:**
```bash
# Run matching with verbose to see failures
uv run python scripts/match_pick_order_games.py --verbose

# Check player names in both sources
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT DISTINCT player_name, player_name_normalized
FROM players
ORDER BY player_name
"

# Add overrides for mismatches
cp data/pick_order_overrides.json.example data/pick_order_overrides.json
# Edit to add mappings
uv run python scripts/match_pick_order_games.py
```

### Problem: Nation mismatch errors

**Cause:** Nation names in sheet don't match save file civilizations

**Solution:**
```bash
# Check valid civilization names
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT DISTINCT civilization
FROM players
ORDER BY civilization
"

# Compare to sheet data
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT DISTINCT first_pick_nation
FROM pick_order_games
UNION
SELECT DISTINCT second_pick_nation
FROM pick_order_games
ORDER BY 1
"

# Fix sheet or add override if player changed civ
```

### Problem: Parser fails to find rounds/games

**Cause:** Sheet structure changed

**Solution:**
```bash
# Run parser with verbose to see what it's finding
uv run python scripts/sync_pick_order_data.py --dry-run --verbose

# Check for changes in:
# - Round header format ("ROUND X")
# - Row labels ("Nation; First Pick", "Second Pick")
# - Game column labels ("Game N")

# May need to update parser if structure changed significantly
```

### Problem: Games not syncing in production

**Cause:** Sync script failing, or API key not set in Fly

**Solution:**
```bash
# Check Fly logs
fly logs -a prospector

# Verify secrets
fly secrets list -a prospector

# Re-run sync
./scripts/sync_tournament_data.sh

# Check if pick order steps ran
# Look for "Syncing pick order data" in output
```

---

## Success Criteria

This implementation is complete when:

1. ✅ Google Sheets client can fetch data from GAMEDATA tab
2. ✅ Parser successfully extracts games from multi-column layout
3. ✅ Sync script stores parsed data in pick_order_games table
4. ✅ Matching script links games to matches with high accuracy (>90%)
5. ✅ Matches table has picker participant IDs populated
6. ✅ Analytics queries return meaningful results
7. ✅ Full sync workflow includes pick order automatically
8. ✅ Production deployment successful and data visible
9. ✅ Documentation complete and accurate
10. ✅ All tests passing

---

## Time Breakdown Summary

| Task | Time Estimate | Type |
|------|---------------|------|
| 1. Add Sheets configuration | 15 min | Config |
| 2. Verify API dependency | 5 min | Setup |
| 3. Create database schema | 30 min | Schema |
| 4. Create Sheets client | 45 min | Code |
| 5. Create sheet parser | 2 hours | Code (complex) |
| 6. Create sync script | 1.5 hours | Code |
| 7. Create matching script | 1.5 hours | Code |
| 8. Integrate into sync workflow | 30 min | Integration |
| 9. Create override examples | 15 min | Docs |
| 10. Add analytics queries | 1 hour | SQL |
| 11. Update documentation | 45 min | Docs |
| 12. Testing & validation | 1 hour | Testing |
| 13. Production deployment | 30 min | Deployment |
| **Total** | **10-11 hours** | |

---

## Commit Strategy

Follow atomic commits - one logical change per commit:

1. ✅ Add Google Sheets configuration
2. ✅ Verify google-api-python-client dependency
3. ✅ Add pick_order_games table schema
4. ✅ Add GoogleSheetsClient module
5. ✅ Add GAMEDATA sheet parser with tests
6. ✅ Add pick order sync script
7. ✅ Add pick order matching script
8. ✅ Integrate into sync workflow
9. ✅ Add override file examples
10. ✅ Add analytics query examples
11. ✅ Update CLAUDE.md documentation
12. ✅ Integration testing verification
13. ✅ Deploy to production

Each commit should:
- Pass all existing tests
- Include relevant test updates
- Follow conventional commit format
- Have clear, descriptive message

---

## Questions to Ask Before Starting

1. **Is the Google Sheets spreadsheet publicly accessible?**
   - If not, may need OAuth instead of API key

2. **Will the sheet structure remain stable?**
   - Or should we build in more flexibility?

3. **How often does the sheet get updated?**
   - Affects how often we need to sync

4. **Are there any other data sources we should consider?**
   - Discord logs, tournament software, etc.

5. **What analytics are most important to the TO?**
   - Helps prioritize which queries to include

---

## Notes for Code Reviewer

**Key Design Decisions:**

1. **Why intermediate storage (pick_order_games)?**
   - Enables debugging and audit trail
   - Can re-run matching without re-fetching
   - Shows what came from sheet vs what matched

2. **Why dynamic row detection vs hardcoded?**
   - Sheet may change row offsets between rounds
   - More robust to minor layout changes
   - Easier to maintain long-term

3. **Why match by player names vs game numbers?**
   - Sheet game numbers may not match Challonge match IDs
   - Player names are more reliable identifier
   - Can validate match is correct by checking nations

4. **Why separate sync and match scripts?**
   - Sync can fail independently of matching
   - Matching can be re-run without re-fetching
   - Clearer error messages and debugging
   - Follows single responsibility principle

**What to Review:**

- Error handling (API failures, parsing errors, match failures)
- Test coverage (especially parser edge cases)
- SQL query performance (joining participants, aggregations)
- Documentation clarity (can someone else use this?)
- Logging (helpful debugging messages?)

---

**End of Implementation Plan**