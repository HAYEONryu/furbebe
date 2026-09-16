"""Explicit opt-in PostgreSQL configuration; never fall back to the application DB."""

import os

import pytest
from sqlalchemy.engine import make_url

from backend.app.core.config import Settings, get_settings
from backend.app.core.database_target import CONNECTION_OVERRIDES, TARGET_ENV


@pytest.fixture
def postgres_settings(monkeypatch):
    url = os.environ.get("FURBEBE_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set FURBEBE_TEST_DATABASE_URL to a disposable test database")
    target = make_url(url)
    if (
        not (target.database or "").startswith("furbebe_test")
        or target.host not in {"localhost", "127.0.0.1", "::1"}
        or set(target.query) & CONNECTION_OVERRIDES
        or any(os.environ.get(key) for key in ("PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE"))
    ):
        pytest.fail("Destructive integration tests require a local furbebe_test database")
    monkeypatch.delenv(TARGET_ENV, raising=False)
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    yield Settings(_env_file=None, app_env="test", database_url=url)
    get_settings.cache_clear()
