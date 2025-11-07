"""
Background tasks for schedule maintenance and verification.

This module provides TaskIQ tasks for periodic schedule maintenance,
including verification jobs and cleanup operations.
"""

import logging
from datetime import UTC, datetime
from typing import Any, Dict

from app.models.base import AsyncSessionLocal
from app.services.schedule_maintenance import ScheduleMaintenanceService
from app.services.scheduler import get_player_schedule_manager
from app.workers.main import broker, get_task_defaults

logger = logging.getLogger(__name__)


# Daily schedule verification job - runs at 3 AM UTC
@broker.task(
    schedule=[{"cron": "0 3 * * *"}],  # Daily at 3 AM UTC
    **get_task_defaults(
        retry_count=2,
        retry_delay=30.0,
        task_timeout=1800.0,  # 30 minutes for verification job
    ),
)
async def schedule_verification_job() -> Dict[str, Any]:
    """
    Periodic job to verify schedule consistency between database and Redis.

    This task runs periodically to ensure that all active players have valid
    schedules and that there are no orphaned schedules in Redis. It performs
    automatic cleanup and fixes where possible.

    Returns:
        Dict containing verification results and any actions taken
    """
    logger.info("Starting periodic schedule verification job")
    start_time = datetime.now(UTC)

    async with AsyncSessionLocal() as db_session:
        try:
            # Create maintenance service
            maintenance_service = ScheduleMaintenanceService(
                get_player_schedule_manager()
            )

            # Get schedule summary
            summary_result = await maintenance_service.get_schedule_summary(
                db_session
            )

            if summary_result["status"] != "success":
                logger.error(
                    f"Failed to get schedule summary: {summary_result.get('error')}"
                )
                return {
                    "status": "error",
                    "error": "Failed to get schedule summary",
                    "details": summary_result,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "duration_seconds": (
                        datetime.now(UTC) - start_time
                    ).total_seconds(),
                }

            summary = summary_result["summary"]
            logger.info(
                f"Schedule summary: {summary['active_players']} active players, "
                f"{summary['scheduled_players']} scheduled, "
                f"{summary['redis_schedules']} Redis schedules"
            )

            # Verify consistency
            consistency_result = (
                await maintenance_service.verify_schedule_consistency(
                    db_session
                )
            )

            if consistency_result["status"] != "success":
                logger.error(
                    f"Schedule consistency verification failed: {consistency_result.get('error')}"
                )
                return {
                    "status": "error",
                    "error": "Consistency verification failed",
                    "details": consistency_result,
                    "summary": summary,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "duration_seconds": (
                        datetime.now(UTC) - start_time
                    ).total_seconds(),
                }

            inconsistencies = consistency_result.get("inconsistencies", [])
            inconsistency_counts = consistency_result.get(
                "inconsistency_types", {}
            )

            # Log inconsistencies found
            if inconsistencies:
                logger.warning(
                    f"Found {len(inconsistencies)} schedule inconsistencies:"
                )
                for inconsistency_type, count in inconsistency_counts.items():
                    logger.warning(f"  {inconsistency_type}: {count}")
            else:
                logger.info("No schedule inconsistencies found")

            # Perform automatic cleanup of orphaned schedules
            cleanup_result = (
                await maintenance_service.cleanup_orphaned_schedules(
                    db_session, dry_run=False
                )
            )

            orphaned_count = len(cleanup_result.get("orphaned_schedules", []))
            removed_count = cleanup_result.get("schedules_removed", 0)

            if orphaned_count > 0:
                logger.info(
                    f"Cleaned up {removed_count} orphaned schedules (found {orphaned_count})"
                )

            # Attempt to fix players with missing schedules
            missing_schedule_inconsistencies = [
                inc
                for inc in inconsistencies
                if inc["type"]
                in ["null_schedule_id", "missing_redis_schedule"]
            ]

            fixed_schedules = 0
            fix_errors = []

            if missing_schedule_inconsistencies:
                logger.info(
                    f"Attempting to fix {len(missing_schedule_inconsistencies)} missing schedules"
                )

                for inconsistency in missing_schedule_inconsistencies:
                    if "player_id" in inconsistency:
                        try:
                            # Get the player and fix their schedule
                            from sqlalchemy import select

                            from app.models.player import Player

                            player_stmt = select(Player).where(
                                Player.id == inconsistency["player_id"]
                            )
                            player_result = await db_session.execute(
                                player_stmt
                            )
                            player = player_result.scalar_one_or_none()

                            if player and player.is_active:
                                fix_result = await maintenance_service.fix_player_schedule(
                                    player, db_session, force_recreate=False
                                )

                                if fix_result["status"] == "success":
                                    fixed_schedules += 1
                                    logger.info(
                                        f"Fixed schedule for {player.username}: {fix_result['new_schedule_id']}"
                                    )
                                else:
                                    fix_errors.append(
                                        f"{player.username}: {fix_result.get('error', 'Unknown error')}"
                                    )

                        except Exception as e:
                            fix_errors.append(
                                f"Player ID {inconsistency['player_id']}: {str(e)}"
                            )
                            logger.error(
                                f"Error fixing schedule for player ID {inconsistency['player_id']}: {e}"
                            )

            if fixed_schedules > 0:
                logger.info(
                    f"Automatically fixed {fixed_schedules} player schedules"
                )

            # Calculate final statistics
            duration = (datetime.now(UTC) - start_time).total_seconds()

            # Determine overall status
            if (
                consistency_result["is_consistent"]
                and orphaned_count == 0
                and len(fix_errors) == 0
            ):
                overall_status = "healthy"
                message = "All schedules are consistent and healthy"
            elif len(fix_errors) == 0:
                overall_status = "cleaned"
                message = f"Cleaned up {removed_count} orphaned schedules, fixed {fixed_schedules} missing schedules"
            else:
                overall_status = "issues_remain"
                message = f"Some issues remain: {len(fix_errors)} schedules could not be fixed"

            result = {
                "status": overall_status,
                "message": message,
                "summary": summary,
                "verification": {
                    "is_consistent": consistency_result["is_consistent"],
                    "inconsistencies_found": len(inconsistencies),
                    "inconsistency_types": inconsistency_counts,
                },
                "cleanup": {
                    "orphaned_schedules_found": orphaned_count,
                    "orphaned_schedules_removed": removed_count,
                },
                "fixes": {
                    "schedules_fixed": fixed_schedules,
                    "fix_errors": fix_errors,
                },
                "timestamp": datetime.now(UTC).isoformat(),
                "duration_seconds": duration,
            }

            if overall_status == "issues_remain":
                logger.warning(
                    f"Schedule verification completed with remaining issues: {len(fix_errors)} errors"
                )
            else:
                logger.info(
                    f"Schedule verification completed successfully ({overall_status})"
                )

            return result

        except Exception as e:
            duration = (datetime.now(UTC) - start_time).total_seconds()
            logger.error(f"Fatal error during schedule verification job: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Schedule verification job failed: {str(e)}",
                "timestamp": datetime.now(UTC).isoformat(),
                "duration_seconds": duration,
            }


# Manual cleanup job (no schedule - triggered manually)
@broker.task(
    **get_task_defaults(
        retry_count=2,
        retry_delay=15.0,
        task_timeout=600.0,  # 10 minutes for cleanup
    )
)
async def cleanup_orphaned_schedules_job() -> Dict[str, Any]:
    """
    Background job to clean up orphaned schedules.

    This task can be run manually or scheduled to remove schedules for
    players that no longer exist or are inactive.

    Returns:
        Dict containing cleanup results
    """
    logger.info("Starting orphaned schedule cleanup job")
    start_time = datetime.now(UTC)

    async with AsyncSessionLocal() as db_session:
        try:
            # Create maintenance service
            maintenance_service = ScheduleMaintenanceService(
                get_player_schedule_manager()
            )

            # Perform cleanup
            cleanup_result = (
                await maintenance_service.cleanup_orphaned_schedules(
                    db_session, dry_run=False
                )
            )

            if cleanup_result["status"] != "success":
                logger.error(
                    f"Orphaned schedule cleanup failed: {cleanup_result.get('error')}"
                )
                return cleanup_result

            orphaned_count = len(cleanup_result.get("orphaned_schedules", []))
            removed_count = cleanup_result.get("schedules_removed", 0)

            duration = (datetime.now(UTC) - start_time).total_seconds()

            if orphaned_count > 0:
                logger.info(
                    f"Cleanup completed: removed {removed_count} orphaned schedules"
                )
            else:
                logger.info("Cleanup completed: no orphaned schedules found")

            # Add duration to result
            cleanup_result["duration_seconds"] = duration

            return cleanup_result

        except Exception as e:
            duration = (datetime.now(UTC) - start_time).total_seconds()
            logger.error(f"Fatal error during orphaned schedule cleanup: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Orphaned schedule cleanup failed: {str(e)}",
                "timestamp": datetime.now(UTC).isoformat(),
                "duration_seconds": duration,
            }
