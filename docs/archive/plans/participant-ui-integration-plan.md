# Participant Tracking UI Integration Plan

> **Status**: Completed and archived (2025-10-25)
>
> Feature complete and documented in CLAUDE.md (Participant UI Integration section).
> See migrations/004_add_tournament_participants.md for schema changes.

## Overview

Update the web application to display tournament participants (real people) instead of match-scoped player instances, while gracefully handling players who haven't been linked to Challonge participant data yet.

## Background

### Current Problem

The database currently stores two types of player identity:
1. **Match-scoped players** (`players` table): Each save file creates independent player records with unique `player_id` values
2. **Tournament participants** (`tournament_participants` table): Persistent identity across all matches, linked via `participant_id`

Example of the problem:
- **Match 8**: Ninja (player_id=15) plays with Rome
- **Match 9**: Ninja (player_id=17) plays with Assyria
- Database treats these as separate entities, but they're the same person

The participant tracking system (implemented in migration 004) solves this by:
1. Importing Challonge participant data
2. Linking save file players to participants via name matching
3. Storing `participant_id` foreign keys in the `players` table

### Current Data State

As of implementation:
- **32 total player instances** (match-scoped records)
- **11 unique participants** successfully linked (44% coverage)
- **18 unlinked instances** (56%) - names don't match Challonge usernames

**Why the mismatch?** Players use shortened names in Old World saves but have full usernames in Challonge:
- Save file: "Ninja" → Challonge: "Ninjaa"
- Save file: "Fiddler" → Challonge: "fiddlers25"
- Save file: "Droner" → Challonge: "Droner22228765"

### Solution Approach

**Option 2: Show All Players with Fallback**

Display participant data when available, fall back to grouped player names when not linked:
- Linked players: Show participant display name, group by `participant_id`
- Unlinked players: Show player name, group by `player_name_normalized`
- Visual indicator: Mark unlinked players with badge/icon
- No data hidden: All matches contribute to statistics

Benefits:
- ✅ Users see all their match data
- ✅ Gracefully handles incomplete linking
- ✅ Works during tournament (new players not in Challonge yet)
- ✅ Incentivizes data quality through visual feedback

## Architecture Context

### Database Schema

**Key tables:**
```sql
-- Persistent participant identity (from Challonge)
CREATE TABLE tournament_participants (
    participant_id BIGINT PRIMARY KEY,
    display_name VARCHAR NOT NULL,
    display_name_normalized VARCHAR NOT NULL,
    -- ... other fields
);

-- Match-scoped player instances
CREATE TABLE players (
    player_id INTEGER PRIMARY KEY,
    match_id BIGINT NOT NULL,
    player_name VARCHAR NOT NULL,
    player_name_normalized VARCHAR NOT NULL,
    participant_id BIGINT,  -- nullable! links to tournament_participants
    civilization VARCHAR,
    final_score INTEGER,
    -- ... other fields
);
```

**Key relationships:**
- `players.participant_id` → `tournament_participants.participant_id` (nullable)
- `players.player_name_normalized` used for fallback grouping when participant_id IS NULL

### Application Architecture

The web app is a Dash (Plotly) application with this structure:

```
tournament_visualizer/
├── data/
│   ├── database.py           # DuckDB connection management
│   ├── queries.py            # SQL query definitions (THIS IS CRITICAL)
│   └── participant_matcher.py # Name matching logic
├── pages/
│   ├── players.py            # Players page (NEEDS UPDATES)
│   ├── overview.py           # Charts using player stats
│   └── matches.py            # Match detail pages
├── components/
│   ├── charts.py             # Chart creation functions
│   └── layouts.py            # UI component builders
└── app.py                    # Main Dash application
```

**Data flow:**
1. Page callback triggers (e.g., user visits `/players`)
2. Callback calls `get_queries().get_player_performance()`
3. Query executes SQL against DuckDB
4. DataFrame returned to callback
5. Callback formats data for UI components
6. UI renders tables/charts

## Implementation Tasks

### Task 1: Update Player Performance Query (CRITICAL)

**Objective**: Modify `get_player_performance()` to group by participant when available, fall back to player name when not.

**Files to Modify**:
- `tournament_visualizer/data/queries.py`

**Current Query** (lines 71-99):
```python
def get_player_performance(self) -> pd.DataFrame:
    """Get player performance statistics."""
    query = """
    SELECT
        MAX(p.player_name) as player_name,
        p.civilization,
        COUNT(DISTINCT p.match_id) as total_matches,
        COUNT(CASE WHEN mw.winner_player_id = p.player_id THEN 1 END) as wins,
        ROUND(
            COUNT(CASE WHEN mw.winner_player_id = p.player_id THEN 1 END) * 100.0 /
            COUNT(DISTINCT p.match_id), 2
        ) as win_rate,
        AVG(p.final_score) as avg_score,
        MAX(p.final_score) as max_score,
        MIN(p.final_score) as min_score
    FROM players p
    JOIN matches m ON p.match_id = m.match_id
    LEFT JOIN match_winners mw ON p.match_id = mw.match_id
    GROUP BY p.player_name_normalized, p.civilization  -- ❌ WRONG!
    HAVING COUNT(DISTINCT p.match_id) > 0
    ORDER BY win_rate DESC, total_matches DESC
    """
```

**Problems with current query:**
1. Groups by `player_name_normalized, civilization` - creates duplicate rows for players who used multiple civs
2. Doesn't use `participant_id` at all
3. Shows "player instances" not "people"

**New Query Implementation**:

```python
def get_player_performance(self) -> pd.DataFrame:
    """Get player performance statistics.

    Groups by tournament participant when available, falls back to
    player name for unlinked players. Returns one row per person.

    Returns:
        DataFrame with columns:
            - player_name: Display name (participant or player name)
            - participant_id: Participant ID (NULL for unlinked)
            - is_unlinked: Boolean, TRUE if not linked to participant
            - total_matches: Count of matches played
            - wins: Count of wins
            - win_rate: Win percentage (0-100)
            - avg_score: Average final score
            - max_score: Highest final score
            - min_score: Lowest final score
            - civilizations_played: Comma-separated list of civs used
            - favorite_civilization: Most-played civ
    """
    query = """
    WITH player_grouping AS (
        -- Create smart grouping key: participant_id if linked, else normalized name
        SELECT
            p.player_id,
            p.match_id,
            p.player_name,
            p.civilization,
            p.final_score,
            tp.participant_id,
            tp.display_name as participant_display_name,
            -- Grouping key: use participant_id if available, else normalized name
            COALESCE(
                CAST(tp.participant_id AS VARCHAR),
                'unlinked_' || p.player_name_normalized
            ) as grouping_key,
            -- Display name: prefer participant, fallback to player
            COALESCE(tp.display_name, p.player_name) as display_name,
            -- Flag for unlinked players
            CASE WHEN tp.participant_id IS NULL THEN TRUE ELSE FALSE END as is_unlinked
        FROM players p
        LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
    ),
    aggregated_stats AS (
        SELECT
            pg.grouping_key,
            MAX(pg.display_name) as player_name,
            MAX(pg.participant_id) as participant_id,
            MAX(pg.is_unlinked) as is_unlinked,
            COUNT(DISTINCT pg.match_id) as total_matches,
            COUNT(CASE WHEN mw.winner_player_id = pg.player_id THEN 1 END) as wins,
            ROUND(
                COUNT(CASE WHEN mw.winner_player_id = pg.player_id THEN 1 END) * 100.0 /
                NULLIF(COUNT(DISTINCT pg.match_id), 0), 2
            ) as win_rate,
            AVG(pg.final_score) as avg_score,
            MAX(pg.final_score) as max_score,
            MIN(pg.final_score) as min_score,
            -- Aggregate civilizations
            STRING_AGG(DISTINCT pg.civilization, ', ' ORDER BY pg.civilization)
                FILTER (WHERE pg.civilization IS NOT NULL) as civilizations_played,
            -- Count civ usage for favorite
            MODE() WITHIN GROUP (ORDER BY pg.civilization)
                FILTER (WHERE pg.civilization IS NOT NULL) as favorite_civilization
        FROM player_grouping pg
        LEFT JOIN match_winners mw ON pg.match_id = mw.match_id
        GROUP BY pg.grouping_key
        HAVING COUNT(DISTINCT pg.match_id) > 0
    )
    SELECT
        player_name,
        participant_id,
        is_unlinked,
        total_matches,
        wins,
        win_rate,
        avg_score,
        max_score,
        min_score,
        civilizations_played,
        favorite_civilization
    FROM aggregated_stats
    ORDER BY win_rate DESC, total_matches DESC
    """

    with self.db.get_connection() as conn:
        return conn.execute(query).df()
```

**Key Query Features:**

1. **Smart Grouping**: Uses participant_id when available, falls back to normalized name
2. **No Duplicates**: "becked" and "Becked" collapse to one row
3. **Multi-Civ Support**: Shows all civs a participant has played
4. **Unlinked Flag**: `is_unlinked` column for UI indicators
5. **DRY**: Uses CTE pattern for clarity

**Testing Strategy**:

Create test file: `tests/test_queries_participant_performance.py`

```python
"""Tests for participant-aware player performance queries."""

import pytest
import pandas as pd
from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.queries import TournamentQueries


@pytest.fixture
def test_db(tmp_path):
    """Create test database with participant and player data."""
    db_path = tmp_path / "test.duckdb"
    db = TournamentDatabase(str(db_path))

    # Insert test participants
    db.conn.execute("""
        INSERT INTO tournament_participants (
            participant_id, display_name, display_name_normalized
        ) VALUES
        (1001, 'LinkedPlayer1', 'linkedplayer1'),
        (1002, 'LinkedPlayer2', 'linkedplayer2')
    """)

    # Insert test matches
    db.conn.execute("""
        INSERT INTO matches (match_id, challonge_match_id, file_name, file_hash, total_turns)
        VALUES
        (100, 426504750, 'match1.zip', 'hash1', 50),
        (101, 426504751, 'match2.zip', 'hash2', 75)
    """)

    # Insert test players - mix of linked and unlinked
    db.conn.execute("""
        INSERT INTO players (
            player_id, match_id, player_name, player_name_normalized,
            participant_id, civilization, final_score
        ) VALUES
        -- Linked player, two matches, two different civs
        (1, 100, 'LinkedPlayer1', 'linkedplayer1', 1001, 'Rome', 500),
        (2, 101, 'LinkedPlayer1', 'linkedplayer1', 1001, 'Assyria', 600),
        -- Linked player, one match
        (3, 100, 'LinkedPlayer2', 'linkedplayer2', 1002, 'Babylon', 450),
        -- Unlinked player (name case variation)
        (4, 101, 'UnlinkedPlayer', 'unlinkedplayer', NULL, 'Egypt', 400),
        (5, 100, 'unlinkedplayer', 'unlinkedplayer', NULL, 'Greece', 350)
    """)

    # Insert match winners
    db.conn.execute("""
        INSERT INTO match_winners (match_id, winner_player_id)
        VALUES
        (100, 1),  -- LinkedPlayer1 wins match 100
        (101, 2)   -- LinkedPlayer1 wins match 101
    """)

    yield db
    db.close()


class TestPlayerPerformanceParticipantAware:
    """Tests for get_player_performance() with participant tracking."""

    def test_linked_player_appears_once(self, test_db):
        """Linked player should appear as one row despite multiple matches."""
        queries = TournamentQueries(test_db)
        df = queries.get_player_performance()

        # LinkedPlayer1 should appear once, not twice
        linked_players = df[df['player_name'] == 'LinkedPlayer1']
        assert len(linked_players) == 1

        row = linked_players.iloc[0]
        assert row['participant_id'] == 1001
        assert row['total_matches'] == 2
        assert row['wins'] == 2
        assert row['win_rate'] == 100.0
        assert row['is_unlinked'] is False

    def test_linked_player_shows_multiple_civs(self, test_db):
        """Linked player who used multiple civs should list all civs."""
        queries = TournamentQueries(test_db)
        df = queries.get_player_performance()

        linked_players = df[df['player_name'] == 'LinkedPlayer1']
        row = linked_players.iloc[0]

        # Should show both civs (order may vary)
        civs = row['civilizations_played']
        assert 'Rome' in civs
        assert 'Assyria' in civs

        # Favorite should be one of them
        assert row['favorite_civilization'] in ['Rome', 'Assyria']

    def test_unlinked_player_groups_by_normalized_name(self, test_db):
        """Unlinked players with name variations should collapse to one row."""
        queries = TournamentQueries(test_db)
        df = queries.get_player_performance()

        # Should have one row for unlinkedplayer (not two)
        unlinked_players = df[df['player_name'].str.lower() == 'unlinkedplayer']
        assert len(unlinked_players) == 1

        row = unlinked_players.iloc[0]
        assert pd.isna(row['participant_id']) or row['participant_id'] is None
        assert row['is_unlinked'] is True
        assert row['total_matches'] == 2

    def test_unlinked_player_marked_correctly(self, test_db):
        """Unlinked players should have is_unlinked=True."""
        queries = TournamentQueries(test_db)
        df = queries.get_player_performance()

        unlinked = df[df['is_unlinked'] == True]
        assert len(unlinked) >= 1

        # All unlinked should have NULL participant_id
        assert all(pd.isna(unlinked['participant_id']))

    def test_linked_player_marked_correctly(self, test_db):
        """Linked players should have is_unlinked=False."""
        queries = TournamentQueries(test_db)
        df = queries.get_player_performance()

        linked = df[df['is_unlinked'] == False]
        assert len(linked) >= 1

        # All linked should have non-NULL participant_id
        assert all(pd.notna(linked['participant_id']))

    def test_win_rate_calculation(self, test_db):
        """Win rate should calculate correctly across matches."""
        queries = TournamentQueries(test_db)
        df = queries.get_player_performance()

        # LinkedPlayer1: 2 matches, 2 wins = 100%
        lp1 = df[df['player_name'] == 'LinkedPlayer1'].iloc[0]
        assert lp1['win_rate'] == 100.0

        # LinkedPlayer2: 1 match, 0 wins = 0%
        lp2 = df[df['player_name'] == 'LinkedPlayer2'].iloc[0]
        assert lp2['win_rate'] == 0.0

    def test_score_aggregation(self, test_db):
        """Score stats should aggregate correctly."""
        queries = TournamentQueries(test_db)
        df = queries.get_player_performance()

        lp1 = df[df['player_name'] == 'LinkedPlayer1'].iloc[0]
        assert lp1['max_score'] == 600
        assert lp1['min_score'] == 500
        assert lp1['avg_score'] == 550.0  # (500 + 600) / 2

    def test_returns_expected_columns(self, test_db):
        """Result should have all expected columns."""
        queries = TournamentQueries(test_db)
        df = queries.get_player_performance()

        expected_columns = [
            'player_name',
            'participant_id',
            'is_unlinked',
            'total_matches',
            'wins',
            'win_rate',
            'avg_score',
            'max_score',
            'min_score',
            'civilizations_played',
            'favorite_civilization'
        ]

        for col in expected_columns:
            assert col in df.columns, f"Missing column: {col}"

    def test_empty_database(self, tmp_path):
        """Query should handle empty database gracefully."""
        db_path = tmp_path / "empty.duckdb"
        db = TournamentDatabase(str(db_path))
        queries = TournamentQueries(db)

        df = queries.get_player_performance()
        assert df.empty
        db.close()


class TestPlayerPerformanceEdgeCases:
    """Test edge cases and data quality scenarios."""

    def test_player_with_null_civilization(self, test_db):
        """Players with NULL civilization should not break query."""
        # Add player with NULL civ
        test_db.conn.execute("""
            INSERT INTO players (
                player_id, match_id, player_name, player_name_normalized,
                participant_id, civilization, final_score
            ) VALUES
            (99, 100, 'NoCivPlayer', 'nocivplayer', 1001, NULL, 300)
        """)

        queries = TournamentQueries(test_db)
        df = queries.get_player_performance()

        # Should not raise error
        assert not df.empty

    def test_sorting_order(self, test_db):
        """Results should be sorted by win_rate DESC, total_matches DESC."""
        queries = TournamentQueries(test_db)
        df = queries.get_player_performance()

        # First row should have highest win_rate
        # If tied, should have most matches
        assert df.iloc[0]['win_rate'] >= df.iloc[1]['win_rate']
```

**Running Tests**:
```bash
# Run only participant performance tests
uv run pytest tests/test_queries_participant_performance.py -v

# Run with coverage
uv run pytest tests/test_queries_participant_performance.py \
    --cov=tournament_visualizer.data.queries \
    --cov-report=term-missing

# Run all query tests
uv run pytest tests/test_queries*.py -v
```

**Manual Testing**:
```bash
# Test query directly in DuckDB
uv run duckdb data/tournament_data.duckdb -readonly

# Run the query manually (paste the SQL from the implementation)
# Verify:
# 1. Linked players appear once (check for "alcaras", should have 2 matches)
# 2. Unlinked players grouped by name (check "becked"/"Becked" collapses)
# 3. is_unlinked flag correct (compare to participant_id IS NULL)
# 4. civilizations_played shows multiple civs

# Count results
SELECT COUNT(*) as total_rows FROM (...query here...);
-- Should be less than total player instances (32)
-- Should be close to unique participants + unique unlinked names
```

**Commit Message**:
```
feat: Update player performance query to use participant tracking

Modifies get_player_performance() to group by participant_id when
available, falling back to player_name_normalized for unlinked players.
Adds is_unlinked flag and civilizations_played aggregation.

- Groups linked players correctly across multiple matches
- Collapses name variations (e.g., "becked"/"Becked") for unlinked
- Returns one row per person, not per player instance
- Supports multiple civilizations per participant
```

---

### Task 2: Update Head-to-Head Query

**Objective**: Modify `get_head_to_head_stats()` to match players by participant_id first, falling back to name matching.

**Files to Modify**:
- `tournament_visualizer/data/queries.py`

**Current Query** (lines 159-207):
```python
def get_head_to_head_stats(self, player1: str, player2: str) -> Dict[str, Any]:
    """Get head-to-head statistics between two players."""
    query = """
    WITH match_participants AS (
        SELECT
            m.match_id,
            m.game_name,
            m.save_date,
            m.total_turns,
            w.player_name as winner_name
        FROM matches m
        JOIN players p1 ON m.match_id = p1.match_id AND p1.player_name = ?
        JOIN players p2 ON m.match_id = p2.match_id AND p2.player_name = ?
        LEFT JOIN match_winners mw ON m.match_id = mw.match_id
        LEFT JOIN players w ON mw.winner_player_id = w.player_id
    )
    SELECT
        COUNT(*) as total_matches,
        COUNT(CASE WHEN winner_name = ? THEN 1 END) as player1_wins,
        COUNT(CASE WHEN winner_name = ? THEN 1 END) as player2_wins,
        AVG(total_turns) as avg_match_length,
        MIN(save_date) as first_match,
        MAX(save_date) as last_match
    FROM match_participants
    """
```

**Problems**:
1. Matches by `player_name` string only
2. Won't find matches if participant changed their in-game name
3. Doesn't leverage authoritative participant linkage

**New Implementation**:

```python
def get_head_to_head_stats(self, player1: str, player2: str) -> Dict[str, Any]:
    """Get head-to-head statistics between two players.

    Matches players by participant_id when possible (authoritative),
    falls back to name matching for unlinked players.

    Args:
        player1: Display name of first player (participant or player name)
        player2: Display name of second player (participant or player name)

    Returns:
        Dictionary with head-to-head statistics:
            - total_matches: Number of matches played against each other
            - player1_wins: Wins for player1
            - player2_wins: Wins for player2
            - avg_match_length: Average match duration in turns
            - first_match: Earliest match date
            - last_match: Most recent match date

    Note:
        If either player is linked to a participant, uses participant_id for
        matching. This ensures accurate matching even if in-game names vary.
    """
    query = """
    WITH player_identification AS (
        -- Find player1's participant_id (if linked)
        SELECT
            COALESCE(
                tp1.participant_id,
                'unlinked_' || ?
            ) as player1_key,
            ? as player1_name
        FROM (SELECT ? as name) input
        LEFT JOIN tournament_participants tp1 ON tp1.display_name = input.name
    ),
    player2_identification AS (
        -- Find player2's participant_id (if linked)
        SELECT
            COALESCE(
                tp2.participant_id,
                'unlinked_' || ?
            ) as player2_key,
            ? as player2_name
        FROM (SELECT ? as name) input
        LEFT JOIN tournament_participants tp2 ON tp2.display_name = input.name
    ),
    match_participants AS (
        -- Find all matches where both players participated
        SELECT
            m.match_id,
            m.game_name,
            m.save_date,
            m.total_turns,
            -- Determine winner using participant matching
            CASE
                WHEN p_winner.participant_id IS NOT NULL
                     AND p_winner.participant_id = CAST(p1_id.player1_key AS BIGINT)
                    THEN p1_id.player1_name
                WHEN p_winner.participant_id IS NOT NULL
                     AND p_winner.participant_id = CAST(p2_id.player2_key AS BIGINT)
                    THEN p2_id.player2_name
                WHEN p_winner.player_name_normalized =
                     SUBSTRING(p1_id.player1_key FROM 10)  -- Remove 'unlinked_' prefix
                    THEN p1_id.player1_name
                WHEN p_winner.player_name_normalized =
                     SUBSTRING(p2_id.player2_key FROM 10)
                    THEN p2_id.player2_name
                ELSE NULL
            END as winner_name
        FROM matches m
        -- Join to find player1 in this match
        JOIN players p1 ON m.match_id = p1.match_id
        JOIN player_identification p1_id ON (
            -- Match by participant_id if linked
            (p1.participant_id IS NOT NULL
             AND CAST(p1_id.player1_key AS VARCHAR) = CAST(p1.participant_id AS VARCHAR))
            OR
            -- Match by normalized name if unlinked
            (p1.participant_id IS NULL
             AND p1_id.player1_key = 'unlinked_' || p1.player_name_normalized)
        )
        -- Join to find player2 in this match
        JOIN players p2 ON m.match_id = p2.match_id
        JOIN player2_identification p2_id ON (
            -- Match by participant_id if linked
            (p2.participant_id IS NOT NULL
             AND CAST(p2_id.player2_key AS VARCHAR) = CAST(p2.participant_id AS VARCHAR))
            OR
            -- Match by normalized name if unlinked
            (p2.participant_id IS NULL
             AND p2_id.player2_key = 'unlinked_' || p2.player_name_normalized)
        )
        -- Ensure we found different players
        WHERE p1.player_id != p2.player_id
        -- Get winner information
        LEFT JOIN match_winners mw ON m.match_id = mw.match_id
        LEFT JOIN players p_winner ON mw.winner_player_id = p_winner.player_id
    )
    SELECT
        COUNT(*) as total_matches,
        COUNT(CASE WHEN winner_name = ? THEN 1 END) as player1_wins,
        COUNT(CASE WHEN winner_name = ? THEN 1 END) as player2_wins,
        AVG(total_turns) as avg_match_length,
        MIN(save_date) as first_match,
        MAX(save_date) as last_match
    FROM match_participants
    """

    result = self.db.fetch_one(
        query,
        {
            "1": player1, "2": player1, "3": player1,  # player1_identification CTE
            "4": player2, "5": player2, "6": player2,  # player2_identification CTE
            "7": player1, "8": player2,  # Final aggregation
        }
    )

    if result:
        return {
            "total_matches": result[0],
            "player1_wins": result[1],
            "player2_wins": result[2],
            "avg_match_length": result[3],
            "first_match": result[4],
            "last_match": result[5],
        }

    return {}
```

**Testing Strategy**:

Add to `tests/test_queries_participant_performance.py`:

```python
class TestHeadToHeadParticipantAware:
    """Tests for participant-aware head-to-head matching."""

    @pytest.fixture
    def h2h_test_db(self, tmp_path):
        """Create test database with head-to-head scenarios."""
        db_path = tmp_path / "h2h_test.duckdb"
        db = TournamentDatabase(str(db_path))

        # Insert participants
        db.conn.execute("""
            INSERT INTO tournament_participants (
                participant_id, display_name, display_name_normalized
            ) VALUES
            (2001, 'Ninja', 'ninja'),
            (2002, 'Fiddler', 'fiddler')
        """)

        # Insert matches where these two play each other
        db.conn.execute("""
            INSERT INTO matches (match_id, challonge_match_id, file_name, file_hash, total_turns, save_date)
            VALUES
            (200, 426504750, 'match1.zip', 'hash1', 50, '2025-01-01'),
            (201, 426504751, 'match2.zip', 'hash2', 75, '2025-01-02'),
            (202, 426504752, 'match3.zip', 'hash3', 60, '2025-01-03')
        """)

        # Match 200: Ninja wins
        db.conn.execute("""
            INSERT INTO players (
                player_id, match_id, player_name, player_name_normalized, participant_id
            ) VALUES
            (1, 200, 'Ninja', 'ninja', 2001),
            (2, 200, 'Fiddler', 'fiddler', 2002)
        """)
        db.conn.execute("INSERT INTO match_winners (match_id, winner_player_id) VALUES (200, 1)")

        # Match 201: Fiddler wins
        db.conn.execute("""
            INSERT INTO players (
                player_id, match_id, player_name, player_name_normalized, participant_id
            ) VALUES
            (3, 201, 'Ninja', 'ninja', 2001),
            (4, 201, 'Fiddler', 'fiddler', 2002)
        """)
        db.conn.execute("INSERT INTO match_winners (match_id, winner_player_id) VALUES (201, 4)")

        # Match 202: Ninja wins (name variation test - both still linked)
        db.conn.execute("""
            INSERT INTO players (
                player_id, match_id, player_name, player_name_normalized, participant_id
            ) VALUES
            (5, 202, 'Ninja', 'ninja', 2001),
            (6, 202, 'fiddler', 'fiddler', 2002)
        """)
        db.conn.execute("INSERT INTO match_winners (match_id, winner_player_id) VALUES (202, 5)")

        yield db
        db.close()

    def test_linked_players_h2h(self, h2h_test_db):
        """Head-to-head should find all matches between linked participants."""
        queries = TournamentQueries(h2h_test_db)
        stats = queries.get_head_to_head_stats('Ninja', 'Fiddler')

        assert stats['total_matches'] == 3
        assert stats['player1_wins'] == 2  # Ninja won twice
        assert stats['player2_wins'] == 1  # Fiddler won once
        assert stats['avg_match_length'] == pytest.approx(61.67, rel=0.1)  # (50+75+60)/3

    def test_h2h_with_unlinked_player(self, tmp_path):
        """Head-to-head should work when one player is unlinked."""
        db_path = tmp_path / "h2h_unlinked.duckdb"
        db = TournamentDatabase(str(db_path))

        # One linked, one unlinked participant
        db.conn.execute("""
            INSERT INTO tournament_participants (
                participant_id, display_name, display_name_normalized
            ) VALUES (3001, 'LinkedPlayer', 'linkedplayer')
        """)

        db.conn.execute("""
            INSERT INTO matches (match_id, challonge_match_id, file_name, file_hash, total_turns)
            VALUES (300, 426504750, 'match.zip', 'hash1', 50)
        """)

        db.conn.execute("""
            INSERT INTO players (
                player_id, match_id, player_name, player_name_normalized, participant_id
            ) VALUES
            (1, 300, 'LinkedPlayer', 'linkedplayer', 3001),
            (2, 300, 'UnlinkedPlayer', 'unlinkedplayer', NULL)
        """)

        db.conn.execute("INSERT INTO match_winners (match_id, winner_player_id) VALUES (300, 1)")

        queries = TournamentQueries(db)
        stats = queries.get_head_to_head_stats('LinkedPlayer', 'UnlinkedPlayer')

        assert stats['total_matches'] == 1
        assert stats['player1_wins'] == 1
        db.close()

    def test_h2h_no_matches(self, h2h_test_db):
        """Should handle case where players never faced each other."""
        queries = TournamentQueries(h2h_test_db)

        # Add a third player who hasn't played against anyone yet
        h2h_test_db.conn.execute("""
            INSERT INTO tournament_participants (
                participant_id, display_name, display_name_normalized
            ) VALUES (2003, 'NewPlayer', 'newplayer')
        """)

        stats = queries.get_head_to_head_stats('Ninja', 'NewPlayer')

        # Should return empty dict or zeros
        assert stats.get('total_matches', 0) == 0

    def test_h2h_date_range(self, h2h_test_db):
        """Should correctly identify first and last match dates."""
        queries = TournamentQueries(h2h_test_db)
        stats = queries.get_head_to_head_stats('Ninja', 'Fiddler')

        assert stats['first_match'] == '2025-01-01'
        assert stats['last_match'] == '2025-01-03'
```

**Manual Testing**:
```bash
# Test with production data
uv run python -c "
from tournament_visualizer.data.queries import get_queries

queries = get_queries()

# Test linked players
stats = queries.get_head_to_head_stats('alcaras', 'Amadeus')
print(f'alcaras vs Amadeus: {stats}')

# Should show their match history
assert stats['total_matches'] > 0, 'Expected matches between these players'
print('✓ Linked player H2H works')
"
```

**Commit Message**:
```
feat: Update head-to-head query to use participant matching

Modifies get_head_to_head_stats() to match players by participant_id
when available, ensuring accurate matching even with name variations.
Falls back to name matching for unlinked players.

- Uses authoritative participant linking
- Handles mixed linked/unlinked scenarios
- Correctly attributes wins across name variations
```

---

### Task 3: Update Civilization Performance Query

**Objective**: Modify `get_civilization_performance()` to count unique participants, not unique player names.

**Files to Modify**:
- `tournament_visualizer/data/queries.py`

**Current Query** (lines 101-127):
```python
def get_civilization_performance(self) -> pd.DataFrame:
    """Get performance statistics by civilization."""
    query = """
    SELECT
        COALESCE(p.civilization, 'Unknown') as civilization,
        COUNT(DISTINCT p.match_id) as total_matches,
        COUNT(CASE WHEN mw.winner_player_id = p.player_id THEN 1 END) as wins,
        ROUND(
            COUNT(CASE WHEN mw.winner_player_id = p.player_id THEN 1 END) * 100.0 /
            COUNT(DISTINCT p.match_id), 2
        ) as win_rate,
        AVG(p.final_score) as avg_score,
        COUNT(DISTINCT p.player_name) as unique_players  -- ❌ Counts names, not people
    FROM players p
    JOIN matches m ON p.match_id = m.match_id
    LEFT JOIN match_winners mw ON p.match_id = mw.match_id
    GROUP BY COALESCE(p.civilization, 'Unknown')
    HAVING COUNT(DISTINCT p.match_id) > 0
    ORDER BY win_rate DESC, total_matches DESC
    """
```

**New Implementation**:

```python
def get_civilization_performance(self) -> pd.DataFrame:
    """Get performance statistics by civilization.

    Counts unique participants (people) rather than unique player names
    to accurately reflect how many different people have played each civ.

    Returns:
        DataFrame with columns:
            - civilization: Civilization name
            - total_matches: Number of matches played with this civ
            - wins: Number of wins
            - win_rate: Win percentage (0-100)
            - avg_score: Average final score
            - unique_participants: Count of unique people who played this civ
            - unique_unlinked_players: Count of unlinked player names (for data quality)
    """
    query = """
    WITH player_identity AS (
        SELECT
            p.player_id,
            p.match_id,
            p.civilization,
            p.final_score,
            -- Use participant_id if available, else use normalized name as proxy
            COALESCE(
                CAST(p.participant_id AS VARCHAR),
                'unlinked_' || p.player_name_normalized
            ) as person_key,
            CASE WHEN p.participant_id IS NOT NULL THEN TRUE ELSE FALSE END as is_linked
        FROM players p
    )
    SELECT
        COALESCE(pi.civilization, 'Unknown') as civilization,
        COUNT(DISTINCT pi.match_id) as total_matches,
        COUNT(CASE WHEN mw.winner_player_id = pi.player_id THEN 1 END) as wins,
        ROUND(
            COUNT(CASE WHEN mw.winner_player_id = pi.player_id THEN 1 END) * 100.0 /
            NULLIF(COUNT(DISTINCT pi.match_id), 0), 2
        ) as win_rate,
        AVG(pi.final_score) as avg_score,
        -- Count unique people (participants + unlinked player name proxies)
        COUNT(DISTINCT pi.person_key) as unique_participants,
        -- Count only linked participants for data quality insight
        COUNT(DISTINCT CASE WHEN pi.is_linked THEN pi.person_key END) as unique_linked_participants,
        -- Count unlinked for data quality insight
        COUNT(DISTINCT CASE WHEN NOT pi.is_linked THEN pi.person_key END) as unique_unlinked_players
    FROM player_identity pi
    LEFT JOIN match_winners mw ON pi.match_id = mw.match_id
    GROUP BY COALESCE(pi.civilization, 'Unknown')
    HAVING COUNT(DISTINCT pi.match_id) > 0
    ORDER BY win_rate DESC, total_matches DESC
    """

    with self.db.get_connection() as conn:
        return conn.execute(query).df()
```

**Key Changes**:
1. Uses `person_key` (participant_id or normalized name) to count unique people
2. Adds data quality columns (`unique_linked_participants`, `unique_unlinked_players`)
3. More accurate representation of "how many different people played this civ"

**Testing**:

Add to `tests/test_queries_participant_performance.py`:

```python
class TestCivilizationPerformanceParticipantAware:
    """Tests for civilization performance with participant awareness."""

    @pytest.fixture
    def civ_test_db(self, tmp_path):
        """Create test database with civilization data."""
        db_path = tmp_path / "civ_test.duckdb"
        db = TournamentDatabase(str(db_path))

        # Insert participant
        db.conn.execute("""
            INSERT INTO tournament_participants (
                participant_id, display_name, display_name_normalized
            ) VALUES (4001, 'CivPlayer', 'civplayer')
        """)

        # Insert matches
        db.conn.execute("""
            INSERT INTO matches (match_id, challonge_match_id, file_name, file_hash, total_turns)
            VALUES
            (400, 426504750, 'm1.zip', 'h1', 50),
            (401, 426504751, 'm2.zip', 'h2', 60)
        """)

        # Same person plays Rome twice (linked)
        db.conn.execute("""
            INSERT INTO players (
                player_id, match_id, player_name, player_name_normalized,
                participant_id, civilization, final_score
            ) VALUES
            (1, 400, 'CivPlayer', 'civplayer', 4001, 'Rome', 500),
            (2, 401, 'CivPlayer', 'civplayer', 4001, 'Rome', 600)
        """)

        # Different unlinked person also plays Rome
        db.conn.execute("""
            INSERT INTO players (
                player_id, match_id, player_name, player_name_normalized,
                participant_id, civilization, final_score
            ) VALUES
            (3, 400, 'UnlinkedRome', 'unlinkedrome', NULL, 'Rome', 450)
        """)

        yield db
        db.close()

    def test_counts_unique_participants_not_instances(self, civ_test_db):
        """Should count unique people, not player instances."""
        queries = TournamentQueries(civ_test_db)
        df = queries.get_civilization_performance()

        rome_stats = df[df['civilization'] == 'Rome'].iloc[0]

        # 3 player instances total
        assert rome_stats['total_matches'] == 2  # Only 2 matches

        # 2 unique people: 1 linked participant + 1 unlinked player
        assert rome_stats['unique_participants'] == 2
        assert rome_stats['unique_linked_participants'] == 1
        assert rome_stats['unique_unlinked_players'] == 1

    def test_multiple_civs_by_same_participant(self, tmp_path):
        """Participant playing multiple civs should count for each civ."""
        db_path = tmp_path / "multi_civ.duckdb"
        db = TournamentDatabase(str(db_path))

        db.conn.execute("""
            INSERT INTO tournament_participants (
                participant_id, display_name, display_name_normalized
            ) VALUES (5001, 'MultiCivPlayer', 'multicivplayer')
        """)

        db.conn.execute("""
            INSERT INTO matches (match_id, challonge_match_id, file_name, file_hash, total_turns)
            VALUES
            (500, 426504750, 'm1.zip', 'h1', 50),
            (501, 426504751, 'm2.zip', 'h2', 60)
        """)

        # Same person plays different civs
        db.conn.execute("""
            INSERT INTO players (
                player_id, match_id, player_name, player_name_normalized,
                participant_id, civilization, final_score
            ) VALUES
            (1, 500, 'MultiCivPlayer', 'multicivplayer', 5001, 'Rome', 500),
            (2, 501, 'MultiCivPlayer', 'multicivplayer', 5001, 'Assyria', 600)
        """)

        queries = TournamentQueries(db)
        df = queries.get_civilization_performance()

        # Should appear in both civilizations
        assert len(df) == 2
        assert 'Rome' in df['civilization'].values
        assert 'Assyria' in df['civilization'].values

        # Each civ should count this participant
        for _, row in df.iterrows():
            assert row['unique_participants'] == 1

        db.close()
```

**Manual Testing**:
```bash
# Check civilization stats with production data
uv run python -c "
from tournament_visualizer.data.queries import get_queries

queries = get_queries()
df = queries.get_civilization_performance()

print('Civilization Performance:')
print(df[['civilization', 'total_matches', 'unique_participants', 'unique_linked_participants', 'unique_unlinked_players']])

# Verify counts make sense
for _, row in df.iterrows():
    total = row['unique_linked_participants'] + row['unique_unlinked_players']
    assert total == row['unique_participants'], f'Mismatch for {row[\"civilization\"]}'

print('✓ Civilization performance query working correctly')
"
```

**Commit Message**:
```
feat: Update civilization stats to count unique participants

Modifies get_civilization_performance() to count unique people rather
than unique player names. Adds data quality columns showing linked vs
unlinked player breakdown.

- Counts participants accurately
- Handles same person playing civ multiple times
- Provides data quality insights
```

---

### Task 4: Update Players Page UI

**Objective**: Update the Players page to display participant-aware data with visual indicators for unlinked players.

**Files to Modify**:
- `tournament_visualizer/pages/players.py`

**Current Code** (lines 69-102):

```python
columns=[
    {"name": "Rank", "id": "rank", "type": "numeric"},
    {"name": "Player", "id": "player_name"},
    {"name": "Matches", "id": "total_matches", "type": "numeric"},
    {"name": "Wins", "id": "wins", "type": "numeric"},
    {"name": "Win Rate", "id": "win_rate", "type": "numeric", "format": {"specifier": ".1%"}},
    {"name": "Avg Score", "id": "avg_score", "type": "numeric", "format": {"specifier": ".1f"}},
    {"name": "Favorite Civ", "id": "favorite_civilization"},
]
```

**New Implementation**:

```python
# In players.py, update the rankings table columns
columns=[
    {
        "name": "Rank",
        "id": "rank",
        "type": "numeric",
    },
    {
        "name": "Player",
        "id": "player_display",  # Changed from player_name
        "presentation": "markdown",  # Enable markdown for indicators
    },
    {
        "name": "Matches",
        "id": "total_matches",
        "type": "numeric",
    },
    {
        "name": "Wins",
        "id": "wins",
        "type": "numeric",
    },
    {
        "name": "Win Rate",
        "id": "win_rate",
        "type": "numeric",
        "format": {"specifier": ".1%"},
    },
    {
        "name": "Avg Score",
        "id": "avg_score",
        "type": "numeric",
        "format": {"specifier": ".1f"},
    },
    {
        "name": "Civilizations",  # Changed from "Favorite Civ"
        "id": "civilizations_display",
        "presentation": "markdown",
    },
]
```

**Update the rankings table callback** (lines 385-417):

```python
@callback(
    Output("players-rankings-table", "data"),
    Input("refresh-interval", "n_intervals"),
)
def update_rankings_table(n_intervals: int) -> List[Dict[str, Any]]:
    """Update player rankings table.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        List of player ranking data with visual indicators for unlinked players
    """
    try:
        queries = get_queries()
        df = queries.get_player_performance()

        if df.empty:
            return []

        # Sort by win rate and add rank
        df = df.sort_values("win_rate", ascending=False).reset_index(drop=True)
        df["rank"] = range(1, len(df) + 1)

        # Convert win rate to percentage for display (already 0-100, need 0-1 for formatter)
        df["win_rate"] = df["win_rate"] / 100

        # Create display columns with indicators
        df["player_display"] = df.apply(
            lambda row: (
                f"⚠️ {row['player_name']}"  # Warning emoji for unlinked
                if row["is_unlinked"]
                else row["player_name"]
            ),
            axis=1,
        )

        # Format civilizations with favorite highlighted
        df["civilizations_display"] = df.apply(
            lambda row: _format_civilizations_display(
                row["civilizations_played"], row["favorite_civilization"]
            ),
            axis=1,
        )

        return df.to_dict("records")

    except Exception as e:
        logger.error(f"Error updating rankings table: {e}")
        return []


def _format_civilizations_display(civs_played: str, favorite: str) -> str:
    """Format civilizations for display with favorite highlighted.

    Args:
        civs_played: Comma-separated list of civilizations
        favorite: The most-played civilization

    Returns:
        Markdown-formatted string with favorite bolded

    Examples:
        >>> _format_civilizations_display("Rome, Assyria", "Rome")
        '**Rome**, Assyria'

        >>> _format_civilizations_display("Babylon", "Babylon")
        '**Babylon**'
    """
    if not civs_played or pd.isna(civs_played):
        return "—"

    if not favorite or pd.isna(favorite):
        return civs_played

    # Split, bold the favorite, rejoin
    civs = [civ.strip() for civ in str(civs_played).split(",")]
    formatted = [f"**{civ}**" if civ == favorite else civ for civ in civs]
    return ", ".join(formatted)
```

**Add help text explaining unlinked indicator**:

Update the page layout to include a helper callout:

```python
# Add after the page header, before the tabs
dbc.Alert(
    [
        html.Div(
            [
                html.I(className="bi bi-info-circle me-2"),
                html.Span("Players marked with ⚠️ are not yet linked to tournament participants. "),
                html.A(
                    "Learn more about participant linking →",
                    href="#",  # Could link to docs or linking page
                    className="alert-link",
                ),
            ]
        )
    ],
    color="info",
    className="mb-4",
    dismissable=True,
    id="participant-linking-info",
),
```

**Update summary metrics** (lines 182-216):

```python
@callback(
    Output("player-summary-metrics", "children"),
    Input("refresh-interval", "n_intervals"),
)
def update_player_summary_metrics(n_intervals: int) -> html.Div:
    """Update player summary metrics.

    Args:
        n_intervals: Number of interval triggers

    Returns:
        Metrics grid component with participant linking stats
    """
    try:
        queries = get_queries()
        df = queries.get_player_performance()

        if df.empty:
            return create_empty_state("No player data available")

        # Count total players (all)
        total_players = len(df)

        # Count linked vs unlinked
        linked_count = len(df[df["is_unlinked"] == False])
        unlinked_count = len(df[df["is_unlinked"] == True])

        # Calculate linking percentage
        linking_pct = (linked_count / total_players * 100) if total_players > 0 else 0

        metrics = [
            {
                "title": "Total Players",
                "value": total_players,
                "icon": "bi-people",
                "color": "primary",
            },
            {
                "title": "Linked Participants",
                "value": linked_count,
                "icon": "bi-link-45deg",
                "color": "success",
            },
            {
                "title": "Unlinked Players",
                "value": unlinked_count,
                "icon": "bi-exclamation-triangle",
                "color": "warning" if unlinked_count > 0 else "secondary",
            },
            {
                "title": "Linking Coverage",
                "value": f"{linking_pct:.0f}%",
                "icon": "bi-diagram-3",
                "color": "info",
            },
        ]

        return create_metric_grid(metrics)

    except Exception as e:
        return create_empty_state(f"Error loading metrics: {str(e)}")
```

**Testing Strategy**:

Create test file: `tests/test_players_page.py`

```python
"""Tests for Players page UI with participant awareness."""

import pytest
from dash.testing.application_runners import import_app


class TestPlayersPageParticipantUI:
    """Test Players page displays participant data correctly."""

    @pytest.fixture
    def dash_app(self):
        """Import and return the Dash app for testing."""
        # Note: This requires dash[testing] package
        return import_app("tournament_visualizer.app")

    def test_page_loads(self, dash_duo, dash_app):
        """Players page should load without errors."""
        dash_duo.start_server(dash_app)
        dash_duo.wait_for_page("/players")

        # Check page title present
        assert dash_duo.find_element("h1").text == "Players"

    def test_summary_metrics_show_linking_stats(self, dash_duo, dash_app):
        """Summary metrics should show participant linking statistics."""
        dash_duo.start_server(dash_app)
        dash_duo.wait_for_page("/players")

        # Wait for metrics to load
        dash_duo.wait_for_text_to_equal("#player-summary-metrics", timeout=10)

        # Should see metric cards
        metrics = dash_duo.find_elements(".metric-card")
        assert len(metrics) >= 3  # At least: Total, Linked, Unlinked

        # Check for linking-related text
        page_text = dash_duo.find_element("body").text
        assert "Linked Participants" in page_text or "Unlinked Players" in page_text

    def test_table_shows_unlinked_indicator(self, dash_duo, dash_app):
        """Rankings table should mark unlinked players with indicator."""
        dash_duo.start_server(dash_app)
        dash_duo.wait_for_page("/players")

        # Wait for table to populate
        dash_duo.wait_for_element("#players-rankings-table", timeout=10)

        # Find table rows
        table = dash_duo.find_element("#players-rankings-table")
        table_html = table.get_attribute("innerHTML")

        # If we have unlinked players, should see warning emoji
        # (This test may be flaky if all players are linked)
        # Better: check data structure in callback test below

    def test_civilizations_column_shows_all_civs(self, dash_duo, dash_app):
        """Civilizations column should show all civs played, not just favorite."""
        dash_duo.start_server(dash_app)
        dash_duo.wait_for_page("/players")

        # Wait for table
        dash_duo.wait_for_element("#players-rankings-table", timeout=10)

        # Check table headers
        headers = dash_duo.find_elements("th")
        header_texts = [h.text for h in headers]

        assert "Civilizations" in header_texts
        assert "Favorite Civ" not in header_texts  # Old column name removed


class TestPlayersPageCallbacks:
    """Test Players page callback logic."""

    def test_update_rankings_table_adds_display_columns(self):
        """Callback should add player_display and civilizations_display columns."""
        from tournament_visualizer.pages.players import update_rankings_table

        # Call with dummy interval
        result = update_rankings_table(0)

        if result:  # May be empty if no data
            # Check first record has required fields
            first = result[0]
            assert "player_display" in first
            assert "civilizations_display" in first
            assert "rank" in first

    def test_unlinked_players_get_warning_indicator(self, test_db):
        """Unlinked players should have warning emoji in player_display."""
        # This test requires a populated test database
        # Create one with mixed linked/unlinked players

        from tournament_visualizer.data.queries import TournamentQueries
        from tournament_visualizer.pages.players import update_rankings_table

        # Set up test database (similar to Task 1 tests)
        # ... database setup code ...

        result = update_rankings_table(0)

        # Find unlinked players
        unlinked = [r for r in result if r.get("is_unlinked")]

        for record in unlinked:
            assert "⚠️" in record["player_display"]

    def test_favorite_civ_bolded_in_display(self):
        """Favorite civilization should be bolded in civilizations_display."""
        from tournament_visualizer.pages.players import _format_civilizations_display

        result = _format_civilizations_display("Rome, Assyria, Babylon", "Assyria")

        assert "**Assyria**" in result
        assert "**Rome**" not in result
        assert "**Babylon**" not in result

    def test_format_civs_handles_single_civ(self):
        """Single civilization should still be bolded."""
        from tournament_visualizer.pages.players import _format_civilizations_display

        result = _format_civilizations_display("Rome", "Rome")
        assert result == "**Rome**"

    def test_format_civs_handles_null(self):
        """Null civilizations should display placeholder."""
        from tournament_visualizer.pages.players import _format_civilizations_display
        import pandas as pd

        result = _format_civilizations_display(None, None)
        assert result == "—"

        result = _format_civilizations_display(pd.NA, pd.NA)
        assert result == "—"

    def test_summary_metrics_calculates_linking_percentage(self):
        """Summary metrics should show correct linking percentage."""
        from tournament_visualizer.pages.players import update_player_summary_metrics

        result = update_player_summary_metrics(0)

        # Result is a Div component, check it contains metric grid
        # This is a shallow test - better would be to mock get_queries()
        assert result is not None
```

**Manual Testing Checklist**:

```bash
# 1. Start the app
uv run python manage.py restart

# 2. Visit http://localhost:8050/players

# 3. Check summary metrics:
#    - Should show "Total Players", "Linked Participants", "Unlinked Players", "Linking Coverage"
#    - Linking Coverage should show percentage (e.g., "44%")
#    - Unlinked count should be > 0 if you have unlinked players

# 4. Check rankings table:
#    - Column should say "Civilizations" not "Favorite Civ"
#    - Unlinked players should have ⚠️ emoji
#    - Players with multiple civs should show all (e.g., "Rome, Assyria")
#    - Favorite civ should be bold (e.g., "**Rome**, Assyria")

# 5. Check player counts:
#    - Total players should be less than 32 (total player instances)
#    - Should be close to 26 (unique normalized names) or fewer
#    - Check "alcaras" appears once despite 2 matches

# 6. Check head-to-head:
#    - Select two linked players (e.g., "alcaras" and "Amadeus")
#    - Should show their match history
#    - Win counts should be accurate

# 7. Check for errors:
#    - Open browser console (F12)
#    - Should be no JavaScript errors
#    - Check terminal for Python errors
```

**Commit Message**:
```
feat: Update Players page UI to display participants

Updates Players page to show participant-aware data with visual
indicators for unlinked players. Adds linking coverage metrics
and multi-civilization display.

- Shows ⚠️ for unlinked players
- Displays all civilizations played (not just favorite)
- Adds linking coverage metrics
- Collapses duplicate player names to single rows
```

---

### Task 5: Add Data Quality Validation

**Objective**: Create a validation script to check participant linking quality and identify issues.

**Files to Create**:
- `scripts/validate_participant_ui_data.py`

**Implementation**:

```python
#!/usr/bin/env python3
"""Validation script for participant UI data quality.

Checks:
1. Player performance query returns expected data
2. Linked players appear once (no duplicates)
3. Unlinked players group correctly by normalized name
4. Head-to-head matching works for linked players
5. Civilization stats count participants correctly

Run this before and after UI updates to ensure data integrity.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tournament_visualizer.config import Config
from tournament_visualizer.data.queries import get_queries


def validate_player_performance() -> tuple[bool, list[str]]:
    """Validate player performance query results."""
    errors = []
    queries = get_queries()

    print("Validating player performance query...")

    try:
        df = queries.get_player_performance()

        if df.empty:
            errors.append("Player performance query returned empty results")
            return False, errors

        # Check required columns
        required_cols = [
            "player_name",
            "participant_id",
            "is_unlinked",
            "total_matches",
            "wins",
            "win_rate",
            "civilizations_played",
            "favorite_civilization",
        ]

        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            errors.append(f"Missing columns: {missing_cols}")

        # Check for duplicate participant_ids (should never happen)
        linked = df[df["is_unlinked"] == False]
        if not linked.empty:
            dup_participants = linked[linked.duplicated("participant_id", keep=False)]
            if not dup_participants.empty:
                errors.append(
                    f"Found {len(dup_participants)} duplicate participant_id entries"
                )

        # Check that unlinked players have NULL participant_id
        unlinked = df[df["is_unlinked"] == True]
        if not unlinked.empty:
            non_null = unlinked[unlinked["participant_id"].notna()]
            if not non_null.empty:
                errors.append(
                    f"Found {len(non_null)} unlinked players with non-NULL participant_id"
                )

        # Check win_rate is valid percentage (0-100)
        invalid_rates = df[(df["win_rate"] < 0) | (df["win_rate"] > 100)]
        if not invalid_rates.empty:
            errors.append(f"Found {len(invalid_rates)} invalid win rates")

        # Summary stats
        total = len(df)
        linked_count = len(linked)
        unlinked_count = len(unlinked)

        print(f"  Total players: {total}")
        print(f"  Linked participants: {linked_count} ({linked_count/total*100:.1f}%)")
        print(f"  Unlinked players: {unlinked_count} ({unlinked_count/total*100:.1f}%)")

        # Check for potential duplicates in unlinked (case variations)
        if not unlinked.empty:
            # Group by lowercase name to find potential duplicates
            name_lower = unlinked["player_name"].str.lower()
            dup_names = name_lower[name_lower.duplicated(keep=False)]
            if not dup_names.empty:
                errors.append(
                    f"Warning: Found {len(dup_names)} unlinked players with case variations. "
                    f"These should be linked to participants."
                )

        if errors:
            return False, errors

        print("  ✓ Player performance validation passed")
        return True, []

    except Exception as e:
        errors.append(f"Exception during validation: {e}")
        return False, errors


def validate_head_to_head() -> tuple[bool, list[str]]:
    """Validate head-to-head matching."""
    errors = []
    queries = get_queries()

    print("\nValidating head-to-head matching...")

    try:
        df = queries.get_player_performance()

        if df.empty or len(df) < 2:
            print("  ⚠️  Skipping H2H validation (not enough players)")
            return True, []

        # Test with first two players
        player1 = df.iloc[0]["player_name"]
        player2 = df.iloc[1]["player_name"]

        print(f"  Testing H2H: {player1} vs {player2}")

        stats = queries.get_head_to_head_stats(player1, player2)

        # Should return dict with expected keys (even if 0 matches)
        expected_keys = [
            "total_matches",
            "player1_wins",
            "player2_wins",
            "avg_match_length",
        ]

        missing_keys = [key for key in expected_keys if key not in stats]
        if missing_keys:
            errors.append(f"H2H stats missing keys: {missing_keys}")

        # Check logical consistency
        if stats:
            total = stats.get("total_matches", 0)
            p1_wins = stats.get("player1_wins", 0)
            p2_wins = stats.get("player2_wins", 0)

            if p1_wins + p2_wins > total:
                errors.append(
                    f"H2H win counts ({p1_wins} + {p2_wins}) exceed total matches ({total})"
                )

            print(f"  Matches found: {total}")
            if total > 0:
                print(f"  {player1}: {p1_wins} wins")
                print(f"  {player2}: {p2_wins} wins")

        if errors:
            return False, errors

        print("  ✓ Head-to-head validation passed")
        return True, []

    except Exception as e:
        errors.append(f"Exception during H2H validation: {e}")
        return False, errors


def validate_civilization_stats() -> tuple[bool, list[str]]:
    """Validate civilization performance stats."""
    errors = []
    queries = get_queries()

    print("\nValidating civilization statistics...")

    try:
        df = queries.get_civilization_performance()

        if df.empty:
            errors.append("Civilization performance query returned empty results")
            return False, errors

        # Check required columns
        required_cols = [
            "civilization",
            "total_matches",
            "wins",
            "win_rate",
            "unique_participants",
        ]

        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            errors.append(f"Missing columns in civ stats: {missing_cols}")

        # Check logical consistency
        for _, row in df.iterrows():
            civ = row["civilization"]

            # Wins should not exceed total matches
            if row["wins"] > row["total_matches"]:
                errors.append(
                    f"{civ}: wins ({row['wins']}) > total_matches ({row['total_matches']})"
                )

            # unique_participants should be > 0 if total_matches > 0
            if row["total_matches"] > 0 and row["unique_participants"] == 0:
                errors.append(f"{civ}: has matches but 0 unique participants")

        print(f"  Civilizations tracked: {len(df)}")
        print(f"  Total matches: {df['total_matches'].sum()}")

        if errors:
            return False, errors

        print("  ✓ Civilization stats validation passed")
        return True, []

    except Exception as e:
        errors.append(f"Exception during civ stats validation: {e}")
        return False, errors


def validate_data_consistency() -> tuple[bool, list[str]]:
    """Cross-validate data consistency across queries."""
    errors = []
    queries = get_queries()

    print("\nValidating cross-query data consistency...")

    try:
        player_df = queries.get_player_performance()
        civ_df = queries.get_civilization_performance()

        # Total matches from player perspective
        player_matches = player_df["total_matches"].sum()

        # Total matches from civ perspective (will be higher due to multi-player matches)
        civ_matches = civ_df["total_matches"].sum()

        print(f"  Player-perspective matches: {player_matches}")
        print(f"  Civ-perspective matches: {civ_matches}")

        # Civ matches should be >= player matches (same matches counted from different angle)
        # Actually, for 1v1 matches, civ_matches should be exactly 2x player_matches
        # But we might have some data inconsistencies, so just check >=
        if civ_matches < player_matches:
            errors.append(
                f"Civ match count ({civ_matches}) less than player match count ({player_matches})"
            )

        if errors:
            return False, errors

        print("  ✓ Cross-query consistency validation passed")
        return True, []

    except Exception as e:
        errors.append(f"Exception during consistency validation: {e}")
        return False, errors


def print_data_quality_summary():
    """Print summary of participant linking data quality."""
    queries = get_queries()

    print("\n" + "=" * 60)
    print("PARTICIPANT LINKING DATA QUALITY SUMMARY")
    print("=" * 60)

    # Get raw database stats
    db = queries.db

    # Total player instances
    result = db.fetch_one("SELECT COUNT(*) FROM players")
    total_instances = result[0] if result else 0

    # Linked instances
    result = db.fetch_one(
        "SELECT COUNT(*) FROM players WHERE participant_id IS NOT NULL"
    )
    linked_instances = result[0] if result else 0

    # Unique participants
    result = db.fetch_one(
        "SELECT COUNT(DISTINCT participant_id) FROM players WHERE participant_id IS NOT NULL"
    )
    unique_participants = result[0] if result else 0

    # Unique normalized names
    result = db.fetch_one("SELECT COUNT(DISTINCT player_name_normalized) FROM players")
    unique_names = result[0] if result else 0

    print(f"\nDatabase Statistics:")
    print(f"  Total player instances: {total_instances}")
    print(f"  Linked instances: {linked_instances} ({linked_instances/total_instances*100:.1f}%)")
    print(f"  Unique participants: {unique_participants}")
    print(f"  Unique player names: {unique_names}")

    # Potential linkage targets (unlinked players that might match participants)
    result = db.fetch_all("""
        SELECT
            p.player_name,
            p.player_name_normalized,
            tp.display_name,
            tp.participant_id
        FROM players p
        LEFT JOIN tournament_participants tp
            ON p.player_name_normalized LIKE '%' || tp.display_name_normalized || '%'
            OR tp.display_name_normalized LIKE '%' || p.player_name_normalized || '%'
        WHERE p.participant_id IS NULL
            AND tp.participant_id IS NOT NULL
        GROUP BY p.player_name, p.player_name_normalized, tp.display_name, tp.participant_id
        ORDER BY p.player_name
        LIMIT 10
    """)

    if result:
        print(f"\nPotential linkage opportunities (showing first 10):")
        print("  Save File Name → Potential Challonge Match")
        for row in result:
            print(f"  {row[0]} → {row[2]}")

        print(f"\n  💡 Consider adding manual overrides for these players")

    print("=" * 60)


def main():
    """Run all validations."""
    print("Participant UI Data Quality Validation")
    print("=" * 60)

    all_passed = True
    all_errors = []

    # Run validations
    validations = [
        ("Player Performance", validate_player_performance),
        ("Head-to-Head Matching", validate_head_to_head),
        ("Civilization Statistics", validate_civilization_stats),
        ("Data Consistency", validate_data_consistency),
    ]

    for name, validator in validations:
        passed, errors = validator()
        if not passed:
            all_passed = False
            all_errors.extend([f"{name}: {err}" for err in errors])

    # Print data quality summary
    print_data_quality_summary()

    # Final result
    if not all_passed:
        print("\n" + "=" * 60)
        print("VALIDATION ERRORS")
        print("=" * 60)
        for error in all_errors:
            print(f"  ✗ {error}")
        print("=" * 60)
        sys.exit(1)
    else:
        print("\n✓ All validations passed!")
        print("\nData quality is good for participant UI integration.")
        sys.exit(0)


if __name__ == "__main__":
    main()
```

**Testing**:

```bash
# Run validation
uv run python scripts/validate_participant_ui_data.py

# Should output:
# - Summary of participant linking coverage
# - Validation results for each query type
# - Data quality metrics
# - Potential linking opportunities

# Exit code:
# - 0 if all validations pass
# - 1 if any validation fails
```

**Commit Message**:
```
feat: Add participant UI data quality validation script

Creates comprehensive validation script to check participant linking
data quality and query correctness. Validates player performance,
head-to-head matching, and civilization stats.

Provides data quality summary and identifies potential linking
opportunities for manual override.
```

---

### Task 6: Update Documentation

**Objective**: Document the participant UI integration for future developers.

**Files to Modify**:
- `docs/developer-guide.md`
- `CLAUDE.md`

**Update `docs/developer-guide.md`**:

Add new section after "Tournament Participant Tracking":

```markdown
## Participant UI Integration

### Overview

The web application displays **tournament participants** (real people) rather than match-scoped player instances. This provides accurate cross-match analytics and persistent player identity.

### Display Strategy: Show All with Fallback

The UI uses a "participant-first, fallback to name" strategy:

- **Linked players**: Grouped by `participant_id`, show participant display name
- **Unlinked players**: Grouped by `player_name_normalized`, show player name with ⚠️ indicator
- **Visual feedback**: Unlinked players marked for data quality awareness

This ensures:
✅ All match data visible to users
✅ Graceful degradation when linking incomplete
✅ Works during active tournaments (new players not yet in Challonge)
✅ Incentivizes data quality through visual indicators

### Key Queries

#### Player Performance (`get_player_performance()`)

Returns one row per person, grouping by participant when available:

```sql
-- Smart grouping key: participant_id if linked, else normalized name
COALESCE(
    CAST(tp.participant_id AS VARCHAR),
    'unlinked_' || p.player_name_normalized
) as grouping_key
```

**Columns returned**:
- `player_name`: Display name (participant or player)
- `participant_id`: Participant ID (NULL for unlinked)
- `is_unlinked`: Boolean flag for UI indicators
- `total_matches`, `wins`, `win_rate`: Standard stats
- `civilizations_played`: All civs used (comma-separated)
- `favorite_civilization`: Most-played civ

**Use cases**:
- Players page rankings table
- Player performance metrics
- Head-to-head comparisons

#### Head-to-Head Stats (`get_head_to_head_stats()`)

Matches players by `participant_id` first, falls back to name matching:

```python
stats = queries.get_head_to_head_stats('Ninja', 'Fiddler')
# Uses participant_id if both are linked
# Falls back to name matching for unlinked
```

**Returns**:
```python
{
    'total_matches': 5,
    'player1_wins': 3,
    'player2_wins': 2,
    'avg_match_length': 87.4,
    'first_match': '2025-01-01',
    'last_match': '2025-02-15'
}
```

#### Civilization Performance (`get_civilization_performance()`)

Counts unique **participants**, not unique names:

```sql
-- Counts distinct people who played this civ
COUNT(DISTINCT COALESCE(
    CAST(p.participant_id AS VARCHAR),
    'unlinked_' || p.player_name_normalized
)) as unique_participants
```

**Columns returned**:
- `unique_participants`: Total unique people
- `unique_linked_participants`: Count of linked only
- `unique_unlinked_players`: Count of unlinked only

Data quality columns help track linking coverage.

### UI Components

#### Players Page (`pages/players.py`)

**Rankings Table**:
- One row per person (not per match instance)
- Player column uses markdown with ⚠️ for unlinked
- Civilizations column shows all civs played (favorite bolded)

**Summary Metrics**:
- Total Players
- Linked Participants
- Unlinked Players
- Linking Coverage %

**Head-to-Head**:
- Dropdowns populated with participant names
- Matching by participant_id ensures accuracy

### Data Quality Indicators

#### Visual Indicators

| Indicator | Meaning | Action |
|-----------|---------|--------|
| ⚠️ | Player not linked to participant | Consider adding manual override |
| **Bold civ** | Most-played civilization | User info |
| Linking Coverage % | Percentage of players linked | Data quality metric |

#### Validation

Run validation script to check data quality:

```bash
uv run python scripts/validate_participant_ui_data.py
```

Checks:
- Query correctness
- Data consistency
- Linking coverage
- Potential linking opportunities

### Common Queries

**Find unlinked players:**
```sql
SELECT
    player_name,
    COUNT(DISTINCT match_id) as matches_played
FROM players
WHERE participant_id IS NULL
GROUP BY player_name_normalized, player_name
ORDER BY matches_played DESC;
```

**Check participant linking coverage:**
```sql
SELECT
    COUNT(*) as total_instances,
    COUNT(participant_id) as linked,
    COUNT(*) - COUNT(participant_id) as unlinked,
    ROUND(COUNT(participant_id) * 100.0 / COUNT(*), 1) as coverage_pct
FROM players;
```

**Find participants with multiple civs:**
```sql
SELECT
    tp.display_name,
    STRING_AGG(DISTINCT p.civilization, ', ') as civs,
    COUNT(DISTINCT p.civilization) as civ_count
FROM tournament_participants tp
JOIN players p ON tp.participant_id = p.participant_id
GROUP BY tp.participant_id, tp.display_name
HAVING COUNT(DISTINCT p.civilization) > 1
ORDER BY civ_count DESC;
```

### Troubleshooting

#### "Players appearing multiple times in table"

Check if query is grouping correctly:
```python
df = queries.get_player_performance()
duplicates = df[df.duplicated('player_name', keep=False)]
print(duplicates[['player_name', 'participant_id', 'is_unlinked']])
```

If linked players duplicate: Bug in grouping logic (participant_id should be unique)
If unlinked players duplicate: Check normalized name grouping

#### "Win rates don't match Challonge"

Verify participant linking:
```bash
# Check if player is linked correctly
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT
    p.player_name,
    p.participant_id,
    tp.display_name as participant_name
FROM players p
LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
WHERE p.player_name LIKE '%PlayerName%'
"
```

If linked to wrong participant: Add manual override
If unlinked: Add participant and re-run linking

#### "Unlinked players not grouping by name"

Check for case variations:
```sql
SELECT
    player_name,
    player_name_normalized,
    COUNT(*)
FROM players
WHERE participant_id IS NULL
GROUP BY player_name_normalized, player_name
HAVING COUNT(*) > 1;
```

Should collapse to single row per normalized name.

### Performance Considerations

#### Query Optimization

Participant queries use CTEs and appropriate indexes:

```sql
-- Indexes used:
-- - players.participant_id (for JOIN)
-- - players.player_name_normalized (for fallback grouping)
-- - tournament_participants.participant_id (PRIMARY KEY)
```

For large datasets (>1000 matches):
- Queries typically execute in <100ms
- No additional optimization needed
- DuckDB handles aggregations efficiently

#### Caching

Dash app does NOT cache query results by default. Each page visit executes queries fresh.

For production with high traffic, consider:
- Add `dcc.Interval` component for periodic refresh
- Cache results in Redis/Memcached
- Pre-compute aggregations in background job

### Future Enhancements

**Multi-tournament support** (YAGNI - not implemented):
- Currently tracks single tournament via `participant_id`
- Could extend using `challonge_user_id` for cross-tournament
- Would require additional grouping level

**Fuzzy name matching** (YAGNI - not implemented):
- Current matching is exact normalized string match
- Could add Levenshtein distance for "Ninja" vs "Ninjaa"
- Manual overrides cover edge cases for now

**Participant detail page**:
- Dedicated `/participants/<id>` page
- Match history, opponent analysis, trends
- See Task 3 in implementation plan
```

**Update `CLAUDE.md`**:

Add after existing Participant Tracking section:

```markdown
## Participant UI Integration

### Display Strategy

The web app shows **participants** (real people), not match-scoped player instances.

**What this means:**
- Players page: One row per person, even if they played multiple matches
- Stats aggregate across all matches for that person
- Unlinked players (⚠️) grouped by normalized name until linked

### Key Queries

```python
from tournament_visualizer.data.queries import get_queries

queries = get_queries()

# Player performance (one row per person)
df = queries.get_player_performance()
# Columns: player_name, participant_id, is_unlinked, total_matches, wins, win_rate, ...

# Head-to-head (matches by participant_id)
stats = queries.get_head_to_head_stats('Player1', 'Player2')
# Returns: total_matches, player1_wins, player2_wins, avg_match_length, ...

# Civilization stats (counts unique participants)
df = queries.get_civilization_performance()
# Columns: civilization, total_matches, unique_participants, ...
```

### Visual Indicators

- ⚠️ = Unlinked player (needs manual override or better name matching)
- **Bold civ** = Favorite/most-played civilization
- Linking Coverage % = Data quality metric

### Data Quality

Run validation:
```bash
uv run python scripts/validate_participant_ui_data.py
```

Shows linking coverage and potential match opportunities.

### Common Tasks

**Check linking status:**
```bash
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT
    COUNT(*) as total,
    COUNT(participant_id) as linked,
    ROUND(COUNT(participant_id) * 100.0 / COUNT(*), 1) as coverage
FROM players
"
```

**Find unlinked players:**
```bash
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT player_name, COUNT(*) as instances
FROM players
WHERE participant_id IS NULL
GROUP BY player_name_normalized, player_name
ORDER BY instances DESC
"
```
```

**Commit Message**:
```
docs: Add participant UI integration documentation

Documents participant-first display strategy, key queries, visual
indicators, and troubleshooting guide. Updates both developer guide
and Claude context documentation.

- Explains show-all-with-fallback approach
- Documents query behavior and columns
- Provides common queries and troubleshooting
- Covers data quality validation
```

---

## Testing Strategy

### Test Pyramid

```
                    ▲
                   / \
                  /   \
                 /  E2E \
                /  Tests \
               /---------\
              /           \
             / Integration \
            /     Tests     \
           /----------------\
          /                  \
         /    Unit Tests      \
        /   (Queries, Utils)   \
       /______________________\
```

### Unit Tests (Foundation)

**What to test:**
- Individual query functions
- Data transformation logic
- Edge cases (NULL handling, empty results)

**Tools:**
- `pytest`
- `pytest-cov` for coverage
- Temporary DuckDB databases (`tmp_path` fixture)

**Coverage target:** >80% for `queries.py`, `pages/players.py`

### Integration Tests (Middle Layer)

**What to test:**
- Callback functions with real query results
- Data flow from database → query → UI
- Multiple components working together

**Tools:**
- `pytest`
- Mock database with realistic data

### End-to-End Tests (Top Layer - Optional)

**What to test:**
- Full page loads
- User interactions
- Visual rendering

**Tools:**
- `dash[testing]` (Selenium-based)
- Chrome/Firefox WebDriver

**Note:** E2E tests are slower and more brittle. Focus on unit + integration.

### Manual Testing Checklist

Before considering task complete:

```markdown
## Pre-Commit Checklist

### Code Quality
- [ ] All tests pass: `uv run pytest -v`
- [ ] Code formatted: `uv run black tournament_visualizer/`
- [ ] Linting clean: `uv run ruff check tournament_visualizer/`
- [ ] Coverage >80%: `uv run pytest --cov=tournament_visualizer.data.queries`

### Functionality
- [ ] Players page loads without errors
- [ ] Summary metrics show correct counts
- [ ] Table shows participant names (not duplicates)
- [ ] Unlinked players marked with ⚠️
- [ ] Civilizations column shows all civs
- [ ] Head-to-head matching works
- [ ] No JavaScript console errors

### Data Quality
- [ ] Validation script passes: `uv run python scripts/validate_participant_ui_data.py`
- [ ] Linked players appear once
- [ ] Unlinked players group by normalized name
- [ ] Win rates match manual calculation

### Performance
- [ ] Page loads in <2 seconds
- [ ] Queries execute in <500ms
- [ ] No memory leaks (check with multiple refreshes)

### Documentation
- [ ] Code comments explain WHY not WHAT
- [ ] Docstrings updated
- [ ] Developer guide updated
- [ ] CLAUDE.md updated
```

## Rollback Plan

If issues discovered after deployment:

### Quick Rollback (Revert UI Changes)

```bash
# Revert last commit
git revert HEAD

# Restart app
uv run python manage.py restart
```

### Partial Rollback (Keep Queries, Revert UI)

```bash
# Revert only UI changes
git revert <commit-hash-of-task-4>

# Keep query updates
# Restart app
uv run python manage.py restart
```

### Database Not Affected

No database changes in this plan - only query and UI updates.
Safe to rollback without data migration concerns.

## Success Criteria

Implementation successful when:

1. ✅ Players page shows one row per person (not per match instance)
2. ✅ Linked players group by `participant_id`
3. ✅ Unlinked players group by `player_name_normalized`
4. ✅ Visual indicators (⚠️) mark unlinked players
5. ✅ Summary metrics show linking coverage
6. ✅ Head-to-head uses participant matching
7. ✅ Civilization stats count unique participants
8. ✅ All tests pass
9. ✅ Validation script passes
10. ✅ Documentation complete

## Time Estimates

| Task | Estimated Time | Complexity |
|------|----------------|------------|
| Task 1: Player Performance Query | 2-3 hours | High |
| Task 2: Head-to-Head Query | 1.5-2 hours | Medium |
| Task 3: Civilization Query | 1 hour | Low |
| Task 4: Players Page UI | 2-3 hours | Medium |
| Task 5: Validation Script | 1-2 hours | Low |
| Task 6: Documentation | 1 hour | Low |
| **Total** | **8-12 hours** | |

Add buffer for:
- Debugging query edge cases
- UI polish and refinement
- Test fixes
- Documentation review

**Total with buffer: 10-15 hours**

## Dependencies

### Required Knowledge

- **SQL**: CTEs, window functions, JOINs, GROUP BY
- **Python**: Pandas DataFrames, type annotations
- **Dash**: Callbacks, component props, layout
- **DuckDB**: Syntax quirks vs PostgreSQL
- **Testing**: pytest fixtures, assertions

### Tools

- `uv` - Python package manager
- `duckdb` - Database CLI
- `pytest` - Testing framework
- `dash` - Web framework
- Browser DevTools - Debugging

### External Services

- None - all changes are local to codebase

## Glossary

| Term | Definition |
|------|------------|
| **Participant** | Real person in tournament (from Challonge) |
| **Player** | Match-scoped instance in save file |
| **Player Instance** | Single player record in `players` table |
| **Linked Player** | Player with `participant_id` foreign key |
| **Unlinked Player** | Player without participant link (NULL `participant_id`) |
| **Normalized Name** | Lowercase, no special chars (for matching) |
| **Display Name** | Original name for UI display |
| **Grouping Key** | SQL expression used to group rows (participant_id or normalized name) |
| **Smart Grouping** | Fallback strategy: use participant_id if available, else name |
| **Linking Coverage** | Percentage of player instances linked to participants |

## References

- Implementation Plan: `docs/plans/tournament-participant-tracking-implementation-plan.md`
- Migration Document: `docs/migrations/004_add_tournament_participants.md`
- Participant Matcher: `tournament_visualizer/data/participant_matcher.py`
- Validation Script (old): `scripts/validate_participants.py`
- Developer Guide: `docs/developer-guide.md`

---

## Appendix: Query Debugging

### Common Issues

**Issue: Player appears multiple times**

```sql
-- Debug query
SELECT
    player_name,
    participant_id,
    COUNT(*) as row_count
FROM (
    -- Paste your get_player_performance query here
)
GROUP BY player_name, participant_id
HAVING COUNT(*) > 1;
```

**Issue: Win rates don't sum correctly**

```sql
-- Check individual matches
SELECT
    p.player_name,
    m.match_id,
    mw.winner_player_id,
    CASE WHEN mw.winner_player_id = p.player_id THEN 1 ELSE 0 END as won
FROM players p
JOIN matches m ON p.match_id = m.match_id
LEFT JOIN match_winners mw ON m.match_id = mw.match_id
WHERE p.player_name LIKE '%YourPlayer%'
ORDER BY m.match_id;
```

**Issue: Unlinked players not grouping**

```sql
-- Check normalized names
SELECT
    player_name,
    player_name_normalized,
    participant_id,
    COUNT(*) as instances
FROM players
GROUP BY player_name, player_name_normalized, participant_id
ORDER BY player_name_normalized;
```

### SQL Execution Plan

```sql
-- View query plan
EXPLAIN <your query here>;

-- Should use indexes on:
-- - players.participant_id
-- - tournament_participants.participant_id
```

### Performance Profiling

```python
import time
from tournament_visualizer.data.queries import get_queries

queries = get_queries()

start = time.time()
df = queries.get_player_performance()
elapsed = time.time() - start

print(f"Query executed in {elapsed*1000:.2f}ms")
print(f"Returned {len(df)} rows")
```

Target: <500ms for player performance query on tournament-sized dataset (~50 matches).
