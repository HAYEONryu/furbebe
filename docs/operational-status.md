# 운영 상태

확인 기준: **2026-10-05, Asia/Seoul**. 숫자와 상태는 이 시점의 관측이며 실시간 dashboard가 아닙니다.
이 문서에는 수행 사실과 남은 작업만 기록합니다. 평상시 절차는 [인프라](infrastructure.md)와 [운영](operations.md)을 따릅니다.

## 운영 DB: 테이블 생성·최초 적재 완료

| 항목 | 확인 결과 |
| --- | --- |
| 프로젝트 | xhlenzdnqnbczekkovgl |
| 대상 | supabase-prod; DEV와 다른 프로젝트 |
| PostgreSQL | 17.11 |
| 연결 | session pooler, port 5432, TLS require |
| revision | 20261005_0005 |
| public 테이블 | animals, shelters, animal_images, tags, animal_tags, sync_runs, alembic_version |
| 최초 sync ID | 24b9fe4a-3457-4bc6-bd0a-4e8202e82ec4 |
| 원천 기본 범위 관측 | 발견일 2026-09-05~2026-10-05 |
| 수신 | 6,732건, 빈 종료 페이지 포함 8페이지 |
| 신규 저장 개 | 2,880건 |
| 원천 비대상 제외 | 3,852건 |
| 갱신·삭제·오류·거부·중복·재시도 | 각각 0 |

최초 적재 직후 행수: animals 2,880 / shelters 246 / animal_images 6,247 /
tags 27 / animal_tags 6,944 / sync_runs 1.
원천 timezone 없는 timestamp는 품질 이슈로 보존했고 체중 미해석도 원문을 유지했습니다.

capture와 저장 대상 ID/raw_payload 일치, 고아 참조·범위 위반 0을 읽기 전용으로 확인했습니다.
운영 DB를 사용한 로컬 API의 health/list/tags/meta/stats/detail/similar는 200이었습니다.
입양 가능 필터는 검증 시점 1,741건입니다. 한국 날짜와 수집에 따라 변합니다.

비공개 증거:

- .local/production-operations/initial-migration-report.json
- .local/production-operations/initial-sync-verification.json
- .local/sync/3c4173ce73034cb99e06e79382719998/

## 백업

적용 직전 backup ID: 20261005T084303Z.
.local/production-backups/20261005T084303Z에 public schema archive와 암호화 자료를 권한 제한해 보관했습니다.
archive 읽기·암호화 왕복 checksum·별도 PostgreSQL 17 복구 검증은 완료했습니다.

**이 backup은 테이블 생성 전 빈 public schema입니다. 최초 적재 데이터의 backup이 아닙니다.**
managed schema, roles/grants, Storage·외부 사진·클라우드 설정은 포함하지 않습니다.
외부 비공개 저장, 별도 key custody, 자동 매일 backup, 실데이터 restore rehearsal은 미검증입니다.
목표 정책은 매일+schema 변경 전 / 30일 보관 / RPO 24시간 / RTO 4시간이며 실제 구성 완료가 필요합니다.

## 애플리케이션·외부 배포

- 로컬 127.0.0.1:8080 API는 명시적 운영 DB 선택으로 확인했습니다.
- 로컬 127.0.0.1:5173 프런트엔드 정상 응답을 확인했습니다.
- 운영 Cloud Run/HTTPS LB/Cloudflare 신규 배포·DNS 연결 완료는 확인되지 않았습니다.
- 최근 외부 확인에서 furbebe.site는 530, /ads.txt는 404였습니다. API host도 DNS 미연결 상태였습니다.
- source에는 모든 페이지의 AdSense meta/script와 ads.txt가 있습니다. 외부 배포본 반영은 별도입니다.
- GitHub 운영 schedule 활성화와 environment secret 구성은 미완료로 남아 있습니다.
- DB 읽기/sync/migration 역할 분리와 staging 운영 성능 검증은 미완료입니다.

운영 DB에 데이터가 있으므로 “운영 테이블 없음”을 현재 상태로 안내하지 않습니다.
외부 배포·DNS·정기 수집·외부 백업은 완료된 DB 적재와 별개의 후속 작업입니다.

## 2026-10-06 후속 배포 보고

사용자가 프로젝트 `furbebe-backend`, region `asia-northeast3`에서 Cloud Build 빌드·업로드와
기존 Cloud Run `api` 서비스 갱신까지 성공했다고 보고했습니다.
이 기록은 사용자 보고를 근거로 하며 외부 `/health`·실제 데이터 API·DNS·TLS를 재검증한 결과는 아닙니다.
위 2026-10-05 외부 점검 결과와 구분합니다.
GitHub API 수동 배포용 `deploy/cloudbuild.api.yaml`과 연결 매뉴얼을 준비했습니다.
사용자 선호는 GitHub 코드를 연결하되 Run trigger 버튼을 누를 때만 배포하는 방식입니다.
GitHub repository 연결, 수동 trigger 활성화와 첫 버튼 배포는 아직 확인되지 않았습니다.
