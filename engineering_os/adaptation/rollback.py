"""Atomic future-only rollback. Does not kill running tasks or mutate Git."""

from __future__ import annotations

from typing import Any


def rollback_binding(
    current: dict[str, Any],
    *,
    expected_version: int | None = None,
    reason: str,
    trigger: str,
) -> dict[str, Any]:
    version = int(current.get("binding_version") or 0)
    if expected_version is not None and version != expected_version:
        return {"status": "conflict", "reason": "CAS_MISMATCH", "binding_version": version}
    if current.get("state") in {"ROLLED_BACK", "DISABLED"} and current.get("mode") in {"BASELINE", "DISABLED"}:
        return {
            "status": "success",
            "already_baseline": True,
            "idempotent": True,
            "binding_version_before": version,
            "binding_version_after": version,
            "state": current.get("state"),
            "mode": "BASELINE",
            "interrupt_running": False,
            "mutate_git": False,
            "delete_evidence": False,
            "reason": reason,
            "trigger": trigger,
        }
    return {
        "status": "success",
        "already_baseline": False,
        "idempotent": True,
        "binding_version_before": version,
        "binding_version_after": version + 1,
        "state": "ROLLED_BACK",
        "mode": "BASELINE",
        "policy_hash": None,
        "fallback_config_hash": current.get("fallback_config_hash"),
        "interrupt_running": False,
        "mutate_git": False,
        "delete_evidence": False,
        "reason": reason,
        "trigger": trigger,
    }


def apply_auto_disable(current: dict[str, Any], *, reason: str) -> dict[str, Any]:
    """Guardrail FAIL disables future assignment only. Running workers stay up."""
    payload = rollback_binding(current, reason=reason, trigger="auto-disable")
    payload["auto_promote"] = False
    payload["interrupt_running"] = False
    return payload


def next_binding(
    current: dict[str, Any] | None,
    *,
    policy_hash: str | None,
    mode: str,
    state: str,
    binding_key: str,
    expected_version: int | None = None,
) -> dict[str, Any]:
    version = int((current or {}).get("binding_version") or 0)
    if expected_version is not None and version != expected_version:
        return {"status": "conflict", "reason": "CAS_MISMATCH", "binding_version": version}
    return {
        "status": "success",
        "binding_key": binding_key,
        "binding_version": version + 1,
        "policy_hash": policy_hash,
        "mode": mode,
        "state": state,
        "previous_version": version,
    }
