"""Cron-like task scheduler."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any, Callable, Dict, List, Optional

import redis.asyncio as redis
from croniter import croniter

from src.config import settings

logger = logging.getLogger(__name__)


class ScheduledTask:
    """A task that runs on a cron schedule."""

    def __init__(
        self,
        name: str,
        cron_expression: str,
        task_func: Callable[[], Any],
        description: str = "",
    ):
        """
        Initialize a scheduled task.

        Args:
            name: Unique name for the task
            cron_expression: Cron expression (e.g., "0 2 * * *" for daily at 2 AM)
            task_func: Async function to execute
            description: Human-readable description
        """
        self.name = name
        self.cron_expression = cron_expression
        self.task_func = task_func
        self.description = description

        # Validate cron expression
        try:
            croniter(cron_expression)
        except Exception as e:
            raise ValueError(f"Invalid cron expression '{cron_expression}': {e}")

    def get_next_run_time(self, base_time: Optional[datetime] = None) -> datetime:
        """Get the next time this task should run."""
        if base_time is None:
            base_time = datetime.now(UTC)

        cron = croniter(self.cron_expression, base_time)
        return cron.get_next(datetime)

    def should_run(self, current_time: datetime, last_run: Optional[datetime]) -> bool:
        """Check if this task should run now."""
        if last_run is None:
            # Never run before, check if we're past the first scheduled time
            return True

        # Get the next scheduled time after the last run
        next_run = self.get_next_run_time(last_run)
        return current_time >= next_run


class TaskScheduler:
    """Cron-like scheduler for background tasks."""

    def __init__(self) -> None:
        """Initialize the scheduler."""
        self.tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._task: Optional[asyncio.Task[None]] = None
        self._redis_client: Optional[redis.Redis] = None
        self._check_interval = 60  # Check every minute

    def add_task(
        self,
        name: str,
        cron_expression: str,
        task_func: Callable[[], Any],
        description: str = "",
    ) -> None:
        """
        Add a task to the scheduler.

        Args:
            name: Unique name for the task
            cron_expression: Cron expression (e.g., "0 2 * * *")
            task_func: Async function to execute
            description: Human-readable description
        """
        if name in self.tasks:
            raise ValueError(f"Task '{name}' already exists")

        task = ScheduledTask(name, cron_expression, task_func, description)
        self.tasks[name] = task
        logger.info(f"Added scheduled task: {name} ({cron_expression}) - {description}")

    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler is already running")
            return

        logger.info(f"Starting scheduler with {len(self.tasks)} tasks")

        # Create Redis client
        self._redis_client = redis.from_url(settings.redis.url)

        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())

    async def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            return

        logger.info("Stopping scheduler")
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        if self._redis_client:
            await self._redis_client.aclose()
            self._redis_client = None

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        logger.info("Scheduler loop started")

        try:
            while self._running:
                current_time = datetime.now(UTC)

                # Check each task
                for task in self.tasks.values():
                    try:
                        await self._check_and_run_task(task, current_time)
                    except Exception as e:
                        logger.error(f"Error checking task {task.name}: {e}")

                # Sleep until next check
                await asyncio.sleep(self._check_interval)

        except asyncio.CancelledError:
            logger.info("Scheduler loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in scheduler loop: {e}")
            raise
        finally:
            logger.info("Scheduler loop ended")

    async def _check_and_run_task(
        self, task: ScheduledTask, current_time: datetime
    ) -> None:
        """Check if a task should run and execute it if needed."""
        if not self._redis_client:
            logger.warning("Redis client not available")
            return

        # Redis keys for this task
        lock_key = f"osrsdiff:scheduler:lock:{task.name}"
        last_run_key = f"osrsdiff:scheduler:last_run:{task.name}"

        # Get last run time
        try:
            last_run_str = await self._redis_client.get(last_run_key)
            last_run = None
            if last_run_str:
                last_run = datetime.fromisoformat(last_run_str.decode())
        except Exception as e:
            logger.error(f"Failed to get last run time for {task.name}: {e}")
            return

        # Check if task should run
        if not task.should_run(current_time, last_run):
            return

        # Try to acquire lock
        lock_timeout = 300  # 5 minutes
        try:
            acquired = await self._redis_client.set(
                lock_key,
                "locked",
                nx=True,  # Only set if key doesn't exist
                ex=lock_timeout,  # Expire after timeout
            )

            if not acquired:
                logger.debug(f"Could not acquire lock for task {task.name}")
                return

            # Double-check that another worker hasn't run this recently
            last_run_str = await self._redis_client.get(last_run_key)
            if last_run_str:
                last_run = datetime.fromisoformat(last_run_str.decode())
                if not task.should_run(current_time, last_run):
                    logger.debug(
                        f"Task {task.name} was run by another worker, skipping"
                    )
                    await self._redis_client.delete(lock_key)
                    return

            # Run the task
            logger.info(f"Running scheduled task: {task.name}")
            try:
                await task.task_func()

                # Update last run time
                await self._redis_client.set(last_run_key, current_time.isoformat())
                logger.info(f"Successfully completed task: {task.name}")

            except Exception as e:
                logger.error(f"Task {task.name} failed: {e}")

            # Release lock
            await self._redis_client.delete(lock_key)

        except Exception as e:
            logger.error(f"Error running task {task.name}: {e}")
            # Try to release lock on error
            try:
                await self._redis_client.delete(lock_key)
            except:
                pass

    async def trigger_task(self, task_name: str) -> None:
        """Manually trigger a specific task."""
        if task_name not in self.tasks:
            raise ValueError(f"Task '{task_name}' not found")

        task = self.tasks[task_name]
        logger.info(f"Manually triggering task: {task_name}")

        try:
            await task.task_func()
            logger.info(f"Successfully triggered task: {task_name}")
        except Exception as e:
            logger.error(f"Manually triggered task {task_name} failed: {e}")
            raise

    def list_tasks(self) -> List[Dict[str, Any]]:
        """List all registered tasks with their schedules."""
        result = []
        for task in self.tasks.values():
            next_run = task.get_next_run_time()
            result.append(
                {
                    "name": task.name,
                    "cron_expression": task.cron_expression,
                    "description": task.description,
                    "next_run": next_run.isoformat(),
                }
            )
        return result

    async def get_task_status(self, task_name: str) -> Dict[str, Any]:
        """Get status information for a specific task."""
        if task_name not in self.tasks:
            raise ValueError(f"Task '{task_name}' not found")

        task = self.tasks[task_name]

        # Get last run time from Redis
        last_run = None
        if self._redis_client:
            try:
                last_run_key = f"osrsdiff:scheduler:last_run:{task_name}"
                last_run_str = await self._redis_client.get(last_run_key)
                if last_run_str:
                    last_run = datetime.fromisoformat(last_run_str.decode())
            except Exception as e:
                logger.error(f"Failed to get last run time for {task_name}: {e}")

        next_run = (
            task.get_next_run_time(last_run) if last_run else task.get_next_run_time()
        )

        return {
            "name": task.name,
            "cron_expression": task.cron_expression,
            "description": task.description,
            "last_run": last_run.isoformat() if last_run else None,
            "next_run": next_run.isoformat(),
            "should_run_now": task.should_run(datetime.now(UTC), last_run),
        }


# Global scheduler instance
_scheduler: Optional[TaskScheduler] = None


def get_scheduler() -> TaskScheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler()
    return _scheduler


async def setup_scheduled_tasks() -> None:
    """Set up all scheduled tasks from configuration."""
    scheduler = get_scheduler()

    # Import task configuration
    from src.workers.task_config import get_task_configs

    # Set up tasks from configuration
    task_configs = get_task_configs()

    for config in task_configs:
        # Dynamically import the task function
        module_name = config["task_module"]
        function_name = config["task_function"]

        try:
            # Import the module and get the task function
            module = __import__(module_name, fromlist=[function_name])
            task_func = getattr(module, function_name)

            # Add the task to scheduler
            async def create_task_wrapper(tf: Any = task_func) -> Any:
                return await tf.kiq()

            scheduler.add_task(
                name=config["name"],
                cron_expression=config["cron_expression"],
                task_func=create_task_wrapper,
                description=config["description"],
            )

            logger.info(
                f"Configured task: {config['name']} ({config['cron_expression']})"
            )

        except Exception as e:
            logger.error(f"Failed to configure task {config['name']}: {e}")
            raise


async def start_scheduler() -> None:
    """Start the scheduler with all tasks."""
    await setup_scheduled_tasks()
    scheduler = get_scheduler()
    await scheduler.start()


async def stop_scheduler() -> None:
    """Stop the scheduler."""
    scheduler = get_scheduler()
    await scheduler.stop()


async def trigger_task(task_name: str) -> None:
    """Manually trigger a specific task."""
    scheduler = get_scheduler()
    await scheduler.trigger_task(task_name)
