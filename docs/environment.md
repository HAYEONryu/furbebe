# 환경 변수와 DB 선택

## 파일과 우선순위

| 설정 | 읽는 위치 | 프로세스 환경 우선 |
| --- | --- | --- |
| 일반 Backend Settings | 저장소 루트 .env | 예 |
| 명시적 Supabase 설정 | 루트 .env, 값 보간 없음 | 예 |
| 원천 API 키 | 프로세스 환경 또는 루트 .env | 예 |
| 프런트엔드 공개 URL | frontend/.env, .env.local, 모드별 .env.* | 예 |
| FURBEBE_DATABASE_TARGET | **프로세스 환경만** | 해당 |
| FURBEBE_BUILD_TARGET | **프로세스 환경만** | 해당 |
| 수집·재생성 대상 | CLI argument | CLI가 선택 |

같은 파일에 APP_ENV를 두 번 쓰지 않습니다. dotenv의 중복 항목은 뒤 값으로 덮어써질 수 있습니다.
DATABASE_URL_dev와 DATABASE_URL_prod는 다른 이름이므로 함께 존재할 수 있지만 대상 선택과 APP_ENV는 실행마다 하나입니다.
환경을 나눈 파일이 실수 방지에 도움이 됩니다. 현재 로더는 루트 .env를 기본으로 읽습니다.
셸에서 .env를 source하지 말고 앱의 dotenv 로더 또는 secret 주입을 사용합니다.

## 꼭 필요한 변수

| 실행 | 필수 | 추가 조건 |
| --- | --- | --- |
| 로컬/일반 API | DATABASE_URL, FRONTEND_ORIGIN | APP_ENV는 development 기본 |
| 일반 운영 API container | APP_ENV=production, DATABASE_URL, FRONTEND_ORIGIN | 정확한 HTTPS origins |
| 명시적 Supabase DEV | DATABASE_URL_dev, SUPABASE_URL_dev | APP_ENV=development |
| 명시적 Supabase PROD | APP_ENV=production, DATABASE_URL_prod, SUPABASE_URL_prod, FURBEBE_PROD_PROJECT_REF | 대상 selector도 지정 |
| 실시간 수집 | 대상 DB 설정 + DATA_GO_KR_SERVICE_KEY | 날짜 범위 또는 --full |
| 프런트엔드 | VITE_API_BASE_URL, VITE_SITE_URL | 기본값은 있으나 명시 권장 |
| 운영 Worker 빌드 | 위 공개 URL + FURBEBE_BUILD_TARGET=production | 프로세스 환경으로 주입 |
| 상세 sitemap snapshot | SITEMAP_API_BASE_URL | 공개 API 준비 후 사용 |

**SUPABASE_PUBLISHABLE_KEY, SUPABASE_SECRET_KEY, SUPABASE_JWKS_URL은 현재 코드에서 사용하지 않습니다.**
host_dev/port_dev/database_dev/user_dev와 prod 대응 값은 선택적 일치 검사일 뿐 필수가 아닙니다.
접속 URL에 호스트·포트·DB·사용자가 있어 최소 설정에서 생략합니다.
SUPABASE_URL_dev/prod는 명시적 대상의 프로젝트 확인용이며 DB 접속 URL을 대신하지 않습니다.

## 개발 예제

로컬 DB:

```dotenv
APP_ENV=development
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/furbebe_dev
FRONTEND_ORIGIN=http://127.0.0.1:5173,http://localhost:5173
DATA_GO_KR_SERVICE_KEY=YOUR_APPROVED_SERVICE_KEY
```

Supabase DEV:

```dotenv
APP_ENV=development
DATABASE_URL_dev=postgresql://postgres.DEV_REF:ENCODED_PASSWORD@DEV_SESSION_POOLER:5432/postgres?sslmode=require
SUPABASE_URL_dev=https://DEV_REF.supabase.co
FRONTEND_ORIGIN=http://127.0.0.1:5173,http://localhost:5173
DATA_GO_KR_SERVICE_KEY=YOUR_APPROVED_SERVICE_KEY
```

```sh
APP_ENV=development FURBEBE_DATABASE_TARGET=supabase-dev backend/.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8080 --reload --no-access-log
```

## 운영 DB와 DATABASE_URL_prod

운영 프로젝트 ref는 xhlenzdnqnbczekkovgl입니다. 호스트·사용자·포트는 Supabase Connect의 **Session pooler**에서 복사합니다.

```dotenv
APP_ENV=production
DATABASE_URL_prod=postgresql://postgres.xhlenzdnqnbczekkovgl:ENCODED_PASSWORD@PROD_SESSION_POOLER:5432/postgres?sslmode=require
SUPABASE_URL_prod=https://xhlenzdnqnbczekkovgl.supabase.co
FURBEBE_PROD_PROJECT_REF=xhlenzdnqnbczekkovgl
FRONTEND_ORIGIN=https://furbebe.site,https://www.furbebe.site
DB_POOL_SIZE=1
DB_MAX_OVERFLOW=1
```

selector를 프로세스에 전달합니다. **.env에 selector 한 줄만 추가해서는 선택되지 않습니다.**

```sh
APP_ENV=production FURBEBE_DATABASE_TARGET=supabase-prod backend/.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8080 --no-access-log
```

이 명령은 로컬에서 운영 DB를 읽습니다. production CORS에는 localhost가 없으므로 로컬 SSR loader는
서버에서 API를 호출할 수 있어도 브라우저 직접 API 호출은 차단됩니다. 일반 개발은 개발 DB를 사용합니다.

Cloud Run 템플릿은 일반 Settings 경로입니다. secret을 **DATABASE_URL**로 주입하고 selector는 넣지 않습니다.
CLI의 supabase-prod는 suffixed 설정만 사용하며 일반 DATABASE_URL 또는 DEV로 fallback하지 않습니다.
일반 Settings 경로의 별칭이 필요하면 dotenv에서 DATABASE_URL=${DATABASE_URL_prod}로 명시할 수 있습니다.
명시적 Supabase 로더는 보간하지 않으므로 DATABASE_URL_prod에는 실제 접속 URL을 넣습니다.

## 대상 검증

프로젝트 HTTPS URL, 접속 URL 사용자/호스트, 포트 5432, DB postgres, 비밀번호, APP_ENV를 검증합니다.
PROD는 FURBEBE_PROD_PROJECT_REF 일치와 DEV URL과의 차이도 확인합니다.
sslmode는 require/verify-ca/verify-full만 허용하고 미지정이면 require를 추가합니다.
접속을 다른 곳으로 돌리는 URL query 옵션과 PGHOSTADDR/PGSERVICE/PGSERVICEFILE은 거부합니다.

일반 Settings의 target 이름 local은 일반 DATABASE_URL을 의미합니다.
API·Alembic에는 원격 접속 금지 검사까지 제공하지 않습니다. loopback guard는 수집 CLI의 local 대상에 적용됩니다.

## 프런트엔드

frontend/.env.local:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8080
VITE_SITE_URL=https://furbebe.site
```

frontend/.env.production:

```dotenv
VITE_API_BASE_URL=https://api.furbebe.site
VITE_SITE_URL=https://furbebe.site
```

프로세스 환경의 공개 URL이 .env.local보다 우선합니다. 루트 .env를 frontend로 복사하지 않습니다.
Vite define에는 VITE_API_BASE_URL/VITE_SITE_URL만 전달합니다.
SITEMAP_API_BASE_URL은 sitemap 스크립트용이며 클라이언트 설정이 아닙니다.
FURBEBE_BUILD_TARGET은 파일만으로 읽히지 않으므로 빌드 명령 앞에 지정합니다.

## 연결 제한

| 변수 | Settings 기본 | PROD 명시적 CLI 기본 | Cloud Run 템플릿 |
| --- | --- | --- | --- |
| DB_POOL_SIZE | 5 | 1 | 3 |
| DB_MAX_OVERFLOW | 5 | 1 | 1 |
| DB_POOL_TIMEOUT | 5초 | 5초 | 5초 |
| DB_POOL_RECYCLE | 1800초 | 1800초 | 1800초 |
| DB_CONNECT_TIMEOUT | 5초 | 5초 | 5초 |
| DB_STATEMENT_TIMEOUT_MS | 5000ms | 5000ms | 5000ms |

설정값이 있으면 기본값을 덮어씁니다. 수집은 lock 연결과 완료 기록 연결을 함께 사용할 수 있어 pool 1+1을 사용합니다.
변경 후 API·Vite를 재시작합니다. 운영 공개 URL 변경은 프런트엔드 재빌드·재배포가 필요합니다.
