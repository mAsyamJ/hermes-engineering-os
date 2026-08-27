"""Bounded read-only evidence about the active Hermes runtime."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

SERVICES = (
    "hermes-dashboard.service",
    "hermes-gateway.service",
    "hermes-gateway-rp-friend.service",
)


def _run(argv: list[str], timeout: float = 3.0) -> str:
    return subprocess.run(
        argv,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
        env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(Path.home())},
    ).stdout.strip()


def service_status(name: str) -> dict[str, Any]:
    if name not in SERVICES:
        raise ValueError("service not allowlisted")
    fields = _run(
        [
            "systemctl",
            "--user",
            "show",
            name,
            "--property=ActiveState,SubState,MainPID",
        ]
    )
    parsed = dict(line.split("=", 1) for line in fields.splitlines() if "=" in line)
    return {
        "name": name,
        "active": parsed.get("ActiveState"),
        "substate": parsed.get("SubState"),
        "pid": int(parsed.get("MainPID") or 0),
    }


def runtime_status() -> dict[str, Any]:
    executable = shutil.which("hermes") or "/home/ubuntu/.local/bin/hermes"
    version = _run([executable, "--version"])
    usage = shutil.disk_usage("/")
    return {
        "version": version,
        "executable": str(Path(executable).resolve(strict=False)),
        "services": [service_status(name) for name in SERVICES],
        "storage": {
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "percent_used": round(usage.used / usage.total * 100, 1),
        },
    }

