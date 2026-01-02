"""Game state comparison component for match analysis.

This module provides a 7-column table showing per-turn game state comparisons
between two players, including events, orders, and mini bar comparators.
"""

from typing import Optional

import pandas as pd
import dash_bootstrap_components as dbc
from dash import html

from tournament_visualizer.components.layouts import create_empty_state
from tournament_visualizer.data.game_constants import (
    get_tech_icon_path,
    get_law_icon_path,
    get_wonder_icon_path,
    get_family_crest_icon_path,
    ARCHETYPE_ICONS,
)


# Yield icon paths
YIELD_ORDERS_ICON = "/assets/icons/yields/YIELD_ORDERS.png"
YIELD_SCIENCE_ICON = "/assets/icons/yields/YIELD_SCIENCE.png"
YIELD_TRAINING_ICON = "/assets/icons/other/Cycle_Military.png"


def _create_mini_bar_comparator(
    p1_value: float,
    p2_value: float,
    p1_color: str,
    p2_color: str,
    icon_path: Optional[str] = None,
) -> html.Div:
    """Create a mini two-bar comparator showing relative values.

    Shows an optional icon, two horizontal bars (P1 on top, P2 on bottom)
    with widths proportional to their values, plus a delta indicator.

    Args:
        p1_value: Player 1's value
        p2_value: Player 2's value
        p1_color: Color for player 1's bar
        p2_color: Color for player 2's bar
        icon_path: Optional path to yield icon

    Returns:
        HTML div containing the mini bar comparator
    """
    # Handle zero/null values
    p1_val = p1_value if p1_value and p1_value > 0 else 0
    p2_val = p2_value if p2_value and p2_value > 0 else 0

    # Calculate percentages (normalize to max)
    max_val = max(p1_val, p2_val, 1)  # Avoid division by zero
    p1_pct = (p1_val / max_val) * 100
    p2_pct = (p2_val / max_val) * 100

    # Calculate delta
    delta = p1_val - p2_val

    # Determine delta color and sign
    if delta > 0:
        delta_color = "#69db7c"  # Green - P1 ahead
        delta_text = f"+{delta:.0f}"
    elif delta < 0:
        delta_color = "#ff6b6b"  # Red - P1 behind
        delta_text = f"{delta:.0f}"
    else:
        delta_color = "#868e96"  # Gray - equal
        delta_text = "0"

    bar_height = "4px"
    bar_container_style = {
        "display": "flex",
        "flexDirection": "column",
        "gap": "2px",
        "flex": "1",
        "minWidth": "40px",
    }

    bar_bg_style = {
        "backgroundColor": "#2d3748",
        "borderRadius": "2px",
        "height": bar_height,
        "width": "100%",
        "overflow": "hidden",
    }

    p1_bar = html.Div(
        html.Div(
            style={
                "backgroundColor": p1_color,
                "height": "100%",
                "width": f"{p1_pct}%",
                "borderRadius": "2px",
            }
        ),
        style=bar_bg_style,
    )

    p2_bar = html.Div(
        html.Div(
            style={
                "backgroundColor": p2_color,
                "height": "100%",
                "width": f"{p2_pct}%",
                "borderRadius": "2px",
            }
        ),
        style=bar_bg_style,
    )

    delta_style = {
        "color": delta_color,
        "fontSize": "0.7rem",
        "fontWeight": "bold",
        "textAlign": "right",
    }

    # Build children list
    children = []

    # Add icon if provided
    if icon_path:
        children.append(
            html.Img(
                src=icon_path,
                style={
                    "width": "14px",
                    "height": "14px",
                    "opacity": "0.7",
                },
            )
        )

    children.append(html.Div([p1_bar, p2_bar], style=bar_container_style))
    children.append(html.Div(delta_text, style=delta_style))

    return html.Div(
        children,
        style={
            "display": "flex",
            "alignItems": "center",
            "gap": "4px",
            "padding": "2px 0",
        },
        title=f"{p1_val:.0f} vs {p2_val:.0f} ({delta_text})",
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
) -> html.Div:
    """Create 7-column game state comparison table.

    Layout: Turn | P1 Icons | P1 Orders | Mil Comp | Sci Comp | P2 Orders | P2 Icons

    Args:
        comparison_df: DataFrame from get_match_turn_comparisons() with columns:
            turn_number, p1_military, p2_military, p1_orders, p2_orders,
            p1_science, p2_science, mil_ratio, orders_ratio, science_ratio
        events_df: DataFrame from get_match_timeline_events() with event data
        player1_name: Display name for player 1
        player2_name: Display name for player 2
        player1_id: Database player ID for player 1
        player2_id: Database player ID for player 2
        player1_color: Nation color for player 1 (hex)
        player2_color: Nation color for player 2 (hex)

    Returns:
        Dash HTML component with 7-column table
    """
    if comparison_df.empty:
        return create_empty_state(
            title="No Game State Data",
            message="No comparison data found for this match.",
            icon="bi-bar-chart",
        )

    # Common styles
    row_style = {
        "display": "flex",
        "flexDirection": "row",
        "borderBottom": "1px solid var(--bs-border-color)",
        "minHeight": "32px",
        "width": "100%",
        "alignItems": "center",
        "backgroundColor": "#0e1b2e",
    }

    # Column styles - 6 columns (Turn, P1 Events, 3x Comparisons, P2 Events)
    # Unified background color to avoid visual artifacts
    turn_col_style = {
        "flex": "0 0 50px",
        "width": "50px",
        "textAlign": "center",
        "fontWeight": "bold",
        "padding": "6px 4px",
        "color": "#edf1f6",
    }

    events_col_style = {
        "flex": "1 1 25%",
        "padding": "6px 8px",
        "color": "#edf2f7",
    }

    comparison_col_style = {
        "flex": "0 0 105px",
        "width": "105px",
        "padding": "4px 12px 4px 4px",  # Extra right padding for visual separation
    }

    # Header comparison column style (shared)
    header_comparison_style = {
        **comparison_col_style,
        "fontSize": "0.75rem",
        "fontWeight": "bold",
        "textAlign": "center",
        "color": "#edf1f6",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
    }

    # Build header with separate border row for clean alignment
    header_content = html.Div(
        [
            html.Div("Turn", style=turn_col_style),
            html.Div(
                player1_name,
                style={
                    **events_col_style,
                    "textAlign": "right",
                    "fontWeight": "bold",
                },
            ),
            html.Div(
                [
                    html.Img(
                        src=YIELD_ORDERS_ICON,
                        style={"width": "16px", "height": "16px", "marginRight": "4px", "verticalAlign": "middle"},
                        title="Orders per Turn",
                    ),
                    "Ord",
                ],
                style=header_comparison_style,
                title="Orders per Turn Comparison",
            ),
            html.Div(
                [
                    html.Img(
                        src=YIELD_TRAINING_ICON,
                        style={"width": "16px", "height": "16px", "marginRight": "4px", "verticalAlign": "middle"},
                        title="Military Power",
                    ),
                    "Mil",
                ],
                style=header_comparison_style,
                title="Military Power Comparison",
            ),
            html.Div(
                [
                    html.Img(
                        src=YIELD_SCIENCE_ICON,
                        style={"width": "16px", "height": "16px", "marginRight": "4px", "verticalAlign": "middle"},
                        title="Science Rate",
                    ),
                    "Sci",
                ],
                style=header_comparison_style,
                title="Science Rate Comparison",
            ),
            html.Div(
                player2_name,
                style={
                    **events_col_style,
                    "textAlign": "left",
                    "fontWeight": "bold",
                },
            ),
        ],
        style={
            "display": "flex",
            "flexDirection": "row",
            "width": "100%",
            "alignItems": "center",
        },
    )

    # Separate border row with colored segments matching column widths
    header_border = html.Div(
        [
            # Turn column - no border
            html.Div(style={"flex": "0 0 50px", "height": "3px"}),
            # P1 events - player1 color
            html.Div(style={"flex": "1 1 25%", "height": "3px", "backgroundColor": player1_color}),
            # Comparison columns - gradient
            html.Div(style={
                "flex": "0 0 315px",  # 3 x 105px
                "height": "3px",
                "background": f"linear-gradient(to right, {player1_color}, {player2_color})",
            }),
            # P2 events - player2 color
            html.Div(style={"flex": "1 1 25%", "height": "3px", "backgroundColor": player2_color}),
        ],
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

    for turn in all_turns:
        # Get events for this turn
        turn_events = events_df[events_df["turn"] == turn] if not events_df.empty else pd.DataFrame()
        p1_events = turn_events[turn_events["player_id"] == player1_id] if not turn_events.empty else pd.DataFrame()
        p2_events = turn_events[turn_events["player_id"] == player2_id] if not turn_events.empty else pd.DataFrame()

        # Build event icons
        p1_icons = _build_event_icons(p1_events)
        p2_icons = _build_event_icons(p2_events)

        # Get comparison data if available
        comp_row = comparison_by_turn.get(turn)

        if comp_row is not None:
            # Create mini bar comparators with yield icons
            ord_bars = _create_mini_bar_comparator(
                comp_row["p1_orders"],
                comp_row["p2_orders"],
                player1_color,
                player2_color,
                icon_path=YIELD_ORDERS_ICON,
            )
            mil_bars = _create_mini_bar_comparator(
                comp_row["p1_military"],
                comp_row["p2_military"],
                player1_color,
                player2_color,
                icon_path=YIELD_TRAINING_ICON,
            )
            sci_bars = _create_mini_bar_comparator(
                comp_row["p1_science"],
                comp_row["p2_science"],
                player1_color,
                player2_color,
                icon_path=YIELD_SCIENCE_ICON,
            )
        else:
            # No comparison data - show empty comparators
            ord_bars = _create_mini_bar_comparator(0, 0, player1_color, player2_color, icon_path=YIELD_ORDERS_ICON)
            mil_bars = _create_mini_bar_comparator(0, 0, player1_color, player2_color, icon_path=YIELD_TRAINING_ICON)
            sci_bars = _create_mini_bar_comparator(0, 0, player1_color, player2_color, icon_path=YIELD_SCIENCE_ICON)

        data_row = html.Div(
            [
                html.Div(str(turn), style=turn_col_style),
                html.Div(
                    p1_icons,
                    style={**events_col_style, "textAlign": "right"},
                ),
                html.Div(ord_bars, style=comparison_col_style),
                html.Div(mil_bars, style=comparison_col_style),
                html.Div(sci_bars, style=comparison_col_style),
                html.Div(
                    p2_icons,
                    style={**events_col_style, "textAlign": "left"},
                ),
            ],
            style=row_style,
            className="game-state-row",
        )
        data_rows.append(data_row)

    return html.Div(
        data_rows,
        className="game-state-container",
    )


def _build_event_icons(events_df: pd.DataFrame) -> list:
    """Build compact icon list from events DataFrame.

    Args:
        events_df: DataFrame with event data for one player on one turn

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

        icon_element = _create_event_icon(event_type, title, icon_emoji, details)
        icons.append(icon_element)

    return icons


def _create_event_icon(
    event_type: str, title: str, fallback_emoji: str, details: str = ""
) -> html.Img | html.Span:
    """Create an icon element for an event.

    Args:
        event_type: Type of event (tech, law, ruler, wonder_start, wonder_complete, etc.)
        title: Event title
        fallback_emoji: Emoji to use if no game icon available
        details: Event details (used for ruler archetype)

    Returns:
        html.Img for game icons, html.Span for emoji fallback
    """
    icon_path = None
    tooltip = title

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
    elif event_type == "wonder_start" and title.startswith("Started: "):
        wonder_name = title[9:]
        icon_path = get_wonder_icon_path(wonder_name)
        tooltip = f"Started: {wonder_name}"
    elif event_type == "wonder_complete" and title.startswith("Completed: "):
        wonder_name = title[11:]
        icon_path = get_wonder_icon_path(wonder_name)
        tooltip = f"Completed: {wonder_name}"
    elif event_type in ("city", "capital") and details:
        # details contains family_name like "FAMILY_BARCID"
        is_capital = event_type == "capital"
        icon_path = get_family_crest_icon_path(details, is_seat=is_capital)
        # Extract just the city name without "Founded: " or "Capital: " prefix
        if title.startswith("Founded: "):
            tooltip = title[9:]
        elif title.startswith("Capital: "):
            tooltip = title[9:]
        else:
            tooltip = title
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
        else:
            tooltip = "7 laws adopted"

    icon_style = {
        "width": "20px",
        "height": "20px",
        "verticalAlign": "middle",
    }

    # Fixed-size container for icon ensures consistent alignment
    icon_container_style = {
        "position": "relative",
        "display": "inline-flex",
        "alignItems": "center",
        "justifyContent": "center",
        "width": "20px",
        "height": "20px",
        "marginRight": "5px",
        "flexShrink": "0",
    }

    label_style = {
        "fontSize": "11px",
        "verticalAlign": "middle",
        "color": "#adb5bd",
    }

    wrapper_style = {
        "display": "inline-flex",
        "alignItems": "center",
        "backgroundColor": "rgba(255,255,255,0.05)",
        "borderRadius": "4px",
        "padding": "4px 8px 4px 6px",
        "marginRight": "6px",
        "marginBottom": "3px",
    }

    if icon_path:
        img_element = html.Img(
            src=icon_path,
            className="game-state-icon",
            title=tooltip,
            style=icon_style,
        )

        # Add corner badge for wonder, law_swap, and uu_unlock events
        if event_type in ("wonder_start", "wonder_complete", "law_swap", "uu_unlock"):
            if event_type == "wonder_start":
                badge_text = "🔨"
                badge_bg = "#f59f00"  # Orange
            elif event_type == "wonder_complete":
                badge_text = "✓"
                badge_bg = "#40c057"  # Green
            elif event_type == "law_swap":
                badge_text = "🔄"
                badge_bg = "#748ffc"  # Blue/purple
            else:  # uu_unlock
                badge_text = "4" if is_4th_law else "7"
                badge_bg = "#339af0" if is_4th_law else "#fab005"  # Blue for 4, Gold for 7
            badge_style = {
                "position": "absolute",
                "bottom": "-2px",
                "right": "-4px",
                "fontSize": "8px",
                "backgroundColor": badge_bg,
                "borderRadius": "50%",
                "width": "11px",
                "height": "11px",
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                "lineHeight": "1",
            }
            icon_with_badge = html.Div(
                [
                    img_element,
                    html.Span(badge_text, style=badge_style),
                ],
                style=icon_container_style,
            )
            return html.Span(
                [icon_with_badge, html.Span(tooltip, style=label_style)],
                style=wrapper_style,
                title=tooltip,
            )

        # Wrap icon in fixed-size container for consistent alignment
        icon_container = html.Div([img_element], style=icon_container_style)
        return html.Span(
            [icon_container, html.Span(tooltip, style=label_style)],
            style=wrapper_style,
            title=tooltip,
        )
    else:
        emoji_container = html.Div(
            [html.Span(fallback_emoji)],
            style=icon_container_style,
        )
        return html.Span(
            [emoji_container, html.Span(tooltip, style=label_style)],
            style=wrapper_style,
            title=tooltip,
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
        width: 24px;
        height: 24px;
        vertical-align: middle;
    }
    """
