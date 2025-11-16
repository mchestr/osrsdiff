"""TaskIQ broker configuration and setup."""

import logging
from logging.config import dictConfig

from taskiq import TaskiqEvents
from taskiq.middlewares import SmartRetryMiddleware
from taskiq.state import TaskiqState
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

from app.config import LogConfig
from app.config import settings as config_defaults
from app.services.setting import setting_service as settings_cache

dictConfig(LogConfig().model_dump())

logger = logging.getLogger(__name__)


# Create Redis result backend (will be reconfigured after cache loads)
result_backend: RedisAsyncResultBackend = RedisAsyncResultBackend(
    redis_url=config_defaults.redis.url,
    max_connection_pool_size=config_defaults.redis.max_connections,
)

# Create Redis broker with result backend (will be reconfigured after cache loads)
broker = RedisStreamBroker(
    url=config_defaults.redis.url,
    max_connection_pool_size=config_defaults.redis.max_connections,
).with_result_backend(result_backend)

# Add smart retry middleware (will be reconfigured after cache loads)
broker.add_middlewares(
    SmartRetryMiddleware(
        default_retry_count=config_defaults.taskiq.default_retry_count,
        default_delay=config_defaults.taskiq.default_retry_delay,
        use_jitter=config_defaults.taskiq.use_jitter,
        use_delay_exponent=config_defaults.taskiq.use_delay_exponent,
        max_delay_exponent=config_defaults.taskiq.max_delay_exponent,
    )
)

# Add task execution tracking middleware
from app.workers.middleware import TaskExecutionTrackingMiddleware

broker.add_middlewares(TaskExecutionTrackingMiddleware())

# Import redis_schedule_source from scheduler module to ensure single instance
# This ensures FastAPI and worker processes use the same Redis connection
from app.workers.scheduler import redis_schedule_source


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup_event(context: TaskiqState) -> None:
    """Initialize worker resources on startup."""
    logger.info("TaskIQ worker starting up...")

    # Initialize database connection pool for workers
    from app.models.base import init_db

    await init_db()

    # Load settings from database into cache
    await settings_cache.load_from_database()

    # Note: TaskiqScheduler is run separately via CLI command
    # No need to start custom scheduler here anymore

    logger.info("TaskIQ worker startup complete")


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def shutdown_event(context: TaskiqState) -> None:
    """Clean up worker resources on shutdown."""
    logger.info("TaskIQ worker shutting down...")

    # Close database connections
    from app.models.base import close_db

    await close_db()

    logger.info("TaskIQ worker shutdown complete")


@broker.on_event(TaskiqEvents.CLIENT_STARTUP)
async def client_startup_event(context: TaskiqState) -> None:
    """Initialize client resources on startup."""
    logger.info("TaskIQ client starting up...")


@broker.on_event(TaskiqEvents.CLIENT_SHUTDOWN)
async def client_shutdown_event(context: TaskiqState) -> None:
    """Clean up client resources on shutdown."""
    logger.info("TaskIQ client shutting down...")


# Import all task modules to ensure tasks are registered with the broker
# This must happen after broker is defined and before worker starts
from app.workers import fetch  # noqa: F401, E402
from app.workers import maintenance  # noqa: F401, E402
from app.workers import summaries  # noqa: F401, E402
from app.workers import tasks  # noqa: F401, E402
