import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_utils import require_admin, require_auth
from app.exceptions import (
    InvalidUsernameError,
    OSRSAPIError,
    OSRSPlayerNotFoundError,
    PlayerAlreadyExistsError,
    PlayerNotFoundError,
    PlayerServiceError,
)
from app.models.base import get_db_session
from app.models.hiscore import HiscoreRecord
from app.models.player import Player
from app.models.player_summary import PlayerSummary
from app.services.osrs_api import (
    OSRSAPIClient,
    get_osrs_api_client,
)
from app.services.player import (
    PlayerService,
    get_player_service,
)
from app.services.player_type_classifier import PlayerTypeClassificationError

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
    game_mode: str | None = Field(
        None,
        description="Player game mode (regular, ironman, hardcore, ultimate)",
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
            game_mode=player.game_mode,
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
    game_mode: str | None = Field(
        None,
        description="Player game mode (regular, ironman, hardcore, ultimate)",
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
            game_mode=player.game_mode,
        )


# Router
router = APIRouter(prefix="/players", tags=["players"])


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

    except (
        InvalidUsernameError,
        PlayerAlreadyExistsError,
        OSRSPlayerNotFoundError,
        OSRSAPIError,
    ):
        # These exceptions are handled by the exception handler in main.py
        raise
    except Exception as e:
        logger.error(f"Unexpected error adding player {request.username}: {e}")
        raise PlayerServiceError(f"Failed to add player: {e}")


@router.delete("/{username}", response_model=MessageResponse)
async def remove_player(
    username: str,
    player_service: PlayerService = Depends(get_player_service),
    current_user: Dict[str, Any] = Depends(require_auth),
) -> MessageResponse:
    """
    Remove a player from the tracking system.

    This endpoint removes the player and all associated hiscore records
    from the database. Player summaries are preserved (player_id set to NULL)
    for cost analysis purposes. This action cannot be undone.

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
            raise PlayerNotFoundError(username)

        logger.info(f"Successfully removed player: {username}")
        return MessageResponse(
            message=f"Player '{username}' has been removed from tracking"
        )

    except (PlayerNotFoundError, PlayerServiceError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error removing player {username}: {e}")
        raise PlayerServiceError(f"Failed to remove player: {e}")


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
        raise PlayerServiceError(f"Failed to list players: {e}")


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
            raise PlayerNotFoundError(username)

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
            raise PlayerServiceError(f"Failed to enqueue fetch task: {e}")

    except (PlayerNotFoundError, PlayerServiceError):
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error triggering manual fetch for {username}: {e}"
        )
        raise PlayerServiceError(f"Failed to trigger manual fetch: {e}")


@router.get("/{username}/metadata", response_model=PlayerMetadataResponse)
async def get_player_metadata(
    username: str,
    db_session: AsyncSession = Depends(get_db_session),
    player_service: PlayerService = Depends(get_player_service),
) -> PlayerMetadataResponse:
    """
    Get detailed metadata and statistics for a specific player.

    Returns comprehensive information about a player including record counts,
    fetch history, and timing statistics. Useful for monitoring individual
    player tracking performance and troubleshooting. If the player doesn't exist
    in the database but exists in OSRS, they will be automatically added.

    Args:
        username: OSRS player username
        db_session: Database session dependency
        player_service: Player service dependency

    Returns:
        PlayerMetadataResponse: Detailed player metadata and statistics

    Raises:
        400 Bad Request: Invalid username format
        404 Not Found: Player not found in OSRS hiscores
        502 Bad Gateway: OSRS API unavailable
        500 Internal Server Error: Database or calculation errors
    """
    try:
        logger.info(f"Requesting metadata for player: {username}")

        # Ensure player exists (auto-add if they exist in OSRS)
        player = await player_service.ensure_player_exists(username)

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

    except (PlayerNotFoundError, OSRSPlayerNotFoundError):
        raise
    except Exception as e:
        logger.error(f"Error retrieving metadata for player {username}: {e}")
        raise PlayerServiceError(f"Failed to retrieve player metadata: {e}")


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
            raise PlayerNotFoundError(username)

        logger.info(f"Successfully deactivated player: {username}")
        return MessageResponse(
            message=f"Player '{username}' has been deactivated (automatic fetching stopped)"
        )

    except (PlayerNotFoundError, PlayerServiceError):
        raise
    except Exception as e:
        logger.error(f"Error deactivating player {username}: {e}")
        raise PlayerServiceError(f"Failed to deactivate player: {e}")


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
            raise PlayerNotFoundError(username)

        logger.info(f"Successfully reactivated player: {username}")
        return MessageResponse(
            message=f"Player '{username}' has been reactivated (automatic fetching resumed)"
        )

    except (PlayerNotFoundError, PlayerServiceError):
        raise
    except Exception as e:
        logger.error(f"Error reactivating player {username}: {e}")
        raise PlayerServiceError(f"Failed to reactivate player: {e}")


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
            raise PlayerNotFoundError(username)

        # Get updated player to return
        player = await player_service.get_player(username)
        if not player:
            raise PlayerServiceError(
                "Failed to retrieve updated player information"
            )

        logger.info(
            f"Successfully updated fetch interval for player {username} "
            f"to {request.fetch_interval_minutes} minutes"
        )

        return PlayerResponse.from_player(player)

    except ValueError as e:
        logger.warning(f"Invalid fetch interval for player {username}: {e}")
        raise InvalidUsernameError(str(e))
    except (PlayerNotFoundError, PlayerServiceError, InvalidUsernameError):
        raise
    except Exception as e:
        logger.error(
            f"Error updating fetch interval for player {username}: {e}"
        )
        raise PlayerServiceError(
            f"Failed to update player fetch interval: {e}"
        )


@router.post(
    "/{username}/recalculate-game-mode", response_model=PlayerResponse
)
async def recalculate_player_game_mode(
    username: str,
    player_service: PlayerService = Depends(get_player_service),
    current_user: Dict[str, Any] = Depends(require_auth),
) -> PlayerResponse:
    """
    Recalculate and update a player's game mode.

    This endpoint reclassifies the player's game mode by checking all hiscores
    endpoints (regular, ironman, hardcore, ultimate) and comparing experiences
    to determine the correct game mode. Useful when a player's game mode may
    have changed (e.g., de-ironing) or was not correctly classified initially.

    Args:
        username: OSRS player username
        player_service: Player service dependency
        current_user: Authenticated user information

    Returns:
        PlayerResponse: Updated player information with new game_mode

    Raises:
        404 Not Found: Player not found in system
        502 Bad Gateway: OSRS API unavailable
        500 Internal Server Error: Classification or service errors
    """
    try:
        logger.info(
            f"User {current_user.get('username')} recalculating game mode "
            f"for player: {username}"
        )

        # Recalculate the player's game mode
        updated = await player_service.recalculate_game_mode(username)

        if not updated:
            raise PlayerNotFoundError(username)

        # Get updated player to return
        player = await player_service.get_player(username)
        if not player:
            raise PlayerServiceError(
                "Failed to retrieve updated player information"
            )

        logger.info(
            f"Successfully recalculated game mode for player {username}: "
            f"{player.game_mode}"
        )

        return PlayerResponse.from_player(player)

    except PlayerTypeClassificationError as e:
        logger.error(
            f"Failed to classify game mode for player {username}: {e}"
        )
        raise OSRSAPIError(f"Failed to classify game mode: {e}", detail=str(e))
    except (PlayerNotFoundError, PlayerServiceError):
        raise
    except Exception as e:
        logger.error(
            f"Error recalculating game mode for player {username}: {e}"
        )
        raise PlayerServiceError(f"Failed to recalculate game mode: {e}")


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
        raise PlayerServiceError(f"Failed to list player schedules: {e}")


class PlayerSummaryResponse(BaseModel):
    """Response model for a player summary."""

    id: int = Field(description="Summary ID")
    player_id: int | None = Field(
        description="Player ID (null if player was deleted)"
    )
    period_start: str = Field(description="Start of the summary period")
    period_end: str = Field(description="End of the summary period")
    summary_text: str = Field(
        description="Generated summary text (JSON or plain text)"
    )
    summary: Optional[str] = Field(
        None,
        description="Concise summary overview (structured format)",
    )
    summary_points: List[str] = Field(
        default_factory=list,
        description="Parsed summary points (structured format)",
    )
    generated_at: str = Field(description="When the summary was generated")
    model_used: Optional[str] = Field(
        None, description="OpenAI model used for generation"
    )
    prompt_tokens: Optional[int] = Field(
        None, description="Number of tokens used in the prompt"
    )
    completion_tokens: Optional[int] = Field(
        None, description="Number of tokens used in the completion"
    )
    total_tokens: Optional[int] = Field(
        None, description="Total number of tokens used (prompt + completion)"
    )
    finish_reason: Optional[str] = Field(
        None, description="Reason the completion finished"
    )
    response_id: Optional[str] = Field(
        None, description="OpenAI API response ID"
    )

    @classmethod
    def from_summary(cls, summary: PlayerSummary) -> "PlayerSummaryResponse":
        """Create response model from PlayerSummary entity."""
        from app.services.summary import parse_summary_text

        parsed = parse_summary_text(summary.summary_text)
        return cls(
            id=summary.id,
            player_id=summary.player_id,
            period_start=summary.period_start.isoformat(),
            period_end=summary.period_end.isoformat(),
            summary_text=summary.summary_text,
            summary=parsed.get("summary"),
            summary_points=parsed.get("points", []),
            generated_at=summary.generated_at.isoformat(),
            model_used=summary.model_used,
            prompt_tokens=summary.prompt_tokens,
            completion_tokens=summary.completion_tokens,
            total_tokens=summary.total_tokens,
            finish_reason=summary.finish_reason,
            response_id=summary.response_id,
        )


@router.get(
    "/{username}/summary", response_model=Optional[PlayerSummaryResponse]
)
async def get_player_summary(
    username: str,
    db_session: AsyncSession = Depends(get_db_session),
    player_service: PlayerService = Depends(get_player_service),
) -> Optional[PlayerSummaryResponse]:
    """
    Get the most recent AI-generated summary for a player.

    Returns the latest summary if available, or None if no summary exists.
    If the player doesn't exist in the database but exists in OSRS, they will
    be automatically added.

    Args:
        username: OSRS player username
        db_session: Database session dependency
        player_service: Player service dependency

    Returns:
        PlayerSummaryResponse: Most recent summary or None

    Raises:
        400 Bad Request: Invalid username format
        404 Not Found: Player not found in OSRS hiscores
        502 Bad Gateway: OSRS API unavailable
        500 Internal Server Error: Database errors
    """
    try:
        logger.info(f"Requesting summary for player: {username}")

        # Ensure player exists (auto-add if they exist in OSRS)
        player = await player_service.ensure_player_exists(username)

        # Get most recent summary
        summary_stmt = (
            select(PlayerSummary)
            .where(PlayerSummary.player_id == player.id)
            .order_by(PlayerSummary.generated_at.desc())
            .limit(1)
        )
        summary_result = await db_session.execute(summary_stmt)
        summary = summary_result.scalar_one_or_none()

        if not summary:
            return None

        return PlayerSummaryResponse.from_summary(summary)

    except (PlayerNotFoundError, OSRSPlayerNotFoundError):
        raise
    except Exception as e:
        logger.error(f"Error retrieving summary for player {username}: {e}")
        raise PlayerServiceError(f"Failed to retrieve player summary: {e}")


class GeneratePlayerSummaryRequest(BaseModel):
    """Request model for generating a player summary."""

    force_regenerate: bool = Field(
        False, description="Force regeneration even if recent summary exists"
    )


@router.post("/{username}/summary", response_model=PlayerSummaryResponse)
async def generate_player_summary(
    username: str,
    request: GeneratePlayerSummaryRequest,
    db_session: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(require_admin),
) -> PlayerSummaryResponse:
    """
    Generate an AI-powered progress summary for a specific player.

    This endpoint generates a summary using OpenAI API that analyzes player progress
    over the last day and week. Only admins can trigger summary generation.

    Args:
        username: OSRS player username
        request: Summary generation request with force_regenerate option
        db_session: Database session dependency
        current_user: Authenticated admin user information

    Returns:
        PlayerSummaryResponse: Generated summary

    Raises:
        403 Forbidden: User is not an admin
        404 Not Found: Player not found
        500 Internal Server Error: Summary generation errors
    """
    try:
        logger.info(
            f"Admin {current_user.get('username')} generating summary for player: {username} "
            f"(force={request.force_regenerate})"
        )

        # Get player
        player_result = await db_session.execute(
            select(Player).where(Player.username.ilike(username))
        )
        player = player_result.scalar_one_or_none()

        if not player:
            raise PlayerNotFoundError(username)

        # Generate summary
        from app.services.summary import SummaryService, get_summary_service

        summary_service = get_summary_service(db_session)

        try:
            summary = await summary_service.generate_summary_for_player(
                player.id, force_regenerate=request.force_regenerate
            )
            if summary is None:
                raise PlayerServiceError(
                    "Failed to generate summary: returned None"
                )
        except Exception as e:
            logger.error(
                f"Failed to generate summary for player {username}: {e}"
            )
            raise PlayerServiceError(f"Failed to generate summary: {e}")

        logger.info(f"Successfully generated summary for player {username}")
        return PlayerSummaryResponse.from_summary(summary)

    except (PlayerNotFoundError, PlayerServiceError):
        raise
    except Exception as e:
        logger.error(
            f"Error generating summary for player {username}: {e}",
            exc_info=True,
        )
        raise PlayerServiceError(f"Failed to generate summary: {e}")
