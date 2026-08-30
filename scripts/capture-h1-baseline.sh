#!/usr/bin/env bash
# Read-only H1 baseline capture. Never prints secrets; never changes units.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
OUT="${EOS_H1_CAPTURE:-$ROOT/.runtime/h1-baseline}"
mkdir -p "$OUT"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
file="$OUT/before-$stamp.txt"

{
  echo "captured_at=$stamp"
  echo "live_head=$(git -C /home/ubuntu/.hermes/hermes-agent rev-parse HEAD)"
  echo "live_dirty=$(git -C /home/ubuntu/.hermes/hermes-agent status --porcelain | tr '\n' ';')"
  echo "transform_hits=$(rg -c transform_kanban_worker_spawn /home/ubuntu/.hermes/hermes-agent/hermes_cli/kanban_db.py 2>/dev/null || echo 0)"
  echo "tree_hash=$(find /home/ubuntu/.hermes/hermes-agent -path '*/.git/*' -prune -o -path '*/venv/*' -prune -o -path '*/node_modules/*' -prune -o -name package-lock.json -prune -o -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}')"
  echo "default_gateway=$(ps -o user,uid,pid,cmd -C python 2>/dev/null | rg 'hermes_cli.main gateway run' | rg -v 'rg ' | head -n 5 || true)"
  echo "rp_friend=$(ps -o user,uid,pid,cmd -C python 2>/dev/null | rg 'profile rp-friend' | rg -v 'rg ' | head -n 5 || true)"
  echo "gateway_user_unit=$(systemctl --user show hermes-gateway.service -p FragmentPath,MainPID,ActiveState --no-page 2>/dev/null || true)"
  echo "rp_friend_unit=$(systemctl --user show hermes-gateway-rp-friend.service -p FragmentPath,MainPID,ActiveState --no-page 2>/dev/null || true)"
  echo "dispatcher_lock=$(stat -c '%U %a %n' /home/ubuntu/.hermes/kanban/.dispatcher.lock 2>/dev/null || echo missing)"
  echo "config_present=$([[ -f /home/ubuntu/.hermes/config.yaml ]] && echo yes || echo no)"
  echo "env_present=$([[ -f /home/ubuntu/.hermes/.env ]] && echo yes || echo no)"
  echo "auth_present=$([[ -f /home/ubuntu/.hermes/auth.json ]] && echo yes || echo no)"
  echo "memory_hash=$(sha256sum /home/ubuntu/.hermes/memories/MEMORY.md 2>/dev/null | awk '{print $1}' || echo missing)"
  echo "skills_count=$(find /home/ubuntu/.hermes/skills -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)"
  echo "profiles=$(ls /home/ubuntu/.hermes/profiles 2>/dev/null | tr '\n' ',')"
  echo "plugin_eos=$(readlink -f /home/ubuntu/.hermes/plugins/engineering-os 2>/dev/null || echo missing)"
  principals=$(getent passwd | awk -F: '$3>=1000 && $3<65534 {printf "%s:%s ",$1,$3}')
  echo "principals=${principals}"
} > "$file"

echo "wrote $file"
echo "NOTE: secret file contents are not captured; only presence/hashes."
