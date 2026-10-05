"""Additional empirical diagnostics; proposals never assign production tags."""

import re
from collections import Counter

from .evidence import classify
from .field_stats import distribution, meaningful, parse_age, parse_date, parse_weight, ratio, text

COLOR_CANDIDATES = {
    "흰색": "white",
    "백색": "white",
    "화이트": "white",
    "갈색": "brown",
    "브라운": "brown",
    "검정": "black",
    "검정색": "black",
    "검은색": "black",
    "흑색": "black",
    "블랙": "black",
    "크림색": "cream",
    "크림": "cream",
    "회색": "gray",
    "그레이": "gray",
    "황갈색": "tan",
    "황색": "yellow",
    "노란색": "yellow",
    "금색": "gold",
}


def color_candidate(value):
    """Exact observed vocabulary only; unknown compound terms stay unresolved."""
    if not meaningful(value):
        return None
    tokens = [p.strip() for p in re.split(r"[&/,·+]", value)]
    if any(p not in COLOR_CANDIDATES for p in tokens):
        return None
    return list(dict.fromkeys(COLOR_CANDIDATES[p] for p in tokens))


def profile_observations(rows, today, redactor):
    sizes, ages, age_forms, months = Counter(), Counter(), Counter(), Counter()
    literal_sizes = Counter()
    update_calendar_gaps = []
    source_pairs, organs, state_counts = Counter(), Counter(), Counter()
    color_counts, color_proposals = Counter(), {}
    date_violations = Counter()
    for row in rows:
        w = parse_weight(row.get("weight"))
        size = (
            "unknown"
            if w is None or w <= 0
            else "tiny"
            if w <= 5
            else "small"
            if w <= 10
            else "medium"
            if w <= 20
            else "large"
        )
        sizes[size] += 1
        literal_sizes["tiny" if w is not None and w <= 0 else size] += 1
        year = parse_age(row.get("age"))
        estimated = today.year - year if year is not None else None
        age = (
            "unknown"
            if estimated is None or estimated < 0
            else "puppy"
            if estimated <= 1
            else "young"
            if estimated <= 4
            else "adult"
            if estimated <= 9
            else "senior"
        )
        ages[age] += 1
        value = text(row.get("age"))
        age_forms[
            "year_only"
            if re.fullmatch(r"\d{4}\(년생\)", value)
            else "under_60_days_annotation"
            if re.fullmatch(r"\d{4}\(60일미만\)\(년생\)", value)
            else "other"
        ] += 1
        found = parse_date(row.get("happenDt"))
        months[found.strftime("%Y-%m") if found else "unknown"] += 1
        updated = parse_date(row.get("updTm"))
        if updated:
            update_calendar_gaps.append((today - updated.date()).days)
        source_pairs[(text(row.get("upKindCd")), text(row.get("upKindNm")))] += 1
        organs[redactor.text(row.get("orgNm"), personal=True)] += 1
        state_counts[redactor.text(row.get("processState"), personal=True)] += 1
        raw_color = text(row.get("colorCd"))
        proposal = color_candidate(raw_color)
        color_proposals[redactor.text(raw_color, personal=True)] = proposal
        color_counts[
            "unmapped" if proposal is None else "single" if len(proposal) == 1 else "multiple"
        ] += 1
        for key in ("happenDt", "noticeSdt", "noticeEdt"):
            if (d := parse_date(row.get(key))) and d.date() > today:
                date_violations[key + "_future"] += 1
    pairs = Counter()
    for row in rows:
        org = text(row.get("orgNm")).split()
        addr = text(row.get("careAddr")).split()
        if org and addr and org[0] != addr[0]:
            pairs[(org[0], addr[0])] += 1
    return {
        "denominator_unique_dogs": len(rows),
        "proposed_size_groups": dict(sizes),
        "contract_size_groups_before_quality_policy": dict(literal_sizes),
        "proposed_age_groups": dict(ages),
        "proposal_note": "Existing contract thresholds evaluated, not finalized or changed. "
        "The proposed size counts exclude zero/negative weights; this quality policy is "
        "not approved for production. Literal contract counts are shown separately. "
        ">100kg values remain diagnostic large candidates, not validated measurements. "
        "Future birth years excluded from proposed age groups.",
        "age_formats": dict(age_forms),
        "year_only_parser_coverage": ratio(age_forms["year_only"], len(rows)),
        "found_month_distribution": dict(sorted(months.items())),
        "species_code_name_pairs": [
            {"code": c, "name": n, "count": count} for (c, n), count in sorted(source_pairs.items())
        ],
        "organization_frequencies": dict(organs.most_common()),
        "organization_address_prefix_difference_pairs": [
            {
                "organization_prefix": redactor.text(a, personal=True),
                "address_prefix": redactor.text(b, personal=True),
                "count": n,
            }
            for (a, b), n in pairs.most_common()
        ],
        "region_note": "Different prefixes may reflect jurisdiction, shelter location or renamed "
        "administrative areas; do not label all differences data errors.",
        "process_state_frequencies_dogs": dict(state_counts),
        "sex_frequencies_dogs": dict(Counter(text(r.get("sexCd")) for r in rows)),
        "neuter_frequencies_dogs": dict(Counter(text(r.get("neuterYn")) for r in rows)),
        "animals_active_candidate_protecting_only": state_counts.get("보호중", 0),
        "active_note": "Candidate definition only: raw processState=보호중. "
        "This is not evidence of immediate adoption eligibility.",
        "color_mapping_candidate_counts": dict(color_counts),
        "color_unmapped_candidate_ratio": ratio(color_counts["unmapped"], len(rows)),
        "color_mapping_candidates": color_proposals,
        "adoption_text_meaningful_ratio": ratio(
            sum(classify(r.get("adptnTxt"))["meaningful"] for r in rows), len(rows)
        ),
        "future_date_counts": dict(date_violations),
        "updTm_calendar_date_gap_days": distribution(update_calendar_gaps),
        "update_gap_note": "Difference between the analysis calendar date and the raw updTm "
        "calendar date only. Not an absolute source-update lag; source timezone is unconfirmed.",
    }
