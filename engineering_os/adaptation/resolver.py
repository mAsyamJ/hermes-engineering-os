"""Deterministic policy resolver. Fail-closed for candidate, fail-open to baseline."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from engineering_os.adaptation import (
    CACHE_NAME,
    KILL_NAME,
)
from engineering_os.adaptation.paths import adaptation_runtime_dir


def runtime_dir() -> Path:
    return adaptation_runtime_dir(create=True)


def kill_path() -> Path:
    return runtime_dir() / KILL_NAME


def cache_path() -> Path:
    return runtime_dir() / CACHE_NAME


def kill_engaged(state: dict[str, Any] | None = None) -> bool:
    if kill_path().is_file():
        return True
    if state and state.get("kill_switch"):
        return True
    return False


def match_selector(selector: dict[str, Any], context: dict[str, Any]) -> bool:
    try:
        conditions = selector.get("conditions") or []
        combine = selector.get("match") or "ALL"
        results: list[bool] = []
        for cond in conditions:
            field = cond.get("field")
            op = cond.get("op")
            values = [str(v) for v in (cond.get("values") or [])]
            raw = context.get(field)
            haystack: list[str]
            if isinstance(raw, list):
                haystack = [str(item) for item in raw]
            elif raw is None:
                haystack = []
            else:
                haystack = [str(raw)]
            if op == "EQ":
                ok = bool(values) and values[0] in haystack
            elif op == "IN":
                ok = any(item in values for item in haystack)
            elif op == "NOT_IN":
                ok = bool(haystack) and all(item not in values for item in haystack)
            else:
                return False
            results.append(ok)
        if not results:
            return False
        return all(results) if combine == "ALL" else any(results)
    except Exception:
        return False


def _rank(binding: dict[str, Any]) -> int:
    mode = binding.get("mode") or binding.get("precedence") or "APPROVED_POLICY"
    if binding.get("deny") or mode == "EXPLICIT_DENY":
        return 1
    if binding.get("state") in {"DISABLED", "ROLLED_BACK"} or mode in {"DISABLED", "ROLLBACK_DISABLE"}:
        return 2
    if mode == "CANARY":
        return 3
    if mode in {"APPROVED_POLICY", "SHADOW", "PROMOTED"}:
        return 4
    return 5


def resolve_policy(task_context: dict[str, Any], state: dict[str, Any] | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        state = state if state is not None else load_cache()
        if kill_engaged(state):
            return _baseline("GLOBAL_KILL_SWITCH", started, task_context)
        bindings = list(state.get("bindings") or [])
        matched: list[dict[str, Any]] = []
        for binding in bindings:
            spec = binding.get("spec") or binding
            selectors = spec.get("selectors") or binding.get("selectors")
            if not selectors:
                continue
            if match_selector(selectors, task_context):
                matched.append(binding)
        if not matched:
            return _baseline("NOT_ELIGIBLE", started, task_context, result="NOT_ELIGIBLE")
        by_rank: dict[int, list[dict[str, Any]]] = {}
        for binding in matched:
            by_rank.setdefault(_rank(binding), []).append(binding)
        best = min(by_rank)
        winners = by_rank[best]
        if best == 1:
            return _baseline("EXPLICIT_DENY", started, task_context)
        if best == 2:
            return _baseline("ROLLBACK_DISABLE", started, task_context)
        if len(winners) > 1:
            return {
                "result": "CONFLICT",
                "resolution": "BASELINE",
                "reason": "POLICY_CONFLICT",
                "policy_id": None,
                "policy_hash": None,
                "config_hash": None,
                "conflict": True,
                "matched": [w.get("policy_id") or (w.get("spec") or {}).get("policy_id") for w in winners],
                "latency_ms": (time.perf_counter() - started) * 1000.0,
                "task_context": task_context,
            }
        winner = winners[0]
        spec = winner.get("spec") or winner
        if winner.get("state") in {"DISABLED", "ROLLED_BACK"}:
            return _baseline("ROLLBACK_DISABLE", started, task_context)
        if winner.get("mode") == "SHADOW":
            # Shadow bindings never return CANDIDATE for actuation; caller records would-select.
            candidate_hash = spec.get("candidate_config_hash") or (spec.get("candidate") or {}).get("config_hash")
            return {
                "result": "CANDIDATE",
                "resolution": "BASELINE",
                "actuate": False,
                "shadow": True,
                "reason": "SHADOW",
                "policy_id": spec.get("policy_id") or winner.get("policy_id"),
                "policy_hash": spec.get("_policy_hash") or winner.get("policy_hash"),
                "config_hash": candidate_hash,
                "fallback_config_hash": spec.get("fallback_config_hash")
                or (spec.get("fallback") or {}).get("config_hash"),
                "conflict": False,
                "latency_ms": (time.perf_counter() - started) * 1000.0,
                "task_context": task_context,
            }
        candidate_hash = spec.get("candidate_config_hash") or (spec.get("candidate") or {}).get("config_hash")
        if not candidate_hash:
            cand = spec.get("candidate") or {}
            candidate_hash = cand.get("variant_id") or cand.get("artifact")
        if not candidate_hash:
            return _baseline("candidate config unavailable", started, task_context)
        return {
            "result": "CANDIDATE",
            "resolution": "CANDIDATE",
            "actuate": winner.get("mode") == "CANARY",
            "shadow": winner.get("mode") == "SHADOW",
            "reason": winner.get("mode") or "APPROVED_POLICY",
            "policy_id": spec.get("policy_id") or winner.get("policy_id"),
            "policy_hash": spec.get("_policy_hash") or winner.get("policy_hash"),
            "config_hash": candidate_hash,
            "fallback_config_hash": spec.get("fallback_config_hash")
            or (spec.get("fallback") or {}).get("config_hash"),
            "conflict": False,
            "latency_ms": (time.perf_counter() - started) * 1000.0,
            "task_context": task_context,
            "candidate": spec.get("candidate"),
            "fallback": spec.get("fallback"),
        }
    except Exception as exc:
        return _baseline(f"{type(exc).__name__}: {exc}", started, task_context)


def _baseline(reason: str, started: float, task_context: dict[str, Any], result: str = "BASELINE") -> dict[str, Any]:
    return {
        "result": result,
        "resolution": "BASELINE",
        "actuate": False,
        "shadow": False,
        "reason": reason,
        "policy_id": None,
        "policy_hash": None,
        "config_hash": None,
        "conflict": result == "CONFLICT",
        "latency_ms": (time.perf_counter() - started) * 1000.0,
        "task_context": task_context,
    }


def load_cache() -> dict[str, Any]:
    path = cache_path()
    if not path.is_file():
        return {"kill_switch": kill_path().is_file(), "bindings": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"kill_switch": True, "bindings": [], "reason": "cache corrupted"}
        data.setdefault("kill_switch", kill_path().is_file())
        data.setdefault("bindings", [])
        return data
    except Exception:
        return {"kill_switch": True, "bindings": [], "reason": "cache unreadable"}


def write_cache(state: dict[str, Any]) -> Path:
    path = cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    path.chmod(0o600)
    return path


def engage_kill_switch(reason: str = "operator disable-all") -> None:
    path = kill_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(reason + "\n", encoding="utf-8")
    path.chmod(0o600)


def clear_kill_switch() -> None:
    path = kill_path()
    if path.is_file():
        path.unlink()
