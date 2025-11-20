import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.models.base import AsyncSessionLocal
from app.models.setting import Setting

logger = logging.getLogger(__name__)


class SettingService:
    """Service for managing application settings with caching support."""

    def __init__(self) -> None:
        """Initialize the setting service with cache."""
        self._cache: Dict[str, str] = {}
        self._initialized = False

    async def load_cache_from_database(self) -> None:
        """Load all settings from database into cache."""
        try:
            async with AsyncSessionLocal() as db:
                self._cache = await self.get_all_settings_dict(db)
                self._initialized = True
                logger.info(
                    f"Loaded {len(self._cache)} settings from database into cache"
                )
        except Exception as e:
            logger.warning(f"Failed to load settings from database: {e}")
            logger.info("Using config.py defaults")
            self._initialized = False

    async def load_from_database(self) -> None:
        """Alias for load_cache_from_database for backward compatibility."""
        await self.load_cache_from_database()

    def refresh(self) -> None:
        """Mark cache as needing refresh (will reload on next access)."""
        self._initialized = False

    def refresh_cache(self) -> None:
        """Alias for refresh for backward compatibility."""
        self.refresh()

    def _get_from_config(
        self, key: str, default: Optional[str] = None
    ) -> Optional[str]:
        """Get value from config.py using nested key path."""
        try:
            parts = key.split(".")
            value = app_settings
            for part in parts:
                value = getattr(value, part)
            return str(value) if value is not None else default
        except AttributeError:
            return default

    def get_cached(
        self, key: str, default: Optional[str] = None
    ) -> Optional[str]:
        """
        Get a setting value by key from cache, falling back to config.

        Args:
            key: Setting key (e.g., 'database.url', 'jwt.secret_key')
            default: Default value if setting not found

        Returns:
            Setting value or default
        """
        if self._initialized:
            # Try exact key first
            if key in self._cache:
                return self._cache[key]
            # Try underscore version (for OpenAI settings stored as openai_enabled)
            underscore_key = key.replace(".", "_")
            if underscore_key in self._cache:
                return self._cache[underscore_key]
        # Fallback to config.py if not in cache
        return self._get_from_config(key, default)

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Alias for get_cached for backward compatibility."""
        return self.get_cached(key, default)

    def get_cached_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean setting value from cache."""
        value = self.get_cached(key)
        if value is None:
            return default
        return value.lower() in ("true", "1", "yes", "on")

    def get_cached_int(self, key: str, default: int = 0) -> int:
        """Get an integer setting value from cache."""
        value = self.get_cached(key)
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def get_cached_float(self, key: str, default: float = 0.0) -> float:
        """Get a float setting value from cache."""
        value = self.get_cached(key)
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    # Convenience properties for common setting groups
    @property
    def database_url(self) -> str:
        """Get database URL."""
        return self.get_cached("database.url") or app_settings.database.url

    @property
    def database_echo(self) -> bool:
        """Get database echo setting."""
        return self.get_cached_bool(
            "database.echo", app_settings.database.echo
        )

    @property
    def database_pool_size(self) -> int:
        """Get database pool size."""
        return self.get_cached_int(
            "database.pool_size", app_settings.database.pool_size
        )

    @property
    def database_max_overflow(self) -> int:
        """Get database max overflow."""
        return self.get_cached_int(
            "database.max_overflow", app_settings.database.max_overflow
        )

    @property
    def database_pool_recycle(self) -> int:
        """Get database pool recycle."""
        return self.get_cached_int(
            "database.pool_recycle", app_settings.database.pool_recycle
        )

    @property
    def redis_url(self) -> str:
        """Get Redis URL."""
        return self.get_cached("redis.url") or app_settings.redis.url

    @property
    def redis_max_connections(self) -> int:
        """Get Redis max connections."""
        return self.get_cached_int(
            "redis.max_connections", app_settings.redis.max_connections
        )

    @property
    def jwt_secret_key(self) -> str:
        """Get JWT secret key."""
        return self.get_cached("jwt.secret_key") or app_settings.jwt.secret_key

    @property
    def jwt_algorithm(self) -> str:
        """Get JWT algorithm."""
        return self.get_cached("jwt.algorithm") or app_settings.jwt.algorithm

    @property
    def jwt_access_token_expire_minutes(self) -> int:
        """Get JWT access token expire minutes."""
        return self.get_cached_int(
            "jwt.access_token_expire_minutes",
            app_settings.jwt.access_token_expire_minutes,
        )

    @property
    def jwt_refresh_token_expire_days(self) -> int:
        """Get JWT refresh token expire days."""
        return self.get_cached_int(
            "jwt.refresh_token_expire_days",
            app_settings.jwt.refresh_token_expire_days,
        )

    @property
    def taskiq_default_retry_count(self) -> int:
        """Get TaskIQ default retry count."""
        return self.get_cached_int(
            "taskiq.default_retry_count",
            app_settings.taskiq.default_retry_count,
        )

    @property
    def taskiq_default_retry_delay(self) -> float:
        """Get TaskIQ default retry delay."""
        return self.get_cached_float(
            "taskiq.default_retry_delay",
            app_settings.taskiq.default_retry_delay,
        )

    @property
    def taskiq_use_jitter(self) -> bool:
        """Get TaskIQ use jitter setting."""
        return self.get_cached_bool(
            "taskiq.use_jitter", app_settings.taskiq.use_jitter
        )

    @property
    def taskiq_use_delay_exponent(self) -> bool:
        """Get TaskIQ use delay exponent setting."""
        return self.get_cached_bool(
            "taskiq.use_delay_exponent",
            app_settings.taskiq.use_delay_exponent,
        )

    @property
    def taskiq_max_delay_exponent(self) -> int:
        """Get TaskIQ max delay exponent."""
        return self.get_cached_int(
            "taskiq.max_delay_exponent",
            int(app_settings.taskiq.max_delay_exponent),
        )

    @property
    def taskiq_scheduler_prefix(self) -> str:
        """Get TaskIQ scheduler prefix."""
        return (
            self.get_cached("taskiq.scheduler_prefix")
            or app_settings.taskiq.scheduler_prefix
        )

    @property
    def admin_username(self) -> str:
        """Get admin username."""
        return self.get_cached("admin.username") or app_settings.admin.username

    @property
    def admin_password(self) -> str:
        """Get admin password."""
        return self.get_cached("admin.password") or app_settings.admin.password

    @property
    def admin_email(self) -> str:
        """Get admin email."""
        result = self.get_cached("admin.email") or app_settings.admin.email
        return result if result is not None else ""

    @property
    def openai_enabled(self) -> bool:
        """Get OpenAI enabled setting."""
        return self.get_cached_bool(
            "openai.enabled", app_settings.openai.enabled
        )

    @property
    def openai_api_key(self) -> str:
        """Get OpenAI API key."""
        result = (
            self.get_cached("openai.api_key") or app_settings.openai.api_key
        )
        return result if result is not None else ""

    @property
    def openai_model(self) -> str:
        """Get OpenAI model."""
        return self.get_cached("openai.model") or app_settings.openai.model

    @property
    def openai_max_tokens(self) -> int:
        """Get OpenAI max tokens."""
        return self.get_cached_int(
            "openai.max_tokens", app_settings.openai.max_tokens
        )

    @property
    def openai_temperature(self) -> float:
        """Get OpenAI temperature."""
        return self.get_cached_float(
            "openai.temperature", app_settings.openai.temperature
        )

    @property
    def debug(self) -> bool:
        """Get debug setting."""
        return self.get_cached_bool("debug", app_settings.debug)

    @property
    def environment(self) -> str:
        """Get environment setting."""
        return self.get_cached("environment") or app_settings.environment

    @property
    def log_level(self) -> str:
        """Get log level setting."""
        return self.get_cached("log_level") or app_settings.log_level

    async def get_setting(
        self, db: AsyncSession, key: str
    ) -> Optional[Setting]:
        """Get a setting by key."""
        result = await db.execute(select(Setting).where(Setting.key == key))
        return result.scalar_one_or_none()

    async def get_setting_value(
        self, db: AsyncSession, key: str, default: Optional[str] = None
    ) -> Optional[str]:
        """Get a setting value by key, returning default if not found."""
        setting = await self.get_setting(db, key)
        if setting:
            return setting.value
        return default

    async def get_all_settings(self, db: AsyncSession) -> List[Setting]:
        """Get all settings."""
        result = await db.execute(select(Setting).order_by(Setting.key))
        return list(result.scalars().all())

    async def get_all_settings_dict(self, db: AsyncSession) -> Dict[str, str]:
        """Get all settings as a dictionary."""
        settings = await self.get_all_settings(db)
        return {setting.key: setting.value for setting in settings}

    async def create_or_update_setting(
        self,
        db: AsyncSession,
        key: str,
        value: str,
        description: Optional[str] = None,
        display_name: Optional[str] = None,
        setting_type: Optional[str] = None,
        allowed_values: Optional[str] = None,
        is_secret: Optional[bool] = None,
    ) -> Setting:
        """Create or update a setting."""
        setting = await self.get_setting(db, key)
        if setting:
            setting.value = value
            if description is not None:
                setting.description = description
            if display_name is not None:
                setting.display_name = display_name
            if setting_type is not None:
                setting.setting_type = setting_type
            if allowed_values is not None:
                setting.allowed_values = allowed_values
            if is_secret is not None:
                setting.is_secret = is_secret
        else:
            # Generate display_name if not provided
            if display_name is None:
                display_name = self._generate_display_name(key)
            # Infer type if not provided
            if setting_type is None:
                setting_type = self._infer_setting_type(key, value)
            # Auto-detect secret if not explicitly provided
            if is_secret is None:
                is_secret = self._is_secret_setting(key)
            setting = Setting(
                key=key,
                value=value,
                description=description,
                display_name=display_name,
                setting_type=setting_type,
                allowed_values=allowed_values,
                is_secret=is_secret,
            )
            db.add(setting)

        await db.commit()
        await db.refresh(setting)
        # Update cache if initialized
        if self._initialized:
            self._cache[setting.key] = setting.value
        return setting

    def _infer_setting_type(self, key: str, value: str) -> str:
        """Infer setting type from key and value."""
        # Check for boolean patterns
        if value.lower() in (
            "true",
            "false",
            "1",
            "0",
            "yes",
            "no",
            "on",
            "off",
        ):
            return "boolean"

        # Check for enum patterns in key
        enum_keys = ["environment", "log_level", "jwt_algorithm"]
        if any(enum_key in key for enum_key in enum_keys):
            return "enum"

        # Check if it's a number
        try:
            float(value)
            # Check if it's an integer
            if "." not in value:
                return "number"
            return "number"
        except ValueError:
            pass

        return "string"

    def _is_secret_setting(self, key: str) -> bool:
        """Determine if a setting should be marked as secret based on its key."""
        secret_keywords = [
            "password",
            "secret",
            "api_key",
            "token",
            "key",
            "credential",
            "auth",
            "private",
            "database_url",
            "redis_url",
        ]
        key_lower = key.lower()
        return any(keyword in key_lower for keyword in secret_keywords)

    def _generate_display_name(self, key: str) -> str:
        """Generate a friendly display name from a setting key."""
        # Replace underscores with spaces and title case
        display_name = key.replace("_", " ").title()
        # Handle common prefixes
        if display_name.startswith("Openai "):
            display_name = display_name.replace("Openai ", "OpenAI ")
        if display_name.startswith("Jwt "):
            display_name = display_name.replace("Jwt ", "JWT ")
        # Handle common abbreviations
        display_name = display_name.replace("Api ", "API ")
        display_name = display_name.replace("Id ", "ID ")
        return display_name

    async def delete_setting(self, db: AsyncSession, key: str) -> bool:
        """Delete a setting by key."""
        setting = await self.get_setting(db, key)
        if setting:
            await db.delete(setting)
            await db.commit()
            # Remove from cache if initialized
            if self._initialized and key in self._cache:
                del self._cache[key]
            return True
        return False

    async def reset_setting_to_default(
        self, db: AsyncSession, key: str
    ) -> Optional[Setting]:
        """Reset a setting to its default value from config.py."""
        setting = await self.get_setting(db, key)
        if not setting:
            return None

        # Get the config path for this key
        config_path = self._get_config_path_for_key(key)
        if not config_path:
            # If no config path found, can't reset
            return None

        # Get default value from config
        default_value = self._get_nested_config_value(
            app_settings, config_path
        )
        if default_value is None:
            # If no default value found, can't reset
            return None

        # Convert to string
        default_value_str = str(default_value)

        # Update the setting with the default value
        setting.value = default_value_str
        await db.commit()
        await db.refresh(setting)
        return setting

    def _get_all_config_settings(self) -> List[tuple]:
        """Get all configurable settings from config.py."""
        # Format: (key, env_var_path, display_name, description, setting_type, allowed_values)
        return [
            # Environment settings
            (
                "environment",
                "environment",
                "Environment",
                "Application environment (development, production, etc.)",
                "enum",
                json.dumps(
                    ["development", "production", "staging", "testing"]
                ),
            ),
            (
                "debug",
                "debug",
                "Debug Mode",
                "Enable debug mode",
                "boolean",
                None,
            ),
            (
                "log_level",
                "log_level",
                "Log Level",
                "Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
                "enum",
                json.dumps(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
            ),
            # Database settings
            (
                "database_url",
                "database.url",
                "Database URL",
                "Database connection URL",
                "string",
                None,
            ),
            (
                "database_echo",
                "database.echo",
                "Database Echo",
                "Enable SQLAlchemy query logging",
                "boolean",
                None,
            ),
            (
                "database_pool_size",
                "database.pool_size",
                "Database Pool Size",
                "Database connection pool size",
                "number",
                None,
            ),
            (
                "database_max_overflow",
                "database.max_overflow",
                "Database Max Overflow",
                "Maximum overflow connections",
                "number",
                None,
            ),
            (
                "database_pool_recycle",
                "database.pool_recycle",
                "Database Pool Recycle",
                "Connection recycle time in seconds",
                "number",
                None,
            ),
            # Redis settings
            (
                "redis_url",
                "redis.url",
                "Redis URL",
                "Redis connection URL",
                "string",
                None,
            ),
            (
                "redis_max_connections",
                "redis.max_connections",
                "Redis Max Connections",
                "Maximum Redis connections in pool",
                "number",
                None,
            ),
            # JWT settings
            (
                "jwt_secret_key",
                "jwt.secret_key",
                "JWT Secret Key",
                "Secret key for JWT token signing",
                "string",
                None,
            ),
            (
                "jwt_algorithm",
                "jwt.algorithm",
                "JWT Algorithm",
                "JWT signing algorithm",
                "enum",
                json.dumps(
                    ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
                ),
            ),
            (
                "jwt_access_token_expire_minutes",
                "jwt.access_token_expire_minutes",
                "Access Token Expiration (Minutes)",
                "Access token expiration time in minutes",
                "number",
                None,
            ),
            (
                "jwt_refresh_token_expire_days",
                "jwt.refresh_token_expire_days",
                "Refresh Token Expiration (Days)",
                "Refresh token expiration time in days",
                "number",
                None,
            ),
            # Admin settings
            (
                "admin_username",
                "admin.username",
                "Admin Username",
                "Default admin username",
                "string",
                None,
            ),
            (
                "admin_password",
                "admin.password",
                "Admin Password",
                "Default admin password",
                "string",
                None,
            ),
            (
                "admin_email",
                "admin.email",
                "Admin Email",
                "Default admin email",
                "string",
                None,
            ),
            # OpenAI settings
            (
                "openai_enabled",
                "openai.enabled",
                "OpenAI Enabled",
                "Enable OpenAI functionality for summary generation",
                "boolean",
                None,
            ),
            (
                "openai_api_key",
                "openai.api_key",
                "OpenAI API Key",
                "OpenAI API key for generating summaries",
                "string",
                None,
            ),
            (
                "openai_model",
                "openai.model",
                "OpenAI Model",
                "OpenAI model to use for summary generation",
                "string",
                None,
            ),
            (
                "openai_max_tokens",
                "openai.max_tokens",
                "Max Tokens",
                "Maximum tokens for summary generation",
                "number",
                None,
            ),
            (
                "openai_temperature",
                "openai.temperature",
                "Temperature",
                "Temperature for summary generation (0.0-1.0)",
                "number",
                None,
            ),
        ]

    async def initialize_from_config(self, db: AsyncSession) -> None:
        """Initialize all settings from config.py if they don't exist."""
        config_settings = self._get_all_config_settings()
        initialized_count = 0

        for (
            key,
            config_path,
            display_name,
            description,
            setting_type,
            allowed_values,
        ) in config_settings:
            # Check if setting already exists
            existing = await self.get_setting(db, key)
            if existing:
                # Update display_name and type if missing
                updated = False
                if not existing.display_name:
                    existing.display_name = display_name
                    updated = True
                if (
                    not existing.setting_type
                    or existing.setting_type == "string"
                ):
                    existing.setting_type = setting_type
                    updated = True
                if not existing.allowed_values and allowed_values:
                    existing.allowed_values = allowed_values
                    updated = True
                # Auto-detect and update is_secret if not set
                if not existing.is_secret and self._is_secret_setting(key):
                    existing.is_secret = True
                    updated = True
                if updated:
                    await db.commit()
                continue

            # Get value from nested config path
            value = self._get_nested_config_value(app_settings, config_path)
            if value is None:
                continue

            # Convert value to string
            value_str = str(value)

            # Create setting with display_name, type, and allowed_values
            await self.create_or_update_setting(
                db,
                key,
                value_str,
                description,
                display_name,
                setting_type,
                allowed_values,
            )
            initialized_count += 1
            logger.debug(f"Initialized setting '{key}' from config")

        if initialized_count > 0:
            logger.info(
                f"Initialized {initialized_count} settings from config"
            )

    def _get_config_path_for_key(self, key: str) -> Optional[str]:
        """Get the config path for a setting key."""
        # Map keys to config paths
        key_mapping = {
            "environment": "environment",
            "debug": "debug",
            "log_level": "log_level",
            "database_url": "database.url",
            "database_echo": "database.echo",
            "database_pool_size": "database.pool_size",
            "database_max_overflow": "database.max_overflow",
            "database_pool_recycle": "database.pool_recycle",
            "redis_url": "redis.url",
            "redis_max_connections": "redis.max_connections",
            "jwt_secret_key": "jwt.secret_key",
            "jwt_algorithm": "jwt.algorithm",
            "jwt_access_token_expire_minutes": "jwt.access_token_expire_minutes",
            "jwt_refresh_token_expire_days": "jwt.refresh_token_expire_days",
            "admin_username": "admin.username",
            "admin_password": "admin.password",
            "admin_email": "admin.email",
            "openai_enabled": "openai.enabled",
            "openai_api_key": "openai.api_key",
            "openai_model": "openai.model",
            "openai_max_tokens": "openai.max_tokens",
            "openai_temperature": "openai.temperature",
            "openai_model": "openai.model",
            "openai_max_tokens": "openai.max_tokens",
            "openai_temperature": "openai.temperature",
        }
        return key_mapping.get(key)

    def _get_nested_config_value(
        self, config_obj: object, path: str
    ) -> Optional[object]:
        """Get a nested config value by dot-separated path."""
        parts = path.split(".")
        current = config_obj
        for part in parts:
            if not hasattr(current, part):
                return None
            current = getattr(current, part)
        return current


# Global setting service instance
setting_service = SettingService()

# Alias for backward compatibility
settings_cache = setting_service
