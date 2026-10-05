"""Opt-in integration checks against a dedicated disposable PostgreSQL database."""

import io
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import CheckConstraint, func, inspect, select, text

from backend.app.db.models import Base
from backend.app.db.session import Database
from backend.app.main import create_app

pytestmark = pytest.mark.postgres


def test_health_uses_real_postgres(postgres_settings):
    with TestClient(create_app(postgres_settings)) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "furbebe-api", "version": "1"}


def test_uncommitted_session_is_rolled_back(postgres_settings):
    database = Database(postgres_settings)
    try:
        with database.session() as session:
            session.execute(text("CREATE TEMP TABLE phase2_rollback_probe (id integer)"))
        with database.session() as session:
            assert (
                session.execute(text("SELECT to_regclass('phase2_rollback_probe')")).scalar()
                is None
            )
    finally:
        database.dispose()


def test_alembic_upgrade_downgrade_upgrade_and_metadata_match(postgres_settings):
    path = Path(__file__).resolve().parents[1] / "alembic.ini"
    config = Config(str(path), stdout=io.StringIO())
    database = Database(postgres_settings)
    try:
        command.upgrade(config, "head")
        # A downgrade destroys tables: refuse a database with unexpected tables or data.
        assert set(inspect(database.engine).get_table_names()) == {
            *Base.metadata.tables,
            "alembic_version",
        }
        with database.session() as session:
            for table in Base.metadata.sorted_tables:
                assert session.scalar(select(func.count()).select_from(table)) == 0, (
                    "Roundtrip requires empty domain tables in a disposable test database"
                )
        command.check(config)
        with pytest.raises(RuntimeError, match="roll-forward"):
            command.downgrade(config, "base")
        command.upgrade(config, "head")
        command.upgrade(config, "head")
        command.current(config)
        command.check(config)
        inspector = inspect(database.engine)
        assert set(inspector.get_table_names()) == {*Base.metadata.tables, "alembic_version"}
        # Alembic autogenerate does not detect every CHECK change; check their presence too.
        for table in Base.metadata.sorted_tables:
            expected = {c.name for c in table.constraints if isinstance(c, CheckConstraint)}
            assert {c["name"] for c in inspector.get_check_constraints(table.name)} == expected
        with database.session() as session:
            assert session.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == ("20261005_0005")
    finally:
        database.dispose()
