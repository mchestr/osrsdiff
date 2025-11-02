"""History service for analyzing OSRS player progress over time."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.player import Player
from src.models.hiscore import HiscoreRecord

logger = logging.getLogger(__name__)


class HistoryServiceError(Exception):
    """Base exception for history service errors."""

    pass


class PlayerNotFoundError(HistoryServiceError):
    """Raised when a requested player is not found."""

    pass


class InsufficientDataError(HistoryServiceError):
    """Raised when there is insufficient data for progress analysis."""

    pass


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
            start_exp = start_skills.get(skill_name, {}).get("experience", 0)
            end_exp = end_skills.get(skill_name, {}).get("experience", 0)
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
            start_level = start_skills.get(skill_name, {}).get("level", 1)
            end_level = end_skills.get(skill_name, {}).get("level", 1)
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
            start_kc = start_bosses.get(boss_name, {}).get("kill_count", 0)
            end_kc = end_bosses.get(boss_name, {}).get("kill_count", 0)
            gains[boss_name] = max(0, end_kc - start_kc)

        return gains

    @property
    def daily_experience_rates(self) -> Dict[str, float]:
        """Calculate daily experience rates."""
        exp_gains = self.experience_gained
        return {skill: gain / self.days_elapsed for skill, gain in exp_gains.items()}

    @property
    def daily_boss_rates(self) -> Dict[str, float]:
        """Calculate daily boss kill rates."""
        boss_gains = self.boss_kills_gained
        return {boss: gain / self.days_elapsed for boss, gain in boss_gains.items()}

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
                "start_record_id": self.start_record.id if self.start_record else None,
                "end_record_id": self.end_record.id if self.end_record else None,
                "start_fetched_at": (
                    self.start_record.fetched_at.isoformat() if self.start_record else None
                ),
                "end_fetched_at": (
                    self.end_record.fetched_at.isoformat() if self.end_record else None
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
        self.records = sorted(records, key=lambda r: r.fetched_at)
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
        self.records = sorted(records, key=lambda r: r.fetched_at)
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
                    "kill_count": record.get_boss_kills(self.boss_name),
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

        Args:
            username: OSRS player username
            start_date: Start date for progress analysis
            end_date: End date for progress analysis

        Returns:
            ProgressAnalysis: Calculated progress data

        Raises:
            PlayerNotFoundError: If player doesn't exist
            InsufficientDataError: If insufficient data for analysis
            HistoryServiceError: For other service errors
        """
        if not username:
            raise PlayerNotFoundError("Username cannot be empty")

        if start_date >= end_date:
            raise HistoryServiceError("Start date must be before end date")

        username = username.strip()

        try:
            logger.debug(
                f"Calculating progress for {username} between {start_date} and {end_date}"
            )

            # Verify player exists
            player_stmt = select(Player).where(Player.username.ilike(username))
            player_result = await self.db_session.execute(player_stmt)
            player = player_result.scalar_one_or_none()

            if not player:
                raise PlayerNotFoundError(f"Player '{username}' not found")

            # Find records closest to start and end dates
            start_record = await self._get_record_closest_to_date(
                player.id, start_date, before=True
            )
            end_record = await self._get_record_closest_to_date(
                player.id, end_date, before=True
            )

            if not start_record or not end_record:
                raise InsufficientDataError(
                    f"Insufficient data for progress analysis between {start_date} and {end_date}"
                )

            if start_record.id == end_record.id:
                raise InsufficientDataError(
                    "Start and end records are the same - no progress to calculate"
                )

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

        Args:
            username: OSRS player username
            skill: Skill name (e.g., 'attack', 'defence')
            days: Number of days to look back

        Returns:
            SkillProgress: Skill-specific progress data

        Raises:
            PlayerNotFoundError: If player doesn't exist
            InsufficientDataError: If insufficient data for analysis
            HistoryServiceError: For other service errors
        """
        if not username:
            raise PlayerNotFoundError("Username cannot be empty")

        if not skill:
            raise HistoryServiceError("Skill name cannot be empty")

        if days <= 0:
            raise HistoryServiceError("Days must be positive")

        username = username.strip()
        skill = skill.lower().strip()

        try:
            logger.debug(f"Getting {skill} progress for {username} over {days} days")

            # Verify player exists
            player_stmt = select(Player).where(Player.username.ilike(username))
            player_result = await self.db_session.execute(player_stmt)
            player = player_result.scalar_one_or_none()

            if not player:
                raise PlayerNotFoundError(f"Player '{username}' not found")

            # Get records from the last N days
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            records = await self._get_records_since_date(player.id, cutoff_date)

            if len(records) < 2:
                raise InsufficientDataError(
                    f"Insufficient data for {skill} progress analysis (need at least 2 records)"
                )

            # Filter records that have data for this skill
            skill_records = [
                record for record in records
                if record.get_skill_data(skill) is not None
            ]

            if len(skill_records) < 2:
                raise InsufficientDataError(
                    f"Insufficient {skill} data for progress analysis"
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

        Args:
            username: OSRS player username
            boss: Boss name (e.g., 'zulrah', 'vorkath')
            days: Number of days to look back

        Returns:
            BossProgress: Boss-specific progress data

        Raises:
            PlayerNotFoundError: If player doesn't exist
            InsufficientDataError: If insufficient data for analysis
            HistoryServiceError: For other service errors
        """
        if not username:
            raise PlayerNotFoundError("Username cannot be empty")

        if not boss:
            raise HistoryServiceError("Boss name cannot be empty")

        if days <= 0:
            raise HistoryServiceError("Days must be positive")

        username = username.strip()
        boss = boss.lower().strip()

        try:
            logger.debug(f"Getting {boss} progress for {username} over {days} days")

            # Verify player exists
            player_stmt = select(Player).where(Player.username.ilike(username))
            player_result = await self.db_session.execute(player_stmt)
            player = player_result.scalar_one_or_none()

            if not player:
                raise PlayerNotFoundError(f"Player '{username}' not found")

            # Get records from the last N days
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            records = await self._get_records_since_date(player.id, cutoff_date)

            if len(records) < 2:
                raise InsufficientDataError(
                    f"Insufficient data for {boss} progress analysis (need at least 2 records)"
                )

            # Filter records that have data for this boss
            boss_records = [
                record for record in records
                if record.get_boss_data(boss) is not None
            ]

            if len(boss_records) < 2:
                raise InsufficientDataError(
                    f"Insufficient {boss} data for progress analysis"
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


async def get_history_service(db_session: AsyncSession) -> HistoryService:
    """
    Dependency injection function for FastAPI.

    Args:
        db_session: Database session

    Returns:
        HistoryService: Configured history service instance
    """
    return HistoryService(db_session)