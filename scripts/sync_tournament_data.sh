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

# Step 3: Stop the app (closes database connections)
echo -e "${YELLOW}[3/6] Stopping app to close database connections...${NC}"

# Get machine ID from machine list (match lines starting with machine ID pattern)
MACHINE_ID=$(fly machine list -a "${APP_NAME}" 2>&1 | grep -E '^[a-z0-9]{14}' | awk '{print $1}')

if [ -z "$MACHINE_ID" ]; then
    echo -e "${RED}Error: Could not determine machine ID${NC}"
    echo "Run 'fly machine list -a ${APP_NAME}' to see machines"
    exit 1
fi

echo -e "${BLUE}Stopping machine ${MACHINE_ID}...${NC}"
if fly machine stop "${MACHINE_ID}" -a "${APP_NAME}"; then
    echo -e "${GREEN}✓ App stopped${NC}"
else
    echo -e "${RED}Error: Failed to stop app${NC}"
    exit 1
fi
echo ""

# Step 4: Remove old database files (including WAL)
echo -e "${YELLOW}[4/6] Removing old database files...${NC}"
REMOTE_PATH="/data/tournament_data.duckdb"
if fly ssh console -a "${APP_NAME}" -C "rm -f ${REMOTE_PATH} ${REMOTE_PATH}.wal ${REMOTE_PATH}.shm"; then
    echo -e "${GREEN}✓ Old database files removed${NC}"
else
    echo -e "${YELLOW}Warning: Could not remove old files (may not exist)${NC}"
fi
echo ""

# Step 5: Upload new database to Fly.io
echo -e "${YELLOW}[5/6] Uploading new database to Fly.io...${NC}"
DB_PATH="data/tournament_data.duckdb"

if [ ! -f "${DB_PATH}" ]; then
    echo -e "${RED}Error: Database file not found at ${DB_PATH}${NC}"
    exit 1
fi

# Show file size for progress indication
DB_SIZE=$(du -h "${DB_PATH}" | cut -f1)
echo -e "${BLUE}Uploading ${DB_SIZE} database file...${NC}"

# Use fly ssh sftp to upload the file
if echo "put ${DB_PATH} ${REMOTE_PATH}" | fly ssh sftp shell -a "${APP_NAME}"; then
    echo -e "${GREEN}✓ Database uploaded${NC}"
else
    echo -e "${RED}Error: Failed to upload database${NC}"
    echo "Attempting to restart app anyway..."
    fly apps restart "${APP_NAME}"
    exit 1
fi

# Fix file permissions (app runs as appuser uid:1000 gid:1000)
echo -e "${BLUE}Fixing file ownership and permissions...${NC}"
if fly ssh console -a "${APP_NAME}" -C "chown appuser:appuser ${REMOTE_PATH} && chmod 664 ${REMOTE_PATH}"; then
    echo -e "${GREEN}✓ Permissions fixed${NC}"
else
    echo -e "${RED}Error: Failed to fix permissions${NC}"
    exit 1
fi
echo ""

# Step 6: Start the app to load new data
echo -e "${YELLOW}[6/6] Starting app to load new data...${NC}"

# Machine ID should still be set from step 3
if [ -z "$MACHINE_ID" ]; then
    # Try to get it again if somehow lost
    MACHINE_ID=$(fly machine list -a "${APP_NAME}" 2>&1 | grep -E '^[a-z0-9]{14}' | awk '{print $1}')
fi

if [ -z "$MACHINE_ID" ]; then
    echo -e "${YELLOW}Could not determine machine ID, using restart...${NC}"
    fly apps restart "${APP_NAME}"
else
    echo -e "${BLUE}Starting machine ${MACHINE_ID}...${NC}"
    if fly machine start "${MACHINE_ID}" -a "${APP_NAME}"; then
        echo -e "${GREEN}✓ App started${NC}"

        # Wait for health checks
        echo -e "${BLUE}Waiting for health checks...${NC}"
        sleep 15

        # Check final status
        if fly status -a "${APP_NAME}" | grep -q "passing"; then
            echo -e "${GREEN}✓ Health checks passing${NC}"
        else
            echo -e "${YELLOW}Warning: Check health status manually${NC}"
        fi
    else
        echo -e "${RED}Error: Failed to start machine${NC}"
        exit 1
    fi
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
