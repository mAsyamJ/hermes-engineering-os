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
EVIDENCE="$ROOT/evidence/phase7/fail-open"
mkdir -p "$EVIDENCE"
PY="/home/ubuntu/.hermes/hermes-agent/venv/bin/python"

assert_core() {
  "$DR" /api/plugins/engineering-os/health --expect-status 200 --quiet
  curl -fsS http://127.0.0.1:6006/healthz >/dev/null
  test "$(ps -p 924 -o pid= | tr -d ' ')" = "924"
  test "$(ps -p 2381797 -o pid= | tr -d ' ')" = "2381797"
}

echo "=== A sidecar unavailable ==="
"${COMPOSE[@]}" stop analytics-api >/dev/null
sleep 1
assert_core
python3 "$DR" /api/plugins/engineering-os/health >"$EVIDENCE/a-health.json"
python3 "$DR" /api/plugins/engineering-os/adaptation >"$EVIDENCE/a-adaptation.json"
python3 - "$EVIDENCE" <<'PY'
import json, sys
from pathlib import Path
evidence = Path(sys.argv[1])
health = json.loads(evidence.joinpath("a-health.json").read_text())["data"]
adapt = json.loads(evidence.joinpath("a-adaptation.json").read_text())["data"]
assert health.get("status") == "AVAILABLE", health
assert adapt.get("status") == "DEGRADED", adapt
print("A health", health.get("status"), "adaptation", adapt.get("status"))
PY
"${COMPOSE[@]}" start analytics-api >/dev/null
for _ in $(seq 1 20); do
  if curl -fsS http://127.0.0.1:9120/health >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
echo "PASS: A"

echo "=== B resolver missing cache -> baseline ==="
EOS_ADAPTATION_RUNTIME="$EVIDENCE/empty-runtime" "$PY" - <<'PY'
from engineering_os.adaptation.resolver import resolve_policy
d = resolve_policy({"board": "eos-phase6-exp", "task_class": "fixture", "environment": "fixture"})
assert d["resolution"] == "BASELINE", d
print("B", d["result"], d["reason"])
PY
echo "PASS: B"

echo "=== C corrupt cache -> baseline ==="
mkdir -p "$EVIDENCE/corrupt"
echo 'not-json' > "$EVIDENCE/corrupt/bindings.json"
EOS_ADAPTATION_RUNTIME="$EVIDENCE/corrupt" "$PY" - <<'PY'
from engineering_os.adaptation.resolver import resolve_policy
d = resolve_policy({"board": "eos-phase6-exp", "task_class": "fixture"})
assert d["resolution"] == "BASELINE", d
print("C", d["reason"])
PY
echo "PASS: C"

echo "=== D expired approval ==="
"$PY" - <<'PY'
from engineering_os.adaptation.approval import sign_test, verify_test
fields = {
    "stage": "A", "recommendation_id": "r", "policy_hash": "h", "policy_version": "1",
    "scope": "FIXTURE", "max_exposure": 1, "expires_at": "2020-01-01T00:00:00+00:00",
    "rollback_hash": "fb", "operator_identity": "t",
}
sig = sign_test(fields, key=b"k")
v = verify_test(fields, sig, key=b"k")
assert not v["ok"] and "expired" in v["reason"]
print("D", v)
PY
echo "PASS: D"

echo "=== E hash mismatch approval ==="
"$PY" - <<'PY'
from engineering_os.adaptation.approval import sign_test, verify_test
fields = {
    "stage": "A", "recommendation_id": "r", "policy_hash": "h", "policy_version": "1",
    "scope": "FIXTURE", "max_exposure": 1, "expires_at": "2027-01-01T00:00:00+00:00",
    "rollback_hash": "fb", "operator_identity": "t",
}
sig = sign_test(fields, key=b"k")
v = verify_test({**fields, "policy_hash": "other"}, sig, key=b"k")
assert not v["ok"]
print("E", v)
PY
echo "PASS: E"

echo "=== N conflict -> baseline ==="
"$PY" - <<'PY'
from engineering_os.adaptation.resolver import resolve_policy
from engineering_os.adaptation.schema import load_id
a = load_id("fixture-conflict-a-v1")
b = load_id("fixture-conflict-b-v1")
d = resolve_policy(
    {"board": "eos-phase6-exp", "task_class": "fixture"},
    {"kill_switch": False, "bindings": [
        {"policy_id": "a", "state": "ACTIVE", "mode": "CANARY", "spec": a, "selectors": a["selectors"]},
        {"policy_id": "b", "state": "ACTIVE", "mode": "CANARY", "spec": b, "selectors": b["selectors"]},
    ]},
)
assert d["result"] == "CONFLICT" and d["resolution"] == "BASELINE"
print("N", d["reason"])
PY
echo "PASS: N"

echo "=== O test approval production rejected ==="
"$PY" - <<'PY'
from engineering_os.adaptation.approval import sign_test, approve_production
try:
    sign_test({"scope": "PRODUCTION_FULL", "stage": "B"}, key=b"k")
    raise SystemExit("FAIL: signed production")
except Exception as exc:
    print("O sign rejected", type(exc).__name__)
blocked = approve_production()
assert blocked["status"] == "BLOCKED_APPROVAL_BOUNDARY"
assert blocked["granted"] is False
print("O production", blocked["status"])
PY
echo "PASS: O"

echo "=== P auto-disable bad canary ==="
"$PY" - <<'PY'
from engineering_os.adaptation.guardrails import evaluate, canary_health
guard = evaluate(
    [{"id": "phase4.quality_vector.tests", "fail_on": "FAIL", "critical": True, "min_n": 1, "candidate_only": True}],
    [{"selected": "CANDIDATE", "outcome": {"quality_vector": {"tests": "FAIL"}}}],
)
assert guard["auto_disable"] is True
assert guard["auto_promote"] is False
assert canary_health(guard, [{"selected": "CANDIDATE"}]) == "CANARY_UNHEALTHY"
print("P", guard["reason"])
PY
echo "PASS: P"

assert_core
echo "PASS: adaptation-fail-open-test"
