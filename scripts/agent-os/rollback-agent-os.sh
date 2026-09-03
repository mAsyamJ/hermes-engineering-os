#!/usr/bin/env bash
# Disable Agent OS without destroying Hermes state.
set -euo pipefail

HERMES="/home/ubuntu/.local/bin/hermes"
LINK="/home/ubuntu/.hermes/plugins/agent-os-router"
SKILLS_MD="/home/ubuntu/.hermes/SKILLS.md"

"$HERMES" plugins disable agent-os-router || true

# Generated projection only — never touch native skills/
if [[ -f "$SKILLS_MD" ]]; then
  # Keep a copy under backups for forensics
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  backup="/var/backups/hermes-engineering-os/agent-os-rollback-$stamp"
  sudo install -d -o ubuntu -g ubuntu -m 0700 "$backup"
  cp --preserve=mode,timestamps "$SKILLS_MD" "$backup/SKILLS.md"
  rm -f "$SKILLS_MD"
  echo "removed generated SKILLS.md (backup=$backup)"
fi

# Leave symlink in place (disabled) or remove on request
if [[ "${1:-}" == "--remove-symlink" && -L "$LINK" ]]; then
  rm -f "$LINK"
  echo "removed plugin symlink"
fi

echo "PASS: agent-os-router disabled; native skills/sessions/DBs untouched"
"$HERMES" plugins list --json --user | python3 -c 'import json,sys; d=json.load(sys.stdin);
print([x for x in d if x.get("name")=="agent-os-router"])'
