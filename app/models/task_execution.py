"""Task execution tracking model for error tracking and debugging."""

from __future__ import annotations

import traceback
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, Optional

from sqlalchemy import JSON, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class TaskExecutionStatus(str, Enum):
    """Status of a task execution."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    WARNING = "warning"


class TaskExecution(Base):
    """
    Model for tracking task executions and errors.

    This model stores detailed information about every task execution,
    including successes, failures, retries, and errors. This enables
    debugging of why tasks may not have executed at scheduled times.
    """

    __tablename__ = "task_executions"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True)

    # Task identification
    task_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Name of the task function (e.g., 'fetch_player_hiscores_task')",
    )

    # Task arguments and context
    task_args: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="Task arguments as JSON (e.g., {'username': 'player1'})",
    )

    # Execution metadata
    status: Mapped[TaskExecutionStatus] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Execution status (success, failure, retry, etc.)",
    )

    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of retry attempts (0 for first attempt)",
    )

    schedule_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="TaskIQ schedule ID if this was a scheduled task",
    )

    schedule_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Type of schedule (e.g., 'player_fetch', 'maintenance')",
    )

    player_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        doc="Player ID if this task is related to a player",
    )

    # Execution timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="When the task execution started",
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the task execution completed",
    )

    duration_seconds: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        doc="Task execution duration in seconds",
    )

    # Error information
    error_type: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Type/class name of the error (e.g., 'RateLimitError')",
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Error message",
    )

    error_traceback: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Full error traceback for debugging",
    )

    # Result data
    result_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="Task result data as JSON (for successful executions)",
    )

    # Additional metadata
    execution_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="Additional execution metadata",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        doc="When this record was created",
    )

    def __init__(self, **kwargs: Any) -> None:
        """Initialize TaskExecution with proper defaults."""
        # Set defaults if not provided
        if "retry_count" not in kwargs:
            kwargs["retry_count"] = 0
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        """String representation of the task execution."""
        return (
            f"<TaskExecution(id={self.id}, task='{self.task_name}', "
            f"status='{self.status}', retry={self.retry_count})>"
        )

    @classmethod
    def create_from_exception(
        cls,
        task_name: str,
        exception: Exception,
        task_args: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
        schedule_id: Optional[str] = None,
        schedule_type: Optional[str] = None,
        player_id: Optional[int] = None,
        started_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TaskExecution:
        """
        Create a TaskExecution record from an exception.

        Args:
            task_name: Name of the task
            exception: The exception that occurred
            task_args: Task arguments
            retry_count: Number of retry attempts
            schedule_id: Schedule ID if applicable
            schedule_type: Schedule type if applicable
            player_id: Player ID if applicable
            started_at: When the task started
            metadata: Additional metadata

        Returns:
            TaskExecution instance
        """
        now = datetime.now(UTC)
        completed_at = now
        duration = None
        if started_at:
            duration = (completed_at - started_at).total_seconds()

        return cls(
            task_name=task_name,
            task_args=task_args,
            status=TaskExecutionStatus.FAILURE,
            retry_count=retry_count,
            schedule_id=schedule_id,
            schedule_type=schedule_type,
            player_id=player_id,
            started_at=started_at or now,
            completed_at=completed_at,
            duration_seconds=duration,
            error_type=type(exception).__name__,
            error_message=str(exception),
            error_traceback="".join(
                traceback.format_exception(
                    type(exception), exception, exception.__traceback__
                )
            ),
            execution_metadata=metadata,
        )

    @classmethod
    def create_from_result(
        cls,
        task_name: str,
        result: Dict[str, Any],
        task_args: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
        schedule_id: Optional[str] = None,
        schedule_type: Optional[str] = None,
        player_id: Optional[int] = None,
        started_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TaskExecution:
        """
        Create a TaskExecution record from a task result.

        Args:
            task_name: Name of the task
            result: Task result dictionary
            task_args: Task arguments
            retry_count: Number of retry attempts
            schedule_id: Schedule ID if applicable
            schedule_type: Schedule type if applicable
            player_id: Player ID if applicable
            started_at: When the task started
            metadata: Additional metadata

        Returns:
            TaskExecution instance
        """
        now = datetime.now(UTC)
        status_str = result.get("status", "success")
        try:
            status = TaskExecutionStatus(status_str)
        except ValueError:
            # Handle unknown status values
            status = (
                TaskExecutionStatus.SUCCESS
                if status_str == "success"
                else TaskExecutionStatus.WARNING
            )

        completed_at = now
        duration = result.get("duration_seconds")
        if started_at and not duration:
            duration = (completed_at - started_at).total_seconds()

        # Extract error information from result if present
        error_type = result.get("error_type")
        error_message = result.get("error") or result.get("message")

        return cls(
            task_name=task_name,
            task_args=task_args,
            status=status,
            retry_count=retry_count,
            schedule_id=schedule_id,
            schedule_type=schedule_type,
            player_id=player_id,
            started_at=started_at or now,
            completed_at=completed_at,
            duration_seconds=duration,
            error_type=error_type,
            error_message=error_message,
            result_data=result,
            execution_metadata=metadata,
        )
