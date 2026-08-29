"""External LLM execution requires an explicit authorization artifact."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def authorization_path() -> Path:
    override = os.environ.get("EOS_EXPERIMENT_RUNTIME")
    base = Path(override) if override else ROOT / ".runtime" / "experiments"
    return base / "LLM_BUDGET_AUTHORIZATION"


def budget_authorization_status() -> dict[str, Any]:
    path = authorization_path()
    if path.is_file():
        return {
            "status": "AUTHORIZED",
            "path": str(path),
            "reason": "authorization artifact present",
        }
    return {
        "status": "READY_FOR_LLM_BUDGET_AUTHORIZATION",
        "authorized": False,
        "reason": "LLM_BUDGET_AUTHORIZATION_REQUIRED",
        "default": "NONE",
    }


def require_budget_authorization() -> dict[str, Any]:
    status = budget_authorization_status()
    if status.get("status") != "AUTHORIZED":
        return {
            "ok": False,
            "executed": False,
            "status": "READY_FOR_LLM_BUDGET_AUTHORIZATION",
            "reason": "unauthorized experiment blocked",
        }
    return {"ok": True, "status": "AUTHORIZED"}
