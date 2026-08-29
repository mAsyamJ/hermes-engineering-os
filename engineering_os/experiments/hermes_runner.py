"""Real Hermes inference gate. Default: do not execute paid/provider calls."""

from __future__ import annotations

from typing import Any

from engineering_os.experiments.budget_gate import require_budget_authorization


def run_real_unit(assignment: dict[str, Any], protocol: dict[str, Any]) -> dict[str, Any]:
    gate = require_budget_authorization(protocol)
    if not gate.get("ok"):
        return {
            "executed": False,
            "llm_calls": 0,
            "status": gate.get("status"),
            "reason": gate.get("reason"),
        }
    return execute_authorized_unit(assignment, protocol, gate)


def execute_authorized_unit(
    assignment: dict[str, Any],
    protocol: dict[str, Any],
    gate: dict[str, Any],
) -> dict[str, Any]:
    """Isolated BENCHMARK execution. Unreachable unless a valid human artifact exists."""
    remaining = int(gate.get("max_llm_calls") or 0)
    if remaining <= 0:
        return {
            "executed": False,
            "llm_calls": 0,
            "status": "BLOCKED_BUDGET",
            "reason": "authorization max_llm_calls exhausted",
        }
    from engineering_os.experiments.real_executor import run_isolated_real_unit

    return run_isolated_real_unit(assignment, protocol, gate)
