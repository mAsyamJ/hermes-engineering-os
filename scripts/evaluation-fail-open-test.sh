#!/usr/bin/env bash
set -euo pipefail
# Fail-open A, B, E, F, J for Phase 4. Does not stop Phoenix or gateways.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
ENV="$ROOT/deploy/observability/.env"
# shellcheck disable=SC1090
set -a
source "$ENV"
set +a
COMPOSE=(sudo -n docker compose --env-file "$ENV" -f "$ROOT/deploy/observability/compose.yaml")
DR="$ROOT/scripts/dashboard-request.py"
EVIDENCE="$ROOT/evidence/phase4/fail-open"
mkdir -p "$EVIDENCE"

assert_core() {
  "$DR" /api/plugins/engineering-os/health --expect-status 200 --quiet
  curl -fsS http://127.0.0.1:6006/healthz >/dev/null
  test "$(ps -p 924 -o pid= | tr -d ' ')" = "924"
  test "$(ps -p 2381797 -o pid= | tr -d ' ')" = "2381797"
}

echo "=== A evaluation DB / sidecar unavailable ==="
"${COMPOSE[@]}" stop analytics-api >/dev/null
sleep 1
assert_core
python3 "$DR" /api/plugins/engineering-os/health >"$EVIDENCE/a-health.json"
python3 "$DR" /api/plugins/engineering-os/evaluations >"$EVIDENCE/a-evaluations.json"
python3 "$DR" /api/plugins/engineering-os/analytics >"$EVIDENCE/a-analytics.json"
python3 - "$EVIDENCE" <<'PY'
import json, sys
from pathlib import Path
evidence = Path(sys.argv[1])
health = json.loads(evidence.joinpath("a-health.json").read_text())["data"]
evaluations = json.loads(evidence.joinpath("a-evaluations.json").read_text())["data"]
analytics = json.loads(evidence.joinpath("a-analytics.json").read_text())["data"]
assert health.get("status") == "AVAILABLE", health
assert evaluations.get("status") == "DEGRADED", evaluations
assert analytics.get("status") == "DEGRADED", analytics
print("A health", health.get("status"), "evaluations", evaluations.get("status"))
PY
"${COMPOSE[@]}" start analytics-api >/dev/null
for _ in $(seq 1 20); do
  if curl -fsS http://127.0.0.1:9120/health >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
echo "PASS: A"

echo "=== J GitHub BLOCKED_AUTH non-blocking ==="
PYTHONPATH="$ROOT" EOS_EVAL_SANDBOX=inline python3 - <<'PY'
from pathlib import Path
from engineering_os.evaluation.engine import evaluate_trees
from engineering_os.evaluation.profiles import load_profile
profile = load_profile("fixture")
tree = Path("/opt/hermes-engineering-os/tests/evaluation/fixture_src")
payload = evaluate_trees(tree, profile, baseline=tree, github_state="BLOCKED_AUTH")
assert payload["quality_vector"]["ci"] == "BLOCKED_AUTH"
assert payload["quality_vector"]["tests"] == "PASS"
print("J BLOCKED_AUTH with tests", payload["quality_vector"]["tests"])
PY
assert_core
echo "PASS: J"

echo "=== F missing artifact ==="
PYTHONPATH="$ROOT" python3 - <<'PY'
from engineering_os.evaluation.eligibility import classify_task
decision = classify_task({"id": "t_missing"}, git={}, cohort="production")
assert decision["eligibility"] == "INSUFFICIENT_EVIDENCE"
print("F", decision)
PY
echo "PASS: F"

echo "=== B sandbox runner failure ==="
PYTHONPATH="$ROOT" python3 - <<'PY'
from pathlib import Path
from unittest.mock import patch
from engineering_os.evaluation.engine import _command_result
from engineering_os.evaluation.sandbox import SandboxResult, run_docker
tree = Path("/opt/hermes-engineering-os/tests/evaluation/fixture_src")
ran = run_docker(["python3", "-c", "print(1)"], tree, image="hermes-eos-missing:phase4")
assert ran.detail == "sandbox_runner_failure" or ran.exit_code not in {0}, ran
fake = SandboxResult(1, "", "Unable to find image", 5, False, False, "missing", "none", "sandbox_runner_failure")
with patch("engineering_os.evaluation.sandbox.run_command", return_value=fake):
    result = _command_result(["true"], Path("."), 1)
assert result["verdict"] == "ERROR", result
print("B runner", ran.detail, ran.exit_code, "mapped", result["verdict"])
PY
assert_core
echo "PASS: B"

echo "=== C candidate timeout ==="
PYTHONPATH="$ROOT" python3 - <<'PY'
from pathlib import Path
from engineering_os.evaluation.sandbox import run_inline
tree = Path("/opt/hermes-engineering-os/tests/evaluation/fixture_src")
ran = run_inline(["python3", "-c", "import time; time.sleep(8)"], tree, timeout_seconds=1)
assert ran.timeout, ran
assert ran.duration_ms < 8000
print("C timeout", ran.duration_ms, "ms")
PY
assert_core
echo "PASS: C"

echo "=== D candidate OOM/resource ==="
PYTHONPATH="$ROOT" python3 - <<'PY'
from pathlib import Path
from engineering_os.evaluation.sandbox import run_docker
tree = Path("/opt/hermes-engineering-os/tests/evaluation/fixture_src")
ran = run_docker(
    ["python3", "-c", "x = bytearray(512 * 1024 * 1024)"],
    tree,
    timeout_seconds=20,
    memory="32m",
)
assert ran.resource_failure or ran.exit_code in {137, 139, 1, None}, ran
print("D resource", ran.exit_code, ran.resource_failure, ran.detail)
PY
assert_core
echo "PASS: D"

echo "=== E Phoenix unavailable during projection ==="
PYTHONPATH="$ROOT" PHOENIX_BASE=http://127.0.0.1:1 python3 - <<'PY'
from engineering_os.evaluation.project import project_vector
result = project_vector(
    "3c6a188a33999ef09cf0bc74c2cae76b",
    "00000000-0000-0000-0000-000000000001",
    {"correctness": "PASS", "tests": "PASS", "regression": "UNCHANGED_PASS", "build": "PASS"},
)
assert result["status"] == "DEGRADED", result
assert result.get("canonical") is False
print("E projection", result["status"])
PY
curl -fsS http://127.0.0.1:6006/healthz >/dev/null
assert_core
echo "PASS: E"

echo "=== G duplicate scheduler lock ==="
sudo -n docker exec hermes-eos-postgres psql -U hermes_engineering -d hermes_engineering \
  -c "SELECT pg_advisory_lock(420260827); SELECT pg_sleep(20); SELECT pg_advisory_unlock(420260827);" \
  >"$EVIDENCE/g-lock.log" 2>&1 &
LOCKPID=$!
sleep 2
"$ROOT/scripts/evaluate.sh" --incremental --json >"$EVIDENCE/g.json"
python3 - "$EVIDENCE/g.json" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text().strip().splitlines()[-1])
assert payload.get("status") == "locked", payload
print("G locked")
PY
wait "$LOCKPID" || true
assert_core
echo "PASS: G"

echo "=== H killed mid-run transaction integrity ==="
BEFORE=$(sudo -n docker exec hermes-eos-postgres psql -U hermes_engineering -d hermes_engineering -tAc \
  "SELECT count(*) FROM evaluation_runs r LEFT JOIN evaluation_summaries s USING (evaluation_run_id) WHERE s.evaluation_run_id IS NULL")
"${COMPOSE[@]}" run --rm --no-deps --name eos-eval-kill-test \
  --entrypoint python evaluation-engine -m engineering_os.evaluation --incremental --json \
  >"$EVIDENCE/h-kill.log" 2>&1 &
DPID=$!
sleep 2
sudo -n docker kill eos-eval-kill-test >/dev/null 2>&1 || true
wait "$DPID" || true
sudo -n docker rm -f eos-eval-kill-test >/dev/null 2>&1 || true
AFTER=$(sudo -n docker exec hermes-eos-postgres psql -U hermes_engineering -d hermes_engineering -tAc \
  "SELECT count(*) FROM evaluation_runs r LEFT JOIN evaluation_summaries s USING (evaluation_run_id) WHERE s.evaluation_run_id IS NULL")
test "$AFTER" = "0"
echo "H orphans before=$BEFORE after=$AFTER"
assert_core
echo "PASS: H"

echo "=== I analytics lock does not block evaluation ==="
sudo -n docker exec hermes-eos-postgres psql -U hermes_engineering -d hermes_engineering \
  -c "SELECT pg_advisory_lock(320260827); SELECT pg_sleep(20); SELECT pg_advisory_unlock(320260827);" \
  >"$EVIDENCE/i-lock.log" 2>&1 &
ALOCK=$!
sleep 2
"$ROOT/scripts/evaluate.sh" --incremental --json >"$EVIDENCE/i.json"
python3 - "$EVIDENCE/i.json" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text().strip().splitlines()[-1])
assert payload.get("status") in {"success", "locked"}, payload
assert payload.get("status") != "locked" or True
# Evaluation uses 420260827; analytics lock must not force evaluation locked.
assert payload.get("status") == "success", payload
print("I evaluation", payload.get("status"), "scanned", payload.get("tasks_scanned"))
PY
wait "$ALOCK" || true
assert_core
echo "PASS: I"

echo "PASS: Phase 4 fail-open subset"
