"""Tests for OSRS API client service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientError

from app.exceptions import OSRSPlayerNotFoundError
from app.services.osrs_api import (
    APIUnavailableError,
    HiscoreData,
    OSRSAPIClient,
    OSRSAPIError,
    RateLimitError,
)


class TestOSRSAPIClient:
    """Test cases for OSRSAPIClient."""

    @pytest.fixture
    async def client(self):
        """Create an OSRS API client for testing."""
        client = OSRSAPIClient()
        yield client
        await client.close()

    @pytest.fixture
    def mock_hiscore_response(self):
        """Mock OSRS API JSON response."""
        return {
            "name": "TestPlayer",
            "skills": [
                {
                    "id": 0,
                    "name": "Overall",
                    "rank": 1000,
                    "level": 1500,
                    "xp": 50000000,
                },
                {
                    "id": 1,
                    "name": "Attack",
                    "rank": 500,
                    "level": 99,
                    "xp": 13034431,
                },
                {
                    "id": 2,
                    "name": "Defence",
                    "rank": 600,
                    "level": 90,
                    "xp": 5346332,
                },
                {
                    "id": 3,
                    "name": "Strength",
                    "rank": 400,
                    "level": 99,
                    "xp": 13034431,
                },
            ],
            "activities": [
                {"id": 0, "name": "Abyssal Sire", "rank": 100, "score": 50},
                {"id": 1, "name": "Zulrah", "rank": 200, "score": 100},
                {
                    "id": 2,
                    "name": "Vorkath",
                    "rank": -1,
                    "score": -1,
                },  # No kills
            ],
        }

    async def test_parse_skill_data_valid(self, client):
        """Test parsing valid skill data."""
        skill_data = {"rank": 1000, "level": 99, "xp": 13034431}
        result = client._parse_skill_data(skill_data)

        assert result == {"rank": 1000, "level": 99, "experience": 13034431}

    async def test_parse_skill_data_no_rank(self, client):
        """Test parsing skill data with no rank (-1)."""
        skill_data = {"rank": -1, "level": 50, "xp": 100000}
        result = client._parse_skill_data(skill_data)

        assert result == {"rank": None, "level": 50, "experience": 100000}

    async def test_parse_activity_data_valid(self, client):
        """Test parsing valid activity data."""
        activity_data = {"rank": 100, "score": 50}
        result = client._parse_activity_data(activity_data)

        assert result == {"rank": 100, "kc": 50}

    async def test_parse_activity_data_no_kills(self, client):
        """Test parsing activity data with no kills (-1)."""
        activity_data = {"rank": -1, "score": -1}
        result = client._parse_activity_data(activity_data)

        assert result == {"rank": None, "kc": None}

    async def test_parse_hiscore_data_complete(
        self, client, mock_hiscore_response
    ):
        """Test parsing complete hiscore data."""
        result = client._parse_hiscore_data(mock_hiscore_response)

        assert isinstance(result, HiscoreData)
        assert result.overall == {
            "rank": 1000,
            "level": 1500,
            "experience": 50000000,
        }
        assert "attack" in result.skills
        assert result.skills["attack"] == {
            "rank": 500,
            "level": 99,
            "experience": 13034431,
        }
        assert "abyssal_sire" in result.bosses
        assert result.bosses["abyssal_sire"] == {"rank": 100, "kc": 50}
        assert result.bosses["vorkath"] == {"rank": None, "kc": None}

    async def test_parse_hiscore_data_invalid_format(self, client):
        """Test parsing invalid hiscore data format."""
        with pytest.raises(OSRSAPIError, match="Invalid hiscore data format"):
            client._parse_hiscore_data("invalid_data")

    async def test_fetch_player_hiscores_empty_username(self, client):
        """Test fetching hiscores with empty username."""
        with pytest.raises(ValueError, match="Username cannot be empty"):
            await client.fetch_player_hiscores("")

        with pytest.raises(ValueError, match="Username cannot be empty"):
            await client.fetch_player_hiscores("   ")

    async def test_check_player_exists_found(
        self, client, mock_hiscore_response
    ):
        """Test checking if player exists when they do."""
        with patch.object(client, "fetch_player_hiscores") as mock_fetch:
            mock_fetch.return_value = HiscoreData(
                overall={"rank": 1000, "level": 1500, "experience": 50000000},
                skills={},
                bosses={},
            )

            result = await client.check_player_exists("test_player")
            assert result is True
            mock_fetch.assert_called_once_with("test_player")

    async def test_check_player_exists_not_found(self, client):
        """Test checking if player exists when they don't."""
        with patch.object(client, "fetch_player_hiscores") as mock_fetch:
            mock_fetch.side_effect = OSRSPlayerNotFoundError(
                "Player not found"
            )

            result = await client.check_player_exists("nonexistent_player")
            assert result is False

    async def test_check_player_exists_api_error(self, client):
        """Test checking player existence when API has errors."""
        with patch.object(client, "fetch_player_hiscores") as mock_fetch:
            mock_fetch.side_effect = APIUnavailableError("API unavailable")

            with pytest.raises(APIUnavailableError):
                await client.check_player_exists("test_player")

    async def test_context_manager(self):
        """Test using client as async context manager."""
        async with OSRSAPIClient() as client:
            assert client._session is not None
            assert not client._session.closed

        # Session should be closed after exiting context
        assert client._session is None or client._session.closed

    async def test_504_error_retries_with_exponential_backoff(self, client):
        """Test that 504 errors retry with exponential backoff and eventually succeed."""
        mock_response_success = AsyncMock()
        mock_response_success.status = 200
        mock_response_success.json = AsyncMock(
            return_value={
                "name": "TestPlayer",
                "skills": [
                    {
                        "id": 0,
                        "name": "Overall",
                        "rank": 1000,
                        "level": 1500,
                        "xp": 50000000,
                    }
                ],
                "activities": [],
            }
        )

        mock_response_504 = AsyncMock()
        mock_response_504.status = 504

        # Create async context managers for each response
        def make_context_manager(response):
            cm = AsyncMock()
            cm.__aenter__ = AsyncMock(return_value=response)
            cm.__aexit__ = AsyncMock(return_value=None)
            return cm

        mock_session = AsyncMock()
        # First two attempts return 504, third succeeds
        mock_session.get = MagicMock(
            side_effect=[
                make_context_manager(mock_response_504),
                make_context_manager(mock_response_504),
                make_context_manager(mock_response_success),
            ]
        )
        mock_session.closed = False

        client._session = mock_session

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await client._make_request("testplayer")

            # Should have retried twice (2 sleep calls)
            assert mock_sleep.call_count == 2
            # Verify exponential backoff delays: 1.0s, 2.0s
            assert mock_sleep.call_args_list[0][0][0] == pytest.approx(
                1.0, rel=0.1
            )
            assert mock_sleep.call_args_list[1][0][0] == pytest.approx(
                2.0, rel=0.1
            )
            # Should have made 3 requests total (2 failures + 1 success)
            assert mock_session.get.call_count == 3
            # Should return successful response
            assert result["name"] == "TestPlayer"

    async def test_504_error_retries_until_max_retries(self, client):
        """Test that 504 errors retry until max retries then raise APIUnavailableError."""
        mock_response_504 = AsyncMock()
        mock_response_504.status = 504

        # Create async context manager for 504 response
        def make_context_manager(response):
            cm = AsyncMock()
            cm.__aenter__ = AsyncMock(return_value=response)
            cm.__aexit__ = AsyncMock(return_value=None)
            return cm

        mock_session = AsyncMock()
        # All attempts return 504
        mock_session.get = MagicMock(
            return_value=make_context_manager(mock_response_504)
        )
        mock_session.closed = False

        client._session = mock_session

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(
                APIUnavailableError,
                match="OSRS API unavailable after 4 attempts",
            ):
                await client._make_request("testplayer")

            # Should have retried MAX_RETRIES times (3 sleep calls for 3 retries)
            assert mock_sleep.call_count == client.MAX_RETRIES
            # Verify exponential backoff delays: 1.0s, 2.0s, 4.0s
            assert mock_sleep.call_args_list[0][0][0] == pytest.approx(
                1.0, rel=0.1
            )
            assert mock_sleep.call_args_list[1][0][0] == pytest.approx(
                2.0, rel=0.1
            )
            assert mock_sleep.call_args_list[2][0][0] == pytest.approx(
                4.0, rel=0.1
            )
            # Should have made MAX_RETRIES + 1 requests (4 total: initial + 3 retries)
            assert mock_session.get.call_count == client.MAX_RETRIES + 1

    async def test_500_error_retries_with_exponential_backoff(self, client):
        """Test that other 5xx errors (500) also retry with exponential backoff."""
        mock_response_success = AsyncMock()
        mock_response_success.status = 200
        mock_response_success.json = AsyncMock(
            return_value={
                "name": "TestPlayer",
                "skills": [
                    {
                        "id": 0,
                        "name": "Overall",
                        "rank": 1000,
                        "level": 1500,
                        "xp": 50000000,
                    }
                ],
                "activities": [],
            }
        )

        mock_response_500 = AsyncMock()
        mock_response_500.status = 500

        # Create async context managers for each response
        def make_context_manager(response):
            cm = AsyncMock()
            cm.__aenter__ = AsyncMock(return_value=response)
            cm.__aexit__ = AsyncMock(return_value=None)
            return cm

        mock_session = AsyncMock()
        # First attempt returns 500, second succeeds
        mock_session.get = MagicMock(
            side_effect=[
                make_context_manager(mock_response_500),
                make_context_manager(mock_response_success),
            ]
        )
        mock_session.closed = False

        client._session = mock_session

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await client._make_request("testplayer")

            # Should have retried once (1 sleep call)
            assert mock_sleep.call_count == 1
            # Verify exponential backoff delay: 1.0s
            assert mock_sleep.call_args_list[0][0][0] == pytest.approx(
                1.0, rel=0.1
            )
            # Should have made 2 requests total (1 failure + 1 success)
            assert mock_session.get.call_count == 2
            # Should return successful response
            assert result["name"] == "TestPlayer"

    async def test_503_error_retries_with_exponential_backoff(self, client):
        """Test that 503 errors also retry with exponential backoff."""
        mock_response_success = AsyncMock()
        mock_response_success.status = 200
        mock_response_success.json = AsyncMock(
            return_value={
                "name": "TestPlayer",
                "skills": [
                    {
                        "id": 0,
                        "name": "Overall",
                        "rank": 1000,
                        "level": 1500,
                        "xp": 50000000,
                    }
                ],
                "activities": [],
            }
        )

        mock_response_503 = AsyncMock()
        mock_response_503.status = 503

        # Create async context managers for each response
        def make_context_manager(response):
            cm = AsyncMock()
            cm.__aenter__ = AsyncMock(return_value=response)
            cm.__aexit__ = AsyncMock(return_value=None)
            return cm

        mock_session = AsyncMock()
        # First attempt returns 503, second succeeds
        mock_session.get = MagicMock(
            side_effect=[
                make_context_manager(mock_response_503),
                make_context_manager(mock_response_success),
            ]
        )
        mock_session.closed = False

        client._session = mock_session

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await client._make_request("testplayer")

            # Should have retried once (1 sleep call)
            assert mock_sleep.call_count == 1
            # Verify exponential backoff delay: 1.0s
            assert mock_sleep.call_args_list[0][0][0] == pytest.approx(
                1.0, rel=0.1
            )
            # Should have made 2 requests total (1 failure + 1 success)
            assert mock_session.get.call_count == 2
            # Should return successful response
            assert result["name"] == "TestPlayer"

    async def test_backoff_delay_respects_max_backoff(self, client):
        """Test that backoff delays are capped at MAX_BACKOFF."""
        # Temporarily set MAX_RETRIES to a high value to test max backoff
        original_max_retries = client.MAX_RETRIES
        original_max_backoff = client.MAX_BACKOFF
        client.MAX_RETRIES = 10  # More retries to test max backoff
        client.MAX_BACKOFF = 60.0

        mock_response_504 = AsyncMock()
        mock_response_504.status = 504

        # Create async context manager for 504 response
        def make_context_manager(response):
            cm = AsyncMock()
            cm.__aenter__ = AsyncMock(return_value=response)
            cm.__aexit__ = AsyncMock(return_value=None)
            return cm

        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            return_value=make_context_manager(mock_response_504)
        )
        mock_session.closed = False

        client._session = mock_session

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(APIUnavailableError):
                await client._make_request("testplayer")

            # Check that delays don't exceed MAX_BACKOFF
            for call in mock_sleep.call_args_list:
                delay = call[0][0]
                assert (
                    delay <= client.MAX_BACKOFF
                ), f"Delay {delay} exceeds MAX_BACKOFF {client.MAX_BACKOFF}"

        # Restore original values
        client.MAX_RETRIES = original_max_retries
        client.MAX_BACKOFF = original_max_backoff


@pytest.mark.integration
class TestOSRSAPIClientIntegration:
    """Integration tests for OSRS API client (requires network access)."""

    @pytest.fixture
    async def client(self):
        """Create an OSRS API client for integration testing."""
        client = OSRSAPIClient()
        yield client
        await client.close()

    @pytest.mark.slow
    async def test_fetch_real_player_data(self, client):
        """Test fetching data for a real player (slow test)."""
        # Using a well-known player that should exist
        # Note: This test may fail if the player doesn't exist or API is down
        try:
            result = await client.fetch_player_hiscores("Lynx Titan")
            assert isinstance(result, HiscoreData)
            assert result.overall is not None
            assert len(result.skills) > 0
        except OSRSPlayerNotFoundError:
            # Player might not exist anymore, skip test
            pytest.skip("Test player not found")
        except (APIUnavailableError, OSRSAPIError):
            # API might be down, skip test
            pytest.skip("OSRS API unavailable")

    @pytest.mark.slow
    async def test_fetch_nonexistent_player(self, client):
        """Test fetching data for a nonexistent player."""
        with pytest.raises(OSRSPlayerNotFoundError):
            await client.fetch_player_hiscores(
                "ThisPlayerShouldNotExist123456789"
            )
