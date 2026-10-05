"""FURBEBE v1 read API; database operations remain explicit and read-only."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.animals import router as animals_router
from backend.app.api.health import router as health_router
from backend.app.core.config import Settings
from backend.app.core.database_target import get_operational_settings
from backend.app.core.http import RequestContextMiddleware, install_error_handlers
from backend.app.core.logging import configure_logging
from backend.app.db.session import Database
from backend.app.schemas.common import UTF8JSONResponse


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_operational_settings()
    configure_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database = Database(settings)
        app.state.database = database
        try:
            yield
        finally:
            database.dispose()

    app = FastAPI(
        title="FURBEBE API",
        version="1",
        debug=False,
        openapi_url=None if settings.app_env == "production" else "/openapi.json",
        lifespan=lifespan,
        default_response_class=UTF8JSONResponse,
        docs_url=None if settings.app_env == "production" else "/docs",
        redoc_url=None,
    )
    app.state.settings = settings
    install_error_handlers(app)
    app.include_router(health_router)
    app.include_router(animals_router)
    # CORS wraps the request/error middleware, so 500/503 also carry allowed origins.
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    return app


app = create_app()
