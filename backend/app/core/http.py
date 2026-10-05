"""Safe JSON errors and request IDs, including unhandled failures."""

import json
import logging
import time
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.schemas.common import ErrorBody, ErrorResponse, UTF8JSONResponse
from backend.app.services.errors import AnimalNotFound, TagNotFound
from backend.app.services.health import DatabaseUnavailable

logger = logging.getLogger("furbebe.http")


def error_response(request, status, code, message, details=None):
    request_id = request.state.request_id
    body = ErrorResponse(
        error=ErrorBody(code=code, message=message, details=details, request_id=request_id)
    )
    return UTF8JSONResponse(
        body.model_dump(), status_code=status, headers={"X-Request-ID": request_id}
    )


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        started = time.perf_counter()
        supplied = request.headers.get("X-Request-ID", "")
        try:
            request.state.request_id = str(UUID(supplied))
        except ValueError:
            request.state.request_id = str(uuid4())
        try:
            response = await call_next(request)
        except Exception:
            # Exception text, SQL, URL and request contents can carry credentials.
            logger.error("Unhandled request failure request_id=%s", request.state.request_id)
            response = error_response(request, 500, "INTERNAL_ERROR", "Internal server error")
        route = request.scope.get("route")
        # Route templates avoid logging arbitrary path/query input or animal IDs.
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request.state.request_id,
                    "endpoint": getattr(route, "path", "<unmatched>"),
                    "method": request.method
                    if request.method
                    in {"GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"}
                    else "OTHER",
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                }
            )
        )
        response.headers["X-Request-ID"] = request.state.request_id
        return response


def install_error_handlers(app: FastAPI):
    @app.exception_handler(AnimalNotFound)
    async def animal_not_found(request: Request, exc: AnimalNotFound):
        return error_response(request, 404, "ANIMAL_NOT_FOUND", "Animal not found")

    @app.exception_handler(TagNotFound)
    async def tag_not_found(request: Request, exc: TagNotFound):
        return error_response(request, 404, "TAG_NOT_FOUND", "Tag not found")

    @app.exception_handler(DatabaseUnavailable)
    async def unavailable(request: Request, exc: DatabaseUnavailable):
        return error_response(request, 503, "SERVICE_UNAVAILABLE", "Database unavailable")

    @app.exception_handler(RequestValidationError)
    async def validation(request: Request, exc: RequestValidationError):
        # Keep locations; do not echo input values or custom validator exception messages.
        details = [
            {"field": ".".join(map(str, issue["loc"][1:])), "message": "Invalid value"}
            for issue in exc.errors()
        ]
        return error_response(
            request, 422, "VALIDATION_ERROR", "Request validation failed", details
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        message = {404: "Not found", 405: "Method not allowed"}.get(
            exc.status_code, "Invalid request"
        )
        response = error_response(request, exc.status_code, "INVALID_REQUEST", message)
        if exc.status_code == 405 and exc.headers and "Allow" in exc.headers:
            response.headers["Allow"] = exc.headers["Allow"]
        return response
