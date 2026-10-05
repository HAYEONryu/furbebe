# Sync schedule configuration

GitHub Environment `development-sync`:
- Secret: `DATABASE_URL_dev`, `DATA_GO_KR_SERVICE_KEY`
- Variables: `SUPABASE_URL_dev`
- APP_ENV is fixed to development in the workflow.

GitHub Environment `production-sync`:
- Secret: `DATABASE_URL_prod`, `DATA_GO_KR_SERVICE_KEY`
- Variables: `SUPABASE_URL_prod`, `FURBEBE_PROD_PROJECT_REF`
- APP_ENV is fixed to production. Project reference is checked against both project URL and credential.
- Configure permitted deployment branch `main`; use protected workflow changes and required reviewers when the GitHub plan supports them.
- Do not put prod credentials in repository-wide secrets or the development environment.

Scheduled collection runs twice daily at **00:00 and 12:00 Asia/Seoul**, using UTC cron `0 3,15 * * *`. With `PRODUCTION_SYNC_ENABLED` unset/false, the development job runs on schedule against the current DEV database. Setting it to true switches scheduled collection to the production job; DEV and PROD never both run for one scheduled event. Both scheduled jobs use `--full`. Required environment secrets and variables above must be configured, and the workflow must be present on GitHub's default branch for schedules to run. GitHub may delay scheduled starts; these are trigger times rather than an exact-time guarantee.

Manual DEV and PROD selection remains available. Manual production also requires `APPROVED_PRODUCTION_SYNC`. Sync stores only dogs with source status 보호중 or 입양 가능; ended posts are excluded and previously stored posts that become ended are removed. The read API derives 입양 가능 from 보호중 after ten calendar days from notice start. The filter defaults to 입양 가능 and offers 보호중 as its only other option.

CLI remains `python -m backend.jobs.animal_sync.main`; target is explicit `--database-target supabase-prod` or `supabase-dev`. Production requires APP_ENV=production, separate `DATABASE_URL_prod` and expected project metadata. No fallback to generic DATABASE_URL or DEV; production replay is rejected. Session-mode port 5432 is required because sync uses session advisory locks. Pool 1 + overflow 1 covers the held sync connection and finalization connection. The existing PostgreSQL advisory lock also protects against overlapping writers outside Actions.

Raw pages remain ephemeral on the runner. Do not upload `.local/sync` captures as public artifacts. Logs retain only existing redacted reports and page counters. Limit Actions log retention and repository access. Failures before sync initialization may have only a safe error code rather than a sync id.

Manual runs default to a supplied YYYY-MM-DD date window with max_animals=1000, rejected before writes if larger. Empty/invalid date inputs fail before opening a DB connection. A full API-window manual scan requires an explicit full_scan checkbox. Scheduled runs use --full.
