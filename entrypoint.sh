#!/bin/bash
set -e

echo "Starting entrypoint script..."
echo "TOURNAMENT_DB_PATH: $TOURNAMENT_DB_PATH"
echo "SAVES_DIRECTORY: $SAVES_DIRECTORY"
echo "Working directory: $(pwd)"

# Ensure directories exist
echo "Creating directories..."
mkdir -p /duckdb/db
mkdir -p /duckdb/saves

echo "Directory structure:"
ls -la /duckdb/

# Initialize database if it doesn't exist
if [ ! -f "$TOURNAMENT_DB_PATH" ]; then
    echo "Database not found at $TOURNAMENT_DB_PATH, initializing..."
    cd /app
    python -c "
import sys
sys.path.insert(0, '/app')
from tournament_visualizer.data.database import TournamentDatabase
db = TournamentDatabase(db_path='$TOURNAMENT_DB_PATH', read_only=False)
db.create_schema()
db.close()
print('Database initialized successfully')
"
else
    echo "Database already exists at $TOURNAMENT_DB_PATH"
fi

echo "Final directory check:"
ls -la /duckdb/db/

# Execute the main command
exec "$@"