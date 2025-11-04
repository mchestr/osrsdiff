"""System administration and metadata API endpoints."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import require_auth
from src.models.base import get_db_session
from src.models.hiscore import HiscoreRecord
from src.models.player import Player

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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve database statistics",
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform system health check",
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve player distribution statistics",
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


@router.post("/trigger-game-mode-check", response_model=TaskTriggerResponse)
async def trigger_game_mode_check(
    current_user: Dict[str, Any] = Depends(require_auth),
) -> TaskTriggerResponse:
    """
    Manually trigger a game mode downgrade check for all active players.

    This endpoint allows administrators to manually trigger the daily game mode
    check task without waiting for the scheduled run. The task will check all
    active players to see if their game mode has changed (e.g., hardcore ironman
    died and became regular ironman).

    Args:
        current_user: Authenticated user information

    Returns:
        TaskTriggerResponse: Confirmation that the task was triggered

    Raises:
        500 Internal Server Error: Task trigger errors
    """
    try:
        logger.info(
            f"User {current_user.get('username')} manually triggering game mode check"
        )

        # Import the task directly and trigger it
        from src.workers.fetch import check_game_mode_downgrades_task

        # Trigger the task directly using TaskIQ
        await check_game_mode_downgrades_task.kiq()

        response = TaskTriggerResponse(
            task_name="check_game_mode_downgrades",
            message="Game mode downgrade check task has been triggered successfully",
            timestamp=datetime.utcnow().isoformat(),
        )

        logger.info("Successfully triggered manual game mode check")
        return response

    except Exception as e:
        logger.error(f"Error triggering game mode check: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger game mode check: {str(e)}",
        )


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
        from src.workers.main import scheduler

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
            # Add static information about known scheduled tasks
            tasks_info.append(
                ScheduledTaskInfo(
                    name="check_game_mode_downgrades_task",
                    cron_expression="0 2 * * *",
                    description="Daily game mode downgrade check",
                    last_run=None,
                    next_run="Daily at 2 AM UTC",
                    should_run_now=False,
                )
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve scheduled tasks: {str(e)}",
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

        # Map task names to actual TaskIQ tasks
        task_mapping = {
            "check_game_mode_downgrades_task": "src.workers.fetch:check_game_mode_downgrades_task",
            "check_game_modes": "src.workers.fetch:check_game_mode_downgrades_task",  # Alias
        }

        if task_name not in task_mapping:
            raise ValueError(f"Task '{task_name}' not found")

        # Import and trigger the specific task
        if task_name in [
            "check_game_mode_downgrades_task",
            "check_game_modes",
        ]:
            from src.workers.fetch import check_game_mode_downgrades_task

            await check_game_mode_downgrades_task.kiq()
        else:
            raise ValueError(f"Task '{task_name}' not supported")

        response = TaskTriggerResponse(
            task_name=task_name,
            message=f"Task '{task_name}' has been triggered successfully",
            timestamp=datetime.utcnow().isoformat(),
        )

        logger.info(f"Successfully triggered task: {task_name}")
        return response

    except ValueError as e:
        # Task not found
        logger.warning(f"Task not found: {task_name}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error triggering task {task_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger task: {str(e)}",
        )
