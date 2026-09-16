# API profiling decisions

> 2026-09-15 최신 결정: 체중 A(5/10/20kg), 나이 A(0~1/2~4/5~8/9+), v1 animals_active 제외, 근거 있는 행동·건강 설명 선택 제공이 사용자 승인으로 확정됐다. [Phase 1.5 확정 기록](phase1-5-product-decisions.md)이 아래 Phase 1 당시 pending/proposal 표기보다 우선한다.

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

## Launch 전 검토 범위 — 현재 확정되지 않은 항목

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

## Animal unique key

Decision: Animal unique key

Evidence: Run 20260914T232312940282Z

```json
{
  "raw_item_count": 17000,
  "unique_desertion_no_count": 17000,
  "unusable_id_count": 0,
  "unusable_id_ratio": 0.0,
  "missing_count": 0,
  "null_count": 0,
  "blank_count": 0,
  "non_string_count": 0,
  "duplicate_item_count": 0,
  "duplicate_ratio_raw": 0.0,
  "identical_duplicate_item_count": 0,
  "conflicting_additional_versions": 0,
  "conflicting_id_count": 0,
  "conflicting_id_ratio_unique": 0.0,
  "conflict_fields": {},
  "content_sampling_policy": "First observed payload per usable string ID for descriptive statistics only; no authoritative UPSERT winner selected. Every version is retained in the local raw capture."
}
```

Chosen: Retain source + desertionNo; no authoritative conflict winner selected.

Rejected alternatives: fabricated defaults, unmeasured production mappings, or contract changes outside the approved scope.

Reason: retain source uncertainty and the latest user decisions.

Revisit when: live results, source documentation or human review supplies evidence.

## Dog filtering

Decision: Dog filtering

Evidence: Run 20260914T232312940282Z

```json
{
  "dog_count": 10507,
  "non_dog_count": 6493,
  "unresolved_count": 0,
  "dog_ratio": 0.618059,
  "filter": "local exact upKindNm == 개; no server-side species assumption"
}
```

Chosen: Content metrics: exact upKindNm=개. Report unresolved species separately.

Rejected alternatives: fabricated defaults, unmeasured production mappings, or contract changes outside the approved scope.

Reason: retain source uncertainty and the latest user decisions.

Revisit when: live results, source documentation or human review supplies evidence.

## Weight normalization

Decision: Weight normalization

Evidence: Run 20260914T232312940282Z

```json
{
  "denominator_nonplaceholder": 10507,
  "parse_success": 10445,
  "parse_failure": 62,
  "parse_success_ratio": 0.994099,
  "parse_failure_ratio": 0.005901,
  "parseable_coverage_all_unique": 0.994099,
  "distribution": {
    "count": 10445,
    "min": 0.0,
    "p25": 2.8,
    "median": 5.0,
    "p75": 10.0,
    "p95": 20.7,
    "max": 52.05,
    "mean": 7.430286261369076
  },
  "top_invalid": {
    "1~1.2(Kg)": 9,
    "3~3.5(Kg)": 8,
    "1.5~2(Kg)": 6,
    "2.5~3.0(Kg)": 5,
    "1,7(Kg)": 3,
    "2~2.5(Kg)": 3,
    "2.2~2.5(Kg)": 2,
    "12..00(Kg)": 1,
    "12...00(Kg)": 1,
    "4,58(Kg)": 1,
    "7,52(Kg)": 1,
    "5..56(Kg)": 1,
    "1,5(Kg)": 1,
    "1,3(Kg)": 1,
    "1,6(Kg)": 1,
    "6,4(Kg)": 1,
    "24,2(Kg)": 1,
    "7,2(Kg)": 1,
    "1,1(Kg)": 1,
    "6,3(Kg)": 1
  },
  "zero_count": 11,
  "negative_count": 0,
  "over_100kg_candidate": 0,
  "extreme_definition": ">100kg diagnostic candidate, not a correction rule"
}
```

Chosen: Strict decimal (Kg) parser; unknown remains null; report anomalies.

Rejected alternatives: fabricated defaults, unmeasured production mappings, or contract changes outside the approved scope.

Reason: retain source uncertainty and the latest user decisions.

Revisit when: live results, source documentation or human review supplies evidence.

## Age normalization

Decision: Age normalization

Evidence: Run 20260914T232312940282Z

```json
{
  "denominator_nonplaceholder": 10507,
  "parse_success": 10507,
  "parse_failure": 0,
  "parse_success_ratio": 1.0,
  "parse_failure_ratio": 0.0,
  "parseable_coverage_all_unique": 1.0,
  "distribution": {
    "count": 10507,
    "min": 2007,
    "p25": 2022.0,
    "median": 2024,
    "p75": 2026.0,
    "p95": 2026.0,
    "max": 2026,
    "mean": 2023.3992576377652
  },
  "top_invalid": {},
  "future_birth_year_count": 0,
  "observed_format_note": "Year-only and exact (60일미만)(년생) forms supported after live observation; no birth date inferred. Compare year_only_parser_coverage in observations."
}
```

Chosen: Extract birth_year from observed YYYY(년생) and YYYY(60일미만)(년생) forms. Retain age_text and do not infer a birthday. Empty year stays null.

Rejected alternatives: fabricated defaults, unmeasured production mappings, or contract changes outside the approved scope.

Reason: retain source uncertainty and the latest user decisions.

Revisit when: live results, source documentation or human review supplies evidence.

## Sex mapping

Decision: Sex mapping

Evidence: Run 20260914T232312940282Z

```json
{
  "M": 5239,
  "F": 5162,
  "Q": 106
}
```

Chosen: Source mapping proposal: M→male, F→female, Q→unknown; preserve raw values. Public enum unchanged.

Rejected alternatives: fabricated defaults, unmeasured production mappings, or contract changes outside the approved scope.

Reason: retain source uncertainty and the latest user decisions.

Revisit when: live results, source documentation or human review supplies evidence.

## Neuter mapping

Decision: Neuter mapping

Evidence: Run 20260914T232312940282Z

```json
{
  "N": 6731,
  "U": 2990,
  "Y": 786
}
```

Chosen: Source mapping proposal: Y→yes, N→no, U→unknown; preserve raw values. Public enum unchanged.

Rejected alternatives: fabricated defaults, unmeasured production mappings, or contract changes outside the approved scope.

Reason: retain source uncertainty and the latest user decisions.

Revisit when: live results, source documentation or human review supplies evidence.

## processState handling

Decision: processState handling

Evidence: Run 20260914T232312940282Z

```json
{
  "policy_version": "notice-start-10-calendar-days-v1",
  "as_of_date": "2026-09-15",
  "timezone": "Asia/Seoul (UTC+09:00)",
  "rule": "source processState=보호중 and today-noticeSdt >= 10 calendar days → 입양 가능",
  "display_state_frequencies": {
    "종료(입양)": 1569,
    "종료(안락사)": 760,
    "종료(자연사)": 843,
    "입양 가능": 3909,
    "종료(반환)": 1849,
    "보호중": 1189,
    "종료(기증)": 388
  },
  "issues": {},
  "note": "User-defined display label, not a new upstream state or shelter confirmation. noticeEdt and happenDt do not replace noticeSdt. Source payload unchanged. animals_active remains a separate launch decision."
}
```

Chosen: For raw processState=보호중 only: today-noticeSdt >= 10 calendar days displays 입양 가능; earlier dates display 보호중. Other source states remain unchanged. Preserve the raw source value.

Rejected alternatives: fabricated defaults, unmeasured production mappings, or contract changes outside the approved scope.

Reason: retain source uncertainty and the latest user decisions.

Revisit when: live results, source documentation or human review supplies evidence.

## Region source/mapping

Decision: Region source/mapping

Evidence: Run 20260914T232312940282Z

```json
{
  "source": "sido_v2.orgCd → upr_cd; sigungu_v2.orgCd → org_cd",
  "normalization_policy": {
    "sido": "sido_v2.orgCd == upr_cd",
    "sigungu": "sigungu_v2.orgCd == org_cd"
  },
  "animal_join": "Exact official organization name; whitespace normalization only. Province self-row used only when its official code equals the parent code. For ambiguous names, every original dog ID must be confirmed by scoped source animal responses with one consistent code. No fuzzy alias or shelter-address inference.",
  "mapped_dogs": 10507,
  "unresolved_dogs": 0,
  "ambiguous_dogs": 0,
  "unresolved_organization_counts": {},
  "ambiguous_organization_counts": {},
  "organizations_confirmed_by_scoped_animal_ids": {
    "경상남도 창원시 의창성산구": 211
  },
  "scoped_animal_evidence": [
    {
      "upr_cd": "6480000",
      "org_cd": "5280000",
      "totalCount": 0,
      "rows": 0,
      "capture_sha256": "6feff202bae2d34915c5483d4aeaab2a5a1d2ecfe7be384ab26a84f1ddaa6784"
    },
    {
      "upr_cd": "6480000",
      "org_cd": "5320000",
      "totalCount": 0,
      "rows": 0,
      "capture_sha256": "17ca9886fc4ca0fc8db726acf419dd4702d52ec35ee2dc50e05509b303b3ed8c"
    },
    {
      "upr_cd": "6480000",
      "org_cd": "5670000",
      "totalCount": 657,
      "rows": 657,
      "capture_sha256": "281d4eddfb309ef91edd50edb582c6a2bab6ead89ff8a40ab2031d5b210bd9fc"
    }
  ],
  "organization_code_mapping": {
    "강원특별자치도 강릉시": {
      "sido": "6530000",
      "sigungu": "4201000",
      "upr_cd": "6530000",
      "org_cd": "4201000"
    },
    "강원특별자치도 고성군": {
      "sido": "6530000",
      "sigungu": "4341000",
      "upr_cd": "6530000",
      "org_cd": "4341000"
    },
    "강원특별자치도 동해시": {
      "sido": "6530000",
      "sigungu": "4211000",
      "upr_cd": "6530000",
      "org_cd": "4211000"
    },
    "강원특별자치도 삼척시": {
      "sido": "6530000",
      "sigungu": "4241000",
      "upr_cd": "6530000",
      "org_cd": "4241000"
    },
    "강원특별자치도 속초시": {
      "sido": "6530000",
      "sigungu": "4231000",
      "upr_cd": "6530000",
      "org_cd": "4231000"
    },
    "강원특별자치도 양구군": {
      "sido": "6530000",
      "sigungu": "4321000",
      "upr_cd": "6530000",
      "org_cd": "4321000"
    },
    "강원특별자치도 양양군": {
      "sido": "6530000",
      "sigungu": "4351000",
      "upr_cd": "6530000",
      "org_cd": "4351000"
    },
    "강원특별자치도 영월군": {
      "sido": "6530000",
      "sigungu": "4271000",
      "upr_cd": "6530000",
      "org_cd": "4271000"
    },
    "강원특별자치도 원주시": {
      "sido": "6530000",
      "sigungu": "4191000",
      "upr_cd": "6530000",
      "org_cd": "4191000"
    },
    "강원특별자치도 인제군": {
      "sido": "6530000",
      "sigungu": "4331000",
      "upr_cd": "6530000",
      "org_cd": "4331000"
    },
    "강원특별자치도 정선군": {
      "sido": "6530000",
      "sigungu": "4291000",
      "upr_cd": "6530000",
      "org_cd": "4291000"
    },
    "강원특별자치도 철원군": {
      "sido": "6530000",
      "sigungu": "4301000",
      "upr_cd": "6530000",
      "org_cd": "4301000"
    },
    "강원특별자치도 춘천시": {
      "sido": "6530000",
      "sigungu": "4181000",
      "upr_cd": "6530000",
      "org_cd": "4181000"
    },
    "강원특별자치도 태백시": {
      "sido": "6530000",
      "sigungu": "4221000",
      "upr_cd": "6530000",
      "org_cd": "4221000"
    },
    "강원특별자치도 평창군": {
      "sido": "6530000",
      "sigungu": "4281000",
      "upr_cd": "6530000",
      "org_cd": "4281000"
    },
    "강원특별자치도 홍천군": {
      "sido": "6530000",
      "sigungu": "4251000",
      "upr_cd": "6530000",
      "org_cd": "4251000"
    },
    "강원특별자치도 화천군": {
      "sido": "6530000",
      "sigungu": "4311000",
      "upr_cd": "6530000",
      "org_cd": "4311000"
    },
    "강원특별자치도 횡성군": {
      "sido": "6530000",
      "sigungu": "4261000",
      "upr_cd": "6530000",
      "org_cd": "4261000"
    },
    "경기도 가평군": {
      "sido": "6410000",
      "sigungu": "4160000",
      "upr_cd": "6410000",
      "org_cd": "4160000"
    },
    "경기도 고양시": {
      "sido": "6410000",
      "sigungu": "3940000",
      "upr_cd": "6410000",
      "org_cd": "3940000"
    },
    "경기도 과천시": {
      "sido": "6410000",
      "sigungu": "3970000",
      "upr_cd": "6410000",
      "org_cd": "3970000"
    },
    "경기도 광명시": {
      "sido": "6410000",
      "sigungu": "3900000",
      "upr_cd": "6410000",
      "org_cd": "3900000"
    },
    "경기도 광주시": {
      "sido": "6410000",
      "sigungu": "5540000",
      "upr_cd": "6410000",
      "org_cd": "5540000"
    },
    "경기도 구리시": {
      "sido": "6410000",
      "sigungu": "3980000",
      "upr_cd": "6410000",
      "org_cd": "3980000"
    },
    "경기도 군포시": {
      "sido": "6410000",
      "sigungu": "4020000",
      "upr_cd": "6410000",
      "org_cd": "4020000"
    },
    "경기도 김포시": {
      "sido": "6410000",
      "sigungu": "4090000",
      "upr_cd": "6410000",
      "org_cd": "4090000"
    },
    "경기도 남양주시": {
      "sido": "6410000",
      "sigungu": "3990000",
      "upr_cd": "6410000",
      "org_cd": "3990000"
    },
    "경기도 동두천시": {
      "sido": "6410000",
      "sigungu": "3920000",
      "upr_cd": "6410000",
      "org_cd": "3920000"
    },
    "경기도 부천시": {
      "sido": "6410000",
      "sigungu": "3860000",
      "upr_cd": "6410000",
      "org_cd": "3860000"
    },
    "경기도 성남시": {
      "sido": "6410000",
      "sigungu": "3780000",
      "upr_cd": "6410000",
      "org_cd": "3780000"
    },
    "경기도 수원시": {
      "sido": "6410000",
      "sigungu": "3740000",
      "upr_cd": "6410000",
      "org_cd": "3740000"
    },
    "경기도 시흥시": {
      "sido": "6410000",
      "sigungu": "4010000",
      "upr_cd": "6410000",
      "org_cd": "4010000"
    },
    "경기도 안산시": {
      "sido": "6410000",
      "sigungu": "3930000",
      "upr_cd": "6410000",
      "org_cd": "3930000"
    },
    "경기도 안성시": {
      "sido": "6410000",
      "sigungu": "4080000",
      "upr_cd": "6410000",
      "org_cd": "4080000"
    },
    "경기도 안양시": {
      "sido": "6410000",
      "sigungu": "3830000",
      "upr_cd": "6410000",
      "org_cd": "3830000"
    },
    "경기도 양주시": {
      "sido": "6410000",
      "sigungu": "5590000",
      "upr_cd": "6410000",
      "org_cd": "5590000"
    },
    "경기도 양평군": {
      "sido": "6410000",
      "sigungu": "4170000",
      "upr_cd": "6410000",
      "org_cd": "4170000"
    },
    "경기도 여주시": {
      "sido": "6410000",
      "sigungu": "5700000",
      "upr_cd": "6410000",
      "org_cd": "5700000"
    },
    "경기도 연천군": {
      "sido": "6410000",
      "sigungu": "4140000",
      "upr_cd": "6410000",
      "org_cd": "4140000"
    },
    "경기도 오산시": {
      "sido": "6410000",
      "sigungu": "4000000",
      "upr_cd": "6410000",
      "org_cd": "4000000"
    },
    "경기도 용인시": {
      "sido": "6410000",
      "sigungu": "4050000",
      "upr_cd": "6410000",
      "org_cd": "4050000"
    },
    "경기도 의왕시": {
      "sido": "6410000",
      "sigungu": "4030000",
      "upr_cd": "6410000",
      "org_cd": "4030000"
    },
    "경기도 의정부시": {
      "sido": "6410000",
      "sigungu": "3820000",
      "upr_cd": "6410000",
      "org_cd": "3820000"
    },
    "경기도 이천시": {
      "sido": "6410000",
      "sigungu": "4070000",
      "upr_cd": "6410000",
      "org_cd": "4070000"
    },
    "경기도 파주시": {
      "sido": "6410000",
      "sigungu": "4060000",
      "upr_cd": "6410000",
      "org_cd": "4060000"
    },
    "경기도 평택시": {
      "sido": "6410000",
      "sigungu": "3910000",
      "upr_cd": "6410000",
      "org_cd": "3910000"
    },
    "경기도 포천시": {
      "sido": "6410000",
      "sigungu": "5600000",
      "upr_cd": "6410000",
      "org_cd": "5600000"
    },
    "경기도 하남시": {
      "sido": "6410000",
      "sigungu": "4040000",
      "upr_cd": "6410000",
      "org_cd": "4040000"
    },
    "경기도 화성시": {
      "sido": "6410000",
      "sigungu": "5530000",
      "upr_cd": "6410000",
      "org_cd": "5530000"
    },
    "경상남도 거제시": {
      "sido": "6480000",
      "sigungu": "5370000",
      "upr_cd": "6480000",
      "org_cd": "5370000"
    },
    "경상남도 거창군": {
      "sido": "6480000",
      "sigungu": "5470000",
      "upr_cd": "6480000",
      "org_cd": "5470000"
    },
    "경상남도 고성군": {
      "sido": "6480000",
      "sigungu": "5420000",
      "upr_cd": "6480000",
      "org_cd": "5420000"
    },
    "경상남도 김해시": {
      "sido": "6480000",
      "sigungu": "5350000",
      "upr_cd": "6480000",
      "org_cd": "5350000"
    },
    "경상남도 남해군": {
      "sido": "6480000",
      "sigungu": "5430000",
      "upr_cd": "6480000",
      "org_cd": "5430000"
    },
    "경상남도 밀양시": {
      "sido": "6480000",
      "sigungu": "5360000",
      "upr_cd": "6480000",
      "org_cd": "5360000"
    },
    "경상남도 사천시": {
      "sido": "6480000",
      "sigungu": "5340000",
      "upr_cd": "6480000",
      "org_cd": "5340000"
    },
    "경상남도 산청군": {
      "sido": "6480000",
      "sigungu": "5450000",
      "upr_cd": "6480000",
      "org_cd": "5450000"
    },
    "경상남도 양산시": {
      "sido": "6480000",
      "sigungu": "5380000",
      "upr_cd": "6480000",
      "org_cd": "5380000"
    },
    "경상남도 의령군": {
      "sido": "6480000",
      "sigungu": "5390000",
      "upr_cd": "6480000",
      "org_cd": "5390000"
    },
    "경상남도 진주시": {
      "sido": "6480000",
      "sigungu": "5310000",
      "upr_cd": "6480000",
      "org_cd": "5310000"
    },
    "경상남도 창녕군": {
      "sido": "6480000",
      "sigungu": "5410000",
      "upr_cd": "6480000",
      "org_cd": "5410000"
    },
    "경상남도 창원시 의창성산구": {
      "sido": "6480000",
      "sigungu": "5670000",
      "upr_cd": "6480000",
      "org_cd": "5670000"
    },
    "경상남도 통영시": {
      "sido": "6480000",
      "sigungu": "5330000",
      "upr_cd": "6480000",
      "org_cd": "5330000"
    },
    "경상남도 하동군": {
      "sido": "6480000",
      "sigungu": "5440000",
      "upr_cd": "6480000",
      "org_cd": "5440000"
    },
    "경상남도 함안군": {
      "sido": "6480000",
      "sigungu": "5400000",
      "upr_cd": "6480000",
      "org_cd": "5400000"
    },
    "경상남도 함양군": {
      "sido": "6480000",
      "sigungu": "5460000",
      "upr_cd": "6480000",
      "org_cd": "5460000"
    },
    "경상남도 합천군": {
      "sido": "6480000",
      "sigungu": "5480000",
      "upr_cd": "6480000",
      "org_cd": "5480000"
    },
    "경상북도 경산시": {
      "sido": "6470000",
      "sigungu": "5130000",
      "upr_cd": "6470000",
      "org_cd": "5130000"
    },
    "경상북도 경주시": {
      "sido": "6470000",
      "sigungu": "5050000",
      "upr_cd": "6470000",
      "org_cd": "5050000"
    },
    "경상북도 고령군": {
      "sido": "6470000",
      "sigungu": "5200000",
      "upr_cd": "6470000",
      "org_cd": "5200000"
    },
    "경상북도 구미시": {
      "sido": "6470000",
      "sigungu": "5080000",
      "upr_cd": "6470000",
      "org_cd": "5080000"
    },
    "경상북도 김천시": {
      "sido": "6470000",
      "sigungu": "5060000",
      "upr_cd": "6470000",
      "org_cd": "5060000"
    },
    "경상북도 문경시": {
      "sido": "6470000",
      "sigungu": "5120000",
      "upr_cd": "6470000",
      "org_cd": "5120000"
    },
    "경상북도 봉화군": {
      "sido": "6470000",
      "sigungu": "5240000",
      "upr_cd": "6470000",
      "org_cd": "5240000"
    },
    "경상북도 상주시": {
      "sido": "6470000",
      "sigungu": "5110000",
      "upr_cd": "6470000",
      "org_cd": "5110000"
    },
    "경상북도 성주군": {
      "sido": "6470000",
      "sigungu": "5210000",
      "upr_cd": "6470000",
      "org_cd": "5210000"
    },
    "경상북도 안동시": {
      "sido": "6470000",
      "sigungu": "5070000",
      "upr_cd": "6470000",
      "org_cd": "5070000"
    },
    "경상북도 영덕군": {
      "sido": "6470000",
      "sigungu": "5180000",
      "upr_cd": "6470000",
      "org_cd": "5180000"
    },
    "경상북도 영양군": {
      "sido": "6470000",
      "sigungu": "5170000",
      "upr_cd": "6470000",
      "org_cd": "5170000"
    },
    "경상북도 영주시": {
      "sido": "6470000",
      "sigungu": "5090000",
      "upr_cd": "6470000",
      "org_cd": "5090000"
    },
    "경상북도 영천시": {
      "sido": "6470000",
      "sigungu": "5100000",
      "upr_cd": "6470000",
      "org_cd": "5100000"
    },
    "경상북도 예천군": {
      "sido": "6470000",
      "sigungu": "5230000",
      "upr_cd": "6470000",
      "org_cd": "5230000"
    },
    "경상북도 울진군": {
      "sido": "6470000",
      "sigungu": "5250000",
      "upr_cd": "6470000",
      "org_cd": "5250000"
    },
    "경상북도 의성군": {
      "sido": "6470000",
      "sigungu": "5150000",
      "upr_cd": "6470000",
      "org_cd": "5150000"
    },
    "경상북도 청도군": {
      "sido": "6470000",
      "sigungu": "5190000",
      "upr_cd": "6470000",
      "org_cd": "5190000"
    },
    "경상북도 청송군": {
      "sido": "6470000",
      "sigungu": "5160000",
      "upr_cd": "6470000",
      "org_cd": "5160000"
    },
    "경상북도 칠곡군": {
      "sido": "6470000",
      "sigungu": "5220000",
      "upr_cd": "6470000",
      "org_cd": "5220000"
    },
    "경상북도 포항시": {
      "sido": "6470000",
      "sigungu": "5020000",
      "upr_cd": "6470000",
      "org_cd": "5020000"
    },
    "대구광역시 군위군": {
      "sido": "6270000",
      "sigungu": "5141000",
      "upr_cd": "6270000",
      "org_cd": "5141000"
    },
    "대구광역시 남구": {
      "sido": "6270000",
      "sigungu": "3440000",
      "upr_cd": "6270000",
      "org_cd": "3440000"
    },
    "대구광역시 달서구": {
      "sido": "6270000",
      "sigungu": "3470000",
      "upr_cd": "6270000",
      "org_cd": "3470000"
    },
    "대구광역시 달성군": {
      "sido": "6270000",
      "sigungu": "3480000",
      "upr_cd": "6270000",
      "org_cd": "3480000"
    },
    "대구광역시 동구": {
      "sido": "6270000",
      "sigungu": "3420000",
      "upr_cd": "6270000",
      "org_cd": "3420000"
    },
    "대구광역시 북구": {
      "sido": "6270000",
      "sigungu": "3450000",
      "upr_cd": "6270000",
      "org_cd": "3450000"
    },
    "대구광역시 서구": {
      "sido": "6270000",
      "sigungu": "3430000",
      "upr_cd": "6270000",
      "org_cd": "3430000"
    },
    "대구광역시 수성구": {
      "sido": "6270000",
      "sigungu": "3460000",
      "upr_cd": "6270000",
      "org_cd": "3460000"
    },
    "대구광역시 중구": {
      "sido": "6270000",
      "sigungu": "3410000",
      "upr_cd": "6270000",
      "org_cd": "3410000"
    },
    "대전광역시 대덕구": {
      "sido": "6300000",
      "sigungu": "3680000",
      "upr_cd": "6300000",
      "org_cd": "3680000"
    },
    "대전광역시 동구": {
      "sido": "6300000",
      "sigungu": "3640000",
      "upr_cd": "6300000",
      "org_cd": "3640000"
    },
    "대전광역시 서구": {
      "sido": "6300000",
      "sigungu": "3660000",
      "upr_cd": "6300000",
      "org_cd": "3660000"
    },
    "대전광역시 유성구": {
      "sido": "6300000",
      "sigungu": "3670000",
      "upr_cd": "6300000",
      "org_cd": "3670000"
    },
    "대전광역시 중구": {
      "sido": "6300000",
      "sigungu": "3650000",
      "upr_cd": "6300000",
      "org_cd": "3650000"
    },
    "부산광역시 강서구": {
      "sido": "6260000",
      "sigungu": "3360000",
      "upr_cd": "6260000",
      "org_cd": "3360000"
    },
    "부산광역시 금정구": {
      "sido": "6260000",
      "sigungu": "3350000",
      "upr_cd": "6260000",
      "org_cd": "3350000"
    },
    "부산광역시 기장군": {
      "sido": "6260000",
      "sigungu": "3400000",
      "upr_cd": "6260000",
      "org_cd": "3400000"
    },
    "부산광역시 남구": {
      "sido": "6260000",
      "sigungu": "3310000",
      "upr_cd": "6260000",
      "org_cd": "3310000"
    },
    "부산광역시 동구": {
      "sido": "6260000",
      "sigungu": "3270000",
      "upr_cd": "6260000",
      "org_cd": "3270000"
    },
    "부산광역시 동래구": {
      "sido": "6260000",
      "sigungu": "3300000",
      "upr_cd": "6260000",
      "org_cd": "3300000"
    },
    "부산광역시 부산진구": {
      "sido": "6260000",
      "sigungu": "3290000",
      "upr_cd": "6260000",
      "org_cd": "3290000"
    },
    "부산광역시 북구": {
      "sido": "6260000",
      "sigungu": "3320000",
      "upr_cd": "6260000",
      "org_cd": "3320000"
    },
    "부산광역시 사상구": {
      "sido": "6260000",
      "sigungu": "3390000",
      "upr_cd": "6260000",
      "org_cd": "3390000"
    },
    "부산광역시 사하구": {
      "sido": "6260000",
      "sigungu": "3340000",
      "upr_cd": "6260000",
      "org_cd": "3340000"
    },
    "부산광역시 서구": {
      "sido": "6260000",
      "sigungu": "3260000",
      "upr_cd": "6260000",
      "org_cd": "3260000"
    },
    "부산광역시 수영구": {
      "sido": "6260000",
      "sigungu": "3380000",
      "upr_cd": "6260000",
      "org_cd": "3380000"
    },
    "부산광역시 연제구": {
      "sido": "6260000",
      "sigungu": "3370000",
      "upr_cd": "6260000",
      "org_cd": "3370000"
    },
    "부산광역시 영도구": {
      "sido": "6260000",
      "sigungu": "3280000",
      "upr_cd": "6260000",
      "org_cd": "3280000"
    },
    "부산광역시 중구": {
      "sido": "6260000",
      "sigungu": "3250000",
      "upr_cd": "6260000",
      "org_cd": "3250000"
    },
    "부산광역시 해운대구": {
      "sido": "6260000",
      "sigungu": "3330000",
      "upr_cd": "6260000",
      "org_cd": "3330000"
    },
    "서울특별시 강남구": {
      "sido": "6110000",
      "sigungu": "3220000",
      "upr_cd": "6110000",
      "org_cd": "3220000"
    },
    "서울특별시 강동구": {
      "sido": "6110000",
      "sigungu": "3240000",
      "upr_cd": "6110000",
      "org_cd": "3240000"
    },
    "서울특별시 강북구": {
      "sido": "6110000",
      "sigungu": "3080000",
      "upr_cd": "6110000",
      "org_cd": "3080000"
    },
    "서울특별시 강서구": {
      "sido": "6110000",
      "sigungu": "3150000",
      "upr_cd": "6110000",
      "org_cd": "3150000"
    },
    "서울특별시 관악구": {
      "sido": "6110000",
      "sigungu": "3200000",
      "upr_cd": "6110000",
      "org_cd": "3200000"
    },
    "서울특별시 광진구": {
      "sido": "6110000",
      "sigungu": "3040000",
      "upr_cd": "6110000",
      "org_cd": "3040000"
    },
    "서울특별시 구로구": {
      "sido": "6110000",
      "sigungu": "3160000",
      "upr_cd": "6110000",
      "org_cd": "3160000"
    },
    "서울특별시 금천구": {
      "sido": "6110000",
      "sigungu": "3170000",
      "upr_cd": "6110000",
      "org_cd": "3170000"
    },
    "서울특별시 노원구": {
      "sido": "6110000",
      "sigungu": "3100000",
      "upr_cd": "6110000",
      "org_cd": "3100000"
    },
    "서울특별시 도봉구": {
      "sido": "6110000",
      "sigungu": "3090000",
      "upr_cd": "6110000",
      "org_cd": "3090000"
    },
    "서울특별시 동대문구": {
      "sido": "6110000",
      "sigungu": "3050000",
      "upr_cd": "6110000",
      "org_cd": "3050000"
    },
    "서울특별시 동작구": {
      "sido": "6110000",
      "sigungu": "3190000",
      "upr_cd": "6110000",
      "org_cd": "3190000"
    },
    "서울특별시 마포구": {
      "sido": "6110000",
      "sigungu": "3130000",
      "upr_cd": "6110000",
      "org_cd": "3130000"
    },
    "서울특별시 서대문구": {
      "sido": "6110000",
      "sigungu": "3120000",
      "upr_cd": "6110000",
      "org_cd": "3120000"
    },
    "서울특별시 서초구": {
      "sido": "6110000",
      "sigungu": "3210000",
      "upr_cd": "6110000",
      "org_cd": "3210000"
    },
    "서울특별시 성동구": {
      "sido": "6110000",
      "sigungu": "3030000",
      "upr_cd": "6110000",
      "org_cd": "3030000"
    },
    "서울특별시 성북구": {
      "sido": "6110000",
      "sigungu": "3070000",
      "upr_cd": "6110000",
      "org_cd": "3070000"
    },
    "서울특별시 송파구": {
      "sido": "6110000",
      "sigungu": "3230000",
      "upr_cd": "6110000",
      "org_cd": "3230000"
    },
    "서울특별시 양천구": {
      "sido": "6110000",
      "sigungu": "3140000",
      "upr_cd": "6110000",
      "org_cd": "3140000"
    },
    "서울특별시 영등포구": {
      "sido": "6110000",
      "sigungu": "3180000",
      "upr_cd": "6110000",
      "org_cd": "3180000"
    },
    "서울특별시 용산구": {
      "sido": "6110000",
      "sigungu": "3020000",
      "upr_cd": "6110000",
      "org_cd": "3020000"
    },
    "서울특별시 은평구": {
      "sido": "6110000",
      "sigungu": "3110000",
      "upr_cd": "6110000",
      "org_cd": "3110000"
    },
    "서울특별시 종로구": {
      "sido": "6110000",
      "sigungu": "3000000",
      "upr_cd": "6110000",
      "org_cd": "3000000"
    },
    "서울특별시 중구": {
      "sido": "6110000",
      "sigungu": "3010000",
      "upr_cd": "6110000",
      "org_cd": "3010000"
    },
    "서울특별시 중랑구": {
      "sido": "6110000",
      "sigungu": "3060000",
      "upr_cd": "6110000",
      "org_cd": "3060000"
    },
    "세종특별자치시": {
      "sido": "5690000",
      "sigungu": "5690000",
      "upr_cd": "5690000",
      "org_cd": "5690000"
    },
    "울산광역시 남구": {
      "sido": "6310000",
      "sigungu": "3700000",
      "upr_cd": "6310000",
      "org_cd": "3700000"
    },
    "울산광역시 동구": {
      "sido": "6310000",
      "sigungu": "3710000",
      "upr_cd": "6310000",
      "org_cd": "3710000"
    },
    "울산광역시 북구": {
      "sido": "6310000",
      "sigungu": "3720000",
      "upr_cd": "6310000",
      "org_cd": "3720000"
    },
    "울산광역시 울주군": {
      "sido": "6310000",
      "sigungu": "3730000",
      "upr_cd": "6310000",
      "org_cd": "3730000"
    },
    "울산광역시 중구": {
      "sido": "6310000",
      "sigungu": "3690000",
      "upr_cd": "6310000",
      "org_cd": "3690000"
    },
    "인천광역시 강화군": {
      "sido": "6280000",
      "sigungu": "3570000",
      "upr_cd": "6280000",
      "org_cd": "3570000"
    },
    "인천광역시 검단구": {
      "sido": "6280000",
      "sigungu": "3565000",
      "upr_cd": "6280000",
      "org_cd": "3565000"
    },
    "인천광역시 계양구": {
      "sido": "6280000",
      "sigungu": "3550000",
      "upr_cd": "6280000",
      "org_cd": "3550000"
    },
    "인천광역시 남동구": {
      "sido": "6280000",
      "sigungu": "3530000",
      "upr_cd": "6280000",
      "org_cd": "3530000"
    },
    "인천광역시 미추홀구": {
      "sido": "6280000",
      "sigungu": "3510500",
      "upr_cd": "6280000",
      "org_cd": "3510500"
    },
    "인천광역시 부평구": {
      "sido": "6280000",
      "sigungu": "3540000",
      "upr_cd": "6280000",
      "org_cd": "3540000"
    },
    "인천광역시 서해구": {
      "sido": "6280000",
      "sigungu": "3561000",
      "upr_cd": "6280000",
      "org_cd": "3561000"
    },
    "인천광역시 연수구": {
      "sido": "6280000",
      "sigungu": "3520000",
      "upr_cd": "6280000",
      "org_cd": "3520000"
    },
    "인천광역시 영종구": {
      "sido": "6280000",
      "sigungu": "3491000",
      "upr_cd": "6280000",
      "org_cd": "3491000"
    },
    "인천광역시 옹진군": {
      "sido": "6280000",
      "sigungu": "3580000",
      "upr_cd": "6280000",
      "org_cd": "3580000"
    },
    "인천광역시 제물포구": {
      "sido": "6280000",
      "sigungu": "3501000",
      "upr_cd": "6280000",
      "org_cd": "3501000"
    },
    "전남광주통합특별시 강진군": {
      "sido": "6130000",
      "sigungu": "5865000",
      "upr_cd": "6130000",
      "org_cd": "5865000"
    },
    "전남광주통합특별시 고흥군": {
      "sido": "6130000",
      "sigungu": "5845000",
      "upr_cd": "6130000",
      "org_cd": "5845000"
    },
    "전남광주통합특별시 곡성군": {
      "sido": "6130000",
      "sigungu": "5835000",
      "upr_cd": "6130000",
      "org_cd": "5835000"
    },
    "전남광주통합특별시 광산구": {
      "sido": "6130000",
      "sigungu": "5825000",
      "upr_cd": "6130000",
      "org_cd": "5825000"
    },
    "전남광주통합특별시 광양시": {
      "sido": "6130000",
      "sigungu": "5800000",
      "upr_cd": "6130000",
      "org_cd": "5800000"
    },
    "전남광주통합특별시 구례군": {
      "sido": "6130000",
      "sigungu": "5840000",
      "upr_cd": "6130000",
      "org_cd": "5840000"
    },
    "전남광주통합특별시 나주시": {
      "sido": "6130000",
      "sigungu": "5795000",
      "upr_cd": "6130000",
      "org_cd": "5795000"
    },
    "전남광주통합특별시 남구": {
      "sido": "6130000",
      "sigungu": "5815000",
      "upr_cd": "6130000",
      "org_cd": "5815000"
    },
    "전남광주통합특별시 담양군": {
      "sido": "6130000",
      "sigungu": "5830000",
      "upr_cd": "6130000",
      "org_cd": "5830000"
    },
    "전남광주통합특별시 동구": {
      "sido": "6130000",
      "sigungu": "5805000",
      "upr_cd": "6130000",
      "org_cd": "5805000"
    },
    "전남광주통합특별시 목포시": {
      "sido": "6130000",
      "sigungu": "5780000",
      "upr_cd": "6130000",
      "org_cd": "5780000"
    },
    "전남광주통합특별시 무안군": {
      "sido": "6130000",
      "sigungu": "5880000",
      "upr_cd": "6130000",
      "org_cd": "5880000"
    },
    "전남광주통합특별시 보성군": {
      "sido": "6130000",
      "sigungu": "5850000",
      "upr_cd": "6130000",
      "org_cd": "5850000"
    },
    "전남광주통합특별시 북구": {
      "sido": "6130000",
      "sigungu": "5820000",
      "upr_cd": "6130000",
      "org_cd": "5820000"
    },
    "전남광주통합특별시 서구": {
      "sido": "6130000",
      "sigungu": "5810000",
      "upr_cd": "6130000",
      "org_cd": "5810000"
    },
    "전남광주통합특별시 순천시": {
      "sido": "6130000",
      "sigungu": "5790000",
      "upr_cd": "6130000",
      "org_cd": "5790000"
    },
    "전남광주통합특별시 신안군": {
      "sido": "6130000",
      "sigungu": "5910000",
      "upr_cd": "6130000",
      "org_cd": "5910000"
    },
    "전남광주통합특별시 여수시": {
      "sido": "6130000",
      "sigungu": "5785000",
      "upr_cd": "6130000",
      "org_cd": "5785000"
    },
    "전남광주통합특별시 영광군": {
      "sido": "6130000",
      "sigungu": "5890000",
      "upr_cd": "6130000",
      "org_cd": "5890000"
    },
    "전남광주통합특별시 영암군": {
      "sido": "6130000",
      "sigungu": "5875000",
      "upr_cd": "6130000",
      "org_cd": "5875000"
    },
    "전남광주통합특별시 완도군": {
      "sido": "6130000",
      "sigungu": "5900000",
      "upr_cd": "6130000",
      "org_cd": "5900000"
    },
    "전남광주통합특별시 장성군": {
      "sido": "6130000",
      "sigungu": "5895000",
      "upr_cd": "6130000",
      "org_cd": "5895000"
    },
    "전남광주통합특별시 진도군": {
      "sido": "6130000",
      "sigungu": "5905000",
      "upr_cd": "6130000",
      "org_cd": "5905000"
    },
    "전남광주통합특별시 함평군": {
      "sido": "6130000",
      "sigungu": "5885000",
      "upr_cd": "6130000",
      "org_cd": "5885000"
    },
    "전남광주통합특별시 해남군": {
      "sido": "6130000",
      "sigungu": "5870000",
      "upr_cd": "6130000",
      "org_cd": "5870000"
    },
    "전남광주통합특별시 화순군": {
      "sido": "6130000",
      "sigungu": "5855000",
      "upr_cd": "6130000",
      "org_cd": "5855000"
    },
    "전북특별자치도 고창군": {
      "sido": "6540000",
      "sigungu": "4781000",
      "upr_cd": "6540000",
      "org_cd": "4781000"
    },
    "전북특별자치도 군산시": {
      "sido": "6540000",
      "sigungu": "4671000",
      "upr_cd": "6540000",
      "org_cd": "4671000"
    },
    "전북특별자치도 김제시": {
      "sido": "6540000",
      "sigungu": "4711000",
      "upr_cd": "6540000",
      "org_cd": "4711000"
    },
    "전북특별자치도 남원시": {
      "sido": "6540000",
      "sigungu": "4701000",
      "upr_cd": "6540000",
      "org_cd": "4701000"
    },
    "전북특별자치도 무주군": {
      "sido": "6540000",
      "sigungu": "4741000",
      "upr_cd": "6540000",
      "org_cd": "4741000"
    },
    "전북특별자치도 부안군": {
      "sido": "6540000",
      "sigungu": "4791000",
      "upr_cd": "6540000",
      "org_cd": "4791000"
    },
    "전북특별자치도 순창군": {
      "sido": "6540000",
      "sigungu": "4771000",
      "upr_cd": "6540000",
      "org_cd": "4771000"
    },
    "전북특별자치도 완주군": {
      "sido": "6540000",
      "sigungu": "4721000",
      "upr_cd": "6540000",
      "org_cd": "4721000"
    },
    "전북특별자치도 익산시": {
      "sido": "6540000",
      "sigungu": "4681000",
      "upr_cd": "6540000",
      "org_cd": "4681000"
    },
    "전북특별자치도 임실군": {
      "sido": "6540000",
      "sigungu": "4761000",
      "upr_cd": "6540000",
      "org_cd": "4761000"
    },
    "전북특별자치도 장수군": {
      "sido": "6540000",
      "sigungu": "4751000",
      "upr_cd": "6540000",
      "org_cd": "4751000"
    },
    "전북특별자치도 전주시": {
      "sido": "6540000",
      "sigungu": "4641000",
      "upr_cd": "6540000",
      "org_cd": "4641000"
    },
    "전북특별자치도 정읍시": {
      "sido": "6540000",
      "sigungu": "4691000",
      "upr_cd": "6540000",
      "org_cd": "4691000"
    },
    "전북특별자치도 진안군": {
      "sido": "6540000",
      "sigungu": "4731000",
      "upr_cd": "6540000",
      "org_cd": "4731000"
    },
    "제주특별자치도": {
      "sido": "6500000",
      "sigungu": "6500000",
      "upr_cd": "6500000",
      "org_cd": "6500000"
    },
    "충청남도 계룡시": {
      "sido": "6440000",
      "sigungu": "5580000",
      "upr_cd": "6440000",
      "org_cd": "5580000"
    },
    "충청남도 공주시": {
      "sido": "6440000",
      "sigungu": "4500000",
      "upr_cd": "6440000",
      "org_cd": "4500000"
    },
    "충청남도 금산군": {
      "sido": "6440000",
      "sigungu": "4550000",
      "upr_cd": "6440000",
      "org_cd": "4550000"
    },
    "충청남도 논산시": {
      "sido": "6440000",
      "sigungu": "4540000",
      "upr_cd": "6440000",
      "org_cd": "4540000"
    },
    "충청남도 당진시": {
      "sido": "6440000",
      "sigungu": "5680000",
      "upr_cd": "6440000",
      "org_cd": "5680000"
    },
    "충청남도 보령시": {
      "sido": "6440000",
      "sigungu": "4510000",
      "upr_cd": "6440000",
      "org_cd": "4510000"
    },
    "충청남도 부여군": {
      "sido": "6440000",
      "sigungu": "4570000",
      "upr_cd": "6440000",
      "org_cd": "4570000"
    },
    "충청남도 서산시": {
      "sido": "6440000",
      "sigungu": "4530000",
      "upr_cd": "6440000",
      "org_cd": "4530000"
    },
    "충청남도 서천군": {
      "sido": "6440000",
      "sigungu": "4580000",
      "upr_cd": "6440000",
      "org_cd": "4580000"
    },
    "충청남도 아산시": {
      "sido": "6440000",
      "sigungu": "4520000",
      "upr_cd": "6440000",
      "org_cd": "4520000"
    },
    "충청남도 예산군": {
      "sido": "6440000",
      "sigungu": "4610000",
      "upr_cd": "6440000",
      "org_cd": "4610000"
    },
    "충청남도 천안시": {
      "sido": "6440000",
      "sigungu": "4490000",
      "upr_cd": "6440000",
      "org_cd": "4490000"
    },
    "충청남도 청양군": {
      "sido": "6440000",
      "sigungu": "4590000",
      "upr_cd": "6440000",
      "org_cd": "4590000"
    },
    "충청남도 태안군": {
      "sido": "6440000",
      "sigungu": "4620000",
      "upr_cd": "6440000",
      "org_cd": "4620000"
    },
    "충청남도 홍성군": {
      "sido": "6440000",
      "sigungu": "4600000",
      "upr_cd": "6440000",
      "org_cd": "4600000"
    },
    "충청북도 괴산군": {
      "sido": "6430000",
      "sigungu": "4460000",
      "upr_cd": "6430000",
      "org_cd": "4460000"
    },
    "충청북도 단양군": {
      "sido": "6430000",
      "sigungu": "4480000",
      "upr_cd": "6430000",
      "org_cd": "4480000"
    },
    "충청북도 보은군": {
      "sido": "6430000",
      "sigungu": "4420000",
      "upr_cd": "6430000",
      "org_cd": "4420000"
    },
    "충청북도 영동군": {
      "sido": "6430000",
      "sigungu": "4440000",
      "upr_cd": "6430000",
      "org_cd": "4440000"
    },
    "충청북도 옥천군": {
      "sido": "6430000",
      "sigungu": "4430000",
      "upr_cd": "6430000",
      "org_cd": "4430000"
    },
    "충청북도 음성군": {
      "sido": "6430000",
      "sigungu": "4470000",
      "upr_cd": "6430000",
      "org_cd": "4470000"
    },
    "충청북도 제천시": {
      "sido": "6430000",
      "sigungu": "4400000",
      "upr_cd": "6430000",
      "org_cd": "4400000"
    },
    "충청북도 증평군": {
      "sido": "6430000",
      "sigungu": "5570000",
      "upr_cd": "6430000",
      "org_cd": "5570000"
    },
    "충청북도 진천군": {
      "sido": "6430000",
      "sigungu": "4450000",
      "upr_cd": "6430000",
      "org_cd": "4450000"
    },
    "충청북도 청주시": {
      "sido": "6430000",
      "sigungu": "5710000",
      "upr_cd": "6430000",
      "org_cd": "5710000"
    },
    "충청북도 충주시": {
      "sido": "6430000",
      "sigungu": "4390000",
      "upr_cd": "6430000",
      "org_cd": "4390000"
    }
  },
  "sido_catalog_count": 16,
  "sigungu_catalog_count": 252
}
```

Chosen: Use sido_v2.orgCd as upr_cd and sigungu_v2.orgCd as org_cd. Join organization names exactly after whitespace normalization; unresolved names remain data-quality findings.

Rejected alternatives: fabricated defaults, unmeasured production mappings, or contract changes outside the approved scope.

Reason: retain source uncertainty and the latest user decisions.

Revisit when: live results, source documentation or human review supplies evidence.

## Main image policy

Decision: Main image policy

Evidence: Run 20260914T232312940282Z

```json
{
  "zero_images": 1,
  "one_image": 0,
  "two_images": 9388,
  "three_plus_images": 1118,
  "average_images_per_animal": 2.255258399162463,
  "primary_image_coverage": 0.999905,
  "duplicate_url_within_animal": 2,
  "url_schemes": {
    "http": 23762
  },
  "extensions": {
    "jpg": 21158,
    "jpeg": 1014,
    "png": 1590
  },
  "invalid_url_shape": 0,
  "nonplaceholder_url_values": 23762,
  "urls_shared_by_distinct_animals": 0,
  "url_hosts": {
    "openapi.animal.go.kr": 23762
  },
  "notes": "Primary = first valid popfile1..8 URL, deduplicated in source order. No image requests; URL coverage is not image availability."
}
```

Chosen: First valid popfile1..8 URL, source order and animal-level deduplication.

Rejected alternatives: fabricated defaults, unmeasured production mappings, or contract changes outside the approved scope.

Reason: retain source uncertainty and the latest user decisions.

Revisit when: live results, source documentation or human review supplies evidence.

## Meaningful text policy

Decision: Meaningful text policy

Evidence: Run 20260914T232312940282Z

```json
{
  "specialMark": {
    "presence_ratio": 1.0,
    "meaningful_ratio": 0.958409,
    "placeholder_ratio": 0.041591,
    "median_length_nonblank": 17,
    "p95_length_nonblank": 50.0,
    "classes": {
      "BEHAVIOR_RELATED": 4236,
      "DESCRIPTIVE": 4056,
      "HEALTH_RELATED": 671,
      "MIXED": 623,
      "ADMINISTRATIVE": 484,
      "PLACEHOLDER": 437
    },
    "behavior_candidates": 4792,
    "health_candidates": 1152,
    "administrative_candidates": 715,
    "short_text_candidates": 561,
    "negation_markers": 708
  },
  "sfeSoci": {
    "presence_ratio": 0.015609,
    "meaningful_ratio": 0.015609,
    "placeholder_ratio": 0.0,
    "median_length_nonblank": 26.5,
    "p95_length_nonblank": 35.0,
    "classes": {
      "EMPTY": 10343,
      "BEHAVIOR_RELATED": 54,
      "DESCRIPTIVE": 100,
      "MIXED": 2,
      "ADMINISTRATIVE": 8
    },
    "behavior_candidates": 56,
    "health_candidates": 0,
    "administrative_candidates": 10,
    "short_text_candidates": 0,
    "negation_markers": 0
  },
  "sfeHealth": {
    "presence_ratio": 0.014371,
    "meaningful_ratio": 0.009042,
    "placeholder_ratio": 0.00533,
    "median_length_nonblank": 8,
    "p95_length_nonblank": 39.0,
    "classes": {
      "EMPTY": 10356,
      "DESCRIPTIVE": 74,
      "HEALTH_RELATED": 18,
      "PLACEHOLDER": 56,
      "MIXED": 3
    },
    "behavior_candidates": 0,
    "health_candidates": 21,
    "administrative_candidates": 3,
    "short_text_candidates": 56,
    "negation_markers": 57
  },
  "etcBigo": {
    "presence_ratio": 0.070905,
    "meaningful_ratio": 0.0,
    "placeholder_ratio": 0.070905,
    "median_length_nonblank": 1,
    "p95_length_nonblank": 1.0,
    "classes": {
      "EMPTY": 9762,
      "PLACEHOLDER": 745
    },
    "behavior_candidates": 0,
    "health_candidates": 0,
    "administrative_candidates": 0,
    "short_text_candidates": 745,
    "negation_markers": 0
  },
  "adptnTxt": {
    "presence_ratio": 0.006091,
    "meaningful_ratio": 0.006091,
    "placeholder_ratio": 0.0,
    "median_length_nonblank": 194.0,
    "p95_length_nonblank": 194.0,
    "classes": {
      "EMPTY": 10443,
      "DESCRIPTIVE": 64
    },
    "behavior_candidates": 0,
    "health_candidates": 0,
    "administrative_candidates": 0,
    "short_text_candidates": 0,
    "negation_markers": 0
  }
}
```

Chosen: Separate empty/placeholder/admin/descriptive/health/behavior/mixed. Short-text and evidence flags overlap for words like 순함/경계; record both, without choosing production eligibility.

Rejected alternatives: fabricated defaults, unmeasured production mappings, or contract changes outside the approved scope.

Reason: retain source uncertainty and the latest user decisions.

Revisit when: live results, source documentation or human review supplies evidence.

## Personality trait eligibility

Decision: Personality trait eligibility

Evidence: Run 20260914T232312940282Z

```json
{
  "any_behavior": 0.458837,
  "any_health": 0.110974,
  "any_administrative": 0.068335,
  "behavior_and_health": 0.040449,
  "administrative_only": 0.046065,
  "only_specialMark_behavior": 0.453507,
  "sfeSoci_behavior": 0.00533,
  "adoption_description_behavior": 0.0
}
```

Chosen: Keywords are candidates, not tags. Negation and context require human review; specialMark existence is insufficient.

Rejected alternatives: fabricated defaults, unmeasured production mappings, or contract changes outside the approved scope.

Reason: retain source uncertainty and the latest user decisions.

Revisit when: live results, source documentation or human review supplies evidence.

## Health text handling

Decision: Health text handling

Evidence: Run 20260914T232312940282Z

```json
{
  "vaccinationChk": 0.159227,
  "healthChk": 0.132007,
  "sfeHealth": 0.014371
}
```

Chosen: Preserve source evidence, no diagnoses. 없음 can express a negative finding; a placeholder count does not rewrite source text.

Rejected alternatives: fabricated defaults, unmeasured production mappings, or contract changes outside the approved scope.

Reason: retain source uncertainty and the latest user decisions.

Revisit when: live results, source documentation or human review supplies evidence.

## Adoption promotion storage

Decision: Adoption promotion storage

Evidence: Run 20260914T232312940282Z

```json
{
  "fields": {
    "adptnTitle": 0.006091,
    "adptnSDate": 0.006091,
    "adptnEDate": 0.006091,
    "adptnConditionLimitTxt": 0.006091,
    "adptnTxt": 0.006091,
    "adptnImg": 0.006091
  },
  "any_ratio": 0.006091,
  "complete_ratio": 0.006091
}
```

Chosen: Preserve raw fields. Later API uses fixed nullable object shape.

Rejected alternatives: fabricated defaults, unmeasured production mappings, or contract changes outside the approved scope.

Reason: retain source uncertainty and the latest user decisions.

Revisit when: live results, source documentation or human review supplies evidence.

## Size group thresholds

Decision: Size group thresholds

Evidence: Run 20260914T232312940282Z

```json
{
  "literal_contract": {
    "tiny": 5426,
    "large": 538,
    "medium": 1970,
    "small": 2511,
    "unknown": 62
  },
  "quality_policy_candidate": {
    "tiny": 5415,
    "large": 538,
    "medium": 1970,
    "small": 2511,
    "unknown": 73
  },
  "note": "Existing contract thresholds evaluated, not finalized or changed. The proposed size counts exclude zero/negative weights; this quality policy is not approved for production. Literal contract counts are shown separately. >100kg values remain diagnostic large candidates, not validated measurements. Future birth years excluded from proposed age groups."
}
```

Chosen: Measured 5/10/20kg boundaries remain a launch proposal. Zero-weight null policy and extreme-value handling need review; no production threshold or normalizer changed.

Rejected alternatives: fabricated defaults, unmeasured production mappings, or contract changes outside the approved scope.

Reason: retain source uncertainty and the latest user decisions.

Revisit when: live results, source documentation or human review supplies evidence.

## Age group thresholds

Decision: Age group thresholds

Evidence: Run 20260914T232312940282Z

```json
{
  "puppy": 4920,
  "adult": 1770,
  "young": 3220,
  "senior": 597
}
```

Chosen: Measured approximate year-based 0–1/2–4/5–8/9+ groups remain a launch proposal. No exact attained age or production rule finalized.

Rejected alternatives: fabricated defaults, unmeasured production mappings, or contract changes outside the approved scope.

Reason: retain source uncertainty and the latest user decisions.

Revisit when: live results, source documentation or human review supplies evidence.

## animals_active definition

Decision: animals_active definition

Evidence: Run 20260914T232312940282Z

```json
{
  "protecting_only_candidate": 5098,
  "adoption_eligibility_established": false
}
```

Chosen: Definition and launch field presence require source status review.

Rejected alternatives: fabricated defaults, unmeasured production mappings, or contract changes outside the approved scope.

Reason: retain source uncertainty and the latest user decisions.

Revisit when: live results, source documentation or human review supplies evidence.

