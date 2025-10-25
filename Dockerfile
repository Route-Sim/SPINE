# Multi-stage Dockerfile for SPINE Application
# Stage 1: Builder - Install dependencies and build the application
FROM python:3.10-slim AS builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry with retry logic
RUN pip install --retries=5 poetry==1.8.3

# Configure Poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    POETRY_HTTP_TIMEOUT=300 \
    POETRY_REPOSITORIES_PYPI_URL=https://pypi.org/simple/

# Set working directory
WORKDIR /app

# Copy Poetry configuration files
COPY pyproject.toml poetry.lock ./

# Install dependencies with retry logic
RUN for i in {1..3}; do \
        poetry lock --no-update && \
        poetry install --only main --no-root --timeout=300 && \
        break || \
        (echo "Attempt $i failed, retrying..." && sleep 10); \
    done && \
    rm -rf $POETRY_CACHE_DIR

# Copy application code
COPY agents/ ./agents/
COPY core/ ./core/
COPY world/ ./world/

# Install the project itself with retry logic
RUN for i in {1..3}; do \
        poetry install --only main && \
        break || \
        (echo "Attempt $i failed, retrying..." && sleep 10); \
    done

# Stage 2: Runtime - Minimal production image
FROM python:3.10-slim AS runtime

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    LOG_LEVEL=INFO

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application code from builder stage
COPY --from=builder /app/agents ./agents
COPY --from=builder /app/core ./core
COPY --from=builder /app/world ./world
COPY --from=builder /app/pyproject.toml ./
COPY --from=builder /app/poetry.lock ./

# Install Poetry in runtime stage
RUN pip install --timeout=300 --retries=5 poetry==1.8.3

# Configure Poetry for runtime
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_HTTP_TIMEOUT=300

# Install only production dependencies
RUN poetry install --only main

# Verify installation using Poetry
RUN poetry run python -c "import uvicorn; print('uvicorn installed successfully')"

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD poetry run python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Run the application
CMD ["sh", "-c", "poetry run python -m world.sim.runner --host $HOST --port $PORT --log-level $LOG_LEVEL"]
