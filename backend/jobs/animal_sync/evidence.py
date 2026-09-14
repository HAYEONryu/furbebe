"""Profiling heuristics only. No production personality or diagnosis assignments."""

import csv
import random
import re
from collections import Counter
from statistics import median

from .client import ApiFailure
from .field_stats import TEXT_FIELDS, distribution, meaningful, ratio, text

BEHAVIOR = re.compile(
    r"사람.{0,5}좋아|잘\s*따[름르]|따라다[님니]|애교|친화|순[함하한]|얌전|차분|"
    r"활발|산책|경계|낯가림|무서워|겁이|예민"
)
HEALTH = re.compile(r"절단|골절|상처|피부|심장사상충|접종|중성화|질병|치료|절음")
ADMIN = re.compile(r"119|인계|마을에서\s*발견|포획|구조")
NEGATION = re.compile(r"없[음다어]|않[음다아]|아님|못함|미접종|불명")


def classify(value) -> dict:
    raw = text(value)
    behavior, health, administrative = (bool(p.search(raw)) for p in (BEHAVIOR, HEALTH, ADMIN))
    short = bool(raw) and len(raw) <= 2
    empty = not raw
    placeholder = bool(raw) and (not meaningful(raw) or not re.search(r"[가-힣A-Za-z0-9]", raw))
    categories = [
        name
        for name, found in (
            ("BEHAVIOR_RELATED", behavior),
            ("HEALTH_RELATED", health),
            ("ADMINISTRATIVE", administrative),
        )
        if found
    ]
    category = (
        "EMPTY"
        if empty
        else "PLACEHOLDER"
        if placeholder
        else "MIXED"
        if len(categories) > 1
        else categories[0]
        if categories
        else "PLACEHOLDER"
        if short
        else "DESCRIPTIVE"
    )
    return {
        "class": category,
        "behavior": behavior,
        "health": health,
        "administrative": administrative,
        "negation_marker": bool(NEGATION.search(raw)),
        "short_text_candidate": short,
        "meaningful": not empty and not placeholder and (not short or bool(categories)),
    }


def profile_evidence(rows: list[dict]) -> dict:
    by_field = {}
    for field in TEXT_FIELDS:
        classifications = [classify(row.get(field)) for row in rows]
        lengths = [len(text(row.get(field))) for row in rows if text(row.get(field))]
        by_field[field] = {
            "presence_ratio": ratio(sum(field in row for row in rows), len(rows)),
            "meaningful_ratio": ratio(sum(v["meaningful"] for v in classifications), len(rows)),
            "placeholder_ratio": ratio(
                sum(v["class"] == "PLACEHOLDER" for v in classifications), len(rows)
            ),
            "median_length_nonblank": median(lengths) if lengths else None,
            "p95_length_nonblank": distribution(lengths)["p95"],
            "classes": dict(Counter(v["class"] for v in classifications)),
            "behavior_candidates": sum(v["behavior"] for v in classifications),
            "health_candidates": sum(v["health"] for v in classifications),
            "administrative_candidates": sum(v["administrative"] for v in classifications),
            "short_text_candidates": sum(v["short_text_candidate"] for v in classifications),
            "negation_markers": sum(v["negation_marker"] for v in classifications),
        }
    counters = Counter()
    for row in rows:
        evidence = {f: classify(row.get(f)) for f in TEXT_FIELDS}
        behavior_fields = [f for f, v in evidence.items() if v["behavior"]]
        health = any(v["health"] for v in evidence.values())
        admin = any(v["administrative"] for v in evidence.values())
        counters["any_behavior"] += bool(behavior_fields)
        counters["any_health"] += health
        counters["any_administrative"] += admin
        counters["behavior_and_health"] += bool(behavior_fields) and health
        counters["administrative_only"] += admin and not behavior_fields and not health
        counters["only_specialMark_behavior"] += behavior_fields == ["specialMark"]
        counters["sfeSoci_behavior"] += "sfeSoci" in behavior_fields
        counters["adoption_description_behavior"] += "adptnTxt" in behavior_fields
    return {
        "denominator": len(rows),
        "by_field": by_field,
        "counts": dict(counters),
        "ratios": {name: ratio(count, len(rows)) for name, count in counters.items()},
        "health_structured_coverage": {
            f: ratio(sum(meaningful(r.get(f)) for r in rows), len(rows))
            for f in ("vaccinationChk", "healthChk", "sfeHealth")
        },
        "notes": "Multi-label keyword candidates, not tags or diagnoses. Short text and keyword "
        "flags overlap (e.g. 순함, 경계). Negation requires human review.",
    }


def review_sample(rows: list[dict], seed: int) -> tuple[list[dict], dict]:
    rng = random.Random(seed)
    ordered = sorted(rows, key=lambda r: r["desertionNo"])
    categories = {
        "behavior": [
            r for r in ordered if any(classify(r.get(f))["behavior"] for f in TEXT_FIELDS)
        ],
        "health": [r for r in ordered if any(classify(r.get(f))["health"] for f in TEXT_FIELDS)],
        "administrative_or_meaningless": [
            r
            for r in ordered
            if classify(r.get("specialMark"))["class"] in {"EMPTY", "PLACEHOLDER", "ADMINISTRATIVE"}
        ],
        "random": ordered[:],
    }
    selected, seen, actual = [], set(), {}
    for group, pool in categories.items():
        candidates = [r for r in pool if r["desertionNo"] not in seen]
        rng.shuffle(candidates)
        chosen = candidates[:25]
        actual[group] = len(chosen)
        for row in chosen:
            selected.append({"row": row, "stratum": group})
            seen.add(row["desertionNo"])
    remaining = [r for r in ordered if r["desertionNo"] not in seen]
    rng.shuffle(remaining)
    filler = remaining[: max(0, min(100, len(ordered)) - len(selected))]
    selected.extend({"row": r, "stratum": "backfill_random"} for r in filler)
    return selected, {
        "seed": seed,
        "requested": 100,
        "actual": len(selected),
        "strata": actual,
        "backfilled": len(filler),
        "review_status": "pending_human_review",
        "notes": "Disjoint strata in declared order; shortages backfilled at random.",
    }


def export_review(path, selected, redactor):
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as existing:
            if any((row.get("review_notes") or "").strip() for row in csv.DictReader(existing)):
                raise ApiFailure(
                    "MANUAL_REVIEW_NOTES_EXIST: preserve the reviewed CSV before replay"
                )
    fields = [
        "desertionNo",
        "specialMark",
        "sfeSoci",
        "sfeHealth",
        "etcBigo",
        "auto_text_class",
        "behavior_candidate",
        "health_candidate",
        "stratum",
        "review_notes",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        for entry in selected:
            row = entry["row"]
            combined = " ".join(text(row.get(f)) for f in TEXT_FIELDS)
            evidence = classify(combined)
            export = {f: redactor.text(row.get(f, ""), personal=True) for f in fields[:5]}
            export.update(
                auto_text_class=evidence["class"],
                behavior_candidate=evidence["behavior"],
                health_candidate=evidence["health"],
                stratum=entry["stratum"],
                review_notes="",
            )
            # Protect spreadsheet readers from formula execution.
            writer.writerow(
                {
                    k: "'" + v
                    if isinstance(v, str) and bool(v.strip()) and v.lstrip()[:1] in "=+-@"
                    else v
                    for k, v in export.items()
                }
            )
