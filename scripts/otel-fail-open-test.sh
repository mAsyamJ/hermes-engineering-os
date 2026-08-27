#!/usr/bin/env bash
# Fail-open chaos: Phoenix down, observability Postgres down, invalid OTLP.
# Hermes must complete. Engineering OS observability must be DEGRADED, not a
# Hermes-wide failure. Restores the stack before exit.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HERMES="${HERMES:-/home/ubuntu/.local/bin/hermes}"
EVIDENCE="$ROOT/evidence/phase2/fail-open"
COMPOSE="$ROOT/deploy/observability/compose.yaml"
ENV_FILE="$ROOT/deploy/observability/.env"
mkdir -p "$EVIDENCE"
"$ROOT/scripts/create-fixture-repo.sh"
FIXTURE="$ROOT/.runtime/fixture-repo"
PROMPT="Reply with the single word pong. Do not use tools."

restore() {
  sudo -n docker compose --env-file "$ENV_FILE" -f "$COMPOSE" up -d >/dev/null 2>&1 || true
  for _ in $(seq 1 40); do
    if curl -fsS -o /dev/null http://127.0.0.1:6006/; then
      return 0
    fi
    sleep 2
  done
  echo "WARN: Phoenix UI not back yet" >&2
}
trap restore EXIT

run_cli() {
  local label="$1"
  local endpoint="$2"
  local out="$EVIDENCE/${label}.out"
  local err="$EVIDENCE/${label}.err"
  set +e
  HERMES_KANBAN_TASK="t_failopen" \
  HERMES_KANBAN_RUN_ID="9002" \
  HERMES_KANBAN_BOARD="eos-phase2-obs" \
  HERMES_KANBAN_WORKSPACE="$FIXTURE" \
  OTEL_PHOENIX_ENDPOINT="$endpoint" \
  OTEL_PROJECT_NAME="hermes-agent" \
  HERMES_OTEL_CONFIG="${HERMES_OTEL_CONFIG:-$HOME/.hermes/hermes_otel.yaml}" \
  env -u HERMES_OTEL_DEBUG \
    "$HERMES" chat -q "$PROMPT" --in "$FIXTURE" -Q --yolo --max-turns 3 --ignore-rules \
    >"$out" 2>"$err"
  local status=$?
  set -e
  echo "${label}_exit=$status" | tee -a "$EVIDENCE/results.txt"
  if [[ "$status" -ne 0 ]]; then
    echo "FAIL: Hermes did not fail-open during $label" >&2
    tail -n 40 "$err" >&2 || true
    exit "$status"
  fi
}

echo "=== 2.12 stop Phoenix ===" | tee "$EVIDENCE/results.txt"
sudo -n docker compose --env-file "$ENV_FILE" -f "$COMPOSE" stop phoenix
run_cli phoenix_down "http://127.0.0.1:6006/v1/traces"
"$ROOT/scripts/dashboard-request.py" /api/plugins/engineering-os/observability --quiet \
  || true
python3 - "$ROOT" <<'PY' | tee -a "$EVIDENCE/results.txt"
import sys
sys.path.insert(0, sys.argv[1])
from engineering_os.observability import health
snap = health.snapshot()
print("phoenix_down_eos_status=" + snap["status"])
print("phoenix_down_phoenix=" + str(snap["phoenix"]))
assert snap["status"] == "DEGRADED"
assert snap["fail_open"] is True
PY

echo "=== restore Phoenix, stop Postgres ===" | tee -a "$EVIDENCE/results.txt"
sudo -n docker compose --env-file "$ENV_FILE" -f "$COMPOSE" start phoenix
sleep 5
sudo -n docker compose --env-file "$ENV_FILE" -f "$COMPOSE" stop postgres
run_cli postgres_down "http://127.0.0.1:6006/v1/traces"
python3 - "$ROOT" <<'PY' | tee -a "$EVIDENCE/results.txt"
import sys
sys.path.insert(0, sys.argv[1])
from engineering_os.observability import health
snap = health.snapshot()
print("postgres_down_eos_status=" + snap["status"])
print("postgres_down_postgresql=" + str(snap["postgresql"]))
assert snap["status"] == "DEGRADED"
assert snap["postgresql"] == "DOWN"
assert snap["fail_open"] is True
PY

echo "=== 2.14 invalid OTLP ===" | tee -a "$EVIDENCE/results.txt"
restore
run_cli invalid_otlp "http://127.0.0.1:1/v1/traces"

restore
python3 - "$ROOT" <<'PY' | tee -a "$EVIDENCE/results.txt"
import sys
sys.path.insert(0, sys.argv[1])
from engineering_os.observability import health
snap = health.snapshot()
print("restored_phoenix=" + str(snap["phoenix"]))
print("restored_postgresql=" + str(snap["postgresql"]))
assert snap["fail_open"] is True
print("GATE_2_12_2_14_PASS")
PY
echo "PASS: fail-open chaos"
