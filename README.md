# FURBEBE — Phase 8 Dog Detail

React Router Framework + React + Vite + JavaScript/JSX + Tailwind 기반의 프런트엔드를
`frontend/`에 구현했습니다. Cloudflare Workers SSR loader가 FastAPI v1을 호출하며,
데이터 경계는 React → FastAPI → PostgreSQL입니다.
`/`는 실제 API 사진을 사용하는 Hero·Quick Discovery·최근 등록 동물을,
`/dogs`는 검색·필터·정렬·페이지·관심 저장을 제공합니다. `/dogs/:animalId`는 실제 사진 갤러리,
기본·발견 정보, 원문 설명, 보호소 연락, 조건부 홍보 정보, 관심 저장·공유와 유사 동물을 제공합니다.
사용자 선택에 따라 개·고양이·기타 구조동물을 함께 표시합니다.
필터·정렬·페이지는 URL에 보존하며, 품종·지역·상태·그룹 옵션은 FastAPI 메타를 사용합니다.
지역명을 표시하기 위해 기존 지역 코드 응답에 `sido_label`·`sigungu_labels`를 호환 확장했습니다.

## Frontend 실행

태그 생성은 [TRAIT 3.0 / VIBE 2.0 규칙과 재생성 안내](docs/tag-generation.md)를 따릅니다.
성격·관계·색상·현재 몸집 태그와 별도 안전 배지를 제공하며 건강·나이·성별 태그는 생성하지 않습니다.

Node.js 22.22 이상이 필요하며 Node.js 24.18.0 / npm 12.0.2에서 검증했습니다.
앞서 Backend를 `127.0.0.1:8080`에서 실행한 후 별도 터미널에서 실행합니다.

```powershell
npm --prefix frontend ci
npm run dev
```

개발 주소는 `http://127.0.0.1:5173`입니다. 개발 API 기본값은 `http://127.0.0.1:8080`,
production 기본값은 `https://api.furbebe.com`입니다. 변경이 필요할 때만
`frontend/.env.example`을 `frontend/.env.local`로 복사해 `VITE_API_BASE_URL`을 설정합니다.
이 값은 공개 build-time 설정이며 production 빌드에는 production API 주소를 지정합니다.
**루트 `.env`를 frontend로 복사하지 않습니다.** Vite는 frontend 디렉터리의 공개 API 변수 하나만 허용합니다.

```powershell
npm test
npm run lint
npm run build
npm --prefix frontend run check:worker
npm run preview
```

`check:worker`는 `wrangler deploy --dry-run`이며 실제 배포하지 않습니다.
preview 주소는 `http://127.0.0.1:4173`이며 빌드 시 선택한 API를 사용합니다.
기본 preview의 Main·목록·상세에는 `https://api.furbebe.com`의 운영 준비가 필요합니다.
구조는 [Phase 6 보고](docs/phase6-frontend-base.md), Main·목록은 [Phase 7 보고](docs/phase7-discovery.md),
상세 화면·검증·잔여 항목은 [Phase 8 보고](docs/phase8-detail.md)를 참조합니다.
상세 화면은 detail와 `similar?limit=4` 두 API만 사용합니다. 설명·행동·건강 정보는 원문이 있을 때만 표시합니다.
Phase 8 승인 후 [Phase 8.5 행동 규칙 정제](docs/phase8-5-behavior.md)를 구현하고 DEV에 반영했습니다.
사람 검토 완료를 간주하라는 사용자 지시로 진행했으며 실측 precision은 미측정입니다.
보수적인 TRAIT 5종/6개 규칙만 활성화했습니다. **Phase 9는 승인 전 시작하지 않습니다.**

## Phase 5 구현

FastAPI → service → repository → SQLAlchemy → psycopg → PostgreSQL로
동물 목록·상세·비슷한 동물·태그·필터·통계 읽기 API를 제공합니다.
기존 수집·정규화·UPSERT와 읽기 API를 Supabase DEV PostgreSQL에서 검증했습니다.

## Phase 5 검증 — 2026-09-21

`/health`, `/api/v1/animals`, `/api/v1/animals/{animal_id}`,
`/api/v1/animals/{animal_id}/similar`, `/api/v1/tags`, `/api/v1/meta/filters`,
`/api/v1/stats/overview`를 구현했습니다. 모든 도메인 조회는 읽기 전용 transaction입니다.

실제 DEV 동물 **7,290건**을 대상으로 Uvicorn HTTP **37개 검사**를 통과했습니다.
조회 전후 여섯 도메인 테이블의 데이터 digest가 일치하며 무결성 위반은 0건입니다.
목록은 1건·24건 모두 SQL 4회로 N+1이 없습니다. 나이·표시 상태·오늘 통계는 Asia/Seoul 기준입니다.
이번 HTTP 측정에서 목록 24건은 593~705ms, 상세 383~399ms, 비슷한 동물 520~863ms,
필터 메타 2,093~3,791ms였습니다. 메타 집계가 가장 느리며 부하 시험 결과는 아닙니다.

검증 범위·정책·실행 방법·테스트 결과는 [Phase 5 완료 보고](docs/phase5-read-api.md)에 있습니다.
전체 테스트 **390 passed / 0 skipped**, Ruff 통과. PostgreSQL 테스트는 별도 로컬 DB에서 실행했습니다.
후속 [재검토](docs/phase5-review.md)에서 DEV 설정 반영·자정 캐시 결함 2건을 재현했으며 아직 수정하지 않았습니다.
Phase 5 승인 후 Phase 6 프런트엔드 기반을 구현했습니다. Backend Docker build/run은 미검증입니다.

## Phase 4B 검증 — 2026-09-16

Supabase DEV PostgreSQL 17.6에 `20260915_0001`을 적용했으며, 여섯 도메인 테이블의
컬럼·PK·FK·UNIQUE·CHECK·인덱스가 로컬 PostgreSQL 및 SQLAlchemy metadata와 일치합니다.
315건 smoke sync와 같은 capture 재실행에서 **신규 0 / 변경 0 / 동일 315 / 중복 증가 0**을 확인했습니다.

기본 API 조회의 모든 페이지에서 **7,290건**을 수신·저장했습니다. 보호소 287, 이미지 15,985,
태그 사전 17, 동물 태그 18,405행이며 중복·고아 참조·confidence 범위 위반은 모두 0입니다.
capture 전체와 DB의 source ID 및 raw payload도 일치합니다. 실행 시간은 약 39.79초입니다.

**`--full`은 API 기본 조회 범위의 모든 페이지를 수집합니다. 과거 전체 이력 수집을 뜻하지 않습니다.**
이번 저장 데이터의 발견일은 2026-08-16~09-16입니다. 범위 차이 확인용 조회에서 기본 조회와
이 기간의 명시적 조회가 같은 7,383건을 반환했고, Phase 1 기간 조회는 60,702건을 반환했습니다.
7,383건은 이후 시점의 확인 값이며 기존 7,290건 capture와 합산하지 않습니다.

전체 테스트 **300 passed / 0 skipped**, Ruff 통과. PostgreSQL 통합 테스트는 별도 로컬 테스트 DB에서,
DEV 최종 검사는 읽기 전용 transaction에서 실행했습니다.
실행 명령·counter 의미·상세 결과는 [동기화 운영 문서](docs/sync-design.md)에 있습니다.
위 수치는 Phase 4B 당시 기록입니다. 현재 읽기 API 검증은 상단 Phase 5 결과를 기준으로 합니다.

## Phase 4A 검증 기록 — 2026-09-16

전체 테스트 **282 passed / 0 skipped**, Ruff 통과. 별도 로컬 PostgreSQL에서
2026-09-14 하루의 실제 API **315건**을 적재했고, 같은 capture를 다시 실행해
**신규 0 / 갱신 315 / 중복 0** 및 내부 ID 보존을 확인했습니다.
합성 1,001건으로 여러 batch와 반복 실행도 검증했습니다.

CLI 기본 대상은 loopback의 `furbebe_dev*` 또는 `furbebe_test*` DB입니다.
Phase 4B에서 `--database-target supabase-dev`를 명시한 DEV 연결을 추가했습니다.
위 갱신 315건은 Phase 4A 당시의 집계입니다. 현재 `updated_count`는 내용이 변경된 동물만 세며,
같은 payload는 `unchanged_count`로 구분합니다. [Phase 4A 결과](docs/phase4a-local-sync.md)는 당시 기록입니다.
GitHub Actions 스케줄은 후속 범위이며, 읽기 API는 Phase 5에 구현했습니다.

## Backend 실행

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt -c backend/requirements-runtime-lock.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8080
```

프로젝트 `.env`에 `DATABASE_URL`을 설정합니다. `postgresql://` 및
`postgresql+psycopg://`를 지원하며 psycopg 3를 사용합니다. 값은 채팅에 붙이지 않습니다.
개발 환경에서 DB 미설정·연결 실패 시 `/health`는 계약대로 503을 반환합니다.
연결 성공 시 `{"status":"ok","service":"furbebe-api","version":"1"}`을 반환합니다.
production은 `APP_ENV=production`, DB URL, 명시적인 HTTPS `FRONTEND_ORIGIN`이 필요합니다.

Phase 4B의 기존 `DATABASE_URL_dev`·`SUPABASE_URL_dev` 설정으로 DEV 읽기 API를 실행하려면
현재 PowerShell 프로세스에서 대상을 명시합니다. `.env` 변수명을 변경할 필요는 없습니다.

```powershell
$env:FURBEBE_DATABASE_TARGET = 'supabase-dev'
try {
    .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8080
} finally {
    Remove-Item Env:FURBEBE_DATABASE_TARGET
}
```

개발용 OpenAPI 문서는 `http://127.0.0.1:8080/docs`에서 확인합니다.
DEV 검증 CLI는 대상을 자체적으로 선택하며 schema·데이터를 변경하지 않습니다.

```powershell
.\.venv\Scripts\python.exe -m backend.jobs.read_api_verification
```

```powershell
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini heads
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head --sql
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

전체 PostgreSQL 통합 테스트는 별도 로컬 disposable DB를 `FURBEBE_TEST_DATABASE_URL`로
지정해야 합니다. 미지정 시 DB 테스트가 skip됩니다. DEV DB는 테스트 대상으로 사용하지 않습니다.

Phase 3 revision은 `20260915_0001`이며 shelters/animals/animal_images/tags/animal_tags/sync_runs를 생성합니다.
`upgrade head`는 지정한 PostgreSQL DB에 실제 schema를 적용합니다. 자동 migration은 하지 않습니다.
전용 로컬 PostgreSQL에서 upgrade → downgrade → upgrade를 검증했으며 재현 방법은 [DB schema 문서](docs/database-schema.md)에 있습니다.

Docker가 있는 환경에서 프로젝트 루트를 build context로 사용합니다.

```powershell
docker build -f backend/Dockerfile -t furbebe-api:phase2 .
docker run --rm --env-file .env -p 127.0.0.1:8080:8080 furbebe-api:phase2
```

컨테이너에서는 컨테이너가 접근 가능한 PostgreSQL 주소를 사용해야 합니다.
**Docker build/run 미검증. 현재 blocker가 아니며 실제 컨테이너 검증은 deployment 단계에서 수행합니다.**
Phase 2의 실제 Uvicorn HTTP 요청과 Phase 3의 로컬 PostgreSQL 18.6 schema 검증을 완료했습니다.

- [Phase 2 결과·검증·실행 안내](docs/phase2-backend-base.md)
- [Phase 3 DB schema·관계·제약·migration 검증](docs/database-schema.md)
- [Phase 4A 로컬 sync·재실행·검증 결과](docs/phase4a-local-sync.md)
- [Phase 4B Supabase DEV migration·동기화 운영](docs/sync-design.md)
- [Phase 5 읽기 API·실제 DEV 검증·성능](docs/phase5-read-api.md)
- [아키텍처](docs/architecture.md)
- [API Contract 사본과 확정 정책](docs/api-contract.md)
- [제품 정책 확정 기록](docs/phase1-5-product-decisions.md)

체중 A(5/10/20kg), 나이 A(0~1/2~4/5~8/9+), v1 `animals_active` 제외,
근거 있는 행동·건강 설명의 선택 제공이 확정됐습니다. 동물 정규화는 Phase 4A,
읽기 API는 Phase 5에 구현했습니다.

## 현재 결과 — 2026-09-15

API 키 등록 및 인증을 확인했고 실데이터 수집·재분석을 실행했습니다.
고정 조회 기간은 2026-01-01~2026-09-14, totalCount는 60,515건입니다.
17페이지에서 raw 17,000건, 고유 동물 17,000건, 고유 개 10,507건을 확보했습니다.
중복·실패 페이지·충돌 ID·재시도는 없습니다. 기존 run과 합산하지 않았습니다.
개의 실제 발견일 범위는 2026-07-06~2026-09-14입니다. 목표 수에 도달해 수집을 종료했으므로
전체 기간의 전수 조사 또는 전체 동물 모집단으로 일반화하지 않습니다.

수집량 기준은 충족했습니다. 지역 코드는 `sido_v2.orgCd = upr_cd`,
`sigungu_v2.orgCd = org_cd`로 정규화하고, 원문 상태가 `보호중`인 자료는
공고 시작일로부터 현재 날짜까지 10일 이상이면 화면 상태를 `입양 가능`, 그 전이면
`보호중`으로 표시합니다. 원문 상태와 미매칭 지역은 보존합니다.
상세 내용은 [결정 문서](docs/api-profiling-decisions.md)를 확인합니다.
수동 검토용 표본 100건의 review_notes는 빈 칸입니다.

최신 검증에서 개 10,507건 모두 지역 코드 연결에 성공했습니다.
2026-09-15 기준 표시 상태는 `입양 가능` 3,909건, `보호중` 1,189건이며 종료 상태는 유지됩니다.
시도 16개, 시군구 조회 항목 252개, 품종 245개(개 206 / 고양이 38 / 기타 1),
보호소 소속 항목 330개가 있는 기존 공식 코드 캐시 247개 범위를 재사용했습니다.
변경된 날짜 조건의 창원 지역 ID 대조를 위해 동물 API 3페이지를 추가 조회했습니다.
네트워크 차단 재실행에서 참조 분석과 생성 결과가 동일했고 캐시 247회 재사용·네트워크 0회를 확인했습니다.
저장된 목록에 없는 품종 코드 6개(개 531건)와 보호소 코드 11개(개 479건)는
원문을 보존하고 데이터 품질 항목으로 보고했습니다. 누락 원인이나 폐지 여부는 단정하지 않습니다.

현재 run을 API 호출 없이 다시 분석하는 명령:

```powershell
.\.venv\Scripts\python.exe -m backend.jobs.animal_sync.profiling --input .local/profiling/20260914T232312940282Z/raw-20260914T232312940282Z.jsonl
```

이 run은 수집·코드 연결 등 데이터 blocker가 있으면 exit code 2를 반환합니다.
체중·나이 A안과 animals_active 제외는 사용자 승인으로 확정됐습니다.
이 절의 수치는 이전 profiling 결과입니다. 현재 Phase 4A sync 검증은 상단의 별도 결과를 기준으로 합니다.
재분석 전에 사람이 입력한 검토 의견이 있다면 CSV를 별도로 보관합니다.

## API 키 입력

프로젝트 루트의 `.env` 파일을 열어 다음 항목의 오른쪽에 키를 입력하고 저장합니다.

```dotenv
DATA_GO_KR_SERVICE_KEY=
```

공공데이터포털에서 이 API의 활용 승인을 받은 키를 사용합니다.
일반 키와 percent-encoded 키 모두 지원합니다. 환경변수가 있으면 .env보다 우선합니다.
키를 채팅이나 명령행에 붙여넣지 않습니다. .env는 Git 제외 대상입니다.
새 checkout에는 `.env.example`을 `.env`로 복사합니다.

공식 서비스 안내: https://www.data.go.kr/data/15098931/openapi.do
필요한 요청 파라미터와 실제 계정 한도는 공식 상세 명세와 승인 정보를 확인합니다.

## 실행 환경

Python 3.12+; 현재 검증 환경은 Python 3.14.6 / Windows PowerShell입니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe -m backend.jobs.animal_sync.profiling --check-config
```

마지막 명령은 키 존재 여부만 출력하며 네트워크를 호출하지 않습니다.

## 테스트

```powershell
.\.venv\Scripts\python.exe -m ruff check backend
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

모든 unit test는 합성 fixture와 mock transport를 사용합니다.
합성 fixture 통계를 실제 API 조사 결과로 사용하지 않습니다.

## 실제 API 사전 확인

```powershell
.\.venv\Scripts\python.exe -m backend.jobs.animal_sync.profiling --probe
```

HTTPS만 사용합니다. Redirect, 인증 실패, HTTP/application 오류는 안전한 코드로 보고합니다.
HTTP로 자동 전환하거나 TLS 검증을 해제하지 않습니다.
실제 단건 응답은 .local/profiling 아래에만 저장합니다.

## 본 수집

아래는 이번 수집에 사용한 조건입니다. 다시 실행하면 새 API 수집이 시작됩니다.

```powershell
.\.venv\Scripts\python.exe -m backend.jobs.animal_sync.profiling --target-unique 10000 --min-unique 5000 --page-size 1000 --max-pages 20 --request-interval 1 --seed 20260915 --start-date 20260101 --end-date 20260914
```

이번 목표는 unique 개 10,000건, 전체 수집 상한은 20페이지·20,000행입니다.
17페이지에서 목표에 도달해 고유 동물 17,000건으로 요청 범위를 충족했습니다.
전체 source 응답을 보존하고 `upKindNm=개`로
명확히 확인된 개의 주요 통계를 별도로 집계합니다. 분류가 모호한 자료는 보고합니다.
목표 전에 표본이 부족하면 더 넓은 기간으로 새 run을 실행합니다. 여러 run의 raw를
무작정 합쳐 표본 수를 늘리지 않습니다.

기본 최대 페이지는 2,000입니다. 종료 사유·요청/성공/실패·재시도·중복·totalCount를 기록합니다.
실패/변동/반복 페이지를 정상 완료로 숨기지 않습니다. 키를 포함한 URL을 출력하지 않습니다.
전체 응답 envelope는 JSONL의 한 행에 한 페이지씩 저장합니다.

5,000건 미만 예외는 실제 전체 모집단이 5,000 미만이고 전수 수집이 증명된 경우에만
사용합니다. `--entire-population-confirmed`는 공식 조회 범위가 실제 전체임을 확인한
경우에만 사용하며 날짜 제한과 함께 사용할 수 없습니다. API 기본 조회 기간을
모른다면 이 옵션을 사용하지 않습니다. 안정적인 totalCount와 마지막 빈 페이지,
raw/unique/duplicate 수를 함께 검증합니다.

## 로컬 결과와 재분석

공식 참조 코드를 조회하고 기존 동물 데이터와 연결합니다. 기본 실행은 완전 오프라인이며,
`--fetch-missing`을 붙인 경우에만 없는 조회 범위·코드를 가져옵니다.

```powershell
.\.venv\Scripts\python.exe -m backend.jobs.animal_sync.references --input .local/profiling/20260914T232312940282Z/raw-20260914T232312940282Z.jsonl --fetch-missing --as-of 2026-09-15
```

캐시: `.local/profiling/reference-data/cache.json`.
시도 전체, 시도별 시군구, 축종별 품종, 시도·시군구별 보호소로 나눠 저장합니다.
이미 있는 코드는 재조회하지 않습니다. 조회했지만 없는 코드는 24시간 동안 반복 요청을 막습니다.
서로 다른 관할에서 같은 보호소를 이용할 수 있어 보호소 소속은 `(upr_cd, org_cd, careRegNo)`로 검증합니다.
실제 코드 목록에 같은 지역명이 여러 코드로 나오면 임의 선택하지 않고, 코드별 동물 조회의
ID와 원본 표본을 대조합니다. 이 추가 증거도 로컬에 저장해 재사용합니다.

참조 결과는 동물 run 안의 `reference-profile.json`과
[참조 코드 보고서](docs/api-reference-data-profile.md)에 기록됩니다.
이후 아래 profiling 재분석 명령을 실행하면 참조 결과를 포함해 기존 3개 보고서도 갱신합니다.
참조 결과의 run ID와 원본 checksum이 맞지 않으면 중단합니다.
상태 계산은 기본적으로 실행일의 한국 날짜를 사용합니다. 재현할 때는 references 명령에
`--as-of 2026-09-15`처럼 기준일을 고정합니다. 기존 profiling의 기준일은 원본 run 날짜를 유지합니다.

표시 상태는 매 계산일마다 `noticeSdt`로부터 경과 일수를 계산합니다. 9일은 `보호중`,
10일 이상은 `입양 가능`입니다. 원문이 다른 상태이면 유지하고, 날짜가 없거나 잘못되었거나
미래이면 입양 가능으로 변경하지 않습니다. 표시 상태를 영구 캐시해 날짜 변화가 누락되게 하지 않습니다.

`.local/profiling/<run-id>/`에 다음 파일을 생성합니다.

- raw-<run-id>.jsonl: 모든 원본 페이지. 인증정보 echo만 제거.
- run.json: 키 없는 요청 조건·실행 metadata·raw SHA-256.
- summary-<run-id>.json: 상세 집계.
- field-stats-<run-id>.csv: 전체 필드 사전.
- manual-review-<run-id>.csv: 비식별 처리한 검토 표본, review_notes는 빈 칸.

```powershell
.\.venv\Scripts\python.exe -m backend.jobs.animal_sync.profiling --input .local/profiling/<run-id>/raw-<run-id>.jsonl
```

재분석은 네트워크와 API 키가 필요 없습니다. 원본 checksum과 실행 기준일·seed를 사용합니다.
동일 run 재분석은 집계 및 검토 CSV를 다시 생성합니다. 사람이 입력한 review_notes가
존재하면 덮어쓰지 않고 중단합니다. 검토한 CSV를 별도 로컬 파일로 보관한 뒤 실행합니다.

공유 가능한 docs 보고서는 마지막 분석 결과로 갱신됩니다. 모든 행 단위 자료는
.local/profiling에만 둡니다. 이미지 네트워크 검사나 다운로드는 수행하지 않습니다.

## 결과 해석과 중단

exit code 0: 요청한 작업 성공. probe/config 성공은 Phase 1 완료를 의미하지 않습니다.
exit code 2: 키/수집/분석 blocker 또는 미확정 의사결정. 상세 사유를 확인합니다.

성격/건강/행정 키워드는 후보 지표이며 실제 태그나 진단이 아닙니다.
순함·경계 같은 짧은 단어는 short-text와 evidence 후보를 모두 기록합니다.
지역 코드는 공식 `sido_v2`/`sigungu_v2` 조회 결과로 정규화하며, 미매칭은 데이터 품질
결과로 남기고 연결 불가 항목은 blocker로 보고합니다. 확정된 제품 정책과 현재 구현 범위는
상단의 Phase 2 안내 및 제품 결정 문서를 기준으로 합니다.

## 문서

- [Phase 0 감사](docs/phase0-repo-audit.md)
- [실데이터 분석](docs/api-data-profile.md)
- [필드 사전](docs/api-field-dictionary.md)
- [결정·보류 항목](docs/api-profiling-decisions.md)
- [공식 참조 코드·상태 정책](docs/api-reference-data-profile.md)

전체 아키텍처는 Frontend → FastAPI → SQLAlchemy → PostgreSQL을 유지합니다.
최신 사용자 결정은 Phase 0 감사 및 결정 문서에 기록되어 있습니다.
