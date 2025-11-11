"""Tests for TaskExecutionTrackingMiddleware."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task_execution import TaskExecution, TaskExecutionStatus
from app.workers.middleware import TaskExecutionTrackingMiddleware


class TestTaskExecutionTrackingMiddleware:
    """Test TaskExecutionTrackingMiddleware functionality."""

    @pytest.fixture
    def middleware(self):
        """Create a middleware instance."""
        return TaskExecutionTrackingMiddleware()

    @pytest.fixture
    def mock_message(self):
        """Create a mock message with labels."""
        message = MagicMock()
        message.task_id = "test_task_123"
        message.task_name = "app.workers.fetch.fetch_player_hiscores_task"
        message.labels = {
            "schedule_id": "test_schedule_123",
            "schedule_type": "player_fetch",
            "player_id": "42",
            "retry_count": "0",
        }
        message.args = ["test_user"]
        return message

    @pytest.fixture
    def mock_result(self):
        """Create a mock TaskiqResult."""
        result = MagicMock()
        result.return_value = {
            "status": "success",
            "username": "test_user",
            "player_id": 42,
            "duration_seconds": 1.5,
        }
        return result

    @pytest.mark.asyncio
    async def test_pre_execute_stores_metadata(self, middleware, mock_message):
        """Test that pre_execute stores task metadata."""
        result = await middleware.pre_execute(mock_message)

        # Should return the message
        assert result == mock_message

        # Should store metadata
        assert hasattr(middleware, "_task_start_times")
        assert mock_message.task_id in middleware._task_start_times

        metadata = middleware._task_start_times[mock_message.task_id]
        assert metadata["schedule_id"] == "test_schedule_123"
        assert metadata["schedule_type"] == "player_fetch"
        assert metadata["player_id"] == 42
        assert "started_at" in metadata

    @pytest.mark.asyncio
    async def test_pre_execute_without_labels(self, middleware):
        """Test pre_execute with message without labels."""
        message = MagicMock()
        message.task_id = "test_id"
        message.task_name = "test_task"
        message.labels = {}

        result = await middleware.pre_execute(message)

        assert result == message
        assert hasattr(middleware, "_task_start_times")
        assert "test_id" in middleware._task_start_times

    @pytest.mark.asyncio
    async def test_pre_execute_handles_errors(self, middleware):
        """Test that pre_execute handles errors gracefully."""
        # Create a message that will cause an error
        message = MagicMock()
        message.task_id = "test_id"
        message.task_name = "test_task"
        message.labels = None

        result = await middleware.pre_execute(message)

        # Should still return message even if there's an error
        assert result == message

    @pytest.mark.asyncio
    async def test_post_execute_logs_success(
        self, middleware, mock_message, mock_result, test_session: AsyncSession
    ):
        """Test that post_execute logs successful task execution."""
        # Set up metadata from pre_execute
        middleware._task_start_times = {
            mock_message.task_id: {
                "started_at": datetime.now(UTC),
                "schedule_id": "test_schedule_123",
                "schedule_type": "player_fetch",
                "player_id": 42,
            }
        }

        with patch(
            "app.workers.middleware.AsyncSessionLocal",
            return_value=test_session,
        ):
            await middleware.post_execute(mock_message, mock_result)

        # Should have logged execution
        await test_session.commit()
        from sqlalchemy import select

        stmt = select(TaskExecution).where(
            TaskExecution.task_name == mock_message.task_name
        )
        result_query = await test_session.execute(stmt)
        execution = result_query.scalar_one_or_none()

        assert execution is not None
        assert execution.status == TaskExecutionStatus.SUCCESS
        assert execution.task_args == {"username": "test_user"}
        assert execution.schedule_id == "test_schedule_123"
        assert execution.player_id == 42
        assert execution.result_data == mock_result.return_value

        # Should clean up metadata
        assert mock_message.task_id not in middleware._task_start_times

    @pytest.mark.asyncio
    async def test_post_execute_handles_db_errors(
        self, middleware, mock_message
    ):
        """Test that post_execute handles database errors gracefully."""
        mock_message.task_id = "test_task_123"
        mock_message.task_name = "test_task"
        mock_message.args = []

        middleware._task_start_times = {
            mock_message.task_id: {"started_at": datetime.now(UTC)}
        }

        result = MagicMock()
        result.return_value = {"status": "success"}

        # Mock database error
        with patch(
            "app.workers.middleware.AsyncSessionLocal",
            side_effect=Exception("DB error"),
        ):
            # Should not raise, just log error
            await middleware.post_execute(mock_message, result)

    @pytest.mark.asyncio
    async def test_on_error_logs_failure(
        self, middleware, mock_message, test_session: AsyncSession
    ):
        """Test that on_error logs failed task execution."""
        error = ValueError("Test error message")

        # Set up metadata from pre_execute
        middleware._task_start_times = {
            mock_message.task_id: {
                "started_at": datetime.now(UTC),
                "schedule_id": "test_schedule_123",
                "player_id": 42,
            }
        }

        result = MagicMock()
        result.return_value = None

        with patch(
            "app.workers.middleware.AsyncSessionLocal",
            return_value=test_session,
        ):
            await middleware.on_error(mock_message, result, error)

        # Should have logged execution
        await test_session.commit()
        from sqlalchemy import select

        stmt = select(TaskExecution).where(
            TaskExecution.task_name == mock_message.task_name
        )
        result_query = await test_session.execute(stmt)
        execution = result_query.scalar_one_or_none()

        assert execution is not None
        assert execution.status == TaskExecutionStatus.FAILURE
        assert execution.error_type == "ValueError"
        assert execution.error_message == "Test error message"
        assert execution.error_traceback is not None
        assert execution.task_args == {"username": "test_user"}

        # Should clean up metadata
        assert mock_message.task_id not in middleware._task_start_times

    @pytest.mark.asyncio
    async def test_on_error_handles_db_errors(self, middleware, mock_message):
        """Test that on_error handles database errors gracefully."""
        mock_message.task_id = "test_task_123"
        mock_message.task_name = "test_task"
        mock_message.args = []

        error = RuntimeError("Test error")

        middleware._task_start_times = {
            mock_message.task_id: {"started_at": datetime.now(UTC)}
        }

        result = MagicMock()
        result.return_value = None

        # Mock database error
        with patch(
            "app.workers.middleware.AsyncSessionLocal",
            side_effect=Exception("DB error"),
        ):
            # Should not raise, just log error
            await middleware.on_error(mock_message, result, error)

    @pytest.mark.asyncio
    async def test_post_execute_extracts_task_args(
        self, middleware, test_session
    ):
        """Test that post_execute extracts task arguments correctly."""
        message = MagicMock()
        message.task_id = "test_task_123"
        message.task_name = "app.workers.fetch.fetch_player_hiscores_task"
        message.labels = {}
        message.args = ["test_user"]

        middleware._task_start_times = {
            message.task_id: {"started_at": datetime.now(UTC)}
        }

        result = MagicMock()
        result.return_value = {"status": "success"}

        with patch(
            "app.workers.middleware.AsyncSessionLocal",
            return_value=test_session,
        ):
            await middleware.post_execute(message, result)

        await test_session.commit()
        from sqlalchemy import select

        stmt = select(TaskExecution).where(
            TaskExecution.task_name == message.task_name
        )
        result_query = await test_session.execute(stmt)
        execution = result_query.scalar_one_or_none()

        assert execution is not None
        assert execution.task_args == {"username": "test_user"}

    @pytest.mark.asyncio
    async def test_post_execute_with_retry_count(
        self, middleware, test_session: AsyncSession
    ):
        """Test that post_execute captures retry count."""
        message = MagicMock()
        message.task_id = "test_task_123"
        message.task_name = "test_task"
        message.labels = {"retry_count": "3"}
        message.args = []

        middleware._task_start_times = {
            message.task_id: {"started_at": datetime.now(UTC)}
        }

        result = MagicMock()
        result.return_value = {"status": "success"}

        with patch(
            "app.workers.middleware.AsyncSessionLocal",
            return_value=test_session,
        ):
            await middleware.post_execute(message, result)

        await test_session.commit()
        from sqlalchemy import select

        stmt = select(TaskExecution).where(
            TaskExecution.task_name == message.task_name
        )
        result_query = await test_session.execute(stmt)
        execution = result_query.scalar_one_or_none()

        assert execution is not None
        assert execution.retry_count == 3

    @pytest.mark.asyncio
    async def test_post_execute_with_non_dict_result(
        self, middleware, test_session: AsyncSession
    ):
        """Test that post_execute handles non-dict results."""
        message = MagicMock()
        message.task_id = "test_task_123"
        message.task_name = "test_task"
        message.labels = {}
        message.args = []

        middleware._task_start_times = {
            message.task_id: {"started_at": datetime.now(UTC)}
        }

        result = MagicMock()
        result.return_value = "simple string result"

        with patch(
            "app.workers.middleware.AsyncSessionLocal",
            return_value=test_session,
        ):
            await middleware.post_execute(message, result)

        await test_session.commit()
        from sqlalchemy import select

        stmt = select(TaskExecution).where(
            TaskExecution.task_name == message.task_name
        )
        result_query = await test_session.execute(stmt)
        execution = result_query.scalar_one_or_none()

        assert execution is not None
        assert execution.result_data == {"result": "simple string result"}
