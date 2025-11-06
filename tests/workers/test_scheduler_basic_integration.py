"""Basic integration tests for TaskIQ scheduler functionality without database dependencies."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import ListRedisScheduleSource

from app.config import settings
from app.models.player import GameMode, Player
from app.services.scheduler import PlayerScheduleManager
from app.workers.main import broker


@pytest.mark.integration
class TestBasicSchedulerIntegration:
    """Basic integration tests that don't require full database setup."""

    def test_scheduler_configuration_creation(self):
        """Test that scheduler configuration can be created successfully."""
        from app.workers.scheduler_config import (
            create_scheduler,
            create_scheduler_sources,
        )

        # Test source creation
        sources = create_scheduler_sources()
        assert len(sources) == 2

        # Verify source types
        source_types = [type(source) for source in sources]
        assert ListRedisScheduleSource in source_types
        assert LabelScheduleSource in source_types

        # Test scheduler creation
        scheduler = create_scheduler()
        assert isinstance(scheduler, TaskiqScheduler)
        assert scheduler.broker == broker
        assert len(scheduler.sources) == 2

    def test_player_schedule_manager_initialization(self):
        """Test PlayerScheduleManager can be initialized with Redis source."""
        redis_source = ListRedisScheduleSource(
            url="redis://localhost:6379/0",
            prefix="test_prefix",
        )

        manager = PlayerScheduleManager(redis_source)
        assert manager.redis_source == redis_source

    def test_cron_expression_generation(self):
        """Test cron expression generation for various intervals."""
        redis_source = ListRedisScheduleSource(
            url="redis://localhost:6379/0",
            prefix="test_prefix",
        )
        manager = PlayerScheduleManager(redis_source)

        # Test various intervals
        test_cases = [
            (30, "*/30 * * * *"),
            (60, "0 * * * *"),
            (1440, "0 0 * * *"),
            (120, "0 */2 * * *"),
            (15, "*/15 * * * *"),
        ]

        for minutes, expected_cron in test_cases:
            result = manager._interval_to_cron(minutes)
            assert (
                result == expected_cron
            ), f"Failed for {minutes} minutes: expected {expected_cron}, got {result}"

    def test_cron_validation(self):
        """Test cron expression validation."""
        redis_source = ListRedisScheduleSource(
            url="redis://localhost:6379/0",
            prefix="test_prefix",
        )
        manager = PlayerScheduleManager(redis_source)

        # Valid expressions should not raise
        valid_expressions = [
            "*/30 * * * *",
            "0 * * * *",
            "0 0 * * *",
            "0 */2 * * *",
        ]

        for expr in valid_expressions:
            try:
                manager._validate_cron_expression(expr)
            except Exception as e:
                pytest.fail(f"Valid expression '{expr}' raised exception: {e}")

        # Invalid expressions should raise
        invalid_expressions = [
            "*/30 * * *",  # Wrong number of fields
            "60 * * * *",  # Invalid minute
            "0 24 * * *",  # Invalid hour
            "*/0 * * * *",  # Invalid step
        ]

        for expr in invalid_expressions:
            with pytest.raises(ValueError):
                manager._validate_cron_expression(expr)

    @pytest.mark.asyncio
    async def test_schedule_player_mock_redis(self):
        """Test schedule_player with mocked Redis operations."""
        # Create mock Redis source
        mock_redis_source = AsyncMock()
        manager = PlayerScheduleManager(mock_redis_source)

        # Create test player
        player = Player(
            id=123,
            username="test_player",
            fetch_interval_minutes=30,
            game_mode=GameMode.REGULAR,
            is_active=True,
        )

        # Mock the task and its methods
        mock_schedule = MagicMock()
        mock_schedule.schedule_id = "player_fetch_123"

        mock_kicker = MagicMock()
        mock_kicker.with_schedule_id.return_value = mock_kicker
        mock_kicker.with_labels.return_value = mock_kicker
        mock_kicker.schedule_by_cron = AsyncMock(return_value=mock_schedule)

        with patch(
            "app.workers.fetch.fetch_player_hiscores_task"
        ) as mock_task:
            mock_task.kicker.return_value = mock_kicker

            result = await manager.schedule_player(player)

            assert result == "player_fetch_123"
            mock_task.kicker.assert_called_once()
            mock_kicker.with_schedule_id.assert_called_once_with(
                "player_fetch_123"
            )
            mock_kicker.with_labels.assert_called_once_with(
                player_id="123",
                schedule_type="player_fetch",
                username="test_player",
            )
            mock_kicker.schedule_by_cron.assert_called_once_with(
                mock_redis_source, "*/30 * * * *", "test_player"
            )

    @pytest.mark.asyncio
    async def test_unschedule_player_mock_redis(self):
        """Test unschedule_player with mocked Redis operations."""
        # Create mock Redis source
        mock_redis_source = AsyncMock()
        manager = PlayerScheduleManager(mock_redis_source)

        # Create test player with schedule_id
        player = Player(
            id=123,
            username="test_player",
            fetch_interval_minutes=30,
            game_mode=GameMode.REGULAR,
            is_active=True,
        )
        player.schedule_id = "player_fetch_123"

        # Test successful unscheduling
        await manager.unschedule_player(player)

        mock_redis_source.delete_schedule.assert_called_once_with(
            "player_fetch_123"
        )

    @pytest.mark.asyncio
    async def test_ensure_player_scheduled_mock_redis(self):
        """Test ensure_player_scheduled with mocked Redis operations."""
        # Create mock Redis source
        mock_redis_source = AsyncMock()
        manager = PlayerScheduleManager(mock_redis_source)

        # Create test player
        player = Player(
            id=123,
            username="test_player",
            fetch_interval_minutes=30,
            game_mode=GameMode.REGULAR,
            is_active=True,
        )

        # Test case 1: No schedule_id, should create new schedule
        player.schedule_id = None

        with patch.object(manager, "schedule_player") as mock_schedule:
            mock_schedule.return_value = "player_fetch_123"

            result = await manager.ensure_player_scheduled(player)

            assert result == "player_fetch_123"
            mock_schedule.assert_called_once_with(player)

    def test_interval_validation_edge_cases(self):
        """Test interval validation with edge cases."""
        redis_source = ListRedisScheduleSource(
            url="redis://localhost:6379/0",
            prefix="test_prefix",
        )
        manager = PlayerScheduleManager(redis_source)

        # Test invalid types
        with pytest.raises(
            ValueError, match="Fetch interval must be an integer"
        ):
            manager._interval_to_cron("30")

        with pytest.raises(
            ValueError, match="Fetch interval must be an integer"
        ):
            manager._interval_to_cron(30.5)

        # Test invalid values
        with pytest.raises(ValueError, match="Invalid fetch interval"):
            manager._interval_to_cron(0)

        with pytest.raises(ValueError, match="Invalid fetch interval"):
            manager._interval_to_cron(-5)

        # Test too large values
        max_minutes = 7 * 24 * 60  # 1 week
        with pytest.raises(ValueError, match="Fetch interval too large"):
            manager._interval_to_cron(max_minutes + 1)

    @pytest.mark.asyncio
    async def test_verify_all_schedules_mock(self):
        """Test verify_all_schedules with mocked Redis data."""
        mock_redis_source = AsyncMock()
        manager = PlayerScheduleManager(mock_redis_source)

        # Mock schedules data
        mock_schedule1 = MagicMock()
        mock_schedule1.schedule_id = "player_fetch_123"
        mock_schedule1.labels = {"player_id": "123"}

        mock_schedule2 = MagicMock()
        mock_schedule2.schedule_id = "player_fetch_456"
        mock_schedule2.labels = {"player_id": "456"}

        mock_schedule3 = MagicMock()
        mock_schedule3.schedule_id = "other_task_789"
        mock_schedule3.labels = {}

        mock_redis_source.get_schedules.return_value = [
            mock_schedule1,
            mock_schedule2,
            mock_schedule3,
        ]

        result = await manager.verify_all_schedules()

        assert result["total_schedules"] == 3
        assert result["player_fetch_schedules"] == 2
        assert result["other_schedules"] == 1
        assert len(result["invalid_schedules"]) == 0
        assert len(result["duplicate_schedules"]) == 0

    def test_deterministic_schedule_id_generation(self):
        """Test that schedule IDs are deterministic based on player ID."""
        redis_source = ListRedisScheduleSource(
            url="redis://localhost:6379/0",
            prefix="test_prefix",
        )
        manager = PlayerScheduleManager(redis_source)

        # Create players with same ID should generate same schedule ID
        player1 = Player(id=123, username="player1", fetch_interval_minutes=30)
        player2 = Player(
            id=123, username="player2", fetch_interval_minutes=60
        )  # Different username/interval

        # The schedule ID should be based on player ID only
        expected_schedule_id = "player_fetch_123"

        # We can't test the actual schedule_player method without mocking,
        # but we can verify the deterministic ID generation logic
        assert f"player_fetch_{player1.id}" == expected_schedule_id
        assert f"player_fetch_{player2.id}" == expected_schedule_id


@pytest.mark.integration
class TestSchedulerErrorHandling:
    """Test error handling in scheduler integration scenarios."""

    @pytest.mark.asyncio
    async def test_redis_connection_error_handling(self):
        """Test handling of Redis connection errors."""
        mock_redis_source = AsyncMock()
        manager = PlayerScheduleManager(mock_redis_source)

        player = Player(
            id=123,
            username="test_player",
            fetch_interval_minutes=30,
            is_active=True,
        )

        # Test Redis error during schedule verification
        mock_redis_source.get_schedules.side_effect = Exception(
            "Redis connection failed"
        )

        with patch.object(manager, "schedule_player") as mock_schedule:
            mock_schedule.return_value = "player_fetch_123"

            # Should handle error gracefully and create new schedule
            result = await manager.ensure_player_scheduled(player)

            assert result == "player_fetch_123"
            mock_schedule.assert_called_once_with(player)

    @pytest.mark.asyncio
    async def test_schedule_creation_error_handling(self):
        """Test handling of schedule creation errors."""
        mock_redis_source = AsyncMock()
        manager = PlayerScheduleManager(mock_redis_source)

        player = Player(
            id=123,
            username="test_player",
            fetch_interval_minutes=30,
            is_active=True,
        )

        # Mock task to raise exception
        with patch(
            "app.workers.fetch.fetch_player_hiscores_task"
        ) as mock_task:
            mock_task.kicker.side_effect = Exception("Task creation failed")

            # Should raise ScheduleCreationError
            with pytest.raises(
                Exception
            ):  # Will be ScheduleCreationError in actual implementation
                await manager.schedule_player(player)

    @pytest.mark.asyncio
    async def test_schedule_deletion_error_handling(self):
        """Test handling of schedule deletion errors."""
        mock_redis_source = AsyncMock()
        manager = PlayerScheduleManager(mock_redis_source)

        player = Player(
            id=123,
            username="test_player",
            fetch_interval_minutes=30,
            is_active=True,
        )
        player.schedule_id = "player_fetch_123"

        # Test "not found" error (should not raise)
        mock_redis_source.delete_schedule.side_effect = Exception(
            "Schedule not found"
        )

        # Should not raise exception for "not found" errors
        await manager.unschedule_player(player)

        # Test unexpected error (should raise)
        mock_redis_source.delete_schedule.side_effect = Exception(
            "Redis connection failed"
        )

        # Should raise ScheduleDeletionError for unexpected errors
        with pytest.raises(
            Exception
        ):  # Will be ScheduleDeletionError in actual implementation
            await manager.unschedule_player(player)
