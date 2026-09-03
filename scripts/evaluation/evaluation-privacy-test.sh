#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=../lib/repo-root.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/../lib/repo-root.sh"
ROOT="$(_eos_repo_root_from "${BASH_SOURCE[0]}")"
SECRET="FAKE_PHASE4_SECRET_ABC123"
EVIDENCE="$ROOT/evidence/phase4/privacy"
mkdir -p "$EVIDENCE"
export PYTHONPATH="$ROOT"
export EOS_EVAL_SANDBOX=inline
python3 - "$ROOT" "$SECRET" "$EVIDENCE" <<'PY'
import json, sys
from pathlib import Path
from engineering_os.evaluation.artifacts import scan_bytes
from engineering_os.evaluation.engine import evaluate_trees
from engineering_os.evaluation.profiles import load_profile
root = Path(sys.argv[1])
secret = sys.argv[2]
assert scan_bytes(secret.encode()) == "FAIL"
profile = load_profile("fixture")
tree = root / "tests/evaluation/fixture_src"
payload = evaluate_trees(tree, profile, baseline=tree)
blob = json.dumps(payload)
assert secret not in blob
Path(sys.argv[3], "vector.json").write_text(blob)
print("PASS: fake secret not in evaluation payload")
PY
# Host secret paths must not appear in candidate env of inline sanitized_env
python3 - <<'PY'
from engineering_os.evaluation.sandbox import sanitized_env
env = sanitized_env()
assert "SSH_AUTH_SOCK" not in env
assert not any("SECRET" in key or "TOKEN" in key for key in env)
print("PASS: sanitized env")
PY
echo "PASS: evaluation privacy"
