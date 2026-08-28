#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
HERMES_PY="/home/ubuntu/.hermes/hermes-agent/venv/bin/python"
LINK="/home/ubuntu/.hermes/plugins/engineering-os"
BROWSERS="$ROOT/.cache/ms-playwright"

test -L "$LINK"
test "$(readlink -f "$LINK")" = "$ROOT"
test "$(git -C "$ROOT" ls-files upstream | wc -l)" -eq 0

(
  cd /var/backups/hermes-engineering-os/20260827T120255Z
  sha256sum --quiet -c SHA256SUMS
)
echo "PASS: Phase 0 backup checksums"

"/home/ubuntu/.local/bin/hermes" plugins list --json --user \
  | rg -q '"engineering-os"'
echo "PASS: Engineering OS is enabled"

"$ROOT/scripts/verify-plugins.sh"

PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" PYTHONDONTWRITEBYTECODE=1 "$HERMES_PY" \
  -m unittest discover -s "$ROOT/tests/python" -v

(
  cd "$ROOT/dashboard"
  npm run check
  npm run build
  npm test
  PLAYWRIGHT_BROWSERS_PATH="$BROWSERS" npm run test:browser
  LIVE_DASHBOARD=1 PLAYWRIGHT_BROWSERS_PATH="$BROWSERS" \
    npx playwright test browser/live.spec.cjs
)

for view in health overview tasks runs agents plugins github workspaces observability analytics evaluations performance experiments; do
  "$ROOT/scripts/dashboard-request.py" \
    "/api/plugins/engineering-os/$view" \
    --expect-status 200 \
    --quiet
done
curl -fsS \
  http://127.0.0.1:9119/dashboard-plugins/engineering-os/dist/index.js \
  >/dev/null
curl -fsS \
  http://127.0.0.1:9119/dashboard-plugins/engineering-os/dist/style.css \
  >/dev/null
echo "PASS: live routes and assets"

python3 - "$ROOT" <<'PY'
from pathlib import Path
import json
import shutil
import sys

root = Path(sys.argv[1])
pre_path = sorted((root / "tests/evidence").glob("pre-install-*.json"))[-1]
post_path = sorted((root / "tests/evidence").glob("post-install-*.json"))[-1]
pre = json.loads(pre_path.read_text(encoding="utf-8"))
post = json.loads(post_path.read_text(encoding="utf-8"))
assert pre["production_git"] == post["production_git"]
for service in ("hermes-gateway.service", "hermes-gateway-rp-friend.service"):
    assert pre["services"][service] == post["services"][service]
assert post["services"]["hermes-dashboard.service"]["ActiveState"] == "active"

keys = ("Names", "State", "Ports", "HealthStatus", "Image")

def docker_name(item):
    return str(item.get("Names") or "").lstrip("/")

def docker_boundary(payload, exclude_eos=False):
    rows = []
    for item in payload:
        if exclude_eos and docker_name(item).startswith("hermes-eos-"):
            continue
        rows.append(tuple(item.get(key) for key in keys))
    return sorted(rows)

assert docker_boundary(pre["docker"]) == docker_boundary(post["docker"])

usage = shutil.disk_usage("/")
assert usage.free >= 20 * 1024**3, usage.free
assert usage.used / usage.total < 0.80, usage.used / usage.total

entry_path = sorted((root / "tests/evidence").glob("phase2-entry-*.json"))[-1]
entry = json.loads(entry_path.read_text(encoding="utf-8"))
close_paths = sorted((root / "tests/evidence").glob("phase2-close-*.json"))
if close_paths:
    live = json.loads(close_paths[-1].read_text(encoding="utf-8"))
    assert live["production_git"] == entry["production_git"]
    for service in ("hermes-gateway.service", "hermes-gateway-rp-friend.service"):
        assert live["services"][service]["MainPID"] == entry["services"][service]["MainPID"]
    assert docker_boundary(live["docker"], exclude_eos=True) == docker_boundary(
        entry["docker"], exclude_eos=True
    )
print("PASS: production Git, Docker, gateway, dispatcher, and storage boundaries")
PY

if rg -n \
  '(gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|Bearer [A-Za-z0-9._~+/=-]{12,}|sk-[A-Za-z0-9]{16,})' \
  "$ROOT/dashboard/dist" "$ROOT/docs" "$ROOT/provenance" \
  "$ROOT/tests/evidence"; then
  echo "FAIL: secret-like value in shipped output or evidence" >&2
  exit 1
fi
echo "PASS: no secret-like values in shipped output or evidence"
"$ROOT/scripts/verify-experiment-data.sh"
echo "PASS: Phase 6 verification complete"

