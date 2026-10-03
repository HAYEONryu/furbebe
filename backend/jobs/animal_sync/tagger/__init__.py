"""Source-backed character tags. Health, age and sex never generate tags."""

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from ..normalizer import NormalizedAnimal
from .behavior import generate_behavior_tags
from .catalog import CATALOG, CATEGORIES, LEGACY_KEYS, OWNED_KEYS
from .colors import pick_color

__all__ = [
    "CATALOG",
    "CATEGORIES",
    "GENERATOR",
    "LEGACY_KEYS",
    "OWNED_KEYS",
    "VERSION",
    "generate_tags",
    "generate_safety_badges",
]
GENERATOR = "rules"
VERSION = "2.0"
TEXT_FIELDS = ("special_mark", "social_text", "health_text")

# Patterns run on compact clauses, never across punctuation or source fields.
PATTERNS = {
    "curly": r"곱슬",
    "pointed_ears": r"쫑긋",
    "wagging_tail": r"꼬리(?:를)?(?:마구)?흔(?:듦|드는|들)|꼬리살랑|꼬리치며",
    "fluffy": r"복슬(?:복슬)?(?:한털)?|복실(?:복실)?(?:한털)?"
    r"|털(?:숱)?(?:이|은)?(?:매우|아주|엄청|너무)?풍성|풍성한털",
}
SAFETY_PATTERNS = {
    "bite_caution": ("입질주의", r"입질|물려고|으르렁"),
    "strong_guarding": ("강한경계", r"공격성|사나(?:움|운|워)|경계(?:가|심이?)매우(?:심|강)"),
}
NEGATIVE = re.compile(
    r"^(?:성이|성은|심이|심은|이|가|은|는|을|를|도)?"
    r"(?:전혀|거의|별로)?(?:많이|많|함|한편|한|하|해|적|다|좋아)?"
    r"(?:(?:하지|있지|지)(?:는|도)?)?"
    r"(?:없|않|아니|아님|못|안함|안해|안보|불명|미확인)"
)


@dataclass(frozen=True)
class TagEvidence:
    tag_key: str
    evidence: str
    rule_id: str
    confidence: Decimal = Decimal("1")
    generator: str = GENERATOR
    generator_version: str = VERSION


def clauses(values):
    for field in TEXT_FIELDS:
        for clause in re.split(r"[.,;/|!?\n\r]+", values.get(field) or ""):
            original = " ".join(clause.split())
            if original:
                yield field, original, re.sub(r"\s+", "", original).lower()


def positive_match(pattern, compact):
    for match in re.finditer(pattern, compact):
        before = compact[: match.start()]
        after = compact[match.end() :].lstrip(":：([{")
        if before.endswith(("안", "못")) or NEGATIVE.match(after):
            continue
        # Shared negation: "입질 및 공격성 없음" must negate both terms.
        if re.match(r"^(?:및|과|와)", after) and re.search(r"(?:없|않|아니)", after):
            continue
        return True
    return False


def text_evidence(values, pattern):
    return next(
        (
            f"{field}: {original}"
            for field, original, compact in clauses(values)
            if positive_match(pattern, compact)
        ),
        None,
    )


def generate_safety_badges(values):
    """Separate API field, recomputed from the stored source snapshot on reads."""
    return [
        {"key": key, "label": label, "evidence": evidence}
        for key, (label, pattern) in SAFETY_PATTERNS.items()
        if (evidence := text_evidence(values, pattern))
    ]


def generate_tags(animal: NormalizedAnimal, *, today: date) -> list[TagEvidence]:
    values = animal.values
    tags = [
        TagEvidence(key, evidence, f"{key}-v2")
        for key, pattern in PATTERNS.items()
        if (evidence := text_evidence(values, pattern))
    ]
    tags.extend(TagEvidence(**vars(tag)) for tag in generate_behavior_tags(values))
    if color := pick_color(values.get("color_text"), values.get("special_mark")):
        key, evidence = color
        tags.append(TagEvidence(key, evidence, "single-color-v2"))
    try:
        weight = Decimal(str(values.get("weight_kg")))
    except (InvalidOperation, ValueError):
        weight = Decimal("NaN")
    if weight.is_finite() and weight >= 0:
        key = next(
            (
                key
                for upper, key in ((5, "pocket"), (10, "cuddly"), (20, "sturdy"))
                if weight < upper
            ),
            "giant",
        )
        tags.append(TagEvidence(key, f"weight_kg={weight}; 현재 몸집", "current-size-v2"))
    order = {row["key"]: row["display_order"] for row in CATALOG}
    unique = {tag.tag_key: tag for tag in tags}
    return sorted(unique.values(), key=lambda tag: order[tag.tag_key])
