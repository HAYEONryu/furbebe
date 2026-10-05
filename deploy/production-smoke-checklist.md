# 배포 후 점검표

release commit, API image digest/Cloud Run revision, Worker version, DB revision,
secret version, 실행자·시각·실제 UUID와 결과를 기록합니다. 설정 파일만 보고 통과로 표시하지 않습니다.

## API

- [ ] api.furbebe.site DNS/TLS, /health 200과 status=ok/service=furbebe-api/version=1.
- [ ] X-Request-ID UUID, 실제 DB 연결.
- [ ] animals pagination/total, 활성 개만 노출; 기본 API와 UI 상태 필터 차이 확인.
- [ ] 실제 UUID 상세·similar, 원본 제외, null 안전성, 원문과 보호소 연락처.
- [ ] tags 27개 사전과 현재 생성 규칙·근거 일치; 미배정 사전 항목 구분.
- [ ] meta 지역 label/그룹·stats, cold/warm 지연.
- [ ] 잘못된 UUID/query 422, 없는 UUID/key 404, 안전한 오류 envelope.
- [ ] apex/www CORS 허용, unrelated/local origin 미허용, credentials 미사용.
- [ ] production docs/OpenAPI off, reload/debug off, secret 없는 앱 로그.
- [ ] Cloud Run ingress/invocation, LB NEG와 직접 외부 run.app 제한.
- [ ] 작은 동시 요청에서 memory·pool timeout·p95/p99.

## 화면·SEO·광고·후원

- [ ] /, /dogs, 실제 /dogs/UUID의 SSR과 hydration, 정상 HTTP status.
- [ ] 목록 검색·필터·any/all·sort·page·뒤로가기·빈 결과.
- [ ] 실제 원천 사진과 broken image fallback, 모바일 320/360/768/1440 overflow.
- [ ] 관심 저장 reload·storage fallback, share/clipboard/manual fallback.
- [ ] 키보드·focus·modal Escape/복원·태그 tooltip.
- [ ] www가 path/query를 보존해 apex 308; 정적 파일도 동일.
- [ ] canonical/robots/OG, 필터 noindex, 오류 status/noindex.
- [ ] robots.txt·sitemap.xml 200, 상세 UUID snapshot 사용 시 실제 URL 표본 200.
- [ ] 공통 head의 AdSense meta/script, ads.txt 200과 publisher 일치.
- [ ] AdSense 계정 사이트 상태·자동 광고 설정; 광고 미노출을 코드 누락으로 단정하지 않음.
- [ ] 계좌 클릭 시 79792875935 복사, 안내 2초 해제·실패 수동 복사.

## 수집·보존·복구

- [ ] current=head, backup 범위/checksum·실데이터 복구 검증.
- [ ] PROD environment/target 일치, 수동 run success, capture·counter 확인.
- [ ] raw received와 저장 대상 수 차이를 excluded로 설명.
- [ ] 정상 수집 삭제 0, 기존 비대상/빠진 사진·태그 비활성 보존.
- [ ] failed run·partial batch·running/lock 충돌 대응.
- [ ] 활성화한 경우 KST 00:00/12:00 정기 실행과 freshness 확인.
- [ ] API·Worker 이전 revision rollback 정보, schema 호환성.
- [ ] 신규 indexable 자료가 필요하면 수집 뒤 sitemap rebuild/deploy.
