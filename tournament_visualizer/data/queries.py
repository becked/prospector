"""Reusable SQL queries for tournament data analysis.

This module contains predefined SQL queries for common data analysis tasks
in the tournament visualization application.
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from .database import TournamentDatabase, get_database


class TournamentQueries:
    """Collection of reusable queries for tournament data analysis."""

    def __init__(self, database: Optional[TournamentDatabase] = None) -> None:
        """Initialize with database connection.

        Args:
            database: Database instance to use (defaults to global instance)
        """
        self.db = database or get_database()

    def get_match_summary(self) -> pd.DataFrame:
        """Get comprehensive match summary data.

        Returns:
            DataFrame with match summary information including player nations
        """
        query = """
        WITH player_info AS (
            SELECT
                match_id,
                STRING_AGG(
                    player_name || ' (' || COALESCE(civilization, 'Unknown') || ')',
                    ' vs '
                    ORDER BY player_id
                ) as players_with_nations
            FROM players
            GROUP BY match_id
        )
        SELECT
            m.match_id,
            COALESCE(m.game_name, 'Unknown Game') as game_name,
            m.save_date,
            m.total_turns,
            COALESCE(m.map_size, 'Unknown') as map_size,
            COALESCE(m.map_class, 'Unknown') as map_class,
            COALESCE(m.turn_style, 'Unknown') as turn_style,
            COALESCE(m.victory_conditions, 'Unknown') as victory_conditions,
            COUNT(p.player_id) as player_count,
            COALESCE(w.player_name, 'Unknown') as winner_name,
            COALESCE(w.civilization, 'Unknown') as winner_civilization,
            pi.players_with_nations,
            m.processed_date
        FROM matches m
        LEFT JOIN players p ON m.match_id = p.match_id
        LEFT JOIN match_winners mw ON m.match_id = mw.match_id
        LEFT JOIN players w ON mw.winner_player_id = w.player_id
        LEFT JOIN player_info pi ON m.match_id = pi.match_id
        GROUP BY m.match_id, m.game_name, m.save_date, m.total_turns,
                 m.map_size, m.map_class, m.turn_style, m.victory_conditions,
                 w.player_name, w.civilization, pi.players_with_nations, m.processed_date
        ORDER BY m.save_date DESC NULLS LAST, m.processed_date DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query).df()

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
                - unique_linked_participants: Count of linked only
                - unique_unlinked_players: Count of unlinked only (for data quality)
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

    def get_match_duration_analysis(self) -> pd.DataFrame:
        """Get match duration analysis.

        Returns:
            DataFrame with match duration statistics
        """
        query = """
        SELECT
            m.match_id,
            COALESCE(m.game_name, 'Unknown Game') as game_name,
            m.total_turns,
            COALESCE(m.map_size, 'Unknown') as map_size,
            COALESCE(m.turn_style, 'Unknown') as turn_style,
            COUNT(p.player_id) as player_count,
            CASE 
                WHEN m.total_turns <= 50 THEN 'Short (≤50)'
                WHEN m.total_turns <= 100 THEN 'Medium (51-100)'
                WHEN m.total_turns <= 150 THEN 'Long (101-150)'
                ELSE 'Very Long (>150)'
            END as duration_category
        FROM matches m
        LEFT JOIN players p ON m.match_id = p.match_id
        WHERE m.total_turns > 0
        GROUP BY m.match_id, m.game_name, m.total_turns, m.map_size, m.turn_style
        ORDER BY m.total_turns DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query).df()

    def get_opponents(self, player_name: str) -> List[str]:
        """Get list of players who have faced the given player.

        Matches players by participant_id when possible (authoritative),
        falls back to name matching for unlinked players.

        Args:
            player_name: Display name of player (participant or player name)

        Returns:
            List of opponent display names, sorted alphabetically
        """
        query = """
        WITH player_identification AS (
            -- Find target player's participant_id (if linked)
            SELECT
                COALESCE(
                    CAST(tp.participant_id AS VARCHAR),
                    'unlinked_' || LOWER(?)
                ) as player_key,
                ? as player_name
            FROM (SELECT ? as name) input
            LEFT JOIN tournament_participants tp ON tp.display_name = input.name
        ),
        player_matches AS (
            -- Find all matches where target player participated
            SELECT DISTINCT
                m.match_id,
                p_target.player_id as target_player_id
            FROM matches m
            CROSS JOIN player_identification p_id
            -- Join to find target player in matches
            JOIN players p_target ON m.match_id = p_target.match_id
                AND (
                    -- Match by participant_id if linked
                    (p_target.participant_id IS NOT NULL
                     AND CAST(p_target.participant_id AS VARCHAR) = p_id.player_key)
                    OR
                    -- Match by normalized name if unlinked
                    (p_target.participant_id IS NULL
                     AND p_id.player_key = 'unlinked_' || LOWER(p_target.player_name))
                )
        ),
        opponents AS (
            -- Find all players who faced the target player
            SELECT DISTINCT
                COALESCE(tp.display_name, p.player_name) as opponent_name
            FROM player_matches pm
            JOIN players p ON pm.match_id = p.match_id
                AND p.player_id != pm.target_player_id
            LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
        )
        SELECT opponent_name
        FROM opponents
        ORDER BY opponent_name
        """

        with self.db.get_connection() as conn:
            result = conn.execute(
                query,
                [player_name.lower(), player_name, player_name],
            ).fetchall()

        return [row[0] for row in result]

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
                    CAST(tp1.participant_id AS VARCHAR),
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
                    CAST(tp2.participant_id AS VARCHAR),
                    'unlinked_' || ?
                ) as player2_key,
                ? as player2_name
            FROM (SELECT ? as name) input
            LEFT JOIN tournament_participants tp2 ON tp2.display_name = input.name
        ),
        match_participants AS (
            -- Find all matches where both players participated
            SELECT DISTINCT
                m.match_id,
                m.game_name,
                m.save_date,
                m.total_turns,
                p1_id.player1_name,
                p2_id.player2_name,
                -- Determine winner using participant matching
                CASE
                    WHEN p_winner.participant_id IS NOT NULL
                         AND CAST(p_winner.participant_id AS VARCHAR) = p1_id.player1_key
                        THEN p1_id.player1_name
                    WHEN p_winner.participant_id IS NOT NULL
                         AND CAST(p_winner.participant_id AS VARCHAR) = p2_id.player2_key
                        THEN p2_id.player2_name
                    WHEN p_winner.participant_id IS NULL
                         AND LOWER(p_winner.player_name) = SUBSTRING(p1_id.player1_key, 10)
                        THEN p1_id.player1_name
                    WHEN p_winner.participant_id IS NULL
                         AND LOWER(p_winner.player_name) = SUBSTRING(p2_id.player2_key, 10)
                        THEN p2_id.player2_name
                    ELSE NULL
                END as winner_name
            FROM matches m
            CROSS JOIN player_identification p1_id
            CROSS JOIN player2_identification p2_id
            -- Join to find player1 in this match
            JOIN players p1 ON m.match_id = p1.match_id
                AND (
                    -- Match by participant_id if linked
                    (p1.participant_id IS NOT NULL
                     AND CAST(p1.participant_id AS VARCHAR) = p1_id.player1_key)
                    OR
                    -- Match by normalized name if unlinked
                    (p1.participant_id IS NULL
                     AND p1_id.player1_key = 'unlinked_' || LOWER(p1.player_name))
                )
            -- Join to find player2 in the same match
            JOIN players p2 ON m.match_id = p2.match_id
                AND p2.player_id != p1.player_id
                AND (
                    -- Match by participant_id if linked
                    (p2.participant_id IS NOT NULL
                     AND CAST(p2.participant_id AS VARCHAR) = p2_id.player2_key)
                    OR
                    -- Match by normalized name if unlinked
                    (p2.participant_id IS NULL
                     AND p2_id.player2_key = 'unlinked_' || LOWER(p2.player_name))
                )
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
                "1": player1.lower(),  # player1_identification CTE param 1
                "2": player1,  # player1_identification CTE param 2
                "3": player1,  # player1_identification CTE param 3
                "4": player2.lower(),  # player2_identification CTE param 1
                "5": player2,  # player2_identification CTE param 2
                "6": player2,  # player2_identification CTE param 3
                "7": player1,  # Final aggregation player1
                "8": player2,  # Final aggregation player2
            },
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

    def get_map_performance_analysis(self) -> pd.DataFrame:
        """Get performance analysis by map characteristics.

        Counts unique participants (people) rather than player name strings
        to accurately reflect how many different people have played on each
        map configuration.

        Returns:
            DataFrame with map performance data including aspect ratio and participant counts:
                - map_size: Map size (e.g., 'SMALL', 'MEDIUM', 'LARGE')
                - map_class: Map class (e.g., 'INLAND', 'LAKES')
                - map_aspect_ratio: Aspect ratio (e.g., 'STANDARD', 'WIDE')
                - total_matches: Number of matches with this configuration
                - avg_turns: Average match length in turns
                - min_turns: Shortest match
                - max_turns: Longest match
                - unique_participants: Count of unique people (linked + unlinked proxy)
                - unique_linked_participants: Count of properly linked only
                - unique_unlinked_players: Count of unlinked only (data quality metric)
        """
        query = """
        WITH player_identity AS (
            SELECT
                m.match_id,
                p.player_id,
                m.map_size,
                m.map_class,
                m.map_aspect_ratio,
                m.total_turns,
                -- Create person key: participant_id if available, else normalized name
                COALESCE(
                    CAST(p.participant_id AS VARCHAR),
                    'unlinked_' || p.player_name_normalized
                ) as person_key,
                CASE WHEN p.participant_id IS NOT NULL THEN TRUE ELSE FALSE END as is_linked
            FROM matches m
            LEFT JOIN players p ON m.match_id = p.match_id
        )
        SELECT
            COALESCE(pi.map_size, 'Unknown') as map_size,
            COALESCE(pi.map_class, 'Unknown') as map_class,
            COALESCE(pi.map_aspect_ratio, 'Unknown') as map_aspect_ratio,
            COUNT(DISTINCT pi.match_id) as total_matches,
            AVG(pi.total_turns) as avg_turns,
            MIN(pi.total_turns) as min_turns,
            MAX(pi.total_turns) as max_turns,
            -- Count unique people (participants + unlinked player proxies)
            COUNT(DISTINCT pi.person_key) as unique_participants,
            -- Count only linked participants for data quality insight
            COUNT(DISTINCT CASE WHEN pi.is_linked THEN pi.person_key END) as unique_linked_participants,
            -- Count unlinked for data quality insight
            COUNT(DISTINCT CASE WHEN NOT pi.is_linked THEN pi.person_key END) as unique_unlinked_players
        FROM player_identity pi
        GROUP BY
            COALESCE(pi.map_size, 'Unknown'),
            COALESCE(pi.map_class, 'Unknown'),
            COALESCE(pi.map_aspect_ratio, 'Unknown')
        ORDER BY total_matches DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query).df()

    def get_turn_progression_data(self, match_id: int) -> pd.DataFrame:
        """Get turn-by-turn progression data for a specific match.

        DEPRECATED: The game_state table was removed in migration 002 because
        all rows had turn_number=0 (broken data). Use get_event_timeline() or
        the new history tables instead.

        Returns:
            Empty DataFrame with expected columns
        """
        return pd.DataFrame(
            columns=[
                "turn_number",
                "game_year",
                "active_player",
                "civilization",
                "events_count",
            ]
        )

    def get_resource_progression(
        self, match_id: int, player_name: Optional[str] = None
    ) -> pd.DataFrame:
        """Get resource progression over time for a match.

        Args:
            match_id: ID of the match
            player_name: Optional player name to filter by

        Returns:
            DataFrame with resource progression data
        """
        base_query = """
        SELECT
            r.turn_number,
            p.player_name,
            r.resource_type,
            r.amount
        FROM player_yield_history r
        JOIN players p ON r.player_id = p.player_id
        WHERE r.match_id = ?
        """

        params = [match_id]

        if player_name:
            base_query += " AND p.player_name = ?"
            params.append(player_name)

        base_query += " ORDER BY r.turn_number, p.player_name, r.resource_type"

        with self.db.get_connection() as conn:
            return conn.execute(base_query, params).df()

    def get_event_timeline(
        self, match_id: int, event_types: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """Get event timeline for a specific match, including both MemoryData and LogData events.

        Args:
            match_id: ID of the match
            event_types: Optional list of event types to filter by

        Returns:
            DataFrame with event timeline data, showing individual events with better categorization
        """
        # Build the main query to get all events
        # Excludes MEMORYPLAYER_* events as they lack useful context
        base_query = """
        WITH categorized_events AS (
            SELECT
                e.event_id,
                e.turn_number,
                e.event_type,
                p.player_name,
                e.description,
                e.x_coordinate,
                e.y_coordinate,
                CASE
                    WHEN e.event_data IS NOT NULL AND json_extract(e.event_data, '$.family') IS NOT NULL
                        THEN json_extract(e.event_data, '$.family')
                    WHEN e.event_data IS NOT NULL AND json_extract(e.event_data, '$.religion') IS NOT NULL
                        THEN json_extract(e.event_data, '$.religion')
                    ELSE NULL
                END as ambition,
                CASE
                    WHEN e.event_type LIKE 'MEMORY%' THEN 'Memory'
                    ELSE 'Game Log'
                END as event_category,
                CASE
                    -- LogData events get higher priority for display
                    WHEN e.event_type = 'LAW_ADOPTED' THEN 1
                    WHEN e.event_type = 'TECH_DISCOVERED' THEN 2
                    WHEN e.event_type = 'GOAL_STARTED' THEN 3
                    WHEN e.event_type = 'GOAL_FINISHED' THEN 4
                    WHEN e.event_type = 'CITY_FOUNDED' THEN 5
                    WHEN e.event_type = 'WONDER_ACTIVITY' THEN 6
                    WHEN e.event_type = 'CHARACTER_BIRTH' THEN 7
                    WHEN e.event_type = 'CHARACTER_DEATH' THEN 8
                    WHEN e.event_type = 'RELIGION_FOUNDED' THEN 9
                    WHEN e.event_type = 'THEOLOGY_ESTABLISHED' THEN 10
                    WHEN e.event_type LIKE 'TEAM_%' THEN 11
                    WHEN e.event_type LIKE 'TRIBE_%' THEN 12
                    ELSE 99
                END as display_priority
            FROM events e
            LEFT JOIN players p ON e.player_id = p.player_id AND e.match_id = p.match_id
            WHERE e.match_id = ?
                -- Exclude all MEMORYPLAYER_* events as they lack useful context
                AND e.event_type NOT LIKE 'MEMORYPLAYER_%'
        )
        SELECT
            turn_number,
            event_type,
            player_name,
            description,
            x_coordinate,
            y_coordinate,
            ambition,
            event_category
        FROM categorized_events
        WHERE 1=1
        """

        params = [match_id]

        if event_types:
            placeholders = ", ".join(["?" for _ in event_types])
            base_query += f" AND event_type IN ({placeholders})"
            params.extend(event_types)

        base_query += (
            " ORDER BY turn_number DESC, display_priority, event_type, player_name"
        )

        with self.db.get_connection() as conn:
            return conn.execute(base_query, params).df()

    def get_territory_control_summary(self, match_id: int) -> pd.DataFrame:
        """Get territory control summary over time.

        Args:
            match_id: ID of the match

        Returns:
            DataFrame with territory control data
        """
        query = """
        WITH territory_counts AS (
            SELECT
                t.turn_number,
                p.player_name,
                COUNT(*) as controlled_territories
            FROM territories t
            LEFT JOIN players p ON t.owner_player_id = p.player_id
            WHERE t.match_id = ?
            GROUP BY t.turn_number, p.player_name
        )
        SELECT
            turn_number,
            player_name,
            controlled_territories,
            SUM(controlled_territories) OVER (PARTITION BY turn_number) as total_territories
        FROM territory_counts
        ORDER BY turn_number, controlled_territories DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id]).df()

    def get_victory_condition_analysis(self) -> pd.DataFrame:
        """Get analysis of victory conditions and their success rates.

        Returns:
            DataFrame with victory condition analysis
        """
        query = """
        SELECT
            COALESCE(m.victory_conditions, 'Unknown') as victory_conditions,
            COUNT(*) as total_matches,
            AVG(m.total_turns) as avg_turns,
            MIN(m.total_turns) as min_turns,
            MAX(m.total_turns) as max_turns
        FROM matches m
        GROUP BY COALESCE(m.victory_conditions, 'Unknown')
        ORDER BY total_matches DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query).df()

    def get_recent_matches(self, limit: int | None = 10) -> pd.DataFrame:
        """Get most recently processed matches.

        Args:
            limit: Number of matches to return. If None, returns all matches.

        Returns:
            DataFrame with recent match data including player names with nations
        """
        query = """
        WITH ranked_players AS (
            SELECT
                match_id,
                player_name,
                civilization,
                ROW_NUMBER() OVER (PARTITION BY match_id ORDER BY player_id) as player_rank
            FROM players
        )
        SELECT
            m.match_id,
            COALESCE(m.game_name, 'Unknown Game') as game_name,
            m.save_date,
            m.processed_date,
            m.total_turns,
            COALESCE(
                p1.player_name || ' (' || COALESCE(p1.civilization, 'Unknown') || ')',
                'Unknown'
            ) as player1,
            COALESCE(
                p2.player_name || ' (' || COALESCE(p2.civilization, 'Unknown') || ')',
                'Unknown'
            ) as player2,
            COALESCE(w.player_name, 'Unknown') as winner_name,
            COALESCE(
                m.map_size || ' ' || COALESCE(m.map_class, '') || ' ' || COALESCE(m.map_aspect_ratio, ''),
                'Unknown'
            ) as map_info
        FROM matches m
        LEFT JOIN ranked_players p1 ON m.match_id = p1.match_id AND p1.player_rank = 1
        LEFT JOIN ranked_players p2 ON m.match_id = p2.match_id AND p2.player_rank = 2
        LEFT JOIN match_winners mw ON m.match_id = mw.match_id
        LEFT JOIN players w ON mw.winner_player_id = w.player_id
        ORDER BY m.save_date DESC
        """

        if limit is not None:
            query += " LIMIT ?"
            with self.db.get_connection() as conn:
                return conn.execute(query, [limit]).df()
        else:
            with self.db.get_connection() as conn:
                return conn.execute(query).df()

    def get_database_statistics(self) -> Dict[str, Any]:
        """Get comprehensive database statistics.

        Returns:
            Dictionary with database statistics
        """
        stats = {}

        # Table counts
        tables = [
            "matches",
            "players",
            "events",
            "territories",
            "player_yield_history",  # Renamed from resources
            # Note: game_state was removed in migration 002 (had broken data)
        ]
        for table in tables:
            result = self.db.fetch_one(f"SELECT COUNT(*) FROM {table}")
            # Use friendly name for yield history
            key_name = "yield_history" if table == "player_yield_history" else table
            stats[f"{key_name}_count"] = result[0] if result else 0

        # Unique counts
        result = self.db.fetch_one("SELECT COUNT(DISTINCT player_name) FROM players")
        stats["unique_players"] = result[0] if result else 0

        result = self.db.fetch_one(
            "SELECT COUNT(DISTINCT civilization) FROM players WHERE civilization IS NOT NULL"
        )
        stats["unique_civilizations"] = result[0] if result else 0

        # Date ranges
        result = self.db.fetch_one(
            "SELECT MIN(save_date), MAX(save_date) FROM matches WHERE save_date IS NOT NULL"
        )
        if result and result[0]:
            stats["date_range"] = {"earliest": result[0], "latest": result[1]}

        # Turn statistics
        result = self.db.fetch_one(
            "SELECT AVG(total_turns), MIN(total_turns), MAX(total_turns) FROM matches WHERE total_turns > 0"
        )
        if result and result[0]:
            stats["turn_stats"] = {"avg": result[0], "min": result[1], "max": result[2]}

        return stats

    def get_technology_comparison(self, match_id: int) -> pd.DataFrame:
        """Get technology research comparison for all players in a match.

        Args:
            match_id: ID of the match

        Returns:
            DataFrame with technology research data by player
        """
        query = """
        SELECT
            p.player_name,
            p.civilization,
            tp.tech_name,
            tp.count
        FROM technology_progress tp
        JOIN players p ON tp.player_id = p.player_id
        WHERE tp.match_id = ?
        ORDER BY p.player_name, tp.tech_name
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id]).df()

    def get_player_statistics_by_category(
        self, match_id: int, category: Optional[str] = None
    ) -> pd.DataFrame:
        """Get player statistics for a match, optionally filtered by category.

        Args:
            match_id: ID of the match
            category: Optional category filter (e.g., 'STAT_IMPROVEMENTS', 'STAT_PRODUCTION')

        Returns:
            DataFrame with player statistics
        """
        base_query = """
        SELECT
            p.player_name,
            p.civilization,
            ps.stat_category,
            ps.stat_name,
            ps.value
        FROM player_statistics ps
        JOIN players p ON ps.player_id = p.player_id
        WHERE ps.match_id = ?
        """

        params: List[Any] = [match_id]

        if category:
            base_query += " AND ps.stat_category = ?"
            params.append(category)

        base_query += " ORDER BY p.player_name, ps.stat_category, ps.stat_name"

        with self.db.get_connection() as conn:
            return conn.execute(base_query, params).df()

    def get_match_metadata(self, match_id: int) -> Dict[str, Any]:
        """Get detailed match metadata including game settings and options.

        Args:
            match_id: ID of the match

        Returns:
            Dictionary with match metadata
        """
        query = """
        SELECT
            difficulty,
            event_level,
            victory_type,
            victory_turn,
            opponent_level,
            tribe_level,
            development,
            advantage,
            succession_gender,
            succession_order,
            mortality,
            victory_point_modifier,
            game_options,
            dlc_content,
            map_settings
        FROM match_metadata
        WHERE match_id = ?
        """

        result = self.db.fetch_one(query, {"1": match_id})

        if result:
            return {
                "difficulty": result[0],
                "event_level": result[1],
                "victory_type": result[2],
                "victory_turn": result[3],
                "opponent_level": result[4],
                "tribe_level": result[5],
                "development": result[6],
                "advantage": result[7],
                "succession_gender": result[8],
                "succession_order": result[9],
                "mortality": result[10],
                "victory_point_modifier": result[11],
                "game_options": result[12],
                "dlc_content": result[13],
                "map_settings": result[14],
            }

        return {}

    def get_stat_categories(self, match_id: int) -> List[str]:
        """Get list of unique statistic categories available for a match.

        Args:
            match_id: ID of the match

        Returns:
            List of unique stat category names
        """
        query = """
        SELECT DISTINCT stat_category
        FROM player_statistics
        WHERE match_id = ?
        ORDER BY stat_category
        """

        with self.db.get_connection() as conn:
            df = conn.execute(query, [match_id]).df()
            return df["stat_category"].tolist() if not df.empty else []

    def get_technology_summary(self, match_id: int) -> pd.DataFrame:
        """Get aggregated technology research summary by player.

        Args:
            match_id: ID of the match

        Returns:
            DataFrame with total tech counts per player
        """
        query = """
        SELECT
            p.player_name,
            p.civilization,
            COUNT(DISTINCT tp.tech_name) as unique_techs,
            SUM(tp.count) as total_tech_count
        FROM technology_progress tp
        JOIN players p ON tp.player_id = p.player_id
        WHERE tp.match_id = ?
        GROUP BY p.player_name, p.civilization
        ORDER BY total_tech_count DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id]).df()

    def get_law_progression(self, match_id: int) -> pd.DataFrame:
        """Get law progression data for a specific match.

        Args:
            match_id: ID of the match

        Returns:
            DataFrame with law change counts by player
        """
        query = """
        SELECT
            p.player_name,
            p.civilization,
            ps.stat_name as law_type,
            ps.value as law_count
        FROM player_statistics ps
        JOIN players p ON ps.player_id = p.player_id
        WHERE ps.match_id = ?
            AND ps.stat_category = 'law_changes'
            AND ps.value > 0
        ORDER BY p.player_name, ps.stat_name
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id]).df()

    def get_total_laws_by_player(self, match_id: Optional[int] = None) -> pd.DataFrame:
        """Get total law counts by player, optionally filtered by match.

        Args:
            match_id: Optional match ID to filter by

        Returns:
            DataFrame with total law counts per player
        """
        base_query = """
        SELECT
            p.player_name,
            p.civilization,
            m.match_id,
            m.game_name,
            m.total_turns,
            SUM(ps.value) as total_laws
        FROM player_statistics ps
        JOIN players p ON ps.player_id = p.player_id
        JOIN matches m ON ps.match_id = m.match_id
        WHERE ps.stat_category = 'law_changes'
        """

        params: List[Any] = []

        if match_id:
            base_query += " AND ps.match_id = ?"
            params.append(match_id)

        base_query += """
        GROUP BY p.player_name, p.civilization, m.match_id, m.game_name, m.total_turns
        ORDER BY total_laws DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(base_query, params).df()

    def get_law_milestone_timing(self) -> pd.DataFrame:
        """Get timing analysis for law milestones across all matches.

        Calculates when players reach 4 laws and 7 laws based on
        turns per law ratio.

        Returns:
            DataFrame with estimated milestone timing
        """
        query = """
        WITH law_totals AS (
            SELECT
                ps.match_id,
                ps.player_id,
                p.player_name,
                p.civilization,
                m.total_turns,
                m.game_name,
                SUM(ps.value) as total_laws
            FROM player_statistics ps
            JOIN players p ON ps.player_id = p.player_id
            JOIN matches m ON ps.match_id = m.match_id
            WHERE ps.stat_category = 'law_changes'
            GROUP BY ps.match_id, ps.player_id, p.player_name, p.civilization,
                     m.total_turns, m.game_name
            HAVING SUM(ps.value) > 0
        )
        SELECT
            player_name,
            civilization,
            game_name,
            total_turns,
            total_laws,
            CAST(total_turns AS FLOAT) / total_laws as turns_per_law,
            CASE
                WHEN total_laws >= 4
                    THEN CAST((4.0 * total_turns / total_laws) AS INTEGER)
                ELSE NULL
            END as estimated_turn_to_4_laws,
            CASE
                WHEN total_laws >= 7
                    THEN CAST((7.0 * total_turns / total_laws) AS INTEGER)
                ELSE NULL
            END as estimated_turn_to_7_laws
        FROM law_totals
        WHERE total_laws > 0
        ORDER BY turns_per_law ASC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query).df()

    def get_player_law_progression_stats(self) -> pd.DataFrame:
        """Get aggregate law progression statistics per player.

        Returns:
            DataFrame with average law counts and milestone estimates per player
        """
        query = """
        WITH match_laws AS (
            SELECT
                p.player_name_normalized,
                MAX(p.player_name) as player_name,
                ps.match_id,
                m.total_turns,
                SUM(ps.value) as total_laws
            FROM player_statistics ps
            JOIN players p ON ps.player_id = p.player_id
            JOIN matches m ON ps.match_id = m.match_id
            WHERE ps.stat_category = 'law_changes'
            GROUP BY p.player_name_normalized, ps.match_id, m.total_turns
            HAVING SUM(ps.value) > 0
        )
        SELECT
            player_name,
            COUNT(DISTINCT match_id) as matches_played,
            AVG(total_laws) as avg_laws_per_game,
            MAX(total_laws) as max_laws,
            MIN(total_laws) as min_laws,
            AVG(CAST(total_turns AS FLOAT) / total_laws) as avg_turns_per_law,
            AVG(CASE
                WHEN total_laws >= 4
                    THEN CAST((4.0 * total_turns / total_laws) AS INTEGER)
                ELSE NULL
            END) as avg_turn_to_4_laws,
            AVG(CASE
                WHEN total_laws >= 7
                    THEN CAST((7.0 * total_turns / total_laws) AS INTEGER)
                ELSE NULL
            END) as avg_turn_to_7_laws
        FROM match_laws
        GROUP BY player_name_normalized, player_name
        HAVING COUNT(DISTINCT match_id) > 0
        ORDER BY avg_laws_per_game DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query).df()

    def get_nation_win_stats(self) -> pd.DataFrame:
        """Get win statistics by nation/civilization.

        Returns:
            DataFrame with nation, wins, total_matches, win_percentage
        """
        query = """
        SELECT
            COALESCE(p.civilization, 'Unknown') as nation,
            COUNT(CASE WHEN mw.winner_player_id = p.player_id THEN 1 END) as wins,
            COUNT(DISTINCT p.match_id) as total_matches,
            ROUND(
                COUNT(CASE WHEN mw.winner_player_id = p.player_id THEN 1 END) * 100.0 /
                NULLIF(COUNT(DISTINCT p.match_id), 0), 2
            ) as win_percentage
        FROM players p
        LEFT JOIN match_winners mw ON p.match_id = mw.match_id
        GROUP BY p.civilization
        HAVING COUNT(DISTINCT p.match_id) > 0
        ORDER BY wins DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query).df()

    def get_nation_loss_stats(self) -> pd.DataFrame:
        """Get loss statistics by nation/civilization.

        Returns:
            DataFrame with nation, losses, total_matches, loss_percentage
        """
        query = """
        SELECT
            COALESCE(p.civilization, 'Unknown') as nation,
            COUNT(CASE WHEN mw.winner_player_id != p.player_id OR mw.winner_player_id IS NULL THEN 1 END) as losses,
            COUNT(DISTINCT p.match_id) as total_matches,
            ROUND(
                COUNT(CASE WHEN mw.winner_player_id != p.player_id OR mw.winner_player_id IS NULL THEN 1 END) * 100.0 /
                NULLIF(COUNT(DISTINCT p.match_id), 0), 2
            ) as loss_percentage
        FROM players p
        LEFT JOIN match_winners mw ON p.match_id = mw.match_id
        GROUP BY p.civilization
        HAVING COUNT(DISTINCT p.match_id) > 0
        ORDER BY losses DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query).df()

    def get_nation_popularity(self) -> pd.DataFrame:
        """Get nation popularity statistics based on total matches played.

        Returns:
            DataFrame with nation, total_matches
        """
        query = """
        SELECT
            COALESCE(p.civilization, 'Unknown') as nation,
            COUNT(DISTINCT p.match_id) as total_matches
        FROM players p
        GROUP BY p.civilization
        HAVING COUNT(DISTINCT p.match_id) > 0
        ORDER BY total_matches DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query).df()

    def get_map_breakdown(self) -> pd.DataFrame:
        """Get map breakdown statistics by map type, aspect ratio, and size.

        Returns:
            DataFrame with map_class, map_aspect_ratio, map_size, count
        """
        query = """
        SELECT
            COALESCE(map_class, 'Unknown') as map_class,
            COALESCE(map_aspect_ratio, 'Unknown') as map_aspect_ratio,
            COALESCE(map_size, 'Unknown') as map_size,
            COUNT(*) as count
        FROM matches
        GROUP BY map_class, map_aspect_ratio, map_size
        HAVING COUNT(*) > 0
        ORDER BY count DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query).df()

    def get_unit_popularity(self) -> pd.DataFrame:
        """Get unit popularity statistics with category and role classification.

        Returns:
            DataFrame with category, role, unit_type, total_count
        """
        query = """
        SELECT
            COALESCE(uc.category, 'Unknown') as category,
            COALESCE(uc.role, 'Unknown') as role,
            up.unit_type,
            SUM(up.count) as total_count
        FROM units_produced up
        LEFT JOIN unit_classifications uc ON up.unit_type = uc.unit_type
        GROUP BY uc.category, uc.role, up.unit_type
        HAVING SUM(up.count) > 0
        ORDER BY uc.category, uc.role, total_count DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query).df()

    def get_law_progression_by_match(
        self, match_id: Optional[int] = None
    ) -> pd.DataFrame:
        """Get law progression for players, showing when they reached 4 and 7 laws.

        Groups by tournament participant when available. When called without match_id,
        aggregates across all matches to show how people (not player instances)
        progress through laws.

        Args:
            match_id: Optional match_id to filter (None for all matches)

        Returns:
            DataFrame with columns:
                - match_id: Match ID
                - player_id: Database player ID (match-scoped)
                - player_name: Display name (participant name if linked, else player name)
                - participant_id: Participant ID (NULL if unlinked)
                - is_unlinked: Boolean, TRUE if not linked to participant
                - civilization: Civilization played
                - turn_to_4_laws: Turn number when 4th law adopted (NULL if <4 laws)
                - turn_to_7_laws: Turn number when 7th law adopted (NULL if <7 laws)
                - total_laws: Total laws adopted in this match
        """
        match_filter = "AND e.match_id = ?" if match_id else ""

        query = f"""
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
            -- Prefer participant name over player name
            COALESCE(tp.display_name, p.player_name) as player_name,
            p.participant_id,
            CASE WHEN p.participant_id IS NULL THEN TRUE ELSE FALSE END as is_unlinked,
            p.civilization,
            m.turn_to_4_laws,
            m.turn_to_7_laws,
            m.total_laws
        FROM milestones m
        JOIN players p ON m.match_id = p.match_id AND m.player_id = p.player_id
        LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
        ORDER BY m.match_id, m.player_id
        """

        params = [match_id] if match_id else []

        with self.db.get_connection() as conn:
            return conn.execute(query, params).df()

    def get_tech_timeline_by_match(self, match_id: int) -> pd.DataFrame:
        """Get chronological tech discoveries for a match.

        Args:
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

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id]).df()

    def get_tech_count_by_turn(self, match_id: int) -> pd.DataFrame:
        """Get cumulative tech count by turn for each player.

        Useful for racing line charts showing tech progression over time.

        Args:
            match_id: Match ID to analyze

        Returns:
            DataFrame with columns: player_id, player_name, turn_number, cumulative_techs, tech_list, new_techs
        """
        query = """
        WITH tech_events AS (
            SELECT
                e.player_id,
                p.player_name,
                e.turn_number,
                e.event_id,
                json_extract(e.event_data, '$.tech') as tech_name,
                COUNT(*) OVER (
                    PARTITION BY e.player_id
                    ORDER BY e.turn_number, e.event_id
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) as cumulative_techs
            FROM events e
            JOIN players p ON e.match_id = p.match_id AND e.player_id = p.player_id
            WHERE e.event_type = 'TECH_DISCOVERED'
                AND e.match_id = ?
        ),
        techs_up_to_turn AS (
            SELECT
                te1.player_id,
                te1.player_name,
                te1.turn_number,
                te1.cumulative_techs,
                te1.event_id,
                string_agg(te2.tech_name, ', ') FILTER (WHERE te2.tech_name IS NOT NULL) as tech_list
            FROM tech_events te1
            LEFT JOIN tech_events te2 ON te1.player_id = te2.player_id
                AND te2.event_id <= te1.event_id
            GROUP BY te1.player_id, te1.player_name, te1.turn_number, te1.cumulative_techs, te1.event_id
        ),
        new_techs_this_turn AS (
            SELECT
                te1.player_id,
                te1.turn_number,
                te1.event_id,
                string_agg(te2.tech_name, ', ') FILTER (WHERE te2.tech_name IS NOT NULL) as new_techs
            FROM tech_events te1
            LEFT JOIN tech_events te2 ON te1.player_id = te2.player_id
                AND te2.turn_number = te1.turn_number
                AND te2.event_id <= te1.event_id
            GROUP BY te1.player_id, te1.turn_number, te1.event_id
        )
        SELECT
            tut.player_id,
            tut.player_name,
            tut.turn_number,
            MAX(tut.cumulative_techs) as cumulative_techs,
            MAX(tut.tech_list) as tech_list,
            MAX(ntt.new_techs) as new_techs
        FROM techs_up_to_turn tut
        LEFT JOIN new_techs_this_turn ntt ON tut.player_id = ntt.player_id
            AND tut.turn_number = ntt.turn_number
            AND tut.event_id = ntt.event_id
        GROUP BY tut.player_id, tut.player_name, tut.turn_number
        ORDER BY tut.player_id, tut.turn_number
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id]).df()

    def get_cumulative_law_count_by_turn(self, match_id: int) -> pd.DataFrame:
        """Get cumulative law count by turn for each player.

        Similar to get_tech_count_by_turn, but for laws. Shows participant names
        when available for consistency with other UI elements.

        Args:
            match_id: Match ID to analyze

        Returns:
            DataFrame with columns:
                - player_id: Database player ID
                - player_name: Display name (participant if linked, else player name)
                - participant_id: Participant ID (NULL if unlinked)
                - turn_number: Turn when law was adopted
                - cumulative_laws: Total laws up to this turn
                - law_list: Comma-separated list of all laws adopted
                - new_laws: Comma-separated list of laws adopted this turn
        """
        query = """
        WITH law_events AS (
            SELECT
                e.player_id,
                -- Prefer participant name from join
                COALESCE(tp.display_name, p.player_name) as player_name,
                p.participant_id,
                e.turn_number,
                e.event_id,
                json_extract(e.event_data, '$.law') as law_name,
                ROW_NUMBER() OVER (
                    PARTITION BY e.player_id
                    ORDER BY e.turn_number, e.event_id
                ) as cumulative_laws
            FROM events e
            JOIN players p ON e.match_id = p.match_id AND e.player_id = p.player_id
            LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
            WHERE e.event_type = 'LAW_ADOPTED'
                AND e.match_id = ?
        ),
        laws_up_to_turn AS (
            SELECT
                le1.player_id,
                le1.player_name,
                le1.participant_id,
                le1.turn_number,
                le1.cumulative_laws,
                le1.event_id,
                string_agg(le2.law_name, ', ') FILTER (WHERE le2.law_name IS NOT NULL) as law_list
            FROM law_events le1
            LEFT JOIN law_events le2 ON le1.player_id = le2.player_id
                AND le2.event_id <= le1.event_id
            GROUP BY le1.player_id, le1.player_name, le1.participant_id, le1.turn_number, le1.cumulative_laws, le1.event_id
        ),
        new_laws_this_turn AS (
            SELECT
                le1.player_id,
                le1.turn_number,
                le1.event_id,
                string_agg(le2.law_name, ', ') FILTER (WHERE le2.law_name IS NOT NULL) as new_laws
            FROM law_events le1
            LEFT JOIN law_events le2 ON le1.player_id = le2.player_id
                AND le2.turn_number = le1.turn_number
                AND le2.event_id <= le1.event_id
            GROUP BY le1.player_id, le1.turn_number, le1.event_id
        )
        SELECT DISTINCT
            lut.player_id,
            lut.player_name,
            lut.participant_id,
            lut.turn_number,
            lut.cumulative_laws,
            lut.law_list,
            nlt.new_laws
        FROM laws_up_to_turn lut
        LEFT JOIN new_laws_this_turn nlt ON lut.player_id = nlt.player_id
            AND lut.turn_number = nlt.turn_number
            AND lut.event_id = nlt.event_id
        ORDER BY lut.player_id, lut.turn_number, lut.cumulative_laws
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id]).df()

    def get_points_history_by_match(self, match_id: int) -> pd.DataFrame:
        """Get victory points progression for all players in a match.

        Returns data from the player_points_history table which tracks
        turn-by-turn victory point totals for each player.

        Args:
            match_id: Match ID to query

        Returns:
            DataFrame with columns:
            - player_id: Database player ID
            - player_name: Player name
            - turn_number: Turn number
            - points: Victory points at that turn

        Example usage:
            df = queries.get_points_history_by_match(1)
            # Create a line chart with turn_number on x-axis, points on y-axis,
            # with separate lines for each player_name
        """
        query = """
        SELECT
            ph.player_id,
            p.player_name,
            p.civilization,
            ph.turn_number,
            ph.points
        FROM player_points_history ph
        JOIN players p ON ph.player_id = p.player_id AND ph.match_id = p.match_id
        WHERE ph.match_id = ?
        ORDER BY ph.turn_number, ph.player_id
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id]).df()

    def get_points_history_all_matches(self) -> pd.DataFrame:
        """Get victory points progression across all matches.

        Useful for aggregate analysis like "how do points typically progress?"

        Returns:
            DataFrame with match_id, player_id, player_name, turn_number, points
        """
        query = """
        SELECT
            ph.match_id,
            ph.player_id,
            p.player_name,
            p.civilization,
            ph.turn_number,
            ph.points
        FROM player_points_history ph
        JOIN players p ON ph.player_id = p.player_id AND ph.match_id = p.match_id
        ORDER BY ph.match_id, ph.turn_number, ph.player_id
        """

        with self.db.get_connection() as conn:
            return conn.execute(query).df()

    def get_yield_history_by_match(
        self, match_id: int, yield_types: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """Get yield production progression for all players in a match.

        Returns data from player_yield_history showing turn-by-turn
        yield production rates (YIELD_GROWTH, YIELD_CIVICS, etc.)

        Args:
            match_id: Match ID to query
            yield_types: Optional list of yield types to filter
                        (e.g., ['YIELD_GROWTH', 'YIELD_SCIENCE'])
                        If None, returns all yield types.

        Returns:
            DataFrame with columns:
            - player_id, player_name, civilization
            - turn_number
            - resource_type: The yield type (YIELD_GROWTH, etc.)
            - amount: Production rate for that yield on that turn
        """
        base_query = """
        SELECT
            yh.player_id,
            p.player_name,
            p.civilization,
            yh.turn_number,
            yh.resource_type,
            yh.amount
        FROM player_yield_history yh
        JOIN players p ON yh.player_id = p.player_id AND yh.match_id = p.match_id
        WHERE yh.match_id = ?
        """

        params = [match_id]

        if yield_types:
            placeholders = ", ".join(["?" for _ in yield_types])
            base_query += f" AND yh.resource_type IN ({placeholders})"
            params.extend(yield_types)

        base_query += " ORDER BY yh.turn_number, yh.player_id, yh.resource_type"

        with self.db.get_connection() as conn:
            return conn.execute(base_query, params).df()

    def get_yield_types(self, match_id: Optional[int] = None) -> List[str]:
        """Get list of available yield types.

        Args:
            match_id: Optional match ID to filter by. If None, returns all yield types
                     across all matches.

        Returns:
            List of yield type names (e.g., ['YIELD_GROWTH', 'YIELD_CIVICS', ...])
        """
        if match_id:
            query = """
            SELECT DISTINCT resource_type
            FROM player_yield_history
            WHERE match_id = ?
            ORDER BY resource_type
            """
            params = [match_id]
        else:
            query = """
            SELECT DISTINCT resource_type
            FROM player_yield_history
            ORDER BY resource_type
            """
            params = []

        with self.db.get_connection() as conn:
            df = conn.execute(query, params).df()
            return df["resource_type"].tolist() if not df.empty else []

    def get_military_history_by_match(self, match_id: int) -> pd.DataFrame:
        """Get military power progression for all players in a match.

        Returns data from player_military_history showing turn-by-turn
        military strength values.

        Args:
            match_id: Match ID to query

        Returns:
            DataFrame with columns:
            - player_id, player_name, civilization
            - turn_number
            - military_power: Military strength value for that turn
        """
        query = """
        SELECT
            mh.player_id,
            p.player_name,
            p.civilization,
            mh.turn_number,
            mh.military_power
        FROM player_military_history mh
        JOIN players p ON mh.player_id = p.player_id AND mh.match_id = p.match_id
        WHERE mh.match_id = ?
        ORDER BY mh.turn_number, mh.player_id
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id]).df()

    def get_legitimacy_history_by_match(self, match_id: int) -> pd.DataFrame:
        """Get legitimacy progression for all players in a match.

        Returns data from player_legitimacy_history showing turn-by-turn
        legitimacy values (governance stability, 0-100).

        Args:
            match_id: Match ID to query

        Returns:
            DataFrame with columns:
            - player_id, player_name, civilization
            - turn_number
            - legitimacy: Legitimacy value (0-100) for that turn
        """
        query = """
        SELECT
            lh.player_id,
            p.player_name,
            p.civilization,
            lh.turn_number,
            lh.legitimacy
        FROM player_legitimacy_history lh
        JOIN players p ON lh.player_id = p.player_id AND lh.match_id = p.match_id
        WHERE lh.match_id = ?
        ORDER BY lh.turn_number, lh.player_id
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id]).df()

    def get_family_opinion_history_by_match(
        self, match_id: int, family_names: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """Get family opinion progression for all players in a match.

        Returns data from family_opinion_history showing turn-by-turn
        family opinion values (0-100) for each family.

        Args:
            match_id: Match ID to query
            family_names: Optional list of family names to filter
                         (e.g., ['FAMILY_JULII', 'FAMILY_BRUTII'])

        Returns:
            DataFrame with columns:
            - player_id, player_name, civilization
            - turn_number
            - family_name: Name of the family (e.g., 'FAMILY_JULII')
            - opinion: Opinion value (0-100) for that family on that turn
        """
        base_query = """
        SELECT
            fh.player_id,
            p.player_name,
            p.civilization,
            fh.turn_number,
            fh.family_name,
            fh.opinion
        FROM family_opinion_history fh
        JOIN players p ON fh.player_id = p.player_id AND fh.match_id = p.match_id
        WHERE fh.match_id = ?
        """

        params = [match_id]

        if family_names:
            placeholders = ", ".join(["?" for _ in family_names])
            base_query += f" AND fh.family_name IN ({placeholders})"
            params.extend(family_names)

        base_query += " ORDER BY fh.turn_number, fh.player_id, fh.family_name"

        with self.db.get_connection() as conn:
            return conn.execute(base_query, params).df()

    def get_family_names(self, match_id: Optional[int] = None) -> List[str]:
        """Get list of family names that appear in the data.

        Args:
            match_id: Optional match ID to filter by

        Returns:
            List of family names (e.g., ['FAMILY_JULII', 'FAMILY_BRUTII', ...])
        """
        if match_id:
            query = """
            SELECT DISTINCT family_name
            FROM family_opinion_history
            WHERE match_id = ?
            ORDER BY family_name
            """
            params = [match_id]
        else:
            query = """
            SELECT DISTINCT family_name
            FROM family_opinion_history
            ORDER BY family_name
            """
            params = []

        with self.db.get_connection() as conn:
            df = conn.execute(query, params).df()
            return df["family_name"].tolist() if not df.empty else []

    def get_religion_opinion_history_by_match(
        self, match_id: int, religion_names: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """Get religion opinion progression for all players in a match.

        Returns data from religion_opinion_history showing turn-by-turn
        religion opinion values (0-100) for each religion.

        Args:
            match_id: Match ID to query
            religion_names: Optional list of religion names to filter
                           (e.g., ['RELIGION_JUPITER', 'RELIGION_BAAL'])

        Returns:
            DataFrame with columns:
            - player_id, player_name, civilization
            - turn_number
            - religion_name: Name of the religion
            - opinion: Opinion value (0-100) for that religion on that turn
        """
        base_query = """
        SELECT
            rh.player_id,
            p.player_name,
            p.civilization,
            rh.turn_number,
            rh.religion_name,
            rh.opinion
        FROM religion_opinion_history rh
        JOIN players p ON rh.player_id = p.player_id AND rh.match_id = p.match_id
        WHERE rh.match_id = ?
        """

        params = [match_id]

        if religion_names:
            placeholders = ", ".join(["?" for _ in religion_names])
            base_query += f" AND rh.religion_name IN ({placeholders})"
            params.extend(religion_names)

        base_query += " ORDER BY rh.turn_number, rh.player_id, rh.religion_name"

        with self.db.get_connection() as conn:
            return conn.execute(base_query, params).df()

    def get_religion_names(self, match_id: Optional[int] = None) -> List[str]:
        """Get list of religion names that appear in the data.

        Args:
            match_id: Optional match ID to filter by

        Returns:
            List of religion names (e.g., ['RELIGION_JUPITER', 'RELIGION_BAAL', ...])
        """
        if match_id:
            query = """
            SELECT DISTINCT religion_name
            FROM religion_opinion_history
            WHERE match_id = ?
            ORDER BY religion_name
            """
            params = [match_id]
        else:
            query = """
            SELECT DISTINCT religion_name
            FROM religion_opinion_history
            ORDER BY religion_name
            """
            params = []

        with self.db.get_connection() as conn:
            df = conn.execute(query, params).df()
            return df["religion_name"].tolist() if not df.empty else []

    def get_techs_at_law_milestone(
        self, match_id: int, milestone: int = 4
    ) -> pd.DataFrame:
        """Get list of techs each player had when reaching a law milestone.

        Args:
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

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id, milestone]).df()

    def get_aggregated_event_timeline(self, max_turn: int = 150) -> pd.DataFrame:
        """Get aggregated event timeline across all matches.

        Returns average event counts by turn and event type, normalized
        across all matches. Useful for showing typical event patterns.

        Args:
            max_turn: Maximum turn number to include (default 150)

        Returns:
            DataFrame with columns: turn_number, event_type, avg_event_count
        """
        query = """
        WITH all_events AS (
            SELECT
                e.match_id,
                e.turn_number,
                e.event_type
            FROM events e
            WHERE e.turn_number <= ?
                AND e.event_type NOT LIKE 'MEMORYPLAYER_%'
        ),
        match_turn_combinations AS (
            SELECT DISTINCT
                m.match_id,
                t.turn_number
            FROM matches m
            CROSS JOIN (
                SELECT DISTINCT turn_number
                FROM all_events
            ) t
            WHERE t.turn_number <= m.total_turns
        ),
        event_counts_per_match_turn AS (
            SELECT
                mtc.match_id,
                mtc.turn_number,
                ae.event_type,
                COUNT(ae.event_type) as event_count
            FROM match_turn_combinations mtc
            LEFT JOIN all_events ae ON mtc.match_id = ae.match_id
                AND mtc.turn_number = ae.turn_number
            GROUP BY mtc.match_id, mtc.turn_number, ae.event_type
        )
        SELECT
            turn_number,
            event_type,
            AVG(event_count) as avg_event_count
        FROM event_counts_per_match_turn
        WHERE event_type IS NOT NULL
        GROUP BY turn_number, event_type
        HAVING AVG(event_count) > 0
        ORDER BY turn_number, event_type
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [max_turn]).df()

    def get_ambition_timeline(self, match_id: int) -> pd.DataFrame:
        """Get ambition/goal timeline for a specific match.

        Returns all GOAL_* events (started, finished, failed) for visualization.

        Args:
            match_id: Match ID to analyze

        Returns:
            DataFrame with columns: player_id, player_name, turn_number,
                                    event_type, status, description
        """
        query = """
        SELECT
            e.player_id,
            p.player_name,
            p.civilization,
            e.turn_number,
            e.event_type,
            CASE
                WHEN e.event_type = 'GOAL_STARTED' THEN 'Started'
                WHEN e.event_type = 'GOAL_FINISHED' THEN 'Completed'
                WHEN e.event_type = 'GOAL_FAILED' THEN 'Failed'
            END as status,
            e.description
        FROM events e
        JOIN players p ON e.match_id = p.match_id AND e.player_id = p.player_id
        WHERE e.match_id = ?
            AND e.event_type IN ('GOAL_STARTED', 'GOAL_FINISHED', 'GOAL_FAILED')
        ORDER BY e.turn_number, e.player_id, e.event_type
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id]).df()

    def get_ambition_summary(self, match_id: int) -> pd.DataFrame:
        """Get ambition summary statistics by player.

        Args:
            match_id: Match ID to analyze

        Returns:
            DataFrame with columns: player_name, started, completed, failed, completion_rate
        """
        query = """
        WITH ambition_counts AS (
            SELECT
                p.player_name,
                p.civilization,
                COUNT(CASE WHEN e.event_type = 'GOAL_STARTED' THEN 1 END) as started,
                COUNT(CASE WHEN e.event_type = 'GOAL_FINISHED' THEN 1 END) as completed,
                COUNT(CASE WHEN e.event_type = 'GOAL_FAILED' THEN 1 END) as failed
            FROM events e
            JOIN players p ON e.match_id = p.match_id AND e.player_id = p.player_id
            WHERE e.match_id = ?
                AND e.event_type IN ('GOAL_STARTED', 'GOAL_FINISHED', 'GOAL_FAILED')
            GROUP BY p.player_name, p.civilization
        )
        SELECT
            player_name,
            civilization,
            started,
            completed,
            failed,
            CASE
                WHEN started > 0 THEN ROUND(completed * 100.0 / started, 1)
                ELSE 0
            END as completion_rate
        FROM ambition_counts
        ORDER BY completed DESC, started DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id]).df()

    def get_ruler_archetype_win_rates(self) -> pd.DataFrame:
        """Get win rates by starting ruler archetype.

        Analyzes starting rulers only (succession_order = 0) to show which
        archetypes correlate with victory.

        Returns:
            DataFrame with columns:
            - archetype: Ruler archetype name
            - games: Total games played with this archetype
            - wins: Number of wins
            - win_rate: Win percentage (0-100)
        """
        query = """
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

        with self.db.get_connection() as conn:
            return conn.execute(query).df()

    def get_ruler_trait_win_rates(self, min_games: int = 2) -> pd.DataFrame:
        """Get win rates by starting ruler trait.

        Analyzes starting traits chosen at game initialization to show which
        traits correlate with victory.

        Args:
            min_games: Minimum number of games required to include trait (default 2)

        Returns:
            DataFrame with columns:
            - starting_trait: Trait name
            - games: Total games played with this trait
            - wins: Number of wins
            - win_rate: Win percentage (0-100)
        """
        query = """
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
        HAVING COUNT(*) >= ?
        ORDER BY win_rate DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [min_games]).df()

    def get_ruler_succession_impact(self) -> pd.DataFrame:
        """Get correlation between ruler succession count and victory.

        Analyzes whether having more/fewer rulers correlates with winning.

        Returns:
            DataFrame with columns:
            - succession_category: Grouped ruler count (e.g., '2 rulers')
            - games: Total games in this category
            - wins: Number of wins
            - win_rate: Win percentage (0-100)
        """
        query = """
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
            END as succession_category,
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
        ORDER BY
            CASE succession_category
                WHEN '1 ruler' THEN 1
                WHEN '2 rulers' THEN 2
                WHEN '3 rulers' THEN 3
                WHEN '4+ rulers' THEN 4
            END
        """

        with self.db.get_connection() as conn:
            return conn.execute(query).df()

    def get_ruler_archetype_matchups(self) -> pd.DataFrame:
        """Get win rates for archetype vs archetype matchups.

        Analyzes head-to-head performance between starting ruler archetypes
        to identify favorable and unfavorable matchups.

        Returns:
            DataFrame with columns:
            - archetype: The archetype (row in matrix)
            - opponent_archetype: The opposing archetype (column in matrix)
            - games: Number of games with this matchup
            - wins: Number of wins for archetype
            - win_rate: Win percentage for archetype (0-100)
        """
        query = """
        WITH matchups AS (
            -- Get all matchups in both directions
            SELECT
                r1.archetype as archetype,
                r2.archetype as opponent_archetype,
                CASE WHEN mw.winner_player_id = r1.player_id THEN 1 ELSE 0 END as won
            FROM rulers r1
            JOIN rulers r2 ON r1.match_id = r2.match_id AND r1.player_id != r2.player_id
            JOIN match_winners mw ON r1.match_id = mw.match_id
            WHERE r1.succession_order = 0 AND r2.succession_order = 0
            AND r1.archetype IS NOT NULL AND r2.archetype IS NOT NULL
        )
        SELECT
            archetype,
            opponent_archetype,
            COUNT(*) as games,
            SUM(won) as wins,
            ROUND(SUM(won) * 100.0 / COUNT(*), 2) as win_rate
        FROM matchups
        GROUP BY archetype, opponent_archetype
        ORDER BY archetype, opponent_archetype
        """

        with self.db.get_connection() as conn:
            return conn.execute(query).df()

    def get_ruler_archetype_trait_combinations(self, limit: int = 10) -> pd.DataFrame:
        """Get most popular archetype + trait combinations for starting rulers.

        Args:
            limit: Maximum number of combinations to return (default 10)

        Returns:
            DataFrame with columns:
            - archetype: Ruler archetype name
            - starting_trait: Starting trait name
            - count: Number of times this combo was chosen
        """
        query = """
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
        LIMIT ?
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [limit]).df()


# Global queries instance
queries = TournamentQueries()


def get_queries() -> TournamentQueries:
    """Get the global queries instance.

    Returns:
        TournamentQueries instance
    """
    return queries
