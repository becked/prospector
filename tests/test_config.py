"""Test configuration classes."""

import os
from tournament_visualizer.config import (
    Config,
    DevelopmentConfig,
    ProductionConfig,
    TestConfig,
    get_config,
)


def test_production_config_uses_port_env() -> None:
    """Production config should use PORT environment variable."""
    # Set PORT environment variable
    os.environ["PORT"] = "9999"

    config = ProductionConfig()

    assert config.APP_PORT == 9999
    assert config.APP_HOST == "0.0.0.0"
    assert config.DEBUG_MODE is False

    # Cleanup
    del os.environ["PORT"]


def test_production_config_defaults() -> None:
    """Production config should have sensible defaults."""
    # Ensure PORT is not set
    os.environ.pop("PORT", None)

    config = ProductionConfig()

    assert config.APP_PORT == 8080  # Default
    assert config.APP_HOST == "0.0.0.0"
    assert config.DEBUG_MODE is False
    assert config.CACHE_TIMEOUT == 3600


def test_production_config_uses_database_path_env() -> None:
    """Production config should use TOURNAMENT_DB_PATH environment variable."""
    os.environ["TOURNAMENT_DB_PATH"] = "/data/custom.duckdb"

    config = ProductionConfig()

    assert config.DATABASE_PATH == "/data/custom.duckdb"

    # Cleanup
    del os.environ["TOURNAMENT_DB_PATH"]


def test_get_config_auto_detects_production() -> None:
    """get_config should detect production when PORT is set."""
    # Set PORT (simulates Fly.io environment)
    os.environ["PORT"] = "8080"
    os.environ.pop("FLASK_ENV", None)  # Remove explicit FLASK_ENV

    config = get_config()

    # Should return ProductionConfig instance
    assert isinstance(config, ProductionConfig)
    assert config.APP_PORT == 8080
    assert config.DEBUG_MODE is False

    # Cleanup
    del os.environ["PORT"]


def test_get_config_respects_flask_env() -> None:
    """get_config should respect explicit FLASK_ENV."""
    os.environ["FLASK_ENV"] = "development"

    config = get_config()

    assert isinstance(config, DevelopmentConfig)

    # Cleanup
    del os.environ["FLASK_ENV"]


def test_get_config_returns_instance_not_class() -> None:
    """get_config should return a config instance, not class."""
    config = get_config("development")

    # Should be instance of Config
    assert isinstance(config, Config)

    # Should have attributes accessible
    assert hasattr(config, "APP_PORT")
    assert hasattr(config, "DATABASE_PATH")


def test_development_config_defaults() -> None:
    """Development config should have debug-friendly defaults."""
    config = DevelopmentConfig()

    assert config.DEBUG_MODE is True
    assert config.APP_HOST == "0.0.0.0"
    assert config.CACHE_TIMEOUT == 10  # Short cache for development


def test_test_config_uses_memory_database() -> None:
    """Test config should use in-memory database."""
    config = TestConfig()

    assert config.DATABASE_PATH == ":memory:"
    assert config.DEBUG_MODE is False
    assert config.CACHE_TIMEOUT == 0  # No caching for tests


def test_modebar_config_structure() -> None:
    """MODEBAR_CONFIG should have correct structure and values."""
    from tournament_visualizer.config import MODEBAR_CONFIG

    # Verify it's a dictionary
    assert isinstance(MODEBAR_CONFIG, dict)

    # Verify required keys exist
    assert "displayModeBar" in MODEBAR_CONFIG
    assert "displaylogo" in MODEBAR_CONFIG
    assert "modeBarButtonsToRemove" in MODEBAR_CONFIG

    # Verify correct values
    assert MODEBAR_CONFIG["displayModeBar"] == "hover"
    assert MODEBAR_CONFIG["displaylogo"] is False
    assert isinstance(MODEBAR_CONFIG["modeBarButtonsToRemove"], list)


def test_modebar_removes_correct_buttons() -> None:
    """MODEBAR_CONFIG should remove all buttons except zoom in/out."""
    from tournament_visualizer.config import MODEBAR_CONFIG

    removed_buttons = MODEBAR_CONFIG["modeBarButtonsToRemove"]

    # These buttons MUST be removed (we don't want them)
    expected_removed = [
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
    ]

    for button in expected_removed:
        assert button in removed_buttons, f"{button} should be removed"

    # These buttons MUST NOT be removed (we want to keep them)
    # Note: If a button isn't in modeBarButtonsToRemove, it will be shown
    assert "zoomIn2d" not in removed_buttons
    assert "zoomOut2d" not in removed_buttons
