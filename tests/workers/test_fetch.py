"""Tests for hiscore fetch worker tasks."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import OSRSPlayerNotFoundError
from app.models.player import Player
from app.services.osrs_api import (
    APIUnavailableError,
    HiscoreData,
    RateLimitError,
)
from app.workers.fetch import (
    fetch_player_hiscores_task,
)


class TestFetchPlayerHiscores:
    """Test individual player hiscore fetching."""

    @pytest_asyncio.fixture
    async def sample_player(self, test_session: AsyncSession):
        """Create a sample player for testing."""
        player = Player(username="test_player")
        test_session.add(player)
        await test_session.commit()
        await test_session.refresh(player)
        return player

    @pytest.mark.asyncio
    async def test_fetch_player_hiscores_success(
        self, test_session, sample_player
    ):
        """Test successful hiscore fetch for a player."""
        # Mock OSRS API response
        mock_hiscore_data = HiscoreData(
            overall={"rank": 1000, "level": 1500, "experience": 50000000},
            skills={
                "attack": {"rank": 500, "level": 99, "experience": 13034431},
                "defence": {"rank": 600, "level": 90, "experience": 5346332},
            },
            bosses={
                "zulrah": {"rank": 100, "kc": 500},
                "vorkath": {"rank": 200, "kc": 300},
            },
            fetched_at=datetime.now(UTC),
        )

        with patch("app.workers.fetch.OSRSAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client
            )
            mock_client.fetch_player_hiscores.return_value = mock_hiscore_data

            # Execute the task (player already in database from fixture)
            with patch(
                "app.workers.fetch.AsyncSessionLocal"
            ) as mock_session_local:
                mock_session_local.return_value.__aenter__.return_value = (
                    test_session
                )
                result = await fetch_player_hiscores_task.original_func(
                    sample_player.username
                )

                # Verify result
                assert result["status"] == "success"
                assert result["username"] == sample_player.username
                assert result["player_id"] == sample_player.id
                assert "record_id" in result
                assert result["overall_level"] == 1500
                assert result["overall_experience"] == 50000000
                assert result["skills_count"] == 2
                assert result["bosses_count"] == 2

                # Verify player's last_fetched was updated
                await test_session.refresh(sample_player)
                assert sample_player.last_fetched is not None

    @pytest.mark.asyncio
    async def test_fetch_player_not_in_database(self):
        """Test fetch for player not in database."""
        # Mock the entire AsyncSessionLocal context manager
        with patch(
            "app.workers.fetch.AsyncSessionLocal"
        ) as mock_session_local:
            # Create a mock session
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = (
                mock_session
            )

            # Create a mock result that returns None for scalar_one_or_none
            mock_result = AsyncMock()
            # Make scalar_one_or_none a regular method that returns None
            mock_result.scalar_one_or_none = lambda: None
            mock_session.execute = AsyncMock(return_value=mock_result)

            result = await fetch_player_hiscores_task.original_func(
                "nonexistent_player"
            )

            assert result["status"] == "error"
            assert result["error_type"] == "player_not_found"
            assert result["username"] == "nonexistent_player"
            assert "not found in database" in result["error"]

    @pytest.mark.asyncio
    async def test_fetch_inactive_player(self, test_session, sample_player):
        """Test fetch for inactive player."""
        # Make player inactive
        sample_player.is_active = False
        await test_session.commit()

        with patch(
            "app.workers.fetch.AsyncSessionLocal"
        ) as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = (
                test_session
            )
            result = await fetch_player_hiscores_task.original_func(
                sample_player.username
            )

        assert result["status"] == "skipped"
        assert result["reason"] == "player_inactive"
        assert result["username"] == sample_player.username

    @pytest.mark.asyncio
    async def test_fetch_player_not_found_in_osrs(
        self, test_session, sample_player
    ):
        """Test fetch when player not found in OSRS hiscores."""
        with patch("app.workers.fetch.OSRSAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client
            )
            mock_client.fetch_player_hiscores.side_effect = (
                OSRSPlayerNotFoundError("test_player")
            )

            with patch(
                "app.workers.fetch.AsyncSessionLocal"
            ) as mock_session_local:
                mock_session_local.return_value.__aenter__.return_value = (
                    test_session
                )
                result = await fetch_player_hiscores_task.original_func(
                    sample_player.username
                )

            assert result["status"] == "warning"
            assert result["error_type"] == "osrs_player_not_found"
            assert result["username"] == sample_player.username

    @pytest.mark.asyncio
    async def test_fetch_rate_limit_error(self, test_session, sample_player):
        """Test fetch with rate limit error (should raise for retry)."""
        with patch("app.workers.fetch.OSRSAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client
            )
            mock_client.fetch_player_hiscores.side_effect = RateLimitError(
                "Rate limit exceeded"
            )

            with patch(
                "app.workers.fetch.AsyncSessionLocal"
            ) as mock_session_local:
                mock_session_local.return_value.__aenter__.return_value = (
                    test_session
                )
                # Should raise the exception for task retry
                with pytest.raises(RateLimitError):
                    await fetch_player_hiscores_task.original_func(
                        sample_player.username
                    )

    @pytest.mark.asyncio
    async def test_fetch_api_unavailable_error(
        self, test_session, sample_player
    ):
        """Test fetch with API unavailable error (should raise for retry)."""
        with patch("app.workers.fetch.OSRSAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client
            )
            mock_client.fetch_player_hiscores.side_effect = (
                APIUnavailableError("API unavailable")
            )

            with patch(
                "app.workers.fetch.AsyncSessionLocal"
            ) as mock_session_local:
                mock_session_local.return_value.__aenter__.return_value = (
                    test_session
                )
                # Should raise the exception for task retry
                with pytest.raises(APIUnavailableError):
                    await fetch_player_hiscores_task.original_func(
                        sample_player.username
                    )
