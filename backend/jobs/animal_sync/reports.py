"""Render local machine artifacts and shareable aggregate reports."""

import csv
import json

from .client import ENDPOINT
from .evidence import export_review
from .field_stats import FIELDS

SECTIONS = [
    "실행 날짜 / API endpoint",
    "표본 규모",
    "응답 형태",
    "Identity 품질",
    "필드 coverage",
    "Date 품질",
    "Weight/Age 품질",
    "State/Enum 값",
    "Image coverage",
    "Shelter/Region 품질",
    "Description 품질",
    "Behavior evidence 비율",
    "Health evidence 비율",
    "Adoption promotion coverage",
    "데이터 이상치",
    "Manual review 대상",
    "DB 설계에 미치는 영향",
    "Tag 설계에 미치는 영향",
    "Frontend UX에 미치는 영향",
    "Phase 2 진행 전 결정 필요사항",
]
DECISIONS = {
    "Animal unique key": "Retain source + desertionNo; no authoritative conflict winner selected.",
    "Dog filtering": "Content metrics: exact upKindNm=개. Report unresolved species separately.",
    "Weight normalization": "Strict decimal (Kg) parser; unknown remains null; report anomalies.",
    "Age normalization": "Retain birth_year and age_text; no exact birthday or attained-age claim.",
    "Sex mapping": "Public male/female/unknown fixed; source mapping awaits observed values.",
    "Neuter mapping": "Public yes/no/unknown fixed; source mapping awaits observed values.",
    "processState handling": "For raw processState=보호중 only: today-noticeSdt >= 10 calendar days "
    "displays 입양 가능; earlier dates display 보호중. Other source states remain unchanged. "
    "Preserve the raw source value.",
    "Region source/mapping": "Use sido_v2.orgCd as upr_cd and sigungu_v2.orgCd as org_cd. "
    "Join organization names exactly after whitespace normalization; unresolved names remain "
    "data-quality findings.",
    "Main image policy": "First valid popfile1..8 URL, source order and animal-level deduplication.",
    "Meaningful text policy": "Separate empty/placeholder/admin/descriptive/health/behavior/mixed. "
    "Short-text and evidence flags overlap for words like 순함/경계; "
    "record both, without choosing production eligibility.",
    "Personality trait eligibility": "Keywords are candidates, not tags. Negation and context "
    "require human review; specialMark existence is insufficient.",
    "Health text handling": "Preserve source evidence, no diagnoses. 없음 can express a negative "
    "finding; a placeholder count does not rewrite source text.",
    "Adoption promotion storage": "Preserve raw fields. Later API uses fixed nullable object shape.",
    "Size group thresholds": "5/10/20kg remain proposals pending measured distribution.",
    "Age group thresholds": "0–1/2–4/5–8/9+ remain proposals pending measured distribution.",
    "animals_active definition": "Definition and launch field presence require source status review.",
}


def json_block(value):
    fence = chr(96) * 3
    return (
        "\n"
        + fence
        + "json\n"
        + json.dumps(value, ensure_ascii=False, indent=2)
        + "\n"
        + fence
        + "\n"
    )


def cell(value):
    return str(value).replace("|", r"\|").replace("\n", " ").replace("\r", " ")


def measured_overview(summary):
    n = summary["species"]["dog_count"]
    evidence = summary["evidence"]

    def pct(value, digits=2):
        return "not measured" if value is None else f"{value * 100:.{digits}f}%"

    output = "## Measured findings / 주요 결과\n\n"
    output += (
        f"- Raw {summary['items']['raw_item_count']:,}; unique animals "
        f"{summary['items']['unique_desertion_no_count']:,}; unique dogs {n:,}.\n"
        f"- Duplicate rows {summary['items']['duplicate_item_count']}; conflicting IDs "
        f"{summary['items']['conflicting_id_count']}; unusable IDs "
        f"{summary['items']['unusable_id_count']}.\n"
        f"- Behavior candidates {pct(evidence['ratios'].get('any_behavior'))}; "
        f"health {pct(evidence['ratios'].get('any_health'))}; "
        f"administrative {pct(evidence['ratios'].get('any_administrative'))}. "
        "Multi-label candidates, not confirmed traits or diagnoses.\n"
        f"- Primary image URL coverage {pct(summary['images']['primary_image_coverage'], 3)} "
        f"({n - summary['images']['zero_images']:,}/{n:,}); "
        "image availability and HTTPS support were not tested.\n"
        f"- Weight syntax parse {pct(summary['weight']['parse_success_ratio'])}; "
        f"zero weights {summary['weight']['zero_count']}; "
        f">100kg candidates {summary['weight']['over_100kg_candidate']}. No correction applied.\n"
        f"- Age parse {pct(summary['age']['parse_success_ratio'])}; original age_text retained.\n"
        f"- Any adoption promotion {pct(summary['promotions']['adptn']['any_ratio'])}; "
        "nullable detail object remains appropriate.\n"
        "- Requested date range and sampled date range differ; target-based collection is "
        "not an exhaustive population census.\n"
        "- Human review notes are blank. Region code mapping and the 10-calendar-day "
        "protecting-status display policy are decided; unresolved joins remain data-quality "
        "findings. No Phase 2 implementation.\n\n"
    )
    output += (
        "### 결과 해석\n\n"
        f"- 지역 세 원문의 시도 prefix가 다른 개는 "
        f"{summary['shelter_region']['raw_prefix_disagreements']:,}건입니다. 관할 기관과 보호소 소재지, "
        "옛 명칭과 새 명칭의 차이가 섞여 있어 모두 데이터 오류로 단정할 수 없습니다. "
        "사용자 결정에 따라 공식 코드 목록으로 연결하며, 실제 매칭 결과는 참조 코드 보고서를 확인합니다.\n"
        f"- 발견일이 공고 종료일보다 늦은 자료 "
        f"{summary['dates']['consistency']['happenDt<=noticeEdt']['violations']:,}건, "
        f"품종명과 전체 품종명 문자열 불일치 {summary['breed']['kind_full_inconsistent']:,}건을 "
        "보존했습니다. 문자열 불일치가 동물종 판별 오류를 뜻하지는 않습니다.\n"
        "- 행동 후보 coverage는 후보 문장의 존재 비율입니다. 30–60% 구간은 명세의 "
        "선택적 trait 탐색 검토 구간이며, 검토 없이 성격 태그를 부여할 근거가 아닙니다.\n"
        "- 입양 홍보 문구는 개별 동물 설명인지 보호소 공통 안내인지 확인해야 합니다. "
        "낮은 coverage는 계약의 nullable adoption_promotion을 유지할 근거입니다.\n"
        "- 이미지 URL의 HTTP/HTTPS 분포와 실제 브라우저 표시 가능성은 별개입니다. "
        "이미지는 내려받지 않았으며 HTTP 주소를 HTTPS로 임의 변경하지 않았습니다.\n"
        "- updTm에는 시간대가 없어 절대적인 업데이트 지연은 미확정입니다. "
        "원문 날짜와 분석 기준일의 달력 날짜 차이만 별도로 집계합니다.\n\n"
    )
    return output


def decision_evidence(title, summary):
    observations = summary.get("observations", {})
    sources = {
        "Animal unique key": summary["items"],
        "Dog filtering": summary["species"],
        "Weight normalization": summary["weight"],
        "Age normalization": summary["age"],
        "Sex mapping": observations.get("sex_frequencies_dogs", summary["enums"].get("sexCd")),
        "Neuter mapping": observations.get(
            "neuter_frequencies_dogs", summary["enums"].get("neuterYn")
        ),
        "processState handling": summary.get(
            "status_policy", observations.get("process_state_frequencies_dogs")
        ),
        "Region source/mapping": summary.get("reference_data", {}).get(
            "region", summary["shelter_region"]
        ),
        "Main image policy": summary["images"],
        "Meaningful text policy": summary["evidence"]["by_field"],
        "Personality trait eligibility": summary["evidence"]["ratios"],
        "Health text handling": summary["evidence"]["health_structured_coverage"],
        "Adoption promotion storage": summary["promotions"]["adptn"],
        "Size group thresholds": {
            "literal_contract": observations.get("contract_size_groups_before_quality_policy"),
            "quality_policy_candidate": observations.get("proposed_size_groups"),
            "note": observations.get("proposal_note"),
        },
        "Age group thresholds": observations.get("proposed_age_groups"),
        "animals_active definition": {
            "protecting_only_candidate": observations.get(
                "animals_active_candidate_protecting_only"
            ),
            "adoption_eligibility_established": False,
        },
    }
    return sources.get(title)


def decisions_text(summary=None):
    output = """# API profiling decisions

Scope: Phase 0–1 only. Size, age, and animals_active decisions remain pending unless explicitly confirmed.

## Governing sources and confirmed chat decisions

HTTP contract: FURBEBE_FASTAPI_V1_CONTRACT.md.
Profiling methodology/blockers: FURBEBE_CODEX_PHASE0_1_DATA_PROFILING_SPEC.md.
Stack/architecture/prohibitions: CODEX_FURBEBE_DEVELOPMENT_INSTRUCTIONS.md.
Later explicit chat decisions override these documents.

- Similar limit: default 4, min 1, max 12. Four is the current UI default.
- List: sido, sigungu, size_group. No region/size aliases.
- Raw region display is presentation only, not proof of reliable structured normalization.
- Region codes: `sido_v2.orgCd` is `upr_cd`; `sigungu_v2.orgCd` is `org_cd`.
- Status display: raw `processState=보호중` becomes `입양 가능` when
    `today - noticeSdt >= 10` calendar days; otherwise it remains `보호중`.
- Evaluate calendar dates in Asia/Seoul; exactly day 10 qualifies. Other source states remain
  unchanged. Invalid/missing/future noticeSdt does not produce 입양 가능 and is reported.
- Reference lookup APIs: sido_v2, sigungu_v2, kind_v2, shelter_v2, using HTTPS.
  Cache successful catalogs by their parent query codes. Fetch only absent catalogs or
  unknown codes; repeated absent-code checks are limited to once per day.
- Minimum 5,000 unique animals. The exception requires the true entire population below
  5,000, stable totalCount, and exhaustive collection. Report total/raw/unique/duplicates.
- Only size thresholds, age thresholds, region normalization, processState UI semantics,
  and animals_active may be proposed for launch adjustment. Other JSON shapes stay fixed.
- Preserve Frontend → FastAPI → SQLAlchemy → PostgreSQL; no frontend direct DB access.

"""
    if summary is not None:
        output += """## Launch 전 검토 범위 — 현재 확정되지 않은 항목

| 항목 | 실데이터에 따른 제안 | 확정 상태 |
|---|---|---|
| size_group | 초기 5/10/20kg 경계 유지 후보. 원문 파싱과 0kg·극단값의 품질 판정은 분리한다. | 미확정; 아래 분포 비교 |
| age_group | 초기 0–1/2–4/5–8/9+ 경계 유지 후보. 정확한 만 나이로 표시하지 않는다. | 미확정; 아래 분포 |
| region | `sido_v2.orgCd`를 `upr_cd`, `sigungu_v2.orgCd`를 `org_cd`로 사용한다. 매칭되지 않는 동물은 여전히 blocker로 보고한다. | **정책 확정 / 연결 결과 별도 검증** |
| processState UI | 원문 `processState`가 `보호중`이고 `today - noticeSdt >= 10`일이면 `입양 가능`, 아니면 `보호중`으로 표시한다. 원문은 보존한다. | **확정** |
| animals_active | raw processState=보호중 건수는 비교 후보일 뿐이다. 포함/제외 조건과 launch 필드 존재 여부 확정 필요. | processState 결정에 종속 |

그 밖의 endpoint, query, validation, JSON shape는 변경하지 않았습니다.
기존 계약의 process_state 원문 표시 원칙과 이번 사용자 표시 규칙의 차이는 최신 채팅 결정으로 해소합니다.
원본 processState와 계산된 표시 상태를 분리해 보존하며, FastAPI endpoint는 아직 구현하지 않습니다.
키워드 수동 검토와 updTm 시간대 확인도 남아 있습니다.
아래 Chosen 중 proposal/pending 표기는 검토 대상으로 기록한 것이며, 위에서 확정한 지역/상태 정책과 구분합니다.

"""
    evidence = "No live measurement yet." if summary is None else "Run " + summary["run"]["run_id"]
    for title, choice in DECISIONS.items():
        measured = json_block(decision_evidence(title, summary)) if summary is not None else ""
        if summary is not None and title == "Age normalization":
            choice = (
                "Extract birth_year from observed YYYY(년생) and YYYY(60일미만)(년생) "
                "forms. Retain age_text and do not infer a birthday. Empty year stays null."
            )
        if summary is not None and title == "Sex mapping":
            choice = "Source mapping proposal: M→male, F→female, Q→unknown; preserve raw values. Public enum unchanged."
        if summary is not None and title == "Neuter mapping":
            choice = "Source mapping proposal: Y→yes, N→no, U→unknown; preserve raw values. Public enum unchanged."
        if summary is not None and title == "Size group thresholds":
            choice = "Measured 5/10/20kg boundaries remain a launch proposal. Zero-weight null policy and extreme-value handling need review; no production threshold or normalizer changed."
        if summary is not None and title == "Age group thresholds":
            choice = "Measured approximate year-based 0–1/2–4/5–8/9+ groups remain a launch proposal. No exact attained age or production rule finalized."
        output += (
            f"## {title}\n\nDecision: {title}\n\nEvidence: {evidence}\n{measured}\n"
            f"Chosen: {choice}\n\n"
            "Rejected alternatives: fabricated defaults, unmeasured production mappings, "
            "or contract changes outside the approved scope.\n\n"
            "Reason: retain source uncertainty and the latest user decisions.\n\n"
            "Revisit when: live results, source documentation or human review supplies evidence.\n\n"
        )
    return output


def pending_reports(root, reason="API key or live data not available"):
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    output = "# API data profile\n\nStatus: NOT MEASURED — " + reason + ".\n\n"
    output += "No fixture counts are represented as live data. No Phase 1 completion claim.\n"
    for i, name in enumerate(SECTIONS, 1):
        output += f"\n## {i}. {name}\n\nPending live collection / analysis.\n"
    (docs / "api-data-profile.md").write_text(output, encoding="utf-8")
    dictionary = (
        "# API field dictionary\n\nStatus: NOT MEASURED. These fields are required by "
        "the spec; missing and additional fields will be reported after collection.\n\n"
        "| field | category | observation |\n|---|---|---|\n"
    )
    dictionary += "".join(
        f"| {field} | {category} | not measured |\n" for field, category in FIELDS.items()
    )
    (docs / "api-field-dictionary.md").write_text(dictionary, encoding="utf-8")
    (docs / "api-profiling-decisions.md").write_text(decisions_text(), encoding="utf-8")


def write_reports(root, output_dir, summary, selected, redactor):
    stamp = summary["run"]["run_id"]
    (output_dir / f"summary-{stamp}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    fields = summary["fields"]
    with (output_dir / f"field-stats-{stamp}.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        writer = csv.DictWriter(file, fieldnames=list(fields[0]) if fields else ["field"])
        writer.writeheader()
        for row in fields:
            writer.writerow(
                {
                    k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
                    for k, v in row.items()
                }
            )
    export_review(output_dir / f"manual-review-{stamp}.csv", selected, redactor)
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    columns = [
        "field",
        "category",
        "observed_type",
        "presence_count",
        "presence_ratio",
        "missing_count",
        "null_count",
        "blank_count",
        "placeholder_count",
        "distinct_count",
        "sample_values",
        "max_length",
        "parseable_ratio",
        "parseable_denominator",
        "notes",
    ]
    dictionary = "# API field dictionary\n\nRun: " + stamp + ". Denominator: all raw rows.\n\n"
    dictionary += "| " + " | ".join(columns) + " |\n|" + "|".join("---" for _ in columns) + "|\n"
    dictionary += "".join(
        "| " + " | ".join(cell(row.get(c)) for c in columns) + " |\n" for row in fields
    )
    (docs / "api-field-dictionary.md").write_text(dictionary, encoding="utf-8")
    sections = [
        {"endpoint": ENDPOINT, "as_of": summary["as_of_date"], "run": summary["run"]},
        {
            "denominators": summary["denominators"],
            "collection": summary["collection"],
            "species": summary["species"],
        },
        {
            "shapes": summary["run"].get("observed_shapes", {}),
            "headers": summary["run"].get("header_observations", {}),
            "note": "Only recorded shapes are observed live; others are mock-tested.",
        },
        summary["items"],
        {"field_count": len(fields), "dictionary": "api-field-dictionary.md"},
        summary["dates"],
        {"weight": summary["weight"], "age": summary["age"]},
        summary["enums"],
        summary["images"],
        summary["shelter_region"],
        summary["evidence"]["by_field"],
        {
            "counts": summary["evidence"]["counts"],
            "ratios": summary["evidence"]["ratios"],
            "note": summary["evidence"]["notes"],
        },
        summary["evidence"]["health_structured_coverage"],
        summary["promotions"],
        {
            "freshness": summary["freshness"],
            "breed": summary["breed"],
            "color": summary["color"],
            "repeated_discovery_groups": summary["repeated_discovery_groups"],
        },
        summary["manual_review"],
        "Preserve source values and nullable fields. No schema/UPSERT implemented. Review identity.",
        "Behavior/health/admin are separate candidates. Human review pending; no production tags.",
        {
            "project_thresholds_not_source_facts": summary["project_thresholds_not_source_facts"],
            "note": "Coverage is not correctness. No fabricated missing-data values.",
        },
        {"blockers": summary["blockers"], "next": "Report unresolved decisions; no Phase 2."},
    ]
    profile = "# API data profile\n\nRun: " + stamp + ".\n\n"
    profile += (
        "Status: BLOCKED / decisions pending.\n" if summary["blockers"] else "Status: collected.\n"
    )
    profile += "\n" + measured_overview(summary)
    for i, (name, data) in enumerate(zip(SECTIONS, sections, strict=True), 1):
        profile += f"\n## {i}. {name}\n" + (
            json_block(data) if not isinstance(data, str) else "\n" + data + "\n"
        )
    profile += (
        "\n## Method limits\n\nFirst-observed unique dog payloads are diagnostic snapshots. "
        "Do not extrapolate unmeasured periods or regions. Naive timestamps are not silently "
        "UTC. Prefix/keyword heuristics do not prove production mappings or tag correctness. "
        "Review notes remain blank for human review. All row-level files stay local.\n"
    )
    if "observations" in summary:
        profile += "\n## Empirical proposals and sample composition\n" + json_block(
            summary["observations"]
        )
    if "status_policy" in summary:
        profile += "\n## 사용자 확정 상태 규칙\n" + json_block(summary["status_policy"])
    if "reference_data" in summary:
        profile += (
            "\n## 공식 코드 연결 검증\n\n[상세 참조 코드 보고서](api-reference-data-profile.md)\n"
        )
        profile += json_block(
            {
                "blockers": summary["reference_data"]["blockers"],
                "mapped_dogs": summary["reference_data"]["region"]["mapped_dogs"],
                "unresolved_dogs": summary["reference_data"]["region"]["unresolved_dogs"],
            }
        )
    (docs / "api-data-profile.md").write_text(profile, encoding="utf-8")
    (docs / "api-profiling-decisions.md").write_text(decisions_text(summary), encoding="utf-8")


def write_reference_report(root, result):
    region = result["region"]
    missing_breed = sum(sum(v["missing_code_counts"].values()) for v in result["breed"].values())
    missing_shelter = result["shelter"]["missing_careRegNo_counts"]
    output = f"""# 공식 참조 코드·상태 정책 검증

동물 run: {result["animal_run_id"]}; 상태 분석 기준일: {result["as_of_date"]} (Asia/Seoul).
범위: Phase 0–1. FastAPI endpoint 및 DB schema 구현 없음.

## 최신 결정과 측정 결과

- 프로젝트 `sido` 코드 = OpenAPI `upr_cd`, `sigungu` 코드 = `org_cd`.
- `sido_v2.orgCd`가 시도 코드, `sigungu_v2.orgCd`가 시군구 코드이며 `uprCd`로 소속을 확인합니다.
- 고유 개 {result["denominator_unique_dogs"]:,}건 중 코드 연결 {region["mapped_dogs"]:,}건,
  미매칭 {region["unresolved_dogs"]:,}건, 다중 후보 {region["ambiguous_dogs"]:,}건입니다.
- `processState=보호중`이고 `한국 날짜 - noticeSdt >= 10일`이면 표시 상태는 `입양 가능`입니다.
  10일 미만은 `보호중`, 다른 원문 상태는 유지합니다. 정확히 10일째부터 적용합니다.
- 날짜 누락·오류·미래 날짜는 입양 가능으로 바꾸지 않고 보고합니다. `noticeEdt`나 `happenDt`로 대체하지 않습니다.
- 이 계산은 사용자가 정한 FURBEBE 표시 정책입니다. 원본 상태와 원본 동물 데이터는 수정하지 않습니다.
  저장된 동물 snapshot의 상태로 계산했으며 실시간 보호소 상태를 새로 확인한 결과는 아닙니다.

## 캐시 동작

`.local/profiling/reference-data/cache.json`에 코드 목록과 조회 조건·시각·checksum을 저장합니다.
시도 전체 / 시도별 시군구 / 축종별 품종 / 시도·시군구별 보호소 단위로 구분합니다.
기존 코드가 있으면 재실행해도 네트워크를 호출하지 않습니다.
모르는 코드가 나오면 해당 범위만 갱신하고, 조회해도 없었던 코드는 24시간 동안 반복 조회하지 않습니다.
오류·불완전 pagination 결과는 정상 캐시에 덮어쓰지 않습니다. 빈 정상 목록도 조회 이력으로 보존합니다.
보호소 코드는 관할별 소속을 따로 저장하므로 공동 보호소를 다른 지역으로 오인하지 않습니다.
JSON 원문은 `.local/profiling/` 밖으로 저장하지 않으며 키를 로그에 포함하지 않습니다.

## 현재 결과

공식 목록 재조회 후에도 없는 품종 코드에 해당하는 동물은 {missing_breed:,}건입니다.
보호소 코드 {len(missing_shelter)}개는 해당 관할의 현재 보호소 목록에 없으며, 해당 개는 {sum(missing_shelter.values()):,}건입니다.
폐지·변경 여부나 원인은 아직 확인하지 않았습니다. 원문 코드와 이름을 유지하고 임의의 다른 코드로 연결하지 않습니다.
이 항목들은 지역 코드 매칭 성공 여부와 구분해 계속 보고하며, 캐시에 조회 이력을 저장했습니다.

"""
    output += json_block(result)
    output += "\n## 남은 launch 결정\n\nsize/age 경계와 animals_active 정의는 별도 결정입니다. 수동 검토 의견은 자동 작성하지 않습니다.\n"
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "api-reference-data-profile.md").write_text(output, encoding="utf-8")
