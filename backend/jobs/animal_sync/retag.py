"""Regenerate tags from stored source fields, without fetching or changing animals."""

import argparse
import json
from collections import Counter
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.config import ConfigurationError, get_settings
from backend.app.core.database_target import get_dev_database_settings
from backend.app.db.models import Animal, Tag
from backend.app.db.session import DatabaseNotConfigured, create_database_engine

from .client import ApiFailure
from .main import require_local_development
from .normalizer import SOURCE, NormalizedAnimal
from .repositories import SyncRepository
from .service import LOCK_NAMESPACE, LOCK_SOURCE
from .status_policy import korea_today
from .tagger import OWNED_KEYS, VERSION, generate_safety_badges, generate_tags
from .tagger.behavior import VERSION as BEHAVIOR_VERSION


def retag(engine, *, dry_run=False, batch_size=500):
    if not 1 <= batch_size <= 1000:
        raise ValueError("batch_size must be 1..1000")
    today = korea_today(datetime.now(UTC))
    report = {"generator_version": VERSION, "dry_run": dry_run, "animals": 0, "assignments": 0}
    report["generator_versions"] = {"trait": BEHAVIOR_VERSION, "vibe": VERSION}
    tag_counts, safety_counts = Counter(), Counter()
    with engine.begin() as connection:
        if not connection.scalar(
            text("SELECT pg_try_advisory_xact_lock(:namespace, :source)"),
            {"namespace": LOCK_NAMESPACE, "source": LOCK_SOURCE},
        ):
            raise ApiFailure("SYNC_ALREADY_RUNNING")
        repository = SyncRepository(connection)
        if dry_run:
            disabled = set(
                connection.scalars(
                    select(Tag.key).where(Tag.key.in_(OWNED_KEYS), Tag.is_active.is_(False))
                )
            )
            active = OWNED_KEYS - disabled
        else:
            active = repository.catalog()
        last_id = None
        while True:
            statement = (
                select(
                    Animal.id,
                    Animal.source_id,
                    Animal.special_mark,
                    Animal.social_text,
                    Animal.health_text,
                    Animal.color_text,
                    Animal.weight_kg,
                    Animal.raw_payload,
                )
                .where(Animal.source == SOURCE)
                .order_by(Animal.id)
                .limit(batch_size)
            )
            if last_id is not None:
                statement = statement.where(Animal.id > last_id)
            rows = connection.execute(statement).mappings().all()
            if not rows:
                break
            animals = [NormalizedAnimal(dict(row), None, ()) for row in rows]
            for animal in animals:
                tag_counts.update(
                    tag.tag_key
                    for tag in generate_tags(animal, today=today)
                    if tag.tag_key in active
                )
                safety_counts.update(
                    badge["key"] for badge in generate_safety_badges(animal.values)
                )
            if not dry_run:
                repository.reconcile_tags(
                    animals,
                    {row["source_id"]: row["id"] for row in rows},
                    active=active,
                    today=today,
                )
            report["animals"] += len(rows)
            last_id = rows[-1]["id"]
    report.update(
        assignments=sum(tag_counts.values()), tags=dict(tag_counts), safety=dict(safety_counts)
    )
    return report


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--database-target", choices=("local", "supabase-dev"), required=True)
    cli.add_argument("--dry-run", action="store_true")
    args = cli.parse_args(argv)
    engine = None
    try:
        if args.database_target == "supabase-dev":
            settings = get_dev_database_settings()
        else:
            settings = get_settings()
            require_local_development(settings)
        engine = create_database_engine(settings)
        report = retag(engine, dry_run=args.dry_run)
        print(json.dumps({"status": "success", **report}, ensure_ascii=True))
        return 0
    except (ApiFailure, ConfigurationError, DatabaseNotConfigured, SQLAlchemyError):
        # Never print a connection exception containing database credentials.
        print(json.dumps({"status": "failed", "error_code": "RETAG_FAILED"}))
        return 2
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
