import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import String, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.api.auth_utils import require_admin, require_auth
from app.exceptions import InternalServerError, NotFoundError
from app.models.base import get_db_session
from app.models.hiscore import HiscoreRecord
from app.models.player import Player
from app.models.player_summary import PlayerSummary
from app.models.task_execution import TaskExecution, TaskExecutionStatus
from app.utils.common import ensure_timezone_aware

logger = logging.getLogger(__name__)


# Response models
class DatabaseStatsResponse(BaseModel):
    """Response model for database statistics."""

    total_players: int = Field(description="Total number of players in system")
    active_players: int = Field(description="Number of active players")
    inactive_players: int = Field(description="Number of inactive players")
    total_hiscore_records: int = Field(
        description="Total number of hiscore records"
    )
    oldest_record: Optional[str] = Field(
        description="Timestamp of oldest hiscore record"
    )
    newest_record: Optional[str] = Field(
        description="Timestamp of newest hiscore record"
    )
    records_last_24h: int = Field(
        description="Records created in last 24 hours"
    )
    records_last_7d: int = Field(description="Records created in last 7 days")
    avg_records_per_player: float = Field(
        description="Average records per player"
    )


class SystemHealthResponse(BaseModel):
    """Response model for system health check."""

    status: str = Field(description="Overall system status")
    database_connected: bool = Field(description="Database connection status")
    total_storage_mb: Optional[float] = Field(
        description="Total database size in MB"
    )
    uptime_info: Dict[str, Any] = Field(
        description="System uptime information"
    )


class PlayerDistributionResponse(BaseModel):
    """Response model for player distribution statistics."""

    by_fetch_interval: Dict[str, int] = Field(
        description="Players grouped by fetch interval"
    )
    by_last_fetch: Dict[str, int] = Field(
        description="Players grouped by last fetch time"
    )
    never_fetched: int = Field(
        description="Players that have never been fetched"
    )


# Router
router = APIRouter(prefix="/system", tags=["system"])


@router.get("/stats", response_model=DatabaseStatsResponse)
async def get_database_stats(
    db_session: AsyncSession = Depends(get_db_session),
) -> DatabaseStatsResponse:
    """
    Get comprehensive database statistics.

    Returns detailed statistics about players, hiscore records, and system usage.
    Useful for monitoring system growth and usage patterns.
    This endpoint is publicly accessible and does not require authentication.

    Args:
        db_session: Database session dependency

    Returns:
        DatabaseStatsResponse: Comprehensive database statistics

    Raises:
        500 Internal Server Error: Database or calculation errors
    """
    try:
        logger.info("Requesting database stats (public endpoint)")

        # Get player counts
        total_players_result = await db_session.execute(
            select(func.count(Player.id))
        )
        total_players = total_players_result.scalar() or 0

        active_players_result = await db_session.execute(
            select(func.count(Player.id)).where(Player.is_active.is_(True))
        )
        active_players = active_players_result.scalar() or 0

        inactive_players = total_players - active_players

        # Get hiscore record counts
        total_records_result = await db_session.execute(
            select(func.count(HiscoreRecord.id))
        )
        total_records = total_records_result.scalar() or 0

        # Get oldest and newest records
        oldest_record_result = await db_session.execute(
            select(func.min(HiscoreRecord.fetched_at))
        )
        oldest_record = oldest_record_result.scalar()

        newest_record_result = await db_session.execute(
            select(func.max(HiscoreRecord.fetched_at))
        )
        newest_record = newest_record_result.scalar()

        # Get recent record counts
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)

        records_24h_result = await db_session.execute(
            select(func.count(HiscoreRecord.id)).where(
                HiscoreRecord.fetched_at >= last_24h
            )
        )
        records_last_24h = records_24h_result.scalar() or 0

        records_7d_result = await db_session.execute(
            select(func.count(HiscoreRecord.id)).where(
                HiscoreRecord.fetched_at >= last_7d
            )
        )
        records_last_7d = records_7d_result.scalar() or 0

        # Calculate average records per player
        avg_records_per_player = (
            total_records / total_players if total_players > 0 else 0.0
        )

        response = DatabaseStatsResponse(
            total_players=total_players,
            active_players=active_players,
            inactive_players=inactive_players,
            total_hiscore_records=total_records,
            oldest_record=oldest_record.isoformat() if oldest_record else None,
            newest_record=newest_record.isoformat() if newest_record else None,
            records_last_24h=records_last_24h,
            records_last_7d=records_last_7d,
            avg_records_per_player=round(avg_records_per_player, 2),
        )

        logger.info("Successfully retrieved database statistics")
        return response

    except Exception as e:
        logger.error(f"Error retrieving database stats: {e}")
        raise InternalServerError(
            "Failed to retrieve database statistics", detail=str(e)
        )


@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health(
    db_session: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(require_auth),
) -> SystemHealthResponse:
    """
    Get system health information.

    Returns overall system status, database connectivity, and storage information.

    Args:
        db_session: Database session dependency
        current_user: Authenticated user information

    Returns:
        SystemHealthResponse: System health information

    Raises:
        500 Internal Server Error: Health check errors
    """
    try:
        logger.info(
            f"User {current_user.get('username')} requesting system health"
        )

        # Test database connectivity
        database_connected = True
        total_storage_mb = None

        try:
            # Simple query to test database connection
            await db_session.execute(select(1))

            # Try to get database size (PostgreSQL specific)
            try:
                size_result = await db_session.execute(
                    text("SELECT pg_database_size(current_database())")
                )
                size_bytes = size_result.scalar()
                if size_bytes:
                    total_storage_mb = round(size_bytes / (1024 * 1024), 2)
            except Exception as e:
                logger.warning(f"Could not retrieve database size: {e}")

        except Exception as e:
            logger.error(f"Database connectivity test failed: {e}")
            database_connected = False

        # Determine overall status
        status_value = "healthy" if database_connected else "degraded"

        response = SystemHealthResponse(
            status=status_value,
            database_connected=database_connected,
            total_storage_mb=total_storage_mb,
            uptime_info={
                "check_time": datetime.utcnow().isoformat(),
                "status": "System operational",
            },
        )

        logger.info(f"System health check completed: {status_value}")
        return response

    except Exception as e:
        logger.error(f"Error during system health check: {e}")
        raise InternalServerError(
            "Failed to perform system health check", detail=str(e)
        )


@router.get("/distribution", response_model=PlayerDistributionResponse)
async def get_player_distribution(
    db_session: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(require_auth),
) -> PlayerDistributionResponse:
    """
    Get player distribution statistics.

    Returns information about how players are distributed across different
    fetch intervals and last fetch times.

    Args:
        db_session: Database session dependency
        current_user: Authenticated user information

    Returns:
        PlayerDistributionResponse: Player distribution statistics

    Raises:
        500 Internal Server Error: Database or calculation errors
    """
    try:
        logger.info(
            f"User {current_user.get('username')} requesting player distribution"
        )

        # Get distribution by fetch interval
        interval_result = await db_session.execute(
            select(
                Player.fetch_interval_minutes,
                func.count(Player.id).label("count"),
            )
            .group_by(Player.fetch_interval_minutes)
            .order_by(Player.fetch_interval_minutes)
        )

        by_fetch_interval = {}
        for row in interval_result.fetchall():
            by_fetch_interval[f"{row.fetch_interval_minutes}min"] = int(row[1])

        # Get distribution by last fetch time
        now = datetime.utcnow()
        time_ranges = [
            ("never", None, None),
            ("last_hour", now - timedelta(hours=1), now),
            ("last_24h", now - timedelta(hours=24), now - timedelta(hours=1)),
            ("last_week", now - timedelta(days=7), now - timedelta(hours=24)),
            ("last_month", now - timedelta(days=30), now - timedelta(days=7)),
            ("older", None, now - timedelta(days=30)),
        ]

        by_last_fetch = {}
        never_fetched = 0

        for range_name, start_time, end_time in time_ranges:
            if range_name == "never":
                # Count players who have never been fetched
                result = await db_session.execute(
                    select(func.count(Player.id)).where(
                        Player.last_fetched.is_(None)
                    )
                )
                count = result.scalar() or 0
                by_last_fetch[range_name] = count
                never_fetched = count
            elif range_name == "older":
                # Count players fetched before the oldest range
                result = await db_session.execute(
                    select(func.count(Player.id)).where(
                        Player.last_fetched < end_time
                    )
                )
                by_last_fetch[range_name] = result.scalar() or 0
            else:
                # Count players fetched within the time range
                result = await db_session.execute(
                    select(func.count(Player.id)).where(
                        Player.last_fetched.between(start_time, end_time)
                    )
                )
                by_last_fetch[range_name] = result.scalar() or 0

        response = PlayerDistributionResponse(
            by_fetch_interval=by_fetch_interval,
            by_last_fetch=by_last_fetch,
            never_fetched=never_fetched,
        )

        logger.info("Successfully retrieved player distribution statistics")
        return response

    except Exception as e:
        logger.error(f"Error retrieving player distribution: {e}")
        raise InternalServerError(
            "Failed to retrieve player distribution statistics", detail=str(e)
        )


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


class TaskTriggerResponse(BaseModel):
    """Response model for task trigger operations."""

    task_name: str = Field(description="Name of the triggered task")
    message: str = Field(description="Success message")
    timestamp: str = Field(description="When the task was triggered")


class ScheduledTaskInfo(BaseModel):
    """Information about a scheduled task."""

    name: str = Field(description="Task name")
    friendly_name: str = Field(description="Human-readable task name")
    cron_expression: str = Field(description="Cron schedule expression")
    description: str = Field(description="Task description")
    last_run: Optional[str] = Field(description="Last run timestamp")
    should_run_now: bool = Field(description="Whether task should run now")


class ScheduledTasksResponse(BaseModel):
    """Response model for scheduled tasks list."""

    tasks: List[ScheduledTaskInfo] = Field(
        description="List of scheduled tasks"
    )
    total_count: int = Field(description="Total number of tasks")


def _format_task_name(name: str) -> str:
    """Format a task name into a friendly display name."""
    if not name:
        return "Unknown Task"
    # Remove module prefix (e.g., "app.workers.maintenance:")
    without_module = name.split(":")[-1] if ":" in name else name
    # Replace underscores with spaces and capitalize words
    words = without_module.split("_")
    formatted = " ".join(word.capitalize() for word in words if word)
    return formatted if formatted else name


async def _get_friendly_name(
    schedule_id: str, db_session: AsyncSession
) -> str:
    """Get a friendly name for a schedule ID, especially for player tasks."""
    # Check if this is a player fetch task
    if schedule_id.startswith("player_fetch_"):
        try:
            player_id_str = schedule_id.replace("player_fetch_", "")
            player_id = int(player_id_str)
            # Query database for player username
            try:
                player_stmt = select(Player.username).where(
                    Player.id == player_id
                )
                player_result = await db_session.execute(player_stmt)
                player_username = player_result.scalar_one_or_none()
                if player_username:
                    return f"Fetch Player: {player_username}"
                else:
                    return f"Fetch Player: {player_id_str} (deleted)"
            except Exception as db_error:
                # If database query fails (e.g., in tests with mocked sessions), fall back to formatted name
                logger.debug(
                    f"Could not query player name for {schedule_id}: {db_error}"
                )
                return _format_task_name(schedule_id)
        except ValueError:
            # If we can't parse the ID, return formatted name
            return _format_task_name(schedule_id)
    else:
        # For non-player tasks, format the name nicely
        return _format_task_name(schedule_id)


@router.get("/scheduled-tasks", response_model=ScheduledTasksResponse)
async def get_scheduled_tasks(
    current_user: Dict[str, Any] = Depends(require_auth),
    db_session: AsyncSession = Depends(get_db_session),
) -> ScheduledTasksResponse:
    """
    Get information about all scheduled tasks.

    Returns details about each scheduled task including their cron expressions,
    last run times, and current status.

    Note: This endpoint now returns information about TaskIQ scheduled tasks
    managed by the TaskiqScheduler instead of the old custom scheduler.

    Args:
        current_user: Authenticated user information
        db_session: Database session for querying player names

    Returns:
        ScheduledTasksResponse: List of scheduled tasks with their information

    Raises:
        500 Internal Server Error: Scheduler errors
    """
    try:
        logger.info(
            f"User {current_user.get('username')} requesting scheduled tasks info"
        )

        # Import the TaskIQ scheduler and broker
        from app.workers.main import broker
        from app.workers.scheduler import scheduler, redis_schedule_source
        from taskiq_redis import ListRedisScheduleSource

        tasks_info = []

        # Use the same redis_schedule_source instance as the worker to ensure consistency
        # Get dynamic schedules directly from redis_schedule_source instead of scheduler.sources
        # to ensure we're using the exact same instance
        try:
            schedules = await redis_schedule_source.get_schedules()
            logger.info(f"Found {len(schedules)} dynamic schedules from Redis")

            for schedule in schedules:
                schedule_id = getattr(schedule, "schedule_id", None)
                if not schedule_id:
                    # Skip schedules without schedule_id
                    continue
                friendly_name = await _get_friendly_name(
                    schedule_id, db_session
                )
                task_info = ScheduledTaskInfo(
                    name=schedule_id,
                    friendly_name=friendly_name,
                    cron_expression=getattr(schedule, "cron", None) or "N/A",
                    description=f"Dynamic scheduled task: {getattr(schedule, 'task_name', 'unknown')}",
                    last_run=None,  # TaskIQ doesn't track last run in schedule
                    should_run_now=False,  # TaskIQ manages this internally
                )
                tasks_info.append(task_info)
        except Exception as e:
            logger.warning(
                f"Could not retrieve schedules from Redis source: {e}"
            )

        # Get static schedules from broker tasks (instead of LabelScheduleSource)
        try:
            all_tasks = broker.get_all_tasks()
            logger.info(f"Found {len(all_tasks)} total tasks in broker")

            for task_name, task in all_tasks.items():
                # Get schedule information from task.labels["schedule"] (as per LabelScheduleSource)
                task_labels = getattr(task, "labels", {})
                schedule_list = task_labels.get("schedule", [])

                # If task has schedules, create entries for each schedule
                if schedule_list:
                    for schedule_config in schedule_list:
                        if not isinstance(schedule_config, dict):
                            continue

                        # Extract cron expression (can be "cron" or "time" for one-time schedules)
                        cron_expr = schedule_config.get("cron")
                        if not cron_expr and schedule_config.get("time"):
                            cron_expr = (
                                f"One-time: {schedule_config.get('time')}"
                            )
                        cron_expr = cron_expr or "N/A"

                        friendly_name = await _get_friendly_name(
                            task_name, db_session
                        )
                        task_info = ScheduledTaskInfo(
                            name=task_name,
                            friendly_name=friendly_name,
                            cron_expression=cron_expr,
                            description=f"Static scheduled task: {task_name}",
                            last_run=None,  # TaskIQ doesn't track last run in schedule
                            should_run_now=False,  # TaskIQ manages this internally
                        )
                        tasks_info.append(task_info)
                else:
                    # Task exists but has no schedule - still include it
                    friendly_name = await _get_friendly_name(
                        task_name, db_session
                    )
                    task_info = ScheduledTaskInfo(
                        name=task_name,
                        friendly_name=friendly_name,
                        cron_expression="N/A",
                        description=f"Static task (no schedule): {task_name}",
                        last_run=None,
                        should_run_now=False,
                    )
                    tasks_info.append(task_info)
        except Exception as e:
            logger.warning(
                f"Could not retrieve static schedules from broker: {e}"
            )

        response = ScheduledTasksResponse(
            tasks=tasks_info,
            total_count=len(tasks_info),
        )

        logger.info(
            f"Successfully retrieved {len(tasks_info)} scheduled tasks"
        )
        return response

    except Exception as e:
        logger.error(f"Error retrieving scheduled tasks: {e}")
        raise InternalServerError(
            "Failed to retrieve scheduled tasks", detail=str(e)
        )


@router.post("/trigger-task/{task_name}", response_model=TaskTriggerResponse)
async def trigger_scheduled_task(
    task_name: str,
    current_user: Dict[str, Any] = Depends(require_auth),
) -> TaskTriggerResponse:
    """
    Manually trigger any scheduled task.

    This endpoint allows administrators to manually trigger any scheduled task
    without waiting for its scheduled time. Supports triggering TaskIQ tasks
    by their schedule_id.

    Args:
        task_name: Schedule ID of the task to trigger (e.g., "player_fetch_123" or schedule_id)
        current_user: Authenticated user information

    Returns:
        TaskTriggerResponse: Confirmation that the task was triggered

    Raises:
        404 Not Found: Task not found
        500 Internal Server Error: Task trigger errors
    """
    try:
        logger.info(
            f"User {current_user.get('username')} manually triggering task: {task_name}"
        )

        # Import the TaskIQ scheduler
        from app.workers.scheduler import scheduler

        # Import all available maintenance/scheduled task functions
        # Exclude player-specific tasks (fetch_player_hiscores_task, generate_player_summary_task)
        # as they require player-specific arguments
        from app.workers.summaries import daily_summary_generation_job
        from app.workers.maintenance import schedule_maintenance_job

        # Map all available general maintenance task functions by their function names
        # Also include module-prefixed names for compatibility
        task_map = {
            "daily_summary_generation_job": daily_summary_generation_job,
            "app.workers.summaries:daily_summary_generation_job": daily_summary_generation_job,
            "schedule_maintenance_job": schedule_maintenance_job,
            "app.workers.maintenance:schedule_maintenance_job": schedule_maintenance_job,
        }

        # Try to find task by schedule_id or task_name in both Redis and Label sources
        from taskiq.schedule_sources import LabelScheduleSource

        redis_source = scheduler.sources[
            0
        ]  # First source is RedisScheduleSource
        redis_schedules = await redis_source.get_schedules()

        # Find Label source
        label_source = None
        for source in scheduler.sources:
            if isinstance(source, LabelScheduleSource):
                label_source = source
                break

        label_schedules = []
        if label_source:
            try:
                label_schedules = await label_source.get_schedules()
            except Exception as e:
                logger.warning(
                    f"Could not retrieve schedules from Label source: {e}"
                )

        # Search for schedule in both sources
        schedule = None
        for s in redis_schedules + label_schedules:
            schedule_id = (
                s.schedule_id
                if hasattr(s, "schedule_id")
                else getattr(s, "task_name", None)
            )
            if schedule_id == task_name or s.task_name == task_name:
                schedule = s
                break

        task_func = None
        task_args = ()
        task_display_name = task_name

        if schedule:
            # Found a schedule - use its task name and arguments
            schedule_task_name = schedule.task_name
            task_display_name = schedule_task_name

            # Extract function name if it's in "module:function" format
            if ":" in schedule_task_name:
                function_name = schedule_task_name.split(":")[-1]
            else:
                function_name = schedule_task_name

            task_func = task_map.get(schedule_task_name) or task_map.get(
                function_name
            )
            task_args = (
                tuple(schedule.args)
                if hasattr(schedule, "args") and schedule.args
                else ()
            )
        else:
            # No schedule found - try to trigger directly by function name
            # Extract function name if it's in "module:function" format
            if ":" in task_name:
                function_name = task_name.split(":")[-1]
            else:
                function_name = task_name

            task_func = task_map.get(task_name) or task_map.get(function_name)
            # For direct task triggering, use empty args for tasks that don't require them
            # Tasks that require args will need to be triggered via schedule_id
            task_args = ()

        if not task_func:
            available_tasks = [
                k for k in task_map.keys() if not k.startswith("app.workers.")
            ]
            raise NotFoundError(
                f"Task '{task_name}' not found. "
                f"Available tasks: {', '.join(available_tasks)}"
            )

        # Trigger the task
        task_result = await task_func.kiq(*task_args)

        logger.info(
            f"Successfully triggered task '{task_display_name}' "
            f"(schedule_id: {task_name if schedule else 'direct'}, task_id: {task_result.task_id})"
        )

        return TaskTriggerResponse(
            task_name=task_display_name,
            message=f"Task '{task_display_name}' triggered successfully",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error triggering task {task_name}: {e}", exc_info=True)
        raise InternalServerError("Failed to trigger task", detail=str(e))


class TaskExecutionResponse(BaseModel):
    """Response model for a single task execution."""

    id: int = Field(description="Task execution ID")
    task_name: str = Field(description="Name of the task function")
    task_args: Optional[Dict[str, Any]] = Field(
        None, description="Task arguments as JSON"
    )
    status: str = Field(description="Execution status")
    retry_count: int = Field(description="Number of retry attempts")
    schedule_id: Optional[str] = Field(
        None, description="TaskIQ schedule ID if scheduled"
    )
    schedule_type: Optional[str] = Field(None, description="Type of schedule")
    player_id: Optional[int] = Field(
        None, description="Player ID if related to a player"
    )
    started_at: str = Field(description="When the task started")
    completed_at: Optional[str] = Field(
        None, description="When the task completed"
    )
    duration_seconds: Optional[float] = Field(
        None, description="Task execution duration in seconds"
    )
    error_type: Optional[str] = Field(
        None, description="Type/class name of the error"
    )
    error_message: Optional[str] = Field(None, description="Error message")
    error_traceback: Optional[str] = Field(
        None, description="Full error traceback"
    )
    result_data: Optional[Dict[str, Any]] = Field(
        None, description="Task result data"
    )
    execution_metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional execution metadata"
    )
    created_at: str = Field(description="When this record was created")

    @classmethod
    def from_task_execution(
        cls, execution: TaskExecution
    ) -> "TaskExecutionResponse":
        """Create response model from TaskExecution entity."""
        # Handle status: it may be a string (from DB) or enum instance
        status_value = (
            execution.status.value
            if hasattr(execution.status, "value")
            else str(execution.status)
        )
        return cls(
            id=execution.id,
            task_name=execution.task_name,
            task_args=execution.task_args,
            status=status_value,
            retry_count=execution.retry_count,
            schedule_id=execution.schedule_id,
            schedule_type=execution.schedule_type,
            player_id=execution.player_id,
            started_at=execution.started_at.isoformat(),
            completed_at=(
                execution.completed_at.isoformat()
                if execution.completed_at
                else None
            ),
            duration_seconds=execution.duration_seconds,
            error_type=execution.error_type,
            error_message=execution.error_message,
            error_traceback=execution.error_traceback,
            result_data=execution.result_data,
            execution_metadata=execution.execution_metadata,
            created_at=execution.created_at.isoformat(),
        )


class TaskExecutionsListResponse(BaseModel):
    """Response model for listing task executions."""

    total: int = Field(
        description="Total number of executions matching filters"
    )
    limit: int = Field(description="Maximum number of results returned")
    offset: int = Field(description="Number of results skipped")
    executions: List[TaskExecutionResponse] = Field(
        description="List of task executions"
    )


@router.get("/task-executions", response_model=TaskExecutionsListResponse)
async def get_task_executions(
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db_session: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(require_auth),
) -> TaskExecutionsListResponse:
    """
    Get task execution history with search functionality.

    This endpoint allows querying task execution history to debug why tasks
    may not have executed at scheduled times. Supports searching across task name,
    status, schedule_id, and player_name.

    Args:
        search: Search term that matches task name, status, schedule_id, or player_name (partial match)
        limit: Maximum number of results to return (default: 50, max: 200)
        offset: Number of results to skip for pagination
        db_session: Database session dependency
        current_user: Authenticated user information

    Returns:
        TaskExecutionsListResponse: List of task executions with metadata

    Raises:
        500 Internal Server Error: Database query errors
    """
    try:
        logger.info(
            f"User {current_user.get('username')} querying task executions "
            f"(search={search}, limit={limit}, offset={offset})"
        )

        # Validate and clamp limit
        limit = min(max(1, limit), 200)

        # Build query - always join with Player table to enable player name search
        player_alias = aliased(Player)
        query = select(TaskExecution).outerjoin(
            player_alias, TaskExecution.player_id == player_alias.id
        )

        # Apply search filter across all fields
        if search:
            search_term = search.strip()
            if search_term:
                # Try to match status exactly first (case-insensitive)
                status_match = None
                search_lower = search_term.lower()
                for status_value in TaskExecutionStatus:
                    if status_value.value.lower() == search_lower:
                        status_match = TaskExecutionStatus(status_value.value)
                        break

                # Build OR conditions for partial matching
                conditions = [
                    TaskExecution.task_name.contains(search_term),
                    TaskExecution.schedule_id.contains(search_term),
                    player_alias.username.contains(search_term),
                ]

                # Add exact status match if found, otherwise try partial match
                if status_match:
                    conditions.append(TaskExecution.status == status_match)
                else:
                    # Partial match on status string representation
                    conditions.append(
                        TaskExecution.status.cast(String).contains(search_term)
                    )

                query = query.where(or_(*conditions))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await db_session.execute(count_query)
        total = count_result.scalar_one()

        # Apply ordering and pagination
        query = query.order_by(TaskExecution.started_at.desc())
        query = query.limit(limit).offset(offset)

        # Execute query
        result = await db_session.execute(query)
        executions = result.scalars().all()

        return TaskExecutionsListResponse(
            total=total,
            limit=limit,
            offset=offset,
            executions=[
                TaskExecutionResponse.from_task_execution(exec)
                for exec in executions
            ],
        )

    except Exception as e:
        logger.error(f"Error querying task executions: {e}", exc_info=True)
        raise InternalServerError(
            "Failed to query task executions", detail=str(e)
        )


class PlayerSummaryResponse(BaseModel):
    """Response model for a player summary."""

    id: int = Field(description="Summary ID")
    player_id: int | None = Field(
        description="Player ID (null if player was deleted)"
    )
    period_start: str = Field(description="Start of the summary period")
    period_end: str = Field(description="End of the summary period")
    summary_text: str = Field(
        description="Generated summary text (JSON or plain text)"
    )
    summary: Optional[str] = Field(
        None,
        description="Concise summary overview (structured format)",
    )
    summary_points: List[str] = Field(
        default_factory=list,
        description="Parsed summary points (structured format)",
    )
    generated_at: str = Field(description="When the summary was generated")
    model_used: Optional[str] = Field(
        None, description="OpenAI model used for generation"
    )
    prompt_tokens: Optional[int] = Field(
        None, description="Number of tokens used in the prompt"
    )
    completion_tokens: Optional[int] = Field(
        None, description="Number of tokens used in the completion"
    )
    total_tokens: Optional[int] = Field(
        None, description="Total number of tokens used (prompt + completion)"
    )
    finish_reason: Optional[str] = Field(
        None, description="Reason the completion finished"
    )
    response_id: Optional[str] = Field(
        None, description="OpenAI API response ID"
    )

    @classmethod
    def from_summary(cls, summary: Any) -> "PlayerSummaryResponse":
        """Create response model from PlayerSummary entity."""
        from app.models.player_summary import PlayerSummary
        from app.services.player.summary import parse_summary_text

        summary_obj: PlayerSummary = summary
        parsed = parse_summary_text(summary_obj.summary_text)
        return cls(
            id=summary_obj.id,
            player_id=summary_obj.player_id,
            period_start=summary_obj.period_start.isoformat(),
            period_end=summary_obj.period_end.isoformat(),
            summary_text=summary_obj.summary_text,
            summary=parsed.get("summary"),
            summary_points=parsed.get("points", []),
            generated_at=summary_obj.generated_at.isoformat(),
            model_used=summary_obj.model_used,
            prompt_tokens=summary_obj.prompt_tokens,
            completion_tokens=summary_obj.completion_tokens,
            total_tokens=summary_obj.total_tokens,
            finish_reason=summary_obj.finish_reason,
            response_id=summary_obj.response_id,
        )


class CostStatsResponse(BaseModel):
    """Response model for cost statistics."""

    total_summaries: int = Field(
        description="Total number of summaries generated"
    )
    total_prompt_tokens: int = Field(description="Total prompt tokens used")
    total_completion_tokens: int = Field(
        description="Total completion tokens used"
    )
    total_tokens: int = Field(
        description="Total tokens used (prompt + completion)"
    )
    total_cost_usd: float = Field(description="Total estimated cost in USD")
    cost_last_24h_usd: float = Field(
        description="Estimated cost in last 24 hours"
    )
    cost_last_7d_usd: float = Field(
        description="Estimated cost in last 7 days"
    )
    cost_last_30d_usd: float = Field(
        description="Estimated cost in last 30 days"
    )
    by_model: Dict[str, Dict[str, Any]] = Field(
        description="Cost breakdown by model"
    )


# AI model pricing per 1M tokens (as of 2024)
# Prices are in USD per million tokens
# Supports multiple providers (OpenAI, Anthropic, etc.)
AI_MODEL_PRICING: Dict[str, Dict[str, float]] = {
    # OpenAI models
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    # Anthropic models (if used in future)
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    # Default fallback pricing (gpt-4o-mini rates)
    "default": {"input": 0.15, "output": 0.60},
}


def calculate_ai_cost(
    prompt_tokens: Optional[int],
    completion_tokens: Optional[int],
    model: Optional[str],
) -> float:
    """
    Calculate AI API cost based on token usage and model.

    Supports multiple providers (OpenAI, Anthropic, etc.) based on model name.

    Args:
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
        model: Model name (e.g., 'gpt-4o-mini', 'claude-3-5-sonnet')

    Returns:
        float: Estimated cost in USD
    """
    if prompt_tokens is None or completion_tokens is None:
        return 0.0

    # Get pricing for the model, fallback to default if not found
    model_key = model.lower() if model else "default"
    pricing = AI_MODEL_PRICING.get(model_key, AI_MODEL_PRICING["default"])

    # Calculate cost: (tokens / 1M) * price_per_1M
    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]

    return round(input_cost + output_cost, 6)


@router.get("/costs", response_model=CostStatsResponse)
async def get_cost_stats(
    db_session: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(require_auth),
) -> CostStatsResponse:
    """
    Get API cost statistics based on summary generation usage.

    Calculates estimated costs from token usage stored in player summaries.
    Supports cost breakdown by model and time periods (24h, 7d, 30d).
    Works with any AI provider (OpenAI, Anthropic, etc.) based on model name.

    Args:
        db_session: Database session dependency
        current_user: Authenticated user information

    Returns:
        CostStatsResponse: Cost statistics

    Raises:
        500 Internal Server Error: Database or calculation errors
    """
    try:
        logger.info(
            f"User {current_user.get('username')} requesting cost statistics"
        )

        # Get all summaries with token data
        summaries_result = await db_session.execute(
            select(PlayerSummary).where(
                PlayerSummary.prompt_tokens.isnot(None),
                PlayerSummary.completion_tokens.isnot(None),
            )
        )
        all_summaries = summaries_result.scalars().all()

        # Calculate time windows (use timezone-aware datetime)
        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        last_30d = now - timedelta(days=30)

        # Initialize totals
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_tokens = 0
        total_cost = 0.0

        # Time period costs
        cost_24h = 0.0
        cost_7d = 0.0
        cost_30d = 0.0

        # Breakdown by model
        by_model: Dict[str, Dict[str, Any]] = {}

        for summary in all_summaries:
            if (
                summary.prompt_tokens is None
                or summary.completion_tokens is None
            ):
                continue

            prompt_tokens = summary.prompt_tokens
            completion_tokens = summary.completion_tokens
            tokens_sum = prompt_tokens + completion_tokens
            model = summary.model_used or "default"

            # Calculate cost for this summary
            cost = calculate_ai_cost(prompt_tokens, completion_tokens, model)

            # Update totals
            total_prompt_tokens += prompt_tokens
            total_completion_tokens += completion_tokens
            total_tokens += tokens_sum
            total_cost += cost

            # Update time period costs (ensure timezone-aware comparison)
            summary_time = ensure_timezone_aware(summary.generated_at)

            if summary_time >= last_24h:
                cost_24h += cost
            if summary_time >= last_7d:
                cost_7d += cost
            if summary_time >= last_30d:
                cost_30d += cost

            # Update model breakdown
            if model not in by_model:
                by_model[model] = {
                    "count": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "cost_usd": 0.0,
                }

            by_model[model]["count"] += 1
            by_model[model]["prompt_tokens"] += prompt_tokens
            by_model[model]["completion_tokens"] += completion_tokens
            by_model[model]["total_tokens"] += tokens_sum
            by_model[model]["cost_usd"] += cost

        # Round model costs
        for model_data in by_model.values():
            model_data["cost_usd"] = round(model_data["cost_usd"], 6)

        response = CostStatsResponse(
            total_summaries=len(all_summaries),
            total_prompt_tokens=total_prompt_tokens,
            total_completion_tokens=total_completion_tokens,
            total_tokens=total_tokens,
            total_cost_usd=round(total_cost, 6),
            cost_last_24h_usd=round(cost_24h, 6),
            cost_last_7d_usd=round(cost_7d, 6),
            cost_last_30d_usd=round(cost_30d, 6),
            by_model=by_model,
        )

        logger.info(
            f"Successfully calculated costs: ${total_cost:.6f} total, "
            f"${cost_24h:.6f} (24h), ${cost_7d:.6f} (7d), ${cost_30d:.6f} (30d)"
        )
        return response

    except Exception as e:
        logger.error(f"Error calculating costs: {e}", exc_info=True)
        raise InternalServerError(
            "Failed to calculate cost statistics", detail=str(e)
        )
