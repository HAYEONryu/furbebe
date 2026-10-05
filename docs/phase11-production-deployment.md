# Phase 11 — Production Deployment 재시도

확인일: 2026-10-05 (Asia/Seoul).

## Production DB

Production 설정 존재 여부와 기존 target guard 통과. Secret 값 미출력. 네트워크 허용 후 실제 DB 읽기 전용 접속 통과.

- Target: supabase-prod
- Host: aws-0-ap-southeast-2.pooler.supabase.com
- Database / port / TLS: postgres / 5432 / require
- DEV와 PROD project URL이 서로 다름을 확인.
- PostgreSQL: 17.11
- pg_is_in_recovery(): false
- public schema 테이블: 0개. 다른 schema가 비어 있다는 뜻은 아님.
- Alembic current: base (public.alembic_version 없음).
- 저장소 head: 20261003_0004.
- Preflight는 offline upgrade SQL만 생성. 실제 migration 미실행.

## Backup / Recovery

저장소에서 deploy/backup-recovery-checklist.md만 발견. 실제 backup ID/시각/checksum/암호화 off-site 보관 위치/별도 DB restore rehearsal/RPO/RTO는 미확인. 사용자에게 Secret 없이 증거 또는 로컬 기록 경로를 요청했다. 이 증거 없이는 2단계를 통과로 처리하지 않는다.

## 추가 문제

20261003_0004에는 animal_tags 및 tags DELETE가 있다. 사용자의 destructive cleanup 금지에 따라 실행하지 않았다. public 테이블이 없더라도 금지된 cleanup SQL을 그대로 실행하지 않는다. 기존 migration을 임의 수정하거나 revision을 stamp하지 않았다.

현재 .github/workflows/animal-sync.yml은 DEV-only workflow다. APP_ENV=development, supabase-dev --full 실행이며 Production environment/gate/job이 없다. Phase 10 문서의 production sync 준비 설명과 불일치한다. 원격 GitHub 실행 결과나 설정은 아직 검증하지 않았다.

## 최종 상태

BLOCKED — 2단계 외부 백업 보관/키 분리 및 복구 정책 미확정.

3~14단계 미실행. DB reset / DROP / destructive cleanup, sync, Cloud Run/Cloudflare deploy, DNS 변경, production cron 활성화 없음. 이번 실행은 DB 읽기 전용이므로 rollback 불필요.

## 사용자 답변 이후 backup/recovery 준비

사용자가 기존 백업이 없다고 확인했다. PostgreSQL 16 pg_dump는 PROD 17.11과 호환되지 않아 PostgreSQL 17.11 도구를 설치했다. 기존 연결된 PostgreSQL 16 도구나 운영 서비스는 전환하지 않았다. Homebrew 패키지 설치가 로컬 기본 cluster를 초기화했으며 상시 서비스는 시작하지 않았다.

- Backup ID: 20261005T042431Z (2026-10-05 13:24:31 KST).
- 위치: .local/production-backups/20261005T042431Z (git 제외, directory 0700/file 0600).
- 범위: public schema만. 현재 테이블 0개. 관리 schema, roles/grants, Storage 및 계정 설정 제외.
- public.dump archive SHA256: b260b022566ef50b2de9d0e503928f0c1cc216e3177b18b2de91cca4532f1fce.
- public.dump.enc SHA256: 6f7620fabdd9ba9f6bf2661a9ae939944d99b0fa060659b319409968d0419270.
- 암호화: AES-256-CBC / PBKDF2 200000 iterations. Key는 보호된 로컬 파일이며 출력하지 않았다. 현재 archive/key 모두 같은 장치에 있으므로 외부 보관/키 분리 완료로 주장하지 않는다. 원본 archive도 보호된 로컬 폴더에 남아 있다.
- Archive 읽기, 암호화→복호화 checksum 일치 통과.
- 별도 임시 PostgreSQL 17 Unix-socket-only cluster에 복구 통과. source/restored public table 목록 모두 빈 목록. 검증 후 서버 종료.
- 최초 복구는 이미 존재하는 public schema의 CREATE SCHEMA 충돌로 실패. 기본 schema의 CREATE 항목만 TOC에서 제외한 후 재검증 통과. DROP/cleanup 사용 안 함.
- 성공한 초기 상태 복구 검증 소요 1.19초. 이 값은 운영 RTO 또는 실데이터 복구 성능을 뜻하지 않는다.

외부 비공개 보관 위치, 별도 key custody, 담당자, RPO/RTO와 backup cadence/retention은 미확정이며 사용자에게 요청했다. 현재 상태에서는 2단계 완료가 아니므로 3~14단계를 실행하지 않는다. public 외 schema의 복구를 검증한 백업이 아니라는 범위 제한도 유지한다.

## 2026-10-05 선택 사항 반영 및 배포 준비

사용자 선택: 비공개 클라우드 백업 + 비밀번호 관리자 key custody; 매일 및 migration 직전 백업, 30일 보관, RPO 24시간/RTO 4시간 목표; 사용자 복구 담당. 실제 저장소/키 분리와 자동 백업은 아직 미구성이다.

대표 도메인은 가비아에서 구매한 furbebe.site, www.furbebe.site는 308 redirect, API 도메인은 api.furbebe.site로 준비했다. Cloudflare Worker를 assets보다 먼저 실행하고 ASSETS binding으로 canonical host의 정적 파일을 제공하므로 www의 robots/정적 파일도 redirect된다. 운영 DNS/certificate/도메인 소유권은 아직 검증하지 않았다.

Cloud Run 초기 용량은 1 CPU/512MiB/min0/max2/concurrency4. API DB 읽기 역할/sync 쓰기 역할/migration 관리 역할 분리, release commit/CI/staging 통과 후 배포 선택. 실제 DB 역할 분리와 cloud account/project/billing 설정은 아직 완료되지 않았다.

첫 sync는 최근 7 KST calendar days/원천 total 최대 1000건 검증 후 API 기본 조회 기간 전체 적재, 이후 KST 00:00/12:00 정기 실행. 7일 원천 total이 1000을 초과하면 기존 guard가 동물 쓰기 전에 실패하며 임의 truncation/범위 확대는 하지 않는다. PROD workflow를 추가했으나 원격 Environment secrets/variables/보호 설정 및 gate 활성화는 미완료이다.

DEV 읽기 전용 이력 확인: current 20261003_0004. 사용자 선택 3A에 따라 0004를 데이터 보존 UPDATE tags.is_active=false 방식으로 수정했다. 이미 DEV에서 적용된 이전 삭제를 복구하는 변경이 아니며, checksum 변경 이력을 배포 시 고려해야 한다. 새 20261005_0005는 animals/animal_images/animal_tags에 is_active를 추가한다. sync는 종료 동물·이전 이미지·이전 태그를 보존하며 API는 비활성 행을 노출하지 않는다. 전체 base→head offline SQL에 DELETE FROM / DROP TABLE 없음. 자동 downgrade는 거부하고 검증된 복구/roll-forward 계획을 요구한다.

API 코드가 jobs를 import하던 Docker runtime 결함을 발견해 parser/clock을 app/core로 분리했다. 기존 jobs import 경로는 compatibility export로 유지한다.

검증: PostgreSQL 17 전용 로컬 DB backend 420 passed/0 skipped, Ruff 통과; frontend 119 tests/ESLint 통과; furbebe.site production client/SSR build 및 Worker dry-run 통과. API-only 소스 복사 runtime에서 jobs 없이 startup, 로컬 DB /health와 read endpoints, production CORS/DEV 거부/docs off 통과. 실제 Docker/Cloud Run runtime 검증을 대신하지는 않는다. 상세 sitemap은 live API 준비 후 생성해야 하며 현재는 /와 /dogs만 있다.

Production DB migration/sync/deployment/DNS 변경 없음. 실제 외부 백업/키 보관 위치와 API HTTPS 연결 방식(Load Balancer 또는 대체안)이 미선택이다. 비용은 산정 후 승인받아야 한다. 2단계 backup/recovery가 아직 미완료여서 Production migration을 진행하지 않는다. 운영 rollback 불필요.

### 원격 CI / release 준비

Draft PR: https://github.com/HAYEONryu/furbebe/pull/3

53a7855의 GitHub CI에서 backend Python 3.12/3.14 및 Docker build/startup/nonroot/health/CORS/secret-log smoke가 통과했다. Frontend는 URL 상태가 바뀐 직후 DOM commit 전에 확인하는 routes.test.jsx의 비동기 assertion race 1개로 실패했다. DOM 갱신과 URL 조건을 같은 waitFor에서 확인하도록 수정했다. 최종 CI 상태는 최신 commit의 결과로 확인해야 한다. PR은 merge하지 않았다.

GitHub Environment 조회 결과는 빈 목록이며 PRODUCTION_SYNC_ENABLED repository variable도 발견되지 않았다. 운영 sync는 활성화하지 않았다.

0004 이전 checksum: 6a558941c3947272fdcb1ba4bdc33770fe6f0669906f143e62f34c4d92cfae72
0004 데이터 보존 수정 checksum: bc9ad9192d9b9f82e77b07ccf8d7ad7cbda8a6467a441ee8f0327679ab96d449
