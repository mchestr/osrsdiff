import logging
import sys
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_utils import require_auth
from app.models.base import get_db_session
from app.models.hiscore import HiscoreRecord
from app.models.player import Player
from app.services.osrs_api import (
    OSRSAPIClient,
    OSRSAPIError,
)
from app.services.osrs_api import (
    PlayerNotFoundError as OSRSPlayerNotFoundError,
)
from app.services.osrs_api import (
    get_osrs_api_client,
)
from app.services.player import (
    InvalidUsernameError,
    PlayerAlreadyExistsError,
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


class PlayerUpdateIntervalRequest(BaseModel):
    """Request model for updating a player's fetch interval."""

    fetch_interval_minutes: int = Field(
        ...,
        ge=1,
        le=10080,  # 1 week maximum
        description="Fetch interval in minutes (1-10080)",
    )


class PlayerScheduleStatusResponse(BaseModel):
    """Response model for player schedule status."""

    id: int
    username: str
    is_active: bool
    fetch_interval_minutes: int
    schedule_id: str | None
    schedule_status: str = Field(
        description="Status of the schedule: 'scheduled', 'missing', 'invalid', 'not_scheduled'"
    )
    last_verified: str | None = Field(
        description="Timestamp when schedule was last verified"
    )


class ScheduleListResponse(BaseModel):
    """Response model for listing all player schedules."""

    players: List[PlayerScheduleStatusResponse]
    total_count: int
    scheduled_count: int
    missing_count: int
    invalid_count: int


class ScheduleVerificationResponse(BaseModel):
    """Response model for schedule verification results."""

    total_schedules: int
    player_fetch_schedules: int
    other_schedules: int
    invalid_schedules: List[Dict[str, Any]]
    orphaned_schedules: List[str]
    duplicate_schedules: Dict[str, Any]
    verification_timestamp: str


class PlayerResponse(BaseModel):
    """Response model for player data."""

    id: int
    username: str
    created_at: str
    last_fetched: str | None
    is_active: bool
    fetch_interval_minutes: int
    schedule_id: str | None = Field(
        description="TaskIQ schedule ID for this player's fetch task"
    )

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
            schedule_id=player.schedule_id,
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
    schedule_id: str | None = Field(
        description="TaskIQ schedule ID for this player's fetch task"
    )
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
            schedule_id=player.schedule_id,
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
    prevents duplicates, and creates a new Player entity. It also schedules periodic
    hiscore fetches based on the player's fetch interval and triggers an initial fetch
    task to populate baseline statistics.

    Args:
        request: Player creation request with username
        player_service: Player service dependency
        current_user: Authenticated user information

    Returns:
        PlayerResponse: Created player information with schedule_id

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

        # Schedule periodic hiscore fetches for the player
        try:
            from app.services.scheduler import get_player_schedule_manager

            schedule_manager = get_player_schedule_manager()
            schedule_id = await schedule_manager.schedule_player(player)
            player.schedule_id = schedule_id
            await player_service.db_session.commit()
            logger.info(
                f"Scheduled periodic fetch for player {player.username} (schedule_id: {schedule_id})"
            )
        except Exception as e:
            logger.warning(
                f"Failed to schedule periodic fetch for {player.username}: {e}"
            )
            # Don't fail the player creation if scheduling fails

        # Trigger initial fetch task
        try:
            from app.workers.tasks import fetch_player_hiscores_task

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
        logger.info(
            f"User {current_user.get('username')} listing players (active_only={active_only})"
        )

        # Get list of players
        players = await player_service.list_players(active_only=active_only)

        # Convert to response models
        player_responses = [
            PlayerResponse.from_player(player) for player in players
        ]

        logger.info(f"Returning {len(player_responses)} players")
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
            from app.workers.tasks import fetch_player_hiscores_task

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


@router.put("/{username}/fetch-interval", response_model=PlayerResponse)
async def update_player_fetch_interval(
    username: str,
    request: PlayerUpdateIntervalRequest,
    player_service: PlayerService = Depends(get_player_service),
    current_user: Dict[str, Any] = Depends(require_auth),
) -> PlayerResponse:
    """
    Update a player's fetch interval and reschedule their task.

    This endpoint updates the player's fetch interval and automatically
    reschedules their background task with the new interval if they are active.

    Args:
        username: OSRS player username to update
        request: Update request with new fetch interval
        player_service: Player service dependency
        current_user: Authenticated user information

    Returns:
        PlayerResponse: Updated player information

    Raises:
        400 Bad Request: Invalid fetch interval
        404 Not Found: Player not found in system
        500 Internal Server Error: Service errors
    """
    try:
        logger.info(
            f"User {current_user.get('username')} updating fetch interval for player {username} "
            f"to {request.fetch_interval_minutes} minutes"
        )

        # Update the player's fetch interval
        updated = await player_service.update_player_fetch_interval(
            username, request.fetch_interval_minutes
        )

        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player '{username}' not found in tracking system",
            )

        # Get updated player to return
        player = await player_service.get_player(username)
        if not player:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve updated player information",
            )

        logger.info(
            f"Successfully updated fetch interval for player {username} "
            f"to {request.fetch_interval_minutes} minutes"
        )

        return PlayerResponse.from_player(player)

    except ValueError as e:
        logger.warning(f"Invalid fetch interval for player {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(
            f"Error updating fetch interval for player {username}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update player fetch interval",
        )


@router.get("/schedules", response_model=ScheduleListResponse)
async def list_player_schedules(
    player_service: PlayerService = Depends(get_player_service),
    current_user: Dict[str, Any] = Depends(require_auth),
) -> ScheduleListResponse:
    """
    List all players with their schedule status.

    This endpoint provides comprehensive information about all players and
    their scheduling status, including whether schedules exist, are valid,
    or are missing.

    Args:
        player_service: Player service dependency
        current_user: Authenticated user information

    Returns:
        ScheduleListResponse: List of players with schedule status information

    Raises:
        500 Internal Server Error: Service errors
    """
    try:
        logger.info(
            f"User {current_user.get('username')} requesting player schedule list"
        )

        # Get all players
        players = await player_service.list_players(active_only=False)

        # Get schedule manager to verify schedules
        from app.services.scheduler import get_player_schedule_manager

        try:
            schedule_manager = get_player_schedule_manager()
        except Exception as e:
            logger.warning(f"Failed to get schedule manager: {e}")
            schedule_manager = None

        player_statuses = []
        scheduled_count = 0
        missing_count = 0
        invalid_count = 0

        for player in players:
            schedule_status = "not_scheduled"

            if player.is_active and schedule_manager:
                if player.schedule_id:
                    # Verify if schedule exists and is valid
                    try:
                        is_valid = await schedule_manager._verify_schedule_exists_and_valid(
                            player
                        )
                        if is_valid:
                            schedule_status = "scheduled"
                            scheduled_count += 1
                        else:
                            schedule_status = "invalid"
                            invalid_count += 1
                    except Exception as e:
                        logger.warning(
                            f"Failed to verify schedule for player {player.username}: {e}"
                        )
                        schedule_status = "missing"
                        missing_count += 1
                else:
                    schedule_status = "missing"
                    missing_count += 1
            elif not player.is_active:
                schedule_status = "not_scheduled"

            player_status = PlayerScheduleStatusResponse(
                id=player.id,
                username=player.username,
                is_active=player.is_active,
                fetch_interval_minutes=player.fetch_interval_minutes,
                schedule_id=player.schedule_id,
                schedule_status=schedule_status,
                last_verified=None,  # Could be enhanced to track verification timestamps
            )
            player_statuses.append(player_status)

        response = ScheduleListResponse(
            players=player_statuses,
            total_count=len(player_statuses),
            scheduled_count=scheduled_count,
            missing_count=missing_count,
            invalid_count=invalid_count,
        )

        logger.info(
            f"Returning schedule status for {len(player_statuses)} players "
            f"(scheduled: {scheduled_count}, missing: {missing_count}, invalid: {invalid_count})"
        )

        return response

    except Exception as e:
        logger.error(f"Error listing player schedules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list player schedules",
        )


@router.post("/{username}/pause", response_model=MessageResponse)
async def pause_player_schedule(
    username: str,
    player_service: PlayerService = Depends(get_player_service),
    current_user: Dict[str, Any] = Depends(require_auth),
) -> MessageResponse:
    """
    Pause a player's scheduled task without deactivating the player.

    This endpoint removes the player's schedule from TaskIQ but keeps the
    player active in the system. The schedule can be resumed later.

    Args:
        username: OSRS player username to pause
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
            f"User {current_user.get('username')} pausing schedule for player: {username}"
        )

        # Get player
        player = await player_service.get_player(username)
        if not player:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player '{username}' not found in tracking system",
            )

        # Get schedule manager
        from app.services.scheduler import get_player_schedule_manager

        try:
            schedule_manager = get_player_schedule_manager()
        except Exception as e:
            logger.error(f"Failed to get schedule manager: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Schedule management is not available",
            )

        # Unschedule the player
        if player.schedule_id:
            try:
                await schedule_manager.unschedule_player(player)
                player.schedule_id = None
                await player_service.db_session.commit()
                logger.info(f"Paused schedule for player {username}")
            except Exception as e:
                logger.error(
                    f"Failed to pause schedule for player {username}: {e}"
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to pause schedule: {e}",
                )
        else:
            logger.info(f"Player {username} has no active schedule to pause")

        return MessageResponse(
            message=f"Schedule paused for player '{username}' (player remains active)"
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error pausing schedule for player {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pause player schedule",
        )


@router.post("/{username}/resume", response_model=MessageResponse)
async def resume_player_schedule(
    username: str,
    player_service: PlayerService = Depends(get_player_service),
    current_user: Dict[str, Any] = Depends(require_auth),
) -> MessageResponse:
    """
    Resume a player's scheduled task.

    This endpoint recreates the player's schedule in TaskIQ if they are
    active but don't have a current schedule.

    Args:
        username: OSRS player username to resume
        player_service: Player service dependency
        current_user: Authenticated user information

    Returns:
        MessageResponse: Confirmation message

    Raises:
        404 Not Found: Player not found in system
        400 Bad Request: Player is not active
        500 Internal Server Error: Service errors
    """
    try:
        logger.info(
            f"User {current_user.get('username')} resuming schedule for player: {username}"
        )

        # Get player
        player = await player_service.get_player(username)
        if not player:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player '{username}' not found in tracking system",
            )

        if not player.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Player '{username}' is not active. Activate the player first.",
            )

        # Get schedule manager
        from app.services.scheduler import get_player_schedule_manager

        try:
            schedule_manager = get_player_schedule_manager()
        except Exception as e:
            logger.error(f"Failed to get schedule manager: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Schedule management is not available",
            )

        # Ensure player is scheduled
        try:
            schedule_id = await schedule_manager.ensure_player_scheduled(
                player
            )
            player.schedule_id = schedule_id
            await player_service.db_session.commit()
            logger.info(
                f"Resumed schedule for player {username} (schedule_id: {schedule_id})"
            )
        except Exception as e:
            logger.error(
                f"Failed to resume schedule for player {username}: {e}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to resume schedule: {e}",
            )

        return MessageResponse(
            message=f"Schedule resumed for player '{username}' (schedule_id: {schedule_id})"
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error resuming schedule for player {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resume player schedule",
        )


@router.post("/schedules/verify", response_model=ScheduleVerificationResponse)
async def verify_all_schedules(
    current_user: Dict[str, Any] = Depends(require_auth),
) -> ScheduleVerificationResponse:
    """
    Manually trigger schedule verification for all players.

    This endpoint runs a comprehensive verification of all schedules in Redis
    and returns a detailed report of any issues found.

    Args:
        current_user: Authenticated user information

    Returns:
        ScheduleVerificationResponse: Detailed verification report

    Raises:
        500 Internal Server Error: Service errors
    """
    try:
        logger.info(
            f"User {current_user.get('username')} triggering schedule verification"
        )

        # Get schedule manager
        from app.services.scheduler import get_player_schedule_manager

        try:
            schedule_manager = get_player_schedule_manager()
        except Exception as e:
            logger.error(f"Failed to get schedule manager: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Schedule management is not available",
            )

        # Run verification
        try:
            verification_report = await schedule_manager.verify_all_schedules()

            from datetime import datetime

            verification_timestamp = datetime.utcnow().isoformat()

            response = ScheduleVerificationResponse(
                total_schedules=verification_report.get("total_schedules", 0),
                player_fetch_schedules=verification_report.get(
                    "player_fetch_schedules", 0
                ),
                other_schedules=verification_report.get("other_schedules", 0),
                invalid_schedules=verification_report.get(
                    "invalid_schedules", []
                ),
                orphaned_schedules=verification_report.get(
                    "orphaned_schedules", []
                ),
                duplicate_schedules=verification_report.get(
                    "duplicate_schedules", {}
                ),
                verification_timestamp=verification_timestamp,
            )

            logger.info(
                f"Schedule verification completed: {verification_report.get('total_schedules', 0)} total schedules, "
                f"{len(verification_report.get('invalid_schedules', []))} invalid, "
                f"{len(verification_report.get('orphaned_schedules', []))} orphaned"
            )

            return response

        except Exception as e:
            logger.error(f"Failed to verify schedules: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to verify schedules: {e}",
            )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error during schedule verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform schedule verification",
        )
