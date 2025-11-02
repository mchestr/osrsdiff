"""Application configuration."""

import os
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


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


class Settings(BaseSettings):
    """Application settings."""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }

    # Environment
    environment: str = Field(
        default="development", description="Application environment"
    )
    debug: bool = Field(default=False, description="Enable debug mode")

    # Database settings
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/osrsdiff",
        description="Database connection URL",
    )
    database_echo: bool = Field(
        default=False, description="Enable SQLAlchemy query logging"
    )
    database_pool_size: int = Field(
        default=10, description="Database connection pool size"
    )
    database_max_overflow: int = Field(
        default=20, description="Maximum overflow connections"
    )
    database_pool_recycle: int = Field(
        default=3600, description="Connection recycle time in seconds"
    )

    # Redis settings
    redis_url: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )
    redis_max_connections: int = Field(
        default=10, description="Maximum Redis connections in pool"
    )

    # JWT settings
    jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for JWT token signing",
    )
    jwt_algorithm: str = Field(
        default="HS256", description="JWT signing algorithm"
    )
    jwt_access_token_expire_minutes: int = Field(
        default=15, description="Access token expiration time in minutes"
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7, description="Refresh token expiration time in days"
    )

    # TaskIQ settings
    taskiq_default_retry_count: int = Field(
        default=3, description="Default number of task retries"
    )
    taskiq_default_retry_delay: float = Field(
        default=2.0, description="Default retry delay in seconds"
    )
    taskiq_max_retry_delay: float = Field(
        default=60.0, description="Maximum retry delay in seconds"
    )
    taskiq_task_timeout: float = Field(
        default=300.0, description="Default task timeout in seconds"
    )
    taskiq_result_ttl: int = Field(
        default=3600, description="Task result TTL in seconds"
    )
    taskiq_worker_concurrency: int = Field(
        default=4, description="Number of concurrent tasks per worker"
    )

    # Admin user settings
    admin_username: str = Field(
        default="admin", description="Default admin username"
    )
    admin_password: str = Field(
        default="admin", description="Default admin password"
    )
    admin_email: Optional[str] = Field(
        default=None, description="Default admin email"
    )

    @property
    def database(self) -> DatabaseSettings:
        """Get database settings."""
        # Ensure we use asyncpg driver for async SQLAlchemy
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif not url.startswith("postgresql+asyncpg://"):
            # If it's some other format, ensure asyncpg is used
            if "postgresql" in url and "+asyncpg" not in url:
                url = url.replace("postgresql", "postgresql+asyncpg", 1)
        
        return DatabaseSettings(
            url=url,
            echo=self.database_echo,
            pool_size=self.database_pool_size,
            max_overflow=self.database_max_overflow,
            pool_recycle=self.database_pool_recycle,
        )

    @property
    def redis(self) -> RedisSettings:
        """Get Redis settings."""
        return RedisSettings(
            url=self.redis_url,
            max_connections=self.redis_max_connections,
        )

    @property
    def jwt(self) -> JWTSettings:
        """Get JWT settings."""
        return JWTSettings(
            secret_key=self.jwt_secret_key,
            algorithm=self.jwt_algorithm,
            access_token_expire_minutes=self.jwt_access_token_expire_minutes,
            refresh_token_expire_days=self.jwt_refresh_token_expire_days,
        )

    @property
    def taskiq(self) -> TaskIQSettings:
        """Get TaskIQ settings."""
        return TaskIQSettings(
            default_retry_count=self.taskiq_default_retry_count,
            default_retry_delay=self.taskiq_default_retry_delay,
            max_retry_delay=self.taskiq_max_retry_delay,
            task_timeout=self.taskiq_task_timeout,
            result_ttl=self.taskiq_result_ttl,
            worker_concurrency=self.taskiq_worker_concurrency,
        )


# Global settings instance
settings = Settings()
