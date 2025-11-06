"""Tests for TaskIQ broker configuration."""

import pytest
from taskiq.middlewares import SimpleRetryMiddleware
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

from app.workers.main import broker, get_task_defaults


class TestTaskIQBroker:
    """Test TaskIQ broker configuration."""

    def test_broker_is_redis_broker(self):
        """Test that broker is configured as Redis broker."""
        assert isinstance(broker, RedisStreamBroker)

    def test_broker_has_result_backend(self):
        """Test that broker has Redis result backend configured."""
        assert isinstance(broker.result_backend, RedisAsyncResultBackend)

    def test_broker_has_retry_middleware(self):
        """Test that broker has retry middleware configured."""
        retry_middleware = None
        for middleware in broker.middlewares:
            if isinstance(middleware, SimpleRetryMiddleware):
                retry_middleware = middleware
                break

        assert retry_middleware is not None
        assert retry_middleware.default_retry_count == 3

    def test_get_task_defaults(self):
        """Test task defaults configuration."""
        defaults = get_task_defaults()

        assert defaults["retry_count"] == 3
        assert defaults["retry_delay"] == 2.0
        assert defaults["task_timeout"] == 300.0
        assert defaults["result_ttl"] == 3600

    def test_get_task_defaults_with_overrides(self):
        """Test task defaults with custom overrides."""
        defaults = get_task_defaults(
            retry_count=5, custom_setting="test_value"
        )

        assert defaults["retry_count"] == 5  # Overridden
        assert defaults["retry_delay"] == 2.0  # Default
        assert defaults["custom_setting"] == "test_value"  # Custom
