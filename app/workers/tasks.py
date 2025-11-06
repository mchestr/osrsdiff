"""TaskIQ tasks for OSRS hiscore data fetching and processing."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any, Dict

from app.workers.main import broker, get_task_defaults

logger = logging.getLogger(__name__)


async def _health_check_task() -> Dict[str, Any]:
    """
    Health check task implementation.

    Returns:
        Dict containing task execution info
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "message": "TaskIQ worker is operational",
    }


async def _test_retry_task(should_fail: bool = False) -> Dict[str, Any]:
    """
    Test task implementation for verifying retry functionality.

    Args:
        should_fail: Whether the task should fail to test retry logic

    Returns:
        Dict containing task execution info

    Raises:
        RuntimeError: If should_fail is True
    """
    if should_fail:
        raise RuntimeError("Task intentionally failed for testing")

    return {
        "status": "success",
        "timestamp": datetime.now(UTC).isoformat(),
        "message": "Retry test completed successfully",
    }


async def _test_timeout_task(delay_seconds: float = 5.0) -> Dict[str, Any]:
    """
    Test task implementation for verifying timeout functionality.

    Args:
        delay_seconds: How long to sleep before completing

    Returns:
        Dict containing task execution info
    """
    await asyncio.sleep(delay_seconds)

    return {
        "status": "completed",
        "timestamp": datetime.now(UTC).isoformat(),
        "delay_seconds": delay_seconds,
        "message": f"Task completed after {delay_seconds} seconds",
    }


# TaskIQ decorated tasks
health_check_task = broker.task(**get_task_defaults())(_health_check_task)
retry_task = broker.task(**get_task_defaults(retry_count=5, retry_delay=1.0))(
    _test_retry_task
)
timeout_task = broker.task(**get_task_defaults(task_timeout=10.0))(
    _test_timeout_task
)

# Import fetch tasks from fetch module
from app.workers.fetch import (
    fetch_all_players_task,
    fetch_player_hiscores_task,
)
