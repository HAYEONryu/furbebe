# Phase 5 재검토 — 2026-09-21

**판정: 기본 API 기능과 데이터 보존 검증은 통과했지만, 수정이 필요한 결함 2건을 재현했다.**
기존 테스트 성공만으로 설정 변경과 날짜 전환까지 정상이라고 판단할 수 없다.
이번 요청은 검증이므로 구현 코드·`.env`·DEV 데이터는 변경하지 않았다.

## 발견 사항

### P2 — 명시적 DEV 모드에서 .env의 앱 설정 누락

위치: `backend/app/core/database_target.py:70`.

`get_dev_database_settings()`는 지정한 dotenv에서 DEV 접속 값만 읽고
`Settings(_env_file=None, ...)`를 생성한다. 따라서 파일의 `FRONTEND_ORIGIN`,
`DB_CONNECT_TIMEOUT`, `DB_STATEMENT_TIMEOUT_MS`는 설정 객체에 전달되지 않는다.
프로세스 환경변수로 설정했을 때는 적용되지만 `.env`로 설정하면 기본값으로 돌아간다.

합성 DEV 설정 파일로 재현했다. 실제 DEV 접속은 필요하지 않다.

| 설정 | dotenv 입력 | DEV 설정 객체의 실제 값 |
| --- | --- | --- |
| FRONTEND_ORIGIN | `http://localhost:3000` | `http://localhost:5173` |
| DB_CONNECT_TIMEOUT | 11 | 5 |
| DB_STATEMENT_TIMEOUT_MS | 1,234 | 5,000 |

같은 파일을 일반 `Settings(_env_file=...)`로 읽으면 입력값대로 적용된다.
DEV 앱에 `Origin: http://localhost:3000`인 CORS preflight를 보내면 **400**이며
`Access-Control-Allow-Origin`도 없다. `.env`의 origin을 바꿔 실행한 frontend가 API를 사용할 수 없다.

수정 방향: 검증한 DEV DB URL은 유지하면서 일반 앱 설정도 같은 dotenv와 환경변수 우선순위로
읽어야 한다. 사용자 지정 파일·프로세스 환경변수 우선순위·CORS preflight 회귀 검증이 필요하다.

### P2 — 자정을 통과한 요청의 전날 응답이 캐시됨

위치: `backend/app/api/animals.py:41`.

나이·표시 상태·통계는 요청 시작의 `ReadService.today`로 계산하지만,
`cache()`는 조회가 끝난 시점의 날짜로 다음 자정을 구한다.
요청이 KST 자정을 통과하면 전날 기준 응답에 다음 날의 캐시 TTL을 준다.

실제 ReadService와 HTTP route를 사용하고 DB 결과와 시계만 합성해 재현했다.

| 조건 / 응답 | 결과 |
| --- | --- |
| 요청의 계산 기준일 | 2026-12-31, KST 23:59:59 |
| 캐시 헤더 생성 시각 | 2027-01-01, KST 00:00:01 |
| `/api/v1/meta/filters` | 200, `public, max-age=600` |
| `/api/v1/stats/overview` | 200, `public, max-age=60` |
| 필요한 동작 | 전날 기준 결과의 max-age는 0 |

HTTP 캐시가 헤더를 따르면 필터 메타는 최대 10분, 통계는 최대 1분 동안 전날 값을 재사용할 수 있다.
일반 자정에는 표시 상태·오늘 통계, 연도 전환에는 나이 그룹에도 영향을 준다.
실제 브라우저/CDN 캐시 저장 여부까지 시험한 것은 아니며 잘못된 헤더 반환을 확인했다.

수정 방향: 응답 캐시 만료를 조회에 사용한 KST 날짜의 다음 자정으로 제한하고,
헤더 생성 시 그 시각을 지났으면 max-age=0을 반환해야 한다.
자정 직전·직후·조회 중 날짜/연도 전환 회귀 검증이 필요하다.

## 통과한 검증

- Ruff 통과.
- 전체 테스트 **390 passed / 0 skipped**, 67.12초. 기존 라이브러리 deprecation 경고 2개.
- 실제 Supabase DEV 데이터에 대한 Uvicorn HTTP **37개 검사 통과**.
- 동물 7,290건, 조회 전후 여섯 테이블 digest 동일, 무결성 위반 9개 항목 모두 0.
- 목록 1건·24건 모두 데이터 SQL 4회, 상세 3회, 비슷한 동물 4회.
- 이번 관측 시간: 목록 24건 370~512ms, 상세 304~391ms,
  비슷한 동물 417~460ms, 필터 메타 471~687ms.

성능 값은 단일 순차 재실행이며 이전 측정과 조건·캐시 상태가 같다고 보장하지 않는다.
이전 메타 2.1~3.8초가 항상 재현되지는 않았고, 코드 최적화 없이 이번에는 더 빨랐다.
부하 성능 보장이나 영구적인 병목 제거로 해석하지 않는다.

로컬 증거:

- `.local/phase5/pytest-recheck.xml`
- `.local/phase5/dev-api-recheck-20260921T004509Z.json`
- `.local/phase5/recheck-edge-cases.json`

PostgreSQL 통합 테스트는 기존 전용 로컬 테스트 DB에서 수행했다.
검증용으로 기동한 로컬 서버는 종료했다. Phase 6은 시작하지 않았다.
