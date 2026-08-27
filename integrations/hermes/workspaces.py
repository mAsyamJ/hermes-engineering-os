"""Read-only configured repository and Hermes workspace inventory."""

from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any

from engineering_os.config import load_repositories
from .kanban import list_tasks


def _worktrees(repository: Path) -> list[dict[str, Any]]:
    if not (repository / ".git").exists():
        return []
    output = subprocess.run(
        ["git", "-C", str(repository), "worktree", "list", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    ).stdout
    records: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for line in output.splitlines() + [""]:
        if not line:
            if current:
                records.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value or True
    return records


def list_workspaces() -> dict[str, Any]:
    repositories = []
    for config in load_repositories():
        path = Path(config["path"])
        repositories.append(
            {
                **config,
                "exists": path.exists(),
                "worktrees": _worktrees(path) if path.exists() else [],
            }
        )
    task_workspaces = [
        {
            "hermes_kanban_task_id": task.get("id"),
            "path": task.get("workspace_path"),
            "branch": task.get("branch_name"),
            "status": task.get("status"),
        }
        for task in list_tasks(limit=500)
        if task.get("workspace_path")
    ]
    return {"repositories": repositories, "task_workspaces": task_workspaces}

