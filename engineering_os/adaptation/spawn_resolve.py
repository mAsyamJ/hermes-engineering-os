"""Fail-closed pre-spawn configuration resolver. Does not mutate Kanban."""

from __future__ import annotations

import time
from typing import Any

from engineering_os.adaptation import (
    PRODUCTION_ACTUATION,
)
from engineering_os.adaptation.resolver import resolve_policy

ALLOWED_OVERRIDE_KEYS = ("model", "provider", "skills", "profile")
RESOLVER_TIMEOUT_MS = 50.0


def _baseline(reason: str, baseline: dict[str, Any], started: float) -> dict[str, Any]:
    return {
        "resolution": "BASELINE",
        "actuate": False,
        "overrides": {},
        "effective": dict(baseline),
        "reason": reason,
        "mutated_kanban": False,
        "network": False,
        "latency_ms": (time.perf_counter() - started) * 1000.0,
    }


def _sanitize_overrides(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    cleaned: dict[str, Any] = {}
    for key in ALLOWED_OVERRIDE_KEYS:
        if key not in raw:
            continue
        value = raw[key]
        if key == "skills":
            if isinstance(value, (list, tuple)):
                cleaned[key] = [str(item) for item in value if str(item)]
            elif value:
                cleaned[key] = [str(value)]
            continue
        if value in (None, ""):
            continue
        cleaned[key] = str(value)
    return cleaned


def resolve_spawn_configuration(
    task_context: dict[str, Any],
    baseline_config: dict[str, Any],
    *,
    state: dict[str, Any] | None = None,
    timeout_ms: float = RESOLVER_TIMEOUT_MS,
) -> dict[str, Any]:
    """Return baseline or approved overrides. Never writes Kanban or calls a network."""
    started = time.perf_counter()
    baseline = dict(baseline_config or {})
    try:
        scope = str(task_context.get("scope") or "")
        environment = str(task_context.get("environment") or "")
        # Unrestricted production stays disabled. Bounded shadow/canary may
        # continue to the policy resolver; the actuator still requires
        # SO_PEERCRED + signed reservation before any candidate argv.
        if PRODUCTION_ACTUATION != "ENABLED":
            if scope in {"PRODUCTION_BOUNDED", "PRODUCTION_FULL"}:
                return _baseline("PRODUCTION_ACTUATION_DISABLED", baseline, started)
            if environment == "production" and scope not in {"PRODUCTION_SHADOW", "PRODUCTION_CANARY"}:
                return _baseline("PRODUCTION_ACTUATION_DISABLED", baseline, started)
        decision = resolve_policy(task_context, state)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        if elapsed_ms > timeout_ms:
            return _baseline("actuation seam timeout", baseline, started)
        if decision.get("resolution") != "CANDIDATE" or not decision.get("actuate"):
            return _baseline(str(decision.get("reason") or "BASELINE"), baseline, started)
        candidate = decision.get("candidate") or {}
        overrides = _sanitize_overrides(candidate.get("overrides") or candidate)
        if not overrides:
            return _baseline("candidate config unavailable", baseline, started)
        effective = dict(baseline)
        effective.update(overrides)
        return {
            "resolution": "CANDIDATE",
            "actuate": True,
            "overrides": overrides,
            "effective": effective,
            "reason": decision.get("reason") or "APPROVED_POLICY",
            "policy_id": decision.get("policy_id"),
            "policy_hash": decision.get("policy_hash"),
            "config_hash": decision.get("config_hash"),
            "mutated_kanban": False,
            "network": False,
            "latency_ms": (time.perf_counter() - started) * 1000.0,
        }
    except Exception as exc:
        return _baseline(f"{type(exc).__name__}: {exc}", baseline, started)
