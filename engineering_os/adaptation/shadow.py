"""Shadow engine: would-select only. Never mutates Hermes or Kanban."""

from __future__ import annotations

import time
from typing import Any

from engineering_os.adaptation.resolver import resolve_policy
from engineering_os.experiments.config_snapshot import sha256_text


def shadow_decide(task_context: dict[str, Any], state: dict[str, Any] | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    decision = resolve_policy(task_context, state)
    would = "CANDIDATE" if decision.get("result") == "CANDIDATE" else decision.get("result") or "BASELINE"
    actual = task_context.get("actual_config_hash") or task_context.get("baseline_config_hash")
    return {
        "status": "success",
        "mutated": False,
        "actuate": False,
        "task_id": task_context.get("task_id"),
        "board": task_context.get("board"),
        "result": would,
        "resolution": "BASELINE",
        "would_config_hash": decision.get("config_hash"),
        "actual_config_hash": actual,
        "policy_id": decision.get("policy_id"),
        "policy_hash": decision.get("policy_hash"),
        "match_reason": decision.get("reason"),
        "conflict": bool(decision.get("conflict")),
        "latency_ms": decision.get("latency_ms") or ((time.perf_counter() - started) * 1000.0),
        "context": task_context,
        "efficacy_claim": False,
    }


def shadow_batch(contexts: list[dict[str, Any]], state: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = [shadow_decide(ctx, state) for ctx in contexts]
    would_change = sum(1 for row in rows if row["result"] == "CANDIDATE")
    conflicts = sum(1 for row in rows if row["conflict"])
    latencies = [float(row["latency_ms"] or 0) for row in rows]
    return {
        "status": "success",
        "n": len(rows),
        "would_change": would_change,
        "conflicts": conflicts,
        "not_eligible": sum(1 for row in rows if row["result"] == "NOT_ELIGIBLE"),
        "baseline": sum(1 for row in rows if row["result"] == "BASELINE"),
        "mean_latency_ms": (sum(latencies) / len(latencies)) if latencies else 0.0,
        "max_latency_ms": max(latencies) if latencies else 0.0,
        "mutated": False,
        "decisions": rows,
        "batch_hash": sha256_text(str([(r["task_id"], r["result"], r["policy_hash"]) for r in rows])),
    }


def production_task_context(task: dict[str, Any], board: str) -> dict[str, Any]:
    return {
        "task_id": task.get("id"),
        "board": board,
        "profile": task.get("assignee") or task.get("profile"),
        "task_label": task.get("labels") or [],
        "task_class": "production_kanban",
        "environment": "production",
        "scope": "PRODUCTION_SHADOW",
        "repository_id": task.get("repo") or task.get("repository_id"),
        "actual_config_hash": None,
        "model_override": task.get("model_override"),
        "skills": task.get("skills"),
        "status": task.get("status"),
    }
