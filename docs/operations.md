# 운영 매뉴얼

실제 데이터·배포 상태는 [운영 상태](operational-status.md)에, 평상시 수집 명령은 [수집 설계](sync-design.md)에 있습니다.
이 문서는 기존 도구와 명시적 작업을 이용하는 절차입니다. 자동 백업·알림이 이미 설치되었다고 가정하지 않습니다.

## 평상시 확인

- API /health, 목록·메타·상세의 상태와 cold/warm 지연.
- 마지막 success sync_runs.finished_at, failed/running 실행, 오류 코드와 원천 수신량.
- 활성 개 수·이미지·태그의 변화, unexpected excluded/rejected/parsing 이슈.
- Cloud Run memory/instance/concurrency/pool timeout, Workers 오류, Actions 실패.
- 백업의 최근 성공 시각·checksum·외부 보관·키 접근·복구 연습.

API 로그는 request_id, endpoint template, method, status, duration_ms를 제공합니다.
수집 로그는 sync_id, 안전한 오류 코드, 페이지·batch counter를 제공합니다.
query/body/SQL/DB URL/원천 인증 URL을 공개 로그나 이슈에 붙이지 않습니다.
로그 보관·접근 제한과 실제 alert는 사용하는 계정에서 별도 구성합니다.

## 백업 정책과 범위

목표 정책은 **매일 + migration 직전, 30일 보관, RPO 24시간/RTO 4시간**입니다.
복구 담당은 사용자입니다. 실제 자동화·외부 보관·키 분리 완료 여부는 운영 상태를 확인합니다.
이는 목표이며 입증된 실제 복구 성능이 아닙니다.

Supabase Dashboard의 Database > Backups에서 실제 plan·가용 backup·retention을 확인합니다.
관리형 backup/PITR이 모든 plan에 있다는 가정을 하지 않습니다.
DB backup은 Storage object 파일과 외부 보호소 사진을 복구하지 않습니다.
[Supabase 백업 안내](https://supabase.com/docs/guides/platform/backups)

애플리케이션 public schema export에는 여섯 도메인 테이블과 alembic_version을 포함합니다.
roles/grants, extensions, provider 관리 schema, secret, DNS/IAM/Worker 설정은 별도 inventory입니다.
--no-owner/--no-privileges export로 권한까지 복구됐다고 주장하지 않습니다.

## 논리 백업 절차

서버 version과 맞는 PostgreSQL client를 사용합니다. 운영 확인 버전은 17 계열입니다.
pg_dump 16은 PostgreSQL 17 서버를 dump할 수 없습니다.
Custom archive는 pg_restore로 검사·복구합니다. [pg_dump 공식 문서](https://www.postgresql.org/docs/17/app-pgdump.html)

접속 URI·비밀번호를 command argument에 넣지 않습니다.
관리되는 libpq service 파일에 host/port/db/user/TLS를, 권한 0600의 passfile에 암호를 준비합니다.
아래 service 이름은 비밀정보 없이 접근을 참조하는 예제입니다.
PGSERVICE를 전역 export하면 명시적 앱 target guard에 걸릴 수 있으므로 backup 명령에서만 service를 지정합니다.

```sh
umask 077
mkdir -p .local/production-backups/NEW_BACKUP_ID
pg_dump --dbname='service=furbebe_prod_backup' --format=custom --schema=public --no-owner --no-privileges --file=.local/production-backups/NEW_BACKUP_ID/public.dump
pg_restore --list .local/production-backups/NEW_BACKUP_ID/public.dump
shasum -a 256 .local/production-backups/NEW_BACKUP_ID/public.dump
```

실제 backup ID는 시각을 포함해 유일하게 정합니다.
서버 version, project, 시각, revision, 범위, table/count, archive checksum을 manifest에 기록합니다.
검사 후 관리되는 암호화 도구로 archive를 암호화하고 복호화 checksum도 검증합니다.
암호화본은 제한된 비공개 외부 저장소에, 키는 별도 비밀번호 관리자에 보관하고 실제 접근을 시험합니다.
원본·키가 같은 장치에만 있으면 외부 백업·키 분리 완료가 아닙니다.

## 복구 연습

새 disposable DB/프로젝트에 복구합니다. 운영 DB 위에서 --clean/drop을 시험하지 않습니다.
dump의 public CREATE SCHEMA가 이미 존재하는 schema와 충돌하면 TOC를 검토해 해당 생성 항목만 제외합니다.
운영 schema 삭제로 충돌을 피하지 않습니다.

아래 대상 service는 **별도 연습 DB**로 설정합니다.

```sh
pg_restore --dbname='service=furbebe_restore_rehearsal' --no-owner --no-privileges --exit-on-error --single-transaction --use-list=.local/production-backups/NEW_BACKUP_ID/restore.list .local/production-backups/NEW_BACKUP_ID/public.dump
```

restore.list는 pg_restore --list 출력을 검토해 준비한 파일입니다.
누락된 grants/owner와 비DB 설정을 inventory에 따라 재적용합니다.
여섯 테이블·revision·행수·FK/index/중복·raw snapshot을 확인하고 API health/list/detail/meta/similar와
격리된 수집 재실행을 검사합니다. 종료 시점·실제 소요·데이터 손실 창을 기록합니다.
빈 schema 복구 시간으로 실데이터 RTO를 주장하지 않습니다.

## 장애 복구

1. 운영 수집을 중지하고 실행 중 writer를 확인합니다. PRODUCTION_SYNC_ENABLED=false만으로 모든 수집이 멈추지 않습니다.
2. 로그·revision·비밀값 없는 설정·문제 시점·현재 데이터를 보존합니다.
3. 앱 문제면 호환 가능한 이전 release로 rollback합니다.
4. DB 복구가 필요하면 시점을 정하고 별도 target 복구를 우선합니다.
5. 복구 검증 후 승인된 DB secret과 앱 revision으로 전환하고 smoke합니다.
6. 필요한 원천 날짜 구간을 재수집해 누락을 조정하고 schedule을 재개합니다.
7. 복구 시각·RPO/RTO 실제값·영향 범위를 기록합니다.

DB downgrade는 backup이 아닙니다. 전면 재생성·prune·destructive restore를 정상 복구 자동 단계에 넣지 않습니다.

## “정보를 불러오지 못했어요” 진단

| 증상 | 먼저 확인 | 해결 방향 |
| --- | --- | --- |
| API 시작 실패 | APP_ENV 중복, 일반/명시적 DB 변수, selector 프로세스 값 | [환경 설정](environment.md)에 맞춰 재시작 |
| /health 503 | 자격증명·network·pool 한도·DB 가용성 | 연결 문제 해결; DB reset 금지 |
| /health 200, 목록 503 | Alembic revision·누락 column, query timeout | preflight/current 확인 후 필요한 migration |
| API 200, 홈 실패 | 동물뿐 아니라 tags/meta도 200인지, frontend 공개 URL | loader 의존 endpoint 모두 확인 |
| 개발 화면에 production API 사용 | frontend/.env.local, 프로세스 공개 URL | API origin 수정 후 Vite 재시작 |
| 외부 사이트 530·DNS 오류 | Cloudflare zone/custom domain·TLS, API DNS | 인프라 경로 진단; 로컬 성공과 구분 |
| 브라우저에서만 CORS 실패 | 정확한 Origin과 FRONTEND_ORIGIN | 환경 목적에 맞는 허용 origin 설정 |
| 원천 total 제한 실패 | 날짜 범위 raw total | smaller 범위 또는 명시적 full 결정; truncation 금지 |
| SYNC_ALREADY_RUNNING | 다른 Actions/CLI writer와 lock | 종료·최종 status 확인 후 재실행 |
| 늦은 원천 상태·날짜 변화 | 마지막 성공 수집과 조회 시 KST 정책 | 올바른 구간 수집, 캐시 수명 확인 |
| 광고가 보이지 않음 | root head/script, ads.txt, 배포·AdSense 승인·자동 광고 | [프런트엔드](frontend.md)의 확인 순서 |

개발 API reload 부모만 남고 worker가 죽은 경우 요청이 멈출 수 있습니다.
해당 개발 프로세스의 설정 오류를 해결해 재시작하며 무관한 프로세스를 일괄 종료하지 않습니다.

## 보관과 정리

node_modules/가상환경/실행 cache는 개발 동작에 필요합니다.
종료 후 재생성 가능한 Python cache·test-results·브라우저 screenshot·frontend/build는 정리할 수 있습니다.
.env·migration·DB data directory·.local/sync·production-backups·운영 증거는 유지합니다.
sitemap은 정적 파일이므로 성공한 수집 후 새 동물이 indexable해져야 하면 별도 build/deploy로 갱신합니다.
