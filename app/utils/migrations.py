import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.config import settings

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    """
    Run Alembic migrations to the latest version.

    This function runs migrations synchronously using Alembic's command API.
    It should be called from an async context using asyncio.to_thread() or
    similar if needed.
    """
    # Get the project root directory (parent of app/)
    project_root = Path(__file__).parent.parent.parent
    alembic_ini_path = project_root / "alembic.ini"

    if not alembic_ini_path.exists():
        logger.error(f"Alembic config file not found at {alembic_ini_path}")
        raise FileNotFoundError(
            f"Alembic config file not found at {alembic_ini_path}"
        )

    # Create Alembic config
    alembic_cfg = Config(str(alembic_ini_path))

    # Override the database URL from settings
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database.url)

    try:
        # Run migrations to head
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Failed to run database migrations: {e}")
        raise
