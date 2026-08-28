"""Active policy pointer helpers (CAS versioning)."""

from __future__ import annotations

from typing import Any

from engineering_os.adaptation.rollback import next_binding, rollback_binding


def activate(current: dict[str, Any] | None, policy_hash: str, binding_key: str, mode: str = "CANARY") -> dict[str, Any]:
    return next_binding(
        current,
        policy_hash=policy_hash,
        mode=mode,
        state="ACTIVE",
        binding_key=binding_key,
        expected_version=(current or {}).get("binding_version"),
    )


def supersede(current: dict[str, Any], policy_hash: str) -> dict[str, Any]:
    return next_binding(
        current,
        policy_hash=policy_hash,
        mode=current.get("mode") or "CANARY",
        state="ACTIVE",
        binding_key=current.get("binding_key") or "default",
        expected_version=current.get("binding_version"),
    )


def disable(current: dict[str, Any], reason: str, trigger: str = "operator") -> dict[str, Any]:
    payload = rollback_binding(current, expected_version=current.get("binding_version"), reason=reason, trigger=trigger)
    if payload.get("status") == "success":
        payload["state"] = "DISABLED"
        payload["mode"] = "DISABLED"
    return payload
