import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _settings(**overrides: str) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[arg-type]


def test_development_accepts_default_token() -> None:
    assert _settings(app_env="development").internal_token


@pytest.mark.parametrize("token", ["internal-dev-token", "short"])
def test_production_rejects_weak_internal_token(token: str) -> None:
    with pytest.raises(ValidationError, match="Secretos inseguros"):
        _settings(app_env="production", internal_token=token)


def test_production_accepts_strong_internal_token() -> None:
    assert _settings(app_env="production", internal_token="x" * 32).app_env == "production"
