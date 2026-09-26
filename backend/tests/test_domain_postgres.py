"""Real PostgreSQL constraints and ORM ownership with synthetic, rolled-back fixtures."""

import io
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import CheckConstraint, func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.db.models import Animal, AnimalImage, AnimalTag, Base, Shelter, SyncRun, Tag
from backend.app.db.session import Database

pytestmark = pytest.mark.postgres


@pytest.fixture
def domain_session(postgres_settings):
    command.upgrade(
        Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"), stdout=io.StringIO()),
        "head",
    )
    database = Database(postgres_settings)
    try:
        with database.engine.connect() as connection, connection.begin():
            # The outer transaction is always rolled back, including if a test commits its Session.
            outer = connection.get_transaction()
            try:
                with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                    yield session
            finally:
                outer.rollback()
    finally:
        database.dispose()


@pytest.fixture
def graph(domain_session):
    shelter = Shelter(source="test_fixture", source_id="shelter-1", name="검토용 보호소")
    tag = Tag(key="test_fact", type="fact", label="검토용 사실")
    animal = Animal(
        source="test_fixture",
        source_id="animal-1",
        species="dog",
        shelter=shelter,
        raw_payload={"specialMark": "검토용 원문", "nested": {"value": None}},
        special_mark="검토용 원문",
        weight_kg=Decimal("5.0001"),
        birth_year=2024,
    )
    animal.images.append(AnimalImage(image_url="https://example.invalid/fixture.jpg"))
    animal.tag_assignments.append(
        AnimalTag(
            tag=tag,
            confidence=Decimal("0.8"),
            evidence="검토용 원문",
            rule_id="fixture-only",
            generator="fixture",
            generator_version="1",
        )
    )
    domain_session.add(animal)
    domain_session.flush()
    return animal, shelter, tag


def reject(session, instance, constraint):
    with pytest.raises(IntegrityError) as caught, session.begin_nested():
        session.add(instance)
        session.flush()
    assert caught.value.orig.diag.constraint_name == constraint


def test_live_schema_constraints_nullability_and_indexes(domain_session):
    inspector = inspect(domain_session.connection())
    for table in Base.metadata.sorted_tables:
        assert {c["name"]: c["nullable"] for c in inspector.get_columns(table.name)} == {
            c.name: c.nullable for c in table.columns
        }
        assert {c["name"] for c in inspector.get_check_constraints(table.name)} == {
            c.name for c in table.constraints if isinstance(c, CheckConstraint)
        }
        assert {
            tuple(i["column_names"])
            for i in inspector.get_indexes(table.name)
            if not i.get("duplicates_constraint")
        } == {tuple(i.columns.keys()) for i in table.indexes}
        assert {
            (f["constrained_columns"][0], f["referred_table"], f["options"]["ondelete"])
            for f in inspector.get_foreign_keys(table.name)
        } == {(f.parent.name, f.column.table.name, f.ondelete) for f in table.foreign_keys}
    assert inspector.get_view_names() == []


def test_jsonb_uuid_utc_and_missing_evidence_roundtrip(domain_session):
    local_time = datetime(2026, 9, 15, 12, tzinfo=timezone(timedelta(hours=9)))
    animal = Animal(
        source="fixture",
        source_id="minimal",
        raw_payload={"note": "원문", "null": None},
        source_updated_at=local_time,
    )
    domain_session.add(animal)
    domain_session.flush()
    domain_session.refresh(animal)
    assert isinstance(animal.id, UUID)
    assert animal.raw_payload == {"note": "원문", "null": None}
    assert domain_session.scalar(text("SHOW timezone")) == "UTC"
    assert animal.source_updated_at == local_time.astimezone(UTC)
    assert animal.source_updated_at.utcoffset() == timedelta(0)
    for name in ("created_at", "updated_at", "first_seen_at", "last_seen_at"):
        assert getattr(animal, name).utcoffset() == timedelta(0)
    for name in (
        "special_mark",
        "social_text",
        "health_text",
        "etc_text",
        "vaccination_text",
        "health_check_text",
        "weight_kg",
        "birth_year",
    ):
        assert getattr(animal, name) is None
    assert animal.tag_assignments == []
    assert animal.shelter is None


def test_animal_and_shelter_identity_is_scoped_by_source(domain_session, graph):
    animal, shelter, _ = graph
    reject(
        domain_session,
        Animal(source=animal.source, source_id=animal.source_id, raw_payload={}),
        "uq_animals_source_source_id",
    )
    reject(
        domain_session,
        Shelter(source=shelter.source, source_id=shelter.source_id),
        "uq_shelters_source_source_id",
    )
    domain_session.add_all(
        [
            Animal(source="other_source", source_id=animal.source_id, raw_payload={}),
            Shelter(source="other_source", source_id=shelter.source_id),
        ]
    )
    domain_session.flush()


def test_image_url_unique_only_within_animal(domain_session, graph):
    animal, _, _ = graph
    url = animal.images[0].image_url
    reject(
        domain_session,
        AnimalImage(animal_id=animal.id, image_url=url),
        "uq_animal_images_animal_id_image_url",
    )
    other = Animal(source="fixture", source_id="other", raw_payload={})
    other.images.append(AnimalImage(image_url=url))
    domain_session.add(other)
    domain_session.flush()


def test_assignment_unique_includes_generator_and_version(domain_session, graph):
    animal, _, tag = graph
    values = dict(
        animal_id=animal.id,
        tag_key=tag.key,
        confidence=Decimal("0.8"),
        generator="fixture",
        generator_version="1",
    )
    reject(domain_session, AnimalTag(**values), "uq_animal_tags_animal_tag_generator_version")
    domain_session.add_all(
        [
            AnimalTag(**(values | {"generator_version": "2"})),
            AnimalTag(**(values | {"generator": "review_fixture"})),
        ]
    )
    domain_session.flush()


@pytest.mark.parametrize("confidence", ["-0.001", "1.0001", "NaN", "Infinity"])
def test_confidence_rejects_out_of_range_without_rounding(domain_session, graph, confidence):
    animal, _, tag = graph
    reject(
        domain_session,
        AnimalTag(
            animal_id=animal.id,
            tag_key=tag.key,
            confidence=Decimal(confidence),
            generator="boundary",
            generator_version="1",
        ),
        "ck_animal_tags_confidence_range",
    )


@pytest.mark.parametrize("confidence", ["0", "1"])
def test_confidence_inclusive_boundaries(domain_session, graph, confidence):
    animal, _, tag = graph
    item = AnimalTag(
        animal_id=animal.id,
        tag_key=tag.key,
        confidence=Decimal(confidence),
        generator="boundary",
        generator_version="1",
    )
    domain_session.add(item)
    domain_session.flush()
    domain_session.refresh(item)
    assert item.confidence == Decimal(confidence)


@pytest.mark.parametrize("weight", ["-0.001", "NaN", "Infinity", "-Infinity"])
def test_weight_must_be_finite_and_nonnegative(domain_session, weight):
    reject(
        domain_session,
        Animal(source="fixture", source_id="weight", raw_payload={}, weight_kg=Decimal(weight)),
        "ck_animals_weight_kg_finite_nonnegative",
    )


def test_weight_zero_and_fraction_are_preserved_without_group_columns(domain_session, graph):
    animal, _, _ = graph
    domain_session.refresh(animal)
    assert animal.weight_kg == Decimal("5.0001")
    animal.weight_kg = Decimal("0")
    domain_session.flush()
    domain_session.refresh(animal)
    assert animal.weight_kg == 0


@pytest.mark.parametrize(
    "field,value,constraint",
    [
        ("sex", "unexpected", "ck_animals_sex_values"),
        ("neutered", "unexpected", "ck_animals_neutered_values"),
        ("birth_year", 0, "ck_animals_birth_year_range"),
        ("source_id", "   ", "ck_animals_source_id_nonempty"),
    ],
)
def test_invalid_normalized_values_are_rejected(domain_session, field, value, constraint):
    values = {"source": "fixture", "source_id": "invalid", "raw_payload": {}, field: value}
    reject(domain_session, Animal(**values), constraint)


@pytest.mark.parametrize("payload", [None, [], "text"])
def test_raw_payload_requires_json_object(domain_session, payload):
    with pytest.raises(IntegrityError), domain_session.begin_nested():
        domain_session.add(Animal(source="fixture", source_id="invalid-json", raw_payload=payload))
        domain_session.flush()


@pytest.mark.parametrize("tag_type", ["fact", "trait", "vibe"])
def test_tag_type_domain_with_test_fixture_only(domain_session, tag_type):
    domain_session.add(Tag(key="fixture", type=tag_type, label="Test fixture only"))
    domain_session.flush()
    reject(
        domain_session,
        Tag(key="invalid", type="unexpected", label="Invalid"),
        "ck_tags_type_values",
    )


@pytest.mark.parametrize("status", ["running", "success", "failed"])
def test_sync_status_domain_and_counter_defaults(domain_session, status):
    run = SyncRun(source="fixture", status=status)
    domain_session.add(run)
    domain_session.flush()
    assert (
        run.page_count
        == run.received_count
        == run.inserted_count
        == run.updated_count
        == run.error_count
        == 0
    )
    reject(
        domain_session, SyncRun(source="fixture", status="unknown"), "ck_sync_runs_status_values"
    )
    reject(
        domain_session, SyncRun(source="fixture", error_count=-1), "ck_sync_runs_counts_nonnegative"
    )


@pytest.mark.parametrize("loaded", [False, True])
def test_animal_delete_cascades_only_to_owned_rows(domain_session, graph, loaded):
    animal, shelter, tag = graph
    animal_id, shelter_id, tag_key = animal.id, shelter.id, tag.key
    domain_session.expunge_all()
    animal = domain_session.get(Animal, animal_id)
    if loaded:
        assert len(animal.images) == len(animal.tag_assignments) == 1
    domain_session.delete(animal)
    domain_session.flush()
    assert domain_session.scalar(select(func.count()).select_from(AnimalImage)) == 0
    assert domain_session.scalar(select(func.count()).select_from(AnimalTag)) == 0
    assert domain_session.get(Shelter, shelter_id) is not None
    assert domain_session.get(Tag, tag_key) is not None


@pytest.mark.parametrize("parent", ["shelter", "tag"])
@pytest.mark.parametrize("loaded", [False, True])
def test_referenced_shelter_and_tag_delete_is_restricted(domain_session, graph, parent, loaded):
    animal, shelter, tag = graph
    animal_id = animal.id
    model, key, relationship, constraint = (
        (Shelter, shelter.id, "animals", "fk_animals_shelter_id_shelters")
        if parent == "shelter"
        else (Tag, tag.key, "animal_assignments", "fk_animal_tags_tag_key_tags")
    )
    domain_session.expunge_all()
    instance = domain_session.get(model, key)
    if loaded:
        assert len(getattr(instance, relationship)) == 1
    with pytest.raises(IntegrityError) as caught, domain_session.begin_nested():
        domain_session.delete(instance)
        domain_session.flush()
    assert caught.value.orig.diag.constraint_name == constraint
    assert domain_session.get(Animal, animal_id).shelter_id is not None
    assert domain_session.scalar(select(func.count()).select_from(AnimalTag)) == 1


def test_missing_foreign_keys_cannot_create_orphans(domain_session):
    reject(
        domain_session,
        AnimalImage(animal_id=uuid4(), image_url="https://example.invalid/orphan.jpg"),
        "fk_animal_images_animal_id_animals",
    )


def test_unknown_source_state_is_preserved_and_updates_do_not_fake_observation(domain_session):
    old = datetime(2020, 1, 1, tzinfo=UTC)
    animal = Animal(
        source="fixture",
        source_id="unknown-state",
        raw_payload={},
        process_state="새로운 원본 상태",
        first_seen_at=old,
        last_seen_at=old,
        updated_at=old,
    )
    domain_session.add(animal)
    domain_session.flush()
    animal.breed = "검토용"
    domain_session.flush()
    domain_session.refresh(animal)
    assert animal.updated_at > old
    assert animal.first_seen_at == animal.last_seen_at == old
    assert animal.source_updated_at is None
    assert animal.process_state == "새로운 원본 상태"
