# FURBEBE — Phase 0–1

현재 범위는 국가동물보호정보 OpenAPI 수집·품질 분석입니다.
FastAPI endpoint, DB schema/migration, UPSERT, frontend는 구현하지 않습니다.

## 현재 결과 — 2026-09-14

API 키 등록 및 인증을 확인했고 실데이터 수집·재분석을 실행했습니다.
고정 조회 기간은 2026-01-01~2026-09-13, totalCount는 60,174건입니다.
36페이지에서 raw 36,000건, 고유 동물 35,999건, 고유 개 20,471건을 확보했습니다.
동일 원문 중복은 1건이며 실패 페이지·충돌 중복은 없습니다.
개의 실제 발견일 범위는 2026-04-30~2026-09-13입니다. 목표 수에 도달해 수집을 종료했으므로
전체 기간의 전수 조사 또는 전체 동물 모집단으로 일반화하지 않습니다.

수집량 기준은 충족했습니다. 지역 코드는 `sido_v2.orgCd = upr_cd`,
`sigungu_v2.orgCd = org_cd`로 정규화하고, 원문 상태가 `보호중`인 자료는
공고 시작일로부터 현재 날짜까지 10일 이상이면 화면 상태를 `입양 가능`, 그 전이면
`보호중`으로 표시합니다. 원문 상태와 미매칭 지역은 보존합니다.
상세 내용은 [결정 문서](docs/api-profiling-decisions.md)를 확인합니다.
수동 검토용 표본 100건의 review_notes는 빈 칸입니다.

최신 검증에서 개 20,471건 모두 지역 코드 연결에 성공해 기존 지역·상태 blocker를 해소했습니다.
2026-09-14 기준 표시 상태는 `입양 가능` 5,991건, `보호중` 1,068건이며 종료 상태는 유지됩니다.
시도 16개, 시군구 조회 항목 252개, 품종 245개(개 206 / 고양이 38 / 기타 1),
보호소 코드 330개를 저장했습니다. 227개 관할별 보호소 목록을 포함한 조회 범위는 총 247개입니다.
전체 재실행 검증에서 캐시 247회를 재사용했으며 실제 API 호출은 0회였습니다.
현재 조회 목록에 없는 품종 코드 7개(개 1,022건)와 보호소 코드 15개(개 1,057건)는
원문을 보존하고 데이터 품질 항목으로 보고했습니다. 누락 원인이나 폐지 여부는 단정하지 않습니다.

현재 run을 API 호출 없이 다시 분석하는 명령:

```powershell
.\.venv\Scripts\python.exe -m backend.jobs.animal_sync.profiling --input .local/profiling/20260913T230733485043Z/raw-20260913T230733485043Z.jsonl
```

이 run은 수집·코드 연결 등 데이터 blocker가 있으면 exit code 2를 반환합니다.
size/age 경계와 animals_active 정의는 별도 launch 결정이며 Phase 2는 자동 시작하지 않습니다.
재분석 전에 사람이 입력한 검토 의견이 있다면 CSV를 별도로 보관합니다.

## API 키 입력

프로젝트 루트의 `.env` 파일을 열어 다음 항목의 오른쪽에 키를 입력하고 저장합니다.

```dotenv
DATA_GO_KR_SERVICE_KEY=
```

공공데이터포털에서 이 API의 활용 승인을 받은 키를 사용합니다.
일반 키와 percent-encoded 키 모두 지원합니다. 환경변수가 있으면 .env보다 우선합니다.
키를 채팅이나 명령행에 붙여넣지 않습니다. .env는 Git 제외 대상입니다.
새 checkout에는 `.env.example`을 `.env`로 복사합니다.

공식 서비스 안내: https://www.data.go.kr/data/15098931/openapi.do
필요한 요청 파라미터와 실제 계정 한도는 공식 상세 명세와 승인 정보를 확인합니다.

## 실행 환경

Python 3.12+; 현재 검증 환경은 Python 3.14.6 / Windows PowerShell입니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe -m backend.jobs.animal_sync.profiling --check-config
```

마지막 명령은 키 존재 여부만 출력하며 네트워크를 호출하지 않습니다.

## 테스트

```powershell
.\.venv\Scripts\python.exe -m ruff check backend
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

모든 unit test는 합성 fixture와 mock transport를 사용합니다.
합성 fixture 통계를 실제 API 조사 결과로 사용하지 않습니다.

## 실제 API 사전 확인

```powershell
.\.venv\Scripts\python.exe -m backend.jobs.animal_sync.profiling --probe
```

HTTPS만 사용합니다. Redirect, 인증 실패, HTTP/application 오류는 안전한 코드로 보고합니다.
HTTP로 자동 전환하거나 TLS 검증을 해제하지 않습니다.
실제 단건 응답은 .local/profiling 아래에만 저장합니다.

## 본 수집

아래는 이번 수집에 사용한 조건입니다. 다시 실행하면 새 API 수집이 시작됩니다.

```powershell
.\.venv\Scripts\python.exe -m backend.jobs.animal_sync.profiling --target-unique 20000 --min-unique 5000 --page-size 1000 --request-interval 1 --seed 20260911 --start-date 20260101 --end-date 20260913
```

목표는 unique 개 20,000건입니다. 전체 source 응답을 보존하고 `upKindNm=개`로
명확히 확인된 개의 주요 통계를 별도로 집계합니다. 분류가 모호한 자료는 보고합니다.
목표 전에 표본이 부족하면 더 넓은 기간으로 새 run을 실행합니다. 여러 run의 raw를
무작정 합쳐 표본 수를 늘리지 않습니다.

기본 최대 페이지는 2,000입니다. 종료 사유·요청/성공/실패·재시도·중복·totalCount를 기록합니다.
실패/변동/반복 페이지를 정상 완료로 숨기지 않습니다. 키를 포함한 URL을 출력하지 않습니다.
전체 응답 envelope는 JSONL의 한 행에 한 페이지씩 저장합니다.

5,000건 미만 예외는 실제 전체 모집단이 5,000 미만이고 전수 수집이 증명된 경우에만
사용합니다. `--entire-population-confirmed`는 공식 조회 범위가 실제 전체임을 확인한
경우에만 사용하며 날짜 제한과 함께 사용할 수 없습니다. API 기본 조회 기간을
모른다면 이 옵션을 사용하지 않습니다. 안정적인 totalCount와 마지막 빈 페이지,
raw/unique/duplicate 수를 함께 검증합니다.

## 로컬 결과와 재분석

공식 참조 코드를 조회하고 기존 동물 데이터와 연결합니다. 기본 실행은 완전 오프라인이며,
`--fetch-missing`을 붙인 경우에만 없는 조회 범위·코드를 가져옵니다.

```powershell
.\.venv\Scripts\python.exe -m backend.jobs.animal_sync.references --input .local/profiling/20260913T230733485043Z/raw-20260913T230733485043Z.jsonl --fetch-missing
```

캐시: `.local/profiling/reference-data/cache.json`.
시도 전체, 시도별 시군구, 축종별 품종, 시도·시군구별 보호소로 나눠 저장합니다.
이미 있는 코드는 재조회하지 않습니다. 조회했지만 없는 코드는 24시간 동안 반복 요청을 막습니다.
서로 다른 관할에서 같은 보호소를 이용할 수 있어 보호소 소속은 `(upr_cd, org_cd, careRegNo)`로 검증합니다.
실제 코드 목록에 같은 지역명이 여러 코드로 나오면 임의 선택하지 않고, 코드별 동물 조회의
ID와 원본 표본을 대조합니다. 이 추가 증거도 로컬에 저장해 재사용합니다.

참조 결과는 동물 run 안의 `reference-profile.json`과
[참조 코드 보고서](docs/api-reference-data-profile.md)에 기록됩니다.
이후 아래 profiling 재분석 명령을 실행하면 참조 결과를 포함해 기존 3개 보고서도 갱신합니다.
참조 결과의 run ID와 원본 checksum이 맞지 않으면 중단합니다.
상태 계산은 기본적으로 실행일의 한국 날짜를 사용합니다. 재현할 때는 references 명령에
`--as-of 2026-09-14`처럼 기준일을 고정합니다. 기존 profiling의 기준일은 원본 run 날짜를 유지합니다.

표시 상태는 매 계산일마다 `noticeSdt`로부터 경과 일수를 계산합니다. 9일은 `보호중`,
10일 이상은 `입양 가능`입니다. 원문이 다른 상태이면 유지하고, 날짜가 없거나 잘못되었거나
미래이면 입양 가능으로 변경하지 않습니다. 표시 상태를 영구 캐시해 날짜 변화가 누락되게 하지 않습니다.

`.local/profiling/<run-id>/`에 다음 파일을 생성합니다.

- raw-<run-id>.jsonl: 모든 원본 페이지. 인증정보 echo만 제거.
- run.json: 키 없는 요청 조건·실행 metadata·raw SHA-256.
- summary-<run-id>.json: 상세 집계.
- field-stats-<run-id>.csv: 전체 필드 사전.
- manual-review-<run-id>.csv: 비식별 처리한 검토 표본, review_notes는 빈 칸.

```powershell
.\.venv\Scripts\python.exe -m backend.jobs.animal_sync.profiling --input .local/profiling/<run-id>/raw-<run-id>.jsonl
```

재분석은 네트워크와 API 키가 필요 없습니다. 원본 checksum과 실행 기준일·seed를 사용합니다.
동일 run 재분석은 집계 및 검토 CSV를 다시 생성합니다. 사람이 입력한 review_notes가
존재하면 덮어쓰지 않고 중단합니다. 검토한 CSV를 별도 로컬 파일로 보관한 뒤 실행합니다.

공유 가능한 docs 보고서는 마지막 분석 결과로 갱신됩니다. 모든 행 단위 자료는
.local/profiling에만 둡니다. 이미지 네트워크 검사나 다운로드는 수행하지 않습니다.

## 결과 해석과 중단

exit code 0: 요청한 작업 성공. probe/config 성공은 Phase 1 완료를 의미하지 않습니다.
exit code 2: 키/수집/분석 blocker 또는 미확정 의사결정. 상세 사유를 확인합니다.

성격/건강/행정 키워드는 후보 지표이며 실제 태그나 진단이 아닙니다.
순함·경계 같은 짧은 단어는 short-text와 evidence 후보를 모두 기록합니다.
지역 코드는 공식 `sido_v2`/`sigungu_v2` 조회 결과로 정규화하며, 미매칭은 데이터 품질
결과로 남기고 연결 불가 항목은 blocker로 보고합니다. size/age 경계와 활성 동물 정의가
확정되기 전에는 Phase 2로 자동 진행하지 않습니다.

## 문서

- [Phase 0 감사](docs/phase0-repo-audit.md)
- [실데이터 분석](docs/api-data-profile.md)
- [필드 사전](docs/api-field-dictionary.md)
- [결정·보류 항목](docs/api-profiling-decisions.md)
- [공식 참조 코드·상태 정책](docs/api-reference-data-profile.md)

전체 아키텍처는 Frontend → FastAPI → SQLAlchemy → PostgreSQL을 유지합니다.
최신 사용자 결정은 Phase 0 감사 및 결정 문서에 기록되어 있습니다.
