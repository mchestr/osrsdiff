"""TaskIQ broker configuration and setup."""

import asyncio
from typing import Any, Dict

from taskiq import TaskiqEvents
from taskiq.middlewares import SimpleRetryMiddleware
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

from src.config import settings


# Create Redis result backend
result_backend = RedisAsyncResultBackend(
    redis_url=settings.redis.url,
    max_connection_pool_size=settings.redis.max_connections,
)

# Create Redis broker with result backend
broker = RedisStreamBroker(
    url=settings.redis.url,
    max_connection_pool_size=settings.redis.max_connections,
).with_result_backend(result_backend)

# Add retry middleware
broker.add_middlewares(
    SimpleRetryMiddleware(
        default_retry_count=settings.taskiq.default_retry_count,
    )
)


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup_event(context: Dict[str, Any]) -> None:
    """Initialize worker resources on startup."""
    print("TaskIQ worker starting up...")
    
    # Initialize database connection pool for workers
    from src.models.base import init_db
    await init_db()
    
    # Start the task scheduler for periodic fetches
    # Uses Redis lock for leader election to prevent duplicate scheduling
    from src.workers.scheduler import start_scheduler
    await start_scheduler()
    
    print("TaskIQ worker startup complete")


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def shutdown_event(context: Dict[str, Any]) -> None:
    """Clean up worker resources on shutdown."""
    print("TaskIQ worker shutting down...")
    
    # Stop the task scheduler
    from src.workers.scheduler import stop_scheduler
    await stop_scheduler()
    
    # Close database connections
    from src.models.base import close_db
    await close_db()
    
    print("TaskIQ worker shutdown complete")


@broker.on_event(TaskiqEvents.CLIENT_STARTUP)
async def client_startup_event(context: Dict[str, Any]) -> None:
    """Initialize client resources on startup."""
    print("TaskIQ client starting up...")


@broker.on_event(TaskiqEvents.CLIENT_SHUTDOWN)
async def client_shutdown_event(context: Dict[str, Any]) -> None:
    """Clean up client resources on shutdown."""
    print("TaskIQ client shutting down...")


def get_task_defaults(**kwargs: Any) -> Dict[str, Any]:
    """Get task configuration with default settings."""
    defaults = {
        "retry_count": settings.taskiq.default_retry_count,
        "retry_delay": settings.taskiq.default_retry_delay,
        "task_timeout": settings.taskiq.task_timeout,
        "result_ttl": settings.taskiq.result_ttl,
    }
    defaults.update(kwargs)
    return defaults