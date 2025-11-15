"""Tests for maintenance worker tasks."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workers.maintenance import (
    cleanup_orphaned_schedules_job,
    schedule_verification_job,
)


class TestScheduleVerificationJob:
    """Test cases for schedule_verification_job."""

    @pytest.mark.asyncio
    async def test_schedule_verification_job_success(self):
        """Test successful schedule verification job."""
        mock_summary_result = {
            "status": "success",
            "summary": {
                "active_players": 10,
                "scheduled_players": 10,
                "redis_schedules": 10,
            },
        }

        mock_consistency_result = {
            "status": "success",
            "is_consistent": True,
            "inconsistencies": [],
            "inconsistency_types": {},
        }

        mock_cleanup_result = {
            "status": "success",
            "orphaned_schedules": [],
            "schedules_removed": 0,
        }

        with patch(
            "app.workers.maintenance.AsyncSessionLocal"
        ) as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = (
                mock_session
            )

            with patch(
                "app.workers.maintenance.ScheduleMaintenanceService"
            ) as mock_service_class:
                mock_service = MagicMock()
                mock_service_class.return_value = mock_service
                mock_service.get_schedule_summary = AsyncMock(
                    return_value=mock_summary_result
                )
                mock_service.verify_schedule_consistency = AsyncMock(
                    return_value=mock_consistency_result
                )
                mock_service.cleanup_orphaned_schedules = AsyncMock(
                    return_value=mock_cleanup_result
                )
                mock_service.fix_player_schedule = AsyncMock()

                with patch(
                    "app.workers.maintenance.get_player_schedule_manager"
                ) as mock_get_manager:
                    result = await schedule_verification_job()

                    assert result["status"] == "healthy"
                    assert "summary" in result
                    assert "verification" in result
                    assert "cleanup" in result

    @pytest.mark.asyncio
    async def test_schedule_verification_job_with_inconsistencies(self):
        """Test schedule verification job with inconsistencies."""
        mock_summary_result = {
            "status": "success",
            "summary": {
                "active_players": 10,
                "scheduled_players": 8,
                "redis_schedules": 10,
            },
        }

        mock_consistency_result = {
            "status": "success",
            "is_consistent": False,
            "inconsistencies": [
                {
                    "type": "missing_redis_schedule",
                    "player_id": 1,
                    "username": "testplayer",
                }
            ],
            "inconsistency_types": {"missing_redis_schedule": 1},
        }

        mock_cleanup_result = {
            "status": "success",
            "orphaned_schedules": [],
            "schedules_removed": 0,
        }

        mock_player = MagicMock()
        mock_player.id = 1
        mock_player.username = "testplayer"
        mock_player.is_active = True

        with patch(
            "app.workers.maintenance.AsyncSessionLocal"
        ) as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = (
                mock_session
            )

            with patch(
                "app.workers.maintenance.ScheduleMaintenanceService"
            ) as mock_service_class:
                mock_service = MagicMock()
                mock_service_class.return_value = mock_service
                mock_service.get_schedule_summary = AsyncMock(
                    return_value=mock_summary_result
                )
                mock_service.verify_schedule_consistency = AsyncMock(
                    return_value=mock_consistency_result
                )
                mock_service.cleanup_orphaned_schedules = AsyncMock(
                    return_value=mock_cleanup_result
                )
                mock_service.fix_player_schedule = AsyncMock(
                    return_value={"status": "success"}
                )

                with patch(
                    "app.workers.maintenance.get_player_schedule_manager"
                ) as mock_get_manager:
                    # Mock the database query that happens inside the function
                    # The function imports select and Player inside, so we patch at the sqlalchemy level
                    with patch("sqlalchemy.select") as mock_select_module:
                        # Create a mock statement chain
                        mock_stmt = MagicMock()
                        mock_select_module.return_value = mock_stmt
                        mock_stmt.where.return_value = mock_stmt

                        # Mock the execute result
                        mock_result = MagicMock()
                        mock_result.scalar_one_or_none.return_value = (
                            mock_player
                        )
                        mock_session.execute = AsyncMock(
                            return_value=mock_result
                        )

                        result = await schedule_verification_job()

                        assert result["status"] in [
                            "healthy",
                            "cleaned",
                            "issues_remain",
                        ]
                        assert "verification" in result
                        assert "fixes" in result

    @pytest.mark.asyncio
    async def test_schedule_verification_job_error(self):
        """Test schedule verification job with error."""
        with patch(
            "app.workers.maintenance.AsyncSessionLocal"
        ) as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = (
                mock_session
            )

            with patch(
                "app.workers.maintenance.ScheduleMaintenanceService"
            ) as mock_service_class:
                mock_service = MagicMock()
                mock_service_class.return_value = mock_service
                mock_service.get_schedule_summary = AsyncMock(
                    side_effect=Exception("Service error")
                )

                with patch(
                    "app.workers.maintenance.get_player_schedule_manager"
                ) as mock_get_manager:
                    result = await schedule_verification_job()

                    assert result["status"] == "error"
                    assert "error" in result


class TestCleanupOrphanedSchedulesJob:
    """Test cases for cleanup_orphaned_schedules_job."""

    @pytest.mark.asyncio
    async def test_cleanup_orphaned_schedules_job_success(self):
        """Test successful orphaned schedule cleanup job."""
        mock_cleanup_result = {
            "status": "success",
            "orphaned_schedules": [
                {
                    "schedule_id": "player_fetch_999",
                    "reason": "Player not found",
                }
            ],
            "schedules_removed": 1,
        }

        with patch(
            "app.workers.maintenance.AsyncSessionLocal"
        ) as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = (
                mock_session
            )

            with patch(
                "app.workers.maintenance.ScheduleMaintenanceService"
            ) as mock_service_class:
                mock_service = MagicMock()
                mock_service_class.return_value = mock_service
                mock_service.cleanup_orphaned_schedules = AsyncMock(
                    return_value=mock_cleanup_result
                )

                with patch(
                    "app.workers.maintenance.get_player_schedule_manager"
                ) as mock_get_manager:
                    result = await cleanup_orphaned_schedules_job()

                    assert result["status"] == "success"
                    assert result["schedules_removed"] == 1
                    assert "duration_seconds" in result

    @pytest.mark.asyncio
    async def test_cleanup_orphaned_schedules_job_error(self):
        """Test orphaned schedule cleanup job with error."""
        with patch(
            "app.workers.maintenance.AsyncSessionLocal"
        ) as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = (
                mock_session
            )

            with patch(
                "app.workers.maintenance.ScheduleMaintenanceService"
            ) as mock_service_class:
                mock_service = MagicMock()
                mock_service_class.return_value = mock_service
                mock_service.cleanup_orphaned_schedules = AsyncMock(
                    side_effect=Exception("Cleanup error")
                )

                with patch(
                    "app.workers.maintenance.get_player_schedule_manager"
                ) as mock_get_manager:
                    result = await cleanup_orphaned_schedules_job()

                    assert result["status"] == "error"
                    assert "error" in result
                    assert "duration_seconds" in result
