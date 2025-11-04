#!/usr/bin/env python3
"""Script to run the TaskIQ scheduler."""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.workers.scheduler_config import scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def main():
    """Run the TaskIQ scheduler."""
    logger.info("Starting TaskIQ scheduler...")

    try:
        # Start the scheduler
        await scheduler.startup()
        logger.info("TaskIQ scheduler started successfully")

        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
        raise
    finally:
        # Shutdown the scheduler
        await scheduler.shutdown()
        logger.info("TaskIQ scheduler stopped")


if __name__ == "__main__":
    asyncio.run(main())
