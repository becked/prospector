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
