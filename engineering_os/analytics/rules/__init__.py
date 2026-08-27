"""Deterministic phase3-v1 outcome rules. Pure functions; no I/O."""

from __future__ import annotations

from typing import Any

from engineering_os.analytics import RULESET_VERSION
from engineering_os.analytics.scope import cohort_for, is_production

FAILURE_OUTCOMES = frozenset(
    {"crashed", "timed_out", "failed", "spawn_failed", "gave_up"}
)
SUCCESS_OUTCOMES = frozenset({"completed"})
HUMAN_EVENT_KINDS = frozenset(
    {
        "commented",
        "status",
        "edited",
        "promoted_manual",
        "unblocked",
        "archived",
        "review_reopened",
        "model_override_set",
        "assigned",
    }
)
REWORK_EVENT_KINDS = frozenset(
    {"review_reopened", "descendant_invalidated", "changes_requested"}
)


def is_qualifying_run(run: dict[str, Any], events: list[dict[str, Any]]) -> bool:
    run_id = run.get("id")
    started = run.get("started_at")
    ended = run.get("ended_at")
    if started is not None and ended is not None and started == ended:
        return False
    if started is not None and ended is not None and started != ended:
        return True
    if run.get("worker_pid"):
        return True
    return any(
        event.get("kind") == "spawned" and event.get("run_id") == run_id
        for event in events
    )


def is_synthetic_run(run: dict[str, Any]) -> bool:
    started = run.get("started_at")
    ended = run.get("ended_at")
    return started is not None and ended is not None and started == ended


def ordered_runs(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        runs,
        key=lambda item: (
            item.get("started_at") is None,
            item.get("started_at") or 0,
            item.get("id") or 0,
        ),
    )


def run_is_success(run: dict[str, Any]) -> bool:
    outcome = str(run.get("outcome") or "")
    status = str(run.get("status") or "")
    if outcome in SUCCESS_OUTCOMES:
        return True
    return status == "done" and outcome in {"", "completed"}


def run_is_failure(run: dict[str, Any]) -> bool:
    return str(run.get("outcome") or "") in FAILURE_OUTCOMES


def _unix_delta(start: Any, end: Any) -> float | None:
    try:
        if start is None or end is None:
            return None
        value = float(end) - float(start)
    except (TypeError, ValueError):
        return None
    return value


def _typed_verifier(runs: list[dict[str, Any]]) -> str | None:
    for run in reversed(ordered_runs(runs)):
        metadata = run.get("metadata")
        if isinstance(metadata, dict):
            value = metadata.get("objective_result")
            if value in {"PASS", "FAIL"}:
                return str(value)
    return None


def _github_verification(github: dict[str, Any]) -> tuple[str, str]:
    state = str(github.get("evidence_state") or github.get("status") or "UNKNOWN")
    if state == "BLOCKED_AUTH":
        return "UNKNOWN", "BLOCKED_AUTH"
    if state == "NOT_APPLICABLE":
        return "NOT_APPLICABLE", "NOT_APPLICABLE"
    if state == "AVAILABLE":
        conclusion = str(github.get("ci_conclusion") or "").lower()
        if conclusion == "success":
            return "PASS", "AVAILABLE"
        if conclusion in {"failure", "cancelled", "timed_out"}:
            return "FAIL", "AVAILABLE"
        return "UNKNOWN", "AVAILABLE"
    if state == "NOT_FOUND":
        return "UNKNOWN", "NOT_FOUND"
    return "UNKNOWN", state or "UNKNOWN"


def _lifecycle(task: dict[str, Any] | None) -> str:
    if not task:
        return "UNKNOWN"
    status = str(task.get("status") or "")
    if status in {"done", "archived"}:
        return "DONE"
    return "NOT_DONE"


def _human(events: list[dict[str, Any]] | None, comments: list[dict[str, Any]] | None) -> str:
    if events is None and comments is None:
        return "UNKNOWN"
    for event in events or []:
        kind = str(event.get("kind") or "")
        if kind in HUMAN_EVENT_KINDS:
            if kind == "assigned":
                payload = event.get("payload") or {}
                source = ""
                if isinstance(payload, dict):
                    source = str(payload.get("source") or "")
                if source in {"auto", "kanban.default_assignee"}:
                    continue
            return "DETECTED"
    if comments:
        return "DETECTED"
    return "UNKNOWN"


def _rework(
    task: dict[str, Any],
    runs: list[dict[str, Any]],
    events: list[dict[str, Any]] | None,
) -> tuple[str, int | None]:
    if events is None:
        return "UNKNOWN", None
    count = 0
    completed = task.get("completed_at")
    previous_status = None
    for event in sorted(events, key=lambda item: item.get("id") or 0):
        kind = str(event.get("kind") or "")
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        if kind in REWORK_EVENT_KINDS:
            count += 1
            continue
        if kind == "status":
            requested = str(payload.get("requested_status") or payload.get("status") or "")
            if previous_status in {"done", "archived"} and requested not in {
                "done",
                "archived",
                "",
            }:
                count += 1
            if requested:
                previous_status = requested
    if completed:
        for run in runs:
            started = run.get("started_at")
            if started is not None and started > completed and is_qualifying_run(run, events):
                count += 1
    return ("DETECTED" if count else "NOT_DETECTED"), count


def _first_pass(qualifying: list[dict[str, Any]]) -> str:
    if not qualifying:
        return "NOT_APPLICABLE"
    first = qualifying[0]
    if run_is_success(first):
        return "PASS"
    if run_is_failure(first):
        return "FAIL"
    return "UNKNOWN"


def _retry_count(qualifying: list[dict[str, Any]]) -> int | None:
    if not qualifying:
        return 0
    failures = 0
    for run in qualifying:
        if run_is_success(run):
            return failures
        if run_is_failure(run):
            failures += 1
        else:
            return None
    return failures


def _evidence_grade(bundle: dict[str, Any]) -> str:
    task = bundle.get("task")
    traces = bundle.get("traces") or []
    qualifying = bundle.get("qualifying_runs") or []
    if task and qualifying and traces:
        return "HIGH"
    if task and qualifying:
        return "MEDIUM"
    if task:
        return "LOW"
    return "NONE"


def derive_outcome(bundle: dict[str, Any], scope: dict[str, Any]) -> dict[str, Any]:
    task = bundle.get("task")
    runs = list(bundle.get("runs") or [])
    events = bundle.get("events")
    comments = bundle.get("comments")
    traces = list(bundle.get("traces") or [])
    git = dict(bundle.get("git") or {})
    github = dict(bundle.get("github") or {})
    events_list = list(events or [])
    qualifying = [
        run for run in ordered_runs(runs) if is_qualifying_run(run, events_list)
    ]
    lifecycle = _lifecycle(task)
    typed = _typed_verifier(runs)
    github_verification, github_state = _github_verification(github)
    if typed == "PASS":
        verification = "PASS"
    elif typed == "FAIL":
        verification = "FAIL"
    else:
        verification = github_verification
        if github_state == "NOT_APPLICABLE" and typed is None:
            verification = "NOT_APPLICABLE"

    if lifecycle == "UNKNOWN":
        final_outcome = "UNKNOWN"
    elif verification == "FAIL":
        final_outcome = "VERIFIED_FAILURE"
    elif lifecycle == "DONE" and verification == "PASS":
        final_outcome = "VERIFIED_SUCCESS"
    elif lifecycle == "DONE":
        final_outcome = "COMPLETED_UNVERIFIED"
    else:
        final_outcome = "INCOMPLETE"

    first_pass = _first_pass(qualifying)
    retry_count = _retry_count(qualifying)
    rework_status, rework_count = _rework(task or {}, qualifying, events)
    human = _human(events, comments)

    task_wall = _unix_delta(
        (task or {}).get("started_at"), (task or {}).get("completed_at")
    )
    run_walls = [
        _unix_delta(run.get("started_at"), run.get("ended_at")) for run in qualifying
    ]
    run_wall = (
        sum(value for value in run_walls if value is not None) if run_walls else None
    )
    if run_walls and all(value is None for value in run_walls):
        run_wall = None

    llm_calls = sum(int(trace.get("llm_calls") or 0) for trace in traces) if traces else None
    tool_calls = sum(int(trace.get("tool_calls") or 0) for trace in traces) if traces else None
    error_count = sum(int(trace.get("error_count") or 0) for trace in traces) if traces else None
    trace_wall = max(
        (trace.get("trace_wall_seconds") for trace in traces if trace.get("trace_wall_seconds") is not None),
        default=None,
    )
    llm_seconds = sum(
        float(trace.get("llm_total_seconds") or 0) for trace in traces
    ) if traces else None
    tool_seconds = sum(
        float(trace.get("tool_total_seconds") or 0) for trace in traces
    ) if traces else None

    models = bundle.get("models") or []
    skills = bundle.get("skills") or []
    git_state = str(git.get("evidence_quality") or git.get("status") or "UNKNOWN")
    cost_status = "UNKNOWN"
    skill_status = "AVAILABLE" if skills else "UNKNOWN"
    model_status = "AVAILABLE" if models else "UNKNOWN"

    cohort = cohort_for(task or {}, scope) if task else "excluded"
    production = bool(task) and is_production(task, scope)

    reasons = []
    if lifecycle == "DONE":
        reasons.append("Kanban lifecycle is DONE")
    elif lifecycle == "NOT_DONE":
        reasons.append(f"Kanban lifecycle is {task.get('status') if task else 'unread'}")
    else:
        reasons.append("Kanban task was not readable")
    if verification == "PASS":
        reasons.append("typed or GitHub verification PASS")
    elif verification == "FAIL":
        reasons.append("typed or GitHub verification FAIL")
    elif github_state == "BLOCKED_AUTH":
        reasons.append("GitHub API is BLOCKED_AUTH and no typed objective verifier was available")
    elif verification == "NOT_APPLICABLE":
        reasons.append("GitHub is not applicable and no typed verifier was available")
    else:
        reasons.append("no objective verifier evidence")

    evidence = {
        "task_id": (task or {}).get("id"),
        "board": (task or {}).get("board"),
        "runs": [run.get("id") for run in qualifying],
        "trace_ids": [trace.get("trace_id") for trace in traces],
        "commit_sha": git.get("commit_sha"),
        "github_state": github_state,
        "ruleset": RULESET_VERSION,
    }

    return {
        "ruleset_version": RULESET_VERSION,
        "lifecycle_state": lifecycle,
        "verification_state": verification,
        "final_outcome": final_outcome,
        "first_pass_state": first_pass,
        "retry_count": retry_count,
        "rework_status": rework_status,
        "rework_count": rework_count,
        "human_intervention_state": human,
        "task_wall_seconds": task_wall,
        "run_wall_seconds": run_wall,
        "trace_wall_seconds": trace_wall,
        "llm_total_seconds": llm_seconds,
        "tool_total_seconds": tool_seconds,
        "llm_call_count": llm_calls,
        "tool_call_count": tool_calls,
        "error_count": error_count,
        "github_evidence_state": github_state,
        "git_evidence_state": git_state,
        "cost_status": cost_status,
        "skill_usage_status": skill_status,
        "model_usage_status": model_status,
        "production_cohort": production,
        "cohort": cohort,
        "evidence_grade": _evidence_grade(
            {**bundle, "qualifying_runs": qualifying, "traces": traces}
        ),
        "reason": "; ".join(reasons) + ".",
        "evidence": evidence,
        "qualifying_run_ids": [run.get("id") for run in qualifying],
    }
