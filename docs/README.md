# 문서 목차

이 문서들은 현재 저장소의 코드와 설정을 설명합니다. 개발 과정의 단계별 완료 보고서는 유지하지 않습니다.
실제 클라우드 구성 여부와 데이터 건수는 [운영 상태](operational-status.md)의 확인 날짜를 기준으로 읽습니다.

| 문서 | 내용 |
| --- | --- |
| [프로젝트 README](../README.md) | 서비스, 구조, 설치, 로컬 실행 |
| [아키텍처](architecture.md) | 책임 경계, 요청·수집 흐름, 시간·보존 정책 |
| [환경 설정](environment.md) | 최소 변수, DEV/PROD 선택, dotenv와 프로세스 환경 |
| [태그 생성](tag-generation.md) | 전체 사전, 활성 규칙, 부정·불확실성 차단, 색·몸집, 증거·버전 |
| [수집 설계](sync-design.md) | CLI, pagination, UPSERT, 비활성화, capture, counter, 실패 |
| [원천 필드 사전](api-field-dictionary.md) | 공공데이터 필드와 DB·API 연결, 정규화 형식 |
| [DB 스키마](database-schema.md) | 테이블, 제약, 인덱스, migration, 조회 |
| [API 계약](api-contract.md) | endpoint, query, 응답, 오류, 캐시, 유사 동물 |
| [프런트엔드](frontend.md) | SSR, URL 상태, 관심 저장, 공유, 이미지, SEO, AdSense, 후원 |
| [검증](quality.md) | 단위·DB·브라우저·컨테이너·CI 실행 및 해석 |
| [인프라](infrastructure.md) | Supabase, Cloud Run, HTTPS LB, Cloudflare, 배포·롤백 |
| [GitHub API 수동 배포](github-deployment.md) | Cloud Build 저장소 연결·Run trigger 버튼·배포 계정·확인 |
| [운영](operations.md) | 백업, 복구, 데이터 갱신, 관측, 장애 진단 |
| [운영 상태](operational-status.md) | 실제 확인한 운영 DB와 미완료 외부 배포 |
| [원천 분석 도구](source-analysis.md) | 선택적 profiling·참조 코드 분석과 비공개 보고서 |

배포 시 바로 사용할 문서:

- [배포 후 점검표](../deploy/production-smoke-checklist.md)
- [백업·복구 점검표](../deploy/backup-recovery-checklist.md)
- [GitHub 수집 설정](../deploy/sync-environments.md)

규칙이 바뀌면 코드의 검증 근거와 이 문서를 같은 변경에 포함합니다.
생성된 분석 보고서는 .local에 저장하며 사람이 관리하는 안내 문서를 덮어쓰지 않습니다.
