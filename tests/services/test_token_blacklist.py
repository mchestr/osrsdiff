"""Tests for token blacklist service."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.auth import auth_service
from src.services.token_blacklist import TokenBlacklistService


class TestTokenBlacklistService:
    """Test cases for TokenBlacklistService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.blacklist_service = TokenBlacklistService()
        self.test_user_data = {
            "sub": "test_user",
            "username": "testuser",
            "user_id": 123,
        }

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        mock_redis = AsyncMock()
        return mock_redis

    async def test_blacklist_token(self, mock_redis):
        """Test blacklisting a token."""
        # Create a test token
        token = auth_service.create_access_token(self.test_user_data)

        # Mock Redis client
        self.blacklist_service._redis = mock_redis

        # Blacklist the token
        await self.blacklist_service.blacklist_token(token)

        # Verify Redis operations were called
        mock_redis.setex.assert_called_once()
        mock_redis.sadd.assert_called_once()
        mock_redis.expire.assert_called_once()

    async def test_is_token_blacklisted_true(self, mock_redis):
        """Test checking if a blacklisted token is blacklisted."""
        token = "test_token"

        # Mock Redis to return that token exists
        mock_redis.exists.return_value = 1
        self.blacklist_service._redis = mock_redis

        result = await self.blacklist_service.is_token_blacklisted(token)

        assert result is True
        mock_redis.exists.assert_called_once_with(f"blacklist:token:{token}")

    async def test_is_token_blacklisted_false(self, mock_redis):
        """Test checking if a non-blacklisted token is blacklisted."""
        token = "test_token"

        # Mock Redis to return that token doesn't exist
        mock_redis.exists.return_value = 0
        self.blacklist_service._redis = mock_redis

        result = await self.blacklist_service.is_token_blacklisted(token)

        assert result is False
        mock_redis.exists.assert_called_once_with(f"blacklist:token:{token}")

    async def test_is_token_blacklisted_redis_error(self):
        """Test that Redis errors don't break authentication."""
        token = "test_token"

        # Don't set up Redis client to simulate connection error
        result = await self.blacklist_service.is_token_blacklisted(token)

        # Should return False when Redis is unavailable
        assert result is False

    async def test_blacklist_user_tokens(self, mock_redis):
        """Test blacklisting all tokens for a user."""
        user_id = "test_user"
        tokens = ["token1", "token2", "token3"]

        # Mock Redis to return user tokens
        mock_redis.smembers.return_value = tokens
        self.blacklist_service._redis = mock_redis

        # Mock the blacklist_token method to avoid actual token processing
        original_blacklist = self.blacklist_service.blacklist_token
        self.blacklist_service.blacklist_token = AsyncMock()

        try:
            await self.blacklist_service.blacklist_user_tokens(user_id)

            # Verify all tokens were blacklisted
            assert self.blacklist_service.blacklist_token.call_count == len(
                tokens
            )

            # Verify user tokens set was deleted
            mock_redis.delete.assert_called_once_with(
                f"blacklist:user:{user_id}"
            )

        finally:
            # Restore original method
            self.blacklist_service.blacklist_token = original_blacklist

    async def test_cleanup_expired_tokens_redis_error(self):
        """Test cleanup when Redis is unavailable."""
        # Don't set up Redis client to simulate connection error
        result = await self.blacklist_service.cleanup_expired_tokens()

        # Should return 0 when Redis is unavailable
        assert result == 0

    async def test_get_redis_creates_connection(self):
        """Test that get_redis creates a connection if none exists."""
        # Ensure no existing connection
        self.blacklist_service._redis = None

        redis_client = await self.blacklist_service.get_redis()

        assert redis_client is not None
        assert self.blacklist_service._redis is not None

    async def test_close_redis_connection(self):
        """Test closing Redis connection."""
        # Set up a mock Redis connection
        mock_redis = AsyncMock()
        self.blacklist_service._redis = mock_redis

        await self.blacklist_service.close()

        mock_redis.close.assert_called_once()
        assert self.blacklist_service._redis is None
