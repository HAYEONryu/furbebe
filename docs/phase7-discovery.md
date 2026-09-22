# Phase 7 — Main Page + Dogs Listing

Phase 6 승인 후 **발견 → 관심** 범위를 구현했다. 데이터 소스는 Phase 5 FastAPI v1이고,
React/Workers loader → FastAPI → PostgreSQL 경계를 유지한다.
사용자는 `/dogs`에서 기존 API의 개·고양이·기타 구조동물을 함께 표시하기로 선택했다.
Detail 최종 구현·Auth·Redux·Supabase client·TRAIT 규칙 추가·Phase 8·실제 배포는 포함하지 않았다.

## Main

Header → Hero → Quick Discovery → 최근 등록된 친구들 → More CTA → Footer 순서다.
요청한 슬로건과 `Find Your Forever`를 적용했다. 작은 기존 wordmark와 Ivory/Butter 중심 색상,
소량의 Peach accent를 사용한다. Hero의 대표 동물과 카드 사진은 loader가 받은 실제 API 데이터다.
stock 사진·합성 동물·허구의 동물 이름이나 건강·성격 정보는 주입하지 않는다.

Main loader는 최근 등록순 6건, meta/filters, 활성 tags를 병렬 요청한다.
Quick Discovery는 API의 지역·크기·나이 및 VIBE/FACT 태그로 목록 URL을 만든다.
크기·나이의 미상 옵션은 Quick Discovery에서 제외하고 상세 필터에서는 제공한다.
최근 등록 데이터가 없으면 빈 상태를, API 실패 시 공통 오류와 재시도를 제공한다.

## Dogs Listing / Filter

페이지 제목·전체 결과 수·검색·빠른 태그·필터·정렬·AnimalGrid·Pagination을 구현했다.
`/api/v1/animals`, `/api/v1/meta/filters`, `/api/v1/tags`를 공통 service에서 호출한다.
목록은 페이지당 24건이고 전체 건수·페이지 수·이전/다음 여부는 API pagination을 사용한다.
기존 결과를 유지하면서 navigation 상태를 알리고 조건 입력을 잠시 비활성화해 연속 요청의 혼선을 막는다.
고정 위치의 loading 알림과 이미지 비율 예약으로 재조회 시 레이아웃 변화량을 줄인다. 반복 animation은 없다.
실제 DEV의 metadata 응답이 cold 상태에서 11.55초까지 관측되어, 이 aggregate 요청만 20초의
제한을 사용한다. 일반 요청의 10초 timeout과 navigation 취소는 유지한다.

필터 drawer는 native `dialog`를 사용한다. 모바일에서는 bottom sheet, 데스크톱에서는 중앙 dialog다.
필터는 초안을 편집한 뒤 적용하며, 적용 없이 닫으면 URL과 결과를 변경하지 않는다.
시도 변경 시 시군구를 초기화한다. 전체 초기화와 개별 조건 해제도 제공한다.
태그는 여러 개 선택할 수 있고 기본 any, 선택적으로 all 조건을 사용한다.
태그 표시는 기존 FACT/VIBE에 근거하며 새로운 TRAIT 추론은 하지 않는다.

## URL state

공통 `discovery-query.js`에서 파싱·직렬화·변경 규칙을 관리한다.

```text
/dogs?sido=6110000&size_group=tiny&tag=bean&sort=weight_asc&page=2
```

지원 조건: sido, sigungu, breed, sex, neutered, size_group, age_group, tag,
process_state, q, sort, page. 기존 API의 tag_match도 유지한다.
지역에는 label 대신 API의 공식 코드를 쓴다. 반복 `tag`는 중복을 제거하고 한글·특수문자를 인코딩한다.
잘못된 페이지 값과 지원하지 않는 sort는 기본값으로 해석한다.
기본값 recent/page 1은 생성 URL에서 생략한다. 필터·검색·정렬 변경은 page 1로 reset하고
페이지 이동은 나머지 조건을 보존한다. 브라우저 history와 새로고침은 URL로부터 화면을 복원한다.

## AnimalCard / Favorite / Missing data

카드는 API 이미지, 관심 버튼, 품종, 출생연도(또는 원문 나이), 체중, 지역, 상태와 최대 3개 태그를 표시한다.
VIBE를 먼저 표시한다. 이미지는 lazy load하고 Hero만 우선 로드한다.
primary_image가 null이거나 로드에 실패하면 자체 ImageEmptyState로 대체한다.
체중이 null이면 원문 수치를 추정하지 않고 `체중 미상`을 표시한다.
나이·지역·상태의 미상도 표시하며, tags가 비어 있으면 태그 영역을 만들지 않는다.

관심 버튼은 카드 link 안에 중첩하지 않고 형제 button으로 둔다.
Phase 6의 `furbebe:favorites` service/hook을 재사용하며, 클릭은 상세 이동을 발생시키지 않는다.
Main·List·기본 Detail이 같은 저장소를 사용한다. 저장이 차단되면 방문 중 메모리로 동작하고 안내한다.

## Responsive / Accessibility

- 작은 휴대폰에서는 큰 사진의 1열 카드, 너비에 따라 2/3/4열 목록. Main의 데스크톱 최근 목록은 3열.
- 모바일 빠른 태그는 가로 스크롤로 탐색하며 filter sheet 내부만 스크롤한다.
- 주요 버튼·페이지 링크는 44px 이상의 touch target. 폼 label, 이미지 alt, semantic headings와 landmarks.
- 카드 link와 favorite에 별도 키보드 접근, favorite aria-label/aria-pressed, pagination aria-current.
- dialog의 제목 연결, 초기 focus, Tab/Shift+Tab 순환, Escape·닫기 버튼, 닫은 뒤 trigger로 focus 복귀.
- route 이동 후 main focus, reduced-motion 설정과 visible focus 유지.

native dialog 동작은 [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/dialog)을 참고했다.
jsdom은 dialog top layer를 구현하지 않아 unit test에는 최소 showModal/close stub을 사용하고,
실제 포커스·Escape·모바일 배치는 Playwright CLI 브라우저에서 별도로 확인한다.

## 필요한 API 호환 확장

기존 meta는 지역 코드만 반환해 사용자가 지역 이름으로 선택할 수 없었다.
`RegionFilterResponse`에 `sido_label`과 `sigungu_labels`를 추가하고 ReadService가
기존 공식 지역 catalog에서 이름을 제공하도록 했다. 기존 코드 필드·query·SQL·DB schema는 유지한다.
세종의 동일 시도/시군구 코드와 null 시군구 이름도 처리한다.
이 확장에 대한 HTTP 회귀 테스트를 추가했다. [API contract](api-contract.md)에 응답을 문서화했다.

## Tests / Build

검증 기간: 2026-09-21~22. Node.js 24.18.0 / npm 12.0.2 / Windows.

- `npm test`: Vitest + RTL **7 files / 64 passed**.
- Main render/실제 loader 연결, 카드 표시, missing image/weight, favorite와 카드 이동 분리.
- 전체 query 파싱·직렬화·한글 인코딩·잘못된 페이지·시도 변경·페이지 reset.
- URL history back/forward 복원, API pagination, 미적용 filter 초안 폐기, 빈 결과, API 오류·재시도.
- Phase 6의 transport/timeout/cancel/redirect/favorite 저장 실패·탭 동기화/공통 상태 테스트도 포함한다.
- Backend `pytest backend/tests/test_read_api.py -q`: **36 passed**, 기존 dependency deprecation 경고 2개.
- 프런트엔드 ESLint와 변경 backend의 Ruff 통과.
- client + Workers SSR production 빌드 통과. production 기본 API는 `https://api.furbebe.com`.
- 최종 산출물로 `npm --prefix frontend run check:worker` 통과. Workers dry-run만 실행했으며 배포하지 않았다.
- client/SSR 산출물 19개를 검사해 비공개 환경변수 값과 테스트용 Supabase secret sentinel 노출 0건을 확인했다.
  production API 주소가 포함되고 local API 주소는 포함되지 않는 것도 확인했다.

Backend 전체 DB 통합 suite는 이번에 재실행하지 않았으며 위 수치를 Phase 5의 전체 테스트와 합산하지 않는다.

## 실제 API smoke test

로컬 Workers frontend와 local FastAPI를 기존 DEV PostgreSQL에 연결한다.
frontend는 DB에 접근하지 않고 API만 호출한다. 수집·migration·도메인 데이터 쓰기는 실행하지 않는다.
검증용 스크린샷과 결과는 Git 제외 경로 `output/playwright/phase7-*`에 둔다.

실제 데이터 검사 **12개 통과**. 아래 건수는 검증 시점의 값이며 고정 fixture가 아니다.

| 검사 | 결과 |
| --- | --- |
| metadata 지역 이름 | 16개 시도와 반환된 시군구의 이름 제공 |
| Main | HTTP 200, 최근 6건 |
| 목록 첫 페이지 / 둘째 페이지 | 각각 HTTP 200, 24건, 전체 7,290건 |
| 서울 + tiny | HTTP 200, 전체 292건 |
| 세종 시도 + 시군구 | HTTP 200, 전체 32건 |
| bean 태그 + 체중 오름차순 | HTTP 200, 전체 2,377건 |
| female + 중성화 yes + puppy | HTTP 200, 12건 |
| 일치하지 않는 검색어 | HTTP 200, 빈 결과 |
| 범위를 벗어난 page 999999 | HTTP 200, 빈 결과, 전체 건수 유지 |
| 잘못된 sex | HTTP 422 오류 화면 |
| 잘못된 상세 UUID | HTTP 404 기본 오류 화면 |

Main과 정상 목록 응답에서 API items의 ID 집합과 SSR 카드 링크를 대조해 일치함을 확인했다.
브라우저에서도 API 이미지 로드, 페이지 이동 시 필터 유지, 뒤로가기·앞으로가기,
검색 시 page reset과 새로고침 후 검색어/정렬 복원을 확인했다.
favorite 클릭은 현재 URL을 유지하며 reload 후에도 저장 상태를 복원했다.
모바일 필터 적용, Tab/Shift+Tab 순환, Escape 닫기와 trigger focus 복귀를 확인했다.
Main은 320/390/1440px에서 가로 overflow가 없고, 목록은 320/390px과 데스크톱 배치를 확인했다.
320px에서는 body 최소 너비와 검색 grid의 최소 열 너비를 수정해 가로 overflow를 제거했다.
390px 필터 sheet도 시각 검토했다.
최종 Main 브라우저 console에는 React DevTools 안내 외 오류가 없었다.

스크린샷: [Main 데스크톱](../output/playwright/phase7-main-desktop.png),
[Main 모바일](../output/playwright/phase7-main-mobile.png),
[목록 데스크톱](../output/playwright/phase7-list-desktop.png),
[목록 모바일](../output/playwright/phase7-list-mobile.png),
[필터 모바일](../output/playwright/phase7-filter-mobile.png).
상세 검사 결과는 `phase7-api-smoke.json`, 번들 검사는 `phase7-bundle-audit.json`에 있다.

## 미해결 / Phase 8 readiness

- 사용자 결정대로 전체 구조동물 목록이다. 개 전용 필터는 이번 범위가 아니다.
- 기존 [Phase 5 재검토](phase5-review.md)의 DEV dotenv 일반 설정 누락·자정 경계 캐시 결함 2건은 유지된다.
- 운영 Cloudflare/API 도메인 배포 및 production 이미지 전송 환경은 이번 검증 범위가 아니다.
  원천 이미지가 접근 불가능하면 placeholder를 표시한다.
- 지역명을 제공하려면 이번 metadata label 호환 확장이 포함된 FastAPI를 사용해야 한다.
  이전 API와 연결해도 동작하며 그 경우 이름 대신 지역 코드가 표시된다.
- DEV metadata의 cold 응답 지연은 남아 있다. 운영 부하·초기 응답 성능은 후속 환경에서 측정해야 한다.
- Detail은 Phase 6의 기본 화면이며 Phase 8 승인 전 최종 상세 구현을 시작하지 않는다.

## 변경 파일

Phase 7에서 변경한 파일만 나열한다. 기존 Phase 5/6 미커밋 변경은 보존했다.

- `frontend/app/routes/home.jsx`, `frontend/app/routes/dogs.jsx`
- `frontend/app/components/animal-card.jsx`, `discovery-filters.jsx`, `quick-discovery.jsx`, `pagination.jsx`
- `frontend/app/components/animal-image.jsx`, `favorite-button.jsx`, `site-layout.jsx`
- `frontend/app/services/discovery.js`, `discovery-query.js`, `validation.js`
- `frontend/app/services/api.js`, `meta.js`, `frontend/tests/api.test.js`
- `frontend/app/styles/app.css`
- `frontend/tests/animal-card.test.jsx`, `discovery-query.test.js`, `routes.test.jsx`, `fixtures.js`, `setup.js`
- `backend/app/schemas/animals.py`, `backend/app/services/animals.py`, `backend/tests/test_read_api.py`
- `README.md`, `docs/architecture.md`, `docs/api-contract.md`, `docs/phase7-discovery.md`

패키지 의존성 추가·TypeScript 전환·루트 `.env` 변경은 없다. **Phase 8 승인 대기.**
