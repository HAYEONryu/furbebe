"""Enrich a saved profiling capture with official cached catalogs and display status."""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from .client import AnimalApiClient, ApiFailure, Redactor, load_service_key
from .field_stats import text
from .metrics import identity_profile
from .profiling import ROOT, check_git_exclusion, load_capture, local_path
from .reference_cache import ReferenceCache
from .region_evidence import scoped_memberships
from .status_policy import korea_today, profile_status


def normalize_name(value):
    return " ".join(text(value).split())


def region_index(provinces, districts):
    index = defaultdict(set)
    for province in provinces:
        parent, name = province["orgCd"], normalize_name(province.get("orgdownNm"))
        for child in districts.get(parent, []):
            child_name = normalize_name(child.get("orgdownNm"))
            if not name or not child_name:
                continue
            if child["orgCd"] == parent and child_name == name:
                # The official self-code represents province-level administration.
                index[name].add((parent, parent))
            elif child_name != name:
                full = child_name if child_name.startswith(name + " ") else name + " " + child_name
                index[full].add((parent, child["orgCd"]))
    return index


def analyze_references(rows, cache, *, today, redactor=None, progress=None, source_filters=None):
    redactor = redactor or Redactor()
    unique, _ = identity_profile(rows)
    dogs = [r for r in unique if text(r.get("upKindNm")) == "개"]
    orgs = Counter(normalize_name(r.get("orgNm")) for r in dogs)
    provinces = cache.ensure(
        "sido", expected={name.split()[0] for name in orgs if name}, match_field="orgdownNm"
    )
    districts = {}
    for province in provinces:
        prefix = normalize_name(province.get("orgdownNm"))
        expected = {
            name[len(prefix) + 1 :] if name.startswith(prefix + " ") else name
            for name in orgs
            if name == prefix or name.startswith(prefix + " ")
        }
        if expected:
            districts[province["orgCd"]] = cache.ensure(
                "sigungu", {"upr_cd": province["orgCd"]}, expected=expected, match_field="orgdownNm"
            )
    index = region_index(provinces, districts)
    matched, unresolved, ambiguous = {}, Counter(), Counter()
    for name, count in orgs.items():
        candidates = index.get(name, set())
        if len(candidates) == 1:
            matched[name] = next(iter(candidates))
        elif candidates:
            ambiguous[redactor.text(name, personal=True)] += count
        else:
            unresolved[redactor.text(name, personal=True)] += count
    memberships, evidence_captures = scoped_memberships(
        cache, provinces, districts, set(unresolved) | set(ambiguous), source_filters or {}
    )
    evidence_confirmed = {}
    for name in list(unresolved) + list(ambiguous):
        group = [r for r in dogs if normalize_name(r.get("orgNm")) == name]
        choices = [memberships.get((r["desertionNo"], name), set()) for r in group]
        combined = set().union(*choices) if choices else set()
        if choices and all(len(c) == 1 for c in choices) and len(combined) == 1:
            matched[name] = next(iter(combined))
            evidence_confirmed[name] = len(group)
            unresolved.pop(name, None)
            ambiguous.pop(name, None)
    shelter_scopes = defaultdict(set)
    for row in dogs:
        codes = matched.get(normalize_name(row.get("orgNm")))
        if codes:
            shelter_scopes[codes].add(text(row.get("careRegNo")))
    shelter_memberships = set()
    shelter_items = 0
    for completed, ((parent, district), expected) in enumerate(sorted(shelter_scopes.items()), 1):
        items = cache.ensure("shelter", {"upr_cd": parent, "org_cd": district}, expected=expected)
        shelter_items += len(items)
        shelter_memberships.update((parent, district, row["careRegNo"]) for row in items)
        if progress:
            progress(
                {
                    "shelter_scopes_completed": completed,
                    "scope": {"upr_cd": parent, "org_cd": district},
                    "cache": dict(cache.stats),
                }
            )
    shelter_known = 0
    missing_shelter = Counter()
    for row in dogs:
        codes = matched.get(normalize_name(row.get("orgNm")))
        if codes:
            if (*codes, text(row.get("careRegNo"))) in shelter_memberships:
                shelter_known += 1
            else:
                missing_shelter[text(row.get("careRegNo"))] += 1
    breeds = {}
    for species in ("417000", "422400", "429900"):
        animals = [r for r in unique if text(r.get("upKindCd")) == species]
        if not animals:
            continue
        items = cache.ensure(
            "kind", {"up_kind_cd": species}, expected={text(r.get("kindCd")) for r in animals}
        )
        by_code = {r["kindCd"]: r for r in items}
        missing = Counter(
            text(r.get("kindCd")) for r in animals if text(r.get("kindCd")) not in by_code
        )
        mismatch = sum(
            normalize_name(by_code[text(r.get("kindCd"))].get("kindNm"))
            != normalize_name(r.get("kindNm"))
            for r in animals
            if text(r.get("kindCd")) in by_code
        )
        breeds[species] = {
            "catalog_count": len(items),
            "animals": len(animals),
            "missing_code_counts": dict(missing),
            "name_difference_count": mismatch,
        }
    status = profile_status(dogs, today=today)
    blockers = []
    if unresolved or ambiguous:
        blockers.append("official_region_code_join_unresolved")
    if status["issues"]:
        blockers.append("protecting_notice_start_requires_review")
    if cache.stats["offline_missing_catalogs"]:
        blockers.append("reference_catalogs_not_collected")
    return {
        "version": 1,
        "as_of_date": today.isoformat(),
        "denominator_unique_dogs": len(dogs),
        "region": {
            "source": "sido_v2.orgCd → upr_cd; sigungu_v2.orgCd → org_cd",
            "normalization_policy": {
                "sido": "sido_v2.orgCd == upr_cd",
                "sigungu": "sigungu_v2.orgCd == org_cd",
            },
            "animal_join": "Exact official organization name; whitespace normalization only. "
            "Province self-row used only when its official code equals the parent code. "
            "For ambiguous names, every original dog ID must be confirmed by scoped source "
            "animal responses with one consistent code. No fuzzy alias or shelter-address inference.",
            "mapped_dogs": sum(orgs[name] for name in matched),
            "unresolved_dogs": sum(unresolved.values()),
            "ambiguous_dogs": sum(ambiguous.values()),
            "unresolved_organization_counts": dict(unresolved),
            "ambiguous_organization_counts": dict(ambiguous),
            "organizations_confirmed_by_scoped_animal_ids": evidence_confirmed,
            "scoped_animal_evidence": evidence_captures,
            "organization_code_mapping": {
                redactor.text(name, personal=True): {
                    "sido": a,
                    "sigungu": b,
                    "upr_cd": a,
                    "org_cd": b,
                }
                for name, (a, b) in sorted(matched.items())
            },
            "sido_catalog_count": len(provinces),
            "sigungu_catalog_count": sum(len(v) for v in districts.values()),
        },
        "shelter": {
            "requested_scopes": len(shelter_scopes),
            "catalog_memberships": shelter_items,
            "matched_dogs": shelter_known,
            "missing_careRegNo_counts": dict(missing_shelter),
            "note": "Shelter membership is scoped by upr_cd/org_cd/careRegNo. "
            "A shared shelter does not identify an animal's jurisdiction. Missing catalog entries retained.",
        },
        "breed": breeds,
        "status_policy": status,
        "cache": dict(cache.stats),
        "blockers": blockers,
        "launch_decisions_still_pending": [
            "size thresholds",
            "age thresholds",
            "animals_active definition",
        ],
    }


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--input", required=True, type=Path)
    cli.add_argument(
        "--fetch-missing",
        action="store_true",
        help="Fetch only absent catalogs/codes; otherwise offline.",
    )
    cli.add_argument("--as-of", help="YYYY-MM-DD; default is current Korean calendar date")
    args = cli.parse_args(argv)
    try:
        from datetime import date

        today = date.fromisoformat(args.as_of) if args.as_of else korea_today()
        check_git_exclusion(ROOT)
        raw = local_path(ROOT, args.input)
        rows, run = load_capture(raw)
        directory = local_path(ROOT, Path(".local/profiling/reference-data"))
        if args.fetch_missing:
            with AnimalApiClient(load_service_key(ROOT)) as client:
                cache = ReferenceCache(directory, client)
                result = analyze_references(
                    rows,
                    cache,
                    today=today,
                    redactor=client.redactor,
                    progress=lambda value: print(json.dumps(value), flush=True),
                    source_filters=run.get("query_without_key", {}),
                )
        else:
            result = analyze_references(
                rows,
                ReferenceCache(directory),
                today=today,
                source_filters=run.get("query_without_key", {}),
            )
        result["animal_run_id"] = run["run_id"]
        result["animal_raw_sha256"] = run["raw_sha256"]
        result["reference_cache_sha256"] = (
            ReferenceCache.digest(
                json.loads((directory / "cache.json").read_text(encoding="utf-8"))
            )
            if (directory / "cache.json").exists()
            else None
        )
        (raw.parent / "reference-profile.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        from .reports import write_reference_report

        write_reference_report(ROOT, result)
        print(
            json.dumps(
                {
                    "mapped_dogs": result["region"]["mapped_dogs"],
                    "unresolved_dogs": result["region"]["unresolved_dogs"],
                    "status": result["status_policy"]["display_state_frequencies"],
                    "blockers": result["blockers"],
                    "cache": result["cache"],
                }
            )
        )
        return 2 if result["blockers"] else 0
    except ApiFailure as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc)}), file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, TypeError):
        print(
            json.dumps({"status": "blocked", "reason": "REFERENCE_IO_OR_ANALYSIS_ERROR"}),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
