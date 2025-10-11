"""Gunicorn configuration for production deployment.

This configuration is used when running the application with Gunicorn
in production environments like Fly.io.
"""

import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '8080')}"
backlog = 2048

# Worker processes
# For Fly.io shared-cpu-1x (1 shared CPU, 1GB RAM): use 2 workers max
# Each worker loads the full Dash app (Pandas, DuckDB, Plotly) into memory
# More workers = more memory usage and CPU contention on shared CPU
workers = int(os.getenv("WEB_CONCURRENCY", "2"))  # Default to 2, can override via env var
worker_class = "sync"
worker_connections = 1000
timeout = 120  # 2 minutes - important for slow analytics queries
keepalive = 5

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "tournament_visualizer"

# Server mechanics
daemon = False  # Don't daemonize (Fly.io manages the process)
pidfile = None
user = None
group = None
tmp_upload_dir = None

# Preload application code before worker processes are forked
# This can save RAM but we'll disable it for Dash apps (state issues)
preload_app = False

# Maximum number of requests a worker will process before restarting
# Helps prevent memory leaks
max_requests = 1000
max_requests_jitter = 50  # Randomize restart to avoid all workers restarting at once
