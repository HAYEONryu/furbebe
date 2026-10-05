"""Regenerate the entire tag dictionary and assignments in one transaction."""

import argparse
import json
from collections import Counter
from uuid import uuid4

from sqlalchemy import delete, insert, select, text

from backend.app.core.database_target import get_operational_settings
from backend.app.db.models import Animal, AnimalTag, Tag
from backend.app.db.session import create_database_engine
from backend.jobs.animal_sync.normalizer import normalize_animal
from backend.jobs.animal_sync.repositories import chunks
from backend.jobs.animal_sync.service import LOCK_NAMESPACE, LOCK_SOURCE
from backend.jobs.animal_sync.source_models import ValidatedAnimal
from backend.jobs.animal_sync.status_policy import korea_today
from backend.jobs.animal_sync.tagger import CATALOG, VERSION, generate_tags


def rebuild(engine, *, apply=False):
    today = korea_today()
    with engine.begin() as connection:
        connection.execute(text("SET LOCAL statement_timeout = '60s'"))
        if apply:
            locked = connection.scalar(
                text("SELECT pg_try_advisory_xact_lock(:namespace, :source)"),
                {"namespace": LOCK_NAMESPACE, "source": LOCK_SOURCE},
            )
            if not locked:
                raise RuntimeError("SYNC_ALREADY_RUNNING")
            connection.execute(text("SET LOCAL lock_timeout = '10s'"))
            connection.execute(text(
                "LOCK TABLE animals, tags, animal_tags IN SHARE ROW EXCLUSIVE MODE"
            ))
        else:
            connection.execute(text("SET TRANSACTION READ ONLY"))
        animals = connection.execute(select(Animal.id, Animal.raw_payload)).all()
        assignments = []
        seen = set()
        counts = Counter()
        for animal in animals:
            normalized = normalize_animal(
                ValidatedAnimal.model_validate(animal.raw_payload), today=today
            )
            for tag in generate_tags(normalized, today=today):
                identity = (animal.id, tag.tag_key)
                if identity in seen:
                    raise RuntimeError("DUPLICATE_GENERATED_TAG")
                seen.add(identity)
                counts[tag.tag_key] += 1
                assignments.append(dict(
                    id=uuid4(), animal_id=animal.id, tag_key=tag.tag_key,
                    confidence=tag.confidence, evidence=tag.evidence, rule_id=tag.rule_id,
                    generator=tag.generator, generator_version=tag.generator_version,
                ))
        if apply:
            connection.execute(delete(AnimalTag))
            connection.execute(delete(Tag))
            connection.execute(insert(Tag), CATALOG)
            for batch in chunks(assignments, 500):
                connection.execute(insert(AnimalTag), batch)
            duplicates = connection.scalar(text('''
                SELECT count(*) FROM (
                    SELECT animal_id, tag_key FROM animal_tags
                    GROUP BY animal_id, tag_key HAVING count(*) > 1
                ) duplicates
            '''))
            missing = connection.scalar(text(
                "SELECT count(*) FROM tags WHERE emoji IS NULL OR btrim(emoji) = ''"
            ))
            if duplicates or missing:
                raise RuntimeError("TAG_VERIFICATION_FAILED")
        return {
            "applied": apply, "version": VERSION, "animals": len(animals),
            "assignments": len(assignments), "duplicates": 0,
            "tags": [dict(key=t["key"], label=t["label"], emoji=t["emoji"],
                          assignments=counts[t["key"]]) for t in CATALOG],
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True,
                        choices=["local", "supabase-dev", "supabase-prod"])
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    engine = create_database_engine(get_operational_settings(args.target))
    try:
        result = rebuild(engine, apply=args.apply)
        print(json.dumps(result, ensure_ascii=False))
    except Exception as error:
        print(json.dumps({"status": "failed", "error_type": type(error).__name__}))
        raise SystemExit(1) from None
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
