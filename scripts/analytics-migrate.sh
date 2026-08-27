#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
ENV="$ROOT/deploy/observability/.env"
# shellcheck disable=SC1090
set -a
source "$ENV"
set +a
COMPOSE=(sudo -n docker compose --env-file "$ENV" -f "$ROOT/deploy/observability/compose.yaml")
"${COMPOSE[@]}" run --rm --no-deps \
  -e ANALYTICS_MIGRATE_DSN="postgresql://hermes_engineering:${HERMES_ENGINEERING_DB_PASSWORD}@postgres:5432/hermes_engineering" \
  -e ANALYTICS_DATABASE_URL="postgresql://hermes_engineering:${HERMES_ENGINEERING_DB_PASSWORD}@postgres:5432/hermes_engineering" \
  --entrypoint python analytics-materialize -m engineering_os.analytics.migrate --json
