# 프런트엔드 안내

React Router Framework SSR을 Cloudflare Workers에서 실행합니다.
frontend/app/routes.js는 홈, 목록, UUID 상세 세 route를 정의합니다.
SiteLayout은 Header/Footer와 Outlet을 공유하고 오류·로딩 화면에도 공통 영역을 제공합니다.

## 데이터·상태

services/api.js는 GET만 수행하고 공개 origin·로컬 API path를 검증합니다.
credentials를 보내지 않고 redirect를 거부하며 timeout·network·오류 응답을 안전한 UI 오류로 변환합니다.
services/validation.js는 API wire 응답을 검증합니다.

홈과 목록 loader는 animals/meta/tags를 병렬 호출합니다.
홈은 입양 가능 6건, 목록은 기본 입양 가능 24건입니다.
검색은 전체 상태로 전환해 탐색합니다. 상태 all은 API 호출에서 query를 생략합니다.
상세는 실제 facts로 SEO를 만들고, similar만 실패해도 상세 본문은 유지합니다.

필터·tag 반복 query·any/all·sort·page는 URL에 저장합니다.
필터 변경 시 page는 1로, 시도 변경 시 기존 시군구는 초기화합니다.
뒤로가기·링크 공유·새로고침에 동일한 검색 조건을 복원합니다.
지역·품종·그룹 옵션은 FastAPI meta를 사용합니다.

## 태그·이미지·관심 저장

태그 뜻은 frontend/app/services/tag-descriptions.json에서 읽습니다.
백엔드 CATALOG 설명 변경 시 함께 갱신합니다. tooltip은 hover/focus, Escape, viewport·modal 배치에 대응합니다.
태그 칩은 실제 API 배정으로 표시하며 프런트엔드에서 행동·몸집 태그를 생성하지 않습니다.
응답 호환 adapter는 중복 칩을 정리합니다. 현재 생성의 근거와 사전은 [태그 문서](tag-generation.md)를 따릅니다.

사진은 원천 URL 순서와 실패 fallback을 사용하고 hero 등 우선 사진은 priority를 적용합니다.
상세 source gallery는 중복 source URL을 제외합니다.
홍보 이미지와 일반 사진을 임의로 같은 원천 사진으로 취급하지 않습니다.

관심 목록은 localStorage의 furbebe:favorites에 UUID 배열로 저장합니다.
서버 snapshot은 빈 배열이고 다른 tab storage 변경을 반영합니다.
storage가 막혀도 현재 tab 메모리에서 선택을 유지합니다. 로그인·서버 계정 저장 기능은 없습니다.

상세 공유는 검색/hash가 없는 현재 origin의 상세 URL을 사용합니다.
navigator.share → clipboard → 선택 가능한 URL 순서로 fallback하며 사용자 share 취소는 실패 안내를 띄우지 않습니다.

## SEO와 sitemap

VITE_SITE_URL로 canonical origin을 고정합니다. preview Host가 canonical에 들어가지 않습니다.
홈·목록·상세에 title/description/canonical/robots/OG/Twitter metadata를 SSR 렌더링합니다.
필터 URL은 /dogs canonical과 noindex/follow, pagination 링크는 nofollow 정책입니다.
오류 페이지는 상태 코드와 noindex를 확인합니다.

npm build의 prebuild가 robots.txt/sitemap.xml을 생성합니다.
SITEMAP_API_BASE_URL이 없으면 /, /dogs만 포함합니다.
설정하면 공개 API에서 60개씩 UUID를 읽어 상세 경로를 추가합니다.
20초 page timeout, 최대 834페이지, 50,000 URL 제한이며 실패·부분 snapshot은 publish하지 않습니다.
ID 중복은 제거합니다. 수집 성공만으로 이미 배포된 sitemap이 바뀌지는 않습니다.

## Google AdSense

공통 root.jsx의 head에 다음 연결이 있어 모든 route에서 로드됩니다.

- 계정 meta: ca-pub-5519731659948026.
- 비동기 adsbygoogle.js script와 client query.
- public/ads.txt: google.com, pub-5519731659948026, DIRECT, f08c47fec0942fa0.

현재 연결은 자동 광고용이며 수동 ad-slot 컴포넌트·광고 공간 placeholder는 없습니다.
실제 광고는 배포된 head/ads.txt, AdSense 사이트 승인, 계정의 자동 광고 설정과 노출 조건에 따릅니다.
[Google 사이트 준비 안내](https://support.google.com/adsense/answer/7584263?hl=ko),
[자동 광고 설정](https://support.google.com/adsense/answer/9261307?hl=ko)

운영 확인 순서: HTTPS 사이트 정상 응답 → HTML meta/script → /ads.txt 200 → AdSense 사이트 상태·자동 광고.
로컬 source의 연결과 외부 배포본을 구분합니다.

## 개발자 후원

Footer에 “작은 후원으로 FURBEBE를 함께 키워주세요.”와 카카오뱅크 **7979-28-75935**를 표시합니다.
계좌번호 자체를 누르면 **79792875935**를 clipboard에 씁니다. 별도 copy 버튼은 없습니다.
복사 중 중복 동작을 막고 성공 안내는 2초 후 해제합니다.
실패하면 선택된 읽기 전용 숫자 input으로 직접 복사할 수 있습니다.
timer는 재클릭·unmount 시 정리하고 성공 안내 영역 높이를 예약합니다.

계좌·문구 변경은 footer.jsx에서, 광고 계정 변경은 root.jsx와 ads.txt에서 함께 반영합니다.
