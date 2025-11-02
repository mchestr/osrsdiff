"""Task scheduling functionality for periodic hiscore fetches."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Optional

import redis.asyncio as redis

from src.config import settings
from src.workers.fetch import process_scheduled_fetches_task

logger = logging.getLogger(__name__)


class TaskScheduler:
    """
    Scheduler for periodic background tasks.

    This class manages the scheduling of recurring tasks like periodic
    hiscore fetches for all active players.
    """

    def __init__(self, fetch_interval_minutes: int = 30):
        """
        Initialize the task scheduler.

        Args:
            fetch_interval_minutes: How often to run scheduled fetch processing
        """
        self.fetch_interval_minutes = fetch_interval_minutes
        self.fetch_interval = timedelta(minutes=fetch_interval_minutes)
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_scheduled_run: Optional[datetime] = None
        self._redis_client: Optional[redis.Redis] = None
        self._lock_key = "osrsdiff:scheduler:lock"
        self._last_run_key = "osrsdiff:scheduler:last_run"
        self._has_lock = False

    async def start(self) -> None:
        """Start the task scheduler."""
        if self._running:
            logger.warning("Task scheduler is already running")
            return

        logger.info(
            f"Starting task scheduler (fetch interval: {self.fetch_interval_minutes} minutes)"
        )

        # Create Redis client for leader election
        self._redis_client = redis.from_url(settings.redis.url)

        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())

    async def stop(self) -> None:
        """Stop the task scheduler."""
        if not self._running:
            logger.warning("Task scheduler is not running")
            return

        logger.info("Stopping task scheduler")
        self._running = False

        # Release lock if we have it
        await self._release_lock()

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        # Clean up Redis client
        if self._redis_client:
            await self._redis_client.aclose()
            self._redis_client = None

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop that runs periodic tasks."""
        logger.info("Task scheduler loop started")

        try:
            while self._running:
                current_time = datetime.now(UTC)

                # Check if it's time to run scheduled fetches by reading from Redis
                should_run = False

                try:
                    # Get last run timestamp from Redis (shared across all workers)
                    if self._redis_client is None:
                        logger.warning(
                            "Redis client not available, skipping scheduled check"
                        )
                        continue

                    last_run_str = await self._redis_client.get(
                        self._last_run_key
                    )

                    if last_run_str is None:
                        # Never run before across any worker
                        should_run = True
                        logger.info(
                            "First scheduled fetch run (no previous run found in Redis)"
                        )
                    else:
                        # Parse the stored timestamp
                        last_run_time = datetime.fromisoformat(
                            last_run_str.decode()
                        )
                        time_since_last = current_time - last_run_time

                        if time_since_last >= self.fetch_interval:
                            should_run = True
                            logger.info(
                                f"Time for scheduled fetch run (last run: {time_since_last} ago)"
                            )
                        else:
                            time_remaining = (
                                self.fetch_interval - time_since_last
                            )
                            logger.debug(
                                f"Not time for scheduled run yet (next run in: {time_remaining})"
                            )

                except Exception as e:
                    logger.error(
                        f"Failed to check last run time from Redis: {e}"
                    )
                    # Continue without scheduling to avoid duplicate runs

                if should_run:
                    # Use Redis lock for leader election
                    lock_timeout = 30  # 30 seconds

                    try:
                        # Try to acquire lock with 30-second timeout
                        if self._redis_client is None:
                            logger.warning(
                                "Redis client not available, skipping lock acquisition"
                            )
                            continue

                        acquired = await self._redis_client.set(
                            self._lock_key,
                            "locked",
                            nx=True,  # Only set if key doesn't exist
                            ex=lock_timeout,  # Expire after 30 seconds
                        )

                        if acquired:
                            self._has_lock = True
                            logger.info(
                                "Acquired scheduler lock, enqueuing scheduled fetch processing task"
                            )

                            last_run_str = await self._redis_client.get(
                                self._last_run_key
                            )
                            if last_run_str is not None:
                                last_run_time = datetime.fromisoformat(
                                    last_run_str.decode()
                                )
                                time_since_last = current_time - last_run_time
                                if time_since_last < self.fetch_interval:
                                    logger.info(
                                        "Another worker already scheduled recently, skipping"
                                    )
                                    await self._release_lock()
                                    continue

                            # Enqueue the task
                            await process_scheduled_fetches_task.kiq()

                            # Update last run timestamp in Redis (shared state)
                            if self._redis_client is not None:
                                await self._redis_client.set(
                                    self._last_run_key,
                                    current_time.isoformat(),
                                )

                            # Update local timestamp for property access
                            self._last_scheduled_run = current_time

                            logger.info(
                                "Successfully enqueued scheduled fetch processing"
                            )
                        else:
                            logger.warning(
                                "Redis client not available during lock check"
                            )

                        # Release lock immediately after successful scheduling
                        await self._release_lock()

                    except Exception as e:
                        logger.error(
                            f"Failed to enqueue scheduled fetch processing: {e}"
                        )
                        # Release lock on error
                        await self._release_lock()
                        # Continue running even if one enqueue fails

                # Sleep for a reasonable check interval (10 seconds)
                # This ensures we don't miss the scheduled time by too much
                await asyncio.sleep(10)

        except asyncio.CancelledError:
            logger.info("Task scheduler loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in scheduler loop: {e}")
            raise
        finally:
            # Release lock and clean up Redis client
            await self._release_lock()
            if self._redis_client:
                await self._redis_client.aclose()
                self._redis_client = None
            logger.info("Task scheduler loop ended")

    async def _release_lock(self) -> None:
        """Release the scheduler lock if we have it."""
        if self._has_lock and self._redis_client is not None:
            try:
                await self._redis_client.delete(self._lock_key)
                logger.debug("Released scheduler lock")
            except Exception as e:
                logger.error(f"Failed to release scheduler lock: {e}")
            finally:
                # Always reset the flag, even if Redis delete fails
                self._has_lock = False

    async def trigger_immediate_fetch(self) -> None:
        """Trigger an immediate scheduled fetch processing."""
        try:
            logger.info("Triggering immediate scheduled fetch processing")
            await process_scheduled_fetches_task.kiq()
            logger.info("Successfully triggered immediate scheduled fetch")
        except Exception as e:
            logger.error(f"Failed to trigger immediate scheduled fetch: {e}")
            raise

    @property
    def is_running(self) -> bool:
        """Check if the scheduler is currently running."""
        return self._running

    @property
    def last_run(self) -> Optional[datetime]:
        """Get the timestamp of the last scheduled run."""
        return self._last_scheduled_run

    @property
    def next_run(self) -> Optional[datetime]:
        """Get the estimated timestamp of the next scheduled run."""
        if self._last_scheduled_run is None:
            return None
        return self._last_scheduled_run + self.fetch_interval

    async def get_last_run_from_redis(self) -> Optional[datetime]:
        """Get the last run timestamp from Redis (shared across all workers)."""
        if not self._redis_client:
            return None

        last_run_str = await self._redis_client.get(self._last_run_key)
        if last_run_str is None:
            return None
        return datetime.fromisoformat(last_run_str.decode())


# Global scheduler instance
_scheduler: Optional[TaskScheduler] = None


def get_scheduler() -> TaskScheduler:
    """Get the global task scheduler instance."""
    global _scheduler
    if _scheduler is None:
        # Default to 30 minute intervals for scheduled fetches
        # This can be made configurable via settings if needed
        _scheduler = TaskScheduler(fetch_interval_minutes=30)
    return _scheduler


async def start_scheduler() -> None:
    """Start the global task scheduler."""
    scheduler = get_scheduler()
    await scheduler.start()


async def stop_scheduler() -> None:
    """Stop the global task scheduler."""
    scheduler = get_scheduler()
    await scheduler.stop()


async def trigger_immediate_fetch() -> None:
    """Trigger an immediate scheduled fetch via the scheduler."""
    scheduler = get_scheduler()
    await scheduler.trigger_immediate_fetch()
