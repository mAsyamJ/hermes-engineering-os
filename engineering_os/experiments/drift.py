"""Config / environment / skill drift detection."""

from __future__ import annotations

from typing import Any


def detect(frozen: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    mapping = {
        "environment_hash": "environment",
        "definition_hash": "definition",
        "pre_registration_hash": "protocol",
    }
    for field, dimension in mapping.items():
        previous = frozen.get(field)
        actual = current.get(field)
        if previous and actual and previous != actual:
            events.append(
                {
                    "dimension": dimension,
                    "previous_hash": previous,
                    "current_hash": actual,
                    "state": "CONFIG_DRIFT",
                }
            )
    control_prev = (frozen.get("control") or {}).get("config_hash")
    control_now = (current.get("control") or {}).get("config_hash")
    cand_prev = (frozen.get("candidate") or {}).get("config_hash")
    cand_now = (current.get("candidate") or {}).get("config_hash")
    if control_prev and control_now and control_prev != control_now:
        events.append({"dimension": "control_variant", "state": "CONFIG_DRIFT", "previous_hash": control_prev, "current_hash": control_now})
    if cand_prev and cand_now and cand_prev != cand_now:
        events.append({"dimension": "candidate_variant", "state": "CONFIG_DRIFT", "previous_hash": cand_prev, "current_hash": cand_now})
    return events
