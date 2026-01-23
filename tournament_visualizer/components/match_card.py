"""Match Card data processing and analysis for at-a-glance match overview.

This module provides functions to analyze match data and extract key insights
for the Match Card "Overview (Beta)" tab.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Length classification thresholds (turns)
LENGTH_SHORT = 60
LENGTH_MEDIUM = 100
LENGTH_LONG = 140

# Phase thresholds for decisive moment detection
PHASE_EARLY = 40
PHASE_MID = 80

# Expansion thresholds
EXPANSION_FAST_TURN = 30
EXPANSION_BALANCED_TURN = 50
EXPANSION_MILESTONE_5 = 5
EXPANSION_MILESTONE_10 = 10

# Playstyle thresholds
WONDERS_THRESHOLD = 3
TECH_LEAD_THRESHOLD = 5
MILITARY_GROWTH_AGGRESSIVE = 0.05  # 5% per turn
MILITARY_GROWTH_DEFENSIVE = 0.03  # 3% per turn

# World religions (vs pagan religions)
WORLD_RELIGIONS = {"Christianity", "Judaism", "Manichaeism", "Zoroastrianism"}

# Archetype names
ARCHETYPE_EARLY_RUSH = "Early Military Rush"
ARCHETYPE_WONDER_RACE = "Wonder Race"
ARCHETYPE_ECONOMIC = "Economic Domination"
ARCHETYPE_COMEBACK = "Comeback Victory"
ARCHETYPE_LATE_GRIND = "Late-game Grind"
ARCHETYPE_RELIGIOUS = "Religious Control"
ARCHETYPE_BALANCED = "Balanced Contest"


# =============================================================================
# VP Lead Analysis
# =============================================================================


def analyze_vp_lead(
    points_df: pd.DataFrame,
    player_ids: tuple[int, int],
) -> dict[str, Any]:
    """Analyze VP lead patterns throughout the match.

    Args:
        points_df: DataFrame from get_points_history_by_match()
        player_ids: Tuple of (player1_id, player2_id)

    Returns:
        Dict with sparkline_data, max leads, lead changes, permanent lead turn
    """
    if points_df.empty:
        return {
            "sparkline_data": [],
            "max_p1_lead": 0,
            "max_p1_lead_turn": 0,
            "max_p2_lead": 0,
            "max_p2_lead_turn": 0,
            "first_lead_change_turn": None,
            "total_lead_changes": 0,
            "permanent_lead_turn": None,
        }

    p1_id, p2_id = player_ids

    # Pivot to get each player's points per turn
    pivot = points_df.pivot_table(
        index="turn_number",
        columns="player_id",
        values="points",
        aggfunc="first",
    ).fillna(0)

    # Ensure both players have columns
    if p1_id not in pivot.columns:
        pivot[p1_id] = 0
    if p2_id not in pivot.columns:
        pivot[p2_id] = 0

    # Calculate lead (positive = P1 ahead, negative = P2 ahead)
    pivot["lead"] = pivot[p1_id] - pivot[p2_id]
    pivot = pivot.reset_index()

    # Build sparkline data
    sparkline_data = list(zip(pivot["turn_number"], pivot["lead"]))

    # Find max leads
    max_p1_lead = pivot["lead"].max()
    max_p1_lead_turn = (
        int(pivot.loc[pivot["lead"].idxmax(), "turn_number"])
        if max_p1_lead > 0
        else 0
    )

    max_p2_lead = abs(pivot["lead"].min())
    max_p2_lead_turn = (
        int(pivot.loc[pivot["lead"].idxmin(), "turn_number"])
        if max_p2_lead > 0
        else 0
    )

    # Track lead changes (sign changes)
    pivot["sign"] = pivot["lead"].apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    pivot["sign_change"] = pivot["sign"].diff().abs() > 0

    lead_changes = pivot["sign_change"].sum()
    first_lead_change_idx = pivot[pivot["sign_change"]].index
    first_lead_change_turn = (
        int(pivot.loc[first_lead_change_idx[0], "turn_number"])
        if len(first_lead_change_idx) > 0
        else None
    )

    # Find permanent lead turn (last turn where lead changed and never reverted)
    permanent_lead_turn = None
    if len(pivot) > 0:
        final_sign = pivot["sign"].iloc[-1]
        if final_sign != 0:
            # Walk backwards to find when this lead was established
            for i in range(len(pivot) - 1, -1, -1):
                if pivot["sign"].iloc[i] != final_sign:
                    if i + 1 < len(pivot):
                        permanent_lead_turn = int(pivot["turn_number"].iloc[i + 1])
                    break
            else:
                # Leader was ahead from the start
                permanent_lead_turn = int(pivot["turn_number"].iloc[0])

    return {
        "sparkline_data": sparkline_data,
        "max_p1_lead": int(max_p1_lead) if max_p1_lead > 0 else 0,
        "max_p1_lead_turn": max_p1_lead_turn,
        "max_p2_lead": int(max_p2_lead) if max_p2_lead > 0 else 0,
        "max_p2_lead_turn": max_p2_lead_turn,
        "first_lead_change_turn": first_lead_change_turn,
        "total_lead_changes": int(lead_changes),
        "permanent_lead_turn": permanent_lead_turn,
    }


# =============================================================================
# Territory Tempo Analysis
# =============================================================================


def analyze_territory_tempo(
    cities_df: pd.DataFrame,
    expansion_df: pd.DataFrame,
    player_ids: tuple[int, int],
) -> dict[str, Any]:
    """Analyze city expansion patterns for each player.

    Args:
        cities_df: DataFrame from get_match_cities()
        expansion_df: DataFrame from get_player_expansion_stats()
        player_ids: Tuple of (player1_id, player2_id)

    Returns:
        Dict with city counts, milestone turns, and expansion classifications
    """
    p1_id, p2_id = player_ids

    result = {
        "p1_final_cities": 0,
        "p2_final_cities": 0,
        "p1_first_to_5": None,
        "p2_first_to_5": None,
        "p1_first_to_10": None,
        "p2_first_to_10": None,
        "expansion_class_p1": "Balanced",
        "expansion_class_p2": "Balanced",
    }

    if cities_df.empty:
        return result

    # Get final city counts from expansion_df
    if not expansion_df.empty:
        for _, row in expansion_df.iterrows():
            pid = row["player_id"]
            count = row.get("total_cities", 0)
            if pid == p1_id:
                result["p1_final_cities"] = int(count)
            elif pid == p2_id:
                result["p2_final_cities"] = int(count)

    # Calculate milestone turns from cities_df
    for pid, prefix in [(p1_id, "p1"), (p2_id, "p2")]:
        player_cities = cities_df[cities_df["player_id"] == pid].copy()
        if player_cities.empty:
            continue

        # Sort by founding turn
        player_cities = player_cities.sort_values("founded_turn")
        turns = player_cities["founded_turn"].tolist()

        # First to 5 cities
        if len(turns) >= EXPANSION_MILESTONE_5:
            result[f"{prefix}_first_to_5"] = int(turns[EXPANSION_MILESTONE_5 - 1])

        # First to 10 cities
        if len(turns) >= EXPANSION_MILESTONE_10:
            result[f"{prefix}_first_to_10"] = int(turns[EXPANSION_MILESTONE_10 - 1])

        # Classify expansion style
        first_5_turn = result[f"{prefix}_first_to_5"]
        total_cities = result[f"{prefix}_final_cities"]

        if total_cities < EXPANSION_MILESTONE_5:
            result[f"expansion_class_{prefix}"] = "Tall"
        elif first_5_turn is not None:
            if first_5_turn < EXPANSION_FAST_TURN:
                result[f"expansion_class_{prefix}"] = "Fast"
            elif first_5_turn <= EXPANSION_BALANCED_TURN:
                result[f"expansion_class_{prefix}"] = "Balanced"
            else:
                result[f"expansion_class_{prefix}"] = "Tall"

    return result


# =============================================================================
# Key Events Extraction
# =============================================================================

# Thresholds for key event detection
LEAD_THRESHOLD = 0.5  # 50% lead required
BATTLE_DROP_THRESHOLD = 0.3  # 30% military drop
BATTLE_WINDOW = 3  # 3-turn window for battle detection
LAW_MILESTONE_4 = 4
LAW_MILESTONE_7 = 7


def extract_key_events(
    events_df: pd.DataFrame,
    military_df: pd.DataFrame,
    law_df: pd.DataFrame,
    yield_df: pd.DataFrame,
    player_ids: tuple[int, int],
    total_turns: int,
) -> list[dict[str, Any]]:
    """Extract key events from the match.

    Args:
        events_df: DataFrame from get_match_timeline_events()
        military_df: DataFrame from get_military_history_by_match()
        law_df: DataFrame from get_law_timeline()
        yield_df: DataFrame from get_yield_history_by_match()
        player_ids: Tuple of (player1_id, player2_id)
        total_turns: Total turns in the match

    Returns:
        List of key events sorted chronologically by turn
    """
    key_events: list[dict[str, Any]] = []

    # 1. All City Captures
    key_events.extend(_extract_city_captures(events_df))

    # 2. Law Milestones (4th and 7th law)
    key_events.extend(_find_law_milestones(law_df, player_ids))

    # 3. Science Lead Established (50% cumulative lead, once per player)
    key_events.extend(
        _find_science_lead_milestones(yield_df, player_ids, LEAD_THRESHOLD)
    )

    # 4. Military Lead Established (50% power lead, once per player)
    key_events.extend(
        _find_military_lead_milestones(military_df, player_ids, LEAD_THRESHOLD)
    )

    # 5. Major Battles (30% total military drop over 3 turns)
    key_events.extend(
        _find_major_battles(military_df, BATTLE_DROP_THRESHOLD, BATTLE_WINDOW)
    )

    # Sort chronologically by turn
    key_events.sort(key=lambda x: x["turn"])
    return key_events


def _extract_city_captures(events_df: pd.DataFrame) -> list[dict[str, Any]]:
    """Extract all city capture events."""
    if events_df.empty:
        return []

    city_lost_events = events_df[events_df["event_type"] == "city_lost"]
    events = []

    for _, event in city_lost_events.iterrows():
        events.append(
            {
                "turn": int(event["turn"]),
                "player_id": int(event["player_id"]),
                "event_type": "city_lost",
                "title": event["title"],
                "icon": "",
                "priority": 50,
            }
        )

    return events


def _find_law_milestones(
    law_df: pd.DataFrame,
    player_ids: tuple[int, int],
) -> list[dict[str, Any]]:
    """Find turns when each player reaches 4th and 7th law."""
    if law_df.empty:
        return []

    events = []

    for player_id in player_ids:
        player_laws = law_df[law_df["player_id"] == player_id].sort_values(
            "turn_number"
        )

        # 4th law milestone
        if len(player_laws) >= LAW_MILESTONE_4:
            events.append(
                {
                    "turn": int(player_laws.iloc[LAW_MILESTONE_4 - 1]["turn_number"]),
                    "player_id": int(player_id),
                    "event_type": "law_milestone",
                    "title": "4th law",
                    "icon": "",
                    "priority": 50,
                }
            )

        # 7th law milestone
        if len(player_laws) >= LAW_MILESTONE_7:
            events.append(
                {
                    "turn": int(player_laws.iloc[LAW_MILESTONE_7 - 1]["turn_number"]),
                    "player_id": int(player_id),
                    "event_type": "law_milestone",
                    "title": "7th law",
                    "icon": "",
                    "priority": 50,
                }
            )

    return events


def _find_science_lead_milestones(
    yield_df: pd.DataFrame,
    player_ids: tuple[int, int],
    threshold: float,
) -> list[dict[str, Any]]:
    """Find first turn each player achieves threshold cumulative science lead.

    Args:
        yield_df: DataFrame from get_yield_history_by_match()
        player_ids: Tuple of (player1_id, player2_id)
        threshold: Lead threshold (0.5 = 50% more than opponent)

    Returns:
        List of science lead events (at most one per player)
    """
    if yield_df.empty:
        return []

    # Filter to science yields only
    science_df = yield_df[yield_df["resource_type"] == "YIELD_SCIENCE"]
    if science_df.empty:
        return []

    p1_id, p2_id = player_ids

    # Pivot by turn and player
    pivot = science_df.pivot_table(
        index="turn_number",
        columns="player_id",
        values="amount",
        aggfunc="sum",
    ).fillna(0)

    # Ensure both players have columns
    if p1_id not in pivot.columns:
        pivot[p1_id] = 0
    if p2_id not in pivot.columns:
        pivot[p2_id] = 0

    # Calculate cumulative sums
    pivot[f"{p1_id}_cumsum"] = pivot[p1_id].cumsum()
    pivot[f"{p2_id}_cumsum"] = pivot[p2_id].cumsum()

    events = []
    found_lead = {p1_id: False, p2_id: False}

    for turn in pivot.index:
        p1_cum = pivot.loc[turn, f"{p1_id}_cumsum"]
        p2_cum = pivot.loc[turn, f"{p2_id}_cumsum"]

        # Check if P1 has threshold lead over P2
        if not found_lead[p1_id] and p2_cum > 0:
            if (p1_cum - p2_cum) / p2_cum >= threshold:
                events.append(
                    {
                        "turn": int(turn),
                        "player_id": int(p1_id),
                        "event_type": "science_lead",
                        "title": "Science lead",
                        "icon": "",
                        "priority": 50,
                    }
                )
                found_lead[p1_id] = True

        # Check if P2 has threshold lead over P1
        if not found_lead[p2_id] and p1_cum > 0:
            if (p2_cum - p1_cum) / p1_cum >= threshold:
                events.append(
                    {
                        "turn": int(turn),
                        "player_id": int(p2_id),
                        "event_type": "science_lead",
                        "title": "Science lead",
                        "icon": "",
                        "priority": 50,
                    }
                )
                found_lead[p2_id] = True

        # Stop early if both players have achieved leads at some point
        if found_lead[p1_id] and found_lead[p2_id]:
            break

    return events


def _find_military_lead_milestones(
    military_df: pd.DataFrame,
    player_ids: tuple[int, int],
    threshold: float,
) -> list[dict[str, Any]]:
    """Find first turn each player achieves threshold military power lead.

    Args:
        military_df: DataFrame from get_military_history_by_match()
        player_ids: Tuple of (player1_id, player2_id)
        threshold: Lead threshold (0.5 = 50% more than opponent)

    Returns:
        List of military lead events (at most one per player)
    """
    if military_df.empty:
        return []

    p1_id, p2_id = player_ids

    # Pivot by turn and player
    pivot = military_df.pivot_table(
        index="turn_number",
        columns="player_id",
        values="military_power",
        aggfunc="first",
    ).fillna(0)

    # Ensure both players have columns
    if p1_id not in pivot.columns:
        pivot[p1_id] = 0
    if p2_id not in pivot.columns:
        pivot[p2_id] = 0

    events = []
    found_lead = {p1_id: False, p2_id: False}

    for turn in pivot.index:
        p1_power = pivot.loc[turn, p1_id]
        p2_power = pivot.loc[turn, p2_id]

        # Check if P1 has threshold lead over P2
        if not found_lead[p1_id] and p2_power > 0:
            if (p1_power - p2_power) / p2_power >= threshold:
                events.append(
                    {
                        "turn": int(turn),
                        "player_id": int(p1_id),
                        "event_type": "military_lead",
                        "title": "Military lead",
                        "icon": "",
                        "priority": 50,
                    }
                )
                found_lead[p1_id] = True

        # Check if P2 has threshold lead over P1
        if not found_lead[p2_id] and p1_power > 0:
            if (p2_power - p1_power) / p1_power >= threshold:
                events.append(
                    {
                        "turn": int(turn),
                        "player_id": int(p2_id),
                        "event_type": "military_lead",
                        "title": "Military lead",
                        "icon": "",
                        "priority": 50,
                    }
                )
                found_lead[p2_id] = True

        # Stop early if both players have achieved leads
        if found_lead[p1_id] and found_lead[p2_id]:
            break

    return events


def _find_major_battles(
    military_df: pd.DataFrame,
    threshold: float,
    window: int,
) -> list[dict[str, Any]]:
    """Find turns where total military drops significantly over a window.

    A major battle is detected when the combined military power of both players
    drops by threshold (e.g., 30%) over window turns (e.g., 3 turns).

    Args:
        military_df: DataFrame from get_military_history_by_match()
        threshold: Drop threshold (0.3 = 30% drop)
        window: Number of turns to look back

    Returns:
        List of major battle events
    """
    if military_df.empty:
        return []

    # Calculate total military per turn (sum of both players)
    total_by_turn = military_df.groupby("turn_number")["military_power"].sum()

    if len(total_by_turn) < window + 1:
        return []

    events = []
    turns = sorted(total_by_turn.index)

    for i, turn in enumerate(turns):
        if i < window:
            continue

        # Look back 'window' turns
        prev_turn = turns[i - window]
        prev_total = total_by_turn[prev_turn]
        curr_total = total_by_turn[turn]

        if prev_total <= 0:
            continue

        drop_pct = (prev_total - curr_total) / prev_total

        if drop_pct >= threshold:
            # Use the middle of the window as the battle turn
            battle_turn = turns[i - window // 2]
            events.append(
                {
                    "turn": int(battle_turn),
                    "player_id": None,  # Battle involves both players
                    "event_type": "major_battle",
                    "title": "Major battle",
                    "icon": "",
                    "priority": 50,
                }
            )

    # Deduplicate battles that are too close together (within window turns)
    if len(events) <= 1:
        return events

    deduped = [events[0]]
    for event in events[1:]:
        if event["turn"] - deduped[-1]["turn"] >= window:
            deduped.append(event)

    return deduped


# =============================================================================
# Empire Profile Generation
# =============================================================================


def generate_empire_profile(
    player_id: int,
    player_name: str,
    civilization: str,
    events_df: pd.DataFrame,
    yield_df: pd.DataFrame,
    units_df: pd.DataFrame,
    cities_df: pd.DataFrame,
    military_df: pd.DataFrame,
    expansion_class: str,
    captured_cities: int,
    lost_cities: int,
    total_turns: int,
) -> dict[str, Any]:
    """Generate a comprehensive profile for a player.

    Args:
        player_id: Player's database ID
        player_name: Player's display name
        civilization: Civilization played
        events_df: DataFrame from get_match_timeline_events()
        yield_df: DataFrame from get_yield_history_by_match()
        units_df: DataFrame from get_match_units_produced()
        cities_df: DataFrame from get_match_cities()
        military_df: DataFrame from get_military_history_by_match()
        expansion_class: "Fast", "Balanced", or "Tall"
        captured_cities: Number of cities captured by this player
        lost_cities: Number of cities lost by this player
        total_turns: Total turns in the match

    Returns:
        Dict with playstyle_tags, army_composition, wonders_built
    """
    playstyle_tags = {}

    # Expansion tag (already computed)
    playstyle_tags["expansion"] = expansion_class

    # Military posture
    playstyle_tags["military"] = _classify_military_posture(
        player_id, military_df, captured_cities, lost_cities, total_turns
    )

    # Economy focus
    playstyle_tags["economy"] = _classify_economy_focus(player_id, yield_df)

    # Identity tag
    playstyle_tags["identity"] = _classify_identity(player_id, events_df)

    # Army composition
    army_composition = _calculate_army_composition(player_id, units_df)

    # Count wonders
    wonders_built = 0
    if not events_df.empty:
        player_wonders = events_df[
            (events_df["player_id"] == player_id)
            & (events_df["event_type"] == "wonder_complete")
        ]
        wonders_built = len(player_wonders)

    return {
        "player_id": player_id,
        "player_name": player_name,
        "civilization": civilization,
        "playstyle_tags": playstyle_tags,
        "army_composition": army_composition,
        "wonders_built": wonders_built,
    }


def _classify_military_posture(
    player_id: int,
    military_df: pd.DataFrame,
    captured_cities: int,
    lost_cities: int,
    total_turns: int,
) -> str:
    """Classify military posture as Aggressive, Defensive, or Passive."""
    if military_df.empty or total_turns == 0:
        return "Passive"

    player_military = military_df[military_df["player_id"] == player_id]
    if player_military.empty:
        return "Passive"

    # Calculate military growth rate
    first_power = player_military["military_power"].iloc[0]
    last_power = player_military["military_power"].iloc[-1]
    growth_rate = (last_power - first_power) / total_turns / max(first_power, 1)

    if captured_cities > 0 and growth_rate > MILITARY_GROWTH_AGGRESSIVE:
        return "Aggressive"
    elif (
        captured_cities == 0
        and lost_cities == 0
        and growth_rate < MILITARY_GROWTH_DEFENSIVE
    ):
        return "Defensive"
    else:
        return "Passive"


def _classify_economy_focus(player_id: int, yield_df: pd.DataFrame) -> str:
    """Classify economy focus based on cumulative yields."""
    if yield_df.empty:
        return "Balanced"

    player_yields = yield_df[yield_df["player_id"] == player_id]
    if player_yields.empty:
        return "Balanced"

    # Sum up key yield types
    totals = {}
    for yield_type in ["YIELD_SCIENCE", "YIELD_TRAINING", "YIELD_MONEY"]:
        type_df = player_yields[player_yields["resource_type"] == yield_type]
        totals[yield_type] = type_df["amount"].sum() if not type_df.empty else 0

    if not totals:
        return "Balanced"

    # Find dominant yield
    max_yield = max(totals.items(), key=lambda x: x[1])

    # Check if significantly dominant (at least 20% more than second)
    sorted_totals = sorted(totals.values(), reverse=True)
    if len(sorted_totals) >= 2 and sorted_totals[0] > 0:
        dominance = (sorted_totals[0] - sorted_totals[1]) / sorted_totals[0]
        if dominance < 0.2:
            return "Balanced"

    if max_yield[0] == "YIELD_SCIENCE":
        return "Science-focused"
    elif max_yield[0] == "YIELD_TRAINING":
        return "Training-focused"
    elif max_yield[0] == "YIELD_MONEY":
        return "Money-focused"

    return "Balanced"


def _classify_identity(player_id: int, events_df: pd.DataFrame) -> str | None:
    """Classify player identity based on achievements."""
    if events_df.empty:
        return None

    player_events = events_df[events_df["player_id"] == player_id]
    if player_events.empty:
        return None

    # Count wonders
    wonders = len(player_events[player_events["event_type"] == "wonder_complete"])
    if wonders >= WONDERS_THRESHOLD:
        return "Wonder Builder"

    # Check for world religion founding
    religion_events = player_events[player_events["event_type"] == "religion"]
    for _, rel in religion_events.iterrows():
        title = rel["title"]
        if any(wr.lower() in title.lower() for wr in WORLD_RELIGIONS):
            return "Religious"

    return None


def _calculate_army_composition(
    player_id: int, units_df: pd.DataFrame
) -> dict[str, float]:
    """Calculate army composition percentages by role."""
    default = {
        "Infantry": 0.0,
        "Ranged": 0.0,
        "Cavalry": 0.0,
        "Siege": 0.0,
        "Naval": 0.0,
        "Support": 0.0,
    }

    if units_df.empty:
        return default

    player_units = units_df[units_df["player_id"] == player_id]
    if player_units.empty:
        return default

    # Group by role
    role_counts = player_units.groupby("role")["count"].sum()
    total = role_counts.sum()

    if total == 0:
        return default

    # Map roles to our categories
    role_mapping = {
        "infantry": "Infantry",
        "melee": "Infantry",
        "ranged": "Ranged",
        "cavalry": "Cavalry",
        "mounted": "Cavalry",
        "siege": "Siege",
        "naval": "Naval",
        "ship": "Naval",
        "support": "Support",
        "religious": "Support",
        "civilian": "Support",
    }

    composition = default.copy()
    for role, count in role_counts.items():
        if role is None:
            continue
        role_lower = str(role).lower()
        category = role_mapping.get(role_lower, "Support")
        composition[category] += count / total

    return composition


# =============================================================================
# Laws, Religion, Wonders Summary
# =============================================================================


def summarize_laws_religion_wonders(
    events_df: pd.DataFrame,
    law_df: pd.DataFrame,
    player_ids: tuple[int, int],
    player_names: tuple[str, str],
) -> dict[str, Any]:
    """Summarize laws, religion, and wonders for both players.

    Args:
        events_df: DataFrame from get_match_timeline_events()
        law_df: DataFrame from get_law_timeline()
        player_ids: Tuple of (player1_id, player2_id)
        player_names: Tuple of (player1_name, player2_name)

    Returns:
        Dict with laws, religions, and wonders summaries
    """
    p1_id, p2_id = player_ids
    p1_name, p2_name = player_names

    result = {
        "laws": {
            p1_name: {"total": 0, "swaps": 0, "style": "Stable"},
            p2_name: {"total": 0, "swaps": 0, "style": "Stable"},
        },
        "religions": {p1_name: [], p2_name: []},
        "wonders": {
            p1_name: {"count": 0, "list": []},
            p2_name: {"count": 0, "list": []},
        },
    }

    # Laws from law_df
    if not law_df.empty:
        for pid, pname in [(p1_id, p1_name), (p2_id, p2_name)]:
            player_laws = law_df[law_df["player_id"] == pid]
            total = len(player_laws)
            result["laws"][pname]["total"] = total

    # Laws swaps from events_df
    if not events_df.empty:
        for pid, pname in [(p1_id, p1_name), (p2_id, p2_name)]:
            swap_events = events_df[
                (events_df["player_id"] == pid)
                & (events_df["event_type"] == "law_swap")
            ]
            swaps = len(swap_events)
            result["laws"][pname]["swaps"] = swaps
            result["laws"][pname]["style"] = "Cycling" if swaps >= 2 else "Stable"

    # Religions from events_df
    if not events_df.empty:
        religion_events = events_df[events_df["event_type"] == "religion"]
        for pid, pname in [(p1_id, p1_name), (p2_id, p2_name)]:
            player_religions = religion_events[religion_events["player_id"] == pid]
            for _, rel in player_religions.iterrows():
                # Strip "Founded: " prefix from religion name
                title = rel["title"]
                if title.startswith("Founded: "):
                    title = title[9:]  # len("Founded: ") == 9
                result["religions"][pname].append(title)

    # Wonders from events_df
    if not events_df.empty:
        wonder_events = events_df[events_df["event_type"] == "wonder_complete"]
        for pid, pname in [(p1_id, p1_name), (p2_id, p2_name)]:
            player_wonders = wonder_events[wonder_events["player_id"] == pid]
            result["wonders"][pname]["count"] = len(player_wonders)
            result["wonders"][pname]["list"] = player_wonders["title"].tolist()[:5]

    return result


# =============================================================================
# Highlight Reel
# =============================================================================


def generate_highlight_reel(
    events_df: pd.DataFrame,
    military_df: pd.DataFrame,
    cities_df: pd.DataFrame,
    winner_player_id: int | None,
    player_ids: tuple[int, int],
    total_turns: int,
) -> dict[str, Any]:
    """Generate highlight reel with MVP city, pivotal battle, signature tech.

    Args:
        events_df: DataFrame from get_match_timeline_events()
        military_df: DataFrame from get_military_history_by_match()
        cities_df: DataFrame from get_match_cities()
        winner_player_id: ID of the winning player
        player_ids: Tuple of (player1_id, player2_id)
        total_turns: Total turns in the match

    Returns:
        Dict with mvp_city, pivotal_battle, signature_tech
    """
    result = {
        "mvp_city": None,
        "pivotal_battle": None,
        "signature_tech": None,
    }

    # MVP City: city with most wonders
    if not events_df.empty and not cities_df.empty:
        wonder_events = events_df[events_df["event_type"] == "wonder_complete"]
        if not wonder_events.empty:
            # Try to match wonders to cities (this is approximate)
            # For now, just find the winning player's capital or first city
            if winner_player_id:
                winner_cities = cities_df[cities_df["player_id"] == winner_player_id]
                if not winner_cities.empty:
                    # Prefer capital
                    capitals = winner_cities[winner_cities["is_capital"]]
                    if not capitals.empty:
                        city = capitals.iloc[0]
                    else:
                        city = winner_cities.iloc[0]

                    winner_wonders = len(
                        wonder_events[wonder_events["player_id"] == winner_player_id]
                    )
                    result["mvp_city"] = {
                        "name": _clean_city_name(city["city_name"]),
                        "wonders": winner_wonders,
                        "player_id": winner_player_id,
                    }

    # Pivotal Battle: first major battle (30% military drop over 3 turns)
    major_battles = _find_major_battles(
        military_df, BATTLE_DROP_THRESHOLD, BATTLE_WINDOW
    )
    if major_battles:
        result["pivotal_battle"] = major_battles[0]

    # Signature Tech: first tech where winner was 5+ turns ahead
    if not events_df.empty and winner_player_id:
        result["signature_tech"] = _find_signature_tech(
            events_df, winner_player_id, player_ids
        )

    return result


def _find_signature_tech(
    events_df: pd.DataFrame,
    winner_player_id: int,
    player_ids: tuple[int, int],
) -> dict[str, Any] | None:
    """Find first tech where winner was significantly ahead."""
    tech_events = events_df[events_df["event_type"] == "tech"]
    if tech_events.empty:
        return None

    p1_id, p2_id = player_ids
    loser_id = p2_id if winner_player_id == p1_id else p1_id

    winner_techs = tech_events[tech_events["player_id"] == winner_player_id]
    loser_techs = tech_events[tech_events["player_id"] == loser_id]

    if winner_techs.empty:
        return None

    # Build dict of tech -> turn for loser
    loser_tech_turns = {}
    for _, row in loser_techs.iterrows():
        tech_name = row["title"]
        loser_tech_turns[tech_name] = row["turn"]

    # Find first tech where winner was 5+ turns ahead
    for _, row in winner_techs.iterrows():
        tech_name = row["title"]
        winner_turn = row["turn"]
        loser_turn = loser_tech_turns.get(tech_name)

        if loser_turn is None:
            # Loser never got this tech, check if game ended
            continue

        if loser_turn - winner_turn >= TECH_LEAD_THRESHOLD:
            return {
                "tech_name": tech_name,
                "winner_turn": int(winner_turn),
                "loser_turn": int(loser_turn),
                "lead": int(loser_turn - winner_turn),
            }

    return None


def _clean_city_name(city_name: str) -> str:
    """Clean city name for display (remove CITYNAME_ prefix)."""
    if city_name and city_name.startswith("CITYNAME_"):
        name = city_name.replace("CITYNAME_", "")
        return name.replace("_", " ").title()
    return city_name or "Unknown"


# =============================================================================
# Match Archetype Classification
# =============================================================================


def classify_match_archetype(
    points_df: pd.DataFrame,
    military_df: pd.DataFrame,
    events_df: pd.DataFrame,
    yield_df: pd.DataFrame,
    total_turns: int,
    winner_player_id: int | None,
    winner_name: str,
    player_ids: tuple[int, int],
    vp_analysis: dict[str, Any],
) -> dict[str, Any]:
    """Classify the match archetype and generate win story.

    Args:
        points_df: DataFrame from get_points_history_by_match()
        military_df: DataFrame from get_military_history_by_match()
        events_df: DataFrame from get_match_timeline_events()
        yield_df: DataFrame from get_yield_history_by_match()
        total_turns: Total turns in the match
        winner_player_id: ID of the winning player
        winner_name: Name of the winning player
        player_ids: Tuple of (player1_id, player2_id)
        vp_analysis: Result from analyze_vp_lead()

    Returns:
        Dict with archetype, length_class, decisive_phase, win_story
    """
    # Length classification
    if total_turns <= LENGTH_SHORT:
        length_class = "Short"
    elif total_turns <= LENGTH_MEDIUM:
        length_class = "Medium"
    elif total_turns <= LENGTH_LONG:
        length_class = "Long"
    else:
        length_class = "Very Long"

    # Decisive phase
    permanent_lead_turn = vp_analysis.get("permanent_lead_turn")
    if permanent_lead_turn is None:
        decisive_phase = "late"
    elif permanent_lead_turn < PHASE_EARLY:
        decisive_phase = "early"
    elif permanent_lead_turn < PHASE_MID:
        decisive_phase = "mid"
    else:
        decisive_phase = "late"

    # Archetype detection
    archetype = ARCHETYPE_BALANCED
    primary_factor = "balanced play"
    key_differentiator = "no single dominant factor"

    p1_id, p2_id = player_ids
    loser_id = p2_id if winner_player_id == p1_id else p1_id

    # Check each archetype condition in order
    if not events_df.empty:
        # 1. Early Military Rush
        city_capture = events_df[
            (events_df["event_type"] == "city_lost")
            & (events_df["turn"] < 50)
            & (events_df["player_id"] == loser_id)
        ]
        if not city_capture.empty:
            archetype = ARCHETYPE_EARLY_RUSH
            primary_factor = "early aggression"
            capture_turn = int(city_capture.iloc[0]["turn"])
            key_differentiator = f"captured city turn {capture_turn}"
        else:
            # 2. Wonder Race
            winner_wonders = len(
                events_df[
                    (events_df["player_id"] == winner_player_id)
                    & (events_df["event_type"] == "wonder_complete")
                ]
            )
            loser_wonders = len(
                events_df[
                    (events_df["player_id"] == loser_id)
                    & (events_df["event_type"] == "wonder_complete")
                ]
            )
            wonder_diff = winner_wonders - loser_wonders

            if wonder_diff >= 4:
                archetype = ARCHETYPE_WONDER_RACE
                primary_factor = "wonder building"
                key_differentiator = f"{winner_wonders} wonders vs {loser_wonders}"
            else:
                # 3. Economic Domination
                econ_result = _check_economic_domination(
                    yield_df, winner_player_id, loser_id
                )
                if econ_result:
                    archetype = ARCHETYPE_ECONOMIC
                    primary_factor = econ_result["factor"]
                    key_differentiator = econ_result["detail"]
                else:
                    # 4. Comeback Victory
                    if _check_comeback(vp_analysis):
                        archetype = ARCHETYPE_COMEBACK
                        primary_factor = "comeback"
                        key_differentiator = f"took lead turn {permanent_lead_turn}"
                    # 5. Late-game Grind
                    elif (
                        total_turns > 100 and vp_analysis["total_lead_changes"] > 5
                    ):
                        archetype = ARCHETYPE_LATE_GRIND
                        primary_factor = "persistence"
                        lead_changes = vp_analysis["total_lead_changes"]
                        key_differentiator = f"{lead_changes} lead changes"
                    # 6. Religious Control
                    elif _check_religious_control(
                        events_df, winner_player_id, loser_id
                    ):
                        archetype = ARCHETYPE_RELIGIOUS
                        primary_factor = "religious control"
                        key_differentiator = "founded world religion"

    # Generate win story
    win_story = f"{winner_name} wins via {primary_factor} ({key_differentiator})"

    return {
        "archetype": archetype,
        "length_class": length_class,
        "decisive_phase": decisive_phase,
        "win_story": win_story,
    }


def _check_economic_domination(
    yield_df: pd.DataFrame,
    winner_id: int,
    loser_id: int,
) -> dict[str, str] | None:
    """Check if winner had >50% cumulative advantage in key yields."""
    if yield_df.empty:
        return None

    for yield_type, yield_name in [
        ("YIELD_SCIENCE", "science"),
        ("YIELD_TRAINING", "training"),
    ]:
        type_df = yield_df[yield_df["resource_type"] == yield_type]
        if type_df.empty:
            continue

        winner_total = type_df[type_df["player_id"] == winner_id]["amount"].sum()
        loser_total = type_df[type_df["player_id"] == loser_id]["amount"].sum()

        if loser_total > 0:
            advantage = (winner_total - loser_total) / loser_total
            if advantage > 0.5:
                return {
                    "factor": f"superior {yield_name}",
                    "detail": f"{int(winner_total)} vs {int(loser_total)} cumulative",
                }

    return None


def _check_comeback(vp_analysis: dict[str, Any]) -> bool:
    """Check if winner was behind for >60% of turns."""
    sparkline_data = vp_analysis.get("sparkline_data", [])
    if not sparkline_data:
        return False

    # Determine final lead direction
    final_lead = sparkline_data[-1][1] if sparkline_data else 0
    winner_positive = final_lead > 0

    # Count turns winner was behind
    turns_behind = sum(
        1 for _, lead in sparkline_data if (lead < 0) == winner_positive
    )
    total_turns = len(sparkline_data)

    return total_turns > 0 and turns_behind / total_turns > 0.6


def _check_religious_control(
    events_df: pd.DataFrame,
    winner_id: int,
    loser_id: int,
) -> bool:
    """Check if winner founded a world religion that loser never adopted."""
    religion_events = events_df[events_df["event_type"] == "religion"]
    if religion_events.empty:
        return False

    # Check if winner founded a world religion
    winner_religions = religion_events[religion_events["player_id"] == winner_id]
    for _, rel in winner_religions.iterrows():
        title = rel["title"]
        if any(wr.lower() in title.lower() for wr in WORLD_RELIGIONS):
            return True

    return False


# =============================================================================
# Yield Comparison Analysis
# =============================================================================


def analyze_yield_comparison(
    yield_df: pd.DataFrame,
    points_df: pd.DataFrame,
    player_ids: tuple[int, int],
) -> dict[str, Any]:
    """Calculate cumulative yield totals for comparison charts.

    Args:
        yield_df: DataFrame from get_yield_history_by_match()
        points_df: DataFrame from get_points_history_by_match()
        player_ids: Tuple of (player1_id, player2_id)

    Returns:
        Dict with yield comparison data for each metric
    """
    p1_id, p2_id = player_ids

    # Metrics to compare (display_name, yield_type or special)
    metrics = [
        ("Training", "YIELD_TRAINING"),
        ("Science", "YIELD_SCIENCE"),
        ("Civics", "YIELD_CIVICS"),
        ("Orders", "YIELD_ORDERS"),
    ]

    result = {}

    # Calculate cumulative totals for each yield type
    for display_name, yield_type in metrics:
        p1_total = 0.0
        p2_total = 0.0

        if not yield_df.empty:
            yield_data = yield_df[yield_df["resource_type"] == yield_type]
            p1_data = yield_data[yield_data["player_id"] == p1_id]
            p2_data = yield_data[yield_data["player_id"] == p2_id]

            p1_total = p1_data["amount"].sum() if not p1_data.empty else 0.0
            p2_total = p2_data["amount"].sum() if not p2_data.empty else 0.0

        result[display_name.lower()] = {
            "p1_total": p1_total,
            "p2_total": p2_total,
            "display_name": display_name,
        }

    # Victory Points - use final points from points_df
    p1_vp = 0
    p2_vp = 0
    if not points_df.empty:
        # Get max turn for each player
        p1_points = points_df[points_df["player_id"] == p1_id]
        p2_points = points_df[points_df["player_id"] == p2_id]

        if not p1_points.empty:
            max_turn_p1 = p1_points["turn_number"].max()
            p1_vp = p1_points[p1_points["turn_number"] == max_turn_p1]["points"].iloc[0]
        if not p2_points.empty:
            max_turn_p2 = p2_points["turn_number"].max()
            p2_vp = p2_points[p2_points["turn_number"] == max_turn_p2]["points"].iloc[0]

    result["victory_points"] = {
        "p1_total": float(p1_vp),
        "p2_total": float(p2_vp),
        "display_name": "Victory Points",
    }

    return result


# =============================================================================
# Main Analysis Orchestrator
# =============================================================================


def analyze_match(
    match_id: int,
    points_df: pd.DataFrame,
    military_df: pd.DataFrame,
    events_df: pd.DataFrame,
    yield_df: pd.DataFrame,
    cities_df: pd.DataFrame,
    expansion_df: pd.DataFrame,
    units_df: pd.DataFrame,
    law_df: pd.DataFrame,
    total_turns: int,
    winner_player_id: int | None,
    winner_name: str,
    player_ids: tuple[int, int],
    player_names: tuple[str, str],
    civilizations: tuple[str, str],
) -> dict[str, Any]:
    """Run all match analyses and return combined results.

    This is the main entry point for match card data generation.

    Args:
        match_id: Match database ID
        points_df: DataFrame from get_points_history_by_match()
        military_df: DataFrame from get_military_history_by_match()
        events_df: DataFrame from get_match_timeline_events()
        yield_df: DataFrame from get_yield_history_by_match()
        cities_df: DataFrame from get_match_cities()
        expansion_df: DataFrame from get_player_expansion_stats()
        units_df: DataFrame from get_match_units_produced()
        law_df: DataFrame from get_law_timeline()
        total_turns: Total turns in the match
        winner_player_id: ID of the winning player
        winner_name: Name of the winning player
        player_ids: Tuple of (player1_id, player2_id)
        player_names: Tuple of (player1_name, player2_name)
        civilizations: Tuple of (player1_civ, player2_civ)

    Returns:
        Dict with all analysis results
    """
    p1_id, p2_id = player_ids
    p1_name, p2_name = player_names
    p1_civ, p2_civ = civilizations

    # VP Lead Analysis
    vp_analysis = analyze_vp_lead(points_df, player_ids)

    # Territory Tempo Analysis
    territory_analysis = analyze_territory_tempo(cities_df, expansion_df, player_ids)

    # Count captured/lost cities
    p1_captured = 0
    p2_captured = 0
    p1_lost = 0
    p2_lost = 0
    if not events_df.empty:
        city_lost = events_df[events_df["event_type"] == "city_lost"]
        p1_lost = len(city_lost[city_lost["player_id"] == p1_id])
        p2_lost = len(city_lost[city_lost["player_id"] == p2_id])
        p1_captured = p2_lost  # If P2 lost, P1 captured
        p2_captured = p1_lost

    # Empire Profiles
    p1_profile = generate_empire_profile(
        player_id=p1_id,
        player_name=p1_name,
        civilization=p1_civ,
        events_df=events_df,
        yield_df=yield_df,
        units_df=units_df,
        cities_df=cities_df,
        military_df=military_df,
        expansion_class=territory_analysis["expansion_class_p1"],
        captured_cities=p1_captured,
        lost_cities=p1_lost,
        total_turns=total_turns,
    )

    p2_profile = generate_empire_profile(
        player_id=p2_id,
        player_name=p2_name,
        civilization=p2_civ,
        events_df=events_df,
        yield_df=yield_df,
        units_df=units_df,
        cities_df=cities_df,
        military_df=military_df,
        expansion_class=territory_analysis["expansion_class_p2"],
        captured_cities=p2_captured,
        lost_cities=p2_lost,
        total_turns=total_turns,
    )

    # Key Events
    key_events = extract_key_events(
        events_df=events_df,
        military_df=military_df,
        law_df=law_df,
        yield_df=yield_df,
        player_ids=player_ids,
        total_turns=total_turns,
    )

    # Summary
    summary = summarize_laws_religion_wonders(
        events_df, law_df, player_ids, player_names
    )

    # Highlight Reel
    highlights = generate_highlight_reel(
        events_df, military_df, cities_df, winner_player_id, player_ids, total_turns
    )

    # Archetype Classification
    archetype_info = classify_match_archetype(
        points_df=points_df,
        military_df=military_df,
        events_df=events_df,
        yield_df=yield_df,
        total_turns=total_turns,
        winner_player_id=winner_player_id,
        winner_name=winner_name,
        player_ids=player_ids,
        vp_analysis=vp_analysis,
    )

    # Yield Comparison
    yield_comparison = analyze_yield_comparison(yield_df, points_df, player_ids)

    return {
        "match_id": match_id,
        "total_turns": total_turns,
        "winner_player_id": winner_player_id,
        "winner_name": winner_name,
        "player_ids": player_ids,
        "player_names": player_names,
        "civilizations": civilizations,
        "vp_analysis": vp_analysis,
        "territory_analysis": territory_analysis,
        "p1_profile": p1_profile,
        "p2_profile": p2_profile,
        "key_events": key_events,
        "summary": summary,
        "highlights": highlights,
        "archetype_info": archetype_info,
        "yield_comparison": yield_comparison,
    }
