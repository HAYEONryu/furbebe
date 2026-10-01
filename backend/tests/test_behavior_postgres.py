"""TRAIT-only reconciliation in disposable schemas, never application databases."""

from uuid import uuid4

import pytest
from sqlalchemy import insert, select, text, update

from backend.app.db.models import Animal, AnimalTag, Tag
from backend.jobs.animal_sync import behavior_retag
from backend.jobs.animal_sync.behavior_retag import (
    fingerprint,
    protected_fingerprints,
    reconcile_behavior,
    rehearsal,
)
from backend.jobs.animal_sync.client import ApiFailure
from backend.jobs.animal_sync.service import LOCK_NAMESPACE, LOCK_SOURCE
from backend.jobs.animal_sync.tagger.behavior import ALL_RULE_IDS, RELEASED_RULE_IDS, RULES
from backend.tests.sync_fixtures import source_row
from backend.tests.test_behavior import POSITIVES
from backend.tests.test_sync_postgres import run
from backend.tests.test_sync_postgres import sync_engine as sync_engine

pytestmark = pytest.mark.postgres


@pytest.mark.parametrize("rule", RULES, ids=lambda rule: rule.rule_id)
def test_each_rule_migration_idempotency_and_fact_vibe_manual_preservation(sync_engine, rule):
    assert run(sync_engine, [source_row(specialMark=POSITIVES[rule.rule_id])]).status == "success"
    with sync_engine.begin() as connection:
        row = connection.execute(select(Animal.__table__)).mappings().one()
        connection.execute(insert(Tag).values(key="legacy_fact_fixture", type="fact", label="FACT"))
        connection.execute(insert(Tag).values(key="unrelated_trait", type="trait", label="Other"))
        for key, generator, version in (
            ("legacy_fact_fixture", "rules", "1.0"),
            (rule.tag_key, "rules", "1.0"),
            (rule.tag_key, "manual", "1.0"),
            (rule.tag_key, "rules", "future"),
            ("unrelated_trait", "rules", "1.0"),
        ):
            connection.execute(
                insert(AnimalTag).values(
                    id=uuid4(),
                    animal_id=row["id"],
                    tag_key=key,
                    confidence=1,
                    evidence="SYNTHETIC TEST",
                    rule_id="fixture",
                    generator=generator,
                    generator_version=version,
                )
            )
        protected = protected_fingerprints(connection)
        reconcile_behavior(connection, [row], rule_ids={rule.rule_id})
        first = fingerprint(connection, select(AnimalTag.__table__).order_by(AnimalTag.id))
        reconcile_behavior(connection, [row], rule_ids={rule.rule_id})
        second = fingerprint(connection, select(AnimalTag.__table__).order_by(AnimalTag.id))
        assert first == second
        assert protected_fingerprints(connection) == protected
        assignments = (
            connection.execute(
                select(AnimalTag.__table__).where(
                    AnimalTag.generator == "rules",
                    AnimalTag.generator_version.in_(("1.0", "2.0", "3.0")),
                    AnimalTag.tag_key == rule.tag_key,
                )
            )
            .mappings()
            .all()
        )
        assert len(assignments) == 1
        assert assignments[0]["generator_version"] == "3.0"
        assert all(
            assignments[0][field] for field in ("evidence", "rule_id", "confidence", "generator")
        )
        # Removing evidence removes the known automatic TRAIT and nothing protected.
        reconcile_behavior(
            connection, [{**row, "special_mark": "목줄 착용"}], rule_ids={rule.rule_id}
        )
        assert protected_fingerprints(connection) == protected
        assert not connection.scalar(
            select(AnimalTag.id).where(
                AnimalTag.tag_key == rule.tag_key,
                AnimalTag.generator == "rules",
                AnimalTag.generator_version == "3.0",
            )
        )


def test_rehearsal_writes_twice_and_rolls_back_everything(sync_engine):
    assert run(sync_engine, [source_row(adptnTxt="사람을 좋아함")]).status == "success"
    with sync_engine.connect() as connection:
        before = {
            model.__tablename__: fingerprint(
                connection,
                select(model.__table__).order_by(
                    model.key if model is Tag else model.id,
                ),
            )
            for model in (Tag, AnimalTag, Animal)
        }
    result = rehearsal(sync_engine, verify=True, batch_size=1)
    assert result["committed"] is False and set(result["rules_released"]) == RELEASED_RULE_IDS
    assert result["candidate_counts"] == {"people_friendly": 1}
    assert result["protected_unchanged"] and result["idempotent"]
    with sync_engine.connect() as connection:
        after = {
            model.__tablename__: fingerprint(
                connection,
                select(model.__table__).order_by(
                    model.key if model is Tag else model.id,
                ),
            )
            for model in (Tag, AnimalTag, Animal)
        }
    assert after == before
    assert rehearsal(sync_engine)["status"] == "released_preview"


def test_disabled_catalog_and_type_conflict(sync_engine):
    assert run(sync_engine, [source_row(specialMark="온순함")]).status == "success"
    with sync_engine.begin() as connection:
        rows = connection.execute(select(Animal.__table__)).mappings().all()
        connection.execute(update(Tag).where(Tag.key == "gentle").values(is_active=False))
        assert not reconcile_behavior(connection, rows, rule_ids=ALL_RULE_IDS)
        assert connection.scalar(select(Tag.is_active).where(Tag.key == "gentle")) is False
        connection.execute(update(Tag).where(Tag.key == "gentle").values(type="vibe"))
        with pytest.raises(ApiFailure, match="BEHAVIOR_CATALOG_TYPE_CONFLICT"):
            reconcile_behavior(connection, rows, rule_ids=ALL_RULE_IDS)


@pytest.mark.parametrize("mode", ({"verify": True}, {"apply": True}))
def test_rehearsal_lock_and_atomic_rollback(sync_engine, monkeypatch, mode):
    assert (
        run(sync_engine, [source_row("a", specialMark="온순함"), source_row("b")]).status
        == "success"
    )
    with sync_engine.connect() as lock:
        lock.execute(
            text("SELECT pg_advisory_lock(:namespace, :source)"),
            {"namespace": LOCK_NAMESPACE, "source": LOCK_SOURCE},
        )
        lock.commit()
        try:
            with pytest.raises(ApiFailure, match="SYNC_ALREADY_RUNNING"):
                rehearsal(sync_engine, **mode)
        finally:
            lock.execute(
                text("SELECT pg_advisory_unlock(:namespace, :source)"),
                {"namespace": LOCK_NAMESPACE, "source": LOCK_SOURCE},
            )
            lock.commit()
    with sync_engine.connect() as connection:
        before = fingerprint(connection, select(AnimalTag.__table__).order_by(AnimalTag.id))
    original = behavior_retag.reconcile_behavior
    calls = 0

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ApiFailure("TEST_ROLLBACK")
        return original(*args, **kwargs)

    monkeypatch.setattr(behavior_retag, "reconcile_behavior", fail_second)
    with pytest.raises(ApiFailure, match="TEST_ROLLBACK"):
        rehearsal(sync_engine, batch_size=1, **mode)
    with sync_engine.connect() as connection:
        assert fingerprint(connection, select(AnimalTag.__table__).order_by(AnimalTag.id)) == before


def test_operational_cli_rejects_production(capsys):
    with pytest.raises(SystemExit) as exc:
        behavior_retag.main(["--database-target", "production", "--verify"])
    assert exc.value.code == 2


def test_dev_apply_commits_released_traits_and_is_idempotent_across_transactions(sync_engine):
    assert run(sync_engine, [source_row()]).status == "success"
    with sync_engine.begin() as connection:
        connection.execute(
            update(Animal).values(
                special_mark="온순함. 애교가 많음. 무릎강아지.",
                raw_payload={"adptnTxt": "사람을 좋아함"},
            )
        )
        protected = protected_fingerprints(connection)
    first = rehearsal(sync_engine, apply=True, batch_size=1)
    assert first["committed"] and first["protected_unchanged"] and first["idempotent"]
    assert first["candidate_counts"] == {"gentle": 1, "people_friendly": 1}
    assert first["human_precision_measured"] is False
    with sync_engine.connect() as connection:
        assert protected_fingerprints(connection) == protected
        rows = (
            connection.execute(
                select(AnimalTag.__table__).where(
                    AnimalTag.generator_version == "3.0",
                )
            )
            .mappings()
            .all()
        )
        assert len(rows) == 2
        assert all(row["evidence"] and row["rule_id"] for row in rows)
    second = rehearsal(sync_engine, apply=True, batch_size=1)
    assert (
        first["assignments_second"] == second["assignments_first"] == second["assignments_second"]
    )


def test_sync_migrates_only_automatic_traits_and_preserves_legacy_catalog(sync_engine):
    source = source_row(specialMark="온순함", adptnTxt="사람을 좋아함", sfeHealth="활발함")
    assert run(sync_engine, [source]).status == "success"
    with sync_engine.begin() as connection:
        animal_id = connection.scalar(select(Animal.id))
        connection.execute(
            insert(Tag),
            [
                {"key": "puppy", "type": "fact", "label": "기존 FACT"},
                {"key": "cloud", "type": "vibe", "label": "기존 VIBE"},
            ],
        )
        for key, version, generator in (
            ("puppy", "1.0", "rules"),
            ("cloud", "1.0", "rules"),
            ("gentle", "2.0", "rules"),
            ("affectionate", "2.0", "rules"),
            ("affectionate", "1", "manual"),
        ):
            connection.execute(
                insert(AnimalTag).values(
                    id=uuid4(),
                    animal_id=animal_id,
                    tag_key=key,
                    confidence=1,
                    evidence="fixture",
                    rule_id="fixture",
                    generator=generator,
                    generator_version=version,
                )
            )
        before = protected_fingerprints(connection)
    result = run(sync_engine, [source])
    assert result.status == "success" and result.unchanged_count == 1
    with sync_engine.connect() as connection:
        after = protected_fingerprints(connection)
        for key in ("protected_tag_catalog", "protected_assignments"):
            assert before[key] == after[key]
        automatic = connection.execute(
            select(AnimalTag.tag_key, AnimalTag.generator_version).where(
                AnimalTag.generator == "rules",
                AnimalTag.tag_key.in_(("gentle", "people_friendly", "affectionate", "playful")),
            )
        ).all()
        assert set(automatic) == {("gentle", "3.0"), ("people_friendly", "3.0")}
    # Source removal clears only released automatic traits, including adoption text.
    source.update(specialMark="목줄 착용", adptnTxt="")
    assert run(sync_engine, [source]).status == "success"
    with sync_engine.connect() as connection:
        assert not connection.scalar(
            select(AnimalTag.id).where(AnimalTag.generator_version == "3.0")
        )
