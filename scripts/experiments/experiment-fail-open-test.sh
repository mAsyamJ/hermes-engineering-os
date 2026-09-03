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
EVIDENCE="$ROOT/evidence/phase6/fail-open"
mkdir -p "$EVIDENCE"
PY="/home/ubuntu/.hermes/hermes-agent/venv/bin/python"

assert_core() {
  "$DR" /api/plugins/engineering-os/health --expect-status 200 --quiet
  curl -fsS http://127.0.0.1:6006/healthz >/dev/null
  test "$(ps -p 924 -o pid= | tr -d ' ')" = "924"
  test "$(ps -p 2381797 -o pid= | tr -d ' ')" = "2381797"
}

hashes_before() {
  sudo -n docker exec hermes-eos-postgres \
    psql -U eos_admin -d hermes_engineering -tAc \
    "SELECT coalesce(string_agg(assignment_hash, ',' ORDER BY assignment_hash), '') FROM experiment_assignments;"
}

echo "=== A experiment sidecar unavailable ==="
"${COMPOSE[@]}" stop analytics-api >/dev/null
sleep 1
assert_core
python3 "$DR" /api/plugins/engineering-os/health >"$EVIDENCE/a-health.json"
python3 "$DR" /api/plugins/engineering-os/experiments >"$EVIDENCE/a-experiments.json"
python3 "$DR" /api/plugins/engineering-os/analytics >"$EVIDENCE/a-analytics.json"
python3 - "$EVIDENCE" <<'PY'
import json, sys
from pathlib import Path
evidence = Path(sys.argv[1])
health = json.loads(evidence.joinpath("a-health.json").read_text())["data"]
experiments = json.loads(evidence.joinpath("a-experiments.json").read_text())["data"]
analytics = json.loads(evidence.joinpath("a-analytics.json").read_text())["data"]
assert health.get("status") == "AVAILABLE", health
assert experiments.get("status") == "DEGRADED", experiments
assert analytics.get("status") == "DEGRADED", analytics
print("A health", health.get("status"), "experiments", experiments.get("status"))
PY
"${COMPOSE[@]}" start analytics-api >/dev/null
for _ in $(seq 1 20); do
  if curl -fsS http://127.0.0.1:9120/health >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
echo "PASS: A"

BEFORE="$(hashes_before)"

lock_and_run() {
  local label="$1"
  local outfile="$2"
  shift 2
  sudo -n docker exec hermes-eos-postgres \
    psql -U eos_admin -d hermes_engineering -c \
    "SELECT pg_advisory_lock(620260827); SELECT pg_sleep(20); SELECT pg_advisory_unlock(620260827);" \
    >"$EVIDENCE/${label}-lock.log" &
  local lockpid=$!
  sleep 1
  "$ROOT/scripts/experiments/experiment.sh" "$@" >"$outfile" || true
  wait "$lockpid" || true
  python3 - "$outfile" <<'PY'
import json, sys
from pathlib import Path
text = Path(sys.argv[1]).read_text()
start = text.find("{")
payload = json.loads(text[start:])
assert payload.get("status") == "locked", payload
print("locked", payload.get("detail"))
PY
}

echo "=== B registration kill / lock held ==="
lock_and_run b "$EVIDENCE/b-locked.json" preregister fixture-aa-v1
echo "PASS: B"

echo "=== C last-good retained ==="
COUNT="$(sudo -n docker exec hermes-eos-postgres psql -U eos_admin -d hermes_engineering -tAc \
  "SELECT COUNT(*) FROM experiment_results WHERE is_current")"
test "$COUNT" -ge 1
curl -fsS http://127.0.0.1:9120/experiments/health >"$EVIDENCE/c-health.json"
echo "PASS: C last-good n=$COUNT"

echo "=== D Phase 4 unavailable (no observations → not confirmatory) ==="
PYTHONPATH="$ROOT" EOS_EVAL_SANDBOX=inline PYTHONDONTWRITEBYTECODE=1 \
  "$PY" - <<'PY' >"$EVIDENCE/d-phase4.json"
from engineering_os.experiments.definitions import load_id
from engineering_os.experiments.assignment import assign_paired
from engineering_os.experiments.analyze import analyze
from engineering_os.experiments.preregister import freeze
protocol = freeze(load_id("fixture-aa-v1"))
assignments = assign_paired(
    [{"pair_id": f"p{i}", "case_id": f"c{i}", "stratum": "s"} for i in range(8)],
    protocol["assignment"]["seed"],
    protocol["control"]["variant_id"],
    protocol["candidate"]["variant_id"],
)
result = analyze(protocol, assignments, [], final=True)
assert result["blocked"] == "BLOCKED_HORIZON"
assert result["conclusion"] not in {"EVIDENCE_FOR_CANDIDATE", "EVIDENCE_AGAINST_CANDIDATE"}
print("D", result["blocked"], result["conclusion"])
PY
echo "PASS: D"

echo "=== E Phoenix unavailable derived remains readable ==="
curl -fsS http://127.0.0.1:9120/experiments/health >/dev/null
curl -fsS http://127.0.0.1:9120/experiments >/dev/null
assert_core
echo "PASS: E"

echo "=== F GitHub BLOCKED_AUTH non-blocking ==="
python3 "$DR" /api/plugins/engineering-os/experiments --expect-status 200 --quiet
echo "PASS: F"

echo "=== G duplicate controller ==="
lock_and_run g "$EVIDENCE/g-locked.json" analyze fixture-aa-v1 --final
echo "PASS: G"

echo "=== H config drift detected ==="
PYTHONPATH="$ROOT" PYTHONDONTWRITEBYTECODE=1 \
  "$PY" - <<'PY' >"$EVIDENCE/h-drift.json"
from engineering_os.experiments.drift import detect
events = detect(
    {"environment_hash": "aaa", "control": {"config_hash": "c1"}, "candidate": {"config_hash": "d1"}},
    {"environment_hash": "bbb", "control": {"config_hash": "c1"}, "candidate": {"config_hash": "d2"}},
)
assert any(item["dimension"] == "environment" for item in events)
assert any(item["dimension"] == "candidate_variant" for item in events)
print("H", events)
PY
echo "PASS: H"

echo "=== I assignment kill ==="
lock_and_run i "$EVIDENCE/i-locked.json" assign fixture-aa-v1
echo "PASS: I"

echo "=== J collector / analysis kill + data-quality verifier ==="
lock_and_run j-collect "$EVIDENCE/j-collect-locked.json" collect fixture-aa-v1
lock_and_run j-analyze "$EVIDENCE/j-analyze-locked.json" analyze fixture-aa-v1 --final
"$ROOT/scripts/verification/verify-experiment-data.sh" | tee "$EVIDENCE/j-verify.log"
echo "PASS: J"

echo "=== K memory/workspace contamination ==="
PYTHONPATH="$ROOT" PYTHONDONTWRITEBYTECODE=1 \
  "$PY" - <<'PY' >"$EVIDENCE/k-isolation.json"
from pathlib import Path
from tempfile import TemporaryDirectory
from engineering_os.experiments.isolation import memory_ok, workspace_ok
with TemporaryDirectory() as tmp:
    control = Path(tmp) / "c"
    candidate = Path(tmp) / "t"
    control.mkdir()
    candidate.mkdir()
    (control / "a.txt").write_text("1")
    (candidate / "a.txt").write_text("1")
    ok = workspace_ok(control, candidate)
    assert ok["ok"]
    shared = workspace_ok(control, control)
    assert not shared["ok"]
fixture = memory_ok(None, None, fixture=True)
assert fixture["ok"] and fixture["state"] == "PASS"
blocked = memory_ok(None, None, fixture=False)
assert blocked["state"] == "BLOCKED_CAPABILITY"
shared_ns = memory_ok("same", "same", fixture=False)
assert shared_ns["state"] == "FAIL"
print("K workspace", ok["ok"], "memory fixture", fixture["state"], "cognition", blocked["state"])
PY
echo "PASS: K"

echo "=== L budget exhaustion / no silent shrink ==="
PYTHONPATH="$ROOT" PYTHONDONTWRITEBYTECODE=1 \
  "$PY" - <<'PY' >"$EVIDENCE/l-budget.json"
from engineering_os.experiments.plan import plan_binary
result = plan_binary(
    baseline_rate=0.1, mde=0.5, alpha=0.05, power=0.8,
    allocation_ratio=1.0, max_units=4, max_llm_calls=0,
    requires_llm=False, paired=True, discordance=0.8,
)
assert result["status"] == "INFEASIBLE_BUDGET"
assert result["planned_n"] > 4
print("L", result["status"], result["planned_n"])
llm = plan_binary(
    baseline_rate=0.5, mde=0.2, alpha=0.05, power=0.8,
    allocation_ratio=1.0, max_units=100, max_llm_calls=0,
    requires_llm=True, paired=False,
)
assert llm["status"] == "INFEASIBLE_BUDGET"
print("L llm", llm["reason"])
PY
echo "PASS: L"

echo "=== M ITT fallback ==="
PYTHONPATH="$ROOT" PYTHONDONTWRITEBYTECODE=1 \
  "$PY" - <<'PY' >"$EVIDENCE/m-itt.json"
from engineering_os.experiments.exposure import record
row = record({"unit_id": "u1", "variant_id": "cand", "variant_role": "CANDIDATE", "assigned_config_hash": "cand"}, "ctrl", True)
assert row["fidelity"] == "NONCOMPLIANT"
assert row["itt_variant_role"] == "CANDIDATE"
assert row["reassigned"] is False
print("M", row)
PY
echo "PASS: M"

echo "=== N premature final analysis ==="
PYTHONPATH="$ROOT" EOS_EVAL_SANDBOX=inline PYTHONDONTWRITEBYTECODE=1 \
  "$PY" - <<'PY' >"$EVIDENCE/n-peeking.json"
from engineering_os.experiments.definitions import load_id
from engineering_os.experiments.assignment import assign_paired
from engineering_os.experiments.analyze import analyze
from engineering_os.experiments.preregister import freeze
protocol = freeze(load_id("fixture-aa-v1"))
assignments = assign_paired(
    [{"pair_id": f"p{i}", "case_id": f"c{i}", "stratum": "s"} for i in range(8)],
    protocol["assignment"]["seed"],
    protocol["control"]["variant_id"],
    protocol["candidate"]["variant_id"],
)
result = analyze(protocol, assignments, [], final=True)
assert result["blocked"] == "BLOCKED_HORIZON", result
assert result["conclusion"] == "COLLECTING", result
print("N", result["blocked"], result["conclusion"])
PY
echo "PASS: N"

echo "=== O production scope / command injection / guardrail stop ==="
PYTHONPATH="$ROOT" PYTHONDONTWRITEBYTECODE=1 \
  "$PY" - <<'PY' >"$EVIDENCE/o-rejected.json"
from engineering_os.experiments.definitions import DefinitionError, validate_raw
from engineering_os.experiments.guardrails import evaluate
base = {
    "experiment_id": "x", "version": "1", "scope": "FIXTURE", "design": "INDEPENDENT",
    "treatment_dimension": "NONE", "hypothesis": "no", "expected_direction": "NONE",
    "experimental_unit": "x", "control": {"variant_id": "c", "variant_name": "c", "artifact": "a"},
    "candidate": {"variant_id": "t", "variant_name": "t", "artifact": "a"},
    "assignment": {"algorithm": "assign-hmac-sha256-v1", "seed": "s"},
    "primary_metric": {"id": "phase4.quality_vector.tests", "type": "binary"},
    "guardrails": [{"id": "llm_call_count", "fail_on": ">0"}],
    "sample_plan": {"planned_n": 2, "alpha": 0.05, "power": 0.8, "mde": 0.5},
    "analysis": {"population": "INTENTION_TO_TREAT", "method": "independent-binary-wilson-v1", "horizon": "FIXED"},
    "budget": {"max_units": 2, "max_llm_calls": 0},
}
try:
    validate_raw({**base, "scope": "PRODUCTION"})
    raise SystemExit("PRODUCTION should be rejected")
except DefinitionError as exc:
    print("O production", exc)
try:
    validate_raw({**base, "command": "rm -rf /"})
    raise SystemExit("command key should be rejected")
except DefinitionError as exc:
    print("O command", exc)
guard = evaluate(
    {"guardrails": [{"id": "llm_call_count", "fail_on": ">0"}]},
    [],
    llm_calls=1,
)
assert guard["stop"] is True
assert guard["auto_route"] is False
print("O guardrail", guard["reason"])
PY
echo "PASS: O"

AFTER="$(hashes_before)"
test "$BEFORE" = "$AFTER"
assert_core
echo "PASS: experiment fail-open A-O (Hermes still AVAILABLE; assignment hashes unchanged)"
