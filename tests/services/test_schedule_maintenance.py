"""Tests for schedule maintenance service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.player import Player
from app.services.scheduler import ScheduleMaintenanceService


class TestScheduleMaintenanceService:
    """Test cases for ScheduleMaintenanceService."""

    @pytest.fixture
    def mock_redis_source(self):
        """Create a mock Redis schedule source."""
        redis_source = AsyncMock()
        redis_source.get_schedules = AsyncMock(return_value=[])
        redis_source.delete_schedule = AsyncMock()
        return redis_source

    @pytest.fixture
    def maintenance_service(self, mock_redis_source):
        """Create a maintenance service instance."""
        return ScheduleMaintenanceService(mock_redis_source)

    @pytest.fixture
    def mock_schedule(self):
        """Create a mock schedule object."""
        schedule = MagicMock()
        schedule.schedule_id = "player_fetch_1"
        return schedule

    @pytest.mark.asyncio
    async def test_cleanup_orphaned_schedules_no_schedules(
        self, maintenance_service, test_session, mock_redis_source
    ):
        """Test cleanup when no schedules exist."""
        mock_redis_source.get_schedules = AsyncMock(return_value=[])

        result = await maintenance_service.cleanup_orphaned_schedules(
            test_session, dry_run=False
        )

        assert result["status"] == "success"
        assert result["schedules_processed"] == 0
        assert result["schedules_removed"] == 0
        assert result["orphaned_schedules"] == []

    @pytest.mark.asyncio
    async def test_cleanup_orphaned_schedules_dry_run(
        self,
        maintenance_service,
        test_session,
        mock_redis_source,
        mock_schedule,
    ):
        """Test cleanup in dry run mode."""
        # Mock schedule for inactive player
        mock_redis_source.get_schedules = AsyncMock(
            return_value=[mock_schedule]
        )

        # No active players
        with patch("app.services.scheduler.select") as mock_select:
            mock_stmt = MagicMock()
            mock_select.return_value = mock_stmt
            mock_stmt.where.return_value = mock_stmt
            mock_result = MagicMock()
            mock_result.all.return_value = []
            test_session.execute = AsyncMock(return_value=mock_result)

            result = await maintenance_service.cleanup_orphaned_schedules(
                test_session, dry_run=True
            )

            assert result["status"] == "success"
            assert result["dry_run"] is True
            assert result["schedules_removed"] == 0
            # Should not call delete_schedule in dry run
            mock_redis_source.delete_schedule.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_schedule_summary(
        self, maintenance_service, test_session, mock_redis_source
    ):
        """Test getting schedule summary."""
        mock_redis_source.get_schedules = AsyncMock(return_value=[])

        with patch("app.services.scheduler.select") as mock_select:
            with patch("app.services.scheduler.func") as mock_func:
                mock_count_stmt = MagicMock()
                mock_select.return_value = mock_count_stmt

                mock_count_result = MagicMock()
                mock_count_result.scalar.return_value = 5
                test_session.execute = AsyncMock(
                    return_value=mock_count_result
                )

                result = await maintenance_service.get_schedule_summary(
                    test_session
                )

                assert result["status"] == "success"
                assert "summary" in result
                assert "total_players" in result["summary"]

    @pytest.mark.asyncio
    async def test_fix_player_schedule_inactive_player(
        self, maintenance_service, test_session, mock_redis_source
    ):
        """Test fixing schedule for inactive player."""
        player = Player(id=1, username="testplayer", is_active=False)

        result = await maintenance_service.fix_player_schedule(
            player, test_session, force_recreate=False
        )

        assert result["status"] == "error"
        assert "inactive" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_fix_player_schedule_success(
        self, maintenance_service, test_session, mock_redis_source
    ):
        """Test successfully fixing a player schedule."""
        from unittest.mock import patch

        player = Player(
            id=1,
            username="testplayer",
            is_active=True,
            schedule_id="player_fetch_1",
            fetch_interval_minutes=60,
        )

        # Mock schedule exists in Redis
        mock_schedule = MagicMock()
        mock_schedule.schedule_id = "player_fetch_1"
        mock_redis_source.get_schedules = AsyncMock(
            return_value=[mock_schedule]
        )

        with patch(
            "app.services.scheduler.get_player_schedule_manager"
        ) as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.ensure_player_scheduled = AsyncMock(
                return_value="player_fetch_1"
            )
            mock_get_manager.return_value = mock_manager

            result = await maintenance_service.fix_player_schedule(
                player, test_session, force_recreate=False
            )

            assert result["status"] == "success"
            assert result["player_id"] == 1
            assert result["username"] == "testplayer"

    @pytest.mark.asyncio
    async def test_bulk_fix_schedules_no_players(
        self, maintenance_service, test_session, mock_redis_source
    ):
        """Test bulk fix with no players."""
        with patch("app.services.scheduler.select") as mock_select:
            mock_stmt = MagicMock()
            mock_select.return_value = mock_stmt
            mock_stmt.where.return_value = mock_stmt
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            test_session.execute = AsyncMock(return_value=mock_result)

            result = await maintenance_service.bulk_fix_schedules(
                test_session, player_ids=None, force_recreate=False
            )

            assert result["status"] == "success"
            assert result["players_processed"] == 0
            assert result["successful_fixes"] == 0
