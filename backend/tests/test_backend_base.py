"""Phase 2 contract, configuration, and connection ownership checks."""

from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError

from backend.app.core.config import ConfigurationError, Settings, get_settings
from backend.app.db.models import Base
from backend.app.db.session import Database, create_database_engine
from backend.app.main import create_app
from backend.app.repositories.health import HealthRepository

SECRET_URL = "postgresql://test:private-password@private-host/testdb"


def settings(**kwargs):
    return Settings(_env_file=None, app_env="test", **kwargs)


def test_health_success_exact_contract_and_valid_request_id(monkeypatch):
    monkeypatch.setattr(HealthRepository, "check_connection", lambda self: None)
    request_id = str(uuid4())
    with TestClient(create_app(settings())) as client:
        response = client.get("/health", headers={"X-Request-ID": request_id})
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "furbebe-api", "version": "1"}
    assert response.headers["content-type"] == "application/json; charset=utf-8"
    assert response.headers["x-request-id"] == request_id


def test_health_without_config_returns_503():
    with TestClient(create_app(settings(database_url=None))) as client:
        response = client.get("/health", headers={"X-Request-ID": "invalid"})
    assert response.status_code == 503
    error = response.json()["error"]
    assert error == {
        "code": "SERVICE_UNAVAILABLE",
        "message": "Database unavailable",
        "details": None,
        "request_id": response.headers["x-request-id"],
    }
    UUID(error["request_id"])


def test_database_error_is_redacted_and_cors_is_preserved(monkeypatch, caplog):
    def fail(self):
        raise OperationalError("PRIVATE SQL", {"key": "private-parameter"}, Exception(SECRET_URL))

    monkeypatch.setattr(HealthRepository, "check_connection", fail)
    with TestClient(create_app(settings())) as client:
        response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 503
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "private" not in response.text + caplog.text
    assert "PRIVATE SQL" not in response.text + caplog.text


def test_unhandled_exception_is_json_with_request_id_and_no_secrets(caplog):
    app = create_app(settings())

    @app.get("/test-failure")
    def failure():
        raise RuntimeError(SECRET_URL)

    with TestClient(app) as client:
        response = client.get("/test-failure", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "private-password" not in response.text + caplog.text
    assert "private-host" not in response.text + caplog.text


def test_validation_does_not_echo_input():
    app = create_app(settings())

    @app.get("/test-validation")
    def validate(page: int):
        return {"page": page}

    with TestClient(app) as client:
        response = client.get("/test-validation", params={"page": "private-value"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["details"] == [{"field": "page", "message": "Invalid value"}]
    assert "private-value" not in response.text


def test_unknown_route_and_method_use_error_envelope():
    with TestClient(create_app(settings())) as client:
        for method, path, status in [("GET", "/api/v1/not-a-route", 404), ("POST", "/health", 405)]:
            response = client.request(method, path)
            assert response.status_code == status
            assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_cors_allowlist_preflight_and_rejection():
    with TestClient(create_app(settings())) as client:
        allowed = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-Request-ID",
            },
        )
        denied = client.get("/health", headers={"Origin": "https://unexpected.example"})
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in denied.headers


@pytest.mark.parametrize("url", ["mysql://u:p@host/db", "sqlite:///test.db", "postgresql:///db"])
def test_only_explicit_postgresql_connections_are_allowed(url):
    with pytest.raises(ValidationError):
        settings(database_url=url)


def test_url_normalization_keeps_password_and_tls_private():
    config = settings(database_url="postgresql://user:p%40ss@host/db?sslmode=require")
    assert "p%40ss" not in repr(config)
    assert config.database_url.get_secret_value().startswith("postgresql+psycopg://")
    assert "sslmode=require" in config.database_url.get_secret_value()
    engine = create_database_engine(config)
    assert engine.url.password == "p@ss"
    assert engine.url.query["sslmode"] == "require"
    assert engine.dialect.driver == "psycopg"
    engine.dispose()


@pytest.mark.parametrize(
    "origin", ["*", "https://*.example", "https://x/path", "https://u:p@x", ""]
)
def test_origins_require_exact_origins(origin):
    with pytest.raises(ValidationError):
        settings(frontend_origin=origin)


def test_production_requires_database_and_https_allowlist():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production", database_url=None)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production", database_url=SECRET_URL)
    config = Settings(
        _env_file=None,
        app_env="production",
        database_url=SECRET_URL,
        frontend_origin="https://furbebe.com/, https://www.furbebe.com",
    )
    assert config.allowed_origins == ["https://furbebe.com", "https://www.furbebe.com"]
    assert create_app(config).docs_url is None


def test_settings_failure_never_formats_credentials(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "invalid://user:private-password@private-host/db")
    get_settings.cache_clear()
    try:
        with pytest.raises(ConfigurationError) as error:
            get_settings()
        assert "private" not in str(error.value)
    finally:
        get_settings.cache_clear()


def test_lifespan_disposes_engine_without_connecting(monkeypatch):
    engine = MagicMock()
    monkeypatch.setattr("backend.app.db.session.create_database_engine", lambda settings: engine)
    with TestClient(create_app(settings(database_url=SECRET_URL))):
        engine.connect.assert_not_called()
    engine.dispose.assert_called_once()


def test_session_is_closed_after_exception_without_implicit_commit():
    database = Database(settings())
    session = MagicMock()
    database.sessions = MagicMock()
    database.sessions.return_value.__enter__.return_value = session
    with pytest.raises(ValueError), database.session():
        raise ValueError("Abort operation")
    session.commit.assert_not_called()
    database.sessions.return_value.__exit__.assert_called_once()


def test_v1_routes_and_domain_tables_are_explicit():
    schema = create_app(settings()).openapi()
    assert set(schema["paths"]) == {
        "/health",
        "/api/v1/animals",
        "/api/v1/animals/{animal_id}",
        "/api/v1/animals/{animal_id}/similar",
        "/api/v1/tags",
        "/api/v1/meta/filters",
        "/api/v1/stats/overview",
    }
    assert "animals_active" not in str(schema)
    assert set(Base.metadata.tables) == {
        "shelters",
        "animals",
        "animal_images",
        "tags",
        "animal_tags",
        "sync_runs",
    }
