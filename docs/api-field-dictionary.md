# 원천 필드와 정규화 사전

원천 endpoint:
https://apis.data.go.kr/1543061/abandonmentPublicService_v2/abandonmentPublic_v2

원천 전체 측정표가 아닌 **현재 코드의 사용 필드** 안내입니다.
실제 필드 출현·형식 분포는 [분석 도구](source-analysis.md)의 실행별 비공개 보고서에서 확인합니다.

## 동물 식별과 기본 사실

| 원천 | 내부 컬럼/용도 | 규칙 |
| --- | --- | --- |
| desertionNo | source_id | 유의미한 문자열 필수; source와 UNIQUE |
| noticeNo | notice_no | 공고번호; 내부 UUID와 다름 |
| rfidCd | rfid_code | 원문 |
| upKindCd / upKindNm | species | 417000/개 → dog, 422400/고양이 → cat, 429900/기타 → other; 충돌 null |
| kindNm / kindFullNm | breed / breed_full | 원문 |
| kindCd | raw_payload | 공식 코드 분석에 사용; 별도 품종 코드 컬럼 없음 |
| sexCd | sex | M male / F female / Q unknown; 다른 값 null |
| neuterYn | neutered | Y yes / N no / U unknown; 다른 값 null |
| age | age_text / birth_year | YYYY(년생), YYYY(60일미만)(년생); 현재 연도 이하 |
| weight | weight_text / weight_kg | 부호·소수 허용 숫자(Kg); 음수·미해석 null |
| colorCd | color_text | 털색 태그 입력, 원문 보존 |

체중은 “5(Kg)” 형식을 해석하며 단순 “5”, “5kg”, 범위나 혼합 문구는 추측하지 않습니다.
출생연도는 정확한 생일이 아닙니다. 숫자 파싱 실패는 원문을 지우지 않습니다.
species를 정규화할 수 있어도 공개 수집은 개만 대상입니다.

## 날짜·상태·설명

| 원천 | 내부 |
| --- | --- |
| happenDt / happenPlace | found_date / found_place |
| noticeSdt / noticeEdt | notice_start / notice_end |
| processState / endReason | process_state / end_reason |
| updTm | raw_payload + timezone-aware인 경우 source_updated_at |
| specialMark | special_mark |
| sfeSoci / sfeHealth | social_text / health_text |
| etcBigo | etc_text |
| vaccinationChk / healthChk | vaccination_text / health_check_text |

날짜 parser는 YYYYMMDD, YYYY-MM-DD, 정해진 초 단위 ISO timestamp(+offset/Z 포함 가능)를 지원합니다.
잘못된 날짜는 null입니다. updTm에 offset이 없으면 UTC/KST를 추정하지 않고 품질 이슈를 기록합니다.
원천 processState는 그대로 저장하고 표시 상태는 notice_start와 KST 날짜로 조회 시 계산합니다.

텍스트는 앞뒤 공백을 정리하고 빈 값, ., -, 없음, 미상, unknown, null, n/a를 null로 정규화합니다.
단어 “없음”만 있는 설명과 “입질 없음” 같은 문장은 다릅니다. 문장 내 부정은 태그 규칙에서 판단합니다.
건강 원문은 설명으로 제공하며 진단을 추가하지 않습니다.

## 보호소·지역·이미지

| 원천 | 내부·용도 |
| --- | --- |
| careRegNo | shelter source_id; 없으면 연결된 보호소 없음 |
| careNm / careTel / careAddr | shelters.name / phone / address |
| careOwnerNm / orgNm | shelters.owner_name / organization |
| orgNm | raw_payload에서 현재 API 지역 연결·검색 |
| popfile1~popfile8 | animal_images, source 순서 |
| adptnImg | raw_payload에서 adoption_promotion.image_url |

이미지는 공백 정리 후 host가 있고 자격증명이 없는 HTTP(S) URL만 사용합니다.
원천 순서대로 중복 제거하며 실제 다운로드·가용성 검증은 정규화에서 하지 않습니다.
HTTP를 HTTPS로 자동 바꾸거나 이미지를 별도 Storage에 복제하지 않습니다.
원천 adptnImg는 홍보 객체의 URL이며 일반 수집의 source 이미지 reconciliation과 구분합니다.

지역 참조 분석은 sido_v2.orgCd를 시도, sigungu_v2.orgCd를 시군구로 사용하고 uprCd로 소속을 확인합니다.
실제 읽기 API는 저장소의 정적 regions.json을 기관명과 연결하므로 참조 분석 결과를 자동 import하지 않습니다.

## 홍보·추가 필드

adptnTitle, adptnSDate, adptnEDate, adptnConditionLimitTxt, adptnTxt, adptnImg는 raw_payload에 보존하고
API에서 nullable adoption_promotion으로 직렬화합니다. adptnTxt는 행동 태그 입력에도 사용됩니다.
엄격하게 정의되지 않은 추가 필드도 raw_payload에 유지합니다.
인증정보와 key echo는 수신 redactor가 제거합니다. 원천 설명은 개인정보가 포함될 수 있어 비공개 capture로 취급합니다.
