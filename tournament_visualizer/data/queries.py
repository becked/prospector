"""Reusable SQL queries for tournament data analysis.

This module contains predefined SQL queries for common data analysis tasks
in the tournament visualization application.
"""

from typing import Any, Dict, List, Literal, Optional, Tuple

import pandas as pd

from ..config import FAMILY_CLASS_MAP, get_family_class
from .database import TournamentDatabase, get_database

# Type alias for result filtering (winners/losers)
ResultFilter = Literal["all", "winners", "losers"] | None

# =============================================================================
# Science Generation Constants (from docs/science-generation-guide.md)
# =============================================================================
# All values are RAW XML values (divide by 10 for in-game display)

# Specialist tier-based science (all specialists produce science from their tier)
SPECIALIST_TIER_SCIENCE: Dict[str, int] = {
    "rural": 10,  # Farmer, Miner, Woodcutter, etc.
    "apprentice": 20,  # All tier 1 urban specialists
    "master": 30,  # All tier 2 urban specialists
    "elder": 40,  # All tier 3 urban specialists
}

# Rural specialists (all produce 10 science)
RURAL_SPECIALISTS: List[str] = [
    "SPECIALIST_FARMER",
    "SPECIALIST_MINER",
    "SPECIALIST_STONECUTTER",
    "SPECIALIST_WOODCUTTER",
    "SPECIALIST_RANCHER",
    "SPECIALIST_TRAPPER",
    "SPECIALIST_GARDENER",
    "SPECIALIST_FISHER",
]

# Direct science production values per turn (specialists with bonuses + improvements)
SCIENCE_VALUES: Dict[str, int] = {
    # Philosophers: tier + bonus (20+20, 30+30, 40+40)
    "SPECIALIST_PHILOSOPHER_1": 40,
    "SPECIALIST_PHILOSOPHER_2": 60,
    "SPECIALIST_PHILOSOPHER_3": 80,
    # Doctors: tier + bonus (20+0, 30+10, 40+20)
    "SPECIALIST_DOCTOR_1": 20,
    "SPECIALIST_DOCTOR_2": 40,
    "SPECIALIST_DOCTOR_3": 60,
    # Other urban specialists by tier (tier science only, no bonus)
    # Tier 1 (Apprentice) - 20 each
    "SPECIALIST_ACOLYTE_1": 20,
    "SPECIALIST_MONK_1": 20,
    "SPECIALIST_PRIEST_1": 20,
    "SPECIALIST_OFFICER_1": 20,
    "SPECIALIST_POET_1": 20,
    "SPECIALIST_SCRIBE_1": 20,
    "SPECIALIST_SHOPKEEPER_1": 20,
    "SPECIALIST_BISHOP_1": 20,
    # Tier 2 (Master) - 30 each
    "SPECIALIST_ACOLYTE_2": 30,
    "SPECIALIST_MONK_2": 30,
    "SPECIALIST_PRIEST_2": 30,
    "SPECIALIST_OFFICER_2": 30,
    "SPECIALIST_POET_2": 30,
    "SPECIALIST_SCRIBE_2": 30,
    "SPECIALIST_SHOPKEEPER_2": 30,
    "SPECIALIST_BISHOP_2": 30,
    # Tier 3 (Elder) - 40 each
    "SPECIALIST_ACOLYTE_3": 40,
    "SPECIALIST_MONK_3": 40,
    "SPECIALIST_PRIEST_3": 40,
    "SPECIALIST_OFFICER_3": 40,
    "SPECIALIST_POET_3": 40,
    "SPECIALIST_SCRIBE_3": 40,
    "SPECIALIST_SHOPKEEPER_3": 40,
    "SPECIALIST_BISHOP_3": 40,
    # Rural specialists - 10 each
    "SPECIALIST_FARMER": 10,
    "SPECIALIST_MINER": 10,
    "SPECIALIST_STONECUTTER": 10,
    "SPECIALIST_WOODCUTTER": 10,
    "SPECIALIST_RANCHER": 10,
    "SPECIALIST_TRAPPER": 10,
    "SPECIALIST_GARDENER": 10,
    "SPECIALIST_FISHER": 10,
    # Improvements (science per turn)
    "IMPROVEMENT_WATERMILL": 20,
    "IMPROVEMENT_WINDMILL": 20,
    "IMPROVEMENT_MONASTERY_CHRISTIANITY": 20,
    "IMPROVEMENT_MONASTERY_JUDAISM": 20,
    "IMPROVEMENT_MONASTERY_MANICHAEISM": 20,
    "IMPROVEMENT_MONASTERY_ZOROASTRIANISM": 20,
    "IMPROVEMENT_SHRINE_NABU": 10,
    "IMPROVEMENT_SHRINE_ATHENA": 10,
    # City Projects (cumulative science per turn - only highest tier is stored)
    "PROJECT_ARCHIVE_1": 10,  # Cumulative: 10
    "PROJECT_ARCHIVE_2": 30,  # Cumulative: 10 + 20 = 30
    "PROJECT_ARCHIVE_3": 70,  # Cumulative: 10 + 20 + 40 = 70
    "PROJECT_ARCHIVE_4": 150,  # Cumulative: 10 + 20 + 40 + 80 = 150
}

# Science modifier percentages (additive)
SCIENCE_MODIFIERS: Dict[str, int] = {
    "IMPROVEMENT_LIBRARY_1": 10,  # +10%
    "IMPROVEMENT_LIBRARY_2": 20,  # +20%
    "IMPROVEMENT_LIBRARY_3": 30,  # +30%
    "IMPROVEMENT_MUSAEUM": 50,  # +50%
    "PROJECT_SCIENTIFIC_METHOD": 10,  # +10%
}

# Sages family names (provide +10 science per specialist in their cities)
SAGES_FAMILIES: List[str] = [
    "FAMILY_AMORITE",  # Babylonia
    "FAMILY_THUTMOSID",  # Egypt
    "FAMILY_ALCMAEONID",  # Greece
]

# Clerics family names (provide science modifiers via steles: +10/25/50%)
CLERICS_FAMILIES: List[str] = [
    "FAMILY_ERISHUM",  # Assyria
    "FAMILY_AMARNA",  # Egypt
    "FAMILY_SASANID",  # Persia
    "FAMILY_AKSUM_TIGRAYAN",  # Aksum
]

# Science-affecting laws
SCIENCE_LAWS: Dict[str, Dict[str, Any]] = {
    "LAW_CENTRALIZATION": {"bonus": 20, "scope": "capital"},
    "LAW_CONSTITUTION": {"bonus": 10, "scope": "urban_specialists"},
    "LAW_PHILOSOPHY": {"bonus": 10, "scope": "forums"},
}

# Nation with science bonus
SCIENCE_NATIONS: Dict[str, int] = {
    "Babylonia": 10,  # +10 science per turn all cities
}

# Archetype bonuses affecting science
ARCHETYPE_BONUSES: Dict[str, Dict[str, Any]] = {
    "Scholar": {"archive_bonus": 20},  # +20 per Archive project while Scholar is ruling
}

# Character trait bonuses affecting science
TRAIT_BONUSES: Dict[str, Dict[str, Any]] = {
    "Intelligent": {"governed_city": 10},  # +10 science to city governed by character
}


class TournamentQueries:
    """Collection of reusable queries for tournament data analysis."""

    def __init__(self, database: Optional[TournamentDatabase] = None) -> None:
        """Initialize with database connection.

        Args:
            database: Database instance to use (defaults to global instance)
        """
        self.db = database or get_database()
        # Cache for get_match_summary() - stores (timestamp, dataframe)
        self._match_summary_cache: Optional[tuple[float, pd.DataFrame]] = None
        self._match_summary_cache_ttl: float = 60.0  # seconds

    def get_match_summary(self) -> pd.DataFrame:
        """Get comprehensive match summary data.

        Results are cached for 60 seconds to avoid redundant queries.

        Returns:
            DataFrame with match summary information including player nations
        """
        import time

        now = time.time()

        # Return cached result if valid
        if self._match_summary_cache is not None:
            cached_time, cached_df = self._match_summary_cache
            if now - cached_time < self._match_summary_cache_ttl:
                return cached_df.copy()

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
            m.processed_date,
            COALESCE(first_picker.display_name, 'Unknown') as first_picker_name,
            m.first_picker_participant_id
        FROM matches m
        LEFT JOIN players p ON m.match_id = p.match_id
        LEFT JOIN match_winners mw ON m.match_id = mw.match_id
        LEFT JOIN players w ON mw.winner_player_id = w.player_id
        LEFT JOIN player_info pi ON m.match_id = pi.match_id
        LEFT JOIN tournament_participants first_picker ON m.first_picker_participant_id = first_picker.participant_id
        GROUP BY m.match_id, m.game_name, m.save_date, m.total_turns,
                 m.map_size, m.map_class, m.turn_style, m.victory_conditions,
                 w.player_name, w.civilization, pi.players_with_nations, m.processed_date,
                 first_picker.display_name, m.first_picker_participant_id
        ORDER BY m.save_date DESC NULLS LAST, m.processed_date DESC
        """

        with self.db.get_connection() as conn:
            result = conn.execute(query).df()

        self._match_summary_cache = (now, result)
        return result.copy()

    def invalidate_match_summary_cache(self) -> None:
        """Invalidate the match summary cache.

        Call this after data imports or database changes to ensure fresh data.
        """
        self._match_summary_cache = None

    def get_match_narratives(self, match_id: int) -> dict[str, str | None]:
        """Get narrative texts for a match.

        Args:
            match_id: Match database ID

        Returns:
            Dict with keys: match_narrative, p1_narrative, p2_narrative.
            Values are None if not yet generated.
        """
        query = """
            SELECT narrative_summary, p1_narrative, p2_narrative
            FROM matches
            WHERE match_id = ?
        """
        with self.db.get_connection() as conn:
            result = conn.execute(query, [match_id]).fetchone()

        if not result:
            return {
                "match_narrative": None,
                "p1_narrative": None,
                "p2_narrative": None,
            }

        return {
            "match_narrative": result[0],
            "p1_narrative": result[1],
            "p2_narrative": result[2],
        }

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

        WARNING: This query is currently unused. If you activate it in the future,
        remember to apply the yield scale transformation (/ 10.0) to any yield
        values returned from player_yield_history table.

        See: docs/reports/yield-fix-implementation-summary.md
        TODO: Apply /10.0 transformation if this query is activated

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
        WITH player_order AS (
            SELECT
                match_id,
                player_id,
                player_name,
                ROW_NUMBER() OVER (PARTITION BY match_id ORDER BY player_id) as match_player_order
            FROM players
        ),
        territory_counts AS (
            SELECT
                t.turn_number,
                p.player_name,
                COUNT(*) as controlled_territories
            FROM territories t
            LEFT JOIN player_order p ON t.match_id = p.match_id
                                     AND t.owner_player_id = p.match_player_order
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
        """Get law counts by player, optionally filtered by match.

        Uses events table as source of truth for actual law adoptions.
        Also provides unique law pairs and calculated law switches.

        Args:
            match_id: Optional match ID to filter by

        Returns:
            DataFrame with columns:
                - player_name: Player display name
                - civilization: Civilization played
                - match_id: Match ID
                - game_name: Match name
                - total_turns: Total turns in match
                - total_laws_adopted: Total law adoptions from events (includes switches)
                - unique_law_pairs: Unique law categories adopted from statistics
                - law_switches: Number of times player switched laws (derived)
        """
        base_query = """
        WITH law_events AS (
            -- Count actual law adoptions from event log (source of truth)
            SELECT
                match_id,
                player_id,
                COUNT(*) as total_laws_adopted
            FROM events
            WHERE event_type = 'LAW_ADOPTED'
            GROUP BY match_id, player_id
        ),
        law_pairs AS (
            -- Count unique law pairs adopted
            SELECT
                match_id,
                player_id,
                COUNT(*) as unique_law_pairs
            FROM player_statistics
            WHERE stat_category = 'law_changes'
            GROUP BY match_id, player_id
        )
        SELECT
            p.player_name,
            p.civilization,
            m.match_id,
            m.game_name,
            m.total_turns,
            le.total_laws_adopted,
            lp.unique_law_pairs,
            (le.total_laws_adopted - COALESCE(lp.unique_law_pairs, 0)) as law_switches
        FROM players p
        JOIN matches m ON p.match_id = m.match_id
        INNER JOIN law_events le ON p.match_id = le.match_id AND p.player_id = le.player_id
        LEFT JOIN law_pairs lp ON p.match_id = lp.match_id AND p.player_id = lp.player_id
        WHERE 1=1
        """

        params: List[Any] = []

        if match_id:
            base_query += " AND p.match_id = ?"
            params.append(match_id)

        base_query += """
        ORDER BY le.total_laws_adopted DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(base_query, params).df()

    def get_law_milestone_timing(self) -> pd.DataFrame:
        """Get timing analysis for law milestones across all matches.

        Calculates when players reach 4 laws and 7 laws based on
        actual law adoption events from the events table.

        Returns:
            DataFrame with estimated milestone timing
        """
        query = """
        WITH law_totals AS (
            -- Count actual law adoptions from events
            SELECT
                e.match_id,
                e.player_id,
                COUNT(*) as total_laws_adopted
            FROM events e
            WHERE e.event_type = 'LAW_ADOPTED'
            GROUP BY e.match_id, e.player_id
        )
        SELECT
            p.player_name,
            p.civilization,
            m.game_name,
            m.total_turns,
            lt.total_laws_adopted as total_laws,
            CAST(m.total_turns AS FLOAT) / lt.total_laws_adopted as turns_per_law,
            CASE
                WHEN lt.total_laws_adopted >= 4
                    THEN CAST((4.0 * m.total_turns / lt.total_laws_adopted) AS INTEGER)
                ELSE NULL
            END as estimated_turn_to_4_laws,
            CASE
                WHEN lt.total_laws_adopted >= 7
                    THEN CAST((7.0 * m.total_turns / lt.total_laws_adopted) AS INTEGER)
                ELSE NULL
            END as estimated_turn_to_7_laws
        FROM law_totals lt
        JOIN players p ON lt.player_id = p.player_id AND lt.match_id = p.match_id
        JOIN matches m ON lt.match_id = m.match_id
        WHERE lt.total_laws_adopted > 0
        ORDER BY turns_per_law ASC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query).df()

    def get_player_law_progression_stats(self) -> pd.DataFrame:
        """Get aggregate law progression statistics per player.

        Groups by tournament participant when available, ensuring consistent
        aggregation across matches even if in-game names vary.
        Uses events table as source of truth for law adoption counts.

        Returns:
            DataFrame with average law counts and milestone estimates per person:
                - player_name: Display name (participant name if linked, else player name)
                - participant_id: Participant ID (NULL if unlinked)
                - is_unlinked: Boolean, TRUE if not linked to participant
                - matches_played: Number of matches played
                - avg_laws_per_game: Average laws adopted per match
                - max_laws: Most laws in any single match
                - min_laws: Fewest laws in any single match
                - avg_turns_per_law: Average turns between law adoptions
                - avg_turn_to_4_laws: Average turn when 4th law reached
                - avg_turn_to_7_laws: Average turn when 7th law reached
        """
        query = """
        WITH law_event_counts AS (
            -- Count actual law adoptions from events
            SELECT
                match_id,
                player_id,
                COUNT(*) as total_laws_adopted
            FROM events
            WHERE event_type = 'LAW_ADOPTED'
            GROUP BY match_id, player_id
        ),
        player_grouping AS (
            -- Create smart grouping key: participant_id if linked, else normalized name
            SELECT
                lec.match_id,
                p.player_id,
                p.player_name,
                tp.participant_id,
                tp.display_name as participant_display_name,
                m.total_turns,
                lec.total_laws_adopted as total_laws,
                -- Grouping key: use participant_id if available, else normalized name
                COALESCE(
                    CAST(tp.participant_id AS VARCHAR),
                    'unlinked_' || p.player_name_normalized
                ) as grouping_key,
                -- Display name: prefer participant, fallback to player
                COALESCE(tp.display_name, p.player_name) as display_name,
                -- Flag for unlinked players
                CASE WHEN tp.participant_id IS NULL THEN TRUE ELSE FALSE END as is_unlinked
            FROM law_event_counts lec
            JOIN players p ON lec.player_id = p.player_id AND lec.match_id = p.match_id
            LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
            JOIN matches m ON lec.match_id = m.match_id
            WHERE lec.total_laws_adopted > 0
        )
        SELECT
            MAX(display_name) as player_name,
            MAX(participant_id) as participant_id,
            MAX(is_unlinked) as is_unlinked,
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
        FROM player_grouping
        GROUP BY grouping_key
        HAVING COUNT(DISTINCT match_id) > 0
        ORDER BY avg_laws_per_game DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query).df()

    def get_nation_win_stats(
        self,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> pd.DataFrame:
        """Get win statistics by nation/civilization, optionally filtered.

        Args:
            tournament_round: Specific round number
            bracket: Bracket filter
            min_turns: Minimum turns
            max_turns: Maximum turns
            map_size: Map size filter
            map_class: Map class filter
            map_aspect: Map aspect ratio filter
            nations: List of civilizations
            players: List of player names
            result_filter: Filter by match result (winners/losers/all)

        Returns:
            DataFrame with nation, wins, total_matches, win_percentage from filtered matches
        """
        # Get filtered match IDs (or player tuples if result_filter set)
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=result_filter,
        )

        # If no matches, return empty DataFrame
        if not filtered:
            return pd.DataFrame()

        where_clause, params = self._build_player_filter(filtered, result_filter)

        query = f"""
        SELECT
            COALESCE(p.civilization, 'Unknown') as nation,
            COUNT(CASE WHEN mw.winner_player_id = p.player_id THEN 1 END) as wins,
            COUNT(*) as total_matches,
            ROUND(
                COUNT(CASE WHEN mw.winner_player_id = p.player_id THEN 1 END) * 100.0 /
                NULLIF(COUNT(*), 0), 2
            ) as win_percentage
        FROM players p
        LEFT JOIN match_winners mw ON p.match_id = mw.match_id
        WHERE {where_clause}
        GROUP BY p.civilization
        HAVING COUNT(*) > 0
        ORDER BY wins DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, params).df()

    def get_nation_loss_stats(
        self,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> pd.DataFrame:
        """Get loss statistics by nation/civilization, optionally filtered.

        Args:
            tournament_round: Specific round number
            bracket: Bracket filter
            min_turns: Minimum turns
            max_turns: Maximum turns
            map_size: Map size filter
            map_class: Map class filter
            map_aspect: Map aspect ratio filter
            nations: List of civilizations
            players: List of player names
            result_filter: Filter by match result (winners/losers/all)

        Returns:
            DataFrame with nation, losses, total_matches, loss_percentage from filtered matches
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=result_filter,
        )

        if not filtered:
            return pd.DataFrame()

        where_clause, params = self._build_player_filter(filtered, result_filter)

        query = f"""
        SELECT
            COALESCE(p.civilization, 'Unknown') as nation,
            COUNT(CASE WHEN mw.winner_player_id != p.player_id OR mw.winner_player_id IS NULL THEN 1 END) as losses,
            COUNT(*) as total_matches,
            ROUND(
                COUNT(CASE WHEN mw.winner_player_id != p.player_id OR mw.winner_player_id IS NULL THEN 1 END) * 100.0 /
                NULLIF(COUNT(*), 0), 2
            ) as loss_percentage
        FROM players p
        LEFT JOIN match_winners mw ON p.match_id = mw.match_id
        WHERE {where_clause}
        GROUP BY p.civilization
        HAVING COUNT(*) > 0
        ORDER BY losses DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, params).df()

    def get_nation_popularity(
        self,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> pd.DataFrame:
        """Get nation popularity statistics based on total matches played, optionally filtered.

        Args:
            tournament_round: Specific round number
            bracket: Bracket filter
            min_turns: Minimum turns
            max_turns: Maximum turns
            map_size: Map size filter
            map_class: Map class filter
            map_aspect: Map aspect ratio filter
            nations: List of civilizations
            players: List of player names
            result_filter: Filter by match result (winners/losers/all)

        Returns:
            DataFrame with nation, total_matches from filtered matches
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=result_filter,
        )

        if not filtered:
            return pd.DataFrame()

        where_clause, params = self._build_player_filter(filtered, result_filter)

        query = f"""
        SELECT
            COALESCE(p.civilization, 'Unknown') as nation,
            COUNT(DISTINCT p.match_id) as total_matches
        FROM players p
        WHERE {where_clause}
        GROUP BY p.civilization
        HAVING COUNT(DISTINCT p.match_id) > 0
        ORDER BY total_matches DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, params).df()

    def get_map_breakdown(
        self,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> pd.DataFrame:
        """Get map breakdown statistics by map type, aspect ratio, and size.

        Args:
            tournament_round: Specific round number
            bracket: 'Winners', 'Losers', 'Unknown', or None for all
            min_turns: Minimum number of turns
            max_turns: Maximum number of turns
            map_size: Map size filter
            map_class: Map class filter
            map_aspect: Map aspect ratio filter
            nations: List of civilization names to filter by
            players: List of player names to filter by
            result_filter: Filter by match result (winners/losers/all)

        Returns:
            DataFrame with map_class, map_aspect_ratio, map_size, count
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=result_filter,
        )

        if not filtered:
            return pd.DataFrame()

        # Match-level query - only needs match_ids
        match_ids = self._extract_match_ids(filtered, result_filter)

        query = """
        SELECT
            COALESCE(map_class, 'Unknown') as map_class,
            COALESCE(map_aspect_ratio, 'Unknown') as map_aspect_ratio,
            COALESCE(map_size, 'Unknown') as map_size,
            COUNT(*) as count
        FROM matches
        WHERE match_id = ANY($match_ids)
        GROUP BY map_class, map_aspect_ratio, map_size
        HAVING COUNT(*) > 0
        ORDER BY count DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, {"match_ids": match_ids}).df()

    def get_unit_popularity(
        self,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> pd.DataFrame:
        """Get unit popularity statistics with category and role classification.

        Args:
            tournament_round: Specific round number
            bracket: 'Winners', 'Losers', 'Unknown', or None for all
            min_turns: Minimum number of turns
            max_turns: Maximum number of turns
            map_size: Map size filter
            map_class: Map class filter
            map_aspect: Map aspect ratio filter
            nations: List of civilization names to filter by
            players: List of player names to filter by
            result_filter: Filter by match result (winners/losers/all)

        Returns:
            DataFrame with category, role, unit_type, total_count
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=result_filter,
        )

        if not filtered:
            return pd.DataFrame()

        where_clause, params = self._build_player_filter(
            filtered, result_filter, table_alias="up"
        )

        query = f"""
        SELECT
            COALESCE(uc.category, 'Unknown') as category,
            COALESCE(uc.role, 'Unknown') as role,
            up.unit_type,
            SUM(up.count) as total_count
        FROM units_produced up
        LEFT JOIN unit_classifications uc ON up.unit_type = uc.unit_type
        WHERE {where_clause}
        GROUP BY uc.category, uc.role, up.unit_type
        HAVING SUM(up.count) > 0
        ORDER BY uc.category, uc.role, total_count DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, params).df()

    def get_law_progression_by_match(
        self,
        match_id: Optional[int] = None,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> pd.DataFrame:
        """Get law progression for players, showing when they reached 4 and 7 laws.

        Groups by tournament participant when available. When called without filters,
        aggregates across all matches to show how people (not player instances)
        progress through laws.

        Args:
            match_id: Optional match_id to filter (None for all matches)
            tournament_round: Filter by tournament round number (e.g., 1, 2, -1, -2)
            bracket: Filter by bracket ('Winners', 'Losers', 'Unknown')
            min_turns: Filter by minimum total turns
            max_turns: Filter by maximum total turns
            map_size: Filter by map size
            map_class: Filter by map class
            map_aspect: Filter by map aspect ratio
            nations: Filter by civilizations played
            players: Filter by player names
            result_filter: Filter by match result (winners/losers/all)

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
        # If match_id specified, use that directly; otherwise use filter helper
        if match_id is not None:
            filtered: list[int] | list[Tuple[int, int]] = [match_id]
            effective_result_filter: ResultFilter = None
        else:
            filtered = self._get_filtered_match_ids(
                tournament_round=tournament_round,
                bracket=bracket,
                min_turns=min_turns,
                max_turns=max_turns,
                map_size=map_size,
                map_class=map_class,
                map_aspect=map_aspect,
                nations=nations,
                players=players,
                result_filter=result_filter,
            )
            effective_result_filter = result_filter

        if not filtered:
            return pd.DataFrame()

        # Get match_ids for the CTE and player filter for the final JOIN
        match_ids = self._extract_match_ids(filtered, effective_result_filter)
        player_filter, params = self._build_player_filter(
            filtered, effective_result_filter
        )
        params["match_ids"] = match_ids

        # Build WHERE clause for final select
        final_where = f"WHERE {player_filter}" if player_filter else ""

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
                AND e.match_id = ANY($match_ids)
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
        {final_where}
        ORDER BY m.match_id, m.player_id
        """

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

        Counts unique law classes (pairs) adopted, not total adoptions. When a
        player switches from Colonies to Serfdom, it doesn't increase their
        law count since both belong to the same law class.

        Args:
            match_id: Match ID to analyze

        Returns:
            DataFrame with columns:
                - player_id: Database player ID
                - player_name: Display name (participant if linked, else player name)
                - participant_id: Participant ID (NULL if unlinked)
                - turn_number: Turn when law was adopted
                - cumulative_laws: Unique law classes adopted up to this turn
                - law_list: Comma-separated list of current active laws
                - new_laws: Comma-separated list of laws adopted this turn
        """
        query = """
        WITH law_class_mapping AS (
            -- Map each law to its law class (mutually exclusive pairs)
            SELECT * FROM (VALUES
                ('LAW_SLAVERY', 'slavery_freedom'),
                ('LAW_FREEDOM', 'slavery_freedom'),
                ('LAW_CENTRALIZATION', 'centralization_vassalage'),
                ('LAW_VASSALAGE', 'centralization_vassalage'),
                ('LAW_COLONIES', 'colonies_serfdom'),
                ('LAW_SERFDOM', 'colonies_serfdom'),
                ('LAW_MONOTHEISM', 'monotheism_polytheism'),
                ('LAW_POLYTHEISM', 'monotheism_polytheism'),
                ('LAW_TYRANNY', 'tyranny_constitution'),
                ('LAW_CONSTITUTION', 'tyranny_constitution'),
                ('LAW_EPICS', 'epics_exploration'),
                ('LAW_EXPLORATION', 'epics_exploration'),
                ('LAW_DIVINE_RULE', 'divine_rule_legal_code'),
                ('LAW_LEGAL_CODE', 'divine_rule_legal_code'),
                ('LAW_GUILDS', 'guilds_elites'),
                ('LAW_ELITES', 'guilds_elites'),
                ('LAW_ICONOGRAPHY', 'iconography_calligraphy'),
                ('LAW_CALLIGRAPHY', 'iconography_calligraphy'),
                ('LAW_PHILOSOPHY', 'philosophy_engineering'),
                ('LAW_ENGINEERING', 'philosophy_engineering'),
                ('LAW_PROFESSIONAL_ARMY', 'professional_army_volunteers'),
                ('LAW_VOLUNTEERS', 'professional_army_volunteers'),
                ('LAW_TOLERANCE', 'tolerance_orthodoxy'),
                ('LAW_ORTHODOXY', 'tolerance_orthodoxy')
            ) AS t(law_name, law_class)
        ),
        law_events AS (
            SELECT
                e.player_id,
                COALESCE(tp.display_name, p.player_name) as player_name,
                p.participant_id,
                e.turn_number,
                e.event_id,
                TRIM(BOTH '"' FROM json_extract(e.event_data, '$.law')::VARCHAR) as law_name
            FROM events e
            JOIN players p ON e.match_id = p.match_id AND e.player_id = p.player_id
            LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
            WHERE e.event_type = 'LAW_ADOPTED'
                AND e.match_id = ?
                -- Exclude succession laws (not competitive choices)
                AND TRIM(BOTH '"' FROM json_extract(e.event_data, '$.law')::VARCHAR)
                    NOT IN ('LAW_PRIMOGENITURE', 'LAW_SENIORITY', 'LAW_ULTIMOGENITURE')
        ),
        law_events_with_class AS (
            SELECT
                le.*,
                COALESCE(lcm.law_class, le.law_name) as law_class
            FROM law_events le
            LEFT JOIN law_class_mapping lcm ON le.law_name = lcm.law_name
        ),
        cumulative_classes AS (
            -- Count distinct law classes up to each event
            SELECT
                le1.player_id,
                le1.player_name,
                le1.participant_id,
                le1.turn_number,
                le1.event_id,
                le1.law_name,
                (
                    SELECT COUNT(DISTINCT le2.law_class)
                    FROM law_events_with_class le2
                    WHERE le2.player_id = le1.player_id
                      AND le2.event_id <= le1.event_id
                ) as cumulative_laws
            FROM law_events_with_class le1
        ),
        current_laws AS (
            -- Get the most recent law for each class up to each event
            SELECT
                cc.player_id,
                cc.turn_number,
                cc.event_id,
                string_agg(DISTINCT latest.law_name, ', ') as law_list
            FROM cumulative_classes cc
            CROSS JOIN LATERAL (
                SELECT DISTINCT ON (lec.law_class) lec.law_name
                FROM law_events_with_class lec
                WHERE lec.player_id = cc.player_id
                  AND lec.event_id <= cc.event_id
                ORDER BY lec.law_class, lec.event_id DESC
            ) latest
            GROUP BY cc.player_id, cc.turn_number, cc.event_id
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
            cc.player_id,
            cc.player_name,
            cc.participant_id,
            cc.turn_number,
            cc.cumulative_laws,
            cl.law_list,
            nlt.new_laws
        FROM cumulative_classes cc
        LEFT JOIN current_laws cl ON cc.player_id = cl.player_id
            AND cc.turn_number = cl.turn_number
            AND cc.event_id = cl.event_id
        LEFT JOIN new_laws_this_turn nlt ON cc.player_id = nlt.player_id
            AND cc.turn_number = nlt.turn_number
            AND cc.event_id = nlt.event_id
        ORDER BY cc.player_id, cc.turn_number, cc.cumulative_laws
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id]).df()

    def get_tech_timeline(self, match_id: int) -> pd.DataFrame:
        """Get individual technology discoveries for timeline visualization.

        Returns each technology discovery event with player and turn information,
        formatted for timeline/gantt-style charts.

        Args:
            match_id: Match ID to analyze

        Returns:
            DataFrame with columns:
                - player_id: Database player ID
                - player_name: Player's display name
                - turn_number: Turn when tech was discovered
                - tech_name: Technology name (formatted)
        """
        query = """
        SELECT
            e.player_id,
            p.player_name,
            e.turn_number,
            json_extract(e.event_data, '$.tech') as tech_name
        FROM events e
        JOIN players p ON e.match_id = p.match_id AND e.player_id = p.player_id
        WHERE e.event_type = 'TECH_DISCOVERED'
            AND e.match_id = ?
        ORDER BY e.turn_number, e.player_id
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id]).df()

    def get_law_timeline(self, match_id: int) -> pd.DataFrame:
        """Get individual law adoptions for timeline visualization.

        Returns each law adoption event with player and turn information,
        formatted for timeline/gantt-style charts.

        Args:
            match_id: Match ID to analyze

        Returns:
            DataFrame with columns:
                - player_id: Database player ID
                - player_name: Player's display name
                - turn_number: Turn when law was adopted
                - law_name: Law name (formatted)
        """
        query = """
        SELECT
            e.player_id,
            p.player_name,
            e.turn_number,
            json_extract(e.event_data, '$.law') as law_name
        FROM events e
        JOIN players p ON e.match_id = p.match_id AND e.player_id = p.player_id
        WHERE e.event_type = 'LAW_ADOPTED'
            AND e.match_id = ?
        ORDER BY e.turn_number, e.player_id
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

        Note:
            Old World stores yields in units of 0.1 internally (for fixed-point
            arithmetic in multiplayer). This query divides by 10 to return
            display-ready values.

            Example: XML value of 215 returns as 21.5 science/turn

            See: docs/reports/yield-display-scale-issue.md
        """
        base_query = """
        SELECT
            yh.player_id,
            p.player_name,
            p.civilization,
            yh.turn_number,
            yh.resource_type,
            yh.amount / 10.0 AS amount  -- Old World stores in 0.1 units
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

    def has_yield_total_history(self, match_id: int) -> bool:
        """Check if a match has YieldTotalHistory data.

        YieldTotalHistory is only available in v1.0.81366+ saves and provides
        accurate cumulative totals (summing rates gives ~30% lower values).

        Args:
            match_id: Match ID to check

        Returns:
            True if the match has yield total history data
        """
        query = """
        SELECT EXISTS (
            SELECT 1 FROM player_yield_total_history
            WHERE match_id = ?
            LIMIT 1
        )
        """
        with self.db.get_connection() as conn:
            result = conn.execute(query, [match_id]).fetchone()
            return bool(result[0]) if result else False

    def get_yield_total_history_by_match(
        self, match_id: int, yield_types: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """Get cumulative yield totals for all players in a match.

        Returns data from player_yield_total_history showing turn-by-turn
        cumulative totals. Only available for v1.0.81366+ saves.

        These totals include yields from ALL sources (events, bonuses,
        specialists, trade, etc.) - not just rate-based production.
        Summing rates gives ~30% lower values than actual totals.

        Args:
            match_id: Match ID to query
            yield_types: Optional list of yield types to filter

        Returns:
            DataFrame with columns:
            - player_id, player_name, civilization
            - turn_number
            - resource_type: The yield type
            - amount: Cumulative total for that yield through that turn
        """
        base_query = """
        SELECT
            yth.player_id,
            p.player_name,
            p.civilization,
            yth.turn_number,
            yth.resource_type,
            yth.amount / 10.0 AS amount  -- Old World stores in 0.1 units
        FROM player_yield_total_history yth
        JOIN players p ON yth.player_id = p.player_id AND yth.match_id = p.match_id
        WHERE yth.match_id = ?
        """

        params = [match_id]

        if yield_types:
            placeholders = ", ".join(["?" for _ in yield_types])
            base_query += f" AND yth.resource_type IN ({placeholders})"
            params.extend(yield_types)

        base_query += " ORDER BY yth.turn_number, yth.player_id, yth.resource_type"

        with self.db.get_connection() as conn:
            return conn.execute(base_query, params).df()

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

    def get_legitimacy_bonuses_by_match(self, match_id: int) -> pd.DataFrame:
        """Get legitimacy bonus counts for all players in a match.

        Returns data from player_statistics filtered to legitimacy-related bonuses.
        These bonuses track events that affected legitimacy during the game.

        Args:
            match_id: Match ID to query

        Returns:
            DataFrame with columns:
            - player_id, player_name, civilization
            - stat_name: The bonus type (e.g., 'BONUS_CONVERT_LEGITIMACY')
            - value: Number of times this bonus was earned
        """
        query = """
        SELECT
            ps.player_id,
            p.player_name,
            p.civilization,
            ps.stat_name,
            ps.value
        FROM player_statistics ps
        JOIN players p ON ps.player_id = p.player_id AND ps.match_id = p.match_id
        WHERE ps.match_id = ?
            AND ps.stat_category = 'bonus_count'
            AND ps.stat_name LIKE '%LEGIT%'
        ORDER BY p.player_id, ps.stat_name
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

    def get_aggregated_event_timeline(
        self,
        max_turn: int = 150,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> pd.DataFrame:
        """Get aggregated event timeline across all matches.

        Returns average event counts by turn and event type, normalized
        across all matches. Useful for showing typical event patterns.

        Args:
            max_turn: Maximum turn number to include (default 150)
            tournament_round: Specific round number
            bracket: 'Winners', 'Losers', 'Unknown', or None for all
            min_turns: Minimum number of turns
            max_turns: Maximum number of turns
            map_size: Map size filter
            map_class: Map class filter
            map_aspect: Map aspect ratio filter
            nations: List of civilization names to filter by
            players: List of player names to filter by
            result_filter: Filter by match result (winners/losers/all)

        Returns:
            DataFrame with columns: turn_number, event_type, avg_event_count
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=result_filter,
        )

        if not filtered:
            return pd.DataFrame()

        # Match-level query - only needs match_ids
        match_ids = self._extract_match_ids(filtered, result_filter)

        query = """
        WITH all_events AS (
            SELECT
                e.match_id,
                e.turn_number,
                e.event_type
            FROM events e
            WHERE e.turn_number <= $max_turn
                AND e.event_type NOT LIKE 'MEMORYPLAYER_%'
                AND e.match_id = ANY($match_ids)
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
                AND m.match_id = ANY($match_ids)
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
            return conn.execute(
                query, {"match_ids": match_ids, "max_turn": max_turn}
            ).df()

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

    def get_city_founding_timeline(self, match_id: int) -> pd.DataFrame:
        """Get city founding timeline for a specific match.

        Returns CITY_FOUNDED events with player names and turn numbers.

        Args:
            match_id: Match ID to analyze

        Returns:
            DataFrame with columns: player_id, player_name, civilization,
                                    turn_number, city_name, description
        """
        query = """
        SELECT
            e.player_id,
            p.player_name,
            p.civilization,
            e.turn_number,
            TRIM(REPLACE(e.description, 'Founded', '')) as city_name,
            e.description
        FROM events e
        JOIN players p ON e.match_id = p.match_id AND e.player_id = p.player_id
        WHERE e.match_id = ?
            AND e.event_type = 'CITY_FOUNDED'
        ORDER BY e.turn_number, e.player_id
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id]).df()

    def get_ruler_archetype_win_rates(
        self,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> pd.DataFrame:
        """Get win rates by starting ruler archetype, optionally filtered.

        Analyzes starting rulers only (succession_order = 0) to show which
        archetypes correlate with victory.

        Args:
            tournament_round: Specific round number
            bracket: Bracket filter
            min_turns: Minimum turns
            max_turns: Maximum turns
            map_size: Map size filter
            map_class: Map class filter
            map_aspect: Map aspect ratio filter
            nations: List of civilizations
            players: List of player names
            result_filter: Filter by match result (winners/losers/all)

        Returns:
            DataFrame with columns from filtered matches:
            - archetype: Ruler archetype name
            - games: Total games played with this archetype
            - wins: Number of wins
            - win_rate: Win percentage (0-100)
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=result_filter,
        )

        if not filtered:
            return pd.DataFrame()

        where_clause, params = self._build_player_filter(
            filtered, result_filter, table_alias="r"
        )

        query = f"""
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
        WHERE {where_clause}
        AND r.succession_order = 0
        AND r.archetype IS NOT NULL
        GROUP BY r.archetype
        ORDER BY win_rate DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, params).df()

    def get_ruler_trait_win_rates(
        self,
        min_games: int = 2,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> pd.DataFrame:
        """Get win rates by starting ruler trait, optionally filtered.

        Analyzes starting traits chosen at game initialization to show which
        traits correlate with victory.

        Args:
            min_games: Minimum number of games required to include trait (default 2)
            tournament_round: Specific round number
            bracket: Bracket filter
            min_turns: Minimum turns
            max_turns: Maximum turns
            map_size: Map size filter
            map_class: Map class filter
            map_aspect: Map aspect ratio filter
            nations: List of civilizations
            players: List of player names
            result_filter: Filter by match result (winners/losers/all)

        Returns:
            DataFrame with columns from filtered matches:
            - starting_trait: Trait name
            - games: Total games played with this trait
            - wins: Number of wins
            - win_rate: Win percentage (0-100)
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=result_filter,
        )

        if not filtered:
            return pd.DataFrame()

        where_clause, params = self._build_player_filter(
            filtered, result_filter, table_alias="r"
        )
        params["min_games"] = min_games

        query = f"""
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
        WHERE {where_clause}
        AND r.succession_order = 0
        AND r.starting_trait IS NOT NULL
        GROUP BY r.starting_trait
        HAVING COUNT(*) >= $min_games
        ORDER BY win_rate DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, params).df()

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

    def get_ruler_archetype_matchups(
        self,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> pd.DataFrame:
        """Get win rates for archetype vs archetype matchups, optionally filtered.

        Analyzes head-to-head performance between starting ruler archetypes
        to identify favorable and unfavorable matchups.

        Args:
            tournament_round: Specific round number
            bracket: Bracket filter
            min_turns: Minimum turns
            max_turns: Maximum turns
            map_size: Map size filter
            map_class: Map class filter
            map_aspect: Map aspect ratio filter
            nations: List of civilizations
            players: List of player names
            result_filter: Filter by match result (winners/losers/all)

        Returns:
            DataFrame with columns from filtered matches:
            - archetype: The archetype (row in matrix)
            - opponent_archetype: The opposing archetype (column in matrix)
            - games: Number of games with this matchup
            - wins: Number of wins for archetype
            - win_rate: Win percentage for archetype (0-100)
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=result_filter,
        )

        if not filtered:
            return pd.DataFrame()

        # Match-level query - only needs match_ids
        match_ids = self._extract_match_ids(filtered, result_filter)

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
            WHERE r1.match_id = ANY($match_ids)
            AND r1.succession_order = 0 AND r2.succession_order = 0
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

        params = {"match_ids": match_ids}

        with self.db.get_connection() as conn:
            return conn.execute(query, params).df()

    def get_ruler_archetype_trait_combinations(
        self,
        limit: int = 10,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> pd.DataFrame:
        """Get most popular archetype + trait combinations for starting rulers, optionally filtered.

        Args:
            limit: Maximum number of combinations to return (default 10)
            tournament_round: Specific round number
            bracket: Bracket filter
            min_turns: Minimum turns
            max_turns: Maximum turns
            map_size: Map size filter
            map_class: Map class filter
            map_aspect: Map aspect ratio filter
            nations: List of civilizations
            players: List of player names
            result_filter: Filter by match result (winners/losers/all)

        Returns:
            DataFrame with columns from filtered matches:
            - archetype: Ruler archetype name
            - starting_trait: Starting trait name
            - count: Number of times this combo was chosen
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=result_filter,
        )

        if not filtered:
            return pd.DataFrame()

        where_clause, params = self._build_player_filter(
            filtered, result_filter, table_alias="r"
        )
        params["limit"] = limit

        query = f"""
        SELECT
            r.archetype,
            r.starting_trait,
            COUNT(*) as count
        FROM rulers r
        WHERE {where_clause}
        AND r.succession_order = 0
        AND r.archetype IS NOT NULL
        AND r.starting_trait IS NOT NULL
        GROUP BY r.archetype, r.starting_trait
        ORDER BY count DESC
        LIMIT $limit
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, params).df()

    def get_ruler_reign_duration_win_rates(
        self,
        exclude_entire_match: bool = False,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> pd.DataFrame:
        """Get win rates by starting ruler's reign duration, bucketed by quartiles.

        Analyzes how long the starting ruler (succession_order=0) ruled before
        succession occurred, and correlates reign duration with win rate.
        Quartiles are calculated dynamically based on the filtered data distribution.

        Args:
            exclude_entire_match: If True, exclude rulers who ruled the entire match
                (no succession occurred). Default False (include all).
            tournament_round: Filter by tournament round numbers
            bracket: Bracket filter ("Winners", "Losers", "Unknown")
            min_turns: Minimum total match turns
            max_turns: Maximum total match turns
            map_size: Map size filter
            map_class: Map class filter
            map_aspect: Map aspect ratio filter
            nations: List of civilizations to filter
            players: List of player names to filter
            result_filter: Filter by match result (winners/losers/all)

        Returns:
            DataFrame with columns:
            - quartile: 1-4 (1=shortest reigns, 4=longest reigns)
            - quartile_label: Human-readable label (e.g., "Q1: 1-25 turns")
            - min_turns: Minimum reign duration in this quartile
            - max_turns: Maximum reign duration in this quartile
            - games: Number of games in this quartile
            - wins: Number of wins
            - win_rate: Win percentage (0-100)
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=result_filter,
        )

        if not filtered:
            return pd.DataFrame()

        where_clause, params = self._build_player_filter(
            filtered, result_filter, table_alias="r"
        )
        params["exclude_entire_match"] = exclude_entire_match

        query = f"""
        WITH reign_data AS (
            SELECT
                r.match_id,
                r.player_id,
                r.succession_turn as start_turn,
                m.total_turns,
                (
                    SELECT MIN(r2.succession_turn)
                    FROM rulers r2
                    WHERE r2.match_id = r.match_id
                    AND r2.player_id = r.player_id
                    AND r2.succession_order > 0
                ) as next_ruler_turn,
                CASE WHEN mw.winner_player_id = r.player_id THEN 1 ELSE 0 END as won
            FROM rulers r
            JOIN matches m ON r.match_id = m.match_id
            JOIN match_winners mw ON r.match_id = mw.match_id
            WHERE r.succession_order = 0
            AND {where_clause}
        ),
        reign_durations AS (
            SELECT
                match_id,
                player_id,
                CASE
                    WHEN next_ruler_turn IS NOT NULL THEN next_ruler_turn - start_turn
                    ELSE total_turns - start_turn
                END as reign_duration,
                next_ruler_turn IS NULL as ruled_entire_match,
                won
            FROM reign_data
        ),
        filtered_reigns AS (
            SELECT * FROM reign_durations
            WHERE ($exclude_entire_match = FALSE OR ruled_entire_match = FALSE)
        ),
        quartiled AS (
            SELECT
                *,
                NTILE(4) OVER (ORDER BY reign_duration) as quartile
            FROM filtered_reigns
        )
        SELECT
            quartile,
            MIN(reign_duration) as min_turns,
            MAX(reign_duration) as max_turns,
            COUNT(*) as games,
            SUM(won) as wins,
            ROUND(SUM(won) * 100.0 / COUNT(*), 2) as win_rate
        FROM quartiled
        GROUP BY quartile
        ORDER BY quartile
        """

        with self.db.get_connection() as conn:
            df = conn.execute(query, params).df()

        if df.empty:
            return df

        # Add human-readable quartile labels
        df["quartile_label"] = df.apply(
            lambda row: f"Q{int(row['quartile'])}: {int(row['min_turns'])}-{int(row['max_turns'])} turns",
            axis=1,
        )

        return df

    def get_succession_rate_win_rates(
        self,
        exclude_zero_successions: bool = False,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> pd.DataFrame:
        """Get win rates by succession rate (successions per 100 turns), bucketed by quartiles.

        Normalizes succession count by game length to account for longer games
        naturally having more ruler transitions.

        Args:
            exclude_zero_successions: If True, exclude players with 0 successions
                (full-game rulers). Default False (include all).
            tournament_round: Filter by tournament round numbers
            bracket: Bracket filter ("Winners", "Losers", "Unknown")
            min_turns: Minimum total match turns
            max_turns: Maximum total match turns
            map_size: Map size filter
            map_class: Map class filter
            map_aspect: Map aspect ratio filter
            nations: List of civilizations to filter
            players: List of player names to filter
            result_filter: Filter by match result (winners/losers/all)

        Returns:
            DataFrame with columns:
            - quartile: 1-4 (1=lowest rate, 4=highest rate)
            - quartile_label: Human-readable label (e.g., "Q1: 0.0-2.1 per 100 turns")
            - min_rate: Minimum succession rate in this quartile
            - max_rate: Maximum succession rate in this quartile
            - games: Number of games in this quartile
            - wins: Number of wins
            - win_rate: Win percentage (0-100)
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=result_filter,
        )

        if not filtered:
            return pd.DataFrame()

        where_clause, params = self._build_player_filter(
            filtered, result_filter, table_alias="r"
        )
        params["exclude_zero"] = exclude_zero_successions

        query = f"""
        WITH player_successions AS (
            SELECT
                r.match_id,
                r.player_id,
                m.total_turns,
                COUNT(*) - 1 as succession_count,
                MAX(CASE WHEN mw.winner_player_id = r.player_id THEN 1 ELSE 0 END) as won
            FROM rulers r
            JOIN matches m ON r.match_id = m.match_id
            JOIN match_winners mw ON r.match_id = mw.match_id
            WHERE {where_clause}
            GROUP BY r.match_id, r.player_id, m.total_turns
        ),
        filtered_successions AS (
            SELECT * FROM player_successions
            WHERE ($exclude_zero = FALSE OR succession_count > 0)
        ),
        with_rate AS (
            SELECT
                *,
                ROUND(succession_count * 100.0 / total_turns, 2) as succession_rate
            FROM filtered_successions
            WHERE total_turns > 0
        ),
        quartiled AS (
            SELECT *, NTILE(4) OVER (ORDER BY succession_rate) as quartile
            FROM with_rate
        )
        SELECT
            quartile,
            MIN(succession_rate) as min_rate,
            MAX(succession_rate) as max_rate,
            COUNT(*) as games,
            SUM(won) as wins,
            ROUND(SUM(won) * 100.0 / COUNT(*), 2) as win_rate
        FROM quartiled
        GROUP BY quartile
        ORDER BY quartile
        """

        with self.db.get_connection() as conn:
            df = conn.execute(query, params).df()

        if df.empty:
            return df

        # Add human-readable quartile labels
        df["quartile_label"] = df.apply(
            lambda row: f"Q{int(row['quartile'])}: {row['min_rate']:.1f}-{row['max_rate']:.1f} per 100 turns",
            axis=1,
        )

        return df

    def get_starting_ruler_survival_curve(
        self,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
    ) -> pd.DataFrame:
        """Get survival curve data for starting rulers over time.

        Shows what percentage of starting rulers (succession_order=0) are still
        in power at each turn number, split by winners and losers.

        Args:
            tournament_round: Filter by tournament round numbers
            bracket: Bracket filter ("Winners", "Losers", "Unknown")
            min_turns: Minimum total match turns
            max_turns: Maximum total match turns
            map_size: Map size filter
            map_class: Map class filter
            map_aspect: Map aspect ratio filter
            nations: List of civilizations to filter
            players: List of player names to filter

        Returns:
            DataFrame with columns:
            - turn_number: Turn number (1 to max)
            - games_at_turn: Number of games that reached this turn
            - survival_rate: % of starting rulers still ruling (all players)
            - winners_survival_rate: % of starting rulers still ruling (winners only)
            - losers_survival_rate: % of starting rulers still ruling (losers only)
        """
        # Get filtered match IDs (no result_filter since we want both winners and losers)
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=None,
        )

        if not filtered:
            return pd.DataFrame()

        # Build match filter
        if isinstance(filtered[0], tuple):
            # Result filter returned tuples, extract just match IDs
            match_ids = list(set(m for m, _ in filtered))
        else:
            match_ids = filtered

        query = """
        WITH starting_rulers AS (
            SELECT
                r.match_id,
                r.player_id,
                r.succession_turn as start_turn,
                m.total_turns,
                (SELECT MIN(r2.succession_turn)
                 FROM rulers r2
                 WHERE r2.match_id = r.match_id
                 AND r2.player_id = r.player_id
                 AND r2.succession_order > 0) as successor_turn,
                CASE WHEN mw.winner_player_id = r.player_id THEN 1 ELSE 0 END as won
            FROM rulers r
            JOIN matches m ON r.match_id = m.match_id
            JOIN match_winners mw ON r.match_id = mw.match_id
            WHERE r.succession_order = 0
            AND r.match_id = ANY($match_ids)
        ),
        with_reign_end AS (
            SELECT
                match_id,
                player_id,
                start_turn,
                total_turns,
                won,
                COALESCE(successor_turn, total_turns + 1) as reign_end_turn
            FROM starting_rulers
        ),
        turn_series AS (
            SELECT UNNEST(generate_series(1, (SELECT MAX(total_turns) FROM with_reign_end))) as turn_number
        ),
        survival_by_turn AS (
            SELECT
                t.turn_number,
                COUNT(*) as games_at_turn,
                SUM(CASE WHEN wr.reign_end_turn > t.turn_number THEN 1 ELSE 0 END) as still_ruling,
                SUM(CASE WHEN wr.won = 1 THEN 1 ELSE 0 END) as winners_at_turn,
                SUM(CASE WHEN wr.won = 1 AND wr.reign_end_turn > t.turn_number THEN 1 ELSE 0 END) as winners_still_ruling,
                SUM(CASE WHEN wr.won = 0 THEN 1 ELSE 0 END) as losers_at_turn,
                SUM(CASE WHEN wr.won = 0 AND wr.reign_end_turn > t.turn_number THEN 1 ELSE 0 END) as losers_still_ruling
            FROM turn_series t
            CROSS JOIN with_reign_end wr
            WHERE t.turn_number <= wr.total_turns
            GROUP BY t.turn_number
        )
        SELECT
            turn_number,
            games_at_turn,
            ROUND(still_ruling * 100.0 / games_at_turn, 2) as survival_rate,
            ROUND(winners_still_ruling * 100.0 / NULLIF(winners_at_turn, 0), 2) as winners_survival_rate,
            ROUND(losers_still_ruling * 100.0 / NULLIF(losers_at_turn, 0), 2) as losers_survival_rate
        FROM survival_by_turn
        ORDER BY turn_number
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, {"match_ids": match_ids}).df()

    def get_succession_expected_vs_actual_win_rates(
        self,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> pd.DataFrame:
        """Get win rates comparing actual vs expected successions.

        Expected successions are calculated based on average reign duration of 27 turns.
        Categories: "Fewer than expected", "As expected", "More than expected".

        Args:
            tournament_round: Filter by tournament round numbers
            bracket: Bracket filter ("Winners", "Losers", "Unknown")
            min_turns: Minimum total match turns
            max_turns: Maximum total match turns
            map_size: Map size filter
            map_class: Map class filter
            map_aspect: Map aspect ratio filter
            nations: List of civilizations to filter
            players: List of player names to filter
            result_filter: Filter by match result (winners/losers/all)

        Returns:
            DataFrame with columns:
            - category: "Fewer than expected", "As expected", "More than expected"
            - games: Number of games in this category
            - wins: Number of wins
            - win_rate: Win percentage (0-100)
            - avg_actual: Average actual successions in this category
            - avg_expected: Average expected successions in this category
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=result_filter,
        )

        if not filtered:
            return pd.DataFrame()

        where_clause, params = self._build_player_filter(
            filtered, result_filter, table_alias="r"
        )

        # Average reign duration is 27 turns (calculated from actual data)
        avg_reign = 27.0

        query = f"""
        WITH player_successions AS (
            SELECT
                r.match_id,
                r.player_id,
                m.total_turns,
                COUNT(*) - 1 as actual_successions,
                ROUND(m.total_turns / {avg_reign}, 1) as expected_successions,
                MAX(CASE WHEN mw.winner_player_id = r.player_id THEN 1 ELSE 0 END) as won
            FROM rulers r
            JOIN matches m ON r.match_id = m.match_id
            JOIN match_winners mw ON r.match_id = mw.match_id
            WHERE {where_clause}
            GROUP BY r.match_id, r.player_id, m.total_turns
        ),
        with_deviation AS (
            SELECT
                *,
                actual_successions - expected_successions as deviation
            FROM player_successions
        ),
        categorized AS (
            SELECT
                *,
                CASE
                    WHEN deviation < -0.5 THEN 'Fewer than expected'
                    WHEN deviation > 0.5 THEN 'More than expected'
                    ELSE 'As expected'
                END as category
            FROM with_deviation
        )
        SELECT
            category,
            COUNT(*) as games,
            SUM(won) as wins,
            ROUND(SUM(won) * 100.0 / COUNT(*), 2) as win_rate,
            ROUND(AVG(actual_successions), 2) as avg_actual,
            ROUND(AVG(expected_successions), 2) as avg_expected
        FROM categorized
        GROUP BY category
        ORDER BY
            CASE category
                WHEN 'Fewer than expected' THEN 1
                WHEN 'As expected' THEN 2
                WHEN 'More than expected' THEN 3
            END
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, params).df()

    def get_nation_counter_pick_matrix(
        self,
        min_games: int = 1,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> pd.DataFrame:
        """Get counter-pick matchup matrix showing nation performance by pick order, optionally filtered.

        Returns win rates for each first_pick_nation vs second_pick_nation combination
        from the pick_order_games data. This shows which nations are effective
        counter-picks against others.

        Args:
            min_games: Minimum number of games required to include a matchup (default 1)
            tournament_round: Specific round number
            bracket: Bracket filter
            min_turns: Minimum turns
            max_turns: Maximum turns
            map_size: Map size filter
            map_class: Map class filter
            map_aspect: Map aspect ratio filter
            nations: List of civilizations
            players: List of player names
            result_filter: Filter by match result (winners/losers/all)

        Returns:
            DataFrame with columns from filtered matches:
            - first_pick_nation: Nation picked first
            - second_pick_nation: Nation picked second (counter-pick)
            - games: Number of games with this matchup
            - second_picker_wins: Wins for the second picker
            - second_picker_win_rate: Win rate for second picker (0-100)
                Higher values = effective counter-pick

        Example:
            If "Assyria vs Egypt" has 70% second_picker_win_rate, Egypt is a strong
            counter to Assyria when picked second.
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=result_filter,
        )

        if not filtered:
            return pd.DataFrame()

        # Match-level query - only needs match_ids
        match_ids = self._extract_match_ids(filtered, result_filter)

        query = """
        WITH matchups AS (
            SELECT
                pog.first_pick_nation,
                pog.second_pick_nation,
                pog.matched_match_id,
                pog.first_picker_participant_id,
                pog.second_picker_participant_id,
                mw.winner_player_id,
                p_winner.participant_id as winner_participant_id
            FROM pick_order_games pog
            LEFT JOIN match_winners mw ON pog.matched_match_id = mw.match_id
            LEFT JOIN players p_winner ON mw.winner_player_id = p_winner.player_id
            WHERE pog.matched_match_id IS NOT NULL
                AND pog.matched_match_id = ANY($match_ids)
                AND pog.first_picker_participant_id IS NOT NULL
                AND pog.second_picker_participant_id IS NOT NULL
                AND pog.first_pick_nation IS NOT NULL
                AND pog.second_pick_nation IS NOT NULL
        )
        SELECT
            first_pick_nation,
            second_pick_nation,
            COUNT(*) as games,
            SUM(CASE
                WHEN winner_participant_id = second_picker_participant_id THEN 1
                ELSE 0
            END) as second_picker_wins,
            ROUND(
                SUM(CASE
                    WHEN winner_participant_id = second_picker_participant_id THEN 1
                    ELSE 0
                END) * 100.0 / COUNT(*),
                2
            ) as second_picker_win_rate
        FROM matchups
        GROUP BY first_pick_nation, second_pick_nation
        HAVING COUNT(*) >= $min_games
        ORDER BY first_pick_nation, second_pick_nation
        """

        params = {"match_ids": match_ids, "min_games": min_games}

        with self.db.get_connection() as conn:
            return conn.execute(query, params).df()

    def get_pick_order_win_rates(
        self,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> pd.DataFrame:
        """Get overall win rates by pick order (first picker vs second picker), optionally filtered.

        Returns win rates for first and second pickers with confidence intervals
        and statistical significance testing using Wilson score interval.

        Args:
            tournament_round: Specific round number
            bracket: Bracket filter
            min_turns: Minimum turns
            max_turns: Maximum turns
            map_size: Map size filter
            map_class: Map class filter
            map_aspect: Map aspect ratio filter
            nations: List of civilizations
            players: List of player names
            result_filter: Filter by match result (winners/losers/all)

        Returns:
            DataFrame with columns from filtered matches:
            - pick_position: 'First Pick' or 'Second Pick'
            - games: Number of games
            - wins: Number of wins
            - win_rate: Win percentage (0-100)
            - ci_lower: Lower bound of 95% confidence interval (0-100)
            - ci_upper: Upper bound of 95% confidence interval (0-100)
            - standard_error: Standard error of the proportion
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=result_filter,
        )

        if not filtered:
            return pd.DataFrame()

        # Match-level query - only needs match_ids
        match_ids = self._extract_match_ids(filtered, result_filter)

        query = """
        WITH pick_results AS (
            SELECT
                pog.matched_match_id,
                pog.first_picker_participant_id,
                pog.second_picker_participant_id,
                mw.winner_player_id,
                p_winner.participant_id as winner_participant_id
            FROM pick_order_games pog
            LEFT JOIN match_winners mw ON pog.matched_match_id = mw.match_id
            LEFT JOIN players p_winner ON mw.winner_player_id = p_winner.player_id
            WHERE pog.matched_match_id IS NOT NULL
                AND pog.matched_match_id = ANY($match_ids)
                AND pog.first_picker_participant_id IS NOT NULL
                AND pog.second_picker_participant_id IS NOT NULL
        ),
        pick_stats AS (
            SELECT
                'First Pick' as pick_position,
                COUNT(*) as games,
                SUM(CASE WHEN winner_participant_id = first_picker_participant_id THEN 1 ELSE 0 END) as wins
            FROM pick_results
            UNION ALL
            SELECT
                'Second Pick' as pick_position,
                COUNT(*) as games,
                SUM(CASE WHEN winner_participant_id = second_picker_participant_id THEN 1 ELSE 0 END) as wins
            FROM pick_results
        )
        SELECT
            pick_position,
            games,
            wins,
            ROUND(wins * 100.0 / games, 2) as win_rate,
            -- Wilson score interval for 95% confidence (z=1.96)
            -- Lower bound
            ROUND(
                (
                    (wins + 1.96*1.96/2) / (games + 1.96*1.96)
                    - 1.96 * SQRT((wins * (games - wins) / games + 1.96*1.96/4) / (games + 1.96*1.96))
                ) * 100,
                2
            ) as ci_lower,
            -- Upper bound
            ROUND(
                (
                    (wins + 1.96*1.96/2) / (games + 1.96*1.96)
                    + 1.96 * SQRT((wins * (games - wins) / games + 1.96*1.96/4) / (games + 1.96*1.96))
                ) * 100,
                2
            ) as ci_upper,
            -- Standard error for reference
            ROUND(
                SQRT((wins * 1.0 / games) * (1 - wins * 1.0 / games) / games) * 100,
                2
            ) as standard_error
        FROM pick_stats
        WHERE games > 0
        ORDER BY pick_position
        """

        params = {"match_ids": match_ids}

        with self.db.get_connection() as conn:
            return conn.execute(query, params).df()

    def get_metric_progression_stats(
        self,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> Dict[str, pd.DataFrame]:
        """Get metric progression statistics across all matches.

        Calculates median and percentile bands (25th, 75th) for:
        - Science per turn
        - Orders per turn
        - Military score per turn
        - Legitimacy per turn

        Args:
            tournament_round: Filter by tournament round number (e.g., 1, 2, -1, -2)
            bracket: Filter by bracket ('Winners', 'Losers', 'Unknown')
            min_turns: Filter by minimum total turns
            max_turns: Filter by maximum total turns
            map_size: Filter by map size
            map_class: Filter by map class
            map_aspect: Filter by map aspect ratio
            nations: Filter by civilizations played
            players: Filter by player names
            result_filter: Filter by match result (winners/losers/all)

        Returns:
            Dictionary with keys 'science', 'orders', 'military', 'legitimacy',
            each containing a DataFrame with columns:
            - turn_number: Game turn
            - median: Median value at this turn
            - percentile_25: 25th percentile
            - percentile_75: 75th percentile
            - sample_size: Number of games contributing data at this turn
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=result_filter,
        )

        if not filtered:
            return {
                "science": pd.DataFrame(),
                "orders": pd.DataFrame(),
                "military": pd.DataFrame(),
                "legitimacy": pd.DataFrame(),
            }

        # Build player-level filter (handles both match-only and match+player filtering)
        where_clause, params = self._build_player_filter(
            filtered, result_filter, table_alias="h"
        )

        # NOTE: For matches with delta-encoded history (v1.0.81366+, Jan 2026),
        # percentiles are calculated only on recorded turns. Some turns may be
        # missing for sparse matches (2/47 affected). Individual match views
        # use forward-fill in charts.py for complete time series.

        # Science per turn (YIELD_SCIENCE)
        science_query = f"""
        SELECT
            h.turn_number,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY h.amount / 10.0) as median,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY h.amount / 10.0) as percentile_25,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY h.amount / 10.0) as percentile_75,
            COUNT(DISTINCT h.match_id) as sample_size
        FROM player_yield_history h
        WHERE h.resource_type = 'YIELD_SCIENCE'
            AND {where_clause}
        GROUP BY h.turn_number
        ORDER BY h.turn_number
        """

        # Orders per turn (YIELD_ORDERS)
        orders_query = f"""
        SELECT
            h.turn_number,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY h.amount / 10.0) as median,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY h.amount / 10.0) as percentile_25,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY h.amount / 10.0) as percentile_75,
            COUNT(DISTINCT h.match_id) as sample_size
        FROM player_yield_history h
        WHERE h.resource_type = 'YIELD_ORDERS'
            AND {where_clause}
        GROUP BY h.turn_number
        ORDER BY h.turn_number
        """

        # Military score per turn
        military_query = f"""
        SELECT
            h.turn_number,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY h.military_power) as median,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY h.military_power) as percentile_25,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY h.military_power) as percentile_75,
            COUNT(DISTINCT h.match_id) as sample_size
        FROM player_military_history h
        WHERE {where_clause}
        GROUP BY h.turn_number
        ORDER BY h.turn_number
        """

        # Legitimacy per turn
        legitimacy_query = f"""
        SELECT
            h.turn_number,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY h.legitimacy) as median,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY h.legitimacy) as percentile_25,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY h.legitimacy) as percentile_75,
            COUNT(DISTINCT h.match_id) as sample_size
        FROM player_legitimacy_history h
        WHERE {where_clause}
        GROUP BY h.turn_number
        ORDER BY h.turn_number
        """

        with self.db.get_connection() as conn:
            return {
                "science": conn.execute(science_query, params).df(),
                "orders": conn.execute(orders_query, params).df(),
                "military": conn.execute(military_query, params).df(),
                "legitimacy": conn.execute(legitimacy_query, params).df(),
            }

    def get_yield_with_cumulative(
        self,
        yield_type: str,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> Dict[str, pd.DataFrame]:
        """Get yield progression with both rate and cumulative statistics.

        Calculates median and percentile bands (25th, 75th) for:
        - Yield per turn (rate)
        - Cumulative yield produced (running total)

        Args:
            yield_type: The yield type (e.g., 'YIELD_SCIENCE', 'YIELD_FOOD')
            tournament_round: Filter by tournament round number
            bracket: Filter by bracket ('Winners', 'Losers', 'Unknown')
            min_turns: Filter by minimum total turns
            max_turns: Filter by maximum total turns
            map_size: Filter by map size
            map_class: Filter by map class
            map_aspect: Filter by map aspect ratio
            nations: Filter by civilizations played
            players: Filter by player names
            result_filter: Filter by match result (winners/losers/all)

        Returns:
            Dictionary with keys 'rate' and 'cumulative',
            each containing a DataFrame with columns:
            - turn_number: Game turn
            - median: Median value at this turn
            - percentile_25: 25th percentile
            - percentile_75: 75th percentile
            - sample_size: Number of data points at this turn
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=result_filter,
        )

        if not filtered:
            return {
                "rate": pd.DataFrame(),
                "cumulative": pd.DataFrame(),
            }

        # Build player-level filter (handles both match-only and match+player filtering)
        where_clause, params = self._build_player_filter(
            filtered, result_filter, table_alias="yh"
        )

        # Yield rate per turn
        rate_query = f"""
        SELECT
            yh.turn_number,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY yh.amount / 10.0) as median,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY yh.amount / 10.0) as percentile_25,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY yh.amount / 10.0) as percentile_75,
            MIN(yh.amount / 10.0) as min_value,
            MAX(yh.amount / 10.0) as max_value,
            AVG(yh.amount / 10.0) as avg_value,
            STDDEV(yh.amount / 10.0) as std_dev,
            COUNT(DISTINCT yh.match_id) as sample_size
        FROM player_yield_history yh
        WHERE yh.resource_type = $yield_type
            AND {where_clause}
        GROUP BY yh.turn_number
        ORDER BY yh.turn_number
        """

        # Cumulative yield: Use actual totals from player_yield_total_history
        # when available (v1.0.81366+ saves), fall back to SUM() OVER for older saves.
        # Summing rates gives ~30% lower values than actual totals because yields
        # from events, bonuses, specialists, trade, etc. aren't in rate history.
        cumulative_query = f"""
        WITH
        -- Matches that have accurate total history (v1.0.81366+)
        matches_with_totals AS (
            SELECT DISTINCT match_id
            FROM player_yield_total_history
        ),
        -- Actual cumulative totals for newer saves
        actual_totals AS (
            SELECT
                yth.match_id,
                yth.player_id,
                yth.turn_number,
                yth.amount / 10.0 as cumulative_yield
            FROM player_yield_total_history yth
            WHERE yth.resource_type = $yield_type
                AND {where_clause.replace('yh.', 'yth.')}
        ),
        -- Calculated cumulative totals for older saves (fallback)
        calculated_totals AS (
            SELECT
                yh.match_id,
                yh.player_id,
                yh.turn_number,
                SUM(yh.amount / 10.0) OVER (
                    PARTITION BY yh.match_id, yh.player_id
                    ORDER BY yh.turn_number
                ) as cumulative_yield
            FROM player_yield_history yh
            WHERE yh.resource_type = $yield_type
                AND {where_clause}
                AND yh.match_id NOT IN (SELECT match_id FROM matches_with_totals)
        ),
        -- Combine both sources
        cumulative_per_player AS (
            SELECT * FROM actual_totals
            UNION ALL
            SELECT * FROM calculated_totals
        )
        SELECT
            turn_number,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY cumulative_yield) as median,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY cumulative_yield) as percentile_25,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY cumulative_yield) as percentile_75,
            MIN(cumulative_yield) as min_value,
            MAX(cumulative_yield) as max_value,
            AVG(cumulative_yield) as avg_value,
            STDDEV(cumulative_yield) as std_dev,
            COUNT(DISTINCT match_id) as sample_size
        FROM cumulative_per_player
        GROUP BY turn_number
        ORDER BY turn_number
        """

        params["yield_type"] = yield_type

        with self.db.get_connection() as conn:
            return {
                "rate": conn.execute(rate_query, params).df(),
                "cumulative": conn.execute(cumulative_query, params).df(),
            }

    def get_territory_map(self, match_id: int, turn_number: int) -> pd.DataFrame:
        """Get territory map snapshot for a specific match and turn.

        Returns all tiles with their ownership and terrain for visualization.

        Args:
            match_id: Match to query
            turn_number: Turn number to retrieve

        Returns:
            DataFrame with columns:
            - x_coordinate: Tile X position
            - y_coordinate: Tile Y position
            - terrain_type: Terrain constant
            - owner_player_id: Player ID or NULL
            - player_name: Player name (NULL if unowned)
            - civilization: Player civilization (NULL if unowned)
        """
        query = """
        WITH player_order AS (
            SELECT
                match_id,
                player_id,
                player_name,
                civilization,
                ROW_NUMBER() OVER (PARTITION BY match_id ORDER BY player_id) as match_player_order
            FROM players
        )
        SELECT
            t.x_coordinate,
            t.y_coordinate,
            t.terrain_type,
            t.owner_player_id,
            p.player_name,
            p.civilization
        FROM territories t
        LEFT JOIN player_order p ON t.match_id = p.match_id
                                 AND t.owner_player_id = p.match_player_order
        WHERE t.match_id = ?
          AND t.turn_number = ?
        ORDER BY t.y_coordinate, t.x_coordinate
        """

        result = self.db.fetch_all(query, {"1": match_id, "2": turn_number})

        if not result:
            return pd.DataFrame()

        return pd.DataFrame(
            result,
            columns=[
                "x_coordinate",
                "y_coordinate",
                "terrain_type",
                "owner_player_id",
                "player_name",
                "civilization",
            ],
        )

    def get_territory_map_full(self, match_id: int, turn_number: int) -> pd.DataFrame:
        """Get complete territory map snapshot including all layers.

        Returns all tiles with ownership, terrain, improvements, specialists,
        resources, roads, and city information for the Pixi.js map viewer.

        Args:
            match_id: Match to query
            turn_number: Turn number to retrieve

        Returns:
            DataFrame with columns:
            - x_coordinate: Tile X position
            - y_coordinate: Tile Y position
            - terrain_type: Terrain constant
            - owner_player_id: Player ID or NULL
            - player_name: Player name (NULL if unowned)
            - civilization: Player civilization (NULL if unowned)
            - improvement_type: Improvement constant or NULL
            - specialist_type: Specialist constant or NULL
            - resource_type: Resource constant or NULL
            - has_road: Boolean road presence
            - city_name: City name if city tile, else NULL
            - population: City population if city tile, else NULL
            - is_capital: Boolean if capital city
            - family_name: Family that owns the city (e.g., FAMILY_BARCID)
            - is_family_seat: Boolean if this is the family's seat (first city founded)
        """
        query = """
        WITH map_dimensions AS (
            -- Calculate actual map width from territory data
            SELECT
                match_id,
                MAX(x_coordinate) + 1 as map_width
            FROM territories
            WHERE match_id = ? AND turn_number = ?
            GROUP BY match_id
        ),
        player_order AS (
            SELECT
                match_id,
                player_id,
                player_name,
                civilization,
                ROW_NUMBER() OVER (PARTITION BY match_id ORDER BY player_id) as match_player_order
            FROM players
        ),
        family_seats AS (
            -- Determine family seat as the first city founded for each family
            SELECT
                match_id,
                family_name,
                MIN(founded_turn) as seat_founded_turn
            FROM cities
            WHERE match_id = ? AND family_name IS NOT NULL
            GROUP BY match_id, family_name
        ),
        city_tiles AS (
            -- Map city tile_id to x,y coordinates with family info
            SELECT
                c.match_id,
                c.city_name,
                c.population,
                c.is_capital,
                c.tile_id,
                c.family_name,
                CASE WHEN c.founded_turn = fs.seat_founded_turn THEN true ELSE false END as is_family_seat
            FROM cities c
            LEFT JOIN family_seats fs ON c.match_id = fs.match_id
                                      AND c.family_name = fs.family_name
            WHERE c.match_id = ?
        )
        SELECT
            t.x_coordinate,
            t.y_coordinate,
            t.terrain_type,
            t.owner_player_id,
            p.player_name,
            p.civilization,
            t.improvement_type,
            t.specialist_type,
            t.resource_type,
            t.has_road,
            ct.city_name,
            ct.population,
            ct.is_capital,
            ct.family_name,
            ct.is_family_seat
        FROM territories t
        CROSS JOIN map_dimensions md
        LEFT JOIN player_order p ON t.match_id = p.match_id
                                 AND t.owner_player_id = p.match_player_order
        LEFT JOIN city_tiles ct ON t.match_id = ct.match_id
                                AND ct.tile_id = (t.y_coordinate * md.map_width + t.x_coordinate)
        WHERE t.match_id = ?
          AND t.turn_number = ?
        ORDER BY t.y_coordinate, t.x_coordinate
        """

        result = self.db.fetch_all(
            query,
            {
                "1": match_id,
                "2": turn_number,
                "3": match_id,
                "4": match_id,
                "5": match_id,
                "6": turn_number,
            },
        )

        if not result:
            return pd.DataFrame()

        return pd.DataFrame(
            result,
            columns=[
                "x_coordinate",
                "y_coordinate",
                "terrain_type",
                "owner_player_id",
                "player_name",
                "civilization",
                "improvement_type",
                "specialist_type",
                "resource_type",
                "has_road",
                "city_name",
                "population",
                "is_capital",
                "family_name",
                "is_family_seat",
            ],
        )

    def get_territory_turn_range(self, match_id: int) -> Tuple[int, int]:
        """Get the turn range (min, max) for a match's territory data.

        Args:
            match_id: Match to query

        Returns:
            Tuple of (min_turn, max_turn), or (0, 0) if no data
        """
        query = """
        SELECT
            MIN(turn_number) as min_turn,
            MAX(turn_number) as max_turn
        FROM territories
        WHERE match_id = ?
        """

        result = self.db.fetch_one(query, {"1": match_id})

        if not result or result[0] is None:
            return (0, 0)

        return (result[0], result[1])

    def get_improvement_counts_by_player(
        self, match_id: int, turn_number: Optional[int] = None
    ) -> pd.DataFrame:
        """Get improvement counts per player for a match at a specific turn.

        Counts the number of each improvement type owned by each player.
        If turn_number is not specified, uses the final turn of the match.

        Args:
            match_id: Match to query
            turn_number: Turn to get improvements for (default: final turn)

        Returns:
            DataFrame with columns:
                - player_id: Player identifier
                - player_name: Player name
                - improvement_type: Raw improvement type (e.g., 'IMPROVEMENT_MINE')
                - count: Number of that improvement type
        """
        # Get turn to query - use provided turn or final turn
        if turn_number is None:
            _, max_turn = self.get_territory_turn_range(match_id)
            turn_number = max_turn

        # territories.owner_player_id stores local slot numbers (1, 2), not global
        # player_ids. Use player_order CTE to map slots to actual players.
        query = """
        WITH player_order AS (
            SELECT
                match_id,
                player_id,
                player_name,
                ROW_NUMBER() OVER (
                    PARTITION BY match_id ORDER BY player_id
                ) as match_player_order
            FROM players
        )
        SELECT
            p.player_id,
            p.player_name,
            t.improvement_type,
            COUNT(*) as count
        FROM territories t
        JOIN player_order p ON t.match_id = p.match_id
                            AND t.owner_player_id = p.match_player_order
        WHERE t.match_id = ?
          AND t.turn_number = ?
          AND t.improvement_type IS NOT NULL
        GROUP BY p.player_id, p.player_name, t.improvement_type
        ORDER BY p.player_name, count DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id, turn_number]).df()

    def get_specialist_counts_by_player(
        self, match_id: int, turn_number: Optional[int] = None
    ) -> pd.DataFrame:
        """Get specialist counts per player for a match at a specific turn.

        Counts the number of each specialist type employed by each player.
        If turn_number is not specified, uses the final turn of the match.

        Args:
            match_id: Match to query
            turn_number: Turn to get specialists for (default: final turn)

        Returns:
            DataFrame with columns:
                - player_id: Player identifier
                - player_name: Player name
                - specialist_type: Raw specialist type (e.g., 'SPECIALIST_MINER')
                - count: Number of that specialist type
        """
        # Get turn to query - use provided turn or final turn
        if turn_number is None:
            _, max_turn = self.get_territory_turn_range(match_id)
            turn_number = max_turn

        # territories.owner_player_id stores local slot numbers (1, 2), not global
        # player_ids. Use player_order CTE to map slots to actual players.
        query = """
        WITH player_order AS (
            SELECT
                match_id,
                player_id,
                player_name,
                ROW_NUMBER() OVER (
                    PARTITION BY match_id ORDER BY player_id
                ) as match_player_order
            FROM players
        )
        SELECT
            p.player_id,
            p.player_name,
            t.specialist_type,
            COUNT(*) as count
        FROM territories t
        JOIN player_order p ON t.match_id = p.match_id
                            AND t.owner_player_id = p.match_player_order
        WHERE t.match_id = ?
          AND t.turn_number = ?
          AND t.specialist_type IS NOT NULL
        GROUP BY p.player_id, p.player_name, t.specialist_type
        ORDER BY p.player_name, count DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id, turn_number]).df()

    def get_science_infrastructure_timeline(self, match_id: int) -> pd.DataFrame:
        """Get time-series of science infrastructure buildup per player.

        Tracks specialists and improvements that produce science across all turns.

        Args:
            match_id: Match to query

        Returns:
            DataFrame with columns:
                - turn_number: Game turn
                - player_id: Player identifier
                - player_name: Player name
                - asset_category: 'specialist' or 'improvement'
                - asset_type: Raw type (e.g., 'SPECIALIST_PHILOSOPHER_1')
                - count: Number of this asset type
        """
        # Science-producing improvements (from docs/science-generation-guide.md)
        # - Watermills/Windmills: 20 science each
        # - Monasteries: 20 science each
        # - Shrines of Nabu/Athena: 10 science each
        # Note: Libraries and Musaeum are MODIFIERS, not direct producers
        science_improvements = (
            "'IMPROVEMENT_WATERMILL', 'IMPROVEMENT_WINDMILL', "
            "'IMPROVEMENT_MONASTERY_CHRISTIANITY', 'IMPROVEMENT_MONASTERY_JUDAISM', "
            "'IMPROVEMENT_MONASTERY_MANICHAEISM', 'IMPROVEMENT_MONASTERY_ZOROASTRIANISM', "
            "'IMPROVEMENT_SHRINE_NABU', 'IMPROVEMENT_SHRINE_ATHENA'"
        )

        # All specialists produce science (rural=10, apprentice=20, master=30, elder=40)
        # Plus Philosophers and Doctors get additional bonuses
        query = f"""
        WITH player_order AS (
            SELECT
                match_id,
                player_id,
                player_name,
                ROW_NUMBER() OVER (
                    PARTITION BY match_id ORDER BY player_id
                ) as match_player_order
            FROM players
        ),
        specialist_counts AS (
            SELECT
                t.turn_number,
                p.player_id,
                p.player_name,
                'specialist' as asset_category,
                t.specialist_type as asset_type,
                COUNT(*) as count
            FROM territories t
            JOIN player_order p ON t.match_id = p.match_id
                                AND t.owner_player_id = p.match_player_order
            WHERE t.match_id = ?
              AND t.specialist_type IS NOT NULL
            GROUP BY t.turn_number, p.player_id, p.player_name, t.specialist_type
        ),
        improvement_counts AS (
            SELECT
                t.turn_number,
                p.player_id,
                p.player_name,
                'improvement' as asset_category,
                t.improvement_type as asset_type,
                COUNT(*) as count
            FROM territories t
            JOIN player_order p ON t.match_id = p.match_id
                                AND t.owner_player_id = p.match_player_order
            WHERE t.match_id = ?
              AND t.improvement_type IN ({science_improvements})
            GROUP BY t.turn_number, p.player_id, p.player_name, t.improvement_type
        )
        SELECT * FROM specialist_counts
        UNION ALL
        SELECT * FROM improvement_counts
        ORDER BY turn_number, player_name, asset_category, asset_type
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id, match_id]).df()

    def get_science_infrastructure_summary(
        self, match_id: int, turn_number: Optional[int] = None
    ) -> pd.DataFrame:
        """Get science infrastructure summary for hierarchical visualization.

        Returns aggregated counts of science-producing assets for a specific turn.
        If turn_number is not specified, uses the final turn of the match.

        Args:
            match_id: Match to query
            turn_number: Turn to get data for (default: final turn)

        Returns:
            DataFrame with columns:
                - player_id: Player identifier
                - player_name: Player name
                - asset_category: 'specialist' or 'improvement'
                - asset_type: Raw type (e.g., 'SPECIALIST_PHILOSOPHER_1')
                - count: Total count
        """
        if turn_number is None:
            _, max_turn = self.get_territory_turn_range(match_id)
            turn_number = max_turn

        # Science-producing improvements (from docs/science-generation-guide.md)
        # - Watermills/Windmills: 20 science each
        # - Monasteries: 20 science each
        # - Shrines of Nabu/Athena: 10 science each
        # Note: Libraries and Musaeum are MODIFIERS, not direct producers
        science_improvements = (
            "'IMPROVEMENT_WATERMILL', 'IMPROVEMENT_WINDMILL', "
            "'IMPROVEMENT_MONASTERY_CHRISTIANITY', 'IMPROVEMENT_MONASTERY_JUDAISM', "
            "'IMPROVEMENT_MONASTERY_MANICHAEISM', 'IMPROVEMENT_MONASTERY_ZOROASTRIANISM', "
            "'IMPROVEMENT_SHRINE_NABU', 'IMPROVEMENT_SHRINE_ATHENA'"
        )

        # All specialists produce science based on tier
        query = f"""
        WITH player_order AS (
            SELECT
                match_id,
                player_id,
                player_name,
                ROW_NUMBER() OVER (
                    PARTITION BY match_id ORDER BY player_id
                ) as match_player_order
            FROM players
        ),
        specialist_counts AS (
            SELECT
                p.player_id,
                p.player_name,
                'specialist' as asset_category,
                t.specialist_type as asset_type,
                COUNT(*) as count
            FROM territories t
            JOIN player_order p ON t.match_id = p.match_id
                                AND t.owner_player_id = p.match_player_order
            WHERE t.match_id = ?
              AND t.turn_number = ?
              AND t.specialist_type IS NOT NULL
            GROUP BY p.player_id, p.player_name, t.specialist_type
        ),
        improvement_counts AS (
            SELECT
                p.player_id,
                p.player_name,
                'improvement' as asset_category,
                t.improvement_type as asset_type,
                COUNT(*) as count
            FROM territories t
            JOIN player_order p ON t.match_id = p.match_id
                                AND t.owner_player_id = p.match_player_order
            WHERE t.match_id = ?
              AND t.turn_number = ?
              AND t.improvement_type IN ({science_improvements})
            GROUP BY p.player_id, p.player_name, t.improvement_type
        )
        SELECT * FROM specialist_counts
        UNION ALL
        SELECT * FROM improvement_counts
        ORDER BY player_name, asset_category, asset_type
        """

        with self.db.get_connection() as conn:
            return conn.execute(
                query, [match_id, turn_number, match_id, turn_number]
            ).df()

    def get_science_modifiers_summary(
        self, match_id: int, turn_number: Optional[int] = None
    ) -> pd.DataFrame:
        """Get science modifier improvements per player.

        Returns Libraries and Musaeum counts with their modifier percentages.

        Args:
            match_id: Match to query
            turn_number: Turn to get data for (default: final turn)

        Returns:
            DataFrame with columns:
                - player_id: Player identifier
                - player_name: Player name
                - modifier_type: Improvement type (e.g., 'IMPROVEMENT_LIBRARY_1')
                - modifier_percent: Modifier percentage (e.g., 10 for +10%)
                - count: Number of this improvement
        """
        if turn_number is None:
            _, max_turn = self.get_territory_turn_range(match_id)
            turn_number = max_turn

        modifier_improvements = (
            "'IMPROVEMENT_LIBRARY_1', 'IMPROVEMENT_LIBRARY_2', "
            "'IMPROVEMENT_LIBRARY_3', 'IMPROVEMENT_MUSAEUM'"
        )

        query = f"""
        WITH player_order AS (
            SELECT
                match_id,
                player_id,
                player_name,
                ROW_NUMBER() OVER (
                    PARTITION BY match_id ORDER BY player_id
                ) as match_player_order
            FROM players
        )
        SELECT
            p.player_id,
            p.player_name,
            t.improvement_type as modifier_type,
            COUNT(*) as count
        FROM territories t
        JOIN player_order p ON t.match_id = p.match_id
                            AND t.owner_player_id = p.match_player_order
        WHERE t.match_id = ?
          AND t.turn_number = ?
          AND t.improvement_type IN ({modifier_improvements})
        GROUP BY p.player_id, p.player_name, t.improvement_type
        ORDER BY p.player_name, t.improvement_type
        """

        with self.db.get_connection() as conn:
            df = conn.execute(query, [match_id, turn_number]).df()

            # Add Clerics family stele tracking
            # Clerics families get steles that provide +10/25/50% science modifiers
            # One stele per Clerics family type (built at family seat)
            clerics_list = ", ".join(f"'{f}'" for f in CLERICS_FAMILIES)
            clerics_query = f"""
            SELECT
                p.player_id,
                p.player_name,
                'CLERICS_STELE' as modifier_type,
                COUNT(DISTINCT c.family_name) as count
            FROM cities c
            JOIN players p ON c.match_id = p.match_id AND c.player_id = p.player_id
            WHERE c.match_id = ?
              AND c.family_name IN ({clerics_list})
            GROUP BY p.player_id, p.player_name
            """
            clerics_df = conn.execute(clerics_query, [match_id]).df()

        # Add modifier_percent column based on SCIENCE_MODIFIERS constant
        if not df.empty:
            df["modifier_percent"] = df["modifier_type"].map(
                lambda x: SCIENCE_MODIFIERS.get(x, 0)
            )
        else:
            df["modifier_percent"] = []

        # Add Clerics stele data with estimated modifier
        # Conservative estimate: +10% per Clerics city (Stele I equivalent)
        if not clerics_df.empty:
            clerics_df["modifier_percent"] = 10  # Conservative: assume Stele I
            df = pd.concat([df, clerics_df], ignore_index=True)

        return df

    def get_science_projects_summary(self, match_id: int) -> pd.DataFrame:
        """Get science-producing city projects per player.

        Returns Archive projects and Scientific Method with their science values.

        Args:
            match_id: Match to query

        Returns:
            DataFrame with columns:
                - player_id: Player identifier
                - player_name: Player name
                - project_type: Project type (e.g., 'PROJECT_ARCHIVE_1')
                - science_value: Science per turn from this project
                - count: Number of times completed
                - is_modifier: True if this is a modifier (Scientific Method)
        """
        query = """
        SELECT
            p.player_id,
            p.player_name,
            cp.project_type,
            SUM(cp.count) as count
        FROM city_projects cp
        JOIN cities c ON cp.match_id = c.match_id AND cp.city_id = c.city_id
        JOIN players p ON c.match_id = p.match_id AND c.player_id = p.player_id
        WHERE cp.match_id = ?
          AND (cp.project_type LIKE 'PROJECT_ARCHIVE_%'
               OR cp.project_type = 'PROJECT_SCIENTIFIC_METHOD')
        GROUP BY p.player_id, p.player_name, cp.project_type
        ORDER BY p.player_name, cp.project_type
        """

        with self.db.get_connection() as conn:
            df = conn.execute(query, [match_id]).df()

        # Add science_value and is_modifier columns
        if not df.empty:
            df["science_value"] = df["project_type"].map(
                lambda x: SCIENCE_VALUES.get(x, 0)
            )
            df["is_modifier"] = df["project_type"] == "PROJECT_SCIENTIFIC_METHOD"
            # For Scientific Method, use modifier value instead
            df.loc[df["is_modifier"], "science_value"] = 0
            df["modifier_percent"] = df["project_type"].map(
                lambda x: SCIENCE_MODIFIERS.get(x, 0)
            )
        else:
            df["science_value"] = []
            df["is_modifier"] = []
            df["modifier_percent"] = []

        return df

    def get_science_bonuses_summary(self, match_id: int) -> pd.DataFrame:
        """Get nation bonuses, Sages family cities, and science laws per player.

        Args:
            match_id: Match to query

        Returns:
            DataFrame with columns:
                - player_id: Player identifier
                - player_name: Player name
                - bonus_type: 'nation', 'sages_family', or 'law'
                - bonus_source: Specific source (e.g., 'Babylonia', 'LAW_CENTRALIZATION')
                - science_value: Estimated science contribution
                - details: Additional context
        """
        results = []

        # 1. Get nation bonuses
        nation_query = """
        SELECT
            p.player_id,
            p.player_name,
            p.civilization,
            (SELECT COUNT(*) FROM cities c WHERE c.match_id = p.match_id AND c.player_id = p.player_id) as city_count
        FROM players p
        WHERE p.match_id = ?
        """
        with self.db.get_connection() as conn:
            nations_df = conn.execute(nation_query, [match_id]).df()

        for _, row in nations_df.iterrows():
            civ = row["civilization"]
            if civ in SCIENCE_NATIONS:
                bonus_per_city = SCIENCE_NATIONS[civ]
                total_bonus = bonus_per_city * row["city_count"]
                results.append(
                    {
                        "player_id": row["player_id"],
                        "player_name": row["player_name"],
                        "bonus_type": "nation",
                        "bonus_source": civ,
                        "science_value": total_bonus,
                        "details": f"+{bonus_per_city}/city × {row['city_count']} cities",
                    }
                )

        # 2. Get Sages family cities and specialist counts
        # First get the Sages city info
        sages_cities_query = """
        SELECT
            c.player_id,
            p.player_name,
            c.city_id,
            c.city_name
        FROM cities c
        JOIN players p ON c.match_id = p.match_id AND c.player_id = p.player_id
        WHERE c.match_id = ?
          AND c.family_name IN ('FAMILY_AMORITE', 'FAMILY_THUTMOSID', 'FAMILY_ALCMAEONID')
        """
        with self.db.get_connection() as conn:
            sages_cities_df = conn.execute(sages_cities_query, [match_id]).df()

        if not sages_cities_df.empty:
            # Try to count specialists in Sages cities using city_id in territories
            # This requires the city_id column to be populated (after re-import)
            try:
                sages_specialist_query = """
                WITH sages_cities AS (
                    SELECT city_id, player_id
                    FROM cities
                    WHERE match_id = ?
                      AND family_name IN ('FAMILY_AMORITE', 'FAMILY_THUTMOSID', 'FAMILY_ALCMAEONID')
                ),
                final_turn AS (
                    SELECT MAX(turn_number) as max_turn
                    FROM territories
                    WHERE match_id = ?
                )
                SELECT
                    sc.player_id,
                    COUNT(*) as specialist_count
                FROM territories t
                JOIN sages_cities sc ON t.city_id = sc.city_id
                CROSS JOIN final_turn ft
                WHERE t.match_id = ?
                  AND t.turn_number = ft.max_turn
                  AND t.specialist_type IS NOT NULL
                  AND t.city_id IS NOT NULL
                GROUP BY sc.player_id
                """
                with self.db.get_connection() as conn:
                    specialist_df = conn.execute(
                        sages_specialist_query, [match_id, match_id, match_id]
                    ).df()

                # If we got specialist counts, use them
                if not specialist_df.empty:
                    for player_id in sages_cities_df["player_id"].unique():
                        player_name = sages_cities_df[
                            sages_cities_df["player_id"] == player_id
                        ]["player_name"].iloc[0]
                        city_count = len(
                            sages_cities_df[sages_cities_df["player_id"] == player_id]
                        )

                        # Get specialist count for this player
                        player_specialists = specialist_df[
                            specialist_df["player_id"] == player_id
                        ]
                        specialist_count = (
                            int(player_specialists["specialist_count"].iloc[0])
                            if not player_specialists.empty
                            else 0
                        )

                        # Sages bonus is now tracked per-city (subject to Library modifiers)
                        # Show details for informational purposes but don't add to bonuses
                        if specialist_count > 0:
                            results.append(
                                {
                                    "player_id": player_id,
                                    "player_name": player_name,
                                    "bonus_type": "sages_family",
                                    "bonus_source": "Sages Family",
                                    "science_value": 0,  # Tracked per-city, not as flat bonus
                                    "details": f"+10 × {specialist_count} specialists in {city_count} Sages cities (per-city)",
                                }
                            )
                        else:
                            # Has Sages cities but no specialists yet
                            results.append(
                                {
                                    "player_id": player_id,
                                    "player_name": player_name,
                                    "bonus_type": "sages_family",
                                    "bonus_source": "Sages Family",
                                    "science_value": 0,
                                    "details": f"{city_count} Sages cities (no specialists)",
                                }
                            )
                else:
                    # city_id data not available yet, show placeholder
                    for player_id in sages_cities_df["player_id"].unique():
                        player_name = sages_cities_df[
                            sages_cities_df["player_id"] == player_id
                        ]["player_name"].iloc[0]
                        city_count = len(
                            sages_cities_df[sages_cities_df["player_id"] == player_id]
                        )
                        results.append(
                            {
                                "player_id": player_id,
                                "player_name": player_name,
                                "bonus_type": "sages_family",
                                "bonus_source": "Sages Family",
                                "science_value": 0,
                                "details": f"{city_count} Sages cities (+10/specialist, re-import needed)",
                            }
                        )
            except Exception:
                # city_id column doesn't exist or query failed, show placeholder
                for player_id in sages_cities_df["player_id"].unique():
                    player_name = sages_cities_df[
                        sages_cities_df["player_id"] == player_id
                    ]["player_name"].iloc[0]
                    city_count = len(
                        sages_cities_df[sages_cities_df["player_id"] == player_id]
                    )
                    results.append(
                        {
                            "player_id": player_id,
                            "player_name": player_name,
                            "bonus_type": "sages_family",
                            "bonus_source": "Sages Family",
                            "science_value": 0,
                            "details": f"{city_count} Sages cities (+10/specialist, re-import needed)",
                        }
                    )

        # 3. Get science laws (deduplicated - laws can be adopted multiple times)
        laws_query = """
        SELECT DISTINCT
            p.player_id,
            p.player_name,
            json_extract_string(e.event_data, '$.law') as law
        FROM events e
        JOIN players p ON e.match_id = p.match_id AND e.player_id = p.player_id
        WHERE e.match_id = ?
          AND e.event_type = 'LAW_ADOPTED'
          AND json_extract_string(e.event_data, '$.law') IN ('LAW_CENTRALIZATION', 'LAW_CONSTITUTION', 'LAW_PHILOSOPHY')
        """
        with self.db.get_connection() as conn:
            laws_df = conn.execute(laws_query, [match_id]).df()

            for _, row in laws_df.iterrows():
                law = row["law"]
                player_id = row["player_id"]
                player_name = row["player_name"]

                if law == "LAW_CENTRALIZATION":
                    # +20 × capital culture level (from effectCity.xml)
                    capital_query = """
                    SELECT culture_level
                    FROM cities
                    WHERE match_id = ? AND player_id = ? AND is_capital = TRUE
                    """
                    capital_df = conn.execute(
                        capital_query, [match_id, player_id]
                    ).df()
                    culture_level = (
                        int(capital_df["culture_level"].iloc[0])
                        if not capital_df.empty and capital_df["culture_level"].iloc[0] is not None
                        else 2  # Default to Developing
                    )
                    science_value = 20 * culture_level
                    results.append(
                        {
                            "player_id": player_id,
                            "player_name": player_name,
                            "bonus_type": "law",
                            "bonus_source": law,
                            "science_value": science_value,
                            "details": f"+{science_value} (capital culture {culture_level})",
                        }
                    )

                elif law == "LAW_CONSTITUTION":
                    # +10 per urban specialist
                    # Build exclusion list for rural specialists
                    rural_list = ", ".join(f"'{s}'" for s in RURAL_SPECIALISTS)
                    urban_query = f"""
                    SELECT COUNT(*) as urban_count
                    FROM territories t
                    WHERE t.match_id = ?
                      AND t.owner_player_id = ?
                      AND t.turn_number = (
                          SELECT MAX(turn_number) FROM territories WHERE match_id = ?
                      )
                      AND t.specialist_type IS NOT NULL
                      AND t.specialist_type NOT IN ({rural_list})
                    """
                    urban_df = conn.execute(
                        urban_query, [match_id, player_id, match_id]
                    ).df()
                    urban_count = (
                        int(urban_df["urban_count"].iloc[0])
                        if not urban_df.empty
                        else 0
                    )
                    science_value = urban_count * 10
                    results.append(
                        {
                            "player_id": player_id,
                            "player_name": player_name,
                            "bonus_type": "law",
                            "bonus_source": law,
                            "science_value": science_value,
                            "details": f"+10 × {urban_count} urban specialists",
                        }
                    )

                elif law == "LAW_PHILOSOPHY":
                    # +10 per forum project
                    forum_query = """
                    SELECT COALESCE(SUM(cp.count), 0) as forum_count
                    FROM city_projects cp
                    JOIN cities c ON cp.match_id = c.match_id AND cp.city_id = c.city_id
                    WHERE cp.match_id = ?
                      AND c.player_id = ?
                      AND cp.project_type LIKE 'PROJECT_FORUM%'
                    """
                    forum_df = conn.execute(forum_query, [match_id, player_id]).df()
                    forum_count = (
                        int(forum_df["forum_count"].iloc[0])
                        if not forum_df.empty
                        else 0
                    )
                    science_value = forum_count * 10
                    results.append(
                        {
                            "player_id": player_id,
                            "player_name": player_name,
                            "bonus_type": "law",
                            "bonus_source": law,
                            "science_value": science_value,
                            "details": f"+10 × {forum_count} forums",
                        }
                    )

        # 4. Get Scholar archetype bonus (+20 per Archive while Scholar is ruling)
        # Find the active ruler at the final turn for each player
        scholar_query = """
        WITH final_turn AS (
            SELECT total_turns FROM matches WHERE match_id = ?
        ),
        active_rulers AS (
            -- Get the ruler who was in power at the final turn
            -- (highest succession_turn that's <= final_turn, or death_turn IS NULL)
            SELECT
                r.player_id,
                r.archetype,
                r.ruler_name
            FROM rulers r
            CROSS JOIN final_turn ft
            WHERE r.match_id = ?
              AND r.succession_turn <= ft.total_turns
              AND (r.death_turn IS NULL OR r.death_turn > ft.total_turns)
        ),
        archive_counts AS (
            SELECT
                c.player_id,
                COUNT(*) as archive_count
            FROM city_projects cp
            JOIN cities c ON cp.match_id = c.match_id AND cp.city_id = c.city_id
            WHERE cp.match_id = ?
              AND cp.project_type LIKE 'PROJECT_ARCHIVE%'
            GROUP BY c.player_id
        )
        SELECT
            p.player_id,
            p.player_name,
            ar.archetype,
            ar.ruler_name,
            COALESCE(ac.archive_count, 0) as archive_count
        FROM players p
        LEFT JOIN active_rulers ar ON p.player_id = ar.player_id
        LEFT JOIN archive_counts ac ON p.player_id = ac.player_id
        WHERE p.match_id = ?
        """
        with self.db.get_connection() as conn:
            scholar_df = conn.execute(
                scholar_query, [match_id, match_id, match_id, match_id]
            ).df()

        for _, row in scholar_df.iterrows():
            archetype = row["archetype"]
            if archetype in ARCHETYPE_BONUSES:
                bonus_info = ARCHETYPE_BONUSES[archetype]
                archive_bonus = bonus_info.get("archive_bonus", 0)
                archive_count = row["archive_count"]
                if archive_count > 0 and archive_bonus > 0:
                    total_bonus = archive_bonus * archive_count
                    results.append(
                        {
                            "player_id": row["player_id"],
                            "player_name": row["player_name"],
                            "bonus_type": "archetype",
                            "bonus_source": f"{archetype} ({row['ruler_name']})",
                            "science_value": total_bonus,
                            "details": f"+{archive_bonus}/Archive × {archive_count} Archives",
                        }
                    )

        # 5. Get Intelligent trait bonus (+10 × culture level to governed city)
        # Governor must have the Intelligent trait
        # Per Reference XML: EFFECTCITY_TRAIT_INTELLIGENT gives +10 science per culture level
        intelligent_query = """
        SELECT
            c.player_id,
            p.player_name,
            c.city_name,
            c.culture_level,
            c.is_capital,
            c.founded_turn,
            r.ruler_name,
            r.character_id
        FROM cities c
        JOIN rulers r ON c.match_id = r.match_id AND c.governor_id = r.character_id
        JOIN players p ON c.match_id = p.match_id AND c.player_id = p.player_id
        WHERE c.match_id = ?
          AND c.governor_id IS NOT NULL
          AND r.starting_trait = 'Intelligent'
        """
        with self.db.get_connection() as conn:
            intelligent_df = conn.execute(intelligent_query, [match_id]).df()

        # Calculate bonus per city using actual culture level from database
        # Fall back to estimate if culture_level not available (old data)
        if not intelligent_df.empty:
            for player_id in intelligent_df["player_id"].unique():
                player_cities = intelligent_df[intelligent_df["player_id"] == player_id]
                player_name = player_cities["player_name"].iloc[0]
                governor_names = player_cities["ruler_name"].unique()

                total_bonus = 0
                city_details = []
                for _, city in player_cities.iterrows():
                    # Use actual culture level if available, otherwise estimate
                    if city["culture_level"] is not None:
                        culture_level = int(city["culture_level"])
                    elif city["is_capital"] or (
                        city["founded_turn"] is not None and city["founded_turn"] < 20
                    ):
                        culture_level = 3
                    else:
                        culture_level = 2

                    city_bonus = 10 * culture_level  # +10 × culture level
                    total_bonus += city_bonus
                    city_details.append(f"{city['city_name']}:+{city_bonus // 10}")

                results.append(
                    {
                        "player_id": player_id,
                        "player_name": player_name,
                        "bonus_type": "trait",
                        "bonus_source": f"Intelligent ({', '.join(governor_names)})",
                        "science_value": total_bonus,
                        "details": f"+10×culture: {', '.join(city_details)}",
                    }
                )

        # 5b. Get Intelligent Ruler bonus (+5 × culture level ALL cities)
        # Per Reference XML: EFFECTCITY_TRAIT_INTELLIGENT_ALL gives +5 science per culture
        # level to ALL cities when the ruler has the Intelligent trait
        # Find active ruler (succession_turn <= current and not dead)
        intelligent_ruler_query = """
        SELECT
            p.player_id,
            p.player_name,
            r.ruler_name,
            (SELECT COUNT(*) FROM cities c
             WHERE c.match_id = p.match_id AND c.player_id = p.player_id) as city_count,
            (SELECT COALESCE(SUM(COALESCE(c.culture_level, 2)), 0) FROM cities c
             WHERE c.match_id = p.match_id AND c.player_id = p.player_id) as total_culture
        FROM players p
        JOIN rulers r ON r.match_id = p.match_id
            AND r.player_id = p.player_id
        WHERE p.match_id = ?
          AND r.starting_trait = 'Intelligent'
          AND r.succession_turn <= (
              SELECT MAX(turn_number) FROM territories WHERE match_id = p.match_id
          )
          AND (r.death_turn IS NULL OR r.death_turn > (
              SELECT MAX(turn_number) FROM territories WHERE match_id = p.match_id
          ))
        """
        with self.db.get_connection() as conn:
            ruler_intelligent_df = conn.execute(
                intelligent_ruler_query, [match_id]
            ).df()

        if not ruler_intelligent_df.empty:
            for _, row in ruler_intelligent_df.iterrows():
                # Use actual total culture level from database
                # +5 science per culture level across all cities
                total_culture = int(row["total_culture"]) if row["total_culture"] else 0
                city_count = row["city_count"]
                total_bonus = 5 * total_culture
                avg_culture = total_culture / city_count if city_count > 0 else 0
                results.append(
                    {
                        "player_id": row["player_id"],
                        "player_name": row["player_name"],
                        "bonus_type": "trait",
                        "bonus_source": "Intelligent Ruler",
                        "science_value": total_bonus,
                        "details": f"{row['ruler_name']}: +5×{total_culture} culture ({city_count} cities, avg {avg_culture:.1f})",
                    }
                )

        # 6. Get Competitive Mode bonus (+40 science/turn for all players)
        competitive_query = """
        SELECT game_options
        FROM match_metadata
        WHERE match_id = ?
        """
        with self.db.get_connection() as conn:
            meta_df = conn.execute(competitive_query, [match_id]).df()

            if not meta_df.empty and meta_df["game_options"].iloc[0]:
                import json

                try:
                    game_options = json.loads(meta_df["game_options"].iloc[0])
                    # Get player list once for game settings
                    players_query = """
                    SELECT player_id, player_name FROM players WHERE match_id = ?
                    """
                    players_df = conn.execute(players_query, [match_id]).df()

                    if game_options.get("GAMEOPTION_COMPETITIVE_MODE"):
                        # Add +40 science to all players in this match
                        for _, row in players_df.iterrows():
                            results.append(
                                {
                                    "player_id": row["player_id"],
                                    "player_name": row["player_name"],
                                    "bonus_type": "game_setting",
                                    "bonus_source": "Competitive Mode",
                                    "science_value": 40,
                                    "details": "+40/turn (game setting)",
                                }
                            )

                    if game_options.get("GAMEOPTION_NO_STARTING_TECHS"):
                        # Add +80 science to all players in this match
                        # Per effectPlayer.xml: EFFECTPLAYER_NO_STARTING_TECHS
                        for _, row in players_df.iterrows():
                            results.append(
                                {
                                    "player_id": row["player_id"],
                                    "player_name": row["player_name"],
                                    "bonus_type": "game_setting",
                                    "bonus_source": "No Starting Techs",
                                    "science_value": 80,
                                    "details": "+80/turn (game setting)",
                                }
                            )
                except (json.JSONDecodeError, TypeError):
                    pass  # Invalid JSON or None value

        # 7. Get Dualism theology bonus (+10 science per religion level)
        # Per Reference XML: EFFECTCITY_THEOLOGY_DUALISM gives +10 per religion
        # (aiYieldRateReligion means per religion level in cities)
        # Description format: "{Religion} Dualism established by {Nation} ({Player})"
        dualism_query = """
        SELECT DISTINCT
            p.player_id,
            p.player_name,
            e.description,
            (SELECT COALESCE(SUM(COALESCE(c.religion_count, 2)), 0)
             FROM cities c WHERE c.match_id = p.match_id AND c.player_id = p.player_id
            ) as total_religions
        FROM events e
        JOIN players p ON e.match_id = p.match_id AND e.player_id = p.player_id
        WHERE e.match_id = ?
          AND e.event_type = 'THEOLOGY_ESTABLISHED'
          AND (e.description LIKE '%Dualism%' OR e.description LIKE '%Dualismus%')
        """
        with self.db.get_connection() as conn:
            dualism_df = conn.execute(dualism_query, [match_id]).df()

        if not dualism_df.empty:
            for player_id in dualism_df["player_id"].unique():
                player_rows = dualism_df[dualism_df["player_id"] == player_id]
                player_name = player_rows["player_name"].iloc[0]
                # Count distinct Dualism theologies (could be multiple religions)
                dualism_count = len(player_rows)
                # Use actual total religion count from database, or estimate 2 per city
                total_religions = int(player_rows["total_religions"].iloc[0]) if player_rows["total_religions"].iloc[0] else 0
                # +10 per religion level across all cities
                total_bonus = 10 * total_religions if total_religions > 0 else 10 * dualism_count * 2
                results.append(
                    {
                        "player_id": player_id,
                        "player_name": player_name,
                        "bonus_type": "theology",
                        "bonus_source": "Dualism",
                        "science_value": total_bonus,
                        "details": f"+10×{total_religions} religions ({dualism_count} Dualism theolog{'ies' if dualism_count > 1 else 'y'})",
                    }
                )

        return pd.DataFrame(results)

    def get_science_total_estimate(self, match_id: int) -> pd.DataFrame:
        """Get estimated total science production per player.

        Combines all science sources and modifiers into an estimate,
        along with the actual science rate and happiness penalty from yield history.

        Args:
            match_id: Match to query

        Returns:
            DataFrame with columns:
                - player_id: Player identifier
                - player_name: Player name
                - specialists_science: Science from specialists (display units)
                - improvements_science: Science from improvements (display units)
                - projects_science: Science from city projects (display units)
                - bonuses_science: Science from nation/laws (display units)
                - base_science: Total before modifiers (display units)
                - modifier_percent: Total modifier percentage (positive bonuses)
                - estimated_total: Final estimated science/turn (from tracked sources)
                - actual_science: Actual science/turn from yield history
                - net_happiness: Net happiness value (negative = unhappy)
                - happiness_penalty_pct: Estimated penalty % from unhappiness
        """
        # Get per-city science breakdown with modifiers applied
        city_science_df = self.get_science_by_city(match_id)

        # Get empire-wide bonuses (Competitive Mode, laws)
        bonuses_df = self.get_science_bonuses_summary(match_id)

        # Get player list with actual science rate and happiness from final turn
        players_query = """
        WITH final_science AS (
            SELECT
                yh.player_id,
                yh.amount / 10.0 as actual_science
            FROM player_yield_history yh
            WHERE yh.match_id = ?
              AND yh.resource_type = 'YIELD_SCIENCE'
              AND yh.turn_number = (
                  SELECT MAX(turn_number)
                  FROM player_yield_history
                  WHERE match_id = yh.match_id
                    AND player_id = yh.player_id
                    AND resource_type = 'YIELD_SCIENCE'
              )
        ),
        final_happiness AS (
            SELECT
                yh.player_id,
                yh.amount / 10.0 as net_happiness
            FROM player_yield_history yh
            WHERE yh.match_id = ?
              AND yh.resource_type = 'YIELD_HAPPINESS'
              AND yh.turn_number = (
                  SELECT MAX(turn_number)
                  FROM player_yield_history
                  WHERE match_id = yh.match_id
                    AND player_id = yh.player_id
                    AND resource_type = 'YIELD_HAPPINESS'
              )
        )
        SELECT
            p.player_id,
            p.player_name,
            COALESCE(fs.actual_science, 0) as actual_science,
            COALESCE(fh.net_happiness, 0) as net_happiness
        FROM players p
        LEFT JOIN final_science fs ON p.player_id = fs.player_id
        LEFT JOIN final_happiness fh ON p.player_id = fh.player_id
        WHERE p.match_id = ?
        """
        with self.db.get_connection() as conn:
            players_df = conn.execute(
                players_query, [match_id, match_id, match_id]
            ).df()

        results = []
        for _, player in players_df.iterrows():
            pid = player["player_id"]
            pname = player["player_name"]
            actual = player["actual_science"]
            net_happiness = player["net_happiness"]

            # Calculate happiness penalty (-5% per level of negative happiness)
            happiness_penalty_pct = 0
            if net_happiness < 0:
                happiness_levels = int(abs(net_happiness) / 10)
                happiness_penalty_pct = happiness_levels * 5

            # Get per-city totals for this player
            player_cities = city_science_df[city_science_df["player_id"] == pid]

            if not player_cities.empty:
                # Sum raw values from cities (includes Sages bonus, before modifiers)
                specialist_science = player_cities["specialist_science"].sum()
                improvement_science = player_cities["improvement_science"].sum()
                project_science = player_cities["project_science"].sum()
                sages_bonus = player_cities["sages_bonus"].sum()

                # Sum modified science (modifiers already applied per-city)
                city_modified_total = player_cities["modified_science"].sum()

                # Calculate average modifier for display
                base_total = player_cities["base_science"].sum()
                if base_total > 0:
                    avg_modifier = ((city_modified_total / base_total) - 1) * 100
                else:
                    avg_modifier = 0
            else:
                specialist_science = 0
                improvement_science = 0
                project_science = 0
                sages_bonus = 0
                city_modified_total = 0
                avg_modifier = 0

            # Add empire-wide bonuses (Competitive Mode, Centralization, Constitution, Philosophy)
            # These are NOT subject to city modifiers
            bonus_science = 0
            if not bonuses_df.empty:
                player_bonuses = bonuses_df[bonuses_df["player_id"] == pid]
                bonus_science = player_bonuses["science_value"].sum()

            # Convert from raw XML values to display values (divide by 10)
            specialist_science_display = specialist_science / 10.0
            improvement_science_display = improvement_science / 10.0
            project_science_display = project_science / 10.0
            sages_bonus_display = sages_bonus / 10.0
            bonus_science_display = bonus_science / 10.0
            city_modified_display = city_modified_total / 10.0

            # Base science = city production (without modifiers) + empire bonuses
            base_science = (
                specialist_science + improvement_science + project_science + sages_bonus
            ) / 10.0 + bonus_science_display

            # Estimated total = city production (with modifiers) + empire bonuses
            estimated_total = city_modified_display + bonus_science_display

            results.append(
                {
                    "player_id": pid,
                    "player_name": pname,
                    "specialists_science": specialist_science_display,
                    "improvements_science": improvement_science_display,
                    "projects_science": project_science_display + sages_bonus_display,
                    "bonuses_science": bonus_science_display,
                    "base_science": round(base_science, 1),
                    "modifier_percent": round(avg_modifier, 1),
                    "estimated_total": round(estimated_total, 1),
                    "actual_science": actual,
                    "net_happiness": net_happiness,
                    "happiness_penalty_pct": happiness_penalty_pct,
                }
            )

        return pd.DataFrame(results)

    def get_science_breakdown_for_chart(self, match_id: int) -> pd.DataFrame:
        """Get science breakdown with post-modifier values for chart display.

        Each category shows science AFTER city modifiers are applied.
        Empire bonuses are separate (not affected by city modifiers).
        Happiness penalty is calculated based on net happiness (-5% per 20 unhappiness).

        Args:
            match_id: Match to query

        Returns:
            DataFrame with columns:
                - player_id, player_name
                - base_city_science: Post-modifier base city science (+10/city)
                - specialists_science: Post-modifier specialist science
                - improvements_science: Post-modifier improvement science
                - projects_science: Post-modifier project + sages bonus
                - bonuses_science: Empire-wide bonuses (NOT modified, display units)
                - happiness_penalty: Negative value from unhappiness (-5% per 20)
                - total_science: Sum of all categories (before penalty)
                - net_science: total_science + happiness_penalty
                - actual_science: From yield history
                - tooltip_data: Dict with breakdown details for tooltips
        """
        import json

        # Get per-city science breakdown with modifiers
        city_df = self.get_science_by_city(match_id)

        # Get empire-wide bonuses
        bonuses_df = self.get_science_bonuses_summary(match_id)

        # Get actual science and happiness from yield history
        actual_query = """
        SELECT
            p.player_id,
            p.player_name,
            COALESCE((
                SELECT yh.amount / 10.0
                FROM player_yield_history yh
                WHERE yh.match_id = p.match_id
                  AND yh.player_id = p.player_id
                  AND yh.resource_type = 'YIELD_SCIENCE'
                  AND yh.turn_number = (
                      SELECT MAX(turn_number)
                      FROM player_yield_history
                      WHERE match_id = yh.match_id
                        AND player_id = yh.player_id
                        AND resource_type = 'YIELD_SCIENCE'
                  )
            ), 0) as actual_science,
            COALESCE((
                SELECT yh.amount / 10.0
                FROM player_yield_history yh
                WHERE yh.match_id = p.match_id
                  AND yh.player_id = p.player_id
                  AND yh.resource_type = 'YIELD_HAPPINESS'
                  AND yh.turn_number = (
                      SELECT MAX(turn_number)
                      FROM player_yield_history
                      WHERE match_id = yh.match_id
                        AND player_id = yh.player_id
                        AND resource_type = 'YIELD_HAPPINESS'
                  )
            ), 0) as net_happiness
        FROM players p
        WHERE p.match_id = ?
        """
        with self.db.get_connection() as conn:
            actual_df = conn.execute(actual_query, [match_id]).df()

        results = []
        for _, player in actual_df.iterrows():
            pid = player["player_id"]
            pname = player["player_name"]
            actual = player["actual_science"]

            # Get this player's cities
            player_cities = city_df[city_df["player_id"] == pid]

            # Initialize category totals (raw values, will convert to display at end)
            base_city_modified = 0.0
            specialists_modified = 0.0
            improvements_modified = 0.0
            projects_modified = 0.0  # Includes sages_bonus

            # Tooltip detail builders
            city_count = len(player_cities)
            modifier_sum = 0.0
            modifier_count = 0

            if not player_cities.empty:
                for _, city in player_cities.iterrows():
                    # Get modifier factor for this city
                    total_mod = float(city.get("total_modifier", 0) or 0)
                    modifier_factor = 1 + total_mod / 100

                    # Track for average modifier calculation
                    modifier_sum += total_mod
                    modifier_count += 1

                    # Base city science (+10 per city, affected by modifier)
                    base_raw = float(city.get("base_city_science", 10) or 10)
                    base_city_modified += base_raw * modifier_factor

                    # Specialists (specialist_science + doctor_science, NO sages)
                    spec_raw = float(city.get("specialist_science", 0) or 0) + float(
                        city.get("doctor_science", 0) or 0
                    )
                    specialists_modified += spec_raw * modifier_factor

                    # Improvements
                    imp_raw = float(city.get("improvement_science", 0) or 0)
                    improvements_modified += imp_raw * modifier_factor

                    # Projects (archives + other projects + sages_bonus)
                    proj_raw = (
                        float(city.get("project_science", 0) or 0)
                        + float(city.get("other_project_science", 0) or 0)
                        + float(city.get("sages_bonus", 0) or 0)
                    )
                    projects_modified += proj_raw * modifier_factor

            # Convert to display values (divide by 10)
            base_city_display = base_city_modified / 10.0
            specialists_display = specialists_modified / 10.0
            improvements_display = improvements_modified / 10.0
            projects_display = projects_modified / 10.0

            # Average modifier for tooltip
            avg_modifier = modifier_sum / modifier_count if modifier_count > 0 else 0

            # Empire bonuses (not affected by city modifiers)
            # Note: bonuses_df science_value is in RAW units, divide by 10
            bonuses_raw = 0.0
            bonus_list: list[dict[str, Any]] = []
            if not bonuses_df.empty:
                player_bonuses = bonuses_df[bonuses_df["player_id"] == pid]
                bonuses_raw = float(player_bonuses["science_value"].sum())
                for _, bonus in player_bonuses.iterrows():
                    bonus_list.append(
                        {
                            "source": bonus["bonus_source"],
                            "value": float(bonus["science_value"]) / 10.0,  # Display
                            "details": bonus.get("details", ""),
                        }
                    )
            bonuses_display = bonuses_raw / 10.0

            # Total science from tracked sources (before happiness penalty)
            total_science = (
                base_city_display
                + specialists_display
                + improvements_display
                + projects_display
                + bonuses_display
            )

            # Calculate happiness penalty
            # From yield.xml: iNegativeHappinessModifier = -5 (per level)
            # Based on data analysis: 1 level = 20 happiness points
            net_happiness = float(player.get("net_happiness", 0) or 0)
            happiness_penalty = 0.0
            happiness_penalty_pct = 0.0
            if net_happiness < 0:
                # Calculate penalty: -5% per 20 unhappiness
                happiness_levels = abs(net_happiness) / 20.0
                happiness_penalty_pct = happiness_levels * 5.0
                # Apply penalty to total science (as negative value)
                happiness_penalty = -total_science * (happiness_penalty_pct / 100.0)

            # Net science after happiness penalty
            net_science = total_science + happiness_penalty

            # Build tooltip data
            tooltip_data = {
                "city_count": city_count,
                "avg_modifier": round(avg_modifier, 1),
                "bonuses": bonus_list,
                "net_happiness": round(net_happiness, 1),
                "happiness_penalty_pct": round(happiness_penalty_pct, 1),
            }

            results.append(
                {
                    "player_id": pid,
                    "player_name": pname,
                    "base_city_science": round(base_city_display, 1),
                    "specialists_science": round(specialists_display, 1),
                    "improvements_science": round(improvements_display, 1),
                    "projects_science": round(projects_display, 1),
                    "bonuses_science": round(bonuses_display, 1),
                    "happiness_penalty": round(happiness_penalty, 1),
                    "total_science": round(total_science, 1),
                    "net_science": round(net_science, 1),
                    "actual_science": round(actual, 1),
                    "tooltip_data": json.dumps(tooltip_data),
                }
            )

        return pd.DataFrame(results)

    def get_science_by_city(
        self, match_id: int, turn_number: Optional[int] = None
    ) -> pd.DataFrame:
        """Get per-city science breakdown with modifiers correctly applied.

        Calculates science at the city level, applying modifiers (Library, Musaeum,
        Scientific Method, Clerics steles) to each city's base science before summing.

        Args:
            match_id: Match to query
            turn_number: Turn to get data for (default: final turn)

        Returns:
            DataFrame with columns:
                - player_id: Player identifier
                - player_name: Player name
                - city_id: City identifier
                - city_name: City name
                - family_name: City's family
                - is_capital: Whether this is the capital
                - culture_level: City culture level (1-4)
                - culture_level_modifier: Culture modifier % (10/20/50/100)
                - specialist_science: Raw science from specialists
                - improvement_science: Raw science from improvements
                - project_science: Raw science from city projects (Archives)
                - sages_bonus: Bonus from Sages family (+10 per specialist)
                - base_science: Total before modifiers
                - library_modifier: Library modifier % (highest tier)
                - musaeum_modifier: Musaeum modifier % (50 if present)
                - scientific_method_modifier: Scientific Method modifier % (10 if present)
                - clerics_stele_modifier: Clerics stele modifier % (10 if Clerics family)
                - total_modifier: Sum of all modifiers (including culture level)
                - modified_science: base_science * (1 + total_modifier/100)
        """
        if turn_number is None:
            _, max_turn = self.get_territory_turn_range(match_id)
            turn_number = max_turn

        # Build list of science-producing improvements for SQL
        science_improvements = (
            "'IMPROVEMENT_WATERMILL', 'IMPROVEMENT_WINDMILL', "
            "'IMPROVEMENT_MONASTERY_CHRISTIANITY', 'IMPROVEMENT_MONASTERY_JUDAISM', "
            "'IMPROVEMENT_MONASTERY_MANICHAEISM', 'IMPROVEMENT_MONASTERY_ZOROASTRIANISM', "
            "'IMPROVEMENT_SHRINE_NABU', 'IMPROVEMENT_SHRINE_ATHENA'"
        )

        # Build Sages family list for SQL
        sages_list = ", ".join(f"'{f}'" for f in SAGES_FAMILIES)

        # Build Clerics family list for SQL
        clerics_list = ", ".join(f"'{f}'" for f in CLERICS_FAMILIES)

        query = f"""
        WITH player_order AS (
            SELECT
                match_id,
                player_id,
                player_name,
                ROW_NUMBER() OVER (
                    PARTITION BY match_id ORDER BY player_id
                ) as match_player_order
            FROM players
        ),
        -- Get specialists by city
        city_specialists AS (
            SELECT
                t.city_id,
                t.specialist_type,
                COUNT(*) as count
            FROM territories t
            WHERE t.match_id = ?
              AND t.turn_number = ?
              AND t.city_id IS NOT NULL
              AND t.specialist_type IS NOT NULL
            GROUP BY t.city_id, t.specialist_type
        ),
        -- Get science-producing improvements by city
        city_improvements AS (
            SELECT
                t.city_id,
                t.improvement_type,
                COUNT(*) as count
            FROM territories t
            WHERE t.match_id = ?
              AND t.turn_number = ?
              AND t.city_id IS NOT NULL
              AND t.improvement_type IN ({science_improvements})
            GROUP BY t.city_id, t.improvement_type
        ),
        -- Get Library modifiers by city (highest tier only)
        city_libraries AS (
            SELECT
                t.city_id,
                MAX(CASE
                    WHEN t.improvement_type = 'IMPROVEMENT_LIBRARY_3' THEN 30
                    WHEN t.improvement_type = 'IMPROVEMENT_LIBRARY_2' THEN 20
                    WHEN t.improvement_type = 'IMPROVEMENT_LIBRARY_1' THEN 10
                    ELSE 0
                END) as library_modifier
            FROM territories t
            WHERE t.match_id = ?
              AND t.turn_number = ?
              AND t.city_id IS NOT NULL
              AND t.improvement_type LIKE 'IMPROVEMENT_LIBRARY%'
            GROUP BY t.city_id
        ),
        -- Get Musaeum by city
        city_musaeum AS (
            SELECT
                t.city_id,
                50 as musaeum_modifier
            FROM territories t
            WHERE t.match_id = ?
              AND t.turn_number = ?
              AND t.city_id IS NOT NULL
              AND t.improvement_type = 'IMPROVEMENT_MUSAEUM'
            GROUP BY t.city_id
        ),
        -- Get Scientific Method projects by city
        city_scientific_method AS (
            SELECT
                cp.city_id,
                10 as scientific_method_modifier
            FROM city_projects cp
            WHERE cp.match_id = ?
              AND cp.project_type = 'PROJECT_SCIENTIFIC_METHOD'
        ),
        -- Get other science modifier projects by city
        city_other_modifiers AS (
            SELECT
                cp.city_id,
                SUM(CASE
                    WHEN cp.project_type = 'PROJECT_MIDWIFERY' THEN 20
                    WHEN cp.project_type = 'PROJECT_PAGAN_COLLEGES' THEN 20
                    WHEN cp.project_type = 'PROJECT_PAGAN_CULT_WISDOM' THEN 20
                    WHEN cp.project_type = 'PROJECT_AVESTA_TREASURY' THEN 10
                    WHEN cp.project_type = 'PROJECT_TERRACE_WISDOM_SHRINE' THEN 10
                    ELSE 0
                END) as other_modifier
            FROM city_projects cp
            WHERE cp.match_id = ?
              AND cp.project_type IN (
                  'PROJECT_MIDWIFERY', 'PROJECT_PAGAN_COLLEGES',
                  'PROJECT_PAGAN_CULT_WISDOM', 'PROJECT_AVESTA_TREASURY',
                  'PROJECT_TERRACE_WISDOM_SHRINE'
              )
            GROUP BY cp.city_id
        ),
        -- Get Archive projects by city
        city_archives AS (
            SELECT
                cp.city_id,
                MAX(CASE
                    WHEN cp.project_type = 'PROJECT_ARCHIVE_4' THEN 150
                    WHEN cp.project_type = 'PROJECT_ARCHIVE_3' THEN 70
                    WHEN cp.project_type = 'PROJECT_ARCHIVE_2' THEN 30
                    WHEN cp.project_type = 'PROJECT_ARCHIVE_1' THEN 10
                    ELSE 0
                END) as archive_science
            FROM city_projects cp
            WHERE cp.match_id = ?
              AND cp.project_type LIKE 'PROJECT_ARCHIVE%'
            GROUP BY cp.city_id
        ),
        -- Get other science-producing projects by city
        city_other_projects AS (
            SELECT
                cp.city_id,
                SUM(CASE
                    WHEN cp.project_type = 'PROJECT_LOCAL_ASCETIC' THEN 20
                    WHEN cp.project_type = 'PROJECT_GOVERNOR' THEN 20
                    WHEN cp.project_type = 'PROJECT_NEIGHBORS_FEAST_PERSIA' THEN 20
                    WHEN cp.project_type = 'PROJECT_CONVOY' THEN 10
                    ELSE 0
                END) as other_project_science
            FROM city_projects cp
            WHERE cp.match_id = ?
              AND cp.project_type IN (
                  'PROJECT_LOCAL_ASCETIC', 'PROJECT_GOVERNOR',
                  'PROJECT_NEIGHBORS_FEAST_PERSIA', 'PROJECT_CONVOY'
              )
            GROUP BY cp.city_id
        )
        SELECT
            p.player_id,
            p.player_name,
            c.city_id,
            c.city_name,
            c.family_name,
            c.is_capital,
            c.culture_level,
            -- Culture level modifier: Weak=10%, Developing=20%, Strong=50%, Legendary=100%
            CASE c.culture_level
                WHEN 1 THEN 10
                WHEN 2 THEN 20
                WHEN 3 THEN 50
                WHEN 4 THEN 100
                ELSE 0  -- No modifier if culture level unknown
            END as culture_level_modifier,
            -- Base city science: every city generates +10 science (EFFECTCITY_BASE)
            10 as base_city_science,
            -- ALL specialists give science via EffectCityExtra bonuses!
            -- Rural specialists: +10 (EFFECTCITY_SPECIALIST_RURAL)
            -- Woodcutter: +10 (rural) + 10 (woodcutter effect) = +20
            -- Urban tier 1 (_1): +20 (EFFECTCITY_SPECIALIST_APPRENTICE)
            -- Urban tier 2 (_2): +30 (EFFECTCITY_SPECIALIST_MASTER)
            -- Urban tier 3 (_3): +40 (EFFECTCITY_SPECIALIST_ELDER)
            -- Philosophers add extra: +20/30/40 on top of apprentice/master/elder
            COALESCE((
                SELECT SUM(
                    cs.count * CASE
                        -- Philosophers: base + apprentice/master/elder
                        WHEN cs.specialist_type = 'SPECIALIST_PHILOSOPHER_3' THEN 80  -- 40 + 40
                        WHEN cs.specialist_type = 'SPECIALIST_PHILOSOPHER_2' THEN 60  -- 30 + 30
                        WHEN cs.specialist_type = 'SPECIALIST_PHILOSOPHER_1' THEN 40  -- 20 + 20
                        -- Woodcutter: rural + woodcutter effect
                        WHEN cs.specialist_type = 'SPECIALIST_WOODCUTTER' THEN 20  -- 10 + 10
                        -- Other rural specialists
                        WHEN cs.specialist_type IN ('SPECIALIST_FARMER', 'SPECIALIST_MINER',
                            'SPECIALIST_STONECUTTER', 'SPECIALIST_RANCHER', 'SPECIALIST_TRAPPER',
                            'SPECIALIST_GARDENER', 'SPECIALIST_FISHER') THEN 10
                        -- Urban tier 3 specialists (elder bonus)
                        WHEN cs.specialist_type LIKE '%_3' THEN 40
                        -- Urban tier 2 specialists (master bonus)
                        WHEN cs.specialist_type LIKE '%_2' THEN 30
                        -- Urban tier 1 specialists (apprentice bonus)
                        WHEN cs.specialist_type LIKE '%_1' THEN 20
                        ELSE 0
                    END
                )
                FROM city_specialists cs
                WHERE cs.city_id = c.city_id
            ), 0) as specialist_science,
            -- Doctor specialists give science based on culture level
            -- DOCTOR_2: +10 × culture, DOCTOR_3: +20 × culture
            COALESCE((
                SELECT SUM(
                    cs.count * CASE
                        WHEN cs.specialist_type = 'SPECIALIST_DOCTOR_3' THEN 20
                        WHEN cs.specialist_type = 'SPECIALIST_DOCTOR_2' THEN 10
                        ELSE 0
                    END
                ) * COALESCE(c.culture_level, 2)
                FROM city_specialists cs
                WHERE cs.city_id = c.city_id
            ), 0) as doctor_science,
            -- Improvement science
            COALESCE((
                SELECT SUM(
                    ci.count * CASE
                        WHEN ci.improvement_type LIKE 'IMPROVEMENT_MONASTERY%' THEN 20
                        WHEN ci.improvement_type IN ('IMPROVEMENT_WATERMILL', 'IMPROVEMENT_WINDMILL') THEN 20
                        WHEN ci.improvement_type LIKE 'IMPROVEMENT_SHRINE%' THEN 10
                        ELSE 0
                    END
                )
                FROM city_improvements ci
                WHERE ci.city_id = c.city_id
            ), 0) as improvement_science,
            -- Project science (Archives)
            COALESCE(ca.archive_science, 0) as project_science,
            -- Other projects that give science (Local Ascetic, Governor, Convoy, etc.)
            COALESCE(cop.other_project_science, 0) as other_project_science,
            -- Sages bonus: +10 per specialist in Sages family cities
            CASE
                WHEN c.family_name IN ({sages_list}) THEN
                    COALESCE((
                        SELECT SUM(cs.count) * 10
                        FROM city_specialists cs
                        WHERE cs.city_id = c.city_id
                    ), 0)
                ELSE 0
            END as sages_bonus,
            -- Library modifier
            COALESCE(cl.library_modifier, 0) as library_modifier,
            -- Musaeum modifier
            COALESCE(cm.musaeum_modifier, 0) as musaeum_modifier,
            -- Scientific Method modifier
            COALESCE(csm.scientific_method_modifier, 0) as scientific_method_modifier,
            -- Other project modifiers (Midwifery, Pagan Colleges, etc.)
            COALESCE(com.other_modifier, 0) as other_project_modifier,
            -- Clerics stele modifier (conservative +10% for Clerics family cities)
            CASE
                WHEN c.family_name IN ({clerics_list}) THEN 10
                ELSE 0
            END as clerics_stele_modifier
        FROM cities c
        JOIN player_order p ON c.match_id = p.match_id AND c.player_id = p.player_id
        LEFT JOIN city_libraries cl ON c.city_id = cl.city_id
        LEFT JOIN city_musaeum cm ON c.city_id = cm.city_id
        LEFT JOIN city_scientific_method csm ON c.city_id = csm.city_id
        LEFT JOIN city_other_modifiers com ON c.city_id = com.city_id
        LEFT JOIN city_archives ca ON c.city_id = ca.city_id
        LEFT JOIN city_other_projects cop ON c.city_id = cop.city_id
        WHERE c.match_id = ?
        ORDER BY p.player_name, c.city_id
        """

        with self.db.get_connection() as conn:
            df = conn.execute(
                query,
                [
                    match_id,
                    turn_number,  # city_specialists
                    match_id,
                    turn_number,  # city_improvements
                    match_id,
                    turn_number,  # city_libraries
                    match_id,
                    turn_number,  # city_musaeum
                    match_id,  # city_scientific_method
                    match_id,  # city_other_modifiers
                    match_id,  # city_archives
                    match_id,  # city_other_projects
                    match_id,  # main query
                ],
            ).df()

        if df.empty:
            return df

        # Calculate derived columns
        df["base_science"] = (
            df["base_city_science"]  # +10 per city (EFFECTCITY_BASE)
            + df["specialist_science"]
            + df["doctor_science"]  # Doctors give science × culture level
            + df["improvement_science"]
            + df["project_science"]
            + df["other_project_science"]  # Local Ascetic, Governor, Convoy, etc.
            + df["sages_bonus"]
        )
        df["total_modifier"] = (
            df["culture_level_modifier"]
            + df["library_modifier"]
            + df["musaeum_modifier"]
            + df["scientific_method_modifier"]
            + df["other_project_modifier"]  # Midwifery, Pagan Colleges, etc.
            + df["clerics_stele_modifier"]
        )
        df["modified_science"] = df["base_science"] * (1 + df["total_modifier"] / 100.0)

        return df

    def get_match_cities(self, match_id: int) -> pd.DataFrame:
        """Get all cities for a specific match.

        Args:
            match_id: Tournament match ID

        Returns:
            DataFrame with columns:
                - city_id: City identifier
                - city_name: City name (e.g., 'CITYNAME_NINEVEH')
                - player_id: Current owner player ID
                - player_name: Current owner player name
                - founded_turn: Turn when city was founded
                - is_capital: Boolean, TRUE if capital city
                - population: City population (may be NULL)
                - tile_id: Map tile location
        """
        query = """
        SELECT
            c.city_id,
            c.city_name,
            c.player_id,
            p.player_name,
            c.founded_turn,
            c.is_capital,
            c.population,
            c.tile_id
        FROM cities c
        JOIN players p ON c.match_id = p.match_id AND c.player_id = p.player_id
        WHERE c.match_id = ?
        ORDER BY c.founded_turn, c.city_id
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id]).df()

    def get_player_expansion_stats(self, match_id: int) -> pd.DataFrame:
        """Get expansion statistics for each player in a match.

        Args:
            match_id: Tournament match ID

        Returns:
            DataFrame with columns:
                - player_id: Player identifier
                - player_name: Player name
                - total_cities: Total number of cities owned
                - first_city_turn: Turn when first city was founded
                - last_city_turn: Turn when last city was founded
                - capital_count: Number of capital cities
        """
        query = """
        SELECT
            p.player_id,
            p.player_name,
            COUNT(c.city_id) as total_cities,
            MIN(c.founded_turn) as first_city_turn,
            MAX(c.founded_turn) as last_city_turn,
            SUM(CASE WHEN c.is_capital THEN 1 ELSE 0 END) as capital_count
        FROM players p
        LEFT JOIN cities c ON p.match_id = c.match_id AND p.player_id = c.player_id
        WHERE p.match_id = ?
        GROUP BY p.player_id, p.player_name
        ORDER BY total_cities DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id]).df()

    def get_family_city_counts(self, match_id: int) -> pd.DataFrame:
        """Get city counts grouped by family for each player.

        Args:
            match_id: Tournament match ID

        Returns:
            DataFrame with columns:
                - player_id: Player identifier
                - player_name: Player name
                - family_name: Family internal name (e.g., FAMILY_BARCID)
                - city_count: Number of cities owned by this family
        """
        query = """
        SELECT
            p.player_id,
            p.player_name,
            c.family_name,
            COUNT(c.city_id) as city_count
        FROM players p
        LEFT JOIN cities c ON p.match_id = c.match_id AND p.player_id = c.player_id
        WHERE p.match_id = ?
            AND c.family_name IS NOT NULL
        GROUP BY p.player_id, p.player_name, c.family_name
        ORDER BY p.player_id, city_count DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id]).df()

    def get_production_summary(self, match_id: int) -> pd.DataFrame:
        """Get unit production summary for each player.

        Args:
            match_id: Tournament match ID

        Returns:
            DataFrame with columns:
                - player_id: Player identifier
                - player_name: Player name
                - total_units_produced: Total units produced across all cities
                - unique_unit_types: Number of different unit types produced
                - settlers: Total settler units produced
                - workers: Total worker units produced
        """
        query = """
        SELECT
            p.player_id,
            p.player_name,
            COALESCE(SUM(prod.count), 0) as total_units_produced,
            COUNT(DISTINCT prod.unit_type) as unique_unit_types,
            COALESCE(SUM(CASE WHEN prod.unit_type = 'UNIT_SETTLER' THEN prod.count ELSE 0 END), 0) as settlers,
            COALESCE(SUM(CASE WHEN prod.unit_type = 'UNIT_WORKER' THEN prod.count ELSE 0 END), 0) as workers
        FROM players p
        LEFT JOIN cities c ON p.match_id = c.match_id AND p.player_id = c.player_id
        LEFT JOIN city_unit_production prod ON c.match_id = prod.match_id AND c.city_id = prod.city_id
        WHERE p.match_id = ?
        GROUP BY p.player_id, p.player_name
        ORDER BY total_units_produced DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id]).df()

    def get_match_units_produced(self, match_id: int) -> pd.DataFrame:
        """Get detailed unit production for a specific match.

        Returns all units produced by each player with classification info.

        Args:
            match_id: Tournament match ID

        Returns:
            DataFrame with columns:
                - player_id: Player identifier
                - player_name: Player name
                - unit_type: Unit type (e.g., UNIT_WARRIOR)
                - unit_name: Human-readable unit name
                - count: Number of units produced
                - category: Unit category (military, civilian, religious)
                - role: Unit role (infantry, ranged, cavalry, etc.)
        """
        query = """
        SELECT
            p.player_id,
            p.player_name,
            up.unit_type,
            REPLACE(REPLACE(up.unit_type, 'UNIT_', ''), '_', ' ') as unit_name,
            up.count,
            COALESCE(uc.category, 'unknown') as category,
            COALESCE(uc.role, 'unknown') as role
        FROM units_produced up
        JOIN players p ON up.match_id = p.match_id AND up.player_id = p.player_id
        LEFT JOIN unit_classifications uc ON up.unit_type = uc.unit_type
        WHERE up.match_id = ?
        ORDER BY p.player_name, uc.category, uc.role, up.count DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id]).df()

    def get_tournament_expansion_timeline(
        self,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> pd.DataFrame:
        """Get average cumulative city count over time for all players.

        Analyzes expansion strategies by showing how quickly players founded cities.
        For players who played multiple matches as the same civilization, returns
        the average cumulative count at each founding turn.

        Args:
            tournament_round: Filter by tournament round number (e.g., 1, 2, -1, -2)
            bracket: Filter by bracket ('Winners', 'Losers', 'Unknown')
            min_turns: Filter by minimum total turns
            max_turns: Filter by maximum total turns
            map_size: Filter by map size
            map_class: Filter by map class
            map_aspect: Filter by map aspect ratio
            nations: Filter by civilizations played
            players: Filter by player names
            result_filter: Filter by match result (winners/losers/all)

        Returns:
            DataFrame with columns:
                - player_name: Player name
                - civilization: Player's civilization
                - founded_turn: Turn when city was founded
                - cumulative_cities: Average cities founded up to this turn
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=result_filter,
        )

        if not filtered:
            return pd.DataFrame()

        # Build player-level filter (handles both match-only and match+player filtering)
        where_clause, params = self._build_player_filter(
            filtered, result_filter, table_alias="p"
        )

        # Calculate cumulative cities per match, then average across matches
        # for players who played multiple games as the same civilization
        query = f"""
        WITH per_match_cumulative AS (
            -- Calculate cumulative count within each match
            SELECT
                c.match_id,
                p.player_name,
                p.civilization,
                c.founded_turn,
                COUNT(*) OVER (
                    PARTITION BY c.match_id, p.player_id
                    ORDER BY c.founded_turn
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) as cumulative_cities
            FROM cities c
            JOIN players p ON c.match_id = p.match_id AND c.player_id = p.player_id
            WHERE {where_clause}
        ),
        -- Deduplicate: multiple cities on same turn create duplicate rows
        per_match_per_turn AS (
            SELECT DISTINCT
                match_id,
                player_name,
                civilization,
                founded_turn,
                cumulative_cities
            FROM per_match_cumulative
        )
        SELECT
            player_name,
            civilization,
            founded_turn,
            ROUND(AVG(cumulative_cities), 1) as cumulative_cities
        FROM per_match_per_turn
        GROUP BY player_name, civilization, founded_turn
        ORDER BY player_name, civilization, founded_turn
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, params).df()

    def get_tournament_city_founding_distribution(self) -> pd.DataFrame:
        """Get distribution of city foundings across turn ranges.

        Shows how many cities were founded in early game vs. mid game vs. late game.
        Useful for understanding tournament-wide expansion timing patterns.

        Returns:
            DataFrame with columns:
                - turn_range: Turn range bucket (e.g., '1-20', '21-40')
                - city_count: Number of cities founded in this range
                - percentage: Percentage of all cities founded in this range
        """
        query = """
        WITH turn_buckets AS (
            SELECT
                CASE
                    WHEN founded_turn <= 20 THEN '1-20'
                    WHEN founded_turn <= 40 THEN '21-40'
                    WHEN founded_turn <= 60 THEN '41-60'
                    WHEN founded_turn <= 80 THEN '61-80'
                    WHEN founded_turn <= 100 THEN '81-100'
                    ELSE '101+'
                END as turn_range,
                COUNT(*) as city_count
            FROM cities
            GROUP BY turn_range
        ),
        total AS (
            SELECT COUNT(*) as total_cities FROM cities
        )
        SELECT
            turn_range,
            city_count,
            ROUND(city_count * 100.0 / total_cities, 1) as percentage
        FROM turn_buckets, total
        ORDER BY
            CASE turn_range
                WHEN '1-20' THEN 1
                WHEN '21-40' THEN 2
                WHEN '41-60' THEN 3
                WHEN '61-80' THEN 4
                WHEN '81-100' THEN 5
                ELSE 6
            END
        """

        with self.db.get_connection() as conn:
            return conn.execute(query).df()

    def get_tournament_production_strategies(
        self,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> pd.DataFrame:
        """Get average production strategies for all players across the tournament.

        Calculates production per match first, then averages across matches for
        players who played multiple games as the same civilization.

        Args:
            tournament_round: Filter by tournament round number (e.g., 1, 2, -1, -2)
            bracket: Filter by bracket ('Winners', 'Losers', 'Unknown')
            min_turns: Filter by minimum total turns
            max_turns: Filter by maximum total turns
            map_size: Filter by map size
            map_class: Filter by map class
            map_aspect: Filter by map aspect ratio
            nations: Filter by civilizations played
            players: Filter by player names
            result_filter: Filter by match result (winners/losers/all)

        Returns:
            DataFrame with columns:
                - player_name: Player name
                - civilization: Player's civilization
                - settlers: Average settler units produced per match
                - workers: Average worker units produced per match
                - disciples: Average disciple units produced per match
                - military: Average military units produced per match
                - projects: Average city projects completed per match
                - total_production: Average total production per match
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=result_filter,
        )

        if not filtered:
            return pd.DataFrame()

        # Build player-level filter (handles both match-only and match+player filtering)
        where_clause, params = self._build_player_filter(
            filtered, result_filter, table_alias="p"
        )

        # Calculate production per match, then average across matches
        query = f"""
        WITH per_match_units AS (
            -- Calculate unit production per match per player
            SELECT
                p.match_id,
                p.player_name,
                p.civilization,
                COALESCE(SUM(CASE WHEN u.unit_type = 'UNIT_SETTLER' THEN u.count ELSE 0 END), 0) as settlers,
                COALESCE(SUM(CASE WHEN u.unit_type = 'UNIT_WORKER' THEN u.count ELSE 0 END), 0) as workers,
                COALESCE(SUM(CASE WHEN u.unit_type LIKE '%_DISCIPLE' THEN u.count ELSE 0 END), 0) as disciples,
                COALESCE(SUM(
                    CASE WHEN u.unit_type NOT IN ('UNIT_SETTLER', 'UNIT_WORKER')
                         AND u.unit_type NOT LIKE '%_DISCIPLE'
                    THEN u.count ELSE 0 END
                ), 0) as military
            FROM players p
            LEFT JOIN units_produced u ON p.match_id = u.match_id AND p.player_id = u.player_id
            WHERE {where_clause}
            GROUP BY p.match_id, p.player_name, p.civilization
        ),
        per_match_projects AS (
            -- Calculate project count per match per player
            SELECT
                p.match_id,
                p.player_name,
                p.civilization,
                COALESCE(SUM(proj.count), 0) as projects
            FROM players p
            LEFT JOIN cities c ON p.match_id = c.match_id AND p.player_id = c.player_id
            LEFT JOIN city_projects proj ON c.match_id = proj.match_id AND c.city_id = proj.city_id
            WHERE {where_clause}
            GROUP BY p.match_id, p.player_name, p.civilization
        ),
        per_match_combined AS (
            -- Combine units and projects per match
            SELECT
                COALESCE(u.match_id, pr.match_id) as match_id,
                COALESCE(u.player_name, pr.player_name) as player_name,
                COALESCE(u.civilization, pr.civilization) as civilization,
                COALESCE(u.settlers, 0) as settlers,
                COALESCE(u.workers, 0) as workers,
                COALESCE(u.disciples, 0) as disciples,
                COALESCE(u.military, 0) as military,
                COALESCE(pr.projects, 0) as projects
            FROM per_match_units u
            FULL OUTER JOIN per_match_projects pr
                ON u.match_id = pr.match_id
                AND u.player_name = pr.player_name
                AND u.civilization = pr.civilization
        )
        SELECT
            player_name,
            civilization,
            ROUND(AVG(settlers), 1) as settlers,
            ROUND(AVG(workers), 1) as workers,
            ROUND(AVG(disciples), 1) as disciples,
            ROUND(AVG(military), 1) as military,
            ROUND(AVG(projects), 1) as projects,
            ROUND(AVG(settlers + workers + disciples + military + projects), 1) as total_production
        FROM per_match_combined
        GROUP BY player_name, civilization
        HAVING AVG(settlers + workers + disciples + military + projects) > 0
        ORDER BY total_production DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, params).df()

    def get_tournament_project_priorities(self) -> pd.DataFrame:
        """Get city project priorities for all players across the tournament.

        Shows which projects players prioritized (forums, treasuries, festivals, etc).

        Returns:
            DataFrame with columns:
                - player_name: Player name
                - civilization: Player's civilization
                - project_type: Project type (e.g., 'PROJECT_FESTIVAL')
                - project_count: Total times this project was completed
        """
        query = """
        SELECT
            p.player_name,
            p.civilization,
            proj.project_type,
            SUM(proj.count) as project_count
        FROM players p
        JOIN cities c ON p.match_id = c.match_id AND p.player_id = c.player_id
        JOIN city_projects proj ON c.match_id = proj.match_id AND c.city_id = proj.city_id
        GROUP BY p.player_name, p.civilization, proj.project_type
        ORDER BY p.player_name, project_count DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query).df()

    def get_tournament_conquest_summary(self) -> pd.DataFrame:
        """Get summary of all city conquests across the tournament.

        Identifies cities that changed ownership (first_player_id != player_id).
        This is rare but strategically significant.

        Returns:
            DataFrame with columns:
                - conqueror_name: Name of player who conquered the city
                - conqueror_civ: Civilization of conqueror
                - original_founder_name: Name of player who founded the city
                - original_founder_civ: Civilization of original founder
                - city_name: Name of conquered city
                - founded_turn: Turn when city was founded
                - match_id: Match where conquest occurred
        """
        query = """
        SELECT
            conqueror.player_name as conqueror_name,
            conqueror.civilization as conqueror_civ,
            founder.player_name as original_founder_name,
            founder.civilization as original_founder_civ,
            c.city_name,
            c.founded_turn,
            c.match_id
        FROM cities c
        JOIN players conqueror ON c.match_id = conqueror.match_id AND c.player_id = conqueror.player_id
        JOIN players founder ON c.match_id = founder.match_id AND c.first_player_id = founder.player_id
        WHERE c.first_player_id IS NOT NULL
          AND c.first_player_id != c.player_id
        ORDER BY c.match_id, c.founded_turn
        """

        with self.db.get_connection() as conn:
            return conn.execute(query).df()

    def _get_winner_player_ids(
        self, match_ids: Optional[List[int]] = None
    ) -> set[Tuple[int, int]]:
        """Get (match_id, player_id) tuples for winners.

        Args:
            match_ids: If provided, filter to only these matches

        Returns:
            Set of (match_id, player_id) tuples for winners
        """
        query = """
            SELECT match_id, winner_player_id
            FROM match_winners
            WHERE winner_player_id IS NOT NULL
        """
        params: Dict[str, Any] = {}

        if match_ids:
            query += " AND match_id = ANY($match_ids)"
            params["match_ids"] = match_ids

        with self.db.get_connection() as conn:
            df = conn.execute(query, params).df()
            if df.empty:
                return set()
            return set(zip(df["match_id"], df["winner_player_id"]))

    def _build_player_filter(
        self,
        filtered: list[int] | list[Tuple[int, int]],
        result_filter: ResultFilter,
        table_alias: str = "p",
    ) -> Tuple[str, Dict[str, Any]]:
        """Build WHERE clause for player filtering based on result_filter.

        Args:
            filtered: Result from _get_filtered_match_ids() - either match_ids
                or (match_id, player_id) tuples
            result_filter: The result filter that was used
            table_alias: Table alias to use (default 'p' for players table)

        Returns:
            Tuple of (where_clause, params) where:
            - where_clause uses the specified table alias
            - params contains the query parameters
        """
        if not filtered:
            return "", {}

        if result_filter in ("winners", "losers"):
            # filtered is list of (match_id, player_id) tuples
            # Use tuple matching to preserve exact pairs
            values_list = ", ".join(f"({m}, {pid})" for m, pid in filtered)
            return (
                f"({table_alias}.match_id, {table_alias}.player_id) IN (VALUES {values_list})",
                {},
            )
        else:
            # filtered is list of match_ids
            return f"{table_alias}.match_id = ANY($match_ids)", {"match_ids": filtered}

    def _extract_match_ids(
        self,
        filtered: list[int] | list[Tuple[int, int]],
        result_filter: ResultFilter,
    ) -> list[int]:
        """Extract match_ids from filtered result for match-level queries.

        Args:
            filtered: Result from _get_filtered_match_ids()
            result_filter: The result filter that was used

        Returns:
            List of unique match_ids
        """
        if result_filter in ("winners", "losers"):
            # filtered is list of (match_id, player_id) tuples
            return list(set(m for m, _ in filtered))
        else:
            # filtered is already list of match_ids
            return filtered

    def _get_filtered_match_ids(
        self,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> list[int] | list[Tuple[int, int]]:
        """Get list of match IDs that match the given filters.

        This is a helper method to avoid duplicating filter logic across queries.
        Returns all match IDs if no filters are provided.

        Args:
            tournament_round: List of round numbers to include
            bracket: Bracket filter
            min_turns: Minimum turns
            max_turns: Maximum turns
            map_size: List of map sizes to include
            map_class: List of map classes to include
            map_aspect: List of map aspect ratios to include
            nations: List of civilizations
            players: List of player names
            result_filter: Filter by match result ("winners", "losers", "all", or None)

        Returns:
            List of match_id integers, or list of (match_id, player_id) tuples
            when result_filter is "winners" or "losers"
        """
        query = "SELECT DISTINCT m.match_id FROM matches m WHERE 1=1"
        params = {}

        # Apply filters (reuse logic from get_matches_by_round)
        if tournament_round and len(tournament_round) > 0:
            query += " AND m.tournament_round = ANY($tournament_round)"
            params["tournament_round"] = tournament_round

        if bracket == "Winners":
            query += " AND m.tournament_round > 0"
        elif bracket == "Losers":
            query += " AND m.tournament_round < 0"
        elif bracket == "Unknown":
            query += " AND m.tournament_round IS NULL"

        if min_turns is not None:
            query += " AND m.total_turns >= $min_turns"
            params["min_turns"] = min_turns
        if max_turns is not None:
            query += " AND m.total_turns <= $max_turns"
            params["max_turns"] = max_turns

        if map_size and len(map_size) > 0:
            query += " AND m.map_size = ANY($map_size)"
            params["map_size"] = map_size
        if map_class and len(map_class) > 0:
            query += " AND m.map_class = ANY($map_class)"
            params["map_class"] = map_class
        if map_aspect and len(map_aspect) > 0:
            query += " AND m.map_aspect_ratio = ANY($map_aspect)"
            params["map_aspect"] = map_aspect

        if nations and len(nations) > 0:
            query += """ AND EXISTS (
                SELECT 1 FROM players p
                WHERE p.match_id = m.match_id
                AND p.civilization = ANY($nations)
            )"""
            params["nations"] = nations

        if players and len(players) > 0:
            query += """ AND EXISTS (
                SELECT 1 FROM players p
                WHERE p.match_id = m.match_id
                AND p.player_name = ANY($players)
            )"""
            params["players"] = players

        with self.db.get_connection() as conn:
            df = conn.execute(query, params).df()
            match_ids = df["match_id"].tolist() if not df.empty else []

        # If no result filter or "all", return match IDs only (existing behavior)
        if result_filter is None or result_filter == "all":
            return match_ids

        if not match_ids:
            return []

        # Get winner (match_id, player_id) pairs
        winner_pairs = self._get_winner_player_ids(match_ids)

        if result_filter == "winners":
            return list(winner_pairs)

        # For losers: only include matches that have winner data
        matches_with_winners = [m for m, _ in winner_pairs]
        if not matches_with_winners:
            return []

        all_players_query = """
            SELECT DISTINCT match_id, player_id
            FROM players
            WHERE match_id = ANY($match_ids)
        """
        with self.db.get_connection() as conn:
            all_players_df = conn.execute(
                all_players_query, {"match_ids": matches_with_winners}
            ).df()

        if all_players_df.empty:
            return []

        all_pairs = set(zip(all_players_df["match_id"], all_players_df["player_id"]))
        loser_pairs = all_pairs - winner_pairs
        return list(loser_pairs)

    def get_matches_by_round(
        self,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> pd.DataFrame:
        """Get matches filtered by tournament round and/or bracket.

        This method uses _get_filtered_match_ids() internally to avoid
        duplicating filtering logic.

        Args:
            tournament_round: Specific round number (positive for Winners, negative for Losers)
            bracket: 'Winners', 'Losers', 'Unknown', or None for all
            min_turns: Minimum number of turns
            max_turns: Maximum number of turns
            map_size: Map size filter
            map_class: Map class filter
            map_aspect: Map aspect ratio filter
            nations: List of civilization names to filter by
            players: List of player names to filter by
            result_filter: Filter by match result (winners/losers/all)

        Returns:
            DataFrame with columns:
                - match_id: Match identifier
                - game_name: Game name
                - save_date: Match date
                - tournament_round: Round number
                - total_turns: Total turns in match
                - challonge_match_id: Challonge match ID
                - bracket: Bracket name (Winners/Losers/Unknown)
                - winner_name: Winner player name
                - map_info: Map information
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=result_filter,
        )

        if not filtered:
            return pd.DataFrame()

        # Match-level query - only needs match_ids
        match_ids = self._extract_match_ids(filtered, result_filter)

        # Get full match details for those IDs
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
            m.tournament_round,
            m.total_turns,
            m.challonge_match_id,
            CASE
                WHEN m.tournament_round > 0 THEN 'Winners'
                WHEN m.tournament_round < 0 THEN 'Losers'
                ELSE 'Unknown'
            END as bracket,
            COALESCE(w.player_name, 'Unknown') as winner_name,
            COALESCE(
                m.map_size || ' ' || COALESCE(m.map_class, '') || ' ' || COALESCE(m.map_aspect_ratio, ''),
                'Unknown'
            ) as map_info
        FROM matches m
        LEFT JOIN ranked_players p1 ON m.match_id = p1.match_id AND p1.player_rank = 1
        LEFT JOIN ranked_players p2 ON m.match_id = p2.match_id AND p2.player_rank = 2
        LEFT JOIN match_winners mw ON m.match_id = mw.match_id
        LEFT JOIN players w ON mw.match_id = w.match_id AND mw.winner_player_id = w.player_id
        WHERE m.match_id = ANY($match_ids)
        ORDER BY m.save_date DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, {"match_ids": match_ids}).df()

    def get_available_rounds(self) -> pd.DataFrame:
        """Get list of tournament rounds that have matches.

        Returns:
            DataFrame with columns:
                - tournament_round: Round number
                - bracket: Bracket name (Winners/Losers/Unknown)
                - match_count: Number of matches in this round
        """
        query = """
        SELECT
            tournament_round,
            CASE
                WHEN tournament_round > 0 THEN 'Winners'
                WHEN tournament_round < 0 THEN 'Losers'
                ELSE 'Unknown'
            END as bracket,
            COUNT(*) as match_count
        FROM matches
        GROUP BY tournament_round
        ORDER BY tournament_round
        """

        with self.db.get_connection() as conn:
            return conn.execute(query).df()

    def get_available_map_sizes(self) -> list[str]:
        """Get list of unique map sizes from matches.

        Returns:
            List of map size strings
        """
        query = """
        SELECT DISTINCT map_size
        FROM matches
        WHERE map_size IS NOT NULL
        ORDER BY map_size
        """
        with self.db.get_connection() as conn:
            df = conn.execute(query).df()
            return df["map_size"].tolist() if not df.empty else []

    def get_available_map_classes(self) -> list[str]:
        """Get list of unique map classes from matches.

        Returns:
            List of map class strings
        """
        query = """
        SELECT DISTINCT map_class
        FROM matches
        WHERE map_class IS NOT NULL
        ORDER BY map_class
        """
        with self.db.get_connection() as conn:
            df = conn.execute(query).df()
            return df["map_class"].tolist() if not df.empty else []

    def get_available_map_aspects(self) -> list[str]:
        """Get list of unique map aspect ratios from matches.

        Returns:
            List of map aspect ratio strings
        """
        query = """
        SELECT DISTINCT map_aspect_ratio
        FROM matches
        WHERE map_aspect_ratio IS NOT NULL
        ORDER BY map_aspect_ratio
        """
        with self.db.get_connection() as conn:
            df = conn.execute(query).df()
            return df["map_aspect_ratio"].tolist() if not df.empty else []

    def get_available_nations(self) -> list[str]:
        """Get list of unique civilizations from players.

        Returns:
            List of civilization names
        """
        query = """
        SELECT DISTINCT civilization
        FROM players
        WHERE civilization IS NOT NULL
        ORDER BY civilization
        """
        with self.db.get_connection() as conn:
            df = conn.execute(query).df()
            return df["civilization"].tolist() if not df.empty else []

    def get_available_players(self) -> list[str]:
        """Get list of unique player names.

        Returns:
            List of player names
        """
        query = """
        SELECT DISTINCT player_name
        FROM players
        WHERE player_name IS NOT NULL
        ORDER BY player_name
        """
        with self.db.get_connection() as conn:
            df = conn.execute(query).df()
            return df["player_name"].tolist() if not df.empty else []

    def get_turn_range(self) -> tuple[int, int]:
        """Get the minimum and maximum turn counts across all matches.

        Returns:
            Tuple of (min_turns, max_turns)
        """
        query = """
        SELECT
            MIN(total_turns) as min_turns,
            MAX(total_turns) as max_turns
        FROM matches
        WHERE total_turns IS NOT NULL
        """
        with self.db.get_connection() as conn:
            df = conn.execute(query).df()
            if df.empty or df["min_turns"].iloc[0] is None:
                return (0, 200)
            return (int(df["min_turns"].iloc[0]), int(df["max_turns"].iloc[0]))

    def get_science_win_correlation(
        self,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[List[str]] = None,
        players: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """Get turn-by-turn science progression for winners vs losers.

        Returns one row per turn number with:
        - turn_number: Turn in the game (1-based)
        - avg_science_winners: Average science production for winners at this turn
        - avg_science_losers: Average science production for losers at this turn
        - p25_winners: 25th percentile for winners
        - p75_winners: 75th percentile for winners
        - p25_losers: 25th percentile for losers
        - p75_losers: 75th percentile for losers
        - winner_count: Number of winner data points at this turn
        - loser_count: Number of loser data points at this turn

        All science values are divided by 10 to convert from internal storage format
        to display-ready values (see docs/archive/reports/yield-display-scale-issue.md).

        Args:
            tournament_round: Filter by tournament round number
            bracket: Filter by bracket ('Winners' or 'Losers')
            min_turns: Minimum game length filter
            max_turns: Maximum game length filter
            map_size: Filter by map size
            map_class: Filter by map class
            map_aspect: Filter by map aspect ratio
            nations: Filter by civilizations (list of nation names)
            players: Filter by player names (list)

        Returns:
            DataFrame with turn-by-turn science progression for winners vs losers
        """
        # Build filter conditions
        filters = ["yh.resource_type = 'YIELD_SCIENCE'"]

        if tournament_round is not None and len(tournament_round) > 0:
            rounds_list = ", ".join(str(r) for r in tournament_round)
            filters.append(f"m.tournament_round IN ({rounds_list})")

        if bracket:
            if bracket == "Winners":
                filters.append("m.tournament_round > 0")
            elif bracket == "Losers":
                filters.append("m.tournament_round < 0")

        if min_turns is not None:
            filters.append(f"m.total_turns >= {min_turns}")

        if max_turns is not None:
            filters.append(f"m.total_turns <= {max_turns}")

        if map_size:
            map_size_list = "', '".join(map_size)
            filters.append(f"m.map_size IN ('{map_size_list}')")

        if map_class:
            map_class_list = "', '".join(map_class)
            filters.append(f"m.map_class IN ('{map_class_list}')")

        if map_aspect:
            map_aspect_list = "', '".join(map_aspect)
            filters.append(f"m.map_aspect IN ('{map_aspect_list}')")

        if nations:
            nations_list = "', '".join(nations)
            filters.append(f"p.civilization IN ('{nations_list}')")

        if players:
            players_list = "', '".join(players)
            filters.append(f"tp.display_name IN ('{players_list}')")

        where_clause = " AND ".join(filters)

        query = f"""
        WITH player_outcomes AS (
            SELECT
                yh.match_id,
                yh.player_id,
                yh.turn_number,
                yh.amount / 10.0 as science,
                CASE WHEN mw.winner_player_id = yh.player_id THEN 1 ELSE 0 END as won
            FROM player_yield_history yh
            JOIN matches m ON yh.match_id = m.match_id
            JOIN players p ON yh.match_id = p.match_id AND yh.player_id = p.player_id
            LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
            LEFT JOIN match_winners mw ON yh.match_id = mw.match_id
            WHERE {where_clause}
        )
        SELECT
            turn_number,
            AVG(CASE WHEN won = 1 THEN science END) as avg_science_winners,
            AVG(CASE WHEN won = 0 THEN science END) as avg_science_losers,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY CASE WHEN won = 1 THEN science END) as p25_winners,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY CASE WHEN won = 1 THEN science END) as p75_winners,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY CASE WHEN won = 0 THEN science END) as p25_losers,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY CASE WHEN won = 0 THEN science END) as p75_losers,
            COUNT(CASE WHEN won = 1 THEN 1 END) as winner_count,
            COUNT(CASE WHEN won = 0 THEN 1 END) as loser_count
        FROM player_outcomes
        GROUP BY turn_number
        HAVING winner_count > 0 AND loser_count > 0
        ORDER BY turn_number
        """

        with self.db.get_connection() as conn:
            return conn.execute(query).df()

    def get_match_timeline_events(self, match_id: int) -> pd.DataFrame:
        """Get unified timeline of key game events for a match.

        Combines tech discoveries, law adoptions, wonder construction, city founding,
        ruler successions/deaths, and battle detection into a single timeline.

        Args:
            match_id: ID of the match

        Returns:
            DataFrame with columns:
            - turn: int
            - player_id: int
            - event_type: str (tech, law, law_swap, wonder_start, wonder_complete,
                              city, capital, ruler, death, battle, uu_unlock)
            - title: str (short display text)
            - details: str (hover tooltip)
            - icon: str (emoji)
            - subtype: str | None (tech type, law class, etc.)
        """
        from tournament_visualizer.data.game_constants import (
            EVENT_PRIORITY,
            IGNORED_LAWS,
            LAW_TO_CLASS,
            TECH_TYPES,
            TIMELINE_ICONS,
        )

        query = """
        WITH
        -- 1. Tech events (excluding _BONUS_ variants)
        tech_events AS (
            SELECT
                e.turn_number as turn,
                e.player_id,
                'tech' as event_type,
                -- Title case: first letter uppercase, rest lowercase for each word
                'Discovered: ' || ARRAY_TO_STRING(
                    LIST_TRANSFORM(
                        STRING_SPLIT(REPLACE(REPLACE(json_extract_string(e.event_data, '$.tech'), 'TECH_', ''), '_', ' '), ' '),
                        word -> UPPER(word[1]) || LOWER(word[2:])
                    ),
                    ' '
                ) as title,
                e.description as details,
                json_extract_string(e.event_data, '$.tech') as raw_value
            FROM events e
            WHERE e.match_id = ?
              AND e.event_type = 'TECH_DISCOVERED'
              AND json_extract_string(e.event_data, '$.tech') NOT LIKE '%_BONUS_%'
        ),

        -- 2. Law events (with swap detection)
        law_events_raw AS (
            SELECT
                e.turn_number as turn,
                e.player_id,
                json_extract_string(e.event_data, '$.law') as law,
                e.description as details,
                ROW_NUMBER() OVER (PARTITION BY e.player_id ORDER BY e.turn_number, e.event_id) as law_order
            FROM events e
            WHERE e.match_id = ?
              AND e.event_type = 'LAW_ADOPTED'
        ),

        -- 3. Wonder events (deduplicated, parsed from description)
        -- Player name is in parentheses in description: "Carthage (Marauder) has begun..."
        wonder_events AS (
            SELECT
                e.turn_number as turn,
                -- Assign to the player whose name appears in description
                CASE
                    WHEN e.description LIKE '%(' || p1.player_name || ')%' THEN p1.player_id
                    WHEN e.description LIKE '%(' || p2.player_name || ')%' THEN p2.player_id
                    ELSE e.player_id  -- fallback to original if no match
                END as player_id,
                CASE
                    WHEN e.description LIKE '%has begun construction%'
                      OR e.description LIKE '%begonnen%'
                      OR e.description LIKE '%начинает%'
                    THEN 'wonder_start'
                    ELSE 'wonder_complete'
                END as event_type,
                e.description as details,
                -- Extract wonder name from description
                CASE
                    -- English completed: "The X completed by..."
                    WHEN e.description LIKE '%completed by%'
                    THEN TRIM(REGEXP_EXTRACT(e.description, '^\\s*(.+?) completed', 1))
                    -- English started: "...construction of X." or "...construction of X" (no punctuation)
                    WHEN e.description LIKE '%construction of%'
                    THEN TRIM(RTRIM(REGEXP_EXTRACT(e.description, 'construction of (.+)', 1), '.!'))
                    -- German started: "begonnen: X."
                    WHEN e.description LIKE '%begonnen:%'
                    THEN TRIM(RTRIM(REGEXP_EXTRACT(e.description, 'begonnen: (.+)', 1), '.!'))
                    -- German completed: "X (abgeschlossen|fertiggestellt)"
                    WHEN e.description LIKE '%abgeschlossen%' OR e.description LIKE '%fertiggestellt%'
                    THEN TRIM(REGEXP_EXTRACT(e.description, '^\\s*(.+?) (abgeschlossen|fertiggestellt)', 1))
                    -- Russian: "строительство {wonder}." or "строительство {wonder}!"
                    WHEN e.description LIKE '%строительство%'
                    THEN TRIM(RTRIM(REGEXP_EXTRACT(e.description, 'строительство (.+)', 1), '.!'))
                    ELSE e.description
                END as wonder_name,
                ROW_NUMBER() OVER (
                    PARTITION BY e.turn_number,
                        CASE
                            WHEN e.description LIKE '%has begun construction%'
                              OR e.description LIKE '%начинает строительство%'
                              OR e.description LIKE '%begonnen%'
                            THEN 'start'
                            WHEN e.description LIKE '%completed by%'
                              OR e.description LIKE '%завершает строительство%'
                              OR e.description LIKE '%fertiggestellt%'
                            THEN 'complete'
                            ELSE 'other'
                        END
                    -- Dedupe by turn + event type only (two wonders completing same turn is rare)
                    -- Previous approach using English wonder names failed for non-English saves
                    ORDER BY e.event_id
                ) as rn
            FROM events e
            CROSS JOIN (SELECT player_id, player_name FROM players WHERE match_id = ? LIMIT 1) p1
            CROSS JOIN (SELECT player_id, player_name FROM players WHERE match_id = ? ORDER BY player_id LIMIT 1 OFFSET 1) p2
            WHERE e.match_id = ?
              AND e.event_type = 'WONDER_ACTIVITY'
        ),

        -- 4. City founding events
        -- Join on founded_turn AND city name to avoid cross-product when multiple cities
        -- founded on same turn. City name extracted from event description.
        -- Falls back to family_archetype from event_data for rebel/captured cities
        city_events AS (
            SELECT
                e.turn_number as turn,
                e.player_id,
                CASE WHEN c.is_capital THEN 'capital' ELSE 'city' END as event_type,
                CASE WHEN c.is_capital
                    THEN 'Capital: ' || TRIM(REPLACE(e.description, 'Founded', ''))
                    ELSE TRIM(REPLACE(e.description, 'Founded', ''))
                END as title,
                COALESCE(
                    c.family_name,
                    'ARCHETYPE_' || (e.event_data->>'family_archetype'),
                    ''
                ) as details
            FROM events e
            LEFT JOIN cities c ON e.match_id = c.match_id
                AND e.player_id = c.player_id
                AND e.turn_number = c.founded_turn
                -- Match city name: event has "Founded  Samuha", cities has "CITYNAME_SAMUHA"
                AND UPPER(TRIM(REPLACE(e.description, 'Founded', ''))) =
                    REPLACE(REPLACE(c.city_name, 'CITYNAME_', ''), '_', ' ')
            WHERE e.match_id = ?
              AND e.event_type = 'CITY_FOUNDED'
        ),

        -- 4b. City breach/capture events (deduplicated)
        -- Description format: "CityName breached by Nation (PlayerName)"
        -- The player in parentheses is the ATTACKER, so the OTHER player lost
        city_breach_events AS (
            SELECT
                e.turn_number as turn,
                -- Identify attacker from "(player_name)" in description, assign loss to other player
                CASE
                    WHEN e.description LIKE '%(' || p1.player_name || ')%' THEN p2.player_id
                    WHEN e.description LIKE '%(' || p2.player_name || ')%' THEN p1.player_id
                    ELSE NULL
                END as player_id,
                'city_lost' as event_type,
                'Lost ' || TRIM(REGEXP_EXTRACT(e.description, '^\\s*(.+?) (breached|captured)', 1)) as title,
                e.description as details,
                ROW_NUMBER() OVER (
                    PARTITION BY e.turn_number,
                        REGEXP_EXTRACT(e.description, '^\\s*(.+?) (breached|captured)', 1)
                    ORDER BY e.event_id
                ) as rn
            FROM events e
            CROSS JOIN (SELECT player_id, player_name FROM players WHERE match_id = ? LIMIT 1) p1
            CROSS JOIN (SELECT player_id, player_name FROM players WHERE match_id = ? ORDER BY player_id LIMIT 1 OFFSET 1) p2
            WHERE e.match_id = ?
              AND e.event_type = 'CITY_BREACHED'
        ),

        -- 5. Ruler succession events
        ruler_events AS (
            SELECT
                r.succession_turn as turn,
                r.player_id,
                'ruler' as event_type,
                CASE WHEN r.succession_order = 0
                    THEN 'Starting Ruler: ' || COALESCE(r.ruler_name, 'Unknown')
                    ELSE 'Crowned ' || COALESCE(r.ruler_name, 'Unknown')
                END as title,
                COALESCE(r.archetype, 'Unknown') || COALESCE(' - ' || r.starting_trait, '') as details,
                r.succession_order
            FROM rulers r
            WHERE r.match_id = ?
        ),

        -- 6. Ruler death events (inferred from next succession - same turn as crowning)
        death_events AS (
            SELECT
                r2.succession_turn as turn,
                r1.player_id,
                'death' as event_type,
                COALESCE(r1.ruler_name, 'Ruler') || ' Died' as title,
                'Ruler died' as details,
                r1.succession_order
            FROM rulers r1
            JOIN rulers r2 ON r1.match_id = r2.match_id
                AND r1.player_id = r2.player_id
                AND r2.succession_order = r1.succession_order + 1
            WHERE r1.match_id = ?
        ),

        -- 7. Battle detection (20%+ military power drop)
        military_with_change AS (
            SELECT
                m.turn_number,
                m.player_id,
                m.military_power,
                LAG(m.military_power) OVER (
                    PARTITION BY m.player_id ORDER BY m.turn_number
                ) as prev_power
            FROM player_military_history m
            WHERE m.match_id = ?
        ),
        battle_events AS (
            SELECT
                turn_number as turn,
                player_id,
                'battle' as event_type,
                'Lost Battle (-' || ROUND(100.0 * (prev_power - military_power) / NULLIF(prev_power, 0), 0) || '%)' as title,
                'Lost ' || ROUND(100.0 * (prev_power - military_power) / NULLIF(prev_power, 0), 0) || '% military power' as details
            FROM military_with_change
            WHERE prev_power > 0
              AND (prev_power - military_power) * 1.0 / prev_power >= 0.20
        ),

        -- 8. Ambition completion events (GOAL_FINISHED)
        ambition_events AS (
            SELECT
                e.turn_number as turn,
                e.player_id,
                'ambition' as event_type,
                -- Extract ambition name from "Completed link(CONCEPT_AMBITION,1): Control Six Mines"
                'Ambition: ' || COALESCE(
                    REGEXP_EXTRACT(e.description, ': (.+)$', 1),
                    e.description
                ) as title,
                e.description as details
            FROM events e
            WHERE e.match_id = ?
              AND e.event_type = 'GOAL_FINISHED'
        ),

        -- 9. Religion founding events (RELIGION_FOUNDED)
        -- Deduplicate: both players get notified, but only one actually founded it.
        -- Priority: 1) player owns the city where religion was founded, 2) lowest player_id
        religion_events_raw AS (
            SELECT
                e.turn_number as turn,
                e.player_id,
                'religion' as event_type,
                -- Extract religion name: "Carthaginian Paganism founded in  Carthago"
                'Founded: ' || COALESCE(
                    TRIM(REGEXP_EXTRACT(e.description, '^(.+?) founded', 1)),
                    e.description
                ) as title,
                e.description as details,
                -- Check if player owns the city where religion was founded (definitive signal)
                CASE WHEN c.player_id = e.player_id THEN 1 ELSE 0 END as owns_city,
                ROW_NUMBER() OVER (
                    PARTITION BY e.turn_number, REGEXP_EXTRACT(e.description, '^(.+?) founded', 1)
                    ORDER BY
                        -- Player who owns the city is the founder
                        CASE WHEN c.player_id = e.player_id THEN 0 ELSE 1 END,
                        e.player_id  -- fallback to lowest player_id
                ) as rn
            FROM events e
            JOIN players p ON e.player_id = p.player_id AND e.match_id = p.match_id
            -- Join to cities table: extract city name from "founded in  CityName"
            LEFT JOIN cities c
                ON c.match_id = e.match_id
                AND c.city_name = 'CITYNAME_' || UPPER(TRIM(REGEXP_EXTRACT(e.description, 'founded in\\s+(.+)$', 1)))
            WHERE e.match_id = ?
              AND e.event_type = 'RELIGION_FOUNDED'
        ),
        religion_events AS (
            SELECT turn, player_id, event_type, title, details
            FROM religion_events_raw
            WHERE rn = 1
        ),

        -- 10. Theology established events (THEOLOGY_ESTABLISHED)
        -- Only show for the player who actually established it (player name in description)
        theology_events AS (
            SELECT
                e.turn_number as turn,
                e.player_id,
                'theology' as event_type,
                -- Extract theology and religion: "Zoroastrian Legalism" -> "Legalism (Zoroastrianism)"
                COALESCE(
                    REGEXP_EXTRACT(e.description, '^[A-Za-z]+ ([A-Za-z]+) established', 1),
                    'Theology'
                ) || ' (' ||
                CASE REGEXP_EXTRACT(e.description, '^([A-Za-z]+) ', 1)
                    WHEN 'Zoroastrian' THEN 'Zoroastrianism'
                    WHEN 'Jewish' THEN 'Judaism'
                    WHEN 'Christian' THEN 'Christianity'
                    WHEN 'Manichaean' THEN 'Manichaeism'
                    ELSE REGEXP_EXTRACT(e.description, '^([A-Za-z]+) ', 1)
                END || ')' as title,
                e.description as details
            FROM events e
            JOIN players p ON e.match_id = p.match_id AND e.player_id = p.player_id
            WHERE e.match_id = ?
              AND e.event_type = 'THEOLOGY_ESTABLISHED'
              AND e.description LIKE '%(' || p.player_name || ')%'
        ),

        -- 11. Religion adoption events (RELIGION_ADOPTED)
        -- Shows when a player adopted a world religion as their state religion
        religion_adopted_events AS (
            SELECT
                e.turn_number as turn,
                e.player_id,
                'religion_adopted' as event_type,
                e.description as title,  -- "Adopted Zoroastrianism"
                e.description as details
            FROM events e
            WHERE e.match_id = ?
              AND e.event_type = 'RELIGION_ADOPTED'
        )

        -- Combine all events
        SELECT * FROM (
            SELECT turn, player_id, event_type, title, details, raw_value as subtype, NULL as succession_order
            FROM tech_events

            UNION ALL

            SELECT turn, player_id,
                   'law' as event_type,
                   -- Title case for law names with "Adopted:" prefix
                   'Adopted: ' || ARRAY_TO_STRING(
                       LIST_TRANSFORM(
                           STRING_SPLIT(REPLACE(REPLACE(law, 'LAW_', ''), '_', ' '), ' '),
                           word -> UPPER(word[1]) || LOWER(word[2:])
                       ),
                       ' '
                   ) as title,
                   details,
                   law as subtype,
                   NULL as succession_order
            FROM law_events_raw

            UNION ALL

            SELECT turn, player_id, event_type,
                   CASE
                       WHEN event_type = 'wonder_start' THEN 'Started: ' || wonder_name
                       ELSE 'Completed: ' || wonder_name
                   END as title,
                   details, NULL as subtype, NULL as succession_order
            FROM wonder_events
            WHERE rn = 1

            UNION ALL

            SELECT turn, player_id, event_type, title, details, NULL as subtype, NULL as succession_order
            FROM city_events

            UNION ALL

            SELECT turn, player_id, event_type, title, details, NULL as subtype, NULL as succession_order
            FROM city_breach_events
            WHERE rn = 1

            UNION ALL

            SELECT turn, player_id, event_type, title, details, NULL as subtype, succession_order
            FROM ruler_events

            UNION ALL

            SELECT turn, player_id, event_type, title, details, NULL as subtype, succession_order
            FROM death_events

            UNION ALL

            SELECT turn, player_id, event_type, title, details, NULL as subtype, NULL as succession_order
            FROM battle_events

            UNION ALL

            SELECT turn, player_id, event_type, title, details, NULL as subtype, NULL as succession_order
            FROM ambition_events

            UNION ALL

            SELECT turn, player_id, event_type, title, details, NULL as subtype, NULL as succession_order
            FROM religion_events

            UNION ALL

            SELECT turn, player_id, event_type, title, details, NULL as subtype, NULL as succession_order
            FROM theology_events

            UNION ALL

            SELECT turn, player_id, event_type, title, details, NULL as subtype, NULL as succession_order
            FROM religion_adopted_events
        ) all_events
        ORDER BY turn, player_id, succession_order NULLS LAST
        """

        params = [
            match_id
        ] * 16  # 16 placeholders: tech, law, wonder(x3), city, breach(x3), ruler, death, military, ambition, religion, theology, religion_adopted

        with self.db.get_connection() as conn:
            df = conn.execute(query, params).df()

        if df.empty:
            # Return empty DataFrame with correct schema
            return pd.DataFrame(
                columns=[
                    "turn",
                    "player_id",
                    "event_type",
                    "title",
                    "details",
                    "icon",
                    "subtype",
                ]
            )

        # Post-process: add icons and tech types
        df["icon"] = df["event_type"].map(TIMELINE_ICONS).fillna("")

        # Add tech type classification
        def get_subtype(row: pd.Series) -> str | None:
            if row["event_type"] == "tech" and row["subtype"]:
                return TECH_TYPES.get(row["subtype"])
            if row["event_type"] in ("law", "law_swap") and row["subtype"]:
                # Filter out ignored laws
                if row["subtype"] in IGNORED_LAWS:
                    return None
                return LAW_TO_CLASS.get(row["subtype"])
            return row["subtype"]

        df["subtype"] = df.apply(get_subtype, axis=1)

        # Filter out ignored laws (titles are now "Adopted: X" format)
        ignored_law_names = [
            l.replace("LAW_", "").replace("_", " ").title() for l in IGNORED_LAWS
        ]
        df = df[
            ~(
                (df["event_type"] == "law")
                & (df["subtype"].isna())
                & (
                    df["title"]
                    .str.replace("Adopted: ", "", regex=False)
                    .isin(ignored_law_names)
                )
            )
        ]

        # Detect law swaps (same class adopted twice by same player)
        law_history: dict[tuple[int, str], str] = (
            {}
        )  # (player_id, class) -> previous law title
        swap_indices = []

        for idx, row in df[df["event_type"] == "law"].iterrows():
            player_id = row["player_id"]
            law_class = row["subtype"]
            if law_class and pd.notna(law_class):
                key = (player_id, law_class)
                if key in law_history:
                    # This is a swap - extract law names from "Adopted: X" format
                    prev_title = law_history[key]
                    prev_law_name = prev_title.replace("Adopted: ", "")
                    current_law_name = row["title"].replace("Adopted: ", "")
                    # Update title to show swap
                    df.at[idx, "title"] = (
                        f"Swapped {prev_law_name} → {current_law_name}"
                    )
                    df.at[idx, "event_type"] = "law_swap"
                    df.at[idx, "icon"] = TIMELINE_ICONS.get("law_swap", "⚖️")
                # Track this law's title
                law_history[key] = row["title"]

        # Add UU unlock detection (4th and 7th law for each player)
        # Only count new law categories, not law swaps (swaps don't unlock UUs)
        law_counts: dict[int, int] = {}
        uu_events = []

        for idx, row in df[df["event_type"] == "law"].iterrows():
            player_id = row["player_id"]
            if pd.isna(player_id):
                continue
            player_id = int(player_id)
            law_counts[player_id] = law_counts.get(player_id, 0) + 1
            count = law_counts[player_id]

            if count == 4:
                uu_events.append(
                    {
                        "turn": row["turn"],
                        "player_id": player_id,
                        "event_type": "uu_unlock",
                        "title": "6 Strength UU",
                        "details": "Unlocked 6 strength unique unit (4th law)",
                        "icon": TIMELINE_ICONS.get("uu_unlock", "🗡️"),
                        "subtype": None,
                    }
                )
            elif count == 7:
                uu_events.append(
                    {
                        "turn": row["turn"],
                        "player_id": player_id,
                        "event_type": "uu_unlock",
                        "title": "8 Strength UU",
                        "details": "Unlocked 8 strength unique unit (7th law)",
                        "icon": TIMELINE_ICONS.get("uu_unlock", "🗡️"),
                        "subtype": None,
                    }
                )

        if uu_events:
            uu_df = pd.DataFrame(uu_events)
            df = pd.concat([df, uu_df], ignore_index=True)

        # Sort by turn, then by event priority
        df["_priority"] = df["event_type"].map(EVENT_PRIORITY).fillna(99)
        df = df.sort_values(["turn", "player_id", "_priority"]).drop(
            columns=["_priority"]
        )

        # Add player names
        player_query = """
        SELECT player_id, player_name
        FROM players
        WHERE match_id = ?
        """
        with self.db.get_connection() as conn:
            players_df = conn.execute(player_query, [match_id]).df()

        if not players_df.empty:
            df = df.merge(players_df, on="player_id", how="left")
        else:
            df["player_name"] = None

        return df.reset_index(drop=True)

    def get_match_turn_comparisons(
        self,
        match_id: int,
        player1_id: int,
        player2_id: int,
    ) -> pd.DataFrame:
        """Get per-turn comparison metrics for game state analysis.

        Returns military power, orders, science, and victory points for both players
        at each turn, with interpolation to fill missing values (carry forward last
        known value).

        Args:
            match_id: ID of the match
            player1_id: Database player ID for player 1 (left column)
            player2_id: Database player ID for player 2 (right column)

        Returns:
            DataFrame with columns:
            - turn_number: int
            - p1_military, p2_military: Military power values
            - p1_orders, p2_orders: Orders per turn (display-ready, divided by 10)
            - p1_science, p2_science: Cumulative science (total accumulated)
            - p1_vp, p2_vp: Victory points
            - mil_ratio, orders_ratio, science_ratio, vp_ratio: P1/P2 ratios
        """
        query = """
        WITH
        -- Get all turns from ALL data sources (each may have different turn coverage)
        all_turns AS (
            SELECT DISTINCT turn_number FROM player_military_history WHERE match_id = ?
            UNION
            SELECT DISTINCT turn_number FROM player_yield_history WHERE match_id = ?
            UNION
            SELECT DISTINCT turn_number FROM player_points_history WHERE match_id = ?
        ),

        -- Military power per player per turn
        military AS (
            SELECT turn_number, player_id, military_power
            FROM player_military_history
            WHERE match_id = ?
        ),

        -- Orders per player per turn
        orders AS (
            SELECT turn_number, player_id, amount / 10.0 as orders
            FROM player_yield_history
            WHERE match_id = ? AND resource_type = 'YIELD_ORDERS'
        ),

        -- Cumulative science per player per turn (total accumulated, not rate)
        science AS (
            SELECT turn_number, player_id,
                   SUM(amount / 10.0) OVER (
                       PARTITION BY player_id ORDER BY turn_number
                   ) as science
            FROM player_yield_history
            WHERE match_id = ? AND resource_type = 'YIELD_SCIENCE'
        ),

        -- Victory points per player per turn
        points AS (
            SELECT turn_number, player_id, points as vp
            FROM player_points_history
            WHERE match_id = ?
        ),

        -- Pivot to get p1 and p2 columns, then interpolate
        combined AS (
            SELECT
                t.turn_number,
                -- Player 1 metrics
                m1.military_power as p1_military_raw,
                o1.orders as p1_orders_raw,
                s1.science as p1_science_raw,
                vp1.vp as p1_vp_raw,
                -- Player 2 metrics
                m2.military_power as p2_military_raw,
                o2.orders as p2_orders_raw,
                s2.science as p2_science_raw,
                vp2.vp as p2_vp_raw
            FROM all_turns t
            LEFT JOIN military m1 ON t.turn_number = m1.turn_number AND m1.player_id = ?
            LEFT JOIN military m2 ON t.turn_number = m2.turn_number AND m2.player_id = ?
            LEFT JOIN orders o1 ON t.turn_number = o1.turn_number AND o1.player_id = ?
            LEFT JOIN orders o2 ON t.turn_number = o2.turn_number AND o2.player_id = ?
            LEFT JOIN science s1 ON t.turn_number = s1.turn_number AND s1.player_id = ?
            LEFT JOIN science s2 ON t.turn_number = s2.turn_number AND s2.player_id = ?
            LEFT JOIN points vp1 ON t.turn_number = vp1.turn_number AND vp1.player_id = ?
            LEFT JOIN points vp2 ON t.turn_number = vp2.turn_number AND vp2.player_id = ?
        ),

        -- Forward-fill missing values using last known value
        interpolated AS (
            SELECT
                turn_number,
                -- Use LAST_VALUE with IGNORE NULLS to carry forward
                LAST_VALUE(p1_military_raw IGNORE NULLS) OVER (
                    ORDER BY turn_number ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) as p1_military,
                LAST_VALUE(p2_military_raw IGNORE NULLS) OVER (
                    ORDER BY turn_number ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) as p2_military,
                LAST_VALUE(p1_orders_raw IGNORE NULLS) OVER (
                    ORDER BY turn_number ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) as p1_orders,
                LAST_VALUE(p2_orders_raw IGNORE NULLS) OVER (
                    ORDER BY turn_number ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) as p2_orders,
                LAST_VALUE(p1_science_raw IGNORE NULLS) OVER (
                    ORDER BY turn_number ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) as p1_science,
                LAST_VALUE(p2_science_raw IGNORE NULLS) OVER (
                    ORDER BY turn_number ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) as p2_science,
                LAST_VALUE(p1_vp_raw IGNORE NULLS) OVER (
                    ORDER BY turn_number ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) as p1_vp,
                LAST_VALUE(p2_vp_raw IGNORE NULLS) OVER (
                    ORDER BY turn_number ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) as p2_vp
            FROM combined
        )

        SELECT
            turn_number,
            COALESCE(p1_military, 0) as p1_military,
            COALESCE(p2_military, 0) as p2_military,
            COALESCE(p1_orders, 0) as p1_orders,
            COALESCE(p2_orders, 0) as p2_orders,
            COALESCE(p1_science, 0) as p1_science,
            COALESCE(p2_science, 0) as p2_science,
            COALESCE(p1_vp, 0) as p1_vp,
            COALESCE(p2_vp, 0) as p2_vp,
            -- Compute ratios (avoid division by zero)
            CASE
                WHEN COALESCE(p2_military, 0) = 0 THEN NULL
                ELSE COALESCE(p1_military, 0) / p2_military
            END as mil_ratio,
            CASE
                WHEN COALESCE(p2_orders, 0) = 0 THEN NULL
                ELSE COALESCE(p1_orders, 0) / p2_orders
            END as orders_ratio,
            CASE
                WHEN COALESCE(p2_science, 0) = 0 THEN NULL
                ELSE COALESCE(p1_science, 0) / p2_science
            END as science_ratio,
            CASE
                WHEN COALESCE(p2_vp, 0) = 0 THEN NULL
                ELSE COALESCE(p1_vp, 0) * 1.0 / p2_vp
            END as vp_ratio
        FROM interpolated
        ORDER BY turn_number
        """

        # Parameters: match_id (7x for all_turns union + 4 CTEs),
        # then player IDs for joins (8x alternating p1, p2)
        params = [
            match_id,  # all_turns - military
            match_id,  # all_turns - yield
            match_id,  # all_turns - points
            match_id,  # military CTE
            match_id,  # orders CTE
            match_id,  # science CTE
            match_id,  # points CTE
            player1_id,  # m1 join
            player2_id,  # m2 join
            player1_id,  # o1 join
            player2_id,  # o2 join
            player1_id,  # s1 join
            player2_id,  # s2 join
            player1_id,  # vp1 join
            player2_id,  # vp2 join
        ]

        with self.db.get_connection() as conn:
            return conn.execute(query, params).df()

    def get_ruler_legitimacy_breakdown(self, match_id: int) -> pd.DataFrame:
        """Get rulers with cognomens for legitimacy breakdown calculation.

        Returns all rulers for each player in the match, ordered by succession
        order (most recent first). The caller should calculate decay based on
        generations_ago (0 = current ruler, 1 = previous, etc.).

        Args:
            match_id: Match ID to query

        Returns:
            DataFrame with columns:
                - player_id: Player ID
                - player_name: Player name
                - ruler_name: Name of the ruler
                - cognomen: Cognomen type (e.g., "Lion", "Great")
                - succession_order: Order of succession (0 = first ruler)
                - succession_turn: Turn when this ruler took power
                - max_succession: Highest succession_order for this player
                - generations_ago: How many rulers ago (0 = current)
        """
        query = """
        WITH max_succession AS (
            SELECT player_id, MAX(succession_order) as max_order
            FROM rulers
            WHERE match_id = ?
            GROUP BY player_id
        )
        SELECT
            r.player_id,
            p.player_name,
            r.ruler_name,
            r.cognomen,
            r.succession_order,
            r.succession_turn,
            ms.max_order as max_succession,
            ms.max_order - r.succession_order as generations_ago
        FROM rulers r
        JOIN players p ON r.player_id = p.player_id AND r.match_id = p.match_id
        JOIN max_succession ms ON r.player_id = ms.player_id
        WHERE r.match_id = ?
        ORDER BY r.player_id, r.succession_order DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id, match_id]).df()

    def get_ambitions_completed_by_match(self, match_id: int) -> pd.DataFrame:
        """Get count of completed ambitions (goals) for each player in a match.

        Counts GOAL_FINISHED events which track completed ambitions.

        Args:
            match_id: Match ID to query

        Returns:
            DataFrame with columns:
                - player_id: Player ID
                - player_name: Player name
                - ambitions_completed: Number of GOAL_FINISHED events
        """
        query = """
        SELECT
            p.player_id,
            p.player_name,
            COUNT(e.event_id) as ambitions_completed
        FROM players p
        LEFT JOIN events e ON p.player_id = e.player_id
            AND p.match_id = e.match_id
            AND e.event_type = 'GOAL_FINISHED'
        WHERE p.match_id = ?
        GROUP BY p.player_id, p.player_name
        ORDER BY p.player_id
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id]).df()

    def get_legitimacy_events_by_match(self, match_id: int) -> pd.DataFrame:
        """Get legitimacy-related events with turn numbers for ruler attribution.

        Returns memory events that typically affect legitimacy, with turn numbers
        so they can be attributed to specific rulers.

        Args:
            match_id: Match ID to query

        Returns:
            DataFrame with columns:
                - player_id: Player ID
                - event_type: Event type (e.g., MEMORYFAMILY_FOUNDED_FAMILY_SEAT)
                - turn_number: Turn when event occurred
                - count: Number of times this event occurred on this turn
        """
        query = """
        SELECT
            e.player_id,
            e.event_type,
            e.turn_number,
            COUNT(*) as count
        FROM events e
        WHERE e.match_id = ?
        AND e.event_type LIKE 'MEMORY%'
        GROUP BY e.player_id, e.event_type, e.turn_number
        ORDER BY e.player_id, e.turn_number, count DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id]).df()

    def get_family_opinions_by_match(self, match_id: int) -> pd.DataFrame:
        """Get final family opinion totals for each player in a match.

        Returns the sum of all family opinions at the last recorded turn.

        Args:
            match_id: Match ID to query

        Returns:
            DataFrame with columns:
                - player_id: Player ID
                - player_name: Player name
                - total_family_opinion: Sum of all family opinions
        """
        query = """
        WITH max_turns AS (
            SELECT player_id, MAX(turn_number) as max_turn
            FROM family_opinion_history
            WHERE match_id = ?
            GROUP BY player_id
        )
        SELECT
            p.player_id,
            p.player_name,
            COALESCE(SUM(foh.opinion), 0) as total_family_opinion
        FROM players p
        LEFT JOIN max_turns mt ON p.player_id = mt.player_id
        LEFT JOIN family_opinion_history foh ON p.player_id = foh.player_id
            AND p.match_id = foh.match_id
            AND foh.turn_number = mt.max_turn
        WHERE p.match_id = ?
        GROUP BY p.player_id, p.player_name
        ORDER BY p.player_id
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id, match_id]).df()

    def get_legacies_completed_by_match(self, match_id: int) -> pd.DataFrame:
        """Get count of completed legacies for each player in a match.

        Counts legacy-related memory events.

        Args:
            match_id: Match ID to query

        Returns:
            DataFrame with columns:
                - player_id: Player ID
                - player_name: Player name
                - legacies_completed: Number of legacy events
        """
        query = """
        SELECT
            p.player_id,
            p.player_name,
            COUNT(e.event_id) as legacies_completed
        FROM players p
        LEFT JOIN events e ON p.player_id = e.player_id
            AND p.match_id = e.match_id
            AND e.event_type IN ('MEMORYFAMILY_OUR_LEGACY', 'MEMORYRELIGION_OUR_LEGACY')
        WHERE p.match_id = ?
        GROUP BY p.player_id, p.player_name
        ORDER BY p.player_id
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id]).df()

    # =========================================================================
    # Family Class Analytics (Tournament-wide)
    # =========================================================================

    def get_family_class_win_stats(
        self,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> pd.DataFrame:
        """Get family class win statistics across matches.

        Family classes are derived from city family assignments. A player "uses"
        a family class if they have at least one city belonging to that class.

        Args:
            tournament_round: Specific round numbers to filter
            bracket: Bracket filter
            min_turns: Minimum turns
            max_turns: Maximum turns
            map_size: Map size filter
            map_class: Map class filter
            map_aspect: Map aspect ratio filter
            nations: List of civilizations to filter
            players: List of player names to filter
            result_filter: Filter by match result (winners/losers/all)

        Returns:
            DataFrame with columns: family_class, wins, total_picks, win_percentage
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=result_filter,
        )

        if not filtered:
            return pd.DataFrame()

        where_clause, params = self._build_player_filter(filtered, result_filter)

        # Query family usage per player-match, then transform to class in Python
        query = f"""
        SELECT DISTINCT
            p.player_id,
            p.match_id,
            c.family_name,
            CASE WHEN mw.winner_player_id = p.player_id THEN 1 ELSE 0 END as is_winner
        FROM players p
        JOIN cities c ON p.match_id = c.match_id AND p.player_id = c.player_id
        LEFT JOIN match_winners mw ON p.match_id = mw.match_id
        WHERE {where_clause}
            AND c.family_name IS NOT NULL
        """

        with self.db.get_connection() as conn:
            df = conn.execute(query, params).df()

        if df.empty:
            return pd.DataFrame()

        # Transform family_name to family_class
        df["family_class"] = df["family_name"].apply(get_family_class)
        df = df[df["family_class"] != "Unknown"]

        # Aggregate by family class
        result = (
            df.groupby("family_class")
            .agg(
                wins=("is_winner", "sum"),
                total_picks=("is_winner", "count"),
            )
            .reset_index()
        )
        result["win_percentage"] = (
            result["wins"] * 100.0 / result["total_picks"]
        ).round(2)

        return result.sort_values("wins", ascending=False)

    def get_family_class_popularity(
        self,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> pd.DataFrame:
        """Get family class popularity (how often each class is picked).

        Args:
            tournament_round: Specific round numbers to filter
            bracket: Bracket filter
            min_turns: Minimum turns
            max_turns: Maximum turns
            map_size: Map size filter
            map_class: Map class filter
            map_aspect: Map aspect ratio filter
            nations: List of civilizations to filter
            players: List of player names to filter
            result_filter: Filter by match result (winners/losers/all)

        Returns:
            DataFrame with columns: family_class, pick_count, pick_percentage
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=result_filter,
        )

        if not filtered:
            return pd.DataFrame()

        where_clause, params = self._build_player_filter(filtered, result_filter)

        # Get distinct family per player-match
        query = f"""
        SELECT DISTINCT
            p.player_id,
            p.match_id,
            c.family_name
        FROM players p
        JOIN cities c ON p.match_id = c.match_id AND p.player_id = c.player_id
        WHERE {where_clause}
            AND c.family_name IS NOT NULL
        """

        with self.db.get_connection() as conn:
            df = conn.execute(query, params).df()

        if df.empty:
            return pd.DataFrame()

        # Transform to family class
        df["family_class"] = df["family_name"].apply(get_family_class)
        df = df[df["family_class"] != "Unknown"]

        # Count picks per class
        result = df.groupby("family_class").size().reset_index(name="pick_count")
        total_picks = result["pick_count"].sum()
        result["pick_percentage"] = (result["pick_count"] * 100.0 / total_picks).round(
            2
        )

        return result.sort_values("pick_count", ascending=False)

    def get_family_class_counter_pick_matrix(
        self,
        min_games: int = 1,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
    ) -> pd.DataFrame:
        """Get family class counter-pick effectiveness matrix.

        Calculates win rate when one player's classes face opponent's classes.

        Args:
            min_games: Minimum games for a matchup to be included
            tournament_round: Specific round numbers to filter
            bracket: Bracket filter
            min_turns: Minimum turns
            max_turns: Maximum turns
            map_size: Map size filter
            map_class: Map class filter
            map_aspect: Map aspect ratio filter
            nations: List of civilizations to filter
            players: List of player names to filter

        Returns:
            DataFrame with columns: player_class, opponent_class, games,
                player_wins, win_rate
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=None,
        )

        if not filtered:
            return pd.DataFrame()

        match_ids = (
            filtered
            if not isinstance(filtered[0], tuple)
            else list(set(m for m, _ in filtered))
        )

        # Get all player family assignments with winner info
        query = """
        SELECT DISTINCT
            p.player_id,
            p.match_id,
            c.family_name,
            CASE WHEN mw.winner_player_id = p.player_id THEN 1 ELSE 0 END as is_winner
        FROM players p
        JOIN cities c ON p.match_id = c.match_id AND p.player_id = c.player_id
        LEFT JOIN match_winners mw ON p.match_id = mw.match_id
        WHERE p.match_id = ANY($match_ids)
            AND c.family_name IS NOT NULL
        """

        with self.db.get_connection() as conn:
            df = conn.execute(query, {"match_ids": match_ids}).df()

        if df.empty:
            return pd.DataFrame()

        # Transform to family class
        df["family_class"] = df["family_name"].apply(get_family_class)
        df = df[df["family_class"] != "Unknown"]

        # Build matchup matrix
        # For each match, get unique classes per player, then cross-join
        matchups = []
        for match_id in df["match_id"].unique():
            match_df = df[df["match_id"] == match_id]
            players_in_match = match_df["player_id"].unique()
            if len(players_in_match) != 2:
                continue

            p1, p2 = players_in_match
            p1_classes = match_df[match_df["player_id"] == p1]["family_class"].unique()
            p2_classes = match_df[match_df["player_id"] == p2]["family_class"].unique()
            p1_won = match_df[match_df["player_id"] == p1]["is_winner"].iloc[0]

            for c1 in p1_classes:
                for c2 in p2_classes:
                    matchups.append(
                        {
                            "player_class": c1,
                            "opponent_class": c2,
                            "player_won": p1_won,
                        }
                    )
                    # Also add reverse perspective
                    matchups.append(
                        {
                            "player_class": c2,
                            "opponent_class": c1,
                            "player_won": 1 - p1_won,
                        }
                    )

        if not matchups:
            return pd.DataFrame()

        matchup_df = pd.DataFrame(matchups)
        result = (
            matchup_df.groupby(["player_class", "opponent_class"])
            .agg(
                games=("player_won", "count"),
                player_wins=("player_won", "sum"),
            )
            .reset_index()
        )
        result["win_rate"] = (result["player_wins"] * 100.0 / result["games"]).round(2)

        # Filter by min_games
        result = result[result["games"] >= min_games]

        return result.sort_values(["player_class", "opponent_class"])

    def get_family_class_omission_stats(
        self,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> pd.DataFrame:
        """Get statistics on which family class players omit (don't pick).

        Players pick 3 of 4 available family classes. This analyzes which class
        is left out most often and how it correlates with winning.

        Args:
            tournament_round: Specific round numbers to filter
            bracket: Bracket filter
            min_turns: Minimum turns
            max_turns: Maximum turns
            map_size: Map size filter
            map_class: Map class filter
            map_aspect: Map aspect ratio filter
            nations: List of civilizations to filter
            players: List of player names to filter
            result_filter: Filter by match result (winners/losers/all)

        Returns:
            DataFrame with columns: omitted_class, omission_count,
                omission_percentage, win_rate_when_omitted
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=result_filter,
        )

        if not filtered:
            return pd.DataFrame()

        where_clause, params = self._build_player_filter(filtered, result_filter)

        # Get player families with civilization and win info
        query = f"""
        SELECT DISTINCT
            p.player_id,
            p.match_id,
            p.civilization,
            c.family_name,
            CASE WHEN mw.winner_player_id = p.player_id THEN 1 ELSE 0 END as is_winner
        FROM players p
        JOIN cities c ON p.match_id = c.match_id AND p.player_id = c.player_id
        LEFT JOIN match_winners mw ON p.match_id = mw.match_id
        WHERE {where_clause}
            AND c.family_name IS NOT NULL
        """

        with self.db.get_connection() as conn:
            df = conn.execute(query, params).df()

        if df.empty:
            return pd.DataFrame()

        # Transform to family class
        df["family_class"] = df["family_name"].apply(get_family_class)
        df = df[df["family_class"] != "Unknown"]

        # Get all classes available per civilization
        civ_classes: Dict[str, set] = {}
        for family_name, family_class in FAMILY_CLASS_MAP.items():
            # Extract civilization from family name pattern
            civ = self._get_civ_from_family(family_name)
            if civ:
                civ_classes.setdefault(civ, set()).add(family_class)

        # Find omitted class per player-match
        omissions = []
        for (match_id, player_id), group in df.groupby(["match_id", "player_id"]):
            civ = group["civilization"].iloc[0]
            is_winner = group["is_winner"].iloc[0]
            picked_classes = set(group["family_class"].unique())

            available = civ_classes.get(civ, set())
            omitted = available - picked_classes

            for omitted_class in omitted:
                omissions.append(
                    {
                        "omitted_class": omitted_class,
                        "is_winner": is_winner,
                    }
                )

        if not omissions:
            return pd.DataFrame()

        omission_df = pd.DataFrame(omissions)
        result = (
            omission_df.groupby("omitted_class")
            .agg(
                omission_count=("is_winner", "count"),
                wins_when_omitted=("is_winner", "sum"),
            )
            .reset_index()
        )

        total_omissions = result["omission_count"].sum()
        result["omission_percentage"] = (
            result["omission_count"] * 100.0 / total_omissions
        ).round(2)
        result["win_rate_when_omitted"] = (
            result["wins_when_omitted"] * 100.0 / result["omission_count"]
        ).round(2)

        return result.sort_values("omission_count", ascending=False)

    def _get_civ_from_family(self, family_name: str) -> Optional[str]:
        """Get civilization name from family name.

        Based on the FAMILY_CLASS_MAP structure in config.py.
        """
        # Map family prefixes to civilizations
        family_civ_map = {
            "FAMILY_SARGONID": "Assyria",
            "FAMILY_TUDIYA": "Assyria",
            "FAMILY_ADASI": "Assyria",
            "FAMILY_ERISHUM": "Assyria",
            "FAMILY_KASSITE": "Babylonia",
            "FAMILY_CHALDEAN": "Babylonia",
            "FAMILY_ISIN": "Babylonia",
            "FAMILY_AMORITE": "Babylonia",
            "FAMILY_BARCID": "Carthage",
            "FAMILY_MAGONID": "Carthage",
            "FAMILY_HANNONID": "Carthage",
            "FAMILY_DIDONIAN": "Carthage",
            "FAMILY_RAMESSIDE": "Egypt",
            "FAMILY_SAITE": "Egypt",
            "FAMILY_AMARNA": "Egypt",
            "FAMILY_THUTMOSID": "Egypt",
            "FAMILY_ARGEAD": "Greece",
            "FAMILY_CYPSELID": "Greece",
            "FAMILY_SELEUCID": "Greece",
            "FAMILY_ALCMAEONID": "Greece",
            "FAMILY_SASANID": "Persia",
            "FAMILY_MIHRANID": "Persia",
            "FAMILY_ARSACID": "Persia",
            "FAMILY_ACHAEMENID": "Persia",
            "FAMILY_FABIUS": "Rome",
            "FAMILY_CLAUDIUS": "Rome",
            "FAMILY_VALERIUS": "Rome",
            "FAMILY_JULIUS": "Rome",
            "FAMILY_KUSSARAN": "Hatti",
            "FAMILY_NENASSAN": "Hatti",
            "FAMILY_ZALPUWAN": "Hatti",
            "FAMILY_HATTUSAN": "Hatti",
            "FAMILY_YAM": "Nubia",
            "FAMILY_IRTJET": "Nubia",
            "FAMILY_WAWAT": "Nubia",
            "FAMILY_SETJU": "Nubia",
            "FAMILY_AKSUM_AGAW": "Aksum",
            "FAMILY_AKSUM_AGAZI": "Aksum",
            "FAMILY_AKSUM_TIGRAYAN": "Aksum",
            "FAMILY_AKSUM_BARYA": "Aksum",
        }
        return family_civ_map.get(family_name)

    def get_family_class_combo_stats(
        self,
        min_games: int = 2,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> pd.DataFrame:
        """Get statistics for 3-class family combinations.

        Analyzes which combinations of 3 family classes are most successful.

        Args:
            min_games: Minimum games for a combo to be included
            tournament_round: Specific round numbers to filter
            bracket: Bracket filter
            min_turns: Minimum turns
            max_turns: Maximum turns
            map_size: Map size filter
            map_class: Map class filter
            map_aspect: Map aspect ratio filter
            nations: List of civilizations to filter
            players: List of player names to filter
            result_filter: Filter by match result (winners/losers/all)

        Returns:
            DataFrame with columns: combo, games, wins, win_percentage
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=result_filter,
        )

        if not filtered:
            return pd.DataFrame()

        where_clause, params = self._build_player_filter(filtered, result_filter)

        query = f"""
        SELECT DISTINCT
            p.player_id,
            p.match_id,
            c.family_name,
            CASE WHEN mw.winner_player_id = p.player_id THEN 1 ELSE 0 END as is_winner
        FROM players p
        JOIN cities c ON p.match_id = c.match_id AND p.player_id = c.player_id
        LEFT JOIN match_winners mw ON p.match_id = mw.match_id
        WHERE {where_clause}
            AND c.family_name IS NOT NULL
        """

        with self.db.get_connection() as conn:
            df = conn.execute(query, params).df()

        if df.empty:
            return pd.DataFrame()

        # Transform to family class
        df["family_class"] = df["family_name"].apply(get_family_class)
        df = df[df["family_class"] != "Unknown"]

        # Build combo per player-match
        combos = []
        for (match_id, player_id), group in df.groupby(["match_id", "player_id"]):
            is_winner = group["is_winner"].iloc[0]
            classes = sorted(group["family_class"].unique())
            # Create combo string (sorted for consistency)
            combo = " + ".join(classes)
            combos.append({"combo": combo, "is_winner": is_winner})

        if not combos:
            return pd.DataFrame()

        combo_df = pd.DataFrame(combos)
        result = (
            combo_df.groupby("combo")
            .agg(
                games=("is_winner", "count"),
                wins=("is_winner", "sum"),
            )
            .reset_index()
        )
        result["win_percentage"] = (result["wins"] * 100.0 / result["games"]).round(2)

        # Filter by min_games
        result = result[result["games"] >= min_games]

        return result.sort_values("win_percentage", ascending=False)

    def get_nation_family_class_affinity(
        self,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> pd.DataFrame:
        """Get nation to family class affinity (how often each nation picks each class).

        Args:
            tournament_round: Specific round numbers to filter
            bracket: Bracket filter
            min_turns: Minimum turns
            max_turns: Maximum turns
            map_size: Map size filter
            map_class: Map class filter
            map_aspect: Map aspect ratio filter
            nations: List of civilizations to filter
            players: List of player names to filter
            result_filter: Filter by match result (winners/losers/all)

        Returns:
            DataFrame with columns: nation, family_class, pick_count, pick_percentage
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=result_filter,
        )

        if not filtered:
            return pd.DataFrame()

        where_clause, params = self._build_player_filter(filtered, result_filter)

        # Get distinct family classes per player (each player picks 3 of 4 families)
        query = f"""
        SELECT DISTINCT
            p.player_id,
            p.match_id,
            p.civilization as nation,
            c.family_name
        FROM players p
        JOIN cities c ON p.match_id = c.match_id AND p.player_id = c.player_id
        WHERE {where_clause}
            AND c.family_name IS NOT NULL
        """

        with self.db.get_connection() as conn:
            df = conn.execute(query, params).df()

        if df.empty:
            return pd.DataFrame()

        # Transform to family class
        df["family_class"] = df["family_name"].apply(get_family_class)
        df = df[df["family_class"] != "Unknown"]

        # Get unique player-class combinations (did this player pick this class?)
        player_picks = df.drop_duplicates(
            subset=["player_id", "match_id", "nation", "family_class"]
        )

        # Count how many players picked each class per nation
        result = (
            player_picks.groupby(["nation", "family_class"])
            .size()
            .reset_index(name="pick_count")
        )

        # Count total players per nation
        total_players_per_nation = (
            player_picks.groupby("nation")[["player_id", "match_id"]]
            .apply(lambda x: x.drop_duplicates().shape[0])
            .to_dict()
        )

        # Calculate percentage: what % of nation's players picked this class
        result["pick_percentage"] = result.apply(
            lambda row: round(
                row["pick_count"] * 100.0 / total_players_per_nation[row["nation"]], 2
            ),
            axis=1,
        )

        return result.sort_values(["nation", "pick_count"], ascending=[True, False])

    def get_family_city_distribution_by_result(
        self,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
    ) -> pd.DataFrame:
        """Get city distribution across family classes for winners vs losers.

        Args:
            tournament_round: Specific round numbers to filter
            bracket: Bracket filter
            min_turns: Minimum turns
            max_turns: Maximum turns
            map_size: Map size filter
            map_class: Map class filter
            map_aspect: Map aspect ratio filter
            nations: List of civilizations to filter
            players: List of player names to filter

        Returns:
            DataFrame with columns: result, family_class, avg_cities, total_cities
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=None,
        )

        if not filtered:
            return pd.DataFrame()

        match_ids = (
            filtered
            if not isinstance(filtered[0], tuple)
            else list(set(m for m, _ in filtered))
        )

        query = """
        SELECT
            p.player_id,
            p.match_id,
            c.family_name,
            COUNT(c.city_id) as city_count,
            CASE WHEN mw.winner_player_id = p.player_id THEN 'Winner' ELSE 'Loser' END as result
        FROM players p
        JOIN cities c ON p.match_id = c.match_id AND p.player_id = c.player_id
        LEFT JOIN match_winners mw ON p.match_id = mw.match_id
        WHERE p.match_id = ANY($match_ids)
            AND c.family_name IS NOT NULL
        GROUP BY p.player_id, p.match_id, c.family_name, mw.winner_player_id
        """

        with self.db.get_connection() as conn:
            df = conn.execute(query, {"match_ids": match_ids}).df()

        if df.empty:
            return pd.DataFrame()

        # Transform to family class
        df["family_class"] = df["family_name"].apply(get_family_class)
        df = df[df["family_class"] != "Unknown"]

        # Aggregate by result and class
        result = (
            df.groupby(["result", "family_class"])
            .agg(
                avg_cities=("city_count", "mean"),
                total_cities=("city_count", "sum"),
            )
            .reset_index()
        )
        result["avg_cities"] = result["avg_cities"].round(2)

        return result.sort_values(["result", "family_class"])

    def get_family_opinion_correlation(
        self,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
    ) -> pd.DataFrame:
        """Get average family opinion by match outcome.

        Analyzes whether higher family opinion correlates with winning.

        Args:
            tournament_round: Specific round numbers to filter
            bracket: Bracket filter
            min_turns: Minimum turns
            max_turns: Maximum turns
            map_size: Map size filter
            map_class: Map class filter
            map_aspect: Map aspect ratio filter
            nations: List of civilizations to filter
            players: List of player names to filter

        Returns:
            DataFrame with columns: player_name, match_id, avg_family_opinion, is_winner
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=None,
        )

        if not filtered:
            return pd.DataFrame()

        match_ids = (
            filtered
            if not isinstance(filtered[0], tuple)
            else list(set(m for m, _ in filtered))
        )

        # Get final turn family opinions for each player
        query = """
        WITH max_turns AS (
            SELECT
                match_id,
                player_id,
                MAX(turn_number) as max_turn
            FROM family_opinion_history
            WHERE match_id = ANY($match_ids)
            GROUP BY match_id, player_id
        )
        SELECT
            p.player_name,
            p.match_id,
            AVG(foh.opinion) as avg_family_opinion,
            CASE WHEN mw.winner_player_id = p.player_id THEN 1 ELSE 0 END as is_winner
        FROM players p
        JOIN max_turns mt ON p.match_id = mt.match_id AND p.player_id = mt.player_id
        JOIN family_opinion_history foh ON p.match_id = foh.match_id
            AND p.player_id = foh.player_id
            AND foh.turn_number = mt.max_turn
        LEFT JOIN match_winners mw ON p.match_id = mw.match_id
        WHERE p.match_id = ANY($match_ids)
        GROUP BY p.player_name, p.match_id, mw.winner_player_id, p.player_id
        """

        with self.db.get_connection() as conn:
            df = conn.execute(query, {"match_ids": match_ids}).df()

        if df.empty:
            return pd.DataFrame()

        df["avg_family_opinion"] = df["avg_family_opinion"].round(2)
        return df

    def get_family_opinion_over_time(
        self,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
    ) -> pd.DataFrame:
        """Get average family opinion over game progress for winners vs losers.

        Normalizes turn numbers to game percentage (0-100%) to compare
        across matches of different lengths.

        Args:
            tournament_round: Specific round numbers to filter
            bracket: Bracket filter
            min_turns: Minimum turns
            max_turns: Maximum turns
            map_size: Map size filter
            map_class: Map class filter
            map_aspect: Map aspect ratio filter
            nations: List of civilizations to filter
            players: List of player names to filter

        Returns:
            DataFrame with columns: game_pct, result, avg_opinion
        """
        match_ids = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
        )

        if not match_ids:
            return pd.DataFrame()

        # Normalize turns to game percentage and aggregate by winner/loser
        query = """
        WITH match_max_turns AS (
            SELECT match_id, MAX(turn_number) as max_turn
            FROM family_opinion_history
            WHERE match_id = ANY($match_ids)
            GROUP BY match_id
        ),
        opinion_with_pct AS (
            SELECT
                foh.match_id,
                foh.player_id,
                foh.turn_number,
                foh.opinion,
                mmt.max_turn,
                -- Bucket into 10% increments (0-10%, 10-20%, etc.)
                FLOOR((foh.turn_number::FLOAT / mmt.max_turn) * 10) * 10 as game_pct,
                CASE WHEN mw.winner_player_id = foh.player_id THEN 'Winner' ELSE 'Loser' END as result
            FROM family_opinion_history foh
            JOIN match_max_turns mmt ON foh.match_id = mmt.match_id
            LEFT JOIN match_winners mw ON foh.match_id = mw.match_id
            WHERE foh.match_id = ANY($match_ids)
              AND mmt.max_turn > 0
        )
        SELECT
            CAST(game_pct AS INTEGER) as game_pct,
            result,
            AVG(opinion) as avg_opinion
        FROM opinion_with_pct
        GROUP BY game_pct, result
        ORDER BY game_pct, result
        """

        with self.db.get_connection() as conn:
            df = conn.execute(query, {"match_ids": match_ids}).df()

        if df.empty:
            return pd.DataFrame()

        df["avg_opinion"] = df["avg_opinion"].round(2)
        return df

    def get_family_opinion_timeline(
        self,
        tournament_round: Optional[list[int]] = None,
        bracket: Optional[str] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None,
        map_size: Optional[list[str]] = None,
        map_class: Optional[list[str]] = None,
        map_aspect: Optional[list[str]] = None,
        nations: Optional[list[str]] = None,
        players: Optional[list[str]] = None,
        result_filter: ResultFilter = None,
    ) -> pd.DataFrame:
        """Get average family opinion per turn for each player across all their matches.

        Shows how each player's family relationships evolved throughout their games.
        Each player gets one line showing their average family opinion over time,
        aggregated across all their matches.

        Args:
            tournament_round: Filter by tournament round number
            bracket: Filter by bracket
            min_turns: Minimum turns
            max_turns: Maximum turns
            map_size: Map size filter
            map_class: Map class filter
            map_aspect: Map aspect ratio filter
            nations: List of civilizations to filter
            players: List of player names to filter
            result_filter: Filter by match result

        Returns:
            DataFrame with columns: player_name, turn_number, avg_opinion
        """
        filtered = self._get_filtered_match_ids(
            tournament_round=tournament_round,
            bracket=bracket,
            min_turns=min_turns,
            max_turns=max_turns,
            map_size=map_size,
            map_class=map_class,
            map_aspect=map_aspect,
            nations=nations,
            players=players,
            result_filter=result_filter,
        )

        if not filtered:
            return pd.DataFrame()

        # Build player-level filter
        where_clause, params = self._build_player_filter(
            filtered, result_filter, table_alias="p"
        )

        query = f"""
        SELECT
            p.player_name,
            foh.turn_number,
            AVG(foh.opinion) as avg_opinion
        FROM family_opinion_history foh
        JOIN players p ON foh.match_id = p.match_id AND foh.player_id = p.player_id
        WHERE {where_clause}
        GROUP BY p.player_name, foh.turn_number
        ORDER BY p.player_name, foh.turn_number
        """

        with self.db.get_connection() as conn:
            df = conn.execute(query, params).df()

        if df.empty:
            return pd.DataFrame()

        df["avg_opinion"] = df["avg_opinion"].round(2)
        return df

    # =========================================================================
    # Player Skill Rating Methods
    # =========================================================================

    def get_player_skill_ratings(self, min_matches: int = 1) -> pd.DataFrame:
        """Calculate composite skill ratings for all players.

        Combines win rate, economic efficiency, and governance stability into
        a single skill score (0-100). Players with fewer matches have their
        scores regressed toward the population mean.

        Components (equal weights, 25% each):
        - Win Component: Win rate (70%) + Win margin percentile (30%)
        - Economy Component: Total productive yields per turn
        - Governance Component: Legitimacy (33%) + Expansion rate (33%) + Law rate (33%)
        - Military Component: Military power (40%) + Army diversity (20%) + Power lead (40%)

        Args:
            min_matches: Minimum matches played to include (default 1)

        Returns:
            DataFrame with columns:
                - player_name: Display name
                - participant_id: Participant ID (NULL if unlinked)
                - matches_played: Number of matches
                - skill_score: Composite score (0-100)
                - is_provisional: True if < 3 matches
                - win_component: Win-based sub-score (0-100)
                - economy_component: Economy sub-score (0-100)
                - governance_component: Governance sub-score (0-100)
                - military_component: Military sub-score (0-100)
        """
        # Get per-game metrics for all players
        per_game_df = self._get_per_game_skill_metrics()

        if per_game_df.empty:
            return pd.DataFrame()

        # Aggregate to player level with game-length weighting
        player_df = self._aggregate_skill_metrics(per_game_df)

        if player_df.empty:
            return pd.DataFrame()

        # Filter by minimum matches
        player_df = player_df[player_df["matches_played"] >= min_matches].copy()

        if player_df.empty:
            return pd.DataFrame()

        # Calculate percentiles within population for normalization
        player_df = self._normalize_skill_metrics(player_df)

        # Calculate composite score with confidence adjustment
        player_df = self._calculate_composite_score(player_df)

        player_df["is_provisional"] = player_df["matches_played"] < 3

        # Select and order final columns
        result_columns = [
            "player_name",
            "participant_id",
            "matches_played",
            "skill_score",
            "is_provisional",
            "win_component",
            "economy_component",
            "governance_component",
            "military_component",
            "win_rate",
            "avg_win_margin",
            "avg_total_yields",
            "avg_expansion_rate",
            "avg_law_rate",
            "avg_legitimacy",
            "avg_military_power",
            "avg_army_diversity",
            "avg_power_lead",
        ]

        # Only include columns that exist
        result_columns = [c for c in result_columns if c in player_df.columns]

        return player_df[result_columns].sort_values(
            "skill_score", ascending=False
        ).reset_index(drop=True)

    def _get_per_game_skill_metrics(self) -> pd.DataFrame:
        """Calculate skill metrics for each player in each match.

        Returns:
            DataFrame with per-game metrics for aggregation
        """
        query = """
        WITH match_game_lengths AS (
            SELECT match_id, total_turns
            FROM matches
            WHERE total_turns >= 20  -- Exclude very short games
        ),
        player_wins AS (
            SELECT
                p.player_id,
                p.match_id,
                CASE WHEN mw.winner_player_id = p.player_id THEN 1 ELSE 0 END as won
            FROM players p
            LEFT JOIN match_winners mw ON p.match_id = mw.match_id
        ),
        final_points AS (
            -- Get final turn points for each player
            SELECT
                pph.player_id,
                pph.match_id,
                pph.points as final_points
            FROM player_points_history pph
            INNER JOIN (
                SELECT player_id, match_id, MAX(turn_number) as max_turn
                FROM player_points_history
                GROUP BY player_id, match_id
            ) last_turn ON pph.player_id = last_turn.player_id
                AND pph.match_id = last_turn.match_id
                AND pph.turn_number = last_turn.max_turn
        ),
        point_margins AS (
            -- Calculate win margin (winner points - loser points)
            SELECT
                mw.match_id,
                mw.winner_player_id,
                fp_winner.final_points - fp_loser.final_points as win_margin
            FROM match_winners mw
            JOIN final_points fp_winner ON mw.match_id = fp_winner.match_id
                AND mw.winner_player_id = fp_winner.player_id
            JOIN players p_loser ON mw.match_id = p_loser.match_id
                AND p_loser.player_id != mw.winner_player_id
            JOIN final_points fp_loser ON p_loser.match_id = fp_loser.match_id
                AND p_loser.player_id = fp_loser.player_id
        ),
        total_yields_per_turn AS (
            -- Sum of all productive yields per turn for each player-match
            -- Includes: science, civics, training, culture, money, growth, food, orders
            -- Normalized by sqrt(game_length/50) to account for yield scaling with game progression
            SELECT
                yh.player_id,
                yh.match_id,
                AVG(yh.amount / 10.0) as avg_total_yields_raw,
                -- Normalize: divide by sqrt(game_length/50) so shorter games aren't penalized
                AVG(yh.amount / 10.0) / SQRT(m.total_turns / 50.0) as avg_total_yields
            FROM player_yield_history yh
            JOIN matches m ON yh.match_id = m.match_id
            WHERE yh.resource_type IN (
                'YIELD_SCIENCE', 'YIELD_CIVICS', 'YIELD_TRAINING', 'YIELD_CULTURE',
                'YIELD_MONEY', 'YIELD_GROWTH', 'YIELD_FOOD', 'YIELD_ORDERS'
            )
            AND m.total_turns > 0
            GROUP BY yh.player_id, yh.match_id, m.total_turns
        ),
        expansion_rates AS (
            -- Cities per 100 turns for each player-match
            SELECT
                c.player_id,
                c.match_id,
                (COUNT(DISTINCT c.city_id) * 100.0 / m.total_turns) as expansion_rate
            FROM cities c
            JOIN matches m ON c.match_id = m.match_id
            WHERE m.total_turns > 0
            GROUP BY c.player_id, c.match_id, m.total_turns
        ),
        law_rates AS (
            -- Laws adopted per 100 turns for each player-match
            SELECT
                e.player_id,
                e.match_id,
                (COUNT(*) * 100.0 / m.total_turns) as law_rate
            FROM events e
            JOIN matches m ON e.match_id = m.match_id
            WHERE e.event_type = 'LAW_ADOPTED'
                AND e.player_id IS NOT NULL
                AND m.total_turns > 0
            GROUP BY e.player_id, e.match_id, m.total_turns
        ),
        legitimacy_stats AS (
            -- Legitimacy avg and min for each player-match
            SELECT
                lh.player_id,
                lh.match_id,
                AVG(lh.legitimacy) as avg_legitimacy,
                MIN(lh.legitimacy) as min_legitimacy
            FROM player_legitimacy_history lh
            GROUP BY lh.player_id, lh.match_id
        ),
        -- Military metrics for Military dimension
        military_power_stats AS (
            -- Average military power per player-match
            SELECT
                mh.player_id,
                mh.match_id,
                AVG(mh.military_power) as avg_military_power
            FROM player_military_history mh
            GROUP BY mh.player_id, mh.match_id
        ),
        army_diversity AS (
            -- Count distinct military unit roles used (infantry, cavalry, ranged, siege, naval)
            -- Normalized to 0-100: 5 roles = 100, 1 role = 20
            SELECT
                up.player_id,
                up.match_id,
                COUNT(DISTINCT uc.role) as distinct_roles,
                (COUNT(DISTINCT uc.role) * 100.0 / 5.0) as diversity_score
            FROM units_produced up
            JOIN unit_classifications uc ON up.unit_type = uc.unit_type
            WHERE uc.category = 'military'
            GROUP BY up.player_id, up.match_id
        ),
        power_lead AS (
            -- Percentage of turns where player has strictly higher military power than opponent
            SELECT
                p1.player_id,
                p1.match_id,
                COUNT(CASE WHEN m1.military_power > m2.military_power THEN 1 END) * 100.0
                    / NULLIF(COUNT(*), 0) as power_lead_pct
            FROM players p1
            JOIN players p2 ON p1.match_id = p2.match_id AND p1.player_id != p2.player_id
            JOIN player_military_history m1 ON p1.player_id = m1.player_id
                AND p1.match_id = m1.match_id
            JOIN player_military_history m2 ON p2.player_id = m2.player_id
                AND p2.match_id = m2.match_id AND m1.turn_number = m2.turn_number
            GROUP BY p1.player_id, p1.match_id
        )
        SELECT
            p.player_id,
            p.match_id,
            COALESCE(tp.display_name, p.player_name) as player_name,
            tp.participant_id,
            COALESCE(
                CAST(tp.participant_id AS VARCHAR),
                'unlinked_' || p.player_name_normalized
            ) as grouping_key,
            mgl.total_turns as game_length,
            pw.won,
            COALESCE(pm.win_margin, 0) as win_margin,
            COALESCE(typt.avg_total_yields, 0) as total_yields_per_turn,
            COALESCE(er.expansion_rate, 0) as expansion_rate,
            COALESCE(lr.law_rate, 0) as law_rate,
            COALESCE(ls.avg_legitimacy, 50) as avg_legitimacy,
            COALESCE(ls.min_legitimacy, 0) as min_legitimacy,
            -- Military metrics
            COALESCE(mps.avg_military_power, 0) as avg_military_power,
            COALESCE(ad.diversity_score, 0) as army_diversity_score,
            COALESCE(pl.power_lead_pct, 0) as power_lead_pct
        FROM players p
        JOIN match_game_lengths mgl ON p.match_id = mgl.match_id
        LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
        LEFT JOIN player_wins pw ON p.player_id = pw.player_id AND p.match_id = pw.match_id
        LEFT JOIN point_margins pm ON p.match_id = pm.match_id
            AND p.player_id = pm.winner_player_id
        LEFT JOIN total_yields_per_turn typt ON p.player_id = typt.player_id
            AND p.match_id = typt.match_id
        LEFT JOIN expansion_rates er ON p.player_id = er.player_id
            AND p.match_id = er.match_id
        LEFT JOIN law_rates lr ON p.player_id = lr.player_id
            AND p.match_id = lr.match_id
        LEFT JOIN legitimacy_stats ls ON p.player_id = ls.player_id
            AND p.match_id = ls.match_id
        LEFT JOIN military_power_stats mps ON p.player_id = mps.player_id
            AND p.match_id = mps.match_id
        LEFT JOIN army_diversity ad ON p.player_id = ad.player_id
            AND p.match_id = ad.match_id
        LEFT JOIN power_lead pl ON p.player_id = pl.player_id
            AND p.match_id = pl.match_id
        ORDER BY p.player_id, p.match_id
        """

        with self.db.get_connection() as conn:
            return conn.execute(query).df()

    def _load_player_name_aliases(self) -> dict[str, str]:
        """Load player name aliases from config file.

        Returns:
            Dict mapping normalized names to canonical names
        """
        import json
        from pathlib import Path

        # Use path relative to this file's location (file is in tournament_visualizer/)
        this_dir = Path(__file__).parent
        package_dir = this_dir.parent
        alias_file = package_dir / "player_name_aliases.json"
        if not alias_file.exists():
            return {}

        try:
            with open(alias_file) as f:
                data = json.load(f)
            return data.get("aliases", {})
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load player name aliases: {e}")
            return {}

    def _apply_name_aliases(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply player name aliases to grouping_key column.

        Args:
            df: DataFrame with grouping_key column

        Returns:
            DataFrame with aliases applied to grouping_key
        """
        aliases = self._load_player_name_aliases()
        if not aliases:
            return df

        # Apply aliases to grouping_key (format: 'unlinked_<normalized_name>')
        def apply_alias(key: str) -> str:
            if key.startswith("unlinked_"):
                normalized = key[9:]  # Remove 'unlinked_' prefix
                if normalized in aliases:
                    return f"unlinked_{aliases[normalized]}"
            return key

        df = df.copy()
        df["grouping_key"] = df["grouping_key"].apply(apply_alias)
        return df

    def _aggregate_skill_metrics(self, per_game_df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate per-game metrics to player level with game-length weighting.

        Args:
            per_game_df: DataFrame from _get_per_game_skill_metrics()

        Returns:
            DataFrame with one row per player, aggregated metrics
        """
        import numpy as np

        if per_game_df.empty:
            return pd.DataFrame()

        # Apply name aliases before aggregation
        per_game_df = self._apply_name_aliases(per_game_df)

        # Weight by sqrt(game_length) for balanced short/long game influence
        per_game_df["weight"] = np.sqrt(per_game_df["game_length"])

        def weighted_avg(group: pd.DataFrame, col: str) -> float:
            """Calculate weighted average for a column."""
            weights = group["weight"]
            values = group[col]
            # Handle NaN values
            mask = ~np.isnan(values)
            if not mask.any():
                return 0.0
            return np.average(values[mask], weights=weights[mask])

        # Group by player (using grouping_key for consistency)
        aggregated = per_game_df.groupby("grouping_key").agg(
            player_name=("player_name", "first"),
            participant_id=("participant_id", "first"),
            matches_played=("match_id", "nunique"),
            wins=("won", "sum"),
            total_win_margin=("win_margin", "sum"),
        ).reset_index()

        # Calculate win rate
        aggregated["win_rate"] = (
            aggregated["wins"] * 100.0 / aggregated["matches_played"]
        ).round(2)

        # Calculate average win margin (only for wins)
        win_margins = per_game_df[per_game_df["won"] == 1].groupby("grouping_key").agg(
            avg_win_margin=("win_margin", "mean")
        ).reset_index()
        aggregated = aggregated.merge(win_margins, on="grouping_key", how="left")
        aggregated["avg_win_margin"] = aggregated["avg_win_margin"].fillna(0)

        # Calculate weighted averages for other metrics
        weighted_metrics = per_game_df.groupby("grouping_key").apply(
            lambda g: pd.Series({
                "avg_total_yields": weighted_avg(g, "total_yields_per_turn"),
                "avg_expansion_rate": weighted_avg(g, "expansion_rate"),
                "avg_law_rate": weighted_avg(g, "law_rate"),
                "avg_legitimacy": weighted_avg(g, "avg_legitimacy"),
                # Military metrics
                "avg_military_power": weighted_avg(g, "avg_military_power"),
                "avg_army_diversity": weighted_avg(g, "army_diversity_score"),
                "avg_power_lead": weighted_avg(g, "power_lead_pct"),
            }),
            include_groups=False
        ).reset_index()

        aggregated = aggregated.merge(weighted_metrics, on="grouping_key", how="left")

        return aggregated

    def _normalize_skill_metrics(self, player_df: pd.DataFrame) -> pd.DataFrame:
        """Convert raw metrics to percentiles within the population.

        Args:
            player_df: DataFrame with aggregated player metrics

        Returns:
            DataFrame with percentile-normalized metrics added
        """
        from scipy import stats

        def to_percentile(series: pd.Series) -> pd.Series:
            """Convert values to percentiles (0-100)."""
            return series.apply(
                lambda x: stats.percentileofscore(series.dropna(), x)
                if pd.notna(x) else 50.0
            )

        # Normalize each metric to percentile
        player_df["win_rate_pct"] = to_percentile(player_df["win_rate"])
        player_df["win_margin_pct"] = to_percentile(player_df["avg_win_margin"])
        player_df["total_yields_pct"] = to_percentile(player_df["avg_total_yields"])
        player_df["expansion_pct"] = to_percentile(player_df["avg_expansion_rate"])
        player_df["law_rate_pct"] = to_percentile(player_df["avg_law_rate"])
        player_df["legitimacy_pct"] = to_percentile(player_df["avg_legitimacy"])

        # Military metrics - military_power uses percentile, others are already 0-100
        player_df["military_power_pct"] = to_percentile(player_df["avg_military_power"])
        # army_diversity and power_lead are already on 0-100 scale, no percentile needed

        return player_df

    def _calculate_composite_score(self, player_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate final composite skill score with confidence adjustment.

        Formula (equal weights):
        - Win Component (25%): win_rate_pct * 0.7 + win_margin_pct * 0.3
        - Economy Component (25%): total_yields_pct (all productive yields combined)
        - Governance Component (25%): legitimacy (33%) + expansion (33%) + law rate (33%)
        - Military Component (25%): military_power (40%) + army_diversity (20%) + power_lead (40%)

        Low-sample players are regressed toward population mean (50).

        Args:
            player_df: DataFrame with percentile-normalized metrics

        Returns:
            DataFrame with composite scores added
        """
        import numpy as np

        # Calculate component scores
        player_df["win_component"] = (
            player_df["win_rate_pct"] * 0.7 +
            player_df["win_margin_pct"] * 0.3
        )

        player_df["economy_component"] = player_df["total_yields_pct"]

        player_df["governance_component"] = (
            player_df["legitimacy_pct"] / 3.0 +
            player_df["expansion_pct"] / 3.0 +
            player_df["law_rate_pct"] / 3.0
        )

        # Military component: military_power (40%) + army_diversity (20%) + power_lead (40%)
        # military_power_pct is percentile-normalized (0-100)
        # avg_army_diversity and avg_power_lead are already 0-100 scale
        player_df["military_component"] = (
            player_df["military_power_pct"] * 0.40 +
            player_df["avg_army_diversity"] * 0.20 +
            player_df["avg_power_lead"] * 0.40
        )

        # Calculate raw composite score (equal weights for all 4 components)
        raw_score = (
            player_df["win_component"] * 0.25 +
            player_df["economy_component"] * 0.25 +
            player_df["governance_component"] * 0.25 +
            player_df["military_component"] * 0.25
        )

        # Apply confidence adjustment (regress toward 50 for low sample sizes)
        # At 1 match: 20% actual, 80% population mean
        # At 3 matches: 50% actual, 50% population mean
        # At 5+ matches: 80%+ actual
        confidence_threshold = 5
        confidence = np.minimum(
            player_df["matches_played"] / confidence_threshold, 1.0
        )
        weight = np.sqrt(confidence)  # sqrt for faster initial confidence gain

        population_mean = 50.0
        player_df["skill_score"] = (
            weight * raw_score + (1 - weight) * population_mean
        ).round(1)

        # Round component scores for display
        player_df["win_component"] = player_df["win_component"].round(1)
        player_df["economy_component"] = player_df["economy_component"].round(1)
        player_df["governance_component"] = player_df["governance_component"].round(1)
        player_df["military_component"] = player_df["military_component"].round(1)

        return player_df

    def get_player_skill_breakdown(self, player_name: str) -> pd.DataFrame:
        """Get detailed skill breakdown for a specific player.

        Shows per-game performance with all raw metrics for detailed analysis.

        Args:
            player_name: Player name to look up

        Returns:
            DataFrame with per-game metrics for this player
        """
        per_game_df = self._get_per_game_skill_metrics()

        if per_game_df.empty:
            return pd.DataFrame()

        # Filter to specific player
        player_games = per_game_df[
            per_game_df["player_name"].str.lower() == player_name.lower()
        ].copy()

        if player_games.empty:
            return pd.DataFrame()

        # Add readable columns
        player_games["result"] = player_games["won"].map({1: "Win", 0: "Loss"})

        return player_games[[
            "match_id",
            "game_length",
            "result",
            "win_margin",
            "science_per_turn",
            "expansion_rate",
            "ambition_rate",
            "avg_legitimacy",
            "min_legitimacy",
        ]].sort_values("match_id")


# Global queries instance
queries = TournamentQueries()


def get_queries() -> TournamentQueries:
    """Get the global queries instance.

    Returns:
        TournamentQueries instance
    """
    return queries
