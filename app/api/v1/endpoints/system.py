import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_utils import require_auth
from app.exceptions import InternalServerError, NotFoundError
from app.models.base import get_db_session
from app.models.hiscore import HiscoreRecord
from app.models.player import Player
from app.models.task_execution import TaskExecution, TaskExecutionStatus

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
    current_user: Dict[str, Any] = Depends(require_auth),
) -> DatabaseStatsResponse:
    """
    Get comprehensive database statistics.

    Returns detailed statistics about players, hiscore records, and system usage.
    Useful for monitoring system growth and usage patterns.

    Args:
        db_session: Database session dependency
        current_user: Authenticated user information

    Returns:
        DatabaseStatsResponse: Comprehensive database statistics

    Raises:
        500 Internal Server Error: Database or calculation errors
    """
    try:
        logger.info(
            f"User {current_user.get('username')} requesting database stats"
        )

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


class TaskTriggerResponse(BaseModel):
    """Response model for task trigger operations."""

    task_name: str = Field(description="Name of the triggered task")
    message: str = Field(description="Success message")
    timestamp: str = Field(description="When the task was triggered")


class ScheduledTaskInfo(BaseModel):
    """Information about a scheduled task."""

    name: str = Field(description="Task name")
    cron_expression: str = Field(description="Cron schedule expression")
    description: str = Field(description="Task description")
    last_run: Optional[str] = Field(description="Last run timestamp")
    next_run: str = Field(description="Next scheduled run timestamp")
    should_run_now: bool = Field(description="Whether task should run now")


class ScheduledTasksResponse(BaseModel):
    """Response model for scheduled tasks list."""

    tasks: List[ScheduledTaskInfo] = Field(
        description="List of scheduled tasks"
    )
    total_count: int = Field(description="Total number of tasks")


@router.get("/scheduled-tasks", response_model=ScheduledTasksResponse)
async def get_scheduled_tasks(
    current_user: Dict[str, Any] = Depends(require_auth),
) -> ScheduledTasksResponse:
    """
    Get information about all scheduled tasks.

    Returns details about each scheduled task including their cron expressions,
    last run times, next run times, and current status.

    Note: This endpoint now returns information about TaskIQ scheduled tasks
    managed by the TaskiqScheduler instead of the old custom scheduler.

    Args:
        current_user: Authenticated user information

    Returns:
        ScheduledTasksResponse: List of scheduled tasks with their information

    Raises:
        500 Internal Server Error: Scheduler errors
    """
    try:
        logger.info(
            f"User {current_user.get('username')} requesting scheduled tasks info"
        )

        # Import the TaskIQ scheduler
        from app.workers.main import scheduler

        # Get schedules from Redis schedule source
        tasks_info = []

        # Get schedules from the Redis schedule source
        redis_source = scheduler.sources[
            0
        ]  # First source is RedisScheduleSource
        try:
            schedules = await redis_source.get_schedules()

            for schedule in schedules:
                # Convert TaskIQ schedule to our response format
                task_info = ScheduledTaskInfo(
                    name=schedule.schedule_id,
                    cron_expression=schedule.cron or "N/A",
                    description=f"TaskIQ scheduled task: {schedule.task_name}",
                    last_run=None,  # TaskIQ doesn't track last run in schedule
                    next_run="Managed by TaskIQ scheduler",
                    should_run_now=False,  # TaskIQ manages this internally
                )
                tasks_info.append(task_info)

        except Exception as e:
            logger.warning(f"Could not retrieve schedules from Redis: {e}")

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
    without waiting for its scheduled time. Currently supports triggering
    TaskIQ tasks directly.

    Args:
        task_name: Name of the task to trigger (e.g., "check_game_mode_downgrades_task")
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

        # No scheduled tasks currently supported for manual triggering
        raise NotFoundError(f"Task '{task_name}' not found")

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error triggering task {task_name}: {e}")
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
    task_name: Optional[str] = None,
    status: Optional[str] = None,
    schedule_id: Optional[str] = None,
    player_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    db_session: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(require_auth),
) -> TaskExecutionsListResponse:
    """
    Get task execution history with filtering options.

    This endpoint allows querying task execution history to debug why tasks
    may not have executed at scheduled times. Supports filtering by task name,
    status, schedule_id, and player_id.

    Args:
        task_name: Filter by task name (e.g., 'fetch_player_hiscores_task')
        status: Filter by status (e.g., 'failure', 'success', 'retry')
        schedule_id: Filter by schedule ID
        player_id: Filter by player ID
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
            f"(task_name={task_name}, status={status}, schedule_id={schedule_id}, "
            f"player_id={player_id}, limit={limit}, offset={offset})"
        )

        # Validate and clamp limit
        limit = min(max(1, limit), 200)

        # Build query
        query = select(TaskExecution)

        # Apply filters
        if task_name:
            query = query.where(TaskExecution.task_name == task_name)
        if status:
            try:
                status_enum = TaskExecutionStatus(status)
                query = query.where(TaskExecution.status == status_enum)
            except ValueError:
                # Invalid status, return empty results
                return TaskExecutionsListResponse(
                    total=0,
                    limit=limit,
                    offset=offset,
                    executions=[],
                )
        if schedule_id:
            query = query.where(TaskExecution.schedule_id == schedule_id)
        if player_id:
            query = query.where(TaskExecution.player_id == player_id)

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
