import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import (
    HistoryServiceError,
    InsufficientDataError,
    PlayerNotFoundError,
)
from app.models.hiscore import HiscoreRecord
from app.models.player import Player
from app.utils.common import ensure_timezone_aware, normalize_username

logger = logging.getLogger(__name__)


class ProgressAnalysis:
    """Data class for progress analysis results."""

    def __init__(
        self,
        username: str,
        start_date: datetime,
        end_date: datetime,
        start_record: Optional[HiscoreRecord] = None,
        end_record: Optional[HiscoreRecord] = None,
    ):
        self.username = username
        self.start_date = start_date
        self.end_date = end_date
        self.start_record = start_record
        self.end_record = end_record
        self.days_elapsed = (end_date - start_date).days or 1

    @property
    def experience_gained(self) -> Dict[str, int]:
        """Calculate experience gained for each skill."""
        if not self.start_record or not self.end_record:
            return {}

        gains = {}
        start_skills = self.start_record.skills_data or {}
        end_skills = self.end_record.skills_data or {}

        # Calculate overall experience gain
        start_overall = self.start_record.overall_experience or 0
        end_overall = self.end_record.overall_experience or 0
        gains["overall"] = max(0, end_overall - start_overall)

        # Calculate individual skill gains
        for skill_name in end_skills.keys():
            start_exp = start_skills.get(skill_name, {}).get("experience") or 0
            end_exp = end_skills.get(skill_name, {}).get("experience") or 0
            gains[skill_name] = max(0, end_exp - start_exp)

        return gains

    @property
    def levels_gained(self) -> Dict[str, int]:
        """Calculate levels gained for each skill."""
        if not self.start_record or not self.end_record:
            return {}

        gains = {}
        start_skills = self.start_record.skills_data or {}
        end_skills = self.end_record.skills_data or {}

        # Calculate overall level gain
        start_overall = self.start_record.overall_level or 0
        end_overall = self.end_record.overall_level or 0
        gains["overall"] = max(0, end_overall - start_overall)

        # Calculate individual skill level gains
        for skill_name in end_skills.keys():
            start_level = start_skills.get(skill_name, {}).get("level") or 1
            end_level = end_skills.get(skill_name, {}).get("level") or 1
            gains[skill_name] = max(0, end_level - start_level)

        return gains

    @property
    def boss_kills_gained(self) -> Dict[str, int]:
        """Calculate boss kills gained."""
        if not self.start_record or not self.end_record:
            return {}

        gains = {}
        start_bosses = self.start_record.bosses_data or {}
        end_bosses = self.end_record.bosses_data or {}

        for boss_name in end_bosses.keys():
            start_boss_data = start_bosses.get(boss_name, {})
            end_boss_data = end_bosses.get(boss_name, {})
            start_kc = start_boss_data.get("kc") or 0
            end_kc = end_boss_data.get("kc") or 0
            gains[boss_name] = max(0, end_kc - start_kc)

        return gains

    @property
    def daily_experience_rates(self) -> Dict[str, float]:
        """Calculate daily experience rates."""
        exp_gains = self.experience_gained
        return {
            skill: gain / self.days_elapsed
            for skill, gain in exp_gains.items()
        }

    @property
    def daily_boss_rates(self) -> Dict[str, float]:
        """Calculate daily boss kill rates."""
        boss_gains = self.boss_kills_gained
        return {
            boss: gain / self.days_elapsed for boss, gain in boss_gains.items()
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert progress analysis to dictionary format."""
        return {
            "username": self.username,
            "period": {
                "start_date": self.start_date.isoformat(),
                "end_date": self.end_date.isoformat(),
                "days_elapsed": self.days_elapsed,
            },
            "records": {
                "start_record_id": (
                    self.start_record.id if self.start_record else None
                ),
                "end_record_id": (
                    self.end_record.id if self.end_record else None
                ),
                "start_fetched_at": (
                    self.start_record.fetched_at.isoformat()
                    if self.start_record
                    else None
                ),
                "end_fetched_at": (
                    self.end_record.fetched_at.isoformat()
                    if self.end_record
                    else None
                ),
            },
            "progress": {
                "experience_gained": self.experience_gained,
                "levels_gained": self.levels_gained,
                "boss_kills_gained": self.boss_kills_gained,
            },
            "rates": {
                "daily_experience": self.daily_experience_rates,
                "daily_boss_kills": self.daily_boss_rates,
            },
        }


class SkillProgress:
    """Data class for skill-specific progress analysis."""

    def __init__(
        self,
        username: str,
        skill_name: str,
        records: List[HiscoreRecord],
        days: int,
    ):
        self.username = username
        self.skill_name = skill_name

        # Ensure all fetched_at are timezone-aware for sorting
        self.records = sorted(
            records, key=lambda r: ensure_timezone_aware(r.fetched_at)
        )
        self.days = days

    @property
    def total_experience_gained(self) -> int:
        """Calculate total experience gained over the period."""
        if len(self.records) < 2:
            return 0

        start_exp = self.records[0].get_skill_experience(self.skill_name) or 0
        end_exp = self.records[-1].get_skill_experience(self.skill_name) or 0
        return max(0, end_exp - start_exp)

    @property
    def levels_gained(self) -> int:
        """Calculate levels gained over the period."""
        if len(self.records) < 2:
            return 0

        start_level = self.records[0].get_skill_level(self.skill_name) or 1
        end_level = self.records[-1].get_skill_level(self.skill_name) or 1
        return max(0, end_level - start_level)

    @property
    def daily_experience_rate(self) -> float:
        """Calculate daily experience rate."""
        return self.total_experience_gained / max(1, self.days)

    def to_dict(self) -> Dict[str, Any]:
        """Convert skill progress to dictionary format."""
        return {
            "username": self.username,
            "skill": self.skill_name,
            "period_days": self.days,
            "total_records": len(self.records),
            "progress": {
                "experience_gained": self.total_experience_gained,
                "levels_gained": self.levels_gained,
                "daily_experience_rate": self.daily_experience_rate,
            },
            "timeline": [
                {
                    "date": record.fetched_at.isoformat(),
                    "level": record.get_skill_level(self.skill_name),
                    "experience": record.get_skill_experience(self.skill_name),
                }
                for record in self.records
            ],
        }


class BossProgress:
    """Data class for boss-specific progress analysis."""

    def __init__(
        self,
        username: str,
        boss_name: str,
        records: List[HiscoreRecord],
        days: int,
    ):
        self.username = username
        self.boss_name = boss_name

        # Ensure all fetched_at are timezone-aware for sorting
        self.records = sorted(
            records, key=lambda r: ensure_timezone_aware(r.fetched_at)
        )
        self.days = days

    @property
    def total_kills_gained(self) -> int:
        """Calculate total kills gained over the period."""
        if len(self.records) < 2:
            return 0

        start_kc = self.records[0].get_boss_kills(self.boss_name) or 0
        end_kc = self.records[-1].get_boss_kills(self.boss_name) or 0
        return max(0, end_kc - start_kc)

    @property
    def daily_kill_rate(self) -> float:
        """Calculate daily kill rate."""
        return self.total_kills_gained / max(1, self.days)

    def to_dict(self) -> Dict[str, Any]:
        """Convert boss progress to dictionary format."""
        return {
            "username": self.username,
            "boss": self.boss_name,
            "period_days": self.days,
            "total_records": len(self.records),
            "progress": {
                "kills_gained": self.total_kills_gained,
                "daily_kill_rate": self.daily_kill_rate,
            },
            "timeline": [
                {
                    "date": record.fetched_at.isoformat(),
                    "kc": record.get_boss_kills(self.boss_name),
                }
                for record in self.records
            ],
        }


class HistoryService:
    """Service for analyzing historical OSRS player progress."""

    def __init__(self, db_session: AsyncSession):
        """
        Initialize the history service.

        Args:
            db_session: Database session for operations
        """
        self.db_session = db_session

    async def get_progress_between_dates(
        self, username: str, start_date: datetime, end_date: datetime
    ) -> ProgressAnalysis:
        """
        Calculate progress between two specific dates.

        Returns whatever data is available, even if it's less than requested.
        If only one record is available, it will be used for both start and end.
        If records are the same, progress will be zero but data will still be returned.

        Args:
            username: OSRS player username
            start_date: Start date for progress analysis
            end_date: End date for progress analysis

        Returns:
            ProgressAnalysis: Calculated progress data (may be partial)

        Raises:
            PlayerNotFoundError: If player doesn't exist
            InsufficientDataError: If no data available at all
            HistoryServiceError: For other service errors
        """
        username = normalize_username(username)

        if start_date >= end_date:
            raise HistoryServiceError("Start date must be before end date")

        try:
            logger.debug(
                f"Calculating progress for {username} between {start_date} and {end_date}"
            )

            # Verify player exists
            player_stmt = select(Player).where(Player.username.ilike(username))
            player_result = await self.db_session.execute(player_stmt)
            player = player_result.scalar_one_or_none()

            if not player:
                raise PlayerNotFoundError(username)

            # Find records closest to start and end dates
            start_record = await self._get_record_closest_to_date(
                player.id, start_date, before=True
            )
            end_record = await self._get_record_closest_to_date(
                player.id, end_date, before=True
            )

            # If we don't have both records, adjust dates to available data
            if not start_record and not end_record:
                raise InsufficientDataError(
                    f"No data available for progress analysis between {start_date} and {end_date}"
                )

            # If we can't find a start record (requested date is before any data),
            # use the oldest available record instead of the end record
            if not start_record:
                oldest_record = await self._get_oldest_record(player.id)
                if oldest_record:
                    start_record = oldest_record
                    # Ensure timezone consistency
                    start_date = ensure_timezone_aware(
                        oldest_record.fetched_at
                    )
                else:
                    # Fallback to end_record if no oldest record found
                    start_record = end_record
                    if end_record:
                        start_date = ensure_timezone_aware(
                            end_record.fetched_at
                        )
            elif not end_record:
                end_record = start_record
                if start_record:
                    end_date = ensure_timezone_aware(start_record.fetched_at)

            # If records are the same, still return the data (just no progress)
            # At this point, both start_record and end_record are guaranteed to be not None
            assert start_record is not None and end_record is not None
            if start_record.id == end_record.id:
                # Use the actual fetched_at date for both
                actual_date = ensure_timezone_aware(start_record.fetched_at)
                start_date = actual_date
                end_date = actual_date

            progress = ProgressAnalysis(
                username=player.username,
                start_date=start_date,
                end_date=end_date,
                start_record=start_record,
                end_record=end_record,
            )

            logger.debug(
                f"Progress calculated for {username}: "
                f"{progress.experience_gained.get('overall', 0)} overall XP gained"
            )

            return progress

        except (PlayerNotFoundError, InsufficientDataError):
            raise
        except Exception as e:
            logger.error(f"Error calculating progress for {username}: {e}")
            raise HistoryServiceError(f"Failed to calculate progress: {e}")

    async def get_skill_progress(
        self, username: str, skill: str, days: int
    ) -> SkillProgress:
        """
        Get progress for a specific skill over a number of days.

        Returns whatever data is available, even if it's less than requested.
        The period_days in the response will reflect the actual data available.

        Args:
            username: OSRS player username
            skill: Skill name (e.g., 'attack', 'defence')
            days: Number of days to look back (requested)

        Returns:
            SkillProgress: Skill-specific progress data (may be partial)

        Raises:
            PlayerNotFoundError: If player doesn't exist
            HistoryServiceError: For other service errors
        """
        username = normalize_username(username)

        if not skill:
            raise HistoryServiceError("Skill name cannot be empty")

        if days <= 0:
            raise HistoryServiceError("Days must be positive")

        skill = skill.lower().strip()

        try:
            logger.debug(
                f"Getting {skill} progress for {username} over {days} days"
            )

            # Verify player exists
            player_stmt = select(Player).where(Player.username.ilike(username))
            player_result = await self.db_session.execute(player_stmt)
            player = player_result.scalar_one_or_none()

            if not player:
                raise PlayerNotFoundError(username)

            # Get records from the last N days
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            records = await self._get_records_since_date(
                player.id, cutoff_date
            )

            # Filter records that have data for this skill
            skill_records = [
                record
                for record in records
                if record.get_skill_data(skill) is not None
            ]

            # If we have no records, try to get the most recent record regardless of date
            if len(skill_records) == 0:
                # Get the most recent record with this skill data
                stmt = (
                    select(HiscoreRecord)
                    .where(HiscoreRecord.player_id == player.id)
                    .order_by(HiscoreRecord.fetched_at.desc())
                )
                result = await self.db_session.execute(stmt)
                all_records = list(result.scalars().all())
                skill_records = [
                    record
                    for record in all_records
                    if record.get_skill_data(skill) is not None
                ]
                # If we found records, calculate actual days based on oldest record
                if skill_records:

                    oldest_record = min(
                        skill_records,
                        key=lambda r: ensure_timezone_aware(r.fetched_at),
                    )
                    oldest_dt = ensure_timezone_aware(oldest_record.fetched_at)
                    actual_days = (datetime.now(timezone.utc) - oldest_dt).days
                    days = max(1, actual_days)

            # Calculate actual period based on available data
            if len(skill_records) > 0:
                oldest_record = min(
                    skill_records,
                    key=lambda r: ensure_timezone_aware(r.fetched_at),
                )
                newest_record = max(
                    skill_records,
                    key=lambda r: ensure_timezone_aware(r.fetched_at),
                )
                oldest_dt = ensure_timezone_aware(oldest_record.fetched_at)
                newest_dt = ensure_timezone_aware(newest_record.fetched_at)
                actual_days = (newest_dt - oldest_dt).days
                if actual_days > 0:
                    days = actual_days
                elif len(skill_records) == 1:
                    # Single record, use days from now
                    days = max(
                        1, (datetime.now(timezone.utc) - oldest_dt).days
                    )

            progress = SkillProgress(
                username=player.username,
                skill_name=skill,
                records=skill_records,
                days=days,
            )

            logger.debug(
                f"{skill.title()} progress for {username}: "
                f"{progress.total_experience_gained} XP gained, "
                f"{progress.levels_gained} levels gained"
            )

            return progress

        except (PlayerNotFoundError, InsufficientDataError):
            raise
        except Exception as e:
            logger.error(f"Error getting {skill} progress for {username}: {e}")
            raise HistoryServiceError(f"Failed to get {skill} progress: {e}")

    async def get_boss_progress(
        self, username: str, boss: str, days: int
    ) -> BossProgress:
        """
        Get progress for a specific boss over a number of days.

        Returns whatever data is available, even if it's less than requested.
        The period_days in the response will reflect the actual data available.

        Args:
            username: OSRS player username
            boss: Boss name (e.g., 'zulrah', 'vorkath')
            days: Number of days to look back (requested)

        Returns:
            BossProgress: Boss-specific progress data (may be partial)

        Raises:
            PlayerNotFoundError: If player doesn't exist
            HistoryServiceError: For other service errors
        """
        username = normalize_username(username)

        if not boss:
            raise HistoryServiceError("Boss name cannot be empty")

        if days <= 0:
            raise HistoryServiceError("Days must be positive")

        boss = boss.lower().strip()

        try:
            logger.debug(
                f"Getting {boss} progress for {username} over {days} days"
            )

            # Verify player exists
            player_stmt = select(Player).where(Player.username.ilike(username))
            player_result = await self.db_session.execute(player_stmt)
            player = player_result.scalar_one_or_none()

            if not player:
                raise PlayerNotFoundError(username)

            # Get records from the last N days
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            records = await self._get_records_since_date(
                player.id, cutoff_date
            )

            # Filter records that have data for this boss
            boss_records = [
                record
                for record in records
                if record.get_boss_data(boss) is not None
            ]

            # If we have no records, try to get the most recent record regardless of date
            if len(boss_records) == 0:
                # Get the most recent record with this boss data
                stmt = (
                    select(HiscoreRecord)
                    .where(HiscoreRecord.player_id == player.id)
                    .order_by(HiscoreRecord.fetched_at.desc())
                )
                result = await self.db_session.execute(stmt)
                all_records = list(result.scalars().all())
                boss_records = [
                    record
                    for record in all_records
                    if record.get_boss_data(boss) is not None
                ]
                # If we found records, calculate actual days based on oldest record
                if boss_records:

                    oldest_record = min(
                        boss_records,
                        key=lambda r: ensure_timezone_aware(r.fetched_at),
                    )
                    oldest_dt = ensure_timezone_aware(oldest_record.fetched_at)
                    actual_days = (datetime.now(timezone.utc) - oldest_dt).days
                    days = max(1, actual_days)

            # Calculate actual period based on available data
            if len(boss_records) > 0:
                oldest_record = min(
                    boss_records,
                    key=lambda r: ensure_timezone_aware(r.fetched_at),
                )
                newest_record = max(
                    boss_records,
                    key=lambda r: ensure_timezone_aware(r.fetched_at),
                )
                oldest_dt = ensure_timezone_aware(oldest_record.fetched_at)
                newest_dt = ensure_timezone_aware(newest_record.fetched_at)
                actual_days = (newest_dt - oldest_dt).days
                if actual_days > 0:
                    days = actual_days
                elif len(boss_records) == 1:
                    # Single record, use days from now
                    days = max(
                        1, (datetime.now(timezone.utc) - oldest_dt).days
                    )

            progress = BossProgress(
                username=player.username,
                boss_name=boss,
                records=boss_records,
                days=days,
            )

            logger.debug(
                f"{boss.title()} progress for {username}: "
                f"{progress.total_kills_gained} kills gained"
            )

            return progress

        except (PlayerNotFoundError, InsufficientDataError):
            raise
        except Exception as e:
            logger.error(f"Error getting {boss} progress for {username}: {e}")
            raise HistoryServiceError(f"Failed to get {boss} progress: {e}")

    async def _get_record_closest_to_date(
        self, player_id: int, target_date: datetime, before: bool = True
    ) -> Optional[HiscoreRecord]:
        """
        Get the hiscore record closest to a target date.

        Args:
            player_id: Player ID
            target_date: Target date
            before: If True, get record on or before date; if False, on or after

        Returns:
            Optional[HiscoreRecord]: Closest record or None
        """
        if before:
            # Get most recent record on or before target date
            stmt = (
                select(HiscoreRecord)
                .where(
                    and_(
                        HiscoreRecord.player_id == player_id,
                        HiscoreRecord.fetched_at <= target_date,
                    )
                )
                .order_by(HiscoreRecord.fetched_at.desc())
                .limit(1)
            )
        else:
            # Get earliest record on or after target date
            stmt = (
                select(HiscoreRecord)
                .where(
                    and_(
                        HiscoreRecord.player_id == player_id,
                        HiscoreRecord.fetched_at >= target_date,
                    )
                )
                .order_by(HiscoreRecord.fetched_at.asc())
                .limit(1)
            )

        result = await self.db_session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_records_since_date(
        self, player_id: int, since_date: datetime
    ) -> List[HiscoreRecord]:
        """
        Get all hiscore records for a player since a specific date.

        Args:
            player_id: Player ID
            since_date: Date to get records since

        Returns:
            List[HiscoreRecord]: Records since the date, ordered by fetched_at
        """
        stmt = (
            select(HiscoreRecord)
            .where(
                and_(
                    HiscoreRecord.player_id == player_id,
                    HiscoreRecord.fetched_at >= since_date,
                )
            )
            .order_by(HiscoreRecord.fetched_at.asc())
        )

        result = await self.db_session.execute(stmt)
        return list(result.scalars().all())

    async def _get_oldest_record(
        self, player_id: int
    ) -> Optional[HiscoreRecord]:
        """
        Get the oldest hiscore record for a player.

        Args:
            player_id: Player ID

        Returns:
            Optional[HiscoreRecord]: Oldest record or None
        """
        stmt = (
            select(HiscoreRecord)
            .where(HiscoreRecord.player_id == player_id)
            .order_by(HiscoreRecord.fetched_at.asc())
            .limit(1)
        )

        result = await self.db_session.execute(stmt)
        return result.scalar_one_or_none()


async def get_history_service(db_session: AsyncSession) -> HistoryService:
    """
    Dependency injection function for FastAPI.

    Args:
        db_session: Database session

    Returns:
        HistoryService: Configured history service instance
    """
    return HistoryService(db_session)
