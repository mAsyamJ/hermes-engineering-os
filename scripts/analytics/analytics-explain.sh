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
TASK="${1:?usage: analytics-explain.sh <task_id> [board]}"
BOARD="${2:-retropick-markets-release}"
sudo -n docker compose --env-file "$ENV" -f "$ROOT/deploy/observability/compose.yaml" \
  run --rm --no-deps \
  -e ANALYTICS_DATABASE_URL="postgresql://hermes_engineering_reader:${HERMES_ENGINEERING_READER_PASSWORD}@postgres:5432/hermes_engineering" \
  --entrypoint python analytics-materialize -m engineering_os.analytics.explain "$TASK" --board "$BOARD"
