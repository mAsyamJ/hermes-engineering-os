"""External LLM execution requires an explicit bound authorization artifact."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_FIELDS = (
    "protocol_id",
    "protocol_hash",
    "max_units",
    "max_llm_calls",
    "control_model",
    "candidate_model",
    "scope",
    "expiry",
)
ALLOWED_SCOPES = {"BENCHMARK", "NON_PRODUCTION"}
FORBIDDEN_CREATORS = ("pag1", "pag-1", "automation", "engineering-os")


def authorization_path() -> Path:
    override = os.environ.get("EOS_EXPERIMENT_RUNTIME")
    base = Path(override) if override else ROOT / ".runtime" / "experiments"
    return base / "LLM_BUDGET_AUTHORIZATION"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_expiry(value: str) -> datetime | None:
    try:
        when = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when


def load_authorization_artifact() -> dict[str, Any]:
    path = authorization_path()
    if not path.is_file():
        return {
            "ok": False,
            "present": False,
            "status": "READY_FOR_BUDGET_AUTHORIZATION",
            "reason": "LLM_BUDGET_AUTHORIZATION_REQUIRED",
            "default": "NONE",
        }
    raw = path.read_text(encoding="utf-8").strip()
    if raw.lower() in {"yes", "y", "true", "authorize", "ok"}:
        return {
            "ok": False,
            "present": True,
            "status": "INVALID",
            "reason": "generic yes is not a bound authorization",
        }
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "ok": False,
            "present": True,
            "status": "INVALID",
            "reason": "authorization artifact is not JSON",
        }
    if not isinstance(data, dict):
        return {"ok": False, "present": True, "status": "INVALID", "reason": "authorization artifact must be an object"}
    missing = [key for key in REQUIRED_FIELDS if key not in data]
    if missing:
        return {
            "ok": False,
            "present": True,
            "status": "INVALID",
            "reason": f"authorization missing fields: {missing}",
        }
    creator = str(data.get("created_by") or "").lower()
    if any(token in creator for token in FORBIDDEN_CREATORS):
        return {
            "ok": False,
            "present": True,
            "status": "INVALID",
            "reason": "PAG-1 automation cannot authorize LLM budget",
        }
    if str(data.get("scope")) not in ALLOWED_SCOPES:
        return {"ok": False, "present": True, "status": "INVALID", "reason": "authorization scope is not BENCHMARK/NON_PRODUCTION"}
    expires = _parse_expiry(str(data.get("expiry") or ""))
    if expires is None or expires < _now():
        return {"ok": False, "present": True, "status": "INVALID", "reason": "authorization expired or expiry invalid"}
    try:
        max_units = int(data["max_units"])
        max_calls = int(data["max_llm_calls"])
    except (TypeError, ValueError):
        return {"ok": False, "present": True, "status": "INVALID", "reason": "authorization budgets must be integers"}
    if max_units <= 0 or max_calls <= 0:
        return {"ok": False, "present": True, "status": "INVALID", "reason": "authorization budgets must be positive"}
    return {
        "ok": True,
        "present": True,
        "status": "AUTHORIZED",
        "path": str(path),
        "artifact": data,
        "max_units": max_units,
        "max_llm_calls": max_calls,
    }


def bind_protocol(artifact: dict[str, Any], protocol: dict[str, Any] | None) -> dict[str, Any]:
    if not protocol:
        return artifact
    expected_hash = str(protocol.get("_definition_hash") or protocol.get("protocol_hash") or "")
    expected_id = str(protocol.get("experiment_id") or "")
    data = artifact.get("artifact") or {}
    if expected_id and str(data.get("protocol_id")) != expected_id:
        return {"ok": False, "status": "INVALID", "reason": "authorization protocol_id mismatch"}
    if expected_hash and str(data.get("protocol_hash")) != expected_hash:
        return {"ok": False, "status": "INVALID", "reason": "authorization protocol hash mismatch"}
    control = str((protocol.get("control") or {}).get("model") or "")
    candidate = str((protocol.get("candidate") or {}).get("model") or "")
    if control and str(data.get("control_model")) != control:
        return {"ok": False, "status": "INVALID", "reason": "authorization control model mismatch"}
    if candidate and str(data.get("candidate_model")) != candidate:
        return {"ok": False, "status": "INVALID", "reason": "authorization candidate model mismatch"}
    planned_units = int((protocol.get("budget") or {}).get("planned_max_units") or 0)
    planned_calls = int((protocol.get("budget") or {}).get("planned_max_llm_calls") or 0)
    if planned_units <= 0:
        planned_units = int((protocol.get("sample_plan") or {}).get("planned_n") or 0) * 2
    if planned_calls <= 0:
        planned_calls = planned_units
    auth_units = int(data.get("max_units") or 0)
    auth_calls = int(data.get("max_llm_calls") or 0)
    if auth_units > planned_units or auth_calls > planned_calls:
        return {
            "ok": False,
            "status": "INVALID",
            "reason": "authorization exceeds registered protocol budget",
        }
    return artifact


def budget_authorization_status(protocol: dict[str, Any] | None = None) -> dict[str, Any]:
    loaded = load_authorization_artifact()
    if not loaded.get("ok"):
        return loaded
    return bind_protocol(loaded, protocol)


def require_budget_authorization(protocol: dict[str, Any] | None = None) -> dict[str, Any]:
    status = budget_authorization_status(protocol)
    if not status.get("ok"):
        return {
            "ok": False,
            "executed": False,
            "status": status.get("status") or "READY_FOR_BUDGET_AUTHORIZATION",
            "reason": status.get("reason") or "unauthorized experiment blocked",
        }
    return {"ok": True, "status": "AUTHORIZED", **status}
