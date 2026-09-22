# Phase 8 재점검 — 2026-09-22

작업 중단으로 파일이나 기능이 불완전해졌는지 현재 작업 폴더를 기준으로 재검증했다.
**이번 점검에서 새로운 동작 오류나 구현 누락은 재현되지 않았다. 추가 애플리케이션 코드 수정은 하지 않았다.**

## 파일 상태

- 점검 시작 시 HEAD: `fa5321e` (`phase8`).
- 마지막 커밋 이후 메타 태그의 `loaderData` 사용, 원본 이미지 비율, 갤러리 선택 범위,
  CTA 스타일과 회귀 테스트 등 후속 보완이 미커밋 상태로 보존되어 있었다.
- 해당 보완과 `docs/phase8-detail.md`를 포함한 현재 작업 폴더를 검사했다.
  HEAD 커밋만으로 같은 완료 상태가 된다는 의미는 아니다.
- 충돌 마커·미완성 placeholder·누락된 import/route 연결을 발견하지 않았다. `git diff --check` 통과.
- 기존 변경을 되돌리거나 커밋하지 않았다. `.env`와 Backend·DB는 변경하지 않았다.

## 재실행 결과

| 검사 | 결과 |
| --- | --- |
| `npm test` | 9 files / 89 passed, 18.95초. 이전 Main 대기시간 초과 재현되지 않음 |
| `npm run lint` | 통과 |
| `npm run build` | client + Workers SSR 통과 |
| `npm --prefix frontend run check:worker` | 통과, 실제 배포 없음 |
| 최종 빌드 환경변수 검사 | 파일 19개에서 비공개 설정값 노출 0건. production API 포함, local API 미포함 |
| 실제 DEV API와 SSR 비교 | 상세 3건 + invalid/nonexistent ID 404 2건, 총 5개 시나리오 통과 |
| 실제 브라우저 | 사진 선택·키보드 이동·관심 저장/reload·clipboard 복사·제목 검증 통과 |
| 화면 크기 | 320/390/768/1440px 가로 overflow 없음, 주요 버튼 44px 이상 |

테스트와 빌드를 순서대로 실행하고, 빌드 완료 후 개발 서버와 브라우저를 실행했다.
이번에는 개발 서버와 빌드를 동시에 실행하지 않았다.

## 상세 확인 범위

- 상세와 `similar?limit=4` 두 API만 사용하며, 잘못된 ID·HTTP 오류·잘못된 JSON은 공통 오류 경계에서 처리한다.
- 설명과 건강 정보는 실제 원문만 표시하고 null/공백 섹션은 숨긴다. 기존 태그를 표시하며 추가 추론은 없다.
- 실제 API 사진 URL, 원문 설명, 보호소 전화 링크, 유사 동물 4개 ID, SSR description이 화면과 일치했다.
- 404·누락 사진·사진 변경·누락 보호소/전화·홍보 정보·공유 실패/취소·유사 동물 실패는 기존 단위 테스트도 재통과했다.
- 갤러리 선택 clamp, `object-contain`, React Router 8 `meta({ loaderData })` 보완이 남아 있는 것을 확인했다.
- 브라우저 console에는 React DevTools 안내만 있으며 이번 검증 중 오류 로그는 없었다.

실행 근거는 Git 제외 경로의 `output/playwright/phase8-api-smoke.json`,
`phase8-browser-smoke.js`, `phase8-review-bundle.json`과 [완료 보고](phase8-detail.md)에 기록했다.

## 검증 한계

운영 HTTPS에서의 원천 이미지 접근, 실제 기기 OS 공유 메뉴, 전체 production 배포는 이번에도 검증하지 않았다.
기존 Phase 5 설정·자정 캐시 및 Phase 7 metadata cold 응답 문제는 이번 점검 범위에서 수정하지 않았다.
Phase 8.5 / 9는 시작하지 않았다.
