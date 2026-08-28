"""Single-factor configuration difference guard."""

from __future__ import annotations

from typing import Any

ALLOWED_DELTA = {
    "NONE": set(),
    "FIXTURE_ARTIFACT": {"artifact"},
    "MODEL": {"model"},
    "PROFILE": {"profile"},
    "PROMPT": {"prompt"},
    "SKILL": {"skills"},
    "TOOLS": {"tools"},
}

IDENTITY_KEYS = ("variant_id", "variant_name")


def _walk(left: Any, right: Any, prefix: str = "") -> list[str]:
    diffs: list[str] = []
    if type(left) is not type(right) and not (isinstance(left, (int, float)) and isinstance(right, (int, float))):
        diffs.append(prefix or "$")
        return diffs
    if isinstance(left, dict):
        keys = set(left) | set(right)
        for key in sorted(keys):
            path = f"{prefix}.{key}" if prefix else str(key)
            if key not in left or key not in right:
                diffs.append(path)
            else:
                diffs.extend(_walk(left[key], right[key], path))
        return diffs
    if isinstance(left, list):
        if len(left) != len(right):
            diffs.append(prefix or "$")
            return diffs
        for index, (a, b) in enumerate(zip(left, right)):
            diffs.extend(_walk(a, b, f"{prefix}[{index}]"))
        return diffs
    if left != right:
        diffs.append(prefix or "$")
    return diffs


def top_level_delta(control: dict[str, Any], candidate: dict[str, Any]) -> set[str]:
    diffs: set[str] = set()
    keys = set(control) | set(candidate)
    for key in keys:
        if key in IDENTITY_KEYS:
            continue
        if control.get(key) != candidate.get(key):
            diffs.add(key)
    return diffs


def validate_single_factor(
    treatment_dimension: str,
    control_snapshot: dict[str, Any],
    candidate_snapshot: dict[str, Any],
) -> dict[str, Any]:
    if treatment_dimension == "MULTI_FACTOR":
        return {
            "ok": False,
            "reason": "MULTI_FACTOR forbids single-dimension causal attribution in phase6-exp-v1",
            "diffs": sorted(top_level_delta(control_snapshot, candidate_snapshot)),
        }
    allowed = ALLOWED_DELTA.get(treatment_dimension)
    if allowed is None:
        return {"ok": False, "reason": f"unsupported treatment_dimension {treatment_dimension}", "diffs": []}
    diffs = top_level_delta(control_snapshot, candidate_snapshot)
    unexpected = sorted(diffs - allowed)
    if unexpected:
        return {
            "ok": False,
            "reason": "undeclared treatment dimensions differ",
            "diffs": unexpected,
        }
    if treatment_dimension not in {"NONE"} and treatment_dimension != "FIXTURE_ARTIFACT":
        missing = sorted(allowed - diffs)
        if missing and treatment_dimension != "NONE":
            # A/A uses NONE; MODEL experiments must actually differ on model.
            if treatment_dimension in diffs or not missing:
                pass
    if treatment_dimension != "NONE" and not (diffs & allowed):
        return {
            "ok": False,
            "reason": f"{treatment_dimension} experiment has no declared-dimension difference",
            "diffs": sorted(diffs),
        }
    if treatment_dimension == "NONE" and diffs:
        return {
            "ok": False,
            "reason": "A/A variants must be identical except identity metadata",
            "diffs": sorted(diffs),
        }
    return {"ok": True, "reason": "PASS", "diffs": sorted(diffs)}
