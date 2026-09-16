from typing import Literal

from pydantic import BaseModel
from starlette.responses import JSONResponse


class UTF8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: Literal["furbebe-api"] = "furbebe-api"
    version: Literal["1"] = "1"


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] | None = None
    request_id: str


class ApiErrorResponse(BaseModel):
    error: ErrorBody


# Keep the foundation's import name compatible; OpenAPI uses the contract model name.
ErrorResponse = ApiErrorResponse
