"""Main Dash application for the tournament visualizer.

This module creates and configures the main Dash application with multi-page
support for tournament data visualization.
"""

import atexit
import logging
import os
import signal
import sys

# Set up logging to both file and console
from datetime import datetime
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, dcc, html

from tournament_visualizer.config import get_config, validate_config
from tournament_visualizer.data.database import get_database


def setup_logging() -> str:
    """Set up logging configuration. Only configures once per process."""
    # Check if logging is already configured
    if logging.getLogger().handlers:
        return "Already configured"

    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Create a unique log filename with timestamp
    log_filename = (
        log_dir
        / f"tournament_visualizer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )

    # Configure logging with both file and console handlers
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler(),  # Console output
        ],
    )
    return str(log_filename)


# Only setup logging when running as main module
if __name__ == "__main__":
    log_file = setup_logging()
    logger = logging.getLogger(__name__)
    if log_file != "Already configured":
        logger.info(f"Logging to file: {log_file}")
else:
    logger = logging.getLogger(__name__)

# Get configuration
config = get_config()

# Validate configuration
config_errors = validate_config(config)
if config_errors:
    logger.error("Configuration errors found:")
    for error in config_errors:
        logger.error(f"  - {error}")
    sys.exit(1)

# CSS for styling Dash core components with Bootstrap themes
# See: https://github.com/AnnMarieW/dash-bootstrap-templates
DBC_CSS = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"

# Initialize Dash app with Bootstrap theme
app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP, DBC_CSS],
    suppress_callback_exceptions=True,
    title=config.APP_TITLE,
    update_title="Loading...",
    assets_folder=config.ASSETS_DIRECTORY,
)

# Set dark theme on HTML element for Bootstrap 5.3 color mode
# Style block after {%css%} ensures our overrides load after Bootstrap
app.index_string = """<!DOCTYPE html>
<html data-bs-theme="dark">
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            /* Override Bootstrap dark theme with dark blue palette */
            [data-bs-theme=dark] {
                --bs-body-bg: #0e1b2e;
                --bs-body-color: #edf2f7;
                --bs-secondary-bg: #364c6b;
                --bs-tertiary-bg: #3a5a7e;
                --bs-card-bg: #364c6b;
                --bs-card-cap-bg: #3a5a7e;
                --bs-modal-bg: #364c6b;
                --bs-dropdown-bg: #3a5a7e;
                --bs-border-color: rgba(255, 255, 255, 0.18);
                --bs-link-color: #c8d4e3;
                --bs-link-hover-color: #ffffff;
            }
            body {
                background-color: #0e1b2e !important;
            }
            .navbar {
                background-color: #3b4c69 !important;
            }
            /* DataTable links - must be here to override Dash CSS */
            .dash-table-container a,
            .dash-spreadsheet-container a,
            .dash-cell a {
                color: #c8d4e3 !important;
                text-decoration: underline;
            }
            .dash-table-container a:hover,
            .dash-spreadsheet-container a:hover,
            .dash-cell a:hover {
                color: #ffffff !important;
            }
            /* DataTable filter inputs - override dbc.css --bs-body-bg variable */
            .dbc .dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner th.dash-filter input:not([type=radio]):not([type=checkbox]) {
                --bs-body-bg: #41597b;
                background-color: #41597b !important;
                color: #edf2f7 !important;
            }
            .dbc .dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner th.dash-filter input::placeholder {
                color: #c8d4e3 !important;
            }
            /* Chat input - remove focus glow and placeholder on focus */
            #chat-input:focus {
                box-shadow: none !important;
                outline: none !important;
            }
            #chat-input:focus::placeholder {
                color: transparent !important;
            }
            /* DataTable sort indicators - match header text color */
            .dash-table-container .column-header--sort {
                color: #edf2f7 !important;
            }
            /* Export buttons - light grey to match borders */
            .btn-outline-primary {
                border-color: #c8d4e3 !important;
                color: #c8d4e3 !important;
            }
            .btn-outline-primary:hover {
                background-color: #c8d4e3 !important;
                border-color: #c8d4e3 !important;
                color: #0e1b2e !important;
            }
            /* Plotly modebar icons - light color for dark theme */
            .modebar-btn path {
                fill: #c8d4e3 !important;
            }
            .modebar-btn:hover path {
                fill: #ffffff !important;
            }
            /* Switch/checkbox toggles - pointer cursor on hover */
            .form-check,
            .form-check-label,
            .form-check-input {
                cursor: pointer;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>"""

# Set up the app layout
app.layout = dbc.Container(
    [
        # Navigation header
        dbc.NavbarSimple(
            children=[
                dbc.Nav(
                    [
                        dbc.NavItem(
                            dbc.NavLink(
                                "Overview",
                                href="/",
                                active="exact",
                            )
                        ),
                        dbc.NavItem(
                            dbc.NavLink(
                                "Matches",
                                href="/matches",
                                active="exact",
                            )
                        ),
                        dbc.NavItem(
                            dbc.NavLink(
                                "Players",
                                href="/players",
                                active="exact",
                            )
                        ),
                        dbc.NavItem(
                            dbc.NavLink(
                                "Maps",
                                href="/maps",
                                active="exact",
                            )
                        ),
                        dbc.NavItem(
                            dbc.NavLink(
                                ["Chat", html.Sup("beta", className="ms-1", style={"fontSize": "0.6em"})],
                                href="/chat",
                                active="exact",
                            )
                        ),
                    ],
                    className="me-auto",
                    navbar=True,
                ),
                # Database status indicator
                dbc.Badge(
                    id="db-status-badge",
                    color="secondary",
                    className="me-2 align-self-center",
                ),
            ],
            brand=config.APP_TITLE,
            brand_href="/",
            dark=True,  # Sets light text color
            style={"backgroundColor": "#3b4c69"},  # Custom dark blue background
            className="mb-4",
        ),
        # Main content area - no Loading wrapper to avoid visual "reload" on tab switches
        html.Div([dash.page_container]),
        # Hidden div to store app state
        dcc.Store(id="app-state", data={}),
    ],
    fluid=True,
    className="dbc px-4",
)


@callback(
    Output("db-status-badge", "children"),
    Output("db-status-badge", "color"),
    Input("_pages_location", "pathname"),
)
def update_database_status(pathname: str) -> tuple[str, str]:
    """Update the database status indicator.

    Args:
        pathname: Current page path (triggers on page load)

    Returns:
        Tuple of (badge_text, badge_color)
    """
    try:
        db = get_database()

        # Use the context manager to properly handle the connection
        with db.get_connection() as conn:
            result = conn.execute("SELECT COUNT(*) FROM matches").fetchone()
            match_count = result[0] if result else 0

        if match_count == 0:
            return "No Data", "warning"
        else:
            return f"{match_count} Matches", "success"

    except Exception as e:
        logger.error(f"Database status check failed: {e}")
        return "DB Error", "danger"




def create_error_page(error_message: str) -> html.Div:
    """Create an error page layout.

    Args:
        error_message: Error message to display

    Returns:
        Error page layout
    """
    return html.Div(
        [
            dbc.Alert(
                [
                    html.H4("Application Error", className="alert-heading"),
                    html.P(error_message),
                    html.Hr(),
                    html.P(
                        [
                            "Please check the application logs for more details. ",
                            "Try refreshing the page or contact support if the problem persists.",
                        ]
                    ),
                ],
                color="danger",
            )
        ],
        className="mt-5",
    )


def check_database_connection() -> bool:
    """Check if database connection is working.

    Returns:
        True if database is accessible, False otherwise
    """
    try:
        db = get_database()
        with db.get_connection() as conn:
            conn.execute("SELECT 1").fetchone()
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


def cleanup_resources() -> None:
    """Clean up database connections and other resources."""
    try:
        db = get_database()
        db.close()
        logger.info("Database connections cleaned up")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


def signal_handler(signum, frame) -> None:
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    cleanup_resources()
    sys.exit(0)


def run_development_server() -> None:
    """Run the development server."""
    try:
        logger.info(f"Starting {config.APP_TITLE} in development mode")
        logger.info(f"Server will run on http://{config.APP_HOST}:{config.APP_PORT}")

        # Register cleanup handlers
        atexit.register(cleanup_resources)
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Check database connection
        if not check_database_connection():
            logger.warning("Database connection failed - some features may not work")

        use_reloader = os.getenv("FLASK_DEBUG") == "1"
        if use_reloader:
            logger.info("Running with auto-reloader enabled")
        app.run(
            host=config.APP_HOST,
            port=config.APP_PORT,
            debug=False,
            threaded=True,
            use_reloader=use_reloader,
        )
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except OSError as e:
        if "Address already in use" in str(e):
            logger.error(
                f"Port {config.APP_PORT} is already in use. Try a different port or stop other servers."
            )
        else:
            logger.error(f"OS error starting server: {e}")
    except Exception as e:
        logger.error(f"Unexpected error starting server: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        cleanup_resources()


def create_production_server():
    """Create the production WSGI server.

    Returns:
        WSGI application object
    """
    logger.info(f"Starting {config.APP_TITLE} in production mode")

    # Check database connection
    if not check_database_connection():
        logger.error(
            "Database connection failed - application may not function properly"
        )

    return app.server


# Export the server for WSGI deployment
server = app.server

# Register Flask blueprints for API routes
from tournament_visualizer.api import map_api

server.register_blueprint(map_api)
logger.info("Registered map_api blueprint")


# Health check endpoint for Fly.io and other platforms
@server.route("/health")
def health_check():
    """Health check endpoint for monitoring.

    Returns:
        JSON response with health status
    """
    from flask import jsonify

    try:
        # Simple health check - just verify the app is responding
        # Don't check database to avoid lock conflicts and slow responses
        return jsonify({"status": "healthy", "app": "running"}), 200

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "error": "Health check failed"}), 503


if __name__ == "__main__":
    # Run development server
    run_development_server()
