from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as redis
from jose import jwt  # type: ignore

from app.config import settings


class TokenBlacklistService:
    """Service for managing blacklisted JWT tokens using Redis."""

    def __init__(self) -> None:
        """Initialize the token blacklist service."""
        self._redis: Optional[redis.Redis] = None
        self.redis_url = settings.redis.url
        self.max_connections = settings.redis.max_connections
        self.jwt_secret = settings.jwt.secret_key
        self.jwt_algorithm = settings.jwt.algorithm

    async def get_redis(self) -> redis.Redis:
        """Get Redis connection, creating it if necessary."""
        if self._redis is None:
            self._redis = redis.from_url(
                self.redis_url,
                max_connections=self.max_connections,
                decode_responses=True,
            )
        return self._redis

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None

    def _get_token_key(self, token: str) -> str:
        """Generate Redis key for a token."""
        return f"blacklist:token:{token}"

    def _get_user_tokens_key(self, user_id: str) -> str:
        """Generate Redis key for user's tokens."""
        return f"blacklist:user:{user_id}"

    async def blacklist_token(self, token: str) -> None:
        """
        Add a token to the blacklist.

        Args:
            token: The JWT token to blacklist
        """
        try:
            # Decode token to get expiration time
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
                options={
                    "verify_exp": False
                },  # Don't verify expiration for blacklisting
            )

            exp = payload.get("exp")
            if exp is None:
                # If no expiration, set a default TTL of 24 hours
                ttl = 86400
            else:
                # Calculate TTL based on token expiration
                exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
                now = datetime.now(timezone.utc)
                ttl = max(int((exp_datetime - now).total_seconds()), 0)

            # Only blacklist if token hasn't already expired
            if ttl > 0:
                redis_client = await self.get_redis()
                token_key = self._get_token_key(token)

                # Store token in blacklist with TTL matching token expiration
                await redis_client.setex(token_key, ttl, "blacklisted")

                # Also add to user's token set for bulk operations
                user_id = payload.get("sub") or payload.get(
                    "user_id", "unknown"
                )
                user_tokens_key = self._get_user_tokens_key(str(user_id))
                await redis_client.sadd(user_tokens_key, token)
                await redis_client.expire(user_tokens_key, ttl)

        except Exception:
            # If we can't decode the token, still try to blacklist it
            # with a default TTL
            redis_client = await self.get_redis()
            token_key = self._get_token_key(token)
            await redis_client.setex(token_key, 86400, "blacklisted")

    async def is_token_blacklisted(self, token: str) -> bool:
        """
        Check if a token is blacklisted.

        Args:
            token: The JWT token to check

        Returns:
            True if token is blacklisted, False otherwise
        """
        try:
            redis_client = await self.get_redis()
            token_key = self._get_token_key(token)
            result = await redis_client.exists(token_key)
            return bool(result)
        except Exception:
            # If Redis is unavailable, assume token is not blacklisted
            # This prevents Redis outages from breaking authentication
            return False

    async def blacklist_user_tokens(self, user_id: str) -> None:
        """
        Blacklist all tokens for a specific user.

        Args:
            user_id: The user ID whose tokens should be blacklisted
        """
        try:
            redis_client = await self.get_redis()
            user_tokens_key = self._get_user_tokens_key(user_id)

            # Get all tokens for the user
            tokens = set(await redis_client.smembers(user_tokens_key))

            # Blacklist each token
            for token in tokens:
                await self.blacklist_token(token)

            # Remove the user tokens set
            await redis_client.delete(user_tokens_key)

        except Exception:
            # If Redis operations fail, continue silently
            pass

    async def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired tokens from the blacklist.

        This method is primarily for maintenance and monitoring.
        Redis TTL should handle most cleanup automatically.

        Returns:
            Number of tokens cleaned up
        """
        try:
            redis_client = await self.get_redis()

            # Get all blacklist keys
            pattern = "blacklist:token:*"
            keys = []
            async for key in redis_client.scan_iter(match=pattern):
                keys.append(key)

            if not keys:
                return 0

            # Check which keys have expired (TTL = -2)
            expired_keys = []
            for key in keys:
                ttl = int(await redis_client.ttl(key))
                if ttl == -2:  # Key doesn't exist (expired)
                    expired_keys.append(key)

            return len(expired_keys)

        except Exception:
            return 0


# Global token blacklist service instance
token_blacklist_service = TokenBlacklistService()
