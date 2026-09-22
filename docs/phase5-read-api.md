# Phase 5 — FastAPI v1 Read API 완료 보고

최종 검증일: **2026-09-21, Asia/Seoul**. Python 3.14.6 / Windows.

**후속 재검토:** 기존 테스트·DEV 검증은 다시 통과했지만 설정 반영·자정 캐시에서
미수정 결함 2건을 재현했다. 현재 판정은 [Phase 5 재검토](phase5-review.md)를 함께 참조한다.

이전에 구현한 읽기 API와 쿼리 성능 수정을 재검증하고 문서 정리를 완료했다.
전체 테스트 **390 passed / 0 skipped**, Ruff 통과. 실제 Supabase DEV 데이터에 대한
Uvicorn HTTP **37개 검사**가 성공했다. 조회 전후 여섯 도메인 테이블의 digest가 동일하다.

## Endpoint와 API Contract

원본 `FURBEBE_FASTAPI_V1_CONTRACT.md`와 이후 사용자 확정 정책을 기준으로 한다.
저장소의 [API Contract](api-contract.md)에 현재 정책과 구현 상태를 반영했다.

| Method | Path | 역할 |
| --- | --- | --- |
| GET | `/health` | 실제 PostgreSQL 연결 상태 |
| GET | `/api/v1/animals` | 필터·검색·정렬·페이지 목록 |
| GET | `/api/v1/animals/{animal_id}` | source·notice·animal·found·images·tags·설명·보호소·입양 홍보 상세 |
| GET | `/api/v1/animals/{animal_id}/similar` | 동일 동물을 제외한 규칙 기반 추천 |
| GET | `/api/v1/tags` | 실제 DB 태그 사전, type·active_only 필터 |
| GET | `/api/v1/meta/filters` | 현재 데이터에 존재하는 필터 선택지 |
| GET | `/api/v1/stats/overview` | 전체·오늘 신규·대표 이미지·마지막 성공 sync 통계 |

router → service → repository → SQLAlchemy → psycopg → PostgreSQL 경계를 유지한다.
ORM과 Pydantic 응답 모델은 분리되어 있고 `raw_payload` 전체, favorite 정보,
`animals_active`, 추천 점수는 반환하지 않는다. 행동·건강 설명은 nullable 원문이며 추론하지 않는다.
입양 홍보 값이 모두 없으면 null, 일부만 있으면 나머지 필드를 null로 둔 object다.

## Filtering과 Pagination

- 기본값은 `page=1`, `page_size=24`, `sort=recent`, `tag_match=any`다. page_size는 1~60이다.
- sido·sigungu·breed·sex·neutered·size_group·age_group·tag·tag_match·process_state·q·sort를 지원한다.
  `region`, `size` 등 계약에 없는 query는 422다.
- 지역은 공식 코드 `sido=upr_cd`, `sigungu=org_cd`로 입력·반환한다.
  기존 공식 참조 자료의 2026-09-15 버전 매핑을 사용하며 지역명은 `region.display`다.
  매핑되지 않은 source 지역은 코드를 추정하지 않고 null과 원문 display를 반환한다.
- 체중은 ≤5 / >5~10 / >10~20 / >20kg이며 NULL만 unknown이다. 0kg는 tiny다.
- 나이는 **요청 시 Asia/Seoul 연도 - birth_year**로 계산한 추정값이다.
  ≤1 / 2~4 / 5~8 / ≥9, NULL은 unknown이며 그룹을 DB에 저장하지 않는다.
- 표시 상태는 원문이 `보호중`이고 공고 시작일에서 KST 달력 기준 10일 이상 지난 경우
  `입양 가능`이다. 시작일이 없거나 미래이면 원문을 유지한다. 목록·상세·필터·메타가 같은 계산을 쓴다.
- `?tag=puppy&tag=white`처럼 반복 query를 받고 중복 key는 제거한다.
  any는 하나 이상, all은 모두 일치해야 한다. 없는 key는 404 `TAG_NOT_FOUND`,
  사전에 존재하지만 비활성인 태그만으로는 검색 결과가 생기지 않는다.
- `q`는 최대 50자로 품종·보호소명·지역 표시 원문의 부분 문자열을 검색한다.
  `%`, `_`, 역슬래시는 검색 문자열 그대로 처리한다.
- recent·notice_end·weight_asc·weight_desc·age_youngest·age_oldest를 지원한다.
  각 정렬의 기본 컬럼 뒤에 source_updated_at DESC, id ASC를 적용하고 NULL은 마지막에 둔다.
- offset/page 방식이며 total·total_pages·has_next·has_previous를 반환한다.
  결과가 없으면 200과 빈 items, total=0, total_pages=0이다. 페이지를 넘겨도 안정적인 순서를 유지한다.

동물·태그 key별 노출은 하나로 합친다. 연도가 바뀌어 현재 그룹과 맞지 않는
`rules/1.0` 나이 태그는 제외하며 조회 중 새 태그를 생성하거나 DB를 갱신하지 않는다.

## Similar / Meta / Stats

비슷한 동물은 동일 시도 +3, 동일 크기 그룹 +2, 동일 품종 +2, 동일 성별 +1,
공유하는 노출 태그 하나당 +2, 동일 나이 그룹 +1로 계산한다.
알 수 없는 지역·크기·성별·나이에 일치 점수를 주지 않고 본인을 제외한다.
동점은 recent 순서로 결정하며 limit은 기본 4, 최소 1, 최대 12다.

메타는 DB의 현재 값으로 지역·품종·성별·중성화·크기·나이·표시 상태를 집계한다.
태그 사전도 실제 DB를 조회하며 기본은 active_only=true, type은 fact/trait/vibe다.

`new_today`는 **KST 오늘 00:00 이상, 다음 날 00:00 미만의 first_seen_at** 수다.
`with_primary_image`는 source/adoption 이미지가 하나 이상 있는 동물 수이며
`last_synced_at`는 성공한 sync_runs의 최대 finished_at이다. 성공 기록이 없으면 null이다.

## 실제 DEV DB 검증

기존 `.env`의 DEV 연결을 검증한 뒤 loopback Uvicorn에 실제 HTTP 요청을 보냈다.
DEV에는 migration·fixture·sync·reset을 수행하지 않았다.

| 검증 | 결과 |
| --- | --- |
| HTTP 검사 | 37개 성공: 목록·페이지·필터·검색·6개 정렬·상세·추천·태그·메타·통계·오류 |
| DB revision | `20260915_0001` |
| 동물 / 고유 source 동물 | 각각 7,290 |
| 보호소 / 이미지 | 287 / 15,985 |
| 태그 사전 / 동물 태그 / sync_runs | 17 / 18,405 / 3 |
| 조회 전후 데이터 | 여섯 테이블 digest 동일 |
| 중복·고아 참조·confidence 등 무결성 위반 | 9개 집계 항목 모두 0 |
| 도메인 SQL | 모두 읽기 전용 transaction |
| 통계 | animals_total=7,290, new_today=0, with_primary_image=7,289 |
| 마지막 성공 sync | 2026-09-15T23:29:06.082939Z, KST 2026-09-16 08:29:06 |
| 메타 선택지 | 시도 16, 품종 82, 성별 3, 중성화 3, 크기 5, 나이 4, 표시 상태 8 |

이 수치는 기존 DEV snapshot의 조회 결과이며 2026-09-21에 source를 다시 수집한 결과가 아니다.
검증 중 source API 요청은 없고 읽기 API도 upstream API를 호출하지 않는다.

## N+1과 성능

| HTTP 조회 | 최초 측정 (ms) | 반복 측정 (ms) | 데이터 SQL 수 |
| --- | ---: | ---: | ---: |
| 목록 24건 | 704.76 | 698.79 / 592.91 | 4 |
| 상세 | 398.54 | 382.58 | 3 |
| 필터 메타 | 3,790.67 | 2,092.99 | 1 |
| 비슷한 동물 | 862.90 | 520.33 | 4 |

목록 1건과 24건 모두 count·본체·이미지·태그 조회의 **4회**였다.
태그 필터를 사용하면 사전 존재 확인 1회가 추가되어 5회다. 빈 목록은 count만 조회한다.
SET LOCAL 및 transaction 제어는 데이터 SQL 수에서 제외했다.

HTTP 시간은 로컬 서버 처리와 원격 DEV 왕복을 포함한 단일 순차 실행 관측값이다.
최초/반복은 이 검증 프로세스의 호출 순서이며 DB 캐시를 비우지 않았다.
부하 시험·백분위 지연·운영 SLA를 뜻하지 않는다.

현재 가장 느린 경로는 메타 집계다. 기존 구현에서 모든 동물의 지역 정규화와 파생 그룹을
집계하므로 향후 데이터량이 늘면 다시 측정할 대상이다. 이번에는 추가 인덱스·캐시를 도입하지 않았다.
이전 작업의 태그 any/all·추천 쿼리는 태그 집합을 한 번 집계하는 방식으로 수정되어 있으며
DEV 데이터에서 statement timeout 없이 동작함을 재확인했다.

## Error Handling과 transaction

404 ANIMAL_NOT_FOUND/TAG_NOT_FOUND, 422 VALIDATION_ERROR, 503 SERVICE_UNAVAILABLE,
500 INTERNAL_ERROR, 일반 HTTP 오류의 INVALID_REQUEST를 공통 envelope로 반환한다.
X-Request-ID를 응답 헤더와 오류 JSON에 제공한다. SQL·traceback·DB URL·secret은 노출하지 않는다.

도메인 조회는 요청당 REPEATABLE READ / READ ONLY transaction이다.
`DB_STATEMENT_TIMEOUT_MS`는 기본 5,000ms이며 `SET LOCAL statement_timeout`으로 적용한다.
session pooler의 시작 옵션 처리와 무관하게 제한이 적용되는지 로컬 실제 DB에서 확인했다.
쓰기 거부와 100ms 제한의 느린 SQL 취소도 통합 테스트로 검증했다.

성공 캐시 헤더는 목록·통계 60초, 상세·추천 300초, 태그·메타 600초다.
날짜 파생값을 위해 KST 자정까지 남은 시간으로 TTL을 제한한다. 오류에는 성공용 캐시를 적용하지 않는다.

## Tests / Ruff / 재현

| 검사 | 결과 |
| --- | --- |
| `ruff check .` | 통과 |
| 전체 `pytest backend/tests -q` | **390 passed / 0 skipped**, 99.68초 |
| PostgreSQL 통합 검사 | 별도로 생성한 로컬 disposable DB에서 115개 실행 |
| 기존 라이브러리 경고 | Starlette TestClient의 httpx·AnyIO deprecation 2개 |
| 실제 DEV HTTP | 37개 통과, 데이터 불변성·무결성 확인 |

전체 suite는 source 수집·정규화·sync·migration과 기존 테스트를 포함한다.
Phase 5 검사는 합성 경계값·NULL·모든 필터·안정적 정렬·연도 변경·상태 9/10일·추천·오류·N+1을 포함한다.
DEV의 실데이터 검증과 로컬 합성 테스트 결과를 구분한다.

```powershell
.\.venv\Scripts\python.exe -m ruff check .
# 전용 로컬 테스트 DB를 FURBEBE_TEST_DATABASE_URL로 지정한 환경에서 실행
.\.venv\Scripts\python.exe -m pytest backend/tests -q --junitxml=.local/phase5/pytest.xml
# 기존 DATABASE_URL_dev / SUPABASE_URL_dev를 사용한 DEV 읽기 전용 검증
.\.venv\Scripts\python.exe -m backend.jobs.read_api_verification
```

FURBEBE_TEST_DATABASE_URL 미지정 시 PostgreSQL 검사는 skip되므로 전체 검증 완료로 보지 않는다.
DEV 연결값을 통합 테스트용 변수에 넣지 않는다. 값은 로그·문서·명령행에 출력하지 않는다.
앱의 일반 실행과 명시적 DEV 실행 방법은 [README](../README.md#backend-실행)를 참조한다.

로컬 검증 증거는 `.local/phase5/pytest.xml`, `.local/phase5/dev-api-verification.json`이다.
Git에는 집계 결과와 실행 방법만 기록한다.

## 변경 파일과 Phase 6 Readiness

Phase 5 구현은 `api/animals.py`, `services/animals.py`, `services/regions.py`,
`repositories/animals.py`, `schemas/animals.py`, `data/regions.json`, 공통 오류·앱·DB 연결 코드,
`jobs/read_api_verification.py`, `tests/test_read_api.py`, `tests/test_read_postgres.py`,
`tests/read_fixtures.py`에 있다.

이번 재개에서는 구현을 재검증하고 README, architecture, api-contract, sync-design의
이전 상태 문구를 갱신했으며 이 완료 보고를 추가했다. `.env`와 기존 migration은 변경하지 않았다.

기본 읽기 API 기능 검증은 통과했다. 이후 [재검토](phase5-review.md)에서
설정 반영·자정 캐시 결함 2건을 확인했으므로 기존의 무조건적인 완료 판정을 보완한다.
메타 집계 지연, 버전 고정 지역 매핑, 수집 당시 snapshot이라는 한계는 위에 기록했다.
Docker build/run은 미검증이며 배포 단계 범위다. Phase 6은 사용자 승인 전 시작하지 않는다.
