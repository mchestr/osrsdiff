"""Hiscore data fetching worker tasks."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.base import AsyncSessionLocal
from src.models.hiscore import HiscoreRecord
from src.models.player import Player
from src.services.osrs_api import (
    APIUnavailableError,
    HiscoreData,
    OSRSAPIClient,
    OSRSAPIError,
    PlayerNotFoundError,
    RateLimitError,
)
from src.workers.main import broker, get_task_defaults

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


async def _fetch_player_hiscores(username: str) -> Dict[str, Any]:
    """
    Fetch and store hiscore data for a specific player.

    This task retrieves current hiscore data from the OSRS API and stores
    it as a new HiscoreRecord in the database only if the data has changed
    from the previous record. It handles various error conditions gracefully
    and provides detailed status information.

    Args:
        username: OSRS player username to fetch data for

    Returns:
        Dict containing task execution results with status, data, and metadata

    Raises:
        RateLimitError: If OSRS API rate limit is exceeded (will trigger retry)
        APIUnavailableError: If OSRS API is unavailable (will trigger retry)
        Exception: For database or other unexpected errors (will trigger retry)
    """
    logger.info(f"Starting hiscore fetch for player: {username}")
    start_time = datetime.now(UTC)

    async with AsyncSessionLocal() as db_session:
        try:
            # Get player from database
            stmt = select(Player).where(Player.username.ilike(username))
            result = await db_session.execute(stmt)
            player = result.scalar_one_or_none()

            if not player:
                error_msg = f"Player '{username}' not found in database"
                logger.error(error_msg)
                return {
                    "status": "error",
                    "error_type": "player_not_found",
                    "username": username,
                    "error": error_msg,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "duration_seconds": (
                        datetime.now(UTC) - start_time
                    ).total_seconds(),
                }

            if not player.is_active:
                info_msg = f"Player '{username}' is inactive, skipping fetch"
                logger.info(info_msg)
                return {
                    "status": "skipped",
                    "username": username,
                    "player_id": player.id,
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

            # Fetch hiscore data from OSRS API using player's game mode
            async with OSRSAPIClient() as osrs_client:
                try:
                    logger.debug(
                        f"Fetching hiscore data from OSRS API for {username} (game mode: {player.game_mode.value})"
                    )
                    hiscore_data = await osrs_client.fetch_player_hiscores(
                        username, player.game_mode.value
                    )
                    logger.debug(
                        f"Successfully fetched hiscore data for {username}"
                    )

                except PlayerNotFoundError as e:
                    logger.warning(
                        f"Player {username} not found in OSRS hiscores: {e}"
                    )
                    # Player might have been renamed or deleted from hiscores
                    # This is not a retry-able error, just log and return warning status
                    return {
                        "status": "warning",
                        "error_type": "osrs_player_not_found",
                        "username": username,
                        "player_id": player.id,
                        "error": str(e),
                        "message": "Player not found in OSRS hiscores - may have been renamed or deleted",
                        "timestamp": datetime.now(UTC).isoformat(),
                        "duration_seconds": (
                            datetime.now(UTC) - start_time
                        ).total_seconds(),
                    }

                except RateLimitError as e:
                    logger.error(
                        f"OSRS API rate limit exceeded for {username}: {e}"
                    )
                    # Rate limit errors should trigger task retry
                    raise

                except APIUnavailableError as e:
                    logger.error(f"OSRS API unavailable for {username}: {e}")
                    # API unavailable errors should trigger task retry
                    raise

                except OSRSAPIError as e:
                    logger.error(f"OSRS API error for {username}: {e}")
                    # Other API errors are not retry-able
                    return {
                        "status": "error",
                        "error_type": "osrs_api_error",
                        "username": username,
                        "player_id": player.id,
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
                    f"(duration: {duration:.2f}s)"
                )

                return {
                    "status": "unchanged",
                    "username": username,
                    "player_id": player.id,
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
                f"(record ID: {hiscore_record.id}, duration: {duration:.2f}s)"
            )

            return {
                "status": "success",
                "username": username,
                "player_id": player.id,
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
                f"Unexpected error fetching hiscores for {username}: {e}"
            )
            # Unexpected errors should also trigger retry
            raise


async def _process_scheduled_fetches() -> Dict[str, Any]:
    """
    Process scheduled hiscore fetches for all active players.

    This task queries all active players and determines which ones need
    their hiscore data updated based on their fetch_interval_minutes setting.
    It then enqueues individual fetch tasks for each player that needs updating.

    The task respects each player's individual fetch interval and only enqueues
    tasks for players whose data is stale according to their settings.

    Returns:
        Dict containing processing results and statistics
    """
    logger.info("Starting scheduled fetch processing")
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
                logger.info("No active players found for scheduled fetching")
                return {
                    "status": "success",
                    "message": "No active players to process",
                    "players_processed": 0,
                    "players_needing_fetch": 0,
                    "tasks_enqueued": 0,
                    "failed_enqueues": 0,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "duration_seconds": (
                        datetime.now(UTC) - start_time
                    ).total_seconds(),
                }

            logger.info(f"Found {len(active_players)} active players")

            # Determine which players need fetching
            current_time = datetime.now(UTC)
            players_to_fetch = []

            for player in active_players:
                # Check if player needs fetching based on interval
                if player.last_fetched is None:
                    # Never fetched before, definitely needs fetching
                    players_to_fetch.append(player)
                    logger.debug(
                        f"Player {player.username} never fetched, queuing"
                    )
                else:
                    # Check if enough time has passed since last fetch
                    time_since_fetch = current_time - player.last_fetched
                    fetch_interval = timedelta(
                        minutes=player.fetch_interval_minutes
                    )

                    if time_since_fetch >= fetch_interval:
                        players_to_fetch.append(player)
                        logger.debug(
                            f"Player {player.username} last fetched "
                            f"{time_since_fetch} ago, queuing (interval: {fetch_interval})"
                        )
                    else:
                        time_remaining = fetch_interval - time_since_fetch
                        logger.debug(
                            f"Player {player.username} fetched recently, "
                            f"next fetch in {time_remaining}"
                        )

            if not players_to_fetch:
                logger.info("No players need fetching at this time")
                return {
                    "status": "success",
                    "message": "No players need fetching",
                    "players_processed": len(active_players),
                    "players_needing_fetch": 0,
                    "tasks_enqueued": 0,
                    "failed_enqueues": 0,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "duration_seconds": (
                        datetime.now(UTC) - start_time
                    ).total_seconds(),
                }

            # Enqueue fetch tasks for players that need updating
            tasks_enqueued = 0
            failed_enqueues = 0
            enqueue_errors = []

            for player in players_to_fetch:
                try:
                    # Import the task here to avoid circular imports
                    from src.workers.tasks import fetch_player_hiscores_task

                    # Enqueue individual fetch task
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
                f"Scheduled fetch processing complete: {tasks_enqueued} tasks enqueued, "
                f"{failed_enqueues} failed (duration: {duration:.2f}s)"
            )

            response_data = {
                "status": "success",
                "players_processed": len(active_players),
                "players_needing_fetch": len(players_to_fetch),
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
            logger.error(f"Error in scheduled fetch processing: {e}")
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
                    from src.workers.tasks import fetch_player_hiscores_task

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

process_scheduled_fetches_task = broker.task(
    **get_task_defaults(
        retry_count=3,
        retry_delay=10.0,
        task_timeout=300.0,  # 5 minutes for processing all players
    )
)(_process_scheduled_fetches)

fetch_all_players_task = broker.task(
    **get_task_defaults(
        retry_count=2,
        retry_delay=15.0,
        task_timeout=600.0,  # 10 minutes for fetching all players
    )
)(_fetch_all_players)


async def _check_game_mode_downgrades() -> Dict[str, Any]:
    """
    Check all active players for game mode downgrades.

    This task runs daily to detect when players have transitioned between game modes
    (e.g., hardcore ironman dies and becomes regular ironman, or ironman becomes regular).
    It updates the player's game mode in the database and logs any changes.

    Returns:
        Dict containing task execution results with statistics and any changes detected
    """
    logger.info("Starting daily game mode downgrade check")
    start_time = datetime.now(UTC)

    players_checked = 0
    players_updated = 0
    errors = []
    changes = []

    async with AsyncSessionLocal() as db_session:
        try:
            # Get all active players
            stmt = select(Player).where(Player.is_active.is_(True))
            db_result = await db_session.execute(stmt)
            active_players = db_result.scalars().all()

            logger.info(
                f"Checking game modes for {len(active_players)} active players"
            )

            async with OSRSAPIClient() as osrs_client:
                for player in active_players:
                    try:
                        players_checked += 1
                        old_game_mode = player.game_mode.value

                        logger.debug(
                            f"Checking game mode for {player.username} (current: {old_game_mode})"
                        )

                        # Detect current game mode
                        detected_game_mode = (
                            await osrs_client.detect_player_game_mode(
                                player.username
                            )
                        )

                        if detected_game_mode != old_game_mode:
                            # Import GameMode enum
                            from src.models.player import GameMode

                            new_game_mode_enum = GameMode(detected_game_mode)

                            # Update player's game mode
                            player.game_mode = new_game_mode_enum
                            players_updated += 1

                            change_info = {
                                "username": player.username,
                                "old_mode": old_game_mode,
                                "new_mode": detected_game_mode,
                                "timestamp": datetime.now(UTC).isoformat(),
                            }
                            changes.append(change_info)

                            logger.info(
                                f"Game mode changed for {player.username}: {old_game_mode} → {detected_game_mode}"
                            )
                        else:
                            logger.debug(
                                f"No game mode change for {player.username}"
                            )

                    except PlayerNotFoundError:
                        # Player not found in any hiscores - they might have been renamed or deleted
                        error_info = {
                            "username": player.username,
                            "error": "Player not found in OSRS hiscores",
                            "timestamp": datetime.now(UTC).isoformat(),
                        }
                        errors.append(error_info)
                        logger.warning(
                            f"Player {player.username} not found in OSRS hiscores during game mode check"
                        )

                    except (RateLimitError, APIUnavailableError) as e:
                        # API issues - log but don't fail the entire task
                        error_info = {
                            "username": player.username,
                            "error": f"OSRS API error: {str(e)}",
                            "timestamp": datetime.now(UTC).isoformat(),
                        }
                        errors.append(error_info)
                        logger.error(
                            f"OSRS API error checking {player.username}: {e}"
                        )

                    except Exception as e:
                        # Unexpected error for this player
                        error_info = {
                            "username": player.username,
                            "error": f"Unexpected error: {str(e)}",
                            "timestamp": datetime.now(UTC).isoformat(),
                        }
                        errors.append(error_info)
                        logger.error(
                            f"Unexpected error checking game mode for {player.username}: {e}"
                        )

                    # Small delay between players to be respectful to the OSRS API
                    await asyncio.sleep(
                        2.1
                    )  # Slightly longer than the API client's rate limit

            # Commit all changes
            await db_session.commit()

            duration = (datetime.now(UTC) - start_time).total_seconds()

            result = {
                "status": "completed",
                "timestamp": datetime.now(UTC).isoformat(),
                "duration_seconds": duration,
                "players_checked": players_checked,
                "players_updated": players_updated,
                "changes": changes,
                "errors": errors,
                "message": f"Game mode check completed: {players_checked} players checked, {players_updated} updated, {len(errors)} errors",
            }

            if changes:
                logger.info(
                    f"Game mode downgrade check completed with {len(changes)} changes detected"
                )
                for change in changes:
                    logger.info(
                        f"  {change['username']}: {change['old_mode']} → {change['new_mode']}"
                    )
            else:
                logger.info(
                    "Game mode downgrade check completed with no changes detected"
                )

            if errors:
                logger.warning(f"Game mode check had {len(errors)} errors")

            return result

        except Exception as e:
            await db_session.rollback()
            logger.error(f"Fatal error during game mode downgrade check: {e}")
            return {
                "status": "error",
                "timestamp": datetime.now(UTC).isoformat(),
                "duration_seconds": (
                    datetime.now(UTC) - start_time
                ).total_seconds(),
                "players_checked": players_checked,
                "players_updated": players_updated,
                "changes": changes,
                "errors": errors,
                "error": str(e),
                "message": f"Game mode check failed after checking {players_checked} players",
            }


check_game_mode_downgrades_task = broker.task(
    **get_task_defaults(
        retry_count=2,
        retry_delay=30.0,
        task_timeout=1800.0,  # 30 minutes for checking all players
    )
)(_check_game_mode_downgrades)
