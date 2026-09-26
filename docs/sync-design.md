# Phase 4B — Supabase DEV Migration / Smoke Sync / Full Sync

검증일: 2026-09-16, Asia/Seoul. Python 3.14.6 / Windows.

Supabase DEV migration과 smoke sync 2회, API 기본 조회의 전 페이지 sync를 완료했다.
중단 전에 끝난 적재 결과를 재개 시점에 읽기 전용 SQL과 원본 capture로 대조했으며,
전체 pytest를 별도 로컬 PostgreSQL에서 다시 실행했다. 이 문서는 Phase 4B 당시 기록이다.
후속 승인으로 구현한 읽기 API의 현재 결과는 [Phase 5 완료 보고](phase5-read-api.md)에 있다.

## 연결과 schema

| 검증 | 결과 |
| --- | --- |
| 대상 | Supabase DEV PostgreSQL, 연결 성공 |
| PostgreSQL | 17.6; 비교한 로컬 PostgreSQL은 18.6 |
| 최초 public schema | domain table 0, 기타 table 0, alembic_version 없음 |
| migration head | `20260915_0001` |
| domain table | shelters, animals, animal_images, tags, animal_tags, sync_runs |
| SQLAlchemy metadata 차이 | 0 |
| 로컬 migration manifest 차이 | 0 |
| 재개 후 DEV schema 차이 | 0 |

컬럼 타입·nullable·PK·FK·UNIQUE·CHECK·인덱스를 실제 PostgreSQL inspector로 비교했다.
TIMESTAMPTZ의 timezone 플래그와 `raw_payload` JSONB도 일치한다.
`UNIQUE(source, source_id)`, 이미지 URL 중복 방지, 태그 generator/version 단위 중복 방지,
confidence 0~1 CHECK와 FK 삭제 정책도 포함한다. Alembic autogenerate 비교만으로 CHECK를 판정하지 않았다.
기존 migration을 수정하거나 DEV에서 downgrade·DROP·RESET을 실행하지 않았다.

운영 명령은 `DATABASE_URL_dev`와 `SUPABASE_URL_dev`에 지정한 프로젝트를 비교한다.
직접 연결 또는 5432 session pooler만 허용하고 TLS를 적용한다. 6543 transaction pooler는
세션 advisory lock의 수명을 유지할 수 없어 허용하지 않는다. 접속 대상을 바꾸는 URL query나
libpq service/hostaddr 환경변수도 거부한다. 일반 `DATABASE_URL`로 자동 대체하지 않는다.
`host_dev`, `port_dev`, `database_dev`, `user_dev`가 있으면 연결 문자열과의 일치도 검사한다.
Supabase API 키는 SQL 비밀번호의 대체물이 아니며 sync는 PostgreSQL 연결만 사용한다.

## Smoke sync와 반복 실행

범위는 2026-09-14 하루, page size 1,000, batch size 500이다. 첫 실행은 live API,
두 번째는 checksum과 완전성을 검사한 동일 capture 재실행이다.

| 항목 | 첫 실행 | 같은 capture 재실행 |
| --- | ---: | ---: |
| received / unique / normalized | 315 / 315 / 315 | 315 / 315 / 315 |
| inserted_count | 315 | 0 |
| updated_count | 0 | 0 |
| unchanged_count | 0 | 315 |
| animals | 315 | 315 |
| shelters | 122 | 122 |
| animal_images | 630 | 630 |
| tags | 17 | 17 |
| animal_tags | 735 | 735 |
| sync_runs | 1 | 2 |
| API 요청 | 2 | 0 |
| 오류 / 재시도 / 중복 증가 | 0 / 0 / 0 | 0 / 0 / 0 |
| 소요 시간 | 약 5.77초 | 약 3.45초 |

SQL 샘플 10건의 source/source_id, notice_no, breed, weight, birth_year, 보호소 FK,
이미지, raw_payload, first_seen_at, last_seen_at 검증을 통과했다.
두 실행의 identity digest가 같고 동물·보호소·이미지·태그 수가 증가하지 않았다.

## Full sync와 최종 데이터 검증

실행 시각: 2026-09-16 08:28:26~08:29:06 KST.
날짜·축종·지역 등 필터 없이 API가 반환한 모든 페이지를 수집했다.

| 항목 | 결과 |
| --- | ---: |
| OpenAPI totalCount / received / unique | 7,290 / 7,290 / 7,290 |
| normalized | 7,290 |
| inserted / updated / unchanged / stale | 6,975 / 0 / 315 / 0 |
| animals DB count / unique source animals | 7,290 / 7,290 |
| shelters | 287 |
| animal_images | 15,985 |
| tags | 17 |
| animal_tags | 18,405 |
| 축종 | 개 4,619 / 고양이 2,515 / 기타 156 |
| 페이지 / API 요청 | 데이터 8 + 빈 종료 1 / 9회 |
| batch size | 500 |
| rejected / error / duplicate / retry | 모두 0 |
| 전체 / API fetch / DB 시간 | 약 39.79 / 11.76 / 27.16초 |
| 정규화 시간 | 약 0.73초 |
| 처리율 | 약 183.20건/초 |

처리율은 이 실행의 로컬 관측값이며 운영 성능 보장이 아니다. CLI 시작·capture 사전 검사 시간은
`total_seconds`에 포함하지 않는다. 단계별 시간은 전체 시간 안에 포함된다.

| 최종 SQL·capture 검사 | 결과 |
| --- | ---: |
| orphan animal_images / animal_tags | 0 / 0 |
| invalid shelter FK | 0 |
| duplicate source/source_id | 0 |
| duplicate animal images / animal tags | 0 / 0 |
| confidence outside 0~1 | 0 |
| invalid raw_payload / first_seen > last_seen | 0 / 0 |
| capture에는 있지만 DB에 없는 source ID | 0 |
| DB에는 있지만 capture에 없는 source ID | 0 |
| capture와 DB의 raw_payload 불일치 | 0 |
| smoke 최초 관측 시각이 full sync 이후로 바뀐 동물 | 0; 기존 315건 유지 |
| last_seen_at이 full sync 시작보다 오래된 동물 | 0 |
| SQL 샘플 | 10건 통과 |

최종 검사는 `REPEATABLE READ` + `SET TRANSACTION READ ONLY`에서 실행했다.
capture SHA-256과 빈 종료 페이지까지 다시 검사하고 7,290건 전체의 ID와 raw payload를 DB와 비교했다.

### Phase 1 수치와 다른 이유

`--full`은 **API 기본 조회 범위의 모든 페이지**이며 과거 전체 이력의 수집을 뜻하지 않는다.
이번 capture의 실제 발견일 범위는 2026-08-16~09-16이다.
Phase 1의 60,515건은 2026-01-01~09-14를 명시한 totalCount이며,
그중 목표 표본까지 받은 17,000건과 이번 DB 수치를 동일 모집단으로 비교하지 않는다.

2026-09-16 13:17 KST에 각 조건의 1행만 읽어 범위 차이를 확인했다(총 3회, 재시도 0).

| 비교용 요청 조건 | 당시 totalCount |
| --- | ---: |
| 필터 없음 | 7,383 |
| 2026-08-16~09-16 명시 | 7,383 |
| Phase 1과 같은 2026-01-01~09-14 | 60,702 |

두 조회의 같은 totalCount와 capture 발견일 범위는 기본 조회가 최근 한 달 범위로 제한된다는
관측 근거다. 제공기관의 영구적인 기본값 보장으로 해석하지 않는다.
[공식 서비스 안내](https://www.data.go.kr/data/15098931/openapi.do)는 참조했으나,
이 범위 설명은 실제 비교 요청의 관측 결과에 근거한다.
오전 적재 7,290건과 오후 확인 7,383건은 서로 다른 시점이다. 이후 조회 3건은 적재하지 않았고,
기존 capture·DB에 합산하지 않았다. 과거 이력 backfill은 필요한 날짜 범위를 정해 별도로 실행한다.

## Counter와 갱신 정책

- `inserted_count`: 새 `(source, source_id)` 동물 수.
- `updated_count`: 기존 동물의 정규화 내용·raw payload 등 저장 내용이 바뀐 수.
- `unchanged_count`: 저장 내용이 같아 동물의 `last_seen_at`만 갱신한 수. 동물 `updated_at`은 유지한다.
- `stale_count`: 명시적 source 수정 시각이 더 오래되어 사실을 덮어쓰지 않고 관측 시각만 갱신한 수.

이 네 counter는 서로 구분된다. 이미지·태그·보호소 갱신 수를 동물 updated_count에 더하지 않는다.
동물 내용이 같아도 source 소유 이미지·현재 버전 규칙 태그의 관계를 재확인하며 수동 소유권은 보존한다.
`sync_runs`에는 기존 schema대로 inserted/updated가 저장된다. unchanged/stale는 로컬 실행 report에 남긴다.
Phase 4A 보고서의 updated는 기존 동물 관측 수였으며, Phase 4B에서 사용자 원칙에 맞춰 변경했다.

batch별 동물·자식 관계·삽입/변경 counter는 같은 transaction으로 commit한다.
API 장애, totalCount 변동, 0건, 불완전 페이지, 거절 행, DB 실패를 정상 완료로 숨기지 않는다.
이미 commit한 batch는 보존하며 누락만으로 기존 동물을 삭제하거나 inactive 처리하지 않는다.

## sync_runs

| 실행 | 상태 | page / received | inserted / updated | error | 종료 시각 |
| --- | --- | --- | --- | --- | --- |
| smoke live | success | 2 / 315 | 315 / 0 | 0 | 기록됨 |
| smoke replay | success | 2 / 315 | 0 / 0 | 0 | 기록됨 |
| full live | success | 9 / 7,290 | 6,975 / 0 | 0 | 기록됨 |

최종 DB에는 세 실행만 있으며 running 상태는 없다. full report와 DB counter·종료 기록도 일치한다.

## 실행 명령

프로젝트 루트에서 실행한다. 접속 문자열과 키는 `.env` 또는 환경변수에서 읽으며 명령에 붙이지 않는다.
`DATABASE_URL_dev`, `SUPABASE_URL_dev`를 사용하고 `.env.example`에 변수 이름이 있다.
앱의 `DATABASE_URL`과 운영 명령의 DEV 설정은 별개다.

```powershell
# 읽기 전용 사전 확인: 설정 target을 검증한 후 public schema 현황만 출력
@'
import json
from sqlalchemy import text
from backend.app.core.database_target import get_dev_database_settings
from backend.app.db.session import create_database_engine
from backend.jobs.animal_sync.verification import preflight

engine = None
try:
    engine = create_database_engine(get_dev_database_settings())
    with engine.connect() as conn, conn.begin():
        conn.execute(text("SET TRANSACTION READ ONLY"))
        print(json.dumps(preflight(conn)))
except Exception:
    print('{"status":"failed","error_code":"DEV_PREFLIGHT_FAILED"}')
    raise SystemExit(2)
finally:
    if engine is not None:
        engine.dispose()
'@ | .\.venv\Scripts\python.exe -

# 최초 적용: 사전 검토한 DEV에만 적용. 현재 검증된 DEV에는 이미 적용됨.
$previousTarget = $env:FURBEBE_DATABASE_TARGET
try {
    $env:FURBEBE_DATABASE_TARGET = 'supabase-dev'
    .\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
} finally {
    $env:FURBEBE_DATABASE_TARGET = $previousTarget
}

# 315건 smoke에 사용한 조건. source total이 1,000을 넘으면 동물 적재 전에 실패.
.\.venv\Scripts\python.exe -m backend.jobs.animal_sync.main --database-target supabase-dev --begin-date 2026-09-14 --end-date 2026-09-14 --max-animals 1000 --max-pages 3 --batch-size 500

# 위 실행이 출력한 output_directory의 capture를 지정
.\.venv\Scripts\python.exe -m backend.jobs.animal_sync.main --database-target supabase-dev --replay .local/sync/<smoke-run-directory>/pages.jsonl --max-pages 3 --batch-size 500

# API 기본 날짜 범위의 모든 페이지. 모든 과거 이력이 아님.
.\.venv\Scripts\python.exe -m backend.jobs.animal_sync.main --database-target supabase-dev --full --page-size 1000 --batch-size 500
```

위 명령을 재실행하면 새 sync_runs와 관측 시각이 기록된다. 과거 결과 확인에는 보관된 report와 capture를 사용한다.
live 성공은 exit 0, 실패는 exit 2이며 schema를 자동 생성하지 않는다.
`--max-animals`는 일부 동물만 잘라 성공시키는 기능이 아니라 totalCount 상한 검사다.
`--max-pages`에는 빈 종료 페이지가 포함된다. `--full`과 날짜·동물 상한은 함께 사용할 수 없다.

## Tests와 검증 자료

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

재개 후 전체 suite는 **300 passed / 0 skipped**, Ruff 통과다.
Starlette/httpx와 AnyIO 관련 기존 deprecation 경고 2개가 있다.
DB 환경변수를 지정하지 않은 일반 실행은 240 passed / 60 skipped다.
통합 테스트를 포함하려면 `FURBEBE_TEST_DATABASE_URL`에 비어 있는 loopback `furbebe_test*`
전용 DB를 지정한다. 실제 DEV는 테스트 fixture 대상으로 사용하지 않는다.
fixture는 원격 host·연결 우회 query를 거부하고 Alembic의 DEV target 선택을 해제한다.
이번 테스트에 사용한 로컬 PostgreSQL은 검증 후 종료한다.

로컬 증거는 `.local/phase4b/`에 보관한다.

- `preflight.json`, `migration-verification.json`: 최초 DEV 상태, migration 및 schema manifest 비교.
- `smoke-verification.json`: smoke 두 실행, SQL 샘플, identity digest, 중복 검사.
- `full-report.json`, `full-cli.log`: 원래 full 실행의 수량·페이지·시간.
- `full-verification.json`: 재개 후 읽기 전용 DEV schema·무결성·sample·sync_runs.
- `capture-database-verification.json`: 7,290건 capture와 DB의 전체 ID·raw 대조, 관측 시각 확인.
- `query-scope-verification.json`: 기본 조회와 날짜 범위의 1행 비교 요청 3회.
- `pytest-resume.xml`: 재개 후 300개 전체 테스트 결과.

원본 응답·연결정보·단건 데이터는 Git 제외 경로에만 보관한다. 문서에는 aggregate만 기록한다.

## 알려진 제한과 다음 단계

실제 7,290건 모두 원천 수정 시각에 timezone이 없어 `source_updated_at=NULL`이다.
체중 44건은 해석할 수 없는 원문이라 `weight_kg=NULL`이며 raw payload를 보존했다.
API는 페이지 사이의 snapshot isolation을 보장하지 않는다. 같은 totalCount 안의 동시 변경까지
검출했다고 주장하지 않는다. 프로세스 강제 종료나 DB 완전 단절 시 sync_runs가 running으로 남을 수 있다.

과거 전체 이력 backfill과 자동 스케줄링은 이번 검증에 포함하지 않았다.
수동 태그 품질 검토와 외부 규칙 파일화는 기존 후속 항목이다.
Supabase Data API·Edge Functions·Realtime·Frontend client는 추가하지 않았다.
Docker build/run은 **미검증 유지**이며 deployment 단계에서 검증한다.

Phase 4B 검증 blocker는 없다. 당시 Phase 5 진행 가능으로 보고했으며,
후속 사용자 승인에 따른 구현·검증 결과는 [Phase 5 완료 보고](phase5-read-api.md)에 기록한다.
