"""FastAPI v1 wire models, independent of persistence models."""

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

Sex = Literal["male", "female", "unknown"]
Neutered = Literal["yes", "no", "unknown"]
SizeGroup = Literal["tiny", "small", "medium", "large", "unknown"]
AgeGroup = Literal["puppy", "young", "adult", "senior", "unknown"]
TagType = Literal["fact", "trait", "vibe"]
Sort = Literal["recent", "notice_end", "weight_asc", "weight_desc", "age_youngest", "age_oldest"]


class AnimalFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=24, ge=1, le=60)
    sido: str | None = None
    sigungu: str | None = None
    breed: str | None = None
    sex: Sex | None = None
    neutered: Neutered | None = None
    size_group: SizeGroup | None = None
    age_group: AgeGroup | None = None
    tag: list[Annotated[str, Field(min_length=1)]] = Field(default_factory=list)
    tag_match: Literal["any", "all"] = "any"
    process_state: str | None = None
    q: str | None = Field(default=None, max_length=50)
    sort: Sort = "recent"

    @field_validator("sido", "sigungu", "breed", "process_state", "q")
    @classmethod
    def trim_optional(cls, value):
        if value is not None and "\x00" in value:
            raise ValueError("Invalid text")
        return (value.strip() or None) if value is not None else None

    @field_validator("tag")
    @classmethod
    def unique_tags(cls, values):
        if any(not value.strip() or "\x00" in value for value in values):
            raise ValueError("Invalid tag")
        return list(dict.fromkeys(value.strip() for value in values))


class ImageResponse(BaseModel):
    url: str
    order: int = Field(ge=1)
    type: Literal["source", "adoption"]


class TagAssignmentResponse(BaseModel):
    key: str
    type: TagType
    label: str
    emoji: str | None
    confidence: float = Field(ge=0, le=1)
    evidence: str | None


class RegionResponse(BaseModel):
    sido: str | None
    sigungu: str | None
    display: str | None


class ShelterResponse(BaseModel):
    id: UUID
    name: str | None
    phone: str | None
    address: str | None
    organization: str | None


class AdoptionPromotionResponse(BaseModel):
    title: str | None
    start_date: date | None
    end_date: date | None
    condition_text: str | None
    description: str | None
    image_url: str | None


class AnimalSummaryResponse(BaseModel):
    id: UUID
    notice_no: str | None
    breed: str | None
    breed_full: str | None
    sex: Sex | None
    birth_year: int | None
    age_text: str | None
    age_group: AgeGroup
    weight_kg: float | None
    weight_text: str | None
    size_group: SizeGroup
    color_text: str | None
    process_state: str | None
    found_date: date | None
    notice_end: date | None
    region: RegionResponse
    primary_image: ImageResponse | None
    tags: list[TagAssignmentResponse]


class PaginationResponse(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_previous: bool


class AppliedAnimalFiltersResponse(BaseModel):
    sido: str | None
    sigungu: str | None
    breed: str | None
    sex: Sex | None
    neutered: Neutered | None
    size_group: SizeGroup | None
    age_group: AgeGroup | None
    tags: list[str]
    tag_match: Literal["any", "all"]
    process_state: str | None
    q: str | None
    sort: Sort


class AnimalListResponse(BaseModel):
    items: list[AnimalSummaryResponse]
    pagination: PaginationResponse
    applied_filters: AppliedAnimalFiltersResponse


class SourceResponse(BaseModel):
    provider: str
    source_id: str
    source_updated_at: datetime | None


class NoticeResponse(BaseModel):
    notice_no: str | None
    start_date: date | None
    end_date: date | None
    process_state: str | None
    end_reason: str | None


class AnimalFactsResponse(BaseModel):
    species: str | None
    breed: str | None
    breed_full: str | None
    sex: Sex | None
    neutered: Neutered | None
    birth_year: int | None
    age_text: str | None
    age_group: AgeGroup
    weight_kg: float | None
    weight_text: str | None
    size_group: SizeGroup
    color_text: str | None
    rfid_code: str | None


class FoundResponse(BaseModel):
    date: date | None
    place: str | None
    region: RegionResponse


class DescriptionsResponse(BaseModel):
    special_mark: str | None
    social: str | None
    health: str | None
    etc: str | None
    vaccination: str | None
    health_check: str | None


class AnimalDetailResponse(BaseModel):
    id: UUID
    source: SourceResponse
    notice: NoticeResponse
    animal: AnimalFactsResponse
    found: FoundResponse
    images: list[ImageResponse]
    tags: list[TagAssignmentResponse]
    descriptions: DescriptionsResponse
    shelter: ShelterResponse | None
    adoption_promotion: AdoptionPromotionResponse | None
    first_seen_at: datetime
    last_seen_at: datetime


class SimilarAnimalsResponse(BaseModel):
    source_animal_id: UUID
    items: list[AnimalSummaryResponse]


class TagResponse(BaseModel):
    key: str
    type: TagType
    label: str
    emoji: str | None
    description: str | None


class TagListResponse(BaseModel):
    items: list[TagResponse]


class RegionFilterResponse(BaseModel):
    sido: str
    sigungu: list[str]
    sido_label: str | None = None
    sigungu_labels: dict[str, str] = Field(default_factory=dict)


class FilterOptionResponse(BaseModel):
    value: str
    label: str


class BreedFilterResponse(BaseModel):
    value: str
    count: int


class StateFilterResponse(FilterOptionResponse):
    count: int


class FilterMetaResponse(BaseModel):
    regions: list[RegionFilterResponse]
    breeds: list[BreedFilterResponse]
    sexes: list[FilterOptionResponse]
    neutered: list[FilterOptionResponse]
    size_groups: list[FilterOptionResponse]
    age_groups: list[FilterOptionResponse]
    process_states: list[StateFilterResponse]


class OverviewStatsResponse(BaseModel):
    animals_total: int
    new_today: int
    with_primary_image: int
    last_synced_at: datetime | None
