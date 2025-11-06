"""Player management service with CRUD operations."""

import logging
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.player import Player
from app.services.osrs_api import (
    OSRSAPIClient,
    OSRSAPIError,
)
from app.services.osrs_api import (
    PlayerNotFoundError as OSRSPlayerNotFoundError,
)

if TYPE_CHECKING:
    from app.services.scheduler import PlayerScheduleManager

logger = logging.getLogger(__name__)


class PlayerServiceError(Exception):
    """Base exception for player service errors."""

    pass


class PlayerAlreadyExistsError(PlayerServiceError):
    """Raised when trying to add a player that already exists."""

    pass


class PlayerNotFoundServiceError(PlayerServiceError):
    """Raised when a requested player is not found in the database."""

    pass


class InvalidUsernameError(PlayerServiceError):
    """Raised when a username is invalid."""

    pass


class PlayerService:
    """Service for managing OSRS players in the tracking system."""

    def __init__(
        self,
        db_session: AsyncSession,
        osrs_api_client: OSRSAPIClient,
        schedule_manager: Optional["PlayerScheduleManager"] = None,
    ):
        """
        Initialize the player service.

        Args:
            db_session: Database session for operations
            osrs_api_client: OSRS API client for validation
            schedule_manager: Optional schedule manager for TaskIQ integration
        """
        self.db_session = db_session
        self.osrs_api_client = osrs_api_client
        self.schedule_manager = schedule_manager

    async def add_player(self, username: str) -> Player:
        """
        Add a new player to the tracking system.

        This method validates the username format, checks if the player exists
        in OSRS hiscores, prevents duplicates, and creates a new Player entity.

        Args:
            username: OSRS player username to add

        Returns:
            Player: The created player entity

        Raises:
            InvalidUsernameError: If username format is invalid
            PlayerAlreadyExistsError: If player already exists in system
            OSRSPlayerNotFoundError: If player doesn't exist in OSRS hiscores
            OSRSAPIError: If OSRS API is unavailable or other API errors
            PlayerServiceError: For other service-level errors
        """
        if not username:
            raise InvalidUsernameError("Username cannot be empty")

        # Normalize username (strip whitespace)
        username = username.strip()

        # Validate username format
        if not Player.validate_username(username):
            raise InvalidUsernameError(
                f"Invalid username format: '{username}'. "
                "Username must be 1-12 characters, contain only letters, numbers, "
                "spaces, hyphens, and underscores, and not start/end with spaces."
            )

        logger.info(f"Adding player: {username}")

        try:
            # Check if player already exists in our database
            existing_player = await self.get_player(username)
            if existing_player:
                raise PlayerAlreadyExistsError(
                    f"Player '{username}' is already being tracked"
                )

            # Verify player exists in OSRS hiscores
            logger.debug(
                f"Verifying player exists in OSRS hiscores: {username}"
            )
            player_exists = await self.osrs_api_client.check_player_exists(
                username
            )
            if not player_exists:
                raise OSRSPlayerNotFoundError(
                    f"Player '{username}' not found in OSRS hiscores"
                )

            # Create new player entity
            new_player = Player(username=username)
            self.db_session.add(new_player)

            try:
                await self.db_session.commit()
                await self.db_session.refresh(new_player)

                # Create schedule for the new player if schedule manager is available
                if self.schedule_manager:
                    try:
                        from app.services.scheduler import (
                            PlayerScheduleManagerError,
                        )

                        schedule_id = (
                            await self.schedule_manager.schedule_player(
                                new_player
                            )
                        )
                        new_player.schedule_id = schedule_id
                        await self.db_session.commit()
                        logger.info(
                            f"Created schedule {schedule_id} for new player {username}"
                        )
                    except PlayerScheduleManagerError as e:
                        logger.error(
                            f"Failed to create schedule for new player {username}: {e}. "
                            "Player created but scheduling failed."
                        )
                        # Don't fail player creation if scheduling fails

                logger.info(
                    f"Successfully added player: {username} (ID: {new_player.id})"
                )
                return new_player

            except IntegrityError as e:
                await self.db_session.rollback()
                # This could happen if another process added the same player concurrently
                logger.warning(
                    f"Integrity error adding player {username}: {e}"
                )
                raise PlayerAlreadyExistsError(
                    f"Player '{username}' was already added by another process"
                )

        except (OSRSPlayerNotFoundError, OSRSAPIError):
            # Re-raise OSRS API related errors
            raise
        except (PlayerAlreadyExistsError, InvalidUsernameError):
            # Re-raise service-level errors
            raise
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Unexpected error adding player {username}: {e}")
            raise PlayerServiceError(f"Failed to add player '{username}': {e}")

    async def get_player(self, username: str) -> Optional[Player]:
        """
        Get a player by username.

        Args:
            username: OSRS player username

        Returns:
            Optional[Player]: Player entity if found, None otherwise

        Raises:
            PlayerServiceError: For database or other service errors
        """
        if not username:
            return None

        username = username.strip()

        try:
            logger.debug(f"Getting player: {username}")

            # Query for player by username (case-insensitive)
            stmt = select(Player).where(Player.username.ilike(username))
            result = await self.db_session.execute(stmt)
            player = result.scalar_one_or_none()

            if player:
                logger.debug(f"Found player: {username} (ID: {player.id})")
            else:
                logger.debug(f"Player not found: {username}")

            return player

        except Exception as e:
            logger.error(f"Error getting player {username}: {e}")
            raise PlayerServiceError(f"Failed to get player '{username}': {e}")

    async def list_players(self, active_only: bool = True) -> List[Player]:
        """
        List all players in the tracking system.

        Args:
            active_only: If True, only return active players. If False, return all players.

        Returns:
            List[Player]: List of player entities

        Raises:
            PlayerServiceError: For database or other service errors
        """
        try:
            logger.debug(f"Listing players (active_only={active_only})")

            # Build query
            stmt = select(Player).order_by(Player.username)
            if active_only:
                stmt = stmt.where(Player.is_active.is_(True))

            result = await self.db_session.execute(stmt)
            players = result.scalars().all()

            logger.debug(f"Found {len(players)} players")
            return list(players)

        except Exception as e:
            logger.error(f"Error listing players: {e}")
            raise PlayerServiceError(f"Failed to list players: {e}")

    async def remove_player(self, username: str) -> bool:
        """
        Remove a player from the tracking system.

        This method will delete the player and all associated hiscore records
        due to the cascade delete relationship.

        Args:
            username: OSRS player username to remove

        Returns:
            bool: True if player was removed, False if player was not found

        Raises:
            PlayerServiceError: For database or other service errors
        """
        if not username:
            return False

        username = username.strip()

        try:
            logger.info(f"Removing player: {username}")

            # First check if player exists
            player = await self.get_player(username)
            if not player:
                logger.debug(f"Player not found for removal: {username}")
                return False

            # Clean up schedule before deleting player
            if self.schedule_manager and player.schedule_id:
                try:
                    from app.services.scheduler import (
                        PlayerScheduleManagerError,
                    )

                    await self.schedule_manager.unschedule_player(player)
                    logger.info(f"Cleaned up schedule for player {username}")
                except PlayerScheduleManagerError as e:
                    logger.warning(
                        f"Failed to clean up schedule for player {username}: {e}. "
                        "Proceeding with player deletion."
                    )

            # Delete the player (cascade will handle hiscore records)
            stmt = delete(Player).where(Player.username.ilike(username))
            result = await self.db_session.execute(stmt)
            await self.db_session.commit()

            removed = bool(getattr(result, "rowcount", 0) > 0)
            if removed:
                logger.info(f"Successfully removed player: {username}")
            else:
                logger.warning(
                    f"Player {username} was not removed (may have been deleted concurrently)"
                )

            return removed

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Error removing player {username}: {e}")
            raise PlayerServiceError(
                f"Failed to remove player '{username}': {e}"
            )

    async def deactivate_player(self, username: str) -> bool:
        """
        Deactivate a player (soft delete) instead of removing completely.

        This sets is_active to False, which will stop automatic fetching
        but preserve historical data.

        Args:
            username: OSRS player username to deactivate

        Returns:
            bool: True if player was deactivated, False if player was not found

        Raises:
            PlayerServiceError: For database or other service errors
        """
        if not username:
            return False

        username = username.strip()

        try:
            logger.info(f"Deactivating player: {username}")

            player = await self.get_player(username)
            if not player:
                logger.debug(f"Player not found for deactivation: {username}")
                return False

            if not player.is_active:
                logger.debug(f"Player {username} is already inactive")
                return True

            # Unschedule the player when deactivating
            if self.schedule_manager and player.schedule_id:
                try:
                    from app.services.scheduler import (
                        PlayerScheduleManagerError,
                    )

                    await self.schedule_manager.unschedule_player(player)
                    player.schedule_id = None
                    logger.info(
                        f"Unscheduled player {username} during deactivation"
                    )
                except PlayerScheduleManagerError as e:
                    logger.warning(
                        f"Failed to unschedule player {username} during deactivation: {e}. "
                        "Proceeding with deactivation."
                    )

            player.is_active = False
            await self.db_session.commit()

            logger.info(f"Successfully deactivated player: {username}")
            return True

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Error deactivating player {username}: {e}")
            raise PlayerServiceError(
                f"Failed to deactivate player '{username}': {e}"
            )

    async def reactivate_player(self, username: str) -> bool:
        """
        Reactivate a previously deactivated player.

        Args:
            username: OSRS player username to reactivate

        Returns:
            bool: True if player was reactivated, False if player was not found

        Raises:
            PlayerServiceError: For database or other service errors
        """
        if not username:
            return False

        username = username.strip()

        try:
            logger.info(f"Reactivating player: {username}")

            player = await self.get_player(username)
            if not player:
                logger.debug(f"Player not found for reactivation: {username}")
                return False

            if player.is_active:
                logger.debug(f"Player {username} is already active")
                return True

            # Reschedule the player when reactivating
            if self.schedule_manager:
                try:
                    from app.services.scheduler import (
                        PlayerScheduleManagerError,
                    )

                    schedule_id = (
                        await self.schedule_manager.ensure_player_scheduled(
                            player
                        )
                    )
                    player.schedule_id = schedule_id
                    logger.info(
                        f"Rescheduled player {username} during reactivation"
                    )
                except PlayerScheduleManagerError as e:
                    logger.warning(
                        f"Failed to reschedule player {username} during reactivation: {e}. "
                        "Proceeding with reactivation."
                    )

            player.is_active = True
            await self.db_session.commit()

            logger.info(f"Successfully reactivated player: {username}")
            return True

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Error reactivating player {username}: {e}")
            raise PlayerServiceError(
                f"Failed to reactivate player '{username}': {e}"
            )

    async def update_player_fetch_interval(
        self, username: str, new_interval_minutes: int
    ) -> bool:
        """
        Update a player's fetch interval and reschedule their task.

        Args:
            username: OSRS player username to update
            new_interval_minutes: New fetch interval in minutes

        Returns:
            bool: True if interval was updated, False if player was not found

        Raises:
            PlayerServiceError: For database or other service errors
            ValueError: If the new interval is invalid
        """
        if not username:
            return False

        username = username.strip()

        # Validate the new interval
        if (
            not isinstance(new_interval_minutes, int)
            or new_interval_minutes < 1
        ):
            raise ValueError(
                f"Invalid fetch interval: {new_interval_minutes}. Must be a positive integer."
            )

        try:
            logger.info(
                f"Updating fetch interval for player {username} to {new_interval_minutes} minutes"
            )

            player = await self.get_player(username)
            if not player:
                logger.debug(
                    f"Player not found for interval update: {username}"
                )
                return False

            old_interval = player.fetch_interval_minutes
            if old_interval == new_interval_minutes:
                logger.debug(
                    f"Player {username} already has interval {new_interval_minutes} minutes"
                )
                return True

            # Update the interval
            player.fetch_interval_minutes = new_interval_minutes

            # Reschedule the player if they are active and we have a schedule manager
            if player.is_active and self.schedule_manager:
                try:
                    from app.services.scheduler import (
                        PlayerScheduleManagerError,
                    )

                    schedule_id = (
                        await self.schedule_manager.reschedule_player(player)
                    )
                    player.schedule_id = schedule_id
                    logger.info(
                        f"Rescheduled player {username} with new interval {new_interval_minutes} minutes"
                    )
                except PlayerScheduleManagerError as e:
                    logger.warning(
                        f"Failed to reschedule player {username} with new interval: {e}. "
                        "Interval updated but scheduling may be inconsistent."
                    )

            await self.db_session.commit()

            logger.info(
                f"Successfully updated fetch interval for {username}: {old_interval} -> {new_interval_minutes} minutes"
            )
            return True

        except Exception as e:
            await self.db_session.rollback()
            logger.error(
                f"Error updating fetch interval for player {username}: {e}"
            )
            raise PlayerServiceError(
                f"Failed to update fetch interval for player '{username}': {e}"
            )


async def get_player_service(
    db_session: AsyncSession, osrs_api_client: OSRSAPIClient
) -> PlayerService:
    """
    Dependency injection function for FastAPI.

    Args:
        db_session: Database session
        osrs_api_client: OSRS API client

    Returns:
        PlayerService: Configured player service instance
    """
    # Import here to avoid circular imports
    from app.services.scheduler import get_player_schedule_manager

    try:
        schedule_manager = await get_player_schedule_manager()
    except Exception as e:
        logger.warning(
            f"Failed to get schedule manager: {e}. Player service will work without scheduling."
        )
        schedule_manager = None

    return PlayerService(db_session, osrs_api_client, schedule_manager)
