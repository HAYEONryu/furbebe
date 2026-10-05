"""User-approved display policy; source state is never rewritten."""

import re
from collections import Counter
from datetime import date

from backend.app.core.clock import KST as KST
from backend.app.core.clock import korea_today as korea_today

from .field_stats import parse_date

POLICY_VERSION = "notice-start-10-calendar-days-v1"


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


def is_listed_dog(values, *, today: date):
    """Keep dogs in either selectable state; ended posts stay outside public results."""
    return values.get("species") == "dog" and values.get("process_state") in {
        "보호중", "입양 가능"
    }


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
