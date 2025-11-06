"""Tests for TaskIQ scheduler configuration."""

import pytest
from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import ListRedisScheduleSource

from app.workers.main import (
    broker,
    label_schedule_source,
    redis_schedule_source,
    scheduler,
)


class TestSchedulerConfiguration:
    """Test TaskIQ scheduler configuration."""

    def test_redis_schedule_source_configuration(self):
        """Test Redis schedule source is properly configured."""
        assert isinstance(redis_schedule_source, ListRedisScheduleSource)
        # ListRedisScheduleSource doesn't expose prefix directly, but we can verify it's configured

    def test_label_schedule_source_configuration(self):
        """Test label schedule source is properly configured."""
        assert isinstance(label_schedule_source, LabelScheduleSource)
        assert label_schedule_source.broker == broker

    def test_scheduler_configuration(self):
        """Test TaskiqScheduler is properly configured."""
        assert isinstance(scheduler, TaskiqScheduler)
        assert scheduler.broker == broker
        assert len(scheduler.sources) == 2

        # Verify sources are correct types
        source_types = [type(source) for source in scheduler.sources]
        assert ListRedisScheduleSource in source_types
        assert LabelScheduleSource in source_types

    def test_scheduler_has_correct_sources(self):
        """Test scheduler has the correct schedule sources."""
        # Find Redis and Label sources
        redis_source = None
        label_source = None

        for source in scheduler.sources:
            if isinstance(source, ListRedisScheduleSource):
                redis_source = source
            elif isinstance(source, LabelScheduleSource):
                label_source = source

        assert redis_source is not None, "Redis schedule source not found"
        assert label_source is not None, "Label schedule source not found"

        # Verify Label source configuration
        assert label_source.broker == broker
