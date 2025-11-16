"""Settings cache service for accessing settings from database."""

import logging
from typing import Any, Dict, Optional

from app.config import settings as config_defaults
from app.models.base import AsyncSessionLocal
from app.services.setting import setting_service

logger = logging.getLogger(__name__)


class SettingsCache:
    """Cache for application settings loaded from database."""

    def __init__(self) -> None:
        """Initialize the settings cache."""
        self._cache: Dict[str, str] = {}
        self._initialized = False

    async def load_from_database(self) -> None:
        """Load all settings from database into cache."""
        try:
            async with AsyncSessionLocal() as db:
                self._cache = await setting_service.get_all_settings_dict(db)
                self._initialized = True
                logger.info(
                    f"Loaded {len(self._cache)} settings from database"
                )
        except Exception as e:
            logger.warning(f"Failed to load settings from database: {e}")
            logger.info("Using config.py defaults")
            self._initialized = False

    def refresh(self) -> None:
        """Mark cache as needing refresh (will reload on next access)."""
        self._initialized = False

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a setting value by key.

        Args:
            key: Setting key (e.g., 'database.url', 'jwt.secret_key')
            default: Default value if setting not found

        Returns:
            Setting value or default
        """
        if self._initialized and key in self._cache:
            return self._cache[key]
        # Fallback to config.py if not in cache
        return self._get_from_config(key, default)

    def _get_from_config(
        self, key: str, default: Optional[str] = None
    ) -> Optional[str]:
        """Get value from config.py using nested key path."""
        try:
            parts = key.split(".")
            value = config_defaults
            for part in parts:
                value = getattr(value, part)
            return str(value) if value is not None else default
        except AttributeError:
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean setting value."""
        value = self.get(key)
        if value is None:
            return default
        return value.lower() in ("true", "1", "yes", "on")

    def get_int(self, key: str, default: int = 0) -> int:
        """Get an integer setting value."""
        value = self.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get a float setting value."""
        value = self.get(key)
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    # Convenience methods for common setting groups

    @property
    def database_url(self) -> str:
        """Get database URL."""
        return self.get("database.url") or config_defaults.database.url

    @property
    def database_echo(self) -> bool:
        """Get database echo setting."""
        return self.get_bool("database.echo", config_defaults.database.echo)

    @property
    def database_pool_size(self) -> int:
        """Get database pool size."""
        return self.get_int(
            "database.pool_size", config_defaults.database.pool_size
        )

    @property
    def database_max_overflow(self) -> int:
        """Get database max overflow."""
        return self.get_int(
            "database.max_overflow", config_defaults.database.max_overflow
        )

    @property
    def database_pool_recycle(self) -> int:
        """Get database pool recycle."""
        return self.get_int(
            "database.pool_recycle", config_defaults.database.pool_recycle
        )

    @property
    def redis_url(self) -> str:
        """Get Redis URL."""
        return self.get("redis.url") or config_defaults.redis.url

    @property
    def redis_max_connections(self) -> int:
        """Get Redis max connections."""
        return self.get_int(
            "redis.max_connections", config_defaults.redis.max_connections
        )

    @property
    def jwt_secret_key(self) -> str:
        """Get JWT secret key."""
        return self.get("jwt.secret_key") or config_defaults.jwt.secret_key

    @property
    def jwt_algorithm(self) -> str:
        """Get JWT algorithm."""
        return self.get("jwt.algorithm") or config_defaults.jwt.algorithm

    @property
    def jwt_access_token_expire_minutes(self) -> int:
        """Get JWT access token expire minutes."""
        return self.get_int(
            "jwt.access_token_expire_minutes",
            config_defaults.jwt.access_token_expire_minutes,
        )

    @property
    def jwt_refresh_token_expire_days(self) -> int:
        """Get JWT refresh token expire days."""
        return self.get_int(
            "jwt.refresh_token_expire_days",
            config_defaults.jwt.refresh_token_expire_days,
        )

    @property
    def taskiq_default_retry_count(self) -> int:
        """Get TaskIQ default retry count."""
        return self.get_int(
            "taskiq.default_retry_count",
            config_defaults.taskiq.default_retry_count,
        )

    @property
    def taskiq_default_retry_delay(self) -> float:
        """Get TaskIQ default retry delay."""
        return self.get_float(
            "taskiq.default_retry_delay",
            config_defaults.taskiq.default_retry_delay,
        )

    @property
    def taskiq_use_jitter(self) -> bool:
        """Get TaskIQ use jitter setting."""
        return self.get_bool(
            "taskiq.use_jitter", config_defaults.taskiq.use_jitter
        )

    @property
    def taskiq_use_delay_exponent(self) -> bool:
        """Get TaskIQ use delay exponent setting."""
        return self.get_bool(
            "taskiq.use_delay_exponent",
            config_defaults.taskiq.use_delay_exponent,
        )

    @property
    def taskiq_max_delay_exponent(self) -> int:
        """Get TaskIQ max delay exponent."""
        return self.get_int(
            "taskiq.max_delay_exponent",
            int(config_defaults.taskiq.max_delay_exponent),
        )

    @property
    def taskiq_scheduler_prefix(self) -> str:
        """Get TaskIQ scheduler prefix."""
        return (
            self.get("taskiq.scheduler_prefix")
            or config_defaults.taskiq.scheduler_prefix
        )

    @property
    def admin_username(self) -> str:
        """Get admin username."""
        return self.get("admin.username") or config_defaults.admin.username

    @property
    def admin_password(self) -> str:
        """Get admin password."""
        return self.get("admin.password") or config_defaults.admin.password

    @property
    def admin_email(self) -> str:
        """Get admin email."""
        result = self.get("admin.email") or config_defaults.admin.email
        return result if result is not None else ""

    @property
    def openai_api_key(self) -> str:
        """Get OpenAI API key."""
        result = self.get("openai.api_key") or config_defaults.openai.api_key
        return result if result is not None else ""

    @property
    def openai_model(self) -> str:
        """Get OpenAI model."""
        return self.get("openai.model") or config_defaults.openai.model

    @property
    def openai_max_tokens(self) -> int:
        """Get OpenAI max tokens."""
        return self.get_int(
            "openai.max_tokens", config_defaults.openai.max_tokens
        )

    @property
    def openai_temperature(self) -> float:
        """Get OpenAI temperature."""
        return self.get_float(
            "openai.temperature", config_defaults.openai.temperature
        )

    @property
    def debug(self) -> bool:
        """Get debug setting."""
        return self.get_bool("debug", config_defaults.debug)

    @property
    def environment(self) -> str:
        """Get environment setting."""
        return self.get("environment") or config_defaults.environment

    @property
    def log_level(self) -> str:
        """Get log level setting."""
        return self.get("log_level") or config_defaults.log_level


# Global settings cache instance
settings_cache = SettingsCache()
