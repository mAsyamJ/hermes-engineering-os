"""Read-only worker projection from canonical Kanban run records."""

from __future__ import annotations

import os
from typing import Any

from .kanban import list_runs


def _pid_alive(pid: Any) -> bool:
    try:
        value = int(pid)
        if value <= 0:
            return False
        os.kill(value, 0)
        return True
    except (TypeError, ValueError, ProcessLookupError, PermissionError):
        return False


def list_workers() -> list[dict[str, Any]]:
    workers = []
    for run in list_runs(limit=500):
        if run.get("status") != "running":
            continue
        workers.append(
            {
                "profile": run.get("profile"),
                "hermes_kanban_task_id": run.get("task_id"),
                "hermes_kanban_run_id": run.get("id"),
                "worker_pid": run.get("worker_pid"),
                "pid_alive": _pid_alive(run.get("worker_pid")),
                "status": run.get("status"),
                "last_heartbeat_at": run.get("last_heartbeat_at"),
            }
        )
    return workers

