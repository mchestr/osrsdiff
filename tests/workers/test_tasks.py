"""Tests for basic TaskIQ tasks."""

import pytest
from datetime import datetime

from src.workers.tasks import health_check_task, retry_task, timeout_task


class TestBasicTasks:
    """Test basic TaskIQ tasks."""

    @pytest.mark.asyncio
    async def test_health_check_task(self):
        """Test health check task execution."""
        result = await health_check_task.original_func()
        
        assert result["status"] == "healthy"
        assert "timestamp" in result
        assert result["message"] == "TaskIQ worker is operational"
        
        # Verify timestamp is valid ISO format
        datetime.fromisoformat(result["timestamp"])

    @pytest.mark.asyncio
    async def test_retry_task_success(self):
        """Test retry task with successful execution."""
        result = await retry_task.original_func(should_fail=False)
        
        assert result["status"] == "success"
        assert "timestamp" in result
        assert result["message"] == "Retry test completed successfully"

    @pytest.mark.asyncio
    async def test_retry_task_failure(self):
        """Test retry task with failure."""
        with pytest.raises(RuntimeError, match="Task intentionally failed"):
            await retry_task.original_func(should_fail=True)

    @pytest.mark.asyncio
    async def test_timeout_task(self):
        """Test timeout task execution."""
        delay = 0.1  # Short delay for testing
        result = await timeout_task.original_func(delay_seconds=delay)
        
        assert result["status"] == "completed"
        assert "timestamp" in result
        assert result["delay_seconds"] == delay
        assert f"Task completed after {delay} seconds" in result["message"]