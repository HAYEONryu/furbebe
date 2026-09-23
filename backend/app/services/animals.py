"""Read policy and explicit wire serialization; no SQL or upstream API requests."""

from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy.exc import SQLAlchemyError

from backend.app.db.session import Database, DatabaseNotConfigured, get_database
from backend.app.repositories.animals import PROMOTION_FIELDS, SUMMARY_FIELDS, ReadRepository
from backend.app.schemas.animals import (
    AdoptionPromotionResponse,
    AnimalDetailResponse,
    AnimalListResponse,
    AnimalSummaryResponse,
    FilterMetaResponse,
    OverviewStatsResponse,
    SimilarAnimalsResponse,
    TagListResponse,
)
from backend.app.services.errors import AnimalNotFound, TagNotFound
from backend.app.services.health import DatabaseUnavailable
from backend.app.services.regions import matching_organizations, region_for
from backend.jobs.animal_sync.normalizer import nullable_text
from backend.jobs.animal_sync.parsing import parse_date, valid_url
from backend.jobs.animal_sync.status_policy import korea_today
from backend.jobs.animal_sync.tagger import CATEGORIES, generate_safety_badges

LABELS = {
    "sexes": {"male": "수컷", "female": "암컷", "unknown": "미상"},
    "neutered": {"yes": "중성화 완료", "no": "중성화 안 됨", "unknown": "미상"},
    "size_groups": {
        "tiny": "아주 작아요",
        "small": "작아요",
        "medium": "중간",
        "large": "커요",
        "unknown": "미상",
    },
    "age_groups": {
        "puppy": "아가댕",
        "young": "어린 친구",
        "adult": "성견",
        "senior": "시니어",
        "unknown": "미상",
    },
}


def region_response(organization):
    region = region_for(organization)
    return {
        "sido": region["sido_code"] if region else None,
        "sigungu": region["sigungu_code"] if region else None,
        "display": organization,
    }


def summary(row):
    return AnimalSummaryResponse(
        **{name: row[name] for name in SUMMARY_FIELDS},
        age_group=row["age_group"],
        size_group=row["size_group"],
        process_state=row["process_state"],
        region=region_response(row["organization"]),
        primary_image=row["images"][0] if row["images"] else None,
        tags=[dict(tag, category=CATEGORIES.get(tag["key"])) for tag in row["tags"]],
        safety_badges=generate_safety_badges(row),
    )


def promotion(row):
    values = {field: nullable_text(row["promotion_" + field]) for field in PROMOTION_FIELDS}
    for field in ("start_date", "end_date"):
        parsed = parse_date(values[field])
        values[field] = parsed.date() if parsed else None
    if not valid_url(values["image_url"]):
        values["image_url"] = None
    return (
        AdoptionPromotionResponse(**values)
        if any(value is not None for value in values.values())
        else None
    )


class ReadService:
    def __init__(self, repository, *, today):
        self.repository = repository
        self.today = today

    @contextmanager
    def snapshot(self):
        try:
            with self.repository.snapshot(self.today) as queries:
                yield queries
        except (DatabaseNotConfigured, SQLAlchemyError):
            raise DatabaseUnavailable("Database unavailable") from None

    def animals(self, filters):
        organizations = (
            matching_organizations(sido=filters.sido, sigungu=filters.sigungu)
            if filters.sido is not None or filters.sigungu is not None
            else None
        )
        with self.snapshot() as queries:
            if filters.tag and queries.known_tags(filters.tag) != set(filters.tag):
                raise TagNotFound
            rows, total = queries.list_animals(filters, organizations=organizations)
        pages = (total + filters.page_size - 1) // filters.page_size
        applied = filters.model_dump(exclude={"page", "page_size", "tag"})
        return AnimalListResponse(
            items=[summary(row) for row in rows],
            pagination={
                "page": filters.page,
                "page_size": filters.page_size,
                "total": total,
                "total_pages": pages,
                "has_next": filters.page < pages,
                "has_previous": filters.page > 1 and total > 0,
            },
            applied_filters={**applied, "tags": filters.tag},
        )

    def detail(self, animal_id):
        with self.snapshot() as queries:
            row = queries.animal(animal_id)
            if row is None:
                raise AnimalNotFound
            row = queries.attach_children([row])[0]
        return AnimalDetailResponse(
            id=row["id"],
            source={
                "provider": "국가동물보호정보시스템"
                if row["source"] == "national_animal_api"
                else row["source"],
                "source_id": row["source_id"],
                "source_updated_at": row["source_updated_at"],
            },
            notice={
                "notice_no": row["notice_no"],
                "start_date": row["notice_start"],
                "end_date": row["notice_end"],
                "process_state": row["process_state"],
                "end_reason": row["end_reason"],
            },
            animal={
                name: row[name]
                for name in (
                    "species",
                    "breed",
                    "breed_full",
                    "sex",
                    "neutered",
                    "birth_year",
                    "age_text",
                    "age_group",
                    "weight_kg",
                    "weight_text",
                    "size_group",
                    "color_text",
                    "rfid_code",
                )
            },
            found={
                "date": row["found_date"],
                "place": row["found_place"],
                "region": region_response(row["organization"]),
            },
            images=row["images"],
            tags=[dict(tag, category=CATEGORIES.get(tag["key"])) for tag in row["tags"]],
            safety_badges=generate_safety_badges(row),
            descriptions={
                "special_mark": row["special_mark"],
                "social": row["social_text"],
                "health": row["health_text"],
                "etc": row["etc_text"],
                "vaccination": row["vaccination_text"],
                "health_check": row["health_check_text"],
            },
            shelter={
                "id": row["shelter_id"],
                **{
                    name: row["shelter_" + name]
                    for name in ("name", "phone", "address", "organization")
                },
            }
            if row["shelter_id"] is not None
            else None,
            adoption_promotion=promotion(row),
            first_seen_at=row["first_seen_at"],
            last_seen_at=row["last_seen_at"],
        )

    def similar(self, animal_id, *, limit):
        with self.snapshot() as queries:
            source = queries.animal(animal_id)
            if source is None:
                raise AnimalNotFound
            region = region_for(source["organization"])
            organizations = matching_organizations(sido=region["sido_code"]) if region else []
            rows = queries.similar(source, region_organizations=organizations, limit=limit)
        return SimilarAnimalsResponse(
            source_animal_id=animal_id, items=[summary(row) for row in rows]
        )

    def tags(self, *, type, active_only):
        with self.snapshot() as queries:
            rows = queries.tag_catalog(type=type, active_only=active_only)
        return TagListResponse(
            items=[dict(row, category=CATEGORIES.get(row["key"])) for row in rows]
        )

    def meta(self):
        with self.snapshot() as queries:
            rows = queries.filter_facets()
        counters = defaultdict(Counter)
        for row in rows:
            for name, value in row.items():
                if name != "count" and value is not None:
                    counters[name][value] += row["count"]
        regions = defaultdict(set)
        region_labels = {}
        child_labels = {}
        for organization in counters["organizations"]:
            if region := region_for(organization):
                regions[region["sido_code"]].add(region["sigungu_code"])
                region_labels[region["sido_code"]] = region["sido_name"]
                child_labels[(region["sido_code"], region["sigungu_code"])] = (
                    region["sigungu_name"]
                    or (region["sido_name"] if region["sigungu_code"] == region["sido_code"]
                        else region["sigungu_code"])
                )
        return FilterMetaResponse(
            regions=[
                {
                    "sido": parent,
                    "sigungu": sorted(children),
                    "sido_label": region_labels[parent],
                    "sigungu_labels": {
                        child: child_labels[(parent, child)] for child in sorted(children)
                    },
                }
                for parent, children in sorted(regions.items())
            ],
            breeds=[
                {"value": value, "count": count}
                for value, count in sorted(
                    counters["breeds"].items(), key=lambda pair: (-pair[1], pair[0])
                )
            ],
            process_states=[
                {"value": value, "label": value, "count": count}
                for value, count in sorted(counters["process_states"].items())
            ],
            **{
                name: [
                    {"value": value, "label": label}
                    for value, label in labels.items()
                    if counters[name][value]
                ]
                for name, labels in LABELS.items()
            },
        )

    def stats(self):
        with self.snapshot() as queries:
            values = queries.overview()
        return OverviewStatsResponse(**values)


def read_today():
    # A single KST calendar date per request controls age, status, and today's counts.
    return korea_today(datetime.now(UTC))


def get_read_service(
    database: Annotated[Database, Depends(get_database)],
    today: Annotated[date, Depends(read_today)],
):
    return ReadService(ReadRepository(database), today=today)
