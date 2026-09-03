#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=../lib/repo-root.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/../lib/repo-root.sh"
ROOT="$(_eos_repo_root_from "${BASH_SOURCE[0]}")"
LINK="/home/ubuntu/.hermes/plugins/engineering-os"
HERMES="/home/ubuntu/.local/bin/hermes"

if [[ ! -e "$LINK" && ! -L "$LINK" ]]; then
  echo "PASS: engineering-os plugin link already absent"
  exit 0
fi
test -L "$LINK"
test "$(readlink -f "$LINK")" = "$ROOT"

"$HERMES" plugins disable engineering-os
"$ROOT/scripts/maintenance/dashboard-request.py" \
  /api/plugins/engineering-os/health \
  --expect-status 404 \
  --quiet
"$ROOT/scripts/maintenance/rescan-dashboard.sh"
unlink "$LINK"
"$ROOT/scripts/maintenance/rescan-dashboard.sh"

inventory="$("$ROOT/scripts/maintenance/dashboard-request.py" /api/dashboard/plugins)"
if printf '%s' "$inventory" | rg -q '"engineering-os"'; then
  echo "engineering-os remains in dashboard inventory" >&2
  exit 1
fi

echo "PASS: engineering-os disabled and exact symlink removed"

