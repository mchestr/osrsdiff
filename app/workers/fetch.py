"""Hiscore data fetching worker tasks."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from taskiq import Context, TaskiqDepends

from app.models.base import AsyncSessionLocal
from app.models.hiscore import HiscoreRecord
from app.models.player import Player
from app.services.osrs_api import (
    APIUnavailableError,
    HiscoreData,
    OSRSAPIClient,
    OSRSAPIError,
    PlayerNotFoundError,
    RateLimitError,
)
from app.workers.main import broker, get_task_defaults

if TYPE_CHECKING:
    from taskiq import AsyncTaskiqTask

logger = logging.getLogger(__name__)


class FetchWorkerError(Exception):
    """Base exception for fetch worker errors."""

    pass


class PlayerNotInDatabaseError(FetchWorkerError):
    """Raised when a player is not found in the database."""

    pass


def _hiscore_data_changed(
    new_data: "HiscoreData", last_record: Optional[HiscoreRecord]
) -> bool:
    """
    Compare new hiscore data with the last record to determine if data has changed.

    Args:
        new_data: New hiscore data from OSRS API
        last_record: Last hiscore record from database (None if no previous record)

    Returns:
        bool: True if data has changed or no previous record exists, False otherwise
    """
    if last_record is None:
        # No previous record, always save
        return True

    # Compare overall stats
    if (
        new_data.overall.get("rank") != last_record.overall_rank
        or new_data.overall.get("level") != last_record.overall_level
        or new_data.overall.get("experience") != last_record.overall_experience
    ):
        return True

    # Compare skills data
    if new_data.skills != last_record.skills_data:
        return True

    # Compare bosses data
    if new_data.bosses != last_record.bosses_data:
        return True

    # No changes detected
    return False


async def _fetch_player_hiscores(
    username: str, context: Context = TaskiqDepends()
) -> Dict[str, Any]:
    """
    Fetch and store hiscore data for a specific player.

    This task retrieves current hiscore data from the OSRS API and stores
    it as a new HiscoreRecord in the database only if the data has changed
    from the previous record. It handles various error conditions gracefully
    and provides detailed status information.

    Args:
        username: OSRS player username to fetch data for
        context: TaskIQ context containing schedule metadata in labels

    Returns:
        Dict containing task execution results with status, data, and metadata

    Raises:
        RateLimitError: If OSRS API rate limit is exceeded (will trigger retry)
        APIUnavailableError: If OSRS API is unavailable (will trigger retry)
        Exception: For database or other unexpected errors (will trigger retry)
    """
    # Access schedule metadata from context labels
    player_id = None
    schedule_id = None
    schedule_type = None

    if (
        context
        and hasattr(context, "message")
        and context.message
        and hasattr(context.message, "labels")
    ):
        labels = context.message.labels
        player_id = labels.get("player_id")
        schedule_id = labels.get("schedule_id")
        schedule_type = labels.get("schedule_type")

        # Log all available schedule metadata for debugging
        logger.debug(f"Task context labels: {dict(labels)}")

    # Enhanced logging with schedule metadata
    logger.info(
        f"Starting hiscore fetch for player: {username} "
        f"(player_id: {player_id}, schedule_id: {schedule_id}, schedule_type: {schedule_type})"
    )
    start_time = datetime.now(UTC)

    async with AsyncSessionLocal() as db_session:
        try:
            # Get player from database
            stmt = select(Player).where(Player.username.ilike(username))
            result = await db_session.execute(stmt)
            player = result.scalar_one_or_none()

            if not player:
                error_msg = f"Player '{username}' not found in database"
                logger.error(f"{error_msg} (schedule_id: {schedule_id})")
                return {
                    "status": "error",
                    "error_type": "player_not_found",
                    "username": username,
                    "player_id": player_id,
                    "schedule_id": schedule_id,
                    "schedule_type": schedule_type,
                    "error": error_msg,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "duration_seconds": (
                        datetime.now(UTC) - start_time
                    ).total_seconds(),
                }

            if not player.is_active:
                info_msg = f"Player '{username}' is inactive, skipping fetch"
                logger.info(f"{info_msg} (schedule_id: {schedule_id})")
                return {
                    "status": "skipped",
                    "username": username,
                    "player_id": player.id,
                    "schedule_id": schedule_id,
                    "schedule_type": schedule_type,
                    "message": info_msg,
                    "reason": "player_inactive",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "duration_seconds": (
                        datetime.now(UTC) - start_time
                    ).total_seconds(),
                }

            # Get the most recent hiscore record for comparison
            last_record_stmt = (
                select(HiscoreRecord)
                .where(HiscoreRecord.player_id == player.id)
                .order_by(HiscoreRecord.fetched_at.desc())
                .limit(1)
            )
            last_record_result = await db_session.execute(last_record_stmt)
            last_record = last_record_result.scalar_one_or_none()

            # Fetch hiscore data from OSRS API
            async with OSRSAPIClient() as osrs_client:
                try:
                    logger.debug(
                        f"Fetching hiscore data from OSRS API for {username}"
                    )
                    hiscore_data = await osrs_client.fetch_player_hiscores(
                        username
                    )
                    logger.debug(
                        f"Successfully fetched hiscore data for {username}"
                    )

                except PlayerNotFoundError as e:
                    logger.warning(
                        f"Player {username} not found in OSRS hiscores: {e} (schedule_id: {schedule_id})"
                    )
                    # Player might have been renamed or deleted from hiscores
                    # This is not a retry-able error, just log and return warning status
                    return {
                        "status": "warning",
                        "error_type": "osrs_player_not_found",
                        "username": username,
                        "player_id": player.id,
                        "schedule_id": schedule_id,
                        "schedule_type": schedule_type,
                        "error": str(e),
                        "message": "Player not found in OSRS hiscores - may have been renamed or deleted",
                        "timestamp": datetime.now(UTC).isoformat(),
                        "duration_seconds": (
                            datetime.now(UTC) - start_time
                        ).total_seconds(),
                    }

                except RateLimitError as e:
                    logger.error(
                        f"OSRS API rate limit exceeded for {username}: {e} (schedule_id: {schedule_id})"
                    )
                    # Rate limit errors should trigger task retry
                    raise

                except APIUnavailableError as e:
                    logger.error(
                        f"OSRS API unavailable for {username}: {e} (schedule_id: {schedule_id})"
                    )
                    # API unavailable errors should trigger task retry
                    raise

                except OSRSAPIError as e:
                    logger.error(
                        f"OSRS API error for {username}: {e} (schedule_id: {schedule_id})"
                    )
                    # Other API errors are not retry-able
                    return {
                        "status": "error",
                        "error_type": "osrs_api_error",
                        "username": username,
                        "player_id": player.id,
                        "schedule_id": schedule_id,
                        "schedule_type": schedule_type,
                        "error": str(e),
                        "timestamp": datetime.now(UTC).isoformat(),
                        "duration_seconds": (
                            datetime.now(UTC) - start_time
                        ).total_seconds(),
                    }

            # Check if data has changed compared to the last record
            data_changed = _hiscore_data_changed(hiscore_data, last_record)

            # Always update player's last_fetched timestamp regardless of data changes
            player.last_fetched = hiscore_data.fetched_at

            if not data_changed:
                # Data hasn't changed, don't save a new record
                await db_session.commit()  # Still commit to update last_fetched

                duration = (datetime.now(UTC) - start_time).total_seconds()

                logger.info(
                    f"Hiscore data for {username} unchanged, skipping save "
                    f"(duration: {duration:.2f}s, schedule_id: {schedule_id})"
                )

                return {
                    "status": "unchanged",
                    "username": username,
                    "player_id": player.id,
                    "schedule_id": schedule_id,
                    "schedule_type": schedule_type,
                    "message": "Hiscore data unchanged from previous fetch",
                    "last_record_id": last_record.id if last_record else None,
                    "overall_rank": hiscore_data.overall.get("rank"),
                    "overall_level": hiscore_data.overall.get("level"),
                    "overall_experience": hiscore_data.overall.get(
                        "experience"
                    ),
                    "skills_count": len(hiscore_data.skills),
                    "bosses_count": len(hiscore_data.bosses),
                    "fetched_at": hiscore_data.fetched_at.isoformat(),
                    "timestamp": datetime.now(UTC).isoformat(),
                    "duration_seconds": duration,
                }

            # Data has changed, create and save new hiscore record
            hiscore_record = HiscoreRecord(
                player_id=player.id,
                fetched_at=hiscore_data.fetched_at,
                overall_rank=hiscore_data.overall.get("rank"),
                overall_level=hiscore_data.overall.get("level"),
                overall_experience=hiscore_data.overall.get("experience"),
                skills_data=hiscore_data.skills,
                bosses_data=hiscore_data.bosses,
            )

            # Save to database
            db_session.add(hiscore_record)
            await db_session.commit()
            await db_session.refresh(hiscore_record)

            duration = (datetime.now(UTC) - start_time).total_seconds()

            logger.info(
                f"Successfully stored new hiscore data for {username} "
                f"(record ID: {hiscore_record.id}, duration: {duration:.2f}s, schedule_id: {schedule_id})"
            )

            return {
                "status": "success",
                "username": username,
                "player_id": player.id,
                "schedule_id": schedule_id,
                "schedule_type": schedule_type,
                "record_id": hiscore_record.id,
                "data_changed": True,
                "overall_rank": hiscore_record.overall_rank,
                "overall_level": hiscore_record.overall_level,
                "overall_experience": hiscore_record.overall_experience,
                "skills_count": len(hiscore_data.skills),
                "bosses_count": len(hiscore_data.bosses),
                "fetched_at": hiscore_data.fetched_at.isoformat(),
                "timestamp": datetime.now(UTC).isoformat(),
                "duration_seconds": duration,
            }

        except (RateLimitError, APIUnavailableError):
            # Re-raise these for task retry
            raise

        except Exception as e:
            await db_session.rollback()
            logger.error(
                f"Unexpected error fetching hiscores for {username}: {e} (schedule_id: {schedule_id})"
            )
            # Unexpected errors should also trigger retry
            raise


async def _fetch_all_players() -> Dict[str, Any]:
    """
    Fetch hiscore data for all active players immediately.

    This is a utility task for manual triggering of fetches for all players,
    regardless of their last fetch time or interval settings. Useful for
    administrative purposes or initial data population.

    Returns:
        Dict containing processing results and statistics
    """
    logger.info("Starting fetch for all active players")
    start_time = datetime.now(UTC)

    async with AsyncSessionLocal() as db_session:
        try:
            # Get all active players
            stmt = (
                select(Player)
                .where(Player.is_active.is_(True))
                .order_by(Player.username)
            )
            result = await db_session.execute(stmt)
            active_players = result.scalars().all()

            if not active_players:
                logger.info("No active players found")
                return {
                    "status": "success",
                    "message": "No active players to fetch",
                    "players_processed": 0,
                    "tasks_enqueued": 0,
                    "failed_enqueues": 0,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "duration_seconds": (
                        datetime.now(UTC) - start_time
                    ).total_seconds(),
                }

            logger.info(
                f"Enqueuing fetch tasks for {len(active_players)} active players"
            )

            # Enqueue fetch tasks for all active players
            tasks_enqueued = 0
            failed_enqueues = 0
            enqueue_errors = []

            for player in active_players:
                try:
                    # Import the task here to avoid circular imports
                    from app.workers.tasks import (
                        fetch_player_hiscores_task,
                    )

                    await fetch_player_hiscores_task.kiq(player.username)
                    tasks_enqueued += 1
                    logger.debug(f"Enqueued fetch task for {player.username}")

                except Exception as e:
                    failed_enqueues += 1
                    error_msg = f"Failed to enqueue fetch task for {player.username}: {e}"
                    enqueue_errors.append(error_msg)
                    logger.error(error_msg)

            duration = (datetime.now(UTC) - start_time).total_seconds()

            logger.info(
                f"Fetch all players complete: {tasks_enqueued} tasks enqueued, "
                f"{failed_enqueues} failed (duration: {duration:.2f}s)"
            )

            response_data = {
                "status": "success",
                "players_processed": len(active_players),
                "tasks_enqueued": tasks_enqueued,
                "failed_enqueues": failed_enqueues,
                "timestamp": datetime.now(UTC).isoformat(),
                "duration_seconds": duration,
            }

            if enqueue_errors:
                response_data["enqueue_errors"] = enqueue_errors

            return response_data

        except Exception as e:
            duration = (datetime.now(UTC) - start_time).total_seconds()
            logger.error(f"Error in fetch all players: {e}")
            raise


# Task decorators and exports
fetch_player_hiscores_task = broker.task(
    **get_task_defaults(
        retry_count=5,  # More retries for API calls
        retry_delay=5.0,  # Longer delay between retries for rate limiting
        task_timeout=120.0,  # 2 minutes timeout for individual fetch
    )
)(_fetch_player_hiscores)


fetch_all_players_task = broker.task(
    **get_task_defaults(
        retry_count=2,
        retry_delay=15.0,
        task_timeout=600.0,  # 10 minutes for fetching all players
    )
)(_fetch_all_players)
