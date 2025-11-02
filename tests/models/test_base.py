"""Tests for database base configuration."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.base import Base, AsyncSessionLocal, engine, get_db_session


class TestDatabaseConfiguration:
    """Test database configuration and session management."""

    def test_base_model_metadata(self):
        """Test that Base model has proper metadata configuration."""
        assert Base.metadata is not None
        assert Base.metadata.naming_convention is not None
        
        # Check naming convention keys
        expected_keys = {"ix", "uq", "ck", "fk", "pk"}
        assert set(Base.metadata.naming_convention.keys()) == expected_keys

    def test_engine_configuration(self):
        """Test that async engine is properly configured."""
        assert engine is not None
        assert engine.url.drivername == "postgresql+asyncpg"
        # Access pool configuration through engine.pool
        assert engine.pool.size() == 10  # Default value
        assert engine.pool._max_overflow == 20  # Default value

    def test_session_factory_configuration(self):
        """Test that session factory is properly configured."""
        assert AsyncSessionLocal is not None
        assert AsyncSessionLocal.class_ == AsyncSession
        # Access session configuration through kw dict
        assert AsyncSessionLocal.kw.get('expire_on_commit') is False
        assert AsyncSessionLocal.kw.get('autoflush') is False
        assert AsyncSessionLocal.kw.get('autocommit') is False

    @pytest.mark.asyncio
    async def test_get_db_session_generator(self):
        """Test that get_db_session returns an async generator."""
        session_gen = get_db_session()
        assert hasattr(session_gen, '__aiter__')
        assert hasattr(session_gen, '__anext__')
        
        # Clean up the generator
        await session_gen.aclose()

    @pytest.mark.asyncio
    async def test_session_context_manager(self):
        """Test that session works as async context manager."""
        async with AsyncSessionLocal() as session:
            assert isinstance(session, AsyncSession)
            assert session.is_active