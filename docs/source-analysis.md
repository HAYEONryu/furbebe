# 원천 분석 도구

분석 CLI는 원천 형식·품질·공식 코드 연결을 조사하는 보조 도구입니다.
사이트의 실제 데이터를 저장하는 명령은 [animal_sync.main](sync-design.md)입니다.
profiling을 실행했다고 DB가 갱신되거나 공개 태그가 새로 생기지 않습니다.

## 설정 확인·단건 probe

```sh
backend/.venv/bin/python -m backend.jobs.animal_sync.profiling --check-config
backend/.venv/bin/python -m backend.jobs.animal_sync.profiling --probe
```

check-config는 원천 키 존재 여부만 확인하며 네트워크를 호출하지 않습니다.
probe는 실제 단건 HTTPS 응답을 .local/profiling에 저장합니다.
service key를 command argument에 넣지 않습니다.

## 수집형 분석

```sh
backend/.venv/bin/python -m backend.jobs.animal_sync.profiling --target-unique 10000 --min-unique 5000 --page-size 1000 --max-pages 20 --start-date 20261001 --end-date 20261005
```

날짜는 YYYYMMDD이며 둘 다 지정합니다. 예제 날짜는 실제 조사 범위로 바꿉니다.
분석 목표·상한과 기간이 있으므로 전수 또는 전체 모집단으로 일반화하지 않습니다.
entire-population-confirmed 예외는 실제 전체 범위와 완전성이 증명될 때만 사용하며 기간 제한과 결합하지 않습니다.

## 재분석과 참조 코드

```sh
backend/.venv/bin/python -m backend.jobs.animal_sync.profiling --input .local/profiling/RUN_ID/raw-RUN_ID.jsonl
backend/.venv/bin/python -m backend.jobs.animal_sync.references --input .local/profiling/RUN_ID/raw-RUN_ID.jsonl --as-of 2026-10-05
```

references 기본은 offline입니다. 없는 코드 조회가 필요할 때만 --fetch-missing을 추가합니다.
캐시는 .local/profiling/reference-data/cache.json입니다.
시도 전체 / 시도별 시군구 / 축종별 품종 / 시도·시군구별 보호소 단위로 기록합니다.
조회해도 없던 코드는 24시간 반복 요청을 막고, 오류·불완전 결과는 정상 캐시로 덮어쓰지 않습니다.
참조 결과는 animal run ID와 raw checksum에 묶습니다. 다른 capture의 결과를 섞으면 중단합니다.
실제 API의 정적 regions.json이 자동 갱신되는 것은 아닙니다.

## 결과와 해석

run 디렉터리에 raw JSONL, run.json, summary JSON, field-stats CSV, manual-review CSV,
reference-profile.json과 reports/의 Markdown 집계를 저장합니다.
생성 보고서는 .local 아래에만 두어 README와 안내 문서를 덮어쓰지 않습니다.
키는 제거하지만 원천 설명에 개인 정보가 있을 수 있어 raw 파일을 공개하지 않습니다.
수동 review_notes를 자동 정답으로 채우지 않습니다. 재분석 전 사람이 작성한 검토 CSV는 별도 보관합니다.

분석의 keyword coverage는 후보 문장의 비율이며 현재 공개 tagger의 precision/recall이 아닙니다.
실행별 표본 분포와 exploratory 분류는 [현재 API 그룹](api-contract.md) 또는 [태그 규칙](tag-generation.md)을 변경하지 않습니다.
분석 blocker의 exit code 2는 조사 미완료를 의미하며 live API 배포·DB 건강 상태와 별도로 판단합니다.
