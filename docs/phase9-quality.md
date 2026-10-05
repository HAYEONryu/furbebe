# Phase 9 — SEO / Accessibility / Performance / Quality Pass

검증일: 2026-10-01 (Asia/Seoul). 새 핵심 기능이나 실제 배포는 수행하지 않았다. Phase 10은 사용자 승인 전 시작하지 않는다.

## SEO

React Router Framework SSR (`ssr: true`)의 route `meta`에서 Main, Dogs, Dog Detail의 title, description, canonical, Open Graph, og:image를 생성한다. SSR 응답 HTML에서 canonical과 OG 태그를 브라우저 smoke test로 확인했다. Detail의 품종, 지역, 보호 상태, 사진은 검증된 FastAPI 응답에서만 사용한다. 사진이 없거나 URL이 안전하지 않으면 1200×630 PNG 브랜드 이미지로 대체한다. 동물의 성격·긴급성·남은 보호 기간을 만들지 않는다.

`VITE_SITE_URL`은 HTTP(S) origin만 허용하고 canonical과 sitemap의 기준으로 사용한다. Host 헤더나 preview URL을 canonical에 반영하지 않는다. 기본값은 기존 도메인인 `https://furbebe.com`이며, 배포 환경에서 실제 공개 origin을 명시적으로 확인한다. Vite 공개 환경변수 allowlist에 이 값만 추가했다. 저장소 루트의 `env`를 프런트엔드로 복사하거나 읽지 않았다.

## Sitemap / Robots / Filter SEO

- `npm run build`의 prebuild가 `public/sitemap.xml`, `public/robots.txt`를 생성한다. 두 파일은 정적 자산으로 제공하며 HTTP request-time API 스캔은 없다.
- `SITEMAP_API_BASE_URL`을 빌드 환경 또는 frontend `.env.production`에 설정하면 `/api/v1/animals`에서 실제 UUID를 수집한다. 프런트엔드가 DB에 접근하지 않는다.
- FastAPI 계약의 최대 page_size=60, 최대 834페이지, 페이지별 20초 timeout, 최대 50,000 URL 제한을 둔다. 실패·비정상 응답·페이지 상한 도달은 빌드를 실패시켜 부분 sitemap 발행을 막는다. UUID 검증·중복 제거·XML escaping 후 임시 파일을 rename한다. 임의 lastmod는 넣지 않는다.
- API 미설정 시 sitemap에는 `/`, `/dogs`만 들어간다. 현재 체크인된 파일도 이 두 경로만 포함한다. 테스트 UUID나 존재 여부가 확인되지 않은 동물 URL은 넣지 않았다.
- 동기화 후 다음 빌드에서 snapshot을 갱신한다. 현재 첫 서비스 규모에 적합한 방식이며, 50,000개에 접근하면 분할 sitemap이 필요하다. 빌드 중 목록 변경은 transactional snapshot이 아니므로 동기화가 끝난 안정적인 시점에 생성한다.
- `/dogs`의 모든 non-empty query(필터·검색·정렬·페이지·미지의 query 포함)는 canonical `/dogs`, `noindex, follow`다. query가 없는 기본 목록만 index 허용한다.
- 필터 UI는 버튼/폼이며 조합별 정적 링크를 생성하지 않는다. query 페이지의 페이지네이션 링크는 `rel=nofollow`로 crawl 확장을 줄인다.
- robots.txt는 crawl을 허용해 검색엔진이 noindex를 읽게 한다. robots Disallow와 noindex를 동시에 사용하지 않는다. 이는 모든 crawler의 방문을 강제 차단한다는 뜻은 아니다.
- 404/502/503 및 SSR 오류는 `X-Robots-Tag: noindex, nofollow`를 반환한다. 정상 데이터가 없는 route meta도 noindex다. HEAD 오류에도 동일 헤더를 적용한다.

참고: [React Router meta](https://reactrouter.com/how-to/meta), [Google noindex](https://developers.google.com/search/docs/crawling-indexing/block-indexing), [Google faceted navigation](https://developers.google.com/crawling/docs/faceted-navigation), [Google sitemap](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap).

## Performance / Images

이미지 width/height는 640×480으로 예약한다. 기본 카드와 상세 사진은 4:3, 홈 hero는 1:1이다. 오류 placeholder도 같은 비율을 유지한다. 갤러리와 홍보 이미지는 contain으로 전체 사진을 보여준다. Tailwind utilities가 기존 컴포넌트의 비율과 object-fit을 덮던 문제를 공통 `.animal-image` 스타일로 수정했다. 홍보 이미지도 일정 비율을 예약한다.

홈 hero와 상세 주요 사진은 eager/high priority를 유지하고, Dogs의 첫 카드만 eager/high priority로 지정했다. 나머지 카드, thumbnail, 홍보 이미지는 lazy다. missing/unsafe URL 및 실제 load error fallback, 새 source 변경 시 복구는 단위 테스트로 확인했다. broken hero 전후 크기가 동일함도 브라우저로 검증했다.

로컬 production SSR 빌드, 합성 API·가벼운 로컬 PNG, Chromium, 900px 높이에서 측정:

| 화면 폭 | Main LCP | Dogs LCP | Detail LCP | CLS |
| --- | ---: | ---: | ---: | ---: |
| 360px | 148ms | 72ms | 52ms | 모두 0 |
| 390px | 64ms | 60ms | 48ms | 모두 0 |
| 768px | 60ms | 76ms | 48ms | 모두 0 |
| 1440px | 120ms | 76ms | 52ms | 모두 0 |

이 값은 실제 보호소 사진·운영 API latency·모바일 네트워크·field Core Web Vitals를 대체하지 않는다. 배포 후 실제 사진과 모바일 환경에서 다시 측정해야 한다. 초기 SSR API 호출은 Main/Dogs 각각 3개(목록·필터·태그), Detail 2개(상세·추천)이며 hydration 추가 호출은 0개다. 병렬 요청 구조를 유지했고 측정 근거 없는 캐시·memo·state 구조 변경은 하지 않았다. 코드 검토상 사용하지 않는 직접 dependency는 없었다.

production build 기준 client entry gzip 67.16kB, React/runtime 공통 chunk 39.66kB, route chunk home 2.11kB / dogs 2.12kB / detail 4.26kB, CSS 6.33kB. route 분할을 유지한다. npm audit의 개발 도구 취약점 4건은 Cloudflare 플러그인·Wrangler 수정 버전으로 제거했다. npm install 최종 audit 결과 0건.

## Accessibility / Responsive

Main / Dogs / Detail을 360, 390, 768, 1440px에서 검사하고 screenshot을 남겼다. 12개 route/viewport 모두 `documentElement.scrollWidth <= innerWidth`, WCAG 2 A/AA 및 2.1 AA axe 위반 0건, H1 1개, main landmark 1개를 확인했다. screenshot 시각 검토도 수행했다.

키보드 Tab → skip link → Enter → main focus, Tab으로 필터 진입, Enter로 modal 열기, 25회 Tab이 dialog 내부에 머무름, Escape 종료 및 trigger focus 복구를 실제 Chromium에서 검사했다. 기존 focus-visible, form label, button accessible name, heading, alt 및 emoji aria-hidden 처리를 유지했다. dialog가 열린 상태의 axe 검사도 통과했다. Native dialog와 기존 focus trap을 유지한다. 장문 데이터 줄바꿈을 보강했다. 자동 검사는 모든 스크린리더/브라우저 조합의 수동 검증을 대체하지 않는다.

## Error UX / Copy Review

브라우저에서 FastAPI 503, timeout, detail 404, 없는 route 404, empty search, missing image, null shelter/descriptions/promotion, malformed weight를 재현했다. 상태 코드는 각각 유지되고 사용자용 안내를 보여준다. SQL 등 upstream 원문을 노출하지 않는다. 부가 추천 API 오류의 독립 fallback은 기존 단위 테스트로 확인한다.

UI/메타 문구에서 근거 없는 안락사·구조 요청·성격 단정이나 불쌍함을 강조하는 표현은 확인되지 않았다. 원천 설명은 등록 원문으로 표시하고 보호 상태와 입양 절차는 보호소에 확인하도록 안내한다.

## Tests / Build

- Frontend: 10 files, 97 tests passed.
- Browser smoke: 21 passed. SSR HTML/SEO, 12 route/viewport, axe/contrast, keyboard/dialog, crawler assets, image failure geometry, 7 error scenarios.
- Backend: 391 passed, 0 skipped. Python 3.12 + PostgreSQL 16 로컬 disposable `furbebe_test_phase9`에서 실행. 운영 DB는 사용하지 않았다. Starlette의 httpx TestClient deprecation warning 1개는 현재 pinned 도구 호환성 안내이며 테스트 실패는 아니다.
- Frontend ESLint 및 backend Ruff: passed.
- React Router production client + SSR build: passed. smoke용 API 설정은 최종 빌드에 남기지 않았다.
- Cloudflare Worker deploy dry-run: passed. 실제 배포하지 않았다.

재실행:

```sh
npm ci --prefix frontend
npm test
npm run lint
npm run build
cd frontend
npx playwright install chromium
npm run test:smoke
npm run check:worker
```

smoke는 4173/8089 포트를 사용하는 합성 API와 production SSR 빌드를 실행한다. 테스트 종료 후 기본 운영 빌드가 필요하면 `npm run build`를 재실행한다. screenshot/trace는 ignored `frontend/.local`에 저장된다.

```sh
backend/.venv/bin/ruff check .
FURBEBE_TEST_DATABASE_URL=postgresql+psycopg://USER@127.0.0.1:PORT/furbebe_test_NAME backend/.venv/bin/pytest -q
```

## 배포 Blocker / Phase 10 Readiness

코드·테스트에서 확인된 미해결 blocker는 없다. 운영 배포의 완료를 주장하지 않는다. Phase 10 승인 후 공개 frontend/API origin, API CORS/연결 및 운영 데이터 존재, 실데이터 sitemap 생성, 실사진 LCP, preview indexing 차단 정책, 배포 환경의 route/robots/sitemap smoke를 확인해야 한다. 현재 sitemap에 실제 detail URL이 들어갔다는 뜻은 아니다.

Phase 10은 시작하지 않았다.

## 변경 파일

- `frontend/app/services/seo.js`, `animal-detail.js`
- `frontend/app/routes/home.jsx`, `dogs.jsx`, `dog-detail.jsx`
- `frontend/app/entry.server.jsx`
- `frontend/app/components/animal-card.jsx`, `animal-image.jsx`, `states.jsx`, `pagination.jsx`
- `frontend/app/styles/app.css`, `detail.css`
- `frontend/public/og-image.png`, `robots.txt`, `sitemap.xml`
- `frontend/scripts/generate-sitemap.mjs`
- `frontend/tests/seo.test.js`
- `frontend/e2e/fixture-api.mjs`, `quality.spec.js`, `frontend/playwright.config.js`
- `frontend/.env.example`, `vite.config.js`, `eslint.config.js`, `package.json`, `package-lock.json`
- `docs/phase9-quality.md`, `README.md`

사용자의 기존 `env` 파일은 변경하지 않았다. backend 소스와 migration 변경도 없다.
