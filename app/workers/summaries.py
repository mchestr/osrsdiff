"""
Background tasks for generating AI-powered player progress summaries.

This module provides TaskIQ tasks for periodic summary generation,
including daily automated summaries and on-demand generation.
"""

import logging
from datetime import UTC, datetime
from typing import Any, Dict, List

from app.models.base import AsyncSessionLocal
from app.services.summary import SummaryService
from app.workers.main import broker

logger = logging.getLogger(__name__)


# Daily summary generation job - runs at 2 AM UTC
@broker.task(
    schedule=[{"cron": "0 2 * * *"}],
    retry_on_error=True,
    max_retries=2,
    delay=30.0,
    task_timeout=3600.0,  # 1 hour timeout for batch processing
)
async def daily_summary_generation_job() -> Dict[str, Any]:
    """
    Periodic job to generate AI-powered summaries for all active players.

    This task runs daily to generate summaries analyzing player progress
    over the last day and week. Summaries are stored in the database
    and can be retrieved via the API.

    Returns:
        Dict containing generation results and statistics
    """
    logger.info("Starting daily summary generation job")
    start_time = datetime.now(UTC)

    async with AsyncSessionLocal() as db_session:
        try:
            summary_service = SummaryService(db_session)

            # Generate summaries for all active players
            summaries = (
                await summary_service.generate_summaries_for_all_players(
                    force_regenerate=False
                )
            )

            duration = (datetime.now(UTC) - start_time).total_seconds()

            result = {
                "status": "success",
                "summaries_generated": len(summaries),
                "timestamp": datetime.now(UTC).isoformat(),
                "duration_seconds": duration,
            }

            logger.info(
                f"Daily summary generation completed: {len(summaries)} summaries generated in {duration:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(
                f"Error in daily summary generation job: {e}", exc_info=True
            )
            duration = (datetime.now(UTC) - start_time).total_seconds()
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
                "duration_seconds": duration,
            }


@broker.task(
    retry_on_error=True,
    max_retries=2,
    delay=30.0,
    task_timeout=300.0,  # 5 minute timeout for single player
)
async def generate_player_summary_task(
    player_id: int, force_regenerate: bool = False
) -> Dict[str, Any]:
    """
    Generate a summary for a specific player.

    This task can be triggered on-demand to generate a summary for a
    specific player, useful for testing or immediate generation needs.

    Args:
        player_id: ID of the player to generate summary for
        force_regenerate: If True, regenerate even if recent summary exists

    Returns:
        Dict containing generation result
    """
    logger.info(
        f"Starting summary generation for player {player_id} (force={force_regenerate})"
    )
    start_time = datetime.now(UTC)

    async with AsyncSessionLocal() as db_session:
        try:
            summary_service = SummaryService(db_session)

            summary = await summary_service.generate_summary_for_player(
                player_id, force_regenerate=force_regenerate
            )

            duration = (datetime.now(UTC) - start_time).total_seconds()

            result = {
                "status": "success",
                "player_id": player_id,
                "summary_id": summary.id,
                "timestamp": datetime.now(UTC).isoformat(),
                "duration_seconds": duration,
            }

            logger.info(
                f"Summary generation completed for player {player_id} (summary ID: {summary.id}) in {duration:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(
                f"Error generating summary for player {player_id}: {e}",
                exc_info=True,
            )
            duration = (datetime.now(UTC) - start_time).total_seconds()
            return {
                "status": "error",
                "player_id": player_id,
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
                "duration_seconds": duration,
            }
