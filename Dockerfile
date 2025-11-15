# Production Dockerfile: Multi-stage build combining frontend and backend
# Stage 1: Build frontend React application
FROM node:25-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package.json frontend/package-lock.json* ./

# Clear npm cache and install frontend dependencies
# Remove any existing node_modules to avoid version conflicts
RUN rm -rf node_modules && \
    npm cache clean --force && \
    npm ci

# Copy frontend source code (including generated API client if it exists)
COPY frontend/ ./

# Build frontend (outputs to dist/)
RUN npm run build

# Stage 2: Backend Python application
FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    libpq-dev \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files first (for better Docker cache)
COPY ./pyproject.toml ./uv.lock ./alembic.ini ./README.md /app/

# Install dependencies using uv (without installing the project yet)
# Use cache mount for uv cache to speed up builds
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --frozen --no-install-project

# Copy application code
COPY ./app /app/app
COPY ./migrations /app/migrations
COPY ./templates /app/templates

# Copy built frontend static files from frontend-builder stage
COPY --from=frontend-builder /app/frontend/dist /app/static

# Now install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --frozen

# Create non-root user for security
RUN groupadd -r appuser && \
    useradd -r -g appuser -d /home/appuser -m appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Use exec form for CMD (recommended by FastAPI docs)
CMD ["fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
