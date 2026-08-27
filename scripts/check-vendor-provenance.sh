#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAP="$ROOT/provenance/VENDOR_MAP.md"

python3 - "$ROOT" "$MAP" <<'PY'
from pathlib import Path
import re
import sys

root = Path(sys.argv[1]).resolve()
text = Path(sys.argv[2]).read_text(encoding="utf-8")
mapped = set(re.findall(r"local_path: `([^`]+)`", text))
actual = {
    str(path.relative_to(root))
    for path in (root / "vendor").rglob("*")
    if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
}
missing = sorted(actual - mapped)
stale = sorted(path for path in mapped if path.startswith("vendor/") and path not in actual)
if missing or stale:
    print("unmapped:", *missing, sep="\n  ")
    print("stale:", *stale, sep="\n  ")
    raise SystemExit(1)
for path in actual:
    if path.startswith("vendor/agent-kanban"):
        raise SystemExit("agent-kanban source is forbidden in vendor/")
print(f"PASS: {len(actual)} vendor files have provenance records")
PY

if rg -n --hidden \
  '(localhost:[0-9]+/api/tasks|new WebSocket|node-pty|@xyflow/react|framer-motion|from ["'\'']react["'\'']|session[_-]?token)' \
  "$ROOT/vendor" \
  --glob '!**/LICENSE' \
  --glob '!**/README.md'; then
  echo "FAIL: forbidden donor runtime assumption found" >&2
  exit 1
fi

echo "PASS: no forbidden donor runtime dependencies"

