"""Source validation and batch orchestration. Never infer absence from a failed scan."""

import hashlib
import json
import logging
import time
from collections import Counter
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .client import ApiFailure
from .normalizer import normalize_animal
from .pagination import PaginationProgress, iter_pages
from .parsing import meaningful
from .repositories import SyncRepository, chunks
from .source_models import ValidatedAnimal
from .status_policy import korea_today

LOGGER = logging.getLogger(__name__)
LOCK_NAMESPACE, LOCK_SOURCE = 1179996738, 1


@dataclass
class SyncReport:
    sync_id: UUID = field(default_factory=uuid4)
    status: str = "running"
    pagination: PaginationProgress = field(default_factory=PaginationProgress)
    normalized_count: int = 0
    rejected_count: int = 0
    duplicate_count: int = 0
    inserted_count: int = 0
    updated_count: int = 0
    unchanged_count: int = 0
    stale_count: int = 0
    excluded_count: int = 0
    deleted_count: int = 0
    error_count: int = 0
    error_code: str | None = None
    run_persisted: bool = False
    normalize_seconds: float = 0
    database_seconds: float = 0
    total_seconds: float = 0
    batch_size: int = 500
    database_retries: int = 0
    api_attempts: int = 0
    api_retries: int = 0
    normalization_issues: dict = field(default_factory=dict)
    pages: list[dict] = field(default_factory=list)

    def to_dict(self):
        result = asdict(self)
        result["sync_id"] = str(self.sync_id)
        result["rows_per_second"] = (
            (self.inserted_count + self.updated_count + self.unchanged_count + self.stale_count)
            / self.total_seconds
            if self.total_seconds
            else 0
        )
        return result


@contextmanager
def timed(report, field_name):
    started = time.perf_counter()
    try:
        yield
    finally:
        setattr(report, field_name, getattr(report, field_name) + time.perf_counter() - started)


def emit(
    report,
    *,
    page,
    received=0,
    normalized=0,
    rejected=0,
    inserted=0,
    updated=0,
    duration=0,
    event="page",
):
    record = dict(
        sync_id=str(report.sync_id),
        event=event,
        page=page,
        received=received,
        normalized=normalized,
        rejected=rejected,
        inserted=inserted,
        updated=updated,
        duration=round(duration, 6),
    )
    report.pages.append(record)
    LOGGER.info(json.dumps(record))


def validate_json_text(value):
    """PostgreSQL JSONB needs valid UTF-8 strings without actual NUL characters."""
    if isinstance(value, str):
        if "\x00" in value:
            raise ValueError("Unsupported source character")
        value.encode("utf-8")
    elif isinstance(value, dict):
        for key, child in value.items():
            validate_json_text(key)
            validate_json_text(child)
    elif isinstance(value, list):
        for child in value:
            validate_json_text(child)


def prepare_page(page, seen, report, *, today):
    normalized = []
    rejected = 0
    issues = Counter()
    with timed(report, "normalize_seconds"):
        for raw in page.items:
            try:
                item = ValidatedAnimal.model_validate(raw)
                # JSONB rejects NUL and non-finite numbers, including unknown extra fields.
                snapshot = item.model_dump(exclude_unset=True)
                validate_json_text(snapshot)
                encoded = json.dumps(
                    snapshot,
                    ensure_ascii=True,
                    sort_keys=True,
                    allow_nan=False,
                )
                animal = normalize_animal(item, today=today)
            except (ValidationError, ValueError):
                rejected += 1
                continue
            key = animal.values["source_id"]
            digest = hashlib.sha256(encoded.encode()).digest()
            if key in seen:
                if seen[key] != digest:
                    raise ApiFailure("CONFLICTING_SOURCE_ID")
                report.duplicate_count += 1
                continue
            seen[key] = digest
            normalized.append(animal)
            issues.update(animal.issues)
        report.rejected_count += rejected
        report.error_count += rejected
        report.normalized_count += len(normalized)
        report.normalization_issues = dict(Counter(report.normalization_issues) + issues)
        if page.items and rejected / len(page.items) > 0.1:
            raise ApiFailure("SOURCE_VALIDATION_CATASTROPHIC")
        for field_name, issue in (("weight", "weight_unparsed"), ("age", "age_unparsed")):
            candidates = sum(meaningful(row.get(field_name)) for row in page.items)
            if candidates >= 20 and issues[issue] / candidates > 0.5:
                raise ApiFailure("PARSING_CATASTROPHIC")
    return normalized, rejected


def write_batch(connection, repository, report, animals, *, today, clock, sleeper):
    for attempt in range(3):
        try:
            with timed(report, "database_seconds"), connection.begin():
                return repository.upsert_batch(report.sync_id, animals, now=clock(), today=today)
        except SQLAlchemyError as exc:
            sqlstate = getattr(getattr(exc, "orig", None), "sqlstate", None)
            # Only retry transactions the server has definitely aborted.
            if sqlstate not in {"40001", "40P01"} or attempt == 2:
                raise
            report.database_retries += 1
            sleeper(0.5 * (2**attempt))
    raise AssertionError("unreachable")


def sync(
    engine,
    client,
    *,
    batch_size=500,
    page_size=1000,
    max_pages=10000,
    max_animals=None,
    filters=None,
    clock=lambda: datetime.now(UTC),
    sleeper=time.sleep,
) -> SyncReport:
    if (
        not 500 <= batch_size <= 1000
        or not 1 <= page_size <= 1000
        or max_pages < 1
        or max_animals is not None
        and max_animals < 1
    ):
        raise ValueError("Invalid sync bounds")
    report = SyncReport(batch_size=batch_size)
    started = time.perf_counter()
    now = clock()
    if now.tzinfo is None:
        raise ValueError("An aware UTC clock is required")
    today = korea_today(now)
    connection = None
    locked = False
    try:
        with timed(report, "database_seconds"):
            connection = engine.connect()
            repository = SyncRepository(connection)
            with connection.begin():
                repository.start_run(report.sync_id, now)
            report.run_persisted = True
            with connection.begin():
                locked = connection.scalar(
                    text("SELECT pg_try_advisory_lock(:namespace, :source)"),
                    {"namespace": LOCK_NAMESPACE, "source": LOCK_SOURCE},
                )
            if not locked:
                raise ApiFailure("SYNC_ALREADY_RUNNING")
        seen = {}
        for page in iter_pages(
            client,
            report.pagination,
            page_size=page_size,
            max_pages=max_pages,
            max_animals=max_animals,
            filters=filters,
        ):
            page_started = time.perf_counter()
            normalized, rejected = prepare_page(page, seen, report, today=today)
            page_inserted = page_updated = 0
            for batch in chunks(normalized, batch_size):
                counts = write_batch(
                    connection, repository, report, batch, today=today, clock=clock, sleeper=sleeper
                )
                report.inserted_count += counts.inserted
                report.updated_count += counts.updated
                report.unchanged_count += counts.unchanged
                report.stale_count += counts.stale
                report.excluded_count += counts.excluded
                report.deleted_count += counts.deleted
                page_inserted += counts.inserted
                page_updated += counts.updated
                emit(
                    report,
                    page=page.number,
                    received=len(batch),
                    normalized=len(batch),
                    inserted=counts.inserted,
                    updated=counts.updated,
                    event="batch_committed",
                    duration=time.perf_counter() - page_started,
                )
            with timed(report, "database_seconds"), connection.begin():
                repository.progress(
                    report.sync_id,
                    page_count=report.pagination.page_count,
                    received_count=report.pagination.fetched_count,
                    error_count=report.error_count,
                )
            emit(
                report,
                page=page.number,
                received=len(page.items),
                normalized=len(normalized),
                rejected=rejected,
                inserted=page_inserted,
                updated=page_updated,
                duration=time.perf_counter() - page_started,
            )
        report.status = "failed" if report.rejected_count else "success"
        if report.rejected_count:
            report.error_code = "ROWS_REJECTED"
    except (Exception, KeyboardInterrupt) as exc:
        # No exception repr, traceback, input row, SQL, or authenticated URL in sync logs.
        report.error_code = (
            exc.kind.split(":", 1)[0]
            if isinstance(exc, ApiFailure)
            else "DATABASE_ERROR"
            if isinstance(exc, SQLAlchemyError)
            else "INTERRUPTED"
            if isinstance(exc, KeyboardInterrupt)
            else "INTERNAL_SYNC_ERROR"
        )
        report.status = "failed"
        report.error_count += 1
        if (
            report.pagination.page_no
            and report.pagination.page_no not in report.pagination.failed_pages
        ):
            report.pagination.failed_pages.append(report.pagination.page_no)
        emit(report, page=report.pagination.page_no, rejected=report.rejected_count, event="failed")
    finally:
        if report.run_persisted:
            try:
                # A fresh connection also handles a lost/invalidated data connection.
                with timed(report, "database_seconds"), engine.begin() as final_connection:
                    final = SyncRepository(final_connection)
                    final.progress(
                        report.sync_id,
                        page_count=report.pagination.page_count,
                        received_count=report.pagination.fetched_count,
                        error_count=report.error_count,
                    )
                    final.finish_run(
                        report.sync_id,
                        status=report.status,
                        now=clock(),
                        error_message=json.dumps(
                            {
                                "code": report.error_code,
                                "rejected": report.rejected_count,
                                "failed_pages": report.pagination.failed_pages[:20],
                                "partial_batches_committed": bool(
                                    report.inserted_count
                                    + report.updated_count
                                    + report.unchanged_count
                                    + report.stale_count
                                ),
                            }
                        )
                        if report.error_code
                        else None,
                    )
                    report.inserted_count, report.updated_count = final.counts(report.sync_id)
            except SQLAlchemyError:
                report.status = "failed"
                report.error_code = "RUN_FINALIZATION_FAILED"
                report.error_count += 1
        if connection is not None:
            try:
                if connection.in_transaction():
                    connection.rollback()
                if locked and not connection.invalidated:
                    with connection.begin():
                        connection.execute(
                            text("SELECT pg_advisory_unlock(:namespace, :source)"),
                            {"namespace": LOCK_NAMESPACE, "source": LOCK_SOURCE},
                        )
            except SQLAlchemyError:
                connection.invalidate()
            finally:
                connection.close()
        report.api_attempts = getattr(client, "attempts", 0)
        report.api_retries = getattr(client, "retries", 0)
        report.total_seconds = time.perf_counter() - started
    return report
