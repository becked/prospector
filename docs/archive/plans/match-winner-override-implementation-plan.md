# Match Winner Override System - Implementation Plan

> **Status**: Completed and archived (2025-10-25)
>
> Override systems complete and documented in CLAUDE.md (Override Systems Design section).

## Problem Statement

Tournament save files can have incorrect winner data for several reasons:
1. **Old World bug**: Players cannot locate completed save files, requiring manual intervention
2. **Manual corruption**: Tournament organizers open saves and surrender the wrong player to reveal the map
3. **Missing data**: Save files lack TeamVictoriesCompleted stanzas for proper winner determination

**Real-world example**: Match #426504724 (PBM vs MongrelEyes) has the wrong winner in the save file because the TO manually opened it and surrendered the wrong player to reveal the map. The file shows MongrelEyes won, but PBM actually won.

## Solution

Implement a match winner override system that:
- Maintains a JSON file mapping match IDs to correct winners
- Checks overrides first during data import, falls back to save file data
- Lives in `/data/` mount on Fly.io for persistence across deployments
- Includes validation, logging, and documentation

## Architecture Overview

### Data Flow

```
Import Process (scripts/import_attachments.py)
    ↓
ETL Pipeline (tournament_visualizer/data/etl.py)
    ↓
Parse Save File (tournament_visualizer/data/parser.py)
    ↓
Load Override Config (NEW: data/match_winner_overrides.json)
    ↓
Apply Override if exists → Otherwise use parsed winner
    ↓
Store in match_winners table (tournament_visualizer/data/database.py)
```

### File Structure

```
data/
├── tournament_data.duckdb              # Existing database
├── match_winner_overrides.json         # NEW: Override file (not in git)
└── match_winner_overrides.json.example # NEW: Template (in git)

tournament_visualizer/data/
├── etl.py          # MODIFY: Load and apply overrides
├── parser.py       # NO CHANGES NEEDED
└── database.py     # NO CHANGES NEEDED (already has match_winners table)

scripts/
├── import_attachments.py               # NO CHANGES NEEDED
└── sync_tournament_data.sh             # MODIFY: Upload override file

tests/
├── test_winner_overrides.py            # NEW: Tests for override system
└── fixtures/
    └── test_overrides.json             # NEW: Test data
```

## Database Schema

**NO SCHEMA CHANGES NEEDED!** The system already has:

```sql
CREATE TABLE match_winners (
    match_id BIGINT PRIMARY KEY REFERENCES matches(match_id),
    winner_player_id BIGINT NOT NULL REFERENCES players(player_id),
    winner_determination_method VARCHAR(50) DEFAULT 'automatic',
    determined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

The `winner_determination_method` field tracks how winner was determined:
- `'parser_determined'` - From save file TeamVictoriesCompleted stanza
- `'score_based'` - Fallback when no victory data exists
- `'manual_override'` - NEW value for override system

## JSON File Format

### Production File: `data/match_winner_overrides.json`

**Simple structure** (direct lookup, O(1) performance):

```json
{
  "426504724": {
    "winner_player_name": "PBM",
    "reason": "TO manually surrendered wrong player to reveal map",
    "date_added": "2025-10-16",
    "notes": "MongrelEyes shown in save but PBM actually won"
  },
  "999999999": {
    "winner_player_name": "seasand",
    "reason": "Player conceded between play sessions",
    "date_added": "2025-10-16",
    "notes": "Cycle4x conceded but save file shows them as winner"
  }
}
```

**Key design decisions:**
- **Match IDs are strings** (JSON limitation, converted to int in code)
- **Use player_name not player_id** (player_id is database-specific, name is stable)
- **Required fields**: `winner_player_name`, `reason`
- **Optional fields**: `date_added`, `notes`
- **No version field** (YAGNI - can add later if format evolves)

### Example File: `data/match_winner_overrides.json.example`

```json
{
  "_comment": "Match winner overrides for corrupted save files",
  "_instructions": [
    "Copy this file to match_winner_overrides.json and add your overrides",
    "Match IDs must be strings (JSON limitation)",
    "winner_player_name must match the exact player name from save file",
    "Required fields: winner_player_name, reason",
    "Optional fields: date_added, notes"
  ],
  "426504724": {
    "winner_player_name": "PBM",
    "reason": "TO manually surrendered wrong player to reveal map",
    "date_added": "2025-10-16",
    "notes": "Example: MongrelEyes shown in save but PBM actually won"
  }
}
```

## Implementation Tasks

### Task 1: Create Override Module

**File**: `tournament_visualizer/data/winner_overrides.py`

**Purpose**: Centralized logic for loading, validating, and applying overrides

**Implementation**:

```python
"""Match winner override system for corrupted save files.

This module handles loading and applying manual winner overrides for matches
where the save file contains incorrect winner data due to bugs or manual
intervention.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class MatchWinnerOverrides:
    """Manages match winner overrides from JSON configuration."""

    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialize override system.

        Args:
            config_path: Path to override JSON file (default: data/match_winner_overrides.json)
        """
        self.config_path = Path(config_path or "data/match_winner_overrides.json")
        self.overrides: Dict[str, Dict[str, Any]] = {}
        self._load_overrides()

    def _load_overrides(self) -> None:
        """Load overrides from JSON file.

        Validates format and logs warnings for any issues.
        Missing file is not an error - system works without overrides.
        """
        if not self.config_path.exists():
            logger.info(
                f"No override file found at {self.config_path} - using save file winners"
            )
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Filter out comment/instruction fields
            self.overrides = {
                k: v for k, v in data.items() if not k.startswith("_")
            }

            logger.info(
                f"Loaded {len(self.overrides)} match winner overrides from {self.config_path}"
            )

            # Validate each override
            for match_id, override_data in self.overrides.items():
                self._validate_override(match_id, override_data)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {self.config_path}: {e}")
            self.overrides = {}
        except Exception as e:
            logger.error(f"Error loading overrides from {self.config_path}: {e}")
            self.overrides = {}

    def _validate_override(
        self, match_id: str, override_data: Dict[str, Any]
    ) -> bool:
        """Validate a single override entry.

        Args:
            match_id: Challonge match ID as string
            override_data: Override configuration dict

        Returns:
            True if valid, False if invalid (logs warning)
        """
        # Check required fields
        if "winner_player_name" not in override_data:
            logger.warning(
                f"Override for match {match_id} missing required field 'winner_player_name'"
            )
            return False

        if "reason" not in override_data:
            logger.warning(
                f"Override for match {match_id} missing required field 'reason'"
            )
            return False

        # Validate types
        if not isinstance(override_data["winner_player_name"], str):
            logger.warning(
                f"Override for match {match_id}: winner_player_name must be string"
            )
            return False

        return True

    def get_override_winner(
        self, challonge_match_id: Optional[int]
    ) -> Optional[str]:
        """Get override winner player name for a match.

        Args:
            challonge_match_id: Challonge match ID (can be None for local files)

        Returns:
            Winner player name if override exists, None otherwise
        """
        if challonge_match_id is None:
            return None

        # Convert to string for JSON lookup
        match_id_str = str(challonge_match_id)

        if match_id_str in self.overrides:
            override = self.overrides[match_id_str]
            winner_name = override["winner_player_name"]
            reason = override.get("reason", "unknown")

            logger.info(
                f"Applying winner override for match {challonge_match_id}: "
                f"winner={winner_name}, reason={reason}"
            )

            return winner_name

        return None

    def has_override(self, challonge_match_id: Optional[int]) -> bool:
        """Check if an override exists for a match.

        Args:
            challonge_match_id: Challonge match ID

        Returns:
            True if override exists
        """
        if challonge_match_id is None:
            return False
        return str(challonge_match_id) in self.overrides


# Global instance for convenience
_overrides_instance: Optional[MatchWinnerOverrides] = None


def get_overrides() -> MatchWinnerOverrides:
    """Get or create the global overrides instance.

    Returns:
        Global MatchWinnerOverrides instance
    """
    global _overrides_instance
    if _overrides_instance is None:
        _overrides_instance = MatchWinnerOverrides()
    return _overrides_instance
```

**Testing strategy**:
- Unit tests for loading valid JSON
- Unit tests for handling invalid JSON (malformed, missing fields)
- Unit tests for missing file (should not error)
- Integration test with actual override application

**Time estimate**: 1-2 hours (including tests)

**Commit**: `feat: Add match winner override loading system`

---

### Task 2: Integrate Overrides into ETL Pipeline

**File**: `tournament_visualizer/data/etl.py`

**Changes**: Modify `_load_tournament_data` method to check for overrides

**Current code** (lines 106-140):

```python
def _load_tournament_data(self, parsed_data: Dict[str, Any]) -> None:
    """Load parsed tournament data into the database."""
    # Start with match data (without winner_player_id for now)
    match_metadata = parsed_data["match_metadata"].copy()
    original_winner_id = match_metadata.pop("winner_player_id", None)
    match_id = self.db.insert_match(match_metadata)

    logger.info(f"Inserted match with ID: {match_id}")

    # Process players
    players_data = parsed_data["players"]
    player_id_mapping = {}  # Map original index to database ID
    winner_db_id = None

    for i, player_data in enumerate(players_data):
        player_data["match_id"] = match_id
        player_id = self.db.insert_player(player_data)
        original_player_id = i + 1  # Assuming 1-based indexing
        player_id_mapping[original_player_id] = player_id

        # Check if this is the winner
        if original_winner_id and original_player_id == original_winner_id:
            winner_db_id = player_id

    logger.info(f"Inserted {len(players_data)} players")

    # Insert winner information into separate table
    if winner_db_id:
        self.db.insert_match_winner(match_id, winner_db_id, "parser_determined")
        logger.info(f"Recorded winner: player_id {winner_db_id}")
```

**New code** (modify lines 106-140):

```python
def _load_tournament_data(self, parsed_data: Dict[str, Any]) -> None:
    """Load parsed tournament data into the database.

    Winner determination priority:
    1. Manual override (from match_winner_overrides.json)
    2. Parser-determined (from save file TeamVictoriesCompleted)
    3. No winner recorded (None)
    """
    # Start with match data (without winner_player_id for now)
    match_metadata = parsed_data["match_metadata"].copy()
    original_winner_id = match_metadata.pop("winner_player_id", None)
    challonge_match_id = match_metadata.get("challonge_match_id")
    match_id = self.db.insert_match(match_metadata)

    logger.info(f"Inserted match with ID: {match_id}")

    # Check for manual override BEFORE processing players
    from .winner_overrides import get_overrides
    overrides = get_overrides()
    override_winner_name = overrides.get_override_winner(challonge_match_id)

    # Process players
    players_data = parsed_data["players"]
    player_id_mapping = {}  # Map original index to database ID
    player_name_to_db_id = {}  # Map player name to database ID
    winner_db_id = None
    winner_method = "parser_determined"

    for i, player_data in enumerate(players_data):
        player_data["match_id"] = match_id
        player_id = self.db.insert_player(player_data)
        original_player_id = i + 1  # Assuming 1-based indexing
        player_id_mapping[original_player_id] = player_id

        # Track player names for override lookup
        player_name = player_data["player_name"]
        player_name_to_db_id[player_name] = player_id

        # Check if this is the winner (override takes precedence)
        if override_winner_name:
            if player_name == override_winner_name:
                winner_db_id = player_id
                winner_method = "manual_override"
        elif original_winner_id and original_player_id == original_winner_id:
            winner_db_id = player_id

    logger.info(f"Inserted {len(players_data)} players")

    # Validate override was applied if requested
    if override_winner_name and not winner_db_id:
        logger.error(
            f"Override winner '{override_winner_name}' not found in player list "
            f"for match {challonge_match_id}. Available players: {list(player_name_to_db_id.keys())}"
        )
        # Fall back to parser-determined winner
        for i, player_data in enumerate(players_data):
            original_player_id = i + 1
            if original_winner_id and original_player_id == original_winner_id:
                winner_db_id = player_id_mapping[original_player_id]
                winner_method = "parser_determined"
                logger.warning(
                    f"Falling back to parser-determined winner for match {challonge_match_id}"
                )
                break

    # Insert winner information into separate table
    if winner_db_id:
        self.db.insert_match_winner(match_id, winner_db_id, winner_method)
        logger.info(
            f"Recorded winner: player_id {winner_db_id} (method: {winner_method})"
        )
```

**Testing strategy**:
- Unit test: Override applied correctly when match ID matches
- Unit test: Parser winner used when no override exists
- Unit test: Error handling when override player name not found
- Integration test: Full import with override file

**Time estimate**: 1 hour (including tests)

**Commit**: `feat: Integrate winner overrides into ETL pipeline`

---

### Task 3: Update Sync Script for Fly.io Deployment

**File**: `scripts/sync_tournament_data.sh`

**Changes**: Add upload of override file after database upload

**Location**: After line 146 (after database verification)

**Add these lines**:

```bash
# Step 4.5: Upload override file if it exists
if [ -f "data/match_winner_overrides.json" ]; then
    echo -e "${YELLOW}[4.5/5] Uploading match winner overrides...${NC}"

    if echo "put data/match_winner_overrides.json /data/match_winner_overrides.json" | fly ssh sftp shell -a "${APP_NAME}"; then
        echo -e "${GREEN}✓ Override file uploaded${NC}"

        # Fix permissions
        fly ssh console -a "${APP_NAME}" -C "chmod 664 /data/match_winner_overrides.json" 2>/dev/null
        fly ssh console -a "${APP_NAME}" -C "chown appuser:appuser /data/match_winner_overrides.json" 2>/dev/null
    else
        echo -e "${YELLOW}Warning: Could not upload override file${NC}"
    fi

    echo ""
else
    echo -e "${BLUE}No override file found - skipping upload${NC}"
    echo ""
fi
```

**Testing strategy**:
- Manual test: Run sync script with override file present
- Manual test: Run sync script without override file
- Verify file permissions on Fly.io after upload

**Time estimate**: 30 minutes (including testing)

**Commit**: `feat: Upload match winner overrides in sync script`

---

### Task 4: Create Example Override File

**File**: `data/match_winner_overrides.json.example`

**Content**: (see JSON format section above)

**Add to `.gitignore`**:

```
# Match winner overrides (production data, not versioned)
data/match_winner_overrides.json
```

**Testing strategy**:
- Verify example file is valid JSON
- Verify actual override file is git-ignored
- Verify example file contains clear instructions

**Time estimate**: 15 minutes

**Commit**: `docs: Add match winner override example file`

---

### Task 5: Write Comprehensive Tests

**File**: `tests/test_winner_overrides.py`

**Test coverage**:

```python
"""Tests for match winner override system."""

import json
import tempfile
from pathlib import Path

import pytest

from tournament_visualizer.data.winner_overrides import MatchWinnerOverrides


class TestMatchWinnerOverrides:
    """Tests for MatchWinnerOverrides class."""

    def test_load_valid_overrides(self, tmp_path: Path) -> None:
        """Test loading valid override file."""
        override_file = tmp_path / "overrides.json"
        override_file.write_text(
            json.dumps(
                {
                    "12345": {
                        "winner_player_name": "PlayerOne",
                        "reason": "Test reason",
                        "date_added": "2025-10-16",
                    }
                }
            )
        )

        overrides = MatchWinnerOverrides(str(override_file))

        assert overrides.has_override(12345)
        assert overrides.get_override_winner(12345) == "PlayerOne"
        assert not overrides.has_override(99999)

    def test_missing_file_not_error(self, tmp_path: Path) -> None:
        """Test that missing override file doesn't raise error."""
        missing_file = tmp_path / "does_not_exist.json"

        overrides = MatchWinnerOverrides(str(missing_file))

        assert not overrides.has_override(12345)
        assert overrides.get_override_winner(12345) is None

    def test_invalid_json_handled(self, tmp_path: Path) -> None:
        """Test that invalid JSON is handled gracefully."""
        override_file = tmp_path / "invalid.json"
        override_file.write_text("{ invalid json content }")

        overrides = MatchWinnerOverrides(str(override_file))

        # Should not crash, just log error and have no overrides
        assert not overrides.has_override(12345)

    def test_missing_required_fields(self, tmp_path: Path) -> None:
        """Test validation of required fields."""
        override_file = tmp_path / "missing_fields.json"
        override_file.write_text(
            json.dumps(
                {
                    "12345": {
                        "winner_player_name": "PlayerOne"
                        # Missing 'reason' field
                    },
                    "67890": {
                        "reason": "Test reason"
                        # Missing 'winner_player_name' field
                    },
                }
            )
        )

        overrides = MatchWinnerOverrides(str(override_file))

        # Both should be loaded but validation warnings logged
        # (validation is informational, doesn't block loading)
        assert len(overrides.overrides) == 2

    def test_comment_fields_ignored(self, tmp_path: Path) -> None:
        """Test that _comment and _instructions fields are filtered out."""
        override_file = tmp_path / "with_comments.json"
        override_file.write_text(
            json.dumps(
                {
                    "_comment": "This is a comment",
                    "_instructions": ["Do this", "Do that"],
                    "12345": {
                        "winner_player_name": "PlayerOne",
                        "reason": "Test",
                    },
                }
            )
        )

        overrides = MatchWinnerOverrides(str(override_file))

        # Only the actual override should be loaded
        assert len(overrides.overrides) == 1
        assert overrides.has_override(12345)

    def test_none_match_id_returns_none(self) -> None:
        """Test that None match ID returns None (local files)."""
        overrides = MatchWinnerOverrides()

        assert not overrides.has_override(None)
        assert overrides.get_override_winner(None) is None


class TestETLIntegration:
    """Integration tests for override system in ETL pipeline."""

    def test_override_applied_in_etl(
        self, test_save_file: Path, override_file: Path
    ) -> None:
        """Test that overrides are applied during ETL import.

        This test requires:
        1. A test save file with incorrect winner
        2. An override file with correct winner
        3. Verification that override winner is stored in database
        """
        # TODO: Implement integration test
        # This requires setting up a test database and test save file
        # Left as skeleton for developer to complete
        pass
```

**Test fixtures** (`tests/fixtures/test_overrides.json`):

```json
{
  "12345": {
    "winner_player_name": "TestPlayer",
    "reason": "Test override reason",
    "date_added": "2025-10-16"
  }
}
```

**Testing strategy**:
- Run pytest with coverage: `uv run pytest tests/test_winner_overrides.py -v --cov=tournament_visualizer.data.winner_overrides`
- Target: >90% code coverage
- Run tests on CI/CD if available

**Time estimate**: 2 hours (writing tests + achieving coverage)

**Commit**: `test: Add comprehensive tests for winner override system`

---

### Task 6: Update Documentation

**File**: `CLAUDE.md`

**Add section** (under "## Old World Save File Structure"):

```markdown
### Match Winner Overrides

**Problem**: Some save files have incorrect winner data due to:
- Old World bug preventing access to completed saves
- Manual corruption from TO opening files to reveal maps
- Missing TeamVictoriesCompleted data

**Solution**: Manual override system via JSON configuration

**Location**: `data/match_winner_overrides.json` (not in git)

**Format**:
```json
{
  "challonge_match_id": {
    "winner_player_name": "PlayerName",
    "reason": "Why this override is needed",
    "date_added": "YYYY-MM-DD",
    "notes": "Optional additional context"
  }
}
```

**Usage**:
1. Copy `data/match_winner_overrides.json.example` to `data/match_winner_overrides.json`
2. Add override entry for problematic match
3. Re-import data: `uv run python scripts/import_attachments.py --force`
4. For production: `./scripts/sync_tournament_data.sh` (uploads override file automatically)

**Priority**: Overrides take precedence over save file data
**Logging**: Check logs for "Applying winner override" messages
**Validation**: Errors logged if override player name not found in save file
```

**Testing strategy**:
- Proofread for clarity
- Verify all commands are accurate
- Test commands on fresh clone

**Time estimate**: 30 minutes

**Commit**: `docs: Document match winner override system`

---

### Task 7: Create Real Override File for Production

**File**: `data/match_winner_overrides.json` (local only)

**Content**:

```json
{
  "426504724": {
    "winner_player_name": "PBM",
    "reason": "TO manually surrendered wrong player to reveal map",
    "date_added": "2025-10-16",
    "notes": "MongrelEyes shown in save file but PBM actually won. Confirmed by TO and match observation."
  }
}
```

**Testing strategy**:
- Run local import with this file
- Verify PBM is recorded as winner
- Check database: `SELECT * FROM match_winners WHERE match_id = <id>`
- Verify `winner_determination_method = 'manual_override'`

**Time estimate**: 15 minutes

**Commit**: None (file not in git)

**Deployment**: Will be uploaded via sync script in Task 8

---

### Task 8: Deploy to Production

**Steps**:

1. **Verify local testing complete**:
   ```bash
   # Run all tests
   uv run pytest tests/test_winner_overrides.py -v

   # Test local import with override
   uv run python scripts/import_attachments.py --force --verbose

   # Verify winner in database
   uv run duckdb data/tournament_data.duckdb -c "
     SELECT m.game_name, p.player_name, mw.winner_determination_method
     FROM matches m
     JOIN match_winners mw ON m.match_id = mw.match_id
     JOIN players p ON mw.winner_player_id = p.player_id
     WHERE m.challonge_match_id = 426504724
   "
   ```

2. **Deploy to Fly.io**:
   ```bash
   # Sync data (includes override file upload)
   ./scripts/sync_tournament_data.sh
   ```

3. **Verify production**:
   ```bash
   # Check Fly.io logs
   fly logs -a prospector | grep "override"

   # SSH to verify file exists
   fly ssh console -a prospector -C "ls -la /data/match_winner_overrides.json"

   # Check app for correct winner display
   # Visit: https://prospector.fly.dev/matches
   ```

**Rollback plan**:
```bash
# If issues occur, remove override file and restart
fly ssh console -a prospector -C "rm /data/match_winner_overrides.json"
fly machine restart <machine-id> -a prospector
```

**Testing strategy**:
- Smoke test production after deployment
- Verify correct winner displayed for match #426504724
- Check logs for any errors

**Time estimate**: 30 minutes

**Commit**: None (production data)

---

## Testing Checklist

### Unit Tests
- [ ] MatchWinnerOverrides loads valid JSON
- [ ] MatchWinnerOverrides handles missing file gracefully
- [ ] MatchWinnerOverrides handles invalid JSON gracefully
- [ ] Override validation catches missing required fields
- [ ] Comment fields (_comment, _instructions) are filtered out
- [ ] None match ID returns None (for local files)

### Integration Tests
- [ ] Override applied during full ETL import
- [ ] Parser winner used when no override exists
- [ ] Error logged when override player name not found
- [ ] Database stores correct winner_determination_method

### Manual Tests
- [ ] Local import with override file works
- [ ] Local import without override file works
- [ ] Sync script uploads override file to Fly.io
- [ ] Sync script works when override file missing
- [ ] Production database shows correct winner
- [ ] Production logs show override application

### Edge Cases
- [ ] Override file with only comments (no actual overrides)
- [ ] Override for match that doesn't exist in saves/
- [ ] Override player name with typo (doesn't match any player)
- [ ] Multiple overrides for same match (last one wins)
- [ ] Override file with wrong permissions (unreadable)

## Success Criteria

1. **Functionality**:
   - ✅ Overrides loaded from JSON file
   - ✅ Overrides applied during import
   - ✅ Correct winner stored in database
   - ✅ Proper logging of override application

2. **Reliability**:
   - ✅ System works without override file (optional)
   - ✅ Invalid JSON doesn't crash import
   - ✅ Missing player names are handled gracefully
   - ✅ All tests passing

3. **Deployment**:
   - ✅ Override file uploaded to Fly.io
   - ✅ File persists across deployments (/data mount)
   - ✅ Sync script handles missing file
   - ✅ Production shows correct winner

4. **Documentation**:
   - ✅ CLAUDE.md updated with override instructions
   - ✅ Example file provides clear template
   - ✅ Comments explain why each override exists

## Time Estimates

| Task | Estimated Time | Running Total |
|------|---------------|---------------|
| 1. Create override module | 1-2 hours | 2 hours |
| 2. Integrate into ETL | 1 hour | 3 hours |
| 3. Update sync script | 30 minutes | 3.5 hours |
| 4. Create example file | 15 minutes | 3.75 hours |
| 5. Write tests | 2 hours | 5.75 hours |
| 6. Update docs | 30 minutes | 6.25 hours |
| 7. Create prod override | 15 minutes | 6.5 hours |
| 8. Deploy to production | 30 minutes | 7 hours |

**Total estimated time**: 7 hours (approximately 1 day)

## Commit Strategy

Following DRY, YAGNI, and atomic commit principles:

1. `feat: Add match winner override loading system`
   - Task 1: winner_overrides.py module

2. `feat: Integrate winner overrides into ETL pipeline`
   - Task 2: etl.py modifications

3. `feat: Upload match winner overrides in sync script`
   - Task 3: sync_tournament_data.sh modifications

4. `docs: Add match winner override example file`
   - Task 4: Example file + .gitignore

5. `test: Add comprehensive tests for winner override system`
   - Task 5: All tests

6. `docs: Document match winner override system`
   - Task 6: CLAUDE.md updates

7. (No commit for Tasks 7-8: production data)

Each commit is:
- **Atomic**: Single logical change
- **Tested**: All tests pass before commit
- **Documented**: Code comments explain WHY not WHAT
- **Reviewable**: Clear diff, easy to understand

## Risk Mitigation

### Risk: Override file corrupted/deleted
- **Mitigation**: Keep example file in git, system works without it
- **Recovery**: Restore from backup, recreate from documentation

### Risk: Player name typo in override
- **Mitigation**: Validation logs error, falls back to parser winner
- **Detection**: Check logs for "Override winner not found" messages

### Risk: Override file uploaded incorrectly to Fly.io
- **Mitigation**: Sync script validates upload, checks file size
- **Recovery**: Re-run sync script

### Risk: Wrong player marked as winner
- **Mitigation**: Manual testing before production deployment
- **Recovery**: Fix override, re-import data, re-deploy

## Future Enhancements (YAGNI - Not Implementing Now)

- Web UI for managing overrides
- Database table for overrides (instead of JSON)
- Audit log of override changes
- Email notifications when override applied
- Bulk override import from spreadsheet
- Override validation against Challonge API

These can be added later if needed. For now, JSON file + manual editing is sufficient.

## Questions for Developer

Before starting implementation, verify:

1. **Database access**: Can you run DuckDB queries locally?
2. **Test environment**: Do you have `uv` and `pytest` installed?
3. **Fly.io access**: Can you run `fly ssh console`?
4. **Python version**: Confirm Python 3.8+ (required by project)

## References

### Key Files to Understand
- `tournament_visualizer/data/parser.py:1019-1066` - Winner determination logic
- `tournament_visualizer/data/etl.py:106-140` - ETL winner processing
- `tournament_visualizer/data/database.py:241-254` - match_winners table schema
- `scripts/sync_tournament_data.sh:96-119` - Database upload process

### Related Documentation
- `docs/developer-guide.md` - Architecture overview (if exists)
- `docs/deployment-guide.md` - Fly.io deployment guide
- `CLAUDE.md` - Project conventions and practices

### External Resources
- JSON validation: https://jsonlint.com/
- DuckDB SQL reference: https://duckdb.org/docs/
- Fly.io persistent storage: https://fly.io/docs/reference/volumes/

---

**Document version**: 1.0
**Created**: 2025-10-16
**Last updated**: 2025-10-16
**Author**: Implementation plan for match winner override system
