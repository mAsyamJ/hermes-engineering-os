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
for path in "$ROOT"/migrations/control/*.sql; do
  version="$(basename "$path" .sql)"
  applied="$(sudo -n docker exec hermes-eos-postgres \
    psql -U hermes_control_owner -d hermes_control -tAc \
    "SELECT COUNT(*) FROM schema_migrations WHERE version='${version}';")"
  if [ "$applied" = "1" ]; then
    echo "skip $version"
    continue
  fi
  echo "apply $version"
  sudo -n docker exec -i hermes-eos-postgres \
    psql -v ON_ERROR_STOP=1 -U hermes_control_owner -d hermes_control < "$path"
done
echo "PASS: control-db-migrate"
