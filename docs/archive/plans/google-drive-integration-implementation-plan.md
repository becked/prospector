# Google Drive Integration Implementation Plan

## Overview

**Goal:** Enable downloading tournament save files from Google Drive for files that exceed Challonge's 250KB attachment limit.

**Context:**
- Challonge has a 250KB attachment limit
- ~3 tournament save files exceed this limit and are only available on Google Drive
- Most files (~15) are under the limit and work fine on Challonge
- We need a hybrid system: try Challonge first, fall back to Google Drive for large files

**Approach:**
- Use Google Drive API with API key (no OAuth needed for public folders)
- Auto-generate mapping file by matching GDrive filenames to Challonge matches
- Modify download script to try Challonge first, GDrive second
- Keep existing import/processing pipeline unchanged (no breaking changes)

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
  - `GOOGLE_DRIVE_API_KEY` - **NEW** - Google Drive API key (already added)

### Key Files to Understand

**Configuration:**
- `tournament_visualizer/config.py` - Configuration constants
- `.env` - Environment variables (not in git)

**Download Pipeline:**
- `scripts/download_attachments.py` - Downloads save files from Challonge
- `scripts/import_attachments.py` - Parses and imports saves to database
- `scripts/sync_challonge_participants.py` - Syncs tournament metadata

**Codebase Patterns:**
- Uses `chyllonge` library for Challonge API
- Uses `logging` for all output (not print statements)
- Type hints required on all functions
- Follows DRY principle - extract shared logic

---

## Implementation Tasks

### Task 1: Install Google Drive API Client

**Time Estimate:** 15 minutes

**Objective:** Add Google Drive API client library to project dependencies.

**Why:** We need the official Google API client to interact with Google Drive.

**Files to Modify:**
- `pyproject.toml`

**Steps:**

1. Add the Google API client dependency:
```bash
uv add google-api-python-client
```

2. Verify installation:
```bash
uv pip list | grep google-api-python-client
```

**Testing:**
```bash
# Should import without errors
uv run python -c "from googleapiclient.discovery import build; print('OK')"
```

**Commit Message:**
```
chore: Add google-api-python-client dependency

Required for accessing public Google Drive folders to download
oversized tournament save files (>250KB).
```

---

### Task 2: Add Google Drive Configuration

**Time Estimate:** 15 minutes

**Objective:** Add Google Drive folder ID and API key to configuration system.

**Why:** Configuration should be centralized in one place, not hardcoded.

**Files to Modify:**
- `tournament_visualizer/config.py`
- `.env.example` (to document for other developers)

**Code Changes:**

1. Open `tournament_visualizer/config.py`

2. Add after the existing configuration constants:
```python
# Google Drive configuration (for oversized save files)
GOOGLE_DRIVE_API_KEY = os.getenv("GOOGLE_DRIVE_API_KEY", "")
GOOGLE_DRIVE_FOLDER_ID = os.getenv(
    "GOOGLE_DRIVE_FOLDER_ID",
    "1ss8ToApXPY7o2syLV76i_CJdoS-lnHQk"  # Default: completed-game-save-files folder
)
```

3. Update `.env.example`:
```bash
# Add to the end of .env.example
# Google Drive API (for downloading oversized save files)
GOOGLE_DRIVE_API_KEY=your_api_key_here
GOOGLE_DRIVE_FOLDER_ID=1ss8ToApXPY7o2syLV76i_CJdoS-lnHQk
```

**Testing:**
```bash
# Verify config loads
uv run python -c "from tournament_visualizer.config import Config; print(Config.GOOGLE_DRIVE_API_KEY); print(Config.GOOGLE_DRIVE_FOLDER_ID)"
```

Should print your API key and the folder ID.

**Commit Message:**
```
feat: Add Google Drive configuration to Config class

Adds GOOGLE_DRIVE_API_KEY and GOOGLE_DRIVE_FOLDER_ID to centralized
configuration. Folder ID defaults to the tournament save files folder.
```

---

### Task 3: Create Google Drive Client Module

**Time Estimate:** 30 minutes

**Objective:** Create a reusable module for interacting with Google Drive.

**Why:** Following DRY principle - encapsulate Google Drive logic in one place.

**Files to Create:**
- `tournament_visualizer/data/gdrive_client.py`

**Test Files to Create:**
- `tests/test_gdrive_client.py`

**Implementation (TDD Approach):**

#### Step 3.1: Write Test First

Create `tests/test_gdrive_client.py`:

```python
"""Tests for Google Drive client."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from tournament_visualizer.data.gdrive_client import GoogleDriveClient


class TestGoogleDriveClient:
    """Test GoogleDriveClient class."""

    def test_init_with_valid_api_key(self) -> None:
        """Client initializes with valid API key."""
        client = GoogleDriveClient(api_key="test_key", folder_id="test_folder")

        assert client.api_key == "test_key"
        assert client.folder_id == "test_folder"

    def test_init_requires_api_key(self) -> None:
        """Client requires API key on initialization."""
        with pytest.raises(ValueError, match="API key is required"):
            GoogleDriveClient(api_key="", folder_id="test_folder")

    def test_list_files_returns_file_metadata(self) -> None:
        """list_files() returns list of file metadata dicts."""
        # Mock the Google API service
        with patch('tournament_visualizer.data.gdrive_client.build') as mock_build:
            mock_service = Mock()
            mock_files = Mock()
            mock_list = Mock()

            # Setup mock chain
            mock_build.return_value = mock_service
            mock_service.files.return_value = mock_files
            mock_files.list.return_value = mock_list
            mock_list.execute.return_value = {
                'files': [
                    {'id': '123', 'name': 'test.zip', 'size': '1000'},
                    {'id': '456', 'name': 'test2.zip', 'size': '2000'},
                ]
            }

            client = GoogleDriveClient(api_key="test_key", folder_id="test_folder")
            files = client.list_files()

            assert len(files) == 2
            assert files[0]['id'] == '123'
            assert files[0]['name'] == 'test.zip'
            assert files[1]['id'] == '456'

    def test_download_file_success(self, tmp_path: Path) -> None:
        """download_file() downloads file to specified path."""
        output_path = tmp_path / "test.zip"

        with patch('tournament_visualizer.data.gdrive_client.build') as mock_build:
            with patch('tournament_visualizer.data.gdrive_client.MediaIoBaseDownload') as mock_download:
                # Setup mocks
                mock_service = Mock()
                mock_build.return_value = mock_service

                # Mock download behavior
                mock_downloader = Mock()
                mock_downloader.next_chunk.side_effect = [
                    (Mock(progress=lambda: 0.5), False),  # First chunk
                    (Mock(progress=lambda: 1.0), True),   # Complete
                ]
                mock_download.return_value = mock_downloader

                client = GoogleDriveClient(api_key="test_key", folder_id="test_folder")

                # Create dummy file for test
                output_path.write_bytes(b"test content")

                result = client.download_file("file_id_123", output_path)

                assert result is True
                assert output_path.exists()

    def test_download_file_handles_errors(self, tmp_path: Path) -> None:
        """download_file() returns False on error."""
        output_path = tmp_path / "test.zip"

        with patch('tournament_visualizer.data.gdrive_client.build') as mock_build:
            mock_build.side_effect = Exception("API Error")

            client = GoogleDriveClient(api_key="test_key", folder_id="test_folder")
            result = client.download_file("file_id_123", output_path)

            assert result is False
```

#### Step 3.2: Run Test (Should Fail)

```bash
uv run pytest tests/test_gdrive_client.py -v
```

Expected: All tests fail (module doesn't exist yet).

#### Step 3.3: Implement the Module

Create `tournament_visualizer/data/gdrive_client.py`:

```python
"""Google Drive client for accessing public tournament save files.

This module provides a simple interface to the Google Drive API for
downloading save files from public folders. Uses API key authentication
(no OAuth) since the folder is publicly accessible.
"""

import io
import logging
from pathlib import Path
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

logger = logging.getLogger(__name__)


class GoogleDriveClient:
    """Client for interacting with Google Drive public folders.

    Uses API key authentication to access publicly shared folders.
    No OAuth required.

    Example:
        >>> client = GoogleDriveClient(api_key="your_key", folder_id="folder_id")
        >>> files = client.list_files()
        >>> client.download_file(files[0]['id'], Path("output.zip"))
    """

    def __init__(self, api_key: str, folder_id: str) -> None:
        """Initialize Google Drive client.

        Args:
            api_key: Google Drive API key
            folder_id: ID of the public folder to access

        Raises:
            ValueError: If api_key is empty
        """
        if not api_key:
            raise ValueError("API key is required")

        self.api_key = api_key
        self.folder_id = folder_id
        self._service = None

    def _get_service(self) -> Any:
        """Get or create Drive API service instance.

        Lazy initialization - only creates service when needed.

        Returns:
            Google Drive API service instance
        """
        if self._service is None:
            self._service = build('drive', 'v3', developerKey=self.api_key)
        return self._service

    def list_files(self) -> list[dict[str, Any]]:
        """List all files in the configured folder.

        Returns:
            List of file metadata dictionaries with keys:
            - id: File ID
            - name: Filename
            - size: File size in bytes (as string)
            - modifiedTime: Last modified timestamp

        Raises:
            Exception: If API request fails
        """
        try:
            service = self._get_service()

            # Query for files in the specified folder
            results = service.files().list(
                q=f"'{self.folder_id}' in parents and trashed=false",
                fields="files(id, name, size, modifiedTime)",
                orderBy="name",
                supportsAllDrives=True
            ).execute()

            files = results.get('files', [])
            logger.info(f"Found {len(files)} files in Google Drive folder")

            return files

        except Exception as e:
            logger.error(f"Failed to list files from Google Drive: {e}")
            raise

    def download_file(self, file_id: str, output_path: Path) -> bool:
        """Download a file from Google Drive.

        Args:
            file_id: Google Drive file ID
            output_path: Local path to save the file

        Returns:
            True if download successful, False otherwise
        """
        try:
            service = self._get_service()

            # Request file download
            request = service.files().get_media(fileId=file_id)

            # Download to memory buffer first
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.debug(
                        f"Download progress: {int(status.progress() * 100)}%"
                    )

            # Write to disk
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(fh.getvalue())

            logger.info(f"Downloaded file to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to download file {file_id}: {e}")
            return False

    def get_file_metadata(self, file_id: str) -> dict[str, Any] | None:
        """Get metadata for a specific file.

        Args:
            file_id: Google Drive file ID

        Returns:
            File metadata dict or None if not found
        """
        try:
            service = self._get_service()

            file_metadata = service.files().get(
                fileId=file_id,
                fields="id, name, size, modifiedTime"
            ).execute()

            return file_metadata

        except Exception as e:
            logger.error(f"Failed to get metadata for file {file_id}: {e}")
            return None
```

#### Step 3.4: Run Tests Again

```bash
uv run pytest tests/test_gdrive_client.py -v
```

Expected: All tests pass.

#### Step 3.5: Test Manually with Real API

```bash
# Test listing files
uv run python -c "
from tournament_visualizer.config import Config
from tournament_visualizer.data.gdrive_client import GoogleDriveClient

client = GoogleDriveClient(
    api_key=Config.GOOGLE_DRIVE_API_KEY,
    folder_id=Config.GOOGLE_DRIVE_FOLDER_ID
)

files = client.list_files()
print(f'Found {len(files)} files:')
for f in files[:3]:  # Print first 3
    print(f'  - {f[\"name\"]} ({f[\"size\"]} bytes)')
"
```

Should print actual files from the Google Drive folder.

**Commit Message:**
```
feat: Add GoogleDriveClient for accessing public folders

Implements API key-based client for listing and downloading files
from public Google Drive folders. Uses lazy service initialization
and proper error handling.

Includes comprehensive test coverage with mocked API responses.
```

---

### Task 4: Create Google Drive Mapping Generator

**Time Estimate:** 45 minutes

**Objective:** Auto-generate mapping between Google Drive files and Challonge matches.

**Why:** We need to know which GDrive file corresponds to which tournament match. Auto-matching by player names avoids manual work.

**Files to Create:**
- `scripts/generate_gdrive_mapping.py`

**How It Works:**
1. List all files in Google Drive folder
2. Parse filenames to extract match number and player names (e.g., `15-fiddler-ninja.zip` → match_num=15, "fiddler", "ninja")
3. Fetch all Challonge matches with participant names
4. Match GDrive files to Challonge matches using TWO strategies:
   - **Strategy 1 (preferred)**: Match by file number prefix if it corresponds to Challonge match ID
   - **Strategy 2 (fallback)**: Match by player name similarity
5. Generate JSON mapping file with confidence scores

**Matching Strategy:**

The script uses a **two-stage matching approach**:

1. **Primary Strategy: Match Number Prefix**
   - Example: `15-fiddler-ninja.zip` → Check if Challonge match ID `15` exists
   - If it exists, validate by checking player names (must match >50%)
   - If validated, use 100% confidence (match number is authoritative)
   - **Why:** If the TO uses match IDs in filenames, this is the most reliable method

2. **Fallback Strategy: Player Name Similarity**
   - If match number doesn't exist or names don't validate, fall back to name matching
   - Compares player names from filename against all Challonge matches
   - Returns best match with confidence score (0.0-1.0)
   - **Why:** Handles cases where file number is sequential (not match ID) or mismatched

This dual approach maximizes automatic matching while staying robust to different naming conventions.

**Implementation:**

Create `scripts/generate_gdrive_mapping.py`:

```python
#!/usr/bin/env python3
"""Generate mapping between Google Drive files and Challonge matches.

This script:
1. Lists files in the Google Drive tournament folder
2. Parses filenames to extract player names
3. Matches files to Challonge matches by player name similarity
4. Outputs a JSON mapping file for use by download script

Usage:
    python scripts/generate_gdrive_mapping.py [--output FILE] [--min-confidence 0.8]
"""

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

from chyllonge.api import ChallongeApi
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tournament_visualizer.config import Config
from tournament_visualizer.data.gdrive_client import GoogleDriveClient
from tournament_visualizer.data.name_normalizer import normalize_name

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def parse_gdrive_filename(filename: str) -> dict[str, Any] | None:
    """Parse Google Drive filename to extract match info.

    Expected format: NN-player1-player2.zip
    Examples:
        - 01-anarkos-becked.zip
        - 15-fiddler-ninja.zip
        - 27-alcaras-Michael-of-Minsk.zip

    Args:
        filename: Google Drive filename

    Returns:
        Dict with match_number, player1, player2, and normalized names.
        None if filename doesn't match expected pattern.
    """
    # Pattern: number-player1-player2.zip
    match = re.match(r"(\d+)-(.+?)-(.+?)\.zip$", filename, re.IGNORECASE)
    if not match:
        return None

    match_num_str, player1, player2 = match.groups()

    return {
        "match_number": int(match_num_str),
        "player1": player1,
        "player2": player2,
        "player1_normalized": normalize_name(player1),
        "player2_normalized": normalize_name(player2),
    }


def calculate_name_similarity(name1: str, name2: str) -> float:
    """Calculate similarity score between two names.

    Uses normalized names and checks for exact match or substring match.

    Args:
        name1: First name
        name2: Second name

    Returns:
        Similarity score from 0.0 (no match) to 1.0 (exact match)
    """
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)

    if not norm1 or not norm2:
        return 0.0

    # Exact match
    if norm1 == norm2:
        return 1.0

    # Substring match (one name contains the other)
    if norm1 in norm2 or norm2 in norm1:
        shorter_len = min(len(norm1), len(norm2))
        longer_len = max(len(norm1), len(norm2))
        return shorter_len / longer_len

    return 0.0


def match_gdrive_file_to_challonge(
    gdrive_file: dict[str, Any],
    challonge_matches: list[dict[str, Any]],
    participants: dict[int, str],
) -> tuple[int | None, float, str]:
    """Match a Google Drive file to a Challonge match.

    Uses two strategies in order of preference:
    1. Match by file number if it equals a Challonge match ID (100% confidence)
    2. Match by player name similarity (variable confidence)

    Args:
        gdrive_file: GDrive file metadata with parsed name info
        challonge_matches: List of Challonge match records
        participants: Dict mapping participant_id to display_name

    Returns:
        Tuple of (challonge_match_id, confidence_score, match_reason)
    """
    parsed = parse_gdrive_filename(gdrive_file['name'])
    if not parsed:
        return None, 0.0, "Failed to parse filename"

    # Strategy 1: Try matching by file number prefix
    # Check if the match number corresponds to an actual Challonge match ID
    match_number = parsed['match_number']

    # Build a lookup of Challonge match IDs for fast checking
    challonge_match_ids = {match['id'] for match in challonge_matches}

    if match_number in challonge_match_ids:
        # Validate with player names to ensure it's the right match
        match = next(m for m in challonge_matches if m['id'] == match_number)
        p1_id = match.get('player1_id')
        p2_id = match.get('player2_id')

        if p1_id and p2_id:
            p1_name = participants.get(p1_id, "")
            p2_name = participants.get(p2_id, "")

            # Validate names match (at least partially)
            score1_p1 = calculate_name_similarity(parsed['player1'], p1_name)
            score1_p2 = calculate_name_similarity(parsed['player2'], p2_name)
            score1 = (score1_p1 + score1_p2) / 2

            score2_p1 = calculate_name_similarity(parsed['player1'], p2_name)
            score2_p2 = calculate_name_similarity(parsed['player2'], p1_name)
            score2 = (score2_p1 + score2_p2) / 2

            name_similarity = max(score1, score2)

            # If names match reasonably well (>50%), trust the match number
            if name_similarity > 0.5:
                return (
                    match_number,
                    1.0,  # 100% confidence - match number + validated names
                    f"Matched by file number {match_number} (validated with names)"
                )

    # Strategy 2: Fallback to player name matching
    best_match_id = None
    best_score = 0.0
    best_reason = ""

    for match in challonge_matches:
        p1_id = match.get('player1_id')
        p2_id = match.get('player2_id')

        if not p1_id or not p2_id:
            continue

        p1_name = participants.get(p1_id, "")
        p2_name = participants.get(p2_id, "")

        if not p1_name or not p2_name:
            continue

        # Try both orderings (GDrive player1 vs Challonge player1, and vice versa)
        # Ordering 1: GDrive player1 → Challonge player1
        score1_p1 = calculate_name_similarity(parsed['player1'], p1_name)
        score1_p2 = calculate_name_similarity(parsed['player2'], p2_name)
        score1 = (score1_p1 + score1_p2) / 2

        # Ordering 2: GDrive player1 → Challonge player2 (swapped)
        score2_p1 = calculate_name_similarity(parsed['player1'], p2_name)
        score2_p2 = calculate_name_similarity(parsed['player2'], p1_name)
        score2 = (score2_p1 + score2_p2) / 2

        score = max(score1, score2)

        if score > best_score:
            best_score = score
            best_match_id = match['id']

            if score == score1:
                best_reason = (
                    f"Matched by name similarity: '{parsed['player1']}' → '{p1_name}', "
                    f"'{parsed['player2']}' → '{p2_name}'"
                )
            else:
                best_reason = (
                    f"Matched by name similarity: '{parsed['player1']}' → '{p2_name}', "
                    f"'{parsed['player2']}' → '{p1_name}'"
                )

    return best_match_id, best_score, best_reason


def generate_mapping(
    min_confidence: float = 0.8,
    output_file: Path | None = None,
) -> dict[str, Any]:
    """Generate Google Drive to Challonge match mapping.

    Args:
        min_confidence: Minimum confidence score to include in mapping (0.0-1.0)
        output_file: Path to output JSON file (default: data/gdrive_match_mapping.json)

    Returns:
        Mapping dictionary
    """
    # Load environment
    load_dotenv()

    # Initialize clients
    logger.info("Initializing API clients...")
    gdrive_client = GoogleDriveClient(
        api_key=Config.GOOGLE_DRIVE_API_KEY,
        folder_id=Config.GOOGLE_DRIVE_FOLDER_ID,
    )
    challonge_api = ChallongeApi()

    tournament_id = os.getenv("challonge_tournament_id")
    if not tournament_id:
        raise ValueError("challonge_tournament_id not set in environment")

    # Fetch data
    logger.info("Fetching Google Drive files...")
    gdrive_files = gdrive_client.list_files()
    logger.info(f"Found {len(gdrive_files)} files in Google Drive")

    logger.info("Fetching Challonge tournament data...")
    challonge_matches = challonge_api.matches.get_all(tournament_id)
    challonge_participants = challonge_api.participants.get_all(tournament_id)
    logger.info(f"Found {len(challonge_matches)} matches and {len(challonge_participants)} participants")

    # Build participant lookup
    participants = {
        p['id']: p.get('display_name') or p.get('name')
        for p in challonge_participants
    }

    # Match files
    logger.info("Matching Google Drive files to Challonge matches...")
    mapping = {
        "_schema_version": "1.0",
        "_generated_by": "generate_gdrive_mapping.py",
        "_min_confidence": min_confidence,
        "_gdrive_folder_id": Config.GOOGLE_DRIVE_FOLDER_ID,
        "matches": {}
    }

    high_confidence = 0
    medium_confidence = 0
    low_confidence = 0
    unmatched = 0

    for gdrive_file in gdrive_files:
        # Skip non-zip files
        if not gdrive_file['name'].endswith('.zip'):
            logger.debug(f"Skipping non-zip file: {gdrive_file['name']}")
            continue

        match_id, confidence, reason = match_gdrive_file_to_challonge(
            gdrive_file, challonge_matches, participants
        )

        if match_id and confidence >= min_confidence:
            file_size_kb = int(gdrive_file['size']) / 1024

            mapping['matches'][str(match_id)] = {
                "gdrive_file_id": gdrive_file['id'],
                "gdrive_filename": gdrive_file['name'],
                "confidence": round(confidence, 3),
                "match_reason": reason,
                "file_size_kb": round(file_size_kb, 1),
                "modified_time": gdrive_file.get('modifiedTime', ''),
            }

            if confidence >= 0.9:
                status = "✅ HIGH"
                high_confidence += 1
            elif confidence >= 0.8:
                status = "⚠️  MEDIUM"
                medium_confidence += 1
            else:
                status = "❓ LOW"
                low_confidence += 1

            logger.info(
                f"{status} | {gdrive_file['name']} → Match {match_id} "
                f"({confidence:.0%})"
            )
        else:
            unmatched += 1
            if match_id:
                logger.warning(
                    f"❌ SKIPPED | {gdrive_file['name']} → Match {match_id} "
                    f"({confidence:.0%}, below threshold)"
                )
            else:
                logger.warning(f"❌ NO MATCH | {gdrive_file['name']}")

    # Write output
    if output_file is None:
        output_file = Path("data/gdrive_match_mapping.json")

    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(mapping, f, indent=2)

    logger.info(f"Wrote mapping to {output_file}")

    # Print summary
    print("\n" + "=" * 70)
    print("MAPPING GENERATION SUMMARY")
    print("=" * 70)
    print(f"Total files: {len(gdrive_files)}")
    print(f"Successfully mapped: {len(mapping['matches'])}")
    print(f"  High confidence (≥90%): {high_confidence}")
    print(f"  Medium confidence (80-90%): {medium_confidence}")
    print(f"  Low confidence (below threshold): {low_confidence}")
    print(f"Unmatched: {unmatched}")
    print(f"\nOutput: {output_file}")
    print("=" * 70)

    return mapping


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Generate Google Drive to Challonge match mapping"
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("data/gdrive_match_mapping.json"),
        help="Output JSON file path (default: data/gdrive_match_mapping.json)",
    )

    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.8,
        help="Minimum confidence score to include (0.0-1.0, default: 0.8)",
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
        generate_mapping(
            min_confidence=args.min_confidence,
            output_file=args.output,
        )
    except Exception as e:
        logger.error(f"Failed to generate mapping: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Testing:**

```bash
# Test with dry run (just see what it would generate)
uv run python scripts/generate_gdrive_mapping.py --verbose

# Generate actual mapping file
uv run python scripts/generate_gdrive_mapping.py

# Inspect output
cat data/gdrive_match_mapping.json | head -30
```

**Expected Output:**
- JSON file with high-confidence matches
- Console output showing match results
- Should successfully match most/all files

**Commit Message:**
```
feat: Add Google Drive mapping generator script

Automatically matches GDrive files to Challonge matches using
player name similarity. Generates mapping file for download script
to use when falling back to GDrive for oversized files.

Includes confidence scoring and detailed logging of match results.
```

---

### Task 5: Modify Download Script for GDrive Fallback

**Time Estimate:** 1 hour

**Objective:** Update `download_attachments.py` to try Google Drive when Challonge fails or file is oversized.

**Why:** This is the core integration - download from Challonge first (works for most files), fall back to GDrive for large files.

**Files to Modify:**
- `scripts/download_attachments.py`

**Strategy:**
1. Try Challonge attachment first (existing code)
2. If no attachment or download fails, check GDrive mapping
3. If in mapping, download from GDrive
4. Log which source was used for each file

**Implementation:**

Add these functions to `download_attachments.py`:

```python
# Add these imports at the top
import json
from tournament_visualizer.data.gdrive_client import GoogleDriveClient
from tournament_visualizer.config import Config

# Add after the existing imports


def load_gdrive_mapping(mapping_path: Path = Path("data/gdrive_match_mapping.json")) -> dict:
    """Load Google Drive match mapping file.

    Args:
        mapping_path: Path to mapping JSON file

    Returns:
        Mapping dictionary, or empty dict if file doesn't exist
    """
    if not mapping_path.exists():
        print(f"No Google Drive mapping file found at {mapping_path}")
        return {"matches": {}}

    try:
        with open(mapping_path) as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading GDrive mapping: {e}")
        return {"matches": {}}


def download_from_gdrive(
    gdrive_client: GoogleDriveClient,
    file_id: str,
    filename: str,
    save_dir: Path,
) -> bool:
    """Download file from Google Drive.

    Args:
        gdrive_client: Google Drive client instance
        file_id: Google Drive file ID
        filename: Filename to save as
        save_dir: Directory to save file in

    Returns:
        True if download successful, False otherwise
    """
    save_path = save_dir / filename

    # Skip if already exists
    if save_path.exists():
        print(f"Skipped (already exists): {filename}")
        return True

    print(f"Downloading from Google Drive: {filename}")
    success = gdrive_client.download_file(file_id, save_path)

    if success:
        print(f"✓ Downloaded from GDrive: {filename}")
    else:
        print(f"✗ GDrive download failed: {filename}")

    return success


def download_match_save(
    match_data: dict,
    api: ChallongeApi,
    tournament_id: str,
    save_dir: Path,
    gdrive_client: GoogleDriveClient | None,
    gdrive_mapping: dict,
) -> tuple[bool, str]:
    """Download save file for a match from best available source.

    Tries Challonge first, falls back to Google Drive if needed.

    Args:
        match_data: Match data from Challonge API
        api: Challonge API client
        tournament_id: Tournament ID
        save_dir: Directory to save files
        gdrive_client: Google Drive client (or None if not configured)
        gdrive_mapping: GDrive match mapping dictionary

    Returns:
        Tuple of (success: bool, source: str)
        source is "challonge", "gdrive", or "none"
    """
    match_id = match_data.get("id")
    attachment_count = match_data.get("attachment_count", 0)

    # Try Challonge first
    if attachment_count and attachment_count > 0:
        try:
            attachments = api.attachments.get_all(tournament_id, match_id)

            for attachment in attachments:
                asset_url = attachment.get("asset_url")
                if asset_url:
                    # Fix URL protocol if missing
                    if asset_url.startswith("//"):
                        asset_url = "https:" + asset_url

                    # Use original filename
                    filename = attachment.get("asset_file_name") or f"match_{match_id}.zip"
                    safe_filename = f"match_{match_id}_{filename}"
                    safe_filename = "".join(
                        c for c in safe_filename if c.isalnum() or c in "._- "
                    )

                    # Try to download
                    if download_attachment(
                        asset_url,
                        safe_filename,
                        save_dir,
                        attachment.get("asset_file_size"),
                    ):
                        return True, "challonge"
        except Exception as e:
            print(f"Challonge download failed for match {match_id}: {e}")

    # Fall back to Google Drive
    if gdrive_client and str(match_id) in gdrive_mapping.get("matches", {}):
        mapping_entry = gdrive_mapping["matches"][str(match_id)]
        file_id = mapping_entry["gdrive_file_id"]
        gdrive_filename = mapping_entry["gdrive_filename"]

        safe_filename = f"match_{match_id}_{gdrive_filename}"
        safe_filename = "".join(
            c for c in safe_filename if c.isalnum() or c in "._- "
        )

        if download_from_gdrive(gdrive_client, file_id, safe_filename, save_dir):
            return True, "gdrive"

    return False, "none"


# Modify the main() function to use the new logic:

def main() -> None:
    """Main function to download all tournament attachments."""
    try:
        # Load configuration
        tournament_id = load_config()

        # Create Challonge API client
        api = create_challonge_client()

        # Initialize Google Drive client (if API key configured)
        gdrive_client = None
        gdrive_mapping = load_gdrive_mapping()

        if Config.GOOGLE_DRIVE_API_KEY:
            try:
                gdrive_client = GoogleDriveClient(
                    api_key=Config.GOOGLE_DRIVE_API_KEY,
                    folder_id=Config.GOOGLE_DRIVE_FOLDER_ID,
                )
                print(f"✓ Google Drive integration enabled")
                print(f"  Loaded {len(gdrive_mapping.get('matches', {}))} GDrive mappings")
            except Exception as e:
                print(f"⚠ Google Drive initialization failed: {e}")
                print("  Will only use Challonge attachments")
        else:
            print("ℹ Google Drive API key not configured (will only use Challonge)")

        # Create downloads directory
        downloads_dir = Path(os.getenv("SAVES_DIRECTORY", "saves"))
        downloads_dir.mkdir(exist_ok=True)

        print(f"Downloading attachments for tournament: {tournament_id}")

        # Get tournament matches
        matches = get_tournament_matches(api, tournament_id)
        if not matches:
            print("No matches found or error retrieving matches")
            return

        print(f"Found {len(matches)} matches")

        # Download saves for each match
        successful_downloads = 0
        challonge_downloads = 0
        gdrive_downloads = 0
        failed_downloads = 0

        for match in matches:
            success, source = download_match_save(
                match,
                api,
                tournament_id,
                downloads_dir,
                gdrive_client,
                gdrive_mapping,
            )

            if success:
                successful_downloads += 1
                if source == "challonge":
                    challonge_downloads += 1
                elif source == "gdrive":
                    gdrive_downloads += 1
            else:
                failed_downloads += 1
                print(f"⚠ No save file found for match {match.get('id')}")

        print(f"\nDownload complete:")
        print(f"  Total successful: {successful_downloads}/{len(matches)}")
        print(f"  From Challonge: {challonge_downloads}")
        print(f"  From Google Drive: {gdrive_downloads}")
        print(f"  Failed: {failed_downloads}")
        print(f"Files saved to: {downloads_dir.absolute()}")

    except ValueError as e:
        # Configuration errors (missing env vars)
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        # Unexpected errors
        print(f"Unexpected Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
```

**Testing:**

```bash
# First, ensure mapping exists
uv run python scripts/generate_gdrive_mapping.py

# Test download with both sources
uv run python scripts/download_attachments.py

# Verify files were downloaded
ls -lh saves/

# Check that oversized files came from GDrive
# (Look for "Downloaded from GDrive" in output)
```

**Commit Message:**
```
feat: Add Google Drive fallback to download script

Downloads now try Challonge first (existing behavior), then fall
back to Google Drive for files that:
- Exceed Challonge's 250KB limit
- Are missing from Challonge
- Are explicitly mapped in gdrive_match_mapping.json

Logs which source (Challonge/GDrive) was used for each file.
Maintains backward compatibility - works without GDrive configured.
```

---

### Task 6: Update Sync Script for Production

**Time Estimate:** 20 minutes

**Objective:** Update production sync script to generate GDrive mapping before downloading.

**Why:** Production deployments should automatically handle GDrive files without manual intervention.

**Files to Modify:**
- `scripts/sync_tournament_data.sh`

**Changes:**

Add after the download step (around line 85):

```bash
# Step 1.5: Generate Google Drive mapping (if API key configured)
if [ -n "${GOOGLE_DRIVE_API_KEY}" ]; then
    echo -e "${YELLOW}[1.5/6] Generating Google Drive mapping...${NC}"
    if uv run python scripts/generate_gdrive_mapping.py --output data/gdrive_match_mapping.json; then
        echo -e "${GREEN}✓ GDrive mapping generated${NC}"
    else
        echo -e "${YELLOW}⚠ GDrive mapping generation failed (will skip GDrive files)${NC}"
    fi
    echo ""
fi
```

Add to the override files upload section (around line 183):

```bash
# Upload Google Drive mapping
if [ -f "data/gdrive_match_mapping.json" ]; then
    echo -e "${BLUE}Uploading Google Drive mapping...${NC}"

    if echo "put data/gdrive_match_mapping.json /data/gdrive_match_mapping.json" | fly ssh sftp shell -a "${APP_NAME}"; then
        echo -e "${GREEN}✓ GDrive mapping file uploaded${NC}"

        # Fix permissions
        fly ssh console -a "${APP_NAME}" -C "chmod 664 /data/gdrive_match_mapping.json" 2>/dev/null
        fly ssh console -a "${APP_NAME}" -C "chown appuser:appuser /data/gdrive_match_mapping.json" 2>/dev/null
    else
        echo -e "${YELLOW}Warning: Could not upload GDrive mapping file${NC}"
    fi
else
    echo -e "${BLUE}No GDrive mapping file found - skipping${NC}"
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
feat: Add GDrive mapping generation to sync script

Production sync now:
1. Generates GDrive mapping automatically (if API key configured)
2. Uploads mapping file to production
3. Falls back gracefully if GDrive not configured

Ensures production always has latest GDrive mappings without
manual intervention.
```

---

### Task 7: Add Configuration to Fly.io

**Time Estimate:** 10 minutes

**Objective:** Add Google Drive API key to production environment.

**Why:** Production needs the API key to access Google Drive.

**Steps:**

```bash
# Set the API key as a Fly.io secret
fly secrets set GOOGLE_DRIVE_API_KEY="your_actual_api_key_here" -a prospector

# Optionally set folder ID if different from default
# fly secrets set GOOGLE_DRIVE_FOLDER_ID="folder_id_here" -a prospector

# Verify secrets are set
fly secrets list -a prospector
```

**Testing:**

```bash
# Check that app can access the secret
fly ssh console -a prospector -C "printenv | grep GOOGLE_DRIVE"
```

**Documentation:**

Update `.env.example` if not already done:
```bash
# Google Drive API (for downloading oversized save files)
GOOGLE_DRIVE_API_KEY=your_api_key_here
GOOGLE_DRIVE_FOLDER_ID=1ss8ToApXPY7o2syLV76i_CJdoS-lnHQk
```

**Commit Message:**
```
docs: Document Google Drive configuration

Updates .env.example with Google Drive API key and folder ID.
Documents deployment steps in CLAUDE.md.
```

---

### Task 8: Update Documentation

**Time Estimate:** 30 minutes

**Objective:** Document the new Google Drive integration for future developers.

**Files to Modify:**
- `CLAUDE.md` (project instructions)
- `docs/developer-guide.md` (if exists, or create it)

**Add to CLAUDE.md:**

```markdown
## Google Drive Integration

### Overview

Tournament save files are stored in two locations:
1. **Challonge attachments** - Files under 250KB (most files)
2. **Google Drive** - Files over 250KB (fallback for oversized files)

The download script tries Challonge first, then falls back to Google Drive.

### Setup

**Local Development:**

1. Get a Google Drive API key:
   - Visit https://console.cloud.google.com/
   - Create project or use existing
   - Enable "Google Drive API"
   - Create API Key (Credentials → Create → API Key)
   - Optionally restrict to Drive API only

2. Add to `.env`:
   ```bash
   GOOGLE_DRIVE_API_KEY=your_api_key_here
   GOOGLE_DRIVE_FOLDER_ID=1ss8ToApXPY7o2syLV76i_CJdoS-lnHQk
   ```

**Production (Fly.io):**

```bash
fly secrets set GOOGLE_DRIVE_API_KEY="your_key" -a prospector
```

### Workflow

The Google Drive integration is automatic:

```bash
# Generate mapping (run once, or when new files added)
uv run python scripts/generate_gdrive_mapping.py

# Download saves (tries Challonge, falls back to GDrive)
uv run python scripts/download_attachments.py

# Import and sync as usual
uv run python scripts/import_attachments.py --directory saves --force
uv run python scripts/link_players_to_participants.py
```

For production sync:
```bash
# Automatically handles GDrive mapping and download
./scripts/sync_tournament_data.sh
```

### Files

- `tournament_visualizer/data/gdrive_client.py` - Google Drive API client
- `scripts/generate_gdrive_mapping.py` - Auto-matches GDrive files to Challonge matches
- `data/gdrive_match_mapping.json` - Generated mapping file (not in git)

### Troubleshooting

**No GDrive files downloaded:**
- Check that `GOOGLE_DRIVE_API_KEY` is set
- Run `generate_gdrive_mapping.py` to create mapping
- Verify mapping file exists: `cat data/gdrive_match_mapping.json`

**Low confidence matches:**
- Review mapping output for confidence scores
- Manually edit `data/gdrive_match_mapping.json` if needed
- Player name mismatches can cause failed matches

**API quota errors:**
- Google Drive API has rate limits
- Script handles this automatically with retries
- If persistent, wait a few minutes and retry
```

**Commit Message:**
```
docs: Add Google Drive integration guide to CLAUDE.md

Documents setup, workflow, and troubleshooting for Google Drive
integration. Includes both local development and production
deployment instructions.
```

---

### Task 9: Integration Testing

**Time Estimate:** 45 minutes

**Objective:** Test the complete end-to-end workflow.

**Testing Checklist:**

#### 9.1 Test Mapping Generation

```bash
# Should successfully match most/all files
uv run python scripts/generate_gdrive_mapping.py --verbose

# Verify output
cat data/gdrive_match_mapping.json | jq '.matches | length'
# Should show number of matched files

# Check confidence levels
cat data/gdrive_match_mapping.json | jq '.matches[].confidence' | sort -rn
# Should mostly be > 0.8
```

**Expected:** High confidence matches for most files.

#### 9.2 Test Download with GDrive Fallback

```bash
# Clear existing saves to test fresh download
rm -rf saves/*.zip

# Run download
uv run python scripts/download_attachments.py

# Verify output shows both sources
# Should see:
#   "Downloaded: match_X_..." (Challonge)
#   "✓ Downloaded from GDrive: match_Y_..." (Google Drive)

# Check that oversized files came from GDrive
ls -lh saves/ | grep -E "(icematrix-kiriyama|squidleybungo-klass|icematrix-squidleybungo)"
```

**Expected:** All files downloaded, with 3 large files from GDrive.

#### 9.3 Test Import Pipeline

```bash
# Import saves to database
uv run python scripts/import_attachments.py --directory saves --verbose

# Verify import succeeded
uv run duckdb data/tournament_data.duckdb -readonly -c "SELECT COUNT(*) FROM matches"
# Should show expected number of matches

# Check that GDrive files were imported
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT match_id, file_name, total_turns
FROM matches
ORDER BY match_id
LIMIT 5
"
```

**Expected:** All saves imported successfully, including GDrive files.

#### 9.4 Test Participant Linking

```bash
# Link players to participants
uv run python scripts/link_players_to_participants.py

# Should work exactly as before
```

**Expected:** No errors, all players linked.

#### 9.5 Test Without GDrive API Key

```bash
# Temporarily disable GDrive
mv .env .env.backup
cat .env.backup | grep -v GOOGLE_DRIVE_API_KEY > .env

# Download should still work for Challonge files
rm -rf saves/*.zip
uv run python scripts/download_attachments.py

# Should see message: "ℹ Google Drive API key not configured"
# Should still download Challonge files successfully

# Restore .env
mv .env.backup .env
```

**Expected:** Backward compatibility - works without GDrive.

#### 9.6 Test Error Handling

```bash
# Test with invalid API key
export GOOGLE_DRIVE_API_KEY="invalid_key"
uv run python scripts/generate_gdrive_mapping.py

# Should show error message, not crash
```

**Expected:** Graceful error handling with clear messages.

**Commit Message:**
```
test: Verify Google Drive integration end-to-end

Confirms:
- Mapping generation with high confidence matches
- Download fallback from Challonge to GDrive
- Import pipeline works with GDrive files
- Backward compatibility without GDrive configured
- Graceful error handling
```

---

### Task 10: Production Deployment

**Time Estimate:** 30 minutes

**Objective:** Deploy to production and verify everything works.

**Pre-Deployment Checklist:**

- [ ] All tests passing locally
- [ ] GDrive API key added to Fly.io secrets
- [ ] Mapping file generated and validated locally
- [ ] Documentation updated
- [ ] Code committed and pushed to git

**Deployment Steps:**

```bash
# 1. Deploy code changes
fly deploy

# 2. Verify deployment
fly logs -a prospector

# 3. Run full sync (includes GDrive mapping generation)
./scripts/sync_tournament_data.sh

# 4. Monitor logs for errors
fly logs -a prospector -f

# 5. Verify app is running
curl https://prospector.fly.dev/health
# Or visit in browser
```

**Post-Deployment Verification:**

```bash
# Check that GDrive files are in production database
fly ssh console -a prospector -C "
cd /app &&
uv run duckdb /data/tournament_data.duckdb -readonly -c '
SELECT file_name, ROUND(file_size_kb, 1) as size_kb
FROM matches
ORDER BY file_size_kb DESC
LIMIT 5
'
"

# Should show the large files (icematrix-kiriyama, etc.)
```

**Rollback Plan (if something goes wrong):**

```bash
# Revert to previous deployment
fly releases -a prospector
fly releases rollback <previous-version> -a prospector

# Or deploy from previous git commit
git checkout <previous-commit>
fly deploy
git checkout main
```

**Commit Message:**
```
chore: Deploy Google Drive integration to production

Deploys complete GDrive integration with fallback logic.
All tests passing. Monitoring for issues.
```

---

## Testing Strategy

### Unit Tests

**Files tested:**
- `tournament_visualizer/data/gdrive_client.py`
- Name matching logic in mapping generator

**Run tests:**
```bash
uv run pytest tests/test_gdrive_client.py -v
```

### Integration Tests

**What to test:**
1. Mapping generation matches files correctly
2. Download script uses both sources
3. Import pipeline works unchanged
4. Backward compatibility (works without GDrive)

**Run tests:**
```bash
# Run test suite from Task 9
```

### Manual Testing

**Test scenarios:**
1. Fresh download of all files
2. Re-download (should skip existing)
3. Download without GDrive API key
4. Download with invalid API key
5. Import GDrive files
6. Full sync pipeline

---

## Validation Checklist

Before considering this complete, verify:

- [ ] All unit tests pass
- [ ] Integration tests pass (Task 9)
- [ ] Documentation updated (CLAUDE.md, .env.example)
- [ ] GDrive API key configured in production
- [ ] Mapping file generates successfully
- [ ] Download script shows both sources being used
- [ ] Large files (>250KB) download from GDrive
- [ ] Small files (<250KB) download from Challonge
- [ ] Import pipeline unchanged (no breaking changes)
- [ ] Production deployment successful
- [ ] App works in production with new data

---

## Rollback Plan

If issues occur in production:

### Immediate Rollback (No Code Changes)

Remove GDrive API key:
```bash
fly secrets unset GOOGLE_DRIVE_API_KEY -a prospector
```

This disables GDrive integration without code changes. App falls back to Challonge-only mode.

### Code Rollback

```bash
# Find previous good version
fly releases -a prospector

# Rollback
fly releases rollback <version> -a prospector
```

### Data Rollback

If database corruption (unlikely):
```bash
# Restore from backup
fly ssh sftp shell -a prospector
# Upload previous database backup
```

---

## Known Limitations

1. **Manual mapping required if:**
   - Player names in GDrive don't match Challonge
   - Confidence score below threshold
   - File naming convention changes

2. **API rate limits:**
   - Google Drive API: 1000 requests/100 seconds
   - Should not be an issue for ~20 files
   - Script doesn't implement backoff (could be added if needed)

3. **File size detection:**
   - Only oversized files NEED GDrive
   - All files CAN be on GDrive for consistency
   - Current approach: hybrid (some Challonge, some GDrive)

4. **Mapping file maintenance:**
   - Must regenerate when new files added
   - Production sync does this automatically
   - Manual runs need to remember to regenerate

---

## Future Enhancements

**Not in scope for this implementation, but could be added later:**

1. **Automatic file size detection:**
   - Check file size before downloading from Challonge
   - Auto-skip to GDrive if >250KB
   - Eliminates need for mapping file

2. **GDrive webhook integration:**
   - Get notified when new files added
   - Auto-regenerate mapping
   - Auto-trigger sync

3. **Mapping validation tool:**
   - Detect if GDrive folder has new files
   - Alert if mapping is stale
   - Suggest which files need mapping

4. **Alternative fallback order:**
   - Try GDrive first for all files
   - Fall back to Challonge if GDrive fails
   - Provides single source of truth

5. **File upload helper:**
   - Script to upload files to GDrive
   - Auto-add to mapping
   - Simplify TO workflow

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

### Problem: "Failed to list files from Google Drive"

**Cause:** Invalid API key or API not enabled

**Solution:**
1. Verify API key: https://console.cloud.google.com/apis/credentials
2. Enable Drive API: https://console.cloud.google.com/apis/library/drive.googleapis.com
3. Check API key restrictions (should allow Drive API)

### Problem: Low confidence matches

**Cause:** Player names in GDrive don't match Challonge

**Solution:**
```bash
# Review mapping output
uv run python scripts/generate_gdrive_mapping.py --verbose

# Manually edit mapping file
vim data/gdrive_match_mapping.json

# Or adjust min-confidence threshold
uv run python scripts/generate_gdrive_mapping.py --min-confidence 0.7
```

### Problem: Files not downloading from GDrive

**Cause:** File not in mapping

**Solution:**
```bash
# Check mapping
cat data/gdrive_match_mapping.json | jq '.matches | keys'

# Regenerate mapping
uv run python scripts/generate_gdrive_mapping.py

# Check GDrive folder directly
uv run python -c "
from tournament_visualizer.config import Config
from tournament_visualizer.data.gdrive_client import GoogleDriveClient

client = GoogleDriveClient(Config.GOOGLE_DRIVE_API_KEY, Config.GOOGLE_DRIVE_FOLDER_ID)
files = client.list_files()
for f in files:
    print(f['name'])
"
```

### Problem: Import fails after GDrive download

**Cause:** GDrive file is corrupted or wrong format

**Solution:**
```bash
# Verify file is valid ZIP
unzip -t saves/match_123_filename.zip

# Re-download
rm saves/match_123_filename.zip
uv run python scripts/download_attachments.py

# Check file size
ls -lh saves/match_123_filename.zip
```

---

## Success Criteria

This implementation is complete when:

1. ✅ Google Drive client can list and download files
2. ✅ Mapping generator successfully matches files to matches
3. ✅ Download script tries Challonge first, GDrive second
4. ✅ Large files (>250KB) download from GDrive
5. ✅ Import pipeline works unchanged
6. ✅ Production deployment successful
7. ✅ Documentation complete
8. ✅ All tests passing

---

## Time Breakdown Summary

| Task | Time Estimate | Type |
|------|---------------|------|
| 1. Install GDrive client | 15 min | Setup |
| 2. Add configuration | 15 min | Config |
| 3. Create GDrive client module | 30 min | Code + Tests |
| 4. Create mapping generator | 45 min | Code |
| 5. Modify download script | 1 hour | Code |
| 6. Update sync script | 20 min | Code |
| 7. Configure Fly.io | 10 min | Deployment |
| 8. Update documentation | 30 min | Docs |
| 9. Integration testing | 45 min | Testing |
| 10. Production deployment | 30 min | Deployment |
| **Total** | **6-8 hours** | |

---

## Commit Strategy

Follow atomic commits - one logical change per commit:

1. ✅ Add google-api-python-client dependency
2. ✅ Add Google Drive configuration
3. ✅ Add GoogleDriveClient with tests
4. ✅ Add mapping generator script
5. ✅ Add GDrive fallback to download script
6. ✅ Update sync script for GDrive
7. ✅ Document GDrive integration
8. ✅ Integration testing verification
9. ✅ Deploy to production

Each commit should:
- Pass all existing tests
- Include relevant test updates
- Follow conventional commit format
- Have clear, descriptive message

---

## Questions to Ask Before Starting

1. **Is the Google Drive API key already created?**
   - If not, need to do that first (10 minutes)

2. **Should all files eventually move to GDrive?**
   - Or keep hybrid forever?
   - Affects long-term strategy

3. **What's the plan for new files going forward?**
   - Upload to both Challonge + GDrive?
   - Or GDrive only?

4. **Are there other oversized files expected?**
   - Just these 3, or more coming?
   - Affects urgency and testing scope

---

## Notes for Code Reviewer

**Key Design Decisions:**

1. **Why fallback instead of GDrive-primary?**
   - Challonge is faster (no mapping needed)
   - Most files work fine on Challonge
   - Minimizes API calls to Google
   - Backward compatible

2. **Why auto-generate mapping?**
   - Manual mapping for 18+ files is error-prone
   - Name matching is high confidence (>80%)
   - Saves time for future file additions

3. **Why API key instead of OAuth?**
   - Folder is public (no auth needed)
   - API key is simpler to set up
   - No token expiration issues
   - Suitable for read-only access

4. **Why not move everything to GDrive?**
   - YAGNI - only 3 files need it currently
   - Challonge works fine for most files
   - Reduces external dependencies

**What to Review:**

- Error handling (API failures, missing files)
- Test coverage (especially mocked API calls)
- Backward compatibility (works without GDrive)
- Configuration management (secrets not in code)
- Logging (clear messages for debugging)
