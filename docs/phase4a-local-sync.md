# Phase 4A — Local Animal Sync

검증일: 2026-09-16, Asia/Seoul. Python 3.14.6 / PostgreSQL 18.6 / Windows.

이 문서는 Phase 4A 당시 기록이다. 이후 [Phase 4B](sync-design.md)에서 명시적 Supabase DEV
대상을 추가했고, `updated_count`를 내용이 변경된 동물 수로 수정했다. 동일 payload는
`unchanged_count`, 더 오래된 source는 `stale_count`로 구분한다. 아래 로컬 제한과 갱신 수치는 당시 기준이다.

## 결과

기존 미완성 sync를 이어서 로컬 CLI·실제 PostgreSQL·실제 API capture 재실행까지 검증했다.
source 검증 → 정규화 → 보호소·동물 UPSERT → 이미지·태그 갱신 → sync_runs 종료 기록을 수행한다.
원격 DB와 production 환경은 CLI에서 거부한다. 기존 Phase 3 migration을 사용하며 새 revision은 없다.

| 검증 | 결과 |
| --- | --- |
| `ruff check .` | 통과 |
| 전체 `pytest backend/tests -q` | 282 passed, 0 skipped, 기존 라이브러리 deprecation 경고 2개 |
| 합성 1,001건 최초 실행 | 신규 1,001 / 갱신 0; batch 크기 500 |
| 동일 합성 capture 재실행 | 신규 0 / 갱신 1,001; 동물 UUID·총 행 수 동일 |
| 실제 API: 2026-09-14 하루 | totalCount·수신·고유·정규화·신규 모두 315 |
| 실제 API 요청 | 데이터 1페이지 + 빈 종료 1페이지, 2회; 재시도 0 |
| 실제 capture 오프라인 재실행 | 신규 0 / 갱신 315; API 요청 0; UUID·총 행 수 동일 |
| 실제 실행 실패·거절·중복 | 모두 0; 두 sync_runs 모두 success·종료 시각 기록 |
| 기존 profiling raw·수동 검토 CSV | 이전 SHA-256과 일치 |

실제 표본은 개 177 / 고양이 133 / 기타 5건이다. 저장된 보호소 122, 이미지 630,
태그 사전 17, 동물 태그 735행이다. 이 하루의 조회 결과를 전체 모집단이나 전체 기간의 수치로 해석하지 않는다.

합성 최초/반복 sync는 각각 약 2.45/2.77초, 실제 최초/반복 sync는 약 2.05/0.89초였다.
CLI 시작과 replay 사전 검사는 `total_seconds`에 포함되지 않는다. 이 값은 로컬 검증 관측값이며 운영 성능 보장이 아니다.

## 로컬 실행

프로젝트 `.env` 또는 환경변수에 DB URL과 기존 API 키를 설정한다. 값은 로그·채팅에 붙이지 않는다.
DB 이름은 `furbebe_dev` 또는 `furbebe_test`로 시작하고 host는 `localhost`, `127.0.0.1`, `::1`이어야 한다.
`APP_ENV=production`과 연결 대상을 덮어쓰는 URL query의 host/hostaddr/port/dbname/service/servicefile은 거부한다.
TLS 관련 query는 사용할 수 있다.

```powershell
# 지정한 로컬 개발 DB에 최초 1회 schema 적용
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head

# 명시한 날짜 범위만 새로 수집. page limit에는 빈 종료 페이지도 포함한다.
.\.venv\Scripts\python.exe -m backend.jobs.animal_sync.main --begin-date 2026-09-14 --end-date 2026-09-14 --batch-size 500 --max-pages 10

# 실제 앞선 실행의 output_directory 아래 pages.jsonl 사용
.\.venv\Scripts\python.exe -m backend.jobs.animal_sync.main --replay .local/sync/<run-directory>/pages.jsonl --batch-size 500 --max-pages 10
```

성공은 exit 0, 수집·검증·DB 실패는 exit 2다. 시작 시 schema를 자동 생성하지 않는다.
운영 앱의 `.env`와 별도로 이 검증의 접속 설정은 `.local/phase4a/` 아래에 보관했다.
로컬 테스트 DB와 실제 API를 적재한 로컬 개발 DB는 서로 다르다.

DB 통합 테스트에는 비어 있는 전용 disposable DB를 `FURBEBE_TEST_DATABASE_URL`로 지정한다.
이름은 `furbebe_test`로 시작해야 한다. 전체 suite에는 빈 public schema의 migration 왕복 검증이 있으므로
실데이터가 있는 개발 DB를 테스트 DB로 지정하지 않는다.

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

## 저장·갱신 정책

- `(source, source_id)`로 UPSERT하며 ID·created_at·first_seen_at을 보존한다.
- raw_payload는 source object를 보존한다. 인증정보 echo는 기존 client에서 제거한다.
- 체중은 Decimal, 출생연도는 정수다. 0kg는 보존하며 없는 값으로 대체하지 않는다.
- 텍스트 placeholder·파싱 실패는 정규화 필드에서 NULL, 원문은 raw_payload에 남긴다.
- source 수정 시각의 timezone이 명시된 경우 UTC로 저장한다. timezone을 추측하지 않는다.
- 보호소는 careRegNo로 식별한다. 없으면 가짜 보호소를 만들지 않는다.
- 같은 batch에서 같은 보호소는 source ID 정렬상 첫 비어 있지 않은 값을 선택한다.
  이후 batch의 비어 있지 않은 값은 기존 값을 갱신한다. 이 정책은 연락처의 최신성을 보증하지 않는다.
- 같은 동물의 이미지 URL은 중복 제거한다. source 소유 이미지의 변경·삭제만 반영하고 수동 이미지 소유권을 보존한다.
- FACT는 체중·출생연도·전체 필드가 일치하는 색상이며 VIBE는 명시적인 FACT 대응이다.
  개의 체중·나이 그룹만 생성하고 색상 FACT는 다른 종에도 적용한다. 행동·건강 원문으로 TRAIT를 만들지 않는다.
- 태그는 generator=`rules`, version=`1.0`, evidence·rule_id를 기록한다.
  해당 generator/version/지원 key 범위만 갱신하고 수동 태그·다른 버전은 보존한다.
- `updated_count`는 관측한 기존 행 수이며 값이 달라진 행만 세는 수치가 아니다.
  더 오래된 명시적 source 시각을 가진 행은 사실을 덮어쓰지 않고 관측 시각만 갱신하며 stale_count에도 기록한다.

## 실패 처리와 재실행

- PostgreSQL source 단위 advisory lock으로 동시 sync를 막는다.
- batch별 동물·이미지·태그·누적 삽입/갱신 counter를 같은 transaction에서 commit한다.
  실패한 batch는 rollback하며 이전에 commit한 batch는 보존하고 partial 상태를 기록한다.
- serialization failure와 deadlock만 최대 2회 재시도한다. commit 여부가 불명확한 연결 오류는 자동 재시도하지 않는다.
- totalCount 변화, 비정상 페이지 크기, 부족한 데이터, 고유 수 불일치, page limit을 성공으로 처리하지 않는다.
  0건 응답도 보수적으로 실패 처리한다. 실패·누락만으로 기존 animal을 삭제하거나 일괄 inactive 처리하지 않는다.
- page의 source 검증 거절 비율이 10%를 넘으면 해당 page를 적재하지 않는다.
  의미 있는 체중/나이 입력 20개 이상에서 파싱 실패가 50%를 넘는 경우도 중단한다.
  소수 거절은 유효한 행을 저장한 뒤 전체 실행을 failed로 기록한다.
- live capture는 `.local/sync/<directory>/pages.jsonl`, SHA-256, report.json으로 남긴다.
  replay는 파일 경로·checksum·요청 metadata·모든 페이지·빈 종료 페이지·추가 데이터 여부를 DB 연결 전에 검사한다.
  불완전한 live capture는 replay할 수 없으며 날짜 범위로 새 실행을 해야 한다.
- capture checksum은 파일을 통째로 메모리에 올리지 않고 계산한다. pagination의 고유 ID 집합은 수집량에 비례한다.

## 이번에 수정한 문제

1. 통합 테스트 종료 시 schema 이름 길이를 46으로 검사했지만 실제 길이는 45여서 18개 테스트의 정리가 실패했다.
   이제 해당 fixture가 생성한 token과 일치하는 schema만 정리하며 setup 실패 때도 engine을 닫는다.
2. replay 생성 시 파일 형태·page size·날짜 범위·완전성을 검사하고 실패한 생성자의 파일 handle을 닫는다.
   잘린 capture가 DB에 일부 적재된 뒤 실패하는 동작을 방지했다.
3. 실제 NUL·잘못된 Unicode 문자열을 개별 행 검증에서 거절한다.
   문자 그대로의 `\u0000` 텍스트를 NUL로 잘못 판정하던 동작을 수정했다.
4. 로컬처럼 보이는 DB URL의 query로 실제 연결 대상을 바꾸는 설정을 거부한다.

## 알려진 한계와 후속 범위

실제 315건 모두 source 수정 시각에 timezone이 없어 `source_updated_at=NULL`이다.
체중 4건은 `6.6.(Kg)`, `1,8(Kg)`, `0,91(Kg)`, `1,0(Kg)` 형식이라 숫자로 추정하지 않고 NULL로 두었다.
원문은 보존하며 두 경우 모두 normalization_issues에 집계한다.

이 실행은 선택한 기간의 현재 응답 snapshot이다. API가 snapshot isolation을 보장하지 않으므로
같은 totalCount 안의 동시 수정까지 검출했다고 주장하지 않는다.
프로세스 강제 종료나 DB 전체 단절로 최종 기록을 못 하면 sync_runs가 running으로 남을 수 있다.
규칙 사전은 현재 tagger Python 모듈에 있으며 외부 규칙 파일화·스케줄링·원격 운영은 후속 작업이다.
읽기 API는 이후 단계이고 `/health`만 제공한다. Docker build/run 검증도 deployment 단계에 남아 있다.

로컬 증거: `.local/phase4a/pytest.xml`, `verification.json`, `live-verification.json`, CLI 로그와 `.local/sync/` capture.
raw·접속정보·단건 데이터는 Git 제외 경로에만 보관한다.
