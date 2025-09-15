# Production Dockerfile for ONEX Smart Responder Chain
FROM python:3.12-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 onex && \
    useradd --uid 1000 --gid onex --shell /bin/bash --create-home onex

# Set work directory
WORKDIR /app

# Install Poetry
RUN pip install poetry==1.8.0

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Configure poetry
RUN poetry config virtualenvs.create false

# Production stage
FROM base as production

# Install production dependencies
RUN poetry install --no-dev --extras "full"

# Copy application code
COPY src/ ./src/
COPY README.md ./

# Install the package
RUN pip install -e .

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/cache && \
    chown -R onex:onex /app

# Switch to non-root user
USER onex

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD omni-agent status || exit 1

# Default command
CMD ["omni-agent", "serve", "--host", "0.0.0.0", "--port", "8000"]

# Development stage
FROM base as development

# Install all dependencies including dev dependencies
RUN poetry install --extras "full"

# Copy application code
COPY . .

# Install in development mode
RUN pip install -e .

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/cache && \
    chown -R onex:onex /app

# Switch to non-root user
USER onex

# Default command for development
CMD ["omni-agent", "serve", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# CLI stage - lightweight container for CLI operations
FROM base as cli

# Install CLI dependencies only
RUN poetry install --no-dev --extras "cli"

# Copy application code
COPY src/ ./src/
COPY README.md ./

# Install the package
RUN pip install -e .

# Switch to non-root user
USER onex

# Set entrypoint to CLI
ENTRYPOINT ["omni-agent"]
CMD ["--help"]
