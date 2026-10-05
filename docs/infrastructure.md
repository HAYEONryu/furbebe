# 인프라와 배포 매뉴얼

운영 주소는 **https://furbebe.site**, www는 apex로 308 redirect,
API는 **https://api.furbebe.site**입니다.
이 문서는 저장소 설정과 배포 절차를 설명합니다. 실제 구성 완료 여부는 [운영 상태](operational-status.md)를 확인합니다.

## 구성과 담당

| 구성 | 역할 | 설정·실행 위치 |
| --- | --- | --- |
| Cloudflare Workers | React Router SSR, 정적 파일, www redirect | frontend/wrangler.production.jsonc |
| Cloud Run | FastAPI 읽기 container | deploy/cloud-run.service.yaml |
| HTTPS Load Balancer | API 도메인·인증서·Cloud Run 연결 | 외부 계정에서 구성 필요 |
| Supabase PROD | PostgreSQL 데이터 | project xhlenzdnqnbczekkovgl |
| Supabase DEV | 개발용 PostgreSQL | project ckajshgtefzsmhttajoo |
| GitHub Actions | 품질 검증, 수집 | .github/workflows |
| Secret Manager | API DB 접속 secret | furbebe-prod-database-url |

Cloud Run YAML에는 project/image/service account/secret version placeholder가 있습니다.
LB, DB 역할, backup 자동화와 DNS의 완성된 IaC는 저장소에 없습니다.
CI는 image를 build·검사하지만 registry push나 실제 배포를 하지 않습니다.
GitHub 코드를 Run trigger 버튼으로 수동 배포하는 Cloud Build 설정은 [deploy/cloudbuild.api.yaml](../deploy/cloudbuild.api.yaml)입니다.
저장소 연결·배포 계정·Manual invocation 설정은 [GitHub 수동 배포 매뉴얼](github-deployment.md)을 따릅니다.
Google Cloud에서 수동 trigger를 연결하고 버튼을 눌러 실행합니다.

## 1. 배포 준비

release commit, DB revision, API image digest, Worker version을 기록합니다.
동일 release에서 품질 CI를 확인하고 별도 staging에서 실제 데이터·사진·메모리·동시 요청을 점검합니다.
staging은 별도 Worker 이름·도메인·DEV DB를 사용합니다. 기본 wrangler와 production profile의 Worker 이름은 같으므로
기본 profile을 “격리된 staging”으로 간주해 배포하지 않습니다.

계정에서 다음 항목을 확인합니다.

- GCP project/billing, Artifact Registry, Cloud Run·Secret Manager·Compute API.
- Cloudflare account, furbebe.site 활성 zone, domain 소유권과 기존 DNS 충돌.
- Supabase 실제 plan, pooler/server connection 한도, network 제한, DB 역할.
- GitHub default branch의 workflow, production-sync environment와 secret·variable.
- [검증 가능한 백업과 복구](operations.md), 이미지·revision rollback 정보.

새 클라우드 자원 생성과 유료 옵션은 비용을 확인한 뒤 해당 운영 절차로 진행합니다.
이 매뉴얼의 provisioning 명령을 문서 검토만으로 실행하지 않습니다.

## 2. Supabase 연결과 역할

API는 SQLAlchemy → psycopg로 PostgreSQL에 접속합니다. Supabase API/Auth key는 필요 없습니다.
현재 명시적 대상 guard는 session pooler/direct의 port 5432, postgres DB, TLS를 요구합니다.
수집의 session advisory lock을 유지해야 하므로 transaction pooler 6543로 바꾸지 않습니다.
Supabase Connect에서 실제 URI를 복사하며 region 이름으로 pooler host를 만들어 쓰지 않습니다.
IPv4에서는 session pooler가 direct IPv6의 대안입니다. [공식 접속 안내](https://supabase.com/docs/guides/database/connecting-to-postgres)

DB 접속 역할은 다음 책임으로 분리합니다. 현재 실제 분리 여부는 운영 상태를 봅니다.

| 역할 | 권한 범위 |
| --- | --- |
| API 읽기 | public schema USAGE와 도메인 SELECT |
| sync 쓰기 | 필요한 SELECT/INSERT/UPDATE; 정상 sync는 DELETE 불필요 |
| migration 관리 | Alembic과 필요한 DDL·데이터 migration |
| backup | 검증된 export 범위의 읽기 권한 |

명시적 pooler guard는 username이 .PROJECT_REF로 끝나는지 검사합니다.
사용자 역할 접속도 Dashboard에서 제공·검증한 형식을 사용합니다.
SUPABASE_URL_prod와 FURBEBE_PROD_PROJECT_REF가 자격증명 대상과 일치해야 합니다.

API container에는 DATABASE_URL secret만 주입합니다.
원천 API key는 수집 환경에만 넣습니다. Runtime 서비스 계정의 Secret Accessor는 필요한 secret에 제한합니다.
secret version을 고정하면 rollback 시 어떤 DB 설정이 사용되는지 추적할 수 있습니다.

## 3. DB 스키마 준비

APP_ENV=production에서 production_preflight를 실행해 current, head, 적용 SQL, checksum을 확인합니다.
이미 운영 head가 적용돼 있다면 초기 적재를 다시 시작하지 않습니다.
revision 차이가 있으면 검증된 백업과 영향 검토 후 별도 Alembic 실행 환경에서 upgrade합니다.
API image에는 migrations/jobs가 없으므로 container 시작 명령에 migration을 넣지 않습니다.
[DB 매뉴얼](database-schema.md)을 따릅니다.

## 4. API image

저장소 루트에서 실행합니다. 아래 변수는 계정의 실제 값으로 설정한 후 사용합니다.

```sh
docker buildx build --platform linux/amd64 \
  --provenance=false --sbom=false \
  -f backend/Dockerfile -t "$FURBEBE_IMAGE_TAG" --push .
docker buildx imagetools inspect "$FURBEBE_IMAGE_TAG"
```

push에는 registry 인증과 기존 repository가 필요합니다. 배포는 tag 대신 확인한 sha256 digest로 고정합니다.
Cloud Run은 linux/amd64 실행 이미지를 사용합니다. 위 명령은 빌드 증명용 manifest 생성을 끕니다.
digest는 inspect의 최상위 Digest 또는 검증한 linux/amd64 실행 manifest를 사용하며,
unknown/unknown 또는 attestation-manifest의 digest를 선택하지 않습니다.
[Cloud Run 이미지 조건](https://docs.cloud.google.com/run/docs/container-contract),
[Docker 빌드 증명 형식](https://docs.docker.com/build/metadata/attestations/attestation-storage/)
Docker는 Python 3.14 slim, UID 10001 nonroot, 프로세스 1개, 8080 포트, reload/debug off입니다.
.dockerignore는 API source/지역 사전/runtime requirements만 허용합니다.
.env·원천 capture·백업·jobs·migration·test·가상환경은 image에 없습니다.

### Cloud Shell Docker 업로드 연결 실패

`docker push`가 `dial tcp ...:443: connect: connection refused`로 실패하면
image 생성과 registry 업로드를 구분합니다. 로컬 image가 있어도 push가 완료되지 않으면 Cloud Run에서 tag를 찾을 수 없습니다.
Shell의 curl이 HTTP 응답을 받아도 Docker daemon의 접속 경로가 정상이라는 뜻은 아닙니다.
반복되는 경우 Cloud Build 실행 환경에서 image를 생성하고 push하는 대안을 사용합니다.
정확한 Cloud Shell 네트워크 원인은 별도 확인하며, 이 대안의 성공을 미리 단정하지 않습니다.

Cloud Build API를 활성화하고, 빌드 서비스 계정의 source bucket 읽기·로그 쓰기·해당 repository 쓰기 권한을 확인합니다.
기본 빌드 계정은 프로젝트에 따라 다르므로 고정된 이메일을 추측하지 않습니다.
`gcloud builds get-default-service-account`로 확인할 수 있습니다.
[Cloud Build 빌드·업로드](https://docs.cloud.google.com/build/docs/build-push-docker-image),
[기본 빌드 계정](https://docs.cloud.google.com/build/docs/cloud-build-service-account-updates)

빌드 설정의 Docker 단계는 저장소 루트에서 `backend/Dockerfile`을 사용합니다.
Docker 20.10/24 기반 공식 builder의 `DOCKER_BUILDKIT=0`과 `--platform linux/amd64`로
빌드 증명 manifest 없이 실행 image를 생성할 수 있습니다. `images` 항목에 같은 image tag를 지정해 업로드합니다.
Cloud Build에 보내는 source에도 secret이 들어가지 않아야 합니다.
`.dockerignore`를 별도 `.gcloudignore-api`로 복사한 뒤 `!backend/Dockerfile`, `!.dockerignore`,
사용할 빌드 YAML 파일의 허용 항목을 추가하고, submit에 `--ignore-file=.gcloudignore-api`를 지정합니다.
Docker의 ignore 규칙만으로 Cloud Build source 업로드가 제한된다고 가정하지 않습니다.
빌드 결과 SUCCESS와 registry의 새 tag를 확인한 뒤 기존 Cloud Run 서비스의 이미지만 변경합니다.

## 5. Cloud Run

템플릿을 별도 작업 파일로 복사해 placeholder를 실제 값으로 채웁니다.
기존 서비스 변경이라면 현재 YAML·revision·traffic·IAM도 먼저 기록합니다.

| 항목 | 템플릿 값 |
| --- | --- |
| region | asia-northeast3 |
| CPU / memory | 1 CPU / 512Mi |
| min / max instances | 0 / 2 |
| concurrency / process | 4 / 1 |
| request timeout | 30초 |
| DB pool | 3 + overflow 1 |
| pool timeout / recycle | 5초 / 1800초 |
| connect / statement timeout | 5초 / 5000ms |
| ingress | internal-and-cloud-load-balancing |
| startup probe | TCP 8080 |

min0은 cold start를 허용합니다. /health는 DB 연결 상태를 확인하는 운영 smoke에 사용합니다.
DB 장애를 이유로 반복 재시작하지 않도록 Cloud Run startup은 TCP probe입니다.
Docker HEALTHCHECK와 Cloud Run startup probe는 별도 설정입니다.

```sh
gcloud run services replace "$FURBEBE_SERVICE_CONFIG" --project "$FURBEBE_GCP_PROJECT" --region asia-northeast3
gcloud run services describe furbebe-api --project "$FURBEBE_GCP_PROJECT" --region asia-northeast3
```

API는 APP_ENV=production, HTTPS FRONTEND_ORIGIN 두 개, 일반 DATABASE_URL secret으로 실행합니다.
일반 API template에 FURBEBE_DATABASE_TARGET=supabase-prod를 추가하면 suffixed secret이 없어 설정 오류가 날 수 있습니다.

### 이미지 가져오기 실패

Container import failed와 함께 `Manifest.Layers vs ConfigFile.RootFS.DiffIDs`가 표시되면
배포한 manifest가 실제 실행 이미지인지 확인합니다. 빌드 증명용 OCI artifact도 registry에 함께 표시될 수 있으며,
그 artifact의 빈 config는 실행 가능한 root filesystem 정보를 갖고 있지 않습니다.
위 빌드 명령으로 새 tag를 push하고 실제 실행 이미지 또는 최상위 image index를 선택해 다시 배포합니다.
이 단계의 실패는 앱 실행 전 발생하므로 포트·DB 설정·startup timeout 변경으로 해결하지 않습니다.
기존 Cloud Run 서비스에서는 이미지 필드만 변경해 환경변수와 secret 참조를 유지합니다.

외부 LB 경로의 공개 GET 요청은 Cloud Run invocation 설정도 맞아야 합니다.
선택한 공개 방식에 따라 invoker IAM 또는 invoker check 설정을 검토합니다.
CORS만으로 invocation이 허용되지 않습니다.
ingress를 유지해 외부 run.app 직접 접근을 제한합니다.
[Cloud Run ingress](https://cloud.google.com/run/docs/securing/ingress)

정상 용량 계산은 2 instances × 1 process × (3+1)=API 8연결, sync는 추가 2연결입니다.
배포 겹침·사전검사·관리·내부 예약 연결과 provider client/server 한도를 더해 여유를 확인합니다.
max instances를 DB hard cap으로 보지 않습니다. [Cloud Run 최대 인스턴스](https://cloud.google.com/run/docs/configuring/max-instances)

## 6. API HTTPS와 DNS

저장소의 ingress 설정에 맞춘 경로는 **global external Application Load Balancer + serverless NEG**입니다.
이 경로는 준비 절차이며 LB가 이미 생성되었다는 뜻이 아닙니다.

Cloud Console에서 일관된 LB 유형을 선택해 다음 순서로 구성합니다.

1. 같은 GCP project, asia-northeast3의 furbebe-api Cloud Run을 가리키는 serverless NEG.
2. 해당 NEG를 쓰는 backend service; serverless backend의 지원 설정을 사용.
3. api.furbebe.site를 backend로 보내는 URL map.
4. 승인된 고정 IP, HTTPS frontend 443, api.furbebe.site 인증서.
5. API DNS A record를 **실제 할당 IP**로 연결하고 TLS 발급·검증 확인.
6. Cloud Run ingress/invocation을 확인하고 외부 /health와 read endpoints 검사.

사용할 인증서 방식에 맞춰 DNS 인증 절차도 완료합니다.
AAAA는 IPv6 frontend가 실제 제공될 때만 추가합니다.
초기 API DNS는 DNS-only로 구성하는 경로를 검토하고, proxy 사용 시 TLS와 routing을 별도 검증합니다.
Cloudflare Worker route로 API host를 연결하지 않습니다.
[Google serverless HTTPS LB 설정](https://docs.cloud.google.com/load-balancing/docs/https/setting-up-https-serverless)

## 7. Worker 운영 빌드·배포

API가 준비된 뒤 frontend 디렉터리에서 실행합니다.

```sh
npm ci
FURBEBE_BUILD_TARGET=production VITE_API_BASE_URL=https://api.furbebe.site VITE_SITE_URL=https://furbebe.site SITEMAP_API_BASE_URL=https://api.furbebe.site npm run build
npm run check:worker
```

SITEMAP_API_BASE_URL을 설정하면 빌드 전 실제 UUID 전체를 읽습니다.
API 실패·부분 snapshot은 build를 실패시킵니다. API 미준비 상태의 빌드에서는 이 변수 없이 정적 경로만 생성합니다.
.env.local이 존재할 수 있어 운영 공개 URL은 위처럼 프로세스 환경으로 지정합니다.

운영 profile은 두 Custom Domain, workers_dev=false, preview_urls=false,
ASSETS binding과 run_worker_first=true를 포함합니다.
www의 정적 파일 요청도 Worker가 먼저 받아 apex로 308 이동하고 path/query를 보존합니다.
Vite/React Router build가 생성한 build/server/wrangler.json과 .wrangler/deploy/config.json의 연결을 확인합니다.

검토한 동일 build를 배포합니다.

```sh
npx wrangler deploy
```

생성 설정을 사용하는 위 명령을 frontend에서 실행합니다.
원본 workers/app.js의 virtual import가 남은 상태로 raw config만 배포하지 않습니다.
[React Router Workers 배포](https://developers.cloudflare.com/workers/framework-guides/web-apps/react-router/)

furbebe.site와 www.furbebe.site는 활성 Cloudflare zone에서 Worker Custom Domain으로 구성합니다.
Custom Domain 연결이 필요한 DNS와 인증서를 관리하므로 기존 충돌 record를 먼저 확인합니다.
도메인 등록기관과 authoritative nameserver 설정은 zone 활성화 상태에 맞춥니다.
[Workers Custom Domains](https://developers.cloudflare.com/workers/configuration/routing/custom-domains/)

## 8. 수집 활성화와 완료 검사

첫 수집·스키마 확인 후 production-sync를 구성하고 수동 실행 결과를 확인합니다.
PRODUCTION_SYNC_ENABLED=true는 default branch의 정기 작업을 운영으로 전환합니다.
false/unset이면 정기 DEV 수집이 실행되므로 전체 수집 비활성화 스위치가 아닙니다.
필요한 중지는 workflow schedule 자체를 disable하는 방식으로 처리합니다.
[수집 설정](../deploy/sync-environments.md)을 따릅니다.

[배포 후 점검표](../deploy/production-smoke-checklist.md)로 HTTP/TLS/CORS/SSR/사진/태그/후원/ads.txt/SEO를 검사합니다.
성능은 cold/warm, memory, p95/p99, pool timeout과 작은 동시 요청으로 확인합니다.
LB·Cloud Run·DB·registry·Workers·로그의 실제 요금과 quota는 각 계정에서 확인합니다.

## rollback

API는 알려진 이전 image/Cloud Run revision으로 traffic을 돌립니다.
Worker는 알려진 이전 version 또는 이전 commit의 동일 공개 설정 build를 배포합니다.
DB downgrade를 앱 rollback과 묶지 않습니다. schema 호환성을 확인하고 필요하면 roll-forward 또는 검증된 별도 DB 복구를 합니다.
변경 전후 release/image/Worker/secret/revision과 smoke 결과를 기록합니다.
