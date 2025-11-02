"""Statistics API endpoints."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import require_auth
from src.models.base import get_db_session
from src.services.statistics import (
    NoDataAvailableError,
    PlayerNotFoundError,
    StatisticsService,
    StatisticsServiceError,
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


class MultipleStatsMetadataResponse(BaseModel):
    """Response model for multiple stats query metadata."""

    total_requested: int = Field(
        description="Total number of players requested"
    )
    total_found: int = Field(description="Number of players with data found")
    total_missing: int = Field(description="Number of players without data")


class MultipleStatsResponse(BaseModel):
    """Response model for multiple player statistics."""

    players: Dict[str, PlayerStatsResponse] = Field(
        description="Statistics for each requested player"
    )
    metadata: MultipleStatsMetadataResponse = Field(
        description="Query metadata"
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

    except PlayerNotFoundError as e:
        logger.warning(f"Player not found: {username} - {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player '{username}' not found in tracking system",
        )
    except StatisticsServiceError as e:
        logger.error(f"Statistics service error for player {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while retrieving statistics",
        )
    except Exception as e:
        logger.error(f"Unexpected error getting stats for {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while retrieving statistics",
        )


@router.get("/stats", response_model=MultipleStatsResponse)
async def get_multiple_player_stats(
    usernames: List[str] = Query(
        ...,
        description="List of OSRS player usernames to get statistics for",
        min_items=1,
        max_items=50,  # Reasonable limit to prevent abuse
    ),
    statistics_service: StatisticsService = Depends(get_statistics_service),
    current_user: Dict[str, Any] = Depends(require_auth),
) -> MultipleStatsResponse:
    """
    Get current statistics for multiple players in a single request.

    This endpoint allows querying statistics for multiple players efficiently,
    returning a mapping of username to statistics data. Players not found in
    the system or without data will have appropriate error indicators.

    Args:
        usernames: List of OSRS player usernames (1-50 players)
        statistics_service: Statistics service dependency
        current_user: Authenticated user information

    Returns:
        MultipleStatsResponse: Statistics for all requested players with metadata

    Raises:
        400 Bad Request: Invalid request parameters
        500 Internal Server Error: Service errors
    """
    try:
        logger.debug(
            f"User {current_user.get('username')} requesting stats for {len(usernames)} players"
        )

        # Validate usernames list
        if not usernames:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one username must be provided",
            )

        if len(usernames) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 50 usernames allowed per request",
            )

        # Remove duplicates while preserving order
        unique_usernames = list(dict.fromkeys(usernames))

        # Get stats for all players
        stats_map = await statistics_service.get_multiple_stats(
            unique_usernames
        )

        # Format the response
        formatted_data = (
            await statistics_service.format_multiple_stats_response(stats_map)
        )

        # Convert to response models
        players_response = {}
        for username, player_data in formatted_data["players"].items():
            if "error" in player_data:
                # Player without data
                players_response[username] = PlayerStatsResponse(
                    username=player_data["username"],
                    fetched_at=player_data["fetched_at"],
                    overall=None,
                    combat_level=player_data["combat_level"],
                    skills=player_data["skills"],
                    bosses=player_data["bosses"],
                    metadata=StatsMetadataResponse(**player_data["metadata"]),
                    error=player_data["error"],
                )
            else:
                # Player with data
                players_response[username] = PlayerStatsResponse(
                    username=player_data["username"],
                    fetched_at=player_data["fetched_at"],
                    overall=(
                        OverallStatsResponse(**player_data["overall"])
                        if player_data["overall"]
                        else None
                    ),
                    combat_level=player_data["combat_level"],
                    skills=player_data["skills"],
                    bosses=player_data["bosses"],
                    metadata=StatsMetadataResponse(**player_data["metadata"]),
                    error=None,
                )

        response = MultipleStatsResponse(
            players=players_response,
            metadata=MultipleStatsMetadataResponse(
                **formatted_data["metadata"]
            ),
        )

        logger.debug(
            f"Successfully retrieved stats for {formatted_data['metadata']['total_found']} "
            f"out of {len(unique_usernames)} requested players"
        )
        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except StatisticsServiceError as e:
        logger.error(f"Statistics service error for multiple players: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while retrieving statistics",
        )
    except Exception as e:
        logger.error(f"Unexpected error getting multiple stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while retrieving statistics",
        )
