import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import (
    HistoryServiceError,
    InsufficientDataError,
    PlayerNotFoundError,
)
from app.models.player import Player
from app.models.player_summary import PlayerSummary
from app.services.history import HistoryService

logger = logging.getLogger(__name__)


class SummaryGenerationError(Exception):
    """Base exception for summary generation errors."""

    pass


class SummaryService:
    """Service for generating AI-powered player progress summaries."""

    def __init__(self, db_session: AsyncSession):
        """
        Initialize the summary service.

        Args:
            db_session: Database session for operations
        """
        self.db_session = db_session
        self.history_service = HistoryService(db_session)

    async def generate_summary_for_player(
        self, player_id: int, force_regenerate: bool = False
    ) -> PlayerSummary:
        """
        Generate a summary for a specific player covering the last day and week.

        Args:
            player_id: ID of the player to generate summary for
            force_regenerate: If True, generate even if a recent summary exists

        Returns:
            PlayerSummary: The generated summary

        Raises:
            PlayerNotFoundError: If player doesn't exist
            InsufficientDataError: If insufficient data for summary
            SummaryGenerationError: If summary generation fails
        """
        # Get player
        player_stmt = select(Player).where(Player.id == player_id)
        player_result = await self.db_session.execute(player_stmt)
        player = player_result.scalar_one_or_none()

        if not player:
            raise PlayerNotFoundError(f"Player with ID {player_id} not found")

        # Check if we should skip (recent summary exists and not forcing)
        if not force_regenerate:
            recent_summary = await self._get_recent_summary(player_id)
            if recent_summary:
                logger.info(
                    f"Recent summary exists for player {player.username}, skipping"
                )
                return recent_summary

        # Calculate time periods
        now = datetime.now(timezone.utc)
        one_day_ago = now - timedelta(days=1)
        seven_days_ago = now - timedelta(days=7)

        # Get progress data
        try:
            day_progress = (
                await self.history_service.get_progress_between_dates(
                    player.username, one_day_ago, now
                )
            )
            week_progress = (
                await self.history_service.get_progress_between_dates(
                    player.username, seven_days_ago, now
                )
            )
        except InsufficientDataError as e:
            raise InsufficientDataError(
                f"Insufficient data to generate summary for {player.username}: {e}"
            ) from e

        # Generate summary using OpenAI
        summary_text = await self._generate_summary_text(
            player.username, day_progress, week_progress
        )

        # Create and save summary
        summary = PlayerSummary(
            player_id=player.id,
            period_start=seven_days_ago,
            period_end=now,
            summary_text=summary_text,
            model_used=settings.openai.model,
        )

        self.db_session.add(summary)
        await self.db_session.commit()
        await self.db_session.refresh(summary)

        logger.info(
            f"Generated summary for player {player.username} (ID: {player_id})"
        )
        return summary

    async def generate_summaries_for_all_players(
        self, force_regenerate: bool = False
    ) -> List[PlayerSummary]:
        """
        Generate summaries for all active players.

        Args:
            force_regenerate: If True, regenerate even if recent summaries exist

        Returns:
            List[PlayerSummary]: List of generated summaries
        """
        # Get all active players
        players_stmt = select(Player).where(Player.is_active.is_(True))
        players_result = await self.db_session.execute(players_stmt)
        players = list(players_result.scalars().all())

        summaries = []
        errors = []

        for player in players:
            try:
                summary = await self.generate_summary_for_player(
                    player.id, force_regenerate=force_regenerate
                )
                summaries.append(summary)
            except (InsufficientDataError, SummaryGenerationError) as e:
                logger.warning(
                    f"Failed to generate summary for player {player.username}: {e}"
                )
                errors.append({"player": player.username, "error": str(e)})
            except Exception as e:
                logger.error(
                    f"Unexpected error generating summary for player {player.username}: {e}",
                    exc_info=True,
                )
                errors.append({"player": player.username, "error": str(e)})

        logger.info(
            f"Generated {len(summaries)} summaries, {len(errors)} errors"
        )
        return summaries

    async def _get_recent_summary(
        self, player_id: int, hours: int = 20
    ) -> Optional[PlayerSummary]:
        """
        Get the most recent summary for a player if it was generated recently.

        Args:
            player_id: Player ID
            hours: Consider summaries within this many hours as "recent"

        Returns:
            Optional[PlayerSummary]: Recent summary if found, None otherwise
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = (
            select(PlayerSummary)
            .where(
                PlayerSummary.player_id == player_id,
                PlayerSummary.generated_at >= cutoff,
            )
            .order_by(PlayerSummary.generated_at.desc())
            .limit(1)
        )
        result = await self.db_session.execute(stmt)
        return result.scalar_one_or_none()

    async def _generate_summary_text(
        self,
        username: str,
        day_progress: Any,
        week_progress: Any,
    ) -> str:
        """
        Generate summary text using OpenAI API.

        Args:
            username: Player username
            day_progress: ProgressAnalysis for the last day
            week_progress: ProgressAnalysis for the last week

        Returns:
            str: Generated summary text

        Raises:
            SummaryGenerationError: If generation fails
        """
        if not settings.openai.api_key:
            raise SummaryGenerationError(
                "OpenAI API key not configured. Set OPENAI__API_KEY environment variable."
            )

        try:
            # Import OpenAI client
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=settings.openai.api_key)

            # Prepare progress data for the prompt
            day_data = day_progress.to_dict()
            week_data = week_progress.to_dict()

            # Create prompt
            prompt = self._create_summary_prompt(username, day_data, week_data)

            # Call OpenAI API
            response = await client.chat.completions.create(
                model=settings.openai.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert Old School RuneScape (OSRS) analyst. "
                        "You analyze player progress data and provide insightful, engaging summaries "
                        "of their achievements and gameplay patterns. Keep summaries concise but informative, "
                        "highlighting notable achievements, skill gains, and activity patterns.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=settings.openai.max_tokens,
                temperature=settings.openai.temperature,
            )

            summary_text = response.choices[0].message.content
            if not summary_text:
                raise SummaryGenerationError("OpenAI returned empty summary")

            return summary_text.strip()

        except ImportError:
            raise SummaryGenerationError(
                "OpenAI library not installed. Install with: pip install openai"
            )
        except Exception as e:
            logger.error(
                f"Error generating summary with OpenAI: {e}", exc_info=True
            )
            raise SummaryGenerationError(
                f"Failed to generate summary: {e}"
            ) from e

    def _create_summary_prompt(
        self,
        username: str,
        day_data: Dict[str, Any],
        week_data: Dict[str, Any],
    ) -> str:
        """
        Create the prompt for OpenAI based on progress data.

        Args:
            username: Player username
            day_data: Progress data for the last day
            week_data: Progress data for the last week

        Returns:
            str: Formatted prompt
        """
        # Format experience gains
        day_exp = day_data.get("progress", {}).get("experience_gained", {})
        week_exp = week_data.get("progress", {}).get("experience_gained", {})

        # Get top skills by XP gain
        def get_top_skills(
            exp_data: Dict[str, int], n: int = 5
        ) -> List[tuple]:
            """Get top N skills by experience gain."""
            skills = [
                (skill, exp)
                for skill, exp in exp_data.items()
                if skill != "overall" and exp > 0
            ]
            return sorted(skills, key=lambda x: x[1], reverse=True)[:n]

        day_top_skills = get_top_skills(day_exp)
        week_top_skills = get_top_skills(week_exp)

        prompt = f"""Analyze the progress of OSRS player "{username}" and provide a concise summary.

LAST 24 HOURS:
- Overall XP gained: {day_exp.get('overall', 0):,}
- Top skills by XP: {', '.join([f'{skill.title()} ({exp:,} XP)' for skill, exp in day_top_skills]) if day_top_skills else 'None'}
- Levels gained: {sum(day_data.get('progress', {}).get('levels_gained', {}).values())}
- Boss kills: {sum(day_data.get('progress', {}).get('boss_kills_gained', {}).values())}

LAST 7 DAYS:
- Overall XP gained: {week_exp.get('overall', 0):,}
- Top skills by XP: {', '.join([f'{skill.title()} ({exp:,} XP)' for skill, exp in week_top_skills]) if week_top_skills else 'None'}
- Levels gained: {sum(week_data.get('progress', {}).get('levels_gained', {}).values())}
- Boss kills: {sum(week_data.get('progress', {}).get('boss_kills_gained', {}).values())}

Provide a brief, engaging summary (2-4 sentences) highlighting:
1. Notable achievements or milestones
2. Most active skills or activities
3. Overall activity level and progress pace
4. Any interesting patterns or trends

Keep it concise and player-friendly."""

        return prompt


def get_summary_service(db_session: AsyncSession) -> SummaryService:
    """
    Dependency injection function for FastAPI.

    Args:
        db_session: Database session

    Returns:
        SummaryService: Configured summary service instance
    """
    return SummaryService(db_session)
