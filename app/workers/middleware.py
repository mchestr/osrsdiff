"""TaskIQ middleware for error tracking and task execution logging."""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Dict

from taskiq.abc.middleware import TaskiqMiddleware

if TYPE_CHECKING:
    from taskiq.message import TaskiqMessage
    from taskiq.result import TaskiqResult

from app.models.base import AsyncSessionLocal
from app.models.task_execution import (
    TaskExecution,
)

logger = logging.getLogger(__name__)


class TaskExecutionTrackingMiddleware(TaskiqMiddleware):
    """
    Middleware to track all task executions in the database.

    This middleware automatically logs task executions, including:
    - Task start and completion
    - Success and failure status
    - Retry attempts
    - Error details with stack traces
    - Execution metadata (schedule_id, player_id, etc.)
    """

    async def pre_execute(
        self,
        message: "TaskiqMessage",
    ) -> "TaskiqMessage":
        """Called before task execution starts."""
        try:
            # Extract task info from message
            task_id = message.task_id
            task_name = message.task_name

            # Extract metadata from message labels if available
            schedule_id = None
            schedule_type = None
            player_id = None

            if message.labels:
                schedule_id = message.labels.get("schedule_id")
                schedule_type = message.labels.get("schedule_type")
                player_id_str = message.labels.get("player_id")
                if player_id_str:
                    try:
                        player_id = int(player_id_str)
                    except (ValueError, TypeError):
                        pass

            # Store start time in context for later use
            if not hasattr(self, "_task_start_times"):
                self._task_start_times = {}
            self._task_start_times[task_id] = {
                "started_at": datetime.now(UTC),
                "schedule_id": schedule_id,
                "schedule_type": schedule_type,
                "player_id": player_id,
            }

            logger.debug(
                f"Task {task_name} (id: {task_id}) starting "
                f"(schedule_id: {schedule_id}, player_id: {player_id})"
            )
        except Exception as e:
            # Don't let middleware errors break task execution
            task_name = getattr(message, "task_name", "unknown")
            logger.warning(
                f"Error in pre_execute middleware for {task_name}: {e}",
                exc_info=True,
            )

        # Return message to allow middleware chain to continue
        return message

    async def post_execute(
        self,
        message: "TaskiqMessage",
        result: "TaskiqResult[Any]",
    ) -> None:
        """Called after task execution completes successfully."""
        try:
            # Extract task info from message
            task_id = message.task_id
            task_name = message.task_name

            task_metadata = getattr(self, "_task_start_times", {}).get(
                task_id, {}
            )
            started_at = task_metadata.get("started_at", datetime.now(UTC))
            schedule_id = task_metadata.get("schedule_id")
            schedule_type = task_metadata.get("schedule_type")
            player_id = task_metadata.get("player_id")

            # Clean up
            if hasattr(self, "_task_start_times"):
                self._task_start_times.pop(task_id, None)

            # Extract task arguments from message
            task_args: Dict[str, Any] = {}
            if message.args:
                # For fetch_player_hiscores_task, first arg is username
                if (
                    "fetch_player_hiscores_task" in task_name
                    and message.args
                    and len(message.args) > 0
                ):
                    task_args["username"] = str(message.args[0])

            # Extract result value - TaskiqResult has return_value attribute
            result_value = (
                result.return_value
                if hasattr(result, "return_value")
                else None
            )

            # Handle result - could be a dict with status or a simple value
            result_dict: Dict[str, Any] = {}
            if isinstance(result_value, dict):
                result_dict = result_value
            elif result_value is not None:
                result_dict = {"result": result_value}

            # Determine retry count from message labels if available
            retry_count = 0
            if message.labels:
                retry_count_str = message.labels.get("retry_count")
                if retry_count_str:
                    try:
                        retry_count = int(retry_count_str)
                    except (ValueError, TypeError):
                        pass

            try:
                async with AsyncSessionLocal() as db_session:
                    execution = TaskExecution.create_from_result(
                        task_name=task_name,
                        result=result_dict,
                        task_args=task_args if task_args else None,
                        retry_count=retry_count,
                        schedule_id=schedule_id,
                        schedule_type=schedule_type,
                        player_id=player_id,
                        started_at=started_at,
                    )
                    db_session.add(execution)
                    await db_session.commit()

                    logger.debug(
                        f"Logged task execution: {task_name} (id: {execution.id}, "
                        f"status: {execution.status})"
                    )
            except Exception as e:
                # Don't let tracking errors break task execution
                logger.error(
                    f"Failed to log task execution for {task_name}: {e}",
                    exc_info=True,
                )
        except Exception as e:
            # Don't let middleware errors break task execution
            logger.error(
                f"Error in post_execute middleware: {e}",
                exc_info=True,
            )

    async def on_error(
        self,
        message: "TaskiqMessage",
        result: "TaskiqResult[Any]",
        exception: BaseException,
    ) -> None:
        """Called when task execution fails with an error."""
        try:
            # Extract task info from message
            task_id = message.task_id
            task_name = message.task_name

            task_metadata = getattr(self, "_task_start_times", {}).get(
                task_id, {}
            )
            started_at = task_metadata.get("started_at", datetime.now(UTC))
            schedule_id = task_metadata.get("schedule_id")
            schedule_type = task_metadata.get("schedule_type")
            player_id = task_metadata.get("player_id")

            # Clean up
            if hasattr(self, "_task_start_times"):
                self._task_start_times.pop(task_id, None)

            # Extract task arguments from message
            task_args: Dict[str, Any] = {}
            if message.args:
                # For fetch_player_hiscores_task, first arg is username
                if (
                    "fetch_player_hiscores_task" in task_name
                    and message.args
                    and len(message.args) > 0
                ):
                    task_args["username"] = str(message.args[0])

            # Determine retry count from message labels if available
            retry_count = 0
            if message.labels:
                retry_count_str = message.labels.get("retry_count")
                if retry_count_str:
                    try:
                        retry_count = int(retry_count_str)
                    except (ValueError, TypeError):
                        pass

            # Convert BaseException to Exception for create_from_exception
            error = (
                exception
                if isinstance(exception, Exception)
                else Exception(str(exception))
            )

            try:
                async with AsyncSessionLocal() as db_session:
                    execution = TaskExecution.create_from_exception(
                        task_name=task_name,
                        exception=error,
                        task_args=task_args if task_args else None,
                        retry_count=retry_count,
                        schedule_id=schedule_id,
                        schedule_type=schedule_type,
                        player_id=player_id,
                        started_at=started_at,
                    )
                    db_session.add(execution)
                    await db_session.commit()

                    logger.debug(
                        f"Logged task error: {task_name} (id: {execution.id}, "
                        f"error: {error.__class__.__name__})"
                    )
            except Exception as e:
                # Don't let tracking errors break task execution
                logger.error(
                    f"Failed to log task error for {task_name}: {e}",
                    exc_info=True,
                )
        except Exception as e:
            # Don't let middleware errors break task execution
            logger.error(
                f"Error in on_error middleware: {e}",
                exc_info=True,
            )
