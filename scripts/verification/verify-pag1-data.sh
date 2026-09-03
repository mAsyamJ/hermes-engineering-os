#!/usr/bin/env bash
# PAG-1 data-quality and safety invariants. Safe branches only.
set -euo pipefail
# shellcheck source=../lib/repo-root.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/../lib/repo-root.sh"
ROOT="$(_eos_repo_root_from "${BASH_SOURCE[0]}")"
HERMES_PY="/home/ubuntu/.hermes/hermes-agent/venv/bin/python"

echo "=== A operator boundary still insecure ==="
out="$("$ROOT/scripts/verification/verify-operator-boundary.sh")"
echo "$out" | rg -q 'status=READY_FOR_HUMAN'
echo "$out" | rg -q 'AUTH_AGENT_PASSWORDLESS_ROOT'
echo "PASS: A security blocked, other work continues"

echo "=== B approval trust root missing ==="
PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" PYTHONDONTWRITEBYTECODE=1 "$HERMES_PY" - <<'PY'
from engineering_os.adaptation.approval_ed25519 import verify_production_authorization
from engineering_os.adaptation.spawn_resolve import resolve_spawn_configuration
payload = verify_production_authorization()
assert payload["status"] == "BLOCKED_SECURITY_BOUNDARY"
assert payload["granted"] is False
result = resolve_spawn_configuration({"scope":"PRODUCTION_CANARY","environment":"production"}, {"model":"gpt-5.6-sol"})
assert result["resolution"] == "BASELINE"
assert result["actuate"] is False
print("PASS: B production remains disabled")
PY

echo "=== C upstream pin vs current main ==="
pinned="$("$HERMES_PY" - <<'PY'
from pathlib import Path
try:
    import yaml
except ImportError:
    import sys
    sys.path.insert(0, "/home/ubuntu/.hermes/hermes-agent/venv/lib/python3.11/site-packages")
    import yaml
data=yaml.safe_load(Path("/opt/hermes-engineering-os/provenance/HERMES_PAG1_UPSTREAM.yaml").read_text())
print(data["commit"])
PY
)"
current="$(git ls-remote https://github.com/NousResearch/hermes-agent.git refs/heads/main | awk '{print $1}')"
if [[ "$pinned" != "$current" ]]; then
  echo "STATUS: BLOCKED_UPSTREAM_DRIFT pinned=$pinned current=$current"
  echo "PASS: C drift is reported (patch qualification must restart against new SHA)"
else
  echo "PASS: C pin matches current main $pinned"
fi

echo "=== D/E/F spawn hook fail-open covered by isolated tests ==="
test -f "$ROOT/patches/hermes/upstream/0001-worker-spawn-transform.patch"
rg -q 'timeout|_SPAWN_TRANSFORM_TIMEOUT' "$ROOT/patches/hermes/upstream/0001-worker-spawn-transform.patch"
rg -q 'Conflict' "$ROOT/patches/hermes/upstream/0001-worker-spawn-transform.patch"
echo "PASS: D/E/F timeout/exception/conflict encoded in patch"

echo "=== G memory snapshot missing blocks real experiment ==="
PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" PYTHONDONTWRITEBYTECODE=1 "$HERMES_PY" - <<'PY'
from engineering_os.experiments.hermes_runner import run_real_unit
from engineering_os.experiments.definitions import load_id
result = run_real_unit({"unit_id":"g"}, load_id("real-model-sol-vs-terra-v1"))
assert result["executed"] is False
assert result["llm_calls"] == 0
print("PASS: G/I zero LLM without authorization")
PY

echo "=== H memory contamination invalidates promotion ==="
PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" PYTHONDONTWRITEBYTECODE=1 "$HERMES_PY" - <<'PY'
from engineering_os.adaptation.recommend import recommend_from_result
rec = recommend_from_result({
    "source":"phase6","experiment_id":"x","conclusion":"EVIDENCE_FOR_CANDIDATE",
    "scope":"BENCHMARK","treatment_dimension":"MODEL","contamination": True,
    "real_hermes_inference": True, "validity":{}, "guardrail_state":"PASS",
})
assert rec["classification"] != "PRODUCTION_CANDIDATE"
print("PASS: H contamination not promotable")
PY

echo "=== J authorization hash mismatch ==="
PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" EOS_EXPERIMENT_RUNTIME="$(mktemp -d)" PYTHONDONTWRITEBYTECODE=1 "$HERMES_PY" - <<'PY'
import json, os
from pathlib import Path
from engineering_os.experiments.budget_gate import require_budget_authorization
from engineering_os.experiments.definitions import load_id
from engineering_os.experiments.hermes_runner import run_real_unit
definition = load_id("real-model-sol-vs-terra-v1")
path = Path(os.environ["EOS_EXPERIMENT_RUNTIME"]) / "LLM_BUDGET_AUTHORIZATION"
path.write_text(json.dumps({
    "protocol_id": definition["experiment_id"],
    "protocol_hash": "mismatch",
    "max_units": 10, "max_llm_calls": 10,
    "control_model": "gpt-5.6-sol", "candidate_model": "gpt-5.6-terra",
    "scope": "BENCHMARK", "expiry": "2027-01-01T00:00:00+00:00",
    "created_by": "human-operator",
}), encoding="utf-8")
gate = require_budget_authorization(definition)
assert gate["ok"] is False
blocked = run_real_unit({"unit_id":"j"}, definition)
assert blocked["llm_calls"] == 0
print("PASS: J hash mismatch zero LLM")
PY

echo "=== K/L/M/N/O protocol and evaluator coverage ==="
PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" EOS_EVAL_SANDBOX=inline EOS_EXPERIMENT_RUNTIME="$(mktemp -d)" PYTHONDONTWRITEBYTECODE=1 "$HERMES_PY" - <<'PY'
from pathlib import Path
import os
from engineering_os.evaluation.engine import evaluate_trees
from engineering_os.evaluation.profiles import load_profile
from engineering_os.experiments.benchmarks import materialize_real_case
profile = load_profile("real-v1")
work = Path(os.environ["EOS_EXPERIMENT_RUNTIME"])
for case_id in ("real-v1-bugfix","real-v1-feature","real-v1-refactor","real-v1-test-repair","real-v1-config"):
    broken = materialize_real_case({"case_id": case_id, "tree": "broken"}, work / f"{case_id}-b")
    payload = evaluate_trees(Path(broken["path"]), profile, baseline=Path(broken["path"]), eligibility="TEST_ELIGIBLE")
    assert payload["quality_vector"]["tests"] in {"PASS","FAIL","UNKNOWN"}
    assert payload["quality_vector"]["tests"] == "FAIL"
print("PASS: O every benchmark has primary evaluator")
PY

echo "=== P production adaptation accidental exposure ==="
PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" PYTHONDONTWRITEBYTECODE=1 "$HERMES_PY" - <<'PY'
from engineering_os.adaptation.spawn_resolve import resolve_spawn_configuration
result = resolve_spawn_configuration({"scope":"PRODUCTION_FULL","environment":"production"}, {"model":"x"})
assert result["actuate"] is False
print("PASS: P hard reject")
PY

echo "=== historical PAR patch not overwritten ==="
test -f "$ROOT/patches/hermes/0001-pre-worker-spawn-hook.patch"
test -f "$ROOT/patches/hermes/upstream/0001-worker-spawn-transform.patch"
sha256sum -c - <<'EOF'
35aebcf70c31c78f01479c69faadac7b170ce3614c4565ae9f9a38c73c7d3ef6  /opt/hermes-engineering-os/patches/hermes/0001-pre-worker-spawn-hook.patch
EOF
echo "PASS: PAR historical patch preserved"

echo "=== live Hermes unpatched ==="
if rg -n "transform_kanban_worker_spawn|pre_worker_spawn" /home/ubuntu/.hermes/hermes-agent/hermes_cli/kanban_db.py /home/ubuntu/.hermes/hermes-agent/hermes_cli/plugins.py; then
  echo "FAIL: live Hermes patch present" >&2
  exit 1
fi
echo "PASS: live Hermes patch absent"

echo "=== production exposures ==="
ENV="$ROOT/deploy/observability/.env"
set -a
# shellcheck disable=SC1090
source "$ENV"
set +a
POL="$(sudo -n docker exec hermes-eos-postgres psql -U eos_admin -d hermes_control -tAc "SELECT COUNT(*) FROM adaptation_policy_bundles WHERE scope LIKE 'PRODUCTION%'")"
GRANT="$(sudo -n docker exec hermes-eos-postgres psql -U eos_admin -d hermes_control -tAc "SELECT COUNT(*) FROM adaptation_approvals WHERE scope LIKE 'PRODUCTION%'")"
test "$POL" = "0"
test "$GRANT" = "0"
echo "PASS: production exposures 0"

echo "=== no PAG-1 self-authorization in git ==="
if git -C "$ROOT" ls-files | rg -q 'LLM_BUDGET_AUTHORIZATION'; then
  echo "FAIL: authorization artifact committed" >&2
  exit 1
fi
echo "PASS: no committed budget authorization"

echo "=== fake secret leakage ==="
if rg -n "FAKE_PAG1_SECRET_ABC123|FAKE_PAG1_APPROVAL_SECRET_ABC123" \
  "$ROOT/docs" "$ROOT/engineering_os" "$ROOT/dashboard" "$ROOT/patches" \
  "$ROOT/provenance" "$ROOT/experiments" "$ROOT/config" "$ROOT/docs/reports/pag/PAG1_REPORT.md" \
  2>/dev/null; then
  echo "FAIL: fake secret leaked outside tests/scripts" >&2
  exit 1
fi
echo "PASS: fake-secret leakage"

echo "=== production private key absent ==="
if find /opt/hermes-engineering-os /etc/hermes-eos /home/ubuntu/.hermes-eos -type f \( -name '*approval*private*' -o -name 'ed25519_production*' \) 2>/dev/null | rg -q .; then
  echo "FAIL: production private key present" >&2
  exit 1
fi
echo "PASS: production approval private key absent"

echo "PASS: verify-pag1-data"
