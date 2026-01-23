"""Match Card UI components for at-a-glance match overview.

This module provides layout components for the Match Card "Overview (Beta)" tab.
"""

from __future__ import annotations

import logging
from typing import Any

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import dcc, html

from tournament_visualizer.components.layouts import create_empty_state
from tournament_visualizer.data.game_constants import get_nation_crest_icon_path

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Badge colors by category
BADGE_COLORS = {
    # Expansion
    "Fast": "success",
    "Balanced": "info",
    "Tall": "secondary",
    # Military
    "Aggressive": "danger",
    "Defensive": "warning",
    "Passive": "secondary",
    # Economy
    "Science-focused": "primary",
    "Training-focused": "danger",
    "Money-focused": "warning",
    # Identity
    "Wonder Builder": "info",
    "Religious": "purple",
    "Tech Leader": "primary",
}

# Archetype badge colors
ARCHETYPE_COLORS = {
    "Early Military Rush": "danger",
    "Wonder Race": "info",
    "Economic Domination": "success",
    "Comeback Victory": "warning",
    "Late-game Grind": "secondary",
    "Religious Control": "purple",
    "Balanced Contest": "primary",
}

# Army composition colors
ARMY_COLORS = {
    "Infantry": "#4dabf7",
    "Ranged": "#69db7c",
    "Cavalry": "#ffd43b",
    "Siege": "#ff8787",
    "Naval": "#748ffc",
    "Support": "#868e96",
}

# Chart theme colors
CHART_BG = "#1a1a1a"
CHART_PAPER = "#2d3748"
CHART_GRID = "#4a5568"
CHART_TEXT = "#e2e8f0"
CHART_MUTED = "#a0aec0"


# =============================================================================
# Match Card Header
# =============================================================================


def create_match_card_header(
    archetype: str,
    length_class: str,
    decisive_phase: str,
    total_turns: int,
    win_story: str,
) -> dbc.Card:
    """Create the match card header with archetype, length, and win story.

    Args:
        archetype: Match archetype classification
        length_class: "Short", "Medium", "Long", or "Very Long"
        decisive_phase: "early", "mid", or "late"
        total_turns: Total turns in the match
        win_story: One-sentence win summary

    Returns:
        dbc.Card component
    """
    badge_color = ARCHETYPE_COLORS.get(archetype, "primary")

    return dbc.Card(
        dbc.CardBody(
            [
                # Archetype badge
                html.Div(
                    [
                        dbc.Badge(
                            archetype,
                            color=badge_color,
                            className="fs-6 me-2",
                        ),
                        html.Span(
                            f"{length_class} ({total_turns} turns) - "
                            f"lead from {decisive_phase} game",
                            className="text-muted",
                        ),
                    ],
                    className="mb-2",
                ),
                # Win story
                html.P(
                    win_story,
                    className="mb-0 fs-5",
                    style={"fontStyle": "italic"},
                ),
            ]
        ),
        className="mb-3",
    )


# =============================================================================
# VP Sparkline
# =============================================================================


def create_vp_sparkline(
    sparkline_data: list[tuple[int, int]],
    p1_color: str,
    p2_color: str,
    p1_name: str,
    p2_name: str,
    height: int = 100,
) -> dcc.Graph:
    """Create a small VP lead sparkline chart.

    Args:
        sparkline_data: List of (turn, lead) tuples where positive = P1 ahead
        p1_color: Hex color for player 1
        p2_color: Hex color for player 2
        p1_name: Player 1's name
        p2_name: Player 2's name
        height: Chart height in pixels

    Returns:
        dcc.Graph component
    """
    if not sparkline_data:
        return create_empty_state("No VP history available")

    turns = [d[0] for d in sparkline_data]
    leads = [d[1] for d in sparkline_data]

    # Separate positive and negative for dual coloring
    pos_leads = [max(0, lead) for lead in leads]
    neg_leads = [min(0, lead) for lead in leads]

    fig = go.Figure()

    # Positive area (P1 ahead)
    fig.add_trace(
        go.Scatter(
            x=turns,
            y=pos_leads,
            fill="tozeroy",
            fillcolor=f"rgba({_hex_to_rgb(p1_color)}, 0.4)",
            line=dict(color=p1_color, width=1),
            name=f"{p1_name} leads",
            hovertemplate="Turn %{x}: +%{y} VP<extra></extra>",
        )
    )

    # Negative area (P2 ahead)
    fig.add_trace(
        go.Scatter(
            x=turns,
            y=neg_leads,
            fill="tozeroy",
            fillcolor=f"rgba({_hex_to_rgb(p2_color)}, 0.4)",
            line=dict(color=p2_color, width=1),
            name=f"{p2_name} leads",
            hovertemplate="Turn %{x}: %{y} VP<extra></extra>",
        )
    )

    # Zero line
    fig.add_hline(y=0, line_dash="dash", line_color=CHART_MUTED, line_width=1)

    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=10, b=25),
        paper_bgcolor=CHART_PAPER,
        plot_bgcolor=CHART_BG,
        showlegend=False,
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            color=CHART_TEXT,
            title=None,
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            color=CHART_TEXT,
            title=None,
        ),
        hovermode="x unified",
    )

    return dcc.Graph(
        figure=fig,
        config={"displayModeBar": False},
        style={"height": f"{height}px"},
    )


def _hex_to_rgb(hex_color: str) -> str:
    """Convert hex color to RGB string for rgba()."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"{r}, {g}, {b}"


# =============================================================================
# Lead Stats Card
# =============================================================================


def create_lead_stats_card(
    vp_analysis: dict[str, Any],
    p1_name: str,
    p2_name: str,
    p1_color: str,
    p2_color: str,
) -> dbc.Card:
    """Create the VP lead card with sparkline and stats.

    Args:
        vp_analysis: Result from analyze_vp_lead()
        p1_name: Player 1's name
        p2_name: Player 2's name
        p1_color: Player 1's color
        p2_color: Player 2's color

    Returns:
        dbc.Card component
    """
    sparkline = create_vp_sparkline(
        vp_analysis.get("sparkline_data", []),
        p1_color,
        p2_color,
        p1_name,
        p2_name,
    )

    # Stats row
    stats = [
        _create_stat_item(
            f"Max {p1_name} lead",
            f"+{vp_analysis['max_p1_lead']} (T{vp_analysis['max_p1_lead_turn']})",
            p1_color,
        ),
        _create_stat_item(
            f"Max {p2_name} lead",
            f"+{vp_analysis['max_p2_lead']} (T{vp_analysis['max_p2_lead_turn']})",
            p2_color,
        ),
        _create_stat_item(
            "Lead changes",
            str(vp_analysis["total_lead_changes"]),
        ),
    ]

    if vp_analysis["permanent_lead_turn"]:
        stats.append(
            _create_stat_item(
                "Permanent lead",
                f"Turn {vp_analysis['permanent_lead_turn']}",
            )
        )

    return dbc.Card(
        [
            dbc.CardHeader("VP Lead Progression"),
            dbc.CardBody(
                [
                    sparkline,
                    html.Hr(className="my-2"),
                    html.Div(stats, className="d-flex flex-wrap gap-3"),
                ]
            ),
        ],
        className="h-100",
    )


def _create_stat_item(
    label: str,
    value: str,
    color: str | None = None,
) -> html.Div:
    """Create a single stat item."""
    value_style = {"color": color} if color else {}
    return html.Div(
        [
            html.Small(label, className="text-muted d-block"),
            html.Span(value, className="fw-bold", style=value_style),
        ]
    )


# =============================================================================
# Territory Card
# =============================================================================


def create_territory_card(
    territory_analysis: dict[str, Any],
    p1_name: str,
    p2_name: str,
    p1_color: str,
    p2_color: str,
) -> dbc.Card:
    """Create the territory tempo card with city counts and expansion badges.

    Args:
        territory_analysis: Result from analyze_territory_tempo()
        p1_name: Player 1's name
        p2_name: Player 2's name
        p1_color: Player 1's color
        p2_color: Player 2's color

    Returns:
        dbc.Card component
    """
    p1_cities = territory_analysis["p1_final_cities"]
    p2_cities = territory_analysis["p2_final_cities"]

    text_color = "#eef2f7"

    # City count comparison
    city_comparison = html.Div(
        [
            html.Span(p1_name, className="me-1", style={"color": text_color}),
            html.Span(
                str(p1_cities),
                className="fw-bold",
                style={"color": text_color},
            ),
            html.Span(" cities ", className="mx-2", style={"color": text_color}),
            html.Span(
                str(p2_cities),
                className="fw-bold",
                style={"color": text_color},
            ),
            html.Span(p2_name, className="ms-1", style={"color": text_color}),
        ],
        className="d-flex justify-content-center align-items-center mb-3",
    )

    # Milestones
    milestones = []
    for prefix, pname, pcolor in [("p1", p1_name, p1_color), ("p2", p2_name, p2_color)]:
        first_5 = territory_analysis.get(f"{prefix}_first_to_5")
        first_10 = territory_analysis.get(f"{prefix}_first_to_10")
        expansion_class = territory_analysis.get(
            f"expansion_class_{prefix}", "Balanced"
        )

        player_milestones = html.Div(
            [
                html.Div(
                    [
                        html.Span(pname, style={"color": text_color}),
                        html.Span(": ", style={"color": text_color}),
                        dbc.Badge(
                            expansion_class,
                            color=BADGE_COLORS.get(expansion_class, "secondary"),
                            className="ms-1",
                        ),
                    ],
                    className="mb-1",
                ),
                html.Small(
                    [
                        f"5 cities: T{first_5}" if first_5 else "5 cities: —",
                        " | ",
                        f"10 cities: T{first_10}" if first_10 else "10 cities: —",
                    ],
                    style={"color": text_color},
                ),
            ],
            className="mb-2",
        )
        milestones.append(player_milestones)

    return dbc.Card(
        [
            dbc.CardHeader("Territory & Expansion"),
            dbc.CardBody([city_comparison, html.Hr(className="my-2")] + milestones),
        ],
        className="h-100",
    )


# =============================================================================
# Key Events Box
# =============================================================================


def create_key_events_box(
    events: list[dict[str, Any]],
    player_names: dict[int, str],
    civilizations: dict[int, str],
) -> dbc.Card:
    """Create the key events box showing top 5 pivotal moments.

    Args:
        events: List of key event dicts with turn, type, title, player_id
        player_names: Dict mapping player_id to player name
        civilizations: Dict mapping player_id to civilization name

    Returns:
        dbc.Card component
    """
    if not events:
        return dbc.Card(
            [
                dbc.CardHeader("Key Events"),
                dbc.CardBody(create_empty_state("No key events detected")),
            ],
            className="h-100",
        )

    # Sort events by turn (not by player)
    sorted_events = sorted(events, key=lambda x: x.get("turn", 0))

    event_rows = []
    for event in sorted_events:
        turn = event.get("turn", 0)
        title = event.get("title", "Unknown event")
        event_type = event.get("event_type", "")
        player_id = event.get("player_id")
        icon = _get_event_icon(event_type)

        # Get player name (empty string if no player)
        if player_id is not None:
            player_name = player_names.get(player_id, "Unknown")
        else:
            player_name = ""

        row = html.Div(
            [
                html.Span(
                    str(turn),
                    className="text-muted",
                    style={"minWidth": "30px", "fontSize": "14px"},
                ),
                html.Span(
                    player_name,
                    style={
                        "minWidth": "100px",
                        "fontSize": "14px",
                        "color": "#eef2f7",
                    },
                ),
                html.Span(icon, className="me-1", style={"fontSize": "14px"}),
                html.Span(
                    title,
                    style={"color": "#eef2f7", "fontSize": "14px"},
                ),
            ],
            className="d-flex align-items-center py-1",
        )
        event_rows.append(row)

    return dbc.Card(
        [
            dbc.CardHeader("Key Events"),
            dbc.CardBody(event_rows),
        ],
        className="h-100",
    )


def _get_event_icon(event_type: str) -> str:
    """Get emoji icon for event type."""
    icons = {
        "wonder_complete": "",
        "wonder_start": "",
        "city_lost": "",
        "city": "",
        "religion": "",
        "permanent_lead": "",
        "military_swing": "",
        "tech": "",
        "law": "",
        "law_milestone": "",
        "science_lead": "",
        "military_lead": "",
        "major_battle": "",
    }
    return icons.get(event_type, "")


# =============================================================================
# Empire Profile Card
# =============================================================================


def create_empire_profile_card(
    profile: dict[str, Any],
    player_color: str,
    religions: list[str],
    law_count: int,
    law_swaps: int,
    city_count: int,
) -> dbc.Card:
    """Create an empire profile card for a player.

    Args:
        profile: Result from generate_empire_profile()
        player_color: Player's color
        religions: List of religions founded by this player
        law_count: Number of laws enacted
        law_swaps: Number of law swaps
        city_count: Number of cities

    Returns:
        dbc.Card component
    """
    text_color = "#eef2f7"
    player_id = profile.get("player_id", 0)
    player_name = profile.get("player_name", "Unknown")
    civilization = profile.get("civilization", "Unknown")
    playstyle_tags = profile.get("playstyle_tags", {})
    army_composition = profile.get("army_composition", {})
    wonders_built = profile.get("wonders_built", 0)

    # Header with crest and name
    crest_path = get_nation_crest_icon_path(civilization)
    header = html.Div(
        [
            _create_colored_crest(crest_path, player_color, "24px"),
            html.Span(player_name, className="ms-2 fs-5 fw-bold"),
            html.Span(f"({civilization})", className="text-muted ms-1"),
        ],
        className="d-flex align-items-center mb-3",
    )

    # Playstyle badges
    badges = create_playstyle_badges(playstyle_tags, player_id)

    # Army composition bar
    army_bar = create_army_composition_bar(army_composition)

    # Quick stats (aligned label and value columns)
    if law_swaps > 0:
        swap_word = "swap" if law_swaps == 1 else "swaps"
        laws_value = f"{law_count}, {law_swaps} {swap_word}"
    else:
        laws_value = str(law_count)

    stat_style = {"fontSize": "14px", "color": text_color}
    label_style = {"minWidth": "70px", "fontSize": "14px", "color": text_color}

    def stat_row(label: str, value: str) -> html.Div:
        return html.Div(
            [
                html.Span(label, style=label_style),
                html.Span(value, style=stat_style),
            ],
            className="d-flex",
        )

    stats_lines = [
        stat_row("Cities", str(city_count)),
        stat_row("Wonders", str(wonders_built)),
        stat_row("Laws", laws_value),
    ]
    if religions:
        religion_str = ", ".join(religions)
        stats_lines.append(stat_row("Religions", religion_str))

    stats = html.Div(stats_lines, className="mt-2")

    return dbc.Card(
        dbc.CardBody([header, badges, html.Hr(className="my-2"), army_bar, stats]),
        className="h-100",
    )


def _create_colored_crest(
    crest_path: str,
    color: str,
    size: str = "16px",
) -> html.Div:
    """Create a nation crest icon tinted with the nation's color."""
    return html.Div(
        style={
            "width": size,
            "height": size,
            "backgroundColor": color,
            "maskImage": f"url({crest_path})",
            "WebkitMaskImage": f"url({crest_path})",
            "maskSize": "contain",
            "WebkitMaskSize": "contain",
            "maskRepeat": "no-repeat",
            "WebkitMaskRepeat": "no-repeat",
            "maskPosition": "center",
            "WebkitMaskPosition": "center",
            "display": "inline-block",
            "verticalAlign": "middle",
        }
    )


# =============================================================================
# Playstyle Badges
# =============================================================================


def create_playstyle_badges(tags: dict[str, str], player_id: int) -> html.Div:
    """Create playstyle badge components with tooltips.

    Args:
        tags: Dict with expansion, military, economy, identity keys
        player_id: Unique player ID for generating unique element IDs

    Returns:
        html.Div with badges
    """
    # Tooltips explaining how each badge is determined (keyed by category:value)
    badge_tooltips = {
        # Expansion
        "expansion:Fast": "Reached 5 cities before turn 30",
        "expansion:Balanced": "Reached 5 cities between turns 30-50",
        "expansion:Tall": "Reached 5 cities after turn 50, or fewer than 5 total",
        # Military
        "military:Aggressive": "Captured cities and high military growth rate",
        "military:Defensive": "No captures, low military growth, no cities lost",
        "military:Passive": "Minimal military activity",
        # Economy
        "economy:Science-focused": "Science was the highest cumulative yield",
        "economy:Training-focused": "Training was the highest cumulative yield",
        "economy:Money-focused": "Money was the highest cumulative yield",
        "economy:Balanced": "No single yield dominated",
        # Identity
        "identity:Wonder Builder": "Built 3 or more wonders",
        "identity:Religious": "Founded a world religion",
        "identity:Tech Leader": "Reached final tech 10+ turns ahead",
    }

    badges = []

    # Order: expansion, military, economy, identity
    for category, label in [
        ("expansion", "Expansion"),
        ("military", "Military"),
        ("economy", "Economy"),
        ("identity", "Identity"),
    ]:
        value = tags.get(category)
        if value:
            color = BADGE_COLORS.get(value, "secondary")
            tooltip_text = badge_tooltips.get(f"{category}:{value}", "")

            badge_id = f"badge-p{player_id}-{category}-{value.lower().replace(' ', '-')}"
            badge = dbc.Badge(
                [
                    html.Small(f"{label}: ", className="fw-normal"),
                    value,
                ],
                color=color,
                className="me-1 mb-1",
                id=badge_id,
            )

            if tooltip_text:
                badges.append(
                    html.Span(
                        [
                            badge,
                            dbc.Tooltip(
                                tooltip_text,
                                target=badge_id,
                                placement="top",
                            ),
                        ]
                    )
                )
            else:
                badges.append(badge)

    return html.Div(badges, className="d-flex flex-wrap")


# =============================================================================
# Army Composition Bar
# =============================================================================


def create_army_composition_bar(
    composition: dict[str, float],
    height: int = 24,
) -> html.Div:
    """Create a horizontal stacked bar showing army composition.

    Args:
        composition: Dict mapping role to percentage (0-1)
        height: Bar height in pixels

    Returns:
        html.Div with stacked bar
    """
    # Filter out zero values and sort by percentage
    non_zero = {k: v for k, v in composition.items() if v > 0.01}
    if not non_zero:
        return html.Div(
            html.Small("No military units", className="text-muted"),
        )

    # Build bar segments
    segments = []
    for role, pct in sorted(non_zero.items(), key=lambda x: -x[1]):
        color = ARMY_COLORS.get(role, CHART_MUTED)
        width_pct = pct * 100

        # Use full name if segment is wide enough, otherwise abbreviate
        if width_pct > 25:
            label = f"{role} {int(pct*100)}%"
        else:
            label = f"{role[:3]} {int(pct*100)}%"

        segment = html.Div(
            html.Span(
                label,
                style={
                    "fontSize": "0.65rem",
                    "whiteSpace": "nowrap",
                    "overflow": "hidden",
                },
            )
            if width_pct > 10
            else None,
            style={
                "width": f"{width_pct}%",
                "height": f"{height}px",
                "backgroundColor": color,
                "display": "inline-flex",
                "alignItems": "center",
                "justifyContent": "center",
                "color": "#fff",
            },
            title=f"{role}: {int(pct*100)}%",
        )
        segments.append(segment)

    return html.Div(
        [
            html.Small("Army Composition", className="text-muted d-block mb-1"),
            html.Div(
                segments,
                style={
                    "display": "flex",
                    "borderRadius": "4px",
                    "overflow": "hidden",
                },
            ),
        ]
    )


# =============================================================================
# Summary Cards (Religion, Laws, Wonders)
# =============================================================================


def create_summary_cards(
    summary: dict[str, Any],
    player_names: tuple[str, str],
    player_colors: tuple[str, str],
) -> dbc.Row:
    """Create the three summary cards for religion, laws, and wonders.

    Args:
        summary: Result from summarize_laws_religion_wonders()
        player_names: Tuple of (player1_name, player2_name)
        player_colors: Tuple of (player1_color, player2_color)

    Returns:
        dbc.Row with three cards
    """
    p1_name, p2_name = player_names
    text_color = "#eef2f7"

    # Religion card
    religion_content = []
    for pname in [p1_name, p2_name]:
        religions = summary["religions"].get(pname, [])
        religion_content.append(
            html.Div(
                [
                    html.Span(f"{pname}: ", style={"color": text_color}),
                    html.Span(
                        ", ".join(religions) if religions else "None",
                        style={"color": text_color},
                    ),
                ],
                className="mb-1",
            )
        )

    religion_card = dbc.Card(
        [
            dbc.CardHeader("Religion"),
            dbc.CardBody(religion_content),
        ],
        className="h-100",
    )

    # Laws card
    laws_content = []
    for pname in [p1_name, p2_name]:
        law_info = summary["laws"].get(pname, {})
        total = law_info.get("total", 0)
        swaps = law_info.get("swaps", 0)

        laws_content.append(
            html.Div(
                html.Span(
                    f"{pname}: {total} laws, {swaps} swaps",
                    style={"color": text_color},
                ),
                className="mb-1",
            )
        )

    laws_card = dbc.Card(
        [
            dbc.CardHeader("Laws"),
            dbc.CardBody(laws_content),
        ],
        className="h-100",
    )

    # Wonders card
    wonders_content = []
    for pname in [p1_name, p2_name]:
        wonder_info = summary["wonders"].get(pname, {})
        count = wonder_info.get("count", 0)
        wonder_list = wonder_info.get("list", [])
        # Clean wonder names
        clean_names = [_clean_wonder_name(w) for w in wonder_list[:3]]

        wonder_text = f"{pname}: {count}"
        if clean_names:
            wonder_text += f" ({', '.join(clean_names)})"

        wonders_content.append(
            html.Div(
                html.Span(wonder_text, style={"color": text_color}),
                className="mb-1",
            )
        )

    wonders_card = dbc.Card(
        [
            dbc.CardHeader("Wonders"),
            dbc.CardBody(wonders_content),
        ],
        className="h-100",
    )

    return dbc.Row(
        [
            dbc.Col(religion_card, width=4),
            dbc.Col(laws_card, width=4),
            dbc.Col(wonders_card, width=4),
        ],
        className="mb-3 g-3",
    )


def _clean_wonder_name(title: str) -> str:
    """Extract clean wonder name from title."""
    # Title format is often "Completed: Wonder Name"
    if ":" in title:
        return title.split(":")[-1].strip()
    return title


# =============================================================================
# Yield Comparison Charts
# =============================================================================


def create_yield_comparison_card(
    yield_comparison: dict[str, Any],
    p1_name: str,
    p2_name: str,
    p1_color: str,
    p2_color: str,
) -> dbc.Card:
    """Create small comparison charts for key metrics.

    Args:
        yield_comparison: Result from analyze_yield_comparison()
        p1_name: Player 1's name
        p2_name: Player 2's name
        p1_color: Player 1's color
        p2_color: Player 2's color

    Returns:
        dbc.Card component with comparison charts
    """
    text_color = "#eef2f7"

    # Order of metrics to display
    metric_order = ["victory_points", "training", "science", "civics", "orders"]

    charts = []
    for metric_key in metric_order:
        if metric_key not in yield_comparison:
            continue

        metric_data = yield_comparison[metric_key]
        p1_val = metric_data["p1_total"]
        p2_val = metric_data["p2_total"]
        display_name = metric_data["display_name"]

        # Create a mini butterfly bar chart
        charts.append(
            _create_mini_comparison_bar(
                display_name, p1_val, p2_val, p1_name, p2_name, p1_color, p2_color
            )
        )

    if not charts:
        return dbc.Card(
            [
                dbc.CardHeader("Key Metrics"),
                dbc.CardBody(
                    html.Small("No data available", style={"color": text_color})
                ),
            ],
            className="h-100",
        )

    return dbc.Card(
        [
            dbc.CardHeader("Key Metrics"),
            dbc.CardBody(charts),
        ],
        className="h-100",
    )


def _get_contrasting_text_color(bg_color: str) -> str:
    """Return black or white text color based on background luminance."""
    # Parse hex color
    color = bg_color.lstrip("#")
    if len(color) == 3:
        color = "".join(c * 2 for c in color)

    try:
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
    except (ValueError, IndexError):
        return "#fff"  # Default to white

    # Calculate relative luminance (per WCAG)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255

    # Use dark text on light backgrounds
    return "#1a1a2e" if luminance > 0.5 else "#fff"


def _create_mini_comparison_bar(
    label: str,
    p1_val: float,
    p2_val: float,
    p1_name: str,
    p2_name: str,
    p1_color: str,
    p2_color: str,
) -> html.Div:
    """Create a single mini comparison bar.

    Shows label on top, then a horizontal bar comparing the two values.
    """
    text_color = "#eef2f7"
    max_val = max(p1_val, p2_val, 1)  # Avoid division by zero

    # Calculate percentages for bar widths
    p1_pct = (p1_val / max_val) * 100
    p2_pct = (p2_val / max_val) * 100

    # Get contrasting text colors for each bar
    p1_text = _get_contrasting_text_color(p1_color)
    p2_text = _get_contrasting_text_color(p2_color)

    # Format values for display (integers, with k suffix for thousands)
    def format_val(v: float) -> str:
        v_int = int(round(v))
        if v_int >= 10000:
            return f"{v_int // 1000}k"
        elif v_int >= 1000:
            return f"{v_int / 1000:.1f}k"
        else:
            return str(v_int)

    return html.Div(
        [
            # Label
            html.Div(
                label,
                style={
                    "color": text_color,
                    "fontSize": "0.75rem",
                    "fontWeight": "500",
                    "marginBottom": "2px",
                },
            ),
            # Bars container
            html.Div(
                [
                    # P1 bar (left)
                    html.Div(
                        [
                            html.Div(
                                format_val(p1_val),
                                style={
                                    "position": "absolute",
                                    "left": "4px",
                                    "top": "50%",
                                    "transform": "translateY(-50%)",
                                    "fontSize": "0.65rem",
                                    "color": p1_text,
                                    "fontWeight": "bold",
                                },
                            )
                            if p1_pct > 20
                            else None,
                        ],
                        style={
                            "width": f"{p1_pct}%",
                            "backgroundColor": p1_color,
                            "height": "16px",
                            "borderRadius": "2px 0 0 2px",
                            "position": "relative",
                            "minWidth": "2px" if p1_val > 0 else "0",
                        },
                    ),
                    # Divider
                    html.Div(
                        style={
                            "width": "2px",
                            "backgroundColor": "#3b4c69",
                            "height": "16px",
                            "flexShrink": "0",
                        },
                    ),
                    # P2 bar (right)
                    html.Div(
                        [
                            html.Div(
                                format_val(p2_val),
                                style={
                                    "position": "absolute",
                                    "right": "4px",
                                    "top": "50%",
                                    "transform": "translateY(-50%)",
                                    "fontSize": "0.65rem",
                                    "color": p2_text,
                                    "fontWeight": "bold",
                                },
                            )
                            if p2_pct > 20
                            else None,
                        ],
                        style={
                            "width": f"{p2_pct}%",
                            "backgroundColor": p2_color,
                            "height": "16px",
                            "borderRadius": "0 2px 2px 0",
                            "position": "relative",
                            "minWidth": "2px" if p2_val > 0 else "0",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "width": "100%",
                    "backgroundColor": "rgba(255,255,255,0.1)",
                    "borderRadius": "2px",
                },
            ),
        ],
        className="mb-2",
    )


# =============================================================================
# Highlight Reel
# =============================================================================


def create_highlight_reel(
    highlights: dict[str, Any],
    player_names: dict[int, str],
) -> dbc.Card:
    """Create the highlight reel card with MVP city and pivotal battle.

    Args:
        highlights: Result from generate_highlight_reel()
        player_names: Dict mapping player_id to name

    Returns:
        dbc.Card component
    """
    items = []

    # MVP City
    mvp_city = highlights.get("mvp_city")
    if mvp_city:
        pname = player_names.get(mvp_city.get("player_id"), "Unknown")
        items.append(
            _create_highlight_item(
                "",
                "MVP City",
                f"{mvp_city['name']} ({pname}) - {mvp_city['wonders']} wonders",
            )
        )

    # Pivotal Battle
    battle = highlights.get("pivotal_battle")
    if battle:
        pname = player_names.get(battle.get("player_id"), "Unknown")
        items.append(
            _create_highlight_item(
                "",
                "Pivotal Moment",
                f"Turn {battle['turn']}: {pname} gained "
                f"{battle['magnitude']} military power",
            )
        )

    if not items:
        return dbc.Card(
            [
                dbc.CardHeader("Highlight Reel"),
                dbc.CardBody(
                    html.Small("No highlights detected", className="text-muted")
                ),
            ]
        )

    return dbc.Card(
        [
            dbc.CardHeader("Highlight Reel"),
            dbc.CardBody(items),
        ],
    )


def _create_highlight_item(
    icon: str,
    label: str,
    description: str,
) -> html.Div:
    """Create a single highlight item."""
    text_color = "#eef2f7"
    return html.Div(
        [
            html.Span(icon, className="me-2", style={"fontSize": "1.2rem"}),
            html.Span(label, className="fw-bold me-2", style={"color": text_color}),
            html.Span(description, style={"color": text_color}),
        ],
        className="mb-2",
    )


# =============================================================================
# Main Layout Assembly
# =============================================================================


def create_match_card_layout(analysis: dict[str, Any]) -> html.Div:
    """Assemble the complete match card layout from analysis results.

    Args:
        analysis: Complete analysis result from analyze_match()

    Returns:
        html.Div with full layout
    """
    # Extract data
    archetype_info = analysis.get("archetype_info", {})
    vp_analysis = analysis.get("vp_analysis", {})
    territory_analysis = analysis.get("territory_analysis", {})
    key_events = analysis.get("key_events", [])
    p1_profile = analysis.get("p1_profile", {})
    p2_profile = analysis.get("p2_profile", {})
    summary = analysis.get("summary", {})
    highlights = analysis.get("highlights", {})
    yield_comparison = analysis.get("yield_comparison", {})

    player_names = analysis.get("player_names", ("Player 1", "Player 2"))
    civilizations = analysis.get("civilizations", ("Unknown", "Unknown"))
    player_ids = analysis.get("player_ids", (1, 2))
    total_turns = analysis.get("total_turns", 0)

    p1_name, p2_name = player_names
    p1_civ, p2_civ = civilizations
    p1_id, p2_id = player_ids

    # Get player colors
    from tournament_visualizer.nation_colors import get_match_player_colors

    p1_color, p2_color = get_match_player_colors(p1_civ, p2_civ)

    player_colors = {p1_id: p1_color, p2_id: p2_color}
    player_names_dict = {p1_id: p1_name, p2_id: p2_name}
    civilizations_dict = {p1_id: p1_civ, p2_id: p2_civ}

    # Extract summary data for each player
    p1_religions = summary.get("religions", {}).get(p1_name, [])
    p2_religions = summary.get("religions", {}).get(p2_name, [])
    p1_laws = summary.get("laws", {}).get(p1_name, {"total": 0, "swaps": 0})
    p2_laws = summary.get("laws", {}).get(p2_name, {"total": 0, "swaps": 0})

    # Get city counts from territory analysis
    p1_cities = territory_analysis.get("p1_final_cities", 0)
    p2_cities = territory_analysis.get("p2_final_cities", 0)

    # Build layout
    return html.Div(
        [
            # Empire Profiles Row
            dbc.Row(
                [
                    dbc.Col(
                        create_empire_profile_card(
                            p1_profile,
                            p1_color,
                            p1_religions,
                            p1_laws["total"],
                            p1_laws["swaps"],
                            p1_cities,
                        ),
                        width=6,
                    ),
                    dbc.Col(
                        create_empire_profile_card(
                            p2_profile,
                            p2_color,
                            p2_religions,
                            p2_laws["total"],
                            p2_laws["swaps"],
                            p2_cities,
                        ),
                        width=6,
                    ),
                ],
                className="mb-3 g-3",
            ),
            # Key Events and Key Metrics Row
            dbc.Row(
                [
                    dbc.Col(
                        create_key_events_box(
                            key_events, player_names_dict, civilizations_dict
                        ),
                        width=4,
                    ),
                    dbc.Col(
                        create_yield_comparison_card(
                            yield_comparison, p1_name, p2_name, p1_color, p2_color
                        ),
                        width=8,
                    ),
                ],
                className="mb-3 g-3",
            ),
            # Reference Panel (collapsible)
            create_reference_panel(),
        ]
    )


def create_reference_panel() -> dbc.Accordion:
    """Create an expandable reference panel explaining labels and metrics."""
    text_color = "#eef2f7"
    muted_color = "#a0aec0"

    def ref_item(term: str, definition: str) -> html.Div:
        return html.Div(
            [
                html.Span(term, style={"fontWeight": "bold", "color": text_color}),
                html.Span(" - ", style={"color": muted_color}),
                html.Span(definition, style={"color": muted_color}),
            ],
            className="mb-1",
        )

    expansion_refs = html.Div(
        [
            ref_item("Fast", "Reached 5 cities before turn 30"),
            ref_item("Balanced", "Reached 5 cities between turns 30-50"),
            ref_item("Tall", "Reached 5 cities after turn 50, or fewer than 5 total"),
        ]
    )

    military_refs = html.Div(
        [
            ref_item("Aggressive", "Captured at least 1 city and military growth >5%/turn"),
            ref_item("Defensive", "No captures or losses and military growth <3%/turn"),
            ref_item("Passive", "Neither aggressive nor defensive"),
        ]
    )

    economy_refs = html.Div(
        [
            ref_item("Science-focused", "Cumulative science at least 20% higher than next yield"),
            ref_item("Training-focused", "Cumulative training at least 20% higher than next yield"),
            ref_item("Money-focused", "Cumulative money at least 20% higher than next yield"),
            ref_item("Balanced", "No single yield 20% higher than next"),
        ]
    )

    identity_refs = html.Div(
        [
            ref_item("Wonder Builder", "Built 3 or more wonders"),
            ref_item("Religious", "Founded a world religion"),
        ]
    )

    events_refs = html.Div(
        [
            ref_item("Science lead", "First to have 50% more cumulative science than opponent"),
            ref_item("Military lead", "First to have 50% more military power than opponent"),
            ref_item("Major battle", "Total military dropped 30% over 3 turns"),
            ref_item("4th/7th law", "Player enacted their 4th or 7th law"),
        ]
    )

    content = html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H6("Expansion", style={"color": text_color}),
                            expansion_refs,
                        ],
                        width=4,
                    ),
                    dbc.Col(
                        [
                            html.H6("Military", style={"color": text_color}),
                            military_refs,
                        ],
                        width=8,
                    ),
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H6("Identity", style={"color": text_color}),
                            identity_refs,
                        ],
                        width=4,
                    ),
                    dbc.Col(
                        [
                            html.H6("Key Events", style={"color": text_color}),
                            events_refs,
                        ],
                        width=8,
                    ),
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H6("Economy", style={"color": text_color}),
                            economy_refs,
                        ],
                        width=8,
                    ),
                ],
            ),
        ],
        style={"fontSize": "13px"},
    )

    return dbc.Accordion(
        [
            dbc.AccordionItem(
                content,
                title="Reference",
            ),
        ],
        start_collapsed=True,
        className="mt-3",
    )
