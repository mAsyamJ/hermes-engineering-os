"""Configuration loading with a fixed repository allowlist."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPOSITORIES_PATH = ROOT / "config/repositories.json"


def load_repositories(path: Path = REPOSITORIES_PATH) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    repositories = payload.get("repositories", [])
    if not isinstance(repositories, list):
        raise ValueError("repositories must be a list")
    result = []
    for item in repositories:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError("repository entries require string id")
        configured = Path(str(item.get("path", ""))).expanduser()
        if not configured.is_absolute():
            raise ValueError(f"repository {item['id']} path must be absolute")
        result.append({**item, "path": str(configured.resolve(strict=False))})
    return result


def repository_by_id(repository_id: str) -> dict[str, Any]:
    matches = [item for item in load_repositories() if item["id"] == repository_id]
    if len(matches) != 1:
        raise KeyError(repository_id)
    return matches[0]

