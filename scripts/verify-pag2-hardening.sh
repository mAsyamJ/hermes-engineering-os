#!/usr/bin/env bash
# PAG-2 hardening invariants. Safe / read-only except existing control-db migrate already applied.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

echo "=== operator boundary (honest; PASS only after H1) ==="
out="$("$ROOT/scripts/verify-operator-boundary.sh")"
echo "$out"
if echo "$out" | rg -q '^status=PASS$'; then
  echo "$out" | rg -q 'AUTH_AGENT_PASSWORDLESS_ROOT' && {
    echo "FAIL: PASS claimed while ubuntu still has NOPASSWD ALL" >&2
    exit 1
  }
  echo "$out" | rg -q 'AUTH_GATEWAY_RUNS_AS_AGENT' && {
    echo "FAIL: PASS claimed while gateway still runs as agent" >&2
    exit 1
  }
  echo "PASS: H1 verifier PASS"
elif echo "$out" | rg -q '^status=READY_FOR_HUMAN$'; then
  echo "$out" | rg -q 'AUTH_AGENT_PASSWORDLESS_ROOT'
  if echo "$out" | rg -q 'hermes_op_present=no'; then
    echo "$out" | rg -q 'AUTH_NO_HERMES_OP'
  else
    echo "$out" | rg -q 'hermes_op_present=yes'
  fi
  echo "PASS: H1 not faked"
else
  echo "FAIL: unexpected verifier status" >&2
  exit 1
fi

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

echo "=== pag2-status dashboard is honest ==="
status_out="$("$ROOT/scripts/pag2-status.sh")"
echo "$status_out"
echo "$status_out" | rg -q '^auto_promote=false$'
echo "$status_out" | rg -q '^live_spawn_hook=ABSENT$'
if echo "$status_out" | rg -q '^h1=PASS$'; then
  echo "$status_out" | rg -q -e '^next=(HUMAN ACTION REQUIRED — (H2|EXPERIMENT|H3|APPROVAL A|CANARY|EVIDENCE \(.+\))|VALID_NO_PROMOTION — skip canary)$'
else
  echo "$status_out" | rg -q '^h1=READY_FOR_HUMAN$'
  echo "$status_out" | rg -q '^next=HUMAN ACTION REQUIRED — H1$'
fi
echo "PASS: pag2-status"

echo "=== RetroPick / Android unchanged vs PAG-1 freeze ==="
test "$(git -C /opt/retropick rev-parse HEAD)" = "a8edf7dd3e7195aea6f1c826fcf2199ead525162"
test "$(git -C /opt/retropick-android rev-parse HEAD)" = "e962490dab3ac1072d9ee6371eb1077c0a05c0ac"
echo "PASS: product SHAs"

echo "PASS: verify-pag2-hardening"
