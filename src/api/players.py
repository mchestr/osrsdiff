"""Player management API endpoints."""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import require_auth
from src.models.base import get_db_session
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
