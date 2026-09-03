#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=../lib/repo-root.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/../lib/repo-root.sh"
ROOT="$(_eos_repo_root_from "${BASH_SOURCE[0]}")"
COMPOSE="$ROOT/deploy/observability/compose.yaml"
ENV="$ROOT/deploy/observability/.env"
test -f "$ENV"
chmod +x "$ROOT/deploy/observability/init-db.sh"
cd "$ROOT/deploy/observability"
TARGET="${1:-all}"
if [[ "$TARGET" == "postgres" ]]; then
  sudo -n docker compose --env-file "$ENV" -f "$COMPOSE" up -d postgres
else
  sudo -n docker compose --env-file "$ENV" -f "$COMPOSE" up -d
fi
echo "PASS: observability start ($TARGET)"
