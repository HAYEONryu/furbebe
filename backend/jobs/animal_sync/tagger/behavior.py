"""Conservative TRAIT rules; release authorized under the user's review assumption.

No row-level human labels were supplied. Release authorization is not an empirical
precision claim. Rules absent from the 100-case source sample remain disabled.
"""

import re
from dataclasses import dataclass
from decimal import Decimal

GENERATOR = "rules"
VERSION = "3.0"


@dataclass(frozen=True)
class BehaviorRule:
    rule_id: str
    tag_key: str
    pattern: str
    topic: str


# Keep existing public keys/labels. cautious and active describe semantics, not
# new API keys. Neither walking/rescue context nor generic friendliness suffices.
RULES = (
    BehaviorRule(
        "gentle-explicit-v3", "gentle", r"온순|순(?:함|하고|하며|한성격)", r"온순|순함|순하"
    ),
    BehaviorRule(
        "cautious-explicit-v3",
        "shy",
        r"겁(?:이)?(?:많|있|조금있)|소심|경계심(?:이)?(?:있|많|강)",
        r"겁|소심|경계|낯가림",
    ),
    BehaviorRule("active-explicit-v3", "playful", r"활발|활동적", r"활발|활동적"),
    BehaviorRule("calm-explicit-v3", "calm", r"얌전|차분", r"얌전|차분"),
    BehaviorRule(
        "people-like-v3",
        "people_friendly",
        r"사람(?:을)?(?:너무|매우|엄청|넘)?좋아|사람손길(?:을)?좋아",
        r"사람.*(?:좋아|싫어|경계|무서워)",
    ),
    BehaviorRule(
        "people-follow-v3",
        "people_friendly",
        r"사람(?:을)?잘따(?:름|르|라)",
        r"사람.*(?:따|싫어|경계|무서워)",
    ),
    BehaviorRule(
        "people-approach-v3",
        "people_friendly",
        r"사람에게(?:도)?먼저다가(?:옴|오|감|가)",
        r"사람.*(?:다가|싫어|경계|무서워)",
    ),
    BehaviorRule(
        "affection-explicit-v3",
        "affectionate",
        r"애교(?:가)?(?:많|있)|(?:다가가면|만져주면)발라당|발라당.*만져",
        r"애교|발라당",
    ),
    BehaviorRule(
        "lap-explicit-v3",
        "lap_dog",
        r"무릎(?:강아지|댕댕이)|무릎(?:에|위에)"
        r"(?:앉(?:는것을|기를)|올라오는걸)좋아",
        r"무릎.*(?:강아지|댕댕이|앉|올라)",
    ),
)
RULE_BY_ID = {rule.rule_id: rule for rule in RULES}
ALL_RULE_IDS = frozenset(RULE_BY_ID)
RELEASED_RULE_IDS = frozenset(
    {
        "gentle-explicit-v3",
        "cautious-explicit-v3",
        "active-explicit-v3",
        "calm-explicit-v3",
        "people-like-v3",
        "people-follow-v3",
    }
)
RELEASE_BASIS = "user_assumed_review_complete_without_row_labels"

# Deliberately abstain for the entire sentence, including shared negation across
# commas. Do not turn a negated negative into a positive personality assertion.
NEGATION = re.compile(
    r"없|않|아니|아님|아닌|아닐|아닙|못|싫|안(?:함|해|하|좋|따|다가|온순|순|활발|얌전|차분|경계|보)"
)
UNCERTAIN = re.compile(
    r"추정|같음|같아|같은|보임|듯|미확인|불명|모름|가능성|아직|적응중|으면|[?？]"
)
ADMIN = re.compile(
    r"발견|구조|신고|공고|접수|문의|상담|연락|입양|"
    r"희망자|보호자|봉사|담당자|직원|가족을|가정|환경|센터|보호소|"
    r"홍보|안내|교육|훈련|문구|예시|바람|바랍니다|해주세요|해주실|원하|원해|검토|하는분"
)
TEMPORARY = re.compile(r"입소당시|검진|진료|주사|치료중|수술후|마취|통증|기력|무기력")


@dataclass(frozen=True)
class BehaviorEvidence:
    tag_key: str
    evidence: str
    rule_id: str
    confidence: Decimal = Decimal("0.90")
    generator: str = GENERATOR
    generator_version: str = VERSION


def source_sentences(values):
    raw = values.get("raw_payload")
    fields = [(name, values.get(name)) for name in ("special_mark", "social_text")]
    fields.append(("raw_payload.adptnTxt", raw.get("adptnTxt") if isinstance(raw, dict) else None))
    for field, value in fields:
        if not isinstance(value, str):
            continue
        for match in re.finditer(r"[^.!?;\n\r。！？；]+[.!?;。！？；]?", value):
            sentence = match.group().strip()
            if sentence:
                yield field, sentence, re.sub(r"\s+", "", sentence)


def match_candidates(values, *, rule_ids=ALL_RULE_IDS):
    """One evidence per matching rule; evaluation keeps overlapping rules separate."""
    if set(rule_ids) - ALL_RULE_IDS:
        raise ValueError("Unknown behavior rule")
    sentences = list(source_sentences(values))
    blocked_tags = set()
    for _, _, compact in sentences:
        # A conflicting statement in another source sentence vetoes this tag too.
        # Ambiguous coordination can lower recall; it must not raise coverage.
        if NEGATION.search(compact) or UNCERTAIN.search(compact):
            blocked_tags.update(rule.tag_key for rule in RULES if re.search(rule.topic, compact))
        if re.search(r"사람.*(?:경계|무서워|싫어)", compact):
            blocked_tags.add("people_friendly")
    matches = []
    for rule in RULES:
        if rule.rule_id not in rule_ids or rule.tag_key in blocked_tags:
            continue
        for field, sentence, compact in sentences:
            if any(p.search(compact) for p in (NEGATION, UNCERTAIN, ADMIN, TEMPORARY)):
                continue
            if re.search(rule.pattern, compact):
                matches.append(BehaviorEvidence(rule.tag_key, f"{field}: {sentence}", rule.rule_id))
                break
    return matches


def generate_behavior_tags(values, *, rule_ids=RELEASED_RULE_IDS):
    """No fallback or minimum count. Stable first-rule precedence deduplicates tags."""
    tags = {}
    for match in match_candidates(values, rule_ids=rule_ids):
        tags.setdefault(match.tag_key, match)
    return list(tags.values())
