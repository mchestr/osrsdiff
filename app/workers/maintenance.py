"""
Background tasks for schedule maintenance and verification.

This module provides TaskIQ tasks for periodic schedule maintenance,
including verification jobs and cleanup operations.
"""

import logging
from datetime import UTC, datetime
from typing import Any, Dict

from app.models.base import AsyncSessionLocal
from app.services.scheduler import (
    ScheduleMaintenanceService,
    get_player_schedule_manager,
)
from app.workers.main import broker

logger = logging.getLogger(__name__)


# Daily schedule maintenance job - runs at 4 AM UTC
@broker.task(
    schedule=[{"cron": "0 4 * * *"}],
    retry_on_error=True,
    max_retries=2,
    delay=30.0,
    task_timeout=1800.0,
)
async def schedule_maintenance_job() -> Dict[str, Any]:
    """
    Comprehensive schedule maintenance job.

    This task performs complete schedule maintenance including:
    - Getting schedule summary and statistics
    - Verifying consistency between database and Redis
    - Cleaning up orphaned schedules (for deleted or inactive players)
    - Removing duplicate schedules (keeping only the first occurrence)
    - Automatically fixing missing or invalid schedules

    Returns:
        Dict containing comprehensive maintenance results
    """
    logger.info("Starting comprehensive schedule maintenance job")
    start_time = datetime.now(UTC)

    async with AsyncSessionLocal() as db_session:
        try:
            # Create maintenance service with direct Redis access
            from app.workers.scheduler import redis_schedule_source

            maintenance_service = ScheduleMaintenanceService(
                redis_schedule_source
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

            # Cleanup orphaned schedules
            orphaned_result = (
                await maintenance_service.cleanup_orphaned_schedules(
                    db_session, dry_run=False
                )
            )

            orphaned_count = len(orphaned_result.get("orphaned_schedules", []))
            orphaned_removed = orphaned_result.get("schedules_removed", 0)

            if orphaned_count > 0:
                logger.info(
                    f"Cleaned up {orphaned_removed} orphaned schedules (found {orphaned_count})"
                )

            # Cleanup duplicate schedules
            duplicate_result = (
                await maintenance_service.cleanup_duplicate_schedules(
                    db_session, dry_run=False
                )
            )

            duplicate_count = duplicate_result.get("duplicates_found", 0)
            duplicate_removed = duplicate_result.get("duplicates_removed", 0)

            if duplicate_count > 0:
                logger.info(
                    f"Cleaned up {duplicate_removed} duplicate schedules (found {duplicate_count})"
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
                and duplicate_count == 0
                and len(fix_errors) == 0
            ):
                overall_status = "healthy"
                message = "All schedules are consistent and healthy"
            elif len(fix_errors) == 0:
                overall_status = "cleaned"
                message = (
                    f"Maintenance completed: removed {orphaned_removed} orphaned schedules, "
                    f"{duplicate_removed} duplicate schedules, fixed {fixed_schedules} missing schedules"
                )
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
                    "orphaned_schedules_removed": orphaned_removed,
                    "duplicates_found": duplicate_count,
                    "duplicates_removed": duplicate_removed,
                },
                "fixes": {
                    "schedules_fixed": fixed_schedules,
                    "fix_errors": fix_errors,
                },
                "orphaned_cleanup": orphaned_result,
                "duplicate_cleanup": duplicate_result,
                "timestamp": datetime.now(UTC).isoformat(),
                "duration_seconds": duration,
            }

            # Check for errors in cleanup operations
            if orphaned_result.get("status") != "success":
                result["status"] = "partial_success"
                result["orphaned_error"] = orphaned_result.get("error")
                logger.warning(
                    f"Orphaned schedule cleanup had errors: {orphaned_result.get('error')}"
                )

            if duplicate_result.get("status") != "success":
                result["status"] = "partial_success"
                result["duplicate_error"] = duplicate_result.get("error")
                logger.warning(
                    f"Duplicate schedule cleanup had errors: {duplicate_result.get('error')}"
                )

            if overall_status == "issues_remain":
                logger.warning(
                    f"Schedule maintenance completed with remaining issues: {len(fix_errors)} errors"
                )
            else:
                logger.info(
                    f"Schedule maintenance completed successfully ({overall_status})"
                )

            return result

        except Exception as e:
            duration = (datetime.now(UTC) - start_time).total_seconds()
            logger.error(f"Fatal error during schedule maintenance: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Schedule maintenance failed: {str(e)}",
                "timestamp": datetime.now(UTC).isoformat(),
                "duration_seconds": duration,
            }
