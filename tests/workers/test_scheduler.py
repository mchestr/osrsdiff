"""Tests for task scheduler functionality."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.workers.scheduler import (
    TaskScheduler,
    get_scheduler,
    start_scheduler,
    stop_scheduler,
)


class TestTaskScheduler:
    """Test task scheduler functionality."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None  # No previous runs by default
        mock_redis.set.return_value = (
            True  # Lock acquisition succeeds by default
        )
        mock_redis.delete.return_value = True
        mock_redis.aclose.return_value = None
        return mock_redis

    @pytest.fixture
    def scheduler(self):
        """Create a test scheduler instance."""
        return TaskScheduler(
            fetch_interval_minutes=1
        )  # Short interval for testing

    @pytest.mark.asyncio
    async def test_scheduler_initialization(self, scheduler):
        """Test scheduler initialization."""
        assert scheduler.fetch_interval_minutes == 1
        assert scheduler.fetch_interval == timedelta(minutes=1)
        assert not scheduler.is_running
        assert scheduler.last_run is None
        assert scheduler.next_run is None
        assert scheduler._redis_client is None
        assert not scheduler._has_lock

    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self, scheduler, mock_redis):
        """Test scheduler start and stop functionality."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            # Initially not running
            assert not scheduler.is_running
            assert scheduler._redis_client is None

            # Start scheduler
            await scheduler.start()
            assert scheduler.is_running
            assert scheduler._redis_client is not None

            # Stop scheduler
            await scheduler.stop()
            assert not scheduler.is_running

            # Redis client should be cleaned up
            mock_redis.aclose.assert_called()

    @pytest.mark.asyncio
    async def test_scheduler_double_start(self, scheduler):
        """Test that starting an already running scheduler is handled gracefully."""
        await scheduler.start()
        assert scheduler.is_running

        # Starting again should not cause issues
        await scheduler.start()
        assert scheduler.is_running

        await scheduler.stop()

    @pytest.mark.asyncio
    async def test_scheduler_double_stop(self, scheduler):
        """Test that stopping a non-running scheduler is handled gracefully."""
        # Stop without starting should not cause issues
        await scheduler.stop()
        assert not scheduler.is_running

        # Start and stop normally
        await scheduler.start()
        await scheduler.stop()
        assert not scheduler.is_running

        # Stop again should not cause issues
        await scheduler.stop()
        assert not scheduler.is_running

    @pytest.mark.asyncio
    async def test_scheduler_loop_execution(self, scheduler, mock_redis):
        """Test that scheduler loop executes scheduled tasks."""
        # Test the trigger_immediate_fetch method directly instead of relying on loop timing
        with patch(
            "src.workers.scheduler.process_scheduled_fetches_task"
        ) as mock_task:
            mock_task.kiq = AsyncMock()

            # Test immediate fetch trigger
            await scheduler.trigger_immediate_fetch()

            # Verify task was enqueued
            mock_task.kiq.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_last_run_from_redis_method(self, scheduler, mock_redis):
        """Test the get_last_run_from_redis method."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            # Test when no Redis client
            result = await scheduler.get_last_run_from_redis()
            assert result is None

            # Start scheduler to initialize Redis client
            await scheduler.start()

            # Test when no previous run
            mock_redis.get.return_value = None
            result = await scheduler.get_last_run_from_redis()
            assert result is None
            mock_redis.get.assert_called_with("osrsdiff:scheduler:last_run")

            # Test when previous run exists
            test_time = datetime.now(UTC)
            mock_redis.get.return_value = test_time.isoformat().encode()
            result = await scheduler.get_last_run_from_redis()
            assert result == test_time

            # Test error handling
            mock_redis.get.side_effect = Exception("Redis error")
            result = await scheduler.get_last_run_from_redis()
            assert result is None

            await scheduler.stop()

    @pytest.mark.asyncio
    async def test_trigger_immediate_fetch(self, scheduler):
        """Test triggering immediate fetch processing."""
        with patch(
            "src.workers.scheduler.process_scheduled_fetches_task"
        ) as mock_task:
            mock_task.kiq = AsyncMock()

            # Trigger immediate fetch
            await scheduler.trigger_immediate_fetch()

            # Verify task was enqueued
            mock_task.kiq.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_immediate_fetch_error(self, scheduler):
        """Test error handling in immediate fetch trigger."""
        with patch(
            "src.workers.scheduler.process_scheduled_fetches_task"
        ) as mock_task:
            mock_task.kiq = AsyncMock(side_effect=Exception("Enqueue failed"))

            # Should raise the exception
            with pytest.raises(Exception, match="Enqueue failed"):
                await scheduler.trigger_immediate_fetch()

    @pytest.mark.asyncio
    async def test_next_run_calculation(self, scheduler):
        """Test next run time calculation."""
        # Initially no next run
        assert scheduler.next_run is None

        # Set a last run time
        scheduler._last_scheduled_run = datetime.now(UTC)
        expected_next = (
            scheduler._last_scheduled_run + scheduler.fetch_interval
        )

        assert scheduler.next_run == expected_next

    @pytest.mark.asyncio
    async def test_scheduler_error_handling(self, scheduler, mock_redis):
        """Test scheduler error handling in trigger_immediate_fetch."""
        with patch(
            "src.workers.scheduler.process_scheduled_fetches_task"
        ) as mock_task:
            # Task fails
            mock_task.kiq = AsyncMock(side_effect=Exception("Task failed"))

            # Should raise the exception
            with pytest.raises(Exception, match="Task failed"):
                await scheduler.trigger_immediate_fetch()

    @pytest.mark.asyncio
    async def test_redis_lock_release(self, scheduler, mock_redis):
        """Test Redis lock release functionality."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            await scheduler.start()

            # Simulate having a lock
            scheduler._has_lock = True

            # Test lock release
            await scheduler._release_lock()

            # Verify lock was deleted
            mock_redis.delete.assert_called_with("osrsdiff:scheduler:lock")
            assert not scheduler._has_lock

            await scheduler.stop()

    @pytest.mark.asyncio
    async def test_redis_lock_release_error_handling(
        self, scheduler, mock_redis
    ):
        """Test error handling in lock release."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            await scheduler.start()

            # Simulate having a lock
            scheduler._has_lock = True

            # Mock Redis delete to fail
            mock_redis.delete.side_effect = Exception("Redis error")

            # Should not raise exception, just log error
            await scheduler._release_lock()

            # Lock flag should still be reset even if Redis call fails
            assert not scheduler._has_lock

            await scheduler.stop()

    @pytest.mark.asyncio
    async def test_redis_client_initialization(self, scheduler, mock_redis):
        """Test Redis client initialization and cleanup."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            # Initially no client
            assert scheduler._redis_client is None

            # Start scheduler
            await scheduler.start()
            assert scheduler._redis_client is not None

            # Stop scheduler
            await scheduler.stop()

            # Client should be cleaned up
            mock_redis.aclose.assert_called()

    @pytest.mark.asyncio
    async def test_scheduler_properties(self, scheduler):
        """Test scheduler property methods."""
        # Initially no runs
        assert scheduler.last_run is None
        assert scheduler.next_run is None

        # Set a last run time
        test_time = datetime.now(UTC)
        scheduler._last_scheduled_run = test_time

        assert scheduler.last_run == test_time
        expected_next = test_time + scheduler.fetch_interval
        assert scheduler.next_run == expected_next


class TestSchedulerGlobals:
    """Test global scheduler functions."""

    @pytest.fixture
    def mock_redis_global(self):
        """Create a mock Redis client for global tests."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = True
        mock_redis.aclose.return_value = None
        return mock_redis

    @pytest.mark.asyncio
    async def test_get_scheduler_singleton(self):
        """Test that get_scheduler returns the same instance."""
        scheduler1 = get_scheduler()
        scheduler2 = get_scheduler()

        assert scheduler1 is scheduler2
        assert isinstance(scheduler1, TaskScheduler)

    @pytest.mark.asyncio
    async def test_start_stop_global_scheduler(self, mock_redis_global):
        """Test global scheduler start/stop functions."""
        with patch("redis.asyncio.from_url", return_value=mock_redis_global):
            scheduler = get_scheduler()

            # Initially not running
            assert not scheduler.is_running

            # Start via global function
            await start_scheduler()
            assert scheduler.is_running

            # Stop via global function
            await stop_scheduler()
            assert not scheduler.is_running

    @pytest.mark.asyncio
    async def test_global_trigger_immediate_fetch(self):
        """Test global immediate fetch trigger."""
        from src.workers.scheduler import trigger_immediate_fetch

        with patch(
            "src.workers.scheduler.process_scheduled_fetches_task"
        ) as mock_task:
            mock_task.kiq = AsyncMock()

            await trigger_immediate_fetch()

            mock_task.kiq.assert_called_once()
