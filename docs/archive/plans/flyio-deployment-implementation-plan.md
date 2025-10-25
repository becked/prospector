# Fly.io Deployment Implementation Plan

## Overview

This plan covers deploying the Old World Tournament Visualizer Dash application to Fly.io with:
- Persistent DuckDB database storage using Fly volumes
- Automated data refresh on deployment (download + import)
- Production-ready WSGI server (Gunicorn)
- Environment variable management via Fly secrets
- Zero-downtime deployment strategy

**Estimated Time**: 4-6 hours for experienced developer new to the codebase

## Prerequisites Knowledge

### What is Fly.io?
Fly.io is a platform for running applications close to users. Key concepts:
- **Apps**: Your deployed application (we'll create one)
- **Volumes**: Persistent disk storage (survives deploys, stores DuckDB file)
- **Secrets**: Encrypted environment variables (API keys)
- **Release Commands**: Run once per deploy before traffic routing

### What is Gunicorn?
Gunicorn is a production WSGI server for Python web apps. Dash's built-in server (`app.run()`) is development-only. Gunicorn provides:
- Process management (multiple workers)
- Graceful restarts
- Better performance under load

### What is DuckDB?
DuckDB is an embedded analytical database (like SQLite but for analytics). It stores data in a single file: `data/tournament_data.duckdb`. This file must persist across deployments using a Fly volume.

### What is a Fly Volume?
A volume is persistent disk storage attached to your Fly app. Unlike regular filesystem (wiped on deploy), volumes retain data. Perfect for databases.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│ Fly.io Deployment                                   │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │ Release Command (runs once per deploy)      │  │
│  │ 1. download_attachments.py                   │  │
│  │ 2. import_attachments.py                     │  │
│  └──────────────────────────────────────────────┘  │
│                      ↓                              │
│  ┌──────────────────────────────────────────────┐  │
│  │ Gunicorn WSGI Server                         │  │
│  │ - Multiple workers (2-4)                     │  │
│  │ - Serves Dash app                            │  │
│  │ - Reads from DuckDB via volume              │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │ Fly Volume: /data                            │  │
│  │ - tournament_data.duckdb (persistent)        │  │
│  │ - saves/*.zip files (persistent)             │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## Task Breakdown

### Task 1: Add Gunicorn Dependency
**Estimated Time**: 5 minutes
**Complexity**: Simple
**Files to Modify**: `pyproject.toml`

#### Context
Currently `pyproject.toml` lists all dependencies. We need to add Gunicorn as a production dependency (not dev-only).

#### Implementation Steps

1. Open `pyproject.toml`
2. Find the `dependencies` array (around line 10)
3. Add Gunicorn after the existing dependencies:

```toml
dependencies = [
    # Core visualization and web framework
    "dash>=2.17.1",
    "plotly>=5.17.0",
    "dash-bootstrap-components>=1.5.0",
    # Database and data processing
    "duckdb>=0.9.1",
    "pandas>=2.1.3",
    # XML processing
    "lxml>=4.9.3",
    # Date and time utilities
    "python-dateutil>=2.8.2",
    # Type hints
    "typing-extensions>=4.8.0",
    "python-dotenv>=1.1.1",
    # Challonge API client
    "chyllonge>=1.1.1",
    # Production WSGI server
    "gunicorn>=21.2.0",
]
```

#### Testing

Run locally to verify:
```bash
# Install the new dependency
uv sync

# Verify gunicorn is available
uv run gunicorn --version
```

Expected output: `gunicorn (version 21.2.0)` or similar

#### Commit
```bash
git add pyproject.toml uv.lock
git commit -m "feat: Add gunicorn as production WSGI server dependency"
```

---

### Task 2: Create Gunicorn Configuration
**Estimated Time**: 15 minutes
**Complexity**: Moderate
**Files to Create**: `gunicorn.conf.py`

#### Context
Gunicorn needs configuration for production. We'll create a config file that:
- Sets number of worker processes (2-4 for 512MB RAM)
- Configures timeout (important for data import)
- Sets up logging
- Binds to correct host:port for Fly.io

#### Implementation Steps

1. Create `gunicorn.conf.py` in project root:

```python
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
# Use 2-4 workers for 512MB-1GB RAM
# Formula: (2 x $num_cores) + 1, but cap at 4 for our small instance
workers = min(multiprocessing.cpu_count() * 2 + 1, 4)
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
```

2. Create the file using the Write tool

#### Testing Strategy

**Test 1: Verify Gunicorn Starts Locally**

Create a test script `test_gunicorn_local.sh`:
```bash
#!/bin/bash
# Test that gunicorn can start the app locally

echo "Starting Gunicorn locally..."
PORT=8050 uv run gunicorn "tournament_visualizer.app:server" \
    --config gunicorn.conf.py \
    --timeout 30 &

GUNICORN_PID=$!
echo "Gunicorn started with PID: $GUNICORN_PID"

# Wait for server to start
sleep 3

# Test health check
echo "Testing HTTP endpoint..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8050/)

if [ "$HTTP_STATUS" = "200" ]; then
    echo "✅ SUCCESS: Server returned HTTP $HTTP_STATUS"
    kill $GUNICORN_PID
    exit 0
else
    echo "❌ FAIL: Server returned HTTP $HTTP_STATUS (expected 200)"
    kill $GUNICORN_PID
    exit 1
fi
```

Make it executable:
```bash
chmod +x test_gunicorn_local.sh
```

Run the test:
```bash
./test_gunicorn_local.sh
```

**Expected Output**:
```
Starting Gunicorn locally...
Gunicorn started with PID: 12345
[2025-10-11 10:00:00] [INFO] Starting gunicorn 21.2.0
[2025-10-11 10:00:00] [INFO] Listening at: http://0.0.0.0:8050
Testing HTTP endpoint...
✅ SUCCESS: Server returned HTTP 200
```

**Test 2: Verify Worker Count**

Check logs for worker count:
```bash
PORT=8050 uv run gunicorn "tournament_visualizer.app:server" --config gunicorn.conf.py 2>&1 | grep "Booting worker"
```

Expected: Should see 2-4 worker boot messages

**Test 3: Access via Browser**

1. Start Gunicorn: `PORT=8050 uv run gunicorn "tournament_visualizer.app:server" --config gunicorn.conf.py`
2. Open browser: http://localhost:8050
3. Verify dashboard loads
4. Check navigation works (click "Matches", "Players", "Maps")
5. Stop with Ctrl+C

#### Common Issues & Solutions

**Issue**: "Failed to find application object 'server'"
**Solution**: Verify `tournament_visualizer/app.py` has `server = app.server` at module level (line 440)

**Issue**: Workers timeout on startup
**Solution**: Increase timeout in gunicorn.conf.py to 180

**Issue**: Port already in use
**Solution**: Stop the development server first: `uv run python manage.py stop`

#### Commit
```bash
git add gunicorn.conf.py test_gunicorn_local.sh
git commit -m "feat: Add gunicorn configuration for production deployment

- Configure 2-4 workers for 512MB-1GB RAM
- Set 2-minute timeout for analytics queries
- Enable stdout/stderr logging for Fly.io
- Add local test script to verify gunicorn setup"
```

---

### Task 3: Create Fly.io Configuration
**Estimated Time**: 20 minutes
**Complexity**: Moderate
**Files to Create**: `fly.toml`, `Dockerfile`

#### Context

Fly.io needs two configuration files:

1. **fly.toml**: Fly.io app configuration (ports, health checks, volumes)
2. **Dockerfile**: Instructions to build the application container

#### Part A: Create fly.toml

Create `fly.toml` in project root:

```toml
# Fly.io deployment configuration for Old World Tournament Visualizer
# See: https://fly.io/docs/reference/configuration/

app = "old-world-tournament"  # Change this to your desired app name
primary_region = "sjc"        # San Jose - change to your preferred region

# Enable experimental HTTP/2 support
[experimental]
  auto_rollback = true

# Build configuration
[build]
  dockerfile = "Dockerfile"

# Environment variables (non-secret)
[env]
  PORT = "8080"
  DASH_HOST = "0.0.0.0"
  DASH_PORT = "8080"
  FLASK_ENV = "production"
  TOURNAMENT_DB_PATH = "/data/tournament_data.duckdb"
  SAVES_DIRECTORY = "/data/saves"

# HTTP service configuration
[[services]]
  internal_port = 8080
  protocol = "tcp"

  # Concurrency settings
  [services.concurrency]
    type = "connections"
    hard_limit = 250
    soft_limit = 200

  # HTTP checks
  [[services.ports]]
    port = 80
    handlers = ["http"]
    force_https = true

  [[services.ports]]
    port = 443
    handlers = ["http", "tls"]

  # Health check - verify app is responding
  [[services.tcp_checks]]
    interval = "15s"
    timeout = "10s"
    grace_period = "30s"
    restart_limit = 0

  # HTTP health check
  [[services.http_checks]]
    interval = 30000        # 30 seconds
    timeout = 10000         # 10 seconds
    grace_period = "30s"
    method = "GET"
    path = "/"
    protocol = "http"
    tls_skip_verify = false

# Persistent volume for database and save files
[mounts]
  source = "tournament_data"
  destination = "/data"
  initial_size = "1gb"

# Release command - runs before deployment completes
# This downloads attachments and imports them into the database
[deploy]
  release_command = "uv run python scripts/download_attachments.py && uv run python scripts/import_attachments.py --directory /data/saves --verbose"
```

#### Part B: Create Dockerfile

Create `Dockerfile` in project root:

```dockerfile
# Dockerfile for Old World Tournament Visualizer
# Multi-stage build for smaller final image

# Stage 1: Build stage - install dependencies
FROM python:3.11-slim as builder

# Install system dependencies needed for Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package installer)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy dependency files first (for Docker layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# Stage 2: Runtime stage - minimal image
FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv in runtime stage
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Create non-root user for security
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appuser . .

# Create directories for data and logs
RUN mkdir -p /data/saves logs && \
    chown -R appuser:appuser /data logs

# Switch to non-root user
USER appuser

# Set Python path to use virtual environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# Command to run - uses gunicorn with our config
CMD ["gunicorn", "tournament_visualizer.app:server", "--config", "gunicorn.conf.py"]
```

#### Understanding the Dockerfile

**Multi-stage Build**:
- Stage 1 (builder): Installs build tools and dependencies
- Stage 2 (runtime): Copies only what's needed to run the app
- Result: Smaller final image (~400MB vs ~1GB)

**Why non-root user?**
Security best practice. If app is compromised, attacker has limited permissions.

**Why PYTHONUNBUFFERED=1?**
Ensures Python output appears immediately in logs (not buffered).

**Health check**:
Fly.io will call `curl http://localhost:8080/` every 30s to verify app is healthy.

#### Testing Strategy

**Test 1: Build Docker Image Locally**

```bash
# Build the image
docker build -t tournament-visualizer:test .

# Check image size (should be ~400-600MB)
docker images tournament-visualizer:test
```

**Test 2: Run Container Locally**

Create `.env.docker` file for testing (DO NOT COMMIT):
```bash
CHALLONGE_KEY=your_key_here
CHALLONGE_USER=your_username
challonge_tournament_id=your_tournament_id
```

Run container:
```bash
docker run --rm \
    -p 8080:8080 \
    -v $(pwd)/data:/data \
    --env-file .env.docker \
    tournament-visualizer:test
```

**Expected output**:
```
[INFO] Starting gunicorn 21.2.0
[INFO] Listening at: http://0.0.0.0:8080
[INFO] Using worker: sync
[INFO] Booting worker with pid: 12
[INFO] Booting worker with pid: 13
```

**Test 3: Verify Container Health**

In another terminal:
```bash
# Test HTTP endpoint
curl http://localhost:8080/

# Check Docker health status
docker ps
```

Expected: Container shows "healthy" status after 40 seconds

**Test 4: Verify App Functionality**

1. Open browser: http://localhost:8080
2. Click through all navigation items
3. Verify no errors in Docker logs
4. Stop container: `docker stop <container_id>`

#### Common Issues & Solutions

**Issue**: "uv: command not found"
**Solution**: Check uv install step in Dockerfile succeeded. Try: `docker build --no-cache`

**Issue**: "Permission denied" on /data
**Solution**: Verify the `chown -R appuser:appuser /data` line in Dockerfile

**Issue**: Container exits immediately
**Solution**: Check logs: `docker logs <container_id>`. Likely import error.

**Issue**: Build fails on "COPY uv.lock"
**Solution**: Run `uv lock` locally first to generate uv.lock

#### Commit
```bash
# Add to .gitignore
echo ".env.docker" >> .gitignore

git add fly.toml Dockerfile .gitignore
git commit -m "feat: Add Fly.io deployment configuration

- Add fly.toml with volume mount and health checks
- Add multi-stage Dockerfile for optimal image size
- Configure release command to run data import on deploy
- Set production environment variables
- Use non-root user for security"
```

---

### Task 4: Update Scripts for Production Environment
**Estimated Time**: 25 minutes
**Complexity**: Moderate
**Files to Modify**: `scripts/download_attachments.py`, `scripts/import_attachments.py`

#### Context

Current scripts assume:
- `.env` file exists locally
- `saves/` directory is relative to project root

In production on Fly.io:
- Environment variables come from Fly secrets (no .env file)
- Paths may be different (`/data/saves` instead of `./saves`)
- Scripts must handle missing directories gracefully
- Need better error handling and exit codes

#### Part A: Update download_attachments.py

**Change 1**: Make directory path configurable

Find the line (around line 124):
```python
downloads_dir = Path("saves")
```

Replace with:
```python
# Use SAVES_DIRECTORY env var if set, otherwise default to "saves"
downloads_dir = Path(os.getenv("SAVES_DIRECTORY", "saves"))
```

**Change 2**: Add error handling for missing environment variables

Find the `load_config()` function (around line 16):
```python
def load_config() -> str:
    """Load tournament ID from environment variables.

    Note: chyllonge uses CHALLONGE_KEY and CHALLONGE_USER env vars automatically.
    """
    load_dotenv()

    tournament_id = os.getenv("challonge_tournament_id")

    if not tournament_id:
        raise ValueError("challonge_tournament_id not found in .env file")

    return tournament_id
```

Replace with:
```python
def load_config() -> str:
    """Load tournament ID from environment variables.

    Note: chyllonge uses CHALLONGE_KEY and CHALLONGE_USER env vars automatically.

    Environment variables are loaded from .env file in development,
    or directly from environment in production (Fly.io secrets).
    """
    # Try to load .env file (development), silently skip if not found (production)
    load_dotenv()

    tournament_id = os.getenv("challonge_tournament_id")

    if not tournament_id:
        raise ValueError(
            "challonge_tournament_id not found in environment variables. "
            "In development: check .env file. "
            "In production: set via 'flyctl secrets set challonge_tournament_id=VALUE'"
        )

    # Verify other required environment variables
    if not os.getenv("CHALLONGE_KEY"):
        raise ValueError(
            "CHALLONGE_KEY not found in environment variables. "
            "Required for Challonge API access."
        )

    if not os.getenv("CHALLONGE_USER"):
        raise ValueError(
            "CHALLONGE_USER not found in environment variables. "
            "Required for Challonge API access."
        )

    return tournament_id
```

**Change 3**: Add main error handling with exit codes

Find the `main()` function (around line 114) and wrap try/except:

```python
def main() -> None:
    """Main function to download all tournament attachments."""
    try:
        # Load configuration
        tournament_id = load_config()

        # ... rest of existing code ...

    except ValueError as e:
        # Configuration errors (missing env vars)
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        # Unexpected errors
        print(f"Unexpected Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

Don't forget to import `sys` at the top:
```python
import sys
```

#### Part B: Update import_attachments.py

The import script already has good structure, but we need to add better exit codes.

Find the `main()` function (around line 127) and update the exception handling:

```python
    except Exception as e:
        logger.error(f"Import failed: {e}")
        print(f"\n❌ Import failed: {e}", file=sys.stderr)

        # Import traceback for detailed error output
        import traceback
        traceback.print_exc()

        sys.exit(1)
```

Also verify the `--directory` default uses environment variable. Find the argument parser (around line 133):

```python
parser.add_argument(
    "--directory",
    "-d",
    default="saves",
    help="Directory containing tournament save files (default: saves)",
)
```

Update to:
```python
parser.add_argument(
    "--directory",
    "-d",
    default=os.getenv("SAVES_DIRECTORY", "saves"),
    help="Directory containing tournament save files (default: $SAVES_DIRECTORY or 'saves')",
)
```

Add `import os` at the top if not already present.

#### Testing Strategy

**Test 1: Verify Scripts Work Without .env File**

```bash
# Temporarily rename .env to simulate production
mv .env .env.backup

# Set environment variables manually
export CHALLONGE_KEY="your_key"
export CHALLONGE_USER="your_username"
export challonge_tournament_id="your_tournament_id"
export SAVES_DIRECTORY="saves"

# Test download script
uv run python scripts/download_attachments.py

# Test import script
uv run python scripts/import_attachments.py --verbose

# Restore .env
mv .env.backup .env
unset CHALLONGE_KEY CHALLONGE_USER challonge_tournament_id SAVES_DIRECTORY
```

**Expected**: Both scripts should run successfully using environment variables.

**Test 2: Verify Error Messages for Missing Env Vars**

```bash
# Test download script without required vars
uv run python scripts/download_attachments.py 2>&1 | grep "Configuration Error"
```

**Expected output**:
```
Configuration Error: challonge_tournament_id not found in environment variables...
```

**Test 3: Verify Custom SAVES_DIRECTORY**

```bash
# Create test directory
mkdir -p /tmp/test_saves

# Set custom directory
export SAVES_DIRECTORY="/tmp/test_saves"
export CHALLONGE_KEY="your_key"
export CHALLONGE_USER="your_username"
export challonge_tournament_id="your_tournament_id"

# Run download (should create files in /tmp/test_saves)
uv run python scripts/download_attachments.py

# Verify files exist
ls -la /tmp/test_saves/

# Cleanup
unset SAVES_DIRECTORY CHALLONGE_KEY CHALLONGE_USER challonge_tournament_id
rm -rf /tmp/test_saves
```

**Test 4: Write Automated Test**

Create `tests/test_script_env_handling.py`:

```python
"""Test that scripts handle environment variables correctly."""

import os
import subprocess
from pathlib import Path


def test_download_script_requires_tournament_id():
    """Verify download script exits with error when tournament_id missing."""
    # Remove tournament ID from environment
    env = os.environ.copy()
    env.pop("challonge_tournament_id", None)

    # Run script
    result = subprocess.run(
        ["uv", "run", "python", "scripts/download_attachments.py"],
        env=env,
        capture_output=True,
        text=True,
    )

    # Should exit with error code 1
    assert result.returncode == 1
    assert "challonge_tournament_id not found" in result.stderr


def test_download_script_requires_api_key():
    """Verify download script exits with error when API key missing."""
    env = os.environ.copy()
    env.pop("CHALLONGE_KEY", None)
    env["challonge_tournament_id"] = "test"

    result = subprocess.run(
        ["uv", "run", "python", "scripts/download_attachments.py"],
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "CHALLONGE_KEY not found" in result.stderr


def test_import_script_uses_saves_directory_env():
    """Verify import script respects SAVES_DIRECTORY environment variable."""
    # This is a dry-run test - won't actually import
    env = os.environ.copy()
    env["SAVES_DIRECTORY"] = "/tmp/custom_saves"

    # Create the directory so validation passes
    Path("/tmp/custom_saves").mkdir(exist_ok=True)

    # Run with --dry-run
    result = subprocess.run(
        ["uv", "run", "python", "scripts/import_attachments.py", "--dry-run"],
        env=env,
        capture_output=True,
        text=True,
    )

    # Should mention the custom directory in output
    assert "/tmp/custom_saves" in result.stdout or "/tmp/custom_saves" in result.stderr

    # Cleanup
    Path("/tmp/custom_saves").rmdir()
```

Run the test:
```bash
uv run pytest tests/test_script_env_handling.py -v
```

**Expected output**:
```
test_script_env_handling.py::test_download_script_requires_tournament_id PASSED
test_script_env_handling.py::test_download_script_requires_api_key PASSED
test_script_env_handling.py::test_import_script_uses_saves_directory_env PASSED
```

#### Commit
```bash
git add scripts/download_attachments.py scripts/import_attachments.py tests/test_script_env_handling.py
git commit -m "feat: Update scripts for production environment

- Make SAVES_DIRECTORY configurable via environment variable
- Add validation for required Challonge API environment variables
- Improve error messages with production/development context
- Add proper exit codes for script failures
- Add tests for environment variable handling"
```

---

### Task 5: Add Procfile for Local Testing
**Estimated Time**: 10 minutes
**Complexity**: Simple
**Files to Create**: `Procfile`

#### Context

A Procfile tells process managers (like Fly.io or Heroku) how to run your app. While Fly.io uses Dockerfile CMD, having a Procfile is useful for:
- Documentation (shows how to run the app)
- Local testing with `foreman` or `hivemind`
- Alternative deployment platforms

#### Implementation Steps

Create `Procfile` in project root:

```
# Process types for Old World Tournament Visualizer
#
# This Procfile defines how to run the application.
# Used by Fly.io, Heroku, and process managers like foreman/hivemind.
#
# Usage with foreman:
#   gem install foreman
#   foreman start
#
# Usage with hivemind:
#   brew install hivemind  # macOS
#   hivemind

# Web server - production WSGI server
web: gunicorn tournament_visualizer.app:server --config gunicorn.conf.py

# Release - run before deployment (handled by fly.toml deploy.release_command)
release: python scripts/download_attachments.py && python scripts/import_attachments.py --directory ${SAVES_DIRECTORY:-saves} --verbose
```

#### Testing Strategy

**Test 1: Install foreman (if not installed)**

macOS:
```bash
gem install foreman
```

Linux:
```bash
gem install foreman
# or
sudo apt-get install ruby-foreman
```

**Test 2: Run with foreman**

```bash
# Ensure .env file exists with required variables
foreman start web
```

**Expected output**:
```
08:00:00 web.1  | started with pid 12345
08:00:00 web.1  | [INFO] Starting gunicorn 21.2.0
08:00:00 web.1  | [INFO] Listening at: http://0.0.0.0:8080
08:00:00 web.1  | [INFO] Using worker: sync
08:00:00 web.1  | [INFO] Booting worker with pid: 12346
```

**Test 3: Access the app**

Open browser: http://localhost:8080

Stop foreman with Ctrl+C

**Test 4: Test release command manually**

```bash
foreman run release
```

Expected: Should download attachments and import them successfully

#### Commit
```bash
git add Procfile
git commit -m "feat: Add Procfile for process management

- Define web and release process types
- Enable local testing with foreman/hivemind
- Document production run command"
```

---

### Task 6: Create Fly.io Deployment Documentation
**Estimated Time**: 20 minutes
**Complexity**: Simple
**Files to Create**: `docs/deployment/flyio-deployment-guide.md`

#### Context

Create comprehensive documentation for deploying and managing the app on Fly.io. This is crucial for:
- Future deployments
- Team members who need to manage production
- Troubleshooting issues

#### Implementation Steps

Create `docs/deployment/flyio-deployment-guide.md`:

```markdown
# Fly.io Deployment Guide

This guide covers deploying the Old World Tournament Visualizer to Fly.io.

## Prerequisites

1. **Fly.io Account**: Sign up at https://fly.io/
2. **Fly CLI**: Install flyctl
   ```bash
   # macOS
   brew install flyctl

   # Linux
   curl -L https://fly.io/install.sh | sh

   # Windows
   iwr https://fly.io/install.ps1 -useb | iex
   ```

3. **Fly.io Authentication**:
   ```bash
   flyctl auth login
   ```

4. **Challonge API Credentials**:
   - API Key: Get from https://challonge.com/settings/developer
   - Username: Your Challonge username
   - Tournament ID: The tournament to track

## First-Time Deployment

### Step 1: Launch the App

```bash
# Launch app (creates app on Fly.io)
flyctl launch --no-deploy

# Answer prompts:
# - App name: old-world-tournament (or your choice)
# - Region: Choose closest to your users
# - Postgres database: No
# - Redis: No
```

This creates the app but doesn't deploy yet (we need to set secrets first).

### Step 2: Create Volume for Persistent Storage

```bash
# Create 1GB volume for database and save files
flyctl volumes create tournament_data --size 1 --region sjc

# Verify volume was created
flyctl volumes list
```

**Important**: The volume must be in the same region as your app.

### Step 3: Set Environment Secrets

```bash
# Set Challonge API credentials
flyctl secrets set CHALLONGE_KEY="your_api_key_here"
flyctl secrets set CHALLONGE_USER="your_username"
flyctl secrets set challonge_tournament_id="your_tournament_id"

# Verify secrets are set (values are hidden)
flyctl secrets list
```

**Never commit these values to git!**

### Step 4: Deploy

```bash
# Deploy the application
flyctl deploy

# This will:
# 1. Build Docker image
# 2. Push to Fly.io registry
# 3. Run release command (download + import data)
# 4. Start the app
# 5. Run health checks
```

**First deployment takes 5-10 minutes** due to:
- Docker image build (~2-3 minutes)
- Data download (~1-2 minutes)
- Data import (~2-5 minutes)

### Step 5: Verify Deployment

```bash
# Check app status
flyctl status

# View logs
flyctl logs

# Open in browser
flyctl open
```

Expected status: All instances should show "started" and health checks passing.

## Subsequent Deployments

After initial setup, deployments are simpler:

```bash
# Make code changes
git add .
git commit -m "your changes"

# Deploy
flyctl deploy

# Watch logs during deployment
flyctl logs --follow
```

## Managing the Application

### View Logs

```bash
# Recent logs
flyctl logs

# Follow logs (live tail)
flyctl logs --follow

# Filter by severity
flyctl logs --level error
```

### Scale Resources

**Change Memory**:
```bash
# Scale to 1GB RAM (recommended for busy sites)
flyctl scale memory 1024

# Scale to 512MB RAM (minimum recommended)
flyctl scale memory 512
```

**Change Region**:
```bash
# Add instance in another region
flyctl scale count 2 --region lax
```

### Access Database

To inspect the DuckDB database:

```bash
# SSH into the running instance
flyctl ssh console

# Once inside:
cd /data
duckdb tournament_data.duckdb -readonly

# Example queries:
.tables
SELECT COUNT(*) FROM matches;
SELECT * FROM players LIMIT 10;

# Exit duckdb: Ctrl+D
# Exit SSH: exit
```

### Manual Data Refresh

If you need to refresh data without deploying:

```bash
# SSH into instance
flyctl ssh console

# Run scripts manually
cd /app
uv run python scripts/download_attachments.py
uv run python scripts/import_attachments.py --directory /data/saves --verbose

# Exit
exit
```

### Restart Application

```bash
# Restart all instances
flyctl apps restart old-world-tournament
```

## Troubleshooting

### App Won't Start

**Check logs**:
```bash
flyctl logs --level error
```

**Common issues**:
1. **Missing secrets**: Verify with `flyctl secrets list`
2. **Volume not mounted**: Check `flyctl volumes list`
3. **Import failed**: Check logs during release command
4. **Out of memory**: Scale to 1GB with `flyctl scale memory 1024`

### Release Command Fails

The release command runs before deployment completes. If it fails:

```bash
# View release command logs
flyctl releases --image

# SSH and run manually
flyctl ssh console
uv run python scripts/download_attachments.py
uv run python scripts/import_attachments.py --directory /data/saves --verbose
```

### Health Checks Failing

```bash
# Check health check status
flyctl status

# Common fixes:
# 1. Increase timeout in fly.toml http_checks.timeout
# 2. Check app actually runs on port 8080
# 3. Verify /data volume is mounted
```

### Database Corruption

If DuckDB database gets corrupted:

```bash
# SSH into instance
flyctl ssh console

# Backup existing database
cd /data
cp tournament_data.duckdb tournament_data.duckdb.backup

# Remove corrupted database
rm tournament_data.duckdb

# Re-import from saves
cd /app
uv run python scripts/import_attachments.py --directory /data/saves --force --verbose

# Exit
exit
```

## Monitoring

### View Metrics

```bash
# Resource usage
flyctl metrics

# App status
flyctl status

# Health checks
flyctl checks
```

### Set Up Alerts (Optional)

Fly.io can send alerts when:
- Health checks fail
- App crashes
- High resource usage

Configure at: https://fly.io/dashboard/personal/monitoring

## Costs

Typical monthly costs (as of 2025):
- **shared-cpu-1x @ 512MB**: ~$3.88/month
- **shared-cpu-1x @ 1GB**: ~$7.76/month
- **Volume (1GB)**: ~$0.15/month
- **Bandwidth**: Usually free tier (160GB/month)

**Total**: ~$4-8/month

Monitor usage: https://fly.io/dashboard/personal/billing

## Backup Strategy

### Automated Backups (Recommended)

Use Fly.io snapshots:

```bash
# Enable daily snapshots (costs ~$0.05/snapshot/month)
flyctl volumes create tournament_data_backup --snapshot-id <volume-snapshot-id>
```

### Manual Backups

```bash
# SSH into instance
flyctl ssh console

# Create backup
cd /data
tar -czf backup-$(date +%Y%m%d).tar.gz tournament_data.duckdb saves/

# Download to local machine (from local terminal)
flyctl ssh sftp get /data/backup-20251011.tar.gz ./backups/

# Exit SSH
exit
```

## Updating Configuration

### Update fly.toml

1. Edit `fly.toml` locally
2. Deploy: `flyctl deploy`

### Update Environment Variables

```bash
# Update a secret
flyctl secrets set CHALLONGE_KEY="new_key_value"

# Note: This triggers a restart
```

### Update Gunicorn Config

1. Edit `gunicorn.conf.py`
2. Commit changes
3. Deploy: `flyctl deploy`

## Destroying the App

**Warning**: This deletes everything including volumes!

```bash
# Delete app and all resources
flyctl apps destroy old-world-tournament

# You'll be prompted to confirm
```

## Additional Resources

- Fly.io Documentation: https://fly.io/docs/
- Fly.io Status: https://status.flyio.net/
- Community Forum: https://community.fly.io/
- Discord: https://fly.io/discord

## Getting Help

1. **Check logs first**: `flyctl logs --level error`
2. **Check Fly.io status**: https://status.flyio.net/
3. **Community forum**: https://community.fly.io/
4. **Project issues**: Create issue in this repo
```

Create directory first:
```bash
mkdir -p docs/deployment
```

#### Testing

**Validation checklist**:
- [ ] All commands are correct syntax
- [ ] Links work
- [ ] Markdown renders correctly
- [ ] Covers common scenarios
- [ ] Troubleshooting section is comprehensive

**Test rendering**:
```bash
# View in terminal (if you have glow installed)
glow docs/deployment/flyio-deployment-guide.md

# Or open in any markdown viewer
```

#### Commit
```bash
git add docs/deployment/flyio-deployment-guide.md
git commit -m "docs: Add comprehensive Fly.io deployment guide

- Cover first-time deployment steps
- Document volume and secrets management
- Add troubleshooting section
- Include monitoring and backup strategies
- Provide cost estimates"
```

---

### Task 7: Add .dockerignore File
**Estimated Time**: 5 minutes
**Complexity**: Simple
**Files to Create**: `.dockerignore`

#### Context

`.dockerignore` works like `.gitignore` but for Docker builds. It tells Docker which files to exclude when building the image. This:
- Reduces build time (fewer files to copy)
- Reduces image size
- Prevents secrets from accidentally being included

#### Implementation Steps

Create `.dockerignore` in project root:

```
# Python artifacts
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/
*.egg

# Virtual environments
venv/
env/
ENV/
.venv/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# OS
.DS_Store
Thumbs.db

# Git
.git/
.gitignore
.gitattributes

# Local development
.env
.env.*
!.env.example

# Data and logs (will use volume mount instead)
data/*.duckdb
data/*.duckdb.wal
logs/*.log
saves/*.zip

# Documentation and development files
docs/
tests/
*.md
!README.md

# CI/CD
.github/

# Development scripts
.server.pid
test_*.sh

# Temporary files
tmp/
*.tmp
```

#### Testing

**Test 1: Build image and verify size**

```bash
# Build without .dockerignore (for comparison)
mv .dockerignore .dockerignore.bak
docker build -t test-without:latest .
docker images test-without:latest

# Build with .dockerignore
mv .dockerignore.bak .dockerignore
docker build -t test-with:latest .
docker images test-with:latest
```

Expected: Image with .dockerignore should be 50-100MB smaller

**Test 2: Verify excluded files not in image**

```bash
# Build image
docker build -t test:latest .

# Check for files that should be excluded
docker run --rm test:latest ls -la /app/.git 2>&1 || echo "✅ .git correctly excluded"
docker run --rm test:latest ls -la /app/tests 2>&1 || echo "✅ tests correctly excluded"
docker run --rm test:latest ls -la /app/.env 2>&1 || echo "✅ .env correctly excluded"
```

Expected: All checks should pass (files excluded)

#### Commit
```bash
git add .dockerignore
git commit -m "feat: Add .dockerignore to optimize Docker builds

- Exclude Python artifacts and virtual environments
- Exclude development files and tests
- Exclude sensitive files like .env
- Reduce image size by 50-100MB"
```

---

### Task 8: Update Configuration for Production
**Estimated Time**: 15 minutes
**Complexity**: Moderate
**Files to Modify**: `tournament_visualizer/config.py`

#### Context

Current `config.py` has `ProductionConfig` class but it needs adjustments for Fly.io:
- Ensure host is 0.0.0.0 (not 127.0.0.1)
- Use PORT environment variable
- Disable debug mode in production
- Adjust cache timeouts

#### Implementation Steps

Open `tournament_visualizer/config.py` and update the `ProductionConfig` class:

Find the class definition (around line 94):
```python
class ProductionConfig(Config):
    """Production-specific configuration."""

    DEBUG_MODE = False
    CACHE_TIMEOUT = 3600  # Longer cache for production
    LAZY_LOADING = True
```

Replace with:
```python
class ProductionConfig(Config):
    """Production-specific configuration for Fly.io and other hosts."""

    DEBUG_MODE = False

    # Bind to 0.0.0.0 to accept external connections
    APP_HOST = "0.0.0.0"

    # Use PORT environment variable (Fly.io sets this to 8080)
    APP_PORT = int(os.getenv("PORT", "8080"))

    # Database path from environment (volume mount on Fly.io)
    DATABASE_PATH = os.getenv("TOURNAMENT_DB_PATH", "data/tournament_data.duckdb")

    # Saves directory from environment (volume mount on Fly.io)
    SAVES_DIRECTORY = os.getenv("SAVES_DIRECTORY", "saves")

    # Longer cache for production
    CACHE_TIMEOUT = 3600  # 1 hour

    # Enable lazy loading for better performance
    LAZY_LOADING = True
```

Also update the `get_config()` function to better detect production environment:

Find the function (around line 118):
```python
def get_config(config_name: str = None) -> Config:
    """Get configuration object based on environment.

    Args:
        config_name: Configuration name (development/production/testing)

    Returns:
        Configuration object
    """
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    return CONFIG_MAP.get(config_name, DevelopmentConfig)
```

Replace with:
```python
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
```

**Important fix**: The function was returning the class itself, not an instance. This could cause issues.

#### Testing Strategy

**Test 1: Verify Configuration Classes Work**

Create `tests/test_config.py`:

```python
"""Test configuration classes."""

import os
from tournament_visualizer.config import (
    Config,
    DevelopmentConfig,
    ProductionConfig,
    TestConfig,
    get_config,
)


def test_production_config_uses_port_env():
    """Production config should use PORT environment variable."""
    # Set PORT environment variable
    os.environ["PORT"] = "9999"

    config = ProductionConfig()

    assert config.APP_PORT == 9999
    assert config.APP_HOST == "0.0.0.0"
    assert config.DEBUG_MODE is False

    # Cleanup
    del os.environ["PORT"]


def test_production_config_defaults():
    """Production config should have sensible defaults."""
    # Ensure PORT is not set
    os.environ.pop("PORT", None)

    config = ProductionConfig()

    assert config.APP_PORT == 8080  # Default
    assert config.APP_HOST == "0.0.0.0"
    assert config.DEBUG_MODE is False
    assert config.CACHE_TIMEOUT == 3600


def test_production_config_uses_database_path_env():
    """Production config should use TOURNAMENT_DB_PATH environment variable."""
    os.environ["TOURNAMENT_DB_PATH"] = "/data/custom.duckdb"

    config = ProductionConfig()

    assert config.DATABASE_PATH == "/data/custom.duckdb"

    # Cleanup
    del os.environ["TOURNAMENT_DB_PATH"]


def test_get_config_auto_detects_production():
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


def test_get_config_respects_flask_env():
    """get_config should respect explicit FLASK_ENV."""
    os.environ["FLASK_ENV"] = "development"

    config = get_config()

    assert isinstance(config, DevelopmentConfig)

    # Cleanup
    del os.environ["FLASK_ENV"]


def test_get_config_returns_instance_not_class():
    """get_config should return a config instance, not class."""
    config = get_config("development")

    # Should be instance of Config
    assert isinstance(config, Config)

    # Should have attributes accessible
    assert hasattr(config, "APP_PORT")
    assert hasattr(config, "DATABASE_PATH")


def test_development_config_defaults():
    """Development config should have debug-friendly defaults."""
    config = DevelopmentConfig()

    assert config.DEBUG_MODE is True
    assert config.APP_HOST == "0.0.0.0"
    assert config.CACHE_TIMEOUT == 10  # Short cache for development


def test_test_config_uses_memory_database():
    """Test config should use in-memory database."""
    config = TestConfig()

    assert config.DATABASE_PATH == ":memory:"
    assert config.DEBUG_MODE is False
    assert config.CACHE_TIMEOUT == 0  # No caching for tests
```

Run tests:
```bash
uv run pytest tests/test_config.py -v
```

**Expected output**:
```
tests/test_config.py::test_production_config_uses_port_env PASSED
tests/test_config.py::test_production_config_defaults PASSED
tests/test_config.py::test_production_config_uses_database_path_env PASSED
tests/test_config.py::test_get_config_auto_detects_production PASSED
tests/test_config.py::test_get_config_respects_flask_env PASSED
tests/test_config.py::test_get_config_returns_instance_not_class PASSED
tests/test_config.py::test_development_config_defaults PASSED
tests/test_config.py::test_test_config_uses_memory_database PASSED
```

**Test 2: Manual Verification**

```bash
# Test development config
FLASK_ENV=development uv run python -c "
from tournament_visualizer.config import get_config
config = get_config()
print(f'Mode: {config.__class__.__name__}')
print(f'Debug: {config.DEBUG_MODE}')
print(f'Port: {config.APP_PORT}')
"

# Test production config with PORT
PORT=8080 uv run python -c "
from tournament_visualizer.config import get_config
config = get_config()
print(f'Mode: {config.__class__.__name__}')
print(f'Debug: {config.DEBUG_MODE}')
print(f'Port: {config.APP_PORT}')
print(f'Host: {config.APP_HOST}')
"
```

**Expected output**:
```
# Development:
Mode: DevelopmentConfig
Debug: True
Port: 8050

# Production:
Mode: ProductionConfig
Debug: False
Port: 8080
Host: 0.0.0.0
```

#### Commit
```bash
git add tournament_visualizer/config.py tests/test_config.py
git commit -m "feat: Update ProductionConfig for Fly.io deployment

- Use PORT environment variable for dynamic port binding
- Bind to 0.0.0.0 in production for external access
- Auto-detect production when PORT is set
- Fix get_config to return instance instead of class
- Add comprehensive config tests"
```

---

### Task 9: Create Pre-Deployment Checklist
**Estimated Time**: 10 minutes
**Complexity**: Simple
**Files to Create**: `docs/deployment/pre-deployment-checklist.md`

#### Context

A checklist ensures nothing is forgotten before deploying. Especially useful for first-time deployments.

#### Implementation Steps

Create `docs/deployment/pre-deployment-checklist.md`:

```markdown
# Pre-Deployment Checklist

Use this checklist before deploying to Fly.io to ensure everything is ready.

## Code Readiness

- [ ] All tests pass locally
  ```bash
  uv run pytest -v
  ```

- [ ] Code is formatted and linted
  ```bash
  uv run black tournament_visualizer/
  uv run ruff check tournament_visualizer/
  ```

- [ ] Git working directory is clean
  ```bash
  git status
  ```

- [ ] All changes are committed
  ```bash
  git log -1
  ```

## Local Testing

- [ ] App runs with development server
  ```bash
  uv run python manage.py start
  # Visit http://localhost:8050
  ```

- [ ] App runs with Gunicorn locally
  ```bash
  PORT=8080 uv run gunicorn "tournament_visualizer.app:server" --config gunicorn.conf.py
  # Visit http://localhost:8080
  ```

- [ ] Scripts work with environment variables
  ```bash
  export CHALLONGE_KEY="your_key"
  export CHALLONGE_USER="your_username"
  export challonge_tournament_id="your_tournament_id"
  uv run python scripts/download_attachments.py
  uv run python scripts/import_attachments.py --verbose
  ```

- [ ] Docker image builds successfully
  ```bash
  docker build -t tournament-visualizer:test .
  ```

- [ ] Docker container runs successfully
  ```bash
  docker run --rm -p 8080:8080 --env-file .env tournament-visualizer:test
  # Visit http://localhost:8080
  ```

## Fly.io Setup

- [ ] Fly.io CLI installed
  ```bash
  flyctl version
  ```

- [ ] Authenticated to Fly.io
  ```bash
  flyctl auth whoami
  ```

- [ ] App name chosen (must be globally unique)
  - Update `app = "..."` in `fly.toml`
  - Verify available: `flyctl apps create <name> --org personal`

- [ ] Region selected
  - Update `primary_region = "..."` in `fly.toml`
  - List regions: `flyctl platform regions`

## API Credentials

- [ ] Challonge API key obtained
  - Get from: https://challonge.com/settings/developer
  - Store securely (password manager)

- [ ] Challonge username confirmed
  - Your Challonge login username

- [ ] Tournament ID identified
  - Example: `oldworld1v1league` from URL `challonge.com/oldworld1v1league`

## Environment Variables

- [ ] `.env` file exists locally (for development)
  ```bash
  cat .env
  ```

- [ ] `.env` contains all required variables:
  - `CHALLONGE_KEY`
  - `CHALLONGE_USER`
  - `challonge_tournament_id`

- [ ] `.env` is in `.gitignore` (never commit secrets!)
  ```bash
  grep "^\.env$" .gitignore
  ```

## Configuration Files

- [ ] `fly.toml` reviewed and updated
  - App name is unique
  - Region is correct
  - Volume mount is configured
  - Health checks are appropriate

- [ ] `Dockerfile` is present and correct
  - Multi-stage build
  - Non-root user
  - Correct CMD

- [ ] `gunicorn.conf.py` is present
  - Worker count appropriate
  - Timeout set to 120s

- [ ] `.dockerignore` is present
  - Excludes .git, tests, docs
  - Excludes .env and sensitive files

## Documentation

- [ ] Deployment guide reviewed
  - `docs/deployment/flyio-deployment-guide.md`

- [ ] Implementation plan reviewed
  - `docs/plans/flyio-deployment-implementation-plan.md`

## First Deployment Only

- [ ] Volume created
  ```bash
  flyctl volumes create tournament_data --size 1 --region <region>
  ```

- [ ] Secrets set
  ```bash
  flyctl secrets set CHALLONGE_KEY="..."
  flyctl secrets set CHALLONGE_USER="..."
  flyctl secrets set challonge_tournament_id="..."
  ```

- [ ] Verify secrets
  ```bash
  flyctl secrets list
  ```

## Final Checks

- [ ] Recent backup of local database (if exists)
  ```bash
  cp data/tournament_data.duckdb data/tournament_data.duckdb.backup_$(date +%Y%m%d)
  ```

- [ ] README updated with deployment info (if needed)

- [ ] Team notified of deployment (if applicable)

## Deploy!

Once all checks pass:

```bash
# Deploy to Fly.io
flyctl deploy

# Watch logs during deployment
flyctl logs --follow

# Verify status
flyctl status

# Open in browser
flyctl open
```

## Post-Deployment Verification

After deployment completes:

- [ ] App is accessible via URL
  ```bash
  flyctl open
  ```

- [ ] All navigation links work
  - Overview page
  - Matches page
  - Players page
  - Maps page

- [ ] Data is present
  - Matches table shows data
  - Player statistics appear
  - No "No Data" messages

- [ ] No errors in logs
  ```bash
  flyctl logs --level error
  ```

- [ ] Health checks passing
  ```bash
  flyctl checks
  ```

## Rollback Plan

If deployment fails:

1. **View error logs**:
   ```bash
   flyctl logs --level error
   ```

2. **Check releases**:
   ```bash
   flyctl releases
   ```

3. **Rollback to previous version**:
   ```bash
   flyctl releases rollback <previous-version>
   ```

4. **Debug locally**:
   - Pull down the image: `flyctl ssh console`
   - Check files: `ls -la /app /data`
   - Run scripts manually

## Success Criteria

Deployment is successful when:

✅ Health checks are passing
✅ App loads in browser
✅ Data is visible (matches, players, etc.)
✅ Navigation works
✅ No errors in logs
✅ Response time is reasonable (<3 seconds)

## Notes

- First deployment takes 5-10 minutes (includes data import)
- Subsequent deployments take 2-5 minutes
- Volume persists across deployments
- Secrets persist (no need to reset)
```

#### Testing

Review checklist yourself and verify all items are actionable and clear.

#### Commit
```bash
git add docs/deployment/pre-deployment-checklist.md
git commit -m "docs: Add pre-deployment checklist

- Comprehensive checklist for first-time deployment
- Includes local testing steps
- Covers Fly.io setup requirements
- Provides post-deployment verification
- Includes rollback plan"
```

---

### Task 10: Add Health Check Endpoint (Optional but Recommended)
**Estimated Time**: 20 minutes
**Complexity**: Moderate
**Files to Modify**: `tournament_visualizer/app.py`

#### Context

Currently Fly.io health checks hit the home page `/`. This works but:
- Home page is heavy (runs dashboard queries)
- Slow health checks can cause false failures
- No explicit health information returned

A dedicated `/health` endpoint is lightweight and provides explicit status.

#### Implementation Steps

Open `tournament_visualizer/app.py` and add a health check endpoint.

Add after the imports (around line 22):

```python
from flask import jsonify
```

Add before the app layout (around line 82):

```python
# Health check endpoint for monitoring
@app.server.route('/health')
def health_check():
    """Health check endpoint for load balancers and monitoring.

    Returns:
        JSON response with health status and basic metrics
    """
    try:
        # Check database connectivity
        db = get_database()
        with db.get_connection() as conn:
            result = conn.execute("SELECT COUNT(*) FROM matches").fetchone()
            match_count = result[0] if result else 0

        # Return success with metrics
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "matches": match_count,
            "version": "1.0.0"
        }), 200

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        # Return error but with 503 (service unavailable)
        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }), 503
```

Update `fly.toml` to use the health endpoint. Find the http_checks section:

```toml
  [[services.http_checks]]
    interval = 30000        # 30 seconds
    timeout = 10000         # 10 seconds
    grace_period = "30s"
    method = "GET"
    path = "/"
    protocol = "http"
    tls_skip_verify = false
```

Change `path = "/"` to `path = "/health"`:

```toml
  [[services.http_checks]]
    interval = 30000        # 30 seconds
    timeout = 10000         # 10 seconds
    grace_period = "30s"
    method = "GET"
    path = "/health"
    protocol = "http"
    tls_skip_verify = false
```

#### Testing Strategy

**Test 1: Health endpoint returns 200**

Start the app:
```bash
uv run python manage.py start
```

Test health endpoint:
```bash
curl http://localhost:8050/health
```

**Expected output**:
```json
{
  "status": "healthy",
  "database": "connected",
  "matches": 42,
  "version": "1.0.0"
}
```

**Test 2: Health endpoint with Gunicorn**

```bash
PORT=8080 uv run gunicorn "tournament_visualizer.app:server" --config gunicorn.conf.py &
sleep 3
curl http://localhost:8080/health
```

**Test 3: Health endpoint in Docker**

```bash
docker build -t tournament-visualizer:test .
docker run --rm -p 8080:8080 --env-file .env tournament-visualizer:test &
sleep 5
curl http://localhost:8080/health
docker stop $(docker ps -q --filter ancestor=tournament-visualizer:test)
```

**Test 4: Health endpoint fails gracefully with no database**

```bash
# Temporarily move database
mv data/tournament_data.duckdb data/tournament_data.duckdb.bak

# Start app
uv run python manage.py start

# Test health (should return 503)
curl -i http://localhost:8050/health

# Restore database
mv data/tournament_data.duckdb.bak data/tournament_data.duckdb
```

**Expected output**:
```
HTTP/1.1 503 Service Unavailable
Content-Type: application/json

{
  "status": "unhealthy",
  "database": "disconnected",
  "error": "..."
}
```

**Test 5: Automated test**

Add to `tests/test_app.py` (create if doesn't exist):

```python
"""Test main application functionality."""

import pytest
from tournament_visualizer.app import app


@pytest.fixture
def client():
    """Create test client."""
    app.server.config['TESTING'] = True
    with app.server.test_client() as client:
        yield client


def test_health_check_returns_200(client):
    """Health check endpoint should return 200 when healthy."""
    response = client.get('/health')

    assert response.status_code == 200

    data = response.get_json()
    assert data['status'] == 'healthy'
    assert 'database' in data
    assert 'matches' in data
    assert 'version' in data


def test_health_check_has_database_connection(client):
    """Health check should verify database connectivity."""
    response = client.get('/health')
    data = response.get_json()

    assert data['database'] == 'connected'
    assert isinstance(data['matches'], int)
    assert data['matches'] >= 0


def test_health_check_returns_json(client):
    """Health check should return JSON content type."""
    response = client.get('/health')

    assert response.content_type == 'application/json'
```

Run test:
```bash
uv run pytest tests/test_app.py -v
```

#### Commit
```bash
git add tournament_visualizer/app.py fly.toml tests/test_app.py
git commit -m "feat: Add dedicated /health endpoint for monitoring

- Add lightweight health check endpoint
- Return JSON with status and metrics
- Update Fly.io health checks to use /health
- Add tests for health endpoint
- Return 503 on database errors"
```

---

### Task 11: Create Deployment Script
**Estimated Time**: 15 minutes
**Complexity**: Simple
**Files to Create**: `scripts/deploy.sh`

#### Context

Create a convenience script that runs pre-deployment checks and deploys to Fly.io. This:
- Automates common steps
- Reduces human error
- Documents the deployment process

#### Implementation Steps

Create `scripts/deploy.sh`:

```bash
#!/bin/bash
# Deployment script for Fly.io
#
# This script runs pre-deployment checks and deploys the application to Fly.io.
# It ensures code quality, runs tests, and verifies configuration before deploying.
#
# Usage:
#   ./scripts/deploy.sh [--skip-tests] [--skip-checks]

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
SKIP_TESTS=false
SKIP_CHECKS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --skip-checks)
            SKIP_CHECKS=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--skip-tests] [--skip-checks]"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}=== Old World Tournament Visualizer Deployment ===${NC}\n"

# Check we're in the project root
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}❌ Error: Must run from project root${NC}"
    exit 1
fi

# Check flyctl is installed
if ! command -v flyctl &> /dev/null; then
    echo -e "${RED}❌ Error: flyctl not found${NC}"
    echo "Install: https://fly.io/docs/hands-on/install-flyctl/"
    exit 1
fi

# Check we're authenticated
if ! flyctl auth whoami &> /dev/null; then
    echo -e "${RED}❌ Error: Not authenticated to Fly.io${NC}"
    echo "Run: flyctl auth login"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites check passed${NC}\n"

# Git status check
if ! $SKIP_CHECKS; then
    echo -e "${YELLOW}Checking git status...${NC}"

    if [ -n "$(git status --porcelain)" ]; then
        echo -e "${YELLOW}⚠️  Warning: Uncommitted changes detected${NC}"
        git status --short
        echo ""
        read -p "Continue with deployment? (y/N) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${RED}Deployment cancelled${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✅ Git working directory clean${NC}"
    fi
    echo ""
fi

# Run linting
if ! $SKIP_CHECKS; then
    echo -e "${YELLOW}Running code quality checks...${NC}"

    echo "  - Black (formatting)..."
    if ! uv run black --check tournament_visualizer/ scripts/; then
        echo -e "${RED}❌ Code formatting issues found${NC}"
        echo "Run: uv run black tournament_visualizer/ scripts/"
        exit 1
    fi

    echo "  - Ruff (linting)..."
    if ! uv run ruff check tournament_visualizer/ scripts/; then
        echo -e "${RED}❌ Linting issues found${NC}"
        echo "Run: uv run ruff check --fix tournament_visualizer/ scripts/"
        exit 1
    fi

    echo -e "${GREEN}✅ Code quality checks passed${NC}\n"
fi

# Run tests
if ! $SKIP_TESTS; then
    echo -e "${YELLOW}Running tests...${NC}"

    if ! uv run pytest -v; then
        echo -e "${RED}❌ Tests failed${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ All tests passed${NC}\n"
fi

# Verify fly.toml exists
if [ ! -f "fly.toml" ]; then
    echo -e "${RED}❌ Error: fly.toml not found${NC}"
    exit 1
fi

# Show what will be deployed
echo -e "${YELLOW}Deployment information:${NC}"
echo "  App: $(grep '^app = ' fly.toml | cut -d'"' -f2)"
echo "  Region: $(grep '^primary_region = ' fly.toml | cut -d'"' -f2)"
echo "  Branch: $(git branch --show-current)"
echo "  Commit: $(git log -1 --oneline)"
echo ""

# Confirm deployment
read -p "Deploy to Fly.io? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Deployment cancelled${NC}"
    exit 0
fi

# Deploy
echo -e "${GREEN}Deploying to Fly.io...${NC}\n"

if flyctl deploy; then
    echo -e "\n${GREEN}✅ Deployment successful!${NC}\n"

    # Show status
    echo -e "${YELLOW}App status:${NC}"
    flyctl status

    echo ""
    echo -e "${GREEN}View logs: ${NC}flyctl logs --follow"
    echo -e "${GREEN}Open app: ${NC}flyctl open"
else
    echo -e "\n${RED}❌ Deployment failed${NC}"
    echo -e "${YELLOW}Check logs: ${NC}flyctl logs"
    exit 1
fi
```

Make it executable:
```bash
chmod +x scripts/deploy.sh
```

#### Testing Strategy

**Test 1: Dry run (no actual deployment)**

Temporarily change the deploy command in script to echo:
```bash
# Change this line:
if flyctl deploy; then

# To:
if echo "Would run: flyctl deploy"; then
```

Run script:
```bash
./scripts/deploy.sh
```

Verify it runs all checks and prompts correctly.

Revert the change.

**Test 2: Test with skip flags**

```bash
# Skip tests only
./scripts/deploy.sh --skip-tests

# Skip all checks
./scripts/deploy.sh --skip-tests --skip-checks
```

**Test 3: Test error handling**

```bash
# Introduce a linting error temporarily
echo "x=1" >> tournament_visualizer/config.py

# Run deploy (should fail at linting)
./scripts/deploy.sh

# Revert
git checkout tournament_visualizer/config.py
```

Expected: Script should exit with error before deploying.

#### Commit
```bash
git add scripts/deploy.sh
git commit -m "feat: Add automated deployment script

- Run code quality checks before deploying
- Run tests to verify functionality
- Check git status for uncommitted changes
- Provide deployment confirmation prompt
- Show app status after successful deployment
- Add --skip-tests and --skip-checks flags"
```

---

### Task 12: Update README with Deployment Info
**Estimated Time**: 10 minutes
**Complexity**: Simple
**Files to Modify**: `README.md`

#### Context

Update the README to mention Fly.io deployment and link to documentation.

#### Implementation Steps

Open `README.md` and add a Deployment section. Find a good place (after Setup or Usage section) and add:

```markdown
## Deployment

### Fly.io (Recommended)

The application is production-ready for Fly.io deployment:

```bash
# First-time deployment
./scripts/deploy.sh
```

See [Fly.io Deployment Guide](docs/deployment/flyio-deployment-guide.md) for:
- First-time setup instructions
- Volume and secrets configuration
- Monitoring and troubleshooting
- Backup strategies

**Quick Start**:
1. Install [Fly.io CLI](https://fly.io/docs/hands-on/install-flyctl/)
2. Authenticate: `flyctl auth login`
3. Follow the [Pre-Deployment Checklist](docs/deployment/pre-deployment-checklist.md)
4. Deploy: `./scripts/deploy.sh`

**Cost**: ~$4-8/month for small tournaments

### Local Development

For local development, continue using:

```bash
uv run python manage.py start
```

See [Development Guide](docs/developer-guide.md) for details.
```

#### Testing

Review the changes in markdown viewer or GitHub preview.

#### Commit
```bash
git add README.md
git commit -m "docs: Add Fly.io deployment section to README

- Link to deployment guide
- Quick start instructions
- Mention deployment cost
- Link to pre-deployment checklist"
```

---

## Final Integration Testing

After completing all tasks, perform end-to-end testing:

### Local Docker Test

```bash
# Build image
docker build -t tournament-visualizer:final .

# Run container
docker run --rm -p 8080:8080 --env-file .env tournament-visualizer:final

# Test in browser
open http://localhost:8080

# Verify health endpoint
curl http://localhost:8080/health

# Stop container
docker stop $(docker ps -q --filter ancestor=tournament-visualizer:final)
```

### Full Deployment Test

```bash
# Run deployment script
./scripts/deploy.sh

# Monitor deployment
flyctl logs --follow

# Verify deployment
flyctl status
flyctl checks
flyctl open

# Check health endpoint
curl https://your-app.fly.dev/health
```

### Post-Deployment Verification

1. Open app in browser
2. Navigate to all pages (Overview, Matches, Players, Maps)
3. Verify data is present
4. Check for any errors in browser console
5. Review Fly.io logs: `flyctl logs`
6. Verify health checks: `flyctl checks`

---

## Troubleshooting Common Issues

### Issue: Release command times out

**Symptom**: Deployment fails during release command
**Cause**: Data download/import takes too long
**Solution**:
1. Increase timeout in fly.toml (add `timeout = "10m"` under `[deploy]`)
2. Or run import manually after deploy via SSH

### Issue: Volume not mounted

**Symptom**: Database errors, can't write to /data
**Cause**: Volume wasn't created or attached
**Solution**:
```bash
flyctl volumes list
flyctl volumes create tournament_data --size 1 --region <region>
```

### Issue: Secrets not set

**Symptom**: "challonge_tournament_id not found" error
**Cause**: Environment variables not set
**Solution**:
```bash
flyctl secrets set CHALLONGE_KEY="..."
flyctl secrets set CHALLONGE_USER="..."
flyctl secrets set challonge_tournament_id="..."
```

### Issue: Out of memory

**Symptom**: App crashes, logs show memory errors
**Cause**: 512MB insufficient for workload
**Solution**:
```bash
flyctl scale memory 1024
```

### Issue: Health checks failing

**Symptom**: App restarts constantly
**Cause**: Health check endpoint not responding
**Solution**:
1. Check logs: `flyctl logs --level error`
2. SSH in: `flyctl ssh console`
3. Test health manually: `curl http://localhost:8080/health`
4. Increase grace period in fly.toml

---

## Success Criteria

Deployment is complete when:

✅ All 12 tasks completed
✅ All tests pass locally
✅ Docker image builds and runs
✅ App deploys to Fly.io successfully
✅ Health checks pass
✅ Data is visible in production
✅ All documentation complete
✅ Deployment script works end-to-end

---

## Estimated Timeline

| Task | Description | Time | Cumulative |
|------|-------------|------|------------|
| 1 | Add Gunicorn dependency | 5 min | 5 min |
| 2 | Create Gunicorn config | 15 min | 20 min |
| 3 | Create Fly.io config | 20 min | 40 min |
| 4 | Update scripts | 25 min | 1h 5min |
| 5 | Add Procfile | 10 min | 1h 15min |
| 6 | Create deployment docs | 20 min | 1h 35min |
| 7 | Add .dockerignore | 5 min | 1h 40min |
| 8 | Update config | 15 min | 1h 55min |
| 9 | Create checklist | 10 min | 2h 5min |
| 10 | Add health endpoint | 20 min | 2h 25min |
| 11 | Create deploy script | 15 min | 2h 40min |
| 12 | Update README | 10 min | 2h 50min |
| | Testing & Verification | 1h | 3h 50min |

**Total: 3-4 hours for experienced developer**

---

## Commit Strategy

Follow these principles:
- **Atomic commits**: One logical change per commit
- **Commit after each task**: Don't batch multiple tasks
- **Good commit messages**: Use conventional commit format
- **Test before committing**: Each commit should be in working state

Example commit flow:
```bash
# Task 1
git add pyproject.toml uv.lock
git commit -m "feat: Add gunicorn dependency"

# Task 2
git add gunicorn.conf.py test_gunicorn_local.sh
git commit -m "feat: Add gunicorn configuration"

# etc...
```

---

## Additional Resources

- **Fly.io Documentation**: https://fly.io/docs/
- **Gunicorn Documentation**: https://docs.gunicorn.org/
- **Docker Best Practices**: https://docs.docker.com/develop/dev-best-practices/
- **Dash Deployment**: https://dash.plotly.com/deployment

---

## Next Steps After Deployment

Once deployed successfully:

1. **Set up monitoring** (optional)
   - Configure Fly.io monitoring alerts
   - Set up external uptime monitoring (UptimeRobot, etc.)

2. **Implement backups** (recommended)
   - Enable volume snapshots
   - Schedule periodic backups

3. **Add CI/CD** (optional)
   - GitHub Actions for automatic deployment
   - Run tests on pull requests

4. **Performance optimization** (if needed)
   - Add caching layer
   - Optimize database queries
   - Add CDN for static assets

5. **Custom domain** (optional)
   - Add custom domain to Fly.io
   - Configure SSL certificate

---

## Support

If you encounter issues:

1. Check logs: `flyctl logs --level error`
2. Review troubleshooting section above
3. Check Fly.io status: https://status.flyio.net/
4. Search Fly.io community: https://community.fly.io/
5. Create issue in this repository

---

## Conclusion

This plan provides a complete, step-by-step guide to deploying the Old World Tournament Visualizer to Fly.io. Each task is:

- **Self-contained**: Can be completed independently
- **Testable**: Includes testing strategy
- **Documented**: Provides context and rationale
- **Atomic**: Results in a single commit

Follow the tasks in order, test thoroughly, commit frequently, and you'll have a production-ready deployment! 🚀
