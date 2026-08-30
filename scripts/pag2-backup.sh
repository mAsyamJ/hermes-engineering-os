#!/usr/bin/env bash
# Capture a secret-free PAG-2 backup. Does not print .env/auth.json.
# hermes-op sudo writes /var/backups/hermes-engineering-os/. ubuntu writes
# only .runtime/pag2-backup/. ubuntu sudo is refused.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
if [[ "$(id -u)" -eq 0 ]]; then
  if [[ "${SUDO_USER:-}" != "hermes-op" ]]; then
    echo "REFUSED: /var/backups backup is hermes-op only" >&2
    exit 1
  fi
  dest="/var/backups/hermes-engineering-os/pag2-$stamp"
  install -d -m 0750 -o root -g hermes-op /var/backups/hermes-engineering-os
  install -d -m 0750 -o root -g hermes-op "$dest"
else
  dest="${EOS_PAG2_BACKUP:-$ROOT/.runtime/pag2-backup}/$stamp"
  mkdir -p "$dest"
fi
protected=/usr/lib/hermes-runtime/hermes-agent/hermes_cli/kanban_db.py
{
  echo "captured_at=$stamp"
  echo "live_head=$(git -C /home/ubuntu/.hermes/hermes-agent rev-parse HEAD 2>/dev/null || echo missing)"
  echo "eos_head=$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo missing)"
  echo "protected_head=$(git -c safe.directory=/usr/lib/hermes-runtime/hermes-agent -C /usr/lib/hermes-runtime/hermes-agent rev-parse HEAD 2>/dev/null || echo missing)"
  echo "transform_live=$(rg -c transform_kanban_worker_spawn /home/ubuntu/.hermes/hermes-agent/hermes_cli/kanban_db.py 2>/dev/null || echo 0)"
  echo "transform_protected=$(rg -c transform_kanban_worker_spawn "$protected" 2>/dev/null || echo 0)"
  echo "h1=$("$ROOT/scripts/verify-operator-boundary.sh" | awk -F= '/^status=/{print $2; exit}')"
  echo "principals=$(getent passwd | awk -F: '$3>=1000 && $3<65534 {printf "%s:%s ",$1,$3}')"
  echo "gateway=$(pgrep -af 'hermes_cli.main' | rg 'gateway run' | rg -v 'rg ' || true)"
} > "$dest/summary.txt"
if [[ "$(id -u)" -eq 0 ]]; then
  if [[ -f /etc/hermes-eos/actuator.env ]]; then
    cp -a /etc/hermes-eos/actuator.env "$dest/actuator.env"
  fi
  if [[ -f /var/lib/hermes-actuator/state.json ]]; then
    cp -a /var/lib/hermes-actuator/state.json "$dest/state.json"
  fi
fi
if rg -q "FAKE_PAG2_SECRET_ABC123|BEGIN OPENSSH PRIVATE|production-approval.ed25519" "$dest" 2>/dev/null; then
  echo "FAIL: backup contained secret material" >&2
  exit 1
fi
echo "wrote $dest/summary.txt"
if [[ "$(id -u)" -ne 0 ]]; then
  echo "NOTE: /var/backups/hermes-engineering-os copy requires hermes-op sudo after H1"
fi
