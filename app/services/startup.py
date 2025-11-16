import asyncio
import logging

from app.models.base import AsyncSessionLocal
from app.services.setting import setting_service
from app.services.settings_cache import settings_cache
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
                admin_username = settings_cache.admin_username
                # Check if admin user already exists
                existing_admin = await user_service.get_user_by_username(
                    db, admin_username
                )

                if existing_admin:
                    logger.info(
                        f"Admin user '{admin_username}' already exists"
                    )
                    return

                # Create admin user
                admin_user = await user_service.create_user(
                    db=db,
                    username=admin_username,
                    password=settings_cache.admin_password,
                    email=settings_cache.admin_email,
                    is_admin=True,
                )

                logger.info(
                    f"Created admin user '{admin_user.username}' with ID {admin_user.id}"
                )

            except Exception as e:
                logger.error(f"Failed to create admin user: {e}")
                raise

    async def initialize_settings(self) -> None:
        """Initialize settings from config.py if they don't exist."""
        async with AsyncSessionLocal() as db:
            try:
                await setting_service.initialize_from_config(db)
            except Exception as e:
                logger.error(f"Failed to initialize settings: {e}")
                raise

    async def load_settings_cache(self) -> None:
        """Load settings from database into cache."""
        try:
            await settings_cache.load_from_database()
        except Exception as e:
            logger.error(f"Failed to load settings cache: {e}")
            raise

    async def startup(self) -> None:
        """
        Run all startup tasks.

        Note: This method is deprecated. Startup tasks are now handled
        directly in the FastAPI lifespan function for better integration.
        """
        logger.warning(
            "StartupService.startup() is deprecated. "
            "Use individual methods or handle in lifespan."
        )
        await self.run_database_migrations()
        await self.initialize_settings()
        await self.load_settings_cache()
        await self.create_admin_user()


# Global startup service instance
startup_service = StartupService()
