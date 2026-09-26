from datetime import date

import pytest

from backend.jobs.animal_sync.client import Redactor
from backend.jobs.animal_sync.field_stats import parse_age
from backend.jobs.animal_sync.metrics import build_profile, shelter_region_profile
from backend.jobs.animal_sync.observations import color_candidate, profile_observations
from backend.jobs.animal_sync.reports import measured_overview


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026(60일미만)(년생)", 2026),
        ("2026(년생)", 2026),
        ("(년생)", None),
        ("2026(90일미만)(년생)", None),
        ("2026(60일미만)", None),
    ],
)
def test_observed_age_annotation(value, expected):
    assert parse_age(value) == expected


def test_island_name_is_not_inferred_to_be_a_province():
    result = shelter_region_profile(
        [
            {
                "desertionNo": "001",
                "orgNm": "인천광역시 중구",
                "careAddr": "인천광역시 중구",
                "happenPlace": "월미도 선착장",
            }
        ],
        Redactor(),
    )
    assert result["source_prefixes"]["happenPlace"] == {"[unresolved]": 1}
    assert result["raw_prefix_disagreements"] == 0
    assert result["normalization_status"] == "decision_required"


def test_color_candidates_do_not_force_unknown_compounds():
    assert color_candidate("갈색&흰색") == ["brown", "white"]
    assert color_candidate("크림색") == ["cream"]
    assert color_candidate("기타(믹스)") is None
    assert color_candidate("엷은 황갈색&흰색") is None


def test_proposed_groups_retain_unknown_and_source_annotation():
    rows = [
        {"age": "2026(60일미만)(년생)", "weight": "0(Kg)", "processState": "보호중"},
        {"age": "2027(년생)", "weight": "5(Kg)", "processState": "종료(입양)"},
    ]
    result = profile_observations(rows, date(2026, 9, 14), Redactor())
    assert result["proposed_size_groups"] == {"unknown": 1, "tiny": 1}
    assert result["contract_size_groups_before_quality_policy"] == {"tiny": 2}
    assert result["proposed_age_groups"] == {"puppy": 1, "unknown": 1}
    assert result["animals_active_candidate_protecting_only"] == 1
    assert result["age_formats"]["under_60_days_annotation"] == 1
    assert rows[0]["age"] == "2026(60일미만)(년생)"


def test_calendar_gap_does_not_claim_absolute_update_lag():
    result = profile_observations(
        [{"updTm": "2026-09-13 23:59:00.0"}], date(2026, 9, 14), Redactor()
    )
    assert result["updTm_calendar_date_gap_days"]["median"] == 1
    assert "Not an absolute source-update lag" in result["update_gap_note"]


def test_non_dog_capture_still_renders_diagnostic_report():
    summary, _ = build_profile(
        [{"desertionNo": "cat-001", "upKindNm": "고양이"}],
        {},
        Redactor(),
        today=date(2026, 9, 14),
    )
    assert "no_confirmed_dog_records" in summary["blockers"]
    assert "not measured" in measured_overview(summary)
