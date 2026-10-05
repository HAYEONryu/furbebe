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
