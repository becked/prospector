# Dockerfile for Old World Tournament Visualizer
# Multi-stage build for smaller final image

# Stage 1: Build stage - install dependencies
FROM python:3.11-slim AS builder

# Install system dependencies needed for Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package installer)
# Download and install uv, then move to a location accessible to all layers
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    mv /root/.local/bin/uvx /usr/local/bin/uvx

# Set working directory
WORKDIR /app

# Copy dependency files and source code for building
COPY pyproject.toml uv.lock README.md ./
COPY tournament_visualizer/ ./tournament_visualizer/

# Install dependencies and package using uv
RUN uv sync --frozen --no-dev

# Stage 2: Runtime stage - minimal image
FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Set environment variables EARLY - before any Python code runs
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app:${PYTHONPATH}"
ENV PYTHONUNBUFFERED=1
ENV SAVES_DIRECTORY=/duckdb/saves
ENV TOURNAMENT_DB_PATH=/duckdb/db/tournament_data.duckdb
ENV PORT=8080
ENV FLASK_ENV=production

# Copy installed dependencies from builder
COPY --from=builder /app/.venv /app/.venv

# Copy entrypoint script BEFORE switching user
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Copy application code with proper structure
COPY --chown=appuser:appuser pyproject.toml uv.lock README.md ./
COPY --chown=appuser:appuser tournament_visualizer/ ./tournament_visualizer/
COPY --chown=appuser:appuser gunicorn.conf.py ./

# Create directories for duckdb data and logs
RUN mkdir -p /duckdb/saves /duckdb/db logs && \
    chown -R appuser:appuser /duckdb logs /app/entrypoint.sh

# Switch to non-root user
USER appuser

# Declare volume for persistent data
VOLUME ["/duckdb"]

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Command to run - uses gunicorn with our config
CMD ["gunicorn", "tournament_visualizer.app:server", "--config", "gunicorn.conf.py"]