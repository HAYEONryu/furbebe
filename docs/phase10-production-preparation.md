# Phase 10 — Production Deployment Preparation

준비/검증일: 2026-10-01 (Asia/Seoul). Cloud Run/Cloudflare production deploy, registry push, PROD migration, PROD sync, DNS 변경, Supabase project 생성 및 유료 provisioning은 실행하지 않았다. 사용자의 `env` 값도 읽거나 변경하지 않았다.

## Docker / Security

로컬에 Docker CLI/runtime이 없었다. 사용자의 지시에 따라 임의 설치하지 않았다. Docker build/run이 통과했다고 주장하지 않는다. `.github/workflows/ci.yml`에 Ubuntu의 Docker build와 `deploy/docker-smoke.sh` run 검증을 준비했다. CI green이 배포 전 blocker다.

API 이미지는 기존 Python 3.14 slim / pinned runtime constraints를 유지한다. nonroot UID 10001, 프로세스 1개, 0.0.0.0:8080, reload/debug off, raw URL을 기록하는 Uvicorn access log off다. APP_ENV=production에서 docs/OpenAPI도 비활성화한다.

COPY는 runtime requirements와 backend API Python/지역 catalog만 대상으로 한다. Docker context는 deny-all 뒤 source allowlist이며 `.env`, `env`, virtualenv, 테스트, sync capture/jobs, migration, key 파일은 포함하지 않는다. Build args/ENV에 DATABASE_URL/API key를 넣지 않는다. GitHub sync는 API 이미지가 아닌 checkout 소스에서 기존 CLI를 실행한다.

CI Docker smoke는 disposable PostgreSQL 16을 만들고 1 CPU/512MB 컨테이너에 합성 DATABASE_URL/APP_ENV/CORS/pool을 주입한다. startup, 실제 /health DB 연결, nonroot, 이미지 안 dotenv/secret ENV 없음, production debug/docs off, 두 origin 허용/DEV 거부, 합성 DB 암호 log 미노출을 검사한다. 실제 PROD DB에 연결하지 않는다. container port는 Cloud Run YAML과 동일한 8080이다.

## Cloud Run Config / DB Connections

`deploy/cloud-run.service.yaml`은 placeholder가 있는 검토용 template이다. 승인 후 project/service account/image digest/secret version을 채워야 한다.

| 항목 | 초기값 |
| --- | --- |
| Region | asia-northeast3 |
| CPU / memory | 1 CPU / 512MiB |
| Minimum / maximum | 0 / 2 (service + revision maximum) |
| Billing | request CPU allocation, idle CPU throttled |
| Container concurrency | 4 |
| Uvicorn processes | 1 |
| Request timeout | 30초 |
| DB pool_size / max_overflow | 3 / 1 |
| Pool timeout / recycle | 5초 / 1800초 |
| pre_ping | true |
| Connect / statement timeout | 5초 / 5000ms |
| Startup | TCP 8080; DB outage로 반복 재시작하지 않음 |
| Ingress | internal-and-cloud-load-balancing (선택한 ALB 경로) |

SQLAlchemy → psycopg → Supabase PostgreSQL을 유지한다. Data API로 바꾸지 않는다. Supabase Connect의 session pooler port 5432 + TLS를 초기 선택으로 한다. IPv4 접근성과 DEV에서 검증한 연결 방식을 유지하고, psycopg prepared statements 및 sync session advisory lock을 지원한다. Transaction pooler 6543로 임의 변경하지 않는다. Direct connection은 migration/backup에 적합하지만 IPv6/IPv4 add-on 및 실행 환경 접근성을 먼저 확인한다. [Supabase 연결 지침](https://supabase.com/docs/guides/database/connecting-to-postgres).

기존 개발 기본 pool 5+5는 유지하며 환경변수로 조정할 수 있게 했다. 운영 API는 3+1, production operational CLI/sync 기본은 1+1이다. Actions sync도 1+1을 명시해 sync lock 보유 연결과 finalization 연결을 수용한다.

정상 이론상 API 상한은 `2 instances × 1 process × (3+1) = 8`, sync는 추가 2다. 관리/사전검사 연결과 배포 중 transient instance에 별도 여유가 필요하다. 초기 제안은 애플리케이션 전용 available connection budget 최소 24를 확인하는 것이다. 이것은 Supabase의 실제 max_connections/계획을 확인한 값이 아니다. Supabase 내부 예약·다른 서비스·pooler client/server limits를 빼고 판단한다. autoscaling max는 순간 초과 가능성이 있어 hard DB cap으로 간주하지 않는다. [Cloud Run 최대 인스턴스 지침](https://docs.cloud.google.com/run/docs/configuring/max-instances).

기존 성능 근거: Phase 5 재검증의 목록 370~512ms, 상세 304~391ms, similar 417~460ms, filters 471~687ms. Phase 7에서 DEV cold metadata 11.55초도 관측되었다. 따라서 1CPU/512MiB/concurrency4/max2는 비용·DB 연결을 제한하는 보수적 시작점이며 실제 Cloud Run 성능 검증값이 아니다. staging에서 실제 데이터의 cold/warm latency, memory, concurrency4, pool timeout, p95/p99를 검증하고 조정해야 한다. frontend 일반 timeout 10초 / metadata 20초와 Cloud Run 30초를 함께 점검한다. min0은 cold start를 허용한다.

Runtime DATABASE_URL secret은 PROD read 역할을 사용하고 sync는 별도 write 역할로 구성한다. migrations는 별도 관리 자격증명/승인 절차를 사용한다. SQLAlchemy read transaction 보호를 유지한다. Runtime 서비스 계정에는 필요한 DB secret 하나에 대해서만 Secret Accessor 권한을 부여하고 sync 원천 API key는 API 컨테이너에 넣지 않는다. 현재 Supabase network restrictions와 Cloud Run egress 접근성을 확인한다. 고정 egress/NAT를 임의 도입하지 않았다.

## Cloudflare / CORS

Production profile `frontend/wrangler.production.jsonc`: furbebe.com, www.furbebe.com custom domains; workers.dev/preview_urls=false; nodejs_compat와 static assets/observability 유지. Vite의 `FURBEBE_BUILD_TARGET=production`일 때 해당 profile을 사용한다. 검증된 생성 Wrangler 설정에는 두 route와 disabled preview가 반영되었다.

Production build의 공개 API origin은 `https://api.furbebe.com`, canonical origin은 `https://furbebe.com`이다. 다른 origin을 넣으면 production build를 거부한다. frontend에는 이 두 공개 값만 define하며 server-secret canary를 빌드에 주입해 미포함을 확인했다. Cloud Run generated URL은 frontend에 하드코딩하지 않는다. `deploy/frontend.production.env.example`은 공개 설정만 포함한다.

Cloud Run YAML의 FRONTEND_ORIGIN은 정확히 `https://furbebe.com,https://www.furbebe.com`이다. local 개발 설정과 분리되며 wildcard/credentials는 허용하지 않는다. 두 origin의 실제 middleware CORS 허용 및 localhost 거부를 backend 테스트로 확인했다. CORS는 공개 read API의 인증/호출량 제한 기능이 아니다.

## Domains / DNS 필요사항

Seoul은 Cloud Run 기본 domain mapping 지원 지역이 아니고, Google도 해당 preview 방식을 production 권장안으로 제시하지 않는다. [Google 공식 domain 문서](https://docs.cloud.google.com/run/docs/mapping-custom-domains). 따라서 초안은 global external Application Load Balancer + Seoul serverless NEG + Google-managed HTTPS certificate이다. 별도의 비용 승인이 필요하며 아무 LB/IP/certificate도 생성하지 않았다. Cloud Run regional service는 그대로 Seoul에 둔다.

| Host / record | 승인 후 연결 | 지금 상태 |
| --- | --- | --- |
| furbebe.com | Cloudflare Worker Custom Domain의 managed DNS/certificate | 준비만 완료 |
| www.furbebe.com | 동일 Worker Custom Domain의 managed DNS/certificate | 준비만 완료 |
| api.furbebe.com A | 승인 후 할당할 global HTTPS LB static IPv4 | 실제 IP 미할당; Cloudflare DNS-only 초기안 |
| api AAAA | LB IPv6를 따로 승인한 경우에만 제공된 실제 IPv6 | 기본 필요 없음 |
| 인증 validation record | 선택한 certificate 방식에서 공급자가 요구할 때만 실제 제공 값을 사용 | 값 미확정 |

Cloudflare zone가 active이어야 한다. Workers custom domain 연결 시 Cloudflare가 DNS/인증서를 관리하며 기존 충돌 record(특히 CNAME)는 승인 전 목록을 점검한다. 임의 apex IP/CNAME 값을 만들지 않는다. [Cloudflare Custom Domains](https://developers.cloudflare.com/workers/configuration/routing/custom-domains/).

`api`를 단순 CNAME으로 run.app에 연결하는 것만으로 해당 host의 TLS/route가 해결되지는 않는다. Frontend는 api.furbebe.com만 호출한다. 공개 read API를 위해 service 단위 `allUsers → roles/run.invoker`의 unauthenticated invocation 허용을 별도 승인받아 구성하고, ingress로 run.app 직접 외부 접근을 제한한다. 조직 정책이 public IAM binding을 막으면 대체 invocation 방식을 먼저 결정해야 한다. 정적 LB IP, backend/NEG, certificate, host routing, API public invocation은 배포 전 unresolved 설정이다.

## CI / Sync Job

Quality CI는 pull_request, main push, manual에서 npm ci/test/lint/build, secret-canary/build-host 검사, Worker dry-run, Python 3.12/3.14 + disposable PostgreSQL pytest/Ruff, Docker build/run을 수행하도록 구성했다. contents:read, checkout credentials 미보존, timeout/concurrency 제한을 둔다. registry push나 production deployment step은 없다. GitHub 서버에서 실제 workflow 실행 결과는 아직 없다.

Sync는 `python -m backend.jobs.animal_sync.main`을 유지한다. DEV와 PROD GitHub Environment와 DB secret 이름을 분리했다. PROD CLI는 APP_ENV=production + DATABASE_URL_prod + SUPABASE_URL_prod + 독립 FURBEBE_PROD_PROJECT_REF 일치를 요구한다. generic DATABASE_URL/DEV secret으로 fallback하지 않고 transaction port/target redirect/TLS disable/production replay를 거부한다.

수집 주기는 KST 매일 00:00·12:00, 하루 2회로 변경했다. UTC cron은 `0 3,15 * * *`이다. `PRODUCTION_SYNC_ENABLED`가 unset/false이면 현재 DEV 수집 job이 schedule로 실행되고, true이면 PROD job만 실행한다. 자동 실행에는 workflow의 GitHub 기본 branch 반영과 해당 Environment의 secrets/variables 설정이 필요하다. 수동 PROD는 기존 confirmation과 Environment 설정을 유지한다. 상세 설정은 `deploy/sync-environments.md`를 따른다.

환경 이름/필요 항목은 `deploy/sync-environments.md`를 따른다. Actions concurrency + PostgreSQL advisory lock으로 동시 sync를 제어한다. 60분 timeout, 원천 API 기존 rate limit/retry와 안전한 부분 commit/report를 유지한다. 첫 PROD sync는 별도 승인과 bounded 범위 검토 후 실시한다. 수동 Actions는 begin/end 날짜 + max_animals=1000을 기본으로 하고, 날짜가 없거나 잘못되면 DB 접근 전 실패한다. full_scan checkbox를 명시한 경우만 수동 full 범위로 바꾼다. 이후 승인된 cron은 기존 `--full`(API 기본 date window)을 사용한다. schedule은 정확한 실시간 SLA가 아니다.

## Secrets 이름

| 위치 | 이름 | 용도 |
| --- | --- | --- |
| Cloud Run | DATABASE_URL ← Secret Manager furbebe-prod-database-url의 명시 version | PROD read API DB; 실제 값 없음 |
| GitHub development-sync | DATABASE_URL_dev, DATA_GO_KR_SERVICE_KEY | DEV DB / 원천 API |
| GitHub production-sync | DATABASE_URL_prod, DATA_GO_KR_SERVICE_KEY | PROD sync DB / 원천 API |
| 비밀이 아닌 target metadata | SUPABASE_URL_dev, SUPABASE_URL_prod, FURBEBE_PROD_PROJECT_REF | URL/ref와 credential target consistency |
| Frontend 공개 값 | VITE_API_BASE_URL, VITE_SITE_URL | 공개 API/canonical; server secret 아님 |

향후 Auth를 별도로 도입할 때 검토할 이름: SUPABASE_URL, SUPABASE_SECRET_KEY, SUPABASE_JWKS_URL. 현재 Auth나 해당 secret은 요구하거나 주입하지 않았다. 비밀 key는 browser/VITE_*와 Docker build args/CI artifacts에 넣지 않는다. 모든 기존 사용자 secret 값을 출력하지 않았다.

## Production Migration Plan

새 migration은 없다. 저장소 target head는 `20260915_0001`이다. PROD target/current revision은 아직 접속·조회하지 않아 미확인이다.

Read-only 도구 `python -m backend.jobs.production_preflight`를 준비했다. 명시 PROD project guard를 검증하고 READ ONLY transaction으로 현재 revision을 읽는다. 보고서는 target host/database/port, current/target revision, pending migration 파일 SHA256, offline upgrade SQL, 실행하지 않았다는 상태, rollback 주의를 포함한다. SQL 생성은 DB upgrade 실행이 아니다. 여러 head/current, 알 수 없는 revision이면 보고를 거부한다.

초기 upgrade는 shelters, animals, animal_images, tags, animal_tags, sync_runs 6개 table, UUID/JSONB, constraints/FK/index를 생성한다. downgrade는 이 6개를 삭제하므로 데이터가 있는 PROD에서 기본 rollback으로 사용하지 않는다.

승인 전 순서:
1. DEV와 다른 PROD project/ref, secret/role, connection mode/TLS 확인.
2. 현재 revision 조회 + head/current diff + migration SHA/SQL 보고. 현재와 target이 같으면 변경 없음으로 보고.
3. verified backup ID/checksum·restore drill·중단/복구 시간, DB 권한과 적용 영향 보고.
4. 코드 release commit/image digest와 rollback/roll-forward 방안 보고 후 사용자의 별도 migration 승인.
5. 승인 후에만 명시 target으로 Alembic 수행; current revision/health/data contract 검증. startup/CI는 PROD migration을 실행하지 않는다.

실행 예시는 approval 이후 운영자가 protected environment에서 secret을 주입한 상태에서만 사용한다. shell에 connection string을 붙이거나 set -x를 켜지 않는다.

```sh
# Read-only review; does not upgrade/downgrade.
python -m backend.jobs.production_preflight
# ONLY AFTER separate migration approval and reviewed backup/plan:
FURBEBE_DATABASE_TARGET=supabase-prod python -m alembic -c backend/alembic.ini upgrade head
```

## Backup / Recovery / Observability / Smoke

현재 Supabase plan의 실제 backup/PITR availability는 미확인이다. `deploy/backup-recovery-checklist.md`에서 Dashboard backup timestamp/retention/restore 가능 여부, encrypted off-site export, RPO/RTO, 별도 target restore rehearsal, 외부 사진/Storage/role/config 제외 범위를 확인하도록 준비했다. downgrade를 backup으로 취급하지 않는다. 새 paid monitoring/backup add-on은 도입하지 않았다.

HTTP application log: UUID request_id, matched endpoint template, method, status, duration_ms. 원시 query/body/headers, arbitrary unmatched path, SQL/DB URL/예외 repr을 log하지 않는다. production Uvicorn raw access log는 끈다. 기존 안전한 error handler와 X-Request-ID를 유지한다.

Sync page/report에 더해 final summary는 sync_id, received, inserted, updated, error/error_code, duration_seconds, status를 남긴다. 기존 source-serviceKey redaction 및 httpx/httpcore log 억제를 유지한다. API /health는 DB outage에 503이며 이를 운영 관측에 사용한다. Cloud Run platform request logs/Workers/Actions의 별도 retention/access를 점검하며 인증정보를 URL query에 전달하지 않는다. 실제 계정의 log sinks/retention은 변경하지 않았다.

배포 후 확인 항목은 `deploy/production-smoke-checklist.md`에 있다: frontend 세 route, 실제 API /health/list/filters/tags/detail/similar, images/favorites/share, keyboard/responsive, SEO/sitemap/robots, 두 domain CORS와 DEV 거부, sync/복구, 운영 사진·cold API 성능. 아직 production smoke를 실행하지 않았다.

## 비용 관련 설정

실제로 provisioning된 신규 cloud 자원은 없다. 비용 가능 항목만 검토한다.

- Cloud Run request CPU/memory/requests/egress. min0/max2/1CPU512MiB로 시작하되 max는 강제 비용 상한이 아니다. [Cloud Run pricing](https://cloud.google.com/run/pricing).
- API HTTPS용 external ALB의 forwarding rule/processing, 승인할 static IP, certificate 방식 관련 비용. min0 Cloud Run과 별개로 고정 비용이 발생할 수 있다. 미승인 상태다.
- Artifact Registry image storage/egress와 향후 선택한 image build/push 방식. 현재 CI는 local Docker build만 한다.
- Supabase PROD project/compute/storage/egress, paid backup/PITR 및 IPv4 add-on. plan/quotas 미확인; session pooler로 시작하고 add-on을 임의 활성화하지 않는다.
- Workers request/CPU/logging의 actual plan quota, Cloud Logging retention/storage.
- 하루 2회 sync의 Actions 실행 시간, 원천 API quota/rate limit, DB load. 실행 시간을 보고 billed minutes를 추산해야 한다. 실제 활성화 여부는 원격 기본 branch 및 Environment 설정으로 확인한다.

가격을 임의 확정하거나 큰 resource/NAT/새 SaaS를 provisioning하지 않았다.

## 사용자 설정 / 실제 배포 전 Blocker

- Cloud project/billing/region, Artifact Registry, 최소 runtime 서비스 계정과 Secret Manager version 권한을 확인한다. 생성/수정은 별도 승인 후.
- DEV/PROD를 서로 다른 Supabase project로 구성하고 plan/DB connection budget/TLS/role/backup 정책을 검증한다.
- Cloudflare active zone/account, 충돌 DNS, production domain ownership/certificate를 확인한다.
- API custom-domain 경로(초안 ALB)의 비용과 LB/IP/IAM/TLS/DNS 작업을 승인한다.
- repository GitHub Environments/secret/variables/branch protection을 구성한다. PROD gate는 승인 전 false 유지.
- GitHub CI에서 Docker build/run 및 Python 3.14 matrix green을 확보한다. 로컬 Docker는 아직 미검증이다.
- staging의 실제 데이터/사진 성능과 512MiB memory, connection 여유를 확인한다.
- PROD migration preflight/current revision과 verified restore/rollback 계획을 보고·승인받는다.
- 배포/첫 sync/DNS/cron 활성화는 각각 필요한 별도 사용자 승인 후에만 한다.

## 검증 결과

- npm ci: 성공, npm audit 0 vulnerabilities.
- Frontend 97 tests, ESLint 통과.
- Backend 전체 PostgreSQL tests 408개 통과, skip 0개. Ruff 통과. 고정 runtime constraints에서도 확인했고 third-party deprecation warnings 2개는 실패가 아니다.
- Production profile의 React Router client + SSR build 및 Worker deploy dry-run 통과. Public origin 고정, preview disable과 두 domain route 확인.
- 합성 server-secret canary / run.app generated host: client/server build 검색에서 미포함.
- CI/Cloud Run YAML parse, Docker smoke shell syntax, git diff whitespace 검사 통과.
- 실제 GitHub CI/Docker/Cloud Run 런타임 결과는 미확인. 실제 deploy/migration/DNS/sync 실행 없음.

## Phase 10 변경 파일

`.dockerignore`, `.env.example`, `backend/Dockerfile`, backend `app/core/config.py`, `database_target.py`, `http.py`, `logging.py`, `app/db/session.py`, `app/main.py`, `jobs/animal_sync/main.py`, `jobs/production_preflight.py`, `tests/test_production_preparation.py`; frontend `vite.config.js`, `wrangler.production.jsonc`; `.github/workflows/ci.yml`, `animal-sync.yml`; deploy `cloud-run.service.yaml`, `docker-smoke.sh`, `frontend.production.env.example`, `sync-environments.md`, `backup-recovery-checklist.md`, `production-smoke-checklist.md`; 본 문서와 `README.md`.

이전에 승인된 Phase 9 변경을 그대로 보존했고 `env`는 변경하지 않았다. 준비 단계에서 멈춘다.
