"""Tests for OSRS API client service."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import ClientError

from app.services.osrs_api import (
    APIUnavailableError,
    HiscoreData,
    OSRSAPIClient,
    OSRSAPIError,
    PlayerNotFoundError,
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

    async def test_rate_limiting(self, client):
        """Test that rate limiting is enforced."""
        # Mock the session to avoid actual HTTP requests
        with patch.object(client, "_session") as mock_session:
            mock_session.closed = False

            start_time = asyncio.get_event_loop().time()

            # First request should not be delayed
            await client._enforce_rate_limit()
            first_time = asyncio.get_event_loop().time()

            # Second request should be delayed
            await client._enforce_rate_limit()
            second_time = asyncio.get_event_loop().time()

            # Should have waited at least the rate limit delay
            time_diff = second_time - first_time
            assert (
                time_diff >= client.RATE_LIMIT_DELAY - 0.1
            )  # Allow small timing variance

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
            mock_fetch.side_effect = PlayerNotFoundError("Player not found")

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
        except PlayerNotFoundError:
            # Player might not exist anymore, skip test
            pytest.skip("Test player not found")
        except (APIUnavailableError, OSRSAPIError):
            # API might be down, skip test
            pytest.skip("OSRS API unavailable")

    @pytest.mark.slow
    async def test_fetch_nonexistent_player(self, client):
        """Test fetching data for a nonexistent player."""
        with pytest.raises(PlayerNotFoundError):
            await client.fetch_player_hiscores(
                "ThisPlayerShouldNotExist123456789"
            )
