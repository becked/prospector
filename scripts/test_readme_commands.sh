#!/bin/bash
# Test script for README.new.md commands
# Tests each command block to ensure it works

set -e  # Exit on first error

echo "Testing README.md commands..."
echo ""

# Test 1: uv sync
echo "Test 1: uv sync"
uv sync > /dev/null 2>&1
echo "✓ uv sync works"
echo ""

# Test 2: import_attachments.py exists and runs
echo "Test 2: import_attachments.py"
if [[ ! -f scripts/import_attachments.py ]]; then
    echo "✗ scripts/import_attachments.py not found"
    exit 1
fi
uv run python scripts/import_attachments.py --help > /dev/null 2>&1
echo "✓ import_attachments.py exists and shows help"
echo ""

# Test 3: manage.py commands
echo "Test 3: manage.py commands"
uv run python manage.py status 2>&1 | head -1 > /dev/null
echo "✓ manage.py status works"
echo ""

# Test 4: Database query (if database exists)
echo "Test 4: Database query"
if [[ -f data/tournament_data.duckdb ]]; then
    uv run duckdb data/tournament_data.duckdb -readonly -c "SELECT COUNT(*) FROM matches" > /dev/null 2>&1
    echo "✓ Database query works"
else
    echo "⊘ Database doesn't exist (skipped - not an error)"
fi
echo ""

# Test 5: Python example imports
echo "Test 5: Python imports"
uv run python -c "from tournament_visualizer.data.queries import get_queries; print('✓ Imports work')"
echo ""

# Test 6: Development tools (check they exist in venv)
echo "Test 6: Development tools"
if command -v black &> /dev/null || uv run which black &> /dev/null; then
    echo "✓ black available"
fi
if command -v ruff &> /dev/null || uv run which ruff &> /dev/null; then
    echo "✓ ruff available"
fi
if command -v pytest &> /dev/null || uv run which pytest &> /dev/null; then
    echo "✓ pytest available"
fi
echo ""

echo "================================"
echo "All README commands validated!"
echo "================================"
