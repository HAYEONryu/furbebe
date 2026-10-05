# Post-deployment smoke checklist

Not executed against production during Phase 10. Use after separate deployment approval. Record release commit/image digest, operator, timestamp, request IDs and results. Use an actual API UUID, never a fixture ID.

## API / TLS / CORS

- [ ] `https://api.furbebe.site/health`: valid certificate, HTTP 200, `{status:ok, service:furbebe-api, version:1}`, UUID `X-Request-ID`. This checks real PostgreSQL connectivity.
- [ ] `/api/v1/animals?page_size=24`: contract, correct total/pagination, real database rows, no raw_payload or server secret.
- [ ] `/api/v1/meta/filters`: valid catalog and region labels, cold/warm duration; cold response fits frontend 20s timeout.
- [ ] `/api/v1/tags`: registered tag catalog; no invented characteristics.
- [ ] `/api/v1/animals/:actual-id`: factual breed, region, status, descriptions, shelter, null-safe optional data.
- [ ] `/api/v1/animals/:actual-id/similar?limit=4`: excludes source, valid UUIDs; independent error fallback.
- [ ] Unknown UUID / invalid query: safe 404 / 422 envelope. Simulated upstream outage only in staging: safe 503/timeout, no SQL or connection URI.
- [ ] GET and OPTIONS from `https://furbebe.site` and `https://www.furbebe.site`: exact allow-origin, GET/X-Request-ID allowed, no credentials wildcard.
- [ ] Origin `http://localhost:5173` and unrelated origin: no allow-origin. CORS does not authenticate this public API.
- [ ] `/docs`, `/openapi.json`: unavailable in production; debug/reload off.
- [ ] Application log sample: request_id, endpoint template, status, duration_ms. No query/body/secret.
- [ ] Load balancer host/certificate `api.furbebe.site`, serverless NEG in asia-northeast3, IAM/invocation works. Direct public run.app access is restricted by ingress.

## Frontend

- [ ] `/`: SSR actual data, links, primary image, no hydration errors.
- [ ] `/dogs`: list, search/filter/sort/page/back behavior; empty search reset.
- [ ] `/dogs/:actual-id`: HTTP 200, detail and related animals; missing ID gives 404.
- [ ] Images: HTTP(S) source URLs, appropriate eager/lazy loading, stable aspect ratios, missing/broken fallback. Test actual third-party image providers.
- [ ] Favorites: toggle without opening card, persisted across reload, storage-disabled fallback.
- [ ] Share: native share, clipboard and selectable-URL fallback; clean detail URL.
- [ ] Keyboard-only navigation, skip link, visible focus, filter modal trap/Escape/restore.
- [ ] All three routes at 360/390/768/1440px: no horizontal overflow.
- [ ] Real mobile cold/warm LCP/CLS and API latency under small concurrent load. Watch memory, 503/pool timeout, p95/p99 before increasing concurrency/max instances.

## SEO / Domains / Assets

- [ ] Apex + www HTTPS are served by the intended Worker. Canonical remains apex, metadata rendered in initial HTML.
- [ ] Main/Dogs/Detail title, description, OG URL/image; detail metadata matches actual record. Check crawler accessibility of the source image.
- [ ] `/dogs?...`: canonical `/dogs`, noindex/follow; pagination nofollow.
- [ ] `/sitemap.xml`: XML 200, actual live UUIDs when snapshot configured, no fixture/query/dead URLs. Spot-check detail responses.
- [ ] `/robots.txt`: 200 with canonical sitemap URL; filtered pages remain crawlable to read noindex.
- [ ] Missing/error page: correct status and X-Robots-Tag noindex.
- [ ] workers.dev and preview URLs disabled in production config. Public staging requires separate noindex policy/access control.

## Sync / Recovery

- [ ] Before activating cron: approved PROD target, current=target migration revision, verified backup and recovery rehearsal, explicit first live sync approval.
- [ ] First manual production run uses production-sync environment and matching expected project. DEV secrets cannot be used for PROD.
- [ ] sync id, received/inserted/updated/error/duration present; DB sync_runs completed. Exit 2 / partial commit is investigated before proceeding.
- [ ] Repeat run is idempotent; advisory lock and Actions concurrency prevent overlapping writers.
- [ ] After separate frequency activation approval: 2-hour cron is enabled, completed runs and freshness are checked. Schedules can be delayed.
- [ ] Rebuild sitemap after a successful stable sync if newly indexable records must be discoverable immediately.
- [ ] Alert/operational check for 503s, slow cold metadata, pool saturation, stale or failed sync. Use existing Cloud Logging/Workers/Actions facilities; no paid SaaS required.
