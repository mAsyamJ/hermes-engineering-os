#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=../lib/repo-root.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/../lib/repo-root.sh"
ROOT="$(_eos_repo_root_from "${BASH_SOURCE[0]}")"
COMPOSE="$ROOT/deploy/observability/compose.yaml"
ENV="$ROOT/deploy/observability/.env"
cd "$ROOT/deploy/observability"
sudo -n docker compose --env-file "$ENV" -f "$COMPOSE" stop
echo "PASS: observability stack stopped (volumes retained)"
