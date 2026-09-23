"""DEV-only TRAIT preview, rollback rehearsal and verified release regeneration."""

import argparse
import hashlib
import json
from collections import Counter

from sqlalchemy import and_, not_, select, text
from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.config import ConfigurationError
from backend.app.core.database_target import get_dev_database_settings
from backend.app.db.models import Animal, AnimalImage, AnimalTag, Shelter, SyncRun, Tag
from backend.app.db.session import DatabaseNotConfigured, create_database_engine

from .client import ApiFailure
from .normalizer import SOURCE
from .repositories import owned_assignments, reconcile_behavior
from .service import LOCK_NAMESPACE, LOCK_SOURCE
from .tagger.behavior import (
    ALL_RULE_IDS,
    GENERATOR,
    RELEASE_BASIS,
    RELEASED_RULE_IDS,
    VERSION,
    generate_behavior_tags,
)
from .tagger.catalog import TRAIT_KEYS


def fingerprint(connection, statement):
    digest = hashlib.sha256()
    count = 0
    for row in connection.execute(statement).mappings():
        digest.update(
            json.dumps(dict(row), sort_keys=True, default=str, ensure_ascii=False).encode()
        )
        digest.update(b"\n")
        count += 1
    return {"count": count, "sha256": digest.hexdigest()}


def protected_fingerprints(connection):
    statements = {
        model.__tablename__: select(model.__table__).order_by(model.id)
        for model in (Animal, AnimalImage, Shelter, SyncRun)
    }
    statements["protected_tag_catalog"] = (
        select(Tag.__table__)
        .where(
            not_(and_(Tag.key.in_(TRAIT_KEYS), Tag.type == "trait")),
        )
        .order_by(Tag.key)
    )
    statements["protected_assignments"] = (
        select(AnimalTag.__table__)
        .where(
            not_(owned_assignments()),
        )
        .order_by(AnimalTag.id)
    )
    return {name: fingerprint(connection, statement) for name, statement in statements.items()}


def rehearsal(engine, *, verify=False, apply=False, batch_size=500):
    """Regenerate twice and check all protected rows before an explicit DEV commit.

    verify=True evaluates all candidates and rolls back; apply=True commits only
    released rules. Both modes verify idempotency before completing.
    The operational CLI resolves only the specifically named Supabase DEV target.
    """
    if verify and apply:
        raise ValueError("Choose either verify or apply")
    if not 1 <= batch_size <= 1000:
        raise ValueError("batch_size must be 1..1000")
    if apply and not RELEASED_RULE_IDS:
        raise ApiFailure("NO_RELEASED_BEHAVIOR_RULES")
    write = verify or apply
    rule_ids = ALL_RULE_IDS if verify else RELEASED_RULE_IDS
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            if not write:
                connection.execute(text("SET TRANSACTION READ ONLY"))
            if not connection.scalar(
                text("SELECT pg_try_advisory_xact_lock(:namespace, :source)"),
                {"namespace": LOCK_NAMESPACE, "source": LOCK_SOURCE},
            ):
                raise ApiFailure("SYNC_ALREADY_RUNNING")
            before = protected_fingerprints(connection) if write else None
            statement = (
                select(
                    Animal.id,
                    Animal.special_mark,
                    Animal.social_text,
                    Animal.raw_payload,
                )
                .where(Animal.source == SOURCE)
                .order_by(Animal.id)
            )
            rows = connection.execute(statement).mappings().all()
            counts = Counter()
            if write:
                for offset in range(0, len(rows), batch_size):
                    counts.update(
                        reconcile_behavior(
                            connection, rows[offset : offset + batch_size], rule_ids=rule_ids
                        )
                    )
                first = fingerprint(connection, select(AnimalTag.__table__).order_by(AnimalTag.id))
                for offset in range(0, len(rows), batch_size):
                    reconcile_behavior(
                        connection, rows[offset : offset + batch_size], rule_ids=rule_ids
                    )
                second = fingerprint(connection, select(AnimalTag.__table__).order_by(AnimalTag.id))
                after = protected_fingerprints(connection)
                if before != after or first != second:
                    raise ApiFailure("BEHAVIOR_REGENERATION_INVARIANT_FAILED")
            else:
                for row in rows:
                    counts.update(t.tag_key for t in generate_behavior_tags(row, rule_ids=rule_ids))
            if apply:
                transaction.commit()
            return {
                "status": "released_traits_committed"
                if apply
                else ("candidate_rehearsal_rolled_back" if verify else "released_preview"),
                "generator": GENERATOR,
                "generator_version": VERSION,
                "animals": len(rows),
                "candidate_assignments": sum(counts.values()),
                "candidate_counts": dict(counts),
                "committed": apply,
                "rules_released": sorted(RELEASED_RULE_IDS),
                "evaluated_rules": sorted(rule_ids),
                "release_basis": RELEASE_BASIS,
                "human_precision_measured": False,
                "protected_unchanged": before == after if write else None,
                "idempotent": first == second if write else None,
                "protected_before": before,
                "protected_after": after if write else None,
                "assignments_first": first if write else None,
                "assignments_second": second if write else None,
            }
        finally:
            if transaction.is_active:
                transaction.rollback()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-target", choices=("supabase-dev",), required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--verify", action="store_true", help="Regenerate candidates twice, then roll back"
    )
    mode.add_argument(
        "--apply", action="store_true", help="Verify and commit released TRAIT rules to DEV"
    )
    args = parser.parse_args(argv)
    engine = None
    try:
        engine = create_database_engine(get_dev_database_settings())
        print(
            json.dumps(rehearsal(engine, verify=args.verify, apply=args.apply), ensure_ascii=True)
        )
        return 0
    except (ApiFailure, ConfigurationError, DatabaseNotConfigured, SQLAlchemyError):
        print(json.dumps({"status": "failed", "error_code": "BEHAVIOR_REHEARSAL_FAILED"}))
        return 2
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
