"""Tests for player service."""

from unittest.mock import AsyncMock, Mock

import pytest

from app.exceptions import OSRSPlayerNotFoundError, PlayerNotFoundError
from app.models.player import Player
from app.services.osrs_api import (
    APIUnavailableError,
    OSRSAPIClient,
    OSRSAPIError,
)
from app.services.player import (
    InvalidUsernameError,
    PlayerAlreadyExistsError,
    PlayerService,
    PlayerServiceError,
)


class TestPlayerService:
    """Test cases for PlayerService."""

    @pytest.fixture
    def mock_osrs_client(self):
        """Create a mock OSRS API client."""
        client = AsyncMock(spec=OSRSAPIClient)
        return client

    @pytest.fixture
    def player_service(self, test_session, mock_osrs_client):
        """Create a player service instance for testing."""
        return PlayerService(test_session, mock_osrs_client)

    @pytest.mark.asyncio
    async def test_add_player_success(self, player_service, mock_osrs_client):
        """Test successfully adding a new player."""
        username = "testplayer"
        mock_osrs_client.check_player_exists.return_value = True

        result = await player_service.add_player(username)

        assert isinstance(result, Player)
        assert result.username == username
        assert result.is_active is True
        assert result.fetch_interval_minutes == 1440
        mock_osrs_client.check_player_exists.assert_called_once_with(username)

    @pytest.mark.asyncio
    async def test_add_player_invalid_username_empty(self, player_service):
        """Test adding player with empty username."""
        with pytest.raises(
            InvalidUsernameError, match="Username cannot be empty"
        ):
            await player_service.add_player("")

    @pytest.mark.asyncio
    async def test_add_player_invalid_username_format(self, player_service):
        """Test adding player with invalid username format."""
        invalid_usernames = [
            "toolongname123",  # Too long (>12 chars)
            "user@name",  # Invalid character
            "user#name",  # Invalid character
            "user$name",  # Invalid character
            "",  # Empty string
        ]

        for username in invalid_usernames:
            with pytest.raises(InvalidUsernameError):
                await player_service.add_player(username)

    @pytest.mark.asyncio
    async def test_add_player_not_found_in_osrs(
        self, player_service, mock_osrs_client
    ):
        """Test adding player that doesn't exist in OSRS hiscores."""
        username = "nonexistent"
        mock_osrs_client.check_player_exists.return_value = False

        with pytest.raises(OSRSPlayerNotFoundError):
            await player_service.add_player(username)

    @pytest.mark.asyncio
    async def test_add_player_already_exists(
        self, player_service, mock_osrs_client
    ):
        """Test adding player that already exists in database."""
        username = "existing"
        mock_osrs_client.check_player_exists.return_value = True

        # Add player first time
        await player_service.add_player(username)

        # Try to add same player again
        with pytest.raises(PlayerAlreadyExistsError):
            await player_service.add_player(username)

    @pytest.mark.asyncio
    async def test_add_player_osrs_api_error(
        self, player_service, mock_osrs_client
    ):
        """Test adding player when OSRS API is unavailable."""
        from app.services.player import PlayerServiceError

        username = "testplayer"
        mock_osrs_client.check_player_exists.side_effect = APIUnavailableError(
            "API down"
        )

        with pytest.raises(PlayerServiceError) as exc_info:
            await player_service.add_player(username)

        assert "Failed to add player" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_player_exists(self, player_service, mock_osrs_client):
        """Test getting an existing player."""
        username = "testplayer"
        mock_osrs_client.check_player_exists.return_value = True

        # Add player first
        added_player = await player_service.add_player(username)

        # Get the player
        result = await player_service.get_player(username)

        assert result is not None
        assert result.id == added_player.id
        assert result.username == username

    @pytest.mark.asyncio
    async def test_get_player_not_exists(self, player_service):
        """Test getting a non-existent player."""
        result = await player_service.get_player("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_player_empty_username(self, player_service):
        """Test getting player with empty username."""
        result = await player_service.get_player("")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_player_case_insensitive(
        self, player_service, mock_osrs_client
    ):
        """Test getting player with different case."""
        username = "TestPlayer"
        mock_osrs_client.check_player_exists.return_value = True

        # Add player with mixed case
        await player_service.add_player(username)

        # Get with different case
        result = await player_service.get_player("testplayer")
        assert result is not None
        assert result.username == username

    @pytest.mark.asyncio
    async def test_list_players_empty(self, player_service):
        """Test listing players when none exist."""
        result = await player_service.list_players()
        assert result == []

    @pytest.mark.asyncio
    async def test_list_players_with_data(
        self, player_service, mock_osrs_client
    ):
        """Test listing players with data."""
        usernames = ["player1", "player2", "player3"]
        mock_osrs_client.check_player_exists.return_value = True

        # Add multiple players
        for username in usernames:
            await player_service.add_player(username)

        # List all players
        result = await player_service.list_players()

        assert len(result) == 3
        result_usernames = [p.username for p in result]
        assert sorted(result_usernames) == sorted(usernames)

    @pytest.mark.asyncio
    async def test_list_players_active_only(
        self, player_service, mock_osrs_client
    ):
        """Test listing only active players."""
        mock_osrs_client.check_player_exists.return_value = True

        # Add players
        player1 = await player_service.add_player("active")
        player2 = await player_service.add_player("inactive")

        # Deactivate one player
        await player_service.deactivate_player("inactive")

        # List active players only
        result = await player_service.list_players(active_only=True)
        assert len(result) == 1
        assert result[0].username == "active"

        # List all players
        result_all = await player_service.list_players(active_only=False)
        assert len(result_all) == 2

    @pytest.mark.asyncio
    async def test_remove_player_success(
        self, player_service, mock_osrs_client
    ):
        """Test successfully removing a player."""
        username = "testplayer"
        mock_osrs_client.check_player_exists.return_value = True

        # Add player first
        await player_service.add_player(username)

        # Remove the player
        result = await player_service.remove_player(username)
        assert result is True

        # Verify player is gone
        player = await player_service.get_player(username)
        assert player is None

    @pytest.mark.asyncio
    async def test_remove_player_not_exists(self, player_service):
        """Test removing a non-existent player."""
        result = await player_service.remove_player("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_player_empty_username(self, player_service):
        """Test removing player with empty username."""
        result = await player_service.remove_player("")
        assert result is False

    @pytest.mark.asyncio
    async def test_deactivate_player_success(
        self, player_service, mock_osrs_client
    ):
        """Test successfully deactivating a player."""
        username = "testplayer"
        mock_osrs_client.check_player_exists.return_value = True

        # Add player first
        await player_service.add_player(username)

        # Deactivate the player
        result = await player_service.deactivate_player(username)
        assert result is True

        # Verify player is deactivated
        player = await player_service.get_player(username)
        assert player is not None
        assert player.is_active is False

    @pytest.mark.asyncio
    async def test_deactivate_player_not_exists(self, player_service):
        """Test deactivating a non-existent player."""
        result = await player_service.deactivate_player("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_deactivate_player_already_inactive(
        self, player_service, mock_osrs_client
    ):
        """Test deactivating an already inactive player."""
        username = "testplayer"
        mock_osrs_client.check_player_exists.return_value = True

        # Add and deactivate player
        await player_service.add_player(username)
        await player_service.deactivate_player(username)

        # Try to deactivate again
        result = await player_service.deactivate_player(username)
        assert result is True  # Should still return True

    @pytest.mark.asyncio
    async def test_reactivate_player_success(
        self, player_service, mock_osrs_client
    ):
        """Test successfully reactivating a player."""
        username = "testplayer"
        mock_osrs_client.check_player_exists.return_value = True

        # Add and deactivate player
        await player_service.add_player(username)
        await player_service.deactivate_player(username)

        # Reactivate the player
        result = await player_service.reactivate_player(username)
        assert result is True

        # Verify player is active
        player = await player_service.get_player(username)
        assert player is not None
        assert player.is_active is True

    @pytest.mark.asyncio
    async def test_reactivate_player_not_exists(self, player_service):
        """Test reactivating a non-existent player."""
        result = await player_service.reactivate_player("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_reactivate_player_already_active(
        self, player_service, mock_osrs_client
    ):
        """Test reactivating an already active player."""
        username = "testplayer"
        mock_osrs_client.check_player_exists.return_value = True

        # Add player (active by default)
        await player_service.add_player(username)

        # Try to reactivate
        result = await player_service.reactivate_player(username)
        assert result is True  # Should still return True

    @pytest.mark.asyncio
    async def test_username_normalization(
        self, player_service, mock_osrs_client
    ):
        """Test that usernames are properly normalized (trimmed)."""
        username = "  testplayer  "
        normalized = "testplayer"
        mock_osrs_client.check_player_exists.return_value = True

        # Add player with whitespace
        result = await player_service.add_player(username)
        assert result.username == normalized

        # Get player with whitespace
        player = await player_service.get_player(username)
        assert player is not None
        assert player.username == normalized

    @pytest.mark.asyncio
    async def test_add_player_username_with_internal_spaces(
        self, player_service, mock_osrs_client
    ):
        """Test adding player with internal spaces (should be valid)."""
        username = "test player"
        mock_osrs_client.check_player_exists.return_value = True

        result = await player_service.add_player(username)
        assert result.username == username
