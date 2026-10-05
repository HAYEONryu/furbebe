"""Validated source -> normalized domain DTOs; no SQL and no inferred descriptions."""

from dataclasses import dataclass
from datetime import UTC, date
from decimal import Decimal
from typing import Any

from .parsing import (
    IMAGE_FIELDS,
    animal_images,
    meaningful,
    parse_age,
    parse_date,
    parse_weight_decimal,
    text,
)
from .source_models import ValidatedAnimal

SOURCE = "national_animal_api"
TEXT_MAPPING = {
    "notice_no": "noticeNo",
    "rfid_code": "rfidCd",
    "breed": "kindNm",
    "breed_full": "kindFullNm",
    "age_text": "age",
    "weight_text": "weight",
    "color_text": "colorCd",
    "found_place": "happenPlace",
    "process_state": "processState",
    "end_reason": "endReason",
    "special_mark": "specialMark",
    "social_text": "sfeSoci",
    "health_text": "sfeHealth",
    "etc_text": "etcBigo",
    "vaccination_text": "vaccinationChk",
    "health_check_text": "healthChk",
}


def nullable_text(value) -> str | None:
    return text(value) if meaningful(value) else None


@dataclass(frozen=True)
class NormalizedAnimal:
    values: dict[str, Any]
    shelter: dict[str, Any] | None
    images: tuple[str, ...]
    issues: tuple[str, ...] = ()


def normalize_animal(item: ValidatedAnimal, *, today: date) -> NormalizedAnimal:
    raw = item.model_dump(exclude_unset=True)
    values = {name: nullable_text(raw.get(field)) for name, field in TEXT_MAPPING.items()}
    issues = []
    weight = parse_weight_decimal(item.weight)
    if weight is not None and weight < 0:
        weight = None
    birth_year = parse_age(item.age)
    if birth_year is not None and not 1 <= birth_year <= today.year:
        birth_year = None
    if meaningful(item.weight) and weight is None:
        issues.append("weight_unparsed")
    if meaningful(item.age) and birth_year is None:
        issues.append("age_unparsed")
    species = {"417000": "dog", "422400": "cat", "429900": "other"}.get(item.upKindCd)
    named_species = {"개": "dog", "고양이": "cat", "기타": "other"}.get(item.upKindNm)
    if species and named_species and species != named_species:
        species = None
        issues.append("species_conflict")
    else:
        species = species or named_species
    values.update(
        source=SOURCE,
        source_id=item.desertionNo.strip(),
        raw_payload=raw,
        species=species,
        weight_kg=weight,
        birth_year=birth_year,
        sex={"M": "male", "F": "female", "Q": "unknown"}.get(item.sexCd),
        neutered={"Y": "yes", "N": "no", "U": "unknown"}.get(item.neuterYn),
    )
    for target, field in (
        ("found_date", "happenDt"),
        ("notice_start", "noticeSdt"),
        ("notice_end", "noticeEdt"),
    ):
        parsed = parse_date(raw.get(field))
        values[target] = parsed.date() if parsed else None
    updated = parse_date(item.updTm)
    values["source_updated_at"] = updated.astimezone(UTC) if updated and updated.tzinfo else None
    if updated and not updated.tzinfo:
        issues.append("source_timestamp_timezone_unknown")
    shelter = None
    if source_id := nullable_text(item.careRegNo):
        shelter = {"source": SOURCE, "source_id": source_id}
        shelter.update(
            {
                name: nullable_text(raw.get(field))
                for name, field in (
                    ("name", "careNm"),
                    ("phone", "careTel"),
                    ("address", "careAddr"),
                    ("owner_name", "careOwnerNm"),
                    ("organization", "orgNm"),
                )
            }
        )
    # Shared URL validator/deduplicator retains the source order; trim before validation.
    image_values = {name: text(raw.get(name)) for name in IMAGE_FIELDS}
    images = tuple(animal_images(image_values))
    return NormalizedAnimal(values, shelter, images, tuple(issues))


def size_group(weight: Decimal | None) -> str:
    if weight is None:
        return "unknown"
    for upper, group in ((5, "tiny"), (10, "small"), (20, "medium")):
        if weight <= upper:
            return group
    return "large"


def age_group(birth_year: int | None, *, year: int) -> str:
    if birth_year is None:
        return "unknown"
    age = year - birth_year
    for upper, group in ((1, "puppy"), (4, "young"), (9, "adult")):
        if age <= upper:
            return group
    return "senior"
