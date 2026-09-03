#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
HERMES_PY="/home/ubuntu/.hermes/hermes-agent/venv/bin/python"
HERMES="/home/ubuntu/.local/bin/hermes"

echo "== Agent OS unit tests =="
PYTHONPATH="$ROOT" PYTHONDONTWRITEBYTECODE=1 "$HERMES_PY" \
  -m unittest tests.python.test_agent_os_router -v

echo "== Registry regenerate idempotence =="
PYTHONPATH="$ROOT" "$HERMES_PY" - <<'PY'
from agent_os.generate import regenerate
a = regenerate(write_hermes_projection=True)
b = regenerate(write_hermes_projection=True)
assert a["skills_registry_sha256"] == b["skills_registry_sha256"]
assert a["skills_md_sha256"] == b["skills_md_sha256"]
print("idempotent", a)
PY

test -f /home/ubuntu/.hermes/SKILLS.md
head -n 6 /home/ubuntu/.hermes/SKILLS.md | rg -q "Generated artifact"

echo "== Plugin present =="
"$HERMES" plugins list --json --user | rg -q 'agent-os-router'

echo "== Hermes CLI health =="
"$HERMES" version >/dev/null
"$HERMES" skills list --source local >/dev/null

echo "== Core untouched =="
extra="$(git -C /home/ubuntu/.hermes/hermes-agent diff --name-only | rg -v '^package-lock.json$' || true)"
test -z "$extra"

echo "PASS: agent-os-verify"
