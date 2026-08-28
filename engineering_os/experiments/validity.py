"""Multi-dimensional experiment validity. Never blended into one score."""

from __future__ import annotations

from typing import Any

from engineering_os.experiments import VALIDITY_DIMENSIONS


def evaluate(facts: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    scope = facts.get("scope") or "FIXTURE"
    result["PROTOCOL_INTEGRITY"] = "PASS" if facts.get("protocol_hash_ok") else "FAIL"
    result["ASSIGNMENT_INTEGRITY"] = "PASS" if facts.get("assignment_ok") else "FAIL"
    result["CONFIG_INTEGRITY"] = "PASS" if facts.get("config_ok") else "FAIL"
    result["ENVIRONMENT_INTEGRITY"] = "PASS" if facts.get("environment_ok") else "FAIL"
    if scope == "FIXTURE" and facts.get("memory_mode") in {"NA", "fixture_executor"}:
        result["MEMORY_ISOLATION"] = "PASS"
    elif facts.get("memory_isolated"):
        result["MEMORY_ISOLATION"] = "PASS"
    elif facts.get("memory_blocked"):
        result["MEMORY_ISOLATION"] = "BLOCKED_CAPABILITY"
    else:
        result["MEMORY_ISOLATION"] = "FAIL"
    result["WORKSPACE_ISOLATION"] = "PASS" if facts.get("workspace_ok") else "FAIL"
    fidelity = facts.get("exposure_fidelity") or "UNKNOWN"
    if facts.get("fidelity_required") and fidelity in {"UNKNOWN", "NONCOMPLIANT", "PARTIAL"}:
        result["EXPOSURE_FIDELITY"] = "FAIL"
    else:
        result["EXPOSURE_FIDELITY"] = "PASS" if fidelity in {"MATCHED", "PARTIAL", "NONCOMPLIANT", "UNKNOWN"} else "FAIL"
        if scope == "FIXTURE":
            result["EXPOSURE_FIDELITY"] = "PASS"
    result["OUTCOME_COVERAGE"] = "PASS" if facts.get("coverage_ok") else "FAIL"
    result["EVALUATOR_COMPATIBILITY"] = "PASS" if facts.get("evaluator_ok") else "FAIL"
    for name in VALIDITY_DIMENSIONS:
        result.setdefault(name, "FAIL")
    return result


def confirmatory_allowed(validity: dict[str, str], scope: str = "FIXTURE") -> bool:
    for name, state in validity.items():
        if state == "PASS":
            continue
        if name == "MEMORY_ISOLATION" and state == "BLOCKED_CAPABILITY" and scope == "FIXTURE":
            continue
        if state == "NA":
            continue
        return False
    return True
