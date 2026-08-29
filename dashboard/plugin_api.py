"""Authenticated, GET-only dashboard routes for Hermes Engineering OS."""

from __future__ import annotations

from pathlib import Path
import json
import sys
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

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


ANALYTICS_BASE = "http://127.0.0.1:9120"


def _analytics_proxy(path: str) -> dict[str, Any]:
    request = Request(ANALYTICS_BASE + path, method="GET")
    try:
        with urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode())
        if isinstance(payload, dict):
            return payload
        return {"status": "AVAILABLE", "data": payload}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"body": body[:500]}
        if exc.code == 404:
            raise HTTPException(status_code=404, detail="analytics resource not found") from exc
        return {
            "status": "DEGRADED",
            "source": "analytics:sidecar",
            "detail": f"HTTP {exc.code}",
            "data": parsed,
        }
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return {
            "status": "DEGRADED",
            "source": "analytics:sidecar",
            "mode": "read-only",
            "detail": f"{type(exc).__name__}: {exc}",
        }


@router.get("/analytics")
def analytics() -> dict[str, Any]:
    return redact(_analytics_proxy("/summary"))


@router.get("/analytics/health")
def analytics_health() -> dict[str, Any]:
    return redact(_analytics_proxy("/health"))


@router.get("/analytics/coverage")
def analytics_coverage() -> dict[str, Any]:
    return redact(_analytics_proxy("/coverage"))


@router.get("/analytics/summary")
def analytics_summary() -> dict[str, Any]:
    return redact(_analytics_proxy("/summary"))


@router.get("/analytics/tasks")
def analytics_tasks(limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0)) -> dict[str, Any]:
    return redact(_analytics_proxy(f"/tasks?limit={limit}&offset={offset}"))


@router.get("/analytics/tasks/{task_id}")
def analytics_task(task_id: str, board: str = Query(default="retropick-markets-release")) -> dict[str, Any]:
    return redact(_analytics_proxy(f"/tasks/{task_id}?board={board}"))


@router.get("/analytics/runs/{run_id}")
def analytics_run(run_id: int, board: str = Query(default="retropick-markets-release")) -> dict[str, Any]:
    return redact(_analytics_proxy(f"/runs/{run_id}?board={board}"))


@router.get("/analytics/materialization")
def analytics_materialization() -> dict[str, Any]:
    return redact(_analytics_proxy("/materialization"))


@router.get("/evaluations")
def evaluations() -> dict[str, Any]:
    return redact(_analytics_proxy("/evaluations"))


@router.get("/evaluations/health")
def evaluations_health() -> dict[str, Any]:
    return redact(_analytics_proxy("/evaluations/health"))


@router.get("/evaluations/coverage")
def evaluations_coverage() -> dict[str, Any]:
    return redact(_analytics_proxy("/evaluations/coverage"))


@router.get("/evaluations/recent")
def evaluations_recent() -> dict[str, Any]:
    return redact(_analytics_proxy("/evaluations/recent"))


@router.get("/evaluations/profiles")
def evaluations_profiles() -> dict[str, Any]:
    return redact(_analytics_proxy("/evaluations/profiles"))


@router.get("/evaluations/evaluators")
def evaluations_evaluators() -> dict[str, Any]:
    return redact(_analytics_proxy("/evaluations/evaluators"))


@router.get("/evaluations/tasks/{task_id}")
def evaluations_task(task_id: str, board: str = Query(default="retropick-markets-release")) -> dict[str, Any]:
    return redact(_analytics_proxy(f"/evaluations/tasks/{task_id}?board={board}"))


@router.get("/evaluations/runs/{evaluation_run_id}")
def evaluations_run(evaluation_run_id: str) -> dict[str, Any]:
    return redact(_analytics_proxy(f"/evaluations/runs/{evaluation_run_id}"))


@router.get("/evaluations/artifacts/{artifact_id}")
def evaluations_artifact(artifact_id: str) -> dict[str, Any]:
    return redact(_analytics_proxy(f"/evaluations/artifacts/{artifact_id}"))


@router.get("/performance")
def performance() -> dict[str, Any]:
    return redact(_analytics_proxy("/performance/summary"))


@router.get("/performance/health")
def performance_health() -> dict[str, Any]:
    return redact(_analytics_proxy("/performance/health"))


@router.get("/performance/coverage")
def performance_coverage() -> dict[str, Any]:
    return redact(_analytics_proxy("/performance/coverage"))


@router.get("/performance/summary")
def performance_summary() -> dict[str, Any]:
    return redact(_analytics_proxy("/performance/summary"))


@router.get("/performance/cohorts")
def performance_cohorts() -> dict[str, Any]:
    return redact(_analytics_proxy("/performance/cohorts"))


@router.get("/performance/metrics")
def performance_metrics(limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0)) -> dict[str, Any]:
    return redact(_analytics_proxy(f"/performance/metrics?limit={limit}&offset={offset}"))


@router.get("/performance/models")
def performance_models() -> dict[str, Any]:
    return redact(_analytics_proxy("/performance/models"))


@router.get("/performance/profiles")
def performance_profiles() -> dict[str, Any]:
    return redact(_analytics_proxy("/performance/profiles"))


@router.get("/performance/skills")
def performance_skills() -> dict[str, Any]:
    return redact(_analytics_proxy("/performance/skills"))


@router.get("/performance/failures")
def performance_failures() -> dict[str, Any]:
    return redact(_analytics_proxy("/performance/failures"))


@router.get("/performance/trends")
def performance_trends() -> dict[str, Any]:
    return redact(_analytics_proxy("/performance/trends"))


@router.get("/performance/comparisons")
def performance_comparisons() -> dict[str, Any]:
    return redact(_analytics_proxy("/performance/comparisons"))


@router.get("/performance/insights")
def performance_insights() -> dict[str, Any]:
    return redact(_analytics_proxy("/performance/insights"))


@router.get("/performance/why")
def performance_why(
    metric: str = Query(default="lifecycle_completion_rate"),
    cohort: str = Query(default="production_all"),
    dimension_type: str = Query(default="cohort"),
    dimension_value: str | None = Query(default=None),
) -> dict[str, Any]:
    query = f"/performance/why?metric={metric}&cohort={cohort}&dimension_type={dimension_type}"
    if dimension_value:
        query += f"&dimension_value={dimension_value}"
    return redact(_analytics_proxy(query))


@router.get("/performance/tasks/{task_id}")
def performance_task(task_id: str, board: str = Query(default="retropick-markets-release")) -> dict[str, Any]:
    return redact(_analytics_proxy(f"/performance/tasks/{task_id}?board={board}"))


@router.get("/experiments")
def experiments() -> dict[str, Any]:
    return redact(_analytics_proxy("/experiments"))


@router.get("/experiments/health")
def experiments_health() -> dict[str, Any]:
    return redact(_analytics_proxy("/experiments/health"))


@router.get("/experiments/{experiment_id}")
def experiment_detail(experiment_id: str) -> dict[str, Any]:
    return redact(_analytics_proxy(f"/experiments/{experiment_id}/explain"))


@router.get("/experiments/{experiment_id}/protocol")
def experiment_protocol(experiment_id: str) -> dict[str, Any]:
    return redact(_analytics_proxy(f"/experiments/{experiment_id}/protocol"))


@router.get("/experiments/{experiment_id}/variants")
def experiment_variants(experiment_id: str) -> dict[str, Any]:
    return redact(_analytics_proxy(f"/experiments/{experiment_id}/variants"))


@router.get("/experiments/{experiment_id}/assignments")
def experiment_assignments(experiment_id: str) -> dict[str, Any]:
    return redact(_analytics_proxy(f"/experiments/{experiment_id}/assignments"))


@router.get("/experiments/{experiment_id}/exposures")
def experiment_exposures(experiment_id: str) -> dict[str, Any]:
    return redact(_analytics_proxy(f"/experiments/{experiment_id}/exposures"))


@router.get("/experiments/{experiment_id}/progress")
def experiment_progress(experiment_id: str) -> dict[str, Any]:
    return redact(_analytics_proxy(f"/experiments/{experiment_id}/progress"))


@router.get("/experiments/{experiment_id}/analysis")
def experiment_analysis(experiment_id: str) -> dict[str, Any]:
    return redact(_analytics_proxy(f"/experiments/{experiment_id}/analysis"))


@router.get("/experiments/{experiment_id}/guardrails")
def experiment_guardrails(experiment_id: str) -> dict[str, Any]:
    return redact(_analytics_proxy(f"/experiments/{experiment_id}/guardrails"))


@router.get("/experiments/{experiment_id}/explain")
def experiment_explain(experiment_id: str) -> dict[str, Any]:
    return redact(_analytics_proxy(f"/experiments/{experiment_id}/explain"))


@router.get("/adaptation")
def adaptation() -> dict[str, Any]:
    return redact(_analytics_proxy("/adaptation"))


@router.get("/adaptation/health")
def adaptation_health() -> dict[str, Any]:
    return redact(_analytics_proxy("/adaptation/health"))


@router.get("/adaptation/readiness")
def adaptation_readiness() -> dict[str, Any]:
    return redact(_analytics_proxy("/adaptation/readiness"))


@router.get("/adaptation/readiness/authority")
def adaptation_readiness_authority() -> dict[str, Any]:
    return redact(_analytics_proxy("/adaptation/readiness/authority"))


@router.get("/adaptation/readiness/runtime")
def adaptation_readiness_runtime() -> dict[str, Any]:
    return redact(_analytics_proxy("/adaptation/readiness/runtime"))


@router.get("/adaptation/readiness/memory")
def adaptation_readiness_memory() -> dict[str, Any]:
    return redact(_analytics_proxy("/adaptation/readiness/memory"))


@router.get("/adaptation/readiness/evidence")
def adaptation_readiness_evidence() -> dict[str, Any]:
    return redact(_analytics_proxy("/adaptation/readiness/evidence"))


@router.get("/adaptation/readiness/pag2")
def adaptation_readiness_pag2() -> dict[str, Any]:
    return redact(_analytics_proxy("/adaptation/readiness/pag2"))


@router.get("/adaptation/readiness/experiment")
def adaptation_readiness_experiment() -> dict[str, Any]:
    return redact(_analytics_proxy("/adaptation/readiness/experiment"))


@router.get("/adaptation/readiness/upstream")
def adaptation_readiness_upstream() -> dict[str, Any]:
    return redact(_analytics_proxy("/adaptation/readiness/upstream"))


@router.get("/adaptation/recommendations")
def adaptation_recommendations() -> dict[str, Any]:
    return redact(_analytics_proxy("/adaptation/recommendations"))


@router.get("/adaptation/recommendations/{recommendation_id}")
def adaptation_recommendation(recommendation_id: str) -> dict[str, Any]:
    return redact(_analytics_proxy(f"/adaptation/recommendations/{recommendation_id}"))


@router.get("/adaptation/policies")
def adaptation_policies() -> dict[str, Any]:
    return redact(_analytics_proxy("/adaptation/policies"))


@router.get("/adaptation/policies/{policy_id}")
def adaptation_policy(policy_id: str) -> dict[str, Any]:
    return redact(_analytics_proxy(f"/adaptation/policies/{policy_id}"))


@router.get("/adaptation/shadow")
def adaptation_shadow() -> dict[str, Any]:
    return redact(_analytics_proxy("/adaptation/shadow"))


@router.get("/adaptation/canaries")
def adaptation_canaries() -> dict[str, Any]:
    return redact(_analytics_proxy("/adaptation/canaries"))


@router.get("/adaptation/guardrails")
def adaptation_guardrails() -> dict[str, Any]:
    return redact(_analytics_proxy("/adaptation/guardrails"))


@router.get("/adaptation/rollbacks")
def adaptation_rollbacks() -> dict[str, Any]:
    return redact(_analytics_proxy("/adaptation/rollbacks"))


@router.get("/adaptation/audit")
def adaptation_audit() -> dict[str, Any]:
    return redact(_analytics_proxy("/adaptation/audit"))


@router.get("/adaptation/explain/{object_id}")
def adaptation_explain(object_id: str) -> dict[str, Any]:
    return redact(_analytics_proxy(f"/adaptation/explain/{object_id}"))


