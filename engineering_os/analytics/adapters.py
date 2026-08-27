"""Read-only analytics facades over Phase 1/2 adapters. Never mutate sources."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engineering_os.models import Evidence, EvidenceStatus
from engineering_os.redaction import redact
from integrations.github.client import pull_request_evidence
from integrations.github.local_git import branch_commit, resolve_repository_for_workspace
from integrations.hermes import kanban
from engineering_os.observability import phoenix_client


HERMES_HOME = Path.home() / ".hermes"


def hermes_home() -> Path:
    override = Path(__import__("os").environ.get("HERMES_HOME", str(HERMES_HOME)))
    return override


def board_database(board: str) -> Path:
    home = hermes_home()
    if board in {"default", ""}:
        return home / "kanban.db"
    return home / "kanban" / "boards" / board / "kanban.db"


def list_boards() -> list[str]:
    return kanban.list_boards(hermes_home())


def read_task(board: str, task_id: str) -> dict[str, Any] | None:
    path = board_database(board)
    if not path.is_file():
        return None
    task = kanban.get_task(task_id, path=path)
    if task is None:
        return None
    task["board"] = board
    return task


def iter_task_ids(board: str, since: int | None = None) -> list[str]:
    path = board_database(board)
    if not path.is_file():
        return []
    return kanban.list_task_ids(path=path, since=since)


def read_comment_authors(board: str, task_id: str) -> list[dict[str, Any]]:
    path = board_database(board)
    if not path.is_file():
        return []
    return kanban.list_comment_authors(task_id, path=path)


def phoenix_traces(task_id: str) -> Evidence[list[dict[str, Any]]]:
    try:
        rows = phoenix_client.traces_for_task(task_id)
        return Evidence(EvidenceStatus.AVAILABLE, "phoenix:graphql", rows)
    except Exception as exc:
        return Evidence(
            EvidenceStatus.DEGRADED,
            "phoenix:graphql",
            [],
            detail=f"{type(exc).__name__}: {exc}",
        )


def git_for_task(task: dict[str, Any]) -> Evidence[dict[str, Any]]:
    workspace = task.get("workspace_path")
    branch = task.get("branch_name")
    if not workspace:
        return Evidence(
            EvidenceStatus.UNKNOWN,
            "git:local",
            {"evidence_quality": "UNKNOWN"},
            detail="task has no workspace_path",
        )
    try:
        repository = resolve_repository_for_workspace(str(workspace))
    except KeyError:
        return Evidence(
            EvidenceStatus.UNKNOWN,
            "git:local",
            {"evidence_quality": "UNKNOWN", "workspace": workspace},
            detail="workspace is not allowlisted",
        )
    if repository.get("mode") == "disposable-fixture" and not branch:
        return Evidence(
            EvidenceStatus.UNKNOWN,
            "git:local",
            {
                "evidence_quality": "NOT_APPLICABLE",
                "repository_id": repository.get("id"),
            },
            detail="disposable fixture without branch",
        )
    if not branch:
        return Evidence(
            EvidenceStatus.UNKNOWN,
            "git:local",
            {
                "evidence_quality": "UNKNOWN",
                "repository_id": repository.get("id"),
            },
            detail="task has no branch_name",
        )
    try:
        info = branch_commit(str(repository["id"]), str(branch))
    except Exception as exc:
        return Evidence(
            EvidenceStatus.DEGRADED,
            "git:local",
            {"evidence_quality": "UNKNOWN"},
            detail=f"{type(exc).__name__}: {exc}",
        )
    quality = "AVAILABLE" if info.get("commit_sha") else "NOT_FOUND"
    payload = {
        "repository_id": repository["id"],
        "branch": branch,
        "commit_sha": info.get("commit_sha"),
        "dirty_at_observation": info.get("dirty"),
        "evidence_quality": quality,
    }
    status = EvidenceStatus.AVAILABLE if quality == "AVAILABLE" else EvidenceStatus.UNKNOWN
    return Evidence(status, "git:local", payload, detail=None if info.get("commit_sha") else "branch ref not found")


def github_for_task(task: dict[str, Any], repository: dict[str, Any] | None = None) -> Evidence[dict[str, Any]]:
    if repository is None:
        workspace = task.get("workspace_path")
        if workspace:
            try:
                repository = resolve_repository_for_workspace(str(workspace))
            except KeyError:
                repository = None
    if repository is None or not repository.get("github"):
        return Evidence(
            EvidenceStatus.UNKNOWN,
            "github:api",
            {"evidence_state": "NOT_APPLICABLE", "evidence_quality": "NOT_APPLICABLE"},
            detail="repository has no GitHub slug",
        )
    slug = str(repository["github"])
    branch = str(task.get("branch_name") or "")
    return pull_request_evidence(slug, branch)


def redact_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    return redact(bundle)
