# GitHub에서 Cloud Run API 수동 배포

GitHub `HAYEONryu/furbebe`를 연결하고, Cloud Build의 Run trigger 버튼을 누른 시점에
선택한 branch의 코드를 받아 image를 만듭니다. Artifact Registry에 업로드한 뒤 기존 Cloud Run `api` 서비스를 갱신합니다.
GitHub push·PR·merge는 이 수동 배포를 시작하지 않습니다.
프로젝트는 `furbebe-backend`, region은 `asia-northeast3`입니다.
이 문서는 연결 절차이며 trigger가 실제 생성·활성화됐다는 뜻은 아닙니다.

사용하는 설정은 [deploy/cloudbuild.api.yaml](../deploy/cloudbuild.api.yaml)입니다.
빌드 context는 저장소 루트, Dockerfile은 `backend/Dockerfile`입니다.
Cloud Run의 Dockerfile 자동 설정에서 context를 backend로 지정하면
`COPY backend/...` 경로가 어긋나므로 이 프로젝트는 Cloud Build YAML 방식으로 연결합니다.

## 1. GitHub에 설정 반영

앞선 안내로 Push to a branch 배포 trigger를 이미 만들었다면 먼저 해당 trigger를 비활성화하거나 삭제합니다.
Cloud Run의 continuous deployment가 연결돼 있다면 연결된 자동 배포 trigger도 확인합니다.
아래 수동 trigger에는 push/PR 이벤트나 schedule을 연결하지 않습니다.
실행 시점은 Cloud Build trigger의 Event가 결정하며 YAML 파일만으로 수동 실행이 강제되는 것은 아닙니다.

배포할 코드와 `deploy/cloudbuild.api.yaml`이 GitHub main에 있어야 합니다.
로컬에만 있는 파일은 trigger가 읽을 수 없습니다. 작업 branch의 변경을 검토하고 main에 merge합니다.
.env, 비밀번호, API key, .local 자료는 Git에 넣지 않습니다.
실제 DB URL은 기존 Cloud Run의 Secret Manager 참조로 관리합니다.

배포하려는 commit의 GitHub Quality workflow 결과를 확인한 뒤 Run trigger를 누릅니다.
수동 Cloud Build 실행도 GitHub Actions 완료를 자동으로 기다리지 않습니다.
GitHub Actions의 수집 workflow와 품질 workflow는 기존 역할을 유지합니다.

## 2. 빌드 계정 확인과 배포 권한

먼저 성공한 수동 build의 상세 화면에서 Service account를 확인합니다.
기본 계정을 사용했다면 Cloud Shell에서도 확인할 수 있습니다.

```sh
gcloud builds get-default-service-account --project=furbebe-backend --region=asia-northeast3
gcloud run services describe api --project=furbebe-backend --region=asia-northeast3 --format='value(spec.template.spec.serviceAccountName)'
```

첫 결과는 빌드 계정, 두 번째는 API runtime 계정입니다.
두 계정은 책임이 다릅니다. API runtime 계정을 trigger의 빌드 계정으로 선택하지 않습니다.
일반적으로 두 번째는 앞서 만든 `furbebe-api-runtime@furbebe-backend.iam.gserviceaccount.com`이며 실제 조회값을 사용합니다.
성공한 빌드 계정의 source 읽기·이미지 업로드 권한을 유지하고 다음 권한도 확인합니다.

| 대상 | 빌드 계정에 필요한 역할 |
| --- | --- |
| Artifact Registry `furbebe` repository | Artifact Registry Writer |
| Cloud Run `api` 서비스 | Cloud Run Developer |
| API runtime 서비스 계정 | Service Account User |
| `furbebe-backend` 프로젝트 | Logs Writer |

아래 placeholder 두 개를 실제 이메일로 바꾼 뒤 Cloud Shell에서 실행할 수 있습니다.

```sh
FURBEBE_BUILD_SA='실제-빌드-계정-이메일'
FURBEBE_RUNTIME_SA='실제-API-runtime-계정-이메일'

gcloud artifacts repositories add-iam-policy-binding furbebe \
  --project=furbebe-backend --location=asia-northeast3 \
  --member="serviceAccount:$FURBEBE_BUILD_SA" --role=roles/artifactregistry.writer
gcloud run services add-iam-policy-binding api \
  --project=furbebe-backend --region=asia-northeast3 \
  --member="serviceAccount:$FURBEBE_BUILD_SA" --role=roles/run.developer
gcloud iam service-accounts add-iam-policy-binding "$FURBEBE_RUNTIME_SA" \
  --project=furbebe-backend \
  --member="serviceAccount:$FURBEBE_BUILD_SA" --role=roles/iam.serviceAccountUser
gcloud projects add-iam-policy-binding furbebe-backend \
  --member="serviceAccount:$FURBEBE_BUILD_SA" --role=roles/logging.logWriter
```

연결·trigger를 관리하는 사용자도 선택한 빌드 계정에 `iam.serviceAccounts.actAs` 권한이 필요합니다.
새 빌드 계정을 만들 경우 source storage 접근 권한도 별도로 구성합니다.
이 절차는 이미 성공한 수동 build 계정을 재사용하는 경우를 기준으로 합니다.
[배포 권한](https://docs.cloud.google.com/run/docs/reference/iam/roles),
[빌드 계정과 로그](https://docs.cloud.google.com/build/docs/securing-builds/configure-user-specified-service-accounts)

## 3. GitHub 저장소 연결

1. Google Cloud Console에서 프로젝트 `furbebe-backend` 선택.
2. Cloud Build → Repositories에서 GitHub 저장소 연결 흐름 시작.
3. region은 `asia-northeast3` 선택. 2nd gen 연결을 사용하는 경우 같은 region에 connection과 repository 생성.
4. GitHub 로그인·앱 설치 화면에서 `HAYEONryu/furbebe` 저장소 접근 허용.
5. 목록에 해당 repository가 나타나고 연결 상태가 정상인지 확인.

GitHub 로그인·repository 접근 허용은 사용자 계정에서 직접 진행합니다.
Cloud Build API는 이전 수동 build에서 사용한 활성화 상태를 유지합니다.

## 4. 수동 배포 trigger 생성

Cloud Build → Triggers → Create trigger에서 다음 값을 입력합니다.

| 항목 | 값 |
| --- | --- |
| Name | furbebe-api-manual |
| Region | asia-northeast3 |
| Event | Manual invocation (수동 호출) |
| Repository generation | 연결한 저장소와 같은 세대; 새 2nd gen 연결이면 2nd gen |
| Repository | HAYEONryu/furbebe |
| Branch | `main` (정규식이 아닌 브랜치 이름) |
| Configuration | Cloud Build configuration file (YAML or JSON) |
| Configuration location | Repository |
| Configuration file | `deploy/cloudbuild.api.yaml` (루트 기준) |
| Service account | 2절에서 확인한 빌드 계정 |

Cloud Build 설정의 기본 substitution은 `_REGION=asia-northeast3`, `_REPOSITORY=furbebe`, `_SERVICE=api`입니다.
`$PROJECT_ID`, `$COMMIT_SHA`, `$BUILD_ID`는 Cloud Build가 공급하므로 직접 고정하지 않습니다.
이미지 tag는 commit SHA와 build ID를 함께 사용합니다. 같은 commit을 다시 수동 배포해도 별도 tag를 만듭니다.
현재 Cloud Run 서비스 이름은 `api`이며 초기 준비용 YAML의 `furbebe-api`와 구분합니다.
[수동 trigger 생성·실행](https://docs.cloud.google.com/build/docs/manually-build-code-source-repos?generation=2nd-gen),
[빌드 변수](https://docs.cloud.google.com/build/docs/configuring-builds/substitute-variable-values)

## 5. 첫 실행과 확인

Cloud Build → Triggers → `furbebe-api-manual` → Run trigger를 누릅니다.
실행 패널에서 main을 선택하고 Run trigger를 누르면 그 시점의 GitHub 코드를 빌드·배포합니다.
배포할 branch/tag는 실행 패널에서 바꿀 수 있으며 대상 commit과 검사 결과를 확인합니다.
build-api → push-api → update-api 단계와 최종 SUCCESS를 확인합니다.
Artifact Registry의 새 image tag는 `<commit SHA>-<build ID>`이며 Cloud Run revision에서 해당 image digest를 확인합니다.
배포는 기존 `api`의 image만 갱신합니다. Secret 참조·환경변수·runtime 계정·포트·리소스·ingress는 기존 설정을 사용합니다.
새 서비스 생성, 공개 권한 변경, DB migration·수집, 프런트엔드 배포는 이 설정에서 실행하지 않습니다.
traffic이 기존 특정 revision에 고정돼 있다면 새 revision이 생성돼도 실제 요청 대상이 바뀌지 않을 수 있으므로 traffic도 확인합니다.

현재 접근 경로에서 `/health`와 실제 목록·상세 API를 확인합니다.
`/health`는 DB 연결 점검이므로 Cloud Build SUCCESS만으로 데이터 조회까지 성공했다고 판단하지 않습니다.
배포 버튼을 겹쳐 누르면 이전 build가 나중에 끝날 수 있습니다. 진행 중인 배포가 끝난 뒤 다음 실행을 시작하고,
배포된 commit을 확인합니다. 장애 시 Cloud Run의 검증된 이전 revision으로 traffic을 되돌립니다.
로그와 [배포 후 점검표](../deploy/production-smoke-checklist.md)를 함께 사용합니다.
