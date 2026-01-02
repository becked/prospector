"""Timeline component for match event visualization.

This module provides a two-column timeline display showing key game events
for both players side-by-side, organized by turn number.
"""

from typing import Optional

import pandas as pd
import dash_bootstrap_components as dbc
from dash import html

from tournament_visualizer.components.layouts import create_empty_state
from tournament_visualizer.data.game_constants import get_tech_icon_path, get_law_icon_path, ARCHETYPE_ICONS


def create_timeline_component(
    events_df: pd.DataFrame,
    player1_name: str,
    player2_name: str,
    player1_id: int,
    player2_id: int,
    player1_color: str = "#4dabf7",
    player2_color: str = "#ff6b6b",
) -> html.Div:
    """Create two-column timeline HTML component.

    Renders a timeline with player 1 events on the left, turn numbers in the
    center column, and player 2 events on the right.

    Args:
        events_df: DataFrame from get_match_timeline_events() with columns:
            turn, player_id, event_type, title, details, icon, subtype, player_name
        player1_name: Display name for player 1 (left column)
        player2_name: Display name for player 2 (right column)
        player1_id: Player ID for player 1
        player2_id: Player ID for player 2
        player1_color: Nation color for player 1 (hex)
        player2_color: Nation color for player 2 (hex)

    Returns:
        Dash HTML component with timeline layout
    """
    if events_df.empty:
        return create_empty_state(
            title="No Timeline Events",
            message="No events found for this match.",
            icon="bi-calendar-x",
        )

    # Get unique turns and sort
    turns = sorted(events_df["turn"].unique())

    # Build timeline rows
    timeline_rows = []

    # Common row styles for flexbox layout
    row_style = {
        "display": "flex",
        "flexDirection": "row",
        "borderBottom": "1px solid var(--bs-border-color)",
        "minHeight": "32px",
        "width": "100%",
    }

    left_cell_style = {
        "flex": "1 1 40%",
        "padding": "6px 12px",
        "textAlign": "right",
        "borderRight": "1px solid var(--bs-border-color)",
        "backgroundColor": "#0e1b2e",  # Match page background
    }

    center_cell_style = {
        "flex": "0 0 60px",
        "width": "60px",
        "textAlign": "center",
        "fontWeight": "bold",
        "padding": "6px 4px",
        "backgroundColor": "#172133",
        "color": "#edf1f6",
    }

    right_cell_style = {
        "flex": "1 1 40%",
        "padding": "6px 12px",
        "textAlign": "left",
        "borderLeft": "1px solid var(--bs-border-color)",
        "backgroundColor": "#0e1b2e",  # Match page background
    }

    # Header row with player names
    header_row = html.Div(
        [
            html.Div(
                player1_name,
                style={
                    **left_cell_style,
                    "fontWeight": "bold",
                    "borderBottom": f"3px solid {player1_color}",
                    "borderRight": "none",  # No border in header
                    "textAlign": "center",
                },
            ),
            html.Div(
                "Turn",
                style={
                    **center_cell_style,
                    "fontWeight": "bold",
                    "backgroundColor": "inherit",  # Match header row background
                },
            ),
            html.Div(
                player2_name,
                style={
                    **right_cell_style,
                    "fontWeight": "bold",
                    "borderBottom": f"3px solid {player2_color}",
                    "borderLeft": "none",  # No border in header
                    "textAlign": "center",
                },
            ),
        ],
        style={
            **row_style,
            "position": "sticky",
            "top": "0",
            "backgroundColor": "#172133",  # Dark header background
            "zIndex": "10",
            "borderBottom": "none",
        },
        className="timeline-row timeline-header",
    )
    timeline_rows.append(header_row)

    # Event rows by turn
    for turn in turns:
        turn_events = events_df[events_df["turn"] == turn]

        # Split events by player
        p1_events = turn_events[turn_events["player_id"] == player1_id]
        p2_events = turn_events[turn_events["player_id"] == player2_id]

        # Build event lists for each player
        p1_content = _build_event_list(p1_events)
        p2_content = _build_event_list(p2_events)

        # Only show row if at least one player has events
        if len(p1_events) > 0 or len(p2_events) > 0:
            row = html.Div(
                [
                    html.Div(
                        p1_content if p1_content else "",
                        style=left_cell_style,
                        className="timeline-cell-left",
                    ),
                    html.Div(
                        str(turn),
                        style=center_cell_style,
                        className="timeline-cell-center",
                    ),
                    html.Div(
                        p2_content if p2_content else "",
                        style=right_cell_style,
                        className="timeline-cell-right",
                    ),
                ],
                style=row_style,
                className="timeline-row",
            )
            timeline_rows.append(row)

    return html.Div(
        timeline_rows,
        className="timeline-container",
    )


def _build_event_list(events_df: pd.DataFrame) -> list:
    """Build a list of event components from DataFrame rows.

    Consolidates multiple events of the same type into a single line.
    Pairs death events with their corresponding ruler crowning events.

    Args:
        events_df: DataFrame with event data

    Returns:
        List of HTML components for events
    """
    if events_df.empty:
        return []

    # Separate death, crowned, starting ruler, and other events
    death_events = events_df[events_df["event_type"] == "death"]
    ruler_events = events_df[events_df["event_type"] == "ruler"]
    crowned_events = ruler_events[ruler_events["title"].str.startswith("Crowned ")]
    starting_events = ruler_events[ruler_events["title"].str.startswith("Starting Ruler:")]
    other_events = events_df[~events_df["event_type"].isin(["death", "ruler"])]

    event_items = []

    # Convert to lists - they should already be in succession order from the query
    death_list = list(death_events.iterrows())
    crowned_list = list(crowned_events.iterrows())

    # Pair deaths with crownings by position (1:1 in succession order)
    # Same-name successions are valid (parent → child with same name)
    for i, (_, death_row) in enumerate(death_list):
        dead_name = death_row.get("title", "").replace(" Died", "")

        if i < len(crowned_list):
            _, ruler_row = crowned_list[i]
            new_ruler_name = ruler_row.get("title", "").replace("Crowned ", "")
            details = ruler_row.get("details", "")

            # Create archetype icon for the new ruler
            icon_element = _create_icon_element("ruler", ruler_row.get("title", ""), "👑", details)

            # Format: "OldRuler Died → NewRuler {icon} Crowned"
            css_class = "timeline-event timeline-event-ruler"
            event_items.append(
                html.Div(
                    [f"{dead_name} Died → {new_ruler_name} ", icon_element, " Crowned"],
                    className=css_class,
                    style={"color": "#edf2f7"},
                )
            )
        else:
            # No matching ruler, show death alone
            event_items.append(_format_event_item(death_row))

    # Add starting ruler events (not paired with deaths)
    for _, ruler_row in starting_events.iterrows():
        event_items.append(_format_event_item(ruler_row))

    # Event types that can be consolidated with their prefix to strip
    consolidatable = {
        "tech": "Discovered: ",
        "law": "Adopted: ",
        "city": "Founded: ",
        "capital": "Capital: ",
    }

    # Process other events
    grouped = other_events.groupby("event_type")

    for event_type, group in grouped:
        if event_type in consolidatable and len(group) > 1:
            # Consolidate multiple events of same type
            prefix = consolidatable[event_type]
            items = []
            for _, row in group.iterrows():
                title = row.get("title", "")
                if title.startswith(prefix):
                    items.append(title[len(prefix):])
                else:
                    items.append(title)

            fallback_icon = group.iloc[0].get("icon", "")
            consolidated_title = f"{prefix}{', '.join(items)}"
            css_class = f"timeline-event timeline-event-{event_type}"

            if event_type == "tech":
                icons = [
                    html.Img(
                        src=get_tech_icon_path(name),
                        className="timeline-icon",
                        title=name,
                        style={"width": "36px", "height": "36px", "verticalAlign": "middle", "marginRight": "2px"},
                    )
                    for name in items
                ]
                event_items.append(
                    html.Div(icons, className=css_class, style={"color": "#edf2f7"})
                )
            elif event_type == "law":
                icons = [
                    html.Img(
                        src=get_law_icon_path(name),
                        className="timeline-icon",
                        title=f"Adopted: {name}",
                        style={"width": "36px", "height": "36px", "verticalAlign": "middle", "marginRight": "2px"},
                    )
                    for name in items
                ]
                event_items.append(
                    html.Div(icons + [f"  {consolidated_title}"], className=css_class, style={"color": "#edf2f7"})
                )
            else:
                event_items.append(
                    html.Div(
                        f"{fallback_icon}  {consolidated_title}",
                        className=css_class,
                        style={"color": "#edf2f7"},
                    )
                )
        else:
            for _, row in group.iterrows():
                event_items.append(_format_event_item(row))

    return event_items


def _create_icon_element(
    event_type: str, title: str, fallback_emoji: str, details: str = ""
) -> html.Img | html.Span:
    """Create an icon element - game image or fallback emoji.

    Args:
        event_type: Type of event (tech, law, ruler, etc.)
        title: Event title to extract name from
        fallback_emoji: Emoji to use if no game icon available
        details: Event details (used for ruler archetype)

    Returns:
        html.Img for game icons, html.Span for emoji fallback
    """
    icon_path = None
    tooltip = title

    if event_type == "tech" and title.startswith("Discovered: "):
        tech_name = title[12:]  # Strip "Discovered: "
        icon_path = get_tech_icon_path(tech_name)
        tooltip = tech_name  # Just the tech name for tooltip
    elif event_type in ("law", "law_swap") and title.startswith("Adopted: "):
        law_name = title[9:]  # Strip "Adopted: "
        icon_path = get_law_icon_path(law_name)
    elif event_type == "ruler" and details:
        # Details contains "Archetype" or "Archetype - Trait"
        archetype = details.split(" - ")[0] if " - " in details else details
        icon_path = ARCHETYPE_ICONS.get(archetype)
        tooltip = f"{title} ({details})"

    if icon_path:
        return html.Img(
            src=icon_path,
            className="timeline-icon",
            title=tooltip,
            style={"width": "36px", "height": "36px", "verticalAlign": "middle"},
        )
    else:
        return html.Span(fallback_emoji)


def _format_event_item(row: pd.Series) -> html.Div:
    """Format a single event for display.

    Args:
        row: DataFrame row with event data

    Returns:
        HTML div element with formatted event
    """
    icon = row.get("icon", "")
    title = row.get("title", "")
    details = row.get("details", "")
    event_type = row.get("event_type", "")

    # Get CSS class for event type styling
    css_class = f"timeline-event timeline-event-{event_type}"

    # Try to use game icon for tech/law/ruler, fall back to emoji
    icon_element = _create_icon_element(event_type, title, icon, details)

    # Tech events: icon only (tooltip shows name)
    if event_type == "tech":
        return html.Div(
            [icon_element],
            className=css_class,
            style={"color": "#edf2f7"},
        )

    return html.Div(
        [icon_element, f"  {title}"],
        className=css_class,
        style={"color": "#edf2f7"},
    )


def get_timeline_styles() -> str:
    """Get CSS styles for timeline component.

    Returns:
        CSS string for timeline styling
    """
    return """
    .timeline-container {
        max-height: 600px;
        overflow-y: auto;
        font-size: 0.9rem;
    }

    .timeline-row {
        display: flex;
        border-bottom: 1px solid var(--bs-border-color);
        min-height: 32px;
    }

    .timeline-header {
        position: sticky;
        top: 0;
        background-color: var(--bs-body-bg);
        z-index: 10;
    }

    .timeline-cell-left,
    .timeline-cell-right {
        flex: 1;
        padding: 6px 12px;
    }

    .timeline-cell-left {
        text-align: right;
        border-right: 1px solid var(--bs-border-color);
    }

    .timeline-cell-right {
        text-align: left;
        border-left: 1px solid var(--bs-border-color);
    }

    .timeline-cell-center {
        width: 60px;
        min-width: 60px;
        text-align: center;
        font-weight: bold;
        color: #edf1f6;
        padding: 6px 4px;
        background-color: #172133;
    }

    .timeline-event {
        display: block;
        padding: 2px 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .timeline-event-icon {
        margin-right: 4px;
    }

    .timeline-event-title {
        font-size: 0.85rem;
    }

    /* Event type specific styling */
    .timeline-event-ruler {
        color: #ffd43b;
    }

    .timeline-event-death {
        color: #868e96;
    }

    .timeline-event-capital,
    .timeline-event-city {
        color: #69db7c;
    }

    .timeline-event-city_lost {
        color: #ff6b6b;
    }

    .timeline-event-tech {
        color: #74c0fc;
    }

    .timeline-event-law,
    .timeline-event-law_swap {
        color: #da77f2;
    }

    .timeline-event-wonder_start,
    .timeline-event-wonder_complete {
        color: #ffa94d;
    }

    .timeline-event-battle {
        color: #ff6b6b;
    }

    .timeline-event-uu_unlock {
        color: #20c997;
    }
    """


def expand_filter_types(filters: list[str]) -> list[str]:
    """Expand filter categories to specific event types.

    Args:
        filters: List of filter category names (tech, law, wonder, city, ruler, battle)

    Returns:
        List of specific event type strings
    """
    type_map = {
        "tech": ["tech"],
        "law": ["law", "law_swap"],
        "wonder": ["wonder_start", "wonder_complete"],
        "city": ["city", "capital", "city_lost"],
        "ruler": ["ruler", "death"],
        "battle": ["battle"],
        "uu": ["uu_unlock"],
    }

    result = []
    for f in filters:
        if f in type_map:
            result.extend(type_map[f])

    return result
