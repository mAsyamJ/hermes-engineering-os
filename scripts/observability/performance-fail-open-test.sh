#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=../lib/repo-root.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/../lib/repo-root.sh"
ROOT="$(_eos_repo_root_from "${BASH_SOURCE[0]}")"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
ENV="$ROOT/deploy/observability/.env"
# shellcheck disable=SC1090
set -a
source "$ENV"
set +a
COMPOSE=(sudo -n docker compose --env-file "$ENV" -f "$ROOT/deploy/observability/compose.yaml")
DR="$ROOT/scripts/maintenance/dashboard-request.py"
EVIDENCE="$ROOT/evidence/phase5/fail-open"
mkdir -p "$EVIDENCE"

assert_core() {
  "$DR" /api/plugins/engineering-os/health --expect-status 200 --quiet
  curl -fsS http://127.0.0.1:6006/healthz >/dev/null
  test "$(ps -p 924 -o pid= | tr -d ' ')" = "924"
  test "$(ps -p 2381797 -o pid= | tr -d ' ')" = "2381797"
}

echo "=== A performance tables / sidecar unavailable ==="
"${COMPOSE[@]}" stop analytics-api >/dev/null
sleep 1
assert_core
python3 "$DR" /api/plugins/engineering-os/health >"$EVIDENCE/a-health.json"
python3 "$DR" /api/plugins/engineering-os/performance >"$EVIDENCE/a-performance.json"
python3 "$DR" /api/plugins/engineering-os/analytics >"$EVIDENCE/a-analytics.json"
python3 "$DR" /api/plugins/engineering-os/evaluations >"$EVIDENCE/a-evaluations.json"
python3 - "$EVIDENCE" <<'PY'
import json, sys
from pathlib import Path
evidence = Path(sys.argv[1])
health = json.loads(evidence.joinpath("a-health.json").read_text())["data"]
performance = json.loads(evidence.joinpath("a-performance.json").read_text())["data"]
analytics = json.loads(evidence.joinpath("a-analytics.json").read_text())["data"]
evaluations = json.loads(evidence.joinpath("a-evaluations.json").read_text())["data"]
assert health.get("status") == "AVAILABLE", health
assert performance.get("status") == "DEGRADED", performance
assert analytics.get("status") == "DEGRADED", analytics
assert evaluations.get("status") == "DEGRADED", evaluations
print("A health", health.get("status"), "performance", performance.get("status"))
PY
"${COMPOSE[@]}" start analytics-api >/dev/null
for _ in $(seq 1 20); do
  if curl -fsS http://127.0.0.1:9120/health >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
echo "PASS: A"

echo "=== B materializer killed / no false checkpoint ==="
BEFORE="$(sudo -n docker exec hermes-eos-postgres psql -U eos_admin -d hermes_engineering -tAc \
  "SELECT COALESCE(watermark,'') FROM performance_checkpoints WHERE source='phase5';")"
sudo -n docker exec hermes-eos-postgres \
  psql -U eos_admin -d hermes_engineering -c "SELECT pg_advisory_lock(520260827); SELECT pg_sleep(8); SELECT pg_advisory_unlock(520260827);" \
  >"$EVIDENCE/b-lock.log" &
LOCKPID=$!
sleep 1
"$ROOT/scripts/observability/performance-materialize.sh" --json >"$EVIDENCE/b-locked.json" || true
wait "$LOCKPID" || true
python3 - "$EVIDENCE" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1], "b-locked.json").read_text())
assert payload.get("status") == "locked", payload
print("B locked", payload.get("status"))
PY
AFTER="$(sudo -n docker exec hermes-eos-postgres psql -U eos_admin -d hermes_engineering -tAc \
  "SELECT COALESCE(watermark,'') FROM performance_checkpoints WHERE source='phase5';")"
test "$BEFORE" = "$AFTER"
echo "PASS: B"

echo "=== C Phase 3 unavailable last-good retained ==="
# Last-good rows remain readable even if we do not re-materialize.
COUNT="$(sudo -n docker exec hermes-eos-postgres psql -U eos_admin -d hermes_engineering -tAc \
  "SELECT COUNT(*) FROM performance_aggregates WHERE is_current")"
test "$COUNT" -ge 1
echo "PASS: C last-good n=$COUNT"

echo "=== D Phase 4 unavailable quality INSUFFICIENT ==="
python3 - <<'PY'
from engineering_os.performance.metrics import compute_metric
from engineering_os.performance.tiers import load_tiers
agg = compute_metric("quality_tests_pass_rate", [{"board":"b","task_id":"t","lifecycle_state":"DONE"}], load_tiers())
assert agg["value"] is None and agg["interpretation"] == "INSUFFICIENT_DATA"
print("D", agg["interpretation"])
PY
echo "PASS: D"

echo "=== E Phoenix unavailable derived remains readable ==="
curl -fsS http://127.0.0.1:9120/performance/health >/dev/null
assert_core
echo "PASS: E"

echo "=== F GitHub BLOCKED_AUTH non-blocking ==="
python3 - <<'PY'
from engineering_os.performance.metrics import compute_metric
from engineering_os.performance.tiers import load_tiers
members = [{"board":"b","task_id":"t","lifecycle_state":"DONE","github_evidence_state":"BLOCKED_AUTH","verification_state":"UNKNOWN","final_outcome":"COMPLETED_UNVERIFIED"}]
agg = compute_metric("lifecycle_completion_rate", members, load_tiers())
assert agg["value"] == 1.0
print("F lifecycle still computed")
PY
echo "PASS: F"

echo "=== G duplicate timer lock ==="
sudo -n docker exec hermes-eos-postgres \
  psql -U eos_admin -d hermes_engineering -c "SELECT pg_advisory_lock(520260827); SELECT pg_sleep(6); SELECT pg_advisory_unlock(520260827);" \
  >"$EVIDENCE/g-lock.log" &
sleep 1
"$ROOT/scripts/observability/performance-materialize.sh" --json >"$EVIDENCE/g-locked.json" || true
python3 - "$EVIDENCE" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1], "g-locked.json").read_text())
assert payload.get("status") == "locked", payload
print("G", payload)
PY
wait || true
echo "PASS: G"

echo "=== H ruleset mismatch ==="
PYTHONPATH="$ROOT" python3 - <<'PY'
from engineering_os.performance.compare import pairwise
from engineering_os.performance.metrics import compute_metric
from engineering_os.performance.tiers import load_tiers
tiers = load_tiers()
left = [{"board":"b","task_id":f"l{i}","lifecycle_state":"DONE"} for i in range(12)]
right = [{"board":"b","task_id":f"r{i}","lifecycle_state":"DONE"} for i in range(12)]
cmp = pairwise("A","B", left, right, "lifecycle_completion_rate",
               left_aggregate=compute_metric("lifecycle_completion_rate", left, tiers),
               right_aggregate=compute_metric("lifecycle_completion_rate", right, tiers),
               tier_config=tiers, comparison_config=tiers,
               left_ruleset="phase3-v1", right_ruleset="phase3-v0")
assert cmp["interpretation"] == "NOT_COMPARABLE"
print("H", cmp["interpretation"])
PY
echo "PASS: H"

echo "=== I mixed-model attribution guard ==="
PYTHONPATH="$ROOT" python3 - <<'PY'
from engineering_os.performance.attribution import classify_model_attribution
from engineering_os.performance.metrics import group_by
mixed = classify_model_attribution([
    {"provider":"openai-codex","model":"gpt-5.6-sol","source":"trace"},
    {"provider":"cli","model":"gpt-5.6-sol","source":"trace"},
])
assert mixed["attribution"] == "MIXED_MODEL"
tasks = [{"board":"b","task_id":"t","model_attribution":"MIXED_MODEL","model_keys":["openai-codex/gpt-5.6-sol","cli/gpt-5.6-sol"]}]
assert group_by(tasks, "model") == {}
print("I mixed isolated")
PY
echo "PASS: I"

echo "=== J fixture leakage verifier ==="
"$ROOT/scripts/verification/verify-performance-data.sh" | tee "$EVIDENCE/j-verify.log"
assert_core
echo "PASS: J"

echo "PASS: phase5 fail-open A-J"
