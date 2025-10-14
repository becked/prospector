# YouTube Playtime Tracking Implementation Plan

## Overview

### Problem
Tournament matches are played over multiple sessions spanning multiple days. The save files only contain the final game state with no timing information. We need to track the actual playtime for each match to provide insights into match duration.

### Solution
Each match has accompanying YouTube video(s) documenting the gameplay sessions. By fetching video metadata from the YouTube Data API, we can calculate total playtime by summing the duration of all videos associated with each match.

### Success Criteria
- Extract video durations from YouTube playlist
- Match videos to tournament matches by player names
- Store total playtime and session count in database
- Display playtime on match detail pages
- Handle edge cases (missing videos, multiple sessions, naming variations)

---

## Prerequisites

### Required Knowledge
- **Python 3.11+**: Our project uses modern Python with type hints
- **DuckDB**: Analytics database (like SQLite but optimized for analytics)
- **uv**: Python package manager (replaces pip/poetry)
- **Dash/Plotly**: Web framework for the visualization dashboard
- **pytest**: Testing framework

### Required Setup
1. **YouTube API Key**
   - Visit: https://console.cloud.google.com/apis/credentials
   - Create project → Enable "YouTube Data API v3" → Create credentials (API key)
   - Set environment variable: `export YOUTUBE_API_KEY="your_key_here"`
   - Add to `.env` file (create if doesn't exist):
     ```
     YOUTUBE_API_KEY=your_key_here
     ```

2. **Install Dependencies**
   ```bash
   # Already in pyproject.toml, just need to add google-api-python-client
   uv pip install google-api-python-client
   ```

---

## Architecture Overview

### Current System
```
Challonge API
    ↓ (downloads attachments)
saves/*.zip (Old World save files)
    ↓ (parsed by tournament_visualizer/data/parser.py)
DuckDB (data/tournament_data.duckdb)
    ↓ (queried by tournament_visualizer/data/queries.py)
Dash App (tournament_visualizer/app.py)
```

### After This Change
```
Challonge API → saves/*.zip → DuckDB ← YouTube API
                                ↓
                            Dash App
```

### New Components
1. **YouTube API Client** (`tournament_visualizer/integrations/youtube.py`)
   - Fetches playlist videos
   - Parses durations from ISO 8601 format
   - Returns structured data

2. **Video Matcher** (`tournament_visualizer/data/video_matcher.py`)
   - Matches video titles to match players
   - Handles name variations and fuzzy matching
   - Groups sessions by match

3. **Database Migration** (schema changes)
   - Add columns to `matches` table
   - Create `match_videos` table for many-to-many relationship

4. **Import Script** (`scripts/import_youtube_data.py`)
   - Orchestrates the end-to-end process
   - Callable from command line

---

## Database Schema Changes

### Current `matches` Table (Relevant Columns)
```sql
CREATE TABLE matches (
    match_id INTEGER PRIMARY KEY,
    challonge_match_id INTEGER,
    file_name VARCHAR,
    player1_name VARCHAR,
    player2_name VARCHAR,
    winner_player_id INTEGER,
    total_turns INTEGER,
    save_date TIMESTAMP,
    ...
);
```

### New Schema

#### Option A: Simple (Add Columns to `matches`)
**Pros**: Easy to query, simple implementation
**Cons**: Harder to track individual videos, can't handle multiple playlists

```sql
ALTER TABLE matches ADD COLUMN youtube_video_ids JSON;
ALTER TABLE matches ADD COLUMN total_playtime_seconds INTEGER;
ALTER TABLE matches ADD COLUMN session_count INTEGER;
```

#### Option B: Normalized (Separate `match_videos` Table)
**Pros**: Proper relational design, flexible, can track video metadata
**Cons**: Requires JOINs for queries

```sql
CREATE TABLE match_videos (
    id INTEGER PRIMARY KEY,
    match_id INTEGER REFERENCES matches(match_id),
    youtube_video_id VARCHAR(11) NOT NULL,
    video_title VARCHAR,
    duration_seconds INTEGER,
    upload_date TIMESTAMP,
    session_number INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_match_videos_match_id ON match_videos(match_id);
```

**Recommendation**: Use Option B (normalized). It's more maintainable and follows database best practices.

---

## Task Breakdown

### Task 0: Project Setup & Discovery
**Goal**: Understand the codebase and verify prerequisites

#### Subtask 0.1: Explore Existing Code (15 min)
**What to do**:
1. Read `CLAUDE.md` to understand project conventions
2. Examine database schema:
   ```bash
   uv run duckdb data/tournament_data.duckdb -readonly -c "DESCRIBE matches"
   ```
3. Look at existing integrations:
   - `scripts/download_attachments.py` (Challonge API usage)
   - `scripts/import_attachments.py` (Database import pattern)
4. Check how player names are stored:
   ```bash
   uv run duckdb data/tournament_data.duckdb -readonly -c "SELECT player1_name, player2_name FROM matches LIMIT 5"
   ```

**Expected Output**:
- Understanding of player name format (e.g., "anarkos", "becked")
- Knowledge of how imports work
- Familiarity with project structure

#### Subtask 0.2: Get YouTube API Key (10 min)
**What to do**:
1. Go to https://console.cloud.google.com/apis/credentials
2. Create new project or select existing
3. Enable "YouTube Data API v3"
4. Create API Key (API key, not OAuth)
5. Add to `.env`:
   ```bash
   echo "YOUTUBE_API_KEY=your_actual_key_here" >> .env
   ```
6. Test it works:
   ```bash
   curl "https://www.googleapis.com/youtube/v3/playlists?part=snippet&id=PLsRPrwJXwEjaUyfAN956kM8WBGWPsHBEp&key=YOUR_KEY"
   ```

**Expected Output**: JSON response with playlist details

#### Subtask 0.3: Install Dependencies (5 min)
**What to do**:
```bash
uv pip install google-api-python-client python-dotenv
```

**Files to modify**: None yet, dependencies are installed system-wide by uv

**Test it works**:
```bash
uv run python -c "from googleapiclient.discovery import build; print('OK')"
```

**Commit Point**: ✓ "chore: Install YouTube API dependencies"

---

### Task 1: Create YouTube API Client (TDD)
**Estimated Time**: 1 hour
**Files to Create**:
- `tournament_visualizer/integrations/__init__.py`
- `tournament_visualizer/integrations/youtube.py`
- `tests/test_youtube_client.py`

#### Subtask 1.1: Write Test First (TDD)
**File**: `tests/test_youtube_client.py`

```python
"""Tests for YouTube API client.

Test Strategy:
- Use pytest fixtures to mock YouTube API responses
- Test happy path and error cases separately
- Use real example data from the playlist
- Don't call real API in tests (use mocks)
"""

import pytest
from unittest.mock import MagicMock, patch
from tournament_visualizer.integrations.youtube import YouTubeClient, Video


class TestYouTubeClient:
    """Test YouTube API client functionality."""

    @pytest.fixture
    def mock_youtube_service(self):
        """Create a mock YouTube API service.

        This replaces the real API with a fake one for testing.
        Returns a MagicMock that pretends to be the YouTube API.
        """
        mock = MagicMock()
        return mock

    @pytest.fixture
    def youtube_client(self, mock_youtube_service):
        """Create a YouTube client with mocked service.

        This ensures tests don't call the real YouTube API.
        """
        with patch('tournament_visualizer.integrations.youtube.build') as mock_build:
            mock_build.return_value = mock_youtube_service
            client = YouTubeClient(api_key="fake_key_for_testing")
            return client

    def test_parse_duration_full(self):
        """Test parsing ISO 8601 duration with hours, minutes, seconds.

        YouTube returns durations like 'PT1H23M45S' (1 hour, 23 min, 45 sec).
        We need to convert this to total seconds: 1*3600 + 23*60 + 45 = 5025
        """
        client = YouTubeClient(api_key="fake_key")

        # Test case: 1 hour, 23 minutes, 45 seconds
        duration = "PT1H23M45S"
        expected_seconds = 1*3600 + 23*60 + 45  # 5025 seconds

        result = client._parse_duration(duration)
        assert result == expected_seconds

    def test_parse_duration_minutes_only(self):
        """Test parsing duration with only minutes and seconds.

        Example: PT15M30S = 15 minutes, 30 seconds = 930 seconds
        """
        client = YouTubeClient(api_key="fake_key")

        duration = "PT15M30S"
        expected_seconds = 15*60 + 30  # 930 seconds

        result = client._parse_duration(duration)
        assert result == expected_seconds

    def test_parse_duration_seconds_only(self):
        """Test parsing duration with only seconds.

        Example: PT45S = 45 seconds
        """
        client = YouTubeClient(api_key="fake_key")

        duration = "PT45S"
        expected_seconds = 45

        result = client._parse_duration(duration)
        assert result == expected_seconds

    def test_get_playlist_videos_success(self, youtube_client, mock_youtube_service):
        """Test fetching videos from a playlist (happy path).

        Mocks the YouTube API to return fake video data.
        Verifies that our client correctly processes the response.
        """
        # Setup: Mock the API response
        # This is what the real YouTube API would return
        mock_youtube_service.playlistItems().list().execute.return_value = {
            'items': [
                {'snippet': {'resourceId': {'videoId': 'abc123'}}},
                {'snippet': {'resourceId': {'videoId': 'def456'}}},
            ]
        }

        mock_youtube_service.videos().list().execute.return_value = {
            'items': [
                {
                    'id': 'abc123',
                    'snippet': {
                        'title': 'anarkos vs becked - Session 1',
                        'publishedAt': '2025-09-20T10:00:00Z'
                    },
                    'contentDetails': {'duration': 'PT1H30M0S'}
                },
                {
                    'id': 'def456',
                    'snippet': {
                        'title': 'anarkos vs becked - Session 2',
                        'publishedAt': '2025-09-21T10:00:00Z'
                    },
                    'contentDetails': {'duration': 'PT2H15M30S'}
                },
            ]
        }

        # Execute: Call our client
        playlist_id = "PLsRPrwJXwEjaUyfAN956kM8WBGWPsHBEp"
        videos = youtube_client.get_playlist_videos(playlist_id)

        # Verify: Check the results
        assert len(videos) == 2

        # Check first video
        assert videos[0].video_id == 'abc123'
        assert videos[0].title == 'anarkos vs becked - Session 1'
        assert videos[0].duration_seconds == 1*3600 + 30*60  # 5400 seconds
        assert 'anarkos' in videos[0].title.lower()
        assert 'becked' in videos[0].title.lower()

        # Check second video
        assert videos[1].video_id == 'def456'
        assert videos[1].duration_seconds == 2*3600 + 15*60 + 30  # 8130 seconds

    def test_get_playlist_videos_empty_playlist(self, youtube_client, mock_youtube_service):
        """Test handling of empty playlist.

        Edge case: What if the playlist has no videos?
        Should return empty list, not crash.
        """
        mock_youtube_service.playlistItems().list().execute.return_value = {
            'items': []
        }

        videos = youtube_client.get_playlist_videos("empty_playlist")
        assert videos == []

    def test_get_playlist_videos_api_error(self, youtube_client, mock_youtube_service):
        """Test handling of API errors.

        Edge case: What if YouTube API returns an error?
        Should raise a helpful exception, not crash silently.
        """
        from googleapiclient.errors import HttpError

        # Mock an API error (e.g., invalid API key, rate limit)
        mock_response = MagicMock()
        mock_response.status = 403
        mock_youtube_service.playlistItems().list().execute.side_effect = HttpError(
            resp=mock_response,
            content=b'Invalid API key'
        )

        with pytest.raises(Exception) as exc_info:
            youtube_client.get_playlist_videos("some_playlist")

        # Verify error message is helpful
        assert "YouTube API error" in str(exc_info.value) or "Invalid API key" in str(exc_info.value)
```

**Why This Test Design?**
1. **Fixtures**: Reusable setup code (`mock_youtube_service`, `youtube_client`)
2. **Mocking**: Never calls real API (fast, reliable, no quota usage)
3. **Happy Path First**: Test normal usage before edge cases
4. **Edge Cases**: Empty playlist, API errors
5. **Clear Names**: Test names explain what they test
6. **Comments**: Explain WHY, not just WHAT

**Run the test (it will fail)**:
```bash
uv run pytest tests/test_youtube_client.py -v
```

**Expected**: All tests fail because `youtube.py` doesn't exist yet. This is correct for TDD!

**Commit Point**: ✓ "test: Add YouTube client tests (TDD, failing)"

#### Subtask 1.2: Implement YouTube Client (Make Tests Pass)
**File**: `tournament_visualizer/integrations/__init__.py`

```python
"""External integrations (YouTube, etc.)."""
```

**File**: `tournament_visualizer/integrations/youtube.py`

```python
"""YouTube Data API v3 client for fetching video metadata.

This module handles all interactions with the YouTube API:
- Fetching playlist videos
- Parsing video durations
- Extracting metadata

Usage:
    client = YouTubeClient(api_key="your_key")
    videos = client.get_playlist_videos("PLsRPrwJXwEjaUyfAN956kM8WBGWPsHBEp")

    for video in videos:
        print(f"{video.title}: {video.duration_seconds} seconds")
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


@dataclass
class Video:
    """Represents a YouTube video with its metadata.

    Attributes:
        video_id: YouTube video ID (11 characters)
        title: Video title
        duration_seconds: Total duration in seconds
        upload_date: When video was uploaded
    """
    video_id: str
    title: str
    duration_seconds: int
    upload_date: datetime


class YouTubeClient:
    """Client for YouTube Data API v3.

    Handles fetching video metadata from playlists.
    Uses API quota efficiently by batching requests.
    """

    def __init__(self, api_key: str) -> None:
        """Initialize YouTube client.

        Args:
            api_key: YouTube Data API v3 key

        Raises:
            ValueError: If api_key is empty
        """
        if not api_key:
            raise ValueError("YouTube API key is required")

        self.api_key = api_key
        self._service = build('youtube', 'v3', developerKey=api_key)
        logger.info("Initialized YouTube API client")

    def get_playlist_videos(self, playlist_id: str) -> List[Video]:
        """Fetch all videos from a YouTube playlist.

        Makes two API calls:
        1. playlistItems.list - Get video IDs from playlist
        2. videos.list - Get metadata for each video

        Args:
            playlist_id: YouTube playlist ID

        Returns:
            List of Video objects with metadata

        Raises:
            Exception: If API call fails
        """
        logger.info(f"Fetching videos from playlist: {playlist_id}")

        try:
            # Step 1: Get video IDs from playlist
            video_ids = self._get_video_ids_from_playlist(playlist_id)

            if not video_ids:
                logger.warning(f"No videos found in playlist {playlist_id}")
                return []

            # Step 2: Get metadata for each video
            videos = self._get_video_metadata(video_ids)

            logger.info(f"Successfully fetched {len(videos)} videos")
            return videos

        except HttpError as e:
            logger.error(f"YouTube API error: {e}")
            raise Exception(f"YouTube API error: {e.resp.status} - {e.content}")

    def _get_video_ids_from_playlist(self, playlist_id: str) -> List[str]:
        """Fetch video IDs from playlist.

        Handles pagination if playlist has >50 videos.

        Args:
            playlist_id: YouTube playlist ID

        Returns:
            List of video IDs
        """
        video_ids = []
        next_page_token = None

        while True:
            # API call: Get playlist items
            request = self._service.playlistItems().list(
                part="snippet",
                playlistId=playlist_id,
                maxResults=50,  # Max allowed by API
                pageToken=next_page_token
            )
            response = request.execute()

            # Extract video IDs
            for item in response.get('items', []):
                video_id = item['snippet']['resourceId']['videoId']
                video_ids.append(video_id)

            # Check for more pages
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break

        return video_ids

    def _get_video_metadata(self, video_ids: List[str]) -> List[Video]:
        """Fetch metadata for multiple videos.

        Batches requests (50 videos per call) to minimize API quota usage.

        Args:
            video_ids: List of YouTube video IDs

        Returns:
            List of Video objects
        """
        videos = []

        # Process in batches of 50 (API limit)
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i+50]

            # API call: Get video details
            request = self._service.videos().list(
                part="snippet,contentDetails",
                id=",".join(batch)
            )
            response = request.execute()

            # Parse each video
            for item in response.get('items', []):
                video = self._parse_video(item)
                if video:
                    videos.append(video)

        return videos

    def _parse_video(self, item: dict) -> Optional[Video]:
        """Parse YouTube API response into Video object.

        Args:
            item: Video item from API response

        Returns:
            Video object or None if parsing fails
        """
        try:
            video_id = item['id']
            title = item['snippet']['title']
            duration_iso = item['contentDetails']['duration']
            upload_date_str = item['snippet']['publishedAt']

            # Parse duration from ISO 8601 format
            duration_seconds = self._parse_duration(duration_iso)

            # Parse upload date
            upload_date = datetime.fromisoformat(upload_date_str.replace('Z', '+00:00'))

            return Video(
                video_id=video_id,
                title=title,
                duration_seconds=duration_seconds,
                upload_date=upload_date
            )
        except (KeyError, ValueError) as e:
            logger.warning(f"Failed to parse video: {e}")
            return None

    def _parse_duration(self, duration: str) -> int:
        """Parse ISO 8601 duration to seconds.

        YouTube returns durations like:
        - PT1H23M45S (1 hour, 23 minutes, 45 seconds)
        - PT15M30S (15 minutes, 30 seconds)
        - PT45S (45 seconds)

        Args:
            duration: ISO 8601 duration string

        Returns:
            Total seconds

        Examples:
            >>> client._parse_duration("PT1H23M45S")
            5025
            >>> client._parse_duration("PT15M30S")
            930
            >>> client._parse_duration("PT45S")
            45
        """
        # Pattern: PT(\d+H)?(\d+M)?(\d+S)?
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
        match = re.match(pattern, duration)

        if not match:
            logger.warning(f"Invalid duration format: {duration}")
            return 0

        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)

        total_seconds = hours * 3600 + minutes * 60 + seconds
        return total_seconds
```

**Run tests again**:
```bash
uv run pytest tests/test_youtube_client.py -v
```

**Expected**: All tests pass ✓

**Commit Point**: ✓ "feat: Add YouTube API client with duration parsing"

---

### Task 2: Create Video Matcher (Match Videos to Players)
**Estimated Time**: 1.5 hours
**Files to Create**:
- `tournament_visualizer/data/video_matcher.py`
- `tests/test_video_matcher.py`

#### Subtask 2.1: Write Tests (TDD)
**File**: `tests/test_video_matcher.py`

```python
"""Tests for video-to-match matcher.

Test Strategy:
- Test exact name matches first (simplest case)
- Test case-insensitive matching
- Test name variations (nicknames, different order)
- Test ambiguous cases (how to handle?)
- Use real player names from database
"""

import pytest
from tournament_visualizer.data.video_matcher import VideoMatcher, MatchedVideo
from tournament_visualizer.integrations.youtube import Video
from datetime import datetime


class TestVideoMatcher:
    """Test video matching to tournament matches."""

    @pytest.fixture
    def sample_matches(self):
        """Sample match data from database.

        This mimics what we'd get from querying the matches table.
        Use real player names from your tournament.
        """
        return [
            {
                'match_id': 1,
                'player1_name': 'anarkos',
                'player2_name': 'becked',
            },
            {
                'match_id': 2,
                'player1_name': 'Fluffbunny',
                'player2_name': 'moose',
            },
            {
                'match_id': 3,
                'player1_name': 'yagman',
                'player2_name': 'Marauder',
            },
        ]

    @pytest.fixture
    def sample_videos(self):
        """Sample YouTube videos from the playlist."""
        return [
            Video(
                video_id='abc123',
                title='anarkos vs becked - Session 1',
                duration_seconds=5400,  # 1.5 hours
                upload_date=datetime(2025, 9, 20)
            ),
            Video(
                video_id='def456',
                title='anarkos vs becked - Session 2',
                duration_seconds=7200,  # 2 hours
                upload_date=datetime(2025, 9, 21)
            ),
            Video(
                video_id='ghi789',
                title='Fluffbunny v Moose (Game 1)',
                duration_seconds=3600,  # 1 hour
                upload_date=datetime(2025, 9, 22)
            ),
        ]

    def test_exact_match_case_insensitive(self, sample_matches, sample_videos):
        """Test matching with exact names (case-insensitive).

        Most videos should have player names in the title.
        Should match regardless of case: 'anarkos' == 'Anarkos' == 'ANARKOS'
        """
        matcher = VideoMatcher()

        # Match videos to matches
        results = matcher.match_videos_to_matches(sample_videos, sample_matches)

        # Should find matches for first 3 videos
        assert len(results) == 3

        # Check anarkos vs becked matches (2 sessions)
        anarkos_videos = [r for r in results if r.match_id == 1]
        assert len(anarkos_videos) == 2
        assert anarkos_videos[0].video_id == 'abc123'
        assert anarkos_videos[1].video_id == 'def456'

        # Check Fluffbunny vs moose match
        fluff_videos = [r for r in results if r.match_id == 2]
        assert len(fluff_videos) == 1
        assert fluff_videos[0].video_id == 'ghi789'

    def test_no_match_returns_empty(self, sample_matches):
        """Test video that doesn't match any player names.

        Edge case: Video title doesn't contain player names.
        Example: "Old World Tournament - Highlights"
        Should not crash, just skip it.
        """
        matcher = VideoMatcher()

        unmatched_video = Video(
            video_id='xyz999',
            title='Tournament Highlights Compilation',
            duration_seconds=600,
            upload_date=datetime(2025, 9, 25)
        )

        results = matcher.match_videos_to_matches([unmatched_video], sample_matches)

        # Should return empty list (no match found)
        assert len(results) == 0

    def test_normalize_name_variations(self):
        """Test name normalization handles variations.

        Players might be called different things:
        - 'Marauder' vs 'The Marauder'
        - 'moose' vs 'moose1234'
        - Spaces, special characters
        """
        matcher = VideoMatcher()

        # Test various normalizations
        assert matcher._normalize_name('anarkos') == 'anarkos'
        assert matcher._normalize_name('Anarkos') == 'anarkos'
        assert matcher._normalize_name(' anarkos ') == 'anarkos'
        assert matcher._normalize_name('The Marauder') == 'marauder'  # Remove "the"

    def test_calculate_match_duration(self, sample_matches, sample_videos):
        """Test calculating total duration for a match with multiple sessions.

        Example: anarkos vs becked has 2 sessions
        Session 1: 5400 seconds (1.5h)
        Session 2: 7200 seconds (2h)
        Total: 12600 seconds (3.5h)
        """
        matcher = VideoMatcher()

        matched_videos = matcher.match_videos_to_matches(sample_videos, sample_matches)

        # Calculate duration for match_id=1 (anarkos vs becked)
        match_1_videos = [v for v in matched_videos if v.match_id == 1]
        total_duration = matcher.calculate_total_duration(match_1_videos)

        expected = 5400 + 7200  # 12600 seconds
        assert total_duration == expected

    def test_multiple_matches_same_video_impossible(self, sample_matches):
        """Test that a video can only match ONE match.

        Edge case: What if video title is ambiguous?
        Example: 'anarkos game' could match multiple matches with anarkos.

        Strategy: Match to the most recent match (by upload date).
        Or: Require both player names in title.

        Let's require BOTH names for safety.
        """
        matcher = VideoMatcher()

        # Video with only one player name (ambiguous)
        ambiguous_video = Video(
            video_id='amb123',
            title='anarkos plays Old World',  # Only one player name
            duration_seconds=3600,
            upload_date=datetime(2025, 9, 23)
        )

        results = matcher.match_videos_to_matches([ambiguous_video], sample_matches)

        # Should NOT match (requires both player names)
        assert len(results) == 0
```

**Run tests (should fail)**:
```bash
uv run pytest tests/test_video_matcher.py -v
```

**Commit Point**: ✓ "test: Add video matcher tests (TDD, failing)"

#### Subtask 2.2: Implement Video Matcher
**File**: `tournament_visualizer/data/video_matcher.py`

```python
"""Match YouTube videos to tournament matches based on player names.

This module implements fuzzy matching between video titles and match player names.
It handles name variations, case differences, and multiple sessions per match.

Matching Strategy:
1. Normalize all names (lowercase, remove special chars)
2. Require BOTH player names in video title (avoid ambiguity)
3. Match case-insensitively
4. Handle name variations ('The Marauder' -> 'marauder')
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Dict, Any

from tournament_visualizer.integrations.youtube import Video

logger = logging.getLogger(__name__)


@dataclass
class MatchedVideo:
    """Represents a video matched to a tournament match.

    Attributes:
        match_id: Tournament match ID
        video_id: YouTube video ID
        video_title: Video title
        duration_seconds: Video duration
        session_number: Which session (1, 2, 3...) based on upload order
    """
    match_id: int
    video_id: str
    video_title: str
    duration_seconds: int
    session_number: int


class VideoMatcher:
    """Matches YouTube videos to tournament matches."""

    def match_videos_to_matches(
        self,
        videos: List[Video],
        matches: List[Dict[str, Any]]
    ) -> List[MatchedVideo]:
        """Match videos to tournament matches based on player names.

        Args:
            videos: List of YouTube videos
            matches: List of match dictionaries with player names

        Returns:
            List of matched videos with match_id assigned
        """
        matched_videos = []

        for video in videos:
            match_id = self._find_match_for_video(video, matches)

            if match_id:
                matched_videos.append(MatchedVideo(
                    match_id=match_id,
                    video_id=video.video_id,
                    video_title=video.title,
                    duration_seconds=video.duration_seconds,
                    session_number=0  # Will assign later
                ))
                logger.info(f"Matched video '{video.title}' to match {match_id}")
            else:
                logger.warning(f"No match found for video: {video.title}")

        # Assign session numbers based on video order
        matched_videos = self._assign_session_numbers(matched_videos)

        return matched_videos

    def _find_match_for_video(
        self,
        video: Video,
        matches: List[Dict[str, Any]]
    ) -> int | None:
        """Find which match this video belongs to.

        Requires BOTH player names to be in the video title for safety.

        Args:
            video: YouTube video
            matches: List of tournament matches

        Returns:
            match_id if found, None otherwise
        """
        video_title_normalized = video.title.lower()

        for match in matches:
            player1 = self._normalize_name(match['player1_name'])
            player2 = self._normalize_name(match['player2_name'])

            # Check if BOTH player names appear in title
            if player1 in video_title_normalized and player2 in video_title_normalized:
                return match['match_id']

        return None

    def _normalize_name(self, name: str) -> str:
        """Normalize player name for matching.

        Handles:
        - Case differences: 'Anarkos' -> 'anarkos'
        - Leading/trailing spaces: ' moose ' -> 'moose'
        - Common prefixes: 'The Marauder' -> 'marauder'

        Args:
            name: Player name

        Returns:
            Normalized name
        """
        if not name:
            return ""

        # Lowercase and strip
        normalized = name.lower().strip()

        # Remove "the " prefix
        if normalized.startswith('the '):
            normalized = normalized[4:]

        return normalized

    def _assign_session_numbers(
        self,
        matched_videos: List[MatchedVideo]
    ) -> List[MatchedVideo]:
        """Assign session numbers to videos for the same match.

        Groups videos by match_id, then assigns session numbers
        based on video order (assuming videos are chronological).

        Args:
            matched_videos: List of matched videos

        Returns:
            Same list with session_number assigned
        """
        # Group by match_id
        by_match: Dict[int, List[MatchedVideo]] = {}
        for video in matched_videos:
            if video.match_id not in by_match:
                by_match[video.match_id] = []
            by_match[video.match_id].append(video)

        # Assign session numbers
        result = []
        for match_id, videos in by_match.items():
            for session_num, video in enumerate(videos, start=1):
                # Create new instance with session number
                result.append(MatchedVideo(
                    match_id=video.match_id,
                    video_id=video.video_id,
                    video_title=video.video_title,
                    duration_seconds=video.duration_seconds,
                    session_number=session_num
                ))

        return result

    def calculate_total_duration(self, matched_videos: List[MatchedVideo]) -> int:
        """Calculate total duration for a set of videos.

        Args:
            matched_videos: Videos for a single match

        Returns:
            Total duration in seconds
        """
        return sum(v.duration_seconds for v in matched_videos)
```

**Run tests**:
```bash
uv run pytest tests/test_video_matcher.py -v
```

**Expected**: All tests pass ✓

**Commit Point**: ✓ "feat: Add video matcher with player name matching"

---

### Task 3: Database Schema Migration
**Estimated Time**: 45 minutes
**Files to Create**:
- `docs/migrations/003_add_match_videos_table.md`
- `scripts/migrate_add_match_videos.py`

#### Subtask 3.1: Write Migration Documentation
**File**: `docs/migrations/003_add_match_videos_table.md`

```markdown
# Migration 003: Add Match Videos Table

## Overview
Add support for tracking YouTube videos associated with tournament matches.
This enables calculation of total match playtime across multiple sessions.

## Rationale
- Matches are played over multiple sessions (multiple days)
- Each session is recorded in a YouTube video
- We need to track total playtime, not just turn count
- Proper normalization: many videos can belong to one match

## Schema Changes

### New Table: `match_videos`
```sql
CREATE TABLE match_videos (
    id INTEGER PRIMARY KEY,
    match_id INTEGER NOT NULL REFERENCES matches(match_id),
    youtube_video_id VARCHAR(11) NOT NULL,
    video_title VARCHAR NOT NULL,
    duration_seconds INTEGER NOT NULL,
    upload_date TIMESTAMP,
    session_number INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_match_videos_match_id ON match_videos(match_id);
CREATE UNIQUE INDEX idx_match_videos_video_id ON match_videos(youtube_video_id);
```

### Table Details
- `id`: Auto-incrementing primary key
- `match_id`: Foreign key to matches table
- `youtube_video_id`: YouTube video ID (11 chars, e.g., 'dQw4w9WgXcQ')
- `video_title`: Original video title for reference
- `duration_seconds`: Video duration in seconds
- `upload_date`: When video was uploaded to YouTube
- `session_number`: Which session (1, 2, 3...) for multi-session matches
- `created_at`: When record was inserted

### Indexes
- `idx_match_videos_match_id`: Fast lookup of videos by match
- `idx_match_videos_video_id`: Prevent duplicate videos, fast lookup by video

## Migration Script

See: `scripts/migrate_add_match_videos.py`

Run with:
```bash
uv run python scripts/migrate_add_match_videos.py
```

## Rollback Procedure

To undo this migration:
```sql
DROP TABLE IF EXISTS match_videos;
```

Or run:
```bash
uv run duckdb data/tournament_data.duckdb <<EOF
DROP TABLE IF EXISTS match_videos;
EOF
```

## Verification

After migration, verify:
```bash
# Check table exists
uv run duckdb data/tournament_data.duckdb -readonly -c "DESCRIBE match_videos"

# Should show: id, match_id, youtube_video_id, video_title, duration_seconds, upload_date, session_number, created_at

# Check indexes
uv run duckdb data/tournament_data.duckdb -readonly -c "SHOW TABLES"
```

## Related Files
- `tournament_visualizer/data/video_matcher.py`: Populates this table
- `tournament_visualizer/data/queries.py`: Queries this table
- `scripts/import_youtube_data.py`: Imports data into this table
```

**Commit Point**: ✓ "docs: Add migration 003 for match_videos table"

#### Subtask 3.2: Write Migration Script with Tests
**File**: `tests/test_migration_003.py`

```python
"""Tests for migration 003 (match_videos table).

Test Strategy:
- Test migration on a fresh database
- Test migration is idempotent (safe to run twice)
- Test rollback works
- Use a temporary test database
"""

import pytest
import duckdb
from pathlib import Path
import tempfile
import shutil


class TestMigration003:
    """Test match_videos table migration."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database for testing."""
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test.duckdb"

        # Create a minimal matches table for FK constraint
        conn = duckdb.connect(str(db_path))
        conn.execute("""
            CREATE TABLE matches (
                match_id INTEGER PRIMARY KEY,
                player1_name VARCHAR,
                player2_name VARCHAR
            )
        """)
        conn.execute("""
            INSERT INTO matches VALUES
            (1, 'anarkos', 'becked'),
            (2, 'moose', 'fluffbunny')
        """)
        conn.close()

        yield db_path

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_migration_creates_table(self, temp_db_path):
        """Test that migration creates match_videos table."""
        from scripts.migrate_add_match_videos import migrate_up

        # Run migration
        migrate_up(str(temp_db_path))

        # Verify table exists
        conn = duckdb.connect(str(temp_db_path), read_only=True)
        result = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='match_videos'").fetchone()
        conn.close()

        assert result is not None

    def test_migration_creates_indexes(self, temp_db_path):
        """Test that indexes are created."""
        from scripts.migrate_add_match_videos import migrate_up

        migrate_up(str(temp_db_path))

        conn = duckdb.connect(str(temp_db_path), read_only=True)

        # Check indexes exist
        indexes = conn.execute("SHOW INDEXES FROM match_videos").fetchall()
        conn.close()

        index_names = [idx[0] for idx in indexes]
        assert 'idx_match_videos_match_id' in index_names
        assert 'idx_match_videos_video_id' in index_names

    def test_migration_idempotent(self, temp_db_path):
        """Test that running migration twice is safe."""
        from scripts.migrate_add_match_videos import migrate_up

        # Run twice
        migrate_up(str(temp_db_path))
        migrate_up(str(temp_db_path))  # Should not crash

        # Verify table still exists
        conn = duckdb.connect(str(temp_db_path), read_only=True)
        result = conn.execute("SELECT COUNT(*) FROM match_videos").fetchone()
        conn.close()

        assert result[0] == 0  # Empty table

    def test_can_insert_video(self, temp_db_path):
        """Test that we can insert data into match_videos table."""
        from scripts.migrate_add_match_videos import migrate_up

        migrate_up(str(temp_db_path))

        conn = duckdb.connect(str(temp_db_path))
        conn.execute("""
            INSERT INTO match_videos (
                match_id, youtube_video_id, video_title,
                duration_seconds, session_number
            ) VALUES (1, 'abc123xyz', 'Test Video', 3600, 1)
        """)

        result = conn.execute("SELECT * FROM match_videos").fetchone()
        conn.close()

        assert result[1] == 1  # match_id
        assert result[2] == 'abc123xyz'  # youtube_video_id
        assert result[3] == 'Test Video'  # video_title
        assert result[4] == 3600  # duration_seconds

    def test_foreign_key_constraint(self, temp_db_path):
        """Test that foreign key to matches table works."""
        from scripts.migrate_add_match_videos import migrate_up

        migrate_up(str(temp_db_path))

        conn = duckdb.connect(str(temp_db_path))

        # Try to insert video with non-existent match_id
        with pytest.raises(duckdb.ConstraintException):
            conn.execute("""
                INSERT INTO match_videos (
                    match_id, youtube_video_id, video_title,
                    duration_seconds, session_number
                ) VALUES (999, 'test123', 'Test', 100, 1)
            """)

        conn.close()

    def test_unique_video_id_constraint(self, temp_db_path):
        """Test that duplicate video IDs are prevented."""
        from scripts.migrate_add_match_videos import migrate_up

        migrate_up(str(temp_db_path))

        conn = duckdb.connect(str(temp_db_path))

        # Insert first video
        conn.execute("""
            INSERT INTO match_videos (
                match_id, youtube_video_id, video_title,
                duration_seconds, session_number
            ) VALUES (1, 'duplicate123', 'Video 1', 100, 1)
        """)

        # Try to insert same video ID again
        with pytest.raises(duckdb.ConstraintException):
            conn.execute("""
                INSERT INTO match_videos (
                    match_id, youtube_video_id, video_title,
                    duration_seconds, session_number
                ) VALUES (2, 'duplicate123', 'Video 2', 200, 1)
            """)

        conn.close()

    def test_rollback(self, temp_db_path):
        """Test that rollback removes the table."""
        from scripts.migrate_add_match_videos import migrate_up, migrate_down

        # Migrate up
        migrate_up(str(temp_db_path))

        # Verify table exists
        conn = duckdb.connect(str(temp_db_path), read_only=True)
        tables_before = conn.execute("SHOW TABLES").fetchall()
        conn.close()
        table_names_before = [t[0] for t in tables_before]
        assert 'match_videos' in table_names_before

        # Rollback
        migrate_down(str(temp_db_path))

        # Verify table is gone
        conn = duckdb.connect(str(temp_db_path), read_only=True)
        tables_after = conn.execute("SHOW TABLES").fetchall()
        conn.close()
        table_names_after = [t[0] for t in tables_after]
        assert 'match_videos' not in table_names_after
```

**Run tests (will fail)**:
```bash
uv run pytest tests/test_migration_003.py -v
```

**Commit Point**: ✓ "test: Add migration 003 tests (TDD, failing)"

#### Subtask 3.3: Implement Migration Script
**File**: `scripts/migrate_add_match_videos.py`

```python
"""Migration 003: Add match_videos table.

This migration adds support for tracking YouTube videos associated with matches.

Usage:
    # Apply migration
    uv run python scripts/migrate_add_match_videos.py

    # Rollback migration
    uv run python scripts/migrate_add_match_videos.py --rollback

See: docs/migrations/003_add_match_videos_table.md
"""

import argparse
import logging
from pathlib import Path

import duckdb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "data/tournament_data.duckdb"


def migrate_up(db_path: str = DEFAULT_DB_PATH) -> None:
    """Apply migration: Create match_videos table.

    Args:
        db_path: Path to DuckDB database
    """
    logger.info(f"Applying migration 003 to {db_path}")

    conn = duckdb.connect(db_path)

    try:
        # Create table (IF NOT EXISTS makes it idempotent)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS match_videos (
                id INTEGER PRIMARY KEY,
                match_id INTEGER NOT NULL REFERENCES matches(match_id),
                youtube_video_id VARCHAR(11) NOT NULL,
                video_title VARCHAR NOT NULL,
                duration_seconds INTEGER NOT NULL,
                upload_date TIMESTAMP,
                session_number INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_match_videos_match_id
            ON match_videos(match_id)
        """)

        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_match_videos_video_id
            ON match_videos(youtube_video_id)
        """)

        logger.info("✓ Migration 003 applied successfully")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        conn.close()


def migrate_down(db_path: str = DEFAULT_DB_PATH) -> None:
    """Rollback migration: Drop match_videos table.

    Args:
        db_path: Path to DuckDB database
    """
    logger.info(f"Rolling back migration 003 from {db_path}")

    conn = duckdb.connect(db_path)

    try:
        conn.execute("DROP TABLE IF EXISTS match_videos")
        logger.info("✓ Migration 003 rolled back successfully")

    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        raise
    finally:
        conn.close()


def verify_migration(db_path: str = DEFAULT_DB_PATH) -> None:
    """Verify migration was applied correctly.

    Args:
        db_path: Path to DuckDB database
    """
    conn = duckdb.connect(db_path, read_only=True)

    try:
        # Check table exists
        result = conn.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='match_videos'
        """).fetchone()

        if result:
            logger.info("✓ match_videos table exists")

            # Check columns
            columns = conn.execute("DESCRIBE match_videos").fetchall()
            column_names = [col[0] for col in columns]

            expected_columns = [
                'id', 'match_id', 'youtube_video_id', 'video_title',
                'duration_seconds', 'upload_date', 'session_number', 'created_at'
            ]

            for col in expected_columns:
                if col in column_names:
                    logger.info(f"✓ Column '{col}' exists")
                else:
                    logger.error(f"✗ Column '{col}' missing")
        else:
            logger.error("✗ match_videos table does not exist")

    finally:
        conn.close()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Apply or rollback migration 003"
    )
    parser.add_argument(
        '--rollback',
        action='store_true',
        help='Rollback the migration'
    )
    parser.add_argument(
        '--db',
        default=DEFAULT_DB_PATH,
        help='Path to database (default: data/tournament_data.duckdb)'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify migration was applied'
    )

    args = parser.parse_args()

    if args.verify:
        verify_migration(args.db)
    elif args.rollback:
        migrate_down(args.db)
    else:
        migrate_up(args.db)


if __name__ == '__main__':
    main()
```

**Run tests**:
```bash
uv run pytest tests/test_migration_003.py -v
```

**Expected**: All tests pass ✓

**Test on real database** (make backup first):
```bash
# Backup database
cp data/tournament_data.duckdb data/tournament_data.duckdb.backup_before_migration_003

# Apply migration
uv run python scripts/migrate_add_match_videos.py

# Verify
uv run python scripts/migrate_add_match_videos.py --verify

# Check manually
uv run duckdb data/tournament_data.duckdb -readonly -c "DESCRIBE match_videos"
```

**Commit Point**: ✓ "feat: Add migration script for match_videos table"

---

### Task 4: Create Import Script
**Estimated Time**: 1 hour
**Files to Create**:
- `scripts/import_youtube_data.py`
- `tests/test_import_youtube_data.py`

#### Subtask 4.1: Write Tests (TDD)
**File**: `tests/test_import_youtube_data.py`

```python
"""Tests for YouTube data import script.

Test Strategy:
- Mock YouTube API and database
- Test end-to-end flow
- Test error handling
- Use temporary database
"""

import pytest
from unittest.mock import MagicMock, patch
import duckdb
import tempfile
import shutil
from pathlib import Path
from datetime import datetime


class TestImportYouTubeData:
    """Test YouTube data import."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database with test data."""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test.duckdb"

        conn = duckdb.connect(str(db_path))

        # Create matches table
        conn.execute("""
            CREATE TABLE matches (
                match_id INTEGER PRIMARY KEY,
                player1_name VARCHAR,
                player2_name VARCHAR
            )
        """)

        conn.execute("""
            INSERT INTO matches VALUES
            (1, 'anarkos', 'becked'),
            (2, 'moose', 'fluffbunny')
        """)

        # Create match_videos table
        conn.execute("""
            CREATE TABLE match_videos (
                id INTEGER PRIMARY KEY,
                match_id INTEGER NOT NULL,
                youtube_video_id VARCHAR(11) NOT NULL,
                video_title VARCHAR NOT NULL,
                duration_seconds INTEGER NOT NULL,
                upload_date TIMESTAMP,
                session_number INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.close()

        yield db_path

        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_youtube_videos(self):
        """Mock YouTube API response."""
        from tournament_visualizer.integrations.youtube import Video

        return [
            Video(
                video_id='abc123',
                title='anarkos vs becked - Session 1',
                duration_seconds=5400,
                upload_date=datetime(2025, 9, 20)
            ),
            Video(
                video_id='def456',
                title='anarkos vs becked - Session 2',
                duration_seconds=7200,
                upload_date=datetime(2025, 9, 21)
            ),
        ]

    @patch('scripts.import_youtube_data.YouTubeClient')
    def test_import_success(self, mock_youtube_class, temp_db_path, mock_youtube_videos):
        """Test successful import of YouTube data."""
        # Setup mocks
        mock_client = MagicMock()
        mock_client.get_playlist_videos.return_value = mock_youtube_videos
        mock_youtube_class.return_value = mock_client

        # Run import
        from scripts.import_youtube_data import import_youtube_data

        result = import_youtube_data(
            playlist_id="test_playlist",
            db_path=str(temp_db_path),
            api_key="fake_key"
        )

        # Verify results
        assert result['videos_fetched'] == 2
        assert result['videos_matched'] == 2
        assert result['videos_imported'] == 2

        # Verify database
        conn = duckdb.connect(str(temp_db_path), read_only=True)
        videos = conn.execute("SELECT * FROM match_videos ORDER BY session_number").fetchall()
        conn.close()

        assert len(videos) == 2
        assert videos[0][1] == 1  # match_id
        assert videos[0][2] == 'abc123'  # youtube_video_id
        assert videos[0][4] == 5400  # duration_seconds
        assert videos[0][6] == 1  # session_number

    @patch('scripts.import_youtube_data.YouTubeClient')
    def test_import_no_matches(self, mock_youtube_class, temp_db_path):
        """Test import when no videos match any matches."""
        from tournament_visualizer.integrations.youtube import Video

        # Mock unmatched videos
        unmatched_videos = [
            Video(
                video_id='xyz789',
                title='Random Video',
                duration_seconds=1000,
                upload_date=datetime(2025, 9, 22)
            )
        ]

        mock_client = MagicMock()
        mock_client.get_playlist_videos.return_value = unmatched_videos
        mock_youtube_class.return_value = mock_client

        # Run import
        from scripts.import_youtube_data import import_youtube_data

        result = import_youtube_data(
            playlist_id="test_playlist",
            db_path=str(temp_db_path),
            api_key="fake_key"
        )

        # Verify results
        assert result['videos_fetched'] == 1
        assert result['videos_matched'] == 0
        assert result['videos_imported'] == 0

        # Verify database is empty
        conn = duckdb.connect(str(temp_db_path), read_only=True)
        count = conn.execute("SELECT COUNT(*) FROM match_videos").fetchone()[0]
        conn.close()

        assert count == 0

    def test_import_duplicate_video(self, temp_db_path, mock_youtube_videos):
        """Test that importing same video twice is handled."""
        from scripts.import_youtube_data import import_youtube_data

        # Import once
        with patch('scripts.import_youtube_data.YouTubeClient') as mock_youtube_class:
            mock_client = MagicMock()
            mock_client.get_playlist_videos.return_value = mock_youtube_videos
            mock_youtube_class.return_value = mock_client

            import_youtube_data(
                playlist_id="test_playlist",
                db_path=str(temp_db_path),
                api_key="fake_key"
            )

        # Import again (should skip duplicates)
        with patch('scripts.import_youtube_data.YouTubeClient') as mock_youtube_class:
            mock_client = MagicMock()
            mock_client.get_playlist_videos.return_value = mock_youtube_videos
            mock_youtube_class.return_value = mock_client

            result = import_youtube_data(
                playlist_id="test_playlist",
                db_path=str(temp_db_path),
                api_key="fake_key"
            )

        # Should skip duplicates
        assert result['videos_imported'] == 0

        # Database should still have only 2 videos
        conn = duckdb.connect(str(temp_db_path), read_only=True)
        count = conn.execute("SELECT COUNT(*) FROM match_videos").fetchone()[0]
        conn.close()

        assert count == 2
```

**Run tests (will fail)**:
```bash
uv run pytest tests/test_import_youtube_data.py -v
```

**Commit Point**: ✓ "test: Add import script tests (TDD, failing)"

#### Subtask 4.2: Implement Import Script
**File**: `scripts/import_youtube_data.py`

```python
"""Import YouTube video data and match to tournament matches.

This script:
1. Fetches videos from YouTube playlist
2. Matches videos to tournament matches by player names
3. Imports video metadata into database

Usage:
    # Import from default playlist
    uv run python scripts/import_youtube_data.py

    # Import from specific playlist
    uv run python scripts/import_youtube_data.py --playlist PLsRPrwJXwEjaUyfAN956kM8WBGWPsHBEp

    # Dry run (don't insert into database)
    uv run python scripts/import_youtube_data.py --dry-run

Requirements:
    - YOUTUBE_API_KEY environment variable must be set
    - Database must have match_videos table (run migration 003 first)
"""

import argparse
import logging
import os
from pathlib import Path
from typing import Dict, Any, List

import duckdb
from dotenv import load_dotenv

from tournament_visualizer.integrations.youtube import YouTubeClient
from tournament_visualizer.data.video_matcher import VideoMatcher, MatchedVideo

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DEFAULT_PLAYLIST_ID = "PLsRPrwJXwEjaUyfAN956kM8WBGWPsHBEp"
DEFAULT_DB_PATH = "data/tournament_data.duckdb"


def import_youtube_data(
    playlist_id: str,
    db_path: str = DEFAULT_DB_PATH,
    api_key: str | None = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """Import YouTube video data for tournament matches.

    Args:
        playlist_id: YouTube playlist ID
        db_path: Path to DuckDB database
        api_key: YouTube API key (defaults to env var)
        dry_run: If True, don't insert into database

    Returns:
        Dictionary with import statistics

    Raises:
        ValueError: If API key is missing or database doesn't exist
    """
    # Get API key
    if not api_key:
        api_key = os.getenv('YOUTUBE_API_KEY')

    if not api_key:
        raise ValueError(
            "YouTube API key required. "
            "Set YOUTUBE_API_KEY environment variable or pass --api-key"
        )

    # Check database exists
    if not Path(db_path).exists():
        raise ValueError(f"Database not found: {db_path}")

    logger.info("=" * 60)
    logger.info("YouTube Data Import")
    logger.info("=" * 60)
    logger.info(f"Playlist: {playlist_id}")
    logger.info(f"Database: {db_path}")
    logger.info(f"Dry run: {dry_run}")
    logger.info("")

    # Step 1: Fetch videos from YouTube
    logger.info("Step 1: Fetching videos from YouTube...")
    youtube_client = YouTubeClient(api_key=api_key)
    videos = youtube_client.get_playlist_videos(playlist_id)
    logger.info(f"✓ Fetched {len(videos)} videos")
    logger.info("")

    # Step 2: Load matches from database
    logger.info("Step 2: Loading matches from database...")
    matches = _load_matches(db_path)
    logger.info(f"✓ Loaded {len(matches)} matches")
    logger.info("")

    # Step 3: Match videos to matches
    logger.info("Step 3: Matching videos to tournament matches...")
    matcher = VideoMatcher()
    matched_videos = matcher.match_videos_to_matches(videos, matches)
    logger.info(f"✓ Matched {len(matched_videos)} videos")

    # Show unmatched videos
    matched_ids = {v.video_id for v in matched_videos}
    unmatched = [v for v in videos if v.video_id not in matched_ids]
    if unmatched:
        logger.warning(f"⚠ {len(unmatched)} videos did not match any tournament match:")
        for video in unmatched:
            logger.warning(f"  - {video.title}")
    logger.info("")

    # Step 4: Insert into database
    logger.info("Step 4: Inserting into database...")
    if dry_run:
        logger.info("DRY RUN - Skipping database insert")
        inserted_count = 0
    else:
        inserted_count = _insert_matched_videos(db_path, matched_videos)
        logger.info(f"✓ Inserted {inserted_count} videos")
    logger.info("")

    # Summary
    logger.info("=" * 60)
    logger.info("Import Summary")
    logger.info("=" * 60)
    logger.info(f"Videos fetched:  {len(videos)}")
    logger.info(f"Videos matched:  {len(matched_videos)}")
    logger.info(f"Videos imported: {inserted_count}")
    logger.info(f"Videos skipped:  {len(unmatched)}")
    logger.info("=" * 60)

    return {
        'videos_fetched': len(videos),
        'videos_matched': len(matched_videos),
        'videos_imported': inserted_count,
        'videos_skipped': len(unmatched)
    }


def _load_matches(db_path: str) -> List[Dict[str, Any]]:
    """Load matches from database.

    Args:
        db_path: Path to database

    Returns:
        List of match dictionaries
    """
    conn = duckdb.connect(db_path, read_only=True)

    result = conn.execute("""
        SELECT
            match_id,
            player1_name,
            player2_name
        FROM matches
        WHERE player1_name IS NOT NULL
          AND player2_name IS NOT NULL
    """).fetchall()

    conn.close()

    matches = []
    for row in result:
        matches.append({
            'match_id': row[0],
            'player1_name': row[1],
            'player2_name': row[2]
        })

    return matches


def _insert_matched_videos(
    db_path: str,
    matched_videos: List[MatchedVideo]
) -> int:
    """Insert matched videos into database.

    Skips videos that already exist (based on youtube_video_id).

    Args:
        db_path: Path to database
        matched_videos: Videos to insert

    Returns:
        Number of videos inserted
    """
    if not matched_videos:
        return 0

    conn = duckdb.connect(db_path)
    inserted_count = 0

    for video in matched_videos:
        try:
            # Check if video already exists
            existing = conn.execute(
                "SELECT id FROM match_videos WHERE youtube_video_id = ?",
                [video.video_id]
            ).fetchone()

            if existing:
                logger.debug(f"Skipping duplicate video: {video.video_id}")
                continue

            # Insert video
            conn.execute("""
                INSERT INTO match_videos (
                    match_id,
                    youtube_video_id,
                    video_title,
                    duration_seconds,
                    session_number
                ) VALUES (?, ?, ?, ?, ?)
            """, [
                video.match_id,
                video.video_id,
                video.video_title,
                video.duration_seconds,
                video.session_number
            ])

            inserted_count += 1
            logger.debug(f"Inserted video: {video.video_title}")

        except Exception as e:
            logger.error(f"Failed to insert video {video.video_id}: {e}")

    conn.close()

    return inserted_count


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Import YouTube video data for tournament matches"
    )
    parser.add_argument(
        '--playlist',
        default=DEFAULT_PLAYLIST_ID,
        help='YouTube playlist ID'
    )
    parser.add_argument(
        '--db',
        default=DEFAULT_DB_PATH,
        help='Path to database'
    )
    parser.add_argument(
        '--api-key',
        help='YouTube API key (defaults to YOUTUBE_API_KEY env var)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run (don\'t insert into database)'
    )

    args = parser.parse_args()

    try:
        import_youtube_data(
            playlist_id=args.playlist,
            db_path=args.db,
            api_key=args.api_key,
            dry_run=args.dry_run
        )
    except Exception as e:
        logger.error(f"Import failed: {e}")
        raise


if __name__ == '__main__':
    main()
```

**Run tests**:
```bash
uv run pytest tests/test_import_youtube_data.py -v
```

**Expected**: All tests pass ✓

**Test manually (dry run first)**:
```bash
# Dry run
uv run python scripts/import_youtube_data.py --dry-run

# Real import
uv run python scripts/import_youtube_data.py

# Verify
uv run duckdb data/tournament_data.duckdb -readonly -c "SELECT COUNT(*) FROM match_videos"
```

**Commit Point**: ✓ "feat: Add YouTube data import script with matching"

---

### Task 5: Add Database Query Helper
**Estimated Time**: 30 minutes
**Files to Modify**:
- `tournament_visualizer/data/queries.py`
- `tests/test_queries.py`

#### Subtask 5.1: Add Tests
**File**: `tests/test_queries.py` (add to existing file or create new)

```python
"""Tests for database queries (YouTube-related)."""

import pytest
import duckdb
import tempfile
import shutil
from pathlib import Path


class TestMatchVideosQueries:
    """Test queries for match videos."""

    @pytest.fixture
    def temp_db_with_videos(self):
        """Create test database with sample video data."""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test.duckdb"

        conn = duckdb.connect(str(db_path))

        # Create tables
        conn.execute("""
            CREATE TABLE matches (
                match_id INTEGER PRIMARY KEY,
                player1_name VARCHAR,
                player2_name VARCHAR,
                total_turns INTEGER
            )
        """)

        conn.execute("""
            CREATE TABLE match_videos (
                id INTEGER PRIMARY KEY,
                match_id INTEGER,
                youtube_video_id VARCHAR(11),
                video_title VARCHAR,
                duration_seconds INTEGER,
                session_number INTEGER
            )
        """)

        # Insert test data
        conn.execute("""
            INSERT INTO matches VALUES
            (1, 'anarkos', 'becked', 92),
            (2, 'moose', 'fluffbunny', 47)
        """)

        conn.execute("""
            INSERT INTO match_videos VALUES
            (1, 1, 'abc123', 'anarkos vs becked - Session 1', 5400, 1),
            (2, 1, 'def456', 'anarkos vs becked - Session 2', 7200, 2),
            (3, 2, 'ghi789', 'moose vs fluffbunny', 3600, 1)
        """)

        conn.close()

        yield db_path

        shutil.rmtree(temp_dir)

    def test_get_match_videos(self, temp_db_with_videos):
        """Test getting videos for a specific match."""
        from tournament_visualizer.data.queries import get_match_videos

        videos = get_match_videos(1, str(temp_db_with_videos))

        assert len(videos) == 2
        assert videos[0]['session_number'] == 1
        assert videos[0]['duration_seconds'] == 5400
        assert videos[1]['session_number'] == 2

    def test_get_match_total_playtime(self, temp_db_with_videos):
        """Test calculating total playtime for a match."""
        from tournament_visualizer.data.queries import get_match_total_playtime

        # Match 1 has 2 sessions: 5400 + 7200 = 12600 seconds
        playtime = get_match_total_playtime(1, str(temp_db_with_videos))

        assert playtime == 12600

    def test_get_all_matches_with_playtime(self, temp_db_with_videos):
        """Test getting all matches with playtime."""
        from tournament_visualizer.data.queries import get_matches_with_playtime

        matches = get_matches_with_playtime(str(temp_db_with_videos))

        assert len(matches) == 2

        # Check match 1
        match_1 = [m for m in matches if m['match_id'] == 1][0]
        assert match_1['total_playtime_seconds'] == 12600
        assert match_1['session_count'] == 2

        # Check match 2
        match_2 = [m for m in matches if m['match_id'] == 2][0]
        assert match_2['total_playtime_seconds'] == 3600
        assert match_2['session_count'] == 1
```

**Run tests (will fail)**:
```bash
uv run pytest tests/test_queries.py::TestMatchVideosQueries -v
```

**Commit Point**: ✓ "test: Add query tests for match videos (TDD, failing)"

#### Subtask 5.2: Implement Query Functions
**File**: `tournament_visualizer/data/queries.py` (add to existing file)

```python
# Add these functions to the existing queries.py file

def get_match_videos(match_id: int, db_path: str = "data/tournament_data.duckdb") -> List[Dict[str, Any]]:
    """Get all videos for a specific match.

    Args:
        match_id: Tournament match ID
        db_path: Path to database

    Returns:
        List of video dictionaries
    """
    conn = duckdb.connect(db_path, read_only=True)

    result = conn.execute("""
        SELECT
            youtube_video_id,
            video_title,
            duration_seconds,
            session_number,
            upload_date
        FROM match_videos
        WHERE match_id = ?
        ORDER BY session_number
    """, [match_id]).fetchall()

    conn.close()

    videos = []
    for row in result:
        videos.append({
            'youtube_video_id': row[0],
            'video_title': row[1],
            'duration_seconds': row[2],
            'session_number': row[3],
            'upload_date': row[4]
        })

    return videos


def get_match_total_playtime(match_id: int, db_path: str = "data/tournament_data.duckdb") -> int:
    """Calculate total playtime for a match.

    Args:
        match_id: Tournament match ID
        db_path: Path to database

    Returns:
        Total playtime in seconds, or 0 if no videos
    """
    conn = duckdb.connect(db_path, read_only=True)

    result = conn.execute("""
        SELECT SUM(duration_seconds)
        FROM match_videos
        WHERE match_id = ?
    """, [match_id]).fetchone()

    conn.close()

    return result[0] or 0


def get_matches_with_playtime(db_path: str = "data/tournament_data.duckdb") -> List[Dict[str, Any]]:
    """Get all matches with playtime statistics.

    Args:
        db_path: Path to database

    Returns:
        List of match dictionaries with playtime data
    """
    conn = duckdb.connect(db_path, read_only=True)

    result = conn.execute("""
        SELECT
            m.match_id,
            m.player1_name,
            m.player2_name,
            m.total_turns,
            COALESCE(SUM(v.duration_seconds), 0) as total_playtime_seconds,
            COUNT(v.id) as session_count
        FROM matches m
        LEFT JOIN match_videos v ON m.match_id = v.match_id
        GROUP BY m.match_id, m.player1_name, m.player2_name, m.total_turns
        ORDER BY m.match_id
    """).fetchall()

    conn.close()

    matches = []
    for row in result:
        matches.append({
            'match_id': row[0],
            'player1_name': row[1],
            'player2_name': row[2],
            'total_turns': row[3],
            'total_playtime_seconds': row[4],
            'session_count': row[5],
            'playtime_hours': row[4] / 3600.0 if row[4] else 0
        })

    return matches
```

**Run tests**:
```bash
uv run pytest tests/test_queries.py::TestMatchVideosQueries -v
```

**Expected**: All tests pass ✓

**Commit Point**: ✓ "feat: Add query functions for match videos and playtime"

---

### Task 6: Update Dash App UI
**Estimated Time**: 1 hour
**Files to Modify**:
- `tournament_visualizer/app.py` (or wherever match detail page is)

**Note**: Without seeing your actual Dash app code, I'll provide a general approach:

#### Subtask 6.1: Add Playtime to Match Detail Page

Find the match detail page component and add:

```python
def create_match_detail_layout(match_id: int) -> html.Div:
    """Create match detail page layout."""
    from tournament_visualizer.data.queries import (
        get_match_total_playtime,
        get_match_videos
    )

    # Get existing match data
    # ... existing code ...

    # Get playtime data
    total_playtime = get_match_total_playtime(match_id)
    videos = get_match_videos(match_id)

    # Format playtime
    hours = total_playtime // 3600
    minutes = (total_playtime % 3600) // 60
    playtime_str = f"{hours}h {minutes}m"

    # Create playtime display
    playtime_section = html.Div([
        html.H3("Match Playtime"),
        html.P(f"Total Duration: {playtime_str} ({len(videos)} sessions)"),

        # Video session list
        html.Ul([
            html.Li([
                html.A(
                    f"Session {v['session_number']}: {v['duration_seconds'] // 60} minutes",
                    href=f"https://youtube.com/watch?v={v['youtube_video_id']}",
                    target="_blank"
                )
            ])
            for v in videos
        ]) if videos else html.P("No video data available")
    ])

    return html.Div([
        # ... existing layout ...
        playtime_section
    ])
```

#### Subtask 6.2: Add Playtime to Match List/Table

Update match list to show playtime:

```python
def create_match_table() -> dash_table.DataTable:
    """Create match list table."""
    from tournament_visualizer.data.queries import get_matches_with_playtime

    matches = get_matches_with_playtime()

    return dash_table.DataTable(
        data=matches,
        columns=[
            {'name': 'Match ID', 'id': 'match_id'},
            {'name': 'Player 1', 'id': 'player1_name'},
            {'name': 'Player 2', 'id': 'player2_name'},
            {'name': 'Turns', 'id': 'total_turns'},
            {'name': 'Playtime (hours)', 'id': 'playtime_hours', 'type': 'numeric', 'format': {'specifier': '.1f'}},
            {'name': 'Sessions', 'id': 'session_count'},
        ],
        # ... other DataTable props ...
    )
```

**Manual Testing**:
1. Run import script to populate data
2. Start Dash app: `uv run python manage.py restart`
3. Navigate to match detail page
4. Verify playtime is displayed
5. Click YouTube links to verify they work

**Commit Point**: ✓ "feat: Display match playtime in UI with YouTube links"

---

## Final Integration & Testing

### Integration Test
**File**: `tests/integration/test_youtube_integration.py`

```python
"""Integration test for complete YouTube workflow.

This tests the entire flow:
1. Fetch videos from YouTube (mocked)
2. Match to tournament matches
3. Import into database
4. Query playtime data
"""

import pytest
import duckdb
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime


def test_complete_youtube_workflow():
    """Test complete workflow from YouTube API to database."""
    # Setup: Create temporary database
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test.duckdb"

    try:
        # Create schema
        conn = duckdb.connect(str(db_path))
        conn.execute("""
            CREATE TABLE matches (
                match_id INTEGER PRIMARY KEY,
                player1_name VARCHAR,
                player2_name VARCHAR
            )
        """)
        conn.execute("INSERT INTO matches VALUES (1, 'anarkos', 'becked')")

        conn.execute("""
            CREATE TABLE match_videos (
                id INTEGER PRIMARY KEY,
                match_id INTEGER,
                youtube_video_id VARCHAR(11),
                video_title VARCHAR,
                duration_seconds INTEGER,
                session_number INTEGER
            )
        """)
        conn.close()

        # Mock YouTube API
        from tournament_visualizer.integrations.youtube import Video

        mock_videos = [
            Video(
                video_id='abc123',
                title='anarkos vs becked - Session 1',
                duration_seconds=5400,
                upload_date=datetime(2025, 9, 20)
            ),
            Video(
                video_id='def456',
                title='anarkos vs becked - Session 2',
                duration_seconds=7200,
                upload_date=datetime(2025, 9, 21)
            ),
        ]

        # Run import
        with patch('scripts.import_youtube_data.YouTubeClient') as mock_youtube:
            mock_client = MagicMock()
            mock_client.get_playlist_videos.return_value = mock_videos
            mock_youtube.return_value = mock_client

            from scripts.import_youtube_data import import_youtube_data

            result = import_youtube_data(
                playlist_id="test_playlist",
                db_path=str(db_path),
                api_key="fake_key"
            )

        # Verify import
        assert result['videos_imported'] == 2

        # Query playtime
        from tournament_visualizer.data.queries import get_match_total_playtime

        total_playtime = get_match_total_playtime(1, str(db_path))
        assert total_playtime == 12600  # 5400 + 7200

        # Query videos
        from tournament_visualizer.data.queries import get_match_videos

        videos = get_match_videos(1, str(db_path))
        assert len(videos) == 2
        assert videos[0]['session_number'] == 1
        assert videos[1]['session_number'] == 2

    finally:
        shutil.rmtree(temp_dir)
```

**Run integration test**:
```bash
uv run pytest tests/integration/test_youtube_integration.py -v
```

**Commit Point**: ✓ "test: Add end-to-end integration test for YouTube workflow"

---

## Documentation

### Update User Documentation
**File**: `CLAUDE.md` (add section)

```markdown
## YouTube Video Tracking

### Overview
Tournament matches are tracked via YouTube videos. The system automatically fetches video durations and calculates total playtime.

### Setup
1. Get YouTube API key: https://console.cloud.google.com/apis/credentials
2. Set environment variable: `export YOUTUBE_API_KEY="your_key"`
3. Run migration: `uv run python scripts/migrate_add_match_videos.py`

### Usage
```bash
# Import video data from default playlist
uv run python scripts/import_youtube_data.py

# Dry run (preview without inserting)
uv run python scripts/import_youtube_data.py --dry-run

# Use different playlist
uv run python scripts/import_youtube_data.py --playlist YOUR_PLAYLIST_ID
```

### Querying Playtime
```python
from tournament_visualizer.data.queries import (
    get_match_total_playtime,
    get_match_videos
)

# Get total playtime for a match
playtime = get_match_total_playtime(match_id=1)
print(f"Total: {playtime // 3600} hours, {(playtime % 3600) // 60} minutes")

# Get all videos for a match
videos = get_match_videos(match_id=1)
for video in videos:
    print(f"Session {video['session_number']}: {video['video_title']}")
```

### Troubleshooting
- **API quota exceeded**: YouTube API has daily quota limits. Wait 24 hours or request increase.
- **No videos matched**: Check that video titles contain both player names.
- **Duplicate videos**: Import script automatically skips existing videos.
```

**Commit Point**: ✓ "docs: Add YouTube video tracking documentation"

---

## Final Checklist

Before marking complete, verify:

- [ ] All tests pass: `uv run pytest -v`
- [ ] Code formatted: `uv run black tournament_visualizer/ scripts/`
- [ ] Linting passes: `uv run ruff check --fix tournament_visualizer/ scripts/`
- [ ] Migration applied: `uv run python scripts/migrate_add_match_videos.py --verify`
- [ ] Import works: `uv run python scripts/import_youtube_data.py --dry-run`
- [ ] Documentation complete
- [ ] Manual UI testing passed
- [ ] All commits pushed

---

## Time Estimates

| Task | Estimated Time | Description |
|------|---------------|-------------|
| 0. Setup | 30 min | Prerequisites, exploration |
| 1. YouTube Client | 1 hour | TDD implementation |
| 2. Video Matcher | 1.5 hours | Matching logic |
| 3. Database Migration | 45 min | Schema changes |
| 4. Import Script | 1 hour | End-to-end import |
| 5. Query Functions | 30 min | Database queries |
| 6. UI Updates | 1 hour | Dash app changes |
| 7. Integration Test | 30 min | E2E testing |
| 8. Documentation | 30 min | User docs |
| **Total** | **7.5 hours** | Full implementation |

---

## Common Pitfalls

### Pitfall 1: YouTube API Quota
**Problem**: YouTube API has daily quota limits (10,000 units/day).
**Solution**:
- Cache API responses locally
- Use `--dry-run` for testing
- Each playlist fetch costs ~3-5 units

### Pitfall 2: Name Matching Failures
**Problem**: Video titles don't match player names.
**Solution**:
- Check player names in database: `SELECT DISTINCT player1_name FROM matches`
- Ensure video titles follow format: "player1 vs player2"
- Add name normalization rules in `video_matcher.py`

### Pitfall 3: Database Connection Issues
**Problem**: DuckDB file locked or permission errors.
**Solution**:
- Close all connections properly (`conn.close()`)
- Use `read_only=True` for queries
- Backup database before migrations

### Pitfall 4: Test Isolation
**Problem**: Tests affect each other.
**Solution**:
- Use fixtures with temporary databases
- Never use real database in tests
- Mock all external APIs

---

## Success Criteria

You'll know the implementation is complete when:

1. ✅ All tests pass (`pytest -v`)
2. ✅ Import script successfully fetches and matches videos
3. ✅ Database contains `match_videos` table with data
4. ✅ UI displays playtime on match pages
5. ✅ YouTube links work and open correct videos
6. ✅ Documentation is complete and accurate
7. ✅ Code is formatted and linted
8. ✅ All commits follow conventions

---

## Questions?

If stuck:
1. Check test output for specific errors
2. Review existing code patterns in similar files
3. Verify environment variables are set
4. Check logs: `uv run python manage.py logs`
5. Test individual components in Python REPL

Good luck! Remember: TDD, DRY, YAGNI, frequent commits. 🚀
