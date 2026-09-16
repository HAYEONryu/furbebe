"""Small, explicit structured FACT rules and their presentation-only VIBE mapping."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ..normalizer import NormalizedAnimal, age_group, size_group

GENERATOR = "rules"
VERSION = "1.0"
FACT_LABELS = {
    "tiny": "5kg 이하",
    "small": "5kg 초과~10kg",
    "medium": "10kg 초과~20kg",
    "large": "20kg 초과",
    "puppy": "추정 1세 이하",
    "young": "추정 2~4세",
    "adult": "추정 5~8세",
    "senior": "추정 9세 이상",
    "white": "흰색",
    "cream": "크림색",
    "black": "검정색",
    "brown": "갈색",
}
VIBES = {
    "tiny": ("bean", "콩만이", "🫘"),
    "cream": ("cheese", "치즈", "🧀"),
    "white": ("cloud", "구름이", "☁️"),
    "puppy": ("baby_dog", "아가댕", "🐣"),
    "senior": ("senior_dog", "어르신댕", "👴"),
}
# Whole-field matches only. Mixed colors and descriptive prose remain untagged.
COLOR_FACTS = {
    "흰색": "white",
    "백색": "white",
    "하양": "white",
    "white": "white",
    "크림색": "cream",
    "크림": "cream",
    "cream": "cream",
    "검정색": "black",
    "검정": "black",
    "검은색": "black",
    "black": "black",
    "갈색": "brown",
    "brown": "brown",
}
CATALOG = [
    {
        "key": key,
        "type": "fact",
        "label": label,
        "emoji": None,
        "description": "구조화된 원천 필드의 탐색용 사실",
        "display_order": order,
    }
    for order, (key, label) in enumerate(FACT_LABELS.items())
] + [
    {
        "key": key,
        "type": "vibe",
        "label": label,
        "emoji": emoji,
        "description": f"{fact} FACT에 대응하는 표시 이름; 성격 추론 아님",
        "display_order": 100 + order,
    }
    for order, (fact, (key, label, emoji)) in enumerate(VIBES.items())
]
OWNED_KEYS = frozenset(row["key"] for row in CATALOG)


@dataclass(frozen=True)
class TagEvidence:
    tag_key: str
    evidence: str
    rule_id: str
    confidence: Decimal = Decimal("1")


def generate_tags(animal: NormalizedAnimal, *, today: date) -> list[TagEvidence]:
    values = animal.values
    facts = []
    # The approved size and age UX was evaluated on dogs, not all species.
    if values["species"] == "dog":
        size = size_group(values["weight_kg"])
        if size != "unknown":
            facts.append(
                TagEvidence(size, f"weight_kg={values['weight_kg']}; source=weight", "size-a-v1")
            )
        age = age_group(values["birth_year"], year=today.year)
        if age != "unknown":
            facts.append(
                TagEvidence(
                    age,
                    f"birth_year={values['birth_year']}; as_of_year={today.year}; estimated",
                    "age-a-v1",
                )
            )
    color = COLOR_FACTS.get((values["color_text"] or "").lower())
    if color:
        facts.append(TagEvidence(color, f"colorCd={values['color_text']}", "color-exact-v1"))
    vibes = [
        TagEvidence(VIBES[f.tag_key][0], f"fact={f.tag_key}; {f.evidence}", "fact-vibe-v1")
        for f in facts
        if f.tag_key in VIBES
    ]
    return facts + vibes
