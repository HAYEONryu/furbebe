# Phase 8.5 재개 점검 — 2026-09-29

점검 기준은 현재 HEAD `e393ef3` (`phase8.5`, 2026-09-23)이다. 재개 시 작업 트리는 깨끗했다.

## 기준 확인

앞선 대화의 첨부 파일 `FURBEBE_tag_generation_logic.txt` 이후에 저장소 규칙이 변경되어 있다.
[현재 규칙](tag-generation.md)과 [Phase 8.5 완료 보고](phase8-5-behavior.md)는
건강 태그를 생성하지 않고 행동 TRAIT 5종/6개 규칙만 활성화한 상태를 기록한다.
첨부 파일의 건강양호/케어필요, 넓은 행동 태그 목록, 표시명과 차이가 있다.

재개 중 사용자에게 적용 기준을 확인 요청했다. 이번 점검은 현재 Phase 8.5 구현을 기준으로
진행하며, 과거 첨부 규칙으로의 재변경이나 Phase 9 착수는 수행하지 않는다.
이는 첨부 파일과 현재 구현이 완전히 일치한다는 보고가 아니다.

## 검증

- Backend 일반 검사: 497 passed, PostgreSQL 미설정으로 134 skipped.
- Backend Ruff: 통과.
- Frontend: 92 passed, 9개 파일.
- Frontend ESLint: 통과.
- Vite client/SSR production build: 통과.
- Cloudflare Workers `wrangler deploy --dry-run`: 통과. 배포 없음.

프런트엔드 최초 병렬 실행에서 필터 적용 후 화면 전환을 기다리는 테스트 1개가 시간 초과로
실패했다. 해당 파일 11개 테스트를 단독 재실행하고 전체 92개 테스트를 재실행한 결과
모두 통과했다. 실행 부하에 따른 일시적 시간 초과로 추정하며, 앱 코드나 테스트 조건을
완화하지 않았다.

- PostgreSQL을 포함한 Backend 전체 검사: **631 passed, 0 skipped**, 181.49초.
  localhost 전용 새 임시 PostgreSQL 클러스터와 `furbebe_test_recheck_20260929` DB를
  사용했다. 테스트 후 직접 시작한 서버를 종료했다.
- 기존 FastAPI/Starlette 테스트 의존성의 deprecation 경고 2건은 남아 있다.
- DEV 읽기 전용 `behavior_retag --database-target supabase-dev` 조회는 수 분 동안
  결과를 반환하지 않아 해당 조회 프로세스만 종료했다. 이번 DEV 데이터 재검증은
  **미완료**이며 원인은 확정하지 않았다. `--apply`/`--verify`는 실행하지 않았다.
  9월 23일 완료 보고의 DEV 반영 건수를 이번에 다시 확인한 값으로 취급하지 않는다.

## 변경 범위

이번 재개에서는 제품 코드, 태그 규칙, 사람 검토 CSV, 운영/DEV DB를 수정하지 않았다.
검증 결과를 이 문서에 기록하고, 로컬 검증 도구를 git 제외 경로
`.local/recheck-20260929/`에 보관한다.
