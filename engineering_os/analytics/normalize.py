"""Normalize adapter bundles into fact dicts. No source mutation. No prompt bodies."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from engineering_os.analytics.rules import is_qualifying_run, is_synthetic_run
from engineering_os.analytics.scope import cohort_for
from engineering_os.analytics import RULESET_VERSION


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def strip_task(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": task.get("id"),
        "board": task.get("board"),
        "title": task.get("title"),
        "status": task.get("status"),
        "assignee": task.get("assignee"),
        "created_at": task.get("created_at"),
        "started_at": task.get("started_at"),
        "completed_at": task.get("completed_at"),
        "workspace_path": task.get("workspace_path"),
        "branch_name": task.get("branch_name"),
        "current_run_id": task.get("current_run_id"),
    }


def strip_run(run: dict[str, Any]) -> dict[str, Any]:
    metadata = run.get("metadata")
    typed = None
    if isinstance(metadata, dict) and metadata.get("objective_result") in {"PASS", "FAIL"}:
        typed = metadata.get("objective_result")
    return {
        "id": run.get("id"),
        "task_id": run.get("task_id"),
        "profile": run.get("profile"),
        "status": run.get("status"),
        "outcome": run.get("outcome"),
        "started_at": run.get("started_at"),
        "ended_at": run.get("ended_at"),
        "worker_pid": run.get("worker_pid"),
        "metadata": {"objective_result": typed} if typed else None,
    }


def strip_event(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    allowed = {}
    for key in ("status", "requested_status", "source", "actor"):
        if key in payload:
            allowed[key] = payload[key]
    return {
        "id": event.get("id"),
        "run_id": event.get("run_id"),
        "kind": event.get("kind"),
        "payload": allowed,
        "created_at": event.get("created_at"),
    }


def collect_models(traces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for trace in traces:
        run_id = trace.get("hermes_kanban_run_id")
        items = trace.get("models") or []
        if items:
            for item in items:
                rows.append(
                    {
                        "run_id": run_id,
                        "model": item.get("model"),
                        "provider": item.get("provider") or "",
                        "source": "trace",
                        "call_count": 1,
                    }
                )
        elif trace.get("model"):
            rows.append(
                {
                    "run_id": run_id,
                    "model": trace.get("model"),
                    "provider": trace.get("provider") or "",
                    "source": "trace",
                    "call_count": int(trace.get("llm_calls") or 1),
                }
            )
    return rows


def collect_skills(traces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for trace in traces:
        run_id = trace.get("hermes_kanban_run_id")
        for skill in trace.get("skills") or []:
            rows.append(
                {
                    "run_id": run_id,
                    "skill_name": skill,
                    "source": "span",
                    "call_count": 1,
                }
            )
    return rows


def normalize_bundle(raw: dict[str, Any], scope: dict[str, Any]) -> dict[str, Any]:
    task = strip_task(raw["task"]) if raw.get("task") else None
    if task:
        task["board"] = raw.get("board") or task.get("board")
        task["cohort"] = cohort_for(task, scope)
        task["ruleset_version"] = RULESET_VERSION
    events = [strip_event(event) for event in raw.get("events") or []]
    runs = [strip_run(run) for run in raw.get("runs") or []]
    for run in runs:
        run["qualifying"] = is_qualifying_run(run, events)
        run["synthetic"] = is_synthetic_run(run)
    traces = list(raw.get("traces") or [])
    models = collect_models(traces)
    skills = collect_skills(traces)
    comments = [
        {"id": item.get("id"), "author": item.get("author"), "created_at": item.get("created_at")}
        for item in raw.get("comments") or []
    ]
    git = dict(raw.get("git") or {})
    github = dict(raw.get("github") or {})
    return {
        "task": task,
        "runs": runs,
        "events": events if raw.get("events") is not None else None,
        "comments": comments if raw.get("comments") is not None else None,
        "traces": traces,
        "git": git,
        "github": github,
        "models": models,
        "skills": skills,
        "partial_source_failures": list(raw.get("partial_source_failures") or []),
        "source_hash": canonical_hash(
            {
                "task": task,
                "runs": runs,
                "events": events,
                "traces": [
                    {
                        "trace_id": item.get("trace_id"),
                        "llm_calls": item.get("llm_calls"),
                        "tool_calls": item.get("tool_calls"),
                    }
                    for item in traces
                ],
                "git": git,
                "github": github,
            }
        ),
    }
