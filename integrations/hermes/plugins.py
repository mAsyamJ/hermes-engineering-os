"""Plugin inventory without importing plugins into the dashboard process."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Any

PLUGIN_ROOT = Path.home() / ".hermes/plugins"


def _manifest_state(plugin: dict[str, Any]) -> dict[str, Any]:
    raw_path = plugin.get("path")
    if not raw_path and isinstance(plugin.get("name"), str):
        candidate = PLUGIN_ROOT / plugin["name"]
        if candidate.exists():
            raw_path = str(candidate)
    if not raw_path:
        return {"dashboard_manifest": False}
    path = Path(str(raw_path)).resolve(strict=False)
    dashboard = path / "dashboard/manifest.json"
    state: dict[str, Any] = {
        "path": str(path),
        "is_symlink": Path(str(raw_path)).is_symlink(),
        "dashboard_manifest": dashboard.is_file(),
    }
    if dashboard.is_file():
        try:
            manifest = json.loads(dashboard.read_text(encoding="utf-8"))
            state["dashboard"] = {
                key: manifest.get(key)
                for key in ("name", "label", "version", "entry", "api")
            }
        except (OSError, json.JSONDecodeError) as exc:
            state["dashboard_error"] = type(exc).__name__
    return state


def list_plugins() -> dict[str, Any]:
    executable = "/home/ubuntu/.local/bin/hermes"
    process = subprocess.run(
        [executable, "plugins", "list", "--json", "--user"],
        check=True,
        capture_output=True,
        text=True,
        timeout=8,
        env={"HOME": str(Path.home()), "PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    )
    payload = json.loads(process.stdout)
    items = payload if isinstance(payload, list) else payload.get("plugins", [])
    return {
        "plugins": [{**item, **_manifest_state(item)} for item in items],
        "stderr": process.stderr.strip()[:500],
    }

