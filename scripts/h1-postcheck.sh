#!/usr/bin/env bash
# Read-only H1 PASS checklist. Never changes users, sudoers, or units.
# Intended AFTER the human H1 sequence. Before H1 this script must fail.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
# shellcheck source=pag2-inspect-ubuntu.sh
source "$ROOT/scripts/pag2-inspect-ubuntu.sh"
fail=0
note() { echo "FAIL: $1"; fail=1; }
pass() { echo "PASS: $1"; }

out="$("$ROOT/scripts/verify-operator-boundary.sh" || true)"
echo "$out"
if echo "$out" | rg -q '^status=PASS$'; then
  pass "verifier status=PASS"
else
  note "verifier is not PASS"
fi
if echo "$out" | rg -q 'AUTH_AGENT_PASSWORDLESS_ROOT'; then
  note "ubuntu still has NOPASSWD ALL"
fi

getent passwd hermes-op >/dev/null && pass "hermes-op exists" || note "hermes-op missing"
getent passwd hermes-runtime >/dev/null && pass "hermes-runtime exists" || note "hermes-runtime missing"
getent passwd hermes-actuator >/dev/null && pass "hermes-actuator exists" || note "hermes-actuator missing"

user="$(systemctl show hermes-gateway.service -p User --value 2>/dev/null || true)"
if [[ "$user" == "hermes-runtime" ]]; then
  pass "system gateway User=hermes-runtime"
else
  note "system gateway User is not hermes-runtime ($user)"
fi

runtime_py="/usr/lib/hermes-runtime/hermes-agent/hermes_cli/kanban_db.py"
if [[ ! -f "$runtime_py" ]]; then
  note "protected runtime tree missing"
elif rg -q transform_kanban_worker_spawn "$runtime_py"; then
  note "protected runtime already has spawn-transform (H1 forbids this)"
else
  pass "protected runtime present and unpatched"
fi

if [[ ! -f /etc/hermes-eos/approval-trust.pub ]]; then
  note "trust pub missing"
elif pag2_ubuntu_writable /etc/hermes-eos/approval-trust.pub; then
  note "trust pub writable by ubuntu"
else
  pass "trust pub present and not ubuntu-writable"
fi

if [[ ! -f /usr/local/lib/hermes-eos/hermes-eos-deploy-tool.py ]]; then
  note "protected deploy-tool missing"
else
  pass "protected deploy-tool present"
fi

if [[ ! -f /usr/local/lib/hermes-eos/scripts/verify-operator-boundary.sh || ! -f /usr/local/lib/hermes-eos/scripts/pag2-inspect-ubuntu.sh ]]; then
  note "protected verifier script missing"
else
  pass "protected verifier script present"
fi

if [[ ! -f /usr/local/lib/hermes-eos/deploy/pag2/eos-actuation-plugin/__init__.py || ! -f /usr/local/lib/hermes-eos/deploy/pag2/eos-actuation-plugin/plugin.yaml ]]; then
  note "protected eos-actuation plugin source missing"
else
  pass "protected eos-actuation plugin source present"
fi

actuator_py="/usr/local/lib/hermes-eos/engineering_os/adaptation/actuator.py"
if [[ ! -f "$actuator_py" ]]; then
  note "protected actuator missing"
elif ! rg -q SO_PEERCRED "$actuator_py"; then
  note "protected actuator missing SO_PEERCRED"
else
  pass "protected actuator has SO_PEERCRED"
fi

if [[ ! -f /etc/hermes-eos/actuator.env ]]; then
  note "actuator.env missing"
elif pag2_ubuntu_writable /etc/hermes-eos/actuator.env; then
  note "actuator.env writable by ubuntu"
else
  pass "actuator.env present and not ubuntu-writable"
fi

user_enabled="$(pag2_ubuntu_unit_enabled hermes-gateway.service)"
if [[ "$user_enabled" == "masked" ]]; then
  pass "ubuntu user gateway masked"
else
  note "ubuntu user gateway not masked ($user_enabled)"
fi

if pgrep -u ubuntu -f 'hermes_cli.main gateway run' >/dev/null 2>&1; then
  note "ubuntu still runs a gateway process"
else
  pass "no ubuntu gateway process"
fi

# After H1, /run/hermes-eos and /var/lib/hermes-actuator are 0750.
# ubuntu cannot stat them; FileNotFoundError ≠ PermissionError.
if pag2_as_ubuntu python3 - <<'PY'
import socket, sys
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.settimeout(0.5)
try:
    sock.connect("/run/hermes-eos/actuator.sock")
except FileNotFoundError:
    print("FAIL: actuator socket missing")
    sys.exit(2)
except OSError as exc:
    print(f"PASS: ubuntu connect refused ({type(exc).__name__})")
    sys.exit(0)
else:
    sock.close()
    print("FAIL: ubuntu connected to actuator socket")
    sys.exit(1)
PY
then
  pass "ubuntu cannot connect to actuator socket"
else
  rc=$?
  if [[ "$rc" -eq 2 ]]; then
    note "actuator socket missing"
  else
    note "ubuntu was able to connect to actuator socket"
  fi
fi

if [[ -f /var/lib/hermes-actuator/state.json ]]; then
  if pag2_ubuntu_writable /var/lib/hermes-actuator/state.json; then
    note "actuator state.json writable by ubuntu"
  else
    pass "actuator state.json present and not ubuntu-writable"
  fi
elif [[ "$(systemctl is-active hermes-eos-actuator.service 2>/dev/null || true)" == "active" ]] \
  && ! pag2_ubuntu_writable /var/lib/hermes-actuator \
  && ! pag2_ubuntu_writable /var/lib/hermes-actuator/state.json; then
  pass "actuator state.json not ubuntu-visible (0750) and actuator active"
else
  note "actuator state.json missing"
fi

if [[ -e /usr/local/lib/hermes-eos/.runtime ]]; then
  note "protected TCB contains .runtime (must stay read-only code)"
else
  pass "protected TCB has no .runtime write target"
fi

if [[ ! -x /usr/lib/hermes-runtime/cpython/bin/python3.11 ]]; then
  note "protected cpython missing"
else
  pass "protected cpython present"
fi

plugin_link="$(readlink -f /var/lib/hermes-runtime/home/profiles/rp-friend/plugins 2>/dev/null || true)"
if echo "$plugin_link" | rg -q '^/home/ubuntu|^/opt/hermes-engineering-os'; then
  note "rp-friend plugins still point at agent-writable path ($plugin_link)"
elif [[ -n "$plugin_link" ]]; then
  pass "rp-friend plugins not agent-writable"
elif [[ "$(systemctl show hermes-gateway-rp-friend.service -p User --value 2>/dev/null || true)" == "hermes-runtime" ]] \
  && [[ "$(systemctl is-active hermes-gateway-rp-friend.service 2>/dev/null || true)" == "active" ]] \
  && ! pag2_ubuntu_writable /var/lib/hermes-runtime/home; then
  pass "rp-friend plugins not ubuntu-visible (700 home); gateway is hermes-runtime"
else
  note "rp-friend plugins path missing"
fi

if [[ "$fail" -ne 0 ]]; then
  echo "H1 POSTCHECK: NOT PASS"
  exit 1
fi
echo "H1 POSTCHECK: PASS"
exit 0
