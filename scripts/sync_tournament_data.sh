#!/bin/bash
# Script to sync tournament data by processing LOCALLY and uploading to Fly.io
# This is much faster than processing on Fly.io due to better CPU/disk performance
#
# Usage: ./scripts/sync_tournament_data_local.sh [options] [app-name]
# Options:
#   --force    Force reimport of all files (clears existing data)
# Default app name: prospector

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
FORCE_FLAG=""
APP_NAME="prospector"

while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE_FLAG="--force"
            shift
            ;;
        -*)
            echo -e "${RED}Error: Unknown option $1${NC}"
            echo "Usage: ./scripts/sync_tournament_data_local.sh [--force] [app-name]"
            exit 1
            ;;
        *)
            APP_NAME="$1"
            shift
            ;;
    esac
done

echo "======================================"
echo "Tournament Data Sync (Local Processing)"
echo "======================================"
echo -e "${BLUE}App: ${APP_NAME}${NC}"
if [ -n "$FORCE_FLAG" ]; then
    echo -e "${YELLOW}Mode: Force reimport (existing data will be cleared)${NC}"
fi
echo ""

# Check if flyctl is installed
if ! command -v fly &> /dev/null; then
    echo -e "${RED}Error: flyctl is not installed${NC}"
    echo "Install it from: https://fly.io/docs/hands-on/install-flyctl/"
    exit 1
fi

# Check if uv is installed (for running Python scripts)
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv is not installed${NC}"
    echo "Install it from: https://docs.astral.sh/uv/"
    exit 1
fi

# Verify we can access the app
echo -e "${YELLOW}Verifying app access...${NC}"
if ! fly status -a "${APP_NAME}" &> /dev/null; then
    echo -e "${RED}Error: Cannot access app '${APP_NAME}'${NC}"
    echo "Make sure you're logged in: fly auth login"
    echo "Or specify a different app: ./scripts/sync_tournament_data_local.sh [--force] <app-name>"
    exit 1
fi
echo -e "${GREEN}✓ App accessible${NC}"
echo ""

# Step 1: Download attachments from Challonge (locally)
echo -e "${YELLOW}[1/6] Downloading attachments from Challonge (local)...${NC}"
if uv run python scripts/download_attachments.py; then
    echo -e "${GREEN}✓ Download complete${NC}"
else
    echo -e "${RED}Error: Failed to download attachments${NC}"
    echo "Check that CHALLONGE_KEY, CHALLONGE_USER, and challonge_tournament_id are set in environment"
    exit 1
fi
echo ""

# Step 2: Import attachments into DuckDB (locally - FAST!)
echo -e "${YELLOW}[2/6] Importing save files into DuckDB (local - fast!)...${NC}"
IMPORT_CMD="uv run python scripts/import_attachments.py --directory saves --verbose ${FORCE_FLAG}"
if ${IMPORT_CMD}; then
    echo -e "${GREEN}✓ Import complete${NC}"
else
    echo -e "${RED}Error: Failed to import attachments${NC}"
    exit 1
fi
echo ""

# Step 3: Upload new database to temporary location (while app is running)
echo -e "${YELLOW}[3/6] Uploading new database to temporary location...${NC}"
DB_PATH="data/tournament_data.duckdb"
REMOTE_PATH="/data/tournament_data.duckdb"
REMOTE_TEMP="/data/tournament_data.duckdb.new"

if [ ! -f "${DB_PATH}" ]; then
    echo -e "${RED}Error: Database file not found at ${DB_PATH}${NC}"
    exit 1
fi

# Show file size for progress indication
DB_SIZE=$(du -h "${DB_PATH}" | cut -f1)
echo -e "${BLUE}Uploading ${DB_SIZE} database file to temporary location...${NC}"

# Upload to temporary file (app can keep running)
if echo "put ${DB_PATH} ${REMOTE_TEMP}" | fly ssh sftp shell -a "${APP_NAME}"; then
    echo -e "${GREEN}✓ Database upload command completed${NC}"

    # Verify the file was actually uploaded
    echo -e "${BLUE}Verifying upload...${NC}"

    # Use wc -c which is portable across Linux and macOS
    REMOTE_SIZE=$(fly ssh console -a "${APP_NAME}" -C "wc -c < ${REMOTE_TEMP} 2>/dev/null || echo 0" | tr -d ' ')
    LOCAL_SIZE=$(wc -c < "${DB_PATH}" | tr -d ' ')

    if [ "$REMOTE_SIZE" -eq "$LOCAL_SIZE" ] 2>/dev/null; then
        echo -e "${GREEN}✓ Upload verified (${LOCAL_SIZE} bytes)${NC}"
    else
        echo -e "${RED}Error: Upload verification failed${NC}"
        echo -e "${RED}Local: ${LOCAL_SIZE} bytes, Remote: ${REMOTE_SIZE} bytes${NC}"

        # Try to check if file exists at all
        if fly ssh console -a "${APP_NAME}" -C "test -f ${REMOTE_TEMP}"; then
            echo -e "${YELLOW}File exists but size mismatch - upload may be incomplete${NC}"
        else
            echo -e "${RED}File does not exist on remote${NC}"
        fi
        exit 1
    fi
else
    echo -e "${RED}Error: Failed to upload database${NC}"
    exit 1
fi
echo ""

# Step 4: Stop the app (closes database connections)
echo -e "${YELLOW}[4/6] Stopping app to close database connections...${NC}"

# Get machine ID from machine list (match lines starting with machine ID pattern)
MACHINE_ID=$(fly machine list -a "${APP_NAME}" 2>&1 | grep -E '^[a-z0-9]{14}' | awk '{print $1}')

if [ -z "$MACHINE_ID" ]; then
    echo -e "${RED}Error: Could not determine machine ID${NC}"
    echo "Run 'fly machine list -a ${APP_NAME}' to see machines"
    exit 1
fi

echo -e "${BLUE}Stopping machine ${MACHINE_ID}...${NC}"
if fly machine stop "${MACHINE_ID}" -a "${APP_NAME}"; then
    echo -e "${GREEN}✓ Stop initiated${NC}"
else
    echo -e "${RED}Error: Failed to stop app${NC}"
    exit 1
fi

# Wait for machine to fully stop
echo -e "${BLUE}Waiting for machine to fully stop...${NC}"
MAX_WAIT=30
WAIT_COUNT=0
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    # Get just the state value from the first "State:" line
    STATE=$(fly machine status "${MACHINE_ID}" -a "${APP_NAME}" 2>&1 | grep "^State:" | head -1 | awk '{print $2}')
    if [ "$STATE" = "stopped" ]; then
        echo -e "${GREEN}✓ Machine fully stopped${NC}"
        break
    fi
    echo -e "${BLUE}  Machine state: ${STATE}, waiting...${NC}"
    sleep 2
    WAIT_COUNT=$((WAIT_COUNT + 1))
done

if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
    echo -e "${YELLOW}Warning: Machine may not have fully stopped, attempting start anyway...${NC}"
fi
echo ""

# Step 5: Start the app (will have clean DB state)
echo -e "${YELLOW}[5/6] Starting app...${NC}"
echo -e "${BLUE}Starting machine ${MACHINE_ID}...${NC}"
if fly machine start "${MACHINE_ID}" -a "${APP_NAME}"; then
    echo -e "${GREEN}✓ App started${NC}"

    # Wait for machine to fully start and SSH to be available
    echo -e "${BLUE}Waiting for SSH to be ready...${NC}"
    sleep 10
else
    echo -e "${RED}Error: Failed to start machine${NC}"
    exit 1
fi
echo ""

# Step 6: Replace old database with new one
echo -e "${YELLOW}[6/6] Replacing database and fixing permissions...${NC}"

# Remove old database files and move new one into place
REPLACE_CMD="rm -f ${REMOTE_PATH} ${REMOTE_PATH}.wal ${REMOTE_PATH}.shm && mv ${REMOTE_TEMP} ${REMOTE_PATH} && chown appuser:appuser ${REMOTE_PATH} && chmod 664 ${REMOTE_PATH}"

if fly ssh console -a "${APP_NAME}" -C "${REPLACE_CMD}"; then
    echo -e "${GREEN}✓ Database replaced and permissions fixed${NC}"
else
    echo -e "${RED}Error: Failed to replace database${NC}"
    exit 1
fi

# Restart app to pick up new database
echo -e "${BLUE}Restarting app to load new database...${NC}"
if fly machine restart "${MACHINE_ID}" -a "${APP_NAME}" --skip-health-checks; then
    echo -e "${GREEN}✓ App restarted${NC}"
else
    echo -e "${YELLOW}Warning: Restart may have failed, trying alternative method...${NC}"
    fly apps restart "${APP_NAME}"
fi

# Wait for health checks
echo -e "${BLUE}Waiting for health checks...${NC}"
sleep 15

# Check final status
if fly status -a "${APP_NAME}" | grep -q "passing"; then
    echo -e "${GREEN}✓ Health checks passing${NC}"
else
    echo -e "${YELLOW}Warning: Check health status manually with: fly status -a ${APP_NAME}${NC}"
fi

echo ""
echo "======================================"
echo -e "${GREEN}Sync Complete!${NC}"
echo "======================================"
echo ""
echo "The production database has been updated with the latest tournament data."
echo "The app has been restarted to load the new data."
echo ""
echo -e "${BLUE}Performance benefit:${NC} Processing locally is ~10x faster than on Fly.io!"
echo ""
echo "View the app at: https://${APP_NAME}.fly.dev"
echo ""
echo "To check logs: fly logs -a ${APP_NAME}"
echo ""
