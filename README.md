# FURBEBE

가족을 기다리는 보호견의 공고·사진·보호소 정보를 모아, 검색과 태그로 만남을 돕는 서비스입니다.
국가동물보호정보시스템의 공공데이터를 수집해 PostgreSQL에 보관하고 FastAPI로 제공합니다.

## 서비스와 데이터

- **홈**: 실제 등록 사진, 빠른 탐색, 최근 등록된 친구 6마리.
- **목록 /dogs**: 검색, 지역·품종·성별·중성화·체중·나이·상태·태그 필터, 정렬, 24개씩 페이지 이동.
- **상세 /dogs/:animalId**: 원문 설명, 등록 사진, 공고 정보, 보호소 연락처, 비슷한 친구.
- **관심 저장과 공유**: 브라우저에 관심 UUID 저장, 시스템 공유·클립보드·직접 복사 지원.
- **공통 화면**: Google AdSense 연결, 개발자 후원 계좌 클릭 시 숫자만 복사.

공개 조회 대상은 **is_active=true인 개**입니다. 수집기는 원천 상태가 **보호중 또는 입양 가능**인 개를 신규 저장하고,
기존 개가 대상에서 벗어나면 비활성화해 기록을 보존합니다. 실패하거나 조회 범위 밖에서 빠진 자료를 자동 삭제하지 않습니다.

화면의 **입양 가능**은 원천 상태가 보호중이고 공고 시작일부터 한국 날짜 기준 10일 이상 지난 경우에 표시합니다.
보호소가 실시간으로 확정한 입양 승인 상태가 아니므로 실제 입양 가능 여부와 절차는 보호소에 확인해야 합니다.
홈과 목록의 기본 상태는 입양 가능이며, 목록에서 전체 또는 보호중을 선택할 수 있습니다.

## 구조

```mermaid
flowchart LR
  U[브라우저] --> W[Cloudflare Workers<br/>React Router SSR]
  U --> A[FastAPI 읽기 API]
  W --> A
  A --> P[(Supabase PostgreSQL)]
  G[공공데이터 API] --> J[수집 작업]
  J --> P
```

프런트엔드는 FastAPI만 호출합니다. Supabase SDK, Data API 또는 DB 직접 연결을 사용하지 않습니다.
API 서버는 DB 조회만 담당하고, 수집·마이그레이션은 별도 명령으로 실행합니다.

| 구성 | 코드와 설정 |
| --- | --- |
| 프런트엔드 | React 19, React Router 8 Framework, Vite 8, JavaScript/JSX, Tailwind CSS 4 |
| API | Python 3.12+, FastAPI, SQLAlchemy 2, psycopg 3 |
| DB | PostgreSQL, Alembic; 현재 migration head: 20261005_0005 |
| 운영 배포 설정 | Cloudflare Workers 프런트엔드, Cloud Run API, Supabase DB |
| 수집 자동화 | GitHub Actions; 하루 2회 KST 00:00/12:00 |

배포 설정이 존재한다고 외부 서비스가 배포되어 있다는 뜻은 아닙니다.
운영 DB 적재 결과와 남은 인프라 작업은 [운영 상태](docs/operational-status.md)에 따로 기록합니다.

## 로컬 시작

명령은 macOS/Linux 셸과 저장소 루트 기준입니다. Node.js 22.22 이상, Python 3.12 이상,
접근 가능한 PostgreSQL이 필요합니다. Windows에서는 가상환경 경로를 backend/.venv/Scripts/python.exe로 바꿉니다.

### 1. 의존성

```sh
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt -c backend/requirements-runtime-lock.txt
npm --prefix frontend ci
```

### 2. 환경 설정

새 checkout에서만 예제를 복사하고 값을 채웁니다. 기존 .env는 덮어쓰지 않습니다.

```sh
cp .env.example .env
cp frontend/.env.example frontend/.env.local
```

루트 .env의 개발 최소 설정:

```dotenv
APP_ENV=development
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/furbebe_dev
FRONTEND_ORIGIN=http://127.0.0.1:5173,http://localhost:5173
DATA_GO_KR_SERVICE_KEY=YOUR_APPROVED_SERVICE_KEY
```

DATA_GO_KR_SERVICE_KEY는 수집할 때만 필요합니다. DB 비밀번호의 URL 예약 문자는 percent-encoding합니다.
frontend/.env.local에는 공개 값만 넣습니다.

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8080
VITE_SITE_URL=https://furbebe.site
```

DATABASE_URL_prod만 채웠다면 일반 DATABASE_URL로 자동 선택되지 않습니다.
운영 DB를 로컬 API에서 조회하려면 [명시적 DB 선택](docs/environment.md)을 따라
APP_ENV=production과 프로세스 환경 변수 FURBEBE_DATABASE_TARGET=supabase-prod를 함께 지정합니다.
로컬 개발 기본 예제는 개발 DB입니다.

### 3. 테이블 생성과 수집

아래는 **로컬 개발 DB**를 준비하는 명령입니다. 기존 운영 DB 초기화에 사용하지 않습니다.

```sh
FURBEBE_DATABASE_TARGET=local backend/.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
backend/.venv/bin/python -m backend.jobs.animal_sync.main --database-target local --full
```

수집 CLI의 local 대상은 loopback 주소의 furbebe_dev* 또는 furbebe_test* DB만 허용합니다.
**--full은 공공데이터 API의 기본 날짜 범위 전체 페이지 수집**입니다. 과거 전체 이력을 뜻하지 않습니다.
DEV·PROD 적재, 실패 처리와 원본 capture는 [수집 안내](docs/sync-design.md)를 따릅니다.

### 4. 서버 실행

첫 번째 터미널:

```sh
FURBEBE_DATABASE_TARGET=local backend/.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8080 --reload --no-access-log
```

두 번째 터미널:

```sh
npm run dev
```

- 사이트: http://127.0.0.1:5173
- DB 연결 확인: http://127.0.0.1:8080/health
- 개발 OpenAPI: http://127.0.0.1:8080/docs
- APP_ENV=production이면 /docs와 /openapi.json은 비활성화됩니다.

## 검증

```sh
backend/.venv/bin/python -m ruff check .
backend/.venv/bin/python -m pytest backend/tests -q
npm test
npm run lint
```

PostgreSQL 통합 테스트는 별도의 loopback furbebe_test* DB를 FURBEBE_TEST_DATABASE_URL로 지정해야 합니다.
미지정하면 DB 테스트가 skip되며, 운영·DEV Supabase DB를 테스트 대상으로 사용하지 않습니다.
브라우저 smoke, 운영 빌드, Worker dry-run과 CI 범위는 [검증 안내](docs/quality.md)에 있습니다.

## 문서

| 필요한 작업 | 안내 |
| --- | --- |
| 전체 문서 탐색 | [문서 목차](docs/README.md) |
| 환경 변수·DEV/PROD 선택 | [환경 설정](docs/environment.md) |
| 태그의 근거·규칙·버전·재생성 | [태그 생성 로직](docs/tag-generation.md) |
| 원천 수집·정규화·보존 | [수집 설계와 실행](docs/sync-design.md), [원천 필드 사전](docs/api-field-dictionary.md) |
| DB 구조·migration | [DB 스키마](docs/database-schema.md) |
| 공개 API 요청·응답 | [API 계약](docs/api-contract.md) |
| Cloudflare·Cloud Run·Supabase·DNS | [인프라 배포 매뉴얼](docs/infrastructure.md) |
| GitHub에서 API 수동 배포 | [Cloud Build 연결 매뉴얼](docs/github-deployment.md) |
| 백업·장애 대응·복구 | [운영 매뉴얼](docs/operations.md) |
| UI·SEO·광고·후원 | [프런트엔드 안내](docs/frontend.md) |
| 현재 운영 상태 | [운영 상태](docs/operational-status.md) |

비밀번호·API 키·원천 capture·백업은 커밋하지 않습니다.
환경 설정과 .local의 비공개 운영 자료는 안내 문서 재작성이나 임시 파일 정리 대상에서 제외합니다.
