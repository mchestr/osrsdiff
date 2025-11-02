"""Statistics service for retrieving current hiscore data."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.player import Player
from src.models.hiscore import HiscoreRecord

logger = logging.getLogger(__name__)


class StatisticsServiceError(Exception):
    """Base exception for statistics service errors."""

    pass


class PlayerNotFoundError(StatisticsServiceError):
    """Raised when a requested player is not found."""

    pass


class NoDataAvailableError(StatisticsServiceError):
    """Raised when no hiscore data is available for a player."""

    pass


class StatisticsService:
    """Service for retrieving current and historical hiscore statistics."""

    def __init__(self, db_session: AsyncSession):
        """
        Initialize the statistics service.

        Args:
            db_session: Database session for operations
        """
        self.db_session = db_session

    async def get_current_stats(self, username: str) -> Optional[HiscoreRecord]:
        """
        Get the most recent hiscore record for a player.

        Args:
            username: OSRS player username

        Returns:
            Optional[HiscoreRecord]: Most recent hiscore record or None if no data

        Raises:
            PlayerNotFoundError: If player doesn't exist in the system
            StatisticsServiceError: For database or other service errors
        """
        if not username:
            raise PlayerNotFoundError("Username cannot be empty")

        username = username.strip()

        try:
            logger.debug(f"Getting current stats for player: {username}")

            # Query for player with their hiscore records
            stmt = (
                select(Player)
                .options(selectinload(Player.hiscore_records))
                .where(Player.username.ilike(username))
            )
            result = await self.db_session.execute(stmt)
            player = result.scalar_one_or_none()

            if not player:
                raise PlayerNotFoundError(f"Player '{username}' not found")

            # Get the latest hiscore record (already ordered by fetched_at desc)
            latest_record = player.latest_hiscore
            
            if latest_record:
                logger.debug(
                    f"Found current stats for {username}: "
                    f"fetched at {latest_record.fetched_at}, "
                    f"overall level {latest_record.overall_level}"
                )
            else:
                logger.debug(f"No hiscore data available for player: {username}")

            return latest_record

        except PlayerNotFoundError:
            # Re-raise player not found errors
            raise
        except Exception as e:
            logger.error(f"Error getting current stats for {username}: {e}")
            raise StatisticsServiceError(
                f"Failed to get current stats for '{username}': {e}"
            )

    async def get_multiple_stats(
        self, usernames: List[str]
    ) -> Dict[str, Optional[HiscoreRecord]]:
        """
        Get current statistics for multiple players in a single query.

        Args:
            usernames: List of OSRS player usernames

        Returns:
            Dict[str, Optional[HiscoreRecord]]: Mapping of username to latest hiscore record.
                                               None values indicate no data available.

        Raises:
            StatisticsServiceError: For database or other service errors
        """
        if not usernames:
            return {}

        # Normalize usernames
        usernames = [username.strip() for username in usernames if username.strip()]
        
        if not usernames:
            return {}

        try:
            logger.debug(f"Getting current stats for {len(usernames)} players")

            # Query for all players with their hiscore records
            stmt = (
                select(Player)
                .options(selectinload(Player.hiscore_records))
                .where(Player.username.in_(usernames))
            )
            result = await self.db_session.execute(stmt)
            players = result.scalars().all()

            # Create mapping of username to latest hiscore record
            stats_map = {}
            found_usernames = set()

            for player in players:
                # Use original case from database for consistency
                stats_map[player.username] = player.latest_hiscore
                found_usernames.add(player.username.lower())

            # Add None entries for players not found
            for username in usernames:
                if username.lower() not in found_usernames:
                    stats_map[username] = None

            logger.debug(
                f"Retrieved stats for {len(players)} players, "
                f"{len(usernames) - len(players)} not found"
            )

            return stats_map

        except Exception as e:
            logger.error(f"Error getting multiple stats: {e}")
            raise StatisticsServiceError(f"Failed to get multiple stats: {e}")

    async def get_stats_at_date(
        self, username: str, date: datetime
    ) -> Optional[HiscoreRecord]:
        """
        Get the hiscore record closest to a specific date for a player.

        This method finds the most recent hiscore record that was fetched
        on or before the specified date.

        Args:
            username: OSRS player username
            date: Target date to find stats for

        Returns:
            Optional[HiscoreRecord]: Hiscore record closest to the date or None if no data

        Raises:
            PlayerNotFoundError: If player doesn't exist in the system
            StatisticsServiceError: For database or other service errors
        """
        if not username:
            raise PlayerNotFoundError("Username cannot be empty")

        username = username.strip()

        try:
            logger.debug(f"Getting stats at date {date} for player: {username}")

            # First verify player exists
            player_stmt = select(Player).where(Player.username.ilike(username))
            player_result = await self.db_session.execute(player_stmt)
            player = player_result.scalar_one_or_none()

            if not player:
                raise PlayerNotFoundError(f"Player '{username}' not found")

            # Query for the most recent hiscore record on or before the date
            stmt = (
                select(HiscoreRecord)
                .where(
                    HiscoreRecord.player_id == player.id,
                    HiscoreRecord.fetched_at <= date,
                )
                .order_by(HiscoreRecord.fetched_at.desc())
                .limit(1)
            )
            result = await self.db_session.execute(stmt)
            record = result.scalar_one_or_none()

            if record:
                logger.debug(
                    f"Found stats for {username} at {date}: "
                    f"record from {record.fetched_at}, "
                    f"overall level {record.overall_level}"
                )
            else:
                logger.debug(f"No stats found for {username} at or before {date}")

            return record

        except PlayerNotFoundError:
            # Re-raise player not found errors
            raise
        except Exception as e:
            logger.error(f"Error getting stats at date for {username}: {e}")
            raise StatisticsServiceError(
                f"Failed to get stats at date for '{username}': {e}"
            )

    async def format_stats_response(
        self, record: HiscoreRecord, username: str
    ) -> Dict[str, Any]:
        """
        Format a hiscore record for API response.

        This method transforms the database record into a structured format
        suitable for API responses, including skill levels, experience points,
        and boss kill counts.

        Args:
            record: HiscoreRecord to format
            username: Player username to include in response

        Returns:
            Dict: Formatted statistics data
        """
        if not record:
            return {}

        try:
            # Calculate combat level if possible
            combat_level = record.calculate_combat_level()

            formatted_data = {
                "username": username,
                "fetched_at": record.fetched_at.isoformat(),
                "overall": {
                    "rank": record.overall_rank,
                    "level": record.overall_level,
                    "experience": record.overall_experience,
                },
                "combat_level": combat_level,
                "skills": record.skills_data or {},
                "bosses": record.bosses_data or {},
                "metadata": {
                    "total_skills": record.total_skills,
                    "total_bosses": record.total_bosses,
                    "record_id": record.id,
                },
            }

            return formatted_data

        except Exception as e:
            logger.error(f"Error formatting stats response: {e}")
            raise StatisticsServiceError(f"Failed to format stats response: {e}")

    async def format_multiple_stats_response(
        self, stats_map: Dict[str, Optional[HiscoreRecord]]
    ) -> Dict[str, Any]:
        """
        Format multiple hiscore records for API response.

        Args:
            stats_map: Mapping of username to hiscore record

        Returns:
            Dict: Formatted statistics data for multiple players
        """
        try:
            formatted_data = {}

            for username, record in stats_map.items():
                if record:
                    formatted_data[username] = await self.format_stats_response(record, username)
                else:
                    formatted_data[username] = {
                        "username": username,
                        "error": "No data available",
                        "fetched_at": None,
                        "overall": None,
                        "combat_level": None,
                        "skills": {},
                        "bosses": {},
                        "metadata": {
                            "total_skills": 0,
                            "total_bosses": 0,
                            "record_id": None,
                        },
                    }

            return {
                "players": formatted_data,
                "metadata": {
                    "total_requested": len(stats_map),
                    "total_found": sum(1 for record in stats_map.values() if record),
                    "total_missing": sum(1 for record in stats_map.values() if not record),
                },
            }

        except Exception as e:
            logger.error(f"Error formatting multiple stats response: {e}")
            raise StatisticsServiceError(f"Failed to format multiple stats response: {e}")


async def get_statistics_service(db_session: AsyncSession) -> StatisticsService:
    """
    Dependency injection function for FastAPI.

    Args:
        db_session: Database session

    Returns:
        StatisticsService: Configured statistics service instance
    """
    return StatisticsService(db_session)