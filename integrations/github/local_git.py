"""Fixed-argv local Git inspection for allowlisted repositories."""

from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any

import re

from engineering_os.config import load_repositories, repository_by_id

_BRANCH_RE = re.compile(r"^[A-Za-z0-9._/\-]+$")


def _git(path: Path, *args: str, check: bool = True) -> str:
    process = subprocess.run(
        ["git", "-C", str(path), *args],
        check=check,
        capture_output=True,
        text=True,
        timeout=5,
    )
    return process.stdout.strip()


def repository_status(repository_id: str) -> dict[str, Any]:
    configured = repository_by_id(repository_id)
    path = Path(configured["path"])
    if not path.exists():
        return {**configured, "exists": False}
    remote = _git(path, "remote", "get-url", "origin", check=False)
    branch = _git(path, "branch", "--show-current")
    head = _git(path, "rev-parse", "HEAD")
    porcelain = _git(path, "status", "--porcelain=v1", "-uno")
    default_ref = _git(
        path, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD", check=False
    )
    return {
        **configured,
        "exists": True,
        "remote": remote,
        "branch": branch or None,
        "head": head,
        "default_branch": default_ref.removeprefix("origin/") or None,
        "dirty": bool(porcelain),
        "porcelain_count": len(porcelain.splitlines()) if porcelain else 0,
    }


def all_repository_statuses() -> list[dict[str, Any]]:
    return [repository_status(item["id"]) for item in load_repositories()]


def resolve_repository_for_workspace(workspace: str) -> dict[str, Any]:
    target = Path(workspace).resolve(strict=False)
    matches = []
    for repository in load_repositories():
        configured = Path(repository["path"]).resolve(strict=False)
        if target == configured or configured in target.parents:
            matches.append(repository)
    if len(matches) != 1:
        raise KeyError(workspace)
    return dict(matches[0])


def branch_commit(repository_id: str, branch: str) -> dict[str, Any]:
    if not _BRANCH_RE.match(branch):
        raise ValueError("invalid branch name")
    configured = repository_by_id(repository_id)
    path = Path(configured["path"])
    if not path.exists():
        return {**configured, "commit_sha": None, "dirty": None, "exists": False}
    sha = _git(path, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", check=False)
    if not sha:
        sha = _git(
            path,
            "rev-parse",
            "--verify",
            "--quiet",
            f"refs/remotes/origin/{branch}",
            check=False,
        )
    porcelain = _git(path, "status", "--porcelain=v1", "-uno", check=False)
    return {
        **configured,
        "exists": True,
        "branch": branch,
        "commit_sha": sha or None,
        "dirty": bool(porcelain),
    }

