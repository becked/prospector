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
