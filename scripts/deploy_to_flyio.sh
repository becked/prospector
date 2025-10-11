#!/usr/bin/env bash

# Fly.io Deployment Script for Old World Tournament Visualizer
# This script automates the deployment process with pre-checks and validation

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="prospector"
REGION="sjc"
VOLUME_NAME="tournament_data"

# Helper functions
print_header() {
    echo -e "\n${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Pre-deployment checks
print_header "Pre-Deployment Checks"

# Check if flyctl is installed
if ! command -v flyctl &> /dev/null; then
    print_error "flyctl is not installed"
    echo "Install: https://fly.io/docs/hands-on/install-flyctl/"
    exit 1
fi
print_success "flyctl is installed"

# Check if authenticated
if ! flyctl auth whoami &> /dev/null; then
    print_error "Not authenticated to Fly.io"
    echo "Run: flyctl auth login"
    exit 1
fi
print_success "Authenticated to Fly.io"

# Check if git repo is clean
if [[ -n $(git status -s) ]]; then
    print_warning "Git working directory has uncommitted changes"
    git status -s
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    print_success "Git working directory is clean"
fi

# Run tests
print_header "Running Tests"
if uv run pytest -v; then
    print_success "All tests passed"
else
    print_error "Tests failed"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if app exists
print_header "Checking App Status"
if flyctl apps list | grep -q "$APP_NAME"; then
    print_info "App '$APP_NAME' exists"

    # Show current status
    echo -e "\nCurrent app status:"
    flyctl status --app "$APP_NAME" || true

    # Check if volume exists
    if flyctl volumes list --app "$APP_NAME" | grep -q "$VOLUME_NAME"; then
        print_success "Volume '$VOLUME_NAME' exists"
    else
        print_error "Volume '$VOLUME_NAME' not found"
        read -p "Create volume now? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            flyctl volumes create "$VOLUME_NAME" --size 1 --region "$REGION" --app "$APP_NAME"
            print_success "Volume created"
        else
            exit 1
        fi
    fi

    # Check if secrets are set
    print_info "Checking secrets..."
    SECRETS=$(flyctl secrets list --app "$APP_NAME" 2>&1 || echo "")

    if echo "$SECRETS" | grep -q "CHALLONGE_KEY"; then
        print_success "CHALLONGE_KEY is set"
    else
        print_warning "CHALLONGE_KEY is not set"
        read -p "Set from .env file? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if [[ -f .env ]]; then
                source .env
                flyctl secrets set CHALLONGE_KEY="$CHALLONGE_KEY" --app "$APP_NAME"
                print_success "CHALLONGE_KEY set"
            else
                print_error ".env file not found"
                exit 1
            fi
        fi
    fi

    if echo "$SECRETS" | grep -q "CHALLONGE_USER"; then
        print_success "CHALLONGE_USER is set"
    else
        print_warning "CHALLONGE_USER is not set"
        read -p "Set from .env file? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if [[ -f .env ]]; then
                source .env
                flyctl secrets set CHALLONGE_USER="$CHALLONGE_USER" --app "$APP_NAME"
                print_success "CHALLONGE_USER set"
            else
                print_error ".env file not found"
                exit 1
            fi
        fi
    fi

    if echo "$SECRETS" | grep -q "challonge_tournament_id"; then
        print_success "challonge_tournament_id is set"
    else
        print_warning "challonge_tournament_id is not set"
        read -p "Set from .env file? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if [[ -f .env ]]; then
                source .env
                flyctl secrets set challonge_tournament_id="$challonge_tournament_id" --app "$APP_NAME"
                print_success "challonge_tournament_id set"
            else
                print_error ".env file not found"
                exit 1
            fi
        fi
    fi

else
    print_error "App '$APP_NAME' does not exist"
    echo ""
    print_info "First-time setup required:"
    echo "  1. Create app: flyctl launch --no-deploy"
    echo "  2. Create volume: flyctl volumes create $VOLUME_NAME --size 1 --region $REGION"
    echo "  3. Set secrets: flyctl secrets set CHALLONGE_KEY=... CHALLONGE_USER=... challonge_tournament_id=..."
    echo "  4. Run this script again"
    exit 1
fi

# Deploy
print_header "Deploying to Fly.io"
print_info "Starting deployment..."

if flyctl deploy --app "$APP_NAME"; then
    print_success "Deployment successful"
else
    print_error "Deployment failed"
    echo ""
    print_info "View logs: flyctl logs --app $APP_NAME"
    exit 1
fi

# Post-deployment verification
print_header "Post-Deployment Verification"

# Wait for deployment to stabilize
print_info "Waiting 10 seconds for deployment to stabilize..."
sleep 10

# Check status
print_info "Checking app status..."
flyctl status --app "$APP_NAME"

# Check health
print_info "Checking health endpoint..."
HEALTH_URL="https://${APP_NAME}.fly.dev/health"
if curl -f -s "$HEALTH_URL" | grep -q "healthy"; then
    print_success "Health check passed"
else
    print_warning "Health check did not return 'healthy'"
    curl -s "$HEALTH_URL" || true
fi

# Show logs
print_info "Recent logs (last 10 seconds):"
flyctl logs --app "$APP_NAME" || true

# Final summary
print_header "Deployment Complete"
print_success "App is deployed at: https://${APP_NAME}.fly.dev"
echo ""
print_info "Useful commands:"
echo "  View logs:   flyctl logs --app $APP_NAME"
echo "  View status: flyctl status --app $APP_NAME"
echo "  Open app:    flyctl open --app $APP_NAME"
echo "  SSH console: flyctl ssh console --app $APP_NAME"
echo ""
