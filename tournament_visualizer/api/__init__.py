"""Flask API blueprint for the tournament visualizer.

This module provides Flask routes for the interactive map viewer and related APIs.
"""

from flask import Blueprint

# Create the API blueprint
map_api = Blueprint(
    "map_api",
    __name__,
    url_prefix="",  # Routes define their own prefixes
    template_folder="../templates",
    static_folder="../static",
)

# Import routes to register them with the blueprint
from tournament_visualizer.api import map_routes  # noqa: F401, E402
