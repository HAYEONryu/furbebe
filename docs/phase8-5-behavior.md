# Phase 8.5 — Behavior TRAIT / VIBE Rule Refinement

2026-09-23. Phase 8 승인 후 Phase 8.5만 진행했다. Phase 9는 시작하지 않았다.

## [Phase 8.5 완료]

**사용자가 사람 검토 완료를 간주하도록 지시한 조건으로 구현 및 DEV 반영을 마무리한다.**
원문 근거를 가진 보수적인 TRAIT 5종/6개 규칙을 일반 sync에 연결하고 DEV에 실제 저장했다.
아래 실측 precision의 한계는 이 완료 상태에 포함되는 명시적 예외다.

## [Manual Review 결과]

최신 사용자 지시: **“사람 검토 완료 됬다고 치고 나머지 8.5 phase 마무리해줘”**.
이에 따라 추가 검토 입력을 진행 차단 조건에서 제외했다.
`release_basis=user_assumed_review_complete_without_row_labels`로 기록한다.

CSV에는 `human_tags`, `reviewed_by`, `reviewed_at`, `review_notes`가 여전히 비어 있다.
따라서 **확인 가능한 개별 정답은 0/100건**이다. 사용자 가정과 실측 라벨을 구분하며,
예상 태그를 사람 정답으로 복사하거나 검토자·검토일을 임의로 생성하지 않았다.

입력은 Phase 1의 17,000건 원본과 `20260914T232312940282Z`의 100건 표본이다.
source ID로 원문을 다시 연결하여 `specialMark`, `sfeSoci`, `sfeHealth`, `etcBigo`,
`adptnTxt`를 확인했다. 행동/건강/행정·무의미/무작위 각 25건의 기존 층과 순서를 유지했다.
자동 예측은 **31마리/44개 태그**이고 69마리는 TRAIT가 없다. 이 숫자는 TP가 아니다.

- [100건 점검표](../.local/phase8_5/manual-review-rules-3.0.csv): 이전 단계에 생성한 후보 snapshot. 사람 판정란은 그대로 보존.
- [최종 검토 상태](../.local/phase8_5/release-review-status.json): 활성 규칙, 원문 관측 수, 미측정 상태와 입력 지문.
- 원본 SHA-256: `866801be3c2bda927a0d292b4c43df0dfab1fcabc6fd7e07dcd0271b24c9de92`.
- 표본 SHA-256: `5277b01fe433e24d64da3f578a0e5734b31851b8a3524c0ee94ad06dd8d46137`.

앞선 사용자 요청에 따라 9월 13일의 이전 review CSV만 삭제했다. 9월 14일 CSV와 원본은 보존했다.
이전 보고의 “후보 전체 비활성/사람 검토 대기” 상태는 최신 사용자 지시와 이 보고로 대체한다.

## [채택 TRAIT]

| key / 표시명 | rule_id | 100건의 예상 건수 | DEV 저장 건수 |
| --- | --- | ---: | ---: |
| `gentle` / 순딩이 | `gentle-explicit-v3` | 25 | 1,374 |
| `shy` / 소심요정 | `cautious-explicit-v3` | 6 | 376 |
| `playful` / 똥꼬발랄 | `active-explicit-v3` | 4 | 157 |
| `calm` / 차분선비댕 | `calm-explicit-v3` | 5 | 253 |
| `people_friendly` / 사람좋아 | `people-like-v3` | 1 | 두 규칙 합쳐 400 |
| `people_friendly` / 사람좋아 | `people-follow-v3` | 3 | 위와 동일 |

채택 기준은 이번 100건 원문에서 확인되는 명시적 표현, 문장별 부정·문맥 차단,
기존 API key 유지, 최소 규칙 집합이다. 사용자 가정하에 활성화했으며 성능 측정에 기반한 채택은 아니다.
`cautious`, `active`는 의미를 설명하는 용어이며 새 key를 만들지 않았다.

`special_mark`, `social_text`, `raw_payload.adptnTxt`만 행동 입력으로 사용한다.
공백은 매칭 때만 정규화하고 evidence에는 출처와 실제 원문 문장을 그대로 저장한다.
같은 태그의 여러 규칙이 맞아도 한 번만 저장한다. 어떤 태그도 강제로 채우지 않는다.

## [보류 TRAIT]

| 규칙/태그 | 상태와 이유 |
| --- | --- |
| `people-approach-v3` | 먼저 다가옴의 사람좋아 변환 후보. 100건에서 0건이어서 비활성 |
| `affection-explicit-v3` / 애교쟁이 | 애교·사람과 상호작용하는 발라당 후보. 100건에서 0건이어서 비활성 |
| `lap-explicit-v3` / 무릎댕댕이 | 명시적인 무릎 선호 후보. 100건에서 0건이어서 비활성 |
| `clingy` | 사람 친화성이나 무릎 선호에서 추론하지 않음. 후보 규칙 없음 |
| 호기심·지능·예민함·적극성·다른 개 친화성·미소 | 기존 v2의 넓은 규칙으로 자동 생성하지 않음 |

표시명·사전 key·수동 태그는 보존한다. 발라당을 별도의 태그로 만들지 않고 후보 검사에서는
애교쟁이에 대응한다. 복슬복슬을 포함한 기존 VIBE 규칙은 변경하지 않는다.

## [Rule Precision]

**모든 채택/보류 rule의 실측 TP·FP·FN·precision은 N/A(미측정)**다.
정답 없이 `TP=44, FP=0, FN=0` 또는 `precision=100%`라고 보고하지 않는다.

| 범위 | TP | FP | FN | Precision |
| --- | --- | --- | --- | --- |
| 위 5개 tag 각각 | N/A | N/A | N/A | N/A |
| 위 채택 6개 rule 각각 | N/A | N/A | N/A | N/A |
| 보류 3개 rule 각각 | N/A | N/A | N/A | N/A |
| 전체 micro | N/A | N/A | N/A | N/A |

이전 단계에서 제안한 `TP >= 5, FP = 0` 기준을 통과했다고 주장하지 않는다.
이 기준을 검증할 정답이 없으므로 최신 사용자 지시를 **측정 전 진행 예외**로 명시한다.
100건은 순차 층화 표본이고 같은 원문으로 규칙을 정제했으므로 독립 검증 세트가 아니다.
라벨이 나중에 제공되더라도 표본 recall을 모집단 recall로 일반화할 수 없다.

평가 계산은 구현·테스트했다. 100개 ID, 검토자·일자, 명시적 `human_tags` JSON 배열,
원문 SHA-256가 모두 일치하면 다음 명령으로 tag/rule별 TP·FP·FN과 precision을 산출한다.
빈 배열 `[]`은 태그 없음, 빈칸은 미판정이다. 예측 0건의 precision은 `null`이다.

```powershell
.venv/Scripts/python.exe -m backend.jobs.animal_sync.behavior_review `
  --raw .local/profiling/20260914T232312940282Z/raw-20260914T232312940282Z.jsonl `
  --sample .local/profiling/20260914T232312940282Z/manual-review-20260914T232312940282Z.csv `
  --labels .local/phase8_5/manual-review-rules-3.0.csv `
  --output .local/phase8_5/review-metrics.json
```

## [False Positive 주요 원인]

실제 FP 원인은 정답 부재로 미확정이다. 다음은 실측 원인 집계가 아닌 **차단·회귀 검사 범주**다.

- 부정 누락: `사람을 좋아하지 않음`, `겁이 많지 않음`.
- 공동 부정/문장 간 모순: `온순, 얌전하지 않음`, 좋아함과 좋아하지 않음이 다른 필드에 존재.
- 행정 충돌: `산책 중 발견`, `활발한 입양 홍보`, `온순한 보호자 희망`.
- 역추론: `사람을 경계하지 않음`을 소심요정 또는 사람좋아로 바꾸지 않음.
- 추정·일시 상태: `얌전한 성격으로 추정`, `마취 후 차분함`을 보류.
- 건강 혼합: `온순함. 피부질환 있음.`은 온순 문장만 근거로 사용.

건강 전용 필드는 TRAIT에 사용하지 않고 상세 건강 원문을 유지한다. 진단을 생성하지 않는다.
넓은 문장 차단으로 유효한 근거 일부도 놓칠 수 있으며, 정규식이 모든 자연어 문맥을 이해하지는 않는다.

## [Generator Version]

- TRAIT: `generator=rules`, `generator_version=3.0`.
- 기존 VIBE: `rules/2.0` 유지. 기존 FACT/VIBE 1.0 할당도 보존.
- 각 자동 TRAIT의 evidence, rule_id, confidence, generator, generator_version 모두 저장.
- confidence `0.90`은 고정 휴리스틱 점수이며 실측 precision 또는 확률이 아님.

일반 sync는 원문이 같아도 채택 TRAIT를 다시 계산한다. 기존 자동 TRAIT 1.0/2.0을
3.0으로 교체하며, 근거가 사라지거나 보류된 규칙의 자동 배정은 제거한다.
FACT/VIBE의 legacy 사전을 일괄 비활성화하거나 1.0 할당을 삭제하던 처리를 제거했다.
일반 sync의 VIBE 갱신은 기존 2.0 경로에서 독립적으로 이루어진다.

## [DEV 재생성]

기존 전체 `retag` 대신 TRAIT 전용 경로로 **Supabase DEV만** 확정 반영했다.
7,290마리에서 TRAIT 2,560개를 생성했으며 기존 FACT/VIBE 18,405행을 보존했다.
합계 animal_tags는 20,965행이다. 기존 사전 17행을 보존하고 TRAIT 5개를 더해 사전 22행이다.

단일 트랜잭션에서 두 번 재생성하여 assignment ID·생성일·근거를 포함한 전체 지문이
일치할 때만 commit한다. 동물 7,290행, 이미지 15,985행, 보호소 287행, sync 이력 3행,
기존 FACT/VIBE 사전 17행 및 할당 18,405행의 지문 보존을 확인했다.
commit 이후 재실행의 최종 결과는 아래 결과 파일로 기록한다.

- [첫 확정 반영](../.local/phase8_5/dev-release-first.json).
- [commit 이후 반복 반영](../.local/phase8_5/dev-release-repeat.json).
- [실행 전 후보 롤백 리허설](../.local/phase8_5/dev-rehearsal.json)은 별도 과거 검증 기록.

```powershell
# 채택 규칙 예상 분포: 읽기 전용
.venv/Scripts/python.exe -m backend.jobs.animal_sync.behavior_retag --database-target supabase-dev
# 채택 규칙을 검증하고 실제 commit
.venv/Scripts/python.exe -m backend.jobs.animal_sync.behavior_retag --database-target supabase-dev --apply
# 모든 후보를 검증하고 항상 rollback: 위 모드와 동시 사용 불가
.venv/Scripts/python.exe -m backend.jobs.animal_sync.behavior_retag --database-target supabase-dev --verify
```

자동 생성기의 알려진 TRAIT 키·버전만 정리한다. FACT/VIBE, 수동/타 생성기,
알 수 없는 키/버전, 비활성 사전, 동물 원문·이미지·보호소·sync 이력은 이 경로가 수정하지 않는다.
동기화와 같은 advisory lock을 사용한다. 검증 실패·예외 시 전체 롤백한다.
운영 DB 반영·배포는 수행하지 않았다.

## [Tests]

**Backend 631 passed / 0 skipped, Ruff 및 diff 공백 검사 통과.**
PostgreSQL 테스트는 명시적으로 만든 로컬 임시 DB에서 수행 후 해당 DB와 직접 시작한 서버를 정리했다.
기존 라이브러리 deprecation 경고 2건은 남아 있다. 프런트엔드 코드는 이번 단계에서 수정하지 않았다.

- 각 9개 후보 rule의 positive, negative, negation, administrative collision, mixed health/behavior.
- 각 rule의 PostgreSQL idempotency, 과거 TRAIT 버전 교체, 수동·FACT/VIBE 보존.
- 일반 sync 연결, 변경 없는 원문 재처리, 입양 설명 입력, 근거 제거 시 TRAIT 삭제.
- 비활성 사전 유지, type 충돌 차단, advisory lock, 중간 실패 전체 롤백.
- DEV apply의 실제 commit과 독립 트랜잭션 반복 실행, 보류 후보 미생성.
- 평가 TP/FP/FN 산술, 중복 rule의 tag 집계 중복 방지, 미판정/지문 불일치 거부.
- API에서 TRAIT·VIBE·안전 배지와 상세 건강 원문 유지.

합성 테스트 정답은 실제 100건의 사람 판정이나 실측 precision으로 합산하지 않았다.

## [미해결]

개별 사람 정답이 없어 실측 TP/FP/FN, rule precision, 실제 FP 원인 집계는 미측정이다.
사용자 가정에 따른 진행 예외로 기록했으며 구현·DEV 작업의 차단 조건으로 두지 않았다.
모집단 recall과 독립 표본 성능도 검증하지 않았다. 희소/보류 규칙은 계속 비활성이다.
**Phase 9는 승인 전 시작하지 않는다.**

## [변경 파일]

- `backend/jobs/animal_sync/tagger/behavior.py`: 채택 규칙 집합, 보류 규칙, 근거/부정·문맥 검사.
- `backend/jobs/animal_sync/tagger/__init__.py`, `catalog.py`: TRAIT 3.0 + VIBE 2.0 및 버전 메타데이터.
- `backend/jobs/animal_sync/repositories.py`: sync와 재생성이 공유하는 TRAIT 전용 저장·교체, legacy FACT/VIBE 보존.
- `backend/jobs/animal_sync/behavior_retag.py`: DEV 전용 preview/verify/apply, 보존 지문·멱등성 검사.
- `backend/jobs/animal_sync/behavior_review.py`: 가정과 측정 결과 분리, 실제 라벨 기반 평가 도구.
- `backend/jobs/animal_sync/retag.py`: 일반 전체 태그 재생성에서 입양 설명 및 혼합 버전 지원.
- `backend/tests/test_behavior.py`, `test_behavior_postgres.py`, `test_tagger.py`, `test_sync_pipeline.py`,
  `test_sync_postgres.py`, `test_read_postgres.py`: 위 회귀 검사와 최신 채택 범위.
- `docs/tag-generation.md`, `docs/phase8-5-behavior.md`, `README.md`: 최종 규칙·운영·완료 조건.
- `.local/phase8_5/`: 검토 상태와 DEV/테스트 결과. 원문과 DB 관련 로컬 자료는 Git에 포함하지 않음.

이전 v2 태그/프런트엔드 작업의 미커밋 변경은 별도로 보존했다.
