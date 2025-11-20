import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import (
    HistoryServiceError,
    InsufficientDataError,
    PlayerNotFoundError,
)
from app.models.player import Player
from app.models.player_summary import PlayerSummary
from app.services.player.history import HistoryService
from app.services.setting import setting_service as settings_cache
from app.utils.template_loader import render_template

logger = logging.getLogger(__name__)


class SummaryGenerationError(Exception):
    """Base exception for summary generation errors."""

    pass


def parse_summary_text(summary_text: str) -> Dict[str, Any]:
    """
    Parse summary text into structured format.

    Handles both JSON format (new) and plain text format (legacy).

    Args:
        summary_text: Summary text from database (may be JSON or plain text)

    Returns:
        Dict with "summary" (optional), "points" array, and "format" indicator
    """
    try:
        # Try to parse as JSON first
        data = json.loads(summary_text)
        if isinstance(data, dict):
            result: Dict[str, Any] = {
                "format": "structured",
            }
            # Extract summary if present
            if "summary" in data and isinstance(data["summary"], str):
                result["summary"] = data["summary"]
            # Extract points (required)
            if "points" in data and isinstance(data["points"], list):
                result["points"] = data["points"]
            else:
                # If no points but has summary, use summary as single point
                if "summary" in result:
                    result["points"] = [result["summary"]]
                else:
                    result["points"] = []
            return result
    except (json.JSONDecodeError, TypeError):
        pass

    # Fallback: treat as plain text (legacy format)
    # Split by common separators or treat as single point
    if "\n" in summary_text:
        # Try to split by bullet points or newlines
        lines = [
            line.strip()
            for line in summary_text.split("\n")
            if line.strip() and not line.strip().startswith("#")
        ]
        # Filter out common prefixes
        cleaned_lines = []
        for line in lines:
            # Remove bullet points, dashes, etc.
            cleaned = line.lstrip("•-* ").strip()
            if cleaned:
                cleaned_lines.append(cleaned)
        if cleaned_lines:
            # Use first line as summary if multiple lines, rest as points
            if len(cleaned_lines) > 1:
                return {
                    "summary": cleaned_lines[0],
                    "points": cleaned_lines[1:],
                    "format": "legacy",
                }
            else:
                return {
                    "points": cleaned_lines,
                    "format": "legacy",
                }

    # Single point fallback
    return {
        "points": [summary_text.strip()],
        "format": "legacy",
    }


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

    def _has_progress(self, progress: Any) -> bool:
        """
        Check if there's been any meaningful progress.

        Args:
            progress: ProgressAnalysis object

        Returns:
            bool: True if there's been any XP, levels, or boss kills gained
        """
        if not progress.start_record or not progress.end_record:
            return False

        # Check for any XP gained
        exp_gained = progress.experience_gained
        if exp_gained.get("overall", 0) > 0:
            return True

        # Check for any levels gained
        levels_gained = progress.levels_gained
        if any(levels_gained.values()):
            return True

        # Check for any boss kills gained
        boss_kills = progress.boss_kills_gained
        if any(boss_kills.values()):
            return True

        return False

    async def generate_summary_for_player(
        self, player_id: int, force_regenerate: bool = False
    ) -> Optional[PlayerSummary]:
        """
        Generate a summary for a specific player covering the last day and week.

        Args:
            player_id: ID of the player to generate summary for
            force_regenerate: If True, generate even if a recent summary exists

        Returns:
            Optional[PlayerSummary]: The generated summary, or None if no progress

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

        # Check if there's been any progress in the last 7 days
        if not self._has_progress(week_progress):
            logger.info(
                f"No progress detected for player {player.username} in last 7 days, skipping summary generation"
            )
            return None

        # Check if OpenAI is enabled
        if not settings_cache.openai_enabled:
            logger.info(
                f"OpenAI functionality is disabled, skipping summary generation for player {player.username}"
            )
            return None

        # Generate summary using OpenAI
        summary_text, openai_metadata = await self._generate_summary_text(
            player.username, day_progress, week_progress
        )

        # Create and save summary
        summary = PlayerSummary(
            player_id=player.id,
            period_start=seven_days_ago,
            period_end=now,
            summary_text=summary_text,
            model_used=settings_cache.openai_model,
            prompt_tokens=openai_metadata.get("prompt_tokens"),
            completion_tokens=openai_metadata.get("completion_tokens"),
            total_tokens=openai_metadata.get("total_tokens"),
            finish_reason=openai_metadata.get("finish_reason"),
            response_id=openai_metadata.get("response_id"),
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
                if summary is not None:
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
    ) -> tuple[str, Dict[str, Any]]:
        """
        Generate summary text using OpenAI API.

        Args:
            username: Player username
            day_progress: ProgressAnalysis for the last day
            week_progress: ProgressAnalysis for the last week

        Returns:
            tuple[str, Dict[str, Any]]: Generated summary text and OpenAI response metadata

        Raises:
            SummaryGenerationError: If generation fails
        """
        api_key = settings_cache.openai_api_key
        if not api_key:
            raise SummaryGenerationError(
                "OpenAI API key not configured. Set OPENAI__API_KEY environment variable."
            )

        try:
            # Import OpenAI client
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=api_key)

            # Prepare progress data for the prompt
            day_data = day_progress.to_dict()
            week_data = week_progress.to_dict()

            # Create prompts from templates
            system_prompt = self._load_system_prompt()
            user_prompt = self._create_summary_prompt(
                username, day_data, week_data
            )

            # Call OpenAI API with JSON response format
            # Use response_format if supported by the model (gpt-4o-mini and newer)
            create_kwargs: Dict[str, Any] = {
                "model": settings_cache.openai_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": settings_cache.openai_max_tokens,
                "temperature": settings_cache.openai_temperature,
            }

            # Try to use JSON mode if available (gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo, etc.)
            # JSON mode is supported by most modern OpenAI models
            try:
                # Enable JSON mode for structured output
                # This ensures the model returns valid JSON
                create_kwargs["response_format"] = {"type": "json_object"}
            except Exception:
                # If response_format not supported, continue without it
                # The model should still follow JSON format instructions
                pass

            response = await client.chat.completions.create(**create_kwargs)

            summary_text = response.choices[0].message.content
            if not summary_text:
                raise SummaryGenerationError("OpenAI returned empty summary")

            # Extract metadata from response
            usage = response.usage
            metadata = {
                "prompt_tokens": usage.prompt_tokens if usage else None,
                "completion_tokens": (
                    usage.completion_tokens if usage else None
                ),
                "total_tokens": usage.total_tokens if usage else None,
                "finish_reason": (
                    response.choices[0].finish_reason
                    if response.choices
                    else None
                ),
                "response_id": response.id,
            }

            # Parse JSON response
            try:
                summary_data = json.loads(summary_text.strip())
                if not isinstance(summary_data, dict):
                    raise ValueError(
                        "Invalid JSON structure: must be an object"
                    )

                # Validate structure
                if "points" not in summary_data:
                    raise ValueError(
                        "Invalid JSON structure: missing 'points' key"
                    )
                if not isinstance(summary_data["points"], list):
                    raise ValueError(
                        "Invalid JSON structure: 'points' must be an array"
                    )

                # Summary is optional but should be a string if present
                if "summary" in summary_data and not isinstance(
                    summary_data["summary"], str
                ):
                    raise ValueError(
                        "Invalid JSON structure: 'summary' must be a string"
                    )

                # Format as structured JSON string for storage
                formatted_summary = json.dumps(
                    summary_data, ensure_ascii=False
                )
                return formatted_summary, metadata
            except json.JSONDecodeError as e:
                logger.warning(
                    f"Failed to parse JSON response, attempting to extract JSON: {e}"
                )
                # Try to extract JSON from markdown code blocks or plain text
                cleaned_text = summary_text.strip()
                # Remove markdown code blocks if present
                if cleaned_text.startswith("```"):
                    lines = cleaned_text.split("\n")
                    cleaned_text = "\n".join(
                        line
                        for line in lines
                        if not line.strip().startswith("```")
                    )

                try:
                    summary_data = json.loads(cleaned_text)
                    if (
                        not isinstance(summary_data, dict)
                        or "points" not in summary_data
                    ):
                        raise ValueError("Invalid JSON structure")
                    # Ensure summary is a string if present
                    if "summary" in summary_data and not isinstance(
                        summary_data["summary"], str
                    ):
                        summary_data["summary"] = str(summary_data["summary"])
                    formatted_summary = json.dumps(
                        summary_data, ensure_ascii=False
                    )
                    return formatted_summary, metadata
                except Exception:
                    # Fallback: wrap the text in a points array
                    logger.warning(
                        "Could not parse JSON, wrapping response as single point"
                    )
                    fallback_data = {"points": [summary_text.strip()]}
                    formatted_summary = json.dumps(
                        fallback_data, ensure_ascii=False
                    )
                    return formatted_summary, metadata

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

    def _load_system_prompt(self) -> str:
        """
        Load the system prompt from template.

        Returns:
            str: System prompt content

        Raises:
            SummaryGenerationError: If template cannot be loaded
        """
        try:
            return render_template("summary/system_prompt.j2", {})
        except Exception as e:
            logger.error(
                f"Failed to load system prompt template: {e}", exc_info=True
            )
            raise SummaryGenerationError(
                f"Cannot load system prompt template: {e}"
            ) from e

    def _create_summary_prompt(
        self,
        username: str,
        day_data: Dict[str, Any],
        week_data: Dict[str, Any],
    ) -> str:
        """
        Create the prompt for OpenAI based on progress data using template.

        Args:
            username: Player username
            day_data: Progress data for the last day
            week_data: Progress data for the last week

        Returns:
            str: Formatted prompt

        Raises:
            SummaryGenerationError: If template cannot be loaded
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

        # Format top skills as strings
        def format_top_skills(skills: List[tuple]) -> str:
            """Format top skills list as comma-separated string."""
            if not skills:
                return "None"
            return ", ".join(
                [f"{skill.title()} ({exp:,} XP)" for skill, exp in skills]
            )

        day_top_skills_formatted = format_top_skills(day_top_skills)
        week_top_skills_formatted = format_top_skills(week_top_skills)

        # Get boss kills data
        day_boss_kills_data = day_data.get("progress", {}).get(
            "boss_kills_gained", {}
        )
        week_boss_kills_data = week_data.get("progress", {}).get(
            "boss_kills_gained", {}
        )

        # Format boss kills (similar to top skills)
        def format_boss_kills(boss_kills: Dict[str, int]) -> str:
            """Format boss kills as comma-separated string."""
            if not boss_kills:
                return "None"
            # Filter out bosses with 0 kills and sort by kills descending
            active_bosses = [
                (boss, kills)
                for boss, kills in boss_kills.items()
                if kills > 0
            ]
            if not active_bosses:
                return "None"
            sorted_bosses = sorted(
                active_bosses, key=lambda x: x[1], reverse=True
            )
            return ", ".join(
                [
                    f"{boss.title()} ({kills:,} KC)"
                    for boss, kills in sorted_bosses
                ]
            )

        day_boss_kills_formatted = format_boss_kills(day_boss_kills_data)
        week_boss_kills_formatted = format_boss_kills(week_boss_kills_data)

        # Calculate totals
        day_levels_gained = sum(
            day_data.get("progress", {}).get("levels_gained", {}).values()
        )
        day_boss_kills_total = sum(day_boss_kills_data.values())
        week_levels_gained = sum(
            week_data.get("progress", {}).get("levels_gained", {}).values()
        )
        week_boss_kills_total = sum(week_boss_kills_data.values())

        # Render template
        try:
            return render_template(
                "summary/user_prompt.j2",
                {
                    "username": username,
                    "day_overall_xp": f"{day_exp.get('overall', 0):,}",
                    "day_top_skills_formatted": day_top_skills_formatted,
                    "day_levels_gained": day_levels_gained,
                    "day_boss_kills_formatted": day_boss_kills_formatted,
                    "day_boss_kills_total": day_boss_kills_total,
                    "week_overall_xp": f"{week_exp.get('overall', 0):,}",
                    "week_top_skills_formatted": week_top_skills_formatted,
                    "week_levels_gained": week_levels_gained,
                    "week_boss_kills_formatted": week_boss_kills_formatted,
                    "week_boss_kills_total": week_boss_kills_total,
                },
            )
        except Exception as e:
            logger.error(
                f"Failed to load user prompt template: {e}", exc_info=True
            )
            raise SummaryGenerationError(
                f"Cannot load user prompt template: {e}"
            ) from e


def get_summary_service(db_session: AsyncSession) -> SummaryService:
    """
    Dependency injection function for FastAPI.

    Args:
        db_session: Database session

    Returns:
        SummaryService: Configured summary service instance
    """
    return SummaryService(db_session)
