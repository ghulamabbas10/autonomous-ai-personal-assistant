import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_normalize_log_level() -> None:
    settings = Settings(log_level="warning", _env_file=None)
    assert settings.log_level == "WARNING"


def test_settings_reject_sync_database_driver() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="postgresql://localhost/assistant", _env_file=None)


def test_settings_reject_placeholder_production_secrets() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production", _env_file=None)
