from typing import Annotated

from fastapi import Depends
from sqlalchemy.exc import SQLAlchemyError

from backend.app.db.session import Database, DatabaseNotConfigured, get_database
from backend.app.repositories.health import HealthRepository


class DatabaseUnavailable(RuntimeError):
    pass


class HealthService:
    def __init__(self, repository: HealthRepository):
        self.repository = repository

    def check(self):
        try:
            self.repository.check_connection()
        except (DatabaseNotConfigured, SQLAlchemyError):
            raise DatabaseUnavailable("Database unavailable") from None


def get_health_service(database: Annotated[Database, Depends(get_database)]) -> HealthService:
    return HealthService(HealthRepository(database))
