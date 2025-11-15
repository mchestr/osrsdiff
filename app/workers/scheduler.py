"""TaskIQ scheduler configuration module."""

import logging
from typing import Any, List

from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import ListRedisScheduleSource

from app.config import settings as config_defaults
from app.services.settings_cache import settings_cache
from app.workers.main import broker

logger = logging.getLogger(__name__)


# Create scheduler sources for direct access
# Redis-based schedule source for dynamic scheduling
# Note: This is initialized at import time, so it uses config defaults
# The scheduler will be recreated if needed after cache loads
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
