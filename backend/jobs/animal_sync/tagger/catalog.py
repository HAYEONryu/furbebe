"""Stable API keys; display categories are separate from the existing tag types."""

GROUPS = {
    "personality": [
        ("gentle", "순딩이"),
        ("shy", "소심요정"),
        ("playful", "똥꼬발랄"),
        ("affectionate", "애교쟁이"),
        ("calm", "차분선비댕"),
        ("curious", "호기심대장"),
        ("smart", "똑똑이"),
        ("sensitive", "까칠이"),
    ],
    "relationship": [
        ("people_friendly", "사람좋아"),
        ("outgoing", "적극댕댕이"),
        ("dog_friendly", "친구좋아"),
        ("smiley", "미소천사"),
        ("lap_dog", "무릎댕댕이"),
    ],
    "appearance_color": [
        ("patterned_coat", "삼색이"),
        ("cookies_cream", "쿠앤크"),
        ("brownie", "브라우니"),
        ("cream_coat", "크림이"),
        ("black_coat", "검댕이"),
        ("white_coat", "흰둥이"),
    ],
    "appearance_extra": [
        ("curly", "곱슬몽실"),
        ("pointed_ears", "쫑긋귀"),
        ("wagging_tail", "꼬리콥터"),
        ("fluffy", "복슬복슬"),
    ],
    "size": [
        ("pocket", "쪼꼬미"),
        ("cuddly", "품에쏙"),
        ("sturdy", "댕든든"),
        ("giant", "왕크왕귀"),
    ],
}
CATEGORIES = {key: category for category, entries in GROUPS.items() for key, _ in entries}
CATALOG = [
    {
        "key": key,
        "type": "trait" if category in {"personality", "relationship"} else "vibe",
        "label": label,
        "emoji": None,
        "description": f"보호소 등록 정보에 근거한 {category} 태그",
        "display_order": order,
    }
    for order, (category, key, label) in enumerate(
        (category, key, label) for category, entries in GROUPS.items() for key, label in entries
    )
]
OWNED_KEYS = frozenset(CATEGORIES)
TRAIT_CATALOG = [row for row in CATALOG if row["type"] == "trait"]
TRAIT_KEYS = frozenset(row["key"] for row in TRAIT_CATALOG)
VIBE_KEYS = OWNED_KEYS - TRAIT_KEYS
LEGACY_KEYS = frozenset(
    {
        "tiny",
        "small",
        "medium",
        "large",
        "puppy",
        "young",
        "adult",
        "senior",
        "white",
        "cream",
        "black",
        "brown",
        "bean",
        "cheese",
        "cloud",
        "baby_dog",
        "senior_dog",
    }
)
