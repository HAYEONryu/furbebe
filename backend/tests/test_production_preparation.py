"""Production guards use synthetic settings or a disposable local test DB only."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.core.config import ConfigurationError, Settings
from backend.app.core.database_target import get_prod_database_settings
from backend.app.db.session import create_database_engine
from backend.app.main import create_app
from backend.app.repositories.health import HealthRepository
from backend.jobs.animal_sync.main import main as sync_main
from backend.jobs.production_preflight import migration_plan, read_current

PROD_URL = (
    "postgresql://postgres.prodfixture:fake-password@aws-0-region.pooler.supabase.com:5432/postgres"
)


@pytest.fixture
def production_env(tmp_path, monkeypatch):
    for key in (
        "APP_ENV",
        "DATABASE_URL_prod",
        "DATABASE_URL_dev",
        "SUPABASE_URL_prod",
        "SUPABASE_URL_dev",
        "FURBEBE_PROD_PROJECT_REF",
        "PGHOSTADDR",
        "PGSERVICE",
        "PGSERVICEFILE",
        "FRONTEND_ORIGIN",
        "DB_POOL_SIZE",
        "DB_MAX_OVERFLOW",
    ):
        monkeypatch.delenv(key, raising=False)

    def write(**changes):
        values = {
            "APP_ENV": "production",
            "DATABASE_URL_prod": PROD_URL,
            "SUPABASE_URL_prod": "https://prodfixture.supabase.co",
            "FURBEBE_PROD_PROJECT_REF": "prodfixture",
            **changes,
        }
        path = tmp_path / ".env"
        path.write_text("".join(f"{key}={value}\n" for key, value in values.items()))
        return path

    return write


def test_prod_target_binds_project_and_does_not_use_generic_database(production_env, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@dev.example/dev")
    settings = get_prod_database_settings(production_env())
    assert settings.app_env == "production"
    assert "fake-password" not in repr(settings)
    engine = create_database_engine(settings)
    assert engine.url.username == "postgres.prodfixture"
    assert engine.url.query["sslmode"] == "require"
    engine.dispose()


@pytest.mark.parametrize(
    "changes",
    [
        {"DATABASE_URL_prod": ""},
        {"APP_ENV": "development"},
        {"APP_ENV": ""},
        {"DATABASE_URL_prod": PROD_URL.replace("prodfixture", "devfixture")},
        {"FURBEBE_PROD_PROJECT_REF": "devfixture"},
        {"SUPABASE_URL_dev": "https://prodfixture.supabase.co"},
        {"DATABASE_URL_prod": PROD_URL.replace(":5432", ":6543")},
        {"DATABASE_URL_prod": PROD_URL + "?sslmode=disable"},
        {"DATABASE_URL_prod": PROD_URL + "?host=other.example"},
        {"DB_POOL_SIZE": "0"},
    ],
)
def test_prod_target_refuses_ambiguous_or_unsafe_settings(production_env, changes):
    with pytest.raises(ConfigurationError) as exc:
        get_prod_database_settings(production_env(**changes))
    assert "fake-password" not in str(exc.value)


def test_prod_replay_refused_before_any_database_access():
    with pytest.raises(SystemExit):
        sync_main(["--database-target", "supabase-prod", "--replay", "/tmp/fake"])


def test_configurable_pool_budget_and_pre_ping():
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=PROD_URL,
        db_pool_size=3,
        db_max_overflow=1,
        db_pool_timeout=4,
        db_pool_recycle=1200,
    )
    engine = create_database_engine(settings)
    assert engine.pool.size() == 3
    assert engine.pool._max_overflow == 1
    assert engine.pool._pre_ping is True
    assert engine.pool.timeout() == 4
    engine.dispose()
    with pytest.raises(ValidationError):
        Settings(_env_file=None, db_max_overflow=-1)


def test_production_cors_debug_and_structured_logs_do_not_echo_query_secrets(monkeypatch, caplog):
    monkeypatch.setattr(HealthRepository, "check_connection", lambda self: None)
    settings = Settings(
        _env_file=None,
        app_env="production",
        database_url=PROD_URL,
        frontend_origin="https://furbebe.site,https://www.furbebe.site",
    )
    app = create_app(settings)
    assert not app.debug and app.docs_url is None and app.openapi_url is None
    with TestClient(app) as client:
        for origin in settings.allowed_origins:
            response = client.get("/health?serviceKey=PRIVATE_CANARY", headers={"Origin": origin})
            assert response.headers["access-control-allow-origin"] == origin
        denied = client.get("/health", headers={"Origin": "http://localhost:5173"})
        assert "access-control-allow-origin" not in denied.headers
        client.get("/PRIVATE_CANARY")
    records = [
        json.loads(record.message)
        for record in caplog.records
        if record.message.startswith('{"event": "http_request"')
    ]
    assert records and records[0]["endpoint"] == "/health"
    assert records[0]["status"] == 200 and records[0]["duration_ms"] >= 0
    assert records[0]["request_id"]
    assert records[-1]["endpoint"] == "<unmatched>"
    assert "PRIVATE_CANARY" not in caplog.text and "fake-password" not in caplog.text


def test_migration_plan_is_offline_and_reports_destructive_rollback_without_execution():
    plan = migration_plan(None)
    assert plan["current_revision"] == "base" and plan["target_revision"] == "20261005_0005"
    assert "CREATE TABLE animals" in plan["upgrade_sql"]
    assert "DELETE FROM" not in plan["upgrade_sql"]
    assert "DROP TABLE" not in plan["upgrade_sql"]
    assert plan["migration_files"][0]["sha256"]
    assert plan["executed_migration"] is False
    assert not migration_plan("20261005_0005")["migration_files"]
    assert len(migration_plan("20260915_0001")["migration_files"]) == 4
    with pytest.raises(ConfigurationError):
        migration_plan("unknown")


@pytest.mark.postgres
def test_read_current_is_only_reading_disposable_database(postgres_settings):
    engine = create_database_engine(postgres_settings)
    try:
        # Previous integration fixtures migrate this disposable DB to head.
        assert read_current(engine) in {None, "20261005_0005"}
    finally:
        engine.dispose()


def test_api_image_copies_only_application_and_has_no_secret_build_arguments():
    root = Path(__file__).resolve().parents[2]
    dockerfile = (root / "backend/Dockerfile").read_text()
    assert "COPY backend /app/backend" not in dockerfile
    assert "ARG DATABASE_URL" not in dockerfile
    assert "ENV DATABASE_URL" not in dockerfile
    assert '"--no-access-log"' in dockerfile and "USER 10001" in dockerfile
