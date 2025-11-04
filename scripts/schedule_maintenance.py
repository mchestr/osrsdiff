#!/usr/bin/env python3
"""
Schedule maintenance utilities for TaskIQ scheduler.

This script provides utilities for cleaning up orphaned schedules, verifying
schedule consistency between database and Redis, and performing bulk operations
on player schedules.

Usage:
    python scripts/schedule_maintenance.py <command> [options]

Commands:
    cleanup-orphaned    Remove schedules for deleted/inactive players
    verify-consistency  Check DB/Redis schedule consistency
    bulk-reschedule     Reschedule all players (useful after interval changes)
    list-schedules      List all player schedules with status
    remove-schedule     Remove a specific schedule by ID
    recreate-schedule   Recreate a specific player's schedule

Options:
    --dry-run          Show what would be done without making changes
    --player-id        Specific player ID for single-player operations
    --schedule-id      Specific schedule ID for schedule operations
    --batch-size       Number of items to process in each batch (default: 50)
    --force            Force operations without confirmation prompts
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime, UTC
from typing import Dict, List, Optional, Any, Set

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

# Add src to path for imports
sys.path.insert(0, "src")

from src.models.base import AsyncSessionLocal, init_db
from src.models.player import Player
from src.services.scheduler import PlayerScheduleManager
from src.workers.main import redis_schedule_source

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            f"schedule_maintenance_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.log"
        ),
    ],
)

logger = logging.getLogger(__name__)


class MaintenanceError(Exception):
    """Base exception for maintenance errors."""

    pass


class MaintenanceStats:
    """Track maintenance operation statistics."""

    def __init__(self, operation: str):
        self.operation = operation
        self.start_time = datetime.now(UTC)
        self.processed_items = 0
        self.successful_operations = 0
        self.failed_operations = 0
        self.skipped_items = 0
        self.errors: List[Dict[str, Any]] = []

    def add_success(self, item_id: str, message: str = ""):
        """Record a successful operation."""
        self.successful_operations += 1
        self.processed_items += 1
        logger.info(f"✓ {item_id}: {message}")

    def add_failure(self, item_id: str, error: str):
        """Record a failed operation."""
        self.failed_operations += 1
        self.processed_items += 1
        error_info = {
            "item_id": item_id,
            "error": error,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self.errors.append(error_info)
        logger.error(f"✗ {item_id}: {error}")

    def add_skip(self, item_id: str, reason: str):
        """Record a skipped item."""
        self.skipped_items += 1
        self.processed_items += 1
        logger.info(f"⊘ {item_id}: {reason}")

    def get_summary(self) -> Dict[str, Any]:
        """Get operation summary statistics."""
        duration = (datetime.now(UTC) - self.start_time).total_seconds()

        return {
            "operation": self.operation,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now(UTC).isoformat(),
            "duration_seconds": duration,
            "processed_items": self.processed_items,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "skipped_items": self.skipped_items,
            "success_rate": (
                self.successful_operations / max(1, self.processed_items) * 100
            ),
            "errors": self.errors,
        }

    def print_summary(self):
        """Print a formatted summary of the operation."""
        summary = self.get_summary()

        print("\n" + "=" * 60)
        print(f"MAINTENANCE SUMMARY: {summary['operation'].upper()}")
        print("=" * 60)
        print(f"Duration: {summary['duration_seconds']:.2f} seconds")
        print(f"Processed: {summary['processed_items']}")
        print(f"✓ Successful: {summary['successful_operations']}")
        print(f"⊘ Skipped: {summary['skipped_items']}")
        print(f"✗ Failed: {summary['failed_operations']}")
        print(f"Success rate: {summary['success_rate']:.1f}%")

        if self.errors:
            print(f"\nERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error['item_id']}: {error['error']}")

        print("=" * 60)


async def get_all_redis_schedules(
    schedule_manager: PlayerScheduleManager,
) -> List[Any]:
    """Get all schedules from Redis."""
    try:
        schedules = await schedule_manager.redis_source.get_schedules()
        return list(schedules)
    except Exception as e:
        logger.error(f"Failed to get schedules from Redis: {e}")
        return []


async def get_player_fetch_schedules(schedules: List[Any]) -> List[Any]:
    """Filter schedules to only player fetch schedules."""
    player_schedules = []
    for schedule in schedules:
        if hasattr(
            schedule, "schedule_id"
        ) and schedule.schedule_id.startswith("player_fetch_"):
            player_schedules.append(schedule)
    return player_schedules


async def cleanup_orphaned_schedules(
    dry_run: bool = False, batch_size: int = 50
) -> MaintenanceStats:
    """
    Remove schedules for deleted or inactive players.

    This function identifies schedules in Redis that correspond to players
    that no longer exist or are inactive, and removes them to prevent
    unnecessary task execution.

    Args:
        dry_run: If True, show what would be done without making changes
        batch_size: Number of schedules to process in each batch

    Returns:
        MaintenanceStats with cleanup results
    """
    stats = MaintenanceStats("cleanup-orphaned")

    logger.info("Starting cleanup of orphaned schedules")
    if dry_run:
        logger.info("DRY RUN MODE - No changes will be made")

    # Initialize database and schedule manager
    await init_db()
    schedule_manager = PlayerScheduleManager(redis_schedule_source)

    async with AsyncSessionLocal() as db_session:
        try:
            # Get all schedules from Redis
            all_schedules = await get_all_redis_schedules(schedule_manager)
            player_schedules = await get_player_fetch_schedules(all_schedules)

            logger.info(
                f"Found {len(player_schedules)} player fetch schedules in Redis"
            )

            if not player_schedules:
                logger.info("No player schedules found - cleanup complete")
                return stats

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

            logger.info(
                f"Found {len(active_players)} active players in database"
            )

            # Process schedules in batches
            orphaned_schedules = []

            for schedule in player_schedules:
                try:
                    schedule_id = schedule.schedule_id

                    # Extract player ID from schedule ID (format: player_fetch_{player_id})
                    if not schedule_id.startswith("player_fetch_"):
                        stats.add_skip(
                            schedule_id, "Not a player fetch schedule"
                        )
                        continue

                    try:
                        player_id_str = schedule_id.replace(
                            "player_fetch_", ""
                        )
                        player_id = int(player_id_str)
                    except ValueError:
                        stats.add_failure(
                            schedule_id,
                            "Invalid player ID format in schedule_id",
                        )
                        continue

                    # Check if player exists and is active
                    if str(player_id) not in active_player_ids:
                        # Player doesn't exist or is inactive - schedule is orphaned
                        orphaned_schedules.append(
                            {
                                "schedule": schedule,
                                "schedule_id": schedule_id,
                                "player_id": player_id,
                                "reason": "Player not found or inactive",
                            }
                        )
                    elif schedule_id not in active_schedule_ids:
                        # Player exists but doesn't have this schedule_id in database
                        orphaned_schedules.append(
                            {
                                "schedule": schedule,
                                "schedule_id": schedule_id,
                                "player_id": player_id,
                                "reason": "Schedule not referenced in database",
                            }
                        )
                    else:
                        stats.add_skip(
                            schedule_id, "Schedule is valid and active"
                        )

                except Exception as e:
                    stats.add_failure(
                        getattr(schedule, "schedule_id", "unknown"),
                        f"Error processing schedule: {str(e)}",
                    )

            logger.info(f"Found {len(orphaned_schedules)} orphaned schedules")

            # Remove orphaned schedules
            for orphan_info in orphaned_schedules:
                schedule_id = orphan_info["schedule_id"]
                reason = orphan_info["reason"]

                try:
                    if dry_run:
                        stats.add_success(
                            schedule_id, f"Would remove: {reason}"
                        )
                    else:
                        await schedule_manager.redis_source.delete_schedule(
                            schedule_id
                        )
                        stats.add_success(
                            schedule_id, f"Removed orphaned schedule: {reason}"
                        )

                except Exception as e:
                    stats.add_failure(
                        schedule_id, f"Failed to remove schedule: {str(e)}"
                    )

        except Exception as e:
            logger.error(f"Fatal error during orphaned schedule cleanup: {e}")
            raise MaintenanceError(f"Cleanup failed: {str(e)}") from e

    logger.info("Orphaned schedule cleanup completed")
    return stats


async def verify_schedule_consistency(
    batch_size: int = 50,
) -> MaintenanceStats:
    """
    Verify consistency between database and Redis schedules.

    This function checks that all active players with schedule_ids have
    corresponding schedules in Redis, and that all player schedules in
    Redis correspond to active players in the database.

    Args:
        batch_size: Number of players to process in each batch

    Returns:
        MaintenanceStats with verification results
    """
    stats = MaintenanceStats("verify-consistency")

    logger.info("Starting schedule consistency verification")

    # Initialize database and schedule manager
    await init_db()
    schedule_manager = PlayerScheduleManager(redis_schedule_source)

    async with AsyncSessionLocal() as db_session:
        try:
            # Get all schedules from Redis
            all_schedules = await get_all_redis_schedules(schedule_manager)
            player_schedules = await get_player_fetch_schedules(all_schedules)

            # Create lookup for Redis schedules
            redis_schedule_ids = {
                schedule.schedule_id for schedule in player_schedules
            }

            logger.info(
                f"Found {len(player_schedules)} player schedules in Redis"
            )

            # Get all active players with schedule_ids
            active_players_stmt = select(Player).where(
                Player.is_active.is_(True), Player.schedule_id.is_not(None)
            )
            active_players_result = await db_session.execute(
                active_players_stmt
            )
            active_players = list(active_players_result.scalars().all())

            logger.info(
                f"Found {len(active_players)} active players with schedule_ids in database"
            )

            # Check each player's schedule
            for player in active_players:
                player_key = f"{player.username} (ID: {player.id})"

                try:
                    if not player.schedule_id:
                        stats.add_failure(
                            player_key, "Player has null schedule_id"
                        )
                        continue

                    # Check if schedule exists in Redis
                    if player.schedule_id not in redis_schedule_ids:
                        stats.add_failure(
                            player_key,
                            f"Schedule {player.schedule_id} not found in Redis",
                        )
                        continue

                    # Verify schedule configuration
                    verification = await schedule_manager._verify_schedule_exists_and_valid(
                        player
                    )

                    if verification:
                        stats.add_success(
                            player_key,
                            f"Schedule {player.schedule_id} is valid",
                        )
                    else:
                        stats.add_failure(
                            player_key,
                            f"Schedule {player.schedule_id} is invalid or misconfigured",
                        )

                except Exception as e:
                    stats.add_failure(
                        player_key, f"Error verifying schedule: {str(e)}"
                    )

            # Check for schedules in Redis without corresponding active players
            active_player_ids = {player.id for player in active_players}

            for schedule in player_schedules:
                try:
                    schedule_id = schedule.schedule_id

                    # Extract player ID from schedule
                    if schedule_id.startswith("player_fetch_"):
                        try:
                            player_id_str = schedule_id.replace(
                                "player_fetch_", ""
                            )
                            player_id = int(player_id_str)

                            if player_id not in active_player_ids:
                                stats.add_failure(
                                    f"Schedule {schedule_id}",
                                    f"No active player found for player_id {player_id}",
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
                                    stats.add_failure(
                                        f"Schedule {schedule_id}",
                                        f"Player {player_id} has different schedule_id: {corresponding_player.schedule_id}",
                                    )

                        except ValueError:
                            stats.add_failure(
                                f"Schedule {schedule_id}",
                                "Invalid player ID format in schedule_id",
                            )

                except Exception as e:
                    stats.add_failure(
                        f"Schedule {getattr(schedule, 'schedule_id', 'unknown')}",
                        f"Error checking schedule: {str(e)}",
                    )

        except Exception as e:
            logger.error(f"Fatal error during consistency verification: {e}")
            raise MaintenanceError(f"Verification failed: {str(e)}") from e

    logger.info("Schedule consistency verification completed")
    return stats


async def bulk_reschedule_players(
    dry_run: bool = False, batch_size: int = 50
) -> MaintenanceStats:
    """
    Reschedule all active players.

    This function recreates schedules for all active players, which is useful
    after making changes to scheduling logic or intervals.

    Args:
        dry_run: If True, show what would be done without making changes
        batch_size: Number of players to process in each batch

    Returns:
        MaintenanceStats with reschedule results
    """
    stats = MaintenanceStats("bulk-reschedule")

    logger.info("Starting bulk reschedule of all active players")
    if dry_run:
        logger.info("DRY RUN MODE - No changes will be made")

    # Initialize database and schedule manager
    await init_db()
    schedule_manager = PlayerScheduleManager(redis_schedule_source)

    async with AsyncSessionLocal() as db_session:
        try:
            # Get all active players
            active_players_stmt = select(Player).where(
                Player.is_active.is_(True)
            )
            active_players_result = await db_session.execute(
                active_players_stmt
            )
            active_players = list(active_players_result.scalars().all())

            logger.info(
                f"Found {len(active_players)} active players to reschedule"
            )

            if not active_players:
                logger.info("No active players found - reschedule complete")
                return stats

            # Process players in batches
            for i in range(0, len(active_players), batch_size):
                batch = active_players[i : i + batch_size]

                logger.info(
                    f"Processing batch {i//batch_size + 1}: {len(batch)} players"
                )

                for player in batch:
                    player_key = f"{player.username} (ID: {player.id})"

                    try:
                        if dry_run:
                            stats.add_success(
                                player_key,
                                f"Would reschedule with {player.fetch_interval_minutes}min interval",
                            )
                        else:
                            # Reschedule the player
                            new_schedule_id = (
                                await schedule_manager.reschedule_player(
                                    player
                                )
                            )

                            # Update database
                            player.schedule_id = new_schedule_id
                            await db_session.commit()

                            stats.add_success(
                                player_key, f"Rescheduled to {new_schedule_id}"
                            )

                    except Exception as e:
                        await db_session.rollback()
                        stats.add_failure(
                            player_key, f"Failed to reschedule: {str(e)}"
                        )

                # Small delay between batches
                await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"Fatal error during bulk reschedule: {e}")
            raise MaintenanceError(f"Bulk reschedule failed: {str(e)}") from e

    logger.info("Bulk reschedule completed")
    return stats


async def list_all_schedules() -> Dict[str, Any]:
    """
    List all player schedules with their status.

    Returns:
        Dict with schedule information
    """
    logger.info("Listing all player schedules")

    # Initialize database and schedule manager
    await init_db()
    schedule_manager = PlayerScheduleManager(redis_schedule_source)

    async with AsyncSessionLocal() as db_session:
        try:
            # Get all schedules from Redis
            all_schedules = await get_all_redis_schedules(schedule_manager)
            player_schedules = await get_player_fetch_schedules(all_schedules)

            # Get all players (active and inactive)
            all_players_stmt = select(Player)
            all_players_result = await db_session.execute(all_players_stmt)
            all_players = list(all_players_result.scalars().all())

            # Create player lookup
            players_by_id = {player.id: player for player in all_players}

            schedule_info = []

            # Process Redis schedules
            for schedule in player_schedules:
                try:
                    schedule_id = schedule.schedule_id

                    # Extract player ID
                    if schedule_id.startswith("player_fetch_"):
                        player_id_str = schedule_id.replace(
                            "player_fetch_", ""
                        )
                        try:
                            player_id = int(player_id_str)
                        except ValueError:
                            schedule_info.append(
                                {
                                    "schedule_id": schedule_id,
                                    "status": "invalid",
                                    "error": "Invalid player ID format",
                                    "player_id": None,
                                    "username": None,
                                    "is_active": None,
                                    "fetch_interval": None,
                                    "cron": getattr(
                                        schedule, "cron", "unknown"
                                    ),
                                }
                            )
                            continue

                        # Get player info
                        player = players_by_id.get(player_id)

                        if player:
                            # Check if schedule_id matches
                            db_schedule_matches = (
                                player.schedule_id == schedule_id
                            )

                            status = (
                                "valid"
                                if db_schedule_matches and player.is_active
                                else "orphaned"
                            )
                            if not player.is_active:
                                status = "inactive_player"
                            elif not db_schedule_matches:
                                status = "db_mismatch"

                            schedule_info.append(
                                {
                                    "schedule_id": schedule_id,
                                    "status": status,
                                    "player_id": player.id,
                                    "username": player.username,
                                    "is_active": player.is_active,
                                    "fetch_interval": player.fetch_interval_minutes,
                                    "db_schedule_id": player.schedule_id,
                                    "cron": getattr(
                                        schedule, "cron", "unknown"
                                    ),
                                }
                            )
                        else:
                            schedule_info.append(
                                {
                                    "schedule_id": schedule_id,
                                    "status": "no_player",
                                    "player_id": player_id,
                                    "username": None,
                                    "is_active": None,
                                    "fetch_interval": None,
                                    "cron": getattr(
                                        schedule, "cron", "unknown"
                                    ),
                                }
                            )

                except Exception as e:
                    schedule_info.append(
                        {
                            "schedule_id": getattr(
                                schedule, "schedule_id", "unknown"
                            ),
                            "status": "error",
                            "error": str(e),
                            "player_id": None,
                            "username": None,
                            "is_active": None,
                            "fetch_interval": None,
                            "cron": getattr(schedule, "cron", "unknown"),
                        }
                    )

            # Check for players with schedule_ids but no Redis schedule
            for player in all_players:
                if player.schedule_id and player.is_active:
                    # Check if this schedule exists in our Redis list
                    redis_schedule_exists = any(
                        s["schedule_id"] == player.schedule_id
                        for s in schedule_info
                    )

                    if not redis_schedule_exists:
                        schedule_info.append(
                            {
                                "schedule_id": player.schedule_id,
                                "status": "missing_redis",
                                "player_id": player.id,
                                "username": player.username,
                                "is_active": player.is_active,
                                "fetch_interval": player.fetch_interval_minutes,
                                "cron": "missing",
                            }
                        )

            # Sort by status and then by player_id
            schedule_info.sort(
                key=lambda x: (x["status"], x["player_id"] or 0)
            )

            # Create summary
            status_counts = {}
            for info in schedule_info:
                status = info["status"]
                status_counts[status] = status_counts.get(status, 0) + 1

            return {
                "total_schedules": len(schedule_info),
                "status_counts": status_counts,
                "schedules": schedule_info,
            }

        except Exception as e:
            logger.error(f"Error listing schedules: {e}")
            return {"error": str(e)}


async def remove_specific_schedule(
    schedule_id: str, dry_run: bool = False
) -> Dict[str, Any]:
    """
    Remove a specific schedule by ID.

    Args:
        schedule_id: Schedule ID to remove
        dry_run: If True, show what would be done without making changes

    Returns:
        Dict with removal results
    """
    logger.info(f"Removing schedule: {schedule_id}")
    if dry_run:
        logger.info("DRY RUN MODE - No changes will be made")

    # Initialize schedule manager
    await init_db()
    schedule_manager = PlayerScheduleManager(redis_schedule_source)

    try:
        if dry_run:
            # Just check if schedule exists
            all_schedules = await get_all_redis_schedules(schedule_manager)
            schedule_exists = any(
                getattr(s, "schedule_id", None) == schedule_id
                for s in all_schedules
            )

            if schedule_exists:
                return {
                    "status": "would_remove",
                    "schedule_id": schedule_id,
                    "message": f"Would remove schedule {schedule_id}",
                }
            else:
                return {
                    "status": "not_found",
                    "schedule_id": schedule_id,
                    "message": f"Schedule {schedule_id} not found in Redis",
                }
        else:
            # Actually remove the schedule
            await schedule_manager.redis_source.delete_schedule(schedule_id)

            return {
                "status": "removed",
                "schedule_id": schedule_id,
                "message": f"Successfully removed schedule {schedule_id}",
            }

    except Exception as e:
        return {
            "status": "error",
            "schedule_id": schedule_id,
            "error": str(e),
            "message": f"Failed to remove schedule {schedule_id}: {str(e)}",
        }


async def recreate_player_schedule(
    player_id: int, dry_run: bool = False
) -> Dict[str, Any]:
    """
    Recreate a specific player's schedule.

    Args:
        player_id: Player ID to recreate schedule for
        dry_run: If True, show what would be done without making changes

    Returns:
        Dict with recreation results
    """
    logger.info(f"Recreating schedule for player ID: {player_id}")
    if dry_run:
        logger.info("DRY RUN MODE - No changes will be made")

    # Initialize database and schedule manager
    await init_db()
    schedule_manager = PlayerScheduleManager(redis_schedule_source)

    async with AsyncSessionLocal() as db_session:
        try:
            # Get the player
            player_stmt = select(Player).where(Player.id == player_id)
            player_result = await db_session.execute(player_stmt)
            player = player_result.scalar_one_or_none()

            if not player:
                return {
                    "status": "error",
                    "player_id": player_id,
                    "error": "Player not found",
                    "message": f"Player with ID {player_id} not found in database",
                }

            if not player.is_active:
                return {
                    "status": "error",
                    "player_id": player_id,
                    "username": player.username,
                    "error": "Player is inactive",
                    "message": f"Player {player.username} is inactive and cannot be scheduled",
                }

            if dry_run:
                return {
                    "status": "would_recreate",
                    "player_id": player_id,
                    "username": player.username,
                    "current_schedule_id": player.schedule_id,
                    "fetch_interval": player.fetch_interval_minutes,
                    "message": f"Would recreate schedule for {player.username} with {player.fetch_interval_minutes}min interval",
                }
            else:
                # Recreate the schedule
                new_schedule_id = (
                    await schedule_manager.ensure_player_scheduled(player)
                )

                # Update database
                player.schedule_id = new_schedule_id
                await db_session.commit()

                return {
                    "status": "recreated",
                    "player_id": player_id,
                    "username": player.username,
                    "new_schedule_id": new_schedule_id,
                    "fetch_interval": player.fetch_interval_minutes,
                    "message": f"Successfully recreated schedule for {player.username}: {new_schedule_id}",
                }

        except Exception as e:
            await db_session.rollback()
            return {
                "status": "error",
                "player_id": player_id,
                "error": str(e),
                "message": f"Failed to recreate schedule for player {player_id}: {str(e)}",
            }


def print_schedule_list(schedule_data: Dict[str, Any]):
    """Print a formatted list of schedules."""
    if "error" in schedule_data:
        print(f"Error: {schedule_data['error']}")
        return

    schedules = schedule_data.get("schedules", [])
    status_counts = schedule_data.get("status_counts", {})

    print(f"\nFound {len(schedules)} total schedules")
    print("\nStatus Summary:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")

    print(f"\nSchedule Details:")
    print("-" * 120)
    print(
        f"{'Schedule ID':<30} {'Status':<15} {'Player ID':<10} {'Username':<15} {'Active':<8} {'Interval':<10} {'Cron':<20}"
    )
    print("-" * 120)

    for schedule in schedules:
        schedule_id = schedule.get("schedule_id", "")[:29]
        status = schedule.get("status", "")
        player_id = (
            str(schedule.get("player_id", ""))
            if schedule.get("player_id")
            else ""
        )
        username = schedule.get("username", "") or ""
        is_active = (
            str(schedule.get("is_active", ""))
            if schedule.get("is_active") is not None
            else ""
        )
        fetch_interval = (
            str(schedule.get("fetch_interval", ""))
            if schedule.get("fetch_interval")
            else ""
        )
        cron = schedule.get("cron", "")[:19]

        print(
            f"{schedule_id:<30} {status:<15} {player_id:<10} {username:<15} {is_active:<8} {fetch_interval:<10} {cron:<20}"
        )


def confirm_operation(operation: str, details: str = "") -> bool:
    """Ask user for confirmation before performing operation."""
    print(f"\nYou are about to perform: {operation}")
    if details:
        print(f"Details: {details}")

    response = input("\nDo you want to continue? (yes/no): ").strip().lower()
    return response in ["yes", "y"]


def main():
    """Main entry point for the maintenance script."""
    parser = argparse.ArgumentParser(
        description="Schedule maintenance utilities for TaskIQ scheduler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  cleanup-orphaned    Remove schedules for deleted/inactive players
  verify-consistency  Check DB/Redis schedule consistency  
  bulk-reschedule     Reschedule all players
  list-schedules      List all player schedules with status
  remove-schedule     Remove a specific schedule by ID
  recreate-schedule   Recreate a specific player's schedule

Examples:
  # List all schedules
  python scripts/schedule_maintenance.py list-schedules
  
  # Dry run cleanup
  python scripts/schedule_maintenance.py cleanup-orphaned --dry-run
  
  # Verify consistency
  python scripts/schedule_maintenance.py verify-consistency
  
  # Remove specific schedule
  python scripts/schedule_maintenance.py remove-schedule --schedule-id player_fetch_123
  
  # Recreate player schedule
  python scripts/schedule_maintenance.py recreate-schedule --player-id 123
        """,
    )

    parser.add_argument(
        "command",
        choices=[
            "cleanup-orphaned",
            "verify-consistency",
            "bulk-reschedule",
            "list-schedules",
            "remove-schedule",
            "recreate-schedule",
        ],
        help="Maintenance command to execute",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    parser.add_argument(
        "--player-id",
        type=int,
        help="Specific player ID for single-player operations",
    )

    parser.add_argument(
        "--schedule-id",
        type=str,
        help="Specific schedule ID for schedule operations",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of items to process in each batch (default: 50)",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force operations without confirmation prompts",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.command in ["remove-schedule"] and not args.schedule_id:
        print("Error: --schedule-id is required for remove-schedule command")
        sys.exit(1)

    if args.command in ["recreate-schedule"] and not args.player_id:
        print("Error: --player-id is required for recreate-schedule command")
        sys.exit(1)

    if args.batch_size < 1:
        print("Error: batch-size must be at least 1")
        sys.exit(1)

    async def run():
        try:
            if args.command == "cleanup-orphaned":
                if not args.force and not args.dry_run:
                    if not confirm_operation(
                        "Cleanup orphaned schedules",
                        "This will remove schedules for deleted/inactive players",
                    ):
                        print("Operation cancelled")
                        return

                stats = await cleanup_orphaned_schedules(
                    args.dry_run, args.batch_size
                )
                stats.print_summary()

                if stats.failed_operations > 0:
                    sys.exit(1)

            elif args.command == "verify-consistency":
                stats = await verify_schedule_consistency(args.batch_size)
                stats.print_summary()

                if stats.failed_operations > 0:
                    print(
                        f"\n⚠ Found {stats.failed_operations} consistency issues"
                    )
                    sys.exit(1)

            elif args.command == "bulk-reschedule":
                if not args.force and not args.dry_run:
                    if not confirm_operation(
                        "Bulk reschedule all players",
                        "This will recreate schedules for all active players",
                    ):
                        print("Operation cancelled")
                        return

                stats = await bulk_reschedule_players(
                    args.dry_run, args.batch_size
                )
                stats.print_summary()

                if stats.failed_operations > 0:
                    sys.exit(1)

            elif args.command == "list-schedules":
                schedule_data = await list_all_schedules()
                print_schedule_list(schedule_data)

            elif args.command == "remove-schedule":
                if not args.force and not args.dry_run:
                    if not confirm_operation(
                        f"Remove schedule {args.schedule_id}"
                    ):
                        print("Operation cancelled")
                        return

                result = await remove_specific_schedule(
                    args.schedule_id, args.dry_run
                )
                print(f"Result: {result['message']}")

                if result["status"] == "error":
                    sys.exit(1)

            elif args.command == "recreate-schedule":
                if not args.force and not args.dry_run:
                    if not confirm_operation(
                        f"Recreate schedule for player ID {args.player_id}"
                    ):
                        print("Operation cancelled")
                        return

                result = await recreate_player_schedule(
                    args.player_id, args.dry_run
                )
                print(f"Result: {result['message']}")

                if result["status"] == "error":
                    sys.exit(1)

        except KeyboardInterrupt:
            print("\n\nOperation interrupted by user")
            sys.exit(130)
        except Exception as e:
            logger.exception("Fatal error during maintenance operation")
            print(f"\n✗ Operation failed: {e}")
            sys.exit(1)

    # Run the async operation
    asyncio.run(run())


if __name__ == "__main__":
    main()
