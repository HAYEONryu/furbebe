"""HTTP v1 contracts. All data access is owned by the service/repository layers."""

from datetime import UTC, datetime, time, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.animals import (
    AnimalDetailResponse,
    AnimalFilters,
    AnimalListResponse,
    FilterMetaResponse,
    OverviewStatsResponse,
    SimilarAnimalsResponse,
    TagListResponse,
    TagType,
)
from backend.app.schemas.common import ApiErrorResponse
from backend.app.services.animals import ReadService, get_read_service
from backend.jobs.animal_sync.status_policy import KST

router = APIRouter(
    prefix="/api/v1", responses={code: {"model": ApiErrorResponse} for code in (404, 422, 503, 500)}
)
Service = Annotated[ReadService, Depends(get_read_service)]


class SimilarQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int = Field(default=4, ge=1, le=12)


class TagQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: TagType | None = None
    active_only: bool = True


def cache(response, seconds, *, today):
    now = datetime.now(UTC).astimezone(KST)
    midnight = datetime.combine(today + timedelta(days=1), time.min, KST)
    # Expire at the query date's midnight, even if the query finishes next day.
    seconds = min(seconds, max(0, int((midnight - now).total_seconds())))
    response.headers["Cache-Control"] = f"public, max-age={seconds}"


@router.get("/animals", response_model=AnimalListResponse)
def animals(filters: Annotated[AnimalFilters, Query()], service: Service, response: Response):
    result = service.animals(filters)
    cache(response, 60, today=service.today)
    return result


@router.get("/animals/{animal_id}", response_model=AnimalDetailResponse)
def animal_detail(animal_id: UUID, service: Service, response: Response):
    result = service.detail(animal_id)
    cache(response, 300, today=service.today)
    return result


@router.get("/animals/{animal_id}/similar", response_model=SimilarAnimalsResponse)
def similar_animals(
    animal_id: UUID, query: Annotated[SimilarQuery, Query()], service: Service, response: Response
):
    result = service.similar(animal_id, limit=query.limit)
    cache(response, 300, today=service.today)
    return result


@router.get("/tags", response_model=TagListResponse)
def tags(query: Annotated[TagQuery, Query()], service: Service, response: Response):
    result = service.tags(type=query.type, active_only=query.active_only)
    cache(response, 600, today=service.today)
    return result


@router.get("/meta/filters", response_model=FilterMetaResponse)
def filters_meta(service: Service, response: Response):
    result = service.meta()
    cache(response, 600, today=service.today)
    return result


@router.get("/stats/overview", response_model=OverviewStatsResponse)
def stats_overview(service: Service, response: Response):
    result = service.stats()
    cache(response, 60, today=service.today)
    return result
