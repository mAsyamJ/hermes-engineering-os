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
  psql -U hermes_control_owner -d hermes_control -tAc \
  "SELECT version FROM schema_migrations ORDER BY 1;" | rg -q '0001_adaptation'
sudo -n docker exec hermes-eos-postgres \
  psql -U hermes_control_owner -d hermes_control -tAc \
  "SELECT version FROM schema_migrations ORDER BY 1;" | rg -q '0002_par_readiness'
echo "=== adaptation quality ==="
sudo -n docker compose --env-file "$ENV" -f "$ROOT/deploy/observability/compose.yaml" \
  run --rm --no-deps \
  --entrypoint python adaptation-engine -m engineering_os.adaptation.quality
echo "=== reader cannot write control ==="
if sudo -n docker exec hermes-eos-postgres \
  psql -U hermes_control_reader -d hermes_control \
  -c "INSERT INTO adaptation_checkpoints(source) VALUES ('should-fail');" >/tmp/eos-adapt-reader-write.log 2>&1; then
  echo "FAIL: reader wrote control" >&2
  exit 1
fi
echo "PASS: reader cannot write control"
echo "=== resolver cannot mutate ==="
if sudo -n docker exec hermes-eos-postgres \
  psql -U hermes_control_resolver -d hermes_control \
  -c "UPDATE adaptation_kill_switch SET engaged = TRUE WHERE id = 1;" >/tmp/eos-adapt-resolver-write.log 2>&1; then
  echo "FAIL: resolver mutated control" >&2
  exit 1
fi
echo "PASS: resolver cannot mutate"
echo "=== operator cannot connect phoenix ==="
if sudo -n docker exec hermes-eos-postgres \
  psql -U hermes_control_operator -d phoenix -c "SELECT 1" >/tmp/eos-adapt-operator-phoenix.log 2>&1; then
  echo "FAIL: operator connected to phoenix" >&2
  exit 1
fi
echo "PASS: operator cannot connect phoenix"
echo "=== isolation counts ==="
PHOENIX="$(sudo -n docker exec hermes-eos-postgres \
  psql -U eos_admin -d phoenix -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';")"
HE="$(sudo -n docker exec hermes-eos-postgres \
  psql -U eos_admin -d hermes_engineering -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';")"
test "$PHOENIX" = "65"
test "$HE" = "46"
echo "phoenix=$PHOENIX hermes_engineering=$HE"
echo "=== production policy from fixture ==="
LEAK="$(sudo -n docker exec hermes-eos-postgres \
  psql -U eos_admin -d hermes_control -tAc \
  "SELECT COUNT(*) FROM adaptation_policy_bundles WHERE scope LIKE 'PRODUCTION%' AND coalesce(spec->>'source_classification','') = 'TEST_ONLY';")"
test "$LEAK" = "0"
echo "=== test approval production ==="
TAP="$(sudo -n docker exec hermes-eos-postgres \
  psql -U eos_admin -d hermes_control -tAc \
  "SELECT COUNT(*) FROM adaptation_approvals WHERE approval_class='TEST' AND scope LIKE 'PRODUCTION%' AND state='GRANTED';")"
test "$TAP" = "0"
echo "=== rollback still assigning ==="
RB="$(sudo -n docker exec hermes-eos-postgres \
  psql -U eos_admin -d hermes_control -tAc \
  "SELECT COUNT(*) FROM adaptation_bindings WHERE is_current AND state IN ('ROLLED_BACK','DISABLED') AND mode='CANARY';")"
test "$RB" = "0"
echo "PASS: verify-adaptation-data"
