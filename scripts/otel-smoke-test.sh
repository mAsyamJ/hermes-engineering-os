#!/usr/bin/env bash
# Disposable Hermes CLI smoke: one LLM + one tool + one file read in the fixture
# repo. Does not use RetroPick. Does not restart gateways.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HERMES="${HERMES:-/home/ubuntu/.local/bin/hermes}"
EVIDENCE="$ROOT/evidence/phase2/real-hermes-smoke"
mkdir -p "$EVIDENCE"
"$ROOT/scripts/create-fixture-repo.sh"
FIXTURE="$ROOT/.runtime/fixture-repo"
TASK_ID="${HERMES_KANBAN_TASK:-t_phase2obs}"
RUN_ID="${HERMES_KANBAN_RUN_ID:-9001}"
BOARD="${HERMES_KANBAN_BOARD:-eos-phase2-obs}"
PROMPT="${1:-Read README.md in this workspace, then run the terminal command wc -l README.md. Reply with the line count only. Do not modify files.}"
export HERMES_KANBAN_TASK="$TASK_ID"
export HERMES_KANBAN_RUN_ID="$RUN_ID"
export HERMES_KANBAN_BOARD="$BOARD"
export HERMES_KANBAN_WORKSPACE="$FIXTURE"
export OTEL_PHOENIX_ENDPOINT="${OTEL_PHOENIX_ENDPOINT:-http://127.0.0.1:6006/v1/traces}"
export OTEL_PROJECT_NAME="${OTEL_PROJECT_NAME:-hermes-agent}"
export HERMES_OTEL_CONFIG="${HERMES_OTEL_CONFIG:-$HOME/.hermes/hermes_otel.yaml}"
unset HERMES_OTEL_DEBUG || true
{
  echo "task_id=$TASK_ID"
  echo "run_id=$RUN_ID"
  echo "board=$BOARD"
  echo "workspace=$FIXTURE"
  echo "endpoint=$OTEL_PHOENIX_ENDPOINT"
} | tee "$EVIDENCE/env.txt"
set +e
"$HERMES" chat -q "$PROMPT" --in "$FIXTURE" -Q --yolo --max-turns 8 --ignore-rules \
  >"$EVIDENCE/hermes.out" 2>"$EVIDENCE/hermes.err"
STATUS=$?
set -e
echo "hermes_exit=$STATUS" | tee "$EVIDENCE/exit.txt"
if [[ "$STATUS" -ne 0 ]]; then
  echo "FAIL: disposable Hermes smoke exited $STATUS" >&2
  tail -n 80 "$EVIDENCE/hermes.err" >&2 || true
  exit "$STATUS"
fi
echo "PASS: disposable Hermes CLI completed (DISPOSABLE_RUNTIME_OTEL)"
