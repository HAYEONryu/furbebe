"""Read-only PROD migration report. Does not upgrade or downgrade a database."""

import hashlib
import io
import json
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.config import ROOT, ConfigurationError
from backend.app.core.database_target import get_prod_database_settings
from backend.app.db.session import create_database_engine


def migration_plan(current: str | None):
    config = Config(str(ROOT / "backend" / "alembic.ini"), stdout=io.StringIO())
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    if len(heads) != 1:
        raise ConfigurationError("Migration plan requires one reviewed target head")
    target = heads[0]
    try:
        revisions = list(script.iterate_revisions(target, current or "base"))
    except Exception:
        raise ConfigurationError("Current revision is not an ancestor of target") from None
    buffer = io.StringIO()
    config.output_buffer = buffer
    command.upgrade(config, f"{current or 'base'}:{target}", sql=True)
    return {
        "current_revision": current or "base",
        "target_revision": target,
        "migration_files": [
            {
                "path": str(Path(revision.path).relative_to(ROOT)),
                "sha256": hashlib.sha256(Path(revision.path).read_bytes()).hexdigest(),
            }
            for revision in reversed(revisions)
        ],
        "upgrade_sql": buffer.getvalue(),
        "rollback": "No automatic downgrade. Review data loss; restore verified backup or roll forward.",
        "executed_migration": False,
    }


def read_current(engine):
    with engine.connect() as connection, connection.begin():
        connection.execute(text("SET TRANSACTION READ ONLY"))
        exists = connection.scalar(text("SELECT to_regclass('public.alembic_version')"))
        revisions = (
            list(connection.scalars(text("SELECT version_num FROM public.alembic_version")))
            if exists
            else []
        )
        if len(revisions) > 1:
            raise ConfigurationError("Multiple current revisions require manual review")
        return revisions[0] if revisions else None


def main():
    engine = None
    try:
        settings = get_prod_database_settings()
        engine = create_database_engine(settings)
        current = read_current(engine)
        plan = migration_plan(current)
        plan["target"] = {
            "environment": "production",
            "database_target": "supabase-prod",
            "host": engine.url.host,
            "database": engine.url.database,
            "port": engine.url.port,
        }
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    except (ConfigurationError, SQLAlchemyError, OSError):
        print(json.dumps({"status": "blocked", "error": "PRODUCTION_PREFLIGHT_FAILED"}))
        return 2
    finally:
        if engine:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
