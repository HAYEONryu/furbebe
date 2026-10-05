# 태그 생성 로직

기준 코드: backend/jobs/animal_sync/tagger/{__init__,behavior,colors,catalog}.py.
태그는 원천 설명·털색·등록 체중의 근거를 요약합니다. 품종·사진·나이·성별에서 성격을 추측하지 않습니다.
AI 모델, 사진 분석, 무작위 태그, 최소 태그 수를 맞추는 보정은 없습니다.

## 입력과 생성 순서

ValidatedAnimal → normalize_animal → generate_tags 순서로 실행합니다.
일반 수집은 대상 개를 저장할 때 태그를 생성합니다. 동일 원문 재수집에서도 태그 규칙은 다시 적용합니다.

1. 특성: special_mark, social_text, health_text에서 곱슬·귀·꼬리·풍성한 털 근거를 찾습니다.
2. 행동: special_mark, social_text, raw_payload.adptnTxt에서 공개 허용된 행동 규칙을 적용합니다.
3. 털색: color_text를 먼저 해석하고 조건에 따라 special_mark로 보완합니다.
4. 몸집: 파싱된 weight_kg에서 현재 몸집 태그를 하나 만듭니다.
5. 같은 key는 하나로 합치고 CATALOG.display_order 순서로 정렬합니다.

행동 규칙은 health_text를 입력으로 쓰지 않습니다. 일반 털 특성 규칙은 health_text도 읽습니다.
이 차이 때문에 “건강 설명을 전혀 읽지 않는다”라고 설명하면 부정확합니다.
건강·질병·나이·성별 자체를 표현하는 태그는 생성하지 않습니다.

## 사전: 27개

사전 등록은 생성 활성화와 별개입니다. /tags는 기본적으로 활성 사전을 반환하므로 배정이 없는 태그도 나올 수 있습니다.
아래 표의 “미생성”은 현재 공개 생성기가 해당 key를 부여하지 않는다는 뜻입니다.

| 분류 | API type | key | 표시 | 현재 생성 |
| --- | --- | --- | --- | --- |
| 성격 | trait | gentle | 🙂 순딩이 | 활성 |
| 성격 | trait | shy | 🧚 수줍요정 | 활성 |
| 성격 | trait | playful | 🤸 똥꼬발랄 | 활성 |
| 성격 | trait | affectionate | 💕 애교쟁이 | 미생성 |
| 성격 | trait | calm | 🍵 차분선비댕 | 활성 |
| 성격 | trait | curious | 🔎 호기심대장 | 미생성 |
| 성격 | trait | smart | 🧠 똑똑이 | 미생성 |
| 성격 | trait | sensitive | 🌵 새콤새침 | 미생성 |
| 관계 | trait | people_friendly | 🥰 사람좋아 | 활성 |
| 관계 | trait | outgoing | 🙋 적극댕댕이 | 미생성 |
| 관계 | trait | dog_friendly | 🐕 친구좋아 | 미생성 |
| 관계 | trait | smiley | 😄 미소천사 | 미생성 |
| 관계 | trait | lap_dog | 🛋️ 무릎댕댕이 | 미생성 |
| 털색 | vibe | patterned_coat | 🎨 삼색이 | 조건 일치 |
| 털색 | vibe | cookies_cream | 🍪 쿠앤크 | 조건 일치 |
| 털색 | vibe | brownie | 🤎 브라우니 | 조건 일치 |
| 털색 | vibe | cream_coat | 🍦 크림이 | 조건 일치 |
| 털색 | vibe | black_coat | 🖤 검댕이 | 조건 일치 |
| 털색 | vibe | white_coat | 🤍 흰둥이 | 조건 일치 |
| 특성 | vibe | curly | 🌀 곱슬몽실 | 조건 일치 |
| 특성 | vibe | pointed_ears | 👂 쫑긋귀 | 조건 일치 |
| 특성 | vibe | wagging_tail | 🚁 꼬리콥터 | 조건 일치 |
| 특성 | vibe | fluffy | ☁️ 복슬복슬 | 조건 일치 |
| 몸집 | vibe | pocket | 🫘 쪼꼬미 | 0 ≤ kg < 5 |
| 몸집 | vibe | cuddly | 🧸 품에쏙 | 5 ≤ kg < 10 |
| 몸집 | vibe | sturdy | 💪 댕든든 | 10 ≤ kg < 20 |
| 몸집 | vibe | giant | 🦁 왕크왕귀 | kg ≥ 20 |

분류는 내부 CATEGORIES이며 현재 응답 모델의 별도 category 필드가 아닙니다.
API type enum은 fact/trait/vibe를 지원하지만 현재 CATALOG는 trait 13개, vibe 14개만 생성합니다.

## 행동 규칙: 공개 활성 6개, 결과 key 5개

behavior.RELEASED_RULE_IDS가 실제 공개 생성의 기준입니다. 전체 RULES에 존재한다고 활성화된 것은 아닙니다.

| rule_id | key | 허용되는 명시적 근거 예 |
| --- | --- | --- |
| gentle-explicit-v3 | gentle | 온순, 순함, 순하고, 순하며, 순한 성격 |
| cautious-explicit-v3 | shy | 겁이 많음/있음/조금 있음, 소심, 경계심이 있음/많음/강함 |
| active-explicit-v3 | playful | 활발, 활동적 |
| calm-explicit-v3 | calm | 얌전, 차분 |
| people-like-v3 | people_friendly | 사람을 좋아, 사람 손길을 좋아 |
| people-follow-v3 | people_friendly | 사람을 잘 따름/따르는 표현 |

두 사람 관련 규칙이 일치하면 먼저 정의된 규칙의 근거를 사용합니다.
people-approach-v3, affection-explicit-v3, lap-explicit-v3는 평가 후보로 정의되어 있으나 공개 생성에서는 꺼져 있습니다.
curious/smart/sensitive/outgoing/dog_friendly/smiley에는 현재 활성 규칙이 없습니다.

공개 허용은 사용자의 검토 완료 가정에 근거합니다.
행 단위 정답 라벨이 없어 실제 precision·recall·정확도 측정이 완료되었다고 주장하지 않습니다.
confidence=0.90은 생성기의 고정 metadata이며 실제 정답 확률이 아닙니다.

### 문장과 차단 조건

입력은 마침표·느낌표·물음표·세미콜론·줄바꿈 및 대응하는 일부 전각 문장부호로 나눕니다.
쉼표는 행동 문장을 나누지 않습니다. 원문 문장을 보관하고 공백을 제거한 문장에서 규칙을 찾습니다.

다음 표현이 포함된 문장은 행동 후보에서 제외합니다.

- **부정**: 없음, 않음, 아님/아닌, 못, 싫음, 안 좋아/안 따름 등.
- **불확실성**: 추정, 같음/같아, 보임, 듯, 미확인, 불명, 모름, 가능성, 아직, 적응 중, 조건 표현, ?.
- **행정·안내**: 발견·구조·공고·입양·문의·보호자·직원·환경·센터·훈련·예시·해주세요 등.
- **일시 상태**: 입소 당시, 검진, 진료, 주사, 치료 중, 수술 후, 마취, 통증, 기력/무기력.

전체 입력을 먼저 확인해 부정·불확실 문장에 해당 성격 topic이 있으면 그 key를 다른 긍정 문장에서도 차단합니다.
“사람을 경계/무서워/싫어”는 people_friendly를 별도로 차단합니다.
보수적인 문장 제외 때문에 참인 특성도 누락될 수 있습니다. coverage를 높이려고 자동 fallback하지 않습니다.

| 원문 예 | 결과 |
| --- | --- |
| 온순하고 차분함. 사람을 잘 따름 | gentle, calm, people_friendly |
| 온순하지 않음 | gentle 없음 |
| 온순함. 온순한 것 같음 | gentle 없음: 다른 문장의 불확실성도 차단 |
| 온순하고 활발하며 입질 없음 | 행동 태그 없음: 쉼표·연결어를 포함한 문장 전체 차단 |
| 산책 잘함 | 행동 태그 없음 |
| 애교가 많음 | affectionate 없음: 공개 규칙 비활성 |

## 털색: 대표 태그 최대 1개

colors.FAMILIES가 한국어·영어 동의어를 묶습니다.
회색/실버/그레이, 갈색/탄/금색/레몬색/주황색, 크림/베이지, 검정, 흰색 계열을 인식합니다.
긴 토큰을 먼저 찾고 짧은 단어와 영어에는 경계를 적용합니다.

우선순위는 다음과 같습니다.

1. 회색 계열이 하나라도 있으면 색 태그를 생성하지 않습니다. 무늬가 함께 있어도 제외하며 원문 보완도 하지 않습니다.
2. 반점·얼룩·점박·호반색·호피·브린들 또는 색 계열 3개 이상이면 patterned_coat.
3. 검정+흰색만 있으면 cookies_cream.
4. 갈색 계열이 있으면 brownie.
5. 크림 계열이 있으면 cream_coat.
6. 검정만 있으면 black_coat, 흰색만 있으면 white_coat.

color_text에서 인식된 경우 그 결과를 확정합니다.
인식할 수 없을 때만 special_mark를 문장 조각으로 나누어 보완합니다.
피부·눈·상처·오염·목줄·옷·리드줄·하네스·아닌·아님·없을 포함한 조각은 보완에서 제외합니다.
보완 조각은 합쳐서 해석합니다. 여러 털색 태그를 동시에 만들지 않습니다.

예: 흰색&갈색 → brownie, 흑백 → cookies_cream, 검정·흰색·갈색 → patterned_coat,
회색 얼룩 → 색 태그 없음. 털색은 성격 근거로 사용하지 않습니다.

## 추가 특성과 부정 처리

곱슬, 쫑긋, 꼬리 흔드는 표현, 복슬/복실·풍성한 털의 명시적 패턴을 찾습니다.
문장 조각은 . , ; / | ! ? 및 줄바꿈으로 나누며 서로 다른 필드를 이어 붙여 매칭하지 않습니다.
일치 앞의 안/못, 뒤의 없음·않음·아님·불명·미확인 등과 공유 부정은 배제합니다.
이 규칙의 부정 처리는 행동 규칙의 문장 전체 차단과 다릅니다.

입질주의/강한경계를 계산하는 generate_safety_badges 함수도 있습니다.
**현재 수집·API 직렬화는 이 함수를 호출하지 않으며 API에 safety_badges 필드는 없습니다.**
운영 화면에 이미 제공되는 기능으로 설명하거나 광고성 태그로 혼합하지 않습니다.

## 몸집 태그와 체중 필터의 차이

등록 체중이 유한한 0 이상이면 몸집 태그를 생성합니다. null·미해석 체중이면 생성하지 않습니다.
0kg도 현재 코드에서는 pocket입니다. 성견 예상 체중을 추론하지 않습니다.

| 값 | 몸집 태그 | API size_group 필터 |
| --- | --- | --- |
| 5kg | cuddly | tiny |
| 10kg | sturdy | small |
| 20kg | giant | medium |

필터는 tiny ≤5 / small >5~10 / medium >10~20 / large >20입니다.
태그는 <5 / <10 / <20 / ≥20입니다. 두 경계를 임의로 같은 정책으로 문서화하지 않습니다.

## 근거·버전·저장

| 생성 | generator | generator_version | confidence | rule_id |
| --- | --- | --- | --- | --- |
| 행동 | rules | 3.0 | 0.90 | 위 행동 규칙 ID |
| 색 | rules | 2.0 | 1 | single-color-v2 |
| 몸집 | rules | 2.0 | 1 | current-size-v2 |
| 추가 특성 | rules | 2.0 | 1 | key-v2 |

evidence는 필드명과 원문 문장, 또는 weight_kg 수치를 기록합니다.
전체 tagger.VERSION=2.0만 보고 행동 배정도 2.0이라고 판단하지 않습니다.
DB unique key는 동물/key/generator/version이며 읽기는 활성 배정 중 최근 animal/key 한 행을 반환합니다.

일반 수집은 현재 생성기가 소유한 배정만 갱신합니다.
근거가 사라지거나 버전이 바뀐 배정은 is_active=false로 보존합니다.
사전의 label/emoji/description/order는 갱신하지만 관리자가 변경한 is_active를 되돌리지 않습니다.
별도 생성기와 독립 소유 데이터는 일반 reconciliation에서 유지합니다.

## 재생성과 변경 절차

먼저 같은 대상의 dry-run으로 총 동물 수·배정 수·태그별 건수를 확인합니다.

```sh
APP_ENV=development backend/.venv/bin/python -m backend.jobs.rebuild_tags --target supabase-dev
```

rebuild_tags는 **모든 저장 동물**의 raw_payload를 읽습니다. 공개 활성 동물만 읽는 작업이 아닙니다.
--apply는 transaction/advisory lock/테이블 lock 안에서 **전체 animal_tags와 tags를 삭제 후 다시 작성**합니다.
수동·다른 생성기·과거 버전 배정과 사전 활성 설정도 보존하지 않습니다.
운영에는 일반 수집을 통한 보존형 갱신을 기본으로 사용하고, 전면 재생성은 백업과 영향 검토 후 별도 실행합니다.
출력의 version은 전체 생성기 값이며 배정별 행동 버전과는 다릅니다.

규칙을 변경할 때는 부정·불확실·행정·일시 상태와 색/체중 경계 예제를 검증하고 버전 정책을 정합니다.
공개 허용 규칙 확대에는 원문 표본과 정답 검토를 확보합니다.
CATALOG 설명을 바꾸면 frontend/app/services/tag-descriptions.json도 함께 맞춥니다.
