"""TaskIQ scheduler configuration module."""

import logging
from typing import TYPE_CHECKING, Any, List

from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import ListRedisScheduleSource

from app.config import settings as config_defaults

if TYPE_CHECKING:
    from taskiq_redis import RedisStreamBroker

logger = logging.getLogger(__name__)

# Import broker after TYPE_CHECKING to avoid circular import issues
from app.workers.main import broker  # noqa: E402

# Create scheduler sources for direct access
# Redis-based schedule source for dynamic scheduling
# Uses config.py settings which can be configured via environment variables
redis_schedule_source = ListRedisScheduleSource(
    url=config_defaults.redis.url,
    prefix=config_defaults.taskiq.scheduler_prefix,
    max_connection_pool_size=config_defaults.redis.max_connections,
)

# Label-based schedule source for static schedules
label_schedule_source = LabelScheduleSource(broker)  # type: ignore[has-type]


def create_scheduler_sources() -> List[Any]:
    """Create and configure scheduler sources."""
    sources: List[Any] = [
        redis_schedule_source,
        label_schedule_source,
    ]

    logger.info(f"Configured {len(sources)} scheduler sources")
    return sources


def create_scheduler() -> TaskiqScheduler:
    """Create and configure the TaskIQ scheduler."""
    sources = create_scheduler_sources()

    scheduler = TaskiqScheduler(
        broker=broker,
        sources=sources,
    )

    logger.info("TaskIQ scheduler configured successfully")
    return scheduler


# Create the scheduler instance
scheduler = create_scheduler()
