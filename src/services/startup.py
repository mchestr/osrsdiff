"""Startup service for application initialization."""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.base import AsyncSessionLocal, create_tables
from src.services.user import user_service

logger = logging.getLogger(__name__)


class StartupService:
    """Service for handling application startup tasks."""

    async def initialize_database(self) -> None:
        """Initialize database tables."""
        logger.info("Creating database tables...")
        await create_tables()
        logger.info("Database tables created successfully")

    async def create_admin_user(self) -> None:
        """Create default admin user if it doesn't exist."""
        async with AsyncSessionLocal() as db:
            try:
                # Check if admin user already exists
                existing_admin = await user_service.get_user_by_username(
                    db, settings.admin_username
                )
                
                if existing_admin:
                    logger.info(f"Admin user '{settings.admin_username}' already exists")
                    return

                # Create admin user
                admin_user = await user_service.create_user(
                    db=db,
                    username=settings.admin_username,
                    password=settings.admin_password,
                    email=settings.admin_email,
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
        
        # Initialize database
        await self.initialize_database()
        
        # Create admin user
        await self.create_admin_user()
        
        logger.info("Application initialization completed")


# Global startup service instance
startup_service = StartupService()