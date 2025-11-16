import logging
from collections import Counter
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, overload

from sqlalchemy import Row, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from taskiq_redis import ListRedisScheduleSource

from app.models.player import Player

if TYPE_CHECKING:
    Schedule = Any

logger = logging.getLogger(__name__)

PLAYER_SCHEDULE_PREFIX = "player_fetch_"


class PlayerScheduleManagerError(Exception):
    """Base exception for player schedule manager errors."""

    pass


class ScheduleCreationError(PlayerScheduleManagerError):
    """Raised when schedule creation fails."""

    pass


class ScheduleDeletionError(PlayerScheduleManagerError):
    """Raised when schedule deletion fails."""

    pass


class PlayerScheduleManager:
    """
    Manages individual player scheduling using TaskIQ scheduler.

    This service handles creating, updating, and deleting scheduled tasks
    for individual players using TaskIQ's RedisScheduleSource for dynamic
    scheduling capabilities.
    """

    def __init__(self, redis_source: ListRedisScheduleSource):
        """
        Initialize the player schedule manager.

        Args:
            redis_source: TaskIQ Redis schedule source for dynamic scheduling
        """
        self.redis_source = redis_source

    async def schedule_player(self, player: Player) -> str:
        """
        Create a scheduled task for a player.

        Uses deterministic schedule IDs based on player ID to avoid duplicates
        and enable easy lookup/management. The schedule ID format is:
        player_fetch_{player_id}

        This method checks if a schedule already exists and removes it before
        creating a new one to prevent duplicates.

        Args:
            player: Player entity to schedule

        Returns:
            str: The schedule ID that was created

        Raises:
            ScheduleCreationError: If schedule creation fails
        """
        try:
            # Generate deterministic schedule ID
            custom_schedule_id = f"player_fetch_{player.id}"

            # Check if schedule already exists and remove it to prevent duplicates
            try:
                existing_schedules = await self.redis_source.get_schedules()
                for existing_schedule in existing_schedules:
                    if existing_schedule.schedule_id == custom_schedule_id:
                        logger.warning(
                            f"Schedule {custom_schedule_id} already exists for player {player.username}, "
                            "removing existing schedule before creating new one"
                        )
                        await self.redis_source.delete_schedule(
                            custom_schedule_id
                        )
                        break
            except Exception as e:
                logger.warning(
                    f"Could not check for existing schedule {custom_schedule_id}: {e}. "
                    "Proceeding with schedule creation."
                )

            # Convert fetch interval to cron expression
            cron_expression = self._interval_to_cron(
                player.fetch_interval_minutes
            )

            logger.info(
                f"Creating schedule for player {player.username} (ID: {player.id}) "
                f"with interval {player.fetch_interval_minutes} minutes (cron: {cron_expression})"
            )

            # Import the task here to avoid circular imports
            from app.workers.fetch import fetch_player_hiscores_task

            # Create the schedule with labels for metadata
            schedule = (
                await fetch_player_hiscores_task.kicker()
                .with_schedule_id(custom_schedule_id)
                .with_labels(
                    player_id=str(player.id),
                    schedule_type="player_fetch",
                    username=player.username,
                )
                .schedule_by_cron(
                    self.redis_source,
                    cron_expression,
                    player.username,  # Task argument
                )
            )

            logger.info(
                f"Successfully created schedule {schedule.schedule_id} for player {player.username}"
            )

            return str(schedule.schedule_id)

        except Exception as e:
            error_msg = f"Failed to create schedule for player {player.username} (ID: {player.id}): {e}"
            logger.error(error_msg)
            raise ScheduleCreationError(error_msg) from e

    async def unschedule_player(self, player: Player) -> None:
        """
        Remove a player's scheduled task.

        This method handles errors gracefully and will not fail if the schedule
        doesn't exist in Redis (e.g., if it was already deleted or never created).

        Args:
            player: Player entity to unschedule

        Raises:
            ScheduleDeletionError: If schedule deletion fails unexpectedly
        """
        if not player.schedule_id:
            logger.debug(
                f"Player {player.username} has no schedule_id, nothing to unschedule"
            )
            return

        try:
            logger.info(
                f"Unscheduling player {player.username} (schedule_id: {player.schedule_id})"
            )

            # Delete the schedule from Redis
            if player.schedule_id:
                await self.redis_source.delete_schedule(player.schedule_id)

            logger.info(f"Successfully unscheduled player {player.username}")

        except Exception as e:
            # Log warning but don't raise - schedule might already be deleted
            logger.warning(
                f"Failed to delete schedule {player.schedule_id} for player {player.username}: {e}. "
                "This may be expected if the schedule was already deleted."
            )
            # Only raise if it's an unexpected error type
            if "not found" not in str(e).lower():
                error_msg = f"Unexpected error unscheduling player {player.username}: {e}"
                logger.error(error_msg)
                raise ScheduleDeletionError(error_msg) from e

    async def reschedule_player(self, player: Player) -> str:
        """
        Update a player's schedule (unschedule + schedule).

        This is used when a player's fetch interval is changed. It will
        remove the existing schedule and create a new one with the updated
        interval.

        Args:
            player: Player entity to reschedule

        Returns:
            str: The new schedule ID

        Raises:
            ScheduleCreationError: If the new schedule creation fails
            ScheduleDeletionError: If the old schedule deletion fails unexpectedly
        """
        logger.info(
            f"Rescheduling player {player.username} with new interval {player.fetch_interval_minutes} minutes"
        )

        # First unschedule the existing task
        await self.unschedule_player(player)

        # Then create a new schedule
        new_schedule_id = await self.schedule_player(player)

        logger.info(
            f"Successfully rescheduled player {player.username} with new schedule_id: {new_schedule_id}"
        )

        return new_schedule_id

    async def ensure_player_scheduled(self, player: Player) -> str:
        """
        Ensure player has a valid schedule, create if missing.

        This method verifies that the player's schedule exists in Redis and
        recreates it if it's missing. It includes comprehensive validation
        and recovery logic to handle various failure scenarios.

        Args:
            player: Player entity to verify/ensure scheduling

        Returns:
            str: The schedule ID (existing or newly created)

        Raises:
            ScheduleCreationError: If schedule creation fails
        """
        # If no schedule_id in database, create new schedule
        if not player.schedule_id:
            logger.info(
                f"Player {player.username} has no schedule_id, creating new schedule"
            )
            return await self.schedule_player(player)

        try:
            # Verify schedule still exists in Redis and is valid
            is_valid = await self._verify_schedule_exists_and_valid(player)

            if is_valid:
                logger.debug(
                    f"Schedule {player.schedule_id} is valid for player {player.username}"
                )
                return player.schedule_id
            else:
                logger.warning(
                    f"Schedule {player.schedule_id} is invalid or missing for player {player.username}, recreating"
                )
                # Clear the old schedule_id and create new schedule
                old_schedule_id: Optional[str] = player.schedule_id
                player.schedule_id = None

                # Try to clean up the old schedule if it exists
                if old_schedule_id:
                    try:
                        await self.redis_source.delete_schedule(
                            old_schedule_id
                        )
                        logger.debug(
                            f"Cleaned up old schedule {old_schedule_id}"
                        )
                    except Exception as cleanup_error:
                        logger.debug(
                            f"Could not clean up old schedule {old_schedule_id}: {cleanup_error}"
                        )

                return await self.schedule_player(player)

        except Exception as e:
            logger.error(
                f"Failed to verify schedule existence for player {player.username}: {e}"
            )
            # Recreate schedule to be safe
            logger.info(
                f"Recreating schedule for player {player.username} due to verification error"
            )
            old_schedule_id = player.schedule_id
            player.schedule_id = None

            # Try to clean up the old schedule if it exists
            if old_schedule_id:
                try:
                    await self.redis_source.delete_schedule(old_schedule_id)
                    logger.debug(
                        f"Cleaned up old schedule {old_schedule_id} during error recovery"
                    )
                except Exception as cleanup_error:
                    logger.debug(
                        f"Could not clean up old schedule {old_schedule_id} during error recovery: {cleanup_error}"
                    )

            return await self.schedule_player(player)

    async def _verify_schedule_exists_and_valid(self, player: Player) -> bool:
        """
        Verify that a player's schedule exists in Redis and is valid.

        This method checks both the existence of the schedule and validates
        that its configuration matches the player's current settings.

        Args:
            player: Player entity to verify

        Returns:
            bool: True if schedule exists and is valid, False otherwise
        """
        if not player.schedule_id:
            return False

        try:
            # Get all schedules from Redis
            schedules = await self.redis_source.get_schedules()

            # Find the player's schedule
            player_schedule = None
            for schedule in schedules:
                if schedule.schedule_id == player.schedule_id:
                    player_schedule = schedule
                    break

            if not player_schedule:
                logger.debug(
                    f"Schedule {player.schedule_id} not found in Redis"
                )
                return False

            # Validate schedule configuration matches player settings
            expected_cron = self._interval_to_cron(
                player.fetch_interval_minutes
            )

            # Check if cron expression matches (allowing for some flexibility in format)
            if (
                hasattr(player_schedule, "cron")
                and player_schedule.cron != expected_cron
            ):
                logger.warning(
                    f"Schedule {player.schedule_id} has mismatched cron expression. "
                    f"Expected: {expected_cron}, Found: {player_schedule.cron}"
                )
                return False

            # Check if task name matches
            # TaskIQ stores task names as "module:function_name" format
            if hasattr(player_schedule, "task_name"):
                expected_task_name = "fetch_player_hiscores_task"
                # Extract function name from stored task name (handles both formats)
                stored_task_name = player_schedule.task_name
                # If stored name contains ':', extract the function name part
                if ":" in stored_task_name:
                    stored_function_name = stored_task_name.split(":")[-1]
                else:
                    stored_function_name = stored_task_name

                if stored_function_name != expected_task_name:
                    logger.warning(
                        f"Schedule {player.schedule_id} has wrong task name. "
                        f"Expected: {expected_task_name}, Found: {stored_task_name} (extracted: {stored_function_name})"
                    )
                    return False

            # Check if labels contain correct player_id
            if hasattr(player_schedule, "labels") and player_schedule.labels:
                stored_player_id = player_schedule.labels.get("player_id")
                if stored_player_id != str(player.id):
                    logger.warning(
                        f"Schedule {player.schedule_id} has wrong player_id in labels. "
                        f"Expected: {player.id}, Found: {stored_player_id}"
                    )
                    return False

            logger.debug(
                f"Schedule {player.schedule_id} is valid for player {player.username}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error verifying schedule for player {player.username}: {e}"
            )
            return False

    def _interval_to_cron(self, minutes: int) -> str:
        """
        Convert fetch interval to cron expression with proper validation.

        This method converts a fetch interval in minutes to a valid cron
        expression that can be used with TaskIQ's scheduler. It includes
        comprehensive validation to ensure the interval is reasonable and
        will produce a valid cron expression.

        Args:
            minutes: Fetch interval in minutes

        Returns:
            str: Cron expression

        Raises:
            ValueError: If the interval is invalid or would produce an invalid cron
        """
        # Validate input type and range
        if not isinstance(minutes, int):
            raise ValueError(
                f"Fetch interval must be an integer, got {type(minutes).__name__}"
            )

        if minutes < 1:
            raise ValueError(
                f"Invalid fetch interval: {minutes} minutes. Must be at least 1 minute."
            )

        # Set reasonable upper limit to prevent excessive scheduling
        max_interval_days = 7  # 1 week maximum
        max_minutes = max_interval_days * 24 * 60
        if minutes > max_minutes:
            raise ValueError(
                f"Fetch interval too large: {minutes} minutes. "
                f"Maximum allowed is {max_minutes} minutes ({max_interval_days} days)."
            )

        # Generate cron expression based on interval
        cron_expr = self._generate_cron_expression(minutes)

        # Validate the generated cron expression
        self._validate_cron_expression(cron_expr)

        return cron_expr

    def _generate_cron_expression(self, minutes: int) -> str:
        """
        Generate cron expression for the given interval in minutes.

        Args:
            minutes: Fetch interval in minutes

        Returns:
            str: Cron expression
        """
        if minutes < 60:
            # Sub-hourly intervals: */N * * * *
            # Validate that the interval divides evenly into 60 for better scheduling
            if 60 % minutes != 0 and minutes > 30:
                logger.warning(
                    f"Interval {minutes} minutes does not divide evenly into an hour. "
                    "This may result in irregular scheduling patterns."
                )
            return f"*/{minutes} * * * *"
        elif minutes == 60:
            # Hourly: 0 * * * *
            return "0 * * * *"
        elif minutes == 1440:
            # Daily: 0 0 * * *
            return "0 0 * * *"
        elif minutes % 1440 == 0:
            # Multi-day intervals: use daily cron with day-of-week or day-of-month
            days = minutes // 1440
            if days <= 7:
                # Weekly or less: use day-of-week (0 = Sunday)
                return f"0 0 */{days} * *"
            else:
                # Longer than weekly: use daily (will run every day, but this is the safest approach)
                logger.warning(
                    f"Interval {days} days is longer than a week. Using daily cron for safety."
                )
                return "0 0 * * *"
        elif minutes % 60 == 0:
            # Multi-hour intervals: 0 */N * * *
            hours = minutes // 60
            if hours <= 23:
                return f"0 */{hours} * * *"
            elif hours == 24:
                return "0 0 * * *"  # Daily
            else:
                # Longer than 24 hours but not exact days
                logger.warning(
                    f"Interval {hours} hours ({minutes} minutes) is longer than a day but not exact days. "
                    "Using daily cron for safety."
                )
                return "0 0 * * *"
        else:
            # Non-standard intervals: use minute-based cron with warnings for large values
            if minutes > 1440:  # More than a day
                logger.warning(
                    f"Large non-standard interval {minutes} minutes may cause performance issues. "
                    "Consider using a standard interval (hourly, daily, etc.)."
                )
            return f"*/{minutes} * * * *"

    def _validate_cron_expression(self, cron_expr: str) -> None:
        """
        Validate that a cron expression is properly formatted.

        This performs basic validation to ensure the cron expression has the
        correct number of fields and reasonable values.

        Args:
            cron_expr: Cron expression to validate

        Raises:
            ValueError: If the cron expression is invalid
        """
        if not isinstance(cron_expr, str):
            raise ValueError(
                f"Cron expression must be a string, got {type(cron_expr).__name__}"
            )

        fields = cron_expr.strip().split()
        if len(fields) != 5:
            raise ValueError(
                f"Cron expression must have exactly 5 fields (minute hour day month weekday), "
                f"got {len(fields)}: '{cron_expr}'"
            )

        minute, hour, day, month, weekday = fields

        # Basic field validation
        self._validate_cron_field(minute, "minute", 0, 59)
        self._validate_cron_field(hour, "hour", 0, 23)
        self._validate_cron_field(day, "day", 1, 31)
        self._validate_cron_field(month, "month", 1, 12)
        self._validate_cron_field(
            weekday, "weekday", 0, 7
        )  # 0 and 7 both represent Sunday

    def _validate_cron_field(
        self, field: str, field_name: str, min_val: int, max_val: int
    ) -> None:
        """
        Validate a single cron field.

        Args:
            field: Cron field value (e.g., "*/5", "0", "*")
            field_name: Name of the field for error messages
            min_val: Minimum allowed value for this field
            max_val: Maximum allowed value for this field

        Raises:
            ValueError: If the field is invalid
        """
        if field == "*":
            return  # Wildcard is always valid

        # Handle step values (*/N)
        if field.startswith("*/"):
            try:
                step = int(field[2:])
                if step < 1:
                    raise ValueError(
                        f"Invalid {field_name} step value: {step}. Must be at least 1."
                    )

                # For step values, we allow larger values than the field maximum
                # because they represent intervals (e.g., */90 means "every 90 minutes")
                # We only validate that it's a reasonable positive integer
                if step > 10080:  # 1 week in minutes - reasonable upper bound
                    raise ValueError(
                        f"Invalid {field_name} step value: {step}. Step value too large."
                    )

            except ValueError as e:
                if "invalid literal" in str(e):
                    raise ValueError(
                        f"Invalid {field_name} step format: '{field}'. Expected */N where N is a number."
                    )
                raise
            return

        # Handle single numeric values
        try:
            value = int(field)
            if value < min_val or value > max_val:
                raise ValueError(
                    f"Invalid {field_name} value: {value}. Must be between {min_val} and {max_val}."
                )
        except ValueError as e:
            if "invalid literal" in str(e):
                raise ValueError(
                    f"Invalid {field_name} format: '{field}'. Expected number, *, or */N."
                )
            raise


# Global instance - lazily initialized to avoid circular imports
_player_schedule_manager: Optional[PlayerScheduleManager] = None


def _get_redis_schedule_source() -> ListRedisScheduleSource:
    """Lazy import to avoid circular dependency."""
    from app.workers.scheduler import redis_schedule_source

    return redis_schedule_source


def get_player_schedule_manager() -> PlayerScheduleManager:
    """
    Get or create the global player schedule manager instance.

    Uses lazy initialization to avoid circular import issues.

    Returns:
        PlayerScheduleManager: Configured player schedule manager instance
    """
    global _player_schedule_manager
    if _player_schedule_manager is None:
        redis_source = _get_redis_schedule_source()
        _player_schedule_manager = PlayerScheduleManager(redis_source)
    return _player_schedule_manager


# Create a simple accessor that looks like a variable
class _PlayerScheduleManagerProxy:
    """Proxy object that provides attribute access to the manager."""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_player_schedule_manager(), name)

    def __call__(self, *args: Any, **kwargs: Any) -> PlayerScheduleManager:
        return get_player_schedule_manager()


# Module-level variable that acts like PlayerScheduleManager
player_schedule_manager = _PlayerScheduleManagerProxy()


# Schedule maintenance methods (merged from ScheduleMaintenanceService)
class ScheduleMaintenanceService:
    """
    Service for performing schedule maintenance operations.

    This service provides methods for cleaning up orphaned schedules,
    verifying consistency, and performing bulk operations on player schedules.

    Works directly with Redis schedule source to avoid issues with the scheduler abstraction.
    """

    def __init__(self, redis_source: ListRedisScheduleSource):
        """
        Initialize the maintenance service.

        Args:
            redis_source: Redis schedule source for direct Redis access
        """
        self.redis_source = redis_source

    # Helper methods
    async def _get_player_schedules(self) -> list["Schedule"]:
        """Get all player schedules from Redis."""
        all_schedules = await self.redis_source.get_schedules()
        return [
            s
            for s in all_schedules
            if hasattr(s, "schedule_id")
            and getattr(s, "schedule_id", "").startswith(
                PLAYER_SCHEDULE_PREFIX
            )
        ]

    @overload
    async def _get_active_players(
        self,
        db_session: AsyncSession,
        include_schedule_id: bool,
    ) -> list[Row[tuple[int, str, str | None]]]: ...

    @overload
    async def _get_active_players(
        self,
        db_session: AsyncSession,
        include_schedule_id: bool = False,
    ) -> list[Player]: ...

    async def _get_active_players(
        self,
        db_session: AsyncSession,
        include_schedule_id: bool = True,
    ) -> list[Row[tuple[int, str, str | None]]] | list[Player]:
        """Get active players from database."""
        if include_schedule_id:
            row_stmt = select(
                Player.id, Player.username, Player.schedule_id
            ).where(Player.is_active.is_(True))
            result: Any = await db_session.execute(row_stmt)
            return list(result.all())
        else:
            player_stmt = select(Player).where(Player.is_active.is_(True))
            result = await db_session.execute(player_stmt)
            return list(result.scalars().all())

    def _extract_player_id_from_schedule_id(
        self, schedule_id: str
    ) -> int | None:
        """Extract player ID from schedule_id, return None if invalid."""
        if not schedule_id.startswith(PLAYER_SCHEDULE_PREFIX):
            return None
        try:
            return int(schedule_id.removeprefix(PLAYER_SCHEDULE_PREFIX))
        except ValueError:
            return None

    def _create_result(
        self,
        status: str,
        message: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create standardized result dictionary."""
        from datetime import UTC

        return {
            "status": status,
            "message": message,
            "timestamp": datetime.now(UTC).isoformat(),
            **kwargs,
        }

    def _create_error_result(
        self, error: str, message: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Create standardized error result."""
        return self._create_result("error", message, error=error, **kwargs)

    async def cleanup_orphaned_schedules(
        self, db_session: AsyncSession, dry_run: bool = False
    ) -> dict[str, Any]:
        """
        Remove schedules for deleted or inactive players.

        Args:
            db_session: Database session
            dry_run: If True, return what would be done without making changes

        Returns:
            Dict with cleanup results and statistics
        """
        logger.info("Starting cleanup of orphaned schedules")

        try:
            player_schedules = await self._get_player_schedules()
            if not player_schedules:
                return self._create_result(
                    "success",
                    "No player schedules found",
                    schedules_processed=0,
                    schedules_removed=0,
                    orphaned_schedules=[],
                )

            active_players = await self._get_active_players(db_session)
            # When called with default (include_schedule_id=True), returns Row objects
            active_player_ids = {str(player.id) for player in active_players}
            active_schedule_ids = {
                player.schedule_id
                for player in active_players
                if player.schedule_id is not None
            }

            orphaned_schedule_ids = set()
            orphaned_schedules = []

            for schedule in player_schedules:
                schedule_id = getattr(schedule, "schedule_id", "")
                if schedule_id in orphaned_schedule_ids:
                    continue

                player_id = self._extract_player_id_from_schedule_id(
                    schedule_id
                )
                if player_id is None:
                    orphaned_schedule_ids.add(schedule_id)
                    orphaned_schedules.append(
                        {
                            "schedule_id": schedule_id,
                            "reason": "Invalid player ID format",
                            "player_id": None,
                        }
                    )
                    continue

                player_id_str = str(player_id)
                if player_id_str not in active_player_ids:
                    orphaned_schedule_ids.add(schedule_id)
                    orphaned_schedules.append(
                        {
                            "schedule_id": schedule_id,
                            "reason": "Player not found or inactive",
                            "player_id": player_id_str,
                        }
                    )
                elif schedule_id not in active_schedule_ids:
                    orphaned_schedule_ids.add(schedule_id)
                    orphaned_schedules.append(
                        {
                            "schedule_id": schedule_id,
                            "reason": "Schedule not referenced in database",
                            "player_id": player_id_str,
                        }
                    )

            removed_count = 0
            removal_errors = []

            if not dry_run:
                for orphan in orphaned_schedules:
                    schedule_id = orphan.get("schedule_id")
                    if schedule_id and schedule_id != "unknown":
                        try:
                            await self.redis_source.delete_schedule(
                                schedule_id
                            )
                            removed_count += 1
                        except Exception as e:
                            removal_errors.append(
                                f"Failed to remove {schedule_id}: {str(e)}"
                            )
                            logger.error(
                                f"Error removing orphaned schedule {schedule_id}: {e}",
                                exc_info=True,
                            )

            result = self._create_result(
                "success",
                f"Cleanup completed: {len(orphaned_schedules)} orphaned schedules found",
                schedules_processed=len(player_schedules),
                schedules_removed=removed_count if not dry_run else 0,
                orphaned_schedules=orphaned_schedules,
                dry_run=dry_run,
            )

            if removal_errors:
                result["removal_errors"] = removal_errors

            return result

        except Exception as e:
            logger.error(
                f"Error during orphaned schedule cleanup: {e}", exc_info=True
            )
            return self._create_error_result(
                str(e), f"Cleanup failed: {str(e)}"
            )

    async def verify_schedule_consistency(
        self, db_session: AsyncSession
    ) -> dict[str, Any]:
        """
        Verify consistency between database and Redis schedules.

        Args:
            db_session: Database session

        Returns:
            Dict with verification results and inconsistencies found
        """
        logger.info("Starting schedule consistency verification")

        try:
            player_schedules = await self._get_player_schedules()
            redis_schedule_ids = {
                getattr(schedule, "schedule_id", "")
                for schedule in player_schedules
            }

            active_players = await self._get_active_players(
                db_session, include_schedule_id=False
            )
            # When include_schedule_id=False, we get Player objects
            active_players_with_schedule = [
                p for p in active_players if p.schedule_id is not None
            ]
            active_player_ids = {player.id for player in active_players}
            player_by_id = {player.id: player for player in active_players}

            inconsistencies = []

            # Check each player's schedule
            for player in active_players_with_schedule:
                if not player.schedule_id:
                    inconsistencies.append(
                        {
                            "type": "null_schedule_id",
                            "player_id": player.id,
                            "username": player.username,
                            "issue": "Player has null schedule_id",
                        }
                    )
                elif player.schedule_id not in redis_schedule_ids:
                    inconsistencies.append(
                        {
                            "type": "missing_redis_schedule",
                            "player_id": player.id,
                            "username": player.username,
                            "schedule_id": player.schedule_id,
                            "issue": f"Schedule {player.schedule_id} not found in Redis",
                        }
                    )

            # Check for schedules in Redis without corresponding active players
            for schedule in player_schedules:
                schedule_id = getattr(schedule, "schedule_id", "")
                player_id = self._extract_player_id_from_schedule_id(
                    schedule_id
                )

                if player_id is None:
                    inconsistencies.append(
                        {
                            "type": "invalid_schedule_format",
                            "schedule_id": schedule_id,
                            "issue": "Invalid player ID format in schedule_id",
                        }
                    )
                elif player_id not in active_player_ids:
                    inconsistencies.append(
                        {
                            "type": "orphaned_redis_schedule",
                            "schedule_id": schedule_id,
                            "player_id": player_id,
                            "issue": f"No active player found for player_id {player_id}",
                        }
                    )
                else:
                    db_player = player_by_id.get(player_id)
                    if (
                        db_player is not None
                        and db_player.schedule_id != schedule_id
                    ):
                        inconsistencies.append(
                            {
                                "type": "schedule_id_mismatch",
                                "schedule_id": schedule_id,
                                "player_id": player_id,
                                "username": db_player.username,
                                "db_schedule_id": db_player.schedule_id,
                                "issue": f"Player has different schedule_id in database: {db_player.schedule_id}",
                            }
                        )

            # Categorize inconsistencies
            inconsistency_counts = Counter(
                inconsistency.get("type", "unknown")
                for inconsistency in inconsistencies
            )

            is_consistent = not inconsistencies
            inconsistency_msg = (
                "No inconsistencies found"
                if is_consistent
                else f"{len(inconsistencies)} inconsistencies found"
            )

            return self._create_result(
                "success",
                f"Verification completed: {inconsistency_msg}",
                is_consistent=is_consistent,
                redis_schedules_count=len(player_schedules),
                active_players_count=len(active_players),
                inconsistencies_count=len(inconsistencies),
                inconsistency_types=dict(inconsistency_counts),
                inconsistencies=inconsistencies,
            )

        except Exception as e:
            logger.error(
                f"Error during consistency verification: {e}", exc_info=True
            )
            return self._create_error_result(
                str(e), f"Verification failed: {str(e)}"
            )

    async def get_schedule_summary(
        self, db_session: AsyncSession
    ) -> dict[str, Any]:
        """
        Get a summary of all schedules and their status.

        Args:
            db_session: Database session

        Returns:
            Dict with schedule summary information
        """
        logger.info("Getting schedule summary")

        try:
            player_schedules = await self._get_player_schedules()

            total_players = (
                await db_session.execute(select(func.count(Player.id)))
            ).scalar() or 0

            active_players = (
                await db_session.execute(
                    select(func.count(Player.id)).where(
                        Player.is_active.is_(True)
                    )
                )
            ).scalar() or 0

            scheduled_players = (
                await db_session.execute(
                    select(func.count(Player.id)).where(
                        Player.is_active.is_(True),
                        Player.schedule_id.is_not(None),
                    )
                )
            ).scalar() or 0

            unscheduled_players = (
                await db_session.execute(
                    select(func.count(Player.id)).where(
                        Player.is_active.is_(True),
                        Player.schedule_id.is_(None),
                    )
                )
            ).scalar() or 0

            return self._create_result(
                "success",
                "Schedule summary retrieved",
                summary={
                    "total_players": total_players,
                    "active_players": active_players,
                    "scheduled_players": scheduled_players,
                    "unscheduled_players": unscheduled_players,
                    "redis_schedules": len(player_schedules),
                    "schedule_coverage_percentage": (
                        scheduled_players / max(1, active_players)
                    )
                    * 100,
                },
            )

        except Exception as e:
            logger.error(f"Error getting schedule summary: {e}", exc_info=True)
            return self._create_error_result(
                str(e), f"Failed to get schedule summary: {str(e)}"
            )

    async def fix_player_schedule(
        self,
        player: Player,
        db_session: AsyncSession,
        force_recreate: bool = False,
    ) -> dict[str, Any]:
        """
        Fix a specific player's schedule by ensuring it exists and is valid.

        Args:
            player: Player to fix schedule for
            db_session: Database session
            force_recreate: If True, recreate schedule even if it appears valid

        Returns:
            Dict with fix results
        """
        logger.info(
            f"Fixing schedule for player {player.username} (ID: {player.id})"
        )

        try:
            if not player.is_active:
                return self._create_error_result(
                    "Player is inactive",
                    "Cannot fix schedule for inactive player",
                    player_id=player.id,
                    username=player.username,
                )

            old_schedule_id = player.schedule_id

            if force_recreate and old_schedule_id:
                try:
                    await self.redis_source.delete_schedule(old_schedule_id)
                except Exception as e:
                    logger.warning(
                        f"Could not delete old schedule {old_schedule_id}: {e}"
                    )
                player.schedule_id = None

            schedule_manager = get_player_schedule_manager()
            new_schedule_id = await schedule_manager.ensure_player_scheduled(
                player
            )

            player.schedule_id = new_schedule_id
            await db_session.commit()

            action = (
                "recreated"
                if force_recreate or old_schedule_id != new_schedule_id
                else "verified"
            )

            return self._create_result(
                "success",
                f"Successfully {action} schedule for {player.username}: {new_schedule_id}",
                player_id=player.id,
                username=player.username,
                action=action,
                old_schedule_id=old_schedule_id,
                new_schedule_id=new_schedule_id,
                fetch_interval=player.fetch_interval_minutes,
            )

        except Exception as e:
            await db_session.rollback()
            logger.error(
                f"Error fixing schedule for player {player.username}: {e}",
                exc_info=True,
            )
            return self._create_error_result(
                str(e),
                f"Failed to fix schedule: {str(e)}",
                player_id=player.id,
                username=player.username,
            )

    async def bulk_fix_schedules(
        self,
        db_session: AsyncSession,
        player_ids: list[int] | None = None,
        force_recreate: bool = False,
    ) -> dict[str, Any]:
        """
        Fix schedules for multiple players.

        Args:
            db_session: Database session
            player_ids: Specific player IDs to fix (None for all active players)
            force_recreate: If True, recreate all schedules even if they appear valid

        Returns:
            Dict with bulk fix results
        """
        logger.info(
            f"Starting bulk schedule fix (force_recreate: {force_recreate})"
        )

        try:
            if player_ids:
                players_stmt = select(Player).where(
                    Player.id.in_(player_ids), Player.is_active.is_(True)
                )
            else:
                players_stmt = select(Player).where(Player.is_active.is_(True))

            players = list(
                (await db_session.execute(players_stmt)).scalars().all()
            )

            if not players:
                return self._create_result(
                    "success",
                    "No players found to fix",
                    players_processed=0,
                    successful_fixes=0,
                    failed_fixes=0,
                    results=[],
                )

            logger.info(f"Fixing schedules for {len(players)} players")

            results = []
            successful_fixes = 0
            failed_fixes = 0

            for player in players:
                try:
                    fix_result = await self.fix_player_schedule(
                        player, db_session, force_recreate
                    )
                    results.append(fix_result)

                    if fix_result["status"] == "success":
                        successful_fixes += 1
                    else:
                        failed_fixes += 1

                except Exception as e:
                    failed_fixes += 1
                    results.append(
                        self._create_error_result(
                            str(e),
                            f"Unexpected error fixing schedule: {str(e)}",
                            player_id=player.id,
                            username=player.username,
                        )
                    )
                    logger.error(
                        f"Unexpected error fixing schedule for {player.username}: {e}",
                        exc_info=True,
                    )

            return self._create_result(
                "success",
                f"Bulk fix completed: {successful_fixes} successful, {failed_fixes} failed",
                players_processed=len(players),
                successful_fixes=successful_fixes,
                failed_fixes=failed_fixes,
                results=results,
            )

        except Exception as e:
            logger.error(f"Error during bulk schedule fix: {e}", exc_info=True)
            return self._create_error_result(
                str(e), f"Bulk fix failed: {str(e)}"
            )

    async def _get_redis_duplicates(self) -> dict[str, int]:
        """Get duplicate schedule IDs from Redis list directly."""
        try:
            import redis.asyncio as redis
            from app.config import settings as config_defaults

            redis_client = redis.from_url(
                config_defaults.redis.url, decode_responses=True
            )
            prefix = config_defaults.taskiq.scheduler_prefix
            cron_list_key = f"{prefix}:cron"

            redis_schedule_ids = await redis_client.lrange(
                cron_list_key, 0, -1
            )
            await redis_client.close()

            schedule_id_counts = Counter(redis_schedule_ids)

            return {
                schedule_id: count
                for schedule_id, count in schedule_id_counts.items()
                if count > 1
            }
        except Exception as e:
            logger.warning(f"Could not check Redis list for duplicates: {e}")
            return {}

    async def cleanup_duplicate_schedules(
        self, db_session: AsyncSession, dry_run: bool = False
    ) -> dict[str, Any]:
        """
        Remove duplicate schedules, keeping only the first occurrence.

        This method checks Redis directly to find duplicates, as get_schedules()
        may deduplicate by schedule_id. It inspects the underlying Redis list
        to detect all occurrences.

        Args:
            db_session: Database session
            dry_run: If True, return what would be done without making changes

        Returns:
            Dict with cleanup results and statistics
        """
        logger.info("Starting cleanup of duplicate schedules")

        try:
            all_schedules = await self.redis_source.get_schedules()
            redis_duplicates = await self._get_redis_duplicates()

            # Track duplicates from get_schedules() API
            schedule_ids_seen: dict[str, list[Any]] = {}
            for schedule in all_schedules:
                schedule_id = getattr(schedule, "schedule_id", "")
                schedule_ids_seen.setdefault(schedule_id, []).append(schedule)

            duplicate_schedules = {
                schedule_id: occurrences
                for schedule_id, occurrences in schedule_ids_seen.items()
                if len(occurrences) > 1
            }

            # Merge Redis duplicates into our tracking
            schedule_by_id = {
                getattr(s, "schedule_id", ""): s for s in all_schedules
            }
            for schedule_id, count in redis_duplicates.items():
                if schedule_id not in duplicate_schedules:
                    matching_schedule = schedule_by_id.get(schedule_id)
                    if matching_schedule:
                        duplicate_schedules[schedule_id] = [
                            matching_schedule
                        ] * count
                    else:
                        duplicate_schedules[schedule_id] = []

            if not duplicate_schedules:
                return self._create_result(
                    "success",
                    "No duplicate schedules found",
                    schedules_processed=len(all_schedules),
                    duplicates_found=0,
                    duplicates_removed=0,
                    duplicate_schedules={},
                    redis_duplicates_checked=len(redis_duplicates),
                )

            removed_count = 0
            removal_errors = []
            duplicate_details = {}
            player_schedules_to_recreate = []

            if not dry_run:
                active_players = await self._get_active_players(db_session)
                # When include_schedule_id=True (default), we get Row objects
                active_player_ids = {
                    getattr(player, "id", None)
                    for player in active_players
                    if hasattr(player, "id")
                }

                for schedule_id, occurrences in duplicate_schedules.items():
                    if not occurrences:
                        # Orphaned schedule - delete all occurrences
                        try:
                            duplicate_count = redis_duplicates.get(
                                schedule_id, 1
                            )
                            await self.redis_source.delete_schedule(
                                schedule_id
                            )
                            removed_count += duplicate_count
                            duplicate_details[schedule_id] = {
                                "total_occurrences": duplicate_count,
                                "kept": 0,
                                "removed": duplicate_count,
                                "reason": "Orphaned schedule",
                            }
                        except Exception as e:
                            removal_errors.append(
                                f"Failed to remove orphaned duplicate {schedule_id}: {str(e)}"
                            )
                        continue

                    total_duplicates = len(occurrences) - 1
                    duplicate_details[schedule_id] = {
                        "total_occurrences": len(occurrences),
                        "kept": 1,
                        "removed": total_duplicates,
                    }

                    try:
                        await self.redis_source.delete_schedule(schedule_id)
                        removed_count += total_duplicates

                        player_id = self._extract_player_id_from_schedule_id(
                            schedule_id
                        )
                        if player_id and player_id in active_player_ids:
                            player_schedules_to_recreate.append(schedule_id)
                    except Exception as e:
                        removal_errors.append(
                            f"Failed to remove duplicate {schedule_id}: {str(e)}"
                        )

                # Recreate player schedules
                for schedule_id in player_schedules_to_recreate:
                    try:
                        player_id = self._extract_player_id_from_schedule_id(
                            schedule_id
                        )
                        if not player_id:
                            continue

                        player = (
                            await db_session.execute(
                                select(Player).where(Player.id == player_id)
                            )
                        ).scalar_one_or_none()

                        if player and player.is_active:
                            schedule_manager = get_player_schedule_manager()
                            await schedule_manager.ensure_player_scheduled(
                                player
                            )
                    except Exception as e:
                        removal_errors.append(
                            f"Failed to recreate schedule {schedule_id}: {str(e)}"
                        )

            result = self._create_result(
                "success",
                f"Cleanup completed: {len(duplicate_schedules)} duplicate schedule IDs found",
                schedules_processed=len(all_schedules),
                duplicates_found=len(duplicate_schedules),
                duplicates_removed=removed_count if not dry_run else 0,
                duplicate_schedules=duplicate_details,
                dry_run=dry_run,
            )

            if removal_errors:
                result["removal_errors"] = removal_errors

            return result

        except Exception as e:
            logger.error(
                f"Error during duplicate schedule cleanup: {e}", exc_info=True
            )
            return self._create_error_result(
                str(e), f"Cleanup failed: {str(e)}"
            )
