"""Committed sync transactions in isolated schemas of an explicitly selected test DB."""

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, insert, select, text
from sqlalchemy.schema import CreateSchema, DropSchema

from backend.app.db.models import Animal, AnimalImage, AnimalTag, Base, Shelter, SyncRun, Tag
from backend.app.db.session import create_database_engine
from backend.jobs.animal_sync.client import ApiFailure
from backend.jobs.animal_sync.repositories import SyncRepository
from backend.jobs.animal_sync.service import LOCK_NAMESPACE, LOCK_SOURCE, sync
from backend.tests.sync_fixtures import SnapshotClient, source_row

pytestmark = pytest.mark.postgres
NOW = datetime(2026, 9, 15, 3, tzinfo=UTC)


@pytest.fixture
def sync_engine(postgres_settings):
    parent = create_database_engine(postgres_settings)
    token = uuid4().hex
    schema = "phase4a_test_" + token
    with parent.begin() as connection:
        connection.execute(CreateSchema(schema))
    engine = parent.execution_options(schema_translate_map={None: schema})
    try:
        Base.metadata.create_all(engine)
        yield engine
    finally:
        # Drop only the schema created by this fixture, never public/application tables.
        try:
            assert schema == "phase4a_test_" + token
            with parent.begin() as connection:
                connection.execute(DropSchema(schema, cascade=True))
        finally:
            parent.dispose()


def run(engine, rows, **kwargs):
    return sync(engine, SnapshotClient(rows), clock=lambda: NOW, sleeper=lambda _: None, **kwargs)


def counts(engine):
    with engine.connect() as connection:
        return {
            model.__tablename__: connection.scalar(select(func.count()).select_from(model))
            for model in (Animal, Shelter, AnimalImage, Tag, AnimalTag)
        }


def test_only_protected_and_adoptable_dogs_are_stored_and_exclusions_are_not_errors(sync_engine):
    rows = [
        source_row("eligible", noticeSdt="20260905"),
        source_row("too-recent", noticeSdt="20260906"),
        source_row("missing-date", noticeSdt=None),
        source_row("ended", processState="종료(입양)"),
        source_row("cat", upKindNm="고양이", upKindCd="422400"),
    ]
    result = run(sync_engine, rows)
    assert result.status == "success" and result.error_count == 0
    assert result.inserted_count == 3 and result.excluded_count == 2
    with sync_engine.connect() as connection:
        assert set(connection.scalars(select(Animal.source_id))) == {"eligible", "too-recent", "missing-date"}


def test_ended_animals_are_preserved_with_children_and_hidden(sync_engine):
    row = source_row(updTm="2026-09-15T03:00:00Z")
    assert run(sync_engine, [row]).inserted_count == 1
    ended = row | {"processState": "종료(입양)", "updTm": "2026-09-15T04:00:00Z"}
    result = run(sync_engine, [ended])
    assert result.status == "success" and result.deleted_count == 0 and result.updated_count == 1
    assert counts(sync_engine)["animals"] == 1
    assert counts(sync_engine)["animal_images"] == 2
    assert counts(sync_engine)["animal_tags"] > 0
    with sync_engine.connect() as connection:
        animal = connection.execute(select(Animal.__table__)).mappings().one()
        assert animal["is_active"] is False and animal["raw_payload"] == ended
        from backend.app.repositories.animals import AnimalQueries
        assert AnimalQueries(connection, NOW.date()).animal(animal["id"]) is None
        assert AnimalQueries(connection, NOW.date()).overview()["animals_total"] == 0
    repeat = run(sync_engine, [ended])
    assert repeat.inserted_count == 0 and repeat.updated_count == 0
    assert run(sync_engine, [row | {"updTm": "2026-09-15T05:00:00Z"}]).updated_count == 1
    with sync_engine.connect() as connection:
        assert connection.scalar(select(Animal.is_active)) is True


def test_stale_ended_observation_does_not_delete_current_adoptable_dog(sync_engine):
    row = source_row(updTm="2026-09-15T04:00:00Z")
    run(sync_engine, [row])
    result = run(sync_engine, [row | {
        "processState": "종료(입양)", "updTm": "2026-09-15T03:00:00Z"
    }])
    assert result.stale_count == 1 and result.deleted_count == 0
    assert counts(sync_engine)["animals"] == 1


def test_initial_insert_repeat_and_durable_counters(sync_engine):
    rows = [source_row(str(i)) for i in range(5)]
    first = run(sync_engine, rows, page_size=2)
    assert first.status == "success"
    assert (first.inserted_count, first.updated_count) == (5, 0)
    initial = counts(sync_engine)
    assert initial == {
        "animals": 5,
        "shelters": 1,
        "animal_images": 10,
        "tags": 27,
        "animal_tags": 10,
    }
    second = run(sync_engine, rows, page_size=2)
    assert second.status == "success"
    assert (second.inserted_count, second.updated_count, second.unchanged_count) == (0, 0, 5)
    assert counts(sync_engine) == initial
    with sync_engine.connect() as connection:
        record = (
            connection.execute(select(SyncRun.__table__).where(SyncRun.id == second.sync_id))
            .mappings()
            .one()
        )
    assert record["status"] == "success" and record["finished_at"] is not None
    assert record["page_count"] == 4 and record["received_count"] == 5
    assert record["inserted_count"] == 0 and record["updated_count"] == 0


def test_controlled_update_reconciles_images_tags_and_preserves_identity(sync_engine):
    row = source_row(updTm="2026-09-15T03:00:00Z")
    assert run(sync_engine, [row, source_row("unobserved")]).status == "success"
    with sync_engine.begin() as connection:
        old = (
            connection.execute(select(Animal.__table__).where(Animal.source_id == "animal-1"))
            .mappings()
            .one()
        )
        old_images = (
            connection.execute(
                select(AnimalImage.__table__).where(AnimalImage.animal_id == old["id"], AnimalImage.is_active.is_(True))
            )
            .mappings()
            .all()
        )
        connection.execute(
            insert(AnimalImage).values(
                id=uuid4(),
                animal_id=old["id"],
                image_url="https://example.invalid/manual.jpg",
                sort_order=9,
                image_type="adoption",
            )
        )
        connection.execute(
            insert(Tag).values(key="human_fixture", type="trait", label="Manual test fixture")
        )
        connection.execute(
            insert(AnimalTag).values(
                id=uuid4(),
                animal_id=old["id"],
                tag_key="human_fixture",
                confidence=1,
                generator="manual",
                generator_version="1",
                evidence="human fixture",
            )
        )
    changed = row | {
        "processState": "보호중",
        "specialMark": "수정한 검토용 원문",
        "popfile1": row["popfile2"],
        "popfile2": "https://example.invalid/new.jpg",
        "weight": "15(Kg)",
        "age": "2010(년생)",
        "colorCd": "크림색",
        "updTm": "2026-09-15T04:00:00Z",
    }
    result = sync(sync_engine, SnapshotClient([changed]), clock=lambda: NOW + timedelta(hours=1))
    assert result.status == "success" and result.updated_count == 1
    with sync_engine.connect() as connection:
        updated = (
            connection.execute(select(Animal.__table__).where(Animal.id == old["id"]))
            .mappings()
            .one()
        )
        images = (
            connection.execute(
                select(AnimalImage.__table__).where(AnimalImage.animal_id == old["id"], AnimalImage.is_active.is_(True))
            )
            .mappings()
            .all()
        )
        tags = set(
            connection.scalars(select(AnimalTag.tag_key).where(AnimalTag.animal_id == old["id"], AnimalTag.is_active.is_(True)))
        )
    for field in ("id", "created_at", "first_seen_at"):
        assert updated[field] == old[field]
    assert updated["last_seen_at"] == updated["updated_at"] == NOW + timedelta(hours=1)
    assert updated["source_updated_at"] == NOW + timedelta(hours=1)
    assert (
        updated["process_state"] == "보호중" and updated["special_mark"] == "수정한 검토용 원문"
    )
    assert updated["raw_payload"] == changed
    assert {image["image_url"] for image in images} == {
        row["popfile2"],
        changed["popfile2"],
        "https://example.invalid/manual.jpg",
    }
    retained = next(image for image in images if image["image_url"] == row["popfile2"])
    original = next(image for image in old_images if image["image_url"] == row["popfile2"])
    assert retained["id"] == original["id"] and retained["sort_order"] == 1
    assert tags == {"cream_coat", "sturdy", "human_fixture"}
    with sync_engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(AnimalImage).where(AnimalImage.animal_id == old["id"], AnimalImage.is_active.is_(False))) == 1
        assert connection.scalar(select(func.count()).select_from(AnimalTag).where(AnimalTag.animal_id == old["id"], AnimalTag.is_active.is_(False))) > 0
    assert counts(sync_engine)["animals"] == 2


@pytest.mark.parametrize(
    "error", ["HTTP_ERROR", "APPLICATION_ERROR", "NETWORK_ERROR", "RESPONSE_SHAPE_UNRESOLVED"]
)
def test_catastrophic_first_page_failure_keeps_existing_data(sync_engine, error, caplog):
    assert run(sync_engine, [source_row()]).status == "success"
    before = counts(sync_engine)
    client = SnapshotClient([], fail_on=1, failure=ApiFailure(error))
    result = sync(sync_engine, client)
    assert result.status == "failed" and result.pagination.failed_pages == [1]
    assert counts(sync_engine) == before
    with sync_engine.connect() as connection:
        assert (
            connection.scalar(select(SyncRun.status).where(SyncRun.id == result.sync_id))
            == "failed"
        )
        assert (
            connection.scalar(select(SyncRun.finished_at).where(SyncRun.id == result.sync_id))
            is not None
        )
    assert "password" not in caplog.text and "serviceKey" not in caplog.text


@pytest.mark.parametrize(
    "client",
    [SnapshotClient([]), SnapshotClient([], total=3), SnapshotClient([source_row()], total=0)],
)
def test_zero_and_abnormal_totals_do_not_delete_or_update(sync_engine, client):
    assert run(sync_engine, [source_row()]).status == "success"
    before = counts(sync_engine)
    result = sync(sync_engine, client)
    assert result.status == "failed"
    assert result.inserted_count == result.updated_count == 0
    assert counts(sync_engine) == before


def test_later_page_failure_reports_partial_committed_work(sync_engine):
    client = SnapshotClient(
        [source_row(str(i)) for i in range(4)], fail_on=2, failure=ApiFailure("HTTP_ERROR")
    )
    result = sync(sync_engine, client, page_size=2)
    assert result.status == "failed"
    assert result.inserted_count == counts(sync_engine)["animals"] == 2
    with sync_engine.connect() as connection:
        error = connection.scalar(select(SyncRun.error_message).where(SyncRun.id == result.sync_id))
    assert json.loads(error)["partial_batches_committed"] is True


def test_batch_failure_rolls_back_children_and_counters_then_replay_recovers(
    sync_engine, monkeypatch
):
    original = SyncRepository.reconcile_tags
    calls = 0

    def fail_second(self, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            self.connection.execute(text("SELECT 1 / 0"))
        return original(self, *args, **kwargs)

    monkeypatch.setattr(SyncRepository, "reconcile_tags", fail_second)
    rows = [source_row(str(i)) for i in range(501)]
    result = run(sync_engine, rows)
    assert result.status == "failed" and result.inserted_count == 500
    assert counts(sync_engine)["animals"] == 500
    assert counts(sync_engine)["animal_images"] == 1000
    monkeypatch.setattr(SyncRepository, "reconcile_tags", original)
    recovery = run(sync_engine, rows)
    assert (
        recovery.status == "success"
        and recovery.inserted_count == 1
        and recovery.updated_count == 0
        and recovery.unchanged_count == 500
    )
    assert counts(sync_engine)["animals"] == 501


def test_serialization_failure_retries_whole_batch_without_duplicates(sync_engine, monkeypatch):
    original = SyncRepository.reconcile_tags
    calls = 0

    def fail_once(self, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            self.connection.execute(
                text("DO $$ BEGIN RAISE EXCEPTION 'test rollback' USING ERRCODE = '40001'; END $$")
            )
        return original(self, *args, **kwargs)

    monkeypatch.setattr(SyncRepository, "reconcile_tags", fail_once)
    result = run(sync_engine, [source_row()])
    assert (
        result.status == "success" and result.database_retries == 1 and result.inserted_count == 1
    )
    assert counts(sync_engine)["animal_tags"] == 2


@pytest.mark.parametrize(
    "field, value, code",
    [
        ("desertionNo", None, "SOURCE_VALIDATION_CATASTROPHIC"),
        ("weight", "unparseable", "PARSING_CATASTROPHIC"),
    ],
)
def test_catastrophic_validation_does_not_clear_existing_facts(sync_engine, field, value, code):
    assert run(sync_engine, [source_row()]).status == "success"
    before = counts(sync_engine)
    rows = [source_row(str(i), **{field: value}) for i in range(20)]
    result = run(sync_engine, rows)
    assert result.status == "failed" and result.error_code == code
    assert counts(sync_engine) == before


def test_small_rejection_is_reported_as_failed_with_valid_rows_committed(sync_engine):
    rows = [source_row(str(i)) for i in range(20)]
    rows[0]["desertionNo"] = None
    result = run(sync_engine, rows)
    assert result.status == "failed" and result.rejected_count == 1 and result.inserted_count == 19
    assert result.error_code in {"ROWS_REJECTED", "UNIQUE_COUNT_MISMATCH"}


def test_concurrent_sync_is_refused_and_recorded(sync_engine):
    with sync_engine.connect() as lock:
        lock.execute(
            text("SELECT pg_advisory_lock(:namespace,:source)"),
            {"namespace": LOCK_NAMESPACE, "source": LOCK_SOURCE},
        )
        lock.commit()
        try:
            result = run(sync_engine, [source_row()])
            assert result.status == "failed" and result.error_code == "SYNC_ALREADY_RUNNING"
            assert counts(sync_engine)["animals"] == 0
        finally:
            lock.execute(
                text("SELECT pg_advisory_unlock(:namespace,:source)"),
                {"namespace": LOCK_NAMESPACE, "source": LOCK_SOURCE},
            )
            lock.commit()


def test_older_aware_source_cannot_replace_newer_snapshot(sync_engine):
    assert run(sync_engine, [source_row(updTm="2026-09-15T03:00:00Z")]).status == "success"
    old = source_row(
        updTm="2026-09-14T03:00:00Z", specialMark="older snapshot", popfile1=None, popfile2=None
    )
    result = run(sync_engine, [old])
    assert result.status == "success" and result.stale_count == 1
    assert result.updated_count == 0
    with sync_engine.connect() as connection:
        assert connection.scalar(select(Animal.special_mark)) == "검토용 원문"
    assert counts(sync_engine)["animal_images"] == 2


def test_year_change_does_not_generate_retired_age_tags(sync_engine):
    row = source_row()
    assert run(sync_engine, [row]).status == "success"
    result = sync(sync_engine, SnapshotClient([row]), clock=lambda: NOW.replace(year=2027))
    assert result.status == "success"
    assert result.updated_count == 0 and result.unchanged_count == 1
    with sync_engine.connect() as connection:
        tags = set(connection.scalars(select(AnimalTag.tag_key)))
    assert tags == {"white_coat", "cuddly"}


def test_identical_snapshot_only_refreshes_observation_timestamp(sync_engine):
    row = source_row(extraField={"a": 1, "b": 2})
    assert run(sync_engine, [row]).status == "success"
    with sync_engine.connect() as connection:
        before = connection.execute(select(Animal.__table__)).mappings().one()
    later = NOW + timedelta(days=1)
    same = row | {"extraField": {"b": 2, "a": 1}}
    result = sync(sync_engine, SnapshotClient([same]), clock=lambda: later)
    assert result.status == "success"
    assert result.inserted_count == result.updated_count == 0
    assert result.unchanged_count == 1
    with sync_engine.connect() as connection:
        after = connection.execute(select(Animal.__table__)).mappings().one()
    assert after["last_seen_at"] == later
    for name in ("id", "first_seen_at", "created_at", "updated_at", "raw_payload"):
        assert before[name] == after[name]


def test_smoke_limit_refuses_oversized_scope_before_domain_writes(sync_engine):
    result = run(sync_engine, [source_row(str(i)) for i in range(3)], max_animals=2)
    assert result.status == "failed" and result.error_code == "SOURCE_TOTAL_EXCEEDS_LIMIT"
    assert result.inserted_count == result.updated_count == 0
    assert all(count == 0 for count in counts(sync_engine).values())
