"""Rule regressions and scoring arithmetic; synthetic cases are NOT human review."""

import csv
import json
from dataclasses import asdict

import pytest

from backend.jobs.animal_sync.behavior_review import (
    evaluate,
    export_label_template,
    load_labels,
    load_sample,
    source_digest,
)
from backend.jobs.animal_sync.tagger.behavior import (
    ALL_RULE_IDS,
    RELEASED_RULE_IDS,
    RULES,
    generate_behavior_tags,
    match_candidates,
)

POSITIVES = {
    "gentle-explicit-v3": "온순함",
    "cautious-explicit-v3": "겁이 많음",
    "active-explicit-v3": "활발함",
    "calm-explicit-v3": "얌전함",
    "people-like-v3": "사람을 좋아함",
    "people-follow-v3": "사람을 잘 따름",
    "people-approach-v3": "사람에게 먼저 다가옴",
    "affection-explicit-v3": "애교가 많음",
    "lap-explicit-v3": "무릎강아지",
}


@pytest.mark.parametrize("rule", RULES, ids=lambda rule: rule.rule_id)
@pytest.mark.parametrize("field", ("special_mark", "social_text", "adptnTxt"))
def test_each_rule_positive_original_evidence_and_metadata(rule, field):
    sentence = POSITIVES[rule.rule_id] + "."
    values = {"raw_payload": {field: sentence}} if field == "adptnTxt" else {field: sentence}
    matches = match_candidates(values, rule_ids={rule.rule_id})
    assert len(matches) == 1
    result = asdict(matches[0])
    assert result["tag_key"] == rule.tag_key
    assert result["evidence"].endswith(sentence)
    assert result["generator"] == "rules" and result["generator_version"] == "3.0"
    assert 0 < result["confidence"] < 1
    assert result["rule_id"] == rule.rule_id


@pytest.mark.parametrize("rule", RULES, ids=lambda rule: rule.rule_id)
@pytest.mark.parametrize("kind", ("negative", "negation", "administrative", "uncertain", "mixed"))
def test_each_rule_guards_and_mixed_health_behavior(rule, kind):
    positive = POSITIVES[rule.rule_id]
    sentence = {
        "negative": "갈색 목걸이 착용",
        "negation": positive + " 아님",
        "administrative": "입양 홍보 문구: " + positive,
        "uncertain": positive + "으로 추정",
        "mixed": positive + ". 피부질환 있음. 심장사상충 음성.",
    }[kind]
    result = match_candidates({"special_mark": sentence}, rule_ids={rule.rule_id})
    assert bool(result) is (kind == "mixed")
    assert not match_candidates({"health_text": positive}, rule_ids={rule.rule_id})


@pytest.mark.parametrize(
    "sentence",
    [
        "사람을 좋아하지 않음",
        "사람을 전혀 좋아하지 않음",
        "사람 안 좋아함",
        "사람을 잘 따르지 않음",
        "사람에게 먼저 다가오지 않음",
        "사람을 경계하지 않음",
        "경계심 없음",
        "겁이 많지 않음",
        "소심하지 않음",
        "소심함은 아님",
        "산책 중 발견",
        "산책을 좋아함",
        "활발한 입양 홍보",
        "활발한 입양 문의",
        "차분한 환경 필요",
        "온순한 보호자 희망",
        "사람을 좋아하는 분의 입양을 기다림",
        "사람을 좋아하는 분",
        "친화적인 보호소 직원",
        "얌전한 성격으로 추정",
        "치료 중 얌전함",
        "마취 후 차분함",
        "활발함 없음",
        "온순, 얌전하지 않음",
        "애교와 활발함 없음",
        "발라당",
        "무릎 관절 수술",
        "애교가 많음?",
        "온순함이 아닐까",
        "사람이 좋아하는 강아지",
        "강아지를 좋아함",
        "먼저 다가오는 보호자",
        "활발해졌으면 함",
        "건강 양호",
    ],
)
def test_collisions_and_negation_abstain(sentence):
    assert match_candidates({"special_mark": sentence}) == []


def test_conflicting_fields_shared_negation_dedupe_and_conservative_release():
    values = {"special_mark": "사람을 좋아함. 온순함.", "social_text": "사람을 좋아하지 않음"}
    assert {tag.tag_key for tag in match_candidates(values)} == {"gentle"}
    assert not match_candidates({"special_mark": "사람", "social_text": "좋아함"})
    assert not match_candidates({"special_mark": "사람. 좋아함"})
    values = {"special_mark": "사람을 좋아함. 사람을 잘 따름. 사람에게 먼저 다가옴."}
    assert len(match_candidates(values)) == 3
    assert len(generate_behavior_tags(values, rule_ids=ALL_RULE_IDS)) == 1
    assert [tag.tag_key for tag in generate_behavior_tags(values)] == ["people_friendly"]
    for rule in RULES:
        assert bool(generate_behavior_tags({"special_mark": POSITIVES[rule.rule_id]})) is (
            rule.rule_id in RELEASED_RULE_IDS
        )
    with pytest.raises(ValueError, match="Unknown behavior rule"):
        match_candidates(values, rule_ids={"invented"})


def test_approved_belly_phrase_maps_to_affection_not_a_new_tag():
    matches = match_candidates({"special_mark": "다가가면 발라당 누워서 만져주라고 함"})
    assert [tag.tag_key for tag in matches] == ["affectionate"]


@pytest.fixture
def review_rows():
    return [
        {
            "desertionNo": str(i),
            "specialMark": "온순함" if i < 2 else "목줄 착용",
            "stratum": ("behavior", "health", "administrative_or_meaningless", "random")[i // 25],
        }
        for i in range(100)
    ]


def test_confusion_counts_per_tag_rule_and_no_truth_is_not_zero(review_rows):
    pending = evaluate(review_rows)
    assert pending["metrics"] is None and pending["human_label_count"] == 0
    assert pending["status"] == "unmeasured_user_assumed_review"
    assert pending["human_precision_measured"] is False
    assert set(pending["release_enabled"]) == RELEASED_RULE_IDS
    truth = {str(i): {"gentle"} if i in (0, 2) else set() for i in range(100)}
    metrics = evaluate(review_rows, truth)["metrics"]
    assert metrics["micro"] == {
        "true_positive": 1,
        "false_positive": 1,
        "false_negative": 1,
        "precision": 0.5,
        "recall_in_sample": 0.5,
    }
    for result in (metrics["by_tag"]["gentle"], metrics["by_rule"]["gentle-explicit-v3"]):
        assert (result["true_positive"], result["false_positive"], result["false_negative"]) == (
            1,
            1,
            1,
        )
        assert result["true_negative"] == 97
    assert metrics["by_tag"]["lap_dog"]["precision"] is None
    assert metrics["by_rule"]["gentle-explicit-v3"]["eligible_for_release_review"] is False
    assert metrics["cases"][1]["false_positive"] == ["gentle"]
    assert metrics["cases"][2]["false_negative"] == ["gentle"]


def test_rule_overlap_not_double_counted_in_tag_metrics(review_rows):
    review_rows[0]["specialMark"] = "사람을 좋아함. 사람을 잘 따름."
    truth = {str(i): {"people_friendly"} if i == 0 else set() for i in range(100)}
    report = evaluate(review_rows, truth)
    assert report["candidate_counts"]["people_friendly"] == 1
    assert report["metrics"]["by_tag"]["people_friendly"]["true_positive"] == 1
    for rule_id in ("people-like-v3", "people-follow-v3"):
        assert report["metrics"]["by_rule"][rule_id]["true_positive"] == 1


def test_export_separates_predictions_from_human_truth_and_never_overwrites(tmp_path, review_rows):
    path = tmp_path / "new-review.csv"
    export_label_template(path, review_rows)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 100
    assert rows[0]["candidate_tags"] == '["gentle"]'
    assert all(row["human_tags"] == row["reviewed_by"] == row["reviewed_at"] == "" for row in rows)
    assert rows[0]["source_sha256"] == source_digest(review_rows[0])
    with pytest.raises(FileExistsError):
        export_label_template(path, review_rows)
    with pytest.raises(ValueError, match="Human reviewer"):
        load_labels(path, review_rows)
    # Synthetic truth only: never use this fixture as real review metrics.
    for row in rows:
        row.update(human_tags="[]", reviewed_by="TEST FIXTURE", reviewed_at="2026-09-23")
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    assert load_labels(path, review_rows) == {str(i): set() for i in range(100)}
    review_rows[0]["specialMark"] = "changed source"
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        load_labels(path, review_rows)


def test_sample_join_restores_adoption_description(tmp_path, review_rows):
    raw, sample = tmp_path / "raw.jsonl", tmp_path / "sample.csv"
    review_rows[0]["adptnTxt"] = "사람을 좋아함"
    raw.write_text(
        json.dumps(
            {
                "response": {
                    "response": {
                        "body": {
                            "items": {"item": review_rows},
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    with sample.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("desertionNo", "stratum"))
        writer.writeheader()
        writer.writerows({k: row[k] for k in ("desertionNo", "stratum")} for row in review_rows)
    assert load_sample(raw, sample)[0]["adptnTxt"] == "사람을 좋아함"
    with pytest.raises(ValueError, match="100 distinct"):
        evaluate(review_rows[:99])
    with pytest.raises(ValueError, match="Incomplete"):
        evaluate(review_rows, {})
