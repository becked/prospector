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
echo -e "${YELLOW}[1/5] Downloading attachments from Challonge (local)...${NC}"
if uv run python scripts/download_attachments.py; then
    echo -e "${GREEN}✓ Download complete${NC}"
else
    echo -e "${RED}Error: Failed to download attachments${NC}"
    echo "Check that CHALLONGE_KEY, CHALLONGE_USER, and challonge_tournament_id are set in environment"
    exit 1
fi
echo ""

# Step 2: Import attachments into DuckDB (locally - FAST!)
echo -e "${YELLOW}[2/5] Importing save files into DuckDB (local - fast!)...${NC}"
IMPORT_CMD="uv run python scripts/import_attachments.py --directory saves --verbose ${FORCE_FLAG}"
if ${IMPORT_CMD}; then
    echo -e "${GREEN}✓ Import complete${NC}"
else
    echo -e "${RED}Error: Failed to import attachments${NC}"
    exit 1
fi
echo ""

# Step 3: Upload new database via atomic replacement
echo -e "${YELLOW}[3/5] Uploading new database...${NC}"
DB_PATH="data/tournament_data.duckdb"
REMOTE_PATH="/data/tournament_data.duckdb"
REMOTE_TEMP_PATH="/data/tournament_data.duckdb.new"

if [ ! -f "${DB_PATH}" ]; then
    echo -e "${RED}Error: Database file not found at ${DB_PATH}${NC}"
    exit 1
fi

# Show file size for progress indication
DB_SIZE=$(du -h "${DB_PATH}" | cut -f1)
echo -e "${BLUE}Uploading ${DB_SIZE} database file to temporary location...${NC}"

# Upload to new filename (avoids file locking issues)
if echo "put ${DB_PATH} ${REMOTE_TEMP_PATH}" | fly ssh sftp shell -a "${APP_NAME}"; then
    echo -e "${GREEN}✓ Database uploaded to temporary location${NC}"
else
    echo -e "${RED}Error: Failed to upload database${NC}"
    exit 1
fi
echo ""

# Step 4: Verify upload succeeded
echo -e "${YELLOW}[4/5] Verifying upload...${NC}"

# Get local file size (macOS syntax)
LOCAL_SIZE=$(stat -f %z "${DB_PATH}" 2>/dev/null || stat -c %s "${DB_PATH}" 2>/dev/null)

# Get remote file size (Linux syntax on Fly.io)
# Extract just the number from output (may include connection messages)
REMOTE_SIZE=$(fly ssh console -a "${APP_NAME}" -C "stat -c %s ${REMOTE_TEMP_PATH}" 2>&1 | grep -oE '[0-9]+' | tail -n 1)

# Check if we got a valid number
if [ -z "$REMOTE_SIZE" ] || ! [[ "$REMOTE_SIZE" =~ ^[0-9]+$ ]]; then
    echo -e "${RED}Error: Could not verify remote file size${NC}"
    echo -e "${RED}Remote stat output: ${REMOTE_SIZE}${NC}"
    exit 1
fi

# Compare sizes
if [ "$LOCAL_SIZE" -eq "$REMOTE_SIZE" ]; then
    echo -e "${GREEN}✓ Upload verified (${LOCAL_SIZE} bytes)${NC}"
else
    echo -e "${RED}Error: File size mismatch${NC}"
    echo -e "${RED}Local: ${LOCAL_SIZE} bytes, Remote: ${REMOTE_SIZE} bytes${NC}"
    exit 1
fi
echo ""

# Step 5: Atomically replace database and restart
echo -e "${YELLOW}[5/5] Replacing database and restarting app...${NC}"

# Atomic move (replaces locked file while app is running)
if fly ssh console -a "${APP_NAME}" -C "mv ${REMOTE_TEMP_PATH} ${REMOTE_PATH}"; then
    echo -e "${GREEN}✓ Database replaced atomically${NC}"
else
    echo -e "${RED}Error: Failed to replace database${NC}"
    exit 1
fi

# Sync filesystem to ensure writes are committed
fly ssh console -a "${APP_NAME}" -C "sync" 2>/dev/null
echo -e "${GREEN}✓ Filesystem synced${NC}"

# Fix ownership
if fly ssh console -a "${APP_NAME}" -C "chown appuser:appuser ${REMOTE_PATH}"; then
    echo -e "${GREEN}✓ Ownership fixed${NC}"
else
    echo -e "${YELLOW}Warning: Could not fix ownership${NC}"
fi

# Fix permissions
if fly ssh console -a "${APP_NAME}" -C "chmod 664 ${REMOTE_PATH}"; then
    echo -e "${GREEN}✓ Permissions fixed${NC}"
else
    echo -e "${YELLOW}Warning: Could not fix permissions${NC}"
fi

# Sync filesystem to ensure writes are committed
fly ssh console -a "${APP_NAME}" -C "sync" 2>/dev/null

# Get machine ID for restart
MACHINE_ID=$(fly machine list -a "${APP_NAME}" 2>&1 | grep -E '^[a-z0-9]{14}' | awk '{print $1}')

if [ -z "$MACHINE_ID" ]; then
    echo -e "${YELLOW}Could not determine machine ID, using generic restart...${NC}"
    fly apps restart "${APP_NAME}"
else
    # Restart app to pick up new database
    echo -e "${BLUE}Restarting app to load new database...${NC}"
    if fly machine restart "${MACHINE_ID}" -a "${APP_NAME}"; then
        echo -e "${GREEN}✓ App restarted${NC}"

        # Wait for health checks
        echo -e "${BLUE}Waiting for health checks...${NC}"
        sleep 15

        # Check final status
        if fly status -a "${APP_NAME}" | grep -q "passing"; then
            echo -e "${GREEN}✓ Health checks passing${NC}"
        else
            echo -e "${YELLOW}Warning: Check health status manually with: fly status -a ${APP_NAME}${NC}"
        fi
    else
        echo -e "${RED}Error: Failed to restart machine${NC}"
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
