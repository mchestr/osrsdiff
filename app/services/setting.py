import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.models.setting import Setting

logger = logging.getLogger(__name__)


class SettingService:
    """Service for managing application settings."""

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
            # TaskIQ settings
            (
                "taskiq_default_retry_count",
                "taskiq.default_retry_count",
                "TaskIQ Default Retry Count",
                "Default number of task retries",
                "number",
                None,
            ),
            (
                "taskiq_default_retry_delay",
                "taskiq.default_retry_delay",
                "TaskIQ Default Retry Delay",
                "Default retry delay in seconds (base for exponential backoff)",
                "number",
                None,
            ),
            (
                "taskiq_max_retry_delay",
                "taskiq.max_retry_delay",
                "TaskIQ Max Retry Delay",
                "Maximum retry delay in seconds",
                "number",
                None,
            ),
            (
                "taskiq_task_timeout",
                "taskiq.task_timeout",
                "TaskIQ Task Timeout",
                "Default task timeout in seconds",
                "number",
                None,
            ),
            (
                "taskiq_result_ttl",
                "taskiq.result_ttl",
                "TaskIQ Result TTL",
                "Task result TTL in seconds",
                "number",
                None,
            ),
            (
                "taskiq_worker_concurrency",
                "taskiq.worker_concurrency",
                "TaskIQ Worker Concurrency",
                "Number of concurrent tasks per worker",
                "number",
                None,
            ),
            (
                "taskiq_scheduler_prefix",
                "taskiq.scheduler_prefix",
                "TaskIQ Scheduler Prefix",
                "Redis prefix for TaskIQ schedules",
                "string",
                None,
            ),
            (
                "taskiq_use_jitter",
                "taskiq.use_jitter",
                "TaskIQ Use Jitter",
                "Enable jitter to distribute retries evenly",
                "boolean",
                None,
            ),
            (
                "taskiq_use_delay_exponent",
                "taskiq.use_delay_exponent",
                "TaskIQ Use Delay Exponent",
                "Enable exponential backoff for retries",
                "boolean",
                None,
            ),
            (
                "taskiq_max_delay_exponent",
                "taskiq.max_delay_exponent",
                "TaskIQ Max Delay Exponent",
                "Maximum delay exponent in seconds for exponential backoff",
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

    async def load_settings_to_config(self, db: AsyncSession) -> None:
        """Load settings from database and apply them to the config object."""
        settings_dict = await self.get_all_settings_dict(db)

        if not settings_dict:
            logger.debug(
                "No settings found in database, using config defaults"
            )
            return

        applied_count = 0
        for key, value in settings_dict.items():
            try:
                # Map setting keys to config paths
                config_path = self._get_config_path_for_key(key)
                if config_path:
                    self._set_nested_config_value(
                        app_settings, config_path, value
                    )
                    applied_count += 1
                    logger.debug(f"Applied setting '{key}' to config")
            except Exception as e:
                logger.warning(
                    f"Failed to apply setting '{key}' to config: {e}"
                )

        if applied_count > 0:
            logger.info(
                f"Applied {applied_count} settings from database to config"
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
            "taskiq_default_retry_count": "taskiq.default_retry_count",
            "taskiq_default_retry_delay": "taskiq.default_retry_delay",
            "taskiq_max_retry_delay": "taskiq.max_retry_delay",
            "taskiq_task_timeout": "taskiq.task_timeout",
            "taskiq_result_ttl": "taskiq.result_ttl",
            "taskiq_worker_concurrency": "taskiq.worker_concurrency",
            "taskiq_scheduler_prefix": "taskiq.scheduler_prefix",
            "taskiq_use_jitter": "taskiq.use_jitter",
            "taskiq_use_delay_exponent": "taskiq.use_delay_exponent",
            "taskiq_max_delay_exponent": "taskiq.max_delay_exponent",
            "admin_username": "admin.username",
            "admin_password": "admin.password",
            "admin_email": "admin.email",
            "openai_api_key": "openai.api_key",
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

    def _set_nested_config_value(
        self, config_obj: object, path: str, value: Any
    ) -> None:
        """Set a nested config value by dot-separated path."""
        parts = path.split(".")
        current = config_obj

        # Navigate to the parent object
        for part in parts[:-1]:
            if not hasattr(current, part):
                raise ValueError(f"Config path '{path}' is invalid")
            current = getattr(current, part)

        # Set the value on the final object
        final_key = parts[-1]
        if not hasattr(current, final_key):
            raise ValueError(f"Config path '{path}' is invalid")

        # Convert value to appropriate type based on current value
        current_value = getattr(current, final_key)
        if isinstance(current_value, bool):
            value = value.lower() in ("true", "1", "yes", "on")
        elif isinstance(current_value, int):
            value = int(value)
        elif isinstance(current_value, float):
            value = float(value)
        elif isinstance(current_value, str):
            value = str(value)
        # For Optional types, handle None
        elif current_value is None:
            if value.lower() in ("none", "null", ""):
                value = None
            else:
                value = str(value)

        setattr(current, final_key, value)


# Global setting service instance
setting_service = SettingService()
