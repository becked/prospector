"""Configuration settings for the tournament visualization application.

This module contains all configuration settings including database paths,
UI settings, and application constants.
"""

import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


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
    # Relative to app.py location (tournament_visualizer/)
    ASSETS_DIRECTORY = "assets"

    # Override files
    PARTICIPANT_NAME_OVERRIDES_PATH = os.getenv(
        "PARTICIPANT_NAME_OVERRIDES_PATH", "data/participant_name_overrides.json"
    )

    # Google Drive configuration (for oversized save files)
    GOOGLE_DRIVE_API_KEY = os.getenv("GOOGLE_DRIVE_API_KEY", "")
    GOOGLE_DRIVE_FOLDER_ID = os.getenv(
        "GOOGLE_DRIVE_FOLDER_ID",
        "1ss8ToApXPY7o2syLV76i_CJdoS-lnHQk",  # Default: completed-game-save-files folder
    )

    # Google Sheets configuration (for pick order data)
    GOOGLE_SHEETS_SPREADSHEET_ID = os.getenv(
        "GOOGLE_SHEETS_SPREADSHEET_ID",
        "19t5AbJtQr5kZ62pw8FJ-r2b9LVkz01zl2GUNWkIrhAc",  # Default: OWT 25 Stats sheet
    )
    GOOGLE_SHEETS_GAMEDATA_GID = os.getenv(
        "GOOGLE_SHEETS_GAMEDATA_GID", "1663493966"  # Default: GAMEDATA tab
    )

    # Anthropic API configuration (for match narrative generation)
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

    # UI Configuration
    DEFAULT_PAGE_SIZE = 25
    MAX_CHART_POINTS = 1000
    CHART_HEIGHT = 400
    CHART_MARGIN = {"l": 50, "r": 50, "t": 50, "b": 50}

    # Color schemes
    PRIMARY_COLORS = [
        "#4aba6e",  # Green (accent_success) - replaces blue for dark theme
        "#ff7f0e",  # Orange
        "#64b5f6",  # Light blue (accent_primary)
        "#d62728",  # Red
        "#9467bd",  # Purple
        "#8c564b",  # Brown
        "#e377c2",  # Pink
        "#7f7f7f",  # Gray
        "#bcbd22",  # Yellow-green
        "#4dd0e1",  # Teal (accent_info)
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
        self.DATABASE_PATH = os.getenv(
            "TOURNAMENT_DB_PATH", "data/tournament_data.duckdb"
        )
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


# Cognomen base legitimacy values
# Values based on in-game mechanics: range from 0 (New) to 100 (Great)
# Negative cognomens possible for poor performance
COGNOMEN_LEGITIMACY: Dict[str, int] = {
    # Starting/Low tier
    "New": 0,
    "Able": 10,
    "Capable": 10,
    "Ready": 10,
    # Mid-low tier
    "Ambitious": 20,
    "Good": 20,
    "Just": 20,
    "Brave": 30,
    "Noble": 30,
    "Valiant": 30,
    "Warrior": 30,
    # Mid tier
    "Devout": 40,
    "Intrepid": 40,
    "Learned": 40,
    "Mason": 40,
    "Settler": 40,
    "Strong": 40,
    "Wise": 40,
    # Mid-high tier
    "Beloved": 50,
    "Brilliant": 50,
    "Explorer": 50,
    "Fountainhead": 50,
    "Holy": 50,
    "Keystone": 50,
    "Pioneer": 50,
    # High tier
    "Architect": 60,
    "Drillmaster": 60,
    "Enlightened": 60,
    "Magnificent": 60,
    "Subjugator": 60,
    "Victorious": 60,
    # Very high tier
    "Conqueror": 80,
    "Glorious": 80,
    "Invincible": 80,
    "Lion": 80,
    "Mighty": 80,
    # Top tier
    "Great": 100,
    # Age-based cognomens
    "Old": 40,
    "Ancient": 50,
    # Negative cognomens
    "Bloody": -20,
    "Foolish": -10,
    "Unfortunate": -10,
    "Unready": -10,
}

# Cognomen display names (for formatting "X the Lion")
COGNOMEN_DISPLAY_NAMES: Dict[str, str] = {
    "Able": "the Able",
    "Ambitious": "the Ambitious",
    "Ancient": "the Ancient",
    "Architect": "the Architect",
    "Beloved": "the Beloved",
    "Bloody": "the Bloody",
    "Brave": "the Brave",
    "Brilliant": "the Brilliant",
    "Capable": "the Capable",
    "Conqueror": "the Conqueror",
    "Devout": "the Devout",
    "Drillmaster": "the Drillmaster",
    "Enlightened": "the Enlightened",
    "Explorer": "the Explorer",
    "Foolish": "the Foolish",
    "Fountainhead": "the Fountainhead",
    "Glorious": "the Glorious",
    "Good": "the Good",
    "Great": "the Great",
    "Holy": "the Holy",
    "Intrepid": "the Intrepid",
    "Invincible": "the Invincible",
    "Just": "the Just",
    "Keystone": "the Keystone",
    "Learned": "the Learned",
    "Lion": "the Lion",
    "Magnificent": "the Magnificent",
    "Mason": "the Mason",
    "Mighty": "the Mighty",
    "New": "the New",
    "Noble": "the Noble",
    "Old": "the Old",
    "Pioneer": "the Pioneer",
    "Ready": "the Ready",
    "Settler": "the Settler",
    "Strong": "the Strong",
    "Subjugator": "the Subjugator",
    "Unfortunate": "the Unfortunate",
    "Unready": "the Unready",
    "Valiant": "the Valiant",
    "Victorious": "the Victorious",
    "Warrior": "the Warrior",
    "Wise": "the Wise",
}


# Family class mapping
# Maps family internal names to their class (game data is static)
FAMILY_CLASS_MAP: Dict[str, str] = {
    # Assyria
    "FAMILY_SARGONID": "Champions",
    "FAMILY_TUDIYA": "Hunters",
    "FAMILY_ADASI": "Patrons",
    "FAMILY_ERISHUM": "Clerics",
    # Babylon
    "FAMILY_KASSITE": "Hunters",
    "FAMILY_CHALDEAN": "Artisans",
    "FAMILY_ISIN": "Traders",
    "FAMILY_AMORITE": "Sages",
    # Carthage
    "FAMILY_BARCID": "Riders",
    "FAMILY_MAGONID": "Artisans",
    "FAMILY_HANNONID": "Traders",
    "FAMILY_DIDONIAN": "Statesmen",
    # Egypt
    "FAMILY_RAMESSIDE": "Riders",
    "FAMILY_SAITE": "Landowners",
    "FAMILY_AMARNA": "Clerics",
    "FAMILY_THUTMOSID": "Sages",
    # Greece
    "FAMILY_ARGEAD": "Champions",
    "FAMILY_CYPSELID": "Artisans",
    "FAMILY_SELEUCID": "Patrons",
    "FAMILY_ALCMAEONID": "Sages",
    # Persia
    "FAMILY_SASANID": "Clerics",
    "FAMILY_MIHRANID": "Hunters",
    "FAMILY_ARSACID": "Riders",
    "FAMILY_ACHAEMENID": "Statesmen",
    # Rome
    "FAMILY_FABIUS": "Champions",
    "FAMILY_CLAUDIUS": "Landowners",
    "FAMILY_VALERIUS": "Patrons",
    "FAMILY_JULIUS": "Statesmen",
    # Hatti
    "FAMILY_KUSSARAN": "Riders",
    "FAMILY_NENASSAN": "Landowners",
    "FAMILY_ZALPUWAN": "Patrons",
    "FAMILY_HATTUSAN": "Traders",
    # Nubia
    "FAMILY_YAM": "Hunters",
    "FAMILY_IRTJET": "Artisans",
    "FAMILY_WAWAT": "Traders",
    "FAMILY_SETJU": "Landowners",
    # Aksum
    "FAMILY_AKSUM_AGAW": "Champions",
    "FAMILY_AKSUM_AGAZI": "Traders",
    "FAMILY_AKSUM_TIGRAYAN": "Clerics",
    "FAMILY_AKSUM_BARYA": "Patrons",
}

# Family class color mapping for charts
FAMILY_CLASS_COLORS: Dict[str, str] = {
    "Champions": "#e63946",  # Red - aggressive military
    "Riders": "#f4a261",  # Orange - mobile cavalry
    "Hunters": "#2a9d8f",  # Teal - wilderness/nature
    "Artisans": "#e9c46a",  # Gold - crafting/production
    "Traders": "#457b9d",  # Blue - commerce
    "Sages": "#9b5de5",  # Purple - knowledge/wisdom
    "Statesmen": "#264653",  # Dark blue - politics/governance
    "Patrons": "#a8dadc",  # Light blue - support/nobility
    "Clerics": "#f1faee",  # Off-white - religious
    "Landowners": "#8d6e63",  # Brown - land/agriculture
}


def get_family_class_color(family_class: str) -> str:
    """Get the color for a family class.

    Args:
        family_class: Class name (e.g., "Champions", "Riders")

    Returns:
        Hex color string, or gray fallback if not found
    """
    return FAMILY_CLASS_COLORS.get(family_class, "#808080")


def get_family_class(family_name: str) -> str:
    """Get the class name for a family.

    Args:
        family_name: Internal family name (e.g., FAMILY_BARCID)

    Returns:
        Human-readable class name (e.g., "Riders"), or "Unknown" if not found
    """
    return FAMILY_CLASS_MAP.get(family_name, "Unknown")


def format_family_display_name(family_name: str) -> str:
    """Format a family name for display.

    Converts FAMILY_BARCID to "Barcid".

    Args:
        family_name: Internal family name

    Returns:
        Human-readable family name
    """
    if family_name.startswith("FAMILY_"):
        name = family_name[7:]  # Remove "FAMILY_" prefix
    else:
        name = family_name

    # Handle AKSUM families (e.g., AKSUM_TIGRAYAN -> Tigrayan)
    if name.startswith("AKSUM_"):
        name = name[6:]

    return name.replace("_", " ").title()


def get_cognomen_decay_rate(generations_ago: int) -> float:
    """Calculate decay rate for cognomen legitimacy based on how many rulers ago.

    Legitimacy from previous leaders' cognomens decays:
    - Current ruler: 100%
    - Previous ruler: 50%
    - Two rulers ago: 33%
    - Three rulers ago: 25%
    - etc.

    Args:
        generations_ago: 0 for current ruler, 1 for previous, etc.

    Returns:
        Decay multiplier (1.0 for current, 0.5 for previous, etc.)
    """
    if generations_ago < 0:
        return 0.0
    return 1.0 / (generations_ago + 1)


def format_event_type_display(event_type: str) -> str:
    """Format an event type for display.

    Converts MEMORYFAMILY_FOUNDED_FAMILY_SEAT to "Founded Family Seat".

    Args:
        event_type: Raw event type string

    Returns:
        Human-readable event name
    """
    # Remove common prefixes
    name = event_type
    for prefix in ["MEMORYFAMILY_", "MEMORYRELIGION_", "MEMORYTRIBE_",
                   "MEMORYPLAYER_", "MEMORYCHARACTER_"]:
        if name.startswith(prefix):
            name = name[len(prefix):]
            break

    # Convert underscores to spaces and title case
    name = name.replace("_", " ").title()

    return name


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


# Default chart layouts - uses dark theme colors
from tournament_visualizer.theme import CHART_THEME

DEFAULT_CHART_LAYOUT = {
    "margin": Config.CHART_MARGIN,
    "height": Config.CHART_HEIGHT,
    "showlegend": True,
    "legend": {
        "x": 0,
        "y": 1,
        "bgcolor": CHART_THEME["legend_bgcolor"],
        "bordercolor": CHART_THEME["legend_bordercolor"],
        "borderwidth": 1,
        "font": {"color": CHART_THEME["font_color"]},
    },
    "font": {"size": 12, "color": CHART_THEME["font_color"]},
    "plot_bgcolor": CHART_THEME["plot_bgcolor"],
    "paper_bgcolor": CHART_THEME["paper_bgcolor"],
    # Hover tooltip styling (critical - cannot be done via CSS)
    "hoverlabel": {
        "bgcolor": CHART_THEME["hoverlabel_bgcolor"],
        "bordercolor": CHART_THEME["hoverlabel_bordercolor"],
        "font": {"color": CHART_THEME["hoverlabel_font_color"]},
    },
    "xaxis": {
        "gridcolor": CHART_THEME["gridcolor"],
        "tickfont": {"color": CHART_THEME["font_color"]},
        "title_font": {"color": CHART_THEME["font_color"]},
    },
    "yaxis": {
        "gridcolor": CHART_THEME["gridcolor"],
        "tickfont": {"color": CHART_THEME["font_color"]},
        "title_font": {"color": CHART_THEME["font_color"]},
    },
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
