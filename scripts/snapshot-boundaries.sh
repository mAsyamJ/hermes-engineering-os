#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="${1:-snapshot}"
OUT="$ROOT/tests/evidence/${LABEL}-$(date -u +%Y%m%dT%H%M%SZ).json"

python3 - "$OUT" <<'PY'
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time

def run(argv):
    return subprocess.run(argv, check=True, capture_output=True, text=True, timeout=15).stdout.strip()

def git_state(path):
    porcelain = run(["git", "-C", path, "status", "--porcelain=v1"])
    return {
        "head": run(["git", "-C", path, "rev-parse", "HEAD"]),
        "porcelain_count": len(porcelain.splitlines()) if porcelain else 0,
        "porcelain_sha256": hashlib.sha256(porcelain.encode()).hexdigest(),
    }

services = {}
for name in ("hermes-dashboard.service", "hermes-gateway.service", "hermes-gateway-rp-friend.service"):
    fields = run(["systemctl", "--user", "show", name, "-p", "ActiveState,SubState,MainPID"])
    parsed = dict(line.split("=", 1) for line in fields.splitlines())
    services[name] = parsed

docker_lines = run(["sudo", "-n", "docker", "ps", "-a", "--format", "{{json .}}"])
docker = [json.loads(line) for line in docker_lines.splitlines() if line]
disk = shutil.disk_usage("/")
db = Path("/home/ubuntu/.hermes/kanban/boards/retropick-markets-release/kanban.db")
kanban = {"path": str(db), "exists": db.is_file()}
if db.is_file():
    connection = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    connection.execute("PRAGMA query_only=ON")
    kanban["task_count"] = connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    kanban["run_count"] = connection.execute("SELECT COUNT(*) FROM task_runs").fetchone()[0]
    connection.close()

payload = {
    "captured_at": int(time.time()),
    "storage": {
        "total_bytes": disk.total,
        "used_bytes": disk.used,
        "free_bytes": disk.free,
        "percent_used": round(disk.used / disk.total * 100, 1),
    },
    "services": services,
    "production_git": {
        "/opt/retropick": git_state("/opt/retropick"),
        "/opt/retropick-android": git_state("/opt/retropick-android"),
    },
    "docker": docker,
    "kanban": kanban,
    "hermes_source": git_state("/home/ubuntu/.hermes/hermes-agent"),
}
Path(sys.argv[1]).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(sys.argv[1])
PY

