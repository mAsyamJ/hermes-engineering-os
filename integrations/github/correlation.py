"""Conservative task-to-Git evidence correlation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engineering_os.models import Evidence, EvidenceStatus
from .local_git import all_repository_statuses


def correlate_task(task: dict[str, Any]) -> Evidence[dict[str, Any]]:
    task_id = task.get("id")
    workspace = task.get("workspace_path")
    branch = task.get("branch_name")
    if not task_id or not workspace or not branch:
        return Evidence(
            EvidenceStatus.UNKNOWN,
            "correlation:explicit-metadata",
            {"hermes_kanban_task_id": task_id},
            detail="task lacks explicit workspace and branch metadata",
        )
    target = Path(str(workspace)).resolve(strict=False)
    matches = []
    for repository in all_repository_statuses():
        configured = Path(repository["path"]).resolve(strict=False)
        if target == configured or configured in target.parents:
            matches.append(repository)
    if len(matches) != 1:
        return Evidence(
            EvidenceStatus.UNKNOWN,
            "correlation:allowlist",
            {"hermes_kanban_task_id": task_id, "workspace": str(target), "branch": branch},
            detail="workspace does not map unambiguously to one configured repository",
        )
    repository = matches[0]
    return Evidence(
        EvidenceStatus.AVAILABLE,
        "correlation:explicit-metadata",
        {
            "hermes_kanban_task_id": task_id,
            "workspace": str(target),
            "branch": branch,
            "repository_id": repository["id"],
            "git_sha": repository.get("head") if repository.get("branch") == branch else None,
            "github_pr_id": None,
            "github_checks": [],
            "github_state": "UNKNOWN",
        },
    )

