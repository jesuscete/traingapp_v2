import pytest
from pydantic import ValidationError

from app.core.config import Settings

STRONG = "x" * 32
SAFE_DB = "postgresql+asyncpg://prod_user:Str0ngPass@db:5432/traingapp"


def _settings(**overrides: str) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[arg-type]


def test_development_accepts_defaults() -> None:
    assert _settings(app_env="development").jwt_secret


@pytest.mark.parametrize(
    "overrides",
    [
        {},
        {"internal_token": STRONG, "database_url": SAFE_DB},
        {"jwt_secret": STRONG, "database_url": SAFE_DB},
        {"jwt_secret": STRONG, "internal_token": STRONG},
        {"jwt_secret": "short", "internal_token": STRONG, "database_url": SAFE_DB},
    ],
)
def test_production_rejects_insecure_secrets(overrides: dict[str, str]) -> None:
    with pytest.raises(ValidationError, match="Secretos inseguros"):
        _settings(app_env="production", **overrides)


def test_production_accepts_strong_secrets() -> None:
    s = _settings(
        app_env="production",
        jwt_secret=STRONG,
        internal_token=STRONG,
        database_url=SAFE_DB,
    )
    assert s.app_env == "production"


def test_cors_origins_parsed_from_comma_list() -> None:
    s = _settings(cors_origins=" http://localhost:3000 , http://192.168.1.50:3000,")
    assert s.cors_origin_list == ["http://localhost:3000", "http://192.168.1.50:3000"]
