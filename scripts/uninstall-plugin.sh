#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
LINK="/home/ubuntu/.hermes/plugins/engineering-os"
HERMES="/home/ubuntu/.local/bin/hermes"

if [[ ! -e "$LINK" && ! -L "$LINK" ]]; then
  echo "PASS: engineering-os plugin link already absent"
  exit 0
fi
test -L "$LINK"
test "$(readlink -f "$LINK")" = "$ROOT"

"$HERMES" plugins disable engineering-os
"$ROOT/scripts/dashboard-request.py" \
  /api/plugins/engineering-os/health \
  --expect-status 404 \
  --quiet
"$ROOT/scripts/rescan-dashboard.sh"
unlink "$LINK"
"$ROOT/scripts/rescan-dashboard.sh"

inventory="$("$ROOT/scripts/dashboard-request.py" /api/dashboard/plugins)"
if printf '%s' "$inventory" | rg -q '"engineering-os"'; then
  echo "engineering-os remains in dashboard inventory" >&2
  exit 1
fi

echo "PASS: engineering-os disabled and exact symlink removed"

