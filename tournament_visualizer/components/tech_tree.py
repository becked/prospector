"""Tech tree visualization component using Cytoscape."""

from typing import Any, Dict, List, Optional, Set, Tuple

import dash_cytoscape as cyto
from dash import html

from tournament_visualizer.tech_tree import PREREQUISITES, TECHS
from tournament_visualizer.theme import DARK_THEME

# Node dimensions and spacing (compact for side-by-side display)
NODE_WIDTH = 55
NODE_HEIGHT = 25
COL_SPACING = 70
ROW_SPACING = 35

# Colors for tech states
TECH_RESEARCHED_BG = DARK_THEME["accent_success"]  # Green
TECH_RESEARCHED_BORDER = "#3d9959"  # Darker green
TECH_LOCKED_BG = DARK_THEME["bg_medium"]  # Blue-gray
TECH_LOCKED_BORDER = DARK_THEME["bg_light"]  # Lighter blue-gray
EDGE_COLOR = "rgba(255, 255, 255, 0.3)"
EDGE_RESEARCHED_COLOR = DARK_THEME["accent_success"]


def get_techs_at_turn(tech_timeline_df, player_id: int, turn: int) -> Set[str]:
    """Get set of techs researched by a player at a given turn.

    Args:
        tech_timeline_df: DataFrame with columns player_id, turn_number, tech_name
        player_id: Player ID to filter for
        turn: Turn number (inclusive)

    Returns:
        Set of tech IDs researched by that turn (only techs in our TECHS dict)
    """
    if tech_timeline_df is None or tech_timeline_df.empty:
        return set()

    player_techs = tech_timeline_df[
        (tech_timeline_df["player_id"] == player_id) &
        (tech_timeline_df["turn_number"] <= turn)
    ]

    # Clean tech names (remove quotes from JSON extraction) and filter to known techs
    tech_names = set()
    for tech in player_techs["tech_name"].tolist():
        # Strip quotes if present (from json_extract)
        clean_tech = tech.strip('"') if isinstance(tech, str) else tech
        # Only include techs that are in our tech tree
        if clean_tech in TECHS:
            tech_names.add(clean_tech)

    return tech_names


def build_cytoscape_elements(researched: Optional[Set[str]] = None) -> List[Dict]:
    """Build Cytoscape elements from tech tree data.

    Args:
        researched: Set of tech IDs that have been researched

    Returns:
        List of Cytoscape elements (nodes and edges)
    """
    if researched is None:
        researched = set()

    elements = []

    # Create nodes - skip bonus/resource techs for cleaner display
    for tech_id, (name, col, row) in TECHS.items():
        # Skip techs without positions (event bonuses)
        if col is None or row is None:
            continue

        # Skip bonus techs - they clutter the display
        if "BONUS" in tech_id or "RESOURCE" in tech_id:
            continue

        is_researched = tech_id in researched

        # Calculate position
        pos_x = col * COL_SPACING + NODE_WIDTH // 2
        pos_y = row * ROW_SPACING + NODE_HEIGHT // 2

        elements.append({
            "data": {
                "id": tech_id,
                "label": name,
            },
            "position": {
                "x": pos_x,
                "y": pos_y,
            },
            "classes": "researched" if is_researched else "locked",
        })

    # Create edges - only for main techs (not bonus)
    valid_tech_ids = {
        tech_id for tech_id, (_, col, row) in TECHS.items()
        if col is not None and row is not None
        and "BONUS" not in tech_id and "RESOURCE" not in tech_id
    }

    for prereq, unlocks in PREREQUISITES:
        # Skip edges involving bonus techs
        if prereq not in valid_tech_ids or unlocks not in valid_tech_ids:
            continue

        # Only mark edge as researched if both techs are researched
        both_researched = prereq in researched and unlocks in researched
        elements.append({
            "data": {
                "source": prereq,
                "target": unlocks,
            },
            "classes": "edge-researched" if both_researched else "edge-locked",
        })

    return elements


# Cytoscape stylesheet for tech tree appearance
TECH_TREE_STYLESHEET = [
    # Base node style
    {
        "selector": "node",
        "style": {
            "shape": "roundrectangle",
            "width": NODE_WIDTH,
            "height": NODE_HEIGHT,
            "label": "data(label)",
            "text-valign": "center",
            "text-halign": "center",
            "font-size": "9px",
            "font-weight": "500",
            "text-wrap": "wrap",
            "text-max-width": str(NODE_WIDTH - 4),
            "color": DARK_THEME["text_primary"],
            "text-outline-color": "transparent",
            "text-outline-width": 0,
        },
    },
    # Researched tech style
    {
        "selector": "node.researched",
        "style": {
            "background-color": TECH_RESEARCHED_BG,
            "border-color": TECH_RESEARCHED_BORDER,
            "border-width": 2,
        },
    },
    # Locked tech style
    {
        "selector": "node.locked",
        "style": {
            "background-color": TECH_LOCKED_BG,
            "border-color": TECH_LOCKED_BORDER,
            "border-width": 2,
        },
    },
    # Base edge style
    {
        "selector": "edge",
        "style": {
            "width": 2,
            "curve-style": "bezier",
            "target-arrow-shape": "triangle",
            "target-arrow-color": EDGE_COLOR,
            "line-color": EDGE_COLOR,
            "arrow-scale": 0.8,
        },
    },
    # Researched edge style
    {
        "selector": "edge.edge-researched",
        "style": {
            "line-color": EDGE_RESEARCHED_COLOR,
            "target-arrow-color": EDGE_RESEARCHED_COLOR,
        },
    },
]


def create_tech_tree_cytoscape(
    researched: Optional[Set[str]] = None,
    cytoscape_id: str = "tech-tree",
) -> cyto.Cytoscape:
    """Create a Cytoscape component for the tech tree.

    Args:
        researched: Set of tech IDs that have been researched
        cytoscape_id: ID for the Cytoscape component

    Returns:
        Cytoscape component
    """
    elements = build_cytoscape_elements(researched)

    # Calculate dimensions based on tech tree size
    max_col = max(col for _, (_, col, _) in TECHS.items())
    max_row = max(row for _, (_, _, row) in TECHS.items())
    width = (max_col + 1) * COL_SPACING + NODE_WIDTH
    height = (max_row + 1) * ROW_SPACING + NODE_HEIGHT

    return cyto.Cytoscape(
        id=cytoscape_id,
        elements=elements,
        stylesheet=TECH_TREE_STYLESHEET,
        layout={"name": "preset"},  # Use positions defined in elements
        style={
            "width": "100%",
            "height": f"{height}px",
            "background-color": DARK_THEME["bg_dark"],
        },
        minZoom=0.5,
        maxZoom=2,
        userZoomingEnabled=True,
        userPanningEnabled=True,
        boxSelectionEnabled=False,
    )


def create_tech_tree_card(
    player_name: str,
    researched: Optional[Set[str]] = None,
    cytoscape_id: str = "tech-tree",
) -> html.Div:
    """Create a card containing the tech tree for a player.

    Args:
        player_name: Name to display in card header
        researched: Set of tech IDs that have been researched
        cytoscape_id: ID for the Cytoscape component

    Returns:
        Div containing the tech tree card
    """
    cytoscape = create_tech_tree_cytoscape(researched, cytoscape_id)

    # Count stats
    total_techs = len(TECHS)
    researched_count = len(researched) if researched else 0

    return html.Div([
        html.Div([
            html.Span(player_name, className="fw-bold"),
            html.Span(
                f" ({researched_count}/{total_techs} techs)",
                className="text-muted ms-2",
            ),
        ], className="mb-2"),
        cytoscape,
    ])
