# FURBEBE Engineering Rules

## Architecture

Frontend / Workers → FastAPI → SQLAlchemy / psycopg → PostgreSQL.
Frontend에서 Supabase SDK, Data API 또는 PostgreSQL 직접 접근을 하지 않는다.
API 읽기와 수집·migration 실행 경계를 유지한다.

## Stack

Frontend: React, React Router Framework SSR, Vite, JavaScript/JSX, Tailwind CSS.
Backend: Python 3.12+, FastAPI, SQLAlchemy, psycopg, Alembic, PostgreSQL.
Production settings: Cloudflare Workers, Cloud Run API, Supabase PostgreSQL.

## Data rules

공개 조회는 활성 개이며 신규 수집은 원천 보호중/입양 가능인 개다.
원문 snapshot과 불확실성을 보존하고 없는 사실·성격·건강 진단을 만들지 않는다.
정상 sync의 비대상 동물·빠진 원천 이미지·태그는 비활성화해 기록을 보존한다.
KST 날짜 기반 상태/나이 정책, 태그와 체중 필터의 서로 다른 경계를 유지한다.

## Verification

Frontend (repository root): npm test, npm run lint.
Backend: backend/.venv/bin/python -m ruff check ., backend/.venv/bin/python -m pytest backend/tests -q.
DB integration tests는 명시적 disposable loopback furbebe_test* DB만 사용한다.
Build와 browser/container checks의 실행 범위는 docs/quality.md를 따른다.

## Restrictions

- MySQL, Redux를 도입하지 않는다.
- Redis와 AI 기능은 별도 요구사항과 설계 결정 없이 도입하지 않는다.
- migration 파일을 삭제하지 않는다.
- production data를 삭제하지 않는다.
- 환경 secret, 원천 capture, DB backup을 Git·공개 artifact·로그에 넣지 않는다.
- 문서와 생성 보고서는 구분한다. 분석 보고서는 .local에만 생성한다.

## Documentation

README.md와 docs/README.md를 문서 진입점으로 사용한다.
규칙 변경 시 docs/tag-generation.md, sync-design.md, api-contract.md 등 관련 현재 안내를 함께 갱신한다.
실행 완료 사실은 docs/operational-status.md에 확인 날짜·범위와 함께 기록한다.
