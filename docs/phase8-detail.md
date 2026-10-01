# Phase 8 — Dog Detail Page

Phase 7 승인 후 `/dogs/:animalId`를 구현했다. 사용자가 선택한 전체 구조동물 범위를 유지하며,
사진 → 기본정보 → 설명 → 보호소 → 연결 순서로 읽을 수 있다. 검증일은 2026-09-22다.

## Detail / Data

- 공통 Header/Footer 안에 Gallery, Summary, Tags, 기본·발견 정보, 원문 설명, 행동·건강,
  보호소, 조건부 입양 홍보, Favorite/Share, 문의 CTA, Similar를 배치했다.
- service에서 `GET /api/v1/animals/{id}`와 `GET /api/v1/animals/{id}/similar?limit=4`만 병렬 호출한다.
  Detail은 meta·tags·list endpoint를 추가 조회하지 않는다.
- 기존 공통 API layer의 origin·HTTP 오류·JSON·취소·timeout 처리를 사용한다.
  frontend에서 DB/Supabase에 접근하지 않는다. Backend·schema·수집·TRAIT 규칙 변경은 없다.
- 상세 API 실패와 404는 공통 route error를 사용한다. invalid UUID는 API 호출 전 404로 처리한다.
  유사 동물만 실패하면 상세는 유지하며 해당 영역에 실패 안내와 재시도를 제공한다.

## Gallery

API `images`의 source 사진을 order 순서로 정렬하고 같은 URL은 중복 제거한다.
primary/secondary를 썸네일 button으로 선택하며 현재 사진은 aria-pressed와 사진 수로 알린다.
Tab/Enter/Space 외에 좌우 방향키·Home/End를 지원하고, 자동 재생·carousel 의존성은 없다.
동물 ID가 바뀌면 사진 선택과 공유 상태를 초기화한다.

대표 사진은 `object-contain`과 4:3 예약 영역으로 전체 이미지를 표시한다. 사진 없음·잘못된 URL·
로드 실패는 기존 FURBEBE ImageEmptyState를 사용한다. 홍보 이미지는 별도 홍보 영역에서 원본 비율로 표시한다.
Main/List의 기본 image crop 동작은 유지한다. Stock image는 사용하지 않는다.

## Summary / Tags / Evidence

품종·성별·중성화·출생연도/원문 나이·API 나이 그룹·체중·크기 그룹·털색·상태·지역을 표시한다.
측정값과 그룹을 새로 계산하지 않는다. enum은 기존 API 계약에 맞는 한글 문구로 표시하며,
나이 그룹이 추정 범위이고 크기 그룹이 체중 기반 탐색 기준임을 안내한다.
없는 기본 정보는 `정보 없음`으로 표시한다.

FACT/VIBE 및 응답에 이미 있는 TRAIT를 표시한다. 등록된 tag evidence는 접을 수 있는 원문 영역에 둔다.
confidence는 사용자 화면에 확률로 표시하지 않으며 새로운 태그를 생성하지 않는다.

- 설명: `special_mark`, `etc`.
- 행동·건강: `social`, `health`, `vaccination`, `health_check`.
- null·빈 문자열·공백만 있는 값은 숨긴다. 섹션의 값이 모두 비면 제목까지 숨긴다.
- 줄바꿈과 원문 내용을 유지하며 HTML로 해석하지 않는다.
- 건강·성격·긴급성·안락사 예정 등을 원문 없이 추론하지 않는다.

## Shelter / Adoption Promotion

보호소 이름·전화·주소·관할 기관을 표시한다. 유효한 전화번호는 문의 CTA의 `tel:` 링크로 연결한다.
전화가 없으면 전화 링크를 만들지 않고 안내한다. 형식이 전화 링크에 적합하지 않은 원문은 표시하되
임의로 번호를 추정하지 않는다. 보호소 자체가 null인 경우도 자연스럽게 안내한다.

`adoption_promotion`이 있을 때만 입양 홍보 영역을 만든다. title, start/end dates,
condition_text, description, image_url을 존재하는 필드만 원문대로 표시한다.
기간이 지났다는 이유로 임의의 상태 문구나 입양 가능 여부를 만들지 않는다.

## Favorite / Share

Phase 6의 FavoriteButton·useFavorites·favoritesStore와 `furbebe:favorites`를 그대로 사용한다.
새 저장소 구현이나 UI의 localStorage 직접 조작은 없다.

사용자가 공유 버튼을 누르면 Web Share API를 우선 사용한다. 미지원 또는 일반 실패는 URL 복사,
clipboard 거부·미지원은 focus된 읽기 전용 URL 입력창으로 수동 복사를 제공한다.
공유를 취소하면 자동으로 복사하지 않는다. 공유 URL은 현재 origin의 `/dogs/{id}`이며 query/hash는 제외한다.
기기 공유 메뉴 동작과 clipboard 제한은 [MDN share](https://developer.mozilla.org/en-US/docs/Web/API/Navigator/share),
[MDN writeText](https://developer.mozilla.org/en-US/docs/Web/API/Clipboard/writeText)를 확인했다.

## Similar / SEO readiness

기존 AnimalGrid/AnimalCard를 재사용하고 limit=4를 요청한다. 본인 ID·중복 ID를 방어적으로 제외하고
최대 4건만 표시한다. source_animal_id가 다르면 잘못 연결된 추천으로 보고 실패 상태를 표시한다.
정상 빈 응답과 조회 실패는 구분한다. 재시도는 route loader를 재검증한다.

loader는 사실 기반 `seo: { title, description, path }`를 제공한다.
현재 React Router 8의 `meta({ loaderData })`를 사용하며 실제 SSR HTML에서 title/description을 검증했다.
없는 품종·지역·보호 상태를 만들지 않는다. 전체 canonical/OG/structured data/sitemap 정책은 후속 Phase 범위다.

## Responsive / Accessibility

모바일은 사진 먼저 1열, 데스크톱은 사진/요약과 기본/발견 정보를 2열로 배치한다.
긴 주소·설명은 줄바꿈하고 섹션은 내용에 맞춰 늘어난다. 과도한 animation이나 고정 overlay는 없다.
semantic article/section/headings/dl, 사진 alt, thumbnail aria-pressed/controls, 공유 live status,
focus-visible과 44px 이상 주요 touch target을 사용한다.

## Tests / Lint / Build

프런트엔드 Vitest + React Testing Library: **9 files / 89 passed**.
Phase 6/7 테스트를 포함하며 Phase 8에서 25개를 추가했다.

검증: detail 성공·두 endpoint 제한·invalid ID·404·API 실패/재시도·누락 이미지·여러 사진·
사진 로드 오류 복구·재조회 시 선택 사진 제거·동물 이동 시 사진 reset·null/공백 설명·건강 원문·기존 TRAIT와 confidence 비노출·
보호소 없음/전화 없음·홍보 필드·favorite 복원·share 복사/수동 fallback·native 성공/취소·
similar 본인/중복 제외·최대 4건·빈 응답/실패 구분·잘못된 JSON 구조를 확인한다.

빌드·브라우저와 병렬 실행한 회차에서 기존 Main 테스트 2개가 RTL 대기시간을 초과했다.
서버와 브라우저를 종료한 후 동일한 기본 `npm test`로 89개 모두 통과했다.
테스트 timeout이나 판정 조건은 완화하지 않았다.

최종 `npm run lint`와 client + Workers SSR `npm run build`가 통과했다.
`npm --prefix frontend run check:worker`도 통과했으며 실제 배포는 하지 않았다.
Workers dry-run 산출물은 829.52 KiB / gzip 175.90 KiB이며 새 binding은 없다.
최종 빌드 파일 19개를 검사해 비공개 환경변수·Supabase 설정값·테스트 secret sentinel 노출 0건을 확인했다.
production API 주소는 `https://api.furbebe.com`이고 local API 주소는 산출물에 없다.
검사 결과는 `output/playwright/phase8-bundle-audit.json`에 기록했다.
Backend 코드는 이번 Phase에서 변경하지 않아 기존 DB 통합 suite를 재실행하지 않았다.

## 실제 DEV / Browser smoke

로컬 FastAPI를 기존 DEV PostgreSQL에 연결하고 Workers 개발 서버에서 실제 응답으로 확인했다.
조회만 수행하며 migration·수집·도메인 데이터 쓰기는 실행하지 않았다.

- 기존 Phase 7 검증에 사용한 ID 6건을 detail endpoint로 확인: 각 source 사진 2장, 실제 설명·보호소 전화 존재.
- 그중 3건에서 API와 SSR 화면을 대조: 사진 URL, 설명 원문, 유사 동물 ID 4건, 전화 링크, SEO description 일치.
- null인 행동·건강·홍보 섹션이 실제 SSR 화면에서 숨겨짐을 확인.
- invalid UUID 및 존재하지 않는 UUID가 각각 HTTP 404와 공통 오류 화면을 반환.
- 결과: `output/playwright/phase8-api-smoke.json`의 5개 시나리오 통과.

Playwright CLI 실제 브라우저에서도 사진 1/2 선택, Home/End/방향키 focus 이동과 순환,
관심 저장 후 같은 URL 유지 및 reload 복원, 실제 clipboard URL 복사를 확인했다.
기기 공유는 테스트에서 비활성화하여 clipboard fallback을 검증했다.
320/390/768/1440px에서 가로 overflow가 없고 gallery/favorite/share/전화 CTA의 touch target이
44px 이상임을 확인했다. 사진 object-fit이 contain이고 title이 실제 품종·지역을 반영함도 확인했다.
전화 링크의 번호는 확인했으나 보호소로 실제 통화하지 않았다.

화면: [데스크톱](../output/playwright/phase8-detail-desktop.png),
[모바일](../output/playwright/phase8-detail-mobile.png).
브라우저 검증 스크립트는 Git 제외 경로 `output/playwright/phase8-browser-smoke.js`에 있다.
검증용 브라우저와 로컬 서버는 종료했다.

실제 샘플의 promotion/social/health/vaccination/health_check는 null이었다.
이 필드가 있는 경우, 사진 없음, 보호소 전화 없음은 synthetic unit fixture로 검증했다.

## 미해결 / Phase 8.5 / 9 Readiness

- 운영 Cloudflare 배포·production 이미지 전송·실제 기기의 OS 공유 메뉴는 별도 검증이 필요하다.
  native share는 단위 테스트로 검증하고, 브라우저에서는 clipboard fallback을 검증한다.
- 원천 API 사진에 HTTP URL이 있다. 운영 HTTPS에서 원천 사진 접근이 실패하면 placeholder를 표시한다.
  이번 Phase에 image proxy·변환 서비스는 추가하지 않았다.
- 기존 Phase 5의 DEV dotenv 설정 반영·자정 캐시 문제와 Phase 7의 cold metadata 응답 지연은 유지된다.
  Detail은 metadata endpoint를 호출하지 않는다.
- Phase 8.5 / 9는 승인 대기이며 시작하지 않았다. 실제 배포도 수행하지 않았다.

## 변경 파일

Phase 8 범위만 기록한다. 기존 Phase 5/6/7 미커밋 변경은 보존했다.

- `frontend/app/routes/dog-detail.jsx`
- `frontend/app/components/image-gallery.jsx` (신규), `share-button.jsx` (신규), `animal-image.jsx`
- `frontend/app/services/animal-detail.js` (신규), `share.js` (신규), `validation.js`
- `frontend/app/styles/detail.css` (신규), `app.css`
- `frontend/tests/detail.test.jsx` (신규), `share.test.js` (신규), `fixtures.js`, `routes.test.jsx`
- `README.md`, `docs/architecture.md`, `docs/phase8-detail.md` (신규)

새 패키지 추가·TypeScript 전환·Redux/Auth·Backend 수정·루트 `.env` 변경은 없다.
