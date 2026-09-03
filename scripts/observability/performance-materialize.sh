#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=../lib/repo-root.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/../lib/repo-root.sh"
ROOT="$(_eos_repo_root_from "${BASH_SOURCE[0]}")"
ENV="$ROOT/deploy/observability/.env"
# shellcheck disable=SC1090
set -a
source "$ENV"
set +a
COMPOSE=(sudo -n docker compose --env-file "$ENV" -f "$ROOT/deploy/observability/compose.yaml")
"${COMPOSE[@]}" run --rm --no-deps performance-materialize "$@"
