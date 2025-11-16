import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import (
    HistoryServiceError,
    PlayerNotFoundError,
)
from app.models.hiscore import HiscoreRecord
from app.models.player import Player
from app.utils.common import ensure_timezone_aware, normalize_username

logger = logging.getLogger(__name__)


class SkillRecord:
    """Data class for a skill record (top exp gain in a day)."""

    def __init__(
        self,
        skill_name: str,
        exp_gain: int,
        date: datetime,
        start_exp: int,
        end_exp: int,
    ):
        self.skill_name = skill_name
        self.exp_gain = exp_gain
        self.date = date
        self.start_exp = start_exp
        self.end_exp = end_exp

    def to_dict(self) -> Dict[str, Any]:
        """Convert skill record to dictionary format."""
        return {
            "skill": self.skill_name,
            "exp_gain": self.exp_gain,
            "date": self.date.isoformat(),
            "start_exp": self.start_exp,
            "end_exp": self.end_exp,
        }


class PlayerRecords:
    """Data class for player records across different time periods."""

    def __init__(self, username: str):
        self.username = username
        self.day_records: Dict[str, SkillRecord] = {}
        self.week_records: Dict[str, SkillRecord] = {}
        self.month_records: Dict[str, SkillRecord] = {}
        self.year_records: Dict[str, SkillRecord] = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert player records to dictionary format."""
        return {
            "username": self.username,
            "records": {
                "day": {
                    skill: record.to_dict()
                    for skill, record in self.day_records.items()
                },
                "week": {
                    skill: record.to_dict()
                    for skill, record in self.week_records.items()
                },
                "month": {
                    skill: record.to_dict()
                    for skill, record in self.month_records.items()
                },
                "year": {
                    skill: record.to_dict()
                    for skill, record in self.year_records.items()
                },
            },
        }


class RecordsService:
    """Service for calculating top exp gains per day within different time periods."""

    def __init__(self, db_session: AsyncSession):
        """
        Initialize the records service.

        Args:
            db_session: Database session for operations
        """
        self.db_session = db_session

    async def get_player_records(self, username: str) -> PlayerRecords:
        """
        Get top exp gains per day for a player across different time periods.

        For each skill, finds the day with the highest exp gain within:
        - Last day (24 hours)
        - Last week (7 days)
        - Last month (30 days)
        - Last year (365 days)

        Args:
            username: OSRS player username

        Returns:
            PlayerRecords: Records for each time period

        Raises:
            PlayerNotFoundError: If player doesn't exist
            HistoryServiceError: For other service errors
        """
        username = normalize_username(username)

        try:
            logger.debug(f"Getting records for player: {username}")

            # Verify player exists
            player_stmt = select(Player).where(Player.username.ilike(username))
            player_result = await self.db_session.execute(player_stmt)
            player = player_result.scalar_one_or_none()

            if not player:
                raise PlayerNotFoundError(username)

            now = datetime.now(timezone.utc)

            # Calculate records for each time period
            day_records = await self._calculate_period_records(
                player.id, now - timedelta(days=1), now
            )
            week_records = await self._calculate_period_records(
                player.id, now - timedelta(days=7), now
            )
            month_records = await self._calculate_period_records(
                player.id, now - timedelta(days=30), now
            )
            year_records = await self._calculate_period_records(
                player.id, now - timedelta(days=365), now
            )

            records = PlayerRecords(username=player.username)
            records.day_records = day_records
            records.week_records = week_records
            records.month_records = month_records
            records.year_records = year_records

            logger.debug(
                f"Successfully calculated records for {username}: "
                f"{len(day_records)} day, {len(week_records)} week, "
                f"{len(month_records)} month, {len(year_records)} year records"
            )

            return records

        except PlayerNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting records for {username}: {e}")
            raise HistoryServiceError(f"Failed to get records: {e}")

    async def _calculate_period_records(
        self, player_id: int, start_date: datetime, end_date: datetime
    ) -> Dict[str, SkillRecord]:
        """
        Calculate top exp gains per day for each skill within a time period.

        Args:
            player_id: Player ID
            start_date: Start of the period
            end_date: End of the period

        Returns:
            Dict mapping skill names to SkillRecord objects
        """
        # Get all records in the period
        records = await self._get_records_in_period(
            player_id, start_date, end_date
        )

        if len(records) < 2:
            # Need at least 2 records to calculate gains
            return {}

        # Group records by day (date only, ignoring time)
        records_by_day: Dict[datetime, List[HiscoreRecord]] = defaultdict(list)
        for record in records:
            # Normalize to date (midnight UTC)
            day = ensure_timezone_aware(record.fetched_at).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            records_by_day[day].append(record)

        # For each day, calculate exp gains between consecutive records
        # Then find the maximum gain per skill across all days
        max_gains: Dict[str, SkillRecord] = {}

        for day, day_records in records_by_day.items():
            # Sort records by time within the day
            day_records.sort(key=lambda r: ensure_timezone_aware(r.fetched_at))

            # Calculate exp gains between consecutive records in this day
            for i in range(len(day_records) - 1):
                start_record = day_records[i]
                end_record = day_records[i + 1]

                # Calculate gains for all skills
                gains = self._calculate_exp_gains(start_record, end_record)

                for skill_name, exp_gain in gains.items():
                    if exp_gain > 0:
                        # Update max gain if this is higher
                        if (
                            skill_name not in max_gains
                            or exp_gain > max_gains[skill_name].exp_gain
                        ):
                            start_exp = (
                                start_record.get_skill_experience(skill_name)
                                or 0
                            )
                            end_exp = (
                                end_record.get_skill_experience(skill_name)
                                or 0
                            )
                            max_gains[skill_name] = SkillRecord(
                                skill_name=skill_name,
                                exp_gain=exp_gain,
                                date=day,
                                start_exp=start_exp,
                                end_exp=end_exp,
                            )

        return max_gains

    def _calculate_exp_gains(
        self, start_record: HiscoreRecord, end_record: HiscoreRecord
    ) -> Dict[str, int]:
        """
        Calculate exp gains between two records for all skills.

        Args:
            start_record: Starting record
            end_record: Ending record

        Returns:
            Dict mapping skill names to exp gains
        """
        gains: Dict[str, int] = {}

        # Calculate overall gain
        start_overall = start_record.overall_experience or 0
        end_overall = end_record.overall_experience or 0
        overall_gain = max(0, end_overall - start_overall)
        if overall_gain > 0:
            gains["overall"] = overall_gain

        # Calculate individual skill gains
        start_skills = start_record.skills_data or {}
        end_skills = end_record.skills_data or {}

        # Get all skills that exist in either record
        all_skills = set(start_skills.keys()) | set(end_skills.keys())

        for skill_name in all_skills:
            start_exp = start_skills.get(skill_name, {}).get("experience") or 0
            end_exp = end_skills.get(skill_name, {}).get("experience") or 0
            exp_gain = max(0, end_exp - start_exp)
            if exp_gain > 0:
                gains[skill_name] = exp_gain

        return gains

    async def _get_records_in_period(
        self, player_id: int, start_date: datetime, end_date: datetime
    ) -> List[HiscoreRecord]:
        """
        Get all hiscore records for a player within a time period.

        Args:
            player_id: Player ID
            start_date: Start of the period
            end_date: End of the period

        Returns:
            List of HiscoreRecord objects, ordered by fetched_at
        """
        stmt = (
            select(HiscoreRecord)
            .where(
                and_(
                    HiscoreRecord.player_id == player_id,
                    HiscoreRecord.fetched_at >= start_date,
                    HiscoreRecord.fetched_at <= end_date,
                )
            )
            .order_by(HiscoreRecord.fetched_at.asc())
        )

        result = await self.db_session.execute(stmt)
        return list(result.scalars().all())


async def get_records_service(db_session: AsyncSession) -> RecordsService:
    """
    Dependency injection function for FastAPI.

    Args:
        db_session: Database session

    Returns:
        RecordsService: Configured records service instance
    """
    return RecordsService(db_session)
