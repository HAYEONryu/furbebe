# 검증과 CI

실행 명령은 저장소 루트 기준입니다. 특정 과거 test 수를 현재 보장 수로 사용하지 않습니다.
검증 결과를 남길 때 commit, 환경, pass/skip/fail, 실행 범위를 기록합니다.

## Backend

```sh
backend/.venv/bin/python -m ruff check .
backend/.venv/bin/python -m pytest backend/tests -q
```

단위 테스트는 mock·합성 원천 자료로 parser/규칙/query/오류/수집 경계를 검사합니다.
PostgreSQL 테스트는 별도로 만든 loopback furbebe_test* DB를 요구합니다.

```sh
APP_ENV=test FURBEBE_TEST_DATABASE_URL='postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/furbebe_test_local' backend/.venv/bin/python -m pytest backend/tests -q
```

위는 disposable test 설정 예제이며 실제 password를 shared log나 shell history에 넣지 않습니다.
서비스 자격증명이 아닌 비민감 전용 test 자격증명을 사용합니다.
설정 미지정이면 DB 테스트를 skip합니다. DB 테스트에는 table/drop과 migration 재적용이 있으므로 원격 DEV/PROD를 사용하지 않습니다.

태그 변경 검증은 행동 부정·불확실·행정·일시 문맥, 공개 허용 규칙,
털색 우선순위·회색 제외, 체중 0/5/10/20/null, 중복 제거·evidence/version을 포함합니다.
DB 검증은 idempotency, stale timestamp, 활성 flag·자식 보존, read-only transaction,
KST 상태/나이/cache, unknown tags, 유사 동물과 SQL 횟수를 확인합니다.

## Frontend

```sh
npm test
npm run lint
```

Vitest는 route/service/응답 검증, query 상태, tags, 이미지·관심 저장·공유·SEO를 검사합니다.
운영 origin과 Worker www redirect/asset 흐름도 확인합니다.

브라우저 smoke:

```sh
npm --prefix frontend exec -- playwright install chromium
npm --prefix frontend run test:smoke
```

Playwright는 실제 운영 API 대신 fixture API 8089를 시작하고 별도 build/preview 4173을 사용합니다.
두 포트를 점유한 기존 프로세스가 없어야 합니다.
반응형·keyboard·modal·태그 도움말·axe·검색·이미지·SEO의 브라우저 동작을 확인합니다.
산출물은 frontend/.local/playwright-results에 저장하며 Git 제외입니다.
이 build는 fixture API를 포함하므로 운영에 배포하지 않습니다.
production 배포 전에는 [인프라 매뉴얼](infrastructure.md)의 명령으로 다시 build합니다.

## 운영 build와 Worker dry-run

```sh
FURBEBE_BUILD_TARGET=production VITE_API_BASE_URL=https://api.furbebe.site VITE_SITE_URL=https://furbebe.site npm run build
npm --prefix frontend run check:worker
```

dry-run은 실제 배포가 아닙니다. 생성된 Wrangler의 두 domain, preview disable, ASSETS/run_worker_first와
client/SSR의 공개 URL을 확인합니다.
상세 sitemap을 검사하려면 준비된 API를 SITEMAP_API_BASE_URL로 별도 지정합니다.
secret·원천 key·DB URL·의도하지 않은 run.app host가 build에 들어가지 않아야 합니다.

## Docker와 GitHub CI

Docker 검증은 별도 8080 포트 사용 환경에서 실행합니다.

```sh
docker build -f backend/Dockerfile -t furbebe-api:ci .
bash deploy/docker-smoke.sh
```

smoke는 disposable PostgreSQL 16과 API container를 만들고 종료 시 제거합니다.
nonroot, 실제 health 연결, production 설정·CORS, image secret/불필요 파일 제외, log redaction을 확인합니다.
schema와 전체 read endpoint를 검사하는 운영 smoke를 대신하지 않습니다.

.github/workflows/ci.yml:

- frontend: Node 22.23.3, npm ci/test/lint, production build, secret canary scan, Worker dry-run.
- backend: Python 3.12/3.14, disposable PostgreSQL 16, Ruff와 전체 pytest.
- docker: build와 docker-smoke.

PR/push(main)/수동 trigger이며 registry push·cloud deploy·migration·수집은 포함하지 않습니다.
green CI는 live DNS/TLS·운영 사진·부하·백업/복구·AdSense 승인 완료 증거가 아닙니다.
실제 배포 후 검증은 [운영 점검표](../deploy/production-smoke-checklist.md)를 사용합니다.
