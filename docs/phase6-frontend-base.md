# Phase 6 — Frontend Base Architecture

사용자의 Phase 5 승인에 따라 프런트엔드 기반만 구현했다. Main/List/Detail은
라우팅과 데이터 연결을 검증하는 최소 화면이며 최종 디자인·제품 기능 완성을 의미하지 않는다.
Phase 7과 production 배포는 시작하지 않았다. 루트 `.env`, backend 코드, DB schema와 데이터는 변경하지 않았다.

## Frontend 구조

`frontend/`는 독립 npm package와 lockfile을 가진다. 루트 `package.json`은 실행 명령만 전달한다.
React 19.3, React Router Framework 8.4, Vite 8.3, Tailwind 4.3을 사용한다.
코드는 JavaScript/JSX이고 TypeScript 전환·Redux·추가 상태관리/validation framework는 없다.

```text
frontend/
  app/
    routes.js, root.jsx, entry.client.jsx, entry.server.jsx
    routes/                  home, dogs, dog-detail
    services/                api, animals, tags, meta, validation, route-loader, favorites
    hooks/                   use-favorites
    components/              공통 layout, 상태, 버튼, 태그, 이미지
    styles/app.css           Tailwind와 FURBEBE 토큰
  workers/app.js             Workers fetch handler
  public/favicon.svg        로컬 FURBEBE 자산
  tests/                    Vitest + React Testing Library
  vite.config.js, react-router.config.js, wrangler.jsonc
```

## Routes와 데이터 흐름

| 경로 | Phase 6 구현 |
| --- | --- |
| `/` | 정적 소개, 목록 이동 링크, API 없이 렌더링 |
| `/dogs` | URL query → loader → FastAPI 목록, 기본 검색 form과 텍스트 링크 |
| `/dogs/:animalId` | UUID 검사 → 상세 loader, API 사진/placeholder, 기본 태그·favorite |

React → React Router Workers loader → FastAPI `/api/v1` → PostgreSQL 경계를 유지한다.
첫 요청에는 SSR을 수행하고 브라우저 이동에도 Framework loader를 사용한다.
로그인·admin·application·donation 경로는 없다. URL query가 서버 데이터의 기준이고,
loader 결과 다음으로 component state, localStorage를 사용한다.

## API layer와 환경변수

- `api.js`: HTTP(S) origin 검사, URL query 인코딩, JSON parse, HTTP/네트워크/timeout 오류 정규화.
- GET 요청에 JSON Accept, credentials omit, 10초 timeout, navigation 취소 signal을 적용한다.
- Workers가 `redirect: error`를 지원하지 않으므로 `manual`로 요청하고 3xx/opaque redirect를 502로 정규화한다.
  다른 origin으로 자동 이동하지 않는다. Workers 실제 연결 검증에서 발견한 문제를 수정하고 회귀 테스트를 추가했다.
- 서버 오류 원문·SQL·입력값 대신 고정 사용자 메시지와 유효한 UUID 문의 번호만 전달한다.
- `animals.js`: 목록·상세·비슷한 동물, 지원 query allowlist, 유효하지 않은 ID의 로컬 404.
- `tags.js`: 태그 조회. `meta.js`: 필터 메타·개요 통계. Component에서 fetch를 반복하지 않는다.
- `validation.js`: UI가 사용하는 필수 구조만 검사하고 추가 backend 필드는 허용한다.
- FastAPI 요청과 SSR 문서에는 별도 캐시를 추가하지 않는다.

공개 build-time 변수는 `VITE_API_BASE_URL` 하나다. 기본값은 개발 `http://127.0.0.1:8080`,
production `https://api.furbebe.com`이며 Cloud Run 기본 URL은 없다.
Vite `envDir`는 frontend로 고정하고 `envPrefix: []`와 정확한 `define` allowlist를 사용한다.
다른 `VITE_*` 값도 자동 노출되지 않는다. `frontend/.env.example`에는 공개 API 주소만 있다.
루트 `.env`를 읽거나 복사하지 않으며 frontend에 Supabase SDK·Data API·PostgreSQL 연결은 없다.

## Design system과 공통 components

Tailwind `@theme`는 CSS 변수와 `bg-ivory`, `bg-butter` 등의 utility를 함께 제공한다.

| 토큰 | 값 |
| --- | --- |
| `--color-ivory` | `#F6F0E4` |
| `--color-cream` | `#DEC6A4` |
| `--color-biscuit` | `#B99972` |
| `--color-butter` | `#F2D77C` |
| `--color-peach` | `#EBAFA5` |

Ivory 배경과 Butter 강조를 기본으로 사용한다. 가독성을 위한 ink/muted/outline을 보조 토큰으로 둔다.
외부 font·stock image 요청은 없고 실제 구조동물 API 이미지 또는 자체 SVG placeholder만 사용한다.
`AnimalImage`는 사진 없음·유효하지 않은 URL·로드 실패를 `ImageEmptyState`로 전환한다.

Header, Footer, LoadingState, ErrorState, EmptyState, ImageEmptyState, Button, ButtonLink,
TagChip 및 최소 SiteLayout/RouteError/AnimalImage/FavoriteButton을 구현했다.
semantic landmarks, skip link, route 이동 후 main focus, focus-visible, label/alt/aria-pressed,
live status, 44px 이상 주요 조작 영역과 reduced-motion 설정을 포함한다.

## Favorite

`furbebe:favorites`에 animal UUID 배열을 저장한다. `createFavoritesStore`의 storage adapter와
`useFavorites` hook으로 캡슐화하고 UI에는 조회·toggle만 노출한다.
깨진 JSON·잘못된 ID·중복을 정리하며 저장소 차단/용량 오류에는 현재 탭 메모리로 동작하고 사용자에게 알린다.
다른 탭의 storage event를 반영하고 SSR은 빈 snapshot으로 hydration 불일치를 피한다.
새로고침 후 복원되며 나중에 로그인 기반 adapter/hook 구현을 교체할 수 있다.
현재 계정 동기화·서버 저장·여러 탭의 동시 쓰기 transaction은 제공하지 않는다.

## 실행과 검증

Node.js 24.18.0 / npm 12.0.2 / Windows에서 검증했다. 최소 Node 버전은 22.22다.
새 설치는 `npm --prefix frontend ci`, 개발 서버는 루트에서 `npm run dev`다.
Backend는 별도로 `127.0.0.1:8080`에서 실행한다. 기존 DEV 대상 선택 방법은 [README](../README.md)를 따른다.
공개 API 주소 변경이 필요한 경우만 `frontend/.env.local` 또는 빌드 프로세스 환경변수에 설정한다.
로컬 주소가 들어간 파일로 production을 빌드하면 해당 주소가 유지되므로 production API 값을 명시한다.

| 검증 | 결과 |
| --- | --- |
| `npm test` | Vitest + RTL, 5 files / **43 passed** |
| `npm run lint` | ESLint, jsx-a11y, hooks 규칙 / warning 0 |
| `npm --prefix frontend audit --audit-level=high` | 알려진 취약점 0 |
| `npm run build` | client + Workers SSR production build |
| `npm --prefix frontend run check:worker` | Wrangler deploy dry-run, 실제 배포 없음 |
| 실제 DEV 연결 | Workers loader에서 API 목록·상세 200, 실제 등록 수 7,290건 |
| 브라우저 | 목록 → 상세 이동, 실제 API 사진, favorite 저장·새로고침 복원 |
| 빈 결과·HTTP 오류 | 실제 DEV의 빈 검색 결과, 잘못된 query 422, 잘못된 animal ID 404 확인 |
| 모바일·키보드 | 390px 상세 / 320px 홈 가로 넘침 없음, Tab skip link와 visible focus 확인 |
| production preview | 로컬 Workers에서 홈 200, favicon 200, 잘못된 ID 404; 홈 console error/warning 0 |
| 환경변수 노출 검사 | client/SSR 산출물 18개에서 실제 비공개 값 7개 및 비밀값 표식 검출 0 |

번들 검사는 `VITE_SUPABASE_SECRET_KEY`와 `SUPABASE_SECRET_KEY`에 합성 표식을 넣고
production을 빌드해 검사했다. 공개 API는 `https://api.furbebe.com`이고 로컬 API 주소는 산출물에 없다.
검사 중 실제 비밀값은 출력하지 않았다. 로컬 증거는 Git 제외 경로
`output/playwright/phase6-bundle-audit.json`, `phase6-detail-mobile.png`,
`phase6-home-production-mobile.png`에 있다. production preview의 목록·상세는 운영 API에
연결하지 않았으며 실제 API 동작은 개발 Workers → 로컬 FastAPI → DEV PostgreSQL에서 검증했다.

테스트는 API client/오류 정규화/redirect/timeout/취소, JSON 경계, favorites의
SSR·저장 실패·탭 동기화, 기본 routes·query·오류 재시도·404, ErrorState·ImageEmptyState를 포함한다.
합성 fixture는 unit test에만 사용하며 실제 동물인 것처럼 UI에 기본 주입하지 않는다.
브라우저 확인은 Playwright CLI로 수행했다. 테스트마다 전체 end-to-end 환경을 요구하지 않는다.
검증을 위해 실행한 브라우저와 로컬 API/dev/preview 서버는 종료했다.
Backend 전체 회귀는 이번 프런트엔드 변경에서 재실행하지 않았으며 Phase 5의 390건 결과와 구분한다.

## Cloudflare 준비

`@cloudflare/vite-plugin`의 SSR environment, Workers `fetch` entry, Wrangler assets 설정을 연결했다.
Framework `ssr: true`, compatibility date `2026-09-21`, `nodejs_compat`를 사용한다.
생성된 `build/server/wrangler.json`을 Wrangler가 사용하며 `build/client`를 static assets로 제공한다.
`npm run preview`는 빌드 결과를 로컬 Workers runtime의 4173 포트에서 실행한다.
Cloudflare 계정·도메인·production 환경 설정, 실제 API 도메인 연결 및 운영 배포 검증은 후속 작업이다.

공식 근거: [Cloudflare React Router](https://developers.cloudflare.com/workers/framework-guides/web-apps/react-router/),
[React Router loaders](https://reactrouter.com/start/framework/data-loading),
[Tailwind Vite](https://tailwindcss.com/docs/installation/using-vite).

## 미해결 / Phase 7 readiness

- Phase 6 기반 구조의 구현은 완료했다. Main/List/Detail 최종 디자인, 상세 필터·페이지 UI 등은 미구현 범위다.
- 현재 v1 animals API는 모든 축종을 반환하고 species query가 없다. `/dogs`의 기본 연결 화면에도
  고양이·기타 축종이 포함될 수 있다. Phase 7의 개 전용 목록은 backend 계약 결정이 먼저 필요하다.
  페이지를 받은 뒤 frontend에서 임의 필터링해 pagination을 왜곡하지 않는다.
- [Phase 5 재검토](phase5-review.md)의 DEV dotenv 일반 설정 누락과 자정 통과 캐시 결함 2건은 기존 backend 미해결 사항이다.
  현재 server loader는 브라우저 CORS에 의존하지 않지만 직접 browser API 호출을 추가할 때는
  backend 프로세스 환경변수의 `FRONTEND_ORIGIN`을 실제 origin과 맞춰야 한다.
- 실제 production 배포·API 도메인 가동은 검증하지 않았다. dry-run 성공은 운영 배포 성공을 뜻하지 않는다.
- 이후 UI를 구축할 route/service/token/component/favorite/test 경계는 준비됐다. **Phase 7 승인 대기.**

## 변경 파일

- 루트: `package.json`, `.gitignore`, `README.md`.
- 문서: `docs/architecture.md`, `docs/phase6-frontend-base.md`.
- Frontend 설정: `.env.example`, `package.json`, `package-lock.json`, `vite.config.js`,
  `react-router.config.js`, `wrangler.jsonc`, `eslint.config.js`, `vitest.config.js`.
- Frontend app: `root.jsx`, `entry.client.jsx`, `entry.server.jsx`, `routes.js`,
  `routes/{home,dogs,dog-detail}.jsx`, `styles/app.css`.
- Components: `header.jsx`, `footer.jsx`, `site-layout.jsx`, `button.jsx`, `states.jsx`,
  `route-error.jsx`, `animal-image.jsx`, `favorite-button.jsx`, `tag-chip.jsx`.
- Services/hooks: `services/{api,animals,tags,meta,validation,route-loader,favorites}.js`, `hooks/use-favorites.js`.
- Worker/asset: `workers/app.js`, `public/favicon.svg`.
- Tests: `setup.js`, `fixtures.js`, `api.test.js`, `services.test.js`,
  `favorites.test.jsx`, `components.test.jsx`, `routes.test.jsx`.

위 frontend 상대 경로는 모두 `frontend/` 아래다. Phase 5 작업부터 존재하던 다른 미커밋 문서는 이번 구현 범위가 아니다.
