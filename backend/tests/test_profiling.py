"""Offline tests only. Synthetic fixtures must never count as live profiling."""

import copy
import json
from datetime import date
from pathlib import Path
from urllib.parse import quote

import httpx
import pytest

from backend.jobs.animal_sync.client import AnimalApiClient, ApiFailure, Redactor, load_service_key
from backend.jobs.animal_sync.evidence import (
    classify,
    export_review,
    profile_evidence,
    review_sample,
)
from backend.jobs.animal_sync.field_stats import (
    FIELDS,
    animal_images,
    parse_age,
    parse_date,
    parse_weight,
    profile_dates,
    profile_fields,
    valid_url,
)
from backend.jobs.animal_sync.metrics import assess_collection, build_profile, identity_profile
from backend.jobs.animal_sync.profiling import collect, load_capture, local_path
from backend.jobs.animal_sync.reports import pending_reports, write_reports
from backend.jobs.animal_sync.source_models import SourceShapeError, normalize_items

FIXTURE = Path(__file__).parent / "fixtures" / "openapi_sample.json"


@pytest.fixture
def payload():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def envelope(rows, *, total=None, page=1, code="00"):
    return {
        "response": {
            "header": {"resultCode": code, "resultMsg": "fixture"},
            "body": {
                "pageNo": page,
                "numOfRows": 100,
                "totalCount": len(rows) if total is None else total,
                "items": {"item": rows},
            },
        }
    }


def client_for(handler, **kwargs):
    return AnimalApiClient(
        "FAKE_KEY_ONLY",
        transport=httpx.MockTransport(handler),
        interval=0,
        sleeper=lambda _: None,
        **kwargs,
    )


def dog(number, **extras):
    return {"desertionNo": f"{number:015d}", "upKindNm": "개", **extras}


@pytest.mark.parametrize(
    ("container", "size", "shape"),
    [
        ({"item": {"desertionNo": "001"}}, 1, "object"),
        ({"item": [{"desertionNo": "001"}, {"desertionNo": "002"}]}, 2, "array"),
        (None, 0, "items_empty"),
        ("", 0, "items_empty"),
        ({}, 0, "item_empty"),
        ({"item": None}, 0, "item_empty"),
        ({"item": []}, 0, "array"),
    ],
)
def test_response_shapes(container, size, shape):
    rows, actual = normalize_items({"items": container})
    assert len(rows) == size
    assert actual == shape


@pytest.mark.parametrize("container", [42, {"item": 42}, {"item": [None]}, {"item": ["bad"]}])
def test_invalid_shapes(container):
    with pytest.raises(SourceShapeError):
        normalize_items({"items": container})


def test_preserves_unknown_fields_and_raw_types():
    rows, _ = normalize_items(
        {"items": {"item": {"desertionNo": "0001", "weight": 7, "unseen": {"nested": [None, 1]}}}}
    )
    assert rows[0].root == {"desertionNo": "0001", "weight": 7, "unseen": {"nested": [None, 1]}}
    assert "age" not in rows[0].root


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("7(Kg)", 7.0),
        ("16.42(Kg)", 16.42),
        ("1.3(Kg)", 1.3),
        ("0(Kg)", 0),
        ("-2(Kg)", -2),
        ("about 7 kg", None),
        ("5~7(Kg)", None),
        ("NaN(Kg)", None),
        ("", None),
        (None, None),
        (7, None),
        ("7(Kg) extra", None),
    ],
)
def test_weight(value, expected):
    assert parse_weight(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2022(년생)", 2022),
        ("2026(년생)", 2026),
        ("미상", None),
        ("약 4살", None),
        ("2022", None),
        (2022, None),
        (None, None),
    ],
)
def test_age(value, expected):
    assert parse_age(value) == expected


@pytest.mark.parametrize(
    ("value", "valid"),
    [
        ("20260909", True),
        ("2026-09-09", True),
        ("2026-09-09 21:12:11.0", True),
        ("2026-09-09T12:12:11Z", True),
        ("2026-09-09T21:12:11+09:00", True),
        ("20240229", True),
        ("20260229", False),
        ("20261301", False),
        ("September 9", False),
        (None, False),
        (20260909, False),
    ],
)
def test_dates(value, valid):
    assert (parse_date(value) is not None) == valid


def test_naive_timestamp_not_assigned_timezone():
    assert parse_date("2026-09-09 21:12:11.0").tzinfo is None


def test_date_order_and_future():
    result = profile_dates(
        [dog(1, noticeSdt="20260920", noticeEdt="20260901", happenDt="20260920")], date(2026, 9, 11)
    )
    assert result["consistency"]["noticeSdt<=noticeEdt"]["violations"] == 1
    assert result["happenDt"]["future_dates"] == 1


@pytest.mark.parametrize(
    ("value", "category"),
    [
        ("", "EMPTY"),
        (".", "PLACEHOLDER"),
        ("-", "PLACEHOLDER"),
        ("  ", "EMPTY"),
        ("119 인계", "ADMINISTRATIVE"),
        ("마을에서 발견", "ADMINISTRATIVE"),
        ("우측 뒷다리 절단", "HEALTH_RELATED"),
        ("사람을 경계함", "BEHAVIOR_RELATED"),
        ("사람을 경계함. 상처 치료. 119 인계", "MIXED"),
    ],
)
def test_text_classes(value, category):
    assert classify(value)["class"] == category


def test_short_keyword_and_negation_flags_are_not_tags():
    result = classify("순함")
    assert result["behavior"] and result["short_text_candidate"]
    result = classify("사람을 좋아하지 않음")
    assert result["behavior"] and result["negation_marker"]
    assert "tag" not in result


def test_evidence_denominators_and_sources():
    rows = [
        dog(1, specialMark="119 인계"),
        dog(2, specialMark="사람을 경계함"),
        dog(3, sfeSoci="애교 많음", sfeHealth="상처 치료"),
    ]
    result = profile_evidence(rows)
    assert result["counts"]["any_behavior"] == 2
    assert result["counts"]["any_health"] == 1
    assert result["counts"]["administrative_only"] == 1
    assert result["counts"]["only_specialMark_behavior"] == 1
    assert result["counts"]["sfeSoci_behavior"] == 1
    assert result["denominator"] == 3


def test_image_dedup_and_no_promotion_substitution():
    row = dog(
        1,
        popfile1="https://example.invalid/1.jpg",
        popfile2="https://example.invalid/1.jpg",
        popfile3="http://example.invalid/2.jpg",
        adptnImg="https://example.invalid/promo.jpg",
    )
    assert animal_images(row) == ["https://example.invalid/1.jpg", "http://example.invalid/2.jpg"]
    assert animal_images({"adptnImg": row["adptnImg"]}) == []


@pytest.mark.parametrize(
    "value",
    [
        "javascript:alert(1)",
        "file:///C:/x.jpg",
        "https://",
        "https://user:pass@example.com/x.jpg",
        "https://bad url",
        None,
    ],
)
def test_invalid_image_urls(value):
    assert not valid_url(value)


def test_identity_duplicate_classes_and_missing():
    first = dog(1, specialMark="first")
    rows = [first, first.copy(), dog(1, specialMark="changed"), dog(2), {}, {"desertionNo": 3}]
    unique, stats = identity_profile(rows)
    assert len(unique) == 2
    assert stats["unusable_id_count"] == 2
    assert stats["duplicate_item_count"] == 2
    assert stats["identical_duplicate_item_count"] == 1
    assert stats["conflicting_additional_versions"] == 1
    assert stats["conflict_fields"]["specialMark"] == 1
    assert unique[0]["specialMark"] == "first"


def test_field_dictionary_keeps_missing_null_blank_placeholder_separate():
    rows = [{}, {"age": None}, {"age": ""}, {"age": "."}, {"age": "2022(년생)", "extra": [1]}]
    stats = {r["field"]: r for r in profile_fields(rows, Redactor())}
    age = stats["age"]
    assert set(FIELDS).issubset(stats)
    assert (
        age["missing_count"]
        == age["null_count"]
        == age["blank_count"]
        == age["placeholder_count"]
        == 1
    )
    assert age["parseable_denominator"] == 1
    assert age["parseable_ratio"] == 1
    assert stats["extra"]["observed_type"] == {"list": 1}


@pytest.mark.parametrize("status", [400, 401, 403])
def test_no_retry_on_bad_request_or_auth(status):
    with client_for(lambda _: httpx.Response(status, text="FAKE_KEY_ONLY")) as client:
        with pytest.raises(ApiFailure, match="HTTP_ERROR") as caught:
            client.fetch(1, 100)
        assert "FAKE_KEY_ONLY" not in str(caught.value)
        assert client.attempts == 1


def test_http_retry_bounded_and_url_not_logged(caplog):
    with client_for(lambda _: httpx.Response(503, text="FAKE_KEY_ONLY")) as client:
        with pytest.raises(ApiFailure):
            client.fetch(1, 100)
        assert client.attempts == 4 and client.retries == 3
    assert "FAKE_KEY_ONLY" not in caplog.text
    assert "serviceKey=" not in caplog.text


def test_http_200_application_error_not_success():
    with client_for(lambda _: httpx.Response(200, json=envelope([], code="30"))) as client:
        with pytest.raises(ApiFailure, match="APPLICATION_ERROR"):
            client.fetch(1, 100)
        assert client.attempts == 1


def test_gateway_xml_error():
    xml = (
        "<OpenAPI_ServiceResponse><cmmMsgHeader><returnReasonCode>30</returnReasonCode>"
        "</cmmMsgHeader></OpenAPI_ServiceResponse>"
    )
    with client_for(lambda _: httpx.Response(200, text=xml)) as client:
        with pytest.raises(ApiFailure, match="code=30"):
            client.fetch(1, 100)


def test_timeout_redacts_underlying_request_exception():
    def handler(request):
        raise httpx.ConnectTimeout("secret in " + str(request.url), request=request)

    with client_for(handler) as client:
        with pytest.raises(ApiFailure) as caught:
            client.fetch(1, 100)
        assert "FAKE_KEY_ONLY" not in str(caught.value)
        assert "http" not in str(caught.value)
        assert client.attempts == 4


def test_client_keeps_payload_but_redacts_echoed_credentials(payload):
    payload["response"]["body"]["items"]["item"][0]["debug"] = "FAKE_KEY_ONLY"
    with client_for(lambda _: httpx.Response(200, json=payload)) as client:
        page = client.fetch(1, 100)
    assert page.items[0]["desertionNo"].startswith("000")
    assert "FAKE_KEY_ONLY" not in json.dumps(page.envelope)
    assert page.items[1]["unexpectedFixtureField"] == "retained"


def test_header_or_page_shape_error():
    payload = envelope([dog(1)], page=7)
    with client_for(lambda _: httpx.Response(200, json=payload)) as client:
        with pytest.raises(ApiFailure, match="RESPONSE_SHAPE"):
            client.fetch(1, 100)


def test_environment_and_dotenv_key_never_printed(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("DATA_GO_KR_SERVICE_KEY", raising=False)
    key = "FAKE+KEY/="
    (tmp_path / ".env").write_text(
        "DATA_GO_KR_SERVICE_KEY=" + quote(key, safe=""), encoding="utf-8"
    )
    assert load_service_key(tmp_path) == key
    monkeypatch.setenv("DATA_GO_KR_SERVICE_KEY", "ENVIRONMENT_FAKE")
    assert load_service_key(tmp_path) == "ENVIRONMENT_FAKE"
    assert not capsys.readouterr().out


def test_missing_key_error_safe(tmp_path, monkeypatch):
    monkeypatch.delenv("DATA_GO_KR_SERVICE_KEY", raising=False)
    with pytest.raises(ApiFailure, match="MISSING_SERVICE_KEY"):
        load_service_key(tmp_path)


def test_output_cannot_escape_local_directory(tmp_path):
    assert local_path(tmp_path, Path(".local/profiling/a")).is_relative_to(tmp_path)
    for path in (Path("docs/raw.jsonl"), Path(".local/profiling/../../raw.jsonl")):
        with pytest.raises(ApiFailure):
            local_path(tmp_path, path)


def test_collect_exhaustive_and_offline_replay(tmp_path):
    def handler(request):
        page = int(request.url.params["pageNo"])
        return httpx.Response(
            200, json=envelope([dog(page)] if page <= 2 else [], total=2, page=page)
        )

    raw = tmp_path / "raw.jsonl"
    with client_for(handler) as client:
        rows, run = collect(client, raw, run_id="test", page_size=1, entire_population=True)
    assert len(rows) == 2 and run["exhausted"]
    assert run["requested_pages"] == 3
    (tmp_path / "run.json").write_text(json.dumps(run), encoding="utf-8")
    replay, meta = load_capture(raw)
    assert replay == rows and meta["exhausted"]


def test_repeated_page_is_preserved_and_blocked(tmp_path):
    def handler(request):
        return httpx.Response(
            200, json=envelope([dog(1)], total=5000, page=int(request.url.params["pageNo"]))
        )

    with client_for(handler) as client:
        rows, run = collect(client, tmp_path / "raw.jsonl", run_id="test", max_pages=10)
    assert len(rows) == 2
    assert run["stop_reason"] == "repeated_page"
    assert not run["exhausted"]


def test_total_count_drift_blocks(tmp_path):
    def handler(request):
        page = int(request.url.params["pageNo"])
        return httpx.Response(200, json=envelope([dog(page)], total=5000 + page, page=page))

    with client_for(handler) as client:
        rows, run = collect(client, tmp_path / "raw.jsonl", run_id="test")
    assert run["stop_reason"] == "totalCount_changed"
    _, items = identity_profile(rows)
    assert "reported_totalCount_changed" in assess_collection(run, items, 2, 5000)["issues"]


@pytest.mark.parametrize(
    ("entire", "exhausted", "total", "failed", "allowed"),
    [
        (True, True, 2, 0, True),
        (False, True, 2, 0, False),
        (True, False, 2, 0, False),
        (True, True, 5000, 0, False),
        (True, True, 2, 1, False),
    ],
)
def test_small_population_exception(entire, exhausted, total, failed, allowed):
    _, items = identity_profile([dog(1), dog(2)])
    run = {
        "reported_total_counts": [total],
        "entire_population_scope": entire,
        "exhausted": exhausted,
        "failed_pages": failed,
    }
    result = assess_collection(run, items, 2, 5000)
    assert result["whole_population_exception"] is allowed
    assert (result["status"] == "sufficient") is allowed


def test_exception_reports_duplicates():
    _, items = identity_profile([dog(1), dog(1), dog(2)])
    run = {"reported_total_counts": [3], "entire_population_scope": True, "exhausted": True}
    assert assess_collection(run, items, 2, 5000)["whole_population_exception"]
    assert items["duplicate_item_count"] == 1


def test_failed_page_not_silent(tmp_path):
    with client_for(lambda _: httpx.Response(403)) as client:
        rows, run = collect(client, tmp_path / "raw.jsonl", run_id="test")
    assert rows == []
    assert run["failed_pages"] == 1 and run["failed_page_numbers"] == [1]


def test_manual_sample_deterministic_unique_blank_notes(tmp_path):
    rows = [
        dog(i, specialMark="사람을 경계함" if i < 40 else "상처 치료" if i < 80 else "119 인계")
        for i in range(120)
    ]
    selected, meta = review_sample(rows, 7)
    same, _ = review_sample(list(reversed(rows)), 7)
    assert [x["row"]["desertionNo"] for x in selected] == [x["row"]["desertionNo"] for x in same]
    assert len({x["row"]["desertionNo"] for x in selected}) == 100
    assert meta["review_status"] == "pending_human_review"
    path = tmp_path / "review.csv"
    export_review(path, selected, Redactor())
    import csv

    with path.open(encoding="utf-8-sig") as file:
        assert all(r["review_notes"] == "" for r in csv.DictReader(file))


def test_redaction_and_spreadsheet_formula(tmp_path):
    selected = [
        {
            "row": dog(1, specialMark="=FAKE_KEY 010-1234-5678 tester@example.com 담당자: 홍길동"),
            "stratum": "random",
        }
    ]
    path = tmp_path / "review.csv"
    export_review(path, selected, Redactor("FAKE_KEY"))
    output = path.read_text(encoding="utf-8-sig")
    for secret in ("FAKE_KEY", "010-1234-5678", "tester@example.com", "홍길동"):
        assert secret not in output
    assert "'=" in output


def test_profile_reports_all_domains_and_no_schema(tmp_path, payload):
    rows = copy.deepcopy(payload["response"]["body"]["items"]["item"])
    rows.append({"desertionNo": "cat", "upKindNm": "고양이"})
    run = {"run_id": "offline-test", "reported_total_counts": [3], "entire_population_scope": False}
    summary, selected = build_profile(rows, run, Redactor(), today=date(2026, 9, 11))
    assert summary["species"]["dog_count"] == 2
    assert summary["species"]["non_dog_count"] == 1
    assert summary["images"]["primary_image_coverage"] == 0.5
    assert summary["evidence"]["counts"]["any_behavior"] == 1
    assert summary["evidence"]["counts"]["any_health"] == 1
    assert summary["evidence"]["counts"]["any_administrative"] == 1
    assert "structured_region_normalization_needs_decision" in summary["blockers"]
    output = tmp_path / ".local" / "profiling"
    output.mkdir(parents=True)
    docs = tmp_path / "docs"
    docs.mkdir()
    guide = docs / "api-field-dictionary.md"
    guide.write_text("human-owned field guide", encoding="utf-8")
    write_reports(tmp_path, output, summary, selected, Redactor())
    assert guide.read_text(encoding="utf-8") == "human-owned field guide"
    assert sorted(p.name for p in docs.iterdir()) == ["api-field-dictionary.md"]
    report = (output / "reports" / "api-data-profile.md").read_text(encoding="utf-8")
    assert "## 20." in report
    assert not (tmp_path / "backend" / "app").exists()
    assert (output / "manual-review-offline-test.csv").exists()


def test_pending_reports_do_not_claim_observations(tmp_path):
    pending_reports(tmp_path)
    report = (tmp_path / ".local/profiling/reports/api-data-profile.md").read_text(encoding="utf-8")
    assert "NOT MEASURED" in report
    assert "Pending live" in report
