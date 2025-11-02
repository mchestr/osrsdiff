# Multi-stage Dockerfile for OSRS Diff service

FROM python:3.11-slim AS base

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

# Create app user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Copy package files needed for installation
COPY pyproject.toml README.md ./

# Install Python dependencies (extract from pyproject.toml)
RUN pip install \
    "fastapi>=0.104.0" \
    "uvicorn[standard]>=0.24.0" \
    "sqlalchemy[asyncio]>=2.0.0" \
    "asyncpg>=0.29.0" \
    "alembic>=1.12.0" \
    "taskiq>=0.11.0" \
    "taskiq-redis>=1.1.0" \
    "redis>=5.0.0" \
    "aiohttp>=3.9.0" \
    "python-jose[cryptography]>=3.3.0" \
    "passlib[bcrypt]>=1.7.4" \
    "python-multipart>=0.0.6" \
    "pydantic>=2.5.0" \
    "pydantic-settings>=2.1.0" \
    "python-dateutil>=2.8.2" \
    "structlog>=23.2.0"

# Install dev dependencies for base stage
RUN pip install \
    "pytest>=7.4.0" \
    "pytest-asyncio>=0.21.0" \
    "pytest-cov>=4.1.0" \
    "httpx>=0.25.0" \
    "factory-boy>=3.3.0" \
    "freezegun>=1.2.2" \
    "black>=23.0.0" \
    "isort>=5.12.0" \
    "mypy>=1.7.0" \
    "pytest-postgresql>=5.0.0" \
    "aiosqlite>=0.19.0"

# Development stage
FROM base AS development

# Copy source code
COPY . .

# Change ownership to app user
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Default command
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage  
FROM python:3.11-slim AS production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Install only production Python dependencies
RUN pip install \
    "fastapi>=0.104.0" \
    "uvicorn[standard]>=0.24.0" \
    "sqlalchemy[asyncio]>=2.0.0" \
    "asyncpg>=0.29.0" \
    "alembic>=1.12.0" \
    "taskiq>=0.11.0" \
    "taskiq-redis>=1.1.0" \
    "redis>=5.0.0" \
    "aiohttp>=3.9.0" \
    "python-jose[cryptography]>=3.3.0" \
    "passlib[bcrypt]>=1.7.4" \
    "python-multipart>=0.0.6" \
    "pydantic>=2.5.0" \
    "pydantic-settings>=2.1.0" \
    "python-dateutil>=2.8.2" \
    "structlog>=23.2.0"

# Copy source code
COPY src/ ./src/
COPY alembic.ini ./
COPY migrations/ ./migrations/

# Change ownership to app user
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]