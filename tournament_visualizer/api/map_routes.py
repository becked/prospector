"""Flask routes for the interactive map viewer.

Provides:
- /map/viewer/{match_id} - HTML page with Pixi.js map viewer
- /api/map/territories/{match_id}/{turn} - JSON territory data
- /api/map/turn-range/{match_id} - JSON turn range for a match
"""

import logging
from typing import Any

import pandas as pd
from flask import jsonify, render_template, request

from tournament_visualizer.api import map_api
from tournament_visualizer.config import get_family_class
from tournament_visualizer.data.queries import get_queries
from tournament_visualizer.nation_colors import get_nation_map_color

logger = logging.getLogger(__name__)


@map_api.route("/hex_test_<config_name>.html")
def hex_test(config_name: str) -> str:
    """Serve hex tiling test pages."""
    return render_template(f"hex_test_{config_name}.html")


@map_api.route("/hex_test_masked.html")
def hex_test_masked() -> str:
    """Serve masked hex tiling test page."""
    return render_template("hex_test_masked.html")


@map_api.route("/map/viewer/<int:match_id>")
def map_viewer(match_id: int) -> str:
    """Render the Pixi.js map viewer page.

    Args:
        match_id: The match ID to display

    Returns:
        Rendered HTML template
    """
    queries = get_queries()

    # Get players for this match to build the title
    try:
        # Use the territory query to get player info (it already has player names)
        min_turn, max_turn = queries.get_territory_turn_range(match_id)
        df = queries.get_territory_map_full(match_id, max_turn)

        if df.empty:
            return render_template(
                "map_viewer.html",
                match_id=match_id,
                error="Match not found or no territory data",
                match_title="Match Not Found",
            )

        # Get unique players
        players_df = df[df["owner_player_id"].notna()].drop_duplicates(
            subset=["owner_player_id"]
        )
        player_names = players_df["player_name"].tolist()

        if len(player_names) >= 2:
            match_title = f"{player_names[0]} vs {player_names[1]}"
        elif len(player_names) == 1:
            match_title = f"{player_names[0]}'s Match"
        else:
            match_title = f"Match {match_id}"

    except Exception as e:
        logger.error(f"Error getting match info for map viewer: {e}")
        return render_template(
            "map_viewer.html",
            match_id=match_id,
            error=f"Error loading match: {str(e)}",
            match_title="Error",
        )

    return render_template(
        "map_viewer.html",
        match_id=match_id,
        match_title=match_title,
        error=None,
    )


@map_api.route("/api/map/turn-range/<int:match_id>")
def api_turn_range(match_id: int) -> tuple[Any, int]:
    """Get the turn range for a match.

    Args:
        match_id: The match ID

    Returns:
        JSON with min_turn and max_turn
    """
    queries = get_queries()

    try:
        min_turn, max_turn = queries.get_territory_turn_range(match_id)
        return jsonify({
            "match_id": match_id,
            "min_turn": min_turn,
            "max_turn": max_turn,
        }), 200
    except Exception as e:
        logger.error(f"Error getting turn range for match {match_id}: {e}")
        return jsonify({"error": str(e)}), 500


@map_api.route("/api/map/territories/<int:match_id>/<int:turn_number>")
def api_territories(match_id: int, turn_number: int) -> tuple[Any, int]:
    """Get complete territory data for a match at a specific turn.

    Args:
        match_id: The match ID
        turn_number: The turn number to fetch

    Returns:
        JSON with tiles, players, and map info
    """
    queries = get_queries()

    try:
        # Get full territory data
        df = queries.get_territory_map_full(match_id, turn_number)

        if df.empty:
            return jsonify({
                "error": "No territory data found",
                "match_id": match_id,
                "turn_number": turn_number,
            }), 404

        # Calculate map dimensions from data
        max_x = int(df["x_coordinate"].max()) + 1
        max_y = int(df["y_coordinate"].max()) + 1

        # Build player info with colors
        players = []
        player_colors = {}
        for _, row in df[df["owner_player_id"].notna()].drop_duplicates(
            subset=["owner_player_id"]
        ).iterrows():
            player_id = int(row["owner_player_id"])
            civilization = row.get("civilization", "")
            color = get_nation_map_color(civilization) if civilization else "#808080"
            player_colors[player_id] = color
            players.append({
                "player_id": player_id,
                "name": row.get("player_name", f"Player {player_id}"),
                "civilization": civilization,
                "color": color,
            })

        # Handle same-nation case (player 2 gets green)
        if len(players) == 2:
            if players[0]["civilization"] and players[1]["civilization"]:
                if players[0]["civilization"].upper() == players[1]["civilization"].upper():
                    players[1]["color"] = "#228B22"  # Forest green
                    player_colors[players[1]["player_id"]] = "#228B22"

        # Build tiles array
        tiles = []
        for _, row in df.iterrows():
            # Handle pandas NaN values - NaN is not valid JSON, must convert to None
            def safe_str(val: Any) -> str | None:
                return val if pd.notna(val) else None

            def safe_int(val: Any) -> int | None:
                return int(val) if pd.notna(val) else None

            tile = {
                "x": int(row["x_coordinate"]),
                "y": int(row["y_coordinate"]),
                "terrain": safe_str(row.get("terrain_type")),
                "owner": safe_int(row.get("owner_player_id")),
                "improvement": safe_str(row.get("improvement_type")),
                "specialist": safe_str(row.get("specialist_type")),
                "resource": safe_str(row.get("resource_type")),
                "road": bool(row.get("has_road", False)),
            }
            pop_value = safe_int(row.get("population"))

            # Add city info if this is a city tile
            city_name = row.get("city_name")
            if city_name and pd.notna(city_name):
                family_name = row.get("family_name")
                family_class = None
                if family_name and pd.notna(family_name):
                    family_class = get_family_class(family_name)
                    if family_class == "Unknown":
                        family_class = None

                tile["city"] = {
                    "name": city_name,
                    "population": pop_value,
                    "is_capital": bool(row.get("is_capital", False)),
                    "family_class": family_class,
                    "is_family_seat": bool(row.get("is_family_seat", False)),
                }
            else:
                tile["city"] = None

            tiles.append(tile)

        return jsonify({
            "match_id": match_id,
            "turn_number": turn_number,
            "map_info": {
                "width": max_x,
                "height": max_y,
                "total_tiles": len(tiles),
            },
            "players": players,
            "tiles": tiles,
        }), 200

    except Exception as e:
        logger.error(f"Error getting territories for match {match_id} turn {turn_number}: {e}")
        return jsonify({"error": str(e)}), 500
