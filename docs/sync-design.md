# 원천 수집 설계와 실행

진입점: python -m backend.jobs.animal_sync.main.
수집은 schema를 만들지 않습니다. 먼저 대상 DB의 Alembic current=head를 확인합니다.
연결 자격증명은 [환경 설정](environment.md), 자동 실행은 [Actions 설정](../deploy/sync-environments.md)을 따릅니다.

## 대상과 명령

| --database-target | 설정 | 제약 |
| --- | --- | --- |
| local | 일반 DATABASE_URL | development/test, loopback, furbebe_dev* 또는 furbebe_test* |
| supabase-dev | DATABASE_URL_dev + SUPABASE_URL_dev | APP_ENV development |
| supabase-prod | DATABASE_URL_prod + PROD project metadata | APP_ENV production; replay 금지 |

최근 범위 개발 수집:

```sh
APP_ENV=development backend/.venv/bin/python -m backend.jobs.animal_sync.main --database-target supabase-dev --begin-date 2026-10-01 --end-date 2026-10-05 --max-animals 1000
```

위 날짜는 입력 형식 예제입니다. 실제 수집할 범위로 변경합니다.
max-animals는 저장 대상 개 수가 아니라 **원천 totalCount 제한**입니다.
total이 제한을 넘으면 동물 쓰기 전에 실패합니다. 앞 1000건만 잘라 저장하지 않습니다.
실행 기록인 sync_runs는 이미 생성되었을 수 있습니다.

전체 기본 범위 운영 수집:

```sh
APP_ENV=production backend/.venv/bin/python -m backend.jobs.animal_sync.main --database-target supabase-prod --full --page-size 1000 --batch-size 500
```

이 명령은 실제 운영 데이터를 갱신합니다. 운영 target과 쓰기 범위를 확인한 후 사용합니다.
--full은 날짜 파라미터 없이 API 기본 날짜 범위의 모든 페이지를 요청합니다. 과거 전체 이력이 아닙니다.

## 옵션

| 옵션 | 기본·유효 범위 |
| --- | --- |
| --begin-date / --end-date | YYYY-MM-DD; 둘 다 필요, 시작 ≤ 종료 |
| --full | 날짜·max-animals와 동시 사용 불가 |
| --page-size | 1000; 1~1000 |
| --batch-size | 500; 500~1000 |
| --max-pages | 10000; 빈 종료 페이지도 포함할 여유 필요 |
| --max-animals | 선택적 양의 정수; total 제한 |
| --replay | .local/sync 내부 pages.jsonl; 날짜·full 동시 사용 불가 |

CLI target 기본은 local입니다. API용 FURBEBE_DATABASE_TARGET만 설정해도 수집 CLI target이 바뀌지 않습니다.

## 수신과 완전성

공식 HTTPS abandonmentPublic_v2를 사용하고 JSON을 요청합니다.
응답 shape·header success·totalCount·pageNo·numOfRows를 검사합니다.
배열/단일 object/정상 빈 items를 구분합니다. redirect를 따라가거나 TLS 검증을 해제하지 않습니다.

총건수·페이지 크기가 도중에 변하거나 중간 페이지가 누락되면 실패합니다.
동일 ID의 다른 payload, 반복 페이지, max-pages 도달을 정상 완료로 기록하지 않습니다.
수신 raw 수뿐 아니라 고유 원천 ID 수=totalCount와 **마지막 빈 페이지**를 확인합니다.
totalCount=0은 현재 pagination에서 정상 빈 성공으로 처리하지 않고 ABNORMAL_TOTAL_OR_PAGE로 실패합니다.

HTTP timeout/429/일부 5xx와 재시도 가능 원천 코드만 최대 3회 재시도합니다.
기본 요청 간격은 1초, 재시도 대기는 1/2/4초입니다.
serviceKey와 인증정보는 capture에서 제거하고 인증 URL·원천 오류 body를 로그에 출력하지 않습니다.

## 정규화와 저장 정책

- 필드 타입과 원천 ID를 엄격하게 검증합니다. 문자열 ID를 숫자로 강제 변환하지 않습니다.
- 알려지지 않은 추가 필드는 raw_payload에 보존합니다.
- NUL·잘못된 UTF-8·NaN/Infinity JSON은 거부합니다.
- 체중·출생연도 파싱 실패는 null과 품질 이슈로 기록합니다.
- 종 code/name 충돌은 species=null로 표시하고 수집 대상에서 제외합니다.
- 신규 저장은 개 + 원천 상태 보호중/입양 가능입니다.
- 기존 동물이 종료·비대상으로 바뀌면 원문을 갱신하고 is_active=false로 보존합니다.
- 더 오래된 timezone-aware source_updated_at payload는 내용을 덮어쓰지 않습니다.

페이지 내 거부율이 10%를 넘거나, 유의미한 체중/나이 표본 20건 이상에서 파싱 실패가 50%를 넘으면 중단합니다.
소수 item 거부가 있어도 실행 최종 status는 failed/ROWS_REJECTED입니다. 오류를 성공으로 숨기지 않습니다.

(source, source_id) UPSERT는 UUID·first_seen_at·created_at을 보존합니다.
동일 내용이면 unchanged로 집계하고 last_seen_at만 갱신합니다.
보호소 null 입력은 기존 값을 비우지 않습니다.
사진은 popfile1~8의 유효 URL을 중복 제거해 원천 순서대로 처리합니다.
빠진 원천 이미지와 자동 태그는 비활성화합니다. 독립 소유 이미지·별도 생성기는 일반 수집에서 유지합니다.

기간 밖·미수신 동물을 일괄 비활성화하지 않습니다.
장기 미관측 자료가 남을 수 있으므로 기간 범위와 source 상태 확인을 운영자가 판단합니다.

## transaction과 lock

session advisory lock (1179996738, 1)은 실행 전체를 보호합니다.
동시에 다른 협력 수집기가 실행 중이면 SYNC_ALREADY_RUNNING으로 종료합니다.
batch transaction은 도메인 변경과 sync_runs 신규/갱신 counter를 함께 commit합니다.
직렬화 실패 40001·deadlock 40P01만 최대 3번 transaction 재시도합니다.
네트워크 단절이나 commit 결과가 불확실한 오류를 임의 재시도하지 않습니다.

session lock 때문에 Supabase session pooler 5432 또는 검증된 direct 접속을 사용합니다.
완료 기록은 별도 연결로 작성할 수 있으므로 pool 1 + overflow 1을 사용합니다.
뒤에서 실패해도 앞 batch는 유지됩니다. report와 sync_runs를 같이 확인하고 동일 범위를 안전하게 다시 수집합니다.

## 보고서와 counter

.local/sync/<capture-id>/에 pages.jsonl, pages.sha256, report.json을 남깁니다.
capture-id 디렉터리 이름과 DB sync_id는 서로 다릅니다.
원문 설명이 포함될 수 있어 capture를 공개 artifact로 올리지 않습니다.

| counter | 의미 |
| --- | --- |
| pagination.fetched_count | 수신 raw 행; 제외 동물 포함 |
| pagination.unique_count | 페이지에서 본 사용 가능한 고유 원천 ID |
| normalized_count | 검증·정규화한 고유 item; 저장 비대상 포함 |
| rejected_count | item validation 거부 |
| duplicate_count | 동일 ID+동일 snapshot 중복 |
| inserted_count | 신규 저장 대상 동물 |
| updated_count | 내용 변경; 기존 비대상 전환 변경도 포함 |
| unchanged_count | 내용이 같은 현재 대상 동물 |
| stale_count | 기존보다 오래된 원천 시각으로 내용 갱신하지 않은 동물 |
| excluded_count | 현재 저장 대상이 아닌 item; 기존 비활성 전환 포함 |
| deleted_count | 정상 수집은 0 |
| error_count / error_code | 거부·실패와 안전한 코드 |
| run_persisted | sync_runs 기록 생성 여부 |

sync_runs에는 핵심 counter만 보관합니다. 상세 unchanged/excluded·품질 이슈·재시도는 report.json을 봅니다.
정상 종료 code=0, 실패/설정 오류 code=2입니다. 강제 종료로 running 기록이 남을 수도 있습니다.
최종 상태가 success여도 raw total과 저장 동물 수가 같을 필요는 없습니다.

## 개발 replay와 별도 정리 도구

```sh
APP_ENV=development backend/.venv/bin/python -m backend.jobs.animal_sync.main --database-target local --replay .local/sync/CAPTURE_ID/pages.jsonl
```

replay는 checksum·request 조건·pagination 완전성을 **쓰기 전에** 확인합니다. 네트워크를 호출하지 않습니다.
PROD replay는 거부합니다.

prune_animals는 정상 수집 경로가 아닙니다. --apply 없는 실행으로 후보만 점검합니다.

```sh
APP_ENV=development backend/.venv/bin/python -m backend.jobs.prune_animals --target supabase-dev
```

--apply는 비대상 동물을 물리 삭제하고 FK cascade로 자식도 삭제합니다.
운영 보존 정책에는 이 apply 경로를 사용하지 않습니다.
태그 전면 재생성의 삭제 범위는 [태그 안내](tag-generation.md)를 확인합니다.
