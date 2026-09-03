#!/usr/bin/env bash
# Install agent-os-router as a guarded symlink plugin (does not touch engineering-os).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
PLUGIN_SRC="$ROOT/agent_os/plugin"
LINK="/home/ubuntu/.hermes/plugins/agent-os-router"
HERMES="/home/ubuntu/.local/bin/hermes"

test -f "$PLUGIN_SRC/plugin.yaml"
test -f "$PLUGIN_SRC/__init__.py"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup="/var/backups/hermes-engineering-os/agent-os-plugin-$stamp"
sudo install -d -o ubuntu -g ubuntu -m 0700 "$backup"
if [[ -f /home/ubuntu/.hermes/config.yaml ]]; then
  cp --preserve=mode,timestamps /home/ubuntu/.hermes/config.yaml "$backup/config.yaml"
fi
"$HERMES" plugins list --json --user > "$backup/plugins-before.json"
chmod 0600 "$backup"/* 2>/dev/null || true

if [[ -L "$LINK" ]]; then
  test "$(readlink -f "$LINK")" = "$(readlink -f "$PLUGIN_SRC")" \
    || { echo "refusing to replace symlink pointing elsewhere: $LINK" >&2; exit 1; }
elif [[ -e "$LINK" ]]; then
  echo "refusing to replace existing non-symlink: $LINK" >&2
  exit 1
else
  ln -s "$PLUGIN_SRC" "$LINK"
fi

# Ensure registry exists before first load
PYTHONPATH="$ROOT" /home/ubuntu/.hermes/hermes-agent/venv/bin/python - <<'PY'
from agent_os.generate import regenerate
print(regenerate(write_hermes_projection=True))
PY

"$HERMES" plugins enable agent-os-router --no-allow-tool-override
# Safety guards for agent-authored skills
"$HERMES" config set skills.guard_agent_created true

"$HERMES" plugins list --json --user > "$backup/plugins-after.json"
chmod 0600 "$backup/plugins-after.json"
(cd "$backup" && sha256sum ./* > SHA256SUMS)

echo "PASS: agent-os-router enabled from $LINK"
echo "backup=$backup"
