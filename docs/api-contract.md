# FastAPI 읽기 API

기준: backend/app/api/animals.py, schemas/animals.py, repositories/animals.py.
운영 origin은 https://api.furbebe.site, 로컬은 http://127.0.0.1:8080입니다.
GET 전용 공개 읽기 API이며 인증·DB 쓰기·입양 신청 endpoint는 없습니다.

## endpoint

| GET 경로 | 응답·목적 | 최대 Cache-Control |
| --- | --- | --- |
| /health | 실제 DB SELECT 1 연결 확인 | 별도 cache 지정 없음 |
| /api/v1/animals | items, pagination, applied_filters | 60초 |
| /api/v1/animals/{animal_id} | 상세 | 300초 |
| /api/v1/animals/{animal_id}/similar | source_animal_id, items | 300초 |
| /api/v1/tags | items 태그 사전 | 600초 |
| /api/v1/meta/filters | 현재 활성 개에서 집계한 필터 옵션 | 600초 |
| /api/v1/stats/overview | 전체·오늘 신규·사진·마지막 성공 수집 | 60초 |

캐시는 KST 다음 자정까지 남은 시간과 위 값 중 작은 값입니다.
정적 서버 캐시나 자정 뒤 파생 나이·상태가 그대로라는 뜻이 아닙니다.
모든 응답에 UUID X-Request-ID가 붙습니다. 유효 UUID를 요청 header로 보내면 재사용합니다.

## 목록 query

```sh
curl --fail --silent 'http://127.0.0.1:8080/api/v1/animals?page=1&page_size=24&process_state=%EC%9E%85%EC%96%91%20%EA%B0%80%EB%8A%A5&tag=gentle&tag=white_coat&tag_match=all'
```

| query | 기본 / 허용 값 |
| --- | --- |
| page | 1; 양의 정수 |
| page_size | 24; 1~60 |
| sido / sigungu | 지역 코드; meta의 값 사용 |
| breed | DB 품종 exact match |
| sex | male / female / unknown |
| neutered | yes / no / unknown |
| size_group | tiny / small / medium / large / unknown |
| age_group | puppy / young / adult / senior / unknown |
| process_state | 계산된 표시 상태 문자열; 미지정은 모든 활성 개 |
| tag | 반복 query, 중복 key 제거 |
| tag_match | any / all; 기본 any |
| q | 최대 50자, 공고번호·품종·관할기관·보호소 부분 검색 |
| sort | recent / notice_end / weight_asc / weight_desc / age_youngest / age_oldest |

알 수 없는 query 이름·enum·형식은 422입니다. 알 수 없는 tag key는 404 TAG_NOT_FOUND입니다.
비활성으로 사전에 남은 key는 “알 수 없는 key”가 아니며 활성 배정이 없어 검색 결과가 비어 있을 수 있습니다.
q의 %, _, 역슬래시는 SQL wildcard가 아닌 literal 문자로 처리합니다.
검색과 exact match는 parameter binding을 사용합니다.

recent는 found_date 내림차순입니다. 다른 정렬은 이름에 해당하는 컬럼 순서입니다.
null은 뒤로, 동률은 source_updated_at 내림차순 → UUID 오름차순으로 정렬합니다.
범위를 벗어난 page는 빈 items와 실제 total을 반환합니다.

**API는 상태 기본 필터가 없습니다. 프런트엔드는 입양 가능을 기본 query로 전달합니다.**
UI의 process_state=all은 API에 전달하지 않고 상태 query를 생략합니다.

## 파생 값

- 공개 조건: species=dog, is_active=true.
- 표시 상태: 보호중 + notice_start ≤ 한국 오늘-10일 → 입양 가능.
- size_group: ≤5 tiny, >5~10 small, >10~20 medium, >20 large; null unknown.
- age_group: 현재 한국 연도-출생연도 기준 0~1 puppy, 2~4 young, 5~9 adult, 10+ senior; null unknown.
- 미래 출생연도는 정규화에서 null 처리합니다. 정확한 생일·만 나이를 추정하지 않습니다.
- region: 공백 정리한 raw orgNm을 backend/app/data/regions.json으로 연결; 미매칭 코드는 null, 원문 표시 유지.

몸집 태그 경계는 size_group과 다릅니다. [태그 생성](tag-generation.md)을 확인합니다.

## 응답 필드

| 모델 | 구성 |
| --- | --- |
| 목록 items | id, notice_no, breed/breed_full, sex, birth_year/age_text/age_group, weight_kg/weight_text/size_group, color_text, process_state, found_date, notice_end, region, primary_image, image_candidates, tags |
| pagination | page, page_size, total, total_pages, has_next, has_previous |
| applied_filters | query 반영; tag는 tags 배열로 반환, page/page_size 제외 |
| region | sido, sigungu, display; 모두 nullable |
| image | url, order(1부터), type(source/adoption) |
| tag 배정 | key, type, label, emoji, confidence, evidence |
| 상세 | id, source, notice, animal, found, images, tags, descriptions, shelter, adoption_promotion, first_seen_at, last_seen_at |
| source | provider, source_id, source_updated_at |
| notice | notice_no, start_date, end_date, process_state, end_reason |
| animal | species, breed/breed_full, sex, neutered, birth_year/age_text/age_group, weight_kg/weight_text/size_group, color_text, rfid_code |
| found | date, place, region |
| descriptions | special_mark, social, health, etc, vaccination, health_check |
| shelter | id, name, phone, address, organization; 없으면 null |
| adoption_promotion | title, start_date, end_date, condition_text, description, image_url; 모두 없으면 null |
| 태그 사전 items | key, type, label, emoji, description |
| overview | animals_total, new_today, with_primary_image, last_synced_at |

raw_payload, DB URL, rule_id/generator/version은 공개 응답에 포함하지 않습니다.
이미지·태그는 활성 행만 제공합니다. image_candidates는 source 사진만 포함합니다.
DB null은 계약에 따라 null 또는 빈 배열로 전달하며 미상 데이터의 사실값을 만들어 채우지 않습니다.
현재 API에는 safety_badges 필드가 없습니다.

날짜는 YYYY-MM-DD, timestamp는 timezone 포함 ISO 형식입니다.
new_today는 발견일이 아니라 first_seen_at이 한국 오늘에 속한 활성 개 수입니다.
last_synced_at은 성공 sync_runs의 마지막 종료 시각입니다.

## 유사 동물

limit 기본 4, 범위 1~12. 원본 동물은 제외하며 공개 활성 개만 후보입니다.

| 일치 | 점수 |
| --- | --- |
| 같은 시도 | +3 |
| 같은 체중 그룹 | +2 |
| 같은 품종 | +2 |
| 같은 성별 | +1 |
| 같은 나이 그룹 | +1 |
| 공유 활성 태그 | key마다 +2 |

unknown/null 사실값은 해당 일치 점수를 주지 않습니다.
총점 내림차순 뒤 recent 정렬을 적용합니다. 점수가 낮아도 반환할 수 있으며 추천 정확도를 보장하지 않습니다.

## 태그와 필터 메타

/tags의 type은 fact/trait/vibe, active_only 기본 true입니다.
등록 사전을 반환하므로 실제 배정 수와 연결된 “인기 태그” API가 아닙니다.
meta는 regions(코드와 label), breeds(value/count), sexes, neutered, size_groups, age_groups,
process_states(value/label/count)를 반환합니다. 현재 자료에 존재하는 옵션만 나옵니다.
지역 label을 프런트엔드에서 별도 하드코딩하지 않습니다.

## 오류

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [{"field": "page", "message": "Invalid value"}],
    "request_id": "00000000-0000-4000-8000-000000000000"
  }
}
```

| HTTP | code | 의미 |
| --- | --- | --- |
| 404 | ANIMAL_NOT_FOUND | UUID는 유효하지만 공개 동물 없음 |
| 404 | TAG_NOT_FOUND | 사전에 없는 요청 key |
| 422 | VALIDATION_ERROR | query 또는 UUID 검증 실패 |
| 503 | SERVICE_UNAVAILABLE | 미설정 DB·연결·조회 실패 |
| 500 | INTERNAL_ERROR | 예상하지 못한 서버 오류 |
| 404/405 등 | INVALID_REQUEST | 없는 경로·허용하지 않는 HTTP method |

오류는 입력 원문·SQL·비밀번호·예외 repr을 반환하지 않습니다.
CORS는 정확한 FRONTEND_ORIGIN에 GET, Content-Type/X-Request-ID를 허용하고 credentials를 사용하지 않습니다.
CORS는 API 인증 또는 요청량 제한 기능이 아닙니다.
APP_ENV=production은 docs/OpenAPI를 끕니다. 개발의 /openapi.json을 상세 모델 확인에 사용할 수 있습니다.
