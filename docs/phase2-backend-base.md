# Phase 2 — Backend Base

작성일: 2026-09-15, Asia/Seoul.

## 결과

**Phase 2 코드 구현 및 로컬 PostgreSQL·HTTP 검증 완료. Docker build/run 미검증. 사용자 결정에 따라 현재 blocker가 아니며 실제 컨테이너 검증은 deployment 단계에서 수행한다.**

이 문서의 revision 0개·163개 테스트는 Phase 2 완료 당시 기록이다.
이후 승인된 Phase 3의 도메인 모델·migration·검증 결과는 [database-schema.md](database-schema.md)에 기록한다.

개발 지시서 `CODEX_FURBEBE_DEVELOPMENT_INSTRUCTIONS.md` §36의 Phase 2 범위는
FastAPI, config, DB 연결, SQLAlchemy, Alembic, Docker, health다.
도메인 tables/indexes/migration revision은 Phase 3, 정규화·UPSERT는 Phase 4,
동물 읽기 API는 Phase 5다. 이번 작업은 Phase 2까지 진행했다.

## 확정한 제품 정책

| 항목 | 사용자 확정 |
| --- | --- |
| 체중 | A: tiny ≤5 / small >5~10 / medium >10~20 / large >20kg |
| 나이 | A: 현재 연도 − birth_year, 0~1 / 2~4 / 5~8 / 9 이상; 정확한 만 나이 아님 |
| animals_active | v1에서 제외 |
| 행동·건강 정보 | 근거 있는 설명을 선택 제공; 추측 성격·건강 진단이나 production 태그 생성 없음 |

기존 [Phase 1.5 문서](phase1-5-product-decisions.md)에 사용자 확정 기록을 추가했다.
[Repository Contract](api-contract.md)는 사용자가 제공한 Contract의 사본이며,
승인한 `animals_active` 제외와 최신 정책을 명시했다. Downloads의 원본 Contract는 보존했다.

## 구현

- FastAPI app factory와 lifespan, `/health` router/service/repository.
- Pydantic Settings: 프로젝트 루트 `.env`와 환경변수, secret URL 마스킹,
  PostgreSQL/psycopg 연결 제한, production DB·HTTPS origin 검사.
- SQLAlchemy engine/session/base metadata. 종료 시 dispose, 미커밋 session rollback.
- Alembic online/offline 환경·revision template. 현재 revision과 도메인 table은 0개다.
- UTF-8 JSON, UUID 요청 ID, 422/503/500 공통 오류 envelope, CORS allowlist.
- Python slim 기반 Dockerfile, non-root 실행, runtime dependency constraints, healthcheck,
  secret·raw·test를 제외하는 `.dockerignore`.

## 실행

프로젝트 루트에서:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt -c backend/requirements-runtime-lock.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8080
```

`.env.example`을 참고해 로컬 `.env`에 DB URL을 설정한다. 키나 비밀번호는 명령행에 붙이지 않는다.
개발 환경에서 DATABASE_URL이 비어 있으면 서버는 시작하고 `/health`는 503을 반환한다.
production은 DATABASE_URL과 명시적인 HTTPS FRONTEND_ORIGIN이 없으면 안전한 설정 오류로 중단한다.
`postgresql://` 입력은 psycopg 3 driver로 연결하며 TLS query 옵션을 보존한다.

정상 DB 응답:

```json
{"status":"ok","service":"furbebe-api","version":"1"}
```

DB 미설정·연결 실패 응답은 HTTP 503이며 다음 구조다.

```json
{"error":{"code":"SERVICE_UNAVAILABLE","message":"Database unavailable","details":null,"request_id":"<uuid>"}}
```

## Alembic

```powershell
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini heads
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head --sql
```

현재는 revision이 없어 offline SQL이 BEGIN/COMMIT만 출력된다.
online `upgrade head`는 지정한 DB에 Alembic 관리 table을 생성할 수 있다.
이번에는 전용 로컬 검증 DB에만 실행했으며, 반복 upgrade와 `alembic check`를 검증했다.
실제 도메인 migration은 Phase 3에서 추가한다. 실행 중 migration 자동 적용은 하지 않는다.

## 검증

| 확인 항목 | 결과 |
| --- | --- |
| 전체 pytest | **163 passed**: 기존 profiling 139 + backend 기본 21 + PostgreSQL 통합 3 |
| Ruff | `ruff check .` 통과 |
| 신규 Python 형식 | `ruff format --check` 대상 파일 통과 |
| 의존성 | `pip check` 통과 |
| 실제 PostgreSQL | 공식 배포 PostgreSQL 18.6, 루프백 전용 테스트 DB 연결 성공 |
| 실제 HTTP | Uvicorn을 별도 프로세스로 실행하고 `/health` 200 확인 |
| HTTP 계약 | status/service/version 정확히 일치, JSON UTF-8, 요청 ID 확인 |
| 오류 경로 | DB 미설정·SQLAlchemy 오류 503, 예외 500, validation 422, secret 비노출 검사 |
| CORS | 허용 origin, 차단 origin, preflight, 오류 응답 검사 |
| DB session | 실제 PostgreSQL에서 미커밋 임시 table 생성의 rollback 확인 |
| Alembic | head upgrade 2회, current, check; `alembic_version` 외 도메인 table 없음 |
| Docker | Dockerfile 준비. Docker/Podman 런타임 부재로 이미지 빌드·실행 미검증 |

테스트용 PostgreSQL은 기존 환경에 없어서 [공식 Windows 다운로드 안내](https://www.postgresql.org/download/windows/)에서 연결되는
EDB binary archive를 `.local/phase2/pg-package/`에 내려받아 사용했다.
시스템 서비스로 설치하지 않았고 127.0.0.1에만 bind했다.
검증 DB 이름은 `furbebe_test_phase2`, 계정·비밀번호는 로컬 전용 파일에만 보관했다.
원본 17,000건을 DB에 적재하지 않았다.

로컬 검사 자료는 `.local/phase2/`에 있다. 공개 문서에 인증 URL이나 비밀번호를 기록하지 않았다.
HTTP 검사 결과: `http-smoke-result.json`. 서버 로그: `uvicorn-smoke.log`.
검증이 끝난 뒤 Uvicorn과 테스트 PostgreSQL 프로세스를 종료했다. 상시 서비스로 남기지 않았다.

일반 테스트는 다음과 같다. 전용 DB를 지정하지 않으면 통합 3건은 skip한다.

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

실제 PostgreSQL 검사는 `FURBEBE_TEST_DATABASE_URL` 환경변수에 **검증 전용** 연결을 설정한 뒤 실행한다.
DB 이름이 `furbebe_test`로 시작하지 않으면 통합 테스트가 거부한다.
일반 `DATABASE_URL`을 자동 사용하지 않는다. API 호출은 합성 mock을 사용하며 국가 OpenAPI를 재수집하지 않는다.

테스트에는 설치된 Starlette/AnyIO의 deprecated 인터페이스 경고 2개가 있다.
실패는 아니며 기존 OpenAPI client의 httpx 동작을 바꾸지 않았다.

## Docker 검증이 남은 이유와 재현 명령

현재 환경에는 Docker·Podman 실행 파일과 daemon이 없다.
따라서 로컬 Python/DB 검증 성공을 컨테이너 검증으로 보고하지 않는다.

```powershell
docker build -f backend/Dockerfile -t furbebe-api:phase2 .
docker run --rm --env-file .env -p 127.0.0.1:8080:8080 furbebe-api:phase2
```

프로젝트 루트가 build context다. DATABASE_URL은 컨테이너에서 접근 가능한 주소여야 한다.
Dockerfile은 8080을 사용하며 DB 연결 실패 시 healthcheck도 실패한다.
실제 deployment 단계에서 위 명령과 `/health` 검사로 검증한다. 현재 Docker를 설치하거나 개발 환경을 변경하지 않는다.

## 사용한 공식 참고 자료

- [FastAPI 환경 설정](https://fastapi.tiangolo.com/advanced/settings/)
- [SQLAlchemy engine 설정](https://docs.sqlalchemy.org/en/20/core/engines.html)
- [Alembic 환경과 실행](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [FastAPI Docker 구성](https://fastapi.tiangolo.com/deployment/docker/)

## 다음 단계

Docker 빌드·실행 검증은 deployment 단계로 이관했다. Phase 3 도메인 schema는 별도 사용자 승인에 따라 구현했다.
Phase 4 sync와 이후 동물 읽기 endpoint는 아직 구현하지 않았다.
