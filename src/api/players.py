"""Player management API endpoints."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import require_auth
from src.models.base import get_db_session
from src.models.hiscore import HiscoreRecord
from src.models.player import Player
from src.services.osrs_api import (
    OSRSAPIClient,
    OSRSAPIError,
)
from src.services.osrs_api import (
    PlayerNotFoundError as OSRSPlayerNotFoundError,
)
from src.services.osrs_api import (
    get_osrs_api_client,
)
from src.services.player import (
    InvalidUsernameError,
    PlayerAlreadyExistsError,
    PlayerNotFoundServiceError,
    PlayerService,
)

logger = logging.getLogger(__name__)


# Request/Response models
class PlayerCreateRequest(BaseModel):
    """Request model for creating a new player."""

    username: str = Field(
        ...,
        min_length=1,
        max_length=12,
        description="OSRS player username (1-12 characters)",
    )


class PlayerResponse(BaseModel):
    """Response model for player data."""

    id: int
    username: str
    created_at: str
    last_fetched: str | None
    is_active: bool
    fetch_interval_minutes: int
    game_mode: str

    @classmethod
    def from_player(cls, player: Player) -> "PlayerResponse":
        """Create response model from Player entity."""
        return cls(
            id=player.id,
            username=player.username,
            created_at=player.created_at.isoformat(),
            last_fetched=(
                player.last_fetched.isoformat()
                if player.last_fetched
                else None
            ),
            is_active=player.is_active,
            fetch_interval_minutes=player.fetch_interval_minutes,
            game_mode=player.game_mode.value,
        )


class PlayersListResponse(BaseModel):
    """Response model for listing players."""

    players: List[PlayerResponse]
    total_count: int


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


class FetchTriggerResponse(BaseModel):
    """Response model for manual fetch trigger."""

    task_id: str
    username: str
    message: str
    estimated_completion_seconds: int
    status: str = "enqueued"


class PlayerMetadataResponse(BaseModel):
    """Response model for player metadata and admin information."""

    id: int
    username: str
    created_at: str
    last_fetched: str | None
    is_active: bool
    fetch_interval_minutes: int
    game_mode: str
    total_records: int = Field(description="Total number of hiscore records")
    first_record: str | None = Field(
        description="Timestamp of first hiscore record"
    )
    latest_record: str | None = Field(
        description="Timestamp of latest hiscore record"
    )
    records_last_24h: int = Field(
        description="Records created in last 24 hours"
    )
    records_last_7d: int = Field(description="Records created in last 7 days")
    avg_fetch_frequency_hours: float | None = Field(
        description="Average time between fetches in hours"
    )

    @classmethod
    def from_player_with_metadata(
        cls, player: Player, metadata: Dict[str, Any]
    ) -> "PlayerMetadataResponse":
        """Create response model from Player entity with metadata."""
        return cls(
            id=player.id,
            username=player.username,
            created_at=player.created_at.isoformat(),
            last_fetched=(
                player.last_fetched.isoformat()
                if player.last_fetched
                else None
            ),
            is_active=player.is_active,
            fetch_interval_minutes=player.fetch_interval_minutes,
            game_mode=player.game_mode.value,
            total_records=metadata.get("total_records", 0),
            first_record=metadata.get("first_record"),
            latest_record=metadata.get("latest_record"),
            records_last_24h=metadata.get("records_last_24h", 0),
            records_last_7d=metadata.get("records_last_7d", 0),
            avg_fetch_frequency_hours=metadata.get(
                "avg_fetch_frequency_hours"
            ),
        )


# Router
router = APIRouter(prefix="/players", tags=["players"])


async def get_player_service(
    db_session: AsyncSession = Depends(get_db_session),
    osrs_api_client: OSRSAPIClient = Depends(get_osrs_api_client),
) -> PlayerService:
    """Dependency injection for PlayerService."""
    return PlayerService(db_session, osrs_api_client)


@router.post(
    "", response_model=PlayerResponse, status_code=status.HTTP_201_CREATED
)
async def add_player(
    request: PlayerCreateRequest,
    player_service: PlayerService = Depends(get_player_service),
    current_user: Dict[str, Any] = Depends(require_auth),
) -> PlayerResponse:
    """
    Add a new player to the tracking system.

    This endpoint validates the username, checks if the player exists in OSRS hiscores,
    prevents duplicates, and creates a new Player entity. It also triggers an initial
    fetch task to populate baseline statistics.

    Args:
        request: Player creation request with username
        player_service: Player service dependency
        current_user: Authenticated user information

    Returns:
        PlayerResponse: Created player information

    Raises:
        400 Bad Request: Invalid username format
        404 Not Found: Player not found in OSRS hiscores
        409 Conflict: Player already exists in system
        502 Bad Gateway: OSRS API unavailable
        500 Internal Server Error: Other service errors
    """
    try:
        logger.info(
            f"User {current_user.get('username')} adding player: {request.username}"
        )

        # Add player to tracking system
        player = await player_service.add_player(request.username)

        # Trigger initial fetch task
        try:
            from src.workers.tasks import fetch_player_hiscores_task

            await fetch_player_hiscores_task.kiq(player.username)
            logger.info(
                f"Triggered initial fetch task for player {player.username}"
            )
        except Exception as e:
            logger.warning(
                f"Failed to trigger initial fetch for {player.username}: {e}"
            )
            # Don't fail the player creation if fetch trigger fails

        logger.info(
            f"Successfully added player {player.username} (ID: {player.id})"
        )

        return PlayerResponse.from_player(player)

    except InvalidUsernameError as e:
        logger.warning(f"Invalid username format: {request.username} - {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    except PlayerAlreadyExistsError as e:
        logger.warning(f"Player already exists: {request.username} - {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e)
        )
    except OSRSPlayerNotFoundError as e:
        logger.warning(
            f"Player not found in OSRS hiscores: {request.username} - {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    except OSRSAPIError as e:
        logger.error(f"OSRS API error for player {request.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OSRS API unavailable: {e}",
        )
    except Exception as e:
        logger.error(f"Unexpected error adding player {request.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while adding player",
        )


@router.delete("/{username}", response_model=MessageResponse)
async def remove_player(
    username: str,
    player_service: PlayerService = Depends(get_player_service),
    current_user: Dict[str, Any] = Depends(require_auth),
) -> MessageResponse:
    """
    Remove a player from the tracking system.

    This endpoint removes the player and all associated hiscore records
    from the database. This action cannot be undone.

    Args:
        username: OSRS player username to remove
        player_service: Player service dependency
        current_user: Authenticated user information

    Returns:
        MessageResponse: Confirmation message

    Raises:
        404 Not Found: Player not found in system
        500 Internal Server Error: Service errors
    """
    try:
        logger.info(
            f"User {current_user.get('username')} removing player: {username}"
        )

        # Remove player from tracking system
        removed = await player_service.remove_player(username)

        if not removed:
            logger.warning(f"Player not found for removal: {username}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player '{username}' not found in tracking system",
            )

        logger.info(f"Successfully removed player: {username}")
        return MessageResponse(
            message=f"Player '{username}' has been removed from tracking"
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error removing player {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while removing player",
        )


@router.get("", response_model=PlayersListResponse)
async def list_players(
    active_only: bool = True,
    player_service: PlayerService = Depends(get_player_service),
    current_user: Dict[str, Any] = Depends(require_auth),
) -> PlayersListResponse:
    """
    List all tracked players in the system.

    Args:
        active_only: If True, only return active players. If False, return all players.
        player_service: Player service dependency
        current_user: Authenticated user information

    Returns:
        PlayersListResponse: List of players with total count

    Raises:
        500 Internal Server Error: Service errors
    """
    try:
        logger.debug(
            f"User {current_user.get('username')} listing players (active_only={active_only})"
        )

        # Get list of players
        players = await player_service.list_players(active_only=active_only)

        # Convert to response models
        player_responses = [
            PlayerResponse.from_player(player) for player in players
        ]

        logger.debug(f"Returning {len(player_responses)} players")
        return PlayersListResponse(
            players=player_responses, total_count=len(player_responses)
        )

    except Exception as e:
        logger.error(f"Unexpected error listing players: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while listing players",
        )


@router.post("/{username}/fetch", response_model=FetchTriggerResponse)
async def trigger_manual_fetch(
    username: str,
    player_service: PlayerService = Depends(get_player_service),
    current_user: Dict[str, Any] = Depends(require_auth),
) -> FetchTriggerResponse:
    """
    Trigger a manual hiscore data fetch for a specific player.

    This endpoint enqueues a background task to fetch the latest hiscore data
    from the OSRS API for the specified player. The task will run asynchronously
    and the response includes a task ID for tracking progress.

    Args:
        username: OSRS player username to fetch data for
        player_service: Player service dependency
        current_user: Authenticated user information

    Returns:
        FetchTriggerResponse: Task information with ID and estimated completion time

    Raises:
        404 Not Found: Player not found in tracking system
        500 Internal Server Error: Task enqueue or other service errors
    """
    try:
        logger.info(
            f"User {current_user.get('username')} triggering manual fetch for: {username}"
        )

        # Verify player exists in our system
        player = await player_service.get_player(username)
        if not player:
            logger.warning(f"Player not found for manual fetch: {username}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player '{username}' not found in tracking system",
            )

        # Import and enqueue the fetch task
        try:
            from src.workers.tasks import fetch_player_hiscores_task

            # Enqueue the task and get task info
            task_result = await fetch_player_hiscores_task.kiq(username)
            task_id = task_result.task_id

            logger.info(
                f"Successfully enqueued manual fetch task for {username} (task ID: {task_id})"
            )

            # Estimated completion time based on typical OSRS API response time
            # and processing overhead (usually 5-15 seconds)
            estimated_completion_seconds = 15

            return FetchTriggerResponse(
                task_id=task_id,
                username=username,
                message=f"Manual fetch task enqueued for player '{username}'",
                estimated_completion_seconds=estimated_completion_seconds,
                status="enqueued",
            )

        except Exception as e:
            logger.error(f"Failed to enqueue fetch task for {username}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to enqueue fetch task: {e}",
            )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error triggering manual fetch for {username}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while triggering manual fetch",
        )


@router.get("/{username}/metadata", response_model=PlayerMetadataResponse)
async def get_player_metadata(
    username: str,
    db_session: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(require_auth),
) -> PlayerMetadataResponse:
    """
    Get detailed metadata and statistics for a specific player.

    Returns comprehensive information about a player including record counts,
    fetch history, and timing statistics. Useful for monitoring individual
    player tracking performance and troubleshooting.

    Args:
        username: OSRS player username
        db_session: Database session dependency
        current_user: Authenticated user information

    Returns:
        PlayerMetadataResponse: Detailed player metadata and statistics

    Raises:
        404 Not Found: Player not found in system
        500 Internal Server Error: Database or calculation errors
    """
    try:
        logger.info(
            f"User {current_user.get('username')} requesting metadata for player: {username}"
        )

        # Get player
        player_result = await db_session.execute(
            select(Player).where(Player.username.ilike(username))
        )
        player = player_result.scalar_one_or_none()

        if not player:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player '{username}' not found in tracking system",
            )

        # Get record count
        total_records_result = await db_session.execute(
            select(func.count(HiscoreRecord.id)).where(
                HiscoreRecord.player_id == player.id
            )
        )
        total_records = total_records_result.scalar() or 0

        # Get first and latest record timestamps
        first_record_result = await db_session.execute(
            select(func.min(HiscoreRecord.fetched_at)).where(
                HiscoreRecord.player_id == player.id
            )
        )
        first_record = first_record_result.scalar()

        latest_record_result = await db_session.execute(
            select(func.max(HiscoreRecord.fetched_at)).where(
                HiscoreRecord.player_id == player.id
            )
        )
        latest_record = latest_record_result.scalar()

        # Get recent record counts
        from datetime import datetime, timedelta

        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)

        records_24h_result = await db_session.execute(
            select(func.count(HiscoreRecord.id)).where(
                HiscoreRecord.player_id == player.id,
                HiscoreRecord.fetched_at >= last_24h,
            )
        )
        records_last_24h = records_24h_result.scalar() or 0

        records_7d_result = await db_session.execute(
            select(func.count(HiscoreRecord.id)).where(
                HiscoreRecord.player_id == player.id,
                HiscoreRecord.fetched_at >= last_7d,
            )
        )
        records_last_7d = records_7d_result.scalar() or 0

        # Calculate average fetch frequency
        avg_fetch_frequency_hours = None
        if total_records > 1 and first_record and latest_record:
            time_span = latest_record - first_record
            if time_span.total_seconds() > 0:
                avg_fetch_frequency_hours = round(
                    time_span.total_seconds() / 3600 / (total_records - 1), 2
                )

        metadata = {
            "total_records": total_records,
            "first_record": first_record.isoformat() if first_record else None,
            "latest_record": (
                latest_record.isoformat() if latest_record else None
            ),
            "records_last_24h": records_last_24h,
            "records_last_7d": records_last_7d,
            "avg_fetch_frequency_hours": avg_fetch_frequency_hours,
        }

        response = PlayerMetadataResponse.from_player_with_metadata(
            player, metadata
        )

        logger.info(f"Successfully retrieved metadata for player: {username}")
        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error retrieving metadata for player {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve player metadata",
        )


@router.post("/{username}/deactivate", response_model=MessageResponse)
async def deactivate_player(
    username: str,
    player_service: PlayerService = Depends(get_player_service),
    current_user: Dict[str, Any] = Depends(require_auth),
) -> MessageResponse:
    """
    Deactivate a player (soft delete) to stop automatic fetching.

    This sets is_active to False, which stops automatic hiscore fetching
    but preserves all historical data. The player can be reactivated later.

    Args:
        username: OSRS player username to deactivate
        player_service: Player service dependency
        current_user: Authenticated user information

    Returns:
        MessageResponse: Confirmation message

    Raises:
        404 Not Found: Player not found in system
        500 Internal Server Error: Service errors
    """
    try:
        logger.info(
            f"User {current_user.get('username')} deactivating player: {username}"
        )

        deactivated = await player_service.deactivate_player(username)

        if not deactivated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player '{username}' not found in tracking system",
            )

        logger.info(f"Successfully deactivated player: {username}")
        return MessageResponse(
            message=f"Player '{username}' has been deactivated (automatic fetching stopped)"
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error deactivating player {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate player",
        )


@router.post("/{username}/reactivate", response_model=MessageResponse)
async def reactivate_player(
    username: str,
    player_service: PlayerService = Depends(get_player_service),
    current_user: Dict[str, Any] = Depends(require_auth),
) -> MessageResponse:
    """
    Reactivate a previously deactivated player.

    This sets is_active to True, which resumes automatic hiscore fetching
    according to the player's fetch interval.

    Args:
        username: OSRS player username to reactivate
        player_service: Player service dependency
        current_user: Authenticated user information

    Returns:
        MessageResponse: Confirmation message

    Raises:
        404 Not Found: Player not found in system
        500 Internal Server Error: Service errors
    """
    try:
        logger.info(
            f"User {current_user.get('username')} reactivating player: {username}"
        )

        reactivated = await player_service.reactivate_player(username)

        if not reactivated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player '{username}' not found in tracking system",
            )

        logger.info(f"Successfully reactivated player: {username}")
        return MessageResponse(
            message=f"Player '{username}' has been reactivated (automatic fetching resumed)"
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error reactivating player {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reactivate player",
        )


@router.post("/{username}/update-game-mode", response_model=MessageResponse)
async def update_player_game_mode(
    username: str,
    player_service: PlayerService = Depends(get_player_service),
    current_user: Dict[str, Any] = Depends(require_auth),
) -> MessageResponse:
    """
    Update a player's game mode by re-detecting it from OSRS hiscores.

    This endpoint is useful when a player transitions between game modes
    (e.g., hardcore ironman dies and becomes regular ironman). It will
    fetch the player's current stats from all game mode hiscores and
    determine their current mode based on the highest experience values.

    Args:
        username: OSRS player username to update
        player_service: Player service dependency
        current_user: Authenticated user information

    Returns:
        MessageResponse: Confirmation message with old and new game mode

    Raises:
        404 Not Found: Player not found in system or OSRS hiscores
        502 Bad Gateway: OSRS API unavailable
        500 Internal Server Error: Service errors
    """
    try:
        logger.info(
            f"User {current_user.get('username')} updating game mode for player: {username}"
        )

        # Get current player to show old game mode
        player = await player_service.get_player(username)
        if not player:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player '{username}' not found in tracking system",
            )

        old_game_mode = player.game_mode.value

        # Update game mode
        updated = await player_service.update_player_game_mode(username)

        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player '{username}' not found in tracking system",
            )

        # Get updated player to show new game mode
        updated_player = await player_service.get_player(username)
        new_game_mode = (
            updated_player.game_mode.value if updated_player else old_game_mode
        )

        if old_game_mode == new_game_mode:
            message = (
                f"Player '{username}' game mode unchanged: {old_game_mode}"
            )
        else:
            message = f"Player '{username}' game mode updated: {old_game_mode} → {new_game_mode}"

        logger.info(f"Successfully updated game mode for player: {username}")
        return MessageResponse(message=message)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error updating game mode for player {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update player game mode",
        )
