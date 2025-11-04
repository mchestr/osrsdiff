#!/usr/bin/env python3
"""
Deployment script for TaskIQ scheduler migration.

This script orchestrates the complete deployment process for migrating from
the custom scheduler to TaskIQ's native scheduler. It handles database migrations,
service updates, and verification steps.

Usage:
    python scripts/deploy_scheduler.py [--environment ENV] [--dry-run] [--skip-migration]

Options:
    --environment: Target environment (development, staging, production)
    --dry-run: Show what would be done without making changes
    --skip-migration: Skip the player migration step (useful for rollbacks)
    --verify-only: Only verify the current state without making changes
"""

import argparse
import asyncio
import logging
import subprocess
import sys
import time
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add src to path for imports
sys.path.insert(0, "src")

from src.models.base import init_db
from scripts.migrate_to_taskiq_scheduler import (
    run_migration,
    verify_migration_completeness,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            f"deployment_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.log"
        ),
    ],
)

logger = logging.getLogger(__name__)


class DeploymentError(Exception):
    """Base exception for deployment errors."""

    pass


class DeploymentManager:
    """Manages the scheduler deployment process."""

    def __init__(
        self, environment: str = "development", dry_run: bool = False
    ):
        self.environment = environment
        self.dry_run = dry_run
        self.deployment_steps = []
        self.start_time = datetime.now(UTC)

    def log_step(
        self, step: str, status: str = "started", details: Optional[str] = None
    ):
        """Log a deployment step with timestamp."""
        timestamp = datetime.now(UTC).isoformat()
        step_info = {
            "step": step,
            "status": status,
            "timestamp": timestamp,
            "details": details,
        }
        self.deployment_steps.append(step_info)

        if status == "started":
            logger.info(f"🚀 Starting: {step}")
        elif status == "completed":
            logger.info(f"✓ Completed: {step}")
        elif status == "failed":
            logger.error(f"✗ Failed: {step} - {details}")
        elif status == "skipped":
            logger.info(f"⊘ Skipped: {step} - {details}")

    async def check_prerequisites(self) -> bool:
        """Check that all prerequisites are met for deployment."""
        self.log_step("Checking deployment prerequisites")

        try:
            # Check if database is accessible
            await init_db()
            logger.info("✓ Database connection successful")

            # Check if Redis is accessible
            from src.workers.main import redis_schedule_source

            try:
                # Test Redis connection by attempting to get schedules
                await redis_schedule_source.get_schedules()
                logger.info("✓ Redis connection successful")
            except Exception as e:
                logger.error(f"✗ Redis connection failed: {e}")
                return False

            # Check if required files exist
            required_files = [
                "src/workers/main.py",
                "src/services/scheduler.py",
                "docker-compose.yml",
            ]

            for file_path in required_files:
                if not Path(file_path).exists():
                    logger.error(f"✗ Required file missing: {file_path}")
                    return False

            logger.info("✓ All required files present")

            self.log_step("Checking deployment prerequisites", "completed")
            return True

        except Exception as e:
            self.log_step(
                "Checking deployment prerequisites", "failed", str(e)
            )
            return False

    def run_database_migrations(self) -> bool:
        """Run Alembic database migrations."""
        self.log_step("Running database migrations")

        try:
            if self.dry_run:
                logger.info("DRY RUN: Would run 'alembic upgrade head'")
                self.log_step(
                    "Running database migrations", "completed", "dry run"
                )
                return True

            # Run Alembic migrations
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode == 0:
                logger.info("✓ Database migrations completed successfully")
                if result.stdout:
                    logger.info(f"Migration output: {result.stdout}")
                self.log_step("Running database migrations", "completed")
                return True
            else:
                logger.error(f"✗ Database migration failed: {result.stderr}")
                self.log_step(
                    "Running database migrations", "failed", result.stderr
                )
                return False

        except subprocess.TimeoutExpired:
            error_msg = "Database migration timed out after 5 minutes"
            logger.error(f"✗ {error_msg}")
            self.log_step("Running database migrations", "failed", error_msg)
            return False
        except Exception as e:
            self.log_step("Running database migrations", "failed", str(e))
            return False

    async def migrate_players_to_scheduler(self) -> bool:
        """Migrate existing players to TaskIQ scheduler."""
        self.log_step("Migrating players to TaskIQ scheduler")

        try:
            # Run the player migration
            stats = await run_migration(dry_run=self.dry_run)

            # Check if migration was successful
            if stats.failed_migrations > 0:
                error_msg = f"Migration completed with {stats.failed_migrations} failures"
                logger.warning(f"⚠ {error_msg}")
                self.log_step(
                    "Migrating players to TaskIQ scheduler",
                    "failed",
                    error_msg,
                )
                return False

            success_msg = f"Migrated {stats.successful_migrations} players, {stats.already_scheduled} already scheduled"
            logger.info(f"✓ {success_msg}")
            self.log_step(
                "Migrating players to TaskIQ scheduler",
                "completed",
                success_msg,
            )
            return True

        except Exception as e:
            self.log_step(
                "Migrating players to TaskIQ scheduler", "failed", str(e)
            )
            return False

    async def verify_deployment(self) -> bool:
        """Verify that the deployment was successful."""
        self.log_step("Verifying deployment")

        try:
            # Verify migration completeness
            verification = await verify_migration_completeness()

            if not verification.get("migration_complete", False):
                error_msg = f"Migration incomplete: {verification.get('unscheduled_players', 0)} players unscheduled"
                logger.error(f"✗ {error_msg}")
                self.log_step("Verifying deployment", "failed", error_msg)
                return False

            # Additional verification steps could be added here:
            # - Check that scheduler service is running
            # - Verify Redis schedule storage
            # - Test task execution

            success_msg = f"All {verification['total_active_players']} active players are properly scheduled"
            logger.info(f"✓ {success_msg}")
            self.log_step("Verifying deployment", "completed", success_msg)
            return True

        except Exception as e:
            self.log_step("Verifying deployment", "failed", str(e))
            return False

    def update_docker_services(self) -> bool:
        """Update Docker services for the new scheduler."""
        self.log_step("Updating Docker services")

        try:
            if self.dry_run:
                logger.info("DRY RUN: Would restart Docker services")
                self.log_step(
                    "Updating Docker services", "completed", "dry run"
                )
                return True

            # Stop old services
            logger.info("Stopping existing services...")
            subprocess.run(
                ["docker-compose", "stop", "worker", "app"],
                check=True,
                timeout=60,
            )

            # Start services with scheduler
            logger.info("Starting services with scheduler...")
            subprocess.run(
                ["docker-compose", "up", "-d", "postgres", "redis"],
                check=True,
                timeout=60,
            )

            # Wait a moment for services to be ready
            time.sleep(5)

            subprocess.run(
                ["docker-compose", "up", "-d", "app", "worker", "scheduler"],
                check=True,
                timeout=60,
            )

            logger.info("✓ Docker services updated successfully")
            self.log_step("Updating Docker services", "completed")
            return True

        except subprocess.CalledProcessError as e:
            error_msg = f"Docker command failed: {e}"
            logger.error(f"✗ {error_msg}")
            self.log_step("Updating Docker services", "failed", error_msg)
            return False
        except Exception as e:
            self.log_step("Updating Docker services", "failed", str(e))
            return False

    def print_deployment_summary(self):
        """Print a summary of the deployment process."""
        duration = (datetime.now(UTC) - self.start_time).total_seconds()

        print("\n" + "=" * 60)
        print("DEPLOYMENT SUMMARY")
        print("=" * 60)
        print(f"Environment: {self.environment}")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Dry run: {self.dry_run}")
        print(f"Total steps: {len(self.deployment_steps)}")

        # Count step statuses
        completed = sum(
            1
            for step in self.deployment_steps
            if step["status"] == "completed"
        )
        failed = sum(
            1 for step in self.deployment_steps if step["status"] == "failed"
        )
        skipped = sum(
            1 for step in self.deployment_steps if step["status"] == "skipped"
        )

        print(f"✓ Completed: {completed}")
        print(f"⊘ Skipped: {skipped}")
        print(f"✗ Failed: {failed}")

        if failed > 0:
            print(f"\nFAILED STEPS:")
            for step in self.deployment_steps:
                if step["status"] == "failed":
                    print(f"  - {step['step']}: {step['details']}")

        print("\nDETAILED STEPS:")
        for step in self.deployment_steps:
            status_icon = {
                "completed": "✓",
                "failed": "✗",
                "skipped": "⊘",
                "started": "→",
            }.get(step["status"], "?")

            print(f"  {status_icon} {step['step']} ({step['status']})")
            if step["details"]:
                print(f"    {step['details']}")

        print("=" * 60)


async def run_deployment(
    environment: str = "development",
    dry_run: bool = False,
    skip_migration: bool = False,
    verify_only: bool = False,
) -> bool:
    """
    Run the complete scheduler deployment process.

    Args:
        environment: Target environment
        dry_run: If True, show what would be done without making changes
        skip_migration: If True, skip the player migration step
        verify_only: If True, only verify current state

    Returns:
        True if deployment was successful, False otherwise
    """
    deployment = DeploymentManager(environment, dry_run)

    logger.info(f"Starting TaskIQ scheduler deployment for {environment}")
    if dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
    if verify_only:
        logger.info("VERIFY ONLY MODE - Only checking current state")

    try:
        # Step 1: Check prerequisites
        if not await deployment.check_prerequisites():
            logger.error("Prerequisites check failed - aborting deployment")
            return False

        if verify_only:
            # Only run verification
            success = await deployment.verify_deployment()
            deployment.print_deployment_summary()
            return success

        # Step 2: Run database migrations
        if not deployment.run_database_migrations():
            logger.error("Database migration failed - aborting deployment")
            return False

        # Step 3: Migrate players (unless skipped)
        if not skip_migration:
            if not await deployment.migrate_players_to_scheduler():
                logger.error("Player migration failed - aborting deployment")
                return False
        else:
            deployment.log_step(
                "Migrating players to TaskIQ scheduler",
                "skipped",
                "skip-migration flag",
            )

        # Step 4: Update Docker services
        if not deployment.update_docker_services():
            logger.error("Docker service update failed - aborting deployment")
            return False

        # Step 5: Verify deployment
        if not await deployment.verify_deployment():
            logger.error("Deployment verification failed")
            return False

        logger.info("✓ Scheduler deployment completed successfully!")
        deployment.print_deployment_summary()
        return True

    except Exception as e:
        logger.exception("Fatal error during deployment")
        deployment.print_deployment_summary()
        return False


def main():
    """Main entry point for the deployment script."""
    parser = argparse.ArgumentParser(
        description="Deploy TaskIQ scheduler migration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run deployment
  python scripts/deploy_scheduler.py --dry-run
  
  # Deploy to staging environment
  python scripts/deploy_scheduler.py --environment staging
  
  # Deploy without migrating players (for rollback scenarios)
  python scripts/deploy_scheduler.py --skip-migration
  
  # Verify current deployment state
  python scripts/deploy_scheduler.py --verify-only
        """,
    )

    parser.add_argument(
        "--environment",
        choices=["development", "staging", "production"],
        default="development",
        help="Target environment (default: development)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    parser.add_argument(
        "--skip-migration",
        action="store_true",
        help="Skip the player migration step",
    )

    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify current state without making changes",
    )

    args = parser.parse_args()

    async def run():
        try:
            success = await run_deployment(
                environment=args.environment,
                dry_run=args.dry_run,
                skip_migration=args.skip_migration,
                verify_only=args.verify_only,
            )

            if not success:
                print("\n✗ Deployment failed!")
                sys.exit(1)

            print("\n✓ Deployment completed successfully!")

        except KeyboardInterrupt:
            print("\n\nDeployment interrupted by user")
            sys.exit(130)
        except Exception as e:
            logger.exception("Fatal error during deployment")
            print(f"\n✗ Deployment failed: {e}")
            sys.exit(1)

    # Run the async deployment
    asyncio.run(run())


if __name__ == "__main__":
    main()
