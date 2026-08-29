"""Real Hermes inference gate. Default: do not execute paid/provider calls."""

from __future__ import annotations

from typing import Any

from engineering_os.experiments.budget_gate import require_budget_authorization


def run_real_unit(_assignment: dict[str, Any], _protocol: dict[str, Any]) -> dict[str, Any]:
    gate = require_budget_authorization()
    if not gate.get("ok"):
        return {
            "executed": False,
            "llm_calls": 0,
            "status": gate.get("status"),
            "reason": gate.get("reason"),
        }
    raise RuntimeError("authorized real runner is not wired in this PAR goal")
