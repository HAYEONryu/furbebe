#!/usr/bin/env bash
# Only disposable CI containers. Never reads a repository dotenv or remote DB.
set -euo pipefail
trap 'docker rm -f furbebe-ci-api furbebe-ci-db >/dev/null 2>&1 || true; docker network rm furbebe-ci-net >/dev/null 2>&1 || true' EXIT

docker network create furbebe-ci-net >/dev/null
docker run -d --name furbebe-ci-db --network furbebe-ci-net \
  -e POSTGRES_USER=furbebe -e POSTGRES_PASSWORD=ci-disposable-only \
  -e POSTGRES_DB=furbebe_test_docker postgres:16 >/dev/null
for attempt in $(seq 1 30); do
  if docker exec furbebe-ci-db pg_isready -U furbebe -d furbebe_test_docker >/dev/null 2>&1; then break; fi
  sleep 1
done
docker exec furbebe-ci-db pg_isready -U furbebe -d furbebe_test_docker >/dev/null

# Check image independently of environment injection.
docker run --rm --entrypoint python furbebe-api:ci -c '
import os
from pathlib import Path
assert os.getuid() == 10001
assert not any(name in os.environ for name in ("DATABASE_URL", "DATA_GO_KR_SERVICE_KEY"))
assert all(p.name not in (".env", "env", ".venv", "tests", "jobs", "migrations") for p in Path("/app").rglob("*"))
'
docker run -d --name furbebe-ci-api --network furbebe-ci-net \
  --cpus=1 --memory=512m -p 127.0.0.1:8080:8080 \
  -e APP_ENV=production \
  -e FRONTEND_ORIGIN=https://furbebe.site,https://www.furbebe.site \
  -e DATABASE_URL=postgresql+psycopg://furbebe:ci-disposable-only@furbebe-ci-db:5432/furbebe_test_docker \
  -e DB_POOL_SIZE=3 -e DB_MAX_OVERFLOW=1 furbebe-api:ci >/dev/null
for attempt in $(seq 1 30); do
  if curl --fail --silent http://127.0.0.1:8080/health >/dev/null; then break; fi
  sleep 1
done
curl --fail --silent http://127.0.0.1:8080/health

docker exec furbebe-ci-api python -c '
from backend.app.core.config import get_settings
from backend.app.main import app
s = get_settings()
assert s.app_env == "production" and s.db_pool_size == 3 and s.db_max_overflow == 1
assert s.allowed_origins == ["https://furbebe.site", "https://www.furbebe.site"]
assert not app.debug and app.docs_url is None and app.openapi_url is None
'
for origin in https://furbebe.site https://www.furbebe.site; do
  curl --silent --fail -H "Origin: $origin" -D - http://127.0.0.1:8080/health | grep -qi "access-control-allow-origin: $origin"
done
if curl --silent -H 'Origin: http://localhost:5173' -D - http://127.0.0.1:8080/health | grep -qi 'access-control-allow-origin:'; then
  echo 'Development origin must not be allowed in production'
  exit 1
fi
if docker logs furbebe-ci-api 2>&1 | grep -q 'ci-disposable-only'; then
  echo 'Unexpected database credential in container log'
  exit 1
fi
echo 'Docker startup, nonroot image, injection, health, CORS and log smoke passed'
