from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.schemas.common import ErrorResponse, HealthResponse
from backend.app.services.health import HealthService, get_health_service

router = APIRouter()


@router.get("/health", response_model=HealthResponse, responses={503: {"model": ErrorResponse}})
def health(service: Annotated[HealthService, Depends(get_health_service)]):
    service.check()
    return HealthResponse()
