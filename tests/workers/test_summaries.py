"""Tests for summary generation worker tasks."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workers.summaries import (
    daily_summary_generation_job,
    generate_player_summary_task,
)


class TestSummaryTasks:
    """Test cases for summary generation tasks."""

    @pytest.mark.asyncio
    async def test_daily_summary_generation_job_success(self):
        """Test successful daily summary generation job."""
        from app.models.player_summary import PlayerSummary

        mock_summary = PlayerSummary(
            id=1,
            player_id=1,
            period_start=datetime.now(timezone.utc) - timedelta(days=7),
            period_end=datetime.now(timezone.utc),
            summary_text="Generated summary",
            generated_at=datetime.now(timezone.utc),
        )

        with patch(
            "app.workers.summaries.AsyncSessionLocal"
        ) as mock_session_local:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_local.return_value = mock_session

            with patch(
                "app.workers.summaries.SummaryService"
            ) as mock_service_class:
                mock_service = MagicMock()
                mock_service.generate_summaries_for_all_players = AsyncMock(
                    return_value=[mock_summary]
                )
                mock_service_class.return_value = mock_service

                result = await daily_summary_generation_job()

                assert result["status"] == "success"
                assert result["summaries_generated"] == 1
                assert "duration_seconds" in result

    @pytest.mark.asyncio
    async def test_daily_summary_generation_job_error(self):
        """Test daily summary generation job handles errors."""
        with patch(
            "app.workers.summaries.AsyncSessionLocal"
        ) as mock_session_local:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_local.return_value = mock_session

            with patch(
                "app.workers.summaries.SummaryService"
            ) as mock_service_class:
                mock_service = MagicMock()
                mock_service.generate_summaries_for_all_players = AsyncMock(
                    side_effect=Exception("Test error")
                )
                mock_service_class.return_value = mock_service

                result = await daily_summary_generation_job()

                assert result["status"] == "error"
                assert "error" in result
                assert "Test error" in result["error"]

    @pytest.mark.asyncio
    async def test_generate_player_summary_task_success(self):
        """Test successful player summary generation task."""
        from app.models.player_summary import PlayerSummary

        mock_summary = PlayerSummary(
            id=1,
            player_id=1,
            period_start=datetime.now(timezone.utc) - timedelta(days=7),
            period_end=datetime.now(timezone.utc),
            summary_text="Generated summary",
            generated_at=datetime.now(timezone.utc),
        )

        with patch(
            "app.workers.summaries.AsyncSessionLocal"
        ) as mock_session_local:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_local.return_value = mock_session

            with patch(
                "app.workers.summaries.SummaryService"
            ) as mock_service_class:
                mock_service = MagicMock()
                mock_service.generate_summary_for_player = AsyncMock(
                    return_value=mock_summary
                )
                mock_service_class.return_value = mock_service

                result = await generate_player_summary_task(
                    player_id=1, force_regenerate=False
                )

                assert result["status"] == "success"
                assert result["player_id"] == 1
                assert result["summary_id"] == 1
                assert "duration_seconds" in result

    @pytest.mark.asyncio
    async def test_generate_player_summary_task_error(self):
        """Test player summary generation task handles errors."""
        with patch(
            "app.workers.summaries.AsyncSessionLocal"
        ) as mock_session_local:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_local.return_value = mock_session

            with patch(
                "app.workers.summaries.SummaryService"
            ) as mock_service_class:
                mock_service = MagicMock()
                mock_service.generate_summary_for_player = AsyncMock(
                    side_effect=Exception("Test error")
                )
                mock_service_class.return_value = mock_service

                result = await generate_player_summary_task(
                    player_id=1, force_regenerate=False
                )

                assert result["status"] == "error"
                assert result["player_id"] == 1
                assert "error" in result
                assert "Test error" in result["error"]
