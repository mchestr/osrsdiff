# Technology Stack

## Core Framework & Language

- **Python 3.11+**: Modern async Python with type hints
- **FastAPI**: Async web framework for REST API endpoints
- **Uvicorn**: ASGI server for production deployment

## Database & Persistence

- **PostgreSQL 15**: Primary database with JSONB support
- **SQLAlchemy 2.0+**: Async ORM with declarative models
- **Asyncpg**: High-performance async PostgreSQL driver
- **Alembic**: Database migration management

## Task Queue & Caching

- **TaskIQ**: Modern async task queue for background jobs
- **Redis 7**: Task broker and caching layer

## Authentication & Security

- **JWT**: Token-based authentication with refresh tokens
- **python-jose**: JWT token handling with cryptography
- **passlib**: Password hashing with bcrypt

## HTTP & External APIs

- **aiohttp**: Async HTTP client for OSRS API integration
- **Pydantic**: Data validation and serialization

## Development Tools

- **Black**: Code formatting (line length: 88)
- **isort**: Import sorting with black profile
- **mypy**: Static type checking with strict settings
- **flake8**: Linting
- **pytest**: Testing with async support and coverage

## Build System & Dependencies

- **pyproject.toml**: Modern Python packaging with hatchling
- **mise**: Task runner and environment management
- **pip**: Package management with editable installs

## Common Commands

### Development Setup

```bash
# Install dependencies
mise run dev-install
# or: pip install -e .[dev]

# Start development environment
mise run docker:up
# or: docker-compose up -d

# Run locally (after starting postgres/redis)
mise run dev
# or: uvicorn src.main:app --reload

# Start background worker
mise run worker
# or: taskiq worker src.workers.main:broker
```

### Code Quality

```bash
# Format code
mise run format
# or: black src/ tests/ && isort src/ tests/

# Run linting
mise run lint
# or: flake8 src/ tests/ && mypy src/

# Type checking only
mise run typecheck
# or: mypy src/
```

### Testing

```bash
# Run tests
mise run test
# or: pytest

# Run with coverage
mise run test:cov
# or: pytest --cov=src --cov-report=html --cov-report=term
```

### Database Management

```bash
# Run migrations
mise run db:upgrade
# or: alembic upgrade head

# Create new migration
mise run db:revision -- "description"
# or: alembic revision --autogenerate -m "description"

# Rollback migration
mise run db:downgrade
# or: alembic downgrade -1
```

### Docker Operations

```bash
# Build images
mise run docker:build
# or: docker-compose build

# View logs
mise run docker:logs
# or: docker-compose logs -f

# Stop services
mise run docker:down
# or: docker-compose down
```

## Architecture Patterns

- **Async-first**: All I/O operations use async/await
- **Dependency Injection**: FastAPI's dependency system for services
- **Repository Pattern**: Service layer abstracts database operations
- **Background Tasks**: TaskIQ workers for OSRS API fetching
- **Clean Architecture**: Separation of API, business logic, and data layers
