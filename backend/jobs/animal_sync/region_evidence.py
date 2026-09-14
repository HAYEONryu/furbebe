"""Resolve ambiguous official names using scoped source animal IDs, never fuzzy aliases."""

import json
import math
from collections import defaultdict

from .client import ApiFailure
from .field_stats import identifier, text
from .source_models import normalize_items, source_integer


def scoped_memberships(cache, provinces, districts, unresolved, source_filters):
    source_filters = {
        key: source_filters[key] for key in ("bgnde", "endde") if key in source_filters
    }
    candidates = set()
    for province in provinces:
        parent, province_name = province["orgCd"], province.get("orgdownNm", "")
        for child in districts.get(parent, []):
            name = child.get("orgdownNm", "")
            full = province_name + " " + name
            if name and any(org == full or org.startswith(full + " ") for org in unresolved):
                candidates.add((parent, child["orgCd"]))
    directory = cache.directory / "organization-evidence"
    memberships = defaultdict(set)
    used = []
    for parent, code in sorted(candidates):
        filters = {"upr_cd": parent, "org_cd": code, **source_filters}
        if not {"bgnde", "endde"} <= filters.keys():
            continue
        # Code-keyed capture with exact filter verification: mismatches are never reused.
        path = directory / f"{code}.json"
        saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        if saved is not None and saved.get("filters") != filters:
            path = directory / f"{code}-{cache.digest(filters)[:12]}.json"
            saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        if saved is None and cache.client is not None:
            page = cache.client.fetch(1, 1000, filters=filters)
            cache.stats["organization_evidence_network_pages"] += 1
            total = page.total
            pages = [page.envelope]
            for number in range(2, math.ceil(total / 1000) + 1):
                page = cache.client.fetch(number, 1000, filters=filters)
                cache.stats["organization_evidence_network_pages"] += 1
                pages.append(page.envelope)
            saved = {"filters": filters, "envelopes": pages}
            directory.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
        if saved is None:
            continue
        if saved.get("filters") != filters:
            raise ApiFailure("ORGANIZATION_EVIDENCE_SCOPE_MISMATCH")
        envelopes = saved.get("envelopes") or [saved["envelope"]]
        total = None
        row_count = 0
        for expected_page, payload in enumerate(envelopes, 1):
            envelope = payload["response"]
            if str(envelope["header"].get("resultCode")) != "00":
                raise ApiFailure("ORGANIZATION_EVIDENCE_NOT_SUCCESS")
            body = envelope["body"]
            if source_integer(body["pageNo"], "pageNo") != expected_page:
                raise ApiFailure("ORGANIZATION_EVIDENCE_PAGE_MISMATCH")
            items, _ = normalize_items(body)
            page_total = source_integer(body["totalCount"], "totalCount")
            if total is not None and page_total != total:
                raise ApiFailure("ORGANIZATION_EVIDENCE_TOTAL_CHANGED")
            total = page_total
            row_count += len(items)
            for item in items:
                key = identifier(item.root)
                if key:
                    memberships[(key, " ".join(text(item.root.get("orgNm")).split()))].add(
                        (parent, code)
                    )
        if total is None or row_count > total or row_count < total and len(envelopes) == 1:
            raise ApiFailure("ORGANIZATION_EVIDENCE_COUNT_MISMATCH")
        used.append(
            {
                "upr_cd": parent,
                "org_cd": code,
                "totalCount": total,
                "rows": row_count,
                "capture_sha256": cache.digest(saved),
            }
        )
    return memberships, used
