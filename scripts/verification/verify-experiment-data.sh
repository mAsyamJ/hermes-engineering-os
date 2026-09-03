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
  "SELECT version FROM schema_migrations ORDER BY 1;" | rg -q '0004_experiments'
echo "=== experiment quality ==="
sudo -n docker compose --env-file "$ENV" -f "$ROOT/deploy/observability/compose.yaml" \
  run --rm --no-deps \
  -e ANALYTICS_DATABASE_URL="postgresql://hermes_engineering_reader:${HERMES_ENGINEERING_READER_PASSWORD}@postgres:5432/hermes_engineering" \
  --entrypoint python experiments-engine -m engineering_os.experiments.quality
echo "=== reader cannot write experiments ==="
if sudo -n docker exec hermes-eos-postgres \
  psql -U hermes_engineering_reader -d hermes_engineering \
  -c "INSERT INTO experiment_checkpoints(source) VALUES ('should-fail');" >/tmp/eos-exp-reader-write.log 2>&1; then
  echo "FAIL: reader wrote experiments" >&2
  exit 1
fi
echo "PASS: reader cannot write experiments"
echo "=== writer cannot connect phoenix ==="
if sudo -n docker exec hermes-eos-postgres \
  psql -U hermes_engineering_writer -d phoenix -c "SELECT 1" >/tmp/eos-exp-writer-phoenix.log 2>&1; then
  echo "FAIL: writer connected to phoenix" >&2
  exit 1
fi
echo "PASS: writer cannot connect phoenix"
COUNT="$(sudo -n docker exec hermes-eos-postgres \
  psql -U eos_admin -d phoenix -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema');")"
echo "phoenix_user_tables=$COUNT"
test "$COUNT" = "65"
echo "=== production protocols ==="
PROD="$(sudo -n docker exec hermes-eos-postgres \
  psql -U eos_admin -d hermes_engineering -tAc \
  "SELECT COUNT(*) FROM experiment_protocol_versions WHERE scope = 'PRODUCTION';")"
test "$PROD" = "0"
echo "PASS: no production experiments"
echo "=== fixture leakage into Phase 5 production ==="
LEAK="$(sudo -n docker exec hermes-eos-postgres \
  psql -U eos_admin -d hermes_engineering -tAc \
  "SELECT COUNT(*) FROM performance_aggregates WHERE is_current AND cohort_id LIKE 'production%' AND (dimension_value LIKE 't_exp_%' OR dimension_value LIKE 't_eval_canary%');")"
test "$LEAK" = "0"
echo "PASS: no experiment fixture dimensions in production aggregates"
echo "=== ITT reassignment ==="
REASSIGN="$(sudo -n docker exec hermes-eos-postgres \
  psql -U eos_admin -d hermes_engineering -tAc \
  "SELECT COUNT(*) FROM experiment_exposures WHERE reassigned IS TRUE;")"
test "$REASSIGN" = "0"
echo "PASS: no ITT reassignment"
echo "PASS: verify-experiment-data"
