import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.hiscore import HiscoreRecord
from app.models.player import Player

logger = logging.getLogger(__name__)

# OSRS skills list
OSRS_SKILLS = [
    "attack",
    "hitpoints",
    "mining",
    "strength",
    "agility",
    "smithing",
    "defence",
    "herblore",
    "fishing",
    "ranged",
    "thieving",
    "cooking",
    "prayer",
    "crafting",
    "firemaking",
    "magic",
    "fletching",
    "woodcutting",
    "runecraft",
    "slayer",
    "farming",
    "construction",
    "hunter",
    "sailing",
]


class LeaderboardService:
    """Service for retrieving leaderboard data across all tracked players."""

    def __init__(self, db_session: AsyncSession):
        """
        Initialize the leaderboard service.

        Args:
            db_session: Database session for operations
        """
        self.db_session = db_session

    async def get_top_by_overall_exp(
        self, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get top players by overall experience.

        Args:
            limit: Maximum number of players to return

        Returns:
            List of dicts with username, overall_experience, overall_level, and rank
        """
        try:
            logger.debug(f"Getting top {limit} players by overall EXP")

            # Get the latest hiscore record for each active player
            # Using a subquery to get the most recent record per player
            subquery = (
                select(
                    HiscoreRecord.player_id,
                    func.max(HiscoreRecord.fetched_at).label("max_fetched_at"),
                )
                .join(Player, HiscoreRecord.player_id == Player.id)
                .where(Player.is_active.is_(True))
                .group_by(HiscoreRecord.player_id)
                .subquery()
            )

            stmt = (
                select(
                    Player.username,
                    HiscoreRecord.overall_experience,
                    HiscoreRecord.overall_level,
                    HiscoreRecord.overall_rank,
                    HiscoreRecord.fetched_at,
                )
                .join(HiscoreRecord, Player.id == HiscoreRecord.player_id)
                .join(
                    subquery,
                    (HiscoreRecord.player_id == subquery.c.player_id)
                    & (HiscoreRecord.fetched_at == subquery.c.max_fetched_at),
                )
                .where(
                    Player.is_active.is_(True),
                    HiscoreRecord.overall_experience.isnot(None),
                )
                .order_by(desc(HiscoreRecord.overall_experience))
                .limit(limit)
            )

            result = await self.db_session.execute(stmt)
            rows = result.all()

            leaderboard = []
            for rank, row in enumerate(rows, start=1):
                leaderboard.append(
                    {
                        "rank": rank,
                        "username": row.username,
                        "overall_experience": row.overall_experience,
                        "overall_level": row.overall_level,
                        "overall_rank": row.overall_rank,
                        "fetched_at": (
                            row.fetched_at.isoformat()
                            if row.fetched_at
                            else None
                        ),
                    }
                )

            logger.debug(
                f"Found {len(leaderboard)} players for EXP leaderboard"
            )
            return leaderboard

        except Exception as e:
            logger.error(f"Error getting top players by EXP: {e}")
            raise

    async def get_top_by_total_level(
        self, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get top players by total level.

        Args:
            limit: Maximum number of players to return

        Returns:
            List of dicts with username, overall_level, overall_experience, and rank
        """
        try:
            logger.debug(f"Getting top {limit} players by total level")

            # Get the latest hiscore record for each active player
            subquery = (
                select(
                    HiscoreRecord.player_id,
                    func.max(HiscoreRecord.fetched_at).label("max_fetched_at"),
                )
                .join(Player, HiscoreRecord.player_id == Player.id)
                .where(Player.is_active.is_(True))
                .group_by(HiscoreRecord.player_id)
                .subquery()
            )

            stmt = (
                select(
                    Player.username,
                    HiscoreRecord.overall_level,
                    HiscoreRecord.overall_experience,
                    HiscoreRecord.overall_rank,
                    HiscoreRecord.fetched_at,
                )
                .join(HiscoreRecord, Player.id == HiscoreRecord.player_id)
                .join(
                    subquery,
                    (HiscoreRecord.player_id == subquery.c.player_id)
                    & (HiscoreRecord.fetched_at == subquery.c.max_fetched_at),
                )
                .where(
                    Player.is_active.is_(True),
                    HiscoreRecord.overall_level.isnot(None),
                )
                .order_by(desc(HiscoreRecord.overall_level))
                .limit(limit)
            )

            result = await self.db_session.execute(stmt)
            rows = result.all()

            leaderboard = []
            for rank, row in enumerate(rows, start=1):
                leaderboard.append(
                    {
                        "rank": rank,
                        "username": row.username,
                        "overall_level": row.overall_level,
                        "overall_experience": row.overall_experience,
                        "overall_rank": row.overall_rank,
                        "fetched_at": (
                            row.fetched_at.isoformat()
                            if row.fetched_at
                            else None
                        ),
                    }
                )

            logger.debug(
                f"Found {len(leaderboard)} players for total level leaderboard"
            )
            return leaderboard

        except Exception as e:
            logger.error(f"Error getting top players by total level: {e}")
            raise

    async def get_top_by_skill(
        self, skill_name: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get top players by a specific skill (level or experience).

        Args:
            skill_name: Name of the skill (e.g., 'attack', 'strength')
            limit: Maximum number of players to return

        Returns:
            List of dicts with username, skill level, skill experience, and rank
        """
        try:
            skill_name_lower = skill_name.lower()
            logger.debug(
                f"Getting top {limit} players by skill: {skill_name_lower}"
            )

            # Handle "overall" as a special case
            if skill_name_lower == "overall":
                return await self.get_top_by_total_level(limit)

            # Get the latest hiscore record for each active player
            subquery = (
                select(
                    HiscoreRecord.player_id,
                    func.max(HiscoreRecord.fetched_at).label("max_fetched_at"),
                )
                .join(Player, HiscoreRecord.player_id == Player.id)
                .where(Player.is_active.is_(True))
                .group_by(HiscoreRecord.player_id)
                .subquery()
            )

            # Query for players with their latest hiscore records
            stmt = (
                select(
                    Player.username,
                    HiscoreRecord.skills_data,
                    HiscoreRecord.fetched_at,
                )
                .join(HiscoreRecord, Player.id == HiscoreRecord.player_id)
                .join(
                    subquery,
                    (HiscoreRecord.player_id == subquery.c.player_id)
                    & (HiscoreRecord.fetched_at == subquery.c.max_fetched_at),
                )
                .where(Player.is_active.is_(True))
            )

            result = await self.db_session.execute(stmt)
            rows = result.all()

            # Filter and sort by skill experience (or level if exp not available)
            players_with_skill = []
            for row in rows:
                skills_data = row.skills_data or {}
                skill_data = skills_data.get(skill_name_lower)

                if skill_data and isinstance(skill_data, dict):
                    exp = skill_data.get("experience")
                    level = skill_data.get("level")
                    rank = skill_data.get("rank")

                    if exp is not None or level is not None:
                        players_with_skill.append(
                            {
                                "username": row.username,
                                "skill_experience": exp,
                                "skill_level": level,
                                "skill_rank": rank,
                                "fetched_at": (
                                    row.fetched_at.isoformat()
                                    if row.fetched_at
                                    else None
                                ),
                            }
                        )

            # Sort by experience (descending), then by level if exp is None
            players_with_skill.sort(
                key=lambda x: (
                    (
                        x["skill_experience"]
                        if x["skill_experience"] is not None
                        else 0
                    ),
                    x["skill_level"] if x["skill_level"] is not None else 0,
                ),
                reverse=True,
            )

            # Limit and add rank
            leaderboard = []
            for rank, player in enumerate(players_with_skill[:limit], start=1):
                leaderboard.append(
                    {
                        "rank": rank,
                        "username": player["username"],
                        "skill_experience": player["skill_experience"],
                        "skill_level": player["skill_level"],
                        "skill_rank": player["skill_rank"],
                        "fetched_at": player["fetched_at"],
                    }
                )

            logger.debug(
                f"Found {len(leaderboard)} players for {skill_name_lower} leaderboard"
            )
            return leaderboard

        except Exception as e:
            logger.error(
                f"Error getting top players by skill {skill_name}: {e}"
            )
            raise

    async def get_all_skill_leaderboards(
        self, limit: int = 100
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get leaderboards for all skills.

        Args:
            limit: Maximum number of players to return per skill

        Returns:
            Dict mapping skill names to their leaderboards
        """
        try:
            logger.debug(f"Getting leaderboards for all skills (top {limit})")

            leaderboards = {}
            for skill in OSRS_SKILLS:
                try:
                    leaderboards[skill] = await self.get_top_by_skill(
                        skill, limit
                    )
                except Exception as e:
                    logger.warning(
                        f"Error getting leaderboard for skill {skill}: {e}"
                    )
                    leaderboards[skill] = []

            return leaderboards

        except Exception as e:
            logger.error(f"Error getting all skill leaderboards: {e}")
            raise
