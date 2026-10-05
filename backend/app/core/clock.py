"""Shared calendar clock without collection-job dependencies."""

from datetime import UTC, date, datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))


def korea_today(now: datetime | None = None) -> date:
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("An aware clock is required")
    return now.astimezone(KST).date()
