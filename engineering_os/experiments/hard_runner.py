"""Sequential isolated real-model runner. Enforces HARD unit/invocation/wall caps."""

from __future__ import annotations

import time
from typing import Any

from engineering_os.experiments.budget_gate import require_budget_authorization
from engineering_os.experiments.budget_limits import per_unit_wall_seconds, total_wall_seconds
from engineering_os.experiments.hermes_runner import execute_authorized_unit


def run_authorized_sequence(
    assignments: list[dict[str, Any]],
    protocol: dict[str, Any],
) -> dict[str, Any]:
    gate = require_budget_authorization(protocol)
    if not gate.get("ok"):
        return {
            "ok": False,
            "executed": False,
            "status": gate.get("status"),
            "reason": gate.get("reason"),
            "results": [],
        }
    max_units = int(gate.get("max_units") or 0)
    max_calls = int(gate.get("max_llm_calls") or 0)
    wall_total = total_wall_seconds(protocol)
    started = time.monotonic()
    results: list[dict[str, Any]] = []
    invocations = 0
    for index, assignment in enumerate(assignments):
        if index >= max_units:
            return {
                "ok": True,
                "status": "HARD_STOP_UNITS",
                "results": results,
                "units": len(results),
                "invocations": invocations,
            }
        if invocations >= max_calls:
            return {
                "ok": True,
                "status": "HARD_STOP_INVOCATIONS",
                "results": results,
                "units": len(results),
                "invocations": invocations,
            }
        elapsed = time.monotonic() - started
        if wall_total and elapsed >= wall_total:
            return {
                "ok": True,
                "status": "HARD_STOP_WALL_TOTAL",
                "results": results,
                "units": len(results),
                "invocations": invocations,
                "elapsed_seconds": elapsed,
            }
        remaining_total = max(1, int(wall_total - elapsed)) if wall_total else per_unit_wall_seconds(protocol)
        remaining_gate = dict(gate)
        remaining_gate["max_llm_calls"] = max_calls - invocations
        remaining_gate["remaining_wall_seconds"] = remaining_total
        result = execute_authorized_unit(assignment, protocol, remaining_gate)
        results.append(result)
        if result.get("executed"):
            invocations += int(result.get("llm_calls") or 1)
    return {
        "ok": True,
        "status": "COMPLETE",
        "results": results,
        "units": len(results),
        "invocations": invocations,
        "elapsed_seconds": time.monotonic() - started,
    }
