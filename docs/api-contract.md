> Repository contract snapshot; implementation status updated 2026-09-21.
> Latest user decisions: size A (5/10/20kg), age A (0-1/2-4/5-8/9+), omit animals_active in v1.
> Provide optional source-backed behavior/health descriptions; no inferred traits or diagnoses.
> Region fields use official codes: sido=upr_cd, sigungu=org_cd; names appear in display.
> Preserve source processState separately; the approved 10-calendar-day notice-start policy controls display.
> Phase 5 implements all seven GET endpoints below. Verification and operational policies: [Phase 5 report](phase5-read-api.md).
> Example counts and animal values below are illustrative, not current DEV observations.
> Age and display state are calculated using the request's Asia/Seoul date; new_today counts first_seen_at within that KST day.

# FURBEBE FastAPI v1 — 확정 API Contract

> 목적: FURBEBE 1차 Frontend와 Backend 사이의 HTTP 계약을 고정한다.
> Base path: `/api/v1`
> Format: JSON UTF-8
> Date: `YYYY-MM-DD`
> Datetime: ISO-8601 UTC 또는 offset 포함
> ID: UUID string
> 필드가 존재하지만 값이 알려지지 않은 경우 `null`.
> API에 근거가 없는 값을 임의 생성하지 않는다.

---

# 1. 공통 규칙

## 1.1 API Domain

Production:

```text
https://api.furbebe.com
```

Frontend는 Cloud Run 기본 URL을 직접 사용하지 않는다.

---

## 1.2 Content Type

Request body가 있을 경우:

```http
Content-Type: application/json
```

Response:

```http
Content-Type: application/json; charset=utf-8
```

---

## 1.3 Request ID

Backend는 가능하면 모든 응답에:

```http
X-Request-ID: <uuid>
```

를 반환한다.

클라이언트가 valid `X-Request-ID`를 보내면 재사용 가능하되, 없으면 서버 생성.

---

## 1.4 Null 정책

정보 없음:

```json
null
```

사용.

다음과 같이 가짜 값을 만들지 않는다.

```json
"weight_kg": 0
"breed": "알 수 없음"
```

`알 수 없음`은 Frontend presentation에서 처리한다.

---

## 1.5 Enum 정책

API 자체 enum:

```text
sex:
  male
  female
  unknown

neutered:
  yes
  no
  unknown

tag.type:
  fact
  trait
  vibe

size_group:
  tiny
  small
  medium
  large
  unknown

age_group:
  puppy
  young
  adult
  senior
  unknown

tag_match:
  any
  all

sort:
  recent
  notice_end
  weight_asc
  weight_desc
  age_youngest
  age_oldest
```

`process_state`는 Phase 1에서 source value를 확인한 후에도 v1에서는 raw display string을 유지한다.

원문 상태는 DB에 보존하고, 응답·필터·메타에는 승인된 표시 정책을 적용한다.
`보호중`이고 공고 시작일로부터 KST 달력 기준 10일 이상 경과하면 `입양 가능`,
그 밖에는 원문을 유지한다. 공고 시작일이 없거나 미래이면 `입양 가능`으로 바꾸지 않는다.

즉 source의 새로운 상태값 때문에 API enum이 깨지지 않도록:

```json
"process_state": "보호중"
```

형태.

---

# 2. Project-derived size_group

공식 분류가 아니라 FURBEBE 내부 탐색 기준이다.

Phase 1 프로파일링 후 사용자 승인으로 v1 기준을 확정했다.

확정 기준:

```text
tiny   : weight_kg <= 5
small  : 5 < weight_kg <= 10
medium : 10 < weight_kg <= 20
large  : weight_kg > 20
unknown: weight_kg null
```

Frontend에는 공식 견종 크기 분류라고 표시하지 않는다.

---

# 3. Project-derived age_group

`birth_year` 기반의 대략적 탐색 그룹.

정확한 생일을 모른다는 점을 전제로 한다.

확정 기준:

```text
puppy  : estimated_age_years <= 1
young  : 2 <= estimated_age_years <= 4
adult  : 5 <= estimated_age_years <= 8
senior : estimated_age_years >= 9
unknown: birth_year null
```

`estimated_age_years`는 요청 시 Asia/Seoul 연도 - birth_year 기준의 대략값이며 별도 응답 필드가 아니다.

API Detail에는 원본 `age_text`와 `birth_year`를 함께 제공한다.

---

# 4. Error Envelope

모든 명시적 API error는 가능한 한 같은 구조를 사용한다.

```json
{
  "error": {
    "code": "ANIMAL_NOT_FOUND",
    "message": "Animal not found",
    "details": null,
    "request_id": "a56d0f4c-8983-4f6d-a47e-6f66fead2313"
  }
}
```

## Error codes

```text
INVALID_REQUEST
VALIDATION_ERROR
ANIMAL_NOT_FOUND
TAG_NOT_FOUND
SERVICE_UNAVAILABLE
INTERNAL_ERROR
```

500 응답에서 내부 traceback/SQL/secret 반환 금지.

---

# 5. Validation Error — 422

예:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "page_size",
        "message": "Input should be less than or equal to 60"
      }
    ],
    "request_id": "a56d0f4c-8983-4f6d-a47e-6f66fead2313"
  }
}
```

FastAPI 기본 validation response를 그대로 노출하지 않고 application error envelope로 변환한다.

---

# 6. Shared Model — Image

```json
{
  "url": "http://openapi.animal.go.kr/example.jpg",
  "order": 1,
  "type": "source"
}
```

Fields:

```text
url   string, required
order integer, required, >= 1
type  "source" | "adoption"
```

---

# 7. Shared Model — Tag

```json
{
  "key": "cautious",
  "type": "trait",
  "label": "낯가림",
  "emoji": "🙈",
  "confidence": 0.95,
  "evidence": "사람을 매우 경계함"
}
```

Fields:

```text
key         string
type        fact | trait | vibe
label       string
emoji       string|null
confidence  number 0.0~1.0
evidence    string|null
```

Frontend는 `confidence`를 확률이라고 표현하지 않는다.

---

# 8. Shared Model — Region

```json
{
  "sido": "5690000",
  "sigungu": "5690000",
  "display": "세종특별자치시"
}
```

Fields nullable.

`sido`는 공식 `upr_cd`, `sigungu`는 공식 `org_cd`다. 이름은 `display`에 제공한다.
Phase 5는 기존 공식 참조 자료로 만든 버전 고정 매핑과 source `orgNm`을 대조한다.
매핑에 없는 지역은 코드를 추정하지 않고:

```json
{
  "sido": null,
  "sigungu": null,
  "display": "세종특별자치시"
}
```

처럼 display raw fallback 허용.

---

# 9. Shared Model — ShelterSummary

```json
{
  "id": "df456c93-1472-4b85-a5ab-9e763377cbb2",
  "name": "세종유기동물보호센터",
  "phone": "010-4435-3720",
  "address": "세종특별자치시 ...",
  "organization": "세종특별자치시"
}
```

모르는 값은 null.

---

# 10. Shared Model — AnimalSummary

목록/비슷한 동물에 사용.

```json
{
  "id": "53ce2984-fb29-4488-bcec-2f579be9294e",
  "notice_no": "세종-세종-2026-00249",
  "breed": "말티즈",
  "breed_full": "[개] 말티즈",
  "sex": "female",
  "birth_year": 2026,
  "age_text": "2026(년생)",
  "age_group": "puppy",
  "weight_kg": 3.1,
  "weight_text": "3.1(Kg)",
  "size_group": "tiny",
  "color_text": "흰색",
  "process_state": "보호중",
  "found_date": "2026-09-09",
  "notice_end": "2026-09-21",
  "region": {
    "sido": "5690000",
    "sigungu": "5690000",
    "display": "세종특별자치시"
  },
  "primary_image": {
    "url": "http://openapi.animal.go.kr/example.jpg",
    "order": 1,
    "type": "source"
  },
  "tags": [
    {
      "key": "tiny",
      "type": "fact",
      "label": "작은 체구",
      "emoji": null,
      "confidence": 1.0,
      "evidence": "3.1kg"
    },
    {
      "key": "bean",
      "type": "vibe",
      "label": "콩만이",
      "emoji": "🫘",
      "confidence": 1.0,
      "evidence": "tiny"
    }
  ]
}
```

`is_favorite`:

1차 favorite는 localStorage이므로 Backend는 favorite를 모른다.

따라서 v1 response에서 필드 자체를 **제외한다**.

Frontend에서 localStorage와 merge한다.

최종 contract에는 `is_favorite`를 반환하지 않는다.

---

# 11. GET /health

Base path 적용하지 않음.

```http
GET /health
```

200:

```json
{
  "status": "ok",
  "service": "furbebe-api",
  "version": "1"
}
```

DB 연결 실패 시:

```http
503
```

```json
{
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "Database unavailable",
    "details": null,
    "request_id": "..."
  }
}
```

Health endpoint는 secret, DB host 등 상세 인프라 정보를 반환하지 않는다.

---

# 12. GET /api/v1/animals

동물 탐색 목록.

## Query parameters

```text
page
  integer
  default 1
  min 1

page_size
  integer
  default 24
  min 1
  max 60

sido
  string|null, official upr_cd

sigungu
  string|null, official org_cd

breed
  string|null

sex
  male|female|unknown|null

neutered
  yes|no|unknown|null

size_group
  tiny|small|medium|large|unknown|null

age_group
  puppy|young|adult|senior|unknown|null

tag
  repeated string
  example:
  ?tag=cream&tag=cautious

tag_match
  any|all
  default any

process_state
  string|null
  exact value from meta filters

q
  string|null
  max 50
  initial scope:
  breed / shelter name / region display
  full text search engine는 사용하지 않음

sort
  recent
  notice_end
  weight_asc
  weight_desc
  age_youngest
  age_oldest
  default recent
```

### recent definition

우선순위:

```text
found_date DESC
source_updated_at DESC
id
```

정확한 SQL 정렬은 deterministic하게 tie breaker를 둔다.

---

## Request example

```http
GET /api/v1/animals?page=1&page_size=24&sido=5690000&size_group=tiny&tag=puppy&sort=recent
```

GET body 없음.

---

## 200 Response

```json
{
  "items": [
    {
      "id": "53ce2984-fb29-4488-bcec-2f579be9294e",
      "notice_no": "세종-세종-2026-00249",
      "breed": "말티즈",
      "breed_full": "[개] 말티즈",
      "sex": "female",
      "birth_year": 2026,
      "age_text": "2026(년생)",
      "age_group": "puppy",
      "weight_kg": 3.1,
      "weight_text": "3.1(Kg)",
      "size_group": "tiny",
      "color_text": "흰색",
      "process_state": "보호중",
      "found_date": "2026-09-09",
      "notice_end": "2026-09-21",
      "region": {
        "sido": "5690000",
        "sigungu": "5690000",
        "display": "세종특별자치시"
      },
      "primary_image": {
        "url": "http://openapi.animal.go.kr/example.jpg",
        "order": 1,
        "type": "source"
      },
      "tags": [
        {
          "key": "tiny",
          "type": "fact",
          "label": "작은 체구",
          "emoji": null,
          "confidence": 1.0,
          "evidence": "3.1kg"
        },
        {
          "key": "bean",
          "type": "vibe",
          "label": "콩만이",
          "emoji": "🫘",
          "confidence": 1.0,
          "evidence": "tiny"
        }
      ]
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 24,
    "total": 124,
    "total_pages": 6,
    "has_next": true,
    "has_previous": false
  },
  "applied_filters": {
    "sido": "5690000",
    "sigungu": null,
    "breed": null,
    "sex": null,
    "neutered": null,
    "size_group": "tiny",
    "age_group": null,
    "tags": ["puppy"],
    "tag_match": "any",
    "process_state": null,
    "q": null,
    "sort": "recent"
  }
}
```

Empty result:

```http
200
```

```json
{
  "items": [],
  "pagination": {
    "page": 1,
    "page_size": 24,
    "total": 0,
    "total_pages": 0,
    "has_next": false,
    "has_previous": false
  },
  "applied_filters": {
    "sido": null,
    "sigungu": null,
    "breed": null,
    "sex": null,
    "neutered": null,
    "size_group": null,
    "age_group": null,
    "tags": [],
    "tag_match": "any",
    "process_state": null,
    "q": "존재하지않는검색어",
    "sort": "recent"
  }
}
```

---

# 13. GET /api/v1/animals/{animal_id}

## Path

```text
animal_id UUID
```

Invalid UUID:

```http
422
```

Not found:

```http
404
```

```json
{
  "error": {
    "code": "ANIMAL_NOT_FOUND",
    "message": "Animal not found",
    "details": null,
    "request_id": "..."
  }
}
```

---

## 200 Response

```json
{
  "id": "53ce2984-fb29-4488-bcec-2f579be9294e",
  "source": {
    "provider": "국가동물보호정보시스템",
    "source_id": "469569202600608",
    "source_updated_at": "2026-09-09T21:12:10+09:00"
  },
  "notice": {
    "notice_no": "세종-세종-2026-00249",
    "start_date": "2026-09-09",
    "end_date": "2026-09-21",
    "process_state": "보호중",
    "end_reason": null
  },
  "animal": {
    "species": "dog",
    "breed": "말티즈",
    "breed_full": "[개] 말티즈",
    "sex": "female",
    "neutered": "no",
    "birth_year": 2026,
    "age_text": "2026(년생)",
    "age_group": "puppy",
    "weight_kg": 3.1,
    "weight_text": "3.1(Kg)",
    "size_group": "tiny",
    "color_text": "흰색",
    "rfid_code": null
  },
  "found": {
    "date": "2026-09-09",
    "place": "세종시 대평동 698",
    "region": {
      "sido": "5690000",
      "sigungu": "5690000",
      "display": "세종특별자치시"
    }
  },
  "images": [
    {
      "url": "http://openapi.animal.go.kr/example-1.jpg",
      "order": 1,
      "type": "source"
    },
    {
      "url": "http://openapi.animal.go.kr/example-2.jpg",
      "order": 2,
      "type": "source"
    }
  ],
  "tags": [
    {
      "key": "white",
      "type": "fact",
      "label": "흰색",
      "emoji": null,
      "confidence": 1.0,
      "evidence": "흰색"
    },
    {
      "key": "cloud",
      "type": "vibe",
      "label": "구름이",
      "emoji": "☁️",
      "confidence": 1.0,
      "evidence": "white"
    }
  ],
  "descriptions": {
    "special_mark": "보람119안전센터인계",
    "social": null,
    "health": null,
    "etc": null,
    "vaccination": null,
    "health_check": null
  },
  "shelter": {
    "id": "df456c93-1472-4b85-a5ab-9e763377cbb2",
    "name": "세종유기동물보호센터",
    "phone": "010-4435-3720",
    "address": "세종특별자치시 ...",
    "organization": "세종특별자치시"
  },
  "adoption_promotion": null,
  "first_seen_at": "2026-09-09T12:13:20Z",
  "last_seen_at": "2026-09-11T04:00:02Z"
}
```

---

# 14. adoption_promotion object

source API에 관련 값이 있을 때:

```json
{
  "title": "새 가족을 기다립니다",
  "start_date": "2026-09-10",
  "end_date": "2026-09-30",
  "condition_text": "입양 조건 원문",
  "description": "입양 홍보 원문",
  "image_url": "https://example.com/adoption.jpg"
}
```

전부 비어 있으면:

```json
"adoption_promotion": null
```

부분 값만 있으면 object를 만들고 없는 field는 null.

원문을 AI로 재작성하지 않는다.

---

# 15. GET /api/v1/animals/{animal_id}/similar

Query:

```text
limit
  integer
  default 4
  min 1
  max 12
```

200:

```json
{
  "source_animal_id": "53ce2984-fb29-4488-bcec-2f579be9294e",
  "items": [
    {
      "id": "4e20a49d-dca2-48c5-b8b4-60b785a39edc",
      "notice_no": "세종-세종-2026-00250",
      "breed": "믹스견",
      "breed_full": "[개] 믹스견",
      "sex": "male",
      "birth_year": 2024,
      "age_text": "2024(년생)",
      "age_group": "young",
      "weight_kg": 16.4,
      "weight_text": "16.4(Kg)",
      "size_group": "medium",
      "color_text": "갈색",
      "process_state": "보호중",
      "found_date": "2026-09-09",
      "notice_end": "2026-09-21",
      "region": {
        "sido": "5690000",
        "sigungu": "5690000",
        "display": "세종특별자치시"
      },
      "primary_image": {
        "url": "http://openapi.animal.go.kr/example.jpg",
        "order": 1,
        "type": "source"
      },
      "tags": []
    }
  ]
}
```

추천 score는 response에 기본 노출하지 않는다.

동일 animal 제외.

없는 animal:

```http
404 ANIMAL_NOT_FOUND
```

---

# 16. GET /api/v1/tags

Query:

```text
type
  fact|trait|vibe|null

active_only
  boolean
  default true
```

200:

```json
{
  "items": [
    {
      "key": "cloud",
      "type": "vibe",
      "label": "구름이",
      "emoji": "☁️",
      "description": "흰색 계열의 아이를 위한 탐색 태그"
    },
    {
      "key": "cautious",
      "type": "trait",
      "label": "낯가림",
      "emoji": "🙈",
      "description": "제공된 설명에 사람에 대한 경계 표현이 있는 경우"
    }
  ]
}
```

Tag list의 description은 운영자가 작성한 설명.
동물별 evidence와 다르다.

---

# 17. GET /api/v1/meta/filters

Frontend filter option의 source of truth.

하드코딩된 보호소/품종/상태 목록을 Frontend에 넣지 않는다.

200:

```json
{
  "regions": [
    {
      "sido": "5690000",
      "sigungu": ["5690000"]
    },
    {
      "sido": "6480000",
      "sigungu": ["5410000", "5480000", "5670000"]
    }
  ],
  "breeds": [
    {
      "value": "믹스견",
      "count": 820
    },
    {
      "value": "말티즈",
      "count": 76
    }
  ],
  "sexes": [
    {
      "value": "male",
      "label": "수컷"
    },
    {
      "value": "female",
      "label": "암컷"
    },
    {
      "value": "unknown",
      "label": "미상"
    }
  ],
  "neutered": [
    {
      "value": "yes",
      "label": "중성화 완료"
    },
    {
      "value": "no",
      "label": "중성화 안 됨"
    },
    {
      "value": "unknown",
      "label": "미상"
    }
  ],
  "size_groups": [
    {
      "value": "tiny",
      "label": "아주 작아요"
    },
    {
      "value": "small",
      "label": "작아요"
    },
    {
      "value": "medium",
      "label": "중간"
    },
    {
      "value": "large",
      "label": "커요"
    }
  ],
  "age_groups": [
    {
      "value": "puppy",
      "label": "아가댕"
    },
    {
      "value": "young",
      "label": "어린 친구"
    },
    {
      "value": "adult",
      "label": "성견"
    },
    {
      "value": "senior",
      "label": "시니어"
    }
  ],
  "process_states": [
    {
      "value": "보호중",
      "label": "보호중",
      "count": 1200
    }
  ]
}
```

`process_states`는 DB에서 실제 관찰한 상태에 승인된 KST 표시 정책을 적용해 집계한다.
`regions`의 `sido`·`sigungu`도 공식 코드이며 목록 필터 요청에 그대로 사용할 수 있다.
품종과 옵션은 실제 데이터에 존재하는 값만 반환한다.

Phase 7에서는 지역별 `sido_label`(문자열 또는 null)과 `sigungu_labels`(코드 → 이름 object)를
추가했다. 기존 `sido`·`sigungu`의 값과 자료형은 유지한다. 새 이름 필드는 backend의 기존 공식
지역 매핑에서 가져오며, frontend에서 지역 전체 목록을 별도로 관리하지 않는다.
세종처럼 시군구 코드가 시도와 같고 별도 시군구 이름이 없는 경우 시도 이름을 표시한다.

```json
{
  "sido": "5690000",
  "sigungu": ["5690000"],
  "sido_label": "세종특별자치시",
  "sigungu_labels": { "5690000": "세종특별자치시" }
}
```

UI에는 label을 표시하고 요청 URL에는 code를 전달한다. 위 값은 응답 모양을 설명하는 예시이며
frontend에 하드코딩할 목록이 아니다. `/dogs`는 사용자 결정에 따라 이 API의 전체 구조동물을 표시한다.

---

# 18. GET /api/v1/stats/overview

Main Hero/Quick Discovery용.

200:

```json
{
  "animals_total": 2450,
  "new_today": 73,
  "with_primary_image": 2291,
  "last_synced_at": "2026-09-11T04:00:02Z"
}
```

Confirmed 2026-09-15: animals_active is omitted from the v1 response.
Recorded protecting-state counts do not establish current adoption availability.
Other response fields retain the original contract.

`new_today`는 요청 시 Asia/Seoul 오늘 00:00 이상, 다음 날 00:00 미만의 `first_seen_at` 수다.
`last_synced_at`는 `status=success`인 sync_runs의 최신 `finished_at`이며 없으면 null이다.
`with_primary_image`는 API가 지원하는 source/adoption 이미지가 하나 이상 있는 동물 수다.

---

# 19. Cache policy

Public read endpoint 권장:

```text
GET /animals                 Cache-Control: public, max-age=60
GET /animals/{id}            public, max-age=300
GET /animals/{id}/similar    public, max-age=300
GET /tags                    public, max-age=600
GET /meta/filters            public, max-age=600
GET /stats/overview          public, max-age=60
```

실제 Cloudflare caching은 별도 deployment 설정에서 적용 가능.
Phase 5는 날짜 파생값이 오래 남지 않도록 위 TTL을 KST 다음 자정까지의 초 이내로 제한한다.

개인정보가 생기는 2차 API에는 이 정책을 자동 적용하지 않는다.

---

# 20. OpenAPI / Swagger

FastAPI 자동 문서:

Development/Staging:

```text
/docs
/openapi.json
```

Production은 공개 여부를 설정으로 결정한다.

Pydantic response model을 모든 endpoint에 명시한다.

Swagger 예시가 이 문서 JSON과 맞도록 `json_schema_extra`를 사용할 수 있다.

---

# 21. API Response model naming

권장 Pydantic schema:

```text
AnimalSummaryResponse
AnimalDetailResponse
AnimalListResponse
SimilarAnimalsResponse

ImageResponse
TagAssignmentResponse
RegionResponse
ShelterResponse
AdoptionPromotionResponse

PaginationResponse
AppliedAnimalFiltersResponse
TagListResponse
FilterMetaResponse
OverviewStatsResponse

ApiErrorResponse
ValidationErrorDetail
```

DB ORM model을 그대로 JSON serialize하지 않는다.

---

# 22. Source data privacy / exposure

Detail에서 노출 가능:

```text
notice_no
source provider
source_id
source_updated_at
```

다음 raw payload 전체는 사용자 API로 반환하지 않는다.

```text
raw_payload
```

필요 시 운영 debugging에서만 사용.

---

# 23. Query security

`sort`는 enum whitelist.
사용자 string을 SQL ORDER BY에 직접 삽입하지 않는다.

`page_size <= 60`.

`q <= 50`.

Tag key는 DB parameter binding.

모든 SQLAlchemy query parameterized.

---

# 24. N+1 방지

`GET /animals`에서 각 card마다 별도 query 금지.

목록 query에서:

```text
primary image
tags
region/shelter 필요한 최소값
```

을 효율적으로 eager load 또는 aggregate.

24 cards 때문에:

```text
1 + 24 images + 24 tags + 24 shelters
```

query가 발생하지 않게 test/log로 확인.

---

# 25. Pagination 정책

v1은 offset/page pagination으로 시작.

```text
page
page_size
```

트래픽/row 수가 커지면 cursor pagination은 v2 또는 backward compatible 확장으로 검토.

정렬 tie breaker 필수.

---

# 26. Frontend handling rules

Frontend는:

```text
null
empty array
404
422
500/503
```

를 정상적으로 처리한다.

예:

```text
primary_image = null
→ FURBEBE ImageEmptyState

tags = []
→ 태그 영역 숨김

shelter.phone = null
→ 전화 CTA disabled/hidden

adoption_promotion = null
→ 섹션 숨김
```

데이터가 없다고 가짜 문구를 API response에 삽입하지 않는다.

---

# 27. API Contract tests

Backend pytest에서 최소:

```text
GET /health 200
GET /animals default
GET /animals pagination
GET /animals max page size validation
GET /animals multiple tag query
GET /animals empty
GET /animals invalid enum 422
GET /animals/{id} 200
GET /animals/{id} 404
GET /animals invalid UUID 422
GET /similar excludes self
GET /tags
GET /meta/filters
GET /stats/overview
error envelope format
null field serialization
```

Frontend contract fixture도 같은 JSON structure 사용.

---

# 28. Phase 1 결과로 launch 전에 확정할 마지막 항목

다음 5개만 profiling 후 수정 가능:

```text
1. size_group thresholds
2. age_group thresholds
3. normalized region logic
4. processState UI meaning
5. stats.animals_active definition
```

이외 v1 JSON shape는 가능한 유지한다.

---

# 29. Codex FastAPI 구현 프롬프트

```text
FURBEBE FastAPI v1을 첨부 API Contract대로 구현해.

중요:
- API JSON field 이름과 null 정책을 임의 변경하지 마.
- ORM model을 그대로 response로 쓰지 말고 Pydantic response schema를 분리해.
- router → service → repository → SQLAlchemy 구조를 지켜.
- Frontend는 DB에 직접 접근하지 않는다.
- `/api/v1` version prefix를 유지해.
- error response는 공통 envelope로 변환해.
- FastAPI validation error도 FURBEBE error envelope로 변환해.
- query parameter에 max length/max page size를 적용해.
- 목록 endpoint에서 N+1 query를 만들지 마.
- raw_payload는 API로 반환하지 마.
- API에 근거 없는 성격/건강/입양상태를 생성하지 마.
- process_state는 profiling 전 임의 enum mapping하지 마.
- adoption_promotion은 nullable object로 구현해.
- Pydantic response model과 pytest contract test를 함께 작성해.

구현하기 전에:
1. 기존 DB model 확인
2. Phase 1 profiling 결과 확인
3. 이 Contract와 충돌하는 부분 목록
4. 변경 예정 파일
을 먼저 보고해.

충돌이 있으면 임의로 Contract를 바꾸지 말고 사용자에게 알려.
```
