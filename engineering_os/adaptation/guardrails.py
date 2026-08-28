"""Deterministic canary guardrails from Phase 3/4 evidence. No Phoenix hot path."""

from __future__ import annotations

from typing import Any


def evaluate(guardrails: list[dict[str, Any]], exposures: list[dict[str, Any]], *, llm_calls: int = 0) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    state = "PASS"
    unknown = False
    auto_disable = False
    promote_blocked = False
    for spec in guardrails or []:
        metric_id = spec.get("id") or spec.get("metric")
        fail_on = spec.get("fail_on")
        critical = bool(spec.get("critical", True))
        min_n = int(spec.get("min_n") or spec.get("minimum_evidence") or 1)
        if metric_id == "llm_call_count":
            triggered = llm_calls > 0
            events.append({"metric_id": metric_id, "state": "FAIL" if triggered else "PASS", "n": llm_calls})
            if triggered and critical:
                state = "FAIL"
                auto_disable = True
            continue
        values: list[str] = []
        for exposure in exposures:
            if spec.get("candidate_only") and exposure.get("selected") != "CANDIDATE":
                continue
            vector = ((exposure.get("outcome") or {}).get("quality_vector")) or {}
            if metric_id in {"phase4.quality_vector.tests", "tests"}:
                raw = vector.get("tests")
            elif metric_id in {"phase4.quality_vector.build", "build"}:
                raw = vector.get("build")
            elif metric_id in {"phase4.quality_vector.security", "security"}:
                raw = vector.get("security")
            elif metric_id in {"task_failure_rate", "failure_rate"}:
                raw = "FAIL" if vector.get("tests") == "FAIL" else "PASS"
            else:
                raw = vector.get(metric_id)
            if raw is None:
                continue
            values.append(str(raw))
        if len(values) < min_n:
            events.append({"metric_id": metric_id, "state": "UNKNOWN", "n": len(values), "reason": "insufficient evidence"})
            unknown = True
            if critical:
                promote_blocked = True
                state = "UNKNOWN" if state == "PASS" else state
            continue
        fails = [v for v in values if v == str(fail_on) or v == "FAIL"]
        threshold = spec.get("threshold")
        failed = bool(fails)
        if threshold is not None:
            failed = (len(fails) / len(values)) >= float(threshold)
        elif fail_on == "FAIL":
            failed = bool(fails)
        event_state = "FAIL" if failed else "PASS"
        events.append({"metric_id": metric_id, "state": event_state, "n": len(values), "fails": len(fails)})
        if failed and critical:
            state = "FAIL"
            auto_disable = True
            promote_blocked = True
    if unknown and state == "PASS":
        promote_blocked = True
    return {
        "state": state,
        "events": events,
        "auto_disable": auto_disable,
        "auto_promote": False,
        "promote_blocked": promote_blocked or auto_disable or unknown,
        "unknown": unknown,
        "reason": "GUARDRAIL_FAIL" if auto_disable else ("UNKNOWN_BLOCKS_PROMOTION" if promote_blocked else "PASS"),
    }


def canary_health(guard: dict[str, Any], exposures: list[dict[str, Any]]) -> str:
    if guard.get("auto_disable") or guard.get("state") == "FAIL":
        return "CANARY_UNHEALTHY"
    if guard.get("unknown") or guard.get("state") == "UNKNOWN":
        return "CANARY_UNKNOWN"
    if not exposures:
        return "CANARY_UNKNOWN"
    return "CANARY_HEALTHY"
