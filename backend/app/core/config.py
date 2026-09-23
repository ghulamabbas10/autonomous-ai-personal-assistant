from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated backend configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_name: str = "Autonomous Assistant"
    api_base_url: AnyHttpUrl = AnyHttpUrl("http://localhost:8000")
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://assistant:change-me@localhost:5432/assistant"
    redis_url: str = "redis://localhost:6379/0"
    session_secret: SecretStr = SecretStr("development-only-change-me-please")
    data_encryption_key: SecretStr = SecretStr("development-only-change-me")
    default_daily_budget_usd: float = Field(default=5.0, ge=0)
    default_monthly_budget_usd: float = Field(default=100.0, ge=0)
    max_agent_iterations: int = Field(default=30, ge=1, le=1_000)
    max_tool_calls_per_run: int = Field(default=50, ge=1, le=10_000)
    max_task_duration_seconds: int = Field(default=7_200, ge=1)
    default_timezone: str = "UTC"
    session_ttl_hours: int = Field(default=168, ge=1, le=24 * 90)
    auth_rate_limit_attempts: int = Field(default=5, ge=1, le=100)
    auth_rate_limit_window_seconds: int = Field(default=900, ge=1, le=86_400)
    session_cookie_name: str = "assistant_session"
    csrf_cookie_name: str = "assistant_csrf"

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        value = value.upper()
        if value not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("invalid log level")
        return value

    @field_validator("database_url")
    @classmethod
    def require_async_database_driver(cls, value: str) -> str:
        if not value.startswith(("postgresql+asyncpg://", "sqlite+aiosqlite://")):
            raise ValueError("DATABASE_URL must use asyncpg or aiosqlite")
        return value

    @model_validator(mode="after")
    def reject_placeholder_production_secrets(self) -> "Settings":
        if self.app_env != "production":
            return self
        for name, secret in (
            ("SESSION_SECRET", self.session_secret.get_secret_value()),
            ("DATA_ENCRYPTION_KEY", self.data_encryption_key.get_secret_value()),
        ):
            lowered = secret.casefold()
            if len(secret) < 32 or "replace" in lowered or "development" in lowered:
                raise ValueError(f"{name} must be a non-placeholder secret in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
