"""Lazy PostgreSQL connections, explicit transactions, no automatic schema creation."""

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import Settings


class DatabaseNotConfigured(RuntimeError):
    pass


def create_database_engine(settings: Settings) -> Engine:
    if settings.database_url is None:
        raise DatabaseNotConfigured("Database unavailable")
    return create_engine(
        make_url(settings.database_url.get_secret_value()),
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
        hide_parameters=True,
        connect_args={
            "connect_timeout": settings.db_connect_timeout,
            "options": f"-c timezone=UTC -c statement_timeout={settings.db_statement_timeout_ms}",
        },
    )


class Database:
    def __init__(self, settings: Settings):
        self.statement_timeout_ms = settings.db_statement_timeout_ms
        self.engine = create_database_engine(settings) if settings.database_url else None
        self.sessions = (
            sessionmaker(bind=self.engine, expire_on_commit=False) if self.engine else None
        )

    @contextmanager
    def session(self) -> Iterator[Session]:
        if self.sessions is None:
            raise DatabaseNotConfigured("Database unavailable")
        # Closing rolls back uncommitted work, including after exceptions.
        # Transaction ownership stays with the calling service/job.
        with self.sessions() as session:
            yield session

    def dispose(self):
        if self.engine is not None:
            self.engine.dispose()


def get_database(request: Request) -> Database:
    return request.app.state.database
