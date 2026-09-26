"""Shared source parsers. Profiling re-exports these functions for compatibility."""

import math
import re
from datetime import datetime
from decimal import Decimal
from typing import Any
from urllib.parse import urlsplit

IMAGE_FIELDS = [f"popfile{i}" for i in range(1, 9)]
PLACEHOLDERS = {".", "-", "없음", "미상", "unknown", "null", "n/a"}


def text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def meaningful(value: Any) -> bool:
    return (
        isinstance(value, str) and bool(value.strip()) and value.strip().lower() not in PLACEHOLDERS
    )


def identifier(row: dict) -> str | None:
    value = row.get("desertionNo")
    # Source number types are retained raw but never accepted as a lossless string ID.
    return text(value) if isinstance(value, str) and meaningful(value) else None


def parse_weight_decimal(value: Any) -> Decimal | None:
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"\s*([+-]?\d+(?:\.\d+)?)\s*\(\s*kg\s*\)\s*", value, re.I)
    if not match:
        return None
    number = Decimal(match[1])
    return number if number.is_finite() else None


def parse_weight(value: Any) -> float | None:
    parsed = parse_weight_decimal(value)
    number = float(parsed) if parsed is not None else None
    return number if number is not None and math.isfinite(number) else None


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
