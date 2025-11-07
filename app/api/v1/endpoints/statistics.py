import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_utils import require_auth
from app.models.base import get_db_session
from app.exceptions import (
    PlayerNotFoundError,
    StatisticsServiceError,
)
from app.services.statistics import (
    StatisticsService,
)

logger = logging.getLogger(__name__)


async def get_statistics_service(
    db_session: AsyncSession = Depends(get_db_session),
) -> StatisticsService:
    """Dependency injection for StatisticsService."""
    return StatisticsService(db_session)


# Response models
class OverallStatsResponse(BaseModel):
    """Response model for overall statistics."""

    rank: Optional[int] = Field(None, description="Overall rank in hiscores")
    level: Optional[int] = Field(None, description="Total level")
    experience: Optional[int] = Field(None, description="Total experience")


class StatsMetadataResponse(BaseModel):
    """Response model for statistics metadata."""

    total_skills: int = Field(description="Number of skills with data")
    total_bosses: int = Field(description="Number of bosses with data")
    record_id: Optional[int] = Field(None, description="Database record ID")


class PlayerStatsResponse(BaseModel):
    """Response model for individual player statistics."""

    username: str = Field(description="Player username")
    fetched_at: Optional[str] = Field(
        None, description="When the data was last fetched (ISO format)"
    )
    overall: Optional[OverallStatsResponse] = Field(
        None, description="Overall statistics"
    )
    combat_level: Optional[int] = Field(
        None, description="Calculated combat level"
    )
    skills: Dict[str, Any] = Field(
        default_factory=dict,
        description="Skills data with levels and experience",
    )
    bosses: Dict[str, Any] = Field(
        default_factory=dict, description="Boss kill counts and ranks"
    )
    metadata: StatsMetadataResponse = Field(
        description="Additional metadata about the record"
    )
    error: Optional[str] = Field(
        None, description="Error message if data unavailable"
    )


# Router
router = APIRouter(prefix="/players", tags=["statistics"])


@router.get("/{username}/stats", response_model=PlayerStatsResponse)
async def get_player_stats(
    username: str,
    statistics_service: StatisticsService = Depends(get_statistics_service),
    current_user: Dict[str, Any] = Depends(require_auth),
) -> PlayerStatsResponse:
    """
    Get current statistics for a specific player.

    This endpoint returns the most recent hiscore record for the specified player,
    including skill levels, experience points, boss kill counts, and calculated
    combat level.

    Args:
        username: OSRS player username
        statistics_service: Statistics service dependency
        current_user: Authenticated user information

    Returns:
        PlayerStatsResponse: Current player statistics

    Raises:
        404 Not Found: Player not found in system
        500 Internal Server Error: Service errors
    """
    try:
        logger.debug(
            f"User {current_user.get('username')} requesting stats for player: {username}"
        )

        # Get current stats for the player
        record = await statistics_service.get_current_stats(username)

        if record is None:
            # Player exists but has no data
            logger.debug(f"No hiscore data available for player: {username}")
            return PlayerStatsResponse(
                username=username,
                fetched_at=None,
                overall=None,
                combat_level=None,
                skills={},
                bosses={},
                metadata=StatsMetadataResponse(
                    total_skills=0,
                    total_bosses=0,
                    record_id=None,
                ),
                error="No data available",
            )

        # Format the response
        formatted_data = await statistics_service.format_stats_response(
            record, username
        )

        # Convert to response model
        response = PlayerStatsResponse(
            username=formatted_data["username"],
            fetched_at=formatted_data["fetched_at"],
            overall=(
                OverallStatsResponse(**formatted_data["overall"])
                if formatted_data["overall"]
                else None
            ),
            combat_level=formatted_data["combat_level"],
            skills=formatted_data["skills"],
            bosses=formatted_data["bosses"],
            metadata=StatsMetadataResponse(**formatted_data["metadata"]),
            error=None,
        )

        logger.debug(f"Successfully retrieved stats for player: {username}")
        return response

    except (PlayerNotFoundError, StatisticsServiceError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting stats for {username}: {e}")
        raise StatisticsServiceError(f"Failed to retrieve statistics: {e}")
