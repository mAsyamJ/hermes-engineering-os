#!/usr/bin/env bash
# Present canonical Approval A fields. Does not write a grant. Does not sign.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"
echo "HUMAN ACTION REQUIRED — APPROVAL A"
echo
python3 - <<'PY'
import json
from engineering_os.adaptation.pag2_ops import present_approval_a_request

payload = present_approval_a_request()
if not payload.get("ok"):
    print(payload.get("status") or "BLOCKED")
    print(payload.get("reason") or "Approval A is not ready to sign")
    raise SystemExit(2)
print(json.dumps(payload["grant"], indent=2, sort_keys=True))
print()
print("canonical_hex=" + payload["canonical_hex"])
print()
print("Run this after H3 so live_patch_hash is taken from /etc/hermes-eos/actuator.env.")
print("Sign the canonical_hex bytes off-VPS (not the pretty JSON).")
print("Add a 'signature' hex field to the JSON, then install as hermes-op only:")
print("  sudo install -m 0440 -o root -g hermes-op /path/to/approval-a.granted /var/lib/hermes-actuator/approval-a.granted")
print("Do not paste the private key. Agent-writable copies are not grants.")
print("Status reads verify this file with consume=False so they do not burn the nonce.")
PY
