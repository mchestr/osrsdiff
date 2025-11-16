import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import get_db_session
from app.services.player.leaderboard import LeaderboardService

logger = logging.getLogger(__name__)


async def get_leaderboard_service(
    db_session: AsyncSession = Depends(get_db_session),
) -> LeaderboardService:
    """Dependency injection for LeaderboardService."""
    return LeaderboardService(db_session)


# Response models
class LeaderboardEntryResponse(BaseModel):
    """Response model for a single leaderboard entry."""

    rank: int = Field(description="Rank in this leaderboard")
    username: str = Field(description="Player username")
    fetched_at: Optional[str] = Field(
        None, description="When the data was fetched (ISO format)"
    )


class OverallExpLeaderboardEntryResponse(LeaderboardEntryResponse):
    """Response model for overall EXP leaderboard entry."""

    overall_experience: Optional[int] = Field(
        None, description="Total experience across all skills"
    )
    overall_level: Optional[int] = Field(
        None, description="Total level across all skills"
    )
    overall_rank: Optional[int] = Field(
        None, description="Overall rank in OSRS hiscores"
    )


class TotalLevelLeaderboardEntryResponse(LeaderboardEntryResponse):
    """Response model for total level leaderboard entry."""

    overall_level: Optional[int] = Field(
        None, description="Total level across all skills"
    )
    overall_experience: Optional[int] = Field(
        None, description="Total experience across all skills"
    )
    overall_rank: Optional[int] = Field(
        None, description="Overall rank in OSRS hiscores"
    )


class SkillLeaderboardEntryResponse(LeaderboardEntryResponse):
    """Response model for skill-specific leaderboard entry."""

    skill_experience: Optional[int] = Field(
        None, description="Experience in this skill"
    )
    skill_level: Optional[int] = Field(None, description="Level in this skill")
    skill_rank: Optional[int] = Field(
        None, description="Rank in OSRS hiscores for this skill"
    )


class OverallExpLeaderboardResponse(BaseModel):
    """Response model for overall EXP leaderboard."""

    leaderboard: List[OverallExpLeaderboardEntryResponse] = Field(
        description="List of players ranked by overall experience"
    )


class TotalLevelLeaderboardResponse(BaseModel):
    """Response model for total level leaderboard."""

    leaderboard: List[TotalLevelLeaderboardEntryResponse] = Field(
        description="List of players ranked by total level"
    )


class SkillLeaderboardResponse(BaseModel):
    """Response model for skill-specific leaderboard."""

    skill: str = Field(description="Skill name")
    leaderboard: List[SkillLeaderboardEntryResponse] = Field(
        description="List of players ranked by this skill"
    )


class AllSkillLeaderboardsResponse(BaseModel):
    """Response model for all skill leaderboards."""

    leaderboards: Dict[str, List[SkillLeaderboardEntryResponse]] = Field(
        description="Dict mapping skill names to their leaderboards"
    )


# Router
router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("/overall-exp", response_model=OverallExpLeaderboardResponse)
async def get_overall_exp_leaderboard(
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of players to return",
    ),
    leaderboard_service: LeaderboardService = Depends(get_leaderboard_service),
) -> OverallExpLeaderboardResponse:
    """
    Get leaderboard of top players by overall experience.

    This endpoint returns the top players ranked by their total experience
    across all skills, using their most recent hiscore data.

    Args:
        limit: Maximum number of players to return (1-1000)
        leaderboard_service: Leaderboard service dependency

    Returns:
        OverallExpLeaderboardResponse: Leaderboard data
    """
    try:
        logger.debug(f"Requesting overall EXP leaderboard (limit={limit})")

        leaderboard_data = await leaderboard_service.get_top_by_overall_exp(
            limit
        )

        leaderboard = [
            OverallExpLeaderboardEntryResponse(**entry)
            for entry in leaderboard_data
        ]

        return OverallExpLeaderboardResponse(leaderboard=leaderboard)

    except Exception as e:
        logger.error(f"Error getting overall EXP leaderboard: {e}")
        raise


@router.get("/total-level", response_model=TotalLevelLeaderboardResponse)
async def get_total_level_leaderboard(
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of players to return",
    ),
    leaderboard_service: LeaderboardService = Depends(get_leaderboard_service),
) -> TotalLevelLeaderboardResponse:
    """
    Get leaderboard of top players by total level.

    This endpoint returns the top players ranked by their total level
    across all skills, using their most recent hiscore data.

    Args:
        limit: Maximum number of players to return (1-1000)
        leaderboard_service: Leaderboard service dependency

    Returns:
        TotalLevelLeaderboardResponse: Leaderboard data
    """
    try:
        logger.debug(f"Requesting total level leaderboard (limit={limit})")

        leaderboard_data = await leaderboard_service.get_top_by_total_level(
            limit
        )

        leaderboard = [
            TotalLevelLeaderboardEntryResponse(**entry)
            for entry in leaderboard_data
        ]

        return TotalLevelLeaderboardResponse(leaderboard=leaderboard)

    except Exception as e:
        logger.error(f"Error getting total level leaderboard: {e}")
        raise


@router.get("/skill/{skill_name}", response_model=SkillLeaderboardResponse)
async def get_skill_leaderboard(
    skill_name: str,
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of players to return",
    ),
    leaderboard_service: LeaderboardService = Depends(get_leaderboard_service),
) -> SkillLeaderboardResponse:
    """
    Get leaderboard of top players for a specific skill.

    This endpoint returns the top players ranked by their experience
    (or level if experience not available) in the specified skill,
    using their most recent hiscore data.

    Args:
        skill_name: Name of the skill (e.g., 'attack', 'strength', 'mining')
        limit: Maximum number of players to return (1-1000)
        leaderboard_service: Leaderboard service dependency

    Returns:
        SkillLeaderboardResponse: Leaderboard data for the skill
    """
    try:
        logger.debug(
            f"Requesting leaderboard for skill {skill_name} (limit={limit})"
        )

        leaderboard_data = await leaderboard_service.get_top_by_skill(
            skill_name, limit
        )

        leaderboard = [
            SkillLeaderboardEntryResponse(**entry)
            for entry in leaderboard_data
        ]

        return SkillLeaderboardResponse(
            skill=skill_name, leaderboard=leaderboard
        )

    except Exception as e:
        logger.error(f"Error getting skill leaderboard for {skill_name}: {e}")
        raise


@router.get("/skills/all", response_model=AllSkillLeaderboardsResponse)
async def get_all_skill_leaderboards(
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of players to return per skill",
    ),
    leaderboard_service: LeaderboardService = Depends(get_leaderboard_service),
) -> AllSkillLeaderboardsResponse:
    """
    Get leaderboards for all skills.

    This endpoint returns leaderboards for all OSRS skills,
    with the top players ranked by experience (or level) for each skill.

    Args:
        limit: Maximum number of players to return per skill (1-1000)
        leaderboard_service: Leaderboard service dependency

    Returns:
        AllSkillLeaderboardsResponse: Leaderboards for all skills
    """
    try:
        logger.debug(f"Requesting all skill leaderboards (limit={limit})")

        leaderboards_data = (
            await leaderboard_service.get_all_skill_leaderboards(limit)
        )

        leaderboards = {
            skill: [
                SkillLeaderboardEntryResponse(**entry) for entry in entries
            ]
            for skill, entries in leaderboards_data.items()
        }

        return AllSkillLeaderboardsResponse(leaderboards=leaderboards)

    except Exception as e:
        logger.error(f"Error getting all skill leaderboards: {e}")
        raise
