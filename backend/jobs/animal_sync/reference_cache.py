"""Persistent official lookup catalogs, scoped by parent codes, with bounded misses."""

import hashlib
import json
import time
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .client import REFERENCE_ENDPOINTS, ApiFailure
from .field_stats import canonical

ID_FIELDS = {"sido": "orgCd", "sigungu": "orgCd", "kind": "kindCd", "shelter": "careRegNo"}


class ReferenceCache:
    def __init__(self, directory: Path, client=None, *, clock=None):
        self.directory = directory
        self.path = directory / "cache.json"
        self.client = client
        self.clock = clock or (lambda: datetime.now(UTC))
        self.queried = set()
        self.stats = Counter()
        self.data = {"version": 1, "catalogs": {}}
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if data["version"] != 1 or not isinstance(data["catalogs"], dict):
                    raise ValueError
                for entry in data["catalogs"].values():
                    if entry["complete"] is not True or not isinstance(entry["items"], list):
                        raise ValueError
                    if entry["items_sha256"] != self.digest(entry["items"]):
                        raise ValueError
                self.data = data
            except (ValueError, KeyError, TypeError):
                raise ApiFailure("REFERENCE_CACHE_INVALID") from None

    @staticmethod
    def digest(value):
        return hashlib.sha256(canonical(value).encode()).hexdigest()

    @staticmethod
    def scope(resource, filters):
        if resource not in REFERENCE_ENDPOINTS:
            raise ApiFailure("UNKNOWN_REFERENCE_RESOURCE")
        return canonical([resource, sorted(filters.items())])

    def save(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        pending = self.path.with_suffix(".tmp")
        pending.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        for attempt in range(3):
            try:
                pending.replace(self.path)
                return
            except PermissionError:
                if attempt == 2:
                    raise ApiFailure("REFERENCE_CACHE_REPLACE_DENIED") from None
                time.sleep(0.1 * (attempt + 1))

    def ensure(self, resource, filters=None, *, expected=(), match_field=None):
        filters = filters or {}
        scope = self.scope(resource, filters)
        entry = self.data["catalogs"].get(scope)
        field = match_field or ID_FIELDS[resource]
        expected = {str(value) for value in expected}
        now = self.clock()
        missing = expected - {str(row.get(field)) for row in entry["items"]} if entry else expected
        recent_misses = entry.get("missing_checks", {}) if entry else {}
        unchecked = {
            value
            for value in missing
            if field + ":" + value not in recent_misses
            or now - datetime.fromisoformat(recent_misses[field + ":" + value]) >= timedelta(days=1)
        }
        needs_fetch = entry is None or bool(unchecked and scope not in self.queried)
        if needs_fetch and self.client is not None:
            items, pages, total = self.fetch_all(resource, filters)
            entry = {
                "resource": resource,
                "endpoint": REFERENCE_ENDPOINTS[resource],
                "filters": filters,
                "complete": True,
                "fetched_at": now.isoformat(),
                "pages": pages,
                "totalCount": total,
                "duplicate_rows": total - len(items),
                "items": items,
                "items_sha256": self.digest(items),
                "missing_checks": dict(recent_misses),
            }
            self.data["catalogs"][scope] = entry
            self.queried.add(scope)
            self.stats["catalog_fetches"] += 1
        elif needs_fetch:
            self.stats["offline_missing_catalog_or_code"] += 1
            if entry is None:
                self.stats["offline_missing_catalogs"] += 1
        else:
            self.stats["cache_hits"] += 1
        if entry is None:
            return []
        if self.client is not None and scope in self.queried:
            for value in expected - {str(row.get(field)) for row in entry["items"]}:
                entry["missing_checks"][field + ":" + value] = now.isoformat()
            self.save()
        return entry["items"]

    def fetch_all(self, resource, filters):
        rows, seen, total = [], {}, None
        raw_count, fingerprints = 0, set()
        for number in range(1, 101):
            page = self.client.fetch_reference(resource, number, 1000, filters=filters)
            self.stats["network_pages"] += 1
            # Preserve the full envelope only in the ignored profiling tree.
            captures = self.directory / "responses"
            captures.mkdir(parents=True, exist_ok=True)
            stamp = self.clock().strftime("%Y%m%dT%H%M%S%fZ")
            suffix = self.digest([resource, filters, number])[:12]
            capture = captures / f"{stamp}-{resource}-{suffix}.json"
            capture.write_text(json.dumps(page.envelope, ensure_ascii=False), encoding="utf-8")
            if total is not None and total != page.total:
                raise ApiFailure("REFERENCE_TOTAL_CHANGED")
            total = page.total
            fingerprint = self.digest(page.items)
            if page.items and fingerprint in fingerprints:
                raise ApiFailure("REFERENCE_REPEATED_PAGE")
            fingerprints.add(fingerprint)
            raw_count += len(page.items)
            for row in page.items:
                value = row.get(ID_FIELDS[resource])
                if not isinstance(value, str) or not value:
                    raise ApiFailure("REFERENCE_CODE_MISSING")
                if value in seen:
                    if seen[value] != canonical(row):
                        raise ApiFailure("REFERENCE_CODE_CONFLICT")
                    continue
                if resource == "sigungu":
                    parent = row.get("uprCd")
                    # Observed province self-row omits uprCd; do not invent a district.
                    province_self = parent is None and value == filters["upr_cd"]
                    if parent != filters["upr_cd"] and not province_self:
                        raise ApiFailure("REFERENCE_PARENT_MISMATCH")
                seen[value] = canonical(row)
                rows.append(row)
            if raw_count == total:
                return rows, number, total
            if raw_count > total or not page.items:
                raise ApiFailure("REFERENCE_PAGINATION_INCOMPLETE")
        raise ApiFailure("REFERENCE_PAGE_LIMIT")
