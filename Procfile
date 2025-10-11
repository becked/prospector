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
