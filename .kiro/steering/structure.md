# Project Structure

## Directory Organization

```
src/
├── __init__.py
├── main.py              # FastAPI application entry point
├── api/                 # REST API endpoints and routing
│   ├── __init__.py
│   ├── auth.py          # Authentication endpoints
│   ├── players.py       # Player management endpoints
│   ├── statistics.py    # Statistics and current data endpoints
│   └── history.py       # Historical progress endpoints
├── models/              # SQLAlchemy database models
│   ├── __init__.py
│   ├── base.py          # Base model class and database setup
│   ├── player.py        # Player model
│   └── hiscore.py       # HiscoreRecord model
├── services/            # Business logic layer
│   ├── __init__.py
│   ├── auth.py          # JWT authentication service
│   ├── player.py        # Player management service
│   ├── statistics.py    # Statistics retrieval service
│   ├── history.py       # Progress analysis service
│   └── osrs_api.py      # OSRS API client service
└── workers/             # Background task workers
    ├── __init__.py
    ├── main.py          # TaskIQ broker configuration
    └── fetch.py         # Hiscore data fetching tasks

tests/
├── __init__.py
├── conftest.py          # Pytest configuration and fixtures
├── api/                 # API endpoint tests
│   ├── __init__.py
│   ├── test_auth.py
│   ├── test_players.py
│   ├── test_statistics.py
│   └── test_history.py
├── models/              # Database model tests
│   ├── __init__.py
│   ├── test_player.py
│   └── test_hiscore.py
├── services/            # Service layer tests
│   ├── __init__.py
│   ├── test_auth.py
│   ├── test_player.py
│   ├── test_statistics.py
│   ├── test_history.py
│   └── test_osrs_api.py
└── workers/             # Background worker tests
    ├── __init__.py
    └── test_fetch.py

scripts/
└── init-db.sql          # Database initialization script

migrations/              # Alembic database migrations (auto-generated)
├── versions/
└── alembic.ini

.kiro/
├── steering/            # AI assistant guidance documents
└── specs/               # Feature specifications and design docs
```

## Code Organization Patterns

### API Layer (`src/api/`)

- Each module handles related endpoints (auth, players, statistics, history)
- Use FastAPI dependency injection for services and authentication
- Pydantic models for request/response validation
- Consistent error handling and HTTP status codes

### Models Layer (`src/models/`)

- SQLAlchemy async models with type hints
- Base model class with common fields (id, created_at, updated_at)
- Relationships defined with `Mapped` and `relationship()`
- JSON columns for flexible data storage (skills, bosses)

### Services Layer (`src/services/`)

- Business logic separated from API and database concerns
- Async methods for all I/O operations
- Dependency injection for database sessions and external clients
- Error handling with custom exceptions

### Workers Layer (`src/workers/`)

- TaskIQ background tasks for OSRS API fetching
- Retry logic and error handling for external API calls
- Rate limiting compliance for OSRS API
- Task scheduling and periodic execution

## File Naming Conventions

- **Snake case** for all Python files and directories
- **Descriptive names** that indicate purpose (e.g., `osrs_api.py`, `fetch.py`)
- **Plural nouns** for collections (e.g., `players.py`, `statistics.py`)
- **Test files** prefixed with `test_` matching source structure

## Import Organization

Follow isort configuration with black profile:

```python
# Standard library imports
import asyncio
from datetime import datetime
from typing import Optional, List

# Third-party imports
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

# Local imports
from src.models.player import Player
from src.services.player import PlayerService
```

## Configuration Management

- **Environment variables** for all configuration
- **Pydantic Settings** for validation and type safety
- **`.env.example`** file documenting all required variables
- **Separate configs** for development, testing, and production

## Database Conventions

- **Async SQLAlchemy** with `AsyncSession` for all database operations
- **Alembic migrations** for schema changes
- **Foreign key constraints** with proper relationships
- **JSON columns** for flexible nested data (skills, bosses)
- **Indexes** on frequently queried columns (username, fetched_at)

## Testing Structure

- **Mirror source structure** exactly in test directories
- **Test files** prefixed with `test_` and match corresponding source files
- **Async test fixtures** for database and external services
- **Factory pattern** for test data generation
- **Separate unit and integration tests** with pytest markers
- **Same directory hierarchy** as `src/` for easy navigation and maintenance
