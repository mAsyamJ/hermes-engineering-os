#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
ENV="$ROOT/deploy/observability/.env"
# shellcheck disable=SC1090
set -a
source "$ENV"
set +a
echo "=== schema ==="
sudo -n docker exec hermes-eos-postgres \
  psql -U hermes_engineering -d hermes_engineering -tAc \
  "SELECT version FROM schema_migrations ORDER BY 1;"
echo "=== quality ==="
sudo -n docker compose --env-file "$ENV" -f "$ROOT/deploy/observability/compose.yaml" \
  run --rm --no-deps \
  -e ANALYTICS_DATABASE_URL="postgresql://hermes_engineering_reader:${HERMES_ENGINEERING_READER_PASSWORD}@postgres:5432/hermes_engineering" \
  --entrypoint python analytics-materialize -m engineering_os.analytics.quality
echo "=== reader cannot write ==="
if sudo -n docker exec hermes-eos-postgres \
  psql -U hermes_engineering_reader -d hermes_engineering \
  -c "INSERT INTO schema_migrations(version) VALUES ('should-fail');" >/tmp/eos-reader-write.log 2>&1; then
  echo "FAIL: reader wrote" >&2
  exit 1
fi
echo "PASS: reader cannot write"
echo "=== writer cannot connect phoenix ==="
if sudo -n docker exec hermes-eos-postgres \
  psql -U hermes_engineering_writer -d phoenix -c "SELECT 1" >/tmp/eos-writer-phoenix.log 2>&1; then
  echo "FAIL: writer connected to phoenix" >&2
  exit 1
fi
echo "PASS: writer cannot connect phoenix"
echo "=== phoenix table count ==="
COUNT="$(sudo -n docker exec hermes-eos-postgres \
  psql -U eos_admin -d phoenix -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema');")"
echo "phoenix_user_tables=$COUNT"
test "$COUNT" = "65"
echo "PASS: verify-analytics-data"
