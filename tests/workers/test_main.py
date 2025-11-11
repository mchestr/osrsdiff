"""Tests for TaskIQ broker configuration."""

import pytest
from taskiq.middlewares import SmartRetryMiddleware
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

from app.workers.main import broker


class TestTaskIQBroker:
    """Test TaskIQ broker configuration."""

    def test_broker_is_redis_broker(self):
        """Test that broker is configured as Redis broker."""
        assert isinstance(broker, RedisStreamBroker)

    def test_broker_has_result_backend(self):
        """Test that broker has Redis result backend configured."""
        assert isinstance(broker.result_backend, RedisAsyncResultBackend)

    def test_broker_has_retry_middleware(self):
        """Test that broker has smart retry middleware configured."""
        retry_middleware = None
        for middleware in broker.middlewares:
            if isinstance(middleware, SmartRetryMiddleware):
                retry_middleware = middleware
                break

        assert retry_middleware is not None
        assert retry_middleware.default_retry_count == 3
