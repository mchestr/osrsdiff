"""TaskIQ scheduler configuration module."""

import logging
from typing import Any, List

from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import ListRedisScheduleSource

from app.config import settings
from app.workers.main import broker

logger = logging.getLogger(__name__)


def create_scheduler_sources() -> List[Any]:
    """Create and configure scheduler sources."""
    sources: List[Any] = []

    # Redis-based schedule source for dynamic scheduling
    redis_schedule_source = ListRedisScheduleSource(
        url=settings.redis.url,
        prefix=settings.taskiq.scheduler_prefix,
        max_connection_pool_size=settings.redis.max_connections,
    )
    sources.append(redis_schedule_source)

    # Label-based schedule source for static schedules
    label_schedule_source = LabelScheduleSource(broker)
    sources.append(label_schedule_source)

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
