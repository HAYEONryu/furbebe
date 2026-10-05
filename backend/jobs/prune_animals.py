"""Explicit, transactional cleanup of posts outside the protected/adoptable dog scope."""

import argparse
import json

from sqlalchemy import and_, delete, func, not_, select, text

from backend.app.core.database_target import get_operational_settings
from backend.app.db.models import Animal
from backend.app.db.session import create_database_engine
from backend.jobs.animal_sync.normalizer import SOURCE
from backend.jobs.animal_sync.service import LOCK_NAMESPACE, LOCK_SOURCE
from backend.jobs.animal_sync.status_policy import korea_today


def prune(engine, *, apply=False):
    today = korea_today()
    eligible = and_(
        Animal.species == "dog", Animal.process_state.in_(["보호중", "입양 가능"])
    )
    scope = Animal.source == SOURCE
    unwanted = and_(scope, not_(func.coalesce(eligible, False)))
    with engine.begin() as connection:
        connection.exec_driver_sql("SET LOCAL statement_timeout = 60000")
        if apply:
            locked = connection.scalar(
                text("SELECT pg_try_advisory_xact_lock(:namespace, :source)"),
                {"namespace": LOCK_NAMESPACE, "source": LOCK_SOURCE},
            )
            if not locked:
                raise RuntimeError("Sync is running; retry cleanup later")
            connection.exec_driver_sql("LOCK TABLE animals IN SHARE ROW EXCLUSIVE MODE")
        total = connection.scalar(select(func.count()).select_from(Animal).where(scope))
        ended = connection.scalar(
            select(func.count()).select_from(Animal).where(scope, Animal.process_state.like("종료%"))
        )
        candidates = connection.scalar(select(func.count()).select_from(Animal).where(unwanted))
        deleted = connection.execute(delete(Animal).where(unwanted)).rowcount if apply else 0
        remaining = connection.scalar(select(func.count()).select_from(Animal).where(scope))
        outside_scope = connection.scalar(
            select(func.count()).select_from(Animal).where(unwanted)
        )
        if apply and (deleted != candidates or outside_scope != 0):
            raise RuntimeError("Cleanup verification failed; transaction rolled back")
        return {
            "as_of_date": today.isoformat(), "applied": apply, "before": total,
            "ended": ended, "candidates": candidates, "deleted": deleted,
            "remaining": remaining, "outside_scope_remaining": outside_scope,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True,
                        choices=["local", "supabase-dev", "supabase-prod"])
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    engine = None
    try:
        engine = create_database_engine(get_operational_settings(args.target))
        print(json.dumps(prune(engine, apply=args.apply), ensure_ascii=False))
    except Exception as error:
        print(json.dumps({"error_type": type(error).__name__, "applied": False}))
        raise SystemExit(1) from None
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
