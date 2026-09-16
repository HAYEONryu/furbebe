# API data profile

Run: 20260914T232312940282Z.

Status: collected.

## 2026-09-15 실행 요약 및 중단 판정

**Phase 0 재검증 후 실제 OpenAPI 신규 수집·분석을 완료했다. 수집·데이터 blocker는 없으며, 아래 미확정 사항을 보고하고 여기서 멈춘다.**

- 출처: [공공데이터포털 국가동물보호정보시스템 구조동물 조회 서비스](https://www.data.go.kr/data/15098931/openapi.do). 측정값은 안내 페이지의 예시가 아닌 이번 HTTPS 응답에서 집계했다.
- 수집 시각: 2026-09-15 08:23:13~08:24:40 KST. 조회 조건: 2026-01-01~2026-09-14, 지역·축종 서버 필터 없음.
- 요청/성공/실패: **17 / 17 / 0페이지**. 페이지당 1,000행, 재시도 0회, 각 페이지의 `totalCount=60,515` 일치.
- Raw **17,000행**, `desertionNo` 기준 **17,000 unique animals**. 개 10,507 / 고양이 6,098 / 기타 395; 축종 판별 불명 0. 중복·충돌·사용 불가 ID 모두 0.
- 기존 CLI의 목표 단위가 개이므로 `--target-unique 10000 --max-pages 20`을 사용했다. 고유 개 목표를 충족한 17페이지에서 종료했으며, 사용자 요청인 전체 고유 동물 5,000~20,000건 범위도 충족했다. 기존 35,999건 run과 합산하지 않았다.
- 실제 개 표본의 발견일은 **2026-07-06~2026-09-14**다. 요청 기간 전체를 조사한 결과나 무작위 전국 대표 표본으로 해석하지 않는다.
- **필드 사전은 전체 17,000행**, 아래 행동·건강·지역·상태·체중·나이 주요 통계는 **고유 개 10,507건**이 분모다. 64개 필드를 점검했고 실제 존재한 필드는 51개, 표본에서 관측되지 않은 필드는 13개다.

### 주요 측정값 — 고유 개 기준

| 항목 | 건수 / 비율 또는 분포 |
| --- | --- |
| behavior 후보 | 4,821 / 45.88% |
| health 후보 | 1,166 / 11.10% |
| administrative 후보 | 718 / 6.83%; 행정만 해당 484 |
| behavior와 health 동시 후보 | 425 / 4.04%; 복수 분류 허용 |
| 체중 파싱 | 10,445 / 10,507 = 99.41%; 실패 62, 파싱된 0kg 11 |
| 체중 분포 | min 0 / p25 2.8 / median 5 / p75 10 / p95 20.7 / max 52.05kg |
| 출생연도 파싱 | 10,507 / 10,507 = 100%; 2007~2026년, 미래 출생연도 0 |
| 나이 원문 형식 | 연도만 8,175 / 60일 미만 주석 포함 2,332; 정확한 생일·만 나이 추정 없음 |
| 기본 이미지 URL | 10,506 / 10,507 = 99.990%; URL이 없는 개 1 |
| 입양 홍보 필드 중 하나 이상 | 64 / 10,507 = 0.61% |
| 공식 지역 코드 연결 | 10,507 / 10,507 = 100%; 미매칭·다중 후보 0 |
| 원문 상태 | 보호중 5,098 / 입양 종료 1,569 / 반환 종료 1,849 / 안락사 종료 760 / 자연사 종료 843 / 기증 종료 388 |
| 사용자 표시 정책 적용 | 2026-09-15 기준 입양 가능 3,909 / 보호중 1,189; 종료 상태 유지 |

분류는 텍스트 필드별 키워드 후보 측정이다. `specialMark`의 존재율 100%와 행동 후보율은 다르며, 부정·문맥의 정확도를 검증한 성격 태그나 건강 진단이 아니다. 검토 CSV 100건은 행동/건강/행정·무의미/무작위 각 25건이며 `review_notes`는 전부 비워 두었다.

### 핵심 필드 coverage / unique / parsing — 전체 동물 기준

| 필드 | 존재 건수 / 17,000 | 존재율 | distinct 값 수 | 파싱 성공 / 대상 |
| --- | --- | --- | --- | --- |
| desertionNo | 17,000 | 100% | 17,000 | 해당 없음 |
| specialMark | 17,000 | 100% | 11,477 | 해당 없음 |
| sfeSoci | 236 | 1.39% | 85 | 해당 없음 |
| sfeHealth | 224 | 1.32% | 48 | 해당 없음 |
| etcBigo | 755 | 4.44% | 1 | 전부 placeholder |
| adptnTxt | 94 | 0.55% | 1 | 해당 없음 |
| weight | 17,000 | 100% | 934 | 16,897 / 17,000 = 99.39% |
| age | 17,000 | 100% | 22 | 16,999 / 17,000 = 99.994% |
| careRegNo | 17,000 | 100% | 300 | 해당 없음 |
| orgNm | 17,000 | 100% | 228 | 원문 distinct; 개의 코드 연결은 위 표 참조 |
| popfile1 | 16,999 | 99.994% | 16,999 | URL 형식 16,999 / 16,999 |

존재율은 비어 있지 않거나 의미 있는 값의 비율을 뜻하지 않는다. 전체 64필드의 type·missing·null·blank·placeholder·distinct·길이·parsing과 비식별 예시는 [필드 사전](api-field-dictionary.md), enum 전체 값과 빈도는 아래 8절에 있다.

### Blocker와 남은 결정사항

| 구분 | 결과 / 영향 |
| --- | --- |
| 수집·데이터 blocker | **없음**. ID 신뢰성, 응답 shape, 축종 구분, 파서 실행, 표본 수, 개의 지역 코드 연결 검증 통과 |
| Launch 전 결정 필요 | **size_group 경계, age_group 경계, animals_active 정의**는 미확정. 이 실행에서 확정하지 않았다. |
| 태그 품질 검토 | 사람이 검토할 표본 100건 대기. 45.88% 후보율만으로 태그 품질이나 production 적합성을 확정하지 않는다. |
| 시간대 | `updTm`의 시간대 미확인. 날짜 단위 차이를 집계했으며 절대 업데이트 지연을 단정하지 않는다. |
| 보존한 데이터 품질 이슈 | 개 체중 파싱 실패 62·0kg 11, 발견일이 공고 종료일보다 늦은 개 264, 지역 원문 prefix 차이 2,318. 원문 보존 및 nullable 처리를 검토할 항목이다. |
| 참조 목록 누락 | 캐시의 품종 목록에 없는 코드 6개/개 531건, 관할별 보호소 목록에 없는 코드 11개/개 479건. 원문 코드·이름 유지; 폐지·변경 원인 미확인 |
| 중단 범위 | 보고서·검토 자료 작성까지 완료. Phase 2는 시작하지 않았다. |

공식 코드 목록은 2026-09-14 09:14~13:40 KST에 수집한 캐시 247개 조회 범위를 재사용했다. 날짜 조건이 바뀐 창원 지역의 모호한 명칭은 추가 동물 조회 3페이지로 ID를 대조하여 이번 표본 211건을 확인했다. 이 추가 조회의 raw는 지역 연결 증거이며 본 표본 17,000건에 합산하지 않았다. [참조 검증 보고서](api-reference-data-profile.md)에 원본 checksum과 연결 근거가 있다.

### 실행 및 검증 근거

```powershell
.\.venv\Scripts\python.exe -m backend.jobs.animal_sync.profiling --target-unique 10000 --min-unique 5000 --page-size 1000 --max-pages 20 --request-interval 1 --seed 20260915 --start-date 20260101 --end-date 20260914
.\.venv\Scripts\python.exe -m backend.jobs.animal_sync.references --input .local/profiling/20260914T232312940282Z/raw-20260914T232312940282Z.jsonl --fetch-missing --as-of 2026-09-15
.\.venv\Scripts\python.exe -m backend.jobs.animal_sync.profiling --input .local/profiling/20260914T232312940282Z/raw-20260914T232312940282Z.jsonl
```

- `ruff check .` 통과; `pytest backend/tests -q` **139 passed**; `pip check` 통과. 소스 코드는 수정하지 않았다.
- 네트워크 호출을 차단한 재실행에서 참조 분석 결과가 일치했고 캐시 247회 재사용·네트워크 0회를 확인했다. 프로파일링 exit code 0, 생성 보고서 3개·summary·통계 CSV·검토 CSV의 바이트가 재실행 전후 동일했다. 이 상단 실행 요약은 그 검증 후 추가한 설명이다.
- 17개 원본 페이지에서 ID·건수·totalCount·성공 header를 별도로 대조했고 SHA-256이 `run.json`과 일치했다. 문장 분류·표시 상태·필드 presence 합계와 검토 표본 100개 고유 ID를 확인했다.
- 원본 SHA-256: `866801be3c2bda927a0d292b4c43df0dfab1fcabc6fd7e07dcd0271b24c9de92`.
- 원본·행 단위 자료·`verification.json`은 `.local/profiling/20260914T232312940282Z/`에 저장했다. `.env`·원본은 Git 제외이며 보고서와 새 run 파일에서 현재 인증키 일치는 발견되지 않았다.

---

## Measured findings / 주요 결과

- Raw 17,000; unique animals 17,000; unique dogs 10,507.
- Duplicate rows 0; conflicting IDs 0; unusable IDs 0.
- Behavior candidates 45.88%; health 11.10%; administrative 6.83%. Multi-label candidates, not confirmed traits or diagnoses.
- Primary image URL coverage 99.990% (10,506/10,507); image availability and HTTPS support were not tested.
- Weight syntax parse 99.41%; zero weights 11; >100kg candidates 0. No correction applied.
- Age parse 100.00%; original age_text retained.
- Any adoption promotion 0.61%; nullable detail object remains appropriate.
- Requested date range and sampled date range differ; target-based collection is not an exhaustive population census.
- Human review notes are blank. Region code mapping and the 10-calendar-day protecting-status display policy are decided; unresolved joins remain data-quality findings. No Phase 2 implementation.

### 결과 해석

- 지역 세 원문의 시도 prefix가 다른 개는 2,318건입니다. 관할 기관과 보호소 소재지, 옛 명칭과 새 명칭의 차이가 섞여 있어 모두 데이터 오류로 단정할 수 없습니다. 사용자 결정에 따라 공식 코드 목록으로 연결하며, 실제 매칭 결과는 참조 코드 보고서를 확인합니다.
- 발견일이 공고 종료일보다 늦은 자료 264건, 품종명과 전체 품종명 문자열 불일치 80건을 보존했습니다. 문자열 불일치가 동물종 판별 오류를 뜻하지는 않습니다.
- 행동 후보 coverage는 후보 문장의 존재 비율입니다. 30–60% 구간은 명세의 선택적 trait 탐색 검토 구간이며, 검토 없이 성격 태그를 부여할 근거가 아닙니다.
- 입양 홍보 문구는 개별 동물 설명인지 보호소 공통 안내인지 확인해야 합니다. 낮은 coverage는 계약의 nullable adoption_promotion을 유지할 근거입니다.
- 이미지 URL의 HTTP/HTTPS 분포와 실제 브라우저 표시 가능성은 별개입니다. 이미지는 내려받지 않았으며 HTTP 주소를 HTTPS로 임의 변경하지 않았습니다.
- updTm에는 시간대가 없어 절대적인 업데이트 지연은 미확정입니다. 원문 날짜와 분석 기준일의 달력 날짜 차이만 별도로 집계합니다.


## 1. 실행 날짜 / API endpoint

```json
{
  "endpoint": "https://apis.data.go.kr/1543061/abandonmentPublicService_v2/abandonmentPublic_v2",
  "as_of": "2026-09-15",
  "run": {
    "run_id": "20260914T232312940282Z",
    "started_at": "2026-09-14T23:23:13.009500+00:00",
    "endpoint": "https://apis.data.go.kr/1543061/abandonmentPublicService_v2/abandonmentPublic_v2",
    "query_without_key": {
      "bgnde": "20260101",
      "endde": "20260914"
    },
    "target_unique_dogs": 10000,
    "page_size": 1000,
    "requested_pages": 17,
    "successful_pages": 17,
    "failed_pages": 0,
    "failed_page_numbers": [],
    "reported_total_counts": [
      60515,
      60515,
      60515,
      60515,
      60515,
      60515,
      60515,
      60515,
      60515,
      60515,
      60515,
      60515,
      60515,
      60515,
      60515,
      60515,
      60515
    ],
    "observed_shapes": {
      "array": 17
    },
    "header_observations": {
      "reqNo": {
        "present:int": 17
      },
      "resultCode": {
        "00": 17
      },
      "resultMsg": {
        "NORMAL SERVICE.": 17
      },
      "errorMsg": {
        "missing": 17
      }
    },
    "entire_population_scope": false,
    "exhausted": false,
    "stop_reason": "target_reached",
    "raw_file": "raw-20260914T232312940282Z.jsonl",
    "finished_at": "2026-09-14T23:24:40.012010+00:00",
    "request_attempts": 17,
    "retries": 0,
    "errors": {},
    "observed_page_sizes": {
      "1000": 17
    },
    "raw_sha256": "866801be3c2bda927a0d292b4c43df0dfab1fcabc6fd7e07dcd0271b24c9de92",
    "as_of_date": "2026-09-15",
    "seed": 20260915,
    "analysis_mode": "offline_replay"
  }
}
```

## 2. 표본 규모

```json
{
  "denominators": {
    "field_dictionary": "all raw rows",
    "identity": "all raw rows / unique IDs",
    "content_metrics": "first-observed payload per unique dog ID",
    "unique_dogs": 10507,
    "unique_all_animals": 17000
  },
  "collection": {
    "status": "sufficient",
    "minimum": 5000,
    "whole_population_exception": false,
    "reported_stable_total": 60515,
    "issues": []
  },
  "species": {
    "dog_count": 10507,
    "non_dog_count": 6493,
    "unresolved_count": 0,
    "dog_ratio": 0.618059,
    "filter": "local exact upKindNm == 개; no server-side species assumption"
  }
}
```

## 3. 응답 형태

```json
{
  "shapes": {
    "array": 17
  },
  "headers": {
    "reqNo": {
      "present:int": 17
    },
    "resultCode": {
      "00": 17
    },
    "resultMsg": {
      "NORMAL SERVICE.": 17
    },
    "errorMsg": {
      "missing": 17
    }
  },
  "note": "Only recorded shapes are observed live; others are mock-tested."
}
```

## 4. Identity 품질

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

## 5. 필드 coverage

```json
{
  "field_count": 64,
  "dictionary": "api-field-dictionary.md"
}
```

## 6. Date 품질

```json
{
  "happenDt": {
    "nonplaceholder_count": 10507,
    "parse_success": 10507,
    "parse_failure": 0,
    "parse_success_ratio": 1.0,
    "invalid_calendar_dates": 0,
    "formats": {
      "YYYYMMDD": 10507
    },
    "minimum": "2026-07-06",
    "maximum": "2026-09-14",
    "future_dates": 0,
    "naive_timestamps": 0
  },
  "noticeSdt": {
    "nonplaceholder_count": 10507,
    "parse_success": 10507,
    "parse_failure": 0,
    "parse_success_ratio": 1.0,
    "invalid_calendar_dates": 0,
    "formats": {
      "YYYYMMDD": 10507
    },
    "minimum": "2026-07-06",
    "maximum": "2026-09-15",
    "future_dates": 0,
    "naive_timestamps": 0
  },
  "noticeEdt": {
    "nonplaceholder_count": 10507,
    "parse_success": 10507,
    "parse_failure": 0,
    "parse_success_ratio": 1.0,
    "invalid_calendar_dates": 0,
    "formats": {
      "YYYYMMDD": 10507
    },
    "minimum": "2026-07-06",
    "maximum": "2026-10-07",
    "future_dates": 1298,
    "naive_timestamps": 0
  },
  "updTm": {
    "nonplaceholder_count": 10507,
    "parse_success": 10507,
    "parse_failure": 0,
    "parse_success_ratio": 1.0,
    "invalid_calendar_dates": 0,
    "formats": {
      "timestamp_naive": 10507
    },
    "minimum": "2026-07-07",
    "maximum": "2026-09-15",
    "future_dates": 0,
    "naive_timestamps": 10507
  },
  "adptnSDate": {
    "nonplaceholder_count": 64,
    "parse_success": 64,
    "parse_failure": 0,
    "parse_success_ratio": 1.0,
    "invalid_calendar_dates": 0,
    "formats": {
      "YYYYMMDD": 64
    },
    "minimum": "2026-01-01",
    "maximum": "2026-01-01",
    "future_dates": 0,
    "naive_timestamps": 0
  },
  "adptnEDate": {
    "nonplaceholder_count": 64,
    "parse_success": 64,
    "parse_failure": 0,
    "parse_success_ratio": 1.0,
    "invalid_calendar_dates": 0,
    "formats": {
      "YYYYMMDD": 64
    },
    "minimum": "2027-03-15",
    "maximum": "2027-03-15",
    "future_dates": 64,
    "naive_timestamps": 0
  },
  "sprtSDate": {
    "nonplaceholder_count": 0,
    "parse_success": 0,
    "parse_failure": 0,
    "parse_success_ratio": null,
    "invalid_calendar_dates": 0,
    "formats": {},
    "minimum": null,
    "maximum": null,
    "future_dates": 0,
    "naive_timestamps": 0
  },
  "sprtEDate": {
    "nonplaceholder_count": 0,
    "parse_success": 0,
    "parse_failure": 0,
    "parse_success_ratio": null,
    "invalid_calendar_dates": 0,
    "formats": {},
    "minimum": null,
    "maximum": null,
    "future_dates": 0,
    "naive_timestamps": 0
  },
  "srvcSDate": {
    "nonplaceholder_count": 64,
    "parse_success": 64,
    "parse_failure": 0,
    "parse_success_ratio": 1.0,
    "invalid_calendar_dates": 0,
    "formats": {
      "YYYYMMDD": 64
    },
    "minimum": "2026-01-01",
    "maximum": "2026-01-01",
    "future_dates": 0,
    "naive_timestamps": 0
  },
  "srvcEDate": {
    "nonplaceholder_count": 64,
    "parse_success": 64,
    "parse_failure": 0,
    "parse_success_ratio": 1.0,
    "invalid_calendar_dates": 0,
    "formats": {
      "YYYYMMDD": 64
    },
    "minimum": "2027-03-15",
    "maximum": "2027-03-15",
    "future_dates": 64,
    "naive_timestamps": 0
  },
  "evntSDate": {
    "nonplaceholder_count": 0,
    "parse_success": 0,
    "parse_failure": 0,
    "parse_success_ratio": null,
    "invalid_calendar_dates": 0,
    "formats": {},
    "minimum": null,
    "maximum": null,
    "future_dates": 0,
    "naive_timestamps": 0
  },
  "evntEDate": {
    "nonplaceholder_count": 0,
    "parse_success": 0,
    "parse_failure": 0,
    "parse_success_ratio": null,
    "invalid_calendar_dates": 0,
    "formats": {},
    "minimum": null,
    "maximum": null,
    "future_dates": 0,
    "naive_timestamps": 0
  },
  "consistency": {
    "noticeSdt<=noticeEdt": {
      "comparable": 10507,
      "violations": 0
    },
    "happenDt<=noticeEdt": {
      "comparable": 10507,
      "violations": 264
    },
    "adptnSDate<=adptnEDate": {
      "comparable": 64,
      "violations": 0
    },
    "sprtSDate<=sprtEDate": {
      "comparable": 0,
      "violations": 0
    },
    "srvcSDate<=srvcEDate": {
      "comparable": 64,
      "violations": 0
    },
    "evntSDate<=evntEDate": {
      "comparable": 0,
      "violations": 0
    }
  }
}
```

## 7. Weight/Age 품질

```json
{
  "weight": {
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
  },
  "age": {
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
}
```

## 8. State/Enum 값

```json
{
  "upKindNm": {
    "고양이": 6098,
    "개": 10507,
    "기타": 395
  },
  "sexCd": {
    "M": 7794,
    "F": 7477,
    "Q": 1729
  },
  "neuterYn": {
    "N": 11439,
    "U": 4522,
    "Y": 1039
  },
  "processState": {
    "종료(입양)": 2752,
    "종료(자연사)": 3527,
    "종료(안락사)": 964,
    "보호중": 7011,
    "종료(반환)": 1954,
    "종료(방사)": 281,
    "종료(기증)": 511
  },
  "kindNm": {
    "한국 고양이": 5179,
    "믹스견": 7835,
    "말티즈": 481,
    "기타축종": 395,
    "시츄": 81,
    "비숑 프리제": 161,
    "프렌치 불독": 42,
    "진도견": 199,
    "페르시안": 50,
    "포메라니안": 266,
    "스피츠": 47,
    "믹스묘": 629,
    "푸들": 508,
    "요크셔 테리어": 35,
    "베들링턴 테리어": 2,
    "치와와": 85,
    "시베리안 허스키": 36,
    "스탠다드 닥스훈트": 14,
    "기타": 94,
    "레그돌": 28,
    "라이카": 11,
    "포인터": 8,
    "와이마라너": 1,
    "러시안 블루": 22,
    "시바": 81,
    "골든 리트리버": 70,
    "빠삐용(콘티넨탈 토이 스파니엘)": 3,
    "보스턴 테리어": 11,
    "코카 스파니엘": 11,
    "토이 푸들": 7,
    "잭 러셀 테리어": 3,
    "먼치킨": 14,
    "보더 콜리": 63,
    "스코티시폴드": 37,
    "이탈리안 그레이 하운드": 12,
    "셔틀랜드 쉽독": 6,
    "라브라도 리트리버": 80,
    "아메리칸 쇼트헤어": 17,
    "삽살개": 17,
    "플랫 코티드 리트리버": 1,
    "하일랜드 폴드": 5,
    "터키시 앙고라": 18,
    "브리티시 쇼트헤어": 31,
    "미니어쳐 핀셔": 12,
    "웰시 코기 펨브로크": 27,
    "웰시 코기 카디건": 11,
    "스탠다드 푸들": 13,
    "브리타니 스파니엘": 4,
    "사모예드": 18,
    "미니어쳐 닥스훈트": 4,
    "올드 잉글리쉬 불독": 1,
    "퍼그": 8,
    "도베르만": 9,
    "셰퍼드": 12,
    "그레이 하운드": 13,
    "키스 훈드": 1,
    "미니어쳐 푸들": 7,
    "아비시니안": 8,
    "미디엄 푸들": 4,
    "페키니즈": 10,
    "샴": 14,
    "폭스테리어": 2,
    "차우차우": 4,
    "노르웨이 숲": 4,
    "말라뮤트": 6,
    "슈나우져": 4,
    "그레이트 피레니즈": 1,
    "페르시안-페르시안 친칠라": 9,
    "메인쿤": 2,
    "잉글리쉬 포인터": 2,
    "아메리칸불리": 1,
    "풍산견": 14,
    "불독": 4,
    "벵갈": 5,
    "브리티쉬롱헤어": 4,
    "잉글리쉬 스프링거 스파니엘": 1,
    "캐벌리어 킹 찰스 스파니엘": 1,
    "도사 믹스견": 14,
    "도사": 1,
    "올드 잉글리쉬 쉽독": 2,
    "샤페이": 2,
    "미니어쳐 슈나우저": 1,
    "휘펫": 1,
    "차이니즈 크레스티드 독": 1,
    "마리노이즈": 11,
    "아메리칸 코카 스파니엘": 4,
    "비글": 3,
    "스노우 슈": 1,
    "울프독": 2,
    "스핑크스": 8,
    "핏불테리어": 1,
    "콜리": 1,
    "비즐라": 1,
    "동경견": 3,
    "잉글리쉬 세터": 1,
    "저먼 셰퍼드 독": 3,
    "시베리안라이카": 1,
    "라사 압소": 1,
    "아메리칸 아키다": 1
  },
  "colorCd": {
    "검정색": 911,
    "레몬색&흰색": 913,
    "갈색": 1408,
    "흰색": 3444,
    "흰색/검은색 얼룩무늬": 811,
    "기타(갈/흰)": 97,
    "기타(검/갈/흰)": 32,
    "갈색&흰색": 961,
    "검은색흰색황토색조합": 869,
    "기타(갈)": 28,
    "검정&흰색": 643,
    "평행·전체·부분줄무늬": 530,
    "기타(갈/검/흰)": 90,
    "기타(흰)": 8,
    "기타(빨/흰)": 1,
    "기타(갈색줄무늬)": 3,
    "기타(흰/검/초)": 1,
    "기타(검/흰/초)": 1,
    "기타(고등어무늬)": 16,
    "기타(진삼색)": 1,
    "기타(회색무늬)": 1,
    "기타(회색)": 76,
    "검정&은색": 10,
    "기타(노랑색흰색)": 1,
    "갈색&검정": 608,
    "기타(진검정밤색)": 1,
    "검정&황갈색": 189,
    "기타(밝은 갈색)": 1,
    "기타(흰검정색)": 1,
    "회색": 94,
    "검정&금색": 4,
    "은색&흰색": 14,
    "흰색&황갈색": 145,
    "기타(횐회노주)": 1,
    "기타(검)": 8,
    "기타(노/갈/녹)": 1,
    "기타(빨/주/초)": 1,
    "기타(회/검/흰)": 2,
    "기타(검/흰)": 132,
    "기타(흰/갈)": 8,
    "기타(회/갈)": 2,
    "기타(노/녹)": 4,
    "기타(검/노)": 3,
    "갈색&검정&흰색": 315,
    "기타(회/흰)": 25,
    "기타(회/흰/검)": 1,
    "기타(검/갈)": 7,
    "기타(갈/회)": 1,
    "기타(흰/초/노)": 1,
    "기타(흰/주/노)": 1,
    "기타(검줄/갈/흰)": 25,
    "기타(흰/회검)": 1,
    "기타(노/회/흰)": 1,
    "기타(갈/노)": 3,
    "기타(노/초/파)": 1,
    "옅은 황색": 111,
    "기타(검/회)": 3,
    "기타(회)": 5,
    "기타(회/검)": 12,
    "기타(회/검/갈)": 1,
    "기타(회/녹/빨)": 1,
    "기타(검/흰/갈)": 4,
    "기타(노/초/빨)": 1,
    "검정 황갈색&흰색": 94,
    "기타(치즈)": 122,
    "흑갈색": 77,
    "기타(황)": 3,
    "기타(황/흰)": 1,
    "기타(검/연갈)": 1,
    "기타(검/흰/노)": 1,
    "기타(회/갈/흰)": 1,
    "기타(황색)": 25,
    "크림색": 448,
    "기타(삼색이)": 15,
    "기타(턱시도)": 21,
    "기타(젖소)": 9,
    "바이블루": 1,
    "엷은 황갈색&흰색": 66,
    "기타(고등테비)": 1,
    "기타(고등어)": 113,
    "기타(주황)": 4,
    "기타(카오스)": 14,
    "기타(고등젖소)": 4,
    "기타(고등삼색)": 1,
    "기타(회갈흰검)": 1,
    "기타(흰/검)": 5,
    "기타(주/흰)": 4,
    "기타(검정,흰색)": 41,
    "기타(검정흰색)": 8,
    "기타(파/흰)": 1,
    "은색/검정색 줄무늬": 15,
    "기타(흰/갈/회)": 1,
    "기타()": 2,
    "청회색": 10,
    "기타(흰황색)": 6,
    "기타(흰회색)": 19,
    "기타(검흰색)": 9,
    "기타(활갈색)": 1,
    "기타(청녹색)": 1,
    "기타(황색.흰색)": 1,
    "기타(검청색)": 1,
    "기타(은회색)": 1,
    "기타(검갈색)": 27,
    "기타(노란색)": 10,
    "기타(빨강)": 1,
    "기타(검정색)": 22,
    "기타(진갈/검)": 1,
    "기타(진갈)": 1,
    "기타(연갈)": 5,
    "기타(검/주/갈)": 1,
    "기타(다홍/흰)": 1,
    "기타(갈/녹/검)": 1,
    "기타(노/주)": 1,
    "기타(검/회/흰)": 3,
    "쵸콜릿색": 21,
    "기타(갈/검)": 7,
    "기타(갈/회/노)": 1,
    "기타(녹)": 1,
    "기타(노랑)": 22,
    "기타(갈,흰)": 4,
    "기타(고동줄무늬)": 2,
    "기타(검정점박)": 1,
    "기타(검갈흰)": 14,
    "기타(갈.검.흰)": 3,
    "기타(갈,검)": 3,
    "기타(초록색)": 3,
    "기타(하늘색)": 2,
    "기타(황/갈/흰)": 1,
    "기타(갈색)": 78,
    "기타(회색,흰색)": 3,
    "기타(검,갈)": 8,
    "기타(흰,연갈)": 1,
    "기타(흰색)": 92,
    "기타(검,갈,흰)": 8,
    "금색&흰색": 54,
    "붉고 엷은 황갈색": 42,
    "기타(실버)": 4,
    "어두운청색&황갈색": 3,
    "하얀바탕에 한가지색 또는 두가지색의 명확한 반점": 14,
    "기타(흰연청색)": 1,
    "금색": 57,
    "황갈색": 229,
    "호반색(호랑이무늬)": 37,
    "적갈색": 14,
    "흰색&갈색&탄": 27,
    "기타(흰재색)": 2,
    "기타(레그돌)": 1,
    "적갈&검정&흰색": 8,
    "어두운회색": 5,
    "기타(연회색)": 4,
    "금갈색": 48,
    "기타(금색)": 2,
    "기타(흰색&회색)": 6,
    "노란색": 22,
    "기타(갈,검,흰)": 4,
    "기타(흰,검)": 5,
    "기타(연갈색)": 32,
    "기타(검갈)": 11,
    "기타(검흰)": 29,
    "기타(갈흰)": 40,
    "기타(흰갈)": 19,
    "기타(갈검흰)": 6,
    "기타(검회색)": 7,
    "기타(흰검갈)": 5,
    "기타(연갈흰)": 3,
    "기타(흰갈검)": 11,
    "기타(갈검)": 18,
    "기타(흰회갈)": 1,
    "기타(흰검)": 14,
    "기타(갈흰검)": 2,
    "기타(회흰색)": 1,
    "기타(검회고등어)": 1,
    "기타(회,갈,흰)": 1,
    "기타(흰,회)": 5,
    "기타(검,흰)": 10,
    "적갈&흰색": 6,
    "기타(블랙&탄)": 1,
    "기타(검정&회색)": 11,
    "기타(흰, 노)": 3,
    "기타(검,회,흰)": 4,
    "기타(갈,노,흰)": 2,
    "기타(흰,노)": 1,
    "기타(연갈,흰)": 1,
    "기타(회,흰)": 1,
    "기타(갈색 흰색)": 2,
    "기타(흰, 갈, 검)": 1,
    "기타(갈색.흰)": 1,
    "기타(검,흰,갈)": 1,
    "기타(갈&검)": 1,
    "흰색&검은반점": 37,
    "살구색": 13,
    "기타(검정)": 38,
    "겨자색": 10,
    "기타(흰&베이지)": 1,
    "기타(갈색&검정)": 3,
    "기타(아이보리색)": 6,
    "기타(회피무늬)": 1,
    "울프그레이": 5,
    "청회색&흰색": 6,
    "밤색&흰색": 9,
    "기타(황토색)": 5,
    "오렌지브라운/흑색": 1,
    "기타(갈색&흰색)": 9,
    "기타(흰노랑주황)": 1,
    "기타(황색흰색)": 6,
    "기타(흰색황색)": 5,
    "기타(갈색흰색)": 6,
    "기타(회식,흰색)": 1,
    "기타(흰색, 회색)": 1,
    "기타(흰색,회색)": 9,
    "기타(황색, 흰색)": 1,
    "기타(흰검색)": 3,
    "기타(혼합색)": 3,
    "기타(노흰색)": 5,
    "기타(회검색)": 1,
    "기타(갈회색)": 4,
    "기타(검갈흰색)": 1,
    "기타(갈흰색)": 2,
    "기타(흰색회색)": 4,
    "기타(흑갈색)": 9,
    "기타(검정_갈색)": 1,
    "기타(갈+검+흰)": 7,
    "기타(검+갈+흰)": 17,
    "기타(갈+흰)": 24,
    "기타(갈+검)": 18,
    "기타(검+흰)": 25,
    "기타(삼색)": 140,
    "기타(검+갈)": 5,
    "기타(회+흰)": 1,
    "기타(노란,황갈)": 1,
    "기타(회색+흰색)": 6,
    "기타(노랑, 파란)": 1,
    "기타(흰색황토색)": 6,
    "기타(흰색검은색)": 8,
    "기타(검은색흰색)": 26,
    "주황&흰색": 11,
    "기타(황갈색)": 5,
    "기타(검은색)": 7,
    "기타(검정+갈색)": 14,
    "기타(갈색+흰색)": 51,
    "기타(검정+흰색)": 23,
    "기타(회색+검정)": 1,
    "기타(갈색+검정)": 4,
    "기타(황토색흰색)": 4,
    "기타(갈+흰+검)": 3,
    "기타(초록+빨강)": 1,
    "기타(분홍색)": 1,
    "기타(검은색 등)": 1,
    "기타(흰색&황색)": 1,
    "기타(갈검흰색)": 10,
    "기타(황검색)": 2,
    "기타(황검흰색)": 5,
    "기타(검은색갈색)": 2,
    "기타(검정황토색)": 1,
    "기타(황토색검정)": 1,
    "기타(회색흰색)": 22,
    "기타(검정&흰색)": 17,
    "기타(회색&흰색)": 7,
    "기타(검정&갈색)": 5,
    "기타(검&갈&흰)": 2,
    "기타(흰,갈)": 8,
    "기타(스탠다드)": 1,
    "빨간색&흰색": 2,
    "기타(초록)": 1,
    "기타(갈색노란색)": 1,
    "회색&흰색": 1,
    "기타(흰색/회색)": 3,
    "기타(검은+갈색)": 1,
    "기타(파랑)": 1,
    "기타(흰.검.카키)": 1,
    "기타(밤갈색)": 1,
    "기타(흰색 회색)": 2,
    "빨간색": 2,
    "BLUE&GOLD": 1,
    "기타(연두색)": 3,
    "기타(흑,백)": 3,
    "밤색": 5,
    "기타(치즈태비)": 18,
    "기타(갈색태비)": 4,
    "기타(고등어태비)": 11,
    "기타(흰색,갈색)": 18,
    "기타(흑,갈,백)": 2,
    "기타(흑갈줄무늬)": 1,
    "기타(미황, 백)": 1,
    "기타(녹,백,흑)": 1,
    "기타(흑,회,백)": 1,
    "기타(흑갈색태비)": 2,
    "기타(흑,황갈)": 1,
    "기타(흰색/갈색)": 1,
    "기타(초콜릿색)": 1,
    "기타(흰색,노랑)": 2,
    "기타(연 회색)": 1,
    "기타(흰.검회색)": 1,
    "기타(노란태비)": 1,
    "기타(연두노랑)": 1,
    "기타(흰색치즈)": 1,
    "기타(흰색.노랑)": 1,
    "기타(흰색.갈색)": 1,
    "기타(흰색.회색)": 2,
    "기타(검정.흰색)": 4,
    "기타(갈색.흰색)": 3,
    "기타(검갈.흰색)": 1,
    "기타(고등어흰색)": 1,
    "기타(연한치즈)": 1,
    "기타(블루)": 3,
    "은색&갈색": 5,
    "기타(백)": 58,
    "기타(흰노)": 2,
    "기타(흰,검,회)": 1,
    "크림색/암갈색 말단": 5,
    "밝은 금색": 3,
    "기타(흰색&금색)": 1,
    "기타(치즈무늬)": 11,
    "기타(검정,노랑)": 2,
    "회색얼룩무늬": 8,
    "청회색말단": 1,
    "기타(반고등어)": 6,
    "기타(고등어테비)": 9,
    "기타(치즈테비)": 9,
    "기타(토터셸)": 1,
    "기타(블랙탄)": 14,
    "기타(노랑+검정)": 1,
    "기타(검+회+흰색)": 1,
    "기타(짙은녹색)": 1,
    "기타(흰색+회색)": 7,
    "기타(흰,검정)": 8,
    "기타(바둑이)": 1,
    "기타(고등어색)": 32,
    "기타(녹색)": 7,
    "기타(검은,흰색)": 1,
    "기타(노랑색)": 17,
    "기타(크림색)": 10,
    "기타(크림)": 3,
    "기타(파란색)": 1,
    "기타(흰갈색)": 11,
    "기타(흰,노랑)": 2,
    "기타(흰색노랑)": 1,
    "기타(베이지)": 12,
    "기타(흰+회얼룩)": 1,
    "기타(검정.회색)": 1,
    "기타(주.노.초)": 1,
    "기타(노랑테비)": 1,
    "은색": 3,
    "엷은 황갈색": 3,
    "기타(회색카오스)": 1,
    "기타(크림갈색)": 1,
    "기타(턱시도턱)": 1,
    "기타(빨강.노랑)": 1,
    "기타(검정흰반점)": 1,
    "기타(희+회)": 1,
    "기타(갈검색)": 6,
    "기타(연녹색)": 1,
    "기타(치즈색)": 7,
    "기타(검정갈색)": 5,
    "기타(갈색검정)": 1,
    "기타(치즈냥이)": 3,
    "기타(흰색/삼색)": 1,
    "기타(검정/흰색)": 11,
    "주황색": 1,
    "기타(얼룩고등어)": 1,
    "기타(회갈색)": 14,
    "기타(실버화이트)": 1,
    "기타(흰색&검정)": 7,
    "기타(흰색&갈색)": 4,
    "호반색&흰색": 6,
    "등쪽은 어둡고 얼굴과 다리쪽은 옅은색": 1,
    "갈색/갈색 무늬": 4,
    "기타(회백)": 14,
    "기타(회백색)": 6,
    "기타(백황)": 14,
    "기타(흑황)": 10,
    "기타(황회색)": 2,
    "기타(황백)": 9,
    "기타(황적색)": 1,
    "기타(황녹)": 1,
    "기타(흑백)": 36,
    "기타(흑회색)": 5,
    "기타(검백)": 12,
    "기타(백색)": 2,
    "기타(백검)": 2,
    "기타(백회)": 1,
    "기타(회검)": 1,
    "기타(흰/핑)": 1,
    "기타(흰/검/회)": 1,
    "기타(갈색검은색)": 1,
    "기타(검/흰/황)": 1,
    "기타(갈색  흰색)": 1,
    "기타(검정 흰색)": 2,
    "기타(연핑/살색)": 1,
    "기타(흰색/검정)": 1,
    "기타(흰&노&회색)": 1,
    "기타(흰&초)": 1,
    "고동색말단": 4,
    "기타(빨&노&초)": 1,
    "기타(검&흰)": 1,
    "기타(갈색,빨강)": 1,
    "얼룩무늬": 5,
    "기타(노랑&주황)": 1,
    "기타(백흑색)": 4,
    "기타(갈흑색)": 2,
    "기타(노란,흰색)": 1,
    "기타(연한갈색)": 2,
    "기타(흑갈백색)": 1,
    "기타(흑백색)": 4,
    "기타(백갈색)": 2,
    "기타(백갈흑색)": 4,
    "기타(백흑갈색)": 4,
    "기타(호구)": 4,
    "기타(갈백색)": 3,
    "기타(갈색크림색)": 1,
    "기타(회색검정)": 1,
    "기타(검정회색)": 3,
    "기타(검백색)": 14,
    "기타(.)": 2,
    "기타(노란색흰색)": 1,
    "기타(흰색갈색)": 10,
    "기타(베이지색)": 3,
    "기타(흑회백색)": 2,
    "기타(검정 갈색)": 2,
    "기타(흑색,백색)": 5,
    "기타(흑색)": 1,
    "기타(진회색)": 2,
    "기타(흑갈)": 17,
    "기타(검, 갈)": 1,
    "기타(녹검빨)": 1,
    "기타(진갈색)": 1,
    "기타(은색, 갈색)": 1,
    "기타(연갈백)": 1,
    "기타(백색 갈색)": 1,
    "기타(갈색 백색)": 1,
    "기타(흑백갈)": 1,
    "기타(흰+검정)": 1,
    "기타(노/회)": 1,
    "기타(검/회/녹)": 1,
    "기타(노/갈)": 1,
    "기타(노/검/빨)": 1,
    "기타(갈백)": 59,
    "기타(흑)": 10,
    "기타(갈흑)": 30,
    "기타(흑갈백)": 7,
    "기타(갈흑백)": 19,
    "기타(노흑)": 1,
    "기타(백갈)": 17,
    "기타(노주초)": 1,
    "기타(노흑주)": 1,
    "기타(노검)": 1,
    "기타(흰.회)": 2,
    "기타(초노빨)": 1,
    "기타(회색,흰색 )": 1,
    "기타(흰색,갈색 )": 1,
    "기타(회색/흰색)": 1,
    "기타(백흑갈)": 5,
    "기타(백갈흑)": 5,
    "기타(흰색+검정 )": 1,
    "기타(백흑)": 10,
    "기타(흰/치즈)": 1,
    "기타(옅은 회색)": 1,
    "기타(흰/회)": 4,
    "기타(회색/검정)": 1,
    "기타(갈/검/노)": 1,
    "기타(흰/노)": 4,
    "기타(노/흰)": 5,
    "기타(검/노/흰)": 2,
    "기타(흑회)": 1,
    "기타(회갈)": 1,
    "기타(노백)": 2,
    "기타(초빨파)": 1,
    "기타(갈백흑)": 1,
    "기타(회주)": 1,
    "기타(턱시도시)": 1,
    "기타(녹갈색)": 1,
    "기타(황색,흰색)": 2,
    "기타(검정황색)": 2,
    "기타(삼색고등어)": 1,
    "기타(회검정)": 1,
    "기타(옅은황색)": 2,
    "기타(흰색검정색)": 1,
    "기타(갈/회/흰)": 3,
    "기타(에프리)": 1,
    "기타(회색,갈색)": 2,
    "기타(블랙 갈색)": 1,
    "기타(첳색)": 1,
    "기타(갈,흰,검)": 4,
    "기타(아이보리)": 2,
    "기타(초,빨,노)": 1,
    "기타(흰, 검정색)": 2,
    "기타(줄무늬)": 1,
    "기타(청백)": 1,
    "기타(노적)": 1,
    "기타(노백흑)": 1,
    "기타(노흑백)": 1,
    "기타(호피무늬)": 2,
    "기타(흰색검정)": 17,
    "기타(갈, 흰색)": 1,
    "기타(크림, 흰색)": 1,
    "기타(연갈, 흰색)": 2,
    "기타(검, 흰색)": 5,
    "갈색 얼룩무늬": 4,
    "기타(검, 흰)": 1,
    "기타(흰, 노, 녹)": 1,
    "기타(옅은 갈색)": 3,
    "기타(빨, 파, 검)": 1,
    "기타(흑갈, 흰색)": 1,
    "기타(갈/연갈)": 1,
    "기타(연갈/흰)": 1,
    "기타(검줄/흰)": 1,
    "기타(흰/검줄/갈)": 2,
    "기타(검줄)": 1,
    "기타(흰/검줄)": 1,
    "기타(갈/검줄/흰)": 1,
    "기타(흰회색검줄)": 2,
    "기타(검정크림색)": 2,
    "기타(황갈색흰색)": 8,
    "기타(흑색흰색)": 1,
    "기타(흰회갈검줄)": 2,
    "기타(회색크림색)": 1,
    "기타(검정색흰색)": 3,
    "기타(블랙탄블)": 1,
    "기타(흑갈색흰색)": 2,
    "기타(흰색크림색)": 5,
    "기타(세가지색)": 2,
    "기타(노,녹,파)": 1,
    "기타(검/흰/회색)": 1,
    "기타(갈색/흰색)": 3,
    "기타(파랑/검정)": 1,
    "기타(검정/갈색)": 2,
    "기타(흰/갈/검)": 1,
    "기타(파/노/흰)": 1,
    "기타(빨강,주황)": 1,
    "기타(빨,주,초)": 1,
    "기타(청색흰색)": 1,
    "기타(노랑초록)": 1,
    "기타(갈색,흰색)": 13,
    "기타(연고등어)": 1,
    "기타(한국고양이)": 1,
    "기타(청색)": 2,
    "기타(검/흰/회)": 1,
    "기타(갈/흰/검)": 4,
    "기타(검/녹/노)": 1,
    "기타(노/초/검)": 1,
    "기타(갈/노/검)": 1,
    "기타(흰/연갈)": 2,
    "기타(누렁)": 1,
    "기타(노/녹/검)": 1,
    "기타(호반색)": 1,
    "기타(검정색재색)": 1,
    "기타(황갈색황)": 1,
    "기타(갈색검정색)": 2,
    "기타(은색회색)": 1,
    "기타(흰,갈색)": 2,
    "기타(흰,회색)": 4,
    "기타(청록,흰색)": 1,
    "기타(호피색)": 2,
    "기타(회,검정)": 1,
    "기타(갈,파,흰)": 1,
    "기타(블루멀)": 1,
    "기타(연갈/검)": 1,
    "기타(회색태비)": 1,
    "청색": 2,
    "기타(흰,검,갈)": 2,
    "기타(회/황)": 1,
    "기타(흰/황)": 2,
    "기타(검,갈색)": 1,
    "황토색": 1,
    "기타(검정,회색)": 2,
    "기타(검정, 갈색)": 2,
    "기타(노랑갈색)": 1,
    "기타(검정하늘)": 1,
    "기타(청록색)": 2,
    "기타(연노랑)": 2,
    "기타(태비)": 16,
    "기타(호피)": 4,
    "기타(검정/노랑)": 1,
    "기타(흰.황색)": 1,
    "기타(흰.갈색)": 1,
    "기타(옅은갈색)": 2,
    "기타(검정.황색)": 1,
    "기타(흰색(회색))": 2,
    "기타(검정(흰줄))": 1,
    "기타(황색(흰줄))": 1,
    "기타(갈색(흰줄))": 1,
    "기타(흰검갈색)": 1,
    "기타(검정 얼룩)": 1,
    "기타(갈색 혼합)": 1,
    "기타(검, 회, 갈)": 1,
    "적갈색&밝은갈색": 1,
    "기타(회, 흰)": 1,
    "기타(회색, 흰색)": 1,
    "기타(알록달록)": 1,
    "기타(노랑+흰색)": 4,
    "기타(검갈회)": 1,
    "기타(청회색)": 2,
    "기타(흰+검+회)": 1,
    "기타(블루 )": 1,
    "기타(핑크)": 1,
    "기타(흑/황색)": 2,
    "기타(흑/갈/백색)": 4,
    "기타(흑/갈색)": 1,
    "기타(흰/연갈색)": 1,
    "기타(황/백색)": 5,
    "기타(검/흰색)": 1,
    "기타(흰/갈색)": 1,
    "기타(흑/백/갈색)": 1,
    "기타(흰/검정색)": 1,
    "기타(흰갈검은색)": 1,
    "기타(갈/검정색)": 1,
    "기타(검/흰/노랑)": 1,
    "기타(검/갈/백색)": 1,
    "기타(크림&갈색)": 1,
    "기타(갈색,회색)": 1,
    "기타(노랑,초록)": 2,
    "기타(흰색,연갈)": 1,
    "기타(흰색, 노랑)": 1,
    "기타(갈색, 흰색)": 2,
    "기타(검정줄무늬)": 1,
    "기타(검정, 흰색)": 3,
    "기타(황백색)": 2,
    "기타(흑황백색)": 1,
    "기타(흰색+검정)": 1,
    "기타(흰색+갈색)": 3,
    "기타(미색)": 1,
    "기타(노랑,재색)": 1,
    "기타(회색줄무늬)": 2,
    "기타(노랑,흰색)": 1,
    "기타(크림&흰색)": 1,
    "기타(회황흰검)": 1,
    "기타(검. 노. 흰)": 1,
    "기타(흰.갈.회)": 1,
    "기타(노,흰)": 1,
    "기타(크림/회색)": 1,
    "기타(노랑,검정)": 1,
    "기타(쥐색)": 5,
    "황색/검정 얼룩무늬": 1,
    "기타(흰회검)": 3,
    "기타(쵸콜릿색)": 2,
    "기타(초코&흰색)": 3,
    "기타(회색블루)": 1,
    "기타(믹스)": 78,
    "기타(비숑믹스)": 1,
    "기타(푸들믹스)": 1,
    "기타(흰색, 갈색)": 1,
    "회색(회청색)바탕에 검정얼룩무늬": 3,
    "기타(황색줄무늬)": 1,
    "기타(연한 갈색)": 1,
    "기타(흰,갈,검)": 3,
    "기타(갈,검,회)": 1,
    "기타(회색,검정)": 2,
    "기타(회,갈,검)": 2,
    "기타(황금색)": 1,
    "기타(검정,갈색)": 4,
    "기타(치즈,흰색)": 1,
    "기타(흰,주,검)": 2,
    "기타(크림,흰색)": 1,
    "기타(갈색,검정)": 1,
    "기타(회색&검정)": 1,
    "기타(크림&회색)": 2,
    "기타(회색?)": 1,
    "기타(Amelanisti)": 1,
    "기타(밀색)": 1,
    "기타(흰연황색)": 1,
    "갈색&회색": 1,
    "기타(검은 얼룩)": 1,
    "기타(검고 흰색)": 3,
    "기타(분홍)": 1,
    "기타(흰색.검정)": 1,
    "기타(회색 흰색)": 1,
    "기타(흰색 갈색)": 2,
    "기타(흰 갈 검)": 1,
    "기타(연두빨강)": 1,
    "기타(붉/녹/주황)": 1,
    "기타(검정,연갈)": 1,
    "기타(청갈색)": 1,
    "기타(연갈,검정)": 1,
    "기타(연갈,흰색)": 1,
    "기타(흰색,검정)": 2,
    "기타(고등어 )": 1,
    "기타(황색검정)": 1,
    "기타(갈색,하양)": 2,
    "기타(검갈줄무늬)": 1,
    "기타(검회 라인)": 1,
    "기타(초록+흰색)": 1,
    "기타(연갈+검정)": 1,
    "기타(연갈+흰색)": 2,
    "기타(검+연갈+흰)": 1,
    "기타(브린들)": 9,
    "기타(흰회)": 2,
    "기타(짙은회색)": 1,
    "기타(옅은회색)": 1
  }
}
```

## 9. Image coverage

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

## 10. Shelter/Region 품질

```json
{
  "distinct_careRegNo": 277,
  "careRegNo_coverage": 1.0,
  "shelter_name_address_conflicts": {
    "careNm": 0,
    "careAddr": 0
  },
  "phone_blank_or_missing_ratio": 0.0,
  "address_blank_or_missing_ratio": 0.0,
  "source_prefixes": {
    "orgNm": {
      "서울특별시": 385,
      "전남광주통합특별시": 1377,
      "부산광역시": 384,
      "대구광역시": 241,
      "인천광역시": 400,
      "대전광역시": 175,
      "울산광역시": 140,
      "경기도": 1968,
      "강원특별자치도": 583,
      "충청북도": 492,
      "충청남도": 879,
      "전북특별자치도": 908,
      "경상북도": 1021,
      "경상남도": 1107,
      "제주특별자치도": 418,
      "세종특별자치시": 29
    },
    "careAddr": {
      "경기도": 2309,
      "서울특별시": 114,
      "전남광주통합특별시": 229,
      "전라남도": 1148,
      "부산광역시": 534,
      "대구광역시": 241,
      "인천광역시": 364,
      "대전광역시": 175,
      "울산광역시": 140,
      "강원도": 401,
      "강원특별자치도": 148,
      "충청북도": 492,
      "충청남도": 879,
      "전라북도": 277,
      "전북특별자치도": 631,
      "경상북도": 1021,
      "경상남도": 957,
      "제주특별자치도": 418,
      "세종특별자치시": 29
    },
    "happenPlace": {
      "[unresolved]": 10104,
      "전남광주통합특별시": 6,
      "인천광역시": 20,
      "경기도": 89,
      "강원특별자치도": 87,
      "강원도": 1,
      "충청북도": 11,
      "충청남도": 22,
      "전북특별자치도": 8,
      "경상북도": 110,
      "경상남도": 47,
      "세종특별자치시": 2
    }
  },
  "two_or_more_sources_comparable": 10507,
  "raw_prefix_agreements": 8189,
  "raw_prefix_disagreements": 2318,
  "no_sido_prefix_candidate": 0,
  "normalization_status": "official_codes_verified_for_capture",
  "notes": "Raw prefix diagnostics retained for comparison. Official code joins and scoped animal-ID evidence are recorded in reference_data; no source values rewritten."
}
```

## 11. Description 품질

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

## 12. Behavior evidence 비율

```json
{
  "counts": {
    "any_behavior": 4821,
    "any_health": 1166,
    "any_administrative": 718,
    "behavior_and_health": 425,
    "administrative_only": 484,
    "only_specialMark_behavior": 4765,
    "sfeSoci_behavior": 56,
    "adoption_description_behavior": 0
  },
  "ratios": {
    "any_behavior": 0.458837,
    "any_health": 0.110974,
    "any_administrative": 0.068335,
    "behavior_and_health": 0.040449,
    "administrative_only": 0.046065,
    "only_specialMark_behavior": 0.453507,
    "sfeSoci_behavior": 0.00533,
    "adoption_description_behavior": 0.0
  },
  "note": "Multi-label keyword candidates, not tags or diagnoses. Short text and keyword flags overlap (e.g. 순함, 경계). Negation requires human review."
}
```

## 13. Health evidence 비율

```json
{
  "vaccinationChk": 0.159227,
  "healthChk": 0.132007,
  "sfeHealth": 0.014371
}
```

## 14. Adoption promotion coverage

```json
{
  "adptn": {
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
  },
  "sprt": {
    "fields": {
      "sprtTitle": 0.0,
      "sprtSDate": 0.0,
      "sprtEDate": 0.0,
      "sprtConditionLimitTxt": 0.0,
      "sprtTxt": 0.0,
      "sprtImg": 0.0
    },
    "any_ratio": 0.0,
    "complete_ratio": 0.0
  },
  "srvc": {
    "fields": {
      "srvcTitle": 0.006091,
      "srvcSDate": 0.006091,
      "srvcEDate": 0.006091,
      "srvcConditionLimitTxt": 0.006091,
      "srvcTxt": 0.006091,
      "srvcImg": 0.0
    },
    "any_ratio": 0.006091,
    "complete_ratio": 0.0
  },
  "evnt": {
    "fields": {
      "evntTitle": 0.0,
      "evntSDate": 0.0,
      "evntEDate": 0.0,
      "evntConditionLimitTxt": 0.0,
      "evntTxt": 0.0,
      "evntImg": 0.0
    },
    "any_ratio": 0.0,
    "complete_ratio": 0.0
  }
}
```

## 15. 데이터 이상치

```json
{
  "freshness": {
    "days_since_found": {
      "count": 10507,
      "min": 1,
      "p25": 19.0,
      "median": 36,
      "p75": 55.0,
      "p95": 68.0,
      "max": 71,
      "mean": 36.39792519272866
    },
    "days_until_notice_end": {
      "count": 10507,
      "min": -71,
      "p25": -43.0,
      "median": -26,
      "p75": -8.0,
      "p95": 6.0,
      "max": 22,
      "mean": -25.38412486913486
    },
    "source_update_lag_days_aware_only": {
      "count": 0,
      "min": null,
      "p25": null,
      "median": null,
      "p75": null,
      "p95": null,
      "max": null,
      "mean": null
    },
    "source_update_lag_note": "Naive updTm excluded until source timezone is confirmed."
  },
  "breed": {
    "top_50": {
      "믹스견": 7835,
      "푸들": 508,
      "말티즈": 481,
      "포메라니안": 266,
      "진도견": 199,
      "비숑 프리제": 161,
      "치와와": 85,
      "시츄": 81,
      "시바": 81,
      "기타": 81,
      "라브라도 리트리버": 80,
      "골든 리트리버": 70,
      "보더 콜리": 63,
      "스피츠": 47,
      "프렌치 불독": 42,
      "시베리안 허스키": 36,
      "요크셔 테리어": 35,
      "웰시 코기 펨브로크": 27,
      "사모예드": 18,
      "삽살개": 17,
      "스탠다드 닥스훈트": 14,
      "풍산견": 14,
      "도사 믹스견": 14,
      "스탠다드 푸들": 13,
      "그레이 하운드": 13,
      "이탈리안 그레이 하운드": 12,
      "미니어쳐 핀셔": 12,
      "셰퍼드": 12,
      "라이카": 11,
      "보스턴 테리어": 11,
      "코카 스파니엘": 11,
      "웰시 코기 카디건": 11,
      "마리노이즈": 11,
      "페키니즈": 10,
      "도베르만": 9,
      "포인터": 8,
      "퍼그": 8,
      "토이 푸들": 7,
      "미니어쳐 푸들": 7,
      "셔틀랜드 쉽독": 6,
      "말라뮤트": 6,
      "브리타니 스파니엘": 4,
      "미니어쳐 닥스훈트": 4,
      "미디엄 푸들": 4,
      "차우차우": 4,
      "슈나우져": 4,
      "불독": 4,
      "아메리칸 코카 스파니엘": 4,
      "빠삐용(콘티넨탈 토이 스파니엘)": 3,
      "잭 러셀 테리어": 3
    },
    "mixed_ratio": 0.747026,
    "blank_ratio": 0.0,
    "kind_full_inconsistent": 80
  },
  "color": {
    "multi_color_candidate_ratio": 0.329875,
    "single_color_candidate_ratio": 0.670125,
    "unmapped_ratio": 0.140668,
    "mapping_status": "measured_exact_vocabulary_candidates_not_production"
  },
  "repeated_discovery_groups": 696
}
```

## 16. Manual review 대상

```json
{
  "seed": 20260915,
  "requested": 100,
  "actual": 100,
  "strata": {
    "behavior": 25,
    "health": 25,
    "administrative_or_meaningless": 25,
    "random": 25
  },
  "backfilled": 0,
  "review_status": "pending_human_review",
  "notes": "Disjoint strata in declared order; shortages backfilled at random."
}
```

## 17. DB 설계에 미치는 영향

Preserve source values and nullable fields. No schema/UPSERT implemented. Review identity.

## 18. Tag 설계에 미치는 영향

Behavior/health/admin are separate candidates. Human review pending; no production tags.

## 19. Frontend UX에 미치는 영향

```json
{
  "project_thresholds_not_source_facts": {
    "identity_missing_review": 0.001,
    "conflicting_id_review": 0.001,
    "weight_parse_failure_unknown_ux": 0.1,
    "image_empty_ux": 0.7,
    "behavior_exploration_bands": [
      0.3,
      0.6
    ]
  },
  "note": "Coverage is not correctness. No fabricated missing-data values."
}
```

## 20. Phase 2 진행 전 결정 필요사항

```json
{
  "blockers": [],
  "next": "Report unresolved decisions; no Phase 2."
}
```

## Method limits

First-observed unique dog payloads are diagnostic snapshots. Do not extrapolate unmeasured periods or regions. Naive timestamps are not silently UTC. Prefix/keyword heuristics do not prove production mappings or tag correctness. Review notes remain blank for human review. All row-level files stay local.

## Empirical proposals and sample composition

```json
{
  "denominator_unique_dogs": 10507,
  "proposed_size_groups": {
    "tiny": 5415,
    "large": 538,
    "medium": 1970,
    "small": 2511,
    "unknown": 73
  },
  "contract_size_groups_before_quality_policy": {
    "tiny": 5426,
    "large": 538,
    "medium": 1970,
    "small": 2511,
    "unknown": 62
  },
  "proposed_age_groups": {
    "puppy": 4920,
    "adult": 1770,
    "young": 3220,
    "senior": 597
  },
  "proposal_note": "Existing contract thresholds evaluated, not finalized or changed. The proposed size counts exclude zero/negative weights; this quality policy is not approved for production. Literal contract counts are shown separately. >100kg values remain diagnostic large candidates, not validated measurements. Future birth years excluded from proposed age groups.",
  "age_formats": {
    "under_60_days_annotation": 2332,
    "year_only": 8175
  },
  "year_only_parser_coverage": 0.778053,
  "found_month_distribution": {
    "2026-07": 4062,
    "2026-08": 4399,
    "2026-09": 2046
  },
  "species_code_name_pairs": [
    {
      "code": "417000",
      "name": "개",
      "count": 10507
    }
  ],
  "organization_frequencies": {
    "제주특별자치도": 418,
    "경기도 화성시": 214,
    "전북특별자치도 익산시": 213,
    "경상남도 창원시 의창성산구": 211,
    "전남광주통합특별시 나주시": 202,
    "충청북도 청주시": 165,
    "부산광역시 강서구": 154,
    "경기도 포천시": 153,
    "경상남도 김해시": 150,
    "경상북도 경주시": 140,
    "충청남도 천안시": 135,
    "경기도 평택시": 122,
    "경상북도 포항시": 120,
    "충청남도 서산시": 115,
    "강원특별자치도 춘천시": 112,
    "경기도 안성시": 103,
    "경기도 파주시": 101,
    "전북특별자치도 전주시": 101,
    "경기도 안산시": 97,
    "경기도 남양주시": 97,
    "충청북도 음성군": 96,
    "경기도 광주시": 95,
    "경상남도 밀양시": 93,
    "전북특별자치도 부안군": 92,
    "울산광역시 울주군": 91,
    "전남광주통합특별시 목포시": 90,
    "인천광역시 강화군": 88,
    "충청남도 논산시": 88,
    "경상북도 경산시": 88,
    "전북특별자치도 군산시": 87,
    "전북특별자치도 정읍시": 87,
    "충청남도 부여군": 84,
    "경상남도 진주시": 84,
    "전남광주통합특별시 여수시": 83,
    "경기도 고양시": 82,
    "충청남도 아산시": 82,
    "전남광주통합특별시 해남군": 81,
    "전남광주통합특별시 광양시": 80,
    "전남광주통합특별시 함평군": 80,
    "강원특별자치도 원주시": 80,
    "경기도 양평군": 78,
    "충청남도 당진시": 78,
    "전북특별자치도 남원시": 78,
    "경기도 성남시": 77,
    "전북특별자치도 고창군": 77,
    "경상남도 거창군": 77,
    "전남광주통합특별시 고흥군": 71,
    "경기도 이천시": 69,
    "경기도 여주시": 68,
    "강원특별자치도 강릉시": 67,
    "강원특별자치도 동해시": 66,
    "전남광주통합특별시 순천시": 65,
    "경상남도 창녕군": 65,
    "경기도 시흥시": 64,
    "경상북도 구미시": 64,
    "경기도 수원시": 62,
    "충청남도 태안군": 62,
    "경상남도 함안군": 62,
    "경상북도 영천시": 61,
    "경기도 양주시": 60,
    "전남광주통합특별시 화순군": 59,
    "전북특별자치도 김제시": 59,
    "전남광주통합특별시 보성군": 58,
    "경기도 용인시": 58,
    "경상북도 문경시": 58,
    "경상남도 거제시": 58,
    "경기도 김포시": 57,
    "충청북도 옥천군": 57,
    "경상북도 울진군": 56,
    "전남광주통합특별시 담양군": 55,
    "경상북도 청도군": 55,
    "인천광역시 미추홀구": 54,
    "대전광역시 서구": 54,
    "경기도 연천군": 51,
    "전남광주통합특별시 영암군": 50,
    "서울특별시 관악구": 49,
    "인천광역시 검단구": 48,
    "경상남도 사천시": 48,
    "경상남도 합천군": 48,
    "경상남도 의령군": 47,
    "충청남도 예산군": 46,
    "전북특별자치도 임실군": 46,
    "전남광주통합특별시 광산구": 45,
    "충청남도 공주시": 45,
    "경상북도 의성군": 45,
    "전남광주통합특별시 북구": 44,
    "경상북도 영주시": 44,
    "인천광역시 남동구": 43,
    "강원특별자치도 철원군": 43,
    "충청남도 홍성군": 43,
    "전남광주통합특별시 장성군": 42,
    "대구광역시 동구": 42,
    "대전광역시 동구": 42,
    "전북특별자치도 완주군": 42,
    "인천광역시 계양구": 41,
    "경기도 부천시": 41,
    "경상북도 상주시": 41,
    "경상북도 성주군": 39,
    "대구광역시 북구": 38,
    "대구광역시 달성군": 38,
    "경기도 광명시": 38,
    "충청북도 충주시": 38,
    "충청남도 보령시": 38,
    "전남광주통합특별시 신안군": 37,
    "대전광역시 유성구": 36,
    "충청북도 영동군": 36,
    "경기도 의정부시": 34,
    "경상북도 칠곡군": 34,
    "경상북도 고령군": 33,
    "서울특별시 은평구": 32,
    "서울특별시 강서구": 32,
    "부산광역시 기장군": 32,
    "경상북도 김천시": 32,
    "전남광주통합특별시 구례군": 31,
    "전남광주통합특별시 완도군": 31,
    "대구광역시 서구": 31,
    "인천광역시 영종구": 31,
    "인천광역시 서해구": 31,
    "충청북도 괴산군": 31,
    "서울특별시 강북구": 30,
    "경상북도 영덕군": 30,
    "경상북도 안동시": 29,
    "세종특별자치시": 29,
    "전남광주통합특별시 무안군": 28,
    "충청북도 진천군": 28,
    "경상북도 예천군": 28,
    "경상남도 고성군": 28,
    "경상남도 하동군": 28,
    "대전광역시 중구": 27,
    "전남광주통합특별시 영광군": 26,
    "경기도 오산시": 26,
    "충청남도 금산군": 26,
    "경상남도 통영시": 26,
    "전남광주통합특별시 곡성군": 25,
    "대구광역시 수성구": 25,
    "경기도 가평군": 25,
    "강원특별자치도 고성군": 25,
    "경상남도 남해군": 25,
    "인천광역시 부평구": 24,
    "경기도 하남시": 24,
    "강원특별자치도 정선군": 24,
    "경기도 동두천시": 23,
    "부산광역시 부산진구": 22,
    "부산광역시 북구": 22,
    "부산광역시 해운대구": 22,
    "대구광역시 달서구": 22,
    "경상남도 양산시": 22,
    "서울특별시 동대문구": 21,
    "경기도 구리시": 21,
    "강원특별자치도 속초시": 21,
    "경상남도 산청군": 21,
    "전남광주통합특별시 동구": 20,
    "전남광주통합특별시 서구": 20,
    "전남광주통합특별시 강진군": 20,
    "대구광역시 군위군": 20,
    "강원특별자치도 삼척시": 20,
    "강원특별자치도 인제군": 20,
    "서울특별시 노원구": 19,
    "충청북도 제천시": 19,
    "강원특별자치도 횡성군": 18,
    "충청남도 서천군": 18,
    "서울특별시 서초구": 17,
    "전남광주통합특별시 남구": 17,
    "전남광주통합특별시 진도군": 17,
    "부산광역시 동래구": 17,
    "부산광역시 사상구": 17,
    "강원특별자치도 홍천군": 17,
    "서울특별시 성북구": 16,
    "부산광역시 금정구": 16,
    "부산광역시 연제구": 16,
    "대전광역시 대덕구": 16,
    "울산광역시 남구": 16,
    "서울특별시 구로구": 15,
    "서울특별시 강동구": 15,
    "강원특별자치도 태백시": 15,
    "서울특별시 마포구": 14,
    "대구광역시 중구": 14,
    "인천광역시 제물포구": 14,
    "인천광역시 옹진군": 14,
    "경상남도 함양군": 14,
    "서울특별시 중랑구": 13,
    "부산광역시 남구": 13,
    "울산광역시 중구": 13,
    "울산광역시 북구": 13,
    "강원특별자치도 평창군": 13,
    "강원특별자치도 양구군": 13,
    "전북특별자치도 진안군": 13,
    "경상북도 청송군": 13,
    "서울특별시 영등포구": 12,
    "서울특별시 동작구": 12,
    "서울특별시 송파구": 12,
    "부산광역시 서구": 12,
    "부산광역시 사하구": 12,
    "인천광역시 연수구": 12,
    "강원특별자치도 화천군": 12,
    "강원특별자치도 양양군": 12,
    "서울특별시 종로구": 11,
    "서울특별시 도봉구": 11,
    "서울특별시 금천구": 11,
    "대구광역시 남구": 11,
    "경기도 안양시": 11,
    "충청북도 보은군": 11,
    "충청남도 청양군": 11,
    "서울특별시 서대문구": 10,
    "부산광역시 영도구": 10,
    "부산광역시 수영구": 10,
    "경상북도 봉화군": 10,
    "서울특별시 광진구": 9,
    "서울특별시 성동구": 8,
    "경기도 의왕시": 8,
    "충청남도 계룡시": 8,
    "서울특별시 용산구": 7,
    "울산광역시 동구": 7,
    "충청북도 증평군": 7,
    "서울특별시 강남구": 6,
    "경기도 군포시": 6,
    "전북특별자치도 무주군": 6,
    "부산광역시 동구": 5,
    "강원특별자치도 영월군": 5,
    "전북특별자치도 장수군": 5,
    "부산광역시 중구": 4,
    "충청북도 단양군": 4,
    "경기도 과천시": 3,
    "서울특별시 중구": 2,
    "전북특별자치도 순창군": 2,
    "서울특별시 양천구": 1,
    "경상북도 영양군": 1
  },
  "organization_address_prefix_difference_pairs": [
    {
      "organization_prefix": "전남광주통합특별시",
      "address_prefix": "전라남도",
      "count": 1148
    },
    {
      "organization_prefix": "강원특별자치도",
      "address_prefix": "강원도",
      "count": 401
    },
    {
      "organization_prefix": "전북특별자치도",
      "address_prefix": "전라북도",
      "count": 277
    },
    {
      "organization_prefix": "서울특별시",
      "address_prefix": "경기도",
      "count": 271
    },
    {
      "organization_prefix": "경상남도",
      "address_prefix": "부산광역시",
      "count": 150
    },
    {
      "organization_prefix": "인천광역시",
      "address_prefix": "경기도",
      "count": 36
    },
    {
      "organization_prefix": "강원특별자치도",
      "address_prefix": "경기도",
      "count": 34
    }
  ],
  "region_note": "Different prefixes may reflect jurisdiction, shelter location or renamed administrative areas; do not label all differences data errors.",
  "process_state_frequencies_dogs": {
    "종료(입양)": 1569,
    "종료(안락사)": 760,
    "종료(자연사)": 843,
    "보호중": 5098,
    "종료(반환)": 1849,
    "종료(기증)": 388
  },
  "sex_frequencies_dogs": {
    "M": 5239,
    "F": 5162,
    "Q": 106
  },
  "neuter_frequencies_dogs": {
    "N": 6731,
    "U": 2990,
    "Y": 786
  },
  "animals_active_candidate_protecting_only": 5098,
  "active_note": "Candidate definition only: raw processState=보호중. This is not evidence of immediate adoption eligibility.",
  "color_mapping_candidate_counts": {
    "single": 6108,
    "unmapped": 1478,
    "multiple": 2921
  },
  "color_unmapped_candidate_ratio": 0.140668,
  "color_mapping_candidates": {
    "갈색": [
      "brown"
    ],
    "흰색": [
      "white"
    ],
    "기타(갈/흰)": null,
    "갈색&흰색": [
      "brown",
      "white"
    ],
    "검정&흰색": [
      "black",
      "white"
    ],
    "검정&은색": null,
    "갈색&검정": [
      "brown",
      "black"
    ],
    "검정&황갈색": [
      "black",
      "tan"
    ],
    "회색": [
      "gray"
    ],
    "검정&금색": [
      "black",
      "gold"
    ],
    "은색&흰색": null,
    "흰색&황갈색": [
      "white",
      "tan"
    ],
    "기타(검)": null,
    "기타(흰/갈)": null,
    "기타(회/갈)": null,
    "검정색": [
      "black"
    ],
    "갈색&검정&흰색": [
      "brown",
      "black",
      "white"
    ],
    "기타(검/갈)": null,
    "기타(갈/회)": null,
    "기타(검/흰)": null,
    "옅은 황색": null,
    "기타(검/회)": null,
    "기타(회/검)": null,
    "기타(회/검/갈)": null,
    "검정 황갈색&흰색": null,
    "흑갈색": null,
    "기타(황)": null,
    "기타(황/흰)": null,
    "기타(회색)": null,
    "기타(검/연갈)": null,
    "기타(흰)": null,
    "크림색": [
      "cream"
    ],
    "바이블루": null,
    "엷은 황갈색&흰색": null,
    "기타(검/갈/흰)": null,
    "기타(흰/검)": null,
    "기타(진갈/검)": null,
    "기타(진갈)": null,
    "기타(연갈)": null,
    "기타(회/흰)": null,
    "기타(검/회/흰)": null,
    "쵸콜릿색": null,
    "금색&흰색": [
      "gold",
      "white"
    ],
    "붉고 엷은 황갈색": null,
    "어두운청색&황갈색": null,
    "하얀바탕에 한가지색 또는 두가지색의 명확한 반점": null,
    "금색": [
      "gold"
    ],
    "황갈색": [
      "tan"
    ],
    "호반색(호랑이무늬)": null,
    "적갈색": null,
    "흰색&갈색&탄": null,
    "적갈&검정&흰색": null,
    "어두운회색": null,
    "금갈색": null,
    "노란색": [
      "yellow"
    ],
    "기타(갈,검,흰)": null,
    "기타(검갈색)": null,
    "기타(연갈색)": null,
    "기타(검갈)": null,
    "기타(흰갈)": null,
    "기타(갈흰)": null,
    "기타(흰검갈)": null,
    "기타(연갈흰)": null,
    "기타(검회색)": null,
    "기타(검갈흰)": null,
    "기타(갈검)": null,
    "기타(흰갈검)": null,
    "기타(회흰색)": null,
    "기타(갈색)": null,
    "기타(흰회색)": null,
    "기타(갈검흰)": null,
    "적갈&흰색": null,
    "기타(블랙&탄)": null,
    "기타(검정&회색)": null,
    "기타(검,회,흰)": null,
    "레몬색&흰색": null,
    "기타(흰색)": null,
    "기타(갈&검)": null,
    "흰색&검은반점": null,
    "살구색": null,
    "겨자색": null,
    "기타(흰&베이지)": null,
    "기타(갈색&검정)": null,
    "기타(아이보리색)": null,
    "기타(회피무늬)": null,
    "울프그레이": null,
    "청회색&흰색": null,
    "기타(검정)": null,
    "밤색&흰색": null,
    "기타(회검색)": null,
    "기타(갈회색)": null,
    "기타(갈흰색)": null,
    "기타(갈+검)": null,
    "기타(검+흰)": null,
    "주황&흰색": null,
    "기타(검정+흰색)": null,
    "기타(갈색+흰색)": null,
    "기타(갈색흰색)": null,
    "기타(황토색흰색)": null,
    "기타(검+갈+흰)": null,
    "빨간색&흰색": null,
    "회색&흰색": [
      "gray",
      "white"
    ],
    "기타(흰색 회색)": null,
    "빨간색": null,
    "BLUE&GOLD": null,
    "밤색": null,
    "기타(흑,갈,백)": null,
    "기타(흰색/갈색)": null,
    "은색&갈색": null,
    "기타(검정,흰색)": null,
    "밝은 금색": null,
    "기타(흰색&금색)": null,
    "기타(흰색,회색)": null,
    "회색얼룩무늬": null,
    "기타(블랙탄)": null,
    "기타(베이지)": null,
    "기타(크림갈색)": null,
    "주황색": null,
    "기타(실버화이트)": null,
    "기타(흰색&검정)": null,
    "호반색&흰색": null,
    "등쪽은 어둡고 얼굴과 다리쪽은 옅은색": null,
    "기타(크림색)": null,
    "기타(백황)": null,
    "기타(황회색)": null,
    "기타(흑백)": null,
    "기타(검백)": null,
    "기타(황색)": null,
    "기타(황백)": null,
    "기타(흑황)": null,
    "기타(검정색)": null,
    "기타(흰색/검정)": null,
    "얼룩무늬": null,
    "기타(갈흑색)": null,
    "기타(흰갈색)": null,
    "기타(연한갈색)": null,
    "기타(회백색)": null,
    "기타(백갈색)": null,
    "기타(흑백색)": null,
    "기타(호구)": null,
    "기타(흑갈색)": null,
    "기타(갈색크림색)": null,
    "기타(회갈색)": null,
    "기타(.)": null,
    "기타(황갈색)": null,
    "기타(검은색)": null,
    "기타(베이지색)": null,
    "기타(실버)": null,
    "기타(진갈색)": null,
    "기타(은색, 갈색)": null,
    "기타(연갈백)": null,
    "기타(갈/검/흰)": null,
    "기타(갈백)": null,
    "기타(백)": null,
    "기타(갈흑)": null,
    "기타(갈)": null,
    "기타(흰색,갈색 )": null,
    "기타(흑갈)": null,
    "기타(백갈)": null,
    "기타(흰색+검정 )": null,
    "기타(흑)": null,
    "기타(흰/노)": null,
    "기타(노/흰)": null,
    "기타(백갈흑)": null,
    "기타(흑회)": null,
    "기타(흑갈백)": null,
    "기타(백흑갈)": null,
    "기타(갈백흑)": null,
    "기타(회백)": null,
    "기타(흰색황색)": null,
    "기타(검정흰색)": null,
    "기타(황색,흰색)": null,
    "기타(옅은황색)": null,
    "기타(에프리)": null,
    "기타(갈,흰,검)": null,
    "기타(갈,흰)": null,
    "기타(검,흰)": null,
    "기타(아이보리)": null,
    "기타(금색)": null,
    "기타(검,갈)": null,
    "기타(갈,검)": null,
    "기타(검,갈,흰)": null,
    "기타(크림)": null,
    "기타(흰/회)": null,
    "기타(크림, 흰색)": null,
    "기타(연갈, 흰색)": null,
    "기타(옅은 갈색)": null,
    "기타(흑갈, 흰색)": null,
    "기타(갈/연갈)": null,
    "기타(연갈/흰)": null,
    "기타(갈/검)": null,
    "기타(검정크림색)": null,
    "기타(황갈색흰색)": null,
    "기타(흑색흰색)": null,
    "기타(회색크림색)": null,
    "기타(블랙탄블)": null,
    "기타(흑갈색흰색)": null,
    "기타(흰색크림색)": null,
    "기타(세가지색)": null,
    "기타(검/흰/회색)": null,
    "기타(흰색/회색)": null,
    "기타(갈색/흰색)": null,
    "기타(검정/갈색)": null,
    "기타(검/노)": null,
    "기타(검/노/흰)": null,
    "기타(검정&흰색)": null,
    "기타(갈색,흰색)": null,
    "기타(흰/연갈)": null,
    "기타(누렁)": null,
    "기타(호반색)": null,
    "기타(검정색재색)": null,
    "기타(황갈색황)": null,
    "기타(갈색검정색)": null,
    "기타(호피색)": null,
    "기타(블루멀)": null,
    "기타(연갈/검)": null,
    "기타(회)": null,
    "기타(회/황)": null,
    "기타(흰/황)": null,
    "기타(검,갈색)": null,
    "황토색": null,
    "기타(검정 갈색)": null,
    "기타(흰색&회색)": null,
    "은색": null,
    "기타(호피)": null,
    "기타(옅은갈색)": null,
    "기타(흰색(회색))": null,
    "기타(검정(흰줄))": null,
    "기타(황색(흰줄))": null,
    "기타(흰황색)": null,
    "기타(검흰색)": null,
    "기타(갈색(흰줄))": null,
    "기타(검, 회, 갈)": null,
    "적갈색&밝은갈색": null,
    "기타(회색, 흰색)": null,
    "기타(흑/황색)": null,
    "기타(흰/연갈색)": null,
    "기타(흰/갈색)": null,
    "기타(노랑색)": null,
    "기타(흑/갈/백색)": null,
    "기타(흑/백/갈색)": null,
    "기타(황/백색)": null,
    "기타(검/갈/백색)": null,
    "기타(흰색,연갈)": null,
    "기타()": null,
    "기타(흑황백색)": null,
    "기타(황백색)": null,
    "기타(미색)": null,
    "기타(호피무늬)": null,
    "기타(연노랑)": null,
    "기타(노랑,재색)": null,
    "기타(주황)": null,
    "기타(노랑,흰색)": null,
    "기타(크림&흰색)": null,
    "기타(회황흰검)": null,
    "기타(흰,갈)": null,
    "기타(흰,검)": null,
    "기타(검정회색)": null,
    "황색/검정 얼룩무늬": null,
    "기타(쵸콜릿색)": null,
    "기타(믹스)": null,
    "기타(비숑믹스)": null,
    "기타(푸들믹스)": null,
    "기타(흰색, 갈색)": null,
    "회색(회청색)바탕에 검정얼룩무늬": null,
    "기타(연한 갈색)": null,
    "기타(갈,검,회)": null,
    "기타(황금색)": null,
    "기타(검정,갈색)": null,
    "기타(회색,갈색)": null,
    "기타(크림,흰색)": null,
    "기타(회색,검정)": null,
    "청색": null,
    "기타(흰연황색)": null,
    "갈색&회색": [
      "brown",
      "gray"
    ],
    "기타(회색 흰색)": null,
    "기타(흰색 갈색)": null,
    "기타(흰 갈 검)": null,
    "기타(흰색,갈색)": null,
    "기타(검정,연갈)": null,
    "기타(연갈,검정)": null,
    "기타(황색흰색)": null,
    "기타(검정갈색)": null,
    "기타(검정황색)": null,
    "기타(황색검정)": null,
    "기타(갈색,하양)": null,
    "기타(연갈+검정)": null,
    "기타(연갈+흰색)": null,
    "기타(검+연갈+흰)": null,
    "기타(브린들)": null
  },
  "adoption_text_meaningful_ratio": 0.006091,
  "future_date_counts": {
    "noticeEdt_future": 1298
  },
  "updTm_calendar_date_gap_days": {
    "count": 10507,
    "min": 0,
    "p25": 10.0,
    "median": 21,
    "p75": 40.0,
    "p95": 61.0,
    "max": 70,
    "mean": 25.682592557342723
  },
  "update_gap_note": "Difference between the analysis calendar date and the raw updTm calendar date only. Not an absolute source-update lag; source timezone is unconfirmed."
}
```

## 사용자 확정 상태 규칙

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

## 공식 코드 연결 검증

[상세 참조 코드 보고서](api-reference-data-profile.md)

```json
{
  "blockers": [],
  "mapped_dogs": 10507,
  "unresolved_dogs": 0
}
```
