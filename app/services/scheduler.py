import logging
from typing import Any, Dict, List, Optional

from taskiq_redis import ListRedisScheduleSource

from app.models.player import Player

logger = logging.getLogger(__name__)


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
