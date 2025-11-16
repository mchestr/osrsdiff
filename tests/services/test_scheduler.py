"""Tests for PlayerScheduleManager service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.player import Player
from app.services.scheduler import (
    PlayerScheduleManager,
    ScheduleCreationError,
    ScheduleDeletionError,
)


class TestPlayerScheduleManager:
    """Test cases for PlayerScheduleManager."""

    @pytest.fixture
    def mock_redis_source(self):
        """Create a mock Redis schedule source."""
        mock_source = AsyncMock()
        return mock_source

    @pytest.fixture
    def schedule_manager(self, mock_redis_source):
        """Create a PlayerScheduleManager instance with mocked dependencies."""
        return PlayerScheduleManager(mock_redis_source)

    @pytest.fixture
    def sample_player(self):
        """Create a sample player for testing."""
        return Player(
            id=123,
            username="test_player",
            fetch_interval_minutes=30,
            is_active=True,
        )

    def test_interval_to_cron_sub_hourly(self, schedule_manager):
        """Test cron conversion for sub-hourly intervals."""
        assert schedule_manager._interval_to_cron(30) == "*/30 * * * *"
        assert schedule_manager._interval_to_cron(15) == "*/15 * * * *"
        assert schedule_manager._interval_to_cron(5) == "*/5 * * * *"

    def test_interval_to_cron_hourly(self, schedule_manager):
        """Test cron conversion for hourly interval."""
        assert schedule_manager._interval_to_cron(60) == "0 * * * *"

    def test_interval_to_cron_daily(self, schedule_manager):
        """Test cron conversion for daily interval."""
        assert schedule_manager._interval_to_cron(1440) == "0 0 * * *"

    def test_interval_to_cron_multi_hour(self, schedule_manager):
        """Test cron conversion for multi-hour intervals."""
        assert (
            schedule_manager._interval_to_cron(120) == "0 */2 * * *"
        )  # 2 hours
        assert (
            schedule_manager._interval_to_cron(360) == "0 */6 * * *"
        )  # 6 hours

    def test_interval_to_cron_invalid(self, schedule_manager):
        """Test cron conversion with invalid interval."""
        with pytest.raises(ValueError, match="Invalid fetch interval"):
            schedule_manager._interval_to_cron(0)

        with pytest.raises(ValueError, match="Invalid fetch interval"):
            schedule_manager._interval_to_cron(-5)

    def test_interval_to_cron_type_validation(self, schedule_manager):
        """Test cron conversion with invalid types."""
        with pytest.raises(
            ValueError, match="Fetch interval must be an integer"
        ):
            schedule_manager._interval_to_cron("30")

        with pytest.raises(
            ValueError, match="Fetch interval must be an integer"
        ):
            schedule_manager._interval_to_cron(30.5)

    def test_interval_to_cron_too_large(self, schedule_manager):
        """Test cron conversion with excessively large interval."""
        max_minutes = 7 * 24 * 60  # 1 week
        with pytest.raises(ValueError, match="Fetch interval too large"):
            schedule_manager._interval_to_cron(max_minutes + 1)

    def test_interval_to_cron_multi_day(self, schedule_manager):
        """Test cron conversion for multi-day intervals."""
        # 2 days
        assert schedule_manager._interval_to_cron(2880) == "0 0 */2 * *"
        # 3 days
        assert schedule_manager._interval_to_cron(4320) == "0 0 */3 * *"

    def test_interval_to_cron_edge_cases(self, schedule_manager):
        """Test cron conversion for edge cases."""
        # 24 hours (should be daily)
        assert schedule_manager._interval_to_cron(1440) == "0 0 * * *"
        # 12 hours
        assert schedule_manager._interval_to_cron(720) == "0 */12 * * *"
        # 90 minutes (non-standard)
        assert schedule_manager._interval_to_cron(90) == "*/90 * * * *"

    def test_validate_cron_expression_valid(self, schedule_manager):
        """Test cron expression validation with valid expressions."""
        # These should not raise exceptions
        schedule_manager._validate_cron_expression("*/30 * * * *")
        schedule_manager._validate_cron_expression("0 * * * *")
        schedule_manager._validate_cron_expression("0 0 * * *")
        schedule_manager._validate_cron_expression("0 */2 * * *")

    def test_validate_cron_expression_invalid(self, schedule_manager):
        """Test cron expression validation with invalid expressions."""
        # Wrong number of fields
        with pytest.raises(ValueError, match="must have exactly 5 fields"):
            schedule_manager._validate_cron_expression("*/30 * * *")

        # Invalid minute value
        with pytest.raises(ValueError, match="Invalid minute value"):
            schedule_manager._validate_cron_expression("60 * * * *")

        # Invalid hour value
        with pytest.raises(ValueError, match="Invalid hour value"):
            schedule_manager._validate_cron_expression("0 24 * * *")

        # Invalid step value
        with pytest.raises(ValueError, match="Invalid minute step value"):
            schedule_manager._validate_cron_expression("*/0 * * * *")

    @pytest.mark.asyncio
    async def test_schedule_player_success(
        self, schedule_manager, mock_redis_source, sample_player
    ):
        """Test successful player scheduling."""
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

            result = await schedule_manager.schedule_player(sample_player)

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
    async def test_schedule_player_failure(
        self, schedule_manager, mock_redis_source, sample_player
    ):
        """Test player scheduling failure."""
        with patch(
            "app.workers.fetch.fetch_player_hiscores_task"
        ) as mock_task:
            mock_task.kicker.side_effect = Exception("Redis connection failed")

            with pytest.raises(
                ScheduleCreationError, match="Failed to create schedule"
            ):
                await schedule_manager.schedule_player(sample_player)

    @pytest.mark.asyncio
    async def test_unschedule_player_success(
        self, schedule_manager, mock_redis_source, sample_player
    ):
        """Test successful player unscheduling."""
        sample_player.schedule_id = "player_fetch_123"

        await schedule_manager.unschedule_player(sample_player)

        mock_redis_source.delete_schedule.assert_called_once_with(
            "player_fetch_123"
        )

    @pytest.mark.asyncio
    async def test_unschedule_player_no_schedule_id(
        self, schedule_manager, mock_redis_source, sample_player
    ):
        """Test unscheduling player with no schedule_id."""
        sample_player.schedule_id = None

        await schedule_manager.unschedule_player(sample_player)

        mock_redis_source.delete_schedule.assert_not_called()

    @pytest.mark.asyncio
    async def test_unschedule_player_not_found(
        self, schedule_manager, mock_redis_source, sample_player
    ):
        """Test unscheduling player when schedule not found in Redis."""
        sample_player.schedule_id = "player_fetch_123"
        mock_redis_source.delete_schedule.side_effect = Exception(
            "Schedule not found"
        )

        # Should not raise exception for "not found" errors
        await schedule_manager.unschedule_player(sample_player)

        mock_redis_source.delete_schedule.assert_called_once_with(
            "player_fetch_123"
        )

    @pytest.mark.asyncio
    async def test_unschedule_player_unexpected_error(
        self, schedule_manager, mock_redis_source, sample_player
    ):
        """Test unscheduling player with unexpected error."""
        sample_player.schedule_id = "player_fetch_123"
        mock_redis_source.delete_schedule.side_effect = Exception(
            "Redis connection failed"
        )

        with pytest.raises(
            ScheduleDeletionError, match="Unexpected error unscheduling"
        ):
            await schedule_manager.unschedule_player(sample_player)

    @pytest.mark.asyncio
    async def test_reschedule_player_success(
        self, schedule_manager, mock_redis_source, sample_player
    ):
        """Test successful player rescheduling."""
        sample_player.schedule_id = "old_schedule_123"

        # Mock the schedule_player method to return new schedule ID
        with (
            patch.object(
                schedule_manager, "unschedule_player"
            ) as mock_unschedule,
            patch.object(schedule_manager, "schedule_player") as mock_schedule,
        ):

            mock_schedule.return_value = "player_fetch_123"

            result = await schedule_manager.reschedule_player(sample_player)

            assert result == "player_fetch_123"
            mock_unschedule.assert_called_once_with(sample_player)
            mock_schedule.assert_called_once_with(sample_player)

    @pytest.mark.asyncio
    async def test_ensure_player_scheduled_no_schedule_id(
        self, schedule_manager, mock_redis_source, sample_player
    ):
        """Test ensure_player_scheduled when player has no schedule_id."""
        sample_player.schedule_id = None

        with patch.object(
            schedule_manager, "schedule_player"
        ) as mock_schedule:
            mock_schedule.return_value = "player_fetch_123"

            result = await schedule_manager.ensure_player_scheduled(
                sample_player
            )

            assert result == "player_fetch_123"
            mock_schedule.assert_called_once_with(sample_player)

    @pytest.mark.asyncio
    async def test_ensure_player_scheduled_exists_in_redis(
        self, schedule_manager, mock_redis_source, sample_player
    ):
        """Test ensure_player_scheduled when schedule exists in Redis."""
        sample_player.schedule_id = "player_fetch_123"

        # Mock Redis to return existing schedule
        mock_schedule = MagicMock()
        mock_schedule.schedule_id = "player_fetch_123"
        mock_redis_source.get_schedules.return_value = [mock_schedule]

        result = await schedule_manager.ensure_player_scheduled(sample_player)

        assert result == "player_fetch_123"
        mock_redis_source.get_schedules.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_player_scheduled_missing_from_redis(
        self, schedule_manager, mock_redis_source, sample_player
    ):
        """Test ensure_player_scheduled when schedule missing from Redis."""
        sample_player.schedule_id = "player_fetch_123"

        # Mock Redis to return empty schedules
        mock_redis_source.get_schedules.return_value = []

        with patch.object(
            schedule_manager, "schedule_player"
        ) as mock_schedule:
            mock_schedule.return_value = "player_fetch_456"

            result = await schedule_manager.ensure_player_scheduled(
                sample_player
            )

            assert result == "player_fetch_456"
            assert sample_player.schedule_id is None  # Should be cleared
            mock_schedule.assert_called_once_with(sample_player)

    @pytest.mark.asyncio
    async def test_ensure_player_scheduled_redis_error(
        self, schedule_manager, mock_redis_source, sample_player
    ):
        """Test ensure_player_scheduled when Redis verification fails."""
        sample_player.schedule_id = "player_fetch_123"

        # Mock Redis to raise exception
        mock_redis_source.get_schedules.side_effect = Exception(
            "Redis connection failed"
        )

        with patch.object(
            schedule_manager, "schedule_player"
        ) as mock_schedule:
            mock_schedule.return_value = "player_fetch_456"

            result = await schedule_manager.ensure_player_scheduled(
                sample_player
            )

            assert result == "player_fetch_456"
            assert sample_player.schedule_id is None  # Should be cleared
            mock_schedule.assert_called_once_with(sample_player)

    @pytest.mark.asyncio
    async def test_verify_schedule_exists_and_valid_success(
        self, schedule_manager, mock_redis_source, sample_player
    ):
        """Test schedule verification when schedule is valid."""
        sample_player.schedule_id = "player_fetch_123"

        # Mock a valid schedule
        mock_schedule = MagicMock()
        mock_schedule.schedule_id = "player_fetch_123"
        mock_schedule.cron = "*/30 * * * *"
        mock_schedule.task_name = "fetch_player_hiscores_task"
        mock_schedule.labels = {
            "player_id": "123",
            "schedule_type": "player_fetch",
        }

        mock_redis_source.get_schedules.return_value = [mock_schedule]

        result = await schedule_manager._verify_schedule_exists_and_valid(
            sample_player
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_verify_schedule_exists_and_valid_missing(
        self, schedule_manager, mock_redis_source, sample_player
    ):
        """Test schedule verification when schedule is missing."""
        sample_player.schedule_id = "player_fetch_123"

        # Mock empty schedules
        mock_redis_source.get_schedules.return_value = []

        result = await schedule_manager._verify_schedule_exists_and_valid(
            sample_player
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_verify_schedule_exists_and_valid_wrong_cron(
        self, schedule_manager, mock_redis_source, sample_player
    ):
        """Test schedule verification when cron expression is wrong."""
        sample_player.schedule_id = "player_fetch_123"
        sample_player.fetch_interval_minutes = 30

        # Mock schedule with wrong cron
        mock_schedule = MagicMock()
        mock_schedule.schedule_id = "player_fetch_123"
        mock_schedule.cron = (
            "*/60 * * * *"  # Wrong cron for 30-minute interval
        )
        mock_schedule.task_name = "fetch_player_hiscores_task"
        mock_schedule.labels = {
            "player_id": "123",
            "schedule_type": "player_fetch",
        }

        mock_redis_source.get_schedules.return_value = [mock_schedule]

        result = await schedule_manager._verify_schedule_exists_and_valid(
            sample_player
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_verify_schedule_exists_and_valid_wrong_player_id(
        self, schedule_manager, mock_redis_source, sample_player
    ):
        """Test schedule verification when player_id in labels is wrong."""
        sample_player.schedule_id = "player_fetch_123"

        # Mock schedule with wrong player_id in labels
        mock_schedule = MagicMock()
        mock_schedule.schedule_id = "player_fetch_123"
        mock_schedule.cron = "*/30 * * * *"
        mock_schedule.task_name = "fetch_player_hiscores_task"
        mock_schedule.labels = {
            "player_id": "456",
            "schedule_type": "player_fetch",
        }  # Wrong player_id

        mock_redis_source.get_schedules.return_value = [mock_schedule]

        result = await schedule_manager._verify_schedule_exists_and_valid(
            sample_player
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_verify_schedule_exists_and_valid_task_name_full_path(
        self, schedule_manager, mock_redis_source, sample_player
    ):
        """Test schedule verification with full task path format (module:function)."""
        sample_player.schedule_id = "player_fetch_123"
        sample_player.fetch_interval_minutes = 30

        # Mock schedule with full task path format (as TaskIQ stores it)
        mock_schedule = MagicMock()
        mock_schedule.schedule_id = "player_fetch_123"
        mock_schedule.cron = "*/30 * * * *"
        mock_schedule.task_name = (
            "app.workers.fetch:fetch_player_hiscores_task"
        )
        mock_schedule.labels = {
            "player_id": "123",
            "schedule_type": "player_fetch",
        }

        mock_redis_source.get_schedules.return_value = [mock_schedule]

        result = await schedule_manager._verify_schedule_exists_and_valid(
            sample_player
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_verify_schedule_exists_and_valid_task_name_simple(
        self, schedule_manager, mock_redis_source, sample_player
    ):
        """Test schedule verification with simple task name format (backward compatibility)."""
        sample_player.schedule_id = "player_fetch_123"
        sample_player.fetch_interval_minutes = 30

        # Mock schedule with simple task name format
        mock_schedule = MagicMock()
        mock_schedule.schedule_id = "player_fetch_123"
        mock_schedule.cron = "*/30 * * * *"
        mock_schedule.task_name = "fetch_player_hiscores_task"
        mock_schedule.labels = {
            "player_id": "123",
            "schedule_type": "player_fetch",
        }

        mock_redis_source.get_schedules.return_value = [mock_schedule]

        result = await schedule_manager._verify_schedule_exists_and_valid(
            sample_player
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_verify_schedule_exists_and_valid_wrong_task_name(
        self, schedule_manager, mock_redis_source, sample_player
    ):
        """Test schedule verification when task name is wrong."""
        sample_player.schedule_id = "player_fetch_123"
        sample_player.fetch_interval_minutes = 30

        # Mock schedule with wrong task name (full path format)
        mock_schedule = MagicMock()
        mock_schedule.schedule_id = "player_fetch_123"
        mock_schedule.cron = "*/30 * * * *"
        mock_schedule.task_name = "app.workers.fetch:wrong_task_name"
        mock_schedule.labels = {
            "player_id": "123",
            "schedule_type": "player_fetch",
        }

        mock_redis_source.get_schedules.return_value = [mock_schedule]

        result = await schedule_manager._verify_schedule_exists_and_valid(
            sample_player
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_verify_schedule_exists_and_valid_wrong_task_name_simple(
        self, schedule_manager, mock_redis_source, sample_player
    ):
        """Test schedule verification when task name is wrong (simple format)."""
        sample_player.schedule_id = "player_fetch_123"
        sample_player.fetch_interval_minutes = 30

        # Mock schedule with wrong task name (simple format)
        mock_schedule = MagicMock()
        mock_schedule.schedule_id = "player_fetch_123"
        mock_schedule.cron = "*/30 * * * *"
        mock_schedule.task_name = "wrong_task_name"
        mock_schedule.labels = {
            "player_id": "123",
            "schedule_type": "player_fetch",
        }

        mock_redis_source.get_schedules.return_value = [mock_schedule]

        result = await schedule_manager._verify_schedule_exists_and_valid(
            sample_player
        )

        assert result is False
