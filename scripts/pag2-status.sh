#!/usr/bin/env bash
# Read-only PAG-2 gate dashboard. Never changes users, units, or production.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"

live="$(git -C /home/ubuntu/.hermes/hermes-agent rev-parse HEAD 2>/dev/null || echo missing)"
if rg -q transform_kanban_worker_spawn /home/ubuntu/.hermes/hermes-agent/hermes_cli/kanban_db.py 2>/dev/null; then
  live_hook=PRESENT
else
  live_hook=ABSENT
fi
protected="$(git -c safe.directory=/usr/lib/hermes-runtime/hermes-agent -C /usr/lib/hermes-runtime/hermes-agent rev-parse HEAD 2>/dev/null || echo missing)"
if [[ -f /usr/lib/hermes-runtime/hermes-agent/hermes_cli/kanban_db.py ]] \
  && rg -q transform_kanban_worker_spawn /usr/lib/hermes-runtime/hermes-agent/hermes_cli/kanban_db.py; then
  protected_hook=PRESENT
else
  protected_hook=ABSENT
fi

python3 - <<'PY'
from engineering_os.adaptation.pag2_ops import (
    approval_a_granted,
    h3_live_seam_present,
    load_pag2_label,
    read_h1_status,
)
from engineering_os.experiments.budget_gate import require_budget_authorization
from engineering_os.experiments.definitions import load_id

definition = load_id("real-model-sol-vs-terra-v2")
budget = require_budget_authorization(definition)
h1 = read_h1_status()
h3 = h3_live_seam_present()
label = load_pag2_label()
approval = approval_a_granted()
print(f"h1={h1}")
print(f"h3={str(h3).lower()}")
print(f"pag2_label={label}")
print(f"budget={budget.get('status')}")
print(f"approval_a={str(approval).lower()}")
print("auto_promote=false")
if h1 != "PASS":
    nxt = "HUMAN ACTION REQUIRED — H1"
elif not budget.get("ok"):
    nxt = "HUMAN ACTION REQUIRED — H2"
elif label in {"NOT_STARTED", "COLLECTING"}:
    nxt = "HUMAN ACTION REQUIRED — EXPERIMENT"
elif label == "VALID_NO_PROMOTION":
    nxt = "VALID_NO_PROMOTION — skip canary"
elif label != "QUALIFIED_CANDIDATE":
    nxt = f"HUMAN ACTION REQUIRED — EVIDENCE ({label})"
elif not h3:
    nxt = "HUMAN ACTION REQUIRED — H3"
elif not approval:
    nxt = "HUMAN ACTION REQUIRED — APPROVAL A"
else:
    nxt = "HUMAN ACTION REQUIRED — CANARY"
print(f"next={nxt}")
PY

echo "live_sha=$live"
echo "live_spawn_hook=$live_hook"
echo "protected_sha=$protected"
echo "protected_spawn_hook=$protected_hook"
