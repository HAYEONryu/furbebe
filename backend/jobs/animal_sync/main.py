"""Explicit local / Supabase DEV / approved PROD sync CLI. No schema auto-creation."""

import argparse
import json
import logging
from datetime import date
from pathlib import Path
from uuid import uuid4

from sqlalchemy.engine import make_url

from backend.app.core.config import ROOT, ConfigurationError, Settings, get_settings
from backend.app.core.database_target import (
    get_dev_database_settings,
    get_prod_database_settings,
)
from backend.app.db.session import DatabaseNotConfigured, create_database_engine

from .capture import RecordingClient, ReplayClient
from .client import AnimalApiClient, ApiFailure, load_service_key
from .service import sync


def require_local_development(settings: Settings):
    if not settings.database_url:
        raise ApiFailure("LOCAL_DATABASE_REQUIRED")
    url = make_url(settings.database_url.get_secret_value())
    if (
        settings.app_env == "production"
        or url.host not in {"127.0.0.1", "localhost", "::1"}
        or not (url.database or "").startswith(("furbebe_test", "furbebe_dev"))
        or set(url.query) & {"host", "hostaddr", "port", "dbname", "service", "servicefile"}
    ):
        raise ApiFailure("PHASE4A_LOCAL_DEVELOPMENT_DATABASE_REQUIRED")


def date_argument(value):
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Use YYYY-MM-DD") from None


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--begin-date", type=date_argument)
    cli.add_argument("--end-date", type=date_argument)
    cli.add_argument("--page-size", type=int, default=1000)
    cli.add_argument("--batch-size", type=int, default=500)
    cli.add_argument("--max-pages", type=int, default=10000)
    cli.add_argument("--max-animals", type=int, help="Reject a larger source total before writes")
    cli.add_argument(
        "--database-target", choices=("local", "supabase-dev", "supabase-prod"), default="local"
    )
    cli.add_argument(
        "--full",
        action="store_true",
        help="Scan every page of the API default date window, not all historical records",
    )
    cli.add_argument(
        "--replay", type=Path, help="Replay an existing .local/sync capture without network"
    )
    return cli


def main(argv=None):
    cli = parser()
    args = cli.parse_args(argv)
    if not 500 <= args.batch_size <= 1000 or not 1 <= args.page_size <= 1000 or args.max_pages < 1:
        cli.error("batch-size must be 500..1000; page-size 1..1000; max-pages positive")
    if args.max_animals is not None and args.max_animals < 1:
        cli.error("max-animals must be positive")
    if args.replay and (args.begin_date or args.end_date or args.full):
        cli.error("Replay uses the recorded date window")
    if args.full and (args.begin_date or args.end_date or args.max_animals):
        cli.error("Full sync cannot be combined with date or animal limits")
    if (
        not args.replay
        and not args.full
        and (not args.begin_date or not args.end_date or args.begin_date > args.end_date)
    ):
        cli.error("Live sync requires an ordered begin-date/end-date window")
    if args.database_target == "supabase-prod" and args.replay:
        cli.error("Production replay is not allowed")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    engine = client = recording = None
    try:
        if args.database_target == "supabase-dev":
            settings = get_dev_database_settings()
        elif args.database_target == "supabase-prod":
            settings = get_prod_database_settings()
        else:
            settings = get_settings()
            require_local_development(settings)
        output_root = (ROOT / ".local" / "sync").resolve()
        if not output_root.is_relative_to(ROOT):
            raise ApiFailure("UNSAFE_LOCAL_OUTPUT")
        if args.replay:
            path = args.replay.resolve()
            if not path.is_relative_to(output_root):
                raise ApiFailure("REPLAY_MUST_BE_UNDER_LOCAL_SYNC")
            client = ReplayClient(path, max_pages=args.max_pages)
            filters, page_size = client.filters, client.page_size
        else:
            client = AnimalApiClient(load_service_key(ROOT))
            filters = (
                {}
                if args.full
                else {
                    "bgnde": args.begin_date.strftime("%Y%m%d"),
                    "endde": args.end_date.strftime("%Y%m%d"),
                }
            )
            page_size = args.page_size
        output = output_root / uuid4().hex
        output.mkdir(parents=True, exist_ok=False)
        engine = create_database_engine(settings)
        if args.replay:
            input_client = client
        else:
            recording = RecordingClient(client, output / "pages.jsonl")
            input_client = recording
        report = sync(
            engine,
            input_client,
            batch_size=args.batch_size,
            page_size=page_size,
            max_pages=args.max_pages,
            max_animals=args.max_animals,
            filters=filters,
        )
        if recording:
            recording.close()
            recording = None
        logging.getLogger("furbebe.sync").info(
            json.dumps(
                {
                    "event": "sync_complete",
                    "sync_id": str(report.sync_id),
                    "status": report.status,
                    "received": report.pagination.fetched_count,
                    "inserted": report.inserted_count,
                    "updated": report.updated_count,
                    "error": report.error_count,
                    "error_code": report.error_code,
                    "duration_seconds": round(report.total_seconds, 6),
                }
            )
        )
        result = report.to_dict() | {
            "mode": "replay" if args.replay else "live",
            "database_target": args.database_target,
            "scope": "unfiltered_api" if not filters else "date_window",
            "query_without_key": filters,
            "output_directory": str(output.relative_to(ROOT)),
        }
        (output / "report.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(result, ensure_ascii=True))
        return 0 if report.status == "success" else 2
    except (ApiFailure, ConfigurationError, DatabaseNotConfigured, OSError) as exc:
        code = (
            exc.kind.split(":", 1)[0]
            if isinstance(exc, ApiFailure)
            else "SYNC_CONFIGURATION_OR_LOCAL_IO_ERROR"
        )
        print(json.dumps({"status": "failed", "error_code": code}))
        return 2
    finally:
        if recording:
            recording.close()
        if isinstance(client, ReplayClient):
            client.close()
        elif client:
            client.http.close()
        if engine:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
