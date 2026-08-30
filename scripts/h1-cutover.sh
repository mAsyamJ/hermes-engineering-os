#!/usr/bin/env bash
# Mechanical H1 cutover. Human-only via hermes-op.
# Does not create hermes-op, does not install SSH keys, does not apply the
# live spawn-transform, does not reduce ubuntu sudo, does not print secrets.
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "REFUSED: run as root via sudo from hermes-op" >&2
  exit 1
fi
if [[ "${SUDO_USER:-}" != "hermes-op" ]]; then
  echo "REFUSED: H1 cutover runs only as hermes-op (SUDO_USER=${SUDO_USER:-empty})" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
LIVE=/home/ubuntu/.hermes/hermes-agent
DEST=/usr/lib/hermes-runtime/hermes-agent
LIVE_SHA=c0106e50e7ecedb3ce34e785d949725dc4e0e457

echo "=== H1 cutover (hermes-op mechanical) ==="

git_at() {
  local repo="$1"; shift
  git -c safe.directory="$repo" -C "$repo" "$@"
}

test "$(git_at "$LIVE" rev-parse HEAD)" = "$LIVE_SHA"
if rg -q transform_kanban_worker_spawn "$LIVE/hermes_cli/kanban_db.py"; then
  echo "FAIL: live tree already has spawn-transform" >&2
  exit 1
fi
if [[ ! -f /etc/hermes-eos/approval-trust.pub ]]; then
  echo "HUMAN ACTION REQUIRED — install public trust only at /etc/hermes-eos/approval-trust.pub" >&2
  exit 1
fi
LIVE_PY="$(readlink -f "$LIVE/venv/bin/python")"
if [[ ! -x "$LIVE_PY" ]]; then
  echo "FAIL: live venv python missing" >&2
  exit 1
fi
CPYTHON_SRC="$(cd "$(dirname "$LIVE_PY")/.." && pwd -P)"
if [[ ! -x "$CPYTHON_SRC/bin/python3.11" ]]; then
  echo "FAIL: live uv cpython missing at $CPYTHON_SRC (from $LIVE_PY)" >&2
  exit 1
fi
TRUST_FP="$(python3 - <<'PY'
from pathlib import Path
import hashlib
raw = Path("/etc/hermes-eos/approval-trust.pub").read_bytes().strip()
pub = raw if len(raw) == 32 else bytes.fromhex(raw.decode().strip())
print(hashlib.sha256(pub).hexdigest()[:16])
PY
)"

getent passwd hermes-runtime >/dev/null || \
  useradd --system --home-dir /var/lib/hermes-runtime --shell /usr/sbin/nologin hermes-runtime
getent passwd hermes-actuator >/dev/null || \
  useradd --system --home-dir /var/lib/hermes-actuator --shell /usr/sbin/nologin hermes-actuator

install -d -m 0750 -o hermes-runtime -g hermes-runtime /var/lib/hermes-runtime
install -d -m 0750 -o hermes-actuator -g hermes-actuator /var/lib/hermes-actuator
install -d -m 0750 -o hermes-actuator -g hermes-runtime /var/lib/hermes-actuator/adaptation
install -d -m 0750 -o root -g hermes-op /var/lib/hermes-actuator/deploy-nonces
if [[ ! -f /var/lib/hermes-actuator/state.json ]]; then
  cat > /var/lib/hermes-actuator/state.json <<JSON
{"maximum_exposure":1,"auto_promote":false,"bindings":[],"runtime_identity":{"runtime_release_hash":"${LIVE_SHA}","live_patch_hash":"","actuator_contract_version":"pag2-actuator-v1","trust_fingerprint":"${TRUST_FP}"}}
JSON
  chown hermes-actuator:hermes-actuator /var/lib/hermes-actuator/state.json
  chmod 0640 /var/lib/hermes-actuator/state.json
fi
install -d -m 0750 -o hermes-actuator -g hermes-runtime /run/hermes-eos
install -d -m 0755 -o root -g hermes-op /etc/hermes-eos
install -d -m 0755 -o root -g hermes-op /usr/local/lib/hermes-eos
install -d -m 0755 -o root -g hermes-runtime /usr/lib/hermes-runtime
install -d -m 0750 -o root -g hermes-op /var/backups/hermes-engineering-os

echo "=== protected verifier / actuator / deploy-tool ==="
rsync -a --delete "$ROOT/engineering_os/" /usr/local/lib/hermes-eos/engineering_os/
install -m 0755 -o root -g hermes-op "$ROOT/scripts/hermes-eos-deploy-tool.py" \
  /usr/local/lib/hermes-eos/hermes-eos-deploy-tool.py
install -d -m 0755 -o root -g hermes-op /usr/local/lib/hermes-eos/scripts
install -m 0755 -o root -g hermes-op "$ROOT/scripts/verify-operator-boundary.sh" \
  /usr/local/lib/hermes-eos/scripts/verify-operator-boundary.sh
install -m 0644 -o root -g hermes-op "$ROOT/scripts/pag2-inspect-ubuntu.sh" \
  /usr/local/lib/hermes-eos/scripts/pag2-inspect-ubuntu.sh
install -d -m 0755 -o root -g hermes-op /usr/local/lib/hermes-eos/deploy/pag2/eos-actuation-plugin
install -m 0644 -o root -g hermes-op \
  "$ROOT/deploy/pag2/eos-actuation-plugin/__init__.py" \
  /usr/local/lib/hermes-eos/deploy/pag2/eos-actuation-plugin/__init__.py
install -m 0644 -o root -g hermes-op \
  "$ROOT/deploy/pag2/eos-actuation-plugin/plugin.yaml" \
  /usr/local/lib/hermes-eos/deploy/pag2/eos-actuation-plugin/plugin.yaml
cat > /etc/hermes-eos/actuator.env <<EOF
# Protected actuator environment. No secrets.
HERMES_EOS_ACTUATOR_SOCK=/run/hermes-eos/actuator.sock
HERMES_EOS_RESERVE_SQLITE=/var/lib/hermes-actuator/reservations.sqlite
HERMES_EOS_ACTUATOR_STATE=/var/lib/hermes-actuator/state.json
EOS_ADAPTATION_RUNTIME=/var/lib/hermes-actuator/adaptation
HERMES_EOS_RUNTIME_RELEASE_HASH=${LIVE_SHA}
HERMES_EOS_LIVE_PATCH_HASH=
HERMES_EOS_TRUST_FINGERPRINT=${TRUST_FP}
EOF
chown root:hermes-op /etc/hermes-eos/actuator.env
chmod 0444 /etc/hermes-eos/actuator.env
ln -sfn /usr/local/lib/hermes-eos/engineering_os/adaptation/approval_ed25519.py \
  /usr/local/lib/hermes-eos/approval-verifier
ln -sfn /usr/local/lib/hermes-eos/engineering_os/adaptation/actuator.py \
  /usr/local/lib/hermes-eos/actuator.py
chown -R root:hermes-op /usr/local/lib/hermes-eos
chmod -R a+rX,go-w /usr/local/lib/hermes-eos
chmod 0755 /usr/local/lib/hermes-eos
rg -q SO_PEERCRED /usr/local/lib/hermes-eos/engineering_os/adaptation/actuator.py

echo "=== same-SHA runtime + protected cpython (no spawn-transform) ==="
rsync -a --delete --exclude venv "$LIVE/" "$DEST/"
rsync -a "$CPYTHON_SRC/" /usr/lib/hermes-runtime/cpython/
if [[ -d /home/ubuntu/.hermes/node ]]; then
  rsync -a /home/ubuntu/.hermes/node/ /usr/lib/hermes-runtime/node/
fi
rsync -a "$LIVE/venv/" /usr/lib/hermes-runtime/venv/
ln -sfn /usr/lib/hermes-runtime/cpython/bin/python3.11 /usr/lib/hermes-runtime/venv/bin/python
ln -sfn python /usr/lib/hermes-runtime/venv/bin/python3
ln -sfn python /usr/lib/hermes-runtime/venv/bin/python3.11
cat > /usr/lib/hermes-runtime/venv/pyvenv.cfg <<'CFG'
home = /usr/lib/hermes-runtime/cpython/bin
implementation = CPython
version_info = 3.11
include-system-site-packages = false
CFG
# Drop ubuntu-path editable finders so production cannot import agent-writable source.
shopt -s nullglob
rm -f /usr/lib/hermes-runtime/venv/lib/python3.11/site-packages/__editable__.*
rm -f /usr/lib/hermes-runtime/venv/lib/python3.11/site-packages/__editable___*
test "$(git_at "$DEST" rev-parse HEAD)" = "$LIVE_SHA"
if rg -q transform_kanban_worker_spawn "$DEST/hermes_cli/kanban_db.py"; then
  echo "FAIL: protected copy has spawn-transform" >&2
  exit 1
fi
chown -R root:hermes-runtime /usr/lib/hermes-runtime
chmod -R a+rX,go-w /usr/lib/hermes-runtime
chmod 0755 /usr/lib/hermes-runtime /usr/lib/hermes-runtime/cpython /usr/lib/hermes-runtime/venv

echo "=== smoke protected interpreter (ubuntu gateways still running) ==="
runuser -u hermes-runtime -- env \
  PYTHONPATH=/usr/local/lib/hermes-eos:/usr/lib/hermes-runtime/hermes-agent \
  /usr/lib/hermes-runtime/venv/bin/python -c \
  'import hermes_cli, engineering_os.adaptation.actuator; print("SMOKE_OK")'

echo "=== install system units (not starting gateways yet) ==="
install -m 0644 "$ROOT/deploy/pag2/hermes-eos-actuator.socket" /etc/systemd/system/
install -m 0644 "$ROOT/deploy/pag2/hermes-eos-actuator.service" /etc/systemd/system/
install -m 0644 "$ROOT/deploy/pag2/hermes-gateway.service" /etc/systemd/system/
install -m 0644 "$ROOT/deploy/pag2/hermes-gateway-rp-friend.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now hermes-eos-actuator.socket hermes-eos-actuator.service

# Rebuildable tool caches (Playwright, go-build, uv, pnpm). --exclude cache
# does not match `.cache`. A full duplicate does not fit this disk; production
# node is already at /usr/lib/hermes-runtime/node. Do not exclude profile
# homes, kanban, sessions, memories, or runtime node_modules.
CRED_RSYNC_EXCLUDES=(
  --exclude /hermes-agent
  --exclude /plugins/engineering-os
  --exclude /cache
  --exclude .cache
)
SRC_HOME=/home/ubuntu/.hermes
DEST_HOME=/var/lib/hermes-runtime/home

echo "=== disk preflight (before stopping ubuntu gateways) ==="
need="$(du -sb --exclude=hermes-agent --exclude=cache --exclude=.cache "$SRC_HOME" | awk '{print $1}')"
avail="$(df -B1 --output=avail /var/lib/hermes-runtime | tail -n1 | tr -d ' ')"
reclaim=0
if [[ -d "$DEST_HOME" ]]; then
  reclaim="$(du -sb "$DEST_HOME" | awk '{print $1}')"
fi
effective=$((avail + reclaim))
buffer=$((2 * 1024 * 1024 * 1024))
echo "credential_rsync_need=${need} avail=${avail} dest_reclaim=${reclaim} buffer=${buffer}"
if (( effective < need + buffer )); then
  echo "FAIL: not enough disk for credential rsync (need ${need} + ${buffer}, effective ${effective})" >&2
  echo "ubuntu gateways left running" >&2
  exit 1
fi

echo "=== drain and STOP ubuntu user gateways (quiesce DBs before rsync) ==="
# Do not reload-then-stop: USR1 restart queues a job that cancels stop.
# replace-irreversibly wins against Restart=always start jobs.
for unit in hermes-gateway.service hermes-gateway-rp-friend.service; do
  systemctl --user -M ubuntu@ reset-failed "$unit" || true
  systemctl --user -M ubuntu@ stop --job-mode=replace-irreversibly "$unit" || true
done
for _ in $(seq 1 90); do
  if systemctl --user -M ubuntu@ is-active hermes-gateway.service hermes-gateway-rp-friend.service \
      | rg -q '^active$'; then
    sleep 1
    continue
  fi
  break
done
if systemctl --user -M ubuntu@ is-active hermes-gateway.service hermes-gateway-rp-friend.service \
    | rg -q '^active$'; then
  echo "FAIL: ubuntu user gateways still active after stop" >&2
  systemctl --user -M ubuntu@ start hermes-gateway.service hermes-gateway-rp-friend.service || true
  exit 1
fi

echo "=== credential home (no secret printing) ==="
rsync -a --delete \
  "${CRED_RSYNC_EXCLUDES[@]}" \
  "$SRC_HOME/" "$DEST_HOME/"
rm -f /var/lib/hermes-runtime/home/plugins/engineering-os
# rp-friend live plugins dir is an absolute symlink into ubuntu home. Point it
# at the protected copy so production cannot load /opt or /home/ubuntu plugins.
if [[ -L /var/lib/hermes-runtime/home/profiles/rp-friend/plugins ]]; then
  rm -f /var/lib/hermes-runtime/home/profiles/rp-friend/plugins
fi
install -d -m 0750 -o hermes-runtime -g hermes-runtime /var/lib/hermes-runtime/home/plugins
ln -sfn /var/lib/hermes-runtime/home/plugins \
  /var/lib/hermes-runtime/home/profiles/rp-friend/plugins
python3 - <<'PY'
from pathlib import Path
root = Path("/var/lib/hermes-runtime/home")
for path in [root / "config.yaml", root / "profiles" / "rp-friend" / "config.yaml"]:
    if not path.is_file():
        continue
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("    - engineering-os\n", ""), encoding="utf-8")
PY
agent_plugin_links="$(find /var/lib/hermes-runtime/home -type l \( -lname '/home/ubuntu/*' -o -lname '/opt/*' \) \
  \( -path '*/plugins' -o -path '*/plugins/*' \) 2>/dev/null || true)"
if [[ -n "$agent_plugin_links" ]]; then
  echo "FAIL: production plugins still symlink into agent-writable paths:" >&2
  echo "$agent_plugin_links" >&2
  exit 1
fi
chown -R hermes-runtime:hermes-runtime /var/lib/hermes-runtime
chmod 0750 /var/lib/hermes-runtime /var/lib/hermes-runtime/home
for cred in .env auth.json; do
  f="/var/lib/hermes-runtime/home/$cred"
  if [[ -f "$f" ]]; then
    chmod 0600 "$f"
    stat -c '%U %a %n' "$f"
  fi
done

echo "=== start hermes-runtime system gateways ==="
systemctl enable --now hermes-gateway.service hermes-gateway-rp-friend.service
sleep 2

echo "=== move ubuntu unit files, then mask (mask is a /dev/null symlink) ==="
backup="/var/backups/hermes-engineering-os/h1-user-units"
install -d -m 0750 -o root -g hermes-op "$backup"
for unit in hermes-gateway.service hermes-gateway-rp-friend.service; do
  src="/home/ubuntu/.config/systemd/user/$unit"
  if [[ -e "$src" && ! -L "$src" ]]; then
    mv -f "$src" "$backup/$unit"
  fi
done
systemctl --user -M ubuntu@ daemon-reload || true
systemctl --user -M ubuntu@ mask hermes-gateway.service hermes-gateway-rp-friend.service
systemctl --user -M ubuntu@ daemon-reload || true

echo "=== postcheck (PASS still requires reducing ubuntu sudo) ==="
"$ROOT/scripts/h1-postcheck.sh" || true
"$ROOT/scripts/verify-operator-boundary.sh" || true
echo "CUTOVER_DONE remaining=reduce ubuntu sudo via deploy/pag2/sudoers-ubuntu then re-run verifier"
echo "Do not claim PASS until scripts/verify-operator-boundary.sh prints status=PASS"
