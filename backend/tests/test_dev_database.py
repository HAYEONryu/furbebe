"""DEV target selection tests use fake credentials and never open a connection."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url

from backend.app.core.config import ConfigurationError
from backend.app.core.database_target import get_dev_database_settings
from backend.app.main import create_app

URL = (
    "postgresql://postgres.devfixture:fake-password@aws-0-region.pooler.supabase.com:5432/postgres"
)
PROJECT = "https://devfixture.supabase.co"


@pytest.fixture
def env_file(tmp_path, monkeypatch):
    for key in (
        "DATABASE_URL_dev",
        "SUPABASE_URL_dev",
        "APP_ENV",
        "FRONTEND_ORIGIN",
        "DB_CONNECT_TIMEOUT",
        "DB_STATEMENT_TIMEOUT_MS",
        "host_dev",
        "port_dev",
        "database_dev",
        "user_dev",
        "PGHOSTADDR",
        "PGSERVICE",
        "PGSERVICEFILE",
    ):
        monkeypatch.delenv(key, raising=False)

    def write(**changes):
        config = {"DATABASE_URL_dev": URL, "SUPABASE_URL_dev": PROJECT, **changes}
        path = tmp_path / ".env"
        path.write_text(
            "".join(f"{key}={value}\n" for key, value in config.items()), encoding="utf-8"
        )
        return path

    return write


def test_explicit_dev_settings_match_project_and_enable_tls(env_file, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@unrelated.example/production")
    settings = get_dev_database_settings(env_file())
    url = make_url(settings.database_url.get_secret_value())
    assert settings.app_env == "development"
    assert url.username == "postgres.devfixture" and url.query["sslmode"] == "require"
    assert url.drivername == "postgresql+psycopg"
    assert "fake-password" not in repr(settings)


@pytest.mark.parametrize(
    "changes",
    [
        {"DATABASE_URL_dev": "not-a-database-url"},
        {"DATABASE_URL_dev": URL.replace("devfixture", "productionfixture")},
        {"DATABASE_URL_dev": URL.replace(":5432", ":6543")},
        {"DATABASE_URL_dev": URL + "?host=other.example"},
        {"DATABASE_URL_dev": URL + "?sslmode=disable"},
        {"DATABASE_URL_dev": URL.replace("fake-password", "[YOUR-PASSWORD]")},
        {"SUPABASE_URL_dev": PROJECT + ".other.example"},
        {"APP_ENV": "production"},
        {"APP_ENV": "test"},
        {"host_dev": "other.example"},
        {"port_dev": "6543"},
        {"database_dev": "other"},
        {"user_dev": "other"},
    ],
)
def test_invalid_or_ambiguous_dev_target_is_rejected_without_echo(env_file, changes):
    with pytest.raises(ConfigurationError) as error:
        get_dev_database_settings(env_file(**changes))
    assert "fake-password" not in str(error.value)
    assert "supabase.com" not in str(error.value)


def test_direct_dev_connection_and_verified_tls_are_supported(env_file):
    url = "postgresql://postgres:fake-password@db.devfixture.supabase.co:5432/postgres?sslmode=verify-full"
    settings = get_dev_database_settings(env_file(DATABASE_URL_dev=url))
    assert make_url(settings.database_url.get_secret_value()).query["sslmode"] == "verify-full"


def test_libpq_environment_cannot_redirect_dev_connection(env_file, monkeypatch):
    monkeypatch.setenv("PGHOSTADDR", "192.0.2.1")
    with pytest.raises(ConfigurationError):
        get_dev_database_settings(env_file())


@pytest.mark.parametrize("custom_file", [False, True])
def test_dev_dotenv_app_settings_and_cors_are_applied(env_file, monkeypatch, custom_file):
    path = env_file(
        FRONTEND_ORIGIN="http://localhost:3000",
        DB_CONNECT_TIMEOUT=11,
        DB_STATEMENT_TIMEOUT_MS=1234,
        DATABASE_URL="postgresql://u:p@unrelated.example/production",
    )
    monkeypatch.setattr("backend.app.core.database_target.ROOT", path.parent)
    settings = get_dev_database_settings(path if custom_file else None)
    assert settings.frontend_origin == "http://localhost:3000"
    assert settings.db_connect_timeout == 11
    assert settings.db_statement_timeout_ms == 1234
    assert make_url(settings.database_url.get_secret_value()).username == "postgres.devfixture"
    # CORS preflight uses the actual app middleware and never connects to the DB.
    with TestClient(create_app(settings)) as client:
        response = client.options(
            "/api/v1/animals",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_dev_process_settings_override_dotenv_without_redirecting_database(env_file, monkeypatch):
    path = env_file(
        FRONTEND_ORIGIN="http://localhost:3000",
        DB_CONNECT_TIMEOUT=11,
        DB_STATEMENT_TIMEOUT_MS=1234,
    )
    monkeypatch.setenv("FRONTEND_ORIGIN", "http://localhost:4000")
    monkeypatch.setenv("DB_CONNECT_TIMEOUT", "12")
    monkeypatch.setenv("DB_STATEMENT_TIMEOUT_MS", "2345")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@unrelated.example/production")
    settings = get_dev_database_settings(path)
    assert settings.frontend_origin == "http://localhost:4000"
    assert settings.db_connect_timeout == 12
    assert settings.db_statement_timeout_ms == 2345
    assert make_url(settings.database_url.get_secret_value()).username == "postgres.devfixture"


@pytest.mark.parametrize(
    "changes",
    [
        {"FRONTEND_ORIGIN": "https://private.invalid/secret-path"},
        {"DB_CONNECT_TIMEOUT": "private-invalid-value"},
        {"DB_STATEMENT_TIMEOUT_MS": "private-invalid-value"},
    ],
)
def test_invalid_dev_app_settings_fail_without_echoing_values(env_file, changes):
    with pytest.raises(ConfigurationError) as error:
        get_dev_database_settings(env_file(**changes))
    assert str(error.value) == "Invalid or mismatched Supabase DEV database settings"
