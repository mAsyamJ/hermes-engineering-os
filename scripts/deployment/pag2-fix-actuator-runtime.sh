#!/usr/bin/env bash
# Apply TCB-safe adaptation runtime paths. hermes-op only.
# Does not consume exposure, does not mutate Kanban, does not weaken TCB.
set -euo pipefail
if [[ "$(id -u)" -ne 0 || "${SUDO_USER:-}" != "hermes-op" ]]; then
  echo "REFUSED: run via sudo from hermes-op" >&2
  exit 1
fi
# shellcheck source=../lib/repo-root.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/../lib/repo-root.sh"
ROOT="$(_eos_repo_root_from "${BASH_SOURCE[0]}")"

echo "=== install protected engineering_os (read-only TCB) ==="
rsync -a --delete "$ROOT/engineering_os/" /usr/local/lib/hermes-eos/engineering_os/
chown -R root:hermes-op /usr/local/lib/hermes-eos
chmod -R a+rX,go-w /usr/local/lib/hermes-eos
chmod 0755 /usr/local/lib/hermes-eos
test ! -e /usr/local/lib/hermes-eos/.runtime

echo "=== actuator-owned mutable adaptation dir ==="
install -d -m 0750 -o hermes-actuator -g hermes-runtime /var/lib/hermes-actuator/adaptation

echo "=== actuator.env + unit ==="
install -m 0644 "$ROOT/deploy/pag2/hermes-eos-actuator.service" /etc/systemd/system/hermes-eos-actuator.service
if ! rg -q '^EOS_ADAPTATION_RUNTIME=' /etc/hermes-eos/actuator.env; then
  printf '\nEOS_ADAPTATION_RUNTIME=/var/lib/hermes-actuator/adaptation\n' >> /etc/hermes-eos/actuator.env
fi
chown root:hermes-op /etc/hermes-eos/actuator.env
chmod 0444 /etc/hermes-eos/actuator.env
systemctl daemon-reload
systemctl try-restart hermes-eos-actuator.service
sleep 1
systemctl is-active hermes-eos-actuator.service

echo "=== ownership ==="
stat -c '%U %G %a %n' /var/lib/hermes-actuator /var/lib/hermes-actuator/adaptation /usr/local/lib/hermes-eos
test "$(stat -c '%U:%G' /var/lib/hermes-actuator/adaptation)" = "hermes-actuator:hermes-runtime"

echo "=== IPC probe (no exposure, no Kanban) ==="
runuser -u hermes-runtime -- env \
  PYTHONPATH=/usr/local/lib/hermes-eos:/usr/lib/hermes-runtime/hermes-agent \
  HERMES_EOS_ACTUATOR_SOCK=/run/hermes-eos/actuator.sock \
  HERMES_EOS_REPO=/opt/hermes-engineering-os \
  EOS_EXPERIMENT_RUNTIME=/opt/hermes-engineering-os/.runtime/experiments \
  /usr/lib/hermes-runtime/venv/bin/python -m engineering_os.adaptation pag2-probe
