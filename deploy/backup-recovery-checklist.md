# 백업·복구 점검표

구체적인 절차는 [운영 매뉴얼](../docs/operations.md)을 따릅니다.
목표: 매일+schema 변경 직전 / 30일 보관 / RPO 24시간 / RTO 4시간.
자동화·외부 보관·실제 복구 시간은 증거로 확인합니다.

- [ ] PROD project·DB version·현재 revision·실제 plan 확인.
- [ ] Dashboard backup/PITR 가용성과 retention 확인.
- [ ] public schema 데이터와 alembic_version export, 역할·권한·비DB 설정 별도 inventory.
- [ ] 서버와 호환되는 pg_dump, 인증정보가 command/log에 없음.
- [ ] archive 읽기·checksum·암호화 왕복 검증.
- [ ] 비공개 offsite archive, 별도 key custody, 접근·보관 기간 확인.
- [ ] 생성 전 빈 schema backup과 적재된 데이터 backup을 구분.
- [ ] 새 disposable DB restore rehearsal, schema 충돌의 TOC 검토.
- [ ] 테이블·행수·FK/중복/index·revision·API·격리 sync 재실행 확인.
- [ ] 실제 복구 시간·데이터 freshness·operator와 결과 기록.
- [ ] 복구 시 writer/schedule 중지, 별도 target 검증 후 전환 계획.
- [ ] schema downgrade를 자동 rollback으로 사용하지 않음.
- [ ] 외부 사진·Storage object·secret/DNS/IAM 제외 범위를 설명.

실제 최초 backup의 범위와 남은 작업은 [운영 상태](../docs/operational-status.md)에 있습니다.
