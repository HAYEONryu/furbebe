# Supabase backup / recovery checklist

Account/project plan has not been inspected. Do not assume DEV/PROD plan, available backup or PITR. Complete the following against the actual production Dashboard before approving migration/sync.

- [ ] Record PROD project identity, region, plan/compute and database version; ensure it differs from DEV.
- [ ] Dashboard Database > Backups: record which backups exist, latest successful timestamp, retention window and restore controls. Verify whether logical/physical backups and downloadable exports are available.
- [ ] If Free: arrange periodic logical off-site exports; do not assume paid-plan managed backups. If paid: verify actual daily backup retention. PITR is a separately priced option, not automatically assumed.
- [ ] Set owner, backup cadence, retention, RPO/RTO and restore authority. Initial proposal: daily encrypted off-site logical export + an additional verified export before schema changes; accept the implied up-to-24-hour data-loss window or choose a tighter policy.
- [ ] Export schema, data, required roles/grants, Alembic revision and relevant non-DB settings. Use native PostgreSQL pg_dump/pg_restore or supported Supabase CLI with a matching client version. Do not place DB URI/password in shell tracing, chat, command artifacts or public logs.
- [ ] Store encrypted off-site copies with separate restricted access and a tested retention policy. Verify checksum, archive readability and secure key access.
- [ ] Understand scope: database backup does not restore external protection-center photos or Supabase Storage object contents. No hosted image copies are created by this app. Account/API/secret configuration also requires a separate inventory.
- [ ] Rehearse restore into a separate disposable project/DB. Check six domain tables, row counts, FK/indexes, Alembic revision, health/list/detail/filter/similar and sync idempotency. Record elapsed time and data freshness. Never rehearse destructive restore on live PROD.
- [ ] Before production schema changes: save verified backup identifier/checksum, restore result, current/target revision and operator-approved recovery instructions.
- [ ] Incident: stop new sync writes, preserve logs, choose a restore timestamp, obtain destructive-operation approval, restore to a separate target where possible, verify data, then switch approved secret/revision and resume traffic/sync. Record missing-data window and reconcile source records.

Migration downgrade is not a backup. Current `20260915_0001` downgrade drops all six domain tables. It cannot recover records and is not an automatic production rollback. Application revision rollback and DB recovery are separate operations.

[Supabase backup documentation](https://supabase.com/docs/guides/platform/backups) describes paid-plan daily backups, Free export guidance, PITR and Storage exclusions. Account-specific availability must be verified in Dashboard. No add-on or paid backup service has been activated.
