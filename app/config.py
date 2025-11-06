"""Application configuration."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogConfig(BaseModel):
    """Logging configuration to be set for the server"""

    LOGGER_NAME: str = "app"
    LOG_FORMAT: str = "%(levelprefix)s | %(asctime)s | %(message)s"
    LOG_LEVEL: str = "DEBUG"
    version: int = 1
    disable_existing_loggers: bool = False

    formatters: dict = Field(
        default_factory=lambda: {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(levelprefix)s | %(asctime)s | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "access": {
                "()": "uvicorn.logging.AccessFormatter",
                "fmt": '%(levelprefix)s %(asctime)s :: %(client_addr)s - "%(request_line)s" %(status_code)s',
                "use_colors": True,
            },
            "error": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(levelprefix)s | %(asctime)s | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        }
    )

    handlers: dict = Field(
        default_factory=lambda: {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
            "error": {
                "formatter": "error",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
        }
    )

    loggers: dict = Field(
        default_factory=lambda: {
            "": {"handlers": ["default"], "level": "DEBUG", "propagate": True},
            "app": {"level": "DEBUG"},
            "uvicorn.access": {"handlers": ["access"], "level": "DEBUG", "propagate": False},
            "uvicorn.error": {"handlers": ["error"], "level": "DEBUG"},
        }
    )


class DatabaseSettings(BaseModel):
    """Database configuration settings."""

    url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/osrsdiff",
        description="Database connection URL",
    )
    echo: bool = Field(
        default=False, description="Enable SQLAlchemy query logging"
    )
    pool_size: int = Field(
        default=10, description="Database connection pool size"
    )
    max_overflow: int = Field(
        default=20, description="Maximum overflow connections"
    )
    pool_recycle: int = Field(
        default=3600, description="Connection recycle time in seconds"
    )

    @field_validator("url", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        """Ensure asyncpg driver is used for PostgreSQL URLs."""
        if isinstance(v, str):
            if v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
            if "postgresql" in v and "+asyncpg" not in v:
                return v.replace("postgresql", "postgresql+asyncpg", 1)
        return v


class RedisSettings(BaseModel):
    """Redis configuration settings."""

    url: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )
    max_connections: int = Field(
        default=10, description="Maximum Redis connections in pool"
    )


class JWTSettings(BaseModel):
    """JWT authentication configuration settings."""

    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for JWT token signing",
    )
    algorithm: str = Field(
        default="HS256", description="JWT signing algorithm"
    )
    access_token_expire_minutes: int = Field(
        default=15, description="Access token expiration time in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=7, description="Refresh token expiration time in days"
    )


class TaskIQSettings(BaseModel):
    """TaskIQ configuration settings."""

    default_retry_count: int = Field(
        default=3, description="Default number of task retries"
    )
    default_retry_delay: float = Field(
        default=2.0, description="Default retry delay in seconds"
    )
    max_retry_delay: float = Field(
        default=60.0, description="Maximum retry delay in seconds"
    )
    task_timeout: float = Field(
        default=300.0, description="Default task timeout in seconds"
    )
    result_ttl: int = Field(
        default=3600, description="Task result TTL in seconds"
    )
    worker_concurrency: int = Field(
        default=4, description="Number of concurrent tasks per worker"
    )
    scheduler_prefix: str = Field(
        default="app:schedules",
        description="Redis prefix for TaskIQ schedules",
    )


class AdminSettings(BaseModel):
    """Admin user configuration settings."""

    username: str = Field(
        default="admin", description="Default admin username"
    )
    password: str = Field(
        default="admin", description="Default admin password"
    )
    email: Optional[str] = Field(
        default=None, description="Default admin email"
    )


class Settings(BaseSettings):
    """Application settings.

    Uses double underscore (__) separator for nested env vars.
    Example: DATABASE__URL, REDIS__URL, JWT__SECRET_KEY
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter="__",
    )

    environment: str = Field(
        default="development", description="Application environment"
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    jwt: JWTSettings = Field(default_factory=JWTSettings)
    taskiq: TaskIQSettings = Field(default_factory=TaskIQSettings)
    admin: AdminSettings = Field(default_factory=AdminSettings)

    @model_validator(mode="after")
    def set_debug_from_environment(self) -> "Settings":
        """Set debug mode based on environment if not explicitly set."""
        if not self.debug:
            self.debug = self.environment.lower() != "production"
        return self


# Global settings instance
settings = Settings()
