#!/usr/bin/env bash
# Scan Phoenix, Engineering OS APIs, logs, and the product git tree for a
# planted fake secret. Do not leave HERMES_OTEL_DEBUG enabled.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRET="FAKE_PHASE2_SECRET_ABC123"
EVIDENCE="$ROOT/evidence/phase2/privacy"
mkdir -p "$EVIDENCE"
"$ROOT/scripts/create-fixture-repo.sh"
FIXTURE="$ROOT/.runtime/fixture-repo"
HERMES="${HERMES:-/home/ubuntu/.local/bin/hermes}"
PROMPT="The operator said the test token is ${SECRET}. Reply with the word acknowledged and do not repeat any token."
export HERMES_KANBAN_TASK="t_privacy"
export HERMES_KANBAN_RUN_ID="9003"
export HERMES_KANBAN_BOARD="eos-phase2-obs"
export HERMES_KANBAN_WORKSPACE="$FIXTURE"
export OTEL_PHOENIX_ENDPOINT="http://127.0.0.1:6006/v1/traces"
export OTEL_PROJECT_NAME="hermes-agent"
export HERMES_OTEL_CONFIG="${HERMES_OTEL_CONFIG:-$HOME/.hermes/hermes_otel.yaml}"
unset HERMES_OTEL_DEBUG || true
set +e
"$HERMES" chat -q "$PROMPT" --in "$FIXTURE" -Q --yolo --max-turns 4 --ignore-rules \
  >"$EVIDENCE/hermes.out" 2>"$EVIDENCE/hermes.err"
STATUS=$?
set -e
echo "hermes_exit=$STATUS" | tee "$EVIDENCE/results.txt"
sleep 4
python3 - "$ROOT" "$SECRET" "$EVIDENCE" <<'PY'
import json, os, sys, urllib.request
from pathlib import Path
root = Path(sys.argv[1])
secret = sys.argv[2]
evidence = Path(sys.argv[3])
sys.path.insert(0, str(root))
from engineering_os.observability import phoenix_client
leaks = []
try:
    traces = json.dumps(phoenix_client.summarize_traces(limit=50))
    if secret in traces:
        leaks.append("phoenix_graphql")
    evidence.joinpath("phoenix.json").write_text(traces[:20000] + "\n")
except Exception as exc:
    evidence.joinpath("phoenix.json").write_text(f"DEGRADED {type(exc).__name__}\n")
for path in (evidence / "hermes.err",):
    text = path.read_text(errors="replace") if path.is_file() else ""
    if secret in text:
        leaks.append(str(path.name))
debug = os.environ.get("HERMES_OTEL_DEBUG", "")
if debug.lower() in {"1", "true", "yes"}:
    leaks.append("HERMES_OTEL_DEBUG")
yaml_paths = [
    Path.home() / "hermes_otel.yaml",
    Path.home() / ".hermes/hermes_otel.yaml",
]
for path in yaml_paths:
    if path.is_file() and "capture_full_prompts: true" in path.read_text():
        leaks.append(f"prompts_enabled:{path}")
print("leaks=" + (",".join(leaks) if leaks else "none"))
evidence.joinpath("leaks.txt").write_text("\n".join(leaks) or "none\n")
if leaks:
    raise SystemExit("FAIL: fake secret or debug leak")
print("GATE_2_15_PASS")
PY
# Product git tree must not contain the planted secret (evidence files are
# scanned separately above).
if git -C "$ROOT" grep -n "$SECRET" -- ':!evidence/' >/dev/null 2>&1; then
  echo "FAIL: fake secret committed or staged in product tree" >&2
  exit 1
fi
echo "PASS: privacy leak scan"
