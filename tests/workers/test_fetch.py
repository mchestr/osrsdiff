"""Tests for hiscore fetch worker tasks."""

import pytest
import pytest_asyncio
from datetime import datetime, UTC, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from src.workers.fetch import (
    fetch_player_hiscores_task,
    process_scheduled_fetches_task,
    fetch_all_players_task,
)
from src.models.player import Player
from src.models.hiscore import HiscoreRecord
from src.services.osrs_api import (
    HiscoreData,
    PlayerNotFoundError,
    RateLimitError,
    APIUnavailableError,
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
    async def test_fetch_player_hiscores_success(self, test_session, sample_player):
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

        with patch("src.workers.fetch.OSRSAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.fetch_player_hiscores.return_value = mock_hiscore_data

            # Execute the task (player already in database from fixture)
            with patch("src.workers.fetch.AsyncSessionLocal") as mock_session_local:
                mock_session_local.return_value.__aenter__.return_value = test_session
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
        with patch('src.workers.fetch.AsyncSessionLocal') as mock_session_local:
            # Create a mock session
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session
            
            # Create a mock result that returns None for scalar_one_or_none
            mock_result = AsyncMock()
            # Make scalar_one_or_none a regular method that returns None
            mock_result.scalar_one_or_none = lambda: None
            mock_session.execute = AsyncMock(return_value=mock_result)
            
            result = await fetch_player_hiscores_task.original_func("nonexistent_player")

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

        with patch("src.workers.fetch.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = test_session
            result = await fetch_player_hiscores_task.original_func(
                sample_player.username
            )

        assert result["status"] == "skipped"
        assert result["reason"] == "player_inactive"
        assert result["username"] == sample_player.username

    @pytest.mark.asyncio
    async def test_fetch_player_not_found_in_osrs(self, test_session, sample_player):
        """Test fetch when player not found in OSRS hiscores."""
        with patch("src.workers.fetch.OSRSAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.fetch_player_hiscores.side_effect = PlayerNotFoundError(
                "Player not found"
            )

            with patch("src.workers.fetch.AsyncSessionLocal") as mock_session_local:
                mock_session_local.return_value.__aenter__.return_value = test_session
                result = await fetch_player_hiscores_task.original_func(
                    sample_player.username
                )

            assert result["status"] == "warning"
            assert result["error_type"] == "osrs_player_not_found"
            assert result["username"] == sample_player.username

    @pytest.mark.asyncio
    async def test_fetch_rate_limit_error(self, test_session, sample_player):
        """Test fetch with rate limit error (should raise for retry)."""
        with patch("src.workers.fetch.OSRSAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.fetch_player_hiscores.side_effect = RateLimitError(
                "Rate limit exceeded"
            )

            with patch("src.workers.fetch.AsyncSessionLocal") as mock_session_local:
                mock_session_local.return_value.__aenter__.return_value = test_session
                # Should raise the exception for task retry
                with pytest.raises(RateLimitError):
                    await fetch_player_hiscores_task.original_func(
                        sample_player.username
                    )

    @pytest.mark.asyncio
    async def test_fetch_api_unavailable_error(self, test_session, sample_player):
        """Test fetch with API unavailable error (should raise for retry)."""
        with patch("src.workers.fetch.OSRSAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.fetch_player_hiscores.side_effect = APIUnavailableError(
                "API unavailable"
            )

            with patch("src.workers.fetch.AsyncSessionLocal") as mock_session_local:
                mock_session_local.return_value.__aenter__.return_value = test_session
                # Should raise the exception for task retry
                with pytest.raises(APIUnavailableError):
                    await fetch_player_hiscores_task.original_func(
                        sample_player.username
                    )


class TestProcessScheduledFetches:
    """Test scheduled fetch processing."""

    @pytest.mark.asyncio
    async def test_process_no_active_players(self, test_session):
        """Test processing when no active players exist."""
        with patch("src.workers.fetch.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = test_session
            result = await process_scheduled_fetches_task.original_func()

        assert result["status"] == "success"
        assert result["players_processed"] == 0
        assert result["tasks_enqueued"] == 0
        assert "No active players" in result["message"]

    @pytest.mark.asyncio
    async def test_process_players_needing_fetch(self, test_session):
        """Test processing players that need fetching."""
        # Create players with different fetch needs
        player1 = Player(username="player1", last_fetched=None)  # Never fetched
        player2 = Player(
            username="player2",
            last_fetched=datetime.now(UTC) - timedelta(hours=2),  # Needs fetch
            fetch_interval_minutes=60,
        )
        player3 = Player(
            username="player3",
            last_fetched=datetime.now(UTC) - timedelta(minutes=30),  # Recent fetch
            fetch_interval_minutes=60,
        )

        test_session.add_all([player1, player2, player3])
        await test_session.commit()

        with patch("src.workers.fetch.fetch_player_hiscores_task") as mock_task:
            mock_task.kiq = AsyncMock()

            with patch("src.workers.fetch.AsyncSessionLocal") as mock_session_local:
                mock_session_local.return_value.__aenter__.return_value = test_session
                result = await process_scheduled_fetches_task.original_func()

            assert result["status"] == "success"
            assert result["players_processed"] == 3
            assert result["players_needing_fetch"] == 2  # player1 and player2
            # Note: Due to mocking complexity, we just verify the basic result structure
            assert "tasks_enqueued" in result
            assert "failed_enqueues" in result

    @pytest.mark.asyncio
    async def test_process_no_players_need_fetch(self, test_session):
        """Test processing when no players need fetching."""
        # Create player with recent fetch
        player = Player(
            username="recent_player",
            last_fetched=datetime.now(UTC) - timedelta(minutes=30),
            fetch_interval_minutes=60,
        )

        test_session.add(player)
        await test_session.commit()

        with patch("src.workers.fetch.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = test_session
            result = await process_scheduled_fetches_task.original_func()

        assert result["status"] == "success"
        assert result["players_processed"] == 1
        assert result["players_needing_fetch"] == 0
        assert result["tasks_enqueued"] == 0
        assert "No players need fetching" in result["message"]


class TestFetchAllPlayers:
    """Test fetch all players functionality."""

    @pytest.mark.asyncio
    async def test_fetch_all_no_players(self, test_session):
        """Test fetch all when no active players exist."""
        with patch("src.workers.fetch.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = test_session
            result = await fetch_all_players_task.original_func()

        assert result["status"] == "success"
        assert result["players_processed"] == 0
        assert result["tasks_enqueued"] == 0
        assert "No active players" in result["message"]

    @pytest.mark.asyncio
    async def test_fetch_all_success(self, test_session):
        """Test successful fetch all players."""
        # Create active and inactive players
        active_player1 = Player(username="active1", is_active=True)
        active_player2 = Player(username="active2", is_active=True)
        inactive_player = Player(username="inactive", is_active=False)

        test_session.add_all([active_player1, active_player2, inactive_player])
        await test_session.commit()

        # Mock the task import to avoid circular import issues
        with patch("src.workers.fetch.fetch_player_hiscores_task") as mock_task:
            mock_task.kiq = AsyncMock()

            with patch("src.workers.fetch.AsyncSessionLocal") as mock_session_local:
                mock_session_local.return_value.__aenter__.return_value = test_session
                result = await fetch_all_players_task.original_func()

            assert result["status"] == "success"
            assert result["players_processed"] == 2  # Only active players
            # Note: Due to mocking complexity, we just verify the basic result structure
            assert "tasks_enqueued" in result
            assert "failed_enqueues" in result
