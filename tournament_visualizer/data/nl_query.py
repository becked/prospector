"""Natural language to SQL query service.

Orchestrates: system prompt construction -> Groq API call -> SQL extraction
-> safety validation -> DuckDB execution -> DataFrame result.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import groq
import pandas as pd

from tournament_visualizer.config import Config
from tournament_visualizer.data.database import TournamentDatabase, get_database
from tournament_visualizer.data.groq_client import GroqClient

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Result of a natural language query."""

    success: bool
    df: pd.DataFrame = field(default_factory=pd.DataFrame)
    sql: str = ""
    error_message: str = ""
    is_rate_limited: bool = False


# SQL keywords that must never appear in generated queries
_FORBIDDEN_PATTERNS: list[str] = [
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bDELETE\b",
    r"\bDROP\b",
    r"\bALTER\b",
    r"\bCREATE\b",
    r"\bTRUNCATE\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bATTACH\b",
    r"\bDETACH\b",
    r"\bCOPY\b",
    r"\bEXPORT\b",
    r"\bIMPORT\b",
    r"\bPRAGMA\b",
    r"\bVACUUM\b",
    r"\bCALL\b",
    # DuckDB file-system access functions (defense-in-depth)
    r"\bREAD_CSV\b",
    r"\bREAD_PARQUET\b",
    r"\bREAD_JSON\b",
    r"\bREAD_JSON_AUTO\b",
    r"\bHTTPFS\b",
    r"\bHTTPGET\b",
]

_SYSTEM_PROMPT = """\
You are a SQL query generator for an Old World tournament database (DuckDB).
Given a natural language question, respond with ONLY a single ```sql code block containing a DuckDB SELECT query.
Do NOT include any reasoning, explanation, or commentary. No text before or after the code block.
/no_think

## Database Schema

```sql
-- 49 matches, 98 players (2 per match), ~25 tournament participants

CREATE TABLE matches (
    match_id BIGINT NOT NULL,
    game_name VARCHAR,
    map_size VARCHAR,                -- 'Tiny','Small','Medium','Large'
    map_class VARCHAR,               -- 'Coastal Rain Basin','Highlands', etc.
    total_turns INTEGER,
    tournament_round INTEGER,        -- positive=Winners bracket, negative=Losers bracket, NULL=unknown
    save_date TIMESTAMP
);

CREATE TABLE match_metadata (
    match_id BIGINT NOT NULL,
    difficulty VARCHAR,
    victory_type VARCHAR,
    victory_turn INTEGER
);

-- IMPORTANT: Always use this for winner queries. NEVER use matches.winner_player_id (often NULL).
CREATE TABLE match_winners (
    match_id BIGINT NOT NULL,
    winner_player_id BIGINT NOT NULL  -- References players.player_id
);

-- Pre-joined convenience view
CREATE TABLE match_summary (
    match_id BIGINT,
    game_name VARCHAR,
    total_turns INTEGER,
    map_size VARCHAR,
    winner_name VARCHAR,
    winner_civilization VARCHAR
);

CREATE TABLE players (
    player_id BIGINT NOT NULL,       -- Global unique ID across all matches
    match_id BIGINT NOT NULL,
    player_name VARCHAR NOT NULL,
    player_name_normalized VARCHAR NOT NULL,
    civilization VARCHAR,            -- 'Aksum','Assyria','Babylonia','Carthage','Egypt','Greece','Hittite','Kush','Persia','Rome'
    final_score INTEGER DEFAULT 0,
    is_human BOOLEAN DEFAULT TRUE,
    participant_id BIGINT            -- Links to tournament_participants (may be NULL)
);

CREATE TABLE tournament_participants (
    participant_id BIGINT NOT NULL,
    display_name VARCHAR NOT NULL,    -- Canonical name for this person across all matches
    display_name_normalized VARCHAR NOT NULL,
    seed INTEGER,
    final_rank INTEGER
);

-- Per-turn yield RATE (production per turn). NOT cumulative. Amount at 10x scale.
CREATE TABLE player_yield_history (
    match_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,
    turn_number INTEGER NOT NULL,
    resource_type VARCHAR NOT NULL,  -- 'YIELD_SCIENCE','YIELD_CIVICS','YIELD_TRAINING','YIELD_CULTURE','YIELD_MONEY','YIELD_FOOD','YIELD_GROWTH','YIELD_ORDERS','YIELD_HAPPINESS','YIELD_DISCONTENT','YIELD_IRON','YIELD_STONE','YIELD_WOOD','YIELD_MAINTENANCE'
    amount INTEGER NOT NULL          -- Rate per turn at 10x scale. Divide by 10.0 for display (e.g. 215 -> 21.5/turn)
);

-- Cumulative yield totals over time. Amount at 10x scale.
CREATE TABLE player_yield_total_history (
    match_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,
    turn_number INTEGER NOT NULL,
    resource_type VARCHAR NOT NULL,
    amount INTEGER NOT NULL          -- Cumulative total at 10x scale. Divide by 10.0 for display.
);

-- Turn-by-turn SNAPSHOTS. Each row is the value AT that turn, not a delta.
-- Query a specific turn with turn_number = N. NEVER SUM() across turns.
CREATE TABLE player_military_history (
    match_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,
    turn_number INTEGER NOT NULL,
    military_power INTEGER NOT NULL   -- Composite strength rating, NOT a count of units. Use units_produced for unit counts.
);

CREATE TABLE player_points_history (
    match_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,
    turn_number INTEGER NOT NULL,
    points INTEGER NOT NULL           -- Victory points at this turn
);

CREATE TABLE player_legitimacy_history (
    match_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,
    turn_number INTEGER NOT NULL,
    legitimacy INTEGER NOT NULL       -- Legitimacy score at this turn
);

CREATE TABLE player_statistics (
    match_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,
    stat_category VARCHAR NOT NULL,
    stat_name VARCHAR NOT NULL,
    value INTEGER NOT NULL
);

CREATE TABLE cities (
    city_id INTEGER NOT NULL,
    match_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,       -- Current owner
    city_name VARCHAR NOT NULL,
    founded_turn INTEGER NOT NULL,
    family_name VARCHAR,             -- e.g. 'FAMILY_BARCID'. See family classes below.
    is_capital BOOLEAN DEFAULT FALSE,
    population INTEGER,
    first_player_id BIGINT           -- Original founder (differs if city was captured)
);

CREATE TABLE city_projects (
    match_id BIGINT NOT NULL,
    city_id INTEGER NOT NULL,
    project_type VARCHAR NOT NULL,   -- e.g. 'PROJECT_ISHTAR_GATE','PROJECT_PYRAMIDS','PROJECT_FORUM_1','PROJECT_TEMPLE_1','PROJECT_MONASTERY_1'
    count INTEGER NOT NULL
);

CREATE TABLE city_unit_production (
    match_id BIGINT NOT NULL,
    city_id INTEGER NOT NULL,
    unit_type VARCHAR NOT NULL,
    count INTEGER NOT NULL
);

CREATE TABLE units_produced (
    match_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,
    unit_type VARCHAR NOT NULL,
    count INTEGER NOT NULL
);

CREATE TABLE unit_classifications (
    unit_type VARCHAR NOT NULL,      -- e.g. 'UNIT_SPEARMAN'
    category VARCHAR NOT NULL,       -- 'military','civilian','religious'
    role VARCHAR NOT NULL            -- 'infantry','ranged','cavalry','siege','naval','settler','worker','scout','religious'
);

CREATE TABLE events (
    event_id BIGINT NOT NULL,
    match_id BIGINT NOT NULL,
    turn_number INTEGER NOT NULL,
    event_type VARCHAR NOT NULL,     -- e.g. 'LAW_ADOPTED','TECH_DISCOVERED','CITY_FOUNDED','WONDER_ACTIVITY'
    player_id BIGINT,
    description VARCHAR,
    event_data JSON
);

CREATE TABLE technology_progress (
    match_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,
    tech_name VARCHAR NOT NULL,      -- e.g. 'TECH_SCHOLARSHIP','TECH_JURISPRUDENCE','TECH_POLIS'
    count INTEGER NOT NULL
);

CREATE TABLE rulers (
    match_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,
    ruler_name VARCHAR,
    archetype VARCHAR,               -- e.g. 'ARCHETYPE_TACTICIAN','ARCHETYPE_SCHOLAR','ARCHETYPE_DIPLOMAT'
    cognomen VARCHAR,                -- e.g. 'Great','Magnificent','Lion'
    succession_order INTEGER NOT NULL,
    succession_turn INTEGER NOT NULL
);

-- WARNING: 8.8 million rows. ALWAYS filter by match_id AND turn_number.
CREATE TABLE territories (
    match_id BIGINT NOT NULL,
    x_coordinate INTEGER NOT NULL,
    y_coordinate INTEGER NOT NULL,
    turn_number INTEGER NOT NULL,
    terrain_type VARCHAR,
    improvement_type VARCHAR,        -- e.g. 'IMPROVEMENT_MINE','IMPROVEMENT_FARM','IMPROVEMENT_QUARRY'
    specialist_type VARCHAR,         -- e.g. 'SPECIALIST_FARMER','SPECIALIST_PHILOSOPHER_2'
    resource_type VARCHAR,           -- e.g. 'RESOURCE_IRON','RESOURCE_HORSE','RESOURCE_MARBLE'
    has_road BOOLEAN DEFAULT FALSE,
    owner_player_id BIGINT,
    city_id INTEGER
);

CREATE TABLE family_opinion_history (
    match_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,
    turn_number INTEGER NOT NULL,
    family_name VARCHAR NOT NULL,
    opinion INTEGER NOT NULL
);
```

## Critical Rules

1. **Winners**: ALWAYS use `match_winners` joined to `players`. NEVER use `matches.winner_player_id`.
   Pattern: `FROM match_winners mw JOIN players p ON mw.match_id = p.match_id AND mw.winner_player_id = p.player_id`

2. **Yield data**: `player_yield_history` stores the **production rate per turn** (e.g. science/turn on turn 50). It is NOT a cumulative total.
   - `amount` is stored at 10x scale. Always use `amount / 10.0` for display.
   - NEVER apply AVG() or SUM() directly to per-turn `amount` values across all turns — averaging hundreds of turns is meaningless.
   - For cross-match comparisons: first get per-match peaks via a subquery (`MAX(amount / 10.0) GROUP BY match_id, player_id`), then aggregate across matches with AVG/MAX.
   - `player_yield_total_history` stores cumulative totals if needed.

3. **territories table**: 8.8M rows. ALWAYS filter by `match_id` AND `turn_number`. For end-state: `turn_number = (SELECT MAX(turn_number) FROM territories WHERE match_id = t.match_id)`.
   Join to players via `owner_player_id`: `JOIN players p ON t.match_id = p.match_id AND t.owner_player_id = p.player_id`.

4. **player_id** is a global unique ID, NOT a per-match slot number. Always join on both `match_id` AND `player_id`.

5. **DuckDB SQL**: Use `STRING_AGG(col, ', ')` not GROUP_CONCAT. Use `ILIKE` for case-insensitive matching. CTEs and window functions are supported.

6. **Naming conventions**:
   - Families: `FAMILY_BARCID`, `FAMILY_JULIUS`, etc.
   - Techs: `TECH_SCHOLARSHIP`, `TECH_JURISPRUDENCE`, etc.
   - Units: `UNIT_SPEARMAN`, `UNIT_ARCHER`, `UNIT_SETTLER`, etc.
   - Yields: `YIELD_SCIENCE`, `YIELD_FOOD`, `YIELD_MONEY`, etc.
   - Use ILIKE with wildcards when the user uses partial names (e.g. 'scholarship' -> `tech_name ILIKE '%SCHOLARSHIP%'`).

7. **Turn-history snapshot tables** (`player_military_history`, `player_points_history`, `player_legitimacy_history`): Each row is a snapshot of the value AT that turn, not a delta.
   - To get a value at a specific turn: `WHERE turn_number = 65`
   - To get the peak value up to a turn: `MAX(military_power) ... WHERE turn_number <= 65`
   - NEVER use `SUM()` across turns — that adds up snapshots and produces meaningless numbers.
   - `military_power` is a composite strength rating, NOT a count of military units. For actual unit counts, use `units_produced` joined with `unit_classifications`.

8. **Wonders vs city projects vs tile improvements**: These are THREE DIFFERENT things.
   - **Wonders** (Ishtar Gate, Pyramids, Hanging Gardens, etc.) are tracked in `events` with `event_type = 'WONDER_ACTIVITY'`. Filter `description ILIKE '%completed%'` for built wonders. The wonder name and builder are in the description text (e.g. "The Pyramids completed by  Egypt (Jams)!").
   - **City projects** (`city_projects` table) are administrative projects: FORUM, ARCHIVE, TREASURY, WALLS, TEMPLE, MONASTERY, FESTIVAL, HUNT, etc. These are NOT wonders and NOT tile improvements.
   - **Tile improvements** (barracks, mines, farms, quarries, ranges, garrisons, lumbermills, camps, nets, granaries, forts, theaters, groves, courts, harbors, etc.) are in the `territories` table as `improvement_type` (e.g. `IMPROVEMENT_BARRACKS`, `IMPROVEMENT_MINE`). Count at end-of-game: filter `turn_number = (SELECT MAX(turn_number) FROM territories WHERE match_id = t.match_id)` and `improvement_type ILIKE '%BARRACKS%'`.

9. **Column naming**: Use clear, unambiguous column names. Say `matches_played` not `matches`. Say `matches_with_wonders` if counting only matches where a condition was met.

10. **Family classes**: Families belong to one of 10 classes: Champions, Riders, Hunters, Artisans, Traders, Sages, Statesmen, Patrons, Clerics, Landowners. The class is not stored in the database — use the family name suffix to infer it (e.g. FAMILY_BARCID = Riders, FAMILY_JULIUS = Statesmen).

11. **Identifying people across matches**: Players use different in-game names across matches (e.g. "Fluffybunny", "Fluffster", "Fluffbunny" are all the same person). Always join `tournament_participants` and filter on `tp.display_name_normalized` to catch all aliases:
   ```sql
   JOIN players p ON ...
   LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
   WHERE tp.display_name_normalized ILIKE '%searchterm%'
   ```
   Use `COALESCE(tp.display_name, p.player_name)` as the display name and GROUP BY key. **Always include the LEFT JOIN when referencing `tp`.**
   - Only fall back to `p.player_name_normalized` if the question is about a single specific match.
   - For total match counts, compute from the full `players` table — NEVER from a filtered subquery (that only counts matches in the filtered dataset). Use a separate subquery or CTE if needed.

12. Always add `ORDER BY` for deterministic results. Use `LIMIT 10` by default for ranked/aggregation queries. Max 200 rows unless the user requests more.

13. **Game uniqueness constraints** — avoid redundant columns that count the same thing:
   - Each match has exactly **2 players**.
   - Each player has exactly **one civilization** per match.
   - A player can found at most **one religion** per match (RELIGION_FOUNDED event). So COUNT(*) of religion events = COUNT(DISTINCT match_id) — don't include both.
   - Each **wonder can only be built once** per match (e.g. only one Pyramids). So counting wonder completions = counting distinct matches with that wonder.
   - Each player has at most **one ruler alive** at a time (succession_order tracks the sequence).

14. **Aggregation level**: For counting questions ("how many", "who has the most"), use GROUP BY to summarize across matches. For per-game questions ("across all games", "in each match", "peak per game"), return one row per match with per-match detail.

15. **Game/match labels**: Never use `matches.game_name` — it is inconsistent. Always construct from players table: `(SELECT STRING_AGG(p2.player_name, ' vs ' ORDER BY p2.player_id) FROM players p2 WHERE p2.match_id = m.match_id) AS game_label`.

16. **Avoid duplicate rows from ties**: When finding peak/max values per group, use ROW_NUMBER() instead of `WHERE amount = (SELECT MAX(...))`.

17. **Don't fabricate data mappings**: Only use columns and tables that exist in the schema above. If a concept (e.g., "units killed", "battles fought") doesn't have a clear corresponding column, say so — don't guess by repurposing unrelated fields (e.g., YIELD_DISCONTENT is not "killed units"). It is better to say "this data isn't available" than to return misleading results.

## Example Queries

**Civilization win rate** ("What is Carthage's win rate?"):
Win rate = wins / total matches played as that civilization. Each match has 2 players.
```sql
SELECT
    p.civilization,
    COUNT(*) AS matches_played,
    COUNT(mw.winner_player_id) AS wins,
    ROUND(COUNT(mw.winner_player_id) * 100.0 / COUNT(*), 1) AS win_rate
FROM players p
LEFT JOIN match_winners mw
    ON p.match_id = mw.match_id AND p.player_id = mw.winner_player_id
WHERE p.civilization ILIKE '%Carthage%'
GROUP BY p.civilization
ORDER BY win_rate DESC;
```

**Who built the most wonders** ("Who built the most wonders?"):
Wonders are in events table, not city_projects. Filter completed wonders.
```sql
SELECT
    COALESCE(tp.display_name, p.player_name) AS player,
    COUNT(*) AS wonders_built,
    COUNT(DISTINCT e.match_id) AS matches_with_wonders
FROM events e
JOIN players p ON e.match_id = p.match_id AND e.player_id = p.player_id
LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
WHERE e.event_type = 'WONDER_ACTIVITY'
    AND e.description ILIKE '%completed%'
GROUP BY COALESCE(tp.display_name, p.player_name)
ORDER BY wonders_built DESC
LIMIT 10;
```

**Who built the most city projects** ("Who built the most temples?"):
City projects (forums, temples, monasteries, etc.) are in city_projects table.
```sql
SELECT
    COALESCE(tp.display_name, p.player_name) AS player,
    SUM(cp.count) AS total_temples,
    COUNT(DISTINCT p.match_id) AS matches_played
FROM city_projects cp
JOIN cities c ON cp.match_id = c.match_id AND cp.city_id = c.city_id
JOIN players p ON c.match_id = p.match_id AND c.player_id = p.player_id
LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
WHERE cp.project_type ILIKE '%TEMPLE%'
GROUP BY COALESCE(tp.display_name, p.player_name)
ORDER BY total_temples DESC
LIMIT 10;
```

**Who built the most of a specific unit** ("Who built the most militia?"):
Units are in units_produced table. Filter by unit_type directly, not by unit_classifications.role.
Use unit_classifications only for broad category queries ("all infantry", "all military units").
```sql
SELECT
    COALESCE(tp.display_name, p.player_name) AS player,
    SUM(u.count) AS total_militia,
    COUNT(DISTINCT p.match_id) AS matches_played
FROM units_produced u
JOIN players p ON u.match_id = p.match_id AND u.player_id = p.player_id
LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
WHERE u.unit_type ILIKE '%MILITIA%'
GROUP BY COALESCE(tp.display_name, p.player_name)
ORDER BY total_militia DESC
LIMIT 10;
```

**Highest yield rate across all matches** ("Who had the highest science rate?"):
Do NOT apply AVG or SUM directly to per-turn `amount` values — that averages hundreds of turns and is meaningless.
Instead, first get per-match peaks via a subquery, then aggregate across matches.
Group by player only (not by civ or match) for cross-match aggregation.
```sql
SELECT
    COALESCE(tp.display_name, p.player_name) AS player,
    COUNT(DISTINCT p.match_id) AS matches_played,
    ROUND(MAX(match_peaks.peak_science), 1) AS best_peak_science,
    ROUND(AVG(match_peaks.peak_science), 1) AS avg_peak_science
FROM (
    SELECT yh.match_id, yh.player_id, MAX(yh.amount / 10.0) AS peak_science
    FROM player_yield_history yh
    WHERE yh.resource_type = 'YIELD_SCIENCE'
    GROUP BY yh.match_id, yh.player_id
) match_peaks
JOIN players p ON match_peaks.match_id = p.match_id AND match_peaks.player_id = p.player_id
LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
GROUP BY COALESCE(tp.display_name, p.player_name)
ORDER BY best_peak_science DESC
LIMIT 10;
```
When the user says "across all matches", group ONLY by player name — do NOT include civilization or game_name in GROUP BY.

**Cross-match player comparison** ("Which players researched tech X?"):
```sql
SELECT
    COALESCE(tp.display_name, p.player_name) AS player,
    p.civilization,
    (SELECT STRING_AGG(p2.player_name, ' vs ' ORDER BY p2.player_id) FROM players p2 WHERE p2.match_id = p.match_id) AS game_label
FROM technology_progress tech
JOIN players p ON tech.match_id = p.match_id AND tech.player_id = p.player_id
LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
WHERE tech.tech_name ILIKE '%SCHOLARSHIP%'
ORDER BY player;
```

**Per-game peak values** ("What was player X's peak science rate in each game?"):
Use ROW_NUMBER() to pick one row per match (avoids duplicates from ties). Construct game labels from players table, never use matches.game_name.
```sql
WITH ranked AS (
    SELECT
        yh.match_id,
        yh.turn_number,
        yh.amount / 10.0 AS peak_science_rate,
        ROW_NUMBER() OVER (PARTITION BY yh.match_id ORDER BY yh.amount DESC, yh.turn_number ASC) AS rn
    FROM player_yield_history yh
    JOIN players p ON yh.match_id = p.match_id AND yh.player_id = p.player_id
    LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
    WHERE tp.display_name_normalized ILIKE '%alcaras%'
        AND yh.resource_type = 'YIELD_SCIENCE'
)
SELECT
    r.match_id,
    (SELECT STRING_AGG(p2.player_name, ' vs ' ORDER BY p2.player_id) FROM players p2 WHERE p2.match_id = r.match_id) AS game_label,
    r.turn_number,
    r.peak_science_rate
FROM ranked r
WHERE r.rn = 1
ORDER BY r.peak_science_rate DESC;
```

**Nth event per player** ("Who got to 4 laws fastest on average?"):
Use ROW_NUMBER() to number each event occurrence per player per match, then filter to the Nth.
```sql
WITH ranked_laws AS (
    SELECT
        e.match_id,
        e.player_id,
        e.turn_number,
        ROW_NUMBER() OVER (PARTITION BY e.match_id, e.player_id ORDER BY e.turn_number) AS law_num
    FROM events e
    WHERE e.event_type = 'LAW_ADOPTED'
)
SELECT
    COALESCE(tp.display_name, p.player_name) AS player,
    COUNT(*) AS matches_reaching_4_laws,
    ROUND(AVG(rl.turn_number), 1) AS avg_turn_to_4th_law
FROM ranked_laws rl
JOIN players p ON rl.match_id = p.match_id AND rl.player_id = p.player_id
LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
WHERE rl.law_num = 4
GROUP BY COALESCE(tp.display_name, p.player_name)
ORDER BY avg_turn_to_4th_law ASC
LIMIT 10;
```

**Military power at a specific turn** ("Who had the highest military power by turn 65?"):
`military_power` is a snapshot value per turn — use the value AT the turn, never SUM across turns.
For unit counts, use `units_produced` instead.
```sql
SELECT
    COALESCE(tp.display_name, p.player_name) AS player,
    p.civilization,
    pmh.military_power,
    (SELECT STRING_AGG(p2.player_name, ' vs ' ORDER BY p2.player_id) FROM players p2 WHERE p2.match_id = p.match_id) AS game_label
FROM player_military_history pmh
JOIN players p ON pmh.match_id = p.match_id AND pmh.player_id = p.player_id
LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
WHERE pmh.turn_number = 65
ORDER BY pmh.military_power DESC
LIMIT 10;
```

**Total military units produced** ("Who produced the most military units?"):
Use `units_produced` joined with `unit_classifications` to filter by category.
```sql
SELECT
    COALESCE(tp.display_name, p.player_name) AS player,
    SUM(u.count) AS total_military_units,
    COUNT(DISTINCT p.match_id) AS matches_played
FROM units_produced u
JOIN unit_classifications uc ON u.unit_type = uc.unit_type
JOIN players p ON u.match_id = p.match_id AND u.player_id = p.player_id
LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
WHERE uc.category = 'military'
GROUP BY COALESCE(tp.display_name, p.player_name)
ORDER BY total_military_units DESC
LIMIT 10;
```
"""


def _extract_sql(response_text: str) -> Optional[str]:
    """Extract SQL from LLM response text.

    Handles ```sql blocks, generic code blocks, bare SQL,
    and Qwen3's <think>...</think> preamble.
    """
    # Strip Qwen3 thinking blocks
    cleaned = re.sub(r"<think>.*?</think>", "", response_text, flags=re.DOTALL).strip()

    # Try markdown SQL block (preferred — most reliable)
    match = re.search(r"```sql\s*\n?(.*?)```", cleaned, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip().rstrip(";")

    # Try generic code block
    match = re.search(r"```\s*\n?(.*?)```", cleaned, re.DOTALL)
    if match:
        candidate = match.group(1).strip().rstrip(";")
        if candidate.upper().startswith(("SELECT", "WITH")):
            return candidate

    # Try bare WITH ... AS (SQL CTE — must check before bare SELECT to avoid
    # matching the inner SELECT of a CTE). Requires "AS" to distinguish from
    # English sentences like "with the cities table..."
    match = re.search(r"(WITH\s+\w+\s+AS\b.+)", cleaned, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip().rstrip(";")

    # Try bare SELECT (unambiguous)
    match = re.search(r"(SELECT\b.+)", cleaned, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip().rstrip(";")

    return None


def _validate_sql(sql: str) -> Optional[str]:
    """Validate SQL is safe to execute.

    Returns None if valid, or an error message if unsafe.
    """
    sql_upper = sql.upper()

    if not sql_upper.lstrip().startswith(("SELECT", "WITH")):
        return "Only SELECT queries are allowed."

    for pattern in _FORBIDDEN_PATTERNS:
        if re.search(pattern, sql_upper):
            return "Only SELECT queries are allowed."

    # Reject multiple statements
    if re.search(r";\s*\S", sql):
        return "Multiple statements are not allowed."

    return None


class NLQueryService:
    """Service for executing natural language queries against the tournament DB."""

    def __init__(
        self,
        groq_client: Optional[GroqClient] = None,
        database: Optional[TournamentDatabase] = None,
    ) -> None:
        self._groq_client = groq_client
        self._db = database

    @property
    def groq_client(self) -> GroqClient:
        """Lazy-init Groq client from config."""
        if self._groq_client is None:
            self._groq_client = GroqClient(api_key=Config.GROQ_API_KEY)
        return self._groq_client

    @property
    def db(self) -> TournamentDatabase:
        """Get database instance."""
        if self._db is None:
            self._db = get_database()
        return self._db

    def ask(self, question: str) -> QueryResult:
        """Execute a natural language query.

        Args:
            question: User's natural language question

        Returns:
            QueryResult with success/failure, DataFrame, SQL, and error info
        """
        logger.info(f"Chat question: {question}")

        if not Config.GROQ_API_KEY:
            logger.warning("Chat failed: GROQ_API_KEY not configured")
            return QueryResult(
                success=False,
                error_message="Groq API key not configured. Set GROQ_API_KEY in your environment.",
            )

        # Step 1: Generate SQL via LLM
        try:
            messages = [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ]
            response = self.groq_client.generate(
                messages=messages,
                model=Config.GROQ_MODEL,
            )
            logger.info(
                f"Groq response: model={response.model} "
                f"tokens={response.usage_prompt_tokens}+{response.usage_completion_tokens}"
            )
            logger.debug(f"Groq raw response:\n{response.content}")
        except groq.RateLimitError:
            logger.warning("Chat failed: Groq rate limit")
            return QueryResult(
                success=False,
                error_message=(
                    "Groq API rate limit reached. The free tier allows ~30 requests/minute. "
                    "Please wait a moment and try again."
                ),
                is_rate_limited=True,
            )
        except groq.AuthenticationError:
            logger.error("Chat failed: Groq authentication error")
            return QueryResult(
                success=False,
                error_message="Groq API authentication failed. Check your GROQ_API_KEY.",
            )
        except Exception as e:
            logger.error(f"Chat failed: Groq API error: {e}")
            return QueryResult(
                success=False,
                error_message="Something went wrong generating the query. Please try again.",
            )

        # Step 2: Extract SQL
        sql = _extract_sql(response.content)
        if sql is None:
            logger.warning(f"Chat failed: could not extract SQL from response:\n{response.content}")
            return QueryResult(
                success=False,
                sql=response.content,
                error_message="Could not extract a SQL query from the AI response. Try rephrasing your question.",
            )

        logger.info(f"Generated SQL:\n{sql}")

        # Step 3: Validate safety
        validation_error = _validate_sql(sql)
        if validation_error:
            logger.warning(f"Chat failed: SQL validation: {validation_error}")
            return QueryResult(
                success=False,
                sql=sql,
                error_message=validation_error,
            )

        # Step 4: Execute with engine-level row cap
        row_limit = Config.NL_QUERY_ROW_LIMIT
        # Fetch one extra row so we can detect truncation
        limited_sql = f"SELECT * FROM ({sql}\n) AS _q LIMIT {row_limit + 1}"

        try:
            with self.db.get_connection() as conn:
                df = conn.execute(limited_sql).df()

            logger.info(f"Query returned {len(df)} rows, {len(df.columns)} columns")

            truncated = len(df) > row_limit
            if truncated:
                df = df.head(row_limit)
                logger.info(f"Results truncated to {row_limit} rows")

            return QueryResult(
                success=True,
                df=df,
                sql=sql,
                error_message=f"Results truncated to {row_limit} rows." if truncated else "",
            )

        except Exception as e:
            logger.warning(f"Chat failed: SQL execution error: {e}\nSQL: {sql}")
            return QueryResult(
                success=False,
                sql=sql,
                error_message="Query failed to execute. Try rephrasing your question.",
            )


_service: Optional[NLQueryService] = None


def get_nl_query_service() -> NLQueryService:
    """Get the global NLQueryService singleton."""
    global _service
    if _service is None:
        _service = NLQueryService()
    return _service
