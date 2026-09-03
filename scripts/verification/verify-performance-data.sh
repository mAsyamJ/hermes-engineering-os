#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=../lib/repo-root.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/../lib/repo-root.sh"
ROOT="$(_eos_repo_root_from "${BASH_SOURCE[0]}")"
ENV="$ROOT/deploy/observability/.env"
# shellcheck disable=SC1090
set -a
source "$ENV"
set +a
echo "=== schema ==="
sudo -n docker exec hermes-eos-postgres \
  psql -U hermes_engineering -d hermes_engineering -tAc \
  "SELECT version FROM schema_migrations ORDER BY 1;"
echo "=== performance quality ==="
sudo -n docker compose --env-file "$ENV" -f "$ROOT/deploy/observability/compose.yaml" \
  run --rm --no-deps \
  -e ANALYTICS_DATABASE_URL="postgresql://hermes_engineering_reader:${HERMES_ENGINEERING_READER_PASSWORD}@postgres:5432/hermes_engineering" \
  --entrypoint python performance-materialize -m engineering_os.performance.quality
echo "=== reader cannot write performance ==="
if sudo -n docker exec hermes-eos-postgres \
  psql -U hermes_engineering_reader -d hermes_engineering \
  -c "INSERT INTO performance_checkpoints(source) VALUES ('should-fail');" >/tmp/eos-perf-reader-write.log 2>&1; then
  echo "FAIL: reader wrote performance" >&2
  exit 1
fi
echo "PASS: reader cannot write performance"
echo "=== writer cannot connect phoenix ==="
if sudo -n docker exec hermes-eos-postgres \
  psql -U hermes_engineering_writer -d phoenix -c "SELECT 1" >/tmp/eos-perf-writer-phoenix.log 2>&1; then
  echo "FAIL: writer connected to phoenix" >&2
  exit 1
fi
echo "PASS: writer cannot connect phoenix"
COUNT="$(sudo -n docker exec hermes-eos-postgres \
  psql -U eos_admin -d phoenix -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema');")"
echo "phoenix_user_tables=$COUNT"
test "$COUNT" = "65"
echo "=== fixture leakage ==="
LEAK="$(sudo -n docker exec hermes-eos-postgres \
  psql -U eos_admin -d hermes_engineering -tAc \
  "SELECT COUNT(*) FROM performance_aggregates WHERE is_current AND cohort_id LIKE 'production%' AND dimension_value LIKE 't_eval_canary%';")"
test "$LEAK" = "0"
echo "PASS: no canary dimension in production aggregates"
echo "=== quality not zero-rate with n=0 ==="
BAD="$(sudo -n docker exec hermes-eos-postgres \
  psql -U eos_admin -d hermes_engineering -tAc \
  "SELECT COUNT(*) FROM performance_aggregates WHERE is_current AND metric_id LIKE 'quality_%' AND known_n = 0 AND value = 0 AND interpretation IS DISTINCT FROM 'INSUFFICIENT_DATA';")"
test "$BAD" = "0"
echo "PASS: zero quality coverage is not a 0% rate"
echo "PASS: verify-performance-data"
