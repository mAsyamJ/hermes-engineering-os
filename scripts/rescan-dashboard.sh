#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"$ROOT/scripts/dashboard-request.py" \
  /api/dashboard/plugins/rescan \
  --expect-status 200 \
  --quiet
echo "PASS: dashboard plugin manifests rescanned"

