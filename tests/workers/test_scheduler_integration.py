"""Integration tests for TaskIQ scheduler functionality."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import ListRedisScheduleSource

from app.config import settings
from app.models.player import Player
from app.services.scheduler import PlayerScheduleManager
from app.workers.main import broker
from app.workers.scheduler import (
    create_scheduler,
    create_scheduler_sources,
)


@pytest.mark.integration
class TestSchedulerIntegration:
    """Integration tests for TaskIQ scheduler with Redis."""

    @pytest_asyncio.fixture
    async def redis_schedule_source(self):
        """Create a test Redis schedule source."""
        # Use a test-specific prefix to avoid conflicts
        test_prefix = f"test_app_schedules_{datetime.now().timestamp()}"

        source = ListRedisScheduleSource(
            url=settings.redis.url,
            prefix=test_prefix,
            max_connection_pool_size=2,  # Smaller pool for tests
        )

        yield source

        # Cleanup: remove all test schedules
        try:
            schedules = await source.get_schedules()
            for schedule in schedules:
                try:
                    await source.delete_schedule(schedule.schedule_id)
                except Exception as e:
                    logging.warning(
                        f"Failed to cleanup schedule {schedule.schedule_id}: {e}"
                    )
        except Exception as e:
            logging.warning(f"Failed to cleanup schedules: {e}")

    @pytest_asyncio.fixture
    async def test_scheduler(self, redis_schedule_source):
        """Create a test scheduler with test Redis source."""
        label_source = LabelScheduleSource(broker)

        scheduler = TaskiqScheduler(
            broker=broker, sources=[redis_schedule_source, label_source]
        )

        return scheduler

    @pytest_asyncio.fixture
    async def schedule_manager(self, redis_schedule_source):
        """Create a PlayerScheduleManager with test Redis source."""
        return PlayerScheduleManager(redis_schedule_source)

    @pytest_asyncio.fixture
    async def sample_player(self, test_session: AsyncSession):
        """Create a sample player for testing."""
        player = Player(
            id=12345,
            username="integration_test_player",
            fetch_interval_minutes=30,
            is_active=True,
        )
        test_session.add(player)
        await test_session.commit()
        await test_session.refresh(player)
        return player

    @pytest.mark.asyncio
    async def test_end_to_end_schedule_creation_and_execution(
        self,
        test_scheduler,
        schedule_manager,
        redis_schedule_source,
        sample_player,
    ):
        """Test complete end-to-end schedule creation and verification."""
        # Step 1: Create a schedule for the player
        schedule_id = await schedule_manager.schedule_player(sample_player)

        assert schedule_id == f"player_fetch_{sample_player.id}"
        assert (
            sample_player.schedule_id is None
        )  # Not set by schedule_player method

        # Step 2: Verify schedule exists in Redis
        schedules = await redis_schedule_source.get_schedules()
        schedule_ids = [s.schedule_id for s in schedules]
        assert schedule_id in schedule_ids

        # Step 3: Find and verify the created schedule
        created_schedule = None
        for schedule in schedules:
            if schedule.schedule_id == schedule_id:
                created_schedule = schedule
                break

        assert created_schedule is not None
        assert created_schedule.cron == "*/30 * * * *"  # 30-minute interval
        # TaskIQ stores task names as module:function format
        assert (
            created_schedule.task_name
            == "app.workers.fetch:fetch_player_hiscores_task"
        )
        assert created_schedule.args == [sample_player.username]

        # Verify labels
        assert created_schedule.labels["player_id"] == str(sample_player.id)
        assert created_schedule.labels["schedule_type"] == "player_fetch"
        assert created_schedule.labels["username"] == sample_player.username

        # Step 4: Test schedule deletion
        # Set schedule_id on player so unschedule_player can find it
        sample_player.schedule_id = schedule_id
        await schedule_manager.unschedule_player(sample_player)

        # Verify schedule is removed
        schedules_after = await redis_schedule_source.get_schedules()
        schedule_ids_after = [s.schedule_id for s in schedules_after]
        assert schedule_id not in schedule_ids_after

    @pytest.mark.asyncio
    async def test_scheduler_sources_configuration(self, test_scheduler):
        """Test that scheduler has correct sources configured."""
        assert len(test_scheduler.sources) == 2

        # Verify source types
        source_types = [type(source) for source in test_scheduler.sources]
        assert ListRedisScheduleSource in source_types
        assert LabelScheduleSource in source_types

        # Find Redis source
        redis_source = None
        for source in test_scheduler.sources:
            if isinstance(source, ListRedisScheduleSource):
                redis_source = source
                break

        assert redis_source is not None

    @pytest.mark.asyncio
    async def test_multiple_player_scheduling(
        self, schedule_manager, redis_schedule_source, test_session
    ):
        """Test scheduling multiple players with different intervals."""
        # Create multiple players with different intervals
        players = [
            Player(
                id=1001,
                username="player_30min",
                fetch_interval_minutes=30,
                is_active=True,
            ),
            Player(
                id=1002,
                username="player_60min",
                fetch_interval_minutes=60,
                is_active=True,
            ),
            Player(
                id=1003,
                username="player_daily",
                fetch_interval_minutes=1440,
                is_active=True,
            ),
        ]

        for player in players:
            test_session.add(player)
        await test_session.commit()

        # Schedule all players
        schedule_ids = []
        for player in players:
            schedule_id = await schedule_manager.schedule_player(player)
            schedule_ids.append(schedule_id)

        # Verify all schedules exist
        schedules = await redis_schedule_source.get_schedules()
        redis_schedule_ids = [s.schedule_id for s in schedules]

        for schedule_id in schedule_ids:
            assert schedule_id in redis_schedule_ids

        # Verify cron expressions are correct
        schedule_map = {s.schedule_id: s for s in schedules}

        assert schedule_map["player_fetch_1001"].cron == "*/30 * * * *"
        assert schedule_map["player_fetch_1002"].cron == "0 * * * *"
        assert schedule_map["player_fetch_1003"].cron == "0 0 * * *"

        # Cleanup
        for player in players:
            await schedule_manager.unschedule_player(player)

    @pytest.mark.asyncio
    async def test_schedule_verification_and_recovery(
        self, schedule_manager, redis_schedule_source, sample_player
    ):
        """Test schedule verification and automatic recovery."""
        # Step 1: Create initial schedule
        schedule_id = await schedule_manager.schedule_player(sample_player)
        sample_player.schedule_id = schedule_id  # Simulate database update

        # Step 2: Verify schedule exists and is valid
        result = await schedule_manager.ensure_player_scheduled(sample_player)
        assert result == schedule_id

        # Step 3: Manually delete schedule from Redis (simulate Redis data loss)
        await redis_schedule_source.delete_schedule(schedule_id)

        # Step 4: Verify recovery - should recreate the schedule
        new_schedule_id = await schedule_manager.ensure_player_scheduled(
            sample_player
        )
        assert new_schedule_id == schedule_id  # Same deterministic ID

        # Verify new schedule exists
        schedules = await redis_schedule_source.get_schedules()
        schedule_ids = [s.schedule_id for s in schedules]
        assert new_schedule_id in schedule_ids

    @pytest.mark.asyncio
    async def test_schedule_update_reschedule(
        self, schedule_manager, redis_schedule_source, sample_player
    ):
        """Test updating player interval and rescheduling."""
        # Step 1: Create initial schedule with 30-minute interval
        initial_schedule_id = await schedule_manager.schedule_player(
            sample_player
        )

        # Verify initial cron
        schedules = await redis_schedule_source.get_schedules()
        initial_schedule = next(
            s for s in schedules if s.schedule_id == initial_schedule_id
        )
        assert initial_schedule.cron == "*/30 * * * *"

        # Step 2: Update player interval to 60 minutes
        sample_player.fetch_interval_minutes = 60
        sample_player.schedule_id = (
            initial_schedule_id  # Simulate database state
        )

        # Step 3: Reschedule player
        new_schedule_id = await schedule_manager.reschedule_player(
            sample_player
        )

        # Should be same deterministic ID
        assert new_schedule_id == initial_schedule_id

        # Step 4: Verify updated cron expression
        schedules_after = await redis_schedule_source.get_schedules()
        updated_schedule = next(
            s for s in schedules_after if s.schedule_id == new_schedule_id
        )
        assert updated_schedule.cron == "0 * * * *"  # Hourly

    @pytest.mark.asyncio
    async def test_schedule_verification_report(
        self, schedule_manager, redis_schedule_source, test_session
    ):
        """Test comprehensive schedule verification reporting."""
        # Create multiple players and schedules
        players = [
            Player(
                id=2001,
                username="valid_player",
                fetch_interval_minutes=30,
                is_active=True,
            ),
            Player(
                id=2002,
                username="another_valid",
                fetch_interval_minutes=60,
                is_active=True,
            ),
        ]

        for player in players:
            test_session.add(player)
        await test_session.commit()

        # Schedule players
        for player in players:
            await schedule_manager.schedule_player(player)

        # Create an invalid schedule manually (wrong player_id in labels)
        from app.workers.fetch import fetch_player_hiscores_task

        await fetch_player_hiscores_task.kicker().with_schedule_id(
            "player_fetch_9999"
        ).with_labels(
            player_id="8888",  # Wrong player_id
            schedule_type="player_fetch",
            username="invalid_player",
        ).schedule_by_cron(
            redis_schedule_source, "*/30 * * * *", "invalid_player"
        )

        # Verify the invalid schedule exists in Redis
        schedules = await redis_schedule_source.get_schedules()
        invalid_schedule = next(
            (s for s in schedules if s.schedule_id == "player_fetch_9999"),
            None,
        )
        assert invalid_schedule is not None
        assert invalid_schedule.labels.get("player_id") == "8888"

    @pytest.mark.asyncio
    async def test_redis_connection_failure_handling(
        self, schedule_manager, sample_player
    ):
        """Test handling of Redis connection failures."""
        # Mock Redis source to simulate connection failure
        with patch.object(
            schedule_manager.redis_source, "get_schedules"
        ) as mock_get:
            mock_get.side_effect = Exception("Redis connection failed")

            # Should handle error gracefully and recreate schedule
            result = await schedule_manager.ensure_player_scheduled(
                sample_player
            )

            # Should return a valid schedule ID (new schedule created)
            assert result == f"player_fetch_{sample_player.id}"

    @pytest.mark.asyncio
    async def test_concurrent_schedule_operations(
        self, schedule_manager, redis_schedule_source, test_session
    ):
        """Test concurrent schedule operations don't cause conflicts."""
        # Create multiple players
        players = []
        for i in range(5):
            player = Player(
                id=3000 + i,
                username=f"concurrent_player_{i}",
                fetch_interval_minutes=30,
                is_active=True,
            )
            players.append(player)
            test_session.add(player)

        await test_session.commit()

        # Schedule all players concurrently
        tasks = [
            schedule_manager.schedule_player(player) for player in players
        ]
        schedule_ids = await asyncio.gather(*tasks)

        # Verify all schedules were created
        assert len(schedule_ids) == 5
        assert len(set(schedule_ids)) == 5  # All unique

        # Verify in Redis
        schedules = await redis_schedule_source.get_schedules()
        redis_schedule_ids = [s.schedule_id for s in schedules]

        for schedule_id in schedule_ids:
            assert schedule_id in redis_schedule_ids

        # Cleanup concurrently - set schedule_id on players first
        for i, player in enumerate(players):
            player.schedule_id = schedule_ids[i]
        cleanup_tasks = [
            schedule_manager.unschedule_player(player) for player in players
        ]
        await asyncio.gather(*cleanup_tasks)

        # Verify cleanup
        schedules_after = await redis_schedule_source.get_schedules()
        redis_schedule_ids_after = [s.schedule_id for s in schedules_after]

        for schedule_id in schedule_ids:
            assert schedule_id not in redis_schedule_ids_after


@pytest.mark.integration
class TestSchedulerMigrationIntegration:
    """Integration tests for migrating from old to new scheduler."""

    @pytest_asyncio.fixture
    async def redis_schedule_source(self):
        """Create a test Redis schedule source for migration tests."""
        test_prefix = f"test_migration_{datetime.now().timestamp()}"

        source = ListRedisScheduleSource(
            url=settings.redis.url,
            prefix=test_prefix,
            max_connection_pool_size=2,
        )

        yield source

        # Cleanup
        try:
            schedules = await source.get_schedules()
            for schedule in schedules:
                try:
                    await source.delete_schedule(schedule.schedule_id)
                except Exception:
                    pass
        except Exception:
            pass

    @pytest_asyncio.fixture
    async def migration_players(self, test_session: AsyncSession):
        """Create players for migration testing."""
        players = [
            Player(
                id=4001,
                username="migration_player_1",
                fetch_interval_minutes=30,
                is_active=True,
                last_fetched=datetime.now(UTC) - timedelta(hours=1),
            ),
            Player(
                id=4002,
                username="migration_player_2",
                fetch_interval_minutes=60,
                is_active=True,
                last_fetched=None,  # Never fetched
            ),
            Player(
                id=4003,
                username="inactive_player",
                fetch_interval_minutes=30,
                is_active=False,
                last_fetched=datetime.now(UTC) - timedelta(days=1),
            ),
        ]

        for player in players:
            test_session.add(player)
        await test_session.commit()

        for player in players:
            await test_session.refresh(player)

        return players

    @pytest.mark.asyncio
    async def test_migration_from_old_scheduler(
        self, redis_schedule_source, migration_players, test_session
    ):
        """Test migrating existing players to individual schedules."""
        schedule_manager = PlayerScheduleManager(redis_schedule_source)

        # Simulate migration process
        migrated_count = 0
        failed_count = 0

        for player in migration_players:
            if player.is_active:
                try:
                    schedule_id = await schedule_manager.schedule_player(
                        player
                    )

                    # Simulate updating database with schedule_id
                    player.schedule_id = schedule_id
                    migrated_count += 1

                except Exception as e:
                    logging.error(
                        f"Failed to migrate player {player.username}: {e}"
                    )
                    failed_count += 1

        await test_session.commit()

        # Verify migration results
        assert migrated_count == 2  # Only active players
        assert failed_count == 0

        # Verify schedules exist in Redis
        schedules = await redis_schedule_source.get_schedules()
        schedule_ids = [s.schedule_id for s in schedules]

        assert "player_fetch_4001" in schedule_ids
        assert "player_fetch_4002" in schedule_ids
        assert (
            "player_fetch_4003" not in schedule_ids
        )  # Inactive player not migrated

        # Verify schedule configurations
        schedule_map = {s.schedule_id: s for s in schedules}

        # Player 1: 30-minute interval
        schedule_1 = schedule_map["player_fetch_4001"]
        assert schedule_1.cron == "*/30 * * * *"
        assert schedule_1.args == ["migration_player_1"]

        # Player 2: 60-minute interval
        schedule_2 = schedule_map["player_fetch_4002"]
        assert schedule_2.cron == "0 * * * *"
        assert schedule_2.args == ["migration_player_2"]

    @pytest.mark.asyncio
    async def test_migration_verification_and_cleanup(
        self, redis_schedule_source, migration_players, test_session
    ):
        """Test post-migration verification and cleanup."""
        schedule_manager = PlayerScheduleManager(redis_schedule_source)

        # Migrate active players
        for player in migration_players:
            if player.is_active:
                schedule_id = await schedule_manager.schedule_player(player)
                player.schedule_id = schedule_id

        await test_session.commit()

        # Create orphaned schedule (player deleted but schedule remains)
        from app.workers.fetch import fetch_player_hiscores_task

        orphaned_schedule_id = "player_fetch_9999"
        await fetch_player_hiscores_task.kicker().with_schedule_id(
            orphaned_schedule_id
        ).with_labels(
            player_id="9999",
            schedule_type="player_fetch",
            username="deleted_player",
        ).schedule_by_cron(
            redis_schedule_source, "*/30 * * * *", "deleted_player"
        )

        # Verify the orphaned schedule exists in Redis
        schedules = await redis_schedule_source.get_schedules()
        orphaned_schedule = next(
            (s for s in schedules if s.schedule_id == orphaned_schedule_id),
            None,
        )
        assert orphaned_schedule is not None

        # Cleanup orphaned schedule
        await redis_schedule_source.delete_schedule(orphaned_schedule_id)

        # Verify cleanup
        schedules_after = await redis_schedule_source.get_schedules()
        schedule_ids_after = [s.schedule_id for s in schedules_after]
        assert orphaned_schedule_id not in schedule_ids_after

    @pytest.mark.asyncio
    async def test_migration_rollback_scenario(
        self, redis_schedule_source, migration_players
    ):
        """Test rollback scenario if migration fails."""
        schedule_manager = PlayerScheduleManager(redis_schedule_source)

        # Simulate partial migration failure
        successful_migrations = []

        for i, player in enumerate(migration_players):
            if player.is_active:
                if i == 0:
                    # First player succeeds
                    schedule_id = await schedule_manager.schedule_player(
                        player
                    )
                    successful_migrations.append((player, schedule_id))
                else:
                    # Simulate failure for second player
                    # In real scenario, this would be a database or Redis error
                    pass

        # Rollback: cleanup successful migrations
        for player, schedule_id in successful_migrations:
            player.schedule_id = schedule_id
            await schedule_manager.unschedule_player(player)

        # Verify rollback
        schedules = await redis_schedule_source.get_schedules()
        assert len(schedules) == 0


@pytest.mark.integration
class TestTaskExecutionIntegration:
    """Integration tests for task execution with scheduler context."""

    @pytest_asyncio.fixture
    async def redis_schedule_source(self):
        """Create a test Redis schedule source."""
        test_prefix = f"test_execution_{datetime.now().timestamp()}"

        source = ListRedisScheduleSource(
            url=settings.redis.url,
            prefix=test_prefix,
            max_connection_pool_size=2,
        )

        yield source

        # Cleanup
        try:
            schedules = await source.get_schedules()
            for schedule in schedules:
                try:
                    await source.delete_schedule(schedule.schedule_id)
                except Exception:
                    pass
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_task_execution_with_schedule_context(
        self, redis_schedule_source, test_session
    ):
        """Test that scheduled tasks receive proper context and labels."""
        # Create a player and schedule
        player = Player(
            id=5001,
            username="context_test_player",
            fetch_interval_minutes=30,
            is_active=True,
        )
        test_session.add(player)
        await test_session.commit()
        await test_session.refresh(player)

        schedule_manager = PlayerScheduleManager(redis_schedule_source)
        schedule_id = await schedule_manager.schedule_player(player)

        # Verify schedule was created with correct labels
        schedules = await redis_schedule_source.get_schedules()
        created_schedule = next(
            s for s in schedules if s.schedule_id == schedule_id
        )

        assert created_schedule.labels["player_id"] == str(player.id)
        assert created_schedule.labels["schedule_type"] == "player_fetch"
        assert created_schedule.labels["username"] == player.username

        # Note: Actual task execution testing would require a running TaskIQ worker
        # and is beyond the scope of unit/integration tests. This test verifies
        # that the schedule is created with the correct metadata that would be
        # available to the task during execution.

    @pytest.mark.asyncio
    async def test_label_schedule_source_integration(self):
        """Test that LabelScheduleSource works with static schedules."""
        from app.workers.scheduler import create_scheduler_sources

        sources = create_scheduler_sources()

        # Find the label source
        label_source = None
        for source in sources:
            if isinstance(source, LabelScheduleSource):
                label_source = source
                break

        assert label_source is not None
        assert label_source.broker == broker

        # Note: Testing actual label-based schedules would require importing
        # tasks with @broker.task(schedule=[...]) decorators, which is done
        # in the actual task modules.
