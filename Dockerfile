FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files first (for better Docker cache)
COPY ./pyproject.toml ./uv.lock ./alembic.ini ./logging.conf ./README.md /app/

# Install dependencies using uv (without installing the project yet)
# Use cache mount for uv cache to speed up builds
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --frozen --no-install-project

# Copy application code
COPY ./app /app/app
COPY ./migrations /app/migrations

# Now install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --frozen

# Create non-root user for security
RUN groupadd -r appuser && \
    useradd -r -g appuser -d /home/appuser -m appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use exec form for CMD (recommended by FastAPI docs)
CMD ["fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
