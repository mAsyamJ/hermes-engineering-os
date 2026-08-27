"""Authenticated, GET-only dashboard routes for Hermes Engineering OS."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

from fastapi import APIRouter, HTTPException, Query

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engineering_os.config import load_repositories  # noqa: E402
from engineering_os.health import safely  # noqa: E402
from engineering_os.observability import health as observability_health  # noqa: E402
from engineering_os.observability import phoenix_client  # noqa: E402
from engineering_os.redaction import redact  # noqa: E402
from integrations.github.client import github_status  # noqa: E402
from integrations.github.correlation import correlate_task  # noqa: E402
from integrations.github.local_git import all_repository_statuses  # noqa: E402
from integrations.hermes import kanban, plugins, profiles, runtime, workers, workspaces  # noqa: E402

router = APIRouter()


def _safe(source: str, operation: Any) -> dict[str, Any]:
    return redact(safely(source, operation))


@router.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "AVAILABLE",
        "plugin": "engineering-os",
        "version": "1.0.0",
        "mode": "read-only",
        "canonical_task_authority": "Hermes Kanban",
    }


@router.get("/overview")
def overview() -> dict[str, Any]:
    return {
        "runtime": _safe("hermes:runtime", runtime.runtime_status),
        "kanban": _safe("hermes:kanban", kanban.summary),
        "plugins": _safe("hermes:plugins", plugins.list_plugins),
        "github": github_view(),
    }


@router.get("/tasks")
def tasks(limit: int = Query(default=200, ge=1, le=500)) -> dict[str, Any]:
    return _safe("hermes:kanban:tasks", lambda: kanban.list_tasks(limit))


@router.get("/tasks/{task_id}")
def task(task_id: str) -> dict[str, Any]:
    value = kanban.get_task(task_id)
    if value is None:
        raise HTTPException(status_code=404, detail="task not found")
    value["correlation"] = correlate_task(value).to_dict()
    value["observability"] = _safe(
        "phoenix:task",
        lambda: phoenix_client.traces_for_task(task_id),
    )
    return redact(value)


@router.get("/runs")
def runs(limit: int = Query(default=200, ge=1, le=500)) -> dict[str, Any]:
    return _safe("hermes:kanban:runs", lambda: kanban.list_runs(limit))


@router.get("/runs/{run_id}")
def run(run_id: int) -> dict[str, Any]:
    value = kanban.get_run(run_id)
    if value is None:
        raise HTTPException(status_code=404, detail="run not found")
    value["observability"] = _safe(
        "phoenix:run",
        lambda: phoenix_client.traces_for_run(str(run_id)),
    )
    return redact(value)


@router.get("/agents")
def agents() -> dict[str, Any]:
    return {
        "profiles": _safe("hermes:profiles", profiles.list_profiles),
        "workers": _safe("hermes:workers", workers.list_workers),
    }


@router.get("/plugins")
def plugin_inventory() -> dict[str, Any]:
    return _safe("hermes:plugins", plugins.list_plugins)


@router.get("/github")
def github_view() -> dict[str, Any]:
    configured = load_repositories()
    slugs = [str(item["github"]) for item in configured if item.get("github")]
    return {
        "local_git": _safe("git:local", all_repository_statuses),
        "github_api": redact(github_status(slugs).to_dict()),
        "mutation": "disabled",
    }


@router.get("/workspaces")
def workspace_inventory() -> dict[str, Any]:
    return _safe("hermes:workspaces", workspaces.list_workspaces)


@router.get("/observability")
def observability() -> dict[str, Any]:
    return redact(observability_health.snapshot())


@router.get("/observability/health")
def observability_health_view() -> dict[str, Any]:
    return observability()


@router.get("/observability/traces")
def observability_traces(limit: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
    return _safe("phoenix:traces", lambda: phoenix_client.summarize_traces(limit))


@router.get("/observability/tasks/{task_id}")
def observability_task(task_id: str) -> dict[str, Any]:
    return _safe(
        "phoenix:task",
        lambda: {
            "hermes_kanban_task_id": task_id,
            "traces": phoenix_client.traces_for_task(task_id),
        },
    )


@router.get("/observability/runs/{run_id}")
def observability_run(run_id: str) -> dict[str, Any]:
    return _safe(
        "phoenix:run",
        lambda: {
            "hermes_kanban_run_id": run_id,
            "traces": phoenix_client.traces_for_run(run_id),
        },
    )

