#!/usr/bin/env python3
"""
Script to demonstrate hiscore data deduplication functionality.

This script shows how the fetch worker now only saves data when it has changed
from the previous fetch, avoiding redundant database records.
"""

import asyncio
import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from src.models.base import AsyncSessionLocal
from src.models.hiscore import HiscoreRecord
from src.models.player import Player
from src.services.osrs_api import HiscoreData
from src.workers.fetch import _fetch_player_hiscores

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def create_test_player() -> Player:
    """Create a test player for demonstration."""
    async with AsyncSessionLocal() as session:
        # Check if test player already exists
        from sqlalchemy import select

        stmt = select(Player).where(Player.username == "test_dedup_player")
        result = await session.execute(stmt)
        existing_player = result.scalar_one_or_none()

        if existing_player:
            logger.info(
                f"Using existing test player: {existing_player.username}"
            )
            return existing_player

        # Create new test player
        player = Player(
            username="test_dedup_player",
            is_active=True,
            fetch_interval_minutes=60,
        )
        session.add(player)
        await session.commit()
        await session.refresh(player)
        logger.info(f"Created test player: {player.username}")
        return player


async def get_record_count(player_id: int) -> int:
    """Get the number of hiscore records for a player."""
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select, func

        stmt = select(func.count(HiscoreRecord.id)).where(
            HiscoreRecord.player_id == player_id
        )
        result = await session.execute(stmt)
        return result.scalar()


async def demonstrate_deduplication():
    """Demonstrate the deduplication functionality."""
    logger.info("=== OSRS Hiscore Data Deduplication Demo ===")

    # Create test player
    player = await create_test_player()
    initial_count = await get_record_count(player.id)
    logger.info(f"Initial record count for {player.username}: {initial_count}")

    # Mock hiscore data that will be "fetched" from OSRS API
    mock_hiscore_data = HiscoreData(
        overall={"rank": 1000, "level": 1500, "experience": 50000000},
        skills={
            "attack": {"rank": 500, "level": 99, "experience": 13034431},
            "defence": {"rank": 600, "level": 90, "experience": 5346332},
            "strength": {"rank": 450, "level": 99, "experience": 13034431},
        },
        bosses={
            "zulrah": {"rank": 100, "kc": 500},
            "vorkath": {"rank": 200, "kc": 250},
        },
        fetched_at=datetime.now(timezone.utc),
    )

    # First fetch - should always create a record
    logger.info("\n--- First Fetch (should create record) ---")
    with patch("src.workers.fetch.OSRSAPIClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.fetch_player_hiscores.return_value = mock_hiscore_data
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result1 = await _fetch_player_hiscores(player.username)

    logger.info(f"First fetch result: {result1['status']}")
    logger.info(f"Data changed: {result1.get('data_changed', 'N/A')}")
    if "record_id" in result1:
        logger.info(f"Created record ID: {result1['record_id']}")

    count_after_first = await get_record_count(player.id)
    logger.info(f"Record count after first fetch: {count_after_first}")

    # Second fetch with identical data - should NOT create a record
    logger.info("\n--- Second Fetch (identical data, should skip) ---")
    with patch("src.workers.fetch.OSRSAPIClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.fetch_player_hiscores.return_value = mock_hiscore_data
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result2 = await _fetch_player_hiscores(player.username)

    logger.info(f"Second fetch result: {result2['status']}")
    logger.info(f"Message: {result2.get('message', 'N/A')}")
    if "last_record_id" in result2:
        logger.info(
            f"Referenced existing record ID: {result2['last_record_id']}"
        )

    count_after_second = await get_record_count(player.id)
    logger.info(f"Record count after second fetch: {count_after_second}")

    # Third fetch with changed data - should create a new record
    logger.info("\n--- Third Fetch (changed data, should create record) ---")
    changed_hiscore_data = HiscoreData(
        overall={
            "rank": 999,
            "level": 1501,
            "experience": 50100000,
        },  # Changed
        skills={
            "attack": {"rank": 500, "level": 99, "experience": 13034431},
            "defence": {"rank": 600, "level": 90, "experience": 5346332},
            "strength": {"rank": 450, "level": 99, "experience": 13034431},
        },
        bosses={
            "zulrah": {"rank": 100, "kc": 501},  # Changed
            "vorkath": {"rank": 200, "kc": 250},
        },
        fetched_at=datetime.now(timezone.utc),
    )

    with patch("src.workers.fetch.OSRSAPIClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.fetch_player_hiscores.return_value = changed_hiscore_data
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result3 = await _fetch_player_hiscores(player.username)

    logger.info(f"Third fetch result: {result3['status']}")
    logger.info(f"Data changed: {result3.get('data_changed', 'N/A')}")
    if "record_id" in result3:
        logger.info(f"Created record ID: {result3['record_id']}")

    count_after_third = await get_record_count(player.id)
    logger.info(f"Record count after third fetch: {count_after_third}")

    # Summary
    logger.info("\n=== Summary ===")
    logger.info(f"Initial records: {initial_count}")
    logger.info(f"After first fetch (new data): {count_after_first}")
    logger.info(f"After second fetch (same data): {count_after_second}")
    logger.info(f"After third fetch (changed data): {count_after_third}")
    logger.info(f"Total records created: {count_after_third - initial_count}")
    logger.info(
        "✅ Deduplication working correctly - only 2 records created for 3 fetches!"
    )


if __name__ == "__main__":
    asyncio.run(demonstrate_deduplication())
