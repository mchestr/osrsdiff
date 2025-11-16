"""Service for classifying OSRS player game modes."""

import logging
from typing import Optional, Tuple

from app.exceptions import (
    APIUnavailableError,
    OSRSAPIError,
    OSRSPlayerNotFoundError,
    RateLimitError,
)
from app.models.player_type import PlayerType
from app.services.osrs_api import OSRSAPIClient

logger = logging.getLogger(__name__)


class PlayerTypeClassificationError(Exception):
    """Error during player type classification."""

    pass


class PlayerTypeClassifier:
    """Service for classifying player game modes using OSRS hiscores."""

    def __init__(self, osrs_api_client: OSRSAPIClient):
        """
        Initialize the player type classifier.

        Args:
            osrs_api_client: OSRS API client instance
        """
        self.osrs_api_client = osrs_api_client

    async def get_overall_experience(
        self, username: str, game_mode: PlayerType
    ) -> Tuple[Optional[int], Optional[Exception]]:
        """
        Get overall experience for a player from a specific game mode hiscores.

        Args:
            username: OSRS player username
            game_mode: Game mode to check

        Returns:
            Tuple of (experience value, error). Experience is -1 if player not found
            on that hiscores, None if error occurred, or the experience value.
            Error is None if successful, or the exception if an error occurred.
        """
        try:
            hiscore_data = await self.osrs_api_client.fetch_player_hiscores(
                username, game_mode
            )
            exp = hiscore_data.overall.get("experience")
            return (exp if exp is not None else -1, None)
        except OSRSPlayerNotFoundError:
            # Player not found on this hiscores
            return (-1, None)
        except (RateLimitError, APIUnavailableError, OSRSAPIError) as e:
            # API error - return the exception
            return (None, e)

    async def find_ironman_subtype(
        self, username: str
    ) -> Tuple[Optional[PlayerType], Optional[int], Optional[Exception]]:
        """
        Find the specific ironman subtype (ironman, hardcore, or ultimate).

        Args:
            username: OSRS player username

        Returns:
            Tuple of (player_type, experience, error). If error is not None,
            the classification failed.
        """
        # Check ironman hiscores
        ironman_exp, ironman_error = await self.get_overall_experience(
            username, PlayerType.IRONMAN
        )

        if ironman_error is not None:
            return (None, None, ironman_error)

        if ironman_exp == -1:
            # Not an ironman
            return (
                None,
                None,
                PlayerTypeClassificationError("NOT_AN_IRONMAN"),
            )

        # Check hardcore hiscores
        hardcore_exp, hardcore_error = await self.get_overall_experience(
            username, PlayerType.HARDCORE
        )

        if hardcore_error is not None:
            return (None, None, hardcore_error)

        # If hardcore exp exists (not -1) and is >= ironman exp, they're hardcore
        if (
            hardcore_exp is not None
            and hardcore_exp != -1
            and ironman_exp is not None
            and hardcore_exp >= ironman_exp
        ):
            return (PlayerType.HARDCORE, hardcore_exp, None)

        # Check ultimate hiscores
        ultimate_exp, ultimate_error = await self.get_overall_experience(
            username, PlayerType.ULTIMATE
        )

        if ultimate_error is not None:
            return (None, None, ultimate_error)

        # If ultimate exp exists (not -1) and is >= ironman exp, they're ultimate
        if (
            ultimate_exp is not None
            and ultimate_exp != -1
            and ironman_exp is not None
            and ultimate_exp >= ironman_exp
        ):
            return (PlayerType.ULTIMATE, ultimate_exp, None)

        # Default to regular ironman
        return (PlayerType.IRONMAN, ironman_exp, None)

    async def classify_player_type(
        self, username: str
    ) -> Tuple[PlayerType, Optional[Exception]]:
        """
        Classify a player's game mode using the same logic as Wise Old Man.

        The logic:
        1. Check regular hiscores experience
        2. Check ironman hiscores (and subtypes)
        3. If player is on ironman hiscores but regular exp > ironman exp, they've de-ironed
        4. If player is not on any hiscores, raise error

        Args:
            username: OSRS player username

        Returns:
            Tuple of (player_type, error). If error is not None, classification failed.

        Raises:
            PlayerTypeClassificationError: If classification fails
        """
        # Get regular hiscores experience
        regular_exp, regular_error = await self.get_overall_experience(
            username, PlayerType.REGULAR
        )

        if regular_error is not None:
            return (PlayerType.REGULAR, regular_error)

        # Try to find ironman subtype
        ironman_type, ironman_exp, ironman_error = (
            await self.find_ironman_subtype(username)
        )

        if ironman_type is not None:
            # Player is on ironman hiscores
            # Check if they've de-ironed (regular exp > ironman exp)
            if (
                regular_exp is not None
                and ironman_exp is not None
                and regular_exp > ironman_exp
            ):
                return (PlayerType.REGULAR, None)
            return (ironman_type, None)

        # Not an ironman - check if error occurred
        if ironman_error is not None:
            # If it's a "NOT_AN_IRONMAN" error, that's fine - continue
            if isinstance(ironman_error, PlayerTypeClassificationError):
                # Check if player exists on regular hiscores
                if regular_exp == -1:
                    # Player doesn't exist on any hiscores
                    return (
                        PlayerType.REGULAR,
                        PlayerTypeClassificationError(
                            "Player not found on any hiscores"
                        ),
                    )
                return (PlayerType.REGULAR, None)
            # Other error occurred
            return (PlayerType.REGULAR, ironman_error)

        # If regular exp is -1, player doesn't exist
        if regular_exp == -1:
            return (
                PlayerType.REGULAR,
                PlayerTypeClassificationError(
                    "Player not found on any hiscores"
                ),
            )

        return (PlayerType.REGULAR, None)

    async def assert_player_type(
        self, username: str, current_type: Optional[PlayerType] = None
    ) -> Tuple[PlayerType, bool]:
        """
        Assert/verify a player's game mode type.

        Args:
            username: OSRS player username
            current_type: Current player type if known (for comparison)

        Returns:
            Tuple of (player_type, changed). Changed is True if the type changed
            from current_type, False otherwise.

        Raises:
            PlayerTypeClassificationError: If classification fails
        """
        player_type, error = await self.classify_player_type(username)

        if error is not None:
            raise error

        changed = current_type is not None and current_type != player_type

        return (player_type, changed)
