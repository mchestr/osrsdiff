import logging
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.player import Player
from app.services.scheduler import PlayerScheduleManager

logger = logging.getLogger(__name__)


class ScheduleMaintenanceService:
    """
    Service for performing schedule maintenance operations.

    This service provides methods for cleaning up orphaned schedules,
    verifying consistency, and performing bulk operations on player schedules.
    """

    def __init__(self, schedule_manager: PlayerScheduleManager):
        """
        Initialize the maintenance service.

        Args:
            schedule_manager: PlayerScheduleManager instance
        """
        self.schedule_manager = schedule_manager

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
            # Get all schedules from Redis
            all_schedules = (
                await self.schedule_manager.redis_source.get_schedules()
            )
            player_schedules = [
                s
                for s in all_schedules
                if hasattr(s, "schedule_id")
                and s.schedule_id.startswith("player_fetch_")
            ]

            if not player_schedules:
                return {
                    "status": "success",
                    "message": "No player schedules found",
                    "schedules_processed": 0,
                    "schedules_removed": 0,
                    "orphaned_schedules": [],
                }

            # Get all active players with their schedule_ids
            active_players_stmt = select(
                Player.id, Player.username, Player.schedule_id
            ).where(Player.is_active.is_(True))
            active_players_result = await db_session.execute(
                active_players_stmt
            )
            active_players = active_players_result.all()

            # Create sets for efficient lookup
            active_player_ids = {str(player.id) for player in active_players}
            active_schedule_ids = {
                player.schedule_id
                for player in active_players
                if player.schedule_id is not None
            }

            # Find orphaned schedules
            orphaned_schedules = []

            for schedule in player_schedules:
                try:
                    schedule_id = schedule.schedule_id

                    # Extract player ID from schedule ID
                    if not schedule_id.startswith("player_fetch_"):
                        continue

                    try:
                        player_id_str = schedule_id.replace(
                            "player_fetch_", ""
                        )
                        player_id = int(player_id_str)
                    except ValueError:
                        orphaned_schedules.append(
                            {
                                "schedule_id": schedule_id,
                                "reason": "Invalid player ID format",
                                "player_id": None,
                            }
                        )
                        continue

                    # Check if player exists and is active
                    if str(player_id) not in active_player_ids:
                        orphaned_schedules.append(
                            {
                                "schedule_id": schedule_id,
                                "reason": "Player not found or inactive",
                                "player_id": str(player_id),
                            }
                        )
                    elif schedule_id not in active_schedule_ids:
                        orphaned_schedules.append(
                            {
                                "schedule_id": schedule_id,
                                "reason": "Schedule not referenced in database",
                                "player_id": str(player_id),
                            }
                        )

                except Exception as e:
                    logger.error(
                        f"Error processing schedule {getattr(schedule, 'schedule_id', 'unknown')}: {e}"
                    )
                    orphaned_schedules.append(
                        {
                            "schedule_id": getattr(
                                schedule, "schedule_id", "unknown"
                            ),
                            "reason": f"Processing error: {str(e)}",
                            "player_id": None,
                        }
                    )

            # Remove orphaned schedules if not dry run
            removed_count = 0
            removal_errors = []

            if not dry_run:
                for orphan in orphaned_schedules:
                    try:
                        schedule_id_value = orphan.get("schedule_id")
                        if (
                            schedule_id_value is not None
                            and schedule_id_value != "unknown"
                        ):
                            await self.schedule_manager.redis_source.delete_schedule(
                                str(schedule_id_value)
                            )
                        removed_count += 1
                        logger.info(
                            f"Removed orphaned schedule: {orphan['schedule_id']} ({orphan['reason']})"
                        )
                    except Exception as e:
                        error_msg = f"Failed to remove {orphan['schedule_id']}: {str(e)}"
                        removal_errors.append(error_msg)
                        logger.error(error_msg)

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
            # Get all schedules from Redis
            all_schedules = (
                await self.schedule_manager.redis_source.get_schedules()
            )
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

                    # Verify schedule configuration
                    is_valid = await self.schedule_manager._verify_schedule_exists_and_valid(
                        player
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
            all_schedules = (
                await self.schedule_manager.redis_source.get_schedules()
            )
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
                        await self.schedule_manager.redis_source.delete_schedule(
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

            # Ensure player has a valid schedule
            new_schedule_id = (
                await self.schedule_manager.ensure_player_scheduled(player)
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

        Args:
            db_session: Database session
            dry_run: If True, return what would be done without making changes

        Returns:
            Dict with cleanup results and statistics
        """
        logger.info("Starting cleanup of duplicate schedules")

        try:
            # Get all schedules from Redis
            all_schedules = (
                await self.schedule_manager.redis_source.get_schedules()
            )

            # Track duplicates - collect all occurrences of each schedule_id
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

            if not duplicate_schedules:
                return {
                    "status": "success",
                    "message": "No duplicate schedules found",
                    "schedules_processed": len(all_schedules),
                    "duplicates_found": 0,
                    "duplicates_removed": 0,
                    "duplicate_schedules": {},
                }

            # Remove duplicates (keep first occurrence, remove the rest)
            # Note: delete_schedule removes all occurrences of a schedule_id,
            # so we delete all and then recreate the first one if it's a player schedule
            removed_count = 0
            removal_errors = []
            duplicate_details = {}
            player_schedules_to_recreate = []

            if not dry_run:
                for schedule_id, occurrences in duplicate_schedules.items():
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
                        # Delete all occurrences (delete_schedule removes all with this schedule_id)
                        await self.schedule_manager.redis_source.delete_schedule(
                            schedule_id
                        )
                        removed_count += total_duplicates
                        logger.info(
                            f"Removed {total_duplicates} duplicate(s) for schedule: {schedule_id}"
                        )

                        # If this is a player schedule, we need to recreate it from the database
                        if schedule_id.startswith("player_fetch_"):
                            player_schedules_to_recreate.append(schedule_id)
                    except Exception as e:
                        error_msg = f"Failed to remove duplicate {schedule_id}: {str(e)}"
                        removal_errors.append(error_msg)
                        logger.error(error_msg)

                # Recreate player schedules that were deleted
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
                            new_schedule_id = await self.schedule_manager.ensure_player_scheduled(
                                player
                            )
                            logger.info(
                                f"Recreated schedule for player {player_id}: {new_schedule_id}"
                            )
                        else:
                            logger.warning(
                                f"Could not recreate schedule {schedule_id}: player {player_id} not found or inactive"
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
async def get_schedule_maintenance_service(
    schedule_manager: PlayerScheduleManager,
) -> ScheduleMaintenanceService:
    """
    Dependency injection function for FastAPI.

    Args:
        schedule_manager: PlayerScheduleManager instance

    Returns:
        ScheduleMaintenanceService: Configured maintenance service instance
    """
    return ScheduleMaintenanceService(schedule_manager)
