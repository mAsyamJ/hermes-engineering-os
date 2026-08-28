"""Guardrail evaluation. Safety stop is not an efficacy ranking."""

from __future__ import annotations

from typing import Any


def evaluate(protocol: dict[str, Any], observations: list[dict[str, Any]], llm_calls: int = 0) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    state = "PASS"
    stop = False
    for spec in protocol.get("guardrails") or []:
        metric_id = spec["id"]
        fail_on = spec.get("fail_on")
        if metric_id == "llm_call_count":
            triggered = llm_calls > 0 if fail_on in {">0", "FAIL", 0, "> 0"} else False
            events.append(
                {
                    "metric_id": metric_id,
                    "state": "FAIL" if triggered else "PASS",
                    "reason": f"llm_calls={llm_calls}",
                }
            )
            if triggered:
                state = "FAIL"
                stop = True
            continue
        values = [row for row in observations if row.get("metric_id") == metric_id]
        fails = [row for row in values if str(row.get("value")) == str(fail_on) or str(row.get("value")) == "FAIL"]
        if fail_on == "FAIL" and fails:
            events.append({"metric_id": metric_id, "state": "FAIL", "reason": "guardrail FAIL observed", "n": len(fails)})
            state = "FAIL"
            stop = True
        else:
            events.append({"metric_id": metric_id, "state": "PASS", "reason": "no guardrail breach", "n": len(values)})
    return {
        "state": state,
        "stop": stop,
        "events": events,
        "auto_route": False,
        "reason": "GUARDRAIL_STOP" if stop else "PASS",
    }
