"""Gunicorn configuration for production deployment.

This configuration is used when running the application with Gunicorn
in production environments like Fly.io.
"""

import logging
from logging.handlers import RotatingFileHandler
import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '8080')}"
backlog = 2048

# Worker processes
# For Fly.io shared-cpu-2x (2 shared CPUs, 1GB RAM): use 4 workers
# Each worker loads the full Dash app (Pandas, DuckDB, Plotly) into memory
# Rule of thumb: 2 * num_cpus for memory-intensive Dash apps
workers = int(os.getenv("WEB_CONCURRENCY", "4"))  # Default to 4, can override via env var
worker_class = "gthread"
threads = 4  # 4 workers x 4 threads = 16 concurrent requests
timeout = 120  # 2 minutes - important for slow analytics queries
keepalive = 5

# Logging
# Access logs go to rotating file on persistent volume for analytics,
# and also to stdout for fly logs. Error logs stay on stdout only.
_log_dir = os.getenv("LOG_DIR", "/data/logs")
os.makedirs(_log_dir, exist_ok=True)
_access_log_path = os.path.join(_log_dir, "access.log")

errorlog = "-"
loglevel = "info"
# %({x-forwarded-for}i)s captures the real client IP behind Fly.io's proxy
access_log_format = '%({x-forwarded-for}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Write access logs to stdout (for fly logs) — gunicorn's built-in
accesslog = "-"


def on_starting(server: "arbiter.Arbiter") -> None:
    """Set up rotating file handler for access logs on the persistent volume."""
    access_logger = logging.getLogger("gunicorn.access")
    handler = RotatingFileHandler(
        _access_log_path,
        maxBytes=10 * 1024 * 1024,  # 10 MB per file
        backupCount=5,              # Keep 5 rotated files (~50 MB max)
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    access_logger.addHandler(handler)

# Process naming
proc_name = "tournament_visualizer"

# Server mechanics
daemon = False  # Don't daemonize (Fly.io manages the process)
pidfile = None
user = None
group = None
tmp_upload_dir = None

# Preload app so Dash component registry is fully initialized before
# workers fork — prevents race conditions with gthread workers
preload_app = True

# Maximum number of requests a worker will process before restarting
# Helps prevent memory leaks
max_requests = 1000
max_requests_jitter = 50  # Randomize restart to avoid all workers restarting at once
