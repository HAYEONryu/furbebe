from sqlalchemy import text

from backend.app.db.session import Database, DatabaseNotConfigured


class HealthRepository:
    def __init__(self, database: Database):
        self.database = database

    def check_connection(self):
        if self.database.engine is None:
            raise DatabaseNotConfigured("Database unavailable")
        with self.database.engine.connect() as connection:
            connection.execute(text("SELECT 1")).scalar_one()
