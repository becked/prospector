# Match Narrative Generation Implementation Plan

## Overview

**Goal:** Generate AI-powered narrative summaries for each match to display on match detail pages.

**Context:**
- Tournament matches generate rich event data (techs, laws, combat, cities, etc.)
- Match detail pages need human-readable summaries to help users understand what happened
- LLMs can analyze event streams and generate concise narrative summaries
- Narratives should be 2-3 paragraphs highlighting key moments and outcome

**Approach:**
- Two-pass LLM process: (1) extract structured timeline, (2) generate narrative prose
- Use Anthropic's Claude API with structured output (tool calling) for timeline extraction
- Store final narrative in `matches.narrative_summary` column
- Run as separate script after data import
- Default: only generate for matches missing narratives
- Support `--force` flag to regenerate all narratives

**Estimated Total Time:** 4-6 hours

---

## Prerequisites

### Environment Setup
- Python 3.9+ with `uv` package manager
- DuckDB database at `data/tournament_data.duckdb`
- Environment variables set in `.env`:
  - `ANTHROPIC_API_KEY` - Anthropic API key (already configured)
  - `CHALLONGE_KEY` - Challonge API key
  - `CHALLONGE_USER` - Challonge username
  - `challonge_tournament_id` - Tournament ID

### Key Files to Understand

**Configuration:**
- `tournament_visualizer/config.py` - Configuration constants
- `.env` - Environment variables (not in git)

**Database Schema:**
- `tournament_visualizer/data/schema.py` - Table definitions
- `matches` table - Match metadata (will add `narrative_summary` column)
- `events` table - Turn-by-turn game events
- `players` table - Per-match player data

**Data Pipeline:**
- `scripts/import_attachments.py` - Parses saves to database
- `scripts/sync_tournament_data.sh` - Complete sync workflow (will add narrative step)

**Existing Patterns:**
- `tournament_visualizer/data/gsheets_client.py` - External API client pattern to follow
- `tournament_visualizer/data/gamedata_parser.py` - Data parsing pattern to follow

**Codebase Patterns:**
- Uses `logging` for all output (not print statements)
- Type hints required on all functions
- Follows DRY principle - extract shared logic
- Follows YAGNI - only implement what's needed now
- Use TDD - write tests first, then implementation

---

## Design Decisions

### Key Architectural Choices

**1. Two-Pass LLM Approach**
- **Pass 1:** Extract structured timeline (JSON) from raw events
  - Game phases (early, mid, war, etc.)
  - Key events (war declarations, city captures, tech milestones)
  - Summary statistics per player
  - Victory outcome
- **Pass 2:** Generate narrative prose from structured timeline
  - 2-3 paragraph summary
  - Focus on outcome and key moments
  - Natural language, not technical

**Why:** Separating extraction from writing improves accuracy and makes prompt tuning easier.

**2. Timeline is Ephemeral**
- Don't store timeline JSON in database
- Use it as intermediate step between passes
- Reduces storage complexity
- Timeline structure may change as prompts evolve

**Why:** Timeline is implementation detail, only final narrative matters to users.

**3. Anthropic Structured Output (Tool Calling)**
- Use Claude's tool calling for Pass 1 timeline extraction
- Define timeline schema as a tool
- More reliable than prompting for JSON and parsing

**Why:** Structured output ensures valid JSON, reduces parsing errors.

**4. Human-Readable Event Format**
- Format events as grouped text by turn
- Include player name + event detail
- Example: "Turn 51: Fluffbunny declared war on Becked"
- Send ALL event types (no filtering)

**Why:** Let LLM determine what's important, avoid missing critical context.

**5. Error Handling: Retry and Skip**
- Retry API calls with exponential backoff on transient failures
- Log error and skip match on persistent failures
- Continue processing other matches
- Report summary of successes/failures at end

**Why:** Don't halt entire batch on single match failure.

**6. Model Choice: Claude 3.5 Haiku**
- Fast and cheap for structured tasks
- Good enough quality for this use case
- Can upgrade to Sonnet if quality issues arise

**Why:** Cost-effective starting point, easy to upgrade later.

---

## Task Breakdown

### Task 1: Add Anthropic SDK Dependency (15 min)

**Goal:** Add the Anthropic Python SDK to project dependencies.

**Files to modify:**
- `pyproject.toml`

**Steps:**

1. **Add dependency:**
   ```toml
   dependencies = [
       # ... existing dependencies ...
       "anthropic>=0.39.0",
   ]
   ```

2. **Install dependency:**
   ```bash
   uv sync
   ```

3. **Verify installation:**
   ```bash
   uv run python -c "import anthropic; print(anthropic.__version__)"
   ```

**Testing:**
- Run the verification command above
- Should print version number (e.g., "0.39.0")

**Commit checkpoint:**
```
chore: Add Anthropic SDK dependency for narrative generation
```

---

### Task 2: Database Migration - Add narrative_summary Column (20 min)

**Goal:** Add column to store narrative summaries in matches table.

**Files to create:**
- `docs/migrations/009_add_match_narrative_summary.md`

**Files to modify:**
- `tournament_visualizer/data/schema.py`

**Steps:**

1. **Create migration documentation:**

Create `docs/migrations/009_add_match_narrative_summary.md`:

```markdown
# Migration 009: Add Match Narrative Summary

## Overview

Adds AI-generated narrative summaries to matches table.

**Date:** 2025-10-19
**Author:** System
**Status:** Pending

---

## Changes

### Updated Table: matches

Adds column to store AI-generated narrative summary.

```sql
ALTER TABLE matches
ADD COLUMN narrative_summary TEXT;
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
uv run duckdb data/tournament_data.duckdb -readonly -c "DESCRIBE matches" | grep narrative
```

Should show:
```
│ narrative_summary │ VARCHAR │ YES │ NULL │ NULL │ NULL │
```

---

## Rollback Procedure

```bash
# Restore from backup
cp data/tournament_data.duckdb.backup_YYYYMMDD_HHMMSS data/tournament_data.duckdb

# Or drop column (DuckDB supports this)
uv run duckdb data/tournament_data.duckdb -c "ALTER TABLE matches DROP COLUMN narrative_summary"
```

---

## Related Files

- `tournament_visualizer/data/schema.py` - Schema definition
- `scripts/generate_match_narratives.py` - Script to populate narratives (Task 3+)
```

2. **Update schema.py:**

Find the `CREATE TABLE matches` statement in `tournament_visualizer/data/schema.py` and add the new column:

```python
# Add after winner_participant_id or last column
narrative_summary TEXT,
```

The complete column should look like:
```python
narrative_summary TEXT,
```

**Important:**
- Add comma after previous column
- Place near end of column list (after participant/picker columns)
- Use `TEXT` type (unlimited length)
- Nullable (no `NOT NULL` constraint)

3. **Test the migration:**
   ```bash
   # Backup first
   cp data/tournament_data.duckdb data/tournament_data.duckdb.backup_$(date +%Y%m%d_%H%M%S)

   # Apply schema
   uv run python -c "
from tournament_visualizer.data.schema import initialize_schema
from tournament_visualizer.config import Config
import duckdb

conn = duckdb.connect(Config.DUCKDB_PATH)
initialize_schema(conn)
conn.close()
print('Schema updated')
"

   # Verify
   uv run duckdb data/tournament_data.duckdb -readonly -c "DESCRIBE matches" | grep narrative
   ```

**Testing:**
- Schema update should not fail
- `DESCRIBE matches` should show `narrative_summary` column
- Column should be `TEXT` type, nullable
- Existing data should be unaffected (all narratives NULL initially)

**Commit checkpoint:**
```
docs: Add migration 009 for narrative_summary column

feat: Add narrative_summary column to matches table
```

(Two commits: one for docs, one for code)

---

### Task 3: Create Anthropic Client Module (30 min)

**Goal:** Create reusable client for Anthropic API calls with retry logic.

**Files to create:**
- `tournament_visualizer/data/anthropic_client.py`

**Why this module:**
- Encapsulates API authentication and configuration
- Provides retry logic for transient failures
- Reusable for future AI features
- Follows same pattern as `gsheets_client.py` and `gdrive_client.py`

**Steps:**

1. **Look at existing client pattern:**
   ```bash
   uv run python -c "
import tournament_visualizer.data.gsheets_client as gc
import inspect
print(inspect.getsource(gc.GoogleSheetsClient))
"
   ```

2. **Create `tournament_visualizer/data/anthropic_client.py`:**

```python
"""Anthropic API client for generating match narratives.

This module provides a simple interface to the Anthropic API for
generating narrative summaries from match event data. Uses API key
authentication and includes retry logic for transient failures.

Example:
    >>> from tournament_visualizer.config import Config
    >>> client = AnthropicClient(api_key=Config.ANTHROPIC_API_KEY)
    >>> response = client.generate_with_tools(
    ...     messages=[{"role": "user", "content": "Extract timeline"}],
    ...     tools=[timeline_tool],
    ...     model="claude-3-5-haiku-20241022"
    ... )
"""

import logging
import time
from typing import Any

import anthropic
from anthropic.types import MessageParam, ToolParam

logger = logging.getLogger(__name__)


class AnthropicClient:
    """Client for calling Anthropic API with retry logic.

    Uses API key authentication. Includes exponential backoff retry
    for rate limits and transient failures.

    Attributes:
        api_key: Anthropic API key
        max_retries: Maximum number of retry attempts (default: 3)
        initial_retry_delay: Initial delay in seconds for exponential backoff (default: 1.0)
    """

    def __init__(
        self,
        api_key: str,
        max_retries: int = 3,
        initial_retry_delay: float = 1.0,
    ) -> None:
        """Initialize Anthropic client.

        Args:
            api_key: Anthropic API key
            max_retries: Maximum number of retry attempts
            initial_retry_delay: Initial delay in seconds for exponential backoff

        Raises:
            ValueError: If api_key is empty
        """
        if not api_key:
            raise ValueError("API key is required")

        self.api_key = api_key
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self._client: anthropic.Anthropic | None = None

    @property
    def client(self) -> anthropic.Anthropic:
        """Lazy-load Anthropic client.

        Returns:
            Anthropic client instance
        """
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def generate_with_tools(
        self,
        messages: list[MessageParam],
        tools: list[ToolParam],
        model: str = "claude-3-5-haiku-20241022",
        max_tokens: int = 4096,
    ) -> anthropic.types.Message:
        """Generate completion using tool calling (structured output).

        Includes retry logic with exponential backoff for rate limits
        and transient failures.

        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: List of tool definitions for structured output
            model: Model name to use (default: Claude 3.5 Haiku)
            max_tokens: Maximum tokens to generate

        Returns:
            Anthropic Message object with tool use in content blocks

        Raises:
            anthropic.APIError: On persistent API errors after retries
        """
        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    f"Calling Anthropic API (attempt {attempt + 1}/{self.max_retries})"
                )
                response = self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    messages=messages,
                    tools=tools,
                )
                logger.debug("API call successful")
                return response

            except anthropic.RateLimitError as e:
                if attempt < self.max_retries - 1:
                    delay = self.initial_retry_delay * (2**attempt)
                    logger.warning(
                        f"Rate limit hit, retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"Rate limit exceeded after {self.max_retries} retries")
                    raise

            except anthropic.APIConnectionError as e:
                if attempt < self.max_retries - 1:
                    delay = self.initial_retry_delay * (2**attempt)
                    logger.warning(
                        f"Connection error, retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Connection failed after {self.max_retries} retries"
                    )
                    raise

            except anthropic.APIError as e:
                # Don't retry on client errors (4xx)
                if hasattr(e, "status_code") and 400 <= e.status_code < 500:
                    logger.error(f"Client error (no retry): {e}")
                    raise
                # Retry on server errors (5xx)
                if attempt < self.max_retries - 1:
                    delay = self.initial_retry_delay * (2**attempt)
                    logger.warning(
                        f"Server error, retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Server error after {self.max_retries} retries"
                    )
                    raise

        # Should never reach here due to raises above
        raise RuntimeError("Retry loop exited unexpectedly")

    def generate_text(
        self,
        messages: list[MessageParam],
        model: str = "claude-3-5-haiku-20241022",
        max_tokens: int = 4096,
    ) -> str:
        """Generate text completion (no structured output).

        Includes retry logic with exponential backoff for rate limits
        and transient failures.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name to use (default: Claude 3.5 Haiku)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text content

        Raises:
            anthropic.APIError: On persistent API errors after retries
        """
        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    f"Calling Anthropic API (attempt {attempt + 1}/{self.max_retries})"
                )
                response = self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    messages=messages,
                )
                logger.debug("API call successful")

                # Extract text from content blocks
                text_blocks = [
                    block.text
                    for block in response.content
                    if hasattr(block, "text")
                ]
                return "\n".join(text_blocks)

            except anthropic.RateLimitError as e:
                if attempt < self.max_retries - 1:
                    delay = self.initial_retry_delay * (2**attempt)
                    logger.warning(
                        f"Rate limit hit, retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"Rate limit exceeded after {self.max_retries} retries")
                    raise

            except anthropic.APIConnectionError as e:
                if attempt < self.max_retries - 1:
                    delay = self.initial_retry_delay * (2**attempt)
                    logger.warning(
                        f"Connection error, retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Connection failed after {self.max_retries} retries"
                    )
                    raise

            except anthropic.APIError as e:
                # Don't retry on client errors (4xx)
                if hasattr(e, "status_code") and 400 <= e.status_code < 500:
                    logger.error(f"Client error (no retry): {e}")
                    raise
                # Retry on server errors (5xx)
                if attempt < self.max_retries - 1:
                    delay = self.initial_retry_delay * (2**attempt)
                    logger.warning(
                        f"Server error, retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Server error after {self.max_retries} retries"
                    )
                    raise

        # Should never reach here due to raises above
        raise RuntimeError("Retry loop exited unexpectedly")
```

**Testing:**

Create simple test to verify client initialization and method signatures:

```bash
uv run python -c "
from tournament_visualizer.data.anthropic_client import AnthropicClient
import os

# Test initialization
api_key = os.getenv('ANTHROPIC_API_KEY', 'test-key')
client = AnthropicClient(api_key=api_key)
print('✓ Client initialized')

# Test that methods exist
assert hasattr(client, 'generate_with_tools')
assert hasattr(client, 'generate_text')
print('✓ Methods exist')

# Test empty API key raises
try:
    bad_client = AnthropicClient(api_key='')
    assert False, 'Should have raised ValueError'
except ValueError:
    print('✓ Empty API key validation works')

print('All checks passed!')
"
```

**Commit checkpoint:**
```
feat: Add Anthropic API client with retry logic
```

---

### Task 4: Create Event Formatter Module (45 min)

**Goal:** Format match events into human-readable text grouped by turn.

**Files to create:**
- `tournament_visualizer/data/event_formatter.py`
- `tests/test_event_formatter.py`

**Why this module:**
- Converts database event rows into text LLM can understand
- Groups events by turn for readability
- Includes player names and event details
- Reusable format for different LLM prompts

**Steps:**

1. **Write tests first (TDD):**

Create `tests/test_event_formatter.py`:

```python
"""Tests for event formatter module."""

import pytest
from tournament_visualizer.data.event_formatter import EventFormatter


@pytest.fixture
def sample_events() -> list[dict]:
    """Sample event data from database."""
    return [
        {
            "turn_number": 1,
            "event_type": "CITY_FOUNDED",
            "player_name": "Fluffbunny",
            "civilization": "Kush",
            "description": "Founded Meroe",
            "event_data": None,
        },
        {
            "turn_number": 1,
            "event_type": "TECH_DISCOVERED",
            "player_name": "Fluffbunny",
            "civilization": "Kush",
            "description": None,
            "event_data": {"tech": "TECH_TRAPPING"},
        },
        {
            "turn_number": 1,
            "event_type": "CITY_FOUNDED",
            "player_name": "Becked",
            "civilization": "Assyria",
            "description": "Founded Nineveh",
            "event_data": None,
        },
        {
            "turn_number": 5,
            "event_type": "TECH_DISCOVERED",
            "player_name": "Becked",
            "civilization": "Assyria",
            "description": None,
            "event_data": {"tech": "TECH_IRONWORKING"},
        },
    ]


def test_format_events_groups_by_turn(sample_events: list[dict]) -> None:
    """Events should be grouped by turn number."""
    formatter = EventFormatter()
    result = formatter.format_events(sample_events)

    # Should have turn headers
    assert "Turn 1:" in result
    assert "Turn 5:" in result

    # Turn 1 events should appear before Turn 5
    turn1_pos = result.index("Turn 1:")
    turn5_pos = result.index("Turn 5:")
    assert turn1_pos < turn5_pos


def test_format_events_includes_player_names(sample_events: list[dict]) -> None:
    """Event descriptions should include player names."""
    formatter = EventFormatter()
    result = formatter.format_events(sample_events)

    assert "Fluffbunny" in result
    assert "Becked" in result


def test_format_events_includes_descriptions(sample_events: list[dict]) -> None:
    """Event descriptions from database should be included."""
    formatter = EventFormatter()
    result = formatter.format_events(sample_events)

    assert "Founded Meroe" in result
    assert "Founded Nineveh" in result


def test_format_events_extracts_tech_names(sample_events: list[dict]) -> None:
    """Tech names should be extracted from event_data JSON."""
    formatter = EventFormatter()
    result = formatter.format_events(sample_events)

    # Should show cleaned tech names (without TECH_ prefix)
    assert "Trapping" in result or "TECH_TRAPPING" in result
    assert "Ironworking" in result or "TECH_IRONWORKING" in result


def test_format_events_handles_empty_list() -> None:
    """Should handle empty event list gracefully."""
    formatter = EventFormatter()
    result = formatter.format_events([])

    assert result == "" or result.strip() == ""


def test_format_events_handles_missing_fields() -> None:
    """Should handle events with missing optional fields."""
    events = [
        {
            "turn_number": 1,
            "event_type": "UNKNOWN_EVENT",
            "player_name": "Player",
            "civilization": None,
            "description": None,
            "event_data": None,
        }
    ]

    formatter = EventFormatter()
    result = formatter.format_events(events)

    # Should not crash, should include turn and player
    assert "Turn 1:" in result
    assert "Player" in result
```

2. **Run tests (they should fail):**
   ```bash
   uv run pytest tests/test_event_formatter.py -v
   ```

3. **Create implementation:**

Create `tournament_visualizer/data/event_formatter.py`:

```python
"""Format match events into human-readable text for LLM consumption.

This module converts database event rows into grouped, readable text
that provides context to LLMs for narrative generation.

Example:
    >>> formatter = EventFormatter()
    >>> events = get_events_from_db(match_id=19)
    >>> text = formatter.format_events(events)
    >>> print(text)
    Turn 1:
      - Fluffbunny (Kush) founded Meroe
      - Fluffbunny (Kush) discovered Trapping
      - Becked (Assyria) founded Nineveh
    Turn 5:
      - Becked (Assyria) discovered Ironworking
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class EventFormatter:
    """Formats match events into human-readable grouped text.

    Groups events by turn and formats each with player context
    and event details.
    """

    def format_events(self, events: list[dict[str, Any]]) -> str:
        """Format events into grouped human-readable text.

        Args:
            events: List of event dicts from database with fields:
                - turn_number: int
                - event_type: str
                - player_name: str
                - civilization: str | None
                - description: str | None
                - event_data: dict | None

        Returns:
            Formatted text with events grouped by turn

        Example:
            >>> events = [
            ...     {"turn_number": 1, "event_type": "CITY_FOUNDED",
            ...      "player_name": "Alice", "civilization": "Rome",
            ...      "description": "Founded Rome", "event_data": None}
            ... ]
            >>> formatter.format_events(events)
            'Turn 1:\\n  - Alice (Rome) founded Rome\\n'
        """
        if not events:
            return ""

        # Group events by turn
        events_by_turn: dict[int, list[dict[str, Any]]] = {}
        for event in events:
            turn = event["turn_number"]
            if turn not in events_by_turn:
                events_by_turn[turn] = []
            events_by_turn[turn].append(event)

        # Format each turn
        lines: list[str] = []
        for turn in sorted(events_by_turn.keys()):
            lines.append(f"Turn {turn}:")
            for event in events_by_turn[turn]:
                formatted = self._format_single_event(event)
                if formatted:
                    lines.append(f"  - {formatted}")

        return "\n".join(lines)

    def _format_single_event(self, event: dict[str, Any]) -> str:
        """Format a single event into readable text.

        Args:
            event: Event dict from database

        Returns:
            Formatted event string (without turn prefix)
        """
        player = event.get("player_name", "Unknown")
        civ = event.get("civilization")
        event_type = event.get("event_type", "UNKNOWN")
        description = event.get("description")
        event_data = event.get("event_data")

        # Build player context
        player_ctx = player
        if civ:
            player_ctx = f"{player} ({civ})"

        # Try to get description from various sources
        detail = self._extract_event_detail(event_type, description, event_data)

        if detail:
            return f"{player_ctx} {detail}"
        else:
            # Fallback: just show event type
            return f"{player_ctx} - {event_type}"

    def _extract_event_detail(
        self,
        event_type: str,
        description: str | None,
        event_data: dict[str, Any] | None,
    ) -> str:
        """Extract human-readable detail from event.

        Args:
            event_type: Type of event (e.g., "TECH_DISCOVERED")
            description: Description field from database
            event_data: JSON event data

        Returns:
            Human-readable event detail
        """
        # Use description if available
        if description:
            return description.lower()

        # Extract from event_data JSON
        if event_data:
            # Tech discovered
            if event_type == "TECH_DISCOVERED" and "tech" in event_data:
                tech = event_data["tech"]
                # Clean up tech name (remove TECH_ prefix)
                if tech.startswith("TECH_"):
                    tech = tech[5:]
                # Convert to title case and replace underscores
                tech = tech.replace("_", " ").title()
                return f"discovered {tech}"

            # Law adopted
            if event_type == "LAW_ADOPTED" and "law" in event_data:
                law = event_data["law"]
                # Clean up law name (remove LAW_ prefix)
                if law.startswith("LAW_"):
                    law = law[4:]
                # Convert to title case and replace underscores
                law = law.replace("_", " ").title()
                return f"adopted {law}"

        # Map common event types to readable verbs
        event_type_map = {
            "CITY_FOUNDED": "founded a city",
            "CITY_BREACHED": "had a city breached",
            "TEAM_DIPLOMACY": "diplomatic action",
            "GOAL_STARTED": "started a goal",
            "GOAL_FINISHED": "finished a goal",
            "GOAL_FAILED": "failed a goal",
            "MEMORYPLAYER_ATTACKED_CITY": "attacked enemy city",
            "MEMORYPLAYER_ATTACKED_UNIT": "attacked enemy unit",
            "MEMORYPLAYER_CAPTURED_CITY": "captured enemy city",
        }

        if event_type in event_type_map:
            return event_type_map[event_type]

        # Return empty string for unmapped types
        # (caller will use fallback)
        return ""
```

4. **Run tests (should pass now):**
   ```bash
   uv run pytest tests/test_event_formatter.py -v
   ```

5. **Test with real data:**
   ```bash
   uv run python -c "
from tournament_visualizer.data.event_formatter import EventFormatter
from tournament_visualizer.config import Config
import duckdb

conn = duckdb.connect(Config.DUCKDB_PATH, read_only=True)

# Get events for match 19 (Fluffbunny vs Becked)
events = conn.execute('''
    SELECT
        e.turn_number,
        e.event_type,
        p.player_name,
        p.civilization,
        e.description,
        e.event_data
    FROM events e
    JOIN players p ON e.player_id = p.player_id
    WHERE e.match_id = 19
    ORDER BY e.turn_number
    LIMIT 50
''').fetchall()

# Convert to dicts
event_dicts = [
    {
        'turn_number': e[0],
        'event_type': e[1],
        'player_name': e[2],
        'civilization': e[3],
        'description': e[4],
        'event_data': e[5],
    }
    for e in events
]

conn.close()

# Format and print
formatter = EventFormatter()
text = formatter.format_events(event_dicts)
print(text)
print(f'\nFormatted {len(event_dicts)} events')
"
   ```

**Testing:**
- All pytest tests should pass
- Real data test should print formatted events grouped by turn
- Should handle missing/null fields gracefully
- Tech and law names should be cleaned up (no TECH_/LAW_ prefix)

**Commit checkpoint:**
```
test: Add tests for event formatter

feat: Add event formatter for LLM-readable event text
```

(Two commits: tests first, then implementation)

---

### Task 5: Create Narrative Generator Module (60 min)

**Goal:** Core logic for two-pass narrative generation using Anthropic API.

**Files to create:**
- `tournament_visualizer/data/narrative_generator.py`
- `tests/test_narrative_generator.py`

**Why this module:**
- Encapsulates the two-pass LLM workflow
- Defines timeline schema for structured output
- Contains prompts for extraction and narrative generation
- Returns final narrative text

**Steps:**

1. **Write tests first:**

Create `tests/test_narrative_generator.py`:

```python
"""Tests for narrative generator module."""

import json
from unittest.mock import MagicMock, patch

import pytest
from tournament_visualizer.data.narrative_generator import (
    NarrativeGenerator,
    MatchTimeline,
)


@pytest.fixture
def sample_formatted_events() -> str:
    """Sample formatted events text."""
    return """Turn 1:
  - Fluffbunny (Kush) founded Meroe
  - Becked (Assyria) founded Nineveh

Turn 51:
  - Fluffbunny (Kush) Declared War on Assyria (Becked)

Turn 57:
  - Becked (Assyria) Tushpa breached by Kush (Fluffbunny)

Turn 64:
  - Becked (Assyria) Qatna breached by Kush (Fluffbunny)"""


@pytest.fixture
def sample_match_metadata() -> dict:
    """Sample match metadata."""
    return {
        "match_id": 19,
        "player1_name": "Fluffbunny",
        "player1_civ": "Kush",
        "player2_name": "Becked",
        "player2_civ": "Assyria",
        "winner_name": "Fluffbunny",
        "total_turns": 64,
    }


def test_generator_initialization() -> None:
    """Should initialize with API key."""
    generator = NarrativeGenerator(api_key="test-key")
    assert generator is not None


def test_generator_requires_api_key() -> None:
    """Should raise if API key is empty."""
    with pytest.raises(ValueError):
        NarrativeGenerator(api_key="")


@patch("tournament_visualizer.data.narrative_generator.AnthropicClient")
def test_generate_narrative_calls_llm_twice(
    mock_client_class: MagicMock,
    sample_formatted_events: str,
    sample_match_metadata: dict,
) -> None:
    """Should make two LLM calls: extraction then narrative."""
    # Mock the client
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    # Mock Pass 1 response (timeline extraction)
    mock_timeline_response = MagicMock()
    mock_timeline_response.content = [
        MagicMock(
            type="tool_use",
            input={
                "outcome": "Fluffbunny won",
                "key_events": [
                    {"turn": 51, "description": "War declared"}
                ],
                "player_stats": {
                    "Fluffbunny": {"cities": 7},
                    "Becked": {"cities": 5}
                }
            }
        )
    ]

    # Mock Pass 2 response (narrative generation)
    mock_narrative_response = "Fluffbunny defeated Becked via conquest."

    mock_client.generate_with_tools.return_value = mock_timeline_response
    mock_client.generate_text.return_value = mock_narrative_response

    # Run generation
    generator = NarrativeGenerator(api_key="test-key")
    result = generator.generate_narrative(
        formatted_events=sample_formatted_events,
        match_metadata=sample_match_metadata,
    )

    # Should have called LLM twice
    assert mock_client.generate_with_tools.call_count == 1
    assert mock_client.generate_text.call_count == 1

    # Should return narrative
    assert result == mock_narrative_response


@patch("tournament_visualizer.data.narrative_generator.AnthropicClient")
def test_generate_narrative_passes_events_to_extraction(
    mock_client_class: MagicMock,
    sample_formatted_events: str,
    sample_match_metadata: dict,
) -> None:
    """Pass 1 should receive formatted events."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_timeline_response = MagicMock()
    mock_timeline_response.content = [
        MagicMock(type="tool_use", input={"outcome": "Test"})
    ]
    mock_client.generate_with_tools.return_value = mock_timeline_response
    mock_client.generate_text.return_value = "Narrative"

    generator = NarrativeGenerator(api_key="test-key")
    generator.generate_narrative(
        formatted_events=sample_formatted_events,
        match_metadata=sample_match_metadata,
    )

    # Check that events were in the prompt
    call_args = mock_client.generate_with_tools.call_args
    messages = call_args.kwargs["messages"]
    prompt_text = messages[0]["content"]

    assert "Turn 1:" in prompt_text
    assert "Turn 51:" in prompt_text


@patch("tournament_visualizer.data.narrative_generator.AnthropicClient")
def test_generate_narrative_passes_timeline_to_writing(
    mock_client_class: MagicMock,
    sample_formatted_events: str,
    sample_match_metadata: dict,
) -> None:
    """Pass 2 should receive extracted timeline."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_timeline_response = MagicMock()
    mock_timeline_response.content = [
        MagicMock(
            type="tool_use",
            input={
                "outcome": "Fluffbunny won via conquest",
                "key_events": [],
                "player_stats": {}
            }
        )
    ]
    mock_client.generate_with_tools.return_value = mock_timeline_response
    mock_client.generate_text.return_value = "Narrative"

    generator = NarrativeGenerator(api_key="test-key")
    generator.generate_narrative(
        formatted_events=sample_formatted_events,
        match_metadata=sample_match_metadata,
    )

    # Check that timeline was in Pass 2 prompt
    call_args = mock_client.generate_text.call_args
    messages = call_args.kwargs["messages"]
    prompt_text = messages[0]["content"]

    assert "Fluffbunny won via conquest" in prompt_text
```

2. **Run tests (should fail):**
   ```bash
   uv run pytest tests/test_narrative_generator.py -v
   ```

3. **Create implementation:**

Create `tournament_visualizer/data/narrative_generator.py`:

```python
"""Generate AI-powered narrative summaries for tournament matches.

This module implements a two-pass approach:
1. Extract structured timeline from event stream (using tool calling)
2. Generate narrative prose from timeline

Example:
    >>> from tournament_visualizer.config import Config
    >>> generator = NarrativeGenerator(api_key=Config.ANTHROPIC_API_KEY)
    >>> narrative = generator.generate_narrative(
    ...     formatted_events=event_text,
    ...     match_metadata={"player1_name": "Alice", ...}
    ... )
    >>> print(narrative)
    Alice (Rome) defeated Bob (Carthage) via military conquest...
"""

import json
import logging
from typing import Any, TypedDict

from anthropic.types import MessageParam, ToolParam

from tournament_visualizer.data.anthropic_client import AnthropicClient

logger = logging.getLogger(__name__)


class MatchTimeline(TypedDict):
    """Structured timeline extracted from match events."""

    outcome: str
    key_events: list[dict[str, Any]]
    player_stats: dict[str, dict[str, Any]]


class NarrativeGenerator:
    """Generate narrative summaries using two-pass LLM approach.

    Pass 1: Extract structured timeline from events
    Pass 2: Write narrative prose from timeline

    Attributes:
        client: AnthropicClient instance
        model: Model name to use (default: Claude 3.5 Haiku)
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-haiku-20241022",
    ) -> None:
        """Initialize narrative generator.

        Args:
            api_key: Anthropic API key
            model: Model name to use

        Raises:
            ValueError: If api_key is empty
        """
        if not api_key:
            raise ValueError("API key is required")

        self.client = AnthropicClient(api_key=api_key)
        self.model = model

    def generate_narrative(
        self,
        formatted_events: str,
        match_metadata: dict[str, Any],
    ) -> str:
        """Generate narrative summary for a match.

        Args:
            formatted_events: Human-readable event text grouped by turn
            match_metadata: Match info (player names, civs, winner, turns)

        Returns:
            2-3 paragraph narrative summary

        Raises:
            anthropic.APIError: On API call failures
        """
        logger.info(
            f"Generating narrative for match {match_metadata.get('match_id')}"
        )

        # Pass 1: Extract timeline
        timeline = self._extract_timeline(formatted_events, match_metadata)
        logger.debug(f"Extracted timeline: {json.dumps(timeline, indent=2)}")

        # Pass 2: Generate narrative
        narrative = self._generate_narrative_text(timeline, match_metadata)
        logger.info(f"Generated narrative ({len(narrative)} chars)")

        return narrative

    def _extract_timeline(
        self,
        formatted_events: str,
        match_metadata: dict[str, Any],
    ) -> MatchTimeline:
        """Pass 1: Extract structured timeline from events.

        Args:
            formatted_events: Human-readable event text
            match_metadata: Match info

        Returns:
            Structured timeline with outcome, key events, stats
        """
        # Define timeline extraction tool
        timeline_tool: ToolParam = {
            "name": "extract_timeline",
            "description": "Extract a structured timeline from match events",
            "input_schema": {
                "type": "object",
                "properties": {
                    "outcome": {
                        "type": "string",
                        "description": "Brief outcome (who won and how, e.g. 'Fluffbunny (Kush) defeated Becked (Assyria) via military conquest after Becked surrendered')",
                    },
                    "key_events": {
                        "type": "array",
                        "description": "List of key turning points in chronological order",
                        "items": {
                            "type": "object",
                            "properties": {
                                "turn": {
                                    "type": "integer",
                                    "description": "Turn number when event occurred",
                                },
                                "description": {
                                    "type": "string",
                                    "description": "What happened (e.g., 'War declared', 'Tushpa captured')",
                                },
                            },
                            "required": ["turn", "description"],
                        },
                    },
                    "player_stats": {
                        "type": "object",
                        "description": "Summary statistics per player (cities founded, techs discovered, etc.)",
                        "additionalProperties": {
                            "type": "object",
                            "properties": {
                                "cities": {"type": "integer"},
                                "techs": {"type": "integer"},
                                "laws": {"type": "integer"},
                                "goals": {"type": "integer"},
                            },
                        },
                    },
                },
                "required": ["outcome", "key_events", "player_stats"],
            },
        }

        # Build prompt
        prompt = f"""You are analyzing a tournament match from the strategy game Old World.

Players:
- {match_metadata.get('player1_name')} ({match_metadata.get('player1_civ')})
- {match_metadata.get('player2_name')} ({match_metadata.get('player2_civ')})

Winner: {match_metadata.get('winner_name')}
Total Turns: {match_metadata.get('total_turns')}

Here are all the events that occurred during the match, grouped by turn:

{formatted_events}

Analyze these events and extract a structured timeline. Identify:
1. The outcome (who won and how)
2. Key turning points (war declarations, city captures, major strategic decisions)
3. Summary statistics for each player

Focus on events that shaped the match outcome. Ignore routine events like character births or minor diplomatic actions with tribes."""

        # Call API with tool
        messages: list[MessageParam] = [{"role": "user", "content": prompt}]
        response = self.client.generate_with_tools(
            messages=messages,
            tools=[timeline_tool],
            model=self.model,
        )

        # Extract tool use from response
        for block in response.content:
            if hasattr(block, "type") and block.type == "tool_use":
                return block.input  # type: ignore

        raise ValueError("No timeline extracted from LLM response")

    def _generate_narrative_text(
        self,
        timeline: MatchTimeline,
        match_metadata: dict[str, Any],
    ) -> str:
        """Pass 2: Generate narrative prose from timeline.

        Args:
            timeline: Structured timeline from Pass 1
            match_metadata: Match info

        Returns:
            2-3 paragraph narrative summary
        """
        # Build prompt with timeline
        timeline_json = json.dumps(timeline, indent=2)

        prompt = f"""You are writing a narrative summary for a tournament match from Old World.

Players:
- {match_metadata.get('player1_name')} ({match_metadata.get('player1_civ')})
- {match_metadata.get('player2_name')} ({match_metadata.get('player2_civ')})

Here is the structured timeline of key events:

{timeline_json}

Write a concise 2-3 paragraph narrative summary of this match. Focus on:
- The outcome and how it was achieved
- Key strategic decisions or turning points
- The overall story arc (peaceful development, economic advantage, military conflict, etc.)

Write in past tense. Be specific about turns and events. Make it engaging but factual.

DO NOT include section headers or labels. Just write the narrative prose."""

        messages: list[MessageParam] = [{"role": "user", "content": prompt}]
        narrative = self.client.generate_text(
            messages=messages,
            model=self.model,
        )

        return narrative.strip()
```

4. **Run tests (should pass):**
   ```bash
   uv run pytest tests/test_narrative_generator.py -v
   ```

5. **Manual test with real data:**
   ```bash
   uv run python -c "
from tournament_visualizer.data.narrative_generator import NarrativeGenerator
from tournament_visualizer.data.event_formatter import EventFormatter
from tournament_visualizer.config import Config
import duckdb

# Get match data
conn = duckdb.connect(Config.DUCKDB_PATH, read_only=True)

# Get match metadata
match_row = conn.execute('''
    SELECT
        m.match_id,
        p1.player_name as player1_name,
        p1.civilization as player1_civ,
        p2.player_name as player2_name,
        p2.civilization as player2_civ,
        pw.player_name as winner_name,
        m.total_turns
    FROM matches m
    LEFT JOIN players p1 ON m.match_id = p1.match_id AND m.player1_participant_id = p1.participant_id
    LEFT JOIN players p2 ON m.match_id = p2.match_id AND m.player2_participant_id = p2.participant_id
    LEFT JOIN players pw ON m.match_id = pw.match_id AND m.winner_participant_id = pw.participant_id
    WHERE m.match_id = 19
''').fetchone()

metadata = {
    'match_id': match_row[0],
    'player1_name': match_row[1],
    'player1_civ': match_row[2],
    'player2_name': match_row[3],
    'player2_civ': match_row[4],
    'winner_name': match_row[5],
    'total_turns': match_row[6],
}

# Get events
events = conn.execute('''
    SELECT
        e.turn_number,
        e.event_type,
        p.player_name,
        p.civilization,
        e.description,
        e.event_data
    FROM events e
    JOIN players p ON e.player_id = p.player_id
    WHERE e.match_id = 19
    ORDER BY e.turn_number
''').fetchall()

event_dicts = [
    {
        'turn_number': e[0],
        'event_type': e[1],
        'player_name': e[2],
        'civilization': e[3],
        'description': e[4],
        'event_data': e[5],
    }
    for e in events
]

conn.close()

# Format events
formatter = EventFormatter()
formatted = formatter.format_events(event_dicts)

# Generate narrative
generator = NarrativeGenerator(api_key=Config.ANTHROPIC_API_KEY)
narrative = generator.generate_narrative(
    formatted_events=formatted,
    match_metadata=metadata,
)

print('=== GENERATED NARRATIVE ===')
print(narrative)
print()
print(f'Characters: {len(narrative)}')
"
   ```

**Note:** This manual test will call the real Anthropic API and incur costs. Only run if you want to test end-to-end.

**Testing:**
- All pytest unit tests should pass (mocked)
- Manual test generates real narrative (if run)
- Narrative should be 2-3 paragraphs
- Should include specific turns and events
- Should be factually accurate based on timeline

**Commit checkpoint:**
```
test: Add tests for narrative generator

feat: Add narrative generator with two-pass LLM approach
```

(Two commits: tests first, then implementation)

---

### Task 6: Create Narrative Generation Script (45 min)

**Goal:** Command-line script to generate narratives for matches.

**Files to create:**
- `scripts/generate_match_narratives.py`

**Why this script:**
- Main entry point for narrative generation
- Handles command-line arguments (--force, --match-id)
- Queries database for matches and events
- Calls narrative generator
- Updates database with results
- Reports progress and errors

**Steps:**

1. **Look at existing script pattern:**
   ```bash
   head -100 scripts/link_players_to_participants.py
   ```

2. **Create `scripts/generate_match_narratives.py`:**

```python
#!/usr/bin/env python3
"""Generate AI-powered narrative summaries for tournament matches.

This script generates narrative summaries using Claude API and stores them
in the matches.narrative_summary column.

Usage:
    # Generate for matches without narratives
    uv run python scripts/generate_match_narratives.py

    # Force regenerate all narratives
    uv run python scripts/generate_match_narratives.py --force

    # Generate for specific match
    uv run python scripts/generate_match_narratives.py --match-id 19

    # Verbose logging
    uv run python scripts/generate_match_narratives.py --verbose
"""

import argparse
import logging
import sys
from typing import Any

import duckdb

from tournament_visualizer.config import Config
from tournament_visualizer.data.event_formatter import EventFormatter
from tournament_visualizer.data.narrative_generator import NarrativeGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_matches_to_process(
    conn: duckdb.DuckDBPyConnection,
    force: bool = False,
    match_id: int | None = None,
) -> list[int]:
    """Get list of match IDs to process.

    Args:
        conn: Database connection
        force: If True, process all matches regardless of existing narratives
        match_id: If provided, only process this specific match

    Returns:
        List of match IDs to process
    """
    if match_id:
        # Verify match exists
        result = conn.execute(
            "SELECT match_id FROM matches WHERE match_id = ?", [match_id]
        ).fetchone()
        if not result:
            logger.error(f"Match {match_id} not found")
            return []
        return [match_id]

    if force:
        # All matches
        query = "SELECT match_id FROM matches ORDER BY match_id"
    else:
        # Only matches without narratives
        query = """
            SELECT match_id
            FROM matches
            WHERE narrative_summary IS NULL
            ORDER BY match_id
        """

    results = conn.execute(query).fetchall()
    return [row[0] for row in results]


def get_match_metadata(
    conn: duckdb.DuckDBPyConnection, match_id: int
) -> dict[str, Any] | None:
    """Get metadata for a match.

    Args:
        conn: Database connection
        match_id: Match ID to fetch

    Returns:
        Match metadata dict or None if not found
    """
    query = """
        SELECT
            m.match_id,
            p1.player_name as player1_name,
            p1.civilization as player1_civ,
            p2.player_name as player2_name,
            p2.civilization as player2_civ,
            pw.player_name as winner_name,
            m.total_turns
        FROM matches m
        LEFT JOIN players p1 ON m.match_id = p1.match_id
            AND m.player1_participant_id = p1.participant_id
        LEFT JOIN players p2 ON m.match_id = p2.match_id
            AND m.player2_participant_id = p2.participant_id
        LEFT JOIN players pw ON m.match_id = pw.match_id
            AND m.winner_participant_id = pw.participant_id
        WHERE m.match_id = ?
    """

    result = conn.execute(query, [match_id]).fetchone()
    if not result:
        return None

    return {
        "match_id": result[0],
        "player1_name": result[1],
        "player1_civ": result[2],
        "player2_name": result[3],
        "player2_civ": result[4],
        "winner_name": result[5],
        "total_turns": result[6],
    }


def get_match_events(
    conn: duckdb.DuckDBPyConnection, match_id: int
) -> list[dict[str, Any]]:
    """Get all events for a match.

    Args:
        conn: Database connection
        match_id: Match ID to fetch events for

    Returns:
        List of event dicts
    """
    query = """
        SELECT
            e.turn_number,
            e.event_type,
            p.player_name,
            p.civilization,
            e.description,
            e.event_data
        FROM events e
        JOIN players p ON e.player_id = p.player_id
        WHERE e.match_id = ?
        ORDER BY e.turn_number, e.event_id
    """

    results = conn.execute(query, [match_id]).fetchall()

    return [
        {
            "turn_number": row[0],
            "event_type": row[1],
            "player_name": row[2],
            "civilization": row[3],
            "description": row[4],
            "event_data": row[5],
        }
        for row in results
    ]


def save_narrative(
    conn: duckdb.DuckDBPyConnection, match_id: int, narrative: str
) -> None:
    """Save narrative to database.

    Args:
        conn: Database connection
        match_id: Match ID to update
        narrative: Narrative text to save
    """
    conn.execute(
        "UPDATE matches SET narrative_summary = ? WHERE match_id = ?",
        [narrative, match_id],
    )
    conn.commit()


def process_match(
    conn: duckdb.DuckDBPyConnection,
    match_id: int,
    generator: NarrativeGenerator,
    formatter: EventFormatter,
) -> bool:
    """Process a single match to generate narrative.

    Args:
        conn: Database connection
        match_id: Match ID to process
        generator: Narrative generator instance
        formatter: Event formatter instance

    Returns:
        True if successful, False if error occurred
    """
    try:
        logger.info(f"Processing match {match_id}")

        # Get match metadata
        metadata = get_match_metadata(conn, match_id)
        if not metadata:
            logger.error(f"Match {match_id} metadata not found")
            return False

        # Get events
        events = get_match_events(conn, match_id)
        if not events:
            logger.warning(f"Match {match_id} has no events, skipping")
            return False

        logger.info(
            f"Match {match_id}: {metadata['player1_name']} ({metadata['player1_civ']}) "
            f"vs {metadata['player2_name']} ({metadata['player2_civ']}) - "
            f"{len(events)} events"
        )

        # Format events
        formatted_events = formatter.format_events(events)

        # Generate narrative
        narrative = generator.generate_narrative(
            formatted_events=formatted_events,
            match_metadata=metadata,
        )

        # Save to database
        save_narrative(conn, match_id, narrative)

        logger.info(
            f"Match {match_id}: Generated narrative ({len(narrative)} chars)"
        )
        return True

    except Exception as e:
        logger.error(f"Match {match_id}: Error - {e}", exc_info=True)
        return False


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        description="Generate narrative summaries for tournament matches"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate narratives for all matches (overwrite existing)",
    )
    parser.add_argument(
        "--match-id",
        type=int,
        help="Generate narrative for specific match ID only",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Check API key
    if not Config.ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY not found in environment")
        logger.error("Set it in .env file or environment variables")
        return 1

    # Initialize generator and formatter
    generator = NarrativeGenerator(api_key=Config.ANTHROPIC_API_KEY)
    formatter = EventFormatter()

    # Connect to database
    logger.info(f"Connecting to database: {Config.DUCKDB_PATH}")
    conn = duckdb.connect(Config.DUCKDB_PATH)

    try:
        # Get matches to process
        match_ids = get_matches_to_process(
            conn, force=args.force, match_id=args.match_id
        )

        if not match_ids:
            if args.force or args.match_id:
                logger.error("No matches found to process")
                return 1
            else:
                logger.info("No matches need narratives (all up to date)")
                return 0

        logger.info(f"Processing {len(match_ids)} matches")

        # Process each match
        success_count = 0
        error_count = 0

        for match_id in match_ids:
            if process_match(conn, match_id, generator, formatter):
                success_count += 1
            else:
                error_count += 1

        # Summary
        logger.info("=" * 60)
        logger.info(f"Processed {len(match_ids)} matches")
        logger.info(f"  Success: {success_count}")
        logger.info(f"  Errors:  {error_count}")

        return 0 if error_count == 0 else 1

    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
```

3. **Add ANTHROPIC_API_KEY to Config:**

Edit `tournament_visualizer/config.py` and add:

```python
# Add after existing API key configs
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
```

4. **Test the script:**

**Dry run (should list matches but not process without API key set):**
```bash
# Check what would be processed
uv run python scripts/generate_match_narratives.py
```

**Test with specific match (requires API key):**
```bash
# Set API key temporarily (or add to .env)
export ANTHROPIC_API_KEY="your-key-here"

# Process one match
uv run python scripts/generate_match_narratives.py --match-id 19 --verbose
```

**Verify narrative was saved:**
```bash
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT
    match_id,
    LENGTH(narrative_summary) as narrative_length,
    SUBSTR(narrative_summary, 1, 100) as narrative_preview
FROM matches
WHERE match_id = 19
"
```

**Testing:**
- Script should run without errors
- Should handle missing API key gracefully
- Should process matches and save narratives to database
- Should log progress clearly
- Error handling should skip failed matches and continue

**Commit checkpoint:**
```
feat: Add script to generate match narratives
```

---

### Task 7: Update Sync Script (15 min)

**Goal:** Add narrative generation to main sync workflow.

**Files to modify:**
- `scripts/sync_tournament_data.sh`

**Steps:**

1. **Open and review current sync script:**
   ```bash
   cat scripts/sync_tournament_data.sh
   ```

2. **Add narrative generation step:**

Find the section where scripts are run (after import, before linking participants).

Add this block after `import_attachments.py` and before `link_players_to_participants.py`:

```bash
# Generate match narratives (only for matches without narratives)
echo "Generating match narratives..."
if ! uv run python scripts/generate_match_narratives.py; then
    echo "Warning: Narrative generation failed, continuing..."
    # Don't exit - narratives are non-critical
fi
```

**Important:** Place this AFTER import but BEFORE upload to Fly.io. The narratives should be generated locally before the database is uploaded.

**Full context - the order should be:**
1. Download attachments
2. Import attachments to database
3. **Generate narratives** ← NEW STEP
4. Link players to participants
5. Upload to Fly.io (if applicable)

3. **Test locally:**
   ```bash
   # Test the full sync workflow
   # (This will call real APIs, only run if you want to test end-to-end)
   ./scripts/sync_tournament_data.sh
   ```

**Testing:**
- Script should run narrative generation step
- If generation fails, script should continue (not exit)
- Narratives should be generated before upload
- Overall workflow should complete successfully

**Commit checkpoint:**
```
feat: Add narrative generation to sync workflow
```

---

### Task 8: Testing & Validation (30 min)

**Goal:** Comprehensive testing of the complete system.

**Steps:**

1. **Run all unit tests:**
   ```bash
   uv run pytest tests/test_event_formatter.py tests/test_narrative_generator.py -v
   ```

2. **Test script with different flags:**
   ```bash
   # Help text
   uv run python scripts/generate_match_narratives.py --help

   # Process missing narratives (should be none if Task 6 ran)
   uv run python scripts/generate_match_narratives.py

   # Force regenerate one match
   uv run python scripts/generate_match_narratives.py --match-id 19 --force

   # Verbose mode
   uv run python scripts/generate_match_narratives.py --match-id 19 --verbose
   ```

3. **Validate database state:**
   ```bash
   # Count matches with narratives
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT
       COUNT(*) as total_matches,
       COUNT(narrative_summary) as with_narratives,
       ROUND(COUNT(narrative_summary) * 100.0 / COUNT(*), 1) as coverage_pct
   FROM matches
   "

   # Check narrative lengths
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT
       match_id,
       LENGTH(narrative_summary) as chars,
       LENGTH(narrative_summary) - LENGTH(REPLACE(narrative_summary, ' ', '')) as words_approx
   FROM matches
   WHERE narrative_summary IS NOT NULL
   ORDER BY match_id
   LIMIT 10
   "

   # View a few narratives
   uv run duckdb data/tournament_data.duckdb -readonly -c "
   SELECT
       match_id,
       narrative_summary
   FROM matches
   WHERE narrative_summary IS NOT NULL
   LIMIT 3
   "
   ```

4. **Quality checks:**
   - Do narratives mention both players?
   - Do they mention the winner?
   - Do they reference specific turns or events?
   - Are they 2-3 paragraphs (roughly 200-600 words)?
   - Do they make factual sense given the events?

5. **Error handling tests:**
   ```bash
   # Try with invalid match ID
   uv run python scripts/generate_match_narratives.py --match-id 99999

   # Try without API key (should fail gracefully)
   ANTHROPIC_API_KEY="" uv run python scripts/generate_match_narratives.py --match-id 19
   ```

6. **Run code quality checks:**
   ```bash
   # Format code
   uv run black tournament_visualizer/data/anthropic_client.py
   uv run black tournament_visualizer/data/event_formatter.py
   uv run black tournament_visualizer/data/narrative_generator.py
   uv run black scripts/generate_match_narratives.py

   # Lint code
   uv run ruff check tournament_visualizer/data/anthropic_client.py
   uv run ruff check tournament_visualizer/data/event_formatter.py
   uv run ruff check tournament_visualizer/data/narrative_generator.py
   uv run ruff check scripts/generate_match_narratives.py

   # Fix any auto-fixable issues
   uv run ruff check --fix tournament_visualizer/
   uv run ruff check --fix scripts/
   ```

**Testing checklist:**
- [ ] All unit tests pass
- [ ] Script runs without errors
- [ ] Narratives are generated and saved
- [ ] Database schema is correct
- [ ] Error handling works (invalid match, missing API key)
- [ ] Code is formatted (black)
- [ ] Code passes linting (ruff)
- [ ] Narratives are factually accurate
- [ ] Narratives are appropriate length

**Commit checkpoint:**
```
test: Validate narrative generation system
```

---

### Task 9: Documentation (20 min)

**Goal:** Update project documentation with narrative generation info.

**Files to modify:**
- `CLAUDE.md`
- `docs/developer-guide.md` (if it exists and is relevant)

**Steps:**

1. **Update CLAUDE.md:**

Add a new section after the "Pick Order Data Integration" section:

```markdown
## Match Narrative Summaries

### Overview

Tournament matches include AI-generated narrative summaries on match detail pages.

**How it works:**
- Analyzes all match events (techs, laws, combat, cities, etc.)
- Uses Claude API with two-pass approach:
  1. Extract structured timeline from events
  2. Generate 2-3 paragraph narrative from timeline
- Stored in `matches.narrative_summary` column

### Generation

**Local Development:**

Generate narratives for matches without summaries:
```bash
uv run python scripts/generate_match_narratives.py
```

Regenerate specific match:
```bash
uv run python scripts/generate_match_narratives.py --match-id 19 --force
```

Regenerate all narratives:
```bash
uv run python scripts/generate_match_narratives.py --force
```

**Production Sync:**

Narratives are automatically generated during sync:
```bash
./scripts/sync_tournament_data.sh
```

This generates narratives locally before uploading database to Fly.io.

### Requirements

**API Key:**
- `ANTHROPIC_API_KEY` must be set in `.env`
- Get key from https://console.anthropic.com/

**For production (Fly.io):**
```bash
fly secrets set ANTHROPIC_API_KEY="your_key" -a prospector
```

### Database Schema

```sql
-- Narratives stored in matches table
ALTER TABLE matches ADD COLUMN narrative_summary TEXT;
```

See `docs/migrations/009_add_match_narrative_summary.md` for details.

### Implementation

**Modules:**
- `tournament_visualizer/data/anthropic_client.py` - API client with retry logic
- `tournament_visualizer/data/event_formatter.py` - Format events for LLM
- `tournament_visualizer/data/narrative_generator.py` - Two-pass generation

**Scripts:**
- `scripts/generate_match_narratives.py` - Generate narratives

**Tests:**
- `tests/test_event_formatter.py`
- `tests/test_narrative_generator.py`

### Troubleshooting

**No narratives generated:**
- Check `ANTHROPIC_API_KEY` is set
- Run with `--verbose` flag to see errors
- Check API quota/billing at https://console.anthropic.com/

**API errors:**
- Rate limits handled with exponential backoff
- Transient errors retried automatically
- Persistent errors logged and skipped

**Narrative quality issues:**
- Regenerate specific match with `--force`
- Check event data quality in database
- Review prompts in `narrative_generator.py`
```

2. **Update migration status:**

Edit `docs/migrations/009_add_match_narrative_summary.md` and change:
```markdown
**Status:** Completed
```

3. **Test documentation:**
   - Read through additions
   - Verify all commands work as documented
   - Check markdown formatting

**Commit checkpoint:**
```
docs: Add narrative generation documentation to CLAUDE.md

docs: Mark migration 009 as completed
```

(Two commits: one for CLAUDE.md, one for migration status)

---

## Summary

### What We Built

1. **Database Schema:**
   - Added `narrative_summary` column to `matches` table
   - Stores AI-generated 2-3 paragraph summaries

2. **Core Modules:**
   - `anthropic_client.py` - Anthropic API client with retry logic
   - `event_formatter.py` - Formats events for LLM consumption
   - `narrative_generator.py` - Two-pass narrative generation

3. **Scripts:**
   - `generate_match_narratives.py` - CLI tool to generate narratives
   - Updated `sync_tournament_data.sh` - Integrated into sync workflow

4. **Tests:**
   - Unit tests for event formatter
   - Unit tests for narrative generator
   - Validation of database state

5. **Documentation:**
   - Migration documentation
   - Usage instructions in CLAUDE.md

### Verification Checklist

Before considering this complete:

- [ ] All unit tests pass (`pytest`)
- [ ] Code is formatted (`black`)
- [ ] Code passes linting (`ruff`)
- [ ] Database migration applied successfully
- [ ] Narratives can be generated for test matches
- [ ] Narratives are factually accurate
- [ ] Script handles errors gracefully
- [ ] Documentation is complete and accurate
- [ ] Sync workflow includes narrative generation
- [ ] All commits are atomic with clear messages

### Next Steps (Not Part of This Implementation)

Future enhancements could include:
- Display narratives on match detail pages in web UI
- Add regenerate button for manual updates
- Track narrative generation metadata (when generated, model version)
- A/B test different prompt strategies
- Support for other LLM providers

---

## Appendix: Useful Commands

### Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest tests/test_event_formatter.py -v
uv run pytest tests/test_narrative_generator.py -v

# Format code
uv run black tournament_visualizer/ scripts/

# Lint code
uv run ruff check tournament_visualizer/ scripts/
uv run ruff check --fix tournament_visualizer/ scripts/
```

### Database Operations

```bash
# Backup database
cp data/tournament_data.duckdb data/tournament_data.duckdb.backup_$(date +%Y%m%d_%H%M%S)

# Check schema
uv run duckdb data/tournament_data.duckdb -readonly -c "DESCRIBE matches"

# View narratives
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT match_id, narrative_summary
FROM matches
WHERE narrative_summary IS NOT NULL
LIMIT 5
"
```

### Narrative Generation

```bash
# Generate for missing matches
uv run python scripts/generate_match_narratives.py

# Regenerate specific match
uv run python scripts/generate_match_narratives.py --match-id 19 --force

# Regenerate all
uv run python scripts/generate_match_narratives.py --force

# Verbose logging
uv run python scripts/generate_match_narratives.py --verbose
```

### Production Deployment

```bash
# Set API key on Fly.io
fly secrets set ANTHROPIC_API_KEY="your_key" -a prospector

# Full sync (includes narrative generation)
./scripts/sync_tournament_data.sh
```
