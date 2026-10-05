"""Boundary, persistence and failure tests; no live service key or network."""

import json
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest

from backend.jobs.animal_sync.client import AnimalApiClient, ApiFailure, Page
from backend.jobs.animal_sync.metrics import apply_reference_results
from backend.jobs.animal_sync.reference_cache import ReferenceCache
from backend.jobs.animal_sync.references import analyze_references, region_index
from backend.jobs.animal_sync.region_evidence import scoped_memberships
from backend.jobs.animal_sync.reports import write_reference_report
from backend.jobs.animal_sync.status_policy import display_status, korea_today


def page(rows, total=None, number=1):
    return Page(number, len(rows) if total is None else total, rows, "array", {}, {}, 1000)


class FakeClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def fetch_reference(self, resource, number, size, *, filters):
        self.calls.append((resource, number, filters))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.mark.parametrize("raw", ["종료(입양)", "종료(반환)", "새로운 원문 상태", None])
def test_non_protecting_status_is_never_converted(raw):
    row = {"processState": raw, "noticeSdt": "20200101"}
    assert display_status(row, today=date(2026, 9, 14))["display_state"] == raw
    assert row["processState"] == raw


@pytest.mark.parametrize("notice", [None, "", "20260230", "2026-09-01", 20260901])
def test_unknown_notice_start_never_creates_adoptable_label(notice):
    result = display_status(
        {"processState": "보호중", "noticeSdt": notice}, today=date(2026, 9, 14)
    )
    assert result["display_state"] == "보호중"
    assert result["issue"] == "invalid_or_missing_notice_start"


def test_future_notice_and_korean_date_boundary():
    now = datetime(2026, 9, 13, 15, 0, tzinfo=UTC)
    assert korea_today(now) == date(2026, 9, 14)
    assert korea_today(now - timedelta(seconds=1)) == date(2026, 9, 13)
    row = {"processState": "보호중", "noticeSdt": "20260904", "noticeEdt": "20260930"}
    assert display_status(row, today=korea_today(now))["display_state"] == "입양 가능"
    assert (
        display_status(row, today=korea_today(now - timedelta(seconds=1)))["display_state"]
        == "보호중"
    )
    row["noticeSdt"] = "20260915"
    assert display_status(row, today=korea_today(now))["issue"] == "future_notice_start"
    with pytest.raises(ValueError):
        korea_today(datetime(2026, 9, 14))


@pytest.mark.parametrize("wrapped", [True, False])
def test_reference_client_uses_requested_endpoint_and_parent(wrapped):
    def handler(request):
        assert request.url.scheme == "https"
        assert request.url.path.endswith("/sigungu_v2")
        assert request.url.params["upr_cd"] == "6110000"
        payload = {
            "header": {"resultCode": "00"},
            "body": {
                "totalCount": "1",
                "pageNo": "1",
                "items": {"item": {"orgCd": "3220000", "uprCd": "6110000", "orgdownNm": "강남구"}},
            },
        }
        return httpx.Response(200, json={"response": payload} if wrapped else payload)

    with AnimalApiClient("synthetic-unit-key", transport=httpx.MockTransport(handler)) as client:
        result = client.fetch_reference("sigungu", 1, 1000, filters={"upr_cd": "6110000"})
        assert result.items[0]["orgCd"] == "3220000"
        with pytest.raises(ApiFailure, match="INVALID_REFERENCE_FILTERS"):
            client.fetch_reference("kind", 1, 1000)
        assert client.attempts == 1


def test_cache_survives_restart_and_new_unknown_refreshes_once(tmp_path):
    a, b = {"kindCd": "a"}, {"kindCd": "b"}
    first = FakeClient([page([a])])
    ReferenceCache(tmp_path, first).ensure("kind", {"up_kind_cd": "417000"}, expected={"a"})
    next_client = FakeClient([page([a, b])])
    next_cache = ReferenceCache(tmp_path, next_client)
    next_cache.ensure("kind", {"up_kind_cd": "417000"}, expected={"a"})
    assert not next_client.calls
    assert next_cache.ensure("kind", {"up_kind_cd": "417000"}, expected={"b"}) == [a, b]
    next_cache.ensure("kind", {"up_kind_cd": "417000"}, expected={"a", "b"})
    assert len(next_client.calls) == 1


def test_absent_code_is_not_repeated_until_negative_cache_expires(tmp_path):
    start = datetime(2026, 9, 14, tzinfo=UTC)
    first = FakeClient([page([])])
    ReferenceCache(tmp_path, first, clock=lambda: start).ensure("sido", expected={"missing"})
    second = FakeClient([])
    cache = ReferenceCache(tmp_path, second, clock=lambda: start + timedelta(hours=23))
    assert cache.ensure("sido", expected={"missing"}) == []
    assert not second.calls
    third = FakeClient([page([])])
    cache = ReferenceCache(tmp_path, third, clock=lambda: start + timedelta(days=1))
    cache.ensure("sido", expected={"missing"})
    cache.ensure("sido", expected={"missing"})
    assert len(third.calls) == 1


def test_empty_success_is_reused_without_an_expected_code(tmp_path):
    client = FakeClient([page([])])
    ReferenceCache(tmp_path, client).ensure("sido")
    assert ReferenceCache(tmp_path, FakeClient([])).ensure("sido") == []


def test_scoped_shelters_and_identical_source_duplicates(tmp_path):
    shelter = {"careRegNo": "s1", "careNm": "공동 보호소"}
    client = FakeClient([page([shelter, shelter, shelter]), page([shelter])])
    cache = ReferenceCache(tmp_path, client)
    assert cache.ensure("shelter", {"upr_cd": "1", "org_cd": "11"}) == [shelter]
    cache.ensure("shelter", {"upr_cd": "1", "org_cd": "12"})
    cache.ensure("shelter", {"upr_cd": "1", "org_cd": "11"})
    assert len(client.calls) == 2
    entry = cache.data["catalogs"][cache.scope("shelter", {"upr_cd": "1", "org_cd": "11"})]
    assert entry["totalCount"] == 3 and entry["duplicate_rows"] == 2


def test_failed_refresh_preserves_good_cache(tmp_path):
    ReferenceCache(tmp_path, FakeClient([page([{"orgCd": "1"}])])).ensure("sido")
    original = (tmp_path / "cache.json").read_bytes()
    failing = FakeClient([page([{"orgCd": "1"}], total=2), ApiFailure("NETWORK_ERROR")])
    cache = ReferenceCache(tmp_path, failing)
    with pytest.raises(ApiFailure, match="NETWORK_ERROR"):
        cache.ensure("sido", expected={"2"})
    assert (tmp_path / "cache.json").read_bytes() == original


def test_parent_self_row_allowed_but_wrong_parent_is_rejected(tmp_path):
    good = {"orgCd": "6110000", "orgdownNm": "서울특별시"}
    bad = {"orgCd": "3220000", "uprCd": "wrong"}
    cache = ReferenceCache(tmp_path, FakeClient([page([good])]))
    assert cache.ensure("sigungu", {"upr_cd": "6110000"}) == [good]
    with pytest.raises(ApiFailure, match="REFERENCE_PARENT_MISMATCH"):
        ReferenceCache(tmp_path / "bad", FakeClient([page([bad])])).ensure(
            "sigungu", {"upr_cd": "6110000"}
        )


def test_conflicting_duplicate_does_not_choose_a_name(tmp_path):
    cache = ReferenceCache(
        tmp_path,
        FakeClient([page([{"orgCd": "1", "orgdownNm": "A"}, {"orgCd": "1", "orgdownNm": "B"}])]),
    )
    with pytest.raises(ApiFailure, match="REFERENCE_CODE_CONFLICT"):
        cache.ensure("sido")
    assert not (tmp_path / "cache.json").exists()


def test_cache_checksum_failure_is_reported(tmp_path):
    cache = ReferenceCache(tmp_path, FakeClient([page([{"orgCd": "1"}])]))
    cache.ensure("sido")
    data = json.loads((tmp_path / "cache.json").read_text(encoding="utf-8"))
    next(iter(data["catalogs"].values()))["items"][0]["orgCd"] = "altered"
    (tmp_path / "cache.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ApiFailure, match="REFERENCE_CACHE_INVALID"):
        ReferenceCache(tmp_path)


def test_official_same_name_codes_stay_ambiguous():
    provinces = [{"orgCd": "1", "orgdownNm": "경상남도"}]
    districts = {
        "1": [{"orgCd": "11", "orgdownNm": "창원시"}, {"orgCd": "12", "orgdownNm": "창원시"}]
    }
    index = region_index(provinces, districts)
    assert len(index["경상남도 창원시"]) == 2
    assert "경상남도 창원시 의창성산구" not in index


def test_reference_offline_report_does_not_claim_complete_catalogs(tmp_path):
    rows = [
        {
            "desertionNo": "1",
            "upKindNm": "개",
            "upKindCd": "417000",
            "orgNm": "서울특별시 강남구",
            "processState": "보호중",
            "noticeSdt": "20260904",
        }
    ]
    result = analyze_references(rows, ReferenceCache(tmp_path / "cache"), today=date(2026, 9, 14))
    assert "reference_catalogs_not_collected" in result["blockers"]
    assert result["status_policy"]["display_state_frequencies"] == {"입양 가능": 1}
    result["animal_run_id"] = "synthetic"
    write_reference_report(tmp_path, result)
    assert (tmp_path / ".local/profiling/reference-data/reports/api-reference-data-profile.md").exists()
    assert not (tmp_path / "docs").exists()


def test_reference_result_from_another_capture_cannot_clear_blockers():
    summary = {"run": {"run_id": "one", "raw_sha256": "hash"}, "species": {"dog_count": 1}}
    with pytest.raises(ApiFailure, match="REFERENCE_PROFILE_CAPTURE_MISMATCH"):
        apply_reference_results(summary, {"animal_run_id": "two"})


def test_verified_reference_updates_region_gate_and_keeps_other_blockers():
    summary = {
        "run": {"run_id": "one", "raw_sha256": "hash"},
        "species": {"dog_count": 2},
        "shelter_region": {"normalization_status": "decision_required"},
        "blockers": ["structured_region_normalization_needs_decision", "collection_failed_pages"],
    }
    reference = {
        "animal_run_id": "one",
        "animal_raw_sha256": "hash",
        "denominator_unique_dogs": 2,
        "region": {"mapped_dogs": 2, "unresolved_dogs": 0, "ambiguous_dogs": 0},
        "blockers": [],
    }
    apply_reference_results(summary, reference)
    assert summary["blockers"] == ["collection_failed_pages"]
    assert (
        summary["shelter_region"]["normalization_status"] == "official_codes_verified_for_capture"
    )


def test_scoped_evidence_preserves_conflicting_memberships_and_never_infers_other_ids(tmp_path):
    cache = ReferenceCache(tmp_path)
    directory = tmp_path / "organization-evidence"
    directory.mkdir()
    source_filters = {"bgnde": "20260101", "endde": "20260913"}
    for code in ("11", "12"):
        saved = {
            "filters": {"upr_cd": "1", "org_cd": code, **source_filters},
            "envelope": {
                "response": {
                    "header": {"resultCode": "00"},
                    "body": {
                        "pageNo": 1,
                        "totalCount": 1,
                        "items": {
                            "item": [{"desertionNo": "a", "orgNm": "경상남도 창원시 의창성산구"}]
                        },
                    },
                }
            },
        }
        (directory / f"{code}.json").write_text(json.dumps(saved), encoding="utf-8")
    provinces = [{"orgCd": "1", "orgdownNm": "경상남도"}]
    districts = {
        "1": [{"orgCd": "11", "orgdownNm": "창원시"}, {"orgCd": "12", "orgdownNm": "창원시"}]
    }
    members, _ = scoped_memberships(
        cache, provinces, districts, {"경상남도 창원시 의창성산구"}, source_filters
    )
    assert len(members[("a", "경상남도 창원시 의창성산구")]) == 2
    assert ("another-animal", "경상남도 창원시 의창성산구") not in members
    assert ("a", "경상남도 창원시") not in members
    changed, _ = scoped_memberships(
        cache,
        provinces,
        districts,
        {"경상남도 창원시 의창성산구"},
        {"bgnde": "20270101", "endde": "20270913"},
    )
    assert not changed


def test_scoped_evidence_fetches_all_pages(tmp_path):
    class Client:
        def __init__(self):
            self.calls = []

        def fetch(self, number, size, *, filters):
            self.calls.append(number)
            item = {"desertionNo": str(number), "orgNm": "서울특별시 강남구"}
            return Page(
                number,
                1001,
                [item],
                "array",
                {"resultCode": "00"},
                {
                    "response": {
                        "header": {"resultCode": "00"},
                        "body": {
                            "pageNo": number,
                            "totalCount": 1001,
                            "items": {"item": [item]},
                        },
                    }
                },
                1000,
            )

    client = Client()
    cache = ReferenceCache(tmp_path, client)
    members, used = scoped_memberships(
        cache,
        [{"orgCd": "1", "orgdownNm": "서울특별시"}],
        {"1": [{"orgCd": "11", "orgdownNm": "강남구"}]},
        {"서울특별시 강남구"},
        {"bgnde": "20260101", "endde": "20260913"},
    )

    assert client.calls == [1, 2]
    assert len(members) == 2
    assert used[0]["rows"] == 2


def test_transient_cache_replace_error_does_not_repeat_api_call(tmp_path, monkeypatch):
    from pathlib import Path

    real_replace = Path.replace
    attempts = []

    def replace(path, target):
        attempts.append(path)
        if len(attempts) == 1:
            raise PermissionError
        return real_replace(path, target)

    monkeypatch.setattr(Path, "replace", replace)
    client = FakeClient([page([{"orgCd": "1"}])])
    assert ReferenceCache(tmp_path, client).ensure("sido") == [{"orgCd": "1"}]
    assert len(attempts) == 2
    assert len(client.calls) == 1
