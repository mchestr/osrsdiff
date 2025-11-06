"""Startup service for application initialization."""

import asyncio
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.base import AsyncSessionLocal
from app.services.user import user_service
from app.utils.migrations import run_migrations

logger = logging.getLogger(__name__)


class StartupService:
    """Service for handling application startup tasks."""

    async def run_database_migrations(self) -> None:
        """Run Alembic database migrations."""
        logger.info("Running database migrations...")
        # Run migrations in a thread pool since Alembic's command API is synchronous
        await asyncio.to_thread(run_migrations)

    async def create_admin_user(self) -> None:
        """Create default admin user if it doesn't exist."""
        async with AsyncSessionLocal() as db:
            try:
                # Check if admin user already exists
                existing_admin = await user_service.get_user_by_username(
                    db, settings.admin.username
                )

                if existing_admin:
                    logger.info(
                        f"Admin user '{settings.admin.username}' already exists"
                    )
                    return

                # Create admin user
                admin_user = await user_service.create_user(
                    db=db,
                    username=settings.admin.username,
                    password=settings.admin.password,
                    email=settings.admin.email,
                    is_admin=True,
                )

                logger.info(
                    f"Created admin user '{admin_user.username}' with ID {admin_user.id}"
                )

            except Exception as e:
                logger.error(f"Failed to create admin user: {e}")
                raise

    async def startup(self) -> None:
        """Run all startup tasks."""
        logger.info("Starting application initialization...")

        # Run database migrations (handles all schema changes)
        await self.run_database_migrations()

        # Create admin user
        await self.create_admin_user()

        logger.info("Application initialization completed")


# Global startup service instance
startup_service = StartupService()
