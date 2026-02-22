"""Evidence panel generation for chat NL query results.

After the LLM generates and executes SQL, this module inspects the generated
SQL and result DataFrame to automatically produce "evidence" detail tables
that show the individual records behind aggregate results. Users can verify
accuracy against their knowledge of the tournament without understanding SQL.
"""

import logging
import re
from dataclasses import dataclass

import pandas as pd

from tournament_visualizer.data.database import TournamentDatabase

logger = logging.getLogger(__name__)

_EVIDENCE_ROW_LIMIT = 500


@dataclass
class EvidencePanel:
    """A collapsible evidence panel showing supporting detail rows."""

    title: str
    description: str
    df: pd.DataFrame


def generate_evidence(
    sql: str, result_df: pd.DataFrame, db: TournamentDatabase
) -> list[EvidencePanel]:
    """Generate evidence panels based on the generated SQL and its results.

    Detects which tables the SQL references, extracts scoping values from
    the result DataFrame, and runs pre-written evidence queries to return
    human-readable detail rows.
    """
    panels: list[EvidencePanel] = []
    sql_upper = sql.upper()
    scope = _extract_scope(result_df)
    sql_filters = _extract_sql_filters(sql)

    evidence_generators = [
        ("MATCH_WINNERS", _match_results_evidence),
        ("EVENTS", _events_evidence),
        ("CITIES", _cities_evidence),
        ("PLAYER_YIELD_HISTORY", _player_yield_evidence),
        ("TERRITORIES", _territories_evidence),
        ("TECHNOLOGY_PROGRESS", _technology_evidence),
        ("UNITS_PRODUCED", _units_produced_evidence),
        ("CITY_UNIT_PRODUCTION", _city_unit_production_evidence),
    ]

    try:
        with db.get_connection() as conn:
            for table_name, generator_fn in evidence_generators:
                if _references_table(sql_upper, table_name):
                    try:
                        panel = generator_fn(conn, scope, sql_filters)
                        if panel and not panel.df.empty:
                            panels.append(panel)
                    except Exception as e:
                        logger.warning(
                            f"Evidence generation failed for {table_name}: {e}"
                        )
    except Exception as e:
        logger.warning(f"Evidence generation failed: {e}")

    return panels


def _references_table(sql_upper: str, table_name: str) -> bool:
    """Check if SQL references a table name (word-boundary match)."""
    return bool(re.search(r"\b" + table_name + r"\b", sql_upper))


def _extract_scope(result_df: pd.DataFrame) -> dict[str, list]:
    """Extract scoping values from the result DataFrame.

    Looks for columns with recognizable names and extracts their unique
    values for use as WHERE filters in evidence queries.
    """
    scope: dict[str, list] = {}

    for col in result_df.columns:
        col_lower = col.lower().replace(" ", "_")

        if col_lower == "match_id":
            try:
                vals = result_df[col].dropna().unique().tolist()
                scope["match_ids"] = [int(v) for v in vals]
            except (ValueError, TypeError):
                pass

        elif col_lower in (
            "player_name",
            "player",
            "winner_name",
            "loser_name",
            "opponent_name",
            "winner",
            "opponent",
        ):
            vals = result_df[col].dropna().unique().tolist()
            if vals and isinstance(vals[0], str):
                scope.setdefault("player_names", []).extend(
                    str(v) for v in vals if str(v).strip()
                )

        elif col_lower in ("civilization", "civ", "nation", "winner_civ"):
            vals = result_df[col].dropna().unique().tolist()
            if vals and isinstance(vals[0], str):
                scope.setdefault("civilizations", []).extend(
                    str(v) for v in vals if str(v).strip()
                )

    # Deduplicate
    for key in ("player_names", "civilizations"):
        if key in scope:
            scope[key] = list(dict.fromkeys(scope[key]))

    return scope


@dataclass
class _SqlFilters:
    """Filters extracted from the LLM's generated SQL."""

    event_types: list[str]
    description_patterns: list[str]
    unit_types: list[str]
    improvement_types: list[str]
    specialist_types: list[str]
    resource_types: list[str]
    tech_patterns: list[str]


def _extract_sql_filters(sql: str) -> _SqlFilters:
    """Extract filter values from the LLM's SQL to scope evidence queries.

    Looks for quoted string literals near known column names to understand
    what subset of data the LLM queried.
    """
    return _SqlFilters(
        event_types=_extract_ilike_or_eq(sql, "event_type"),
        description_patterns=_extract_ilike_or_eq(sql, "description"),
        unit_types=_extract_ilike_or_eq(sql, "unit_type"),
        improvement_types=_extract_ilike_or_eq(sql, "improvement_type"),
        specialist_types=_extract_ilike_or_eq(sql, "specialist_type"),
        resource_types=_extract_ilike_or_eq(sql, "resource_type"),
        tech_patterns=_extract_ilike_or_eq(sql, "tech_name"),
    )


def _extract_ilike_or_eq(sql: str, column_name: str) -> list[str]:
    """Extract string values used in = or ILIKE comparisons for a column.

    Matches patterns like:
      column_name = 'VALUE'
      column_name ILIKE '%VALUE%'
      column_name ILIKE "VALUE"
    """
    # Match single-quoted values
    pattern_single = (
        r"(?:\w+\.)?" + column_name + r"\s+(?:=|ILIKE)\s+'([^']+)'"
    )
    # Match double-quoted values
    pattern_double = (
        r"(?:\w+\.)?" + column_name + r'\s+(?:=|ILIKE)\s+"([^"]+)"'
    )
    matches = re.findall(pattern_single, sql, re.IGNORECASE)
    matches += re.findall(pattern_double, sql, re.IGNORECASE)
    return list(dict.fromkeys(matches))  # deduplicate, preserve order


def _build_where_clause(
    scope: dict[str, list],
    match_id_col: str = "m.match_id",
    player_name_col: str = "COALESCE(tp.display_name, p.player_name)",
    civilization_col: str = "p.civilization",
) -> tuple[str, list]:
    """Build a WHERE clause from scope values.

    Returns (where_sql, params) where where_sql starts with "WHERE" or is empty.
    Player names are matched via COALESCE(tp.display_name, p.player_name)
    since the result DataFrame uses tournament participant display names,
    not raw save file player names.
    """
    conditions: list[str] = []
    params: list = []

    if "match_ids" in scope and scope["match_ids"]:
        placeholders = ", ".join("?" for _ in scope["match_ids"])
        conditions.append(f"{match_id_col} IN ({placeholders})")
        params.extend(scope["match_ids"])
    elif "player_names" in scope and scope["player_names"]:
        placeholders = ", ".join("?" for _ in scope["player_names"])
        conditions.append(f"{player_name_col} IN ({placeholders})")
        params.extend(scope["player_names"])
    elif "civilizations" in scope and scope["civilizations"]:
        placeholders = ", ".join("?" for _ in scope["civilizations"])
        conditions.append(f"{civilization_col} IN ({placeholders})")
        params.extend(scope["civilizations"])

    if conditions:
        return "WHERE " + " AND ".join(conditions), params
    return "", []


def _append_filter_conditions(
    where_clause: str,
    params: list,
    column: str,
    values: list[str],
) -> tuple[str, list]:
    """Append ILIKE conditions for extracted SQL filter values.

    Each value may contain % wildcards (from ILIKE patterns in the original SQL).
    """
    if not values:
        return where_clause, params

    ilike_parts: list[str] = []
    for val in values:
        ilike_parts.append(f"{column} ILIKE ?")
        params.append(val)

    combined = " OR ".join(ilike_parts)
    if len(ilike_parts) > 1:
        combined = f"({combined})"

    if where_clause:
        where_clause += f" AND {combined}"
    else:
        where_clause = f"WHERE {combined}"

    return where_clause, params


# --- Evidence query functions ---


def _match_results_evidence(
    conn: object, scope: dict[str, list], sql_filters: _SqlFilters
) -> EvidencePanel | None:
    """Show individual match results with both players and winner."""
    where_clause, params = _build_where_clause(scope)

    query = f"""
        SELECT
            m.game_name AS match,
            COALESCE(tp.display_name, p.player_name) AS player_name,
            p.civilization,
            CASE WHEN mw.winner_player_id = p.player_id
                 THEN 'Winner' ELSE '' END AS result,
            m.total_turns AS turns
        FROM matches m
        JOIN players p ON m.match_id = p.match_id
        LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
        LEFT JOIN match_winners mw ON m.match_id = mw.match_id
        {where_clause}
        ORDER BY m.match_id, p.player_id
        LIMIT {_EVIDENCE_ROW_LIMIT}
    """

    df = conn.execute(query, params).df()
    if df.empty:
        return None

    match_count = df["match"].nunique()
    description = _scope_description(scope, f"{match_count} match(es)")

    return EvidencePanel(
        title="Match Results",
        description=f"Individual match results for {description}",
        df=df,
    )


def _events_evidence(
    conn: object, scope: dict[str, list], sql_filters: _SqlFilters
) -> EvidencePanel | None:
    """Show individual event records, filtered to the same event types as the LLM query."""
    where_clause, params = _build_where_clause(scope)

    where_clause, params = _append_filter_conditions(
        where_clause, params, "e.event_type", sql_filters.event_types
    )
    where_clause, params = _append_filter_conditions(
        where_clause, params, "e.description", sql_filters.description_patterns
    )

    query = f"""
        SELECT
            m.game_name AS match,
            COALESCE(tp.display_name, p.player_name) AS player_name,
            e.event_type,
            e.description,
            e.turn_number AS turn
        FROM events e
        JOIN matches m ON e.match_id = m.match_id
        LEFT JOIN players p ON e.match_id = p.match_id
            AND e.player_id = p.player_id
        LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
        {where_clause}
        ORDER BY m.match_id, e.turn_number
        LIMIT {_EVIDENCE_ROW_LIMIT}
    """

    df = conn.execute(query, params).df()
    if df.empty:
        return None

    event_count = len(df)
    description = _scope_description(scope, f"{event_count} event(s)")

    return EvidencePanel(
        title="Event Detail",
        description=f"Individual events for {description}",
        df=df,
    )


def _cities_evidence(
    conn: object, scope: dict[str, list], sql_filters: _SqlFilters
) -> EvidencePanel | None:
    """Show individual city records."""
    where_clause, params = _build_where_clause(scope)

    query = f"""
        SELECT
            m.game_name AS match,
            COALESCE(tp.display_name, p.player_name) AS player_name,
            c.city_name,
            c.founded_turn,
            CASE WHEN c.is_capital THEN 'Yes' ELSE '' END AS capital,
            c.population
        FROM cities c
        JOIN matches m ON c.match_id = m.match_id
        JOIN players p ON c.match_id = p.match_id AND c.player_id = p.player_id
        LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
        {where_clause}
        ORDER BY m.match_id, c.founded_turn
        LIMIT {_EVIDENCE_ROW_LIMIT}
    """

    df = conn.execute(query, params).df()
    if df.empty:
        return None

    city_count = len(df)
    description = _scope_description(scope, f"{city_count} city/cities")

    return EvidencePanel(
        title="City Detail",
        description=f"Individual cities for {description}",
        df=df,
    )


def _player_yield_evidence(
    conn: object, scope: dict[str, list], sql_filters: _SqlFilters
) -> EvidencePanel | None:
    """Show yield history records (amount divided by 10 for display)."""
    where_clause, params = _build_where_clause(scope)

    where_clause, params = _append_filter_conditions(
        where_clause, params, "yh.resource_type", sql_filters.resource_types
    )

    query = f"""
        SELECT
            m.game_name AS match,
            COALESCE(tp.display_name, p.player_name) AS player_name,
            yh.resource_type AS yield_type,
            yh.turn_number AS turn,
            yh.amount / 10.0 AS amount
        FROM player_yield_history yh
        JOIN matches m ON yh.match_id = m.match_id
        JOIN players p ON yh.match_id = p.match_id
            AND yh.player_id = p.player_id
        LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
        {where_clause}
        ORDER BY m.match_id, player_name, yh.turn_number
        LIMIT {_EVIDENCE_ROW_LIMIT}
    """

    df = conn.execute(query, params).df()
    if df.empty:
        return None

    row_count = len(df)
    description = _scope_description(scope, f"{row_count} yield record(s)")

    return EvidencePanel(
        title="Yield Detail",
        description=f"Per-turn yield data for {description}",
        df=df,
    )


def _territories_evidence(
    conn: object, scope: dict[str, list], sql_filters: _SqlFilters
) -> EvidencePanel | None:
    """Show territory summary (aggregated improvement/specialist counts).

    Territories data is very large, so we aggregate rather than showing
    individual tile rows.
    """
    where_clause, params = _build_where_clause(scope)

    where_clause, params = _append_filter_conditions(
        where_clause, params, "t.improvement_type", sql_filters.improvement_types
    )
    where_clause, params = _append_filter_conditions(
        where_clause, params, "t.specialist_type", sql_filters.specialist_types
    )

    # Use final turn for each match to show end-state
    query = f"""
        SELECT
            m.game_name AS match,
            COALESCE(tp.display_name, p.player_name) AS player_name,
            t.improvement_type,
            t.specialist_type,
            COUNT(*) AS tile_count
        FROM territories t
        JOIN matches m ON t.match_id = m.match_id
        JOIN players p ON t.match_id = p.match_id
            AND t.owner_player_id = p.player_id
        LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
        {where_clause}
            {"AND" if where_clause else "WHERE"}
            t.turn_number = (
                SELECT MAX(t2.turn_number)
                FROM territories t2
                WHERE t2.match_id = t.match_id
            )
            AND (t.improvement_type IS NOT NULL OR t.specialist_type IS NOT NULL)
        GROUP BY m.game_name, player_name, t.improvement_type, t.specialist_type
        ORDER BY m.game_name, player_name, tile_count DESC
        LIMIT {_EVIDENCE_ROW_LIMIT}
    """

    df = conn.execute(query, params).df()
    if df.empty:
        return None

    row_count = len(df)
    description = _scope_description(
        scope, f"{row_count} improvement/specialist type(s)"
    )

    return EvidencePanel(
        title="Territory Detail",
        description=f"End-of-game improvements and specialists for {description}",
        df=df,
    )


def _technology_evidence(
    conn: object, scope: dict[str, list], sql_filters: _SqlFilters
) -> EvidencePanel | None:
    """Show technology research records."""
    where_clause, params = _build_where_clause(
        scope, player_name_col="COALESCE(tpart.display_name, p.player_name)"
    )

    where_clause, params = _append_filter_conditions(
        where_clause, params, "tp.tech_name", sql_filters.tech_patterns
    )

    query = f"""
        SELECT
            m.game_name AS match,
            COALESCE(tpart.display_name, p.player_name) AS player_name,
            tp.tech_name AS technology,
            tp.count AS times_researched
        FROM technology_progress tp
        JOIN matches m ON tp.match_id = m.match_id
        JOIN players p ON tp.match_id = p.match_id
            AND tp.player_id = p.player_id
        LEFT JOIN tournament_participants tpart ON p.participant_id = tpart.participant_id
        {where_clause}
        ORDER BY m.match_id, player_name, tp.tech_name
        LIMIT {_EVIDENCE_ROW_LIMIT}
    """

    df = conn.execute(query, params).df()
    if df.empty:
        return None

    tech_count = df["technology"].nunique() if "technology" in df.columns else len(df)
    description = _scope_description(scope, f"{tech_count} technology/technologies")

    return EvidencePanel(
        title="Technology Detail",
        description=f"Technology research records for {description}",
        df=df,
    )


def _units_produced_evidence(
    conn: object, scope: dict[str, list], sql_filters: _SqlFilters
) -> EvidencePanel | None:
    """Show per-player unit production totals."""
    where_clause, params = _build_where_clause(scope)

    where_clause, params = _append_filter_conditions(
        where_clause, params, "up.unit_type", sql_filters.unit_types
    )

    query = f"""
        SELECT
            m.game_name AS match,
            COALESCE(tp.display_name, p.player_name) AS player_name,
            up.unit_type,
            up.count
        FROM units_produced up
        JOIN matches m ON up.match_id = m.match_id
        JOIN players p ON up.match_id = p.match_id
            AND up.player_id = p.player_id
        LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
        {where_clause}
        ORDER BY m.match_id, player_name, up.count DESC
        LIMIT {_EVIDENCE_ROW_LIMIT}
    """

    df = conn.execute(query, params).df()
    if df.empty:
        return None

    row_count = len(df)
    description = _scope_description(scope, f"{row_count} unit production record(s)")

    return EvidencePanel(
        title="Unit Production",
        description=f"Units produced per player for {description}",
        df=df,
    )


def _city_unit_production_evidence(
    conn: object, scope: dict[str, list], sql_filters: _SqlFilters
) -> EvidencePanel | None:
    """Show per-city unit production records."""
    where_clause, params = _build_where_clause(scope)

    where_clause, params = _append_filter_conditions(
        where_clause, params, "cup.unit_type", sql_filters.unit_types
    )

    query = f"""
        SELECT
            m.game_name AS match,
            COALESCE(tp.display_name, p.player_name) AS player_name,
            c.city_name,
            cup.unit_type,
            cup.count
        FROM city_unit_production cup
        JOIN cities c ON cup.match_id = c.match_id AND cup.city_id = c.city_id
        JOIN matches m ON cup.match_id = m.match_id
        JOIN players p ON c.match_id = p.match_id AND c.player_id = p.player_id
        LEFT JOIN tournament_participants tp ON p.participant_id = tp.participant_id
        {where_clause}
        ORDER BY m.match_id, player_name, c.city_name, cup.count DESC
        LIMIT {_EVIDENCE_ROW_LIMIT}
    """

    df = conn.execute(query, params).df()
    if df.empty:
        return None

    row_count = len(df)
    description = _scope_description(scope, f"{row_count} city production record(s)")

    return EvidencePanel(
        title="City Unit Production",
        description=f"Units produced per city for {description}",
        df=df,
    )


def _scope_description(scope: dict[str, list], fallback: str) -> str:
    """Build a human-readable description of the scope."""
    parts: list[str] = []

    if "player_names" in scope and scope["player_names"]:
        names = scope["player_names"]
        if len(names) <= 3:
            parts.append(", ".join(names))
        else:
            parts.append(f"{len(names)} players")

    if "civilizations" in scope and scope["civilizations"]:
        civs = scope["civilizations"]
        if len(civs) <= 3:
            parts.append(", ".join(civs))
        else:
            parts.append(f"{len(civs)} civilizations")

    if parts:
        return " / ".join(parts) + f" — {fallback}"
    return fallback
