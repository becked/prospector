#!/bin/bash
# Script to sync tournament data by processing LOCALLY and uploading to Fly.io
# This is much faster than processing on Fly.io due to better CPU/disk performance
#
# Usage: ./scripts/sync_tournament_data_local.sh [options] [app-name]
# Options:
#   --force                Force reimport of all files (clears existing data)
#   --generate-narratives  Generate AI match narratives (requires ANTHROPIC_API_KEY)
# Default app name: prospector

set -e  # Exit on error

# Load environment variables from .env if it exists
if [ -f .env ]; then
    set -a  # Automatically export all variables
    source .env
    set +a  # Disable automatic export
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
FORCE_FLAG=""
GENERATE_NARRATIVES=false
APP_NAME="prospector"

while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE_FLAG="--force"
            shift
            ;;
        --generate-narratives)
            GENERATE_NARRATIVES=true
            shift
            ;;
        -*)
            echo -e "${RED}Error: Unknown option $1${NC}"
            echo "Usage: ./scripts/sync_tournament_data_local.sh [--force] [--generate-narratives] [app-name]"
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
if [ "$GENERATE_NARRATIVES" = true ]; then
    echo -e "${BLUE}Narrative generation: Enabled${NC}"
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

# Step 1.5: Generate Google Drive mapping (if API key configured)
if [ -n "${GOOGLE_DRIVE_API_KEY}" ]; then
    echo -e "${YELLOW}[1.5/6] Generating Google Drive mapping...${NC}"
    if uv run python scripts/generate_gdrive_mapping.py --output data/gdrive_match_mapping.json; then
        echo -e "${GREEN}✓ GDrive mapping generated${NC}"
    else
        echo -e "${YELLOW}⚠ GDrive mapping generation failed (will skip GDrive files)${NC}"
    fi
    echo ""
fi

# Step 2: Import attachments into DuckDB (locally - FAST!)
echo -e "${YELLOW}[2/8] Importing save files into DuckDB (local - fast!)...${NC}"
IMPORT_CMD="uv run python scripts/import_attachments.py --directory saves --verbose ${FORCE_FLAG}"
if ${IMPORT_CMD}; then
    echo -e "${GREEN}✓ Import complete${NC}"
else
    echo -e "${RED}Error: Failed to import attachments${NC}"
    exit 1
fi
echo ""

# Step 2.3: Sync Challonge participants (if configured)
if [ -n "${CHALLONGE_KEY}" ] && [ -n "${CHALLONGE_USER}" ] && [ -n "${challonge_tournament_id}" ]; then
    echo -e "${YELLOW}[2.3/8] Syncing Challonge participants...${NC}"
    if uv run python scripts/sync_challonge_participants.py; then
        echo -e "${GREEN}✓ Participants synced${NC}"

        # Step 2.4: Link players to participants
        echo -e "${YELLOW}[2.4/8] Linking players to participants...${NC}"
        if uv run python scripts/link_players_to_participants.py; then
            echo -e "${GREEN}✓ Players linked to participants${NC}"
        else
            echo -e "${YELLOW}⚠ Player linking failed (pick order features may not work)${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ Participant sync failed (pick order features may not work)${NC}"
    fi
    echo ""
else
    echo -e "${BLUE}[2.3/8] Skipping participant sync (Challonge credentials not configured)${NC}"
    echo -e "${BLUE}[2.4/8] Skipping player linking (requires participants)${NC}"
    echo ""
fi

# Step 2.5: Sync pick order data from Google Sheets (if configured)
if [ -n "${GOOGLE_DRIVE_API_KEY}" ] && [ -n "${GOOGLE_SHEETS_SPREADSHEET_ID}" ]; then
    echo -e "${YELLOW}[2.5/8] Syncing pick order data from Google Sheets...${NC}"
    if uv run python scripts/sync_pick_order_data.py; then
        echo -e "${GREEN}✓ Pick order data synced${NC}"

        echo -e "${YELLOW}[2.6/8] Matching pick order games to matches...${NC}"
        if uv run python scripts/match_pick_order_games.py; then
            echo -e "${GREEN}✓ Pick order games matched${NC}"
        else
            echo -e "${YELLOW}⚠ Pick order matching failed (non-critical)${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ Pick order sync failed (will skip)${NC}"
    fi
    echo ""
else
    echo -e "${BLUE}[2.5/8] Skipping pick order sync (API key or spreadsheet ID not configured)${NC}"
    echo ""
fi

# Step 2.7: Generate match narratives (if requested via flag)
if [ "$GENERATE_NARRATIVES" = true ]; then
    if [ -n "${ANTHROPIC_API_KEY}" ]; then
        echo -e "${YELLOW}[2.7/8] Generating match narratives...${NC}"
        if uv run python scripts/generate_match_narratives.py; then
            echo -e "${GREEN}✓ Match narratives generated${NC}"
        else
            echo -e "${YELLOW}⚠ Narrative generation failed (non-critical, continuing...)${NC}"
        fi
        echo ""
    else
        echo -e "${YELLOW}[2.7/8] Cannot generate narratives: ANTHROPIC_API_KEY not configured${NC}"
        echo ""
    fi
else
    echo -e "${BLUE}[2.7/8] Skipping narrative generation (use --generate-narratives to enable)${NC}"
    echo ""
fi

# Step 3: Upload new database via atomic replacement
echo -e "${YELLOW}[3/8] Uploading new database...${NC}"
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
echo -e "${YELLOW}[4/8] Verifying upload...${NC}"

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
echo -e "${YELLOW}[5/8] Replacing database and restarting app...${NC}"

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
