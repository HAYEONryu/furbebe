# Phase 0 Repository Audit

- 점검일: 2026-09-14, Asia/Seoul.
- 대상: `C:\Users\tec\Desktop\vscode\FURBEBE`.
- 이번 실행 범위: **Phase 0 현황 점검과 이 감사 문서 갱신만 수행**.
- 기존 Phase 1 코드, 보고서, 로컬 데이터는 보존했다. 이번에 수집·재분석·참조 코드 조회를 실행하지 않았다.
- 코드·설정·의존성·Git index를 수정하지 않았다. 이 문서 외 파일의 변경 여부를 해시로 확인했다.
- 기존 문서의 과거 실행 기록과 이번 점검 결과를 구분한다. 과거의 테스트 통과나 데이터 수집 기록은 이번 실행의 검증 결과가 아니다.

## 1. 적용 문서와 승인 범위

읽은 문서:

1. 현재 채팅의 직접 지시와 명시적으로 확정한 결정.
2. `C:\Users\tec\Downloads\FURBEBE_CODEX_PHASE0_1_DATA_PROFILING_SPEC.md`.
3. `C:\Users\tec\Downloads\FURBEBE_FASTAPI_V1_CONTRACT.md`.
4. `C:\Users\tec\Downloads\CODEX_FURBEBE_DEVELOPMENT_INSTRUCTIONS.md`.
5. 저장소의 `Agent.md`.

상위 경로와 저장소에서 적용할 `AGENTS.md`는 발견되지 않았다. 사용자가 지정한 `Agent.md`를 별도로 읽었다.

- HTTP endpoint/request/response/validation: FastAPI v1 Contract가 기준이다.
- Phase 0–1 profiling 방법과 blocker: profiling spec이 기준이다.
- 기술 스택·전체 아키텍처·금지사항: 개발 지시서가 기준이다.
- 이후 채팅에서 명시적으로 확정한 결정이 위 기준보다 우선한다.
- 첨부 문서 안의 실행 지시는 이번 요청의 Phase 0 제한을 확대하는 승인으로 해석하지 않는다.
- **Phase 1은 사용자의 새 승인 전까지 시작하거나 재개하지 않는다.**

## 2. 현재 Repository 구조

다음은 일반 소스 파일과 주요 로컬 디렉터리를 포함한 구조다. Git 관리 파일과 무시된 로컬 파일을 별도로 확인했다.

```text
FURBEBE/
├─ Agent.md
├─ README.md
├─ .env                         # 로컬, Git 제외
├─ .env.example
├─ .gitignore
├─ pyproject.toml
├─ backend/
│  ├─ __init__.py
│  ├─ requirements.txt
│  ├─ requirements-dev.txt
│  ├─ requirements-lock.txt
│  ├─ jobs/
│  │  ├─ __init__.py
│  │  └─ animal_sync/
│  │     ├─ __init__.py
│  │     ├─ client.py
│  │     ├─ source_models.py
│  │     ├─ profiling.py
│  │     ├─ field_stats.py
│  │     ├─ metrics.py
│  │     ├─ evidence.py
│  │     ├─ observations.py
│  │     ├─ reports.py
│  │     ├─ reference_cache.py
│  │     ├─ references.py
│  │     ├─ region_evidence.py
│  │     └─ status_policy.py
│  └─ tests/
│     ├─ fixtures/openapi_sample.json
│     ├─ test_profiling.py
│     ├─ test_regressions.py
│     ├─ test_review_protection.py
│     ├─ test_observed_formats.py
│     ├─ test_reference_policy.py
│     └─ test_reference_regressions.py
├─ docs/
│  ├─ phase0-repo-audit.md
│  ├─ api-data-profile.md
│  ├─ api-field-dictionary.md
│  ├─ api-profiling-decisions.md
│  └─ api-reference-data-profile.md
├─ .local/                      # Git 제외, 기존 수집 자료·테스트 임시 자료
│  └─ profiling/
├─ .venv/                       # Git 제외
├─ .pytest_cache/               # Git 제외
├─ .ruff_cache/                 # Git 제외
└─ .git/
```

- `frontend/`, `backend/app/`, DB 모델·마이그레이션, 배포 설정은 없다.
- `backend/`에는 Python 파일 21개, 합성 JSON fixture 1개, requirements 파일 3개가 있다.
- 기존 `.local/profiling/`에는 266개 파일, 46,018,869 bytes가 있다. 파일 목록·크기·메타데이터와 secret 후보만 확인했다.
- `.local/`에는 과거 테스트 임시 디렉터리도 있다. 이번에 정리하거나 삭제하지 않았다.
- 기존 프런트엔드나 API 애플리케이션을 새로 생성할 필요가 있는 단계로 판단하지 않았다.

## 3. Git 연결·branch·commit·working tree

| 항목 | 이번 확인 결과 |
| --- | --- |
| 현재 branch | `feat/phase0-1-profiling` |
| branch upstream | 설정 없음 |
| origin | `https://github.com/HAYEONryu/furbebe.git` |
| HEAD | `a8b9a3b5cdb63de38d29aac076dbb0a7a5d3d8e6` |
| 최근 commit | `Initial commit`, 2026-09-11 15:55:34 +09:00 |
| 최근 이력 수 | `git log -5`에 commit 1개 |
| HEAD에 포함된 파일 | `Agent.md` 1개 |
| 원격 직접 조회 | `git ls-remote --heads origin` 성공; `main`이 같은 commit을 가리킴 |
| Git index | 32개 경로: 기존 `Agent.md`와 신규 stage 파일 31개 |
| 작업 상태 | 신규 stage 31개 중 12개는 추가 수정(`AM`), untracked 3개 |
| 줄바꿈 설정 | `core.autocrlf=true`; `.gitattributes` 없음 |

`AM` 파일: `README.md`, animal_sync의 `client.py`, `metrics.py`, `profiling.py`, `reference_cache.py`, `references.py`, `reports.py`, `status_policy.py`, `backend/tests/test_reference_policy.py`, `docs/api-data-profile.md`, `docs/api-profiling-decisions.md`, 이 감사 문서.

기존 untracked 파일:

- `backend/jobs/animal_sync/region_evidence.py`
- `backend/tests/test_reference_regressions.py`
- `docs/api-reference-data-profile.md`

### 발견한 문제: stage된 코드 묶음의 불일치

Git index의 `backend/jobs/animal_sync/references.py` 177행은 `write_reference_report`를 `.reports`에서 가져온다. 그러나 **Git index의 `reports.py`에는 이 함수가 없다**. 현재 작업 폴더의 `reports.py`에는 있다.

이것은 index와 작업 폴더를 각각 읽고 AST로 함수 존재를 비교하여 확인한 정적 결함이다. 현재 stage 상태만 commit하면 참조 보고서 작성 경로에서 `ImportError`가 발생할 것으로 예상된다. 실제 CLI를 실행하여 재현하지는 않았다.

또한 현재 작업 폴더의 `references.py`가 사용하는 `region_evidence.py`는 untracked다. 기존 코드 전체를 검토한 뒤 일관된 Git 기준본을 구성해야 한다. **이번에는 add/reset/commit/push로 상태를 변경하지 않았다.**

원격 연결은 정상이나, 현재 구현은 원격 `main`에 없다. 원격에서 clone한 상태만으로 현재 로컬 profiling 작업을 재현할 수 없다. branch upstream 부재는 협업 설정 사항이며 로컬 Python 실행 자체의 blocker는 아니다.

## 4. 현재 기술·환경·설정

| 항목 | 확인 결과 |
| --- | --- |
| Node.js | `v24.18.0` |
| npm | `12.0.2` |
| 시스템 Python | `3.14.6` |
| 프로젝트 `.venv` Python | `3.14.6` |
| Python 요구사항 | 지침의 `3.12+` 충족 |
| 프로젝트 의존성 검사 | `pip check`: No broken requirements found |
| 실행 버전 고정 | `.python-version`, `.nvmrc`, `.node-version` 없음 |
| Docker / Wrangler CLI | 현재 PATH에서 발견되지 않음 |

주요 설치 패키지와 requirements가 일치한다: `httpx==0.28.1`, `pydantic==2.13.4`, `python-dotenv==1.2.3`, `pytest==9.1.1`, `ruff==0.16.7`. 전체 의존성 고정 목록은 `backend/requirements-lock.txt`에 19개 항목으로 존재한다.

`pyproject.toml`은 pytest 경로와 Ruff 설정만 포함한다. Ruff의 `target-version="py312"`는 lint 기준이며 실행 Python을 3.12로 고정하는 설정이 아니다. 정확한 Python 버전이나 `requires-python` 프로젝트 메타데이터는 없다.

| 파일·설정 | 존재 여부 / 의미 |
| --- | --- |
| `package.json`, npm/yarn/pnpm/bun lock | 없음 |
| `backend/requirements.txt` | 있음: profiling 런타임 의존성 |
| `backend/requirements-dev.txt` | 있음: pytest/Ruff |
| `backend/requirements-lock.txt` | 있음: 설치 의존성 버전 목록 |
| `pyproject.toml` | 있음: pytest/Ruff |
| `.env`, `.env.example`, `.gitignore` | 있음 |
| Dockerfile, Compose 설정 | 없음 |
| `wrangler.toml` / `wrangler.json*` | 없음 |
| Vite / React Router 설정 | 없음 |
| Alembic 설정·migration | 없음 |
| `.github/workflows/` | 로컬·HEAD·index 모두 없음 |

FastAPI, SQLAlchemy, Alembic, PostgreSQL 드라이버는 프로젝트 가상환경에서 확인되지 않았다. 현재 독립 profiling job 단계에서는 이 부재를 아키텍처 충돌이나 실행 blocker로 보지 않는다. 설치 또는 framework scaffold를 하지 않았다.

### GitHub Actions

저장소의 GitHub Actions workflows API를 읽기 전용으로 조회했고, `total_count=0`을 확인했다. 즉 현재 원격에도 등록된 workflow가 없다. GitHub Secrets 값, 조직·저장소 관리 설정, branch protection은 확인하지 않았다.

이 Git/GitHub 조회는 저장소 감사에 한정된다. 국가동물보호정보 OpenAPI는 호출하지 않았다.

## 5. 기존 구현 상태와 이번 검증의 한계

현재는 빈 저장소가 아니다. 로컬 작업 폴더에 다음 구현이 이미 있다.

- 인증·응답 처리·재시도를 담당하는 OpenAPI client와 원본 응답 모델.
- 수집 CLI, offline replay, 필드 통계, 관찰 결과, 보고서 생성.
- ID, 날짜, 나이, 체중, 이미지, 보호소, 지역, 상태, 설명, 건강, 입양 홍보 관련 분석 코드.
- 행동·건강·행정 텍스트를 별도 후보로 측정하는 코드와 수동 검토 표본 처리.
- 품종·시도·시군구·보호소 참조 코드 조회 및 로컬 JSON cache.
- 원본 상태와 별도 표시 상태를 유지하는 10일 경과 정책.
- 6개 테스트 모듈과 합성 응답 fixture.

정적으로 확인한 보호 장치에는 local 출력 경로 제한, Git 제외 여부 확인, credential redaction, HTTPS 요청, redirect 제한이 있다. 참조 자료는 `.local/profiling/reference-data/`의 기존 cache를 재사용하는 구조다. cache는 Phase 1 로컬 조사 자료이며 운영 PostgreSQL이나 Redis를 대체하는 구현이 아니다.

**이번 검증:** Python 파일 21개를 `ast.parse`로 읽어 구문 오류가 없음을 확인했다. 정적 함수 정의 기준 테스트 함수는 70개다. 이는 pytest parameterization을 포함한 실행 건수나 테스트 통과를 의미하지 않는다.

**이번에 하지 않은 검증:** pytest, Ruff 실행, profiling CLI 실행, offline replay, 수동 데이터 판독, 이미지 접근 확인, cache 네트워크 차단 테스트, API key 유효성 확인. 기존 문서의 108/138개 테스트 통과 기록은 과거 기록으로만 남는다.

### 이미 존재하는 수집 이력

기존 `.local/profiling/20260913T230733485043Z/run.json`과 저장된 summary에는 2026-09-14 08:07–08:11 KST의 수집 이력이 있다. 저장된 값은 성공 36페이지, raw 36,000건, unique 35,999건, 종료 사유 `target_reached`다.

이 수치는 **기존 파일에서 읽은 기록**이며 이번에 호출·재계산하거나 모집단 전수 수집을 확인한 결과가 아니다. 이전 부분 실행의 `superseded.json`도 보존되어 있다. 기존 보고서에 적힌 Phase 1 완료 여부를 이번 Phase 0 감사로 재승인하지 않는다.

## 6. 문서와 충돌하거나 주의할 부분

전체 구조인 **React / React Router Framework / Vite / JavaScript / Tailwind → FastAPI → SQLAlchemy → PostgreSQL(초기 Supabase)**과 충돌하는 신규 스택 사용은 발견하지 못했다. frontend DB 직접 접근, MySQL, Redux, Redis, 운영 AI 태깅 구현도 확인되지 않았다. 아직 없는 framework·Docker·배포·cron은 이후 단계의 미구현 항목이다.

이미 사용자가 해소한 문서 차이와 남아 있는 표현 차이는 다음과 같다.

| 항목 | 문서 차이 / 현재 기준 |
| --- | --- |
| similar 개수 | 개발 지시서의 4개는 UI 기본 노출 수. Contract와 채팅 결정에 따라 기본 4, 최소 1, 최대 12 |
| 목록 query | `sido`, `sigungu`, `size_group` 사용. `region`, `size` alias 추가 금지 |
| 지역 코드 | 채팅 결정에 따라 `sido → upr_cd`, `sigungu → org_cd`. raw display fallback만으로 정규화 성공 판정 금지 |
| 지역 명칭 예시 | Contract에는 이름 기반 예시가 남아 있다. 코드 기반 조회 결정과 예시의 표현을 향후 문서에서 정합화해야 한다. 이를 근거로 response JSON shape를 임의 변경하지 않는다 |
| 상태 표시 | 문서의 원본 표시 원칙보다 최신 채팅의 10일 정책이 우선. 원본 `processState=보호중`이고 한국 날짜 기준 `today-noticeSdt >= 10`이면 표시를 `입양 가능`으로 설정. 현재 helper는 원본을 별도로 유지 |
| 표본 하한 | 원칙 5,000 unique 이상. 실제 전체 모집단이 5,000 미만이고 totalCount 및 끝까지의 pagination으로 전수 수집을 입증한 경우만 예외 |
| 짧은 행동 문구 | spec의 행동 후보 예시 `순함/경계`와 길이 2 이하 무의미 후보 조건이 겹친다. 현재 코드가 두 flag를 각각 기록한다. 최종 성격 태그의 채택 기준은 아직 결정된 것으로 취급하지 않는다 |

10일 표시 정책은 사용자가 정한 서비스 표시 규칙이다. 이를 별도 보호소 확인이나 공식적인 입양 확정 상태로 해석하지 않는다. 날짜가 누락·잘못되었거나 미래인 경우에는 기존 코드가 issue를 남기는 구조이며, 이번에 실데이터에 재적용하지 않았다.

profiling 결과로 launch 전 조정할 수 있는 범위는 **size_group thresholds, age_group thresholds, region normalization, processState UI semantics, animals_active definition**의 5개다. 이 중 지역 코드와 상태 표시 방향은 채팅으로 결정됐지만 실제 데이터 정규화 품질과 예외는 이후 검증 대상이다. 크기·나이 threshold와 `animals_active` 정의는 이 감사에서 확정하지 않는다.

새로운 전체 아키텍처 충돌은 발견하지 못했다. 위 표현 차이와 겹치는 후보 규칙은 보고만 하며 다른 문서나 코드를 수정하지 않았다.

## 7. Secret / 보안 위험

**Secret 값·일부 문자열·인증 URL은 출력하거나 이 문서에 기록하지 않았다.**

| 확인 항목 | 결과 |
| --- | --- |
| 루트 `.env` | 존재; `DATA_GO_KR_SERVICE_KEY` 설정 여부만 확인, 값 비출력 |
| `.env.example` | 같은 변수의 값은 비어 있음 |
| 프로세스·사용자·시스템 환경 변수 | 점검한 API/DB/Supabase/OpenAI 변수는 없음; 프로젝트 키는 `.env`에 있음 |
| `.env` Git 제외 | `.gitignore` 규칙에 의해 제외 |
| `.local/` Git 제외 | `.gitignore` 규칙에 의해 제외 |
| HEAD / index의 `.env`, `.local/` | 추적 파일 없음 |
| 공개 대상 파일·index·도달 가능한 이력 | 현재 설정 credential의 원문/인코딩/디코딩 형태 일치 없음 |
| PEM private key, Supabase secret/JWT, 인증정보 포함 PostgreSQL URL 후보 | 검사한 공개 대상 파일·index·도달 가능한 이력에서 발견 없음 |
| 원격 URL | credential 포함 userinfo/query 없음 |

변수 이름 기준 점검 대상: `DATA_GO_KR_SERVICE_KEY`, `DATABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_SECRET_KEY`, `SUPABASE_ANON_KEY`, `SUPABASE_PUBLISHABLE_KEY`, `OPENAI_API_KEY`.

현재 credential의 일치 검사는 공개 대상 파일 35개, 기존 local profiling 파일 266개, index 파일 32개, 도달 가능한 commit의 파일 1개에 대해 수행했다. 값은 내부 비교에만 사용했다. 일반 후보 탐색은 공개 대상 파일·index·해당 이력에서 수행했다. 이는 이미 회전된 미지의 secret이나 외부 유출이 전혀 없다는 증명이 아니다.

**조치 필요:** 앞선 사용자 메시지의 IDE 선택 영역에 실제 API key가 포함된 이력이 있다. 현재 파일 내용과 관계없이 채팅 노출 이력이 있으며, 재발급 완료 여부는 확인되지 않았다. 다음 실제 API 호출 전 재발급하고 로컬 `.env`만 갱신하는 것을 권고한다. 이번에는 키를 교체하거나 외부로 검증 요청을 보내지 않았다.

raw 자료에는 원천 데이터의 연락처 등 정보가 포함될 수 있다. `.gitignore`는 Git 추가 방지 장치이며 암호화나 외부 공유 차단 장치가 아니다. 전체 raw dump와 행 단위 검토 자료는 계속 `.local/profiling/`에만 보관해야 한다.

## 8. Phase 1 준비 상태와 Blocker

| 구분 | 판정 / 필요한 후속 조치 |
| --- | --- |
| Phase 0 감사 | 완료. 발견 사항을 기록했으며 임의 수정하지 않음 |
| 로컬 환경 | Python·의존성·키 파일·Git 제외 규칙 존재. 환경 자체의 명확한 실행 blocker는 발견하지 못함 |
| 승인 경계 | **사용자의 새 Phase 1 승인이 필요함.** 이번 요청으로 수집·재분석을 시작할 수 없음 |
| Git 기준본 재현성 | **문제 있음.** stage된 함수 의존성 불일치와 필요한 untracked 파일을 정리해야 현재 작업 폴더를 일관된 commit으로 재현 가능 |
| credential 안전성 | 과거 채팅 노출 이력. 재발급 여부 확인 및 필요 시 재발급 권고 |
| 실제 API 사용 가능 여부 | 이번에 미확인. 키 파일 존재만으로 인증·쿼터·응답 스키마를 보장할 수 없음 |
| 코드 실행 신뢰성 | 구문·의존성 확인만 완료. 현재 working tree의 mock 테스트·lint는 승인 후 재검증 대상 |
| 향후 데이터 blocker | ID/응답 shape/축종/지역/상태/critical parser/5,000 unique 조건을 실제 실행에서 다시 판정해야 함 |
| 참고 사항 | upstream, 버전 고정, CI 부재는 이후 재현성 개선 항목. 현재 독립 profiling의 직접적인 환경 blocker로 보지 않음 |

안전한 시작 조건이 모두 재확인됐다고 판정하지 않는다. 특히 **현재 index를 그대로 commit 가능한 상태로 보지 않는다.** 이 문제를 수정하는 작업과 Phase 1 재개는 이번 감사에 포함하지 않았다.

## 9. Phase 1 생성·수정 예정 파일

아래는 승인 후 재사용·검토·필요 시 수정할 범위를 확정한 목록이다. 현재 이미 존재하는 파일을 신규 scaffold 대상으로 오인하지 않는다. 목록에 있다는 이유만으로 모든 파일을 반드시 수정하는 것은 아니다.

| 범위 | 기존 파일 / 예정 처리 |
| --- | --- |
| client·수집·원본 모델 | `backend/jobs/animal_sync/client.py`, `source_models.py`, `profiling.py`: 현재 구현 검증 및 필요한 결함 수정 |
| profiling 통계·evidence | 같은 디렉터리의 `field_stats.py`, `metrics.py`, `evidence.py`, `observations.py`: 지정 metrics·후보 구분·검토 표본 검증 |
| 참조 코드·상태 | 같은 디렉터리의 `reference_cache.py`, `references.py`, `region_evidence.py`, `status_policy.py`: cache 재사용·미등록 코드 조회·최신 결정 검증 |
| 보고서 생성 | 같은 디렉터리의 `reports.py`: index와 working tree의 불일치를 함께 검토 |
| 테스트 | `backend/tests/test_profiling.py`, `test_regressions.py`, `test_review_protection.py`, `test_observed_formats.py`, `test_reference_policy.py`, `test_reference_regressions.py` 및 `fixtures/openapi_sample.json` |
| 필수 문서 | `docs/api-data-profile.md`, `docs/api-field-dictionary.md`, `docs/api-profiling-decisions.md`: 승인된 실행 근거로 갱신 |
| 참조 코드 문서 | `docs/api-reference-data-profile.md`: 지역·품종·보호소 조회 및 cache 근거 갱신 |
| 사용법·의존성 | `README.md`, `.env.example`, `pyproject.toml`, `backend/requirements.txt`, `requirements-dev.txt`, `requirements-lock.txt`: 실제 변경이 필요할 때만 갱신 |
| 그대로 유지할 기본 파일 | `Agent.md`, 기존 `__init__.py` 파일, 현재 목적에 맞는 `.gitignore` |
| 사용자 관리 secret | 루트 `.env`: 사용자가 재발급 키를 입력하는 위치. Git 추가 금지 |

승인 후 새 실행에서 생성할 수 있는 **로컬 전용 파일**:

- `.local/profiling/<new-run-id>/` 아래 raw 응답 JSONL, `run.json`, summary JSON, field 통계 CSV, manual-review CSV, 필요 시 `reference-profile.json`.
- `.local/profiling/reference-data/`의 cache 및 미등록 조회 응답. 이미 저장된 코드는 우선 재사용한다.
- 전체 raw와 행 단위 자료는 Git commit 대상이 아니다. 이번에는 새 실행 디렉터리도 생성하지 않았다.

`region_evidence.py`, `test_reference_regressions.py`, `api-reference-data-profile.md`는 이미 있는 untracked 파일이다. 새로 만들어야 하는 파일이 아니라 이후 변경 검토에 포함해야 하는 파일이다.

**Phase 1 예정 범위 밖:** frontend scaffold, FastAPI endpoint, `backend/app/`, DB 모델·마이그레이션·UPSERT, 운영 태거, Docker/Wrangler/배포 workflow 신규 구현.

## 10. 이번 변경 파일과 실행한 명령

변경 파일은 **`docs/phase0-repo-audit.md` 1개**다. 기존 감사 문서를 현재 상태로 갱신했다. 구현 파일, 설정, secret 파일, 기존 raw 자료 및 Git stage 내용은 보존했다.

실행한 주요 명령과 읽기 작업:

```text
rg --files --hidden
rg -n <구조·정책·import 관련 패턴> <명시한 소스·문서>
Get-Content / Python UTF-8 read: Agent.md, 첨부 3문서, 소스·설정·기존 보고서
git rev-parse --show-toplevel
git branch / git status --short
git log -5 --format="%h %ad %s" --date=iso-strict
git ls-remote --heads origin
git ls-tree -r --name-only HEAD
git ls-files / git ls-files --stage -z
git diff --stat / git diff --cached --stat
git show :backend/jobs/animal_sync/references.py
git show :backend/jobs/animal_sync/reports.py
git check-ignore -v <.env/.local/.venv/cache 대상>
git config 관련 설정 조회
node --version
npm --version
python --version
py -0p
Get-Command node,npm,python,py,docker,wrangler
.venv/Scripts/python.exe --version
.venv/Scripts/python.exe -m pip list --format=json
.venv/Scripts/python.exe -m pip check
Python 읽기 전용 스크립트: 전체 파일 목록·크기, AST, secret 후보 검사
GitHub GET /repos/HAYEONryu/furbebe/actions/workflows
apply_patch: docs/phase0-repo-audit.md만 갱신
Python SHA-256 비교: 감사 문서 외 파일 및 Git stage 내용 유지 확인
```

secret 검사 스크립트는 설정 여부·일치 여부·안전한 파일 경로만 출력했다. 위 목록은 긴 읽기 스크립트의 목적을 요약하며 실제 credential을 포함한 명령은 실행하지 않았다.

실행하지 않은 작업: 패키지 설치·업데이트, 테스트·lint, profiling/replay/reference CLI, 국가동물보호정보 OpenAPI 호출, `git add/reset/commit/push`, 기존 파일 삭제, framework 생성.

## 11. 다음 권장 단계

1. 이 감사 결과를 검토하고, Git 기준본 불일치의 수정 범위를 승인 후 작업에 포함한다.
2. 이전 채팅에 노출된 API key의 재발급 여부를 확인하고, 필요하면 사용자 로컬 `.env`에 새 키를 입력한다.
3. 사용자가 Phase 1 재개를 명시적으로 승인하면 기존 코드를 기준으로 mock 테스트·lint·cache 보호를 먼저 확인한다.
4. 이후 승인 범위에서 필요한 실제 수집·프로파일링을 수행하고 blocker와 수집 근거를 보고한다. HTTP endpoint와 JSON shape는 이번에 변경하지 않는다.

**여기서 멈춘다. Phase 1은 시작하지 않았다.**
