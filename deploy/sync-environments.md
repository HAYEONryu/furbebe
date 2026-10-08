# GitHub Actions 수집 설정

기준 workflow: [.github/workflows/animal-sync.yml](../.github/workflows/animal-sync.yml).
CI workflow와 달리 이 workflow는 실제 DB에 쓰는 수집 작업입니다.

## DEV job 설정

현재 development job에는 GitHub Environment 지정이 없습니다.
실제 workflow가 읽는 **repository secrets** 이름은 다음과 같습니다.

| GitHub secret | 프로세스 변수 |
| --- | --- |
| DATA_GO_KR_SERVICE_KEY | DATA_GO_KR_SERVICE_KEY |
| DATABASE_URL_DEV | DATABASE_URL_dev |
| SUPABASE_URL_DEV | SUPABASE_URL_dev |

APP_ENV=development, pool 1+1로 실행합니다.
development-sync environment만 만들어 secret을 넣어도 현재 job이 읽지 않습니다.
DEV 수동 실행은 날짜/full_scan 입력과 무관하게 --full입니다.

## PROD job 설정

Environment **production-sync**를 사용합니다.
production secret을 이 environment에 제한하고 가능한 plan에서는 필요한 reviewer와 main branch 제한을 설정합니다.

| GitHub environment 항목 | 이름 | 프로세스 변수 |
| --- | --- | --- |
| secret | DATABASE_URL_PROD | DATABASE_URL_prod |
| secret | DATA_GO_KR_SERVICE_KEY | DATA_GO_KR_SERVICE_KEY |
| variable | SUPABASE_URL_PROD | SUPABASE_URL_prod |
| variable | FURBEBE_PROD_PROJECT_REF | FURBEBE_PROD_PROJECT_REF |

APP_ENV=production, HTTPS FRONTEND_ORIGIN과 pool 1+1은 workflow에서 고정합니다.
프로젝트 ref와 URL·접속 사용자/호스트는 대상 guard가 검사합니다.
GitHub secret/variable 이름은 대소문자를 구분하지 않으며, 프로세스 변수 이름은 표와 동일하게 유지합니다.
이름이 같은 environment 값은 repository 값보다 우선합니다. Environment 값이 없으면 repository secret/variable도 사용합니다.

## 수동 PROD 실행

Actions > Animal Sync > Run workflow:

1. 검토된 branch와 target=supabase-prod (기본값).
2. production_confirmation=APPROVED_PRODUCTION_SYNC.
3. 기본은 오늘과 이전 6일의 KST 7일 범위, raw total 최대 1000.
4. 다른 날짜는 YYYY-MM-DD로 시작·종료를 모두 검토.
5. full_scan=true이면 API 기본 날짜 범위 전체이며 날짜/1000 제한을 사용하지 않음.

raw total이 1000보다 크면 동물 쓰기 전에 실패합니다. 임의 truncation은 없습니다.
수동 확인 문자열은 PROD에만 적용하고 scheduled PROD는 해당 조건을 검사하지 않습니다.
실행 후 status, sync_id, report, DB durable counter와 원천 제외/오류를 확인합니다.

## 정기 실행

UTC cron `0 3,15 * * *` = KST **12:00, 다음 날 00:00**, 하루 2회입니다.

| repository variable PRODUCTION_SYNC_ENABLED | schedule 대상 |
| --- | --- |
| true | PROD job |
| unset 또는 다른 값 | DEV job |

DEV/PROD가 한 schedule event에서 동시에 실행되지 않습니다.
두 scheduled job은 --full입니다.
false는 전체 수집 중지가 아니므로 장애 시 schedule/workflow를 disable하고 running job도 확인합니다.

schedule은 default branch의 workflow에서 실행하며 시작이 지연될 수 있습니다.
[GitHub schedule 안내](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

job timeout은 60분, concurrency는 animal-sync-dev/prod별 한 개,
cancel-in-progress=false입니다. PostgreSQL advisory lock은 Actions 외부 CLI 중복도 막습니다.

runner의 .local/sync 원문은 ephemeral이며 공개 artifact로 업로드하지 않습니다.
실행 로그와 보고서는 권한·retention을 관리합니다.
최초 운영 적재 완료와 schedule 활성화는 별도 작업이며 실제 상태는 [운영 상태](../docs/operational-status.md)를 봅니다.
