import pytest

from app.core.config import REPO_ROOT, Settings


def test_defaults_match_docker_compose_database() -> None:
    settings = Settings(_env_file=None)

    assert settings.database_url == (
        "postgresql+asyncpg://grounded:grounded@localhost:5432/grounded_rag"
    )
    assert settings.db_timeout_seconds == 5.0
    assert settings.log_level == "INFO"


def test_environment_variables_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = Settings(_env_file=None)

    assert settings.db_timeout_seconds == 12.5
    assert settings.log_level == "DEBUG"


def test_env_example_lists_exactly_the_settings_fields() -> None:
    lines = (REPO_ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    example_keys = {
        line.split("=", 1)[0].strip() for line in lines if "=" in line and not line.startswith("#")
    }

    assert example_keys == {name.upper() for name in Settings.model_fields}


def test_repo_root_is_the_directory_holding_backend() -> None:
    assert (REPO_ROOT / "backend" / "app").is_dir()
