#!/usr/bin/env bash
# PAG-2 hardening invariants. Safe / read-only except existing control-db migrate already applied.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

echo "=== operator boundary is not a fake PASS ==="
out="$("$ROOT/scripts/verify-operator-boundary.sh")"
echo "$out" | rg -q '^status=READY_FOR_HUMAN$'
echo "$out" | rg -q 'AUTH_AGENT_PASSWORDLESS_ROOT'
echo "$out" | rg -q 'AUTH_NO_HERMES_OP'
echo "$out" | rg -q 'AUTH_GATEWAY_RUNS_AS_AGENT'
echo "PASS: H1 not faked"

echo "=== live production still unpatched ==="
rg -q transform_kanban_worker_spawn /home/ubuntu/.hermes/hermes-agent/hermes_cli/kanban_db.py && {
  echo "FAIL: live Hermes already has spawn-transform" >&2
  exit 1
}
echo "PASS: live unpatched"

echo "=== live patch artifact hash ==="
actual="$(sha256sum "$ROOT/patches/hermes/live/0001-worker-spawn-transform-live.patch" | awk '{print $1}')"
test "$actual" = "51d4dd4d003143cdfea07d53668e8079f6d5163dc0a2777b3d5c3efd0001ecd4"
rg -q ThreadPoolExecutor "$ROOT/patches/hermes/live/0001-worker-spawn-transform-live.patch" && {
  echo "FAIL: live patch uses ThreadPoolExecutor" >&2
  exit 1
}
echo "PASS: live patch hash"

echo "=== fake secret leakage ==="
if rg -n "FAKE_PAG2_SECRET_ABC123" \
  "$ROOT/docs" "$ROOT/engineering_os" "$ROOT/dashboard" "$ROOT/patches" \
  "$ROOT/provenance" "$ROOT/experiments" "$ROOT/config" "$ROOT/PAG1_REPORT.md" \
  "$ROOT/PAG2_REPORT.md" \
  2>/dev/null; then
  echo "FAIL: fake secret leaked outside tests/scripts" >&2
  exit 1
fi
echo "PASS: fake-secret leakage"

echo "=== RetroPick / Android unchanged vs PAG-1 freeze ==="
test "$(git -C /opt/retropick rev-parse HEAD)" = "a8edf7dd3e7195aea6f1c826fcf2199ead525162"
test "$(git -C /opt/retropick-android rev-parse HEAD)" = "e962490dab3ac1072d9ee6371eb1077c0a05c0ac"
echo "PASS: product SHAs"

echo "PASS: verify-pag2-hardening"
