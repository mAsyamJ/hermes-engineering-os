#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
LINK="/home/ubuntu/.hermes/plugins/engineering-os"
HERMES="/home/ubuntu/.local/bin/hermes"

test "$ROOT" = "/opt/hermes-engineering-os"
test "$(stat -c %U "$ROOT")" = "ubuntu"
test "$(git -C "$ROOT" rev-parse --show-toplevel)" = "$ROOT"
test -z "$(git -C "$ROOT" status --porcelain)"
test -f "$ROOT/plugin.yaml"
test -f "$ROOT/dashboard/manifest.json"
test -f "$ROOT/dashboard/dist/index.js"
test -f "$ROOT/dashboard/plugin_api.py"

"$ROOT/scripts/verify-plugins.sh"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup="/var/backups/hermes-engineering-os/phase1-pre-plugin-$stamp"
sudo install -d -o ubuntu -g ubuntu -m 0700 "$backup"
if [[ -f /home/ubuntu/.hermes/config.yaml ]]; then
  sudo cp --preserve=mode,timestamps /home/ubuntu/.hermes/config.yaml "$backup/config.yaml"
fi
"$HERMES" plugins list --json --user > "/tmp/engineering-os-plugin-state-$$.json"
sudo install -o ubuntu -g ubuntu -m 0600 \
  "/tmp/engineering-os-plugin-state-$$.json" "$backup/plugins-before.json"
rm -f "/tmp/engineering-os-plugin-state-$$.json"
for service in hermes-dashboard.service hermes-gateway.service hermes-gateway-rp-friend.service; do
  printf '%s=%s\n' "$service" "$(systemctl --user show "$service" -p MainPID --value)"
done | sudo tee "$backup/service-pids-before.txt" >/dev/null
printf 'link=%s\n' "$(readlink "$LINK" 2>/dev/null || true)" \
  | sudo tee "$backup/plugin-link-before.txt" >/dev/null
sudo chown ubuntu:ubuntu "$backup/service-pids-before.txt" "$backup/plugin-link-before.txt"
sudo chmod 0600 "$backup/service-pids-before.txt" "$backup/plugin-link-before.txt"
sudo sh -c "cd '$backup' && sha256sum ./* > SHA256SUMS"
sudo chown ubuntu:ubuntu "$backup/SHA256SUMS"
sudo chmod 0600 "$backup/SHA256SUMS"

if [[ -L "$LINK" ]]; then
  test "$(readlink -f "$LINK")" = "$ROOT"
elif [[ -e "$LINK" ]]; then
  echo "refusing to replace existing non-symlink: $LINK" >&2
  exit 1
else
  ln -s "$ROOT" "$LINK"
fi

"$HERMES" plugins enable engineering-os --no-allow-tool-override
"$ROOT/scripts/rescan-dashboard.sh"

echo "PASS: engineering-os enabled from exact guarded symlink"
echo "backup=$backup"

