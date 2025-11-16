import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import (
    BadRequestError,
    HistoryServiceError,
    InsufficientDataError,
    OSRSPlayerNotFoundError,
    PlayerNotFoundError,
)
from app.models.base import get_db_session
from app.services.player import (
    PlayerService,
    get_player_service,
)
from app.services.player.history import (
    HistoryService,
)
from app.services.player.records import (
    RecordsService,
    get_records_service,
)
from app.utils.common import parse_iso_datetime

logger = logging.getLogger(__name__)


async def get_history_service(
    db_session: AsyncSession = Depends(get_db_session),
) -> HistoryService:
    """Dependency injection for HistoryService."""
    return HistoryService(db_session)


async def get_records_service_dep(
    db_session: AsyncSession = Depends(get_db_session),
) -> RecordsService:
    """Dependency injection for RecordsService."""
    return RecordsService(db_session)


# Request/Response models
class ProgressPeriodResponse(BaseModel):
    """Response model for progress period information."""

    start_date: str = Field(
        description="Start date of the analysis period (ISO format)"
    )
    end_date: str = Field(
        description="End date of the analysis period (ISO format)"
    )
    days_elapsed: int = Field(
        description="Number of days in the analysis period"
    )


class ProgressRecordsResponse(BaseModel):
    """Response model for progress record information."""

    start_record_id: Optional[int] = Field(
        None, description="ID of the starting hiscore record"
    )
    end_record_id: Optional[int] = Field(
        None, description="ID of the ending hiscore record"
    )
    start_fetched_at: Optional[str] = Field(
        None, description="When the start record was fetched (ISO format)"
    )
    end_fetched_at: Optional[str] = Field(
        None, description="When the end record was fetched (ISO format)"
    )


class ProgressDataResponse(BaseModel):
    """Response model for progress data."""

    experience_gained: Dict[str, int] = Field(
        description="Experience gained per skill"
    )
    levels_gained: Dict[str, int] = Field(
        description="Levels gained per skill"
    )
    boss_kills_gained: Dict[str, int] = Field(description="Boss kills gained")


class ProgressRatesResponse(BaseModel):
    """Response model for progress rates."""

    daily_experience: Dict[str, float] = Field(
        description="Daily experience rates per skill"
    )
    daily_boss_kills: Dict[str, float] = Field(
        description="Daily boss kill rates"
    )


class ProgressAnalysisResponse(BaseModel):
    """Response model for progress analysis."""

    username: str = Field(description="Player username")
    period: ProgressPeriodResponse = Field(
        description="Analysis period information"
    )
    records: ProgressRecordsResponse = Field(description="Record information")
    progress: ProgressDataResponse = Field(description="Progress data")
    rates: ProgressRatesResponse = Field(description="Progress rates")


class SkillTimelineEntry(BaseModel):
    """Response model for skill timeline entry."""

    date: str = Field(description="Date of the record (ISO format)")
    level: Optional[int] = Field(None, description="Skill level at this date")
    experience: Optional[int] = Field(
        None, description="Skill experience at this date"
    )


class SkillProgressDataResponse(BaseModel):
    """Response model for skill progress data."""

    experience_gained: int = Field(description="Total experience gained")
    levels_gained: int = Field(description="Total levels gained")
    daily_experience_rate: float = Field(description="Daily experience rate")


class SkillProgressResponse(BaseModel):
    """Response model for skill progress analysis."""

    username: str = Field(description="Player username")
    skill: str = Field(description="Skill name")
    period_days: int = Field(description="Number of days analyzed")
    total_records: int = Field(
        description="Number of records used in analysis"
    )
    progress: SkillProgressDataResponse = Field(description="Progress data")
    timeline: List[SkillTimelineEntry] = Field(
        description="Timeline of skill progress"
    )


class BossTimelineEntry(BaseModel):
    """Response model for boss timeline entry."""

    date: str = Field(description="Date of the record (ISO format)")
    kc: Optional[int] = Field(None, description="Boss kill count at this date")


class BossProgressDataResponse(BaseModel):
    """Response model for boss progress data."""

    kills_gained: int = Field(description="Total kills gained")
    daily_kill_rate: float = Field(description="Daily kill rate")


class BossProgressResponse(BaseModel):
    """Response model for boss progress analysis."""

    username: str = Field(description="Player username")
    boss: str = Field(description="Boss name")
    period_days: int = Field(description="Number of days analyzed")
    total_records: int = Field(
        description="Number of records used in analysis"
    )
    progress: BossProgressDataResponse = Field(description="Progress data")
    timeline: List[BossTimelineEntry] = Field(
        description="Timeline of boss progress"
    )


class SkillRecordResponse(BaseModel):
    """Response model for a skill record."""

    skill: str = Field(description="Skill name")
    exp_gain: int = Field(description="Experience gained on this day")
    date: str = Field(description="Date of the record (ISO format)")
    start_exp: int = Field(description="Starting experience")
    end_exp: int = Field(description="Ending experience")


class PeriodRecordsResponse(BaseModel):
    """Response model for records in a time period."""

    day: Dict[str, SkillRecordResponse] = Field(
        description="Top exp gains in the last day"
    )
    week: Dict[str, SkillRecordResponse] = Field(
        description="Top exp gains in the last week"
    )
    month: Dict[str, SkillRecordResponse] = Field(
        description="Top exp gains in the last month"
    )
    year: Dict[str, SkillRecordResponse] = Field(
        description="Top exp gains in the last year"
    )


class PlayerRecordsResponse(BaseModel):
    """Response model for player records."""

    username: str = Field(description="Player username")
    records: PeriodRecordsResponse = Field(
        description="Records for each time period"
    )


# Router
router = APIRouter(prefix="/players", tags=["history"])


@router.get("/{username}/history", response_model=ProgressAnalysisResponse)
async def get_player_history(
    username: str,
    start_date: Optional[str] = Query(
        None,
        description="Start date for analysis (ISO format, e.g., '2024-01-01T00:00:00Z'). "
        "If not provided, defaults to 30 days ago.",
    ),
    end_date: Optional[str] = Query(
        None,
        description="End date for analysis (ISO format, e.g., '2024-01-31T23:59:59Z'). "
        "If not provided, defaults to current time.",
    ),
    days: Optional[int] = Query(
        None,
        description="Number of days to look back from end_date (alternative to start_date). "
        "If provided, overrides start_date.",
        ge=1,
        le=365,
    ),
    history_service: HistoryService = Depends(get_history_service),
    player_service: PlayerService = Depends(get_player_service),
) -> ProgressAnalysisResponse:
    """
    Get historical progress analysis for a player.

    This endpoint analyzes a player's progress between two dates, calculating
    experience gained, levels gained, boss kills gained, and daily rates.
    If the player doesn't exist in the database but exists in OSRS, they will
    be automatically added.

    Args:
        username: OSRS player username
        start_date: Start date for analysis (ISO format)
        end_date: End date for analysis (ISO format)
        days: Alternative to start_date - number of days to look back
        history_service: History service dependency
        player_service: Player service dependency

    Returns:
        ProgressAnalysisResponse: Progress analysis data (returns whatever data is available,
        even if less than requested)

    Raises:
        400 Bad Request: Invalid date parameters or username format
        404 Not Found: Player not found in OSRS hiscores
        422 Unprocessable Entity: No data available at all
        502 Bad Gateway: OSRS API unavailable
        500 Internal Server Error: Service errors
    """
    try:
        logger.debug(f"Requesting history for player: {username}")

        # Ensure player exists (auto-add if they exist in OSRS)
        await player_service.ensure_player_exists(username)

        # Parse and validate dates
        now = datetime.now(timezone.utc)

        if end_date:
            try:
                parsed_end_date = parse_iso_datetime(end_date)
            except ValueError:
                raise BadRequestError(
                    "Invalid end_date format. Use ISO format like '2024-01-31T23:59:59Z'"
                )
        else:
            parsed_end_date = now

        if days:
            # Use days parameter to calculate start_date
            parsed_start_date = parsed_end_date - timedelta(days=days)
        elif start_date:
            try:
                parsed_start_date = parse_iso_datetime(start_date)
            except ValueError:
                raise BadRequestError(
                    "Invalid start_date format. Use ISO format like '2024-01-01T00:00:00Z'"
                )
        else:
            # Default to 30 days ago
            parsed_start_date = parsed_end_date - timedelta(days=30)

        # Validate date range
        if parsed_start_date >= parsed_end_date:
            raise BadRequestError("Start date must be before end date")

        # Check if date range is reasonable (not more than 1 year)
        if (parsed_end_date - parsed_start_date).days > 365:
            raise BadRequestError("Date range cannot exceed 365 days")

        # Get progress analysis
        progress = await history_service.get_progress_between_dates(
            username, parsed_start_date, parsed_end_date
        )

        # Convert to response format
        progress_dict = progress.to_dict()

        response = ProgressAnalysisResponse(
            username=progress_dict["username"],
            period=ProgressPeriodResponse(**progress_dict["period"]),
            records=ProgressRecordsResponse(**progress_dict["records"]),
            progress=ProgressDataResponse(**progress_dict["progress"]),
            rates=ProgressRatesResponse(**progress_dict["rates"]),
        )

        logger.debug(f"Successfully retrieved history for player: {username}")
        return response

    except (
        BadRequestError,
        PlayerNotFoundError,
        OSRSPlayerNotFoundError,
        InsufficientDataError,
        HistoryServiceError,
    ):
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting history for {username}: {e}")
        raise HistoryServiceError(f"Failed to analyze progress: {e}")


@router.get(
    "/{username}/history/skills/{skill}", response_model=SkillProgressResponse
)
async def get_skill_progress(
    username: str,
    skill: str,
    days: int = Query(
        30, description="Number of days to analyze", ge=1, le=365
    ),
    history_service: HistoryService = Depends(get_history_service),
    player_service: PlayerService = Depends(get_player_service),
) -> SkillProgressResponse:
    """
    Get progress analysis for a specific skill.

    This endpoint analyzes a player's progress in a specific skill over a
    specified number of days, including experience gained, levels gained,
    and a timeline of progress. If the player doesn't exist in the database
    but exists in OSRS, they will be automatically added.

    Args:
        username: OSRS player username
        skill: Skill name (e.g., 'attack', 'defence', 'magic')
        days: Number of days to analyze (1-365)
        history_service: History service dependency
        player_service: Player service dependency

    Returns:
        SkillProgressResponse: Skill progress analysis data (returns whatever data is available,
        even if less than requested. period_days reflects actual data available)

    Raises:
        400 Bad Request: Invalid parameters or username format
        404 Not Found: Player not found in OSRS hiscores
        502 Bad Gateway: OSRS API unavailable
        500 Internal Server Error: Service errors
    """
    try:
        logger.debug(
            f"Requesting {skill} progress for player: {username} over {days} days"
        )

        # Ensure player exists (auto-add if they exist in OSRS)
        await player_service.ensure_player_exists(username)

        # Validate skill name
        skill = skill.lower().strip()
        if not skill:
            raise BadRequestError("Skill name cannot be empty")

        # Get skill progress
        progress = await history_service.get_skill_progress(
            username, skill, days
        )

        # Convert to response format
        progress_dict = progress.to_dict()

        response = SkillProgressResponse(
            username=progress_dict["username"],
            skill=progress_dict["skill"],
            period_days=progress_dict["period_days"],
            total_records=progress_dict["total_records"],
            progress=SkillProgressDataResponse(**progress_dict["progress"]),
            timeline=[
                SkillTimelineEntry(**entry)
                for entry in progress_dict["timeline"]
            ],
        )

        logger.debug(
            f"Successfully retrieved {skill} progress for player: {username}"
        )
        return response

    except (
        BadRequestError,
        PlayerNotFoundError,
        OSRSPlayerNotFoundError,
        InsufficientDataError,
        HistoryServiceError,
    ):
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error getting {skill} progress for {username}: {e}"
        )
        raise HistoryServiceError(f"Failed to analyze skill progress: {e}")


@router.get(
    "/{username}/history/bosses/{boss}", response_model=BossProgressResponse
)
async def get_boss_progress(
    username: str,
    boss: str,
    days: int = Query(
        30, description="Number of days to analyze", ge=1, le=365
    ),
    history_service: HistoryService = Depends(get_history_service),
    player_service: PlayerService = Depends(get_player_service),
) -> BossProgressResponse:
    """
    Get progress analysis for a specific boss.

    This endpoint analyzes a player's progress against a specific boss over a
    specified number of days, including kills gained and a timeline of progress.
    If the player doesn't exist in the database but exists in OSRS, they will
    be automatically added.

    Args:
        username: OSRS player username
        boss: Boss name (e.g., 'zulrah', 'vorkath', 'chambers_of_xeric')
        days: Number of days to analyze (1-365)
        history_service: History service dependency
        player_service: Player service dependency

    Returns:
        BossProgressResponse: Boss progress analysis data (returns whatever data is available,
        even if less than requested. period_days reflects actual data available)

    Raises:
        400 Bad Request: Invalid parameters or username format
        404 Not Found: Player not found in OSRS hiscores
        502 Bad Gateway: OSRS API unavailable
        500 Internal Server Error: Service errors
    """
    try:
        logger.debug(
            f"Requesting {boss} progress for player: {username} over {days} days"
        )

        # Ensure player exists (auto-add if they exist in OSRS)
        await player_service.ensure_player_exists(username)

        # Validate boss name
        boss = boss.lower().strip()
        if not boss:
            raise BadRequestError("Boss name cannot be empty")

        # Get boss progress
        progress = await history_service.get_boss_progress(
            username, boss, days
        )

        # Convert to response format
        progress_dict = progress.to_dict()

        response = BossProgressResponse(
            username=progress_dict["username"],
            boss=progress_dict["boss"],
            period_days=progress_dict["period_days"],
            total_records=progress_dict["total_records"],
            progress=BossProgressDataResponse(**progress_dict["progress"]),
            timeline=[
                BossTimelineEntry(**entry)
                for entry in progress_dict["timeline"]
            ],
        )

        logger.debug(
            f"Successfully retrieved {boss} progress for player: {username}"
        )
        return response

    except (
        BadRequestError,
        PlayerNotFoundError,
        OSRSPlayerNotFoundError,
        InsufficientDataError,
        HistoryServiceError,
    ):
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error getting {boss} progress for {username}: {e}"
        )
        raise HistoryServiceError(f"Failed to analyze boss progress: {e}")


@router.get("/{username}/records", response_model=PlayerRecordsResponse)
async def get_player_records(
    username: str,
    records_service: RecordsService = Depends(get_records_service_dep),
    player_service: PlayerService = Depends(get_player_service),
) -> PlayerRecordsResponse:
    """
    Get top exp gains per day for a player across different time periods.

    For each skill, finds the day with the highest exp gain within:
    - Last day (24 hours)
    - Last week (7 days)
    - Last month (30 days)
    - Last year (365 days)

    If the player doesn't exist in the database but exists in OSRS, they will
    be automatically added.

    Args:
        username: OSRS player username
        records_service: Records service dependency
        player_service: Player service dependency

    Returns:
        PlayerRecordsResponse: Records for each time period

    Raises:
        400 Bad Request: Invalid username format
        404 Not Found: Player not found in OSRS hiscores
        502 Bad Gateway: OSRS API unavailable
        500 Internal Server Error: Service errors
    """
    try:
        logger.debug(f"Requesting records for player: {username}")

        # Ensure player exists (auto-add if they exist in OSRS)
        await player_service.ensure_player_exists(username)

        # Get records
        records = await records_service.get_player_records(username)

        # Convert to response format
        records_dict = records.to_dict()

        # Convert skill records to response models
        def convert_period_records(
            period_dict: Dict[str, Dict[str, Any]],
        ) -> Dict[str, SkillRecordResponse]:
            return {
                skill: SkillRecordResponse(**record)
                for skill, record in period_dict.items()
            }

        response = PlayerRecordsResponse(
            username=records_dict["username"],
            records=PeriodRecordsResponse(
                day=convert_period_records(records_dict["records"]["day"]),
                week=convert_period_records(records_dict["records"]["week"]),
                month=convert_period_records(records_dict["records"]["month"]),
                year=convert_period_records(records_dict["records"]["year"]),
            ),
        )

        logger.debug(f"Successfully retrieved records for player: {username}")
        return response

    except (
        PlayerNotFoundError,
        OSRSPlayerNotFoundError,
        HistoryServiceError,
    ):
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting records for {username}: {e}")
        raise HistoryServiceError(f"Failed to get records: {e}")
