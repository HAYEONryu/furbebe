"""Approved examples, user overrides and false-positive regression cases."""

from datetime import date

import pytest

from backend.jobs.animal_sync.normalizer import NormalizedAnimal
from backend.jobs.animal_sync.tagger import (
    CATALOG,
    CATEGORIES,
    generate_safety_badges,
    generate_tags,
)

TODAY = date(2026, 9, 23)
LABELS = {row["key"]: row["label"] for row in CATALOG}


def tags(**values):
    return generate_tags(NormalizedAnimal(values, None, ()), today=TODAY)


def labels(**values):
    return {LABELS[tag.tag_key] for tag in tags(**values)}


@pytest.mark.parametrize(
    "text,color,weight,expected",
    [
        (
            "온순함, 사람을 잘 따름, 활발함",
            "갈색",
            "6.2",
            {"순딩이", "사람좋아", "똥꼬발랄", "브라우니", "품에쏙"},
        ),
        (
            "겁이 많고 사람을 경계함. 피부병 있음.",
            "크림색",
            "4.2",
            {"소심요정", "크림이", "쪼꼬미"},
        ),
        (
            "애교 많고 사람 엄청 좋아함. 모르는 사람보고 꼬리를 마구 흔듦.",
            "갈색&흰색",
            "3",
            {"사람좋아", "꼬리콥터", "브라우니", "쪼꼬미"},
        ),
        ("겁 있음. 방어적 입질. 털 상태 양호.", "흰색", "6.3", {"소심요정", "흰둥이", "품에쏙"}),
        (
            "온순. 얌전. 사람 좋아함. 양 눈 백내장. 피부질환.",
            "흰색",
            "5.7",
            {"순딩이", "차분선비댕", "사람좋아", "흰둥이", "품에쏙"},
        ),
        (
            "호기심 많고 활발함. 사람에게 먼저 다가오는 성격.",
            "검정&흰색",
            "22.4",
            {"똥꼬발랄", "쿠앤크", "왕크왕귀"},
        ),
        ("순함", "청회색", "8", {"순딩이", "품에쏙"}),
    ],
)
def test_document_examples_without_health_tags(text, color, weight, expected):
    assert labels(special_mark=text, color_text=color, weight_kg=weight) == expected


@pytest.mark.parametrize(
    "color,expected",
    [
        ("연갈색", "브라우니"),
        ("옅은 갈색", "브라우니"),
        ("옅은 갈색&흰색", "브라우니"),
        ("흑갈색", "브라우니"),
        ("흰색&갈색&탄", "브라우니"),
        ("갈색 밤색 황갈색", "브라우니"),
        ("레몬색&흰색", "브라우니"),
        ("주황&흰색", "브라우니"),
        ("금색&흰색", "브라우니"),
        ("크림", "크림이"),
        ("옅은 황색", "크림이"),
        ("연베이지", "크림이"),
        ("검정&흰색", "쿠앤크"),
        ("흑백", "쿠앤크"),
        ("흰색+흑갈색", "브라우니"),
        ("갈색/검정/흰색", "삼색이"),
        ("흰색 검은 반점", "삼색이"),
        ("호반색", "삼색이"),
        ("Brindle", "삼색이"),
        ("얼룩무늬", "삼색이"),
        ("흑", "검댕이"),
        ("백", "흰둥이"),
        ("회색", None),
        ("청회색", None),
        ("흰색&회색", None),
        ("검정&실버", None),
        ("갈색&회색", None),
        ("흰색&검정&회색", None),
        ("회색 호피", None),
        ("기타(믹스)", None),
        (None, None),
    ],
)
def test_single_color_and_user_overrides(color, expected):
    assert labels(color_text=color) == ({expected} if expected else set())


def test_color_source_precedence_and_fallback():
    assert labels(color_text="기타(믹스)", special_mark="갈색 털") == {"브라우니"}
    assert labels(special_mark="흰색 털") == {"흰둥이"}
    assert labels(color_text="크림색", special_mark="호피 무늬") == {"크림이"}
    assert labels(color_text="흰색&회색", special_mark="흰색 털") == set()
    assert labels(special_mark="피부에 반점. 검정 목줄 착용. 백내장.") == set()
    assert labels(color_text="black white") == {"쿠앤크"}
    assert labels(special_mark="흰색, 회색") == set()
    assert labels(special_mark="검정, 갈색, 흰색") == {"삼색이"}


@pytest.mark.parametrize(
    "weight,expected",
    [
        (0, "쪼꼬미"),
        ("4.99", "쪼꼬미"),
        (5, "품에쏙"),
        ("9.99", "품에쏙"),
        (10, "댕든든"),
        ("19.99", "댕든든"),
        (20, "왕크왕귀"),
        ("200", "왕크왕귀"),
        (None, None),
        ("invalid", None),
        (-1, None),
        ("NaN", None),
        ("Infinity", None),
    ],
)
def test_current_weight_boundaries(weight, expected):
    assert labels(weight_kg=weight) == ({expected} if expected else set())


@pytest.mark.parametrize(
    "text",
    [
        "입질 없음. 공격성 없음.",
        "입질하지 않음",
        "공격성이 전혀 없음",
        "입질 및 공격성 없음",
        "겁이 많음. 경계심 있음.",
        "온순하지 않음",
        "애교가 많지 않음",
        "예민하지 않음",
        "사람 잘 따르지 않음",
        "사람 좋아하지 않음",
        "꼬리 단미 안됨",
        "꼬리를 흔들지 않음",
    ],
)
def test_negation_and_context(text):
    assert generate_safety_badges({"special_mark": text}) == []
    assert labels(special_mark=text) <= {"소심요정"}


@pytest.mark.parametrize(
    "text,expected",
    [
        ("방어적 입질. 온순한 편.", {"입질주의"}),
        ("으르렁. 물려고 함.", {"입질주의"}),
        ("사나움", {"강한경계"}),
        ("경계가 매우 심함", {"강한경계"}),
        ("경계심 매우 강함", {"강한경계"}),
        ("공격성이 강함. 입질.", {"입질주의", "강한경계"}),
        ("입질 없음. 안으려고 하면 입질.", {"입질주의"}),
    ],
)
def test_safety_is_separate_and_retains_positive_evidence(text, expected):
    badges = generate_safety_badges({"special_mark": text})
    assert {badge["label"] for badge in badges} == expected
    assert all(badge["evidence"].startswith("special_mark:") for badge in badges)
    assert not (expected & labels(special_mark=text))


def test_all_text_fields_dedupe_order_and_no_inference():
    actual = tags(
        special_mark="온순. 곱슬. 쫑긋한 귀",
        social_text="사람잘따름, 온순함",
        health_text="겁 있음. 건강상태 양호. 치료 필요",
        color_text="흰색",
        weight_kg=4,
        sex="male",
        birth_year=2026,
        vaccination_text="백신",
        neutered="yes",
    )
    assert [tag.tag_key for tag in actual] == [
        "gentle",
        "people_friendly",
        "white_coat",
        "curly",
        "pointed_ears",
        "pocket",
    ]
    assert all(tag.evidence and 0 < tag.confidence <= 1 for tag in actual)
    assert (
        labels(health_text="건강양호. 백내장. 수술. 사상충 양성. 치료 필요", birth_year=2026)
        == set()
    )
    assert labels(special_mark="사람", social_text="좋아함") == set()
    assert labels(special_mark="사람/좋아함") == set()
    assert labels(special_mark="사람에게 경계심 있음") == {"소심요정"}
    assert labels(special_mark="모르는 사람에게도 먼저 다가옴") == set()
    assert "health" not in CATEGORIES.values()


@pytest.mark.parametrize(
    "text",
    [
        "입질: 없음",
        "공격성(없음)",
        "다른 강아지와 잘 지내지 않음",
        "곱슬 아님",
    ],
)
def test_qualified_negation(text):
    assert labels(special_mark=text) == set()
    assert generate_safety_badges({"special_mark": text}) == []


@pytest.mark.parametrize(
    "text,expected",
    [
        ("다가가면 발라당 누워서 만져주라고 함", set()),
        ("발라당을 좋아함. 애교 많음", set()),
        ("애교가 풍성함", set()),
        ("무릎강아지", set()),
        ("무릎 강아지", set()),
        ("무릎댕댕이", set()),
        ("무릎에 앉는 것을 좋아함", set()),
        ("무릎 위에 앉기를 좋아함", set()),
        ("무릎 위에 올라오는 걸 좋아함", set()),
        ("복슬복슬한 털", {"복슬복슬"}),
        ("복실복실함", {"복슬복슬"}),
        ("털이 풍성한 편", {"복슬복슬"}),
        ("털숱이 매우 풍성함", {"복슬복슬"}),
        ("풍성한 털", {"복슬복슬"}),
    ],
)
def test_held_affection_lap_and_preserved_fluffy_phrases(text, expected):
    assert labels(special_mark=text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "발라당하지 않음",
        "발라당을 좋아하지 않음",
        "발라당 안함",
        "무릎강아지 아님",
        "무릎에 앉는 것을 좋아하지 않음",
        "무릎 관절 이상",
        "무릎 수술",
        "무릎 부상",
        "안기는 것을 싫어함",
        "복슬복슬하지 않음",
        "복슬한 털이 아님",
        "털이 풍성하지 않음",
        "풍성한 털 아님",
        "장모종",
        "긴 털",
        "처진 귀",
        "팔랑귀",
    ],
)
def test_new_tags_require_their_own_positive_evidence(text):
    assert labels(special_mark=text) == set()


def test_new_tags_combine_without_adding_a_second_color_or_duplicate_affection():
    actual = tags(
        special_mark="애교 많음. 발라당. 무릎강아지. 복슬복슬. 곱슬",
        social_text="발라당. 무릎에 앉는 것을 좋아함",
        health_text="무릎 관절 이상. 피부질환",
        color_text="옅은 갈색",
        weight_kg=4,
    )
    assert [tag.tag_key for tag in actual] == [
        "brownie",
        "curly",
        "fluffy",
        "pocket",
    ]
    assert CATEGORIES["lap_dog"] == "relationship"
    assert CATEGORIES["fluffy"] == "appearance_extra"
    assert labels(social_text="무릎강아지", health_text="복슬한 털") == {"복슬복슬"}
    assert not ({"발라당", "무릎친구", "팔랑귀"} & set(LABELS.values()))
