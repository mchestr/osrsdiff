from typing import AsyncGenerator

from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Note: Database connection initialization uses config.py directly because
# it's needed before the database is available to load settings from it.
# This is the only place where config.py should be used directly;
# all other services should use settings_cache from app.services.settings_cache.


class Base(DeclarativeBase):
    """Base class for all database models."""

    # Use consistent naming convention for constraints
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


# Create async engine with connection pooling
engine = create_async_engine(
    settings.database.url,
    echo=settings.database.echo,
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
    pool_pre_ping=True,  # Validate connections before use
    pool_recycle=settings.database.pool_recycle,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get database session.

    This function is designed to be used with FastAPI's dependency injection
    system to provide database sessions to API endpoints.

    Yields:
        AsyncSession: Database session for the request
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database connection for workers."""
    # Test the database connection
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))


async def close_db() -> None:
    """Close database engine and all connections."""
    await engine.dispose()
