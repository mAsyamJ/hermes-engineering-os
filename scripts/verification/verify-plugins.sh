#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=../lib/repo-root.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/../lib/repo-root.sh"
ROOT="$(_eos_repo_root_from "${BASH_SOURCE[0]}")"
HERMES_PY="/home/ubuntu/.hermes/hermes-agent/venv/bin/python"

test -x "$HERMES_PY"
"$ROOT/scripts/maintenance/check-vendor-provenance.sh"

python3 - "$ROOT" <<'PY'
import ast
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
for path in [
    root / "__init__.py",
    root / "vendor/hermes-dashboard-base/dashboard/plugin_api.py",
]:
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
for path in [
    root / "vendor/hermes-dashboard-base/dashboard/manifest.json",
    root / "vendor/cockpit/dashboard/manifest.json",
]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["entry"].endswith(".js")
    assert ".." not in manifest["entry"]
for path in [
    root / "vendor/hermes-dashboard-base/dashboard/dist/index.js",
    root / "vendor/cockpit/dashboard/dist/index.js",
]:
    source = path.read_text(encoding="utf-8")
    assert "(function" in source
    assert "window.__HERMES_PLUGIN_SDK__" in source
    assert "import React" not in source
    assert "session_token" not in source.lower()
print("PASS: static plugin and dashboard checks")
PY

timeout 30 "$HERMES_PY" -I "$ROOT/scripts/verification/preflight-plugins.py" \
  > "$ROOT/tests/evidence/plugin-preflight.json"

python3 - "$ROOT/tests/evidence/plugin-preflight.json" <<'PY'
import json
from pathlib import Path
import sys
result = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert result["status"] == "PASS"
assert all(item.get("import") == "PASS" for item in result["results"])
print(f"PASS: qualified {len(result['results'])} plugins in isolation")
PY

node "$ROOT/tests/node/vendor-plugin-smoke.cjs" \
  > "$ROOT/tests/evidence/vendor-dashboard-smoke.json"

"$HERMES_PY" -I - "$ROOT" <<'PY'
import importlib.util
from pathlib import Path
import sys

root = Path(sys.argv[1])
entry = root / "vendor/hermes-dashboard-base/dashboard/plugin_api.py"
spec = importlib.util.spec_from_file_location("_example_dashboard_api", entry)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
routes = [route for route in module.router.routes if "/hello" == route.path]
assert len(routes) == 1 and routes[0].methods == {"GET"}
print("PASS: official dashboard backend exposes GET-only fixture route")
PY

