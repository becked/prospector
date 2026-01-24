"""Game state comparison component for match analysis.

This module provides a 7-column table showing per-turn game state comparisons
between two players, including events, orders, and winner indicators.
"""

import re
from typing import Dict, Optional, Tuple

import pandas as pd
import dash_bootstrap_components as dbc
from dash import html

from tournament_visualizer.components.layouts import create_empty_state
from tournament_visualizer.data.game_constants import (
    get_tech_icon_path,
    get_law_icon_path,
    get_wonder_icon_path,
    get_family_crest_icon_path,
    get_nation_crest_icon_path,
    ARCHETYPE_ICONS,
    FAMILY_TO_ARCHETYPE,
    EVENT_FILTER_CATEGORIES,
)


# Yield icon paths
YIELD_ORDERS_ICON = "/assets/icons/yields/YIELD_ORDERS.png"
YIELD_SCIENCE_ICON = "/assets/icons/yields/YIELD_SCIENCE.png"
YIELD_TRAINING_ICON = "/assets/icons/other/Cycle_Military.png"
YIELD_VP_ICON = "/assets/icons/other/VICTORY_Normal.png"
AMBITION_ICON = "/assets/icons/other/TURN_SUMMARY_AMBITION.png"
RELIGION_ICON_DEFAULT = "/assets/icons/other/RELIGION_FOUNDED.png"
CITY_FOUNDED_ICON = "/assets/icons/other/CITY_FOUNDED.png"

# Religion icons mapping (falls back to RELIGION_FOUNDED.png for pagan religions)
RELIGION_ICONS = {
    "Christianity": "/assets/icons/other/RELIGION_CHRISTIANITY.png",
    "Judaism": "/assets/icons/other/RELIGION_JUDAISM.png",
    "Manichaeism": "/assets/icons/other/RELIGION_MANICHAEISM.png",
    "Zoroastrianism": "/assets/icons/other/RELIGION_ZOROASTRIANISM.png",
}

# Theology icons mapping
THEOLOGY_ICONS = {
    "Dualism": "/assets/icons/other/THEOLOGY_DUALISM.png",
    "Enlightenment": "/assets/icons/other/THEOLOGY_ENLIGHTENMENT.png",
    "Gnosticism": "/assets/icons/other/THEOLOGY_GNOSTICISM.png",
    "Legalism": "/assets/icons/other/THEOLOGY_LEGALISM.png",
    "Mythology": "/assets/icons/other/THEOLOGY_MYTHOLOGY.png",
    "Redemption": "/assets/icons/other/THEOLOGY_REDEMPTION.png",
    "Revelation": "/assets/icons/other/THEOLOGY_REVELATION.png",
    "Veneration": "/assets/icons/other/THEOLOGY_VENERATION.png",
}


def _create_styled_tooltip(text: str) -> html.Div:
    """Create a styled tooltip element.

    Args:
        text: Tooltip text to display

    Returns:
        HTML div for the tooltip
    """
    return html.Div(
        text,
        className="event-tooltip",
    )


def _create_colored_crest(
    crest_path: str,
    color: str,
    size: str = "16px",
) -> html.Div:
    """Create a nation crest icon tinted with the nation's color.

    Uses CSS mask-image to display the white crest icon in the specified color.

    Args:
        crest_path: URL path to the crest icon
        color: Hex color to tint the crest (e.g., "#4dabf7")
        size: CSS size for width and height

    Returns:
        HTML div styled as a colored crest icon
    """
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


def _create_winner_indicator(
    p1_value: float,
    p2_value: float,
    p1_crest_path: Optional[str],
    p2_crest_path: Optional[str],
    p1_color: str,
    p2_color: str,
    p1_name: str = "Player 1",
    p2_name: str = "Player 2",
    metric_label: str = "",
) -> html.Div:
    """Create compact winner indicator showing nation crest + percentage.

    Shows the leading player's nation crest with percentage ahead.
    For ties (equal values), shows both crests.

    Args:
        p1_value: Player 1's metric value
        p2_value: Player 2's metric value
        p1_crest_path: Path to P1's nation crest icon
        p2_crest_path: Path to P2's nation crest icon
        p1_color: Fallback color for P1 if no crest
        p2_color: Fallback color for P2 if no crest
        p1_name: Player 1's display name
        p2_name: Player 2's display name
        metric_label: Fallback label if no crests (e.g., "VP")

    Returns:
        HTML div with winner crest and percentage
    """
    # Handle zero/null values
    p1_val = p1_value if p1_value and p1_value > 0 else 0
    p2_val = p2_value if p2_value and p2_value > 0 else 0

    # Both zero - show dash
    if p1_val == 0 and p2_val == 0:
        return html.Div(
            "—",
            style={
                "textAlign": "center",
                "color": "#868e96",
                "fontSize": "0.8rem",
            },
            title="No data",
        )

    # Determine winner/loser for tooltip formatting
    if p1_val >= p2_val:
        winner_name, winner_val = p1_name, p1_val
        loser_name, loser_val = p2_name, p2_val
    else:
        winner_name, winner_val = p2_name, p2_val
        loser_name, loser_val = p1_name, p1_val

    # Determine crests for tooltip (winner first, loser second)
    if p1_val >= p2_val:
        winner_crest_path, loser_crest_path = p1_crest_path, p2_crest_path
        winner_crest_color, loser_crest_color = p1_color, p2_color
    else:
        winner_crest_path, loser_crest_path = p2_crest_path, p1_crest_path
        winner_crest_color, loser_crest_color = p2_color, p1_color

    # Calculate percentage difference
    if p1_val == p2_val:
        # Tie - show both crests
        pct_text = "="
        is_tie = True
        winner_crest = None
    elif p1_val > p2_val:
        # P1 leads
        if p2_val > 0:
            pct = ((p1_val - p2_val) / p2_val) * 100
            pct_text = f"+{pct:.0f}%" if pct < 1000 else ">999%"
        else:
            pct_text = "∞"
        is_tie = False
        winner_crest = p1_crest_path
        winner_color = p1_color
    else:
        # P2 leads
        if p1_val > 0:
            pct = ((p2_val - p1_val) / p1_val) * 100
            pct_text = f"+{pct:.0f}%" if pct < 1000 else ">999%"
        else:
            pct_text = "∞"
        is_tie = False
        winner_crest = p2_crest_path
        winner_color = p2_color

    icon_size = "16px"
    children = []

    if is_tie:
        # Show both crests for tie
        if p1_crest_path:
            children.append(_create_colored_crest(p1_crest_path, p1_color, icon_size))
        if p2_crest_path:
            children.append(_create_colored_crest(p2_crest_path, p2_color, icon_size))
        if not p1_crest_path and not p2_crest_path:
            children.append(html.Span(pct_text, style={"color": "#868e96"}))
    else:
        # Show winner crest + percentage
        if winner_crest:
            children.append(_create_colored_crest(winner_crest, winner_color, icon_size))
        else:
            # Fallback: colored circle
            children.append(
                html.Div(
                    style={
                        "width": icon_size,
                        "height": icon_size,
                        "borderRadius": "50%",
                        "backgroundColor": winner_color,
                    }
                )
            )
        children.append(
            html.Span(
                pct_text,
                style={
                    "color": "#edf2f7",
                    "fontSize": "0.7rem",
                    "fontWeight": "bold",
                },
            )
        )

    # Create HTML tooltip with icons
    tooltip_icon_size = "14px"
    tooltip_row_style = {
        "display": "flex",
        "alignItems": "center",
        "gap": "6px",
        "whiteSpace": "nowrap",
    }
    tooltip_name_style = {
        "minWidth": "80px",
        "textAlign": "right",
    }
    tooltip_value_style = {
        "fontWeight": "bold",
        "minWidth": "50px",
        "textAlign": "right",
    }

    # Winner row
    winner_icon = _create_colored_crest(winner_crest_path, winner_crest_color, tooltip_icon_size) if winner_crest_path else html.Span()
    winner_row = html.Div(
        [
            winner_icon,
            html.Span(winner_name, style=tooltip_name_style),
            html.Span(":", style={"color": "#868e96"}),
            html.Span(f"{winner_val:,.0f}", style=tooltip_value_style),
        ],
        style=tooltip_row_style,
    )

    # Loser row
    loser_icon = _create_colored_crest(loser_crest_path, loser_crest_color, tooltip_icon_size) if loser_crest_path else html.Span()
    loser_row = html.Div(
        [
            loser_icon,
            html.Span(loser_name, style=tooltip_name_style),
            html.Span(":", style={"color": "#868e96"}),
            html.Span(f"{loser_val:,.0f}", style=tooltip_value_style),
        ],
        style=tooltip_row_style,
    )

    tooltip_div = html.Div(
        [winner_row, loser_row],
        className="winner-tooltip",
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": "4px",
        },
    )

    return html.Div(
        [*children, tooltip_div],
        className="winner-indicator",
        style={
            "display": "flex",
            "flexDirection": "column",
            "alignItems": "center",
            "justifyContent": "center",
            "gap": "0px",
            "position": "relative",
        },
    )


def create_game_state_component(
    comparison_df: pd.DataFrame,
    events_df: pd.DataFrame,
    player1_name: str,
    player2_name: str,
    player1_id: int,
    player2_id: int,
    player1_color: str = "#4dabf7",
    player2_color: str = "#ff6b6b",
    player1_civilization: str = "",
    player2_civilization: str = "",
    show_text: bool = False,
    show_metrics: bool = True,
    enabled_categories: Optional[list[str]] = None,
) -> html.Div:
    """Create game state comparison table.

    Layout with metrics: Turn | P1 Events | Ord | Mil | Sci | VP | P2 Events
    Layout without metrics: Turn | P1 Events | P2 Events

    Args:
        comparison_df: DataFrame from get_match_turn_comparisons() with columns:
            turn_number, p1_military, p2_military, p1_orders, p2_orders,
            p1_science, p2_science, p1_vp, p2_vp, and ratio columns
        events_df: DataFrame from get_match_timeline_events() with event data
        player1_name: Display name for player 1
        player2_name: Display name for player 2
        player1_id: Database player ID for player 1
        player2_id: Database player ID for player 2
        player1_color: Nation color for player 1 (hex)
        player2_color: Nation color for player 2 (hex)
        player1_civilization: Civilization name for player 1 (for crest icon)
        player2_civilization: Civilization name for player 2 (for crest icon)
        show_text: Whether to show text labels next to event icons (default False)
        show_metrics: Whether to show the center comparison columns (default True)

    Returns:
        Dash HTML component with comparison table
    """
    if comparison_df.empty:
        return create_empty_state(
            title="No Game State Data",
            message="No comparison data found for this match.",
            icon="bi-bar-chart",
        )

    # Filter events by enabled categories
    if enabled_categories is not None and not events_df.empty:
        # Build list of enabled event types from categories
        enabled_event_types = set()
        for category in enabled_categories:
            if category in EVENT_FILTER_CATEGORIES:
                enabled_event_types.update(EVENT_FILTER_CATEGORIES[category])

        # Filter events to only include enabled event types
        events_df = events_df[events_df["event_type"].isin(enabled_event_types)]

    # Get nation crest paths for winner indicators
    p1_crest = get_nation_crest_icon_path(player1_civilization)
    p2_crest = get_nation_crest_icon_path(player2_civilization)

    # Common styles - base row style (alternating colors applied in loop)
    row_style_base = {
        "display": "flex",
        "flexDirection": "row",
        "borderBottom": "1px solid var(--bs-border-color)",
        "minHeight": "32px",
        "width": "100%",
        "alignItems": "center",
    }
    row_color_even = "#0e1b2e"
    row_color_odd = "#132337"

    # Column styles - 7 columns (Turn, P1 Events, 4x Comparisons, P2 Events)
    turn_col_style = {
        "flex": "0 0 50px",
        "width": "50px",
        "textAlign": "center",
        "fontWeight": "bold",
        "padding": "6px 4px",
        "color": "#edf1f6",
    }

    events_col_style = {
        "flex": "1 1 22%",
        "padding": "6px 8px",
        "color": "#edf2f7",
    }

    comparison_col_style = {
        "flex": "0 0 44px",
        "width": "44px",
        "padding": "4px 2px",
    }

    # Header comparison column style (shared)
    header_comparison_style = {
        **comparison_col_style,
        "fontSize": "0.7rem",
        "fontWeight": "bold",
        "textAlign": "center",
        "color": "#edf1f6",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
    }

    # Build header children list
    # With metrics: Turn | P1 Events | Ord | Mil | Sci | VP | P2 Events
    # Without metrics: P1 Events | Turn | P2 Events
    header_children = []

    if show_metrics:
        # Turn on left when metrics enabled
        header_children.append(html.Div("Turn", style=turn_col_style))

    header_children.append(
        html.Div(
            player1_name,
            style={
                **events_col_style,
                "textAlign": "right",
                "fontWeight": "bold",
            },
        ),
    )

    if show_metrics:
        # All 4 metrics columns
        header_children.extend([
            html.Div(
                [
                    html.Span(
                        [
                            html.Img(
                                src=YIELD_ORDERS_ICON,
                                style={"width": "14px", "height": "14px", "verticalAlign": "middle"},
                            ),
                            _create_styled_tooltip("Orders per Turn"),
                        ],
                        className="event-icon-wrapper",
                        style={"position": "relative"},
                    ),
                ],
                style=header_comparison_style,
            ),
            html.Div(
                [
                    html.Span(
                        [
                            html.Img(
                                src=YIELD_TRAINING_ICON,
                                style={"width": "14px", "height": "14px", "verticalAlign": "middle"},
                            ),
                            _create_styled_tooltip("Military Power"),
                        ],
                        className="event-icon-wrapper",
                        style={"position": "relative"},
                    ),
                ],
                style=header_comparison_style,
            ),
            html.Div(
                [
                    html.Span(
                        [
                            html.Img(
                                src=YIELD_SCIENCE_ICON,
                                style={"width": "14px", "height": "14px", "verticalAlign": "middle"},
                            ),
                            _create_styled_tooltip("Total Science"),
                        ],
                        className="event-icon-wrapper",
                        style={"position": "relative"},
                    ),
                ],
                style=header_comparison_style,
            ),
            html.Div(
                [
                    html.Span(
                        [
                            html.Img(
                                src=YIELD_VP_ICON,
                                style={"width": "14px", "height": "14px", "verticalAlign": "middle"},
                            ),
                            _create_styled_tooltip("Victory Points"),
                        ],
                        className="event-icon-wrapper",
                        style={"position": "relative"},
                    ),
                ],
                style=header_comparison_style,
            ),
        ])
    else:
        # Turn in center when metrics disabled
        header_children.append(html.Div("Turn", style=turn_col_style))

    header_children.append(
        html.Div(
            player2_name,
            style={
                **events_col_style,
                "textAlign": "left",
                "fontWeight": "bold",
            },
        ),
    )

    header_content = html.Div(
        header_children,
        style={
            "display": "flex",
            "flexDirection": "row",
            "width": "100%",
            "alignItems": "center",
        },
    )

    # Build border children list
    # With metrics: Turn | P1 Events | Ord | Mil | Sci | VP | P2 Events
    # Without metrics: P1 Events | Turn | P2 Events
    border_children = []

    if show_metrics:
        # Turn column - no border (on left)
        border_children.append(html.Div(style={"flex": "0 0 50px", "height": "3px"}))

    # P1 events - player1 color
    border_children.append(
        html.Div(style={"flex": "1 1 22%", "height": "3px", "backgroundColor": player1_color})
    )

    if show_metrics:
        # All 4 metrics - gradient (4 x 44px = 176px)
        border_children.append(
            html.Div(style={
                "flex": "0 0 176px",
                "height": "3px",
                "background": f"linear-gradient(to right, {player1_color}, {player2_color})",
            })
        )
    else:
        # Turn column - no border (in center)
        border_children.append(html.Div(style={"flex": "0 0 50px", "height": "3px"}))

    # P2 events - player2 color
    border_children.append(
        html.Div(style={"flex": "1 1 22%", "height": "3px", "backgroundColor": player2_color})
    )

    header_border = html.Div(
        border_children,
        style={"display": "flex", "width": "100%"},
    )

    header_row = html.Div(
        [header_content, header_border],
        style={
            "position": "sticky",
            "top": "0",
            "backgroundColor": "#172133",
            "zIndex": "10",
        },
        className="game-state-header",
    )

    # Build data rows - include all turns from both comparison and events
    data_rows = [header_row]

    # Get all unique turns from comparison and events
    comparison_turns = set(comparison_df["turn_number"].tolist()) if not comparison_df.empty else set()
    event_turns = set(events_df["turn"].tolist()) if not events_df.empty else set()
    all_turns = sorted(comparison_turns | event_turns)

    # Create lookup for comparison data
    comparison_by_turn = {
        int(row["turn_number"]): row for _, row in comparison_df.iterrows()
    } if not comparison_df.empty else {}

    # Track city counts: family counts and total counts per player
    family_city_counts: Dict[Tuple[int, str], int] = {}  # (player_id, family_name) -> count
    player_city_counts: Dict[int, int] = {}  # player_id -> total count

    for row_idx, turn in enumerate(all_turns):
        # Get events for this turn
        turn_events = events_df[events_df["turn"] == turn] if not events_df.empty else pd.DataFrame()
        p1_events = turn_events[turn_events["player_id"] == player1_id] if not turn_events.empty else pd.DataFrame()
        p2_events = turn_events[turn_events["player_id"] == player2_id] if not turn_events.empty else pd.DataFrame()

        # Build event icons (with city count tracking)
        p1_icons = _build_event_icons(p1_events, player1_id, family_city_counts, player_city_counts, show_text)
        p2_icons = _build_event_icons(p2_events, player2_id, family_city_counts, player_city_counts, show_text)

        # Get comparison data if available
        comp_row = comparison_by_turn.get(turn)

        if comp_row is not None:
            # Create winner indicators
            ord_indicator = _create_winner_indicator(
                comp_row["p1_orders"],
                comp_row["p2_orders"],
                p1_crest,
                p2_crest,
                player1_color,
                player2_color,
                player1_name,
                player2_name,
            )
            mil_indicator = _create_winner_indicator(
                comp_row["p1_military"],
                comp_row["p2_military"],
                p1_crest,
                p2_crest,
                player1_color,
                player2_color,
                player1_name,
                player2_name,
            )
            sci_indicator = _create_winner_indicator(
                comp_row["p1_science"],
                comp_row["p2_science"],
                p1_crest,
                p2_crest,
                player1_color,
                player2_color,
                player1_name,
                player2_name,
            )
            vp_indicator = _create_winner_indicator(
                comp_row.get("p1_vp", 0),
                comp_row.get("p2_vp", 0),
                p1_crest,
                p2_crest,
                player1_color,
                player2_color,
                player1_name,
                player2_name,
                metric_label="VP",
            )
        else:
            # No comparison data - show dashes
            ord_indicator = _create_winner_indicator(0, 0, p1_crest, p2_crest, player1_color, player2_color, player1_name, player2_name)
            mil_indicator = _create_winner_indicator(0, 0, p1_crest, p2_crest, player1_color, player2_color, player1_name, player2_name)
            sci_indicator = _create_winner_indicator(0, 0, p1_crest, p2_crest, player1_color, player2_color, player1_name, player2_name)
            vp_indicator = _create_winner_indicator(0, 0, p1_crest, p2_crest, player1_color, player2_color, player1_name, player2_name)

        # Build row children list
        # With metrics: Turn | P1 Events | Ord | Mil | Sci | VP | P2 Events
        # Without metrics: P1 Events | Turn | P2 Events
        row_children = []

        if show_metrics:
            # Turn on left when metrics enabled
            row_children.append(html.Div(str(turn), style=turn_col_style))

        row_children.append(
            html.Div(
                p1_icons,
                style={**events_col_style, "textAlign": "right"},
            ),
        )

        if show_metrics:
            # All 4 metrics
            row_children.extend([
                html.Div(ord_indicator, style=comparison_col_style),
                html.Div(mil_indicator, style=comparison_col_style),
                html.Div(sci_indicator, style=comparison_col_style),
                html.Div(vp_indicator, style=comparison_col_style),
            ])
        else:
            # Turn in center when metrics disabled
            row_children.append(html.Div(str(turn), style=turn_col_style))

        row_children.append(
            html.Div(
                p2_icons,
                style={**events_col_style, "textAlign": "left"},
            ),
        )

        # Apply alternating row colors
        row_bg = row_color_even if row_idx % 2 == 0 else row_color_odd
        row_style = {**row_style_base, "backgroundColor": row_bg}

        data_row = html.Div(
            row_children,
            style=row_style,
            className="game-state-row",
        )
        data_rows.append(data_row)

    return html.Div(
        data_rows,
        className="game-state-container",
    )


def _build_event_icons(
    events_df: pd.DataFrame,
    player_id: int,
    family_city_counts: Dict[Tuple[int, str], int],
    player_city_counts: Dict[int, int],
    show_text: bool = False,
) -> list:
    """Build compact icon list from events DataFrame.

    Args:
        events_df: DataFrame with event data for one player on one turn
        player_id: Database player ID for tracking cities
        family_city_counts: Dict tracking (player_id, family_name) -> count
            This is mutated to track running counts across turns.
        player_city_counts: Dict tracking player_id -> total city count
            This is mutated to track running counts across turns.
        show_text: Whether to show text labels next to icons

    Returns:
        List of HTML elements (icons with tooltips)
    """
    if events_df.empty:
        return []

    icons = []
    for _, event in events_df.iterrows():
        event_type = event.get("event_type", "")
        title = event.get("title", "")
        details = event.get("details", "")
        icon_emoji = event.get("icon", "")

        # Track city counts for city/capital events
        family_count = None
        total_count = None
        if event_type in ("city", "capital") and details:
            family_name = details  # details contains family_name
            key = (player_id, family_name)
            family_city_counts[key] = family_city_counts.get(key, 0) + 1
            family_count = family_city_counts[key]
            player_city_counts[player_id] = player_city_counts.get(player_id, 0) + 1
            total_count = player_city_counts[player_id]

        icon_element = _create_event_icon(event_type, title, icon_emoji, details, family_count, total_count, show_text)
        icons.append(icon_element)

    return icons


def _create_city_event_icons(
    city_name: str,
    family_name: str,
    family_icon_path: Optional[str],
    family_count: Optional[int],
    total_count: Optional[int],
    show_text: bool = False,
) -> html.Span:
    """Create combined city event display: city icon + family icon in one wrapper.

    Args:
        city_name: Name of the city
        family_name: Raw family name like "FAMILY_BARCID"
        family_icon_path: Path to the family crest icon
        family_count: Running count of cities for this family
        total_count: Total cities for this player
        show_text: Whether to show text label

    Returns:
        html.Span containing both icons in a single wrapper
    """
    icon_style = {
        "width": "22px",
        "height": "22px",
        "verticalAlign": "middle",
    }

    icon_container_style = {
        "position": "relative",
        "display": "inline-flex",
        "alignItems": "center",
        "justifyContent": "center",
        "width": "22px",
        "height": "22px",
        "marginRight": "4px",
        "flexShrink": "0",
    }

    badge_style = {
        "position": "absolute",
        "bottom": "-3px",
        "right": "-5px",
        "fontSize": "9px",
        "borderRadius": "50%",
        "width": "12px",
        "height": "12px",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
        "lineHeight": "1",
        "color": "#fff",
    }

    wrapper_style = {
        "display": "inline-flex",
        "alignItems": "center",
        "verticalAlign": "middle",
        "backgroundColor": "rgba(255,255,255,0.05)",
        "borderRadius": "4px",
        "margin": "2px",
    }

    label_style = {
        "fontSize": "14px",
        "verticalAlign": "middle",
        "color": "#c8d4e3",
    }

    # Parse family display name and class from raw name like "FAMILY_BARCID"
    # Handle direct archetype reference (e.g., "ARCHETYPE_PATRONS" for captured/rebel cities)
    if family_name.startswith("ARCHETYPE_"):
        # No family name, just class
        display_family_name = ""
        family_class = family_name.replace("ARCHETYPE_", "").title()
    else:
        # Normal family name like "FAMILY_BARCID" or "EGYPT_RAMESSIDE"
        if "_" in family_name.replace("FAMILY_", ""):
            parts = family_name.replace("FAMILY_", "").split("_")
            display_family_name = parts[-1].title()
        else:
            display_family_name = family_name.replace("FAMILY_", "").title()

        # Look up the archetype/class
        family_class = FAMILY_TO_ARCHETYPE.get(display_family_name, "")

    children = []

    # City founded icon with total count badge
    city_img = html.Img(src=CITY_FOUNDED_ICON, style=icon_style)
    city_badge = None
    if total_count is not None:
        city_badge = html.Span(
            str(total_count),
            style={**badge_style, "backgroundColor": "#40c057"}  # Green
        )
    city_container = html.Div(
        [city_img] + ([city_badge] if city_badge else []),
        style={**icon_container_style, "marginRight": "8px"},
    )
    children.append(city_container)

    # Family crest icon with family count badge
    if family_icon_path:
        family_img = html.Img(src=family_icon_path, style=icon_style)
        family_badge = None
        if family_count is not None:
            family_badge = html.Span(
                str(family_count),
                style={**badge_style, "backgroundColor": "#339af0"}  # Blue
            )
        family_container = html.Div(
            [family_img] + ([family_badge] if family_badge else []),
            style={**icon_container_style, "marginRight": "6px"},
        )
        children.append(family_container)

    # Build tooltip: "CityName (FamilyName Class)"
    if display_family_name and family_class:
        family_info = f"{display_family_name} {family_class}"
    elif display_family_name:
        family_info = display_family_name
    elif family_class:
        family_info = family_class
    else:
        family_info = ""

    tooltip_text = f"{city_name} ({family_info})" if family_info else city_name
    children.append(_create_styled_tooltip(tooltip_text))

    # Add text label if enabled
    if show_text:
        children.append(html.Span(tooltip_text, style=label_style))

    return html.Span(
        children,
        className="event-icon-wrapper",
        style={**wrapper_style, "position": "relative"},
    )


def _create_event_icon(
    event_type: str,
    title: str,
    fallback_emoji: str,
    details: str = "",
    family_count: Optional[int] = None,
    total_count: Optional[int] = None,
    show_text: bool = False,
) -> html.Img | html.Span:
    """Create an icon element for an event.

    Args:
        event_type: Type of event (tech, law, ruler, wonder_start, wonder_complete,
            city, capital, ambition, religion, etc.)
        title: Event title
        fallback_emoji: Emoji to use if no game icon available
        details: Event details (used for ruler archetype, family name)
        family_count: For city/capital events, the running count for this family
        total_count: For city/capital events, the total city count for this player
        show_text: Whether to show text label next to icon

    Returns:
        html.Img for game icons, html.Span for emoji fallback
    """
    icon_path = None
    tooltip = title
    badge_text = None
    badge_bg = None
    is_4th_law = False  # Default for uu_unlock check

    if event_type == "tech" and title.startswith("Discovered: "):
        tech_name = title[12:]
        icon_path = get_tech_icon_path(tech_name)
        tooltip = tech_name
    elif event_type == "law" and title.startswith("Adopted: "):
        law_name = title[9:]
        icon_path = get_law_icon_path(law_name)
        tooltip = law_name
    elif event_type == "law_swap" and "→" in title:
        # Title is "Swapped X → Y", extract Y (new law) for icon
        law_name = title.split("→")[1].strip()
        icon_path = get_law_icon_path(law_name)
        # Show "X → Y" without "Swapped " prefix
        tooltip = title.replace("Swapped ", "")
        badge_text = "🔄"
        badge_bg = "#748ffc"  # Blue/purple
    elif event_type == "wonder_start" and title.startswith("Started: "):
        wonder_name = title[9:]
        icon_path = get_wonder_icon_path(wonder_name)
        tooltip = f"Started: {wonder_name}"
        badge_text = "🔨"
        badge_bg = "#f59f00"  # Orange
    elif event_type == "wonder_complete" and title.startswith("Completed: "):
        wonder_name = title[11:]
        icon_path = get_wonder_icon_path(wonder_name)
        tooltip = f"Completed: {wonder_name}"
        badge_text = "✓"
        badge_bg = "#40c057"  # Green
    elif event_type in ("city", "capital") and details:
        # details contains family_name like "FAMILY_BARCID"
        is_capital = event_type == "capital"
        family_icon_path = get_family_crest_icon_path(details, is_seat=is_capital)
        # Extract just the city name without "Founded: " or "Capital: " prefix
        if title.startswith("Founded: "):
            city_name = title[9:]
        elif title.startswith("Capital: "):
            city_name = title[9:]
        else:
            city_name = title
        # Return early with both icons for city events
        return _create_city_event_icons(
            city_name, details, family_icon_path, family_count, total_count, show_text
        )
    elif event_type == "ruler" and details:
        # Icon shows archetype, so tooltip just needs ruler name
        archetype = details.split(" - ")[0] if " - " in details else details
        icon_path = ARCHETYPE_ICONS.get(archetype)
        tooltip = title
    elif event_type == "battle":
        icon_path = "/assets/icons/military/UNIT_ATTACKED.png"
    elif event_type == "city_lost":
        icon_path = "/assets/icons/other/CITY_BREACHED.png"
    elif event_type == "death":
        icon_path = "/assets/icons/other/CHARACTER_SUCCESSION.png"
    elif event_type == "uu_unlock":
        icon_path = "/assets/icons/other/LAWS_Highlighted.png"
        # Title is "6 Strength UU" (4th law) or "8 Strength UU" (7th law)
        is_4th_law = "6 Strength" in title
        if is_4th_law:
            tooltip = "4 laws adopted"
            badge_text = "4"
            badge_bg = "#339af0"  # Blue
        else:
            tooltip = "7 laws adopted"
            badge_text = "7"
            badge_bg = "#fab005"  # Gold
    elif event_type == "ambition":
        icon_path = AMBITION_ICON
        # Title is "Ambition: Control Six Mines"
        tooltip = title.replace("Ambition: ", "")
    elif event_type == "religion":
        # Title is "Founded: Carthaginian Paganism" or "Founded: Judaism"
        religion_name = title.replace("Founded: ", "")
        tooltip = f"Founded {religion_name}"
        # Look up specific icon, fall back to generic for pagan religions
        icon_path = RELIGION_ICONS.get(religion_name, RELIGION_ICON_DEFAULT)
    elif event_type == "religion_adopted":
        # Title is "Adopted Zoroastrianism"
        religion_name = title.replace("Adopted ", "")
        tooltip = f"Adopted {religion_name}"
        # Look up specific icon, fall back to generic
        icon_path = RELIGION_ICONS.get(religion_name, RELIGION_ICON_DEFAULT)
    elif event_type == "theology":
        # Title is "Legalism (Zoroastrianism)" - extract theology name for icon lookup
        match = re.match(r'^(\w+)\s*\(', title)
        theology_name = match.group(1) if match else title
        icon_path = THEOLOGY_ICONS.get(theology_name)
        tooltip = title  # Show full "Legalism (Zoroastrianism)"

    icon_style = {
        "width": "22px",
        "height": "22px",
        "verticalAlign": "middle",
    }

    # Fixed-size container for icon ensures consistent alignment
    icon_container_style = {
        "position": "relative",
        "display": "inline-flex",
        "alignItems": "center",
        "justifyContent": "center",
        "width": "22px",
        "height": "22px",
        "marginRight": "6px",
        "flexShrink": "0",
    }

    label_style = {
        "fontSize": "14px",
        "verticalAlign": "middle",
        "color": "#c8d4e3",
    }

    wrapper_style = {
        "display": "inline-flex",
        "alignItems": "center",
        "verticalAlign": "middle",
        "backgroundColor": "rgba(255,255,255,0.05)",
        "borderRadius": "4px",
        "margin": "2px",
    }

    badge_style = {
        "position": "absolute",
        "bottom": "-3px",
        "right": "-5px",
        "fontSize": "9px",
        "borderRadius": "50%",
        "width": "12px",
        "height": "12px",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
        "lineHeight": "1",
        "color": "#fff",
    }

    if icon_path:
        img_element = html.Img(
            src=icon_path,
            className="game-state-icon",
            title=tooltip,
            style=icon_style,
        )

        # Add corner badge if specified
        if badge_text and badge_bg:
            icon_with_badge = html.Div(
                [
                    img_element,
                    html.Span(badge_text, style={**badge_style, "backgroundColor": badge_bg}),
                ],
                style=icon_container_style,
            )
            children = [icon_with_badge]
            if show_text:
                children.append(html.Span(tooltip, style=label_style))
            children.append(_create_styled_tooltip(tooltip))
            return html.Span(
                children,
                className="event-icon-wrapper",
                style={**wrapper_style, "position": "relative"},
            )

        # Wrap icon in fixed-size container for consistent alignment
        icon_container = html.Div([img_element], style=icon_container_style)
        children = [icon_container]
        if show_text:
            children.append(html.Span(tooltip, style=label_style))
        children.append(_create_styled_tooltip(tooltip))
        return html.Span(
            children,
            className="event-icon-wrapper",
            style={**wrapper_style, "position": "relative"},
        )
    else:
        # Emoji fallback - style to match icon sizing
        emoji_style = {
            "fontSize": "18px",
            "width": "22px",
            "height": "22px",
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center",
        }
        emoji_element = html.Span(fallback_emoji, style=emoji_style)
        icon_container = html.Div([emoji_element], style=icon_container_style)
        children = [icon_container]
        if show_text:
            children.append(html.Span(tooltip, style=label_style))
        children.append(_create_styled_tooltip(tooltip))
        return html.Span(
            children,
            className="event-icon-wrapper",
            style={**wrapper_style, "position": "relative"},
        )


def get_game_state_styles() -> str:
    """Get CSS styles for game state component.

    Returns:
        CSS string for game state styling
    """
    return """
    .game-state-container {
        font-size: 0.85rem;
    }

    .game-state-row {
        display: flex;
        border-bottom: 1px solid var(--bs-border-color);
        min-height: 32px;
        align-items: center;
    }

    .game-state-header {
        position: sticky;
        top: 0;
        z-index: 10;
    }

    .game-state-icon {
        width: 22px;
        height: 22px;
        vertical-align: middle;
    }

    /* Custom tooltip for winner indicators */
    .winner-indicator {
        cursor: pointer;
    }

    .winner-indicator::after {
        content: attr(data-tooltip-line1) "\\A" attr(data-tooltip-line2);
        white-space: pre;
        position: absolute;
        bottom: 100%;
        left: 50%;
        transform: translateX(-50%);
        background-color: #1a2332;
        color: #c8d4e3;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 13px;
        font-family: monospace;
        line-height: 1.5;
        border: 1px solid #3a5a7e;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
        z-index: 1000;
        pointer-events: none;
        opacity: 0;
        visibility: hidden;
        transition: opacity 0.15s ease, visibility 0.15s ease;
        margin-bottom: 8px;
    }

    .winner-indicator:hover::after {
        opacity: 1;
        visibility: visible;
    }

    /* Arrow for tooltip */
    .winner-indicator::before {
        content: "";
        position: absolute;
        bottom: 100%;
        left: 50%;
        transform: translateX(-50%);
        border: 6px solid transparent;
        border-top-color: #3a5a7e;
        margin-bottom: 2px;
        z-index: 1001;
        opacity: 0;
        visibility: hidden;
        transition: opacity 0.15s ease, visibility 0.15s ease;
    }

    .winner-indicator:hover::before {
        opacity: 1;
        visibility: visible;
    }
    """
