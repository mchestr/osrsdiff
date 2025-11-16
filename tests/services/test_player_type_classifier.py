"""Tests for player type classifier service."""

from unittest.mock import AsyncMock

import pytest

from app.exceptions import (
    APIUnavailableError,
    OSRSAPIError,
    OSRSPlayerNotFoundError,
)
from app.models.player_type import PlayerType
from app.services.osrs_api import HiscoreData
from app.services.player.type_classifier import (
    PlayerTypeClassificationError,
    PlayerTypeClassifier,
)


class TestPlayerTypeClassifier:
    """Test cases for PlayerTypeClassifier."""

    @pytest.fixture
    def mock_osrs_client(self):
        """Create a mock OSRS API client."""
        client = AsyncMock()
        return client

    @pytest.fixture
    def classifier(self, mock_osrs_client):
        """Create a classifier instance for testing."""
        return PlayerTypeClassifier(mock_osrs_client)

    def create_hiscore_data(
        self, overall_exp: int | None = None
    ) -> HiscoreData:
        """Helper to create HiscoreData with overall experience."""
        return HiscoreData(
            overall={"experience": overall_exp, "rank": None, "level": None},
            skills={},
            bosses={},
        )

    @pytest.mark.asyncio
    async def test_classify_regular_player(self, classifier, mock_osrs_client):
        """Test classifying a regular player."""
        # Regular hiscores has exp, ironman doesn't exist
        mock_osrs_client.fetch_player_hiscores.side_effect = [
            self.create_hiscore_data(1000000),  # Regular
            OSRSPlayerNotFoundError("test"),  # Ironman - not found
        ]

        player_type, error = await classifier.classify_player_type(
            "testplayer"
        )

        assert player_type == PlayerType.REGULAR
        assert error is None

    @pytest.mark.asyncio
    async def test_classify_ironman_player(self, classifier, mock_osrs_client):
        """Test classifying an ironman player."""
        # Both regular and ironman have exp, but ironman exp >= regular
        mock_osrs_client.fetch_player_hiscores.side_effect = [
            self.create_hiscore_data(500000),  # Regular
            self.create_hiscore_data(1000000),  # Ironman
            self.create_hiscore_data(800000),  # Hardcore (less than ironman)
            self.create_hiscore_data(600000),  # Ultimate (less than ironman)
        ]

        player_type, error = await classifier.classify_player_type("ironman")

        assert player_type == PlayerType.IRONMAN
        assert error is None

    @pytest.mark.asyncio
    async def test_classify_hardcore_player(
        self, classifier, mock_osrs_client
    ):
        """Test classifying a hardcore ironman player."""
        # Hardcore exp >= ironman exp
        mock_osrs_client.fetch_player_hiscores.side_effect = [
            self.create_hiscore_data(500000),  # Regular
            self.create_hiscore_data(1000000),  # Ironman
            self.create_hiscore_data(1200000),  # Hardcore (>= ironman)
            self.create_hiscore_data(800000),  # Ultimate (less than hardcore)
        ]

        player_type, error = await classifier.classify_player_type("hardcore")

        assert player_type == PlayerType.HARDCORE
        assert error is None

    @pytest.mark.asyncio
    async def test_classify_ultimate_player(
        self, classifier, mock_osrs_client
    ):
        """Test classifying an ultimate ironman player."""
        # Ultimate exp >= ironman exp
        mock_osrs_client.fetch_player_hiscores.side_effect = [
            self.create_hiscore_data(500000),  # Regular
            self.create_hiscore_data(1000000),  # Ironman
            self.create_hiscore_data(800000),  # Hardcore (less than ironman)
            self.create_hiscore_data(1200000),  # Ultimate (>= ironman)
        ]

        player_type, error = await classifier.classify_player_type("ultimate")

        assert player_type == PlayerType.ULTIMATE
        assert error is None

    @pytest.mark.asyncio
    async def test_classify_deironed_player(
        self, classifier, mock_osrs_client
    ):
        """Test detecting a de-ironed player (regular exp > ironman exp)."""
        # Regular exp is higher than ironman exp - player has de-ironed
        # find_ironman_subtype still checks hardcore and ultimate even if ironman exists
        mock_osrs_client.fetch_player_hiscores.side_effect = [
            self.create_hiscore_data(2000000),  # Regular (higher)
            self.create_hiscore_data(1000000),  # Ironman (lower)
            self.create_hiscore_data(800000),  # Hardcore (less than ironman)
            self.create_hiscore_data(600000),  # Ultimate (less than ironman)
        ]

        player_type, error = await classifier.classify_player_type("deironed")

        assert player_type == PlayerType.REGULAR
        assert error is None

    @pytest.mark.asyncio
    async def test_classify_player_not_found(
        self, classifier, mock_osrs_client
    ):
        """Test classifying a player that doesn't exist."""
        # Player not found on any hiscores
        mock_osrs_client.fetch_player_hiscores.side_effect = [
            OSRSPlayerNotFoundError("test"),  # Regular - not found
            OSRSPlayerNotFoundError("test"),  # Ironman - not found
        ]

        player_type, error = await classifier.classify_player_type(
            "nonexistent"
        )

        assert player_type == PlayerType.REGULAR
        assert isinstance(error, PlayerTypeClassificationError)
        assert "not found" in str(error).lower()

    @pytest.mark.asyncio
    async def test_classify_api_error(self, classifier, mock_osrs_client):
        """Test handling API errors during classification."""
        mock_osrs_client.fetch_player_hiscores.side_effect = (
            APIUnavailableError("API unavailable")
        )

        player_type, error = await classifier.classify_player_type(
            "testplayer"
        )

        assert player_type == PlayerType.REGULAR
        assert isinstance(error, APIUnavailableError)

    @pytest.mark.asyncio
    async def test_assert_player_type_changed(
        self, classifier, mock_osrs_client
    ):
        """Test assert_player_type when type changes."""
        mock_osrs_client.fetch_player_hiscores.side_effect = [
            self.create_hiscore_data(1000000),  # Regular
            OSRSPlayerNotFoundError("test"),  # Ironman - not found
        ]

        player_type, changed = await classifier.assert_player_type(
            "testplayer", current_type=PlayerType.IRONMAN
        )

        assert player_type == PlayerType.REGULAR
        assert changed is True

    @pytest.mark.asyncio
    async def test_assert_player_type_unchanged(
        self, classifier, mock_osrs_client
    ):
        """Test assert_player_type when type doesn't change."""
        mock_osrs_client.fetch_player_hiscores.side_effect = [
            self.create_hiscore_data(1000000),  # Regular
            OSRSPlayerNotFoundError("test"),  # Ironman - not found
        ]

        player_type, changed = await classifier.assert_player_type(
            "testplayer", current_type=PlayerType.REGULAR
        )

        assert player_type == PlayerType.REGULAR
        assert changed is False

    @pytest.mark.asyncio
    async def test_get_overall_experience_success(
        self, classifier, mock_osrs_client
    ):
        """Test getting overall experience successfully."""
        mock_osrs_client.fetch_player_hiscores.return_value = (
            self.create_hiscore_data(1000000)
        )

        exp, error = await classifier.get_overall_experience(
            "testplayer", PlayerType.REGULAR
        )

        assert exp == 1000000
        assert error is None

    @pytest.mark.asyncio
    async def test_get_overall_experience_not_found(
        self, classifier, mock_osrs_client
    ):
        """Test getting overall experience when player not found."""
        mock_osrs_client.fetch_player_hiscores.side_effect = (
            OSRSPlayerNotFoundError("test")
        )

        exp, error = await classifier.get_overall_experience(
            "testplayer", PlayerType.REGULAR
        )

        assert exp == -1
        assert error is None

    @pytest.mark.asyncio
    async def test_get_overall_experience_api_error(
        self, classifier, mock_osrs_client
    ):
        """Test getting overall experience when API error occurs."""
        mock_osrs_client.fetch_player_hiscores.side_effect = (
            APIUnavailableError("API unavailable")
        )

        exp, error = await classifier.get_overall_experience(
            "testplayer", PlayerType.REGULAR
        )

        assert exp is None
        assert isinstance(error, APIUnavailableError)
