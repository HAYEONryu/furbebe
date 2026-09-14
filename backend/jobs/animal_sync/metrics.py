"""Aggregate quality diagnostics; keep source facts separate from project gates."""

import re
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from urllib.parse import urlsplit

from .evidence import profile_evidence, review_sample
from .field_stats import (
    ALL_IMAGE_FIELDS,
    IMAGE_FIELDS,
    animal_images,
    canonical,
    distribution,
    identifier,
    meaningful,
    parse_age,
    parse_date,
    parse_weight,
    profile_dates,
    profile_fields,
    ratio,
    text,
)
from .observations import profile_observations
from .status_policy import profile_status

CONFLICT_FIELDS = ["noticeNo", "processState", "careRegNo", "updTm", "popfile1", "specialMark"]
ENUM_FIELDS = ["upKindNm", "sexCd", "neuterYn", "processState", "kindNm", "colorCd"]


def identity_profile(rows: list[dict]) -> tuple[list[dict], dict]:
    by_id = defaultdict(list)
    for row in rows:
        if (key := identifier(row)) is not None:
            by_id[key].append(row)
    conflict_fields = Counter()
    identical, conflicting, conflict_groups = 0, 0, 0
    for group in by_id.values():
        versions = Counter(canonical(row) for row in group)
        identical += sum(n - 1 for n in versions.values())
        conflicting += max(0, len(versions) - 1)
        conflict_groups += len(versions) > 1
        for field in CONFLICT_FIELDS:
            if len({canonical([field in r, r.get(field)]) for r in group}) > 1:
                conflict_fields[field] += 1
    unavailable = sum(identifier(r) is None for r in rows)
    result = {
        "raw_item_count": len(rows),
        "unique_desertion_no_count": len(by_id),
        "unusable_id_count": unavailable,
        "unusable_id_ratio": ratio(unavailable, len(rows)),
        "missing_count": sum("desertionNo" not in r for r in rows),
        "null_count": sum("desertionNo" in r and r["desertionNo"] is None for r in rows),
        "blank_count": sum(
            isinstance(r.get("desertionNo"), str) and not r["desertionNo"].strip() for r in rows
        ),
        "non_string_count": sum(
            r.get("desertionNo") is not None and not isinstance(r["desertionNo"], str) for r in rows
        ),
        "duplicate_item_count": sum(len(g) - 1 for g in by_id.values()),
        "duplicate_ratio_raw": ratio(sum(len(g) - 1 for g in by_id.values()), len(rows)),
        "identical_duplicate_item_count": identical,
        "conflicting_additional_versions": conflicting,
        "conflicting_id_count": conflict_groups,
        "conflicting_id_ratio_unique": ratio(conflict_groups, len(by_id)),
        "conflict_fields": dict(conflict_fields),
        "content_sampling_policy": "First observed payload per usable string ID for descriptive "
        "statistics only; no authoritative UPSERT winner selected. "
        "Every version is retained in the local raw capture.",
    }
    return [by_id[key][0] for key in sorted(by_id)], result


def number_profile(rows, field, parser, redactor):
    raw = [
        r[field]
        for r in rows
        if field in r
        and r[field] is not None
        and (not isinstance(r[field], str) or meaningful(r[field]))
    ]
    valid = [v for s in raw if (v := parser(s)) is not None]
    invalid = Counter(redactor.text(s, personal=True)[:100] for s in raw if parser(s) is None)
    return {
        "denominator_nonplaceholder": len(raw),
        "parse_success": len(valid),
        "parse_failure": len(raw) - len(valid),
        "parse_success_ratio": ratio(len(valid), len(raw)),
        "parse_failure_ratio": ratio(len(raw) - len(valid), len(raw)),
        "parseable_coverage_all_unique": ratio(len(valid), len(rows)),
        "distribution": distribution(valid),
        "top_invalid": dict(invalid.most_common(20)),
    }


def images_profile(rows):
    counts = [len(animal_images(r)) for r in rows]
    all_urls = [r[f] for r in rows for f in ALL_IMAGE_FIELDS if meaningful(r.get(f))]
    valid, invalid = [], 0
    from .field_stats import valid_url

    for value in all_urls:
        if valid_url(value):
            valid.append(value)
        else:
            invalid += 1
    owners = defaultdict(set)
    for row in rows:
        for url in animal_images(row):
            owners[url].add(row["desertionNo"])
    return {
        "zero_images": counts.count(0),
        "one_image": counts.count(1),
        "two_images": counts.count(2),
        "three_plus_images": sum(n >= 3 for n in counts),
        "average_images_per_animal": distribution(counts)["mean"],
        "primary_image_coverage": ratio(sum(n > 0 for n in counts), len(rows)),
        "duplicate_url_within_animal": sum(
            len([r[f] for f in IMAGE_FIELDS if valid_url(r.get(f))]) - len(animal_images(r))
            for r in rows
        ),
        "url_schemes": dict(Counter(urlsplit(u).scheme for u in valid)),
        "extensions": dict(
            Counter(
                urlsplit(u).path.rsplit(".", 1)[-1].lower() if "." in urlsplit(u).path else "[none]"
                for u in valid
            )
        ),
        "invalid_url_shape": invalid,
        "nonplaceholder_url_values": len(all_urls),
        "urls_shared_by_distinct_animals": sum(len(ids) > 1 for ids in owners.values()),
        "url_hosts": dict(Counter(urlsplit(u).hostname for u in valid)),
        "notes": "Primary = first valid popfile1..8 URL, deduplicated in source order. "
        "No image requests; URL coverage is not image availability.",
    }


def shelter_region_profile(rows, redactor):
    shelters = defaultdict(list)
    for row in rows:
        if meaningful(row.get("careRegNo")):
            shelters[text(row["careRegNo"])].append(row)
    conflicts = {
        f: sum(
            len({canonical(r.get(f)) for r in group if meaningful(r.get(f))}) > 1
            for group in shelters.values()
        )
        for f in ("careNm", "careAddr")
    }
    sources = ["orgNm", "careAddr", "happenPlace"]

    # Derive candidates from structured organization/address fields. A place name
    # ending in 도 (e.g. 월미도 or 상도) alone is not a province.
    known_prefixes = {
        tokens[0]
        for row in rows
        for field in ("orgNm", "careAddr")
        if (tokens := text(row.get(field)).split())
        and re.fullmatch(r"[가-힣]+(?:특별자치도|특별자치시|특별시|광역시|도)", tokens[0])
    }

    def prefix(value):
        tokens = text(value).split()
        return tokens[0] if tokens and tokens[0] in known_prefixes else None

    comparable = agreements = disagreements = no_candidate = 0
    for row in rows:
        candidates = [p for f in sources if (p := prefix(row.get(f))) is not None]
        no_candidate += not candidates
        if len(candidates) >= 2:
            comparable += 1
            agreements += len(set(candidates)) == 1
            disagreements += len(set(candidates)) > 1
    return {
        "distinct_careRegNo": len(shelters),
        "careRegNo_coverage": ratio(sum(meaningful(r.get("careRegNo")) for r in rows), len(rows)),
        "shelter_name_address_conflicts": conflicts,
        "phone_blank_or_missing_ratio": ratio(
            sum(not meaningful(r.get("careTel")) for r in rows), len(rows)
        ),
        "address_blank_or_missing_ratio": ratio(
            sum(not meaningful(r.get("careAddr")) for r in rows), len(rows)
        ),
        "source_prefixes": {
            f: dict(
                Counter(
                    redactor.text(prefix(r.get(f)), personal=True)
                    if prefix(r.get(f))
                    else "[unresolved]"
                    for r in rows
                )
            )
            for f in sources
        },
        "two_or_more_sources_comparable": comparable,
        "raw_prefix_agreements": agreements,
        "raw_prefix_disagreements": disagreements,
        "no_sido_prefix_candidate": no_candidate,
        "normalization_status": "decision_required",
        "notes": "Conservative raw prefix diagnostic only, not a region normalizer. Aliases, "
        "concatenated organization values and sigungu need source/manual review. "
        "Raw display fallback does not clear the structured-region gate.",
    }


def assess_collection(run: dict, items: dict, dog_count: int, minimum: int) -> dict:
    unique = items["unique_desertion_no_count"]
    totals = run.get("reported_total_counts", [])
    total = totals[0] if totals and len(set(totals)) == 1 else None
    exception = (
        total is not None
        and 0 < total < minimum
        and run.get("entire_population_scope") is True
        and run.get("exhausted") is True
        and run.get("failed_pages", 0) == 0
        and items["raw_item_count"] == total
        and unique + items["duplicate_item_count"] == total
        and items["unusable_id_count"] == 0
    )
    issues = []
    if run.get("failed_pages", 0):
        issues.append("collection_failed_pages")
    if len(set(totals)) > 1:
        issues.append("reported_totalCount_changed")
    if run.get("stop_reason") in {"repeated_page", "unexpected_empty_page", "page_limit"}:
        issues.append(run["stop_reason"])
    if unique < minimum and not exception:
        issues.append("minimum_unique_not_met_and_population_exception_unproven")
    if dog_count < minimum and not exception:
        issues.append("minimum_unique_dogs_not_met")
    if items["unusable_id_count"]:
        issues.append("desertionNo_reliability_requires_review")
    return {
        "status": "sufficient" if not issues else "blocked",
        "minimum": minimum,
        "whole_population_exception": exception,
        "reported_stable_total": total,
        "issues": issues,
    }


def build_profile(rows, run, redactor, *, today: date, minimum=5000, seed=20260911):
    unique, identities = identity_profile(rows)
    dogs = [r for r in unique if text(r.get("upKindNm")) == "개"]
    non_dogs = [r for r in unique if meaningful(r.get("upKindNm")) and text(r["upKindNm"]) != "개"]
    species_unknown = len(unique) - len(dogs) - len(non_dogs)
    data = dogs  # All source rows retained; primary content metrics explicitly cover unique dogs.
    evidence = profile_evidence(data)
    age = number_profile(data, "age", parse_age, redactor)
    weight = number_profile(data, "weight", parse_weight, redactor)
    age["future_birth_year_count"] = sum(
        (v := parse_age(r.get("age"))) is not None and v > today.year for r in data
    )
    weights = [v for r in data if (v := parse_weight(r.get("weight"))) is not None]
    weight.update(
        zero_count=weights.count(0),
        negative_count=sum(v < 0 for v in weights),
        over_100kg_candidate=sum(v > 100 for v in weights),
        extreme_definition=">100kg diagnostic candidate, not a correction rule",
    )
    images = images_profile(data)
    shelter = shelter_region_profile(data, redactor)
    promotions = {}
    for prefix in ("adptn", "sprt", "srvc", "evnt"):
        names = [prefix + s for s in ("Title", "SDate", "EDate", "ConditionLimitTxt", "Txt", "Img")]
        promotions[prefix] = {
            "fields": {f: ratio(sum(meaningful(r.get(f)) for r in data), len(data)) for f in names},
            "any_ratio": ratio(
                sum(any(meaningful(r.get(f)) for f in names) for r in data), len(data)
            ),
            "complete_ratio": ratio(
                sum(all(meaningful(r.get(f)) for f in names) for r in data), len(data)
            ),
        }
    collection = assess_collection(run, identities, len(dogs), minimum)
    blockers = collection["issues"][:]
    if (identities["conflicting_id_ratio_unique"] or 0) > 0.001:
        blockers.append("conflicting_duplicate_ids_above_0.1_percent")
    if species_unknown:
        blockers.append("dog_non_dog_filtering_unresolved")
    if not data:
        blockers.append("no_confirmed_dog_records")
    status_policy = profile_status(data, today=today)
    if status_policy["issues"]:
        blockers.append("protecting_notice_start_requires_review")
    # Code policy is decided; verify the actual official joins before clearing this gate.
    if data:
        blockers.extend(
            [
                "structured_region_normalization_needs_decision",
            ]
        )
    freshness = {}
    for field, name, sign in (
        ("happenDt", "days_since_found", 1),
        ("noticeEdt", "days_until_notice_end", -1),
    ):
        freshness[name] = distribution(
            [
                (today - d.date()).days * sign
                for r in data
                if (d := parse_date(r.get(field))) is not None
            ]
        )
    aware = [d for r in data if (d := parse_date(r.get("updTm"))) is not None and d.tzinfo]
    as_of = datetime.combine(today, datetime.min.time(), tzinfo=UTC)
    freshness["source_update_lag_days_aware_only"] = distribution(
        [(as_of - d.astimezone(UTC)).total_seconds() / 86400 for d in aware]
    )
    freshness["source_update_lag_note"] = "Naive updTm excluded until source timezone is confirmed."
    groups = Counter(
        canonical(
            [r.get(f) for f in ("careRegNo", "happenDt", "happenPlace", "kindNm", "age", "weight")]
        )
        for r in data
        if all(
            meaningful(r.get(f))
            for f in ("careRegNo", "happenDt", "happenPlace", "kindNm", "age", "weight")
        )
    )
    selected, review = review_sample(data, seed)
    if len(data) < 100:
        review["limitation"] = "Fewer than 100 unique dogs exist in the collected sample."
    fields = profile_fields(rows, redactor)
    observations = profile_observations(data, today, redactor)
    summary = {
        "schema_version": 1,
        "run": run,
        "as_of_date": today.isoformat(),
        "denominators": {
            "field_dictionary": "all raw rows",
            "identity": "all raw rows / unique IDs",
            "content_metrics": "first-observed payload per unique dog ID",
            "unique_dogs": len(dogs),
            "unique_all_animals": len(unique),
        },
        "items": identities,
        "collection": collection,
        "blockers": list(dict.fromkeys(blockers)),
        "species": {
            "dog_count": len(dogs),
            "non_dog_count": len(non_dogs),
            "unresolved_count": species_unknown,
            "dog_ratio": ratio(len(dogs), len(unique)),
            "filter": "local exact upKindNm == 개; no server-side species assumption",
        },
        "fields": fields,
        "dates": profile_dates(data, today),
        "age": age,
        "weight": weight,
        "enums": {
            f: dict(
                Counter(
                    redactor.text(r.get(f), personal=True) if f in r else "[missing]"
                    for r in unique
                )
            )
            for f in ENUM_FIELDS
        },
        "breed": {
            "top_50": dict(
                Counter(redactor.text(r.get("kindNm"), personal=True) for r in data).most_common(50)
            ),
            "mixed_ratio": ratio(
                sum(
                    "믹스" in text(r.get("kindNm")) or "혼종" in text(r.get("kindNm")) for r in data
                ),
                len(data),
            ),
            "blank_ratio": ratio(sum(not meaningful(r.get("kindNm")) for r in data), len(data)),
            "kind_full_inconsistent": sum(
                meaningful(r.get("kindNm"))
                and meaningful(r.get("kindFullNm"))
                and text(r["kindNm"]) not in text(r["kindFullNm"])
                for r in data
            ),
        },
        "color": {
            "multi_color_candidate_ratio": ratio(
                sum(bool(re.search(r"[&/,·+]|및", text(r.get("colorCd")))) for r in data), len(data)
            ),
            "single_color_candidate_ratio": ratio(
                sum(
                    meaningful(r.get("colorCd"))
                    and not re.search(r"[&/,·+]|및", text(r["colorCd"]))
                    for r in data
                ),
                len(data),
            ),
            "unmapped_ratio": None,
            "mapping_status": "pending_observed_value_review",
        },
        "images": images,
        "shelter_region": shelter,
        "evidence": evidence,
        "promotions": promotions,
        "freshness": freshness,
        "repeated_discovery_groups": sum(n > 1 for n in groups.values()),
        "manual_review": review,
        "observations": observations,
        "status_policy": status_policy,
        "project_thresholds_not_source_facts": {
            "identity_missing_review": 0.001,
            "conflicting_id_review": 0.001,
            "weight_parse_failure_unknown_ux": 0.10,
            "image_empty_ux": 0.70,
            "behavior_exploration_bands": [0.30, 0.60],
        },
    }
    summary["color"]["unmapped_ratio"] = observations["color_unmapped_candidate_ratio"]
    summary["color"]["mapping_status"] = "measured_exact_vocabulary_candidates_not_production"
    summary["age"]["observed_format_note"] = (
        "Year-only and exact (60일미만)(년생) forms supported after live observation; "
        "no birth date inferred. Compare year_only_parser_coverage in observations."
    )
    return summary, selected


def apply_reference_results(summary, reference):
    from .client import ApiFailure

    if (
        reference.get("animal_run_id") != summary["run"].get("run_id")
        or reference.get("animal_raw_sha256") != summary["run"].get("raw_sha256")
        or reference.get("denominator_unique_dogs") != summary["species"]["dog_count"]
    ):
        raise ApiFailure("REFERENCE_PROFILE_CAPTURE_MISMATCH")
    summary["reference_data"] = reference
    region = reference["region"]
    if (
        region["mapped_dogs"] == summary["species"]["dog_count"]
        and region["unresolved_dogs"] == 0
        and region["ambiguous_dogs"] == 0
    ):
        summary["shelter_region"]["normalization_status"] = "official_codes_verified_for_capture"
        summary["shelter_region"]["notes"] = (
            "Raw prefix diagnostics retained for comparison. Official code joins and scoped "
            "animal-ID evidence are recorded in reference_data; no source values rewritten."
        )
        summary["blockers"] = [
            b for b in summary["blockers"] if b != "structured_region_normalization_needs_decision"
        ]
    summary["blockers"] = list(dict.fromkeys(summary["blockers"] + reference["blockers"]))
