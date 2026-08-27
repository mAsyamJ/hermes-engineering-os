"""Fixed-argv local Git inspection for allowlisted repositories."""

from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any

from engineering_os.config import repository_by_id


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
    from engineering_os.config import load_repositories

    return [repository_status(item["id"]) for item in load_repositories()]

