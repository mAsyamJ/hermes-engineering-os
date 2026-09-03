#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=../lib/repo-root.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/../lib/repo-root.sh"
ROOT="$(_eos_repo_root_from "${BASH_SOURCE[0]}")"
"$ROOT/scripts/maintenance/dashboard-request.py" \
  /api/dashboard/plugins/rescan \
  --expect-status 200 \
  --quiet
echo "PASS: dashboard plugin manifests rescanned"
