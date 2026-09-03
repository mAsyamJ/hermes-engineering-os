#!/usr/bin/env bash
# Read-only snapshot of this VPS Hermes Agent OS. Never starts units or containers.
set -euo pipefail
# shellcheck source=../lib/repo-root.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/../lib/repo-root.sh"
ROOT="$(_eos_repo_root_from "${BASH_SOURCE[0]}")"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="${1:-$ROOT/tests/evidence/platform-overview-$STAMP.json}"

python3 - "$ROOT" "$DEST" "$STAMP" <<'PY'
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

root, dest, stamp = sys.argv[1], sys.argv[2], sys.argv[3]


def run(cmd: list[str], cwd: str | None = None) -> str:
    try:
        return subprocess.check_output(cmd, cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def unit(scope: str, name: str) -> dict[str, str]:
    cmd = ["systemctl", "show", name, "-p", "Id", "-p", "LoadState", "-p", "ActiveState", "-p", "SubState", "-p", "UnitFileState", "-p", "MainPID"]
    if scope == "user":
        cmd.insert(1, "--user")
    text = run(cmd)
    data: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            data[k] = v
    return data


def http(url: str, method: str = "GET") -> object:
    req = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception as exc:
        return f"ERR:{type(exc).__name__}"


def git(path: str, *args: str) -> str:
    return run(["git", "-C", path, *args])


usage = shutil.disk_usage("/")
docker_rows = []
raw = run(["sudo", "-n", "docker", "ps", "-a", "--filter", "name=hermes-eos", "--format", "{{json .}}"])
for line in raw.splitlines():
    if line.strip():
        item = json.loads(line)
        docker_rows.append(
            {
                "Names": item.get("Names"),
                "State": item.get("State"),
                "Status": item.get("Status"),
                "Ports": item.get("Ports"),
            }
        )

hook_live = run(["rg", "-n", "transform_kanban_worker_spawn|pre_worker_spawn", "/home/ubuntu/.hermes/hermes-agent/hermes_cli/kanban_db.py", "/home/ubuntu/.hermes/hermes-agent/hermes_cli/plugins.py"])
plugin = Path("/home/ubuntu/.hermes/plugins/engineering-os")
profiles = sorted(p.name for p in Path("/home/ubuntu/.hermes/profiles").iterdir()) if Path("/home/ubuntu/.hermes/profiles").is_dir() else []
skills = sorted(p.name for p in Path("/home/ubuntu/.hermes/skills").iterdir() if p.is_dir() and not p.name.startswith(".")) if Path("/home/ubuntu/.hermes/skills").is_dir() else []
plugins = sorted(p.name for p in Path("/home/ubuntu/.hermes/plugins").iterdir()) if Path("/home/ubuntu/.hermes/plugins").is_dir() else []

units = {}
for name in (
    "hermes-dashboard.service",
    "hermes-gateway.service",
    "hermes-gateway-rp-friend.service",
    "hermes-eos-analytics.timer",
    "hermes-eos-evaluate.timer",
    "hermes-eos-performance.timer",
    "hermes-eos-experiments.timer",
    "hermes-eos-adaptation.timer",
):
    units[name] = {"user": unit("user", name), "system": unit("system", name)}
units["hermes-eos-actuator.service"] = {"system": unit("system", "hermes-eos-actuator.service")}

payload = {
    "captured_at": stamp,
    "eos_git": {
        "head": git(root, "rev-parse", "HEAD"),
        "subject": git(root, "log", "-1", "--format=%s"),
        "origin_main": git(root, "rev-parse", "origin/main"),
        "status_sb": git(root, "status", "-sb"),
    },
    "hermes_git": {
        "head": git("/home/ubuntu/.hermes/hermes-agent", "rev-parse", "HEAD"),
        "subject": git("/home/ubuntu/.hermes/hermes-agent", "log", "-1", "--format=%s"),
        "dirty": git("/home/ubuntu/.hermes/hermes-agent", "status", "--porcelain"),
    },
    "retropick": {
        "retropick": git("/opt/retropick", "rev-parse", "HEAD"),
        "android": git("/opt/retropick-android", "rev-parse", "HEAD"),
    },
    "units": units,
    "http": {
        "dashboard_9119": http("http://127.0.0.1:9119/"),
        "sidecar_9120_adaptation_readiness": http("http://127.0.0.1:9120/adaptation/readiness"),
        "sidecar_9120_post_adaptation": http("http://127.0.0.1:9120/adaptation", "POST"),
        "phoenix_6006_healthz": http("http://127.0.0.1:6006/healthz"),
    },
    "docker_eos": docker_rows,
    "plugin_symlink": {
        "path": str(plugin),
        "is_symlink": plugin.is_symlink(),
        "target": os.path.realpath(plugin) if plugin.exists() or plugin.is_symlink() else None,
    },
    "live_spawn_hook": "PRESENT" if hook_live else "ABSENT",
    "disk": {
        "free_gib": round(usage.free / 1024**3, 2),
        "used_pct": round(100 * usage.used / usage.total, 1),
    },
    "profiles": profiles,
    "skills": skills,
    "plugins": plugins,
    "budget_auth_present": Path(root, ".runtime/experiments/LLM_BUDGET_AUTHORIZATION").is_file(),
}

Path(dest).parent.mkdir(parents=True, exist_ok=True)
Path(dest).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(dest)
PY

echo "=== pag2-status ==="
"$ROOT/scripts/deployment/pag2-status.sh" || true
echo "=== operator-boundary ==="
"$ROOT/scripts/verification/verify-operator-boundary.sh" || true
