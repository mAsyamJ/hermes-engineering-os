#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
ENV="$ROOT/deploy/observability/.env"
# shellcheck disable=SC1090
set -a
source "$ENV"
set +a
KEY_FILE="$ROOT/.runtime/adaptation/keys/test-approval.key"
mkdir -p "$(dirname "$KEY_FILE")"
if [ ! -f "$KEY_FILE" ]; then
  python3 -c "import os; print(os.urandom(32).hex(), end='')" > "$KEY_FILE"
  chmod 600 "$KEY_FILE"
fi
COMPOSE=(sudo -n docker compose --env-file "$ENV" -f "$ROOT/deploy/observability/compose.yaml")
"${COMPOSE[@]}" run --rm --no-deps \
  -e EOS_EVAL_SANDBOX="${EOS_EVAL_SANDBOX:-inline}" \
  -e EOS_ADAPTATION_RUNTIME=/tmp/eos-adaptation \
  -e HERMES_CONTROL_TEST_APPROVAL_KEY="$(cat "$KEY_FILE")" \
  adaptation-engine --json "$@"
