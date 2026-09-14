"""Non-destructive parsing and complete source field dictionary statistics."""

import json
import math
import re
from collections import Counter
from datetime import date, datetime
from statistics import mean, median
from typing import Any
from urllib.parse import urlsplit

CATEGORIES = {
    "identifier": "desertionNo noticeNo rfidCd updTm",
    "discovery": "happenDt happenPlace",
    "animal": "kindCd kindFullNm upKindCd upKindNm kindNm colorCd age weight sexCd neuterYn",
    "notice": "noticeSdt noticeEdt processState endReason",
    "description_health": "specialMark sfeSoci sfeHealth etcBigo vaccinationChk healthChk",
    "shelter": "careRegNo careNm careTel careAddr careOwnerNm orgNm",
    "images": " ".join(f"popfile{i}" for i in range(1, 9)),
    **{
        name: " ".join(
            prefix + suffix
            for suffix in ("Title", "SDate", "EDate", "ConditionLimitTxt", "Txt", "Img")
        )
        for name, prefix in (
            ("adoption", "adptn"),
            ("support", "sprt"),
            ("service", "srvc"),
            ("event", "evnt"),
        )
    },
}
FIELDS = {field: category for category, names in CATEGORIES.items() for field in names.split()}
DATE_FIELDS = ["happenDt", "noticeSdt", "noticeEdt", "updTm"] + [
    p + s for p in ("adptn", "sprt", "srvc", "evnt") for s in ("SDate", "EDate")
]
IMAGE_FIELDS = [f"popfile{i}" for i in range(1, 9)]
ALL_IMAGE_FIELDS = IMAGE_FIELDS + [p + "Img" for p in ("adptn", "sprt", "srvc", "evnt")]
TEXT_FIELDS = ["specialMark", "sfeSoci", "sfeHealth", "etcBigo", "adptnTxt"]
PLACEHOLDERS = {".", "-", "없음", "미상", "unknown", "null", "n/a"}
SAFE_SAMPLE_FIELDS = {
    "age",
    "weight",
    "upKindNm",
    "sexCd",
    "neuterYn",
    "processState",
    "kindNm",
    "kindFullNm",
    "colorCd",
    *DATE_FIELDS,
}


def ratio(n: int, total: int) -> float | None:
    return round(n / total, 6) if total else None


def text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def meaningful(value: Any) -> bool:
    return (
        isinstance(value, str) and bool(value.strip()) and value.strip().lower() not in PLACEHOLDERS
    )


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def identifier(row: dict) -> str | None:
    value = row.get("desertionNo")
    # Source number types are retained raw but never accepted as a lossless string ID.
    return text(value) if isinstance(value, str) and meaningful(value) else None


def parse_weight(value: Any) -> float | None:
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"\s*([+-]?\d+(?:\.\d+)?)\s*\(\s*kg\s*\)\s*", value, re.I)
    if not match:
        return None
    number = float(match[1])
    return number if math.isfinite(number) else None


def parse_age(value: Any) -> int | None:
    # Observed in 4,751 unique dogs on 2026-09-14. Retain the annotation in raw age_text.
    match = (
        re.fullmatch(r"\s*(\d{4})\s*(?:\(60일미만\))?\(년생\)\s*", value)
        if isinstance(value, str)
        else None
    )
    return int(match[1]) if match else None


def parse_date(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    try:
        if re.fullmatch(r"\d{8}", value):
            return datetime.strptime(value, "%Y%m%d")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return datetime.fromisoformat(value)
        if re.fullmatch(
            r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?"
            r"(?:Z|[+-]\d{2}:\d{2})?",
            value,
        ):
            return datetime.fromisoformat(value)
    except ValueError:
        return None
    return None


def date_format(value: Any) -> str:
    if not isinstance(value, str):
        return type(value).__name__
    if re.fullmatch(r"\d{8}", value.strip()):
        return "YYYYMMDD"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value.strip()):
        return "YYYY-MM-DD"
    parsed = parse_date(value)
    if parsed:
        return "timestamp_offset" if parsed.tzinfo else "timestamp_naive"
    return "unrecognized_or_invalid"


def valid_url(value: Any) -> bool:
    if not isinstance(value, str) or re.search(r"\s", value):
        return False
    try:
        url = urlsplit(value)
        return (
            url.scheme in {"http", "https"}
            and bool(url.hostname)
            and url.username is None
            and url.password is None
        )
    except ValueError:
        return False


def animal_images(row: dict) -> list[str]:
    return list(dict.fromkeys(row[f] for f in IMAGE_FIELDS if valid_url(row.get(f))))


def distribution(values: list[float | int]) -> dict:
    if not values:
        return {
            "count": 0,
            "min": None,
            "p25": None,
            "median": None,
            "p75": None,
            "p95": None,
            "max": None,
            "mean": None,
        }
    ordered = sorted(values)

    def percentile(p):
        index = (len(ordered) - 1) * p
        lower = int(index)
        fraction = index - lower
        return (
            ordered[lower] + (ordered[min(lower + 1, len(ordered) - 1)] - ordered[lower]) * fraction
        )

    return {
        "count": len(values),
        "min": min(values),
        "p25": percentile(0.25),
        "median": median(values),
        "p75": percentile(0.75),
        "p95": percentile(0.95),
        "max": max(values),
        "mean": mean(values),
    }


def profile_fields(rows: list[dict], redactor) -> list[dict]:
    names = sorted(set(FIELDS) | {key for row in rows for key in row})
    output = []
    for field in names:
        values = [row[field] for row in rows if field in row]
        nonempty = [v for v in values if v is not None and (not isinstance(v, str) or v.strip())]
        candidates = [
            v for v in nonempty if not isinstance(v, str) or v.strip().lower() not in PLACEHOLDERS
        ]
        types = Counter(type(v).__name__ for v in values)
        parser = (
            parse_date
            if field in DATE_FIELDS
            else parse_weight
            if field == "weight"
            else parse_age
            if field == "age"
            else valid_url
            if field in ALL_IMAGE_FIELDS
            else None
        )
        parsed = (
            sum(parser(v) is not None if parser != valid_url else parser(v) for v in candidates)
            if parser
            else None
        )
        samples = list(dict.fromkeys(redactor.text(v, personal=True)[:120] for v in candidates))[:3]
        if field not in SAFE_SAMPLE_FIELDS:
            samples = ["[values withheld; raw is local only]"] if candidates else []
        output.append(
            {
                "field": field,
                "category": FIELDS.get(field, "additional_observed"),
                "observed_type": dict(types),
                "presence_count": len(values),
                "presence_ratio": ratio(len(values), len(rows)),
                "missing_count": len(rows) - len(values),
                "null_count": sum(v is None for v in values),
                "blank_count": sum(isinstance(v, str) and not v.strip() for v in values),
                "placeholder_count": sum(
                    isinstance(v, str) and v.strip().lower() in PLACEHOLDERS for v in nonempty
                ),
                "distinct_count": len({canonical(v) for v in values}),
                "sample_values": samples,
                "max_length": max((len(v) for v in values if isinstance(v, str)), default=None),
                "parseable_ratio": ratio(parsed, len(candidates)) if parser else None,
                "parseable_count": parsed,
                "parseable_denominator": len(candidates) if parser else None,
                "notes": "Raw rows; absent/null/blank/placeholder are separate. Parse denominator excludes "
                "these states. '없음' is a placeholder candidate, not proof of missing health facts.",
            }
        )
    return output


def profile_dates(rows: list[dict], today: date) -> dict:
    result = {}
    for field in DATE_FIELDS:
        raw = [
            row[field]
            for row in rows
            if field in row
            and row[field] is not None
            and (not isinstance(row[field], str) or meaningful(row[field]))
        ]
        parsed = [p for value in raw if (p := parse_date(value)) is not None]
        result[field] = {
            "nonplaceholder_count": len(raw),
            "parse_success": len(parsed),
            "parse_failure": len(raw) - len(parsed),
            "parse_success_ratio": ratio(len(parsed), len(raw)),
            "invalid_calendar_dates": sum(
                isinstance(v, str)
                and bool(re.match(r"^\d{8}$|^\d{4}-\d{2}-\d{2}", v))
                and parse_date(v) is None
                for v in raw
            ),
            "formats": dict(Counter(date_format(v) for v in raw)),
            "minimum": min((p.date().isoformat() for p in parsed), default=None),
            "maximum": max((p.date().isoformat() for p in parsed), default=None),
            "future_dates": sum(p.date() > today for p in parsed),
            "naive_timestamps": sum(
                p.tzinfo is None and date_format(v) == "timestamp_naive"
                for v in raw
                if (p := parse_date(v)) is not None
            ),
        }
    checks = [("noticeSdt", "noticeEdt"), ("happenDt", "noticeEdt")] + [
        (p + "SDate", p + "EDate") for p in ("adptn", "sprt", "srvc", "evnt")
    ]
    result["consistency"] = {}
    for start, end in checks:
        pairs = [
            (a, b)
            for row in rows
            if (a := parse_date(row.get(start))) is not None
            and (b := parse_date(row.get(end))) is not None
        ]
        result["consistency"][start + "<=" + end] = {
            "comparable": len(pairs),
            "violations": sum(a.date() > b.date() for a, b in pairs),
        }
    return result
