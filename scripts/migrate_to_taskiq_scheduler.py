#!/usr/bin/env python3
"""
Migration script to transition existing players from custom scheduler to TaskIQ scheduler.

This script migrates all active players to individual TaskIQ schedules using the
PlayerScheduleManager service. It includes progress tracking, error handling,
and verification to ensure all players are properly scheduled.

Usage:
    python scripts/migrate_to_taskiq_scheduler.py [--dry-run] [--verify-only]

Options:
    --dry-run: Show what would be done without making changes
    --verify-only: Only verify existing schedules without creating new ones
    --batch-size: Number of players to process in each batch (default: 50)
    --continue-from: Player ID to continue from (for resuming partial migrations)
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime, UTC
from typing import Dict, List, Optional, Any

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
            f"migration_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.log"
        ),
    ],
)

logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """Base exception for migration errors."""

    pass


class MigrationStats:
    """Track migration statistics and progress."""

    def __init__(self):
        self.total_players = 0
        self.processed_players = 0
        self.successful_migrations = 0
        self.failed_migrations = 0
        self.skipped_players = 0
        self.already_scheduled = 0
        self.errors: List[Dict[str, Any]] = []
        self.start_time = datetime.now(UTC)

    def add_success(self, player: Player, schedule_id: str):
        """Record a successful migration."""
        self.successful_migrations += 1
        self.processed_players += 1
        logger.info(
            f"✓ Successfully migrated {player.username} (ID: {player.id}) -> {schedule_id}"
        )

    def add_failure(self, player: Player, error: str):
        """Record a failed migration."""
        self.failed_migrations += 1
        self.processed_players += 1
        error_info = {
            "player_id": player.id,
            "username": player.username,
            "error": error,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self.errors.append(error_info)
        logger.error(
            f"✗ Failed to migrate {player.username} (ID: {player.id}): {error}"
        )

    def add_skip(self, player: Player, reason: str):
        """Record a skipped player."""
        self.skipped_players += 1
        self.processed_players += 1
        logger.info(f"⊘ Skipped {player.username} (ID: {player.id}): {reason}")

    def add_already_scheduled(self, player: Player, schedule_id: str):
        """Record a player that was already scheduled."""
        self.already_scheduled += 1
        self.processed_players += 1
        logger.info(
            f"→ {player.username} (ID: {player.id}) already scheduled: {schedule_id}"
        )

    def get_summary(self) -> Dict[str, Any]:
        """Get migration summary statistics."""
        duration = (datetime.now(UTC) - self.start_time).total_seconds()

        return {
            "migration_completed": True,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now(UTC).isoformat(),
            "duration_seconds": duration,
            "total_players": self.total_players,
            "processed_players": self.processed_players,
            "successful_migrations": self.successful_migrations,
            "failed_migrations": self.failed_migrations,
            "skipped_players": self.skipped_players,
            "already_scheduled": self.already_scheduled,
            "success_rate": (
                self.successful_migrations
                / max(1, self.processed_players)
                * 100
            ),
            "errors": self.errors,
        }

    def print_summary(self):
        """Print a formatted summary of the migration."""
        summary = self.get_summary()

        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)
        print(f"Duration: {summary['duration_seconds']:.2f} seconds")
        print(f"Total players: {summary['total_players']}")
        print(f"Processed: {summary['processed_players']}")
        print(f"✓ Successful migrations: {summary['successful_migrations']}")
        print(f"→ Already scheduled: {summary['already_scheduled']}")
        print(f"⊘ Skipped: {summary['skipped_players']}")
        print(f"✗ Failed: {summary['failed_migrations']}")
        print(f"Success rate: {summary['success_rate']:.1f}%")

        if self.errors:
            print(f"\nERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(
                    f"  - {error['username']} (ID: {error['player_id']}): {error['error']}"
                )

        print("=" * 60)


async def get_players_to_migrate(
    db_session: AsyncSession,
    continue_from: Optional[int] = None,
    batch_size: int = 50,
) -> List[Player]:
    """
    Get the next batch of active players that need migration.

    Args:
        db_session: Database session
        continue_from: Player ID to continue from (for resuming)
        batch_size: Number of players to return

    Returns:
        List of Player objects to migrate
    """
    stmt = select(Player).where(Player.is_active.is_(True))

    if continue_from:
        stmt = stmt.where(Player.id >= continue_from)

    stmt = stmt.order_by(Player.id).limit(batch_size)

    result = await db_session.execute(stmt)
    return list(result.scalars().all())


async def verify_player_schedule(
    player: Player, schedule_manager: PlayerScheduleManager
) -> Dict[str, Any]:
    """
    Verify that a player's schedule is properly configured.

    Args:
        player: Player to verify
        schedule_manager: PlayerScheduleManager instance

    Returns:
        Dict with verification results
    """
    if not player.schedule_id:
        return {
            "valid": False,
            "reason": "No schedule_id in database",
            "needs_migration": True,
        }

    try:
        # Use the existing verification method
        is_valid = await schedule_manager._verify_schedule_exists_and_valid(
            player
        )

        if is_valid:
            return {
                "valid": True,
                "schedule_id": player.schedule_id,
                "needs_migration": False,
            }
        else:
            return {
                "valid": False,
                "reason": "Schedule invalid or missing in Redis",
                "schedule_id": player.schedule_id,
                "needs_migration": True,
            }

    except Exception as e:
        return {
            "valid": False,
            "reason": f"Verification error: {str(e)}",
            "schedule_id": player.schedule_id,
            "needs_migration": True,
        }


async def migrate_player(
    player: Player,
    schedule_manager: PlayerScheduleManager,
    db_session: AsyncSession,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Migrate a single player to TaskIQ scheduler.

    Args:
        player: Player to migrate
        schedule_manager: PlayerScheduleManager instance
        db_session: Database session
        dry_run: If True, don't make actual changes

    Returns:
        Dict with migration results
    """
    try:
        # First verify if player already has a valid schedule
        verification = await verify_player_schedule(player, schedule_manager)

        if verification["valid"]:
            return {
                "status": "already_scheduled",
                "schedule_id": verification["schedule_id"],
                "message": "Player already has valid schedule",
            }

        if dry_run:
            return {
                "status": "would_migrate",
                "message": f"Would create schedule for {player.username} with {player.fetch_interval_minutes}min interval",
            }

        # Ensure player has a valid schedule (create or recreate)
        schedule_id = await schedule_manager.ensure_player_scheduled(player)

        # Update the player record with the schedule_id
        player.schedule_id = schedule_id

        # Commit the database changes
        await db_session.commit()

        return {
            "status": "success",
            "schedule_id": schedule_id,
            "message": f"Successfully migrated player to schedule {schedule_id}",
        }

    except Exception as e:
        await db_session.rollback()
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to migrate player: {str(e)}",
        }


async def run_migration(
    dry_run: bool = False,
    verify_only: bool = False,
    batch_size: int = 50,
    continue_from: Optional[int] = None,
) -> MigrationStats:
    """
    Run the complete migration process.

    Args:
        dry_run: If True, show what would be done without making changes
        verify_only: If True, only verify existing schedules
        batch_size: Number of players to process in each batch
        continue_from: Player ID to continue from

    Returns:
        MigrationStats with results
    """
    stats = MigrationStats()

    logger.info("Starting TaskIQ scheduler migration")
    if dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
    if verify_only:
        logger.info("VERIFY ONLY MODE - Only checking existing schedules")

    # Initialize database
    await init_db()

    # Create schedule manager
    schedule_manager = PlayerScheduleManager(redis_schedule_source)

    async with AsyncSessionLocal() as db_session:
        try:
            # Get total count of active players
            count_stmt = select(func.count(Player.id)).where(
                Player.is_active.is_(True)
            )
            if continue_from:
                count_stmt = count_stmt.where(Player.id >= continue_from)

            count_result = await db_session.execute(count_stmt)
            stats.total_players = count_result.scalar() or 0

            logger.info(
                f"Found {stats.total_players} active players to process"
            )

            if stats.total_players == 0:
                logger.info("No active players found - migration complete")
                return stats

            # Process players in batches
            current_continue_from = continue_from

            while True:
                # Get next batch of players
                players_batch = await get_players_to_migrate(
                    db_session, current_continue_from, batch_size
                )

                if not players_batch:
                    logger.info("No more players to process")
                    break

                logger.info(
                    f"Processing batch of {len(players_batch)} players "
                    f"(IDs: {players_batch[0].id} - {players_batch[-1].id})"
                )

                # Process each player in the batch
                for player in players_batch:
                    try:
                        if not player.is_active:
                            stats.add_skip(player, "Player is inactive")
                            continue

                        if verify_only:
                            # Only verify existing schedules
                            verification = await verify_player_schedule(
                                player, schedule_manager
                            )
                            if verification["valid"]:
                                stats.add_already_scheduled(
                                    player, verification["schedule_id"]
                                )
                            else:
                                stats.add_failure(
                                    player, verification["reason"]
                                )
                        else:
                            # Perform migration
                            result = await migrate_player(
                                player, schedule_manager, db_session, dry_run
                            )

                            if result["status"] == "success":
                                stats.add_success(
                                    player, result["schedule_id"]
                                )
                            elif result["status"] == "already_scheduled":
                                stats.add_already_scheduled(
                                    player, result["schedule_id"]
                                )
                            elif result["status"] == "would_migrate":
                                stats.add_success(player, "dry-run")
                            else:
                                stats.add_failure(
                                    player,
                                    result.get("error", "Unknown error"),
                                )

                    except Exception as e:
                        stats.add_failure(
                            player, f"Unexpected error: {str(e)}"
                        )
                        logger.exception(
                            f"Unexpected error processing player {player.username}"
                        )

                # Update continue_from for next batch
                current_continue_from = players_batch[-1].id + 1

                # Progress update
                progress_pct = (
                    stats.processed_players / stats.total_players
                ) * 100
                logger.info(
                    f"Progress: {stats.processed_players}/{stats.total_players} "
                    f"({progress_pct:.1f}%) - "
                    f"Success: {stats.successful_migrations}, "
                    f"Already scheduled: {stats.already_scheduled}, "
                    f"Failed: {stats.failed_migrations}"
                )

                # Small delay between batches to avoid overwhelming Redis
                await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"Fatal error during migration: {e}")
            raise MigrationError(f"Migration failed: {str(e)}") from e

    logger.info("Migration process completed")
    return stats


async def verify_migration_completeness() -> Dict[str, Any]:
    """
    Verify that all active players have been properly migrated.

    Returns:
        Dict with verification results
    """
    logger.info("Verifying migration completeness...")

    async with AsyncSessionLocal() as db_session:
        try:
            # Count active players without schedule_id
            unscheduled_stmt = select(func.count(Player.id)).where(
                Player.is_active.is_(True), Player.schedule_id.is_(None)
            )
            unscheduled_result = await db_session.execute(unscheduled_stmt)
            unscheduled_count = unscheduled_result.scalar() or 0

            # Count active players with schedule_id
            scheduled_stmt = select(func.count(Player.id)).where(
                Player.is_active.is_(True), Player.schedule_id.is_not(None)
            )
            scheduled_result = await db_session.execute(scheduled_stmt)
            scheduled_count = scheduled_result.scalar() or 0

            # Get total active players
            total_stmt = select(func.count(Player.id)).where(
                Player.is_active.is_(True)
            )
            total_result = await db_session.execute(total_stmt)
            total_count = total_result.scalar() or 0

            verification_result = {
                "total_active_players": total_count,
                "scheduled_players": scheduled_count,
                "unscheduled_players": unscheduled_count,
                "migration_complete": unscheduled_count == 0,
                "completion_percentage": (
                    scheduled_count / max(1, total_count)
                )
                * 100,
            }

            if verification_result["migration_complete"]:
                logger.info(
                    "✓ Migration verification PASSED - All active players are scheduled"
                )
            else:
                logger.warning(
                    f"⚠ Migration verification INCOMPLETE - "
                    f"{unscheduled_count} players still need scheduling"
                )

            return verification_result

        except Exception as e:
            logger.error(f"Error during migration verification: {e}")
            return {"error": str(e), "migration_complete": False}


def main():
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(
        description="Migrate existing players to TaskIQ scheduler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to see what would be migrated
  python scripts/migrate_to_taskiq_scheduler.py --dry-run
  
  # Verify existing schedules only
  python scripts/migrate_to_taskiq_scheduler.py --verify-only
  
  # Run actual migration
  python scripts/migrate_to_taskiq_scheduler.py
  
  # Resume migration from player ID 100
  python scripts/migrate_to_taskiq_scheduler.py --continue-from 100
  
  # Process in smaller batches
  python scripts/migrate_to_taskiq_scheduler.py --batch-size 25
        """,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing schedules without creating new ones",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of players to process in each batch (default: 50)",
    )

    parser.add_argument(
        "--continue-from",
        type=int,
        help="Player ID to continue from (for resuming partial migrations)",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.batch_size < 1:
        print("Error: batch-size must be at least 1")
        sys.exit(1)

    if args.continue_from is not None and args.continue_from < 1:
        print("Error: continue-from must be at least 1")
        sys.exit(1)

    async def run():
        try:
            # Run the migration
            stats = await run_migration(
                dry_run=args.dry_run,
                verify_only=args.verify_only,
                batch_size=args.batch_size,
                continue_from=args.continue_from,
            )

            # Print summary
            stats.print_summary()

            # Verify completeness if not a dry run
            if not args.dry_run and not args.verify_only:
                verification = await verify_migration_completeness()

                if not verification.get("migration_complete", False):
                    print(f"\n⚠ WARNING: Migration may be incomplete!")
                    print(
                        f"Consider running with --continue-from {args.continue_from or 1} to retry failed migrations"
                    )
                    sys.exit(1)

            # Exit with error code if there were failures
            if stats.failed_migrations > 0:
                print(
                    f"\n⚠ Migration completed with {stats.failed_migrations} failures"
                )
                sys.exit(1)

            print("\n✓ Migration completed successfully!")

        except KeyboardInterrupt:
            print("\n\nMigration interrupted by user")
            sys.exit(130)
        except Exception as e:
            logger.exception("Fatal error during migration")
            print(f"\n✗ Migration failed: {e}")
            sys.exit(1)

    # Run the async migration
    asyncio.run(run())


if __name__ == "__main__":
    main()
