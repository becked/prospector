"""Configuration settings for the tournament visualization application.

This module contains all configuration settings including database paths,
UI settings, and application constants.
"""

import os
from pathlib import Path
from typing import Any, Dict, List


class Config:
    """Main configuration class for the tournament visualizer."""

    # Database settings
    DATABASE_PATH = os.getenv("TOURNAMENT_DB_PATH", "data/tournament_data.duckdb")

    # Application settings
    APP_TITLE = "Old World Tournament Visualizer"
    APP_HOST = os.getenv("DASH_HOST", "127.0.0.1")
    APP_PORT = int(os.getenv("DASH_PORT", "8050"))
    DEBUG_MODE = os.getenv("DASH_DEBUG", "True").lower() == "true"

    # Data directories
    SAVES_DIRECTORY = os.getenv("SAVES_DIRECTORY", "saves")
    ASSETS_DIRECTORY = "tournament_visualizer/assets"

    # Override files
    PARTICIPANT_NAME_OVERRIDES_PATH = os.getenv(
        "PARTICIPANT_NAME_OVERRIDES_PATH", "data/participant_name_overrides.json"
    )

    # Google Drive configuration (for oversized save files)
    GOOGLE_DRIVE_API_KEY = os.getenv("GOOGLE_DRIVE_API_KEY", "")
    GOOGLE_DRIVE_FOLDER_ID = os.getenv(
        "GOOGLE_DRIVE_FOLDER_ID",
        "1ss8ToApXPY7o2syLV76i_CJdoS-lnHQk"  # Default: completed-game-save-files folder
    )

    # Google Sheets configuration (for pick order data)
    GOOGLE_SHEETS_SPREADSHEET_ID = os.getenv(
        "GOOGLE_SHEETS_SPREADSHEET_ID",
        "19t5AbJtQr5kZ62pw8FJ-r2b9LVkz01zl2GUNWkIrhAc"  # Default: OWT 25 Stats sheet
    )
    GOOGLE_SHEETS_GAMEDATA_GID = os.getenv(
        "GOOGLE_SHEETS_GAMEDATA_GID",
        "1663493966"  # Default: GAMEDATA *SPOILER WARNING* tab
    )

    # UI Configuration
    DEFAULT_PAGE_SIZE = 25
    MAX_CHART_POINTS = 1000
    CHART_HEIGHT = 400
    CHART_MARGIN = {"l": 50, "r": 50, "t": 50, "b": 50}

    # Color schemes
    PRIMARY_COLORS = [
        "#1f77b4",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467bd",
        "#8c564b",
        "#e377c2",
        "#7f7f7f",
        "#bcbd22",
        "#17becf",
    ]

    CIVILIZATION_COLORS = {
        "Assyria": "#8b0000",
        "Babylon": "#4169e1",
        "Carthage": "#800080",
        "Egypt": "#ffd700",
        "Greece": "#0000ff",
        "Persia": "#ff69b4",
        "Rome": "#dc143c",
        "Vikings": "#708090",
    }

    # Map visualization settings
    MAP_TILE_SIZE = 10
    MAP_OPACITY = 0.7
    TERRITORY_BORDER_WIDTH = 1

    # Performance settings
    CACHE_TIMEOUT = 300  # 5 minutes
    LAZY_LOADING = True
    PAGINATION_SIZE = 50

    # Chart type configurations
    CHART_CONFIGS = {
        "timeline": {"type": "line", "mode": "lines+markers", "marker_size": 6},
        "bar": {"type": "bar", "text_position": "auto"},
        "heatmap": {"type": "heatmap", "colorscale": "RdYlBu"},
        "scatter": {"type": "scatter", "mode": "markers", "marker_size": 8},
    }

    # Data validation settings
    VALIDATION_RULES = {
        "max_turns": 1000,
        "max_players": 16,
        "valid_coordinates": {"min": 0, "max": 45},
        "required_fields": ["file_name", "file_hash"],
    }


class DevelopmentConfig(Config):
    """Development-specific configuration."""

    DEBUG_MODE = True
    APP_HOST = "0.0.0.0"
    CACHE_TIMEOUT = 10  # Shorter cache for development


class ProductionConfig(Config):
    """Production-specific configuration for Fly.io and other hosts."""

    DEBUG_MODE = False

    # Bind to 0.0.0.0 to accept external connections
    APP_HOST = "0.0.0.0"

    # Longer cache for production
    CACHE_TIMEOUT = 3600  # 1 hour

    # Enable lazy loading for better performance
    LAZY_LOADING = True

    def __init__(self) -> None:
        """Initialize production config with environment-specific values."""
        super().__init__()
        # Use PORT environment variable (Fly.io sets this to 8080)
        self.APP_PORT = int(os.getenv("PORT", "8080"))
        # Database path from environment (volume mount on Fly.io)
        self.DATABASE_PATH = os.getenv("TOURNAMENT_DB_PATH", "data/tournament_data.duckdb")
        # Saves directory from environment (volume mount on Fly.io)
        self.SAVES_DIRECTORY = os.getenv("SAVES_DIRECTORY", "saves")


class TestConfig(Config):
    """Test-specific configuration."""

    DATABASE_PATH = ":memory:"  # In-memory database for tests
    DEBUG_MODE = False
    CACHE_TIMEOUT = 0  # No caching for tests


# Configuration mapping
CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestConfig,
}


def get_config(config_name: str | None = None) -> Config:
    """Get configuration object based on environment.

    Args:
        config_name: Configuration name (development/production/testing).
                    If None, auto-detects from FLASK_ENV or PORT environment variable.

    Returns:
        Configuration object (Config subclass instance)
    """
    if config_name is None:
        # Check FLASK_ENV first
        config_name = os.getenv("FLASK_ENV", "development")

        # If PORT is set (Fly.io, Heroku), assume production
        # This handles cases where FLASK_ENV isn't explicitly set
        if os.getenv("PORT") and config_name == "development":
            config_name = "production"

    config_class = CONFIG_MAP.get(config_name, DevelopmentConfig)
    return config_class()  # Return instance, not class


# Application constants
APP_CONSTANTS = {
    "VICTORY_CONDITIONS": [
        "Conquest",
        "Wonder",
        "Ambition",
        "Legitimacy",
        "Culture",
        "Science",
    ],
    "DIFFICULTY_LEVELS": ["The Able", "The Good", "The Great", "The Magnificent"],
    "TURN_STYLES": ["Simultaneous", "Sequential", "Classic"],
    "MAP_CLASSES": [
        "Continent",
        "Lakes",
        "Highlands",
        "Wetlands",
        "Inland Sea",
        "Seven Seas",
        "Donut",
        "Riversland",
        "Oasis",
    ],
    "RESOURCE_TYPES": [
        "Food",
        "Stone",
        "Wood",
        "Iron",
        "Gold",
        "Science",
        "Culture",
        "Orders",
        "Training",
        "Civics",
    ],
    "EVENT_TYPES": [
        "Battle",
        "CityFounded",
        "TechDiscovered",
        "ImprovementBuilt",
        "UnitProduced",
        "BuildingConstructed",
        "TradeRoute",
        "Diplomacy",
    ],
}


# Page configuration
PAGE_CONFIG = {
    "overview": {
        "title": "Tournament Overview",
        "icon": "📊",
        "description": "High-level tournament statistics and trends",
    },
    "matches": {
        "title": "Match Analysis",
        "icon": "🎯",
        "description": "Detailed analysis of individual matches",
    },
    "players": {
        "title": "Player Performance",
        "icon": "👥",
        "description": "Player statistics and performance metrics",
    },
    "maps": {
        "title": "Map & Territory",
        "icon": "🗺️",
        "description": "Territory control and map visualizations",
    },
}


# Layout constants
LAYOUT_CONSTANTS = {
    "SIDEBAR_WIDTH": "250px",
    "CONTENT_PADDING": "20px",
    "CARD_MARGIN": "10px",
    "FILTER_HEIGHT": "auto",
    "CHART_MIN_HEIGHT": "300px",
    "TABLE_PAGE_SIZE": 20,
}


# Filter options
FILTER_OPTIONS = {
    "date_ranges": [
        {"label": "Last 7 days", "value": 7},
        {"label": "Last 30 days", "value": 30},
        {"label": "Last 90 days", "value": 90},
        {"label": "All time", "value": "all"},
    ],
    "match_durations": [
        {"label": "Short (≤50 turns)", "value": "short"},
        {"label": "Medium (51-100 turns)", "value": "medium"},
        {"label": "Long (101-150 turns)", "value": "long"},
        {"label": "Very Long (>150 turns)", "value": "very_long"},
    ],
    "player_counts": [
        {"label": "2 players", "value": 2},
        {"label": "3 players", "value": 3},
        {"label": "4 players", "value": 4},
        {"label": "5+ players", "value": 5},
    ],
}


# Default chart layouts
DEFAULT_CHART_LAYOUT = {
    "margin": Config.CHART_MARGIN,
    "height": Config.CHART_HEIGHT,
    "showlegend": True,
    "legend": {"x": 0, "y": 1, "bgcolor": "rgba(255,255,255,0.8)"},
    "font": {"size": 12},
    "plot_bgcolor": "rgba(0,0,0,0)",
    "paper_bgcolor": "rgba(0,0,0,0)",
}

# Plotly modebar configuration
# Show modebar only on hover with just zoom in/out buttons
MODEBAR_CONFIG = {
    "displayModeBar": "hover",  # Show only on hover
    "displaylogo": False,  # Hide Plotly logo
    "modeBarButtonsToRemove": [
        # Remove ALL buttons except zoomIn2d and zoomOut2d
        "pan2d",
        "zoom2d",
        "select2d",
        "lasso2d",
        "autoScale2d",
        "resetScale2d",
        "hoverClosestCartesian",
        "hoverCompareCartesian",
        "toggleSpikelines",
        "toggleHover",
        "toImage",
    ],
}

# Export civilization colors at module level for easier import
CIVILIZATION_COLORS = Config.CIVILIZATION_COLORS


# Error messages
ERROR_MESSAGES = {
    "no_data": "No data available for the selected filters.",
    "database_error": "Database connection error. Please try again.",
    "file_not_found": "Tournament file not found.",
    "invalid_match": "Invalid match ID provided.",
    "parsing_error": "Error parsing tournament data.",
}


# Success messages
SUCCESS_MESSAGES = {
    "import_complete": "Tournament data imported successfully.",
    "database_updated": "Database updated successfully.",
    "export_complete": "Data exported successfully.",
}


def get_app_constants() -> Dict[str, Any]:
    """Get all application constants.

    Returns:
        Dictionary containing all constants
    """
    return {
        "APP_CONSTANTS": APP_CONSTANTS,
        "PAGE_CONFIG": PAGE_CONFIG,
        "LAYOUT_CONSTANTS": LAYOUT_CONSTANTS,
        "FILTER_OPTIONS": FILTER_OPTIONS,
        "ERROR_MESSAGES": ERROR_MESSAGES,
        "SUCCESS_MESSAGES": SUCCESS_MESSAGES,
    }


def validate_config(config: Config) -> List[str]:
    """Validate configuration settings.

    Args:
        config: Configuration object to validate

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Check database path is writable
    try:
        db_path = Path(config.DATABASE_PATH)
        if db_path.exists() and not os.access(db_path, os.W_OK):
            errors.append(f"Database path not writable: {config.DATABASE_PATH}")
    except Exception as e:
        errors.append(f"Invalid database path: {e}")

    # Check saves directory exists
    saves_path = Path(config.SAVES_DIRECTORY)
    if not saves_path.exists():
        errors.append(f"Saves directory does not exist: {config.SAVES_DIRECTORY}")

    # Validate port range
    if not (1024 <= config.APP_PORT <= 65535):
        errors.append(f"Invalid port number: {config.APP_PORT}")

    # Validate chart settings
    if config.MAX_CHART_POINTS <= 0:
        errors.append("MAX_CHART_POINTS must be positive")

    if config.CHART_HEIGHT <= 0:
        errors.append("CHART_HEIGHT must be positive")

    return errors
