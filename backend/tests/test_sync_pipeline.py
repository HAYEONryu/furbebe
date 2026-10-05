import hashlib
import json
from datetime import UTC, date, datetime
from decimal import Decimal

import httpx
import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings
from backend.jobs.animal_sync import main as sync_cli
from backend.jobs.animal_sync.capture import RecordingClient, ReplayClient
from backend.jobs.animal_sync.client import AnimalApiClient, ApiFailure
from backend.jobs.animal_sync.main import require_local_development
from backend.jobs.animal_sync.normalizer import age_group, normalize_animal, size_group
from backend.jobs.animal_sync.pagination import PaginationProgress, iter_pages
from backend.jobs.animal_sync.service import SyncReport, prepare_page
from backend.jobs.animal_sync.source_models import ValidatedAnimal
from backend.jobs.animal_sync.tagger import CATALOG, generate_tags
from backend.tests.sync_fixtures import SnapshotClient, envelope, source_row

TODAY = date(2026, 9, 15)


@pytest.mark.parametrize("identity", [None, 123, True, "", " - "])
def test_source_identity_validation_does_not_coerce(identity):
    with pytest.raises(ValidationError):
        ValidatedAnimal.model_validate(source_row(identity))


def test_source_types_unknown_fields_and_raw_snapshot_are_separate():
    raw = source_row(extraSourceField={"preserve": True})
    item = ValidatedAnimal.model_validate(raw)
    result = normalize_animal(item, today=TODAY)
    assert result.values["raw_payload"] == raw
    assert result.values["source_id"] == "animal-1"
    assert result.values["species"] == "dog"
    assert result.values["weight_kg"] == Decimal(5)
    assert result.values["source_updated_at"] is None
    assert "source_timestamp_timezone_unknown" in result.issues
    assert result.shelter["source_id"] == "shelter-1"
    with pytest.raises(ValidationError):
        ValidatedAnimal.model_validate(source_row(weight=5))


def test_nullable_placeholder_and_invalid_fact_normalization():
    raw = source_row(
        weight="-1(Kg)",
        age="2027(년생)",
        specialMark=" . ",
        sfeSoci=" ",
        sfeHealth="없음",
        etcBigo="-",
        vaccinationChk="null",
        healthChk="n/a",
        careRegNo="미상",
    )
    result = normalize_animal(ValidatedAnimal.model_validate(raw), today=TODAY)
    for key in (
        "weight_kg",
        "birth_year",
        "special_mark",
        "social_text",
        "health_text",
        "etc_text",
        "vaccination_text",
        "health_check_text",
    ):
        assert result.values[key] is None
    assert result.shelter is None
    assert result.values["raw_payload"] == raw


def test_offset_timestamp_and_decimal_precision_are_preserved():
    result = normalize_animal(
        ValidatedAnimal.model_validate(
            source_row(weight="5.0000000000000001(Kg)", updTm="2026-09-15T12:00:00+09:00")
        ),
        today=TODAY,
    )
    assert result.values["weight_kg"] == Decimal("5.0000000000000001")
    assert result.values["source_updated_at"] == datetime(2026, 9, 15, 3, tzinfo=UTC)


@pytest.mark.parametrize("invalid", ["actual\x00nul", "invalid\ud800surrogate"])
def test_invalid_jsonb_text_is_rejected_without_losing_valid_rows(invalid):
    rows = [source_row(str(i)) for i in range(20)]
    rows[0]["unknownField"] = {"nested": [invalid]}
    rows[1]["specialMark"] = r"literal \u0000 remains valid text"
    page = SnapshotClient(rows).fetch(1, 1000)
    report = SyncReport()
    normalized, rejected = prepare_page(page, {}, report, today=TODAY)
    assert rejected == report.rejected_count == 1
    assert len(normalized) == 19
    assert normalized[0].values["special_mark"] == rows[1]["specialMark"]


def test_image_deduplication_trims_blanks_and_retains_source_order():
    result = normalize_animal(
        ValidatedAnimal.model_validate(
            source_row(
                popfile1=" https://example.invalid/b.jpg ",
                popfile2="",
                popfile3="https://example.invalid/b.jpg",
                popfile4="https://example.invalid/a.jpg",
                popfile5="not-a-url",
            )
        ),
        today=TODAY,
    )
    assert result.images == ("https://example.invalid/b.jpg", "https://example.invalid/a.jpg")


@pytest.mark.parametrize(
    "weight,expected",
    [
        (None, "unknown"),
        ("0", "tiny"),
        ("5", "tiny"),
        ("5.0001", "small"),
        ("10", "small"),
        ("10.001", "medium"),
        ("20", "medium"),
        ("20.01", "large"),
    ],
)
def test_size_policy_boundaries(weight, expected):
    assert size_group(Decimal(weight) if weight is not None else None) == expected


@pytest.mark.parametrize(
    "birth,expected",
    [
        (None, "unknown"),
        (2026, "puppy"),
        (2025, "puppy"),
        (2024, "young"),
        (2022, "young"),
        (2021, "adult"),
        (2018, "adult"),
        (2017, "adult"),
        (2016, "senior"),
    ],
)
def test_age_policy_boundaries(birth, expected):
    assert age_group(birth, year=2026) == expected


def test_color_and_explicit_behavior_tags_generate():
    raw = source_row(
        specialMark="애교 많고 활발하며 질병 있음", sfeSoci="낯가림", sfeHealth="치료 필요"
    )
    tags = generate_tags(
        normalize_animal(ValidatedAnimal.model_validate(raw), today=TODAY), today=TODAY
    )
    assert {tag.tag_key for tag in tags} == {"white_coat", "cuddly", "playful"}
    assert all(tag.evidence and 0 < tag.confidence <= 1 for tag in tags)
    assert {row["type"] for row in CATALOG} == {"vibe", "trait"}
    assert all(row["emoji"] for row in CATALOG)
    raw.update(colorCd="흰색&갈색", specialMark="", sfeSoci="", weight="미상")
    mixed = generate_tags(normalize_animal(ValidatedAnimal.model_validate(raw), today=TODAY), today=TODAY)
    assert {tag.tag_key for tag in mixed} == {"brownie"}


def test_pagination_honors_server_size_and_checks_terminal_page():
    client = SnapshotClient([source_row(str(i)) for i in range(5)], clamp=2)
    progress = PaginationProgress()
    pages = list(iter_pages(client, progress))
    assert [len(p.items) for p in pages] == [2, 2, 1, 0]
    assert client.calls == [1, 2, 3, 4]
    assert progress.fetched_count == progress.unique_count == progress.total_count == 5
    assert progress.failed_pages == []


@pytest.mark.parametrize(
    "client,code",
    [
        (SnapshotClient([], total=0), "ABNORMAL_TOTAL_OR_PAGE"),
        (SnapshotClient([], total=5), "INCOMPLETE_OR_EXCESS_PAGE"),
        (SnapshotClient([source_row(), source_row()]), "UNIQUE_COUNT_MISMATCH"),
        (SnapshotClient([source_row()], total=3), "INCOMPLETE_OR_EXCESS_PAGE"),
    ],
)
def test_abnormal_pagination_is_failed(client, code):
    progress = PaginationProgress()
    with pytest.raises(ApiFailure, match=code):
        list(iter_pages(client, progress))
    assert progress.failed_pages


def test_application_error_over_http_200_is_not_success_and_is_retried():
    responses = iter([envelope([], code="01"), envelope([source_row()])])
    with AnimalApiClient(
        "secret-value",
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=next(responses))),
        interval=0,
        sleeper=lambda _: None,
    ) as client:
        assert len(client.fetch(1, 1000).items) == 1
        assert client.retries == 1
    with AnimalApiClient(
        "secret-value",
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=envelope([], code="30"))),
        interval=0,
    ) as client:
        with pytest.raises(ApiFailure, match="APPLICATION_ERROR"):
            client.fetch(1, 1000)


def test_capture_and_replay_preserve_pages_and_detect_tampering(tmp_path):
    path = tmp_path / "pages.jsonl"
    responses = iter([envelope([source_row()]), envelope([], page=2, total=1)])
    with AnimalApiClient(
        "not-persisted",
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=next(responses))),
        interval=0,
    ) as client:
        recorder = RecordingClient(client, path)
        first = recorder.fetch(1, 1000)
        recorder.fetch(2, 1000)
        recorder.close()
        recorder.close()
    replay = ReplayClient(path)
    try:
        assert replay.fetch(1, 1000).items == first.items
        assert replay.fetch(2, 1000).items == []
        assert replay.attempts == replay.retries == 0
    finally:
        replay.close()
    assert "not-persisted" not in path.read_text(encoding="utf-8")
    path.write_text("changed", encoding="utf-8")
    with pytest.raises(ApiFailure, match="REPLAY_HASH_MISMATCH"):
        ReplayClient(path)


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://u:p@project.supabase.co/postgres",
        "postgresql://u:p@127.0.0.1/postgres",
        "postgresql://u:p@db.example/furbebe_dev",
        "postgresql://u:p@127.0.0.1/furbebe_dev?host=remote.example",
        "postgresql://u:p@127.0.0.1/furbebe_dev?hostaddr=192.0.2.1",
        "postgresql://u:p@127.0.0.1/furbebe_dev?dbname=postgres",
        "postgresql://u:p@127.0.0.1/furbebe_dev?service=remote",
    ],
)
def test_phase4a_cli_rejects_remote_or_non_development_database(url):
    with pytest.raises(ApiFailure):
        require_local_development(Settings(_env_file=None, app_env="test", database_url=url))


def write_capture(path, records):
    path.write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")
    path.with_suffix(".sha256").write_text(
        hashlib.sha256(path.read_bytes()).hexdigest(), encoding="ascii"
    )


def capture_record(page, rows):
    return {
        "page_no": page,
        "page_size": 1000,
        "filters": {},
        "response": envelope(rows, page=page, total=1),
    }


@pytest.mark.parametrize(
    "records,code",
    [
        ([None], "INVALID_REPLAY_CAPTURE"),
        ([capture_record(1, [source_row()])], "REPLAY_INCOMPLETE"),
        (
            [capture_record(1, [source_row()]), []],
            "INVALID_REPLAY_CAPTURE",
        ),
        (
            [capture_record(1, [source_row()]), capture_record(3, [])],
            "REPLAY_REQUEST_MISMATCH",
        ),
        (
            [capture_record(1, [source_row()]), capture_record(2, []), {"extra": True}],
            "REPLAY_TRAILING_DATA",
        ),
        ([capture_record(1, [source_row()]) | {"page_size": "1000"}], "INVALID_REPLAY_REQUEST"),
        ([capture_record(1, [source_row()]) | {"page_size": True}], "INVALID_REPLAY_REQUEST"),
        (
            [capture_record(1, [source_row()]) | {"filters": {"bgnde": "20260915"}}],
            "INVALID_REPLAY_REQUEST",
        ),
    ],
)
def test_replay_preflight_rejects_bad_captures_and_closes_file(tmp_path, records, code):
    path = tmp_path / "pages.jsonl"
    write_capture(path, records)
    with pytest.raises(ApiFailure, match=code):
        ReplayClient(path)
    # Windows refuses rename when a failed constructor leaves the capture open.
    path.rename(tmp_path / "closed.jsonl")


def test_cli_incomplete_replay_does_not_create_database_engine(tmp_path, monkeypatch, capsys):
    directory = tmp_path / ".local/sync"
    directory.mkdir(parents=True)
    path = directory / "pages.jsonl"
    write_capture(path, [capture_record(1, [source_row()])])
    monkeypatch.setattr(sync_cli, "ROOT", tmp_path)
    monkeypatch.setattr(
        sync_cli,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            app_env="test",
            database_url="postgresql://u:p@127.0.0.1/furbebe_test_replay",
        ),
    )

    def unexpected_database(*args):
        pytest.fail("Invalid replay must be rejected before database access")

    monkeypatch.setattr(sync_cli, "create_database_engine", unexpected_database)
    assert sync_cli.main(["--replay", str(path)]) == 2
    assert json.loads(capsys.readouterr().out)["error_code"] == "REPLAY_INCOMPLETE"


@pytest.mark.parametrize("description", [
    "낯가림 없음", "순하지 않음", "사람을 좋아하지 않음", "활발한지 미확인", "차분한 듯?",
])
def test_negated_or_uncertain_behavior_is_not_tagged(description):
    raw = source_row(colorCd="혼합", specialMark=description, sfeSoci="", sfeHealth="온순하고 활발함")
    tags = generate_tags(normalize_animal(ValidatedAnimal.model_validate(raw), today=TODAY), today=TODAY)
    assert not any(tag.tag_key in {"gentle", "shy", "playful", "calm", "people_friendly"} for tag in tags)


def test_behavior_evidence_is_deduplicated_across_fields():
    raw = source_row(colorCd="흰색", specialMark="온순하고 차분함. 겁이 많음", sfeSoci="온순하고 차분함. 겁이 많음")
    tags = generate_tags(normalize_animal(ValidatedAnimal.model_validate(raw), today=TODAY), today=TODAY)
    assert {tag.tag_key for tag in tags} == {"white_coat", "gentle", "calm", "shy", "cuddly"}
    assert len(tags) == 5
    assert len({row["emoji"] for row in CATALOG}) == len(CATALOG)
    assert len({row["label"] for row in CATALOG}) == len(CATALOG)
