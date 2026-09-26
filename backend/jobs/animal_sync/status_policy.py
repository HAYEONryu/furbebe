"""User-approved display policy; source state is never rewritten."""

import re
from collections import Counter
from datetime import UTC, date, datetime, timedelta, timezone

from .field_stats import parse_date

KST = timezone(timedelta(hours=9))
POLICY_VERSION = "notice-start-10-calendar-days-v1"


def korea_today(now: datetime | None = None) -> date:
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("An aware clock is required")
    return now.astimezone(KST).date()


def display_status(row, *, today: date):
    raw = row.get("processState")
    result = {"source_state": raw, "display_state": raw, "elapsed_days": None, "issue": None}
    if raw != "보호중":
        return result
    notice = row.get("noticeSdt")
    parsed = (
        parse_date(notice) if isinstance(notice, str) and re.fullmatch(r"\d{8}", notice) else None
    )
    if parsed is None:
        result["issue"] = "invalid_or_missing_notice_start"
        return result
    days = (today - parsed.date()).days
    result["elapsed_days"] = days
    if days < 0:
        result["issue"] = "future_notice_start"
    elif days >= 10:
        result["display_state"] = "입양 가능"
    return result


def profile_status(rows, *, today: date):
    states, issues = Counter(), Counter()
    for row in rows:
        result = display_status(row, today=today)
        states[str(result["display_state"])] += 1
        if result["issue"]:
            issues[result["issue"]] += 1
    return {
        "policy_version": POLICY_VERSION,
        "as_of_date": today.isoformat(),
        "timezone": "Asia/Seoul (UTC+09:00)",
        "rule": "source processState=보호중 and today-noticeSdt >= 10 calendar days → 입양 가능",
        "display_state_frequencies": dict(states),
        "issues": dict(issues),
        "note": "User-defined display label, not a new upstream state or shelter confirmation. "
        "noticeEdt and happenDt do not replace noticeSdt. Source payload unchanged. "
        "animals_active remains a separate launch decision.",
    }
