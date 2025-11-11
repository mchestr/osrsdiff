"""Tests for TaskExecution model."""

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task_execution import (
    TaskExecution,
    TaskExecutionStatus,
)


class TestTaskExecutionModel:
    """Test TaskExecution model functionality."""

    def test_task_execution_creation(self):
        """Test basic task execution model creation."""
        execution = TaskExecution(
            task_name="test_task",
            status=TaskExecutionStatus.SUCCESS,
            started_at=datetime.now(UTC),
        )

        assert execution.task_name == "test_task"
        assert execution.status == TaskExecutionStatus.SUCCESS
        assert execution.retry_count == 0
        assert execution.schedule_id is None
        assert execution.player_id is None

    def test_task_execution_repr(self):
        """Test task execution string representation."""
        execution = TaskExecution(
            id=1,
            task_name="test_task",
            status=TaskExecutionStatus.FAILURE,
            retry_count=2,
            started_at=datetime.now(UTC),
        )

        repr_str = repr(execution)
        assert "TaskExecution" in repr_str
        assert "test_task" in repr_str
        assert "failure" in repr_str.lower()
        assert "2" in repr_str

    def test_create_from_exception(self):
        """Test creating TaskExecution from an exception."""
        exception = ValueError("Test error message")
        started_at = datetime.now(UTC)

        execution = TaskExecution.create_from_exception(
            task_name="test_task",
            exception=exception,
            task_args={"username": "test_user"},
            retry_count=1,
            schedule_id="test_schedule_123",
            schedule_type="player_fetch",
            player_id=42,
            started_at=started_at,
            metadata={"extra": "data"},
        )

        assert execution.task_name == "test_task"
        assert execution.status == TaskExecutionStatus.FAILURE
        assert execution.retry_count == 1
        assert execution.schedule_id == "test_schedule_123"
        assert execution.schedule_type == "player_fetch"
        assert execution.player_id == 42
        assert execution.task_args == {"username": "test_user"}
        assert execution.error_type == "ValueError"
        assert execution.error_message == "Test error message"
        assert execution.error_traceback is not None
        assert "ValueError" in execution.error_traceback
        assert execution.execution_metadata == {"extra": "data"}
        assert execution.completed_at is not None
        assert execution.duration_seconds is not None
        assert execution.duration_seconds >= 0

    def test_create_from_exception_without_started_at(self):
        """Test creating TaskExecution from exception without started_at."""
        exception = RuntimeError("Runtime error")

        execution = TaskExecution.create_from_exception(
            task_name="test_task",
            exception=exception,
        )

        assert execution.task_name == "test_task"
        assert execution.status == TaskExecutionStatus.FAILURE
        assert execution.started_at is not None
        assert execution.completed_at is not None

    def test_create_from_result_success(self):
        """Test creating TaskExecution from a successful result."""
        started_at = datetime.now(UTC)
        result = {
            "status": "success",
            "username": "test_user",
            "player_id": 42,
            "duration_seconds": 1.5,
        }

        execution = TaskExecution.create_from_result(
            task_name="test_task",
            result=result,
            task_args={"username": "test_user"},
            schedule_id="test_schedule_123",
            player_id=42,
            started_at=started_at,
        )

        assert execution.task_name == "test_task"
        assert execution.status == TaskExecutionStatus.SUCCESS
        assert execution.task_args == {"username": "test_user"}
        assert execution.schedule_id == "test_schedule_123"
        assert execution.player_id == 42
        assert execution.result_data == result
        assert execution.duration_seconds == 1.5
        assert execution.error_type is None
        assert execution.error_message is None

    def test_create_from_result_warning(self):
        """Test creating TaskExecution from a warning result."""
        result = {
            "status": "warning",
            "message": "Player not found",
        }

        execution = TaskExecution.create_from_result(
            task_name="test_task",
            result=result,
        )

        assert execution.status == TaskExecutionStatus.WARNING
        assert execution.result_data == result

    def test_create_from_result_error(self):
        """Test creating TaskExecution from an error result."""
        result = {
            "status": "error",
            "error_type": "PlayerNotFoundError",
            "error": "Player not found in database",
        }

        execution = TaskExecution.create_from_result(
            task_name="test_task",
            result=result,
        )

        # Status "error" should map to WARNING (as per create_from_result logic)
        # since it's not a recognized TaskExecutionStatus enum value
        assert execution.status in (
            TaskExecutionStatus.FAILURE,
            TaskExecutionStatus.WARNING,
        )
        assert execution.error_type == "PlayerNotFoundError"
        assert execution.error_message == "Player not found in database"

    def test_create_from_result_unknown_status(self):
        """Test creating TaskExecution with unknown status defaults to warning."""
        result = {
            "status": "unknown_status",
        }

        execution = TaskExecution.create_from_result(
            task_name="test_task",
            result=result,
        )

        # Unknown status should default to WARNING
        assert execution.status == TaskExecutionStatus.WARNING

    def test_create_from_result_calculates_duration(self):
        """Test that duration is calculated if not provided in result."""
        started_at = datetime.now(UTC)
        result = {"status": "success"}

        execution = TaskExecution.create_from_result(
            task_name="test_task",
            result=result,
            started_at=started_at,
        )

        assert execution.duration_seconds is not None
        assert execution.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_task_execution_persistence(
        self, test_session: AsyncSession
    ):
        """Test that TaskExecution can be persisted to database."""
        execution = TaskExecution(
            task_name="test_task",
            status=TaskExecutionStatus.SUCCESS,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            duration_seconds=1.0,
            task_args={"username": "test_user"},
            schedule_id="test_schedule_123",
            player_id=42,
        )

        test_session.add(execution)
        await test_session.commit()
        await test_session.refresh(execution)

        assert execution.id is not None
        assert execution.task_name == "test_task"
        assert execution.status == TaskExecutionStatus.SUCCESS
        assert execution.player_id == 42

    @pytest.mark.asyncio
    async def test_task_execution_with_error_persistence(
        self, test_session: AsyncSession
    ):
        """Test that TaskExecution with error details can be persisted."""
        exception = ValueError("Test error")
        execution = TaskExecution.create_from_exception(
            task_name="test_task",
            exception=exception,
            started_at=datetime.now(UTC),
        )

        test_session.add(execution)
        await test_session.commit()
        await test_session.refresh(execution)

        assert execution.id is not None
        assert execution.status == TaskExecutionStatus.FAILURE
        assert execution.error_type == "ValueError"
        assert execution.error_message == "Test error"
        assert execution.error_traceback is not None
