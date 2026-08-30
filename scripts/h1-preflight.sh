#!/usr/bin/env bash
# Read-only H1 preflight. Never creates users, never cuts over.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
fail=0
note() { echo "MISSING: $1"; fail=1; }
ok() { echo "OK: $1"; }

live=/home/ubuntu/.hermes/hermes-agent
sha="$(git -C "$live" rev-parse HEAD 2>/dev/null || echo missing)"
if [[ "$sha" == c0106e50e7ecedb3ce34e785d949725dc4e0e457 ]]; then
  ok "live SHA c0106e50"
else
  note "live SHA is $sha"
fi
if rg -q transform_kanban_worker_spawn "$live/hermes_cli/kanban_db.py" 2>/dev/null; then
  note "live tree already patched"
else
  ok "live spawn-transform absent"
fi
if [[ -x /home/ubuntu/.hermes/hermes-agent/venv/bin/python ]]; then
  live_py="$(readlink -f /home/ubuntu/.hermes/hermes-agent/venv/bin/python)"
  if [[ -x "$live_py" ]]; then
    ok "live venv python $live_py"
  else
    note "live venv python does not resolve"
  fi
else
  note "live venv python"
fi
getent passwd hermes-op >/dev/null && ok "hermes-op exists" || note "hermes-op (step A)"
getent passwd hermes-runtime >/dev/null && ok "hermes-runtime exists" || note "hermes-runtime (cutover)"
getent passwd hermes-actuator >/dev/null && ok "hermes-actuator exists" || note "hermes-actuator (cutover)"
if [[ -f /etc/hermes-eos/approval-trust.pub ]]; then
  ok "public trust installed"
else
  note "public trust /etc/hermes-eos/approval-trust.pub (step C, off-VPS key)"
fi
if pgrep -u ubuntu -f 'hermes_cli.main gateway run' >/dev/null; then
  echo "NOTE: ubuntu gateways still running (expected before cutover)"
fi
echo "HUMAN ACTION REQUIRED — H1"
echo "Do not claim PASS. Cutover: sudo -u from hermes-op only: scripts/h1-cutover.sh"
if [[ "$fail" -ne 0 ]]; then
  echo "H1 PREFLIGHT: NOT READY"
  exit 1
fi
echo "H1 PREFLIGHT: principals+trust present; run cutover as hermes-op"
exit 0
