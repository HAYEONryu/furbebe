# Phase 5 잔여 결함 수정 — 2026-09-29

사용자가 지정한 범위인 [Phase 5 재검토](phase5-review.md)의 결함 2건을 수정했다.

## DEV 모드의 앱 설정

`get_dev_database_settings()`가 DEV 연결값을 검증한 dotenv 파일을 일반 앱 설정에도 사용한다.
기본 `.env`와 호출자가 지정한 파일 모두 `FRONTEND_ORIGIN`, `DB_CONNECT_TIMEOUT`,
`DB_STATEMENT_TIMEOUT_MS`가 반영된다. 프로세스 환경변수가 dotenv보다 우선한다.
실제 DB 연결은 기존 검증을 통과한 DEV URL이 일반 `DATABASE_URL`보다 우선한다.

합성 dotenv의 origin `http://localhost:3000`, 연결 timeout 11초, statement timeout
1,234ms가 모두 적용되며 실제 앱의 CORS preflight가 200을 반환한다.
환경변수 우선순위와 잘못된 설정의 안전한 오류 처리도 검증했다. 이 검사는 DB에 연결하지 않는다.

## 자정을 넘긴 조회의 캐시

성공 응답의 캐시 만료를 `ReadService.today`로 계산한 다음 KST 자정에 맞춘다.
예를 들어 2026-12-31 기준으로 조회한 응답이 2027-01-01 00:00:01에 완성되면
`Cache-Control: public, max-age=0`을 반환한다. 2027-01-01 기준으로 새로 조회한 응답에는
기존 endpoint별 TTL을 적용한다.

목록·상세·유사 동물·태그·메타·통계의 모든 캐시 호출이 조회 기준일을 전달한다.
자정 직전, 정확한 자정, 자정 직후, 연도 전환과 같은 날의 정상 TTL을 검증했다.
목록·태그·메타·통계는 실제 HTTP route와 ReadService를 거치며 DB 결과와 시계만 합성한다.

## 검증

- 관련 설정·캐시·Read API 테스트: **72 passed**, 회귀 사례 20개 추가.
- 전체 백엔드 PostgreSQL 포함 테스트: **651 passed, 0 skipped**, 214.03초.
- `ruff check .`: 통과. 변경 Python 파일의 Ruff format 검사도 통과.
- `git diff --check`: 통과.
- 기존 Starlette/httpx·AnyIO deprecation 경고 2건은 남아 있다.

전체 검사는 localhost 전용 새 PostgreSQL 클러스터와 `furbebe_test_phase5_fixes_20260929`
DB를 사용했고 검증 후 직접 시작한 서버를 종료했다.
로컬 증거는 `.local/phase5-fixes-20260929/pytest.xml`에 보관한다.
이번 수정 검증에서는 DEV에 연결하지 않았다. 기존 DEV 성능·데이터 집계는 과거 측정값으로 유지한다.
루트 `.env`, DB schema, 태그 규칙, 기존 프런트엔드 작업은 이번 변경 범위에 포함하지 않는다.

## 변경 파일

- `backend/app/core/database_target.py`: 일반 앱 설정을 DEV dotenv에서 함께 로드.
- `backend/app/api/animals.py`: 조회 기준일로 캐시 만료 계산.
- `backend/tests/test_dev_database.py`: dotenv·환경변수·CORS·설정 오류 회귀 검사.
- `backend/tests/test_read_cache.py`: 날짜 전환과 HTTP 캐시 회귀 검사.
- README와 Phase 5 보고 문서: 수정 전 기록을 보존하고 현재 결과 연결.
