#!/bin/bash
# Script to sync tournament data on Fly.io production server
# Runs locally but executes commands remotely via flyctl ssh
#
# Usage: ./scripts/sync_tournament_data.sh [options] [app-name]
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
            echo "Usage: ./scripts/sync_tournament_data.sh [--force] [app-name]"
            exit 1
            ;;
        *)
            APP_NAME="$1"
            shift
            ;;
    esac
done

echo "======================================"
echo "Fly.io Tournament Data Sync"
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

# Verify we can access the app
echo -e "${YELLOW}Verifying app access...${NC}"
if ! fly status -a "${APP_NAME}" &> /dev/null; then
    echo -e "${RED}Error: Cannot access app '${APP_NAME}'${NC}"
    echo "Make sure you're logged in: fly auth login"
    echo "Or specify a different app: ./scripts/sync_tournament_data.sh [--force] <app-name>"
    exit 1
fi
echo -e "${GREEN}✓ App accessible${NC}"
echo ""

# Step 1: Download attachments from Challonge (on remote server)
echo -e "${YELLOW}[1/3] Downloading attachments from Challonge (remote)...${NC}"
if fly ssh console -a "${APP_NAME}" -C "python scripts/download_attachments.py"; then
    echo -e "${GREEN}✓ Download complete${NC}"
else
    echo -e "${RED}Error: Failed to download attachments${NC}"
    echo "Check that CHALLONGE_KEY, CHALLONGE_USER, and challonge_tournament_id are set as secrets"
    exit 1
fi
echo ""

# Step 2: Import attachments into DuckDB (on remote server)
echo -e "${YELLOW}[2/3] Importing save files into DuckDB (remote)...${NC}"
IMPORT_CMD="python scripts/import_attachments.py --directory /data/saves --verbose ${FORCE_FLAG}"
if fly ssh console -a "${APP_NAME}" -C "${IMPORT_CMD}"; then
    echo -e "${GREEN}✓ Import complete${NC}"
else
    echo -e "${RED}Error: Failed to import attachments${NC}"
    exit 1
fi
echo ""

# Step 3: Restart the app to pick up new data
echo -e "${YELLOW}[3/3] Restarting app to load new data...${NC}"
if fly apps restart "${APP_NAME}"; then
    echo -e "${GREEN}✓ App restarted${NC}"
else
    echo -e "${RED}Error: Failed to restart app${NC}"
    echo "You may need to restart manually with: fly apps restart ${APP_NAME}"
    exit 1
fi

echo ""
echo "======================================"
echo -e "${GREEN}Sync Complete!${NC}"
echo "======================================"
echo ""
echo "The production database has been updated with the latest tournament data."
echo "The app has been restarted to load the new data."
echo ""
echo "View the app at: https://${APP_NAME}.fly.dev"
echo ""
echo "To check logs: fly logs -a ${APP_NAME}"
