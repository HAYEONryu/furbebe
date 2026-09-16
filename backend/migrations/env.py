"""Portable Alembic environment, using the same settings and engine as the app."""

from alembic import context
from alembic.util import CommandError
from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.database_target import get_operational_settings
from backend.app.db.models import Base
from backend.app.db.session import DatabaseNotConfigured, create_database_engine

target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        dialect_name="postgresql",
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    engine = None
    try:
        engine = create_database_engine(get_operational_settings())
        with engine.connect() as connection:
            context.configure(
                connection=connection, target_metadata=target_metadata, compare_type=True
            )
            with context.begin_transaction():
                context.run_migrations()
    except (DatabaseNotConfigured, SQLAlchemyError):
        raise CommandError("Database unavailable; migration was not completed") from None
    finally:
        if engine is not None:
            engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
