import logging
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from taskiq_redis import ListRedisScheduleSource

from app.models.player import Player

logger = logging.getLogger(__name__)


class ScheduleMaintenanceService:
    """
    Service for performing schedule maintenance operations.

    This service provides methods for cleaning up orphaned schedules,
    verifying consistency, and performing bulk operations on player schedules.

    Works directly with Redis schedule source to avoid issues with the scheduler abstraction.
    """

    def __init__(self, redis_source: ListRedisScheduleSource):
        """
        Initialize the maintenance service.

        Args:
            redis_source: Redis schedule source for direct Redis access
        """
        self.redis_source = redis_source

    async def cleanup_orphaned_schedules(
        self, db_session: AsyncSession, dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Remove schedules for deleted or inactive players.

        Args:
            db_session: Database session
            dry_run: If True, return what would be done without making changes

        Returns:
            Dict with cleanup results and statistics
        """
        logger.info("Starting cleanup of orphaned schedules")

        try:
            # Get all schedules from Redis directly
            logger.debug("Fetching all schedules from Redis")
            all_schedules = await self.redis_source.get_schedules()
            logger.debug(
                f"Retrieved {len(all_schedules)} total schedules from Redis"
            )

            player_schedules = [
                s
                for s in all_schedules
                if hasattr(s, "schedule_id")
                and s.schedule_id.startswith("player_fetch_")
            ]
            logger.debug(
                f"Found {len(player_schedules)} player schedules (filtered by 'player_fetch_' prefix)"
            )

            if not player_schedules:
                logger.info("No player schedules found in Redis")
                return {
                    "status": "success",
                    "message": "No player schedules found",
                    "schedules_processed": 0,
                    "schedules_removed": 0,
                    "orphaned_schedules": [],
                }

            # Get all active players with their schedule_ids
            logger.debug("Fetching active players from database")
            active_players_stmt = select(
                Player.id, Player.username, Player.schedule_id
            ).where(Player.is_active.is_(True))
            active_players_result = await db_session.execute(
                active_players_stmt
            )
            active_players = active_players_result.all()
            logger.debug(
                f"Found {len(active_players)} active players in database"
            )

            # Create sets for efficient lookup
            active_player_ids = {str(player.id) for player in active_players}
            active_schedule_ids = {
                player.schedule_id
                for player in active_players
                if player.schedule_id is not None
            }
            logger.debug(
                f"Active player IDs: {len(active_player_ids)}, "
                f"Active schedule IDs: {len(active_schedule_ids)}"
            )

            # Find orphaned schedules
            # Use a set to track schedule_ids we've already processed to avoid duplicates
            orphaned_schedule_ids = set()
            orphaned_schedules = []
            processed_count = 0
            skipped_duplicate_count = 0

            logger.debug(
                f"Processing {len(player_schedules)} player schedules to find orphaned ones"
            )
            for schedule in player_schedules:
                try:
                    schedule_id = schedule.schedule_id
                    logger.debug(f"Processing schedule: {schedule_id}")

                    # Skip if we've already processed this schedule_id
                    if schedule_id in orphaned_schedule_ids:
                        skipped_duplicate_count += 1
                        logger.debug(
                            f"Skipping duplicate schedule_id: {schedule_id}"
                        )
                        continue

                    # Extract player ID from schedule ID
                    if not schedule_id.startswith("player_fetch_"):
                        logger.debug(
                            f"Skipping non-player schedule: {schedule_id}"
                        )
                        continue

                    try:
                        player_id_str = schedule_id.replace(
                            "player_fetch_", ""
                        )
                        player_id = int(player_id_str)
                        logger.debug(
                            f"Extracted player_id {player_id} from schedule_id {schedule_id}"
                        )
                    except ValueError as e:
                        logger.warning(
                            f"Invalid player ID format in schedule_id {schedule_id}: {e}"
                        )
                        orphaned_schedule_ids.add(schedule_id)
                        orphaned_schedules.append(
                            {
                                "schedule_id": schedule_id,
                                "reason": "Invalid player ID format",
                                "player_id": None,
                            }
                        )
                        continue

                    # Check if player exists and is active
                    player_id_str = str(player_id)
                    if player_id_str not in active_player_ids:
                        logger.debug(
                            f"Schedule {schedule_id} is orphaned: player_id {player_id} not in active players"
                        )
                        orphaned_schedule_ids.add(schedule_id)
                        orphaned_schedules.append(
                            {
                                "schedule_id": schedule_id,
                                "reason": "Player not found or inactive",
                                "player_id": str(player_id),
                            }
                        )
                    elif schedule_id not in active_schedule_ids:
                        logger.debug(
                            f"Schedule {schedule_id} is orphaned: schedule_id not referenced in database "
                            f"(player_id {player_id} exists but has different schedule_id)"
                        )
                        orphaned_schedule_ids.add(schedule_id)
                        orphaned_schedules.append(
                            {
                                "schedule_id": schedule_id,
                                "reason": "Schedule not referenced in database",
                                "player_id": str(player_id),
                            }
                        )
                    else:
                        logger.debug(
                            f"Schedule {schedule_id} is valid (player_id {player_id} exists and is active)"
                        )

                    processed_count += 1

                except Exception as e:
                    schedule_id_value = getattr(
                        schedule, "schedule_id", "unknown"
                    )
                    logger.error(
                        f"Error processing schedule {schedule_id_value}: {e}",
                        exc_info=True,
                    )
                    if schedule_id_value not in orphaned_schedule_ids:
                        orphaned_schedule_ids.add(schedule_id_value)
                        orphaned_schedules.append(
                            {
                                "schedule_id": schedule_id_value,
                                "reason": f"Processing error: {str(e)}",
                                "player_id": None,
                            }
                        )

            logger.info(
                f"Processed {processed_count} schedules, skipped {skipped_duplicate_count} duplicates, "
                f"found {len(orphaned_schedules)} orphaned schedules"
            )

            # Remove orphaned schedules if not dry run
            removed_count = 0
            removal_errors = []

            if not dry_run:
                logger.info(
                    f"Starting removal of {len(orphaned_schedules)} orphaned schedules"
                )
                for orphan in orphaned_schedules:
                    try:
                        schedule_id_value = orphan.get("schedule_id")
                        reason = orphan.get("reason", "Unknown reason")
                        orphan_player_id = orphan.get("player_id", "unknown")

                        logger.debug(
                            f"Attempting to remove orphaned schedule: {schedule_id_value} "
                            f"(reason: {reason}, player_id: {orphan_player_id})"
                        )

                        if (
                            schedule_id_value is not None
                            and schedule_id_value != "unknown"
                        ):
                            await self.redis_source.delete_schedule(
                                str(schedule_id_value)
                            )
                            logger.debug(
                                f"Successfully deleted schedule {schedule_id_value} from Redis"
                            )
                        else:
                            logger.warning(
                                f"Skipping removal of schedule with invalid ID: {schedule_id_value}"
                            )

                        removed_count += 1
                        logger.info(
                            f"Removed orphaned schedule: {schedule_id_value} ({reason})"
                        )
                    except Exception as e:
                        error_msg = f"Failed to remove {orphan['schedule_id']}: {str(e)}"
                        removal_errors.append(error_msg)
                        logger.error(
                            f"Error removing orphaned schedule {orphan['schedule_id']}: {e}",
                            exc_info=True,
                        )

                logger.info(
                    f"Completed removal: {removed_count} schedules removed, "
                    f"{len(removal_errors)} errors"
                )
            else:
                logger.info(
                    f"DRY RUN: Would remove {len(orphaned_schedules)} orphaned schedules"
                )

            result = {
                "status": "success",
                "message": f"Cleanup completed: {len(orphaned_schedules)} orphaned schedules found",
                "schedules_processed": len(player_schedules),
                "schedules_removed": removed_count if not dry_run else 0,
                "orphaned_schedules": orphaned_schedules,
                "dry_run": dry_run,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            if removal_errors:
                result["removal_errors"] = removal_errors

            return result

        except Exception as e:
            logger.error(f"Error during orphaned schedule cleanup: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Cleanup failed: {str(e)}",
                "timestamp": datetime.now(UTC).isoformat(),
            }

    async def verify_schedule_consistency(
        self, db_session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Verify consistency between database and Redis schedules.

        Args:
            db_session: Database session

        Returns:
            Dict with verification results and inconsistencies found
        """
        logger.info("Starting schedule consistency verification")

        try:
            # Get all schedules from Redis directly
            all_schedules = await self.redis_source.get_schedules()
            player_schedules = [
                s
                for s in all_schedules
                if hasattr(s, "schedule_id")
                and s.schedule_id.startswith("player_fetch_")
            ]

            # Create lookup for Redis schedules
            redis_schedule_ids = {
                schedule.schedule_id for schedule in player_schedules
            }

            # Get all active players with schedule_ids
            active_players_stmt = select(Player).where(
                Player.is_active.is_(True), Player.schedule_id.is_not(None)
            )
            active_players_result = await db_session.execute(
                active_players_stmt
            )
            active_players = list(active_players_result.scalars().all())

            inconsistencies = []

            # Check each player's schedule
            for player in active_players:
                try:
                    if not player.schedule_id:
                        inconsistencies.append(
                            {
                                "type": "null_schedule_id",
                                "player_id": player.id,
                                "username": player.username,
                                "issue": "Player has null schedule_id",
                            }
                        )
                        continue

                    # Check if schedule exists in Redis
                    if player.schedule_id not in redis_schedule_ids:
                        inconsistencies.append(
                            {
                                "type": "missing_redis_schedule",
                                "player_id": player.id,
                                "username": player.username,
                                "schedule_id": player.schedule_id,
                                "issue": f"Schedule {player.schedule_id} not found in Redis",
                            }
                        )
                        continue

                    # Verify schedule configuration by checking if schedule exists in Redis
                    is_valid = False
                    try:
                        redis_schedules = (
                            await self.redis_source.get_schedules()
                        )
                        for redis_schedule in redis_schedules:
                            if (
                                redis_schedule.schedule_id
                                == player.schedule_id
                            ):
                                is_valid = True
                                break
                    except Exception as e:
                        logger.warning(
                            f"Error verifying schedule for {player.username}: {e}"
                        )

                    if not is_valid:
                        inconsistencies.append(
                            {
                                "type": "invalid_schedule_config",
                                "player_id": player.id,
                                "username": player.username,
                                "schedule_id": player.schedule_id,
                                "issue": "Schedule configuration is invalid or misconfigured",
                            }
                        )

                except Exception as e:
                    inconsistencies.append(
                        {
                            "type": "verification_error",
                            "player_id": player.id,
                            "username": player.username,
                            "schedule_id": getattr(
                                player, "schedule_id", None
                            ),
                            "issue": f"Error verifying schedule: {str(e)}",
                        }
                    )

            # Check for schedules in Redis without corresponding active players
            active_player_ids = {player.id for player in active_players}

            for schedule in player_schedules:
                try:
                    schedule_id = schedule.schedule_id

                    if schedule_id.startswith("player_fetch_"):
                        try:
                            player_id_str = schedule_id.replace(
                                "player_fetch_", ""
                            )
                            player_id = int(player_id_str)

                            if player_id not in active_player_ids:
                                inconsistencies.append(
                                    {
                                        "type": "orphaned_redis_schedule",
                                        "schedule_id": schedule_id,
                                        "player_id": player_id,
                                        "issue": f"No active player found for player_id {player_id}",
                                    }
                                )
                            else:
                                # Find the corresponding player
                                corresponding_player = next(
                                    (
                                        p
                                        for p in active_players
                                        if p.id == player_id
                                    ),
                                    None,
                                )
                                if (
                                    corresponding_player
                                    and corresponding_player.schedule_id
                                    != schedule_id
                                ):
                                    inconsistencies.append(
                                        {
                                            "type": "schedule_id_mismatch",
                                            "schedule_id": schedule_id,
                                            "player_id": player_id,
                                            "username": corresponding_player.username,
                                            "db_schedule_id": corresponding_player.schedule_id,
                                            "issue": f"Player has different schedule_id in database: {corresponding_player.schedule_id}",
                                        }
                                    )

                        except ValueError:
                            inconsistencies.append(
                                {
                                    "type": "invalid_schedule_format",
                                    "schedule_id": schedule_id,
                                    "issue": "Invalid player ID format in schedule_id",
                                }
                            )

                except Exception as e:
                    inconsistencies.append(
                        {
                            "type": "schedule_check_error",
                            "schedule_id": getattr(
                                schedule, "schedule_id", "unknown"
                            ),
                            "issue": f"Error checking schedule: {str(e)}",
                        }
                    )

            # Categorize inconsistencies
            inconsistency_counts: Dict[str, int] = {}
            for inconsistency in inconsistencies:
                inconsistency_type = str(inconsistency.get("type", "unknown"))
                inconsistency_counts[inconsistency_type] = (
                    inconsistency_counts.get(inconsistency_type, 0) + 1
                )

            is_consistent = len(inconsistencies) == 0

            return {
                "status": "success",
                "is_consistent": is_consistent,
                "message": f"Verification completed: {'No inconsistencies found' if is_consistent else f'{len(inconsistencies)} inconsistencies found'}",
                "redis_schedules_count": len(player_schedules),
                "active_players_count": len(active_players),
                "inconsistencies_count": len(inconsistencies),
                "inconsistency_types": inconsistency_counts,
                "inconsistencies": inconsistencies,
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error during consistency verification: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Verification failed: {str(e)}",
                "timestamp": datetime.now(UTC).isoformat(),
            }

    async def get_schedule_summary(
        self, db_session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Get a summary of all schedules and their status.

        Args:
            db_session: Database session

        Returns:
            Dict with schedule summary information
        """
        logger.info("Getting schedule summary")

        try:
            # Get Redis schedules
            all_schedules = await self.redis_source.get_schedules()
            player_schedules = [
                s
                for s in all_schedules
                if hasattr(s, "schedule_id")
                and s.schedule_id.startswith("player_fetch_")
            ]

            # Get database statistics
            total_players_stmt = select(func.count(Player.id))
            total_players_result = await db_session.execute(total_players_stmt)
            total_players = total_players_result.scalar() or 0

            active_players_stmt = select(func.count(Player.id)).where(
                Player.is_active.is_(True)
            )
            active_players_result = await db_session.execute(
                active_players_stmt
            )
            active_players = active_players_result.scalar() or 0

            scheduled_players_stmt = select(func.count(Player.id)).where(
                Player.is_active.is_(True), Player.schedule_id.is_not(None)
            )
            scheduled_players_result = await db_session.execute(
                scheduled_players_stmt
            )
            scheduled_players = scheduled_players_result.scalar() or 0

            unscheduled_players_stmt = select(func.count(Player.id)).where(
                Player.is_active.is_(True), Player.schedule_id.is_(None)
            )
            unscheduled_players_result = await db_session.execute(
                unscheduled_players_stmt
            )
            unscheduled_players = unscheduled_players_result.scalar() or 0

            return {
                "status": "success",
                "summary": {
                    "total_players": total_players,
                    "active_players": active_players,
                    "scheduled_players": scheduled_players,
                    "unscheduled_players": unscheduled_players,
                    "redis_schedules": len(player_schedules),
                    "schedule_coverage_percentage": (
                        scheduled_players / max(1, active_players)
                    )
                    * 100,
                },
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting schedule summary: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to get schedule summary: {str(e)}",
                "timestamp": datetime.now(UTC).isoformat(),
            }

    async def fix_player_schedule(
        self,
        player: Player,
        db_session: AsyncSession,
        force_recreate: bool = False,
    ) -> Dict[str, Any]:
        """
        Fix a specific player's schedule by ensuring it exists and is valid.

        Args:
            player: Player to fix schedule for
            db_session: Database session
            force_recreate: If True, recreate schedule even if it appears valid

        Returns:
            Dict with fix results
        """
        logger.info(
            f"Fixing schedule for player {player.username} (ID: {player.id})"
        )

        try:
            if not player.is_active:
                return {
                    "status": "error",
                    "player_id": player.id,
                    "username": player.username,
                    "error": "Player is inactive",
                    "message": "Cannot fix schedule for inactive player",
                }

            old_schedule_id = player.schedule_id

            if force_recreate:
                # Force recreation by clearing schedule_id first
                if old_schedule_id:
                    try:
                        await self.redis_source.delete_schedule(
                            old_schedule_id
                        )
                        logger.info(
                            f"Deleted old schedule {old_schedule_id} for forced recreation"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Could not delete old schedule {old_schedule_id}: {e}"
                        )

                player.schedule_id = None

            # Check if schedule exists in Redis, if not we can't recreate it here
            # (schedule creation should be done through PlayerScheduleManager)
            from app.services.scheduler import get_player_schedule_manager

            schedule_manager = get_player_schedule_manager()
            new_schedule_id = await schedule_manager.ensure_player_scheduled(
                player
            )

            # Update database
            player.schedule_id = new_schedule_id
            await db_session.commit()

            action = (
                "recreated"
                if force_recreate or old_schedule_id != new_schedule_id
                else "verified"
            )

            return {
                "status": "success",
                "player_id": player.id,
                "username": player.username,
                "action": action,
                "old_schedule_id": old_schedule_id,
                "new_schedule_id": new_schedule_id,
                "fetch_interval": player.fetch_interval_minutes,
                "message": f"Successfully {action} schedule for {player.username}: {new_schedule_id}",
            }

        except Exception as e:
            await db_session.rollback()
            logger.error(
                f"Error fixing schedule for player {player.username}: {e}"
            )
            return {
                "status": "error",
                "player_id": player.id,
                "username": player.username,
                "error": str(e),
                "message": f"Failed to fix schedule: {str(e)}",
            }

    async def bulk_fix_schedules(
        self,
        db_session: AsyncSession,
        player_ids: Optional[List[int]] = None,
        force_recreate: bool = False,
    ) -> Dict[str, Any]:
        """
        Fix schedules for multiple players.

        Args:
            db_session: Database session
            player_ids: Specific player IDs to fix (None for all active players)
            force_recreate: If True, recreate all schedules even if they appear valid

        Returns:
            Dict with bulk fix results
        """
        logger.info(
            f"Starting bulk schedule fix (force_recreate: {force_recreate})"
        )

        try:
            # Get players to fix
            if player_ids:
                players_stmt = select(Player).where(
                    Player.id.in_(player_ids), Player.is_active.is_(True)
                )
            else:
                players_stmt = select(Player).where(Player.is_active.is_(True))

            players_result = await db_session.execute(players_stmt)
            players = list(players_result.scalars().all())

            if not players:
                return {
                    "status": "success",
                    "message": "No players found to fix",
                    "players_processed": 0,
                    "successful_fixes": 0,
                    "failed_fixes": 0,
                    "results": [],
                }

            logger.info(f"Fixing schedules for {len(players)} players")

            results = []
            successful_fixes = 0
            failed_fixes = 0

            for player in players:
                try:
                    fix_result = await self.fix_player_schedule(
                        player, db_session, force_recreate
                    )
                    results.append(fix_result)

                    if fix_result["status"] == "success":
                        successful_fixes += 1
                    else:
                        failed_fixes += 1

                except Exception as e:
                    failed_fixes += 1
                    error_result = {
                        "status": "error",
                        "player_id": player.id,
                        "username": player.username,
                        "error": str(e),
                        "message": f"Unexpected error fixing schedule: {str(e)}",
                    }
                    results.append(error_result)
                    logger.error(
                        f"Unexpected error fixing schedule for {player.username}: {e}"
                    )

            return {
                "status": "success",
                "message": f"Bulk fix completed: {successful_fixes} successful, {failed_fixes} failed",
                "players_processed": len(players),
                "successful_fixes": successful_fixes,
                "failed_fixes": failed_fixes,
                "results": results,
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error during bulk schedule fix: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Bulk fix failed: {str(e)}",
                "timestamp": datetime.now(UTC).isoformat(),
            }

    async def cleanup_duplicate_schedules(
        self, db_session: AsyncSession, dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Remove duplicate schedules, keeping only the first occurrence.

        This method checks Redis directly to find duplicates, as get_schedules()
        may deduplicate by schedule_id. It inspects the underlying Redis list
        to detect all occurrences.

        Args:
            db_session: Database session
            dry_run: If True, return what would be done without making changes

        Returns:
            Dict with cleanup results and statistics
        """
        logger.info("Starting cleanup of duplicate schedules")

        try:
            # Get all schedules from Redis using the API (may be deduplicated)
            all_schedules = await self.redis_source.get_schedules()

            # Also check Redis directly to find actual duplicates in the list
            # ListRedisScheduleSource stores schedules in a Redis list at prefix:cron
            import redis.asyncio as redis
            from app.config import settings as config_defaults

            redis_client = redis.from_url(
                config_defaults.redis.url, decode_responses=True
            )

            # Get the prefix used by the schedule source
            prefix = config_defaults.taskiq.scheduler_prefix
            cron_list_key = f"{prefix}:cron"

            # Get all entries from the Redis list (this shows actual duplicates)
            try:
                redis_schedule_ids = await redis_client.lrange(
                    cron_list_key, 0, -1
                )
                await redis_client.close()

                # Count occurrences of each schedule_id in the Redis list
                schedule_id_counts: Dict[str, int] = {}
                for schedule_id in redis_schedule_ids:
                    schedule_id_counts[schedule_id] = (
                        schedule_id_counts.get(schedule_id, 0) + 1
                    )

                # Find duplicates (schedule_ids that appear more than once in Redis)
                redis_duplicates = {
                    schedule_id: count
                    for schedule_id, count in schedule_id_counts.items()
                    if count > 1
                }

                if redis_duplicates:
                    logger.warning(
                        f"Found {len(redis_duplicates)} schedule IDs with duplicates in Redis list: {redis_duplicates}"
                    )
            except Exception as e:
                logger.warning(
                    f"Could not check Redis list directly for duplicates: {e}"
                )
                redis_duplicates = {}

            # Track duplicates from get_schedules() API (may already be deduplicated)
            schedule_ids_seen: Dict[str, List[Any]] = {}
            for schedule in all_schedules:
                schedule_id = schedule.schedule_id
                if schedule_id not in schedule_ids_seen:
                    schedule_ids_seen[schedule_id] = []
                schedule_ids_seen[schedule_id].append(schedule)

            # Find duplicates (schedule_ids that appear more than once)
            duplicate_schedules = {
                schedule_id: occurrences
                for schedule_id, occurrences in schedule_ids_seen.items()
                if len(occurrences) > 1
            }

            # If we found duplicates in Redis but not in get_schedules(), use Redis data
            if redis_duplicates and not duplicate_schedules:
                logger.info(
                    f"Found duplicates in Redis list but not in get_schedules() API. "
                    f"Redis duplicates: {redis_duplicates}"
                )
                # Create duplicate entries based on Redis counts
                for schedule_id, count in redis_duplicates.items():
                    # Find the schedule object for this schedule_id
                    matching_schedule = next(
                        (
                            s
                            for s in all_schedules
                            if s.schedule_id == schedule_id
                        ),
                        None,
                    )
                    if matching_schedule:
                        # Create a list with the schedule repeated 'count' times
                        duplicate_schedules[schedule_id] = [
                            matching_schedule
                        ] * count
                    else:
                        # Schedule not found in get_schedules() - it's orphaned
                        logger.warning(
                            f"Schedule {schedule_id} found in Redis list but not in get_schedules() - orphaned"
                        )
                        # We'll handle this in orphaned cleanup, but log it here
                        duplicate_schedules[schedule_id] = []

            # If we found duplicates in Redis list, we need to clean them up
            # even if get_schedules() doesn't show them
            if redis_duplicates:
                logger.info(
                    f"Found {len(redis_duplicates)} schedule IDs with duplicates in Redis: {redis_duplicates}"
                )
                # Add Redis duplicates to our tracking
                for schedule_id, count in redis_duplicates.items():
                    if schedule_id not in duplicate_schedules:
                        # Find matching schedule or mark as orphaned
                        matching_schedule = next(
                            (
                                s
                                for s in all_schedules
                                if s.schedule_id == schedule_id
                            ),
                            None,
                        )
                        if matching_schedule:
                            duplicate_schedules[schedule_id] = [
                                matching_schedule
                            ] * count
                        else:
                            # Orphaned schedule found in Redis but not in get_schedules()
                            # We still need to clean it up - delete all occurrences from Redis
                            logger.warning(
                                f"Schedule {schedule_id} has {count} duplicates in Redis but not found in get_schedules() - will clean up"
                            )
                            # Mark for cleanup even though we don't have the schedule object
                            # We'll handle this specially in the cleanup loop
                            duplicate_schedules[schedule_id] = []

            if not duplicate_schedules:
                return {
                    "status": "success",
                    "message": "No duplicate schedules found",
                    "schedules_processed": len(all_schedules),
                    "duplicates_found": 0,
                    "duplicates_removed": 0,
                    "duplicate_schedules": {},
                    "redis_duplicates_checked": (
                        len(redis_duplicates) if redis_duplicates else 0
                    ),
                }

            # Remove duplicates (keep first occurrence, remove the rest)
            # Note: delete_schedule removes all occurrences of a schedule_id,
            # so we delete all and then recreate the first one if it's a player schedule
            # But only if the player exists and is active
            removed_count = 0
            removal_errors = []
            duplicate_details = {}
            player_schedules_to_recreate = []

            if not dry_run:
                # First, check which players exist before processing duplicates
                from app.models.player import Player

                all_players_stmt = select(Player.id, Player.is_active).where(
                    Player.is_active.is_(True)
                )
                all_players_result = await db_session.execute(all_players_stmt)
                active_player_ids = {
                    player.id for player in all_players_result.all()
                }

                for schedule_id, occurrences in duplicate_schedules.items():
                    # Handle orphaned schedules found in Redis but not in get_schedules()
                    if not occurrences:
                        # This schedule exists in Redis but not in get_schedules()
                        # We need to delete all occurrences from Redis directly
                        try:
                            # Delete all occurrences of this schedule_id from Redis
                            await self.redis_source.delete_schedule(
                                schedule_id
                            )
                            # Get count from redis_duplicates if available
                            duplicate_count = redis_duplicates.get(
                                schedule_id, 1
                            )
                            removed_count += (
                                duplicate_count  # Count all removed
                            )
                            logger.info(
                                f"Removed {duplicate_count} orphaned duplicate schedule(s) from Redis: {schedule_id}"
                            )
                            duplicate_details[schedule_id] = {
                                "total_occurrences": duplicate_count,
                                "kept": 0,
                                "removed": duplicate_count,
                                "reason": "Orphaned schedule (not in get_schedules())",
                            }
                        except Exception as e:
                            error_msg = f"Failed to remove orphaned duplicate schedule {schedule_id}: {str(e)}"
                            removal_errors.append(error_msg)
                            logger.error(error_msg)
                        continue

                    first_schedule = occurrences[0]
                    total_duplicates = (
                        len(occurrences) - 1
                    )  # Number of duplicates (excluding first)

                    duplicate_details[schedule_id] = {
                        "total_occurrences": len(occurrences),
                        "kept": 1,
                        "removed": total_duplicates,
                    }

                    try:
                        # Check if this is a player schedule and if the player exists
                        should_recreate = False
                        if schedule_id.startswith("player_fetch_"):
                            try:
                                player_id_str = schedule_id.replace(
                                    "player_fetch_", ""
                                )
                                player_id = int(player_id_str)
                                should_recreate = (
                                    player_id in active_player_ids
                                )
                            except ValueError:
                                # Invalid player ID format - don't recreate
                                should_recreate = False

                        # Delete all occurrences (delete_schedule removes all with this schedule_id)
                        await self.redis_source.delete_schedule(schedule_id)
                        removed_count += total_duplicates
                        logger.info(
                            f"Removed {total_duplicates} duplicate(s) for schedule: {schedule_id}"
                        )

                        # Only recreate if player exists and is active
                        if should_recreate:
                            player_schedules_to_recreate.append(schedule_id)
                        elif schedule_id.startswith("player_fetch_"):
                            # Log that we're skipping recreation for non-existent/inactive player
                            try:
                                player_id_str = schedule_id.replace(
                                    "player_fetch_", ""
                                )
                                player_id = int(player_id_str)
                                logger.info(
                                    f"Skipping recreation of duplicate schedule {schedule_id}: "
                                    f"player {player_id} not found or inactive (orphaned schedule)"
                                )
                            except ValueError:
                                logger.info(
                                    f"Skipping recreation of duplicate schedule {schedule_id}: "
                                    "invalid player ID format"
                                )
                    except Exception as e:
                        error_msg = f"Failed to remove duplicate {schedule_id}: {str(e)}"
                        removal_errors.append(error_msg)
                        logger.error(error_msg)

                # Recreate player schedules that were deleted
                # Only recreate if the player exists and is active
                for schedule_id in player_schedules_to_recreate:
                    try:
                        # Extract player_id from schedule_id
                        player_id_str = schedule_id.replace(
                            "player_fetch_", ""
                        )
                        player_id = int(player_id_str)

                        # Get the player from database
                        from app.models.player import Player

                        player_stmt = select(Player).where(
                            Player.id == player_id
                        )
                        player_result = await db_session.execute(player_stmt)
                        player = player_result.scalar_one_or_none()

                        if player and player.is_active:
                            # Recreate the schedule using the schedule manager
                            from app.services.scheduler import (
                                get_player_schedule_manager,
                            )

                            schedule_manager = get_player_schedule_manager()
                            new_schedule_id = (
                                await schedule_manager.ensure_player_scheduled(
                                    player
                                )
                            )
                            logger.info(
                                f"Recreated schedule for player {player_id}: {new_schedule_id}"
                            )
                        else:
                            # Player doesn't exist or is inactive - this is expected for orphaned schedules
                            # The orphaned cleanup should handle these, but we log it here for visibility
                            logger.info(
                                f"Skipping recreation of schedule {schedule_id}: player {player_id} not found or inactive "
                                "(will be cleaned up by orphaned schedule cleanup)"
                            )
                            # Don't treat this as an error - it's expected behavior
                    except ValueError as e:
                        # Invalid player ID format - this schedule should be cleaned up by orphaned cleanup
                        logger.info(
                            f"Skipping recreation of schedule {schedule_id}: invalid player ID format ({str(e)})"
                        )
                    except Exception as e:
                        error_msg = f"Failed to recreate schedule {schedule_id}: {str(e)}"
                        removal_errors.append(error_msg)
                        logger.error(error_msg)

            result = {
                "status": "success",
                "message": f"Cleanup completed: {len(duplicate_schedules)} duplicate schedule IDs found",
                "schedules_processed": len(all_schedules),
                "duplicates_found": len(duplicate_schedules),
                "duplicates_removed": removed_count if not dry_run else 0,
                "duplicate_schedules": duplicate_details,
                "dry_run": dry_run,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            if removal_errors:
                result["removal_errors"] = removal_errors

            return result

        except Exception as e:
            logger.error(f"Error during duplicate schedule cleanup: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Cleanup failed: {str(e)}",
                "timestamp": datetime.now(UTC).isoformat(),
            }


# Dependency injection function for FastAPI
async def get_schedule_maintenance_service() -> ScheduleMaintenanceService:
    """
    Dependency injection function for FastAPI.

    Returns:
        ScheduleMaintenanceService: Configured maintenance service instance
    """
    from app.workers.scheduler import redis_schedule_source

    return ScheduleMaintenanceService(redis_schedule_source)
